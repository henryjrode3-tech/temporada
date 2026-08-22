"""Analysis specialists: technology, market, competition, financials, future.

Each supplies one dimension of the composite score, a narrative, and structured
payload the dashboard renders. Every one has a deterministic fallback derived
from the same figures a model would be shown.
"""

from __future__ import annotations

from typing import Any

from ..core.finmath import burn_runway_years, rule_of_40, safe_ratio
from ..core.scoring import Dimension
from ..llm.client import Tier
from .base import Agent, AgentResult, CandidateContext


class TechnologyAgent(Agent):
    """Real technology, or marketing? (section 4)"""

    name = "technology"
    tier = Tier.DEEP
    dimension = Dimension.TECHNOLOGY
    max_tokens = 1600

    def build_prompt(self, ctx: CandidateContext) -> str:
        return f"""Assess the technology behind this candidate.

{ctx.brief()}

Your central task is to separate REAL TECHNOLOGY from MARKETING. Actively look
for evidence that CONTRADICTS the company's claims. Treat adjectives as noise
and measurements as signal.

Answer as JSON:
{{
  "what_it_does": "plain-language description, no jargon",
  "is_genuinely_novel": true/false,
  "novelty_rationale": "why, citing something concrete",
  "problem_solved": "...",
  "improvement_over_incumbent": "quantified if possible, else 'unquantified'",
  "reproducibility_difficulty": "trivial|moderate|hard|very hard",
  "moats": {{"patents": bool, "proprietary_data": bool, "network_effects": bool,
             "manufacturing": bool, "distribution": bool, "switching_costs": bool,
             "regulatory": bool, "talent": bool}},
  "moat_explanation": "...",
  "scientific_breakthrough_involved": bool,
  "contradicting_evidence": ["specific things that undercut the claims"],
  "marketing_vs_substance": "substance|mixed|mostly marketing",
  "technology_score": 0-10,
  "confidence": 0.0-1.0,
  "rationale": "two or three sentences"
}}"""

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        # Without a model, infer from what is measurable: gross margin is the
        # most honest available proxy for whether a technology is differentiated,
        # since commodity products cannot sustain high margins.
        gm = ctx.gross_margin
        score = 5.0
        if gm is not None:
            score = 8.0 if gm > 0.60 else 6.5 if gm > 0.40 else 5.0 if gm > 0.20 else 3.0 if gm >= 0 else 2.0
        if ctx.hype_score > 50:
            score -= 2.0
        sig_types = {s.get("signal_type") for s in ctx.signals}
        if {"patent_filings", "publications", "research_citations"} & sig_types:
            score += 1.0
        score = max(0.0, min(10.0, score))
        return {
            "what_it_does": ctx.description[:400],
            "is_genuinely_novel": bool({"patent_filings", "publications"} & sig_types),
            "novelty_rationale": "Heuristic: inferred from patent and publication activity.",
            "problem_solved": "Not assessed without a language model.",
            "improvement_over_incumbent": "unquantified",
            "reproducibility_difficulty": "moderate",
            "moats": {"patents": "patent_filings" in sig_types, "proprietary_data": False,
                      "network_effects": False, "manufacturing": False, "distribution": False,
                      "switching_costs": False, "regulatory": False, "talent": False},
            "moat_explanation": "Heuristic assessment; no qualitative moat analysis performed.",
            "scientific_breakthrough_involved": False,
            "contradicting_evidence": [],
            "marketing_vs_substance": "mostly marketing" if ctx.hype_score > 50 else "mixed",
            "technology_score": score,
            "confidence": 0.25,
            "rationale": (
                f"Heuristic score from gross margin "
                f"({f'{gm:.0%}' if gm is not None else 'unknown'}) and research activity. "
                f"No qualitative technology assessment was performed."
            ),
        }

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name, ok=True,
            dimension_score=self.score(
                data.get("technology_score", 5),
                data.get("rationale", ""),
                data.get("confidence", 0.5),
            ),
            payload=data,
            narrative=str(data.get("what_it_does", ""))[:2000],
        )


