from __future__ import annotations

import datetime as dt

from scripts import claim_reasoning_live as live


def node(cid: str, source: str, *, text: str, direction: str = "becomes_contested") -> dict:
    return {
        "claim_id": cid,
        "record_key": f"link:https://example.test/{cid}",
        "_record_id": f"r:{cid}",
        "_link": f"https://example.test/{cid}",
        "_title": f"Publication {cid}",
        "_source": source,
        "_collection": "strand_a",
        "_primary": True,
        "_new_this_scan": False,
        "era": "current",
        "object": "research.infrastructure",
        "secondary_objects": [],
        "mechanism": "assesses",
        "direction": direction,
        "kind": "diagnosis",
        "status": "delivered",
        "status_date": "2026-07-16",
        "merit": 90,
        "text": text,
        "scope": {"level": "eu", "countries": []},
        "actor": {"name": source, "class": "eu_body"},
        "attributes": {},
    }


def raw(claim_ids: list[str]) -> dict:
    return {
        "level": 2,
        "grammar_id": "corroborated_claim",
        "product": "risk",
        "object": "research.infrastructure",
        "mechanism": "assesses",
        "direction": "becomes_contested",
        "status": "delivered",
        "product_basis": "corroborated_constraint",
        "claim_ids": claim_ids,
        "score": 80,
        "score_gate_passes": True,
        "wow_preliminary": 2,
    }


