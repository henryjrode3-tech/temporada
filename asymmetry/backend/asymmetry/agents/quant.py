"""Deterministic agents: valuation/asymmetry, signals, management.

Valuation and signal detection do not call a language model at all. They are
arithmetic, and arithmetic delegated to a language model is arithmetic you
cannot trust. These agents implement the same interface as the others so the
pipeline treats them uniformly, but their ``run`` is pure computation.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ..core.finmath import implied_requirements
from ..core.scenarios import (
    build_scenario_set,
    default_scenarios,
    milestone_ladder,
)
from ..core.scoring import Dimension, DimensionScore, valuation_score_from_reverse
from ..core.signals import (
    SignalType,
    TimeSeriesPoint,
    aggregate_signal_score,
    detect_acceleration,
)
from ..llm.client import Tier
from .base import Agent, AgentResult, CandidateContext


class ValuationAgent(Agent):
    """Scenarios, reverse valuation, milestones and the asymmetry score.

    Entirely deterministic. The qualitative inputs it consumes (market size,
    margins) come from other agents; this agent's job is to turn them into
    numbers correctly and identically every time.
    """

    name = "valuation"
    tier = Tier.CHEAP
    dimension = Dimension.VALUATION

    def build_prompt(self, ctx: CandidateContext) -> str:  # pragma: no cover
        raise NotImplementedError("ValuationAgent is deterministic")

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:  # pragma: no cover
        return {}

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:  # pragma: no cover
        raise NotImplementedError

    def run(self, ctx: CandidateContext) -> AgentResult:
        market_cap = ctx.market_cap
        if not market_cap or market_cap <= 0:
            return AgentResult.failure(self.name, "no market capitalisation available")

        tam = ctx.tam_estimate or (ctx.revenue * 100 if ctx.revenue else None)
        if not tam or tam <= 0:
            return AgentResult.failure(self.name, "no market estimate available")

        years = float(ctx.extra.get("horizon_years", 10.0))
        margin = float(ctx.extra.get("assumed_net_margin", 0.15))
        exit_mult = float(ctx.extra.get("assumed_exit_multiple", 20.0))

        # Dilution history is the best available predictor of future dilution,
        # so use the observed rate rather than a flattering default.
        dilution = 0.05
        if ctx.shares_outstanding and ctx.shares_outstanding_prior:
            observed = ctx.shares_outstanding / ctx.shares_outstanding_prior - 1
            dilution = max(0.0, min(0.35, observed))

        scenario_set = build_scenario_set(
            default_scenarios(
                tam,
                current_revenue=ctx.revenue,
                net_margin=margin,
                exit_multiple=exit_mult,
                dilution_cagr=dilution,
            ),
            market_cap,
            years,
        )

        reverse = implied_requirements(
            market_cap, total_market=tam, net_margin=margin,
            exit_multiple=exit_mult, years=years,
        )
        ladder = milestone_ladder(market_cap, tam, margin, exit_mult, years)

        dim = valuation_score_from_reverse(
            reverse.required_market_share, scenario_set.payoff_ratio
        )

        return AgentResult(
            agent_name=self.name, ok=True, model="deterministic",
            dimension_score=dim,
            payload={
                "scenarios": scenario_set.to_dict(),
                "reverse_valuation": {
                    "required_revenue": reverse.required_revenue,
                    "required_market_share": reverse.required_market_share,
                    "total_market_assumed": reverse.total_market_assumed,
                    "net_margin_assumed": reverse.net_margin_assumed,
                    "exit_multiple_assumed": reverse.exit_multiple_assumed,
                    "years": reverse.years,
                    "verdict": reverse.verdict,
                    "share_is_implausible": reverse.share_is_implausible,
                },
                "milestones": [
                    {
                        "label": m.label, "target_market_cap": m.target_market_cap,
                        "reachable": m.reachable, "required_revenue": m.required_revenue,
                        "required_market_share": m.required_market_share,
                        "multiple_from_here": m.multiple_from_here,
                        "implied_cagr": m.implied_cagr, "commentary": m.commentary,
                    }
                    for m in ladder
                ],
                "asymmetry_score": scenario_set.asymmetry_score,
                "dilution_assumed": dilution,
            },
            narrative=reverse.verdict,
        )


class SignalAgent(Agent):
    """Detects acceleration across every available series (section 8).

    Deterministic. Whether a metric has broken from its baseline is a
    statistical question with a correct answer.
    """

    name = "signal"
    tier = Tier.CHEAP
    dimension = Dimension.EARLY_SIGNALS

    def build_prompt(self, ctx: CandidateContext) -> str:  # pragma: no cover
        raise NotImplementedError("SignalAgent is deterministic")

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:  # pragma: no cover
        return {}

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:  # pragma: no cover
        raise NotImplementedError

    def run(self, ctx: CandidateContext) -> AgentResult:
        series_map: dict[str, list[tuple[date, float]]] = ctx.extra.get("series", {})
        detected = []

        for name, points in series_map.items():
            try:
                stype = SignalType(name)
            except ValueError:
                continue
            ts = [TimeSeriesPoint(at=d, value=v) for d, v in points]
            sig = detect_acceleration(stype, ts, as_of=ctx.as_of)
            if sig:
                detected.append(sig)

        score = aggregate_signal_score(detected)
        return AgentResult(
            agent_name=self.name, ok=True, model="deterministic",
            dimension_score=DimensionScore(
                dimension=Dimension.EARLY_SIGNALS,
                score=score,
                rationale=(
                    f"{len(detected)} signal(s) across "
                    f"{len({s.signal_type for s in detected})} distinct metric(s)."
                    if detected else "No acceleration detected in available series."
                ),
                confidence=0.7 if detected else 0.5,
            ),
            payload={"signals": [s.to_dict() for s in detected]},
            narrative="; ".join(s.description for s in detected[:5]),
        )


class ManagementAgent(Agent):
    """Management quality. The lowest-weighted dimension, and deliberately so:
    it is the hardest to assess from public information without being swayed by
    charisma, which is precisely the bias this system exists to resist."""

    name = "management"
    tier = Tier.CHEAP
    dimension = Dimension.MANAGEMENT
    max_tokens = 900

    def build_prompt(self, ctx: CandidateContext) -> str:
        return f"""Assess management, using behaviour rather than biography.

