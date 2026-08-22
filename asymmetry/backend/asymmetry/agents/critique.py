"""Adversarial agents: contrarian, fact checker, debate and judge.

The contrarian is the most important agent in the system. Analysis engines drift
toward agreeableness - each specialist finds reasons its own dimension looks
interesting - and without structural opposition the result is a machine that
manufactures conviction. So the contrarian is not merely *asked* to disagree:
its output is rejected and retried when it fails to produce concrete,
falsifiable failure modes.
"""

from __future__ import annotations

from typing import Any

from ..core.scoring import Dimension
from ..llm.client import Tier
from .base import Agent, AgentResult, CandidateContext


class ContrarianAgent(Agent):
    """Answers only one question: why is this a terrible idea? (section 9)"""

    name = "contrarian"
    tier = Tier.DEEP
    dimension = Dimension.RISK
    max_tokens = 1800
    temperature = 0.4
    system_prompt = (
        "You are a short-seller and a professional sceptic. Your reputation rests "
        "on finding the flaw everyone else missed. You are structurally forbidden "
        "from concluding that something is a good opportunity - that is not your "
        "job and other analysts handle it. Every failure mode you name must be "
        "concrete and falsifiable: something that could be checked against "
        "reality, not a vague worry. 'Execution risk' is not an answer; "
        "'gross margin has never exceeded 12% and the bull case assumes 30%' is. "
        "Reply with valid JSON only."
    )

    def build_prompt(self, ctx: CandidateContext) -> str:
        return f"""Explain why this is a bad investment. Assume it fails.

{ctx.brief()}

Do not hedge and do not present a balanced view. Build the strongest possible
case that this loses most of its value. Every item must be specific enough that
someone could check whether it came true.

JSON:
{{
  "strongest_bear_case": "the single most persuasive argument, in detail",
  "most_likely_failure_mode": "...",
  "biggest_hidden_risk": "the one not in the risk factors",
  "competitive_threat": "...",
  "valuation_problem": "...",
  "technology_problem": "...",
  "regulatory_problem": "...",
  "management_problem": "...",
  "capital_requirements": "how much more money is needed, and from where",
  "dilution_risk": "...",
  "accounting_warning_signs": ["..."],
  "hype_indicators": ["..."],
  "what_would_have_to_go_right": ["improbable things the bull case requires"],
  "probability_of_permanent_loss": 0.0-1.0,
  "risk_score": 0-10,
  "confidence": 0.0-1.0,
  "rationale": "..."
}}"""

    def validate(self, data: Any) -> bool:
        """Reject agreeable or vacuous output.

        A contrarian that returns platitudes has not done its job, and letting
        that pass would quietly remove the system's main defence against its own
        optimism.
        """
        if not isinstance(data, dict):
            return False
        bear = str(data.get("strongest_bear_case", "")).strip()
        failure = str(data.get("most_likely_failure_mode", "")).strip()
        if len(bear) < 60 or len(failure) < 25:
            return False
        vacuous = {"execution risk", "market risk", "competition", "none",
                   "n/a", "unknown", "general risk", "the usual risks"}
        if bear.lower().strip(".") in vacuous or failure.lower().strip(".") in vacuous:
            return False
        must_go_right = data.get("what_would_have_to_go_right")
        return isinstance(must_go_right, list) and len(must_go_right) >= 1

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        # Build the bear case from the red flags that were actually detected,
        # so even the fallback names specific, checkable problems.
        flags = [f.get("title", "") for f in ctx.red_flags]
        critical = [f for f in ctx.red_flags if f.get("severity") == "critical"]
        risk = 5.0 + min(4.0, len(ctx.red_flags) * 0.6) + (1.0 if critical else 0.0)
        if ctx.hype_score > 50:
            risk += 1.0
        risk = max(0.0, min(10.0, risk))

        bear = (
            f"{ctx.name} carries {len(ctx.red_flags)} detected red flag(s)"
            + (f", including: {', '.join(flags[:4])}. " if flags else ". ")
            + "Detected mechanically from the financial data rather than from "
              "qualitative analysis, so the qualitative case may be worse."
        )
        return {
            "strongest_bear_case": bear,
            "most_likely_failure_mode": (
                "Runs out of capital before reaching self-funding scale and dilutes existing holders"
                if (ctx.free_cash_flow or 0) < 0
                else "Fails to grow into its valuation as competition compresses margins"
            ),
            "biggest_hidden_risk": "Not assessed without a language model.",
            "competitive_threat": "unassessed", "valuation_problem": "unassessed",
            "technology_problem": "unassessed", "regulatory_problem": "unassessed",
            "management_problem": "unassessed",
            "capital_requirements": "unassessed", "dilution_risk": "unassessed",
            "accounting_warning_signs": flags,
            "hype_indicators": ["Elevated promotional language"] if ctx.hype_score > 35 else [],
            "what_would_have_to_go_right": [
                "Revenue must compound for a decade without interruption",
                "Margins must expand well beyond current levels",
                "No incumbent may respond effectively",
            ],
            "probability_of_permanent_loss": min(0.9, 0.35 + len(ctx.red_flags) * 0.05),
            "risk_score": risk, "confidence": 0.4,
            "rationale": "Heuristic bear case assembled from detected red flags.",
        }

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name, ok=True,
            dimension_score=self.score(
                data.get("risk_score", 6), data.get("rationale", ""), data.get("confidence", 0.5)
            ),
            payload=data,
            narrative=str(data.get("strongest_bear_case", ""))[:3000],
        )