def test_single_source_anchor_is_not_labelled_verified_corroboration():
    n = node("c:one", "Source A", text="The publication documents growing opposition to the proposed research infrastructure.")
    cand = live.adapt_candidate(raw(["c:one"]), [n], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["primary_sources"] == 1
    assert cand["direction_grounded_sources"] == 1
    assert cand["evidence_semantic_alignment"] is True
    assert cand["evidence_semantics"] == "single_source_anchor"
    assert cand["verification_mode"] == "single_source_anchor"
    assert cand["verification_gate_passes"] is False
    assert "independent sources" not in cand["reader_summary"].lower()
    assert "contestation widens or hardens" in cand["reader_summary"].lower()
    assert "could become more contested" in cand["reader_title"].lower()
    assert cand["product_basis"] == "single_source_future_anchor"
    assert "evidence-anchored future hypothesis" in cand["topic_label"]


def test_support_rows_preserve_narrow_source_statement_without_generic_contribution_boilerplate():
    statement = "The publication reports growing opposition to the proposed research infrastructure."
    n = node("c:evidence", "Source A", text=statement)
    cand = live.adapt_candidate(raw(["c:evidence"]), [n], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["support"][0]["source_statement"] == statement
    assert cand["support"][0]["evidence_contribution"] == ""
    assert cand["reader_title"] not in statement


def test_two_independent_sources_still_count_as_genuine_corroboration():
    n1 = node("c:a", "Source A", text="Source A reports growing opposition to the infrastructure.")
    n2 = node("c:b", "Source B", text="Source B independently reports that the research infrastructure project is contested.")
    cand = live.adapt_candidate(raw(["c:a", "c:b"]), [n1, n2], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["primary_sources"] == 2
    assert cand["direction_grounded_sources"] == 2
    assert cand["evidence_semantics"] == "corroborated"
    assert cand["verification_mode"] == "corroborated_claim_floor"
    assert cand["verification_gate_passes"] is True


def test_neutral_source_statement_cannot_publish_a_contested_direction():
    statement = "The portfolio is broadly aligned with EU climate-risk priorities and strong in observation, monitoring and foresight capabilities."
    n = node("c:neutral", "European Research Executive Agency", text=statement)
    cand = live.adapt_candidate(raw(["c:neutral"]), [n], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert n["direction"] == "becomes_contested"  # authoritative claim remains untouched
    assert cand["direction_grounded_sources"] == 0
    assert cand["evidence_semantic_alignment"] is False
    assert cand["evidence_semantics"] == "source_statement_direction_mismatch"
    assert cand["verification_mode"] == "source_statement_direction_mismatch"
    ready, reason = live._presentation_ready({**cand, "maturity_score": 90})
    assert ready is False
    assert reason == "source_statement_direction_mismatch"


def shock_node(cid: str, source: str, *, text: str, obj: str, mechanism: str = "assesses") -> dict:
    return {
        "claim_id": cid,
        "record_key": f"link:https://example.test/{cid}",
        "_record_id": f"r:{cid}",
        "_link": f"https://example.test/{cid}",
        "_title": f"Publication {cid}",
        "_source": source,
        "_collection": "strand_a",
        "_primary": True,
        "_new_this_scan": False,
        "era": "current",
        "object": obj,
        "secondary_objects": [],
        "mechanism": mechanism,
        "direction": "unchanged",
        "kind": "diagnosis",
        "status": "delivered",
        "status_date": "2026-09-01",
        "merit": 90,
        "text": text,
        "scope": {"level": "eu", "countries": []},
        "actor": {"name": source, "class": "eu_body"},
        "attributes": {},
    }


def shock_raw(asset_cid: str, driver_cid: str, *, pressure_id: str, pressure_label: str) -> dict:
    def snap(cid: str, role: str, obj: str) -> dict:
        return {
            "claim_id": cid,
            "record_key": f"link:https://example.test/{cid}",
            "role": role,
            "source": "",
            "title": "",
            "status": "delivered",
            "status_date": "2026-09-01",
            "merit": 90,
            "strength": 0.9,
            "object": obj,
            "mechanism": "assesses",
        }

    return {
        "level": 5,
        "grammar_id": "future_shock_hypothesis",
        "product": "shock",
        "capability_object": "compute.capacity",
        "dependency_object": pressure_id,
        "endpoint_objects": ["compute.capacity", f"shock_pressure.{pressure_id}"],
        "pressure_id": pressure_id,
        "pressure_label": pressure_label,
        "shock_driver": True,
        "shock_driver_basis": f"scenario_operator:{pressure_id}",
        "roles": {
            "commitment": snap(asset_cid, "commitment", "compute.capacity"),
            "external_driver": snap(driver_cid, "external_driver", "energy.grid"),
        },
        "missing_roles": ["bridge"],
        "score": 80,
        "floor_ok": True,
        "wow_preliminary": 2,
        "score_gate_passes": False,
        "publication_gate_passes": False,
    }


def test_neutral_energy_arrangement_can_seed_shock_stock_but_not_publication():
    asset = shock_node(
        "c:asset", "EuroHPC", text="Europe is building new AI computing capacity.", obj="compute.capacity", mechanism="builds"
    )
    driver = shock_node(
        "c:driver", "Example Energy Source", text="The company announced a new AI-compute investment and energy arrangement in Finland.", obj="energy.grid"
    )
    cand = live.adapt_candidate(
        shock_raw("c:asset", "c:driver", pressure_id="energy", pressure_label="an abrupt power constraint"),
        [asset, driver], vocab={}, evaluated_on=dt.date(2026, 9, 18),
    )

    assert cand["shock_driver"] is True  # hypothesis formation remains broad
    assert cand["shock_driver_semantic_alignment"] is False
    assert cand["evidence_semantic_alignment"] is False
    assert cand["evidence_semantics"] == "shock_driver_statement_mismatch"
    assert cand["product_basis"] == "shock_driver_statement_mismatch"
    ready, reason = live._presentation_ready({**cand, "maturity_score": 90})
    assert ready is False
    assert reason == "shock_driver_statement_mismatch"


def test_documented_power_constraint_can_anchor_public_shock_semantics():
    asset = shock_node(
        "c:asset2", "EuroHPC", text="Europe is building new AI computing capacity.", obj="compute.capacity", mechanism="builds"
    )
    driver = shock_node(
        "c:driver2", "Market Source", text="European data-centre locations are changing in response to power and land constraints.", obj="energy.grid"
    )
    cand = live.adapt_candidate(
        shock_raw("c:asset2", "c:driver2", pressure_id="energy", pressure_label="an abrupt power constraint"),
        [asset, driver], vocab={}, evaluated_on=dt.date(2026, 9, 18),
    )

    assert cand["shock_driver_semantic_alignment"] is True
    assert cand["shock_driver_grounded_records"] == 1
    assert cand["evidence_semantic_alignment"] is True
    assert cand["evidence_semantics"] == "synthesis"
    assert cand["support"][1]["evidence_contribution"] == "Establishes the documented disruption mechanism used in this scenario."


def test_conditional_direction_must_attach_to_the_claim_object():
    n = {
        **node(
            "c:conditional-mismatch",
            "Source A",
            text="Research security becomes embedded through multi-level coordination, making scientific openness more conditional.",
            direction="becomes_conditional",
        ),
        "object": "research_security.screening",
    }
    r = {
        **raw(["c:conditional-mismatch"]),
        "object": "research_security.screening",
        "direction": "becomes_conditional",
    }
    cand = live.adapt_candidate(r, [n], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["direction_grounded_sources"] == 0
    assert cand["evidence_semantic_alignment"] is False


def test_trend_side_does_not_treat_negated_establishment_as_expansion():
    n = {
        "text": "No substantive proposal could be established: the retrieved material contains framing but not recommendations.",
        "object": "compute.capacity",
        "direction": "expands",
    }
    assert live._reader_trend_side(n) == ""


def test_trend_side_treats_widening_gap_as_constraint_not_expansion():
    n = {
        "text": "A seven-dimension indicator finds widening centre-periphery gaps in innovation performance.",
        "object": "innovation.system_performance",
        "direction": "expands",
    }
    assert live._reader_trend_side(n) == "constrains"


def test_trend_side_treats_asymmetric_external_dependence_as_constraint():
    n = {
        "text": "AI investment is highly asymmetric, leaving EU countries exposed to dependence on external technology and capital.",
        "object": "finance.strategic_investment",
        "direction": "expands",
    }
    assert live._reader_trend_side(n) == "constrains"


def test_shock_story_key_keeps_different_drivers_separate():
    cyber = {
        "product": "shock",
        "pressure_id": "cyber",
        "endpoint_objects": ["compute.capacity", "shock_pressure.cyber"],
    }
    energy = {
        "product": "shock",
        "pressure_id": "energy",
        "endpoint_objects": ["compute.capacity", "shock_pressure.energy"],
    }
    assert live._story_key(cyber) != live._story_key(energy)


def test_direction_evidence_must_name_the_object_not_only_the_direction():
    n = {
        **node(
            "c:wrong-object",
            "EFSA",
            text="EFSA established an EU Early Warning System for emerging chemical risks.",
            direction="expands",
        ),
        "object": "research.system_governance",
        "mechanism": "launches",
        "kind": "action",
        "status": "operating",
    }
    r = {
        **raw(["c:wrong-object"]),
        "product": "opportunity",
        "object": "research.system_governance",
        "direction": "expands",
        "mechanism": "launches",
    }
    cand = live.adapt_candidate(r, [n], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["direction_grounded_sources"] == 0
    assert cand["evidence_semantic_alignment"] is False
    ready, reason = live._presentation_ready({**cand, "maturity_score": 90})
    assert ready is False
    assert reason == "source_statement_direction_mismatch"


def test_hyphenated_object_phrase_still_counts_as_visible_anchor():
    assert live._statement_grounds_object(
        "research_security.screening",
        "Austria established an ERA-linked research-security initiative focused on institutional risk management.",
    ) is True


def test_public_future_shock_can_publish_with_separate_asset_and_driver_anchors():
    asset = shock_node(
        "c:asset3", "EuroHPC", text="Europe is building new AI computing capacity.", obj="compute.capacity", mechanism="builds"
    )
    driver = shock_node(
        "c:driver3", "Market Source", text="European data-centre locations are changing in response to power and land constraints.", obj="energy.grid"
    )
    cand = live.adapt_candidate(
        shock_raw("c:asset3", "c:driver3", pressure_id="energy", pressure_label="an abrupt power constraint"),
        [asset, driver], vocab={}, evaluated_on=dt.date(2026, 9, 18),
    )

    assert cand["shock_driver_semantic_alignment"] is True
    assert cand["role_semantic_alignment"] is True
    assert cand["role_semantic_reason"] == "reader_visible_shock_anchors"
    assert cand["role_semantic_checks"]["bridge_links_asset_and_pressure"] is False
    assert "radar's future hypothesis" in cand["reader_summary"].lower()
    ready, reason = live._presentation_ready({**cand, "maturity_score": 90})
    assert ready is True
    assert reason == "grounded_future_shock"


def test_public_future_shock_can_publish_when_bridge_names_asset_and_pressure_domain():
    asset = shock_node(
        "c:asset4", "EuroHPC", text="Europe is building new AI computing capacity.", obj="compute.capacity", mechanism="builds"
    )
    driver = shock_node(
        "c:driver4", "Market Source", text="European data-centre locations are changing in response to power and land constraints.", obj="energy.grid"
    )
    bridge = shock_node(
        "c:bridge4", "Infrastructure Source", text="The AI compute build-out includes a dedicated electricity and grid connection package.", obj="compute.capacity"
    )
    r = shock_raw("c:asset4", "c:driver4", pressure_id="energy", pressure_label="an abrupt power constraint")
    r["roles"]["bridge"] = {
        "claim_id": "c:bridge4",
        "record_key": "link:https://example.test/c:bridge4",
        "role": "bridge",
        "source": "",
        "title": "",
        "status": "operating",
        "status_date": "2026-09-01",
        "merit": 90,
        "strength": 0.9,
        "object": "compute.capacity",
        "mechanism": "requires",
    }
    r["missing_roles"] = []
    cand = live.adapt_candidate(r, [asset, driver, bridge], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["role_semantic_alignment"] is True
    assert cand["role_semantic_checks"]["bridge_links_asset_and_pressure"] is True
    ready, reason = live._presentation_ready({**cand, "maturity_score": 90})
    assert ready is True
    assert reason == "grounded_future_shock"


def _role_snap(cid: str, role: str, obj: str, mechanism: str = "assesses") -> dict:
    return {
        "claim_id": cid,
        "record_key": f"link:https://example.test/{cid}",
        "role": role,
        "source": "",
        "title": "",
        "status": "delivered",
        "status_date": "2026-09-01",
        "merit": 90,
        "strength": 0.9,
        "object": obj,
        "mechanism": mechanism,
    }


def test_dependency_pathway_keeps_future_propagation_as_radar_inference():
    commitment = shock_node(
        "c:dep-cap", "Source A", text="Europe is expanding innovation-system performance capacity.", obj="innovation.system_performance", mechanism="builds"
    )
    coupling = shock_node(
        "c:dep-couple", "Source B", text="Innovation-system performance depends on research governance capacity.", obj="innovation.system_performance", mechanism="requires"
    )
    propagation = shock_node(
        "c:dep-prop", "Source C", text="Non-animal methods are advancing, but validation and uptake remain uneven.", obj="research.system_governance"
    )
    exposure = shock_node(
        "c:dep-exp", "Source D", text="Innovation performance remains constrained by persistent scale-up gaps.", obj="innovation.system_performance"
    )
    raw_dep = {
        "level": 5,
        "grammar_id": "dependency_pathway",
        "product": "risk",
        "capability_object": "innovation.system_performance",
        "dependency_object": "research.system_governance",
        "endpoint_objects": ["innovation.system_performance", "research.system_governance"],
        "roles": {
            "commitment": _role_snap("c:dep-cap", "commitment", "innovation.system_performance", "builds"),
            "coupling": _role_snap("c:dep-couple", "coupling", "innovation.system_performance", "requires"),
            "propagation": _role_snap("c:dep-prop", "propagation", "research.system_governance"),
            "exposure": _role_snap("c:dep-exp", "exposure", "innovation.system_performance"),
        },
        "missing_roles": [],
        "score": 90,
        "floor_ok": True,
        "wow_preliminary": 4,
        "score_gate_passes": True,
        "publication_gate_passes": False,
    }
    cand = live.adapt_candidate(raw_dep, [commitment, coupling, propagation, exposure], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["role_semantic_alignment"] is True
    assert cand["role_semantic_checks"]["coupling_links_capability_and_dependency"] is True
    assert cand["role_semantic_checks"]["propagation_visible"] is False
    assert not any(x.get("claim_id") == "c:dep-prop" for x in cand["support"])
    assert any(x.get("claim_id") == "c:dep-prop" and x.get("role") == "context" for x in cand["context"])
    assert "radar's inference" in cand["reader_summary"].lower()
    ready, reason = live._presentation_ready({**cand, "maturity_score": 90})
    assert ready is True
    assert reason == "grounded_future_finding"


def test_dependency_pathway_stays_off_page_when_coupling_does_not_link_both_endpoints():
    commitment = shock_node(
        "c:dep-cap2", "Source A", text="Europe is expanding innovation-system performance capacity.", obj="innovation.system_performance", mechanism="builds"
    )
    coupling = shock_node(
        "c:dep-couple2", "Source B", text="Implementation depends on governance capacity and coordination.", obj="innovation.system_performance", mechanism="requires"
    )
    raw_dep = {
        "level": 5, "grammar_id": "dependency_pathway", "product": "risk",
        "capability_object": "innovation.system_performance", "dependency_object": "research.system_governance",
        "endpoint_objects": ["innovation.system_performance", "research.system_governance"],
        "roles": {
            "commitment": _role_snap("c:dep-cap2", "commitment", "innovation.system_performance", "builds"),
            "coupling": _role_snap("c:dep-couple2", "coupling", "innovation.system_performance", "requires"),
        },
        "missing_roles": [], "score": 90, "floor_ok": True, "wow_preliminary": 4, "score_gate_passes": True,
    }
    cand = live.adapt_candidate(raw_dep, [commitment, coupling], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["role_semantic_alignment"] is False
    assert cand["role_semantic_checks"]["coupling_links_capability_and_dependency"] is False
    ready, reason = live._presentation_ready({**cand, "maturity_score": 90})
    assert ready is False
    assert reason == "dependency_anchors_not_visible_in_source_statements"


def test_latent_channel_needs_reader_visible_need_and_structure_before_page_selection():
    structure = shock_node(
        "c:latent-structure", "Source A", text="A research collaboration network is already operating.", obj="research.collaboration", mechanism="launches"
    )
    receiver = shock_node(
        "c:latent-receiver", "Source B", text="The Commission is reviewing an industrial competitiveness instrument.", obj="industrial.competitiveness", mechanism="evaluates"
    )
    raw_latent = {
        "level": 5,
        "grammar_id": "latent_channel",
        "product": "opportunity",
        "endpoint_objects": ["industrial.competitiveness", "research.collaboration"],
        "roles": {
            "existing_structure": _role_snap("c:latent-structure", "existing_structure", "research.collaboration", "launches"),
            "receiving_instrument": _role_snap("c:latent-receiver", "receiving_instrument", "industrial.competitiveness", "evaluates"),
        },
        "missing_roles": ["unresolved_need", "live_connection"],
        "score": 85,
        "floor_ok": True,
        "wow_preliminary": 5,
        "score_gate_passes": False,
        "publication_gate_passes": False,
    }
    cand = live.adapt_candidate(raw_latent, [structure, receiver], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["role_semantic_alignment"] is False
    assert cand["role_semantic_checks"]["unresolved_need_visible"] is False
    ready, reason = live._presentation_ready({**cand, "maturity_score": 90})
    assert ready is False
    assert reason == "latent_channel_missing_reader_visible_core_role"


def test_named_continuity_counts_only_source_visible_object_evidence_and_keeps_history_separate():
    cur1 = node("c:cont-cur1", "Current A", text="European research infrastructure is expanding access to shared facilities.", direction="expands")
    cur2 = node("c:cont-cur2", "Current B", text="Research infrastructure remains a strategic European capability with new shared access routes.", direction="unchanged")
    bad = node("c:cont-bad", "Current C", text="The portfolio is broadly aligned with climate-risk priorities.", direction="unchanged")
    hist1 = node("c:cont-h1", "Historical A", text="European research infrastructure supported shared scientific facilities in the earlier programme period.", direction="unchanged")
    hist2 = node("c:cont-h2", "Historical B", text="Research infrastructure was already treated as a cross-border European capability.", direction="unchanged")
    for h in (hist1, hist2):
        h["era"] = "historical"
        h["_collection"] = "historical_context"
        h["_primary"] = False

    raw_cont = {
        "level": 2,
        "grammar_id": "named_continuity",
        "product": "continuity",
        "object": "research.infrastructure",
        "claim_ids": ["c:cont-cur1", "c:cont-cur2", "c:cont-bad", "c:cont-h1", "c:cont-h2"],
        "missing_roles": [],
        "score": 80,
        "score_gate_passes": True,
        "wow_preliminary": 3,
    }
    cand = live.adapt_candidate(raw_cont, [cur1, cur2, bad, hist1, hist2], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert {x["claim_id"] for x in cand["support"]} == {"c:cont-cur1", "c:cont-cur2"}
    assert any(x.get("claim_id") == "c:cont-bad" and x.get("role") == "context" for x in cand["context"])
    assert {x["claim_id"] for x in cand["continuity_history"]} == {"c:cont-h1", "c:cont-h2"}
    assert cand["current_source_count"] == 2
    assert cand["historical_source_count"] == 2
    ready, reason = live._presentation_ready({**cand, "maturity_score": 90})
    assert ready is True
    assert reason == "two_eras_two_sources"
