"""SEC EDGAR ingestion tests.

Run against a trimmed copy of Apple's real companyfacts document, so they
exercise genuine SEC structure - multiple tags per concept, quarterly rows
inside 10-K filings, stock splits, restatements - without touching the network.

Each of the three bugs pinned here was found on real data and would have
silently corrupted every downstream number.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from asymmetry.sources.edgar import (
    CONCEPTS,
    SPLIT_MIN_JUMP,
    XBRLFact,
    cagr_from_series,
    detect_splits,
    dilution_rate,
    growth_rate,
    parse_company_facts,
    split_adjusted_values,
)

FIXTURE = Path(__file__).parent / "fixtures" / "companyfacts_aapl.json"

needs_network = pytest.mark.skipif(
    __import__("os").environ.get("ASYMMETRY_TEST_NETWORK") != "1",
    reason="set ASYMMETRY_TEST_NETWORK=1 for live SEC tests",
)


@pytest.fixture(scope="module")
def facts() -> list[XBRLFact]:
    return parse_company_facts(json.loads(FIXTURE.read_text()))


class TestParsing:
    def test_parses_real_structure(self, facts):
        assert len(facts) > 500
        assert {"revenue", "net_income", "cash", "shares_outstanding"} <= {
            f.concept for f in facts
        }

    def test_every_fact_has_a_filed_date(self, facts):
        """Undated facts must never enter: they defeat point-in-time entirely."""
        assert all(f.filed is not None for f in facts)

    def test_every_fact_cites_a_filing(self, facts):
        assert all(f.accession for f in facts)
        assert all(f.source_url.startswith("https://www.sec.gov/") for f in facts)

    def test_one_tag_per_concept(self, facts):
        """Mixing tags across periods fabricates step changes in the series."""
        for concept in {f.concept for f in facts}:
            tags = {f.tag for f in facts if f.concept == concept}
            assert len(tags) == 1, f"{concept} mixed tags: {tags}"

    def test_only_statement_forms(self, facts):
        assert all(f.form.startswith(("10-K", "10-Q", "20-F", "40-F")) for f in facts)

    def test_empty_document_is_handled(self):
        assert parse_company_facts({}) == []
        assert parse_company_facts({"facts": {}}) == []


class TestAnnualDetection:
    """Bug 1: a 10-K contains both full-year and Q4 rows."""

    def test_quarterly_rows_in_a_10k_are_not_annual(self, facts):
        rev = [f for f in facts if f.concept == "revenue"]
        quarterly_in_10k = [f for f in rev if f.form == "10-K" and (f.duration_days or 0) < 200]
        assert quarterly_in_10k, "fixture should contain quarterly rows inside 10-Ks"
        assert all(not f.is_annual for f in quarterly_in_10k)

    def test_annual_revenue_is_the_full_year(self, facts):
        """Apple FY2020 revenue is $274.5B. The Q4 figure is $64.7B."""
        from asymmetry.sources.edgar import CompanyIdentity, FinancialHistory

        history = FinancialHistory(CompanyIdentity(320193, "AAPL", "Apple Inc."), facts)
        fy2020 = history.latest("revenue", as_of=date(2021, 1, 1), annual=True)
        assert fy2020 is not None
        assert 270e9 < fy2020.value < 280e9, f"got {fy2020.value/1e9:.1f}B"

    def test_instants_follow_the_form(self, facts):
        """Balance-sheet items have no duration; a year-end balance is annual."""
        cash = [f for f in facts if f.concept == "cash" and f.is_instant]
        assert cash
        assert any(f.is_annual for f in cash if f.form.startswith("10-K"))


class TestTagSelection:
    """Bugs 2 and 3: choosing which tag to trust."""

    def test_prefers_a_tag_with_annual_data(self):
        """A top-priority tag carrying only quarterly rows must not win."""
        raw = {"facts": {"us-gaap": {
            # Highest priority, quarterly only.
            "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
                {"end": "2024-03-31", "start": "2024-01-01", "val": 25,
                 "filed": "2024-05-01", "form": "10-Q", "accn": "a"},
            ]}},
            # Lower priority, but has the annual figure.
            "Revenues": {"units": {"USD": [
                {"end": "2024-12-31", "start": "2024-01-01", "val": 100,
                 "filed": "2025-02-01", "form": "10-K", "accn": "b"},
            ]}},
        }}}
        parsed = parse_company_facts(raw)
        revenue = [f for f in parsed if f.concept == "revenue"]
        assert {f.tag for f in revenue} == {"Revenues"}
        assert revenue[0].value == 100

    def test_prefers_the_current_tag_over_a_longer_dead_one(self):
        """A tag abandoned years ago cannot describe the company now."""
        legacy = [
            {"end": f"{y}-12-31", "start": f"{y}-01-01", "val": 10,
             "filed": f"{y+1}-02-01", "form": "10-K", "accn": f"old{y}"}
            for y in range(2010, 2018)
        ]
        modern = [
            {"end": f"{y}-12-31", "start": f"{y}-01-01", "val": 99,
             "filed": f"{y+1}-02-01", "form": "10-K", "accn": f"new{y}"}
            for y in range(2022, 2026)
        ]
        raw = {"facts": {"us-gaap": {
            "SalesRevenueNet": {"units": {"USD": legacy}},
            "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": modern}},
        }}}
        revenue = [f for f in parse_company_facts(raw) if f.concept == "revenue"]
        assert {f.tag for f in revenue} == {
            "RevenueFromContractWithCustomerExcludingAssessedTax"
        }
        assert max(f.period_end for f in revenue).year == 2025


class TestPointInTime:
    """The property the whole module exists to provide."""

    @pytest.fixture()
    def history(self, facts):
        from asymmetry.sources.edgar import CompanyIdentity, FinancialHistory

        return FinancialHistory(CompanyIdentity(320193, "AAPL", "Apple Inc."), facts)

    def test_filters_on_filed_not_period_end(self, history):
        cutoff = date(2021, 1, 1)
        visible = history.visible_as_of(cutoff)
        assert visible
        assert all(f.filed <= cutoff for f in visible)

    def test_a_period_filed_after_the_cutoff_is_invisible(self, history):
        """FY2020 ended in Sept 2020 but a cutoff before its filing must hide it."""
        rev = history.series("revenue", annual=True)
        fy = next(f for f in rev if f.period_end.year == 2020)
        just_before = date.fromordinal(fy.filed.toordinal() - 1)
        assert fy.period_end < just_before        # period had already ended
        visible = history.series("revenue", as_of=just_before, annual=True)
        assert all(f.period_end.year != 2020 for f in visible)

    def test_later_cutoffs_reveal_more(self, history):
        early = len(history.visible_as_of(date(2015, 1, 1)))
        late = len(history.visible_as_of(date(2024, 1, 1)))
        assert late > early

    def test_no_cutoff_sees_everything(self, history, facts):
        assert len(history.visible_as_of(None)) == len(facts)

    def test_series_keeps_the_original_not_the_restatement(self, history):
        """Ties on period are broken by earliest filing - what was known then."""
        series = history.series("revenue", annual=True)
        periods = [f.period_end for f in series]
        assert len(periods) == len(set(periods)), "one entry per period"


class TestSplits:
    """Splits are not dilution, and confusing them wrecks every per-share number."""

    def _series(self, values: list[tuple[str, float]]) -> list[XBRLFact]:
        return [
            XBRLFact("shares_outstanding", "CommonStockSharesOutstanding", v, "shares",
                     date.fromisoformat(d), date.fromisoformat(d), "10-K", "x")
            for d, v in values
        ]

    def test_detects_a_split_blurred_by_buybacks(self):
        """Apple's 7-for-1 shows as 6.52x because it bought back stock that year."""
        s = self._series([("2013-09-28", 899e6), ("2014-09-27", 5866e6)])
        splits = detect_splits(s)
        assert len(splits) == 1 and splits[0].matched == 7.0

    def test_ordinary_drift_is_never_a_split(self):
        s = self._series([("2023-01-01", 100e6), ("2024-01-01", 108e6)])
        assert detect_splits(s) == []

    def test_a_fifty_percent_raise_is_dilution_not_a_split(self):
        """1.5x is excluded deliberately: for small caps it is nearly always issuance."""
        s = self._series([("2023-01-01", 100e6), ("2024-01-01", 150e6)])
        assert detect_splits(s) == []

    def test_split_adjustment_restates_history(self):
        s = self._series([("2013-01-01", 100e6), ("2014-01-01", 400e6),
                          ("2015-01-01", 400e6)])
        values, splits = split_adjusted_values(s)
        assert len(splits) == 1
        assert values[0][1] == pytest.approx(400e6)   # pre-split scaled up

    def test_buybacks_show_as_negative_dilution(self):
        s = self._series([("2020-01-01", 100e6), ("2021-01-01", 97e6),
                          ("2022-01-01", 94e6), ("2023-01-01", 91e6)])
        est = dilution_rate(s)
        assert est.best_estimate is not None and est.best_estimate < 0

    def test_serial_dilution_is_reported_fully(self):
        s = self._series([("2020-01-01", 100e6), ("2021-01-01", 130e6),
                          ("2022-01-01", 165e6), ("2023-01-01", 210e6)])
        est = dilution_rate(s)
        assert est.best_estimate > 0.25

    def test_ambiguous_split_uses_the_conservative_reading(self):
        """When a jump could be a split or a raise, assume the worse case."""
        s = self._series([("2020-01-01", 100e6), ("2021-01-01", 230e6),
                          ("2022-01-01", 240e6)])
        est = dilution_rate(s)
        if est.splits:
            assert est.has_ambiguous_split
            assert est.best_estimate == est.conservative
            assert "conservative" in est.note()

    def test_reports_both_readings(self):
        s = self._series([("2020-01-01", 100e6), ("2021-01-01", 400e6),
                          ("2022-01-01", 400e6)])
        est = dilution_rate(s)
        assert est.raw is not None and est.adjusted is not None
        assert est.raw > est.adjusted    # unadjusted looks like huge dilution

    def test_too_few_periods(self):
        est = dilution_rate(self._series([("2024-01-01", 100e6)]))
        assert est.best_estimate is None


