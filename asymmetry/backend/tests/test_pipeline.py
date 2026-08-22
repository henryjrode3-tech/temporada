"""Integration tests: database, pipeline, API and the anti-leakage guarantee.

Runs against SQLite in memory, so the suite needs no database server.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pytest

os.environ.setdefault("ASYMMETRY_DATABASE_URL", "sqlite://")
os.environ["ASYMMETRY_USE_MOCK_SOURCES"] = "true"

from asymmetry.db import models as m                    # noqa: E402
from asymmetry.db.seed import seed                      # noqa: E402
from asymmetry.db.session import (                      # noqa: E402
    apply_as_of,
    as_of,
    current_as_of,
    init_db,
    reset_engine,
)
from asymmetry.llm.client import (                      # noqa: E402
    BudgetExceeded,
    BudgetTracker,
    LLMClient,
    ResponseCache,
    extract_json,
)
from asymmetry.pipeline.daily import Pipeline           # noqa: E402


@pytest.fixture()
def session(tmp_path):
    """A fresh file-backed SQLite database per test."""
    os.environ["ASYMMETRY_DATABASE_URL"] = f"sqlite:///{tmp_path/'test.db'}"
    reset_engine()
    init_db(drop=True)
    from asymmetry.db.session import get_session_factory

    s = get_session_factory()()
    try:
        yield s
    finally:
        s.close()
        reset_engine()


@pytest.fixture()
def seeded(session):
    seed(session)
    session.commit()
    return session


# ==========================================================================
class TestSchema:
    def test_all_tables_created(self, session):
        from sqlalchemy import inspect
        from asymmetry.db.session import get_engine

        names = set(inspect(get_engine()).get_table_names())
        for expected in ("candidates", "claims", "sources", "scores", "signals",
                         "theses", "thesis_conditions", "agent_runs",
                         "financial_metrics", "market_estimates", "predictions"):
            assert expected in names

    def test_claim_requires_a_source(self, session):
        """Provenance is structural: an unsourced claim must not be storable."""
        from sqlalchemy.exc import IntegrityError

        session.add(m.Claim(claim="unsourced assertion", source_id=None))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_dedupe_key_is_unique(self, session):
        from sqlalchemy.exc import IntegrityError

        session.add(m.Candidate(name="A", dedupe_key="k"))
        session.add(m.Candidate(name="B", dedupe_key="k"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_timestamps_populated(self, seeded):
        c = seeded.query(m.Candidate).first()
        assert c.created_at is not None and c.updated_at is not None


class TestSeed:
    def test_seeds_candidates(self, seeded):
        assert seeded.query(m.Candidate).count() >= 12

    def test_seed_is_idempotent(self, seeded):
        before = seeded.query(m.Candidate).count()
        seed(seeded)
        seeded.commit()
        assert seeded.query(m.Candidate).count() == before

    def test_all_seeded_data_is_marked_synthetic(self, seeded):
        """Fabricated financials must never look like real evidence."""
        for c in seeded.query(m.Candidate).all():
            assert (c.extra or {}).get("synthetic") is True

    def test_synthetic_source_is_lowest_tier(self, seeded):
        src = seeded.query(m.Source).filter(m.Source.source_type == "synthetic").one()
        assert src.tier == 5
        assert src.reliability_score == 0.0


# ==========================================================================
class TestAsOfIsolation:
    """The mechanism that makes historical backtesting meaningful."""

    def test_context_sets_and_clears(self):
        assert current_as_of() is None
        with as_of(date(2015, 1, 1)):
            assert current_as_of() == date(2015, 1, 1)
        assert current_as_of() is None

    def test_filter_excludes_future_facts(self, seeded):
        query = seeded.query(m.Claim)
        total = query.count()
        assert total > 0
        with as_of(date(2000, 1, 1)):
            filtered = apply_as_of(seeded.query(m.Claim), m.Claim.published_at).count()
        assert filtered == 0

    def test_undated_facts_are_excluded_under_a_cutoff(self, seeded):
        """An undated fact cannot be proven to predate the cutoff, so it is hidden."""
        src = seeded.query(m.Source).first()
        cand = seeded.query(m.Candidate).first()
        seeded.add(m.Claim(candidate_id=cand.id, source_id=src.id,
                           claim="undated", published_at=None))
        seeded.commit()
        with as_of(date.today()):
            rows = apply_as_of(seeded.query(m.Claim), m.Claim.published_at).all()
        assert all(c.claim != "undated" for c in rows)

    def test_no_filter_without_a_cutoff(self, seeded):
        total = seeded.query(m.Claim).count()
        assert apply_as_of(seeded.query(m.Claim), m.Claim.published_at).count() == total

    def test_nesting_restores_outer_value(self):
        with as_of(date(2015, 1, 1)):
            with as_of(date(2020, 1, 1)):
                assert current_as_of() == date(2020, 1, 1)
            assert current_as_of() == date(2015, 1, 1)


# ==========================================================================
class TestLLMClient:
    def test_runs_without_api_key(self):
        c = LLMClient()
        r = c.complete("hello", heuristic=lambda: "fallback")
        assert r.is_heuristic and r.text == "fallback" and r.cost_usd == 0.0

    def test_missing_heuristic_raises(self):
        from asymmetry.llm.client import LLMUnavailable

        c = LLMClient()
        if not c.available:
            with pytest.raises(LLMUnavailable):
                c.complete("hello")

    def test_budget_ceiling_enforced(self):
        b = BudgetTracker(max_cost_usd=0.001, max_calls=2)
        b.spent_usd = 0.001
        with pytest.raises(BudgetExceeded):
            b.check(projected=0.5)

    def test_call_ceiling_enforced(self):
        b = BudgetTracker(max_cost_usd=100, max_calls=1)
        b.calls = 1
        with pytest.raises(BudgetExceeded):
            b.check()

    def test_cache_key_is_content_addressed(self):
        a = ResponseCache.key("m", "s", "p", 0.2)
        assert a == ResponseCache.key("m", "s", "p", 0.2)
        assert a != ResponseCache.key("m", "s", "different", 0.2)


class TestJsonExtraction:
    def test_bare_json(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_json_with_surrounding_prose(self):
        assert extract_json('Here you go:\n{"a": 1}\nHope that helps.') == {"a": 1}

    def test_array(self):
        assert extract_json("[1, 2, 3]") == [1, 2, 3]

    def test_unparseable_raises(self):
        with pytest.raises(ValueError):
            extract_json("no json at all")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            extract_json("")


# ==========================================================================
class TestPipeline:
    def test_runs_end_to_end_without_api_key(self, seeded):
        result = Pipeline(seeded).run_daily(limit=5)
        assert result["analysed"] > 0
        assert result["budget"]["spent_usd"] == 0.0

    def test_produces_scored_candidates(self, seeded):
        Pipeline(seeded).run_daily(limit=5)
        scored = seeded.query(m.Candidate).filter(m.Candidate.overall_score.isnot(None)).all()
        assert scored
        for c in scored:
            assert 0 <= c.overall_score <= 100
            assert 0 <= (c.asymmetry_score or 0) <= 100

    def test_fraud_pattern_is_rejected(self, seeded):
        Pipeline(seeded).run_daily(limit=14)
        fraud = seeded.query(m.Candidate).filter(
            m.Candidate.name == "QuantumLeap AI Dynamics").one()
        assert fraud.verdict == "REJECTED"
        assert fraud.red_flag_score >= 70

    def test_priced_for_perfection_scores_low_asymmetry(self, seeded):
        Pipeline(seeded).run_daily(limit=14)
        rich = seeded.query(m.Candidate).filter(
            m.Candidate.name == "Solstice Solid State").one()
        cheap = seeded.query(m.Candidate).filter(
            m.Candidate.name == "Halden Thermal Systems").one()
        assert (rich.asymmetry_score or 0) < (cheap.asymmetry_score or 0)

    def test_scores_are_append_only(self, seeded):
        p = Pipeline(seeded)
        p.run_daily(limit=3)
        first = seeded.query(m.Score).count()
        p.run_daily(limit=3)
        assert seeded.query(m.Score).count() > first

    def test_score_snapshot_retains_its_own_weights(self, seeded):
        """Historical scores must stay interpretable after recalibration."""
        Pipeline(seeded).run_daily(limit=3)
        score = seeded.query(m.Score).first()
        assert score.weights and score.components and score.contributions

    def test_agent_runs_are_audited(self, seeded):
        Pipeline(seeded).run_daily(limit=3)
        assert seeded.query(m.AgentRun).count() > 0

    def test_new_thesis_is_not_invalidated_immediately(self, seeded):
        """A thesis judged against the data that created it says nothing."""
        result = Pipeline(seeded).run_daily(limit=8)
        assert result["invalidated"] == []
        assert seeded.query(m.Thesis).filter(m.Thesis.status == "invalidated").count() == 0

    def test_thesis_conditions_are_measurable(self, seeded):
        Pipeline(seeded).run_daily(limit=5)
        conditions = seeded.query(m.ThesisCondition).all()
        assert conditions
        assert any(c.metric and c.comparator and c.threshold is not None for c in conditions)

    def test_ranking_records_movement(self, seeded):
        p = Pipeline(seeded)
        p.run_daily(limit=6)
        p.rerank()
        ranked = seeded.query(m.Candidate).filter(m.Candidate.rank.isnot(None)).all()
        assert ranked
        assert sorted(c.rank for c in ranked) == list(range(1, len(ranked) + 1))

    def test_rejected_candidates_are_not_ranked(self, seeded):
        Pipeline(seeded).run_daily(limit=14)
        for c in seeded.query(m.Candidate).filter(m.Candidate.verdict == "REJECTED"):
            assert c.rank is None

    def test_rank_is_cleared_when_a_candidate_becomes_rejected(self, seeded):
        """A stale rank on a rejected candidate misreports it as still ranked."""
        p = Pipeline(seeded)
        p.run_daily(limit=8)
        target = (
            seeded.query(m.Candidate)
            .filter(m.Candidate.rank.isnot(None))
            .order_by(m.Candidate.rank.asc()).first()
        )
        assert target is not None and target.rank == 1

        fin = (
            seeded.query(m.FinancialMetric)
            .filter(m.FinancialMetric.candidate_id == target.id).one()
        )
        fin.free_cash_flow, fin.cash = -190e6, 15e6
        fin.gross_margin, fin.shares_outstanding = 0.04, 44e6
        seeded.commit()

        p.run_daily(limit=8)
        seeded.refresh(target)
        assert target.verdict == "REJECTED"
        assert target.rank is None

    def test_dropping_out_of_the_ranking_is_explained(self, seeded):
        """The most important movement to explain is the one that vanishes."""
        p = Pipeline(seeded)
        p.run_daily(limit=8)
        target = (
            seeded.query(m.Candidate)
            .filter(m.Candidate.rank.isnot(None))
            .order_by(m.Candidate.rank.asc()).first()
        )
        fin = (
            seeded.query(m.FinancialMetric)
            .filter(m.FinancialMetric.candidate_id == target.id).one()
        )
        fin.free_cash_flow, fin.cash = -190e6, 15e6
        fin.gross_margin, fin.shares_outstanding = 0.04, 44e6
        seeded.commit()

        p.run_daily(limit=8)
        latest = (
            seeded.query(m.Score).filter(m.Score.candidate_id == target.id)
            .order_by(m.Score.created_at.desc()).first()
        )
        assert latest.change_reason
        assert "Dropped out of the ranking" in latest.change_reason
        assert "financial health deteriorated" in latest.change_reason

    def test_score_history_records_rank(self, seeded):
        Pipeline(seeded).run_daily(limit=5)
        ranked = seeded.query(m.Candidate).filter(m.Candidate.rank.isnot(None)).first()
        latest = (
            seeded.query(m.Score).filter(m.Score.candidate_id == ranked.id)
            .order_by(m.Score.created_at.desc()).first()
        )
        assert latest.rank == ranked.rank

    def test_historical_mode_suppresses_future_signals(self, seeded):
        """The whole backtest depends on this."""
        old = date.today() - timedelta(days=900)
        result = Pipeline(seeded, as_of=old).run_daily(limit=5)
        assert result["analysed"] > 0
        recent = seeded.query(m.Signal).filter(m.Signal.detected_at > old).count()
        assert recent == 0

    def test_agent_failure_does_not_abort_the_run(self, seeded, monkeypatch):
        from asymmetry.agents.analysis import TechnologyAgent

        def boom(self, ctx):
            raise RuntimeError("simulated agent failure")

        monkeypatch.setattr(TechnologyAgent, "build_prompt", boom)
        monkeypatch.setattr(TechnologyAgent, "heuristic", boom)
        result = Pipeline(seeded).run_daily(limit=3)
        assert result["analysed"] > 0


# ==========================================================================
class TestApi:
    @pytest.fixture()
    def client(self, seeded):
        from fastapi.testclient import TestClient
        from asymmetry.api.app import app
        from asymmetry.db.session import get_db

        Pipeline(seeded).run_daily(limit=6)
        seeded.commit()
        app.dependency_overrides[get_db] = lambda: seeded
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200 and r.json()["database"] is True

    def test_stats(self, client):
        body = client.get("/api/stats").json()
        assert body["total_candidates"] > 0
        assert "llm_mode" in body

    def test_list_candidates(self, client):
        body = client.get("/api/candidates?limit=5").json()
        assert body["total"] > 0 and len(body["items"]) <= 5
        assert "asymmetry_score" in body["items"][0]

    def test_candidate_detail_has_analysis(self, client):
        cid = client.get("/api/candidates?limit=1").json()["items"][0]["id"]
        d = client.get(f"/api/candidates/{cid}").json()
        for key in ("scenarios", "dimension_scores", "red_flags", "signals",
                    "claims", "score_history", "milestones"):
            assert key in d

    def test_scenarios_carry_a_disclaimer(self, client):
        for item in client.get("/api/candidates?limit=8").json()["items"]:
            d = client.get(f"/api/candidates/{item['id']}").json()
            if d.get("scenarios"):
                assert "not a prediction" in d["scenarios"]["disclaimer"].lower()
                return
        pytest.skip("no scenarios produced")

    def test_missing_candidate_is_404(self, client):
        assert client.get("/api/candidates/does-not-exist").status_code == 404

    def test_search_is_injection_safe(self, client):
        r = client.get("/api/candidates", params={"q": "'; DROP TABLE candidates; --"})
        assert r.status_code == 200
        assert client.get("/api/stats").json()["total_candidates"] > 0

    def test_invalid_sort_rejected(self, client):
        assert client.get("/api/candidates?sort=; DROP TABLE").status_code == 422

    def test_portfolio_is_labelled_simulated(self, client):
        assert client.get("/api/portfolio").json()["is_simulated"] is True

    def test_portfolio_rejects_overallocation(self, client):
        cid = client.get("/api/candidates?limit=1").json()["items"][0]["id"]
        r = client.post("/api/portfolio/positions",
                        json={"candidate_id": cid, "amount": 999_999})
        assert r.status_code == 400

    def test_portfolio_rejects_negative_amount(self, client):
        cid = client.get("/api/candidates?limit=1").json()["items"][0]["id"]
        r = client.post("/api/portfolio/positions", json={"candidate_id": cid, "amount": -5})
        assert r.status_code == 422

    def test_techgraph(self, client):
        body = client.get("/api/techgraph").json()
        assert body["nodes"] and body["drivers"] and body["bottlenecks"]

    def test_second_order_endpoint(self, client):
        body = client.get("/api/techgraph/second-order",
                          params={"driver": "AI compute demand"}).json()
        assert body["targets"] and body["chains"]
        assert body["targets"][0]["depth"] >= 2

    def test_second_order_unknown_driver_is_404(self, client):
        r = client.get("/api/techgraph/second-order", params={"driver": "nonsense"})
        assert r.status_code == 404

    def test_daily_report(self, client):
        body = client.get("/api/reports/daily").json()
        assert "disclaimer" in body and "new_discoveries" in body

    def test_no_endpoint_recommends_buying(self, client):
        """The system produces research, not instructions."""
        for path in ("/api/stats", "/api/reports/daily", "/api/opportunities/top",
                     "/api/candidates?limit=10", "/api/portfolio"):
            text = client.get(path).text.upper()
            for banned in ('"BUY"', '"SELL"', '"STRONG_BUY"', "RECOMMEND BUYING"):
                assert banned not in text
