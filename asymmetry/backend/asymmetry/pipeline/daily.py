"""The research pipeline (sections 33 and 43).

Implements the 4-stage funnel. Stage 1 is free and deterministic; only what
survives it is allowed to cost money. That ordering is the whole cost-control
strategy, and it is why the expensive agents are never invoked on the long tail
of obviously unsuitable candidates.

The eleven daily steps from section 33 map onto :meth:`Pipeline.run_daily`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..agents import (
    ANALYSIS_AGENTS,
    Agent,
    AgentResult,
    CandidateContext,
    DebateJudgeAgent,
    FactCheckerAgent,
    ThesisAgent,
)
from ..config import get_settings
from ..core.alerts import CandidateSnapshot, evaluate as evaluate_alerts, sort_alerts
from ..core.hype import analyse_hype
from ..core.movement import explain_movement
from ..core.redflags import FinancialSnapshot, detect_red_flags
from ..core.scoring import (
    Dimension,
    DimensionScore,
    assign_verdict,
    compute_composite,
)
from ..db import models as m
from ..llm.client import BudgetTracker, LLMClient

log = logging.getLogger(__name__)


@dataclass
class StageResult:
    passed: list[str] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)

    def reject(self, cid: str, why: str) -> None:
        self.rejected.append((cid, why))


class Pipeline:
    """Orchestrates discovery, analysis, scoring and ranking."""

    def __init__(self, session: Session, llm: LLMClient | None = None, as_of: date | None = None) -> None:
        self.session = session
        self.settings = get_settings()
        self.as_of = as_of
        self.llm = llm or LLMClient(
            budget=BudgetTracker(
                max_cost_usd=self.settings.max_cost_per_run_usd,
                max_calls=self.settings.max_llm_calls_per_run,
            )
        )

    # ----------------------------------------------------------------------
    # Context assembly
    # ----------------------------------------------------------------------
    def build_context(self, cand: m.Candidate) -> CandidateContext:
        """Assemble everything the agents may see, honouring the as-of cutoff."""
        metric = (
            self.session.query(m.FinancialMetric)
            .filter(m.FinancialMetric.candidate_id == cand.id)
            .filter(m.FinancialMetric.as_of <= self.as_of if self.as_of else True)
            .order_by(m.FinancialMetric.as_of.desc())
            .first()
        )
        est = (
            self.session.query(m.MarketEstimate)
            .filter(m.MarketEstimate.candidate_id == cand.id)
            .filter(m.MarketEstimate.is_management_claim.is_(False))
            .order_by(m.MarketEstimate.as_of.desc())
            .first()
        )
        claims = (
            self.session.query(m.Claim, m.Source)
            .join(m.Source, m.Claim.source_id == m.Source.id)
            .filter(m.Claim.candidate_id == cand.id)
            .limit(40)
            .all()
        )
        competitors = [
            c.name for c in self.session.query(m.Competitor)
            .filter(m.Competitor.candidate_id == cand.id).limit(15)
        ]

        hype = analyse_hype(f"{cand.name}. {cand.description}")

        ctx = CandidateContext(
            candidate_id=cand.id, name=cand.name, ticker=cand.ticker,
            sector=cand.sector, industry=cand.industry,
            description=cand.description, asset_type=cand.asset_type,
            market_cap=metric.market_cap if metric else cand.current_market_cap,
            revenue=metric.revenue if metric else cand.revenue,
            revenue_prior=metric.revenue_prior if metric else None,
            revenue_growth=metric.revenue_growth if metric else cand.revenue_growth,
            gross_margin=metric.gross_margin if metric else None,
            free_cash_flow=metric.free_cash_flow if metric else None,
            cash=metric.cash if metric else cand.cash,
            debt=metric.debt if metric else cand.debt,
            shares_outstanding=metric.shares_outstanding if metric else cand.shares_outstanding,
            shares_outstanding_prior=metric.shares_outstanding_prior if metric else None,
            tam_estimate=est.tam if est else None,
            claims=[
                {"claim": c.claim, "source_name": s.name, "source_tier": s.tier,
                 "published_at": c.published_at.isoformat() if c.published_at else None,
                 "confidence": c.confidence}
                for c, s in claims
            ],
            competitors=competitors,
            hype_score=hype.hype_score,
            as_of=self.as_of,
            extra={
                "series": cand.extra.get("series", {}) if cand.extra else {},
                "insider_ownership": metric.insider_ownership if metric else None,
                "largest_customer_pct": metric.largest_customer_pct if metric else None,
                "hype_analysis": {
                    "hype_score": hype.hype_score,
                    "verdict": hype.verdict,
                    "terms_found": hype.terms_found,
                    "is_unsubstantiated": hype.is_unsubstantiated_hype,
                },
            },
        )

        # Red flags are deterministic and feed several agents, so compute once.
        snapshot = self._snapshot(cand, metric)
        report = detect_red_flags(
            snapshot, hype_score=hype.hype_score,
            hype_unsubstantiated=hype.is_unsubstantiated_hype,
        )
        ctx.red_flags = [f.to_dict() for f in report.flags]
        ctx.extra["red_flag_report"] = report.to_dict()

        # Series stored as ISO strings in JSON must be revived as dates.
        revived: dict[str, list[tuple[date, float]]] = {}
        for name, points in (ctx.extra.get("series") or {}).items():
            revived[name] = [
                (date.fromisoformat(p[0]) if isinstance(p[0], str) else p[0], float(p[1]))
                for p in points
            ]
        ctx.extra["series"] = revived
        return ctx

    def _snapshot(self, cand: m.Candidate, metric: m.FinancialMetric | None) -> FinancialSnapshot:
        extra = cand.extra or {}
        flags = extra.get("flags", {})
        if metric is None:
            return FinancialSnapshot(market_cap=cand.current_market_cap, revenue=cand.revenue)
        return FinancialSnapshot(
            market_cap=metric.market_cap, revenue=metric.revenue,
            revenue_prior=metric.revenue_prior,
            gross_margin=metric.gross_margin, gross_margin_prior=metric.gross_margin_prior,
            operating_income=metric.operating_income, net_income=metric.net_income,
            free_cash_flow=metric.free_cash_flow, cash=metric.cash, debt=metric.debt,
            shares_outstanding=metric.shares_outstanding,
            shares_outstanding_prior=metric.shares_outstanding_prior,
            stock_based_comp=metric.stock_based_comp,
            insider_ownership=metric.insider_ownership,
            largest_customer_pct=metric.largest_customer_pct,
            insider_selling_ratio=flags.get("insider_selling"),
            management_departures_12m=flags.get("departures"),
            going_concern_doubt=bool(flags.get("going_concern")),
            restatements=int(flags.get("restatements", 0)),
            active_investigations=int(flags.get("investigations", 0)),
            material_lawsuits=int(flags.get("lawsuits", 0)),
            auditor_changes_24m=int(flags.get("auditor_changes", 0)),
            missed_milestones=int(flags.get("missed_milestones", 0)),
            related_party_transactions=bool(flags.get("related_party")),
        )

    # ----------------------------------------------------------------------
    # Stage 1: free deterministic screening
    # ----------------------------------------------------------------------
    def stage1_screen(self, candidates: list[m.Candidate]) -> StageResult:
        """Reject the obviously unsuitable without spending anything.

        Deliberately crude. Its job is to protect the budget, not to be subtle;
        anything genuinely borderline is passed through to stage 2.
        """
        result = StageResult()
        for cand in candidates:
            ctx = self.build_context(cand)
            report = ctx.extra["red_flag_report"]

            if report["red_flag_score"] >= 70:
                result.reject(cand.id, "Disqualifying red flags")
                cand.verdict = "REJECTED"
                cand.verdict_reason = "Severe red flags detected during screening."
                cand.red_flag_score = report["red_flag_score"]
                continue

            if ctx.market_cap and ctx.market_cap > 500e9:
                result.reject(cand.id, "Too large to be an overlooked opportunity")
                cand.verdict = "REJECTED"
                cand.verdict_reason = (
                    "Market capitalisation above $500B; not an under-recognised opportunity."
                )
                continue

            hype = ctx.extra["hype_analysis"]
            if hype["is_unsubstantiated"] and (ctx.revenue or 0) < 1e6:
                result.reject(cand.id, "Unsubstantiated promotional language, negligible revenue")
                cand.verdict = "REJECTED"
                cand.verdict_reason = (
                    "Heavily promotional language with no measurable revenue behind it."
                )
                cand.hype_score = hype["hype_score"]
                continue

            cand.stage = 2
            cand.hype_score = hype["hype_score"]
            cand.red_flag_score = report["red_flag_score"]
            result.passed.append(cand.id)
        return result

    # ----------------------------------------------------------------------
    # Stage 3: full multi-agent analysis
    # ----------------------------------------------------------------------
    def analyse(self, cand: m.Candidate) -> dict[str, Any]:
        """Run every specialist, then debate, then score."""
        ctx = self.build_context(cand)
        results: dict[str, AgentResult] = {}
        dimension_scores: list[DimensionScore] = []

        for agent_cls in ANALYSIS_AGENTS:
            agent: Agent = agent_cls(self.llm)
            res = agent.run(ctx)
            results[agent.name] = res
            self._record_run(agent.name, cand.id, res)

            if not res.ok:
                log.warning("agent %s failed for %s: %s", agent.name, cand.name, res.error)
                continue
            if res.dimension_score:
                dimension_scores.append(res.dimension_score)

            # Later agents see what earlier ones concluded.
            if agent.name == "market":
                tam = res.payload.get("tam_usd")
                if isinstance(tam, (int, float)) and tam > 0:
                    ctx.tam_estimate = float(tam)
            elif agent.name == "financial":
                growth = res.payload.get("growth_score")
                if growth is not None:
                    dimension_scores.append(DimensionScore(
                        Dimension.GROWTH, Agent.clamp_score(growth),
                        "Derived from revenue growth.", confidence=0.6,
                    ))

        # Fact check, then debate.
        fc = FactCheckerAgent(self.llm).run(ctx)
        results["factchecker"] = fc
        self._record_run("factchecker", cand.id, fc)

        ctx.extra["agent_positions"] = {
            name: {"score": r.dimension_score.score if r.dimension_score else None,
                   "summary": r.narrative[:600]}
            for name, r in results.items() if r.ok and r.narrative
        }
        judge = DebateJudgeAgent(self.llm).run(ctx)
        results["judge"] = judge
        self._record_run("judge", cand.id, judge)

        thesis = ThesisAgent(self.llm).run(ctx)
        results["thesis"] = thesis
        self._record_run("thesis", cand.id, thesis)

        return self._score_and_persist(cand, ctx, results, dimension_scores)

    def _score_and_persist(
        self, cand: m.Candidate, ctx: CandidateContext,
        results: dict[str, AgentResult], dimension_scores: list[DimensionScore],
    ) -> dict[str, Any]:
        report = ctx.extra["red_flag_report"]
        composite = compute_composite(
            dimension_scores,
            penalty=report["penalty_points"],
            penalty_reasons=[f["title"] for f in report["flags"]],
        )

        val = results.get("valuation")
        scenario_summary: dict[str, Any] = {}
        asymmetry = 0.0
        if val and val.ok:
            scenarios = val.payload.get("scenarios", {})
            asymmetry = float(scenarios.get("asymmetry_score", 0.0))
            scenario_summary = {
                "median_multiple": scenarios.get("median_multiple"),
                "expected_multiple": scenarios.get("expected_multiple"),
                "probability_of_loss": scenarios.get("probability_of_loss"),
                "is_tail_dominated": scenarios.get("is_tail_dominated"),
                "payoff_ratio": scenarios.get("payoff_ratio"),
            }

        contrarian = results.get("contrarian")
        risk = (
            contrarian.dimension_score.score
            if contrarian and contrarian.ok and contrarian.dimension_score else 5.0
        )

        verdict, reason = assign_verdict(
            composite.overall_score, asymmetry, risk,
            composite.confidence_score, report["red_flag_score"],
        )

        by_dim = {ds.dimension: ds.score for ds in dimension_scores}
        cand.technology_score = by_dim.get(Dimension.TECHNOLOGY)
        cand.market_score = by_dim.get(Dimension.MARKET)
        cand.competition_score = by_dim.get(Dimension.COMPETITIVE_ADVANTAGE)
        cand.signal_score = by_dim.get(Dimension.EARLY_SIGNALS)
        cand.management_score = by_dim.get(Dimension.MANAGEMENT)
        cand.financial_score = by_dim.get(Dimension.FINANCIAL_HEALTH)
        cand.valuation_score = by_dim.get(Dimension.VALUATION)
        cand.future_upside_score = by_dim.get(Dimension.FUTURE_UPSIDE)
        cand.risk_score = risk
        cand.asymmetry_score = asymmetry
        cand.overall_score = composite.overall_score
        cand.confidence_score = composite.confidence_score
        cand.red_flag_score = report["red_flag_score"]
        cand.hype_score = ctx.hype_score
        cand.verdict = verdict.value
        cand.verdict_reason = reason
        cand.stage = 4
        cand.last_analyzed_at = datetime.now(timezone.utc)

        self.session.add(m.Score(
            candidate_id=cand.id,
            scored_at=self.as_of or date.today(),
            overall_score=composite.overall_score,
            base_score=composite.base_score,
            penalty=composite.penalty,
            asymmetry_score=asymmetry,
            risk_score=risk,
            confidence_score=composite.confidence_score,
            red_flag_score=report["red_flag_score"],
            verdict=verdict.value,
            components=composite.components,
            weights=composite.weights,
            contributions=composite.contributions,
            penalty_reasons=composite.penalty_reasons,
            scenario_summary=scenario_summary,
        ))

        self._persist_artifacts(cand, ctx, results)
        return {
            "candidate_id": cand.id, "verdict": verdict.value,
            "overall_score": composite.overall_score, "asymmetry_score": asymmetry,
        }

    def _persist_artifacts(
        self, cand: m.Candidate, ctx: CandidateContext, results: dict[str, AgentResult]
    ) -> None:
        """Write signals, risks, debate and thesis."""
        sig = results.get("signal")
        if sig and sig.ok:
            existing = {
                (s.signal_type, s.detected_at)
                for s in self.session.query(m.Signal).filter(m.Signal.candidate_id == cand.id)
            }
            for s in sig.payload.get("signals", []):
                detected = date.fromisoformat(s["detected_at"])
                if (s["signal_type"], detected) in existing:
                    continue
                self.session.add(m.Signal(
                    candidate_id=cand.id, signal_type=s["signal_type"],
                    strength=s["strength"], current_value=s["current_value"],
                    baseline_value=s["baseline_value"], pct_change=s["pct_change"],
                    z_score=s["z_score"], window_label=s["window_label"],
                    detected_at=detected, description=s["description"],
                    is_significant=s["is_significant"], evidence=s.get("evidence", {}),
                ))

        self.session.query(m.RiskFactor).filter(m.RiskFactor.candidate_id == cand.id).delete()
        for f in ctx.red_flags:
            self.session.add(m.RiskFactor(
                candidate_id=cand.id, code=f["code"], severity=f["severity"],
                title=f["title"], detail=f["detail"], points=f["points"],
                evidence=f.get("evidence", {}),
            ))

        judge = results.get("judge")
        if judge and judge.ok:
            self.session.query(m.Debate).filter(m.Debate.candidate_id == cand.id).delete()
            self.session.add(m.Debate(
                candidate_id=cand.id,
                turns=judge.payload.get("turns", []),
                judgment=judge.payload.get("judgment", ""),
                required_assumptions=judge.payload.get("required_assumptions", []),
            ))

        th = results.get("thesis")
        if th and th.ok and th.payload.get("statement"):
            self.session.query(m.Thesis).filter(m.Thesis.candidate_id == cand.id).delete()
            thesis = m.Thesis(
                candidate_id=cand.id,
                statement=th.payload["statement"],
                horizon_years=float(th.payload.get("horizon_years", 10) or 10),
            )
            self.session.add(thesis)
            self.session.flush()
            for c in th.payload.get("conditions", []):
                self.session.add(m.ThesisCondition(
                    thesis_id=thesis.id, text=str(c.get("text", ""))[:1000],
                    metric=c.get("metric"), comparator=c.get("comparator"),
                    threshold=(float(c["threshold"])
                               if isinstance(c.get("threshold"), (int, float)) else None),
                    status="unknown", note=str(c.get("why_it_matters", ""))[:500],
                ))

        for name, res in results.items():
            if res.ok and res.payload:
                self.session.add(m.ResearchReport(
                    candidate_id=cand.id, report_type=f"agent:{name}",
                    title=f"{name} analysis of {cand.name}",
                    body=res.narrative[:5000],
                    report_date=self.as_of or date.today(),
                    payload=res.payload,
                ))

    def _snapshot_for_alerts(self, cand: m.Candidate) -> CandidateSnapshot:
        thesis = (
            self.session.query(m.Thesis)
            .filter(m.Thesis.candidate_id == cand.id)
            .order_by(m.Thesis.created_at.desc()).first()
        )
        return CandidateSnapshot(
            candidate_id=cand.id, name=cand.name, rank=cand.rank,
            overall_score=cand.overall_score, asymmetry_score=cand.asymmetry_score,
            risk_score=cand.risk_score, red_flag_score=cand.red_flag_score,
            verdict=cand.verdict, revenue_growth=cand.revenue_growth,
            thesis_status=thesis.status if thesis else None,
        )

    def _record_run(self, agent_name: str, candidate_id: str, res: AgentResult) -> None:
        self.session.add(m.AgentRun(
            agent_name=agent_name, candidate_id=candidate_id,
            model=res.model, status="ok" if res.ok else "error",
            tokens_in=res.tokens_in, tokens_out=res.tokens_out,
            cost_usd=res.cost_usd, latency_ms=res.latency_ms,
            cache_hit=res.cache_hit, error=res.error,
            output_hash=res.output_hash,
            payload={"is_heuristic": res.is_heuristic},
        ))

    # ----------------------------------------------------------------------
    # Ranking and thesis monitoring
    # ----------------------------------------------------------------------
    def rerank(self) -> list[tuple[str, int, int | None]]:
        """Rank by asymmetry, then overall score. Records movement.

        Asymmetry leads because the platform's purpose is finding lopsided
        payoffs; overall score breaks ties so a merely lopsided but weak
        candidate does not outrank a lopsided and strong one.
        """
        ranked = (
            self.session.query(m.Candidate)
            .filter(m.Candidate.verdict.isnot(None))
            .filter(m.Candidate.verdict != "REJECTED")
            .filter(m.Candidate.overall_score.isnot(None))
            .order_by(m.Candidate.asymmetry_score.desc().nullslast(),
                      m.Candidate.overall_score.desc().nullslast())
            .all()
        )
        new_ranks = {cand.id: i for i, cand in enumerate(ranked, start=1)}

        movements: list[tuple[str, int | None, int | None]] = []
        # Every scored candidate is visited, not just the ranked ones. A
        # candidate that drops out of the ranking entirely is the single most
        # important movement to explain, and skipping it would leave the reader
        # with a stale rank and no account of where it went.
        for cand in self.session.query(m.Candidate).filter(
            m.Candidate.overall_score.isnot(None)
        ):
            cand.previous_rank = cand.rank
            cand.rank = new_ranks.get(cand.id)   # None once no longer eligible
            if cand.previous_rank != cand.rank:
                movements.append((cand.id, cand.rank, cand.previous_rank))
            self._explain_change(cand)

        movements.sort(key=lambda mv: (mv[1] is None, mv[1] or 0))
        return movements

    def _explain_change(self, cand: m.Candidate) -> None:
        """Attribute a candidate's movement to whatever actually changed.

        Written onto the newest score snapshot so the history explains itself
        without needing to recompute anything later.
        """
        history = (
            self.session.query(m.Score)
            .filter(m.Score.candidate_id == cand.id)
            .order_by(m.Score.scored_at.desc(), m.Score.created_at.desc())
            .limit(2).all()
        )
        if not history:
            return

        latest = history[0]
        latest.rank = cand.rank
        if len(history) < 2:
            return

        previous = history[1]

        def snapshot(row: m.Score, rank: int | None) -> dict[str, Any]:
            return {
                "overall_score": row.overall_score,
                "components": row.components,
                "weights": row.weights,
                "penalty": row.penalty,
                "penalty_reasons": row.penalty_reasons,
                "rank": rank,
                "asymmetry_score": row.asymmetry_score,
                "verdict": row.verdict,
            }

        explanation = explain_movement(
            snapshot(previous, cand.previous_rank),
            snapshot(latest, cand.rank),
        )
        summary = explanation.summary
        if cand.previous_rank is not None and cand.rank is None:
            summary = (
                f"Dropped out of the ranking (was #{cand.previous_rank}); "
                f"now {cand.verdict}. " + summary
            )
        latest.change_reason = summary

    def check_theses(self) -> list[dict[str, Any]]:
        """Evaluate every monitored condition against current metrics.

        Theses created in this same run are evaluated but never invalidated. A
        thesis states what must remain true *going forward*; judging it against
        the very data that produced it would invalidate almost everything
        immediately and would say nothing about whether the thesis was wrong.
        Conditions are still recorded, so the starting position is visible.
        """
        invalidated = []
        today = self.as_of or date.today()
        for thesis in self.session.query(m.Thesis).filter(
            m.Thesis.status.in_(("active", "weakening"))
        ):
            cand = self.session.get(m.Candidate, thesis.candidate_id)
            if cand is None:
                continue
            created = thesis.created_at.date() if thesis.created_at else today
            is_new = created >= today
            metric = (
                self.session.query(m.FinancialMetric)
                .filter(m.FinancialMetric.candidate_id == cand.id)
                .order_by(m.FinancialMetric.as_of.desc()).first()
            )
            broken = 0
            for cond in thesis.conditions:
                actual = self._metric_value(cond.metric, cand, metric)
                if actual is None or cond.threshold is None or not cond.comparator:
                    cond.status = "unknown"
                else:
                    ok = {
                        ">": actual > cond.threshold, ">=": actual >= cond.threshold,
                        "<": actual < cond.threshold, "<=": actual <= cond.threshold,
                    }.get(cond.comparator)
                    if ok is None:
                        cond.status = "unknown"
                    elif ok:
                        cond.status = "holding"
                    else:
                        margin = abs(actual - cond.threshold) / max(abs(cond.threshold), 1e-9)
                        cond.status = "at_risk" if margin < 0.15 else "broken"
                    cond.note = f"Observed {actual:.4g} vs threshold {cond.threshold:.4g}"
                cond.last_checked_at = self.as_of or date.today()
                if cond.status == "broken":
                    broken += 1

            total = len(thesis.conditions)
            if is_new:
                # Baseline only. Record where the conditions start, judge later.
                thesis.status = "active"
                continue

            if total and broken >= max(2, total // 2):
                thesis.status = "invalidated"
                thesis.invalidated_at = today
                thesis.invalidation_reason = f"{broken} of {total} conditions broken."
                cand.verdict = "THESIS_INVALIDATED"
                cand.verdict_reason = thesis.invalidation_reason
                invalidated.append({"candidate": cand.name, "reason": thesis.invalidation_reason})
            elif broken:
                thesis.status = "weakening"
                if cand.verdict not in ("REJECTED", "THESIS_INVALIDATED"):
                    cand.verdict = "THESIS_WEAKENING"
                    cand.verdict_reason = f"{broken} of {total} thesis conditions broken."
            else:
                thesis.status = "active"
        return invalidated

    @staticmethod
    def _metric_value(
        metric_name: str | None, cand: m.Candidate, fin: m.FinancialMetric | None
    ) -> float | None:
        if not metric_name:
            return None
        if fin is None:
            return None
        direct = {
            "revenue_growth": fin.revenue_growth, "gross_margin": fin.gross_margin,
            "revenue": fin.revenue, "cash": fin.cash, "debt": fin.debt,
            "free_cash_flow": fin.free_cash_flow, "market_cap": fin.market_cap,
        }
        if metric_name in direct:
            return direct[metric_name]
        if metric_name == "dilution_yoy" and fin.shares_outstanding and fin.shares_outstanding_prior:
            return fin.shares_outstanding / fin.shares_outstanding_prior - 1
        if metric_name == "cash_runway":
            from ..core.finmath import burn_runway_years
            r = burn_runway_years(fin.cash or 0.0, fin.free_cash_flow or 0.0)
            return r if r is not None else 99.0   # not burning cash
        return None

    # ----------------------------------------------------------------------
    # The daily loop (section 33)
    # ----------------------------------------------------------------------
    def run_daily(self, limit: int | None = None) -> dict[str, Any]:
        run = m.PipelineRun(
            as_of=self.as_of, mode="historical" if self.as_of else "live",
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(run)
        self.session.flush()

        try:
            candidates = self.session.query(m.Candidate).all()
            # Snapshot before anything changes, so alerts compare like with like.
            before = {c.id: self._snapshot_for_alerts(c) for c in candidates}
            screen = self.stage1_screen(candidates)
            self.session.flush()

            survivors = (
                self.session.query(m.Candidate)
                .filter(m.Candidate.id.in_(screen.passed))
                .order_by(m.Candidate.current_market_cap.asc().nullslast())
                .limit(limit or self.settings.stage3_max_candidates)
                .all()
            ) if screen.passed else []

            analysed = []
            for cand in survivors:
                try:
                    analysed.append(self.analyse(cand))
                    self.session.flush()
                except Exception as exc:
                    log.exception("analysis failed for %s", cand.name)
                    self.session.add(m.AgentRun(
                        agent_name="pipeline", candidate_id=cand.id,
                        status="error", error=str(exc),
                    ))

            invalidated = self.check_theses()
            movements = self.rerank()

            alerts = []
            for cand in self.session.query(m.Candidate).filter(
                m.Candidate.overall_score.isnot(None)
            ):
                alerts.extend(evaluate_alerts(
                    before.get(cand.id),
                    self._snapshot_for_alerts(cand),
                    when=self.as_of or date.today(),
                ))
            alerts = sort_alerts(alerts)

            signals_count = self.session.query(m.Signal).count()
            run.finished_at = datetime.now(timezone.utc)
            run.status = "ok"
            run.candidates_discovered = len(candidates)
            run.candidates_analyzed = len(analysed)
            run.signals_detected = signals_count
            run.total_cost_usd = self.llm.budget.spent_usd
            run.stats = {
                "screened_out": len(screen.rejected),
                "passed_screen": len(screen.passed),
                "theses_invalidated": len(invalidated),
                "budget": self.llm.budget.summary(),
                "llm_mode": self.settings.llm_mode,
                "alerts": [a.to_dict() for a in alerts[:50]],
            }
            return {
                "run_id": run.id, "analysed": len(analysed),
                "rejected": len(screen.rejected), "invalidated": invalidated,
                "movements": movements[:20], "budget": self.llm.budget.summary(),
                "alerts": [a.to_dict() for a in alerts],
            }
        except Exception as exc:
            run.status = "error"
            run.error = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            raise
