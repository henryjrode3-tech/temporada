"""Evidence grading and price-provider honesty.

The governing property: a report can never look better sourced than it is, and
a missing price is never replaced by a plausible one.
"""

from __future__ import annotations

from datetime import date

import pytest

from asymmetry.core.evidence import (
    Citation,
    Claim,
    EvidenceLedger,
    Grade,
)
from asymmetry.sources.prices import (
    ManualPriceProvider,
    PriceQuote,
    PriceUnavailable,
    TiingoPriceProvider,
    UnavailablePriceProvider,
    get_price_provider,
)

CITE = Citation(source="SEC EDGAR 10-K", filed=date(2025, 2, 1),
                period_end=date(2024, 12, 31), accession="0000-24-1")


class TestGrades:
    def test_ordered_by_reliability(self):
        assert Grade.FACT < Grade.DERIVED < Grade.ESTIMATE < Grade.ASSUMPTION
        assert Grade.ASSUMPTION < Grade.AI_INTERPRETATION

    def test_only_facts_and_derived_count_as_evidence(self):
        assert Grade.FACT.is_evidence and Grade.DERIVED.is_evidence
        assert not Grade.ESTIMATE.is_evidence
        assert not Grade.ASSUMPTION.is_evidence
        assert not Grade.AI_INTERPRETATION.is_evidence


class TestClaim:
    def test_a_fact_must_be_cited(self):
        """An uncited fact is an assumption wearing a better name."""
        with pytest.raises(ValueError, match="no citation"):
            Claim("Revenue", 100.0, Grade.FACT)

    def test_assumptions_need_no_citation(self):
        Claim("Assumed margin", 0.2, Grade.ASSUMPTION)   # must not raise

    def test_derive_inherits_the_weakest_input(self):
        """The rule that stops a sourced-looking number resting on an invented one."""
        fact = Claim("Revenue", 100.0, Grade.FACT, citations=[CITE])
        assumption = Claim("Market size", 5000.0, Grade.ASSUMPTION)
        derived = Claim.derive("Implied share", 0.02, [fact, assumption])
        assert derived.grade is Grade.ASSUMPTION
        assert not derived.is_evidence

    def test_derive_from_facts_alone_is_derived(self):
        a = Claim("Revenue", 100.0, Grade.FACT, citations=[CITE])
        b = Claim("Cost", 60.0, Grade.FACT, citations=[CITE])
        assert Claim.derive("Gross profit", 40.0, [a, b]).grade is Grade.DERIVED

    def test_derive_never_upgrades_to_fact(self):
        a = Claim("Revenue", 100.0, Grade.FACT, citations=[CITE])
        assert Claim.derive("Doubled", 200.0, [a]).grade is not Grade.FACT

    def test_derive_carries_citations_forward(self):
        a = Claim("Revenue", 100.0, Grade.FACT, citations=[CITE])
        assert Claim.derive("x2", 200.0, [a]).citations == [CITE]

    def test_derive_records_its_inputs(self):
        a = Claim("Revenue", 100.0, Grade.FACT, citations=[CITE])
        b = Claim("Shares", 10.0, Grade.FACT, citations=[CITE])
        assert set(Claim.derive("Per share", 10.0, [a, b]).depends_on) == {"Revenue", "Shares"}

    def test_derive_takes_the_lowest_confidence(self):
        a = Claim("A", 1.0, Grade.ASSUMPTION, confidence=0.8)
        b = Claim("B", 2.0, Grade.ASSUMPTION, confidence=0.2)
        assert Claim.derive("C", 3.0, [a, b]).confidence == 0.2

    def test_value_rendering(self):
        assert "$1.50B" in Claim("x", 1.5e9, Grade.ASSUMPTION, unit="USD").render_value()
        assert Claim("x", 0.153, Grade.ASSUMPTION, unit="%").render_value() == "15.3%"
        assert Claim("x", 12.5, Grade.ASSUMPTION, unit="x").render_value() == "12.50x"

    def test_negative_money(self):
        assert Claim("x", -5e8, Grade.ASSUMPTION, unit="USD").render_value().startswith("-$")

    def test_serialises_with_grade(self):
        d = Claim("Revenue", 100.0, Grade.FACT, citations=[CITE]).to_dict()
        assert d["grade"] == "FACT" and d["is_evidence"] and d["citations"]


