"""Live developer-activity series from GitHub.

The signal engine's value depends on being fed real history rather than
synthetic curves. GitHub's statistics endpoints return 52 weeks of actual
weekly commit counts and per-contributor activity, which is exactly the shape
:mod:`asymmetry.core.signals` expects.

Why developer activity matters here: for infrastructure and tooling, sustained
acceleration in contributors and commits tends to precede commercial traction
by a year or more, and it is visible to anyone willing to look while being
invisible to anyone watching only price.

**A caveat that matters for backtesting.** These endpoints return a rolling
52-week window - not a queryable archive. They can support live detection and
they cannot support a 2015 backtest, so the as-of cutoff here can only *narrow*
the window that GitHub happens to be serving today.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import httpx

from ..config import get_settings

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"

#: GitHub computes these statistics asynchronously. The first request for a
#: cold repository returns 202 with an empty body while the cache warms; the
#: correct response is to wait and retry, not to treat it as "no data".
STATS_RETRY_DELAYS = (2.0, 4.0, 8.0)


class GitHubActivityError(RuntimeError):
    pass


@dataclass
class RepoActivity:
    """Real weekly activity for one repository."""

    full_name: str
    commit_series: list[tuple[date, float]]
    contributor_series: list[tuple[date, float]]
    stars: int
    forks: int
    open_issues: int
    fetched_at: datetime

    @property
    def has_history(self) -> bool:
        # Fewer than about six weeks cannot distinguish a trend from a blip.
        return len(self.commit_series) >= 6


def _headers() -> dict[str, str]:
    import os

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": get_settings().user_agent,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_with_stats_retry(client: httpx.Client, url: str) -> Any:
    """GET a statistics endpoint, waiting out GitHub's 202 cache-warming."""
    for delay in (0.0, *STATS_RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        resp = client.get(url, headers=_headers())
        if resp.status_code == 202:
            continue          # still computing
        if resp.status_code == 204:
            return []         # genuinely empty repository
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return []
    log.warning("GitHub statistics still warming for %s", url)
    return []


def fetch_repo_activity(
    full_name: str, *, as_of: date | None = None, timeout: float | None = None
) -> RepoActivity:
    """Fetch real weekly commit and contributor series for ``owner/repo``.

    ``as_of`` narrows the returned window. It cannot extend it: GitHub serves a
    rolling 52 weeks, so a cutoff older than that yields nothing rather than
    silently returning recent data under a historical label.
    """
    if "/" not in full_name:
        raise GitHubActivityError(f"expected 'owner/repo', got {full_name!r}")

    settings = get_settings()
    with httpx.Client(
        timeout=timeout or settings.source_timeout_seconds, follow_redirects=True
    ) as client:
        meta_resp = client.get(f"{GITHUB_API}/repos/{full_name}", headers=_headers())
        if meta_resp.status_code == 404:
            raise GitHubActivityError(f"repository not found: {full_name}")
        meta_resp.raise_for_status()
        meta = meta_resp.json()

        commit_activity = _get_with_stats_retry(
            client, f"{GITHUB_API}/repos/{full_name}/stats/commit_activity"
        )
        contributors = _get_with_stats_retry(
            client, f"{GITHUB_API}/repos/{full_name}/stats/contributors"
        )

    commit_series: list[tuple[date, float]] = []
    for week in commit_activity or []:
        if not isinstance(week, dict) or "week" not in week:
            continue
        when = datetime.fromtimestamp(week["week"], tz=timezone.utc).date()
        commit_series.append((when, float(week.get("total", 0))))
    commit_series.sort()

    # Active contributors per week: how many people committed at all that week.
    # A rising contributor count is a much stronger adoption signal than rising
    # commits, which one enthusiastic maintainer can produce alone.
    weekly_contributors: dict[date, int] = {}
    for contributor in contributors or []:
        if not isinstance(contributor, dict):
            continue
        for week in contributor.get("weeks", []):
            if week.get("c", 0) <= 0:
                continue
            when = datetime.fromtimestamp(week["w"], tz=timezone.utc).date()
            weekly_contributors[when] = weekly_contributors.get(when, 0) + 1
    contributor_series = sorted((d, float(n)) for d, n in weekly_contributors.items())

    if as_of:
        commit_series = [p for p in commit_series if p[0] <= as_of]
        contributor_series = [p for p in contributor_series if p[0] <= as_of]

    return RepoActivity(
        full_name=meta.get("full_name", full_name),
        commit_series=commit_series,
        contributor_series=contributor_series,
        stars=int(meta.get("stargazers_count") or 0),
        forks=int(meta.get("forks_count") or 0),
        open_issues=int(meta.get("open_issues_count") or 0),
        fetched_at=datetime.now(timezone.utc),
    )


def activity_to_series(activity: RepoActivity) -> dict[str, list[tuple[str, float]]]:
    """Shape the activity into the series format the pipeline stores.

    Monthly buckets rather than weekly: weekly commit counts are dominated by
    weekends and holidays, and that seasonality produces false accelerations
    that the significance test then has to work to reject.
    """
    def monthly(series: list[tuple[date, float]], aggregate: str) -> list[tuple[str, float]]:
        buckets: dict[str, list[float]] = {}
        for when, value in series:
            key = when.replace(day=1).isoformat()
            buckets.setdefault(key, []).append(value)
        out = []
        for key in sorted(buckets):
            values = buckets[key]
            # Commits accumulate over a month; contributor counts do not, so
            # summing them would count the same person once per week.
            out.append((key, sum(values) if aggregate == "sum" else max(values)))
        return out

    series: dict[str, list[tuple[str, float]]] = {}
    if activity.commit_series:
        series["github_activity"] = monthly(activity.commit_series, "sum")
    if activity.contributor_series:
        series["github_contributors"] = monthly(activity.contributor_series, "max")
    return series
