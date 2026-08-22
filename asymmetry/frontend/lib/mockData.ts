import { DISCLAIMER, SPECS, type CandidateSpec } from "./mockSpecs";
import { SPECS_B } from "./specsB";
import { SPECS_C } from "./specsC";
import { SPECS_D } from "./specsD";
import { buildScenarioSet } from "./scenarioMath";
import { buildComposite, buildRedFlagReport } from "./scoreMath";
import type {
  AgentRun,
  Candidate,
  CandidateDetail,
  Claim,
  DashboardStats,
  DimensionScore,
  RedFlag,
  ScorePoint,
  Signal,
  Thesis,
  ThesisEntry,
} from "./types";

const ALL_SPECS: CandidateSpec[] = [...SPECS, ...SPECS_B, ...SPECS_C, ...SPECS_D];

const round = (n: number, dp = 1) => {
  const f = 10 ** dp;
  return Math.round(n * f) / f;
};

function buildSignals(spec: CandidateSpec): Signal[] {
  return spec.signals.map(
    ([type, strength, current, baseline, window, at, description]) => {
      const pct = baseline !== 0 ? (current - baseline) / Math.abs(baseline) : 0;
      const magnitude = Math.abs(pct);
      const z =
        strength === "extreme"
          ? 3.4 + magnitude * 0.6
          : strength === "strong"
            ? 2.3 + magnitude * 0.3
            : strength === "moderate"
              ? 1.5 + magnitude * 0.2
              : 0.8 + magnitude * 0.1;
      return {
        signal_type: type,
        strength,
        current_value: current,
        baseline_value: baseline,
        pct_change: round(pct, 4),
        z_score: round(Math.min(z, 6), 2),
        window_label: window,
        detected_at: at,
        description,
        is_significant: strength !== "weak",
      };
    },
  );
}

function buildDimensions(spec: CandidateSpec): DimensionScore[] {
  return spec.dimensions.map(([dimension, score, rationale, confidence]) => ({
    dimension,
    score,
    rationale,
    confidence,
  }));
}

function buildFlags(spec: CandidateSpec): RedFlag[] {
  return spec.flags.map(([code, severity, title, detail, points]) => ({
    code,
    severity,
    title,
    detail,
    points,
  }));
}

function buildClaims(spec: CandidateSpec): Claim[] {
  return spec.claims.map(
    ([claim, source_name, source_tier, source_url, published_at, confidence], i) => ({
      id: `${spec.id}-claim-${i + 1}`,
      claim,
      source_name,
      source_tier,
      source_url,
      published_at,
      confidence,
    }),
  );
}

function buildThesis(spec: CandidateSpec): Thesis {
  return {
    statement: spec.thesis.statement,
    status: spec.thesis.status,
    created_at: spec.thesis.created_at,
    conditions: spec.conditions.map(([text, status, note]) => ({
      text,
      status,
      note,
    })),
  };
}

/** Ten monthly snapshots ending in the current month. */
function buildScoreHistory(
  spec: CandidateSpec,
  finalAsymmetry: number,
): ScorePoint[] {
  const n = spec.score_history.length;
  const first = spec.score_history[0];
  const last = spec.score_history[n - 1];
  const span = last - first || 1;
  return spec.score_history.map((overall, i) => {
    const d = new Date(Date.UTC(2025, 10 + i, 1));
    const progress = (overall - first) / span;
    const asym = Math.max(
      0,
      Math.min(100, Math.round(finalAsymmetry - (1 - progress) * 12)),
    );
    return {
      at: d.toISOString().slice(0, 10),
      overall_score: overall,
      asymmetry_score: asym,
    };
  });
}

interface Built {
  candidate: Candidate;
  detail: CandidateDetail;
}

