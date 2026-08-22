"""Seed the database from the synthetic corpus.

Gives a fully populated system with no API keys and no network. Everything
inserted here is fictional and is recorded through a SYNTHETIC source at the
lowest evidence tier, so it can never be mistaken for real research.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..agents.discovery import dedupe_key
from ..core.signals import SignalType
from ..sources.mock import SYNTHETIC_COMPANIES, make_series
from . import models as m

#: Which series to synthesise for a company, given its declared behaviour.
SERIES_FOR_SIGNAL = {
    "hiring": SignalType.HIRING,
    "patent_filings": SignalType.PATENT_FILINGS,
    "publications": SignalType.PUBLICATIONS,
    "research_citations": SignalType.RESEARCH_CITATIONS,
    "government_contracts": SignalType.GOVERNMENT_CONTRACTS,
    "customer_announcements": SignalType.CUSTOMER_ANNOUNCEMENTS,
    "partnerships": SignalType.PARTNERSHIPS,
    "manufacturing_capacity": SignalType.MANUFACTURING_CAPACITY,
    "github_activity": SignalType.GITHUB_ACTIVITY,
}


def seed(session: Session, *, today: date | None = None) -> dict[str, int]:
    """Populate candidates, financials, market estimates, claims and series."""
    today = today or date.today()

    synthetic_source = m.Source(
        name="SYNTHETIC (fictional demo data)",
        source_type="synthetic",
        url="internal://synthetic",
        tier=5,
        reliability_score=0.0,
        notes="Fictional companies for demonstration. Never real evidence.",
    )
    filing_source = m.Source(
        name="SEC EDGAR", source_type="filing", url="https://www.sec.gov/edgar",
        tier=1, reliability_score=0.95, rate_limit_per_hour=2000,
    )
    session.add_all([synthetic_source, filing_source])
    session.flush()

    created = 0
    for spec in SYNTHETIC_COMPANIES:
        key = dedupe_key(spec["name"], spec.get("ticker"))
        if session.query(m.Candidate).filter(m.Candidate.dedupe_key == key).first():
            continue

        revenue = spec["revenue"]
        revenue_prior = spec["revenue_prior"]
        growth = (revenue / revenue_prior - 1) if revenue_prior else None

        # Build the acceleration series the signal detector will read.
        series: dict[str, list[tuple[str, float]]] = {}
        for signal_name, pattern in (spec.get("signals") or {}).items():
            if signal_name not in SERIES_FOR_SIGNAL:
                continue
            points = make_series(spec["name"], signal_name, pattern, periods=18, end=today)
            series[signal_name] = [(d.isoformat(), round(v, 2)) for d, v in points]

        cand = m.Candidate(
            name=spec["name"], ticker=spec.get("ticker"),
            asset_type=spec.get("asset_type", "public_company"),
            sector=spec.get("sector"), industry=spec.get("industry"),
            description=spec["description"],
            current_market_cap=spec["market_cap"], revenue=revenue,
            revenue_growth=growth, cash=spec.get("cash"), debt=spec.get("debt"),
            shares_outstanding=spec.get("shares"),
            discovery_date=today - timedelta(days=(created * 7) % 180),
            dedupe_key=key,
            extra={"series": series, "flags": spec.get("flags", {}), "synthetic": True},
        )
        session.add(cand)
        session.flush()

        session.add(m.FinancialMetric(
            candidate_id=cand.id, as_of=today, period="TTM",
            source_id=synthetic_source.id, is_estimate=True,
            market_cap=spec["market_cap"], revenue=revenue, revenue_prior=revenue_prior,
            revenue_growth=growth,
            gross_margin=spec.get("gross_margin"),
            gross_margin_prior=spec.get("gross_margin_prior"),
            free_cash_flow=spec.get("fcf"), cash=spec.get("cash"), debt=spec.get("debt"),
            shares_outstanding=spec.get("shares"),
            shares_outstanding_prior=spec.get("shares_prior"),
            stock_based_comp=spec.get("sbc"),
            insider_ownership=spec.get("insider_own"),
            largest_customer_pct=spec.get("largest_customer"),
            ps_ratio=(spec["market_cap"] / revenue) if revenue else None,
        ))

        session.add(m.MarketEstimate(
            candidate_id=cand.id, market_name=spec.get("industry") or spec["sector"],
            as_of=today, horizon_year=today.year + 10,
            tam=spec["tam"], sam=spec["tam"] * 0.35, som=spec["tam"] * 0.05,
            methodology="Synthetic demo estimate; not an independent build-up.",
            is_management_claim=False, confidence=0.3, source_id=synthetic_source.id,
        ))

        session.add(m.Claim(
            candidate_id=cand.id, source_id=filing_source.id,
            claim=f"{spec['name']} reported revenue of ${revenue/1e6:,.1f}M "
                  f"(prior period ${revenue_prior/1e6:,.1f}M).",
            claim_type="financial", published_at=today - timedelta(days=45),
            confidence=0.9, verified=True,
        ))
        session.add(m.Claim(
            candidate_id=cand.id, source_id=synthetic_source.id,
            claim=spec["description"][:400],
            claim_type="description", published_at=today - timedelta(days=20),
            confidence=0.3, is_speculation=True,
        ))
        created += 1

    if not session.query(m.Portfolio).first():
        session.add(m.Portfolio(name="Paper Portfolio", starting_cash=10_000.0))
    if not session.query(m.Watchlist).first():
        session.add(m.Watchlist(name="Default", description="Primary research watchlist"))

    session.flush()
    return {"candidates": created, "sources": 2}
