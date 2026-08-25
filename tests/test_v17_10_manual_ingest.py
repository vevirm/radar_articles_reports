import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

from docx import Document

from scripts import manual_ingest as mi
from scripts import scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, url, html, status=200, content_type='text/html'):
        self.url = url
        self.status_code = status
        self.text = html
        self.content = html.encode('utf-8')
        self.headers = {'content-type': content_type}


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def base_state():
    return {
        'last_updated': '2026-08-25T07:34Z',
        'first_scan_complete': True,
        'scan_results': {'new_a': 2, 'new_b': 0, 'new_c': 1},
        'scan_state': {'institution_seen_fingerprints': {}},
        'strand_a': [], 'strand_b': [], 'strand_c': [], 'frontier_evidence': [],
    }


def write_json_list(tmp_path, rows):
    p = tmp_path / 'manual.json'
    p.write_text(json.dumps(rows), encoding='utf-8')
    return p


def test_docx_manual_parser_handles_current_forthcoming_context_and_last_item(tmp_path):
    p = tmp_path / 'manual.docx'
    doc = Document()
    doc.add_paragraph('A. Talent and research security')
    doc.add_paragraph('A1 Example Institute (29 June 2026). European research talent under geopolitical competition. Example Institute.')
    doc.add_paragraph('https://example.org/report')
    doc.add_paragraph('Type 3 – Science-for-policy & academic. Curated candidate only.')
    doc.add_paragraph('A2 Example University (July 2026). EU research security and international collaboration. Example University.')
    doc.add_paragraph('https://example.edu/paper')
    doc.add_paragraph('4. Expected but not yet published')
    doc.add_paragraph('European Research Area Act – Expected Q3 2026.')
    doc.add_paragraph('5. Essential 2026 context')
    doc.add_paragraph('European Parliament, Resolution on research security, 10 March 2026.')
    doc.add_paragraph('6. Method')
    doc.save(p)
    rows = mi.parse_manual_file(p)
    assert [r['manual_id'] for r in rows[:2]] == ['A1', 'A2']
    assert rows[1]['title'].startswith('EU research security')
    assert any(r['manual_record_status'] == 'forthcoming_unpublished' for r in rows)
    assert any(r['manual_record_status'] == 'context_outside_primary_window' for r in rows)


def test_existing_match_gets_both_provenance_without_duplicate_or_scan_timestamp_change(tmp_path):
    st = base_state()
    st['strand_a'] = [{
        'title': 'European research security under geopolitical competition',
        'authors': 'A', 'source': 'Journal', 'date': '2026-06-01',
        'link': 'https://doi.org/10.1234/example', 'strand': 'A',
        'eu_relevance': 'direct', 'summary': 'Existing admitted evidence.',
        'core_message': 'Existing admitted evidence', 'new_this_scan': False,
    }]
    p = write_json_list(tmp_path, [{
        'id': 'M1', 'title': 'European research security under geopolitical competition',
        'url': 'https://doi.org/10.1234/example', 'date': '2026-06-01'
    }])
    rows = mi.parse_manual_file(p)
    out, summary = mi.apply_manual_ingest(st, rows, source_path=p, fetch=False, now=dt.datetime(2026, 8, 25, 8, 0, tzinfo=dt.timezone.utc))
    assert out['last_updated'] == st['last_updated']
    assert out['scan_results'] == st['scan_results']
    assert len(out['strand_a']) == 1
    assert out['strand_a'][0]['discovery_provenance'] == 'both'
    assert out['strand_a'][0]['provenance'] == ['automated_discovery', 'manual_candidate_ingestion']
    assert summary['counts']['found_in_corpus'] == 1


def test_metadata_only_manual_candidate_is_deferred_and_queued(tmp_path):
    st = base_state()
    p = write_json_list(tmp_path, [{
        'id': 'M1', 'title': 'European semiconductor research and economic security under geopolitical competition',
        'url': 'https://example.org/report', 'date': '2026-06-01'
    }])
    rows = mi.parse_manual_file(p)
    out, summary = mi.apply_manual_ingest(st, rows, source_path=p, fetch=False)
    assert not out['strand_a'] and not out['strand_b']
    assert summary['counts']['deferred'] == 1
    rec = out['manual_ingest']['records'][0]
    assert rec['text_mode'] == 'metadata_only'
    assert rec['decision'] == 'defer_insufficient_or_unverified'
    assert len(out['manual_ingest']['recovery_queue']) == 1


