"""FastAPI application.

Read-mostly by design. The only mutating endpoints concern the *paper*
portfolio and triggering research runs; there is deliberately no endpoint that
could place a trade, because the system has no business having one.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from datetime import date, timedelta
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import models as m
from ..db.session import get_db
from .serializers import (
    serialize_candidate,
    serialize_candidate_detail,
    serialize_signal,
)

log = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="Asymmetry Engine API",
    version="0.1.0",
    description=(
        "Research platform for discovering asymmetric opportunities. "
        "Produces research findings, never investment advice or trade instructions."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Rate limiting
# --------------------------------------------------------------------------
_hits: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Fixed-window limiter keyed on client address.

    In-process, so it protects a single instance rather than a cluster; behind a
    load balancer this belongs in the proxy. It is here so the default
    deployment is not trivially floodable.
    """
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _hits[client]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
    window.append(now)
    return await call_next(request)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Guard for mutating endpoints. Inert until an API key is configured."""
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid or missing API key")


# --------------------------------------------------------------------------
# Read endpoints
# --------------------------------------------------------------------------
@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        db.execute(select(func.count()).select_from(m.Candidate)).scalar_one()
        db_ok = True
    except Exception as exc:
        log.warning("health check database failure: %s", exc)
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "llm_mode": settings.llm_mode,
        "version": app.version,
    }


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    by_verdict = dict(
        db.query(m.Candidate.verdict, func.count(m.Candidate.id))
        .group_by(m.Candidate.verdict).all()
    )
    week_ago = date.today() - timedelta(days=7)
    last_run = db.query(m.PipelineRun).order_by(m.PipelineRun.started_at.desc()).first()
    avg = db.query(func.avg(m.Candidate.asymmetry_score)).filter(
        m.Candidate.asymmetry_score.isnot(None)
    ).scalar()
    return {
        "total_candidates": db.query(func.count(m.Candidate.id)).scalar() or 0,
        "by_verdict": {k or "unscored": v for k, v in by_verdict.items()},
        "signals_last_7d": db.query(func.count(m.Signal.id)).filter(
            m.Signal.detected_at >= week_ago
        ).scalar() or 0,
        "avg_asymmetry": round(float(avg), 1) if avg is not None else 0.0,
        "last_pipeline_run": last_run.started_at.isoformat() if last_run else None,
        "llm_mode": settings.llm_mode,
        "total_cost_usd": round(
            db.query(func.coalesce(func.sum(m.AgentRun.cost_usd), 0.0)).scalar() or 0.0, 4
        ),
    }


@app.get("/api/candidates")
def list_candidates(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    verdict: str | None = None,
    sector: str | None = None,
    q: str | None = None,
    sort: str = Query("rank", pattern="^(rank|asymmetry|overall|risk|discovered|market_cap)$"),
) -> dict[str, Any]:
    query = db.query(m.Candidate)
    if verdict:
        query = query.filter(m.Candidate.verdict == verdict)
    if sector:
        query = query.filter(m.Candidate.sector == sector)
    if q:
        # Parameterised by SQLAlchemy, so the wildcards cannot inject SQL.
        like = f"%{q}%"
        query = query.filter(
            m.Candidate.name.ilike(like) | m.Candidate.description.ilike(like)
        )

    total = query.count()
    order = {
        "rank": m.Candidate.rank.asc().nullslast(),
        "asymmetry": m.Candidate.asymmetry_score.desc().nullslast(),
        "overall": m.Candidate.overall_score.desc().nullslast(),
        "risk": m.Candidate.red_flag_score.desc().nullslast(),
        "discovered": m.Candidate.discovery_date.desc(),
        "market_cap": m.Candidate.current_market_cap.asc().nullslast(),
    }[sort]
    rows = query.order_by(order).offset(offset).limit(limit).all()
    return {"items": [serialize_candidate(db, c) for c in rows], "total": total}


@app.get("/api/candidates/{candidate_id}")
def get_candidate(candidate_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    cand = db.get(m.Candidate, candidate_id)
    if cand is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return serialize_candidate_detail(db, cand)


@app.get("/api/opportunities/top")
def top_opportunities(
    db: Session = Depends(get_db), limit: int = Query(10, ge=1, le=50)
) -> list[dict[str, Any]]:
    rows = (
        db.query(m.Candidate)
        .filter(m.Candidate.rank.isnot(None))
        .filter(m.Candidate.verdict.notin_(["REJECTED", "THESIS_INVALIDATED"]))
        .order_by(m.Candidate.rank.asc())
        .limit(limit).all()
    )
    return [serialize_candidate(db, c) for c in rows]


@app.get("/api/signals")
def list_signals(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    significant_only: bool = False,
) -> list[dict[str, Any]]:
    query = db.query(m.Signal, m.Candidate).join(
        m.Candidate, m.Signal.candidate_id == m.Candidate.id
    )
    if significant_only:
        query = query.filter(m.Signal.is_significant.is_(True))
    rows = query.order_by(m.Signal.detected_at.desc()).limit(limit).all()
    return [
        {**serialize_signal(s), "candidate_id": c.id, "candidate_name": c.name,
         "sector": c.sector}
        for s, c in rows
    ]


@app.get("/api/theses")
def list_theses(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(m.Thesis, m.Candidate).join(
        m.Candidate, m.Thesis.candidate_id == m.Candidate.id
    ).all()
    return [
        {
            "id": t.id, "candidate_id": c.id, "candidate_name": c.name,
            "statement": t.statement, "status": t.status,
            "horizon_years": t.horizon_years,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "invalidated_at": t.invalidated_at.isoformat() if t.invalidated_at else None,
            "invalidation_reason": t.invalidation_reason,
            "conditions": [
                {"text": cond.text, "metric": cond.metric, "comparator": cond.comparator,
                 "threshold": cond.threshold, "status": cond.status, "note": cond.note}
                for cond in t.conditions
            ],
        }
        for t, c in rows
    ]


@app.get("/api/agent-runs")
def list_agent_runs(
    db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=500)
) -> list[dict[str, Any]]:
    rows = (
        db.query(m.AgentRun, m.Candidate)
        .outerjoin(m.Candidate, m.AgentRun.candidate_id == m.Candidate.id)
        .order_by(m.AgentRun.created_at.desc()).limit(limit).all()
    )
    return [
        {
            "id": r.id, "agent_name": r.agent_name, "candidate_id": r.candidate_id,
            "candidate_name": c.name if c else None, "model": r.model, "stage": r.stage,
            "tokens_in": r.tokens_in, "tokens_out": r.tokens_out,
            "cost_usd": r.cost_usd, "latency_ms": r.latency_ms,
            "cache_hit": r.cache_hit, "status": r.status, "error": r.error,
            "is_heuristic": (r.payload or {}).get("is_heuristic", False),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r, c in rows
    ]


@app.get("/api/sectors")
def list_sectors(db: Session = Depends(get_db)) -> list[str]:
    rows = db.query(m.Candidate.sector).distinct().filter(
        m.Candidate.sector.isnot(None)
    ).all()
    return sorted(r[0] for r in rows)


@app.get("/api/movements")
def movements(
    db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=100)
) -> list[dict[str, Any]]:
    """Recent standing changes, with the reason each one happened (section 13)."""
    rows = (
        db.query(m.Score, m.Candidate)
        .join(m.Candidate, m.Score.candidate_id == m.Candidate.id)
        .filter(m.Score.change_reason.isnot(None))
        .order_by(m.Score.created_at.desc())
        .limit(limit).all()
    )
    return [
        {
            "candidate_id": c.id, "candidate_name": c.name, "sector": c.sector,
            "rank": c.rank, "previous_rank": c.previous_rank,
            "rank_change": (
                (c.previous_rank - c.rank)
                if c.rank is not None and c.previous_rank is not None else None
            ),
            "dropped_out": c.previous_rank is not None and c.rank is None,
            "verdict": c.verdict,
            "overall_score": s.overall_score,
            "asymmetry_score": s.asymmetry_score,
            "scored_at": s.scored_at.isoformat() if s.scored_at else None,
            "reason": s.change_reason,
        }
        for s, c in rows
    ]


@app.get("/api/techgraph")
def tech_graph() -> dict[str, Any]:
    """The technology dependency graph (section 37)."""
    from ..core.techgraph import TechGraph

    return TechGraph().to_dict()


@app.get("/api/techgraph/second-order")
def second_order(
    driver: str = Query("AI compute demand"),
    min_depth: int = Query(2, ge=0, le=6),
) -> dict[str, Any]:
    """Trace a trend upstream to what it depends on (section 38)."""
    from ..core.techgraph import TechGraph

    graph = TechGraph()
    if graph.get(driver) is None:
        raise HTTPException(status_code=404, detail=f"unknown node: {driver}")
    return {
        "driver": driver,
        "chains": graph.chain_from(driver),
        "targets": graph.second_order_targets(driver, min_depth=min_depth),
        "queries": graph.discovery_queries(driver),
    }


@app.get("/api/reports/daily")
def daily_report(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Assemble the daily research report (section 34).

    Built from what actually changed rather than from a template, so a quiet day
    produces a short report instead of a padded one.
    """
    run = db.query(m.PipelineRun).order_by(m.PipelineRun.started_at.desc()).first()
    since = date.today() - timedelta(days=7)

    new_discoveries = (
        db.query(m.Candidate).filter(m.Candidate.discovery_date >= since)
        .order_by(m.Candidate.discovery_date.desc()).limit(10).all()
    )
    movers = (
        db.query(m.Candidate)
        .filter(m.Candidate.previous_rank.isnot(None), m.Candidate.rank.isnot(None))
        .all()
    )
    movers.sort(key=lambda c: abs((c.previous_rank or 0) - (c.rank or 0)), reverse=True)

    strongest = (
        db.query(m.Signal, m.Candidate).join(m.Candidate, m.Signal.candidate_id == m.Candidate.id)
        .filter(m.Signal.is_significant.is_(True))
        .order_by(m.Signal.z_score.desc()).limit(8).all()
    )
    riskiest = (
        db.query(m.Candidate).filter(m.Candidate.red_flag_score.isnot(None))
        .order_by(m.Candidate.red_flag_score.desc()).limit(5).all()
    )
    invalidated = db.query(m.Thesis, m.Candidate).join(
        m.Candidate, m.Thesis.candidate_id == m.Candidate.id
    ).filter(m.Thesis.status == "invalidated").limit(10).all()

    return {
        "generated_at": date.today().isoformat(),
        "pipeline_run": {
            "id": run.id if run else None,
            "status": run.status if run else None,
            "analysed": run.candidates_analyzed if run else 0,
            "cost_usd": run.total_cost_usd if run else 0.0,
            "stats": run.stats if run else {},
        },
        "new_discoveries": [
            {"id": c.id, "name": c.name, "sector": c.sector, "verdict": c.verdict,
             "asymmetry_score": c.asymmetry_score}
            for c in new_discoveries
        ],
        "biggest_movers": [
            {"id": c.id, "name": c.name, "rank": c.rank, "previous_rank": c.previous_rank,
             "change": (c.previous_rank or 0) - (c.rank or 0)}
            for c in movers[:8]
        ],
        "strongest_signals": [
            {**serialize_signal(s), "candidate_name": c.name, "candidate_id": c.id}
            for s, c in strongest
        ],
        "biggest_red_flags": [
            {"id": c.id, "name": c.name, "red_flag_score": c.red_flag_score,
             "verdict": c.verdict}
            for c in riskiest
        ],
        "thesis_invalidations": [
            {"candidate_id": c.id, "candidate_name": c.name,
             "reason": t.invalidation_reason}
            for t, c in invalidated
        ],
        "disclaimer": (
            "Research output only. Model estimates under stated assumptions. "
            "Not investment advice and not a recommendation to buy or sell anything."
        ),
    }


