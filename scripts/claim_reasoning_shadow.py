#!/usr/bin/env python3
"""Claim-based reasoning shadow for the Radar reasoning reform.

This module is intentionally read-only with respect to Radar's live state. It builds
an in-memory active corpus, reads schema-validated claims, computes the R-10 distance
table and a first deterministic claim-native reasoning pass, then writes only an
operator artifact when asked. It never mutates radar.json, radar_active.json,
reader_text.json, admission state, Deep Scan state, or public reader files.

Stage 5 purpose: establish a safe claim-native shadow beside the legacy regex
reasoning before any detector switch. The shadow is diagnostic, not publishable.
"""
from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]

try:
    from scripts.active_corpus import build_active_document, load_admission, load_corrections, load_reader
    from scripts.claims_schema import date_precision, load_vocabulary, validate_claim
    from scripts.rebuild_active_radar import _add_historical_context
except ModuleNotFoundError:  # direct script execution from scripts/
    from active_corpus import build_active_document, load_admission, load_corrections, load_reader  # type: ignore
    from claims_schema import date_precision, load_vocabulary, validate_claim  # type: ignore
    from rebuild_active_radar import _add_historical_context  # type: ignore

PROFILE = "radar-claim-reasoning-shadow-v1.3-complete-grammar-shadow"
DECISION_WEIGHT = {"keep": 1.0, "review": 0.6, "needs_manual_verification": 0.35, "provisional": 0.35, "awaiting": 0.35}
STATUS_WEIGHT = {
    "operating": 1.0, "in_force": 1.0, "adopted": 0.9, "announced": 0.8,
    "call_open": 0.8, "delivered": 0.8, "in_negotiation": 0.6,
    "proposed": 0.5, "intention": 0.3, "abandoned": 0.0, "lapsed": 0.0,
}
STATUS_RANK = {
    "abandoned": 0, "lapsed": 0, "intention": 1, "proposed": 2, "in_negotiation": 3,
    "announced": 4, "call_open": 4, "adopted": 5, "delivered": 5, "in_force": 6, "operating": 7,
}
KIND_WEIGHT = {"action": 1.0, "effect": 0.9, "diagnosis": 0.7, "advocacy": 0.5}
ROLE_KINDS: dict[str, set[str]] = {
    "commitment": {"action"}, "coupling": {"action", "effect", "diagnosis"},
    "propagation": {"effect", "diagnosis"}, "channel": {"effect", "diagnosis"},
    "exposure": {"diagnosis", "effect"}, "criterion_a": {"action", "diagnosis"},
    "criterion_b": {"action", "diagnosis"}, "arbitration_gap": {"diagnosis"},
    "divergence": {"effect", "diagnosis"}, "unresolved_need": {"diagnosis", "advocacy"},
    "existing_structure": {"action"}, "live_connection": {"action"},
    "receiving_instrument": {"action"}, "precedent": {"diagnosis", "effect"},
    "payoff_evidence": {"effect"}, "protecting_instrument": {"action"},
    "conversion_condition": {"diagnosis", "effect"}, "enabling_reform": {"action"},
    "historical_relation": {"diagnosis", "effect"}, "side_a": {"action", "effect"},
    "side_b": {"action", "effect"}, "success_condition": {"action", "advocacy"},
    "delivery_instrument": {"action"}, "measurement_blind_spot": {"diagnosis"}, "rule_scope": {"action", "diagnosis", "advocacy"},
}
ABSORBERS = {"substitutes", "diversifies", "adds_capacity", "harmonises", "exempts", "reconciles", "secures", "pre_clears"}
RESTRICTION_MECHANISMS = {"restricts", "conditions", "excludes", "licenses", "regulates", "screens", "opposes"}
COUPLING_MECHANISMS = {"requires", "conditions", "feeds_into", "restricts", "regulates", "secures", "pre_clears", "integrates"}
WORLD_COLLECTIONS = ("strand_a", "frontier_evidence", "strand_c", "historical_context")


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _date(value: Any) -> dt.date | None:
    text = clean(value)
    if date_precision(text) != "day":
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def _source(row: dict[str, Any]) -> str:
    return clean(row.get("source") or row.get("journal") or row.get("institution") or row.get("source_domain") or row.get("link") or row.get("url") or "unknown")


def _record_identity(row: dict[str, Any], fallback: str) -> str:
    claims = row.get("claims") if isinstance(row.get("claims"), list) else []
    if claims and isinstance(claims[0], dict) and clean(claims[0].get("record_key")):
        return clean(claims[0].get("record_key"))
    return clean(row.get("link") or row.get("url") or row.get("id") or fallback)


def build_active_snapshot(root: Path = ROOT) -> dict[str, Any]:
    raw = json.loads((root / "radar.json").read_text(encoding="utf-8"))
    admission = load_admission(root / "admission_state.json")
    corrections = load_corrections(root / "record_corrections.json")
    reader = load_reader(root / "reader_text.json")
    active = build_active_document(raw, admission=admission, corrections=corrections, reader=reader)
    _add_historical_context(active, admission=admission, corrections=corrections, reader=reader, historical_path=root / "historical" / "historical.json")
    return active


def object_clusters(obj: str, vocab: dict[str, Any]) -> set[str]:
    meta = (vocab.get("objects") or {}).get(obj)
    if not isinstance(meta, dict):
        return set()
    out = {clean(meta.get("cluster"))}
    out.update(clean(x) for x in meta.get("secondary_clusters", []) if clean(x))
    return {x for x in out if x}


def primary_cluster(obj: str, vocab: dict[str, Any]) -> str:
    meta = (vocab.get("objects") or {}).get(clean(obj), {})
    return clean(meta.get("cluster")) if isinstance(meta, dict) else ""


def claim_clusters(claim: dict[str, Any], vocab: dict[str, Any]) -> set[str]:
    out = object_clusters(clean(claim.get("object")), vocab)
    for obj in claim.get("secondary_objects", []) if isinstance(claim.get("secondary_objects"), list) else []:
        out.update(object_clusters(clean(obj), vocab))
    return out


def _world_reasoning_allowed(claim: dict[str, Any]) -> bool:
    attrs = claim.get("attributes") if isinstance(claim.get("attributes"), dict) else {}
    return attrs.get("world_reasoning", True) is not False


def flatten_claims(active: dict[str, Any], vocab: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, int]]:
    vocab = vocab or load_vocabulary()
    nodes: list[dict[str, Any]] = []
    diag = Counter()
    for collection in WORLD_COLLECTIONS + ("strand_b",):
        rows = active.get(collection, []) if isinstance(active.get(collection), list) else []
        for ri, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            claims = row.get("claims") if isinstance(row.get("claims"), list) else []
            if not claims:
                diag["records_without_claims"] += 1
                continue
            record_id = _record_identity(row, f"{collection}:{ri}")
            decision = clean(row.get("historical_admission_status") if collection == "historical_context" else row.get("admission_status")).lower() or "keep"
            for claim in claims:
                if not isinstance(claim, dict):
                    diag["invalid_claim_objects"] += 1
                    continue
                # Strand B and explicitly world-disabled claims are outside the world
                # reasoning graph by design. Their schema is validated by the claim
                # import/validator pipeline; the reasoning flattener should exclude
                # them before object-vocabulary checks so methods-only vocabulary does
                # not leak into world reasoning.
                if collection == "strand_b" or not _world_reasoning_allowed(claim):
                    diag["methods_or_world_disabled"] += 1
                    continue
                errors = validate_claim(claim, vocab)
                if errors:
                    diag["schema_invalid_claims"] += 1
                    continue
                era = clean(claim.get("era"))
                kind = clean(claim.get("kind"))
                if era == "historical" or collection == "historical_context":
                    primary = False
                    context_weight = DECISION_WEIGHT.get(decision, 0.35)
                elif collection in {"strand_a", "frontier_evidence"}:
                    primary = True
                    context_weight = 1.0
                elif collection == "strand_c":
                    # R-09: only Deep-Scan KEEP event content from C is primary.
                    # Provisional C claims remain context-only even when their sentence
                    # looks like an action/effect; Deep Scan must verify event semantics
                    # before they can fill a world-reasoning role.
                    provisional = bool(claim.get("provisional")) or clean(claim.get("origin")) == "provisional"
                    primary = (not provisional) and decision == "keep" and kind in {"action", "effect"}
                    context_weight = 1.0 if primary else 0.3
                else:
                    primary = False
                    context_weight = 0.3
                node = dict(claim)
                node.update({
                    "_collection": collection,
                    "_record_id": record_id,
                    "_source": _source(row),
                    "_title": clean(row.get("reader_title") or row.get("title") or row.get("headline")),
                    "_deep_main": clean((row.get("deep_analysis") or {}).get("main_finding") if isinstance(row.get("deep_analysis"), dict) else ""),
                    "_link": clean(row.get("link") or row.get("url")),
                    "_decision": decision,
                    "_primary": primary,
                    "_context_weight": context_weight,
                    "_new_this_scan": bool(row.get("new_this_scan")),
                    "_clusters": sorted(claim_clusters(claim, vocab)),
                })
                nodes.append(node)
                diag["primary_claims" if primary else "context_claims"] += 1
    diag["claims_loaded"] = len(nodes)
    return nodes, dict(diag)


def build_distance_table(nodes: Iterable[dict[str, Any]]) -> dict[str, Any]:
    by_record: dict[str, set[str]] = defaultdict(set)
    for n in nodes:
        if clean(n.get("era")) != "current" or n.get("_collection") not in {"strand_a", "frontier_evidence", "strand_c"}:
            continue
        # Distance is corpus co-occurrence, not only primary-role eligibility.
        by_record[clean(n.get("_record_id"))].update(n.get("_clusters") or [])
    by_record = {k: v for k, v in by_record.items() if k and v}
    N = len(by_record)
    counts = Counter(c for clusters in by_record.values() for c in clusters)
    joint = Counter()
    for clusters in by_record.values():
        for a, b in itertools.combinations(sorted(clusters), 2):
            joint[(a, b)] += 1
    pairs: list[dict[str, Any]] = []
    for a, b in itertools.combinations(sorted(counts), 2):
        na, nb = counts[a], counts[b]
        expected = (na * nb / N) if N else 0.0
        j = joint[(a, b)]
        lift = (j / expected) if expected else None
        if lift is None or lift < 1.0:
            distance, bonus = "distant", 1.20
        elif lift < 2.0:
            distance, bonus = "neutral", 1.10
        else:
            distance, bonus = "familiar", 1.00
        pairs.append({"a": a, "b": b, "n_a": na, "n_b": nb, "joint": j, "expected": round(expected, 4), "lift": None if lift is None else round(lift, 4), "distance": distance, "bonus": bonus})
    return {"N": N, "cluster_counts": dict(sorted(counts.items())), "pairs": pairs}


def distance_for(table: dict[str, Any], a: str, b: str) -> tuple[str, float, float | None]:
    if a == b:
        return "familiar", 1.0, None
    x, y = sorted((a, b))
    for p in table.get("pairs", []):
        if p.get("a") == x and p.get("b") == y:
            return clean(p.get("distance")), float(p.get("bonus", 1.0)), p.get("lift")
    return "distant", 1.20, None


def distance_excluding_records(nodes: Iterable[dict[str, Any]], a: str, b: str, excluded_record_ids: set[str]) -> tuple[str, float, float | None]:
    """R-10 distance after removing the candidate chain's own records."""
    if a == b:
        return "familiar", 1.0, None
    by_record: dict[str, set[str]] = defaultdict(set)
    for n in nodes:
        rid = clean(n.get("_record_id"))
        if rid in excluded_record_ids or clean(n.get("era")) != "current" or n.get("_collection") not in {"strand_a", "frontier_evidence", "strand_c"}:
            continue
        by_record[rid].update(n.get("_clusters") or [])
    by_record = {k:v for k,v in by_record.items() if k and v}
    N = len(by_record)
    if not N:
        return "distant", 1.20, None
    na = sum(1 for cs in by_record.values() if a in cs)
    nb = sum(1 for cs in by_record.values() if b in cs)
    joint = sum(1 for cs in by_record.values() if a in cs and b in cs)
    expected = na * nb / N if N else 0.0
    lift = joint / expected if expected else None
    if lift is None or lift < 1.0:
        return "distant", 1.20, None if lift is None else round(lift,4)
    if lift < 2.0:
        return "neutral", 1.10, round(lift,4)
    return "familiar", 1.0, round(lift,4)


def _role_strength(n: dict[str, Any], role: str) -> float:
    merit = max(0.0, min(100.0, float(n.get("merit", 0) or 0))) / 100.0
    kinds = ROLE_KINDS.get(role)
    role_fit = 1.0 if not kinds or clean(n.get("kind")) in kinds else 0.6
    status = STATUS_WEIGHT.get(clean(n.get("status")), 0.0)
    scope = n.get("scope") if isinstance(n.get("scope"), dict) else {}
    countries = scope.get("countries") if isinstance(scope.get("countries"), list) else []
    level = clean(scope.get("level"))
    breadth = 1.0
    if role in {"criterion_a", "criterion_b", "arbitration_gap", "protecting_instrument", "conversion_condition"}:
        if level == "company_in_eu":
            breadth = 0.5
        elif len(countries) == 1:
            breadth = 0.7
    return round(merit * role_fit * status * breadth, 6)


NEGATIVE_DIRECTIONS = {"contracts", "becomes_conditional", "becomes_contested"}


def _direction_compatible(a: str, b: str) -> bool:
    a, b = clean(a), clean(b)
    if a == b:
        return True
    if a in NEGATIVE_DIRECTIONS and b in NEGATIVE_DIRECTIONS:
        return True
    return False


def _role_corroboration_factor(
    selected: dict[str, Any] | None,
    role: str,
    pool: Iterable[dict[str, Any]],
    *,
    semantic_filter: Any = None,
    anchor_objects: set[str] | None = None,
    max_extra_sources: int = 1,
) -> tuple[float, list[str]]:
    """Conservative independent-source corroboration for an already-filled role.

    Corroboration never fills a role.  The supporting claim may be context (R-09)
    because it only raises confidence in a primary role, but it must come from a
    different record and source and overlap an exact object chosen for that role.
    Level-5 worked examples normally use one second source (x1.1); grammars that
    explicitly aggregate more sources, such as split_recurrence side_a, compute
    their own capped factor.
    """
    if not selected or max_extra_sources <= 0:
        return 1.0, []
    selected_source = clean(selected.get("_source")).lower()
    selected_record = clean(selected.get("_record_id"))
    anchors = set(anchor_objects or _claim_objects(selected))
    supporters: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for n in pool:
        if clean(n.get("era")) != "current":
            continue
        if clean(n.get("_record_id")) == selected_record:
            continue
        src = clean(n.get("_source")).lower()
        if not src or src == selected_source or src in seen_sources:
            continue
        if anchors and not (anchors & _claim_objects(n)):
            continue
        if semantic_filter is not None:
            if not semantic_filter(n):
                continue
        else:
            kinds = ROLE_KINDS.get(role)
            if kinds and clean(n.get("kind")) not in kinds:
                continue
            if not _direction_compatible(clean(selected.get("direction")), clean(n.get("direction"))):
                continue
        supporters.append(n)
        seen_sources.add(src)
        if len(supporters) >= max_extra_sources:
            break
    factor = min(1.30, 1.0 + 0.10 * len(supporters))
    return round(factor, 2), [clean(n.get("claim_id")) for n in supporters]


