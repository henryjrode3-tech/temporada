"""Alert rule tests.

The governing property: alerts fire on transitions, not on states. A rule that
re-fires every run for an unchanged condition trains the reader to ignore it.
"""

from __future__ import annotations

from datetime import date

import pytest

from asymmetry.core.alerts import (
    AlertLevel,
    AlertThresholds,
    CandidateSnapshot,
    evaluate,
    sort_alerts,
)

WHEN = date(2026, 1, 15)


def snap(**kw) -> CandidateSnapshot:
    base = dict(candidate_id="c1", name="Test Co", rank=20, overall_score=60.0,
                asymmetry_score=50.0, risk_score=5.0, red_flag_score=10.0,
                verdict="WATCH", revenue_growth=0.20, thesis_status="active")
    base.update(kw)
    return CandidateSnapshot(**base)


def codes(alerts) -> set[str]:
    return {a.code for a in alerts}


class TestTransitionsNotStates:
    def test_unchanged_high_score_does_not_refire(self):
        """The central rule. A standing condition is not news."""
        high = snap(asymmetry_score=90.0)
        assert "ASYMMETRY_HIGH" not in codes(evaluate(high, high, when=WHEN))

    def test_crossing_the_threshold_fires_once(self):
        before, after = snap(asymmetry_score=70.0), snap(asymmetry_score=90.0)
        assert "ASYMMETRY_HIGH" in codes(evaluate(before, after, when=WHEN))
        assert "ASYMMETRY_HIGH" not in codes(evaluate(after, after, when=WHEN))

    def test_falling_below_does_not_fire(self):
        assert "ASYMMETRY_HIGH" not in codes(
            evaluate(snap(asymmetry_score=90.0), snap(asymmetry_score=40.0), when=WHEN))

    def test_no_previous_snapshot_still_reports_notable_standing(self):
        alerts = evaluate(None, snap(asymmetry_score=90.0, rank=3), when=WHEN)
        assert "ASYMMETRY_HIGH" in codes(alerts)
        assert "ENTERED_TOP" in codes(alerts)

    def test_no_previous_snapshot_does_not_invent_deltas(self):
        alerts = evaluate(None, snap(risk_score=9.0, red_flag_score=90.0), when=WHEN)
        assert "RISK_SPIKE" not in codes(alerts)
        assert "RED_FLAG_SPIKE" not in codes(alerts)


class TestThesis:
    def test_invalidation_is_critical(self):
        alerts = evaluate(snap(), snap(thesis_status="invalidated"), when=WHEN)
        a = [x for x in alerts if x.code == "THESIS_INVALIDATED"][0]
        assert a.level is AlertLevel.CRITICAL

    def test_invalidation_does_not_refire(self):
        broken = snap(thesis_status="invalidated")
        assert "THESIS_INVALIDATED" not in codes(evaluate(broken, broken, when=WHEN))

    def test_weakening_is_high_not_critical(self):
        alerts = evaluate(snap(), snap(thesis_status="weakening"), when=WHEN)
        assert [x for x in alerts if x.code == "THESIS_WEAKENING"][0].level is AlertLevel.HIGH


class TestRisk:
    def test_red_flag_spike(self):
        alerts = evaluate(snap(red_flag_score=10.0), snap(red_flag_score=45.0), when=WHEN)
        assert "RED_FLAG_SPIKE" in codes(alerts)

    def test_small_red_flag_move_is_ignored(self):
        assert "RED_FLAG_SPIKE" not in codes(
            evaluate(snap(red_flag_score=10.0), snap(red_flag_score=18.0), when=WHEN))

    def test_risk_spike(self):
        assert "RISK_SPIKE" in codes(
            evaluate(snap(risk_score=4.0), snap(risk_score=7.0), when=WHEN))

    def test_risk_improvement_does_not_alert(self):
        assert "RISK_SPIKE" not in codes(
            evaluate(snap(risk_score=8.0), snap(risk_score=3.0), when=WHEN))

    def test_becoming_rejected_is_critical(self):
        alerts = evaluate(snap(verdict="INVESTIGATE"), snap(verdict="REJECTED"), when=WHEN)
        assert [x for x in alerts if x.code == "NOW_REJECTED"][0].level is AlertLevel.CRITICAL


class TestRanking:
    def test_entering_top_ten(self):
        assert "ENTERED_TOP" in codes(evaluate(snap(rank=25), snap(rank=4), when=WHEN))

    def test_moving_within_the_top_does_not_refire(self):
        assert "ENTERED_TOP" not in codes(evaluate(snap(rank=4), snap(rank=2), when=WHEN))

    def test_leaving_the_top(self):
        assert "LEFT_TOP" in codes(evaluate(snap(rank=3), snap(rank=40), when=WHEN))

    def test_dropping_out_of_the_ranking_entirely(self):
        alerts = evaluate(snap(rank=3), snap(rank=None), when=WHEN)
        assert "LEFT_TOP" in codes(alerts)
        assert "unranked" in [a for a in alerts if a.code == "LEFT_TOP"][0].detail

    def test_large_move_reported(self):
        assert "LARGE_RANK_MOVE" in codes(evaluate(snap(rank=40), snap(rank=5), when=WHEN))

    def test_small_move_ignored(self):
        assert "LARGE_RANK_MOVE" not in codes(evaluate(snap(rank=12), snap(rank=9), when=WHEN))


class TestFundamentals:
    def test_revenue_acceleration(self):
        assert "REVENUE_ACCELERATION" in codes(
            evaluate(snap(revenue_growth=0.20), snap(revenue_growth=0.65), when=WHEN))

    def test_deceleration_does_not_fire(self):
        assert "REVENUE_ACCELERATION" not in codes(
            evaluate(snap(revenue_growth=0.60), snap(revenue_growth=0.10), when=WHEN))

    def test_new_signals_are_reported(self):
        alerts = evaluate(snap(), snap(new_significant_signals=[
            {"signal_type": "hiring", "strength": "strong", "description": "Hiring +180%"}
        ]), when=WHEN)
        assert "SIGNAL_DETECTED" in codes(alerts)


class TestOrdering:
    def test_most_severe_first(self):
        alerts = evaluate(
            snap(rank=3, verdict="INVESTIGATE"),
            snap(rank=None, verdict="REJECTED", thesis_status="invalidated"),
            when=WHEN,
        )
        ordered = sort_alerts(alerts)
        assert ordered[0].level is AlertLevel.CRITICAL
        levels = [a.level for a in ordered]
        assert levels == sorted(levels, key=lambda l: {"critical": 0, "high": 1, "info": 2}[l.value])

    def test_serialises(self):
        alerts = evaluate(snap(), snap(thesis_status="invalidated"), when=WHEN)
        d = alerts[0].to_dict()
        assert d["code"] and d["level"] and d["raised_at"] == "2026-01-15"


class TestThresholds:
    def test_custom_thresholds_respected(self):
        strict = AlertThresholds(asymmetry_high=95.0)
        assert "ASYMMETRY_HIGH" not in codes(
            evaluate(snap(asymmetry_score=50.0), snap(asymmetry_score=90.0),
                     thresholds=strict, when=WHEN))

    def test_top_n_configurable(self):
        wide = AlertThresholds(top_n=25)
        assert "ENTERED_TOP" in codes(
            evaluate(snap(rank=40), snap(rank=20), thresholds=wide, when=WHEN))
