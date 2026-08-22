"""Tests for the financial mathematics.

These are the numbers the whole platform rests on, so they are pinned against
the worked examples in the specification.
"""

from __future__ import annotations

import math

import pytest

from asymmetry.core.finmath import (
    FinMathError,
    asymmetry_from_payoff,
    burn_runway_years,
    cagr,
    dilute,
    enterprise_value,
    implied_dilution_cagr,
    implied_requirements,
    multiple,
    multiple_from_cagr,
    revenue_from_market,
    rule_of_40,
    safe_ratio,
    value_from_earnings,
    value_from_revenue,
    weighted_outcome,
    years_to_reach,
)


class TestCagr:
    @pytest.mark.parametrize(
        "mult,years,expected_pct",
        [(5, 10, 17.5), (10, 10, 25.9), (50, 10, 47.9), (100, 10, 58.5)],
    )
    def test_matches_specification_examples(self, mult, years, expected_pct):
        assert round(cagr(mult, years) * 100, 1) == expected_pct

    def test_flat_is_zero(self):
        assert cagr(1.0, 10) == pytest.approx(0.0)

    def test_total_loss(self):
        assert cagr(0.0, 10) == -1.0

    def test_halving(self):
        assert cagr(0.5, 10) == pytest.approx(-0.0670, abs=1e-4)

    def test_round_trip_with_multiple_from_cagr(self):
        for m in (2.0, 7.5, 33.0):
            assert multiple_from_cagr(cagr(m, 10), 10) == pytest.approx(m)

    def test_rejects_bad_input(self):
        with pytest.raises(FinMathError):
            cagr(5, 0)
        with pytest.raises(FinMathError):
            cagr(-1, 10)

    def test_years_to_reach_inverts(self):
        assert years_to_reach(10, cagr(10, 10)) == pytest.approx(10.0)


class TestMultiple:
    def test_basic(self):
        assert multiple(80e9, 500e6) == pytest.approx(160.0)

    def test_rejects_zero_base(self):
        with pytest.raises(FinMathError):
            multiple(100, 0)

    def test_rejects_negative_future(self):
        with pytest.raises(FinMathError):
            multiple(-1, 100)


class TestDilution:
    def test_specification_example(self):
        # 10x market cap, 12% annual share growth, 10 years.
        assert dilute(10, 0.12, 10) == pytest.approx(3.22, abs=0.01)

    def test_no_dilution_is_identity(self):
        assert dilute(10, 0.0, 10) == 10.0

    def test_dilution_always_reduces_holder_return(self):
        assert dilute(10, 0.08, 10) < 10.0

    def test_buybacks_increase_holder_return(self):
        assert dilute(10, -0.02, 10) > 10.0

    def test_implied_dilution_round_trip(self):
        rate = implied_dilution_cagr(100e6, 200e6, 10)
        assert rate == pytest.approx(0.0718, abs=1e-3)
        assert dilute(10, rate, 10) == pytest.approx(5.0, abs=0.01)


class TestBottomUpValuation:
    def test_specification_worked_example(self):
        """$200B market, 10% share, 20% net margin, 20x earnings -> $80B."""
        revenue = revenue_from_market(200e9, 0.10)
        assert revenue == pytest.approx(20e9)
        value = value_from_earnings(revenue, 0.20, 20)
        assert value == pytest.approx(80e9)
        assert multiple(value, 500e6) == pytest.approx(160.0)

    def test_revenue_path(self):
        assert value_from_revenue(1e9, 8) == pytest.approx(8e9)

    def test_share_must_be_a_fraction(self):
        with pytest.raises(FinMathError):
            revenue_from_market(100, 1.5)

    def test_negative_margin_floors_at_zero(self):
        assert value_from_earnings(1e9, -0.2, 20) == 0.0


class TestReverseValuation:
    def test_demanding_price_is_flagged(self):
        """A $40B cap needing most of a $60B market should read as demanding."""
        req = implied_requirements(
            40e9, total_market=60e9, net_margin=0.20, exit_multiple=25,
            years=10, required_return=0.15,
        )
        assert req.required_market_share > 0.30
        assert req.share_is_implausible
        assert "already assumes" in req.verdict or "more than the market" in req.verdict

    def test_modest_price_is_not_flagged(self):
        req = implied_requirements(
            300e6, total_market=200e9, net_margin=0.15, exit_multiple=20,
            years=10, required_return=0.15,
        )
        assert req.required_market_share < 0.02
        assert not req.share_is_implausible

    def test_impossible_price_detected(self):
        req = implied_requirements(
            500e9, total_market=10e9, net_margin=0.10, exit_multiple=15,
            years=10, required_return=0.15,
        )
        assert req.required_market_share > 1.0
        assert "more than the market contains" in req.verdict

    def test_unknown_market_is_honest(self):
        req = implied_requirements(
            1e9, total_market=None, net_margin=0.15, exit_multiple=20, years=10,
        )
        assert req.required_market_share is None
        assert "unknown" in req.verdict.lower()

    def test_higher_required_return_demands_more(self):
        low = implied_requirements(1e9, total_market=100e9, net_margin=0.15,
                                   exit_multiple=20, years=10, required_return=0.10)
        high = implied_requirements(1e9, total_market=100e9, net_margin=0.15,
                                    exit_multiple=20, years=10, required_return=0.25)
        assert high.required_market_share > low.required_market_share


