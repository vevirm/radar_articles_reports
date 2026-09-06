import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_scan_v172050", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


def row(title, strand="A", link=None, new=False):
    return {
        "title": title,
        "date": "2026-09-01",
        "link": link or f"https://doi.org/10.5555/{title.lower().replace(' ', '-')}",
        "type": "peer-reviewed article",
        "source": "Research Policy",
        "source_tier": "Tier 2",
        "eu_relevance": "direct",
        "strand": strand,
        "summary": "European research and innovation policy evidence.",
        "new_this_scan": new,
    }


class CuratedCoreTests(unittest.TestCase):
    def test_packaged_radar_has_200_active_and_preserves_archive(self):
        data = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        self.assertEqual(data.get("active_core_limit"), 200)
        self.assertEqual(len(data.get("strand_a", [])) + len(data.get("strand_b", [])), 200)
        self.assertIsInstance(data.get("ab_archive"), list)
        self.assertGreater(len(data["ab_archive"]), 0)
        self.assertEqual(
            len(data["strand_a"]) + len(data["strand_b"]) + len(data["ab_archive"]),
            data.get("active_core_stats", {}).get("accepted_history_total"),
        )

    def test_archive_is_part_of_dedupe_memory(self):
        archived = row("Archived European research policy paper")
        previous = {"strand_a": [], "strand_b": [], "strand_c": [], "ab_archive": [archived]}
        ids, links, _signals, doi_titles = scan.known_sets_from_previous(previous)
        sid = scan.stable_item_identity(archived["title"], archived["link"])
        self.assertIn(sid, ids)
        self.assertIn(scan.normalized_link(archived["link"]), links)
        self.assertIn("title:" + scan.norm_title(archived["title"]), doi_titles)

    def test_rebalance_caps_active_without_losing_history_or_relabelling_archive_new(self):
        active_a = [row(f"A paper {i}", "A", new=(i == 0)) for i in range(6)]
        active_b = [row(f"B method {i}", "B") for i in range(3)]
        archived = [row(f"Archived paper {i}", "A", new=True) for i in range(4)]
        # Use a tiny deterministic core to test mechanics rather than the substantive gate.
        def sort_key(item, strand_hint=None):
            title = str(item.get("title", ""))
            # Higher number in title should rank first.
            try:
                n = int(title.rsplit(" ", 1)[-1])
            except Exception:
                n = 0
            return (-n, title)

        with mock.patch.object(scan, "ACTIVE_CORE_LIMIT", 5), \
             mock.patch.object(scan, "ACTIVE_CORE_B_SLOTS", 1), \
             mock.patch.object(scan, "curated_core_sort_key", side_effect=sort_key), \
             mock.patch.object(scan, "_saved_ab_high_confidence_precision_reject", return_value=False), \
             mock.patch.object(scan, "final_ab_candidate_worthiness", return_value=True), \
             mock.patch.object(scan, "eu_ri_centrality", return_value=(True, "title_eu_ri_central", ["eu", "research"])), \
             mock.patch.object(scan, "_active_core_a_title_central", return_value=True), \
             mock.patch.object(scan, "_method_matches", return_value=["strategic foresight"]):
            a, b, arc, stats = scan.rebalance_active_core(active_a, active_b, archived, "2026-09-06T00:00Z")
        self.assertEqual(len(a) + len(b), 5)
        self.assertEqual(len(b), 1)
        self.assertEqual(len(a) + len(b) + len(arc), 13)
        self.assertEqual(stats["accepted_history_total"], 13)
        self.assertTrue(all(not x.get("new_this_scan") for x in arc))

    def test_git_recovery_cannot_resurrect_old_large_active_corpus(self):
        current = {
            "first_scan_complete": True,
            "last_updated": "2026-09-06T05:11Z",
            "active_core_profile_version": scan.ACTIVE_CORE_PROFILE_VERSION,
            "strand_a": [row("Current core A")],
            "strand_b": [row("Current core B", "B")],
            "ab_archive": [dict(row("Already archived A"), archived_from_strand="A")],
            "strand_c": [],
        }
        recovered = {
            "first_scan_complete": True,
            "last_updated": "2026-09-06T04:00Z",
            "strand_a": [row("Current core A"), row("Old active A"), row("Already archived A")],
            "strand_b": [row("Current core B", "B"), row("Old active B", "B")],
            "strand_c": [],
        }
        with mock.patch.object(scan, "_saved_ab_high_confidence_precision_reject", return_value=False):
            merged = scan._merge_saved_snapshots(current, recovered)
        self.assertEqual([x["title"] for x in merged["strand_a"]], ["Current core A"])
        self.assertEqual([x["title"] for x in merged["strand_b"]], ["Current core B"])
        archived_titles = {x["title"] for x in merged["ab_archive"]}
        self.assertTrue({"Already archived A", "Old active A", "Old active B"}.issubset(archived_titles))


    def test_reader_contract_anchors_survive_rebalance_without_expanding_core(self):
        anchor = row("Anchored European research-system evidence", "A")
        anchor["active_core_anchor"] = True
        ordinary = [row(f"Ordinary paper {i}", "A") for i in range(8)]

        def sort_key(item, strand_hint=None):
            # Deliberately rank the anchor last: protection, not score, must keep it active.
            return (1 if item.get("active_core_anchor") else 0, item.get("title", ""))

        with mock.patch.object(scan, "ACTIVE_CORE_LIMIT", 5), \
             mock.patch.object(scan, "ACTIVE_CORE_B_SLOTS", 0), \
             mock.patch.object(scan, "curated_core_sort_key", side_effect=sort_key), \
             mock.patch.object(scan, "_saved_ab_high_confidence_precision_reject", return_value=False), \
             mock.patch.object(scan, "final_ab_candidate_worthiness", return_value=True), \
             mock.patch.object(scan, "eu_ri_centrality", return_value=(True, "title_eu_ri_central", ["eu", "research"])), \
             mock.patch.object(scan, "_active_core_a_title_central", return_value=True):
            a, b, arc, stats = scan.rebalance_active_core(ordinary + [anchor], [], [], "2026-09-06T00:00Z")
        self.assertEqual(len(a) + len(b), 5)
        self.assertTrue(any(x.get("active_core_anchor") for x in a))
        self.assertEqual(stats.get("reader_contract_anchors_active"), 1)
        self.assertEqual(len(a) + len(b) + len(arc), 9)

    def test_packaged_curated_core_preserves_existing_reader_products(self):
        import subprocess
        code = r"""
const D=require('./radar.json');
const S=require('./shocks/scenarios.js');
const V=require('./shocks/variants.js');
const P=require('./priorities/priorities.js');
const direct=S.buildDirect(D), reasoned=S.build(D), all=[...direct,...reasoned];
if(direct.length<3) process.exit(2);
if(reasoned.length<4) process.exit(3);
const pv=P.buildPriorityView(D,{limit:50});
if(pv.stats.risks<10 || pv.stats.opportunities<10 || pv.stats.externalShocks<1) process.exit(4);
for(const s of all){
  const v=V.build(D,s.id);
  if(!v || v.variants.length!==3 || v.forEvidence.length<3 || v.againstEvidence.length<2) process.exit(5);
}
"""
        subprocess.run(["node", "-e", code], cwd=ROOT, check=True, timeout=30)

    def test_active_to_archive_rotation_is_preservation_not_loss(self):
        old_a = row("Old active European research paper", "A")
        previous = {"strand_a": [old_a], "strand_b": [], "ab_archive": []}
        archived = dict(old_a)
        archived["archived_from_strand"] = "A"
        # Moving an accepted record out of the visible 200 must remain valid.
        scan.assert_accepted_ab_history_preserved(previous, [], [], [archived])

    def test_genuine_loss_from_active_and_archive_is_still_a_hard_failure(self):
        old_a = row("Irreplaceable European research paper", "A")
        previous = {"strand_a": [old_a], "strand_b": [], "ab_archive": []}
        with self.assertRaises(RuntimeError):
            scan.assert_accepted_ab_history_preserved(previous, [], [], [])

    def test_packaged_save_guard_is_archive_aware_and_legacy_workflow_tolerant(self):
        workflow = (ROOT / ".github" / "workflows" / "radar-scan.yml").read_text(encoding="utf-8")
        scanner_source = SCAN_PATH.read_text(encoding="utf-8")
        # Preferred releases carry the archive-aware save guard in YAML. GitHub's
        # browser uploader can retain an older hidden workflow, though, so this
        # regression must not make a live scan depend on hidden-file replacement.
        archive_aware_yaml = (
            "for key in ('strand_a', 'strand_b', 'ab_archive')" in workflow
            and "accepted A/B history lost" in workflow
        )
        if not archive_aware_yaml:
            # Recognised legacy workflow: it still has the single-output isolation
            # guard, while the scanner itself enforces active+archive preservation
            # before writing radar.json and marks the active-core rebalance as an
            # intentional precision cleanup for the stale YAML guard.
            self.assertIn("radar.json is the ONLY persistent output", workflow)
        self.assertIn("active_core_save_compat = bool(ACTIVE_CORE_LIMIT > 0)", scanner_source)
        self.assertIn("assert_accepted_ab_history_preserved(", scanner_source)
        self.assertIn("bool(precision_cleanup or active_core_save_compat)", scanner_source)

    def test_steady_state_source_expansion_is_not_a_four_month_bootstrap(self):
        previous = {
            "last_updated": "2026-09-06T05:11Z",
            "source_expansion_version": "older-target",
        }
        self.assertFalse(scan.CONFIG.get("force_backfill_on_source_expansion"))
        self.assertFalse(scan.needs_source_expansion_backfill(previous))


if __name__ == "__main__":
    unittest.main()
