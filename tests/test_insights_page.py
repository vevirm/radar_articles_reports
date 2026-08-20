from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class InsightsPageTests(unittest.TestCase):
    def run_node(self, script: str):
        subprocess.run(['node','-e',script],cwd=ROOT,check=True)

    def test_page_is_cumulative_and_searchable(self):
        page=(ROOT/'briefing'/'index.html').read_text(encoding='utf-8')
        self.assertIn('Cumulative intelligence layer', page)
        self.assertIn("fetch('../radar.json?ts='+Date.now()", page)
        self.assertIn('Search insights and sources', page)
        self.assertIn('All history', page)
        self.assertIn('cumulative-insights-v12', page)

    def test_main_radar_points_to_v12_briefing(self):
        page=(ROOT/'index.html').read_text(encoding='utf-8')
        self.assertIn('href="briefing/?v=12">Open Radar Insights</a>',page)
        self.assertIn('Cumulative corpus', page)

    def test_old_generator_and_workflow_removed(self):
        self.assertFalse((ROOT/'scripts'/'build_briefing.py').exists())
        self.assertFalse((ROOT/'.github'/'workflows'/'radar-briefing.yml').exists())

    def test_transformer_classifies_and_writes_one_point(self):
        script=r'''
const I=require('./briefing/insights.js');
const data={strand_a:[
 {title:'Critical raw materials strategy',summary:'Europe plans to diversify refining capacity for critical raw materials and reduce dependence on a small number of suppliers.',link:'a',date:'2026-08-18'},
 {title:'European Research Council update',summary:'Horizon Europe will introduce a new grant scheme, the ERC Plus Grant, for European Research Council funding.',link:'b',date:'2026-08-17'},
 {title:'AI factories expand compute access',summary:'The EU will expand AI factory capacity to give researchers and companies greater access to advanced compute.',link:'c',date:'2026-08-16'}
],strand_b:[],strand_c:[]};
const g=I.buildInsights(data);
function group(name){return g.find(x=>x.name===name)}
if(!group('Raw materials')) process.exit(2);
if(!group('Research')) process.exit(3);
if(!group('AI & compute')) process.exit(4);
for(const x of g.flatMap(x=>x.items)) if(!x.point || x.point.split(/\s+/).length>38) process.exit(5);
'''
        self.run_node(script)

    def test_document_debris_is_rejected(self):
        script=r'''
const I=require('./briefing/insights.js');
const junk=[
  '114 ANNEX 3: METHODOLOGY (EXTENDED) ........................................................................',
  'ANNEX 2: TECHNICAL ANNEX',
  'Table of contents',
  'Page 114 of 230',
  '118 APPENDIX A: METHODS __________________________',
  'A S I A D O N O R P A R T N E R S H I P S I N I N T E R N A T I O N'
];
for(const s of junk) if(!I.isDocumentDebris(s)) process.exit(2);
const data={strand_a:[
 {title:'Energy security review',summary:'114 ANNEX 3: METHODOLOGY (EXTENDED) ........................................................................',link:'junk'},
 {title:'Nuclear supply diversification',summary:'European utilities plan to diversify nuclear fuel supply to reduce dependence on Russian suppliers.',link:'good'}
],strand_b:[],strand_c:[]};
const points=I.buildInsights(data).flatMap(g=>g.items.map(x=>x.point));
if(points.some(p=>/ANNEX|METHODOLOGY|\.{4,}/i.test(p))) process.exit(3);
if(!points.some(p=>/diversify nuclear fuel supply/i.test(p))) process.exit(4);
'''
        self.run_node(script)

    def test_live_radar_examples_become_actual_points_not_document_prose(self):
        # Representative text copied from the current radar corpus. These tests are deliberately
        # about meaning: the bullet must be a signal statement, not a random sentence from a PDF.
        script=r'''
const I=require('./briefing/insights.js');
const data={strand_a:[
 {strand:'A',title:'Back to the future? What it will take to deliver nuclear energy in the EU – CEPS',link:'nuclear',summary:`The growing role of non -EU technology vendors for both large -scale reactors and SMRs on the EU market raises broader questions regarding technological sovereignty, industrial competitiveness and strategic dependencies, as also reflected in the negotiations over the Industrial Accelerator Act. 114 ANNEX 3: METHODOLOGY (EXTENDED) ........................................................................................... To support this, Member States willing to pursue nuclear remain responsible for ending stop -and-go cycles.`},
 {strand:'A',title:'Prospects for EU–Asia donor partnerships in international development – CEPS',link:'gateway',summary:`RESEARCH DESIGN AND METHODOLOGY ................................................................................ C E P S I N - D E P T H A N A L Y S I S P R O S P E C T S F O R E U A S I A | SUMMARY As the United States retreats from traditional ODA and China consolidates its infrastructure-led alternative, the EU is recasting development cooperation as investment-led geopolitical statecraft under Global Gateway, with digital transformation as the paradigm's central sector. The European Union has responded by accelerating its own pivot away from traditional grant-based aid.`},
 {strand:'A',title:'Shared gains, secure links: rethinking EU-Asia digital cooperation – CEPS',link:'asia',summary:`Japan and South Korea are anchored in a US security architecture that is becoming less reliable and more transactional, pushing them towards diversification while also binding them to US technology supply chains and export control regimes. Cooperation must proceed through research and innovation frameworks.`},
 {strand:'A',title:'Annual activity report 2025 - European Research Council Executive Agency',link:'erc',summary:`Commission Decision C(2026)62 on the financing of the 2026 work programme implementing Horizon Europe in relation to the European Research Council with a view to introduce a new grant scheme – the ERC Plus Grant. Finally, in line with Article 25 of Council Regulation, operations were assessed.`},
 {strand:'A',title:'Health under the Global Gateway: achievements and future prospects – CEPS',link:'health',summary:`The Global Gateway, including its partnerships on health, also represents an underutilised form of science diplomacy. The analysis is set against a rapidly evolving global context marked by declining official development assistance for health and heightened geopolitical competition.`},
 {strand:'A',title:'Building One Europe, One Market – CEPS',link:'market',summary:`The interaction between digital policy and international technology competition has become most concrete in advanced semiconductors and AI infrastructure. Much has already been written about the digital single market.`},
 {strand:'A',title:'From green to clean to eco-social: how to put wellbeing back onto the EU’s sustainability agenda – CEPS',link:'green',summary:`Since strategic foresight informs policy evaluation and design, this shift underscores broader changes. Building on the EGD but going beyond it, the 8th Environmental Action Programme acknowledged the relevance of promoting wellbeing within planetary boundaries.`}
],strand_b:[
 {strand:'B',title:'Governance logics and foresight functions',link:'f1',summary:`Rather, it contributes by showing how the same foresight methods perform different institutional functions across technocratic, market-managerial, networked and anticipatory governance settings. The purpose of the article is to develop a governance-sensitive framework.`},
 {strand:'B',title:'Co-creating climate-resilient cities',link:'f2',summary:`Abstract mainstream urban planning often remains disconnected from local concerns. This study introduces and tests a multi-method participatory foresight framework for developing locally grounded climate-resilient urban futures, bridging the gap between community-led visioning and formal administrative prioritization.`},
 {strand:'B',title:'Circular futures under institutional diversity',link:'f3',summary:`The article makes three contributions: a replicable procedure for building plausible scenarios and an explanation of why identical instruments perform differently across contexts, providing guidance for circular economy policies.`}
],strand_c:[
 {headline:'Ukraine urges EU sanctions on Rosatom over allegations of nuclear safety violations - politico.eu',source:'Politico Europe',link:'c1'},
 {headline:'West Africa cocoa sector struggles to meet EU anti-deforestation rules, raising supply concerns',source:'Reuters',link:'c2'},
 {headline:'Arctic: China launches “Ice Silk Road” route to Europe - Table.Briefings',source:'Table.Media',link:'c3'}
]};
const groups=I.buildInsights(data);
const points=groups.flatMap(g=>g.items.map(x=>x.point));
const joined=points.join('\n');
const must=[
 /EU nuclear expansion is becoming more dependent on non-EU reactor technology/i,
 /EU is shifting Global Gateway from grant-based aid toward investment-led geopolitical statecraft/i,
 /Japan and South Korea are diversifying partnerships/i,
 /Horizon Europe is introducing the ERC Plus Grant/i,
 /Global Gateway health partnerships are an underused EU science-diplomacy tool/i,
 /Advanced semiconductors and AI infrastructure are becoming a central arena/i,
 /wellbeing within planetary boundaries/i,
 /same foresight methods can serve different functions/i,
 /Participatory foresight can bridge community-led visioning/i,
 /Scenario-building methods can test why the same circular-economy instruments work differently/i,
 /Ukraine urges EU sanctions on Rosatom/i,
 /West Africa cocoa sector struggles to meet EU anti-deforestation rules/i,
 /China launches “Ice Silk Road” route to Europe/i
];
for(const re of must) if(!re.test(joined)){console.error('missing',re,joined);process.exit(10)}
const bad=[/ANNEX/i,/METHODOLOGY/i,/purpose of the article/i,/The analysis is set/i,/Much has already been written/i,/Table\.Briefings/i,/politico\.eu/i,/A S I A D O N O R/i,/Abstract mainstream/i];
for(const re of bad) if(re.test(joined)){console.error('bad',re,joined);process.exit(11)}
for(const p of points) if(p.split(/\s+/).length>38){console.error('too long',p);process.exit(12)}
'''
        self.run_node(script)

    def test_weak_meta_only_item_is_omitted(self):
        script=r'''
const I=require('./briefing/insights.js');
const data={strand_a:[{title:'A strategic report',summary:'The purpose of the report is to provide an overview. This report presents the methodology and references.',link:'x'}],strand_b:[],strand_c:[]};
const points=I.buildInsights(data).flatMap(g=>g.items);
if(points.length!==0) process.exit(2);
'''
        self.run_node(script)

if __name__=='__main__':
    unittest.main()
