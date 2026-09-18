from __future__ import annotations

from scripts import claim_reasoning_live as live
from scripts import claim_reasoning_shadow as shadow


def _node(cid: str, obj: str, source: str, *, title: str = '', secondary=None, kind='action', direction='expands', status='operating', merit=90):
    return {
        'claim_id': cid,
        'record_key': f'id:{cid}',
        '_record_id': f'r:{cid}',
        '_link': f'https://example.test/{cid}',
        '_title': title or cid,
        '_source': source,
        '_collection': 'strand_a',
        '_primary': True,
        '_new_this_scan': False,
        'era': 'current',
        'object': obj,
        'secondary_objects': list(secondary or []),
        'mechanism': 'builds' if kind == 'action' else 'assesses',
        'direction': direction,
        'kind': kind,
        'status': status,
        'status_date': '2026-09-01',
        'merit': merit,
        'scope': {'level': 'eu', 'countries': []},
        'actor': {'name': source, 'class': 'eu_body'},
        'attributes': {},
    }


def test_future_shock_corpus_can_seed_before_direct_bridge_exists():
    vocab = {
        'objects': {
            'compute.asset': {'cluster': 'compute_ai', 'stake_class': 'capability'},
            'energy.grid': {'cluster': 'materials_energy', 'stake_class': 'capability'},
        }
    }
    nodes = [
        _node('asset', 'compute.asset', 'European programme', title='European compute capacity enters operation'),
        _node('pressure', 'energy.grid', 'Grid authority', title='Grid constraint and power supply shortages affect data centres', kind='diagnosis', direction='contracts', status='delivered'),
    ]
    out = shadow.exploratory_shock_hypotheses(nodes, vocab)
    candidate = next(c for c in out if c.get('capability_object') == 'compute.asset' and c.get('pressure_id') == 'energy')
    assert candidate['product'] == 'shock'
    assert candidate['shock_driver'] is True
    assert candidate['missing_roles'] == ['bridge']
    assert candidate['wow_preliminary'] == 3
    assert candidate['publication_gate_passes'] is False


def test_complete_concentrated_shock_can_compete_for_low_wow_slot():
    candidate = {
        'product': 'shock',
        'status': 'watch',
        'maturity_score': 59,
        'primary_sources': 1,
        'primary_records': 3,
        'primary_role_coverage': 1.0,
        'role_strength_floor_passes': True,
        'shock_driver': True,
    }
    ok, reason = live._presentation_ready(candidate)
    assert ok is True
    assert reason == 'grounded_future_shock'

    candidate['primary_records'] = 2
    ok, _ = live._presentation_ready(candidate)
    assert ok is False


def test_two_source_shock_still_uses_normal_grounding_floor():
    candidate = {
        'product': 'shock',
        'status': 'watch',
        'maturity_score': 44,
        'primary_sources': 2,
        'primary_records': 2,
        'primary_role_coverage': 0.5,
        'role_strength_floor_passes': True,
        'shock_driver': True,
    }
    ok, reason = live._presentation_ready(candidate)
    assert ok is True
    assert reason == 'grounded_future_shock'
