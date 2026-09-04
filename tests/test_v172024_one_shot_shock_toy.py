import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OneShotShockToyTests(unittest.TestCase):
    def test_external_shocks_page_exposes_ephemeral_button(self):
        html = (ROOT / 'shocks' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Construct one shock hypothesis', html)
        self.assertIn('id="toyButton"', html)
        self.assertIn('The score assigns source roles only; it does not rank shocks.', html)
        self.assertIn('toy.js?v=17.20.24', html)
        self.assertIn('source_merit.js?v=17.20.24', html)
        self.assertIn('pressing again throws this one away', html)

    def test_constructor_obeys_roles_novelty_and_path_contract(self):
        js = r"""
const fs=require('fs');
const Toy=require('./shocks/toy.js');
const D=JSON.parse(fs.readFileSync('radar.json','utf8'));
const banned=/\b(?:strategic autonomy|technological sovereignty|geopolitics|dual[- ]use|critical raw materials|science diplomacy|research security|export control|de-risking)\b/i;
let seed=123456789;
function rng(){seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;}
const before=JSON.stringify(D);
for(let i=0;i<60;i++){
  const r=Toy.construct(D,{rng});
  if(!r.ok) throw new Error('current corpus should support the toy: '+r.message);
  if(r.sources.length!==3) throw new Error('not three sources');
  if(new Set(r.sources.map(x=>x.source)).size!==3) throw new Error('sources are not distinct');
  const e=r.sources.find(x=>x.role==='event'), s=r.sources.find(x=>x.role==='surface'), m=r.sources.find(x=>x.role==='mechanism');
  if(!e||!s||!m) throw new Error('source roles missing');
  if(!(e.score<78)) throw new Error('event not low-score');
  if(!(s.score>=93)) throw new Error('surface not high-score');
  if(!(m.score>=75&&m.score<=92)) throw new Error('mechanism not middle-score');
  if(r.path.length>4) throw new Error('path too long');
  if(banned.test(r.shock)) throw new Error('shock collapsed into usual framing words');
  if(r.disclaimer!=='a constructed hypothesis drawn from the corpus, asserted by no source in it, not admitted, not retained.') throw new Error('disclaimer changed');
  if(r.attempts>5) throw new Error('too many repair attempts');
}
if(JSON.stringify(D)!==before) throw new Error('toy mutated corpus data');
"""
        subprocess.run(['node', '-e', js], cwd=ROOT, check=True, timeout=30)

    def test_toy_has_no_persistence_or_network_write_path(self):
        js = (ROOT / 'shocks' / 'toy.js').read_text(encoding='utf-8')
        low = js.lower()
        self.assertNotIn('localstorage', low)
        self.assertNotIn('sessionstorage', low)
        self.assertNotIn('indexeddb', low)
        self.assertNotIn('fetch(', low)
        self.assertNotIn('xmlhttprequest', low)
        self.assertIn('attempts<5', js)

    def test_duplicate_titles_and_repeated_core_messages_are_defensively_filtered(self):
        js = r"""
const Toy=require('./shocks/toy.js');
const row={title:'Same title',source:'X',date:'2026-09-01',type:'preprint',summary:'Useful summary',core_message:'Repeated extraction sentence that should be ignored because it occurs everywhere and is long enough.'};
const D={strand_a:[row,{...row,source:'Y'},{title:'Different title',source:'Z',date:'2026-09-01',type:'preprint',summary:'Other',core_message:row.core_message},{title:'Third title',source:'Q',date:'2026-09-01',type:'preprint',summary:'Other',core_message:row.core_message}],strand_b:[],strand_c:[]};
const xs=Toy.prepareCorpus(D);
if(xs.filter(x=>x.title==='Same title').length!==1) throw new Error('duplicate title retained');
if(xs.some(x=>x._usableCore===row.core_message)) throw new Error('repeated extraction error retained');
"""
        subprocess.run(['node', '-e', js], cwd=ROOT, check=True, timeout=20)


if __name__ == '__main__':
    unittest.main()
