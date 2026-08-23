"""End-to-end research report assembly.

Uses the real SEC fixture through a stubbed client, so the whole path from
filings to graded report runs without network.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from asymmetry.core.evidence import Grade
from asymmetry.research.company import CompanyResearcher, _sector_key
from asymmetry.sources.edgar import (
    CompanyIdentity,
    FinancialHistory,
    parse_company_facts,
)
from asymmetry.sources.prices import ManualPriceProvider, UnavailablePriceProvider

FIXTURE = Path(__file__).parent / "fixtures" / "companyfacts_aapl.json"


class StubEdgar:
    """Serves the fixture instead of calling the SEC."""

    def __init__(self) -> None:
        self._facts = parse_company_facts(json.loads(FIXTURE.read_text()))

    def fetch_history(self, ticker: str, **_: object) -> FinancialHistory:
        return FinancialHistory(
            identity=CompanyIdentity(
                cik=320193, ticker=ticker.upper(), name="Apple Inc.",
                sic_description="Electronic Computers",
            ),
            facts=self._facts,
        )


@pytest.fixture()
def researcher_with_price():
    return CompanyResearcher(
        edgar=StubEdgar(), prices=ManualPriceProvider({"AAPL": 200.0})
    )


@pytest.fixture()
def researcher_no_price():
    return CompanyResearcher(edgar=StubEdgar(), prices=UnavailablePriceProvider())


class TestReportWithPrice:
    def test_produces_a_full_report(self, researcher_with_price):
        r = researcher_with_price.research("AAPL")
        assert r.company_name == "Apple Inc." and r.cik == 320193
        assert r.scenarios is not None
        assert r.reverse_valuation is not None
        assert r.milestones

    def test_facts_are_sourced(self, researcher_with_price):
        r = researcher_with_price.research("AAPL")
        for claim in r.ledger.claims:
            if claim.grade is Grade.FACT:
                assert claim.citations, f"{claim.label} is a FACT with no citation"

    def test_contains_every_requested_element(self, researcher_with_price):
        r = researcher_with_price.research("AAPL")
        labels = {c.label for c in r.ledger.claims}
        for expected in ("Revenue (latest annual)", "Revenue growth (YoY)",
                         "Free cash flow", "Shares outstanding", "Annual dilution",
                         "Market capitalisation", "Addressable market"):
            assert expected in labels, f"missing {expected}"
        assert r.financial_history.get("revenue")
        assert r.key_assumptions and r.invalidators
        assert "probability_of_loss" in r.scenarios
        assert "median_multiple" in r.scenarios

    def test_market_size_is_an_assumption_not_a_fact(self, researcher_with_price):
        """The weakest input in the report must be labelled as such."""
        claim = researcher_with_price.research("AAPL").ledger.get("Addressable market")
        assert claim.grade is Grade.ASSUMPTION
        assert not claim.is_evidence
        assert "weakest input" in claim.rationale

    def test_scenarios_carry_the_probability_caveat(self, researcher_with_price):
        note = researcher_with_price.research("AAPL").scenarios["probability_note"]
        assert "ASSUMPTION" in note and "not a measured distribution" in note

    def test_manual_price_is_an_estimate_not_a_fact(self, researcher_with_price):
        claim = researcher_with_price.research("AAPL").ledger.get("Share price")
        assert claim.grade is Grade.ESTIMATE

    def test_market_cap_inherits_the_price_grade(self, researcher_with_price):
        """A cap built on an operator-supplied price cannot outrank it."""
        cap = researcher_with_price.research("AAPL").ledger.get("Market capitalisation")
        assert cap.grade >= Grade.ESTIMATE

    def test_verdict_never_says_buy(self, researcher_with_price):
        r = researcher_with_price.research("AAPL")
        assert "BUY" not in r.verdict and "SELL" not in r.verdict
        assert r.verdict in {
            "WORTH_INVESTIGATING", "WATCH", "NOT_ASYMMETRIC",
            "REJECTED", "INSUFFICIENT_DATA",
        }

    def test_serialises(self, researcher_with_price):
        d = researcher_with_price.research("AAPL").to_dict()
        assert d["evidence"]["claims"] and d["what_would_invalidate"]
        assert "not investment advice" in d["disclaimer"].lower()


class TestDegradesWithoutPrice:
    """A partial report built on facts beats a complete one built on a guess."""

    def test_still_produces_fundamentals(self, researcher_no_price):
        r = researcher_no_price.research("AAPL")
        assert r.ledger.get("Revenue (latest annual)") is not None
        assert r.financial_history.get("revenue")

    def test_omits_valuation_rather_than_inventing_it(self, researcher_no_price):
        r = researcher_no_price.research("AAPL")
        assert r.ledger.get("Market capitalisation") is None
        assert r.scenarios is None
        assert r.verdict == "INSUFFICIENT_DATA"

    def test_says_why_it_is_missing(self, researcher_no_price):
        r = researcher_no_price.research("AAPL")
        assert any("price provider" in m for m in r.missing)


class TestPointInTimeReport:
    def test_historical_cutoff_changes_the_numbers(self, researcher_with_price):
        past = researcher_with_price.research("AAPL", as_of=date(2021, 1, 1))
        now = researcher_with_price.research("AAPL")
        old_rev = past.ledger.get("Revenue (latest annual)")
        new_rev = now.ledger.get("Revenue (latest annual)")
        assert old_rev.value != new_rev.value
        assert old_rev.as_of < new_rev.as_of

    def test_no_fact_postdates_the_cutoff(self, researcher_with_price):
        cutoff = date(2021, 1, 1)
        r = researcher_with_price.research("AAPL", as_of=cutoff)
        for claim in r.ledger.claims:
            for citation in claim.citations:
                if citation.filed:
                    assert citation.filed <= cutoff

    def test_history_series_respects_the_cutoff(self, researcher_with_price):
        cutoff = date(2021, 1, 1)
        r = researcher_with_price.research("AAPL", as_of=cutoff)
        for row in r.financial_history.get("revenue", []):
            assert date.fromisoformat(row["filed"]) <= cutoff


class TestSectorMapping:
    @pytest.mark.parametrize("desc,expected", [
        ("Services-Prepackaged Software", "software"),
        ("Semiconductors & Related Devices", "semiconductor"),
        ("Pharmaceutical Preparations", "pharma"),
        ("Electrical Industrial Apparatus", "industrial"),
        ("Crude Petroleum & Natural Gas", "energy"),
        ("Gold Mining", "mining"),
        (None, "default"),
        ("Something Unclassifiable", "default"),
    ])
    def test_maps_sic_descriptions(self, desc, expected):
        assert _sector_key(desc) == expected