function build(spec: CandidateSpec): Built {
  const scenarios = buildScenarioSet({
    currentMarketCap: spec.current_market_cap,
    currentRevenue: spec.revenue,
    years: spec.years,
    specs: spec.scenarios,
    disclaimer: DISCLAIMER,
  });

  const flags = buildFlags(spec);
  const redFlagReport = buildRedFlagReport(flags);
  const dimensions = buildDimensions(spec);
  const composite = buildComposite(dimensions, redFlagReport);
  const signals = buildSignals(spec);
  const scoreHistory = buildScoreHistory(spec, scenarios.asymmetry_score);

  const candidate: Candidate = {
    id: spec.id,
    name: spec.name,
    ticker: spec.ticker,
    asset_type: spec.asset_type,
    sector: spec.sector,
    industry: spec.industry,
    description: spec.description,
    current_market_cap: spec.current_market_cap,
    revenue: spec.revenue,
    revenue_growth: spec.revenue_growth,
    cash: spec.cash,
    debt: spec.debt,
    overall_score: composite.overall_score,
    asymmetry_score: scenarios.asymmetry_score,
    risk_score: spec.risk_score,
    confidence_score: composite.confidence_score,
    red_flag_score: redFlagReport.red_flag_score,
    verdict: spec.verdict,
    verdict_reason: spec.verdict_reason,
    discovery_date: spec.discovery_date,
    last_updated: spec.last_updated,
    rank: spec.rank,
    rank_change: spec.rank_change,
    latest_signal: signals[0] ?? null,
    scenario_summary: {
      median_multiple: scenarios.median_multiple,
      expected_multiple: scenarios.expected_multiple,
      probability_of_loss: scenarios.probability_of_loss,
      is_tail_dominated: scenarios.is_tail_dominated,
    },
  };

  const detail: CandidateDetail = {
    ...candidate,
    scenarios,
    milestones: spec.milestones.map(
      ([
        label,
        reachable,
        required_revenue,
        required_market_share,
        multiple_from_here,
        implied_cagr,
        commentary,
      ]) => ({
        label,
        reachable,
        required_revenue,
        required_market_share,
        multiple_from_here,
        implied_cagr,
        commentary,
      }),
    ),
    reverse_valuation: spec.reverse_valuation,
    dimension_scores: dimensions,
    composite,
    red_flags: redFlagReport,
    signals,
    claims: buildClaims(spec),
    thesis: buildThesis(spec),
    debate: spec.debate.map(([agent, position, argument]) => ({
      agent,
      position,
      argument,
    })),
    score_history: scoreHistory,
  };

  return { candidate, detail };
}

const BUILT = ALL_SPECS.map(build);

/** Ranks are assigned from overall score; screened-out candidates stay unranked. */
const RANKABLE = BUILT.filter((b) => b.candidate.rank !== null).sort(
  (a, b) => b.candidate.overall_score - a.candidate.overall_score,
);
RANKABLE.forEach((b, i) => {
  b.candidate.rank = i + 1;
  b.detail.rank = i + 1;
});

export const MOCK_CANDIDATES: Candidate[] = BUILT.map((b) => b.candidate).sort(
  (a, b) => b.overall_score - a.overall_score,
);

export const MOCK_DETAILS: Record<string, CandidateDetail> = Object.fromEntries(
  BUILT.map((b) => [b.detail.id, b.detail]),
);

export const MOCK_TOP: Candidate[] = MOCK_CANDIDATES.filter(
  (c) => c.rank !== null,
).slice(0, 10);

/** Signals with candidate attribution, used to enrich the feed page. */
export const MOCK_SIGNAL_ATTRIBUTION: Record<
  string,
  { candidate_id: string; candidate_name: string; ticker: string | null }
> = {};

export const MOCK_SIGNALS: Signal[] = BUILT.flatMap((b) => {
  for (const s of b.detail.signals) {
    MOCK_SIGNAL_ATTRIBUTION[s.description] = {
      candidate_id: b.candidate.id,
      candidate_name: b.candidate.name,
      ticker: b.candidate.ticker,
    };
  }
  return b.detail.signals;
}).sort((a, b) => (a.detected_at < b.detected_at ? 1 : -1));

export const MOCK_THESES: ThesisEntry[] = BUILT.filter(
  (b) => b.detail.thesis !== null,
).map((b) => ({
  ...(b.detail.thesis as Thesis),
  candidate_id: b.candidate.id,
  candidate_name: b.candidate.name,
}));

