import type {
  ConditionStatus,
  DebatePosition,
  Severity,
  SignalStrength,
  Verdict,
} from "./types";
import type { ScenarioSpec } from "./scenarioMath";

export const DISCLAIMER =
  "Scenario outputs are model estimates, not forecasts and not advice. Probabilities are subjective priors set by the analysis agents and revised as evidence arrives. Every figure below is conditional on assumptions listed with each branch; the median branch is a better summary of a typical outcome than the probability-weighted mean.";

/** [dimension, score 0-100, rationale, confidence 0-1] */
export type DimTuple = [string, number, string, number];
/** [code, severity, title, detail, points] */
export type FlagTuple = [string, Severity, string, string, number];
/** [signal_type, strength, current, baseline, window, detected_at, description] */
export type SignalTuple = [
  string,
  SignalStrength,
  number,
  number,
  string,
  string,
  string,
];
/** [claim, source_name, tier, url|null, published_at|null, confidence] */
export type ClaimTuple = [
  string,
  string,
  number,
  string | null,
  string | null,
  number,
];
/** [text, status, note] */
export type ConditionTuple = [string, ConditionStatus, string];
/** [agent, position, argument] */
export type DebateTuple = [string, DebatePosition, string];
/** [label, reachable, required_revenue, required_share|null, multiple, implied_cagr, commentary] */
export type MilestoneTuple = [
  string,
  boolean,
  number,
  number | null,
  number,
  number,
  string,
];

export interface CandidateSpec {
  id: string;
  name: string;
  ticker: string | null;
  asset_type: string;
  sector: string;
  industry: string;
  description: string;
  current_market_cap: number;
  revenue: number | null;
  revenue_growth: number | null;
  cash: number;
  debt: number;
  verdict: Verdict;
  verdict_reason: string;
  discovery_date: string;
  last_updated: string;
  rank: number | null;
  rank_change: number | null;
  risk_score: number;
  years: number;
  scenarios: ScenarioSpec[];
  dimensions: DimTuple[];
  flags: FlagTuple[];
  signals: SignalTuple[];
  claims: ClaimTuple[];
  thesis: { statement: string; status: string; created_at: string };
  conditions: ConditionTuple[];
  debate: DebateTuple[];
  milestones: MilestoneTuple[];
  reverse_valuation: {
    required_revenue: number;
    required_market_share: number | null;
    verdict: string;
    years: number;
  };
  /** Overall-score trail, oldest first. Asymmetry trail is derived. */
  score_history: number[];
}

const M = 1e6;
const B = 1e9;

export const SPECS: CandidateSpec[] = [];

