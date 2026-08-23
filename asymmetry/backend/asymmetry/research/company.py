"""Research a real public company end to end.

Ticker in, evidence-backed asymmetry report out. Every number is graded, and
anything that cannot be sourced is either omitted or clearly marked as an
assumption. Nothing is invented to fill a gap.

The report deliberately degrades rather than fails. Without a price provider
there is no market capitalisation, so valuation and scenarios are omitted and
the report says why - it still contains the full financial history, growth,
dilution, balance sheet and signals, all of it sourced. A partial report built
on facts is worth more than a complete one built on a guess.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..core.evidence import Citation, Claim, EvidenceLedger, Grade, fact_claim
from ..core.finmath import (
    burn_runway_years,
    enterprise_value,
    implied_requirements,
    safe_ratio,
)
from ..core.redflags import FinancialSnapshot, detect_red_flags
from ..core.scenarios import build_scenario_set, default_scenarios, milestone_ladder
from ..sources.edgar import (
    EdgarClient,
    FinancialHistory,
    cagr_from_series,
    dilution_rate,
    growth_rate,
)
from ..sources.prices import PriceProvider, PriceUnavailable, get_price_provider

log = logging.getLogger(__name__)


@dataclass
class ResearchReport:
    """The full output. Structured so nothing implies more certainty than it has."""

    ticker: str
    company_name: str
    cik: int
    industry: str | None
    as_of: date
    generated_at: date

    ledger: EvidenceLedger = field(default_factory=EvidenceLedger)
    financial_history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    scenarios: dict[str, Any] | None = None
    reverse_valuation: dict[str, Any] | None = None
    milestones: list[dict[str, Any]] = field(default_factory=list)
    red_flags: dict[str, Any] = field(default_factory=dict)
    key_assumptions: list[dict[str, Any]] = field(default_factory=list)
    invalidators: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    verdict: str = "INSUFFICIENT_DATA"
    verdict_reason: str = ""

    #: Never "buy". The platform produces research, not instructions.
    disclaimer: str = (
        "Research output. Facts are sourced to SEC filings; estimates and "
        "assumptions are labelled as such. Scenario values are conditional "
        "arithmetic under stated assumptions, not forecasts. Not investment "
        "advice and not a recommendation to transact."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker, "company_name": self.company_name,
            "cik": self.cik, "industry": self.industry,
            "as_of": self.as_of.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "evidence": self.ledger.to_dict(),
            "financial_history": self.financial_history,
            "scenarios": self.scenarios,
            "reverse_valuation": self.reverse_valuation,
            "milestones": self.milestones,
            "red_flags": self.red_flags,
            "key_assumptions": self.key_assumptions,
            "what_would_invalidate": self.invalidators,
            "missing_data": self.missing,
            "verdict": self.verdict, "verdict_reason": self.verdict_reason,
            "disclaimer": self.disclaimer,
        }


#: Sector-level defaults used when nothing better is known. Every one of these
#: is an ASSUMPTION and is graded as such, which is what stops a scenario built
#: on them from presenting as analysis.
SECTOR_ASSUMPTIONS: dict[str, dict[str, float]] = {
    "default":       {"net_margin": 0.12, "exit_multiple": 18.0, "tam_multiple": 60.0},
    "software":      {"net_margin": 0.20, "exit_multiple": 25.0, "tam_multiple": 80.0},
    "semiconductor": {"net_margin": 0.22, "exit_multiple": 22.0, "tam_multiple": 70.0},
    "pharma":        {"net_margin": 0.18, "exit_multiple": 16.0, "tam_multiple": 90.0},
    "industrial":    {"net_margin": 0.10, "exit_multiple": 16.0, "tam_multiple": 40.0},
    "energy":        {"net_margin": 0.09, "exit_multiple": 12.0, "tam_multiple": 35.0},
    "mining":        {"net_margin": 0.12, "exit_multiple": 12.0, "tam_multiple": 30.0},
}


def _sector_key(sic_description: str | None) -> str:
    if not sic_description:
        return "default"
    text = sic_description.lower()
    for key, needles in (
        ("software", ("software", "prepackaged", "computer programming", "services-computer")),
        ("semiconductor", ("semiconductor", "electronic component")),
        ("pharma", ("pharmaceutical", "biological", "medicinal", "in vitro")),
        ("industrial", ("machinery", "industrial", "manufacturing", "electrical", "equipment")),
        ("energy", ("petroleum", "electric", "energy", "natural gas", "power")),
        ("mining", ("mining", "metal", "gold", "copper")),
    ):
        if any(n in text for n in needles):
            return key
    return "default"


class CompanyResearcher:
    """Assembles a report from real filings plus explicitly-labelled assumptions."""

    def __init__(
        self,
        edgar: EdgarClient | None = None,
        prices: PriceProvider | None = None,
    ) -> None:
        self.edgar = edgar or EdgarClient()
        self.prices = prices or get_price_provider()

    def research(
        self,
        ticker: str,
        *,
        as_of: date | None = None,
        horizon_years: float = 10.0,
        tam_override: float | None = None,
    ) -> ResearchReport:
        cutoff = as_of or date.today()
        history = self.edgar.fetch_history(ticker)
        identity = history.identity

        report = ResearchReport(
            ticker=identity.ticker, company_name=identity.name, cik=identity.cik,
            industry=identity.sic_description, as_of=cutoff, generated_at=date.today(),
        )
        ledger = report.ledger

        self._add_fundamentals(report, history, cutoff)
        shares = self._add_share_data(report, history, cutoff)
        market_cap = self._add_valuation(report, ticker, shares, cutoff)
        self._add_history_series(report, history, cutoff)
        self._add_red_flags(report, history, cutoff)

        if market_cap is not None:
            self._add_scenarios(report, history, market_cap, cutoff, horizon_years, tam_override)
        else:
            report.missing.append(
                "Market capitalisation - no price provider configured. Valuation, "
                "scenarios and the asymmetry score are omitted rather than estimated."
            )

        self._assign_verdict(report)
        return report

    # ---- fundamentals ---------------------------------------------------
    def _add_fundamentals(
        self, report: ResearchReport, history: FinancialHistory, cutoff: date
    ) -> None:
        ledger = report.ledger

        revenue = history.latest("revenue", as_of=cutoff, annual=True)
        if revenue:
            ledger.add(fact_claim("Revenue (latest annual)", revenue))
            series = history.series("revenue", as_of=cutoff, annual=True)
            yoy = growth_rate(series)
            if yoy is not None:
                ledger.add(Claim(
                    label="Revenue growth (YoY)", value=yoy, grade=Grade.DERIVED, unit="%",
                    citations=[
                        Citation(source=f"SEC EDGAR {f.form}", url=f.source_url,
                                 accession=f.accession, filed=f.filed,
                                 period_end=f.period_end, tag=f.tag)
                        for f in series[-2:]
                    ],
                    rationale="Latest annual revenue against the prior year, both as "
                              "first reported.",
                    as_of=series[-1].period_end,
                ))
            long_run = cagr_from_series(series)
            if long_run is not None and len(series) >= 3:
                ledger.add(Claim(
                    label=f"Revenue CAGR ({len(series)} periods)", value=long_run,
                    grade=Grade.DERIVED, unit="%",
                    citations=[Citation(source="SEC EDGAR", tag="revenue")],
                    rationale=f"Compound growth from FY{series[0].period_end.year} "
                              f"to FY{series[-1].period_end.year}.",
                ))
        else:
            report.missing.append("Revenue - no annual figure found in XBRL filings.")

        for concept, label in (
            ("net_income", "Net income"),
            ("operating_income", "Operating income"),
            ("gross_profit", "Gross profit"),
            ("operating_cash_flow", "Operating cash flow"),
            ("cash", "Cash and equivalents"),
            ("total_assets", "Total assets"),
            ("equity", "Shareholders' equity"),
            ("stock_based_comp", "Stock-based compensation"),
            ("rd_expense", "R&D expense"),
        ):
            fact = history.latest(concept, as_of=cutoff, annual=True)
            if fact:
                ledger.add(fact_claim(label, fact))

        # Free cash flow is derived, and says so.
        fcf = history.derived_free_cash_flow(as_of=cutoff)
        if fcf:
            value, ocf, capex = fcf
            ledger.add(Claim(
                label="Free cash flow", value=value, grade=Grade.DERIVED, unit="USD",
                citations=[
                    Citation(source=f"SEC EDGAR {ocf.form}", url=ocf.source_url,
                             accession=ocf.accession, filed=ocf.filed,
                             period_end=ocf.period_end, tag=ocf.tag),
                    Citation(source=f"SEC EDGAR {capex.form}", url=capex.source_url,
                             accession=capex.accession, filed=capex.filed,
                             period_end=capex.period_end, tag=capex.tag),
                ],
                rationale="Operating cash flow less capital expenditure. Derived, not "
                          "a reported line item.",
                as_of=ocf.period_end,
            ))

        # Gross margin, if both inputs exist.
        rev = history.latest("revenue", as_of=cutoff, annual=True)
        gp = history.latest("gross_profit", as_of=cutoff, annual=True)
        if rev and gp and rev.value > 0:
            margin_claim = ledger.get("Gross profit")
            revenue_claim = ledger.get("Revenue (latest annual)")
            if margin_claim and revenue_claim:
                ledger.add(Claim.derive(
                    "Gross margin", gp.value / rev.value, [margin_claim, revenue_claim],
                    rationale="Gross profit divided by revenue.", unit="%",
                ))

        # Debt: summed from components when no combined tag is filed.
        debt_total = 0.0
        debt_citations: list[Citation] = []
        for concept in ("long_term_debt", "short_term_debt"):
            fact = history.latest(concept, as_of=cutoff, annual=True)
            if fact:
                debt_total += fact.value
                debt_citations.append(Citation(
                    source=f"SEC EDGAR {fact.form}", url=fact.source_url,
                    accession=fact.accession, filed=fact.filed,
                    period_end=fact.period_end, tag=fact.tag,
                ))
        if debt_citations:
            ledger.add(Claim(
                label="Total debt", value=debt_total,
                grade=Grade.FACT if len(debt_citations) == 1 else Grade.DERIVED,
                unit="USD", citations=debt_citations,
                rationale="Long-term plus current portion of debt as filed."
                          if len(debt_citations) > 1 else "",
            ))
        else:
            report.missing.append("Debt - no debt tags found; the company may carry none.")

        # Runway, which is what actually matters for a cash-burning company.
        cash_claim = ledger.get("Cash and equivalents")
        fcf_claim = ledger.get("Free cash flow")
        if cash_claim and fcf_claim and isinstance(fcf_claim.value, float):
            runway = burn_runway_years(float(cash_claim.value), float(fcf_claim.value))
            if runway is not None:
                ledger.add(Claim.derive(
                    "Cash runway (years)", runway, [cash_claim, fcf_claim],
                    rationale="Cash divided by free-cash-flow burn. Assumes the burn "
                              "rate holds and no further financing.",
                    unit=None,
                ))

    def _add_share_data(
        self, report: ResearchReport, history: FinancialHistory, cutoff: date
    ) -> float | None:
        ledger = report.ledger
        shares_fact = history.latest("shares_outstanding", as_of=cutoff, annual=True)
        if shares_fact is None:
            report.missing.append("Shares outstanding - not found in XBRL filings.")
            return None

        ledger.add(fact_claim("Shares outstanding", shares_fact, unit="shares"))

        series = history.series("shares_outstanding", as_of=cutoff, annual=True)
        estimate = dilution_rate(series)
        if estimate.best_estimate is not None:
            ledger.add(Claim(
                label="Annual dilution", value=estimate.best_estimate,
                grade=Grade.DERIVED if not estimate.has_ambiguous_split else Grade.ESTIMATE,
                unit="%",
                citations=[Citation(source="SEC EDGAR", tag="shares_outstanding")],
                rationale=(
                    f"Share-count growth over {estimate.window_years} years "
                    f"({estimate.periods} periods). {estimate.note()}"
                    + ("".join(f" {s.describe()}" for s in estimate.splits))
                ),
                as_of=shares_fact.period_end,
            ))
        return float(shares_fact.value)

    def _add_valuation(
        self, report: ResearchReport, ticker: str, shares: float | None, cutoff: date
    ) -> float | None:
        if shares is None:
            return None
        historical = cutoff < date.today()
        try:
            quote = self.prices.get_price(ticker, on=cutoff if historical else None)
        except PriceUnavailable as exc:
            log.info("no price for %s: %s", ticker, exc)
            return None

        ledger = report.ledger
        price_claim = ledger.add(Claim(
            label="Share price", value=quote.price,
            grade=Grade.FACT if quote.source != "manual (operator-supplied)" else Grade.ESTIMATE,
            unit="USD",
            citations=[Citation(source=quote.source, period_end=quote.as_of)],
            rationale=f"{quote.source} as of {quote.as_of.isoformat()}."
                      + (f" {quote.stale_days} day(s) stale." if quote.stale_days > 3 else ""),
            as_of=quote.as_of,
        ))
        shares_claim = ledger.get("Shares outstanding")
        market_cap = quote.price * shares

        ledger.add(Claim.derive(
            "Market capitalisation", market_cap,
            [price_claim] + ([shares_claim] if shares_claim else []),
            rationale="Share price times shares outstanding. The share count is the "
                      "latest filed figure, which may lag the price.",
            unit="USD",
        ))

        cash_claim = ledger.get("Cash and equivalents")
        debt_claim = ledger.get("Total debt")
        if cash_claim and debt_claim:
            ev = enterprise_value(market_cap, float(debt_claim.value), float(cash_claim.value))
            ledger.add(Claim.derive(
                "Enterprise value", ev,
                [ledger.get("Market capitalisation"), cash_claim, debt_claim],
                rationale="Market cap plus debt less cash.", unit="USD",
            ))

        revenue_claim = ledger.get("Revenue (latest annual)")
        if revenue_claim and float(revenue_claim.value) > 0:
            ps = safe_ratio(market_cap, float(revenue_claim.value))
            if ps is not None:
                ledger.add(Claim.derive(
                    "Price / sales", ps,
                    [ledger.get("Market capitalisation"), revenue_claim],
                    rationale="Market capitalisation divided by latest annual revenue.",
                    unit="x",
                ))
        return market_cap

    def _add_history_series(
        self, report: ResearchReport, history: FinancialHistory, cutoff: date
    ) -> None:
        """Full annual history, so the reader can see the trend, not just a snapshot."""
        for concept in ("revenue", "net_income", "operating_cash_flow", "cash",
                        "shares_outstanding", "gross_profit"):
            series = history.series(concept, as_of=cutoff, annual=True)
            if len(series) < 2:
                continue
            report.financial_history[concept] = [
                {
                    "period_end": f.period_end.isoformat(),
                    "fiscal_year": f.period_end.year,
                    "value": f.value,
                    "filed": f.filed.isoformat(),
                    "form": f.form,
                    "accession": f.accession,
                    "url": f.source_url,
                }
                for f in series
            ]

    def _add_red_flags(
        self, report: ResearchReport, history: FinancialHistory, cutoff: date
    ) -> None:
        """Deterministic checks over the real filings."""
        def val(concept: str) -> float | None:
            f = history.latest(concept, as_of=cutoff, annual=True)
            return f.value if f else None

        rev_series = history.series("revenue", as_of=cutoff, annual=True)
        share_series = history.series("shares_outstanding", as_of=cutoff, annual=True)
        gp = val("gross_profit")
        rev = val("revenue")
        fcf = history.derived_free_cash_flow(as_of=cutoff)

        gross_margin = (gp / rev) if gp is not None and rev else None
        gross_margin_prior = None
        gp_series = history.series("gross_profit", as_of=cutoff, annual=True)
        if len(gp_series) >= 2 and len(rev_series) >= 2 and rev_series[-2].value:
            gross_margin_prior = gp_series[-2].value / rev_series[-2].value

        snapshot = FinancialSnapshot(
            revenue=rev,
            revenue_prior=rev_series[-2].value if len(rev_series) >= 2 else None,
            gross_margin=gross_margin, gross_margin_prior=gross_margin_prior,
            operating_income=val("operating_income"), net_income=val("net_income"),
            free_cash_flow=fcf[0] if fcf else None,
            cash=val("cash"),
            debt=(val("long_term_debt") or 0) + (val("short_term_debt") or 0) or None,
            shares_outstanding=share_series[-1].value if share_series else None,
            shares_outstanding_prior=share_series[-2].value if len(share_series) >= 2 else None,
            stock_based_comp=val("stock_based_comp"),
        )
        result = detect_red_flags(snapshot)
        report.red_flags = result.to_dict()
        report.red_flags["note"] = (
            "Computed arithmetically from filed figures. Behavioural flags "
            "(insider selling, investigations, auditor changes) are not covered: "
            "they require sources beyond XBRL."
        )

    # ---- scenarios ------------------------------------------------------
    def _add_scenarios(
        self, report: ResearchReport, history: FinancialHistory, market_cap: float,
        cutoff: date, horizon_years: float, tam_override: float | None,
    ) -> None:
        ledger = report.ledger
        revenue_claim = ledger.get("Revenue (latest annual)")
        revenue = float(revenue_claim.value) if revenue_claim else None

        sector = _sector_key(report.industry)
        params = SECTOR_ASSUMPTIONS[sector]

        if tam_override:
            tam = tam_override
            tam_claim = ledger.add(Claim(
                label="Addressable market", value=tam, grade=Grade.ASSUMPTION, unit="USD",
                rationale="Supplied by the operator. Not independently verified.",
                confidence=0.4,
            ))
        elif revenue:
            tam = revenue * params["tam_multiple"]
            tam_claim = ledger.add(Claim(
                label="Addressable market", value=tam, grade=Grade.ASSUMPTION, unit="USD",
                rationale=(
                    f"No independent market study was performed. Approximated as "
                    f"{params['tam_multiple']:.0f}x current revenue, a crude "
                    f"sector heuristic for {sector}. This is the weakest input in "
                    f"the entire report and every scenario inherits its uncertainty."
                ),
                confidence=0.2,
            ))
        else:
            report.missing.append("Addressable market - no revenue to scale from.")
            return

        margin_claim = ledger.add(Claim(
            label="Assumed net margin at maturity", value=params["net_margin"],
            grade=Grade.ASSUMPTION, unit="%",
            rationale=f"Sector norm for {sector}. Not the company's current margin.",
            confidence=0.35,
        ))
        multiple_claim = ledger.add(Claim(
            label="Assumed exit multiple", value=params["exit_multiple"],
            grade=Grade.ASSUMPTION, unit="x",
            rationale=f"Sector norm for {sector}.", confidence=0.35,
        ))

        dilution_claim = ledger.get("Annual dilution")
        dilution = 0.03
        if dilution_claim and isinstance(dilution_claim.value, float):
            # Buybacks are not a promise; assume they stop rather than continue.
            dilution = max(0.0, float(dilution_claim.value))

        scenario_set = build_scenario_set(
            default_scenarios(
                tam, current_revenue=revenue,
                net_margin=params["net_margin"],
                exit_multiple=params["exit_multiple"],
                dilution_cagr=dilution,
            ),
            market_cap, horizon_years,
        )
        report.scenarios = scenario_set.to_dict()
        report.scenarios["probability_note"] = (
            "Scenario probabilities (40/35/20/5) are a hand-chosen prior for "
            "speculative companies, not a measured distribution. They are an "
            "ASSUMPTION and the expected value inherits their uncertainty entirely."
        )

        reverse = implied_requirements(
            market_cap, total_market=tam, net_margin=params["net_margin"],
            exit_multiple=params["exit_multiple"], years=horizon_years,
        )
        report.reverse_valuation = {
            "required_revenue": reverse.required_revenue,
            "required_market_share": reverse.required_market_share,
            "verdict": reverse.verdict,
            "share_is_implausible": reverse.share_is_implausible,
            "years": horizon_years,
            "grade": Grade.ASSUMPTION.label,
            "note": "Rests on the assumed market size, margin and exit multiple above.",
        }
        report.milestones = [
            {"label": mi.label, "reachable": mi.reachable,
             "required_revenue": mi.required_revenue,
             "required_market_share": mi.required_market_share,
             "multiple_from_here": mi.multiple_from_here,
             "implied_cagr": mi.implied_cagr, "commentary": mi.commentary}
            for mi in milestone_ladder(
                market_cap, tam, params["net_margin"], params["exit_multiple"], horizon_years
            )
        ]

        report.key_assumptions = [
            c.to_dict() for c in ledger.claims if c.grade >= Grade.ASSUMPTION
        ]
        report.invalidators = self._invalidators(report, scenario_set)

    def _invalidators(self, report: ResearchReport, scenario_set: Any) -> list[str]:
        """What would break the thesis, tied to figures actually in the report."""
        out: list[str] = []
        ledger = report.ledger

        growth = ledger.get("Revenue growth (YoY)")
        if growth and isinstance(growth.value, float):
            floor = max(0.0, growth.value * 0.5)
            out.append(
                f"Revenue growth falling below {floor:.0%} for two consecutive years "
                f"(currently {growth.value:.0%}) would break the base case."
            )
        margin = ledger.get("Gross margin")
        if margin and isinstance(margin.value, float):
            out.append(
                f"Gross margin falling materially below {margin.value:.0%} would "
                f"undermine the assumed {SECTOR_ASSUMPTIONS[_sector_key(report.industry)]['net_margin']:.0%} "
                f"mature net margin."
            )
        dilution = ledger.get("Annual dilution")
        if dilution and isinstance(dilution.value, float) and dilution.value > 0.05:
            out.append(
                f"Continued dilution at {dilution.value:.0%} a year compounds against "
                f"holders; the per-share outcome is far worse than the market-cap one."
            )
        runway = ledger.get("Cash runway (years)")
        if runway and isinstance(runway.value, float) and runway.value < 3:
            out.append(
                f"Cash runway of {runway.value:.1f} years means financing is likely "
                f"before the thesis resolves, on terms nobody can predict."
            )
        out.append(
            "The addressable market is an assumption, not a study. If the real market "
            "is materially smaller, every scenario above is too optimistic."
        )
        return out

    # ---- verdict --------------------------------------------------------
    def _assign_verdict(self, report: ResearchReport) -> None:
        """Research status. Never a recommendation to transact."""
        ledger = report.ledger
        warnings = ledger.integrity_warnings()
        red_flag_score = report.red_flags.get("red_flag_score", 0)

        if report.scenarios is None:
            report.verdict = "INSUFFICIENT_DATA"
            report.verdict_reason = (
                "Fundamentals were retrieved but valuation could not be computed, so "
                "no asymmetry assessment is possible. " + (report.missing[0] if report.missing else "")
            )
            return

        asymmetry = report.scenarios.get("asymmetry_score", 0)
        if red_flag_score >= 70:
            report.verdict = "REJECTED"
            report.verdict_reason = "Severe red flags in the filed financials."
        elif asymmetry >= 70 and ledger.evidence_ratio >= 0.4:
            report.verdict = "WORTH_INVESTIGATING"
            report.verdict_reason = (
                f"Payoff asymmetry of {asymmetry:.0f}/100 under stated assumptions, on a "
                f"report that is {ledger.evidence_ratio:.0%} sourced. Warrants human "
                f"research, particularly of the market-size assumption."
            )
        elif asymmetry >= 50:
            report.verdict = "WATCH"
            report.verdict_reason = (
                f"Moderate asymmetry ({asymmetry:.0f}/100). Not compelling at this price "
                f"under these assumptions."
            )
        else:
            report.verdict = "NOT_ASYMMETRIC"
            report.verdict_reason = (
                f"Asymmetry of {asymmetry:.0f}/100. Today's price already reflects much "
                f"of the plausible upside."
            )
        if warnings:
            report.verdict_reason += " Caveats: " + " ".join(warnings)


def research_ticker(
    ticker: str,
    *,
    as_of: date | None = None,
    price: float | None = None,
    tam: float | None = None,
    horizon_years: float = 10.0,
) -> ResearchReport:
    """Convenience entry point. ``price`` supplies a manual quote."""
    provider: PriceProvider | None = None
    if price is not None:
        from ..sources.prices import ManualPriceProvider

        provider = ManualPriceProvider({ticker.upper(): price})
    researcher = CompanyResearcher(prices=provider)
    return researcher.research(
        ticker, as_of=as_of, horizon_years=horizon_years, tam_override=tam
    )