class TestDerivedMetrics:
    def test_growth_rate(self):
        s = [
            XBRLFact("revenue", "R", 100, "USD", date(2023, 12, 31), date(2024, 2, 1), "10-K", "a"),
            XBRLFact("revenue", "R", 150, "USD", date(2024, 12, 31), date(2025, 2, 1), "10-K", "b"),
        ]
        assert growth_rate(s) == pytest.approx(0.5)

    def test_growth_needs_two_points(self):
        assert growth_rate([]) is None

    def test_growth_from_zero_base_is_undefined(self):
        s = [
            XBRLFact("revenue", "R", 0, "USD", date(2023, 12, 31), date(2024, 2, 1), "10-K", "a"),
            XBRLFact("revenue", "R", 150, "USD", date(2024, 12, 31), date(2025, 2, 1), "10-K", "b"),
        ]
        assert growth_rate(s) is None

    def test_cagr(self):
        s = [
            XBRLFact("revenue", "R", 100, "USD", date(2020, 12, 31), date(2021, 2, 1), "10-K", "a"),
            XBRLFact("revenue", "R", 200, "USD", date(2024, 12, 31), date(2025, 2, 1), "10-K", "b"),
        ]
        assert cagr_from_series(s) == pytest.approx(0.1892, abs=1e-3)

    def test_free_cash_flow_is_derived_with_both_inputs(self, facts):
        from asymmetry.sources.edgar import CompanyIdentity, FinancialHistory

        h = FinancialHistory(CompanyIdentity(320193, "AAPL", "Apple Inc."), facts)
        result = h.derived_free_cash_flow()
        if result:
            value, ocf, capex = result
            assert value == pytest.approx(ocf.value - abs(capex.value))


@needs_network
class TestLiveSEC:
    def test_resolves_a_real_ticker(self):
        from asymmetry.sources.edgar import EdgarClient

        identity = EdgarClient().resolve_ticker("AAPL")
        assert identity.cik == 320193 and "Apple" in identity.name

    def test_unknown_ticker_is_explained(self):
        from asymmetry.sources.edgar import EdgarClient, TickerNotFound

        with pytest.raises(TickerNotFound, match="not in the SEC"):
            EdgarClient().resolve_ticker("ZZZZQQ")