def _role_strength_corrob(
    selected: dict[str, Any] | None,
    role: str,
    pool: Iterable[dict[str, Any]],
    *,
    semantic_filter: Any = None,
    anchor_objects: set[str] | None = None,
    max_extra_sources: int = 1,
) -> tuple[float, float, list[str]]:
    if not selected:
        return 0.0, 1.0, []
    base = _role_strength(selected, role)
    factor, supporters = _role_corroboration_factor(
        selected, role, pool, semantic_filter=semantic_filter,
        anchor_objects=anchor_objects, max_extra_sources=max_extra_sources,
    )
    return round(min(1.0, base * factor), 6), factor, supporters


def _best(nodes: Iterable[dict[str, Any]], role: str) -> dict[str, Any] | None:
    xs = [n for n in nodes if n.get("_primary")]
    if not xs:
        return None
    return max(xs, key=lambda n: (_role_strength(n, role), float(n.get("merit", 0) or 0), clean(n.get("status_date"))))


def _snap(n: dict[str, Any] | None, role: str) -> dict[str, Any] | None:
    if not n:
        return None
    return {
        "claim_id": n.get("claim_id"), "record_key": n.get("record_key"), "role": role,
        "object": n.get("object"), "secondary_objects": n.get("secondary_objects", []),
        "mechanism": n.get("mechanism"), "direction": n.get("direction"), "status": n.get("status"),
        "status_date": n.get("status_date"), "kind": n.get("kind"), "merit": n.get("merit"),
        "source": n.get("_source"), "title": n.get("_title"), "strength": _role_strength(n, role),
    }


LEVEL2_RISK_DIRECTIONS = {"contracts", "becomes_conditional", "becomes_contested"}
LEVEL2_OPPORTUNITY_MECHANISMS = {
    "procures", "builds", "funds", "recruits", "retains", "associates",
    "collaborates", "coordinates", "prioritises", "allocates", "invests",
    "launches", "supports", "fast_tracks", "refers", "feeds_into",
    "integrates", "adds_capacity", "substitutes", "diversifies",
    "harmonises", "exempts", "reconciles", "secures", "pre_clears",
    "standardises", "certifies",
}
LEVEL2_ACTIVE_STATUSES = {
    "proposed", "in_negotiation", "announced", "call_open",
    "adopted", "in_force", "operating",
}


def _level2_product(rows: list[dict[str, Any]], mechanism: str, direction: str) -> tuple[str, str]:
    """R-25 product polarity for a corroborated same-claim group.

    The Level-2 gate is intentionally conservative.  A constraining/contracting
    corroborated claim is retained as a risk.  Expansion becomes an opportunity only
    when the same corroborated mechanism is a concrete instrument/action and at least
    one supporting record puts that instrument into a live or operating status.
    Diagnostic ``assesses expands`` groups remain evidence for trends/other reasoning
    but are not promoted into opportunity cards merely because the direction is
    positive.
    """
    if direction in LEVEL2_RISK_DIRECTIONS:
        return "risk", "corroborated_constraint"

    if direction == "expands" and mechanism in LEVEL2_OPPORTUNITY_MECHANISMS:
        live_actions = [
            r for r in rows
            if clean(r.get("kind")) == "action"
            and clean(r.get("status")) in LEVEL2_ACTIVE_STATUSES
        ]
        if live_actions:
            return "opportunity", "live_or_operating_instrument"

    return "", "not_a_level2_reader_product"


