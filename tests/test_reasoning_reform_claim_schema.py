import copy
import json
from pathlib import Path

from scripts.claims_schema import load_vocabulary, validate_claim, validate_document

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "reasoning-reform" / "claim_fixtures.json"
VOCAB = ROOT / "claims_vocabulary.json"


def fixture_doc():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_vocabulary_loads_and_is_internally_consistent():
    vocab = load_vocabulary(VOCAB)
    assert vocab["profile"] == "radar-claims-vocabulary-v1"
    assert vocab["object_aliases"]["compute.capacity_in_europe"] == "compute.capacity"
    assert vocab["objects"]["compute.gigafactory"]["stake_class"] == "flagship"
    assert "secures" in vocab["absorbers"]


def test_all_hand_extraction_fixtures_validate():
    doc = fixture_doc()
    assert len(doc["claims"]) == 13  # 11 records; records 1 and 6 have a second claim.
    assert validate_document(doc, load_vocabulary(VOCAB)) == []


def test_fixture_has_one_to_three_claims_per_record():
    doc = fixture_doc()
    counts = {}
    for claim in doc["claims"]:
        counts[claim["record_key"]] = counts.get(claim["record_key"], 0) + 1
    assert len(counts) == 11
    assert min(counts.values()) >= 1
    assert max(counts.values()) <= 3


def test_unknown_object_fails_closed():
    claim = copy.deepcopy(fixture_doc()["claims"][0])
    claim["object"] = "made.up_object"
    problems = validate_claim(claim, load_vocabulary(VOCAB))
    assert any("unknown object" in p for p in problems)


def test_alias_is_not_silently_coerced():
    claim = copy.deepcopy(fixture_doc()["claims"][5])
    claim["object"] = "compute.capacity_in_europe"
    problems = validate_claim(claim, load_vocabulary(VOCAB))
    assert any("use canonical 'compute.capacity'" in p for p in problems)


def test_unknown_mechanism_fails_closed():
    claim = copy.deepcopy(fixture_doc()["claims"][0])
    claim["mechanism"] = "magically_connects"
    problems = validate_claim(claim, load_vocabulary(VOCAB))
    assert any("unknown mechanism" in p for p in problems)


def test_spec_url_prefix_is_rejected_in_favour_of_repository_link_prefix():
    claim = copy.deepcopy(fixture_doc()["claims"][0])
    claim["record_key"] = "url:https://example.org/item"
    problems = validate_claim(claim, load_vocabulary(VOCAB))
    assert any("repository canonical prefix is 'link:'" in p for p in problems)


def test_historical_identity_and_era_must_agree():
    claim = copy.deepcopy(fixture_doc()["claims"][-1])
    claim["era"] = "current"
    problems = validate_claim(claim, load_vocabulary(VOCAB))
    assert any("historical record_key requires era='historical'" in p for p in problems)


def test_member_state_scope_requires_country():
    claim = copy.deepcopy(fixture_doc()["claims"][3])
    claim["scope"]["countries"] = []
    problems = validate_claim(claim, load_vocabulary(VOCAB))
    assert any("must identify at least one country" in p for p in problems)


def test_provisional_origin_and_flag_must_agree():
    claim = copy.deepcopy(fixture_doc()["claims"][0])
    claim["origin"] = "provisional"
    claim["provisional"] = False
    problems = validate_claim(claim, load_vocabulary(VOCAB))
    assert any("origin='provisional'" in p for p in problems)


def test_more_than_three_claims_for_one_record_is_rejected():
    doc = fixture_doc()
    base = copy.deepcopy(doc["claims"][0])
    base["claim_id"] = "c:spec-eurohpc-2026-07-30:3"
    fourth = copy.deepcopy(base)
    fourth["claim_id"] = "c:spec-eurohpc-2026-07-30:4"
    doc["claims"].extend([base, fourth])
    problems = validate_document(doc, load_vocabulary(VOCAB))
    assert any("more than 3 claims" in p for p in problems)


def test_duplicate_claim_id_is_rejected():
    doc = fixture_doc()
    duplicate = copy.deepcopy(doc["claims"][2])
    duplicate["record_key"] = "id:another-record"
    doc["claims"].append(duplicate)
    problems = validate_document(doc, load_vocabulary(VOCAB))
    assert any("duplicate claim_id" in p for p in problems)

def test_partial_month_status_date_is_preserved_without_inventing_a_day():
    claim = copy.deepcopy(fixture_doc()["claims"][0])
    claim["status_date"] = "2025-03"
    claim["status_date_precision"] = "month"
    assert validate_claim(claim, load_vocabulary(VOCAB)) == []


def test_partial_year_status_date_is_preserved_without_inventing_month_or_day():
    claim = copy.deepcopy(fixture_doc()["claims"][0])
    claim["status_date"] = "2013"
    claim["status_date_precision"] = "year"
    assert validate_claim(claim, load_vocabulary(VOCAB)) == []


def test_partial_status_date_requires_matching_precision_marker():
    claim = copy.deepcopy(fixture_doc()["claims"][0])
    claim["status_date"] = "2025-03"
    problems = validate_claim(claim, load_vocabulary(VOCAB))
    assert any("status_date_precision='month'" in p for p in problems)


def test_invalid_partial_date_is_rejected():
    claim = copy.deepcopy(fixture_doc()["claims"][0])
    claim["status_date"] = "2025-13"
    claim["status_date_precision"] = "month"
    problems = validate_claim(claim, load_vocabulary(VOCAB))
    assert any("status_date must be YYYY" in p for p in problems)


def test_deadline_stays_day_precision():
    claim = copy.deepcopy(fixture_doc()["claims"][0])
    claim["deadline"] = "2026-11"
    problems = validate_claim(claim, load_vocabulary(VOCAB))
    assert any("deadline must be null/absent or YYYY-MM-DD" in p for p in problems)

