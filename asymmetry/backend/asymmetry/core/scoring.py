"""Composite scoring.

Two rules govern this module:

1. **Nothing is hidden behind one number.** Every composite stores its
   components and the exact weights used, so any score can be taken apart.
2. **Magnitude and likelihood never mix.** ``asymmetry_score`` says how
   lopsided the payoff is; ``confidence_score`` says how much we trust the
   analysis. Averaging them would destroy the only distinction that matters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# --------------------------------------------------------------------------
# Dimensions
# --------------------------------------------------------------------------
class Dimension(str, Enum):
    TECHNOLOGY = "technology"
    MARKET = "market"
    GROWTH = "growth"
    COMPETITIVE_ADVANTAGE = "competitive_advantage"
    EARLY_SIGNALS = "early_signals"
    MANAGEMENT = "management"
    FINANCIAL_HEALTH = "financial_health"
    VALUATION = "valuation"
    FUTURE_UPSIDE = "future_upside"
    RISK = "risk"


#: Weights per section 11. A starting prior, not a conclusion - section 51
#: replaces these with empirically calibrated weights once enough predictions
#: have resolved. They are defined here, once, rather than scattered through
#: prompts, so that recalibration is a one-line change.
DEFAULT_WEIGHTS: dict[Dimension, float] = {
    Dimension.MARKET: 0.15,                 # future market size
    Dimension.TECHNOLOGY: 0.15,
    Dimension.COMPETITIVE_ADVANTAGE: 0.15,
    Dimension.EARLY_SIGNALS: 0.15,
    Dimension.VALUATION: 0.15,
    Dimension.GROWTH: 0.10,
    Dimension.FINANCIAL_HEALTH: 0.10,
    Dimension.MANAGEMENT: 0.05,
}

#: Deliberately excluded from the weighted average and reported alongside it.
#: Burying risk inside an average is how a dangerous candidate ends up looking
#: merely average.
STANDALONE_DIMENSIONS = {Dimension.RISK, Dimension.FUTURE_UPSIDE}


class ScoringError(ValueError):
    pass


def _validate_weights(weights: dict[Dimension, float]) -> None:
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-6:
        raise ScoringError(f"weights must sum to 1.0, got {total:.4f}")
    for dim in weights:
        if dim in STANDALONE_DIMENSIONS:
            raise ScoringError(f"{dim.value} must stay standalone, not weighted in")


@dataclass
class DimensionScore:
    """A single 0-10 judgement with its justification and provenance."""

    dimension: Dimension
    score: float                       # 0-10
    rationale: str = ""
    confidence: float = 0.5            # 0-1, how much we trust this judgement
    evidence_claim_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 10.0:
            raise ScoringError(f"{self.dimension.value} score must be 0-10, got {self.score}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ScoringError(f"confidence must be 0-1, got {self.confidence}")

    @property
    def is_evidenced(self) -> bool:
        """A judgement with no linked evidence is an opinion, and is labelled so."""
        return bool(self.evidence_claim_ids)


@dataclass
class CompositeScore:
    """A fully decomposable overall score.

    ``base_score`` is the weighted average before penalties, ``penalty`` is the
    red-flag deduction, and ``overall_score`` is the result. All three are
    stored so nothing is ever silently subtracted.
    """

    overall_score: float               # 0-100, after penalty
    base_score: float                  # 0-100, before penalty
    penalty: float                     # points deducted
    components: dict[str, float]       # dimension -> raw 0-10
    weights: dict[str, float]          # dimension -> weight used
    contributions: dict[str, float]    # dimension -> points contributed
    missing_dimensions: list[str]
    confidence_score: float            # 0-100, separate from magnitude
    penalty_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 2),
            "base_score": round(self.base_score, 2),
            "penalty": round(self.penalty, 2),
            "penalty_reasons": self.penalty_reasons,
            "components": {k: round(v, 2) for k, v in self.components.items()},
            "weights": self.weights,
            "contributions": {k: round(v, 2) for k, v in self.contributions.items()},
            "missing_dimensions": self.missing_dimensions,
            "confidence_score": round(self.confidence_score, 2),
        }


def compute_composite(
    dimension_scores: list[DimensionScore],
    *,
    weights: dict[Dimension, float] | None = None,
    penalty: float = 0.0,
    penalty_reasons: list[str] | None = None,
) -> CompositeScore:
    """Weighted composite on a 0-100 scale, with full decomposition retained.

    Missing dimensions are *renormalised over what is present* and listed
    explicitly, rather than being scored as zero. Absence of evidence is not
    evidence of badness, but it must be visible.
    """
    w = dict(weights or DEFAULT_WEIGHTS)
    _validate_weights(w)

    by_dim = {ds.dimension: ds for ds in dimension_scores}
    present = {d: wt for d, wt in w.items() if d in by_dim}
    missing = [d.value for d in w if d not in by_dim]

    if not present:
        raise ScoringError("no scoreable dimensions supplied")

    total_present_weight = sum(present.values())
    contributions: dict[str, float] = {}
    base = 0.0
    for dim, wt in present.items():
        normalised = wt / total_present_weight
        points = by_dim[dim].score * 10.0 * normalised   # 0-10 -> 0-100
        contributions[dim.value] = points
        base += points

    # Confidence is the evidence-weighted mean of per-dimension confidence,
    # then discounted for however much of the weight we could not assess.
    coverage = total_present_weight
    mean_conf = sum(by_dim[d].confidence * wt for d, wt in present.items()) / total_present_weight
    confidence = 100.0 * mean_conf * coverage

    overall = max(0.0, min(100.0, base - penalty))

    return CompositeScore(
        overall_score=overall,
        base_score=base,
        penalty=penalty,
        components={ds.dimension.value: ds.score for ds in dimension_scores},
        weights={d.value: round(wt, 4) for d, wt in w.items()},
        contributions=contributions,
        missing_dimensions=missing,
        confidence_score=confidence,
        penalty_reasons=penalty_reasons or [],
    )


# --------------------------------------------------------------------------
# Research verdicts - never "buy" (section 44)
# --------------------------------------------------------------------------
class Verdict(str, Enum):
    """Research statuses. There is deliberately no BUY, SELL, or HOLD."""

    TOP_OPPORTUNITY = "TOP_OPPORTUNITY"
    INVESTIGATE = "INVESTIGATE"
    WATCH = "WATCH"
    INTERESTING = "INTERESTING"
    HIGH_RISK = "HIGH_RISK"
    THESIS_WEAKENING = "THESIS_WEAKENING"
    THESIS_INVALIDATED = "THESIS_INVALIDATED"
    REJECTED = "REJECTED"


def assign_verdict(
    overall_score: float,
    asymmetry_score: float,
    risk_score: float,
    confidence_score: float,
    red_flag_score: float,
) -> tuple[Verdict, str]:
    """Translate the numbers into a research status and a reason.

    Ordering matters: disqualifying conditions are checked before flattering
    ones, so a high score cannot paper over serious red flags.
    """
    if red_flag_score >= 70:
        return Verdict.REJECTED, "Severe red flags outweigh any thesis."
    if overall_score < 30:
        return Verdict.REJECTED, "Fails on fundamentals across most dimensions."
    if risk_score >= 8.5 and confidence_score < 35:
        return (
            Verdict.HIGH_RISK,
            "Potentially interesting but the analysis is too uncertain to rank.",
        )
    if overall_score >= 75 and asymmetry_score >= 70:
        return (
            Verdict.TOP_OPPORTUNITY,
            "Strong across dimensions with a materially lopsided payoff.",
        )
    if asymmetry_score >= 70 and overall_score >= 55:
        return Verdict.INVESTIGATE, "Payoff asymmetry justifies deeper work."
    if overall_score >= 60:
        return Verdict.WATCH, "Solid but no clear asymmetry at today's price."
    if asymmetry_score >= 55:
        return Verdict.INTERESTING, "Lopsided payoff, weak supporting evidence so far."
    return Verdict.WATCH, "Insufficient evidence either way; monitoring."


# --------------------------------------------------------------------------
# Valuation attractiveness - derived, not vibes
# --------------------------------------------------------------------------
def valuation_score_from_reverse(
    required_market_share: float | None,
    payoff_ratio: float,
) -> DimensionScore:
    """Score valuation attractiveness from what today's price already assumes.

    This deliberately does not look at share price. A $2 stock is not cheap and
    a $200 stock is not expensive; what matters is how much of the future is
    already in the price.
    """
    if required_market_share is None:
        return DimensionScore(
            Dimension.VALUATION,
            5.0,
            "No independent market estimate; valuation attractiveness unknown.",
            confidence=0.2,
        )

    if required_market_share > 1.0:
        score, note = 0.5, "Price implies more than the entire estimated market."
    elif required_market_share > 0.40:
        score, note = 2.0, "Price assumes near-total dominance."
    elif required_market_share > 0.20:
        score, note = 4.0, "Price assumes a commanding position."
    elif required_market_share > 0.08:
        score, note = 6.0, "Price assumes meaningful but achievable share."
    elif required_market_share > 0.02:
        score, note = 8.0, "Price assumes modest share; room for upside surprise."
    else:
        score, note = 9.5, "Price embeds almost no future success."

    # A lopsided payoff nudges attractiveness up slightly, but cannot rescue a
    # valuation that already assumes perfection.
    if payoff_ratio > 5.0:
        score = min(10.0, score + 0.5)

    return DimensionScore(
        Dimension.VALUATION,
        score,
        f"{note} Implied requirement: {required_market_share:.1%} share.",
        confidence=0.6,
    )
