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


def shelf_candidate(cid, *, product="risk", wow=3, score=80, sources=3, records=3, mechanism=None):
    return {
        "id": cid, "claim_native": True, "product": product, "status": "qualified",
        "denial_tested": False, "oddity_passes": True, "wow": wow, "score": score,
        "primary_sources": sources, "primary_records": records, "primary_role_coverage": 1.0,
        "role_strength_floor_passes": True,
        "endpoint_objects": [cid.replace(":", "."), "european.capability"],
        "support": [{"mechanism": mechanism or cid, "quality": 90, "analytical_weight": 1.0, "source": f"S{n}"} for n in range(max(1, sources))],
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


def test_stage7_unexecuted_falsifier_lowers_maturity_but_does_not_ban_future_hypothesis(monkeypatch):
    cand = quantum_candidate()
    nodes = quantum_nodes()
    monkeypatch.setattr(live, "detect_claim_reasoning", lambda *a, **k: fake_detection(cand, nodes))
    query = "quantum.testing_infrastructure common rule export_control.competence"
    raw = {"scan_results": {"finding_context_queries_this_scan": [query], "finding_context_queries_executed": 0}}
    state = live.refresh_claim_high_order(raw, {}, "2026-09-18T00:00:00Z", root=ROOT)
    c = state["candidates"][0]
    assert c["denial_tested"] is False
    assert c["presentation_ready"] is True
    assert c["id"] in state["publications"]["risk"]
    assert c["stock_tier"] == "page"

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
    # C-08: trend pairs are verified by their own two-sided evidence discipline, not
    # by a Level-5 candidate-specific falsifier.
    raw = {"scan_results": {"finding_context_queries_this_scan": [], "finding_context_queries_executed": 0}}
    state = live.refresh_claim_high_order(raw, {}, "2026-09-18T00:00:00Z", root=ROOT)
    assert len(state["publications"]["trend"]) == 1
    c = next(x for x in state["candidates"] if x["grammar_id"] == "opposing_movements")
    assert c["denial_tested"] is False
    assert c["falsifier_queries"] == []
    assert c["verification_mode"] == "trend_evidence_floor"
    assert c["publication_gate_passes"] is True
    b = c["trend_balance"]
    assert b["left_records"] == 3 and b["right_records"] == 3
    assert b["left_sources"] >= 2 and b["right_sources"] >= 2
    assert 15 <= b["raw_left_pull"] <= 85
    assert 15 <= b["left_pull"] <= 85
    assert isinstance(b["left_range"], list) and len(b["left_range"]) == 2


def test_stage7_three_slots_per_wow_and_surplus_goes_to_reserve():
    # Own wow bucket keeps its 3 slots; surplus may fill otherwise-empty slots of
    # other wow levels (full 15-slot page), and anything beyond goes to reserve.
    xs = [shelf_candidate(f"claim:r:{i}", wow=3, score=90-i) for i in range(20)]
    for i, x in enumerate(xs):
        x["object"] = f"risk.topic_{i}"
    pubs, meta = live._select_stage7(copy.deepcopy(xs), {"publications": {}, "candidates": []})
    assert set(pubs["risk"][:15]) >= {"claim:r:0", "claim:r:1", "claim:r:2"}
    assert len(pubs["risk"]) == 15
    assert meta["risk"]["slots_per_wow"] == 3
    assert meta["risk"]["page_capacity"] == 15
    assert meta["risk"]["borrowed_slots"] == 12
    assert meta["risk"]["reserve"] >= 5

def test_stage7_page_cycles_wow_5_to_1_in_three_rounds():
    xs = []
    for wow in (5,4,3,2,1):
        for i in range(3):
            xs.append(shelf_candidate(f"claim:w{wow}:{i}", wow=wow, score=90-i))
    pubs, meta = live._select_stage7(copy.deepcopy(xs), {"publications": {}, "candidates": []})
    expected = []
    for i in range(3):
        for wow in (5,4,3,2,1):
            expected.append(f"claim:w{wow}:{i}")
    assert pubs["risk"] == expected
    assert meta["risk"]["shown"] == 15
    assert meta["risk"]["shown_by_wow"] == {"5":3,"4":3,"3":3,"2":3,"1":3}
    assert meta["risk"]["hard_cap"] is True

def test_stage7_same_wow_never_steals_another_wow_bucket_slots():
    # A wow level with its own findings is never displaced by another level;
    # borrowing only fills slots that would otherwise stay empty.
    xs = [shelf_candidate(f"claim:o:{i}", product="opportunity", wow=2, score=90-i) for i in range(6)]
    xs += [shelf_candidate(f"claim:o5:{i}", product="opportunity", wow=5, score=60-i) for i in range(3)]
    for i, x in enumerate(xs):
        x["object"] = f"opp.topic_{i}"
    pubs, meta = live._select_stage7(copy.deepcopy(xs), {"publications": {}, "candidates": []})
    assert {f"claim:o5:{i}" for i in range(3)} <= set(pubs["opportunity"])
    assert meta["opportunity"]["shown_by_actual_wow"]["5"] == 3

def test_stage7_trends_use_same_three_slots_per_wow_contract():
    xs = []
    for i in range(12):
        xs.append({
            **shelf_candidate(f"claim:t:{i}", product="trend", wow=1, score=95-i, sources=4, records=6),
            "grammar_id": "opposing_movements", "object": f"trend.object.{i}", "trend_key": f"trend:{i}",
            "trend_evidence_floor_passes": i < 5,
            "trend_balance": {"left_records": 2, "right_records": 2, "left_sources": 2, "right_sources": 2},
        })
    pubs, meta = live._select_stage7(copy.deepcopy(xs), {"publications": {}, "candidates": []})
    assert {"claim:t:0", "claim:t:1", "claim:t:2"} <= set(pubs["trend"])
    assert len(pubs["trend"]) == 12  # empty wow levels filled; nothing left over
    assert meta["trend"]["shown_by_actual_wow"]["1"] == 12

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


def test_stage7_feedback_services_qualified_level5_before_watch_candidates():
    state = {"candidates": [
        {
            "id": "claim:risk:ready", "claim_native": True, "product": "risk",
            "status": "qualified", "verification_mode": "executed_candidate_falsifier",
            "denial_tested": False, "wow": 5, "score": 90,
            "falsifier_queries": ["ready risk falsifier"], "support_queries": [],
        },
        {
            "id": "claim:opp:watch", "claim_native": True, "product": "opportunity",
            "status": "watch", "wow": 5, "score": 99,
            "support_queries": ["watch missing bridge"],
            "falsifier_queries": ["watch challenge"],
        },
    ]}
    assert live.claim_feedback_queries(state, 3) == [
        "watch missing bridge", "watch challenge", "ready risk falsifier"
    ]



def test_stage7_level2_corroborated_risk_is_part_of_claim_native_shelf_without_level5_falsifier():
    nodes = [
        node("c:r1", "supply.chain_access", "Alpha", direction="becomes_conditional", mechanism="conditions", kind="action", status="adopted"),
        node("c:r2", "supply.chain_access", "Beta", direction="becomes_conditional", mechanism="conditions", kind="action", status="in_force"),
    ]
    raw = {
        "level": 2, "grammar_id": "corroborated_claim", "product": "risk",
        "object": "supply.chain_access", "mechanism": "conditions",
        "direction": "becomes_conditional", "status": "in_force",
        "product_basis": "corroborated_constraint",
        "claim_ids": ["c:r1", "c:r2"], "score": 84,
        "score_gate_passes": True, "wow_preliminary": 3,
    }
    cand = live.adapt_candidate(raw, nodes, vocab={}, evaluated_on=__import__('datetime').date(2026, 9, 18))
    assert cand["object"] == "supply.chain_access"
    assert cand["mechanism"] == "conditions"
    assert cand["direction"] == "becomes_conditional"
    assert cand["claim_status"] == "in_force"
    assert cand["product_basis"] == "corroborated_constraint"
    assert cand["verification_mode"] == "corroborated_claim_floor"
    assert cand["verification_gate_passes"] is True
    assert cand["falsifier_queries"] == []
    pubs, meta = live._select_stage7([cand], {"publications": {}, "candidates": []})
    assert pubs["risk"] == [cand["id"]]
    assert meta["risk"]["shown"] == 1


def test_stage7_level2_live_instrument_can_supply_opportunity_baseline():
    nodes = [
        node("c:o1", "horizon.association", "Alpha", direction="expands", mechanism="associates", kind="action", status="in_force"),
        node("c:o2", "horizon.association", "Beta", direction="expands", mechanism="associates", kind="action", status="in_negotiation"),
    ]
    raw = {
        "level": 2, "grammar_id": "corroborated_claim", "product": "opportunity",
        "object": "horizon.association", "mechanism": "associates",
        "direction": "expands", "status": "in_force",
        "product_basis": "live_or_operating_instrument",
        "claim_ids": ["c:o1", "c:o2"], "score": 76,
        "score_gate_passes": True, "wow_preliminary": 2,
    }
    cand = live.adapt_candidate(raw, nodes, vocab={}, evaluated_on=__import__('datetime').date(2026, 9, 18))
    pubs, meta = live._select_stage7([cand], {"publications": {}, "candidates": []})
    assert pubs["opportunity"] == [cand["id"]]
    assert meta["opportunity"]["grounded_publishable"] == 1
    assert cand["stock_tier"] == "page"

def test_stage7_new_wow5_has_its_own_slot_and_does_not_displace_wow3():
    incumbents = [shelf_candidate(f"claim:old:{i}", wow=3, score=95-i) for i in range(5)]
    for i, x in enumerate(incumbents):
        x["object"] = f"risk.topic_{i}"
    surprise = shelf_candidate("claim:new:wow5", wow=5, score=82)
    previous = {"publications": {"risk": [c["id"] for c in incumbents[:3]]}, "candidates": [dict(c) for c in incumbents]}
    pubs, meta = live._select_stage7(copy.deepcopy(incumbents + [surprise]), previous)
    assert pubs["risk"][0] == "claim:new:wow5"
    assert all(f"claim:old:{i}" in pubs["risk"] for i in range(3))
    assert meta["risk"]["shown_by_actual_wow"]["5"] == 1

def test_stage7_hysteresis_operates_inside_each_wow_bucket():
    # Fill every wow level so no empty slot can be borrowed; only the swap rule
    # can bring the challenger onto the page.
    filler = [shelf_candidate(f"claim:w{w}:{i}", wow=w, score=90-i) for w in (5, 4, 2, 1) for i in range(3)]
    incumbents = [shelf_candidate("claim:old:0", wow=3, score=90), shelf_candidate("claim:old:1", wow=3, score=89), shelf_candidate("claim:old:2", wow=3, score=88)]
    for i, x in enumerate(filler + incumbents):
        x["object"] = f"risk.topic_{i}"
    shown = [c["id"] for c in filler + incumbents]
    previous = {"publications": {"risk": shown}, "candidates": [dict(c) for c in filler + incumbents]}
    def run(score):
        ch = shelf_candidate("claim:new", wow=3, score=score)
        ch["object"] = "risk.topic_new"
        return live._select_stage7(copy.deepcopy(filler + incumbents + [ch]), previous)[0]["risk"]
    assert "claim:new" not in run(89)   # marginal gain: incumbents keep their slots
    assert "claim:new" in run(100)      # clearly stronger evidence swaps in


