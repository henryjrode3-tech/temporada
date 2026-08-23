"""Share prices and market capitalisation.

The SEC publishes fundamentals but not prices, so this is the one input the
platform cannot obtain for free and legally at the quality it needs. Rather
than invent a number, quietly scrape a site whose terms forbid it, or dress a
placeholder up as data, this module makes the gap explicit.

**The default provider returns nothing and says why.** Every downstream
consumer must handle a missing price, which means a report can be produced
without one - it simply omits valuation and says so, rather than fabricating a
market cap and computing a confident-looking asymmetry score on top of it.

That matters more here than in most systems: market capitalisation is the
denominator of every multiple the platform reports. A wrong price does not
degrade the output, it inverts it.

## Adding a real provider

Implement :class:`PriceProvider`, set ``ASYMMETRY_PRICE_PROVIDER``, and supply
the credential. Options that are legitimate with a key:

* **Nasdaq Data Link / Quandl** - end-of-day US equities, has historical.
* **Polygon.io** - free tier includes end-of-day.
* **Tiingo** - free tier for personal research.
* **Alpha Vantage** - free tier, heavily rate limited.
* **Your broker's API** - often the best data you already pay for.

For backtesting the requirement is stricter: the provider must return the
*close on a historical date*, not just the latest quote, or historical mode
silently prices 2015 decisions at today's price.
"""

from __future__ import annotations

import abc
import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import Any

log = logging.getLogger(__name__)


class PriceUnavailable(RuntimeError):
    """Raised when no price can be obtained. Never substituted with a guess."""


@dataclass(frozen=True)
class PriceQuote:
    """A share price, with the provenance needed to judge it."""

    ticker: str
    price: float
    as_of: date
    currency: str = "USD"
    source: str = "unknown"
    is_historical: bool = False
    stale_days: int = 0

    def market_cap(self, shares_outstanding: float) -> float:
        if shares_outstanding <= 0:
            raise ValueError("shares_outstanding must be positive")
        return self.price * shares_outstanding


class PriceProvider(abc.ABC):
    """Interface every price source implements."""

    name: str = "unnamed"
    requires_credentials: bool = True
    supports_historical: bool = False

    @abc.abstractmethod
    def get_price(self, ticker: str, on: date | None = None) -> PriceQuote:
        """Price for ``ticker``, on ``on`` if the provider supports history.

        Must raise :class:`PriceUnavailable` rather than return a placeholder.
        """

    @property
    def available(self) -> bool:
        """Whether this provider is actually usable right now."""
        return True

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "requires_credentials": self.requires_credentials,
            "supports_historical": self.supports_historical,
        }


class UnavailablePriceProvider(PriceProvider):
    """The default. Obtains no prices and explains what to configure.

    Deliberately not a mock. A mock that returned plausible prices would let
    the entire pipeline run and produce authoritative-looking valuations built
    on invented numbers, which is precisely the failure this platform exists to
    detect in other people's analysis.
    """

    name = "unavailable"
    requires_credentials = True
    supports_historical = False

    @property
    def available(self) -> bool:
        return False

    def get_price(self, ticker: str, on: date | None = None) -> PriceQuote:
        raise PriceUnavailable(
            f"No price provider is configured, so no market capitalisation can be "
            f"computed for {ticker.upper()}. Fundamentals from SEC EDGAR are "
            f"unaffected and the report will include everything except valuation.\n"
            f"To enable valuation, set ASYMMETRY_PRICE_PROVIDER and the matching "
            f"credential - see asymmetry/sources/prices.py for supported options."
        )


