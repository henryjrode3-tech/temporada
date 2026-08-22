"""LLM access layer: tiering, caching, cost ceilings, structured output.

Three responsibilities:

1. **Cost control (section 43).** Cheap models screen, expensive models only
   analyse survivors. A hard per-run ceiling raises rather than overspends -
   an unbounded agent loop is a financial risk, not merely a bug.
2. **Determinism where possible.** Identical prompts return cached results, so
   re-running the pipeline is nearly free and agent behaviour is reproducible.
3. **Graceful degradation.** With no API key the platform still runs end to end
   using deterministic heuristics, clearly labelled as such so heuristic output
   is never mistaken for model reasoning.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from ..config import get_settings

log = logging.getLogger(__name__)


class Tier(str, Enum):
    """Which model class a call deserves."""

    CHEAP = "cheap"     # screening, extraction, deduplication
    DEEP = "deep"       # multi-agent analysis
    JUDGE = "judge"     # final synthesis and adjudication


#: Approximate USD per million tokens, used for budget accounting. Rough
#: figures are sufficient: the purpose is to stop runaway spend, not to
#: reproduce a billing statement.
PRICING: dict[Tier, tuple[float, float]] = {
    Tier.CHEAP: (1.0, 5.0),
    Tier.DEEP: (3.0, 15.0),
    Tier.JUDGE: (15.0, 75.0),
}


class BudgetExceeded(RuntimeError):
    """Raised when a run would exceed its configured spend ceiling."""


class LLMUnavailable(RuntimeError):
    pass


@dataclass
class LLMResponse:
    text: str
    model: str
    tier: Tier
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    cache_hit: bool = False
    is_heuristic: bool = False

    @property
    def output_hash(self) -> str:
        return hashlib.sha256(self.text.encode()).hexdigest()[:16]


@dataclass
class BudgetTracker:
    """Per-run spend and call accounting."""

    max_cost_usd: float
    max_calls: int
    spent_usd: float = 0.0
    calls: int = 0
    cache_hits: int = 0
    tokens_in: int = 0
    tokens_out: int = 0

    def check(self, projected: float = 0.0) -> None:
        if self.calls >= self.max_calls:
            raise BudgetExceeded(f"call ceiling reached ({self.max_calls})")
        if self.spent_usd + projected > self.max_cost_usd:
            raise BudgetExceeded(
                f"cost ceiling reached (${self.spent_usd:.3f} of ${self.max_cost_usd:.2f})"
            )

    def record(self, resp: LLMResponse) -> None:
        self.calls += 1
        self.spent_usd += resp.cost_usd
        self.tokens_in += resp.tokens_in
        self.tokens_out += resp.tokens_out
        if resp.cache_hit:
            self.cache_hits += 1

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.max_cost_usd - self.spent_usd)

    def summary(self) -> dict[str, Any]:
        return {
            "calls": self.calls, "cache_hits": self.cache_hits,
            "spent_usd": round(self.spent_usd, 4),
            "remaining_usd": round(self.remaining_usd, 4),
            "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
        }


class ResponseCache:
    """Content-addressed in-memory cache.

    Keyed on the full request so a changed prompt is a different entry. Swap for
    Redis or a table when running across processes; the interface is small
    enough that doing so is a drop-in change.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    @staticmethod
    def key(model: str, system: str, prompt: str, temperature: float) -> str:
        blob = json.dumps([model, system, prompt, temperature], sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


def extract_json(text: str) -> Any:
    """Pull a JSON value out of a model response.

    Models wrap JSON in prose and code fences with some regularity, so this
    tries progressively more forgiving strategies before giving up.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("empty response")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"no JSON found in response: {text[:200]!r}")


class LLMClient:
    """Anthropic wrapper with tiering, caching, retries and budget enforcement."""

    def __init__(self, budget: BudgetTracker | None = None, cache: ResponseCache | None = None) -> None:
        self.settings = get_settings()
        self.cache = cache or ResponseCache()
        self.budget = budget or BudgetTracker(
            max_cost_usd=self.settings.max_cost_per_run_usd,
            max_calls=self.settings.max_llm_calls_per_run,
        )
        self._client = None

    @property
    def available(self) -> bool:
        return self.settings.llm_available

    def model_for(self, tier: Tier) -> str:
        return {
            Tier.CHEAP: self.settings.model_cheap,
            Tier.DEEP: self.settings.model_deep,
            Tier.JUDGE: self.settings.model_judge,
        }[tier]

    def _anthropic(self):
        if self._client is None:
            if not self.available:
                raise LLMUnavailable("no ANTHROPIC_API_KEY configured")
            import anthropic

            self._client = anthropic.Anthropic(
                api_key=self.settings.anthropic_api_key,
                timeout=self.settings.llm_timeout_seconds,
                max_retries=0,   # retries handled here, with backoff
            )
        return self._client

    def complete(
        self,
        prompt: str,
        *,
        tier: Tier = Tier.CHEAP,
        system: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.2,
        heuristic: Callable[[], str] | None = None,
    ) -> LLMResponse:
        """Run a completion, or fall back to ``heuristic`` when unavailable.

        ``heuristic`` keeps the pipeline working without an API key. Its output
        is flagged ``is_heuristic`` so the UI can distinguish deterministic
        stand-ins from genuine model reasoning.
        """
        model = self.model_for(tier)

        if self.settings.llm_cache_enabled:
            key = ResponseCache.key(model, system, prompt, temperature)
            cached = self.cache.get(key)
            if cached is not None:
                resp = LLMResponse(cached, model, tier, cache_hit=True)
                self.budget.record(resp)
                return resp

        if not self.available:
            if heuristic is None:
                raise LLMUnavailable(
                    "no API key and no heuristic fallback supplied for this call"
                )
            text = heuristic()
            return LLMResponse(text, "heuristic", tier, is_heuristic=True)

        rate_in, rate_out = PRICING[tier]
        self.budget.check(projected=(len(prompt) / 4 * rate_in + max_tokens * rate_out) / 1e6)

        last_error: Exception | None = None
        for attempt in range(self.settings.llm_max_retries):
            started = time.monotonic()
            try:
                client = self._anthropic()
                kwargs: dict[str, Any] = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [{"role": "user", "content": prompt}],
                }
                if system:
                    kwargs["system"] = system
                msg = client.messages.create(**kwargs)

                text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
                tin = getattr(msg.usage, "input_tokens", 0)
                tout = getattr(msg.usage, "output_tokens", 0)
                resp = LLMResponse(
                    text=text, model=model, tier=tier,
                    tokens_in=tin, tokens_out=tout,
                    cost_usd=(tin * rate_in + tout * rate_out) / 1e6,
                    latency_ms=int((time.monotonic() - started) * 1000),
                )
                self.budget.record(resp)
                if self.settings.llm_cache_enabled:
                    self.cache.set(ResponseCache.key(model, system, prompt, temperature), text)
                return resp

            except BudgetExceeded:
                raise
            except Exception as exc:   # network, rate limit, overload
                last_error = exc
                if attempt < self.settings.llm_max_retries - 1:
                    time.sleep(min(2 ** attempt, 8))
                    continue

        if heuristic is not None:
            log.warning("LLM failed after retries (%s); using heuristic", last_error)
            return LLMResponse(heuristic(), "heuristic", tier, is_heuristic=True)
        raise LLMUnavailable(f"LLM call failed after retries: {last_error}")

    def complete_json(
        self,
        prompt: str,
        *,
        tier: Tier = Tier.CHEAP,
        system: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.2,
        heuristic: Callable[[], Any] | None = None,
        validator: Callable[[Any], bool] | None = None,
    ) -> tuple[Any, LLMResponse]:
        """Completion that must yield JSON, retried once on malformed output."""
        heur_text = (lambda: json.dumps(heuristic())) if heuristic else None

        resp = self.complete(
            prompt, tier=tier, system=system, max_tokens=max_tokens,
            temperature=temperature, heuristic=heur_text,
        )
        try:
            data = extract_json(resp.text)
            if validator and not validator(data):
                raise ValueError("response failed schema validation")
            return data, resp
        except (ValueError, json.JSONDecodeError) as exc:
            if resp.is_heuristic:
                raise
            retry = self.complete(
                f"{prompt}\n\nYour previous reply could not be parsed ({exc}). "
                f"Reply with valid JSON only. No prose, no code fences.",
                tier=tier, system=system, max_tokens=max_tokens,
                temperature=0.0, heuristic=heur_text,
            )
            data = extract_json(retry.text)
            if validator and not validator(data):
                raise ValueError("response failed schema validation after retry")
            return data, retry
