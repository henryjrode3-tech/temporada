# Asymmetry Engine

A research platform that hunts for **asymmetric opportunities**: things that are
obscure and reasonably priced today but could plausibly matter enormously in
5–15 years.

It is a **research tool, not a trading system**. It never says "buy". It cannot
predict the future and does not claim to. What it does is find interesting
possibilities before they become obvious, show its working, and argue with
itself about whether it is wrong.

```
$ asymmetry run
$ asymmetry top

  #  Name                       Cap    Asym  Overall  Risk  Verdict
  1  Halden Thermal Systems   $520M      76       64   5.0  INVESTIGATE
  2  Meridian Grid Components   $1.4B    71       64   5.0  INVESTIGATE
  3  Ironbark OT Security     $890M      63       69   5.0  WATCH
```

---

## Quick start

Runs completely offline, with no API key, in about a minute.

```bash
cd asymmetry/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Postgres (recommended)
docker compose -f ../docker-compose.yml up -d
export ASYMMETRY_DATABASE_URL='postgresql+psycopg2://asymmetry:asymmetry@localhost:5432/asymmetry'
# ...or SQLite, for a look around with no server at all:
# export ASYMMETRY_DATABASE_URL='sqlite:///./asymmetry.db'

.venv/bin/python -m asymmetry.cli init --drop
.venv/bin/python -m asymmetry.cli seed      # 14 fictional companies
.venv/bin/python -m asymmetry.cli run       # full pipeline
.venv/bin/python -m asymmetry.cli top
.venv/bin/python -m asymmetry.cli show Halden
```

Then the dashboard:

```bash
cd ../frontend && npm install && npm run dev     # http://localhost:3000
# in another terminal:
cd ../backend && .venv/bin/python -m asymmetry.cli serve   # http://localhost:8000
```

**Everything seeded is fictional.** Inventing financials for real tickers would
manufacture false records about real businesses, so the demo corpus uses
invented companies, tagged synthetic, on the lowest evidence tier.

### With a language model

```bash
export ANTHROPIC_API_KEY=sk-...
.venv/bin/python -m asymmetry.cli run
```

Without a key every agent falls back to deterministic heuristics derived from
the same figures, and each result is labelled `heuristic` so it is never
confused with model reasoning.

---

## Researching a real company

```bash
export ASYMMETRY_USER_AGENT="YourTool/1.0 (you@example.com)"   # the SEC requires this
.venv/bin/python -m asymmetry.cli research IONQ --price 45
```

Pulls real fundamentals from SEC XBRL filings and grades every number:

```
Grade        Item                        Value      Source
FACT         Revenue (latest annual)     $130.02M   SEC EDGAR 10-K · FY2025 · filed 2026-02-25
DERIVED      Revenue growth (YoY)        201.9%     SEC EDGAR 10-K · FY2024 · filed 2025-02-26
FACT         Stock-based compensation    $312.03M   SEC EDGAR 10-K · FY2025 · filed 2026-02-25
DERIVED      Annual dilution             25.1%      SEC EDGAR
ASSUMPTION   Addressable market          $10.40B    No independent market study was performed

critical  Severe dilution — share count grew 63% year over year
high      Extreme stock-based compensation — SBC is 240% of revenue

Today's price requires 127% of the entire estimated market — more than the
market contains.

Verdict: NOT_ASYMMETRIC — asymmetry 4/100
```

**Five grades, and a claim can never outrank its weakest input.** A scenario
built on an assumed market size is an ASSUMPTION however much audited revenue
also went into it — enforced in code, because remembering to downgrade by hand
fails silently and in the flattering direction.

| Grade | Meaning |
| --- | --- |
| FACT | In a regulatory filing. Cited to the exact accession number. |
| DERIVED | Arithmetic on facts. |
| ESTIMATE | Approximated from partial data. |
| ASSUMPTION | Chosen by the model. Not evidence. |
| AI INTERPRETATION | A language model's reading. Unverified. |

### Point-in-time, properly

Every SEC datapoint carries both the period it covers *and the date it was
filed*. The as-of filter reads **filed**, so a 2015 query sees FY2014 as
originally reported — not as restated in 2017.

```bash
.venv/bin/python -m asymmetry.cli research AAPL --as-of 2021-01-01
```

### What has no free source

