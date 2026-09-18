#!/usr/bin/env python3
"""Stage 6 live adapter for claim-native Radar reasoning.

This module switches *detector input* from legacy regex role-fillers to the
schema-validated claim layer while deliberately preserving the existing
lifecycle/publication shell until Stage 7.  It is fail-closed:

- Deep Scan / active-corpus semantics remain authoritative.
- Strand B and world_reasoning=false claims never enter world reasoning.
- Fresh records without authoritative claims receive conservative provisional
  claims so the detector does not become blind while Deep Scan is pending.
- Provisional Strand C claims are context-only; provisional A/frontier claims
  may enter the primary frontier but at conservative merit.
- New claim-native Level-5 candidates are publication locked until candidate-
  specific falsifier execution, wow/oddity and Stage-7 selection are wired.
- Existing reader publications are carried as a compatibility shell; no legacy
  regex detector is allowed to create a new candidate once the authority gate
  passes.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.active_corpus import (
        build_active_document,
        load_admission,
        load_corrections,
        load_reader,
        record_key,
    )
    from scripts.claims_schema import date_precision, load_vocabulary, validate_claim
    from scripts.rebuild_active_radar import _add_historical_context
    from scripts.claim_reasoning_shadow import (
        anchor_demand_candidates,
        build_distance_table,
        claim_expressiveness,
        conflicting_criteria,
        corroborated_claims,
        dependency_pathways,
        era_conjunctions,
        flatten_claims,
        latent_channels,
        level3_findings,
        named_continuities,
        opposing_movements,
        split_recurrence_candidates,
    )
except ModuleNotFoundError:  # direct execution from scripts/
    from active_corpus import (  # type: ignore
        build_active_document,
        load_admission,
        load_corrections,
        load_reader,
        record_key,
    )
    from claims_schema import date_precision, load_vocabulary, validate_claim  # type: ignore
    from rebuild_active_radar import _add_historical_context  # type: ignore
    from claim_reasoning_shadow import (  # type: ignore
        anchor_demand_candidates,
        build_distance_table,
        claim_expressiveness,
        conflicting_criteria,
        corroborated_claims,
        dependency_pathways,
        era_conjunctions,
        flatten_claims,
        latent_channels,
        level3_findings,
        named_continuities,
        opposing_movements,
        split_recurrence_candidates,
    )

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "radar-claim-reasoning-live-v1-stage7"
AUTHORITY_MIN_CLAIMS = 100
AUTHORITY_MIN_COVERAGE = 0.50

_READER_CLAIM_COUNT_CACHE: dict[tuple[str, int, int], int] = {}
_LIVE_DETECTION_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}


def _mtime_ns(path: Path) -> int:
    try:
        return int(path.stat().st_mtime_ns)
    except OSError:
        return 0


def _detection_cache_key(raw: dict[str, Any], root: Path, evaluated_at: str | None) -> tuple[Any, ...]:
    return (
        str(root.resolve()), clean(evaluated_at or raw.get("run_completed_at") or raw.get("last_updated")),
        tuple(len(raw.get(k, [])) if isinstance(raw.get(k), list) else 0 for k in ("strand_a", "frontier_evidence", "strand_c", "strand_b")),
        _mtime_ns(root / "reader_text.json"), _mtime_ns(root / "admission_state.json"),
        _mtime_ns(root / "record_corrections.json"), _mtime_ns(root / "historical" / "historical.json"),
    )



def _inline_claim_count(raw: dict[str, Any]) -> int:
    total = 0
    for collection in ("strand_a", "frontier_evidence", "strand_c", "historical_context"):
        rows = raw.get(collection) if isinstance(raw.get(collection), list) else []
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("claims"), list):
                total += sum(1 for c in row.get("claims", []) if isinstance(c, dict) and clean(c.get("origin")) != "provisional")
    return total


def _reader_claim_count(root: Path) -> int:
    path = root / "reader_text.json"
    try:
        st = path.stat()
    except OSError:
        return 0
    key = (str(path.resolve()), int(st.st_mtime_ns), int(st.st_size))
    if key in _READER_CLAIM_COUNT_CACHE:
        return _READER_CLAIM_COUNT_CACHE[key]
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    records = doc.get("records") if isinstance(doc, dict) and isinstance(doc.get("records"), dict) else {}
    count = sum(len(v.get("claims", [])) for v in records.values() if isinstance(v, dict) and isinstance(v.get("claims"), list))
    _READER_CLAIM_COUNT_CACHE.clear()
    _READER_CLAIM_COUNT_CACHE[key] = count
    return count


def _empty_detection(raw: dict[str, Any], evaluated_at: str | None, *, reason: str, reader_claims: int = 0) -> dict[str, Any]:
    gate = {
        "authoritative_claims": max(_inline_claim_count(raw), reader_claims),
        "current_world_records": sum(len(raw.get(k, [])) if isinstance(raw.get(k), list) else 0 for k in ("strand_a", "frontier_evidence", "strand_c")),
        "records_with_any_claim": 0, "coverage": 0.0,
        "min_authoritative_claims": AUTHORITY_MIN_CLAIMS, "min_coverage": AUTHORITY_MIN_COVERAGE,
        "authority_ready": False, "semantic_quality_ready": False, "ready": False, "reason": reason,
    }
    return {
        "profile": PROFILE, "evaluated_at": _date_only(evaluated_at or raw.get("run_completed_at") or raw.get("last_updated")),
        "nodes": [], "claim_diagnostics": {"claims_loaded": 0, "authoritative_claims": gate["authoritative_claims"]},
        "authority_gate": gate, "claim_expressiveness": {"ready_for_detector_switch": False, "warnings": [reason]},
        "distance_table": {"N": 0, "clusters": {}, "pairs": {}},
        "groups": {
            "level2_corroborated": [], "level2_named_continuity": [], "level3_sequence_gap": [], "level3_era_conjunction": [],
            "level4_opposing_movements": [], "level5_dependency_pathway": [], "level4_5_conflicting_criteria": [],
            "level5_latent_channel": [], "level5_anchor_demand": [], "level5_split_recurrence": [],
        },
    }


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _low(value: Any) -> str:
    return clean(value).lower()


def _date_only(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    # Preserve partial precision.  A timestamp may safely lose only its time part;
    # no missing month/day is invented.
    if re.match(r"^\d{4}-\d{2}-\d{2}[T ]", text):
        text = text[:10]
    return text if date_precision(text) else ""


def _row_text(row: dict[str, Any]) -> str:
    deep = row.get("deep_analysis") if isinstance(row.get("deep_analysis"), dict) else {}
    strategic = row.get("strategic_classification") if isinstance(row.get("strategic_classification"), dict) else {}
    lenses = strategic.get("lenses") if isinstance(strategic.get("lenses"), list) else []
    lens_text = " ".join(clean(x.get("passage")) for x in lenses if isinstance(x, dict))
    return clean(" ".join([
        clean(row.get("reader_title")), clean(row.get("title")), clean(row.get("headline")),
        clean(row.get("reader_what")), clean(row.get("what")), clean(row.get("core_message")),
        clean(deep.get("main_finding")), clean(row.get("reader_why")), clean(row.get("why_it_matters")),
        clean(row.get("summary")), clean(row.get("signal_note")), clean(row.get("relevance_note")), lens_text,
    ]))


def _tokens(value: str) -> set[str]:
    stop = {"the", "and", "for", "with", "from", "into", "system", "policy", "european", "europe", "eu"}
    return {t for t in re.findall(r"[a-z0-9]+", value.lower()) if len(t) >= 3 and t not in stop}


_OBJECT_CUES: dict[str, tuple[str, ...]] = {
    "compute.public_procurement": ("public procurement", "gigafactor", "eurohpc call", "compute procurement"),
    "compute.gigafactory": ("gigafactor", "ai factory", "ai factories"),
    "compute.access_time": ("compute access", "access time", "supercomputer access"),
    "compute.capacity": ("compute capacity", "supercomput", "gpu capacity", "cloud capacity"),
    "compute.private_investment": ("private investment", "hyperscaler investment", "data centre investment", "data center investment"),
    "datacentre.permitting": ("data centre permit", "data center permit", "permitting regime", "planning permission"),
    "datacentre.energy_supply": ("data centre energy", "data center energy", "power supply", "grid connection"),
    "datacentre.local_opposition": ("local opposition", "community opposition", "rural opposition"),
    "datacentre.siting": ("data centre sit", "data center sit", "site selection", "land for data centre", "land for data center"),
    "quantum.equipment": ("quantum equipment", "quantum hardware"),
    "quantum.testing_infrastructure": ("quantum testing", "testing infrastructure", "quantum certification"),
    "quantum.machine": ("quantum computer", "quantum machine"),
    "quantum.standards": ("quantum standard",),
    "quantum.pilot_line": ("quantum pilot",),
    "chips.eu_inference_supplier": ("inference chip", "ai chip supplier", "axelera"),
    "chips.nvidia_gpu": ("nvidia", "gpu"),
    "chips.fab": ("semiconductor fab", "chip fab", "fabrication plant"),
    "chips.pilot_line": ("chip pilot line", "semiconductor pilot line"),
    "export_control.regulation": ("export control", "dual-use regulation", "dual use regulation"),
    "export_control.competence": ("export licensing", "national licensing", "member state competence"),
    "export_control.licence_decision": ("licence decision", "license decision", "export licence", "export license"),
    "research.openness": ("research openness", "open science", "academic openness"),
    "research.open_access": ("open access", "open-access"),
    "research_security.self_assessment": ("self-assessment", "self assessment", "research security assessment"),
    "research_security.screening": ("research security screening", "security screening", "knowledge security"),
    "research_security.espionage_case": ("espionage", "research spying", "chip secrets"),
    "grant.admissibility": ("grant admissibility", "application admissibility", "mandatory part of every application"),
    "talent.recruitment_abroad": ("recruit researchers", "attract researchers", "choose europe", "talent attraction"),
    "talent.retention": ("retain researchers", "researcher retention", "brain drain"),
    "talent.career_structure": ("research career", "career structure"),
    "horizon.association": ("horizon association", "associated country", "associate to horizon"),
    "horizon.access": ("horizon access", "programme access", "program access"),
    "horizon.exclusion": ("horizon exclusion", "locked out", "excluded from horizon"),
    "horizon.budget_2028_34": ("fp10 budget", "horizon budget", "research budget 2028", "framework programme budget"),
    "horizon.success_rate": ("success rate", "unfunded fundable"),
    "materials.critical_raw": ("critical raw material", "critical mineral"),
    "energy.grid": ("electricity grid", "grid capacity", "grid connection"),
    "finance.us_hyperscaler_debt_exposure": ("hyperscaler debt", "us tech debt", "institutional investor exposure"),
    "finance.gulf_capital": ("gulf capital", "uae investment", "saudi investment"),
    "goal.strategic_autonomy": ("strategic autonomy", "technological sovereignty", "technology sovereignty"),
    # Later vocabulary revisions use these; cues are ignored automatically when
    # the current repository vocabulary does not contain the object.
    "digital.sovereignty": ("digital sovereignty", "tech sovereignty", "technology sovereignty"),
    "research.collaboration": ("research collaboration", "scientific cooperation", "science diplomacy"),
    "research.system_governance": ("research system governance", "research governance", "era governance"),
    "innovation.system_performance": ("innovation performance", "innovation system", "competitiveness gap"),
    "industrial.competitiveness": ("industrial competitiveness", "competitiveness"),
    "ai.governance": ("ai governance", "ai act", "artificial intelligence regulation"),
    "digital.public_procurement": ("digital public procurement", "public procurement"),
    "finance.strategic_investment": ("strategic investment", "investment gap", "private capital"),
    "finance.digital_market_infrastructure": ("digital market infrastructure", "financial market infrastructure"),
    "defence.drone_capability": ("drone capability", "unmanned aerial", "defence drone", "defense drone"),
}

_MECHANISM_CUES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pre_clears", ("pre-clear", "preclear")),
    ("adds_capacity", ("adds capacity", "new capacity", "expands capacity", "capacity expansion")),
    ("harmonises", ("harmonis", "harmoniz", "common rule", "single procedure")),
    ("reconciles", ("reconcil", "arbitration rule", "tie-break")),
    ("exempts", ("exempt",)),
    ("diversifies", ("diversif", "alternative supplier")),
    ("substitutes", ("substitut", "replacement")),
    ("standardises", ("standardis", "standardiz", "standard-setting")),
    ("certifies", ("certif", "testing infrastructure")),
    ("licenses", ("licen", "licensing")),
    ("screens", ("screen", "self-assessment", "self assessment")),
    ("restricts", ("restrict", "export control", "ban", "blocked", "withheld")),
    ("excludes", ("exclude", "locked out")),
    ("conditions", ("condition", "conditional", "subject to")),
    ("requires", ("requires", "depends on", "dependent on", "needs ")),
    ("procures", ("procurement", "tender", "purchase", "buyer")),
    ("recruits", ("recruit", "attract talent", "attract researchers")),
    ("retains", ("retain", "retention")),
    ("associates", ("association", "associate to horizon", "joins horizon")),
    ("sells", ("supply deal", "signed contract", "customer contract", "sells")),
    ("supplies", ("supplies", "supplier")),
    ("builds", ("builds", "build-out", "buildout", "construct", "inaugurat", "facility")),
    ("funds", ("funds", "funding", "grant", "investment")),
    ("adopts", ("adopted", "approved", "entered into force", "in force", "enacted")),
    ("proposes", ("proposes", "proposed", "proposal", "calls for", "urges")),
    ("evaluates", ("evaluation", "consultation", "call for evidence")),
    ("regulates", ("regulat", "permit", "rule", "law")),
    ("measures", ("measures", "measurement", "indicator", "metric")),
    ("assesses", ("study", "report", "analysis", "finds", "shows", "assess")),
)


def _candidate_objects(text: str, vocab: dict[str, Any]) -> list[tuple[float, str]]:
    low = text.lower()
    scores: dict[str, float] = {}
    objects = vocab.get("objects") if isinstance(vocab.get("objects"), dict) else {}
    aliases = vocab.get("object_aliases") if isinstance(vocab.get("object_aliases"), dict) else {}
    for obj in objects:
        score = 0.0
        for cue in _OBJECT_CUES.get(obj, ()):
            if cue in low:
                score = max(score, 5.0 + min(2.0, len(cue) / 30.0))
        label_tokens = _tokens(obj.replace(".", " ").replace("_", " "))
        if label_tokens:
            hits = sum(1 for t in label_tokens if re.search(rf"\b{re.escape(t)}\w*\b", low))
            if hits:
                score = max(score, hits / len(label_tokens) * 3.0)
        if score:
            scores[obj] = score
    for alias, canonical in aliases.items():
        if canonical not in objects:
            continue
        phrase = clean(alias).replace("_", " ").replace(".", " ").lower()
        if phrase and phrase in low:
            scores[canonical] = max(scores.get(canonical, 0.0), 4.0)
    return sorted(((v, k) for k, v in scores.items()), reverse=True)


def _mechanism(text: str, vocab: dict[str, Any]) -> str:
    allowed = set(vocab.get("mechanisms") or [])
    low = text.lower()
    for mech, cues in _MECHANISM_CUES:
        if mech in allowed and any(c in low for c in cues):
            return mech
    return "assesses" if "assesses" in allowed else next(iter(sorted(allowed)), "")


def _direction(text: str, mechanism: str, vocab: dict[str, Any]) -> str:
    allowed = set(vocab.get("directions") or [])
    low = text.lower()
    if any(x in low for x in ("contested", "opposition", "dispute", "diverge", "conflict between")) and "becomes_contested" in allowed:
        return "becomes_contested"
    if mechanism in {"conditions", "requires", "screens", "licenses", "regulates"} and "becomes_conditional" in allowed:
        return "becomes_conditional"
    if mechanism in {"restricts", "excludes"} or any(x in low for x in ("cut", "declin", "shortage", "blocked", "locked out")):
        if "contracts" in allowed:
            return "contracts"
    if mechanism in {"builds", "funds", "recruits", "retains", "associates", "adds_capacity", "diversifies", "sells", "supplies", "procures", "adopts", "proposes"}:
        if "expands" in allowed:
            return "expands"
    return "unchanged" if "unchanged" in allowed else next(iter(sorted(allowed)), "")


def _status(row: dict[str, Any], text: str, vocab: dict[str, Any]) -> str:
    allowed = set(vocab.get("statuses") or [])
    existing = _low(row.get("realisation_status") or row.get("status"))
    if existing in allowed:
        return existing
    typ = _low(row.get("type") or row.get("signal_kind"))
    low = text.lower()
    rules = (
        ("abandoned", ("abandoned", "withdrawn", "cancelled", "canceled", "scrapped")),
        ("lapsed", ("lapsed", "expired", "sunset")),
        ("in_force", ("entered into force", "in force", "took effect", "enacted")),
        ("adopted", ("formally adopted", "adopted", "approved", "political agreement")),
        ("in_negotiation", ("under negotiation", "negotiating mandate", "trilogue")),
        ("proposed", ("proposed", "proposal", "tabled", "draft regulation", "call for evidence")),
        ("operating", ("operating", "operational", "in operation", "inaugurated", "mandatory part of every")),
        ("call_open", ("call open", "opened a call", "tender", "competitive call")),
        ("announced", ("announced", "launches", "launched", "committed", "signed")),
    )
    for status, cues in rules:
        if status in allowed and any(c in low for c in cues):
            return status
    if any(x in typ for x in ("peer-reviewed", "journal", "study", "report", "article", "working paper", "preprint")) and "delivered" in allowed:
        return "delivered"
    return "announced" if "announced" in allowed else next(iter(sorted(allowed)), "")


def _kind(row: dict[str, Any], text: str, status: str, mechanism: str, vocab: dict[str, Any]) -> str:
    allowed = set(vocab.get("kinds") or [])
    typ = _low(row.get("type") or row.get("signal_kind"))
    low = text.lower()
    if any(x in typ for x in ("peer-reviewed", "journal", "study", "report", "article", "working paper", "preprint")):
        return "diagnosis" if "diagnosis" in allowed else next(iter(sorted(allowed)), "")
    if re.search(r"\b(calls for|urges|argues|recommends|should)\b", low) and status in {"intention", "proposed", "delivered"}:
        if "advocacy" in allowed:
            return "advocacy"
    if mechanism in {"sells", "supplies"} and status == "delivered" and "effect" in allowed:
        return "effect"
    return "action" if "action" in allowed else next(iter(sorted(allowed)), "")


def _actor(row: dict[str, Any], text: str, vocab: dict[str, Any]) -> dict[str, str]:
    classes = set(vocab.get("actor_classes") or [])
    name = clean(row.get("c_event_actor") or row.get("authors") or row.get("institution") or row.get("source") or "Provisional source")
    low = (name + " " + text[:500]).lower()
    cls = "other"
    if any(x in low for x in ("european commission", "eurohpc", "european parliament", "council of the european union", "eic", "msca", "era portal")):
        cls = "eu_body"
    elif any(x in low for x in ("research council", "national fund", "funding agency")):
        cls = "national_funder"
    elif any(x in low for x in ("university", "academy", "research institute", "research organisation", "research organization")):
        cls = "university_group"
    elif any(x in low for x in ("government", "ministry", "member state", "finland", "germany", "france", "italy", "sweden", "ireland")):
        cls = "member_state"
    elif any(x in low for x in ("china", "united states", "u.s.", "uk government", "india", "japan")):
        cls = "third_country"
    elif any(x in low for x in ("company", "ltd", "inc", "gmbh", "oy", "google", "microsoft", "nvidia", "axelera")):
        cls = "company"
    elif any(x in low for x in ("think tank", "institute for", "council on", "association", "allea", "cesaer")):
        cls = "ngo_thinktank"
    if cls not in classes:
        cls = "other" if "other" in classes else next(iter(sorted(classes)), "other")
    return {"name": name[:180] or "Provisional source", "class": cls}


def _scope(row: dict[str, Any], text: str, vocab: dict[str, Any]) -> dict[str, Any]:
    scopes = set(vocab.get("scopes") or [])
    low = text.lower()
    level = "eu" if "eu" in scopes else next(iter(sorted(scopes)), "external")
    if _low(row.get("eu_relevance")) not in {"direct", "material_external"} and not re.search(r"\b(eu|european|europe)\b", low):
        level = "external" if "external" in scopes else level
    return {"level": level, "countries": []}


def _merit(row: dict[str, Any]) -> int:
    for key in ("source_merit_score", "merit", "quality_score"):
        try:
            n = float(row.get(key))
            if 0 <= n <= 100:
                return int(round(n))
        except (TypeError, ValueError):
            pass
    tier = _low(row.get("source_tier"))
    if "tier 1" in tier:
        return 70
    if "tier 2" in tier:
        return 60
    return 50


def provisional_claim_for_row(row: dict[str, Any], vocab: dict[str, Any]) -> dict[str, Any] | None:
    """Create one conservative scanner-derived claim for a claimless current row.

    This is intentionally less expressive than Deep Scan.  It exists only to stop a
    newly admitted record disappearing from the claim frontier while verification is
    pending; Deep Scan replaces it, never the other way around.
    """
    key = record_key(row)
    text = _row_text(row)
    status_date = _date_only(row.get("date") or row.get("c_event_date") or row.get("first_seen"))
    if not key or not text or not status_date:
        return None
    ranked = _candidate_objects(text, vocab)
    if not ranked or ranked[0][0] < 1.4:
        return None
    obj = ranked[0][1]
    secondary = [name for score, name in ranked[1:4] if score >= 2.0 and name != obj][:3]
    mechanism = _mechanism(text, vocab)
    direction = _direction(text, mechanism, vocab)
    status = _status(row, text, vocab)
    kind = _kind(row, text, status, mechanism, vocab)
    digest = hashlib.sha1(f"{key}|{obj}|{mechanism}|{direction}".encode("utf-8")).hexdigest()[:16]
    claim: dict[str, Any] = {
        "record_key": key,
        "claim_id": f"c:provisional:{digest}",
        "object": obj,
        "secondary_objects": secondary,
        "actor": _actor(row, text, vocab),
        "mechanism": mechanism,
        "direction": direction,
        "status": status,
        "status_date": status_date,
        "scope": _scope(row, text, vocab),
        "kind": kind,
        "merit": _merit(row),
        "qualification": "Provisional scanner-derived claim; awaiting Deep Scan verification.",
        "text": text[:900],
        "confidence": "low",
        "origin": "provisional",
        "era": "current",
        "provisional": True,
        "attributes": {"world_reasoning": True, "provisional_adapter": "stage6"},
    }
    precision = date_precision(status_date)
    if precision in {"year", "month"}:
        claim["status_date_precision"] = precision
    if validate_claim(claim, vocab):
        return None
    return claim


def build_active_from_raw(raw: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    admission = load_admission(root / "admission_state.json")
    corrections = load_corrections(root / "record_corrections.json")
    reader = load_reader(root / "reader_text.json")
    active = build_active_document(raw, admission=admission, corrections=corrections, reader=reader)
    _add_historical_context(
        active,
        admission=admission,
        corrections=corrections,
        reader=reader,
        historical_path=root / "historical" / "historical.json",
    )
    return active


def attach_provisional_claims(active: dict[str, Any], vocab: dict[str, Any]) -> dict[str, int]:
    generated = skipped = 0
    by_collection = Counter()
    for collection in ("strand_a", "frontier_evidence", "strand_c"):
        rows = active.get(collection) if isinstance(active.get(collection), list) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            if isinstance(row.get("claims"), list) and row.get("claims"):
                continue
            claim = provisional_claim_for_row(row, vocab)
            if claim is None:
                skipped += 1
                continue
            row["claims"] = [claim]
            row["claims_profile"] = "radar-claims-v1-provisional-stage6"
            generated += 1
            by_collection[collection] += 1
    return {"generated": generated, "skipped_unmappable": skipped, **{f"generated_{k}": v for k, v in by_collection.items()}}


def live_claim_graph(raw: dict[str, Any], root: Path = ROOT) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    vocab = load_vocabulary(root / "claims_vocabulary.json")
    active = build_active_from_raw(raw, root)
    provisional = attach_provisional_claims(active, vocab)
    nodes, diagnostics = flatten_claims(active, vocab)
    authoritative = [n for n in nodes if clean(n.get("origin")) != "provisional"]
    current_world_rows = sum(
        len(active.get(k, [])) if isinstance(active.get(k), list) else 0
        for k in ("strand_a", "frontier_evidence", "strand_c")
    )
    records_with_claims = len({clean(n.get("_record_id")) for n in nodes if clean(n.get("era")) == "current" and clean(n.get("_record_id"))})
    records_with_authoritative_claims = len({
        clean(n.get("_record_id")) for n in authoritative
        if clean(n.get("era")) == "current" and clean(n.get("_record_id"))
    })
    coverage = records_with_authoritative_claims / current_world_rows if current_world_rows else 0.0
    gate = {
        "authoritative_claims": len(authoritative),
        "current_world_records": current_world_rows,
        "records_with_any_claim": records_with_claims,
        "records_with_authoritative_claims": records_with_authoritative_claims,
        "coverage": round(coverage, 4),
        "min_authoritative_claims": AUTHORITY_MIN_CLAIMS,
        "min_coverage": AUTHORITY_MIN_COVERAGE,
        "authority_ready": len(authoritative) >= AUTHORITY_MIN_CLAIMS and coverage >= AUTHORITY_MIN_COVERAGE,
    }
    diagnostics = {**diagnostics, "authoritative_claims": len(authoritative), **provisional}
    return nodes, diagnostics, gate, vocab


def detect_claim_reasoning(raw: dict[str, Any], root: Path = ROOT, evaluated_at: str | None = None) -> dict[str, Any]:
    cache_key = _detection_cache_key(raw, root, evaluated_at)
    cached = _LIVE_DETECTION_CACHE.get(cache_key)
    if cached is not None:
        return cached
    # Cheap preflight for legacy/synthetic repositories. Production Stage 6 has
    # hundreds of authoritative claims in reader_text.json, so it proceeds to the
    # active-corpus overlay. This avoids repeatedly rebuilding a claimless corpus in
    # legacy unit tests and also fails closed if the claims sidecar disappears.
    inline_count = _inline_claim_count(raw)
    reader_count = _reader_claim_count(root)
    if max(inline_count, reader_count) < AUTHORITY_MIN_CLAIMS:
        result = _empty_detection(raw, evaluated_at, reason="claim authority preflight not ready", reader_claims=reader_count)
        _LIVE_DETECTION_CACHE.clear(); _LIVE_DETECTION_CACHE[cache_key] = result
        return result
    nodes, diagnostics, gate, vocab = live_claim_graph(raw, root)
    # Provisional scanner claims are an anti-blindness bridge, not a semantic
    # quality sample.  The detector-switch gate is judged only on authoritative
    # backfill/Deep-Scan claims.
    authoritative_nodes = [n for n in nodes if clean(n.get("origin")) != "provisional"]
    # Fail fast when the repository has not reached the claim-authority floor. This
    # keeps rollback/synthetic legacy calls cheap and prevents partial claim imports
    # from running an expensive half-switched detector pass.
    if not gate.get("authority_ready"):
        gate["semantic_quality_ready"] = False
        gate["ready"] = False
        result = {
            "profile": PROFILE,
            "evaluated_at": _date_only(evaluated_at or raw.get("run_completed_at") or raw.get("last_updated")),
            "nodes": nodes,
            "claim_diagnostics": diagnostics,
            "authority_gate": gate,
            "claim_expressiveness": {"ready_for_detector_switch": False, "warnings": ["claim authority gate not ready"]},
            "distance_table": {"N": 0, "clusters": {}, "pairs": {}},
            "groups": {
                "level2_corroborated": [], "level2_named_continuity": [], "level3_sequence_gap": [], "level3_era_conjunction": [],
                "level4_opposing_movements": [], "level5_dependency_pathway": [],
                "level4_5_conflicting_criteria": [], "level5_latent_channel": [],
                "level5_anchor_demand": [], "level5_split_recurrence": [],
            },
        }
        _LIVE_DETECTION_CACHE.clear(); _LIVE_DETECTION_CACHE[cache_key] = result
        return result
    expressiveness = claim_expressiveness(authoritative_nodes)
    gate["semantic_quality_ready"] = bool(expressiveness.get("ready_for_detector_switch"))
    gate["ready"] = bool(gate["authority_ready"] and gate["semantic_quality_ready"])
    if not gate["ready"]:
        result = {
            "profile": PROFILE,
            "evaluated_at": _date_only(evaluated_at or raw.get("run_completed_at") or raw.get("last_updated")),
            "nodes": nodes, "claim_diagnostics": diagnostics, "authority_gate": gate,
            "claim_expressiveness": expressiveness, "distance_table": {"N": 0, "clusters": {}, "pairs": {}},
            "groups": {
                "level2_corroborated": [], "level2_named_continuity": [], "level3_sequence_gap": [], "level3_era_conjunction": [],
                "level4_opposing_movements": [], "level5_dependency_pathway": [],
                "level4_5_conflicting_criteria": [], "level5_latent_channel": [],
                "level5_anchor_demand": [], "level5_split_recurrence": [],
            },
        }
        _LIVE_DETECTION_CACHE.clear(); _LIVE_DETECTION_CACHE[cache_key] = result
        return result
    ev = _date_only(evaluated_at or raw.get("run_completed_at") or raw.get("last_updated"))
    ev_date = dt.date.fromisoformat(ev) if date_precision(ev) == "day" else dt.datetime.now(dt.timezone.utc).date()
    distance = build_distance_table(nodes)
    groups = {
        "level2_corroborated": corroborated_claims(nodes),
        "level2_named_continuity": named_continuities(nodes),
        "level3_sequence_gap": level3_findings(nodes, ev_date),
        "level3_era_conjunction": era_conjunctions(nodes),
        "level4_opposing_movements": opposing_movements(nodes, ev_date, vocab),
        "level5_dependency_pathway": dependency_pathways(nodes, vocab, distance),
        "level4_5_conflicting_criteria": conflicting_criteria(nodes, vocab, distance),
        "level5_latent_channel": latent_channels(nodes, vocab),
        "level5_anchor_demand": anchor_demand_candidates(nodes, vocab),
        "level5_split_recurrence": split_recurrence_candidates(nodes, vocab),
    }
    result = {
        "profile": PROFILE,
        "evaluated_at": ev or ev_date.isoformat(),
        "nodes": nodes,
        "claim_diagnostics": diagnostics,
        "authority_gate": gate,
        "claim_expressiveness": expressiveness,
        "distance_table": distance,
        "groups": groups,
    }
    _LIVE_DETECTION_CACHE.clear(); _LIVE_DETECTION_CACHE[cache_key] = result
    return result


def _candidate_key(c: dict[str, Any]) -> str:
    grammar = clean(c.get("grammar_id"))
    if grammar == "corroborated_claim":
        # R-25 Level-2 identity is the corroborated semantic claim itself.  Product
        # polarity is part of the identity so a later polarity correction does not
        # silently rewrite a risk into an opportunity under the same candidate id.
        return "|".join([
            grammar, clean(c.get("product")), clean(c.get("object")),
            clean(c.get("mechanism")), clean(c.get("direction")),
        ])
    # Trend identity must survive movement of individual supporting records.  A
    # controlled object/cluster key is the underlying thing being pulled, not one
    # transient evidence claim.
    if grammar == "opposing_movements" and clean(c.get("trend_key")):
        return "|".join([grammar, clean(c.get("trend_key"))])
    endpoints = [clean(x) for x in c.get("endpoint_objects", []) if clean(x)] if isinstance(c.get("endpoint_objects"), list) else []
    if not endpoints:
        for key in ("capability_object", "dependency_object", "object", "cluster", "objective_object", "delivery_object"):
            if clean(c.get(key)):
                endpoints.append(clean(c.get(key)))
    if not endpoints:
        endpoints = sorted(clean(x) for x in c.get("claim_ids", []) if clean(x))[:4]
    return "|".join([grammar, *endpoints])


def _candidate_id(c: dict[str, Any]) -> str:
    key = _candidate_key(c)
    return "claim:" + clean(c.get("grammar_id") or "finding") + ":" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:14]


def _product_for(c: dict[str, Any]) -> str:
    if clean(c.get("product")) in {"risk", "shock", "opportunity", "trend", "continuity"}:
        return clean(c.get("product"))
    grammar = clean(c.get("grammar_id"))
    if grammar == "opposing_movements":
        return "trend"
    if grammar in {"latent_channel", "anchor_demand"}:
        return "opportunity"
    if grammar in {"conflicting_criteria", "clock_before_rule", "deployment_before_rules", "practice_before_doctrine", "goal_without_measure", "success_metric_gap", "stalled_proposal"}:
        return "risk"
    if grammar in {"named_continuity", "era_conjunction", "split_recurrence"}:
        return "continuity"
    return "continuity"


def _canonical_support_identity(node: dict[str, Any], snap: dict[str, Any]) -> str:
    """Return the downstream-retrace identity spelling for a claim support row.

    The claim graph uses record_key values such as ``link:https://...`` internally,
    while the existing downstream integrity checker indexes surviving evidence as
    ``url:https://...`` (or a deterministic title/source/date fallback).  Live
    claim-native candidates must store the latter so retrace can resolve every
    support reference after the Stage-6 detector switch.
    """
    rk = clean(snap.get("record_key") or node.get("record_key"))
    link = clean(node.get("_link"))
    if not link and rk.startswith("link:"):
        link = rk[5:]
    if link:
        return "url:" + link.lower().rstrip("/")
    title = re.sub(r"[^a-z0-9]+", " ", _low(snap.get("title") or node.get("_title"))).strip()
    source = re.sub(r"[^a-z0-9]+", " ", _low(snap.get("source") or node.get("_source"))).strip()
    date = clean(snap.get("status_date") or node.get("status_date"))[:10]
    if title or source or date:
        return "title:" + hashlib.sha1(f"{title}|{source}|{date}".encode("utf-8")).hexdigest()[:20]
    return rk or clean(snap.get("claim_id") or node.get("claim_id"))


def _strand_code(node: dict[str, Any]) -> str:
    """Normalize active-corpus collections to the public downstream strand codes.

    Frontier evidence is primary Strand A for downstream authority purposes;
    historical_context is always H/context.  This keeps the claim-native output
    aligned with R-09 and with downstream retrace semantics.
    """
    collection = clean(node.get("_collection"))
    if collection in {"strand_a", "frontier_evidence"}:
        return "A"
    if collection == "strand_c":
        return "C"
    if collection == "historical_context" or clean(node.get("era")) == "historical":
        return "H"
    return clean(collection).replace("strand_", "").upper()


def _support_rows(c: dict[str, Any], node_by_claim: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    snaps: list[dict[str, Any]] = []
    roles = c.get("roles") if isinstance(c.get("roles"), dict) else {}
    for role, snap in roles.items():
        if not isinstance(snap, dict):
            continue
        cid = clean(snap.get("claim_id"))
        node = node_by_claim.get(cid, {})
        rk = clean(snap.get("record_key") or node.get("record_key"))
        link = clean(node.get("_link")) or (rk[5:] if rk.startswith("link:") else "")
        snaps.append({
            "identity": _canonical_support_identity(node, snap),
            "claim_id": cid,
            "role": clean(role),
            "strand": _strand_code(node),
            "title": clean(snap.get("title") or node.get("_title")),
            "source": clean(snap.get("source") or node.get("_source")),
            "date": clean(snap.get("status_date") or node.get("status_date")),
            "link": link,
            "quality": int(round(float(snap.get("merit", node.get("merit", 0)) or 0))),
            "new_this_scan": bool(node.get("_new_this_scan")),
            "analytical_weight": round(float(snap.get("strength", 0) or 0), 3),
            "claim_primary": bool(node.get("_primary")),
            "claim_context_weight": round(float(node.get("_context_weight", 1.0) or 0), 3),
            "claim_origin": clean(node.get("origin")),
            "claim_kind": clean(node.get("kind")),
            "claim_status": clean(snap.get("status") or node.get("status")),
            "claim_merit": float(snap.get("merit", node.get("merit", 0)) or 0),
            "mechanism": clean(snap.get("mechanism") or node.get("mechanism")),
            "object": clean(snap.get("object")),
        })
    # Level-2/3 candidates often store claim ids directly instead of role snapshots.
    ids: list[str] = []
    for key in ("claim_ids", "rule_claim_ids"):
        if isinstance(c.get(key), list):
            ids.extend(clean(x) for x in c[key] if clean(x))
    for key in ("commitment_claim_id", "practice_claim_id", "doctrine_claim_id", "delivery_claim_id", "success_claim_id", "proposal_claim_id", "deployment_claim_id", "first_adopted_rule_claim_id", "success_condition_claim_id", "delivery_instrument_claim_id", "relation_claim_id"):
        if clean(c.get(key)):
            ids.append(clean(c.get(key)))
    existing = {x.get("claim_id") for x in snaps}
    for cid in ids:
        if cid in existing:
            continue
        node = node_by_claim.get(cid)
        if not node:
            continue
        rk = clean(node.get("record_key"))
        snaps.append({
            "identity": _canonical_support_identity(node, {"claim_id": cid}), "claim_id": cid, "role": "support",
            "strand": _strand_code(node),
            "title": clean(node.get("_title")), "source": clean(node.get("_source")),
            "date": clean(node.get("status_date")), "link": rk[5:] if rk.startswith("link:") else clean(node.get("_link")),
            "quality": int(round(float(node.get("merit", 0) or 0))), "new_this_scan": bool(node.get("_new_this_scan")),
            "analytical_weight": round(float(node.get("_context_weight", 1.0) or 0), 3),
            "claim_primary": bool(node.get("_primary")),
            "claim_context_weight": round(float(node.get("_context_weight", 1.0) or 0), 3),
            "claim_origin": clean(node.get("origin")),
            "claim_kind": clean(node.get("kind")),
            "claim_status": clean(node.get("status")),
            "claim_merit": float(node.get("merit", 0) or 0),
            "mechanism": clean(node.get("mechanism")),
            "object": clean(node.get("object")),
        })
    return snaps


def _falsifier_queries(c: dict[str, Any]) -> list[str]:
    g = clean(c.get("grammar_id"))
    eps = [clean(x) for x in c.get("endpoint_objects", []) if clean(x)] if isinstance(c.get("endpoint_objects"), list) else []
    a = eps[0] if eps else clean(c.get("capability_object") or c.get("object"))
    b = eps[1] if len(eps) > 1 else clean(c.get("dependency_object"))
    qs: list[str] = []
    if g == "dependency_pathway" and a and b:
        qs = [f"{b} exemption {a}", f"{a} site {b} secured", f"{a} hosting agreement {b} pre-cleared"]
    elif g == "conflicting_criteria" and a and b:
        qs = [f"{a} common rule {b}", f"{b} does not apply to {a}", f"{a} single procedure all members"]
    elif g == "anchor_demand" and a and b:
        qs = [f"{a} award {b} threshold", f"{a} vendor requirement {b}"]
    elif g == "split_recurrence" and a and b:
        qs = [f"{b} follows programme rules only", f"{a} conditions unrelated agreements"]
    elif a and b:
        qs = [f"{a} {b} substitution resilience alternative capacity", f"{a} {b} evidence safeguards do not constrain"]
    elif a:
        qs = [f"{a} substitution resilience alternative capacity", f"{a} evidence safeguards do not constrain"]
    return list(dict.fromkeys(clean(q) for q in qs if clean(q)))[:5]


def _support_queries(c: dict[str, Any]) -> list[str]:
    missing = [clean(x) for x in c.get("missing_roles", []) if clean(x)] if isinstance(c.get("missing_roles"), list) else []
    eps = [clean(x) for x in c.get("endpoint_objects", []) if clean(x)] if isinstance(c.get("endpoint_objects"), list) else []
    if not missing:
        return []
    base = " ".join(eps) or clean(c.get("object") or c.get("capability_object"))
    return [clean(f"{base} {role} evidence Europe research innovation") for role in missing[:3] if base]


def _finite_json_number(value: Any) -> float | int | None:
    """Return only RFC-8259-safe numeric values for persisted Radar JSON."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return number




