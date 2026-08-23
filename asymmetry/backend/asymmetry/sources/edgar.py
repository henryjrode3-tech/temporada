"""SEC EDGAR XBRL fundamentals - real, free, point-in-time correct.

This is the module that turns the platform from a demo into a research system.
Everything it returns is a fact the SEC holds, traceable to a specific filing.

## Why this source and not a convenient financial API

Every XBRL datapoint the SEC publishes carries **two** dates:

* ``end``   - the period the number describes
* ``filed`` - the date that number first became public

Almost every other free source gives only the first. That difference is the
whole ballgame for backtesting. A company's FY2020 revenue as *restated* in
2022 carries ``filed=2022``, so a query as of 2021 correctly cannot see it -
it sees the original figure, which is what an investor actually had. Filtering
on ``end`` instead would quietly feed the system corrected numbers nobody had
at the time and produce a backtest that flatters itself.

So the rule here is absolute: **the as-of filter reads ``filed``, never
``end``.**

## What this module does not provide

Share price, and therefore market capitalisation. The SEC does not publish
prices. Shares outstanding *is* available and is taken from here; price comes
from a separate provider that must be configured (see ``sources/prices.py``).
No price is ever invented.

## Terms of use

The SEC requires a descriptive User-Agent with real contact details and asks
for no more than 10 requests/second. Both are honoured. These are public
endpoints intended for exactly this use.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Sequence

import httpx

from ..config import get_settings

log = logging.getLogger(__name__)

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

#: The SEC permits 10 requests/second. Staying well under it costs nothing and
#: being blocked would remove the platform's only authoritative data source.
MIN_REQUEST_INTERVAL = 0.15


class EdgarError(RuntimeError):
    """Raised when EDGAR cannot answer, distinct from 'no such fact'."""


class TickerNotFound(EdgarError):
    pass


# --------------------------------------------------------------------------
# Concept mapping
# --------------------------------------------------------------------------
#: US-GAAP concepts, in priority order. Filers legitimately tag the same idea
#: differently - a software company reports revenue under
#: RevenueFromContractWithCustomer..., an older filer under SalesRevenueNet -
#: so each metric lists its acceptable tags most-specific first.
CONCEPTS: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
    ],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "short_term_investments": ["ShortTermInvestments", "MarketableSecuritiesCurrent"],
    "total_debt": ["DebtLongtermAndShorttermCombinedAmount"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "short_term_debt": ["LongTermDebtCurrent", "DebtCurrent"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity"],
    "shares_outstanding": [
        "CommonStockSharesOutstanding",
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
    ],
    "stock_based_comp": ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
    "rd_expense": ["ResearchAndDevelopmentExpense"],
}

#: Only these forms are treated as authoritative financial statements.
STATEMENT_FORMS = {"10-K", "10-Q", "20-F", "40-F", "10-K/A", "10-Q/A"}


@dataclass(frozen=True)
class XBRLFact:
    """One reported number, with everything needed to cite and date it."""

    concept: str            # our normalised name, e.g. "revenue"
    tag: str                # the us-gaap tag it came from
    value: float
    unit: str
    period_end: date
    filed: date             # the only date the as-of filter may use
    form: str
    accession: str
    period_start: date | None = None
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    frame: str | None = None

    @property
    def duration_days(self) -> int | None:
        """Length of the period this fact covers. ``None`` for balance sheet
        items, which are instants rather than spans."""
        if self.period_start is None:
            return None
        return (self.period_end - self.period_start).days

    @property
    def is_instant(self) -> bool:
        """Balance-sheet items (cash, debt, share count) have no duration."""
        return self.period_start is None

    @property
    def is_annual(self) -> bool:
        """Whether this covers a full year.

        Judged on the period's actual length, never on the form type. A 10-K
        contains both the full-year figures *and* the fourth-quarter ones, so
        trusting the form label silently reports one quarter of revenue as if
        it were the year - which understated Apple's FY2020 revenue as $64.7B
        instead of $274.5B until this was caught.

        Instants (balance-sheet items) count as annual when they come from an
        annual filing, because a year-end cash balance is the annual figure.
        """
        duration = self.duration_days
        if duration is None:
            return self.form.startswith(("10-K", "20-F", "40-F"))
        return 300 <= duration <= 400

    @property
    def source_url(self) -> str:
        """Link to the exact filing this number came from."""
        clean = self.accession.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{clean}/{self.accession}-index.htm"

    @property
    def lag_days(self) -> int:
        """How long after period end this became public."""
        return (self.filed - self.period_end).days


@dataclass
class CompanyIdentity:
    cik: int
    ticker: str
    name: str
    exchange: str | None = None
    sic: str | None = None
    sic_description: str | None = None
    fiscal_year_end: str | None = None
    state: str | None = None

    @property
    def edgar_url(self) -> str:
        return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={self.cik:010d}"


@dataclass
class FinancialHistory:
    """Every fact retrieved for one company, queryable point-in-time."""

    identity: CompanyIdentity
    facts: list[XBRLFact] = field(default_factory=list)
    retrieved_at: datetime | None = None

    def concepts_available(self) -> set[str]:
        return {f.concept for f in self.facts}

    def visible_as_of(self, as_of: date | None) -> list[XBRLFact]:
        """Facts that were public on ``as_of``.

        Filters on ``filed``. This single line is what separates an honest
        backtest from a fictional one.
        """
        if as_of is None:
            return list(self.facts)
        return [f for f in self.facts if f.filed <= as_of]

    def latest(
        self, concept: str, *, as_of: date | None = None, annual: bool | None = None
    ) -> XBRLFact | None:
        """Most recent reported value for a concept, as known on ``as_of``.

        Ties on period end are broken by the *earliest* filing, so the original
        figure wins over a later restatement of the same period. An investor on
        that date had the original.
        """
        candidates = [f for f in self.visible_as_of(as_of) if f.concept == concept]
        if annual is True:
            candidates = [f for f in candidates if f.is_annual]
        elif annual is False:
            candidates = [f for f in candidates if not f.is_annual]
        if not candidates:
            return None
        return sorted(candidates, key=lambda f: (f.period_end, -f.filed.toordinal()))[-1]

    def series(
        self, concept: str, *, as_of: date | None = None, annual: bool = True
    ) -> list[XBRLFact]:
        """Chronological history of a concept, one entry per period.

        Deduplicates by period, keeping the earliest filing for each - the
        number as first reported rather than as later revised.
        """
        rows = [
            f for f in self.visible_as_of(as_of)
            if f.concept == concept and (f.is_annual if annual else not f.is_annual)
        ]
        by_period: dict[date, XBRLFact] = {}
        for f in sorted(rows, key=lambda f: f.filed):
            by_period.setdefault(f.period_end, f)
        return sorted(by_period.values(), key=lambda f: f.period_end)

    def derived_free_cash_flow(
        self, *, as_of: date | None = None
    ) -> tuple[float, XBRLFact, XBRLFact] | None:
        """Operating cash flow minus capex, with both source facts returned.

        Derived rather than reported, so the caller can label it an estimate
        and cite both inputs.
        """
        ocf = self.latest("operating_cash_flow", as_of=as_of, annual=True)
        capex = self.latest("capex", as_of=as_of, annual=True)
        if ocf is None or capex is None:
            return None
        return ocf.value - abs(capex.value), ocf, capex


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------
class EdgarClient:
    """Fetches and normalises SEC XBRL data.

    Responses are cached on disk because company facts change only when a new
    filing lands, and re-downloading a multi-megabyte document to answer the
    same question is rude to a public service.
    """

    _lock = threading.Lock()
    _last_request = 0.0

    def __init__(self, cache_dir: str | Path | None = None, timeout: float | None = None) -> None:
        settings = get_settings()
        self.user_agent = settings.user_agent
        self.timeout = timeout or settings.source_timeout_seconds
        self.cache_dir = Path(cache_dir or Path.home() / ".cache" / "asymmetry" / "edgar")
        self._ticker_map: dict[str, dict[str, Any]] | None = None

        if "example.com" in self.user_agent or "set ASYMMETRY_USER_AGENT" in self.user_agent:
            log.warning(
                "ASYMMETRY_USER_AGENT is unset. The SEC requires real contact "
                "details and may block requests without them."
            )

    # ---- plumbing ------------------------------------------------------
    def _throttle(self) -> None:
        with EdgarClient._lock:
            gap = time.monotonic() - EdgarClient._last_request
            if gap < MIN_REQUEST_INTERVAL:
                time.sleep(MIN_REQUEST_INTERVAL - gap)
            EdgarClient._last_request = time.monotonic()

    def _get(self, url: str, cache_key: str | None = None, max_age_hours: int = 24) -> Any:
        cache_path = self.cache_dir / f"{cache_key}.json" if cache_key else None
        if cache_path and cache_path.exists():
            age_h = (time.time() - cache_path.stat().st_mtime) / 3600
            if age_h < max_age_hours:
                try:
                    return json.loads(cache_path.read_text())
                except json.JSONDecodeError:
                    cache_path.unlink(missing_ok=True)

        self._throttle()
        headers = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as c:
                resp = c.get(url)
        except httpx.HTTPError as exc:
            raise EdgarError(f"could not reach SEC EDGAR: {exc}") from exc

        if resp.status_code == 404:
            raise EdgarError(f"not found at SEC: {url}")
        if resp.status_code == 403:
            raise EdgarError(
                "SEC returned 403. This usually means the User-Agent lacks real "
                "contact details, or this network blocks sec.gov. Set "
                "ASYMMETRY_USER_AGENT='YourTool/1.0 (you@example.com)'."
            )
        if resp.status_code != 200:
            raise EdgarError(f"SEC returned {resp.status_code} for {url}")

        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise EdgarError(f"SEC returned non-JSON for {url}") from exc

        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(data))
        return data

    # ---- identity ------------------------------------------------------
    def _load_ticker_map(self) -> dict[str, dict[str, Any]]:
        if self._ticker_map is not None:
            return self._ticker_map
        raw = self._get(TICKER_MAP_URL, cache_key="company_tickers", max_age_hours=168)
        mapping: dict[str, dict[str, Any]] = {}
        for entry in raw.values():
            ticker = str(entry.get("ticker", "")).upper().strip()
            if ticker:
                mapping[ticker] = {"cik": int(entry["cik_str"]), "title": entry.get("title", "")}
        self._ticker_map = mapping
        return mapping

    def resolve_ticker(self, ticker: str) -> CompanyIdentity:
        """Ticker to CIK, enriched from the submissions endpoint."""
        symbol = re.sub(r"[^A-Z0-9.\-]", "", ticker.upper().strip())
        if not symbol:
            raise TickerNotFound("empty ticker")

        mapping = self._load_ticker_map()
        entry = mapping.get(symbol)
        if entry is None:
            near = [t for t in mapping if t.startswith(symbol[:3])][:6]
            raise TickerNotFound(
                f"{symbol} is not in the SEC's ticker list. It may be foreign, "
                f"private, delisted, or an ETF."
                + (f" Similar: {', '.join(sorted(near))}" if near else "")
            )

        cik = entry["cik"]
        identity = CompanyIdentity(cik=cik, ticker=symbol, name=entry["title"])
        try:
            sub = self._get(SUBMISSIONS_URL.format(cik=cik), cache_key=f"sub_{cik}", max_age_hours=24)
            identity.name = sub.get("name") or identity.name
            identity.sic = sub.get("sic")
            identity.sic_description = sub.get("sicDescription")
            identity.fiscal_year_end = sub.get("fiscalYearEnd")
            identity.state = sub.get("stateOfIncorporation")
            exchanges = sub.get("exchanges") or []
            identity.exchange = exchanges[0] if exchanges else None
        except EdgarError as exc:
            log.warning("submissions lookup failed for %s: %s", symbol, exc)
        return identity

    # ---- facts ---------------------------------------------------------
    def fetch_history(self, ticker: str, *, max_age_hours: int = 24) -> FinancialHistory:
        """Every mapped concept for a company, normalised into facts."""
        identity = self.resolve_ticker(ticker)
        raw = self._get(
            COMPANY_FACTS_URL.format(cik=identity.cik),
            cache_key=f"facts_{identity.cik}",
            max_age_hours=max_age_hours,
        )
        return FinancialHistory(
            identity=identity,
            facts=parse_company_facts(raw),
            retrieved_at=datetime.now(),
        )


def parse_company_facts(raw: dict[str, Any]) -> list[XBRLFact]:
    """Normalise a companyfacts document into :class:`XBRLFact` records.

    Pure, so it can be tested against a fixture without touching the network.

    Only USD (and share-count) units are kept, and only statement forms. Facts
    without a ``filed`` date are discarded outright: an undated fact cannot
    participate in point-in-time reasoning, and letting one through would
    silently defeat the entire mechanism.
    """
    out: list[XBRLFact] = []
    all_facts = raw.get("facts", {})
    gaap = all_facts.get("us-gaap", {})
    dei = all_facts.get("dei", {})

    for concept, tags in CONCEPTS.items():
        # Gather every candidate tag separately, then choose one. Facts for a
        # concept must all come from a single tag: mixing tags across periods
        # creates discontinuities that read as real changes in the business.
        by_tag: dict[str, list[XBRLFact]] = {}

        for tag in tags:
            node = gaap.get(tag) or dei.get(tag)
            if not node:
                continue
            parsed: list[XBRLFact] = []
            for unit, entries in (node.get("units") or {}).items():
                if unit not in ("USD", "shares", "USD/shares"):
                    continue
                for e in entries:
                    filed_raw = e.get("filed")
                    form = e.get("form", "")
                    if not filed_raw or form not in STATEMENT_FORMS:
                        continue
                    try:
                        period_end = date.fromisoformat(e["end"])
                        filed = date.fromisoformat(filed_raw)
                        value = float(e["val"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    start = None
                    if e.get("start"):
                        try:
                            start = date.fromisoformat(e["start"])
                        except ValueError:
                            start = None
                    parsed.append(XBRLFact(
                        concept=concept, tag=tag, value=value, unit=unit,
                        period_end=period_end, filed=filed, form=form,
                        accession=e.get("accn", ""), period_start=start,
                        fiscal_year=e.get("fy"), fiscal_period=e.get("fp"),
                        frame=e.get("frame"),
                    ))
            if parsed:
                by_tag[tag] = parsed

        if not by_tag:
            continue

        # Choose one tag: most RECENT annual data first, then most annual
        # periods, then declared priority.
        #
        # Both earlier rules were wrong in opposite directions, and each was
        # caught on a real company:
        #
        #  * "first tag with any data" - Plug Power files revenue under four
        #    tags and the top-priority one carries only quarterly data, so the
        #    company appeared to have no annual revenue at all.
        #  * "most annual periods" - Apple's legacy SalesRevenueNet has a
        #    longer history than the modern tag but stopped in 2018, so the
        #    latest revenue came back as FY2017.
        #
        # Recency has to dominate: a tag abandoned years ago cannot describe
        # the company now, however much history it carries. The cost is a
        # shorter series when a filer switches tags, which is the right trade
        # for forward-looking analysis - and far safer than stitching tags
        # together, which would manufacture a step change that the signal
        # detector would happily report as acceleration.
        def rank(item: tuple[str, list[XBRLFact]]) -> tuple[date, int, int]:
            tag, facts = item
            annual = [f for f in facts if f.is_annual]
            latest = max((f.period_end for f in annual), default=date.min)
            return (latest, len(annual), -tags.index(tag))

        _best_tag, best_facts = max(by_tag.items(), key=rank)
        out.extend(best_facts)

    return sorted(out, key=lambda f: (f.concept, f.period_end, f.filed))


def growth_rate(series: Sequence[XBRLFact]) -> float | None:
    """Year-over-year growth from the last two annual periods."""
    if len(series) < 2:
        return None
    prior, latest = series[-2].value, series[-1].value
    if prior <= 0:
        return None
    return latest / prior - 1.0


def cagr_from_series(series: Sequence[XBRLFact]) -> float | None:
    """Compound growth across the whole available history."""
    if len(series) < 2:
        return None
    first, last = series[0], series[-1]
    years = (last.period_end - first.period_end).days / 365.25
    if years < 0.9 or first.value <= 0 or last.value <= 0:
        return None
    return (last.value / first.value) ** (1 / years) - 1.0


#: Ratios a stock split plausibly produces. Splits land almost exactly on
#: simple factors; a financing round produces a messy number like 1.37. That
#: difference is the only thing distinguishing the two from share counts alone.
#: 1.5-for-1 is deliberately absent. It is a rare split and a very common
#: financing outcome, and for the small cash-burning companies this platform
#: targets, a 50% jump in share count is overwhelmingly likely to be issuance.
#: Including it caused Plug Power - a serial diluter - to have two capital
#: raises silently reclassified as splits, understating its dilution and
#: therefore overstating its per-share upside. That is the dangerous direction
#: of error, so the ratio is excluded.
COMMON_SPLIT_RATIOS: tuple[float, ...] = (
    2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 20.0,        # forward
    0.5, 0.333333, 0.25, 0.2, 0.1, 0.05,                   # reverse
)

#: How far an observed annual ratio may sit from a clean split factor and still
#: be called a split.
#:
#: Generous on purpose. A split lands on an exact factor only if nothing else
#: happens that year, which is rare: Apple's 7-for-1 shows up as 6.52x because
#: it bought back ~7% of its stock in the same year, and its 4-for-1 shows up as
#: 3.82x. A 2% tolerance detected neither and reported Apple as diluting 18% a
#: year - the single most damaging number this module could produce, since every
#: per-share scenario divides by it.
SPLIT_TOLERANCE = 0.20

#: Below this, a change is ordinary drift and is never considered a split.
SPLIT_MIN_JUMP = 1.8


#: Within this distance of a clean factor, a split is the far likelier reading.
#: Beyond it (but still within SPLIT_TOLERANCE) the event is genuinely
#: ambiguous and is labelled as such rather than assumed either way.
SPLIT_HIGH_CONFIDENCE = 0.05


@dataclass
class SplitAdjustment:
    """A period where the share count moved like a split rather than a raise."""

    at: date
    ratio: float
    matched: float

    @property
    def confident(self) -> bool:
        return abs(self.ratio - self.matched) / self.matched <= SPLIT_HIGH_CONFIDENCE

    def describe(self) -> str:
        if self.confident:
            return (
                f"{self.at}: share count changed {self.ratio:.2f}x, consistent with a "
                f"{self.matched:g}-for-1 split"
            )
        return (
            f"{self.at}: share count changed {self.ratio:.2f}x. Read as a "
            f"{self.matched:g}-for-1 split, but a large share issuance would look "
            f"similar. AMBIGUOUS - verify against the filing before relying on it."
        )


def detect_splits(series: Sequence[XBRLFact]) -> list[SplitAdjustment]:
    """Find period-over-period jumps that look like splits.

    A split multiplies the share count without diluting anybody. Treating one
    as dilution is a serious error: Apple's count went from 888M to 14.8B
    through two splits, which naively reads as 18%/yr dilution and would gut
    every per-share scenario the platform computes.

    Only large discrete jumps are considered, and the nearest clean factor is
    chosen. The residual ambiguity is real and worth stating: from share counts
    alone, a 2-for-1 split and a dilutive raise that doubles the count look
    identical. This is why every adjustment is returned to the caller and
    surfaced in the report rather than applied silently - the reader can see
    what was assumed and disagree.
    """
    adjustments: list[SplitAdjustment] = []
    for prev, cur in zip(series, series[1:]):
        if prev.value <= 0:
            continue
        ratio = cur.value / prev.value
        if SPLIT_MIN_JUMP > ratio > (1 / SPLIT_MIN_JUMP):
            continue   # ordinary drift

        best = min(COMMON_SPLIT_RATIOS, key=lambda c: abs(ratio - c) / c)
        if abs(ratio - best) / best <= SPLIT_TOLERANCE:
            adjustments.append(SplitAdjustment(cur.period_end, ratio, best))
    return adjustments


def split_adjusted_values(
    series: Sequence[XBRLFact],
) -> tuple[list[tuple[date, float]], list[SplitAdjustment]]:
    """Restate the share count in today's share terms.

    Walks backwards applying each detected split, so every historical figure is
    expressed on the current basis and the remaining change is real dilution.
    """
    splits = detect_splits(series)
    if not splits:
        return [(f.period_end, f.value) for f in series], []

    by_date = {s.at: s.matched for s in splits}
    adjusted: list[tuple[date, float]] = []
    factor = 1.0
    # Reverse order: everything before a split must be scaled up to match.
    for fact in reversed(series):
        adjusted.append((fact.period_end, fact.value * factor))
        if fact.period_end in by_date:
            factor *= by_date[fact.period_end]
    adjusted.reverse()
    return adjusted, splits


@dataclass
class DilutionEstimate:
    """Share-count growth, with the ambiguity left visible.

    Both readings are reported because the adjustment is a judgement. Anything
    downstream that needs one number should take ``conservative``: overstating
    dilution understates upside, which is the safe direction for a system whose
    house bias is optimism.
    """

    adjusted: float | None          # net of detected splits
    raw: float | None               # no adjustment at all
    splits: list[SplitAdjustment] = field(default_factory=list)
    window_years: float | None = None
    periods: int = 0

    @property
    def has_ambiguous_split(self) -> bool:
        return any(not s.confident for s in self.splits)

    @property
    def conservative(self) -> float | None:
        """The higher (worse) of the two readings."""
        options = [v for v in (self.adjusted, self.raw) if v is not None]
        return max(options) if options else None

    @property
    def best_estimate(self) -> float | None:
        """Adjusted when every split is confident, conservative otherwise."""
        if self.splits and self.has_ambiguous_split:
            return self.conservative
        return self.adjusted if self.adjusted is not None else self.raw

    def note(self) -> str:
        if not self.splits:
            return "No share splits detected; the figure is straightforward."
        if self.has_ambiguous_split:
            return (
                "At least one share-count jump could be either a split or a large "
                "issuance. The more conservative (higher-dilution) reading is used."
            )
        return "Adjusted for detected splits."


def dilution_rate(
    series: Sequence[XBRLFact], *, recent_periods: int | None = 6
) -> DilutionEstimate:
    """Annualised share-count growth. Positive means dilution.

    Defaults to the most recent periods rather than the full history, for two
    reasons: forward-looking scenarios care about the company's *current*
    financing behaviour, not what it did a decade ago, and a shorter window is
    less likely to straddle a split at all.
    """
    if len(series) < 2:
        return DilutionEstimate(None, None, [], None, len(series))

    window = series[-recent_periods:] if recent_periods else list(series)
    if len(window) < 2:
        window = series[-2:]

    raw = cagr_from_series(window)
    values, splits = split_adjusted_values(window)
    first_date, first_value = values[0]
    last_date, last_value = values[-1]
    years = (last_date - first_date).days / 365.25

    adjusted = None
    if years >= 0.9 and first_value > 0 and last_value > 0:
        adjusted = (last_value / first_value) ** (1 / years) - 1.0

    return DilutionEstimate(
        adjusted=adjusted, raw=raw, splits=splits,
        window_years=round(years, 2), periods=len(window),
    )