def corroborated_claims(nodes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for n in nodes:
        if not n.get("_primary") or clean(n.get("era")) != "current":
            continue
        groups[(clean(n.get("object")), clean(n.get("mechanism")), clean(n.get("direction")))].append(n)
    out = []
    for key, rows in groups.items():
        sources = {clean(r.get("_source")).lower() for r in rows if clean(r.get("_source"))}
        records = {clean(r.get("_record_id")) for r in rows if clean(r.get("_record_id"))}
        # Broad stock: one grounded record may seed a future risk/opportunity.
        # Independent confirmation raises maturity later; it is not permission to think.
        if not sources or not records:
            continue
        strongest = max(rows, key=lambda r: (float(r.get("merit", 0) or 0), STATUS_RANK.get(clean(r.get("status")), 0)))
        product, product_basis = _level2_product(rows, key[1], key[2])

        # R-25 is a depth gate, not the Level-5 >=80 score gate.  The score below is
        # only an internal evidence-strength tie-breaker for candidates at the same
        # wow level.  It rewards independent sources, record breadth and mature
        # statuses without letting one prestigious source dominate.
        best_by_source: dict[str, dict[str, Any]] = {}
        for row in rows:
            src = clean(row.get("_source")).lower()
            if not src:
                continue
            old = best_by_source.get(src)
            if old is None or float(row.get("merit", 0) or 0) > float(old.get("merit", 0) or 0):
                best_by_source[src] = row
        mean_merit = (sum(float(r.get("merit", 0) or 0) for r in best_by_source.values()) / max(1, len(best_by_source)))
        maturity = max((STATUS_WEIGHT.get(clean(r.get("status")), 0.0) for r in rows), default=0.0)
        evidence_score = min(99, int(round(0.72 * mean_merit + 12 * min(1.0, (len(sources) - 1) / 3) + 15 * maturity)))

        out.append({
            "level": 2,
            "grammar_id": "corroborated_claim",
            "object": key[0],
            "mechanism": key[1],
            "direction": key[2],
            "source_count": len(sources),
            "record_count": len(records),
            "status": strongest.get("status"),
            "claim_ids": sorted({clean(r.get("claim_id")) for r in rows if clean(r.get("claim_id"))}),
            "product": product,
            "product_basis": product_basis,
            "score": evidence_score,
            "score_gate_passes": bool(product),
            # R-13/R-15: ordinary corroborated constraints are the known-worry/new-turn
            # baseline; live constructive instruments are normally the next step.
            "wow_preliminary": 3 if product == "risk" else 2 if product == "opportunity" else 1,
        })
    return sorted(out, key=lambda x: (bool(x.get("product")), x["source_count"], x["record_count"], x["object"]), reverse=True)



def named_continuities(nodes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Level-2 ongoing phenomena: an object with real depth in both eras.

    The original reasoning specification gives ongoing phenomena a deliberately
    broad baseline: a named continuity exists when at least two independent
    historical sources and at least three independent current sources support the
    same controlled object.  This is not a trend direction and not a Level-5 chain;
    it is the persistent stock that lets the continuity product say what keeps
    returning while rarer era-conjunction/split-recurrence findings sit above it.
    """
    current: dict[str, list[dict[str, Any]]] = defaultdict(list)
    historical: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in nodes:
        era = clean(n.get("era"))
        if era == "current" and n.get("_primary"):
            target = current
        elif era == "historical" and clean(n.get("_decision")) == "keep":
            target = historical
        else:
            continue
        for obj in _claim_objects(n):
            if obj and not obj.startswith("methods."):
                target[obj].append(n)

    # Domain-family continuity: a field (e.g. research security) that keeps
    # returning across several related objects.  Requires >=2 member objects in
    # the pooled evidence so it is not a relabelled single-object continuity.
    fam_current: dict[str, list[dict[str, Any]]] = defaultdict(list)
    fam_historical: dict[str, list[dict[str, Any]]] = defaultdict(list)
    fam_members: dict[str, set[str]] = defaultdict(set)
    for src_map, dst_map in ((current, fam_current), (historical, fam_historical)):
        for obj, rows in src_map.items():
            fam = obj.split(".", 1)[0]
            if not fam or fam == obj:
                continue
            key = FAMILY_PREFIX + fam
            seen = {id(r) for r in dst_map[key]}
            dst_map[key].extend(r for r in rows if id(r) not in seen)
            fam_members[key].add(obj)
    scoped: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]] = [
        (obj, current[obj], historical[obj], {}) for obj in sorted(set(current) & set(historical))
    ]
    for key in sorted(set(fam_current) & set(fam_historical)):
        if len(fam_members[key]) < 2:
            continue
        scoped.append((key, fam_current[key], fam_historical[key], {"family_members": sorted(fam_members[key])}))

    out: list[dict[str, Any]] = []
    for obj, cur, hist, extra in scoped:
        cur_sources = {clean(n.get("_source")).lower() for n in cur if clean(n.get("_source"))}
        hist_sources = {clean(n.get("_source")).lower() for n in hist if clean(n.get("_source"))}
        cur_records = {clean(n.get("_record_id")) for n in cur if clean(n.get("_record_id"))}
        hist_records = {clean(n.get("_record_id")) for n in hist if clean(n.get("_record_id"))}
        # Broad stock: continuity begins as soon as both eras are represented.
        # The live selector decides whether breadth is sufficient for reserve/page.
        if len(cur_sources) < 1 or len(hist_sources) < 1:
            continue

        # Evidence strength is only a same-wow ordering device.  Breadth in both
        # eras matters more than one exceptionally prestigious publication.
        evidence_score = min(99, round(35 + 2.0 * min(18, len(cur_sources)) + 1.5 * min(18, len(hist_sources))))
        cur_best = sorted(cur, key=lambda n: (float(n.get("merit", 0) or 0), clean(n.get("status_date"))), reverse=True)[:12]
        hist_best = sorted(hist, key=lambda n: (float(n.get("merit", 0) or 0), clean(n.get("status_date"))), reverse=True)[:8]
        out.append({
            "level": 2,
            "grammar_id": "named_continuity",
            "product": "continuity",
            "object": obj,
            "claim_ids": [clean(n.get("claim_id")) for n in cur_best + hist_best if clean(n.get("claim_id"))],
            "current_record_count": len(cur_records),
            "current_source_count": len(cur_sources),
            "historical_record_count": len(hist_records),
            "historical_source_count": len(hist_sources),
            "score": evidence_score,
            "score_gate_passes": True,
            "wow_preliminary": 1,
            **extra,
        })
    return sorted(
        out,
        key=lambda c: (c["score"], c["current_source_count"], c["historical_source_count"], c["object"]),
        reverse=True,
    )

def _relation_objects(n: dict[str, Any]) -> set[str]:
    return _claim_objects(n)


def _rule_like(n: dict[str, Any]) -> bool:
    """Concrete rule/control claim, not any governance-adjacent action."""
    obj = clean(n.get("object"))
    text = _semantic_text(n)
    mechanism = clean(n.get("mechanism"))
    return (
        any(tok in obj for tok in (".standards", ".certification", ".permitting", "admissibility", "regulation", "screening", "export_control."))
        or mechanism in {"regulates", "standardises", "certifies", "licenses", "screens", "restricts", "conditions", "harmonises", "exempts", "reconciles"}
        or bool(re.search(r"\b(?:permit(?:ting)? rule|licen[cs](?:e|ing)|mandatory screening|admissibility rule|export control|certification rule|technical standard)\b", text))
    )


def _doctrine_like(n: dict[str, Any]) -> bool:
    if clean(n.get("kind")) not in {"action", "advocacy"}:
        return False
    text = _semantic_text(n)
    obj = clean(n.get("object"))
    return bool(
        re.search(r"\b(?:act|regulation|framework|strategy|doctrine|recommendation|guidance|rulebook|policy framework)\b", text)
        or ("governance" in obj and clean(n.get("mechanism")) in {"adopts", "proposes", "prioritises", "standardises", "regulates"})
    )

def _commitment_like(n: dict[str, Any]) -> bool:
    if clean(n.get("kind")) != "action":
        return False
    if clean(n.get("status")) in {"abandoned", "lapsed"}:
        return False
    attrs = n.get("attributes") if isinstance(n.get("attributes"), dict) else {}
    return bool(clean(n.get("deadline")) or clean(attrs.get("construction_window")) or clean(n.get("mechanism")) in {"procures", "builds", "funds", "recruits", "invests", "launches"})


def _success_gap_pairs(current: list[dict[str, Any]]) -> list[tuple[str, str, dict[str, Any]]]:
    """Structural R-24f candidates from explicit two-object current claims.

    The relation claim must actually name both objects.  This deliberately avoids
    guessing programme objectives from topical similarity.
    """
    pairs: list[tuple[str, str, dict[str, Any]]] = []
    for n in current:
        objs = sorted(_claim_objects(n))
        if len(objs) < 2:
            continue
        for a, b in itertools.combinations(objs, 2):
            pairs.append((a, b, n))
    return pairs


def level3_findings(nodes: Iterable[dict[str, Any]], evaluated_on: dt.date) -> list[dict[str, Any]]:
    """R-24 sequence/gap shapes over current primary claims.

    The shadow is conservative: a sequence/gap is emitted only when the claim
    graph itself supplies the relation.  It does not infer a doctrine/tool or
    programme objective from titles alone.
    """
    current = [n for n in nodes if n.get("_primary") and clean(n.get("era")) == "current"]
    by_object: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in current:
        by_object[clean(n.get("object"))].append(n)
    out: list[dict[str, Any]] = []

    # R-24e: stalled proposal.
    for obj, rows in by_object.items():
        for p in rows:
            pd = _date(p.get("status_date"))
            if clean(p.get("status")) != "proposed" or not pd or (evaluated_on - pd).days <= 180:
                continue
            later = [r for r in rows if (_date(r.get("status_date")) or dt.date.min) > pd and STATUS_RANK.get(clean(r.get("status")), 0) > STATUS_RANK["proposed"]]
            if not later:
                out.append({"level": 3, "grammar_id": "stalled_proposal", "object": obj, "proposal_claim_id": p.get("claim_id"), "age_days": (evaluated_on - pd).days})

    # R-24d: goal without measure.
    for obj, rows in by_object.items():
        inv = [r for r in rows if clean(r.get("kind")) in {"advocacy", "action"}]
        meas = [r for r in rows if clean(r.get("kind")) == "effect"]
        if len(inv) >= 12 * max(1, len(meas)) and len(inv) >= 12 and (obj.startswith("goal.") or obj == "goal.strategic_autonomy"):
            out.append({"level": 3, "grammar_id": "goal_without_measure", "object": obj, "invocations": len(inv), "measurements": len(meas), "ratio": None if not meas else round(len(inv) / len(meas), 2)})

    # R-24a: practice before doctrine.  The doctrine must name the practice
    # object structurally through object/secondary_object overlap.
    dated = [n for n in current if _date(n.get("status_date"))]
    for doctrine in dated:
        if not _doctrine_like(doctrine):
            continue
        dd = _date(doctrine.get("status_date"))
        doctrine_objs = _claim_objects(doctrine)
        practices = [
            p for p in dated
            if p is not doctrine and _date(p.get("status_date")) < dd
            and clean(p.get("kind")) == "action"
            and bool(doctrine_objs & _claim_objects(p))
            and not _doctrine_like(p)
        ]
        if not practices:
            continue
        practice = max(practices, key=lambda n: (_date(n.get("status_date")), _role_strength(n, "delivery_instrument")))
        out.append({
            "level": 3, "grammar_id": "practice_before_doctrine", "object": clean(practice.get("object")),
            "practice_claim_id": practice.get("claim_id"), "practice_date": practice.get("status_date"),
            "doctrine_claim_id": doctrine.get("claim_id"), "doctrine_date": doctrine.get("status_date"),
            "relation_mode": "exact_object_overlap",
        })

    # R-24b: deployment before rules.
    for deployment in dated:
        if clean(deployment.get("status")) != "operating" or clean(deployment.get("kind")) != "action" or _rule_like(deployment):
            continue
        dep_date = _date(deployment.get("status_date"))
        dep_objs = _claim_objects(deployment)
        rules = [
            r for r in dated if r is not deployment and _rule_like(r)
            and bool(dep_objs & _claim_objects(r))
            and STATUS_RANK.get(clean(r.get("status")), 0) >= STATUS_RANK["adopted"]
        ]
        if not rules:
            continue
        first_rule = min(rules, key=lambda n: _date(n.get("status_date")))
        if _date(first_rule.get("status_date")) <= dep_date:
            continue
        out.append({
            "level": 3, "grammar_id": "deployment_before_rules", "object": clean(deployment.get("object")),
            "deployment_claim_id": deployment.get("claim_id"), "deployment_date": deployment.get("status_date"),
            "first_adopted_rule_claim_id": first_rule.get("claim_id") if first_rule else None,
            "first_adopted_rule_date": first_rule.get("status_date") if first_rule else None,
        })

    # R-24c: clock before rule.  The commitment's exact-object frontier may
    # carry the rule object (e.g. public compute -> energy -> permitting).
    for commitment in current:
        if not _commitment_like(commitment):
            continue
        attrs = commitment.get("attributes") if isinstance(commitment.get("attributes"), dict) else {}
        deadline = clean(commitment.get("deadline"))
        window = clean(attrs.get("construction_window"))
        if not (deadline or window):
            continue
        frontier, depths = _exact_object_frontier(current, commitment, max_hops=2)
        rule_rows = [r for r in frontier if _rule_like(r) and clean(r.get("claim_id")) != clean(commitment.get("claim_id"))]
        if not rule_rows:
            continue
        adopted = [r for r in rule_rows if STATUS_RANK.get(clean(r.get("status")), 0) >= STATUS_RANK["adopted"] and clean(r.get("status")) not in {"delivered"}]
        if adopted:
            continue
        pending = sorted(rule_rows, key=lambda r: (_role_strength(r, "criterion_b"), -depths.get(clean(r.get("claim_id")), 99)), reverse=True)
        out.append({
            "level": 3, "grammar_id": "clock_before_rule", "object": clean(commitment.get("object")),
            "commitment_claim_id": commitment.get("claim_id"), "deadline": deadline or None,
            "construction_window": window or None,
            "rule_claim_ids": [clean(r.get("claim_id")) for r in pending[:8]],
            "rule_statuses": sorted({clean(r.get("status")) for r in pending}),
            "frontier_mode": "exact_object_overlap", "max_rule_hop": max((depths.get(clean(r.get("claim_id")), 0) for r in pending), default=0),
        })

    # R-24f: success != delivery.  Start from an explicit current claim that
    # names two programme objects.  One side must have action delivery while
    # the other lacks any measured effect.
    seen_gap: set[tuple[str, str]] = set()
    for a, b, relation in _success_gap_pairs(current):
        for objective, delivery in ((a, b), (b, a)):
            key = (objective, delivery)
            if key in seen_gap:
                continue
            objective_rows = [n for n in current if _touches(n, objective)]
            delivery_rows = [n for n in current if _touches(n, delivery)]
            delivery_actions = [n for n in delivery_rows if clean(n.get("kind")) == "action" and STATUS_WEIGHT.get(clean(n.get("status")), 0) > 0]
            objective_effects = [n for n in objective_rows if clean(n.get("kind")) == "effect"]
            objective_conditions = [n for n in objective_rows if clean(n.get("kind")) in {"action", "advocacy", "diagnosis"}]
            if not delivery_actions or objective_effects or not objective_conditions:
                continue
            # R-24f is within one programme: keep the objective and delivery
            # in the same object family, and require the relation claim itself
            # to carry the delivery object as its primary object.
            if objective.split(".", 1)[0] != delivery.split(".", 1)[0]:
                continue
            if clean(relation.get("object")) != delivery:
                continue
            if clean(relation.get("kind")) not in {"action", "advocacy", "diagnosis"}:
                continue
            if not ("retention" in objective or "success" in objective or "outcome" in objective or "performance" in objective or objective.startswith("goal.")):
                continue
            delivery_best = _best(delivery_actions, "delivery_instrument")
            success_best = _best(objective_conditions, "success_condition")
            if not delivery_best or not success_best:
                continue
            out.append({
                "level": 3, "grammar_id": "success_metric_gap", "objective_object": objective,
                "delivery_object": delivery, "success_condition_claim_id": success_best.get("claim_id"),
                "delivery_instrument_claim_id": delivery_best.get("claim_id"),
                "relation_claim_id": relation.get("claim_id"), "measurement_claim_count": 0,
                "relation_mode": "explicit_two_object_claim",
            })
            seen_gap.add(key)

    # Stable de-duplication.
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in out:
        key = (
            item.get("grammar_id"), item.get("object"), item.get("objective_object"), item.get("delivery_object"),
            item.get("proposal_claim_id"), item.get("practice_claim_id"), item.get("deployment_claim_id"), item.get("commitment_claim_id"),
        )
        unique[key] = item
    return sorted(unique.values(), key=lambda x: (clean(x.get("grammar_id")), clean(x.get("object") or x.get("objective_object")), clean(x.get("commitment_claim_id"))))

EXTERNAL_PRESSURE_SCOPES = {"external", "third_country"}
FAMILY_PREFIX = "family:"
CLUSTER_PREFIX = "cluster:"


def opposing_movements(
    nodes: Iterable[dict[str, Any]],
    evaluated_on: dt.date,
    vocab: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """R-50/R-51: keep a living stock of same-object opposing movements.

    Candidate formation is deliberately broader than reader publication:
    any current primary object with at least one independent record pulling toward
    expansion and at least one pulling toward constraint becomes a stock candidate.
    R-51 (>=3 records and >=2 sources on *each* side) is stored separately as the
    reader evidence floor. This prevents the publication floor from erasing the
    reserve/watch stock.

    The object binding follows the specification exactly: a claim contributes to its
    canonical object and its reviewed secondary_objects. We do not invent topic or
    cluster joins. The constraining side includes contracts, becomes_conditional and
    becomes_contested, matching the worked "build capacity vs make capacity
    conditional" example.
    """
    vocab = vocab or {}
    eligible_scopes = {"eu", "member_state", "associated_country", "company_in_eu"}
    by_object_side: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for n in nodes:
        if not n.get("_primary") or clean(n.get("era")) != "current":
            continue
        scope = n.get("scope") if isinstance(n.get("scope"), dict) else {}
        level = clean(scope.get("level"))
        if level not in eligible_scopes and level not in EXTERNAL_PRESSURE_SCOPES:
            continue
        d = _date(n.get("status_date"))
        if d and (evaluated_on - d).days > 180:
            continue

        direction = clean(n.get("direction"))
        if direction == "expands":
            side = "expands"
        elif direction in {"contracts", "becomes_conditional", "becomes_contested"}:
            side = "constrains"
        else:
            continue
        # Non-European actors can only press on a European object from outside:
        # an external constraint is a legitimate counter-pull, but an external
        # expansion is not evidence that Europe's own side is moving.
        if level in EXTERNAL_PRESSURE_SCOPES and side != "constrains":
            continue

        for obj in _claim_objects(n):
            if obj:
                by_object_side[(obj, side)].append(n)

    def record_ids(rows: list[dict[str, Any]]) -> set[str]:
        return {clean(r.get("_record_id")) for r in rows if clean(r.get("_record_id"))}

    def source_ids(rows: list[dict[str, Any]]) -> set[str]:
        return {clean(r.get("_source")).lower() for r in rows if clean(r.get("_source"))}

    def weighted(rows: list[dict[str, Any]]) -> float:
        # One record gets one vote on a side even when Deep Scan emitted several
        # claims naming the same object.
        by_record: dict[str, dict[str, Any]] = {}
        for r in rows:
            rid = clean(r.get("_record_id"))
            old = by_record.get(rid)
            if old is None or float(r.get("merit", 0) or 0) > float(old.get("merit", 0) or 0):
                by_record[rid] = r
        per_source = Counter()
        total = 0.0
        for r in sorted(by_record.values(), key=lambda x: clean(x.get("status_date")), reverse=True):
            src = clean(r.get("_source")).lower()
            per_source[src] += 1
            independence = 1.0 / (2 ** (per_source[src] - 1))
            d = _date(r.get("status_date"))
            age = (evaluated_on - d).days if d else 999
            freshness = 1.0 if age <= 90 else 0.85 if age <= 180 else 0.70
            attrs = r.get("attributes") if isinstance(r.get("attributes"), dict) else {}
            actor = r.get("actor") if isinstance(r.get("actor"), dict) else {}
            witness = (
                1.2
                if attrs.get("hostile_witness") is True
                and clean(actor.get("class")) in {"eu_body", "member_state", "national_funder"}
                else 1.0
            )
            corroboration = min(1.3, max(1.0, float(attrs.get("corroboration_factor", 1.0) or 1.0)))
            total += (
                (float(r.get("merit", 0) or 0) / 100.0)
                * KIND_WEIGHT.get(clean(r.get("kind")), 0.5)
                * STATUS_WEIGHT.get(clean(r.get("status")), 0.0)
                * independence
                * freshness
                * witness
                * corroboration
            )
        return round(total, 4)

    # Domain-family scope: pool the pulls of every object sharing a prefix.  A
    # family trend is only formed when its pulls come from at least two distinct
    # member objects, so it never merely duplicates a single-object trend.
    by_family_side: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    family_members: dict[str, set[str]] = defaultdict(set)
    family_side_objects: dict[tuple[str, str], set[str]] = defaultdict(set)
    for (obj, side), rows in by_object_side.items():
        fam = obj.split(".", 1)[0]
        if not fam or fam == obj or fam == "methods":
            continue
        key = FAMILY_PREFIX + fam
        seen = {id(r) for r in by_family_side[(key, side)]}
        by_family_side[(key, side)].extend(r for r in rows if id(r) not in seen)
        family_members[key].add(obj)
        family_side_objects[(key, side)].add(obj)

    # Reviewed vocabulary clusters can cut across prefixes.  Keep a cluster only
    # when its contributing objects are not already an identical prefix family.
    object_meta = vocab.get("objects") if isinstance(vocab.get("objects"), dict) else {}
    for (obj, side), rows in by_object_side.items():
        meta = object_meta.get(obj) if isinstance(object_meta.get(obj), dict) else {}
        cluster = clean(meta.get("cluster"))
        if not cluster or cluster == "methods":
            continue
        key = CLUSTER_PREFIX + cluster
        seen = {id(r) for r in by_family_side[(key, side)]}
        by_family_side[(key, side)].extend(r for r in rows if id(r) not in seen)
        family_members[key].add(obj)
        family_side_objects[(key, side)].add(obj)
    prefix_sets = {frozenset(v) for k, v in family_members.items() if k.startswith(FAMILY_PREFIX)}
    for key in [k for k in family_members if k.startswith(CLUSTER_PREFIX)]:
        if frozenset(family_members[key]) in prefix_sets:
            del family_members[key]

    scopes: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]] = []
    for obj in sorted({obj for obj, _ in by_object_side}):
        scopes.append((obj, by_object_side[(obj, "expands")], by_object_side[(obj, "constrains")], {}))
    for key in sorted(family_members):
        if len(family_members[key]) < 2:
            continue
        if len(family_side_objects[(key, "expands")] | family_side_objects[(key, "constrains")]) < 2:
            continue
        scopes.append((key, by_family_side[(key, "expands")], by_family_side[(key, "constrains")], {
            "trend_scope": "cluster" if key.startswith(CLUSTER_PREFIX) else "family",
            "family_members": sorted(family_members[key]),
        }))

    out: list[dict[str, Any]] = []
    for obj, left0, right0, extra in scopes:

        # R-53: if one record carries both pulls on the object, treat it as context
        # rather than letting it vote twice.
        ambiguous = record_ids(left0) & record_ids(right0)
        left = [r for r in left0 if clean(r.get("_record_id")) not in ambiguous]
        right = [r for r in right0 if clean(r.get("_record_id")) not in ambiguous]

        lrecords, rrecords = record_ids(left), record_ids(right)
        if not lrecords or not rrecords:
            continue
        lsources, rsources = source_ids(left), source_ids(right)
        floor = (
            len(lrecords) >= 3
            and len(rrecords) >= 3
            and len(lsources) >= 2
            and len(rsources) >= 2
        )
        lw, rw = weighted(left), weighted(right)
        total = lw + rw
        pull = None if total <= 0 else round(100 * lw / total, 1)
        out.append(
            {
                "level": 4,
                "grammar_id": "opposing_movements",
                "trend_scope": "object",
                "object": obj,
                "expands_records": len(lrecords),
                "contracts_records": len(rrecords),  # compatibility key: right/constraining side
                "expands_sources": len(lsources),
                "contracts_sources": len(rsources),
                "expands_weight": lw,
                "contracts_weight": rw,
                "expands_pull_preliminary": pull,
                "trend_stock_passes": True,
                "trend_evidence_floor_passes": floor,
                "score_gate_passes": floor,
                "right_directions": ["contracts", "becomes_conditional", "becomes_contested"],
                "note": "Claim-native trend stock; R-51 is a reader floor, not a candidate-formation floor.",
                **extra,
            }
        )
    return out


def _touches(n: dict[str, Any], obj: str) -> bool:
    return clean(n.get("object")) == obj or obj in [clean(x) for x in (n.get("secondary_objects") or [])]


def _distinct_sources(rows: Iterable[dict[str, Any]]) -> int:
    return len({clean(r.get("_source")).lower() for r in rows if clean(r.get("_source"))})


def _claim_objects(n: dict[str, Any]) -> set[str]:
    out = {clean(n.get("object"))}
    out.update(clean(x) for x in (n.get("secondary_objects") or []) if clean(x))
    return {x for x in out if x}


def _exact_object_frontier(primary: list[dict[str, Any]], seed: dict[str, Any], max_hops: int = 3) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """R-31 frontier: expand by exact object/secondary_object overlap, never cluster-only joins."""
    by_object: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in primary:
        for obj in _claim_objects(n):
            by_object[obj].append(n)
    seen_claims = {clean(seed.get("claim_id"))}
    seen_records = {clean(seed.get("_record_id"))}
    frontier: list[dict[str, Any]] = []
    depths: dict[str, int] = {}
    wave_objects = set(_claim_objects(seed))
    seen_objects = set(wave_objects)
    for hop in range(1, max_hops + 1):
        next_objects: set[str] = set()
        for obj in sorted(wave_objects):
            for n in by_object.get(obj, []):
                cid = clean(n.get("claim_id"))
                rid = clean(n.get("_record_id"))
                if cid in seen_claims or rid in seen_records:
                    continue
                seen_claims.add(cid)
                frontier.append(n)
                depths[cid] = hop
                next_objects.update(_claim_objects(n))
        next_objects -= seen_objects
        if not next_objects:
            break
        seen_objects.update(next_objects)
        wave_objects = next_objects
    return frontier, depths


def _best_excluding(nodes: Iterable[dict[str, Any]], role: str, excluded_claim_ids: set[str] | None = None) -> dict[str, Any] | None:
    excluded_claim_ids = excluded_claim_ids or set()
    xs = [n for n in nodes if n.get("_primary") and clean(n.get("claim_id")) not in excluded_claim_ids]
    if not xs:
        return None
    return max(xs, key=lambda n: (_role_strength(n, role), float(n.get("merit", 0) or 0), clean(n.get("status_date"))))


def _criterion_eligible(n: dict[str, Any]) -> bool:
    """A-2: criteria are actions, or diagnoses of rules that are already adopted/in force/operating."""
    kind = clean(n.get("kind"))
    if kind == "action":
        return True
    return kind == "diagnosis" and clean(n.get("status")) in {"adopted", "in_force", "operating"}


def _semantic_text(n: dict[str, Any]) -> str:
    return " ".join(clean(n.get(k)) for k in ("_title", "text", "_deep_main", "qualification") if clean(n.get(k))).lower()


_PROPAGATION_CUE = re.compile(r"\b(?:spread(?:ing|s)?|across|multiple|several|more than one|regions?|sites?|locations?|geograph(?:y|ic|ically)|network(?:-wide)?|system(?:-wide)?|europe(?:an|-wide)?\s+(?:regions?|sites?|data centres?|facilities|markets))\b", re.I)
_EXPOSURE_CUE = re.compile(r"\b(?:scarci(?:ty|ties)|shortage|bottleneck|limited|concentrat(?:ed|ion)|dependen(?:t|ce|cy)|single[- ]supplier|fragil(?:e|ity)|vulnerab(?:le|ility)|expos(?:ed|ure)|insufficient|capacity gap|supply gap|constraint|constrained|lack of|shortfall)\b", re.I)


def _propagation_eligible(n: dict[str, Any], dependency_object: str) -> bool:
    """R-32 propagation: the dependency disruption reaches more than one site/context."""
    if not _touches(n, dependency_object):
        return False
    if clean(n.get("kind")) not in {"effect", "diagnosis"}:
        return False
    if clean(n.get("direction")) not in {"contracts", "becomes_conditional", "becomes_contested"}:
        return False
    return bool(_PROPAGATION_CUE.search(_semantic_text(n)))


def _exposure_eligible(n: dict[str, Any], capability_objects: set[str]) -> bool:
    """R-32 exposure: evidence of why the capability is vulnerable (scarcity/concentration/dependence)."""
    if not (_claim_objects(n) & capability_objects):
        return False
    if clean(n.get("kind")) not in {"diagnosis", "effect"}:
        return False
    if clean(n.get("direction")) not in {"contracts", "becomes_conditional", "becomes_contested"}:
        return False
    return bool(_EXPOSURE_CUE.search(_semantic_text(n)))


def _trigger_eligible(n: dict[str, Any]) -> bool:
    """R-41: an evidenced event/proposal/rule, not a delivered analytical statement, turns a pathway into risk."""
    if clean(n.get("mechanism")) not in RESTRICTION_MECHANISMS:
        return False
    status = clean(n.get("status"))
    if status in {"abandoned", "lapsed", "delivered", ""}:
        return False
    kind = clean(n.get("kind"))
    return kind == "action" or (kind == "diagnosis" and status in {"adopted", "in_force", "operating"})


def _trigger_maturity_key(n: dict[str, Any]) -> tuple[int, float, str]:
    return (STATUS_RANK.get(clean(n.get("status")), 0), float(n.get("merit", 0) or 0), clean(n.get("status_date")))



def _shock_driver_basis(dep_obj: str, support_nodes: Iterable[dict[str, Any]], vocab: dict[str, Any]) -> tuple[bool, str]:
    """Return whether an untriggered dependency is genuinely shock-shaped.

    "No trigger in the corpus" is necessary for a shock but not sufficient.  The
    earlier implementation classified every triggerless dependency pathway as a
    shock, which produced internal policy couplings such as talent retention ×
    public support.  R-40/R-41 require a discontinuity mechanism: an external
    driver, or a narrow class of abrupt control/input mechanisms capable of a
    sudden European-system flip.
    """
    dep_obj = clean(dep_obj)
    cluster = primary_cluster(dep_obj, vocab)
    rows = list(support_nodes)
    external_rows = []
    for n in rows:
        actor = n.get("actor") if isinstance(n.get("actor"), dict) else {}
        scope = n.get("scope") if isinstance(n.get("scope"), dict) else {}
        if (clean(actor.get("class")) == "third_country" or clean(scope.get("level")) in {"external", "third_country"}) and _touches(n, dep_obj):
            external_rows.append(n)

    if dep_obj.startswith(("finance.us_", "finance.gulf_", "eu_entities.export_access")):
        return True, "explicit_external_dependency_object"
    if dep_obj.startswith("export_control."):
        return True, "abrupt_control_mechanism"
    if dep_obj == "materials.critical_raw":
        return True, "critical_input_disruption"
    if external_rows and cluster in {
        "capital_markets", "materials_energy", "talent", "digital_governance",
        "cybersecurity", "critical_infrastructure", "chips", "compute_ai",
        "research_infrastructure", "health",
    }:
        return True, "external_actor_or_scope"
    return False, "no_discontinuity_driver"


# Future-shock scenario operators.  These are not publication detections and do not
# bypass evidence authority.  They are a compact foresight grammar used to cross an
# evidenced European asset with an evidenced disruption mechanism so the reasoning
# corpus can contain hypotheses before every causal link has already happened.

# Additional disruption families for R&I geopolitics (added with the creative
# reserve).  Each is an abrupt, externally driven change that can knock out a
# European research capability, not a slow trend.
_EXTRA_PRESSURE_REGEX: dict[str, str] = {
    "funding_cut": r"\b(?:budget cuts?|funding cuts?|cut (?:the )?(?:budget|funding)|funding (?:gap|freeze|squeeze|shortfall)|frozen funding|freez\w* (?:grants?|funding)|spending cuts?|austerity|against higher (?:total )?(?:eu )?spending|unfinanced|success rate fell)\b",
    "talent_flight": r"\b(?:brain drain|talent (?:flight|loss|drain)|researchers? (?:leave|leaving|exodus|emigrat)\w*|visa (?:restriction|ban|rules?)|travel ban|poach\w*|mobility barriers?|refused admissions?)\b",
    "political_shift": r"\b(?:election|populis\w*|nationalis\w*|government change|academic freedom|rule of law|exclusion from horizon|horizon exclusion|excluded from horizon|political (?:interference|pressure|shift))\b",
    "regulatory_shift": r"\b(?:court (?:ruling|referral|decision)|cjeu|new (?:regulation|law|act)|proposed the eu [a-z ]+ act|ai act|kids act|gdpr|repeal and replace|regulatory (?:change|shock|burden)|compliance burden)\b",
    "tech_leap": r"\b(?:agi|capability shocks?|frontier (?:ai|model)s?|breakthrough|quantum advantage|leapfrog\w*|technological (?:lead|leap|dominance)|closing (?:hardware )?gaps|chinese dominance|rapid[- ]capability)\b",
    "info_manipulation": r"\b(?:disinformation|information manipulation|foreign (?:information )?interference|influence operations?|propaganda)\b",
    "chokepoint": r"\b(?:chokepoints?|bottlenecks?|single (?:point of failure|supplier|source)|dependen\w* on (?:us|u\.s\.|american|chinese|foreign) (?:cloud|providers?|suppliers?|technology)|lock[- ]in)\b",
    "hazard": r"\b(?:extreme weather|climate (?:risk|hazard|shock)s?|heatwaves?|floods?|wildfires?|drought|pandemic|outbreak)\b",
}

_SHOCK_PRESSURE_PATTERNS: dict[str, re.Pattern[str]] = {
    "export_control": re.compile(r"\b(?:export controls?|export restrictions?|export ban|dual[- ]use licensing|technology restriction)\b", re.I),
    "critical_input": re.compile(r"\b(?:critical raw material|critical mineral|rare earth|material constraints?|supply shortage|single supplier|import dependence)\b", re.I),
    "security_reclassification": re.compile(r"\b(?:research security|knowledge security|dual[- ]use|sensitive research|biosecurity|foreign interference)\b", re.I),
    "acquisition": re.compile(r"\b(?:foreign acquisition|foreign ownership|takeover|investment screening)\b", re.I),
    "conflict": re.compile(r"\b(?:armed conflict|war|invasion|military escalation|geopolitical conflict)\b", re.I),
    "sanctions": re.compile(r"\b(?:sanctions?|asset freeze|payment restriction|financial restriction)\b", re.I),
    "data_access": re.compile(r"\b(?:data access restriction|data transfer restriction|cross[- ]border data|data localisation|data localization)\b", re.I),
    "cyber": re.compile(r"\b(?:cyberattack|cyber attack|ransomware|cybersecurity risk|software vulnerab|digital outage|rogue ai agents?)\b", re.I),
    "energy": re.compile(r"\b(?:energy supply|electricity shortage|power outage|energy crisis|grid constraint|electricity rationing|power supply|energy models?)\b", re.I),
    "commercial": re.compile(r"\b(?:repricing|vendor lock|market withdrawal|service withdrawal|commercial provider|proprietary database|licen[cs]e restriction)\b", re.I),
    "external_finance": re.compile(r"\b(?:hyperscaler debt|gulf capital|external finance|foreign capital)\b", re.I),
}
_SHOCK_PRESSURE_PATTERNS.update({k: re.compile(v, re.I) for k, v in _EXTRA_PRESSURE_REGEX.items()})

_SHOCK_PRESSURE_LABELS = {
    "funding_cut": "a sudden funding cut",
    "talent_flight": "a sudden loss of researchers",
    "political_shift": "a political shift",
    "regulatory_shift": "an abrupt rule change",
    "tech_leap": "a rival technology leap",
    "info_manipulation": "a foreign information campaign",
    "chokepoint": "a supply chokepoint",
    "hazard": "a climate or health emergency",
    "export_control": "external export controls",
    "critical_input": "a critical-input shortage",
    "security_reclassification": "a sudden security reclassification",
    "acquisition": "a foreign acquisition",
    "conflict": "an external conflict escalation",
    "sanctions": "sanctions or payment restrictions",
    "data_access": "a cross-border data restriction",
    "cyber": "a cyber outage",
    "energy": "an abrupt power constraint",
    "commercial": "a provider withdrawal or repricing",
    "external_finance": "an abrupt withdrawal of external finance",
}

# Strongly plausible asset-family × disruption-family combinations.  Other broadly
# applicable pressures can still seed a hypothesis at lower mechanism confidence,
# but clearly nonsensical combinations are excluded below.
_SHOCK_STRONG_COMPAT: dict[str, set[str]] = {
    "compute_ai": {"export_control", "critical_input", "cyber", "energy", "commercial", "sanctions", "acquisition", "data_access", "external_finance", "security_reclassification"},
    "chips": {"export_control", "critical_input", "cyber", "energy", "commercial", "sanctions", "acquisition", "security_reclassification"},
    "quantum": {"export_control", "critical_input", "cyber", "sanctions", "conflict", "data_access", "security_reclassification", "acquisition"},
    "research_infrastructure": {"cyber", "energy", "commercial", "sanctions", "conflict", "data_access", "critical_input", "security_reclassification"},
    "health": {"data_access", "cyber", "sanctions", "conflict", "commercial", "security_reclassification", "acquisition"},
    "talent": {"conflict", "sanctions", "security_reclassification", "data_access"},
    "funding_programme": {"conflict", "sanctions", "security_reclassification", "data_access"},
    "defence_dual_use": {"export_control", "critical_input", "cyber", "conflict", "sanctions", "security_reclassification"},
    "critical_infrastructure": {"cyber", "energy", "critical_input", "conflict", "sanctions", "commercial"},
    "capital_markets": {"acquisition", "sanctions", "conflict", "commercial", "external_finance"},
    "digital_governance": {"cyber", "data_access", "commercial", "sanctions", "security_reclassification"},
    "cybersecurity": {"cyber", "commercial", "conflict", "sanctions"},
    "industrial_competitiveness": {"export_control", "critical_input", "energy", "commercial", "acquisition", "sanctions"},
    "materials_energy": {"export_control", "conflict", "sanctions", "commercial", "energy"},
    "research_system": {"conflict", "sanctions", "security_reclassification", "data_access", "cyber"},
    "innovation_ecosystem": {"acquisition", "commercial", "external_finance", "sanctions", "conflict"},
    "ai_governance": {"cyber", "data_access", "security_reclassification", "export_control"},
}

_SHOCK_WEAK_COMPAT: dict[str, set[str]] = {
    "compute_ai": {"conflict"},
    "chips": {"conflict", "data_access"},
    "quantum": {"energy", "commercial"},
    "research_infrastructure": {"acquisition"},
    "health": {"critical_input", "energy"},
    "talent": {"commercial"},
    "funding_programme": {"commercial", "cyber"},
    "defence_dual_use": {"commercial", "acquisition", "energy"},
    "critical_infrastructure": {"acquisition", "data_access"},
    "capital_markets": {"cyber", "data_access", "security_reclassification"},
    "digital_governance": {"export_control", "acquisition"},
    "cybersecurity": {"acquisition", "export_control"},
    "industrial_competitiveness": {"cyber", "conflict"},
    "materials_energy": {"cyber", "acquisition"},
    "research_system": {"commercial", "cyber"},
    "innovation_ecosystem": {"cyber", "security_reclassification", "data_access", "export_control"},
    "ai_governance": {"commercial", "sanctions", "conflict"},
}

# Strong pairs that are already conceptually close enough to be relatively obvious
# even before the corpus contains a direct bridge.  This helps the wow ladder span
# from familiar/obvious (1) to genuinely distant (5) without using evidence strength
# as a proxy for novelty.
_SHOCK_CLOSE_COMPAT: dict[str, set[str]] = {
    "compute_ai": {"energy", "export_control", "cyber"},
    "chips": {"export_control", "critical_input"},
    "quantum": {"export_control", "security_reclassification"},
    "research_infrastructure": {"cyber", "energy"},
    "health": {"data_access", "cyber"},
    "talent": {"conflict", "sanctions"},
    "funding_programme": {"conflict", "sanctions"},
    "defence_dual_use": {"export_control", "security_reclassification", "critical_input"},
    "critical_infrastructure": {"cyber", "energy"},
    "capital_markets": {"acquisition"},
    "digital_governance": {"data_access", "cyber"},
    "cybersecurity": {"cyber"},
    "industrial_competitiveness": {"critical_input", "energy"},
    "materials_energy": {"export_control", "energy"},
    "research_system": {"security_reclassification"},
    "innovation_ecosystem": {"acquisition", "commercial"},
    "ai_governance": {"data_access", "security_reclassification"},
}


# Wire the additional disruption families into the compatibility maps.
for _pid, _clusters in {'funding_cut': ['funding_programme', 'research_system', 'research_infrastructure', 'talent', 'health', 'quantum', 'innovation_ecosystem'], 'talent_flight': ['talent', 'research_system', 'research_infrastructure', 'quantum', 'compute_ai', 'health'], 'political_shift': ['funding_programme', 'research_system', 'talent', 'digital_governance', 'ai_governance'], 'regulatory_shift': ['ai_governance', 'digital_governance', 'health', 'compute_ai', 'capital_markets', 'innovation_ecosystem'], 'tech_leap': ['compute_ai', 'chips', 'quantum', 'industrial_competitiveness', 'defence_dual_use', 'ai_governance'], 'info_manipulation': ['digital_governance', 'cybersecurity', 'ai_governance', 'research_system'], 'chokepoint': ['compute_ai', 'chips', 'digital_governance', 'critical_infrastructure', 'industrial_competitiveness', 'materials_energy', 'health'], 'hazard': ['research_infrastructure', 'critical_infrastructure', 'materials_energy', 'health']}.items():
    for _cl in _clusters:
        _SHOCK_STRONG_COMPAT.setdefault(_cl, set()).add(_pid)
for _pid, _clusters in {'funding_cut': ['compute_ai', 'defence_dual_use'], 'talent_flight': ['innovation_ecosystem', 'chips'], 'political_shift': ['research_infrastructure', 'health'], 'regulatory_shift': ['research_system', 'chips'], 'tech_leap': ['innovation_ecosystem', 'research_system'], 'info_manipulation': ['health', 'funding_programme'], 'chokepoint': ['quantum', 'research_infrastructure'], 'hazard': ['compute_ai']}.items():
    for _cl in _clusters:
        _SHOCK_WEAK_COMPAT.setdefault(_cl, set()).add(_pid)
for _pid, _clusters in {'funding_cut': ['funding_programme'], 'talent_flight': ['talent'], 'political_shift': ['funding_programme'], 'regulatory_shift': ['ai_governance', 'digital_governance'], 'tech_leap': ['compute_ai', 'quantum'], 'info_manipulation': ['digital_governance'], 'chokepoint': ['chips', 'compute_ai'], 'hazard': ['research_infrastructure']}.items():
    for _cl in _clusters:
        _SHOCK_CLOSE_COMPAT.setdefault(_cl, set()).add(_pid)


def _shock_pressure_classes(n: dict[str, Any]) -> set[str]:
    text = _semantic_text(n)
    objs = _claim_objects(n)
    out = {pid for pid, rx in _SHOCK_PRESSURE_PATTERNS.items() if rx.search(text)}
    if any(o.startswith("export_control.") or o == "eu_entities.export_access" for o in objs):
        out.add("export_control")
    if "materials.critical_raw" in objs:
        out.add("critical_input")
    if any(o in {"energy.grid", "datacentre.energy_supply"} for o in objs):
        out.add("energy")
    if any(o.startswith("finance.us_") or o == "finance.gulf_capital" for o in objs):
        out.add("external_finance")
    return out


def exploratory_shock_hypotheses(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a broad evidence-grounded shock corpus before full causal proof exists.

    Candidate formation is intentionally easier than publication verification.  A
    current European capability/flagship/budget plus a separately evidenced abrupt
    disruption class is enough to seed a hypothesis.  A direct record connecting the
    two is an optional bridge that raises maturity; its absence leaves a support query
    rather than deleting the possible future.
    """
    all_nodes = list(nodes)
    primary = [n for n in all_nodes if n.get("_primary") and clean(n.get("era")) == "current"]
    object_meta = vocab.get("objects") or {}

    # Pick the strongest current anchor for each concrete European asset.  Rules and
    # broad policy goals are not treated as assets that can be physically/operationally
    # knocked out; they can still appear elsewhere in risk reasoning.
    asset_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in primary:
        for obj in _claim_objects(n):
            meta = object_meta.get(obj, {}) if isinstance(object_meta.get(obj, {}), dict) else {}
            if clean(meta.get("stake_class")) not in {"flagship", "capability", "budget"}:
                continue
            asset_rows[obj].append(n)

    # Current primary evidence establishes that the disruption mechanism is a real
    # thing in the Radar's evidence base; it need not already be acting on this asset.
    pressure_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in primary:
        for pid in _shock_pressure_classes(n):
            pressure_rows[pid].append(n)

    def anchor_rank(n: dict[str, Any]) -> tuple[int, int, float, str]:
        return (
            1 if clean(n.get("kind")) == "action" else 0,
            STATUS_RANK.get(clean(n.get("status")), 0),
            float(n.get("merit", 0) or 0),
            clean(n.get("status_date")),
        )

    # Record-level pressure classes across both eras are used only to measure how
    # familiar the asset-pressure pairing already is (wow), not as primary support.
    record_objects: dict[str, set[str]] = defaultdict(set)
    record_pressures: dict[str, set[str]] = defaultdict(set)
    for n in all_nodes:
        rid = clean(n.get("_record_id"))
        if not rid:
            continue
        record_objects[rid].update(_claim_objects(n))
        record_pressures[rid].update(_shock_pressure_classes(n))

    out: list[dict[str, Any]] = []
    for asset_obj, rows in asset_rows.items():
        meta = object_meta.get(asset_obj, {}) if isinstance(object_meta.get(asset_obj, {}), dict) else {}
        cluster = clean(meta.get("cluster"))
        if not cluster:
            continue
        asset = max(rows, key=anchor_rank)
        asset_rid = clean(asset.get("_record_id"))
        asset_src = _source(asset).lower()
        strong = _SHOCK_STRONG_COMPAT.get(cluster, set())

        for pid, prows in pressure_rows.items():
            weak = _SHOCK_WEAK_COMPAT.get(cluster, set())
            compat = 2 if pid in strong else 1 if pid in weak else 0
            if compat == 0:
                continue
            # Foreign acquisition is nonsensical for programme budgets/talent; data
            # restrictions and material/energy shocks are similarly domain-bound.
            if pid == "acquisition" and cluster not in {"compute_ai", "chips", "quantum", "health", "capital_markets", "critical_infrastructure", "research_infrastructure", "innovation_ecosystem", "industrial_competitiveness"}:
                continue
            candidates = [n for n in prows if clean(n.get("_record_id")) != asset_rid]
            if not candidates:
                continue
            # Prefer a driver whose own statement visibly shows the disruption, then
            # one that also names this asset (an already-moving, obvious shock), then
            # source independence and strength.  A tagged-but-silent record can only
            # be used when nothing better exists; publication will then hold it back.
            from scripts.claim_reasoning_live import _shock_driver_is_reader_grounded as _grounded_driver
            pressure = max(candidates, key=lambda n: (
                1 if _grounded_driver(pid, n.get("text")) else 0,
                1 if asset_obj in _claim_objects(n) else 0,
                1 if _source(n).lower() != asset_src else 0,
                anchor_rank(n),
            ))
            pressure_rid = clean(pressure.get("_record_id"))

            # Optional direct bridge: any separate current primary record that both
            # names the asset and contains this disruption class.
            bridge_rows = [
                n for n in primary
                if clean(n.get("_record_id")) not in {asset_rid, pressure_rid}
                and asset_obj in _claim_objects(n) and pid in _shock_pressure_classes(n)
            ]
            bridge = max(bridge_rows, key=anchor_rank) if bridge_rows else None

            joint = sum(1 for rid, objs in record_objects.items() if asset_obj in objs and pid in record_pressures.get(rid, set()))
            if joint >= 2:
                wow = 1
            elif joint == 1:
                wow = 2
            elif compat == 2 and pid in _SHOCK_CLOSE_COMPAT.get(cluster, set()):
                wow = 3
            elif compat == 2:
                wow = 4
            else:
                wow = 5

            roles = {
                "commitment": _snap(asset, "commitment"),
                "external_driver": _snap(pressure, "external_driver"),
                "bridge": _snap(bridge, "bridge") if bridge else None,
            }
            missing = ["bridge"] if bridge is None else []
            strengths = [
                _role_strength(asset, "commitment"),
                max(0.40, (float(pressure.get("merit", 0) or 0) / 100.0) * KIND_WEIGHT.get(clean(pressure.get("kind")), 0.7)),
            ]
            if bridge:
                strengths.append(max(0.40, float(bridge.get("merit", 0) or 0) / 100.0))
            score = round(100 * (sum(strengths) / len(strengths)) * (1.0 if compat == 2 else 0.88))
            out.append({
                "level": 5 if wow >= 4 else 4 if wow == 3 else 3,
                "grammar_id": "future_shock_hypothesis",
                "product": "shock",
                "capability_object": asset_obj,
                "dependency_object": pid,
                "endpoint_objects": [asset_obj, f"shock_pressure.{pid}"],
                "pressure_id": pid,
                "pressure_label": _SHOCK_PRESSURE_LABELS[pid],
                "shock_driver": True,
                "shock_driver_basis": f"scenario_operator:{pid}",
                "roles": roles,
                "missing_roles": missing,
                "score": max(0, min(99, score)),
                "floor_ok": True,
                "wow_preliminary": wow,
                "pair_joint_records": joint,
                "compatibility_strength": compat,
                "score_gate_passes": bool(bridge and score >= 60),
                "publication_gate_passes": False,
            })

    # Stable de-duplication by asset × disruption family.  Keep broad stock large but
    # bounded enough for deterministic scans.
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for c in out:
        key = (clean(c.get("capability_object")), clean(c.get("pressure_id")))
        old = best.get(key)
        if old is None or (int(c.get("score", 0)), -len(c.get("missing_roles", []))) > (int(old.get("score", 0)), -len(old.get("missing_roles", []))):
            best[key] = c
    return sorted(best.values(), key=lambda c: (int(c.get("wow_preliminary", 0)), int(c.get("score", 0))), reverse=True)[:240]

def dependency_pathways(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any], distance: dict[str, Any]) -> list[dict[str, Any]]:
    """Fit the R-32 dependency pathway over exact-object frontiers.

    Stage 5C deliberately separates the four scored roles from the trigger. A
    multi-object coupling names the dependency; propagation must show that same
    dependency spreading across sites/contexts; exposure must describe a
    vulnerability on the capability side; and a mature restriction anywhere on
    the connected dependency branch becomes the trigger that classifies the
    pathway as risk. This prevents generic diagnoses elsewhere in a broad
    cluster from filling load-bearing roles.
    """
    primary = [n for n in nodes if n.get("_primary") and clean(n.get("era")) == "current"]
    commitments = []
    for n in primary:
        stake_classes = {
            (vocab.get("objects") or {}).get(o, {}).get("stake_class")
            for o in _claim_objects(n)
            if isinstance((vocab.get("objects") or {}).get(o, {}), dict)
        }
        if clean(n.get("kind")) == "action" and clean(n.get("direction")) == "expands" and stake_classes & {"flagship", "capability", "budget", "rule"}:
            commitments.append(n)

    out: list[dict[str, Any]] = []
    for commitment in commitments:
        cap_obj = clean(commitment.get("object"))
        cap_objects = _claim_objects(commitment)
        cap_primary_cluster = primary_cluster(cap_obj, vocab)
        frontier, hop_depths = _exact_object_frontier(primary, commitment, max_hops=3)

        coupling_options: list[tuple[dict[str, Any], str]] = []
        for n in frontier:
            objs = _claim_objects(n)
            if clean(n.get("mechanism")) not in COUPLING_MECHANISMS or len(objs) < 2:
                continue
            # A coupling must carry an exact commitment-side object (or an
            # object in the commitment's primary capability cluster) and a
            # distinct object outside that capability cluster.
            cap_side = [o for o in objs if o in cap_objects or (cap_primary_cluster and primary_cluster(o, vocab) == cap_primary_cluster)]
            foreign = [o for o in objs if o not in cap_side and (not cap_primary_cluster or primary_cluster(o, vocab) != cap_primary_cluster)]
            if cap_side and foreign:
                # Prefer a primary foreign object when possible: secondary
                # objects are often context tags rather than the dependency.
                primary_obj = clean(n.get("object"))
                dep = primary_obj if primary_obj in foreign else sorted(foreign)[0]
                coupling_options.append((n, dep))

        for coupling, dep_obj in sorted(coupling_options, key=lambda x: _role_strength(x[0], "coupling"), reverse=True)[:8]:
            dep_clusters = object_clusters(dep_obj, vocab)
            if not dep_clusters:
                continue

            used = {clean(commitment.get("claim_id")), clean(coupling.get("claim_id"))}
            propagation_rows = [
                n for n in frontier
                if n is not coupling and clean(n.get("claim_id")) not in used and _propagation_eligible(n, dep_obj)
            ]
            propagation = _best_excluding(propagation_rows, "propagation", used)
            if propagation:
                used.add(clean(propagation.get("claim_id")))

            # Exposure is about the capability's vulnerability, not simply any
            # negative diagnosis on the dependency branch.
            exposure_rows = [
                n for n in frontier
                if n is not coupling and clean(n.get("claim_id")) not in used and _exposure_eligible(n, cap_objects)
            ]
            exposure = _best_excluding(exposure_rows, "exposure", used)
            if exposure:
                used.add(clean(exposure.get("claim_id")))

            role_nodes = {"commitment": commitment, "coupling": coupling, "propagation": propagation, "exposure": exposure}
            missing = [r for r, n in role_nodes.items() if n is None]
            if len(missing) > 2:
                continue

            support_nodes = [n for n in role_nodes.values() if n]
            record_roles = Counter(clean(n.get("_record_id")) for n in support_nodes)
            if any(v > 2 for v in record_roles.values()):
                continue
            if len({clean(n.get("claim_id")) for n in support_nodes}) < min(3, len(support_nodes)):
                continue
            if len({clean(n.get("_record_id")) for n in support_nodes}) < 2:
                continue

            # The trigger can sit downstream of the coupling object (the worked
            # compute fixture moves energy/siting into a permitting proposal).
            # It must still be attached by an exact object carried by the
            # coupling/propagation branch, and it must be a real proposal/rule/
            # action rather than a delivered analytical statement.
            dependency_branch_objects = set(_claim_objects(coupling))
            if propagation:
                dependency_branch_objects.update(_claim_objects(propagation))
            trigger_rows = [
                n for n in frontier
                if clean(n.get("claim_id")) not in used
                and _trigger_eligible(n)
                and bool(_claim_objects(n) & dependency_branch_objects)
            ]
            trigger = max(trigger_rows, key=_trigger_maturity_key) if trigger_rows else None
            shock_driver, shock_driver_basis = _shock_driver_basis(dep_obj, support_nodes, vocab)
            # R-41: a present disruptive event/decision is a risk.  An absent trigger
            # becomes a shock only when the chain also contains a genuine
            # discontinuity driver.  Otherwise it remains an untriggered structural
            # risk pathway in stock rather than being mislabeled an external shock.
            product = "risk" if trigger or not shock_driver else "shock"

            # R-31 hop ceiling applies to every load-bearing role and to the
            # trigger used to classify a risk.
            role_depths = [hop_depths.get(clean(n.get("claim_id")), 0) for n in (coupling, propagation, exposure, trigger) if n]
            max_hop = max(role_depths or [0])
            if product == "risk" and max_hop > 2:
                continue
            if product == "shock" and max_hop > 3:
                continue

            ccluster = primary_cluster(cap_obj, vocab)
            endpoint_b = clean(trigger.get("object")) if trigger else dep_obj
            dcluster = primary_cluster(endpoint_b, vocab) or primary_cluster(dep_obj, vocab)
            chain_record_ids = {clean(n.get("_record_id")) for n in support_nodes}
            if trigger:
                chain_record_ids.add(clean(trigger.get("_record_id")))
            dist, bonus, lift = distance_excluding_records(nodes, ccluster, dcluster, chain_record_ids) if ccluster and dcluster else ("familiar", 1.0, None)

            strengths: dict[str, float] = {}
            role_corroboration: dict[str, dict[str, Any]] = {}
            for role, n in role_nodes.items():
                if not n:
                    strengths[role] = 0.0
                    role_corroboration[role] = {"factor": 1.0, "claim_ids": []}
                    continue
                # The commitment is one named institutional action; unrelated
                # actions on the same object do not corroborate it. The other
                # pathway roles may receive one independent-source x1.1 boost,
                # matching the worked R-33 arithmetic without turning a broad
                # object family into automatic corroboration.
                if role == "commitment":
                    strength, factor, supporter_ids = _role_strength(n, role), 1.0, []
                elif role == "coupling":
                    semantic_filter = lambda x: (
                        clean(x.get("kind")) in {"action", "effect", "diagnosis"}
                        and (clean(x.get("mechanism")) in COUPLING_MECHANISMS or clean(x.get("direction")) in NEGATIVE_DIRECTIONS)
                    )
                    strength, factor, supporter_ids = _role_strength_corrob(
                        n, role, nodes, semantic_filter=semantic_filter, anchor_objects={dep_obj}
                    )
                elif role == "propagation":
                    semantic_filter = lambda x, dep=dep_obj: (
                        _touches(x, dep) and clean(x.get("kind")) in {"effect", "diagnosis"}
                        and clean(x.get("direction")) in NEGATIVE_DIRECTIONS
                    )
                    strength, factor, supporter_ids = _role_strength_corrob(
                        n, role, nodes, semantic_filter=semantic_filter, anchor_objects={dep_obj}
                    )
                else:  # exposure
                    semantic_filter = lambda x, caps=set(cap_objects): _exposure_eligible(x, caps)
                    strength, factor, supporter_ids = _role_strength_corrob(
                        n, role, nodes, semantic_filter=semantic_filter, anchor_objects=set(cap_objects)
                    )
                strengths[role] = strength
                role_corroboration[role] = {"factor": factor, "claim_ids": supporter_ids}
            base = 0.35*strengths["commitment"] + 0.30*strengths["coupling"] + 0.20*strengths["propagation"] + 0.15*strengths["exposure"]
            chain_objects = set().union(*(_claim_objects(n) for n in support_nodes))
            if trigger:
                chain_objects.update(_claim_objects(trigger))
            counters = [n for n in primary if clean(n.get("mechanism")) in ABSORBERS and bool(chain_objects & _claim_objects(n))]
            penalty = min(12, 3 * len({clean(n.get("_record_id")) for n in counters}))
            floor_ok = all(v >= 0.40 for r, v in strengths.items() if role_nodes[r] is not None)
            pathway_score = max(0, min(99, round(100 * base * bonus) - penalty))

            meta = (vocab.get("objects") or {}).get(cap_obj, {})
            # A commitment can inherit stake class from an explicit secondary
            # object (e.g. public procurement -> gigafactory).
            stake_classes = [
                (vocab.get("objects") or {}).get(o, {}).get("stake_class")
                for o in cap_objects if isinstance((vocab.get("objects") or {}).get(o, {}), dict)
            ]
            stake = next((x for x in ("flagship", "capability", "rule", "budget") if x in stake_classes), meta.get("stake_class"))
            consequence = {"flagship":1.0,"capability":0.9,"rule":0.8,"budget":0.8}.get(stake,0.6)
            absorbers = [n for n in counters if clean(n.get("status")) not in {"abandoned", "lapsed"}]
            if any(clean(n.get("status")) in {"operating", "in_force", "adopted"} for n in absorbers):
                speed = 0.6
            elif absorbers:
                speed = 0.8
            else:
                speed = 1.0
            shock_score = max(0, min(99, round(100 * base * consequence * speed) - penalty))

            endpoint_joint = len({
                clean(n.get("_record_id")) for n in nodes
                if clean(n.get("era")) == "current" and clean(n.get("_record_id")) not in chain_record_ids
                and _touches(n, cap_obj) and _touches(n, endpoint_b)
            })
            level = 5 if dist in {"distant", "neutral"} and endpoint_joint < 2 else 4
            wow = 5 if endpoint_joint == 0 and dist == "distant" else 4 if endpoint_joint <= 1 else 3 if endpoint_joint <= 5 else 2
            candidate_score = shock_score if product == "shock" else pathway_score
            threshold = 60 if product == "shock" else 80
            out.append({
                "level": level, "grammar_id": "dependency_pathway", "product": product,
                "capability_object": cap_obj, "dependency_object": dep_obj,
                "shock_driver": bool(shock_driver), "shock_driver_basis": shock_driver_basis,
                "distance": dist, "distance_lift": lift, "distance_bonus": bonus,
                "frontier_mode": "exact_object_overlap", "coupling_hop": hop_depths.get(clean(coupling.get("claim_id"))), "max_role_hop": max_hop,
                "endpoint_objects": [cap_obj, endpoint_b], "endpoint_joint_outside_chain": endpoint_joint,
                "roles": {r: _snap(n, r) for r, n in role_nodes.items()}, "role_corroboration": role_corroboration,
                "trigger": _snap(trigger, "trigger"), "missing_roles": missing,
                "counter_claim_ids": sorted({clean(n.get("claim_id")) for n in counters if clean(n.get("claim_id"))}),
                "counter_penalty": penalty, "pathway_score": pathway_score, "shock_score": shock_score if product == "shock" else None,
                "score": candidate_score, "floor_ok": floor_ok, "wow_preliminary": wow,
                "score_gate_passes": level == 5 and not missing and floor_ok and candidate_score >= threshold,
                "publication_gate_passes": False,
                "publication_gate_reason": "Shadow only: executed falsifier and oddity/watchability gates are not yet recorded by the live scanner.",
            })
    best: dict[tuple[str,str,str,str], dict[str, Any]] = {}
    for c in out:
        key=(c["product"],c["capability_object"],c["dependency_object"],c["endpoint_objects"][1])
        if key not in best or (c["score_gate_passes"], c["score"], -len(c["missing_roles"])) > (best[key]["score_gate_passes"], best[key]["score"], -len(best[key]["missing_roles"])):
            best[key]=c
    return sorted(best.values(), key=lambda c: (c["score_gate_passes"], c["score"], c["wow_preliminary"]), reverse=True)[:200]

def conflicting_criteria(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any], distance: dict[str, Any]) -> list[dict[str, Any]]:
    """Claim-native conflicting criteria over an exact-object frontier.

    The criteria do not need the same primary object. The worked quantum fixture
    deliberately joins an open testing infrastructure to national export-control
    competence through the controlled equipment object. Discovery remains R-31
    exact-object graph expansion; clusters are used only for distance.
    """
    primary = [n for n in nodes if n.get("_primary") and clean(n.get("era")) == "current"]
    starts = [
        n for n in primary
        if clean(n.get("direction")) == "expands" and _criterion_eligible(n)
        and (vocab.get("objects") or {}).get(clean(n.get("object")), {}).get("stake_class") in {"flagship", "capability", "rule", "budget"}
    ]
    out: list[dict[str, Any]] = []
    for criterion_a in starts:
        frontier, depths = _exact_object_frontier(primary, criterion_a, max_hops=3)
        a_objs = _claim_objects(criterion_a)
        b_rows = [
            n for n in frontier
            if _criterion_eligible(n) and clean(n.get("direction")) in {"contracts", "becomes_conditional"}
            and bool(a_objs & _claim_objects(n))
        ]
        for criterion_b in sorted(b_rows, key=lambda n: _role_strength(n, "criterion_b"), reverse=True)[:5]:
            b_objs = _claim_objects(criterion_b)
            # The arbitration gap must bind the controlling criterion directly.
            gap_rows = [
                n for n in frontier if n is not criterion_b and clean(n.get("kind")) == "diagnosis"
                and clean(n.get("direction")) == "becomes_contested" and bool(b_objs & _claim_objects(n))
            ]
            arbitration = _best_excluding(gap_rows, "arbitration_gap", {clean(criterion_a.get("claim_id")), clean(criterion_b.get("claim_id"))})
            if not arbitration:
                continue
            # Divergence may be two exact-object hops away from the controlling
            # criterion (e.g. dual-use -> research-security national practice), but
            # may not be pulled from an unrelated branch of the seed frontier.
            b_frontier, b_depths = _exact_object_frontier(primary, criterion_b, max_hops=2)
            excluded = {clean(x.get("claim_id")) for x in (criterion_a, criterion_b, arbitration) if x}
            arbitration_objs = _claim_objects(arbitration)
            div_rows = [
                n for n in b_frontier if clean(n.get("claim_id")) not in excluded
                and clean(n.get("kind")) in {"effect", "diagnosis"}
                and clean(n.get("direction")) in {"becomes_contested", "contracts", "becomes_conditional"}
            ]
            # Prefer divergence that stays on the arbitration branch; then prefer
            # an explicitly contested national/institutional balance and the
            # shortest exact-object path. A generic downstream contraction in
            # openness therefore cannot outrank a direct research-security
            # comparison merely because it is newer.
            divergence = max(
                div_rows,
                key=lambda n: (
                    1 if bool(arbitration_objs & _claim_objects(n)) else 0,
                    1 if clean(n.get("direction")) == "becomes_contested" else 0,
                    _role_strength(n, "divergence"),
                    -(b_depths.get(clean(n.get("claim_id")), 99)),
                    float(n.get("merit", 0) or 0),
                    clean(n.get("status_date")),
                ),
                default=None,
            )
            roles = {"criterion_a": criterion_a, "criterion_b": criterion_b, "arbitration_gap": arbitration, "divergence": divergence}
            missing = [r for r,n in roles.items() if not n]
            if len(missing) > 2:
                continue
            support = [n for n in roles.values() if n]
            if len({clean(n.get("claim_id")) for n in support}) < len(support):
                continue
            if len({clean(n.get("_record_id")) for n in support}) < 2:
                continue
            strengths: dict[str, float] = {}
            role_corroboration: dict[str, dict[str, Any]] = {}
            for role, n in roles.items():
                if not n:
                    strengths[role] = 0.0
                    role_corroboration[role] = {"factor": 1.0, "claim_ids": []}
                    continue
                if role == "criterion_a":
                    semantic_filter = lambda x: (
                        clean(x.get("kind")) in {"action", "diagnosis", "effect"}
                        and clean(x.get("direction")) in {"expands", "unchanged"}
                    )
                    anchors = {clean(n.get("object"))}
                elif role == "criterion_b":
                    semantic_filter = lambda x: (
                        clean(x.get("kind")) in {"action", "diagnosis", "effect"}
                        and (
                            clean(x.get("direction")) in NEGATIVE_DIRECTIONS
                            or clean(x.get("mechanism")) in RESTRICTION_MECHANISMS
                            or clean(x.get("mechanism")) == "evaluates"
                        )
                    )
                    anchors = _claim_objects(n)
                elif role == "arbitration_gap":
                    semantic_filter = lambda x: (
                        clean(x.get("kind")) in {"diagnosis", "effect"}
                        and clean(x.get("direction")) == "becomes_contested"
                    )
                    anchors = {clean(n.get("object"))}
                else:  # divergence
                    semantic_filter = lambda x: (
                        clean(x.get("kind")) in {"diagnosis", "effect"}
                        and clean(x.get("direction")) in NEGATIVE_DIRECTIONS
                    )
                    anchors = {clean(n.get("object"))}
                strength, factor, supporter_ids = _role_strength_corrob(
                    n, role, nodes, semantic_filter=semantic_filter, anchor_objects=anchors
                )
                strengths[role] = strength
                role_corroboration[role] = {"factor": factor, "claim_ids": supporter_ids}
            base = .30*strengths["criterion_a"] + .30*strengths["criterion_b"] + .20*strengths["arbitration_gap"] + .20*strengths["divergence"]
            a_cluster = primary_cluster(clean(criterion_a.get("object")), vocab)
            b_cluster = primary_cluster(clean(criterion_b.get("object")), vocab)
            support_record_ids = {clean(n.get("_record_id")) for n in support}
            dist, bonus, lift = distance_excluding_records(nodes, a_cluster, b_cluster, support_record_ids) if a_cluster and b_cluster else ("familiar", 1.0, None)
            endpoint_a, endpoint_b = clean(criterion_a.get("object")), clean(criterion_b.get("object"))
            endpoint_joint = len({
                clean(n.get("_record_id")) for n in nodes
                if clean(n.get("era")) == "current" and clean(n.get("_record_id")) not in support_record_ids
                and _touches(n, endpoint_a) and _touches(n, endpoint_b)
            })
            chain_objs = a_objs | b_objs | _claim_objects(arbitration) | (_claim_objects(divergence) if divergence else set())
            counters = [n for n in primary if clean(n.get("mechanism")) in ABSORBERS and bool(chain_objs & _claim_objects(n))]
            penalty = min(12, 3*len({clean(n.get("_record_id")) for n in counters}))
            score = max(0, min(99, round(100*base*bonus)-penalty))
            floor_ok = all(v >= .40 for r,v in strengths.items() if roles[r])
            out.append({
                "level": 5 if dist != "familiar" and endpoint_joint < 2 else 4, "grammar_id": "conflicting_criteria", "product": "risk",
                "criterion_a_object": clean(criterion_a.get("object")), "criterion_b_object": clean(criterion_b.get("object")),
                "frontier_mode": "exact_object_overlap", "criterion_b_hop": depths.get(clean(criterion_b.get("claim_id"))),
                "endpoint_objects": [endpoint_a, endpoint_b], "endpoint_joint_outside_chain": endpoint_joint,
                "divergence_from_b_hop": b_depths.get(clean(divergence.get("claim_id"))) if divergence else None,
                "roles": {r:_snap(n,r) for r,n in roles.items()}, "role_corroboration": role_corroboration, "missing_roles": missing,
                "distance": dist, "distance_lift": lift, "distance_bonus": bonus, "score": score,
                "counter_claim_ids": sorted({clean(n.get("claim_id")) for n in counters if clean(n.get("claim_id"))}),
                "counter_penalty": penalty, "floor_ok": floor_ok,
                "score_gate_passes": not missing and floor_ok and score >= 80 and dist != "familiar" and endpoint_joint < 2,
                "publication_gate_passes": False, "publication_gate_reason": "Shadow only: no executed falsifier ledger yet."
            })
    best: dict[tuple[str,str], dict[str, Any]] = {}
    for c in out:
        key = (c["criterion_a_object"], c["criterion_b_object"])
        if key not in best or (c["score"], -len(c["missing_roles"])) > (best[key]["score"], -len(best[key]["missing_roles"])):
            best[key] = c
    return sorted(best.values(), key=lambda c:(c["score_gate_passes"], c["score"]), reverse=True)[:200]


