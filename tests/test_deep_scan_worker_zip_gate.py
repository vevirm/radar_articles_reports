"""No worker ZIP can label an importer-rejected result 'upload ready'."""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.prepare_deep_scan_package import CHECKPOINT_TOOL, _portable_importer_rules

ROOT = Path(__file__).resolve().parents[1]


def _valid_result():
    return {
        'record_key': 'historical:id:test-1', 'source_hash': 'source-1',
        'identity_hash': 'identity-1',
        'verification': {
            'identity_verified': True, 'evidence_depth': 'official_full_document',
            'verification_note': 'Read the full authoritative source text from publisher site.',
            'retrieval_attempts': [{'step': 'supplied_url', 'outcome': 'success',
                                    'note': 'Read source document at https://example.org/report'}],
            'recovered_sources': [{'kind':'official_full_document', 'evidence_used':True,
                                   'url':'https://example.org/report', 'title':'Example research report'}],
        },
        'admission': {'decision':'keep', 'target_strand':'A', 'reason_code':'A_SUBSTANTIVE_EU_RI',
                      'reason':'Original primary report studies European research capacity.'},
        'metadata_correction': {'fields':{}, 'unset':[], 'reason':''},
        'duplicate': {'status':'unique', 'duplicate_of':'', 'reason':''},
        'reader_title':'Europe research infrastructure',
        'reader_what':'The research report compares European research infrastructure capacity and policy.',
        'reader_why':'The infrastructure comparison informs European research funding priorities.',
        'reader_more':'A published report compares European research infrastructure evidence across national systems.',
        'deep_analysis': {'work_kind':'research report', 'research_question':'What capacity is available?',
                          'main_finding':'Capacity differs across European systems.',
                          'method_or_basis':'Evidence synthesis of the report data.',
                          'qualification':'Comparative findings do not establish causal policy effects.',
                          'radar_relevance':'EU research infrastructure evidence.',
                          'why_supported':True, 'confidence':'high'},
        'claims': [{'object':'innovation.system_performance', 'secondary_objects':[],
                    'actor':{'name':'European Commission Joint Research Centre','class':'eu_body'},
                    'mechanism':'assesses','direction':'unchanged', 'status':'delivered',
                    'status_date':'2026', 'status_date_precision':'year',
                    'scope':{'level':'eu','countries':[]}, 'kind':'diagnosis',
                    'qualification':'Comparative findings do not establish causal policy effects.',
                    'text':'The report describes variation in European research capacity.',
                    'confidence':'high'}],
    }


@pytest.fixture
def package(tmp_path):
    pkg = tmp_path / 'worker'
    pkg.mkdir()
    result = _valid_result()
    job = {'record_key':result['record_key'], 'source_hash':result['source_hash'],
           'identity_hash':result['identity_hash'], 'corpus_scope':'historical', 'strand':'A',
           'required_output':{'record_key':result['record_key'], 'source_hash':result['source_hash'], 'identity_hash':result['identity_hash']}, 'automatic_scanner':{},
           'possible_duplicates':[]}
    (pkg / 'manifest.json').write_text(json.dumps({'package_id':'test-worker-zip',
                                                    'batches':[{'file':'batch.json'}]}))
    (pkg / 'batch.json').write_text(json.dumps({'jobs':[job]}))
    (pkg / 'IMPORTER_RULES.py').write_text(_portable_importer_rules())
    (pkg / 'CHECKPOINT.py').write_text(CHECKPOINT_TOOL)
    shutil.copyfile(ROOT / 'scripts/deep_scan_offline_check.py',pkg / 'CHECK_RESULTS.py')
    shutil.copyfile(ROOT / 'scripts/claims_schema.py',pkg / 'claims_schema.py')
    shutil.copyfile(ROOT / 'claims_vocabulary.json',pkg / 'claims_vocabulary.json')
    return pkg, result


def _check(pkg, result):
    (pkg / 'result.json').write_text(json.dumps({'format':'radar-deep-scan-results-v2',
      'claims_format':'radar-claims-v1', 'package_id':'test-worker-zip', 'results':[result]}))
    return subprocess.run([sys.executable, 'CHECK_RESULTS.py', 'result.json'], cwd=pkg,
                          text=True, capture_output=True)


def test_valid_historical_a_passes(package):
    pkg, row = package
    checked = _check(pkg, row)
    assert checked.returncode == 0, checked.stdout + checked.stderr


def test_historical_keep_c_blocked(package):
    pkg, row = package
    row['admission']['target_strand'] = 'C'
    checked = _check(pkg, row)
    assert checked.returncode == 1
    assert 'target_strand A/B' in checked.stdout


def test_missing_country_blocked(package):
    pkg, row = package
    row['claims'][0]['scope'] = {'level':'associated_country','countries':[]}
    checked = _check(pkg, row)
    assert checked.returncode == 1
    assert 'scope.countries must identify at least one country' in checked.stdout


def test_doi_correction_blocked(package):
    pkg, row = package
    row['metadata_correction']['fields'] = {'doi':'10.0000/fake'}
    row['metadata_correction']['reason'] = 'An untrusted bibliographic guess changed the DOI.'
    checked = _check(pkg, row)
    assert checked.returncode == 1
    assert 'unsafe metadata correction fields: doi' in checked.stdout


def test_assemble_fails_closed_and_then_passes(package):
    pkg, row = package
    broken = copy.deepcopy(row)
    broken['admission']['target_strand'] = 'C'
    (pkg / 'one.json').write_text(json.dumps(broken))
    saved = subprocess.run([sys.executable,'CHECKPOINT.py','add','one.json'],cwd=pkg, capture_output=True,text=True)
    assert saved.returncode == 1, saved.stdout + saved.stderr
    assert 'failed importer preflight' in saved.stderr
    # An old/hand-edited checkpoint can still contain bad work: final assembly must reject it.
    (pkg / 'WORK_PROGRESS.json').write_text(json.dumps({'package_id':'test-worker-zip',
                                                        'completed':{row['record_key']:broken}}))
    assembled = subprocess.run([sys.executable,'CHECKPOINT.py','assemble'],cwd=pkg,capture_output=True,text=True)
    assert assembled.returncode == 1
    assert 'CHECK_RESULTS.py rejected' in assembled.stderr
    assert not (pkg / 'deep_scan_results.json').exists()
    # A new package/checkpoint can instead assemble a valid row successfully.
    (pkg / 'WORK_PROGRESS.json').write_text(json.dumps({'package_id':'test-worker-zip',
                                                        'completed':{row['record_key']:row}}))
    assembled = subprocess.run([sys.executable,'CHECKPOINT.py','assemble'],cwd=pkg,capture_output=True,text=True)
    assert assembled.returncode == 0, assembled.stdout + assembled.stderr
    assert (pkg / 'deep_scan_results.json').exists()
