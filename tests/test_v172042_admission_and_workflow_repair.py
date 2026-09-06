import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_scan_v172042", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class AdmissionRecallRepairTests(unittest.TestCase):
    def test_recording_and_centrality_vocabularies_cannot_drift_again(self):
        self.assertTrue(set(scan.A_RI_CORE).issubset(set(scan.A_CENTRAL_RI_TERMS)))
        self.assertTrue(set(scan.A_TECH_RI_MECHANISMS).issubset(set(scan.A_CENTRAL_TECH_RI_MECHANISMS)))

    def test_eic_tech_report_deep_tech_stays_in(self):
        ev = scan.gate_scope(
            "EIC Tech Report 2026 identifies 25 emerging deep tech signals to support Europe’s strategic autonomy and resilience",
            "The signals identify emerging deep technologies that may shape Europe’s future innovation, industrial and market capabilities and support strategic autonomy and resilience.",
            "", 1, source_kind="general",
        )
        self.assertTrue(ev["a_pass"])
        self.assertTrue(ev["centrality_pass"])
        self.assertIn("deep tech", [str(x).lower() for x in ev["ri_evidence"]])

    def test_eic_impact_report_deep_tech_stays_in_without_geopolitical_wording(self):
        ev = scan.gate_scope(
            "EIC Impact Report 2026: Europe strengthens its position as a global deep tech scaling hub",
            "The report shows growing evidence that Europe is strengthening its ability to scale deep tech companies into global players, with increasing cross-border scaling across Member States.",
            "", 1, source_kind="general",
        )
        self.assertTrue(ev["a_pass"])
        self.assertEqual(ev["a_route"], "eu-ri-system-relevance")
        self.assertTrue(ev["centrality_pass"])

    def test_horizon_association_joint_committee_is_governance_evidence(self):
        title = "2nd Horizon Europe association Joint Committee meeting between Canada and the European Union"
        abstract = (
            "The agenda reviewed implementation of the agreement, reciprocal access to Canadian R&I programs, "
            "the financial contribution mechanism, participation in Horizon Europe governance structures and the "
            "Horizon Europe Work Programme 2026-27."
        )
        ok, reason, _ = scan.eu_ri_centrality(title, abstract, "", "general")
        self.assertTrue(ok, reason)
        ev = scan.gate_scope(title, abstract, "", 1, source_kind="general")
        self.assertTrue(ev["a_pass"])

    def test_routine_event_recap_stays_out(self):
        ok, reason, _ = scan.eu_ri_centrality(
            "Commission hosts research and innovation workshop in Brussels",
            "Participants exchanged views and networked during the event.",
            "", "general",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "event_recap_not_substantive_evidence")

    def test_stale_top_level_marker_closes_already_cycled_family_backfill(self):
        previous = {
            "last_updated": "2026-09-05T14:00:00Z",
            "source_expansion_version": "older-completion-marker",
            "recall_profile_version": scan.RECALL_PROFILE_VERSION,
            "scan_state": {
                "version": scan.INCREMENTAL_STATE_VERSION,
                "source_expansion_version": scan.SOURCE_EXPANSION_VERSION,
                "backfill": {
                    "openalex": True,
                    "crossref_broad": False,
                    "crossref_priority": True,
                    "institutions": True,
                },
                "completed_cycles": {
                    "openalex": 4, "crossref_broad": 5, "crossref_priority": 3, "institutions": 42,
                },
                "cycle_failed": {
                    "openalex": False, "crossref_broad": False, "crossref_priority": False, "institutions": False,
                },
            },
        }
        state = scan.initial_scan_state(previous)
        # The family has already completed multiple cycles under the current expansion target.
        # A stale top-level completion marker must not keep reopening a four-month migration forever.
        self.assertEqual(
            state["backfill"],
            {"openalex": True, "crossref_broad": True, "crossref_priority": True, "institutions": True},
        )
        self.assertTrue(state.get("source_expansion_legacy_completion_migrated"))
        self.assertFalse(state.get("recall_reset_this_run"))


class WorkflowRepairTests(unittest.TestCase):
    def test_workflow_contract_never_blocks_scanner_on_stale_hidden_yaml(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_workflow_contract.py")],
            cwd=ROOT, text=True, capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        checker = (ROOT / "scripts" / "check_workflow_contract.py").read_text(encoding="utf-8")
        self.assertIn('"--strict"', checker)
        self.assertIn("Compatibility mode: workflow mismatches are warnings", checker)

    def test_release_has_version_config_and_test_marker(self):
        version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^v17\.20\.\d+$")
        cfg = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        self.assertIn(version, cfg.get("admission_profile", ""))
        self.assertIn(f"# {version}", (ROOT / "PATCH_NOTES.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