def _stake_class(obj: str, vocab: dict[str, Any]) -> str:
    meta = (vocab.get("objects") or {}).get(clean(obj), {})
    return clean(meta.get("stake_class")) if isinstance(meta, dict) else ""


def _endpoint_joint(nodes: Iterable[dict[str, Any]], a: str, b: str, excluded: set[str] | None = None, eras: set[str] | None = None) -> int:
    excluded = excluded or set()
    eras = eras or {"current"}
    return len({
        clean(n.get("_record_id")) for n in nodes
        if clean(n.get("era")) in eras and clean(n.get("_record_id")) not in excluded
        and _touches(n, a) and _touches(n, b)
    })


def _wow_from_joint(current_joint: int, archive_joint: int, cross_cluster: bool = True, stake: bool = True) -> int:
    total = current_joint + archive_joint
    if total == 0 and cross_cluster and stake:
        return 5
    if total <= 1:
        return 4
    if total <= 5:
        return 3
    return 2


def _role_bundle_score(
    roles: dict[str, dict[str, Any] | None],
    weights: dict[str, float],
    nodes: Iterable[dict[str, Any]],
    distance_bonus: float,
    *,
    corroborate_roles: set[str] | None = None,
) -> tuple[dict[str, float], dict[str, dict[str, Any]], float]:
    corroborate_roles = corroborate_roles or set()
    strengths: dict[str, float] = {}
    corroboration: dict[str, dict[str, Any]] = {}
    for role, n in roles.items():
        if n and role in corroborate_roles:
            st, fac, ids = _role_strength_corrob(n, role, nodes)
        else:
            st, fac, ids = (_role_strength(n, role), 1.0, []) if n else (0.0, 1.0, [])
        strengths[role] = st
        corroboration[role] = {"factor": fac, "claim_ids": ids}
    base = sum(weights.get(role, 0.0) * strengths.get(role, 0.0) for role in weights)
    return strengths, corroboration, base * distance_bonus


