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

PROFILE = "radar-claim-reasoning-shadow-v1"
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
    "delivery_instrument": {"action"}, "measurement_blind_spot": {"diagnosis"},
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


def dependency_pathways(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any], distance: dict[str, Any]) -> list[dict[str, Any]]:
    primary = [n for n in nodes if n.get("_primary") and clean(n.get("era")) == "current"]
    commitments = []
    for n in primary:
        meta = (vocab.get("objects") or {}).get(clean(n.get("object")), {})
        if clean(n.get("kind")) == "action" and clean(n.get("direction")) == "expands" and meta.get("stake_class") in {"flagship", "capability", "budget"}:
            commitments.append(n)
    out: list[dict[str, Any]] = []
    for commitment in commitments:
        cap_obj = clean(commitment.get("object")); cap_clusters = set(commitment.get("_clusters") or [])
        coupling_options = []
        for n in primary:
            objs = [clean(n.get("object"))] + [clean(x) for x in (n.get("secondary_objects") or [])]
            clusters = set(n.get("_clusters") or [])
            if n is commitment or not (cap_clusters & clusters):
                continue
            if clean(n.get("mechanism")) not in COUPLING_MECHANISMS:
                continue
            foreign = [o for o in objs if o != cap_obj and not (object_clusters(o, vocab) <= cap_clusters)]
            if foreign:
                coupling_options.append((n, foreign[0]))
        for coupling, dep_obj in sorted(coupling_options, key=lambda x: _role_strength(x[0], "coupling"), reverse=True)[:4]:
            dep_clusters = object_clusters(dep_obj, vocab)
            if not dep_clusters:
                continue
            exposure_rows = [n for n in primary if (_touches(n, dep_obj) or set(n.get("_clusters") or []) & dep_clusters) and (clean(n.get("direction")) in {"contracts", "becomes_conditional", "becomes_contested"} or clean(n.get("mechanism")) in RESTRICTION_MECHANISMS)]
            propagation_rows = [n for n in primary if n is not commitment and n is not coupling and (set(n.get("_clusters") or []) & (cap_clusters | dep_clusters)) and clean(n.get("kind")) in {"effect", "diagnosis"}]
            role_nodes = {
                "commitment": commitment,
                "coupling": coupling,
                "propagation": _best(propagation_rows, "propagation"),
                "exposure": _best(exposure_rows, "exposure"),
            }
            missing = [r for r, n in role_nodes.items() if n is None]
            if len(missing) > 1:
                continue
            support_nodes = [n for n in role_nodes.values() if n]
            if len({clean(n.get("_record_id")) for n in support_nodes}) < min(3, len(support_nodes)) or _distinct_sources(support_nodes) < 2:
                continue
            ccluster = sorted(cap_clusters)[0] if cap_clusters else ""
            dcluster = sorted(dep_clusters)[0]
            dist, bonus, lift = distance_for(distance, ccluster, dcluster)
            strengths = {r: (_role_strength(n, r) if n else 0.0) for r, n in role_nodes.items()}
            base = 0.35*strengths["commitment"] + 0.30*strengths["coupling"] + 0.20*strengths["propagation"] + 0.15*strengths["exposure"]
            chain_objects = {cap_obj, dep_obj}
            counters = [n for n in primary if clean(n.get("mechanism")) in ABSORBERS and any(_touches(n, o) for o in chain_objects)]
            penalty = min(12, 3 * len({clean(n.get("_record_id")) for n in counters}))
            trigger = _best([n for n in primary if (_touches(n, dep_obj) or set(n.get("_clusters") or []) & dep_clusters) and clean(n.get("mechanism")) in RESTRICTION_MECHANISMS and clean(n.get("status")) not in {"abandoned", "lapsed"}], "exposure")
            product = "risk" if trigger else "shock"
            floor_ok = all(v >= 0.40 for r, v in strengths.items() if role_nodes[r] is not None)
            pathway_score = max(0, min(99, round(100 * base * bonus) - penalty))
            meta = (vocab.get("objects") or {}).get(cap_obj, {})
            consequence = {"flagship":1.0,"capability":0.9,"rule":0.8,"budget":0.8}.get(meta.get("stake_class"),0.6)
            absorbers = [n for n in counters if clean(n.get("status")) not in {"abandoned", "lapsed"}]
            if any(clean(n.get("status")) in {"operating", "in_force", "adopted"} for n in absorbers): speed = 0.6
            elif absorbers: speed = 0.8
            else: speed = 1.0
            shock_score = max(0, min(99, round(100 * base * consequence * speed) - penalty))
            # Object-level endpoint novelty across current + historical claims.
            endpoint_joint = len({clean(n.get("_record_id")) for n in nodes if _touches(n, cap_obj) and _touches(n, dep_obj)})
            wow = 5 if endpoint_joint == 0 and dist == "distant" else 4 if endpoint_joint <= 1 else 3 if endpoint_joint <= 5 else 2
            candidate_score = shock_score if product == "shock" else pathway_score
            threshold = 60 if product == "shock" else 80
            out.append({
                "level": 5, "grammar_id": "dependency_pathway", "product": product,
                "capability_object": cap_obj, "dependency_object": dep_obj,
                "distance": dist, "distance_lift": lift, "distance_bonus": bonus,
                "roles": {r: _snap(n, r) for r, n in role_nodes.items()}, "missing_roles": missing,
                "counter_claim_ids": sorted({clean(n.get("claim_id")) for n in counters if clean(n.get("claim_id"))}),
                "counter_penalty": penalty, "pathway_score": pathway_score, "shock_score": shock_score if product == "shock" else None,
                "score": candidate_score, "floor_ok": floor_ok, "wow_preliminary": wow,
                "score_gate_passes": not missing and floor_ok and candidate_score >= threshold,
                "publication_gate_passes": False,
                "publication_gate_reason": "Shadow only: executed falsifier and oddity/watchability gates are not yet recorded by the live scanner.",
            })
    # stable dedupe by endpoint/product, keep strongest
    best: dict[tuple[str,str,str], dict[str, Any]] = {}
    for c in out:
        key=(c["product"],c["capability_object"],c["dependency_object"])
        if key not in best or (c["score"], -len(c["missing_roles"])) > (best[key]["score"], -len(best[key]["missing_roles"])):
            best[key]=c
    return sorted(best.values(), key=lambda c: (c["score_gate_passes"], c["score"], c["wow_preliminary"]), reverse=True)[:80]


