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
from collections import Counter, defaultdict
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
        exploratory_shock_hypotheses,
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
        exploratory_shock_hypotheses,
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
            "level4_opposing_movements": [], "level5_dependency_pathway": [], "future_shock_hypothesis": [], "level4_5_conflicting_criteria": [],
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


_DIRECTION_GROUNDING_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "becomes_contested": (
        re.compile(r"\bcontest(?:ed|ation)?\b", re.I), re.compile(r"\boppos(?:e|ed|es|ition)\b", re.I),
        re.compile(r"\bdisput(?:e|ed|es)\b", re.I), re.compile(r"\bdiverg(?:e|es|ed|ence|ent)\b", re.I),
        re.compile(r"\bconflict(?:s|ing|ed)?\b", re.I), re.compile(r"\bcontrovers(?:y|ial)\b", re.I),
        re.compile(r"\bresist(?:ance|ed|s|ing)?\b", re.I),
    ),
    "becomes_conditional": (
        re.compile(r"\bcondition(?:al|ality|ed|s)?\b", re.I), re.compile(r"\bsubject to\b", re.I),
        re.compile(r"\bcontingent (?:on|upon)\b", re.I), re.compile(r"\brequir(?:e|es|ed|ement|ements)\b", re.I),
        re.compile(r"\bapproval\b|\bpermission\b|\blicen[cs](?:e|ing)\b", re.I), re.compile(r"\bscreen(?:ing|ed)?\b", re.I),
        re.compile(r"\beligib(?:le|ility)\b|\bthreshold(?:s)?\b", re.I),
        re.compile(r"\bmandatory\b|\bsafeguard(?:s|ed|ing)?\b|\bonly if\b", re.I),
    ),
    "contracts": (
        re.compile(r"\brestrict(?:s|ed|ion|ions|ive)?\b", re.I), re.compile(r"\blimit(?:s|ed|ation|ations)?\b", re.I),
        re.compile(r"\bconstrain(?:s|ed|t|ts)?\b", re.I), re.compile(r"\bdeclin(?:e|es|ed|ing)\b|\bdecreas(?:e|es|ed|ing)\b", re.I),
        re.compile(r"\bshortage(?:s)?\b|\bscarcity\b|\bbottleneck(?:s)?\b", re.I),
        re.compile(r"\bblock(?:s|ed|ing)?\b|\bcut(?:s|ting)?\b|\bexclude(?:s|d)?\b", re.I),
        re.compile(r"\berod(?:e|es|ed|ing)\b|\bweaken(?:s|ed|ing)?\b|\bloss\b", re.I),
        re.compile(r"\bbarrier(?:s)?\b|\bunderinvest(?:s|ed|ment|ing)?\b", re.I),
        re.compile(r"\bunderperform(?:s|ed|ing|ance)?\b|\bweaker\b|\bdisintegration\b", re.I),
        re.compile(r"\bpersistent dependenc(?:e|y|ies)\b|\bpreparedness gaps?\b|\bmaterial gaps?\b", re.I),
        re.compile(r"\bdid not (?:shift|move|increase|grow|improve)\b|\bstagnat(?:e|es|ed|ion|ing)\b", re.I),
        re.compile(r"\bcapped? adoption\b|\bunderperform(?:s|ed|ing|ance)?\b|\bcapacity gap(?:s)?\b", re.I),
        re.compile(r"\bweak(?:er|ness)?\b|\bdifficulty\b|\bbarriers?\b", re.I),
    ),
    "expands": (
        re.compile(r"\bexpand(?:s|ed|ing|sion)?\b|\bwiden(?:s|ed|ing)?\b", re.I),
        re.compile(r"\bincreas(?:e|es|ed|ing)\b|\bgrow(?:s|th|ing)?\b", re.I),
        re.compile(r"\badd(?:s|ed|ing)?\b.{0,35}\bcapacity\b|\bnew capacity\b", re.I),
        re.compile(r"\bbuild(?:s|ing|out)?\b|\blaunch(?:es|ed|ing)?\b", re.I),
        re.compile(r"\bfund(?:s|ed|ing)?\b|\binvest(?:s|ed|ment|ing)?\b", re.I),
        re.compile(r"\brecruit(?:s|ed|ing)?\b|\bretain(?:s|ed|ing)?\b", re.I),
        re.compile(r"\bopen(?:s|ed|ing)? access\b|\bassociation agreement\b", re.I),
        re.compile(r"\bestablish(?:es|ed|ing)?\b|\bcreat(?:e|es|ed|ing)\b|\bcommit(?:s|ted|ment)?\b", re.I),
        re.compile(r"\bagree(?:s|d|ment)\b|\bcall for\b|\bprogramme\b.{0,40}\b(?:launch|fund|support)\b", re.I),
    ),
}


def _direction_is_reader_grounded(node: dict[str, Any], direction: str | None = None) -> bool:
    """Does the reader-visible source statement actually support this direction?

    This is a downstream publication-semantics check. It does not rewrite the
    authoritative claim. It only prevents an unsupported structured direction from
    being presented as if the publication supplied that directional evidence.
    """
    direction = clean(direction or node.get("direction"))
    if not direction or direction == "unchanged":
        return True
    # Use the authoritative claim statement itself.  Structured mechanism/direction
    # fields and publication titles are useful indexing metadata, but they must not
    # rescue a reader-facing direction that the displayed source statement does not
    # actually express.
    text = clean(node.get("text"))
    if not text:
        # Synthetic/legacy test fixtures can lack reader-visible claim text.  Preserve
        # their historical behaviour without letting structured metadata override a
        # real source statement when one exists.
        mechanism = clean(node.get("mechanism"))
        if direction == "becomes_conditional":
            return mechanism in {"conditions", "requires", "screens", "licenses"}
        if direction == "contracts":
            return mechanism in {"restricts", "excludes"}
        if direction == "expands":
            return mechanism in {"builds", "funds", "recruits", "retains", "associates", "adds_capacity", "diversifies", "supplies", "procures", "invests", "launches", "supports"}
        return False
    # Reader-facing directional evidence has two obligations: the statement must
    # express the direction *and* it must visibly concern the object to which the
    # Radar attaches that direction.  This prevents, for example, an early-warning
    # system from being presented as direct evidence that research-system governance
    # is expanding merely because a structured claim carried that broader tag.
    if not _statement_grounds_object(node.get("object"), text):
        return False
    matches = [m for p in _DIRECTION_GROUNDING_PATTERNS.get(direction, ()) for m in p.finditer(text)]
    if not matches:
        return False

    # Conditional/contested directions are especially easy to misattach: a source
    # may say one thing is conditional or contested while the structured claim
    # points at a different object in the same sentence.  Require the object anchor
    # to sit near the directional phrase before presenting that direction publicly.
    if direction in {"becomes_conditional", "becomes_contested"}:
        low = text.lower()
        terms = _object_anchor_terms(clean(node.get("object")))
        spans: list[tuple[int, int]] = []
        for term in terms:
            start = 0
            while term and (idx := low.find(term, start)) >= 0:
                spans.append((idx, idx + len(term)))
                start = idx + max(1, len(term))
        if spans and not any(min(abs(m.start() - b), abs(a - m.end())) <= 60 for m in matches for a, b in spans):
            return False
    return True



# A future-shock hypothesis may be seeded broadly, but the public page must not
# turn a neutral mention of a policy/domain into evidence that a disruptive shock
# mechanism is already documented.  These checks operate only at publication
# semantics: the hypothesis remains in stock when the displayed source statement
# does not yet evidence the named disruption family.
_SHOCK_DRIVER_GROUNDING_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "export_control": (
        re.compile(r"\bexport (?:controls?|restrictions?|ban|licen[cs](?:e|ing))\b", re.I),
        re.compile(r"\bdual[- ]use (?:controls?|licen[cs](?:e|ing)|restrictions?)\b", re.I),
        re.compile(r"\btechnology restriction(?:s)?\b", re.I),
    ),
    "critical_input": (
        re.compile(r"\b(?:critical raw materials?|critical minerals?|rare earths?)\b.{0,90}\b(?:shortage|scarcity|bottleneck|dependen|constraint|risk|insufficient|reserve|supply)\b", re.I),
        re.compile(r"\b(?:shortage|scarcity|bottleneck|import dependence|supply[- ]chain risk|material constraint)\b", re.I),
        re.compile(r"\bdemand\b.{0,80}\b(?:exceed|above|outstrip)\b.{0,80}\b(?:reserve|supply|capacity)\b", re.I),
    ),
    "security_reclassification": (
        re.compile(r"\breclassif(?:y|ies|ied|ication)\b", re.I),
        re.compile(r"\b(?:classified|designated|treated) as (?:sensitive|dual[- ]use|restricted)\b", re.I),
        re.compile(r"\bsecurity screen(?:ing|ed)?\b.{0,80}\b(?:restrict|exclude|block|limit|access|collaborat)\b", re.I),
        re.compile(r"\b(?:sensitive|dual[- ]use) research\b.{0,80}\b(?:restrict|exclude|block|limit|licen[cs]|screen)\b", re.I),
        re.compile(r"\b(?:access|participation|collaboration)\b.{0,60}\b(?:restricted|limited|excluded|blocked)\b.{0,80}\bsecurity\b", re.I),
        # How reclassification is actually reported: security rules that condition,
        # screen or safeguard research cooperation (de-risking, securitisation).
        re.compile(r"\b(?:de-?risk(?:ing)?|securiti[sz](?:ation|ed|ing))\b", re.I),
        re.compile(r"\bresearch security\b.{0,100}\b(?:condition|screen|safeguard|restrict|rule|guideline|vet|due diligence|risk)\w*", re.I),
        re.compile(r"\b(?:condition|screen|safeguard|vet)\w*\b.{0,80}\b(?:research|scientific|academic) (?:cooperation|collaboration|partnership|openness|exchange)\b", re.I),
        re.compile(r"\bsecurity(?:-| )(?:conditional|relevant research|sensitive research)\b", re.I),
        re.compile(r"\b(?:espionage|knowledge theft|technology leakage)\b", re.I),
    ),
    "acquisition": (
        re.compile(r"\bforeign (?:acquisition|ownership|takeover|buyer|investor)\b", re.I),
        re.compile(r"\b(?:acquisition|takeover)\b.{0,70}\b(?:screen|block|security|strategic)\b", re.I),
        re.compile(r"\binvestment screening\b.{0,80}\b(?:acquisition|ownership|takeover|transaction)\b", re.I),
    ),
    "conflict": (
        re.compile(r"\barmed conflict\b", re.I),
        re.compile(r"\bwar\b|\binvasion\b|\bhostilit(?:y|ies)\b", re.I),
        re.compile(r"\bmilitary escalation\b|\bescalat(?:ion|ing|ed)\b.{0,40}\bmilitary\b", re.I),
    ),
    "sanctions": (
        re.compile(r"\bsanctions?\b|\basset freeze\b", re.I),
        re.compile(r"\b(?:payment|financial) restrictions?\b", re.I),
    ),
    "data_access": (
        re.compile(r"\bdata (?:access|transfer) restrictions?\b", re.I),
        re.compile(r"\bcross[- ]border data\b.{0,60}\b(?:restrict|block|limit|ban)\b", re.I),
        re.compile(r"\bdata locali[sz]ation\b", re.I),
    ),
    "cyber": (
        re.compile(r"\bcyber ?attack\b|\bransomware\b|\bdigital outage\b|\bcyber outage\b", re.I),
        re.compile(r"\b(?:breach|compromise|intrusion|takeover|took over|hijack)\b.{0,80}\b(?:site|website|system|network|server|account|infrastructure)\b", re.I),
        re.compile(r"\b(?:site|website|system|network|server|account|infrastructure)\b.{0,80}\b(?:breach|compromise|intrusion|takeover|took over|hijack)\b", re.I),
        re.compile(r"\bsoftware vulnerab(?:ility|ilities)\b", re.I),
    ),
    "energy": (
        re.compile(r"\b(?:power|electricity|energy) (?:shortage|outage|constraint|rationing|crisis)\b", re.I),
        re.compile(r"\bgrid (?:constraint|congestion|bottleneck|shortage|capacity limit)\b", re.I),
        re.compile(r"\bpower and land constraints?\b", re.I),
        re.compile(r"\b(?:insufficient|limited) (?:power|electricity|grid capacity)\b", re.I),
    ),
    "commercial": (
        re.compile(r"\b(?:provider|vendor|service) (?:withdrawal|exit|repricing)\b", re.I),
        re.compile(r"\bmarket withdrawal\b|\bvendor lock[- ]?in\b", re.I),
        re.compile(r"\b(?:proprietary|commercial)\b.{0,70}\b(?:licen[cs]e restriction|access restriction|withdrawal|repricing)\b", re.I),
    ),
    "external_finance": (
        re.compile(r"\b(?:withdrawal|loss|cut[- ]?off|contraction) of (?:external|foreign) (?:finance|capital|funding)\b", re.I),
        re.compile(r"\bdependen(?:ce|cy|t)\b.{0,80}\b(?:foreign|external) (?:capital|finance|funding)\b", re.I),
        re.compile(r"\b(?:foreign|external) (?:capital|finance|funding)\b.{0,80}\bdependen(?:ce|cy|t)\b", re.I),
    ),
}


try:  # additional disruption families share one definition with the generator
    from scripts.claim_reasoning_shadow import _EXTRA_PRESSURE_REGEX as _EXTRA_PR
except ImportError:  # pragma: no cover
    from claim_reasoning_shadow import _EXTRA_PRESSURE_REGEX as _EXTRA_PR  # type: ignore
for _pid, _rx in _EXTRA_PR.items():
    _SHOCK_DRIVER_GROUNDING_PATTERNS.setdefault(_pid, (re.compile(_rx, re.I),))


def _shock_driver_is_reader_grounded(pressure_id: Any, source_statement: Any) -> bool:
    """Return whether the visible statement actually evidences the named shock class.

    Broad scenario operators may still form candidates from looser topical matches.
    Publication, however, needs at least one displayed external-driver statement that
    describes the disruption mechanism itself rather than merely mentioning the
    surrounding policy area.
    """
    pid = clean(pressure_id)
    text = clean(source_statement)
    if not pid or not text:
        return False
    return any(rx.search(text) for rx in _SHOCK_DRIVER_GROUNDING_PATTERNS.get(pid, ()))