def latent_channels(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any]) -> list[dict[str, Any]]:
    """A-3 latent_channel. One missing role is retained as a watch candidate."""
    primary = [n for n in nodes if n.get("_primary") and clean(n.get("era")) == "current"]
    need_cue = re.compile(r"\b(?:need|needs|gap|missing|lack|barrier|bottleneck|depends? on|requires?|unresolved|onboarding|visibility)\b", re.I)
    starts = [n for n in primary if clean(n.get("kind")) in {"diagnosis", "advocacy"} and need_cue.search(_semantic_text(n))]
    out: list[dict[str, Any]] = []
    for need in starts:
        frontier, depths = _exact_object_frontier(primary, need, max_hops=2)
        structure_cue = re.compile(r"\b(?:platform|federation|infrastructure|service|facility|network|portal|access|authentication|interoperab)\b", re.I)
        structures = [n for n in frontier if clean(n.get("kind")) == "action" and clean(n.get("status")) in {"operating", "in_force", "adopted", "announced", "call_open"} and structure_cue.search(_semantic_text(n))]
        for structure in sorted(structures, key=lambda n: _role_strength(n, "existing_structure"), reverse=True)[:4]:
            endpoint_a, endpoint_b = clean(need.get("object")), clean(structure.get("object"))
            if endpoint_a == endpoint_b:
                continue
            support_pool = [n for n in frontier if n is not structure]
            connection_cue = re.compile(r"\b(?:connect|integrat|interoperab|federat|onboard|link(?:s|ed|ing)?|authentication|single access)\b", re.I)
            instrument_cue = re.compile(r"\b(?:task force|programme|program|call|fund|initiative|instrument|framework|act|working group)\b", re.I)
            precedent_cue = re.compile(r"\b(?:precedent|already|existing|model|demonstrat|operat|service|platform|collectively supported)\b", re.I)
            connection = _best_excluding([
                n for n in support_pool if clean(n.get("kind")) == "action"
                and _touches(n, endpoint_a) and _touches(n, endpoint_b) and connection_cue.search(_semantic_text(n))
            ], "live_connection", {clean(need.get("claim_id")), clean(structure.get("claim_id"))})
            instrument = _best_excluding([
                n for n in support_pool if clean(n.get("kind")) == "action" and clean(n.get("status")) not in {"abandoned", "lapsed"}
                and _touches(n, endpoint_a) and instrument_cue.search(_semantic_text(n))
            ], "receiving_instrument", {clean(need.get("claim_id")), clean(structure.get("claim_id")), clean(connection.get("claim_id")) if connection else ""})
            precedent = _best_excluding([
                n for n in support_pool if clean(n.get("kind")) in {"diagnosis", "effect"}
                and (_touches(n, endpoint_a) or _touches(n, endpoint_b)) and precedent_cue.search(_semantic_text(n))
            ], "precedent", {clean(need.get("claim_id")), clean(structure.get("claim_id")), clean(connection.get("claim_id")) if connection else "", clean(instrument.get("claim_id")) if instrument else ""})
            roles = {"unresolved_need": need, "existing_structure": structure, "live_connection": connection, "receiving_instrument": instrument, "precedent": precedent}
            missing = [r for r,n in roles.items() if not n]
            if len(missing) > 2:
                continue
            support = [n for n in roles.values() if n]
            if len({clean(n.get("_record_id")) for n in support}) < 2:
                continue
            recs = {clean(n.get("_record_id")) for n in support}
            ca, cb = primary_cluster(endpoint_a, vocab), primary_cluster(endpoint_b, vocab)
            dist, bonus, lift = distance_excluding_records(nodes, ca, cb, recs) if ca and cb else ("familiar",1.0,None)
            strengths, corrob, scored = _role_bundle_score(roles, {"unresolved_need":.25,"existing_structure":.25,"live_connection":.25,"receiving_instrument":.15,"precedent":.10}, nodes, bonus)
            score = min(99, round(100 * scored)) if not missing else None
            floor_ok = all(strengths[r] >= .40 for r in roles if roles[r] and r != "precedent")
            joint = _endpoint_joint(nodes, endpoint_a, endpoint_b, recs, {"current"})
            wow = _wow_from_joint(joint, _endpoint_joint(nodes, endpoint_a, endpoint_b, recs, {"historical"}), ca != cb, bool(_stake_class(endpoint_a,vocab) or _stake_class(endpoint_b,vocab)))
            out.append({
                "level": 5, "grammar_id":"latent_channel", "product":"opportunity",
                "endpoint_objects":[endpoint_a,endpoint_b], "roles":{r:_snap(n,r) for r,n in roles.items()},
                "missing_roles":missing, "distance":dist, "distance_lift":lift, "distance_bonus":bonus,
                "score":score, "floor_ok":floor_ok, "wow_preliminary":wow,
                "score_gate_passes": bool(not missing and floor_ok and score is not None and score >= 80 and dist != "familiar" and joint < 2),
                "publication_gate_passes":False, "publication_gate_reason":"Shadow only: no executed falsifier ledger yet.",
                "feedback_search_needed": bool(missing), "frontier_mode":"exact_object_overlap",
            })
    best: dict[tuple[str,str],dict[str,Any]]={}
    for c in out:
        key=tuple(c["endpoint_objects"])
        rank=(0 if c["missing_roles"] else 1, c["score"] or 0)
        if key not in best or rank > (0 if best[key]["missing_roles"] else 1, best[key]["score"] or 0):
            best[key]=c
    return sorted(best.values(), key=lambda c:(not c["missing_roles"], c["score"] or 0), reverse=True)[:200]


