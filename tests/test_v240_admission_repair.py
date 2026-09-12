from pathlib import Path
import importlib.util, json, sys, unittest

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'scripts'/'scan_radar.py'
spec=importlib.util.spec_from_file_location('radar_v240_contract', PATH)
S=importlib.util.module_from_spec(spec); sys.modules[spec.name]=S; spec.loader.exec_module(S)

class V240AdmissionRepairTests(unittest.TestCase):
    def test_explicit_eu_programme_counts_wherever_it_occurs(self):
        rel,hits=S.eu_evidence('Research security and scientific capability', '', 'This report analyses DG RTD and the Framework Programme for strategic research capacity.')
        self.assertEqual(rel,'direct'); self.assertTrue(hits)

    def test_single_member_state_adjective_is_not_direct_eu_scope(self):
        rel,_=S.eu_evidence('Knowledge transfer through German universities', 'We study university-industry collaboration and innovation performance.', '')
        self.assertNotEqual(rel,'direct')


    def test_short_plainly_english_ri_record_is_not_rejected_for_missing_language_metadata(self):
        title='European research infrastructure under geopolitical competition'
        text=title+'. This paper analyses EU research infrastructure, strategic dependencies, foreign technology access and research capacity.'
        self.assertTrue(S.english_record_ok(text, title=title))

    def test_configured_news_source_can_supply_independent_c(self):
        self.assertTrue(S.trusted_independent_c_source('Euractiv','euractiv.com','https://www.euractiv.com/example'))
        self.assertTrue(S.trusted_independent_c_source('Reuters','reuters.com','https://www.reuters.com/example'))
        self.assertFalse(S.trusted_independent_c_source('Random Blog','random.example','https://random.example/post'))
        configured={str(x.get('domain','')) for x in S.CONFIG.get('news_sources',[]) if isinstance(x,dict)}
        self.assertNotIn('blogs.lse.ac.uk', configured)
        self.assertNotIn('bruegel.org', configured)
        self.assertIn('sciencebusiness.net', configured)
        self.assertIn('ft.com', configured)

    def test_project_word_does_not_kill_strategic_analysis_title(self):
        title='Project-based funding and strategic autonomy in European research'
        self.assertIsNone(S.document_exclusion_reason(title, 'Analysis of research funding, strategic autonomy and European research capacity.'))


    def test_formally_tabled_eu_proposal_can_be_c_but_generic_plan_cannot(self):
        self.assertTrue(S.formal_proposal_is_public_signal(
            'The European Commission published a proposal for new research-security screening rules.',
            source='Reuters', link='https://www.reuters.com/example'))
        self.assertFalse(S.formal_proposal_is_public_signal(
            'Europe should consider a plan to strengthen research security.',
            source='Reuters', link='https://www.reuters.com/example'))

    def test_formally_tabled_proposal_survives_as_independent_c(self):
        text=('European Commission publishes proposal for research-security screening of foreign partnerships. '
              'The European Commission published a proposal for screening foreign participation in EU research programmes '
              'amid technology leakage and geopolitical competition.')
        news=[{
            'headline':'European Commission publishes proposal for research-security screening of foreign partnerships',
            '_desc':'The European Commission published a proposal for screening foreign participation in EU research programmes amid technology leakage and geopolitical competition.',
            'source':'Reuters','source_domain':'reuters.com','link':'https://www.reuters.com/example',
            'date':'2026-09-09T08:00Z','_themes':S.themes_for(text),
            '_entities':S.distinct_matches(text, S.ENTITY_TERMS+S.GEO_ACTORS),
            '_formal_proposal_signal':True,
        }]
        out=S.anchor_news(news, [], allow_unanchored=True)
        self.assertEqual(len(out),1)
        self.assertEqual(out[0].get('event_status'),'PROPOSED')
        self.assertEqual(out[0].get('anchor_status'),'unanchored')


    def test_old_b_is_not_aged_out_after_admission(self):
        old_b={'title':'Durable horizon-scanning method','date':'2014-03-01','strand':'B'}
        kept,removed,_=S.enforce_two_tier_ab_window([old_b], S.DATE_FLOOR, S.EXTENDED_DATE_FLOOR)
        self.assertEqual(removed,0)
        self.assertEqual(len(kept),1)

    def test_think_tank_analysis_is_context_not_independent_public_c(self):
        text=('Europe research security analysis warns that foreign interference and strategic dependencies in advanced compute '
              'are changing university access to research infrastructure and scientific capability.')
        news=[{
            'headline':'Analysis: Europe research security exposure is shifting with strategic dependencies',
            '_desc':text,
            'source':'Bruegel','source_domain':'bruegel.org','link':'https://bruegel.org/analysis/example',
            'date':'2026-09-09T08:00Z','_themes':S.themes_for(text),
            '_entities':S.distinct_matches(text, S.ENTITY_TERMS+S.GEO_ACTORS),
            '_trusted_commentary_signal':True,
        }]
        out=S.anchor_news(news, [], allow_unanchored=True)
        self.assertEqual(out, [])

    def test_missing_legacy_admission_profile_does_not_protect_old_seen_tombstones(self):
        source=PATH.read_text(encoding='utf-8')
        self.assertIn('previous_admission_profile != current_admission_profile', source)
        self.assertNotIn('previous_admission_profile and previous_admission_profile != current_admission_profile', source)

    def test_b_has_long_horizon_without_weakening_gate(self):
        cfg=json.loads((ROOT/'radar_config.json').read_text())
        self.assertGreaterEqual(int(cfg.get('b_method_lookback_years',0)),10)
        self.assertIn('b-method', PATH.read_text())

    def test_budget_and_mix_targets(self):
        cfg=json.loads((ROOT/'radar_config.json').read_text())
        self.assertEqual(int(cfg['full_budget_continuation_max_waves']),2)
        self.assertEqual((int(cfg['target_new_a_per_scan']),int(cfg['target_new_b_per_scan']),int(cfg['target_new_c_per_scan'])),(8,1,3))
        self.assertEqual(int(cfg['discovery_overlap_days']),45)

    def test_main_workflow_is_schedule_or_manual_not_push(self):
        text=(ROOT/'.github/workflows/radar-scan.yml').read_text()
        head=text.split('permissions:',1)[0]
        self.assertNotIn('  push:',head)
        self.assertIn("cron: '17 0,4,8,12,16,20 * * *'",head)

if __name__=='__main__': unittest.main()