def test_verified_abstract_runs_same_gate_and_can_be_admitted(tmp_path):
    st = base_state()
    title = 'European semiconductor research, strategic dependencies and competitiveness'
    abstract = (
        'The European Union is strengthening semiconductor research and innovation capacity as geopolitical competition and economic security concerns intensify. '
        'The analysis finds that dependence on non-EU fabrication and design-tool suppliers constrains European technological autonomy and can weaken competitiveness. '
        'It compares EU research infrastructure, strategic technology dependencies and innovation capability against the United States and China, and identifies supply resilience as a core policy challenge.'
    )
    html = f'<html><head><title>{title}</title><meta name="description" content="{abstract}"></head><body></body></html>'
    url = 'https://example.org/eu-semiconductor-report'
    p = write_json_list(tmp_path, [{'id': 'M1', 'title': title, 'url': url, 'date': '2026-06-01'}])
    rows = mi.parse_manual_file(p)
    out, summary = mi.apply_manual_ingest(st, rows, source_path=p, fetch=True, session=FakeSession(FakeResponse(url, html)))
    assert summary['counts']['manual_admitted'] >= 1
    assert out['strand_a']
    item = out['strand_a'][0]
    assert item['discovery_provenance'] == 'manual'
    assert item['evidence_status'] == 'verified_primary_source'
    assert item['source_text_mode'] == 'abstract_only'
    assert not item['new_this_scan']


def test_secondary_and_forthcoming_never_auto_admit(tmp_path):
    st = base_state()
    rows_data = [
        {'id': 'M1', 'title': 'Future EU defence R&D instruments', 'url': 'https://example.org/', 'note': 'Exact title to be confirmed; as reported by secondary source', 'date': '2026-07-30'},
        {'id': 'M2', 'title': 'European Research Area Act', 'status': 'forthcoming', 'date': '2026-09-01'},
    ]
    p = write_json_list(tmp_path, rows_data)
    rows = mi.parse_manual_file(p)
    out, summary = mi.apply_manual_ingest(st, rows, source_path=p, fetch=False)
    assert not out['strand_a'] and not out['strand_b']
    assert summary['counts']['forthcoming'] == 1
    assert summary['counts']['secondary_reference'] == 1
    decisions = {r['manual_id']: r['decision'] for r in out['manual_ingest']['records']}
    assert decisions['M2'] == 'defer_forthcoming'


def test_manual_recovery_queue_is_bounded_and_does_not_lower_gate(monkeypatch):
    prev = {'manual_ingest': {'recovery_queue': [
        {'manual_id': f'M{i}', 'title': f'European semiconductor research and economic security under geopolitical competition {i}', 'url': f'https://example.org/r{i}', 'tier': 1}
        for i in range(20)
    ]}}
    monkeypatch.setattr(sr, 'KNOWN_AB_LINKS', {'https://example.org/r0'})
    jobs = sr.manual_recovery_jobs(prev, limit=4)
    assert len(jobs) == 4
    assert all(x['url'] != 'https://example.org/r0' for x in jobs)
    # The queue is discovery only: metadata alone still fails pass 1.
    ev = sr.gate_scope(jobs[0]['title'], '', '', 1, source_kind='institutional')
    assert not ev['a_pass']
    assert ev['aboutness_reason'] == 'insufficient_text'


def test_claimed_and_implied_quadrants_remain_distinct_in_frontier():
    script = r'''
global.RadarInsights=require('./briefing/insights.js');
const F=require('./frontier/frontier.js');
const d={strand_a:[{
  title:'EU compute dependence creates bottlenecks and competitiveness losses',
  source:'Test source', date:'2026-06-01', link:'https://example.org/x', strand:'A', eu_relevance:'direct',
  summary:'European Union AI infrastructure depends on non-EU cloud and chip suppliers. The dependency creates bottlenecks, shortages and competitiveness losses for European research and innovation.',
  core_message:'EU compute dependence creates bottlenecks and competitiveness losses',
  matrix_dimension:'infrastructure', quadrant_claimed:'A', quadrant_implied:'D'
}],strand_b:[],strand_c:[],frontier_evidence:[]};
const v=F.buildFrontier(d,{now:'2026-08-25T10:00:00+03:00'});
const x=v.signals[0];
console.log(JSON.stringify({column:x&&x.column.id,claimed:x&&x.quadrantClaimed,implied:x&&x.quadrantImplied}));
'''
    out = subprocess.run(['node', '-e', script], cwd=ROOT, text=True, capture_output=True, check=True)
    got = json.loads(out.stdout)
    assert got == {'column': 'D', 'claimed': 'A', 'implied': 'D'}


def test_csv_yaml_and_text_manual_formats_are_normalized(tmp_path):
    csv_p = tmp_path / 'manual.csv'
    csv_p.write_text('id,title,url,date,authors\nC1,European research security under geopolitical competition,https://example.org/c1,2026-06-12,Example Author\n', encoding='utf-8')
    csv_rows = mi.parse_manual_file(csv_p)
    assert csv_rows[0]['manual_id'] == 'C1'
    assert csv_rows[0]['title'].startswith('European research security')
    assert csv_rows[0]['date'] == '2026-06-12'

    yaml_p = tmp_path / 'manual.yaml'
    yaml_p.write_text('items:\n  - id: Y1\n    title: European innovation capacity in strategic competition\n    url: https://example.org/y1\n    date: 2026-07-01\n', encoding='utf-8')
    yaml_rows = mi.parse_manual_file(yaml_p)
    assert yaml_rows[0]['manual_id'] == 'Y1'
    assert yaml_rows[0]['url'] == 'https://example.org/y1'

    txt_p = tmp_path / 'manual.txt'
    txt_p.write_text('1. Candidates\nEuropean Commission (9 July 2026). European research and innovation under geopolitical competition. European Commission.\n', encoding='utf-8')
    txt_rows = mi.parse_manual_file(txt_p)
    assert txt_rows and txt_rows[0]['title'].startswith('European research and innovation')
    assert '.pdf' in mi.SUPPORTED


