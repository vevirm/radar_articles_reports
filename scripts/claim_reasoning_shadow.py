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

PROFILE = "radar-claim-reasoning-shadow-v1.2-role-constrained-frontier"
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
                errors = validate_claim(claim, vocab)
                if errors:
                    diag["schema_invalid_claims"] += 1
                    continue
                if collection == "strand_b" or not _world_reasoning_allowed(claim):
                    diag["methods_or_world_disabled"] += 1
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
                    # R-09: only KEEP event content from C is primary. Diagnosis and
                    # advocacy remain context because they are interpretation, not event.
                    primary = decision == "keep" and kind in {"action", "effect"}
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
        return "familiar", 1.0, math.inf
    x, y = sorted((a, b))
    for p in table.get("pairs", []):
        if p.get("a") == x and p.get("b") == y:
            return clean(p.get("distance")), float(p.get("bonus", 1.0)), p.get("lift")
    return "distant", 1.20, None


def distance_excluding_records(nodes: Iterable[dict[str, Any]], a: str, b: str, excluded_record_ids: set[str]) -> tuple[str, float, float | None]:
    """R-10 distance after removing the candidate chain's own records."""
    if a == b:
        return "familiar", 1.0, math.inf
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
        if len(sources) < 2 or len(records) < 2:
            continue
        strongest = max(rows, key=lambda r: (float(r.get("merit", 0) or 0), STATUS_RANK.get(clean(r.get("status")), 0)))
        out.append({
            "level": 2, "grammar_id": "corroborated_claim", "object": key[0], "mechanism": key[1], "direction": key[2],
            "source_count": len(sources), "record_count": len(records), "status": strongest.get("status"),
            "claim_ids": sorted({clean(r.get("claim_id")) for r in rows if clean(r.get("claim_id"))}),
        })
    return sorted(out, key=lambda x: (x["source_count"], x["record_count"], x["object"]), reverse=True)


def level3_findings(nodes: Iterable[dict[str, Any]], evaluated_on: dt.date) -> list[dict[str, Any]]:
    current = [n for n in nodes if n.get("_primary") and clean(n.get("era")) == "current"]
    by_object: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in current:
        by_object[clean(n.get("object"))].append(n)
    out: list[dict[str, Any]] = []
    for obj, rows in by_object.items():
        for p in rows:
            pd = _date(p.get("status_date"))
            if clean(p.get("status")) != "proposed" or not pd or (evaluated_on - pd).days <= 180:
                continue
            later = [r for r in rows if (_date(r.get("status_date")) or dt.date.min) > pd and STATUS_RANK.get(clean(r.get("status")), 0) > STATUS_RANK["proposed"]]
            if not later:
                out.append({"level": 3, "grammar_id": "stalled_proposal", "object": obj, "proposal_claim_id": p.get("claim_id"), "age_days": (evaluated_on - pd).days})
    # R-24d: goal without measure. Partial dates do not matter because this is a corpus ratio.
    for obj, rows in by_object.items():
        inv = [r for r in rows if clean(r.get("kind")) in {"advocacy", "action"}]
        meas = [r for r in rows if clean(r.get("kind")) == "effect"]
        if len(inv) >= 12 * max(1, len(meas)) and len(inv) >= 12 and (obj.startswith("goal.") or obj == "goal.strategic_autonomy"):
            out.append({"level": 3, "grammar_id": "goal_without_measure", "object": obj, "invocations": len(inv), "measurements": len(meas), "ratio": None if not meas else round(len(inv) / len(meas), 2)})
    return out


