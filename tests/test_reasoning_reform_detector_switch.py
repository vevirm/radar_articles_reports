from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts import claim_reasoning_live as live
from scripts.claim_reasoning_shadow import flatten_claims
from scripts.claims_schema import load_vocabulary

ROOT = Path(__file__).resolve().parents[1]
VOCAB = load_vocabulary(ROOT / "claims_vocabulary.json")


def _row(text: str, strand: str = "A") -> dict:
    return {
        "title": text,
        "source": "European Commission",
        "date": "2026-09-18",
        "link": "https://example.test/" + strand.lower() + "/1",
        "strand": strand,
        "eu_relevance": "direct",
        "realisation_status": "announced",
        "summary": text,
        "new_this_scan": True,
    }


def test_provisional_claim_is_schema_valid_and_preserves_authority_line():
    row = _row("European Commission announced new compute capacity and public procurement for AI infrastructure.")
    c = live.provisional_claim_for_row(row, VOCAB)
    assert c is not None
    assert c["origin"] == "provisional"
    assert c["provisional"] is True
    assert c["status_date"] == "2026-09-18"

    a = copy.deepcopy(row)
    a["claims"] = [c]
    c_row = copy.deepcopy(row)
    c_row["strand"] = "C"
    c_row["admission_status"] = "keep"
    c_row["claims"] = [copy.deepcopy(c)]
    active = {"strand_a": [a], "frontier_evidence": [], "strand_b": [], "strand_c": [c_row], "historical_context": []}
    nodes, _ = flatten_claims(active, VOCAB)
    by_collection = {n["_collection"]: n for n in nodes}
    assert by_collection["strand_a"]["_primary"] is True
    assert by_collection["strand_c"]["_primary"] is False
    assert by_collection["strand_c"]["_context_weight"] == pytest.approx(0.3)


def test_adapted_claim_candidate_is_publication_locked():
    raw = {
        "level": 5,
        "grammar_id": "dependency_pathway",
        "product": "risk",
        "capability_object": "compute.public_procurement",
        "dependency_object": "datacentre.energy_supply",
        "endpoint_objects": ["compute.public_procurement", "datacentre.permitting"],
        "roles": {
            "commitment": {"claim_id": "c:a:1", "record_key": "id:a", "object": "compute.public_procurement", "status_date": "2026-07-30", "merit": 99, "source": "A", "title": "A", "strength": .792},
            "coupling": {"claim_id": "c:b:1", "record_key": "id:b", "object": "compute.private_investment", "status_date": "2026-09-09", "merit": 54, "source": "B", "title": "B", "strength": .432},
            "propagation": {"claim_id": "c:c:1", "record_key": "id:c", "object": "datacentre.energy_supply", "status_date": "2026-08-19", "merit": 54, "source": "C", "title": "C", "strength": .432},
            "exposure": {"claim_id": "c:d:1", "record_key": "id:d", "object": "compute.capacity", "status_date": "2026-08-11", "merit": 100, "source": "D", "title": "D", "strength": .8},
        },
        "missing_roles": [],
        "score": 89,
        "score_gate_passes": True,
        "wow_preliminary": 5,
        "distance": "distant",
        "distance_lift": 0.0,
        "distance_bonus": 1.2,
    }
    cand = live.adapt_candidate(raw, [])
    assert cand["status"] == "qualified"
    assert cand["reader_eligible"] is False
    assert cand["denial_tested"] is False
    assert cand["publication_gate_passes"] is False
    assert cand["falsifier_queries"]
    assert cand["id"].startswith("claim:dependency_pathway:")


