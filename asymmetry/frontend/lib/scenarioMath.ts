import type { ScenarioName, ScenarioResult, ScenarioSet } from "./types";

export interface ScenarioSpec {
  name: ScenarioName;
  probability: number;
  /** Revenue in the terminal year, absolute USD. */
  revenue: number;
  /** Net margin applied to terminal revenue. */
  margin: number;
  /** Market-cap multiple from today. */
  multiple: number;
  /** Share count multiple over the horizon (dilution). */
  dilution: number;
  valuation_path: "earnings" | "revenue";
  narrative: string;
  drivers: string[];
  /** Present when the engine reined the projection back in. */
  clamp?: string;
  assumptions: Record<string, number | null>;
}

const round = (n: number, dp = 2) => {
  const f = 10 ** dp;
  return Math.round(n * f) / f;
};

const cagr = (multiple: number, years: number) =>
  round(multiple ** (1 / years) - 1, 4);

export function buildScenario(
  spec: ScenarioSpec,
  currentMarketCap: number,
  currentRevenue: number | null,
  years: number,
): ScenarioResult {
  const perShare = spec.multiple / spec.dilution;
  const impliedRevCagr =
    currentRevenue && currentRevenue > 0
      ? cagr(spec.revenue / currentRevenue, years)
      : null;
  return {
    name: spec.name,
    probability: spec.probability,
    revenue: spec.revenue,
    earnings: Math.round(spec.revenue * spec.margin),
    future_market_cap: Math.round(currentMarketCap * spec.multiple),
    market_cap_multiple: round(spec.multiple),
    per_share_multiple: round(perShare),
    cagr: cagr(spec.multiple, years),
    per_share_cagr: cagr(perShare, years),
    valuation_path: spec.valuation_path,
    narrative: spec.narrative,
    drivers: spec.drivers,
    implied_revenue_cagr: impliedRevCagr,
    was_clamped: Boolean(spec.clamp),
    clamp_reason: spec.clamp ?? "",
    assumptions: spec.assumptions,
  };
}

/** Expected gain per unit of expected loss, log-compressed to 0-100. */
export function asymmetryFromScenarios(scenarios: ScenarioResult[]): {
  payoffRatio: number;
  score: number;
} {
  let gain = 0;
  let loss = 0;
  for (const s of scenarios) {
    const m = s.per_share_multiple;
    if (m > 1) gain += s.probability * (m - 1);
    else if (m < 1) loss += s.probability * (1 - m);
  }
  const ratio = loss > 0 ? gain / loss : gain > 0 ? 60 : 0;
  const score = Math.max(
    0,
    Math.min(100, Math.round((100 * Math.log10(1 + ratio)) / Math.log10(51))),
  );
  return { payoffRatio: round(ratio), score };
}

export function buildScenarioSet(args: {
  currentMarketCap: number;
  currentRevenue: number | null;
  years: number;
  specs: ScenarioSpec[];
  disclaimer: string;
}): ScenarioSet {
  const { currentMarketCap, currentRevenue, years, specs, disclaimer } = args;
  const scenarios = specs.map((s) =>
    buildScenario(s, currentMarketCap, currentRevenue, years),
  );

  const expectedMultiple = scenarios.reduce(
    (a, s) => a + s.probability * s.per_share_multiple,
    0,
  );
  const expectedValue = currentMarketCap * expectedMultiple;

  const sorted = [...scenarios].sort(
    (a, b) => a.per_share_multiple - b.per_share_multiple,
  );
  let cum = 0;
  let median = sorted[0]?.per_share_multiple ?? 0;
  for (const s of sorted) {
    cum += s.probability;
    if (cum >= 0.5) {
      median = s.per_share_multiple;
      break;
    }
  }

  const probLoss = scenarios
    .filter((s) => s.per_share_multiple < 1)
    .reduce((a, s) => a + s.probability, 0);
  const prob10x = scenarios
    .filter((s) => s.per_share_multiple >= 10)
    .reduce((a, s) => a + s.probability, 0);

  const upside = scenarios.filter((s) => s.per_share_multiple > 1);
  const totalUpside = upside.reduce(
    (a, s) => a + s.probability * (s.per_share_multiple - 1),
    0,
  );
  const tail = scenarios.find((s) => s.name === "extreme_bull");
  const tailContribution =
    totalUpside > 0 && tail
      ? (tail.probability * Math.max(0, tail.per_share_multiple - 1)) /
        totalUpside
      : 0;

  const { payoffRatio, score } = asymmetryFromScenarios(scenarios);

  return {
    scenarios,
    current_market_cap: currentMarketCap,
    years,
    expected_value: Math.round(expectedValue),
    expected_multiple: round(expectedMultiple),
    median_multiple: round(median),
    probability_of_loss: round(probLoss, 3),
    probability_of_10x: round(prob10x, 3),
    payoff_ratio: payoffRatio,
    asymmetry_score: score,
    tail_contribution: round(tailContribution, 3),
    is_tail_dominated: tailContribution > 0.5,
    clamped_scenarios: scenarios.filter((s) => s.was_clamped).map((s) => s.name),
    disclaimer,
  };
}
