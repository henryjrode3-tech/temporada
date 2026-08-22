/**
 * Typed contract for the Asymmetry Engine research API.
 *
 * This is a RESEARCH platform. Nothing here is a recommendation to transact.
 * Verdicts describe research posture, never an action.
 */

export type Verdict =
  | "TOP_OPPORTUNITY"
  | "INVESTIGATE"
  | "WATCH"
  | "INTERESTING"
  | "HIGH_RISK"
  | "THESIS_WEAKENING"
  | "THESIS_INVALIDATED"
  | "REJECTED";

export type ScenarioName = "bear" | "base" | "bull" | "extreme_bull";
export type SignalStrength = "extreme" | "strong" | "moderate" | "weak";
export type Severity = "critical" | "high" | "medium" | "low";
export type ConditionStatus = "holding" | "at_risk" | "broken" | "unknown";
export type DebatePosition = "bull" | "bear" | "neutral";

export interface ScenarioResult {
  name: ScenarioName;
  probability: number;
  revenue: number;
  earnings: number;
  future_market_cap: number;
  market_cap_multiple: number;
  per_share_multiple: number;
  cagr: number;
  per_share_cagr: number;
  valuation_path: "earnings" | "revenue";
  narrative: string;
  drivers: string[];
  implied_revenue_cagr: number | null;
  was_clamped: boolean;
  clamp_reason: string;
  assumptions: Record<string, number | null>;
}

export interface ScenarioSet {
  scenarios: ScenarioResult[];
  current_market_cap: number;
  years: number;
  expected_value: number;
  expected_multiple: number;
  median_multiple: number;
  probability_of_loss: number;
  probability_of_10x: number;
  payoff_ratio: number;
  asymmetry_score: number;
  tail_contribution: number;
  is_tail_dominated: boolean;
  clamped_scenarios: string[];
  disclaimer: string;
}

export interface Signal {
  signal_type: string;
  strength: SignalStrength;
  current_value: number;
  baseline_value: number;
  pct_change: number;
  z_score: number;
  window_label: string;
  detected_at: string;
  description: string;
  is_significant: boolean;
}

export interface RedFlag {
  code: string;
  severity: Severity;
  title: string;
  detail: string;
  points: number;
}

export interface DimensionScore {
  dimension: string;
  score: number;
  rationale: string;
  confidence: number;
}

export interface Claim {
  id: string;
  claim: string;
  source_name: string;
  source_tier: number;
  source_url: string | null;
  published_at: string | null;
  confidence: number;
}

export interface ThesisCondition {
  text: string;
  status: ConditionStatus;
  note: string;
}

export interface Thesis {
  statement: string;
  status: string;
  conditions: ThesisCondition[];
  created_at: string;
}

export interface DebateTurn {
  agent: string;
  position: DebatePosition;
  argument: string;
}

export interface ScenarioSummary {
  median_multiple: number;
  expected_multiple: number;
  probability_of_loss: number;
  is_tail_dominated: boolean;
}

export interface Candidate {
  id: string;
  name: string;
  ticker: string | null;
  asset_type: string;
  sector: string;
  industry: string | null;
  description: string;
  current_market_cap: number | null;
  revenue: number | null;
  revenue_growth: number | null;
  cash: number | null;
  debt: number | null;
  overall_score: number;
  asymmetry_score: number;
  risk_score: number;
  confidence_score: number;
  red_flag_score: number;
  verdict: Verdict;
  verdict_reason: string;
  discovery_date: string;
  last_updated: string;
  rank: number | null;
  rank_change: number | null;
  latest_signal: Signal | null;
  scenario_summary: ScenarioSummary | null;
}

export interface Milestone {
  label: string;
  reachable: boolean;
  required_revenue: number;
  required_market_share: number | null;
  multiple_from_here: number;
  implied_cagr: number;
  commentary: string;
}

export interface ReverseValuation {
  required_revenue: number;
  required_market_share: number | null;
  verdict: string;
  years: number;
}

export interface Composite {
  overall_score: number;
  base_score: number;
  penalty: number;
  penalty_reasons: string[];
  components: Record<string, number>;
  weights: Record<string, number>;
  contributions: Record<string, number>;
  missing_dimensions: string[];
  confidence_score: number;
}

export interface RedFlagReport {
  flags: RedFlag[];
  red_flag_score: number;
  penalty_points: number;
}

export interface ScorePoint {
  at: string;
  overall_score: number;
  asymmetry_score: number;
}

export interface CandidateDetail extends Candidate {
  scenarios: ScenarioSet | null;
  milestones: Milestone[];
  reverse_valuation: ReverseValuation | null;
  dimension_scores: DimensionScore[];
  composite: Composite | null;
  red_flags: RedFlagReport | null;
  signals: Signal[];
  claims: Claim[];
  thesis: Thesis | null;
  debate: DebateTurn[];
  score_history: ScorePoint[];
}

export interface DashboardStats {
  total_candidates: number;
  by_verdict: Record<string, number>;
  signals_last_7d: number;
  avg_asymmetry: number;
  last_pipeline_run: string | null;
  llm_mode: string;
}

export interface CandidateList {
  items: Candidate[];
  total: number;
}

export interface ThesisEntry extends Thesis {
  candidate_id: string;
  candidate_name: string;
}

export interface AgentRun {
  id: string;
  agent_name: string;
  candidate_id: string;
  candidate_name: string;
  model: string;
  stage: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  latency_ms: number;
  cache_hit: boolean;
  status: string;
  created_at: string;
}

export interface CandidateQuery {
  limit?: number;
  offset?: number;
  verdict?: string;
  sector?: string;
  q?: string;
}