class FactCheckerAgent(Agent):
    """Every material claim needs a source, a date and a confidence (section 12)."""

    name = "factchecker"
    tier = Tier.CHEAP
    dimension = None
    max_tokens = 1600
    temperature = 0.0
    system_prompt = (
        "You verify claims. You prefer primary sources: SEC filings, government "
        "databases, peer-reviewed papers, official company filings. You treat "
        "social media as a lead, never as evidence. You distinguish fact from "
        "speculation and you record dates, because a true statement about 2019 "
        "may be false today. Reply with valid JSON only."
    )

    def build_prompt(self, ctx: CandidateContext) -> str:
        claims = "\n".join(
            f"- [{c.get('source_name', '?')} tier {c.get('source_tier', '?')}, "
            f"{c.get('published_at', 'undated')}] {c.get('claim', '')}"
            for c in ctx.claims[:25]
        ) or "(no claims recorded)"
        return f"""Fact-check the claims about this candidate.

{ctx.brief()}

Recorded claims:
{claims}

For each material claim decide: is it a verifiable FACT, an ESTIMATE, or
SPECULATION? Flag anything unsupported, outdated, or contradicted. Treat any
tier-5 (social media) source as insufficient on its own.

JSON:
{{
  "assessments": [
    {{"claim": "...", "classification": "fact|estimate|speculation",
      "supported": bool, "issue": "or empty", "confidence": 0.0-1.0}}
  ],
  "unsupported_claims": ["..."],
  "outdated_information": ["..."],
  "conflicting_information": ["..."],
  "overall_evidence_quality": "strong|adequate|thin|very thin",
  "share_of_claims_from_primary_sources": 0.0-1.0,
  "confidence": 0.0-1.0
}}"""

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        total = len(ctx.claims) or 1
        primary = sum(1 for c in ctx.claims if (c.get("source_tier") or 5) <= 2)
        undated = [c.get("claim", "") for c in ctx.claims if not c.get("published_at")]
        social_only = [c.get("claim", "") for c in ctx.claims if (c.get("source_tier") or 5) >= 5]
        ratio = primary / total
        return {
            "assessments": [
                {"claim": c.get("claim", ""),
                 "classification": "fact" if (c.get("source_tier") or 5) <= 2 else "estimate",
                 "supported": (c.get("source_tier") or 5) <= 4,
                 "issue": "Tier-5 source is not sufficient evidence"
                          if (c.get("source_tier") or 5) >= 5 else "",
                 "confidence": c.get("confidence", 0.5)}
                for c in ctx.claims[:25]
            ],
            "unsupported_claims": social_only,
            "outdated_information": undated,
            "conflicting_information": [],
            "overall_evidence_quality": (
                "strong" if ratio > 0.6 else "adequate" if ratio > 0.3
                else "thin" if ratio > 0.1 else "very thin"
            ),
            "share_of_claims_from_primary_sources": round(ratio, 3),
            "confidence": 0.5,
        }

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name, ok=True, payload=data,
            narrative=f"Evidence quality: {data.get('overall_evidence_quality', 'unknown')}",
        )


