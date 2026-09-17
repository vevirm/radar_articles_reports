from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from scripts.claim_reasoning_shadow import (
    build_distance_table,
    corroborated_claims,
    conflicting_criteria,
    dependency_pathways,
    distance_for,
    flatten_claims,
    level3_findings,
    opposing_movements,
    latent_channels,
    anchor_demand_candidates,
    split_recurrence_candidates,
    era_conjunctions,
    shadow_diff_report,
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
    exposure=claim(key="id:ex",cid="c:ex:1",obj="compute.gigafactory",mech="assesses",direction="contracts",kind="diagnosis",status="operating",merit=95)
    exposure["text"]="The capability is exposed to a concentrated, capacity-limited supply base."
    propagation=claim(key="id:pr",cid="c:pr:1",obj="datacentre.energy_supply",mech="assesses",direction="contracts",kind="effect",status="operating",merit=95)
    propagation["text"]="The disruption is spreading across multiple European sites."
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
    exposure=claim(key="id:ex3",cid="c:ex3:1",obj="compute.gigafactory",mech="assesses",direction="contracts",kind="diagnosis",status="operating",merit=95)
    exposure["text"]="The capability is vulnerable because supply is limited and concentrated."
    propagation=claim(key="id:pr3",cid="c:pr3:1",obj="datacentre.energy_supply",mech="assesses",direction="contracts",kind="effect",status="operating",merit=95)
    propagation["text"]="The disruption reaches multiple sites across Europe."
    nodes=[_node(commitment,"S1"),_node(coupling,"S2"),_node(exposure,"S3"),_node(propagation,"S4")]
    out=dependency_pathways(nodes,VOCAB,build_distance_table(nodes))
    assert out
    assert out[0]["frontier_mode"] == "exact_object_overlap"
    assert out[0]["coupling_hop"] == 1
    assert out[0]["dependency_object"] == "datacentre.energy_supply"


def test_conflicting_criteria_does_not_treat_delivered_generic_diagnosis_as_a_criterion():
    a=claim(key="id:a4",cid="c:a4:1",obj="research.infrastructure",mech="assesses",direction="expands",kind="diagnosis",status="delivered",merit=99)
    b=claim(key="id:b4",cid="c:b4:1",obj="research.infrastructure",mech="assesses",direction="contracts",kind="diagnosis",status="delivered",merit=99)
    g=claim(key="id:g4",cid="c:g4:1",obj="research.infrastructure",mech="assesses",direction="becomes_contested",kind="diagnosis",status="delivered",merit=99)
    d=claim(key="id:d4",cid="c:d4:1",obj="research.infrastructure",mech="assesses",direction="becomes_contested",kind="effect",status="delivered",merit=99)
    nodes=[_node(a,"A"),_node(b,"B"),_node(g,"C"),_node(d,"D")]
    assert conflicting_criteria(nodes,VOCAB,build_distance_table(nodes)) == []


def test_conflicting_criteria_can_join_distinct_endpoint_objects_through_shared_target():
    # Mirrors the quantum worked shape: open testing infrastructure -> controlled
    # equipment -> national export-control competence, with a national divergence
    # branch reached through dual-use/research-security objects.
    a=claim(key="id:qa",cid="c:qa:1",obj="quantum.testing_infrastructure",mech="funds",direction="expands",kind="action",status="call_open",merit=99,secondary=["quantum.equipment"])
    b=claim(key="id:qb",cid="c:qb:1",obj="export_control.competence",mech="restricts",direction="becomes_conditional",kind="diagnosis",status="in_force",merit=68,secondary=["quantum.equipment","innovation.dual_use"])
    gap=claim(key="id:qg",cid="c:qg:1",obj="export_control.competence",mech="assesses",direction="becomes_contested",kind="diagnosis",status="delivered",merit=82)
    bridge=claim(key="id:qbr",cid="c:qbr:1",obj="innovation.dual_use",mech="assesses",direction="unchanged",kind="diagnosis",status="delivered",merit=77,secondary=["research_security.screening"])
    div=claim(key="id:qd",cid="c:qd:1",obj="research_security.screening",mech="assesses",direction="becomes_contested",kind="diagnosis",status="delivered",merit=82)
    nodes=[_node(a,"A"),_node(b,"B"),_node(gap,"C"),_node(bridge,"D"),_node(div,"E")]
    out=conflicting_criteria(nodes,VOCAB,build_distance_table(nodes))
    assert out
    q=out[0]
    assert q["criterion_a_object"]=="quantum.testing_infrastructure"
    assert q["criterion_b_object"]=="export_control.competence"
    assert q["roles"]["arbitration_gap"]["claim_id"]=="c:qg:1"
    assert q["roles"]["divergence"]["claim_id"]=="c:qd:1"
    assert q["score"] >= 70
    assert q["publication_gate_passes"] is False


def test_dependency_roles_require_propagation_and_exposure_semantics_not_generic_negative_diagnoses():
    commitment=claim(key="id:rco",cid="c:rco:1",obj="research.system_governance",mech="adopts",direction="expands",kind="action",status="adopted",merit=99,secondary=["goal.strategic_autonomy"])
    coupling=claim(key="id:rcu",cid="c:rcu:1",obj="goal.strategic_autonomy",mech="requires",direction="becomes_conditional",kind="diagnosis",status="delivered",merit=90,secondary=["finance.strategic_investment"])
    propagation=claim(key="id:rpr",cid="c:rpr:1",obj="finance.strategic_investment",mech="assesses",direction="contracts",kind="diagnosis",status="delivered",merit=90)
    propagation["text"]="Investment conditions changed this year."  # no multi-site propagation evidence
    exposure=claim(key="id:rex",cid="c:rex:1",obj="research.system_governance",mech="assesses",direction="becomes_contested",kind="diagnosis",status="delivered",merit=100)
    exposure["text"]="A status review finds uneven uptake of laboratory methods."  # not scarcity/concentration/dependence
    nodes=[_node(commitment,"S1"),_node(coupling,"S2"),_node(propagation,"S3"),_node(exposure,"S4")]
    out=dependency_pathways(nodes,VOCAB,build_distance_table(nodes))
    assert not any(x.get("score_gate_passes") for x in out)


def test_dependency_worked_shape_allows_downstream_trigger_and_excludes_chain_records_from_distance():
    commitment=claim(key="id:wco",cid="c:wco:1",obj="compute.public_procurement",mech="procures",direction="expands",kind="action",status="call_open",merit=99,secondary=["compute.gigafactory","compute.capacity"])
    coupling=claim(key="id:wcu",cid="c:wcu:1",obj="compute.private_investment",mech="requires",direction="expands",kind="action",status="announced",merit=90,secondary=["datacentre.energy_supply","compute.capacity"])
    propagation=claim(key="id:wpr",cid="c:wpr:1",obj="datacentre.energy_supply",mech="requires",direction="becomes_conditional",kind="effect",status="delivered",merit=90,secondary=["compute.private_investment","compute.capacity"])
    propagation["text"]="European data-centre geography is changing across multiple locations because of power constraints."
    exposure=claim(key="id:wex",cid="c:wex:1",obj="compute.capacity",mech="assesses",direction="contracts",kind="diagnosis",status="delivered",merit=100)
    exposure["text"]="EU compute capacity is limited and geographically concentrated, with supplier dependence."
    trigger=claim(key="id:wtr",cid="c:wtr:1",obj="datacentre.permitting",mech="regulates",direction="becomes_conditional",kind="action",status="proposed",merit=90,secondary=["datacentre.energy_supply","compute.private_investment"])
    nodes=[_node(commitment,"S1"),_node(coupling,"S2"),_node(propagation,"S3"),_node(exposure,"S4"),_node(trigger,"S5")]
    out=dependency_pathways(nodes,VOCAB,build_distance_table(nodes))
    match=next(x for x in out if x["capability_object"]=="compute.public_procurement" and x["dependency_object"]=="datacentre.energy_supply")
    assert match["product"]=="risk"
    assert match["endpoint_objects"]==["compute.public_procurement","datacentre.permitting"]
    assert match["trigger"]["claim_id"]=="c:wtr:1"
    assert match["missing_roles"]==[]
    assert match["distance"]=="distant"
    assert match["endpoint_joint_outside_chain"]==0


def test_delivered_analysis_is_not_a_risk_trigger():
    commitment=claim(key="id:tco",cid="c:tco:1",obj="compute.gigafactory",mech="builds",direction="expands",kind="action",status="operating",merit=99,secondary=["compute.private_investment"])
    coupling=claim(key="id:tcu",cid="c:tcu:1",obj="compute.private_investment",mech="requires",direction="becomes_conditional",kind="action",status="operating",merit=95,secondary=["datacentre.energy_supply"])
    propagation=claim(key="id:tpr",cid="c:tpr:1",obj="datacentre.energy_supply",mech="requires",direction="becomes_conditional",kind="effect",status="delivered",merit=95)
    propagation["text"]="Power constraints are spreading across multiple European sites."
    exposure=claim(key="id:tex",cid="c:tex:1",obj="compute.gigafactory",mech="assesses",direction="contracts",kind="diagnosis",status="delivered",merit=95)
    exposure["text"]="The buildout is exposed to a concentrated and capacity-limited supply base."
    analytical=claim(key="id:tan",cid="c:tan:1",obj="datacentre.energy_supply",mech="restricts",direction="contracts",kind="diagnosis",status="delivered",merit=99)
    nodes=[_node(commitment,"S1"),_node(coupling,"S2"),_node(propagation,"S3"),_node(exposure,"S4"),_node(analytical,"S5")]
    out=dependency_pathways(nodes,VOCAB,build_distance_table(nodes))
    assert out
    assert all(x["product"]=="shock" for x in out if x["capability_object"]=="compute.gigafactory")


def test_conflicting_criteria_divergence_must_bind_the_arbitration_branch():
    a=claim(key="id:ca",cid="c:ca:1",obj="quantum.testing_infrastructure",mech="funds",direction="expands",kind="action",status="call_open",merit=99,secondary=["quantum.equipment"])
    b=claim(key="id:cb",cid="c:cb:1",obj="export_control.competence",mech="restricts",direction="becomes_conditional",kind="diagnosis",status="in_force",merit=80,secondary=["quantum.equipment","innovation.dual_use"])
    gap=claim(key="id:cg",cid="c:cg:1",obj="export_control.competence",mech="assesses",direction="becomes_contested",kind="diagnosis",status="delivered",merit=82,secondary=["research_security.screening"])
    good=claim(key="id:cd",cid="c:cd:1",obj="research_security.screening",mech="assesses",direction="becomes_contested",kind="diagnosis",status="delivered",merit=80,secondary=["research.openness"])
    bad=claim(key="id:cx",cid="c:cx:1",obj="research.openness",mech="assesses",direction="contracts",kind="diagnosis",status="delivered",merit=99)
    nodes=[_node(a,"A"),_node(b,"B"),_node(gap,"C"),_node(good,"D"),_node(bad,"E")]
    out=conflicting_criteria(nodes,VOCAB,build_distance_table(nodes))
    assert out
    assert out[0]["roles"]["divergence"]["claim_id"]=="c:cd:1"



def test_clock_before_rule_requires_a_real_pending_control_rule():
    commitment=claim(key="id:clock",cid="c:clock:1",obj="compute.public_procurement",mech="procures",direction="expands",kind="action",status="call_open",date="2026-07-30",secondary=["compute.capacity"])
    commitment["deadline"]="2026-11-12"
    bridge=claim(key="id:bridge",cid="c:bridge:1",obj="compute.capacity",mech="requires",direction="becomes_conditional",kind="diagnosis",status="delivered",secondary=["datacentre.energy_supply"])
    rule=claim(key="id:rule",cid="c:rule:1",obj="datacentre.permitting",mech="regulates",direction="becomes_conditional",kind="action",status="proposed",secondary=["datacentre.energy_supply"])
    nodes=[_node(commitment,"S1"),_node(bridge,"S2"),_node(rule,"S3")]
    out=level3_findings(nodes,dt.date(2026,9,17))
    clock=next(x for x in out if x["grammar_id"]=="clock_before_rule")
    assert clock["object"]=="compute.public_procurement"
    assert clock["deadline"]=="2026-11-12"
    assert "c:rule:1" in clock["rule_claim_ids"]

    adopted=claim(key="id:rule2",cid="c:rule2:1",obj="datacentre.permitting",mech="regulates",direction="becomes_conditional",kind="action",status="adopted",secondary=["datacentre.energy_supply"])
    out2=level3_findings(nodes+[_node(adopted,"S4")],dt.date(2026,9,17))
    assert not any(x["grammar_id"]=="clock_before_rule" and x.get("object")=="compute.public_procurement" for x in out2)


def test_success_metric_gap_stays_within_one_programme_family_and_requires_no_effect_measurement():
    relation=claim(key="id:rel",cid="c:rel:1",obj="talent.recruitment_abroad",mech="advocates",direction="expands",kind="advocacy",status="delivered",secondary=["talent.retention"])
    relation["text"]="The programme aims to attract and retain researchers."
    delivery=claim(key="id:del",cid="c:del:1",obj="talent.recruitment_abroad",mech="recruits",direction="expands",kind="action",status="call_open")
    success=claim(key="id:suc",cid="c:suc:1",obj="talent.retention",mech="assesses",direction="unchanged",kind="diagnosis",status="delivered")
    nodes=[_node(relation,"S1"),_node(delivery,"S2"),_node(success,"S3")]
    out=level3_findings(nodes,dt.date(2026,9,17))
    assert any(x["grammar_id"]=="success_metric_gap" and x["objective_object"]=="talent.retention" and x["delivery_object"]=="talent.recruitment_abroad" for x in out)
    measured=claim(key="id:meas",cid="c:meas:1",obj="talent.retention",mech="assesses",direction="expands",kind="effect",status="delivered")
    out2=level3_findings(nodes+[_node(measured,"S4")],dt.date(2026,9,17))
    assert not any(x["grammar_id"]=="success_metric_gap" and x["objective_object"]=="talent.retention" for x in out2)


def test_latent_channel_with_one_missing_live_connection_is_watch_only():
    need=claim(key="id:need",cid="c:need:1",obj="research.infrastructure",mech="assesses",direction="becomes_conditional",kind="diagnosis",status="delivered",secondary=["compute.access_time"])
    need["text"]="Research infrastructure onboarding needs a visible service and funding model."
    structure=claim(key="id:str",cid="c:str:1",obj="compute.access_time",mech="builds",direction="expands",kind="action",status="operating")
    structure["text"]="A federation platform provides unified access and authentication."
    instrument=claim(key="id:inst",cid="c:inst:1",obj="research.infrastructure",mech="funds",direction="expands",kind="action",status="announced")
    instrument["text"]="A task force is the receiving instrument for infrastructure onboarding."
    precedent=claim(key="id:pre",cid="c:pre:1",obj="compute.access_time",mech="assesses",direction="expands",kind="effect",status="delivered")
    precedent["text"]="An existing platform demonstrates the service model already operating."
    nodes=[_node(need,"S1"),_node(structure,"S2"),_node(instrument,"S3"),_node(precedent,"S4")]
    out=latent_channels(nodes,VOCAB)
    assert out
    cand=out[0]
    assert cand["missing_roles"]==["live_connection"]
    assert cand["score"] is None
    assert cand["score_gate_passes"] is False
    assert cand["publication_gate_passes"] is False


def test_anchor_demand_requires_supply_payoff_and_keeps_publication_locked():
    commitment=claim(key="id:ac",cid="c:ac:1",obj="compute.gigafactory",mech="builds",direction="expands",kind="action",status="call_open",secondary=["chips.eu_inference_supplier"])
    payoff=claim(key="id:ap",cid="c:ap:1",obj="chips.eu_inference_supplier",mech="sells",direction="expands",kind="effect",status="delivered",secondary=["compute.gigafactory"])
    payoff["text"]="The supplier signed a supply deal and won a customer contract."
    protect=claim(key="id:ai",cid="c:ai:1",obj="chips.eu_inference_supplier",mech="conditions",direction="becomes_conditional",kind="action",status="adopted",secondary=["compute.gigafactory"])
    protect["text"]="The instrument protects EU interests with a blocking stake and IP safeguards."
    conversion=claim(key="id:av",cid="c:av:1",obj="compute.gigafactory",mech="requires",direction="becomes_conditional",kind="diagnosis",status="delivered",secondary=["chips.eu_inference_supplier"])
    conversion["text"]="Conversion to value requires fast access and movement between providers."
    reform=claim(key="id:ar",cid="c:ar:1",obj="compute.gigafactory",mech="proposes",direction="expands",kind="action",status="proposed",secondary=["chips.eu_inference_supplier"])
    reform["text"]="A procurement reform would raise public-sector demand."
    nodes=[_node(commitment,"S1"),_node(payoff,"S2"),_node(protect,"S3"),_node(conversion,"S4"),_node(reform,"S5")]
    out=anchor_demand_candidates(nodes,VOCAB)
    assert out
    cand=out[0]
    assert cand["endpoint_objects"]==["compute.gigafactory","chips.eu_inference_supplier"]
    assert cand["missing_roles"]==[]
    assert cand["publication_gate_passes"] is False


def test_split_recurrence_uses_authoritative_historical_relation_and_current_side_floors():
    hist=claim(key="historical:id:h",cid="c:h:1",obj="horizon.access",mech="conditions",direction="becomes_conditional",kind="diagnosis",status="delivered",date="2018-11-01",secondary=["eu_bilateral_agreements"])
    hist["era"]="historical"; hist["record_key"]="historical:id:h"
    hn=_node(hist,"H",primary=False,collection="historical_context"); hn["_decision"]="keep"; hn["_context_weight"]=1.0
    nodes=[hn]
    for i,(obj,direction) in enumerate([("horizon.access","expands")]*3+[("eu_bilateral_agreements","becomes_conditional")]*3,1):
        c=claim(key=f"id:s{i}",cid=f"c:s{i}:1",obj=obj,mech="conditions" if "bilateral" in obj else "associates",direction=direction,kind="effect" if i%2==0 else "action",status="in_force")
        nodes.append(_node(c,f"S{(i%3)+1}"))
    out=split_recurrence_candidates(nodes,VOCAB)
    assert out
    cand=out[0]
    assert cand["endpoint_objects"]==["eu_bilateral_agreements","horizon.access"] or cand["endpoint_objects"]==["horizon.access","eu_bilateral_agreements"]
    assert cand["current_joint"]==0
    assert cand["wow_preliminary"]==5
    assert cand["publication_gate_passes"] is False


def test_era_conjunction_requires_source_floors_and_lift_gain():
    nodes=[]
    # Six current joint records from six sources, plus marginal records to make the pair unusually coupled.
    for i in range(6):
        c=claim(key=f"id:cj{i}",cid=f"c:cj{i}:1",obj="chips.fab",mech="assesses",direction="unchanged",kind="diagnosis",secondary=["export_control.regulation"])
        nodes.append(_node(c,f"C{i}"))
    for i in range(2):
        nodes.append(_node(claim(key=f"id:ca{i}",cid=f"c:ca{i}:1",obj="chips.fab",mech="assesses",direction="unchanged",kind="diagnosis"),f"CA{i}"))
        nodes.append(_node(claim(key=f"id:cb{i}",cid=f"c:cb{i}:1",obj="export_control.regulation",mech="assesses",direction="unchanged",kind="diagnosis"),f"CB{i}"))
    for i in range(9):
        nodes.append(_node(claim(key=f"id:co{i}",cid=f"c:co{i}:1",obj="talent.retention",mech="assesses",direction="unchanged",kind="diagnosis"),f"CO{i}"))
    # Historical pair is more ordinary: three joint records and marginal records.
    for i in range(3):
        h=claim(key=f"historical:id:hj{i}",cid=f"c:hj{i}:1",obj="chips.fab",mech="assesses",direction="unchanged",kind="diagnosis",date="2018-01-01",secondary=["export_control.regulation"])
        h["era"]="historical"; h["record_key"]=f"historical:id:hj{i}"
        n=_node(h,f"H{i}",primary=False,collection="historical_context"); n["_decision"]="keep"; n["_context_weight"]=1.0; nodes.append(n)
    for i,obj in enumerate(["chips.fab","export_control.regulation","talent.retention","talent.retention"]):
        h=claim(key=f"historical:id:hm{i}",cid=f"c:hm{i}:1",obj=obj,mech="assesses",direction="unchanged",kind="diagnosis",date="2019-01-01")
        h["era"]="historical"; h["record_key"]=f"historical:id:hm{i}"
        n=_node(h,f"HM{i}",primary=False,collection="historical_context"); n["_decision"]="keep"; n["_context_weight"]=1.0; nodes.append(n)
    out=era_conjunctions(nodes)
    match=next(x for x in out if set(x["endpoint_objects"])=={"chips.fab","export_control.regulation"})
    assert match["current_joint"]==6
    assert match["current_sources"]>=5
    assert match["historical_joint"]==3
    assert match["gain"]>=0.38


def test_shadow_diff_is_count_only_and_never_changes_publication():
    legacy={"candidate_count":2,"by_grammar":{"dependency_pathway":1}}
    groups={"level5_dependency_pathway":[{"id":1}],"level4_5_conflicting_criteria":[],"level2_corroborated":[]}
    diff=shadow_diff_report(legacy,groups)
    assert diff["legacy_candidate_count"]==2
    assert diff["shadow_by_grammar"]["dependency_pathway"]==1
    assert diff["publication_delta"]==0