def test_live_refresh_uses_claim_candidates_and_carries_only_existing_publications(monkeypatch):
    raw_candidate = {
        "level": 5,
        "grammar_id": "conflicting_criteria",
        "product": "risk",
        "endpoint_objects": ["quantum.testing_infrastructure", "export_control.competence"],
        "roles": {
            "criterion_a": {"claim_id": "c:a:1", "record_key": "id:a", "object": "quantum.testing_infrastructure", "status_date": "2026-08-13", "merit": 99, "source": "A", "title": "A", "strength": .792},
            "criterion_b": {"claim_id": "c:b:1", "record_key": "id:b", "object": "export_control.competence", "status_date": "2026-06-15", "merit": 68, "source": "B", "title": "B", "strength": .68},
            "arbitration_gap": {"claim_id": "c:c:1", "record_key": "id:c", "object": "export_control.competence", "status_date": "2026-07-06", "merit": 82, "source": "C", "title": "C", "strength": .656},
            "divergence": {"claim_id": "c:d:1", "record_key": "id:d", "object": "research_security.screening", "status_date": "2026-06-08", "merit": 82, "source": "D", "title": "D", "strength": .656},
        },
        "missing_roles": [],
        "score": 89,
        "score_gate_passes": True,
        "wow_preliminary": 5,
        "distance": "distant",
        "distance_lift": 0.0,
        "distance_bonus": 1.2,
    }
    fake = {
        "nodes": [],
        "groups": {
            "level3_sequence_gap": [], "level3_era_conjunction": [], "level4_opposing_movements": [],
            "level5_dependency_pathway": [], "level4_5_conflicting_criteria": [raw_candidate],
            "level5_latent_channel": [], "level5_anchor_demand": [], "level5_split_recurrence": [],
        },
        "authority_gate": {"ready": True},
        "claim_diagnostics": {"claims_loaded": 899, "generated": 3},
        "claim_expressiveness": {"ready_for_detector_switch": True},
        "distance_table": {"N": 500, "pairs": {}},
    }
    monkeypatch.setattr(live, "detect_claim_reasoning", lambda *a, **k: fake)
    old = {
        "publications": {"risk": ["legacy:risk"], "shock": [], "opportunity": [], "continuity": [], "trend": []},
        "candidates": [
            {"id": "legacy:risk", "grammar_id": "legacy", "product": "risk", "status": "qualified", "score": 95, "reader_eligible": True, "denial_tested": True, "falsifier_queries": ["x"]},
            {"id": "legacy:hidden", "grammar_id": "legacy", "product": "risk", "status": "watch", "score": 50},
        ],
    }
    state = live.refresh_claim_high_order({}, old, "2026-09-18T00:00:00Z")
    assert state is not None
    assert state["detector_backend"] == "claim_native"
    ids = {c["id"] for c in state["candidates"]}
    assert "legacy:risk" in ids
    assert "legacy:hidden" not in ids
    assert any(x.startswith("claim:conflicting_criteria:") for x in ids)
    assert state["publications"]["risk"] == ["legacy:risk"]
    claim_candidate = next(c for c in state["candidates"] if c.get("claim_native"))
    assert claim_candidate["reader_eligible"] is False


def test_shock_adapter_freezes_reader_dynamic_shocks(monkeypatch):
    fake = {
        "nodes": [],
        "groups": {"level5_dependency_pathway": [{
            "level": 5, "grammar_id": "dependency_pathway", "product": "shock",
            "capability_object": "compute.capacity", "dependency_object": "export_control.regulation",
            "endpoint_objects": ["compute.capacity", "export_control.regulation"],
            "roles": {}, "missing_roles": [], "score": 60, "score_gate_passes": False,
            "wow_preliminary": 5,
        }]},
        "authority_gate": {"ready": True},
        "claim_diagnostics": {"claims_loaded": 899},
    }
    monkeypatch.setattr(live, "detect_claim_reasoning", lambda *a, **k: fake)
    previous = {"dynamic_shocks": [{"id": "old", "title": "Old reader shock"}]}
    state = live.refresh_claim_shocks({}, previous, "2026-09-18T00:00:00Z")
    assert state is not None
    assert state["detector_backend"] == "claim_native"
    assert state["dynamic_shocks"] == previous["dynamic_shocks"]
    assert state["claim_candidate_count"] == 1
    assert state["claim_candidates"][0]["reader_eligible"] is False


def test_claim_feedback_prefers_falsification_and_missing_links():
    state = {"candidates": [{
        "claim_native": True, "status": "watch", "score": 75,
        "support_queries": ["missing bridge evidence"],
        "falsifier_queries": ["exemption evidence", "secured alternative"],
    }]}
    qs = live.claim_feedback_queries(state, 3)
    assert qs == ["missing bridge evidence", "exemption evidence", "secured alternative"]


def test_high_order_wrapper_does_not_call_legacy_detector_after_claim_switch(monkeypatch):
    from scripts import high_order_inference as hoi
    sentinel = {"detector_backend": "claim_native", "candidates": [], "publications": {}}
    monkeypatch.setattr(live, "refresh_claim_high_order", lambda *a, **k: sentinel)
    monkeypatch.setattr(hoi, "_refresh_high_order_inference_legacy", lambda *a, **k: (_ for _ in ()).throw(AssertionError("legacy detector called")))
    assert hoi.refresh_high_order_inference({}, {}, "2026-09-18T00:00:00Z") is sentinel


def test_shock_wrapper_does_not_call_legacy_detector_after_claim_switch(monkeypatch):
    from scripts import shock_inference as si
    sentinel = {"detector_backend": "claim_native", "dynamic_shocks": [], "claim_candidates": []}
    monkeypatch.setattr(live, "refresh_claim_shocks", lambda *a, **k: sentinel)
    monkeypatch.setattr(si, "_refresh_shock_inference_legacy", lambda *a, **k: (_ for _ in ()).throw(AssertionError("legacy shock detector called")))
    assert si.refresh_shock_inference({}, {}, "2026-09-18T00:00:00Z") is sentinel


