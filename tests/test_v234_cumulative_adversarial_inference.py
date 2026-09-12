import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from high_order_inference import _build_candidate, refresh_high_order_inference, feedback_queries  # noqa: E402


def _row(title, source, *, primary=True, strand='A', new=False, quality=95):
    return {
        '_identity': f'{source}:{title}', '_source': source, '_primary': primary,
        '_historical': strand == 'H', '_strand': strand, '_weight': 1.0 if primary else .3,
        '_quality': quality, '_text': title, '_topics': set(), 'new_this_scan': new,
        'title': title, 'date': '2026-09-01'
    }


def _real_state():
    data = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
    hist = json.loads((ROOT / 'historical' / 'historical.json').read_text(encoding='utf-8'))
    data['historical_context'] = [x for x in hist.get('items', []) if str(x.get('strand', '')).upper() == 'A']
    return refresh_high_order_inference(data, {}, data.get('run_completed_at'))


def test_cannot_close_required_role_with_c_context():
    a1 = _row('primary one', 'S1')
    a2 = _row('primary two', 'S2')
    c = _row('weak signal only', 'News', primary=False, strand='C')
    cand = _build_candidate(
        grammar='test', product='risk', level=4, key='x', label='x',
        role_rows={'one': [a1], 'two': [a2], 'three': [c]}, required_roles=['one', 'two', 'three'],
        context_rows=[c], counter_rows=[], min_records=3, min_sources=2,
        support_queries=['support'], falsifier_queries=['deny'],
    )
    assert cand is not None
    assert cand['status'] != 'qualified'
    assert 'three' in cand['missing_links']


def test_every_publication_is_sparse_and_adversarially_tested():
    state = _real_state()
    by_id = {c['id']: c for c in state['candidates']}
    for product, ids in state['publications'].items():
        assert len(ids) <= 2
        for cid in ids:
            c = by_id[cid]
            assert c['status'] == 'qualified'
            assert c['denial_tested'] is True
            assert c['falsifier_queries']
            assert c['synthesis_across_records'] is True


def test_shock_dependency_grammar_does_not_cross_product_social_topics():
    state = _real_state()
    shock_labels = [c['topic_label'].lower() for c in state['candidates'] if c['grammar_id'] == 'omitted_dependency_chain']
    assert shock_labels
    assert not any('science diplomacy' in x or 'openness' in x or 'research security' in x for x in shock_labels)


def test_trend_balance_is_a_100_point_tug_of_war():
    state = _real_state()
    trends = [c for c in state['candidates'] if c['product'] == 'trend' and c.get('trend_balance')]
    assert trends
    b = trends[0]['trend_balance']
    assert b['left_pull'] + b['right_pull'] == 100
    assert b['raw_left_pull'] + b['raw_right_pull'] == 100
    assert b['left_actions'] >= 3 and b['right_actions'] >= 3
    assert b['left_sources'] >= 2 and b['right_sources'] >= 2


def test_feedback_queries_include_support_and_falsifier_pressure():
    state = _real_state()
    qs = feedback_queries(state, 8)
    assert 2 <= len(qs) <= 8
    candidates = [c for c in state['candidates'] if c['status'] in {'watch', 'dormant', 'qualified'}]
    support = {q for c in candidates for q in c.get('support_queries', [])}
    falsify = {q for c in candidates for q in c.get('falsifier_queries', [])}
    assert any(q in support for q in qs)
    assert any(q in falsify for q in qs)


def test_b_is_not_part_of_high_order_world_evidence_contract():
    src = (ROOT / 'scripts' / 'high_order_inference.py').read_text(encoding='utf-8')
    assert '("strand_b"' not in src
    assert 'Strand C and history may' in src


def test_scanner_keeps_a_protected_while_slightly_expanding_b_and_c():
    cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
    assert cfg['strand_a_protected_scholarly_queries_per_source'] >= 20
    assert 6 <= cfg['queries_b_method_per_scan'] <= 12
    assert cfg['foresight_author_followup_per_scan'] == 10
    assert cfg['weak_signal_followup_queries_per_wave'] == 10
    assert cfg['high_order_inference_news_queries_per_scan'] == 4
    scanner = (ROOT / 'scripts' / 'scan_radar.py').read_text(encoding='utf-8')
    assert 'oa_a_prefix' in scanner and 'cr_a_prefix' in scanner
    assert 'high_order_news_focus' in scanner


