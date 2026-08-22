"""Deterministic mock sources.

Lets the entire pipeline run offline, makes tests hermetic, and gives the
dashboard something meaningful to render before any API key exists.

**Every company here is fictional.** That is deliberate. Attaching invented
financials to a real ticker would manufacture false financial records about a
real business - the exact failure mode the fact-checking layer exists to
prevent - so the synthetic corpus uses invented names, and every record it
produces is tagged ``synthetic: True`` and carries a SYNTHETIC source tier so it
can never be mistaken for evidence.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from typing import Any

from .base import RawDoc, Source, SourceTier

#: Fictional companies spanning the sectors the platform is meant to sweep.
#: Financial shapes are plausible archetypes rather than copies of real firms:
#: pre-revenue deep tech, subscale-but-growing hardware, priced-for-perfection
#: darlings, and a couple of outright frauds for the red-flag engine to catch.
SYNTHETIC_COMPANIES: list[dict[str, Any]] = [
    {
        "name": "Cascade Fission Systems", "ticker": "CFSY", "sector": "Nuclear",
        "industry": "Small modular reactors", "asset_type": "public_company",
        "description": "Designs factory-built 80MW modular fission reactors targeting "
                       "data-centre and industrial-heat customers. Two NRC design "
                       "certification milestones cleared; no commercial unit delivered.",
        "market_cap": 410e6, "revenue": 18e6, "revenue_prior": 9e6,
        "gross_margin": 0.21, "gross_margin_prior": 0.14,
        "cash": 240e6, "debt": 30e6, "fcf": -95e6,
        "shares": 88e6, "shares_prior": 74e6, "sbc": 14e6,
        "tam": 90e9, "insider_own": 0.18, "largest_customer": 0.44,
        "signals": {"government_contracts": "accelerating", "hiring": "accelerating",
                    "patent_filings": "steady"},
    },
    {
        "name": "Meridian Grid Components", "ticker": "MGCP", "sector": "Electrical Equipment",
        "industry": "High-voltage transformers", "asset_type": "public_company",
        "description": "Manufactures large power transformers and phase-shifting "
                       "transformers. Order backlog extends past three years amid "
                       "grid-replacement demand. Unfashionable, profitable, capacity constrained.",
        "market_cap": 1.35e9, "revenue": 620e6, "revenue_prior": 455e6,
        "gross_margin": 0.29, "gross_margin_prior": 0.24,
        "cash": 95e6, "debt": 210e6, "fcf": 61e6,
        "shares": 41e6, "shares_prior": 40.5e6, "sbc": 9e6,
        "tam": 55e9, "insider_own": 0.22, "largest_customer": 0.19,
        "signals": {"manufacturing_capacity": "accelerating", "hiring": "accelerating",
                    "customer_announcements": "accelerating"},
    },
    {
        "name": "Photonic Interconnect Labs", "ticker": "PHIL", "sector": "Semiconductors",
        "industry": "Co-packaged optics", "asset_type": "public_company",
        "description": "Silicon-photonics engine for rack-scale optical interconnect. "
                       "Two hyperscaler qualification programmes disclosed. Pre-volume, "
                       "cash-hungry, dependent on a single foundry partner.",
        "market_cap": 780e6, "revenue": 31e6, "revenue_prior": 12e6,
        "gross_margin": 0.34, "gross_margin_prior": 0.28,
        "cash": 180e6, "debt": 5e6, "fcf": -72e6,
        "shares": 120e6, "shares_prior": 96e6, "sbc": 28e6,
        "tam": 40e9, "insider_own": 0.11, "largest_customer": 0.58,
        "signals": {"patent_filings": "accelerating", "publications": "accelerating",
                    "hiring": "accelerating", "partnerships": "accelerating"},
    },
    {
        "name": "Halden Thermal Systems", "ticker": "HTSY", "sector": "Industrials",
        "industry": "Data-centre liquid cooling", "asset_type": "public_company",
        "description": "Direct-to-chip and immersion cooling loops for high-density "
                       "racks. Profitable, family-controlled, minimal analyst coverage.",
        "market_cap": 520e6, "revenue": 210e6, "revenue_prior": 138e6,
        "gross_margin": 0.37, "gross_margin_prior": 0.35,
        "cash": 60e6, "debt": 25e6, "fcf": 24e6,
        "shares": 26e6, "shares_prior": 25.8e6, "sbc": 4e6,
        "tam": 28e9, "insider_own": 0.41, "largest_customer": 0.22,
        "signals": {"customer_announcements": "accelerating", "hiring": "accelerating",
                    "manufacturing_capacity": "accelerating"},
    },
    {
        "name": "Kestrel Quantum Sensing", "ticker": "KQSN", "sector": "Quantum",
        "industry": "Atomic magnetometry", "asset_type": "public_company",
        "description": "Chip-scale atomic magnetometers for navigation without GPS "
                       "and for biomagnetic imaging. Defence evaluation contracts; "
                       "commercial revenue negligible.",
        "market_cap": 195e6, "revenue": 4.2e6, "revenue_prior": 2.6e6,
        "gross_margin": 0.18, "gross_margin_prior": 0.22,
        "cash": 48e6, "debt": 2e6, "fcf": -31e6,
        "shares": 64e6, "shares_prior": 47e6, "sbc": 11e6,
        "tam": 12e9, "insider_own": 0.14, "largest_customer": 0.71,
        "signals": {"government_contracts": "accelerating", "publications": "accelerating",
                    "research_citations": "accelerating"},
    },
    {
        "name": "Verdant Biomanufacturing", "ticker": "VBIO", "sector": "Biotechnology",
        "industry": "Precision fermentation", "asset_type": "public_company",
        "description": "Continuous fermentation platform producing specialty proteins "
                       "and enzymes at industrial scale. Third plant under construction; "
                       "unit economics unproven above pilot scale.",
        "market_cap": 340e6, "revenue": 47e6, "revenue_prior": 29e6,
        "gross_margin": 0.11, "gross_margin_prior": 0.05,
        "cash": 88e6, "debt": 140e6, "fcf": -66e6,
        "shares": 155e6, "shares_prior": 118e6, "sbc": 12e6,
        "tam": 34e9, "insider_own": 0.09, "largest_customer": 0.31,
        "signals": {"manufacturing_capacity": "accelerating", "patent_filings": "steady"},
    },
    {
        "name": "Anvil Rare Earth Processing", "ticker": "ANVL", "sector": "Materials",
        "industry": "Separation and refining", "asset_type": "public_company",
        "description": "Solvent-free rare-earth separation using ligand-assisted "
                       "chromatography. One demonstration line running; offtake "
                       "agreements signed but not yet binding.",
        "market_cap": 265e6, "revenue": 11e6, "revenue_prior": 3e6,
        "gross_margin": 0.08, "gross_margin_prior": -0.12,
        "cash": 71e6, "debt": 18e6, "fcf": -44e6,
        "shares": 98e6, "shares_prior": 79e6, "sbc": 7e6,
        "tam": 22e9, "insider_own": 0.16, "largest_customer": 0.49,
        "signals": {"government_contracts": "accelerating", "partnerships": "accelerating",
                    "hiring": "steady"},
    },
    {
        "name": "Northline Orbital Imaging", "ticker": "NRTH", "sector": "Space",
        "industry": "Synthetic aperture radar", "asset_type": "public_company",
        "description": "Small SAR constellation providing all-weather imagery. "
                       "Eleven satellites on orbit. Revenue concentrated in two "
                       "government customers; constellation replacement capex is relentless.",
        "market_cap": 610e6, "revenue": 96e6, "revenue_prior": 61e6,
        "gross_margin": 0.42, "gross_margin_prior": 0.38,
        "cash": 130e6, "debt": 95e6, "fcf": -38e6,
        "shares": 142e6, "shares_prior": 121e6, "sbc": 22e6,
        "tam": 18e9, "insider_own": 0.13, "largest_customer": 0.52,
        "signals": {"government_contracts": "accelerating", "customer_announcements": "steady"},
    },
    {
        "name": "Ironbark OT Security", "ticker": "IRBK", "sector": "Cybersecurity",
        "industry": "Industrial control systems", "asset_type": "public_company",
        "description": "Passive monitoring and anomaly detection for SCADA and "
                       "industrial control networks. Sticky contracts, slow sales "
                       "cycles, deeply unglamorous.",
        "market_cap": 890e6, "revenue": 178e6, "revenue_prior": 129e6,
        "gross_margin": 0.71, "gross_margin_prior": 0.68,
        "cash": 145e6, "debt": 0, "fcf": 19e6,
        "shares": 55e6, "shares_prior": 53e6, "sbc": 31e6,
        "tam": 26e9, "insider_own": 0.19, "largest_customer": 0.14,
        "signals": {"hiring": "accelerating", "customer_announcements": "accelerating"},
    },
    {
        "name": "Solstice Solid State", "ticker": "SLST", "sector": "Batteries",
        "industry": "Solid-state cells", "asset_type": "public_company",
        "description": "Sulfide-electrolyte solid-state cells targeting automotive "
                       "qualification. Cycle-life data disclosed only in aggregate. "
                       "Capital requirements enormous relative to current size.",
        "market_cap": 1.9e9, "revenue": 2.1e6, "revenue_prior": 0.4e6,
        "gross_margin": -1.4, "gross_margin_prior": -2.1,
        "cash": 410e6, "debt": 60e6, "fcf": -210e6,
        "shares": 310e6, "shares_prior": 240e6, "sbc": 63e6,
        "tam": 120e9, "insider_own": 0.07, "largest_customer": 0.88,
        "signals": {"patent_filings": "accelerating", "hiring": "steady"},
        "hype": "high",
    },
    {
        "name": "Aperture Metrology", "ticker": "APMT", "sector": "Semiconductors",
        "industry": "Inspection and metrology", "asset_type": "public_company",
        "description": "High-throughput e-beam inspection for advanced logic nodes. "
                       "Two of five leading fabs qualified. Long qualification cycles "
                       "create both the moat and the risk.",
        "market_cap": 2.4e9, "revenue": 380e6, "revenue_prior": 265e6,
        "gross_margin": 0.58, "gross_margin_prior": 0.54,
        "cash": 290e6, "debt": 40e6, "fcf": 72e6,
        "shares": 62e6, "shares_prior": 61e6, "sbc": 38e6,
        "tam": 45e9, "insider_own": 0.24, "largest_customer": 0.34,
        "signals": {"patent_filings": "accelerating", "customer_announcements": "accelerating",
                    "hiring": "accelerating", "research_citations": "steady"},
    },
    {
        "name": "Tessellate Robotics", "ticker": "TSLR", "sector": "Robotics",
        "industry": "Warehouse automation", "asset_type": "public_company",
        "description": "Mobile manipulation for mixed-case palletising. Deployments "
                       "at four logistics operators. Gross margin negative on early units.",
        "market_cap": 1.1e9, "revenue": 64e6, "revenue_prior": 38e6,
        "gross_margin": -0.08, "gross_margin_prior": -0.31,
        "cash": 195e6, "debt": 15e6, "fcf": -88e6,
        "shares": 175e6, "shares_prior": 149e6, "sbc": 42e6,
        "tam": 60e9, "insider_own": 0.12, "largest_customer": 0.41,
        "signals": {"hiring": "accelerating", "customer_announcements": "accelerating",
                    "github_activity": "steady"},
    },
    # --- Deliberate failures, so the red-flag engine has something to catch ---
    {
        "name": "QuantumLeap AI Dynamics", "ticker": "QLAD", "sector": "AI",
        "industry": "Enterprise AI platform", "asset_type": "public_company",
        "description": "Revolutionary AI-powered quantum-enhanced blockchain platform "
                       "poised to disrupt the trillion-dollar enterprise market with "
                       "game-changing, industry-leading, next-generation synergies. "
                       "Unlimited potential in a massive opportunity.",
        "market_cap": 720e6, "revenue": 3.1e6, "revenue_prior": 4.4e6,
        "gross_margin": 0.12, "gross_margin_prior": 0.44,
        "cash": 9e6, "debt": 55e6, "fcf": -41e6,
        "shares": 480e6, "shares_prior": 210e6, "sbc": 22e6,
        "tam": 3e9, "insider_own": 0.03, "largest_customer": 0.67,
        "signals": {},
        "hype": "extreme",
        "flags": {"going_concern": True, "restatements": 1, "investigations": 1,
                  "insider_selling": 0.94, "departures": 4, "auditor_changes": 2,
                  "missed_milestones": 5, "related_party": True, "lawsuits": 3},
    },
    {
        "name": "Helios Fusion Ventures", "ticker": "HLFV", "sector": "Energy",
        "industry": "Fusion", "asset_type": "public_company",
        "description": "Developing a compact fusion device. No peer-reviewed results. "
                       "Timeline has slipped in each of the last four annual reports.",
        "market_cap": 3.2e9, "revenue": 0.0, "revenue_prior": 0.0,
        "gross_margin": None, "gross_margin_prior": None,
        "cash": 120e6, "debt": 10e6, "fcf": -180e6,
        "shares": 290e6, "shares_prior": 205e6, "sbc": 35e6,
        "tam": 200e9, "insider_own": 0.08, "largest_customer": None,
        "signals": {"hiring": "steady"},
        "hype": "high",
        "flags": {"missed_milestones": 4, "insider_selling": 0.81},
    },
]


def _seeded_rng(key: str) -> random.Random:
    """Deterministic RNG per key, so mock output is stable across runs."""
    return random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:12], 16))


def make_series(
    company: str, metric: str, pattern: str, periods: int = 18, end: date | None = None
) -> list[tuple[date, float]]:
    """Generate a monthly series with a stated behaviour.

    ``accelerating`` bends upward late in the window, which is what the signal
    detector is built to notice; ``steady`` grows dully; ``declining`` fades.
    """
    rng = _seeded_rng(f"{company}:{metric}:{pattern}")
    end = end or date.today()
    base = rng.uniform(20, 120)
    out: list[tuple[date, float]] = []
    for i in range(periods):
        t = i / max(1, periods - 1)
        if pattern == "accelerating":
            # Flat, then a pronounced upward bend in the final third.
            factor = 1.0 + 0.15 * t + (2.9 * max(0.0, t - 0.62) ** 1.7)
        elif pattern == "declining":
            factor = 1.0 - 0.45 * t
        else:
            factor = 1.0 + 0.28 * t
        noise = rng.uniform(0.93, 1.07)
        when = end - timedelta(days=30 * (periods - 1 - i))
        out.append((when, max(0.0, base * factor * noise)))
    return out


class MockSource(Source):
    """A source that serves the synthetic corpus."""

    name = "mock:synthetic-corpus"
    source_type = "mock"
    url = "internal://synthetic"
    tier = SourceTier.SOCIAL   # never citable as evidence
    rate_limit_per_hour = 0    # no external calls, so no limiting needed

    def fetch(self, query: str, *, limit: int = 25, as_of: date | None = None) -> list[dict[str, Any]]:
        q = (query or "").lower()
        hits = []
        for c in SYNTHETIC_COMPANIES:
            haystack = f"{c['name']} {c['sector']} {c['industry']} {c['description']}".lower()
            if not q or any(tok in haystack for tok in q.split() if len(tok) > 2):
                hits.append(c)
        return hits[:limit]

    def parse(self, payload: dict[str, Any]) -> RawDoc | None:
        published = date.today() - timedelta(days=_seeded_rng(payload["name"]).randint(3, 120))
        return RawDoc(
            external_id=f"mock-{payload['ticker']}",
            title=f"{payload['name']} ({payload['ticker']})",
            body=payload["description"],
            url=None,
            published_at=published,
            entities=[payload["name"]],
            metrics={"market_cap": payload["market_cap"], "revenue": payload["revenue"]},
            raw={**payload, "synthetic": True},
        )
