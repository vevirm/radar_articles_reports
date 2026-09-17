from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from scripts.claim_reasoning_shadow import (
    build_distance_table,
    corroborated_claims,
    dependency_pathways,
    distance_for,
    flatten_claims,
    level3_findings,
    opposing_movements,
)
from scripts.claims_schema import load_vocabulary

ROOT = Path(__file__).resolve().parents[1]
VOCAB = load_vocabulary(ROOT / "claims_vocabulary.json")


def claim(*, key: str, cid: str, obj: str, mech: str, direction: str, kind: str = "action", status: str = "operating", date: str = "2026-09-01", merit: int = 90, secondary=None, actor_class="eu_body", scope="eu", countries=None, attrs=None):
    return {
        "record_key": key, "claim_id": cid, "object": obj, "secondary_objects": secondary or [],
        "actor": {"name": "Actor " + cid[-1], "class": actor_class}, "mechanism": mech,
        "direction": direction, "status": status, "status_date": date,
        "scope": {"level": scope, "countries": countries or []}, "kind": kind, "merit": merit,
        "qualification": "", "text": "A substantive factual sentence for the fixture.",
        "confidence": "high", "origin": "backfill", "era": "current", "provisional": False,
        **({"attributes": attrs} if attrs is not None else {}),
    }


def row(c, source="Source", decision="keep"):
    return {"title": c[0]["claim_id"], "source": source, "admission_status": decision, "claims": c}


def test_flatten_claims_enforces_r09_primary_context_and_methods_isolation():
    a = claim(key="id:a", cid="c:a:1", obj="compute.capacity", mech="assesses", direction="contracts", kind="diagnosis")
    c_event = claim(key="id:c1", cid="c:c1:1", obj="compute.gigafactory", mech="builds", direction="expands", kind="action")
    c_interp = claim(key="id:c2", cid="c:c2:1", obj="compute.capacity", mech="assesses", direction="becomes_contested", kind="diagnosis")
    c_review = claim(key="id:c3", cid="c:c3:1", obj="chips.fab", mech="builds", direction="expands", kind="action")
    b = claim(key="id:b", cid="c:b:1", obj="methods.horizon_scanning", mech="assesses", direction="unchanged", kind="diagnosis", attrs={"world_reasoning": False})
    h = claim(key="historical:id:h", cid="c:h:1", obj="horizon.access", mech="conditions", direction="becomes_conditional", kind="diagnosis", date="2018-11-01")
    h["era"] = "historical"; h["record_key"] = "historical:id:h"
    active = {
        "strand_a": [row([a], "A")], "frontier_evidence": [],
        "strand_b": [row([b], "B")],
        "strand_c": [row([c_event], "C1", "keep"), row([c_interp], "C2", "keep"), row([c_review], "C3", "review")],
        "historical_context": [{"title":"H","source":"H","historical_admission_status":"keep","claims":[h]}],
    }
    nodes, diag = flatten_claims(active, VOCAB)
    by_id = {n["claim_id"]: n for n in nodes}
    assert by_id["c:a:1"]["_primary"] is True
    assert by_id["c:c1:1"]["_primary"] is True
    assert by_id["c:c2:1"]["_primary"] is False
    assert by_id["c:c3:1"]["_primary"] is False
    assert by_id["c:h:1"]["_primary"] is False
    assert "c:b:1" not in by_id
    assert diag["methods_or_world_disabled"] == 1


def _node(c, source="S", primary=True, collection="strand_a"):
    n=dict(c); n.update({"_primary":primary,"_collection":collection,"_record_id":c["record_key"],"_source":source,"_clusters":sorted(set().union(*(set([VOCAB['objects'][o]['cluster']]) | set(VOCAB['objects'][o].get('secondary_clusters',[])) for o in [c['object'],*c.get('secondary_objects',[])] if o in VOCAB['objects']))),"_title":c['claim_id']})
    return n


def test_distance_table_uses_record_cooccurrence_and_canonical_bonus():
    n1=_node(claim(key="id:1",cid="c:1:1",obj="compute.gigafactory",mech="builds",direction="expands",secondary=["datacentre.energy_supply"]))
    n2=_node(claim(key="id:2",cid="c:2:1",obj="compute.capacity",mech="assesses",direction="contracts",kind="diagnosis"))
    n3=_node(claim(key="id:3",cid="c:3:1",obj="datacentre.permitting",mech="regulates",direction="becomes_conditional"))
    table=build_distance_table([n1,n2,n3])
    d, bonus, lift=distance_for(table,"compute_ai","permitting_siting")
    assert bonus in {1.0,1.1,1.2}
    # This fixture has positive co-occurrence; the canonical distant multiplier is 1.20 when distant.
    if d == "distant": assert bonus == 1.20
    assert table["N"] == 3


def test_level2_requires_two_independent_sources():
    c1=claim(key="id:1",cid="c:1:1",obj="compute.capacity",mech="assesses",direction="contracts",kind="diagnosis")
    c2=claim(key="id:2",cid="c:2:1",obj="compute.capacity",mech="assesses",direction="contracts",kind="diagnosis")
    assert len(corroborated_claims([_node(c1,"S1"),_node(c2,"S2")])) == 1
    assert len(corroborated_claims([_node(c1,"S1"),_node(c2,"S1")])) == 0


def test_partial_date_cannot_create_stalled_proposal():
    p=claim(key="id:p",cid="c:p:1",obj="datacentre.permitting",mech="regulates",direction="becomes_conditional",status="proposed",date="2025-01-01")
    pm=claim(key="id:m",cid="c:m:1",obj="chips.fab",mech="builds",direction="expands",status="proposed",date="2025-01")
    pm["status_date_precision"]="month"
    out=level3_findings([_node(p,"S1"),_node(pm,"S2")],dt.date(2026,9,17))
    assert any(x["object"]=="datacentre.permitting" for x in out)
    assert not any(x["object"]=="chips.fab" for x in out)


