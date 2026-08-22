"""The feedback loop (section 51).

The goal is not an AI that sounds intelligent. It is one that becomes
empirically better at identifying asymmetric opportunities. That requires
writing predictions down, waiting, comparing them to what happened, and letting
the comparison change how the system scores things.

Three measurements, in increasing order of usefulness:

**Brier score** - mean squared error of probabilistic forecasts. Lower is
better. It rewards being right *and* being appropriately uncertain, which is
why it is preferred here over accuracy: a system that says "70% confident"
about everything can look accurate while knowing nothing.

**Skill score** - Brier measured against the base rate rather than against
zero. This is the honest question. If 20% of candidates succeed and the system
predicts 20% for everyone, its Brier score looks respectable while its skill is
exactly zero. Only skill distinguishes a model from a well-calibrated shrug.

**Per-signal lift** - for each signal type, how much more often did candidates
carrying that signal succeed than candidates without it. This is what section
51 is really asking for: *which signals actually preceded large outcomes?* The
answer replaces the hand-tuned weights in the scoring model.

Everything here is pure. No database, no clock, no network.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Sequence

#: Below this many resolved predictions, any accuracy figure is noise. The
#: system reports "insufficient data" rather than a number, because a
#: confident-looking statistic computed from four samples is worse than no
#: statistic at all.
MIN_RESOLUTIONS_FOR_INFERENCE = 20

#: Per-signal lift needs even more, since it partitions the sample.
MIN_RESOLUTIONS_PER_SIGNAL = 12


class LearningError(ValueError):
    pass


@dataclass
class ResolvedPrediction:
    """A prediction that has met its horizon and been checked against reality."""

    prediction_id: str
    candidate_id: str
    made_at: date
    horizon_date: date
    probability: float          # what the system said, 0-1
    outcome: bool               # what actually happened
    driving_signals: list[str] = field(default_factory=list)
    metric: str | None = None
    predicted_value: float | None = None
    actual_value: float | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise LearningError(f"probability must be 0-1, got {self.probability}")

    @property
    def brier(self) -> float:
        """Squared error of this single forecast."""
        return (self.probability - (1.0 if self.outcome else 0.0)) ** 2

    @property
    def was_directionally_right(self) -> bool:
        """Did the forecast land on the correct side of even odds?"""
        return (self.probability >= 0.5) == self.outcome


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------
def brier_score(predictions: Sequence[ResolvedPrediction]) -> float:
    """Mean squared error. 0 is perfect, 0.25 is a coin flip at p=0.5, 1 is worst."""
    if not predictions:
        raise LearningError("no resolved predictions")
    return sum(p.brier for p in predictions) / len(predictions)


def base_rate(predictions: Sequence[ResolvedPrediction]) -> float:
    """How often the thing actually happened, regardless of what was predicted."""
    if not predictions:
        raise LearningError("no resolved predictions")
    return sum(1 for p in predictions if p.outcome) / len(predictions)


def skill_score(predictions: Sequence[ResolvedPrediction]) -> float:
    """Brier skill against always predicting the base rate.

    Positive means the model beats a shrug. Zero means it adds nothing. Negative
    means it would be better to ignore it entirely.

    This is the number that matters, and it is the one a system flattering
    itself would prefer not to compute.
    """
    if not predictions:
        raise LearningError("no resolved predictions")

    bs = brier_score(predictions)
    rate = base_rate(predictions)
    # Reference forecaster: predicts the base rate for everything.
    reference = sum((rate - (1.0 if p.outcome else 0.0)) ** 2 for p in predictions) / len(predictions)

    if reference < 1e-12:
        # Every outcome identical; skill is undefined rather than perfect.
        return 0.0
    return 1.0 - (bs / reference)


@dataclass
class CalibrationBucket:
    lower: float
    upper: float
    count: int
    mean_predicted: float
    observed_rate: float

    @property
    def gap(self) -> float:
        """Positive means overconfident: predicted more than actually happened."""
        return self.mean_predicted - self.observed_rate


def calibration(
    predictions: Sequence[ResolvedPrediction], buckets: int = 5
) -> list[CalibrationBucket]:
    """Bucket forecasts by stated probability and compare to what happened.

    A well-calibrated system that says 70% is right about 70% of the time. This
    diagnoses the specific failure the platform is most prone to - systematic
    overconfidence about speculative companies.
    """
    if not predictions:
        return []
    if buckets < 2:
        raise LearningError("need at least two buckets")

    width = 1.0 / buckets
    out: list[CalibrationBucket] = []
    for i in range(buckets):
        lo, hi = i * width, (i + 1) * width
        # Final bucket is closed so p=1.0 is included somewhere.
        members = [
            p for p in predictions
            if (lo <= p.probability < hi) or (i == buckets - 1 and p.probability == 1.0)
        ]
        if not members:
            continue
        out.append(CalibrationBucket(
            lower=lo, upper=hi, count=len(members),
            mean_predicted=sum(p.probability for p in members) / len(members),
            observed_rate=sum(1 for p in members if p.outcome) / len(members),
        ))
    return out


def overconfidence(predictions: Sequence[ResolvedPrediction]) -> float:
    """Mean predicted probability minus observed rate.

    Positive is overconfident. Reported prominently because optimism is the
    house bias of any system built to find enormous upside.
    """
    if not predictions:
        raise LearningError("no resolved predictions")
    mean_p = sum(p.probability for p in predictions) / len(predictions)
    return mean_p - base_rate(predictions)


# --------------------------------------------------------------------------
# Which signals actually worked
# --------------------------------------------------------------------------
@dataclass
class SignalPerformance:
    """How predictive one signal type turned out to be."""

    signal_type: str
    with_signal: int
    without_signal: int
    success_rate_with: float
    success_rate_without: float
    brier_with: float | None
    sufficient_data: bool

    @property
    def lift(self) -> float:
        """Ratio of success rate with the signal to without it.

        1.0 means the signal told you nothing. Below 1.0 means it was actively
        misleading, which is a real and useful finding.
        """
        if self.success_rate_without < 1e-9:
            return float("inf") if self.success_rate_with > 0 else 1.0
        return self.success_rate_with / self.success_rate_without

    @property
    def verdict(self) -> str:
        if not self.sufficient_data:
            return f"Insufficient data ({self.with_signal} resolved; need {MIN_RESOLUTIONS_PER_SIGNAL})."
        lift = self.lift
        if math.isinf(lift):
            return "Every success carried this signal, but no counter-examples to compare against."
        if lift >= 2.0:
            return f"Strongly predictive: {lift:.1f}x the success rate."
        if lift >= 1.3:
            return f"Modestly predictive: {lift:.1f}x the success rate."
        if lift >= 0.8:
            return f"No detectable predictive value ({lift:.2f}x)."
        return f"Counter-predictive: {lift:.2f}x. Candidates with this signal did worse."


def signal_performance(
    predictions: Sequence[ResolvedPrediction],
) -> list[SignalPerformance]:
    """Measure each signal type against outcomes, ranked by lift.

    This is the mechanism by which the platform learns something a human did not
    tell it. If patent acceleration turns out to be noise and government
    contract acceleration turns out to matter, this is where that shows up -
    and it may well contradict the priors in the scoring model.
    """
    all_types = sorted({s for p in predictions for s in p.driving_signals})
    out: list[SignalPerformance] = []

    for stype in all_types:
        withs = [p for p in predictions if stype in p.driving_signals]
        withouts = [p for p in predictions if stype not in p.driving_signals]
        if not withs:
            continue

        rate_with = sum(1 for p in withs if p.outcome) / len(withs)
        rate_without = (
            sum(1 for p in withouts if p.outcome) / len(withouts) if withouts else 0.0
        )
        out.append(SignalPerformance(
            signal_type=stype,
            with_signal=len(withs),
            without_signal=len(withouts),
            success_rate_with=rate_with,
            success_rate_without=rate_without,
            brier_with=brier_score(withs) if withs else None,
            sufficient_data=len(withs) >= MIN_RESOLUTIONS_PER_SIGNAL and bool(withouts),
        ))

    out.sort(key=lambda s: (-s.lift if math.isfinite(s.lift) else -1e9))
    return out


# --------------------------------------------------------------------------
# Turning measurements into weights
# --------------------------------------------------------------------------
def recalibrate_weights(
    current: dict[str, float],
    performance: Sequence[SignalPerformance],
    *,
    signal_to_dimension: dict[str, str] | None = None,
    max_shift: float = 0.25,
) -> tuple[dict[str, float], list[str]]:
    """Nudge dimension weights toward what the evidence supports.

    Three deliberate constraints:

    * Only signals with sufficient data move anything.
    * No weight moves more than ``max_shift`` relative to its current value in a
      single recalibration, so one unlucky quarter cannot rewrite the model.
    * Weights are renormalised to sum to 1.

    Returns the new weights and a plain-language changelog, because a weighting
    model that changes without explanation is one nobody can audit.
    """
    if not current:
        raise LearningError("no current weights supplied")
    if not 0.0 < max_shift < 1.0:
        raise LearningError("max_shift must be between 0 and 1")

    mapping = signal_to_dimension or DEFAULT_SIGNAL_TO_DIMENSION
    usable = [p for p in performance if p.sufficient_data and math.isfinite(p.lift)]

    if not usable:
        return dict(current), ["No signal had enough resolved predictions to justify a change."]

    # Average the lift of every signal that maps onto each dimension.
    lifts: dict[str, list[float]] = {}
    for perf in usable:
        dim = mapping.get(perf.signal_type)
        if dim and dim in current:
            lifts.setdefault(dim, []).append(perf.lift)

    if not lifts:
        return dict(current), ["No measured signal maps onto a weighted dimension."]

    new = dict(current)
    changelog: list[str] = []
    for dim, values in lifts.items():
        mean_lift = sum(values) / len(values)
        # Lift of 1.0 means no evidence of value, so no movement.
        adjustment = max(-max_shift, min(max_shift, (mean_lift - 1.0) * 0.5))
        before = new[dim]
        after = max(0.01, before * (1.0 + adjustment))
        new[dim] = after
        if abs(after - before) > 1e-6:
            changelog.append(
                f"{dim}: {before:.3f} -> {after:.3f} "
                f"(mean lift {mean_lift:.2f} across {len(values)} signal type(s))"
            )

    total = sum(new.values())
    if total <= 0:
        raise LearningError("recalibration produced non-positive weights")
    new = {k: v / total for k, v in new.items()}
    changelog.append("Weights renormalised to sum to 1.0.")
    return new, changelog


#: Which scoring dimension each signal type speaks to. Signals that are purely
#: about adoption speed inform EARLY_SIGNALS; the rest inform the dimension
#: whose thesis they would confirm.
DEFAULT_SIGNAL_TO_DIMENSION: dict[str, str] = {
    "hiring": "early_signals",
    "github_activity": "early_signals",
    "github_contributors": "early_signals",
    "search_interest": "early_signals",
    "community_activity": "early_signals",
    "patent_filings": "technology",
    "publications": "technology",
    "research_citations": "technology",
    "revenue_growth": "growth",
    "funding": "financial_health",
    "customer_announcements": "market",
    "partnerships": "competitive_advantage",
    "government_contracts": "competitive_advantage",
    "manufacturing_capacity": "market",
}


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
@dataclass
class LearningReport:
    """What the system has learned, and how much to trust it."""

    resolved_count: int
    brier: float | None
    skill: float | None
    base_rate: float | None
    overconfidence: float | None
    directional_accuracy: float | None
    calibration: list[CalibrationBucket]
    signals: list[SignalPerformance]
    sufficient_data: bool
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolved_count": self.resolved_count,
            "brier": round(self.brier, 4) if self.brier is not None else None,
            "skill": round(self.skill, 4) if self.skill is not None else None,
            "base_rate": round(self.base_rate, 4) if self.base_rate is not None else None,
            "overconfidence": (
                round(self.overconfidence, 4) if self.overconfidence is not None else None
            ),
            "directional_accuracy": (
                round(self.directional_accuracy, 4)
                if self.directional_accuracy is not None else None
            ),
            "sufficient_data": self.sufficient_data,
            "calibration": [
                {"range": f"{b.lower:.0%}-{b.upper:.0%}", "count": b.count,
                 "predicted": round(b.mean_predicted, 3),
                 "observed": round(b.observed_rate, 3), "gap": round(b.gap, 3)}
                for b in self.calibration
            ],
            "signals": [
                {"signal_type": s.signal_type, "with_signal": s.with_signal,
                 "success_rate_with": round(s.success_rate_with, 3),
                 "success_rate_without": round(s.success_rate_without, 3),
                 "lift": round(s.lift, 3) if math.isfinite(s.lift) else None,
                 "sufficient_data": s.sufficient_data, "verdict": s.verdict}
                for s in self.signals
            ],
            "summary": self.summary,
        }


def build_report(predictions: Sequence[ResolvedPrediction]) -> LearningReport:
    """Assemble everything measurable, refusing to overclaim on thin data."""
    n = len(predictions)
    if n == 0:
        return LearningReport(
            0, None, None, None, None, None, [], [], False,
            "No predictions have resolved yet. The system has learned nothing "
            "and its scoring weights remain hand-chosen priors.",
        )

    sufficient = n >= MIN_RESOLUTIONS_FOR_INFERENCE
    bs = brier_score(predictions)
    sk = skill_score(predictions)
    rate = base_rate(predictions)
    over = overconfidence(predictions)
    directional = sum(1 for p in predictions if p.was_directionally_right) / n

    if not sufficient:
        summary = (
            f"Only {n} resolved prediction(s); {MIN_RESOLUTIONS_FOR_INFERENCE} are needed "
            f"before these figures mean anything. Reported for transparency, not for use."
        )
    else:
        if sk > 0.15:
            verdict = "The model is adding real predictive value over the base rate."
        elif sk > 0.02:
            verdict = "The model is marginally better than predicting the base rate."
        elif sk > -0.02:
            verdict = (
                "The model is no better than predicting the base rate for everything. "
                "Its apparent accuracy comes from the base rate, not from skill."
            )
        else:
            verdict = (
                "The model is worse than predicting the base rate. Its scores should "
                "not be used until this is understood."
            )
        bias = (
            f" It is overconfident by {over:+.1%}." if over > 0.05
            else f" It is underconfident by {abs(over):.1%}." if over < -0.05
            else " It is reasonably calibrated."
        )
        summary = (
            f"{n} resolved. Brier {bs:.3f}, skill {sk:+.3f} against a base rate of "
            f"{rate:.1%}. {verdict}{bias}"
        )

    return LearningReport(
        resolved_count=n, brier=bs, skill=sk, base_rate=rate,
        overconfidence=over, directional_accuracy=directional,
        calibration=calibration(predictions), signals=signal_performance(predictions),
        sufficient_data=sufficient, summary=summary,
    )