class TestWeightedOutcome:
    def test_expected_value_arithmetic(self):
        pairs = [(0.40, 20e6), (0.35, 300e6), (0.20, 2e9), (0.05, 10e9)]
        out = weighted_outcome(pairs, current_value=100e6)
        expected = 0.40 * 20e6 + 0.35 * 300e6 + 0.20 * 2e9 + 0.05 * 10e9
        assert out.expected_value == pytest.approx(expected)
        assert out.expected_multiple == pytest.approx(expected / 100e6)

    def test_probability_of_loss_and_10x(self):
        pairs = [(0.40, 20e6), (0.35, 300e6), (0.20, 2e9), (0.05, 10e9)]
        out = weighted_outcome(pairs, current_value=100e6)
        assert out.probability_of_loss == pytest.approx(0.40)
        assert out.probability_of_10x == pytest.approx(0.25)

    def test_payoff_ratio_favours_lopsided_bets(self):
        lopsided = weighted_outcome([(0.8, 0.5e6), (0.2, 50e6)], 1e6)
        symmetric = weighted_outcome([(0.5, 0.5e6), (0.5, 1.5e6)], 1e6)
        assert lopsided.payoff_ratio > symmetric.payoff_ratio

    def test_probabilities_must_sum_to_one(self):
        with pytest.raises(FinMathError, match="sum to 1.0"):
            weighted_outcome([(0.5, 1e6), (0.3, 2e6)], 1e6)

    def test_rejects_negative_probability(self):
        with pytest.raises(FinMathError):
            weighted_outcome([(-0.1, 1e6), (1.1, 2e6)], 1e6)


class TestAsymmetryScore:
    def test_bounded(self):
        for r in (0.0, 0.5, 1.0, 10.0, 1000.0):
            assert 0.0 <= asymmetry_from_payoff(r) <= 100.0

    def test_monotonic(self):
        scores = [asymmetry_from_payoff(r) for r in (0.5, 1, 3, 10, 40)]
        assert scores == sorted(scores)

    def test_zero_payoff_scores_zero(self):
        assert asymmetry_from_payoff(0.0) == 0.0

    def test_symmetric_bet_scores_low(self):
        """A 1:1 payoff is not asymmetric, so it must not score well.

        The score measures lopsidedness, not attractiveness. An even-money bet
        scoring highly here would defeat the purpose of the metric.
        """
        assert asymmetry_from_payoff(1.0) < 25

    def test_calibration_of_decision_thresholds(self):
        """Pin the ratios behind the verdict thresholds in scoring.py.

        A change to the compression curve silently moves every verdict boundary,
        so the mapping is asserted rather than left implicit. These figures are
        for ASYMMETRY_SCALE_CAP = 200, chosen because a cap of 50 saturated
        every small company at 100 and destroyed the score's ability to rank.
        """
        assert asymmetry_from_payoff(3.0) == pytest.approx(26.1, abs=1.0)
        assert asymmetry_from_payoff(10.0) == pytest.approx(45.2, abs=1.0)
        assert asymmetry_from_payoff(20.0) == pytest.approx(57.4, abs=1.0)
        assert asymmetry_from_payoff(50.0) == pytest.approx(74.1, abs=1.0)
        assert asymmetry_from_payoff(200.0) == pytest.approx(100.0, abs=0.5)

    def test_scale_cap_is_the_documented_one(self):
        """Guards against the cap drifting without the calibration being revisited."""
        from asymmetry.core.finmath import ASYMMETRY_SCALE_CAP

        assert ASYMMETRY_SCALE_CAP == 200.0


class TestRatios:
    def test_enterprise_value(self):
        assert enterprise_value(1e9, 200e6, 500e6) == pytest.approx(700e6)

    def test_negative_ev_is_allowed(self):
        assert enterprise_value(100e6, 0, 300e6) == pytest.approx(-200e6)

    def test_safe_ratio_refuses_meaningless_pe(self):
        assert safe_ratio(100, 0) is None
        assert safe_ratio(100, -50) is None
        assert safe_ratio(None, 10) is None

    def test_safe_ratio_normal(self):
        assert safe_ratio(100, 4) == pytest.approx(25.0)

    def test_rule_of_40(self):
        assert rule_of_40(0.35, 0.10) == pytest.approx(45.0)

    def test_runway(self):
        assert burn_runway_years(100e6, -50e6) == pytest.approx(2.0)
        assert burn_runway_years(100e6, 10e6) is None
        assert burn_runway_years(0, -50e6) == 0.0
