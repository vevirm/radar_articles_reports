import json
import subprocess
import sys
import types
from pathlib import Path

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    mod = types.ModuleType('feedparser')
    mod.parse = lambda *a, **k: types.SimpleNamespace(entries=[])
    sys.modules['feedparser'] = mod

from scripts import scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


def test_non_english_metadata_is_rejected():
    assert not sr.english_record_ok('European research security and innovation policy', 'de')
    assert sr.english_record_ok('European research security and innovation policy', 'en')


def test_table_tennis_industry_paper_is_out_of_scope():
    ev = sr.gate_scope(
        'Why China Dominates the Global Table Tennis Equipment Industry: Competitive Challenges for European Manufacturers',
        'The paper studies R&D investment and innovation in sports equipment manufacturing under Chinese competition.',
        '', 2, source_kind='scholarly',
    )
    assert not ev['a_pass']


def test_generic_foresight_without_policy_or_ri_destination_is_not_b():
    ev = sr.gate_scope(
        'Comparing horizon scanning methods for strategic foresight',
        'We develop and benchmark a horizon scanning methodology under deep uncertainty.',
        '', 2, source_kind='scholarly',
    )
    assert not ev['b_pass']


def test_specific_external_strategic_shock_can_prefilter_but_generic_ai_cannot():
    assert sr.factual_news(
        'US tightens export controls on advanced AI chips to China',
        'The controls restrict semiconductor research equipment and deepen strategic competition.',
    )
    assert not sr.factual_news(
        'US company launches a faster AI assistant',
        'The product adds new consumer features and a redesigned interface.',
    )


def test_gap_allocation_does_not_hunt_openings_while_risk_cells_are_sparse():
    data = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
    state = sr.initial_scan_state(data)
    focus = sr.frontier_gap_plan(data, state)
    assert focus['targets']
    assert all(not cell.endswith('-A') for cell in focus['targets'])


def test_frontier_requires_realised_gain_for_opening():
    script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
function countA(title){
 const d={strand_a:[],strand_b:[],strand_c:[{headline:title,source:'Test',date:'2026-08-24',watch_theme:'research talent mobility',why_it_matters:'This changes European strategic autonomy and competitiveness.'}]};
 const v=F.buildFrontier(d,{now:'2026-08-24T09:00:00Z'});
 return v.signals.filter(x=>x.column.id==='A').length;
}
console.log(JSON.stringify({
 plan:countA('EU plans to attract and retain international researchers through a new funding call to strengthen European research capacity.'),
 realised:countA('EU attracts and retains international researchers, strengthening European research capacity and reducing reliance on external expertise.')
}));
'''
    out = subprocess.run(['node', '-e', script], cwd=ROOT, text=True, capture_output=True, check=True)
    result = json.loads(out.stdout)
    assert result['plan'] == 0
    assert result['realised'] >= 1


def test_paper_card_fallback_is_specific_not_generic():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'function paperSpecificMessage' in html
    assert 'Geopolitical pressures are reshaping Europe’s research, technology and innovation choices.' not in html


def test_surgical_saved_cleanup_does_not_mass_purge_broad_journals():
    data = {
        'strand_a': [
            {
                'title': 'EU–China research cooperation under a de-risking framework',
                'summary': 'The paper examines research security and EU science policy under strategic competition.',
                'source_tier': 'Tier 2 broad journal', 'type': 'peer-reviewed article', 'link': 'https://doi.org/10.1/example'
            },
            {
                'title': 'Why China Dominates the Global Table Tennis Equipment Industry: Competitive Challenges for European Manufacturers',
                'summary': 'The paper studies R&D investment in sports equipment.',
                'source_tier': 'Tier 2 broad journal', 'type': 'peer-reviewed article', 'link': 'https://doi.org/10.1/sport'
            },
        ],
        'strand_b': [], 'strand_c': []
    }
    cleaned, stats = sr.surgical_precision_cleanup(data)
    assert len(cleaned['strand_a']) == 1
    assert 'EU–China research cooperation' in cleaned['strand_a'][0]['title']
    assert stats['strand_a_removed'] == 1
