from pathlib import Path
import json
import subprocess
import unittest

from scripts import scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class V17130FeedbackRoundTests(unittest.TestCase):
    def test_implied_strategic_context_does_not_require_geopolitics_word(self):
        text = (
            "The European Union's semiconductor research infrastructure relies on non-EU suppliers. "
            "This dependence constrains European research capacity and technological competitiveness."
        )
        ok, families, evidence = sr.implied_strategic_context(text)
        self.assertTrue(ok)
        self.assertIn('dependence_control', families)
        self.assertIn('competition_capability', families)
        self.assertTrue(evidence)
        self.assertNotIn('geopolit', text.lower())

        gate = sr.gate_scope(
            "European semiconductor research infrastructure and external dependence",
            text,
            "",
            1,
            source_kind='scholarly',
        )
        self.assertTrue(gate['a_pass'], gate)
        self.assertEqual(gate['a_route'], 'triangulated-strategic-context')

    def test_generic_competitiveness_alone_is_not_enough(self):
        text = "The European Union should improve innovation capacity and competitiveness through research funding."
        ok, families, _ = sr.implied_strategic_context(text)
        self.assertFalse(ok)
        self.assertLess(len(set(families)), 2)

    def test_weak_signals_are_capped_as_a_minority(self):
        a = [{'date': '2026-08-01'} for _ in range(80)]
        b = [{'date': '2026-08-01'} for _ in range(20)]
        c = [{'date': f'2026-08-{(i % 28) + 1:02d}', 'first_seen': str(i)} for i in range(40)]
        kept, removed = sr.cap_strand_c_share(a, b, c, 0.15)
        self.assertGreater(removed, 0)
        share = len(kept) / (len(a) + len(b) + len(kept))
        self.assertLessEqual(share, 0.15)
        self.assertEqual(float(sr.CONFIG['strand_c_max_share']), 0.15)
        self.assertEqual(int(sr.CONFIG['weak_signal_followup_queries_per_wave']), 0)

    def test_existing_findings_feed_a_rotating_search_context_lane(self):
        previous = {
            'strand_a': [{
                'title': 'European AI factories and compute capacity',
                'summary': 'EU research infrastructure and AI compute capacity are expanding.',
                'core_message': 'Europe is building more AI compute capacity.',
                'relevance_note': 'Direct EU R&I relevance.',
            }]
        }
        bank = sr.finding_context_query_bank(previous, limit=6)
        self.assertTrue(bank)
        self.assertTrue(any('compute' in q.lower() or 'ai' in q.lower() for q in bank), bank)

    def test_researcher_names_are_fallback_attention_not_a_separate_gate(self):
        self.assertGreater(int(sr.CONFIG['priority_people_trigger_below_scholarly_candidates']), 0)
        self.assertEqual(sr.CONFIG['priority_people_rule'].split('.')[0],
                         'Curated researchers receive extra discovery attention inside the ordinary scholarly rotation')
        public = sr.public_item({
            'title': 'European research security',
            'summary': 'European research security affects international collaboration and technological capability.',
            'strand': 'A',
            '_priority_person': 'Example Researcher',
            '_priority_origin': 'openalex',
        })
        self.assertFalse(any(k.startswith('_priority') for k in public))

    def test_reader_first_rewrites_cover_the_requested_examples(self):
        cases = [
            (
                "Global case studies (China, the European Union, and the Bahamas) have been analysed, and the specific features of the Ukrainian e-hryvnia project have been identified as instruments for enhancing transparency and cyber resilience.",
                "Digital instruments of monetary and prudential policy in ensuring the cybersecurity of the financial space",
                'e-hryvnia',
                'cyber resilience',
            ),
            (
                "Despite these obstacles, the study identifies the emergent roles of regional alliances such as the EU and African Union and multistakeholder forums such as IGF and GFCE as promising conduits for normative convergence and collaborative capacity-building.",
                "Global Cybersecurity Governance: Challenges in Harmonizing International Cyber Laws",
                'shared cyber rules',
                'shared cyber rules',
            ),
            (
                "Across the United States, China, the European Union, the United Kingdom, and Japan, AI4S is widely framed as a strategic instrument for overcoming structural development bottlenecks, accelerating knowledge production, and strengthening national competitiveness.",
                "The new frontier of research competition: perspectives on national AI4S strategies",
                'AI for science',
                'competitiveness',
            ),
            (
                "It combines large datasets on patents, scientific publications, and venture capital investment (2010–2025) to map technological specialisation, research capacity, and entrepreneurial activity across the EU and selected global partners.",
                "Mapping of technology specialisation, complexity and relatedness of the EU and selected global partners – CEPS",
                'Patents, papers and venture capital',
                'global partners specialise',
            ),
        ]
        for summary, title, first, second in cases:
            claim = sr.plain_language_claim(summary, title)
            self.assertIn(first, claim)
            self.assertIn(second, claim)

    def test_issue_map_and_quick_matrix_are_progressive_disclosure_views(self):
        read_page = (ROOT / 'read' / 'index.html').read_text(encoding='utf-8')
        quick = (ROOT / 'frontier' / 'quick' / 'index.html').read_text(encoding='utf-8')
        frontier = (ROOT / 'frontier' / 'frontier.js').read_text(encoding='utf-8')
        priorities = (ROOT / 'priorities' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Eight issues. All branches open.', read_page)
        self.assertEqual(read_page.count("{title:'"), 8)
        self.assertIn('issue-chart', read_page)
        self.assertIn('chart-main', read_page)
        self.assertIn('chart-branch', read_page)
        self.assertIn('sub-node', read_page)
        self.assertIn('All eight charts are visible immediately.', read_page)
        self.assertIn('<section class="issue">', read_page)
        self.assertNotIn('Close all maps', read_page)
        self.assertNotIn('<details class="issue"', read_page)
        self.assertIn('distinct source-bound points', quick)
        self.assertIn('rotation priority', quick)
        self.assertNotIn('xs.slice(0,2)', quick)
        self.assertIn('groups.map', quick)
        self.assertIn('shortBullet', quick)
        self.assertIn('shortBullet', priorities)
        self.assertIn('whyBullet', priorities)
        self.assertNotIn('atleast-grid', priorities)
        self.assertNotIn('priorityInterpretation', priorities)
        for label in ('People & knowledge', 'Tools & infrastructure', 'Firms & scale', 'Rules & coordination'):
            self.assertIn(label, frontier)
        for label in ('Stronger on both', 'More control, more cost', 'Faster, but dependent', 'Weaker on both'):
            self.assertIn(label, frontier)


    def test_reader_views_are_publication_specific_and_deduplicated(self):
        stuff = (ROOT / 'stuff' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Publications and what they say', stuff)
        self.assertIn('Download publications workbook (.xlsx)', stuff)
        self.assertIn('<strong>What it says:</strong>', stuff)
        self.assertIn('<strong>Why it matters:</strong>', stuff)
        self.assertNotIn('downloadMatrix', stuff)

        js = r"""
const fs=require('fs');
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const P=require('./priorities/priorities.js');
const d=JSON.parse(fs.readFileSync('radar.json','utf8'));
const v=F.buildFrontier(d,{now:new Date(d.last_updated)});
let duplicateBullets=0, blankWhy=0, sameWhy=0;
for(const [cell,xs] of Object.entries(Object.fromEntries(Object.entries(v.cells).flatMap(([r,cols])=>Object.entries(cols).map(([c,ys])=>[r+'-'+c,ys]))))){
  const seen=new Set();
  for(const x of xs){const b=F.shortBullet(x); if(seen.has(b)) duplicateBullets++; seen.add(b); const w=F.whyBullet(x); if(!w) blankWhy++; if(w.toLowerCase()===b.toLowerCase()) sameWhy++;}
}
const pr=P.buildPriorityView(d,{limit:10,now:new Date(d.last_updated)});
const maxTopic=(xs)=>Math.max(0,...Object.values(xs.reduce((m,x)=>{const k=P.topicKey(x);m[k]=(m[k]||0)+1;return m},{})));
console.log(JSON.stringify({signals:v.signals.length,duplicateBullets,blankWhy,sameWhy,riskN:pr.risks.length,oppN:pr.opportunities.length,riskMaxTopic:maxTopic(pr.risks),oppMaxTopic:maxTopic(pr.opportunities)}));
"""
        out = subprocess.check_output(['node','-e',js], cwd=ROOT, text=True)
        got = json.loads(out.strip())
        self.assertGreater(got['signals'], 0)
        self.assertEqual(got['duplicateBullets'], 0)
        self.assertEqual(got['blankWhy'], 0)
        self.assertEqual(got['sameWhy'], 0)
        self.assertLessEqual(got['riskN'], 10)
        self.assertLessEqual(got['oppN'], 10)
        self.assertLessEqual(got['riskMaxTopic'], 2)
        self.assertLessEqual(got['oppMaxTopic'], 2)

    def test_current_radar_is_within_four_month_window_and_c_is_small(self):
        data = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        self.assertEqual(data.get('corpus_start_date'), '2026-04-28')
        a, b, c = map(lambda k: len(data.get(k, [])), ('strand_a', 'strand_b', 'strand_c'))
        self.assertLessEqual(c / max(1, a + b + c), 0.15)
        self.assertEqual(data.get('display_claim_profile_version'), 'v17.13.2-explicit-subject-120-char')
        chips = [x for x in data.get('strand_a', []) if x.get('title') == 'No one builds alone: The geopolitics of AI chips']
        self.assertEqual(len(chips), 1)
        self.assertNotIn('Chip design engineer', chips[0].get('summary', ''))
        self.assertNotIn('Chairperson', chips[0].get('summary', ''))


if __name__ == '__main__':
    unittest.main()