def _node_objects(n: dict[str, Any]) -> set[str]:
    out = {clean(n.get("object"))}
    out.update(clean(x) for x in (n.get("secondary_objects") or []) if clean(x))
    return {x for x in out if x}


def _feedback_queries_executed(raw: dict[str, Any]) -> list[str]:
    """Exact finding-context queries that actually made a scholarly request this scan.

    scan_radar already commits the finding-context cursor only across a contiguous
    executed prefix.  Persisting that prefix here gives Stage 7 a candidate-specific
    falsifier execution ledger without widening scanner authority or guessing from a
    planned-but-unrun query.
    """
    results = raw.get("scan_results") if isinstance(raw.get("scan_results"), dict) else {}
    planned = results.get("finding_context_queries_this_scan") if isinstance(results.get("finding_context_queries_this_scan"), list) else []
    try:
        count = max(0, int(results.get("finding_context_queries_executed", 0) or 0))
    except (TypeError, ValueError):
        count = 0
    return [clean(q) for q in planned[:count] if clean(q)]


def _stake_class(obj: str, vocab: dict[str, Any]) -> str:
    meta = (vocab.get("objects") or {}).get(clean(obj), {})
    return clean(meta.get("stake_class")) if isinstance(meta, dict) else ""


def _against_rows(c: dict[str, Any], node_by_claim: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for cid in c.get("counter_claim_ids", []) if isinstance(c.get("counter_claim_ids"), list) else []:
        node = node_by_claim.get(clean(cid))
        if not node:
            continue
        rk = clean(node.get("record_key"))
        out.append({
            "identity": _canonical_support_identity(node, {"claim_id": cid}),
            "claim_id": clean(cid), "role": "counter-evidence",
            "strand": _strand_code(node),
            "title": clean(node.get("_title")), "source": clean(node.get("_source")),
            "date": clean(node.get("status_date")),
            "link": rk[5:] if rk.startswith("link:") else clean(node.get("_link")),
            "quality": int(round(float(node.get("merit", 0) or 0))),
            "new_this_scan": bool(node.get("_new_this_scan")),
            "claim_primary": bool(node.get("_primary")),
            "claim_kind": clean(node.get("kind")), "mechanism": clean(node.get("mechanism")),
            "object": clean(node.get("object")),
        })
    return out


def _endpoint_joint_count(nodes: Iterable[dict[str, Any]], a: str, b: str, *, era: str, excluded_records: set[str]) -> int:
    by_record: dict[str, set[str]] = {}
    for n in nodes:
        rid = clean(n.get("_record_id"))
        if not rid or rid in excluded_records or clean(n.get("era")) != era:
            continue
        by_record.setdefault(rid, set()).update(_node_objects(n))
    return sum(1 for objs in by_record.values() if a in objs and b in objs)


def _final_wow(raw_candidate: dict[str, Any], nodes: Iterable[dict[str, Any]], vocab: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    grammar = clean(raw_candidate.get("grammar_id"))
    if grammar == "era_conjunction":
        gain = float(raw_candidate.get("gain", 0) or 0)
        wow = 4 if gain >= 2.0 else 3 if gain >= 1.0 else 2
        return wow, {"mode": "era_gain", "gain": round(gain, 3)}
    if grammar == "opposing_movements":
        return 1, {"mode": "structural_trend"}
    eps = [clean(x) for x in raw_candidate.get("endpoint_objects", []) if clean(x)] if isinstance(raw_candidate.get("endpoint_objects"), list) else []
    if len(eps) < 2:
        # Level-3 sequence/gap findings are known-worry/new-turn by default unless
        # a grammar-specific exception above says otherwise.
        return int(raw_candidate.get("wow_preliminary", 3) or 3), {"mode": "sequence_gap"}
    claim_ids: set[str] = set()
    roles = raw_candidate.get("roles") if isinstance(raw_candidate.get("roles"), dict) else {}
    for snap in roles.values():
        if isinstance(snap, dict) and clean(snap.get("claim_id")):
            claim_ids.add(clean(snap.get("claim_id")))
    for key in ("claim_ids", "rule_claim_ids"):
        if isinstance(raw_candidate.get(key), list):
            claim_ids.update(clean(x) for x in raw_candidate.get(key, []) if clean(x))
    excluded = {clean(n.get("_record_id")) for n in nodes if clean(n.get("claim_id")) in claim_ids}
    cur = _endpoint_joint_count(nodes, eps[0], eps[1], era="current", excluded_records=excluded)
    hist = _endpoint_joint_count(nodes, eps[0], eps[1], era="historical", excluded_records=excluded)
    total = cur + hist
    clusters = []
    for obj in eps[:2]:
        meta = (vocab.get("objects") or {}).get(obj, {})
        clusters.append(clean(meta.get("cluster")) if isinstance(meta, dict) else "")
    stake = any(_stake_class(obj, vocab) in {"flagship", "rule", "budget", "capability"} for obj in eps)
    if total == 0 and len(set(x for x in clusters if x)) >= 2 and stake:
        wow = 5
    elif total <= 1:
        wow = 4
    elif total <= 5:
        wow = 3
    else:
        wow = 2
    return wow, {"mode": "endpoint_cooccurrence", "current": cur, "historical": hist, "total": total}


def _oddity_pass(c: dict[str, Any], vocab: dict[str, Any]) -> tuple[bool, str]:
    if clean(c.get("product")) == "trend" or int(c.get("wow", 0) or 0) <= 3:
        return True, "not_required"
    eps = [clean(x) for x in c.get("endpoint_objects", []) if clean(x)] if isinstance(c.get("endpoint_objects"), list) else []
    stakes = [x for x in eps if _stake_class(x, vocab) in {"flagship", "rule", "budget", "capability"}]
    if not stakes:
        return False, "no_flagship_rule_budget_or_capability_at_stake"
    if len(c.get("support", []) if isinstance(c.get("support"), list) else []) < 2:
        return False, "mechanism_not_grounded_across_records"
    if not (c.get("falsifier_queries") or c.get("support_queries")):
        return False, "no_concrete_watch_item"
    return True, "passes"


def _title_tokens(value: Any) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", _low(value)) if len(x) > 2}


def _near_same_action(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if clean(a.get("status_date")) != clean(b.get("status_date")):
        return False
    ta, tb = _title_tokens(a.get("_title")), _title_tokens(b.get("_title"))
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    overlap = inter / max(1, len(ta | tb))
    containment = inter / max(1, min(len(ta), len(tb)))
    return overlap >= .72 or containment >= .88


def _trend_side(rows: list[dict[str, Any]], evaluated_on: dt.date) -> tuple[list[dict[str, Any]], float, int]:
    # R-54: collapse near-duplicate reporting of one action, retaining the
    # highest-merit row and applying corroboration rather than false independence.
    groups: list[list[dict[str, Any]]] = []
    for row in sorted(rows, key=lambda n: (clean(n.get("status_date")), float(n.get("merit", 0) or 0)), reverse=True):
        placed = False
        for group in groups:
            if any(_near_same_action(row, x) for x in group):
                group.append(row); placed = True; break
        if not placed:
            groups.append([row])
    representatives: list[tuple[dict[str, Any], float]] = []
    for group in groups:
        best = max(group, key=lambda n: float(n.get("merit", 0) or 0))
        extra_sources = max(0, len({clean(n.get("_source")).lower() for n in group if clean(n.get("_source"))}) - 1)
        representatives.append((best, min(1.3, 1 + .1 * extra_sources)))
    source_seen: Counter[str] = Counter()
    total = 0.0
    kept: list[dict[str, Any]] = []
    for row, corroboration in representatives:
        src = clean(row.get("_source")).lower()
        source_seen[src] += 1
        independence = 1.0 if source_seen[src] == 1 else .5 if source_seen[src] == 2 else .25 if source_seen[src] == 3 else .125
        d = _date_only(row.get("status_date"))
        try:
            age = (evaluated_on - dt.date.fromisoformat(d)).days if len(d) == 10 else 999
        except ValueError:
            age = 999
        freshness = 1.0 if age <= 90 else .85 if age <= 180 else .70
        kind = {"action":1.0,"effect":.9,"diagnosis":.7,"advocacy":.5}.get(clean(row.get("kind")), .5)
        status = {"operating":1.0,"in_force":1.0,"adopted":.9,"announced":.8,"call_open":.8,"delivered":.8,"in_negotiation":.6,"proposed":.5,"intention":.3}.get(clean(row.get("status")), 0.0)
        attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
        actor = row.get("actor") if isinstance(row.get("actor"), dict) else {}
        witness = 1.2 if attrs.get("hostile_witness") is True and clean(actor.get("class")) in {"eu_body","member_state","national_funder"} else 1.0
        total += (float(row.get("merit", 0) or 0) / 100.0) * kind * status * independence * freshness * witness * corroboration
        kept.append(row)
    return kept, round(total, 6), len({clean(r.get("_source")).lower() for r in rows if clean(r.get("_source"))})


def _trend_scope_label(scope_kind: str, scope_key: str) -> str:
    del scope_kind
    text = clean(scope_key).replace(".", " ").replace("_", " ")
    aliases = {
        "compute capacity": "compute capacity",
        "research collaboration": "research collaboration",
        "research system governance": "research-system governance",
        "research infrastructure": "research infrastructure",
        "research system capacity": "research-system capacity",
        "industrial competitiveness": "industrial competitiveness",
        "innovation system performance": "innovation-system performance",
        "goal strategic autonomy": "strategic autonomy",
        "horizon budget 2028 34": "the next Horizon budget",
        "research security screening": "research-security screening",
        "talent retention": "researcher retention",
        "ai governance": "AI governance",
    }
    return aliases.get(text, text or "this object")


def _trend_payload(
    raw_candidate: dict[str, Any],
    nodes: list[dict[str, Any]],
    evaluated_on: dt.date,
    vocab: dict[str, Any],
) -> dict[str, Any] | None:
    """R-50..R-59 trend payload over one controlled object.

    The stock and the shelf are intentionally separate. Once both opposing pulls
    exist, the pair is retained in stock. Reader publication still requires the
    stronger R-51 floor of >=3 current records and >=2 independent sources on each
    side. C-08 keeps this structural verification separate from Level-5 falsifiers.
    """
    del vocab
    obj = clean(raw_candidate.get("object"))
    if not obj:
        return None

    rows: list[dict[str, Any]] = []
    for n in nodes:
        if not n.get("_primary") or clean(n.get("era")) != "current" or obj not in _node_objects(n):
            continue
        scope = n.get("scope") if isinstance(n.get("scope"), dict) else {}
        if clean(scope.get("level")) not in {"eu", "member_state", "associated_country", "company_in_eu"}:
            continue
        d = _date_only(n.get("status_date"))
        try:
            if len(d) == 10 and (evaluated_on - dt.date.fromisoformat(d)).days > 180:
                continue
        except ValueError:
            pass
        direction = clean(n.get("direction"))
        if direction == "expands" or direction in {"contracts", "becomes_conditional", "becomes_contested"}:
            rows.append(n)

    def side_of(n: dict[str, Any]) -> str:
        return "expands" if clean(n.get("direction")) == "expands" else "constrains"

    # R-53: a record carrying both sides is context, not two votes.
    by_record: dict[str, set[str]] = {}
    for n in rows:
        by_record.setdefault(clean(n.get("_record_id")), set()).add(side_of(n))
    rows = [n for n in rows if len(by_record.get(clean(n.get("_record_id")), set())) == 1]

    left = [n for n in rows if side_of(n) == "expands"]
    right = [n for n in rows if side_of(n) == "constrains"]
    if not {clean(n.get("_record_id")) for n in left if clean(n.get("_record_id"))}:
        return None
    if not {clean(n.get("_record_id")) for n in right if clean(n.get("_record_id"))}:
        return None

    lk, lw, lsrc = _trend_side(left, evaluated_on)
    rk, rw, rsrc = _trend_side(right, evaluated_on)
    left_records = {clean(n.get("_record_id")) for n in lk if clean(n.get("_record_id"))}
    right_records = {clean(n.get("_record_id")) for n in rk if clean(n.get("_record_id"))}
    if not left_records or not right_records:
        return None

    evidence_floor_passes = (
        len(left_records) >= 3
        and len(right_records) >= 3
        and lsrc >= 2
        and rsrc >= 2
    )

    raw_left = 100 * len(left_records) / max(1, len(left_records) + len(right_records))
    adj_left = 100 * lw / max(.000001, lw + rw)
    raw_left = max(15.0, min(85.0, raw_left))
    adj_left = max(15.0, min(85.0, adj_left))
    low, high = sorted((raw_left, adj_left))
    width = high - low

    thin = len(left_records) == 3 or len(right_records) == 3 or lsrc == 2 or rsrc == 2
    if not evidence_floor_passes:
        label = "under_watch"
    elif thin:
        label = "thin"
    elif width <= 8 and lsrc >= 4 and rsrc >= 4:
        label = "settled"
    else:
        label = "contested_by_source_mix" if width > 8 else "balanced"

    def snaps(xs: list[dict[str, Any]], role: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        seen_records: set[str] = set()
        for n in xs:
            rid = clean(n.get("_record_id"))
            if rid in seen_records:
                continue
            seen_records.add(rid)
            rk0 = clean(n.get("record_key"))
            out.append({
                "identity": _canonical_support_identity(n, {"claim_id": n.get("claim_id")}),
                "claim_id": clean(n.get("claim_id")),
                "role": role,
                "strand": _strand_code(n),
                "title": clean(n.get("_title")),
                "source": clean(n.get("_source")),
                "date": clean(n.get("status_date")),
                "link": rk0[5:] if rk0.startswith("link:") else clean(n.get("_link")),
                "quality": int(round(float(n.get("merit", 0) or 0))),
                "new_this_scan": bool(n.get("_new_this_scan")),
                "claim_primary": True,
                "claim_kind": clean(n.get("kind")),
                "claim_status": clean(n.get("status")),
                "mechanism": clean(n.get("mechanism")),
                "object": obj,
            })
        return out

    label_text = _trend_scope_label("object", obj)

    title_pairs = {
        "ai.governance": ("Turn AI governance into operating rules", "AI governance gets harder to reconcile"),
        "research.collaboration": ("Open more research partnerships", "Put more conditions around collaboration"),
        "innovation.system_performance": ("Push harder on innovation performance", "Structural bottlenecks keep holding performance back"),
        "goal.strategic_autonomy": ("Build more strategic autonomy", "Dependencies keep setting the terms"),
        "compute.capacity": ("Build more European computing capacity", "Power, supply and access constrain the build-out"),
        "research.system_governance": ("Strengthen research-system governance", "More conditions complicate research governance"),
        "research_security.screening": ("Make research-security screening routine", "Keep screening proportionate to open research"),
        "research.infrastructure": ("Build and open more research infrastructure", "Access and operating constraints tighten around it"),
        "industrial.competitiveness": ("Build more European industrial capability", "Cost and dependency pressures keep biting"),
        "research.system_capacity": ("Expand research-system capacity", "Capacity is being stretched or made conditional"),
        "talent.retention": ("Make Europe stickier for researchers", "Career and mobility frictions keep pulling people away"),
        "horizon.budget_2028_34": ("Put more money behind the next Horizon programme", "Frugal positions keep the budget under pressure"),
    }
    left_title, right_title = title_pairs.get(
        obj,
        (f"More {label_text}", f"{label_text[:1].upper()+label_text[1:]} under tighter conditions"),
    )

    mechanism_labels = {
        "procures": "procurement", "builds": "build-outs", "funds": "funding",
        "collaborates": "partnerships", "associates": "association agreements",
        "supports": "support instruments", "adopts": "adopted measures",
        "launches": "new programmes", "invests": "investment", "requires": "requirements",
        "conditions": "conditions", "restricts": "restrictions", "regulates": "rules",
        "screens": "screening", "assesses": "documented constraints",
    }
    def mechanism_phrase(rows: list[dict[str, Any]]) -> str:
        counts = Counter(clean(n.get("mechanism")) for n in rows if clean(n.get("mechanism")))
        labels = [mechanism_labels.get(k, k.replace("_", " ")) for k, _ in counts.most_common(2)]
        return " and ".join(labels) if labels else "independent current evidence"

    def concrete_count(rows: list[dict[str, Any]]) -> int:
        return sum(1 for n in rows if clean(n.get("kind")) in {"action", "effect"})

    lcon, rcon = concrete_count(lk), concrete_count(rk)
    composition = (
        f"The expansion side has {lcon} concrete action/effect record{'s' if lcon != 1 else ''} out of {len(lk)}; "
        f"the constraining side has {rcon} out of {len(rk)}. The rest are diagnoses or positions that explain the pressure."
    )
    left_plain = f"Current evidence is adding or widening {label_text} through {mechanism_phrase(lk)}."
    right_plain = f"Current evidence is making {label_text} more conditional or constrained through {mechanism_phrase(rk)}."

    pending = {"intention", "proposed", "in_negotiation", "announced", "call_open"}
    left_pending = sorted({clean(n.get("status")) for n in lk if clean(n.get("status")) in pending})
    right_pending = sorted({clean(n.get("status")) for n in rk if clean(n.get("status")) in pending})
    def status_trigger(statuses: list[str], fallback: str) -> str:
        if not statuses:
            return fallback
        words = [x.replace("_", " ") for x in statuses[:2]]
        if len(words) == 1:
            return f"{words[0]} measures"
        return f"{' or '.join(words)} measures"
    left_trigger = status_trigger(left_pending, "current expansion measures")
    right_trigger = status_trigger(right_pending, "current constraining measures")
    flip = (
        f"The balance moves toward expansion if {left_trigger} become adopted or operating; "
        f"toward constraint if {right_trigger} become adopted or in force."
    )
    return {
        "support": snaps(lk, "Expands") + snaps(rk, "Constrains"),
        "object": obj,
        "trend_scope": "object",
        "trend_key": f"object:{obj}",
        "trend_evidence_floor_passes": evidence_floor_passes,
        "trend_balance": {
            "family": "claim_native_object",
            "scope_kind": "object",
            "object_key": obj,
            "left_role": "Expands",
            "right_role": "Constrains",
            "left_title": left_title,
            "right_title": right_title,
            "left_plain": left_plain,
            "right_plain": right_plain,
            "raw_left_pull": round(raw_left, 1),
            "raw_right_pull": round(100 - raw_left, 1),
            "left_pull": round(adj_left, 1),
            "right_pull": round(100 - adj_left, 1),
            "left_range": [round(low, 1), round(high, 1)],
            "right_range": [round(100 - high, 1), round(100 - low, 1)],
            "band_width": round(width, 1),
            "label": label,
            "composition": composition,
            "flip_line": flip,
            "left_sources": lsrc,
            "right_sources": rsrc,
            "left_records": len(left_records),
            "right_records": len(right_records),
            "left_actions": len(left_records),
            "right_actions": len(right_records),
            "evidence_floor_passes": evidence_floor_passes,
        },
    }


def _apply_falsifier_ledger(c: dict[str, Any], old: dict[str, Any] | None, executed_queries: set[str], now: str) -> None:
    prior = copy.deepcopy(old.get("falsifier_results", [])) if isinstance(old, dict) and isinstance(old.get("falsifier_results"), list) else []
    seen = {clean(x.get("query")) for x in prior if isinstance(x, dict)}
    fresh_against = [x for x in c.get("against", []) if isinstance(x, dict) and x.get("new_this_scan")]
    for q in c.get("falsifier_queries", []) if isinstance(c.get("falsifier_queries"), list) else []:
        q = clean(q)
        if not q or q not in executed_queries or q in seen:
            continue
        hit = bool(fresh_against)
        prior.append({"query": q, "executed_at": now, "result": "hit" if hit else "miss", "killing_claim_ids": [clean(x.get("claim_id")) for x in fresh_against] if hit else []})
        seen.add(q)
    c["falsifier_results"] = prior
    c["falsifier_executed"] = bool(prior)
    c["denial_tested"] = bool(prior)
    if any(isinstance(x, dict) and x.get("result") == "hit" for x in prior):
        c["status"] = "killed"
        c["reader_eligible"] = False
        c["publication_gate_passes"] = False
        c["lifecycle"] = "killed_by_falsifier"


def _story_key(c: dict[str, Any]) -> tuple[str, str]:
    """Stable duplicate-story key used only for page folding.

    Trend pairs are already defined by a controlled object/cluster scope and must not
    be folded merely because one supporting action uses the same mechanism as another
    pair.  Other products retain the mechanism + endpoint fold used in Stage 7.
    """
    if clean(c.get("product")) == "trend":
        return "trend", clean(c.get("trend_key") or c.get("topic_key"))
    support = [x for x in c.get("support", []) if isinstance(x, dict)] if isinstance(c.get("support"), list) else []
    mechanism = clean(next((x.get("mechanism") for x in support if clean(x.get("mechanism"))), c.get("grammar_id")))
    objects = [clean(x) for x in c.get("endpoint_objects", []) if clean(x)] if isinstance(c.get("endpoint_objects"), list) else []
    obj = objects[0] if objects else clean(c.get("topic_key"))
    return mechanism, obj


# Verification is grammar-specific.  C-08 explicitly says trends use their own
# evidence discipline instead of a Level-5 falsifier.  These structural grammars are
# themselves bounded graph tests over authoritative claims: their finding is the
# observed sequence/gap.  Level-5 cross-evidence hypotheses still require an actually
# executed candidate-specific falsifier before reader publication.
_STRUCTURAL_VERIFICATION_GRAMMARS = {
    "era_conjunction",
    "practice_before_doctrine",
    "deployment_before_rules",
    "clock_before_rule",
    "goal_without_measure",
    "stalled_proposal",
    "success_metric_gap",
    "named_continuity",
}


def _verification_gate(c: dict[str, Any]) -> tuple[bool, str]:
    product = clean(c.get("product"))
    grammar = clean(c.get("grammar_id"))
    if product == "trend" or grammar == "opposing_movements":
        return bool(c.get("trend_evidence_floor_passes")), "trend_evidence_floor"
    if grammar == "corroborated_claim":
        # R-25 is already an explicit two-independent-source depth gate.  Requiring a
        # Level-5 candidate falsifier here would collapse the baseline and recreate
        # the Stage-7 starvation bug at a lower level.
        return (
            bool(c.get("score_gate_passes"))
            and int(c.get("primary_records", 0) or 0) >= 2
            and int(c.get("primary_sources", 0) or 0) >= 2
        ), "corroborated_claim_floor"
    if grammar in _STRUCTURAL_VERIFICATION_GRAMMARS:
        return True, "authoritative_graph_structure"
    return bool(c.get("denial_tested")), "executed_candidate_falsifier"


def _selection_rank(c: dict[str, Any]) -> tuple[int, int, int, int]:
    if clean(c.get("product")) == "trend":
        # Trend page order is an evidence-strength order.  A balanced composition band
        # is useful, but it must never outrank independent records/sources.
        return (
            int(c.get("primary_sources", 0) or 0),
            int(c.get("primary_records", 0) or 0),
            int(c.get("score", 0) or 0),
            int(c.get("wow", 0) or 0),
        )
    return (
        int(c.get("wow", 0) or 0),
        int(c.get("inferential_distance", c.get("level", 0)) or 0),
        int(c.get("score", 0) or 0),
        int(c.get("primary_sources", 0) or 0),
    )


def _select_stage7(candidates: list[dict[str, Any]], previous_state: dict[str, Any]) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Select a visible page from a much larger persistent analytical stock.

    Stage 7 originally conflated three different things: candidate formation,
    verification, and page capacity.  That made a publication-quality falsifier an
    accidental candidate-admission rule and let the soft-target code lift the wow
    floor until *nothing* was shown.  The corrected selector keeps those jobs apart:

    * formation/status is decided by the grammar;
    * verification is grammar-specific (trend floor / graph structure / L5 falsifier);
    * adaptive shelf thresholds choose among verified candidates and leave the rest in reserve;
    * incumbents move slowly, with a six-point same-wow challenger threshold.
    """
    targets = {
        "shock": (1, 4),
        "trend": (4, 10),
        "continuity": (2, 5),
        "risk": (2, 5),
        "opportunity": (2, 5),
    }
    prev_pubs = previous_state.get("publications") if isinstance(previous_state.get("publications"), dict) else {}
    prev_map = {
        clean(x.get("id")): x
        for x in previous_state.get("candidates", [])
        if isinstance(x, dict) and clean(x.get("id"))
    }
    out = {k: [] for k in targets}
    meta: dict[str, Any] = {}

    for product, (floor_target, ceil_target) in targets.items():
        pool = [
            c for c in candidates
            if c.get("claim_native") and clean(c.get("product")) == product
        ]
        for c in pool:
            verified, mode = _verification_gate(c)
            c["verification_mode"] = mode
            c["verification_gate_passes"] = bool(verified)
            c["reader_eligible"] = False
            c["publication_gate_passes"] = False

        # R-71/R-74: wow >=3 is the *top-of-page* floor for risks, opportunities
        # and ongoing phenomena, not a deletion rule.  Verified wow-1/2 findings are
        # the baseline and may appear beneath stronger findings when shelf space is
        # available.  Shocks remain exceptional and therefore keep the hard wow>=4
        # eligibility gate; trends use their own structural evidence floor.
        wow_floor = 0 if product == "trend" else (4 if product == "shock" else 3)
        verified_pool = [
            c for c in pool
            if c.get("status") == "qualified"
            and c.get("verification_gate_passes")
            and c.get("oddity_passes")
        ]
        eligible = [
            c for c in verified_pool
            if product != "shock" or int(c.get("wow", 0) or 0) >= wow_floor
        ]
        eligible.sort(key=_selection_rank, reverse=True)

        prev_ids_ordered = [
            clean(cid) for cid in (prev_pubs.get(product, []) if isinstance(prev_pubs.get(product), list) else [])
            if clean(cid)
        ]
        eligible_by_id = {clean(c.get("id")): c for c in eligible}

        # Fold exact same-story alternatives first.  The stronger candidate owns the
        # visible slot; the other remains a reserve with an explicit relation.
        deduped: list[dict[str, Any]] = []
        folded = 0
        for cand in eligible:
            conflict = next((x for x in deduped if _story_key(x) == _story_key(cand)), None)
            if conflict is None:
                deduped.append(cand)
                continue
            incumbent = clean(conflict.get("id")) in set(prev_ids_ordered)
            challenger = clean(cand.get("id")) not in set(prev_ids_ordered)
            replace = _selection_rank(cand) > _selection_rank(conflict)
            if incumbent and challenger and int(cand.get("wow", 0) or 0) == int(conflict.get("wow", 0) or 0):
                replace = int(cand.get("score", 0) or 0) >= int(conflict.get("score", 0) or 0) + 6
            if replace:
                conflict["folded_into"] = cand.get("id")
                conflict["movement"] = "reserve"
                deduped.remove(conflict)
                deduped.append(cand)
            else:
                cand["folded_into"] = conflict.get("id")
                cand["movement"] = "reserve"
                conflict.setdefault("also_ids", []).append(cand.get("id"))
            folded += 1
        deduped.sort(key=_selection_rank, reverse=True)

        def stable_take(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
            """Choose a small threshold-fallback set without page churn.

            This is used only when an adaptive threshold would otherwise under-fill
            the soft minimum.  Existing visible items keep their place until an
            equal-wow challenger is at least six score points stronger (R-76); a
            higher-wow challenger enters immediately.
            """
            if count <= 0:
                return []
            ranked = sorted(items, key=_selection_rank, reverse=True)
            by_id_local = {clean(c.get("id")): c for c in ranked if clean(c.get("id"))}
            selected: list[dict[str, Any]] = []
            selected_ids: set[str] = set()
            for cid in prev_ids_ordered:
                c = by_id_local.get(cid)
                if c is not None and cid not in selected_ids and len(selected) < count:
                    selected.append(c); selected_ids.add(cid)
            for c in ranked:
                cid = clean(c.get("id"))
                if not cid or cid in selected_ids:
                    continue
                if len(selected) < count:
                    selected.append(c); selected_ids.add(cid)
                    continue
                weakest = min(selected, key=_selection_rank)
                if product == "trend":
                    displace = _selection_rank(c) > _selection_rank(weakest)
                else:
                    cw, ww = int(c.get("wow", 0) or 0), int(weakest.get("wow", 0) or 0)
                    displace = cw > ww or (cw == ww and int(c.get("score", 0) or 0) >= int(weakest.get("score", 0) or 0) + 6)
                if displace:
                    selected.remove(weakest); selected_ids.discard(clean(weakest.get("id")))
                    selected.append(c); selected_ids.add(cid)
            return sorted(selected, key=_selection_rank, reverse=True)

        def adaptive_score_band(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int | None]:
            """Use an evidence-score threshold to curate an overcrowded same-wow band.

            The target range chooses a *threshold*, never the first N records.  Ties are
            allowed to make the visible shelf slightly larger than the nominal range,
            which preserves the specification's no-hard-cap rule.
            """
            ranked = sorted(items, key=_selection_rank, reverse=True)
            if len(ranked) <= ceil_target:
                return ranked, None
            scores = sorted({int(c.get("score", 0) or 0) for c in ranked}, reverse=True)
            viable: list[tuple[int, int, list[dict[str, Any]]]] = []
            for threshold in scores:
                selected = [c for c in ranked if int(c.get("score", 0) or 0) >= threshold]
                if len(selected) >= floor_target:
                    # Prefer a threshold that lands inside the soft range; otherwise
                    # choose the smallest overflow.  Lower thresholds win ties so the
                    # shelf remains inclusive rather than brittle.
                    overflow = 0 if len(selected) <= ceil_target else len(selected) - ceil_target
                    viable.append((overflow, -len(selected), selected))
            if viable:
                viable.sort(key=lambda x: (x[0], x[1]))
                selected = viable[0][2]
                threshold = min(int(c.get("score", 0) or 0) for c in selected) if selected else None
                return selected, threshold
            return stable_take(ranked, floor_target), None

        # R-72 is a *soft target*, not a slot count.  The earlier cutover still
        # stopped at ceil_target (5 for risks/opportunities, 10 for trends), which
        # silently turned the target range into a hard cap.  Selection now works by
        # threshold: when the ordinary top-of-page band is overcrowded, strengthen
        # the relevant evidence/wow/depth floor.  Whatever clears that stronger
        # threshold is shown; verified surplus remains reserve.  The target range
        # therefore guides curation but never limits candidate generation.
        prev_ids = set(prev_ids_ordered)
        chosen: list[dict[str, Any]] = []

        if product == "trend":
            # Trends have no wow floor, so an overcrowded shelf is tightened by the
            # *evidence floor*, not by an arbitrary item count.  R-51 starts at
            # 3 records / 2 sources on each side.  When more than the soft upper
            # range clear that floor, prefer the stronger 4-record / 3-source band.
            # If that would under-fill the soft minimum, supplement with the
            # strongest ordinary-floor pairs only until the minimum is met.
            base = list(deduped)
            if len(base) > ceil_target:
                def stronger_trend_floor(c):
                    b = c.get("trend_balance") if isinstance(c.get("trend_balance"), dict) else {}
                    return (
                        int(b.get("left_records", 0) or 0) >= 4
                        and int(b.get("right_records", 0) or 0) >= 4
                        and int(b.get("left_sources", 0) or 0) >= 3
                        and int(b.get("right_sources", 0) or 0) >= 3
                    )
                chosen = [c for c in base if stronger_trend_floor(c)]
                if len(chosen) < floor_target:
                    chosen_ids_local = {clean(c.get("id")) for c in chosen}
                    remaining = [c for c in base if clean(c.get("id")) not in chosen_ids_local]
                    chosen.extend(stable_take(remaining, floor_target - len(chosen)))
                meta_trend_floor = "4_records_3_sources_each_side"
            else:
                chosen = base
                meta_trend_floor = "3_records_2_sources_each_side"
            wow_floor = 0
        elif product == "shock":
            # Shocks keep the exceptional wow>=4 gate.  Overcrowding raises the
            # floor to wow 5.  If that leaves fewer than the soft minimum, retain
            # only enough strongest wow-4 findings to keep a real shelf; the rest
            # remain verified reserve rather than being discarded or all displayed.
            base = [c for c in deduped if int(c.get("wow", 0) or 0) >= 4]
            higher = [c for c in base if int(c.get("wow", 0) or 0) >= 5]
            if len(base) > ceil_target:
                wow_floor = 5
                chosen = list(higher)
                if len(chosen) < floor_target:
                    chosen_ids_local = {clean(c.get("id")) for c in chosen}
                    remaining = [c for c in base if clean(c.get("id")) not in chosen_ids_local]
                    chosen.extend(stable_take(remaining, floor_target - len(chosen)))
            else:
                wow_floor = 4
                chosen = base
        else:
            # Risks, opportunities and continuities use wow>=3 for the upper shelf.
            # If that band is crowded, raise the floor to wow 4.  Crucially, when
            # the higher band is sparse we do *not* fall back to showing every
            # wow-3 item: we keep just enough strongest wow-3 findings to satisfy
            # the soft minimum, leaving the rest as verified reserve.  If the
            # ordinary top band itself is sparse, show the verified baseline that
            # actually exists (including wow 1-2) as R-72 requires.
            top = [c for c in deduped if int(c.get("wow", 0) or 0) >= 3]
            higher = [c for c in top if int(c.get("wow", 0) or 0) >= 4]
            if len(top) > ceil_target:
                if higher:
                    wow_floor = 4
                    chosen = list(higher)
                    if len(chosen) < floor_target:
                        chosen_ids_local = {clean(c.get("id")) for c in chosen}
                        # If wow alone cannot separate a crowded shelf, prefer findings
                        # built above the corroborated-claim baseline (depth >=3).  This
                        # keeps the page analytically richer without inventing a numeric
                        # cap; all other verified findings stay in reserve.
                        deeper = [
                            c for c in top
                            if clean(c.get("id")) not in chosen_ids_local
                            and int(c.get("inferential_distance", c.get("level", 0)) or 0) >= 3
                        ]
                        needed = max(0, floor_target - len(chosen))
                        if len(deeper) >= needed and deeper:
                            deep_band, _deep_threshold = adaptive_score_band(deeper)
                            chosen.extend(deep_band)
                        else:
                            chosen.extend(deeper)
                            chosen_ids_local = {clean(c.get("id")) for c in chosen}
                            remaining = [c for c in top if clean(c.get("id")) not in chosen_ids_local]
                            chosen.extend(stable_take(remaining, max(0, floor_target - len(chosen))))
                else:
                    # A crowded wow-3 band must not disappear merely because there is
                    # no wow-4 item yet.  Tighten by evidence score *inside the same
                    # wow band* and keep the strongest threshold band visible.
                    wow_floor = 3
                    chosen, _same_wow_threshold = adaptive_score_band(top)
                # R-74: if a lower wow point exists below the active shelf and is
                # not already represented by the minimum-fill step, keep one best
                # baseline representative.  Do not turn that baseline into a cap.
                for lower_wow in range(wow_floor - 1, 0, -1):
                    if any(int(c.get("wow", 0) or 0) == lower_wow for c in chosen):
                        continue
                    lower = [c for c in deduped if int(c.get("wow", 0) or 0) == lower_wow]
                    if lower:
                        chosen.append(max(lower, key=_selection_rank))
            elif len(top) >= floor_target:
                wow_floor = 3
                chosen = list(top)
                for lower_wow in (2, 1):
                    lower = [c for c in deduped if int(c.get("wow", 0) or 0) == lower_wow]
                    if lower:
                        chosen.append(max(lower, key=_selection_rank))
            else:
                wow_floor = 3
                # There is no crowded wow>=3 band.  Ordinary corroborated baseline
                # findings are therefore shown as they exist: the 2-5 target is not
                # a numeric cap (R-72).  Named continuities are a special structural
                # baseline because a mature archive can produce dozens of perfectly
                # valid Level-2 continuities at once.  For that product, strengthen
                # the *corroboration floor* in discrete source-breadth bands and show
                # everything that clears the strongest band which still supplies the
                # soft minimum.  This is an evidence threshold, not a first-N slice.
                if product == "continuity" and len(deduped) > ceil_target:
                    def continuity_breadth(c):
                        return int(c.get("current_source_count", 0) or 0) + int(c.get("historical_source_count", 0) or 0)
                    viable_bands = []
                    for source_floor in (40, 30, 20, 12, 8, 5):
                        band = [c for c in deduped if continuity_breadth(c) >= source_floor]
                        if len(band) >= floor_target:
                            overflow = 0 if len(band) <= ceil_target else len(band) - ceil_target
                            viable_bands.append((overflow, -len(band), source_floor, band))
                    if viable_bands:
                        viable_bands.sort(key=lambda x: (x[0], x[1], -x[2]))
                        chosen = list(viable_bands[0][3])
                        # The breadth floor is a curation threshold, not a reason to
                        # leave a mature continuity page almost empty.  Fill toward
                        # the soft upper range with the strongest remaining verified
                        # continuities; surplus still remains reserve.
                        if len(chosen) < ceil_target:
                            chosen_ids_local = {clean(c.get("id")) for c in chosen}
                            remaining = [c for c in deduped if clean(c.get("id")) not in chosen_ids_local]
                            chosen.extend(stable_take(remaining, ceil_target - len(chosen)))
                    else:
                        chosen = list(deduped)
                else:
                    chosen = list(deduped)

        # Preserve deterministic page order: wow first, then depth/evidence score.
        # Same-story hysteresis was already applied during the folding pass above.
        chosen = list({clean(c.get("id")): c for c in chosen if clean(c.get("id"))}.values())
        chosen.sort(key=_selection_rank, reverse=True)
        out[product] = [clean(c.get("id")) for c in chosen]
        chosen_ids = set(out[product])

        for c in pool:
            cid = clean(c.get("id"))
            old = prev_map.get(cid)
            verified = bool(c.get("verification_gate_passes"))
            if cid in chosen_ids:
                stable = bool(old) and int(c.get("wow", 0) or 0) == int(old.get("wow", 0) or 0) and int(c.get("score", 0) or 0) == int(old.get("score", 0) or 0) and not c.get("updated_this_scan")
                c["shown_unchanged_scans"] = (int(old.get("shown_unchanged_scans", 0) or 0) + 1) if stable else 0
                if product == "trend" and old and isinstance(old.get("trend_balance"), dict) and isinstance(c.get("trend_balance"), dict):
                    old_range = old["trend_balance"].get("left_range") or []
                    new_range = c["trend_balance"].get("left_range") or []
                    if len(old_range) >= 2 and len(new_range) >= 2 and max(abs(float(new_range[0])-float(old_range[0])), abs(float(new_range[1])-float(old_range[1]))) < 3:
                        c["trend_balance_computed"] = copy.deepcopy(c["trend_balance"])
                        c["trend_balance"] = copy.deepcopy(old["trend_balance"])
                        c["published_band_changed"] = False
                    else:
                        c["published_band_changed"] = True
                if cid not in prev_ids:
                    c["movement"] = "up"; c["reader_status_chip"] = "New"
                elif old and (int(c.get("wow", 0) or 0) > int(old.get("wow", 0) or 0) or int(c.get("score", 0) or 0) > int(old.get("score", 0) or 0)):
                    c["movement"] = "up"; c["reader_status_chip"] = "Rising"
                elif old and (int(c.get("wow", 0) or 0) < int(old.get("wow", 0) or 0) or int(c.get("score", 0) or 0) < int(old.get("score", 0) or 0) or int(c.get("missed_detection_scans", 0) or 0) >= 3):
                    c["movement"] = "down"; c["reader_status_chip"] = "Fading"
                elif int(c.get("wow", 0) or 0) == 5 and int(c.get("shown_unchanged_scans", 0) or 0) >= 6:
                    c["movement"] = "standing"; c["reader_status_chip"] = "Standing"
                elif c.get("updated_this_scan"):
                    c["movement"] = "hold"; c["reader_status_chip"] = "Updated"
                else:
                    c["movement"] = "hold"; c["reader_status_chip"] = "Unchanged"
                c["reader_eligible"] = True
                c["publication_gate_passes"] = True
                c["publication_lock_reason"] = ""
                c["stock_tier"] = "page"
            elif c.get("status") == "killed":
                c["movement"] = "killed"
                c["stock_tier"] = "killed"
            elif c.get("status") == "dormant":
                c["movement"] = "dormant"
                c["stock_tier"] = "dormant"
                c["publication_lock_reason"] = clean(c.get("exit_reason")) or "Dormant stock item; not active on the current shelf."
            elif c in eligible or clean(c.get("movement")) == "reserve":
                c["movement"] = "reserve"
                c["stock_tier"] = "reserve"
                c["publication_lock_reason"] = "Verified candidate held on the reserve shelf by page selection or same-story folding."
            else:
                c["movement"] = "watch"
                c["stock_tier"] = "watch"
                if c.get("status") != "qualified":
                    c["publication_lock_reason"] = "Candidate is still missing a grammar qualification condition."
                elif not verified:
                    if clean(c.get("verification_mode")) == "executed_candidate_falsifier":
                        c["publication_lock_reason"] = "Level-5 candidate is waiting for an executed candidate-specific falsifier."
                    elif product == "trend":
                        c["publication_lock_reason"] = "Trend remains in stock below the reader evidence floor."
                    else:
                        c["publication_lock_reason"] = "Candidate has not yet passed its grammar-specific verification gate."
                elif not c.get("oddity_passes"):
                    c["publication_lock_reason"] = "Candidate is held by the oddity/stakes gate."
                elif product != "trend" and int(c.get("wow", 0) or 0) < wow_floor:
                    c["publication_lock_reason"] = f"Candidate is below the reader wow floor ({wow_floor})."

        reserve = sum(1 for c in pool if clean(c.get("movement")) == "reserve")
        watch = sum(1 for c in pool if clean(c.get("movement")) == "watch")
        meta[product] = {
            "soft_target": [floor_target, ceil_target],
            "hard_cap": False,
            "wow_floor": wow_floor,
            "active_evidence_floor": meta_trend_floor if product == "trend" else "grammar_default",
            "verified_eligible": len(verified_pool),
            "top_floor_eligible": sum(1 for c in verified_pool if product == "trend" or int(c.get("wow", 0) or 0) >= wow_floor),
            "baseline_verified": sum(1 for c in verified_pool if product not in {"trend", "shock"} and int(c.get("wow", 0) or 0) < wow_floor),
            "shown": len(chosen),
            "reserve": reserve,
            "watch": watch,
            "folded": folded,
        }

    shown = [c for c in candidates if clean(c.get("id")) in {x for ids in out.values() for x in ids}]
    present = {int(c.get("wow", 0) or 0) for c in shown if clean(c.get("product")) != "trend"}
    meta["page_guarantee"] = {
        "present_wow_levels": sorted(present, reverse=True),
        "missing_wow_levels": [x for x in (5, 4, 3) if x not in present],
        "promotions_forbidden": True,
    }
    return out, meta

def _candidate_topic_label(grammar: str, topic: str) -> str:
    base = clean(topic).replace(".", " ").replace("_", " ") or "European R&I"
    suffix = {
        "practice_before_doctrine": "practice before doctrine",
        "deployment_before_rules": "deployment ahead of settled rules",
        "clock_before_rule": "delivery clock ahead of settled rules",
        "goal_without_measure": "goal without a settled measure",
        "stalled_proposal": "proposal/practice timing gap",
        "success_metric_gap": "delivery/outcome measurement gap",
        "era_conjunction": "current/historical conjunction",
        "conflicting_criteria": "criteria collision",
        "dependency_pathway": "dependency pathway",
        "latent_channel": "latent channel",
        "anchor_demand": "anchor-demand pathway",
        "split_recurrence": "recurring split",
        "corroborated_claim": "corroborated current finding",
    }.get(clean(grammar), "")
    return f"{base} — {suffix}" if suffix else base




def _friendly_object_label(value: Any) -> str:
    obj = clean(value)
    aliases = {
        "compute.public_procurement": "AI-factory public procurement",
        "compute.gigafactory": "AI-gigafactory capacity",
        "compute.capacity": "European computing capacity",
        "compute.private_investment": "private investment in European compute",
        "datacentre.permitting": "data-centre permitting",
        "datacentre.energy_supply": "data-centre power supply",
        "quantum.testing_infrastructure": "open quantum testing",
        "export_control.competence": "national export-control licensing",
        "export_control.regulation": "export-control rules",
        "research_security.screening": "research-security screening",
        "research.collaboration": "research collaboration",
        "research.system_governance": "research-system governance",
        "research.system_capacity": "research-system capacity",
        "research.infrastructure": "research infrastructure",
        "research.infrastructure_access": "access to research infrastructure",
        "research.public_support": "public research support",
        "innovation.system_performance": "innovation-system performance",
        "industrial.competitiveness": "industrial competitiveness",
        "innovation.dual_use": "dual-use innovation",
        "goal.strategic_autonomy": "strategic-autonomy goals",
        "talent.retention": "researcher retention",
        "talent.recruitment_abroad": "international researcher recruitment",
        "horizon.association": "Horizon association",
        "horizon.budget_2028_34": "the next Horizon budget",
        "materials.critical_raw": "critical raw-material supply",
        "finance.strategic_investment": "strategic investment finance",
        "finance.us_hyperscaler_debt_exposure": "European exposure to US AI debt",
        "finance.gulf_capital": "Gulf capital for European technology",
        "health.data_infrastructure": "European health-data infrastructure",
        "digital.sovereignty": "digital sovereignty",
        "ai.governance": "AI governance",
        "ai.adoption": "AI adoption",
        "defence.drone_capability": "European drone capability",
        "defence.innovation_funding": "defence-innovation funding",
    }
    if obj in aliases:
        return aliases[obj]
    text = obj.replace(".", " ").replace("_", " ")
    return clean(text) or "European research and innovation"


def _reader_copy(grammar: str, product: str, raw: dict[str, Any], candidate: dict[str, Any]) -> tuple[str, str]:
    eps = [clean(x) for x in raw.get("endpoint_objects", []) if clean(x)] if isinstance(raw.get("endpoint_objects"), list) else []
    a = _friendly_object_label(eps[0] if eps else raw.get("object") or raw.get("capability_object") or raw.get("objective_object"))
    b = _friendly_object_label(eps[1] if len(eps) > 1 else raw.get("dependency_object") or raw.get("delivery_object"))
    records = int(candidate.get("primary_records", 0) or 0)
    sources = int(candidate.get("primary_sources", 0) or 0)

    if grammar == "named_continuity":
        cur_s = int(raw.get("current_source_count", 0) or 0)
        hist_s = int(raw.get("historical_source_count", 0) or 0)
        title_map = {
            "research collaboration": "Research collaboration keeps changing shape, not disappearing.",
            "innovation-system performance": "Europe keeps returning to the same innovation-conversion problem.",
            "AI governance": "AI governance keeps moving from principles into operating rules.",
            "research-system governance": "Research governance keeps moving closer to delivery and competitiveness.",
            "strategic-autonomy goals": "Strategic autonomy keeps spreading through research and technology policy.",
            "research infrastructure": "Research infrastructure keeps becoming a strategic capability in its own right.",
            "researcher retention": "Researcher retention keeps returning as a capacity constraint.",
            "research-security screening": "Research security keeps moving into ordinary research administration.",
        }
        title = title_map.get(a, f"{a[:1].upper()+a[1:]} keeps returning across the research-policy cycle.")
        return title, f"The same controlled issue is supported by {cur_s} current and {hist_s} historical independent sources. The current form has changed, but the underlying issue has persisted across both eras."

    if grammar == "practice_before_doctrine":
        return f"{a[:1].upper()+a[1:]} is moving into practice before the rulebook catches up.", "Implementation is already visible in the evidence before a later doctrine or framework on the same object has settled. That timing can make provisional practice harden into the default."
    if grammar == "goal_without_measure":
        inv = int(raw.get("invocations", 0) or 0); meas = int(raw.get("measurements", 0) or 0)
        return f"{a[:1].upper()+a[1:]} is being invoked faster than it is being measured.", f"The evidence contains {inv} goal or action claims but only {meas} matching outcome measurements. The gap matters because activity can expand without showing whether the stated objective is being achieved."
    if grammar == "clock_before_rule":
        return f"The delivery clock is running before the rules are settled for {a}.", "A funded or scheduled delivery timetable is already running while the connected rules remain below the adopted stage. The risk is that implementation deadlines arrive before the governance conditions are fixed."
    if grammar == "deployment_before_rules":
        return f"{a[:1].upper()+a[1:]} is moving ahead of settled rules.", "Operating activity appears in the evidence before an adopted rule on the same object. Practice can therefore become established before governance catches up."
    if grammar == "success_metric_gap":
        return f"{a[:1].upper()+a[1:]} can be funded before success is properly measured.", "The stated objective and the delivery instrument are not the same thing, and the evidence base still lacks a matching outcome measure. Delivery can look successful before the intended result is known."
    if grammar == "stalled_proposal":
        return f"A proposal affecting {a} is ageing without a later decision.", "The proposal has remained below implementation for more than six months with no later status transition in the evidence base."
    if grammar == "conflicting_criteria":
        return f"{a[:1].upper()+a[1:]} is colliding with {b}.", "Separate records support both requirements, but the evidence base does not yet show a common tie-break. The same project or facility can therefore receive different answers depending on which rule is applied first."
    if grammar == "dependency_pathway":
        if product == "shock":
            return f"A sudden break in {b} could propagate into {a}.", "The disruptive event itself is not in the corpus, but separate records document the coupling, propagation route and European exposure. This is a possible discontinuity, not a forecast."
        return f"A bottleneck in {b} could propagate into {a}.", "Separate records connect a European capability to a dependency and show a route by which disruption could spread beyond one isolated project."
    if grammar == "latent_channel":
        return f"{b[:1].upper()+b[1:]} could become the missing route into {a}.", "The evidence contains both an unresolved need and an existing structure that could address it. A live connection between the two would turn existing pieces into a usable European capability rather than requiring a new system from scratch."
    if grammar == "anchor_demand":
        return f"{a[:1].upper()+a[1:]} could become an anchor customer for {b}.", "The evidence links a European commitment to a supplier or capability that could benefit from dependable public demand, with conditions that determine whether the demand converts into lasting European capacity."
    if grammar == "era_conjunction":
        return f"{a[:1].upper()+a[1:]} and {b} are becoming one story.", "The two objects co-occur much more strongly in current evidence than in the historical archive, suggesting a durable change in how the issues are coupled."
    if grammar == "split_recurrence":
        return f"An older link between {a} and {b} is returning without being named.", "A historical record states the relationship directly, while current evidence shows both sides moving again without a current record explicitly joining them."
    if grammar == "corroborated_claim":
        direction = clean(raw.get("direction")); mechanism = clean(raw.get("mechanism"))
        if product == "risk":
            verb = "is under sustained pressure" if direction == "contracts" else "is becoming more conditional" if direction == "becomes_conditional" else "is becoming more contested" if direction == "becomes_contested" else "shows a corroborated constraint"
            return f"{a[:1].upper()+a[1:]} {verb}.", f"{records} records from {sources} independent sources point in the same constraining direction. This is the corroborated baseline beneath the higher-order pathway findings."
        action = "is expanding through a live European instrument"
        if mechanism in {"collaborates", "associates"}: action = "is widening through active agreements"
        elif mechanism in {"procures", "builds", "adds_capacity"}: action = "is expanding through active capacity-building"
        elif mechanism == "funds": action = "is expanding through new funding"
        elif mechanism == "prioritises": action = "is being backed by adopted priorities"
        elif mechanism == "launches": action = "is moving into operation through new instruments"
        elif mechanism == "coordinates": action = "is gaining an active coordination route"
        elif mechanism == "invests": action = "is expanding through new investment"
        elif mechanism == "supports": action = "is expanding through a live support instrument"
        return f"{a[:1].upper()+a[1:]} {action}.", f"{records} records from {sources} independent sources point in the same constructive direction, with at least one live or operating instrument."
    return f"{a[:1].upper()+a[1:]}", clean(candidate.get("topic_label"))


def _reader_why(grammar: str, product: str, raw: dict[str, Any]) -> str:
    eps = [clean(x) for x in raw.get("endpoint_objects", []) if clean(x)] if isinstance(raw.get("endpoint_objects"), list) else []
    a = _friendly_object_label(eps[0] if eps else raw.get("object") or raw.get("capability_object") or raw.get("objective_object"))
    b = _friendly_object_label(eps[1] if len(eps) > 1 else raw.get("dependency_object") or raw.get("delivery_object"))
    if grammar == "clock_before_rule": return "Delivery choices can become locked in before permitting, power or other operating conditions are settled."
    if grammar == "success_metric_gap": return "Europe can spend more on an instrument while still not knowing whether the outcome it is meant to produce is improving."
    if grammar == "practice_before_doctrine": return "Early implementation can become the de facto rule before the formal framework has had a chance to arbitrate trade-offs."
    if grammar == "goal_without_measure": return "A goal can dominate policy language without creating an evidence base for whether interventions are working."
    if grammar == "conflicting_criteria": return f"The same European project can be treated differently depending on whether {a} or {b} is applied first."
    if grammar == "dependency_pathway" and product == "risk": return f"A failure in {b} would not stay local if the documented propagation route reaches {a}."
    if grammar == "dependency_pathway" and product == "shock": return f"A sudden disruption in {b} could remove capability faster than the documented European responses can absorb it."
    if grammar == "latent_channel": return "The opportunity is leverage: connect pieces Europe already has instead of creating a new programme from zero."
    if grammar == "anchor_demand": return "Reliable European demand can help turn research and scale-up support into durable production, suppliers and technical capability."
    if grammar == "named_continuity": return "Persistence matters because a recurring issue is more likely to shape future choices than a one-scan spike."
    if grammar == "corroborated_claim" and product == "risk": return "Independent sources are pointing in the same constraining direction, so the issue is broader than one publication or institution."
    if grammar == "corroborated_claim" and product == "opportunity": return "The constructive movement is already attached to a live instrument rather than remaining only an aspiration."
    return ""

def adapt_candidate(c: dict[str, Any], nodes: Iterable[dict[str, Any]], *, vocab: dict[str, Any] | None = None, evaluated_on: dt.date | None = None) -> dict[str, Any]:
    nodes = list(nodes)
    node_by_claim = {clean(n.get("claim_id")): n for n in nodes if clean(n.get("claim_id"))}
    vocab = vocab or {}
    evaluated_on = evaluated_on or dt.date.today()
    support = _support_rows(c, node_by_claim)
    grammar = clean(c.get("grammar_id"))
    if grammar == "goal_without_measure" and not support:
        obj0 = clean(c.get("object"))
        rows0 = [n for n in nodes if n.get("_primary") and clean(n.get("era")) == "current" and obj0 in _node_objects(n) and clean(n.get("kind")) in {"action", "advocacy", "effect"}]
        support = _support_rows({"claim_ids": [clean(n.get("claim_id")) for n in rows0[:16]]}, node_by_claim)
    elif grammar == "era_conjunction" and not support:
        eps0 = [clean(x) for x in c.get("endpoint_objects", []) if clean(x)] if isinstance(c.get("endpoint_objects"), list) else []
        if len(eps0) >= 2:
            rows0 = [n for n in nodes if eps0[0] in _node_objects(n) and eps0[1] in _node_objects(n)]
            support = _support_rows({"claim_ids": [clean(n.get("claim_id")) for n in rows0[:16]]}, node_by_claim)

    # R-09: only primary A/frontier and verified event-C claims may fill
    # downstream support. Historical and context-only C claims remain attached
    # to the candidate, but under context rather than support.
    context = [
        dict(ref, claim_primary=False)
        for ref in support
        if (not bool(ref.get("claim_primary"))) or clean(ref.get("strand")) == "H"
    ]
    support = [
        ref for ref in support
        if bool(ref.get("claim_primary")) and clean(ref.get("strand")) in {"A", "C"}
    ]
    against = _against_rows(c, node_by_claim)
    missing = [clean(x) for x in c.get("missing_roles", []) if clean(x)] if isinstance(c.get("missing_roles"), list) else []
    roles = c.get("roles") if isinstance(c.get("roles"), dict) else {}
    required = list(roles) if roles else (["evidence_floor"] if grammar == "opposing_movements" else (["support"] if support else []))
    covered = [r for r, snap in roles.items() if isinstance(snap, dict)] if roles else (["evidence_floor"] if grammar == "opposing_movements" else (["support"] if support else []))
    score = c.get("score")
    if score is None:
        score = 0
    score = max(0, min(99, int(round(float(score or 0)))))
    level = int(c.get("level", 5) or 5)
    structural_verified = grammar in _STRUCTURAL_VERIFICATION_GRAMMARS
    status = "qualified" if ((bool(c.get("score_gate_passes")) or structural_verified) and not missing) else "watch"
    product = _product_for(c)

    trend = _trend_payload(c, nodes, evaluated_on, vocab) if grammar == "opposing_movements" else None
    if grammar == "opposing_movements":
        if trend is None:
            status = "watch"
        else:
            # The 2x2 floor admits a living stock candidate; only the stronger 3x3,
            # 2-source-per-side floor qualifies it for the visible trend page.
            status = "qualified" if trend.get("trend_evidence_floor_passes") else "watch"
            support = trend["support"]

    topic = " × ".join(clean(x) for x in c.get("endpoint_objects", []) if clean(x)) if isinstance(c.get("endpoint_objects"), list) else ""
    topic = topic or clean(c.get("object") or c.get("cluster") or c.get("capability_object") or c.get("objective_object") or c.get("delivery_object") or c.get("grammar_id"))
    if trend:
        topic = _trend_scope_label(clean(trend.get("trend_scope")), clean(trend.get("trend_balance", {}).get("object_key")))
    sources = {clean(x.get("source")).lower() for x in support if clean(x.get("source"))}
    records = {clean(x.get("identity")) for x in support if clean(x.get("identity"))}
    if structural_verified and score <= 0:
        # Structural Level-3 findings verify by their graph shape rather than an
        # 80-point Level-5 score, but the shelf still needs a sensible same-wow
        # tie-breaker.  Evidence breadth supplies that ordering without becoming a
        # new verification gate.
        score = min(99, 45 + 5 * min(6, len(records)) + 4 * min(6, len(sources)))
    touched = any(bool(x.get("new_this_scan")) for x in support)
    wow, wow_basis = _final_wow(c, nodes, vocab)
    if grammar == "opposing_movements":
        lock_reason = "Trend remains in stock until its own side-evidence floor and page-selection rules pass."
    elif grammar == "corroborated_claim":
        lock_reason = "Corroborated Level-2 finding is verified by its independent-source floor and awaits shelf selection."
    elif structural_verified:
        lock_reason = "Structural candidate is verified by its authoritative graph test and is waiting for page selection."
    else:
        lock_reason = "Level-5 selection requires an executed candidate-specific falsifier plus wow/oddity/selection gates."

    out = {
        "id": _candidate_id(c),
        "grammar_id": grammar,
        "level": level,
        "product": product,
        "inferential_distance": level,
        "topic_key": _candidate_key(c),
        "topic_label": _candidate_topic_label(grammar, topic),
        # Preserve the semantic claim fields separately from the candidate lifecycle
        # status.  Reader surfaces need these to describe Level-2 corroborated
        # findings without falling back to generic wording.
        "object": clean(c.get("object")),
        "mechanism": clean(c.get("mechanism")),
        "direction": clean(c.get("direction")),
        "claim_status": clean(c.get("status")),
        "product_basis": clean(c.get("product_basis")),
        "shock_driver": bool(c.get("shock_driver")),
        "shock_driver_basis": clean(c.get("shock_driver_basis")),
        "status": status,
        "score": score,
        "wow_preliminary": c.get("wow_preliminary"),
        "wow": wow,
        "wow_basis": wow_basis,
        "distance_class": clean(c.get("distance")),
        "distance_lift": _finite_json_number(c.get("distance_lift")),
        "distance_bonus": _finite_json_number(c.get("distance_bonus")),
        "primary_role_coverage": round(len(covered) / max(1, len(required)), 3),
        "required_roles": required,
        "covered_roles": covered,
        "missing_roles": missing,
        "missing_links": missing,
        "primary_records": len(records),
        "primary_sources": len(sources),
        "context_records": len({clean(x.get("identity")) for x in context if clean(x.get("identity"))}),
        "counter_records": len(against),
        "counter_penalty": int(c.get("counter_penalty", 0) or 0),
        "denial_tested": False,
        "falsifier_executed": False,
        "reader_eligible": False,
        "publication_gate_passes": False,
        "publication_lock_reason": lock_reason,
        "synthesis_across_records": len(records) >= 2,
        "support": support,
        "context": context,
        "against": against,
        "support_queries": _support_queries(c),
        "falsifier_queries": [] if grammar in {"opposing_movements", "corroborated_claim"} else _falsifier_queries(c),
        "touched_this_scan": touched,
        "detector_backend": "claim_native",
        "claim_native": True,
        "claim_candidate_key": _candidate_key(c),
        "endpoint_objects": copy.deepcopy(c.get("endpoint_objects", [])),
        "score_gate_passes": (bool(c.get("score_gate_passes")) or structural_verified) if grammar != "opposing_movements" else bool(trend and trend.get("trend_evidence_floor_passes")),
    }
    if grammar == "named_continuity":
        out.update({
            "current_record_count": int(c.get("current_record_count", 0) or 0),
            "current_source_count": int(c.get("current_source_count", 0) or 0),
            "historical_record_count": int(c.get("historical_record_count", 0) or 0),
            "historical_source_count": int(c.get("historical_source_count", 0) or 0),
        })
    if trend:
        out.update(trend)
        out["score"] = int(round(100 - min(85.0, float(trend["trend_balance"].get("band_width", 0) or 0))))
        out["primary_records"] = len({x.get("identity") for x in out["support"]})
        out["primary_sources"] = len({clean(x.get("source")).lower() for x in out["support"] if clean(x.get("source"))})
        out["primary_role_coverage"] = 1.0 if trend.get("trend_evidence_floor_passes") else 0.667
    reader_title, reader_summary = _reader_copy(grammar, product, c, out)
    out["reader_title"] = reader_title
    out["reader_summary"] = reader_summary
    out["reader_why"] = _reader_why(grammar, product, c)
    oddity, oddity_reason = _oddity_pass(out, vocab)
    out["oddity_passes"] = oddity
    out["oddity_reason"] = oddity_reason
    verified, verification_mode = _verification_gate(out)
    out["verification_mode"] = verification_mode
    out["verification_gate_passes"] = verified
    return out

def _fp(c: dict[str, Any]) -> str:
    payload = {
        "id": c.get("id"), "status": c.get("status"), "score": c.get("score"),
        "missing": c.get("missing_roles"),
        "support": [(x.get("identity"), x.get("claim_id"), x.get("role")) for x in c.get("support", [])],
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def _previous_publication_ids(previous_state: dict[str, Any]) -> set[str]:
    pubs = previous_state.get("publications") if isinstance(previous_state.get("publications"), dict) else {}
    return {clean(cid) for ids in pubs.values() if isinstance(ids, list) for cid in ids if clean(cid)}


def refresh_claim_high_order(
    raw: dict[str, Any],
    previous_state: dict[str, Any] | None = None,
    completed_iso: str | None = None,
    *,
    root: Path = ROOT,
) -> dict[str, Any] | None:
    previous_state = previous_state if isinstance(previous_state, dict) else {}
    detected = detect_claim_reasoning(raw, root, completed_iso)
    if not detected["authority_gate"].get("ready"):
        return None
    nodes = detected["nodes"]
    groups = detected["groups"]
    vocab = load_vocabulary(root / "claims_vocabulary.json")
    ev = _date_only(completed_iso or raw.get("run_completed_at") or raw.get("last_updated"))
    try:
        evaluated_on = dt.date.fromisoformat(ev) if len(ev) == 10 else dt.date.today()
    except ValueError:
        evaluated_on = dt.date.today()
    raw_candidates: list[dict[str, Any]] = []
    for group in (
        "level2_corroborated", "level2_named_continuity",
        "level3_sequence_gap", "level3_era_conjunction", "level4_opposing_movements",
        "level5_dependency_pathway", "level4_5_conflicting_criteria", "level5_latent_channel",
        "level5_anchor_demand", "level5_split_recurrence",
    ):
        for x in groups.get(group, []):
            if not isinstance(x, dict):
                continue
            # Level-2 diagnostics that do not satisfy the R-25 risk/opportunity
            # polarity guard remain claim evidence for other grammars but are not a
            # reader-product candidate of their own.
            if group == "level2_corroborated" and clean(x.get("product")) not in {"risk", "opportunity"}:
                continue
            raw_candidates.append(x)
    adapted: dict[str, dict[str, Any]] = {}
    for raw_candidate in raw_candidates:
        cand = adapt_candidate(raw_candidate, nodes, vocab=vocab, evaluated_on=evaluated_on)
        old = adapted.get(cand["id"])
        rank = (int(cand.get("score", 0) or 0), len(cand.get("covered_roles", [])), int(cand.get("primary_sources", 0) or 0))
        old_rank = (int(old.get("score", 0) or 0), len(old.get("covered_roles", [])), int(old.get("primary_sources", 0) or 0)) if old else (-1, -1, -1)
        if old is None or rank > old_rank:
            adapted[cand["id"]] = cand

    prev_candidates = [x for x in previous_state.get("candidates", []) if isinstance(x, dict)] if isinstance(previous_state.get("candidates"), list) else []
    prev_claim = {clean(x.get("id")): x for x in prev_candidates if clean(x.get("id")).startswith("claim:")}
    now = clean(completed_iso) or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    executed_queries = set(_feedback_queries_executed(raw))
    merged: dict[str, dict[str, Any]] = {}
    node_claim_ids = {clean(n.get("claim_id")) for n in nodes if clean(n.get("claim_id"))}
    new_count = updated_count = 0
    bootstrap = not bool(prev_claim)

    for cid, old in prev_claim.items():
        cur = adapted.pop(cid, None)
        if cur is None:
            keep = copy.deepcopy(old)
            misses = int(keep.get("missed_detection_scans", 0) or 0) + 1
            support_ids = {clean(x.get("claim_id")) for x in keep.get("support", []) if isinstance(x, dict) and clean(x.get("claim_id"))}
            evidence_withdrawn = bool(support_ids - node_claim_ids)
            side_floor_exit = clean(keep.get("grammar_id")) == "opposing_movements"
            keep.update({"new_this_scan": False, "updated_this_scan": False, "missed_detection_scans": misses, "lifecycle": "claim_carried_forward"})
            semantic_shock_reclassification = (
                clean(keep.get("grammar_id")) == "dependency_pathway"
                and clean(keep.get("product")) == "shock"
                and "shock_driver" not in keep
            )
            if semantic_shock_reclassification:
                # Migration from the over-broad Stage-7 rule where every triggerless
                # dependency was called a shock.  If the candidate is not rediscovered
                # by the corrected shock grammar in this scan, preserve it in stock as
                # dormant history rather than counting it as an active developing shock.
                keep["status"] = "dormant"; keep["lifecycle"] = "shock_semantic_reclassification"; keep["exit_reason"] = "no current discontinuity driver under the corrected shock definition"
            elif evidence_withdrawn:
                keep["status"] = "watch"; keep["lifecycle"] = "support_evidence_withdrawn"; keep["exit_reason"] = "supporting claim dropped or reinterpreted"
            elif side_floor_exit:
                keep["status"] = "watch"; keep["lifecycle"] = "trend_side_floor_exit"; keep["exit_reason"] = "one trend side fell below the evidence floor"
            elif misses >= 6:
                keep["status"] = "dormant"
            elif misses >= 3 and keep.get("status") == "qualified":
                keep["status"] = "watch"
            keep["reader_eligible"] = False
            keep["publication_gate_passes"] = False
            merged[cid] = keep
            continue
        fp = _fp(cur)
        changed = fp != clean(old.get("fingerprint"))
        cur.update({
            "first_seen_at": clean(old.get("first_seen_at")) or now,
            "last_updated_at": now if changed else (clean(old.get("last_updated_at")) or now),
            "fingerprint": fp,
            "new_this_scan": False,
            "updated_this_scan": bool(changed and cur.get("touched_this_scan")),
            "missed_detection_scans": 0,
            "lifecycle": "updated" if changed else "unchanged",
        })
        _apply_falsifier_ledger(cur, old, executed_queries, now)
        if cur["updated_this_scan"]:
            updated_count += 1
        merged[cid] = cur

    for cid, cur in adapted.items():
        cur = copy.deepcopy(cur)
        cur.update({
            "first_seen_at": now, "last_updated_at": now, "fingerprint": _fp(cur),
            "new_this_scan": bool(cur.get("touched_this_scan")) and not bootstrap,
            "updated_this_scan": False, "missed_detection_scans": 0,
            "lifecycle": "claim_backend_bootstrap" if bootstrap else "new_claim_candidate",
        })
        _apply_falsifier_ledger(cur, None, executed_queries, now)
        if cur["new_this_scan"]:
            new_count += 1
        merged[cid] = cur

    order = {"qualified": 4, "watch": 3, "dormant": 2, "killed": 1}
    candidates = sorted(merged.values(), key=lambda c: (order.get(_low(c.get("status")), 0), int(c.get("wow", 0) or 0), int(c.get("score", 0) or 0), clean(c.get("last_updated_at"))), reverse=True)
    publications, selection = _select_stage7(candidates, previous_state)
    level_counts = Counter(int(c.get("level", 0) or 0) for c in candidates if c.get("claim_native"))
    return {
        "profile_version": PROFILE,
        "detector_backend": "claim_native",
        "detector_switch_stage": 6,
        "selection_stage": 7,
        "evaluated_at": now,
        "new_count": new_count,
        "updated_count": updated_count,
        "qualified_count": sum(1 for c in candidates if c.get("claim_native") and c.get("status") == "qualified"),
        "watch_count": sum(1 for c in candidates if c.get("claim_native") and c.get("status") == "watch"),
        "dormant_count": sum(1 for c in candidates if c.get("claim_native") and c.get("status") == "dormant"),
        "killed_count": sum(1 for c in candidates if c.get("claim_native") and c.get("status") == "killed"),
        "claim_candidate_count": sum(1 for c in candidates if c.get("claim_native")),
        "legacy_publication_carry_count": 0,
        "level_counts": {str(k): v for k, v in sorted(level_counts.items())},
        "claim_diagnostics": detected["claim_diagnostics"],
        "claim_expressiveness": detected["claim_expressiveness"],
        "authority_gate": detected["authority_gate"],
        "distance_table": detected["distance_table"],
        "publication_compatibility_lock": False,
        "falsifier_execution": {"executed_finding_context_queries": sorted(executed_queries), "executed_count": len(executed_queries)},
        "selection": selection,
        "publication_policy": "Stage 7 claim-native selection separates candidate formation, grammar-specific verification, and page selection. Candidate stock is uncapped. Level-2 corroborated findings use the independent-source floor; trends use their own two-sided evidence floor; structural graph findings use their bounded graph test; Level-5 cross-evidence hypotheses require an executed candidate-specific falsifier. Soft target ranges tune the active shelf threshold; verified surplus remains reserve and incomplete hypotheses remain watch.",
        "lifecycle_policy": "Claim-native stock persists as page/reserve/watch tiers; evidence is recomputed each scan, missed detections decay slowly, and evidence withdrawal or a falsifier hit exits the visible shelf immediately.",
        "candidate_search_policy": "Missing-role and falsifier queries remain ordinary scanner discovery inputs and receive no admission waiver.",
        "publications": publications,
        "candidates": candidates,
    }

def refresh_claim_shocks(
    raw: dict[str, Any],
    previous_state: dict[str, Any] | None = None,
    completed_iso: str | None = None,
    *,
    root: Path = ROOT,
) -> dict[str, Any] | None:
    previous_state = previous_state if isinstance(previous_state, dict) else {}
    detected = detect_claim_reasoning(raw, root, completed_iso)
    if not detected["authority_gate"].get("ready"):
        return None
    vocab = load_vocabulary(root / "claims_vocabulary.json")
    ev = _date_only(completed_iso or raw.get("run_completed_at") or raw.get("last_updated"))
    try:
        evaluated_on = dt.date.fromisoformat(ev) if len(ev) == 10 else dt.date.today()
    except ValueError:
        evaluated_on = dt.date.today()
    deps = [x for x in detected["groups"].get("level5_dependency_pathway", []) if isinstance(x, dict) and clean(x.get("product")) == "shock"]
    prev_claim = {clean(x.get("id")): x for x in previous_state.get("claim_candidates", []) if isinstance(x, dict) and clean(x.get("id"))} if isinstance(previous_state.get("claim_candidates"), list) else {}
    executed = set(_feedback_queries_executed(raw))
    now = clean(completed_iso) or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    claim_candidates=[]
    for item in deps:
        cand=adapt_candidate(item, detected["nodes"], vocab=vocab, evaluated_on=evaluated_on)
        _apply_falsifier_ledger(cand, prev_claim.get(clean(cand.get("id"))), executed, now)
        cand["publication_gate_passes"] = bool(cand.get("status") == "qualified" and cand.get("denial_tested") and int(cand.get("wow",0) or 0) >= 4 and cand.get("oddity_passes"))
        cand["reader_eligible"] = cand["publication_gate_passes"]
        claim_candidates.append(cand)
    claim_candidates.sort(key=lambda x: (bool(x.get("publication_gate_passes")), int(x.get("wow", 0) or 0), int(x.get("score", 0) or 0)), reverse=True)
    return {
        "profile_version": PROFILE + "-shock-adapter",
        "detector_backend": "claim_native",
        "detector_switch_stage": 6,
        "selection_stage": 7,
        "evaluated_at": now,
        "new_count": sum(1 for x in claim_candidates if clean(x.get("id")) not in prev_claim),
        "updated_count": 0,
        "unchanged_count": sum(1 for x in claim_candidates if clean(x.get("id")) in prev_claim),
        "claim_candidate_count": len(claim_candidates),
        "claim_candidates": claim_candidates,
        "claim_diagnostics": detected["claim_diagnostics"],
        "authority_gate": detected["authority_gate"],
        "publication_compatibility_lock": False,
        "dynamic_shocks": [],
        "compatibility_note": "Stage 7 retires legacy dynamic-shock publication carry. Reader-selected claim-native shocks are taken from high_order_inference.publications.shock; this registry remains as the shock-specific evidence/falsifier ledger.",
    }

def claim_feedback_queries(state: dict[str, Any] | None, limit: int = 8) -> list[str]:
    """Return bounded discovery feedback without ever changing scanner admission.

    The old Stage-7 ordering put ``watch`` candidates ahead of already-qualified
    candidates.  Because Level-5 publication then required an executed falsifier, the
    candidates closest to publication were starved of the very search that could test
    them.  This queue now gives first service to qualified Level-5 candidates waiting
    only for counter-evidence, round-robins product families, then spends remaining
    slots on missing-link support and ordinary watch-candidate challenges.
    """
    if not isinstance(state, dict):
        return []
    cap = max(0, int(limit or 0))
    if cap <= 0:
        return []
    candidates = [x for x in state.get("candidates", []) if isinstance(x, dict) and x.get("claim_native")]
    if not candidates:
        candidates = [x for x in state.get("claim_candidates", []) if isinstance(x, dict) and x.get("claim_native")]
    if not candidates:
        return []

    product_order = ("risk", "opportunity", "shock", "continuity", "trend")
    urgent = [
        c for c in candidates
        if clean(c.get("status")) == "qualified"
        and clean(c.get("verification_mode") or "executed_candidate_falsifier") == "executed_candidate_falsifier"
        and not c.get("denial_tested")
        and clean(c.get("movement")) != "killed"
        and any(clean(q) for q in (c.get("falsifier_queries") or []))
    ]
    urgent.sort(key=lambda c: (int(c.get("wow", 0) or 0), int(c.get("score", 0) or 0), int(c.get("primary_sources", 0) or 0)), reverse=True)

    by_product: dict[str, list[dict[str, Any]]] = {p: [] for p in product_order}
    for c in urgent:
        by_product.setdefault(clean(c.get("product")) or "continuity", []).append(c)
    ordered_urgent: list[dict[str, Any]] = []
    depth = 0
    while True:
        added = False
        for product in product_order:
            bucket = by_product.get(product, [])
            if depth < len(bucket):
                ordered_urgent.append(bucket[depth])
                added = True
        if not added:
            break
        depth += 1

    out: list[str] = []
    # First give every near-publication Level-5 candidate exactly one falsifier.  One
    # executed no-hit is enough to satisfy the Stage-7 denial gate, so second/third
    # variants are lower priority than helping a near-complete watch candidate mature.
    for c in ordered_urgent:
        qs = [clean(q) for q in c.get("falsifier_queries", []) if clean(q)]
        if qs and qs[0] not in out:
            out.append(qs[0])
            if len(out) >= cap:
                return out[:cap]

    # Missing-link candidates are the next best use of discovery.  Interleave support
    # and challenge queries so a candidate is neither blindly confirmed nor blindly
    # rejected.  Structural/trend candidates may still contribute a challenge query,
    # but such a query is refinement only and is never their publication admission.
    watch = [c for c in candidates if clean(c.get("status")) == "watch" and clean(c.get("movement")) != "killed"]
    watch.sort(
        key=lambda c: (
            1 if len(c.get("missing_roles", []) if isinstance(c.get("missing_roles"), list) else []) == 1 else 0,
            float(c.get("primary_role_coverage", 0) or 0),
            int(c.get("wow", 0) or 0),
            int(c.get("primary_sources", 0) or 0),
            int(c.get("score", 0) or 0),
        ),
        reverse=True,
    )
    # Round-robin the watch shelf too.  A missing opportunity role often has no score
    # yet by construction, so a global score sort would permanently starve it behind
    # already-scorable risks/shocks.  Product fairness lets the stock actually mature.
    watch_product_order = ("opportunity", "risk", "shock", "continuity", "trend")
    watch_by_product: dict[str, list[dict[str, Any]]] = {p: [] for p in watch_product_order}
    for c in watch:
        watch_by_product.setdefault(clean(c.get("product")) or "continuity", []).append(c)
    ordered_watch: list[dict[str, Any]] = []
    depth = 0
    while len(ordered_watch) < 16:
        added = False
        for product in watch_product_order:
            bucket = watch_by_product.get(product, [])
            if depth < len(bucket):
                ordered_watch.append(bucket[depth])
                added = True
                if len(ordered_watch) >= 16:
                    break
        if not added:
            break
        depth += 1

    max_support = max((len(c.get("support_queries") or []) for c in ordered_watch), default=0)
    max_challenge = max((len(c.get("falsifier_queries") or []) for c in ordered_watch), default=0)

    # First support query per watch candidate, product-fair.  With the normal scanner
    # budget this puts a live-connection/receiving-instrument search on the wire in the
    # same scan instead of burying it behind three variants of one falsifier.
    for c in ordered_watch:
        qs = [clean(q) for q in c.get("support_queries", []) if clean(q)]
        if qs and qs[0] not in out:
            out.append(qs[0])
            if len(out) >= cap:
                return out[:cap]

    # Only after broad candidate coverage spend remaining capacity on additional
    # near-publication falsifiers, then deeper watch support/challenge variants.
    max_urgent_falsifiers = max((len(c.get("falsifier_queries") or []) for c in ordered_urgent), default=0)
    for qi in range(1, max_urgent_falsifiers):
        for c in ordered_urgent:
            qs = [clean(q) for q in c.get("falsifier_queries", []) if clean(q)]
            if qi < len(qs) and qs[qi] not in out:
                out.append(qs[qi])
                if len(out) >= cap:
                    return out[:cap]

    for qi in range(max(max_support, max_challenge)):
        if qi > 0:
            for c in ordered_watch:
                qs = [clean(q) for q in c.get("support_queries", []) if clean(q)]
                if qi < len(qs) and qs[qi] not in out:
                    out.append(qs[qi])
                    if len(out) >= cap:
                        return out[:cap]
        for c in ordered_watch:
            qs = [clean(q) for q in c.get("falsifier_queries", []) if clean(q)]
            if qi < len(qs) and qs[qi] not in out:
                out.append(qs[qi])
                if len(out) >= cap:
                    return out[:cap]
    return out[:cap]

