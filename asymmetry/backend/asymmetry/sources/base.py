"""Source interface (section 15).

Every external feed implements the same contract, so adding a source never
requires touching the pipeline. Sources are declarative about their own
trustworthiness and rate limits, and the framework enforces both.

Legal and ethical constraints are part of the interface rather than a matter of
individual diligence: a source declares whether it is an official API, states
its rate limit, and the fetcher honours it. Sources that would require evading
access controls are not implemented; the register of what was excluded and why
is in ``sources/__init__.py`` and is printed by ``asymmetry sources``.
"""

from __future__ import annotations

import abc
import hashlib
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import IntEnum
from typing import Any, Iterable


class SourceTier(IntEnum):
    """Evidence hierarchy from section 41. Lower is more authoritative."""

    GOVERNMENT = 1      # SEC, EDGAR, DOE, NIH, patents, peer-reviewed research
    COMPANY_OFFICIAL = 2  # filings, investor decks, official announcements
    REPUTABLE_PRESS = 3
    INDUSTRY_PRESS = 4
    SOCIAL = 5          # forums, social media - discovery only, never evidence

    @property
    def default_reliability(self) -> float:
        return {1: 0.95, 2: 0.80, 3: 0.65, 4: 0.45, 5: 0.20}[int(self)]

    @property
    def is_citable_evidence(self) -> bool:
        """Tier 5 may surface a lead but can never substantiate a claim."""
        return int(self) <= 4


@dataclass
class RawDoc:
    """One document retrieved from a source, before interpretation.

    ``published_at`` is the field the whole temporal design depends on. A
    document without one can still be stored, but it is invisible to historical
    mode, because there is no way to prove it predates a cutoff.
    """

    external_id: str
    title: str
    body: str
    url: str | None = None
    published_at: date | None = None
    author: str | None = None
    entities: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(f"{self.external_id}|{self.title}|{self.body}".encode()).hexdigest()[:16]

    @property
    def is_dated(self) -> bool:
        return self.published_at is not None


@dataclass
class FetchResult:
    docs: list[RawDoc]
    source_name: str
    fetched_at: datetime
    query: str | None = None
    error: str | None = None
    from_cache: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None


class RateLimiter:
    """Minimal in-process rate limiter.

    Public data sources are a shared resource and several of them (the SEC most
    notably) will ban a client that ignores their published limits, so this is
    a correctness concern rather than politeness.
    """

    def __init__(self, per_hour: int) -> None:
        self.min_interval = 3600.0 / per_hour if per_hour > 0 else 0.0
        self._last: float = 0.0

    def wait(self) -> None:
        if self.min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last = time.monotonic()


class Source(abc.ABC):
    """Base class for every data source."""

    name: str = "unnamed"
    source_type: str = "generic"
    url: str = ""
    tier: SourceTier = SourceTier.INDUSTRY_PRESS
    rate_limit_per_hour: int = 600
    requires_api_key: bool = False
    #: Set False for anything that would need access controls circumvented.
    #: Such sources are simply not implemented.
    is_publicly_permitted: bool = True

    def __init__(self) -> None:
        self._limiter = RateLimiter(self.rate_limit_per_hour)

    @property
    def reliability_score(self) -> float:
        return self.tier.default_reliability

    @abc.abstractmethod
    def fetch(self, query: str, *, limit: int = 25, as_of: date | None = None) -> list[dict[str, Any]]:
        """Retrieve raw payloads. Implementations must honour ``as_of``."""

    @abc.abstractmethod
    def parse(self, payload: dict[str, Any]) -> RawDoc | None:
        """Turn one raw payload into a :class:`RawDoc`, or ``None`` to skip it."""

    def search(self, query: str, *, limit: int = 25, as_of: date | None = None) -> FetchResult:
        """Fetch, parse, and enforce the temporal cutoff.

        The cutoff is applied here, after parsing, as a second line of defence:
        a source implementation that forgets to filter still cannot leak future
        documents into historical mode.
        """
        started = datetime.now(timezone.utc)
        if not self.is_publicly_permitted:
            return FetchResult([], self.name, started, query,
                               error="Source not permitted for automated access.")
        try:
            self._limiter.wait()
            payloads = self.fetch(query, limit=limit, as_of=as_of)
        except Exception as exc:
            return FetchResult([], self.name, started, query, error=f"{type(exc).__name__}: {exc}")

        docs: list[RawDoc] = []
        for p in payloads:
            try:
                doc = self.parse(p)
            except Exception:
                continue  # one malformed record must not abort the sweep
            if doc is None:
                continue
            if as_of is not None and (doc.published_at is None or doc.published_at > as_of):
                continue
            docs.append(doc)

        return FetchResult(docs, self.name, started, query)

    def to_db_row(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source_type": self.source_type,
            "url": self.url,
            "tier": int(self.tier),
            "reliability_score": self.reliability_score,
            "rate_limit_per_hour": self.rate_limit_per_hour,
        }


class SourceRegistry:
    """Registry of available sources, filterable by tier and type."""

    def __init__(self) -> None:
        self._sources: dict[str, Source] = {}

    def register(self, source: Source) -> Source:
        self._sources[source.name] = source
        return source

    def get(self, name: str) -> Source | None:
        return self._sources.get(name)

    def all(self) -> list[Source]:
        return list(self._sources.values())

    def by_tier(self, max_tier: int) -> list[Source]:
        return [s for s in self._sources.values() if int(s.tier) <= max_tier]

    def evidence_grade(self) -> list[Source]:
        """Sources whose output may substantiate a claim."""
        return [s for s in self._sources.values() if s.tier.is_citable_evidence]

    def __len__(self) -> int:
        return len(self._sources)

    def __iter__(self) -> Iterable[Source]:
        return iter(self._sources.values())


registry = SourceRegistry()
