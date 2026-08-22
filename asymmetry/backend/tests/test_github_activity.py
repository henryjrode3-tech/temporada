"""GitHub activity ingestion.

Tested against mocked transports rather than the live API. ``api.github.com``
is blocked by egress policy in some environments (including the one this was
developed in), so relying on a live call would make the suite fail for reasons
unrelated to the code.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import httpx
import pytest

from asymmetry.core.signals import SignalType, TimeSeriesPoint, detect_acceleration
from asymmetry.sources.github_activity import (
    GitHubActivityError,
    RepoActivity,
    activity_to_series,
    fetch_repo_activity,
)


def _week_ts(year: int, month: int, day: int) -> int:
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp())


def _mock_transport(commit_weeks, contributors, *, meta_status=200, stats_status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/stats/commit_activity"):
            if stats_status == 202:
                return httpx.Response(202, json=[])
            return httpx.Response(stats_status, json=commit_weeks)
        if path.endswith("/stats/contributors"):
            return httpx.Response(stats_status, json=contributors)
        if meta_status != 200:
            return httpx.Response(meta_status, json={"message": "Not Found"})
        return httpx.Response(200, json={
            "full_name": "acme/widget", "stargazers_count": 4210,
            "forks_count": 312, "open_issues_count": 47,
        })

    return httpx.MockTransport(handler)


@pytest.fixture()
def patched(monkeypatch):
    """Install a mock transport into the module's client construction."""
    def install(commit_weeks, contributors, **kw):
        transport = _mock_transport(commit_weeks, contributors, **kw)
        real_client = httpx.Client

        def factory(*args, **kwargs):
            kwargs["transport"] = transport
            return real_client(*args, **kwargs)

        monkeypatch.setattr(httpx, "Client", factory)
    return install


#: Flat for eight months, then a pronounced bend upward.
ACCELERATING_WEEKS = [
    {"week": _week_ts(2025, 1, 5), "total": 10},
    {"week": _week_ts(2025, 2, 2), "total": 12},
    {"week": _week_ts(2025, 3, 2), "total": 11},
    {"week": _week_ts(2025, 4, 6), "total": 13},
    {"week": _week_ts(2025, 5, 4), "total": 12},
    {"week": _week_ts(2025, 6, 1), "total": 14},
    {"week": _week_ts(2025, 7, 6), "total": 13},
    {"week": _week_ts(2025, 8, 3), "total": 15},
    {"week": _week_ts(2025, 9, 7), "total": 48},
    {"week": _week_ts(2025, 10, 5), "total": 71},
    {"week": _week_ts(2025, 11, 2), "total": 96},
]

CONTRIBUTORS = [
    {"author": {"login": "a"}, "weeks": [
        {"w": _week_ts(2025, 1, 5), "c": 5}, {"w": _week_ts(2025, 9, 7), "c": 9},
        {"w": _week_ts(2025, 10, 5), "c": 12}, {"w": _week_ts(2025, 11, 2), "c": 15},
    ]},
    {"author": {"login": "b"}, "weeks": [
        {"w": _week_ts(2025, 9, 7), "c": 3}, {"w": _week_ts(2025, 10, 5), "c": 7},
        {"w": _week_ts(2025, 11, 2), "c": 11},
    ]},
    {"author": {"login": "c"}, "weeks": [
        {"w": _week_ts(2025, 10, 5), "c": 2}, {"w": _week_ts(2025, 11, 2), "c": 6},
        {"w": _week_ts(2025, 1, 5), "c": 0},   # zero weeks must not count
    ]},
]