class ManualPriceProvider(PriceProvider):
    """Prices supplied explicitly by the operator.

    The honest way to get a valuation without a data subscription: the user
    states the price they observed. Recorded as a user-supplied input rather
    than as retrieved data, so the report can label it accordingly.
    """

    name = "manual"
    requires_credentials = False
    supports_historical = False

    def __init__(self, prices: dict[str, float] | None = None) -> None:
        self._prices = {k.upper(): v for k, v in (prices or {}).items()}

    def set(self, ticker: str, price: float) -> None:
        if price <= 0:
            raise ValueError("price must be positive")
        self._prices[ticker.upper()] = price

    @property
    def available(self) -> bool:
        return bool(self._prices)

    def get_price(self, ticker: str, on: date | None = None) -> PriceQuote:
        symbol = ticker.upper()
        if symbol not in self._prices:
            raise PriceUnavailable(
                f"No manual price supplied for {symbol}. Pass --price to provide one."
            )
        if on is not None:
            # Being explicit rather than silently pricing history at today's
            # value, which would make any backtest meaningless.
            raise PriceUnavailable(
                f"A manually supplied price cannot be used for the historical date "
                f"{on.isoformat()}. Historical valuation needs a provider with "
                f"price history."
            )
        return PriceQuote(
            ticker=symbol, price=self._prices[symbol], as_of=date.today(),
            source="manual (operator-supplied)", is_historical=False,
        )


class TiingoPriceProvider(PriceProvider):
    """Tiingo end-of-day prices. Requires ``TIINGO_API_KEY``.

    Implemented but unverified: no credential was available in the environment
    where this was written, so the request shape follows Tiingo's documentation
    and has not been exercised against the live API. Treated as unavailable
    until a key is present.
    """

    name = "tiingo"
    requires_credentials = True
    supports_historical = True

    BASE = "https://api.tiingo.com/tiingo/daily"

    def __init__(self, api_key: str | None = None, timeout: float = 20.0) -> None:
        self.api_key = api_key or os.environ.get("TIINGO_API_KEY", "")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def get_price(self, ticker: str, on: date | None = None) -> PriceQuote:
        if not self.available:
            raise PriceUnavailable(
                "TIINGO_API_KEY is not set. Get a free key at tiingo.com or choose "
                "another provider."
            )
        import httpx

        symbol = ticker.upper()
        headers = {"Content-Type": "application/json", "Authorization": f"Token {self.api_key}"}
        if on:
            url = f"{self.BASE}/{symbol}/prices"
            params: dict[str, Any] = {"startDate": on.isoformat(), "endDate": on.isoformat()}
        else:
            url = f"{self.BASE}/{symbol}/prices"
            params = {}

        try:
            with httpx.Client(timeout=self.timeout, headers=headers) as c:
                resp = c.get(url, params=params)
                resp.raise_for_status()
                rows = resp.json()
        except Exception as exc:
            raise PriceUnavailable(f"Tiingo request failed for {symbol}: {exc}") from exc

        if not rows:
            raise PriceUnavailable(
                f"Tiingo returned no price for {symbol}"
                + (f" on {on.isoformat()}" if on else "")
                + ". The date may be a non-trading day, or the ticker may be unsupported."
            )

        row = rows[-1]
        close = row.get("adjClose") or row.get("close")
        if close is None:
            raise PriceUnavailable(f"Tiingo response for {symbol} contained no close price.")

        quoted = date.fromisoformat(row["date"][:10])
        return PriceQuote(
            ticker=symbol, price=float(close), as_of=quoted,
            source="tiingo (end-of-day close)", is_historical=on is not None,
            stale_days=(date.today() - quoted).days,
        )


PROVIDERS: dict[str, type[PriceProvider]] = {
    "unavailable": UnavailablePriceProvider,
    "manual": ManualPriceProvider,
    "tiingo": TiingoPriceProvider,
}


def get_price_provider(name: str | None = None) -> PriceProvider:
    """Build the configured provider, defaulting to the one that refuses to guess."""
    key = (name or os.environ.get("ASYMMETRY_PRICE_PROVIDER") or "unavailable").lower()
    provider_cls = PROVIDERS.get(key)
    if provider_cls is None:
        log.warning(
            "Unknown price provider %r; falling back to 'unavailable'. Known: %s",
            key, ", ".join(sorted(PROVIDERS)),
        )
        return UnavailablePriceProvider()
    return provider_cls()
