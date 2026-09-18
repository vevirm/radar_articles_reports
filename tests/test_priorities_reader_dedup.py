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

    def test_claim_native_stage7_uses_python_shelf_only_and_preserves_publication_order(self):
        js = r'''
const P=require('./priorities/priorities.js');
const legacy={title:'Very high quality legacy talent risk',source:'CESAR',date:'2026-03-30',link:'https://legacy.example/talent',source_tier:'Tier 1',strategic_classification_source:'source_text',strategic_classification:{primary:'risk',lenses:[{type:'risk',passage:'Career precarity could create brain drain.',components:{mechanism:'precarity',carrier:'career system',asset:'research talent',loss:'brain drain'}}]}};
const riskA={id:'claim:risk:a',product:'risk',grammar_id:'clock_before_rule',level:3,inferential_distance:3,status:'qualified',score:70,wow:3,topic_label:'compute public procurement — delivery clock ahead of settled rules',primary_records:4,primary_sources:3,support:[]};
const riskB={id:'claim:risk:b',product:'risk',grammar_id:'corroborated_claim',level:2,inferential_distance:2,status:'qualified',score:99,wow:3,topic_label:'research security screening — corroborated current finding',object:'research_security.screening',mechanism:'conditions',direction:'becomes_conditional',claim_status:'adopted',primary_records:3,primary_sources:3,support:[]};
const opp={id:'claim:opp:a',product:'opportunity',grammar_id:'corroborated_claim',level:2,status:'qualified',score:80,wow:2,topic_label:'horizon association — corroborated current finding',object:'horizon.association',mechanism:'associates',direction:'expands',claim_status:'in_force',primary_records:2,primary_sources:2,support:[]};
const data={strand_a:[legacy],high_order_inference:{detector_backend:'claim_native',selection_stage:7,publications:{risk:['claim:risk:a','claim:risk:b'],opportunity:['claim:opp:a']},candidates:[riskA,riskB,opp],selection:{risk:{reserve:8,watch:4},opportunity:{reserve:2,watch:9}}}};
const view=P.buildPriorityView(data,{limit:20});
console.log(JSON.stringify({
  riskIds:view.risks.map(x=>x.candidateId),
  riskTitles:view.risks.map(P.plainPriorityTitle),
  oppIds:view.opportunities.map(x=>x.candidateId),
  stats:view.stats
}));
'''
        out = self.run_node(js)
        self.assertEqual(out['riskIds'], ['claim:risk:a', 'claim:risk:b'])
        self.assertNotIn('Precarious career paths can make Europe lose research talent it has trained or attracted.', out['riskTitles'])
        self.assertEqual(out['oppIds'], ['claim:opp:a'])
        self.assertTrue(out['stats']['claimNativeCutover'])
        self.assertEqual(out['stats']['riskReserve'], 8)
        self.assertEqual(out['stats']['riskWatch'], 4)
        self.assertEqual(out['stats']['opportunityReserve'], 2)
        self.assertEqual(out['stats']['opportunityWatch'], 9)

    def test_claim_native_level2_reader_language_uses_semantic_direction_and_mechanism(self):
        js = r'''
const P=require('./priorities/priorities.js');
const data={high_order_inference:{detector_backend:'claim_native',selection_stage:7,publications:{risk:['r'],opportunity:['o1','o2']},candidates:[
{id:'r',product:'risk',grammar_id:'corroborated_claim',level:2,wow:3,score:80,topic_label:'supply chain access — corroborated current finding',object:'supply.chain_access',mechanism:'conditions',direction:'becomes_conditional',claim_status:'in_force',primary_records:3,primary_sources:3,support:[]},
{id:'o1',product:'opportunity',grammar_id:'corroborated_claim',level:2,wow:2,score:80,topic_label:'research system governance — corroborated current finding',object:'research.system_governance',mechanism:'prioritises',direction:'expands',claim_status:'adopted',primary_records:2,primary_sources:2,support:[]},
{id:'o2',product:'opportunity',grammar_id:'corroborated_claim',level:2,wow:2,score:79,topic_label:'research system governance — corroborated current finding',object:'research.system_governance',mechanism:'launches',direction:'expands',claim_status:'operating',primary_records:2,primary_sources:2,support:[]}
],selection:{risk:{},opportunity:{}}}};
const v=P.buildPriorityView(data,{limit:20});
console.log(JSON.stringify({riskTitle:P.plainPriorityTitle(v.risks[0]),riskText:P.plainPriorityExplanation(v.risks[0]),oppTitles:v.opportunities.map(P.plainPriorityTitle)}));
'''
        out = self.run_node(js)
        self.assertIn('becoming more conditional', out['riskTitle'])
        self.assertIn('toward tighter conditions', out['riskText'])
        self.assertEqual(len(out['oppTitles']), len(set(out['oppTitles'])))
        self.assertTrue(any('adopted priorities' in x for x in out['oppTitles']))
        self.assertTrue(any('new instruments' in x for x in out['oppTitles']))


if __name__ == '__main__':
    unittest.main()
