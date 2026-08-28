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



def test_english_only_is_fail_closed_for_title_and_body():
    assert not sr.english_record_ok(
        'Demain un cloud souverain européen. Une stratégie pour la souveraineté numérique.',
        '', title='Demain un cloud souverain européen'
    )
    assert not sr.english_record_ok(
        'Naar een menswaardige digitale technologie. Het onderzoek bespreekt beleid en innovatie.',
        '', title='Naar een menswaardige digitale technologie'
    )
    assert not sr.english_record_ok(
        'РОЗВИТОК ЦИФРОВОЇ ЕКОНОМІКИ ЄС У ГЛОБАЛЬНОМУ КОНТЕКСТІ. English abstract text about EU innovation policy.',
        'en', title='РОЗВИТОК ЦИФРОВОЇ ЕКОНОМІКИ ЄС У ГЛОБАЛЬНОМУ КОНТЕКСТІ'
    )
    assert not sr.english_record_ok(
        'Quantum Europe Strategy. L’article présente la logique de la stratégie et discute le rôle attendu du futur Quantum Act.',
        'en', title='Quantum Europe Strategy: Quantum Europe in a changing world'
    )
    assert sr.english_record_ok(
        'Semiconductor supply chains are becoming a strategic dependency for Europe and its industrial policy.',
        '', title='Semiconductor Supply Chains: Strategic Dependencies'
    )


def test_core_message_is_specific_and_at_most_80_characters():
    msg = sr.concise_core_message(
        'The European semiconductor ecosystem is uneven. The results show a diversified but unbalanced European semiconductor ecosystem, with production concentrated in a few countries.',
        'The European semiconductor ecosystem'
    )
    assert len(msg) <= 80
    assert 'unbalanced' in msg.lower() or 'concentrat' in msg.lower()
    assert msg.lower() != 'eu is left behind'

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


def test_gap_allocation_is_balanced_across_opening_and_risk_cells(monkeypatch):
    # Balance is a property of equal scarcity, not a requirement to search A cells
    # after they have already reached the configured target depth.
    counts = {cell: 2 for cell in sr.FRONTIER_CELL_ORDER}
    monkeypatch.setattr(sr, 'frontier_matrix_coverage', lambda previous: (counts, [], ''))
    focus = sr.frontier_gap_plan({}, sr.initial_scan_state({}))
    assert focus['targets']
    assert any(cell.endswith('-A') for cell in focus['targets'])
    assert any(not cell.endswith('-A') for cell in focus['targets'])


def test_frontier_accepts_concrete_committed_opening_but_not_aspiration():
    script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
function countA(title){
 const d={strand_a:[],strand_b:[],strand_c:[{headline:title,source:'Test',date:'2026-08-24',watch_theme:'research talent mobility',why_it_matters:'This changes European strategic autonomy and competitiveness.'}]};
 const v=F.buildFrontier(d,{now:'2026-08-24T09:00:00Z'});
 return v.signals.filter(x=>x.column.id==='A').length;
}
console.log(JSON.stringify({
 plan:countA('EU plans to invest in a new research programme that could strengthen European research capacity.'),
 committed:countA('EU launches and funds a new research programme to expand European research capacity and strengthen competitiveness.'),
 realised:countA('EU attracts and retains international researchers, strengthening European research capacity and reducing reliance on external expertise.')
}));
'''
    out = subprocess.run(['node', '-e', script], cwd=ROOT, text=True, capture_output=True, check=True)
    result = json.loads(out.stdout)
    assert result['plan'] == 0
    assert result['committed'] >= 1
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


def test_current_corpus_has_openings_and_non_openings():
    script = r'''
const fs=require('fs');
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data=JSON.parse(fs.readFileSync('radar.json','utf8'));
const v=F.buildFrontier(data,{now:'2026-08-24T10:29:00Z'});
const c={}; for(const col of F.COLUMNS)c[col.id]=v.signals.filter(x=>x.column.id===col.id).length;
console.log(JSON.stringify(c));
'''
    out = subprocess.run(['node', '-e', script], cwd=ROOT, text=True, capture_output=True, check=True)
    counts = json.loads(out.stdout)
    assert counts['A'] >= 1
    assert counts['B'] + counts['C'] + counts['D'] >= 1
