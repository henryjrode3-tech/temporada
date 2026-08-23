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
| **Real company fundamentals (SEC XBRL)** | ✅ | `sources/edgar.py` - point-in-time on `filed`, not `end` |
| **Evidence grading** | ✅ | `core/evidence.py` - FACT / DERIVED / ESTIMATE / ASSUMPTION / AI |
| **`asymmetry research TICKER`** | ✅ | `research/company.py` - real ticker in, sourced report out |
| **Price provider interface** | ⚠️ | `sources/prices.py` - requires credentials; never invents a price |
| Synthetic corpus + mocks | ✅ | `sources/mock.py` |
| Discovery agent | ✅ | `agents/discovery.py` |
| Financial analysis | ✅ | `agents/analysis.py` |
| Scoring model with full decomposition | ✅ | `core/scoring.py` |
| FastAPI + rate limiting + API-key guard | ✅ | `api/app.py` |
| Next.js dashboard | ✅ | `frontend/` |
| CLI | ✅ | `cli.py` |
| Test suite (379 tests) | ✅ | `tests/` |

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
| Rank movement + explanation | ✅ | `core/movement.py` - attributes change to the dimensions that moved, using the weights in force at the time |
| Alerts (§35) | ✅ | `core/alerts.py` - fires on transitions, not states, so a standing condition never re-fires. Wired into the pipeline and CLI. Delivery (email/webhook) still out of scope. |
| Live source ingestion into signal series | 🟡 | GitHub commit/contributor history wired end to end (`sources/github_activity.py`, `asymmetry ingest-github`). USASpending and PatentsView still to do. |

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

**Half the blocker is now removed.** Point-in-time *fundamentals* are solved:
SEC XBRL stamps every datapoint with the date it was filed, so a query as of
2015 sees the figures as originally reported, not as later restated. That was
the harder half and it is free.

What remains is point-in-time **prices**. The SEC does not publish them, and
market capitalisation is the denominator of every multiple the platform
computes — a wrong price does not degrade the output, it inverts it. So the
price layer is an interface with no default implementation: without
credentials there is simply no valuation, and the report says so.

---

## Phase 5 — Learning 🟡 machinery built, awaiting data

| Item | Status | Notes |
| --- | --- | --- |
| `predictions` table | ✅ | |
| Prediction generation from thesis conditions | ✅ | `pipeline/predictions.py` |
| Resolution + Brier scoring | ✅ | Unmeasurable outcomes left unresolved, never guessed |
| **Skill score against the base rate** | ✅ | The number a self-flattering system would omit |
| Calibration buckets + overconfidence | ✅ | |
| Per-signal predictive lift | ✅ | `core/learning.py` |
| Weight recalibration from measured lift | ✅ | Proposed, never auto-applied |
| `asymmetry learning` + `/api/learning` | ✅ | |
| Ranking / anomaly ML | ⬜ | Premature until there is real outcome data |

Section 51 — the part that makes the system get *better* rather than merely
sound confident. The machinery is built and tested; what it lacks is elapsed
time. Predictions are generated from thesis conditions (already falsifiable by
construction), resolved when their horizon arrives, and graded.

**Three deliberate refusals**, because a learning layer that cannot report
failure is decoration:

1. Under 20 resolved predictions it reports figures but marks them *"not for
   use"*.
2. It computes **skill against the base rate**, so a model that looks accurate
   only because the event is rare is exposed as worthless.
3. Weight recalibration is **proposed, never applied automatically** —
   silently changing the scoring model would make historical scores
   incomparable without anyone noticing.

**What it has already found.** On the seeded data the loop reports the system
as *underconfident by 52%*: predictions are made at the candidate's confidence
score (~40%) while the generated thesis conditions hold ~92% of the time. That
is a genuine mismatch — confidence means "how much do we trust this analysis",
not "how likely is this condition to hold" — and the loop surfacing it on its
first run is the mechanism working. The fix should be driven by calibration
data rather than by another guess.

---

## Known limitations

0. **Market size is the weakest link in every real-company report.** With no
   independent market study, TAM is approximated as a multiple of current
   revenue — a crude sector heuristic. It is graded ASSUMPTION, and because a
   claim can never outrank its weakest input, every scenario built on it is
   graded ASSUMPTION too. Supply `--tam` with a real figure and the report
   improves accordingly.
1. **Scenario probabilities are guesses.** 40/35/20/5 is a reasonable prior for
   speculative small companies, not a measured distribution. Expected values
   inherit that uncertainty entirely.
2. **Signal series are mostly synthetic.** GitHub developer activity is wired
   to real data; hiring, patents and contracts are not yet. Note also that
   GitHub serves a rolling 52-week window rather than an archive, so it
   supports live detection but cannot support a historical backtest.
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

1. **Historical price data** — the last piece blocking real backtesting.
   Tiingo/Polygon free tiers include end-of-day history; the interface is
   written and the implementation is a single file.
2. **Alert delivery** — the rules exist and fire correctly; routing them to
   email or a webhook does not.
3. **Recursive query expansion** so discovery walks into domains nobody listed.
