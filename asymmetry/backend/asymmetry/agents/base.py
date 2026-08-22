"""Agent framework.

Each agent is a narrow specialist with one job, a strict output contract, and a
deterministic fallback. The base class handles budget, caching, validation,
error isolation and audit logging so individual agents stay small enough to
read in one sitting.

Two rules that shape the design:

* **An agent that fails must not abort the pipeline.** Its dimension is recorded
  as missing, and the composite score renormalises over what remains rather
  than silently scoring the gap as zero.
* **Every agent must be able to run without an API key.** The heuristic path is
  not a toy: it derives its judgements from the same structured data the model
  would see, and its output is labelled so nobody mistakes it for reasoning.
"""

from __future__ import annotations

import abc
import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..core.scoring import Dimension, DimensionScore
from ..llm.client import BudgetExceeded, LLMClient, LLMResponse, Tier

log = logging.getLogger(__name__)


@dataclass
class CandidateContext:
    """Everything an agent may look at, assembled once and shared.

    Passing a frozen context rather than a live database session keeps agents
    honest: they cannot wander off and query whatever they like, so the as-of
    cutoff applied when the context was built cannot be circumvented.
    """

    candidate_id: str
    name: str
    ticker: str | None
    sector: str | None
    industry: str | None
    description: str
    asset_type: str = "public_company"

    market_cap: float | None = None
    revenue: float | None = None
    revenue_prior: float | None = None
    revenue_growth: float | None = None
    gross_margin: float | None = None
    free_cash_flow: float | None = None
    cash: float | None = None
    debt: float | None = None
    shares_outstanding: float | None = None
    shares_outstanding_prior: float | None = None

    tam_estimate: float | None = None
    signals: list[dict[str, Any]] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    red_flags: list[dict[str, Any]] = field(default_factory=list)
    hype_score: float = 0.0
    as_of: date | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def brief(self) -> str:
        """Compact factual summary used in prompts.

        Deliberately terse and numeric. Long prose in a prompt invites the model
        to reason about the narrative rather than the figures.
        """
        def money(v: float | None) -> str:
            if v is None:
                return "unknown"
            for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
                if abs(v) >= div:
                    return f"${v/div:,.2f}{unit}"
            return f"${v:,.0f}"

        lines = [
            f"Name: {self.name}" + (f" ({self.ticker})" if self.ticker else ""),
            f"Type: {self.asset_type} | Sector: {self.sector or 'unknown'}"
            f" | Industry: {self.industry or 'unknown'}",
            f"Description: {self.description}",
            f"Market cap: {money(self.market_cap)} | Revenue: {money(self.revenue)}"
            f" | Revenue growth: {f'{self.revenue_growth:.1%}' if self.revenue_growth is not None else 'unknown'}",
            f"Gross margin: {f'{self.gross_margin:.1%}' if self.gross_margin is not None else 'unknown'}"
            f" | FCF: {money(self.free_cash_flow)} | Cash: {money(self.cash)} | Debt: {money(self.debt)}",
        ]
        if self.shares_outstanding and self.shares_outstanding_prior:
            growth = self.shares_outstanding / self.shares_outstanding_prior - 1
            lines.append(f"Share count change YoY: {growth:+.1%}")
        if self.tam_estimate:
            lines.append(f"Independent market estimate: {money(self.tam_estimate)}")
        if self.signals:
            lines.append("Detected signals: " + "; ".join(
                f"{s.get('signal_type')} {s.get('strength')} ({s.get('pct_change', 0)*100:+.0f}%)"
                for s in self.signals[:8]))
        if self.red_flags:
            lines.append("Red flags: " + "; ".join(
                f"{f.get('title')} [{f.get('severity')}]" for f in self.red_flags[:8]))
        if self.competitors:
            lines.append("Known competitors: " + ", ".join(self.competitors[:10]))
        if self.as_of:
            lines.append(
                f"IMPORTANT: analysis date is {self.as_of.isoformat()}. "
                f"Use only information available on or before that date."
            )
        return "\n".join(lines)


