from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SovereigntyFrontierTests(unittest.TestCase):
    def run_node(self, script: str):
        subprocess.run(['node', '-e', script], cwd=ROOT, check=True)

    def test_page_reads_cumulative_radar_without_writing_it(self):
        page = (ROOT / 'frontier' / 'index.html').read_text(encoding='utf-8')
        js = (ROOT / 'frontier' / 'frontier.js').read_text(encoding='utf-8')
        self.assertIn('Insight Summary', page)
        self.assertIn('Sovereignty-Frontier Signals', page)
        self.assertIn("fetch('../radar.json?ts='+Date.now()", page)
        self.assertIn('Every qualifying signal is placed in exactly one cell', page)
        self.assertIn('One-look read', page)
        self.assertIn('Show ${hidden.length} more', page)
        self.assertIn('data-expand', page)
        self.assertNotIn('fetch(', js)
        self.assertNotIn('writeFile', js)
        self.assertNotIn('localStorage', js)

    def test_main_and_insights_link_to_summary(self):
        main = (ROOT / 'index.html').read_text(encoding='utf-8')
        briefing = (ROOT / 'briefing' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('frontier/?v=17.5.5">Open Insight Summary', main)
        self.assertIn('../frontier/">Insight Summary →', briefing)

    def test_four_frontier_columns_are_classified(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data={strand_a:[],strand_b:[],strand_c:[
 {headline:'EU attracts frontier AI researchers and expands European compute capacity, reducing non-EU dependence',source:'Reuters',date:'2026-08-21',watch_theme:'R&I competitiveness / technological capabilities',new_this_scan:true},
 {headline:'EU research security rules reduce foreign dependence but slow scientific collaboration and raise costs',source:'Reuters',date:'2026-08-21',watch_theme:'research security',new_this_scan:true},
 {headline:'European AI labs gain frontier performance by relying on US cloud and non-EU compute suppliers',source:'Reuters',date:'2026-08-21',watch_theme:'technology sovereignty',new_this_scan:true},
 {headline:'Europe loses semiconductor production capacity as foreign suppliers restrict access and EU firms fall behind',source:'Reuters',date:'2026-08-21',watch_theme:'semiconductors',new_this_scan:true}
]};
const v=F.buildFrontier(data,{now:'2026-08-21T18:00:00Z'});
const cols=new Set(v.signals.map(x=>x.column.id));
for(const c of ['A','B','C','D']) if(!cols.has(c)){console.error('missing column',c,v.signals);process.exit(2)}
for(const x of v.signals){
 if(!['knowledge','infrastructure','conversion','rules'].includes(x.row.id)) process.exit(3);
 if(x.triage.total<4||x.triage.total>16) process.exit(4);
 if(!x.actor) process.exit(5);
}
'''
        self.run_node(script)

    def test_generic_geopolitical_noise_does_not_pass_gate(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data={strand_a:[],strand_b:[],strand_c:[
 {headline:'China launches biggest ever auto recall campaign over door handle safety.',source:'Reuters',date:'2026-08-21',watch_theme:'EU–China S&T cooperation / de-risking',why_it_matters:'This may shift the risk–reward balance of EU–China research, technology and innovation cooperation.'},
 {headline:'EXCLUSIVE: US designates American held by China as wrongfully detained.',source:'Reuters',date:'2026-08-20',watch_theme:'EU–China S&T cooperation / de-risking',why_it_matters:'This may shift the risk–reward balance of EU–China research, technology and innovation cooperation.'},
 {headline:'University suspends academic behind plagiarism accusations.',source:'SCMP',date:'2026-08-20',watch_theme:'EU–China S&T cooperation / de-risking',why_it_matters:'This may shift the risk–reward balance of EU–China research, technology and innovation cooperation.'}
]};
const v=F.buildFrontier(data,{now:'2026-08-21T18:00:00Z'});
if(v.signals.length!==0){console.error(v.signals);process.exit(2)}
'''
        self.run_node(script)

    def test_live_style_strong_examples_do_pass(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data={strand_a:[
 {strand:'A',title:'Back to the future? What it will take to deliver nuclear energy in the EU – CEPS',source:'CEPS',date:'2026-07-17',link:'nuclear',type:'institutional report',summary:'The growing role of non-EU technology vendors for large-scale reactors and SMRs on the EU market raises questions about technological sovereignty, industrial competitiveness and strategic dependencies.'}
],strand_b:[],strand_c:[
 {headline:'EU attracts research scientists back to Europe, strengthening frontier research capacity and reducing dependence on foreign talent.',source:'Reuters',date:'2026-08-21',watch_theme:'research talent mobility',why_it_matters:'This changes Europe research capacity and strategic autonomy.'},
 {headline:'Europe loses semiconductor production capacity as foreign suppliers restrict access and EU firms fall behind.',source:'Euronews',date:'2026-08-20',watch_theme:'semiconductors',why_it_matters:"This changes Europe's industrial innovation capacity and technology dependence."}
]};
const v=F.buildFrontier(data,{now:'2026-08-21T18:00:00Z'});
const joined=v.signals.map(x=>x.title).join('\n');
for(const re of [/nuclear expansion.*non-EU reactor technology/i,/attracts research scientists back to Europe/i,/loses semiconductor production capacity/i]) if(!re.test(joined)){console.error(joined);process.exit(2)}
'''
        self.run_node(script)

    def test_live_corpus_and_recovery_guard_survive_frontier_layer(self):
        import json
        radar = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        scanner = (ROOT / 'scripts' / 'scan_radar.py').read_text(encoding='utf-8')
        self.assertGreaterEqual(sum(len(radar.get(k, [])) for k in ('strand_a', 'strand_b', 'strand_c')), 90)
        self.assertEqual((len(radar.get('strand_a', [])), len(radar.get('strand_b', [])), len(radar.get('strand_c', []))), (84, 5, 19))
        self.assertIn('Recovered a larger pre-upload radar corpus from Git history', scanner)
        self.assertIn('clean.pop("repository_bundle_seed", None)', scanner)


if __name__ == '__main__':
    unittest.main()