**Share price.** The SEC does not publish it, and market cap is the denominator
of every multiple here. So there is no default price provider — without one the
report omits valuation entirely and says why, rather than inventing a number
and computing a confident-looking asymmetry score on top of it. Supply one with
`--price`, or configure Tiingo/Polygon.

---

## What it actually does

For each candidate it asks one question — *if this became extremely successful,
what would it be worth, and does today's price reflect that possibility?* — and
answers it in a way you can audit.

**1. Scenarios, built bottom-up.** Bear / base / bull / extreme bull, each from
explicit assumptions:

```
future market × market share = revenue → × margin = earnings → × multiple = value
```

**2. Reality checks on the bull case.** Two ceilings, both reported when they
fire. The revenue-growth ceiling rejects scenarios implying growth no company
has sustained; the market-share ceiling catches large companies being quietly
handed their whole industry. Without them the model cheerfully asserted a 2700x
outcome for a company with $5M of revenue.

**3. Dilution.** Every multiple is also computed per share. A company can 10x
its market cap while tripling its share count and return 3.3x to a holder.

**4. Median, not just mean.** These distributions are power-law shaped, so the
mean is dominated by the least likely branch. Both are shown, and when the top
scenario supplies most of the expected value it says so:

> Median outcome **2.99x** | Expected 22.99x | P(loss) 40%
> ⚠ 63% of the expected value comes from the single least likely scenario. Read the median instead.

**5. Reverse valuation** — the most important defensive step. Given today's
price, what does it already assume?

> "Today's price only requires 2.5% share of a $28B market. Modest embedded expectations."

A great company at a price that already assumes perfection is not an asymmetric
opportunity, and this is what catches that.

**6. Signals.** Acceleration in hiring, patents, publications, contracts,
repositories. Two independent tests must agree — a large percentage move *and*
significance against the metric's own volatility — because a metric that always
swings 300% has not done anything by swinging again.

**7. Red flags.** Deterministic checks: dilution, runway, margin collapse,
customer concentration, insider selling, going-concern doubt, restatements.
Itemised, never a mystery subtraction.

**8. The no-hype rule.** Promotional language is measured and penalised, and
only *measurable* evidence forgives it — and never entirely.

**9. Alerts that fire on change, not state.** "Asymmetry above 85" as a
standing condition would re-fire every run for the same candidate until it
stopped being true, which teaches you to ignore alerts. Every rule compares
against the previous run and fires only on the transition:

```
critical  Halden Thermal Systems: Red-flag score jumped — rose 62 points to 62/100
critical  Halden Thermal Systems: Candidate rejected — moved from INVESTIGATE to REJECTED
high      Halden Thermal Systems: Risk assessment worsened — rose 2.8 to 7.8/10
info      Halden Thermal Systems: Left the top 10 — moved from #1 to unranked
```

**10. Second-order search.** The obvious way to express a trend is crowded and
therefore expensive. The technology graph traces a driver upstream to what it
cannot proceed without:

```
$ asymmetry second-order "AI compute demand"

AI compute demand -> data centre capacity -> electrical power
                  -> grid capacity -> high-voltage transformers
                  -> grain-oriented electrical steel

 Depth  Node                             Bottleneck
     5  grain-oriented electrical steel  yes
     4  high-voltage transformers        yes
     3  semiconductor metrology          yes
```

Depth is the signal: the further from the driver, the less of the narrative is
already in the price. Note that depth is relative to a *driver* — grid capacity
is a first-order electrification play and a third-order AI play at the same
time.

---

## Two numbers that never mix

| | |
| --- | --- |
| **Asymmetry score** | how lopsided the payoff is |
| **Confidence score** | how much the analysis can be trusted |

A candidate with a 25% chance of 20x and a 60% chance of losing 80% scores
*well* on asymmetry and *badly* on confidence. Averaging them would destroy the
only distinction that matters, so they are computed separately and never
combined.

## Verdicts

`TOP_OPPORTUNITY` · `INVESTIGATE` · `WATCH` · `INTERESTING` · `HIGH_RISK` ·
`THESIS_WEAKENING` · `THESIS_INVALIDATED` · `REJECTED`

There is deliberately no BUY, SELL or HOLD, and a test asserts none appears in
any API response.

---

## Cost control

A four-stage funnel. Stage 1 is free and deterministic; only survivors are
allowed to cost money.