def anchor_demand_candidates(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any]) -> list[dict[str, Any]]:
    primary=[n for n in nodes if n.get("_primary") and clean(n.get("era"))=="current"]
    commitments=[n for n in primary if clean(n.get("kind"))=="action" and clean(n.get("direction"))=="expands" and clean(n.get("mechanism")) in {"procures","builds","funds","launches"} and _stake_class(clean(n.get("object")), vocab) in {"flagship","capability","budget"}]
    protect_cue=re.compile(r"\b(?:protect|blocking stake|intellectual property|ip (?:stay|remain)|safeguard|eu interest|ownership rule|screening right)\b",re.I)
    conversion_cue=re.compile(r"\b(?:convert(?:s|ed|ing)? .*value|fast access|move(?:ment)? between providers|switch providers|condition for|depends? on|requires?)\b",re.I)
    reform_cue=re.compile(r"\b(?:procurement reform|innovation procurement|public[- ]sector demand|raise .* demand|market-creation)\b",re.I)
    payoff_cue=re.compile(r"\b(?:supply deal|signed .*contract|wins? .*deal|customer|order|sale|sold|supplier|anchor demand|procurement award)\b",re.I)
    out=[]
    for commitment in commitments:
        frontier,depths=_exact_object_frontier(primary,commitment,max_hops=3)
        payoff_rows=[n for n in frontier if clean(n.get("kind"))=="effect" and clean(n.get("direction"))=="expands" and clean(n.get("object"))!=clean(commitment.get("object")) and payoff_cue.search(_semantic_text(n))]
        for payoff in sorted(payoff_rows,key=lambda n:_role_strength(n,"payoff_evidence"),reverse=True)[:4]:
            excluded={clean(commitment.get("claim_id")),clean(payoff.get("claim_id"))}
            protecting=_best_excluding([n for n in frontier if clean(n.get("kind"))=="action" and protect_cue.search(_semantic_text(n))],"protecting_instrument",excluded)
            if protecting: excluded.add(clean(protecting.get("claim_id")))
            conversion=_best_excluding([n for n in frontier if clean(n.get("kind")) in {"diagnosis","effect"} and conversion_cue.search(_semantic_text(n))],"conversion_condition",excluded)
            if conversion: excluded.add(clean(conversion.get("claim_id")))
            reform=_best_excluding([n for n in frontier if clean(n.get("kind"))=="action" and reform_cue.search(_semantic_text(n))],"enabling_reform",excluded)
            roles={"commitment":commitment,"payoff_evidence":payoff,"protecting_instrument":protecting,"conversion_condition":conversion,"enabling_reform":reform}
            missing=[r for r,n in roles.items() if not n]
            if len(missing)>2: continue
            support=[n for n in roles.values() if n]
            if len({clean(n.get("_record_id")) for n in support})<2: continue
            ea,eb=clean(commitment.get("object")),clean(payoff.get("object")); recs={clean(n.get("_record_id")) for n in support}
            ca,cb=primary_cluster(ea,vocab),primary_cluster(eb,vocab)
            dist,bonus,lift=distance_excluding_records(nodes,ca,cb,recs) if ca and cb else ("familiar",1.0,None)
            strengths,corrob,scored=_role_bundle_score(roles,{"commitment":.30,"payoff_evidence":.25,"protecting_instrument":.20,"conversion_condition":.15,"enabling_reform":.10},nodes,bonus,corroborate_roles={"commitment","payoff_evidence"})
            counters=[]
            for n in nodes:
                if clean(n.get("_record_id")) in recs: continue
                txt=_semantic_text(n)
                if _touches(n,eb) and ("alongside, not instead" in txt or "alongside not instead" in txt): counters.append(n)
            penalty=min(12,3*len({clean(n.get("_record_id")) for n in counters}))
            score=max(0,min(99,round(100*scored)-penalty)) if not missing else None
            floor_ok=all(strengths[r]>=.40 for r in roles if roles[r] and r!="enabling_reform")
            joint=_endpoint_joint(nodes,ea,eb,recs,{"current"})
            wow=_wow_from_joint(joint,_endpoint_joint(nodes,ea,eb,recs,{"historical"}),ca!=cb,bool(_stake_class(ea,vocab) or _stake_class(eb,vocab)))
            out.append({"level":5,"grammar_id":"anchor_demand","product":"opportunity","endpoint_objects":[ea,eb],"roles":{r:_snap(n,r) for r,n in roles.items()},"role_corroboration":corrob,"missing_roles":missing,"distance":dist,"distance_lift":lift,"distance_bonus":bonus,"score":score,"counter_penalty":penalty,"counter_claim_ids":[clean(n.get("claim_id")) for n in counters],"floor_ok":floor_ok,"wow_preliminary":wow,"score_gate_passes":bool(not missing and floor_ok and score is not None and score>=80 and dist!="familiar" and joint<2),"publication_gate_passes":False,"publication_gate_reason":"Shadow only: no executed falsifier ledger yet.","frontier_mode":"exact_object_overlap"})
    best={}
    for c in out:
        key=tuple(c["endpoint_objects"]); rank=(not c["missing_roles"],c["score"] or 0)
        if key not in best or rank>(not best[key]["missing_roles"],best[key]["score"] or 0): best[key]=c
    return sorted(best.values(),key=lambda c:(c["score_gate_passes"],c["score"] or 0),reverse=True)[:200]


