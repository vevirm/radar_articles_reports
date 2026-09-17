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
        opposing_movements,
        split_recurrence_candidates,
    )

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "radar-claim-reasoning-live-v1-stage6"
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
            "level2_corroborated": [], "level3_sequence_gap": [], "level3_era_conjunction": [],
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
                "level2_corroborated": [], "level3_sequence_gap": [], "level3_era_conjunction": [],
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
                "level2_corroborated": [], "level3_sequence_gap": [], "level3_era_conjunction": [],
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
        "level3_sequence_gap": level3_findings(nodes, ev_date),
        "level3_era_conjunction": era_conjunctions(nodes),
        "level4_opposing_movements": opposing_movements(nodes, ev_date),
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
    endpoints = [clean(x) for x in c.get("endpoint_objects", []) if clean(x)] if isinstance(c.get("endpoint_objects"), list) else []
    if not endpoints:
        for key in ("capability_object", "dependency_object", "object", "objective_object", "delivery_object"):
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
    if grammar in {"conflicting_criteria", "clock_before_rule", "deployment_before_rules", "success_metric_gap", "stalled_proposal"}:
        return "risk"
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
            "strand": clean(node.get("_collection")).replace("strand_", "").upper(),
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
            "object": clean(snap.get("object")),
        })
    # Level-2/3 candidates often store claim ids directly instead of role snapshots.
    ids: list[str] = []
    for key in ("claim_ids", "rule_claim_ids"):
        if isinstance(c.get(key), list):
            ids.extend(clean(x) for x in c[key] if clean(x))
    for key in ("commitment_claim_id", "practice_claim_id", "doctrine_claim_id", "delivery_claim_id", "success_claim_id"):
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
            "strand": clean(node.get("_collection")).replace("strand_", "").upper(),
            "title": clean(node.get("_title")), "source": clean(node.get("_source")),
            "date": clean(node.get("status_date")), "link": rk[5:] if rk.startswith("link:") else clean(node.get("_link")),
            "quality": int(round(float(node.get("merit", 0) or 0))), "new_this_scan": bool(node.get("_new_this_scan")),
            "analytical_weight": round(float(node.get("_context_weight", 1.0) or 0), 3),
            "claim_primary": bool(node.get("_primary")),
            "claim_context_weight": round(float(node.get("_context_weight", 1.0) or 0), 3),
            "claim_origin": clean(node.get("origin")),
            "claim_kind": clean(node.get("kind")),
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


