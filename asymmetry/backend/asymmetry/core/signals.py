"""Signal detection (section 18).

Finds *acceleration*: a metric breaking away from its own history. This is the
system's main edge, because acceleration in hiring, patents, repositories,
citations or contracts tends to precede the financial results that eventually
attract mainstream attention.

Two independent tests must agree before a signal is reported:

* **Magnitude** - the percentage change is large.
* **Significance** - the change is large relative to the metric's own volatility
  (a robust z-score).

A metric that always swings 300% has not done anything interesting by swinging
300% again. Requiring both tests is what separates a signal from noise.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Sequence


class SignalType(str, Enum):
    REVENUE_GROWTH = "revenue_growth"
    HIRING = "hiring"
    GITHUB_ACTIVITY = "github_activity"
    GITHUB_CONTRIBUTORS = "github_contributors"
    PATENT_FILINGS = "patent_filings"
    RESEARCH_CITATIONS = "research_citations"
    PUBLICATIONS = "publications"
    FUNDING = "funding"
    CUSTOMER_ANNOUNCEMENTS = "customer_announcements"
    PARTNERSHIPS = "partnerships"
    GOVERNMENT_CONTRACTS = "government_contracts"
    SEARCH_INTEREST = "search_interest"
    MANUFACTURING_CAPACITY = "manufacturing_capacity"
    COMMUNITY_ACTIVITY = "community_activity"


class SignalStrength(str, Enum):
    EXTREME = "extreme"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


#: Per-metric magnitude thresholds. Job postings are noisy and seasonal;
#: government contracts are rare and lumpy, so a smaller move means more.
DEFAULT_THRESHOLDS: dict[SignalType, float] = {
    SignalType.REVENUE_GROWTH: 0.30,
    SignalType.HIRING: 0.50,
    SignalType.GITHUB_ACTIVITY: 0.75,
    SignalType.GITHUB_CONTRIBUTORS: 0.50,
    SignalType.PATENT_FILINGS: 0.40,
    SignalType.RESEARCH_CITATIONS: 0.50,
    SignalType.PUBLICATIONS: 0.50,
    SignalType.FUNDING: 0.50,
    SignalType.CUSTOMER_ANNOUNCEMENTS: 0.30,
    SignalType.PARTNERSHIPS: 0.30,
    SignalType.GOVERNMENT_CONTRACTS: 0.25,
    SignalType.SEARCH_INTEREST: 1.00,
    SignalType.MANUFACTURING_CAPACITY: 0.30,
    SignalType.COMMUNITY_ACTIVITY: 0.60,
}

#: Minimum absolute level before a percentage change means anything. Going from
#: one contributor to four is a 300% increase and almost never important.
MIN_ABSOLUTE_BASE: dict[SignalType, float] = {
    SignalType.GITHUB_ACTIVITY: 20.0,
    SignalType.GITHUB_CONTRIBUTORS: 5.0,
    SignalType.HIRING: 5.0,
    SignalType.PATENT_FILINGS: 3.0,
    SignalType.RESEARCH_CITATIONS: 10.0,
    SignalType.PUBLICATIONS: 3.0,
    SignalType.CUSTOMER_ANNOUNCEMENTS: 2.0,
    SignalType.PARTNERSHIPS: 2.0,
    SignalType.GOVERNMENT_CONTRACTS: 1.0,
}


@dataclass
class TimeSeriesPoint:
    at: date
    value: float


@dataclass
class Signal:
    """A detected acceleration, with the arithmetic that produced it."""

    signal_type: SignalType
    strength: SignalStrength
    current_value: float
    baseline_value: float
    pct_change: float
    z_score: float
    window_label: str
    detected_at: date
    description: str
    is_significant: bool
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type.value,
            "strength": self.strength.value,
            "current_value": self.current_value,
            "baseline_value": self.baseline_value,
            "pct_change": round(self.pct_change, 4),
            "z_score": round(self.z_score, 3),
            "window_label": self.window_label,
            "detected_at": self.detected_at.isoformat(),
            "description": self.description,
            "is_significant": self.is_significant,
            "evidence": self.evidence,
        }


def robust_z_score(value: float, history: Sequence[float]) -> float:
    """Z-score using median and MAD rather than mean and standard deviation.

    A single historic spike inflates the standard deviation enough to hide the
    next spike; the median absolute deviation does not have that problem.
    """
    if len(history) < 3:
        return 0.0
    med = statistics.median(history)
    deviations = [abs(x - med) for x in history]
    mad = statistics.median(deviations)
    if mad < 1e-9:
        # No historical variation: fall back to standard deviation, and if the
        # series is genuinely constant any change is by definition notable.
        try:
            sd = statistics.stdev(history)
        except statistics.StatisticsError:
            return 0.0
        if sd < 1e-9:
            return 6.0 if abs(value - med) > 1e-9 else 0.0
        return (value - med) / sd
    # 1.4826 scales MAD to be a consistent estimator of sigma for normal data.
    return (value - med) / (1.4826 * mad)


def _classify(pct_change: float, z: float, threshold: float) -> SignalStrength:
    if pct_change >= threshold * 4 and z >= 3.0:
        return SignalStrength.EXTREME
    if pct_change >= threshold * 2 and z >= 2.0:
        return SignalStrength.STRONG
    if pct_change >= threshold and z >= 1.5:
        return SignalStrength.MODERATE
    if pct_change >= threshold * 0.5:
        return SignalStrength.WEAK
    return SignalStrength.NONE


def detect_acceleration(
    signal_type: SignalType,
    series: Sequence[TimeSeriesPoint],
    *,
    current_window: int = 3,
    baseline_window: int = 12,
    threshold: float | None = None,
    as_of: date | None = None,
) -> Signal | None:
    """Compare a recent window against a longer baseline.

    ``as_of`` truncates the series, which is how historical mode avoids
    hindsight leakage: the filter lives in the detector, not in a prompt.

    Returns ``None`` when nothing meaningful is happening - the common case,
    and reporting it as a weak signal would drown the real ones.
    """
    if not series:
        return None

    points = sorted(series, key=lambda p: p.at)
    if as_of:
        points = [p for p in points if p.at <= as_of]
    if len(points) < current_window + 3:
        return None

    thresh = threshold if threshold is not None else DEFAULT_THRESHOLDS.get(signal_type, 0.5)

    recent = [p.value for p in points[-current_window:]]
    prior = [p.value for p in points[:-current_window]]
    if not prior:
        return None

    baseline_slice = prior[-baseline_window:] if len(prior) > baseline_window else prior
    current_value = statistics.mean(recent)
    baseline_value = statistics.mean(baseline_slice)

    min_base = MIN_ABSOLUTE_BASE.get(signal_type, 0.0)
    if current_value < min_base:
        return None

    if baseline_value <= 1e-9:
        # Growth from nothing: real, but percentage change is undefined.
        pct_change = float("inf") if current_value > 0 else 0.0
        z = 6.0 if current_value > min_base else 0.0
    else:
        pct_change = (current_value / baseline_value) - 1.0
        z = robust_z_score(current_value, baseline_slice)

    strength = _classify(pct_change, z, thresh)
    if strength is SignalStrength.NONE:
        return None

    detected = as_of or points[-1].at
    pct_text = "from a zero baseline" if math.isinf(pct_change) else f"{pct_change*100:+.0f}%"
    description = (
        f"{signal_type.value.replace('_', ' ').title()} {pct_text} "
        f"({baseline_value:,.1f} to {current_value:,.1f}) over the last "
        f"{current_window} periods versus a {len(baseline_slice)}-period baseline."
    )

    return Signal(
        signal_type=signal_type,
        strength=strength,
        current_value=current_value,
        baseline_value=baseline_value,
        pct_change=0.0 if math.isinf(pct_change) else pct_change,
        z_score=z,
        window_label=f"{current_window}p vs {len(baseline_slice)}p",
        detected_at=detected,
        description=description,
        is_significant=strength in (SignalStrength.STRONG, SignalStrength.EXTREME),
        evidence={
            "recent_values": recent,
            "baseline_values": baseline_slice[-6:],
            "threshold_used": thresh,
            "grew_from_zero": math.isinf(pct_change),
        },
    )


STRENGTH_POINTS: dict[SignalStrength, float] = {
    SignalStrength.EXTREME: 10.0,
    SignalStrength.STRONG: 6.0,
    SignalStrength.MODERATE: 3.0,
    SignalStrength.WEAK: 1.0,
    SignalStrength.NONE: 0.0,
}


def aggregate_signal_score(signals: Sequence[Signal]) -> float:
    """Combine signals into a 0-10 dimension score.

    Rewards *diversity* over intensity. Five different metrics accelerating at
    once is a far stronger indication that something real is happening than one
    metric accelerating five times as hard - which is usually a data artefact.
    """
    if not signals:
        return 0.0

    by_type: dict[SignalType, float] = {}
    for s in signals:
        pts = STRENGTH_POINTS[s.strength]
        by_type[s.signal_type] = max(by_type.get(s.signal_type, 0.0), pts)

    total = sum(by_type.values())
    diversity_bonus = min(3.0, (len(by_type) - 1) * 0.75) if len(by_type) > 1 else 0.0
    # Compress: 20 raw points maps to roughly 7/10 before the diversity bonus.
    compressed = 10.0 * (1.0 - math.exp(-total / 12.0))
    return round(min(10.0, compressed + diversity_bonus), 2)