def conflicting_criteria(nodes: Iterable[dict[str, Any]], distance: dict[str, Any]) -> list[dict[str, Any]]:
    primary = [n for n in nodes if n.get("_primary") and clean(n.get("era")) == "current"]
    by_obj: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in primary:
        by_obj[clean(n.get("object"))].append(n)
    out=[]
    for obj, rows in by_obj.items():
        a = [n for n in rows if clean(n.get("direction")) == "expands" and clean(n.get("kind")) in {"action","diagnosis"}]
        b = [n for n in rows if clean(n.get("direction")) in {"contracts","becomes_conditional"} and clean(n.get("kind")) in {"action","diagnosis"}]
        gap = [n for n in rows if clean(n.get("direction")) == "becomes_contested" and clean(n.get("kind")) == "diagnosis"]
        divergence = [n for n in rows if clean(n.get("kind")) in {"effect","diagnosis"} and clean(n.get("direction")) in {"becomes_contested","contracts","becomes_conditional"}]
        roles={"criterion_a":_best(a,"criterion_a"),"criterion_b":_best(b,"criterion_b"),"arbitration_gap":_best(gap,"arbitration_gap"),"divergence":_best(divergence,"divergence")}
        missing=[r for r,n in roles.items() if not n]
        if len(missing)>1: continue
        support=[n for n in roles.values() if n]
        if len({clean(n.get('_record_id')) for n in support})<3 or _distinct_sources(support)<2: continue
        strengths={r:(_role_strength(n,r) if n else 0.0) for r,n in roles.items()}
        base=.30*strengths['criterion_a']+.30*strengths['criterion_b']+.20*strengths['arbitration_gap']+.20*strengths['divergence']
        clusters=set().union(*(set(n.get('_clusters') or []) for n in support))
        # Same-object tension is familiar by construction unless its secondary clusters are distant.
        bonus=1.0; dist='familiar'; lift=math.inf
        if len(clusters)>=2:
            pair=min(itertools.combinations(sorted(clusters),2),key=lambda p: distance_for(distance,*p)[1],default=None)
            if pair: dist,bonus,lift=distance_for(distance,*pair)
        counters=[n for n in primary if clean(n.get('object'))==obj and clean(n.get('mechanism')) in ABSORBERS]
        penalty=min(12,3*len({clean(n.get('_record_id')) for n in counters}))
        score=max(0,min(99,round(100*base*bonus)-penalty))
        floor_ok=all(v>=.40 for r,v in strengths.items() if roles[r])
        out.append({"level":5 if dist!='familiar' else 4,"grammar_id":"conflicting_criteria","product":"risk","object":obj,"roles":{r:_snap(n,r) for r,n in roles.items()},"missing_roles":missing,"distance":dist,"distance_lift":lift,"distance_bonus":bonus,"score":score,"counter_penalty":penalty,"floor_ok":floor_ok,"score_gate_passes":not missing and floor_ok and score>=80,"publication_gate_passes":False,"publication_gate_reason":"Shadow only: no executed falsifier ledger yet."})
    return sorted(out,key=lambda c:(c['score_gate_passes'],c['score']),reverse=True)[:60]



def claim_expressiveness(nodes: Iterable[dict[str, Any]]) -> dict[str, Any]:
    current = [n for n in nodes if clean(n.get("era")) == "current"]
    primary = [n for n in current if n.get("_primary")]
    mech = Counter(clean(n.get("mechanism")) for n in primary)
    secondary = sum(1 for n in primary if n.get("secondary_objects"))
    relational = sum(1 for n in primary if clean(n.get("mechanism")) in COUPLING_MECHANISMS)
    c_primary = [n for n in primary if n.get("_collection") == "strand_c"]
    action_cue = re.compile(r"\b(?:adopted|took effect|entered into force|enacted|opened|launched|proposes?|signed|establish(?:ed|ing)|fund(?:s|ed|ing)|awarded|selected|announced|approved|introduced|implemented|joined)\b", re.I)
    suspicious_c_diagnosis = [n for n in current if n.get("_collection") == "strand_c" and clean(n.get("kind")) == "diagnosis" and action_cue.search(clean(n.get("_deep_main")))]
    assesses_share = (mech.get("assesses", 0) / len(primary)) if primary else 0.0
    secondary_share = (secondary / len(primary)) if primary else 0.0
    warnings=[]
    if assesses_share > 0.60:
        warnings.append("More than 60% of current primary claims use mechanism=assesses; relation grammars may be under-expressed.")
    if secondary_share < 0.10:
        warnings.append("Fewer than 10% of current primary claims carry secondary_objects; multi-object graph expansion may be sparse.")
    if len(suspicious_c_diagnosis) > 0:
        warnings.append("Some Strand C diagnosis claims contain explicit event/action cues in the Deep Scan main finding and need semantic review before detector switch.")
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
    criteria = conflicting_criteria(nodes, distance)
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
            "Stage 5 implements the distance table plus corroboration, selected Level-3 shapes, opposing-movement discovery, dependency_pathway and conflicting_criteria. Remaining A-3 grammars are added before any detector switch.",
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