def test_verified_source_without_publication_date_is_not_admitted_or_fabricated(tmp_path):
    st = base_state()
    title = 'European semiconductor research and geopolitical competition'
    abstract = (
        'The European Union is strengthening semiconductor research and innovation capacity under geopolitical competition. '
        'The analysis finds non-EU dependencies constrain technological autonomy and European competitiveness.'
    )
    url = 'https://example.org/no-date'
    p = write_json_list(tmp_path, [{'id': 'M1', 'title': title, 'url': url}])
    rows = mi.parse_manual_file(p)
    out, summary = mi.apply_manual_ingest(st, rows, source_path=p, fetch=True, session=FakeSession(FakeResponse(url, f'<html><head><title>{title}</title><meta name="description" content="{abstract}"></head></html>')))
    assert summary['counts']['manual_admitted'] == 0
    assert not out['strand_a'] and not out['strand_b']
    assert out['manual_ingest']['records'][0]['decision'] == 'defer_insufficient_or_unverified'


def test_generic_homepage_is_not_put_in_exact_url_recovery_queue(tmp_path):
    st = base_state()
    p = write_json_list(tmp_path, [{'id': 'M1', 'title': 'European R&I policy analysis', 'url': 'https://example.org/', 'date': '2026-07-01'}])
    rows = mi.parse_manual_file(p)
    out, summary = mi.apply_manual_ingest(st, rows, source_path=p, fetch=False)
    assert summary['counts']['deferred'] == 1
    assert out['manual_ingest']['recovery_queue'] == []


def test_frontier_numbered_docx_parser_preserves_candidates_weak_signals_and_curator_cells(tmp_path):
    p = tmp_path / 'frontier_additions.docx'
    doc = Document()
    doc.add_paragraph('EU R&I in Geopolitical Context — Additions')
    doc.add_paragraph('1. Knowledge & people')
    doc.add_paragraph('K1 Example Institute (23 June 2026). Europe as a research power under geopolitical competition. Example Institute.')
    doc.add_paragraph('https://example.org/k1')
    doc.add_paragraph('Type 4. Cells: K-A, K-D. Curator mapping only.')
    doc.add_paragraph('2. Infrastructure & inputs')
    doc.add_paragraph('I1 Example Institute (19 May 2026). Europe needs compute capacity for strategic research. Example Institute.')
    doc.add_paragraph('https://example.org/i1')
    doc.add_paragraph('Cells: I-B (primary); I-C.')
    doc.add_paragraph('5. Weak signals')
    doc.add_paragraph('W1 Example News (24 July 2026). Export controls disrupt European research inputs. Example News.')
    doc.add_paragraph('https://example.org/w1')
    doc.add_paragraph('Cells: I-D (primary); R-B.')
    doc.add_paragraph('6. Judgment calls and open items')
    doc.add_paragraph('This paragraph must not become a record.')
    doc.save(p)

    rows = mi.parse_manual_file(p)
    assert [r['manual_id'] for r in rows] == ['K1', 'I1', 'W1']
    assert rows[0]['curator_cells'] == ['K-A', 'K-D']
    assert rows[1]['curator_primary_cell'] == 'I-B'
    assert rows[1]['curator_cell_mapping_status'] == 'manual_hint_not_source_evidence'
    assert rows[2]['manual_candidate_kind'] == 'weak_signal'


def test_user_validated_links_are_recorded_but_do_not_bypass_evidence_or_date_verification(tmp_path):
    st = base_state()
    p = write_json_list(tmp_path, [{
        'id': 'M1',
        'title': 'European research security and strategic competition',
        'url': 'https://example.org/verified-link',
        'date': '2026',
        'note': 'Publication date within the window not yet confirmed.'
    }])
    rows = mi.parse_manual_file(p)
    out, summary = mi.apply_manual_ingest(st, rows, source_path=p, fetch=False, links_validated=True)
    assert summary['links_user_validated'] is True
    assert summary['fetch_attempted'] is False
    assert not out['strand_a'] and not out['strand_b']
    rec = out['manual_ingest']['records'][0]
    assert rec['manual_link_status'] == 'user_validated_reachable'
    assert rec['manual_verification_required'] is True
    assert rec['decision'] == 'defer_insufficient_or_unverified'
    assert out['manual_ingest']['recovery_queue'][0]['manual_link_status'] == 'user_validated_reachable'
