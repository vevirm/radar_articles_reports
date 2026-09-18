from __future__ import annotations

import copy
from pathlib import Path

from scripts import claim_reasoning_live as live

ROOT = Path(__file__).resolve().parents[1]


def node(cid, obj, source, *, direction="expands", mechanism="assesses", kind="diagnosis", status="delivered", date="2026-08-01", secondary=None, new=False):
    return {
        "claim_id": cid,
        "record_key": f"link:https://example.test/{cid.replace(':','-')}",
        "_record_id": f"r:{cid}",
        "_link": f"https://example.test/{cid.replace(':','-')}",
        "_title": f"Title {cid}",
        "_source": source,
        "_collection": "strand_a",
        "_primary": True,
        "_new_this_scan": new,
        "era": "current",
        "object": obj,
        "secondary_objects": list(secondary or []),
        "mechanism": mechanism,
        "direction": direction,
        "kind": kind,
        "status": status,
        "status_date": date,
        "merit": 90,
        "scope": {"level": "eu", "countries": []},
        "actor": {"name": source, "class": "eu_body"},
        "attributes": {},
    }


def quantum_candidate(counter=False):
    c = {
        "level": 5,
        "grammar_id": "conflicting_criteria",
        "product": "risk",
        "endpoint_objects": ["quantum.testing_infrastructure", "export_control.competence"],
        "roles": {
            "criterion_a": {"claim_id": "c:a", "record_key": "id:a", "object": "quantum.testing_infrastructure", "status_date": "2026-08-13", "merit": 99, "source": "EuroHPC", "title": "Open test bench", "strength": .792},
            "criterion_b": {"claim_id": "c:b", "record_key": "id:b", "object": "export_control.competence", "status_date": "2026-06-15", "merit": 90, "source": "Trade", "title": "Controls", "strength": .75},
            "arbitration_gap": {"claim_id": "c:c", "record_key": "id:c", "object": "export_control.competence", "status_date": "2026-07-06", "merit": 82, "source": "Policy", "title": "National competence", "strength": .656},
            "divergence": {"claim_id": "c:d", "record_key": "id:d", "object": "research_security.screening", "status_date": "2026-06-08", "merit": 82, "source": "Research", "title": "Different balances", "strength": .722},
        },
        "missing_roles": [],
        "score": 89,
        "score_gate_passes": True,
        "wow_preliminary": 5,
        "distance": "distant",
        "distance_lift": 0.0,
        "distance_bonus": 1.2,
    }
    if counter:
        c["counter_claim_ids"] = ["c:k"]
    return c


def quantum_nodes(counter_new=False):
    rows = [
        node("c:a", "quantum.testing_infrastructure", "EuroHPC", mechanism="procures", kind="action", status="call_open"),
        node("c:b", "export_control.competence", "Trade", mechanism="restricts", kind="diagnosis", status="in_force"),
        node("c:c", "export_control.competence", "Policy", mechanism="assesses", kind="diagnosis"),
        node("c:d", "research_security.screening", "Research", mechanism="assesses", kind="diagnosis"),
    ]
    if counter_new:
        rows.append(node("c:k", "quantum.testing_infrastructure", "EuroHPC", mechanism="harmonises", kind="action", status="adopted", new=True))
    return rows


def fake_detection(candidate, nodes):
    return {
        "nodes": nodes,
        "groups": {
            "level3_sequence_gap": [], "level3_era_conjunction": [], "level4_opposing_movements": [],
            "level5_dependency_pathway": [], "level4_5_conflicting_criteria": [candidate],
            "level5_latent_channel": [], "level5_anchor_demand": [], "level5_split_recurrence": [],
        },
        "authority_gate": {"ready": True},
        "claim_diagnostics": {"claims_loaded": len(nodes)},
        "claim_expressiveness": {"ready_for_detector_switch": True},
        "distance_table": {"N": len(nodes), "pairs": {}},
    }


def test_stage7_executed_falsifier_unlocks_claim_native_risk(monkeypatch):
    cand = quantum_candidate()
    nodes = quantum_nodes()
    monkeypatch.setattr(live, "detect_claim_reasoning", lambda *a, **k: fake_detection(cand, nodes))
    query = "quantum.testing_infrastructure common rule export_control.competence"
    raw = {"scan_results": {"finding_context_queries_this_scan": [query], "finding_context_queries_executed": 1}}
    state = live.refresh_claim_high_order(raw, {}, "2026-09-18T00:00:00Z", root=ROOT)
    assert state["publication_compatibility_lock"] is False
    assert state["selection_stage"] == 7
    assert len(state["publications"]["risk"]) == 1
    c = state["candidates"][0]
    assert c["denial_tested"] is True
    assert c["falsifier_results"][0]["result"] == "miss"
    assert c["wow"] == 5
    assert c["oddity_passes"] is True
    assert c["publication_gate_passes"] is True


def test_stage7_planned_but_unexecuted_falsifier_does_not_unlock(monkeypatch):
    cand = quantum_candidate()
    nodes = quantum_nodes()
    monkeypatch.setattr(live, "detect_claim_reasoning", lambda *a, **k: fake_detection(cand, nodes))
    query = "quantum.testing_infrastructure common rule export_control.competence"
    raw = {"scan_results": {"finding_context_queries_this_scan": [query], "finding_context_queries_executed": 0}}
    state = live.refresh_claim_high_order(raw, {}, "2026-09-18T00:00:00Z", root=ROOT)
    assert state["publications"]["risk"] == []
    c = state["candidates"][0]
    assert c["denial_tested"] is False
    assert c["publication_gate_passes"] is False