class TestFetch:
    def test_parses_commit_and_contributor_series(self, patched):
        patched(ACCELERATING_WEEKS, CONTRIBUTORS)
        a = fetch_repo_activity("acme/widget")
        assert a.full_name == "acme/widget"
        assert len(a.commit_series) == len(ACCELERATING_WEEKS)
        assert a.stars == 4210
        assert a.has_history

    def test_series_is_chronological(self, patched):
        patched(list(reversed(ACCELERATING_WEEKS)), CONTRIBUTORS)
        a = fetch_repo_activity("acme/widget")
        dates = [d for d, _ in a.commit_series]
        assert dates == sorted(dates)

    def test_zero_commit_weeks_do_not_count_a_contributor(self, patched):
        patched(ACCELERATING_WEEKS, CONTRIBUTORS)
        a = fetch_repo_activity("acme/widget")
        january = [n for d, n in a.contributor_series if d == date(2025, 1, 5)]
        assert january == [1.0]     # only contributor "a" was active

    def test_contributor_count_rises(self, patched):
        patched(ACCELERATING_WEEKS, CONTRIBUTORS)
        a = fetch_repo_activity("acme/widget")
        counts = dict(a.contributor_series)
        assert counts[date(2025, 11, 2)] == 3.0

    def test_as_of_narrows_the_window(self, patched):
        patched(ACCELERATING_WEEKS, CONTRIBUTORS)
        a = fetch_repo_activity("acme/widget", as_of=date(2025, 6, 30))
        assert all(d <= date(2025, 6, 30) for d, _ in a.commit_series)
        assert len(a.commit_series) < len(ACCELERATING_WEEKS)

    def test_missing_repository_raises(self, patched):
        patched([], [], meta_status=404)
        with pytest.raises(GitHubActivityError, match="not found"):
            fetch_repo_activity("acme/missing")

    def test_malformed_name_rejected(self):
        with pytest.raises(GitHubActivityError, match="owner/repo"):
            fetch_repo_activity("no-slash")

    def test_cache_warming_does_not_crash(self, patched, monkeypatch):
        """A 202 means 'computing', not 'no data'."""
        monkeypatch.setattr(
            "asymmetry.sources.github_activity.STATS_RETRY_DELAYS", (0.0, 0.0)
        )
        patched(ACCELERATING_WEEKS, CONTRIBUTORS, stats_status=202)
        a = fetch_repo_activity("acme/widget")
        assert a.commit_series == []
        assert not a.has_history

    def test_empty_repository(self, patched):
        patched([], [])
        a = fetch_repo_activity("acme/widget")
        assert a.commit_series == [] and not a.has_history


class TestSeriesShaping:
    def _activity(self, **kw) -> RepoActivity:
        base = dict(
            full_name="acme/widget", commit_series=[], contributor_series=[],
            stars=0, forks=0, open_issues=0, fetched_at=datetime.now(timezone.utc),
        )
        base.update(kw)
        return RepoActivity(**base)

    def test_commits_are_summed_into_months(self, patched):
        a = self._activity(commit_series=[
            (date(2025, 3, 3), 10.0), (date(2025, 3, 10), 15.0), (date(2025, 4, 7), 8.0),
        ])
        series = activity_to_series(a)["github_activity"]
        assert dict(series)["2025-03-01"] == 25.0

    def test_contributors_are_maxed_not_summed(self, patched):
        """Summing weekly contributor counts double-counts the same people."""
        a = self._activity(contributor_series=[
            (date(2025, 3, 3), 4.0), (date(2025, 3, 10), 5.0), (date(2025, 3, 17), 3.0),
        ])
        series = activity_to_series(a)["github_contributors"]
        assert dict(series)["2025-03-01"] == 5.0

    def test_empty_series_produce_no_keys(self):
        assert activity_to_series(self._activity()) == {}


class TestEndToEndDetection:
    """The point of the whole module: real history producing a real signal."""

    def test_acceleration_is_detected_from_ingested_history(self, patched):
        patched(ACCELERATING_WEEKS, CONTRIBUTORS)
        activity = fetch_repo_activity("acme/widget")
        series = activity_to_series(activity)

        points = [
            TimeSeriesPoint(date.fromisoformat(d), v)
            for d, v in series["github_activity"]
        ]
        signal = detect_acceleration(SignalType.GITHUB_ACTIVITY, points)
        assert signal is not None
        assert signal.pct_change > 1.0
        assert signal.is_significant

    def test_flat_history_produces_no_signal(self, patched):
        flat = [
            {"week": _week_ts(2025, month, 5), "total": 30}
            for month in range(1, 12)
        ]
        patched(flat, [])
        series = activity_to_series(fetch_repo_activity("acme/widget"))
        points = [
            TimeSeriesPoint(date.fromisoformat(d), v)
            for d, v in series["github_activity"]
        ]
        assert detect_acceleration(SignalType.GITHUB_ACTIVITY, points) is None
