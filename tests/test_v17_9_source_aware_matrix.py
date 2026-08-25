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


def test_bare_eu_defined_as_environmental_uncertainty_is_not_union_scope():
    title = 'ESG effects on the competitive advantage of construction enterprises in China: the mediating role of innovation under environmental uncertainty'
    abstract = (
        'The study examines technological innovation and competitive advantage in Chinese construction enterprises under environmental uncertainty (EU). '
        'Enterprise innovation mediates the relationship between environmental, social and governance factors and competitive advantage. '
        'EU negatively moderates innovation effects on competitive advantage, with business model innovation and technological innovation playing distinct roles.'
    )
    ev = sr.gate_scope(title, abstract, '', 2, source_kind='scholarly')
    assert not ev['a_pass']
    assert ev['eu_relevance'] is None
    assert ev['aboutness_reason'] == 'no_direct_eu'


def test_abstract_only_uses_substantive_connection_not_nonexistent_section_count():
    abstract = (
        'The European Union is strengthening semiconductor research and innovation capacity as geopolitical competition and economic security concerns intensify. '
        'The analysis finds that reducing dependence on external fabrication and design-tool suppliers can improve European technological autonomy while supporting long-term competitiveness. '
        'It examines the EU semiconductor ecosystem, strategic dependencies, research infrastructure and industrial innovation under global technology competition.'
    )
    ev = sr.gate_scope(
        'European semiconductor research, strategic dependencies and competitiveness',
        abstract, '', 2, source_kind='scholarly'
    )
    assert ev['text_mode'] == 'abstract_only'
    assert ev['aboutness_pass']
    assert ev['a_pass']


def test_metadata_only_is_deferred_not_misreported_as_irrelevant():
    ev = sr.gate_scope(
        'European semiconductor research and economic security under geopolitical competition',
        '', '', 2, source_kind='scholarly'
    )
    assert ev['text_mode'] == 'metadata_only'
    assert ev['aboutness_reason'] == 'insufficient_text'
    assert not ev['a_pass']
    # Scope can still be visible from the title; insufficient text is the reason A is not admitted.
    assert ev['eu_relevance'] == 'direct'


def test_gate_diagnostic_keeps_insufficient_text_separate_from_no_eu():
    sr.ADMISSION_DIAGNOSTICS.clear()
    sr._record_ab_gate_diagnostic('fixture', {
        'a_pass': False, 'b_pass': False, 'eu_relevance': 'direct',
        'aboutness_reason': 'insufficient_text', 'ri_evidence': [], 'a_focus_pass': False,
    })
    assert sr.ADMISSION_DIAGNOSTICS['fixture_defer_insufficient_text'] == 1
    assert sr.ADMISSION_DIAGNOSTICS['fixture_reject_no_direct_eu'] == 0


def test_bundled_matrix_is_useful_without_forcing_equal_cell_counts():
    script = r'''
const fs=require('fs');
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const d=JSON.parse(fs.readFileSync('radar.json','utf8'));
const v=F.buildFrontier(d,{now:'2026-08-25T10:04:00+03:00'});
const counts={}; for(const r of F.ROWS)for(const c of F.COLUMNS)counts[`${r.id}-${c.id}`]=v.cells[r.id][c.id].length;
console.log(JSON.stringify({qualifying:v.signals.length,counts}));
'''
    out = subprocess.run(['node', '-e', script], cwd=ROOT, text=True, capture_output=True, check=True)
    result = json.loads(out.stdout)
    counts = result['counts']
    assert result['qualifying'] >= 40
    assert sum(1 for n in counts.values() if n > 0) >= 14
    assert len(set(counts.values())) > 3  # coverage is evidence-led, not an artificial equal fill


def test_content_claim_is_not_prefixed_with_says_that():
    main = (ROOT / 'index.html').read_text(encoding='utf-8')
    frontier = (ROOT / 'frontier' / 'index.html').read_text(encoding='utf-8')
    assert '`This says that ${c}`' not in main
    assert '`This says that ${c}`' not in frontier
    assert "return c||'Concise source claim unavailable'" in main
    assert "return c||'Concise source claim unavailable'" in frontier