class MarketAgent(Agent):
    """Independent TAM/SAM/SOM. Management's number is evidence, not truth."""

    name = "market"
    tier = Tier.DEEP
    dimension = Dimension.MARKET
    max_tokens = 1600

    def build_prompt(self, ctx: CandidateContext) -> str:
        return f"""Estimate the market this candidate could eventually operate in.

{ctx.brief()}

Build the estimate BOTTOM-UP and independently. Do NOT copy any TAM the company
claims. Reason from: how many potential customers exist, what they would
realistically pay, and how often they would buy.

Consider whether the market itself could grow far beyond its current size, and
whether this technology could turn a small market into a large one.

JSON:
{{
  "market_name": "...",
  "customer_count": number,
  "price_per_customer": number,
  "purchase_frequency_per_year": number,
  "tam_usd": number,
  "sam_usd": number,
  "som_usd": number,
  "tam_2035_usd": number,
  "methodology": "show the arithmetic",
  "market_could_be_created": bool,
  "adjacent_expansion": ["..."],
  "key_uncertainty": "the assumption most likely to be wrong",
  "market_score": 0-10,
  "confidence": 0.0-1.0,
  "rationale": "..."
}}"""

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        tam = ctx.tam_estimate or (ctx.revenue * 200 if ctx.revenue else 5e9)
        score = 9.0 if tam > 100e9 else 7.5 if tam > 40e9 else 6.0 if tam > 10e9 else 4.0 if tam > 2e9 else 2.0
        return {
            "market_name": ctx.industry or ctx.sector or "unspecified",
            "customer_count": 0, "price_per_customer": 0, "purchase_frequency_per_year": 0,
            "tam_usd": tam, "sam_usd": tam * 0.3, "som_usd": tam * 0.05,
            "tam_2035_usd": tam * 1.8,
            "methodology": "Heuristic: supplied estimate, or revenue scaled by a sector multiple.",
            "market_could_be_created": False, "adjacent_expansion": [],
            "key_uncertainty": "No independent bottom-up estimate was constructed.",
            "market_score": score, "confidence": 0.2,
            "rationale": f"Heuristic sizing at ${tam/1e9:.1f}B. Not an independent estimate.",
        }

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name, ok=True,
            dimension_score=self.score(
                data.get("market_score", 5), data.get("rationale", ""), data.get("confidence", 0.5)
            ),
            payload=data,
            narrative=str(data.get("methodology", ""))[:2000],
        )


class CompetitionAgent(Agent):
    """Tries to destroy the moat (section 6)."""

    name = "competition"
    tier = Tier.DEEP
    dimension = Dimension.COMPETITIVE_ADVANTAGE
    max_tokens = 1600
    temperature = 0.3

    def build_prompt(self, ctx: CandidateContext) -> str:
        return f"""Analyse the competitive position, and try to DESTROY the thesis.

{ctx.brief()}

Assume by default that any advantage is temporary. Your job is to find the
reason this company loses. Specifically address whether a large incumbent
(Google, Microsoft, Nvidia, Apple, Amazon, Meta, Tesla, Siemens, ABB, TSMC or a
similar giant in the relevant field) could simply copy this, and what would
actually stop them.

JSON:
{{
  "direct_competitors": ["..."],
  "indirect_competitors": ["..."],
  "incumbents": ["..."],
  "open_source_alternatives": ["..."],
  "substitute_technologies": ["..."],
  "who_is_winning_now": "...",
  "why_they_are_winning": "...",
  "giant_could_copy": bool,
  "what_stops_them": "the honest answer, which may be 'nothing'",
  "durable_advantage_exists": bool,
  "advantage_description": "...",
  "years_of_lead_time": number,
  "strongest_competitive_threat": "...",
  "competitive_advantage_score": 0-10,
  "confidence": 0.0-1.0,
  "rationale": "..."
}}"""

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        gm = ctx.gross_margin
        # Durable pricing power shows up as margin. Absent other evidence this
        # is the only defensible proxy available without a model.
        score = 5.0
        if gm is not None:
            score = 8.0 if gm > 0.65 else 6.0 if gm > 0.40 else 4.0 if gm > 0.20 else 2.5
        if ctx.extra.get("largest_customer_pct", 0) and ctx.extra["largest_customer_pct"] > 0.5:
            score -= 1.5
        score = max(0.0, min(10.0, score))
        return {
            "direct_competitors": ctx.competitors, "indirect_competitors": [],
            "incumbents": [], "open_source_alternatives": [], "substitute_technologies": [],
            "who_is_winning_now": "unknown", "why_they_are_winning": "not assessed",
            "giant_could_copy": gm is None or gm < 0.4,
            "what_stops_them": "Not assessed without a language model.",
            "durable_advantage_exists": bool(gm and gm > 0.5),
            "advantage_description": "Inferred from gross margin only.",
            "years_of_lead_time": 0,
            "strongest_competitive_threat": "unassessed",
            "competitive_advantage_score": score, "confidence": 0.2,
            "rationale": "Heuristic: gross margin used as a proxy for pricing power.",
        }

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name, ok=True,
            dimension_score=self.score(
                data.get("competitive_advantage_score", 5),
                data.get("rationale", ""), data.get("confidence", 0.5),
            ),
            payload=data,
            narrative=str(data.get("advantage_description", ""))[:2000],
        )


