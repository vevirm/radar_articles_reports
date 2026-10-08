"""A-first, C-secondary and B-supporting discovery; no quality-gate changes."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("a_first_scan", ROOT / "scripts/scan_radar.py")
scan = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class AFirstResearchRecoveryTests(unittest.TestCase):
    def test_research_prefix_executes_real_substantive_broad_and_system_research(self):
        prefix = scan.strand_a_first_query_prefix(
            16,
            ["evidence1", "evidence2", "evidence3"],
            ["a_broad1", "a_broad2", "a_broad3"],
            ["system1", "system2", "system3"],
            ["context1", "context2", "context3"],
            ["gap1", "gap2", "gap3"],
            ["strategic1", "strategic2", "strategic3"],
            ["explore1", "explore2", "explore3"],
        )
        self.assertEqual(prefix[:7], [
            "evidence1", "a_broad1", "system1", "context1", "gap1", "strategic1", "explore1"
        ])
        self.assertIn("evidence2", prefix[:14])
        self.assertIn("a_broad2", prefix[:14])

    def test_supplemental_b_does_not_take_over_extra_a_tail(self):
        s = (ROOT / "scripts/scan_radar.py").read_text(encoding="utf-8")
        fragment = s[s.index('        # The full-budget tail is Strand-A research recovery.'):
                     s.index('        continuation_news_bank = list(dict.fromkeys(')]
        self.assertIn('continuation_bank = interleaved_unique_batch(', fragment)
        self.assertNotIn('weighted_strand_query_bank(', fragment)
        self.assertNotIn('b_method_bank', fragment)

    def test_b_and_c_still_get_baseline_and_existing_quality_gate(self):
        cfg = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(cfg["strand_a_protected_scholarly_queries_per_source"], 30)
        self.assertGreaterEqual(cfg["b_method_protected_scholarly_queries_per_source"], 6)
        self.assertEqual(cfg["target_item_mix_mode"], "discovery_weights_no_release_cap")
        self.assertEqual(cfg["target_item_mix_weights"], {"A": 8, "B": 1, "C": 3})
        self.assertTrue(cfg["c_exceptional_release_enabled"])
        self.assertTrue(cfg["full_budget_continuation_enabled"])
        self.assertLessEqual(cfg["full_budget_continuation_max_waves"], 6)
        self.assertLessEqual(cfg["full_budget_continuation_max_waves"] * cfg["full_budget_continuation_stage_seconds"], 500)

    def test_a_source_first_rotates_without_repeat_before_new_targets(self):
        journals = ["A", "B", "C", "D"]
        chosen, cursor, _ = scan.rotating_batch_excluding(journals, 0, 3, ["A", "B"])
        self.assertEqual(chosen, ["C", "D"])
        self.assertEqual(cursor, 0)


if __name__ == '__main__':
    unittest.main()