def _object_anchor_terms(obj: str) -> tuple[str, ...]:
    obj = clean(obj)
    fam = _family_of(obj)
    if fam:
        terms: list[str] = [fam.replace("_", " ")]
        for member in sorted(_FAMILY_MEMBERS.get(obj, ())):
            terms.extend(_object_anchor_terms(member))
        return tuple(dict.fromkeys(t for t in terms if t))
    terminal = obj.split(".")[-1].replace("_", " ") if obj else ""
    full_aliases: dict[str, tuple[str, ...]] = {
        "compute.capacity": ("compute", "computing", "supercomputer", "gigafactor", "data centre", "data-center"),
        "finance.strategic_investment": ("investment", "capital", "subsid", "financ", "equity", "fund"),
        "digital.governance": ("digital governance", "data governance", "digital single market", "digital rules"),
        "research.collaboration": ("collaborat", "cooperation", "partnership"),
        "finance.venture_capital": ("venture capital", "public equity", "funding round", "equity"),
        "innovation.regional_capacity": ("regional", "cohesion", "structural fund", "innovation capacity"),
        "innovation.system_performance": ("innovation performance", "innovation system", "innovation capacity", "entrepreneurial", "r&d intensity"),
        "datacentre.energy_supply": ("data centre", "data-center", "power", "energy", "electricity", "grid"),
        "research.system_governance": ("research governance", "research system", "era", "governance"),
        "industrial.competitiveness": ("compet", "industrial"),
        "research_security.screening": ("research security", "security screening", "screening"),
        "research.openness": ("open science", "scientific openness", "research openness", "openness"),
        "industrial.technology_complexity": ("technolog", "complex"),
        "goal.strategic_autonomy": ("strategic autonomy", "sovereign", "non-dependence", "non dependence"),
        "defence.innovation_funding": ("defence innovation", "defense innovation", "fund"),
        "compute.public_procurement": ("procure", "procurement", "ai gigafactor"),
        "quantum.testing_infrastructure": ("quantum", "testing", "test infrastructure"),
        "quantum.standards": ("quantum", "standard"),
        "quantum.pilot_line": ("quantum", "pilot line"),
        "compute.access_time": ("compute", "access time"),
        "defence.drone_capability": ("drone", "counter-drone", "counter drone"),
        "talent.retention": ("retain", "retention", "researcher", "stay", "remain", "brain drain", "career", "talent", "mobility", "leave europe"),
        # Future-thinking expansion: phrasings the reviewed claims actually use.
        "innovation.system_performance": ("innovation performance", "innovation system", "innovation capacity", "entrepreneurial", "r&d intensity", "innovat", "commerciali", "scale-up", "scale up", "patent", "spin-off", "spinoff", "valorisation", "technology transfer", "productivity"),
        "research.system_governance": ("research governance", "research system", "era", "governance", "research polic", "science polic", "research and innovation polic", "r&i polic", "research assessment", "peer review", "research council", "committee"),
        "funding.route": ("fund", "grant", "call", "programme", "program", "financ", "investment"),
        "ai.governance": ("govern", "ai act", "regulat", "framework", "rules", "safety", "accountab", "oversight", "guideline"),
        "goal.strategic_autonomy": ("strategic autonomy", "sovereign", "non-dependence", "non dependence", "dependen", "self-relian", "resilien", "strategic", "de-risk", "derisk"),
        "horizon.budget_2028_34": ("fp10", "horizon", "framework programme", "mff", "competitiveness fund", "research budget", "2028"),
        "research_security.screening": ("research security", "security screening", "screening", "securit", "de-risk", "derisk", "safeguard", "dual-use", "dual use", "espionage", "sensitive research", "knowledge security"),
        "research.infrastructure": ("infrastructure", "facilit", "observator", "laborator", "esfri", "synchrotron", "testbed", "test bed", "platform"),
        "digital.governance": ("digital governance", "data governance", "digital single market", "digital rules", "gdpr", "data protection", "privacy", "platform", "copyright", "digital services", "data act", "scraping"),
        "industrial.competitiveness": ("compet", "industrial", "industry", "manufactur", "market share", "productiv"),
        "cybersecurity.sme_resilience": ("cyber", "security", "resilien", "attack", "incident", "manipulation"),
        "research.system_capacity": ("capacity", "research system", "research capacit", "scientific base", "workforce", "research performance"),
        "innovation.deep_tech_startups": ("deep tech", "deep-tech", "startup", "start-up", "scale-up", "scaleup", "venture"),
        "chips.fab": ("fab", "semiconductor", "chip", "foundr", "wafer", "manufactur"),
        "research.knowledge_transfer": ("knowledge transfer", "technology transfer", "know-how", "valorisation", "commerciali", "patent", "licens", "spin-off", "industry-academ", "university-industry"),
        "export_control.regulation": ("regulation", "export control", "export restriction", "dual-use", "dual use", "licens"),
        "ai.adoption": ("adoption", "uptake", "use of ai", "deploy", "digital infrastructure", "integration"),
        "green.circular_economy": ("circular economy", "circular", "recycl", "reuse", "waste", "life cycle", "lifecycle"),
        "green.innovation": ("innovation", "green", "clean", "emission", "climate", "sustainab", "pollution"),
        "research.collaboration": ("collaborat", "cooperation", "partnership", "consorti", "joint", "network", "co-author", "association", "openness"),
    }
    aliases: dict[str, tuple[str, ...]] = {
        "screening": ("screen",),
        "openness": ("open science", "scientific openness", "research openness", "openness"),
        "retention": ("retain", "retention"),
        "recruitment abroad": ("recruit", "recruitment"),
        "governance": ("govern",),
        "capacity": ("capacity",),
        "system performance": ("performance", "innovation"),
        "competitiveness": ("compet",),
        "technology complexity": ("technolog", "complex"),
        "strategic autonomy": ("strategic autonomy", "sovereign", "non-dependence", "non dependence"),
        "innovation funding": ("fund", "innovation"),
        "public procurement": ("procure", "procurement"),
        "testing infrastructure": ("testing", "test infrastructure"),
        "standards": ("standard",),
        "pilot line": ("pilot line",),
        "access time": ("access time",),
        "drone capability": ("drone", "counter-drone", "counter drone"),
        "collaboration": ("collaborat", "cooperation", "partnership"),
        "venture capital": ("venture capital", "equity"),
        "strategic investment": ("investment", "capital", "subsid"),
        "regional capacity": ("regional", "capacity"),
        "energy supply": ("energy", "power", "electricity", "grid"),
    }
    return full_aliases.get(obj, aliases.get(terminal, (terminal,) if terminal else ()))


def _anchor_normalize(value: Any) -> str:
    """Normalize reader-visible wording for conservative object-anchor matching."""
    return re.sub(r"[^a-z0-9&]+", " ", _low(value)).strip()


def _statement_grounds_object(object_key: Any, statement: Any) -> bool:
    """Whether the displayed source statement visibly concerns the controlled object.

    Structured object tags remain authoritative indexing metadata, but a public
    evidence row must not use them to make a source appear to speak about an object
    that is absent from the claim text itself.  Hyphens and punctuation are
    normalised so genuine phrases such as ``research-security`` still match.
    """
    obj = clean(object_key)
    text = _anchor_normalize(statement)
    if not obj or not text:
        return True
    return any(
        term and _anchor_normalize(term) in text
        for term in _object_anchor_terms(obj)
    )


_REVIEWED_ORIGINS = {"deep_scan", "backfill"}


def _reviewed_tag_grounds(object_key: Any, primary_object: Any, origin: Any) -> bool:
    """Reviewed Deep Scan / backfill tagging is itself authority for aboutness.

    The Radar reasons about the future, so a statement need not repeat the exact
    object vocabulary when a reviewed claim was filed under that object as its
    *primary* subject.  Provisional scanner claims and secondary tags still have to
    show the object in the visible text.
    """
    key, prim = clean(object_key), clean(primary_object)
    if not key or not prim or clean(origin) not in _REVIEWED_ORIGINS:
        return False
    if key == prim:
        return True
    fam = _family_of(key)
    if fam and key.startswith(FAMILY_PREFIX):
        return prim.split(".", 1)[0] == fam
    if fam:
        return prim in _FAMILY_MEMBERS.get(key, set())
    return False


def _ref_grounds_object(object_key: Any, ref: dict[str, Any]) -> bool:
    return _statement_grounds_object(object_key, ref.get("source_statement")) or _reviewed_tag_grounds(
        object_key, ref.get("object"), ref.get("claim_origin")
    )


def _object_anchor_is_visible(node: dict[str, Any], object_key: str | None = None) -> bool:
    """The visible statement concerns the target object, or a reviewed claim filed it there."""
    key = object_key or node.get("object")
    return _statement_grounds_object(key, node.get("text")) or _reviewed_tag_grounds(key, node.get("object"), node.get("origin"))


def _reader_trend_side(node: dict[str, Any], object_key: str | None = None) -> str:
    """Classify the side a source statement can support on the public trend page.

    The authoritative structured direction is useful for candidate discovery, but
    the reader-facing side must follow the visible statement.  Direction words are
    not enough on their own: the statement must visibly concern the structured
    object, and negated/adverse constructions must not be counted as expansion.
    Ambiguous statements are excluded from the public side counts.
    """
    text = clean(node.get("text"))
    if not text:
        return "expands" if clean(node.get("direction")) == "expands" else "constrains" if clean(node.get("direction")) in {"contracts", "becomes_conditional", "becomes_contested"} else ""
    target_object = clean(object_key or node.get("object"))
    if not _object_anchor_is_visible(node, target_object):
        return ""

    expands = any(rx.search(text) for rx in _DIRECTION_GROUNDING_PATTERNS.get("expands", ()))
    constrains = any(
        rx.search(text)
        for direction in ("contracts", "becomes_conditional", "becomes_contested")
        for rx in _DIRECTION_GROUNDING_PATTERNS.get(direction, ())
    )

    # Reader semantics must respect negation and adverse nouns.  These patterns
    # target recurring false positives where a generic expansion verb modified a
    # gap, dependence or a failed/non-established result rather than the object.
    if re.search(r"\b(?:no|not|without|cannot|can't|could not|failed to|did not)\b.{0,55}\b(?:establish|create|build|expand|increase|grow|fund|invest|launch|support|retain)\w*", text, re.I):
        # Do not erase a separate explicit positive action elsewhere; only remove
        # expansion when the positive cue is itself the negated construction.
        positive_elsewhere = re.search(r"\b(?:launched?|funded?|invested?|built|expanded?|opened?|established?)\b", text, re.I)
        if not positive_elsewhere or positive_elsewhere.group(0).lower() in {"established"}:
            expands = False
    if re.search(r"\b(?:widen(?:ing|ed)?|grow(?:ing|n)?|increas(?:ing|ed)?)\b.{0,40}\b(?:gap|gaps|dependence|dependency|barrier|barriers|deficit|deficits|shortage|shortages|inequality|inequalities|fragmentation)\b", text, re.I):
        constrains = True
        # A widening gap is not evidence that the underlying object is expanding.
        expands = False
    if re.search(r"\b(?:losing|lost) ground\b|\b(?:exposed to|reliant on|dependent on)\b.{0,35}\b(?:external|foreign|non[- ]?european|technology|capital|supplier|suppliers)\b|\bhighly asymmetric\b", text, re.I):
        constrains = True
    if target_object != "talent.retention" and re.search(r"\bretain(?:s|ed|ing)?\b", text, re.I):
        # Retaining a scientific/industrial base is stability, not expansion of a
        # different object.  Talent-retention claims are the intentional exception.
        if not re.search(r"\b(?:expand|increase|grow|build|launch|fund|invest|open|establish)\w*\b", text, re.I):
            expands = False
    if re.search(r"\b(?:less developed|below the .* mean|lower-readiness|persistent gaps?|uneven capacity|scarce specialist capacity|limited capacity|capacity remains weak)\b", text, re.I):
        constrains = True

    # ``investment`` and ``funding`` as bare nouns describe a topic, not necessarily
    # movement.  Require an action/amount/change cue before treating them as expansion.
    if expands and re.search(r"\binvestment\b", text, re.I) and not re.search(r"\b(?:new|additional|major|increased?|expanded?|announced?|committed?|raised?|round|subsid(?:y|ies)|€|eur|million|billion)\b.{0,55}\binvestment\b|\binvestment\b.{0,55}\b(?:increase|grow|expand|round|fund|finance|subsid)", text, re.I):
        # Keep other explicit positive verbs such as launched/built/established.
        if not re.search(r"\b(?:launch(?:ed|es)?|build(?:s|ing|t)?|establish(?:ed|es)?|open(?:ed|s)? access)\b", text, re.I):
            expands = False

    if expands and constrains:
        return ""
    if not expands and not constrains:
        # Neutral wording: trust the reviewed structured direction.  Scanner-only
        # claims stay excluded because their direction is not reviewed.
        if clean(node.get("origin")) in _REVIEWED_ORIGINS:
            direction = clean(node.get("direction"))
            if direction == "expands":
                return "expands"
            if direction in {"contracts", "becomes_conditional", "becomes_contested"}:
                return "constrains"
        return ""
    return "expands" if expands else "constrains"


_DEPENDENCY_LINK_CUE = re.compile(
    r"\b(?:depend(?:s|ed|ence|ency|ent)?|requir(?:e|es|ed|ement|ements)|reli(?:es|ed|ance|ant)|"
    r"coupl(?:e|es|ed|ing)|hinge(?:s|d)? on|conditional on|contingent on|needs?|through|via)\b",
    re.I,
)

_PRESSURE_DOMAIN_PATTERNS: dict[str, re.Pattern[str]] = {
    "export_control": re.compile(r"\b(?:export controls?|dual[- ]use|export licen[cs](?:e|ing)|technology restriction)\b", re.I),
    "critical_input": re.compile(r"\b(?:critical raw material|critical mineral|rare earth|material supply|materials?|mineral supply)\b", re.I),
    "security_reclassification": re.compile(r"\b(?:research security|knowledge security|dual[- ]use|sensitive research|security screening|reclassif)\b", re.I),
    "acquisition": re.compile(r"\b(?:acquisition|takeover|foreign ownership|investment screening)\b", re.I),
    "conflict": re.compile(r"\b(?:war|armed conflict|invasion|military escalation|hostilit)\b", re.I),
    "sanctions": re.compile(r"\b(?:sanctions?|asset freeze|payment restriction|financial restriction)\b", re.I),
    "data_access": re.compile(r"\b(?:data access|data transfer|cross[- ]border data|data locali[sz]ation)\b", re.I),
    "cyber": re.compile(r"\b(?:cyber|ransomware|software vulnerab|digital outage|network|server|website|system intrusion)\b", re.I),
    "energy": re.compile(r"\b(?:energy|power|electricity|grid)\b", re.I),
    "commercial": re.compile(r"\b(?:provider|vendor|service|repricing|market withdrawal|licen[cs]e restriction)\b", re.I),
    "external_finance": re.compile(r"\b(?:external finance|foreign capital|external capital|funding|debt)\b", re.I),
}


for _pid, _rx in _EXTRA_PR.items():
    _PRESSURE_DOMAIN_PATTERNS.setdefault(_pid, re.compile(_rx, re.I))


def _pressure_domain_is_visible(pressure_id: Any, statement: Any) -> bool:
    pid = clean(pressure_id)
    text = clean(statement)
    rx = _PRESSURE_DOMAIN_PATTERNS.get(pid)
    return bool(rx and text and rx.search(text))


def _reader_role_ref_grounded(
    grammar: str,
    raw: dict[str, Any],
    ref: dict[str, Any],
) -> bool:
    """Whether one displayed evidence row actually supports its assigned role.

    Structured role/object tags remain useful for broad candidate formation.  Public
    evidence, however, must not make a source appear to establish a role that is only
    present in metadata.  This predicate is deliberately role-specific and is used to
    demote mismatched rows to context rather than delete the candidate from stock.
    """
    role = clean(ref.get("role"))
    text = clean(ref.get("source_statement"))
    obj = clean(ref.get("object"))
    endpoints = [clean(x) for x in raw.get("endpoint_objects", []) if clean(x)] if isinstance(raw.get("endpoint_objects"), list) else []

    if not text:
        # Legacy/synthetic detector fixtures can predate reader-visible claim text.
        # Preserve their structural semantics; real corpus rows with statements are
        # checked below and cannot be rescued by role/object metadata alone.
        return True

    if grammar == "future_shock_hypothesis":
        asset = clean(raw.get("capability_object") or (endpoints[0] if endpoints else ""))
        pressure = clean(raw.get("pressure_id") or raw.get("dependency_object"))
        if role == "commitment":
            return _statement_grounds_object(asset or obj, text)
        if role == "external_driver":
            return _shock_driver_is_reader_grounded(pressure, text)
        if role == "bridge":
            # A bridge is useful strengthening evidence, but the futures-research
            # design explicitly allows the bridge itself to remain an inference.
            return _statement_grounds_object(asset or obj, text) and _pressure_domain_is_visible(pressure, text)
        return _statement_grounds_object(obj, text) if obj else True

    if grammar == "dependency_pathway":
        cap = clean(raw.get("capability_object") or (endpoints[0] if endpoints else ""))
        dep = clean(raw.get("dependency_object") or (endpoints[1] if len(endpoints) > 1 else ""))
        if role == "commitment":
            return _statement_grounds_object(cap or obj, text)
        if role == "coupling":
            # This is the load-bearing factual link.  It must visibly connect both
            # ends of the pathway and contain dependency language.
            return (
                _statement_grounds_object(cap, text)
                and _statement_grounds_object(dep, text)
                and bool(_DEPENDENCY_LINK_CUE.search(text))
            )
        if role == "propagation":
            # Propagation is allowed to remain the Radar's future inference.  When a
            # source row is displayed under this role, though, it must at least speak
            # directly about one of the pathway endpoints.
            return _statement_grounds_object(dep or obj, text) or _statement_grounds_object(cap, text)
        if role == "exposure":
            return _statement_grounds_object(cap or obj, text)
        return _statement_grounds_object(obj, text) if obj else True

    if grammar == "latent_channel":
        target = clean(endpoints[0] if endpoints else raw.get("objective_object"))
        structure = clean(endpoints[1] if len(endpoints) > 1 else raw.get("delivery_object"))
        if role == "unresolved_need":
            return _statement_grounds_object(target or obj, text)
        if role == "existing_structure":
            return _statement_grounds_object(structure or obj, text)
        if role == "live_connection":
            return (
                _statement_grounds_object(target, text)
                and _statement_grounds_object(structure, text)
                and bool(_DEPENDENCY_LINK_CUE.search(text))
            )
        if role == "receiving_instrument":
            return _statement_grounds_object(target or obj, text)
        if role == "precedent":
            return _statement_grounds_object(obj or target or structure, text)
        return _statement_grounds_object(obj, text) if obj else True

    if grammar == "conflicting_criteria":
        if role in {"criterion_a", "criterion_b", "arbitration_gap", "divergence"}:
            return _statement_grounds_object(obj, text) if obj else True

    return True


