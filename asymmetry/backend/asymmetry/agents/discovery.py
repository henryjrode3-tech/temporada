"""Discovery and thesis agents.

Discovery generates its own search queries rather than reading a fixed list, so
the system can wander into areas nobody told it about. That recursion is the
mechanism behind the "unknown unknown" requirement in section 39: the query
generator is asked what it is *not* looking at.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from ..llm.client import Tier
from .base import Agent, AgentResult, CandidateContext

#: Seed areas. Starting points for query generation, not the full search space -
#: the generator is expected to move beyond them.
SEED_DOMAINS: list[str] = [
    "grid infrastructure and transformers", "small modular nuclear reactors",
    "data-centre cooling and power", "silicon photonics and optical interconnect",
    "semiconductor metrology and inspection", "advanced packaging",
    "industrial robotics and mobile manipulation", "precision fermentation",
    "rare-earth and critical-mineral processing", "solid-state and sodium-ion batteries",
    "space-based sensing and SAR", "operational-technology cybersecurity",
    "quantum sensing and metrology", "superconducting materials",
    "grid-scale long-duration storage", "geothermal drilling technology",
    "carbon capture materials", "biomanufacturing scale-up",
    "defence autonomy and counter-UAS", "advanced materials and composites",
]

#: Query templates aimed at the early, unglamorous corners of a field rather
#: than at whatever is currently being written about.
QUERY_TEMPLATES: list[str] = [
    "{domain} small public company",
    "{domain} government contract award",
    "{domain} patent filing",
    "{domain} manufacturing capacity expansion",
    "{domain} qualification programme customer",
    "{domain} research breakthrough",
    "emerging {domain} startup funding",
    "{domain} supply chain bottleneck",
]


class DiscoveryAgent(Agent):
    """Generates queries and proposes candidates (section 3).

    Runs on the cheap tier: discovery is high-volume and low-stakes, since
    everything it proposes must survive screening before costing real money.
    """

    name = "discovery"
    tier = Tier.CHEAP
    dimension = None
    max_tokens = 1400
    temperature = 0.8   # exploration, not precision
    system_prompt = (
        "You find obscure, early-stage opportunities before they are widely "
        "discussed. You deliberately avoid whatever is currently popular: if a "
        "company is already widely covered, it is not what you are looking for. "
        "You are drawn to unglamorous suppliers, second-order beneficiaries, and "
        "technical bottlenecks that few people think about. "
        "Reply with valid JSON only."
    )

    def build_prompt(self, ctx: CandidateContext) -> str:
        domain = ctx.extra.get("domain", "emerging technology")
        avoid = ctx.extra.get("already_known", [])
        return f"""Propose search queries and candidate areas in: {domain}

Already in the database (do not propose these): {', '.join(avoid[:40]) or 'none'}

Look for what is EARLY and UNDER-DISCUSSED. Prefer suppliers and bottlenecks
over the obvious end-market names. Then name one category that this search is
systematically ignoring.

JSON:
{{
  "queries": ["8-12 specific search queries"],
  "candidate_areas": [
    {{"area": "...", "why_now": "...", "second_order": bool}}
  ],
  "adjacent_domains_to_explore": ["..."],
  "category_being_ignored": "a whole area this search is blind to",
  "rationale": "..."
}}"""

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        domain = ctx.extra.get("domain", SEED_DOMAINS[0])
        return {
            "queries": [t.format(domain=domain) for t in QUERY_TEMPLATES],
            "candidate_areas": [{"area": domain, "why_now": "seed domain", "second_order": False}],
            "adjacent_domains_to_explore": [],
            "category_being_ignored": "unknown without a language model",
            "rationale": "Heuristic: template-expanded queries for the seed domain.",
        }

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        queries = [str(q) for q in data.get("queries", []) if str(q).strip()][:20]
        return AgentResult(
            agent_name=self.name, ok=True,
            payload={**data, "queries": queries},
            narrative=f"{len(queries)} queries generated.",
        )


def dedupe_key(name: str, ticker: str | None = None) -> str:
    """Stable identity key so the same company is not discovered repeatedly.

    Ticker wins when present because names drift (suffixes, punctuation,
    rebrands) while tickers are stable identifiers.
    """
    if ticker and ticker.strip():
        return f"t:{ticker.strip().upper()}"
    normalised = re.sub(r"[^a-z0-9]+", "", name.lower())
    for suffix in ("inc", "corp", "corporation", "ltd", "limited", "plc",
                   "llc", "holdings", "group", "technologies", "systems"):
        if normalised.endswith(suffix):
            normalised = normalised[: -len(suffix)]
            break
    return f"n:{hashlib.sha256(normalised.encode()).hexdigest()[:20]}"


class ThesisAgent(Agent):
    """Writes a falsifiable thesis with monitorable conditions (section 14)."""

    name = "thesis"
    tier = Tier.DEEP
    dimension = None
    max_tokens = 1400
    system_prompt = (
        "You write investment theses that can be proven WRONG. A thesis that "
        "cannot be falsified is worthless. Every condition you state must be "
        "measurable and checkable against future evidence, with a number and a "
        "direction wherever possible. Reply with valid JSON only."
    )

    def build_prompt(self, ctx: CandidateContext) -> str:
        return f"""Write a falsifiable thesis for this candidate.