def test_opposing_movements_requires_three_records_and_two_sources_each_side():
    nodes=[]
    for i,(direction,source) in enumerate([("expands","A"),("expands","B"),("expands","C"),("contracts","D"),("contracts","E"),("contracts","F")],1):
        c=claim(key=f"id:{i}",cid=f"c:{i}:1",obj="compute.capacity",mech="assesses",direction=direction,kind="effect",status="delivered",date="2026-08-01")
        nodes.append(_node(c,source))
    out=opposing_movements(nodes,dt.date(2026,9,17))
    assert len(out)==1
    assert out[0]["object"]=="compute.capacity"


def test_dependency_pathway_is_shadow_only_even_when_score_gate_passes_or_nearly_passes():
    commitment=claim(key="id:co",cid="c:co:1",obj="compute.gigafactory",mech="builds",direction="expands",kind="action",status="operating",merit=99,secondary=["compute.private_investment"])
    coupling=claim(key="id:cu",cid="c:cu:1",obj="compute.private_investment",mech="requires",direction="becomes_conditional",kind="action",status="operating",merit=95,secondary=["datacentre.energy_supply"])
    exposure=claim(key="id:ex",cid="c:ex:1",obj="datacentre.energy_supply",mech="restricts",direction="contracts",kind="diagnosis",status="operating",merit=95)
    propagation=claim(key="id:pr",cid="c:pr:1",obj="compute.capacity",mech="assesses",direction="contracts",kind="effect",status="operating",merit=95,secondary=["datacentre.energy_supply"])
    nodes=[_node(commitment,"S1"),_node(coupling,"S2"),_node(exposure,"S3"),_node(propagation,"S4")]
    table=build_distance_table(nodes)
    out=dependency_pathways(nodes,VOCAB,table)
    assert out
    assert all(x["publication_gate_passes"] is False for x in out)
    assert all("falsifier" in x["publication_gate_reason"].lower() for x in out)


def test_dependency_pathway_rejects_cluster_only_role_join_without_exact_object_path():
    # Both sides sit in strategically adjacent clusters, but R-31 permits expansion only
    # through exact object / secondary_object overlap. This must not form a pathway.
    commitment=claim(key="id:co2",cid="c:co2:1",obj="digital.sovereignty",mech="adopts",direction="expands",kind="action",status="announced",merit=99,secondary=["compute.capacity"])
    coupling=claim(key="id:cu2",cid="c:cu2:1",obj="goal.strategic_autonomy",mech="requires",direction="becomes_conditional",kind="diagnosis",status="delivered",merit=90,secondary=["finance.strategic_investment"])
    exposure=claim(key="id:ex2",cid="c:ex2:1",obj="finance.strategic_investment",mech="restricts",direction="contracts",kind="diagnosis",status="delivered",merit=90)
    propagation=claim(key="id:pr2",cid="c:pr2:1",obj="finance.strategic_investment",mech="assesses",direction="contracts",kind="effect",status="delivered",merit=90)
    nodes=[_node(commitment,"S1"),_node(coupling,"S2"),_node(exposure,"S3"),_node(propagation,"S4")]
    table=build_distance_table(nodes)
    assert dependency_pathways(nodes,VOCAB,table) == []


def test_dependency_pathway_uses_exact_object_frontier_and_reports_hop():
    commitment=claim(key="id:co3",cid="c:co3:1",obj="compute.gigafactory",mech="builds",direction="expands",kind="action",status="operating",merit=99,secondary=["compute.private_investment"])
    coupling=claim(key="id:cu3",cid="c:cu3:1",obj="compute.private_investment",mech="requires",direction="becomes_conditional",kind="action",status="operating",merit=95,secondary=["datacentre.energy_supply"])
    exposure=claim(key="id:ex3",cid="c:ex3:1",obj="datacentre.energy_supply",mech="restricts",direction="contracts",kind="diagnosis",status="operating",merit=95)
    propagation=claim(key="id:pr3",cid="c:pr3:1",obj="datacentre.energy_supply",mech="assesses",direction="contracts",kind="effect",status="operating",merit=95)
    nodes=[_node(commitment,"S1"),_node(coupling,"S2"),_node(exposure,"S3"),_node(propagation,"S4")]
    out=dependency_pathways(nodes,VOCAB,build_distance_table(nodes))
    assert out
    assert out[0]["frontier_mode"] == "exact_object_overlap"
    assert out[0]["coupling_hop"] == 1
    assert out[0]["dependency_object"] == "datacentre.energy_supply"


def test_conflicting_criteria_does_not_treat_delivered_generic_diagnosis_as_a_criterion():
    from scripts.claim_reasoning_shadow import conflicting_criteria
    a=claim(key="id:a4",cid="c:a4:1",obj="research.infrastructure",mech="assesses",direction="expands",kind="diagnosis",status="delivered",merit=99)
    b=claim(key="id:b4",cid="c:b4:1",obj="research.infrastructure",mech="assesses",direction="contracts",kind="diagnosis",status="delivered",merit=99)
    g=claim(key="id:g4",cid="c:g4:1",obj="research.infrastructure",mech="assesses",direction="becomes_contested",kind="diagnosis",status="delivered",merit=99)
    d=claim(key="id:d4",cid="c:d4:1",obj="research.infrastructure",mech="assesses",direction="becomes_contested",kind="effect",status="delivered",merit=99)
    nodes=[_node(a,"A"),_node(b,"B"),_node(g,"C"),_node(d,"D")]
    assert conflicting_criteria(nodes,build_distance_table(nodes)) == []
