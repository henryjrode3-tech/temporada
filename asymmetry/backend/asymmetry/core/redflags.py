"""Red flag engine (section 22).

Deterministic checks over financial and behavioural data. No LLM involved: these
are arithmetic facts about a company, and arithmetic should not be delegated to
a language model.

Each flag carries a severity, the evidence that triggered it, and the points it
deducts, so the resulting penalty is fully itemised rather than a mystery
subtraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .finmath import burn_runway_years, safe_ratio


class Severity(str, Enum):
    CRITICAL = "critical"   # often disqualifying
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


SEVERITY_POINTS: dict[Severity, float] = {
    Severity.CRITICAL: 25.0,
    Severity.HIGH: 12.0,
    Severity.MEDIUM: 6.0,
    Severity.LOW: 2.0,
}


@dataclass
class RedFlag:
    code: str
    severity: Severity
    title: str
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def points(self) -> float:
        return SEVERITY_POINTS[self.severity]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "title": self.title,
            "detail": self.detail,
            "evidence": self.evidence,
            "points": self.points,
        }


@dataclass
class RedFlagReport:
    flags: list[RedFlag]
    red_flag_score: float          # 0-100, higher is worse
    penalty_points: float          # deduction applied to the composite score

    @property
    def reasons(self) -> list[str]:
        return [f"{f.title} ({f.severity.value})" for f in self.flags]

    def to_dict(self) -> dict[str, Any]:
        return {
            "flags": [f.to_dict() for f in self.flags],
            "red_flag_score": round(self.red_flag_score, 2),
            "penalty_points": round(self.penalty_points, 2),
        }


@dataclass
class FinancialSnapshot:
    """Point-in-time financials. ``None`` means unknown, never zero.

    The distinction matters: a company with unknown debt is not a company with
    no debt, and conflating the two is how screens miss balance-sheet risk.
    """

    market_cap: float | None = None
    revenue: float | None = None
    revenue_prior: float | None = None
    gross_margin: float | None = None
    gross_margin_prior: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    free_cash_flow: float | None = None
    cash: float | None = None
    debt: float | None = None
    shares_outstanding: float | None = None
    shares_outstanding_prior: float | None = None
    stock_based_comp: float | None = None
    insider_ownership: float | None = None
    largest_customer_pct: float | None = None
    insider_selling_ratio: float | None = None      # sells / (buys + sells)
    management_departures_12m: int | None = None
    going_concern_doubt: bool = False
    restatements: int = 0
    active_investigations: int = 0
    material_lawsuits: int = 0
    auditor_changes_24m: int = 0
    missed_milestones: int = 0
    related_party_transactions: bool = False


def detect_red_flags(
    fin: FinancialSnapshot,
    *,
    hype_score: float = 0.0,
    hype_unsubstantiated: bool = False,
) -> RedFlagReport:
    """Run every deterministic check and produce an itemised report."""
    flags: list[RedFlag] = []

    def add(code: str, sev: Severity, title: str, detail: str, **evidence: Any) -> None:
        flags.append(RedFlag(code, sev, title, detail, evidence))

    # ---- Accounting integrity: the disqualifying tier ----------------------
    if fin.going_concern_doubt:
        add("GOING_CONCERN", Severity.CRITICAL, "Going-concern doubt",
            "Auditors have raised substantial doubt about the company continuing to operate.")
    if fin.restatements > 0:
        add("RESTATEMENT", Severity.CRITICAL, "Financial restatement",
            f"{fin.restatements} restatement(s) on record.", count=fin.restatements)
    if fin.active_investigations > 0:
        add("INVESTIGATION", Severity.CRITICAL, "Active regulatory investigation",
            f"{fin.active_investigations} open investigation(s).",
            count=fin.active_investigations)
    if fin.auditor_changes_24m >= 2:
        add("AUDITOR_CHURN", Severity.HIGH, "Repeated auditor changes",
            f"{fin.auditor_changes_24m} auditor changes in 24 months.",
            count=fin.auditor_changes_24m)
    if fin.related_party_transactions:
        add("RELATED_PARTY", Severity.HIGH, "Related-party transactions",
            "Revenue or expenses flow through entities connected to insiders.")

    # ---- Dilution: the quiet killer of micro-cap returns -------------------
    if fin.shares_outstanding and fin.shares_outstanding_prior:
        growth = (fin.shares_outstanding / fin.shares_outstanding_prior) - 1.0
        if growth > 0.50:
            add("DILUTION_SEVERE", Severity.CRITICAL, "Severe dilution",
                f"Share count grew {growth:.0%} year over year.", share_growth=growth)
        elif growth > 0.25:
            add("DILUTION_HIGH", Severity.HIGH, "Heavy dilution",
                f"Share count grew {growth:.0%} year over year.", share_growth=growth)
        elif growth > 0.10:
            add("DILUTION_MODERATE", Severity.MEDIUM, "Persistent dilution",
                f"Share count grew {growth:.0%} year over year.", share_growth=growth)

    # ---- Stock-based compensation -----------------------------------------
    sbc_ratio = safe_ratio(fin.stock_based_comp, fin.revenue)
    if sbc_ratio is not None:
        if sbc_ratio > 0.40:
            add("SBC_EXTREME", Severity.HIGH, "Extreme stock-based compensation",
                f"SBC is {sbc_ratio:.0%} of revenue.", sbc_to_revenue=sbc_ratio)
        elif sbc_ratio > 0.20:
            add("SBC_HIGH", Severity.MEDIUM, "High stock-based compensation",
                f"SBC is {sbc_ratio:.0%} of revenue.", sbc_to_revenue=sbc_ratio)

    # ---- Liquidity and solvency -------------------------------------------
    runway = burn_runway_years(fin.cash or 0.0, fin.free_cash_flow or 0.0)
    if runway is not None:
        if runway < 1.0:
            add("RUNWAY_CRITICAL", Severity.CRITICAL, "Under 12 months of cash",
                f"Approximately {runway*12:.0f} months of runway at the current burn.",
                runway_years=runway)
        elif runway < 2.0:
            add("RUNWAY_SHORT", Severity.HIGH, "Under 24 months of cash",
                f"Approximately {runway:.1f} years of runway; financing likely needed.",
                runway_years=runway)

    debt_to_cap = safe_ratio(fin.debt, fin.market_cap)
    if debt_to_cap is not None and debt_to_cap > 1.0:
        add("DEBT_HEAVY", Severity.HIGH, "Debt exceeds market cap",
            f"Debt is {debt_to_cap:.1f}x market capitalisation.", debt_to_market_cap=debt_to_cap)

    # ---- Deteriorating economics ------------------------------------------
    if fin.gross_margin is not None and fin.gross_margin_prior is not None:
        delta = fin.gross_margin - fin.gross_margin_prior
        if delta < -0.10:
            add("MARGIN_COLLAPSE", Severity.HIGH, "Collapsing gross margin",
                f"Gross margin fell {abs(delta)*100:.1f} points.", margin_delta=delta)
        elif delta < -0.05:
            add("MARGIN_EROSION", Severity.MEDIUM, "Eroding gross margin",
                f"Gross margin fell {abs(delta)*100:.1f} points.", margin_delta=delta)

    if fin.revenue is not None and fin.revenue_prior is not None and fin.revenue_prior > 0:
        rev_growth = (fin.revenue / fin.revenue_prior) - 1.0
        if rev_growth < -0.20:
            add("REVENUE_DECLINE", Severity.HIGH, "Revenue declining sharply",
                f"Revenue fell {abs(rev_growth):.0%} year over year.", revenue_growth=rev_growth)

    # ---- Concentration -----------------------------------------------------
    if fin.largest_customer_pct is not None:
        if fin.largest_customer_pct > 0.50:
            add("CUSTOMER_CONCENTRATION_SEVERE", Severity.HIGH, "Extreme customer concentration",
                f"One customer is {fin.largest_customer_pct:.0%} of revenue.",
                largest_customer_pct=fin.largest_customer_pct)
        elif fin.largest_customer_pct > 0.25:
            add("CUSTOMER_CONCENTRATION", Severity.MEDIUM, "Customer concentration",
                f"One customer is {fin.largest_customer_pct:.0%} of revenue.",
                largest_customer_pct=fin.largest_customer_pct)

    # ---- Insider behaviour -------------------------------------------------
    if fin.insider_selling_ratio is not None and fin.insider_selling_ratio > 0.80:
        add("INSIDER_SELLING", Severity.MEDIUM, "Heavy insider selling",
            f"{fin.insider_selling_ratio:.0%} of insider transactions were sales.",
            insider_selling_ratio=fin.insider_selling_ratio)
    if fin.management_departures_12m is not None and fin.management_departures_12m >= 3:
        add("MGMT_TURNOVER", Severity.HIGH, "Management turnover",
            f"{fin.management_departures_12m} senior departures in 12 months.",
            departures=fin.management_departures_12m)

    # ---- Execution ---------------------------------------------------------
    if fin.missed_milestones >= 3:
        add("MISSED_MILESTONES", Severity.HIGH, "Repeatedly missed milestones",
            f"{fin.missed_milestones} publicly stated milestones missed.",
            count=fin.missed_milestones)
    elif fin.missed_milestones > 0:
        add("MISSED_MILESTONE", Severity.LOW, "Missed milestone",
            f"{fin.missed_milestones} publicly stated milestone(s) missed.",
            count=fin.missed_milestones)

    if fin.material_lawsuits >= 2:
        add("LITIGATION", Severity.MEDIUM, "Material litigation",
            f"{fin.material_lawsuits} material lawsuits.", count=fin.material_lawsuits)

    # ---- Language (section 40) --------------------------------------------
    if hype_unsubstantiated:
        add("HYPE_UNSUBSTANTIATED", Severity.HIGH, "Unsubstantiated promotional language",
            f"Hype score {hype_score:.0f}/100 with little measurable evidence.",
            hype_score=hype_score)
    elif hype_score >= 35:
        add("HYPE_ELEVATED", Severity.LOW, "Promotional language",
            f"Hype score {hype_score:.0f}/100.", hype_score=hype_score)

    raw_points = sum(f.points for f in flags)
    # Compress: many small flags should not exceed one catastrophic one.
    red_flag_score = min(100.0, raw_points)
    # Cap the composite deduction so red flags shape the score without erasing
    # the rest of the analysis; genuinely disqualifying cases are handled by
    # the REJECTED verdict instead.
    penalty_points = min(30.0, raw_points * 0.6)

    return RedFlagReport(
        flags=sorted(flags, key=lambda f: -f.points),
        red_flag_score=red_flag_score,
        penalty_points=penalty_points,
    )