def split_recurrence_candidates(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any]) -> list[dict[str, Any]]:
    current=[n for n in nodes if n.get("_primary") and clean(n.get("era"))=="current"]
    historical=[n for n in nodes if clean(n.get("era"))=="historical" and clean(n.get("_decision"))=="keep" and clean(n.get("kind")) in {"diagnosis","effect"} and len(_claim_objects(n))>=2]
    out=[]
    for hist in historical:
        objs=sorted(_claim_objects(hist))
        for a,b in itertools.combinations(objs,2):
            arows=[n for n in current if _touches(n,a) and clean(n.get("kind")) in {"action","effect"}]
            brows=[n for n in current if _touches(n,b) and clean(n.get("kind")) in {"action","effect"}]
            if len({clean(n.get("_record_id")) for n in arows})<1: continue
            if len({clean(n.get("_record_id")) for n in brows})<1: continue
            current_joint=_endpoint_joint(nodes,a,b,set(),{"current"})
            if current_joint: continue
            side_a=max(arows,key=lambda n:_role_strength(n,"side_a")); side_b=max(brows,key=lambda n:_role_strength(n,"side_b"))
            hist_strength=_role_strength(hist,"historical_relation")*float(hist.get("_context_weight",1.0) or 1.0)
            a_strength=min(1.0,_role_strength(side_a,"side_a")*min(1.3,1+.1*max(0,_distinct_sources(arows)-1)))
            b_strength=min(1.0,_role_strength(side_b,"side_b")*min(1.3,1+.1*max(0,_distinct_sources(brows)-1)))
            recs={clean(side_a.get("_record_id")),clean(side_b.get("_record_id"))}
            ca,cb=primary_cluster(a,vocab),primary_cluster(b,vocab); dist,bonus,lift=distance_excluding_records(nodes,ca,cb,recs) if ca and cb else ("familiar",1.0,None)
            base=.35*hist_strength+.30*a_strength+.30*b_strength+.05
            score=min(90,max(0,round(100*base*bonus)))
            floor_ok=min(hist_strength,a_strength,b_strength)>=.40
            out.append({"level":5,"grammar_id":"split_recurrence","product":"phenomenon","endpoint_objects":[a,b],"roles":{"historical_relation":_snap(hist,"historical_relation"),"side_a":_snap(side_a,"side_a"),"side_b":_snap(side_b,"side_b")},"side_a_record_count":len({clean(n.get("_record_id")) for n in arows}),"side_a_source_count":_distinct_sources(arows),"side_b_record_count":len({clean(n.get("_record_id")) for n in brows}),"side_b_source_count":_distinct_sources(brows),"current_joint":0,"distance":dist,"distance_lift":lift,"distance_bonus":bonus,"score":score,"floor_ok":floor_ok,"wow_preliminary":5,"score_gate_passes":bool(floor_ok and score>=80 and dist!="familiar"),"publication_gate_passes":False,"publication_gate_reason":"Shadow only: no executed falsifier ledger yet."})
    best={}
    for c in out:
        key=tuple(c["endpoint_objects"])
        if key not in best or c["score"]>best[key]["score"]: best[key]=c
    return sorted(best.values(),key=lambda c:(c["score_gate_passes"],c["score"]),reverse=True)[:200]


