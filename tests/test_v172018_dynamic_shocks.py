import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from shock_inference import refresh_shock_inference


def row(title, source, summary, *, new=False, tier='Tier 1', typ='institutional report', link=''):
    return {
        'title': title,
        'source': source,
        'summary': summary,
        'source_tier': tier,
        'type': typ,
        'link': link or f'https://example.test/{abs(hash((title, source)))%1000000}',
        'date': '2026-09-01',
        'new_this_scan': new,
    }


class DynamicShockInferenceTests(unittest.TestCase):
    def fixture(self):
        return {
            'strand_a': [
                row('European Biotech Act', 'European Commission', 'Europe is expanding biotechnology and clinical research capacity.'),
                row('Biosecurity governance in Europe', 'Research Policy', 'Biotechnology is increasingly dual-use and research security rules are tightening.', tier='Tier 2 priority journal', typ='peer-reviewed article'),
                row('New dual-use biotechnology interoperability paper', 'Science and Public Policy', 'New evidence links biotechnology, biosecurity, dual-use research and research security.', new=True, tier='Tier 2 priority journal', typ='peer-reviewed article'),
                row('EU research security framework', 'Council of the European Union', 'Research security and knowledge security can narrow access to sensitive and dual-use research.'),
                row('Open biotech infrastructure', 'European Commission', 'European capacity building and resilient shared research infrastructure can mitigate disruption.'),
            ],
            'strand_b': [],
            'strand_c': [],
            'strategic_pathways': [],
        }

    def test_fresh_bridge_creates_new_emergent_shock(self):
        state = refresh_shock_inference(self.fixture(), {}, '2026-09-03T20:00:00Z')
        self.assertGreaterEqual(state['new_count'], 1)
        shock = next(x for x in state['dynamic_shocks'] if x['id'] == 'emergent:biotech:security_reclassification')
        self.assertEqual(shock['status'], 'new')
        self.assertTrue(shock['new_this_scan'])
        self.assertGreaterEqual(shock['best_quality'], 90)
        self.assertGreaterEqual(len({x['source'] for x in shock['support']}), 3)
        self.assertTrue(any(x['new_this_scan'] for x in shock['support']))

    def test_later_evidence_updates_existing_shock_instead_of_calling_it_new(self):
        first_data = self.fixture()
        first = refresh_shock_inference(first_data, {}, '2026-09-03T20:00:00Z')
        second_data = copy.deepcopy(first_data)
        for x in second_data['strand_a']:
            x['new_this_scan'] = False
        second_data['strand_a'].append(
            row('Clinical biosecurity access restrictions', 'OECD', 'A new study links biotechnology research access, biosecurity and research security screening.', new=True)
        )
        second = refresh_shock_inference(second_data, first, '2026-09-04T00:00:00Z')
        shock = next(x for x in second['dynamic_shocks'] if x['id'] == 'emergent:biotech:security_reclassification')
        self.assertEqual(second['new_count'], 0)
        self.assertGreaterEqual(second['updated_count'], 1)
        self.assertEqual(shock['status'], 'updated')
        self.assertTrue(shock['updated_this_scan'])
        self.assertFalse(shock['new_this_scan'])

    def test_external_shock_page_exposes_new_and_updated_states(self):
        html = (ROOT / 'shocks' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Emergent inferred shocks', html)
        self.assertIn('new ·', html)
        self.assertIn('updated ·', html)
        self.assertIn("RadarShockScenarios.buildDynamic", html)
        self.assertIn("s.updatedThisScan?'updated'", html)

    def test_dynamic_shocks_have_variants_and_counter_evidence_support(self):
        js = """
const fs=require('fs');
const S=require('./shocks/scenarios.js');
const V=require('./shocks/variants.js');
const D=JSON.parse(fs.readFileSync('radar.json','utf8'));
const xs=S.buildDynamic(D);
if(!xs.length) process.exit(2);
const v=V.build(D,xs[0].id);
if(!v || !Array.isArray(v.variants) || v.variants.length!==3) process.exit(3);
if(!Array.isArray(v.forEvidence) || !Array.isArray(v.againstEvidence)) process.exit(4);
"""
        subprocess.run(['node', '-e', js], cwd=ROOT, check=True, timeout=20)

    def test_scanner_refreshes_shock_registry_after_every_scan(self):
        scanner = (ROOT / 'scripts' / 'scan_radar.py').read_text(encoding='utf-8')
        self.assertIn('refresh_shock_inference', scanner)
        self.assertIn('inferred_shocks_new_this_run', scanner)
        self.assertIn('inferred_shocks_updated_this_run', scanner)


if __name__ == '__main__':
    unittest.main()
