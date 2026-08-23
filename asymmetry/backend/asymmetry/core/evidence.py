"""Evidence grading: what is a fact, and what is somebody's opinion.

A research report mixes four very different kinds of statement, and a reader
who cannot tell them apart cannot judge anything:

* **FACT** - filed with a regulator or published by a primary source. Citable.
* **DERIVED** - arithmetic on facts. As reliable as its inputs and the formula.
* **ESTIMATE** - a quantity approximated from partial data. Could be wrong.
* **ASSUMPTION** - an input chosen by the model. Not evidence at all.
* **AI_INTERPRETATION** - a language model's reading. Least reliable; may be
  fluent and wrong in the same sentence.

Everything the platform reports carries one of these grades. The rule that
makes it meaningful: **a claim may never be graded above its weakest input.**
A scenario built on an assumed market size is an assumption no matter how much
audited revenue also went into it. `Claim.derive` enforces that automatically,
because the alternative - remembering to downgrade by hand - fails silently and
in the flattering direction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import IntEnum
from typing import Any, Sequence


class Grade(IntEnum):
    """Ordered by reliability. Lower is stronger."""

    FACT = 1
    DERIVED = 2
    ESTIMATE = 3
    ASSUMPTION = 4
    AI_INTERPRETATION = 5

    @property
    def label(self) -> str:
        return {
            Grade.FACT: "FACT",
            Grade.DERIVED: "DERIVED",
            Grade.ESTIMATE: "ESTIMATE",
            Grade.ASSUMPTION: "ASSUMPTION",
            Grade.AI_INTERPRETATION: "AI INTERPRETATION",
        }[self]

    @property
    def description(self) -> str:
        return {
            Grade.FACT: "Reported in a regulatory filing or primary source.",
            Grade.DERIVED: "Computed from reported facts.",
            Grade.ESTIMATE: "Approximated from incomplete data.",
            Grade.ASSUMPTION: "An input chosen by the model, not evidence.",
            Grade.AI_INTERPRETATION: "A language model's reading. Unverified.",
        }[self]

    @property
    def is_evidence(self) -> bool:
        """Only facts and things derived from them support a conclusion."""
        return self <= Grade.DERIVED


@dataclass(frozen=True)
class Citation:
    """Where a fact came from, precisely enough to check it."""

    source: str                 # e.g. "SEC EDGAR 10-K"
    url: str | None = None
    accession: str | None = None
    filed: date | None = None
    period_end: date | None = None
    tag: str | None = None      # the XBRL concept, when applicable

    def render(self, *, compact: bool = False) -> str:
        parts = [self.source]
        if self.period_end:
            parts.append(
                f"FY{self.period_end.year}" if compact
                else f"period ending {self.period_end.isoformat()}"
            )
        if self.filed:
            parts.append(f"filed {self.filed.isoformat()}")
        # The accession identifies the exact filing but is long and adds nothing
        # on screen, so it is kept for the JSON output and dropped from compact
        # rendering rather than being truncated into something unusable.
        if self.accession and not compact:
            parts.append(self.accession)
        return " · ".join(parts)


@dataclass
class Claim:
    """One statement in a report, with its grade and provenance."""

    label: str
    value: Any
    grade: Grade
    unit: str | None = None
    citations: list[Citation] = field(default_factory=list)
    rationale: str = ""
    confidence: float | None = None      # 0-1, only meaningful below FACT
    as_of: date | None = None
    depends_on: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.grade is Grade.FACT and not self.citations:
            raise ValueError(
                f"{self.label!r} is graded FACT but carries no citation. "
                f"An uncited fact is an assumption wearing a better name."
            )

    @classmethod
    def derive(
        cls,
        label: str,
        value: Any,
        inputs: Sequence["Claim"],
        *,
        rationale: str = "",
        unit: str | None = None,
        floor: Grade = Grade.DERIVED,
    ) -> "Claim":
        """Build a claim from others, inheriting the weakest input's grade.

        This is the mechanism that stops a well-sourced-looking number from
        resting on an invented one. The result can never be stronger than
        ``floor`` or than any input.
        """
        weakest = max([floor, *(i.grade for i in inputs)]) if inputs else floor
        confidences = [i.confidence for i in inputs if i.confidence is not None]
        return cls(
            label=label, value=value, grade=Grade(weakest), unit=unit,
            citations=[c for i in inputs for c in i.citations],
            rationale=rationale,
            confidence=min(confidences) if confidences else None,
            depends_on=[i.label for i in inputs],
        )

    @property
    def is_evidence(self) -> bool:
        return self.grade.is_evidence

    def render_value(self) -> str:
        if isinstance(self.value, float):
            if self.unit == "USD":
                return _money(self.value)
            if self.unit == "%":
                return f"{self.value * 100:.1f}%"
            if self.unit == "x":
                return f"{self.value:.2f}x"
            return f"{self.value:,.2f}"
        return str(self.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "rendered": self.render_value(),
            "grade": self.grade.label,
            "grade_rank": int(self.grade),
            "is_evidence": self.is_evidence,
            "unit": self.unit,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "depends_on": self.depends_on,
            "citations": [
                {"source": c.source, "url": c.url, "accession": c.accession,
                 "filed": c.filed.isoformat() if c.filed else None,
                 "period_end": c.period_end.isoformat() if c.period_end else None,
                 "tag": c.tag, "rendered": c.render()}
                for c in self.citations
            ],
        }


def _money(v: float) -> str:
    sign = "-" if v < 0 else ""
    v = abs(v)
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if v >= div:
            return f"{sign}${v/div:,.2f}{unit}"
    return f"{sign}${v:,.0f}"


@dataclass
class EvidenceLedger:
    """Every claim in a report, with a summary of how well-founded it is."""

    claims: list[Claim] = field(default_factory=list)

    def add(self, claim: Claim) -> Claim:
        self.claims.append(claim)
        return claim

    def get(self, label: str) -> Claim | None:
        return next((c for c in self.claims if c.label == label), None)

    def by_grade(self, grade: Grade) -> list[Claim]:
        return [c for c in self.claims if c.grade is grade]

    def counts(self) -> dict[str, int]:
        return {g.label: len(self.by_grade(g)) for g in Grade}

    @property
    def evidence_ratio(self) -> float:
        """Share of claims that are facts or derived from them."""
        if not self.claims:
            return 0.0
        return sum(1 for c in self.claims if c.is_evidence) / len(self.claims)

    @property
    def cited_sources(self) -> list[str]:
        seen: dict[str, None] = {}
        for claim in self.claims:
            for citation in claim.citations:
                seen.setdefault(citation.render(), None)
        return list(seen)

    def integrity_warnings(self) -> list[str]:
        """Structural problems a reader should know about before trusting this."""
        warnings: list[str] = []
        counts = self.counts()

        if self.evidence_ratio < 0.30 and self.claims:
            warnings.append(
                f"Only {self.evidence_ratio:.0%} of claims are facts or derived from "
                f"facts. This report is mostly assumption."
            )
        if counts.get("ASSUMPTION", 0) > counts.get("FACT", 0) and self.claims:
            warnings.append(
                f"Assumptions ({counts['ASSUMPTION']}) outnumber facts "
                f"({counts.get('FACT', 0)})."
            )
        if counts.get("AI INTERPRETATION", 0) and not counts.get("FACT", 0):
            warnings.append(
                "The report contains AI interpretation but no verified facts."
            )
        uncited = [
            c.label for c in self.claims
            if c.grade <= Grade.DERIVED and not c.citations
        ]
        if uncited:
            warnings.append(
                f"Claims graded as evidence but lacking citations: {', '.join(uncited[:5])}."
            )
        return warnings

    def to_dict(self) -> dict[str, Any]:
        return {
            "claims": [c.to_dict() for c in self.claims],
            "counts": self.counts(),
            "evidence_ratio": round(self.evidence_ratio, 3),
            "sources": self.cited_sources,
            "warnings": self.integrity_warnings(),
        }


def sec_citation(fact: Any) -> Citation:
    """Build a citation from an :class:`~asymmetry.sources.edgar.XBRLFact`."""
    return Citation(
        source=f"SEC EDGAR {fact.form}",
        url=fact.source_url,
        accession=fact.accession,
        filed=fact.filed,
        period_end=fact.period_end,
        tag=fact.tag,
    )


def fact_claim(label: str, fact: Any, *, unit: str = "USD", rationale: str = "") -> Claim:
    """A FACT claim straight from a filing."""
    return Claim(
        label=label, value=fact.value, grade=Grade.FACT, unit=unit,
        citations=[sec_citation(fact)], as_of=fact.period_end,
        rationale=rationale or f"As reported in the {fact.form} for the period "
                               f"ending {fact.period_end.isoformat()}.",
    )
