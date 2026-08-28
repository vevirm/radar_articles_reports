from pathlib import Path
import json

from scripts import scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


def current_anchors():
    data = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
    return data.get('strand_a', [])


def test_eu_ri_geopolitics_remains_the_normal_subject_gate():
    ev = sr.gate_scope(
        'National artificial intelligence investment and productivity',
        'This paper studies domestic AI investment, productivity and industrial growth.',
        '', 2, source_kind='scholarly', eu_context_anchors=current_anchors(),
    )
    assert not ev['a_pass']
    assert ev['eu_relevance'] != 'direct'


def test_major_external_ai_shock_can_pass_with_specific_eu_bridge():
    abstract = (
        'China achieved artificial general intelligence in a first demonstrated frontier AI system. '
        'The breakthrough is a step-change in model capability and is being used for scientific research.'
    )
    ev = sr.gate_scope(
        'China achieves artificial general intelligence', abstract, '', 1,
        source_kind='scholarly', eu_context_anchors=current_anchors(),
    )
    assert ev['a_pass'], ev
    assert ev['eu_relevance'] == 'material_external'
    assert ev['a_route'] == 'external-strategic-shock'
    assert ev['external_eu_bridge_is_inference'] is True
    bridge = ev['external_eu_bridge']
    assert 'Europe' in bridge
    assert 'AI research and compute' in bridge
    assert 'technological dependence' in bridge


def test_generic_foreign_ai_news_does_not_use_external_exception():
    abstract = (
        'A Chinese company released a new artificial intelligence product for consumers. '
        'The launch includes new interface features and subscription options.'
    )
    ev = sr.gate_scope(
        'Chinese company releases new AI product', abstract, '', 1,
        source_kind='scholarly', eu_context_anchors=current_anchors(),
    )
    assert not ev['a_pass']
    assert not ev.get('external_eu_bridge')


def test_non_english_publication_can_pass_on_substantive_english_abstract():
    title = 'La politique de recherche dans un monde fragmenté'
    english_abstract = (
        'This study examines European research and innovation under strategic competition with China. '
        'It shows that dependence on external technology suppliers affects research capacity, access to '
        'critical infrastructure and Europe’s ability to compete in frontier technologies.'
    )
    assert sr.english_record_ok(
        f'{title}. {english_abstract}', 'fr', title=title
    )


def test_non_english_title_or_tiny_stub_is_not_enough():
    title = 'La politique de recherche et innovation'
    assert not sr.english_record_ok(
        f'{title}. European research policy.', 'fr', title=title
    )


def test_easy_radar_keeps_full_record_reachable():
    page = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'Show all details' in page
    assert 'All record details' in page
    for label in [
        'Original title', 'Authors', 'Source tier', 'EU relevance', 'Discovery',
        'Relevance / admission note', 'Full available summary', 'Matrix evidence basis',
        'Specific Europe-impact bridge',
    ]:
        assert label in page
    assert 'state.allDetails' in page


def test_config_states_subject_and_language_rules():
    cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
    assert 'subject of Strand A' in cfg['eu_ri_geopolitics_core_rule']
    assert 'non-English publication' in cfg['english_evidence_rule']
    assert cfg['foreign_language_english_evidence_min_words'] >= 20
    assert 'one specific plain-language sentence' in cfg['material_external_shock_rule']


def test_reader_points_are_explicit_complete_and_at_most_120_chars():
    import subprocess
    script = r'''
const fs=require('fs');
const I=require('./briefing/insights.js');
const d=JSON.parse(fs.readFileSync('radar.json','utf8'));
const vague=/^(?:(?:this|these|those|it|they|such)\b|the (?:study|paper|article|report|analysis|research|results?|finding|findings|development|developments|change|changes|trend|trends|issue|issues)\b|to support (?:this|these)|with\b|since\b|because\b|while\b|although\b|building on\b|drawing on\b|based on\b)/i;
let bad=[];
for(const k of ['strand_a','strand_b','strand_c']) for(const x of (d[k]||[])){
  const pts=[['point',I.pointFor(x)]];
  const why=I.whyFor(x); if(why) pts.push(['whyFor',why]);
  if(k==='strand_c') pts.push(['what',I.signalWhat(x)],['why',I.signalWhy(x)]);
  for(const [label,p] of pts){
    if(!p || p.length>120 || /…|\.\.\./.test(p) || vague.test(p) || !/[.!?]$/.test(p)) bad.push([k,label,p]);
  }
}
if(bad.length){console.error(JSON.stringify(bad.slice(0,20),null,2));process.exit(1)}
'''
    subprocess.run(['node', '-e', script], cwd=ROOT, check=True)


def test_vague_ai_act_sentence_is_rewritten_with_explicit_subject():
    source = (
        'These developments also raise novel regulatory and ethical challenges, particularly in light of '
        'the EU’s Artificial Intelligence Act (EU AI Act), which introduces a tiered risk-based framework '
        'for the governance of AI systems'
    )
    point = sr.plain_language_claim('', source)
    assert point == 'The EU AI Act creates a risk-based governance framework for AI systems.'
    assert len(point) <= 120



def test_why_it_matters_is_source_bound_not_generic_topic_filler():
    import subprocess
    script = r'''
const fs=require('fs');
const I=require('./briefing/insights.js');
const d=JSON.parse(fs.readFileSync('radar.json','utf8'));
const all=[...(d.strand_a||[]),...(d.strand_b||[]),...(d.strand_c||[])];
const banned=[
  'EU research funding and international partnerships may change.',
  'European access to key technologies and innovation capacity may change.'
];
for(const x of all){const w=I.whyFor(x);if(banned.includes(w)){console.error(x.title||x.headline,w);process.exit(1)}}
function find(part){return all.find(x=>String(x.title||x.headline||'').includes(part))}
const checks=[
  ['Supercomputers, artificial intelligence',/policy roadmap links supercomputing and AI capacity/i],
  ['National Knowledge Security Guidelines 2026',/Netherlands tightened practical knowledge-security guidance/i],
  ['EU: Shepherded by Brussels',/EU approach has shifted.*de-risking.*economic security/i]
];
for(const [part,re] of checks){const x=find(part);const w=x&&I.whyFor(x);if(!w||!re.test(w)){console.error(part,w);process.exit(1)}}
'''
    subprocess.run(['node', '-e', script], cwd=ROOT, check=True)


def test_main_radar_omits_why_line_when_source_has_no_separate_consequence():
    page = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'whyLine(x)' in page
    assert "return globalThis.RadarInsights?.whyFor?.(x)||''" in page
    assert 'EU research funding and international partnerships may change.' not in page
    assert 'European access to key technologies and innovation capacity may change.' not in page

def test_reader_point_and_package_budgets_are_configured():
    cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
    assert cfg['reader_point_max_chars'] == 120
    assert cfg['package_file_budget'] == 100