@dataclass
class AgentResult:
    """What an agent returns, plus how much it cost to get it."""

    agent_name: str
    ok: bool
    dimension_score: DimensionScore | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    narrative: str = ""
    error: str | None = None
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    cache_hit: bool = False
    is_heuristic: bool = False
    output_hash: str | None = None

    @classmethod
    def failure(cls, agent_name: str, error: str) -> "AgentResult":
        return cls(agent_name=agent_name, ok=False, error=error)


class Agent(abc.ABC):
    """Base class for every specialist."""

    name: str = "agent"
    tier: Tier = Tier.CHEAP
    dimension: Dimension | None = None
    max_tokens: int = 1200
    temperature: float = 0.2
    system_prompt: str = (
        "You are a rigorous, sceptical research analyst. You care about evidence, "
        "not narrative. You distinguish what is measured from what is asserted. "
        "You never recommend buying or selling anything; you produce research "
        "findings. When evidence is thin you say so plainly rather than "
        "manufacturing confidence. Reply with valid JSON only."
    )

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    # ---- to implement -----------------------------------------------------
    @abc.abstractmethod
    def build_prompt(self, ctx: CandidateContext) -> str:
        ...

    @abc.abstractmethod
    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        """Deterministic fallback. Must return the same shape as the model."""

    @abc.abstractmethod
    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        """Turn validated JSON into a result."""

    def validate(self, data: Any) -> bool:
        return isinstance(data, dict)

    # ---- execution --------------------------------------------------------
    def run(self, ctx: CandidateContext) -> AgentResult:
        """Execute, isolating every failure mode from the caller."""
        started = time.monotonic()
        try:
            data, resp = self.llm.complete_json(
                self.build_prompt(ctx),
                tier=self.tier,
                system=self.system_prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                heuristic=lambda: self.heuristic(ctx),
                validator=self.validate,
            )
        except BudgetExceeded as exc:
            # Budget exhaustion is a control decision, not an error: fall back
            # to the deterministic path so the pipeline still completes.
            log.warning("%s: budget exceeded (%s); using heuristic", self.name, exc)
            data = self.heuristic(ctx)
            resp = LLMResponse("", "heuristic", self.tier, is_heuristic=True)
        except Exception as exc:
            log.exception("%s failed for %s", self.name, ctx.name)
            return AgentResult.failure(self.name, f"{type(exc).__name__}: {exc}")

        try:
            result = self.interpret(data, ctx)
        except Exception as exc:
            log.exception("%s could not interpret output for %s", self.name, ctx.name)
            return AgentResult.failure(self.name, f"interpret failed: {exc}")

        result.model = resp.model
        result.tokens_in = resp.tokens_in
        result.tokens_out = resp.tokens_out
        result.cost_usd = resp.cost_usd
        result.cache_hit = resp.cache_hit
        result.is_heuristic = resp.is_heuristic
        result.output_hash = resp.output_hash
        result.latency_ms = int((time.monotonic() - started) * 1000)
        return result

    # ---- helpers ----------------------------------------------------------
    @staticmethod
    def clamp_score(value: Any, default: float = 5.0) -> float:
        """Coerce a model-supplied score into 0-10.

        Models return "7/10", "7.5", or occasionally 75. Clamping rather than
        raising keeps one malformed field from discarding an otherwise useful
        analysis.
        """
        try:
            v = float(str(value).split("/")[0].strip())
        except (TypeError, ValueError):
            return default
        if v > 10:
            v = v / 10 if v <= 100 else 10.0
        return max(0.0, min(10.0, v))

    @staticmethod
    def clamp_confidence(value: Any, default: float = 0.5) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return default
        if v > 1:
            v = v / 100
        return max(0.0, min(1.0, v))

    def score(
        self, value: Any, rationale: str, confidence: Any = 0.5,
        evidence: list[str] | None = None,
    ) -> DimensionScore | None:
        if self.dimension is None:
            return None
        return DimensionScore(
            dimension=self.dimension,
            score=self.clamp_score(value),
            rationale=str(rationale)[:2000],
            confidence=self.clamp_confidence(confidence),
            evidence_claim_ids=evidence or [],
        )