| Stage | Runs | Cost each |
| --- | --- | --- |
| 1 Screen | rules only, no LLM | $0 |
| 2 Triage | one cheap call | ~$0.002 |
| 3 Deep | full multi-agent + debate | ~$0.30 |
| 4 Human | you | — |

Every call is content-hash cached, and a hard per-run ceiling degrades to
heuristics rather than overspending.

## No hindsight leakage

Every fact carries `published_at`. The as-of filter lives in the data-access
layer, not in prompts, so an agent cannot see the future even if asked to:

```python
with as_of(date(2015, 1, 1)):
    ...  # only facts published on or before 2015-01-01 exist
```

Undated facts are excluded under a cutoff, because a fact that cannot be shown
to predate the cutoff might not. This is what makes the historical backtest
worth running.

```bash
.venv/bin/python -m asymmetry.cli run --as-of 2015-01-01
```

## History is the product

`scores`, `financial_metrics` and `market_estimates` are append-only. Each score
snapshot stores its own components *and weights*, so an old score stays
interpretable after the model is recalibrated — and "why did this fall from #2
to #17" is answered, not merely recorded:

> Dropped out of the ranking (was #1); now REJECTED. Score fell 43.2 points.
> Driven by financial health deteriorated 8.0 to 0.0 (−8.0 points) and
> technology deteriorated 5.0 to 3.0 (−3.0 points). New red flags: Collapsing
> gross margin, Severe dilution, Under 12 months of cash.

Attribution uses the weights that were in force at the time, because a
recalibration is a change in the model, not in the candidate.

---

## Commands

```bash
asymmetry init [--drop]        create schema
asymmetry seed                 load the synthetic corpus
asymmetry run [--limit N] [--as-of YYYY-MM-DD]
asymmetry top [--limit N]      current ranking
asymmetry show NAME            full report for one candidate
asymmetry report               daily research report
asymmetry second-order DRIVER  trace a trend upstream to its bottlenecks
asymmetry ingest-github O/R    pull real commit history into the signal series
asymmetry learning             what the system has learned from resolved predictions
asymmetry sources              sources, tiers, and what is deliberately absent
asymmetry serve                start the API
```

## Tests

```bash
cd backend && .venv/bin/python -m pytest      # 379 tests
```

They run on SQLite, so no database server is needed. They cover the financial
mathematics against the specification's worked examples, the plausibility
clamps, signal detection under noise, the anti-leakage guarantee, SQL-injection
safety, and the rule that no endpoint ever says "buy".

## Sources

Only official, documented, openly accessible APIs: SEC EDGAR, arXiv, GitHub,
Hacker News. Sources requiring circumvention of access controls or paywalls are
**deliberately not implemented** and are listed as unavailable with the reason —
run `asymmetry sources`. Social media is tier 5: it may surface a lead but can
never substantiate a claim.

## Status

Phase 1 and much of Phase 2 are built and tested. See
[`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for what is done and what is
next, and [`ARCHITECTURE.md`](ARCHITECTURE.md) for how it fits together.

## Does it actually work?

The system grades itself, and is built to be able to fail that grade.

Predictions are generated from thesis conditions — already falsifiable by
construction — recorded with a horizon and the signals that drove them, then
scored when the horizon arrives.

```
$ asymmetry learning

Only 12 resolved prediction(s); 20 are needed before these figures mean
anything. Reported for transparency, not for use.

Brier 0.348   Skill -3.562   Base rate 91.7%   Overconfidence -52.2%
```

Three things it refuses to do:

- **Draw conclusions from thin data.** Under 20 resolutions, every figure is
  marked *not for use*.
- **Hide behind accuracy.** It computes **skill against the base rate**. A model
  predicting 5% for a 5% event scores a beautiful Brier of 0.048 and a skill of
  exactly zero — and the report says so.
- **Change its own weights quietly.** Recalibration is proposed, never applied.

It has already caught a flaw in itself: the report above shows the system
*underconfident by 52%*, because predictions inherit the analysis confidence
score rather than a per-condition probability. Those are different quantities.
A feedback loop discovering that its own inputs are miscalibrated on the first
run is the mechanism doing its job.

---

## What this is not

It cannot predict the future. The scenarios are conditional arithmetic, not
forecasts, and the probabilities attached to them are priors chosen by hand
rather than measured. Almost every candidate it surfaces will not become
important — that is the nature of the search. It is a machine for finding
interesting possibilities before they are obvious, and for arguing with itself
about whether they are real.

Research output only. Not investment advice.
