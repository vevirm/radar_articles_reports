from pathlib import Path
import subprocess
import unittest

from scripts import scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class PlainLanguageDisplayTests(unittest.TestCase):
    def run_node(self, script: str):
        subprocess.run(['node', '-e', script], cwd=ROOT, check=True)

    def test_main_radar_reader_first_rewrites(self):
        script = r"""
const I=require('./briefing/insights.js');
const items=[
 {strand:'A',title:'Ireland: Interlocking factors shape the approach to China in science-tech innovation',link:'ie',summary:`However, as much of the Irish life science sector is owned by US multinationals, US-China relations to a large extent would determine how much cooperation Ireland and China can have in innovative life science production. It is also shaped by pressure to diversify amid uncertainty surrounding the current US administration, as well as by wider efforts to build resilience in response to geopolitical instability.`},
 {strand:'A',title:'EU chip-war strategy',link:'chips',summary:`This article analyzes the European Union's strategy. Second, it applies technology protection through semiconductor export controls while managing its economic interests toward China and its security relations with the United States.`},
 {strand:'A',title:'A Copernican revolution? Geopolitical tensions, Polish universities and the (dis)continuities of neo-nationalism',link:'poland',summary:`Focusing on the creation of the Copernican Academy and the activities surrounding Collegium Intermarium, the study demonstrates how geopolitical narratives of the Intermarium were instrumentalized to advance neo-nationalist ambitions in global academic governance.`},
 {strand:'A',title:'Foreign direct investment from EU countries as instruments for financing China',link:'fdi',summary:`These vulnerabilities include the diffusion of dual-use technologies, cross-border knowledge transfer, and the emergence of dependencies in strategically important supply chains that may weaken the EU's economic security and strategic autonomy.`}
];
const want=[
 "US–China tensions and US uncertainty are narrowing Ireland's room for science-tech cooperation with China.",
 'EU chip controls protect technology while Europe balances China trade and US security ties.',
 'Polish research policy has been pulled into geopolitical and neo-nationalist projects.',
 'EU research-security risks include dual-use spread, knowledge leakage and critical-supply dependence.'
];
for(let i=0;i<items.length;i++){
  const got=I.pointFor(items[i]);
  if(got!==want[i]){console.error('plain-language mismatch',i,got);process.exit(20+i)}
}
"""
        self.run_node(script)

    def test_matrix_reuses_shared_simple_claim_layer(self):
        script = r"""
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const S=require('./frontier/frontier.js');
const items=[
 {strand:'A',title:'EU chip-war strategy',link:'chips',summary:`The EU is reducing strategic dependence in semiconductors. Second, it applies technology protection through semiconductor export controls while managing its economic interests toward China and its security relations with the United States.`},
 {strand:'A',title:'A Copernican revolution? Geopolitical tensions, Polish universities and the (dis)continuities of neo-nationalism',link:'poland',summary:`European research governance and strategic autonomy are affected. Focusing on the creation of the Copernican Academy and the activities surrounding Collegium Intermarium, the study demonstrates how geopolitical narratives of the Intermarium were instrumentalized to advance neo-nationalist ambitions in global academic governance.`},
 {strand:'A',title:'Foreign direct investment from EU countries as instruments for financing China',link:'fdi',summary:`These vulnerabilities include the diffusion of dual-use technologies, cross-border knowledge transfer, and the emergence of dependencies in strategically important supply chains that may weaken the EU's economic security and strategic autonomy.`}
];
const candidates=S.evidenceCandidates({strand_a:items,frontier_evidence:[]});
const want=[
 'EU chip controls protect technology while Europe balances China trade and US security ties.',
 'Polish research policy has been pulled into geopolitical and neo-nationalist projects.',
 'EU research-security risks include dual-use spread, knowledge leakage and critical-supply dependence.'
];
for(const claim of want){
  if(!candidates.some(x=>x.headline===claim)){console.error('matrix did not reuse simple claim',claim,candidates.map(x=>x.headline));process.exit(30)}
}
"""
        self.run_node(script)

    def test_original_detail_is_not_rewritten(self):
        page=(ROOT/'index.html').read_text(encoding='utf-8')
        self.assertIn("prepareSummary?.(x.summary||'')", page)
        self.assertIn("const title=x.title||x.headline||''", page)
        self.assertIn("const who=x.authors||''", page)
        self.assertIn("[x.source,fmtDate(x.date),x.type]", page)

    def test_scanner_write_boundary_uses_same_plain_language_examples(self):
        cases = [
            (
                "It is also shaped by pressure to diversify amid uncertainty surrounding the current US administration, as well as by wider efforts to build resilience in response to geopolitical instability.",
                "Ireland: Interlocking factors shape the approach to China in science-tech innovation",
                "US–China tensions and US uncertainty are narrowing Ireland's room for science-tech cooperation with China.",
            ),
            (
                "Second, it applies technology protection through semiconductor export controls while managing its economic interests toward China and its security relations with the United States.",
                "EU chip-war strategy",
                "EU chip controls protect technology while Europe balances China trade and US security ties.",
            ),
            (
                "Focusing on the creation of the Copernican Academy and the activities surrounding Collegium Intermarium, the study demonstrates how geopolitical narratives of the Intermarium were instrumentalized to advance neo-nationalist ambitions in global academic governance.",
                "A Copernican revolution? Geopolitical tensions, Polish universities and the (dis)continuities of neo-nationalism",
                "Polish research policy has been pulled into geopolitical and neo-nationalist projects.",
            ),
            (
                "These vulnerabilities include the diffusion of dual-use technologies, cross-border knowledge transfer, and the emergence of dependencies in strategically important supply chains that may weaken the EU's economic security and strategic autonomy.",
                "Foreign direct investment from EU countries as instruments for financing China",
                "EU research-security risks include dual-use spread, knowledge leakage and critical-supply dependence.",
            ),
        ]
        for summary, title, want in cases:
            self.assertEqual(sr.plain_language_claim(summary, title), want)

    def test_global_normalizer_changes_claim_not_bibliography_or_source_detail(self):
        summary = "Second, it applies technology protection through semiconductor export controls while managing its economic interests toward China and its security relations with the United States."
        data = {
            "strand_a": [{
                "title": "EU chip-war strategy",
                "authors": "Example Author",
                "source": "Example Journal",
                "date": "2026-08-01",
                "summary": summary,
                "core_message": summary,
            }],
            "strand_b": [], "strand_c": [], "frontier_evidence": [],
        }
        sr.normalize_reader_claims(data)
        item = data["strand_a"][0]
        self.assertEqual(item["title"], "EU chip-war strategy")
        self.assertEqual(item["authors"], "Example Author")
        self.assertEqual(item["source"], "Example Journal")
        self.assertEqual(item["date"], "2026-08-01")
        self.assertEqual(item["summary"], summary)
        self.assertEqual(
            item["core_message"],
            "EU chip controls protect technology while Europe balances China trade and US security ties.",
        )


if __name__ == '__main__':
    unittest.main()