{ctx.brief()}

State one clear thesis, then list 4-7 conditions that must hold. Each condition
must be measurable: name the metric, the comparator and the threshold, so it can
be checked automatically later.

JSON:
{{
  "statement": "one sentence, specific",
  "horizon_years": number,
  "conditions": [
    {{"text": "human-readable condition",
      "metric": "revenue_growth|gross_margin|customer_count|market_share|cash_runway|...",
      "comparator": ">|>=|<|<=",
      "threshold": number,
      "why_it_matters": "..."}}
  ],
  "what_would_invalidate": ["..."],
  "confidence": 0.0-1.0
}}"""

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        """Conditions anchored to where the company actually stands today.

        Fixed thresholds would declare most candidates broken on day one, which
        says nothing: a thesis is about whether a company holds its trajectory,
        so each condition is set relative to the current observation.
        """
        conditions: list[dict[str, Any]] = []

        if ctx.revenue_growth is not None:
            # Require that growth does not collapse, rather than that it hits an
            # arbitrary bar the company may never have cleared.
            floor = round(max(0.10, ctx.revenue_growth * 0.6), 2)
            conditions.append({
                "text": f"Revenue growth stays above {floor:.0%} "
                        f"(currently {ctx.revenue_growth:.0%})",
                "metric": "revenue_growth", "comparator": ">=", "threshold": floor,
                "why_it_matters": "A sharp deceleration breaks the scenario arithmetic.",
            })

        if ctx.gross_margin is not None:
            floor = round(ctx.gross_margin - 0.08, 3)
            conditions.append({
                "text": f"Gross margin holds above {floor:.0%} "
                        f"(currently {ctx.gross_margin:.0%})",
                "metric": "gross_margin", "comparator": ">=", "threshold": floor,
                "why_it_matters": "Falling margin is the earliest sign a moat is not real.",
            })

        if ctx.shares_outstanding and ctx.shares_outstanding_prior:
            observed = ctx.shares_outstanding / ctx.shares_outstanding_prior - 1
            ceiling = round(max(0.08, observed * 1.2), 3)
            conditions.append({
                "text": f"Annual dilution stays below {ceiling:.0%} "
                        f"(currently {observed:.0%})",
                "metric": "dilution_yoy", "comparator": "<=", "threshold": ceiling,
                "why_it_matters": "Dilution transfers upside away from existing holders.",
            })

        if (ctx.free_cash_flow or 0) < 0:
            conditions.append({
                "text": "Cash runway remains above 1.5 years",
                "metric": "cash_runway", "comparator": ">=", "threshold": 1.5,
                "why_it_matters": "A short runway forces financing on poor terms.",
            })

        if not conditions:
            conditions.append({
                "text": "Revenue grows year over year",
                "metric": "revenue_growth", "comparator": ">", "threshold": 0.0,
                "why_it_matters": "Minimum evidence that the business is working.",
            })

        return {
            "statement": (
                f"{ctx.name} sustains its current trajectory in "
                f"{ctx.industry or ctx.sector or 'its market'}. Generated "
                f"mechanically from financial data, without qualitative analysis."
            ),
            "horizon_years": 10,
            "conditions": conditions,
            "what_would_invalidate": [
                "Growth decelerates sharply for two consecutive periods",
                "A credible incumbent ships a comparable product",
            ],
            "confidence": 0.2,
        }

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        conditions = [c for c in data.get("conditions", []) if isinstance(c, dict)]
        return AgentResult(
            agent_name=self.name, ok=True,
            payload={**data, "conditions": conditions},
            narrative=str(data.get("statement", ""))[:1000],
        )
