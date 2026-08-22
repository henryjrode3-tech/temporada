"""Feedback-loop tests (section 51).

The property under test throughout: the system must be able to discover that it
is bad at its job. A learning layer that cannot report failure is decoration.
"""

from __future__ import annotations

import math
from datetime import date

import pytest

from asymmetry.core.learning import (
    MIN_RESOLUTIONS_FOR_INFERENCE,
    LearningError,
    ResolvedPrediction,
    base_rate,
    brier_score,
    build_report,
    calibration,
    overconfidence,
    recalibrate_weights,
    signal_performance,
    skill_score,
)

MADE = date(2020, 1, 1)
HORIZON = date(2025, 1, 1)


def pred(prob: float, outcome: bool, signals=None, i: int = 0) -> ResolvedPrediction:
    return ResolvedPrediction(
        prediction_id=f"p{i}", candidate_id=f"c{i}", made_at=MADE, horizon_date=HORIZON,
        probability=prob, outcome=outcome, driving_signals=list(signals or []),
    )


class TestBrier:
    def test_perfect_forecasts_score_zero(self):
        preds = [pred(1.0, True, i=0), pred(0.0, False, i=1)]
        assert brier_score(preds) == pytest.approx(0.0)

    def test_maximally_wrong_scores_one(self):
        preds = [pred(0.0, True, i=0), pred(1.0, False, i=1)]
        assert brier_score(preds) == pytest.approx(1.0)

    def test_coin_flip_scores_quarter(self):
        preds = [pred(0.5, True, i=0), pred(0.5, False, i=1)]
        assert brier_score(preds) == pytest.approx(0.25)

    def test_rewards_appropriate_uncertainty(self):
        """Hedging on a wrong call beats being confidently wrong."""
        confident_wrong = [pred(0.95, False, i=0)]
        hedged_wrong = [pred(0.55, False, i=1)]
        assert brier_score(hedged_wrong) < brier_score(confident_wrong)

    def test_empty_raises(self):
        with pytest.raises(LearningError):
            brier_score([])

    def test_probability_must_be_valid(self):
        with pytest.raises(LearningError):
            pred(1.4, True)


class TestSkill:
    def test_base_rate_forecaster_has_zero_skill(self):
        """Predicting the base rate for everyone adds nothing, and must score zero."""
        # 20% base rate, predicted 0.2 for all.
        preds = [pred(0.2, i < 4, i=i) for i in range(20)]
        assert skill_score(preds) == pytest.approx(0.0, abs=1e-9)

    def test_informative_model_has_positive_skill(self):
        preds = [pred(0.9, True, i=i) for i in range(5)]
        preds += [pred(0.1, False, i=5 + i) for i in range(15)]
        assert skill_score(preds) > 0.5

    def test_anti_predictive_model_has_negative_skill(self):
        """The system must be able to discover that it is worse than useless."""
        preds = [pred(0.9, False, i=i) for i in range(5)]
        preds += [pred(0.1, True, i=5 + i) for i in range(5)]
        assert skill_score(preds) < 0

    def test_uniform_outcomes_give_undefined_skill_not_perfect(self):
        preds = [pred(0.5, True, i=i) for i in range(10)]
        assert skill_score(preds) == 0.0

    def test_high_accuracy_can_still_mean_zero_skill(self):
        """The trap this metric exists to catch.

        A rare event predicted at its base rate looks accurate and knows nothing.
        """
        preds = [pred(0.05, False, i=i) for i in range(19)] + [pred(0.05, True, i=19)]
        assert brier_score(preds) < 0.06          # looks excellent
        assert skill_score(preds) == pytest.approx(0.0, abs=1e-9)   # is worthless


class TestCalibration:
    def test_well_calibrated_has_small_gaps(self):
        preds = [pred(0.7, i < 7, i=i) for i in range(10)]
        buckets = calibration(preds)
        assert all(abs(b.gap) < 0.05 for b in buckets)

    def test_overconfidence_detected(self):
        preds = [pred(0.9, i < 3, i=i) for i in range(10)]
        assert overconfidence(preds) > 0.5

    def test_underconfidence_detected(self):
        preds = [pred(0.2, i < 8, i=i) for i in range(10)]
        assert overconfidence(preds) < -0.5

    def test_probability_of_one_is_bucketed(self):
        buckets = calibration([pred(1.0, True, i=0), pred(1.0, False, i=1)])
        assert sum(b.count for b in buckets) == 2

    def test_empty_returns_no_buckets(self):
        assert calibration([]) == []

    def test_requires_at_least_two_buckets(self):
        with pytest.raises(LearningError):
            calibration([pred(0.5, True)], buckets=1)


class TestSignalPerformance:
    def _dataset(self):
        # "government_contracts" genuinely predicts; "patent_filings" does not.
        preds = []
        for i in range(15):
            preds.append(pred(0.6, True, ["government_contracts", "hiring"], i=i))
        for i in range(15):
            preds.append(pred(0.4, False, ["patent_filings", "hiring"], i=100 + i))
        for i in range(15):
            preds.append(pred(0.3, False, ["patent_filings"], i=200 + i))
        return preds

    def test_identifies_the_predictive_signal(self):
        perf = {p.signal_type: p for p in signal_performance(self._dataset())}
        assert perf["government_contracts"].lift > 2.0
        assert perf["government_contracts"].sufficient_data

    def test_identifies_the_useless_signal(self):
        perf = {p.signal_type: p for p in signal_performance(self._dataset())}
        assert perf["patent_filings"].lift < 0.8
        assert "Counter-predictive" in perf["patent_filings"].verdict

    def test_ranked_by_lift(self):
        lifts = [p.lift for p in signal_performance(self._dataset())]
        assert lifts == sorted(lifts, reverse=True)

    def test_thin_data_is_refused_not_reported(self):
        thin = [pred(0.7, True, ["rare_signal"], i=i) for i in range(3)]
        thin += [pred(0.3, False, ["other"], i=10 + i) for i in range(3)]
        perf = {p.signal_type: p for p in signal_performance(thin)}
        assert not perf["rare_signal"].sufficient_data
        assert "Insufficient data" in perf["rare_signal"].verdict

    def test_signal_with_no_counterexamples_is_flagged(self):
        preds = [pred(0.8, True, ["only_signal"], i=i) for i in range(15)]
        perf = signal_performance(preds)[0]
        assert not perf.sufficient_data   # no comparison group

    def test_no_signals_yields_nothing(self):
        assert signal_performance([pred(0.5, True, [], i=0)]) == []


