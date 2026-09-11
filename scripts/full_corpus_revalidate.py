#!/usr/bin/env python3
"""One-time retrospective revalidation of the accepted Radar evidence corpus.

This is deliberately *not* a discovery scan.  It applies the scanner's current saved-item
admission/integrity rules to already accepted/retained A/B/C evidence, supports A<->B
reclassification, removes genuine duplicates, and emits a complete audit trail.

Higher-order products (shocks, risks, opportunities, trends, phenomena, inference state) are
left byte-for-byte equivalent as Python values; only the evidence collections and explicit
revalidation metadata are changed.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.scan_radar as sr

TOOL_VERSION = "v1.2-current-scanner-rules"
AB_KEYS = ("strand_a", "strand_b", sr.AB_ARCHIVE_KEY)
C_KEYS = ("strand_c", sr.SIGNAL_ARCHIVE_KEY)
PROTECTED_HIGHER_ORDER_KEYS = (
    "strategic_pathways", "external_shock_watch", "shock_inference", "high_order_inference",
)


def clean(value: Any) -> str:
    return sr.clean_text(value)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def item_ref(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": clean(item.get("title") or item.get("headline")),
        "source": clean(item.get("source")),
        "date": clean(item.get("date")),
        "link": clean(item.get("link") or item.get("url")),
        "first_seen": clean(item.get("first_seen")),
    }


def source_kind(item: dict[str, Any]) -> str:
    return sr._saved_source_kind(item)


def source_tier(item: dict[str, Any]) -> int:
    return sr._saved_tier(item)


def _ab_gate(item: dict[str, Any], refreshed: tuple[str, str, str] | None = None) -> dict[str, Any]:
    """Run the scanner-owned saved-record gate, including document exclusions.

    A refreshed page may provide richer text, but it must not bypass the current scanner's
    hard document/URL exclusions (for example routine news/press-release landing pages).
    ``_saved_item_passes`` is therefore authoritative both before and after refresh.
    """
    if refreshed:
        title, abstract, body = (clean(x) for x in refreshed)
    else:
        title = clean(item.get("title"))
        abstract = clean(item.get("summary"))
        body = ""

    link = clean(item.get("link"))
    exclusion = sr.document_exclusion_reason(title, abstract, link) if title else "missing title"
    if exclusion:
        return {
            "a_pass": False,
            "b_pass": False,
            "document_rejected": True,
            "aboutness_reason": exclusion,
        }

    # _saved_item_passes is the scanner-owned saved-record entrypoint. Asking for A returns
    # the complete evidence dictionary, including both a_pass and b_pass.
    if refreshed:
        _ok, ev = sr._saved_item_passes(
            item, "a_pass", title=title, abstract=abstract, body=body
        )
    else:
        _ok, ev = sr._saved_item_passes(item, "a_pass")
    return ev or {}


def _a_failure_reason(ev: dict[str, Any]) -> tuple[str, str]:
    if ev.get("document_rejected"):
        return "A_DOCUMENT_EXCLUDED", clean(ev.get("aboutness_reason")) or "Current A/B document-type exclusion rejected the record."
    if ev.get("language_rejected"):
        return "A_LANGUAGE", "The available source evidence does not satisfy the scanner's English-record rule."
    eu = clean(ev.get("eu_relevance"))
    if eu not in {"direct", "member_state", "material_external"}:
        return "A_EU_SCOPE", "The current A gate does not establish substantive European/EU system scope from the source evidence."
    if not ev.get("a_focus_pass"):
        return "A_RI_FOCUS", "The current A gate does not establish substantive R&I-system focus."
    if not ev.get("aboutness_pass"):
        reason = clean(ev.get("aboutness_reason")) or "aboutness"
        return "A_ABOUTNESS", f"The current A aboutness gate failed ({reason})."
    if not ev.get("centrality_pass"):
        reason = clean(ev.get("centrality_reason")) or "centrality"
        return "A_CENTRALITY", f"European R&I is not central enough under the current A gate ({reason})."
    return "A_STRATEGIC_OR_STATE_VARIABLE", "The source does not satisfy either A route: a direct strategic/geopolitical relationship or a qualifying European R&I state variable."


def _b_failure_reason(ev: dict[str, Any]) -> tuple[str, str]:
    if ev.get("document_rejected"):
        return "B_DOCUMENT_EXCLUDED", clean(ev.get("aboutness_reason")) or "Current A/B document-type exclusion rejected the record."
    if ev.get("language_rejected"):
        return "B_LANGUAGE", "The available source evidence does not satisfy the scanner's English-record rule."
    families = ev.get("method_evidence") or ev.get("foresight_evidence") or []
    if families:
        return "B_METHOD_OBJECT", "A foresight/futures family is present, but the method itself is not sufficiently developed, tested, evaluated, compared, validated, criticised, or otherwise studied under the current B contract."
    return "B_NOT_GENUINE_FORESIGHT_METHOD", "The current B gate does not identify a genuine foresight/futures methodology as an object of inquiry."


def _gate_snapshot(ev: dict[str, Any]) -> dict[str, Any]:
    return {
        "a_pass": bool(ev.get("a_pass")),
        "b_pass": bool(ev.get("b_pass")),
        "document_rejected": bool(ev.get("document_rejected")),
        "language_rejected": bool(ev.get("language_rejected")),
        "aboutness_reason": clean(ev.get("aboutness_reason")),
        "centrality_reason": clean(ev.get("centrality_reason")),
        "eu_relevance": clean(ev.get("eu_relevance")),
        "a_route": clean(ev.get("a_route")),
        "b_route": clean(ev.get("b_route")),
        "ri_evidence": list(ev.get("ri_evidence") or [])[:6],
        "geo_evidence": list(ev.get("geo_evidence") or [])[:6],
        "eu_evidence": list(ev.get("eu_evidence") or [])[:6],
        "method_evidence": list(ev.get("method_evidence") or [])[:6],
        "a_context_evidence": list(ev.get("a_context_evidence") or [])[:6],
    }


def _openalex_exact_doi_fallback(item: dict[str, Any]) -> tuple[str, str, str] | None:
    """Recover scholarly source text by exact DOI using the scanner's own helper.

    This is retrieval resilience only. Admission still goes through ``_saved_item_passes``
    and therefore uses the repository's current document, EU-scope, R&I and A/B rules.
    """
    doi = sr._snowball_seed_doi(item)
    if not doi:
        return None
    timeout = int(sr.CONFIG.get("inherited_corpus_audit_timeout_seconds", 8))
    abstract = clean(sr.openalex_abstract_by_doi(doi, timeout=timeout))
    if not abstract:
        return None
    return clean(item.get("title")), abstract, ""


def _refresh_one_ab(item: dict[str, Any]) -> tuple[str, str, str, str] | None:
    """Use the scanner's normal audit refresh, then its exact-DOI OpenAlex helper."""
    try:
        primary = sr._audit_refresh_document(item)
    except Exception:
        primary = None
    if primary:
        return (*primary, "scanner_refresh")
    fallback = _openalex_exact_doi_fallback(item)
    if fallback:
        return (*fallback, "openalex_exact_doi")
    return None

