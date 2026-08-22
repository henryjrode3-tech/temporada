import type { CandidateSpec } from "./mockSpecs";

const M = 1e6;
const B = 1e9;

export const SPECS_C: CandidateSpec[] = [
  // -------------------------------------------------------------------------
  // 8. Quantum sensing
  // -------------------------------------------------------------------------
  {
    id: "halcyon-quantum-sensing",
    name: "Halcyon Quantum Sensing",
    ticker: "HQSN",
    asset_type: "public_equity",
    sector: "Quantum",
    industry: "Atomic magnetometry and gravimetry",
    description:
      "Builds optically pumped magnetometers and cold-atom gravimeters. Ignores quantum computing entirely, which is the interesting part: sensing works today, ships today, and is sold to magnetoencephalography labs, subsurface survey firms and navigation programmes that need to operate without satellite positioning.",
    current_market_cap: 270 * M,
    revenue: 9 * M,
    revenue_growth: 1.12,
    cash: 74 * M,
    debt: 4 * M,
    verdict: "WATCH",
    verdict_reason:
      "Working physics with paying customers, but at $9M of revenue the company is a research programme with a share price. The interesting decision point is instrument cost per unit, not the science.",
    discovery_date: "2026-02-14",
    last_updated: "2026-08-18",
    rank: 11,
    rank_change: 3,
    risk_score: 69,
    years: 15,
    scenarios: [
      {
        name: "bear",
        probability: 0.36,
        revenue: 18 * M,
        margin: -0.1,
        multiple: 0.28,
        dilution: 1.7,
        valuation_path: "revenue",
        narrative:
          "Quantum sensors stay laboratory instruments. Unit costs never fall enough to leave the research market, and Halcyon becomes a small instrument maker funded by grants and periodic equity raises.",
        drivers: [
          "Instrument cost stays above $180k per unit",
          "Navigation programmes stay in evaluation indefinitely",
          "Grant funding replaces commercial revenue",
        ],
        assumptions: { terminal_ps_multiple: 4.2, net_margin: -0.1, share_dilution: 1.7 },
      },
      {
        name: "base",
        probability: 0.38,
        revenue: 140 * M,
        margin: 0.13,
        multiple: 3.4,
        dilution: 1.5,
        valuation_path: "earnings",
        narrative:
          "Magnetoencephalography moves from a handful of shielded rooms to a wearable clinical product, and Halcyon supplies the sensor. A good instrument business with one genuinely large clinical market attached.",
        drivers: [
          "Wearable MEG receives clinical clearance",
          "Sensor cost falls below $40k per channel-array",
          "Subsurface survey becomes a repeatable second market",
        ],
        assumptions: { terminal_pe: 50.4, net_margin: 0.13, share_dilution: 1.5 },
      },
      {
        name: "bull",
        probability: 0.2,
        revenue: 620 * M,
        margin: 0.2,
        multiple: 16,
        dilution: 1.42,
        valuation_path: "earnings",
        narrative:
          "Cold-atom gravimetry becomes a standard navigation input where satellite positioning cannot be trusted, and the same production line serves both clinical and navigation demand at volume economics.",
        drivers: [
          "Navigation programme moves to production quantities",
          "Shared production line across clinical and defence",
          "Unit cost falls below $25k",
        ],
        assumptions: { terminal_pe: 34.8, net_margin: 0.2, share_dilution: 1.42 },
      },
      {
        name: "extreme_bull",
        probability: 0.06,
        revenue: 1.5 * B,
        margin: 0.24,
        multiple: 52,
        dilution: 1.38,
        valuation_path: "earnings",
        narrative:
          "Quantum sensing becomes an ordinary component category the way MEMS accelerometers did, and the company that industrialised the manufacturing process rather than the physics captures the volume.",
        drivers: [
          "Sensor integrated into vehicle and handset navigation stacks",
          "Manufacturing yield moves the category to consumer economics",
          "Halcyon licenses its packaging process",
        ],
        clamp:
          "Unclamped output implied a 15-year revenue CAGR of 47% from a $9M base, reaching $3.9B. No instrument business in the reference set has sustained that; terminal revenue was capped at $1.5B (39% CAGR) and the multiple reduced from 118x to 52x.",
        assumptions: { terminal_pe: 58.5, net_margin: 0.24, share_dilution: 1.38 },
      },
    ],
    dimensions: [
      ["future_market", 72, "Clinical MEG and denied-environment navigation are both large if the cost curve cooperates.", 0.58],
      ["technology", 84, "Working hardware with published field results, not a simulation or a roadmap.", 0.78],
      ["competitive_advantage", 62, "Packaging and vapour-cell manufacturing know-how; three university spin-outs pursuing the same approach.", 0.55],
      ["early_signals", 66, "Two navigation evaluation contracts and a clinical trial site expansion.", 0.62],
      ["valuation", 41, "30x sales on $9M of revenue prices a great deal of the base case already.", 0.74],
      ["growth", 64, "112% growth on a base small enough that the percentage carries little information.", 0.51],
      ["financial_health", 58, "$74M cash against a $19M annual burn; roughly fifteen quarters of runway.", 0.89],
      ["management", 66, "Founding physicists still leading; a manufacturing hire in 2025 was the first real commercial signal.", 0.6],
    ],
    flags: [
      ["PRE_REVENUE_SCALE", "high", "Revenue too small to validate anything", "At $9M, revenue cannot distinguish between a real market and a handful of enthusiastic laboratories.", 10],
      ["COST_CURVE", "medium", "Thesis depends on an unproven cost curve", "The base case requires per-unit cost to fall roughly 4x. No published data yet demonstrates that trajectory at volume.", 8],
      ["KEY_PERSON", "medium", "Key person concentration", "Two founding physicists are named in the risk factors as individually material to the sensor programme.", 5],
    ],
    signals: [
      ["clinical_sites", "strong", 14, 4, "active sites", "2026-08-04T10:00:00Z", "Active clinical MEG sites rose from 4 to 14 in twelve months, including three outside the original academic network."],
      ["evaluation_contracts", "moderate", 2, 0, "navigation programmes", "2026-05-12T09:30:00Z", "Two navigation evaluation contracts awarded, the first commercial engagement outside research funding."],
      ["publication_citations", "moderate", 212, 88, "citations, trailing 12m", "2026-06-25T08:00:00Z", "Citations of the company's vapour-cell packaging papers grew from 88 to 212, indicating the approach is being adopted as a reference by other groups."],
    ],
    claims: [
      ["Fourteen active clinical sites using the wearable MEG array.", "Company presentation", 2, null, "2026-08-03", 0.74],
      ["Two navigation evaluation contracts awarded, values not disclosed.", "SEC 8-K", 1, "https://www.sec.gov/", "2026-05-11", 0.9],
      ["Risk factors name two individuals as material to the sensor development programme.", "SEC 10-K", 1, "https://www.sec.gov/", "2026-03-11", 0.96],
      ["Per-unit instrument cost described as 'roughly $180,000 today, with a path below $50,000'.", "Earnings call transcript", 2, null, "2026-05-14", 0.63],
    ],
    thesis: {
      statement:
        "Quantum sensing already works, unlike quantum computing, and the remaining problem is manufacturing rather than physics. Companies that solve manufacturing problems in categories that already function are a different risk class from companies waiting for a breakthrough.",
      status: "holding",
      created_at: "2026-02-28",
    },
    conditions: [
      ["Per-unit cost falls below $90k by end 2028", "unknown", "$180k today with a stated path; no interim data point yet."],
      ["Clinical site count keeps growing at least 50% annually", "holding", "4 to 14 over twelve months."],
      ["Cash runway stays above 8 quarters", "holding", "About 15 quarters at the current burn."],
      ["At least one navigation contract converts to production", "unknown", "Both still in evaluation."],
    ],
    debate: [
      ["technology_agent", "bull", "The distinction that matters is that this ships. Field results are published, instruments are in third-party hands, and the failure modes are known. That is a completely different risk profile from a computing roadmap."],
      ["contrarian_agent", "bear", "Instrument companies that need a 4x cost reduction to reach their market usually get 1.5x and then explain why the market was never the point."],
      ["market_agent", "neutral", "Fourteen clinical sites is real but small. The number that would change my view is repeat orders from a site that already has one, and that is not disclosed."],
      ["financial_agent", "neutral", "Fifteen quarters of runway is genuinely comfortable and removes the near-term financing risk that usually dominates a company this size."],
      ["valuation_agent", "bear", "30x sales on $9M. The price already contains the base case. Watch, and revisit if the cost curve produces a data point."],
    ],
    milestones: [
      ["2x from here", true, 45 * M, 0.04, 2, 0.047, "Requires clinical site growth to continue and unit cost to fall modestly."],
      ["5x from here", true, 130 * M, 0.11, 5, 0.111, "Needs clinical clearance for the wearable array."],
      ["10x from here", true, 280 * M, 0.2, 10, 0.166, "Requires both clinical volume and a navigation production order."],
      ["50x from here", true, 1.3 * B, 0.52, 50, 0.297, "Only reachable if the category reaches component economics."],
      ["200x from here", false, 5.6 * B, 0.96, 200, 0.412, "Exceeds the modelled market. Rejected."],
    ],
    reverse_valuation: {
      required_revenue: 280 * M,
      required_market_share: 0.2,
      verdict:
        "A 10x needs roughly $280M of revenue in 2041, about 20% of the modelled quantum sensing instrument market. The required share is unremarkable. The required cost reduction is the whole question, and there is no evidence for it yet beyond a management statement.",
      years: 15,
    },
    score_history: [48, 52, 55, 57, 59, 58, 61, 63, 64, 66],
  },

  // -------------------------------------------------------------------------
  // 9. Biomanufacturing
  // -------------------------------------------------------------------------
  {
    id: "meridian-biomanufacturing",
    name: "Meridian Biomanufacturing",
    ticker: "MBIO",
    asset_type: "public_equity",
    sector: "Biomanufacturing",
    industry: "Precision fermentation capacity",
    description:
      "Operates contract precision-fermentation capacity: large steel, downstream purification, and the regulatory files that let a customer's molecule be made at scale. Sells capacity rather than products, which was meant to make it indifferent to which customer's molecule succeeded.",
    current_market_cap: 430 * M,
    revenue: 58 * M,
    revenue_growth: -0.12,
    cash: 41 * M,
    debt: 210 * M,
    verdict: "THESIS_WEAKENING",
    verdict_reason:
      "The capacity-scarcity premise has not held. Utilisation fell as customers delayed scale-up, and two of the three conditions the thesis was built on are now at risk or broken.",
    discovery_date: "2025-05-09",
    last_updated: "2026-08-13",
    rank: 14,
    rank_change: -6,
    risk_score: 74,
    years: 10,
    scenarios: [
      {
        name: "bear",
        probability: 0.44,
        revenue: 60 * M,
        margin: -0.08,
        multiple: 0.22,
        dilution: 1.6,
        valuation_path: "revenue",
        narrative:
          "Fermentation capacity turns out to be abundant rather than scarce. Utilisation stays below 50%, the debt is restructured, and the steel is eventually sold at a discount to a strategic buyer.",
        drivers: [
          "Utilisation stays below 50%",
          "Debt covenant breach forces restructuring",
          "Competing capacity comes online in Asia at lower cost",
        ],
        assumptions: { terminal_ps_multiple: 1.6, net_margin: -0.08, share_dilution: 1.6 },
      },
      {
        name: "base",
        probability: 0.34,
        revenue: 190 * M,
        margin: 0.09,
        multiple: 1.9,
        dilution: 1.35,
        valuation_path: "earnings",
        narrative:
          "Two or three customer molecules reach commercial scale and fill the plant. Meridian becomes a modestly profitable contract manufacturer with a repaired balance sheet and no particular pricing power.",
        drivers: [
          "Two customer products reach commercial volume",
          "Utilisation recovers above 70%",
          "Debt refinanced on non-distressed terms",
        ],
        assumptions: { terminal_pe: 47.8, net_margin: 0.09, share_dilution: 1.35 },
      },
      {
        name: "bull",
        probability: 0.17,
        revenue: 640 * M,
        margin: 0.15,
        multiple: 8.5,
        dilution: 1.28,
        valuation_path: "earnings",
        narrative:
          "Precision fermentation reaches the volumes its advocates predicted, capacity becomes genuinely scarce, and Meridian's regulatory files become the reason customers cannot simply move to cheaper steel elsewhere.",
        drivers: [
          "Regulatory files create real switching costs",
          "Utilisation above 90% with pricing power",
          "Third suite built with customer prepayment",
        ],
        assumptions: { terminal_pe: 38.1, net_margin: 0.15, share_dilution: 1.28 },
      },
      {
        name: "extreme_bull",
        probability: 0.05,
        revenue: 1.4 * B,
        margin: 0.18,
        multiple: 24,
        dilution: 1.25,
        valuation_path: "earnings",
        narrative:
          "Fermentation-derived proteins and materials displace a meaningful share of conventional production, and permitted large-scale capacity with existing regulatory files becomes the constraint on the whole category.",
        drivers: [
          "Category reaches commodity-scale volumes",
          "Permitting becomes the constraint on new capacity",
          "Long-term take-or-pay contracts replace spot capacity sales",
        ],
        clamp:
          "Unclamped output implied $3.1B terminal revenue against declining current revenue, an internally inconsistent projection. Terminal revenue was capped at $1.4B and the multiple cut from 53x to 24x; the branch is retained only because the underlying category outcome is not disproved.",
        assumptions: { terminal_pe: 41, net_margin: 0.18, share_dilution: 1.25 },
      },
    ],
    dimensions: [
      ["future_market", 58, "The category is real but its volume timeline has slipped repeatedly and materially.", 0.54],
      ["technology", 61, "Downstream purification expertise is genuine; the upstream fermentation is not differentiated.", 0.7],
      ["competitive_advantage", 44, "Regulatory files create some switching cost, but Asian capacity is cheaper and expanding.", 0.66],
      ["early_signals", 32, "Utilisation falling, two customer programmes delayed, no new contracts in three quarters.", 0.79],
      ["valuation", 52, "7.4x sales on declining revenue with $169M of net debt.", 0.81],
      ["growth", 21, "Revenue declined 12% year over year as customers deferred scale-up.", 0.9],
      ["financial_health", 27, "Net debt of $169M against $58M of revenue and negative operating cash flow.", 0.93],
      ["management", 48, "Built the plant on schedule; badly misjudged demand timing and financed it with debt.", 0.65],
    ],
    flags: [
      ["REV_DECLINE", "high", "Revenue declining", "Revenue fell 12% year over year on lower utilisation, against a thesis that assumed capacity scarcity.", 11],
      ["COVENANT", "critical", "Covenant pressure", "Net leverage of 4.8x against a 5.0x covenant tested quarterly. A further utilisation decline triggers it.", 15],
      ["DEMAND_TIMING", "high", "Category timeline slipped", "Two customer scale-up programmes delayed by more than a year, and the category's volume forecasts have been revised down twice.", 9],
      ["ASSET_HEAVY", "medium", "Fixed cost base cannot flex", "Roughly 70% of the cost base is fixed, so utilisation declines fall almost entirely to the operating line.", 6],
    ],
    signals: [
      ["utilisation", "strong", 0.47, 0.71, "quarterly average", "2026-08-11T08:00:00Z", "Plant utilisation fell from 71% to 47% over four quarters. This directly contradicts the capacity-scarcity premise of the thesis."],
      ["contract_signings", "moderate", 0, 3, "trailing 12m vs prior 12m", "2026-07-02T12:00:00Z", "No new capacity contracts signed in twelve months, against three in the prior period."],
      ["competing_capacity", "moderate", 240, 90, "kilolitres announced, Asia", "2026-06-08T07:00:00Z", "Announced competing capacity in Asia rose from 90 to 240 kilolitres, at stated build costs well below Meridian's."],
    ],
    claims: [
      ["Plant utilisation of 47% in the most recent quarter, down from 71%.", "Quarterly report", 1, null, "2026-08-10", 0.95],
      ["Net leverage of 4.8x against a 5.0x maintenance covenant.", "Credit agreement amendment", 1, null, "2026-05-30", 0.92],
      ["Two customer scale-up programmes delayed beyond 2027.", "Earnings call transcript", 2, null, "2026-08-10", 0.83],
      ["Competing Asian capacity announced at roughly 60% of Meridian's per-litre build cost.", "Trade publication", 3, null, "2026-06-05", 0.49],
    ],
    thesis: {
      statement:
        "Precision fermentation needs large sterile steel with regulatory files attached, that capacity takes four years to build, and demand was going to arrive before supply did. Owning capacity rather than molecules was meant to make the outcome indifferent to which customer succeeded.",
      status: "weakening",
      created_at: "2025-05-22",
    },
    conditions: [
      ["Utilisation stays above 65%", "broken", "47% and falling. This was the central premise and it has failed."],
      ["Net leverage stays below 4.0x", "broken", "4.8x against a 5.0x covenant."],
      ["At least two new capacity contracts per year", "broken", "None in twelve months."],
      ["Category volume forecasts do not decline", "at_risk", "Revised down twice in eighteen months."],
      ["Regulatory files produce measurable switching cost", "unknown", "No customer has attempted to move, so the switching cost remains untested."],
    ],
    debate: [
      ["contrarian_agent", "bear", "Three of five thesis conditions are broken, not at risk. The correct action is to write down the position's conviction, not to look for a reason the utilisation number is misleading."],
      ["financial_agent", "bear", "4.8x leverage against a 5.0x covenant with 70% fixed costs and falling utilisation. The bear branch is not a de-rating, it is a restructuring."],
      ["market_agent", "neutral", "The category is not dead, it is late. But late is fatal when the balance sheet was built for on-time."],
      ["future_agent", "bull", "If the category does arrive, permitted large-scale capacity will be scarce and this plant will exist. That is why the tail branch survives at 5% rather than being deleted."],
      ["valuation_agent", "bear", "Equity below the debt in an asset-heavy business is an option, and this one is being priced as a business. Downgrade."],
    ],
    milestones: [
      ["2x from here", true, 130 * M, 0.09, 2, 0.072, "Requires utilisation back above 70% and a refinancing."],
      ["5x from here", true, 340 * M, 0.19, 5, 0.175, "Needs two customer molecules at commercial volume."],
      ["10x from here", false, 690 * M, 0.36, 10, 0.259, "Requires the category to arrive at the originally forecast scale."],
      ["25x from here", false, 1.7 * B, 0.74, 25, 0.38, "Implies most of the Western market. Rejected."],
    ],
    reverse_valuation: {
      required_revenue: 690 * M,
      required_market_share: 0.36,
      verdict:
        "A 10x requires about $690M of revenue in 2036, roughly 36% of the modelled Western contract fermentation market, from a plant currently running below half utilisation with a covenant test every quarter. The path requires the balance sheet to survive long enough to reach it.",
      years: 10,
    },
    score_history: [68, 67, 64, 61, 58, 54, 49, 45, 41, 38],
  },

  // -------------------------------------------------------------------------
  // 10. OT cybersecurity
  // -------------------------------------------------------------------------
  {
    id: "bastion-ot-security",
    name: "Bastion OT Security",
    ticker: "BSTN",
    asset_type: "public_equity",
    sector: "Cybersecurity",
    industry: "Operational technology and ICS protection",
    description:
      "Monitors and segments industrial control networks: substations, water treatment, pipeline SCADA, factory floors. Speaks the industrial protocols that IT security products do not, and its detection library is built from a decade of packet captures nobody else has.",
    current_market_cap: 1.15 * B,
    revenue: 198 * M,
    revenue_growth: 0.37,
    cash: 190 * M,
    debt: 0,
    verdict: "INVESTIGATE",
    verdict_reason:
      "Recurring revenue, a genuine data moat in protocol coverage, and a regulatory tailwind that converts a discretionary purchase into a mandated one. Priced as software but growing like infrastructure.",
    discovery_date: "2025-07-21",
    last_updated: "2026-08-20",
    rank: 5,
    rank_change: 3,
    risk_score: 37,
    years: 10,
    scenarios: [
      {
        name: "bear",
        probability: 0.26,
        revenue: 300 * M,
        margin: 0.06,
        multiple: 0.6,
        dilution: 1.2,
        valuation_path: "revenue",
        narrative:
          "The large IT security platforms add adequate industrial protocol support and bundle it at no incremental cost. Bastion's detection library remains better and stops mattering, because good enough arrives free with a renewal.",
        drivers: [
          "Platform vendors bundle OT modules",
          "Regulatory mandates written to accept IT-platform coverage",
          "Net revenue retention falls below 100%",
        ],
        assumptions: { terminal_ps_multiple: 2.3, net_margin: 0.06, share_dilution: 1.2 },
      },
      {
        name: "base",
        probability: 0.44,
        revenue: 950 * M,
        margin: 0.18,
        multiple: 3.4,
        dilution: 1.15,
        valuation_path: "earnings",
        narrative:
          "Industrial security becomes a compliance line item across utilities and manufacturing. Bastion is the specialist that the platforms partner with rather than replace, and compounds at software economics.",
        drivers: [
          "Mandated monitoring in two more regulated sectors",
          "Net revenue retention holds above 115%",
          "Protocol library extends to building management systems",
        ],
        assumptions: { terminal_pe: 22.9, net_margin: 0.18, share_dilution: 1.15 },
      },
      {
        name: "bull",
        probability: 0.24,
        revenue: 2.8 * B,
        margin: 0.24,
        multiple: 11,
        dilution: 1.12,
        valuation_path: "earnings",
        narrative:
          "A significant industrial incident converts OT security from a compliance cost into a board-level priority across every sector with physical consequences. Bastion's protocol coverage becomes the procurement requirement itself.",
        drivers: [
          "Major incident with physical consequences",
          "Protocol coverage written into procurement standards",
          "Expansion into transport and building systems",
        ],
        assumptions: { terminal_pe: 18.8, net_margin: 0.24, share_dilution: 1.12 },
      },
      {
        name: "extreme_bull",
        probability: 0.06,
        revenue: 5.4 * B,
        margin: 0.27,
        multiple: 26,
        dilution: 1.1,
        valuation_path: "earnings",
        narrative:
          "Every device that touches physical infrastructure ends up under continuous monitoring by regulation, and the detection library becomes a de facto standard that competitors license rather than rebuild.",
        drivers: [
          "Continuous monitoring mandated across critical infrastructure",
          "Detection library licensed to platform vendors",
          "International standards converge on Bastion's protocol taxonomy",
        ],
        clamp:
          "Unclamped output implied $9.8B terminal revenue, a 48% 10-year CAGR, and a 61x multiple. Capped to $5.4B (39% CAGR) and 26x; the model does not accept sustained sub-50% CAGRs at this revenue base without a named acquisition path.",
        assumptions: { terminal_pe: 22.2, net_margin: 0.27, share_dilution: 1.1 },
      },
    ],
    dimensions: [
      ["future_market", 83, "Attack surface grows mechanically as industrial systems are networked; regulation converts that into budget.", 0.81],
      ["technology", 74, "Protocol coverage built from a decade of captures that cannot be synthesised quickly.", 0.73],
      ["competitive_advantage", 71, "Data moat is real but the distribution advantage sits with the platform vendors.", 0.69],
      ["early_signals", 79, "Net revenue retention 121%, and three regulated sectors added mandated monitoring this year.", 0.84],
      ["valuation", 67, "5.8x sales for 37% growth with 121% net retention and no debt.", 0.85],
      ["growth", 78, "37% growth, largely subscription, with expansion revenue outpacing new logos.", 0.89],
      ["financial_health", 88, "$190M cash, no debt, free cash flow positive for six quarters.", 0.94],
      ["management", 72, "Sector veterans; resisted a platform acquisition in 2024 that would have capped the outcome.", 0.68],
    ],
    flags: [
      ["PLATFORM_RISK", "medium", "Bundling risk from platform vendors", "Two large IT security platforms have announced industrial modules. Historically, adequate bundled functionality has displaced better standalone products in this industry.", 8],
      ["SALES_CYCLE", "low", "Long regulated sales cycles", "Median sales cycle of 11 months makes quarterly results lumpy and forecasting unreliable.", 3],
    ],
    signals: [
      ["net_retention", "strong", 1.21, 1.08, "trailing 12m", "2026-08-07T09:15:00Z", "Net revenue retention rose from 108% to 121%, driven by expansion into additional sites within existing industrial customers rather than new logos."],
      ["regulatory_mandates", "strong", 3, 0, "sectors added, trailing 12m", "2026-07-19T10:00:00Z", "Three additional regulated sectors introduced continuous monitoring requirements that Bastion's product satisfies as delivered."],
      ["incident_disclosures", "moderate", 27, 14, "disclosed OT incidents, trailing 12m", "2026-06-30T16:00:00Z", "Publicly disclosed industrial control incidents nearly doubled, which historically leads budget allocation by roughly four quarters."],
    ],
    claims: [
      ["Net revenue retention of 121% for the trailing twelve months.", "SEC 10-Q", 1, "https://www.sec.gov/", "2026-08-06", 0.94],
      ["Three regulated sectors introduced continuous OT monitoring requirements in the last year.", "Government register", 1, null, "2026-07-18", 0.89],
      ["Protocol library covers 412 industrial protocols and dialects.", "Product documentation", 2, null, "2026-05-01", 0.77],
      ["Free cash flow positive in each of the last six quarters.", "SEC 10-Q", 1, "https://www.sec.gov/", "2026-08-06", 0.95],
      ["Two IT security platform vendors announced industrial modules during the year.", "Vendor press releases", 2, null, "2026-04-22", 0.86],
    ],
    thesis: {
      statement:
        "Industrial systems were networked without being secured, and the protocols involved are obscure enough that general security products cannot see them. Regulation is converting that gap from an acknowledged risk into a mandated budget line.",
      status: "holding",
      created_at: "2025-08-04",
    },
    conditions: [
      ["Net revenue retention stays above 110%", "holding", "121% and rising."],
      ["No platform vendor achieves comparable protocol coverage", "at_risk", "Two announced modules; coverage claims not yet independently verified."],
      ["Regulated sector count keeps expanding", "holding", "Three added this year."],
      ["Free cash flow stays positive", "holding", "Six consecutive quarters."],
    ],
    debate: [
      ["technology_agent", "bull", "412 protocols and dialects is not a feature list, it is a decade of access to networks that nobody gets to observe twice. That is the kind of dataset that cannot be bought."],
      ["contrarian_agent", "bear", "Security history is a graveyard of better standalone products beaten by adequate bundled ones. The buyer is a CISO consolidating vendors, not an engineer comparing detection rates."],
      ["market_agent", "bull", "Regulation changes the buyer. When monitoring is mandated, the purchase moves to the compliance owner, who buys the thing that demonstrably satisfies the rule rather than the thing already on the contract."],
      ["signal_agent", "bull", "121% net retention with expansion coming from additional sites inside existing customers is the strongest single number in this file. It means the product spreads once it is inside."],
      ["financial_agent", "neutral", "No debt, positive free cash flow, and 5.8x sales. There is not much financial risk here; the entire question is competitive."],
    ],
    milestones: [
      ["2x from here", true, 420 * M, 0.08, 2, 0.072, "Requires only continuation of current growth for roughly three years."],
      ["5x from here", true, 1.1 * B, 0.17, 5, 0.175, "Needs mandated monitoring to continue spreading across sectors."],
      ["10x from here", true, 2.2 * B, 0.29, 10, 0.259, "Requires holding the specialist position against platform bundling."],
      ["25x from here", true, 4.9 * B, 0.51, 25, 0.38, "Only under the standard-setting branch where competitors license the library."],
      ["100x from here", false, 18 * B, 0.95, 100, 0.585, "Exceeds the modelled market. Rejected."],
    ],
    reverse_valuation: {
      required_revenue: 2.2 * B,
      required_market_share: 0.29,
      verdict:
        "A 10x needs about $2.2B of revenue in 2036 and roughly 29% of the modelled OT security market, at software margins the company already demonstrates in part. Among the candidates in this file, this is the least demanding 10x path in absolute terms.",
      years: 10,
    },
    score_history: [61, 63, 66, 68, 69, 71, 73, 74, 76, 77],
  },

  // -------------------------------------------------------------------------
  // 11. Solid-state batteries (tail-dominated)
  // -------------------------------------------------------------------------
  {
    id: "solidyne-energy",
    name: "Solidyne Energy",
    ticker: "SLDN",
    asset_type: "public_equity",
    sector: "Energy Storage",
    industry: "Sulphide solid-state cells",
    description:
      "Developing sulphide-electrolyte solid-state cells with a pilot line running at low yield. Has published cycle-life data that is genuinely better than the field and has never manufactured anything at volume. The gap between those two facts is the entire investment question.",
    current_market_cap: 2.4 * B,
    revenue: 31 * M,
    revenue_growth: 0.44,
    cash: 610 * M,
    debt: 0,
    verdict: "HIGH_RISK",
    verdict_reason:
      "Expected value is dominated by a single low-probability branch. The median outcome is a substantial loss. Treated as a small option, not a position, and the median rather than the mean is the honest summary.",
    discovery_date: "2025-04-03",
    last_updated: "2026-08-19",
    rank: 12,
    rank_change: -2,
    risk_score: 86,
    years: 12,
    scenarios: [
      {
        name: "bear",
        probability: 0.46,
        revenue: 40 * M,
        margin: -0.4,
        multiple: 0.12,
        dilution: 1.8,
        valuation_path: "revenue",
        narrative:
          "Sulphide cells never leave the pilot line at acceptable yield. The moisture-handling problem that has defeated every previous attempt defeats this one too, cash runs down, and the company is acquired for its patents.",
        drivers: [
          "Pilot yield stays below 60%",
          "Dry-room capex proves prohibitive at volume",
          "Automotive partners revert to improved liquid-electrolyte cells",
        ],
        assumptions: { terminal_ps_multiple: 7.2, net_margin: -0.4, share_dilution: 1.8 },
      },
      {
        name: "base",
        probability: 0.34,
        revenue: 420 * M,
        margin: 0.06,
        multiple: 1.4,
        dilution: 1.55,
        valuation_path: "revenue",
        narrative:
          "Solid-state ships in low volume into premium applications where energy density justifies the cost: aviation, defence, medical. A real business, far below what today's price implies.",
        drivers: [
          "Qualification in two premium non-automotive applications",
          "Yield reaches 80% at pilot scale",
          "Cost stays above $180/kWh",
        ],
        assumptions: { terminal_ps_multiple: 8, net_margin: 0.06, share_dilution: 1.55 },
      },
      {
        name: "bull",
        probability: 0.15,
        revenue: 3.1 * B,
        margin: 0.14,
        multiple: 9.5,
        dilution: 1.45,
        valuation_path: "earnings",
        narrative:
          "Yield and dry-room economics are solved, an automotive partner commits to a platform, and solid-state takes the top of the vehicle market where range and charge time are worth paying for.",
        drivers: [
          "Volume yield above 92%",
          "One automotive platform commitment",
          "Cost below $110/kWh at scale",
        ],
        assumptions: { terminal_pe: 52.5, net_margin: 0.14, share_dilution: 1.45 },
      },
      {
        name: "extreme_bull",
        probability: 0.05,
        revenue: 14 * B,
        margin: 0.16,
        multiple: 62,
        dilution: 1.4,
        valuation_path: "earnings",
        narrative:
          "Solid-state becomes the default cell chemistry and Solidyne's electrolyte process is the one that scaled first. Licensing plus own production makes it a structural participant in a market measured in hundreds of gigawatt-hours.",
        drivers: [
          "Chemistry becomes the industry default",
          "Electrolyte process licensed to two large cell makers",
          "Own capacity exceeds 90 GWh",
        ],
        clamp:
          "Unclamped output implied $41B terminal revenue and a 210x multiple, which would make Solidyne larger than the entire modelled solid-state market in 2038. Terminal revenue was capped at $14B and the multiple reduced to 62x. This branch remains the dominant contributor to expected value even after clamping, which is itself a warning.",
        assumptions: { terminal_pe: 66.4, net_margin: 0.16, share_dilution: 1.4 },
      },
    ],
    dimensions: [
      ["future_market", 87, "If solid-state works at volume the addressable market is enormous and well understood.", 0.76],
      ["technology", 64, "Published cycle life leads the field; manufacturability is unproven and is the part that has always failed.", 0.49],
      ["competitive_advantage", 51, "Patent position is decent; six well-funded groups are pursuing the same chemistry.", 0.55],
      ["early_signals", 46, "Pilot yield improving but still far below volume requirements; no platform commitment.", 0.63],
      ["valuation", 22, "77x sales on pilot-line revenue. The price already contains a successful outcome.", 0.8],
      ["growth", 54, "44% growth on $31M of development and sample revenue.", 0.58],
      ["financial_health", 71, "$610M cash and no debt gives roughly six years of runway at current burn.", 0.92],
      ["management", 55, "Strong electrochemistry team, thin manufacturing leadership for a company whose problem is manufacturing.", 0.57],
    ],
    flags: [
      ["TAIL_DOMINATED", "high", "Expected value rests on one improbable branch", "The 5% extreme branch supplies most of the probability-weighted upside. The median outcome is a loss of roughly 10% of capital.", 12],
      ["MANUFACTURING_UNPROVEN", "critical", "Never manufactured at volume", "Every prior sulphide solid-state programme has failed at the transition from pilot to volume, specifically on moisture control and yield.", 14],
      ["VALUATION_EXTREME", "high", "Price embeds success", "77x trailing sales on development revenue. Even the bull branch delivers less than a 10x from the current price.", 10],
      ["COMPETITION", "medium", "Six funded competitors on the same chemistry", "Three are subsidiaries of large cell manufacturers with volume manufacturing experience Solidyne lacks.", 6],
    ],
    signals: [
      ["pilot_yield", "moderate", 0.71, 0.52, "pilot line, quarterly", "2026-08-06T09:00:00Z", "Pilot yield improved from 52% to 71%. Real progress, still far below the roughly 92% needed for volume economics."],
      ["cycle_life", "strong", 1420, 900, "cycles to 80% capacity", "2026-05-28T11:00:00Z", "Independently verified 1,420 cycles to 80% capacity, ahead of the best published competitor figure of 900."],
      ["partner_activity", "weak", 1, 2, "active automotive evaluations", "2026-07-14T15:00:00Z", "Active automotive evaluations fell from two to one after a partner redirected its programme to improved liquid-electrolyte cells."],
    ],
    claims: [
      ["Pilot line yield of 71%, up from 52% a year earlier.", "Earnings call transcript", 2, null, "2026-08-05", 0.78],
      ["Independently verified 1,420 cycles to 80% capacity retention.", "Third-party test report", 1, null, "2026-05-27", 0.88],
      ["One automotive evaluation programme concluded without progressing to a platform commitment.", "SEC 8-K", 1, "https://www.sec.gov/", "2026-07-13", 0.91],
      ["Cash and equivalents of $610M with no debt outstanding.", "SEC 10-Q", 1, "https://www.sec.gov/", "2026-08-05", 0.97],
      ["Volume manufacturing requires yield above 90% to reach target cost, per company statements.", "Investor day presentation", 2, null, "2026-03-12", 0.72],
    ],
    thesis: {
      statement:
        "Solid-state cells solve energy density and thermal safety simultaneously, and sulphide chemistry has the best measured cycle life. If any group solves the manufacturing problem the prize is very large, and that possibility is the only reason this file remains open.",
      status: "holding_with_reservations",
      created_at: "2025-04-18",
    },
    conditions: [
      ["Pilot yield improves at least 15 points annually", "holding", "52% to 71% over twelve months."],
      ["At least one automotive evaluation stays active", "at_risk", "Down to one after a partner redirected in July."],
      ["Cycle-life lead over published competitors maintained", "holding", "1,420 versus 900 cycles."],
      ["Cash runway stays above 12 quarters", "holding", "Roughly 24 quarters at current burn."],
      ["Cost per kWh trajectory published and credible", "unknown", "No independently verified cost data has been published."],
    ],
    debate: [
      ["technology_agent", "bull", "The cycle-life result is independently verified and leads the field by a wide margin. That is not a press release, it is a third-party test report, and it is the one hard fact here."],
      ["contrarian_agent", "bear", "Cycle life in a pouch cell made by PhDs in a dry room tells you nothing about yield on a line. Every failed solid-state programme had excellent coin-cell data."],
      ["financial_agent", "neutral", "Six years of runway removes financing risk entirely, which is unusual for this profile. The company will get to find out whether it works, which is more than most such companies manage."],
      ["valuation_agent", "bear", "At 77x sales even the bull branch returns less than 10x. That is the definition of a poor asymmetry: the upside has already been paid for and the downside has not."],
      ["future_agent", "bull", "Retaining the tail branch is correct. The point of this platform is not to avoid improbable outcomes, it is to size them honestly, and 5% of a very large number is worth keeping on the page."],
      ["fact_check_agent", "neutral", "The 90% yield requirement is a company statement, not an independent figure. It is used in the bear branch as a hurdle, which is the conservative direction, so it is retained."],
    ],
    milestones: [
      ["2x from here", true, 620 * M, 0.06, 2, 0.059, "Requires premium-application qualification and a yield above 80%."],
      ["5x from here", true, 1.8 * B, 0.14, 5, 0.14, "Needs an automotive platform commitment."],
      ["10x from here", false, 3.6 * B, 0.24, 10, 0.211, "Requires volume manufacturing at target cost, which has never been demonstrated for this chemistry."],
      ["50x from here", false, 12 * B, 0.66, 50, 0.376, "Only under the extreme branch. Marked unreachable on current evidence."],
    ],
    reverse_valuation: {
      required_revenue: 3.6 * B,
      required_market_share: 0.24,
      verdict:
        "A 10x from a $2.4B starting valuation requires roughly $3.6B of revenue and about a quarter of the modelled solid-state market in 2038. The share is not the obstacle; the starting price is. Most of the outcome this business is trying to achieve has already been paid for.",
      years: 12,
    },
    score_history: [59, 57, 56, 54, 52, 51, 48, 46, 44, 43],
  },
];