class TestRecalibration:
    WEIGHTS = {
        "market": 0.15, "technology": 0.15, "competitive_advantage": 0.15,
        "early_signals": 0.15, "valuation": 0.15, "growth": 0.10,
        "financial_health": 0.10, "management": 0.05,
    }

    def _perf(self, **kwargs):
        from asymmetry.core.learning import SignalPerformance
        defaults = dict(with_signal=20, without_signal=20, success_rate_with=0.6,
                        success_rate_without=0.2, brier_with=0.2, sufficient_data=True)
        defaults.update(kwargs)
        return SignalPerformance(**defaults)

    def test_predictive_signal_raises_its_dimension(self):
        perf = [self._perf(signal_type="government_contracts")]   # lift 3.0
        new, log = recalibrate_weights(self.WEIGHTS, perf)
        assert new["competitive_advantage"] > self.WEIGHTS["competitive_advantage"]
        assert any("competitive_advantage" in line for line in log)

    def test_counter_predictive_signal_lowers_its_dimension(self):
        perf = [self._perf(signal_type="patent_filings",
                           success_rate_with=0.1, success_rate_without=0.5)]
        new, _ = recalibrate_weights(self.WEIGHTS, perf)
        assert new["technology"] < self.WEIGHTS["technology"]

    def test_weights_stay_normalised(self):
        perf = [self._perf(signal_type="government_contracts")]
        new, _ = recalibrate_weights(self.WEIGHTS, perf)
        assert sum(new.values()) == pytest.approx(1.0)

    def test_movement_is_bounded(self):
        """One extraordinary quarter must not rewrite the model."""
        perf = [self._perf(signal_type="government_contracts",
                           success_rate_with=0.99, success_rate_without=0.01)]
        new, _ = recalibrate_weights(self.WEIGHTS, perf, max_shift=0.25)
        before = self.WEIGHTS["competitive_advantage"]
        assert new["competitive_advantage"] <= before * 1.25 / sum(
            recalibrate_weights(self.WEIGHTS, perf, max_shift=0.25)[0].values()
        ) + 1e-9

    def test_insufficient_data_changes_nothing(self):
        perf = [self._perf(signal_type="hiring", sufficient_data=False)]
        new, log = recalibrate_weights(self.WEIGHTS, perf)
        assert new == self.WEIGHTS
        assert "enough resolved predictions" in log[0]

    def test_unmapped_signal_changes_nothing(self):
        perf = [self._perf(signal_type="something_unmapped")]
        new, log = recalibrate_weights(self.WEIGHTS, perf)
        assert new == self.WEIGHTS
        assert "maps onto" in log[0]

    def test_empty_weights_rejected(self):
        with pytest.raises(LearningError):
            recalibrate_weights({}, [])

    def test_changelog_is_human_readable(self):
        perf = [self._perf(signal_type="government_contracts")]
        _, log = recalibrate_weights(self.WEIGHTS, perf)
        assert any("->" in line and "lift" in line for line in log)


class TestReport:
    def test_no_predictions_says_so_plainly(self):
        r = build_report([])
        assert r.resolved_count == 0 and not r.sufficient_data
        assert "learned nothing" in r.summary
        assert "hand-chosen priors" in r.summary

    def test_thin_data_refuses_to_be_used(self):
        r = build_report([pred(0.6, True, i=i) for i in range(5)])
        assert not r.sufficient_data
        assert "not for use" in r.summary

    def test_sufficient_data_reports_skill(self):
        preds = [pred(0.9, True, i=i) for i in range(8)]
        preds += [pred(0.1, False, i=10 + i) for i in range(15)]
        r = build_report(preds)
        assert r.sufficient_data and r.skill is not None and r.skill > 0
        assert "adding real predictive value" in r.summary

    def test_worthless_model_is_called_worthless(self):
        """The system must be willing to say its scores should not be used."""
        preds = [pred(0.9, False, i=i) for i in range(12)]
        preds += [pred(0.1, True, i=20 + i) for i in range(12)]
        r = build_report(preds)
        assert r.skill < 0
        assert "should" in r.summary and "not be used" in r.summary

    def test_overconfidence_surfaced_in_summary(self):
        preds = [pred(0.9, i < 5, i=i) for i in range(25)]
        assert "overconfident" in build_report(preds).summary

    def test_threshold_is_the_documented_one(self):
        below = build_report([pred(0.5, True, i=i) for i in range(MIN_RESOLUTIONS_FOR_INFERENCE - 1)])
        at = build_report([pred(0.5, i % 2 == 0, i=i) for i in range(MIN_RESOLUTIONS_FOR_INFERENCE)])
        assert not below.sufficient_data and at.sufficient_data

    def test_serialises(self):
        d = build_report([pred(0.7, True, ["hiring"], i=i) for i in range(25)]).to_dict()
        assert "summary" in d and "signals" in d and "calibration" in d
