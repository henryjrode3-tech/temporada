"""Pure financial mathematics.

No I/O, no LLM, no database. Every function here is deterministic and unit
tested, so the numbers the platform reports are trustworthy even when the
language models attached to it are not.

Vocabulary used throughout:

multiple      how many times the *current* value a future value represents.
              2.5 means "two and a half times today's value".
cagr          compound annual growth rate, expressed as a decimal (0.175 = 17.5%).
market cap    price x shares outstanding. The thing that actually has to grow.
per-share     market-cap growth adjusted for share count growth. What a holder
              of the asset actually experiences.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

# A market cap of zero is not a number we can divide by, and a "multiple"
# against a zero baseline is meaningless rather than infinite.
EPSILON = 1e-9


class FinMathError(ValueError):
    """Raised when an input is outside the domain where the maths is meaningful."""


# --------------------------------------------------------------------------
# Growth and multiples
# --------------------------------------------------------------------------
def multiple(future_value: float, current_value: float) -> float:
    """How many times the current value is the future value?

    >>> round(multiple(80_000_000_000, 500_000_000), 1)
    160.0
    """
    if current_value <= EPSILON:
        raise FinMathError("current_value must be positive to compute a multiple")
    if future_value < 0:
        raise FinMathError("future_value cannot be negative")
    return future_value / current_value


def cagr(multiple_: float, years: float) -> float:
    """Compound annual growth rate implied by a multiple over a period.

    The canonical checks from the specification:

    >>> round(cagr(5, 10) * 100, 1)
    17.5
    >>> round(cagr(10, 10) * 100, 1)
    25.9
    >>> round(cagr(50, 10) * 100, 1)
    47.9
    >>> round(cagr(100, 10) * 100, 1)
    58.5
    """
    if years <= 0:
        raise FinMathError("years must be positive")
    if multiple_ < 0:
        raise FinMathError("multiple cannot be negative")
    if multiple_ == 0:
        return -1.0  # total loss
    return multiple_ ** (1.0 / years) - 1.0


def multiple_from_cagr(rate: float, years: float) -> float:
    """Inverse of :func:`cagr` - the multiple implied by a growth rate."""
    if years <= 0:
        raise FinMathError("years must be positive")
    if rate <= -1.0:
        raise FinMathError("rate must be greater than -100%")
    return (1.0 + rate) ** years


def years_to_reach(multiple_: float, rate: float) -> float:
    """How long at ``rate`` to achieve ``multiple``?"""
    if multiple_ <= 0:
        raise FinMathError("multiple must be positive")
    if rate <= -1.0 or abs(rate) < EPSILON:
        raise FinMathError("rate must be non-zero and greater than -100%")
    return math.log(multiple_) / math.log(1.0 + rate)


# --------------------------------------------------------------------------
# Dilution
# --------------------------------------------------------------------------
def dilute(market_cap_multiple: float, dilution_cagr: float, years: float) -> float:
    """Convert a market-cap multiple into the multiple an existing holder gets.

    This is the correction that naive screens omit, and it matters most exactly
    where this system spends its time: cash-burning micro caps fund themselves
    by issuing stock, so the company can succeed spectacularly while the early
    holder does not.

    A 10x market cap with shares compounding 12% a year for a decade:

    >>> round(dilute(10, 0.12, 10), 2)
    3.22
    """
    if years < 0:
        raise FinMathError("years cannot be negative")
    if dilution_cagr <= -1.0:
        raise FinMathError("dilution_cagr must be greater than -100%")
    return market_cap_multiple / ((1.0 + dilution_cagr) ** years)


def implied_dilution_cagr(current_shares: float, future_shares: float, years: float) -> float:
    """Annual share-count growth implied by a projected share count."""
    if current_shares <= EPSILON or future_shares <= EPSILON:
        raise FinMathError("share counts must be positive")
    if years <= 0:
        raise FinMathError("years must be positive")
    return (future_shares / current_shares) ** (1.0 / years) - 1.0


# --------------------------------------------------------------------------
# Bottom-up valuation
# --------------------------------------------------------------------------
def revenue_from_market(total_market: float, market_share: float) -> float:
    """Revenue implied by capturing ``market_share`` of ``total_market``."""
    if total_market < 0:
        raise FinMathError("total_market cannot be negative")
    if not 0.0 <= market_share <= 1.0:
        raise FinMathError("market_share must be a fraction between 0 and 1")
    return total_market * market_share


def value_from_earnings(revenue: float, net_margin: float, exit_multiple: float) -> float:
    """Value a business on earnings: revenue -> margin -> earnings -> multiple.

    The specification's worked example: a $200B market, 10% share, 20% net
    margin, 20x earnings.

    >>> value_from_earnings(revenue_from_market(200e9, 0.10), 0.20, 20) / 1e9
    80.0
    """
    if exit_multiple < 0:
        raise FinMathError("exit_multiple cannot be negative")
    return max(0.0, revenue * net_margin * exit_multiple)


def value_from_revenue(revenue: float, ev_sales_multiple: float) -> float:
    """Value a business on sales, for pre-profit companies."""
    if ev_sales_multiple < 0:
        raise FinMathError("ev_sales_multiple cannot be negative")
    return max(0.0, revenue * ev_sales_multiple)


# --------------------------------------------------------------------------
# Reverse valuation - what does today's price already assume?
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ImpliedRequirements:
    """What must be true for today's valuation to be justified.

    The most important defensive calculation in the system. A great company
    whose price already embeds perfection is not an asymmetric opportunity.
    """

    required_revenue: float
    required_market_share: float | None
    total_market_assumed: float | None
    net_margin_assumed: float
    exit_multiple_assumed: float
    years: float
    verdict: str

    @property
    def share_is_implausible(self) -> bool:
        """Would today's price require an implausibly dominant position?"""
        return self.required_market_share is not None and self.required_market_share > 0.30