// ---------------------------------------------------------------------------
// 1. Thermal management for datacenters
// ---------------------------------------------------------------------------
SPECS.push({
  id: "kairos-thermal",
  name: "Kairos Thermal Systems",
  ticker: "KRTH",
  asset_type: "public_equity",
  sector: "Thermal Infrastructure",
  industry: "Two-phase liquid cooling",
  description:
    "Designs and manufactures two-phase direct-to-chip cold plates and the dielectric coolant loops around them. Sells into hyperscale and colocation retrofits where rack density has outrun what air can remove. Owns the evaporator microchannel patents that most competing designs route around rather than license, and is one of three suppliers qualified on a 130 kW/rack reference design.",
  current_market_cap: 840 * M,
  revenue: 118 * M,
  revenue_growth: 0.62,
  cash: 96 * M,
  debt: 22 * M,
  verdict: "TOP_OPPORTUNITY",
  verdict_reason:
    "Physical bottleneck with a narrow qualified-supplier list, revenue already compounding above 60%, and a valuation that prices roughly the base case rather than the bull case. Downside is bounded by an existing profitable retrofit business.",
  discovery_date: "2025-11-04",
  last_updated: "2026-08-21",
  rank: 1,
  rank_change: 2,
  risk_score: 34,
  years: 10,
  scenarios: [
    {
      name: "bear",
      probability: 0.3,
      revenue: 145 * M,
      margin: 0.04,
      multiple: 0.45,
      dilution: 1.35,
      valuation_path: "revenue",
      narrative:
        "Air-side improvements and rear-door heat exchangers absorb most of the density increase. Two-phase stays a niche for the top 5% of racks; Kairos remains a component vendor with commodity margins and dilutes to fund a factory it does not fill.",
      drivers: [
        "Rear-door exchangers stretch air cooling to 80 kW/rack",
        "Hyperscalers standardise on single-phase cold plates for serviceability",
        "Coolant regulatory pressure on fluorinated dielectrics",
      ],
      assumptions: {
        terminal_ps_multiple: 2.6,
        net_margin: 0.04,
        share_dilution: 1.35,
        attach_rate: 0.05,
      },
    },
    {
      name: "base",
      probability: 0.42,
      revenue: 980 * M,
      margin: 0.12,
      multiple: 3.2,
      dilution: 1.25,
      valuation_path: "earnings",
      narrative:
        "Two-phase becomes the default above ~100 kW/rack. Kairos holds roughly a fifth of a market that grows with accelerator shipments, earns mid-teens gross margin on coolant refills, and trades as a specialised industrial rather than a growth story.",
      drivers: [
        "Accelerator TDP keeps rising through the horizon",
        "Kairos retains 2 of its 3 qualified-supplier slots",
        "Recurring coolant and service revenue reaches 30% of sales",
      ],
      assumptions: {
        terminal_pe: 22.9,
        net_margin: 0.12,
        share_dilution: 1.25,
        market_share: 0.19,
      },
    },
    {
      name: "bull",
      probability: 0.22,
      revenue: 3.4 * B,
      margin: 0.17,
      multiple: 11.5,
      dilution: 1.2,
      valuation_path: "earnings",
      narrative:
        "The microchannel patents hold through challenge and Kairos becomes the reference design rather than a supplier to it. Coolant loop attach extends into edge and industrial inference sites, and the installed base produces a consumables annuity larger than the original hardware sale.",
      drivers: [
        "Patent family survives IPR challenge filed 2026-03",
        "Design win on two of the three largest 2028 rack platforms",
        "Consumables annuity reaches 45% of revenue at 60% gross margin",
      ],
      assumptions: {
        terminal_pe: 16.7,
        net_margin: 0.17,
        share_dilution: 1.2,
        market_share: 0.34,
      },
    },
    {
      name: "extreme_bull",
      probability: 0.06,
      revenue: 4.8 * B,
      margin: 0.2,
      multiple: 28,
      dilution: 1.18,
      valuation_path: "earnings",
      narrative:
        "Thermal capacity becomes the binding constraint on compute deployment and the qualified supplier list never widens. Kairos prices to the value of the megawatt it unlocks rather than to the cost of the metal, and the market re-rates it as infrastructure rather than as a component maker.",
      drivers: [
        "Qualified supplier list stays at three through 2032",
        "Pricing shifts to a per-megawatt-unlocked basis",
        "Retrofit backlog exceeds two years of manufacturing capacity",
      ],
      clamp:
        "Unclamped model output implied $16.8B terminal revenue, a 64% 10-year revenue CAGR. Hardware businesses in the reference set have not sustained above 45%; terminal revenue was reduced to $4.8B (44.7% CAGR) and the market-cap multiple cut from 71x to 28x.",
      assumptions: {
        terminal_pe: 24.5,
        net_margin: 0.2,
        share_dilution: 1.18,
        market_share: 0.41,
      },
    },
  ],
  dimensions: [
    ["future_market", 88, "Thermal envelope is a hard physical constraint on accelerator deployment; demand is derived from compute capex, not from a discretionary budget.", 0.82],
    ["technology", 79, "Microchannel evaporator geometry is genuinely hard to copy; the moat is manufacturing yield, not the physics.", 0.74],
    ["competitive_advantage", 76, "Three qualified suppliers on the leading reference design, and qualification cycles run 14-18 months.", 0.71],
    ["early_signals", 84, "Hiring in field-service roles up 3.1x year over year and two new plant permits filed in Q2.", 0.8],
    ["valuation", 72, "7.1x forward sales for a business compounding above 60% with positive operating cash flow.", 0.86],
    ["growth", 81, "62% trailing revenue growth with backlog coverage of roughly five quarters.", 0.88],
    ["financial_health", 74, "Net cash of $74M, operating cash flow turned positive in the last two quarters.", 0.91],
    ["management", 63, "Operator-heavy team from thermal systems; capital allocation record is short and untested.", 0.55],
  ],
  flags: [
    ["CUST_CONC", "medium", "Customer concentration", "Two customers account for 61% of trailing revenue. A single requalification decision could remove roughly a third of sales.", 6],
    ["IP_LIT", "low", "Pending IP challenge", "An inter partes review of the core evaporator patent family was filed in March 2026. No decision expected before late 2027.", 3],
  ],
  signals: [
    ["hiring_velocity", "strong", 214, 69, "trailing 90d vs 2-year baseline", "2026-08-18T14:20:00Z", "Open field-service and commissioning roles jumped from 69 to 214, concentrated in three metros that map to announced datacenter builds."],
    ["patent_grants", "moderate", 11, 4, "trailing 12m vs 3-year baseline", "2026-07-30T09:05:00Z", "Eleven granted claims in the coolant-distribution family, up from a four-per-year baseline. Continuations suggest a deliberate fencing strategy."],
    ["procurement_mentions", "strong", 37, 8, "trailing 180d vs prior 180d", "2026-08-02T17:44:00Z", "Named as an approved thermal vendor in 37 colocation tender documents, against 8 in the prior period."],
  ],
  claims: [
    ["Qualified as one of three approved two-phase cold-plate suppliers on a 130 kW/rack reference platform.", "SEC 10-Q", 1, "https://www.sec.gov/", "2026-07-28", 0.92],
    ["Backlog of $612M at quarter end, up from $284M a year earlier.", "SEC 10-Q", 1, "https://www.sec.gov/", "2026-07-28", 0.95],
    ["Second manufacturing site permitted in Chandler, AZ with a stated 2027 production start.", "Maricopa County permit filing", 2, null, "2026-06-11", 0.78],
    ["Inter partes review petition filed against US patent covering microchannel evaporator geometry.", "USPTO PTAB docket", 1, "https://ptab.uspto.gov/", "2026-03-19", 0.9],
    ["Two-phase attach rate above 100 kW/rack described as 'the only practical option' by a hyperscaler thermal lead.", "Conference transcript", 3, null, "2026-05-22", 0.51],
  ],
  thesis: {
    statement:
      "If rack power density keeps climbing, heat removal becomes the binding constraint on compute deployment, and the short list of qualified two-phase suppliers captures pricing power that looks nothing like normal component economics.",
    status: "holding",
    created_at: "2025-11-19",
  },
  conditions: [
    ["Qualified supplier list stays at four or fewer through 2028", "holding", "Still three named suppliers on the leading platform as of the July filing."],
    ["Revenue growth stays above 35% annually", "holding", "62% trailing; backlog covers roughly five quarters."],
    ["Core evaporator patent family survives challenge", "at_risk", "PTAB instituted review in June 2026. Institution is not a ruling, but it removes the presumption we were leaning on."],
    ["Gross margin does not fall below 38%", "holding", "41.2% last quarter, down 90bp on coolant input costs."],
    ["Consumables revenue grows faster than hardware revenue", "unknown", "Not separately disclosed. Requested in the next investor call."],
  ],
  debate: [
    ["technology_agent", "bull", "The hard part is not the two-phase physics, it is holding 40-micron channel tolerances across a plate at production yield. Kairos has three years of yield-learning that a new entrant would have to repeat under a customer qualification clock."],
    ["contrarian_agent", "bear", "Every thermal bottleneck in this industry's history has been solved by the chip vendor changing the package, not by the cooling vendor winning. If the accelerator roadmap moves heat off the die differently, the qualified supplier list stops mattering."],
    ["market_agent", "bull", "Derived demand is the point. Nobody buys cooling because they want cooling; they buy it because the megawatt is already committed. That makes the demand curve unusually price-insensitive at the top of the density range."],
    ["financial_agent", "neutral", "Net cash and positive operating cash flow bound the downside, but the Chandler build will consume most of it. The bear case is not bankruptcy, it is a funded company with an underused plant."],
    ["valuation_agent", "bull", "At 7.1x forward sales the market is paying for the base case. The bull branch is available for free, which is the only condition under which this kind of position is worth holding."],
    ["fact_check_agent", "neutral", "The 'only practical option' quote is a conference remark with no transcript authority behind it. It is scored tier 3 and should not carry weight in the composite."],
  ],
  milestones: [
    ["2x from here", true, 460 * M, 0.09, 2, 0.072, "Requires roughly the current backlog converting on schedule with no share gain."],
    ["5x from here", true, 1.35 * B, 0.16, 5, 0.175, "Needs the Chandler site filled and coolant annuity building."],
    ["10x from here", true, 2.9 * B, 0.28, 10, 0.259, "Requires holding two qualified slots and consumables attach above 40%."],
    ["25x from here", true, 6.4 * B, 0.44, 25, 0.38, "Only reachable if the supplier list never widens and pricing moves to a per-megawatt basis."],
    ["100x from here", false, 24 * B, 0.92, 100, 0.585, "Implies more than 90% share of the addressable installed base. Rejected as physically implausible."],
  ],
  reverse_valuation: {
    required_revenue: 2.9 * B,
    required_market_share: 0.28,
    verdict:
      "A 10x from here requires roughly $2.9B of revenue in 2036, about 28% of the modelled two-phase market. That is demanding but not fantastical: it is roughly the share the incumbent air-side leader holds today in its own segment.",
    years: 10,
  },
  score_history: [58, 61, 63, 62, 67, 71, 74, 76, 79, 81],
});

