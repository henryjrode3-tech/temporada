"""Tests for scenarios, scoring, signals, hype and red flags."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from asymmetry.core.hype import analyse_hype
from asymmetry.core.redflags import FinancialSnapshot, Severity, detect_red_flags
from asymmetry.core.scenarios import (
    MAX_MARKET_SHARE,
    MAX_REVENUE_CAGR,
    ScenarioAssumptions,
    ScenarioName,
    build_scenario,
    build_scenario_set,
    default_scenarios,
    milestone_ladder,
)
from asymmetry.core.scoring import (
    DEFAULT_WEIGHTS,
    Dimension,
    DimensionScore,
    ScoringError,
    Verdict,
    assign_verdict,
    compute_composite,
    valuation_score_from_reverse,
)
from asymmetry.core.signals import (
    SignalStrength,
    SignalType,
    TimeSeriesPoint,
    aggregate_signal_score,
    detect_acceleration,
    robust_z_score,
)


# ==========================================================================
class TestScenarios:
    def test_worked_example(self):
        a = ScenarioAssumptions(
            name=ScenarioName.BULL, probability=0.2, total_market=200e9,
            market_share=0.10, net_margin=0.20, exit_multiple=20,
        )
        r = build_scenario(a, current_market_cap=500e6, years=10)
        assert r.revenue == pytest.approx(20e9)
        assert r.future_market_cap == pytest.approx(80e9)
        assert r.market_cap_multiple == pytest.approx(160.0)

    def test_probabilities_must_sum_to_one(self):
        bad = default_scenarios(10e9)
        bad[0].probability = 0.9
        with pytest.raises(Exception):
            build_scenario_set(bad, 100e6, 10)

    def test_dilution_reduces_holder_return(self):
        common = dict(name=ScenarioName.BASE, probability=1.0, total_market=10e9,
                      market_share=0.05, net_margin=0.15, exit_multiple=20)
        clean = build_scenario(ScenarioAssumptions(**common, dilution_cagr=0.0), 100e6, 10)
        diluted = build_scenario(ScenarioAssumptions(**common, dilution_cagr=0.10), 100e6, 10)
        assert diluted.per_share_multiple < clean.per_share_multiple
        assert diluted.market_cap_multiple == pytest.approx(clean.market_cap_multiple)

    def test_unprofitable_uses_revenue_path(self):
        a = ScenarioAssumptions(
            name=ScenarioName.BEAR, probability=1.0, total_market=1e9,
            market_share=0.01, net_margin=0.0, exit_multiple=0,
            ev_sales_multiple=2.0,
        )
        r = build_scenario(a, 50e6, 10)
        assert r.valuation_path == "revenue"
        assert r.future_market_cap == pytest.approx(10e6 * 2.0)


class TestPlausibilityClamps:
    """The constraints that keep bull cases inside observed reality."""

    def test_revenue_cagr_clamp_fires(self):
        # $5M revenue -> 20% of a $40B market implies ~190% CAGR for a decade.
        a = ScenarioAssumptions(
            name=ScenarioName.EXTREME_BULL, probability=1.0, total_market=40e9,
            market_share=0.20, net_margin=0.15, exit_multiple=20, current_revenue=5e6,
        )
        r = build_scenario(a, 80e6, 10)
        assert r.was_clamped
        assert "exceeds" in r.clamp_reason
        ceiling = MAX_REVENUE_CAGR[ScenarioName.EXTREME_BULL]
        assert r.revenue == pytest.approx(5e6 * (1 + ceiling) ** 10, rel=1e-6)

    def test_no_clamp_when_plausible(self):
        a = ScenarioAssumptions(
            name=ScenarioName.BASE, probability=1.0, total_market=10e9,
            market_share=0.02, net_margin=0.15, exit_multiple=20, current_revenue=90e6,
        )
        r = build_scenario(a, 600e6, 10)
        assert not r.was_clamped

    def test_market_share_ceiling_catches_what_cagr_misses(self):
        """A large company can pass the growth test while being handed its industry."""
        a = ScenarioAssumptions(
            name=ScenarioName.BULL, probability=1.0, total_market=100e9,
            market_share=0.80, net_margin=0.15, exit_multiple=20,
            current_revenue=30e9,   # 80% share is only ~10% CAGR from here
        )
        r = build_scenario(a, 50e9, 10)
        assert r.was_clamped
        assert "ceiling" in r.clamp_reason
        ceiling = MAX_MARKET_SHARE[ScenarioName.BULL]
        assert r.revenue == pytest.approx(100e9 * ceiling)

    def test_clamp_is_reported_not_silent(self):
        s = build_scenario_set(
            default_scenarios(40e9, current_revenue=5e6), 80e6, 10
        )
        assert s.clamped_scenarios
        assert any(r.clamp_reason for r in s.scenarios if r.was_clamped)

    def test_anchorless_scenarios_are_unconstrained(self):
        """Without a revenue anchor the CAGR clamp cannot apply - documents the risk."""
        a = ScenarioAssumptions(
            name=ScenarioName.EXTREME_BULL, probability=1.0, total_market=40e9,
            market_share=0.20, net_margin=0.15, exit_multiple=20, current_revenue=None,
        )
        r = build_scenario(a, 80e6, 10)
        assert r.implied_revenue_cagr is None


class TestScenarioSetSummary:
    def test_median_is_not_the_mean(self):
        s = build_scenario_set(default_scenarios(120e9, current_revenue=90e6), 600e6, 10)
        assert s.median_multiple < s.expected_multiple

    def test_tail_dominance_detected(self):
        s = build_scenario_set(default_scenarios(120e9, current_revenue=90e6), 600e6, 10)
        assert s.is_tail_dominated
        assert 0.0 <= s.tail_contribution <= 1.0

    def test_priced_for_perfection_scores_low(self):
        rich = build_scenario_set(default_scenarios(200e9, current_revenue=12e9), 60e9, 10)
        cheap = build_scenario_set(default_scenarios(120e9, current_revenue=90e6), 600e6, 10)
        assert rich.asymmetry_score < cheap.asymmetry_score
        assert rich.asymmetry_score < 30

    def test_asymmetry_discriminates_rather_than_saturating(self):
        """Every small company scoring 100 would make the metric useless."""
        scores = [
            build_scenario_set(default_scenarios(tam, current_revenue=rev), cap, 10).asymmetry_score
            for cap, tam, rev in [
                (80e6, 40e9, 5e6), (600e6, 120e9, 90e6),
                (8e9, 400e9, 2.5e9), (60e9, 200e9, 12e9),
            ]
        ]
        assert len(set(round(s) for s in scores)) == len(scores)
        assert max(scores) - min(scores) > 30


class TestMilestones:
    def test_impossible_milestone_marked_unreachable(self):
        ladder = milestone_ladder(500e6, total_market=5e9, net_margin=0.15,
                                  exit_multiple=20, years=10)
        trillion = [m for m in ladder if m.label == "$1T"][0]
        assert not trillion.reachable
        assert "larger than the market" in trillion.commentary

    def test_reachable_milestone_explains_requirement(self):
        ladder = milestone_ladder(500e6, total_market=200e9, net_margin=0.15,
                                  exit_multiple=20, years=10)
        ten = [m for m in ladder if m.label == "$10B"][0]
        assert ten.reachable
        assert "share of a" in ten.commentary


# ==========================================================================
class TestScoring:
    def _dims(self, value: float = 7.0) -> list[DimensionScore]:
        return [DimensionScore(d, value, "test", 0.8) for d in DEFAULT_WEIGHTS]

    def test_weights_sum_to_one(self):
        assert sum(DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)

    def test_uniform_scores_produce_that_score(self):
        c = compute_composite(self._dims(7.0))
        assert c.base_score == pytest.approx(70.0)

    def test_decomposition_is_retained(self):
        c = compute_composite(self._dims(6.0))
        assert c.components and c.weights and c.contributions
        assert sum(c.contributions.values()) == pytest.approx(c.base_score)

    def test_missing_dimensions_renormalise_not_zero(self):
        partial = [DimensionScore(Dimension.TECHNOLOGY, 8.0, "", 0.8),
                   DimensionScore(Dimension.MARKET, 8.0, "", 0.8)]
        c = compute_composite(partial)
        assert c.base_score == pytest.approx(80.0)   # not dragged down by absence
        assert len(c.missing_dimensions) == len(DEFAULT_WEIGHTS) - 2

    def test_penalty_is_itemised(self):
        c = compute_composite(self._dims(7.0), penalty=15.0, penalty_reasons=["Dilution"])
        assert c.base_score == pytest.approx(70.0)
        assert c.overall_score == pytest.approx(55.0)
        assert c.penalty_reasons == ["Dilution"]

    def test_score_cannot_go_negative(self):
        c = compute_composite(self._dims(1.0), penalty=99.0)
        assert c.overall_score == 0.0

    def test_confidence_falls_with_coverage(self):
        full = compute_composite(self._dims(7.0))
        partial = compute_composite([DimensionScore(Dimension.TECHNOLOGY, 7.0, "", 0.8)])
        assert partial.confidence_score < full.confidence_score

    def test_risk_cannot_be_weighted_in(self):
        with pytest.raises(ScoringError):
            compute_composite(self._dims(), weights={Dimension.RISK: 1.0})

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ScoringError):
            compute_composite(self._dims(), weights={Dimension.TECHNOLOGY: 0.5})

    def test_rejects_out_of_range_score(self):
        with pytest.raises(ScoringError):
            DimensionScore(Dimension.TECHNOLOGY, 11.0, "")


class TestVerdicts:
    def test_severe_red_flags_reject_regardless_of_score(self):
        v, _ = assign_verdict(90, 90, 3, 90, red_flag_score=75)
        assert v is Verdict.REJECTED

    def test_top_opportunity_needs_both_score_and_asymmetry(self):
        v, _ = assign_verdict(80, 75, 5, 70, 0)
        assert v is Verdict.TOP_OPPORTUNITY

    def test_great_company_at_a_bad_price_is_only_watch(self):
        """High quality with no asymmetry must not reach the top list."""
        v, _ = assign_verdict(78, 20, 4, 70, 0)
        assert v is Verdict.WATCH

    def test_high_risk_low_confidence_is_quarantined(self):
        v, _ = assign_verdict(65, 80, 9.0, 30, 0)
        assert v is Verdict.HIGH_RISK

    def test_no_verdict_says_buy(self):
        for v in Verdict:
            assert "BUY" not in v.value and "SELL" not in v.value


class TestValuationScore:
    def test_implausible_requirement_scores_near_zero(self):
        assert valuation_score_from_reverse(1.5, 2.0).score < 1.5

    def test_modest_requirement_scores_high(self):
        assert valuation_score_from_reverse(0.01, 2.0).score > 8.5

    def test_unknown_market_is_neutral_and_low_confidence(self):
        d = valuation_score_from_reverse(None, 2.0)
        assert d.score == 5.0 and d.confidence <= 0.3

    def test_monotonic_in_required_share(self):
        scores = [valuation_score_from_reverse(s, 1.0).score
                  for s in (0.9, 0.3, 0.15, 0.05, 0.01)]
        assert scores == sorted(scores)


# ==========================================================================
class TestSignals:
    def _series(self, values: list[float]) -> list[TimeSeriesPoint]:
        start = date(2024, 1, 1)
        return [TimeSeriesPoint(start + timedelta(days=30 * i), v)
                for i, v in enumerate(values)]

    def test_detects_genuine_acceleration(self):
        s = self._series([50] * 12 + [90, 130, 190])
        sig = detect_acceleration(SignalType.HIRING, s)
        assert sig is not None
        assert sig.pct_change > 1.0
        assert sig.strength in (SignalStrength.STRONG, SignalStrength.EXTREME)

    def test_flat_series_produces_nothing(self):
        assert detect_acceleration(SignalType.HIRING, self._series([50] * 15)) is None

    def test_decline_produces_nothing(self):
        s = self._series([100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30])
        assert detect_acceleration(SignalType.HIRING, s) is None

    def test_noisy_series_needs_more_than_magnitude(self):
        """A metric that always swings wildly has not done anything by swinging again."""
        volatile = self._series([10, 300, 15, 280, 20, 260, 12, 290, 18, 270, 14, 285, 20, 300, 25])
        sig = detect_acceleration(SignalType.HIRING, volatile)
        assert sig is None or sig.strength is not SignalStrength.EXTREME

    def test_small_absolute_numbers_are_ignored(self):
        """One contributor to four is a 300% rise and means nothing."""
        s = self._series([1] * 12 + [3, 4, 4])
        assert detect_acceleration(SignalType.GITHUB_CONTRIBUTORS, s) is None

    def test_as_of_prevents_lookahead(self):
        s = self._series([50] * 12 + [90, 130, 190])
        cutoff = s[11].at
        assert detect_acceleration(SignalType.HIRING, s, as_of=cutoff) is None

    def test_robust_z_resists_a_single_outlier(self):
        history = [10, 11, 9, 10, 10, 11, 9, 500]
        assert robust_z_score(30, history) > 3.0

    def test_z_of_constant_history(self):
        assert robust_z_score(10, [10, 10, 10, 10]) == 0.0

    def test_short_series_returns_none(self):
        assert detect_acceleration(SignalType.HIRING, self._series([1, 2, 3])) is None


class TestSignalAggregation:
    def _sig(self, stype: SignalType, strength: SignalStrength):
        from asymmetry.core.signals import Signal
        return Signal(stype, strength, 100, 50, 1.0, 3.0, "3v12",
                      date(2024, 6, 1), "test", True)

    def test_no_signals_is_zero(self):
        assert aggregate_signal_score([]) == 0.0

    def test_diversity_beats_intensity(self):
        diverse = [self._sig(t, SignalStrength.MODERATE) for t in
                   (SignalType.HIRING, SignalType.PATENT_FILINGS,
                    SignalType.PUBLICATIONS, SignalType.PARTNERSHIPS)]
        concentrated = [self._sig(SignalType.HIRING, SignalStrength.EXTREME)]
        assert aggregate_signal_score(diverse) > aggregate_signal_score(concentrated)

    def test_bounded(self):
        many = [self._sig(t, SignalStrength.EXTREME) for t in SignalType]
        assert 0 <= aggregate_signal_score(many) <= 10


# ==========================================================================
class TestHype:
    def test_promotional_text_scores_high(self):
        text = ("Our revolutionary, game-changing AI-powered platform is poised to "
                "disrupt this massive opportunity with unprecedented, groundbreaking, "
                "industry-leading synergies and unlimited potential.")
        assert analyse_hype(text).hype_score > 50

    def test_factual_text_scores_low(self):
        text = ("Revenue was $210 million, up from $138 million. Gross margin was "
                "37%. The company shipped 1,400 units to 22 customers and holds "
                "14 granted patents.")
        assert analyse_hype(text).hype_score < 15

    def test_evidence_partially_forgives_promotion(self):
        hyped = "Our revolutionary game-changing breakthrough platform is transformative."
        supported = (hyped + " Revenue was $50 million, up 40% year-over-year, "
                     "across 1,200 customers with 30 patents granted.")
        assert analyse_hype(supported).hype_score < analyse_hype(hyped).hype_score

    def test_evidence_never_fully_forgives(self):
        """Real revenue does not license dishonest description."""
        text = ("Revolutionary game-changing paradigm shift with unlimited potential, "
                "guaranteed unprecedented groundbreaking visionary disruption. "
                "Revenue was $50 million, up 40% year-over-year.")
        assert analyse_hype(text).hype_score > 10

    def test_unsubstantiated_flag(self):
        loud = ("Revolutionary game-changing disruptive paradigm shift, unprecedented "
                "groundbreaking transformative visionary unparalleled next-generation "
                "cutting-edge world-class limitless unlimited potential guaranteed.")
        assert analyse_hype(loud).is_unsubstantiated_hype

    def test_empty_text(self):
        assert analyse_hype("").hype_score == 0.0

    def test_normalised_by_length(self):
        """A long filing must not be penalised merely for being long."""
        short = "This revolutionary product is groundbreaking."
        long = short + " The quick brown fox jumps over the lazy dog. " * 60
        assert analyse_hype(long).hype_score < analyse_hype(short).hype_score


# ==========================================================================
class TestRedFlags:
    def test_clean_company_has_no_flags(self):
        fin = FinancialSnapshot(
            market_cap=1e9, revenue=200e6, revenue_prior=150e6,
            gross_margin=0.40, gross_margin_prior=0.38,
            free_cash_flow=30e6, cash=100e6, debt=10e6,
            shares_outstanding=50e6, shares_outstanding_prior=49.5e6,
            stock_based_comp=10e6, largest_customer_pct=0.10,
        )
        assert detect_red_flags(fin).flags == []

    def test_going_concern_is_critical(self):
        r = detect_red_flags(FinancialSnapshot(going_concern_doubt=True))
        assert any(f.severity is Severity.CRITICAL for f in r.flags)

    def test_severe_dilution_detected(self):
        r = detect_red_flags(FinancialSnapshot(
            shares_outstanding=480e6, shares_outstanding_prior=210e6))
        assert any(f.code == "DILUTION_SEVERE" for f in r.flags)

    def test_short_runway_detected(self):
        r = detect_red_flags(FinancialSnapshot(cash=9e6, free_cash_flow=-41e6))
        assert any(f.code == "RUNWAY_CRITICAL" for f in r.flags)

    def test_profitable_company_has_no_runway_flag(self):
        r = detect_red_flags(FinancialSnapshot(cash=9e6, free_cash_flow=41e6))
        assert not any("RUNWAY" in f.code for f in r.flags)

    def test_fraud_pattern_scores_very_high(self):
        fin = FinancialSnapshot(
            market_cap=720e6, revenue=3.1e6, revenue_prior=4.4e6,
            gross_margin=0.12, gross_margin_prior=0.44,
            cash=9e6, debt=55e6, free_cash_flow=-41e6,
            shares_outstanding=480e6, shares_outstanding_prior=210e6,
            going_concern_doubt=True, restatements=1, active_investigations=1,
            insider_selling_ratio=0.94, management_departures_12m=4,
            auditor_changes_24m=2, missed_milestones=5,
            related_party_transactions=True, largest_customer_pct=0.67,
        )
        r = detect_red_flags(fin, hype_score=85, hype_unsubstantiated=True)
        assert r.red_flag_score >= 70
        assert r.penalty_points <= 30.0    # capped so it shapes rather than erases

    def test_unknown_is_not_treated_as_zero(self):
        """A company with unknown debt is not a company with no debt."""
        assert detect_red_flags(FinancialSnapshot()).flags == []

    def test_penalty_is_capped(self):
        fin = FinancialSnapshot(
            going_concern_doubt=True, restatements=3, active_investigations=3,
            auditor_changes_24m=4, related_party_transactions=True,
        )
        assert detect_red_flags(fin).penalty_points <= 30.0


# ==========================================================================
class TestMovementExplanation:
    """Section 13: explain why a candidate moved."""

    BEFORE = {
        "overall_score": 72.0, "rank": 2, "asymmetry_score": 80.0, "verdict": "INVESTIGATE",
        "penalty": 0.0, "penalty_reasons": [],
        "components": {"technology": 8.0, "market": 7.0, "financial_health": 7.0,
                       "valuation": 8.0, "early_signals": 6.0},
        "weights": {"technology": 0.15, "market": 0.15, "financial_health": 0.10,
                    "valuation": 0.15, "early_signals": 0.15},
    }

    def _after(self, **overrides):
        from copy import deepcopy
        d = deepcopy(self.BEFORE)
        d.update(overrides)
        return d

    def test_identifies_the_dimension_that_moved(self):
        from asymmetry.core.movement import explain_movement

        after = self._after(
            overall_score=58.0, rank=17,
            components={**self.BEFORE["components"], "financial_health": 2.0},
        )
        exp = explain_movement(self.BEFORE, after)
        assert exp.changes
        assert exp.changes[0].dimension == "financial_health"
        assert exp.changes[0].delta == -5.0
        assert "financial health deteriorated" in exp.summary

    def test_rank_delta_direction(self):
        from asymmetry.core.movement import explain_movement

        assert explain_movement(self.BEFORE, self._after(rank=17)).rank_delta == -15
        assert explain_movement(self.BEFORE, self._after(rank=1)).rank_delta == 1

    def test_ignores_noise_below_threshold(self):
        from asymmetry.core.movement import explain_movement

        after = self._after(components={**self.BEFORE["components"], "technology": 8.2})
        assert explain_movement(self.BEFORE, after).changes == []

    def test_ranks_by_weighted_impact_not_raw_delta(self):
        """A small move in a heavy dimension can outrank a large move in a light one."""
        from asymmetry.core.movement import explain_movement

        after = self._after(components={
            **self.BEFORE["components"],
            "valuation": 5.0,          # -3.0 at weight 0.15 = -4.5 points
            "financial_health": 3.0,   # -4.0 at weight 0.10 = -4.0 points
        })
        exp = explain_movement(self.BEFORE, after)
        assert exp.changes[0].dimension == "valuation"

    def test_new_red_flags_reported(self):
        from asymmetry.core.movement import explain_movement

        after = self._after(penalty=12.0, penalty_reasons=["Heavy dilution"])
        exp = explain_movement(self.BEFORE, after)
        assert exp.new_penalties == ["Heavy dilution"]
        assert "New red flags" in exp.summary

    def test_resolved_flags_reported(self):
        from asymmetry.core.movement import explain_movement

        before = {**self.BEFORE, "penalty_reasons": ["Short runway"], "penalty": 12.0}
        exp = explain_movement(before, self._after())
        assert exp.resolved_penalties == ["Short runway"]

    def test_movement_with_no_internal_change_is_attributed_to_others(self):
        """Falling because others rose is a different fact from falling on merit."""
        from asymmetry.core.movement import explain_movement

        exp = explain_movement(self.BEFORE, self._after(rank=9))
        assert "other candidates" in exp.summary

    def test_verdict_change_noted(self):
        from asymmetry.core.movement import explain_movement

        exp = explain_movement(self.BEFORE, self._after(verdict="REJECTED"))
        assert "INVESTIGATE to REJECTED" in exp.summary

    def test_attribution_uses_the_earlier_weights(self):
        """A recalibration is a change in the model, not in the candidate."""
        from asymmetry.core.movement import explain_movement

        after = self._after(
            components={**self.BEFORE["components"], "technology": 4.0},
            weights={**self.BEFORE["weights"], "technology": 0.99},
        )
        exp = explain_movement(self.BEFORE, after)
        tech = [c for c in exp.changes if c.dimension == "technology"][0]
        assert tech.weight == 0.15

    def test_no_change_is_stated_plainly(self):
        from asymmetry.core.movement import explain_movement

        assert explain_movement(self.BEFORE, self._after()).summary == "No material change."

    def test_serialises(self):
        from asymmetry.core.movement import explain_movement

        d = explain_movement(self.BEFORE, self._after(rank=17)).to_dict()
        assert "summary" in d and "changes" in d and d["rank_delta"] == -15
