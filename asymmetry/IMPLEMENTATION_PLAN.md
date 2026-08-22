# Implementation plan

Phases follow section 45 of the specification. Two deviations, both deliberate,
are noted below.

---

## Phase 1 — Foundation ✅ complete

| Item | Status | Where |
| --- | --- | --- |
| Database schema, 23 tables, fully timestamped | ✅ | `db/models.py` |
| Append-only score history | ✅ | `db/models.py::Score` |
| Point-in-time provenance + as-of filter | ✅ | `db/session.py` |
| Candidate model (section 17) | ✅ | `db/models.py::Candidate` |
| Source interface, tiers, rate limits | ✅ | `sources/base.py` |
| Live sources: SEC, arXiv, GitHub, HN | ✅ | `sources/public.py` |
| Synthetic corpus + mocks | ✅ | `sources/mock.py` |
| Discovery agent | ✅ | `agents/discovery.py` |
| Financial analysis | ✅ | `agents/analysis.py` |
| Scoring model with full decomposition | ✅ | `core/scoring.py` |
| FastAPI + rate limiting + API-key guard | ✅ | `api/app.py` |
| Next.js dashboard | ✅ | `frontend/` |
| CLI | ✅ | `cli.py` |
| Test suite (203 tests) | ✅ | `tests/` |

**Deviation 1 — the scenario engine was pulled forward from Phase 4.** It is
pure arithmetic with no dependencies, it is what makes every other number
meaningful, and building the scoring model without it would have meant scoring
candidates on dimensions with nothing behind them.

**Deviation 2 — temporal provenance was built in Phase 1 rather than with
backtesting in Phase 4.** `published_at` on every fact cannot be retrofitted:
adding it later means every row already collected is invisible to historical
mode, so the backtest would silently run on a fraction of the data.

---

## Phase 2 — The analyst bench 🟡 mostly complete

| Item | Status | Notes |
| --- | --- | --- |
| Technology agent | ✅ | Real-vs-marketing, moat taxonomy |
| Market agent | ✅ | Independent bottom-up TAM |
| Competition agent | ✅ | Actively tries to destroy the moat |
| Contrarian agent | ✅ | Output **rejected** if it fails to produce falsifiable failure modes |
| Fact checker | ✅ | Source / date / claim / confidence |
| Debate + judge | ✅ | Saved verbatim |
| Hype detection | ✅ | `core/hype.py` |
| Red-flag engine | ✅ | `core/redflags.py` |
| **Remaining** | | |
| Recursive query expansion into new domains | ⬜ | Generator exists; the recursion loop does not |
| Weekly "unknown unknown" sweep (§39) | ⬜ | Needs a scheduler |
| Second-order chain traversal (§38) | ✅ | `core/techgraph.py` - real graph traversal, depth ranking, query generation |
| Technology graph (§37) | ✅ | 19 nodes, 8 bottlenecks, `asymmetry second-order` + two API endpoints |

---

## Phase 3 — Signals and tracking 🟡 partly complete

| Item | Status | Notes |
| --- | --- | --- |
| Acceleration detection, magnitude + significance | ✅ | `core/signals.py` |
| Historical score tracking | ✅ | Append-only |
| Thesis tracker with monitored conditions | ✅ | Conditions individually falsifiable |
| Rank movement + explanation | 🟡 | Movement recorded; the *narrative* explanation is not generated |
| Alerts (§35) | ⬜ | Thresholds defined; no delivery mechanism |
| Live source ingestion into signal series | ⬜ | Series are synthetic; wiring GitHub/USASpending/PatentsView is the next real task |

---

## Phase 4 — Scenarios, backtesting, portfolio 🟡

| Item | Status | Notes |
| --- | --- | --- |
| Scenario engine | ✅ | Pulled forward |
| CAGR / expected value / milestone ladder | ✅ | Verified against the spec's worked examples |
| Reverse valuation | ✅ | |
| Paper portfolio | ✅ | Simulated only, enforced in the schema |
| As-of infrastructure | ✅ | |
| **Historical snapshot harness** | ⬜ | Needs point-in-time *market* data, which is the hard part |
| Hindsight benchmark (§31) | ⬜ | Depends on the above |

**The honest blocker.** Running "what would this have found in 2012" requires
point-in-time fundamentals and prices — what was *known* in 2012, not what has
since been restated. Free sources do not provide this; it needs a paid
point-in-time dataset. The plumbing is ready, the data is not, and pretending
otherwise would produce a backtest that flatters itself. Until then the
harness would only demonstrate that the code runs, not that the method works.

---

## Phase 5 — Learning ⬜ not started

| Item | Status |
| --- | --- |
| `predictions` table | ✅ schema exists |
| Resolution + Brier scoring | ⬜ |
| Per-signal predictive accuracy | ⬜ |
| Replace hand-tuned weights with measured ones | ⬜ |
| Ranking / anomaly ML | ⬜ |

This is section 51 — the part that makes the system get *better* rather than
merely sound confident — and it is the one phase that cannot be rushed. It needs
resolved predictions, which need elapsed time. The schema records every
prediction with a horizon and the signals that drove it, so the data will exist
when the time does.

Until then, the weights in `core/scoring.py` and the probabilities in
`core/scenarios.py` are explicitly **priors chosen by hand**, not measurements,
and are labelled as such in the code.

---

## Known limitations

1. **Scenario probabilities are guesses.** 40/35/20/5 is a reasonable prior for
   speculative small companies, not a measured distribution. Expected values
   inherit that uncertainty entirely.
2. **Signal series are synthetic.** Detection is tested and correct; it is not
   yet fed by live data.
3. **No point-in-time market data**, so backtesting is not yet meaningful.
4. **Heuristic fallbacks are shallow by design.** Without an API key the
   qualitative dimensions fall back to proxies (gross margin for technology
   quality, for instance). They are labelled `heuristic` and carry low
   confidence, but they are proxies, not analysis.
5. **The rate limiter is in-process.** Behind a load balancer it belongs in the
   proxy.
6. **No authentication beyond an optional API key** on mutating endpoints. This
   is a single-user research tool as built.

---

## Next three tasks, in order

1. **Wire one live signal source end to end** — GitHub repository activity into
   the signal series — so acceleration detection runs on real data.
2. **Rank-movement explanations**: diff consecutive score snapshots and state
   which dimension moved and why.
3. **Alert delivery** on the thresholds already defined in section 35.