{ctx.brief()}

Weight what they have DONE - milestones met or missed, capital allocation,
insider buying and selling, how candidly they describe setbacks - over
credentials or charisma.

JSON:
{{
  "track_record": "...",
  "capital_allocation": "...",
  "insider_alignment": "...",
  "candour": "high|moderate|low",
  "promotional_behaviour": bool,
  "concerns": ["..."],
  "management_score": 0-10,
  "confidence": 0.0-1.0,
  "rationale": "..."
}}"""

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        score = 5.0
        insider = ctx.extra.get("insider_ownership")
        if insider is not None:
            score += 1.5 if insider > 0.20 else 0.5 if insider > 0.10 else -0.5
        if ctx.hype_score > 50:
            score -= 2.0
        if any(f.get("code") == "MGMT_TURNOVER" for f in ctx.red_flags):
            score -= 2.0
        if any(f.get("code") == "MISSED_MILESTONES" for f in ctx.red_flags):
            score -= 1.5
        score = max(0.0, min(10.0, score))
        return {
            "track_record": "not assessed", "capital_allocation": "not assessed",
            "insider_alignment": (
                f"Insider ownership {insider:.0%}" if insider is not None else "unknown"
            ),
            "candour": "low" if ctx.hype_score > 50 else "moderate",
            "promotional_behaviour": ctx.hype_score > 50,
            "concerns": [f.get("title") for f in ctx.red_flags
                         if f.get("code") in {"MGMT_TURNOVER", "INSIDER_SELLING",
                                              "MISSED_MILESTONES", "RELATED_PARTY"}],
            "management_score": score, "confidence": 0.25,
            "rationale": "Heuristic from insider ownership, promotional language and flags.",
        }

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name, ok=True,
            dimension_score=self.score(
                data.get("management_score", 5),
                data.get("rationale", ""), data.get("confidence", 0.3),
            ),
            payload=data, narrative=str(data.get("track_record", ""))[:1000],
        )