def test_stage7_falsifier_hit_kills_candidate_same_scan(monkeypatch):
    cand = quantum_candidate(counter=True)
    nodes = quantum_nodes(counter_new=True)
    monkeypatch.setattr(live, "detect_claim_reasoning", lambda *a, **k: fake_detection(cand, nodes))
    query = "quantum.testing_infrastructure common rule export_control.competence"
    raw = {"scan_results": {"finding_context_queries_this_scan": [query], "finding_context_queries_executed": 1}}
    state = live.refresh_claim_high_order(raw, {}, "2026-09-18T00:00:00Z", root=ROOT)
    c = next(x for x in state["candidates"] if x["grammar_id"] == "conflicting_criteria")
    assert c["status"] == "killed"
    assert c["movement"] == "killed"
    assert c["falsifier_results"][0]["result"] == "hit"
    assert state["publications"]["risk"] == []


def test_stage7_claim_native_trend_uses_band_and_side_floor(monkeypatch):
    obj = "compute.capacity"
    nodes = [
        node("c:l1", obj, "S1", mechanism="builds", kind="action", status="operating", date="2026-09-01"),
        node("c:l2", obj, "S2", mechanism="funds", kind="action", status="adopted", date="2026-08-20"),
        node("c:l3", obj, "S3", mechanism="adds_capacity", kind="effect", status="delivered", date="2026-08-10"),
        node("c:r1", obj, "R1", direction="contracts", mechanism="restricts", kind="action", status="in_force", date="2026-09-02"),
        node("c:r2", obj, "R2", direction="contracts", mechanism="assesses", kind="effect", status="delivered", date="2026-08-22"),
        node("c:r3", obj, "R3", direction="contracts", mechanism="conditions", kind="action", status="proposed", date="2026-08-12"),
    ]
    raw_c = {"level": 4, "grammar_id": "opposing_movements", "object": obj}
    fake = fake_detection(quantum_candidate(), nodes)
    fake["groups"]["level4_5_conflicting_criteria"] = []
    fake["groups"]["level4_opposing_movements"] = [raw_c]
    monkeypatch.setattr(live, "detect_claim_reasoning", lambda *a, **k: fake)
    query = "compute.capacity substitution resilience alternative capacity"
    raw = {"scan_results": {"finding_context_queries_this_scan": [query], "finding_context_queries_executed": 1}}
    state = live.refresh_claim_high_order(raw, {}, "2026-09-18T00:00:00Z", root=ROOT)
    assert len(state["publications"]["trend"]) == 1
    c = next(x for x in state["candidates"] if x["grammar_id"] == "opposing_movements")
    b = c["trend_balance"]
    assert b["left_records"] == 3 and b["right_records"] == 3
    assert b["left_sources"] >= 2 and b["right_sources"] >= 2
    assert 15 <= b["raw_left_pull"] <= 85
    assert 15 <= b["left_pull"] <= 85
    assert isinstance(b["left_range"], list) and len(b["left_range"]) == 2


def test_stage7_soft_target_raises_wow_floor_without_hard_cap():
    xs = []
    for i in range(6):
        xs.append({
            "id": f"claim:r:{i}", "claim_native": True, "product": "risk", "status": "qualified",
            "denial_tested": True, "oddity_passes": True, "wow": 3, "score": 90-i,
            "endpoint_objects": [f"o{i}", f"x{i}"], "support": [{"mechanism": f"m{i}"}],
        })
    pubs, meta = live._select_stage7(copy.deepcopy(xs), {"publications": {}, "candidates": []})
    assert pubs["risk"] == []
    assert meta["risk"]["wow_floor"] == 4
    assert meta["risk"]["soft_target"] == [2, 5]


def test_stage7_zero_strength_primary_claim_is_stock_not_publication(monkeypatch):
    # R-09 primary/context authority and R-21 role strength are separate.
    # A primary claim with a lapsed status remains authoritative evidence in
    # stock, but its zero role strength must not satisfy the qualification gate.
    cand = quantum_candidate()
    cand["roles"]["criterion_a"]["strength"] = 0.0
    cand["score_gate_passes"] = False
    nodes = quantum_nodes()
    nodes[0]["status"] = "lapsed"
    monkeypatch.setattr(live, "detect_claim_reasoning", lambda *a, **k: fake_detection(cand, nodes))
    query = "quantum.testing_infrastructure common rule export_control.competence"
    raw = {"scan_results": {"finding_context_queries_this_scan": [query], "finding_context_queries_executed": 1}}
    state = live.refresh_claim_high_order(raw, {}, "2026-09-18T00:00:00Z", root=ROOT)
    c = next(x for x in state["candidates"] if x["grammar_id"] == "conflicting_criteria")
    support = next(x for x in c["support"] if x["claim_id"] == "c:a")
    assert support["claim_primary"] is True
    assert support["analytical_weight"] == 0.0
    assert support["claim_status"] == "lapsed"
    assert c["status"] == "watch"
    assert c["publication_gate_passes"] is False
    assert state["publications"]["risk"] == []