export const MOCK_STATS: DashboardStats = (() => {
  const byVerdict: Record<string, number> = {};
  for (const c of MOCK_CANDIDATES) {
    byVerdict[c.verdict] = (byVerdict[c.verdict] ?? 0) + 1;
  }
  const avg =
    MOCK_CANDIDATES.reduce((a, c) => a + c.asymmetry_score, 0) /
    MOCK_CANDIDATES.length;
  return {
    total_candidates: MOCK_CANDIDATES.length,
    by_verdict: byVerdict,
    signals_last_7d: MOCK_SIGNALS.filter(
      (s) => new Date(s.detected_at) >= new Date("2026-08-15T00:00:00Z"),
    ).length,
    avg_asymmetry: round(avg, 1),
    last_pipeline_run: "2026-08-22T04:12:00Z",
    llm_mode: "mock (deterministic, no API keys required)",
  };
})();

// ---------------------------------------------------------------------------
// Agent activity log
// ---------------------------------------------------------------------------

const AGENTS: [string, string, string][] = [
  ["screening_agent", "stage_1_screen", "deterministic"],
  ["triage_agent", "stage_2_triage", "claude-haiku"],
  ["technology_agent", "stage_3_deep", "claude-sonnet"],
  ["market_agent", "stage_3_deep", "claude-sonnet"],
  ["competition_agent", "stage_3_deep", "claude-sonnet"],
  ["financial_agent", "stage_3_deep", "claude-sonnet"],
  ["signal_agent", "stage_3_deep", "claude-haiku"],
  ["contrarian_agent", "stage_3_deep", "claude-sonnet"],
  ["future_agent", "stage_3_deep", "claude-sonnet"],
  ["valuation_agent", "stage_3_deep", "claude-sonnet"],
  ["fact_check_agent", "stage_3_deep", "claude-haiku"],
  ["debate_moderator", "stage_3_debate", "claude-sonnet"],
  ["judge_agent", "stage_3_judge", "claude-opus"],
];

const COST_PER_MTOK: Record<string, [number, number]> = {
  deterministic: [0, 0],
  "claude-haiku": [0.8, 4],
  "claude-sonnet": [3, 15],
  "claude-opus": [15, 75],
};

/** Deterministic pseudo-random so the log is stable between renders. */
function seeded(n: number): number {
  const x = Math.sin(n * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

export const MOCK_AGENT_RUNS: AgentRun[] = (() => {
  const runs: AgentRun[] = [];
  const ranked = MOCK_CANDIDATES.filter((c) => c.rank !== null).slice(0, 8);
  let i = 0;
  const start = Date.UTC(2026, 7, 22, 4, 12, 0);
  for (const candidate of ranked) {
    for (const [agent_name, stage, model] of AGENTS) {
      i += 1;
      const r = seeded(i);
      const cacheHit = r > 0.72;
      const tokensIn =
        model === "deterministic" ? 0 : Math.round(2200 + r * 9400);
      const tokensOut =
        model === "deterministic" ? 0 : Math.round(320 + seeded(i + 500) * 1800);
      const [inRate, outRate] = COST_PER_MTOK[model];
      const cost = cacheHit
        ? 0
        : (tokensIn / 1e6) * inRate + (tokensOut / 1e6) * outRate;
      const failed = seeded(i + 77) > 0.965;
      runs.push({
        id: `run-${String(i).padStart(4, "0")}`,
        agent_name,
        candidate_id: candidate.id,
        candidate_name: candidate.name,
        model,
        stage,
        tokens_in: cacheHit ? 0 : tokensIn,
        tokens_out: cacheHit ? 0 : tokensOut,
        cost_usd: Math.round(cost * 10000) / 10000,
        latency_ms: cacheHit
          ? Math.round(8 + r * 30)
          : Math.round(900 + r * 14000),
        cache_hit: cacheHit,
        status: failed ? "error" : "ok",
        created_at: new Date(start - i * 137_000).toISOString(),
      });
    }
  }
  return runs.sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
})();
