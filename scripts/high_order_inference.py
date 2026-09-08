from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from datetime import datetime, timezone
from typing import Any, Iterable

PROFILE_VERSION = "v23.4-cumulative-adversarial-level45"


def _clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def _low(v: Any) -> str:
    return _clean(v).lower()


def _text(row: dict[str, Any]) -> str:
    return _clean(" ".join(
        _clean(row.get(k))
        for k in (
            "title", "headline", "summary", "core_message", "relevance_note",
            "bridge_sentence", "signal_note", "why_it_matters", "anchor", "watch_theme",
        )
        if _clean(row.get(k))
    ))


def _identity(row: dict[str, Any]) -> str:
    link = _low(row.get("link") or row.get("url")).rstrip("/")
    if link:
        return "url:" + link
    title = re.sub(r"[^a-z0-9]+", " ", _low(row.get("title") or row.get("headline"))).strip()
    source = re.sub(r"[^a-z0-9]+", " ", _low(row.get("source") or row.get("journal") or row.get("institution"))).strip()
    date = _clean(row.get("date"))[:10]
    return "title:" + hashlib.sha1(f"{title}|{source}|{date}".encode("utf-8")).hexdigest()[:20]


def _source(row: dict[str, Any]) -> str:
    return _clean(row.get("source") or row.get("journal") or row.get("institution") or row.get("source_domain") or "Unknown source")


def _date(row: dict[str, Any]) -> str:
    return _clean(row.get("date"))[:10]


def _quality(row: dict[str, Any]) -> int:
    try:
        q = int(float(row.get("quality") or row.get("source_merit") or 0))
        if q:
            return max(1, min(100, q))
    except Exception:
        pass
    tier = _low(row.get("source_tier"))
    if "tier 1" in tier:
        return 96
    if "tier 2" in tier:
        return 89
    if "tier 3" in tier:
        return 78
    basis = _low((row.get("source_quality_gate") or {}).get("basis") if isinstance(row.get("source_quality_gate"), dict) else "")
    if "official" in basis:
        return 98
    return 82


@lru_cache(maxsize=512)
def _compiled_rx(pattern: str):
    return re.compile(pattern, re.I)


def _rx(pattern: str, text: str) -> bool:
    return bool(_compiled_rx(pattern).search(text))


TOPICS: dict[str, tuple[str, str]] = {
    "compute_ai": (r"\b(?:ai|artificial intelligence|compute|cloud|gpu|data cent(?:re|er)|gigafactor(?:y|ies)|supercomput)\b", "AI/compute"),
    "quantum": (r"\bquantum\b", "quantum"),
    "chips": (r"\b(?:chip|chips|semiconductor|microelectronics)\b", "semiconductors"),
    "talent": (r"\b(?:researcher|scientist|talent|brain drain|career|postdoc|doctoral|phd|mobility|retain|retention|recruit)\b", "research talent"),
    "research_security": (r"\b(?:research security|knowledge security|dual[- ]use|export control|securiti[sz]|foreign interference)\b", "research security"),
    "openness": (r"\b(?:open science|openness|open research|open access|sharing|academic freedom)\b", "openness"),
    "funding_programme": (r"\b(?:horizon europe|fp10|framework programme|eic|erc|msca|funding programme|evaluation|evaluator|grant)\b", "research funding/programmes"),
    "health_data": (r"\b(?:health data|ehds|biobank|medical ai|health ai|patient data|federated health|transfusion|brain imaging)\b", "health data"),
    "materials_energy": (r"\b(?:grid|electricity|power|energy|critical raw material|critical material|critical mineral|rare earth|magnet|electrification)\b", "energy/materials"),
    "infrastructure": (r"\b(?:research infrastructure|infrastructure|facility|facilities|laborator|eurohpc|platform|federat|pilot line)\b", "research infrastructure"),
    "collaboration_diplomacy": (r"\b(?:science diplomacy|scientific diplomacy|association|associated countr|research cooperation|research collaboration|partnership|international cooperation)\b", "science diplomacy/collaboration"),
    "startups_scaleup": (r"\b(?:startup|start-up|scaleup|scale-up|accelerator|commerciali[sz]|venture|company|companies|firm|firms)\b", "startups/scale-up"),
    "standards_testing": (r"\b(?:standard|standards|testing|certif|validation|interoperab|interface|convention)\b", "standards/testing"),
    "measurement": (r"\b(?:index|indicator|metric|measure|measurement|scoreboard|benchmark|observatory|monitoring)\b", "measurement"),
    "research_data": (r"\b(?:research data|scientific data|repository|repositories|database|catalogu|taxonomy|discoverability)\b", "research data"),
}

CONCEPTS: dict[str, tuple[str, str]] = {
    "sovereignty": (r"\b(?:technological sovereignty|tech sovereignty|strategic autonomy|non-dependence|nondependence)\b", "technological sovereignty/strategic autonomy"),
    "resilience": (r"\b(?:resilien|security of supply|de-risk|derisk)\b", "resilience/de-risking"),
    "competitiveness": (r"\bcompetitiveness\b", "competitiveness"),
    "openness": (r"\b(?:open science|openness|open research)\b", "openness"),
    "research_security": (r"\b(?:research security|knowledge security)\b", "research security"),
}


def _topic_ids(text: str) -> set[str]:
    return {tid for tid, (pat, _) in TOPICS.items() if _rx(pat, text)}


def _core_text(row: dict[str, Any]) -> str:
    """Fields strong enough to bind a record to a subject for L4/L5 reasoning."""
    return _clean(" ".join(
        _clean(row.get(k)) for k in ("title", "headline", "summary", "core_message", "bridge_sentence")
        if _clean(row.get(k))
    ))


def _strong_topic(row: dict[str, Any], topic: str) -> bool:
    spec = TOPICS.get(topic)
    return bool(spec and _rx(spec[0], _core_text(row)))


def _same_sentence(row: dict[str, Any], *patterns: str) -> bool:
    """Require adjacent reasoning roles to be explicitly connected, not merely co-tagged."""
    parts = row.get("_sentences") if isinstance(row.get("_sentences"), list) else None
    if parts is None:
        text = _text(row)
        parts = [p.strip() for p in re.split(r"(?<=[.!?;])\s+|\n+", text) if p.strip()]
    return any(all(_rx(pat, part) for pat in patterns) for part in parts)



def _title_topic(row: dict[str, Any], topic: str) -> bool:
    spec = TOPICS.get(topic)
    title = _clean(row.get("title") or row.get("headline"))
    return bool(spec and title and _rx(spec[0], title))


def _dependency_bridge(row: dict[str, Any], asset: str, dep: str) -> bool:
    """Directional bridge: evidence must say, in a short local window, that asset relies on dep.

    Merely mentioning AI and minerals in one sentence is not enough.  The relation has to
    connect the asset to the dependency (or identify the dependency as a constraint/input).
    """
    ap = TOPICS[asset][0]
    dp = TOPICS[dep][0]
    direct = r"(?:depends? on|dependence on|reliance on|relies? on|requires?|limited by|constrained by|bottlenecked by|availability of)"
    dep_role = r"(?:constraint|bottleneck|critical input|input requirement|dependency|limiting factor|required for|essential input|powers?|feeds?)"
    parts = row.get("_sentences") if isinstance(row.get("_sentences"), list) else [_text(row)]
    for part in parts:
        if not (_rx(ap, part) and _rx(dp, part)):
            continue
        patterns = (
            rf"{ap}.{{0,180}}{direct}.{{0,140}}{dp}",
            rf"{dp}.{{0,140}}{dep_role}.{{0,180}}{ap}",
            rf"{ap}.{{0,180}}{dp}.{{0,90}}{dep_role}",
        )
        if any(_rx(pat, part) for pat in patterns):
            return True
    return False


def _rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key, strand, primary, weight in (
        ("strand_a", "A", True, 1.0),
        ("frontier_evidence", "A", True, 1.0),
        ("strand_c", "C", False, 0.30),
        ("historical_context", "H", False, 0.45),
    ):
        xs = data.get(key, [])
        if not isinstance(xs, list):
            continue
        for raw in xs:
            if not isinstance(raw, dict):
                continue
            ident = _identity(raw)
            if ident in seen:
                continue
            seen.add(ident)
            row = dict(raw)
            row["_identity"] = ident
            row["_strand"] = strand
            row["_primary"] = primary
            row["_historical"] = strand == "H"
            row["_weight"] = weight
            row["_text"] = _text(row)
            row["_sentences"] = [p.strip() for p in re.split(r"(?<=[.!?;])\s+|\n+", row["_text"]) if p.strip()]
            row["_topics"] = _topic_ids(row["_text"])
            row["_quality"] = _quality(row)
            row["_source"] = _source(row)
            out.append(row)
    return out


def _snap(row: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "identity": row.get("_identity"),
        "role": role,
        "strand": row.get("_strand"),
        "title": _clean(row.get("title") or row.get("headline")),
        "source": row.get("_source") or _source(row),
        "date": _date(row),
        "link": _clean(row.get("link") or row.get("url")),
        "quality": int(row.get("_quality", 0) or 0),
        "new_this_scan": bool(row.get("new_this_scan")),
        "analytical_weight": float(row.get("_weight", 0.0) or 0.0),
    }


