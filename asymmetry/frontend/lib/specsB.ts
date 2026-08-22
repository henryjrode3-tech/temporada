import type { CandidateSpec } from "./mockSpecs";

const M = 1e6;
const B = 1e9;

export const SPECS_B: CandidateSpec[] = [
  // -------------------------------------------------------------------------
  // 3. Photonics
  // -------------------------------------------------------------------------
  {
    id: "lumenar-photonics",
    name: "Lumenar Photonics",
    ticker: "LMNR",
    asset_type: "public_equity",
    sector: "Photonics",
    industry: "Co-packaged optical interconnect",
    description:
      "Makes the laser sources and fibre-attach tooling for co-packaged optics. Does not build the switch; builds the part of it that everyone else finds hard to yield. Revenue is currently tooling and NRE, which is exactly what a supplier looks like two product generations before volume.",
    current_market_cap: 1.4 * B,
    revenue: 94 * M,
    revenue_growth: 0.91,
    cash: 210 * M,
    debt: 0,
    verdict: "INVESTIGATE",
    verdict_reason:
      "Credible position in a transition that is widely agreed to be coming and repeatedly late. Revenue quality is poor — NRE and tooling, not volume — so the thesis rests on a timing assumption we cannot yet verify.",
    discovery_date: "2026-01-22",
    last_updated: "2026-08-19",
    rank: 3,
    rank_change: 4,
    risk_score: 56,
    years: 10,
    scenarios: [
      {
        name: "bear",
        probability: 0.34,
        revenue: 120 * M,
        margin: 0.02,
        multiple: 0.3,
        dilution: 1.45,
        valuation_path: "revenue",
        narrative:
          "Pluggable optics keep improving just fast enough. Co-packaging slips another two generations, the NRE pipeline dries up when customers pause programmes, and Lumenar raises equity twice into a falling price.",
        drivers: [
          "Linear pluggable optics extend the incumbent roadmap",
          "Two customer programmes paused or cancelled",
          "Cash runway forces dilutive raises in 2028 and 2030",
        ],
        assumptions: { terminal_ps_multiple: 3.5, net_margin: 0.02, share_dilution: 1.45 },
      },
      {
        name: "base",
        probability: 0.38,
        revenue: 720 * M,
        margin: 0.14,
        multiple: 2.9,
        dilution: 1.3,
        valuation_path: "earnings",
        narrative:
          "Co-packaged optics ships in volume around 2030 for the top of the switch line only. Lumenar supplies two of the four platform vendors and earns good but not extraordinary component margins.",
        drivers: [
          "Volume co-packaging at 200T+ switch capacity",
          "Two design wins convert from NRE to production",
          "Laser attach yield reaches 96%",
        ],
        assumptions: { terminal_pe: 40.3, net_margin: 0.14, share_dilution: 1.3, market_share: 0.21 },
      },
      {
        name: "bull",
        probability: 0.22,
        revenue: 2.4 * B,
        margin: 0.21,
        multiple: 12.5,
        dilution: 1.25,
        valuation_path: "earnings",
        narrative:
          "Optical interconnect moves from the switch face to the package across the whole line, and the laser source becomes the scarce input. Lumenar's fibre-attach tooling gets designed into the assembly flow itself, so it earns on every unit whether or not it supplies the laser.",
        drivers: [
          "Attach tooling adopted as the industry assembly standard",
          "Optical I/O extends from switches into accelerator packages",
          "Laser supply consolidates to three credible vendors",
        ],
        assumptions: { terminal_pe: 34.7, net_margin: 0.21, share_dilution: 1.25, market_share: 0.36 },
      },
      {
        name: "extreme_bull",
        probability: 0.06,
        revenue: 4.1 * B,
        margin: 0.24,
        multiple: 34,
        dilution: 1.22,
        valuation_path: "earnings",
        narrative:
          "Copper reaches its practical limit inside the package and optical I/O becomes mandatory rather than premium. Lumenar sits on the critical path of every high-end accelerator assembly line built after 2031.",
        drivers: [
          "In-package copper limit reached at the 2031 node",
          "Optical I/O becomes a requirement, not an option",
          "Tooling installed base creates switching costs at the fab-assembly level",
        ],
        clamp:
          "Unclamped output implied $11.2B terminal revenue (a 61% 10-year CAGR) and a 96x market-cap multiple. Both exceeded the ceilings for pre-volume component suppliers; revenue was reduced to $4.1B (46% CAGR) and the multiple to 34x.",
        assumptions: { terminal_pe: 48.5, net_margin: 0.24, share_dilution: 1.22, market_share: 0.48 },
      },
    ],
    dimensions: [
      ["future_market", 86, "Interconnect energy per bit is a widely agreed constraint with no competing solution at the far end.", 0.79],
      ["technology", 81, "Laser attach yield is the recognised hard problem, and Lumenar's published yield leads the disclosed field.", 0.68],
      ["competitive_advantage", 64, "Tooling installed base is sticky, but three well-funded competitors are pursuing the same attach step.", 0.6],
      ["early_signals", 77, "NRE contracts from two platform vendors and a 3x increase in optical-packaging job postings.", 0.71],
      ["valuation", 48, "14.9x sales on revenue that is mostly non-recurring engineering. The multiple assumes the transition arrives.", 0.83],
      ["growth", 79, "91% growth, but from a small base and of low-quality revenue.", 0.74],
      ["financial_health", 72, "$210M cash, no debt, roughly 11 quarters of runway at the current burn.", 0.89],
      ["management", 58, "Deep optical engineering bench; commercial leadership turned over twice in three years.", 0.52],
    ],
    flags: [
      ["REV_QUALITY", "high", "Revenue is largely non-recurring", "Roughly 68% of trailing revenue is NRE and tooling rather than repeat production, so growth does not compound the way the headline rate implies.", 11],
      ["TIMING_RISK", "medium", "Thesis depends on an adoption date", "Co-packaged optics has slipped in three consecutive industry roadmaps. The thesis is a timing bet dressed as a technology bet.", 8],
      ["MGMT_TURNOVER", "low", "Commercial leadership churn", "Two CROs in three years, both departing within a quarter of a guidance reset.", 3],
    ],
    signals: [
      ["job_postings", "strong", 88, 29, "trailing 90d vs 2-year baseline", "2026-08-11T10:15:00Z", "Optical packaging and test engineering postings tripled, with six roles specifying volume-production process ownership rather than development."],
      ["conference_papers", "moderate", 14, 6, "trailing 12m vs 3-year baseline", "2026-07-08T13:00:00Z", "Fourteen accepted papers on laser attach yield, including two co-authored with a platform vendor's packaging team."],
      ["customer_nre", "moderate", 4, 2, "active programmes", "2026-05-30T16:20:00Z", "Four disclosed NRE programmes against two a year ago, though none has yet converted to a production purchase order."],
    ],
    claims: [
      ["Four active customer-funded development programmes disclosed at the last quarterly call.", "Earnings call transcript", 2, null, "2026-07-24", 0.84],
      ["Laser attach yield of 94.1% reported at a packaging conference, versus a 2024 figure of 71%.", "ECTC conference paper", 2, null, "2026-06-03", 0.76],
      ["No production purchase orders received to date; all revenue is development or tooling.", "SEC 10-K risk factors", 1, "https://www.sec.gov/", "2026-02-18", 0.96],
      ["Industry roadmap moved volume co-packaged optics from 2028 to 2030.", "OIF roadmap update", 2, null, "2026-04-30", 0.87],
    ],
    thesis: {
      statement:
        "Moving bits across copper inside a package is running out of headroom, and the step that everyone finds hard is not the waveguide but attaching a laser to it at yield. Whoever owns that step owns the transition, whenever it finally happens.",
      status: "holding",
      created_at: "2026-02-04",
    },
    conditions: [
      ["At least one NRE programme converts to a production order by end 2027", "unknown", "Company guides to 'first production revenue in 2027'. No order disclosed yet."],
      ["Laser attach yield stays ahead of published competitor figures", "holding", "94.1% versus the best disclosed competitor figure of 88%."],
      ["Industry roadmap does not slip past 2031", "at_risk", "One slip already absorbed, from 2028 to 2030."],
      ["Cash runway stays above 8 quarters without a raise", "holding", "About 11 quarters at the current burn rate."],
    ],
    debate: [
      ["technology_agent", "bull", "Attach yield is the whole game and it is improving faster than the roadmap requires. 71% to 94% in two years is a learning curve, not a fluke."],
      ["contrarian_agent", "bear", "Co-packaged optics has been two generations away for eight years. Each slip is survivable for a company with a real business and fatal for one funded on NRE."],
      ["financial_agent", "bear", "Two thirds of revenue is non-recurring. Applying a growth multiple to NRE is a category error, and the market is currently making it."],
      ["future_agent", "bull", "The tooling angle is underrated. If the attach machine becomes the standard, Lumenar earns on units it does not supply lasers for, which turns a component bet into a toll."],
      ["signal_agent", "neutral", "The hiring shift from development to production process ownership is the single most informative signal here, and it is one quarter old. Not yet enough to move the timing prior."],
    ],
    milestones: [
      ["2x from here", true, 380 * M, 0.11, 2, 0.072, "Requires two NRE programmes converting to modest production volume."],
      ["5x from here", true, 1.1 * B, 0.19, 5, 0.175, "Needs volume co-packaging to arrive by roughly 2030."],
      ["10x from here", true, 2.1 * B, 0.32, 10, 0.259, "Requires the transition plus holding roughly a third of laser supply."],
      ["50x from here", false, 6.8 * B, 0.79, 50, 0.478, "Implies near-monopoly of a market that does not yet exist. Rejected."],
    ],
    reverse_valuation: {
      required_revenue: 2.1 * B,
      required_market_share: 0.32,
      verdict:
        "A 10x needs about $2.1B of 2036 revenue, roughly 32% of the modelled co-packaged laser and attach market. The share is plausible; the date is the fragile assumption. Every year of roadmap slip costs roughly a fifth of the present value.",
      years: 10,
    },
    score_history: [51, 55, 59, 62, 60, 64, 66, 68, 69, 70],
  },

  // -------------------------------------------------------------------------
  // 4. Rare-earth processing
  // -------------------------------------------------------------------------
  {
    id: "terrafirma-separation",
    name: "Terrafirma Separation",
    ticker: "TFSP",
    asset_type: "public_equity",
    sector: "Critical Materials",
    industry: "Rare-earth separation and metallisation",
    description:
      "Runs a small solvent-extraction and metallisation plant for heavy rare earths outside the dominant supply chain. Not a miner. The scarce asset is a permitted separation facility with a qualified metallisation line, which takes about seven years and a hostile permitting process to replicate.",
    current_market_cap: 310 * M,
    revenue: 22 * M,
    revenue_growth: 1.34,
    cash: 58 * M,
    debt: 41 * M,
    verdict: "HIGH_RISK",
    verdict_reason:
      "The strategic case is strong and the operating case is not. Sub-scale, cash-consuming, and exposed to a competitor that has repeatedly used price to eliminate exactly this kind of entrant.",
    discovery_date: "2025-08-30",
    last_updated: "2026-08-17",
    rank: 9,
    rank_change: -3,
    risk_score: 78,
    years: 12,
    scenarios: [
      {
        name: "bear",
        probability: 0.42,
        revenue: 30 * M,
        margin: -0.15,
        multiple: 0.18,
        dilution: 1.9,
        valuation_path: "revenue",
        narrative:
          "The dominant supplier cuts prices for three years, which it can afford and Terrafirma cannot. Offtake customers renegotiate, the metallisation line runs below breakeven, and the equity is recapitalised at a fraction of today's price.",
        drivers: [
          "Sustained price war on dysprosium and terbium oxide",
          "Offtake floors renegotiated downward",
          "Two dilutive rescue financings",
        ],
        assumptions: { terminal_ps_multiple: 1.9, net_margin: -0.15, share_dilution: 1.9 },
      },
      {
        name: "base",
        probability: 0.34,
        revenue: 210 * M,
        margin: 0.12,
        multiple: 2.6,
        dilution: 1.55,
        valuation_path: "earnings",
        narrative:
          "Defence and motor customers pay a documented premium for non-dominant-source material. Terrafirma stays small, profitable, and structurally protected by procurement rules rather than by cost.",
        drivers: [
          "Content rules on defence magnet supply chains hold",
          "Price floors written into two offtake agreements",
          "Metallisation line reaches nameplate throughput",
        ],
        assumptions: { terminal_pe: 32, net_margin: 0.12, share_dilution: 1.55, price_premium: 0.35 },
      },
      {
        name: "bull",
        probability: 0.18,
        revenue: 780 * M,
        margin: 0.19,
        multiple: 14,
        dilution: 1.45,
        valuation_path: "earnings",
        narrative:
          "An export restriction event makes non-dominant heavy rare-earth separation a strategic necessity rather than a preference. Terrafirma is one of two Western plants that can actually run, and it is expanded with public money.",
        drivers: [
          "Export restriction on separated heavy rare earths",
          "Public co-financing of a second separation train",
          "Long-term contracts at administered prices",
        ],
        assumptions: { terminal_pe: 29.3, net_margin: 0.19, share_dilution: 1.45 },
      },
      {
        name: "extreme_bull",
        probability: 0.06,
        revenue: 1.6 * B,
        margin: 0.22,
        multiple: 46,
        dilution: 1.4,
        valuation_path: "earnings",
        narrative:
          "Heavy rare-earth separation outside the dominant supply chain is treated as national infrastructure. Terrafirma's permitted site becomes the anchor of a Western processing cluster with guaranteed volumes at guaranteed prices.",
        drivers: [
          "Strategic reserve purchases at administered prices",
          "Site designated as national critical infrastructure",
          "Downstream magnet plants co-locate to secure feed",
        ],
        clamp:
          "Unclamped output implied a 74x market-cap multiple against a modelled market that would give Terrafirma 84% of Western separated heavy rare-earth supply. Terminal share was capped at 40%, reducing revenue to $1.6B and the multiple to 46x.",
        assumptions: { terminal_pe: 40.5, net_margin: 0.22, share_dilution: 1.4 },
      },
    ],
    dimensions: [
      ["future_market", 79, "Magnet demand from motors and generators is structural; the separation step is the genuine chokepoint.", 0.8],
      ["technology", 52, "Solvent extraction is century-old chemistry. The asset is a permit and a qualified line, not an invention.", 0.84],
      ["competitive_advantage", 61, "Permitting moat is real but the cost position is not defensible against the dominant producer.", 0.7],
      ["early_signals", 58, "Two offtake agreements signed with price floors; defence qualification progressing slowly.", 0.63],
      ["valuation", 55, "14x sales for a sub-scale processor is a strategic-option price, not an earnings price.", 0.77],
      ["growth", 62, "134% growth from a very small base as the metallisation line ramps.", 0.66],
      ["financial_health", 31, "Cash-consuming with $41M of debt and no path to self-funding a second train.", 0.92],
      ["management", 49, "Technically credible, commercially inexperienced; the last two guidance updates were missed.", 0.58],
    ],
    flags: [
      ["GOING_CONCERN", "high", "Structural cash consumption", "Operating cash flow has been negative for eleven consecutive quarters. Cash covers roughly seven quarters at the current burn.", 12],
      ["PRICE_WAR", "critical", "Exposed to a supplier that can set the price", "The dominant producer controls enough capacity to hold prices below Terrafirma's cash cost for years. This has happened twice before to comparable entrants.", 16],
      ["DILUTION", "high", "Repeated dilution", "Share count has increased 68% in three years across three financings, and a second separation train is not fundable from cash flow.", 9],
      ["GUIDANCE_MISS", "medium", "Repeated guidance misses", "Throughput guidance missed in each of the last two years, both times attributed to commissioning issues.", 5],
    ],
    signals: [
      ["policy_mentions", "extreme", 63, 9, "regulatory filings, trailing 180d", "2026-08-05T07:45:00Z", "References to heavy rare-earth separation capacity in Western regulatory and procurement documents rose from 9 to 63, an unusually sharp policy-attention shift."],
      ["offtake_signings", "moderate", 2, 0, "trailing 12m", "2026-04-16T12:00:00Z", "Two offtake agreements signed with stated price floors, the first such terms the company has obtained."],
      ["spot_price", "weak", 214, 246, "USD/kg Dy oxide, current vs 12m average", "2026-08-20T06:00:00Z", "Dysprosium oxide spot drifted 13% below its trailing average, which pressures the unhedged portion of output."],
    ],
    claims: [
      ["Operating cash flow negative in each of the last eleven quarters.", "SEC 10-K", 1, "https://www.sec.gov/", "2026-03-05", 0.97],
      ["Two offtake agreements executed containing price floors and minimum volumes.", "SEC 8-K", 1, "https://www.sec.gov/", "2026-04-15", 0.94],
      ["Metallisation line operating at approximately 54% of nameplate throughput.", "Earnings call transcript", 2, null, "2026-05-21", 0.79],
      ["Site holds the only current Western permit for heavy rare-earth solvent extraction at this scale.", "Industry consultancy note", 3, null, "2026-01-28", 0.55],
    ],
    thesis: {
      statement:
        "Separation, not mining, is the chokepoint in rare earths, and permits for it take the better part of a decade. A permitted, operating Western separation site is an option on a policy shift that keeps looking more likely, held by a company that may not survive to exercise it.",
      status: "at_risk",
      created_at: "2025-09-15",
    },
    conditions: [
      ["Cash runway stays above 6 quarters", "at_risk", "About 7 quarters and shortening; the next raise is likely inside 12 months."],
      ["Offtake price floors hold", "holding", "Both floors intact; neither has been tested by spot yet."],
      ["Metallisation line reaches 80% of nameplate by end 2026", "at_risk", "54% at the last disclosure, against a 2026 target of 80%."],
      ["No sustained spot price below cash cost", "at_risk", "Spot is 13% below the trailing average and within 8% of the disclosed cash cost."],
      ["Western content procurement rules remain in force", "holding", "Strengthened in two jurisdictions this year."],
    ],
    debate: [
      ["contrarian_agent", "bear", "The dominant producer has eliminated two comparable entrants with price alone. Nothing in this file explains why the third attempt survives what the first two did not."],
      ["market_agent", "bull", "What is different is the buyer. Defence procurement does not optimise for price, and the content rules are now written rather than implied. That is a floor the previous entrants never had."],
      ["financial_agent", "bear", "Eleven quarters of negative operating cash flow and a second train that cannot be self-funded. The bull case requires public money, which means the thesis is a political forecast."],
      ["technology_agent", "neutral", "There is no technical edge here and the file should stop implying one. Solvent extraction is well understood. The asset is the permit."],
      ["valuation_agent", "neutral", "At $310M this is priced as an option, and options can expire worthless. The position size implied by a 42% loss branch is small, not zero."],
    ],
    milestones: [
      ["2x from here", true, 95 * M, 0.06, 2, 0.059, "Requires the metallisation line reaching nameplate and holding current pricing."],
      ["5x from here", true, 260 * M, 0.14, 5, 0.14, "Needs a second train, which needs external capital."],
      ["10x from here", true, 540 * M, 0.26, 10, 0.211, "Only reachable under a policy branch with administered prices."],
      ["50x from here", false, 2.4 * B, 0.71, 50, 0.376, "Implies most of Western supply. Rejected as politically and physically implausible."],
    ],
    reverse_valuation: {
      required_revenue: 540 * M,
      required_market_share: 0.26,
      verdict:
        "A 10x requires about $540M of revenue in 2038 and roughly a quarter of Western separated heavy rare-earth supply, at margins the company has never earned. The path exists but every step of it runs through a government decision rather than a commercial one.",
      years: 12,
    },
    score_history: [57, 59, 58, 56, 54, 52, 49, 47, 46, 44],
  },

  // -------------------------------------------------------------------------
  // 5. Nuclear / SMR
  // -------------------------------------------------------------------------
  {
    id: "anvil-nuclear",
    name: "Anvil Nuclear Components",
    ticker: "ANVL",
    asset_type: "public_equity",
    sector: "Nuclear",
    industry: "Heavy forgings and pressure boundary components",
    description:
      "Forges reactor pressure vessels and primary-loop components under nuclear quality assurance. Supplies the existing fleet's life-extension programmes today and holds N-stamp certification plus a large forging press that new SMR developers cannot build around. Sells picks and shovels to an industry with many competing designs and one shared bottleneck.",
    current_market_cap: 560 * M,
    revenue: 141 * M,
    revenue_growth: 0.34,
    cash: 62 * M,
    debt: 88 * M,
    verdict: "TOP_OPPORTUNITY",
    verdict_reason:
      "Design-agnostic exposure to reactor construction with a certification moat and an existing profitable maintenance business underneath. The downside branch is a boring forging company rather than a zero.",
    discovery_date: "2025-06-18",
    last_updated: "2026-08-21",
    rank: 4,
    rank_change: 1,
    risk_score: 44,
    years: 15,
    scenarios: [
      {
        name: "bear",
        probability: 0.3,
        revenue: 190 * M,
        margin: 0.07,
        multiple: 0.55,
        dilution: 1.15,
        valuation_path: "earnings",
        narrative:
          "SMRs stay demonstrations. Anvil keeps the fleet life-extension work, which is stable and unexciting, and the option value on new build quietly deflates without ever being disproved.",
        drivers: [
          "No SMR reaches commercial operation before 2035",
          "Life-extension work continues at current levels",
          "Press utilisation stays near 60%",
        ],
        assumptions: { terminal_pe: 31.6, net_margin: 0.07, share_dilution: 1.15 },
      },
      {
        name: "base",
        probability: 0.4,
        revenue: 620 * M,
        margin: 0.13,
        multiple: 3.6,
        dilution: 1.12,
        valuation_path: "earnings",
        narrative:
          "A handful of SMR designs reach repeat build, and Anvil supplies pressure boundary components to most of them because there is nowhere else to go. Life extension continues underneath as a stable base.",
        drivers: [
          "Three to five designs reach repeat order",
          "Anvil supplies components across multiple designs",
          "Second press line commissioned around 2031",
        ],
        assumptions: { terminal_pe: 25, net_margin: 0.13, share_dilution: 1.12 },
      },
      {
        name: "bull",
        probability: 0.24,
        revenue: 2.1 * B,
        margin: 0.16,
        multiple: 14,
        dilution: 1.1,
        valuation_path: "earnings",
        narrative:
          "Datacenter power procurement pulls nuclear build forward by a decade. Forging capacity under nuclear QA becomes the binding constraint on how fast reactors can be built, and Anvil is the constraint.",
        drivers: [
          "Corporate power agreements underwrite reactor construction",
          "Forging capacity, not licensing, becomes the schedule constraint",
          "Anvil holds capacity reservation fees from three developers",
        ],
        assumptions: { terminal_pe: 23.3, net_margin: 0.16, share_dilution: 1.1 },
      },
      {
        name: "extreme_bull",
        probability: 0.06,
        revenue: 4.4 * B,
        margin: 0.18,
        multiple: 33,
        dilution: 1.08,
        valuation_path: "earnings",
        narrative:
          "Serial reactor construction genuinely arrives and the industry rebuilds around a small number of qualified heavy-forging works. Anvil expands three times over the horizon and still cannot clear its queue.",
        drivers: [
          "More than 40 units per year under construction globally",
          "Nuclear QA forging remains the schedule-critical path",
          "Capacity reservation becomes the standard commercial model",
        ],
        clamp:
          "Unclamped output implied $9.6B terminal revenue, which exceeded the entire modelled Western nuclear heavy-forging market in 2041. Terminal revenue was capped at $4.4B (24.8% CAGR, 46% modelled share) and the multiple reduced from 61x to 33x.",
        assumptions: { terminal_pe: 23.3, net_margin: 0.18, share_dilution: 1.08 },
      },
    ],
    dimensions: [
      ["future_market", 81, "Firm low-carbon power demand is structural, though the delivery mechanism remains contested.", 0.73],
      ["technology", 70, "Forging metallurgy under nuclear QA is hard-won process knowledge rather than novel technology.", 0.8],
      ["competitive_advantage", 87, "N-stamp certification plus press capacity; requalifying a new works runs five to seven years.", 0.85],
      ["early_signals", 72, "Three capacity reservation agreements signed in twelve months, a commercial form that did not previously exist here.", 0.76],
      ["valuation", 82, "4x sales for a certified sole-source position with an existing profitable base.", 0.81],
      ["growth", 69, "34% growth driven by life-extension volume, not yet by new build.", 0.83],
      ["financial_health", 66, "Net debt $26M; the press expansion is partly customer-funded through reservation fees.", 0.88],
      ["management", 74, "Long-tenured, refused two low-margin fixed-price contracts that competitors took and lost money on.", 0.69],
    ],
    flags: [
      ["SCHEDULE_RISK", "medium", "Customer schedules slip constantly", "Nuclear construction schedules have slipped in nearly every recent Western project. Anvil's revenue recognition follows those schedules.", 7],
      ["FIXED_PRICE", "low", "Legacy fixed-price contract", "One life-extension contract signed in 2023 on fixed price is running below target margin through 2027.", 3],
    ],
    signals: [
      ["capacity_reservations", "strong", 3, 0, "agreements, trailing 12m", "2026-08-09T15:30:00Z", "Three developers paid capacity reservation fees to secure forging slots, a commercial structure that did not exist in this market two years ago."],
      ["regulatory_filings", "moderate", 19, 7, "design applications, trailing 12m", "2026-07-15T09:00:00Z", "Nineteen reactor design or site applications filed across Western regulators, up from seven, which raises the number of potential customers regardless of which designs prevail."],
      ["press_utilisation", "moderate", 0.84, 0.61, "quarterly average", "2026-08-01T00:00:00Z", "Press utilisation rose from 61% to 84%, the level at which the company has previously said expansion becomes necessary."],
    ],
    claims: [
      ["Three capacity reservation agreements executed with SMR developers, with non-refundable fees.", "SEC 8-K", 1, "https://www.sec.gov/", "2026-06-30", 0.93],
      ["Holds ASME N-stamp certification for pressure boundary components at the relevant class.", "ASME certificate register", 1, null, "2025-11-02", 0.98],
      ["Press utilisation of 84% in the most recent quarter versus 61% a year earlier.", "Quarterly report", 1, null, "2026-07-31", 0.94],
      ["Second press investment estimated at $180M, roughly 40% customer-funded.", "Earnings call transcript", 2, null, "2026-07-31", 0.72],
      ["Requalification of a new nuclear forging works estimated at five to seven years by a regulator official.", "Regulatory workshop transcript", 2, null, "2026-02-20", 0.66],
    ],
    thesis: {
      statement:
        "The bottleneck on nuclear construction is not designs or licences, it is the small number of works that can forge a pressure boundary under nuclear quality assurance. Whichever reactor design wins, the forging happens in the same few buildings.",
      status: "holding",
      created_at: "2025-07-02",
    },
    conditions: [
      ["Anvil remains design-agnostic across at least three developers", "holding", "Three reservation agreements across three distinct designs."],
      ["Press utilisation stays above 70%", "holding", "84% in the most recent quarter."],
      ["Life-extension base revenue does not decline", "holding", "Up 11% year over year; contracted through 2029."],
      ["No new Western works achieves N-stamp certification before 2030", "holding", "No certification applications currently in progress that we can find."],
      ["Second press decision taken by mid-2027", "unknown", "Company says 'when reservations cover 50% of the cost'; currently around 40%."],
    ],
    debate: [
      ["market_agent", "bull", "The design-agnostic framing is what makes this work. You do not have to pick the winning reactor, which is the part nobody can do, and you still get the exposure."],
      ["contrarian_agent", "bear", "Nuclear has produced a decade of announcements and almost no concrete. Reservation fees are cheap options for developers who may never build, and Anvil is booking them as validation."],
      ["financial_agent", "neutral", "The reservation fees are non-refundable, which makes them better evidence than an announcement, but they are still only 40% of a press that costs $180M."],
      ["technology_agent", "bull", "Forging large sections without unacceptable segregation is genuinely hard and the failure modes are found years later in service. That is exactly the kind of process knowledge that does not transfer."],
      ["future_agent", "bull", "The demand driver changed. Utility procurement is slow and political; corporate power procurement is fast and indifferent to politics. That is a different customer with a different clock."],
      ["fact_check_agent", "neutral", "The five-to-seven year requalification figure comes from a workshop transcript, not a rule. Directionally supported, but it should not be quoted as a regulatory fact."],
    ],
    milestones: [
      ["2x from here", true, 280 * M, 0.08, 2, 0.047, "Reachable on life-extension growth alone if utilisation holds."],
      ["5x from here", true, 720 * M, 0.17, 5, 0.111, "Requires SMR components moving from reservation to production."],
      ["10x from here", true, 1.5 * B, 0.31, 10, 0.166, "Needs repeat build across several designs and a second press."],
      ["30x from here", true, 4.1 * B, 0.44, 30, 0.25, "Requires serial construction at a scale not seen in the West since the 1970s."],
      ["100x from here", false, 12 * B, 0.94, 100, 0.354, "Exceeds the entire modelled market. Rejected."],
    ],
    reverse_valuation: {
      required_revenue: 1.5 * B,
      required_market_share: 0.31,
      verdict:
        "A 10x over fifteen years requires about $1.5B of revenue, roughly 31% of the modelled Western nuclear forging market. That is a large but historically ordinary share for a certified sole-source supplier, and the horizon is long enough for the construction cycle to actually happen.",
      years: 15,
    },
    score_history: [60, 62, 66, 68, 67, 70, 73, 75, 77, 78],
  },

  // -------------------------------------------------------------------------
  // 6. Space ISR
  // -------------------------------------------------------------------------
  {
    id: "orbital-sentinel",
    name: "Orbital Sentinel",
    ticker: "ORBS",
    asset_type: "public_equity",
    sector: "Space",
    industry: "Synthetic aperture radar constellation",
    description:
      "Operates a small synthetic aperture radar constellation and sells tasking and analytics rather than pixels. Radar sees through cloud and darkness, which is the entire commercial argument against optical imaging, and the company's differentiator is a revisit rate over specific latitudes rather than a global average.",
    current_market_cap: 980 * M,
    revenue: 77 * M,
    revenue_growth: 0.58,
    cash: 165 * M,
    debt: 120 * M,
    verdict: "WATCH",
    verdict_reason:
      "Real capability and real contracts, but the customer base is concentrated in government budgets and the constellation needs continuous capital to stay in orbit. Attractive at a lower price or after a commercial-revenue inflection.",
    discovery_date: "2025-12-08",
    last_updated: "2026-08-16",
    rank: 7,
    rank_change: -1,
    risk_score: 61,
    years: 10,
    scenarios: [
      {
        name: "bear",
        probability: 0.32,
        revenue: 110 * M,
        margin: 0.0,
        multiple: 0.35,
        dilution: 1.5,
        valuation_path: "revenue",
        narrative:
          "Government budgets tighten, commercial demand stays a rounding error, and constellation replenishment consumes every dollar of gross profit. The company survives as a contractor with a satellite habit.",
        drivers: [
          "Defence ISR budgets flat or reduced",
          "Commercial analytics revenue stays below 15% of sales",
          "Replenishment capex equals gross profit",
        ],
        assumptions: { terminal_ps_multiple: 3.1, net_margin: 0.0, share_dilution: 1.5 },
      },
      {
        name: "base",
        probability: 0.4,
        revenue: 520 * M,
        margin: 0.11,
        multiple: 3.1,
        dilution: 1.35,
        valuation_path: "earnings",
        narrative:
          "Radar tasking becomes a standard input to defence and insurance workflows. Orbital Sentinel holds a strong second position, earns respectable margins on analytics, and funds replenishment from operations.",
        drivers: [
          "Analytics reaches 40% of revenue at software margins",
          "Two multi-year government programmes renewed",
          "Launch costs continue to fall, cutting replenishment capex",
        ],
        assumptions: { terminal_pe: 53.1, net_margin: 0.11, share_dilution: 1.35 },
      },
      {
        name: "bull",
        probability: 0.22,
        revenue: 1.7 * B,
        margin: 0.19,
        multiple: 11,
        dilution: 1.28,
        valuation_path: "earnings",
        narrative:
          "Persistent radar coverage becomes an assumed layer of infrastructure the way GPS did, and the analytics layer is where the margin sits. Insurance, shipping and commodity monitoring become larger customers than defence.",
        drivers: [
          "Commercial revenue exceeds government revenue",
          "Analytics gross margin above 80%",
          "Constellation revisit rate becomes contractually specified in customer workflows",
        ],
        assumptions: { terminal_pe: 33.4, net_margin: 0.19, share_dilution: 1.28 },
      },
      {
        name: "extreme_bull",
        probability: 0.06,
        revenue: 3.2 * B,
        margin: 0.23,
        multiple: 31,
        dilution: 1.25,
        valuation_path: "earnings",
        narrative:
          "Continuous all-weather monitoring of the Earth's surface turns out to be a foundational data layer, and the two or three operators with sufficient revisit rate own it. Pricing shifts from per-image to per-seat.",
        drivers: [
          "Consolidation to three credible radar operators",
          "Per-seat subscription pricing replaces per-image tasking",
          "Regulatory requirements create mandated monitoring demand",
        ],
        clamp:
          "Unclamped output implied a 44% 10-year revenue CAGR and an 88x multiple. Capital-intensive constellation operators in the reference set have not sustained above 35%; terminal revenue was cut to $3.2B (45% share of the modelled market) and the multiple to 31x.",
        assumptions: { terminal_pe: 41.4, net_margin: 0.23, share_dilution: 1.25 },
      },
    ],
    dimensions: [
      ["future_market", 74, "All-weather monitoring demand is growing, but commercial willingness to pay is still largely unproven.", 0.64],
      ["technology", 71, "Compact SAR payload with a genuine revisit advantage at mid latitudes; not a physics lead.", 0.72],
      ["competitive_advantage", 57, "Two well-funded competitors and no structural barrier beyond capital and time.", 0.68],
      ["early_signals", 69, "Commercial bookings up 2.4x, and two insurance customers moved from pilot to contract.", 0.7],
      ["valuation", 54, "12.7x sales for a capital-intensive operator with government-weighted revenue.", 0.8],
      ["growth", 73, "58% growth with improving revenue mix toward analytics.", 0.78],
      ["financial_health", 51, "Replenishment capex is structural; free cash flow remains negative through the base case until 2029.", 0.85],
      ["management", 61, "Strong technical execution on launch cadence; commercial go-to-market has been slow.", 0.6],
    ],
    flags: [
      ["CUST_CONC", "high", "Government revenue concentration", "71% of revenue comes from three government programmes, each subject to annual appropriation.", 10],
      ["CAPEX_TREADMILL", "high", "Constellation replenishment is permanent", "Satellites have a 5-7 year design life. Maintaining coverage requires continuous capital regardless of demand.", 9],
      ["COMPETITION", "medium", "Two funded competitors with similar capability", "Both competitors have announced constellations of comparable size with launch contracts already signed.", 6],
    ],
    signals: [
      ["commercial_bookings", "strong", 31, 13, "USD millions, trailing 12m", "2026-08-12T11:00:00Z", "Commercial bookings rose from $13M to $31M, with two insurance customers converting from pilot to multi-year contract."],
      ["launch_manifest", "moderate", 9, 4, "satellites manifested, next 24m", "2026-06-19T08:30:00Z", "Nine satellites manifested for the next two years against four previously, which improves revisit rate but raises near-term capex."],
    ],
    claims: [
      ["Government programmes represent 71% of trailing twelve-month revenue.", "SEC 10-K", 1, "https://www.sec.gov/", "2026-02-27", 0.95],
      ["Two insurance customers converted from evaluation to multi-year contracts in the first half.", "Earnings call transcript", 2, null, "2026-08-06", 0.8],
      ["Nine additional satellites contracted for launch through 2028.", "Press release", 2, null, "2026-06-18", 0.85],
      ["Satellite design life stated as six years.", "SEC 10-K", 1, "https://www.sec.gov/", "2026-02-27", 0.93],
    ],
    thesis: {
      statement:
        "Radar sees what optical cannot, and the value is not in the image but in guaranteed revisit. If enough commercial workflows come to assume that coverage exists, the operators with sufficient revisit rate become infrastructure rather than contractors.",
      status: "holding",
      created_at: "2025-12-20",
    },
    conditions: [
      ["Commercial revenue share rises above 30% by 2028", "holding", "Currently 29% and improving; the insurance conversions help."],
      ["Free cash flow turns positive before 2030", "unknown", "Base case models 2029. Nine manifested launches push it later."],
      ["No more than two competitors reach comparable revisit rate", "at_risk", "Both announced competitors now have launch contracts in place."],
      ["Government programmes renewed at or above current value", "holding", "Two of three renewed in the last twelve months."],
    ],
    debate: [
      ["technology_agent", "neutral", "The payload is good, not special. The revisit advantage is a consequence of orbital planes and launch cadence, which is a capital advantage, and capital advantages can be bought."],
      ["market_agent", "bull", "The insurance conversions matter more than their size. A pilot proves interest; a multi-year contract proves the data changed a decision that costs money."],
      ["contrarian_agent", "bear", "Every satellite operator has claimed the commercial inflection is one year away for a decade. Government revenue at 71% is not a mix, it is the business."],
      ["financial_agent", "bear", "The replenishment treadmill is the structural problem. Six-year design life means you rebuild the entire asset base twice over the horizon before earning anything."],
      ["valuation_agent", "neutral", "At 12.7x sales the base case is roughly priced in. This is a watch, not a position, until either the price falls or the commercial mix breaks 40%."],
    ],
    milestones: [
      ["2x from here", true, 290 * M, 0.09, 2, 0.072, "Achievable on government renewals plus modest commercial growth."],
      ["5x from here", true, 760 * M, 0.19, 5, 0.175, "Requires the commercial mix inflection and positive free cash flow."],
      ["10x from here", true, 1.5 * B, 0.34, 10, 0.259, "Needs commercial revenue to exceed government revenue."],
      ["40x from here", false, 5.2 * B, 0.81, 40, 0.445, "Implies dominance of a market with two funded competitors. Rejected."],
    ],
    reverse_valuation: {
      required_revenue: 1.5 * B,
      required_market_share: 0.34,
      verdict:
        "A 10x requires roughly $1.5B of 2036 revenue and about a third of the modelled commercial radar market, with free cash flow positive throughout. The share is attainable; funding the constellation to get there without further dilution is the harder half.",
      years: 10,
    },
    score_history: [66, 68, 67, 65, 66, 64, 63, 64, 62, 63],
  },

  // -------------------------------------------------------------------------
  // 7. Industrial robotics
  // -------------------------------------------------------------------------
  {
    id: "cortex-robotics",
    name: "Cortex Robotics Works",
    ticker: "CRWX",
    asset_type: "public_equity",
    sector: "Robotics",
    industry: "Force-controlled industrial manipulation",
    description:
      "Builds force-controlled manipulators and the servo stack behind them for assembly tasks that position-controlled arms cannot do: insertion, deburring, wire routing. Sells to tier-one automotive and electronics assemblers who have run out of people willing to do the work.",
    current_market_cap: 1.9 * B,
    revenue: 340 * M,
    revenue_growth: 0.31,
    cash: 220 * M,
    debt: 95 * M,
    verdict: "INTERESTING",
    verdict_reason:
      "Solid business in a real category with a demographic tailwind that does not reverse. The asymmetry is limited because the price already reflects competent execution and the moat is narrower than the technology suggests.",
    discovery_date: "2025-10-25",
    last_updated: "2026-08-15",
    rank: 8,
    rank_change: 2,
    risk_score: 39,
    years: 12,
    scenarios: [
      {
        name: "bear",
        probability: 0.3,
        revenue: 420 * M,
        margin: 0.08,
        multiple: 0.5,
        dilution: 1.12,
        valuation_path: "earnings",
        narrative:
          "General-purpose robot platforms with learned control absorb the force-control niche, and Cortex's servo advantage becomes a software feature bundled by larger integrators.",
        drivers: [
          "Learned control closes the force-control gap",
          "Integrators bundle competing arms",
          "Price competition from Asian manufacturers",
        ],
        assumptions: { terminal_pe: 31.1, net_margin: 0.08, share_dilution: 1.12 },
      },
      {
        name: "base",
        probability: 0.44,
        revenue: 1.4 * B,
        margin: 0.13,
        multiple: 2.7,
        dilution: 1.1,
        valuation_path: "earnings",
        narrative:
          "Force-controlled assembly grows steadily as labour supply tightens. Cortex holds its niche, expands into electronics assembly, and compounds at a respectable rather than remarkable rate.",
        drivers: [
          "Assembly labour costs continue rising faster than robot costs",
          "Electronics assembly becomes a second vertical",
          "Service and software attach reaches 25% of revenue",
        ],
        assumptions: { terminal_pe: 28.2, net_margin: 0.13, share_dilution: 1.1 },
      },
      {
        name: "bull",
        probability: 0.2,
        revenue: 2.6 * B,
        margin: 0.17,
        multiple: 5.4,
        dilution: 1.08,
        valuation_path: "earnings",
        narrative:
          "Cortex's control stack becomes the layer that general-purpose robot builders license rather than rebuild, turning a hardware company into a hardware company with a royalty attached.",
        drivers: [
          "Control stack licensed to two humanoid platform builders",
          "Installed base data improves insertion success rates measurably",
          "Software attach exceeds 35% of revenue",
        ],
        assumptions: { terminal_pe: 23.2, net_margin: 0.17, share_dilution: 1.08 },
      },
      {
        name: "extreme_bull",
        probability: 0.06,
        revenue: 5.4 * B,
        margin: 0.2,
        multiple: 12,
        dilution: 1.06,
        valuation_path: "earnings",
        narrative:
          "Physical manipulation becomes a general capability sold as a service, and the force-control stack is the part that took twenty years of failure data to get right. Cortex sits underneath a much larger category than industrial assembly.",
        drivers: [
          "Manipulation-as-a-service pricing model adopted",
          "Control stack becomes a de facto standard",
          "Installed base exceeds 400,000 units",
        ],
        clamp:
          "Unclamped output implied a 34% 12-year revenue CAGR sustained on a $340M base, giving $12.9B terminal revenue and more than the whole modelled segment. Terminal revenue was capped at $5.4B (24.4% CAGR) and the multiple cut from 32x to 12x.",
        assumptions: { terminal_pe: 21.1, net_margin: 0.2, share_dilution: 1.06 },
      },
    ],
    dimensions: [
      ["future_market", 76, "Assembly labour scarcity is demographic and does not reverse within the horizon.", 0.84],
      ["technology", 72, "Genuine force-control expertise, but learned control is closing the gap faster than expected.", 0.61],
      ["competitive_advantage", 58, "Twenty years of failure data in the servo stack, undermined by an open ecosystem forming around it.", 0.63],
      ["early_signals", 61, "Order intake steady; two licensing conversations disclosed but nothing signed.", 0.67],
      ["valuation", 57, "5.6x sales and 34x earnings for 31% growth is a fair price, not a cheap one.", 0.86],
      ["growth", 68, "31% growth, decelerating gently from 38% two years ago.", 0.87],
      ["financial_health", 82, "Net cash $125M, consistently free-cash-flow positive.", 0.93],
      ["management", 77, "Long-tenured engineering leadership, disciplined about not chasing the humanoid narrative.", 0.72],
    ],
    flags: [
      ["MOAT_EROSION", "medium", "Learned control narrowing the gap", "Published benchmarks show learned insertion policies within 12% of Cortex's success rate on standard tasks, versus 40% two years ago.", 8],
      ["CYCLICAL", "low", "Capital-goods cyclicality", "Order intake tracks automotive capex, which has historically fallen 30% or more in downturns.", 4],
    ],
    signals: [
      ["benchmark_gap", "moderate", 0.12, 0.4, "success-rate gap vs learned baselines", "2026-07-22T14:00:00Z", "The measured advantage of Cortex's control stack over published learned policies narrowed from 40% to 12% in two years. This is a signal against the thesis, and it is the most important one in the file."],
      ["order_intake", "weak", 118, 109, "USD millions, trailing quarter", "2026-08-14T09:00:00Z", "Order intake up 8% year over year, roughly in line with the trend and not informative on its own."],
    ],
    claims: [
      ["Installed base of approximately 41,000 manipulators.", "Annual report", 1, null, "2026-03-20", 0.91],
      ["Learned insertion policies reached within 12% of commercial force-control success rates on the standard benchmark set.", "Peer-reviewed paper", 1, null, "2026-06-14", 0.82],
      ["Two licensing discussions with humanoid platform developers disclosed, no agreement signed.", "Earnings call transcript", 2, null, "2026-08-07", 0.7],
      ["Free cash flow positive in each of the last fourteen quarters.", "SEC 10-K", 1, "https://www.sec.gov/", "2026-03-20", 0.96],
    ],
    thesis: {
      statement:
        "The tasks that resist automation are the ones needing force feedback rather than position accuracy, and the failure data required to do them reliably takes decades to accumulate. Cortex owns that data. The open question is whether learning shortcuts it.",
      status: "at_risk",
      created_at: "2025-11-08",
    },
    conditions: [
      ["Control-stack advantage over learned baselines stays above 20%", "broken", "Measured gap fell to 12% in the June benchmark. This condition has failed and is the reason the thesis is marked at risk."],
      ["Revenue growth stays above 25%", "holding", "31% trailing, decelerating slowly."],
      ["Free cash flow stays positive", "holding", "Fourteen consecutive quarters."],
      ["At least one licensing agreement signed by end 2027", "unknown", "Two discussions disclosed, nothing signed."],
    ],
    debate: [
      ["contrarian_agent", "bear", "The benchmark gap closing from 40% to 12% in two years is the whole story. Extrapolate one more year and the moat is inside the noise band."],
      ["technology_agent", "neutral", "Benchmarks are not factory floors. The published tasks are clean; the failure modes that matter are chatter, thermal drift and part variation, none of which the benchmark set captures."],
      ["market_agent", "bull", "Customers do not buy success rates, they buy uptime guarantees. Cortex underwrites its cycle times contractually and the learned systems cannot yet be underwritten."],
      ["future_agent", "bull", "If manipulation becomes a general capability, the control layer is the part nobody wants to rebuild. The licensing conversations are the tell, even unsigned."],
      ["financial_agent", "neutral", "Fourteen quarters of positive free cash flow means the bear case is a de-rating, not a failure. That bounds the loss but it also bounds the asymmetry."],
    ],
    milestones: [
      ["2x from here", true, 900 * M, 0.12, 2, 0.059, "Reachable on current growth without any mix change."],
      ["5x from here", true, 2.3 * B, 0.24, 5, 0.14, "Requires the electronics vertical and software attach above 30%."],
      ["10x from here", false, 4.6 * B, 0.41, 10, 0.211, "Needs licensing revenue that does not currently exist."],
      ["25x from here", false, 10 * B, 0.78, 25, 0.301, "Implies dominance of general manipulation. Rejected."],
    ],
    reverse_valuation: {
      required_revenue: 4.6 * B,
      required_market_share: 0.41,
      verdict:
        "A 10x requires about $4.6B of revenue in 2038 and roughly 41% of the modelled force-controlled manipulation market, which is more share than any industrial robotics vendor holds in any segment today. The base case is sound; the asymmetric case is not well supported.",
      years: 12,
    },
    score_history: [70, 71, 72, 71, 70, 69, 67, 66, 64, 63],
  },
];
