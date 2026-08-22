"""Alert rules (section 35).

Alerts fire on *changes*, not on states. "Asymmetry above 85" is a condition
that would fire every single run for the same candidate until it stopped being
true, which trains the reader to ignore alerts entirely. So each rule compares
the current observation against the previous one and fires only on the
transition.

Delivery is deliberately out of scope here: this module decides *what* is worth
saying. Where it goes - console, email, webhook - is the caller's problem, and
keeping that separation means the rules stay testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Callable


class AlertLevel(str, Enum):
    CRITICAL = "critical"   # act now: something broke
    HIGH = "high"
    INFO = "info"


@dataclass
class Alert:
    code: str
    level: AlertLevel
    candidate_id: str
    candidate_name: str
    title: str
    detail: str
    raised_at: date
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code, "level": self.level.value,
            "candidate_id": self.candidate_id, "candidate_name": self.candidate_name,
            "title": self.title, "detail": self.detail,
            "raised_at": self.raised_at.isoformat(), "evidence": self.evidence,
        }


@dataclass
class AlertThresholds:
    """Tunable trigger points. Defaults are conservative on purpose: an alert
    stream nobody reads is worse than no alerts, because it looks like coverage."""

    asymmetry_high: float = 75.0
    overall_high: float = 80.0
    top_n: int = 10
    rank_jump: int = 15
    risk_spike: float = 2.0          # points on the 0-10 risk scale
    red_flag_spike: float = 20.0     # points on the 0-100 red-flag scale
    revenue_acceleration: float = 0.25


@dataclass
class CandidateSnapshot:
    """The minimum needed to compare one run against the previous."""

    candidate_id: str
    name: str
    rank: int | None = None
    overall_score: float | None = None
    asymmetry_score: float | None = None
    risk_score: float | None = None
    red_flag_score: float | None = None
    verdict: str | None = None
    revenue_growth: float | None = None
    thesis_status: str | None = None
    new_significant_signals: list[dict[str, Any]] = field(default_factory=list)


AlertRule = Callable[[CandidateSnapshot, CandidateSnapshot, AlertThresholds], list[Alert]]


def _alert(code, level, cur, title, detail, when, **evidence) -> Alert:
    return Alert(code, level, cur.candidate_id, cur.name, title, detail, when, evidence)


def evaluate(
    previous: CandidateSnapshot | None,
    current: CandidateSnapshot,
    thresholds: AlertThresholds | None = None,
    when: date | None = None,
) -> list[Alert]:
    """Compare two snapshots and return whatever is genuinely new.

    A candidate with no previous snapshot only raises alerts for standing that
    is notable on its own; everything else needs a baseline to be a change.
    """
    t = thresholds or AlertThresholds()
    day = when or date.today()
    alerts: list[Alert] = []

    # ---- Thesis: the loudest thing the system can say ---------------------
    if current.thesis_status == "invalidated" and (
        previous is None or previous.thesis_status != "invalidated"
    ):
        alerts.append(_alert(
            "THESIS_INVALIDATED", AlertLevel.CRITICAL, current,
            "Thesis invalidated",
            f"The thesis for {current.name} no longer holds.", day,
        ))
    elif current.thesis_status == "weakening" and (
        previous is None or previous.thesis_status != "weakening"
    ):
        alerts.append(_alert(
            "THESIS_WEAKENING", AlertLevel.HIGH, current,
            "Thesis weakening",
            f"One or more monitored conditions for {current.name} have broken.", day,
        ))

    # ---- Risk transitions --------------------------------------------------
    if previous and current.red_flag_score is not None and previous.red_flag_score is not None:
        delta = current.red_flag_score - previous.red_flag_score
        if delta >= t.red_flag_spike:
            alerts.append(_alert(
                "RED_FLAG_SPIKE", AlertLevel.CRITICAL, current,
                "Red-flag score jumped",
                f"Red flags rose {delta:.0f} points to {current.red_flag_score:.0f}/100.",
                day, before=previous.red_flag_score, after=current.red_flag_score,
            ))

    if previous and current.risk_score is not None and previous.risk_score is not None:
        delta = current.risk_score - previous.risk_score
        if delta >= t.risk_spike:
            alerts.append(_alert(
                "RISK_SPIKE", AlertLevel.HIGH, current, "Risk assessment worsened",
                f"Risk rose {delta:.1f} to {current.risk_score:.1f}/10.", day,
                before=previous.risk_score, after=current.risk_score,
            ))

    if current.verdict == "REJECTED" and previous and previous.verdict != "REJECTED":
        alerts.append(_alert(
            "NOW_REJECTED", AlertLevel.CRITICAL, current, "Candidate rejected",
            f"{current.name} moved from {previous.verdict} to REJECTED.", day,
        ))

    # ---- Ranking transitions ----------------------------------------------
    entered_top = (
        current.rank is not None and current.rank <= t.top_n
        and (previous is None or previous.rank is None or previous.rank > t.top_n)
    )
    if entered_top:
        alerts.append(_alert(
            "ENTERED_TOP", AlertLevel.HIGH, current,
            f"Entered the top {t.top_n}",
            f"{current.name} is now ranked #{current.rank}.", day,
            rank=current.rank, previous_rank=previous.rank if previous else None,
        ))

    left_top = (
        previous is not None and previous.rank is not None and previous.rank <= t.top_n
        and (current.rank is None or current.rank > t.top_n)
    )
    if left_top:
        alerts.append(_alert(
            "LEFT_TOP", AlertLevel.INFO, current, f"Left the top {t.top_n}",
            f"{current.name} moved from #{previous.rank} to "
            + (f"#{current.rank}." if current.rank else "unranked."), day,
        ))

    if previous and previous.rank and current.rank:
        jump = previous.rank - current.rank
        if abs(jump) >= t.rank_jump:
            alerts.append(_alert(
                "LARGE_RANK_MOVE", AlertLevel.INFO, current,
                "Large rank movement",
                f"{current.name} moved {'up' if jump > 0 else 'down'} {abs(jump)} "
                f"places (#{previous.rank} to #{current.rank}).", day,
                delta=jump,
            ))

    # ---- Score thresholds, on crossing only -------------------------------
    def crossed(now: float | None, before: float | None, level: float) -> bool:
        return now is not None and now >= level and (before is None or before < level)

    if crossed(current.asymmetry_score, previous.asymmetry_score if previous else None,
               t.asymmetry_high):
        alerts.append(_alert(
            "ASYMMETRY_HIGH", AlertLevel.HIGH, current,
            "Asymmetry crossed threshold",
            f"Asymmetry reached {current.asymmetry_score:.0f}/100.", day,
            score=current.asymmetry_score,
        ))

    if crossed(current.overall_score, previous.overall_score if previous else None,
               t.overall_high):
        alerts.append(_alert(
            "SCORE_HIGH", AlertLevel.HIGH, current, "Overall score crossed threshold",
            f"Overall score reached {current.overall_score:.0f}/100.", day,
            score=current.overall_score,
        ))

    # ---- Fundamentals and signals -----------------------------------------
    if previous and current.revenue_growth is not None and previous.revenue_growth is not None:
        delta = current.revenue_growth - previous.revenue_growth
        if delta >= t.revenue_acceleration:
            alerts.append(_alert(
                "REVENUE_ACCELERATION", AlertLevel.HIGH, current,
                "Revenue growth accelerating",
                f"Growth rose from {previous.revenue_growth:.0%} to "
                f"{current.revenue_growth:.0%}.", day,
                before=previous.revenue_growth, after=current.revenue_growth,
            ))

    for signal in current.new_significant_signals:
        alerts.append(_alert(
            "SIGNAL_DETECTED", AlertLevel.INFO, current,
            f"New {signal.get('strength', '')} signal".strip(),
            signal.get("description", ""), day,
            signal_type=signal.get("signal_type"),
        ))

    return alerts


LEVEL_ORDER = {AlertLevel.CRITICAL: 0, AlertLevel.HIGH: 1, AlertLevel.INFO: 2}


def sort_alerts(alerts: list[Alert]) -> list[Alert]:
    """Most severe first, so a truncated list still carries the worst news."""
    return sorted(alerts, key=lambda a: (LEVEL_ORDER[a.level], a.candidate_name))
