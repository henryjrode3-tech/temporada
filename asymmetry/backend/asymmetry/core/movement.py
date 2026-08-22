"""Score-movement explanation (section 13).

Answers "this was ranked #2 six months ago and is #17 now - why?" by diffing
consecutive score snapshots and attributing the change to the dimensions that
actually moved.

This is only possible because scores are append-only and each snapshot carries
its own weights: attribution needs the weights that were in force at the time,
not today's. Recomputing an old score through a recalibrated model would
manufacture an explanation for a change that never happened.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: A dimension has to move by more than this (0-10 scale) to be worth naming.
#: Below it, the movement is noise from model temperature rather than a change
#: in the world, and reporting it would train the reader to ignore explanations.
MATERIAL_DELTA = 0.5


@dataclass
class DimensionChange:
    dimension: str
    before: float
    after: float
    weight: float
    points_contributed: float   # effect on the 0-100 composite

    @property
    def delta(self) -> float:
        return self.after - self.before

    @property
    def direction(self) -> str:
        return "improved" if self.delta > 0 else "deteriorated"

    def describe(self) -> str:
        return (
            f"{self.dimension.replace('_', ' ')} {self.direction} "
            f"{self.before:.1f} to {self.after:.1f} "
            f"({self.points_contributed:+.1f} points)"
        )


@dataclass
class MovementExplanation:
    """Why a candidate's standing changed."""

    rank_before: int | None
    rank_after: int | None
    score_before: float
    score_after: float
    asymmetry_before: float | None
    asymmetry_after: float | None
    changes: list[DimensionChange] = field(default_factory=list)
    penalty_before: float = 0.0
    penalty_after: float = 0.0
    new_penalties: list[str] = field(default_factory=list)
    resolved_penalties: list[str] = field(default_factory=list)
    verdict_before: str | None = None
    verdict_after: str | None = None
    summary: str = ""

    @property
    def rank_delta(self) -> int | None:
        if self.rank_before is None or self.rank_after is None:
            return None
        return self.rank_before - self.rank_after   # positive = moved up

    @property
    def score_delta(self) -> float:
        return self.score_after - self.score_before

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank_before": self.rank_before, "rank_after": self.rank_after,
            "rank_delta": self.rank_delta,
            "score_before": round(self.score_before, 2),
            "score_after": round(self.score_after, 2),
            "score_delta": round(self.score_delta, 2),
            "asymmetry_before": self.asymmetry_before,
            "asymmetry_after": self.asymmetry_after,
            "verdict_before": self.verdict_before, "verdict_after": self.verdict_after,
            "penalty_before": round(self.penalty_before, 2),
            "penalty_after": round(self.penalty_after, 2),
            "new_penalties": self.new_penalties,
            "resolved_penalties": self.resolved_penalties,
            "changes": [
                {"dimension": c.dimension, "before": round(c.before, 2),
                 "after": round(c.after, 2), "delta": round(c.delta, 2),
                 "weight": c.weight, "points": round(c.points_contributed, 2),
                 "description": c.describe()}
                for c in self.changes
            ],
            "summary": self.summary,
        }


def explain_movement(
    before: dict[str, Any],
    after: dict[str, Any],
) -> MovementExplanation:
    """Diff two score snapshots.

    Each snapshot is expected to carry ``components``, ``weights``,
    ``overall_score``, and optionally ``penalty``, ``penalty_reasons``,
    ``rank``, ``asymmetry_score`` and ``verdict``.

    Attribution uses the *earlier* snapshot's weights, since that is the model
    that produced the earlier score; a change in the weighting scheme is a
    change in the model, not in the candidate, and conflating them would credit
    a company for a recalibration it had nothing to do with.
    """
    comp_before = before.get("components") or {}
    comp_after = after.get("components") or {}
    weights = before.get("weights") or after.get("weights") or {}

    changes: list[DimensionChange] = []
    for dim in sorted(set(comp_before) | set(comp_after)):
        b = comp_before.get(dim)
        a = comp_after.get(dim)
        if b is None or a is None:
            continue     # a dimension appearing or vanishing is a coverage change
        if abs(a - b) < MATERIAL_DELTA:
            continue
        w = float(weights.get(dim, 0.0))
        changes.append(DimensionChange(
            dimension=dim, before=float(b), after=float(a), weight=w,
            points_contributed=(float(a) - float(b)) * 10.0 * w,
        ))

    changes.sort(key=lambda c: -abs(c.points_contributed))

    reasons_before = set(before.get("penalty_reasons") or [])
    reasons_after = set(after.get("penalty_reasons") or [])

    exp = MovementExplanation(
        rank_before=before.get("rank"), rank_after=after.get("rank"),
        score_before=float(before.get("overall_score") or 0.0),
        score_after=float(after.get("overall_score") or 0.0),
        asymmetry_before=before.get("asymmetry_score"),
        asymmetry_after=after.get("asymmetry_score"),
        changes=changes,
        penalty_before=float(before.get("penalty") or 0.0),
        penalty_after=float(after.get("penalty") or 0.0),
        new_penalties=sorted(reasons_after - reasons_before),
        resolved_penalties=sorted(reasons_before - reasons_after),
        verdict_before=before.get("verdict"), verdict_after=after.get("verdict"),
    )
    exp.summary = _summarise(exp)
    return exp


def _summarise(exp: MovementExplanation) -> str:
    """One or two sentences a person can read without decoding a table."""
    parts: list[str] = []

    delta = exp.rank_delta
    if delta is not None and delta != 0:
        parts.append(
            f"Moved {'up' if delta > 0 else 'down'} {abs(delta)} "
            f"place{'s' if abs(delta) != 1 else ''} "
            f"(#{exp.rank_before} to #{exp.rank_after})."
        )
    elif abs(exp.score_delta) >= 1.0:
        parts.append(
            f"Score {'rose' if exp.score_delta > 0 else 'fell'} "
            f"{abs(exp.score_delta):.1f} points."
        )

    if exp.changes:
        drivers = [c for c in exp.changes[:2]]
        parts.append("Driven by " + " and ".join(c.describe() for c in drivers) + ".")
    elif not exp.new_penalties and not exp.resolved_penalties:
        # Movement with no dimension change means other candidates moved, which
        # is a materially different fact and worth saying explicitly.
        if delta:
            parts.append(
                "No material change in this candidate's own scores; the movement "
                "reflects changes in other candidates."
            )

    if exp.new_penalties:
        parts.append("New red flags: " + ", ".join(exp.new_penalties[:3]) + ".")
    if exp.resolved_penalties:
        parts.append("Resolved: " + ", ".join(exp.resolved_penalties[:3]) + ".")

    if exp.verdict_before and exp.verdict_after and exp.verdict_before != exp.verdict_after:
        parts.append(f"Verdict changed from {exp.verdict_before} to {exp.verdict_after}.")

    return " ".join(parts) or "No material change."
