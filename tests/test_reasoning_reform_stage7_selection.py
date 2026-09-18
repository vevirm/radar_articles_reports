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


def test_stage7_soft_target_curates_crowded_same_wow_shelf_into_reserve():
    xs = []
    for i in range(6):
        xs.append({
            "id": f"claim:r:{i}", "claim_native": True, "product": "risk", "status": "qualified",
            "denial_tested": True, "oddity_passes": True, "wow": 3, "score": 90-i,
            "endpoint_objects": [f"o{i}", f"x{i}"], "support": [{"mechanism": f"m{i}"}],
        })
    pubs, meta = live._select_stage7(copy.deepcopy(xs), {"publications": {}, "candidates": []})
    # R-70/R-72: all six remain in the stock, but an overcrowded wow-3 shelf
    # raises the active floor.  Because no wow-4 item exists, retain only enough
    # strongest wow-3 findings to satisfy the soft minimum; the surplus is reserve.
    assert pubs["risk"] == ["claim:r:0", "claim:r:1"]
    assert meta["risk"]["wow_floor"] == 4
    assert meta["risk"]["soft_target"] == [2, 5]
    assert meta["risk"]["hard_cap"] is False
    assert meta["risk"]["reserve"] == 4


def test_stage7_soft_target_raises_wow_floor_without_numeric_cap():
    xs = []
    # six wow-3 findings make the shelf crowded; three wow-4 findings mean the
    # floor can safely rise while still clearing the soft minimum of two.
    for i in range(6):
        xs.append({
            "id": f"claim:r3:{i}", "claim_native": True, "product": "risk", "status": "qualified",
            "denial_tested": True, "oddity_passes": True, "wow": 3, "score": 90-i,
            "endpoint_objects": [f"r3{i}", f"x3{i}"], "support": [{"mechanism": f"m3{i}"}],
        })
    for i in range(3):
        xs.append({
            "id": f"claim:r4:{i}", "claim_native": True, "product": "risk", "status": "qualified",
            "denial_tested": True, "oddity_passes": True, "wow": 4, "score": 80-i,
            "endpoint_objects": [f"r4{i}", f"x4{i}"], "support": [{"mechanism": f"m4{i}"}],
        })
    pubs, meta = live._select_stage7(copy.deepcopy(xs), {"publications": {}, "candidates": []})
    assert meta["risk"]["wow_floor"] == 4
    assert all(x.startswith("claim:r4:") for x in pubs["risk"][:3])
    # R-74 keeps one strongest wow-3 baseline representative beneath the upper shelf.
    assert pubs["risk"] == ["claim:r4:0", "claim:r4:1", "claim:r4:2", "claim:r3:0"]
    assert meta["risk"]["reserve"] == 5


def test_stage7_sparse_baseline_can_exceed_soft_upper_target_without_becoming_a_cap():
    xs = []
    for i in range(6):
        xs.append({
            "id": f"claim:o:{i}", "claim_native": True, "product": "opportunity", "status": "qualified",
            "denial_tested": True, "oddity_passes": True, "wow": 2, "score": 80-i,
            "endpoint_objects": [f"o{i}", f"y{i}"], "support": [{"mechanism": f"m{i}"}],
        })
    pubs, meta = live._select_stage7(copy.deepcopy(xs), {"publications": {}, "candidates": []})
    # There is no wow>=3 upper shelf at all, so R-72's shortage rule shows the
    # verified baseline that exists.  The normal 2-5 target is not a hard cap.
    assert pubs["opportunity"] == [f"claim:o:{i}" for i in range(6)]
    assert meta["opportunity"]["shown"] == 6
    assert meta["opportunity"]["reserve"] == 0


