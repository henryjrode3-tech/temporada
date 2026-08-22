import type { Composite, DimensionScore, RedFlag, RedFlagReport } from "./types";

/** Weights live here, not scattered through prompts. Sum = 1.00 */
export const DIMENSION_WEIGHTS: Record<string, number> = {
  future_market: 0.15,
  technology: 0.15,
  competitive_advantage: 0.15,
  early_signals: 0.15,
  valuation: 0.15,
  growth: 0.1,
  financial_health: 0.1,
  management: 0.05,
};

export const DIMENSION_LABELS: Record<string, string> = {
  future_market: "Future market",
  technology: "Technology",
  competitive_advantage: "Competitive advantage",
  early_signals: "Early signals",
  valuation: "Valuation",
  growth: "Growth",
  financial_health: "Financial health",
  management: "Management",
};

const round = (n: number, dp = 2) => {
  const f = 10 ** dp;
  return Math.round(n * f) / f;
};

export function buildRedFlagReport(flags: RedFlag[]): RedFlagReport {
  const points = flags.reduce((a, f) => a + f.points, 0);
  return {
    flags,
    red_flag_score: Math.min(100, points),
    penalty_points: Math.min(30, points),
  };
}

export function buildComposite(
  dimensions: DimensionScore[],
  report: RedFlagReport,
): Composite {
  const components: Record<string, number> = {};
  const contributions: Record<string, number> = {};
  let base = 0;
  for (const d of dimensions) {
    const w = DIMENSION_WEIGHTS[d.dimension] ?? 0;
    components[d.dimension] = d.score;
    contributions[d.dimension] = round(d.score * w);
    base += d.score * w;
  }
  const missing = Object.keys(DIMENSION_WEIGHTS).filter(
    (k) => !(k in components),
  );
  const penalty = report.penalty_points;
  const confidence =
    dimensions.length > 0
      ? round(
          (dimensions.reduce((a, d) => a + d.confidence, 0) /
            dimensions.length) *
            100,
          1,
        )
      : 0;

  return {
    overall_score: round(Math.max(0, base - penalty), 1),
    base_score: round(base, 1),
    penalty: round(penalty, 1),
    penalty_reasons: report.flags
      .filter((f) => f.points > 0)
      .map((f) => `${f.code}: ${f.title} (-${f.points})`),
    components,
    weights: DIMENSION_WEIGHTS,
    contributions,
    missing_dimensions: missing,
    confidence_score: confidence,
  };
}
