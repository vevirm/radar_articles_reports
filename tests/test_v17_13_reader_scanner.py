import datetime as dt
import json
import re
from pathlib import Path

from scripts import scan_radar as sr

ROOT=Path(__file__).resolve().parents[1]

def test_implied_strategic_context_does_not_need_word_geopolitics():
    text=(
        'EU research and innovation capacity depends on non-EU cloud infrastructure, '
        'while international coordination and standards shape access to frontier systems.'
    )
    ok,families,_=sr.implied_strategic_context(text)
    assert ok
    assert 'dependence_control' in families
    assert len(set(families)) >= 2
    assert 'geopolit' not in text.lower()

def test_single_vague_competitiveness_cue_is_not_enough():
    ok,_,_=sr.implied_strategic_context('European innovation competitiveness is important for growth.')
    assert not ok

def test_gate_can_pass_triangulated_strategic_context():
    title='European research infrastructure dependence and standards'
    abstract=(
        'The European Union research system relies on non-EU cloud infrastructure for advanced scientific computing. '
        'This dependency affects research capacity and access to frontier systems. International coordination and '
        'standard-setting determine how European researchers can use those systems and build alternatives.'
    )
    ev=sr.gate_scope(title,abstract,'',2,'scholarly')
    assert ev['a_focus_pass']
    assert ev['eu_relevance']=='direct'
    assert ev['a_pass']

def test_public_window_is_hard_four_calendar_months():
    assert sr.preserved_corpus_floor({'corpus_start_date':'2025-01-01'},dt.date(2026,8,28)) == dt.date(2026,4,28)
    data={'strand_a':[{'date':'2026-04-27'},{'date':'2026-04-28'}],'strand_b':[],'strand_c':[],'frontier_evidence':[]}
    out,removed=sr.prune_public_window(data,dt.date(2026,4,28))
    assert removed['strand_a']==1
    assert len(out['strand_a'])==1

def test_weak_signals_stay_below_fifteen_percent():
    a=[{'date':'2026-08-01'} for _ in range(85)]
    b=[]
    c=[{'date':f'2026-08-{i:02d}'} for i in range(1,31)]
    kept,_=sr.cap_strand_c_share(a,b,c,0.15)
    assert len(kept)/(len(a)+len(b)+len(kept)) <= 0.15

def test_finding_context_lane_is_live_and_rotatable():
    data={'strand_a':[{'title':'EU critical technologies','summary':'European research capability in semiconductors faces supply chain dependencies and global competition.'}]}
    qs=sr.finding_context_query_bank(data,12)
    assert qs
    assert any('capability' in q.lower() or 'dependency' in q.lower() for q in qs)

def test_priority_people_is_configured_as_fallback_attention():
    cfg=json.loads((ROOT/'radar_config.json').read_text())
    assert cfg['priority_people_trigger_below_scholarly_candidates'] == 18
    assert cfg['weak_signal_followup_queries_per_wave'] == 0
    assert cfg['strand_c_max_share'] == 0.15

def test_reader_claims_remove_biographical_fluff():
    detail=('MIT Science Policy Review spoke with Pranay Kotasthane about the geopolitics of AI chips and the emerging '
            'partnership between India and the European Union. Kotasthane makes a case for open hardware as a concrete '
            'route to strategic autonomy. Chip design engineer by training, Kotasthane is now the Chairperson of a programme.')
    claim=sr.plain_language_claim(detail,'No one builds alone: The geopolitics of AI chips','')
    assert 'Chip design engineer' not in claim
    assert 'Open hardware' in claim

def test_read_page_is_issue_tree_with_five_to_ten_main_issues():
    text=(ROOT/'read/index.html').read_text()
    assert 'Eight issues. Open the branches.' in text
    assert 'sub-node' in text
    titles=re.findall(r"title:'([^']+)'",text)
    assert 5 <= len(titles) <= 10

def test_quick_matrix_exists_and_full_matrix_uses_simple_terms():
    quick=(ROOT/'frontier/quick/index.html').read_text()
    js=(ROOT/'frontier/frontier.js').read_text()
    assert 'without bibliography or method detail' in quick.lower()
    for phrase in ['Stronger on both','More control, more cost','Faster, but dependent','Weaker on both','Firms & scale','Rules & coordination']:
        assert phrase in js
    assert 'Every admitted radar finding reaches the matrix classifier' in js