// ---------------------------------------------------------------------------
// 2. Grid transformers
// ---------------------------------------------------------------------------
SPECS.push({
  id: "vestrand-power",
  name: "Vestrand Power Components",
  ticker: "VSPC",
  asset_type: "public_equity",
  sector: "Electrical Grid",
  industry: "High-voltage transformers and bushings",
  description:
    "Builds large power transformers and HV bushings from a single European works with an unusually deep order book. The plant holds one of a handful of Western presses capable of the core sizes utilities need for interconnection queues, and the qualification path for a new entrant runs close to a decade.",
  current_market_cap: 2.1 * B,
  revenue: 610 * M,
  revenue_growth: 0.28,
  cash: 140 * M,
  debt: 390 * M,
  verdict: "INVESTIGATE",
  verdict_reason:
    "Genuine physical scarcity with multi-year lead times and pricing power that has only recently started to show in margins. The question is whether the capacity constraint is a moat or simply a ceiling on the company's own growth.",
  discovery_date: "2025-09-12",
  last_updated: "2026-08-20",
  rank: 2,
  rank_change: 0,
  risk_score: 41,
  years: 12,
  scenarios: [
    {
      name: "bear",
      probability: 0.24,
      revenue: 720 * M,
      margin: 0.06,
      multiple: 0.62,
      dilution: 1.1,
      valuation_path: "earnings",
      narrative:
        "Interconnection reform stalls, utilities defer, and the order book that looked like scarcity turns out to have been a pull-forward. Vestrand runs its plant at 70% and its pricing power evaporates as Asian suppliers finish Western qualification.",
      drivers: [
        "Chinese and Indian suppliers complete qualification in three Western markets",
        "Grid capex plateaus after the current rate-case cycle",
        "Copper and grain-oriented steel costs stay elevated",
      ],
      assumptions: { terminal_pe: 30, net_margin: 0.06, share_dilution: 1.1 },
    },
    {
      name: "base",
      probability: 0.46,
      revenue: 1.9 * B,
      margin: 0.11,
      multiple: 2.4,
      dilution: 1.08,
      valuation_path: "earnings",
      narrative:
        "Electrification proceeds at the pace utilities can actually build. Vestrand adds one press, doubles capacity over the horizon, and holds pricing because the queue never clears. It becomes a very good industrial rather than a re-rated one.",
      drivers: [
        "Second press commissioned by 2029",
        "Lead times stay above 30 months through the horizon",
        "Service and retrofit revenue reaches 20% of sales",
      ],
      assumptions: {
        terminal_pe: 24.1,
        net_margin: 0.11,
        share_dilution: 1.08,
        capacity_multiple: 2,
      },
    },
    {
      name: "bull",
      probability: 0.24,
      revenue: 4.2 * B,
      margin: 0.15,
      multiple: 7.8,
      dilution: 1.06,
      valuation_path: "earnings",
      narrative:
        "Datacenter interconnection collides with electrification and transformer scarcity becomes a named line item in national industrial policy. Vestrand is subsidised into a capacity expansion it could not have financed alone and keeps the pricing that scarcity earned it.",
      drivers: [
        "Public co-financing of Western transformer capacity",
        "Datacenter interconnect demand adds a second demand curve",
        "Lead times exceed 48 months, moving contracts to cost-plus escalators",
      ],
      assumptions: {
        terminal_pe: 26,
        net_margin: 0.15,
        share_dilution: 1.06,
        capacity_multiple: 4,
      },
    },
    {
      name: "extreme_bull",
      probability: 0.06,
      revenue: 7.1 * B,
      margin: 0.17,
      multiple: 15,
      dilution: 1.05,
      valuation_path: "earnings",
      narrative:
        "Vestrand consolidates two smaller European works and becomes the only integrated Western supplier at the largest core sizes, at which point it is effectively a regulated utility supplier with monopoly economics and a state-backed order book.",
      drivers: [
        "Acquisition of two regional works clears competition review",
        "Strategic-asset designation in at least one jurisdiction",
        "Order book extends beyond eight years",
      ],
      clamp:
        "Unclamped model output implied a 21% 12-year revenue CAGR against a modelled market growing at 9%, i.e. more than 100% terminal share. Terminal revenue was reduced to $7.1B, capping implied share at 61%, and the multiple cut from 24x to 15x.",
      assumptions: {
        terminal_pe: 26.5,
        net_margin: 0.17,
        share_dilution: 1.05,
        capacity_multiple: 6,
      },
    },
  ],
  dimensions: [
    ["future_market", 84, "Electrification and interconnection demand are both structural and both bottlenecked on the same equipment.", 0.85],
    ["technology", 58, "Not a technology story. The advantage is a press, a qualification file, and eighty years of failure data.", 0.79],
    ["competitive_advantage", 82, "Ten-year qualification path and a press that cannot be bought off the shelf.", 0.83],
    ["early_signals", 66, "Order book extended 4 quarters in 18 months; pricing escalators appearing in new contracts.", 0.72],
    ["valuation", 61, "3.4x sales and 21x earnings for a capacity-constrained industrial is not obviously cheap.", 0.88],
    ["growth", 64, "28% growth is capacity-limited, not demand-limited, which caps the near-term rate.", 0.86],
    ["financial_health", 68, "Net debt of $250M against rising working capital needs for long-cycle builds.", 0.9],
    ["management", 71, "Conservative capital allocation, resisted the temptation to over-expand in the last cycle.", 0.66],
  ],
  flags: [
    ["CAPACITY_CEIL", "medium", "Growth capped by physical capacity", "Revenue cannot grow faster than press capacity regardless of demand. The second press is a 2029 event at the earliest.", 7],
    ["FX_CONC", "low", "Single-currency cost base", "Costs are euro-denominated while a growing share of the order book prices in dollars.", 2],
    ["LEVERAGE", "low", "Working-capital leverage", "Net debt to EBITDA of 1.9x with long-cycle contracts that consume cash before they deliver it.", 3],
  ],
  signals: [
    ["order_book_duration", "strong", 41, 26, "months, current vs 3-year baseline", "2026-08-14T08:00:00Z", "Quoted lead time extended from 26 to 41 months, and new contracts now carry raw-material escalators the company did not previously obtain."],
    ["import_substitution", "moderate", 0.18, 0.31, "share of Western installs from Asian suppliers", "2026-06-27T11:30:00Z", "Asian supplier share of Western large-transformer installs fell from 31% to 18% following two grid-security procurement rules."],
  ],
  claims: [
    ["Order backlog equivalent to 41 months of production at current capacity.", "Annual report", 1, null, "2026-03-14", 0.93],
    ["Second press investment decision deferred to FY2027 pending customer prepayment commitments.", "Earnings call transcript", 2, null, "2026-05-08", 0.81],
    ["Grid-security procurement rule restricts non-domestic suppliers on transmission-class equipment in two markets.", "Government register", 1, null, "2026-02-02", 0.88],
    ["Grain-oriented electrical steel supply described as 'the real constraint' by an industry association.", "Trade association briefing", 3, null, "2026-04-19", 0.47],
  ],
  thesis: {
    statement:
      "Western transformer capacity was allowed to atrophy for thirty years while electrification demand quietly compounded. Rebuilding that capacity takes a decade, and for that decade the few qualified works price like scarce infrastructure rather than like metal benders.",
    status: "holding",
    created_at: "2025-10-01",
  },
  conditions: [
    ["Quoted lead times stay above 24 months", "holding", "41 months and still extending."],
    ["No more than one new Western entrant qualifies before 2030", "holding", "No new qualification files known to be in progress."],
    ["Second press decision taken before end of 2027", "at_risk", "Deferred once already, to FY2027, pending customer prepayments."],
    ["Operating margin expands with pricing", "holding", "Up 210bp over two years as escalator contracts roll in."],
  ],
  debate: [
    ["market_agent", "bull", "This is the rare case where the constraint and the moat are the same object. You cannot enter without a press, and you cannot buy a press without a customer, and no customer will commit to an unqualified works."],
    ["contrarian_agent", "bear", "Scarcity attracts capital. There are four announced capacity expansions in this segment. If even two land, the pricing that justifies the current multiple goes away right as Vestrand's own new press comes online."],
    ["financial_agent", "bear", "Long-cycle contracts consume cash before they deliver it. Growth here is cash-negative, and the balance sheet has 1.9x net leverage before the expansion."],
    ["future_agent", "bull", "The second demand curve is the interesting part. Datacenter interconnection was not in anyone's transformer demand model three years ago and it now competes directly with utility orders for the same slots."],
    ["valuation_agent", "neutral", "21x earnings for a capacity-capped industrial only works if you believe pricing power persists past the expansion cycle. That is the whole debate, and the evidence is 18 months old."],
  ],
  milestones: [
    ["2x from here", true, 1.6 * B, 0.11, 2, 0.059, "Achievable on the current order book plus the second press."],
    ["5x from here", true, 3.4 * B, 0.22, 5, 0.14, "Requires the expansion plus sustained pricing through the cycle."],
    ["10x from here", false, 6.1 * B, 0.39, 10, 0.211, "Would need roughly 39% of the modelled Western market and a doubling of terminal margins."],
    ["25x from here", false, 14 * B, 0.86, 25, 0.301, "Implies near-monopoly share. Rejected."],
  ],
  reverse_valuation: {
    required_revenue: 6.1 * B,
    required_market_share: 0.39,
    verdict:
      "A 10x requires roughly $6.1B of revenue and about 39% of the modelled Western transmission-class market in 2038, at margins well above anything the company has posted. Reachable only under the industrial-policy branch, which is a political assumption rather than an industrial one.",
    years: 12,
  },
  score_history: [64, 66, 65, 69, 70, 72, 71, 73, 74, 74],
});