def era_conjunctions(nodes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """R-13b / section 4.3 object-pair lift change between eras."""
    def records(era:str, primary_required:bool) -> tuple[dict[str,set[str]],dict[str,set[str]]]:
        objs:dict[str,set[str]]=defaultdict(set); srcs:dict[str,set[str]]=defaultdict(set)
        for n in nodes:
            if clean(n.get("era"))!=era: continue
            if primary_required and not n.get("_primary"): continue
            rid=clean(n.get("_record_id"));
            if not rid: continue
            objs[rid].update(_claim_objects(n)); srcs[rid].add(clean(n.get("_source")).lower())
        return objs,srcs
    cur,cur_src=records("current",True); hist,hist_src=records("historical",False)
    current_objects=Counter(o for ss in cur.values() for o in ss); historical_objects=Counter(o for ss in hist.values() for o in ss)
    historical_authoritative = {clean(n.get("_record_id")) for n in nodes if clean(n.get("era")) == "historical" and clean(n.get("_decision")) == "keep"}
    candidates=set(current_objects)&set(historical_objects); out=[]
    for a,b in itertools.combinations(sorted(candidates),2):
        cj=[rid for rid,ss in cur.items() if a in ss and b in ss]; hj=[rid for rid,ss in hist.items() if a in ss and b in ss]
        if len(cj)<6 or len(hj)<3: continue
        c_sources={s for rid in cj for s in cur_src.get(rid,set()) if s}; h_sources={s for rid in hj for s in hist_src.get(rid,set()) if s}
        if len(c_sources)<5 or len(h_sources)<3: continue
        if not any(rid in historical_authoritative for rid in hj): continue
        cexp=(current_objects[a]*current_objects[b]/len(cur)) if cur else 0; hexp=(historical_objects[a]*historical_objects[b]/len(hist)) if hist else 0
        clift=len(cj)/cexp if cexp else 0; hlift=len(hj)/hexp if hexp else 0; gain=clift-hlift
        if gain<.38: continue
        wow=4 if gain>=2 else 3 if gain>=1 else 2
        out.append({"level":3,"grammar_id":"era_conjunction","product":"phenomenon","endpoint_objects":[a,b],"current_joint":len(cj),"current_sources":len(c_sources),"historical_joint":len(hj),"historical_sources":len(h_sources),"current_lift":round(clift,3),"historical_lift":round(hlift,3),"gain":round(gain,3),"wow_preliminary":wow,"strength":"strong" if len(cj)>=6 and len(c_sources)>=5 and len(h_sources)>=3 else "watch"})
    return sorted(out,key=lambda x:(x["gain"],x["current_joint"]),reverse=True)[:50]


def shadow_diff_report(legacy: dict[str, Any], groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    shadow_counts={name:len(rows) for name,rows in groups.items()}
    legacy_by_grammar={clean(k):int(v) for k,v in (legacy.get("by_grammar") or {}).items() if clean(k)}
    grammar_alias={
        "corroborated_claim":"level2_corroborated","opposing_movements":"level4_opposing_movements",
        "dependency_pathway":"level5_dependency_pathway","conflicting_criteria":"level4_5_conflicting_criteria",
        "latent_channel":"level5_latent_channel","anchor_demand":"level5_anchor_demand","split_recurrence":"level5_split_recurrence","era_conjunction":"level3_era_conjunction",
    }
    shadow_by_grammar={g:len(groups.get(alias,[])) for g,alias in grammar_alias.items()}
    return {
        "legacy_candidate_count": legacy.get("candidate_count",0),
        "legacy_by_grammar": legacy_by_grammar,
        "shadow_by_grammar": shadow_by_grammar,
        "count_delta_by_grammar": {g:shadow_by_grammar.get(g,0)-legacy_by_grammar.get(g,0) for g in sorted(set(shadow_by_grammar)|set(legacy_by_grammar))},
        "shadow_group_counts": shadow_counts,
        "publication_delta": 0,
        "note":"Diagnostic count diff only. Candidate identity diff remains intentionally fail-closed until the live detector shell is switched in Stage 6.",
    }

def claim_expressiveness(nodes: Iterable[dict[str, Any]]) -> dict[str, Any]:
    current = [n for n in nodes if clean(n.get("era")) == "current"]
    primary = [n for n in current if n.get("_primary")]
    mech = Counter(clean(n.get("mechanism")) for n in primary)
    secondary = sum(1 for n in primary if n.get("secondary_objects"))
    relational = sum(1 for n in primary if clean(n.get("mechanism")) in COUPLING_MECHANISMS)
    c_primary = [n for n in primary if n.get("_collection") == "strand_c"]
    action_cue = re.compile(r"\b(?:adopted|took effect|entered into force|enacted|opened|launched|proposes?|signed|establish(?:ed|ing)|funds|funded (?:a|an|the|new|additional|programme|program|project|call|award)|awarded|selected|announced|approved|introduced|implemented|joined)\b", re.I)
    suspicious_c_diagnosis = [n for n in c_primary if clean(n.get("kind")) == "diagnosis" and action_cue.search(clean(n.get("_deep_main")))]
    assesses_share = (mech.get("assesses", 0) / len(primary)) if primary else 0.0
    secondary_share = (secondary / len(primary)) if primary else 0.0
    warnings=[]
    advisories=[]
    if assesses_share > 0.60:
        advisories.append("Most current primary diagnoses use mechanism=assesses. This is acceptable for descriptive diagnoses, but relational diagnoses should continue to be enriched when Deep Scan states an explicit dependency or restriction.")
    if secondary_share < 0.10:
        warnings.append("Fewer than 10% of current primary claims carry secondary_objects; multi-object graph expansion may be sparse.")
    if len(suspicious_c_diagnosis) > 0:
        warnings.append("Some primary Strand C diagnosis claims contain explicit event/action cues in the Deep Scan main finding and need semantic review before detector switch.")
    return {
        "current_claims": len(current), "current_primary_claims": len(primary),
        "primary_mechanisms_top": mech.most_common(12),
        "assesses_share": round(assesses_share, 4),
        "claims_with_secondary_objects": secondary,
        "secondary_object_share": round(secondary_share, 4),
        "explicit_relational_mechanism_claims": relational,
        "strand_c_primary_action_or_effect": sum(1 for n in c_primary if clean(n.get("kind")) in {"action","effect"}),
        "strand_c_action_cue_but_diagnosis": len(suspicious_c_diagnosis),
        "strand_c_action_cue_examples": [
            {"claim_id": n.get("claim_id"), "title": n.get("_title"), "status": n.get("status"), "mechanism": n.get("mechanism"), "deep_main": n.get("_deep_main")}
            for n in suspicious_c_diagnosis[:25]
        ],
        "ready_for_detector_switch": not warnings,
        "warnings": warnings,
        "advisories": advisories,
    }

def legacy_summary(raw: dict[str, Any]) -> dict[str, Any]:
    # Despite the historical function name, this is the persisted *live detector*
    # snapshot.  Stage 6 uses these fields to prove that the detector backend
    # actually switched while the publication compatibility lock stayed closed.
    state = raw.get("high_order_inference") if isinstance(raw.get("high_order_inference"), dict) else {}
    cs = [c for c in state.get("candidates", []) if isinstance(c, dict)]
    return {
        "profile_version": state.get("profile_version"),
        "detector_backend": state.get("detector_backend", "legacy"),
        "detector_switch_stage": state.get("detector_switch_stage"),
        "selection_stage": state.get("selection_stage"),
        "publication_compatibility_lock": bool(state.get("publication_compatibility_lock", False)),
        "claim_candidate_count": int(state.get("claim_candidate_count", 0) or 0),
        "legacy_publication_carry_count": int(state.get("legacy_publication_carry_count", 0) or 0),
        "claim_switch_error": state.get("claim_switch_error"),
        "candidate_count": len(cs),
        "by_status": dict(Counter(clean(c.get("status")) for c in cs)),
        "by_product": dict(Counter(clean(c.get("product")) for c in cs)),
        "by_grammar": dict(Counter(clean(c.get("grammar_id")) for c in cs)),
        "publications": state.get("publications", {}),
        "selection": state.get("selection", {}),
        "selected_publication_count": sum(len(v) for v in (state.get("publications", {}) or {}).values() if isinstance(v, list)),
    }


def run_shadow(root: Path = ROOT, evaluated_at: str | None = None) -> dict[str, Any]:
    vocab = load_vocabulary(root / "claims_vocabulary.json")
    active = build_active_snapshot(root)
    nodes, diagnostics = flatten_claims(active, vocab)
    if evaluated_at:
        ev_date = _date(evaluated_at) or dt.datetime.now(dt.timezone.utc).date()
    else:
        ev_date = _date(active.get("run_completed_at") or active.get("last_updated")) or dt.datetime.now(dt.timezone.utc).date()
    distance = build_distance_table(nodes)
    expressiveness = claim_expressiveness(nodes)
    level2 = corroborated_claims(nodes)
    continuities = named_continuities(nodes)
    level3 = level3_findings(nodes, ev_date)
    level4 = opposing_movements(nodes, ev_date, vocab)
    dependency = dependency_pathways(nodes, vocab, distance)
    criteria = conflicting_criteria(nodes, vocab, distance)
    latent = latent_channels(nodes, vocab)
    anchor = anchor_demand_candidates(nodes, vocab)
    split = split_recurrence_candidates(nodes, vocab)
    era = era_conjunctions(nodes)
    raw = json.loads((root / "radar.json").read_text(encoding="utf-8"))
    legacy = legacy_summary(raw)
    groups = {
        "level2_corroborated": level2,
        "level2_named_continuity": continuities,
        "level3_sequence_gap": level3,
        "level3_era_conjunction": era,
        "level4_opposing_movements": level4,
        "level5_dependency_pathway": dependency,
        "level4_5_conflicting_criteria": criteria,
        "level5_latent_channel": latent,
        "level5_anchor_demand": anchor,
        "level5_split_recurrence": split,
    }
    diff = shadow_diff_report(legacy, groups)
    score_pool = dependency + criteria + latent + anchor + split
    return {
        "profile": PROFILE,
        "evaluated_at": ev_date.isoformat(),
        "mode": "shadow_only_no_live_writes",
        "safety": {
            "changes_live_reasoning": False,
            "changes_reader": False,
            "changes_scanner": False,
            "changes_deep_scan_decisions": False,
            "publishable": False,
        },
        "claim_diagnostics": diagnostics,
        "claim_expressiveness": expressiveness,
        "distance_table": distance,
        "claim_reasoning": groups,
        "shadow_counts": {
            "level2": len(level2) + len(continuities), "named_continuity": len(continuities), "level3": len(level3) + len(era), "level4": len(level4),
            "dependency_pathway": len(dependency), "conflicting_criteria": len(criteria),
            "latent_channel": len(latent), "anchor_demand": len(anchor),
            "split_recurrence": len(split), "era_conjunction": len(era),
            "score_gate_passes": sum(1 for c in score_pool if c.get("score_gate_passes")),
            "publication_gate_passes": 0,
        },
        "legacy_snapshot": legacy,
        "shadow_diff": diff,
        "migration_gate": {
            "semantic_quality_ready": bool(expressiveness.get("ready_for_detector_switch")),
            "production_grammars_implemented": True,
            "publication_lock_held": bool(legacy.get("publication_compatibility_lock", True)),
            "two_scan_observation_required": clean(legacy.get("detector_backend")) != "claim_native",
            "detector_switch_code_enabled": clean(legacy.get("detector_backend")) == "claim_native",
            "selection_stage": legacy.get("selection_stage"),
            "live_selected_publications": int(legacy.get("selected_publication_count", 0) or 0),
            "live_detector_backend": clean(legacy.get("detector_backend")) or "legacy",
        },
        "limitations": [
            "The shadow itself never publishes; live Stage-7 selection is reported from the persisted claim-native detector snapshot.",
            "A live candidate still requires an actually executed candidate-specific falsifier query before selection.",
            "Reader prose/label lint remains a Stage-8 concern even when Stage-7 selection is active.",
        ],
    }


def summary_markdown(report: dict[str, Any]) -> str:
    c = report["shadow_counts"]; d=report["claim_diagnostics"]; legacy=report["legacy_snapshot"]; gate=report.get("migration_gate",{})
    lines = [
        "# Claim reasoning shadow report", "",
        f"Evaluated: {report['evaluated_at']}", "",
        "**This artifact is diagnostic only. It does not alter the public Radar.**", "",
        "## Claim layer", f"- Loaded world-reasoning claims: {d.get('claims_loaded',0)}", f"- Primary claims: {d.get('primary_claims',0)}", f"- Context claims: {d.get('context_claims',0)}", f"- Methods/world-disabled claims excluded: {d.get('methods_or_world_disabled',0)}", "",
        "## Migration gate", f"- Semantic quality ready: {gate.get('semantic_quality_ready')}", f"- Production grammars implemented in shadow: {gate.get('production_grammars_implemented')}", f"- Live detector backend: {gate.get('live_detector_backend')}", f"- Publication lock held: {gate.get('publication_lock_held')}", f"- Two-scan observation still required: {gate.get('two_scan_observation_required')}", f"- Detector switch enabled: {gate.get('detector_switch_code_enabled')}", f"- Selection stage: {gate.get('selection_stage')}", f"- Live selected publications: {gate.get('live_selected_publications')}", "",
        "## Claim-native shadow", f"- Level 2 corroborated claims: {c['level2']}", f"- Level 3 sequence/gap + era findings: {c['level3']}", f"- Level 4 opposing movements: {c['level4']}", f"- Dependency-pathway candidates: {c['dependency_pathway']}", f"- Conflicting-criteria candidates: {c['conflicting_criteria']}", f"- Latent-channel candidates: {c['latent_channel']}", f"- Anchor-demand candidates: {c['anchor_demand']}", f"- Split-recurrence candidates: {c['split_recurrence']}", f"- Era-conjunction findings: {c['era_conjunction']}", f"- Score gates passed: {c['score_gate_passes']}", f"- Diagnostic shadow publication gates passed: {c['publication_gate_passes']} (shadow never publishes)", "",
        "## Live detector snapshot / diff", f"- Detector backend: {legacy.get('detector_backend','legacy')}", f"- Persisted candidates: {legacy.get('candidate_count',0)}", f"- Claim-native candidates: {legacy.get('claim_candidate_count',0)}", f"- Legacy publication carries: {legacy.get('legacy_publication_carry_count',0)}", f"- Persisted status counts: `{json.dumps(legacy.get('by_status',{}), sort_keys=True)}`", f"- Grammar count delta: `{json.dumps(report.get('shadow_diff',{}).get('count_delta_by_grammar',{}), sort_keys=True)}`", "",
        "## Safety", "- No scanner write", "- No Deep Scan decision change", "- No radar.json/radar_active.json write", "- No reader/publication switch", "",
    ]
    return "\n".join(lines)

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--summary", type=Path, default=None)
    ap.add_argument("--evaluated-at", default="")
    args=ap.parse_args()
    report=run_shadow(args.root, args.evaluated_at or None)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(summary_markdown(report)+"\n",encoding="utf-8")
    print(json.dumps({"profile":report["profile"],"evaluated_at":report["evaluated_at"],"claim_diagnostics":report["claim_diagnostics"],"shadow_counts":report["shadow_counts"],"legacy_snapshot":{k:v for k,v in report["legacy_snapshot"].items() if k!='publications'}},indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
