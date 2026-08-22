# Asymmetry Engine — Architecture

A research platform that hunts for **asymmetric opportunities**: things that are
obscure and reasonably priced today but could plausibly matter enormously in
5–15 years.

It is a **research tool, not a trading system**. It never emits "BUY". Its
verbs are `INVESTIGATE`, `WATCH`, `INTERESTING`, `HIGH_RISK`,
`THESIS_WEAKENING`, `THESIS_INVALIDATED`, `REJECTED`.

---

## 1. Design principles

| Principle | How it is enforced in code |
| --- | --- |
| **Never hide reasoning behind one number** | Every composite score stores its component sub-scores and the exact weights used (`scores.components`, `scores.weights`). |
| **Potential ≠ probability** | Upside magnitude (`asymmetry_score`) and likelihood (`confidence_score`) are computed by separate functions and are never blended into one figure. |
| **No hindsight leakage** | Every fact carries `published_at` / `as_of`. All reads go through an *as-of filter*, so historical mode physically cannot see the future. |
| **History is the product** | `scores`, `financial_metrics`, `market_estimates` are append-only snapshots. Nothing is updated in place, so "what did we believe 6 months ago" is a query, not an archaeology project. |
| **Words are not evidence** | A hype lexicon penalises promotional language; the penalty is only forgiven by *measurable* counter-evidence (revenue, patents, citations, contracts). |
| **Cheap before expensive** | A 4-stage funnel. Stage 1 screening is deterministic/free; only survivors reach expensive multi-agent analysis. |
| **Runs with zero API keys** | Every external source has a deterministic mock. The full pipeline runs offline. |

### The anti-leakage rule

This is the single most important structural decision. `AsOfContext` is threaded
through every repository read:

```python
with as_of(date(2015, 1, 1)):
    candidates = repo.list_candidates()   # sees only facts published <= 2015-01-01
```

Because the filter lives in the data-access layer rather than in agent prompts,
an agent *cannot* accidentally cheat, and the 2012-backtest (§30) is meaningful
rather than self-congratulatory.

---

## 2. Component map

```
                        ┌──────────────────────────┐
                        │   Next.js dashboard      │
                        │   TS + Tailwind          │
                        └───────────┬──────────────┘
                                    │ REST (typed)
                        ┌───────────▼──────────────┐
                        │   FastAPI  (api/)        │
                        └───────────┬──────────────┘
                                    │
       ┌────────────────────────────┼─────────────────────────────┐
       │                            │                             │
┌──────▼───────┐          ┌─────────▼─────────┐        ┌──────────▼────────┐
│  pipeline/   │          │     agents/       │        │      core/        │
│ 4-stage      │─────────▶│ 12 specialists +  │───────▶│ pure functions:   │
│ funnel,      │          │ debate + judge    │        │ math, scenarios,  │
│ daily loop   │          │                   │        │ scoring, signals, │
└──────┬───────┘          └─────────┬─────────┘        │ redflags, hype    │
       │                            │                  └───────────────────┘
       │                  ┌─────────▼─────────┐          (no I/O, no LLM,
       │                  │      llm/         │           fully unit-tested)
       │                  │ tiered client,    │
       │                  │ cache, budget cap │
       │                  └───────────────────┘
┌──────▼───────┐
│  sources/    │  Source interface: fetch() → parse() → RawDoc[]
│  SEC, arXiv, │  each with tier, rate_limit, reliability_score
│  GitHub, HN… │  each with a deterministic Mock twin
└──────┬───────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│  PostgreSQL — append-only, fully timestamped                    │
└─────────────────────────────────────────────────────────────────┘
```

`core/` is deliberately pure: no network, no database, no LLM. All the
financial mathematics lives there and is exhaustively unit-tested, so the
numbers are trustworthy regardless of how erratic the language models are.

---

## 3. The 4-stage funnel (cost control, §43)

| Stage | What runs | Cost/candidate | Survivors |
| --- | --- | --- | --- |
| **1 — Screen** | Deterministic rules. Market-cap sanity, liquidity, hype density, hard red flags. **No LLM.** | $0 | ~15% |
| **2 — Triage** | One cheap LLM call (Haiku). "Is there a plausible 10x story here at all?" | ~$0.002 | ~30% of stage 1 |
| **3 — Deep** | Full multi-agent investigation: technology, market, competition, financial, signal, contrarian, future, valuation, fact-check, then debate + judge. | ~$0.30 | ~20% of stage 2 |
| **4 — Human** | Surfaced in the dashboard for a person to review. | — | — |

Every LLM call is content-hash cached, so re-running the pipeline is nearly free
and agent outputs are reproducible.

---

## 4. Scoring model

Two numbers that must never be conflated, plus a transparent composite.

**Overall score** — weighted per §11 (weights live in `core/scoring.py`, not
scattered in prompts):

