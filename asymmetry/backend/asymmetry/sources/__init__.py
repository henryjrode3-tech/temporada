"""Source registry assembly.

Sources deliberately NOT implemented, and why:

* **Crunchbase / PitchBook / CB Insights** - licensed data behind paid APIs.
  Add them yourself with credentials; scraping them violates their terms.
* **Google Scholar** - no public API and its terms forbid automated access.
  arXiv, PubMed and OpenAlex cover the same ground legitimately.
* **LinkedIn** - automated collection is prohibited. Hiring signals should come
  from company career pages or an aggregator with an actual API.
* **Google Trends** - no official API. ``pytrends`` is unofficial and brittle.
* **Paywalled financial media** - copyright. Headlines via RSS only.

The gap is filled by declaring these in the registry as unavailable rather than
by quietly scraping them, so the absence is visible instead of being papered
over with data of unknown provenance.
"""

from __future__ import annotations

from ..config import get_settings
from .base import RawDoc, Source, SourceRegistry, SourceTier, registry
from .mock import MockSource, SYNTHETIC_COMPANIES, make_series
from .public import register_public_sources

#: Sources a user could enable with their own credentials.
REQUIRES_CREDENTIALS: dict[str, str] = {
    "crunchbase": "Paid API. Set CRUNCHBASE_API_KEY and implement fetch/parse.",
    "pitchbook": "Paid API, enterprise licence required.",
    "usaspending": "Free API, not yet implemented - good next addition for contract signals.",
    "uspto-patentsview": "Free API, not yet implemented - good next addition for patent signals.",
    "openalex": "Free API, not yet implemented - citation acceleration.",
    "fred": "Free API for macro series. Set FRED_API_KEY.",
}


def build_registry(use_mock: bool | None = None) -> SourceRegistry:
    """Assemble the active registry.

    Mock mode registers only the synthetic corpus, which keeps tests hermetic
    and lets the platform be demonstrated with no network access at all.
    """
    settings = get_settings()
    use_mock = settings.use_mock_sources if use_mock is None else use_mock

    reg = SourceRegistry()
    reg.register(MockSource())
    if not use_mock:
        register_public_sources(reg)
    return reg


__all__ = [
    "RawDoc", "Source", "SourceRegistry", "SourceTier", "registry",
    "MockSource", "SYNTHETIC_COMPANIES", "make_series",
    "build_registry", "REQUIRES_CREDENTIALS",
]
