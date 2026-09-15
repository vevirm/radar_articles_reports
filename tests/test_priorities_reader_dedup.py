import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PrioritiesReaderDedupTests(unittest.TestCase):
    def run_node(self, body):
        cp = subprocess.run(["node", "-e", body], cwd=ROOT, check=True, text=True, capture_output=True)
        return json.loads(cp.stdout)

    def test_same_reader_facing_risk_is_one_card_with_additional_primary_evidence(self):
        js = r'''
const P=require('./priorities/priorities.js');
const lens=passage=>({primary:'risk',lenses:[{type:'risk',passage,components:{mechanism:'export controls',carrier:'supplier concentration',asset:'semiconductor supply',loss:'disrupt'}}]});
const make=(title,source,date)=>({title,source,date,link:`https://${source.toLowerCase()}.example/item`,source_tier:'Tier 1',strategic_classification_source:'source_text',strategic_classification:lens(`${title}. Export controls and concentrated supply could disrupt semiconductor supply in Europe.`)});
const data={strand_a:[
  make('Semiconductor supply exposure in China','Alpha','2026-09-03'),
  make('Taiwan chip dependencies and export controls','Beta','2026-09-02'),
  make('Microelectronics supply concentration','Gamma','2026-09-01')
]};
const view=P.buildPriorityView(data,{limit:20});
console.log(JSON.stringify({
  titles:view.risks.map(P.plainPriorityTitle),
  related:view.risks.map(x=>(x.relatedPrimaryEvidence||[]).map(y=>y.source)),
  stats:view.stats
}));
'''
        out = self.run_node(js)
        self.assertEqual(out["titles"], ["Export controls could cut European access to advanced chips before alternatives are ready."])
        self.assertEqual(len(out["related"][0]), 2)
        self.assertEqual(out["stats"]["risks"], 1)
        self.assertEqual(out["stats"]["rawRisks"], 3)
        self.assertEqual(out["stats"]["mergedRiskRecords"], 2)

    def test_distinct_reader_facing_risks_remain_separate(self):
        js = r'''
const P=require('./priorities/priorities.js');
const lens=(passage,asset)=>({primary:'risk',lenses:[{type:'risk',passage,components:{mechanism:'could restrict',carrier:'outside actor',asset,loss:'loss'}}]});
const data={strand_a:[
  {title:'Semiconductor export controls',source:'Alpha',date:'2026-09-03',link:'https://alpha.example/chips',source_tier:'Tier 1',strategic_classification_source:'source_text',strategic_classification:lens('China export controls could restrict semiconductor supply and disrupt chip access in Europe.','semiconductor supply')},
  {title:'Research career precarity',source:'Beta',date:'2026-09-02',link:'https://beta.example/talent',source_tier:'Tier 1',strategic_classification_source:'source_text',strategic_classification:lens('Research career precarity could restrict researcher mobility and cause brain drain in Europe.','research talent')}
]};
const view=P.buildPriorityView(data,{limit:20});
console.log(JSON.stringify({titles:view.risks.map(P.plainPriorityTitle),stats:view.stats}));
'''
        out = self.run_node(js)
        self.assertEqual(len(out["titles"]), 2)
        self.assertEqual(out["stats"]["risks"], 2)
        self.assertEqual(out["stats"]["mergedRiskRecords"], 0)

    def test_reader_wording_uses_lens_components_not_unrelated_source_words(self):
        js = r'''
const P=require('./priorities/priorities.js');
const data={strand_a:[
  {title:'Collaboration inequalities and material conditions',source:'Alpha',date:'2026-09-03',link:'https://alpha.example/collab',source_tier:'Tier 1',strategic_classification_source:'source_text',strategic_classification:{primary:'risk',lenses:[{type:'risk',passage:'The study describes barriers to research collaboration and mentions material conditions elsewhere.',components:{mechanism:'barriers to',carrier:'unequal authority',asset:'research collaboration',loss:'barriers to'}}]}},
  {title:'Investment debate around breakthrough research',source:'Beta',date:'2026-09-02',link:'https://beta.example/research',source_tier:'Tier 1',strategic_classification_source:'source_text',strategic_classification:{primary:'risk',lenses:[{type:'risk',passage:'Investment is discussed, but the identified pathway is constrained European competitiveness.',components:{mechanism:'constrained by',carrier:'incremental research system',asset:'competitiveness',loss:'limits'}}]}}
]};
const view=P.buildPriorityView(data,{limit:20});
console.log(JSON.stringify(view.risks.map(P.plainPriorityTitle)));
'''
        out = self.run_node(js)
        self.assertIn('Unequal or restrictive collaboration conditions could narrow who can participate in and benefit from European research partnerships.', out)
        self.assertNotIn('Critical-material shortages or export controls could slow European research and industry.', out)
        self.assertNotIn('Heavy reliance on foreign investment could shift control of strategic technology away from Europe.', out)

    def test_same_visible_title_is_never_repeated_even_when_one_lens_is_less_structured(self):
        js = r'''
const P=require('./priorities/priorities.js');
const data={strand_a:[
  {title:'AI compute programme',source:'Alpha',date:'2026-09-03',link:'https://alpha.example/a',source_tier:'Tier 1',strategic_classification_source:'source_text',strategic_classification:{primary:'opportunity',lenses:[{type:'opportunity',passage:'A live call will boost European computing capacity.',components:{mechanism:'call',actor:'EU',instrument:'call',gain:'computing capacity',window:'live'}}]}},
  {title:'Computing capacity call',source:'Beta',date:'2026-09-02',link:'https://beta.example/b',source_tier:'Tier 1',strategic_classification_source:'source_text',strategic_classification:{primary:'opportunity',lenses:[{type:'opportunity',passage:'A live call will boost European computing capacity.'}]}}
]};
const view=P.buildPriorityView(data,{limit:20});
console.log(JSON.stringify({titles:view.opportunities.map(P.plainPriorityTitle),merged:view.stats.mergedOpportunityRecords}));
'''
        out = self.run_node(js)
        self.assertEqual(len(out['titles']), len(set(out['titles'])))


if __name__ == '__main__':
    unittest.main()
