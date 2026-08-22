"""Recording and resolving predictions (section 51).

The feedback loop needs three things the analysis pipeline does not naturally
produce: a *falsifiable* claim, a *date* by which it should have come true, and
a record of *which signals* drove it. Without all three, "was the system right?"
is unanswerable after the fact.

Predictions are generated from thesis conditions, because those are already
falsifiable by construction: metric, comparator, threshold. A thesis condition
is a prediction that has not yet been written down as one.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..core.learning import (
    ResolvedPrediction,
    build_report,
    recalibrate_weights,
    signal_performance,
)
from ..core.scoring import DEFAULT_WEIGHTS
from ..db import models as m

log = logging.getLogger(__name__)

#: How far out a generated prediction looks. Long enough for the thesis to have
#: been tested, short enough to produce feedback within the platform's lifetime.
DEFAULT_HORIZON_DAYS = 365

#: A condition still holding at the horizon counts as the prediction coming
#: true. "Broken" counts as false. "Unknown" is unresolvable and is skipped
#: rather than guessed - scoring an unknown as either outcome would poison the
#: very measurements the loop exists to produce.
RESOLVABLE_STATUSES = {"holding", "at_risk", "broken"}


def generate_predictions(
    session: Session,
    candidate: m.Candidate,
    *,
    as_of: date | None = None,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
) -> list[m.Prediction]:
    """Turn a candidate's thesis conditions into recorded predictions.

    The probability attached is the candidate's confidence score. The asymmetry
    score would be the wrong choice outright - it measures payoff size, not
    likelihood, so grading it against binary outcomes is a category error.

    Confidence is the least-wrong available number, but it is not the right one
    either, and the calibration report says so out loud. Confidence means "how
    much do we trust this analysis"; what a prediction needs is "how likely is
    this specific condition to hold". Because the generated conditions are
    anchored to a candidate's current metrics with headroom, they hold far more
    often than the confidence score implies, and the loop duly reports the
    system as systematically underconfident.

    That is the mechanism working as intended rather than a bug to paper over:
    the first thing a feedback loop should discover is that its own inputs are
    miscalibrated. Replacing this with a per-condition probability is a change
    the calibration data should drive, once there is enough of it to justify a
    number rather than a guess.
    """
    today = as_of or date.today()
    thesis = (
        session.query(m.Thesis)
        .filter(m.Thesis.candidate_id == candidate.id)
        .order_by(m.Thesis.created_at.desc())
        .first()
    )
    if thesis is None:
        return []

    driving = [
        s.signal_type for s in
        session.query(m.Signal).filter(m.Signal.candidate_id == candidate.id).all()
    ]
    probability = (candidate.confidence_score or 50.0) / 100.0
    horizon = today + timedelta(days=horizon_days)

    created: list[m.Prediction] = []
    for cond in thesis.conditions:
        if cond.metric is None or cond.threshold is None:
            continue   # not measurable, so not a prediction

        # One open prediction per condition; re-running the pipeline must not
        # manufacture duplicates that would inflate the sample.
        exists = (
            session.query(m.Prediction)
            .filter(m.Prediction.candidate_id == candidate.id)
            .filter(m.Prediction.metric == cond.metric)
            .filter(m.Prediction.resolved_at.is_(None))
            .first()
        )
        if exists:
            continue

        prediction = m.Prediction(
            candidate_id=candidate.id,
            made_at=today,
            horizon_date=horizon,
            statement=cond.text,
            metric=cond.metric,
            predicted_value=cond.threshold,
            probability=probability,
            driving_signals=sorted(set(driving)),
        )
        session.add(prediction)
        created.append(prediction)

    return created


def resolve_due_predictions(
    session: Session, *, as_of: date | None = None
) -> dict[str, Any]:
    """Score every prediction whose horizon has arrived.

    Resolution reads the *current* state of the thesis condition the prediction
    came from. A condition that is unknown at the horizon is left unresolved
    rather than assumed - an unmeasurable outcome is not a failure, and
    recording it as one would make the system look worse than it is while
    corrupting the signal analysis.
    """
    today = as_of or date.today()
    due = (
        session.query(m.Prediction)
        .filter(m.Prediction.resolved_at.is_(None))
        .filter(m.Prediction.horizon_date <= today)
        .all()
    )

    resolved = skipped = 0
    for prediction in due:
        thesis = (
            session.query(m.Thesis)
            .filter(m.Thesis.candidate_id == prediction.candidate_id)
            .order_by(m.Thesis.created_at.desc())
            .first()
        )
        if thesis is None:
            skipped += 1
            continue

        condition = next(
            (c for c in thesis.conditions if c.metric == prediction.metric), None
        )
        if condition is None or condition.status not in RESOLVABLE_STATUSES:
            skipped += 1
            continue

        outcome = condition.status in ("holding", "at_risk")
        prediction.resolved_at = today
        prediction.resolved_correct = outcome
        prediction.brier_score = (prediction.probability - (1.0 if outcome else 0.0)) ** 2
        resolved += 1

    return {"due": len(due), "resolved": resolved, "unresolvable": skipped}


def load_resolved(session: Session) -> list[ResolvedPrediction]:
    """Read resolved predictions into the pure learning layer's shape."""
    rows = (
        session.query(m.Prediction)
        .filter(m.Prediction.resolved_at.isnot(None))
        .filter(m.Prediction.resolved_correct.isnot(None))
        .all()
    )
    return [
        ResolvedPrediction(
            prediction_id=r.id,
            candidate_id=r.candidate_id,
            made_at=r.made_at,
            horizon_date=r.horizon_date,
            probability=r.probability,
            outcome=bool(r.resolved_correct),
            driving_signals=list(r.driving_signals or []),
            metric=r.metric,
            predicted_value=r.predicted_value,
            actual_value=r.actual_value,
        )
        for r in rows
    ]


def learning_report(session: Session) -> dict[str, Any]:
    """Everything the system has learned, plus proposed weight changes.

    The recalibration is *proposed*, never applied automatically. Silently
    changing the scoring model would make historical scores incomparable
    without anyone noticing; the operator applies it deliberately or not at all.
    """
    resolved = load_resolved(session)
    report = build_report(resolved)

    payload = report.to_dict()
    payload["current_weights"] = {k.value: v for k, v in DEFAULT_WEIGHTS.items()}

    if report.sufficient_data:
        proposed, changelog = recalibrate_weights(
            {k.value: v for k, v in DEFAULT_WEIGHTS.items()},
            signal_performance(resolved),
        )
        payload["proposed_weights"] = proposed
        payload["recalibration_log"] = changelog
        payload["applied"] = False
        payload["note"] = (
            "Proposed only. Applying it changes how every future score is "
            "computed, so it is a deliberate operator action rather than an "
            "automatic one."
        )
    else:
        payload["proposed_weights"] = None
        payload["recalibration_log"] = []
        payload["applied"] = False
        payload["note"] = (
            "Not enough resolved predictions to justify changing the weights. "
            "They remain hand-chosen priors."
        )

    open_count = (
        session.query(m.Prediction).filter(m.Prediction.resolved_at.is_(None)).count()
    )
    payload["open_predictions"] = open_count
    return payload