def _refresh_failed_ab(items: list[dict[str, Any]], *, workers: int, enabled: bool) -> tuple[dict[int, tuple[Any, ...] | None], dict[str, int]]:
    results: dict[int, tuple[Any, ...] | None] = {}
    stats = {
        "attempted": 0, "succeeded": 0, "unavailable": 0,
        "scanner_refresh_succeeded": 0, "openalex_exact_doi_succeeded": 0,
    }
    if not enabled or not items:
        return results, stats
    stats["attempted"] = len(items)
    with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = {ex.submit(_refresh_one_ab, item): idx for idx, item in enumerate(items)}
        for fut in cf.as_completed(futures):
            idx = futures[fut]
            try:
                val = fut.result()
            except Exception:
                val = None
            results[idx] = val
            if val:
                stats["succeeded"] += 1
                mode = clean(val[3]) if len(val) >= 4 else "scanner_refresh"
                if mode == "openalex_exact_doi":
                    stats["openalex_exact_doi_succeeded"] += 1
                else:
                    stats["scanner_refresh_succeeded"] += 1
            else:
                stats["unavailable"] += 1
    return results, stats


def _ab_origin(row: dict[str, Any], collection: str) -> str:
    if collection == "strand_a":
        return "A"
    if collection == "strand_b":
        return "B"
    raw = clean(row.get("archived_from_strand") or row.get("strand")).upper()
    return "B" if raw == "B" else "A"


def _apply_ab_evidence(item: dict[str, Any], ev: dict[str, Any], target: str) -> dict[str, Any]:
    out = dict(item)
    out["strand"] = target
    out["new_this_scan"] = False
    out["eu_relevance"] = ev.get("eu_relevance")
    out["eu_evidence"] = list(ev.get("eu_evidence") or [])
    out["ri_evidence"] = list(ev.get("ri_evidence") or [])
    out["geo_evidence"] = list(ev.get("geo_evidence") or [])
    out["text_mode"] = clean(ev.get("text_mode"))
    out["relevance_note"] = sr.relevance_note(ev, target)
    if target == "A":
        out["a_route"] = clean(ev.get("a_route"))
        out["a_context_evidence"] = list(ev.get("a_context_evidence") or [])
        out["bridge_sentence"] = clean(ev.get("bridge_sentence"))
        out["external_eu_bridge"] = clean(ev.get("external_eu_bridge"))
        out["external_eu_bridge_is_inference"] = bool(ev.get("external_eu_bridge_is_inference"))
    else:
        # Mirror the scanner's B representation: method bridge belongs in the reader note,
        # while A-only strategic bridge fields must not survive an A -> B reclassification.
        out["a_route"] = ""
        out["a_context_evidence"] = []
        out["bridge_sentence"] = clean(ev.get("method_bridge"))
        out["external_eu_bridge"] = ""
        out["external_eu_bridge_is_inference"] = False
        out["realisation_status"] = ""
        out["strategic_classification"] = {
            "primary": "", "lenses": [], "trend_context": [], "trend_action": False, "trend_action_passage": ""
        }
        out["strategic_classification_source"] = "source_text"
    return out


def _ab_identity(item: dict[str, Any]) -> str:
    return sr.identity(sr.internalize_previous(item))