def test_reader_products_consume_only_selected_high_order_findings():
    priorities = (ROOT / 'priorities' / 'priorities.js').read_text(encoding='utf-8')
    shocks = (ROOT / 'shocks' / 'index.html').read_text(encoding='utf-8')
    trends = (ROOT / 'trends' / 'trends.js').read_text(encoding='utf-8')
    phenomena = (ROOT / 'phenomena' / 'index.html').read_text(encoding='utf-8')
    assert 'publications?.[kind]' in priorities
    assert 'publications?.shock' in shocks
    assert 'publications?.trend' in trends
    assert 'publications?.continuity' in phenomena


def test_every_new_a_or_c_record_triggers_the_post_scan_thinking_pass_even_if_nothing_surfaces():
    data = {
        'strand_a': [{'title':'A mundane new primary record', 'source':'Primary', 'date':'2026-09-08', 'new_this_scan':True}],
        'strand_b': [{'title':'A methods paper', 'source':'Methods', 'date':'2026-09-08', 'new_this_scan':True}],
        'strand_c': [{'headline':'A mundane new weak signal', 'source':'Trusted News', 'date':'2026-09-08', 'new_this_scan':True}],
        'frontier_evidence': [],
        'historical_context': [],
    }
    state = refresh_high_order_inference(data, {}, '2026-09-08T20:00:00Z')
    trig = state['trigger_summary']
    assert trig['thinking_pass_ran'] is True
    assert trig['new_primary_records_evaluated'] == 1
    assert trig['new_weak_signal_records_evaluated'] == 1
    # Strand B is independent methods evidence and is intentionally not evaluated here.
    assert not state['publications']['shock']


def test_emergent_trend_publishes_raw_vs_independence_adjusted_range_not_false_precision():
    state = _real_state()
    trend = next(c for c in state['candidates'] if c.get('grammar_id') == 'opposing_actions_same_object')
    b = trend['trend_balance']
    assert b['left_range'] == [min(b['left_pull'], b['raw_left_pull']), max(b['left_pull'], b['raw_left_pull'])]
    assert b['right_range'] == [min(b['right_pull'], b['raw_right_pull']), max(b['right_pull'], b['raw_right_pull'])]
    assert b['left_actions'] != b['right_actions']
    assert b['left_adjusted_points'] > 0 and b['right_adjusted_points'] > 0


def test_complete_level5_can_qualify_same_scan_without_waiting_for_future_refutation():
    rows = {
        'a': [_row('role a', 'S1', new=True)],
        'b': [_row('role b', 'S2')],
        'c': [_row('role c', 'S3')],
        'd': [_row('role d', 'S4')],
    }
    cand = _build_candidate(
        grammar='same-scan-test', product='shock', level=5, key='x', label='x',
        role_rows=rows, required_roles=['a', 'b', 'c', 'd'],
        context_rows=[], counter_rows=[], min_records=4, min_sources=4,
        support_queries=['close missing bridge'], falsifier_queries=['alternative explanation', 'absorber'],
    )
    assert cand is not None
    assert cand['status'] == 'qualified'
    assert cand['reader_eligible'] is True
    assert cand['touched_this_scan'] is True
    assert cand['counter_records'] == 0


def test_high_order_findings_accumulate_and_do_not_retire_after_one_missed_detection():
    old = {
        'profile_version':'x',
        'publications':{'shock':['l45:test:x']},
        'candidates':[{
            'id':'l45:test:x','grammar_id':'test','product':'shock','inferential_distance':5,
            'topic_key':'x','topic_label':'x','status':'qualified','score':95,'reader_eligible':True,
            'denial_tested':True,'falsifier_queries':['deny x'],'support_queries':['support x'],
            'synthesis_across_records':True,'primary_sources':4,'primary_records':6,
            'fingerprint':'old','first_seen_at':'2026-08-01T00:00:00Z','last_updated_at':'2026-08-20T00:00:00Z'
        }]
    }
    data={'strand_a':[],'strand_b':[],'strand_c':[],'frontier_evidence':[],'historical_context':[]}
    state=refresh_high_order_inference(data, old, '2026-09-08T20:00:00Z')
    c=next(x for x in state['candidates'] if x['id']=='l45:test:x')
    assert c['status']=='qualified'
    assert c['lifecycle']=='carried_forward'
    assert c['missed_detection_scans']==1
    assert c['id'] in state['publications']['shock']