# --------------------------------------------------------------------------
# Paper portfolio - simulated only
# --------------------------------------------------------------------------
class PositionIn(BaseModel):
    candidate_id: str
    amount: float = Field(gt=0, le=1_000_000)
    notes: str = Field(default="", max_length=1000)


@app.get("/api/portfolio")
def get_portfolio(db: Session = Depends(get_db)) -> dict[str, Any]:
    pf = db.query(m.Portfolio).first()
    if pf is None:
        return {"exists": False, "is_simulated": True, "positions": []}
    positions = []
    for p in pf.positions:
        cand = db.get(m.Candidate, p.candidate_id)
        positions.append({
            "id": p.id, "candidate_id": p.candidate_id,
            "candidate_name": cand.name if cand else "(removed)",
            "amount": p.amount, "opened_at": p.opened_at.isoformat(),
            "entry_market_cap": p.entry_market_cap,
            "current_market_cap": cand.current_market_cap if cand else None,
            "notes": p.notes,
        })
    allocated = sum(p.amount for p in pf.positions)
    return {
        "exists": True, "id": pf.id, "name": pf.name,
        "is_simulated": True,
        "starting_cash": pf.starting_cash,
        "allocated": allocated,
        "uninvested": pf.starting_cash - allocated,
        "positions": positions,
        "notice": "Simulated allocations for testing the research method. No real trades.",
    }