def _ab_preference(item: dict[str, Any]) -> tuple[int, float, int, str]:
    internal = sr.internalize_previous(item)
    typ = sr.normalized(item.get("type", ""))
    preprint = int("preprint" in typ)
    source_rank = float(internal.get("_source_rank", 9.0))
    richness = -len(clean(item.get("summary")).split())
    return preprint, source_rank, richness, clean(item.get("first_seen")) or "9999"


def _substantive_primary_landing(item: dict[str, Any]) -> str:
    landing = sr.normalized_link(item.get("landing_page_url"))
    link = sr.normalized_link(item.get("link") or item.get("url"))
    if not landing or not link or landing == link:
        return ""
    role = sr.normalized(item.get("primary_document_role"))
    basis = sr.normalized(item.get("source_integrity_basis"))
    if role == "landing_page":
        return ""
    try:
        path = sr.normalized(sr.urlparse(link).path)
    except Exception:
        path = ""
    if basis == "institution pdf" or ".pdf" in path or "download-handler" in sr.normalized(link) or "/redirection/document/" in path:
        return landing
    return ""


def dedupe_ab(candidates: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Use the scanner's DOI/title identity plus its landing-page -> primary-object rule."""
    groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for cand in candidates:
        row = cand["item"]
        audit_index = int(cand["audit_index"])
        key = _ab_identity(row)
        groups.setdefault(key, []).append((audit_index, row))

    kept_pairs: list[tuple[int, dict[str, Any]]] = []
    for key, group in groups.items():
        if key == "title:" or len(group) == 1:
            kept_pairs.extend(group)
            continue
        group_sorted = sorted(group, key=lambda pair: _ab_preference(pair[1]))
        winner_idx, winner = group_sorted[0]
        kept_pairs.append((winner_idx, winner))
        earliest = min((clean(x.get("first_seen")) for _, x in group if clean(x.get("first_seen"))), default="")
        if earliest:
            winner["first_seen"] = earliest
        for loser_idx, loser in group_sorted[1:]:
            d = decisions[loser_idx]
            d.update({
                "decision": "duplicate_remove", "target_strand": "",
                "reason_code": "AB_DUPLICATE_IDENTITY",
                "reason": f"Duplicate evidence under the scanner's current DOI/title identity; retained {clean(winner.get('title'))!r}.",
                "duplicate_of": item_ref(winner),
            })

    # Current merge_corpus also replaces an HTML wrapper when its substantive downloadable
    # primary object is present. Apply the same relationship across all surviving A/B rows.
    landing_to_primary: dict[str, tuple[int, dict[str, Any]]] = {}
    for pair in kept_pairs:
        landing = _substantive_primary_landing(pair[1])
        if landing:
            old = landing_to_primary.get(landing)
            if old is None or _ab_preference(pair[1]) < _ab_preference(old[1]):
                landing_to_primary[landing] = pair

    final: list[dict[str, Any]] = []
    for idx, row in kept_pairs:
        link = sr.normalized_link(row.get("link") or row.get("url"))
        primary = landing_to_primary.get(link)
        if primary and primary[0] != idx:
            winner = primary[1]
            d = decisions[idx]
            d.update({
                "decision": "duplicate_remove", "target_strand": "",
                "reason_code": "AB_SUPERSEDED_LANDING_WRAPPER",
                "reason": "The current scanner treats this landing-page wrapper as navigation metadata because the substantive primary document is already retained.",
                "duplicate_of": item_ref(winner),
            })
            if clean(row.get("first_seen")) and (not clean(winner.get("first_seen")) or clean(row.get("first_seen")) < clean(winner.get("first_seen"))):
                winner["first_seen"] = clean(row.get("first_seen"))
            continue
        final.append(row)
    return final


def c_failure_reason(item: dict[str, Any]) -> tuple[str, str]:
    """Diagnostic mirror of _saved_signal_passes; that scanner function remains authoritative."""
    if sr.signal_is_retired(item):
        return "C_RETIRED", "The headline is on the scanner's current retired-signal list."
    if not sr.record_source_integrity_ok(item):
        return "C_SOURCE_INTEGRITY", "The saved signal fails the current source/document integrity rule."
    if not sr.record_date_integrity_ok(item):
        return "C_DATE_INTEGRITY", "The saved signal has no usable date or relies on a disallowed sitemap last-modified date."
    headline = clean(item.get("headline"))
    if not headline:
        return "C_NO_HEADLINE", "The saved signal has no headline."
    desc = clean(item.get("signal_note") or item.get("why_it_matters"))
    if not sr.english_record_ok(f"{headline}. {desc}", item.get("language", ""), title=headline):
        return "C_LANGUAGE", "The signal fails the current English-record rule."
    if sr.routine_signal_noise(headline, desc):
        return "C_ROUTINE_NOISE", "The source is routine activity (for example an event/job/tender/listing) rather than a weak signal."
    if "(strand b)" in sr.normalized(item.get("anchor", "")) or sr.normalized(item.get("anchor_basis", "")) == "watch-theme":
        return "C_BAD_LEGACY_ANCHOR", "The saved C row relies on a legacy Strand-B/watch-theme anchor that the current C model no longer accepts."
    source = clean(item.get("source")); link = clean(item.get("link"))
    if sr.formal_evidence_product(headline, desc, source, link):
        return "C_FORMAL_EVIDENCE_PRODUCT", "This is a completed analytical evidence product and belongs in A/B assessment, not Strand C."
    if not sr.c_date_basis_is_event_usable(item):
        return "C_EVENT_DATE_BASIS", "The C event date is approximate or derived from sitemap modification metadata rather than the event/publication itself."
    if sr.c_standing_funding_or_call_page(headline, desc, source, link):
        return "C_STANDING_CALL_PAGE", "This is a standing funding/call/application page rather than a separately identifiable current development."
    claim = sr.c_saved_source_claim(item) or desc
    relevance_ok, _rel, _hits = sr.c_source_backed_eu_ri_relevance(headline, claim, source, "", link)
    if not relevance_ok:
        return "C_NO_SOURCE_BACKED_EU_RI_EFFECT", "The source-backed claim does not establish a development capable of moving a European R&I state variable."
    themes = set(sr.themes_for(f"{headline}. {claim}")) & sr.WATCH_SIGNAL_THEMES
    if not themes and not sr.c_fallback_watch_theme(headline, claim):
        return "C_NO_RI_WATCH_THEME", "The source-backed claim does not map to a current R&I weak-signal state-variable theme."
    if sr._source_merit_is_eu_official(source, link) and not sr.institutional_weak_signal_eligible(headline, claim, source, link):
        return "C_STANDING_OFFICIAL_DEVELOPMENT", "The official page is standing/routine implementation rather than a sufficiently specific current weak signal."
    event_date = clean(item.get("c_event_date")) or sr.c_event_date(item.get("date"))
    if not event_date:
        return "C_NO_EVENT_DATE", "No usable dated event/finding can be established."
    trusted = sr.trusted_analytical_commentary_candidate(headline, claim, source, "", link)
    status = clean(item.get("event_status")).upper() or sr.signal_event_status(claim, headline, claim)
    formal_proposal = status == "PROPOSED" and sr.formal_proposal_is_public_signal(claim, headline, claim, source, link)
    actor = clean(item.get("c_event_actor")) or sr.c_event_actor(headline, claim, source)
    event_route = sr.c_public_event_route_ok(headline, claim, status, actor, formal_proposal)
    analysis_route = bool(trusted and (sr.reframing_signal_text(f"{headline}. {claim}") or sr.relationship_novelty_dimensions(f"{headline}. {claim}")))
    if not (event_route or analysis_route):
        return "C_NOT_CONCRETE_EVENT_OR_NEW_ANALYSIS", "The item is not a concrete public event/development and does not qualify through the current specific-analysis route."
    return "C_CURRENT_GATE_REJECT", "The scanner's authoritative saved-C gate rejected the row under its current rules."


def _c_first_seen_for_retention(item: dict[str, Any], now: dt.datetime) -> dict[str, Any]:
    out = sr._low_evidence_signal(item)
    if not sr._parse_utc_datetime(out.get("first_seen")):
        # Match prune_public_window: legacy rows without first_seen start retention now rather
        # than being spuriously expired from an old publication date.
        out["first_seen"] = now.isoformat(timespec="minutes").replace("+00:00", "Z")
    return out


def _c_preference(row: dict[str, Any], active: bool) -> tuple[int, int, int, int, str]:
    concrete, date_ord, anchored = sr._c_publication_rank_key(row)
    # Active/currently-eligible public representation first, then current scanner C ranking.
    return (0 if active else 1, -concrete, -date_ord, -anchored, clean(row.get("first_seen")) or "9999")


def dedupe_c(candidates: list[dict[str, Any]], decisions: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    """Greedy same-event dedupe using the scanner's current signals_near_duplicate predicate."""
    ordered = sorted(candidates, key=lambda x: _c_preference(x["item"], x["target"] == "active"))
    kept: list[dict[str, Any]] = []
    for cand in ordered:
        duplicate = next((k for k in kept if sr.signals_near_duplicate(cand["item"], k["item"])), None)
        if duplicate is None:
            kept.append(cand)
            continue
        # Preserve the earliest observation on the retained event.
        loser_seen = clean(cand["item"].get("first_seen"))
        winner_seen = clean(duplicate["item"].get("first_seen"))
        if loser_seen and (not winner_seen or loser_seen < winner_seen):
            duplicate["item"]["first_seen"] = loser_seen
        d = decisions[cand["audit_index"]]
        d.update({
            "decision": "duplicate_remove", "target_collection": "",
            "reason_code": "C_SAME_EVENT_DUPLICATE",
            "reason": "Same underlying C event/claim under the scanner's current event-level duplicate logic.",
            "duplicate_of": item_ref(duplicate["item"]),
        })
    return kept


def _preserve_higher_order(before: dict[str, Any], after: dict[str, Any]) -> None:
    for key in PROTECTED_HIGHER_ORDER_KEYS:
        if key in before and before.get(key) != after.get(key):
            raise RuntimeError(f"Safety stop: revalidation changed protected higher-order key {key!r}.")


def revalidate_document(
    original: dict[str, Any], *, now: dt.datetime, network_refresh: bool, workers: int,
    fail_unverifiable: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (cleaned_document, report).  No files are written here."""
    if not isinstance(original, dict):
        raise ValueError("radar.json must contain a JSON object")

    out = copy.deepcopy(original)
    decisions: list[dict[str, Any]] = []
    ab_candidates: list[dict[str, Any]] = []
    ab_meta: list[dict[str, Any]] = []

    before_counts = {
        "A": len(original.get("strand_a", [])) if isinstance(original.get("strand_a"), list) else 0,
        "B": len(original.get("strand_b", [])) if isinstance(original.get("strand_b"), list) else 0,
        "AB_archive": len(original.get(sr.AB_ARCHIVE_KEY, [])) if isinstance(original.get(sr.AB_ARCHIVE_KEY), list) else 0,
        "C": len(original.get("strand_c", [])) if isinstance(original.get("strand_c"), list) else 0,
        "C_archive": len(original.get(sr.SIGNAL_ARCHIVE_KEY, [])) if isinstance(original.get(sr.SIGNAL_ARCHIVE_KEY), list) else 0,
    }

    # -------- A/B: evaluate every active and historically accepted row --------
    refresh_jobs: list[dict[str, Any]] = []
    refresh_job_to_meta: list[int] = []
    for collection in AB_KEYS:
        raw_rows = original.get(collection, []) if isinstance(original.get(collection), list) else []
        for row in raw_rows:
            if not isinstance(row, dict):
                decisions.append({
                    "corpus": "AB", "origin_collection": collection, "origin_strand": "",
                    "decision": "remove", "reason_code": "AB_NON_OBJECT", "reason": "Corpus entry is not a JSON object."
                })
                continue
            origin = _ab_origin(row, collection)
            audit = {"corpus": "AB", "origin_collection": collection, "origin_strand": origin, **item_ref(row)}
            decisions.append(audit)
            audit_index = len(decisions) - 1

            if not sr.record_source_integrity_ok(row):
                audit.update({"decision": "remove", "target_strand": "", "reason_code": "AB_SOURCE_INTEGRITY", "reason": "The record fails the scanner's current source/document integrity rule."})
                continue
            if not sr.record_date_integrity_ok(row):
                audit.update({"decision": "remove", "target_strand": "", "reason_code": "AB_DATE_INTEGRITY", "reason": "The record has no usable publication/event date under the current integrity rule."})
                continue

            ev = _ab_gate(row)
            origin_pass = bool(ev.get("a_pass" if origin == "A" else "b_pass"))
            meta = {"row": dict(row), "origin": origin, "collection": collection, "audit_index": audit_index, "stored_ev": ev, "final_ev": ev, "refresh": "not_needed"}
            ab_meta.append(meta)
            if not origin_pass:
                refresh_job_to_meta.append(len(ab_meta) - 1)
                refresh_jobs.append(row)

    sr.SCAN_DEADLINE_MONO = time.monotonic() + max(300, int(os.environ.get("FULL_REVALIDATION_NETWORK_BUDGET_SECONDS", "1800") or 1800))
    refresh_results, refresh_stats = _refresh_failed_ab(refresh_jobs, workers=workers, enabled=network_refresh)
    for j, meta_idx in enumerate(refresh_job_to_meta):
        meta = ab_meta[meta_idx]
        refreshed = refresh_results.get(j)
        if refreshed:
            refresh_doc = tuple(refreshed[:3])
            refresh_mode = clean(refreshed[3]) if len(refreshed) >= 4 else "scanner_refresh"
            meta["final_ev"] = _ab_gate(meta["row"], refresh_doc)
            meta["refresh"] = refresh_mode
        else:
            meta["refresh"] = "unavailable" if network_refresh else "disabled"

    # Circuit-breaker: a platform/network outage must never become a mass corpus deletion.
    # This only fires for a broad failure, not for individual dead links.
    if network_refresh and refresh_stats["attempted"] >= 20:
        ratio = refresh_stats["succeeded"] / max(1, refresh_stats["attempted"])
        min_ratio = float(os.environ.get("FULL_REVALIDATION_MIN_REFRESH_SUCCESS_RATIO", "0.20") or 0.20)
        if ratio < min_ratio:
            raise RuntimeError(
                f"Safety stop: only {refresh_stats['succeeded']}/{refresh_stats['attempted']} failed A/B records could be reopened "
                f"({ratio:.1%}); below the {min_ratio:.0%} network-health threshold. radar.json was not changed."
            )

    for meta in ab_meta:
        row = meta["row"]; origin = meta["origin"]; ev = meta["final_ev"]
        audit = decisions[meta["audit_index"]]
        a_pass = bool(ev.get("a_pass")); b_pass = bool(ev.get("b_pass"))
        audit["gate"] = _gate_snapshot(ev)
        audit["evidence_refresh"] = meta["refresh"]

        if origin == "A" and a_pass:
            target = "A"  # both-pass is not a clear reason to move an already valid A.
            decision = "keep"
            code = "A_CURRENT_GATE_PASS"
            reason = "Passes the current Strand A contract."
        elif origin == "B" and b_pass:
            target = "B"
            decision = "keep"
            code = "B_CURRENT_GATE_PASS"
            reason = "Passes the current Strand B method-object contract."
        elif a_pass and not b_pass:
            target = "A"; decision = "reclassify" if origin != "A" else "keep"
            code = "B_TO_A_CURRENT_GATE" if origin == "B" else "A_CURRENT_GATE_PASS"
            reason = "Fails its old Strand B classification but passes the current Strand A contract." if origin == "B" else "Passes the current Strand A contract."
        elif b_pass and not a_pass:
            target = "B"; decision = "reclassify" if origin != "B" else "keep"
            code = "A_TO_B_CURRENT_GATE" if origin == "A" else "B_CURRENT_GATE_PASS"
            reason = "Fails its old Strand A classification but passes the current Strand B method-object contract." if origin == "A" else "Passes the current Strand B contract."
        elif a_pass and b_pass:
            # The original strand already failed above only if this branch is reached from a
            # malformed/archived label; preserve the origin if possible because reclassification
            # must be clear, not arbitrary.
            target = origin if origin in {"A", "B"} else "A"
            decision = "keep"
            code = "AB_BOTH_PASS_KEEP_ORIGIN"
            reason = "Passes both current gates; retained in its existing strand because there is no clear basis for an A↔B move."
        else:
            fail_code, fail_reason = (_a_failure_reason(ev) if origin == "A" else _b_failure_reason(ev))
            if meta["refresh"] in {"unavailable", "disabled"} and not fail_unverifiable:
                target = origin; decision = "keep"; code = "AB_UNVERIFIABLE_DEFERRED"
                reason = "The saved evidence fails the current gate but the source could not be reopened; retained only because fail-unverifiable mode is disabled."
            else:
                audit.update({"decision": "remove", "target_strand": "", "reason_code": fail_code, "reason": fail_reason})
                continue

        cleaned = _apply_ab_evidence(row, ev, target)
        audit.update({"decision": decision, "target_strand": target, "reason_code": code, "reason": reason})
        ab_candidates.append({"item": cleaned, "audit_index": meta["audit_index"]})

    # A/B duplicate removal uses the scanner's current identity and primary-document rules.
    ab_rows = dedupe_ab(ab_candidates, decisions)

    clean_a = [dict(x, strand="A", new_this_scan=False) for x in ab_rows if clean(x.get("strand")).upper() == "A"]
    clean_b = [dict(x, strand="B", new_this_scan=False) for x in ab_rows if clean(x.get("strand")).upper() == "B"]
    clean_a.sort(key=lambda x: (clean(x.get("date")), clean(x.get("title"))), reverse=True)
    clean_b.sort(key=lambda x: (clean(x.get("date")), clean(x.get("title"))), reverse=True)

    # Current repository is cumulative A/B with active_core_limit=0. If that ever changes,
    # hand the validated set to the scanner's own rebalancer rather than inventing a policy.
    if int(sr.ACTIVE_CORE_LIMIT or 0) == 0:
        out["strand_a"], out["strand_b"], out[sr.AB_ARCHIVE_KEY] = clean_a, clean_b, []
    else:
        out["strand_a"], out["strand_b"], out[sr.AB_ARCHIVE_KEY], _ = sr.rebalance_active_core(clean_a, clean_b, [], now.isoformat())

    # -------- C: active + archive, current integrity/gate/retention + same-event dedup --------
    c_candidates: list[dict[str, Any]] = []
    c_decisions: dict[int, dict[str, Any]] = {}
    for collection in C_KEYS:
        raw_rows = original.get(collection, []) if isinstance(original.get(collection), list) else []
        for row in raw_rows:
            if not isinstance(row, dict):
                d = {"corpus": "C", "origin_collection": collection, "decision": "remove", "reason_code": "C_NON_OBJECT", "reason": "Corpus entry is not a JSON object."}
                decisions.append(d)
                continue
            d = {"corpus": "C", "origin_collection": collection, **item_ref(row)}
            decisions.append(d); audit_index = len(decisions) - 1; c_decisions[audit_index] = d
            if sr.signal_is_retired(row):
                code, reason = c_failure_reason(row)
                d.update({"decision": "remove", "target_collection": "", "reason_code": code, "reason": reason})
                continue
            authoritative_pass = sr._saved_signal_passes(row)
            if not authoritative_pass:
                code, reason = c_failure_reason(row)
                d.update({"decision": "remove", "target_collection": "", "reason_code": code, "reason": reason})
                continue
            item = _c_first_seen_for_retention(dict(row), now)
            expired = sr.signal_retention_expired(item, now)
            target = "archive" if expired else "active"
            origin_target = "active" if collection == "strand_c" else "archive"
            if target == origin_target:
                decision = "keep"
                code = "C_CURRENT_GATE_PASS_ACTIVE" if target == "active" else "C_CURRENT_GATE_PASS_ARCHIVED"
                reason = "Passes the current C gate and remains within its status-aware retention window." if target == "active" else "Passes the current C evidence/event gate but remains archived because its current retention window has expired."
            elif target == "archive":
                decision = "archive"
                code = "C_RETENTION_EXPIRED"
                reason = "Passes the current C evidence/event gate, but its status-aware retention window has expired, so it moves from active C to the private signal archive."
            else:
                decision = "reactivate"
                code = "C_VALID_WITHIN_RETENTION"
                reason = "The archived row passes the current C gate and is still within the current retention window, so it returns to active C."
            d.update({"decision": decision, "target_collection": target, "reason_code": code, "reason": reason})
            c_candidates.append({"item": item, "target": target, "audit_index": audit_index})

    c_kept = dedupe_c(c_candidates, c_decisions)
    active_c: list[dict[str, Any]] = []
    archived_c: list[dict[str, Any]] = []
    for cand in c_kept:
        item = dict(cand["item"])
        item["new_this_scan"] = False
        # Same-event dedupe can inherit an earlier first_seen from a duplicate. Re-evaluate
        # retention after dedupe so a duplicate leak cannot artificially restart C's clock.
        target = "archive" if sr.signal_retention_expired(item, now) else "active"
        if target != cand["target"]:
            cand["target"] = target
            audit = decisions[cand["audit_index"]]
            origin_target = "active" if audit.get("origin_collection") == "strand_c" else "archive"
            if target == "archive" and origin_target == "active":
                audit.update({"decision": "archive", "target_collection": "archive", "reason_code": "C_RETENTION_EXPIRED_AFTER_DEDUP", "reason": "After same-event deduplication restored the event's earliest first_seen, the current status-aware C retention window is expired."})
            elif target == "archive":
                audit.update({"decision": "keep", "target_collection": "archive", "reason_code": "C_CURRENT_GATE_PASS_ARCHIVED", "reason": "Passes the current C evidence/event gate but remains archived because its current retention window has expired."})
            elif origin_target == "archive":
                audit.update({"decision": "reactivate", "target_collection": "active", "reason_code": "C_VALID_WITHIN_RETENTION", "reason": "The archived row passes the current C gate and is still within the current retention window, so it returns to active C."})
            else:
                audit.update({"decision": "keep", "target_collection": "active", "reason_code": "C_CURRENT_GATE_PASS_ACTIVE", "reason": "Passes the current C gate and remains within its status-aware retention window."})
        if target == "active":
            item.pop("archive_reason", None); item.pop("archived_at", None); item.pop("public_active", None)
            active_c.append(item)
        else:
            item["public_active"] = False
            item.setdefault("archive_reason", "public_window_expired")
            item.setdefault("archived_at", now.isoformat(timespec="minutes").replace("+00:00", "Z"))
            archived_c.append(item)
    active_c.sort(key=lambda x: clean(x.get("c_event_date") or x.get("date")), reverse=True)
    archived_c.sort(key=lambda x: clean(x.get("date") or x.get("first_seen")), reverse=True)
    out["strand_c"] = active_c
    out[sr.SIGNAL_ARCHIVE_KEY] = archived_c

    # Explicit one-time metadata only. Existing scan timestamps/state and downstream reasoning
    # are intentionally not made to look as though a discovery scan ran.
    stamp = now.isoformat(timespec="minutes").replace("+00:00", "Z")
    out["full_corpus_revalidation"] = {
        "tool_version": TOOL_VERSION,
        "completed_at": stamp,
        "scanner_version": clean((ROOT / "VERSION.txt").read_text(encoding="utf-8") if (ROOT / "VERSION.txt").exists() else ""),
        "discovery_scan": False,
        "higher_order_reasoning_rebuilt": False,
    }

    _preserve_higher_order(original, out)

    # Diagnostics requested by the curator.
    def count_dec(corpus: str, origin: str | None = None, decision: str | None = None, target: str | None = None) -> int:
        n = 0
        for d in decisions:
            if d.get("corpus") != corpus: continue
            if origin is not None and d.get("origin_strand") != origin: continue
            if decision is not None and d.get("decision") != decision: continue
            if target is not None and d.get("target_strand") != target: continue
            n += 1
        return n

    a_kept = sum(1 for d in decisions if d.get("corpus") == "AB" and d.get("origin_strand") == "A" and d.get("decision") == "keep" and d.get("target_strand") == "A")
    a_removed = sum(1 for d in decisions if d.get("corpus") == "AB" and d.get("origin_strand") == "A" and d.get("decision") in {"remove", "duplicate_remove"})
    a_reclass = sum(1 for d in decisions if d.get("corpus") == "AB" and d.get("origin_strand") == "A" and d.get("decision") == "reclassify" and d.get("target_strand") == "B")
    b_kept = sum(1 for d in decisions if d.get("corpus") == "AB" and d.get("origin_strand") == "B" and d.get("decision") == "keep" and d.get("target_strand") == "B")
    b_removed = sum(1 for d in decisions if d.get("corpus") == "AB" and d.get("origin_strand") == "B" and d.get("decision") in {"remove", "duplicate_remove"})
    b_reclass = sum(1 for d in decisions if d.get("corpus") == "AB" and d.get("origin_strand") == "B" and d.get("decision") == "reclassify" and d.get("target_strand") == "A")
    c_removed = sum(1 for d in decisions if d.get("corpus") == "C" and d.get("decision") in {"remove", "duplicate_remove"})
    c_kept = sum(1 for d in decisions if d.get("corpus") == "C" and d.get("decision") in {"keep", "archive", "reactivate"})
    duplicate_removed = sum(1 for d in decisions if d.get("decision") == "duplicate_remove")

    diagnostics = {
        "A": {"kept": a_kept, "removed": a_removed, "reclassified_to_B": a_reclass},
        "B": {"kept": b_kept, "removed": b_removed, "reclassified_to_A": b_reclass},
        "C": {
            "kept_or_retained": c_kept,
            "removed": c_removed,
            "moved_to_archive": sum(1 for d in decisions if d.get("corpus") == "C" and d.get("decision") == "archive"),
            "reactivated": sum(1 for d in decisions if d.get("corpus") == "C" and d.get("decision") == "reactivate"),
        },
        "duplicates_removed": duplicate_removed,
        "final_totals": {"A": len(out.get("strand_a", [])), "B": len(out.get("strand_b", [])), "C": len(out.get("strand_c", [])), "C_archive": len(out.get(sr.SIGNAL_ARCHIVE_KEY, []))},
        "refresh": refresh_stats,
        "soft_mix_policy": {"A": 8, "B": 1, "C": 3, "hard_quota": False, "used_for_accept_reject": False},
    }
    report = {
        "tool": "ONE-TIME Full Corpus Revalidation",
        "tool_version": TOOL_VERSION,
        "completed_at": stamp,
        "before": before_counts,
        "diagnostics": diagnostics,
        "decision_count": len(decisions),
        "decisions": decisions,
    }
    return out, report


def report_markdown(report: dict[str, Any]) -> str:
    d = report["diagnostics"]
    lines = [
        "# ONE-TIME Full Corpus Revalidation",
        "",
        f"Completed: `{report.get('completed_at','')}`",
        "",
        "This was a corpus-only retrospective revalidation. It did **not** run discovery and did **not** rebuild shocks, risks, opportunities, trends, phenomena, or other higher-order reasoning.",
        "",
        "## Diagnostics",
        "",
        f"- A kept: **{d['A']['kept']}**",
        f"- A removed: **{d['A']['removed']}**",
        f"- A reclassified to B: **{d['A']['reclassified_to_B']}**",
        f"- B kept: **{d['B']['kept']}**",
        f"- B removed: **{d['B']['removed']}**",
        f"- B reclassified to A: **{d['B']['reclassified_to_A']}**",
        f"- C kept/retained: **{d['C']['kept_or_retained']}**",
        f"- C removed: **{d['C']['removed']}**",
        f"- C moved to archive: **{d['C']['moved_to_archive']}**",
        f"- C reactivated: **{d['C']['reactivated']}**",
        f"- Duplicates removed: **{d['duplicates_removed']}**",
        f"- Final A/B/C totals: **{d['final_totals']['A']} / {d['final_totals']['B']} / {d['final_totals']['C']}**",
        f"- C archive retained: **{d['final_totals']['C_archive']}**",
        "",
        "The 8:1:3 values were treated only as soft mix/share metadata. They were not used as caps, floors, quotas, rescue targets, or reasons to reject valid evidence.",
        "",
        "## Audit trail",
        "",
        "The JSON report contains one decision record for every active or historically accepted A/B/C row, including the reason, target strand/collection, gate snapshot where applicable, and duplicate winner where applicable.",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--radar", default="radar.json", help="Path to radar.json")
    p.add_argument("--report-json", default="", help="Write detailed JSON audit here")
    p.add_argument("--report-md", default="", help="Write human-readable diagnostics here")
    p.add_argument("--no-network", action="store_true", help="Do not reopen A/B sources that fail on saved evidence")
    p.add_argument("--keep-unverifiable", action="store_true", help="Testing/emergency mode only: retain failed A/B rows when refresh is unavailable")
    p.add_argument("--dry-run", action="store_true", help="Build and validate result but do not replace radar.json")
    p.add_argument("--workers", type=int, default=int(sr.CONFIG.get("inherited_corpus_audit_workers", 8) or 8))
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    radar_path = Path(args.radar)
    before_bytes = radar_path.read_bytes()
    original = json.loads(before_bytes.decode("utf-8"))
    now = dt.datetime.now(dt.timezone.utc)
    cleaned, report = revalidate_document(
        original, now=now, network_refresh=not args.no_network, workers=max(1, args.workers),
        fail_unverifiable=not args.keep_unverifiable,
    )
    report["input_sha256"] = sha256_bytes(before_bytes)
    output_text = json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n"
    report["output_sha256"] = sha256_bytes(output_text.encode("utf-8"))

    if args.report_json:
        Path(args.report_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.report_md:
        Path(args.report_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report_md).write_text(report_markdown(report), encoding="utf-8")
    if not args.dry_run:
        tmp = radar_path.with_suffix(radar_path.suffix + ".revalidation.tmp")
        tmp.write_text(output_text, encoding="utf-8")
        os.replace(tmp, radar_path)

    d = report["diagnostics"]
    print("ONE-TIME Full Corpus Revalidation")
    print(f"A kept / removed / reclassified -> B: {d['A']['kept']} / {d['A']['removed']} / {d['A']['reclassified_to_B']}")
    print(f"B kept / removed / reclassified -> A: {d['B']['kept']} / {d['B']['removed']} / {d['B']['reclassified_to_A']}")
    print(f"C kept-or-retained / removed / archived / reactivated: {d['C']['kept_or_retained']} / {d['C']['removed']} / {d['C']['moved_to_archive']} / {d['C']['reactivated']}")
    print(f"Duplicates removed: {d['duplicates_removed']}")
    print(f"Final A/B/C: {d['final_totals']['A']} / {d['final_totals']['B']} / {d['final_totals']['C']}")
    print(f"Audit decisions: {report['decision_count']}")
    if args.dry_run:
        print("Dry run: radar.json was not replaced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