def test_repeated_non_detection_weakens_slowly_but_never_deletes_candidate_memory():
    candidate={
        'id':'l45:test:x','grammar_id':'test','product':'shock','inferential_distance':5,
        'topic_key':'x','topic_label':'x','status':'qualified','score':95,'reader_eligible':True,
        'denial_tested':True,'falsifier_queries':['deny x'],'support_queries':['support x'],
        'synthesis_across_records':True,'primary_sources':4,'primary_records':6,
        'fingerprint':'old','first_seen_at':'2026-08-01T00:00:00Z','last_updated_at':'2026-08-20T00:00:00Z'
    }
    state={'publications':{'shock':['l45:test:x']},'candidates':[candidate]}
    data={'strand_a':[],'strand_b':[],'strand_c':[],'frontier_evidence':[],'historical_context':[]}
    for i in range(1,7):
        state=refresh_high_order_inference(data,state,f'2026-09-{8+i:02d}T20:00:00Z')
    c=next(x for x in state['candidates'] if x['id']=='l45:test:x')
    assert c['status']=='dormant'
    assert c['missed_detection_scans']==6
    assert c['id'] not in state['publications']['shock']
    assert any(x['id']=='l45:test:x' for x in state['candidates'])


def test_new_candidate_does_not_automatically_replace_qualified_incumbent_publication():
    from high_order_inference import _select_publications
    base={
        'product':'shock','inferential_distance':5,'status':'qualified','reader_eligible':True,
        'denial_tested':True,'falsifier_queries':['deny'],'synthesis_across_records':True,
        'primary_sources':4,'primary_records':6,'reader_title':'x','reader_summary':'x'
    }
    incumbent=dict(base,id='l45:g1:old',grammar_id='g1',topic_key='old',topic_label='old',score=94)
    newcomer=dict(base,id='l45:g2:new',grammar_id='g2',topic_key='new',topic_label='new',score=97)
    pubs=_select_publications([incumbent,newcomer],{'shock':['l45:g1:old']})
    # There is a free second slot, so the new candidate is added rather than deleting the old one.
    assert pubs['shock']==['l45:g2:new','l45:g1:old'] or pubs['shock']==['l45:g1:old','l45:g2:new']
    third=dict(base,id='l45:g3:newer',grammar_id='g3',topic_key='newer',topic_label='newer',score=98)
    pubs2=_select_publications([incumbent,newcomer,third],{'shock':['l45:g1:old','l45:g2:new']})
    assert 'l45:g1:old' in pubs2['shock'] and 'l45:g2:new' in pubs2['shock']


def test_production_detectors_use_reasoning_grammars_not_worked_example_shortcuts():
    import high_order_inference as hoi
    names = {fn.__name__ for fn in hoi.DETECTORS}
    assert '_generic_dependency_chains' in names
    assert '_generic_conflicting_criteria' in names
    assert '_generic_latent_substitute' in names
    assert '_generic_success_metric_gap' in names
    assert '_generic_comparative_advantage' in names
    assert '_generic_practice_precedes_doctrine' in names
    assert '_generic_concentration_distribution_tension' in names
    # These exact worked-example detectors remain useful as fixtures/specifications,
    # but production must not get a privileged answer path through them.
    assert '_omitted_dependency' not in names
    assert '_conflicting_criteria' not in names
    assert '_latent_substitute' not in names
    assert '_success_metric' not in names
    assert '_comparative_advantage' not in names
    assert '_practice_precedes_doctrine' not in names
    assert '_concentration_distribution_tension' not in names


def test_generic_dependency_grammar_can_reconstruct_qualified_shape_without_specific_detector():
    # The exact live-corpus topic may change after evidence/source cleanup. The contract here
    # is that the generic grammar still reconstructs at least one qualified dependency chain
    # without relying on a worked-example detector.
    state = _real_state()
    generic = [
        c for c in state['candidates']
        if c.get('grammar_id') == 'omitted_dependency_chain'
        and c.get('generic_grammar')
        and c.get('status') == 'qualified'
    ]
    assert generic
    c = generic[0]
    assert c['synthesis_across_records'] is True
    assert c['primary_sources'] >= 4
    assert not c['missing_links']