class FinancialAgent(Agent):
    """Financial quality. Mostly arithmetic, so mostly deterministic.

    Runs on the cheap tier because the numbers are computed in ``core`` rather
    than reasoned about: the model's role is interpretation, not calculation.
    """

    name = "financial"
    tier = Tier.CHEAP
    dimension = Dimension.FINANCIAL_HEALTH
    max_tokens = 1000

    def _metrics(self, ctx: CandidateContext) -> dict[str, Any]:
        runway = burn_runway_years(ctx.cash or 0.0, ctx.free_cash_flow or 0.0)
        fcf_margin = safe_ratio(ctx.free_cash_flow, ctx.revenue)
        dilution = None
        if ctx.shares_outstanding and ctx.shares_outstanding_prior:
            dilution = ctx.shares_outstanding / ctx.shares_outstanding_prior - 1
        return {
            "ps_ratio": safe_ratio(ctx.market_cap, ctx.revenue),
            "fcf_margin": fcf_margin,
            "rule_of_40": (
                rule_of_40(ctx.revenue_growth, fcf_margin)
                if ctx.revenue_growth is not None and fcf_margin is not None else None
            ),
            "runway_years": runway,
            "dilution_yoy": dilution,
            "net_cash": (ctx.cash or 0) - (ctx.debt or 0),
            "gross_margin": ctx.gross_margin,
            "revenue_growth": ctx.revenue_growth,
        }

    def build_prompt(self, ctx: CandidateContext) -> str:
        m = self._metrics(ctx)
        return f"""Assess financial health and quality.

{ctx.brief()}

Computed metrics (authoritative - do not recompute):
{m}

Judge durability, not optics: can this company fund its own future, or does it
depend on capital markets staying friendly?

JSON:
{{
  "can_self_fund": bool,
  "financing_risk": "none|low|moderate|high|severe",
  "dilution_assessment": "...",
  "quality_of_growth": "...",
  "balance_sheet_assessment": "...",
  "key_financial_risk": "...",
  "financial_health_score": 0-10,
  "growth_score": 0-10,
  "confidence": 0.0-1.0,
  "rationale": "..."
}}"""

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        m = self._metrics(ctx)
        score = 5.0
        if m["net_cash"] > 0:
            score += 1.0
        if m["runway_years"] is None:          # not burning cash
            score += 2.0
        elif m["runway_years"] < 1:
            score -= 3.0
        elif m["runway_years"] < 2:
            score -= 1.5
        if m["dilution_yoy"] is not None:
            if m["dilution_yoy"] > 0.25:
                score -= 2.0
            elif m["dilution_yoy"] > 0.10:
                score -= 1.0
        if m["gross_margin"] is not None and m["gross_margin"] < 0:
            score -= 1.5
        score = max(0.0, min(10.0, score))

        growth = 5.0
        if ctx.revenue_growth is not None:
            growth = (10.0 if ctx.revenue_growth > 1.0 else 8.5 if ctx.revenue_growth > 0.5
                      else 7.0 if ctx.revenue_growth > 0.3 else 5.0 if ctx.revenue_growth > 0.1
                      else 3.0 if ctx.revenue_growth > 0 else 1.0)
        return {
            "can_self_fund": m["runway_years"] is None,
            "financing_risk": ("none" if m["runway_years"] is None else
                               "severe" if m["runway_years"] < 1 else
                               "high" if m["runway_years"] < 2 else "moderate"),
            "dilution_assessment": (
                f"Share count {m['dilution_yoy']:+.1%} YoY"
                if m["dilution_yoy"] is not None else "unknown"
            ),
            "quality_of_growth": "not assessed",
            "balance_sheet_assessment": f"Net cash ${m['net_cash']/1e6:,.0f}M",
            "key_financial_risk": (
                "Cash runway under two years"
                if m["runway_years"] is not None and m["runway_years"] < 2
                else "None identified arithmetically"
            ),
            "financial_health_score": score, "growth_score": growth,
            "confidence": 0.6,   # arithmetic, so more trustworthy than the other fallbacks
            "rationale": "Computed from balance sheet and cash flow arithmetic.",
            "computed_metrics": m,
        }

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        data.setdefault("computed_metrics", self._metrics(ctx))
        return AgentResult(
            agent_name=self.name, ok=True,
            dimension_score=self.score(
                data.get("financial_health_score", 5),
                data.get("rationale", ""), data.get("confidence", 0.6),
            ),
            payload=data,
            narrative=str(data.get("balance_sheet_assessment", ""))[:2000],
        )


