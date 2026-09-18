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
    n = node("c:one", "Source A", text="The publication documents current research-infrastructure priorities.")
    cand = live.adapt_candidate(raw(["c:one"]), [n], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["primary_sources"] == 1
    assert cand["evidence_semantics"] == "single_source_anchor"
    assert cand["verification_mode"] == "single_source_anchor"
    assert cand["verification_gate_passes"] is False
    assert "independent sources" not in cand["reader_summary"].lower()
    assert "radar's synthesis" in cand["reader_summary"].lower()
    assert "could become more contested" in cand["reader_title"].lower()
    assert cand["product_basis"] == "single_source_future_anchor"
    assert "evidence-anchored future hypothesis" in cand["topic_label"]


def test_support_rows_preserve_narrow_source_statement_and_reader_safe_contribution():
    statement = "The publication reports that the portfolio aligns with climate-risk priorities."
    n = node("c:evidence", "Source A", text=statement)
    cand = live.adapt_candidate(raw(["c:evidence"]), [n], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["support"][0]["source_statement"] == statement
    assert cand["support"][0]["evidence_contribution"]
    assert cand["reader_title"] not in statement


def test_two_independent_sources_still_count_as_genuine_corroboration():
    n1 = node("c:a", "Source A", text="Source A reports the condition.")
    n2 = node("c:b", "Source B", text="Source B independently reports the same condition.")
    cand = live.adapt_candidate(raw(["c:a", "c:b"]), [n1, n2], vocab={}, evaluated_on=dt.date(2026, 9, 18))

    assert cand["primary_sources"] == 2
    assert cand["evidence_semantics"] == "corroborated"
    assert cand["verification_mode"] == "corroborated_claim_floor"
    assert cand["verification_gate_passes"] is True
