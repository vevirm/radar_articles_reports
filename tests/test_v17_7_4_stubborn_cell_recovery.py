import json
import subprocess
import sys, types
import unittest
from pathlib import Path

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    mod = types.ModuleType('feedparser')
    mod.parse = lambda *a, **k: types.SimpleNamespace(entries=[])
    sys.modules['feedparser'] = mod

from scripts import scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class StubbornCellRecoveryTests(unittest.TestCase):
    def test_current_state_does_not_force_opening_cells(self):
        proc = subprocess.run(
            ['node', str(ROOT / 'scripts' / 'frontier_coverage.js')],
            input=(ROOT / 'radar.json').read_text(encoding='utf-8'),
            text=True, capture_output=True, check=True,
        )
        payload = json.loads(proc.stdout)
        empty = {k for k, v in payload['counts'].items() if v == 0}
        self.assertTrue({'knowledge-A','infrastructure-A','conversion-A','rules-A'}.issubset(empty))
        self.assertGreater(payload['counts'].get('conversion-C', 0), 0)

    def test_matrix_depth_recomputes_and_reallocates_during_scan(self):
        scanner = (ROOT / 'scripts' / 'scan_radar.py').read_text(encoding='utf-8')
        self.assertIn('Matrix reallocated after wave', scanner)
        self.assertIn('provisional_frontier_document', scanner)
        self.assertEqual(sr.CONFIG['frontier_gap_recompute_every_n_waves'], 1)

    def test_stubborn_recovery_is_matrix_only_and_historical(self):
        self.assertTrue(sr.CONFIG['frontier_stubborn_recovery_enabled'])
        self.assertGreaterEqual(sr.CONFIG['frontier_stubborn_recovery_lookback_months'], 12)
        self.assertGreaterEqual(sr.CONFIG['frontier_stubborn_recovery_seconds'], 180)
        scanner = (ROOT / 'scripts' / 'scan_radar.py').read_text(encoding='utf-8')
        self.assertIn('matrix-only evidence search', scanner)
        self.assertIn('frontier_evidence', scanner)

    def test_frontier_accepts_matrix_only_brain_drain_evidence(self):
        payload = {
            'strand_a': [], 'strand_b': [], 'strand_c': [],
            'frontier_evidence': [{
                'title': 'Choose Europe: Research Careers, Brain Drain and Policy Lessons from the CESAER Survey',
                'source': 'European Review', 'date': '2026-04-01', 'strand': 'A',
                'eu_relevance': 'direct',
                'summary': 'Europe faces a persistent research brain drain. Researchers leave European universities and the loss of research talent undermines scientific capacity and global competitiveness.',
                'relevance_note': 'Direct EU relevance; research talent and brain drain reduce European research capacity and competitiveness.'
            }]
        }
        # frontier.js needs the shared insight helper in Node exactly as the page does.
        script = r"""
const fs=require('fs');
global.RadarInsights=require('./briefing/insights.js');
const F=require('./frontier/frontier.js');
const d=JSON.parse(fs.readFileSync(0,'utf8'));
const v=F.buildFrontier(d,{now:'2026-08-23T19:00:00Z'});
console.log(JSON.stringify({d:v.cells.knowledge.D.length,t:v.cells.knowledge.D.map(x=>x.title)}));
"""
        proc = subprocess.run(['node','-e',script], cwd=ROOT, input=json.dumps(payload), text=True, capture_output=True, check=True)
        out=json.loads(proc.stdout)
        self.assertEqual(out['d'], 1)
        self.assertTrue(any('brain drain' in t.lower() for t in out['t']))

    def test_talent_sources_and_direct_institutional_signal_lane_exist(self):
        domains={x['domain'] for x in sr.CONFIG['institution_sources']}
        self.assertIn('interface-eu.org', domains)
        self.assertIn('marie-sklodowska-curie-actions.ec.europa.eu', domains)
        self.assertIn('interface-eu.org', sr.CONFIG['frontier_gap_institution_sources']['knowledge-D'])
        self.assertTrue(any('Choose Europe research careers brain drain' in q for q in sr.CONFIG['frontier_gap_scholarly_queries']['knowledge-D']))
        scanner=(ROOT/'scripts'/'scan_radar.py').read_text(encoding='utf-8')
        self.assertIn('INSTITUTION_SIGNAL_CANDIDATES', scanner)

    def test_versions_bumped_without_ab_recall_reset(self):
        self.assertEqual(sr.CONFIG['recall_profile_version'], 'v17.7.2-source-first-contextual-recall')
        self.assertEqual(sr.CONFIG['allocation_profile_version'], 'v17.8.1-risk-weighted-frontier')
        self.assertEqual(sr.CONFIG['signal_discovery_version'], 'v17.7.4-direct-institutional-signals')


if __name__ == '__main__':
    unittest.main()
