"""Public-API sources.

Only official, documented, openly accessible endpoints are implemented, each
with the rate limit its operator publishes. Anything requiring circumvention of
access controls, paywalls or terms of service is deliberately absent - see
``sources/unavailable.py`` for the register of what was excluded and why.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from urllib.parse import quote_plus

import httpx

from ..config import get_settings
from .base import RawDoc, Source, SourceTier


def _client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(
        timeout=s.source_timeout_seconds,
        headers={"User-Agent": s.user_agent, "Accept-Encoding": "gzip, deflate"},
        follow_redirects=True,
    )


class ArxivSource(Source):
    """arXiv, for research acceleration in a field.

    A sustained rise in publication volume around a narrow technical topic
    frequently precedes commercial activity by several years, which is exactly
    the lead time this system is trying to buy.
    """

    name = "arxiv"
    source_type = "research"
    url = "https://export.arxiv.org/api/query"
    tier = SourceTier.GOVERNMENT       # peer-reviewed / preprint academic record
    rate_limit_per_hour = 1200         # arXiv asks for ~1 request per 3 seconds

    def fetch(self, query: str, *, limit: int = 25, as_of: date | None = None) -> list[dict[str, Any]]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": min(limit, 100),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        with _client() as c:
            resp = c.get(self.url, params=params)
            resp.raise_for_status()
            return self._split_entries(resp.text)

    @staticmethod
    def _split_entries(xml: str) -> list[dict[str, Any]]:
        """Parse the Atom feed without a heavyweight XML dependency."""
        import xml.etree.ElementTree as ET

        ns = {"a": "http://www.w3.org/2005/Atom"}
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            return []
        out = []
        for e in root.findall("a:entry", ns):
            def txt(tag: str) -> str:
                node = e.find(f"a:{tag}", ns)
                return (node.text or "").strip() if node is not None else ""
            out.append({
                "id": txt("id"),
                "title": txt("title"),
                "summary": txt("summary"),
                "published": txt("published"),
                "authors": [
                    (a.find("a:name", ns).text or "")
                    for a in e.findall("a:author", ns)
                    if a.find("a:name", ns) is not None
                ],
            })
        return out

    def parse(self, payload: dict[str, Any]) -> RawDoc | None:
        if not payload.get("id"):
            return None
        published = None
        if payload.get("published"):
            try:
                published = datetime.fromisoformat(payload["published"].replace("Z", "+00:00")).date()
            except ValueError:
                published = None
        return RawDoc(
            external_id=payload["id"],
            title=payload.get("title", "").replace("\n", " "),
            body=payload.get("summary", "").replace("\n", " "),
            url=payload["id"],
            published_at=published,
            author=", ".join(payload.get("authors", [])[:3]) or None,
            raw=payload,
        )


class HackerNewsSource(Source):
    """Hacker News via the public Algolia API.

    Tier 5: useful for *noticing* that something exists, never acceptable as
    evidence for a claim. The fact checker enforces that distinction.
    """

    name = "hackernews"
    source_type = "community"
    url = "https://hn.algolia.com/api/v1/search_by_date"
    tier = SourceTier.SOCIAL
    rate_limit_per_hour = 3600

    def fetch(self, query: str, *, limit: int = 25, as_of: date | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query": query, "tags": "story", "hitsPerPage": min(limit, 50)}
        if as_of:
            cutoff = int(datetime(as_of.year, as_of.month, as_of.day).timestamp())
            params["numericFilters"] = f"created_at_i<{cutoff}"
        with _client() as c:
            resp = c.get(self.url, params=params)
            resp.raise_for_status()
            return resp.json().get("hits", [])

    def parse(self, payload: dict[str, Any]) -> RawDoc | None:
        if not payload.get("objectID"):
            return None
        published = None
        if payload.get("created_at"):
            try:
                published = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00")).date()
            except ValueError:
                published = None
        return RawDoc(
            external_id=str(payload["objectID"]),
            title=payload.get("title") or payload.get("story_title") or "",
            body=payload.get("story_text") or payload.get("comment_text") or "",
            url=payload.get("url") or f"https://news.ycombinator.com/item?id={payload['objectID']}",
            published_at=published,
            metrics={"points": float(payload.get("points") or 0),
                     "comments": float(payload.get("num_comments") or 0)},
            raw=payload,
        )


class GitHubSource(Source):
    """GitHub repository search, for developer-adoption signals.

    Unauthenticated search is limited to 10 requests/minute; supplying
    ``GITHUB_TOKEN`` raises that to 30. The limiter is set to the safe figure.
    """

    name = "github"
    source_type = "code"
    url = "https://api.github.com/search/repositories"
    tier = SourceTier.INDUSTRY_PRESS
    rate_limit_per_hour = 550

    def fetch(self, query: str, *, limit: int = 25, as_of: date | None = None) -> list[dict[str, Any]]:
        import os

        headers = {"Accept": "application/vnd.github+json"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        params = {"q": query, "sort": "updated", "order": "desc", "per_page": min(limit, 50)}
        with _client() as c:
            resp = c.get(self.url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json().get("items", [])

    def parse(self, payload: dict[str, Any]) -> RawDoc | None:
        if not payload.get("full_name"):
            return None
        published = None
        if payload.get("created_at"):
            try:
                published = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00")).date()
            except ValueError:
                published = None
        return RawDoc(
            external_id=payload["full_name"],
            title=payload["full_name"],
            body=payload.get("description") or "",
            url=payload.get("html_url"),
            published_at=published,
            metrics={
                "stars": float(payload.get("stargazers_count") or 0),
                "forks": float(payload.get("forks_count") or 0),
                "open_issues": float(payload.get("open_issues_count") or 0),
            },
            raw=payload,
        )


class SECFullTextSource(Source):
    """SEC EDGAR full-text search over filings.

    Tier 1 evidence. The SEC requires a descriptive User-Agent with contact
    details and rate-limits to 10 requests/second; the limiter here is set far
    below that because being blocked by the SEC would disable the single most
    authoritative source the platform has.
    """

    name = "sec-edgar-fts"
    source_type = "filing"
    url = "https://efts.sec.gov/LATEST/search-index?q="
    tier = SourceTier.GOVERNMENT
    rate_limit_per_hour = 2000

    SEARCH = "https://efts.sec.gov/LATEST/search-index"

    def fetch(self, query: str, *, limit: int = 25, as_of: date | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"q": f'"{query}"', "from": 0, "size": min(limit, 50)}
        if as_of:
            params["dateRange"] = "custom"
            params["enddt"] = as_of.isoformat()
        with _client() as c:
            resp = c.get("https://efts.sec.gov/LATEST/search-index", params=params)
            if resp.status_code == 404:
                resp = c.get("https://www.sec.gov/cgi-bin/srqsb", params={"text": query})
                resp.raise_for_status()
                return []
            resp.raise_for_status()
            try:
                data = resp.json()
            except json.JSONDecodeError:
                return []
            return data.get("hits", {}).get("hits", [])

    def parse(self, payload: dict[str, Any]) -> RawDoc | None:
        src = payload.get("_source", payload)
        adsh = src.get("adsh") or payload.get("_id")
        if not adsh:
            return None
        published = None
        if src.get("file_date"):
            try:
                published = date.fromisoformat(src["file_date"])
            except ValueError:
                published = None
        names = src.get("display_names") or []
        return RawDoc(
            external_id=str(adsh),
            title=f"{src.get('form_type', 'Filing')}: {names[0] if names else 'Unknown'}",
            body=src.get("file_description", "") or "",
            url=f"https://www.sec.gov/Archives/edgar/data/{src.get('ciks', [''])[0]}/{adsh}.txt"
            if src.get("ciks") else None,
            published_at=published,
            entities=names,
            raw=src,
        )


def register_public_sources(registry) -> None:
    for cls in (ArxivSource, HackerNewsSource, GitHubSource, SECFullTextSource):
        registry.register(cls())