class TestLedger:
    def _ledger(self) -> EvidenceLedger:
        led = EvidenceLedger()
        led.add(Claim("Revenue", 100.0, Grade.FACT, citations=[CITE]))
        led.add(Claim("Net income", 10.0, Grade.FACT, citations=[CITE]))
        led.add(Claim("Margin", 0.1, Grade.DERIVED, citations=[CITE]))
        led.add(Claim("Market size", 9e9, Grade.ASSUMPTION))
        return led

    def test_evidence_ratio(self):
        assert self._ledger().evidence_ratio == pytest.approx(0.75)

    def test_empty_ledger_has_no_evidence(self):
        assert EvidenceLedger().evidence_ratio == 0.0

    def test_counts_by_grade(self):
        counts = self._ledger().counts()
        assert counts["FACT"] == 2 and counts["ASSUMPTION"] == 1

    def test_warns_when_mostly_assumption(self):
        led = EvidenceLedger()
        for i in range(5):
            led.add(Claim(f"a{i}", 1.0, Grade.ASSUMPTION))
        led.add(Claim("Revenue", 1.0, Grade.FACT, citations=[CITE]))
        warnings = " ".join(led.integrity_warnings())
        assert "mostly assumption" in warnings
        assert "outnumber facts" in warnings

    def test_clean_ledger_has_no_warnings(self):
        assert self._ledger().integrity_warnings() == []

    def test_warns_on_uncited_derived_claim(self):
        led = EvidenceLedger()
        led.add(Claim("Sneaky", 1.0, Grade.DERIVED))
        assert any("lacking citations" in w for w in led.integrity_warnings())

    def test_collects_distinct_sources(self):
        assert len(self._ledger().cited_sources) == 1


class TestPriceProviders:
    def test_default_provider_refuses_to_guess(self):
        """A mock returning plausible prices would let the whole pipeline run
        on invented valuations - the exact failure this platform detects."""
        provider = UnavailablePriceProvider()
        assert not provider.available
        with pytest.raises(PriceUnavailable, match="No price provider is configured"):
            provider.get_price("AAPL")

    def test_default_error_says_what_still_works(self):
        with pytest.raises(PriceUnavailable, match="Fundamentals from SEC EDGAR are"):
            UnavailablePriceProvider().get_price("AAPL")

    def test_manual_provider_returns_what_was_supplied(self):
        quote = ManualPriceProvider({"AAPL": 190.0}).get_price("aapl")
        assert quote.price == 190.0 and "manual" in quote.source

    def test_manual_provider_rejects_unknown_ticker(self):
        with pytest.raises(PriceUnavailable, match="No manual price"):
            ManualPriceProvider({"AAPL": 190.0}).get_price("MSFT")

    def test_manual_provider_refuses_historical_dates(self):
        """Pricing 2015 at today's quote would make any backtest meaningless."""
        with pytest.raises(PriceUnavailable, match="historical"):
            ManualPriceProvider({"AAPL": 190.0}).get_price("AAPL", on=date(2015, 1, 1))

    def test_manual_provider_rejects_nonpositive_price(self):
        with pytest.raises(ValueError):
            ManualPriceProvider().set("AAPL", 0)

    def test_tiingo_unavailable_without_a_key(self, monkeypatch):
        monkeypatch.delenv("TIINGO_API_KEY", raising=False)
        provider = TiingoPriceProvider()
        assert not provider.available
        with pytest.raises(PriceUnavailable, match="TIINGO_API_KEY"):
            provider.get_price("AAPL")

    def test_factory_defaults_to_unavailable(self, monkeypatch):
        monkeypatch.delenv("ASYMMETRY_PRICE_PROVIDER", raising=False)
        assert isinstance(get_price_provider(), UnavailablePriceProvider)

    def test_unknown_provider_falls_back_safely(self):
        assert isinstance(get_price_provider("nonsense"), UnavailablePriceProvider)

    def test_market_cap_arithmetic(self):
        quote = PriceQuote("AAPL", 100.0, date(2025, 1, 1))
        assert quote.market_cap(1e9) == pytest.approx(1e11)

    def test_market_cap_rejects_zero_shares(self):
        with pytest.raises(ValueError):
            PriceQuote("AAPL", 100.0, date(2025, 1, 1)).market_cap(0)
