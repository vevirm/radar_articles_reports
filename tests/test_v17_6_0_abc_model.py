from pathlib import Path
import json
import subprocess
import sys
import types
import unittest

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules['feedparser'] = types.ModuleType('feedparser')

from scripts import scan_radar as scanner

ROOT = Path(__file__).resolve().parents[1]


class ABCModelTests(unittest.TestCase):
    def test_A_rejects_generic_agritourism_bibliometrics(self):
        ev = scanner.gate_scope(
            'The Digital Transformation of Agritourism (2010–2025): A Bibliometric Analysis',
            'This bibliometric study maps digital adoption, tourism research and sustainability themes across countries.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['a_pass'])

    def test_A_rejects_horizon_funding_acknowledgement_as_scope(self):
        ev = scanner.gate_scope(
            'Overcoming challenges for second-life applications for battery packs',
            'Geopolitical uncertainty may increase household demand for backup batteries. '
            'This paper was funded by the European Union Horizon Europe research and innovation programme under grant agreement No 123.',
            '', 1, source_kind='institutional'
        )
        self.assertFalse(ev['a_pass'])

    def test_A_rejects_generic_AI_national_security_with_EU_as_one_case(self):
        ev = scanner.gate_scope(
            'Artificial Intelligence and National Security: Military Power, Digital Sovereignty, and Great-Power Competition',
            'The study compares military AI in the United States, China, Russia and the European Union and examines national security and digital sovereignty.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['a_pass'])

    def test_A_accepts_EU_research_security(self):
        ev = scanner.gate_scope(
            'Governing knowledge, shaping Europe: research security in the EU geopolitical turn',
            'The article examines EU research security policy, foreign interference and restrictions on international scientific collaboration under geopolitical competition.',
            '', 2, source_kind='scholarly'
        )
        self.assertTrue(ev['a_pass'])

    def test_A_accepts_FP10_geopolitics(self):
        ev = scanner.gate_scope(
            'Globalising FP10: engagement with associated countries',
            'The European Union is designing FP10, the next research and innovation framework programme, amid heightened geopolitical tension and economic-security concerns about international cooperation.',
            '', 1, source_kind='institutional'
        )
        self.assertTrue(ev['a_pass'])
        self.assertFalse(ev['b_pass'])

    def test_A_accepts_researcher_mobility_as_geopolitical_RI_channel(self):
        ev = scanner.gate_scope(
            'The Fifth Freedom: researcher mobility in Europe',
            'EU Member States face barriers to researcher mobility and retention that contribute to research brain drain and weaken European research capacity.',
            '', 1, source_kind='institutional'
        )
        self.assertTrue(ev['a_pass'])
        self.assertIn('research-talent allocation / brain drain', ev['geo_evidence'])

    def test_B_rejects_Delphi_application_to_medical_barriers(self):
        ev = scanner.gate_scope(
            'Challenges and barriers to musculoskeletal injury research in sub-Saharan Africa',
            'Methods We conducted a three-stage modified Delphi study. Consensus was reached on funding, workloads and data collection barriers.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['b_pass'])

    def test_B_accepts_method_for_public_technology_futures(self):
        ev = scanner.gate_scope(
            'Evaluating horizon-scanning methods for public technology policy',
            'This study compares horizon scanning methods, evaluation criteria and bias controls for public technology policy. It proposes a framework for integrating weak signals with strategic intelligence under uncertainty.',
            '', 2, source_kind='scholarly'
        )
        self.assertTrue(ev['b_pass'])
        self.assertEqual(ev['b_route'], 'future-of-A-method')

    def test_B_accepts_general_methodological_foresight_paper(self):
        ev = scanner.gate_scope(
            'Comparing horizon-scanning methods for strategic foresight',
            'We develop and benchmark a methodology for horizon scanning, comparing weak-signal detection protocols and validation procedures under deep uncertainty.',
            '', 2, source_kind='scholarly'
        )
        self.assertTrue(ev['b_pass'])


    def test_B_rejects_methodological_application_even_when_future_oriented(self):
        ev = scanner.gate_scope(
            'Using a Delphi methodology to identify future university workforce challenges',
            'We conducted a modified Delphi study to identify future workforce challenges and rank expert priorities. The existing Delphi technique was applied in three rounds.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['b_pass'])

    def test_B_accepts_new_reusable_method_even_if_original_case_is_not_RI(self):
        ev = scanner.gate_scope(
            'A novel horizon-scanning protocol for strategic uncertainty',
            'We develop a new horizon-scanning protocol that combines weak-signal coding with cross-impact analysis. The protocol is designed as a reusable framework across policy domains and can be adapted to emerging technology and innovation questions.',
            '', 2, source_kind='scholarly'
        )
        self.assertTrue(ev['b_pass'])

    def test_B_rejects_validation_only_of_existing_method(self):
        ev = scanner.gate_scope(
            'Validation of a Delphi method for technology forecasting',
            'This study validates an existing Delphi protocol for technology forecasting against a historical expert panel. It does not develop, adapt or extend the method.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['b_pass'])

    def test_B_rejects_case_that_only_uses_scenario_method(self):
        ev = scanner.gate_scope(
            'Lithium pathways under geopolitical fragmentation',
            'The study uses scenario planning to compare three lithium demand pathways and reports the resulting material-security outcomes for Europe.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['b_pass'])

    def test_C_requires_weak_signal_character(self):
        self.assertTrue(scanner.weak_signal_candidate_text(
            'EU first quantum regulation delayed by six months',
            'The timetable has been postponed while officials reconsider the scope.'
        ))
        self.assertFalse(scanner.weak_signal_candidate_text(
            'Japan formally joins Horizon Europe as associated country',
            'The association agreement is now in force.'
        ))

    def test_C_never_anchors_to_B(self):
        news = [{
            'headline': 'German startup begins testing a new research-security screening tool',
            'source': 'Test News', 'date': '2026-08-23T08:00Z', 'link': 'https://example.test/signal',
            '_desc': 'A German startup begins testing a pilot tool for university research security.',
            '_themes': ['research security / foreign interference'],
            '_entities': ['research security'],
        }]
        b = [{
            'title': 'A methodology for research-security horizon scanning', 'source': 'Test',
            'date': '2026-08-20', 'strand': 'B', 'summary': 'Methodology for research security horizon scanning.'
        }]
        self.assertEqual(scanner.anchor_news(news, []), [])
        # Passing B where A is expected must not change the result because the function is A-only by contract.
        self.assertEqual(scanner.anchor_news(news, []), [])

    def test_C_dedupes_near_identical_event_coverage(self):
        a = {'headline': 'Japan officially joins Horizon Europe research programme', 'source': 'A'}
        b = {'headline': 'Japan formally joins Horizon Europe as associated country', 'source': 'B'}
        self.assertTrue(scanner.signals_near_duplicate(a, b))

    def test_frontier_ignores_strand_B_method_papers(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data={strand_a:[],strand_b:[{title:'Research security foresight method',summary:'A methodology for horizon scanning research security and international collaboration risks in Europe.',source:'Test',date:'2026-08-20',strand:'B',eu_relevance:'derived'}],strand_c:[]};
const v=F.buildFrontier(data,{now:'2026-08-23T08:00:00Z'});
console.log(JSON.stringify({signals:v.signals.length,evidenceTotal:v.stats.evidenceTotal}));
'''
        out = json.loads(subprocess.run(['node','-e',script], cwd=ROOT, text=True, capture_output=True, check=True).stdout)
        self.assertEqual(out['signals'], 0)
        self.assertEqual(out['evidenceTotal'], 0)

    def test_quality_change_preserves_rotation_cursors(self):
        prev={'quality_profile_version':'old','scan_state':{
            'version':scanner.INCREMENTAL_STATE_VERSION,
            'source_expansion_version':scanner.SOURCE_EXPANSION_VERSION,
            'openalex_cursor':20,'crossref_broad_cursor':121,'crossref_priority_cursor':270,
            'strand_b_method_cursor':6,'institution_cursor':54,'frontier_gap_cursor':1,
            'frontier_gap_query_cursors':{},'frontier_gap_source_cursors':{},
            'result_depth':{},'backfill':{},'completed_cycles':{},'cycle_failed':{}
        }}
        state=scanner.initial_scan_state(prev)
        self.assertEqual(state['openalex_cursor'],20)
        self.assertEqual(state['crossref_broad_cursor'],121)
        self.assertEqual(state['crossref_priority_cursor'],270)
        self.assertEqual(state['strand_b_method_cursor'],6)
        self.assertEqual(state['institution_cursor'],54)
        self.assertEqual(state['frontier_gap_cursor'],1)


if __name__ == '__main__':
    unittest.main()
