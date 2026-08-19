from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class InsightsPageTests(unittest.TestCase):
    def test_page_is_topics_and_bullets_only(self):
        page=(ROOT/'briefing'/'index.html').read_text(encoding='utf-8')
        self.assertIn('One signal, one clear point.', page)
        self.assertIn("fetch('../radar.json?ts='+Date.now()", page)
        self.assertIn('<h2>${esc(g.name)}</h2><ul>', page)
        self.assertIn('<li>${esc(x.point)}</li>', page)
        for clutter in ('Radar relevance:', 'Strand A', 'Strand B', 'Strand C', 'source_tier', 'Also touches', 'item count', 'TOPIC'):
            self.assertNotIn(clutter,page)

    def test_main_radar_points_to_same_briefing_path_with_cache_bust(self):
        page=(ROOT/'index.html').read_text(encoding='utf-8')
        self.assertIn('href="briefing/?v=7">Radar insights</a>',page)

    def test_old_generator_and_workflow_removed(self):
        self.assertFalse((ROOT/'scripts'/'build_briefing.py').exists())
        self.assertFalse((ROOT/'.github'/'workflows'/'radar-briefing.yml').exists())

    def test_transformer_classifies_and_writes_one_point(self):
        script=r'''
const I=require('./briefing/insights.js');
const data={strand_a:[
 {title:'Critical raw materials strategy',summary:'Europe plans to diversify refining capacity for critical raw materials and reduce dependence on a small number of suppliers.',link:'a',date:'2026-08-18'},
 {title:'European Research Council update',summary:'Commission Decision C(2026)62 on the financing of Horizon Europe with a view to introduce a new grant scheme – the ERC Plus Grant.',link:'b',date:'2026-08-17'},
 {title:'AI factories expand compute access',summary:'The EU will expand AI factory capacity to give researchers and companies greater access to advanced compute.',link:'c',date:'2026-08-16'}
],strand_b:[],strand_c:[]};
const g=I.buildInsights(data);
function group(name){return g.find(x=>x.name===name)}
if(!group('Raw materials')) process.exit(2);
if(!group('Research')) process.exit(3);
if(!group('AI')) process.exit(4);
for(const x of g.flatMap(x=>x.items)) if(!x.point || x.point.split(/\s+/).length>36) process.exit(5);
const research=group('Research').items[0].point;
if(!/introduce a new grant scheme/i.test(research)) process.exit(6);
'''
        subprocess.run(['node','-e',script],cwd=ROOT,check=True)

if __name__=='__main__':
    unittest.main()