def _filter_reader_role_support(
    grammar: str,
    raw: dict[str, Any],
    support: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split role rows into direct source evidence and clearly-labelled context."""
    if grammar not in {"future_shock_hypothesis", "dependency_pathway", "latent_channel", "conflicting_criteria"}:
        return support, []
    direct: list[dict[str, Any]] = []
    contextual: list[dict[str, Any]] = []
    for ref in support:
        if _reader_role_ref_grounded(grammar, raw, ref):
            direct.append(ref)
            continue
        role = clean(ref.get("role")).replace("_", " ") or "assigned role"
        contextual.append(dict(
            ref,
            role="context",
            evidence_contribution=f"Related context; the source statement does not directly establish the {role} used in the finding.",
            original_role=clean(ref.get("role")),
        ))
    return direct, contextual


def _continuity_visible_counts(obj: str, nodes: list[dict[str, Any]]) -> dict[str, int]:
    """Count only source-visible evidence for a named ongoing phenomenon.

    Current primary evidence and historical context keep their separate provenance.
    Structured object tags can seed the candidate, but they do not count toward the
    reader-facing recurrence floor unless the source statement itself visibly concerns
    the named object.
    """
    current_records: set[str] = set()
    current_sources: set[str] = set()
    historical_records: set[str] = set()
    historical_sources: set[str] = set()
    for n in nodes:
        if clean(n.get("origin")) == "provisional":
            continue
        if not _object_matches(obj, n):
            continue
        if not _object_anchor_is_visible(n, obj):
            continue
        era = clean(n.get("era"))
        rid = clean(n.get("_record_id"))
        src = clean(n.get("_source")).lower()
        if era == "current":
            if not n.get("_primary") or _strand_code(n) not in {"A", "C"}:
                continue
            if rid:
                current_records.add(rid)
            if src:
                current_sources.add(src)
        elif era == "historical":
            if rid:
                historical_records.add(rid)
            if src:
                historical_sources.add(src)
    return {
        "current_record_count": len(current_records),
        "current_source_count": len(current_sources),
        "historical_record_count": len(historical_records),
        "historical_source_count": len(historical_sources),
    }


def _reader_visible_role_semantics(
    grammar: str,
    product: str,
    raw: dict[str, Any],
    support: list[dict[str, Any]],
) -> tuple[bool, str, dict[str, bool]]:
    """Check that the load-bearing *source* anchors are visible to the reader.

    The Radar is allowed to make future-facing inferences.  Therefore this guard does
    not require a source to state the future conclusion or every link in the causal
    chain.  It requires the factual anchors that the conclusion depends on, while
    optional/inferential links can remain explicitly Radar-owned.
    """
    by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ref in support:
        role = clean(ref.get("role"))
        if role:
            by_role[role].append(ref)

    checks: dict[str, bool] = {}
    endpoints = [clean(x) for x in raw.get("endpoint_objects", []) if clean(x)] if isinstance(raw.get("endpoint_objects"), list) else []

    if grammar == "future_shock_hypothesis":
        asset = clean(raw.get("capability_object") or (endpoints[0] if endpoints else ""))
        pressure = clean(raw.get("pressure_id") or raw.get("dependency_object"))
        commitments = by_role.get("commitment", [])
        drivers = by_role.get("external_driver", [])
        bridges = by_role.get("bridge", [])
        checks["commitment_names_asset"] = any(_statement_grounds_object(asset, x.get("source_statement")) for x in commitments)
        checks["driver_names_disruption"] = any(_shock_driver_is_reader_grounded(pressure, x.get("source_statement")) for x in drivers)
        checks["bridge_links_asset_and_pressure"] = any(
            _statement_grounds_object(asset, x.get("source_statement"))
            and _pressure_domain_is_visible(pressure, x.get("source_statement"))
            for x in bridges
        )
        # The design intentionally permits a future shock to combine separately
        # evidenced capability + disruption facts into a new scenario.  A direct
        # bridge strengthens maturity but is not a prerequisite for the hypothesis.
        ok = checks["commitment_names_asset"] and checks["driver_names_disruption"]
        return ok, "reader_visible_shock_anchors" if ok else "shock_anchors_not_visible_in_source_statements", checks

    if grammar == "dependency_pathway":
        cap = clean(raw.get("capability_object") or (endpoints[0] if endpoints else ""))
        dep = clean(raw.get("dependency_object") or (endpoints[1] if len(endpoints) > 1 else ""))
        commitments = by_role.get("commitment", [])
        couplings = by_role.get("coupling", [])
        propagation = by_role.get("propagation", [])
        exposure = by_role.get("exposure", [])
        checks["commitment_names_capability"] = any(_statement_grounds_object(cap, x.get("source_statement")) for x in commitments)
        checks["coupling_links_capability_and_dependency"] = any(
            _statement_grounds_object(cap, x.get("source_statement"))
            and _statement_grounds_object(dep, x.get("source_statement"))
            and bool(_DEPENDENCY_LINK_CUE.search(clean(x.get("source_statement"))))
            for x in couplings
        )
        checks["propagation_visible"] = any(
            _statement_grounds_object(dep, x.get("source_statement")) or _statement_grounds_object(cap, x.get("source_statement"))
            for x in propagation
        )
        checks["exposure_names_capability"] = (
            not exposure or any(_statement_grounds_object(cap, x.get("source_statement")) for x in exposure)
        )
        # Capability + dependency coupling are the factual core.  The future
        # propagation is allowed to remain the Radar's inference, exactly as the
        # futures-research architecture requires.
        ok = checks["commitment_names_capability"] and checks["coupling_links_capability_and_dependency"]
        return ok, "reader_visible_dependency_anchors" if ok else "dependency_anchors_not_visible_in_source_statements", checks

    if grammar == "latent_channel":
        target = clean(endpoints[0] if endpoints else raw.get("objective_object"))
        structure_obj = clean(endpoints[1] if len(endpoints) > 1 else raw.get("delivery_object"))
        need = by_role.get("unresolved_need", [])
        structure = by_role.get("existing_structure", [])
        live = by_role.get("live_connection", [])
        receiving = by_role.get("receiving_instrument", [])
        precedent = by_role.get("precedent", [])
        checks["unresolved_need_visible"] = any(_statement_grounds_object(target, x.get("source_statement")) for x in need)
        checks["existing_structure_visible"] = any(_statement_grounds_object(structure_obj, x.get("source_statement")) for x in structure)
        checks["connection_or_receiver_visible"] = any(
            _statement_grounds_object(target, x.get("source_statement")) for x in receiving
        ) or any(
            _statement_grounds_object(target, x.get("source_statement"))
            and _statement_grounds_object(structure_obj, x.get("source_statement"))
            for x in live
        ) or any(
            _statement_grounds_object(target, x.get("source_statement"))
            or _statement_grounds_object(structure_obj, x.get("source_statement"))
            for x in precedent
        )
        ok = all(checks.values())
        return ok, "reader_visible_latent_channel" if ok else "latent_channel_missing_reader_visible_core_role", checks

    if grammar == "conflicting_criteria":
        checks["criterion_a_visible"] = bool(by_role.get("criterion_a"))
        checks["criterion_b_visible"] = bool(by_role.get("criterion_b"))
        checks["arbitration_gap_visible"] = bool(by_role.get("arbitration_gap"))
        ok = all(checks.values())
        return ok, "reader_visible_criteria_collision" if ok else "criteria_collision_missing_reader_visible_core_role", checks

    return True, "not_applicable", checks

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
                "level4_opposing_movements": [], "level5_dependency_pathway": [], "future_shock_hypothesis": [],
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
                "level4_opposing_movements": [], "level5_dependency_pathway": [], "future_shock_hypothesis": [],
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
        "future_shock_hypothesis": exploratory_shock_hypotheses(nodes, vocab),
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


def _support_claim_primary(node: dict[str, Any]) -> bool:
    """Return downstream primary authority for a support node.

    Normal active-corpus nodes carry ``_primary`` explicitly.  A few retrace and
    regression fixtures intentionally provide only ``_collection``; in that case
    Strand A/frontier evidence must still behave as primary, while historical and
    context-only C remain context.  Explicit ``_primary`` always wins.
    """
    if "_primary" in node:
        return bool(node.get("_primary"))
    return _strand_code(node) == "A"


def _reader_evidence_contribution(role: Any) -> str:
    """Translate internal role names into reader-safe evidence contributions.

    These labels describe only what a source contributes to the evidence chain;
    they never attribute the Radar's final synthesis to that source.
    """
    r = clean(role).lower()
    labels = {
        "commitment": "Establishes the European capability, commitment or asset.",
        "coupling": "Establishes the dependency linking that capability to another input or condition.",
        "propagation": "Establishes a mechanism through which disruption could spread.",
        "exposure": "Establishes European exposure or the consequences of losing access.",
        "external_driver": "Establishes the documented disruption mechanism used in this scenario.",
        "bridge": "Establishes a direct link between the outside pressure and the European capability.",
        "unresolved_need": "Establishes the unresolved European need or gap.",
        "existing_structure": "Establishes an existing structure that could be used.",
        "live_connection": "Establishes a live connection between the need and the available structure.",
        "precedent": "Establishes a precedent showing that the route can work.",
        "receiving_instrument": "Establishes an instrument that could receive or scale the route.",
        "criterion_a": "Establishes one requirement acting on the same decision.",
        "criterion_b": "Establishes another requirement acting on the same decision.",
        "arbitration_gap": "Establishes that a common reconciliation rule is not yet visible.",
        "divergence": "Establishes uneven implementation or interpretation.",
        "expands": "Establishes movement in the expanding direction.",
        "constrains": "Establishes movement in the constraining direction.",
        "counter-evidence": "Establishes evidence that could weaken or qualify the finding.",
    }
    return labels.get(r, "")


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
            "claim_primary": _support_claim_primary(node),
            "claim_context_weight": round(float(node.get("_context_weight", 1.0) or 0), 3),
            "claim_origin": clean(node.get("origin")),
            "claim_kind": clean(node.get("kind")),
            "claim_status": clean(snap.get("status") or node.get("status")),
            "claim_merit": float(snap.get("merit", node.get("merit", 0)) or 0),
            "mechanism": clean(snap.get("mechanism") or node.get("mechanism")),
            "object": clean(snap.get("object")),
            # Reader evidence must preserve what the authoritative claim actually
            # says.  Titles identify publications; they are not evidence statements.
            # Keeping this narrow claim text beside the bibliographic metadata lets
            # reader surfaces show SOURCE EVIDENCE separately from Radar synthesis.
            "source_statement": clean(node.get("text")),
            "evidence_contribution": _reader_evidence_contribution(role),
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
            "claim_primary": _support_claim_primary(node),
            "claim_context_weight": round(float(node.get("_context_weight", 1.0) or 0), 3),
            "claim_origin": clean(node.get("origin")),
            "claim_kind": clean(node.get("kind")),
            "claim_status": clean(node.get("status")),
            "claim_merit": float(node.get("merit", 0) or 0),
            "mechanism": clean(node.get("mechanism")),
            "object": clean(node.get("object")),
            "source_statement": clean(node.get("text")),
            "evidence_contribution": _reader_evidence_contribution("support"),
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


# Domain-family scope ("family:research_security") groups every controlled object
# sharing a prefix.  It lets the Radar read a pattern across related objects
# (e.g. several research-security instruments) without inventing a new object.
# Vocabulary clusters ("cluster:compute_ai") are the same idea along the reviewed
# cluster map, which can cut across prefixes.
FAMILY_PREFIX = "family:"
CLUSTER_PREFIX = "cluster:"
_FAMILY_MEMBERS: dict[str, set[str]] = {}


def _family_of(key: Any) -> str:
    """Scope name for a family/cluster key; empty for an ordinary object."""
    key = clean(key)
    for prefix in (FAMILY_PREFIX, CLUSTER_PREFIX):
        if key.startswith(prefix):
            return key[len(prefix):]
    return ""


def _register_family(key: Any, members: Iterable[Any]) -> None:
    key = clean(key)
    if _family_of(key):
        _FAMILY_MEMBERS.setdefault(key, set()).update(clean(m) for m in members if clean(m))


def _object_matches(key: Any, n: dict[str, Any]) -> bool:
    key = clean(key)
    if not key:
        return False
    if key.startswith(CLUSTER_PREFIX):
        return bool(_node_objects(n) & _FAMILY_MEMBERS.get(key, set()))
    if key.startswith(FAMILY_PREFIX):
        fam = key[len(FAMILY_PREFIX):]
        return any(o.split(".", 1)[0] == fam for o in _node_objects(n))
    return key in _node_objects(n)


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
            "claim_primary": _support_claim_primary(node),
            "claim_kind": clean(node.get("kind")), "mechanism": clean(node.get("mechanism")),
            "object": clean(node.get("object")),
            "source_statement": clean(node.get("text")),
            "evidence_contribution": _reader_evidence_contribution("counter-evidence"),
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
    """Classify every finding on the same 1-5 novelty ladder.

    Wow is deliberately independent from evidence strength.  The stock may contain
    weak or incomplete wow-5 hypotheses and extremely well-supported wow-1 findings;
    page selection considers maturity *within* each wow bucket rather than allowing
    evidence strength to erase novelty diversity.
    """
    nodes = list(nodes)
    grammar = clean(raw_candidate.get("grammar_id"))
    if grammar == "era_conjunction":
        gain = float(raw_candidate.get("gain", 0) or 0)
        wow = 4 if gain >= 2.0 else 3 if gain >= 1.0 else 2
        return wow, {"mode": "era_gain", "gain": round(gain, 3)}

    if grammar == "opposing_movements":
        # Trends are structural, but the *novelty of the tension* can still vary.
        # Use how much history the object already has as a conservative proxy: a
        # newly contested capability is more surprising than an old recurring tug.
        obj = clean(raw_candidate.get("object"))
        cur_records = {
            clean(n.get("_record_id")) for n in nodes
            if clean(n.get("era")) == "current" and obj and _object_matches(obj, n)
        }
        hist_records = {
            clean(n.get("_record_id")) for n in nodes
            if clean(n.get("era")) == "historical" and obj and _object_matches(obj, n)
        }
        h = len({x for x in hist_records if x})
        stake = _stake_class(obj, vocab) in {"flagship", "rule", "budget", "capability"}
        if h == 0 and len(cur_records) <= 10:
            wow = 5
        elif h <= 1:
            wow = 4
        elif h <= 5:
            wow = 3
        elif h <= 15:
            wow = 2
        else:
            wow = 1
        return wow, {"mode": "trend_history_novelty", "current_records": len(cur_records), "historical_records": h}

    if grammar == "named_continuity":
        # A long-running issue can still be a new *kind* of phenomenon when its
        # direction or evidential mix changes sharply between eras.
        obj = clean(raw_candidate.get("object"))
        cur = [n for n in nodes if clean(n.get("era")) == "current" and _object_matches(obj, n)]
        hist = [n for n in nodes if clean(n.get("era")) == "historical" and _object_matches(obj, n)]
        directions = ("expands", "contracts", "becomes_conditional", "becomes_contested", "unchanged")
        def shares(rows, key, values):
            total = max(1, len(rows))
            return {v: sum(1 for n in rows if clean(n.get(key)) == v) / total for v in values}
        cd, hd = shares(cur, "direction", directions), shares(hist, "direction", directions)
        direction_shift = 0.5 * sum(abs(cd[v] - hd[v]) for v in directions)
        kinds = ("action", "effect", "diagnosis", "advocacy")
        ck, hk = shares(cur, "kind", kinds), shares(hist, "kind", kinds)
        kind_shift = 0.5 * sum(abs(ck[v] - hk[v]) for v in kinds)
        shift = max(direction_shift, kind_shift)
        wow = 5 if shift >= 0.75 else 4 if shift >= 0.50 else 3 if shift >= 0.35 else 2 if shift >= 0.22 else 1
        return wow, {"mode": "continuity_shape_change", "direction_shift": round(direction_shift, 3), "kind_shift": round(kind_shift, 3)}

    eps = [clean(x) for x in raw_candidate.get("endpoint_objects", []) if clean(x)] if isinstance(raw_candidate.get("endpoint_objects"), list) else []
    if grammar == "future_shock_hypothesis":
        wow = max(1, min(5, int(raw_candidate.get("wow_preliminary", 3) or 3)))
        return wow, {"mode": "shock_pair_familiarity", "joint_records": int(raw_candidate.get("pair_joint_records", 0) or 0), "compatibility_strength": int(raw_candidate.get("compatibility_strength", 0) or 0)}

    if grammar == "corroborated_claim":
        obj = clean(raw_candidate.get("object"))
        current_records = {clean(n.get("_record_id")) for n in nodes if clean(n.get("era")) == "current" and obj and _object_matches(obj, n)}
        historical_records = {clean(n.get("_record_id")) for n in nodes if clean(n.get("era")) == "historical" and obj and _object_matches(obj, n)}
        h = len({x for x in historical_records if x})
        c = len({x for x in current_records if x})
        stake = _stake_class(obj, vocab) in {"flagship", "rule", "budget", "capability"}
        if h == 0 and c <= 2 and stake:
            wow = 4
        elif h <= 2:
            wow = 3
        elif h <= 15:
            wow = 2
        else:
            wow = 1
        return wow, {"mode": "single_object_history_novelty", "current_records": c, "historical_records": h}
    if len(eps) < 2:
        return int(raw_candidate.get("wow_preliminary", 3) or 3), {"mode": "single_object_or_sequence"}
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


_FAMILY_LABELS = {
    "research": "the European research system",
    "research_security": "research security",
    "talent": "research talent",
    "digital": "digital policy",
    "ai": "AI",
    "compute": "computing capacity",
    "quantum": "quantum technology",
    "chips": "semiconductors",
    "horizon": "Horizon Europe",
    "export_control": "export controls",
    "finance": "R&I finance",
    "innovation": "innovation performance",
    "industrial": "industrial capacity",
    "defence": "defence R&I",
    "green": "green innovation",
    "health": "health research",
    "goal": "strategic goals",
    "funding": "research funding",
    "datacentre": "data centres",
    "materials": "critical materials",
    "cybersecurity": "cybersecurity",
    "compute_ai": "compute and AI infrastructure",
    "research_system": "the European research system",
    "capital_markets": "capital for European technology",
    "funding_programme": "EU funding programmes",
    "ai_governance": "AI governance",
    "digital_governance": "digital governance",
    "permitting_siting": "permitting and siting",
    "materials_energy": "materials and energy supply",
}


_TREND_TITLE_POOL: tuple[tuple[str, str], ...] = (
    ("Europe pushes {x} forward", "{X} runs into limits"),
    ("More money and moves behind {x}", "New conditions pile up around {x}"),
    ("{X} gains momentum", "Rules and costs rein {x} in"),
    ("Scaling up {x}", "{X} gets harder to do"),
    ("Europe doubles down on {x}", "Second thoughts slow {x}"),
    ("{X}: the build-out accelerates", "{X}: the fine print tightens"),
    ("Fresh commitments for {x}", "Friction grows around {x}"),
    ("{X} is on the rise", "{X} meets resistance"),
    ("Opening the throttle on {x}", "Pulling the handbrake on {x}"),
    ("{X} finds new backers", "{X} faces new hurdles"),
    ("Europe bets bigger on {x}", "The bill for {x} keeps rising"),
    ("{X} spreads", "{X} gets fenced in"),
)


def _trend_title_pair(label: str, key: str, index: int | None = None) -> tuple[str, str]:
    i = index if index is not None else int(hashlib.sha1(key.encode()).hexdigest(), 16) % len(_TREND_TITLE_POOL)
    left, right = _TREND_TITLE_POOL[i % len(_TREND_TITLE_POOL)]
    X = label[:1].upper() + label[1:]
    return left.format(x=label, X=X), right.format(x=label, X=X)


def _trend_scope_label(scope_kind: str, scope_key: str) -> str:
    if _family_of(scope_key) or scope_kind == "family":
        return _friendly_object_label(scope_key if _family_of(scope_key) else FAMILY_PREFIX + clean(scope_key))
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
    if text in aliases:
        return aliases[text]
    parts = clean(scope_key).split(".")
    if len(parts) == 2 and "_" in parts[1]:
        # "innovation.green_technology" reads as "green technology", not
        # "innovation green technology".
        return parts[1].replace("_", " ")
    return text or "this object"


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
    reader_side_by_claim: dict[str, str] = {}
    for n in nodes:
        if not n.get("_primary") or clean(n.get("era")) != "current" or not _object_matches(obj, n):
            continue
        # Provisional scanner claims may seed developing stock, but they are not
        # authoritative source evidence for a public reasoning card.
        if clean(n.get("origin")) == "provisional":
            continue
        scope = n.get("scope") if isinstance(n.get("scope"), dict) else {}
        scope_level = clean(scope.get("level"))
        external = scope_level in {"external", "third_country"}
        if scope_level not in {"eu", "member_state", "associated_country", "company_in_eu"} and not external:
            continue
        d = _date_only(n.get("status_date"))
        try:
            if len(d) == 10 and (evaluated_on - dt.date.fromisoformat(d)).days > 180:
                continue
        except ValueError:
            pass
        side = _reader_trend_side(n, obj)
        if external and side != "constrains":
            # Outside actors count only as external pressure on the European object.
            side = ""
        if side:
            rows.append(n)
            reader_side_by_claim[clean(n.get("claim_id"))] = side

    def side_of(n: dict[str, Any]) -> str:
        return reader_side_by_claim.get(clean(n.get("claim_id")), "")

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
                "claim_origin": clean(n.get("origin")),
                "claim_kind": clean(n.get("kind")),
                "claim_status": clean(n.get("status")),
                "mechanism": clean(n.get("mechanism")),
                "object": obj,
                "source_statement": clean(n.get("text")),
                "evidence_contribution": _reader_evidence_contribution(role),
            })
        return out

    scope_kind = "cluster" if clean(obj).startswith(CLUSTER_PREFIX) else "family" if _family_of(obj) else "object"
    label_text = _trend_scope_label(scope_kind, obj)

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
    short_label = label_text.replace(" as a whole", "")
    custom_title = obj in title_pairs
    left_title, right_title = title_pairs.get(obj, _trend_title_pair(short_label, obj))

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

    def strongest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        return max(rows, key=lambda n: (1 if clean(n.get("kind")) in {"action", "effect"} else 0,
                                        float(n.get("merit", 0) or 0), clean(n.get("status_date"))), default=None)

    def short(text: Any, words: int = 26) -> str:
        t = clean(text)
        parts = t.split()
        if len(parts) <= words:
            return t.rstrip(".") + "."
        return " ".join(parts[:words]).rstrip(",;:") + "…"

    def side_text(rows: list[dict[str, Any]], fallback: str) -> str:
        n = strongest(rows)
        if not n or not clean(n.get("text")):
            return fallback
        src = clean(n.get("_source"))
        body = short(n.get("text"))
        return f"{src}: {body}" if src else body

    left_plain = side_text(lk, f"Signs of Europe expanding {label_text} through {mechanism_phrase(lk)}.")
    right_plain = side_text(rk, f"Signs of {label_text} being constrained through {mechanism_phrase(rk)}.")

    def weight_word(con: int, total: int) -> str:
        if total == 0:
            return "nothing yet"
        if con == total:
            return "all concrete moves" if total > 1 else "one concrete move"
        if con == 0:
            return "talk rather than action so far" if total > 1 else "a single diagnosis, no action yet"
        return f"{con} concrete move{'s' if con != 1 else ''} among {total} signals"

    lw, rw = weight_word(lcon, len(lk)), weight_word(rcon, len(rk))
    if lcon == 0 and rcon == 0:
        composition = "Both sides are still mostly analysis and positions; neither has turned into concrete action yet."
    elif lcon > rcon:
        composition = f"The push is more concrete ({lw}) than the pushback ({rw})."
    elif rcon > lcon:
        composition = f"The pushback is more concrete ({rw}) than the push ({lw})."
    else:
        composition = f"Both sides are equally concrete: {lw} each way."

    pending = {"intention", "proposed", "in_negotiation", "announced", "call_open"}

    def pending_item(rows: list[dict[str, Any]]) -> str:
        cand = [n for n in rows if clean(n.get("status")) in pending and clean(n.get("_title"))]
        if not cand:
            return ""
        n = max(cand, key=lambda x: float(x.get("merit", 0) or 0))
        return clean(n.get("_title")).rstrip(".")

    lp, rp = pending_item(lk), pending_item(rk)
    if lp and rp:
        flip = f"Watch two things: if \u201c{lp}\u201d goes ahead, the push wins ground; if \u201c{rp}\u201d takes effect, the brakes do."
    elif lp:
        flip = f"The next swing depends on \u201c{lp}\u201d: if it goes ahead, the push gains; if it stalls, the constraints hold."
    elif rp:
        flip = f"The next swing depends on \u201c{rp}\u201d: if it takes effect, the constraints tighten; if it fades, the push regains ground."
    else:
        flip = "Nothing on either side is pending a decision, so the balance will move only with new evidence."

    return {
        "support": snaps(lk, "Expands") + snaps(rk, "Constrains"),
        "object": obj,
        "trend_scope": scope_kind,
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
            "title_label": short_label,
            "custom_title": custom_title,
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
    if clean(c.get("product")) == "shock":
        objects = [clean(x) for x in c.get("endpoint_objects", []) if clean(x)] if isinstance(c.get("endpoint_objects"), list) else []
        # A different disruption mechanism acting on the same European asset is a
        # different shock story.  Include the driver family explicitly; folding only
        # on the asset erased distinct cyber/export-control/power scenarios.
        driver = clean(c.get("pressure_id") or c.get("shock_pressure_id") or c.get("shock_driver_basis") or c.get("dependency_object"))
        return "shock", "|".join(([driver] if driver else []) + objects[:2]) or clean(c.get("topic_key"))
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
        if not bool(c.get("evidence_semantic_alignment", True)):
            return False, "source_statement_direction_mismatch"
        grounded_sources = int(c.get("direction_grounded_sources", c.get("primary_sources", 0)) or 0)
        grounded_records = int(c.get("direction_grounded_records", c.get("primary_records", 0)) or 0)
        # A single source may seed a grounded future hypothesis, but it is not
        # corroboration. Keep it in stock without mislabelling the evidence state.
        if grounded_sources < 2:
            return False, "single_source_anchor"
        # Genuine corroboration is the two-independent-source depth gate.
        return (
            bool(c.get("score_gate_passes"))
            and grounded_records >= 2
            and grounded_sources >= 2
        ), "corroborated_claim_floor"
    if grammar in _STRUCTURAL_VERIFICATION_GRAMMARS:
        return True, "authoritative_graph_structure"
    return bool(c.get("denial_tested")), "executed_candidate_falsifier"


def _maturity_score(c: dict[str, Any]) -> int:
    """Evidence/readiness score used *within* a wow bucket.

    This is intentionally not a permission-to-think gate.  Missing roles, thin
    sourcing and an unrun counter-evidence search lower maturity; they do not erase
    the hypothesis from stock.  Conversely, an executed clean challenge raises
    maturity but is not mandatory for a future-facing candidate to exist.
    """
    product = clean(c.get("product"))
    score = float(c.get("score", 0) or 0)
    records = int(c.get("primary_records", 0) or 0)
    sources = int(c.get("primary_sources", 0) or 0)
    coverage = float(c.get("primary_role_coverage", 0) or 0)
    missing = len(c.get("missing_roles", []) if isinstance(c.get("missing_roles"), list) else [])
    counter = int(c.get("counter_records", 0) or 0)
    # Incomplete Level-5 candidates often have no formal grammar score yet.  Use
    # the quality of the evidence already filling their roles as the provisional
    # score instead of treating them as zero-quality hypotheses.
    support = c.get("support") if isinstance(c.get("support"), list) else []
    qualities = [
        float(x.get("quality", 0) or 0) * float(x.get("analytical_weight", 1.0) if x.get("analytical_weight") is not None else 1.0)
        for x in support if isinstance(x, dict) and float(x.get("quality", 0) or 0) > 0
    ]
    provisional = (sum(qualities) / len(qualities)) * max(0.45, coverage) if qualities else 0.0
    evidence_base = max(score, provisional)
    maturity = 0.58 * evidence_base + 14 * min(1.0, sources / 3.0) + 10 * min(1.0, records / 4.0) + 14 * min(1.0, coverage)
    maturity -= 6 * missing
    maturity -= min(8, 2 * counter)
    if c.get("denial_tested"):
        maturity += 5
    if c.get("verification_gate_passes"):
        maturity += 4
    if c.get("oddity_passes") is False and int(c.get("wow", 0) or 0) >= 4:
        maturity -= 5
    if product == "shock" and not c.get("shock_driver"):
        maturity -= 20
    return max(0, min(99, int(round(maturity))))


def _presentation_ready(c: dict[str, Any]) -> tuple[bool, str]:
    """Low publication floor for a grounded future-facing finding.

    The public shelf is selective because each wow bucket has only three slots, not
    because candidate formation is forced to prove the future in advance.
    """
    product = clean(c.get("product"))
    if clean(c.get("status")) in {"killed", "dormant"}:
        return False, clean(c.get("status"))
    maturity = int(c.get("maturity_score", 0) or 0)
    sources = int(c.get("primary_sources", 0) or 0)
    records = int(c.get("primary_records", 0) or 0)
    coverage = float(c.get("primary_role_coverage", 0) or 0)
    grammar = clean(c.get("grammar_id"))

    if product == "trend":
        b = c.get("trend_balance") if isinstance(c.get("trend_balance"), dict) else {}
        lr, rr = int(b.get("left_records", 0) or 0), int(b.get("right_records", 0) or 0)
        ls, rs = int(b.get("left_sources", 0) or 0), int(b.get("right_sources", 0) or 0)
        total_sources = len({clean(x.get("source")).lower() for x in (c.get("support") or []) if isinstance(x, dict) and clean(x.get("source"))})
        ok = min(lr, rr) >= 1 and total_sources >= 2 and maturity >= 35
        return ok, "grounded_two_sided_tension" if ok else "trend_needs_two_sided_independent_grounding"

    if product == "continuity" and grammar == "named_continuity":
        cs = int(c.get("current_source_count", 0) or 0)
        hs = int(c.get("historical_source_count", 0) or 0)
        # Two current sources plus at least one historical source establishes that
        # the phenomenon spans both eras; a second historical source raises
        # maturity instead of being a hard gate.
        ok = cs >= 2 and hs >= 1 and maturity >= 32
        return ok, ("two_eras_two_sources" if hs >= 2 else "two_eras_grounded") if ok else "continuity_needs_broader_two_era_support"

    if product == "shock":
        if grammar == "future_shock_hypothesis" and not bool(c.get("shock_driver_semantic_alignment", True)):
            return False, "shock_driver_statement_mismatch"
        if grammar in {"future_shock_hypothesis", "dependency_pathway"} and not bool(c.get("role_semantic_alignment", True)):
            return False, clean(c.get("role_semantic_reason")) or "shock_route_not_visible_in_source_statements"
        # Future-facing shock hypotheses should not need the same source diversity as
        # a retrospective factual claim merely to compete for a wow slot.  Two
        # independent sources is the normal floor.  A complete pathway carried by
        # three distinct records from one authoritative source can also compete, but
        # its lower source-diversity score keeps it behind genuinely independent
        # alternatives inside the same wow bucket.
        normal_grounding = sources >= 2 and records >= 2 and coverage >= 0.50 and maturity >= 35
        concentrated_grounding = sources >= 1 and records >= 3 and coverage >= 0.75 and maturity >= 50
        ok = bool(c.get("shock_driver")) and bool(c.get("role_strength_floor_passes", True)) and (normal_grounding or concentrated_grounding)
        return ok, "grounded_future_shock" if ok else "shock_needs_stronger_driver_or_pathway_support"

    if product in {"risk", "opportunity"}:
        if grammar in {"dependency_pathway", "latent_channel", "conflicting_criteria"} and not bool(c.get("role_semantic_alignment", True)):
            return False, clean(c.get("role_semantic_reason")) or "reader_visible_role_semantics_failed"
        if grammar == "corroborated_claim":
            if not bool(c.get("evidence_semantic_alignment", True)):
                return False, "source_statement_direction_mismatch"
            grounded_sources = int(c.get("direction_grounded_sources", sources) or 0)
            grounded_records = int(c.get("direction_grounded_records", records) or 0)
            # A concrete current record can anchor a baseline future implication, but
            # the source statement must actually support the direction used on-card.
            ok = grounded_sources >= 1 and grounded_records >= 1 and maturity >= 48
            return ok, "evidence_anchored_baseline" if ok else "baseline_needs_stronger_source_or_status"
        structural = coverage >= 0.50 or grammar in _STRUCTURAL_VERIFICATION_GRAMMARS
        independent = sources >= 2 and records >= 2 and maturity >= 35
        # A complete mechanism carried by three records of one strong source may
        # compete; its lower source diversity keeps it behind independent findings.
        concentrated = sources >= 1 and records >= 3 and coverage >= 0.75 and maturity >= 48
        ok = bool(c.get("role_strength_floor_passes", True)) and structural and (independent or concentrated)
        return ok, "grounded_future_finding" if ok else "needs_second_source_or_more_complete_mechanism"

    ok = sources >= 2 and records >= 2 and maturity >= 35
    return ok, "grounded_future_finding" if ok else "needs_more_grounding"


SHELF_SWAP_MARGIN = 4

# Page variety: one disruption type or one asset must not dominate a shelf.
SHOCK_MAX_PER_DRIVER = 2
SHOCK_MAX_PER_ASSET = 2
MAX_PER_TOPIC = 2

_SHOCK_TITLES: dict[str, tuple[str, ...]] = {
    "cyber": (
        "What if a cyber incident knocked out {asset}?",
        "One breach, and {asset} goes dark.",
        "{Asset} is one ransomware note away from a standstill.",
    ),
    "energy": (
        "{Asset} could stall if Europe's power runs short.",
        "When the grid is rationed, who switches off {asset} first?",
        "A winter power squeeze could put {asset} on pause.",
    ),
    "export_control": (
        "Foreign export controls could cut {asset} off from what it needs.",
        "A licence stamped abroad could decide the future of {asset}.",
        "One new export list could leave {asset} without its parts.",
    ),
    "security_reclassification": (
        "{Asset} could suddenly be treated as security-sensitive.",
        "Overnight, {asset} could move from open science to closed doors.",
        "A new security label could quietly shrink who may work on {asset}.",
    ),
    "conflict": (
        "A wider conflict could pull people and money away from {asset}.",
        "If fighting spreads, {asset} could be the first budget line to go.",
        "War elsewhere could redraw the map {asset} depends on.",
    ),
    "critical_input": (
        "A materials shortage could halt {asset}.",
        "{Asset} runs on inputs Europe does not control.",
        "No material, no {asset}: a supply squeeze could stop it cold.",
    ),
    "sanctions": (
        "Sanctions could freeze the money and partners behind {asset}.",
        "A sanctions round aimed elsewhere could land on {asset}.",
        "Payments blocked, partners gone: sanctions could strand {asset}.",
    ),
    "acquisition": (
        "A foreign takeover could move {asset} out of European control.",
        "{Asset} could be bought before Europe notices it was for sale.",
        "One acquisition could carry {asset}'s know-how abroad.",
    ),
    "data_access": (
        "A data-transfer ban could stop {asset} using the data it relies on.",
        "If the data stops crossing borders, {asset} stops too.",
    ),
    "commercial": (
        "{Asset} could lose a key provider overnight.",
        "A single price change from a provider could break {asset}.",
    ),
    "external_finance": (
        "{Asset} could lose outside money fast.",
        "When foreign capital blinks, {asset} could be left short.",
    ),
    "funding_cut": (
        "A sudden funding cut could stall {asset}.",
        "The next budget fight could leave {asset} unfinished.",
        "{Asset} could be the quiet casualty of a spending squeeze.",
    ),
    "talent_flight": (
        "{Asset} could lose the people who run it.",
        "If the best researchers leave, {asset} stays behind as an empty shell.",
        "A recruitment drive elsewhere could empty the labs behind {asset}.",
    ),
    "political_shift": (
        "A political turn could put {asset} on the chopping block.",
        "One election could rewrite the rules for {asset}.",
        "{Asset} could become a political bargaining chip.",
    ),
    "regulatory_shift": (
        "A sudden rule change could force {asset} to stop and redesign.",
        "One court ruling could send {asset} back to the drawing board.",
        "{Asset} could wake up non-compliant.",
    ),
    "tech_leap": (
        "A rival's technology leap could make {asset} obsolete before it pays off.",
        "What if someone else gets there first, and {asset} is suddenly yesterday's plan?",
        "A breakthrough abroad could turn {asset} into a catch-up project.",
    ),
    "info_manipulation": (
        "A foreign information campaign could turn opinion against {asset}.",
        "A well-aimed disinformation wave could make {asset} politically toxic.",
    ),
    "chokepoint": (
        "One chokepoint supplier could hold {asset} hostage.",
        "{Asset} hangs on a single thread someone else holds.",
        "Pull one supplier, and {asset} unravels.",
    ),
    "hazard": (
        "A climate or health emergency could shut down {asset}.",
        "One heatwave or outbreak could close the doors on {asset}.",
    ),
}


def _shock_title(pid: str, lead: str, asset: str) -> str:
    variants = _SHOCK_TITLES.get(pid)
    if not variants:
        return f"{lead} could disrupt {asset}."
    # Stable per card (same wording every scan), varied across cards.
    idx = int(hashlib.sha1(f"{pid}|{asset}".encode()).hexdigest(), 16) % len(variants)
    tpl = variants[idx]
    return tpl.format(asset=asset, Asset=asset[:1].upper() + asset[1:])


_SHOCK_CONSEQUENCE = {
    "cyber": "A cyber incident could take {asset} offline or compromise it, and European teams have little ready backup to switch to.",
    "energy": "Scarce or rationed power could force {asset} to compete with other essential uses for electricity, slowing or pausing it.",
    "export_control": "Export controls imposed elsewhere could cut {asset} off from equipment, components or partners it currently relies on.",
    "security_reclassification": "If the work is suddenly reclassified as security-sensitive, {asset} could lose partners, people or openness overnight.",
    "conflict": "A conflict escalation could divert money and attention and cut the people, sites or supply routes that {asset} depends on.",
    "critical_input": "A shortage of critical materials or components could halt {asset} where there is no fast substitute.",
    "sanctions": "Sanctions or payment restrictions could freeze the funding flows and partnerships behind {asset}.",
    "acquisition": "A foreign takeover of a key firm could move control of {asset}, and its know-how, outside Europe.",
    "data_access": "A cross-border data restriction could stop {asset} from lawfully using the data it needs.",
    "commercial": "If a key provider withdraws or reprices, {asset} could lose a service it cannot quickly replace.",
    "external_finance": "If outside money pulls back quickly, {asset} could lose the capital it has been counting on.",
    "funding_cut": "A budget cut or freeze could stop {asset} mid-course, with teams and equipment left stranded.",
    "talent_flight": "If key researchers leave or cannot come, {asset} could lose the expertise it cannot hire back quickly.",
    "political_shift": "A change of government or political climate could withdraw support from {asset} or restrict who can take part.",
    "regulatory_shift": "An abrupt new rule or court ruling could force {asset} to pause, redesign or seek fresh approval.",
    "tech_leap": "If a rival leaps ahead, the case for {asset} could collapse and funding could move elsewhere.",
    "info_manipulation": "A coordinated information campaign could erode public or political trust in {asset}.",
    "chokepoint": "If a single foreign supplier or platform restricts access, {asset} could stall with no ready alternative.",
    "hazard": "An extreme-weather event or public-health emergency could close facilities and halt work on {asset}.",
}


def _shock_consequence(raw: dict[str, Any], out: dict[str, Any]) -> str:
    eps = [clean(x) for x in (raw.get("endpoint_objects") or []) if clean(x)]
    pid = clean(raw.get("pressure_id")) or next((x.split(".", 1)[1] for x in eps if x.startswith("shock_pressure.")), "")
    asset = _friendly_object_label(raw.get("capability_object") or (raw.get("endpoint_objects") or [""])[0])
    base = _SHOCK_CONSEQUENCE.get(pid, "The disruption could remove something {asset} depends on before Europe can replace it.").format(asset=asset)
    base = base[0].upper() + base[1:]
    driver = next((x for x in (out.get("support") or []) if isinstance(x, dict) and clean(x.get("role")) == "external_driver"), None)
    if driver and clean(driver.get("source")):
        return f"{base} Signal behind it: {clean(driver.get('source'))} reports the disruption itself; the link to {asset} is the Radar's hypothesis."
    return base


def _diversity_keys(c: dict[str, Any]) -> list[tuple[str, str, int]]:
    """(kind, key, cap) limits that keep one story from dominating a page."""
    product = clean(c.get("product"))
    eps = [clean(x) for x in (c.get("endpoint_objects") or []) if clean(x)] if isinstance(c.get("endpoint_objects"), list) else []
    if product == "shock":
        driver = next((x for x in eps if x.startswith("shock_pressure.")), "") or clean(c.get("pressure_id"))
        asset = next((x for x in eps if not x.startswith("shock_pressure.")), "")
        keys = []
        if driver:
            keys.append(("driver", driver, SHOCK_MAX_PER_DRIVER))
        if asset:
            keys.append(("asset", asset, SHOCK_MAX_PER_ASSET))
        return keys
    topic = clean(c.get("object") or (eps[0] if eps else "") or c.get("topic_key"))
    return [("topic", topic, MAX_PER_TOPIC)] if topic else []

# Creative reserve: the reserve is not only the runners-up.  It deliberately
# holds hypotheses that are relevant and not contradicted but not yet provable -
# distant, cross-domain, newly emerging, weak-signal or partially grounded - so
# they can mature instead of being filtered out too early.
RESERVE_TARGET = 45
CREATIVE_RESERVE_MIN = 18
# Round-robin over wow levels, weighted toward surprise but still covering 1-2.
CREATIVE_WOW_ORDER = (5, 4, 3, 5, 4, 2, 5, 3, 1)


def _prefix(obj: Any) -> str:
    obj = clean(obj)
    if obj.startswith("shock_pressure."):
        return "shock_pressure"
    return obj.split(".", 1)[0] if obj else ""


def _creative_traits(c: dict[str, Any], evaluated_on: str = "") -> dict[str, bool]:
    support = [x for x in (c.get("support") or []) if isinstance(x, dict)]
    context = [x for x in (c.get("context") or []) if isinstance(x, dict)]
    rows = support + context
    endpoints = [clean(x) for x in (c.get("endpoint_objects") or []) if clean(x)] if isinstance(c.get("endpoint_objects"), list) else []
    obj = clean(c.get("object"))
    domains = {_prefix(x) for x in endpoints} | {_prefix(x.get("object")) for x in rows if clean(x.get("object"))}
    domains.discard("")
    newest = max((clean(x.get("date"))[:10] for x in rows if clean(x.get("date"))), default="")
    recent = False
    if newest and evaluated_on and len(newest) == 10 and len(evaluated_on) >= 10:
        try:
            recent = (dt.date.fromisoformat(evaluated_on[:10]) - dt.date.fromisoformat(newest)).days <= 30
        except ValueError:
            recent = False
    return {
        "distant": int(c.get("wow", 0) or 0) >= 4 or int(c.get("level", 0) or 0) >= 5,
        "cross_domain": len({_prefix(x) for x in endpoints if _prefix(x)}) >= 2
        or bool(_family_of(obj)) or len(domains) >= 3,
        "emerging": bool(c.get("new_this_scan") or c.get("updated_this_scan"))
        or any(x.get("new_this_scan") for x in rows) or recent,
        "weak_signal": any(clean(x.get("strand")) == "C" for x in rows),
        "partially_grounded": any(
            clean(x.get("claim_origin")) in _REVIEWED_ORIGINS for x in rows
        ) or len({clean(x.get("source")).lower() for x in rows if clean(x.get("source"))}) >= 2,
    }


def _creative_eligible(c: dict[str, Any]) -> tuple[bool, str]:
    if clean(c.get("status")) in {"killed", "dormant"}:
        return False, "killed_or_dormant"
    support = [x for x in (c.get("support") or []) if isinstance(x, dict)]
    context = [x for x in (c.get("context") or []) if isinstance(x, dict)]
    if not support and not context:
        return False, "no_evidence"
    counter = int(c.get("counter_records", 0) or 0)
    backing = len({clean(x.get("identity")) for x in support + context if clean(x.get("identity"))})
    if counter and counter >= max(2, backing):
        return False, "contradicted"
    return True, ""


def _creative_score(c: dict[str, Any], traits: dict[str, bool]) -> float:
    return (
        8 * int(c.get("wow", 0) or 0)
        + 12 * traits["cross_domain"]
        + 10 * traits["emerging"]
        + 7 * traits["weak_signal"]
        + 8 * traits["partially_grounded"]
        + 0.25 * min(80, int(c.get("maturity_score", 0) or 0))
    )


def _selection_rank(c: dict[str, Any]) -> tuple[int, int, int, int, str]:
    # The final id component is a fixed tie-breaker: equal findings must not swap
    # places between scans when no evidence changed.
    return (
        int(c.get("maturity_score", 0) or 0),
        int(c.get("score", 0) or 0),
        int(c.get("primary_sources", 0) or 0),
        int(c.get("primary_records", 0) or 0),
        clean(c.get("id")),
    )


def _select_stage7(candidates: list[dict[str, Any]], previous_state: dict[str, Any]) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Build a large hypothesis corpus and a balanced 15-slot reader shelf.

    Every active hypothesis remains in stock.  A deliberately low grounding floor
    separates developing hypotheses from publishable findings.  Publishable findings
    are then ranked *within* wow 1-5, with three slots reserved for each wow level.
    The reader order cycles 5,4,3,2,1 three times so surprise never crowds out the
    baseline and the baseline never crowds out surprise.
    """
    products = ("shock", "trend", "continuity", "risk", "opportunity")
    slots_per_wow = 3
    prev_pubs = previous_state.get("publications") if isinstance(previous_state.get("publications"), dict) else {}
    prev_map = {
        clean(x.get("id")): x
        for x in previous_state.get("candidates", [])
        if isinstance(x, dict) and clean(x.get("id"))
    }
    out = {k: [] for k in products}
    meta: dict[str, Any] = {}

    for product in products:
        pool = [c for c in candidates if c.get("claim_native") and clean(c.get("product")) == product]
        previous_ids = [clean(x) for x in (prev_pubs.get(product, []) if isinstance(prev_pubs.get(product), list) else []) if clean(x)]
        previous_set = set(previous_ids)

        for c in pool:
            verified, mode = _verification_gate(c)
            c["verification_mode"] = mode
            c["verification_gate_passes"] = bool(verified)
            c["maturity_score"] = _maturity_score(c)
            ready, basis = _presentation_ready(c)
            c["presentation_ready"] = bool(ready)
            c["presentation_basis"] = basis
            c["reader_eligible"] = False
            c["publication_gate_passes"] = False
            c.pop("page_slot_wow", None)
            if clean(c.get("grammar_id")) == "future_shock_hypothesis":
                # Carried-forward shocks keep stored copy; refresh the wording so
                # every card uses its disruption-specific title and explanation.
                eps0 = [clean(x) for x in (c.get("endpoint_objects") or []) if clean(x)]
                pid0 = clean(c.get("pressure_id")) or next((x.split(".", 1)[1] for x in eps0 if x.startswith("shock_pressure.")), "")
                asset0 = _friendly_object_label(c.get("capability_object") or next((x for x in eps0 if not x.startswith("shock_pressure.")), ""))
                if pid0 in _SHOCK_TITLES and asset0:
                    c["reader_title"] = _shock_title(pid0, "", asset0)
                    c["reader_consequence"] = _shock_consequence({"pressure_id": pid0, "capability_object": c.get("capability_object") or next((x for x in eps0 if not x.startswith("shock_pressure.")), "")}, c)
            if c.get("creative_reserve") or clean(c.get("stock_tier")) == "creative_reserve":
                # Creative reserve is re-decided every scan; never inherit it as
                # grounded reserve.
                c["creative_reserve"] = False
                c["movement"] = "watch"

        # Shelf lifecycle semantics: ``qualified`` means the finding is grounded
        # enough to compete for a public slot.  ``watch`` means it remains a
        # developing hypothesis.  This keeps the persistent corpus broad while
        # preserving the downstream integrity invariant that every published ID
        # points to a qualified, reader-eligible candidate.  Verification details
        # remain separate in verification_gate_passes / verification_mode.
        for c in pool:
            current_status = clean(c.get("status"))
            if current_status in {"killed", "dormant"}:
                continue
            c["pre_shelf_status"] = current_status
            c["status"] = "qualified" if c.get("presentation_ready") else "watch"

        ready = [c for c in pool if c.get("presentation_ready") and clean(c.get("status")) == "qualified"]
        ready.sort(key=lambda c: (int(c.get("wow", 0) or 0),) + _selection_rank(c), reverse=True)

        # Same-story variants compete for one public narrative.  Keep the strongest
        # version available for page selection; folded variants remain reserve.
        deduped: list[dict[str, Any]] = []
        folded = 0
        def evidence_ids(x: dict[str, Any]) -> set[str]:
            return {clean(r.get("identity")) for r in (x.get("support") or []) if isinstance(r, dict) and clean(r.get("identity"))}

        def same_evidence(a: dict[str, Any], b: dict[str, Any]) -> bool:
            ea, eb = evidence_ids(a), evidence_ids(b)
            return bool(ea and eb) and len(ea & eb) / max(1, min(len(ea), len(eb))) >= 0.8

        for cand in ready:
            # Same story, or the same evidence under another name (e.g. a topic and
            # its wider field built on identical sources), competes for one card.
            conflict = next((x for x in deduped if _story_key(x) == _story_key(cand) or same_evidence(x, cand)), None)
            if conflict is None:
                deduped.append(cand)
                continue
            cr = (int(cand.get("wow", 0) or 0),) + _selection_rank(cand)
            xr = (int(conflict.get("wow", 0) or 0),) + _selection_rank(conflict)
            if cr > xr:
                conflict["folded_into"] = cand.get("id")
                conflict["movement"] = "reserve"
                deduped.remove(conflict)
                deduped.append(cand)
            else:
                cand["folded_into"] = conflict.get("id")
                cand["movement"] = "reserve"
                conflict.setdefault("also_ids", []).append(cand.get("id"))
            folded += 1

        def select_wow_bucket(items: list[dict[str, Any]], wow: int) -> list[dict[str, Any]]:
            bucket = [c for c in items if int(c.get("wow", 0) or 0) == wow]
            bucket.sort(key=_selection_rank, reverse=True)
            if len(bucket) <= slots_per_wow:
                return bucket
            # Evidence-driven churn within a wow bucket.  New records never take a
            # slot by themselves; they update the reasoning (support, sources,
            # maturity) of candidates, and the shelf is re-decided every scan.  An
            # incumbent keeps its slot unless a challenger's recomputed maturity
            # beats it by SHELF_SWAP_MARGIN points.  This does not alter the three-slot
            # capacity and never lets another wow bucket steal the slot.
            # Rank order, not last scan's display order: otherwise equal incumbents
            # flip between their own slots and borrowed slots every scan.
            incumbents = sorted(
                [c for c in bucket if clean(c.get("id")) in previous_set],
                key=_selection_rank, reverse=True,
            )
            selected: list[dict[str, Any]] = []
            selected_ids: set[str] = set()
            for c in incumbents:
                cid = clean(c.get("id"))
                if cid and cid not in selected_ids and len(selected) < slots_per_wow:
                    selected.append(c); selected_ids.add(cid)
            for c in bucket:
                cid = clean(c.get("id"))
                if not cid or cid in selected_ids:
                    continue
                if len(selected) < slots_per_wow:
                    selected.append(c); selected_ids.add(cid); continue
                weakest = min(selected, key=_selection_rank)
                if int(c.get("maturity_score", 0) or 0) >= int(weakest.get("maturity_score", 0) or 0) + SHELF_SWAP_MARGIN:
                    selected.remove(weakest); selected_ids.discard(clean(weakest.get("id")))
                    selected.append(c); selected_ids.add(cid)
            return sorted(selected, key=_selection_rank, reverse=True)

        # Variety caps across the whole page.  Candidates over a cap stay in
        # reserve; if caps make the page impossible to fill they are relaxed.
        diversity_used: Counter = Counter()

        def fits(c: dict[str, Any]) -> bool:
            return all(diversity_used[(k, v)] < cap for k, v, cap in _diversity_keys(c))

        def take(c: dict[str, Any]) -> None:
            for k, v, _cap in _diversity_keys(c):
                diversity_used[(k, v)] += 1

        by_wow = {}
        for wow in (5, 4, 3, 2, 1):
            picked = []
            for c in select_wow_bucket([x for x in deduped if fits(x)], wow):
                if fits(c):
                    picked.append(c); take(c)
            # Top up from the rest of the bucket that still fits.
            rest = sorted([x for x in deduped if int(x.get("wow", 0) or 0) == wow and x not in picked and fits(x)], key=_selection_rank, reverse=True)
            for c in rest:
                if len(picked) >= slots_per_wow:
                    break
                if fits(c):
                    picked.append(c); take(c)
            by_wow[wow] = picked
        # A thin wow bucket must not leave a hole in the 15-slot page.  Each empty
        # slot is filled from the nearest wow level that still has grounded
        # reserve (ties prefer the lower, more visible level), so the page keeps
        # the widest possible 1-5 spread instead of shrinking.
        taken = {clean(c.get("id")) for items in by_wow.values() for c in items}
        spare = {
            wow: sorted(
                [c for c in deduped if int(c.get("wow", 0) or 0) == wow and clean(c.get("id")) not in taken],
                key=_selection_rank, reverse=True,
            )
            for wow in (5, 4, 3, 2, 1)
        }
        borrowed = 0
        for wow in (5, 4, 3, 2, 1):
            while len(by_wow[wow]) < slots_per_wow:
                donors = sorted(
                    (w for w in (5, 4, 3, 2, 1) if w != wow and spare[w]),
                    key=lambda w: (abs(w - wow), w),
                )
                if not donors:
                    break
                fitting = next((x for w in donors for x in spare[w] if fits(x)), None)
                if fitting is None:
                    # Relax one step (cap + 1) before giving up on variety entirely.
                    fitting = next((x for w in donors for x in spare[w] if all(diversity_used[(k, v)] < cap + 1 for k, v, cap in _diversity_keys(x))), None)
                if fitting is not None:
                    spare[int(fitting.get("wow", 0) or 0)].remove(fitting)
                    c = fitting
                else:
                    c = spare[donors[0]].pop(0)  # caps relaxed only as last resort
                take(c)
                c["page_slot_wow"] = wow
                by_wow[wow].append(c)
                borrowed += 1
        chosen: list[dict[str, Any]] = []
        for round_idx in range(slots_per_wow):
            for wow in (5, 4, 3, 2, 1):
                if round_idx < len(by_wow[wow]):
                    chosen.append(by_wow[wow][round_idx])

        if product == "trend":
            # No two trend cards share a title pattern: give each generic card the
            # next unused phrasing, starting from its own preferred one.
            used_patterns: set[int] = set()
            for c in chosen:
                b = c.get("trend_balance") if isinstance(c.get("trend_balance"), dict) else {}
                if b.get("custom_title") or not clean(b.get("title_label")):
                    continue
                key = clean(c.get("object"))
                start = int(hashlib.sha1(key.encode()).hexdigest(), 16) % len(_TREND_TITLE_POOL)
                for k in range(len(_TREND_TITLE_POOL)):
                    idx = (start + k) % len(_TREND_TITLE_POOL)
                    if idx not in used_patterns:
                        used_patterns.add(idx)
                        b["left_title"], b["right_title"] = _trend_title_pair(clean(b["title_label"]), key, idx)
                        break
        if product == "shock":
            # No two shock cards on the page share a phrasing: a card whose
            # preferred wording is taken moves to the next unused variant.
            used_titles: set[str] = set()
            for c in chosen:
                eps0 = [clean(x) for x in (c.get("endpoint_objects") or []) if clean(x)]
                pid0 = clean(c.get("pressure_id")) or next((x.split(".", 1)[1] for x in eps0 if x.startswith("shock_pressure.")), "")
                asset0 = _friendly_object_label(c.get("capability_object") or next((x for x in eps0 if not x.startswith("shock_pressure.")), ""))
                variants = _SHOCK_TITLES.get(pid0)
                if variants and asset0:
                    start = int(hashlib.sha1(f"{pid0}|{asset0}".encode()).hexdigest(), 16) % len(variants)
                    for k in range(len(variants)):
                        tpl = variants[(start + k) % len(variants)]
                        if tpl not in used_titles:
                            used_titles.add(tpl)
                            c["reader_title"] = tpl.format(asset=asset0, Asset=asset0[:1].upper() + asset0[1:])
                            break
        out[product] = [clean(c.get("id")) for c in chosen if clean(c.get("id"))]
        chosen_ids = set(out[product])
        ready_ids = {clean(c.get("id")) for c in ready}

        for c in pool:
            cid = clean(c.get("id"))
            old = prev_map.get(cid)
            if cid in chosen_ids:
                stable = bool(old) and int(c.get("wow", 0) or 0) == int(old.get("wow", 0) or 0) and int(c.get("maturity_score", 0) or 0) == int(old.get("maturity_score", old.get("score", 0)) or 0) and not c.get("updated_this_scan")
                c["shown_unchanged_scans"] = (int(old.get("shown_unchanged_scans", 0) or 0) + 1) if stable else 0
                if product == "trend" and old and isinstance(old.get("trend_balance"), dict) and isinstance(c.get("trend_balance"), dict):
                    old_range = old["trend_balance"].get("left_range") or []
                    new_range = c["trend_balance"].get("left_range") or []
                    if len(old_range) >= 2 and len(new_range) >= 2 and max(abs(float(new_range[0])-float(old_range[0])), abs(float(new_range[1])-float(old_range[1]))) < 3:
                        c["trend_balance_computed"] = copy.deepcopy(c["trend_balance"])
                        fresh = c["trend_balance"]
                        c["trend_balance"] = copy.deepcopy(old["trend_balance"])
                        # Freeze only the numbers (so the bar does not wobble); the
                        # wording always follows the current evidence.
                        for key in ("left_title", "right_title", "left_plain", "right_plain", "composition", "flip_line", "label"):
                            if key in fresh:
                                c["trend_balance"][key] = fresh[key]
                        c["published_band_changed"] = False
                    else:
                        c["published_band_changed"] = True
                if cid not in previous_set:
                    c["movement"] = "up"; c["reader_status_chip"] = "New"
                elif old and int(c.get("wow", 0) or 0) > int(old.get("wow", 0) or 0):
                    c["movement"] = "up"; c["reader_status_chip"] = "Rising"
                elif old and int(c.get("maturity_score", 0) or 0) > int(old.get("maturity_score", old.get("score", 0)) or 0):
                    c["movement"] = "up"; c["reader_status_chip"] = "Rising"
                elif old and (int(c.get("wow", 0) or 0) < int(old.get("wow", 0) or 0) or int(c.get("missed_detection_scans", 0) or 0) >= 3):
                    c["movement"] = "down"; c["reader_status_chip"] = "Fading"
                elif c.get("updated_this_scan"):
                    c["movement"] = "hold"; c["reader_status_chip"] = "Updated"
                else:
                    c["movement"] = "hold"; c["reader_status_chip"] = "Unchanged"
                c["reader_eligible"] = True
                c["publication_gate_passes"] = True
                c["publication_lock_reason"] = ""
                c["stock_tier"] = "page"
            elif clean(c.get("status")) == "killed":
                c["movement"] = "killed"; c["stock_tier"] = "killed"
            elif clean(c.get("status")) == "dormant":
                c["movement"] = "dormant"; c["stock_tier"] = "dormant"
                c["publication_lock_reason"] = clean(c.get("exit_reason")) or "Dormant stock item."
            elif cid in ready_ids or clean(c.get("movement")) == "reserve":
                c["movement"] = "reserve"; c["stock_tier"] = "reserve"
                c["publication_lock_reason"] = "Grounded finding held off-page because its wow bucket already has stronger findings or it is folded into the same story."
            else:
                c["movement"] = "watch"; c["stock_tier"] = "watch"
                c["publication_lock_reason"] = "Developing hypothesis: grounded enough to retain, but it still needs stronger or more independent evidence before public presentation."

        # ---- Creative reserve -------------------------------------------------
        grounded_reserve = [c for c in pool if clean(c.get("movement")) == "reserve"]
        creative_quota = max(CREATIVE_RESERVE_MIN, RESERVE_TARGET - len(grounded_reserve))
        evaluated_on = max((clean(c.get("last_updated_at"))[:10] for c in pool if clean(c.get("last_updated_at"))), default="")
        creative_pool: dict[int, list[tuple[float, dict[str, Any]]]] = {w: [] for w in (5, 4, 3, 2, 1)}
        for c in pool:
            c.pop("creative_reserve", None); c.pop("creative_traits", None)
            if clean(c.get("movement")) != "watch":
                continue
            ok, _why = _creative_eligible(c)
            if not ok:
                continue
            traits = _creative_traits(c, evaluated_on)
            if not any(traits.values()):
                continue
            w = max(1, min(5, int(c.get("wow", 0) or 3)))
            creative_pool[w].append((_creative_score(c, traits), c))
            c["creative_traits"] = [k for k, v in traits.items() if v]
        for w in creative_pool:
            creative_pool[w].sort(key=lambda t: t[0], reverse=True)
        creative: list[dict[str, Any]] = []
        used_stories: set[tuple[str, str]] = {_story_key(c) for c in chosen}
        creative_used: Counter = Counter()
        # Coverage pass (shocks): every disruption type absent from the page and
        # grounded reserve keeps its best uncontradicted hypothesis in reserve, so
        # no type of possible shock is starved of a path to mature.
        if product == "shock":
            present = {v for c in chosen + grounded_reserve for k, v, _ in _diversity_keys(c) if k == "driver"}
            best_by_driver: dict[str, tuple[float, int, dict[str, Any]]] = {}
            for w, items in creative_pool.items():
                for score, c in items:
                    drv = next((v for k, v, _ in _diversity_keys(c) if k == "driver"), "")
                    if drv and drv not in present and (drv not in best_by_driver or score > best_by_driver[drv][0]):
                        best_by_driver[drv] = (score, w, c)
            for drv, (score, w, c) in sorted(best_by_driver.items(), key=lambda kv: kv[1][0], reverse=True):
                if len(creative) >= creative_quota:
                    break
                creative_pool[w] = [t for t in creative_pool[w] if t[1] is not c]
                used_stories.add(_story_key(c))
                for k, v, cap in _diversity_keys(c):
                    creative_used[(k, v)] += 1
                creative.append(c)
        while len(creative) < creative_quota and any(creative_pool.values()):
            progressed = False
            for w in CREATIVE_WOW_ORDER:
                if len(creative) >= creative_quota:
                    break
                for idx, (_score, c) in enumerate(creative_pool[w]):
                    key = _story_key(c)
                    if key in used_stories:
                        continue
                    # Variety in the creative reserve too, so every disruption type
                    # / topic keeps a path to mature (caps are one above page caps).
                    dkeys = [(k, v, cap + 1) for k, v, cap in _diversity_keys(c)]
                    if any(creative_used[(k, v)] >= cap for k, v, cap in dkeys):
                        continue
                    creative_pool[w].pop(idx)
                    used_stories.add(key)
                    for k, v, _cap in dkeys:
                        creative_used[(k, v)] += 1
                    creative.append(c)
                    progressed = True
                    break
            if not progressed:
                break
        for c in creative:
            c["creative_reserve"] = True
            c["movement"] = "reserve"
            c["stock_tier"] = "creative_reserve"
            c["reader_status_chip"] = "Worth holding in mind"
            c["publication_lock_reason"] = (
                "Creative reserve: relevant and not contradicted, but not yet provable ("
                + ", ".join(t.replace("_", " ") for t in c.get("creative_traits", []))
                + "). Held so it can mature instead of being filtered out."
            )
        for c in pool:
            if not c.get("creative_reserve"):
                c.pop("creative_traits", None)

        reserve = sum(1 for c in pool if clean(c.get("movement")) == "reserve")
        watch = sum(1 for c in pool if clean(c.get("movement")) == "watch")
        meta[product] = {
            "page_capacity": 15,
            "slots_per_wow": slots_per_wow,
            "display_cycle": [5, 4, 3, 2, 1] * 3,
            "hard_cap": True,
            "shown": len(chosen),
            "shown_by_wow": {str(w): len(by_wow[w]) for w in (5, 4, 3, 2, 1)},
            "reserve": reserve,
            "watch": watch,
            "developing": watch,
            "grounded_publishable": len(ready_ids),
            "total_active_stock": sum(1 for c in pool if clean(c.get("status")) not in {"killed", "dormant"}),
            "folded": folded,
            "borrowed_slots": borrowed,
            "reserve_grounded": len(grounded_reserve),
            "reserve_creative": len(creative),
            "reserve_target": RESERVE_TARGET,
            "reserve_by_wow": {str(w): sum(1 for c in pool if clean(c.get("movement")) == "reserve" and int(c.get("wow", 0) or 0) == w) for w in (5, 4, 3, 2, 1)},
            "creative_by_trait": {t: sum(1 for c in creative if t in c.get("creative_traits", [])) for t in ("distant", "cross_domain", "emerging", "weak_signal", "partially_grounded")},
            "shown_by_actual_wow": {str(w): sum(1 for c in chosen if int(c.get("wow", 0) or 0) == w) for w in (5, 4, 3, 2, 1)},
        }

    meta["page_guarantee"] = {
        "slots_per_wow": 3,
        "cycle": [5, 4, 3, 2, 1] * 3,
        "promotion_between_wow_buckets": False,
        "empty_slot_fill": "nearest_wow_with_grounded_reserve",
        "swap_margin": SHELF_SWAP_MARGIN,
        "rule": "New records update candidate reasoning; the shelf is re-decided each scan from recomputed maturity. No record takes a slot automatically.",
        "creative_reserve": "Reserve = grounded runners-up + a creative reserve of relevant, uncontradicted hypotheses (distant, cross-domain, emerging, weak-signal or partially grounded), at least 18 and topped up toward 45, rotated across wow levels with weight on surprise. They mature into page competition when grounded.",
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
        "future_shock_hypothesis": "future shock hypothesis",
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
        "ai.public_sector_capacity": "public-sector AI capacity",
        "critical_infrastructure.resilience": "critical-infrastructure resilience",
        "quantum.pilot_line": "the quantum pilot line",
        "research.system_capacity": "research-system capacity",
    }
    if obj in aliases:
        return aliases[obj]
    fam = _family_of(obj)
    if fam:
        return _FAMILY_LABELS.get(fam, fam.replace("_", " ")) + " as a whole"

    text = obj.replace(".", " ").replace("_", " ")
    return clean(text) or "European research and innovation"


def _reader_copy(grammar: str, product: str, raw: dict[str, Any], candidate: dict[str, Any]) -> tuple[str, str]:
    eps = [clean(x) for x in raw.get("endpoint_objects", []) if clean(x)] if isinstance(raw.get("endpoint_objects"), list) else []
    a = _friendly_object_label(eps[0] if eps else raw.get("object") or raw.get("capability_object") or raw.get("objective_object"))
    b = _friendly_object_label(eps[1] if len(eps) > 1 else raw.get("dependency_object") or raw.get("delivery_object"))
    records = int(candidate.get("primary_records", 0) or 0)
    sources = int(candidate.get("primary_sources", 0) or 0)

    if grammar == "named_continuity":
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
        # The title carries the substantive phenomenon.  Leave the summary empty so
        # the reader page supplies its object-specific plain-language explanation
        # instead of generic continuity metatext or source-count arithmetic.
        return title, ""

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
        return f"Funding for {a} is visible before a matching outcome measure is.", "The sources establish the objective and a delivery instrument. The material currently supporting this finding does not establish a corresponding outcome measure, so the Radar treats the measurement gap as an open inference rather than proof that no metric exists."
    if grammar == "stalled_proposal":
        return f"A proposal affecting {a} is ageing without a later decision.", "The proposal has remained below implementation for more than six months with no later status transition in the evidence base."
    if grammar == "conflicting_criteria":
        return f"{a[:1].upper()+a[1:]} could collide with {b}.", "Separate sources establish both requirements and a governance ambiguity around them. The collision itself is the Radar's inference: the same project or facility could receive different answers depending on which rule is applied first."
    if grammar == "future_shock_hypothesis":
        pressure = clean(raw.get("pressure_label")) or "an external disruption"
        asset = _friendly_object_label(raw.get("capability_object") or (eps[0] if eps else ""))
        lead = pressure[:1].upper() + pressure[1:]
        bridge = bool((candidate.get("role_semantic_checks") or {}).get("bridge_links_asset_and_pressure"))
        if bridge:
            summary = f"Sources separately establish the European capability, the external disruption mechanism and a direct link between them. The future disruption itself remains the Radar's scenario, not a claim made by any one source."
        else:
            summary = f"Sources separately establish the European capability and the external disruption mechanism. The claim that the disruption could reach {asset} is the Radar's future hypothesis, not a statement made by either source."
        pid = clean(raw.get("pressure_id")) or next((x.split(".", 1)[1] for x in eps if x.startswith("shock_pressure.")), "")
        return _shock_title(pid, lead, asset), summary
    if grammar == "dependency_pathway":
        checks = candidate.get("role_semantic_checks") if isinstance(candidate.get("role_semantic_checks"), dict) else {}
        route_visible = bool(checks.get("propagation_visible"))
        if product == "shock":
            summary = (
                "Sources establish the European capability, the dependency link and additional evidence along the propagation route. The sudden break and its future consequences remain the Radar's scenario, not a source claim."
                if route_visible
                else "Sources establish the European capability and its dependency. The claim that a sudden break could propagate through that dependency is the Radar's future scenario, not a statement made by any one source."
            )
            return f"A sudden break in {b} could propagate into {a}.", summary
        summary = (
            "Sources establish the European capability, the dependency link and evidence relevant to propagation or exposure. The future spread of disruption is the Radar's inference rather than a claim made by an individual source."
            if route_visible
            else "Sources establish the European capability and its dependency. The claim that a bottleneck could propagate into the capability is the Radar's inference rather than a statement made by an individual source."
        )
        return f"A bottleneck in {b} could propagate into {a}.", summary
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
        corroborated = int(candidate.get("direction_grounded_sources", sources) or 0) >= 2
        if product == "risk":
            if corroborated:
                verb = "is under sustained pressure" if direction == "contracts" else "is becoming more conditional" if direction == "becomes_conditional" else "is becoming more contested" if direction == "becomes_contested" else "shows a current constraint"
                summary = (
                    f"Independent sources document current {a} becoming more constrained." if direction == "contracts"
                    else f"Independent sources document current conditions around {a} becoming more conditional." if direction == "becomes_conditional"
                    else f"Independent sources document current contestation around {a}." if direction == "becomes_contested"
                    else f"Independent sources document a current constraint affecting {a}."
                )
            else:
                verb = "could come under sustained pressure" if direction == "contracts" else "could become more conditional" if direction == "becomes_conditional" else "could become more contested" if direction == "becomes_contested" else "could face a new constraint"
                summary = (
                    f"The source documents a current constraint on {a}; the risk is that the constraint persists or spreads." if direction == "contracts"
                    else f"The source documents current conditions on {a}; the risk is that access or action becomes more conditional." if direction == "becomes_conditional"
                    else f"The source documents current contestation around {a}; the risk is that the contestation widens or hardens." if direction == "becomes_contested"
                    else f"The source documents a current constraint affecting {a}; the risk is that it persists or spreads."
                )
            return f"{a[:1].upper()+a[1:]} {verb}.", summary
        action = "is expanding through a live European instrument"
        if mechanism in {"collaborates", "associates"}: action = "is widening through active agreements"
        elif mechanism in {"procures", "builds", "adds_capacity"}: action = "is expanding through active capacity-building"
        elif mechanism == "funds": action = "is expanding through new funding"
        elif mechanism == "prioritises": action = "is being backed by adopted priorities"
        elif mechanism == "launches": action = "is moving into operation through new instruments"
        elif mechanism == "coordinates": action = "is gaining an active coordination route"
        elif mechanism == "invests": action = "is expanding through new investment"
        elif mechanism == "supports": action = "is expanding through a live support instrument"
        if corroborated:
            summary = "Independent sources document constructive movement in the same direction, including a live or operating instrument. The broader opportunity shown here is the Radar's synthesis."
            title = f"{a[:1].upper()+a[1:]} {action}."
        else:
            summary = "A current source documents a live or operating instrument moving in this direction. The broader opportunity shown here is the Radar's synthesis rather than a claim made by that source."
            if mechanism in {"collaborates", "associates"}: title = f"Active agreements could widen {a}."
            elif mechanism in {"procures", "builds", "adds_capacity"}: title = f"Active capacity-building could expand {a}."
            elif mechanism == "funds": title = f"New funding could expand {a}."
            elif mechanism == "prioritises": title = f"Adopted priorities could strengthen {a}."
            elif mechanism == "launches": title = f"New instruments could move {a} further into operation."
            elif mechanism == "coordinates": title = f"Active coordination could strengthen {a}."
            elif mechanism == "invests": title = f"New investment could expand {a}."
            elif mechanism == "supports": title = f"A live support instrument could expand {a}."
            else: title = f"A live European instrument could expand {a}."
        return title, summary
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
    if grammar == "future_shock_hypothesis": return "The European asset and the outside disruption mechanism are source-evidenced; the causal bridge to a future shock remains explicitly Radar-owned unless a source establishes it directly."
    if grammar == "dependency_pathway" and product == "risk": return f"The source-evidenced dependency creates a plausible route by which a failure in {b} could reach {a}; the future propagation is the Radar's inference."
    if grammar == "dependency_pathway" and product == "shock": return f"The source-evidenced dependency creates a plausible route by which a sudden break in {b} could remove capability; the discontinuity itself remains a Radar scenario."
    if grammar == "latent_channel": return "The opportunity is leverage: connect pieces Europe already has instead of creating a new programme from zero."
    if grammar == "anchor_demand": return "Reliable European demand can help turn research and scale-up support into durable production, suppliers and technical capability."
    if grammar == "named_continuity": return "Persistence matters because a recurring issue is more likely to shape future choices than a one-scan spike."
    if grammar == "corroborated_claim" and product == "risk":
        direction = clean(raw.get("direction"))
        if direction == "becomes_contested": return f"If the documented contestation widens or hardens, it could create more friction around {a}."
        if direction == "becomes_conditional": return f"If the documented conditions tighten or spread, access to {a} could depend on more external approvals or requirements."
        if direction == "contracts": return f"If the documented constraint persists or spreads, it could reduce access to or capacity in {a}."
        return f"If the current constraint persists or spreads, it could narrow room to act around {a}."
    if grammar == "corroborated_claim" and product == "opportunity":
        mechanism = clean(raw.get("mechanism"))
        if mechanism in {"collaborates", "associates"}: return f"If the active agreement is sustained, it could widen European access, networks or participation around {a}."
        if mechanism in {"procures", "builds", "adds_capacity"}: return f"If the current build-out reaches users, it could add usable European capacity in {a}."
        if mechanism == "funds": return f"If the funded activity converts into delivery, it could strengthen European capability in {a}."
        return f"If the live instrument scales or delivers as intended, it could strengthen European capability in {a}."
    return ""

def adapt_candidate(c: dict[str, Any], nodes: Iterable[dict[str, Any]], *, vocab: dict[str, Any] | None = None, evaluated_on: dt.date | None = None) -> dict[str, Any]:
    nodes = list(nodes)
    if _family_of(c.get("object")):
        _register_family(c.get("object"), c.get("family_members") or [])
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

    # Provisional claims remain useful discovery scaffolding, but Deep Scan/backfill
    # claims are the authoritative reasoning layer.  Keep explicit provisional
    # rows as context so the hypothesis survives in stock without presenting them
    # to readers as established source evidence.
    provisional_support = [
        ref for ref in support
        if clean(ref.get("claim_origin")) == "provisional" or clean(ref.get("claim_id")).startswith("c:provisional:")
    ]
    if provisional_support:
        provisional_ids = {clean(ref.get("claim_id")) for ref in provisional_support}
        support = [ref for ref in support if clean(ref.get("claim_id")) not in provisional_ids]
        context.extend(dict(
            ref,
            role="context",
            evidence_contribution="Related scanner context awaiting an authoritative structured claim.",
        ) for ref in provisional_support)

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
        if not support:
            # Creative-reserve bridge: the reviewed structured directions show both
            # pulls, but the wording does not yet make a side reader-visible.  Keep
            # those records as labelled context so the tension can be held and can
            # mature, without presenting it as established trend evidence.
            pulls = [
                n for n in nodes
                if n.get("_primary") and clean(n.get("era")) == "current"
                and clean(n.get("origin")) in _REVIEWED_ORIGINS
                and _object_matches(clean(c.get("object")), n)
                and clean(n.get("direction")) in {"expands", "contracts", "becomes_conditional", "becomes_contested"}
            ]
            pulls.sort(key=lambda n: float(n.get("merit", 0) or 0), reverse=True)
            rows = _support_rows({"claim_ids": [clean(n.get("claim_id")) for n in pulls[:8] if clean(n.get("claim_id"))]}, node_by_claim)
            context.extend(dict(
                r,
                role="context",
                claim_primary=False,
                evidence_contribution="Structured pull on this object; the wording does not yet make the side reader-visible.",
            ) for r in rows)

    topic = " × ".join(clean(x) for x in c.get("endpoint_objects", []) if clean(x)) if isinstance(c.get("endpoint_objects"), list) else ""
    topic = topic or clean(c.get("object") or c.get("cluster") or c.get("capability_object") or c.get("objective_object") or c.get("delivery_object") or c.get("grammar_id"))
    if trend:
        topic = _trend_scope_label(clean(trend.get("trend_scope")), clean(trend.get("trend_balance", {}).get("object_key")))
    grounded_direction_sources: set[str] = set()
    grounded_direction_records: set[str] = set()
    grounded_direction_refs: list[dict[str, Any]] = []
    contextual_direction_refs: list[dict[str, Any]] = []
    if grammar == "corroborated_claim":
        direction = clean(c.get("direction"))
        for ref in support:
            cid = clean(ref.get("claim_id"))
            node = node_by_claim.get(cid)
            if not node or not _direction_is_reader_grounded(node, direction):
                contextual_direction_refs.append(dict(
                    ref,
                    role="context",
                    evidence_contribution="Provides related context but does not establish the direction used in the finding.",
                ))
                continue
            grounded_direction_refs.append(ref)
            src = clean(ref.get("source")).lower()
            rec = clean(ref.get("identity"))
            if src:
                grounded_direction_sources.add(src)
            if rec:
                grounded_direction_records.add(rec)
        # Do not let related-but-nondirectional records appear under the public
        # heading “What the sources state”.  They remain available as explicitly
        # labelled context, while support contains only statements that actually
        # anchor the on-card direction.
        support = grounded_direction_refs
        context.extend(contextual_direction_refs)

    # For ongoing phenomena, the controlled object may have been assigned through
    # structured metadata even when a particular source statement does not visibly
    # discuss that object.  Such rows stay available as context but cannot appear
    # under the reader-facing source-evidence heading.
    continuity_counts: dict[str, int] = {}
    continuity_history: list[dict[str, Any]] = []
    if grammar == "named_continuity":
        target = clean(c.get("object"))
        direct_current: list[dict[str, Any]] = []
        contextual_current: list[dict[str, Any]] = []
        for ref in support:
            if _ref_grounds_object(target, ref):
                direct_current.append(ref)
            else:
                contextual_current.append(dict(
                    ref,
                    role="context",
                    evidence_contribution=f"Related context; the source statement does not directly establish recurrence of {_friendly_object_label(target)}.",
                ))
        support = direct_current
        context.extend(contextual_current)
        continuity_counts = _continuity_visible_counts(target, nodes)
        continuity_history = [
            dict(
                ref,
                role="historical_context",
                evidence_contribution=f"Historical context establishing that {_friendly_object_label(target)} was already present in the earlier period.",
            )
            for ref in context
            if clean(ref.get("strand")) == "H"
            and _ref_grounds_object(target, ref)
        ]

    # Level-5 role metadata is intentionally permissive during candidate formation.
    # Before anything is counted as public source evidence, demote rows whose visible
    # statements do not actually support the role assigned to them.
    support, role_context = _filter_reader_role_support(grammar, c, support)
    if role_context:
        context.extend(role_context)

    # R-09 invariant: anything filed under `context` is not primary support.
    # Rows demoted above (provisional claims, non-directional corroboration,
    # ungrounded continuity/role rows) were copied from primary support and
    # still carried claim_primary=True, so a context row could masquerade as
    # primary evidence. Normalise every context row; keep the original flag
    # for audit.
    context = [
        dict(ref, claim_primary=False, demoted_from_primary=True)
        if bool(ref.get("claim_primary")) else dict(ref, claim_primary=False)
        for ref in context
    ]

    sources = {clean(x.get("source")).lower() for x in support if clean(x.get("source"))}
    records = {clean(x.get("identity")) for x in support if clean(x.get("identity"))}
    shock_driver_grounded_sources: set[str] = set()
    shock_driver_grounded_records: set[str] = set()
    shock_driver_alignment = True
    if grammar == "future_shock_hypothesis":
        pressure_id = clean(c.get("pressure_id"))
        for ref in support:
            if clean(ref.get("role")) != "external_driver":
                continue
            if not _shock_driver_is_reader_grounded(pressure_id, ref.get("source_statement")):
                continue
            src = clean(ref.get("source")).lower()
            rec = clean(ref.get("identity"))
            if src:
                shock_driver_grounded_sources.add(src)
            if rec:
                shock_driver_grounded_records.add(rec)
        shock_driver_alignment = len(shock_driver_grounded_records) >= 1

    role_semantic_alignment, role_semantic_reason, role_semantic_checks = _reader_visible_role_semantics(
        grammar, product, c, support
    )
    semantic_alignment = (
        (grammar != "corroborated_claim" or len(grounded_direction_sources) >= 1)
        and (grammar != "future_shock_hypothesis" or shock_driver_alignment)
    )
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
    elif grammar == "future_shock_hypothesis" and not shock_driver_alignment:
        lock_reason = "The scenario remains in stock, but the displayed external-driver statement does not yet evidence the named disruption mechanism strongly enough for publication."
    elif grammar == "corroborated_claim":
        if not semantic_alignment:
            lock_reason = "The candidate is retained in stock, but the reader-visible source statement does not support the structured direction strongly enough for publication."
        elif len(grounded_direction_sources) >= 2:
            lock_reason = "Independent source statements corroborate the current direction; the finding awaits shelf selection."
        else:
            lock_reason = "A single source statement anchors the current direction; the future implication remains a Radar inference."
    elif structural_verified:
        lock_reason = "Structural candidate is verified by its authoritative graph test and is waiting for page selection."
    else:
        lock_reason = "Level-5 selection requires an executed candidate-specific falsifier plus wow/oddity/selection gates."

    role_floor = c.get("floor_ok")
    if role_floor is None and roles:
        vals = [float(snap.get("strength", 1.0) or 0.0) for snap in roles.values() if isinstance(snap, dict)]
        role_floor = all(v >= 0.40 for v in vals) if vals else True
    if role_floor is None:
        role_floor = True

    out = {
        "id": _candidate_id(c),
        "grammar_id": grammar,
        "level": level,
        "product": product,
        "inferential_distance": level,
        "topic_key": _candidate_key(c),
        "topic_label": (f"{topic} — evidence-anchored future hypothesis" if grammar == "corroborated_claim" and len(grounded_direction_sources) < 2 else _candidate_topic_label(grammar, topic)),
        # Preserve the semantic claim fields separately from the candidate lifecycle
        # status.  Reader surfaces need these to describe Level-2 corroborated
        # findings without falling back to generic wording.
        "object": clean(c.get("object")),
        "family_members": list(c.get("family_members") or []),
        "mechanism": clean(c.get("mechanism")),
        "direction": clean(c.get("direction")),
        "claim_status": clean(c.get("status")),
        "product_basis": (
            "shock_driver_statement_mismatch" if grammar == "future_shock_hypothesis" and not shock_driver_alignment
            else "source_statement_direction_mismatch" if grammar == "corroborated_claim" and not semantic_alignment
            else "single_source_future_anchor" if grammar == "corroborated_claim" and len(grounded_direction_sources) < 2
            else clean(c.get("product_basis"))
        ),
        "shock_driver": bool(c.get("shock_driver")),
        "shock_driver_basis": clean(c.get("shock_driver_basis")),
        "shock_driver_semantic_alignment": bool(shock_driver_alignment),
        "shock_driver_grounded_records": len(shock_driver_grounded_records),
        "shock_driver_grounded_sources": len(shock_driver_grounded_sources),
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
        "evidence_semantics": (
            "shock_driver_statement_mismatch" if grammar == "future_shock_hypothesis" and not shock_driver_alignment
            else "source_statement_direction_mismatch" if grammar == "corroborated_claim" and not semantic_alignment
            else "corroborated" if grammar == "corroborated_claim" and len(grounded_direction_sources) >= 2
            else "single_source_anchor" if grammar == "corroborated_claim"
            else "synthesis"
        ),
        "evidence_semantic_alignment": bool(semantic_alignment),
        "role_semantic_alignment": bool(role_semantic_alignment),
        "role_semantic_reason": role_semantic_reason,
        "role_semantic_checks": role_semantic_checks,
        "direction_grounded_records": len(grounded_direction_records),
        "direction_grounded_sources": len(grounded_direction_sources),
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
        "role_strength_floor_passes": bool(role_floor),
    }
    if grammar == "named_continuity":
        out.update({
            "current_record_count": int(continuity_counts.get("current_record_count", 0) or 0),
            "current_source_count": int(continuity_counts.get("current_source_count", 0) or 0),
            "historical_record_count": int(continuity_counts.get("historical_record_count", 0) or 0),
            "historical_source_count": int(continuity_counts.get("historical_source_count", 0) or 0),
            "continuity_history": continuity_history,
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
    if grammar == "future_shock_hypothesis":
        out["reader_consequence"] = _shock_consequence(c, out)
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
    # Register every family/cluster membership before any candidate is adapted, so
    # grounding never depends on the order candidates happen to be processed in.
    _FAMILY_MEMBERS.clear()
    for _items in groups.values():
        for _raw in _items if isinstance(_items, list) else []:
            if isinstance(_raw, dict) and _family_of(_raw.get("object")):
                _register_family(_raw.get("object"), _raw.get("family_members") or [])
    for _prev in previous_state.get("candidates", []) if isinstance(previous_state.get("candidates"), list) else []:
        if isinstance(_prev, dict) and _family_of(_prev.get("object")) and clean(_prev.get("object")) not in _FAMILY_MEMBERS:
            _register_family(_prev.get("object"), _prev.get("family_members") or [])
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
        "level5_dependency_pathway", "future_shock_hypothesis", "level4_5_conflicting_criteria", "level5_latent_channel",
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
        "publication_policy": "Stage 7 claim-native selection treats the reasoning layer as a future-hypothesis corpus. Candidate formation is broad; missing roles, thin evidence and unrun counter-evidence tests lower maturity rather than forbidding the hypothesis. Grounded candidates compete only within their wow 1-5 bucket. Each product reserves three public slots per wow level (15 total), displayed 5-4-3-2-1 three times; surplus grounded findings remain reserve and weaker hypotheses remain developing.",
        "lifecycle_policy": "Claim-native stock persists as page/reserve/developing tiers. Evidence is recomputed each scan; candidates can strengthen, weaken or move between tiers as new evidence arrives. Counter-evidence and falsifier results affect maturity and can kill a contradicted hypothesis, but an unrun challenge is not a ban on future-facing reasoning.",
        "candidate_search_policy": "Missing-role and falsifier queries remain ordinary scanner discovery inputs and receive no admission waiver.",
        "publications": publications,
        "scenarios_2035": _build_2035(publications, candidates, now),
        "candidates": candidates,
    }


def _build_2035(publications: dict[str, Any], candidates: list[dict[str, Any]], now: str) -> dict[str, Any]:
    """The 2035 page is presentation built on published findings; a failure there
    must never block the scan."""
    try:
        try:
            from scripts.scenarios_2035 import build_scenarios_2035
        except ImportError:  # pragma: no cover
            from scenarios_2035 import build_scenarios_2035  # type: ignore
        return build_scenarios_2035(publications, candidates, now)
    except Exception as exc:  # pragma: no cover - defensive
        return {"horizon": 2035, "evaluated_at": now, "scenarios": [], "error": f"{type(exc).__name__}: {exc}"}

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
    deps = [x for group in ("level5_dependency_pathway", "future_shock_hypothesis") for x in detected["groups"].get(group, []) if isinstance(x, dict) and clean(x.get("product")) == "shock"]
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
    """Use scanner feedback to mature the broad hypothesis corpus.

    Feedback never changes A/B/C admission.  It simply asks ordinary discovery for
    the missing connection, second source or counter-evidence that would move a
    developing hypothesis upward (or kill it).  Product round-robin prevents one
    crowded family from consuming the whole budget.
    """
    if not isinstance(state, dict):
        return []
    cap = max(0, int(limit or 0))
    if cap <= 0:
        return []
    candidates = [x for x in state.get("candidates", []) if isinstance(x, dict) and x.get("claim_native")]
    if not candidates:
        candidates = [x for x in state.get("claim_candidates", []) if isinstance(x, dict) and x.get("claim_native")]
    candidates = [c for c in candidates if clean(c.get("movement")) not in {"killed", "dormant"} and clean(c.get("status")) not in {"killed", "dormant"}]
    if not candidates:
        return []

    product_order = ("opportunity", "risk", "shock", "trend", "continuity")
    def priority(c: dict[str, Any]) -> tuple[int, int, int, int, int]:
        missing = len(c.get("missing_roles", []) if isinstance(c.get("missing_roles"), list) else [])
        maturity = int(c.get("maturity_score", c.get("score", 0)) or 0)
        return (
            1 if clean(c.get("stock_tier")) == "watch" else 0,
            2 - min(2, missing),
            int(c.get("wow", 0) or 0),
            maturity,
            int(c.get("primary_sources", 0) or 0),
        )

    by_product: dict[str, list[dict[str, Any]]] = {p: [] for p in product_order}
    for c in sorted(candidates, key=priority, reverse=True):
        by_product.setdefault(clean(c.get("product")) or "continuity", []).append(c)

    ordered: list[dict[str, Any]] = []
    depth = 0
    while len(ordered) < 25:
        added = False
        for product in product_order:
            bucket = by_product.get(product, [])
            if depth < len(bucket):
                ordered.append(bucket[depth]); added = True
                if len(ordered) >= 25:
                    break
        if not added:
            break
        depth += 1

    out: list[str] = []
    # Pass 1: one missing-link query per candidate.  This maximises corpus breadth.
    for c in ordered:
        qs = [clean(q) for q in c.get("support_queries", []) if clean(q)]
        if qs and qs[0] not in out:
            out.append(qs[0])
            if len(out) >= cap:
                return out[:cap]

    # Pass 2: one challenge/counter-evidence query per candidate.  Challenges refine
    # scores and can kill a hypothesis, but an unrun challenge is not a publication ban.
    for c in ordered:
        qs = [clean(q) for q in c.get("falsifier_queries", []) if clean(q)]
        if qs and qs[0] not in out:
            out.append(qs[0])
            if len(out) >= cap:
                return out[:cap]

    # Pass 3+: deeper variants only after broad candidate coverage.
    max_depth = max((max(len(c.get("support_queries") or []), len(c.get("falsifier_queries") or [])) for c in ordered), default=0)
    for qi in range(1, max_depth):
        for c in ordered:
            for key in ("support_queries", "falsifier_queries"):
                qs = [clean(q) for q in c.get(key, []) if clean(q)]
                if qi < len(qs) and qs[qi] not in out:
                    out.append(qs[qi])
                    if len(out) >= cap:
                        return out[:cap]
    return out[:cap]

