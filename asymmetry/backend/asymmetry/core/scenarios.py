"""Scenario engine: bear / base / bull / extreme bull.

Builds each scenario bottom-up from explicit, structured assumptions so that
every number can be traced to a stated belief and argued with. Assumptions are
data, never prose, which is what lets the contrarian agent attack them and lets
the thesis tracker diff them over time.

Nothing here predicts anything. It answers a conditional question: *if* these
assumptions held, what would the asset be worth?
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any

from .finmath import (
    FinMathError,
    asymmetry_from_payoff,
    cagr,
    dilute,
    multiple,
    revenue_from_market,
    value_from_earnings,
    value_from_revenue,
    weighted_outcome,
)


class ScenarioName(str, Enum):
    BEAR = "bear"
    BASE = "base"
    BULL = "bull"
    EXTREME_BULL = "extreme_bull"


#: Starting prior only. Section 51 replaces these with empirically calibrated
#: values once enough resolved predictions exist. Deliberately pessimistic:
#: most obscure small companies do not become important, and a scenario model
#: that forgets this manufactures optimism.
DEFAULT_PROBABILITIES: dict[ScenarioName, float] = {
    ScenarioName.BEAR: 0.40,
    ScenarioName.BASE: 0.35,
    ScenarioName.BULL: 0.20,
    ScenarioName.EXTREME_BULL: 0.05,
}


#: Maximum revenue CAGR each scenario may assume, sustained over the whole
#: horizon. These are plausibility ceilings, not targets.
#:
#: Sustaining 60% annual revenue growth for a decade is a genuinely rare
#: historical event; sustaining 190% is not a scenario, it is a fantasy. Without
#: this constraint a bottom-up model will happily assert that a company with $5M
#: of revenue captures 20% of a $160B market, because the arithmetic never
#: objects. Clamping here is what keeps the bull cases inside the space of
#: things that have actually happened to real companies.
MAX_REVENUE_CAGR: dict[ScenarioName, float] = {
    ScenarioName.BEAR: 0.15,
    ScenarioName.BASE: 0.35,
    ScenarioName.BULL: 0.55,
    ScenarioName.EXTREME_BULL: 0.75,
}

#: Maximum share of its market a single company may be assumed to hold.
#:
#: A growth-rate ceiling alone does not bound absolute size: a company already
#: earning billions can clear the CAGR test while implicitly being assigned most
#: of its industry. Sustained share above roughly 40% attracts competition,
#: customer diversification and antitrust attention, so these ceilings encode
#: the constraint that the growth-rate test misses.
MAX_MARKET_SHARE: dict[ScenarioName, float] = {
    ScenarioName.BEAR: 0.05,
    ScenarioName.BASE: 0.15,
    ScenarioName.BULL: 0.30,
    ScenarioName.EXTREME_BULL: 0.40,
}


@dataclass
class ScenarioAssumptions:
    """The full set of beliefs behind a single scenario.

    Every field is something a human can disagree with, which is the point.
    """

    name: ScenarioName
    probability: float
    total_market: float             # the addressable market in that future
    market_share: float             # fraction of it captured, 0-1
    net_margin: float               # net income / revenue
    exit_multiple: float            # P/E at exit (earnings path)
    ev_sales_multiple: float | None = None   # used when pre-profit
    dilution_cagr: float = 0.0      # annual share-count growth
    narrative: str = ""             # one sentence a human can argue with
    drivers: list[str] = None       # what must happen for this to occur
    current_revenue: float | None = None     # anchor for the plausibility check

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise FinMathError(f"probability out of range: {self.probability}")
        if not 0.0 <= self.market_share <= 1.0:
            raise FinMathError(f"market_share must be 0-1, got {self.market_share}")
        if self.total_market < 0:
            raise FinMathError("total_market cannot be negative")
        if self.drivers is None:
            self.drivers = []


@dataclass
class ScenarioResult:
    """A computed scenario. Contains the inputs so it is self-explaining."""

    name: ScenarioName
    probability: float
    revenue: float
    earnings: float
    future_market_cap: float
    market_cap_multiple: float
    per_share_multiple: float
    cagr: float
    per_share_cagr: float
    valuation_path: str             # "earnings" or "revenue"
    assumptions: dict[str, Any]
    narrative: str
    drivers: list[str]
    implied_revenue_cagr: float | None = None
    was_clamped: bool = False
    clamp_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["name"] = self.name.value
        return d


def build_scenario(
    assumptions: ScenarioAssumptions,
    current_market_cap: float,
    years: float,
) -> ScenarioResult:
    """Compute one scenario from its assumptions.

    Chooses the earnings path when the scenario is profitable, and falls back
    to a sales multiple when it is not - valuing an unprofitable outcome on a
    P/E is meaningless.
    """
    if current_market_cap <= 0:
        raise FinMathError("current_market_cap must be positive")
    if years <= 0:
        raise FinMathError("years must be positive")

    revenue = revenue_from_market(assumptions.total_market, assumptions.market_share)

    # Plausibility clamp. If the implied revenue growth exceeds what companies
    # have historically sustained, cap the revenue and record why. The clamp is
    # reported rather than applied silently, so the reader can see that the
    # bull case was reined in and judge whether the ceiling is fair.
    implied_rev_cagr: float | None = None
    was_clamped = False
    clamp_reason = ""
    anchor = assumptions.current_revenue

    if anchor is not None and anchor > 0 and revenue > 0:
        implied_rev_cagr = (revenue / anchor) ** (1.0 / years) - 1.0
        ceiling = MAX_REVENUE_CAGR.get(assumptions.name, 0.60)
        if implied_rev_cagr > ceiling:
            capped_revenue = anchor * ((1.0 + ceiling) ** years)
            clamp_reason = (
                f"Implied revenue growth of {implied_rev_cagr*100:.0f}%/yr for "
                f"{years:.0f} years exceeds the {ceiling*100:.0f}% ceiling for a "
                f"{assumptions.name.value.replace('_', ' ')} case. Revenue capped at "
                f"${capped_revenue/1e6:,.0f}M "
                f"({capped_revenue/assumptions.total_market:.2%} share) instead of "
                f"${revenue/1e6:,.0f}M."
            )
            revenue = capped_revenue
            implied_rev_cagr = ceiling
            was_clamped = True

    # Second, independent ceiling: absolute share of the market. The growth-rate
    # test above cannot catch this, because a company already earning billions
    # can satisfy it while being handed most of its industry.
    share_ceiling = MAX_MARKET_SHARE.get(assumptions.name, 0.40)
    if assumptions.total_market > 0:
        effective_share = revenue / assumptions.total_market
        if effective_share > share_ceiling:
            capped_revenue = assumptions.total_market * share_ceiling
            extra = (
                f"Implied share of {effective_share:.0%} exceeds the "
                f"{share_ceiling:.0%} ceiling for a "
                f"{assumptions.name.value.replace('_', ' ')} case; revenue capped at "
                f"${capped_revenue/1e6:,.0f}M."
            )
            clamp_reason = f"{clamp_reason} {extra}".strip()
            revenue = capped_revenue
            was_clamped = True
            if anchor and anchor > 0:
                implied_rev_cagr = (revenue / anchor) ** (1.0 / years) - 1.0

    earnings = revenue * assumptions.net_margin

    if assumptions.net_margin > 0 and assumptions.exit_multiple > 0:
        future_cap = value_from_earnings(
            revenue, assumptions.net_margin, assumptions.exit_multiple
        )
        path = "earnings"
    else:
        # Unprofitable outcome: a sales multiple is the only honest option.
        ev_sales = assumptions.ev_sales_multiple or 1.0
        future_cap = value_from_revenue(revenue, ev_sales)
        path = "revenue"

    cap_multiple = multiple(future_cap, current_market_cap)
    per_share = dilute(cap_multiple, assumptions.dilution_cagr, years)

    return ScenarioResult(
        name=assumptions.name,
        probability=assumptions.probability,
        revenue=revenue,
        earnings=earnings,
        future_market_cap=future_cap,
        market_cap_multiple=cap_multiple,
        per_share_multiple=per_share,
        cagr=cagr(cap_multiple, years),
        per_share_cagr=cagr(per_share, years) if per_share > 0 else -1.0,
        valuation_path=path,
        assumptions={
            "total_market": assumptions.total_market,
            "market_share": assumptions.market_share,
            "effective_market_share": (
                revenue / assumptions.total_market
                if assumptions.total_market > 0 else None
            ),
            "net_margin": assumptions.net_margin,
            "exit_multiple": assumptions.exit_multiple,
            "ev_sales_multiple": assumptions.ev_sales_multiple,
            "dilution_cagr": assumptions.dilution_cagr,
            "current_revenue": assumptions.current_revenue,
            "years": years,
        },
        narrative=assumptions.narrative,
        drivers=list(assumptions.drivers),
        implied_revenue_cagr=implied_rev_cagr,
        was_clamped=was_clamped,
        clamp_reason=clamp_reason,
    )


@dataclass
class ScenarioSet:
    """All four scenarios plus their probability-weighted summary."""

    scenarios: list[ScenarioResult]
    current_market_cap: float
    years: float
    expected_value: float
    expected_multiple: float
    probability_of_loss: float
    probability_of_10x: float
    payoff_ratio: float
    asymmetry_score: float
    median_multiple: float = 0.0        # the 50th-percentile outcome
    tail_contribution: float = 0.0      # share of expected value from the top branch
    clamped_scenarios: list[str] = field(default_factory=list)
    disclaimer: str = (
        "Model estimate under stated assumptions. Not a prediction, not advice. "
        "The expected value is the mean of a deliberately wide distribution and "
        "is not the likely outcome."
    )

    @property
    def is_tail_dominated(self) -> bool:
        """Does the expected value rest almost entirely on the least likely branch?

        When true, the headline expected value is close to meaningless as a
        summary and the median outcome should be read instead.
        """
        return self.tail_contribution > 0.5

    def by_name(self, name: ScenarioName) -> ScenarioResult:
        for s in self.scenarios:
            if s.name == name:
                return s
        raise KeyError(name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarios": [s.to_dict() for s in self.scenarios],
            "current_market_cap": self.current_market_cap,
            "years": self.years,
            "expected_value": self.expected_value,
            "expected_multiple": self.expected_multiple,
            "probability_of_loss": self.probability_of_loss,
            "probability_of_10x": self.probability_of_10x,
            "payoff_ratio": self.payoff_ratio,
            "asymmetry_score": self.asymmetry_score,
            "median_multiple": self.median_multiple,
            "tail_contribution": self.tail_contribution,
            "is_tail_dominated": self.is_tail_dominated,
            "clamped_scenarios": self.clamped_scenarios,
            "disclaimer": self.disclaimer,
        }


def build_scenario_set(
    assumptions: list[ScenarioAssumptions],
    current_market_cap: float,
    years: float = 10.0,
) -> ScenarioSet:
    """Compute all scenarios and the weighted asymmetry summary.

    Probabilities must sum to 1.0. Asymmetry is computed on *per-share*
    multiples, because dilution is a real cost to the holder and excluding it
    systematically flatters cash-burning companies.
    """
    if not assumptions:
        raise FinMathError("at least one scenario is required")

    results = [build_scenario(a, current_market_cap, years) for a in assumptions]

    # Weight on per-share outcomes: what the holder actually receives.
    pairs = [
        (r.probability, r.per_share_multiple * current_market_cap) for r in results
    ]
    outcome = weighted_outcome(pairs, current_market_cap)

    # Median outcome: walk the scenarios worst-to-best accumulating probability
    # until the halfway point. Far more representative than the mean whenever
    # the distribution is power-law shaped, which here it almost always is.
    ordered = sorted(results, key=lambda r: r.per_share_multiple)
    cumulative = 0.0
    median_multiple = ordered[-1].per_share_multiple
    for r in ordered:
        cumulative += r.probability
        if cumulative >= 0.5:
            median_multiple = r.per_share_multiple
            break

    # How much of the expected value comes from the single best branch? A high
    # figure means the headline number is one improbable scenario wearing a
    # statistic as a disguise.
    best = max(results, key=lambda r: r.per_share_multiple)
    best_contribution = best.probability * best.per_share_multiple * current_market_cap
    tail_contribution = (
        best_contribution / outcome.expected_value
        if outcome.expected_value > 0 else 0.0
    )

    return ScenarioSet(
        median_multiple=median_multiple,
        tail_contribution=tail_contribution,
        clamped_scenarios=[r.name.value for r in results if r.was_clamped],
        scenarios=results,
        current_market_cap=current_market_cap,
        years=years,
        expected_value=outcome.expected_value,
        expected_multiple=outcome.expected_multiple,
        probability_of_loss=outcome.probability_of_loss,
        probability_of_10x=outcome.probability_of_10x,
        payoff_ratio=outcome.payoff_ratio,
        asymmetry_score=asymmetry_from_payoff(outcome.payoff_ratio),
    )


# --------------------------------------------------------------------------
# "Could this be a $100B company?" (section 20)
# --------------------------------------------------------------------------
MILESTONES: list[tuple[str, float]] = [
    ("$10B", 10e9),
    ("$50B", 50e9),
    ("$100B", 100e9),
    ("$500B", 500e9),
    ("$1T", 1_000e9),
]


@dataclass
class MilestoneAnalysis:
    """Whether a given size is reachable, and precisely what it would take."""

    label: str
    target_market_cap: float
    reachable: bool
    required_revenue: float
    required_market_share: float | None
    multiple_from_here: float
    implied_cagr: float
    commentary: str


def milestone_ladder(
    current_market_cap: float,
    total_market: float | None,
    net_margin: float,
    exit_multiple: float,
    years: float = 10.0,
) -> list[MilestoneAnalysis]:
    """For each size milestone, state what would have to be true to reach it.

    Marks a milestone unreachable when it would require more than 100% of the
    independently estimated market - the honest answer for most candidates at
    the top of the ladder.
    """
    if current_market_cap <= 0:
        raise FinMathError("current_market_cap must be positive")

    out: list[MilestoneAnalysis] = []
    for label, target in MILESTONES:
        if net_margin <= 0 or exit_multiple <= 0:
            continue
        required_revenue = target / (net_margin * exit_multiple)
        share = (
            required_revenue / total_market
            if total_market and total_market > 0
            else None
        )
        mult = target / current_market_cap
        reachable = share is None or share <= 1.0

        if share is None:
            commentary = f"Needs ${required_revenue/1e9:.1f}B revenue. No independent market estimate to test share against."
        elif share > 1.0:
            commentary = (
                f"Would require {share:.0%} of the estimated ${total_market/1e9:.0f}B "
                f"market - larger than the market. Not credible without the market "
                f"itself growing well beyond our estimate."
            )
        else:
            commentary = (
                f"Needs ${required_revenue/1e9:.1f}B revenue = {share:.1%} share of a "
                f"${total_market/1e9:.0f}B market, a {mult:.1f}x from here "
                f"({cagr(mult, years)*100:.1f}% CAGR over {years:.0f} years)."
            )

        out.append(
            MilestoneAnalysis(
                label=label,
                target_market_cap=target,
                reachable=reachable,
                required_revenue=required_revenue,
                required_market_share=share,
                multiple_from_here=mult,
                implied_cagr=cagr(mult, years),
                commentary=commentary,
            )
        )
    return out


# --------------------------------------------------------------------------
# Default scenario construction
# --------------------------------------------------------------------------
def default_scenarios(
    total_market_base: float,
    *,
    current_revenue: float | None = None,
    bear_share: float = 0.001,
    base_share: float = 0.02,
    bull_share: float = 0.08,
    extreme_share: float = 0.20,
    net_margin: float = 0.15,
    exit_multiple: float = 20.0,
    dilution_cagr: float = 0.05,
    market_growth_in_bull: float = 2.0,
    market_growth_in_extreme: float = 4.0,
) -> list[ScenarioAssumptions]:
    """A reasonable starting set of scenarios for a speculative candidate.

    The bull cases expand the *market* as well as the share, since the whole
    premise of an asymmetric bet is usually that the market itself is about to
    become far larger than it is today - not merely that one firm wins a fixed
    pie. The bear case is a near-total loss, which for obscure companies is the
    single most likely individual outcome.

    ``current_revenue`` anchors the plausibility clamp. Supplying it is strongly
    recommended: without an anchor the share assumptions are unconstrained and
    the bull cases drift into arithmetic that no company has ever achieved.
    """
    return [
        ScenarioAssumptions(
            name=ScenarioName.BEAR,
            probability=DEFAULT_PROBABILITIES[ScenarioName.BEAR],
            total_market=total_market_base,
            market_share=bear_share,
            net_margin=max(0.0, net_margin * 0.2),
            exit_multiple=exit_multiple * 0.5,
            ev_sales_multiple=0.5,
            dilution_cagr=dilution_cagr * 2.5,  # failure is funded by issuing stock
            current_revenue=current_revenue,
            narrative="Adoption stalls; the company remains subscale and dilutes to survive.",
            drivers=["Customer adoption fails to materialise", "Repeated dilutive financing"],
        ),
        ScenarioAssumptions(
            name=ScenarioName.BASE,
            probability=DEFAULT_PROBABILITIES[ScenarioName.BASE],
            total_market=total_market_base,
            market_share=base_share,
            net_margin=net_margin,
            exit_multiple=exit_multiple,
            dilution_cagr=dilution_cagr,
            current_revenue=current_revenue,
            narrative="Becomes a real but modest participant in the market as it exists today.",
            drivers=["Steady revenue growth", "Margins reach industry norms"],
        ),
        ScenarioAssumptions(
            name=ScenarioName.BULL,
            probability=DEFAULT_PROBABILITIES[ScenarioName.BULL],
            total_market=total_market_base * market_growth_in_bull,
            market_share=bull_share,
            net_margin=net_margin * 1.2,
            exit_multiple=exit_multiple * 1.25,
            dilution_cagr=dilution_cagr * 0.6,
            current_revenue=current_revenue,
            narrative="Category leadership as the market itself expands substantially.",
            drivers=[
                "Market expands beyond today's size",
                "Company establishes durable technical lead",
                "Operating leverage lifts margins",
            ],
        ),
        ScenarioAssumptions(
            name=ScenarioName.EXTREME_BULL,
            probability=DEFAULT_PROBABILITIES[ScenarioName.EXTREME_BULL],
            total_market=total_market_base * market_growth_in_extreme,
            market_share=extreme_share,
            net_margin=net_margin * 1.5,
            exit_multiple=exit_multiple * 1.5,
            dilution_cagr=0.0,
            current_revenue=current_revenue,
            narrative="Becomes core infrastructure for an industry far larger than today's.",
            drivers=[
                "Technology becomes an industry standard",
                "Network or manufacturing effects compound",
                "Company self-funds from free cash flow",
            ],
        ),
    ]
