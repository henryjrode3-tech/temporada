"""The no-hype rule (section 40).

Words are not evidence. This module measures promotional language density and
weighs it against *measurable* counter-evidence: revenue, customers, patents,
citations, shipped product, government contracts.

The asymmetry the system hunts for is frequently found in companies that
describe themselves boringly, and almost never in companies that describe
themselves as revolutionary. A high hype score with no substantiation is one of
the strongest negative signals available.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Promotional vocabulary. Weighted: some phrases are merely fashionable,
#: others are near-reliable markers of a company selling a story.
HYPE_TERMS: dict[str, float] = {
    # Generic promotional superlatives
    "revolutionary": 3.0,
    "game-changing": 3.0,
    "game changer": 3.0,
    "disruptive": 2.0,
    "disrupting": 2.0,
    "next generation": 1.5,
    "next-generation": 1.5,
    "cutting edge": 2.0,
    "cutting-edge": 2.0,
    "state of the art": 1.5,
    "world-class": 2.0,
    "best-in-class": 2.0,
    "paradigm shift": 3.0,
    "unprecedented": 2.0,
    "groundbreaking": 2.5,
    "breakthrough": 1.5,
    "transformative": 2.0,
    "visionary": 2.5,
    "unparalleled": 2.5,
    "industry-leading": 2.0,
    "market-leading": 1.5,
    # Buzzword stacking - individually fine, damning in combination
    "ai-powered": 2.0,
    "ai-driven": 2.0,
    "blockchain": 1.5,
    "quantum-powered": 3.0,
    "synergy": 2.0,
    "synergies": 1.5,
    "ecosystem play": 2.0,
    "web3": 2.0,
    "metaverse": 2.5,
    # Promissory language - the future tense used as a substitute for results
    "poised to": 2.5,
    "set to revolutionize": 3.0,
    "will transform": 2.5,
    "positioned to dominate": 3.0,
    "massive opportunity": 2.0,
    "explosive growth": 2.5,
    "exponential growth": 2.0,
    "limitless": 3.0,
    "unlimited potential": 3.0,
    "sky is the limit": 3.0,
    "guaranteed": 3.0,
    "can't lose": 3.0,
    "no competition": 3.0,
    "first-ever": 1.5,
    "only company": 2.0,
}

#: Evidence of the kind that actually substantiates a claim. Presence of these
#: patterns partially forgives promotional language.
EVIDENCE_PATTERNS: dict[str, str] = {
    "revenue_figure": r"\$\s?\d[\d,.]*\s?(million|billion|m\b|bn\b|k\b)",
    "growth_figure": r"\d{1,4}(\.\d+)?\s?%\s?(growth|increase|yoy|year[- ]over[- ]year|cagr)",
    "named_customer": r"\b(customer|client|partner)s?\s+(include|includes|including)\b",
    "patent": r"\b(patent|patents|patented|uspto|patent[- ]pending)\b",
    "peer_review": r"\b(peer[- ]reviewed|published in|nature|science|ieee|arxiv|doi)\b",
    "contract": r"\b(contract|award|awarded|procurement|purchase order|loi|letter of intent)\b",
    "shipped": r"\b(shipped|shipping|deployed|in production|commercially available|ga\b)\b",
    "unit_metric": r"\b\d[\d,]*\s+(units|customers|users|installations|sites|megawatts|mw|gwh)\b",
    "regulatory": r"\b(fda|approval|cleared|certification|certified|ul listed|nrc)\b",
    "financial_filing": r"\b(10-k|10-q|8-k|s-1|annual report|sec filing)\b",
}


@dataclass
class HypeAnalysis:
    """Promotional language weighed against measurable substantiation."""

    hype_score: float                       # 0-100, higher is worse
    raw_hype_weight: float
    word_count: int
    terms_found: dict[str, int] = field(default_factory=dict)
    evidence_found: dict[str, int] = field(default_factory=dict)
    substantiation_ratio: float = 0.0       # evidence markers per hype term
    verdict: str = ""

    @property
    def is_unsubstantiated_hype(self) -> bool:
        """Loud claims with nothing measurable behind them."""
        return self.hype_score >= 50 and self.substantiation_ratio < 0.5


def analyse_hype(text: str) -> HypeAnalysis:
    """Score promotional language density, discounted by hard evidence.

    Normalised per 1,000 words so a long filing is not penalised merely for
    being long.
    """
    if not text or not text.strip():
        return HypeAnalysis(0.0, 0.0, 0, verdict="No text supplied.")

    lowered = text.lower()
    word_count = len(re.findall(r"\b\w+\b", lowered))
    if word_count == 0:
        return HypeAnalysis(0.0, 0.0, 0, verdict="No words to analyse.")

    terms_found: dict[str, int] = {}
    raw_weight = 0.0
    for term, weight in HYPE_TERMS.items():
        # Word-boundary match so "aim" does not match inside "claim".
        hits = len(re.findall(rf"(?<!\w){re.escape(term)}(?!\w)", lowered))
        if hits:
            terms_found[term] = hits
            raw_weight += hits * weight

    evidence_found: dict[str, int] = {}
    evidence_total = 0
    for name, pattern in EVIDENCE_PATTERNS.items():
        hits = len(re.findall(pattern, lowered))
        if hits:
            evidence_found[name] = hits
            evidence_total += hits

    per_1k = raw_weight * 1000.0 / word_count
    # 25 weighted hype points per 1,000 words is treated as saturation.
    base_score = min(100.0, per_1k * 4.0)

    hype_term_count = sum(terms_found.values())
    substantiation = evidence_total / hype_term_count if hype_term_count else float(evidence_total)

    # Evidence forgives up to 60% of the penalty, never all of it: a company
    # can have real revenue and still describe itself dishonestly.
    forgiveness = min(0.6, substantiation * 0.2)
    score = base_score * (1.0 - forgiveness)

    if score >= 60:
        verdict = "Heavily promotional language with little measurable substantiation."
    elif score >= 35:
        verdict = "Noticeably promotional. Treat claims as unproven until verified."
    elif score >= 15:
        verdict = "Some promotional language, partially substantiated."
    else:
        verdict = "Restrained, largely factual language."

    if evidence_total and score < 35:
        verdict += f" {evidence_total} evidence marker(s) present."

    return HypeAnalysis(
        hype_score=round(score, 2),
        raw_hype_weight=raw_weight,
        word_count=word_count,
        terms_found=terms_found,
        evidence_found=evidence_found,
        substantiation_ratio=round(substantiation, 3),
        verdict=verdict,
    )
