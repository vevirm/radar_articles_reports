"""V17.20.47 — fresh-start corpus reset and DOI-first citation snowballing.

Live failure being fixed: every recent scan reported ``seeds_planned: 20, seeds_resolved: 0``
because the seed pool was filled with Tier-1 institutional news pages (no DOI, not in
OpenAlex), while the accumulated 600-item corpus and deep rotation cursors kept the
scanner rediscovering known material. The reset keeps the most important 200 A/B items,
restarts discovery from the beginning and rebuilds snowballing from resolvable seeds.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import scan_radar as scan  # noqa: E402


def _item(title, *, strand="A", tier="Tier 2 trusted-publisher journal", typ="peer-reviewed article",
          link="", date="2026-08-01", summary=None, **extra):
    row = {
        "title": title, "strand": strand, "source_tier": tier, "type": typ,
        "link": link or f"https://example.org/{scan.norm_title(title).replace(' ', '-')}",
        "date": date, "eu_relevance": "direct", "authors": "A. Author, B. Author",
        "summary": summary if summary is not None else ("Substantive abstract about European research and innovation policy under geopolitical pressure. " * 4),
        "ri_evidence": ["research"], "eu_evidence": ["european"], "geo_evidence": [],
        "first_seen": "2026-08-01T00:00Z", "source": "Test Source",
    }
    row.update(extra)
    return row


class ImportanceRankingTests(unittest.TestCase):
    def test_admin_notices_rank_below_doi_backed_geopolitical_papers(self):
        today = dt.date(2026, 9, 6)
        paper = _item("Strategic dependencies of European semiconductor research on non-EU suppliers",
                      link="https://doi.org/10.1016/j.respol.2026.105001", a_route="explicit-geopolitics",
                      geo_evidence=["non-eu suppliers", "dependenc"])
        notice = _item("EU Mission Soil Board appoints new chair", tier="Tier 1", typ="research/policy paper",
                       link="https://era.gv.at/news-items/eu-mission-soil-board-appoints-new-chair",
                       summary="EU Mission Soil Board appoints new chair.")
        self.assertGreater(scan.corpus_reset_importance(paper, today), scan.corpus_reset_importance(notice, today) + 30)

    def test_curator_verified_material_is_protected(self):
        today = dt.date(2026, 9, 6)
        plain = _item("Plain paper")
        curated = _item("Curated paper", curator_primary_cell="rules-B", manual_ingest_ids=["m1"])
        self.assertGreater(scan.corpus_reset_importance(curated, today), scan.corpus_reset_importance(plain, today) + 20)


class ResetApplicationTests(unittest.TestCase):
    def _previous(self, n_a=30, n_b=6):
        a = []
        for i in range(n_a):
            if i % 3 == 0:
                a.append(_item(f"Administrative notice number {i} announces winners", tier="Tier 1",
                               typ="research/policy paper", link=f"https://era.gv.at/news-items/notice-{i}",
                               summary="short"))
            else:
                a.append(_item(f"European research paper {i} on strategic technology dependence",
                               link=f"https://doi.org/10.1000/paper.{i}", a_route="explicit-geopolitics",
                               geo_evidence=["dependence"]))
        b = [_item(f"Foresight method paper {i}", strand="B", tier="Tier 2 broad journal",
                   link=f"https://doi.org/10.2000/method.{i}") for i in range(n_b)]
        return {
            "strand_a": a, "strand_b": b, "strand_c": [], "frontier_evidence": [],
            "last_updated": "2026-09-05T00:00Z", "first_scan_complete": True,
            "source_expansion_version": scan.SOURCE_EXPANSION_VERSION,
            "scan_state": {
                "version": scan.INCREMENTAL_STATE_VERSION, "openalex_cursor": 216, "crossref_broad_cursor": 176,
                "backfill": {"openalex": True, "crossref_broad": True, "crossref_priority": True, "institutions": True},
                "completed_cycles": {"openalex": 4}, "cycle_failed": {"openalex": True},
                "institution_seen_fingerprints": {"https://x": "2026-09-01T00:00Z"},
                "result_depth": {"openalex": {"q": 7}}, "last_completed_at": "2026-09-05T00:00Z",
                "priority_people_openalex_author_ids": {"sepp hochreiter": "A5053148274"},
                "rule_fix_source_recovery_verified_complete": True,
            },
        }

    def test_keeps_top_items_resets_state_and_blocks_pruned(self):
        previous = self._previous()
        with mock.patch.object(scan, "CORPUS_RESET_PROFILE_VERSION", "test-epoch"), \
             mock.patch.object(scan, "CORPUS_RESET_KEEP_ITEMS", 12), \
             mock.patch.object(scan, "CORPUS_RESET_MIN_STRAND_B", 3), \
             mock.patch.object(scan, "_corpus_reset_matrix_cells", return_value={}):
            self.assertTrue(scan.needs_corpus_reset(previous))
            out, report = scan.apply_corpus_reset(previous, "2026-09-06T00:00Z", today=dt.date(2026, 9, 6))
            self.assertFalse(scan.needs_corpus_reset(out))
        self.assertEqual(len(out["strand_a"]) + len(out["strand_b"]), 12)
        self.assertGreaterEqual(len(out["strand_b"]), 3)
        self.assertEqual(report["pruned"], 36 - 12)
        self.assertEqual(report["version"], "test-epoch")
        titles = [x["title"] for x in out["strand_a"]]
        self.assertFalse(any("Administrative notice" in t for t in titles), titles)
        # discovery restarts from the beginning
        state = out["scan_state"]
        self.assertEqual(state["openalex_cursor"], 0)
        self.assertEqual(state["crossref_broad_cursor"], 0)
        self.assertFalse(any(state["backfill"].values()))
        self.assertFalse(any(state["cycle_failed"].values()))
        self.assertEqual(state["institution_seen_fingerprints"], {})
        self.assertEqual(state["result_depth"]["openalex"], {})
        self.assertEqual(out["source_expansion_version"], "")
        # harmless caches / scheduling / one-time markers survive
        self.assertEqual(state["last_completed_at"], "2026-09-05T00:00Z")
        self.assertEqual(state["priority_people_openalex_author_ids"], {"sepp hochreiter": "A5053148274"})
        self.assertTrue(state["rule_fix_source_recovery_verified_complete"])
        self.assertTrue(scan.scan_from_date(out, dt.date(2026, 9, 6))[1], "reset must trigger the bootstrap window")
        # pruned identities are remembered and refused on rediscovery
        with mock.patch.object(scan, "CORPUS_RESET_PROFILE_VERSION", "test-epoch"):
            blocked = scan.corpus_reset_blocked_identities(out)
        self.assertTrue(blocked)
        pruned_title = report["pruned_titles"][0]
        with mock.patch.object(scan, "CORPUS_RESET_BLOCKED_IDENTITIES", blocked):
            self.assertTrue(scan.corpus_reset_blocked({"title": pruned_title, "link": "https://other.example/x"}))
            self.assertFalse(scan.corpus_reset_blocked(out["strand_a"][0]))
            merged = scan.merge_corpus(out["strand_a"], [dict(_item(pruned_title, strand="A"))], "A", "2026-09-06T00:00Z")
            self.assertFalse(any(x["title"] == pruned_title for x in merged))

    def test_reset_is_idempotent_and_disabled_by_empty_marker(self):
        previous = self._previous()
        with mock.patch.object(scan, "CORPUS_RESET_PROFILE_VERSION", ""):
            self.assertFalse(scan.needs_corpus_reset(previous))
        with mock.patch.object(scan, "CORPUS_RESET_PROFILE_VERSION", "e1"):
            previous["corpus_reset"] = {"version": "e1"}
            self.assertFalse(scan.needs_corpus_reset(previous))
            previous["corpus_reset"] = {"version": "e0"}
            self.assertTrue(scan.needs_corpus_reset(previous))


class GitRecoveryEpochGuardTests(unittest.TestCase):
    def _saved(self, n, epoch=None, completed="2026-09-05T00:00Z"):
        data = {
            "strand_a": [_item(f"Paper {i}", link=f"https://doi.org/10.1000/p.{i}") for i in range(n)],
            "strand_b": [], "strand_c": [], "last_updated": completed, "first_scan_complete": True,
            "run_completed_at": completed,
            "scan_state": {"version": scan.INCREMENTAL_STATE_VERSION, "last_completed_at": completed},
        }
        if epoch:
            data["corpus_reset"] = {"version": epoch, "pruned_identities": []}
        return data

    def test_pre_reset_history_cannot_reinflate_reset_bundle(self):
        current = self._saved(3, epoch="e1", completed="2026-09-06T00:00Z")
        old_big = self._saved(40, epoch=None, completed="2026-09-05T23:00Z")
        with mock.patch.object(scan, "CORPUS_RESET_PROFILE_VERSION", "e1"), \
             mock.patch.object(scan, "run_trigger_label", return_value="push"), \
             mock.patch.object(scan, "_recover_radar_from_git", return_value=old_big), \
             tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "radar.json"
            path.write_text(json.dumps(current), encoding="utf-8")
            with mock.patch.object(scan, "OUT_PATH", path):
                loaded = scan.load_previous(allow_git_recovery=True)
        self.assertEqual(len(loaded["strand_a"]), 3)
        self.assertEqual(scan.corpus_reset_version_of(loaded), "e1")

    def test_old_bundle_cannot_overwrite_reset_repository(self):
        current = self._saved(40, epoch=None, completed="2026-09-04T00:00Z")
        reset_repo = self._saved(5, epoch="e1", completed="2026-09-06T00:00Z")
        with mock.patch.object(scan, "CORPUS_RESET_PROFILE_VERSION", "e1"), \
             mock.patch.object(scan, "run_trigger_label", return_value="push"), \
             mock.patch.object(scan, "_recover_radar_from_git", return_value=reset_repo), \
             tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "radar.json"
            path.write_text(json.dumps(current), encoding="utf-8")
            with mock.patch.object(scan, "OUT_PATH", path):
                loaded = scan.load_previous(allow_git_recovery=True)
        self.assertEqual(len(loaded["strand_a"]), 5)
        self.assertEqual(scan.corpus_reset_version_of(loaded), "e1")

    def test_same_epoch_history_still_merges(self):
        current = self._saved(3, epoch="e1", completed="2026-09-06T00:00Z")
        newer = self._saved(6, epoch="e1", completed="2026-09-06T01:00Z")
        with mock.patch.object(scan, "CORPUS_RESET_PROFILE_VERSION", "e1"), \
             mock.patch.object(scan, "run_trigger_label", return_value="push"), \
             mock.patch.object(scan, "_recover_radar_from_git", return_value=newer), \
             tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "radar.json"
            path.write_text(json.dumps(current), encoding="utf-8")
            with mock.patch.object(scan, "OUT_PATH", path):
                loaded = scan.load_previous(allow_git_recovery=True)
        self.assertEqual(len(loaded["strand_a"]), 6)


class SnowballSeedTests(unittest.TestCase):
    def _previous(self):
        rows = [
            _item(f"Institutional notice {i}", tier="Tier 1", typ="research/policy paper",
                  link=f"https://era.gv.at/news-items/notice-{i}", date="2026-09-0" + str(1 + i % 5))
            for i in range(25)
        ]
        rows += [
            _item(f"DOI paper {i}", link=f"https://doi.org/10.1000/doi.{i}", date="2026-07-0" + str(1 + i % 9))
            for i in range(30)
        ]
        return {"strand_a": rows}

    def test_seed_pool_is_doi_first_not_tier_one_news(self):
        with mock.patch.object(scan, "DATE_FLOOR", dt.date(2026, 5, 1)):
            seeds = scan._snowball_seed_pool(self._previous(), [], None)
        self.assertEqual(len(seeds), 20)
        self.assertTrue(all(x.get("_snowball_doi") for x in seeds), [x["title"] for x in seeds])
        self.assertFalse(any("Institutional notice" in x["title"] for x in seeds))

    def test_seed_pool_rotates_with_persisted_cursor_and_skips_recent_failures(self):
        state = {}
        with mock.patch.object(scan, "DATE_FLOOR", dt.date(2026, 5, 1)):
            first = scan._snowball_seed_pool(self._previous(), [], state)
            scan._snowball_advance_cursor(state, len(first))
            second = scan._snowball_seed_pool(self._previous(), [], state)
        self.assertEqual(state["citation_snowball"]["pool_size"], 30)
        self.assertEqual(state["citation_snowball"]["seed_cursor"], 20)
        self.assertNotEqual([x["title"] for x in first], [x["title"] for x in second])
        # a seed that just failed to resolve is not retried next scan
        dead = first[0]["_snowball_key"]
        state["citation_snowball"]["seed_cursor"] = 0
        state["citation_snowball"]["unresolvable"][dead] = dt.datetime.now(dt.timezone.utc).isoformat()
        with mock.patch.object(scan, "DATE_FLOOR", dt.date(2026, 5, 1)):
            third = scan._snowball_seed_pool(self._previous(), [], state)
        self.assertNotIn(dead, [x["_snowball_key"] for x in third])

    def test_batched_doi_resolution_feeds_shared_reference_anchors(self):
        previous = self._previous()
        state = {}
        works = {}
        for i in range(30):
            works[f"https://doi.org/10.1000/doi.{i}"] = {
                "id": f"https://openalex.org/W{i}", "doi": f"https://doi.org/10.1000/doi.{i}",
                "display_name": f"DOI paper {i}", "referenced_works": ["https://openalex.org/W9000", f"https://openalex.org/W{8000 + i}"],
            }

        class Resp:
            def __init__(self, payload, code=200):
                self._p, self.status_code = payload, code
            def json(self):
                return self._p

        calls = []

        def fake_get(path, params=None, timeout=None, **kw):
            calls.append(params)
            filt = str((params or {}).get("filter", ""))
            if filt.startswith("doi:"):
                dois = filt[4:].split("|")
                return Resp({"results": [works[d] for d in dois if d in works]})
            if filt.startswith("openalex:"):
                return Resp({"results": [{"id": "https://openalex.org/W9000", "display_name": "Shared anchor",
                                          "cited_by_count": 50, "publication_date": "2024-01-01"}]})
            if filt.startswith("cites:"):
                return Resp({"results": []})
            return Resp({}, 404)

        with mock.patch.object(scan, "openalex_get", side_effect=fake_get), \
             mock.patch.object(scan, "DATE_FLOOR", dt.date(2026, 5, 1)), \
             mock.patch.object(scan, "candidate_from_openalex", return_value=None):
            rows, stats = scan.collect_citation_snowball(previous, [], [], time.monotonic() + 30, {}, state)
        self.assertEqual(stats["seeds_planned"], 20)
        self.assertEqual(stats["seeds_batch_resolved"], 20)
        self.assertEqual(stats["seeds_resolved"], 20)
        self.assertEqual(stats["shared_references"], 1)
        self.assertEqual(stats["anchors_selected"], 1)
        self.assertEqual(stats["status"], "completed")
        self.assertEqual(sum(1 for p in calls if str(p.get("filter", "")).startswith("doi:")), 1, "one batched DOI request, not twenty")
        self.assertEqual(state["citation_snowball"]["seed_cursor"], 20)
        self.assertIn("https://openalex.org/W9000", state["citation_snowball"]["anchor_history"])
        self.assertEqual(len(state["citation_snowball"]["resolved"]), 20)

    def test_pinned_seed_without_doi_still_uses_title_resolver_and_reports_429(self):
        seed = {"title": "The Global Landscape of National AI Strategies", "date": "2026-07-28", "source_tier": "Tier 3",
                "type": "working paper", "eu_relevance": "direct", "link": "https://example.invalid/radu",
                "_snowball_pinned": True, "_snowball_doi": "", "_snowball_key": "title:x"}
        warnings = []
        with mock.patch.object(scan, "_snowball_seed_pool", return_value=[seed]), \
             mock.patch.object(scan, "_snowball_resolve_seed", side_effect=scan.OpenAlexRateLimit("429")):
            rows, stats = scan.collect_citation_snowball({}, [], warnings, time.monotonic() + 30, {}, {})
        self.assertEqual(rows, [])
        self.assertEqual(stats["status"], "blocked_openalex_429")


class PackagingTests(unittest.TestCase):
    def test_release_markers_and_shipped_radar_are_reset(self):
        version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
        cfg = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        self.assertIn(version, cfg.get("admission_profile", ""))
        self.assertEqual(cfg.get("corpus_reset_keep_items"), 200)
        self.assertTrue(cfg.get("corpus_reset_profile_version"))
        self.assertTrue(cfg.get("citation_snowball_require_doi"))
        radar = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        self.assertEqual(scan.corpus_reset_version_of(radar), cfg["corpus_reset_profile_version"])
        self.assertLessEqual(len(radar["strand_a"]) + len(radar["strand_b"]), 200)
        self.assertFalse(scan.needs_corpus_reset(radar))
        self.assertFalse(any(radar["scan_state"]["backfill"].values()))
        wf = (ROOT / ".github" / "workflows" / "radar-scan.yml").read_text(encoding="utf-8")
        self.assertIn("corpus_reset_this_run", wf)


if __name__ == "__main__":
    unittest.main()