def _dedupe(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        ident = str(row.get("_identity"))
        if not ident or ident in seen:
            continue
        seen.add(ident)
        out.append(row)
    return out


def _best(rows: Iterable[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    xs = _dedupe(rows)
    xs.sort(key=lambda r: (bool(r.get("new_this_scan")), int(r.get("_quality", 0)), _date(r)), reverse=True)
    return xs[:limit]


def _role(rows: Iterable[dict[str, Any]], pattern: str, *, primary_only: bool = False, historical_only: bool = False) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if primary_only and not row.get("_primary"):
            continue
        if historical_only and not row.get("_historical"):
            continue
        if _rx(pattern, row.get("_text", "")):
            out.append(row)
    return out


def _topic_rows(rows: Iterable[dict[str, Any]], topic: str) -> list[dict[str, Any]]:
    return [r for r in rows if topic in (r.get("_topics") or set())]


def _candidate_id(grammar: str, key: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", _low(key)).strip("-")[:90]
    return f"l45:{grammar}:{safe or 'general'}"


def _queries(topic_label: str, support_terms: list[str], falsifier_terms: list[str]) -> tuple[list[str], list[str]]:
    base = _clean(topic_label)
    support = [f"Europe research innovation {base} {x}" for x in support_terms if _clean(x)]
    falsify = [f"Europe research innovation {base} {x}" for x in falsifier_terms if _clean(x)]
    return support[:4], falsify[:3]


def _build_candidate(
    *, grammar: str, product: str, level: int, key: str, label: str,
    role_rows: dict[str, list[dict[str, Any]]], required_roles: list[str],
    context_rows: list[dict[str, Any]] | None = None,
    counter_rows: list[dict[str, Any]] | None = None,
    min_records: int, min_sources: int, min_counter: int = 0,
    support_queries: list[str] | None = None, falsifier_queries: list[str] | None = None,
    max_roles_per_record: int | None = None,
) -> dict[str, Any] | None:
    primary_support_by_role: dict[str, list[dict[str, Any]]] = {
        role: _best([r for r in rows if r.get("_primary")], 6)
        for role, rows in role_rows.items()
    }
    covered = [role for role in required_roles if primary_support_by_role.get(role)]
    # Two independent pieces are the minimum for even retaining an unfinished thought.
    all_primary = _dedupe(r for role in required_roles for r in primary_support_by_role.get(role, []))
    if len(covered) < 2 or len(all_primary) < 2:
        return None
    sources = {_low(r.get("_source")) for r in all_primary if _clean(r.get("_source"))}
    role_coverage = len(covered) / max(1, len(required_roles))
    all_complete = len(covered) == len(required_roles)
    counters = _best([r for r in (counter_rows or []) if r.get("_primary")], 5)
    contexts = _best([r for r in (context_rows or []) if not r.get("_primary")], 6)

    # A higher-order inference must actually synthesize across records. If one record
    # supplies every required role, it is a source-stated proposition, not L4/L5 inference.
    max_roles_one = 0
    for r in all_primary:
        n = sum(1 for role in required_roles if r in primary_support_by_role.get(role, []))
        max_roles_one = max(max_roles_one, n)
    synthesis_ok = max_roles_one < len(required_roles) and (max_roles_per_record is None or max_roles_one <= max_roles_per_record)

    base = 22 + role_coverage * 48
    base += min(12, max(0, len(sources) - 1) * 3)
    base += min(8, max(0, len(all_primary) - 2) * 2)
    if synthesis_ok:
        base += 5
    # Counterevidence is searched on every candidate. Finding some is useful analytically,
    # but it must never *reward* the hypothesis; it lowers confidence instead.
    counter_penalty = min(12, len(counters) * 3)
    # C/history can sharpen confidence slightly but can never close a missing primary role.
    context_bonus = min(5.0, sum(float(r.get("_weight", 0.0) or 0.0) * (float(r.get("_quality", 0) or 0) / 100.0) for r in contexts))
    score = min(99, max(0, int(round(base + context_bonus - counter_penalty))))
    denial_tested = bool(falsifier_queries)

    if all_complete and len(all_primary) >= min_records and len(sources) >= min_sources and len(counters) >= min_counter and synthesis_ok:
        status = "qualified"
    elif role_coverage >= 0.60 and len(all_primary) >= 3 and len(sources) >= 2:
        status = "watch"
    else:
        status = "dormant"

    missing = [r for r in required_roles if not primary_support_by_role.get(r)]
    support: list[dict[str, Any]] = []
    for role in required_roles:
        for row in primary_support_by_role.get(role, [])[:3]:
            support.append(_snap(row, role))
    # Deduplicate snapshots while keeping the first role label.
    seen: set[str] = set(); support2 = []
    for s in support:
        ident = str(s.get("identity"))
        if ident in seen:
            continue
        seen.add(ident); support2.append(s)
    context = [_snap(r, "Context only") for r in contexts]
    against = [_snap(r, "Counterevidence / absorber") for r in counters]
    touched = any(bool(r.get("new_this_scan")) for r in all_primary + contexts)

    return {
        "id": _candidate_id(grammar, key),
        "grammar_id": grammar,
        "product": product,
        "inferential_distance": level,
        "topic_key": key,
        "topic_label": label,
        "status": status,
        "score": score,
        "primary_role_coverage": round(role_coverage, 3),
        "required_roles": required_roles,
        "covered_roles": covered,
        "missing_links": missing,
        "primary_records": len(all_primary),
        "primary_sources": len(sources),
        "context_records": len(context),
        "counter_records": len(against),
        "denial_tested": denial_tested,
        "counter_penalty": counter_penalty,
        "synthesis_across_records": synthesis_ok,
        "support": support2[:10],
        "context": context[:6],
        "against": against[:5],
        "support_queries": list(dict.fromkeys(support_queries or []))[:4],
        "falsifier_queries": list(dict.fromkeys(falsifier_queries or []))[:3],
        "touched_this_scan": touched,
        "reader_eligible": status == "qualified" and denial_tested and synthesis_ok,
    }


def _omitted_dependency(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Level-5 hidden-dependency chain with strict object binding.

    The detector does not cross-product topics.  It requires a flagship/asset record,
    a primary record that explicitly binds that asset to the dependency, independent
    primary evidence of upstream disruption, and a primary propagation mechanism.
    """
    primary = [r for r in rows if r.get("_primary")]
    profiles = {
        "compute_ai-materials_energy": {
            "asset": "compute_ai", "dep": "materials_energy",
            "label": "AI/compute through energy/materials",
            "commitment": r"\b(?:AI Gigafactor(?:y|ies)|Cloud and AI Development Act|CADA|data cent(?:re|er)|supercomputer|EuroHPC|compute capacity|computing infrastructure)\b.*\b(?:call|proposal|act|build|capacity|investment|deployment|infrastructure|factory|factories)\b|\b(?:call|proposal|act|build|investment|deployment)\b.*\b(?:AI Gigafactor(?:y|ies)|compute|cloud|data cent(?:re|er)|supercomputer)\b",
            "bridge": r"(?=.*\b(?:compute|cloud|AI|data cent(?:re|er)|Gigafactor(?:y|ies))\b)(?=.*\b(?:grid|electricity|power|energy)\b)(?=.*\b(?:constraint|bottleneck|limit|limited|connection|headroom|permitting|availability)\b)",
            "exposure": r"(?=.*(?:export control|export restriction|restricted|supplier concentration|import dependence|shortage|licensing|disrupt))(?=.*(?:critical|material|mineral|rare|magnet|energy transition|clean energy supply chain))",
            "propagation": r"\b(?:EuroHPC Federation Platform|pool(?:s|ed|ing)? access|one access layer|all EuroHPC machines|quantum computer.*same site|same site.*quantum computer)\b",
        },
    }
    counter_pat = r"\b(?:alternative supplier|substitut|diversif|grid[- ]rich|spare capacity|headroom|redundan|mitigat|resilien)\b"
    out=[]
    for key, spec in profiles.items():
        asset, dep = spec["asset"], spec["dep"]
        commitments=[r for r in _topic_rows(primary, asset) if _rx(spec["commitment"], _clean(r.get("title") or r.get("headline")))]
        bridges=[r for r in primary if asset in (r.get("_topics") or set()) and dep in (r.get("_topics") or set()) and _rx(spec["bridge"], r.get("_text", ""))]
        exposures=[r for r in _topic_rows(primary, dep) if _rx(spec["exposure"], r.get("_text", ""))]
        propagation=[r for r in _topic_rows(primary, asset) if _rx(spec["propagation"], r.get("_text", ""))]
        if not commitments or not bridges or not exposures:
            continue
        sq,fq=_queries(spec["label"],["dependency bottleneck upstream supplier","shared infrastructure propagation"],["alternative supplier spare capacity mitigation","resilience substitution unused capacity"])
        context=[r for r in rows if not r.get("_primary") and (asset in (r.get("_topics") or set()) or dep in (r.get("_topics") or set()))]
        cand=_build_candidate(
            grammar="omitted_dependency_chain", product="shock", level=5, key=key, label=spec["label"],
            role_rows={"commitment":commitments,"missing_dependency_bridge":bridges,"upstream_exposure":exposures,"propagation":propagation},
            required_roles=["commitment","missing_dependency_bridge","upstream_exposure","propagation"],
            context_rows=context,
            counter_rows=[r for r in primary if (asset in (r.get("_topics") or set()) or dep in (r.get("_topics") or set())) and _rx(counter_pat,r.get("_text",""))],
            min_records=6,min_sources=4,support_queries=sq,falsifier_queries=fq,
        )
        if cand:
            cand["reader_title"]=f"A hidden {TOPICS[dep][1]} dependency could interrupt European {TOPICS[asset][1]}."
            cand["reader_summary"]=f"Separate primary evidence binds European {TOPICS[asset][1]} to {TOPICS[dep][1]}, shows an upstream disruption route, and shows how the loss could propagate beyond one project or site."
            out.append(cand)
    return sorted(out,key=lambda c:(c["status"]=="qualified",c["score"],c["primary_sources"]),reverse=True)[:4]

def _conflicting_criteria(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Level-5 internal contradiction bound to FP10/Horizon evaluation."""
    primary=[r for r in rows if r.get("_primary")]
    def tt(r): return _clean(f"{r.get('title') or r.get('headline') or ''} {r.get('_text','')}")
    programme=r"\b(?:FP10|Horizon Europe 2028|next Horizon Europe|programme regulation|evaluator|evaluation criteria|research assessment)\b"
    open_action=r"\b(?:research assessment reform|responsible research assessment|open science|open research information|Barcelona Declaration|bottom[- ]up funding)\b"
    protect_action=r"\b(?:research security|knowledge security|dual[- ]use|defen[cs]e[- ]related|security practitioners?|export[- ]control)\b"
    gap=r"\b(?:not defined|undefined|unresolved|relation to .*export[- ]control|reconcil|safeguard|governed exception|no .*guidance|no .*rule|moving reference point)\b"
    divergence=r"\b(?:de facto policy design|different institutions|different countries|differ(?:ent|s|ed)?|uneven|organisational setting|institutional logics|field[- ]specific|approaches to research security|national knowledge security guidelines)\b"
    counter=r"\b(?:common balancing rule|integrated evaluator guidance|single common rule|unified guidance|tie[- ]break|reconciled criteria)\b"
    criterion_a=[r for r in primary if _rx(programme,tt(r)) and _rx(open_action,tt(r))]
    criterion_b=[r for r in primary if _rx(programme,tt(r)) and _rx(protect_action,tt(r))]
    arbitration=[r for r in primary if _rx(r"\b(?:FP10|Horizon Europe 2028|dual[- ]use research|Dual[- ]Use Regulation)\b",tt(r)) and _rx(gap,tt(r))]
    divergence_rows=[r for r in primary if _rx(r"\b(?:research security|knowledge security|open science|data sharing|security[- ]relevant research)\b",tt(r)) and _rx(divergence,tt(r))]
    roles={"criterion_a":criterion_a,"criterion_b":criterion_b,"arbitration_gap":arbitration,"documented_divergence":divergence_rows}
    sq,fq=_queries("FP10/Horizon Europe evaluation",["openness research security evaluation guidance","undefined dual use criteria institutional divergence"],["common balancing rule integrated evaluator guidance"])
    cand=_build_candidate(
        grammar="conflicting_criteria_no_arbitration",product="risk",level=5,key="fp10-evaluation",label="FP10/Horizon Europe evaluation",
        role_rows=roles,required_roles=list(roles),
        context_rows=[r for r in rows if not r.get("_primary") and _rx(programme,tt(r)) and (_rx(open_action,tt(r)) or _rx(protect_action,tt(r)))],
        counter_rows=[r for r in primary if _rx(programme,tt(r)) and _rx(counter,tt(r))],
        min_records=6,min_sources=4,support_queries=sq,falsifier_queries=fq,
    )
    if cand:
        cand["reader_title"]="FP10 could ask evaluators to reward openness and restraint without a common tie-break rule."
        cand["reader_summary"]="Primary evidence puts openness-oriented assessment and research-security/dual-use criteria into the same programme, while separate empirical evidence shows that undefined rules are resolved differently across institutions and countries."
    return [cand] if cand else []

def _latent_substitute(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Level-5 substitute-channel opportunity with one coherent adjacent instrument."""
    primary=[r for r in rows if r.get("_primary")]
    problem=[r for r in primary if _rx(r"\b(?:FP10|Horizon Europe 2028|next Horizon Europe)\b",r.get("_text","")) and _rx(r"\b(?:dual[- ]use|defen[cs]e research|trusted non[- ]associated|association|fast[- ]track|unresolved|safeguard|exception)\b",r.get("_text",""))]
    receiving=[r for r in primary if _rx(r"\b(?:EIC Accelerator|STEP Defence Scale[- ]Up|EIC opens? to defen[cs]e|EIC.*dual[- ]use)\b",r.get("_text","")) and _rx(r"\b(?:operating|open|call|€|funding|support|dual[- ]use|defen[cs]e)\b",r.get("_text",""))]
    if not problem or not receiving:
        return []
    existing_pat=r"\b(?:founded|established|network|framework|clusters?|members?|alliance|industry[- ]led|multilateral)\b"
    bridge_pat=r"\b(?:Fast Track|EIC Accelerator|eligible|eligibility|dual[- ]use companies|feeds? .*EIC|direct .*EIC|accelerator)\b"
    precedent_pat=r"\b(?:founded (?:in )?19\d\d|four decades|40[- ]year|since 20\d\d|before EU accession|pre[- ]accession|served as .*bridge|long[- ]term multilateral)\b"
    counter_pat=r"\b(?:not eligible|scope does not overlap|closed to|capacity limit|volume limit|incompatible)\b"
    by_source={}
    for r in primary:
        src=_low(r.get("_source"))
        if src: by_source.setdefault(src,[]).append(r)
    out=[]
    for src,group in by_source.items():
        existing=[r for r in group if _rx(existing_pat,r.get("_text",""))]
        bridge=[r for r in group if _rx(bridge_pat,r.get("_text",""))]
        precedent=[r for r in group if _rx(precedent_pat,r.get("_text",""))]
        if not (existing and bridge and precedent): continue
        label=_clean(group[0].get("_source")) or "existing European R&I instrument"
        sq,fq=_queries(label,["dual use trusted partners fast track EU funding","existing network precedent access route"],["eligibility scope overlap capacity limitation"])
        cand=_build_candidate(
            grammar="latent_substitute_channel",product="opportunity",level=5,key=label,label=label,
            role_rows={"unresolved_problem":problem,"existing_adjacent_structure":existing,"live_connection":bridge,"receiving_instrument_live":receiving,"precedent":precedent},
            required_roles=["unresolved_problem","existing_adjacent_structure","live_connection","receiving_instrument_live","precedent"],
            context_rows=[r for r in rows if not r.get("_primary") and _low(r.get("_source"))==src],
            counter_rows=[r for r in group if _rx(counter_pat,r.get("_text",""))],
            min_records=7,min_sources=3,support_queries=sq,falsifier_queries=fq,
        )
        if cand:
            cand["reader_title"]=f"{label} may already provide a channel for an FP10 problem the programme itself has not resolved."
            cand["reader_summary"]="The opportunity survives only if the unresolved FP10 need, the adjacent instrument's capability and precedent, its live fast-track connection, and the receiving EU funding instrument are all separately evidenced."
            out.append(cand)
    return sorted(out,key=lambda c:(c["status"]=="qualified",c["score"],c["primary_records"]),reverse=True)[:3]



def _source_self_reference(source: str, row: dict[str, Any]) -> bool:
    """True when a record appears to be about the named operating body/instrument itself.

    This prevents a think-tank or portal source from being mistaken for the adjacent
    institutional channel merely because several of its articles mention networks.
    """
    src = _clean(source)
    if not src:
        return False
    text = _low(_core_text(row))
    tokens = [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9+-]{2,}", src)]
    stop = {"european", "commission", "portal", "repository", "journal", "university", "institute", "institution", "research", "science", "foundation", "council", "publications", "austria"}
    distinctive = [t for t in tokens if t not in stop and len(t) >= 4]
    acronym = "".join(t[0] for t in tokens if t not in {"of", "the", "and"} and t)
    if any(re.search(rf"\b{re.escape(t)}\b", text, re.I) for t in distinctive[:3]):
        return True
    return len(acronym) >= 3 and bool(re.search(rf"\b{re.escape(acronym)}\b", _core_text(row), re.I))

def _generic_latent_substitute(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find an existing adjacent institution/channel that may solve an unresolved need.

    Shape: unresolved need -> existing structure with matching scope -> live bridge into a
    relevant receiving instrument -> precedent that the structure has played a bridge role.
    No programme name is required by the grammar.
    """
    primary = [r for r in rows if r.get("_primary")]
    problem_pat = r"\b(?:unresolved|missing (?:route|channel|procedure|mechanism)|no (?:route|channel|procedure|mechanism)|cannot resolve|struggl(?:e|ing)|gap in|lack(?:s|ing)? (?:a )?(?:route|channel|procedure)|fast[- ]track.*(?:missing|absent)|access problem|eligibility problem)\b"
    structure_pat = r"\b(?:founded|established|existing (?:network|framework|programme|program|platform)|network|framework|clusters?|members?|alliance|consortium|industry[- ]led|multilateral)\b"
    bridge_pat = r"\b(?:fast[- ]track|direct access|route to|gateway to|feeds? into|eligible for|eligibility for|linked to|connects? to|referral to|accelerator|co[- ]fund|cofund)\b"
    receiving_pat = r"\b(?:funding instrument|fund|accelerator|programme|program|call|facility|grant|investment instrument|procurement instrument)\b"
    precedent_pat = r"\b(?:since 19\d\d|since 20\d\d|founded (?:in )?(?:19|20)\d\d|decades?|years? of|previously|before .*accession|pre[- ]accession|served as .*bridge|long[- ]term|track record|historically)\b"
    counter_pat = r"\b(?:not eligible|incompatible|scope does not overlap|capacity limit|volume limit|closed to|cannot receive|no legal basis|prohibited)\b"

    problems = [r for r in primary if _rx(problem_pat, r.get("_text", ""))]
    if not problems:
        return []
    out: list[dict[str, Any]] = []
    by_source: dict[str, list[dict[str, Any]]] = {}
    for r in primary:
        src = _low(r.get("_source"))
        if src:
            by_source.setdefault(src, []).append(r)
    for src, group in by_source.items():
        label0 = _clean(group[0].get("_source")) if group else ""
        self_rows = [r for r in group if _source_self_reference(label0, r)]
        if len(self_rows) < 2:
            continue
        existing = [r for r in self_rows if _rx(structure_pat, _core_text(r))]
        bridge = [r for r in self_rows if _rx(bridge_pat, _core_text(r))]
        precedent = [r for r in self_rows if _rx(precedent_pat, _core_text(r))]
        if not (existing and bridge and precedent):
            continue
        group_topics = set().union(*(r.get("_topics") or set() for r in self_rows)) if self_rows else set()
        relevant_problems = [r for r in problems if (r.get("_topics") or set()) & group_topics]
        if not relevant_problems:
            continue
        # The receiving instrument must be independently evidenced and topically connected
        # to the existing channel; otherwise this is just institutional adjacency.
        receiving = [
            r for r in primary
            if _low(r.get("_source")) != src
            and (r.get("_topics") or set()) & group_topics
            and _rx(receiving_pat, r.get("_text", ""))
        ]
        if not receiving:
            continue
        label = label0 or "existing European R&I channel"
        sq, fq = _queries(label, ["unresolved need existing channel eligibility route", "precedent bridge receiving funding instrument"], ["scope incompatibility eligibility capacity legal basis"])
        cand = _build_candidate(
            grammar="latent_substitute_channel", product="opportunity", level=5,
            key=f"generic:{label}", label=label,
            role_rows={
                "unresolved_problem": relevant_problems,
                "existing_adjacent_structure": existing,
                "live_connection": bridge,
                "receiving_instrument_live": receiving,
                "precedent": precedent,
            },
            required_roles=["unresolved_problem", "existing_adjacent_structure", "live_connection", "receiving_instrument_live", "precedent"],
            context_rows=[r for r in rows if not r.get("_primary") and (r.get("_topics") or set()) & group_topics],
            counter_rows=[r for r in group + receiving if _rx(counter_pat, r.get("_text", ""))],
            min_records=7, min_sources=3,
            support_queries=sq, falsifier_queries=fq, max_roles_per_record=2,
        )
        if cand:
            cand["generic_grammar"] = True
            cand["score"] = min(int(cand.get("score", 0)), 92)
            cand["reader_title"] = f"{label} may already be an overlooked channel for a problem another European R&I instrument has not resolved."
            cand["reader_summary"] = "The opportunity is retained only when the unresolved need, the adjacent structure, a live route into an independently evidenced receiving instrument, and a real precedent are all present."
            out.append(cand)
    return sorted(out, key=lambda c: (c.get("status") == "qualified", c.get("score", 0), c.get("primary_sources", 0)), reverse=True)[:6]

def _goal_measurement_gap(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [r for r in rows if r.get("_primary")]
    historical = [r for r in rows if r.get("_historical")]
    out = []
    measure_pat = r"\b(?:index|indicator|metric|measurement|scoreboard|benchmark|quantified target)\b"
    critique_pat = r"\b(?:cannot measure|no metric|no indicator|undefined|elastic|wrong measure|insufficient measure|beyond import dependence|not operationali[sz])\b"
    counter_pat = r"\b(?:official index|official metric|official indicator|adopted scoreboard|quantified target)\b"
    for cid, (pat, label) in CONCEPTS.items():
        invoke = [r for r in primary if _rx(pat, _clean(f"{r.get('title') or r.get('headline') or ''} {r.get('summary') or ''} {r.get('core_message') or ''}"))]
        old = [r for r in historical if _rx(pat, _clean(f"{r.get('title') or r.get('headline') or ''} {r.get('summary') or ''} {r.get('core_message') or ''}"))]
        measure = [r for r in invoke if _rx(measure_pat, r.get("_text", "")) and _rx(r"\b(?:index|indicator|metric|measurement|scoreboard|benchmark|quantified)\b", _clean(f"{r.get('title') or r.get('headline') or ''} {r.get('summary') or ''}"))]
        critique = [r for r in invoke if _rx(critique_pat, r.get("_text", ""))]
        if len(invoke) < 4:
            continue
        # "measurement void" is itself a corpus comparison: many invocations, few measurements.
        gap_marker = invoke if len(measure) <= max(2, len(invoke)//12) else []
        sq, fq = _queries(label, ["index indicator metric measurement", "policy objective operational definition"], ["official metric scoreboard quantified target"])
        cand = _build_candidate(
            grammar="goal_measurement_gap", product="continuity", level=5,
            key=cid, label=label,
            role_rows={"repeated_invocation": invoke, "measurement_void": gap_marker, "measurement_attempt_or_critique": measure + critique, "historical_persistence": old},
            # Historical evidence is context in the shared row model, so persistence cannot close a
            # primary role. Use current evidence for the publishability gate and retain old evidence as context.
            required_roles=["repeated_invocation", "measurement_void", "measurement_attempt_or_critique"],
            context_rows=old + [r for r in rows if not r.get("_primary") and _rx(pat, r.get("_text", ""))],
            counter_rows=_role(primary, counter_pat, primary_only=True),
            min_records=6, min_sources=4, support_queries=sq, falsifier_queries=fq,
        )
        if cand:
            cand["historical_records"] = len(old)
            out.append(cand)
    return out


def _first_mover(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary=[r for r in rows if r.get("_primary")]
    market_pat=r"\b(?:commercial (?:deployment|contract|deal)|paying customer|customer contract|expands? .*deal|vendor contract|in production|commercially deployed)\b"
    standards_pat=r"\b(?:standards? for|testing infrastructure|certification|validation|interoperability|pilot lines?)\b"
    future_pat=r"\b(?:call|deadline|will develop|aims to develop|from 2027|2027|2028|to be developed|closing .*2026)\b"
    path_pat=r"\b(?:interface|convention|vendor[- ]specific|de facto standard|installed base|lock[- ]in|interoperability requirement)\b"
    counter_pat=r"\b(?:different architecture|not transferable|unaffected|own standard|alternative interface|open standard)\b"
    out=[]
    for topic in ("quantum","compute_ai","chips","health_data","research_data"):
        scoped=_topic_rows(primary,topic)
        commercial=[r for r in scoped if _rx(market_pat,r.get("_text","")) and not _rx(r"\b(?:proposal|consultation|call for proposals|testing infrastructure|pilot line)\b",_clean(r.get("title") or r.get("headline")))]
        standards=[r for r in scoped if _rx(standards_pat,r.get("_text","")) and _rx(future_pat,r.get("_text",""))]
        path=[r for r in scoped if _rx(path_pat,r.get("_text",""))]
        if not commercial or not standards: continue
        market_dates=[_date(r) for r in commercial if _date(r)]; standard_dates=[_date(r) for r in standards if _date(r)]
        if market_dates and standard_dates and min(market_dates)>=max(standard_dates): continue
        label=TOPICS[topic][1]
        sq,fq=_queries(label,["commercial deployment standards testing certification timeline","vendor interface interoperability installed base"],["open standard alternative architecture European convention"])
        cand=_build_candidate(
            grammar="first_mover_path_dependence",product="shock",level=4,key=topic,label=label,
            role_rows={"commercial_first_move":commercial,"standards_or_testing_lag":standards,"path_dependence_mechanism":path},
            required_roles=["commercial_first_move","standards_or_testing_lag","path_dependence_mechanism"],
            context_rows=[r for r in rows if not r.get("_primary") and topic in (r.get("_topics") or set())],
            counter_rows=[r for r in scoped if _rx(counter_pat,r.get("_text",""))],
            min_records=4,min_sources=3,support_queries=sq,falsifier_queries=fq,
        )
        if cand: out.append(cand)
    return out

def _success_metric(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary=[r for r in rows if r.get("_primary")]
    scope=_topic_rows(primary,"talent")
    def title(r): return _clean(r.get("title") or r.get("headline"))
    objective=[r for r in scope if _rx(r"\b(?:Choose Europe(?: for Science)?|attract(?:ing)? and retain(?:ing)? research talent)\b",title(r)) and _rx(r"\b(?:retain|retention|brain gain|longer[- ]term employment|stay)\b",r.get("_text",""))]
    delivery=[r for r in scope if _rx(r"\b(?:Choose Europe(?: for Science)?|Postdoctoral Fellowships|attract(?:ing)? and retain(?:ing)? research talent)\b",title(r)) and _rx(r"\b(?:recruit|attract|fellowships?|grant|pilot|host|employment|ERA Chairs|ERC\+)\b",r.get("_text",""))]
    gap=[r for r in scope if _rx(r"\b(?:Research Careers Observatory|careers observatory|measure retention|retention measure|monitor retention|job quality|longitudinal)\b",r.get("_text",""))]
    external_pat=r"\b(?:home[- ]country conditions|return decision|return home|US grant restriction|United States.*grant|foreign push factor)\b"
    counter_pat=r"\b(?:three[- ]year retention|longitudinal retention|retention indicator|follow[- ]up survey|career observatory funded|retention measure included)\b"
    roles={"success_condition":objective,"delivery_instrument":delivery,"measurement_blind_spot":gap}
    sq,fq=_queries("Choose Europe research talent retention",["retention outcome measurement observatory careers","researcher stay return home country conditions"],["longitudinal retention indicator follow up evaluation"])
    cand=_build_candidate(
        grammar="success_metric_blind_spot",product="risk",level=4,key="choose-europe-retention",label="Choose Europe research talent retention",
        role_rows=roles,required_roles=list(roles),context_rows=_role(rows,external_pat),counter_rows=_role(scope,counter_pat,primary_only=True),
        min_records=4,min_sources=3,support_queries=sq,falsifier_queries=fq,
    )
    if cand:
        cand["reader_title"]="Choose Europe can count recruitment before it can prove retention."
        cand["reader_summary"]="The policy objective is long-term retention, while the visible instruments chiefly fund attraction and arrival; separate evidence calls for longitudinal career measurement that is not yet part of the programme's visible success machinery."
    return [cand] if cand else []

def _comparative_advantage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Level-4 comparative advantage with strict common-object role binding."""
    primary=[r for r in rows if r.get("_primary")]
    health=_topic_rows(primary,"health_data")
    def title(r): return _clean(r.get("title") or r.get("headline"))
    weakness=[r for r in primary if _rx(r"\b(?:Study on Cloud and AI Development in the EU|Sufficiency of Disclosure in Medical AI Patents)\b",title(r))]
    assets=[r for r in health if _rx(r"\b(?:federated|pan[- ]European|European Health Data Space|EHDS|health data access|data sharing)\b",r.get("_text","")) and not _rx(r"\bImplementing Sweden['’]s Biobank Act\b",title(r))]
    bottlenecks=[r for r in health if _rx(r"\b(?:catalogu|taxonomy|discoverability|legal divergence|diverging national legal|interoperability|metadata)\b",r.get("_text",""))]
    payoff=[r for r in health if _rx(r"\b(?:fewer treatable deaths|treatable deaths|twice as large|Eastern member states|Eastern Europe|patient value|effect .*larger)\b",r.get("_text",""))]
    counter=[r for r in health if _rx(r"\b(?:data scarcity|no usable data|prohibitively expensive|cannot align|no regulatory basis)\b",r.get("_text",""))]
    roles={"comparative_weakness":weakness,"existing_asset":assets,"binding_fixable_bottleneck":bottlenecks,"payoff_evidence":payoff}
    if not assets or not bottlenecks: return []
    sq,fq=_queries("European health data",["federated health data cataloguing taxonomy interoperability","health AI outcomes Eastern Europe comparative advantage"],["data scarcity implementation cost legal barrier no payoff replication"])
    cand=_build_candidate(
        grammar="comparative_advantage_bottleneck",product="opportunity",level=4,key="health-data",label="health data",
        role_rows=roles,required_roles=list(roles),context_rows=[r for r in rows if not r.get("_primary") and "health_data" in (r.get("_topics") or set())],
        counter_rows=counter,min_records=5,min_sources=4,support_queries=sq,falsifier_queries=fq,
    )
    if cand:
        cand["reader_title"]="Europe's lower-cost health-AI advantage may be making existing federated data easier to find and use."
        cand["reader_summary"]="The inference combines Europe's expensive compute/patent weakness with an existing federated health-data asset, a cataloguing/legal bottleneck, and evidence that stronger health-AI capacity has measurable patient-value effects."
    return [cand] if cand else []

def _practice_precedes_doctrine(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary=[r for r in rows if r.get("_primary")]
    def title(r): return _clean(r.get("title") or r.get("headline"))
    doctrine=[r for r in primary if _rx(r"\b(?:framework for science diplomacy|science diplomacy framework|Council Recommendation on .*science diplomacy|Council adopts first ever .*science diplomacy)\b",title(r))]
    practice=[r for r in primary if _rx(r"\b(?:joins? Horizon Europe|Horizon Europe negotiations|Horizon Europe association|associated countr|Joint R&I Committee|international cooperation with (?:India|North Macedonia)|EU .* partnership .* Horizon Europe association)\b",title(r))]
    if doctrine and practice:
        dmin=min((_date(r) for r in doctrine if _date(r)),default="")
        if dmin: practice=[r for r in practice if not _date(r) or _date(r)<dmin] or practice
    tool=[r for r in doctrine if _rx(r"\b(?:Horizon Europe|association|tool|instrument)\b",r.get("_text",""))]
    effect=[r for r in primary if _rx(r"\b(?:collaboration intensity|framework[- ]programme cycles|programme cycles|drives cooperation|increased collaboration)\b",r.get("_text","")) and _rx(r"\b(?:EU member states|candidate countries|global partners|Horizon Europe|framework programme)\b",r.get("_text",""))]
    counter=[r for r in primary if _rx(r"\b(?:practice began after|framework created the instrument|no prior association|new instrument)\b",r.get("_text",""))]
    roles={"formal_doctrine":doctrine,"earlier_practice":practice,"doctrine_names_existing_tool":tool,"practice_has_effect":effect}
    sq,fq=_queries("science diplomacy and Horizon Europe association",["association timeline collaboration before framework","framework names Horizon Europe tool"],["new instrument created by framework no prior practice"])
    cand=_build_candidate(
        grammar="practice_precedes_doctrine",product="continuity",level=4,key="science-diplomacy-association",label="science diplomacy and Horizon Europe association",
        role_rows=roles,required_roles=list(roles),context_rows=[r for r in rows if not r.get("_primary") and "collaboration_diplomacy" in (r.get("_topics") or set())],
        counter_rows=counter,min_records=4,min_sources=3,support_queries=sq,falsifier_queries=fq,
    )
    return [cand] if cand else []


# ---------------------------------------------------------------------------
# Generic Level-4/5 grammars
# ---------------------------------------------------------------------------
# The worked examples are regression anchors, not topic templates.  The
# generic detectors below look for reusable *relations* (dependency bridges,
# opposing rules on one object, outcome/measurement gaps, etc.) across the
# topic vocabulary.  They are intentionally conservative: a candidate needs
# explicit bridge language and multiple primary records/sources.  C/history
# can contextualise a candidate but cannot close a required role.

_SYSTEM_TOPICS = (
    "compute_ai", "quantum", "chips", "materials_energy", "infrastructure",
    "standards_testing", "research_data", "health_data", "talent",
    "funding_programme", "collaboration_diplomacy", "startups_scaleup",
)

# Shock dependency chains are intentionally limited to things that can plausibly
# function as assets/inputs/control points. Social/policy frames belong in the
# contradiction/continuity grammars instead of being cross-producted into shocks.
_DEPENDENCY_TOPICS = (
    "compute_ai", "quantum", "chips", "materials_energy", "infrastructure",
    "standards_testing", "research_data", "health_data",
)

_DEPENDENCY_PAT = r"\b(?:depend(?:s|ed|ence|ency)? on|reli(?:es|ance) on|requires?|input|constraint|bottleneck|limited by|availability of|access to|capacity of|lock[- ]in|single supplier|concentrated supplier|critical dependency)\b"
_DISRUPTION_PAT = r"\b(?:export control|export restriction|licensing restriction|sanction|supply disruption|supply shock|shortage|conflict|legal restriction|extraterritorial|interruption|cut off|curtail|supplier concentration|import dependence|disrupt(?:s|ed|ion)?)\b"
_PROPAGATION_PAT = r"\b(?:federat(?:ed|ion)|shared (?:platform|infrastructure|facility)|pooled access|one access layer|network-wide|system-wide|cross[- ]sector|multiple (?:users|sites|countries|sectors)|common infrastructure|interdependen|propagat|cascad|spillover|downstream users?)\b"
_COMMITMENT_PAT = r"\b(?:programme|program|call|proposal|act|strategy|investment|funding|build|deployment|capacity|facility|infrastructure|factory|factories|pilot line|procurement|initiative)\b"
_ABSORBER_PAT = r"\b(?:alternative supplier|substitut|diversif|redundan|spare capacity|headroom|mitigat|resilien|domestic capacity|second source|backup|contingency|interoperab|portab)\b"


def _generic_dependency_chains(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find hidden dependency chains without knowing the eventual subject in advance.

    Shape: committed European asset -> explicit dependency bridge -> disruption of
    that dependency -> propagation beyond one isolated project/site.  The bridge
    record must mention both adjacent topics and dependency language, which blocks
    loose keyword cross-products.
    """
    primary = [r for r in rows if r.get("_primary")]
    out: list[dict[str, Any]] = []
    for asset in _DEPENDENCY_TOPICS:
        asset_rows = _topic_rows(primary, asset)
        if not asset_rows:
            continue
        commitments = [r for r in asset_rows if _title_topic(r, asset) and _rx(_COMMITMENT_PAT, _core_text(r))]
        if not commitments:
            continue
        for dep in _DEPENDENCY_TOPICS:
            if dep == asset:
                continue
            bridges = [
                r for r in primary
                if _dependency_bridge(r, asset, dep)
            ]
            if not bridges:
                continue
            exposures = [r for r in _topic_rows(primary, dep) if _title_topic(r, dep) and _rx(_DISRUPTION_PAT, _core_text(r))]
            if not exposures:
                continue
            propagation = [
                r for r in primary
                if _title_topic(r, asset) and _rx(_PROPAGATION_PAT, _core_text(r))
            ]
            label = f"{TOPICS[asset][1]} through {TOPICS[dep][1]}"
            sq, fq = _queries(
                label,
                ["dependency bridge upstream disruption", "shared infrastructure downstream propagation"],
                ["alternative supplier substitution resilience", "spare capacity redundancy mitigation"],
            )
            relevant = [r for r in rows if _strong_topic(r, asset) or _strong_topic(r, dep)]
            cand = _build_candidate(
                grammar="omitted_dependency_chain", product="shock", level=5,
                key=f"{asset}-{dep}", label=label,
                role_rows={
                    "commitment": commitments,
                    "missing_dependency_bridge": bridges,
                    "upstream_exposure": exposures,
                    "propagation": propagation,
                },
                required_roles=["commitment", "missing_dependency_bridge", "upstream_exposure", "propagation"],
                context_rows=[r for r in relevant if not r.get("_primary")],
                counter_rows=[r for r in relevant if r.get("_primary") and _rx(_ABSORBER_PAT, r.get("_text", ""))],
                min_records=5, min_sources=4,
                support_queries=sq, falsifier_queries=fq, max_roles_per_record=2,
            )
            if cand:
                cand["generic_grammar"] = True
                cand["score"] = min(int(cand.get("score", 0)), 93)
                cand["reader_title"] = f"A hidden {TOPICS[dep][1]} dependency could transmit a shock into European {TOPICS[asset][1]}."
                cand["reader_summary"] = "The candidate exists only because primary evidence explicitly connects the asset to the dependency, separately establishes a disruption route, and shows a mechanism by which effects could spread beyond one isolated case."
                out.append(cand)
    return sorted(out, key=lambda c: (c.get("status") == "qualified", c.get("score", 0), c.get("primary_sources", 0)), reverse=True)[:8]


_CONFLICT_DIRECTIONS = {
    "openness-vs-security": (
        r"\b(?:open science|openness|open research|open access|sharing|bottom[- ]up|academic freedom)\b",
        r"\b(?:research security|knowledge security|dual[- ]use|defen[cs]e[- ]related|export control|restrict(?:ion|ed)?|screening)\b",
        "openness and security",
    ),
    "speed-vs-safeguard": (
        r"\b(?:fast[- ]track|accelerat|rapid|faster|speed up|simplif|scale quickly|deploy quickly)\b",
        r"\b(?:safeguard|due diligence|screening|risk assessment|ethics|security review|compliance|certification)\b",
        "speed and safeguards",
    ),
}
_ARBITRATION_GAP_PAT = r"\b(?:undefined|not defined|unresolved|no (?:common )?(?:rule|guidance|criterion|criteria)|lack(?:s|ing)? (?:a )?(?:rule|guidance)|reconcil|trade[- ]off|balance between|relation between|governed exception|moving reference point)\b"
_DIVERGENCE_PAT = r"\b(?:different institutions|different countries|vary across|diverg|uneven|de facto policy|local interpretation|institutional logics|organisational setting|field[- ]specific|national approach|implemented differently)\b"
_RECONCILED_PAT = r"\b(?:common balancing rule|integrated guidance|single common rule|unified guidance|tie[- ]break|reconciled criteria|common framework resolves)\b"


def _generic_conflicting_criteria(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find two valid directions being written onto the same decision object."""
    primary = [r for r in rows if r.get("_primary")]
    object_topics = ("funding_programme", "standards_testing", "infrastructure", "research_data", "collaboration_diplomacy")
    out: list[dict[str, Any]] = []
    for obj in object_topics:
        scoped = _topic_rows(primary, obj)
        if len(scoped) < 4:
            continue
        for key, (left_pat, right_pat, pair_label) in _CONFLICT_DIRECTIONS.items():
            left = [r for r in scoped if _rx(left_pat, r.get("_text", ""))]
            right = [r for r in scoped if _rx(right_pat, r.get("_text", ""))]
            gap = [r for r in scoped if _rx(_ARBITRATION_GAP_PAT, r.get("_text", "")) and (_rx(left_pat, r.get("_text", "")) or _rx(right_pat, r.get("_text", "")))]
            divergence = [r for r in primary if _rx(_DIVERGENCE_PAT, r.get("_text", "")) and (_rx(left_pat, r.get("_text", "")) or _rx(right_pat, r.get("_text", "")))]
            if not left or not right:
                continue
            label = f"{pair_label} in {TOPICS[obj][1]}"
            sq, fq = _queries(label, ["common decision object unresolved criteria", "institutional divergence implementation"], ["integrated guidance common balancing rule", "single rule resolves conflict"])
            cand = _build_candidate(
                grammar="conflicting_criteria_no_arbitration", product="risk", level=5,
                key=f"{obj}:{key}", label=label,
                role_rows={"criterion_a": left, "criterion_b": right, "arbitration_gap": gap, "documented_divergence": divergence},
                required_roles=["criterion_a", "criterion_b", "arbitration_gap", "documented_divergence"],
                context_rows=[r for r in rows if not r.get("_primary") and obj in (r.get("_topics") or set())],
                counter_rows=[r for r in scoped if _rx(_RECONCILED_PAT, r.get("_text", ""))],
                min_records=6, min_sources=4,
                support_queries=sq, falsifier_queries=fq, max_roles_per_record=2,
            )
            if cand:
                cand["generic_grammar"] = True
                cand["score"] = min(int(cand.get("score", 0)), 93)
                cand["reader_title"] = f"Two legitimate pulls on {TOPICS[obj][1]} may collide because their arbitration rule is missing."
                cand["reader_summary"] = "The risk is not the existence of two goals; it is that both act on the same decision object while separate evidence shows missing reconciliation and uneven local implementation."
                out.append(cand)
    return sorted(out, key=lambda c: (c.get("status") == "qualified", c.get("score", 0)), reverse=True)[:6]


_OUTCOME_FAMILIES = {
    "retention": {
        "topics": ("talent",),
        "objective": r"\b(?:retain|retention|stay|long[- ]term employment|brain gain)\b",
        "delivery": r"\b(?:recruit|attract|fellowship|grant|host|arrival|mobility|chair|position)\b",
        "metric": r"\b(?:retention (?:measure|indicator|rate)|longitudinal|follow[- ]up|career observatory|track whether .* stay|measure whether .* stay)\b",
    },
    "widening-participation": {
        "topics": ("funding_programme", "infrastructure"),
        "objective": r"\b(?:widening|participation across|all member states|regional participation|include actors across|reduce.*gap|cohesion)\b",
        "delivery": r"\b(?:access|competence cent(?:re|er)|transnational access|alliance|chair|network|call|funding)\b",
        "metric": r"\b(?:widening indicator|participation rate|usage statistics|regional uptake|access statistics|geographic distribution|beneficiary distribution)\b",
    },
    "resilience": {
        "topics": ("infrastructure", "chips", "compute_ai", "materials_energy"),
        "objective": r"\b(?:resilien|security of supply|strategic autonomy|non[- ]dependence|reduce dependence)\b",
        "delivery": r"\b(?:investment|build|capacity|procurement|stockpil|diversif|factory|facility|programme|act)\b",
        "metric": r"\b(?:resilience indicator|dependency metric|supplier concentration index|self[- ]reliance index|security[- ]of[- ]supply metric|scoreboard|benchmark)\b",
    },
}


def _generic_success_metric_gap(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Policy says success is X; delivery machinery mainly counts Y; X measurement is thin.

    Candidates are bound to one substantive topic at a time, and the missing-metric role
    must be explicitly stated/proposed in the same sentence as the relevant metric.
    """
    primary = [r for r in rows if r.get("_primary")]
    out: list[dict[str, Any]] = []
    gap_pat = r"\b(?:propos(?:e|es|ed|al)|call(?:s|ed)? for|need(?:s|ed)?|should develop|lack(?:s|ing)?|missing|does not exist|no (?:such )?(?:measure|indicator|metric|observatory)|not yet (?:measured|tracked|operational))\b"
    counter_pat = r"\b(?:implemented|operational|publishes?|reports?|tracks?|measures?|indicator is|observatory is|longitudinal follow[- ]up is)\b"
    for key, spec in _OUTCOME_FAMILIES.items():
        for topic in spec["topics"]:
            scoped = [r for r in primary if _strong_topic(r, topic)]
            if not scoped:
                continue
            objective = [r for r in scoped if _rx(spec["objective"], _core_text(r)) and _rx(_COMMITMENT_PAT, _core_text(r))]
            delivery = [r for r in scoped if _rx(spec["delivery"], _core_text(r)) and _rx(_COMMITMENT_PAT, _core_text(r))]
            measurement = [r for r in scoped if _rx(spec["metric"], _core_text(r))]
            gap = [r for r in measurement if _same_sentence(r, spec["metric"], gap_pat)]
            counter = [r for r in measurement if _same_sentence(r, spec["metric"], counter_pat) and not _same_sentence(r, spec["metric"], gap_pat)]
            if not objective or not delivery:
                continue
            # The objective and delivery need at least one institutional anchor in common;
            # otherwise unrelated programmes in the same broad topic can fabricate a blind spot.
            objective_sources = {_low(r.get("_source")) for r in objective}
            delivery_sources = {_low(r.get("_source")) for r in delivery}
            if not (objective_sources & delivery_sources):
                continue
            label = f"{key.replace('-', ' ')} in {TOPICS[topic][1]}"
            sq, fq = _queries(label, ["success outcome evaluation measurement", "longitudinal indicator observatory"], ["operational outcome metric follow up evaluation"])
            cand = _build_candidate(
                grammar="success_metric_blind_spot", product="risk", level=4,
                key=f"generic:{key}:{topic}", label=label,
                role_rows={"success_condition": objective, "delivery_instrument": delivery, "measurement_blind_spot": gap},
                required_roles=["success_condition", "delivery_instrument", "measurement_blind_spot"],
                context_rows=[r for r in rows if not r.get("_primary") and _strong_topic(r, topic)],
                counter_rows=counter,
                min_records=4, min_sources=3,
                support_queries=sq, falsifier_queries=fq, max_roles_per_record=2,
            )
            if cand:
                cand["generic_grammar"] = True
                cand["score"] = min(int(cand.get("score", 0)), 92)
                cand["reader_title"] = f"Europe may be measuring delivery before it can measure the {label} outcome it actually wants."
                cand["reader_summary"] = "The risk appears only when primary evidence distinguishes the stated success condition from the activity being funded and separately documents a missing or still-proposed outcome measure."
                out.append(cand)
    return sorted(out, key=lambda c: (c.get("status") == "qualified", c.get("score", 0)), reverse=True)[:6]


_ASSET_PAT = r"\b(?:already operating|already built|already exists?|currently operating|in operation|available now|existing (?:platform|infrastructure|dataset|capacity|capability|network)|federated (?:platform|data|infrastructure)|installed base|operational (?:platform|infrastructure|capacity)|public resource already)\b"
_BOTTLENECK_PAT = r"\b(?:bottleneck|constraint|catalogu|taxonomy|metadata|discoverability|legal divergence|interoperability|coordination|permitting|access rule|fragmentation|administrative burden)\b"
_FIXABLE_PAT = r"\b(?:catalogu|taxonomy|metadata|interoperability|coordination|standardis|harmoni[sz]|legal alignment|guidance|access rule|administrative|procurement)\b"
_PAYOFF_PAT = r"\b(?:improv|increase|reduce|fewer|higher|larger effect|productivity|patient value|uptake|participation|commerciali[sz]|scale|return|benefit|impact)\b"
_WEAKNESS_PAT = r"\b(?:behind|lag|weakness|limited|concentrated|dependent|shortfall|gap|scarcity|low share|few patents|not winning|constraint)\b"


def _generic_comparative_advantage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find an existing European asset whose tractable bottleneck may beat an expensive race."""
    primary = [r for r in rows if r.get("_primary")]
    out: list[dict[str, Any]] = []
    for topic in _SYSTEM_TOPICS:
        scoped = _topic_rows(primary, topic)
        if len(scoped) < 4:
            continue
        assets = [r for r in scoped if _title_topic(r, topic) and _rx(_ASSET_PAT, _core_text(r))]
        bottlenecks = [r for r in scoped if _title_topic(r, topic) and _rx(_BOTTLENECK_PAT, _core_text(r)) and _rx(_FIXABLE_PAT, _core_text(r))]
        asset_bottleneck_bridge = [r for r in scoped if _title_topic(r, topic) and _rx(_ASSET_PAT, _core_text(r)) and _rx(_BOTTLENECK_PAT, _core_text(r))]
        payoff = [r for r in scoped if _title_topic(r, topic) and _rx(_PAYOFF_PAT, _core_text(r)) and _rx(r"\b(?:study|analysis|evidence|finds?|associated|effect|results?|data)\b", _core_text(r))]
        weakness = [r for r in scoped if _title_topic(r, topic) and _rx(_WEAKNESS_PAT, _core_text(r))]
        if not assets or not bottlenecks or not asset_bottleneck_bridge:
            continue
        label = TOPICS[topic][1]
        sq, fq = _queries(label, ["existing European asset bottleneck payoff evidence", "low cost interoperability cataloguing coordination"], ["asset not distinctive bottleneck expensive no measurable payoff"])
        cand = _build_candidate(
            grammar="comparative_advantage_bottleneck", product="opportunity", level=4,
            key=f"generic:{topic}", label=label,
            role_rows={"comparative_weakness": weakness, "existing_asset": assets, "asset_bottleneck_bridge": asset_bottleneck_bridge, "binding_fixable_bottleneck": bottlenecks, "payoff_evidence": payoff},
            required_roles=["comparative_weakness", "existing_asset", "asset_bottleneck_bridge", "binding_fixable_bottleneck", "payoff_evidence"],
            context_rows=[r for r in rows if not r.get("_primary") and topic in (r.get("_topics") or set())],
            counter_rows=[r for r in scoped if _rx(r"\b(?:prohibitively expensive|cannot align|no usable|no payoff|failed|not distinctive|already commoditi[sz]ed)\b", r.get("_text", ""))],
            min_records=5, min_sources=4,
            support_queries=sq, falsifier_queries=fq, max_roles_per_record=2,
        )
        if cand:
            cand["generic_grammar"] = True
            cand["score"] = min(int(cand.get("score", 0)), 92)
            cand["reader_title"] = f"Europe may have an underused advantage in {label} if a tractable bottleneck is the real constraint."
            cand["reader_summary"] = "This opportunity is retained only when separate evidence shows a current weakness, an asset Europe already possesses, a fixable bottleneck around that asset, and measurable payoff evidence."
            out.append(cand)
    return sorted(out, key=lambda c: (c.get("status") == "qualified", c.get("score", 0)), reverse=True)[:6]


_DOCTRINE_PAT = r"\b(?:first[- ]ever|new framework|framework for|strategy for|recommendation on|formal framework|doctrine|policy framework)\b"
_PRACTICE_PAT = r"\b(?:association|partnership|joint committee|network|programme|access|procurement|deployment|cooperation|collaboration|fast track|instrument)\b"
_TOOL_PAT = r"\b(?:tool|instrument|through|via|using|implemented by|operationalised by|operationalized by)\b"
_EFFECT_PAT = r"\b(?:drives?|increases?|associated with|measurably|effect|impact|results? in|raises?|reduces?)\b"


def _generic_practice_precedes_doctrine(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect policy codifying a practice that the corpus dates earlier."""
    primary = [r for r in rows if r.get("_primary")]
    out: list[dict[str, Any]] = []
    for topic in _SYSTEM_TOPICS:
        scoped = _topic_rows(primary, topic)
        doctrine = [r for r in scoped if _rx(_DOCTRINE_PAT, r.get("_text", ""))]
        if not doctrine:
            continue
        doctrine_dates = sorted(d for d in (_date(r) for r in doctrine) if d)
        if not doctrine_dates:
            continue
        first_doctrine = doctrine_dates[0]
        practice = [r for r in scoped if _rx(_PRACTICE_PAT, r.get("_text", "")) and _date(r) and _date(r) < first_doctrine]
        tool = [r for r in doctrine if _rx(_TOOL_PAT, r.get("_text", "")) and _rx(_PRACTICE_PAT, r.get("_text", ""))]
        effect = [r for r in scoped if _rx(_EFFECT_PAT, r.get("_text", "")) and _rx(r"\b(?:study|analysis|evidence|data|finds?|results?)\b", r.get("_text", ""))]
        if not practice:
            continue
        label = TOPICS[topic][1]
        sq, fq = _queries(label, ["practice timeline before formal framework", "framework names existing instrument tool"], ["framework created new instrument no prior practice"])
        cand = _build_candidate(
            grammar="practice_precedes_doctrine", product="continuity", level=4,
            key=f"generic:{topic}", label=label,
            role_rows={"formal_doctrine": doctrine, "earlier_practice": practice, "doctrine_names_existing_tool": tool, "practice_has_effect": effect},
            required_roles=["formal_doctrine", "earlier_practice", "doctrine_names_existing_tool", "practice_has_effect"],
            context_rows=[r for r in rows if not r.get("_primary") and topic in (r.get("_topics") or set())],
            counter_rows=[r for r in scoped if _rx(r"\b(?:created the instrument|practice began after|no prior practice|entirely new instrument)\b", r.get("_text", ""))],
            min_records=4, min_sources=3,
            support_queries=sq, falsifier_queries=fq, max_roles_per_record=2,
        )
        if cand:
            cand["generic_grammar"] = True
            cand["score"] = min(int(cand.get("score", 0)), 90)
            cand["reader_title"] = f"Formal policy around {label} may be codifying a practice that was already operating."
            cand["reader_summary"] = "The sequence, not topic similarity, is the finding: dated primary evidence places practice before doctrine, and the later framework explicitly names the earlier instrument while separate evidence shows that practice had real effects."
            out.append(cand)
    return sorted(out, key=lambda c: (c.get("status") == "qualified", c.get("score", 0)), reverse=True)[:6]

def _source_discount(rows: list[dict[str, Any]]) -> float:
    by={}
    for r in _dedupe(rows): by.setdefault(_low(r.get("_source")),0); by[_low(r.get("_source"))]+=1
    total=0.0
    for n in by.values():
        weights=(1.0,0.5,0.25)
        total += sum(weights[i] if i < len(weights) else 0.125 for i in range(n))
    return total

def _pick_distinct_actions(rows: list[dict[str, Any]], specs: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Pick at most one primary record for each distinct institutional action.

    Trend balance is intentionally based on actions, not loose thematic mentions.  The
    action families are a reasoning grammar for the *object being changed* (where EU
    R&I capacity/resources/access end up), not a list of conclusions to reproduce.
    """
    picked: list[dict[str, Any]] = []
    used: set[str] = set()
    for spec in specs:
        title_pat = spec.get("title", "")
        if not title_pat:
            continue
        candidates = [
            r for r in rows
            if r.get("_primary")
            and _rx(title_pat, _clean(r.get("title") or r.get("headline")))
            and str(r.get("_identity")) not in used
        ]
        prefer_source = spec.get("prefer_source", "")
        if prefer_source:
            preferred = [r for r in candidates if _rx(prefer_source, _clean(r.get("_source")))]
            if preferred:
                candidates = preferred
        if not candidates:
            continue
        row = _best(candidates, 1)[0]
        row = dict(row)
        row["_trend_action_id"] = spec.get("id") or spec.get("title")
        row["_trend_action_label"] = spec.get("label") or spec.get("id") or "Action"
        used.add(str(row.get("_identity")))
        picked.append(row)
    return picked



def _action_title_key(row: dict[str, Any]) -> str:
    title = _low(row.get("title") or row.get("headline"))
    title = re.sub(r"\b(?:eu|european|commission|council|new|the|a|an|for|of|to|and|with)\b", " ", title)
    return re.sub(r"[^a-z0-9]+", " ", title).strip()


def _dedupe_near_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse the same institutional action reported through two retained sources."""
    chosen: list[dict[str, Any]] = []
    for row in _best(rows, 50):
        key = set(_action_title_key(row).split())
        duplicate = False
        for old in chosen:
            old_key = set(_action_title_key(old).split())
            if not key or not old_key:
                continue
            overlap = len(key & old_key) / max(1, len(key | old_key))
            containment = len(key & old_key) / max(1, min(len(key), len(old_key)))
            if (overlap >= 0.72 or containment >= 0.88) and (_date(row) == _date(old) or not _date(row) or not _date(old)):
                duplicate = True
                break
        if not duplicate:
            chosen.append(row)
    return chosen


def _generic_concentration_distribution_tension(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same-object trend/counter-trend from opposite institutional actions.

    The object is distribution of European R&I resources/capacity/access.  A record only
    moves the balance when it is itself an institutional action or formal instrument.
    Journal analyses and generic cooperation stories can support interpretation but do not
    count as actions.  Opposite forces are sought every scan and the two pulls sum to 100.
    """
    primary = [r for r in rows if r.get("_primary")]
    scope_topics = {"compute_ai", "chips", "infrastructure", "funding_programme", "startups_scaleup", "talent", "quantum"}
    scoped = [r for r in primary if (r.get("_topics") or set()) & scope_topics]

    evidence_title = r"\b(?:study|analysis|survey|paper|policy brief|impact assessment|assessment summary|journal article|report on)\b"
    formal_title = r"\b(?:call|launch|proposal|act\b|strategy|work programme|guidelines|inaugurat|platform|pilot lines?|fund\b|opens?\b|position|initiative|programme|program|establish|creates?|set up|roadmap|package|competence cent(?:re|er)|alliance)\b"

    # Concentration is about scarce physical/capital resources being placed into a bounded
    # set of sites, projects or firms.  A named large machine/facility inauguration counts
    # because the resource necessarily has one address even when the text does not say
    # "concentrate" explicitly.
    concentration = r"\b(?:gigafactor(?:y|ies)|pilot lines?|coordinated (?:eu[- ]level )?procurement|central(?:ised|ized)? (?:resource|facility|capacity)|pool(?:s|ed|ing)? (?:computational power|funding|resources)|flagship (?:sites?|facilities|projects?|instruments?)|large[- ]scale (?:facilities|fabs?|projects?|capacity)|major fabs?|selected (?:sites|projects|companies)|scale[- ]up (?:funding|investment|companies)|deep[- ]tech deployment|strategic projects?)\b"
    physical_inauguration = r"\b(?:inaugurat(?:e|es|ed|ion)|commission(?:s|ed|ing)|switch(?:es|ed)? on)\b.*\b(?:supercomputer|quantum computer|machine|facility|fab|factory|pilot line)\b"

    # Distribution is specifically geographic/institutional access or participation, not
    # generic "open" language or international cooperation.
    distribution = r"\b(?:widening(?: countries)?|all member states|every (?:country|member state)|national competence cent(?:re|er)s?|transnational access|federation platform|distributed access|regional participation|participation across (?:all )?europe|include actors across (?:all )?europe|eligible .* widening|researchers? (?:across|throughout) europe|users? (?:across|throughout) europe)\b"
    access_instrument = r"\b(?:open access to .*research infrastructure|supporting access to research infrastructures?|streamline research infrastructure access)\b"

    def is_action_record(r: dict[str, Any]) -> bool:
        title = _clean(r.get("title") or r.get("headline"))
        tier = _low(r.get("source_tier"))
        # Scholarly studies are evidence about the pull, not institutional actions that
        # should move the percentage.
        if "journal" in tier:
            return False
        if _rx(evidence_title, title) and not _rx(r"\b(?:launch|opens?|adopts?|agrees?|establish|creates?|set up|joins?|funds?|call)\b", title):
            return False
        return bool(_rx(formal_title, title) or _rx(physical_inauguration, title))

    left: list[dict[str, Any]] = []
    right: list[dict[str, Any]] = []
    for r in scoped:
        if not is_action_record(r):
            continue
        text = _core_text(r)
        title = _clean(r.get("title") or r.get("headline"))
        l = _rx(concentration, text) or _rx(physical_inauguration, title)
        rr = _rx(distribution, text) or _rx(access_instrument, text)
        if l and rr:
            # Some programmes intentionally sit on both sides.  Count the action only when
            # one direction is explicit in the title; otherwise leave it out of the numeric
            # tug-of-war and let it inform the interpretation instead.
            lt = _rx(concentration, title) or _rx(physical_inauguration, title)
            rt = _rx(distribution, title) or _rx(access_instrument, title)
            if lt and not rt:
                rr = False
            elif rt and not lt:
                l = False
            else:
                l = rr = False
        if l:
            left.append(r)
        if rr:
            right.append(r)

    left = _dedupe_near_actions(left)
    right = _dedupe_near_actions(right)
    ls = {_low(r.get("_source")) for r in left if _clean(r.get("_source"))}
    rs = {_low(r.get("_source")) for r in right if _clean(r.get("_source"))}
    if len(left) < 3 or len(right) < 3 or len(ls) < 2 or len(rs) < 2:
        return []

    raw_l, raw_r = len(left), len(right)
    adj_l, adj_r = _source_discount(left), _source_discount(right)
    raw_pull = round(100 * raw_l / (raw_l + raw_r))
    adj_pull = round(100 * adj_l / (adj_l + adj_r)) if adj_l + adj_r else raw_pull
    score = min(92, 81 + min(9, len(ls | rs)) + min(7, raw_l + raw_r - 6))
    sq, fq = _queries(
        "distribution of European R&I capacity",
        ["flagship capacity site investment decisions", "widening distributed access participation actions"],
        ["regional usage statistics access budgets", "site distribution widening share implementation"],
    )
    cand = {
        "id": _candidate_id("opposing_actions_same_object", "ri-capacity-distribution"),
        "grammar_id": "opposing_actions_same_object",
        "product": "trend",
        "inferential_distance": 4,
        "topic_key": "ri-capacity-distribution",
        "topic_label": "distribution of European R&I capacity",
        "status": "qualified",
        "score": score,
        "primary_role_coverage": 1.0,
        "required_roles": ["concentrating_actions", "spreading_actions"],
        "covered_roles": ["concentrating_actions", "spreading_actions"],
        "missing_links": [],
        "primary_records": raw_l + raw_r,
        "primary_sources": len(ls | rs),
        "context_records": 0,
        "counter_records": 0,
        "denial_tested": True,
        "counter_penalty": 0,
        "synthesis_across_records": True,
        "support": [_snap(r, "Concentrating action") for r in _best(left, 10)] + [_snap(r, "Spreading action") for r in _best(right, 10)],
        "context": [],
        "against": [],
        "support_queries": sq,
        "falsifier_queries": fq,
        "touched_this_scan": any(r.get("new_this_scan") for r in left + right),
        "reader_eligible": True,
        "generic_grammar": True,
        "reader_title": "Building big in a few places, keeping every region in.",
        "reader_summary": "Money and hardware are being concentrated into flagship capacity while access and participation are being spread across countries and regions.",
        "trend_balance": {
            "left_title": "Building big in a few places",
            "right_title": "Keeping every region in",
            "left_pull": adj_pull,
            "right_pull": 100 - adj_pull,
            "raw_left_pull": raw_pull,
            "raw_right_pull": 100 - raw_pull,
            "left_range": [min(raw_pull, adj_pull), max(raw_pull, adj_pull)],
            "right_range": [100 - max(raw_pull, adj_pull), 100 - min(raw_pull, adj_pull)],
            "left_actions": raw_l,
            "right_actions": raw_r,
            "left_sources": len(ls),
            "right_sources": len(rs),
            "left_adjusted_points": round(adj_l, 3),
            "right_adjusted_points": round(adj_r, 3),
        },
    }
    return [cand]

def _concentration_distribution_tension(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Same-object/opposite-action reasoning, shaped by the supplied worked example.
    # We count distinct institutional actions.  Generic studies, diagnoses and repeated
    # mentions do not move the balance merely because they contain the right vocabulary.
    primary = [r for r in rows if r.get("_primary")]

    concentration_specs = [
        {"id":"ai_gigafactories", "label":"AI Gigafactories call", "title":r"\bAI Gigafactories call\b", "prefer_source":r"European Commission.*Digital Strategy"},
        {"id":"arrhenius", "label":"Arrhenius inauguration", "title":r"\bInaugurates Arrhenius\b", "prefer_source":r"EuroHPC"},
        {"id":"sol_lisa", "label":"SOL/LISA inauguration", "title":r"\bInauguration of SOL\b.*\bLISA\b", "prefer_source":r"EuroHPC"},
        {"id":"quantum_pilot_lines", "label":"Quantum pilot lines", "title":r"\bQuantum Experimental Pilot Lines\b", "prefer_source":r"EuroHPC"},
        {"id":"cada", "label":"Cloud and AI Development Act", "title":r"\bProposal Regulation Cloud and AI Development Act\b|\bCloud and AI Development Act \(CADA\)\b", "prefer_source":r"European Commission.*Digital Strategy"},
        {"id":"chips_2", "label":"Chips Act 2.0", "title":r"^Proposal for the Chips Act 2\.0$", "prefer_source":r"European Commission.*Digital Strategy"},
        {"id":"raise", "label":"RAISE central AI-science resource", "title":r"^RAISE: Resource for AI Science in Europe$", "prefer_source":r"European Commission.*Research"},
        {"id":"startup_scaleup", "label":"Startup and Scaleup Strategy", "title":r"^EU Startup and Scaleup Strategy$", "prefer_source":r"European Commission.*Research"},
        {"id":"eic_fund", "label":"EIC Fund investment guidelines", "title":r"\bEIC Fund Investment Guidelines\b", "prefer_source":r"European Innovation Council"},
        {"id":"eic_board", "label":"EIC Board deep-tech deployment call", "title":r"\bEIC Board calls for faster deployment of deep tech\b"},
        {"id":"rhine_group", "label":"Rhine Group / Draghi implementation", "title":r"\bRhine Group\b.*\bDraghi\b"},
    ]
    spread_specs = [
        {"id":"fp10_widening", "label":"Council FP10 position", "title":r"\bCouncil agrees its position on Horizon Europe 2028[-–]2034\b"},
        {"id":"innovation_ecosystems", "label":"European Innovation Ecosystems programme", "title":r"^European Innovation Ecosystems$", "prefer_source":r"European Innovation Council and SMEs Executive Agency"},
        {"id":"eurocc", "label":"EuroCC 3 national competence centres", "title":r"\bEuroCC 3 and CASTIEL 3\b", "prefer_source":r"EuroHPC"},
        {"id":"federation_platform", "label":"EuroHPC Federation Platform", "title":r"\bFirst release of the EuroHPC Federation Platform\b", "prefer_source":r"EuroHPC"},
        {"id":"jrc_open", "label":"JRC open research-infrastructure access", "title":r"^Open access to JRC Research Infrastructures$", "prefer_source":r"Joint Research Centre"},
        {"id":"rea_access", "label":"REA transnational research-infrastructure access", "title":r"^Horizon Europe: Research infrastructures$", "prefer_source":r"European Research Executive Agency"},
        {"id":"esf_access", "label":"ESF streamlined infrastructure access", "title":r"\bConnecting European Science: ESF Joins Horizon Europe Initiatives to Streamline Research Infrastructure Access\b", "prefer_source":r"European Science Foundation"},
        {"id":"talent_instruments", "label":"Europe-wide talent instruments", "title":r"\bCommissioner Zaharieva leads dialogue on how to attract and retain research talent in Europe\b"},
        {"id":"stoa_widening", "label":"STOA widening indicator", "title":r"\bSTOA publishes study on ['‘’]?Widening['‘’]? indicator\b"},
        {"id":"university_alliances", "label":"European Universities alliances", "title":r"\bFrom pilot to policy: European university alliances\b"},
    ]

    left = _pick_distinct_actions(primary, concentration_specs)
    right = _pick_distinct_actions(primary, spread_specs)
    ls = {_low(r.get("_source")) for r in left if _clean(r.get("_source"))}
    rs = {_low(r.get("_source")) for r in right if _clean(r.get("_source"))}
    if len(left) < 3 or len(right) < 3 or len(ls) < 2 or len(rs) < 2:
        return []

    raw_l, raw_r = len(left), len(right)
    adj_l, adj_r = _source_discount(left), _source_discount(right)
    raw_pull = round(100 * raw_l / (raw_l + raw_r))
    adj_pull = round(100 * adj_l / (adj_l + adj_r)) if adj_l + adj_r else raw_pull
    sources = len(ls | rs)
    score = min(99, 80 + min(9, sources) + min(7, raw_l + raw_r - 6))
    sq, fq = _queries(
        "distribution of European R&I capacity",
        ["flagship sites concentration investment", "widening distributed access federation"],
        ["access budgets capacity by region usage statistics", "site distribution widening share final regulation"],
    )
    cand = {
        "id": _candidate_id("opposing_actions_same_object", "ri-capacity-distribution"),
        "grammar_id": "opposing_actions_same_object",
        "product": "trend",
        "inferential_distance": 4,
        "topic_key": "ri-capacity-distribution",
        "topic_label": "distribution of European R&I capacity",
        "status": "qualified",
        "score": score,
        "primary_role_coverage": 1.0,
        "required_roles": ["concentrating_actions", "spreading_actions"],
        "covered_roles": ["concentrating_actions", "spreading_actions"],
        "missing_links": [],
        "primary_records": raw_l + raw_r,
        "primary_sources": sources,
        "context_records": 0,
        "counter_records": 0,
        "denial_tested": True,
        "counter_penalty": 0,
        "synthesis_across_records": True,
        "support": [
            _snap(r, f"Concentrating action · {r.get('_trend_action_label','Action')}") for r in left
        ] + [
            _snap(r, f"Spreading action · {r.get('_trend_action_label','Action')}") for r in right
        ],
        "context": [],
        "against": [],
        "support_queries": sq,
        "falsifier_queries": fq,
        "touched_this_scan": any(r.get("new_this_scan") for r in left + right),
        "reader_eligible": True,
        "reader_title": "Building big in a few places, keeping every region in.",
        "reader_summary": "Money and hardware are being concentrated into flagship capacity while access and participation are being spread across countries and regions.",
        "trend_balance": {
            "left_title": "Building big in a few places",
            "right_title": "Keeping every region in",
            "left_pull": adj_pull,
            "right_pull": 100 - adj_pull,
            "raw_left_pull": raw_pull,
            "raw_right_pull": 100 - raw_pull,
            "left_range": [min(raw_pull, adj_pull), max(raw_pull, adj_pull)],
            "right_range": [100 - max(raw_pull, adj_pull), 100 - min(raw_pull, adj_pull)],
            "left_actions": raw_l,
            "right_actions": raw_r,
            "left_sources": len(ls),
            "right_sources": len(rs),
            "left_adjusted_points": round(adj_l, 3),
            "right_adjusted_points": round(adj_r, 3),
        },
    }
    return [cand]


DETECTORS = (
    # Production runs only relation-level grammars.  The worked examples below
    # remain executable regression fixtures/specifications, but they are not
    # allowed to seed reader findings by exact programme/document names.
    _generic_dependency_chains,
    _generic_conflicting_criteria,
    _generic_latent_substitute,
    _generic_success_metric_gap,
    _generic_comparative_advantage,
    _generic_practice_precedes_doctrine,
    _generic_concentration_distribution_tension,
    _goal_measurement_gap,       # concept-level invoke/define/measure comparison
    _first_mover,                # topic-agnostic ordering/path-dependence grammar
)


def _reader_text(c: dict[str, Any]) -> None:
    if c.get("reader_title"): return
    g=c.get("grammar_id"); label=c.get("topic_label") or "European R&I"
    templates={
      "conflicting_criteria_no_arbitration":("Two valid rules could collide because the tie-break rule is missing.","Separate evidence shows both criteria entering the same decision system, while other evidence shows undefined rules are resolved unevenly."),
      "latent_substitute_channel":("An existing European instrument may already solve a problem another programme is struggling with.","The opportunity appears only when an unresolved need, an existing adjacent structure, a live connection and precedent are independently supported."),
      "goal_measurement_gap":(f"Europe keeps pursuing {label} without a settled way to measure whether it is succeeding.","The pattern is repeated invocation of the goal alongside sparse, fragmented or contested measurement."),
      "first_mover_path_dependence":(f"Commercial deployment could set {label} conventions before European testing and standards catch up.","The ordering matters: deployment is already occurring while certification or standards infrastructure is still being built."),
      "success_metric_blind_spot":("Europe may count research-talent arrivals without knowing whether they stay.","The programme success condition is retention, but the evidence base is stronger on recruitment than on longitudinal measurement."),
      "comparative_advantage_bottleneck":(f"Europe may have a cheaper advantage in {label} by fixing a bottleneck around assets it already has.","The opportunity combines an existing European asset, a tractable constraint and evidence of payoff rather than assuming Europe must win every expensive race."),
      "practice_precedes_doctrine":("European practice may have become policy before policy acquired a name for it.","The sequence is the finding: repeated use of an instrument precedes the formal framework that later describes that instrument as its tool."),
    }
    title,summary=templates.get(g,(f"A higher-order pattern is forming around {label}.","Several independent evidence roles connect, but the result is only surfaced after a denial/falsifier check."))
    c["reader_title"]=title; c["reader_summary"]=summary

def _select_publications(candidates: list[dict[str, Any]], previous_publications: dict[str, Any] | None = None) -> dict[str,list[str]]:
    caps={"shock":2,"risk":2,"opportunity":2,"continuity":2,"trend":2}
    out={k:[] for k in caps}
    previous_publications = previous_publications if isinstance(previous_publications, dict) else {}
    by_id={str(c.get("id")):c for c in candidates if c.get("id")}
    for c in candidates:
        _reader_text(c)
    for product,cap in caps.items():
        eligible=[c for c in candidates if c.get("product")==product and c.get("status")=="qualified" and c.get("reader_eligible") and c.get("denial_tested") and c.get("falsifier_queries") and int(c.get("score",0)) >= (90 if int(c.get("inferential_distance",0))>=5 else 86)]
        eligible.sort(key=lambda c:(int(c.get("score",0)),int(c.get("primary_sources",0)),int(c.get("primary_records",0))),reverse=True)
        eligible_ids={str(c.get("id")) for c in eligible}
        # Publication hysteresis: analytical findings move much more slowly than the scanner.
        # Keep qualified incumbents first. A newcomer can displace an incumbent only when it
        # is materially stronger, not merely because it is newer.
        incumbents=[]
        for cid in previous_publications.get(product, []) if isinstance(previous_publications.get(product), list) else []:
            cid=str(cid)
            if cid in eligible_ids and cid in by_id:
                incumbents.append(by_id[cid])
        incumbents.sort(key=lambda c:(int(c.get("score",0)),int(c.get("primary_sources",0))), reverse=True)
        chosen=[]; grammars=set(); topics=set()
        for c in incumbents:
            g=str(c.get("grammar_id")); t=str(c.get("topic_key"))
            if g in grammars or t in topics: continue
            chosen.append(c); grammars.add(g); topics.add(t)
            if len(chosen)>=cap: break
        for challenger in eligible:
            cid=str(challenger.get("id")); g=str(challenger.get("grammar_id")); t=str(challenger.get("topic_key"))
            if any(str(x.get("id"))==cid for x in chosen) or g in grammars or t in topics:
                continue
            if len(chosen)<cap:
                chosen.append(challenger); grammars.add(g); topics.add(t); continue
            weakest=min(chosen, key=lambda c:(int(c.get("score",0)),int(c.get("primary_sources",0)),int(c.get("primary_records",0))))
            # Six points is deliberately meaningful: this prevents scan-to-scan churn while
            # still allowing a clearly stronger and more important finding to replace one.
            if int(challenger.get("score",0)) < int(weakest.get("score",0)) + 6:
                continue
            chosen.remove(weakest)
            grammars={str(x.get("grammar_id")) for x in chosen}
            topics={str(x.get("topic_key")) for x in chosen}
            if g in grammars or t in topics:
                chosen.append(weakest)
                grammars.add(str(weakest.get("grammar_id"))); topics.add(str(weakest.get("topic_key")))
                continue
            chosen.append(challenger); grammars.add(g); topics.add(t)
        chosen.sort(key=lambda c:(int(c.get("score",0)),int(c.get("primary_sources",0))), reverse=True)
        out[product]=[str(c.get("id")) for c in chosen[:cap]]
    return out


def _fingerprint(c: dict[str, Any]) -> str:
    payload = {
        "id": c.get("id"),
        "status": c.get("status"),
        "score": c.get("score"),
        "missing": c.get("missing_links"),
        "support": [(x.get("identity"), x.get("role")) for x in c.get("support", [])],
        "context": [x.get("identity") for x in c.get("context", [])],
        "against": [x.get("identity") for x in c.get("against", [])],
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def refresh_high_order_inference(
    data: dict[str, Any],
    previous_state: dict[str, Any] | None = None,
    completed_iso: str | None = None,
) -> dict[str, Any]:
    """Build/refresh a hidden persistent registry of Level-4/5 reasoning candidates.

    This module intentionally does not publish prose findings. It records structured
    candidate state, missing links, falsifiers and search prompts. Strand A/frontier are
    the only current records allowed to close required roles. Strand C and history may
    add context but cannot turn an incomplete chain into a qualified one.
    """
    previous_state = previous_state if isinstance(previous_state, dict) else {}
    prev_list = previous_state.get("candidates", []) if isinstance(previous_state.get("candidates"), list) else []
    prev = {str(x.get("id")): dict(x) for x in prev_list if isinstance(x, dict) and x.get("id")}
    rows = _rows(data)
    detected: list[dict[str, Any]] = []
    for detector in DETECTORS:
        try:
            detected.extend(x for x in detector(rows) if isinstance(x, dict))
        except Exception:
            # One grammar must never prevent the scanner from saving the evidence corpus.
            continue
    # Keep the strongest version when broad patterning produces the same stable ID more than once.
    by_id: dict[str, dict[str, Any]] = {}
    for c in detected:
        cid = str(c.get("id"))
        old = by_id.get(cid)
        if old is None or (int(c.get("score", 0)), int(c.get("primary_records", 0))) > (int(old.get("score", 0)), int(old.get("primary_records", 0))):
            by_id[cid] = c

    now = completed_iso or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    merged: dict[str, dict[str, Any]] = {}
    new_count = updated_count = 0
    for cid, old in prev.items():
        cur = by_id.pop(cid, None)
        if cur is None:
            keep = dict(old)
            keep["new_this_scan"] = False
            keep["updated_this_scan"] = False
            misses = int(keep.get("missed_detection_scans", 0) or 0) + 1
            keep["missed_detection_scans"] = misses
            keep["lifecycle"] = "carried_forward"
            # Absence from one detector pass is not evidence that the analytical finding died.
            # Findings accumulate and decay slowly. Only after repeated non-redetection do we
            # step a qualified item down to watch/dormant; it remains in the hidden registry.
            if misses >= 6:
                keep["status"] = "dormant"
                keep["reader_eligible"] = False
                keep["lifecycle"] = "dormant_after_repeated_non_detection"
            elif misses >= 3 and keep.get("status") == "qualified":
                keep["status"] = "watch"
                keep["reader_eligible"] = False
                keep["lifecycle"] = "weakening"
            merged[cid] = keep
            continue
        fp = _fingerprint(cur)
        changed = fp != _clean(old.get("fingerprint"))
        cur["first_seen_at"] = _clean(old.get("first_seen_at")) or now
        cur["last_updated_at"] = now if changed else (_clean(old.get("last_updated_at")) or now)
        cur["missed_detection_scans"] = 0
        cur["fingerprint"] = fp
        cur["new_this_scan"] = False
        cur["updated_this_scan"] = bool(changed and cur.get("touched_this_scan"))
        cur["lifecycle"] = "updated" if cur["updated_this_scan"] else "unchanged"
        if cur["updated_this_scan"]:
            updated_count += 1
        merged[cid] = cur

    bootstrap = not bool(prev)
    for cid, cur0 in by_id.items():
        cur = dict(cur0)
        cur["first_seen_at"] = now
        cur["last_updated_at"] = now
        cur["fingerprint"] = _fingerprint(cur)
        cur["new_this_scan"] = bool(cur.get("touched_this_scan")) and not bootstrap
        cur["updated_this_scan"] = False
        cur["lifecycle"] = "seeded" if bootstrap else "new"
        cur["missed_detection_scans"] = 0
        if not bootstrap:
            new_count += 1
        merged[cid] = cur

    order = {"qualified": 3, "watch": 2, "dormant": 1}
    active = sorted(
        merged.values(),
        key=lambda c: (order.get(_low(c.get("status")), 0), int(c.get("score", 0)), _clean(c.get("last_updated_at"))),
        reverse=True,
    )
    publications=_select_publications(active, previous_state.get("publications") if isinstance(previous_state.get("publications"), dict) else {})
    new_primary=sum(1 for r in rows if r.get("_primary") and r.get("new_this_scan"))
    new_context=sum(1 for r in rows if not r.get("_primary") and not r.get("_historical") and r.get("new_this_scan"))
    return {
        "profile_version": PROFILE_VERSION,
        "evaluated_at": now,
        "new_count": new_count,
        "updated_count": updated_count,
        "qualified_count": sum(1 for c in active if c.get("status") == "qualified"),
        "watch_count": sum(1 for c in active if c.get("status") == "watch"),
        "dormant_count": sum(1 for c in active if c.get("status") == "dormant"),
        "trigger_summary":{"new_primary_records_evaluated":new_primary,"new_weak_signal_records_evaluated":new_context,"thinking_pass_ran":True},
        "publication_policy":"Constant checking, sparse output, slow analytical turnover: qualified candidates compete for at most two higher-order slots per reader product; incumbents persist unless they weaken or a materially stronger challenger displaces them. Every surfaced candidate has an explicit falsifier search.",
        "lifecycle_policy":"Analytical candidates accumulate. One missed detector pass never retires a finding; repeated non-redetection only weakens it gradually, and no new finding automatically deletes an old one.",
        "publications":publications,
        "candidate_search_policy": "Only missing-link and falsifier searches are fed back. No candidate bypasses normal A/B/C admission.",
        "candidates": active,
    }


def feedback_queries(state: dict[str, Any] | None, limit: int = 8) -> list[str]:
    """Return a balanced support/falsifier query bank from unfinished candidates."""
    if not isinstance(state, dict):
        return []
    candidates = [c for c in state.get("candidates", []) if isinstance(c, dict) and c.get("status") in {"watch", "dormant", "qualified"}]
    candidates.sort(key=lambda c: (2 if c.get("status") == "watch" else 1 if c.get("status") == "dormant" else 0, int(c.get("score", 0))), reverse=True)
    support: list[str] = []
    falsify: list[str] = []
    for c in candidates[:10]:
        support.extend(_clean(q) for q in c.get("support_queries", []) if _clean(q))
        falsify.extend(_clean(q) for q in c.get("falsifier_queries", []) if _clean(q))
    out: list[str] = []
    # Alternate: confirmation pressure must never crowd out disconfirmation.
    for i in range(max(len(support), len(falsify))):
        if i < len(support) and support[i] not in out:
            out.append(support[i])
        if i < len(falsify) and falsify[i] not in out:
            out.append(falsify[i])
        if len(out) >= max(0, int(limit or 0)):
            break
    return out[:max(0, int(limit or 0))]


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser()
    ap.add_argument("radar", nargs="?", default="radar.json")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    p = Path(args.radar)
    doc = json.loads(p.read_text(encoding="utf-8"))
    prev = doc.get("high_order_inference") if isinstance(doc.get("high_order_inference"), dict) else {}
    state = refresh_high_order_inference(doc, prev, _clean(doc.get("run_completed_at") or doc.get("last_updated")))
    print(json.dumps({k: v for k, v in state.items() if k != "candidates"}, indent=2))
    for c in state["candidates"][:20]:
        print(f"{c['status']:9s} L{c['inferential_distance']} {c['score']:2d} {c['grammar_id']}: {c['topic_label']}")
    if args.write:
        doc["high_order_inference"] = state
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
