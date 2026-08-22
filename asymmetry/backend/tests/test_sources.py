"""Source layer tests.

Network calls are opt-in via ``ASYMMETRY_TEST_NETWORK=1`` so the default suite
stays hermetic and fast.
"""

from __future__ import annotations

import os
from datetime import date

import pytest

from asymmetry.sources import build_registry
from asymmetry.sources.base import RawDoc, Source, SourceTier
from asymmetry.sources.mock import MockSource, make_series
from asymmetry.sources.public import ArxivSource, HackerNewsSource

needs_network = pytest.mark.skipif(
    os.environ.get("ASYMMETRY_TEST_NETWORK") != "1",
    reason="set ASYMMETRY_TEST_NETWORK=1 to run live network tests",
)


class TestTiers:
    def test_social_is_never_citable(self):
        assert not SourceTier.SOCIAL.is_citable_evidence

    def test_government_is_citable_and_most_reliable(self):
        assert SourceTier.GOVERNMENT.is_citable_evidence
        assert SourceTier.GOVERNMENT.default_reliability > SourceTier.SOCIAL.default_reliability

    def test_reliability_decreases_with_tier(self):
        vals = [t.default_reliability for t in sorted(SourceTier)]
        assert vals == sorted(vals, reverse=True)

    def test_registry_excludes_social_from_evidence_grade(self):
        reg = build_registry(use_mock=False)
        assert all(int(s.tier) <= 4 for s in reg.evidence_grade())
        assert any(s.name == "hackernews" for s in reg.all())


class TestArxivQueryBuilding:
    """arXiv silently returns nothing for a quoted phrase plus a date range."""

    def test_single_term_no_cutoff(self):
        assert ArxivSource.build_query("battery") == "all:battery"

    def test_phrase_no_cutoff_is_quoted(self):
        assert ArxivSource.build_query("solid state battery") == 'all:"solid state battery"'

    def test_cutoff_uses_and_joined_terms_not_a_phrase(self):
        q = ArxivSource.build_query("solid state battery", date(2015, 1, 1))
        assert '"' not in q
        assert "all:solid AND all:state AND all:battery" in q

    def test_cutoff_embeds_the_date_window(self):
        q = ArxivSource.build_query("battery", date(2015, 1, 1))
        assert "submittedDate:[199101010000 TO 201501010000]" in q

    def test_empty_query_yields_nothing(self):
        assert ArxivSource.build_query("   ") == ""
        assert ArxivSource().fetch("   ") == []


class TestFrameworkSafetyNet:
    """The cutoff is enforced after parsing, so a careless source cannot leak."""

    class LeakySource(Source):
        name = "leaky"
        tier = SourceTier.INDUSTRY_PRESS
        rate_limit_per_hour = 0

        def fetch(self, query, *, limit=25, as_of=None):
            # Deliberately ignores as_of.
            return [{"id": "future", "when": date(2030, 1, 1)},
                    {"id": "past", "when": date(2010, 1, 1)}]

        def parse(self, payload):
            return RawDoc(external_id=payload["id"], title=payload["id"],
                          body="", published_at=payload["when"])

    def test_future_documents_are_dropped(self):
        result = self.LeakySource().search("x", as_of=date(2015, 1, 1))
        ids = {d.external_id for d in result.docs}
        assert ids == {"past"}

    def test_undated_documents_are_dropped_under_a_cutoff(self):
        class Undated(self.LeakySource):
            def parse(self, payload):
                return RawDoc(external_id="undated", title="t", body="", published_at=None)

        assert Undated().search("x", as_of=date(2015, 1, 1)).docs == []

    def test_no_cutoff_keeps_everything(self):
        assert len(self.LeakySource().search("x").docs) == 2

    def test_malformed_record_does_not_abort_the_sweep(self):
        class Partly(self.LeakySource):
            def parse(self, payload):
                if payload["id"] == "future":
                    raise ValueError("malformed")
                return RawDoc(external_id=payload["id"], title="t", body="",
                              published_at=payload["when"])

        assert len(Partly().search("x").docs) == 1

    def test_fetch_failure_is_reported_not_raised(self):
        class Broken(self.LeakySource):
            def fetch(self, query, *, limit=25, as_of=None):
                raise ConnectionError("network down")

        r = Broken().search("x")
        assert not r.ok and "ConnectionError" in r.error

    def test_impermissible_source_refuses_to_run(self):
        class Forbidden(self.LeakySource):
            is_publicly_permitted = False

        r = Forbidden().search("x")
        assert not r.ok and "not permitted" in r.error


class TestMockSource:
    def test_returns_synthetic_companies(self):
        r = MockSource().search("nuclear")
        assert r.ok and r.docs

    def test_every_document_is_flagged_synthetic(self):
        for d in MockSource().search("").docs:
            assert d.raw.get("synthetic") is True

    def test_is_lowest_tier_so_it_can_never_be_evidence(self):
        assert not MockSource().tier.is_citable_evidence

    def test_output_is_deterministic(self):
        a = [d.external_id for d in MockSource().search("photonics").docs]
        b = [d.external_id for d in MockSource().search("photonics").docs]
        assert a == b


class TestSeries:
    def test_accelerating_bends_upward(self):
        s = make_series("X", "hiring", "accelerating", periods=18)
        early = sum(v for _, v in s[:6]) / 6
        late = sum(v for _, v in s[-3:]) / 3
        assert late > early * 1.5

    def test_declining_falls(self):
        s = make_series("X", "hiring", "declining", periods=18)
        assert sum(v for _, v in s[-3:]) / 3 < sum(v for _, v in s[:6]) / 6

    def test_deterministic(self):
        assert make_series("X", "m", "steady") == make_series("X", "m", "steady")

    def test_different_keys_differ(self):
        assert make_series("A", "m", "steady") != make_series("B", "m", "steady")


@needs_network
class TestLiveSources:
    def test_arxiv_current(self):
        r = ArxivSource().search("silicon photonics", limit=3)
        assert r.ok and r.docs

    def test_arxiv_historical_returns_old_papers(self):
        cutoff = date(2015, 1, 1)
        r = ArxivSource().search("solid state battery", limit=5, as_of=cutoff)
        assert r.docs, "historical query returned nothing"
        assert all(d.published_at <= cutoff for d in r.docs)

    def test_hackernews(self):
        r = HackerNewsSource().search("photonics", limit=3)
        assert r.ok
