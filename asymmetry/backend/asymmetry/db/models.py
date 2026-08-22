"""Database schema.

Three properties are structural rather than incidental, and everything else
follows from them:

1. **Everything is timestamped.** Every row records when it was created and,
   where it represents a fact about the world, when that fact was *published*.
2. **Facts are append-only.** Scores, financial metrics and market estimates are
   never updated in place. A new observation is a new row. This is what makes
   "what did the system believe six months ago" a query rather than an
   archaeological dig.
3. **Provenance is mandatory.** A claim without a source is not storable: the
   foreign key is not nullable.

Together these give point-in-time correctness, which is the precondition for
honest backtesting. Retrofitting them later is effectively impossible.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

#: JSONB on PostgreSQL, plain JSON on SQLite, so the test suite needs no server.
JSONType = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class UUIDMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)


# ==========================================================================
# Sources and evidence
# ==========================================================================
class Source(UUIDMixin, TimestampMixin, Base):
    """Where information came from, and how much that origin can be trusted.

    ``tier`` follows section 41: 1 = government/SEC/peer-reviewed,
    5 = forums and social media. Tier 5 may *trigger* discovery but is never
    sufficient as terminal evidence; that rule is enforced in the fact checker.
    """

    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    rate_limit_per_hour: Mapped[int | None] = mapped_column(Integer)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    claims: Mapped[list["Claim"]] = relationship(back_populates="source")

    __table_args__ = (Index("ix_sources_tier", "tier"),)


class Claim(UUIDMixin, TimestampMixin, Base):
    """A single material assertion, with provenance and a confidence.

    Nothing reaches a report without a row here. ``published_at`` is what the
    as-of filter reads, so it is indexed and effectively mandatory for anything
    that should participate in historical mode.
    """

    __tablename__ = "claims"

    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(64), default="fact")
    published_at: Mapped[date | None] = mapped_column(Date, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    supports: Mapped[bool | None] = mapped_column(Boolean)
    contradicted_by: Mapped[str | None] = mapped_column(Text)
    is_speculation: Mapped[bool] = mapped_column(Boolean, default=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    extra: Mapped[dict] = mapped_column(JSONType, default=dict)

    source: Mapped[Source] = relationship(back_populates="claims")
    candidate: Mapped["Candidate | None"] = relationship(back_populates="claims")


# ==========================================================================
# The central entity
# ==========================================================================
class Candidate(UUIDMixin, TimestampMixin, Base):
    """A company, project, technology or open-source effort under research.

    Denormalised current scores live here for fast ranking; the authoritative
    history is in :class:`Score`. The two are kept in step by the pipeline, and
    the denormalised copy is always reconstructible from the score history.
    """

    __tablename__ = "candidates"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ticker: Mapped[str | None] = mapped_column(String(32), index=True)
    asset_type: Mapped[str] = mapped_column(String(64), default="public_company")
    sector: Mapped[str | None] = mapped_column(String(128), index=True)
    industry: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str | None] = mapped_column(Text)

    # Current snapshot, denormalised for ranking.
    current_market_cap: Mapped[float | None] = mapped_column(Float)
    enterprise_value: Mapped[float | None] = mapped_column(Float)
    revenue: Mapped[float | None] = mapped_column(Float)
    revenue_growth: Mapped[float | None] = mapped_column(Float)
    cash: Mapped[float | None] = mapped_column(Float)
    debt: Mapped[float | None] = mapped_column(Float)
    shares_outstanding: Mapped[float | None] = mapped_column(Float)

    # Latest scores, denormalised for ranking.
    technology_score: Mapped[float | None] = mapped_column(Float)
    market_score: Mapped[float | None] = mapped_column(Float)
    competition_score: Mapped[float | None] = mapped_column(Float)
    signal_score: Mapped[float | None] = mapped_column(Float)
    management_score: Mapped[float | None] = mapped_column(Float)
    financial_score: Mapped[float | None] = mapped_column(Float)
    valuation_score: Mapped[float | None] = mapped_column(Float)
    future_upside_score: Mapped[float | None] = mapped_column(Float)
    risk_score: Mapped[float | None] = mapped_column(Float)
    asymmetry_score: Mapped[float | None] = mapped_column(Float, index=True)
    overall_score: Mapped[float | None] = mapped_column(Float, index=True)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    red_flag_score: Mapped[float | None] = mapped_column(Float)
    hype_score: Mapped[float | None] = mapped_column(Float)

    verdict: Mapped[str | None] = mapped_column(String(32), index=True)
    verdict_reason: Mapped[str | None] = mapped_column(Text)

    stage: Mapped[int] = mapped_column(Integer, default=1, index=True)
    rank: Mapped[int | None] = mapped_column(Integer, index=True)
    previous_rank: Mapped[int | None] = mapped_column(Integer)

    discovery_date: Mapped[date] = mapped_column(Date, default=lambda: _now().date(), index=True)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dedupe_key: Mapped[str | None] = mapped_column(String(255), index=True)
    extra: Mapped[dict] = mapped_column(JSONType, default=dict)

    claims: Mapped[list[Claim]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    scores: Mapped[list["Score"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    signals: Mapped[list["Signal"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    metrics: Mapped[list["FinancialMetric"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    theses: Mapped[list["Thesis"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    risks: Mapped[list["RiskFactor"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    competitors: Mapped[list["Competitor"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    market_estimates: Mapped[list["MarketEstimate"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    reports: Mapped[list["ResearchReport"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_candidates_dedupe_key"),
        Index("ix_candidates_rank_score", "overall_score", "asymmetry_score"),
    )


# ==========================================================================
# Point-in-time facts (append-only)
# ==========================================================================
class FinancialMetric(UUIDMixin, TimestampMixin, Base):
    """A financial snapshot as of a date. Never updated - only superseded."""

    __tablename__ = "financial_metrics"

    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    as_of: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(32), default="TTM")
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"))
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=False)

    market_cap: Mapped[float | None] = mapped_column(Float)
    enterprise_value: Mapped[float | None] = mapped_column(Float)
    revenue: Mapped[float | None] = mapped_column(Float)
    revenue_prior: Mapped[float | None] = mapped_column(Float)
    revenue_growth: Mapped[float | None] = mapped_column(Float)
    gross_margin: Mapped[float | None] = mapped_column(Float)
    gross_margin_prior: Mapped[float | None] = mapped_column(Float)
    operating_income: Mapped[float | None] = mapped_column(Float)
    net_income: Mapped[float | None] = mapped_column(Float)
    free_cash_flow: Mapped[float | None] = mapped_column(Float)
    cash: Mapped[float | None] = mapped_column(Float)
    debt: Mapped[float | None] = mapped_column(Float)
    shares_outstanding: Mapped[float | None] = mapped_column(Float)
    shares_outstanding_prior: Mapped[float | None] = mapped_column(Float)
    stock_based_comp: Mapped[float | None] = mapped_column(Float)
    insider_ownership: Mapped[float | None] = mapped_column(Float)
    institutional_ownership: Mapped[float | None] = mapped_column(Float)
    largest_customer_pct: Mapped[float | None] = mapped_column(Float)
    ps_ratio: Mapped[float | None] = mapped_column(Float)
    pe_ratio: Mapped[float | None] = mapped_column(Float)
    ev_sales: Mapped[float | None] = mapped_column(Float)
    ev_ebitda: Mapped[float | None] = mapped_column(Float)
    price_fcf: Mapped[float | None] = mapped_column(Float)
    extra: Mapped[dict] = mapped_column(JSONType, default=dict)

    candidate: Mapped[Candidate] = relationship(back_populates="metrics")

    __table_args__ = (Index("ix_metrics_candidate_asof", "candidate_id", "as_of"),)


class Score(UUIDMixin, TimestampMixin, Base):
    """An append-only scoring snapshot, carrying its own decomposition.

    Storing ``components`` and ``weights`` inline means a historical score stays
    interpretable even after the weighting model has been recalibrated - without
    it, old scores would silently be read through today's assumptions.
    """

    __tablename__ = "scores"

    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    scored_at: Mapped[date] = mapped_column(Date, nullable=False, default=lambda: _now().date(), index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    base_score: Mapped[float | None] = mapped_column(Float)
    penalty: Mapped[float] = mapped_column(Float, default=0.0)
    asymmetry_score: Mapped[float | None] = mapped_column(Float)
    risk_score: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    red_flag_score: Mapped[float | None] = mapped_column(Float)
    rank: Mapped[int | None] = mapped_column(Integer)
    verdict: Mapped[str | None] = mapped_column(String(32))
    components: Mapped[dict] = mapped_column(JSONType, default=dict)
    weights: Mapped[dict] = mapped_column(JSONType, default=dict)
    contributions: Mapped[dict] = mapped_column(JSONType, default=dict)
    penalty_reasons: Mapped[list] = mapped_column(JSONType, default=list)
    scenario_summary: Mapped[dict] = mapped_column(JSONType, default=dict)
    change_reason: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped[Candidate] = relationship(back_populates="scores")

    __table_args__ = (Index("ix_scores_candidate_date", "candidate_id", "scored_at"),)


class Signal(UUIDMixin, TimestampMixin, Base):
    """A detected acceleration, with the arithmetic that justified it."""

    __tablename__ = "signals"

    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    strength: Mapped[str] = mapped_column(String(32), nullable=False)
    current_value: Mapped[float] = mapped_column(Float)
    baseline_value: Mapped[float] = mapped_column(Float)
    pct_change: Mapped[float] = mapped_column(Float)
    z_score: Mapped[float] = mapped_column(Float)
    window_label: Mapped[str | None] = mapped_column(String(64))
    detected_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_significant: Mapped[bool] = mapped_column(Boolean, default=False)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"))
    evidence: Mapped[dict] = mapped_column(JSONType, default=dict)

    candidate: Mapped[Candidate] = relationship(back_populates="signals")

    __table_args__ = (Index("ix_signals_candidate_detected", "candidate_id", "detected_at"),)


class MarketEstimate(UUIDMixin, TimestampMixin, Base):
    """An independent TAM/SAM/SOM estimate.

    ``is_management_claim`` exists so management's own TAM can be stored for
    comparison while never being mistaken for the system's own view.
    """

    __tablename__ = "market_estimates"

    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    technology_id: Mapped[str | None] = mapped_column(ForeignKey("technologies.id", ondelete="CASCADE"))
    market_name: Mapped[str] = mapped_column(String(255), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, default=lambda: _now().date(), index=True)
    horizon_year: Mapped[int | None] = mapped_column(Integer)
    tam: Mapped[float | None] = mapped_column(Float)
    sam: Mapped[float | None] = mapped_column(Float)
    som: Mapped[float | None] = mapped_column(Float)
    methodology: Mapped[str] = mapped_column(Text, default="")
    customer_count: Mapped[float | None] = mapped_column(Float)
    price_per_customer: Mapped[float | None] = mapped_column(Float)
    purchase_frequency: Mapped[float | None] = mapped_column(Float)
    is_management_claim: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.4)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"))

    candidate: Mapped[Candidate | None] = relationship(back_populates="market_estimates")


# ==========================================================================
# Analysis artefacts
# ==========================================================================
class Technology(UUIDMixin, TimestampMixin, Base):
    """A node in the technology graph, for second-order discovery."""

    __tablename__ = "technologies"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    category: Mapped[str | None] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("technologies.id"))
    maturity: Mapped[str | None] = mapped_column(String(64))
    enables: Mapped[list] = mapped_column(JSONType, default=list)
    requires: Mapped[list] = mapped_column(JSONType, default=list)
    extra: Mapped[dict] = mapped_column(JSONType, default=dict)

    children: Mapped[list["Technology"]] = relationship()


class Competitor(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "competitors"

    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    competitor_type: Mapped[str] = mapped_column(String(64), default="direct")
    is_incumbent: Mapped[bool] = mapped_column(Boolean, default=False)
    threat_level: Mapped[str] = mapped_column(String(32), default="medium")
    could_copy: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str] = mapped_column(Text, default="")

    candidate: Mapped[Candidate] = relationship(back_populates="competitors")


class RiskFactor(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "risk_factors"

    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="general")
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    points: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[dict] = mapped_column(JSONType, default=dict)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    candidate: Mapped[Candidate] = relationship(back_populates="risks")


class Thesis(UUIDMixin, TimestampMixin, Base):
    """A falsifiable investment thesis with monitored conditions."""

    __tablename__ = "theses"

    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    horizon_years: Mapped[float] = mapped_column(Float, default=10.0)
    invalidated_at: Mapped[date | None] = mapped_column(Date)
    invalidation_reason: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped[Candidate] = relationship(back_populates="theses")
    conditions: Mapped[list["ThesisCondition"]] = relationship(back_populates="thesis", cascade="all, delete-orphan")


class ThesisCondition(UUIDMixin, TimestampMixin, Base):
    """One thing that must remain true. Individually monitored and falsifiable."""

    __tablename__ = "thesis_conditions"

    thesis_id: Mapped[str] = mapped_column(ForeignKey("theses.id", ondelete="CASCADE"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    metric: Mapped[str | None] = mapped_column(String(128))
    comparator: Mapped[str | None] = mapped_column(String(16))
    threshold: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="unknown")
    last_checked_at: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str] = mapped_column(Text, default="")

    thesis: Mapped[Thesis] = relationship(back_populates="conditions")


class ResearchReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "research_reports"

    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    report_type: Mapped[str] = mapped_column(String(64), default="candidate", index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    report_date: Mapped[date] = mapped_column(Date, default=lambda: _now().date(), index=True)
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)

    candidate: Mapped[Candidate | None] = relationship(back_populates="reports")


class Debate(UUIDMixin, TimestampMixin, Base):
    """A saved adversarial exchange between agents."""

    __tablename__ = "debates"

    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    turns: Mapped[list] = mapped_column(JSONType, default=list)
    judgment: Mapped[str] = mapped_column(Text, default="")
    required_assumptions: Mapped[list] = mapped_column(JSONType, default=list)


class Event(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "events"

    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"))
    impact: Mapped[str | None] = mapped_column(String(32))

    candidate: Mapped[Candidate] = relationship(back_populates="events")


class Person(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "people"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    role: Mapped[str | None] = mapped_column(String(128))
    background: Mapped[str] = mapped_column(Text, default="")
    prior_companies: Mapped[list] = mapped_column(JSONType, default=list)
    joined_at: Mapped[date | None] = mapped_column(Date)
    departed_at: Mapped[date | None] = mapped_column(Date)


# ==========================================================================
# Operations
# ==========================================================================
class AgentRun(UUIDMixin, TimestampMixin, Base):
    """Audit record for every agent invocation, including cost.

    Makes the system's behaviour and spend inspectable rather than mysterious,
    which is a prerequisite for the cost controls in section 43.
    """

    __tablename__ = "agent_runs"

    agent_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id", ondelete="SET NULL"), index=True)
    stage: Mapped[int | None] = mapped_column(Integer)
    model: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="ok", index=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text)
    output_hash: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)


class PipelineRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pipeline_runs"

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="running")
    as_of: Mapped[date | None] = mapped_column(Date)
    mode: Mapped[str] = mapped_column(String(32), default="live")
    candidates_discovered: Mapped[int] = mapped_column(Integer, default=0)
    candidates_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    signals_detected: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    stats: Mapped[dict] = mapped_column(JSONType, default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class Watchlist(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "watchlists"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, default="")

    entries: Mapped[list["WatchlistEntry"]] = relationship(back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistEntry(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "watchlist_entries"

    watchlist_id: Mapped[str] = mapped_column(ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    added_at: Mapped[date] = mapped_column(Date, default=lambda: _now().date())
    removed_at: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text, default="")

    watchlist: Mapped[Watchlist] = relationship(back_populates="entries")


# ==========================================================================
# Paper portfolio and the feedback loop
# ==========================================================================
class Portfolio(UUIDMixin, TimestampMixin, Base):
    """Simulated only. The system never places a real trade."""

    __tablename__ = "portfolios"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    starting_cash: Mapped[float] = mapped_column(Float, default=10_000.0)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    positions: Mapped[list["Position"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")


class Position(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "positions"

    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    opened_at: Mapped[date] = mapped_column(Date, default=lambda: _now().date())
    entry_market_cap: Mapped[float | None] = mapped_column(Float)
    closed_at: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")

    portfolio: Mapped[Portfolio] = relationship(back_populates="positions")


class Prediction(UUIDMixin, TimestampMixin, Base):
    """A falsifiable prediction, later scored against reality (section 51).

    This table is the mechanism by which the platform can improve rather than
    merely sound confident. ``resolved_correct`` and ``brier_score`` are filled
    in when the horizon arrives, and the resulting per-signal accuracy replaces
    the hand-tuned weights in the scoring model.
    """

    __tablename__ = "predictions"

    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    made_at: Mapped[date] = mapped_column(Date, default=lambda: _now().date(), index=True)
    horizon_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    metric: Mapped[str | None] = mapped_column(String(128))
    predicted_value: Mapped[float | None] = mapped_column(Float)
    probability: Mapped[float] = mapped_column(Float, default=0.5)
    driving_signals: Mapped[list] = mapped_column(JSONType, default=list)
    resolved_at: Mapped[date | None] = mapped_column(Date)
    actual_value: Mapped[float | None] = mapped_column(Float)
    resolved_correct: Mapped[bool | None] = mapped_column(Boolean)
    brier_score: Mapped[float | None] = mapped_column(Float)


ALL_TABLES = [
    Source, Claim, Candidate, FinancialMetric, Score, Signal, MarketEstimate,
    Technology, Competitor, RiskFactor, Thesis, ThesisCondition, ResearchReport,
    Debate, Event, Person, AgentRun, PipelineRun, Watchlist, WatchlistEntry,
    Portfolio, Position, Prediction,
]