def test_stage7_crowded_trends_raise_evidence_floor_and_keep_surplus_in_reserve():
    xs = []
    for i in range(12):
        strong = i < 5
        xs.append({
            "id": f"claim:t:{i}", "claim_native": True, "product": "trend", "status": "qualified",
            "oddity_passes": True, "wow": 1, "score": 95-i,
            "trend_evidence_floor_passes": True,
            "trend_balance": {
                "left_records": 4 if strong else 3, "right_records": 4 if strong else 3,
                "left_sources": 3 if strong else 2, "right_sources": 3 if strong else 2,
            },
            "endpoint_objects": [f"t{i}"], "trend_key": f"trend:{i}", "support": [{"mechanism": f"moves{i}"}],
            "primary_sources": 6 if strong else 4, "primary_records": 8 if strong else 6,
        })
    pubs, meta = live._select_stage7(copy.deepcopy(xs), {"publications": {}, "candidates": []})
    assert pubs["trend"] == [f"claim:t:{i}" for i in range(5)]
    assert meta["trend"]["active_evidence_floor"] == "4_records_3_sources_each_side"
    assert meta["trend"]["reserve"] == 7
    assert meta["trend"]["hard_cap"] is False


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
        "ready risk falsifier", "watch missing bridge", "watch challenge"
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
    assert cand["verification_mode"] == "corroborated_claim_floor"
    assert cand["verification_gate_passes"] is True
    assert cand["wow"] == 2
    pubs, meta = live._select_stage7([cand], {"publications": {}, "candidates": []})
    assert pubs["opportunity"] == [cand["id"]]
    assert meta["opportunity"]["baseline_verified"] == 1


def test_stage7_new_wow5_is_shown_even_when_soft_target_is_full():
    base = {
        "claim_native": True, "product": "risk", "status": "qualified",
        "denial_tested": True, "oddity_passes": True, "wow": 3,
        "verification_mode": "executed_candidate_falsifier",
    }
    incumbents = [
        dict(base, id=f"claim:old:{i}", score=95-i, endpoint_objects=[f"old{i}", "x"], support=[{"mechanism": f"m{i}"}])
        for i in range(5)
    ]
    surprise = dict(
        base, id="claim:new:wow5", wow=5, score=82,
        endpoint_objects=["new5", "x"], support=[{"mechanism": "new5"}],
    )
    previous = {
        "publications": {"risk": [c["id"] for c in incumbents]},
        "candidates": [dict(c) for c in incumbents],
    }
    pubs, meta = live._select_stage7(copy.deepcopy(incumbents + [surprise]), previous)
    assert "claim:new:wow5" in pubs["risk"]
    # The new wow-5 enters immediately; the crowded wow-3 band is reserve except
    # for one minimum-fill incumbent.  The target is still a threshold guide, not
    # a five-slot hard cap.
    assert len(pubs["risk"]) == 2
    assert meta["risk"]["soft_target"] == [2, 5]
    assert meta["risk"]["shown"] == 2
    assert meta["risk"]["reserve"] == 4

def test_stage7_hysteresis_keeps_equal_wow_incumbent_in_minimum_fill_until_six_point_challenge():
    base = {
        "claim_native": True, "product": "risk", "status": "qualified",
        "denial_tested": True, "oddity_passes": True, "wow": 3,
        "verification_mode": "executed_candidate_falsifier",
    }
    incumbents = [
        dict(base, id="claim:old:0", score=90, endpoint_objects=["old0", "x"], support=[{"mechanism": "m0"}]),
        dict(base, id="claim:old:1", score=89, endpoint_objects=["old1", "x"], support=[{"mechanism": "m1"}]),
    ]
    filler = [
        dict(base, id=f"claim:filler:{i}", score=80-i, endpoint_objects=[f"f{i}", "x"], support=[{"mechanism": f"f{i}"}])
        for i in range(4)
    ]
    challenger = dict(base, id="claim:new", score=94, endpoint_objects=["new", "x"], support=[{"mechanism": "mn"}])
    previous = {
        "publications": {"risk": [c["id"] for c in incumbents]},
        "candidates": [dict(c) for c in incumbents],
    }
    pubs, _ = live._select_stage7(copy.deepcopy(incumbents + filler + [challenger]), previous)
    assert "claim:new" not in pubs["risk"]  # weakest incumbent 89; +5 is not enough
    challenger["score"] = 95
    pubs, _ = live._select_stage7(copy.deepcopy(incumbents + filler + [challenger]), previous)
    assert "claim:new" in pubs["risk"]  # +6 displaces the weakest incumbent
