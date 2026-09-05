import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_scan_v172025', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class RotationAndPrecisionTests(unittest.TestCase):
    def test_generic_europe_social_policy_does_not_enter_strand_a(self):
        ev = scan.gate_scope(
            'Addressing poverty and social exclusion: a comparative study of 15 social programs across Europe and the Americas',
            'The study compares 15 social programs in Europe and the Americas. The programs were selected for social relevance, innovation and recognition and form part of a broader research program.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['a_pass'])

    def test_generic_eu_ri_project_without_geopolitical_mechanism_fails(self):
        ev = scan.gate_scope(
            'Advancing the WEFE nexus: Expert insights on implementation and challenges',
            'The analysis examines implementation in European research and innovation projects and interviews project coordinators about governance and analytical challenges.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['a_pass'])

    def test_real_eu_ri_geopolitical_source_still_passes(self):
        ev = scan.gate_scope(
            'Research security in European universities under US-China technology competition',
            'European universities face research-security constraints as US-China technology competition changes scientific collaboration, technology access and research capacity.',
            '', 2, source_kind='scholarly'
        )
        self.assertTrue(ev['a_pass'])
        self.assertIn(ev['a_route'], {'explicit-geopolitics', 'triangulated-strategic-context'})

    def test_securitisation_is_recognised_as_geopolitical_context(self):
        ev = scan.gate_scope(
            'Between Weltoffenheit and securitisation: Germany’s science policy towards the People’s Republic of China',
            'The article examines German science policy toward China and how security concerns reshape research cooperation and university policy.',
            '', 2, source_kind='scholarly'
        )
        self.assertTrue(ev['a_pass'])

    def test_source_first_attention_rotates_instead_of_full_census(self):
        cfg = scan.CONFIG
        self.assertFalse(cfg.get('crossref_full_source_census_each_scan'))
        self.assertLess(cfg.get('crossref_source_first_journals_per_scan', 999), len(cfg.get('crossref_priority_journals', [])))
        self.assertFalse(cfg.get('institution_full_census_each_scan'))
        self.assertLess(cfg.get('institution_sources_per_scan', 999), len(cfg.get('institution_sources', [])))

    def test_low_yield_cursor_can_wrap_without_repeating_completed_slice(self):
        bank = [f'q{i}' for i in range(6)]
        planned, next_cursor, wrapped = scan.rotating_batch_excluding(bank, 4, 4, set())
        self.assertEqual(planned, ['q4', 'q5', 'q0', 'q1'])
        self.assertTrue(wrapped)
        state = {}
        committed = scan.commit_planned_cursor_if_executed(state, 'cursor', 4, planned, next_cursor, set(planned))
        self.assertEqual(committed, 2)

    def test_one_logical_cycle_even_if_browser_upload_leaves_legacy_workflow(self):
        workflow = (ROOT / '.github/workflows/radar-scan.yml').read_text(encoding='utf-8')
        # Preferred deployment: one fixed four-hour workflow with no second GitHub rescue.
        # GitHub's browser uploader can, however, leave the hidden .github directory at an
        # older revision while uploading the visible scanner/tests.  That must not make the
        # regression suite block the evidence scan.  In the legacy case the scanner's
        # compatibility layer aligns the old six-hour due gate to the next four-hour slot,
        # and scanner output explicitly disables the old external rescue dispatch.
        if "cron: '17 0,4,8,12,16,20 * * *'" in workflow:
            self.assertNotIn('Launch one fresh 20-minute rescue scan', workflow)
            self.assertNotIn('/actions/workflows/radar-scan.yml/dispatches', workflow)
        else:
            self.assertTrue(scan.legacy_workflow_schedule_compatibility_active(workflow))
            self.assertIn("cron: '17 * * * *'", workflow)
            self.assertIn('age_hours >= 6.0', workflow)
        # In both deployments, low-yield continuation belongs inside scan_radar.py.
        # If the stale workflow still contains its old dispatch step, this false flag makes
        # that step calculate dispatch=false after the scanner completes.
        self.assertFalse(scan.CONFIG.get('low_yield_full_rescue_run_enabled'))
        self.assertGreaterEqual(scan.CONFIG.get('low_yield_fresh_rotation_max_waves', 0), 2)

    def test_current_packaged_corpus_does_not_keep_three_known_false_positives(self):
        doc = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        titles = {str(x.get('title', '')).lower() for x in doc.get('strand_a', []) if isinstance(x, dict)}
        self.assertFalse(any('addressing poverty and social exclusion' in t for t in titles))
        self.assertFalse(any('advancing the wefe nexus' in t for t in titles))
        self.assertFalse(any('dramatherapists in writing their first clinical case study' in t for t in titles))


if __name__ == '__main__':
    unittest.main()