def implied_requirements(
    current_market_cap: float,
    *,
    total_market: float | None,
    net_margin: float,
    exit_multiple: float,
    years: float,
    required_return: float = 0.15,
) -> ImpliedRequirements:
    """Solve backwards: what revenue and market share does today's price assume?

    ``required_return`` is the annual return an investor demands. The future
    value must therefore be today's cap compounded at that rate; we then work
    back to the revenue - and hence the market share - needed to support it.
    """
    if current_market_cap <= EPSILON:
        raise FinMathError("current_market_cap must be positive")
    if net_margin <= 0 or exit_multiple <= 0:
        raise FinMathError("net_margin and exit_multiple must be positive")

    target_value = current_market_cap * multiple_from_cagr(required_return, years)
    required_revenue = target_value / (net_margin * exit_multiple)

    required_share: float | None = None
    if total_market and total_market > EPSILON:
        required_share = required_revenue / total_market

    if required_share is None:
        verdict = "No independent market estimate available; share requirement unknown."
    elif required_share > 1.0:
        verdict = (
            f"Today's price requires {required_share:.0%} of the entire estimated "
            f"market - more than the market contains. The price appears to embed "
            f"a larger market than we can independently justify."
        )
    elif required_share > 0.30:
        verdict = (
            f"Today's price already assumes {required_share:.0%} share of a "
            f"${total_market/1e9:.0f}B market within {years:.0f} years - near-dominance. "
            f"Limited room for upside surprise."
        )
    elif required_share > 0.10:
        verdict = (
            f"Today's price assumes {required_share:.0%} share of a "
            f"${total_market/1e9:.0f}B market - demanding but not absurd."
        )
    else:
        verdict = (
            f"Today's price only requires {required_share:.1%} share of a "
            f"${total_market/1e9:.0f}B market. Modest embedded expectations."
        )

    return ImpliedRequirements(
        required_revenue=required_revenue,
        required_market_share=required_share,
        total_market_assumed=total_market,
        net_margin_assumed=net_margin,
        exit_multiple_assumed=exit_multiple,
        years=years,
        verdict=verdict,
    )


