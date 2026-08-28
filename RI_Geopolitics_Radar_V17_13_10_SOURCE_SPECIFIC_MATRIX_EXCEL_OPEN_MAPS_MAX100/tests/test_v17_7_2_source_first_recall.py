import sys, types
try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules['feedparser'] = types.ModuleType('feedparser')

from scripts import scan_radar as sr


def test_contextual_a_accepts_external_position_evidence_without_geo_word():
    ev = sr.gate_scope(
        "Europe's research and innovation capacity relative to the United States and China",
        "The study compares Europe with the United States and China and finds a widening research capacity gap and weaker innovation performance in semiconductor and quantum technology fields.",
        "", 2, source_kind="scholarly",
    )
    assert ev['a_pass']
    assert ev['a_route'] == 'external-position-evidence'
    assert not ev['geo_evidence']  # proves this is the bounded expansion route


def test_contextual_a_does_not_admit_generic_eu_innovation_performance():
    ev = sr.gate_scope(
        "European innovation performance in regional ecosystems",
        "The paper measures innovation capacity and R&D performance across European regions and universities.",
        "", 2, source_kind="scholarly",
    )
    assert not ev['a_pass']


def test_contextual_a_rejects_facility_access_page_noise():
    ev = sr.gate_scope(
        "PAMEC, Properties of Actinide Materials under Extreme Conditions",
        "The facility provides access for basic research. Horizon Europe calls are open to participants from third countries under the work programme.",
        "", 1, source_kind="scholarly",
    )
    assert not ev['a_pass']


def test_method_first_validated_ri_future_method_can_pass_without_we_develop():
    ev = sr.gate_scope(
        "Bibliometric forecasting methodology for emerging research fronts",
        "The methodology forecasts emerging research and innovation trajectories. We validate the workflow against held-out publication networks and benchmark its robustness across technology fields.",
        "", 2, source_kind="scholarly",
    )
    assert ev['b_pass']
    assert ev['b_route'] == 'ri-futures-analytic-method'


def test_recall_profile_change_resets_search_progress_but_not_by_quality_change_alone():
    prev = {
        'last_updated': '2026-08-23T14:49Z',
        'recall_profile_version': 'older',
        'scan_state': {
            'version': sr.INCREMENTAL_STATE_VERSION,
            'source_expansion_version': sr.SOURCE_EXPANSION_VERSION,
            'openalex_cursor': 61, 'crossref_broad_cursor': 49, 'crossref_priority_cursor': 225,
            'institution_cursor': 36, 'strand_b_method_cursor': 6,
            'institution_seen_fingerprints': {'old|2026-08-01': '2026-08-23T00:00Z'},
            'result_depth': {'openalex': {'x': 3}, 'crossref_broad': {}, 'crossref_priority': {}},
            'backfill': {'openalex': True, 'crossref_broad': True, 'crossref_priority': True, 'institutions': True},
            'completed_cycles': {}, 'cycle_failed': {},
        },
    }
    state = sr.initial_scan_state(prev)
    assert state['recall_reset_this_run'] is True
    assert state['openalex_cursor'] == 0
    assert state['crossref_broad_cursor'] == 0
    assert state['crossref_priority_cursor'] == 0
    assert state['institution_seen_fingerprints'] == {}
    assert not any(state['backfill'].values())


def test_source_first_priority_journal_lane_is_enabled_and_bounded():
    assert 4 <= int(sr.CONFIG['crossref_source_first_journals_per_scan']) <= 12
    assert int(sr.CONFIG['crossref_source_first_rows']) <= 100
    assert sr.CONFIG['recall_profile_version'] == 'v17.7.2-source-first-contextual-recall'


def test_scenario_construction_requires_actual_futures_context():
    ev = sr.gate_scope(
        "Construction and Quantitative Evaluation of Basketball Smart Teaching Scenarios Integrating Ideological and Political Elements",
        "This study proposes an intelligent scenario construction and evaluation framework based on multimodal sensing and digital twin technologies for basketball teaching.",
        "", 2, source_kind="scholarly",
    )
    assert not ev['b_pass']


def test_future_scenario_building_still_passes():
    ev = sr.gate_scope(
        "A Participatory Future Scenario-Building Methodology for Europe's Just Transition",
        "The project develops a scenario-building methodology to anticipate socio-technical transformations through 2050 and supports strategic decision-making under uncertainty.",
        "", 2, source_kind="scholarly",
    )
    assert ev['b_pass']
