#!/usr/bin/env python3
"""One-time downstream evidence-ancestry retrace after corpus revalidation.

This tool intentionally does not discover or revalidate evidence on the network. It treats the
current saved evidence collections as authoritative, then rebuilds all stored downstream
analytical registries from that evidence base under the repository's current inference rules.

Normal scanner persistence is valuable during ordinary scans, but inappropriate for this one-time
operation: an old inference must not survive merely because its ID existed before corpus cleanup.
This script therefore bootstraps fresh downstream state from the current corpus, compares that
state with the pre-retrace registries for audit purposes, archives retired objects, and fails closed
if any active evidence reference does not resolve to an eligible surviving record.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import scripts.high_order_inference as high_order
import scripts.shock_inference as shocks
import scripts.scan_radar as scanner

TOOL_VERSION = "v1.0-current-downstream-rules"
ACTIVE_EVIDENCE_KEYS = ("strand_a", "strand_c", "frontier_evidence", "historical_context")
STRATEGIC_SOURCE_KEYS = ("strand_a", "strand_c", "frontier_evidence")
SHOCK_MIN_SCORE = 80  # mirrors refresh_shock_inference's admission threshold for a genuinely new shock


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def low(value: Any) -> str:
    return clean(value).lower()


def sha1_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def rows(data: dict[str, Any], keys: Iterable[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key in keys:
        xs = data.get(key, [])
        if isinstance(xs, list):
            out.extend(x for x in xs if isinstance(x, dict))
    return out


def evidence_aliases(item: dict[str, Any]) -> set[str]:
    """Return every identity spelling used by the current downstream engines."""
    aliases: set[str] = set()
    try:
        aliases.add(high_order._identity(item))
    except Exception:
        pass
    try:
        aliases.add(shocks._identity(item))
    except Exception:
        pass
    try:
        sid = scanner.strategic_pathway_identity(item)
        if sid:
            aliases.add(sid)
    except Exception:
        pass
    link = clean(item.get("link") or item.get("url"))
    if link:
        aliases.add("url:" + link.lower().rstrip("/"))
    return {x for x in aliases if x}


def evidence_index(data: dict[str, Any]) -> tuple[set[str], dict[str, dict[str, Any]]]:
    valid: set[str] = set()
    by_alias: dict[str, dict[str, Any]] = {}
    for key in ACTIVE_EVIDENCE_KEYS:
        for item in data.get(key, []) if isinstance(data.get(key), list) else []:
            if not isinstance(item, dict):
                continue
            for alias in evidence_aliases(item):
                valid.add(alias)
                by_alias.setdefault(alias, item)
    return valid, by_alias


def support_refs_from_object(kind: str, obj: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if kind in {"strategic_pathway", "possible_external_shock"}:
        ident = scanner.strategic_pathway_identity(obj)
        if ident:
            refs.append({
                "field": "source_record",
                "identity": ident,
                "title": clean(obj.get("title") or obj.get("headline")),
                "strand": clean(obj.get("evidence_role")),
            })
        return refs
    fields = ("support", "against", "prevention_evidence") if kind == "shock" else ("support", "context", "against")
    if kind not in {"shock", "high_order"}:
        return refs
    for field in fields:
        vals = obj.get(field, [])
        if not isinstance(vals, list):
            continue
        for snap in vals:
            if not isinstance(snap, dict):
                continue
            ident = clean(snap.get("identity"))
            if ident:
                refs.append({"field": field, "identity": ident, "title": clean(snap.get("title")), "strand": clean(snap.get("strand"))})
    return refs


def active_objects(data: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    out: list[tuple[str, str, dict[str, Any]]] = []
    shock_state = data.get("shock_inference") if isinstance(data.get("shock_inference"), dict) else {}
    for obj in shock_state.get("dynamic_shocks", []) if isinstance(shock_state.get("dynamic_shocks"), list) else []:
        if isinstance(obj, dict) and clean(obj.get("id")):
            out.append(("shock", clean(obj.get("id")), obj))
    high_state = data.get("high_order_inference") if isinstance(data.get("high_order_inference"), dict) else {}
    for obj in high_state.get("candidates", []) if isinstance(high_state.get("candidates"), list) else []:
        if isinstance(obj, dict) and clean(obj.get("id")):
            out.append(("high_order", clean(obj.get("id")), obj))
    for obj in data.get("strategic_pathways", []) if isinstance(data.get("strategic_pathways"), list) else []:
        if isinstance(obj, dict):
            ident = scanner.strategic_pathway_identity(obj)
            if ident:
                out.append(("strategic_pathway", ident, obj))
    for obj in data.get("external_shock_watch", []) if isinstance(data.get("external_shock_watch"), list) else []:
        if isinstance(obj, dict):
            ident = scanner.strategic_pathway_identity(obj)
            if ident:
                out.append(("possible_external_shock", ident, obj))
    return out


def current_orphans(data: dict[str, Any]) -> list[dict[str, Any]]:
    valid, _ = evidence_index(data)
    out: list[dict[str, Any]] = []
    for kind, oid, obj in active_objects(data):
        if kind in {"shock", "high_order"}:
            for ref in support_refs_from_object(kind, obj):
                if ref["identity"] not in valid:
                    out.append({"kind": kind, "object_id": oid, **ref})
        elif kind in {"strategic_pathway", "possible_external_shock"}:
            if not (evidence_aliases(obj) & valid):
                for ref in support_refs_from_object(kind, obj) or [{"field":"source_record","identity":oid,"title":object_title(kind,obj),"strand":""}]:
                    out.append({"kind": kind, "object_id": oid, **ref})
    # Publication pointers are downstream-to-downstream links, but audit them too.
    high_state = data.get("high_order_inference") if isinstance(data.get("high_order_inference"), dict) else {}
    candidates = {clean(x.get("id")): x for x in high_state.get("candidates", []) if isinstance(x, dict) and clean(x.get("id"))}
    pubs = high_state.get("publications") if isinstance(high_state.get("publications"), dict) else {}
    for product, ids in pubs.items():
        if not isinstance(ids, list):
            continue
        for cid in ids:
            cid = clean(cid)
            c = candidates.get(cid)
            if c is None or c.get("status") != "qualified" or not c.get("reader_eligible"):
                out.append({
                    "kind": "reader_publication",
                    "object_id": f"{product}:{cid}",
                    "field": "candidate_id",
                    "identity": cid,
                    "title": clean((c or {}).get("reader_title")),
                    "strand": "",
                })
    return out


def latest_revalidation_report(root: Path) -> Path | None:
    report_dir = root / "revalidation-reports"
    if not report_dir.exists():
        return None
    files = sorted(report_dir.glob("full-corpus-revalidation-*.json"))
    return files[-1] if files else None


def decision_aliases(decision: dict[str, Any]) -> set[str]:
    pseudo = {
        "title": decision.get("title"),
        "headline": decision.get("title"),
        "source": decision.get("source"),
        "date": decision.get("date"),
        "link": decision.get("link"),
    }
    return evidence_aliases(pseudo)


def load_revalidation_changes(path: Path | None) -> dict[str, Any]:
    result = {
        "report": str(path.relative_to(ROOT)) if path and path.exists() else "",
        "removed_aliases": set(),
        "removed_a_aliases": set(),
        "reclassified_aliases": set(),
        "removed_items": {},
        "reclassified_items": {},
    }
    if not path or not path.exists():
        return result
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return result
    for dec in report.get("decisions", []) if isinstance(report.get("decisions"), list) else []:
        if not isinstance(dec, dict):
            continue
        aliases = decision_aliases(dec)
        decision = clean(dec.get("decision"))
        origin = clean(dec.get("origin_strand")).upper()
        target = clean(dec.get("target_strand")).upper()
        info = {
            "title": clean(dec.get("title")),
            "source": clean(dec.get("source")),
            "date": clean(dec.get("date")),
            "link": clean(dec.get("link")),
            "origin_strand": origin,
            "target_strand": target,
            "reason_code": clean(dec.get("reason_code")),
        }
        if decision == "remove":
            result["removed_aliases"].update(aliases)
            if origin == "A":
                result["removed_a_aliases"].update(aliases)
            for a in aliases:
                result["removed_items"].setdefault(a, info)
        elif target and origin and target != origin:
            result["reclassified_aliases"].update(aliases)
            for a in aliases:
                result["reclassified_items"].setdefault(a, info)
    return result


def _strip_runtime(value: Any) -> Any:
    if isinstance(value, dict):
        drop = {
            "new_this_scan", "updated_this_scan", "touched_this_scan", "first_seen_at", "last_updated_at",
            "first_inferred_at", "last_updated_at", "fingerprint", "lifecycle", "retrace_status", "retrace_at",
        }
        return {k: _strip_runtime(v) for k, v in value.items() if k not in drop}
    if isinstance(value, list):
        return [_strip_runtime(x) for x in value]
    return value


def formulation_signature(kind: str, obj: dict[str, Any]) -> Any:
    if kind == "shock":
        return [clean(obj.get(k)) for k in ("title", "plainly", "second_order", "why_easy_to_miss")]
    if kind == "high_order":
        return [clean(obj.get(k)) for k in ("product", "grammar_id", "topic_key", "reader_title", "reader_summary")]
    if kind == "strategic_pathway":
        c = obj.get("strategic_classification") if isinstance(obj.get("strategic_classification"), dict) else {}
        lenses = []
        for lens in c.get("lenses", []) if isinstance(c.get("lenses"), list) else []:
            if isinstance(lens, dict):
                lenses.append([clean(lens.get("type")), clean(lens.get("shock_family_id")), clean(lens.get("transition_key")), clean(lens.get("passage"))])
        return [clean(obj.get("title")), clean(c.get("primary")), lenses]
    if kind == "possible_external_shock":
        w = obj.get("shock_watch") if isinstance(obj.get("shock_watch"), dict) else {}
        return [clean(obj.get("title")), clean(w.get("shock_family_id")), clean(w.get("passage")), sorted(clean(x) for x in (w.get("missing_tests") or []))]
    return _strip_runtime(obj)


def evidence_signature(kind: str, obj: dict[str, Any]) -> Any:
    if kind in {"shock", "high_order"}:
        return sorted((r["field"], r["identity"]) for r in support_refs_from_object(kind, obj))
    if kind in {"strategic_pathway", "possible_external_shock"}:
        return sorted(evidence_aliases(obj))
    return []


def status_score_signature(kind: str, obj: dict[str, Any]) -> Any:
    if kind == "shock":
        return [obj.get("inference_score"), obj.get("coupling_count"), obj.get("primary_source_count"), obj.get("official_trigger_present")]
    if kind == "high_order":
        return [obj.get("status"), obj.get("score"), obj.get("primary_role_coverage"), obj.get("reader_eligible")]
    if kind == "strategic_pathway":
        return [obj.get("evidence_role"), obj.get("analytical_weight"), obj.get("context_only")]
    return [obj.get("status")]


def object_title(kind: str, obj: dict[str, Any]) -> str:
    return clean(obj.get("title") or obj.get("reader_title") or obj.get("topic_label") or obj.get("headline") or obj.get("id") or kind)


def rebuild_strategic(data: dict[str, Any], previous: dict[str, Any], now: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = rows(data, STRATEGIC_SOURCE_KEYS)
    old_paths = previous.get("strategic_pathways", []) if isinstance(previous.get("strategic_pathways"), list) else []
    paths = scanner.build_strategic_pathway_corpus(
        [], candidates, old_paths, now, data.get("strand_a", []) if isinstance(data.get("strand_a"), list) else []
    )
    old_ids = {scanner.strategic_pathway_identity(x) for x in old_paths if isinstance(x, dict)}
    for item in paths:
        sid = scanner.strategic_pathway_identity(item)
        item["new_this_scan"] = bool(sid and sid not in old_ids)
    old_watch = previous.get("external_shock_watch", []) if isinstance(previous.get("external_shock_watch"), list) else []
    watch = scanner.build_external_shock_watch(
        [], candidates, paths, now, data.get("strand_a", []) if isinstance(data.get("strand_a"), list) else []
    )
    old_watch_ids = {scanner.strategic_pathway_identity(x) for x in old_watch if isinstance(x, dict)}
    for item in watch:
        sid = scanner.strategic_pathway_identity(item)
        item["new_this_scan"] = bool(sid and sid not in old_watch_ids)
    return paths, watch


def rebuild_shocks(data: dict[str, Any], previous: dict[str, Any], now: str) -> dict[str, Any]:
    # _candidate is scan-triggered, so for the one-time whole-corpus replay every current,
    # non-historical row is temporarily marked touched. Evidence role/weight remains unchanged;
    # C stays capped at 0.30 and history is forced non-fresh by shocks._rows.
    replay = copy.deepcopy(data)
    for key in ("strand_a", "strand_c", "strategic_pathways", "frontier_evidence"):
        for item in replay.get(key, []) if isinstance(replay.get(key), list) else []:
            if isinstance(item, dict):
                item["new_this_scan"] = True
    replay_rows = shocks._rows(replay)
    detected: list[dict[str, Any]] = []
    for asset_id in shocks.ASSETS:
        for pressure_id in shocks.PRESSURES:
            candidate = shocks._candidate(asset_id, pressure_id, replay_rows)
            if not candidate or int(candidate.get("inference_score", 0) or 0) < SHOCK_MIN_SCORE:
                continue
            # Remove replay-only freshness language from the saved ancestry.
            for snap in candidate.get("support", []) if isinstance(candidate.get("support"), list) else []:
                if not isinstance(snap, dict):
                    continue
                if clean(snap.get("role")) == "New primary coupling evidence":
                    snap["role"] = "Primary coupling evidence"
                elif clean(snap.get("role")) == "New primary evidence":
                    snap["role"] = "Primary evidence"
                snap["new_this_scan"] = False
            for field in ("against", "prevention_evidence"):
                for snap in candidate.get(field, []) if isinstance(candidate.get(field), list) else []:
                    if isinstance(snap, dict):
                        snap["new_this_scan"] = False
            candidate["fresh_coupling"] = False
            candidate["fresh_context"] = False
            detected.append(candidate)

    # Stable order, no arbitrary top-6 cap: this is a full-corpus replay, not a single scan's novelty list.
    detected.sort(key=lambda x: (int(x.get("inference_score", 0)), int(x.get("best_quality", 0)), clean(x.get("id"))), reverse=True)
    old_list = ((previous.get("shock_inference") or {}).get("dynamic_shocks", [])
                if isinstance(previous.get("shock_inference"), dict) else [])
    old_by_id = {clean(x.get("id")): x for x in old_list if isinstance(x, dict) and clean(x.get("id"))}
    for candidate in detected:
        cid = clean(candidate.get("id"))
        old = old_by_id.get(cid, {})
        candidate["first_inferred_at"] = clean(old.get("first_inferred_at")) or now
        candidate["last_updated_at"] = now
        candidate["fingerprint"] = shocks._fingerprint(candidate)
        candidate["new_this_scan"] = cid not in old_by_id
        candidate["updated_this_scan"] = cid in old_by_id and evidence_signature("shock", old) != evidence_signature("shock", candidate)
        candidate["status"] = "new" if cid not in old_by_id else ("updated" if candidate["updated_this_scan"] else "unchanged")
    return {
        "profile_version": shocks.PROFILE_VERSION,
        "evaluated_at": now,
        "new_count": sum(1 for x in detected if x.get("status") == "new"),
        "updated_count": sum(1 for x in detected if x.get("status") == "updated"),
        "unchanged_count": sum(1 for x in detected if x.get("status") == "unchanged"),
        "dynamic_shocks": detected,
    }


def rebuild_high_order(data: dict[str, Any], now: str) -> dict[str, Any]:
    # Empty previous state is intentional: persistence/hysteresis must not preserve a candidate
    # that the cleaned corpus no longer detects. The detector itself can still infer new IDs.
    return high_order.refresh_high_order_inference(data, {}, now)


def map_objects(data: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(kind, oid): obj for kind, oid, obj in active_objects(data)}


def classify_changes(before: dict[str, Any], after: dict[str, Any], revalidation: dict[str, Any], now: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    old = map_objects(before)
    new = map_objects(after)
    audit: list[dict[str, Any]] = []
    retired_archive: list[dict[str, Any]] = []
    changed_a_shocks: list[dict[str, Any]] = []

    removed_a = revalidation.get("removed_a_aliases") or set()
    removed_all = revalidation.get("removed_aliases") or set()
    reclassified = revalidation.get("reclassified_aliases") or set()

    for key in sorted(old.keys() | new.keys()):
        kind, oid = key
        old_obj = old.get(key)
        new_obj = new.get(key)
        old_refs = support_refs_from_object(kind, old_obj) if old_obj else []
        new_refs = support_refs_from_object(kind, new_obj) if new_obj else []
        old_ref_ids = {x["identity"] for x in old_refs}
        new_ref_ids = {x["identity"] for x in new_refs}
        removed_refs = sorted(old_ref_ids & removed_all)
        reclass_refs = sorted(old_ref_ids & reclassified)
        removed_a_refs = sorted(old_ref_ids & removed_a)

        if old_obj is None and new_obj is not None:
            retrace_status = "newly_inferred"
        elif new_obj is None and old_obj is not None:
            retrace_status = "retired"
        else:
            assert old_obj is not None and new_obj is not None
            formulation_changed = formulation_signature(kind, old_obj) != formulation_signature(kind, new_obj)
            evidence_changed = evidence_signature(kind, old_obj) != evidence_signature(kind, new_obj)
            score_changed = status_score_signature(kind, old_obj) != status_score_signature(kind, new_obj)
            if formulation_changed:
                retrace_status = "materially_rewritten"
            elif evidence_changed or score_changed:
                retrace_status = "rebuilt"
            else:
                retrace_status = "unchanged"

        entry = {
            "kind": kind,
            "id": oid,
            "title": object_title(kind, new_obj or old_obj or {}),
            "retrace_status": retrace_status,
            "previous_status": clean((old_obj or {}).get("status")),
            "current_status": clean((new_obj or {}).get("status")),
            "previous_score": (old_obj or {}).get("inference_score", (old_obj or {}).get("score")),
            "current_score": (new_obj or {}).get("inference_score", (new_obj or {}).get("score")),
            "previous_evidence_refs": len(old_refs),
            "current_evidence_refs": len(new_refs),
            "removed_evidence_refs_detected": removed_refs,
            "reclassified_evidence_refs_detected": reclass_refs,
            "evidence_refs_removed_from_chain": sorted(old_ref_ids - new_ref_ids),
            "evidence_refs_added_to_chain": sorted(new_ref_ids - old_ref_ids),
        }
        audit.append(entry)

        if new_obj is not None:
            new_obj["retrace_status"] = retrace_status
            new_obj["retrace_at"] = now
        if retrace_status == "retired" and old_obj is not None:
            retired_archive.append({
                "kind": kind,
                "id": oid,
                "title": object_title(kind, old_obj),
                "retrace_status": "retired",
                "retired_at": now,
                "reason": "Current cleaned evidence no longer satisfies the repository's current construction threshold for this downstream object.",
                "previous_object": old_obj,
            })
        if kind == "shock" and old_obj is not None and removed_a_refs and (new_obj is None or old_ref_ids != new_ref_ids):
            changed_a_shocks.append({
                "id": oid,
                "title": object_title(kind, new_obj or old_obj),
                "retrace_status": retrace_status,
                "removed_a_support": [revalidation.get("removed_items", {}).get(x, {"identity": x}) for x in removed_a_refs],
                "replacement_support_added": [
                    {"identity": r["identity"], "title": r["title"], "field": r["field"]}
                    for r in new_refs if r["identity"] in (new_ref_ids - old_ref_ids)
                ],
            })

    return audit, retired_archive, changed_a_shocks


def publication_audit(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    def slots(doc: dict[str, Any]) -> set[tuple[str, str]]:
        state = doc.get("high_order_inference") if isinstance(doc.get("high_order_inference"), dict) else {}
        pubs = state.get("publications") if isinstance(state.get("publications"), dict) else {}
        return {(clean(product), clean(cid)) for product, ids in pubs.items() if isinstance(ids, list) for cid in ids if clean(cid)}
    old = slots(before); new = slots(after)
    out = []
    for product, cid in sorted(old | new):
        status = "unchanged" if (product, cid) in old and (product, cid) in new else ("newly_inferred" if (product, cid) in new else "retired")
        out.append({"kind": "reader_publication", "product": product, "id": cid, "retrace_status": status})
    return out


def markdown_report(report: dict[str, Any]) -> str:
    d = report["diagnostics"]
    lines = [
        "# ONE-TIME Downstream Retrace",
        "",
        f"Completed: `{report['completed_at']}`",
        f"Tool version: `{report['tool_version']}`",
        f"Source revalidation report: `{report.get('source_revalidation_report') or 'not found'}`",
        "",
        "## Final diagnostics",
        "",
        f"- Derived objects checked: **{d['derived_objects_checked']}**",
        f"- Unchanged: **{d['unchanged']}**",
        f"- Rebuilt: **{d['rebuilt']}**",
        f"- Materially rewritten: **{d['materially_rewritten']}**",
        f"- Newly inferred: **{d['newly_inferred']}**",
        f"- Retired: **{d['retired']}**",
        f"- Stale evidence-reference occurrences removed: **{d['stale_evidence_references_removed']}**",
        f"- Orphan references remaining: **{d['orphan_references_remaining']}**",
        f"- Shock support chains changed because an A-item disappeared: **{d['shock_support_chains_changed_after_a_removal']}**",
        "",
        "## Evidence hierarchy checks",
        "",
        "- Strand B remains excluded from shock and Level-4/5 primary inference.",
        "- Strand C remains contextual/weak-signal evidence capped at analytical weight 0.30 and cannot close a primary shock or higher-order role.",
        "- Historical evidence remains contextual and cannot replace a required current primary trigger.",
        "- Reader publication pointers were regenerated from the newly rebuilt candidate registry.",
        "",
        "## Active state after retrace",
        "",
        f"- Dynamic shocks: **{d['active_dynamic_shocks']}**",
        f"- High-order candidates: **{d['active_high_order_candidates']}**",
        f"- Strategic pathways: **{d['active_strategic_pathways']}**",
        f"- Possible external shocks: **{d['active_possible_external_shocks']}**",
        f"- Standalone stored matrix registry objects: **{d['standalone_matrix_objects']}**",
        "",
    ]
    if report.get("shock_support_chains_changed_after_a_removal"):
        lines.extend(["## Shock chains affected by removed Strand-A evidence", ""])
        for x in report["shock_support_chains_changed_after_a_removal"]:
            lines.append(f"- `{x['id']}` — **{x['retrace_status']}**")
        lines.append("")
    lines.extend([
        "The complete per-object audit trail is in the paired JSON report. Retired objects are also copied into `radar.json` under `downstream_archive` and are not treated as active analytical products.",
        "",
    ])
    return "\n".join(lines)


def retrace_document(data: dict[str, Any], *, now: str, revalidation_report: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    before = copy.deepcopy(data)
    before_orphans = current_orphans(before)
    revalidation = load_revalidation_changes(revalidation_report)

    # Rebuild direct strategic classifications first because the shock engine may read them.
    paths, watch = rebuild_strategic(data, before, now)
    data["strategic_pathways"] = paths
    data["external_shock_watch"] = watch
    data["shock_inference"] = rebuild_shocks(data, before, now)
    data["high_order_inference"] = rebuild_high_order(data, now)

    audit, retired, changed_a_shocks = classify_changes(before, data, revalidation, now)
    pub_audit = publication_audit(before, data)
    audit.extend(pub_audit)

    # Recalculate category totals after publication-slot audit is included.
    counts = Counter(x["retrace_status"] for x in audit)
    after_orphans = current_orphans(data)
    if after_orphans:
        sample = "; ".join(f"{x['kind']} {x['object_id']} -> {x['identity']}" for x in after_orphans[:6])
        raise RuntimeError(f"Final downstream integrity check failed: {len(after_orphans)} orphan reference(s) remain. {sample}")

    prior_archive = data.get("downstream_archive") if isinstance(data.get("downstream_archive"), dict) else {}
    old_archived = prior_archive.get("objects", []) if isinstance(prior_archive.get("objects"), list) else []
    data["downstream_archive"] = {
        "profile_version": TOOL_VERSION,
        "updated_at": now,
        "objects": old_archived + retired,
    }

    active_ref_count = 0
    for kind, _oid, obj in active_objects(data):
        active_ref_count += len(support_refs_from_object(kind, obj))

    diagnostics = {
        "derived_objects_checked": len(audit),
        "unchanged": counts.get("unchanged", 0),
        "rebuilt": counts.get("rebuilt", 0),
        "materially_rewritten": counts.get("materially_rewritten", 0),
        "newly_inferred": counts.get("newly_inferred", 0),
        "retired": counts.get("retired", 0),
        "stale_evidence_references_before": len(before_orphans),
        "stale_evidence_references_removed": len(before_orphans),
        "orphan_references_remaining": len(after_orphans),
        "active_evidence_reference_occurrences_checked": active_ref_count,
        "shock_support_chains_changed_after_a_removal": len(changed_a_shocks),
        "active_dynamic_shocks": len((data.get("shock_inference") or {}).get("dynamic_shocks", [])),
        "active_high_order_candidates": len((data.get("high_order_inference") or {}).get("candidates", [])),
        "active_strategic_pathways": len(data.get("strategic_pathways", [])),
        "active_possible_external_shocks": len(data.get("external_shock_watch", [])),
        "standalone_matrix_objects": len(data.get("matrices", [])) if isinstance(data.get("matrices"), list) else 0,
        "removed_evidence_decision_refs_seen_in_previous_downstream": sum(
            1 for x in before_orphans if x.get("identity") in (revalidation.get("removed_aliases") or set())
        ),
        "reclassified_evidence_decision_refs_seen_in_previous_downstream": sum(
            1 for kind, _oid, obj in active_objects(before)
            for ref in support_refs_from_object(kind, obj)
            if ref.get("identity") in (revalidation.get("reclassified_aliases") or set())
        ),
    }
    report = {
        "tool": "ONE-TIME Downstream Retrace",
        "tool_version": TOOL_VERSION,
        "completed_at": now,
        "source_revalidation_report": revalidation.get("report", ""),
        "diagnostics": diagnostics,
        "object_audit": audit,
        "shock_support_chains_changed_after_a_removal": changed_a_shocks,
        "orphan_references_before": before_orphans,
        "orphan_references_after": after_orphans,
        "integrity_check": {
            "passed": not after_orphans,
            "requirement": "zero active downstream objects reference evidence absent from the eligible surviving corpus",
        },
    }
    data["downstream_retrace"] = {
        "tool_version": TOOL_VERSION,
        "completed_at": now,
        "source_revalidation_report": revalidation.get("report", ""),
        "diagnostics": diagnostics,
        "integrity_passed": True,
    }
    if isinstance(data.get("reader_products_refresh"), dict):
        data["reader_products_refresh"]["completed_at"] = now
        data["reader_products_refresh"]["shock_inference"] = True
        data["reader_products_refresh"]["high_order_inference"] = True
        data["reader_products_refresh"]["strategic_pathways"] = True
        data["reader_products_refresh"]["risks_opportunities"] = True
        data["reader_products_refresh"]["external_shocks"] = True
        data["reader_products_refresh"]["matrix"] = True
        data["reader_products_refresh"]["read_at_least_this"] = True
    if isinstance(data.get("full_corpus_revalidation"), dict):
        data["full_corpus_revalidation"]["higher_order_reasoning_rebuilt"] = True
        data["full_corpus_revalidation"]["downstream_retrace_completed_at"] = now
    return data, report


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--radar", default="radar.json", help="Path to the cleaned radar.json")
    ap.add_argument("--report-json", default="", help="Write the complete JSON audit here")
    ap.add_argument("--report-md", default="", help="Write a plain-language Markdown summary here")
    ap.add_argument("--revalidation-report", default="", help="Optional full-corpus revalidation JSON; newest repository report is used by default")
    ap.add_argument("--now", default="", help="Override completion timestamp (tests only)")
    ap.add_argument("--check-only", action="store_true", help="Rebuild and validate in memory without writing radar.json")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    radar_path = Path(args.radar)
    data = json.loads(radar_path.read_text(encoding="utf-8"))
    now = clean(args.now) or utc_now()
    rev = Path(args.revalidation_report) if clean(args.revalidation_report) else latest_revalidation_report(ROOT)
    rebuilt, report = retrace_document(data, now=now, revalidation_report=rev)

    if not args.check_only:
        radar_path.write_text(json.dumps(rebuilt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if clean(args.report_json):
        p = Path(args.report_json); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if clean(args.report_md):
        p = Path(args.report_md); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(markdown_report(report), encoding="utf-8")

    print(json.dumps(report["diagnostics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