# --------------------------------------------------------------------------
# Probability-weighted outcomes
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class WeightedOutcome:
    """A probability-weighted summary across scenarios.

    Explicitly a *model estimate*, never a prediction. ``expected_multiple`` is
    the mean of a deliberately wide distribution; the mean is not the likely
    outcome and must never be presented as one.
    """

    expected_value: float
    expected_multiple: float
    probability_of_loss: float
    probability_of_10x: float
    gain_side: float
    loss_side: float

    @property
    def payoff_ratio(self) -> float:
        """Expected gain per unit of expected loss."""
        return self.gain_side / max(self.loss_side, EPSILON)


def weighted_outcome(
    pairs: Sequence[tuple[float, float]],
    current_value: float,
) -> WeightedOutcome:
    """Combine ``(probability, future_value)`` pairs into a weighted summary.

    Probabilities must sum to 1.0; a distribution that does not is a modelling
    bug rather than something to silently normalise away.
    """
    if not pairs:
        raise FinMathError("at least one scenario is required")
    if current_value <= EPSILON:
        raise FinMathError("current_value must be positive")

    total_p = sum(p for p, _ in pairs)
    if abs(total_p - 1.0) > 1e-6:
        raise FinMathError(f"probabilities must sum to 1.0, got {total_p:.4f}")
    if any(p < 0 for p, _ in pairs):
        raise FinMathError("probabilities cannot be negative")

    expected_value = sum(p * v for p, v in pairs)
    gain_side = 0.0
    loss_side = 0.0
    p_loss = 0.0
    p_10x = 0.0

    for p, v in pairs:
        m = v / current_value
        if m > 1.0:
            gain_side += p * (m - 1.0)
        elif m < 1.0:
            loss_side += p * (1.0 - m)
            p_loss += p
        if m >= 10.0:
            p_10x += p

    return WeightedOutcome(
        expected_value=expected_value,
        expected_multiple=expected_value / current_value,
        probability_of_loss=p_loss,
        probability_of_10x=p_10x,
        gain_side=gain_side,
        loss_side=loss_side,
    )


#: Payoff ratio treated as the top of the scale. Calibrated empirically against
#: the candidate profiles the system actually produces: a ceiling of 50 caused
#: every small company to saturate at 100, which destroyed the score's ability
#: to rank the interesting cases against each other.
ASYMMETRY_SCALE_CAP = 200.0


def asymmetry_from_payoff(payoff_ratio: float, cap: float = ASYMMETRY_SCALE_CAP) -> float:
    """Map a payoff ratio onto 0-100.

    Log-compressed, because the difference between a 2:1 and a 6:1 payoff is
    decision-relevant while the difference between 150:1 and 300:1 is mostly
    modelling noise.

    This measures *lopsidedness*, not attractiveness: an even-money bet is not
    asymmetric and correctly scores low.

    >>> asymmetry_from_payoff(1.0) < asymmetry_from_payoff(10.0)
    True
    >>> 0 <= asymmetry_from_payoff(0.0) <= 100
    True
    """
    if payoff_ratio < 0:
        raise FinMathError("payoff_ratio cannot be negative")
    if cap <= 1.0:
        raise FinMathError("cap must exceed 1")
    score = 100.0 * math.log10(1.0 + payoff_ratio) / math.log10(1.0 + cap)
    return max(0.0, min(100.0, score))


# --------------------------------------------------------------------------
# Valuation ratios
# --------------------------------------------------------------------------
def enterprise_value(market_cap: float, debt: float, cash: float) -> float:
    """EV = market cap + debt - cash. May legitimately be negative."""
    return market_cap + debt - cash


def safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    """Ratio that returns ``None`` rather than lying when it is meaningless.

    A P/E on negative earnings is not a large number, it is an undefined one,
    and reporting it as a number is how screens end up recommending nonsense.
    """
    if numerator is None or denominator is None:
        return None
    if denominator <= EPSILON:
        return None
    return numerator / denominator


def rule_of_40(revenue_growth: float, fcf_margin: float) -> float:
    """Growth rate plus free-cash-flow margin, both as percentages."""
    return revenue_growth * 100.0 + fcf_margin * 100.0


def burn_runway_years(cash: float, annual_free_cash_flow: float) -> float | None:
    """Years of cash left at the current burn. ``None`` if not burning."""
    if annual_free_cash_flow >= 0:
        return None
    if cash <= 0:
        return 0.0
    return cash / abs(annual_free_cash_flow)