class FutureAgent(Agent):
    """2030 / 2035 / 2040, and second-order chains (sections 10 and 38)."""

    name = "future"
    tier = Tier.DEEP
    dimension = Dimension.FUTURE_UPSIDE
    max_tokens = 1800
    temperature = 0.5   # divergent thinking is the point of this agent

    def build_prompt(self, ctx: CandidateContext) -> str:
        return f"""Place this candidate in the world of 2030, 2035 and 2040.

{ctx.brief()}

Think in TECHNOLOGICAL CHAINS. The best opportunity is often several layers
away from the obvious trend. For example: AI growth -> data centres ->
electricity -> grid capacity -> transformers -> specialty steel -> mining.

Identify where this candidate sits in such a chain, and whether it benefits from
a trend without being the crowded, obvious way to express it.

JSON:
{{
  "world_2030": "...", "world_2035": "...", "world_2040": "...",
  "chain": ["driver", "consequence", "consequence", "where this sits"],
  "position_in_chain": "...",
  "is_second_order_play": bool,
  "industries_that_grow": ["..."],
  "industries_that_shrink": ["..."],
  "becomes_necessary_infrastructure": bool,
  "what_must_be_true": ["..."],
  "what_would_make_it_irrelevant": ["..."],
  "future_upside_score": 0-10,
  "confidence": 0.0-1.0,
  "rationale": "..."
}}"""

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        tam = ctx.tam_estimate or 0
        score = 8.0 if tam > 100e9 else 6.5 if tam > 30e9 else 5.0 if tam > 10e9 else 3.0
        return {
            "world_2030": "Not assessed without a language model.",
            "world_2035": "Not assessed.", "world_2040": "Not assessed.",
            "chain": [], "position_in_chain": "unknown", "is_second_order_play": False,
            "industries_that_grow": [], "industries_that_shrink": [],
            "becomes_necessary_infrastructure": False,
            "what_must_be_true": [], "what_would_make_it_irrelevant": [],
            "future_upside_score": score, "confidence": 0.15,
            "rationale": "Heuristic: scaled from market size only.",
        }

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name, ok=True,
            dimension_score=self.score(
                data.get("future_upside_score", 5),
                data.get("rationale", ""), data.get("confidence", 0.4),
            ),
            payload=data,
            narrative=str(data.get("position_in_chain", ""))[:2000],
        )