def adapt_candidate(c: dict[str, Any], nodes: Iterable[dict[str, Any]]) -> dict[str, Any]:
    node_by_claim = {clean(n.get("claim_id")): n for n in nodes if clean(n.get("claim_id"))}
    support = _support_rows(c, node_by_claim)
    missing = [clean(x) for x in c.get("missing_roles", []) if clean(x)] if isinstance(c.get("missing_roles"), list) else []
    roles = c.get("roles") if isinstance(c.get("roles"), dict) else {}
    required = list(roles) if roles else (["support"] if support else [])
    covered = [r for r, snap in roles.items() if isinstance(snap, dict)] if roles else (["support"] if support else [])
    score = c.get("score")
    if score is None:
        score = 0
    score = max(0, min(99, int(round(float(score or 0)))))
    status = "qualified" if bool(c.get("score_gate_passes")) and not missing else "watch"
    product = _product_for(c)
    topic = " × ".join(clean(x) for x in c.get("endpoint_objects", []) if clean(x)) if isinstance(c.get("endpoint_objects"), list) else ""
    topic = topic or clean(c.get("object") or c.get("capability_object") or c.get("grammar_id"))
    sources = {clean(x.get("source")).lower() for x in support if clean(x.get("source"))}
    records = {clean(x.get("identity")) for x in support if clean(x.get("identity"))}
    touched = any(bool(x.get("new_this_scan")) for x in support)
    return {
        "id": _candidate_id(c),
        "grammar_id": clean(c.get("grammar_id")),
        "level": int(c.get("level", 5) or 5),
        "product": product,
        "inferential_distance": int(c.get("level", 5) or 5),
        "topic_key": _candidate_key(c),
        "topic_label": topic,
        "status": status,
        "score": score,
        "wow_preliminary": c.get("wow_preliminary"),
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
        "context_records": 0,
        "counter_records": len(c.get("counter_claim_ids", []) if isinstance(c.get("counter_claim_ids"), list) else []),
        "counter_penalty": int(c.get("counter_penalty", 0) or 0),
        "denial_tested": False,
        "falsifier_executed": False,
        "reader_eligible": False,
        "publication_gate_passes": False,
        "publication_lock_reason": "Stage 6 detector switch: claim-native candidate awaits candidate-specific falsifier execution plus Stage-7 wow/oddity/selection gates.",
        "synthesis_across_records": len(records) >= 2,
        "support": support,
        "context": [],
        "against": [],
        "support_queries": _support_queries(c),
        "falsifier_queries": _falsifier_queries(c),
        "touched_this_scan": touched,
        "detector_backend": "claim_native",
        "claim_native": True,
        "claim_candidate_key": _candidate_key(c),
        "endpoint_objects": copy.deepcopy(c.get("endpoint_objects", [])),
        "score_gate_passes": bool(c.get("score_gate_passes")),
    }


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
    raw_candidates: list[dict[str, Any]] = []
    for group in (
        "level3_sequence_gap", "level3_era_conjunction", "level4_opposing_movements",
        "level5_dependency_pathway", "level4_5_conflicting_criteria", "level5_latent_channel",
        "level5_anchor_demand", "level5_split_recurrence",
    ):
        raw_candidates.extend(x for x in groups.get(group, []) if isinstance(x, dict))
    adapted: dict[str, dict[str, Any]] = {}
    for raw_candidate in raw_candidates:
        cand = adapt_candidate(raw_candidate, nodes)
        old = adapted.get(cand["id"])
        # Multiple role fits can express the same semantic endpoint pair.  Keep one
        # stable candidate id and retain the strongest/most-complete fit rather than
        # treating role-choice variants as separate findings.
        rank = (int(cand.get("score", 0) or 0), len(cand.get("covered_roles", [])), int(cand.get("primary_sources", 0) or 0))
        old_rank = (int(old.get("score", 0) or 0), len(old.get("covered_roles", [])), int(old.get("primary_sources", 0) or 0)) if old else (-1, -1, -1)
        if old is None or rank > old_rank:
            adapted[cand["id"]] = cand

    prev_candidates = [x for x in previous_state.get("candidates", []) if isinstance(x, dict)] if isinstance(previous_state.get("candidates"), list) else []
    prev_claim = {clean(x.get("id")): x for x in prev_candidates if clean(x.get("id")).startswith("claim:")}
    publication_ids = _previous_publication_ids(previous_state)
    carry_legacy = {clean(x.get("id")): copy.deepcopy(x) for x in prev_candidates if clean(x.get("id")) in publication_ids and not clean(x.get("id")).startswith("claim:")}
    now = clean(completed_iso) or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    merged: dict[str, dict[str, Any]] = {}
    new_count = updated_count = 0
    bootstrap = not bool(prev_claim)

    for cid, old in prev_claim.items():
        cur = adapted.pop(cid, None)
        if cur is None:
            keep = copy.deepcopy(old)
            misses = int(keep.get("missed_detection_scans", 0) or 0) + 1
            keep.update({"new_this_scan": False, "updated_this_scan": False, "missed_detection_scans": misses, "lifecycle": "claim_carried_forward"})
            if misses >= 6:
                keep["status"] = "dormant"
            elif misses >= 3 and keep.get("status") == "qualified":
                keep["status"] = "watch"
            keep["reader_eligible"] = False
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
        if cur["new_this_scan"]:
            new_count += 1
        merged[cid] = cur

    # Compatibility shell: carry only items already on a reader page.  They are not
    # redetected by regex and cannot create new publications; Stage 7 retires this shell.
    for cid, old in carry_legacy.items():
        old["detector_backend"] = "legacy_publication_carry"
        old["legacy_publication_carry"] = True
        old["new_this_scan"] = False
        old["updated_this_scan"] = False
        old["lifecycle"] = "stage6_publication_compatibility"
        merged[cid] = old

    order = {"qualified": 3, "watch": 2, "dormant": 1}
    candidates = sorted(merged.values(), key=lambda c: (order.get(_low(c.get("status")), 0), int(c.get("score", 0) or 0), clean(c.get("last_updated_at"))), reverse=True)
    prev_pubs = previous_state.get("publications") if isinstance(previous_state.get("publications"), dict) else {}
    publications = {k: [clean(x) for x in (prev_pubs.get(k) or []) if clean(x) in merged] for k in ("shock", "risk", "opportunity", "continuity", "trend")}
    level_counts = Counter(int(c.get("level", 0) or 0) for c in candidates if c.get("claim_native"))
    return {
        "profile_version": PROFILE,
        "detector_backend": "claim_native",
        "detector_switch_stage": 6,
        "evaluated_at": now,
        "new_count": new_count,
        "updated_count": updated_count,
        "qualified_count": sum(1 for c in candidates if c.get("claim_native") and c.get("status") == "qualified"),
        "watch_count": sum(1 for c in candidates if c.get("claim_native") and c.get("status") == "watch"),
        "dormant_count": sum(1 for c in candidates if c.get("claim_native") and c.get("status") == "dormant"),
        "claim_candidate_count": sum(1 for c in candidates if c.get("claim_native")),
        "legacy_publication_carry_count": sum(1 for c in candidates if c.get("legacy_publication_carry")),
        "level_counts": {str(k): v for k, v in sorted(level_counts.items())},
        "claim_diagnostics": detected["claim_diagnostics"],
        "claim_expressiveness": detected["claim_expressiveness"],
        "authority_gate": detected["authority_gate"],
        "distance_table": detected["distance_table"],
        "publication_compatibility_lock": True,
        "publication_policy": "Stage 6 switches detector generation to claims but freezes reader publication IDs. Claim-native candidates remain reader-ineligible until falsifier execution and Stage-7 wow/oddity/selection are active.",
        "lifecycle_policy": "Claim-native candidates persist and decay under the existing slow lifecycle. Only already-published legacy candidates are carried for reader compatibility; regex detection no longer adds candidates.",
        "candidate_search_policy": "Missing-role and falsifier queries come from claim-native candidates and still pass through normal scanner admission.",
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
    deps = [x for x in detected["groups"].get("level5_dependency_pathway", []) if isinstance(x, dict) and clean(x.get("product")) == "shock"]
    claim_candidates = [adapt_candidate(x, detected["nodes"]) for x in deps]
    claim_candidates.sort(key=lambda x: (int(x.get("score", 0) or 0), int(x.get("wow_preliminary", 0) or 0)), reverse=True)
    previous_dynamic = copy.deepcopy(previous_state.get("dynamic_shocks")) if isinstance(previous_state.get("dynamic_shocks"), list) else []
    return {
        "profile_version": PROFILE + "-shock-adapter",
        "detector_backend": "claim_native",
        "detector_switch_stage": 6,
        "evaluated_at": clean(completed_iso) or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "new_count": 0,
        "updated_count": 0,
        "unchanged_count": len(previous_dynamic),
        "claim_candidate_count": len(claim_candidates),
        "claim_candidates": claim_candidates,
        "claim_diagnostics": detected["claim_diagnostics"],
        "authority_gate": detected["authority_gate"],
        "publication_compatibility_lock": True,
        "dynamic_shocks": previous_dynamic,
        "compatibility_note": "Stage 6 shock detector is claim-native; reader-visible dynamic_shocks are frozen legacy carry until Stage 7 activates falsifier/wow/selection gates.",
    }


def claim_feedback_queries(state: dict[str, Any] | None, limit: int = 8) -> list[str]:
    if not isinstance(state, dict):
        return []
    candidates = [x for x in state.get("candidates", []) if isinstance(x, dict) and x.get("claim_native")]
    if not candidates:
        candidates = [x for x in state.get("claim_candidates", []) if isinstance(x, dict) and x.get("claim_native")]
    candidates.sort(key=lambda c: (1 if c.get("status") == "watch" else 0, int(c.get("score", 0) or 0)), reverse=True)
    support: list[str] = []
    falsify: list[str] = []
    for c in candidates[:12]:
        support.extend(clean(q) for q in c.get("support_queries", []) if clean(q))
        falsify.extend(clean(q) for q in c.get("falsifier_queries", []) if clean(q))
    out: list[str] = []
    for i in range(max(len(support), len(falsify))):
        if i < len(support) and support[i] not in out:
            out.append(support[i])
        if i < len(falsify) and falsify[i] not in out:
            out.append(falsify[i])
        if len(out) >= max(0, int(limit or 0)):
            break
    return out[:max(0, int(limit or 0))]