```
future_market 15% · technology 15% · competitive_advantage 15% · early_signals 15%
valuation 15% · growth 10% · financial_health 10% · management 5%
```

then an explicit, itemised red-flag penalty (base score, penalty, and final are
all stored so nothing is silently subtracted).

**Asymmetry score** — expected gain per unit of expected loss, across the four
scenarios:

```
gain = Σ p_i (m_i − 1)   for m_i > 1
loss = Σ p_i (1 − m_i)   for m_i < 1
ratio = gain / loss              →  log-compressed to 0–100
```

This is a payoff ratio, not a return forecast. A candidate with a 25% chance of
20x and a 60% chance of −80% scores *well* on asymmetry and *badly* on
confidence — which is precisely the distinction the whole system exists to draw.

**Per-share reality check.** Every scenario multiple is additionally computed
net of dilution:

```
per_share_multiple = market_cap_multiple / (1 + dilution_cagr) ** years
```

A company that 10x's its market cap while tripling its share count returns
~3.3x to an existing holder. Tools that ignore this systematically overstate
micro-cap upside; this one does not.

---

## 5. Scenario engine (§20, §28)

Bottom-up, transparent, and reversible.

```
future_market × market_share            = revenue
revenue × net_margin                    = earnings
earnings × exit_multiple                = future market cap      (earnings path)
revenue × ev_sales_multiple             = future market cap      (revenue path)
future / current                        = multiple
multiple ** (1/years) − 1               = CAGR
Σ probability × value                   = expected value  (a model estimate)
```

Assumptions are stored as structured data, never prose, so they can be diffed
over time and challenged by the contrarian agent.

**Reverse valuation (§21)** runs the same pipeline backwards: given today's
market cap, solve for the revenue — and therefore the *market share* — that
today's price already assumes. Output reads: *"today's price already implies
34% share of a $60B market by 2035."* This is the primary defence against
falling in love with a great company at a ruinous price.

---

## 6. Agents

All inherit `agents/base.py::Agent`, which handles retries, JSON-schema
validation, caching, cost accounting, and writing an `agent_runs` audit row.

| # | Agent | Job |
| --- | --- | --- |
| 1 | Discovery | Generate queries, sweep sources, propose candidates |
| 2 | Technology | Real tech vs marketing; moat mechanics |
| 3 | Market | Independent TAM/SAM/SOM (never management's number) |
| 4 | Competition | Actively tries to destroy the moat |
| 5 | Financial | Metrics, dilution, quality of earnings |
| 6 | Early Signal | Acceleration detection before mainstream notice |
| 7 | Contrarian | Structurally forbidden from agreeing |
| 8 | Future | 2030/2035/2040 chains, second-order effects |
| 9 | Valuation | Scenarios, asymmetry, reverse valuation |
| 10 | Fact Checker | Source/date/claim/confidence on every assertion |
| 11 | Watchlist | Ranking, movement explanation |
| 12 | Thesis Tracker | Falsifiable conditions, invalidation flags |
| — | Debate + Judge | Adversarial round, saved verbatim |

The contrarian is prompted and *scored* adversarially: its output is rejected
and retried if it fails to produce a concrete, falsifiable failure mode.

---

## 7. Data model (highlights)

17 tables. The ones that carry the design:

- `claims` — every material assertion: `claim, source_id, published_at, confidence, supports/contradicts`. Nothing enters a report without a row here.
- `sources` — with `tier` (1 government/SEC/peer-reviewed → 5 social) and `reliability_score`. Social media may trigger *discovery* but can never be terminal *evidence*.
- `scores` — append-only, one row per scoring run, with components + weights inline.
- `signals` — `metric, window, baseline, current, pct_change, z_score, detected_at`.
- `theses` — with `conditions[]`, each independently monitored and individually invalidatable.
- `agent_runs` — model, tokens, cost, latency, cache hit, output hash. Full auditability of what the machine actually did.

---

## 8. Feedback loop (§51 — the most important feature)

Predictions are written down with a horizon and a falsifiable condition. When
the horizon arrives, `evaluation` compares belief to outcome and records a
Brier score per signal type. Over time this answers the only question that
matters: **which signals actually preceded large outcomes?** Those empirical
weights then replace the hand-tuned ones in §4.

The hand-tuned weights are therefore explicitly a *starting prior*, not the
system's final opinion.

---

## 9. Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2 | Best ecosystem for data/agents/ML (§32) |
| DB | PostgreSQL 16 | Per §16; JSONB for flexible agent payloads |
| Frontend | Next.js + TypeScript + Tailwind | Per §23 |
| LLM | Anthropic, tiered (Haiku screen → Opus deep) | Per §43 |
| Tests | pytest, SQLite in-memory | Zero-dependency test runs |

Tests run against SQLite so the suite needs no server; production runs on
Postgres. Portability is handled with `JSON().with_variant(JSONB, "postgresql")`.
