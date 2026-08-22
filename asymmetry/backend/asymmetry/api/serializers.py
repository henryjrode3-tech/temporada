"""Serialisers shaping ORM objects into the API contract."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..db import models as m


def serialize_signal(s: m.Signal) -> dict[str, Any]:
    return {
        "id": s.id, "signal_type": s.signal_type, "strength": s.strength,
        "current_value": s.current_value, "baseline_value": s.baseline_value,
        "pct_change": s.pct_change, "z_score": s.z_score,
        "window_label": s.window_label,
        "detected_at": s.detected_at.isoformat() if s.detected_at else None,
        "description": s.description, "is_significant": s.is_significant,
        "evidence": s.evidence or {},
    }


def _latest_score(db: Session, candidate_id: str) -> m.Score | None:
    return (
        db.query(m.Score).filter(m.Score.candidate_id == candidate_id)
        .order_by(m.Score.scored_at.desc(), m.Score.created_at.desc()).first()
    )


def serialize_candidate(db: Session, c: m.Candidate) -> dict[str, Any]:
    latest_signal = (
        db.query(m.Signal).filter(m.Signal.candidate_id == c.id)
        .order_by(m.Signal.detected_at.desc()).first()
    )
    score = _latest_score(db, c.id)
    return {
        "id": c.id, "name": c.name, "ticker": c.ticker, "asset_type": c.asset_type,
        "sector": c.sector, "industry": c.industry, "description": c.description,
        "current_market_cap": c.current_market_cap,
        "enterprise_value": c.enterprise_value,
        "revenue": c.revenue, "revenue_growth": c.revenue_growth,
        "cash": c.cash, "debt": c.debt,
        "overall_score": c.overall_score or 0.0,
        "asymmetry_score": c.asymmetry_score or 0.0,
        "risk_score": c.risk_score or 0.0,
        "confidence_score": c.confidence_score or 0.0,
        "red_flag_score": c.red_flag_score or 0.0,
        "hype_score": c.hype_score or 0.0,
        "verdict": c.verdict, "verdict_reason": c.verdict_reason,
        "stage": c.stage,
        "discovery_date": c.discovery_date.isoformat() if c.discovery_date else None,
        "last_updated": (
            c.last_analyzed_at.isoformat() if c.last_analyzed_at
            else (c.updated_at.isoformat() if c.updated_at else None)
        ),
        "rank": c.rank, "previous_rank": c.previous_rank,
        "rank_change": (
            (c.previous_rank - c.rank) if c.rank and c.previous_rank else None
        ),
        "latest_signal": serialize_signal(latest_signal) if latest_signal else None,
        "scenario_summary": (score.scenario_summary or None) if score else None,
        "is_synthetic": bool((c.extra or {}).get("synthetic")),
    }


def _agent_payload(db: Session, candidate_id: str, agent: str) -> dict[str, Any]:
    row = (
        db.query(m.ResearchReport)
        .filter(m.ResearchReport.candidate_id == candidate_id)
        .filter(m.ResearchReport.report_type == f"agent:{agent}")
        .order_by(m.ResearchReport.created_at.desc()).first()
    )
    return (row.payload or {}) if row else {}


def serialize_candidate_detail(db: Session, c: m.Candidate) -> dict[str, Any]:
    base = serialize_candidate(db, c)
    score = _latest_score(db, c.id)

    valuation = _agent_payload(db, c.id, "valuation")
    contrarian = _agent_payload(db, c.id, "contrarian")
    technology = _agent_payload(db, c.id, "technology")
    market = _agent_payload(db, c.id, "market")
    competition = _agent_payload(db, c.id, "competition")
    financial = _agent_payload(db, c.id, "financial")
    future = _agent_payload(db, c.id, "future")
    factcheck = _agent_payload(db, c.id, "factchecker")

    signals = [
        serialize_signal(s) for s in
        db.query(m.Signal).filter(m.Signal.candidate_id == c.id)
        .order_by(m.Signal.detected_at.desc()).all()
    ]
    claims = [
        {
            "id": cl.id, "claim": cl.claim, "claim_type": cl.claim_type,
            "source_name": src.name, "source_tier": src.tier, "source_url": src.url,
            "published_at": cl.published_at.isoformat() if cl.published_at else None,
            "confidence": cl.confidence, "verified": cl.verified,
            "is_speculation": cl.is_speculation,
        }
        for cl, src in db.query(m.Claim, m.Source)
        .join(m.Source, m.Claim.source_id == m.Source.id)
        .filter(m.Claim.candidate_id == c.id).all()
    ]
    flags = [
        {"code": r.code, "severity": r.severity, "title": r.title,
         "detail": r.detail, "points": r.points, "evidence": r.evidence or {}}
        for r in db.query(m.RiskFactor).filter(m.RiskFactor.candidate_id == c.id)
        .order_by(m.RiskFactor.points.desc()).all()
    ]
    thesis_row = (
        db.query(m.Thesis).filter(m.Thesis.candidate_id == c.id)
        .order_by(m.Thesis.created_at.desc()).first()
    )
    debate = (
        db.query(m.Debate).filter(m.Debate.candidate_id == c.id)
        .order_by(m.Debate.created_at.desc()).first()
    )
    history = [
        {"at": s.scored_at.isoformat(), "overall_score": s.overall_score,
         "asymmetry_score": s.asymmetry_score, "rank": s.rank,
         "verdict": s.verdict, "change_reason": s.change_reason}
        for s in db.query(m.Score).filter(m.Score.candidate_id == c.id)
        .order_by(m.Score.scored_at.asc()).all()
    ]

    dimension_scores = []
    if score and score.components:
        rationales = {
            "technology": technology.get("rationale", ""),
            "market": market.get("rationale", ""),
            "competitive_advantage": competition.get("rationale", ""),
            "financial_health": financial.get("rationale", ""),
            "future_upside": future.get("rationale", ""),
            "risk": contrarian.get("rationale", ""),
        }
        for dim, value in score.components.items():
            dimension_scores.append({
                "dimension": dim, "score": value,
                "rationale": rationales.get(dim, ""),
                "weight": (score.weights or {}).get(dim),
                "contribution": (score.contributions or {}).get(dim),
            })

    return {
        **base,
        "scenarios": valuation.get("scenarios"),
        "milestones": valuation.get("milestones", []),
        "reverse_valuation": valuation.get("reverse_valuation"),
        "dimension_scores": dimension_scores,
        "composite": {
            "overall_score": score.overall_score, "base_score": score.base_score,
            "penalty": score.penalty, "penalty_reasons": score.penalty_reasons or [],
            "components": score.components or {}, "weights": score.weights or {},
            "contributions": score.contributions or {},
            "confidence_score": score.confidence_score,
        } if score else None,
        "red_flags": {
            "flags": flags,
            "red_flag_score": c.red_flag_score or 0.0,
            "penalty_points": score.penalty if score else 0.0,
        },
        "signals": signals,
        "claims": claims,
        "thesis": {
            "id": thesis_row.id, "statement": thesis_row.statement,
            "status": thesis_row.status, "horizon_years": thesis_row.horizon_years,
            "created_at": thesis_row.created_at.isoformat() if thesis_row.created_at else None,
            "invalidation_reason": thesis_row.invalidation_reason,
            "conditions": [
                {"text": cond.text, "metric": cond.metric,
                 "comparator": cond.comparator, "threshold": cond.threshold,
                 "status": cond.status, "note": cond.note}
                for cond in thesis_row.conditions
            ],
        } if thesis_row else None,
        "debate": (debate.turns or []) if debate else [],
        "judgment": debate.judgment if debate else "",
        "required_assumptions": (debate.required_assumptions or []) if debate else [],
        "score_history": history,
        "analysis": {
            "technology": technology, "market": market, "competition": competition,
            "financial": financial, "future": future, "contrarian": contrarian,
            "factcheck": factcheck,
        },
    }