class DebateJudgeAgent(Agent):
    """Runs the adversarial round and adjudicates it (section 26).

    Uses the judge tier because synthesis across contradictory expert opinions
    is the hardest reasoning task in the pipeline and the one where a weaker
    model most often defaults to splitting the difference.
    """

    name = "judge"
    tier = Tier.JUDGE
    dimension = None
    max_tokens = 2200
    temperature = 0.3
    system_prompt = (
        "You adjudicate between analysts who disagree. You do not split the "
        "difference to seem balanced; you decide which argument is better "
        "supported and say so. You are explicit about the assumptions a "
        "conclusion depends on, and you state plainly when the evidence cannot "
        "support any confident conclusion. You never recommend buying or "
        "selling. Reply with valid JSON only."
    )

    def build_prompt(self, ctx: CandidateContext) -> str:
        positions = ctx.extra.get("agent_positions", {})
        rendered = "\n\n".join(
            f"{name.upper()} AGENT (score {p.get('score', '?')}/10):\n{p.get('summary', '')}"
            for name, p in positions.items()
        ) or "(no agent positions available)"
        return f"""Adjudicate this analysis.

{ctx.brief()}

Analyst positions:
{rendered}

Produce a debate and a judgment. The debate must contain genuine disagreement -
if every analyst agrees, say so and explain why that is itself suspicious.

JSON:
{{
  "turns": [
    {{"agent": "technology|market|competition|financial|future|contrarian",
      "position": "bull|bear|neutral",
      "argument": "one or two sentences in that analyst's voice"}}
  ],
  "central_disagreement": "...",
  "judgment": "your adjudication, naming which argument is better supported",
  "required_assumptions": ["assumptions the positive case depends on"],
  "assumption_count": number,
  "evidence_gaps": ["what would most change the conclusion if known"],
  "confidence_in_judgment": 0.0-1.0
}}"""

    def heuristic(self, ctx: CandidateContext) -> dict[str, Any]:
        positions = ctx.extra.get("agent_positions", {})
        turns = [
            {"agent": name,
             "position": ("bull" if (p.get("score") or 5) >= 7
                          else "bear" if (p.get("score") or 5) <= 4 else "neutral"),
             "argument": (p.get("summary") or "")[:300]}
            for name, p in positions.items()
        ]
        return {
            "turns": turns,
            "central_disagreement": "Not adjudicated without a language model.",
            "judgment": (
                "Heuristic mode: no adjudication performed. Scores are mechanical "
                "and the qualitative case has not been evaluated."
            ),
            "required_assumptions": [
                "Market estimate is approximately correct",
                "Company reaches and sustains profitability",
                "No incumbent response materially compresses margins",
            ],
            "assumption_count": 3,
            "evidence_gaps": ["Independent verification of the technology claims"],
            "confidence_in_judgment": 0.15,
        }

    def interpret(self, data: dict[str, Any], ctx: CandidateContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name, ok=True, payload=data,
            narrative=str(data.get("judgment", ""))[:3000],
        )