def opposing_movements(nodes: Iterable[dict[str, Any]], evaluated_on: dt.date) -> list[dict[str, Any]]:
    eligible_scopes = {"eu", "member_state", "associated_country", "company_in_eu"}
    by_object_dir: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for n in nodes:
        if not n.get("_primary") or clean(n.get("era")) != "current":
            continue
        scope = n.get("scope") if isinstance(n.get("scope"), dict) else {}
        if clean(scope.get("level")) not in eligible_scopes:
            continue
        d = _date(n.get("status_date"))
        if d and (evaluated_on - d).days > 180:
            continue
        direction = clean(n.get("direction"))
        if direction in {"expands", "contracts"}:
            by_object_dir[(clean(n.get("object")), direction)].append(n)
    out = []
    for obj in sorted({k[0] for k in by_object_dir}):
        left, right = by_object_dir[(obj, "expands")], by_object_dir[(obj, "contracts")]
        def side_ok(rows: list[dict[str, Any]]) -> bool:
            return len({clean(r.get("_record_id")) for r in rows}) >= 3 and len({clean(r.get("_source")).lower() for r in rows}) >= 2
        if not (side_ok(left) and side_ok(right)):
            continue
        def weighted(rows: list[dict[str, Any]]) -> float:
            per_source = Counter()
            total = 0.0
            for r in sorted(rows, key=lambda x: clean(x.get("status_date")), reverse=True):
                src = clean(r.get("_source")).lower()
                per_source[src] += 1
                independence = 1.0 / (2 ** (per_source[src] - 1))
                d = _date(r.get("status_date"))
                age = (evaluated_on - d).days if d else 999
                freshness = 1.0 if age <= 90 else 0.85 if age <= 180 else 0.70
                attrs = r.get("attributes") if isinstance(r.get("attributes"), dict) else {}
                witness = 1.2 if attrs.get("hostile_witness") is True and clean((r.get("actor") or {}).get("class")) in {"eu_body", "member_state", "national_funder", "third_country", "court"} else 1.0
                corroboration = min(1.3, max(1.0, float(attrs.get("corroboration_factor", 1.0) or 1.0)))
                total += (float(r.get("merit", 0) or 0) / 100.0) * KIND_WEIGHT.get(clean(r.get("kind")), 0.5) * STATUS_WEIGHT.get(clean(r.get("status")), 0.0) * independence * freshness * witness * corroboration
            return round(total, 4)
        lw, rw = weighted(left), weighted(right)
        total = lw + rw
        pull = None if total <= 0 else round(100 * lw / total, 1)
        out.append({"level": 4, "grammar_id": "opposing_movements", "object": obj, "expands_records": len({r.get('_record_id') for r in left}), "contracts_records": len({r.get('_record_id') for r in right}), "expands_sources": len({clean(r.get('_source')).lower() for r in left}), "contracts_sources": len({clean(r.get('_source')).lower() for r in right}), "expands_weight": lw, "contracts_weight": rw, "expands_pull_preliminary": pull, "note": "Shadow diagnostic only; hostile-witness/action-dedup metadata are applied only when explicitly present."})
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
            if len(missing) > 1:
                continue

            support_nodes = [n for n in role_nodes.values() if n]
            record_roles = Counter(clean(n.get("_record_id")) for n in support_nodes)
            if any(v > 2 for v in record_roles.values()):
                continue
            if len({clean(n.get("claim_id")) for n in support_nodes}) < min(3, len(support_nodes)):
                continue
            if len({clean(n.get("_record_id")) for n in support_nodes}) < min(3, len(support_nodes)) or _distinct_sources(support_nodes) < 2:
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
            product = "risk" if trigger else "shock"

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
            dist, bonus, lift = distance_excluding_records(nodes, ccluster, dcluster, chain_record_ids) if ccluster and dcluster else ("familiar", 1.0, math.inf)

            strengths = {r: (_role_strength(n, r) if n else 0.0) for r, n in role_nodes.items()}
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
                "distance": dist, "distance_lift": lift, "distance_bonus": bonus,
                "frontier_mode": "exact_object_overlap", "coupling_hop": hop_depths.get(clean(coupling.get("claim_id"))), "max_role_hop": max_hop,
                "endpoint_objects": [cap_obj, endpoint_b], "endpoint_joint_outside_chain": endpoint_joint,
                "roles": {r: _snap(n, r) for r, n in role_nodes.items()}, "trigger": _snap(trigger, "trigger"), "missing_roles": missing,
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
    return sorted(best.values(), key=lambda c: (c["score_gate_passes"], c["score"], c["wow_preliminary"]), reverse=True)[:80]

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
                    -(b_depths.get(clean(n.get("claim_id")), 99)),
                    _role_strength(n, "divergence"),
                    float(n.get("merit", 0) or 0),
                    clean(n.get("status_date")),
                ),
                default=None,
            )
            roles = {"criterion_a": criterion_a, "criterion_b": criterion_b, "arbitration_gap": arbitration, "divergence": divergence}
            missing = [r for r,n in roles.items() if not n]
            if len(missing) > 1:
                continue
            support = [n for n in roles.values() if n]
            if len({clean(n.get("claim_id")) for n in support}) < len(support):
                continue
            if len({clean(n.get("_record_id")) for n in support}) < min(3, len(support)) or _distinct_sources(support) < 2:
                continue
            strengths = {r: (_role_strength(n, r) if n else 0.0) for r,n in roles.items()}
            base = .30*strengths["criterion_a"] + .30*strengths["criterion_b"] + .20*strengths["arbitration_gap"] + .20*strengths["divergence"]
            a_cluster = primary_cluster(clean(criterion_a.get("object")), vocab)
            b_cluster = primary_cluster(clean(criterion_b.get("object")), vocab)
            support_record_ids = {clean(n.get("_record_id")) for n in support}
            dist, bonus, lift = distance_excluding_records(nodes, a_cluster, b_cluster, support_record_ids) if a_cluster and b_cluster else ("familiar", 1.0, math.inf)
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
                "roles": {r:_snap(n,r) for r,n in roles.items()}, "missing_roles": missing,
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
    return sorted(best.values(), key=lambda c:(c["score_gate_passes"], c["score"]), reverse=True)[:60]

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
    state = raw.get("high_order_inference") if isinstance(raw.get("high_order_inference"), dict) else {}
    cs = [c for c in state.get("candidates", []) if isinstance(c, dict)]
    return {
        "profile_version": state.get("profile_version"),
        "candidate_count": len(cs),
        "by_status": dict(Counter(clean(c.get("status")) for c in cs)),
        "by_product": dict(Counter(clean(c.get("product")) for c in cs)),
        "by_grammar": dict(Counter(clean(c.get("grammar_id")) for c in cs)),
        "publications": state.get("publications", {}),
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
    level3 = level3_findings(nodes, ev_date)
    level4 = opposing_movements(nodes, ev_date)
    dependency = dependency_pathways(nodes, vocab, distance)
    criteria = conflicting_criteria(nodes, vocab, distance)
    raw = json.loads((root / "radar.json").read_text(encoding="utf-8"))
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
        "claim_reasoning": {
            "level2_corroborated": level2,
            "level3_sequence_gap": level3,
            "level4_opposing_movements": level4,
            "level5_dependency_pathway": dependency,
            "level4_5_conflicting_criteria": criteria,
        },
        "shadow_counts": {
            "level2": len(level2), "level3": len(level3), "level4": len(level4),
            "dependency_pathway": len(dependency), "conflicting_criteria": len(criteria),
            "score_gate_passes": sum(1 for c in dependency + criteria if c.get("score_gate_passes")),
            "publication_gate_passes": 0,
        },
        "legacy_snapshot": legacy_summary(raw),
        "limitations": [
            "No shadow candidate is publishable until falsifier execution is recorded by candidate fingerprint.",
            "Stage 5C constrains dependency and conflicting-criteria roles to their R-32 semantics. Remaining A-3 grammars are added before any detector switch.",
            "Trend pull is preliminary where explicit action-dedup/hostile-witness metadata are absent.",
        ],
    }


