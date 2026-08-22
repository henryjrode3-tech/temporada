import type { CandidateSpec } from "./mockSpecs";

const M = 1e6;
const B = 1e9;

export const SPECS_D: CandidateSpec[] = [
  // -------------------------------------------------------------------------
  // 12. Semiconductor metrology
  // -------------------------------------------------------------------------
  {
    id: "veritas-metrology",
    name: "Veritas Metrology",
    ticker: "VRTM",
    asset_type: "public_equity",
    sector: "Semiconductors",
    industry: "In-line overlay and defect metrology",
    description:
      "Makes in-line overlay and buried-defect metrology tools for advanced nodes. Sells measurement, not patterning, which means it earns on every process step rather than on lithography capex cycles, and its installed base generates service and software revenue for a decade after the tool ships.",
    current_market_cap: 3.2 * B,
    revenue: 780 * M,
    revenue_growth: 0.24,
    cash: 420 * M,
    debt: 150 * M,
    verdict: "INVESTIGATE",
    verdict_reason:
      "High-quality business with a widening measurement problem as devices go three-dimensional. Less obscure than most of this file, so the asymmetry comes from durability rather than from mispricing.",
    discovery_date: "2025-09-29",
    last_updated: "2026-08-21",
    rank: 6,
    rank_change: 1,
    risk_score: 35,
    years: 10,
    scenarios: [
      {
        name: "bear",
        probability: 0.24,
        revenue: 900 * M,
        margin: 0.14,
        multiple: 0.7,
        dilution: 1.05,
        valuation_path: "earnings",
        narrative:
          "Device scaling stalls, fabs stretch tool life, and the metrology intensity increase that the thesis depends on does not arrive. Veritas remains a good business that grows with wafer starts and nothing more.",
        drivers: [
          "Node transitions slow beyond current roadmaps",
          "Metrology steps per wafer flatten",
          "Two competitors close the buried-defect capability gap",
        ],
        assumptions: { terminal_pe: 17.8, net_margin: 0.14, share_dilution: 1.05 },
      },
      {
        name: "base",
        probability: 0.46,
        revenue: 2.4 * B,
        margin: 0.22,
        multiple: 2.6,
        dilution: 1.04,
        valuation_path: "earnings",
        narrative:
          "Three-dimensional device architectures push measurement steps per wafer steadily higher. Veritas grows faster than wafer starts, and the installed-base service annuity compounds underneath.",
        drivers: [
          "Metrology steps per wafer rise with 3D architectures",
          "Service and software reach 35% of revenue",
          "Installed base exceeds 4,000 tools",
        ],
        assumptions: { terminal_pe: 15.8, net_margin: 0.22, share_dilution: 1.04 },
      },
      {
        name: "bull",
        probability: 0.24,
        revenue: 6.1 * B,
        margin: 0.28,
        multiple: 8,
        dilution: 1.03,
        valuation_path: "earnings",
        narrative:
          "Buried-defect detection becomes the yield-limiting capability at advanced nodes, and Veritas is the only vendor with a production-worthy tool. Metrology moves from a cost centre to the determinant of whether a process can be run at all.",
        drivers: [
          "Buried-defect detection becomes yield-limiting",
          "Sole-source position on two customer processes",
          "Software-driven yield analytics attach at high margin",
        ],
        assumptions: { terminal_pe: 15, net_margin: 0.28, share_dilution: 1.03 },
      },
      {
        name: "extreme_bull",
        probability: 0.06,
        revenue: 11 * B,
        margin: 0.31,
        multiple: 17,
        dilution: 1.02,
        valuation_path: "earnings",
        narrative:
          "Measurement becomes the constraint on process development itself. Veritas's data from thousands of installed tools produces yield models the fabs cannot reproduce internally, and the company earns a share of the yield it unlocks.",
        drivers: [
          "Cross-fab yield models become a licensed product",
          "Measurement intensity doubles per node",
          "Pricing shifts to a yield-share basis",
        ],
        clamp:
          "Unclamped output implied a 32x multiple on a 34% 10-year revenue CAGR. Capital-equipment vendors in the reference set have not sustained above 30%; terminal revenue was reduced to $11B (30.4% CAGR) and the multiple cut to 17x.",
        assumptions: { terminal_pe: 15.9, net_margin: 0.31, share_dilution: 1.02 },
      },
    ],
    dimensions: [
      ["future_market", 79, "Measurement intensity rises mechanically as devices become three-dimensional.", 0.83],
      ["technology", 83, "Buried-defect detection at production throughput is a capability no competitor has demonstrated.", 0.76],
      ["competitive_advantage", 78, "Installed base of 2,100 tools with recipe libraries that make displacement expensive.", 0.8],
      ["early_signals", 64, "Service revenue growing faster than tool revenue; two sole-source qualifications this year.", 0.72],
      ["valuation", 59, "4.1x sales and 24x earnings. A quality price, not a cheap one.", 0.87],
      ["growth", 71, "24% growth, cyclically damped by a wafer-starts pause in the first half.", 0.85],
      ["financial_health", 86, "Net cash $270M, consistently high free cash flow conversion.", 0.94],
      ["management", 76, "Twelve-year CEO tenure, R&D spend held through two downturns.", 0.74],
    ],
    flags: [
      ["CYCLICAL", "medium", "Semiconductor capex cyclicality", "Tool revenue has fallen more than 25% in each of the last three industry downturns, though service revenue has never declined.", 6],
      ["GEO_CONC", "medium", "Geographic concentration", "58% of revenue is delivered to fabs in a single region subject to export controls that have changed three times in four years.", 7],
    ],
    signals: [
      ["sole_source_quals", "moderate", 2, 0, "qualifications, trailing 12m", "2026-08-15T09:00:00Z", "Two sole-source qualifications on customer processes, the first time the company has held that status on a leading-edge flow."],
      ["service_mix", "moderate", 0.31, 0.24, "service share of revenue", "2026-07-30T08:00:00Z", "Service and software rose from 24% to 31% of revenue, which raises the floor under the next downturn."],
      ["patent_grants", "weak", 23, 18, "trailing 12m", "2026-06-21T10:00:00Z", "Patent grants up modestly and concentrated in buried-defect illumination, consistent with the stated roadmap."],
    ],
    claims: [
      ["Installed base of approximately 2,100 tools.", "Annual report", 1, null, "2026-02-25", 0.92],
      ["Two sole-source qualifications achieved on leading-edge customer processes.", "Earnings call transcript", 2, null, "2026-08-14", 0.81],
      ["Service and software revenue reached 31% of total revenue.", "SEC 10-Q", 1, "https://www.sec.gov/", "2026-07-29", 0.95],
      ["58% of revenue delivered to a single geographic region.", "SEC 10-K", 1, "https://www.sec.gov/", "2026-02-25", 0.94],
    ],
    thesis: {
      statement:
        "As devices stack vertically, the number of things that must be measured grows faster than the number of things that must be patterned. Metrology is therefore a structurally better position than lithography, and it is priced as though it were merely a supplier to it.",
      status: "holding",
      created_at: "2025-10-14",
    },
    conditions: [
      ["Metrology steps per wafer keep rising", "holding", "Customer disclosures point to roughly 9% annual growth in measurement steps."],
      ["Service revenue share keeps rising", "holding", "24% to 31% over two years."],
      ["No competitor demonstrates production buried-defect detection", "holding", "No competing tool announced at production throughput."],
      ["Export control changes do not remove regional access", "at_risk", "Rules revised three times in four years; the direction has been consistently restrictive."],
    ],
    debate: [
      ["technology_agent", "bull", "Buried-defect detection at throughput is the differentiator and nobody else has shipped one. The physics is hard and the throughput requirement is what makes it hard."],
      ["market_agent", "bull", "Metrology intensity is the underrated compounding variable. Each architectural transition adds measurement steps that never come back out of the flow."],
      ["contrarian_agent", "bear", "58% of revenue into one region under export controls that have tightened three times. That is not a footnote, it is a scenario that can remove half the business by administrative decision."],
      ["financial_agent", "bull", "31% service revenue means the next downturn hurts far less than the last three. That structurally changes the shape of the bear branch."],
      ["valuation_agent", "neutral", "24x earnings for a quality compounder is a reasonable price and not an asymmetric one. The bull branch is 8x over ten years, which is good rather than remarkable."],
    ],
    milestones: [
      ["2x from here", true, 1.5 * B, 0.14, 2, 0.072, "Requires only continuation of current growth and mix shift."],
      ["5x from here", true, 3.6 * B, 0.26, 5, 0.175, "Needs metrology intensity growth to persist through two node transitions."],
      ["10x from here", false, 7.2 * B, 0.44, 10, 0.259, "Requires roughly 44% of the modelled metrology market, above any current vendor's share."],
      ["25x from here", false, 16 * B, 0.83, 25, 0.38, "Rejected as exceeding plausible market share."],
    ],
    reverse_valuation: {
      required_revenue: 7.2 * B,
      required_market_share: 0.44,
      verdict:
        "A 10x needs about $7.2B of revenue in 2036, roughly 44% of the modelled advanced metrology market. That is above the share any vendor holds today. The realistic case here is a durable 3-5x rather than an asymmetric one, which is why it sits below the leaders in this file.",
      years: 10,
    },
    score_history: [69, 70, 71, 70, 72, 73, 74, 75, 75, 76],
  },

  // -------------------------------------------------------------------------
  // 13. Photonic computing - thesis invalidated
  // -------------------------------------------------------------------------
  {
    id: "ardent-photonic-computing",
    name: "Ardent Photonic Computing",
    ticker: "APCX",
    asset_type: "public_equity",
    sector: "Photonics",
    industry: "Optical matrix accelerators",
    description:
      "Built analogue optical matrix multipliers intended to run inference at a fraction of the energy of electronic accelerators. The thesis rested on a claimed energy-per-operation advantage that a third-party measurement has now contradicted at realistic precision.",
    current_market_cap: 190 * M,
    revenue: 6 * M,
    revenue_growth: -0.34,
    cash: 88 * M,
    debt: 12 * M,
    verdict: "THESIS_INVALIDATED",
    verdict_reason:
      "The central claim has been measured and does not hold. Independent testing put energy per operation at 3.1x the published figure once analogue-to-digital conversion at usable precision is included, which removes the entire reason for the thesis.",
    discovery_date: "2025-03-11",
    last_updated: "2026-08-12",
    rank: null,
    rank_change: null,
    risk_score: 91,
    years: 10,
    scenarios: [
      {
        name: "bear",
        probability: 0.68,
        revenue: 4 * M,
        margin: -0.9,
        multiple: 0.15,
        dilution: 1.7,
        valuation_path: "revenue",
        narrative:
          "The energy advantage does not survive conversion overhead. Customers end evaluations, the company winds down or is acquired for its photonic packaging patents at a fraction of cash.",
        drivers: [
          "Evaluations concluded without design wins",
          "Conversion overhead cannot be engineered away at usable precision",
          "Wind-down or patent sale",
        ],
        assumptions: { terminal_ps_multiple: 7, net_margin: -0.9, share_dilution: 1.7 },
      },
      {
        name: "base",
        probability: 0.22,
        revenue: 45 * M,
        margin: -0.2,
        multiple: 0.6,
        dilution: 1.6,
        valuation_path: "revenue",
        narrative:
          "The technology finds a narrow home in a signal-processing application where precision requirements are low and the conversion overhead does not dominate. A small, marginal business.",
        drivers: [
          "Niche adoption in low-precision signal processing",
          "Photonic packaging IP licensed",
          "Headcount reduced by roughly half",
        ],
        assumptions: { terminal_ps_multiple: 2.5, net_margin: -0.2, share_dilution: 1.6 },
      },
      {
        name: "bull",
        probability: 0.08,
        revenue: 280 * M,
        margin: 0.09,
        multiple: 4.2,
        dilution: 1.5,
        valuation_path: "revenue",
        narrative:
          "A precision-recovery technique closes the conversion gap and the original energy argument is restored. This branch requires a specific technical result that has not been demonstrated by anyone.",
        drivers: [
          "Analogue precision recovery demonstrated",
          "Energy advantage re-established at 8-bit equivalent",
          "One accelerator vendor licenses the approach",
        ],
        assumptions: { terminal_ps_multiple: 2.9, net_margin: 0.09, share_dilution: 1.5 },
      },
      {
        name: "extreme_bull",
        probability: 0.02,
        revenue: 900 * M,
        margin: 0.16,
        multiple: 14,
        dilution: 1.45,
        valuation_path: "revenue",
        narrative:
          "Retained only for completeness. Requires both the precision problem to be solved and optical compute to displace electronic inference at scale, neither of which has any current supporting evidence.",
        drivers: [
          "Precision problem solved",
          "Optical inference displaces electronic accelerators in a real workload",
        ],
        clamp:
          "Branch retained at minimum probability with the multiple reduced from 96x to 14x. With the central technical claim contradicted by measurement, the model does not permit a tail branch to carry meaningful expected value.",
        assumptions: { terminal_ps_multiple: 3, net_margin: 0.16, share_dilution: 1.45 },
      },
    ],
    dimensions: [
      ["future_market", 44, "Inference energy is a real problem; this is not a credible route to solving it.", 0.6],
      ["technology", 18, "The core claim failed independent measurement at usable precision.", 0.86],
      ["competitive_advantage", 21, "Packaging patents have some residual value; the compute approach does not.", 0.7],
      ["early_signals", 14, "Two evaluations ended, revenue declined 34%, three senior researchers departed.", 0.84],
      ["valuation", 38, "Trades near cash, which is the only support under the price.", 0.88],
      ["growth", 9, "Revenue declined 34% as evaluation contracts concluded.", 0.9],
      ["financial_health", 55, "$88M cash against a $26M burn; the balance sheet is the remaining asset.", 0.91],
      ["management", 33, "Published an energy figure that did not survive third-party measurement at realistic precision.", 0.72],
    ],
    flags: [
      ["CLAIM_FAILED", "critical", "Central technical claim contradicted", "Independent measurement put energy per operation at 3.1x the published figure once conversion at 8-bit equivalent precision is included.", 18],
      ["REV_DECLINE", "high", "Revenue declining", "Revenue fell 34% as two evaluation contracts concluded without progressing.", 10],
      ["TALENT_LOSS", "high", "Senior research departures", "Three named researchers from the original architecture team departed within one quarter of the measurement result.", 8],
      ["DISCLOSURE", "medium", "Published figure omitted conversion overhead", "The company's energy figure excluded analogue-to-digital conversion, which is not optional in any real deployment.", 6],
    ],
    signals: [
      ["independent_measurement", "extreme", 3.1, 1.0, "measured vs claimed energy per op", "2026-07-09T13:00:00Z", "Third-party laboratory measured energy per operation at 3.1x the company's published figure once conversion at 8-bit equivalent precision was included. This single result invalidates the thesis."],
      ["researcher_departures", "strong", 3, 0, "senior departures, trailing 90d", "2026-08-01T09:00:00Z", "Three senior researchers from the original architecture team left within a quarter of the measurement publication."],
      ["evaluation_contracts", "strong", 0, 2, "active evaluations", "2026-06-18T10:00:00Z", "Both active customer evaluations concluded without progressing to design wins."],
    ],
    claims: [
      ["Independent measurement of 3.1x the published energy per operation at 8-bit equivalent precision.", "Peer-reviewed measurement study", 1, null, "2026-07-08", 0.93],
      ["Both customer evaluation programmes concluded without design wins.", "SEC 8-K", 1, "https://www.sec.gov/", "2026-06-17", 0.92],
      ["Three senior research staff departures disclosed.", "SEC 8-K", 1, "https://www.sec.gov/", "2026-07-31", 0.9],
      ["Company response states conversion overhead 'can be engineered down substantially'.", "Company statement", 3, null, "2026-07-15", 0.4],
    ],
    thesis: {
      statement:
        "Analogue optical matrix multiplication reduces energy per operation by more than an order of magnitude, and inference energy is becoming the binding constraint on deployment.",
      status: "invalidated",
      created_at: "2025-03-26",
    },
    conditions: [
      ["Energy advantage holds at usable precision", "broken", "Measured at 3.1x the claimed figure at 8-bit equivalent precision. This was the thesis and it has failed."],
      ["At least one evaluation converts to a design win", "broken", "Both evaluations concluded without design wins."],
      ["Core architecture team remains intact", "broken", "Three senior departures in one quarter."],
      ["Cash covers 8 quarters", "holding", "Roughly 13 quarters. The balance sheet is now the only asset."],
    ],
    debate: [
      ["fact_check_agent", "bear", "The published energy figure excluded conversion. That is not a measurement dispute, it is an omission of a mandatory step, and it should have been caught when the thesis was written."],
      ["technology_agent", "bear", "Analogue compute always founders on precision and conversion. This file assumed that the team had solved it because they said so, and did not verify."],
      ["contrarian_agent", "bear", "Note what happened here: the position looked strongest right before the measurement. Score history was rising on hiring signals while nobody had checked the central number."],
      ["future_agent", "neutral", "Inference energy remains a real constraint. The thesis was about this route, not about the problem, and the problem is still there for someone else."],
      ["valuation_agent", "neutral", "Trading near cash means the market has already marked this. There is no residual asymmetry to capture; the file stays open only as a record of what went wrong."],
    ],
    milestones: [
      ["2x from here", false, 60 * M, 0.03, 2, 0.072, "Requires the precision problem to be solved. No demonstrated path."],
      ["5x from here", false, 190 * M, 0.09, 5, 0.175, "Not reachable on current evidence."],
      ["10x from here", false, 420 * M, 0.2, 10, 0.259, "Rejected."],
    ],
    reverse_valuation: {
      required_revenue: 420 * M,
      required_market_share: 0.2,
      verdict:
        "The reverse valuation is no longer meaningful. The technical premise that would generate any revenue at all has been contradicted by independent measurement, so the required-revenue figure describes a path with no demonstrated first step.",
      years: 10,
    },
    score_history: [64, 66, 68, 69, 70, 71, 69, 52, 34, 26],
  },

  // -------------------------------------------------------------------------
  // 14. Grid storage - rejected at screening
  // -------------------------------------------------------------------------
  {
    id: "novacell-grid-storage",
    name: "NovaCell Grid Storage",
    ticker: "NVCG",
    asset_type: "public_equity",
    sector: "Energy Storage",
    industry: "Iron-air long-duration storage",
    description:
      "Promotes a long-duration iron-air storage system with no commercial installations, no disclosed round-trip efficiency at scale, and a promotional density in its communications that the hype lexicon scores in the top percentile of the entire candidate set.",
    current_market_cap: 740 * M,
    revenue: 2 * M,
    revenue_growth: null,
    cash: 54 * M,
    debt: 96 * M,
    verdict: "REJECTED",
    verdict_reason:
      "Rejected at stage 1 screening. Hype density in the 98th percentile with no measurable counter-evidence, a going-concern qualification, and a related-party construction contract. No LLM analysis was run; the deterministic screen was sufficient.",
    discovery_date: "2026-01-07",
    last_updated: "2026-08-10",
    rank: null,
    rank_change: null,
    risk_score: 96,
    years: 10,
    scenarios: [
      {
        name: "bear",
        probability: 0.78,
        revenue: 3 * M,
        margin: -2.0,
        multiple: 0.05,
        dilution: 2.4,
        valuation_path: "revenue",
        narrative:
          "No commercial deployment materialises, the going-concern qualification becomes a restructuring, and the equity is substantially or entirely written off.",
        drivers: [
          "No commercial installation",
          "Going-concern qualification becomes restructuring",
          "Dilution or wipeout",
        ],
        assumptions: { terminal_ps_multiple: 12, net_margin: -2.0, share_dilution: 2.4 },
      },
      {
        name: "base",
        probability: 0.16,
        revenue: 40 * M,
        margin: -0.5,
        multiple: 0.3,
        dilution: 2.0,
        valuation_path: "revenue",
        narrative:
          "One subsidised demonstration project is built and operated at a loss, sustaining the company as a perpetual development-stage business.",
        drivers: [
          "Single subsidised demonstration",
          "Continued equity issuance",
        ],
        assumptions: { terminal_ps_multiple: 5.5, net_margin: -0.5, share_dilution: 2.0 },
      },
      {
        name: "bull",
        probability: 0.05,
        revenue: 300 * M,
        margin: 0.04,
        multiple: 2.2,
        dilution: 1.9,
        valuation_path: "revenue",
        narrative:
          "The chemistry works at grid scale and a utility commits. Retained because it is not physically impossible, not because there is evidence for it.",
        drivers: [
          "Round-trip efficiency disclosed and acceptable",
          "Utility commitment with a firm contract",
        ],
        assumptions: { terminal_ps_multiple: 5.4, net_margin: 0.04, share_dilution: 1.9 },
      },
      {
        name: "extreme_bull",
        probability: 0.01,
        revenue: 900 * M,
        margin: 0.1,
        multiple: 7,
        dilution: 1.85,
        valuation_path: "revenue",
        narrative:
          "Long-duration storage becomes a mandated grid asset and NovaCell is an early supplier. Retained at minimum probability only.",
        drivers: ["Mandated long-duration procurement", "Early-supplier position"],
        clamp:
          "Screening-stage candidates are capped at a 7x extreme branch. No scenario modelling beyond the deterministic screen was performed, so the model refuses to publish a larger tail on unverified inputs.",
        assumptions: { terminal_ps_multiple: 5.8, net_margin: 0.1, share_dilution: 1.85 },
      },
    ],
    dimensions: [
      ["future_market", 68, "Long-duration storage demand is real if round-trip economics work.", 0.55],
      ["technology", 22, "No disclosed round-trip efficiency at scale, no third-party validation.", 0.8],
      ["competitive_advantage", 15, "No installations, no patents of consequence, no manufacturing.", 0.78],
      ["early_signals", 11, "Announcements without contracts; hype density in the 98th percentile.", 0.86],
      ["valuation", 8, "$740M market capitalisation on $2M of revenue and a going-concern qualification.", 0.9],
      ["growth", 12, "Revenue not meaningfully measurable at this scale.", 0.7],
      ["financial_health", 6, "Going-concern qualification, net debt of $42M, negative operating cash flow.", 0.95],
      ["management", 18, "Related-party construction contract disclosed; prior venture wound down in 2019.", 0.74],
    ],
    flags: [
      ["GOING_CONCERN", "critical", "Going-concern qualification", "The auditor issued a going-concern qualification in the most recent annual report.", 20],
      ["HYPE_DENSITY", "critical", "Promotional language without counter-evidence", "Hype lexicon score in the 98th percentile of the candidate set, with no measurable counter-evidence in revenue, patents, citations or contracts to offset it.", 16],
      ["RELATED_PARTY", "high", "Related-party contract", "The construction contract for the demonstration site was awarded to an entity controlled by a board member.", 12],
      ["NO_VALIDATION", "high", "No third-party validation", "No independently verified round-trip efficiency at any scale has been published.", 10],
    ],
    signals: [
      ["hype_density", "extreme", 0.98, 0.41, "lexicon percentile", "2026-08-09T08:00:00Z", "Promotional language density in the 98th percentile of the candidate set, with no offsetting measurable evidence. This is the screen's strongest single rejection input."],
      ["press_releases", "strong", 34, 11, "trailing 12m", "2026-07-28T08:00:00Z", "Thirty-four press releases in twelve months against eleven in the prior period, with no corresponding change in contracted revenue."],
    ],
    claims: [
      ["Auditor issued a going-concern qualification.", "SEC 10-K", 1, "https://www.sec.gov/", "2026-03-30", 0.97],
      ["Demonstration site construction contract awarded to an entity controlled by a director.", "SEC 10-K related-party disclosure", 1, "https://www.sec.gov/", "2026-03-30", 0.95],
      ["No round-trip efficiency figure at pilot scale or above has been disclosed.", "Filing review", 1, null, "2026-03-30", 0.88],
      ["Company describes the technology as 'the definitive answer to grid storage'.", "Press release", 3, null, "2026-06-11", 0.35],
    ],
    thesis: {
      statement:
        "No thesis was constructed. The candidate was rejected at deterministic screening before any analytical work was commissioned.",
      status: "rejected_at_screen",
      created_at: "2026-01-07",
    },
    conditions: [
      ["Going-concern qualification removed", "broken", "Present in the most recent annual report."],
      ["Third-party round-trip efficiency published", "broken", "None published at any scale."],
      ["Related-party contract unwound or independently reviewed", "broken", "No review disclosed."],
    ],
    debate: [
      ["screening_agent", "bear", "Rejected at stage 1. Hype density above the 95th percentile combined with a going-concern qualification is a hard stop in the screen; no analytical budget was allocated."],
    ],
    milestones: [
      ["2x from here", false, 120 * M, 0.06, 2, 0.072, "Requires a commercial installation that does not exist."],
      ["5x from here", false, 340 * M, 0.16, 5, 0.175, "Rejected."],
    ],
    reverse_valuation: {
      required_revenue: 340 * M,
      required_market_share: 0.16,
      verdict:
        "No reverse valuation was performed beyond the screen. At $740M of market capitalisation on $2M of revenue with a going-concern qualification, the required-revenue calculation is not the binding question.",
      years: 10,
    },
    score_history: [22, 21, 19, 18, 17, 16, 15, 14, 13, 12],
  },
];