def test_high_order_post_cutover_failure_holds_claim_state_without_legacy(monkeypatch):
    from scripts import high_order_inference as hoi
    previous = {
        "detector_backend": "claim_native",
        "candidates": [{"id": "claim:x", "claim_native": True, "status": "watch", "score": 70}],
        "publications": {"risk": [], "shock": [], "opportunity": [], "continuity": [], "trend": []},
        "new_count": 2,
        "updated_count": 3,
    }
    monkeypatch.setattr(live, "refresh_claim_high_order", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(hoi, "_refresh_high_order_inference_legacy", lambda *a, **k: (_ for _ in ()).throw(AssertionError("legacy detector called after cutover")))
    state = hoi.refresh_high_order_inference({}, previous, "2026-09-18T00:00:00Z")
    assert state["detector_backend"] == "claim_native_hold"
    assert state["switch_hold"] is True
    assert state["claim_switch_error"] == "RuntimeError"
    assert state["new_count"] == 0
    assert state["updated_count"] == 0
    assert state["candidates"] == previous["candidates"]


def test_shock_post_cutover_failure_holds_claim_state_without_legacy(monkeypatch):
    from scripts import shock_inference as si
    previous = {
        "detector_backend": "claim_native",
        "dynamic_shocks": [{"id": "reader:old"}],
        "claim_candidates": [{"id": "claim:shock:x", "claim_native": True}],
        "new_count": 1,
        "updated_count": 1,
    }
    monkeypatch.setattr(live, "refresh_claim_shocks", lambda *a, **k: None)
    monkeypatch.setattr(si, "_refresh_shock_inference_legacy", lambda *a, **k: (_ for _ in ()).throw(AssertionError("legacy shock detector called after cutover")))
    state = si.refresh_shock_inference({}, previous, "2026-09-18T00:00:00Z")
    assert state["detector_backend"] == "claim_native_hold"
    assert state["switch_hold"] is True
    assert state["claim_switch_error"] == "claim_authority_gate_not_ready"
    assert state["new_count"] == 0
    assert state["updated_count"] == 0
    assert state["dynamic_shocks"] == previous["dynamic_shocks"]


def test_claim_support_uses_downstream_retrace_url_identity():
    raw = {
        "level": 5,
        "grammar_id": "conflicting_criteria",
        "product": "risk",
        "endpoint_objects": ["quantum.testing_infrastructure", "export_control.competence"],
        "roles": {
            "criterion_a": {
                "claim_id": "c:q:1",
                "record_key": "link:https://example.test/Quantum-Thing/",
                "object": "quantum.testing_infrastructure",
                "status_date": "2026-08-13",
                "merit": 99,
                "source": "EuroHPC",
                "title": "Quantum thing",
                "strength": .792,
            }
        },
        "missing_roles": ["criterion_b"],
        "score": 0,
        "score_gate_passes": False,
        "wow_preliminary": 5,
        "distance": "distant",
        "distance_lift": 0.0,
        "distance_bonus": 1.2,
    }
    nodes = [{
        "claim_id": "c:q:1",
        "record_key": "link:https://example.test/Quantum-Thing/",
        "_link": "https://example.test/Quantum-Thing/",
        "_collection": "strand_a",
        "_title": "Quantum thing",
        "_source": "EuroHPC",
        "status_date": "2026-08-13",
    }]
    cand = live.adapt_candidate(raw, nodes)
    assert cand["support"][0]["identity"] == "url:https://example.test/quantum-thing"


def test_claim_candidate_json_is_strict_when_same_cluster_distance_is_unbounded():
    import json
    import math

    raw = {
        "level": 5,
        "grammar_id": "conflicting_criteria",
        "product": "risk",
        "endpoint_objects": ["research.openness", "research.open_access"],
        "roles": {},
        "missing_roles": ["criterion_a"],
        "score": 0,
        "score_gate_passes": False,
        "distance": "familiar",
        "distance_lift": math.inf,
        "distance_bonus": 1.0,
    }
    cand = live.adapt_candidate(raw, [])
    assert cand["distance_lift"] is None
    json.dumps(cand, allow_nan=False)


def test_same_cluster_distance_uses_json_null_not_infinity():
    from scripts.claim_reasoning_shadow import distance_for, distance_excluding_records

    assert distance_for({"pairs": []}, "quantum", "quantum") == ("familiar", 1.0, None)
    assert distance_excluding_records([], "quantum", "quantum", set()) == ("familiar", 1.0, None)