def summary_markdown(report: dict[str, Any]) -> str:
    c = report["shadow_counts"]; d=report["claim_diagnostics"]; legacy=report["legacy_snapshot"]
    lines = [
        "# Claim reasoning shadow report", "",
        f"Evaluated: {report['evaluated_at']}", "",
        "**This artifact is diagnostic only. It does not alter the public Radar.**", "",
        "## Claim layer", f"- Loaded world-reasoning claims: {d.get('claims_loaded',0)}", f"- Primary claims: {d.get('primary_claims',0)}", f"- Context claims: {d.get('context_claims',0)}", f"- Methods/world-disabled claims excluded: {d.get('methods_or_world_disabled',0)}", "",
        "## Claim expressiveness gate", f"- Ready for detector switch: {report['claim_expressiveness']['ready_for_detector_switch']}", f"- assesses share among current primary claims: {report['claim_expressiveness']['assesses_share']:.1%}", f"- secondary-object share: {report['claim_expressiveness']['secondary_object_share']:.1%}", f"- Strand C action-cue diagnoses needing review: {report['claim_expressiveness']['strand_c_action_cue_but_diagnosis']}", "",
        "## Claim-native shadow", f"- Level 2 corroborated claims: {c['level2']}", f"- Level 3 sequence/gap findings: {c['level3']}", f"- Level 4 opposing movements: {c['level4']}", f"- Dependency-pathway candidates: {c['dependency_pathway']}", f"- Conflicting-criteria candidates: {c['conflicting_criteria']}", f"- Score gates passed: {c['score_gate_passes']}", f"- Publication gates passed: {c['publication_gate_passes']} (intentionally zero in Stage 5)", "",
        "## Legacy snapshot", f"- Legacy candidates: {legacy.get('candidate_count',0)}", f"- Legacy status counts: `{json.dumps(legacy.get('by_status',{}), sort_keys=True)}`", "",
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