@app.post("/api/portfolio/positions", dependencies=[Depends(require_api_key)])
def add_position(body: PositionIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    pf = db.query(m.Portfolio).first()
    if pf is None:
        pf = m.Portfolio(name="Paper Portfolio")
        db.add(pf)
        db.flush()
    cand = db.get(m.Candidate, body.candidate_id)
    if cand is None:
        raise HTTPException(status_code=404, detail="candidate not found")

    allocated = sum(p.amount for p in pf.positions)
    if allocated + body.amount > pf.starting_cash:
        raise HTTPException(
            status_code=400,
            detail=f"Exceeds simulated cash: ${pf.starting_cash - allocated:,.2f} available.",
        )

    pos = m.Position(
        portfolio_id=pf.id, candidate_id=cand.id, amount=body.amount,
        entry_market_cap=cand.current_market_cap, notes=body.notes,
    )
    db.add(pos)
    db.commit()
    return {"id": pos.id, "ok": True, "is_simulated": True}


@app.delete("/api/portfolio/positions/{position_id}", dependencies=[Depends(require_api_key)])
def remove_position(position_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    pos = db.get(m.Position, position_id)
    if pos is None:
        raise HTTPException(status_code=404, detail="position not found")
    db.delete(pos)
    db.commit()
    return {"ok": True}
