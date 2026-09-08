"""Cross-evidence external-shock inference for the reader.

This is deliberately separate from strict realised-shock filing.  It looks for a
European R&I capability/exposure in one set of sources and a fast external
mechanism in another, then keeps a persistent registry so a scan can say which
hypotheses are NEW, UPDATED or unchanged.

The engine is recall-first but evidence-weighted: a hypothesis needs multiple
independent sources, a strong publication anchor, and a plausible capability ×
external-mechanism coupling.  It never manufactures a shock merely to make a
non-zero count.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable

PROFILE_VERSION = "23.3-context-weighted-shocks-v3"


def _clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def _low(v: Any) -> str:
    return _clean(v).lower()


def _text(x: dict[str, Any]) -> str:
    parts = [
        x.get("title"), x.get("headline"), x.get("core_message"), x.get("summary"),
        x.get("relevance_note"), x.get("why_it_matters"), x.get("bridge_sentence"),
        " ".join(x.get("geo_evidence") or []) if isinstance(x.get("geo_evidence"), list) else "",
        " ".join(x.get("ri_evidence") or []) if isinstance(x.get("ri_evidence"), list) else "",
        " ".join(x.get("a_context_evidence") or []) if isinstance(x.get("a_context_evidence"), list) else "",
    ]
    return _low(" ".join(_clean(p) for p in parts if p))


def _identity(x: dict[str, Any]) -> str:
    link = _clean(x.get("link") or x.get("url"))
    if link:
        return "url:" + link.lower().rstrip("/")
    title = _low(x.get("title") or x.get("headline") or x.get("what"))
    source = _low(x.get("source") or x.get("journal") or x.get("institution"))
    return "txt:" + hashlib.sha1(f"{title}|{source}".encode("utf-8")).hexdigest()[:20]


def _quality(x: dict[str, Any]) -> int:
    """Compact Python mirror of the reader's source/evidence ranking.

    It is intentionally conservative: Tier-1 institutions and priority journals
    anchor inference; lower-ranked material can corroborate but cannot lead.
    """
    tier = _low(x.get("source_tier") or x.get("sourceTier"))
    typ = _low(x.get("type") or x.get("itemType") or x.get("signal_kind") or x.get("signal_type"))
    source = _clean(x.get("source") or x.get("journal") or x.get("institution"))
    strand = _clean(x.get("_strand") or x.get("strand")).upper()
    try:
        merit = int(round(float(x.get("source_merit_score")))) if x.get("source_merit_score") not in (None, "") else 0
    except Exception:
        merit = 0

    if merit:
        score = max(0, min(100, merit))
    elif "tier 1" in tier:
        score = 96
    elif "priority journal" in tier:
        score = 94
    elif "trusted-publisher journal" in tier:
        score = 90
    elif "tier 2 comparable" in tier:
        score = 88
    elif "tier 2" in tier:
        score = 86
    elif "broad journal" in tier:
        score = 84
    elif "tier 3" in tier:
        score = 72
    else:
        if re.search(r"financial times|reuters|nature|science\|business|politico|research professional|the economist", source, re.I):
            score = 90
        elif strand == "C":
            score = 80
        else:
            score = 78

    if re.search(r"peer-reviewed|institutional report|formal study|research/policy paper|official policy", typ):
        score += 2
    return max(0, min(100, score))


ASSETS: dict[str, tuple[str, str]] = {
    "compute": (r"\b(ai gigafactor|supercomput|eurohpc|high[- ]performance comput|compute capacity|frontier compute|cloud and ai)\b", "shared research computing"),
    "chips": (r"\b(semiconductor|microelectron|advanced chip|chip supply|pilot line)\b", "semiconductor research and chip development"),
    "critical_materials": (r"\b(critical raw material|critical mineral|rare earth|gallium|germanium|graphite|lithium|cobalt)\b", "critical materials used by research and industry"),
    "measurement": (r"\b(bibliometr|scopus|openalex|research assessment|innovation scoreboard|widening indicator|research information|publication data)\b", "research measurement and assessment"),
    "talent": (r"\b(research talent|researcher mobility|brain drain|brain gain|research careers|scientists? leaving|attract researchers|retain researchers)\b", "research talent"),
    "collaboration": (r"\b(international research collaboration|research cooperation|science diplomacy|horizon europe association|associated countr|scientific cooperation|academic cooperation)\b", "international research collaboration"),
    "infrastructure": (r"\b(research infrastructure|shared facilit|research facility|eosc|data infrastructure|laborator(?:y|ies))\b", "research infrastructures"),
    "biotech": (r"\b(biotech|biotechnolog|biosecurity|life science|clinical trial|health data)\b", "biotechnology and clinical research"),
    "startups": (r"\b(startup|scale[- ]?up|venture capital|deep tech|eic accelerator|eic fund)\b", "technology companies trying to grow in Europe"),
    "space": (r"\b(space research|space technolog|satellite|earth observation|galileo|copernicus)\b", "space R&I"),
    "open_science": (r"\b(open science|open access|open research information|data sharing|research data)\b", "open science and research data"),
    "standards": (r"\b(standardisation|standardization|technology standards|interoperab|certification)\b", "standards and interoperability"),
    "funding": (r"\b(horizon europe|framework programme|fp10|research funding|r&d funding|innovation funding|erc grant|eic)\b", "European research and innovation funding"),
    "ip": (r"\b(intellectual property|patent|technology transfer|knowledge transfer|trade secret)\b", "research ownership and technology transfer"),
    "quantum": (r"\bquantum\b", "quantum research and technology"),
}

PRESSURES: dict[str, tuple[str, str, str]] = {
    "export_restriction": (r"\b(export control|export restriction|export ban|technology restriction|trade restriction)\b", "an external export restriction", "An export restriction abruptly cuts Europe’s access to {asset}"),
    "legal_order": (r"\b(extraterritorial|third-country law|foreign jurisdiction|legal order|data localisation|data localization)\b", "a third-country legal order", "A third-country legal order suddenly makes part of Europe’s {asset} unusable"),
    "cyber": (r"\b(cyberattack|cyber attack|ransomware|cybersecurity risk|software vulnerab|digital outage)\b", "a cyber or software outage", "A cyber incident knocks out a shared layer of Europe’s {asset}"),
    "energy": (r"\b(energy supply disruption|electricity shortage|power outage|energy crisis|energy price shock|grid constraint|electricity rationing)\b", "an energy-supply shock", "An energy shock rations Europe’s {asset}"),
    "conflict": (r"\b(armed conflict|war\b|war-|invasion|military escalation|geopolitical conflict)\b", "an armed-conflict escalation", "A conflict escalation severs Europe’s access to {asset}"),
    "partner_restriction": (r"\b(restrictions?.{0,45}(research collaboration|international collaboration|grant|participation)|participation ban|grant restriction|research security screening|knowledge security screening)\b", "a partner-country restriction", "A partner-country rule change abruptly closes part of Europe’s {asset}"),
    "acquisition": (r"\b(foreign acquisition|foreign ownership|takeover|investment screening|foreign investment screening)\b", "a foreign acquisition or control transfer", "A foreign acquisition moves control of Europe’s {asset} outside the system"),
    "commercial": (r"\b(repricing|commercial provider|proprietary database|vendor lock|market withdrawal|service withdrawal|licen[cs]e restriction)\b", "a commercial withdrawal or repricing", "A commercial provider reprices or withdraws a layer Europe’s {asset} depends on"),
    "sanctions": (r"\b(sanction|asset freeze|financial restriction|payment restriction)\b", "sanctions or financial restrictions", "Sanctions make part of Europe’s {asset} operationally unreachable"),
    "supply_chain": (r"\b(supply chain disruption|supply shortage|single supplier|supplier concentration|import dependence|strategic depend|critical depend)\b", "a supply-chain interruption", "A supply-chain break removes a no-substitute input from Europe’s {asset}"),
    "data_access": (r"\b(data access restriction|data transfer restriction|data flow restriction|cross-border data|data sovereignty|data localisation|data localization)\b", "a cross-border data-access restriction", "A cross-border data restriction breaks Europe’s {asset}"),
    "funding_cut": (r"\b(funding cut|budget cut|withdraw funding|funding withdrawal|programme suspension|grant suspension)\b", "an abrupt funding withdrawal", "An abrupt funding withdrawal strands Europe’s {asset}"),
    "security_reclassification": (r"\b(research security|knowledge security|dual[- ]use|dual use|sensitive research|biosecurity|foreign interference)\b", "a sudden security reclassification", "A security reclassification abruptly narrows access to Europe’s {asset}"),
}

# Combinations already represented by the hand-built direct/reasoned library.
# They remain useful there; the emergent layer should add genuinely new seams.
STATIC_OVERLAPS = {
    ("compute", "cyber"), ("infrastructure", "cyber"),
    ("chips", "export_restriction"), ("critical_materials", "export_restriction"), ("compute", "export_restriction"),
    ("infrastructure", "conflict"), ("collaboration", "conflict"),
    ("collaboration", "partner_restriction"),
    ("measurement", "legal_order"), ("measurement", "commercial"),
    ("compute", "energy"), ("startups", "acquisition"),
    ("open_science", "security_reclassification"), ("standards", "legal_order"),
}


ASSET_COUNTER_PATTERNS: dict[str, str] = {
    "compute": r"\b(eurohpc|federation platform|ai gigafactor|european compute|supercomput)\b",
    "chips": r"\b(chips act|pilot line|semiconductor capacity|microelectronics capacity)\b",
    "critical_materials": r"\b(critical raw materials act|diversif|recycl|substitut|alternative supplier)\b",
    "measurement": r"\b(openalex|barcelona declaration|open research information|open science monitoring)\b",
    "talent": r"\b(choose europe for science|fifth freedom|attract and retain|research careers|brain gain)\b",
    "collaboration": r"\b(science diplomacy|horizon europe association|international cooperation|global approach to research)\b",
    "infrastructure": r"\b(open access to .*research infrastructure|shared research infrastructure|federat|eosc)\b",
    "biotech": r"\b(biotech act|european health data space|federated health data|coordinated clinical trial network|biomanufactur)\b",
    "startups": r"\b(step scale up|eic fund|eic accelerator|scaleup europe|venture capital initiative)\b",
    "space": r"\b(copernicus|galileo|iris2|european space|space programme)\b",
    "open_science": r"\b(open research information|barcelona declaration|eosc|open science)\b",
    "standards": r"\b(interoperab|standardisation strategy|standardization strategy|common standard)\b",
    "funding": r"\b(framework programme|horizon europe|fp10|multiannual financial framework|research funding)\b",
    "ip": r"\b(unitary patent|technology transfer office|knowledge valorisation|knowledge valorization)\b",
    "quantum": r"\b(eurohpc.*quantum|quantum testing infrastructure|quantum flagship|european quantum)\b",
}
RESILIENCE_RE = re.compile(
    r"\b(diversif|substitut|alternative supplier|strategic autonomy|resilien|federat|redundan|back[- ]?up|"
    r"domestic capacity|european capacity|build[- ]out|new capacity|open source|open research information|"
    r"association agreement|science diplomacy|stockpil|mitigat|safeguard|retain|attract|interoperab)\b",
    re.I,
)

# Passport-style challenge layer. A shock is not only built from evidence that points
# toward it. The engine also records what would have to be true, what in the same
# corpus pushes the other way, what could prevent the shock, and which observable
# changes would strengthen or weaken the hypothesis. These fields are written for
# audit/read-more use; the easiest pages only show short plain-language selections.
OFFICIAL_TRIGGER_RE = re.compile(
    r"\b(European Commission|Council of the European Union|European Parliament|EUR-Lex|"
    r"Bureau of Industry and Security|Federal Register|Department of Commerce|U\.?S\.? Treasury|"
    r"White House|UK Government|Department for Science|national government|ministry|regulator|authority)\b",
    re.I,
)
OFFICIAL_TYPE_RE = re.compile(r"\b(official|regulation|decision|consultation|government|policy|guidance|law|legislation)\b", re.I)

ASSET_PREVENTION_ACTIONS: dict[str, list[str]] = {
    "compute": [
        "Keep more than one usable route to shared computing capacity.",
        "Build European alternatives for critical hardware and services before they are urgently needed.",
        "Agree common European access rules before a crisis forces emergency screening.",
    ],
    "chips": [
        "Qualify alternative chip suppliers before a restriction removes the preferred source.",
        "Expand European chip production and testing capacity where the dependency is most concentrated.",
        "Design research programmes so critical experiments are not tied to one supplier.",
    ],
    "critical_materials": [
        "Diversify suppliers and qualify substitutes before a shortage reaches laboratories and factories.",
        "Increase recycling, stockpiles and European production for the hardest-to-replace materials.",
    ],
    "measurement": [
        "Keep open European alternatives ready before a commercial research-data service becomes unavailable.",
        "Avoid putting essential funding or assessment decisions on one data provider.",
    ],
    "talent": [
        "Improve long-term research careers so recruited scientists can stay through a disruption.",
        "Use common European mobility and screening rules instead of many conflicting national responses.",
    ],
    "collaboration": [
        "Keep several international partnership routes open so one rule change does not stop a whole programme.",
        "Agree common European safeguards that protect research without closing ordinary cooperation.",
    ],
    "infrastructure": [
        "Maintain alternative facilities and access routes for projects that depend on shared infrastructure.",
        "Avoid a single access system becoming the only route into several European facilities.",
    ],
    "biotech": [
        "Keep compliant European data and trial routes available when an outside provider or jurisdiction is blocked.",
        "Build enough cross-border European capacity that one country or provider is not indispensable.",
    ],
    "startups": [
        "Give growing European technology firms enough capital and customers to avoid a forced outside sale.",
        "Use investment safeguards without cutting firms off from the financing they need to scale.",
    ],
    "space": [
        "Keep alternative suppliers, launch routes and data services available for critical European space work.",
        "Build European replacements for components or services that cannot be substituted quickly today.",
    ],
    "open_science": [
        "Separate genuinely sensitive research from ordinary open research instead of using blanket restrictions.",
        "Use common European safeguards so institutions do not create incompatible access rules.",
    ],
    "standards": [
        "Build enough European technical capacity to implement standards without relying on one outside provider.",
        "Keep interoperable alternatives available when a foreign rule changes access conditions.",
    ],
    "funding": [
        "Avoid sudden funding gaps for capabilities that cannot pause without losing people or infrastructure.",
        "Keep European and national funding routes coordinated when one programme is disrupted.",
    ],
    "ip": [
        "Use clear European ownership and transfer rules before a crisis forces hurried restrictions.",
        "Keep more than one route for lawful technology transfer and collaboration.",
    ],
    "quantum": [
        "Build multiple European routes to quantum hardware, testing and specialist skills.",
        "Avoid tying critical projects to one supplier, facility or foreign access rule.",
    ],
}

PRESSURE_PREVENTION_ACTIONS: dict[str, list[str]] = {
    "export_restriction": ["Secure alternative suppliers and licences before a new export rule takes effect."],
    "legal_order": ["Keep critical European data and technology on routes that remain usable under European law."],
    "cyber": ["Maintain tested backup access and recovery routes for shared services."],
    "energy": ["Protect critical research facilities with backup power and prioritised supply arrangements."],
    "conflict": ["Prepare relocation, remote-access and project-transfer plans before a research corridor closes."],
    "partner_restriction": ["Design international projects so one partner's rule change cannot make the whole project unusable."],
    "acquisition": ["Use investment safeguards early enough that control does not move before alternatives are ready."],
    "commercial": ["Avoid one commercial provider becoming the only route to a critical research service."],
    "sanctions": ["Keep lawful payment, data and equipment routes diversified across partners."],
    "supply_chain": ["Qualify substitutes before a concentrated supply chain breaks."],
    "data_access": ["Keep a compliant European route for essential research data and analysis."],
    "funding_cut": ["Phase funding changes so irreplaceable teams and facilities are not stranded suddenly."],
    "security_reclassification": ["Use common, targeted screening rules rather than broad restrictions that fragment European access."],
}

PRESSURE_WATCH: dict[str, list[str]] = {
    "export_restriction": [
        "A government expands export restrictions to inputs used by European research.",
        "European projects report delayed or denied licences for the affected input.",
    ],
    "legal_order": [
        "A foreign law or court order is applied to technology or data used by European research.",
        "European providers add new nationality, location or legal-access conditions.",
    ],
    "cyber": [
        "A shared European research service reports a serious security breach or prolonged outage.",
        "Several projects lose access through the same software or identity layer.",
    ],
    "energy": [
        "Large research facilities face power limits, rationing or exceptional energy costs.",
        "Projects change schedules because electricity supply is no longer reliable enough.",
    ],
    "conflict": [
        "A research corridor closes, staff are evacuated, or facilities become inaccessible.",
        "European partners take over work that can no longer be carried out locally.",
    ],
    "partner_restriction": [
        "A major partner narrows who can join grants, projects or research data exchanges.",
        "Existing European collaborations begin changing staff, contracts or data routes to comply.",
    ],
    "acquisition": [
        "A foreign buyer seeks control of a European firm or facility holding a scarce research capability.",
        "Investment screening is opened because the capability is considered strategically important.",
    ],
    "commercial": [
        "A critical provider sharply raises prices, changes licences or announces withdrawal.",
        "European institutions begin emergency moves to alternative services.",
    ],
    "sanctions": [
        "New sanctions block payments, equipment, cloud services or other project inputs.",
        "A formally active collaboration can no longer perform ordinary project transactions.",
    ],
    "supply_chain": [
        "A concentrated supplier cuts deliveries or lead times rise sharply for a no-substitute input.",
        "European projects delay tests or production because an input cannot be replaced quickly.",
    ],
    "data_access": [
        "A provider or government restricts cross-border access to data used by European research.",
        "Projects stop pooling or analysing data that previously moved across borders.",
    ],
    "funding_cut": [
        "A major research programme is cut, suspended or redirected with little transition time.",
        "Teams begin closing facilities, ending contracts or cancelling planned work because money stops.",
    ],
    "security_reclassification": [
        "Research previously treated as open is moved into a more restricted security category.",
        "Different European countries apply materially different access decisions to the same work.",
    ],
}


def _official_trigger(x: dict[str, Any]) -> bool:
    source = _clean(x.get("source") or x.get("journal") or x.get("institution"))
    typ = _clean(x.get("type") or x.get("signal_kind") or x.get("signal_type"))
    tier = _low(x.get("source_tier") or x.get("sourceTier"))
    return bool(OFFICIAL_TRIGGER_RE.search(source) or ("tier 1" in tier and OFFICIAL_TYPE_RE.search(typ)))


def _unique_text(items: Iterable[str], limit: int = 6) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        text = _clean(raw)
        key = _low(text)
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out



def _rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Build substantive inference rows with explicit evidence roles.

    Strand B is intentionally absent: it is a methods library. Strand C and trusted-media
    strategic-pathway rows are contextual evidence only. Historical Strand-A rows are also
    contextual and can never be marked fresh.
    """
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    weights = data.get("shock_inference_weights") if isinstance(data.get("shock_inference_weights"), dict) else {}
    try:
        weak_weight = max(0.0, min(1.0, float(weights.get("weak_signal", 0.30))))
    except Exception:
        weak_weight = 0.30
    try:
        historical_weight = max(0.0, min(1.0, float(weights.get("historical_context", 0.45))))
    except Exception:
        historical_weight = 0.45

    for key, prefix in (
        ("strand_a", "A"),
        ("strand_c", "C"),
        ("strategic_pathways", "P"),
        ("historical_context", "H"),
    ):
        xs = data.get(key, [])
        if not isinstance(xs, list):
            continue
        for i, raw in enumerate(xs, 1):
            if not isinstance(raw, dict):
                continue
            ident = _identity(raw)
            if ident in seen:
                continue
            seen.add(ident)
            row = dict(raw)
            row["_row"] = f"{prefix}{i:03d}"
            row["_strand"] = prefix
            row["_identity"] = ident
            role = _low(row.get("evidence_role"))
            basis = _low((row.get("source_quality_gate") or {}).get("basis") if isinstance(row.get("source_quality_gate"), dict) else "")
            if prefix == "H":
                evidence_weight = historical_weight
                context_kind = "historical"
                row["new_this_scan"] = False
            elif prefix == "C" or row.get("context_only") or role in {"weak_signal", "weak signal", "weak_signal_context", "weak signal context"} or (not role and basis == "configured_current_event_source"):
                try:
                    evidence_weight = float(row.get("analytical_weight", weak_weight) or weak_weight)
                except Exception:
                    evidence_weight = weak_weight
                evidence_weight = max(0.0, min(weak_weight, evidence_weight))
                context_kind = "weak_signal"
            else:
                evidence_weight = 1.0
                context_kind = "primary"
            row["_evidence_weight"] = evidence_weight
            row["_context_kind"] = context_kind
            row["_primary_evidence"] = bool(evidence_weight >= 0.999 and context_kind == "primary")
            row["_quality"] = _quality(row)
            row["_text"] = _text(row)
            out.append(row)
    return out


def _match(pattern: str, x: dict[str, Any]) -> bool:
    return bool(re.search(pattern, x.get("_text", ""), re.I))


def _dedupe_pick(rows: Iterable[dict[str, Any]], limit: int, prefer_new: bool = False, focus_pattern: str | None = None) -> list[dict[str, Any]]:
    rows = list(rows)
    rows.sort(
        key=lambda x: (
            1 if (prefer_new and x.get("new_this_scan")) else 0,
            1 if (focus_pattern and re.search(focus_pattern, _low(x.get("title") or x.get("headline")), re.I)) else 0,
            int(x.get("_quality", 0)),
            str(x.get("date") or ""),
        ),
        reverse=True,
    )
    out: list[dict[str, Any]] = []
    sources: set[str] = set()
    titles: set[str] = set()
    for x in rows:
        source = _low(x.get("source") or x.get("journal") or x.get("institution"))
        title = _low(x.get("title") or x.get("headline") or x.get("what"))
        if title and title in titles:
            continue
        # Prefer source diversity but do not require it until selection is complete.
        if source and source in sources and len(out) >= 2:
            continue
        out.append(x)
        if source:
            sources.add(source)
        if title:
            titles.add(title)
        if len(out) >= limit:
            break
    return out


def _snapshot(x: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "identity": x.get("_identity") or _identity(x),
        "row": x.get("_row", ""),
        "strand": x.get("_strand", ""),
        "role": role,
        "evidence_role": _clean(x.get("evidence_role") or x.get("_context_kind") or "primary_evidence"),
        "analytical_weight": round(float(x.get("_evidence_weight", 1.0) or 0.0), 2),
        "title": _clean(x.get("title") or x.get("headline") or x.get("what") or "Evidence"),
        "source": _clean(x.get("source") or x.get("journal") or x.get("institution")),
        "date": _clean(x.get("date")),
        "link": _clean(x.get("link") or x.get("url")),
        "quality": int(x.get("_quality", _quality(x))),
        "new_this_scan": bool(x.get("new_this_scan")),
        "core_message": _clean(x.get("core_message") or x.get("summary") or x.get("relevance_note") or x.get("reader_point"))[:800],
        "geo_evidence": list(x.get("geo_evidence") or [])[:4] if isinstance(x.get("geo_evidence"), list) else [],
        "ri_evidence": list(x.get("ri_evidence") or [])[:4] if isinstance(x.get("ri_evidence"), list) else [],
        "a_context_evidence": list(x.get("a_context_evidence") or [])[:4] if isinstance(x.get("a_context_evidence"), list) else [],
    }


def _candidate(asset_id: str, pressure_id: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if (asset_id, pressure_id) in STATIC_OVERLAPS:
        return None
    asset_pattern, asset_label = ASSETS[asset_id]
    pressure_pattern, pressure_label, title_template = PRESSURES[pressure_id]
    asset_rows = [x for x in rows if _match(asset_pattern, x)]
    pressure_rows = [x for x in rows if _match(pressure_pattern, x)]
    if not asset_rows or not pressure_rows:
        return None

    coupling = [x for x in asset_rows if _match(pressure_pattern, x)]
    primary_asset = [x for x in asset_rows if x.get("_primary_evidence")]
    primary_pressure = [x for x in pressure_rows if x.get("_primary_evidence")]
    primary_coupling = [x for x in coupling if x.get("_primary_evidence")]
    # Context may corroborate an already-supported seam, but cannot supply a missing primary
    # capability, pressure or coupling.
    if not primary_asset or not primary_pressure or not primary_coupling:
        return None

    touched = [
        x for x in asset_rows + pressure_rows
        if x.get("new_this_scan") and x.get("_context_kind") != "historical"
    ]
    if not touched:
        return None
    # NEW shocks require fresh primary coupling. A new C/news item can update an existing
    # hypothesis but cannot create one.
    fresh_coupling = any(x.get("new_this_scan") for x in primary_coupling)

    chosen_primary: list[tuple[dict[str, Any], str]] = []
    chosen_context: list[tuple[dict[str, Any], str]] = []
    used: set[str] = set()

    def add_primary(pool: Iterable[dict[str, Any]], role: str, limit: int, prefer_new: bool = False, focus_pattern: str | None = None) -> None:
        for x in _dedupe_pick(pool, limit=limit, prefer_new=prefer_new, focus_pattern=focus_pattern):
            ident = str(x.get("_identity"))
            if ident in used:
                continue
            used.add(ident)
            chosen_primary.append((x, role))

    def add_context(pool: Iterable[dict[str, Any]], role: str, limit: int, prefer_new: bool = False, focus_pattern: str | None = None) -> None:
        for x in _dedupe_pick(pool, limit=limit, prefer_new=prefer_new, focus_pattern=focus_pattern):
            ident = str(x.get("_identity"))
            if ident in used:
                continue
            used.add(ident)
            chosen_context.append((x, role))

    add_primary([x for x in primary_coupling if x.get("new_this_scan")], "New primary coupling evidence", 1, True, asset_pattern)
    add_primary([x for x in touched if x.get("_primary_evidence")], "New primary evidence", 1, True, asset_pattern)
    add_primary(primary_coupling, "Capability × external mechanism", 1, False, asset_pattern)
    add_primary(primary_asset, f"European capability: {asset_label}", 2, False, asset_pattern)
    add_primary(primary_pressure, f"External mechanism: {pressure_label}", 2, False, pressure_pattern)

    if len(chosen_primary) < 4:
        return None
    sources = {
        _low(x.get("source") or x.get("journal") or x.get("institution"))
        for x, _ in chosen_primary if _clean(x.get("source") or x.get("journal") or x.get("institution"))
    }
    if len(sources) < 3:
        return None
    qualities = [int(x.get("_quality", 0)) for x, _ in chosen_primary]
    if max(qualities, default=0) < 90:
        return None
    avg = sum(qualities) / max(1, len(qualities))
    if avg < 82:
        return None
    if max((_quality(x) for x in primary_asset), default=0) < 88:
        return None
    if max((_quality(x) for x in primary_pressure), default=0) < 88:
        return None

    # Add only a small number of contextual rows after the primary gates have passed.
    weak_rows = [x for x in asset_rows + pressure_rows if x.get("_context_kind") == "weak_signal"]
    historical_rows = [x for x in asset_rows + pressure_rows if x.get("_context_kind") == "historical"]
    weak_coupling = [x for x in coupling if x.get("_context_kind") == "weak_signal"]
    historical_coupling = [x for x in coupling if x.get("_context_kind") == "historical"]
    add_context([x for x in weak_coupling if x.get("new_this_scan")], "Recent weak-signal corroboration", 1, True, asset_pattern)
    add_context(weak_rows, "Recent weak-signal context", 2, True, asset_pattern)
    add_context(historical_coupling, "Historical coupling context", 1, False, asset_pattern)
    add_context(historical_rows, "Historical structural context", 2, False, asset_pattern)

    asset_counter_re = re.compile(ASSET_COUNTER_PATTERNS.get(asset_id, r"$^"), re.I)
    counter_rows = [
        x for x in rows
        if x.get("_primary_evidence")
        and x.get("_identity") not in used
        and (
            asset_counter_re.search(x.get("_text", ""))
            or (_match(asset_pattern, x) and RESILIENCE_RE.search(x.get("_text", "")))
        )
    ]
    counters = _dedupe_pick(counter_rows, limit=5, prefer_new=True, focus_pattern=ASSET_COUNTER_PATTERNS.get(asset_id))

    official_pressure = [x for x in primary_pressure if _official_trigger(x)]
    pressure_sources = {
        _low(x.get("source") or x.get("journal") or x.get("institution"))
        for x in primary_pressure if _clean(x.get("source") or x.get("journal") or x.get("institution"))
    }
    coupling_sources = {
        _low(x.get("source") or x.get("journal") or x.get("institution"))
        for x in primary_coupling if _clean(x.get("source") or x.get("journal") or x.get("institution"))
    }

    weak_context_count = sum(1 for x, _ in chosen_context if x.get("_context_kind") == "weak_signal")
    historical_context_count = sum(1 for x, _ in chosen_context if x.get("_context_kind") == "historical")
    context_weight_total = sum(float(x.get("_evidence_weight", 0.0) or 0.0) for x, _ in chosen_context)
    context_strength = sum(
        float(x.get("_evidence_weight", 0.0) or 0.0) * (float(x.get("_quality", 0) or 0) / 100.0)
        for x, _ in chosen_context
    )

    title = title_template.format(asset=asset_label)
    plainly = (
        f"Europe relies on {asset_label}. Separate primary evidence shows that {pressure_label} can change access quickly. "
        "Recent weak signals and historical material may strengthen the context, but neither can establish the shock on its own."
    )
    second = "Projects may keep their grants and institutions but still lose time, access or usable capacity while a replacement is found."
    hidden = (
        "The hypothesis appears when durable European capability evidence and a separately evidenced external pressure are read as one chain; "
        "low-weight current signals and history are then used only as context."
    )
    conditions = [
        f"Europe materially depends on {asset_label} for current or planned work.",
        f"{pressure_label.capitalize()} reaches the supplier, service, partner or rule that the European capability depends on.",
        "Europe cannot substitute, reroute or absorb the change before projects begin losing usable capacity.",
    ]
    reasoning = [
        f"Primary retained evidence shows European reliance on or expansion of {asset_label}.",
        f"Separate primary retained evidence shows a live mechanism for {pressure_label}.",
        f"Primary evidence contains {len(primary_coupling)} direct capability × pressure coupling record(s).",
    ]
    if weak_context_count:
        reasoning.append(f"{weak_context_count} recent weak-signal item(s) point in the same direction; each is capped at 30% of a primary evidence item and none satisfies a primary threshold.")
    if historical_context_count:
        reasoning.append(f"{historical_context_count} historical Strand-A item(s) provide structural context; they cannot serve as the current trigger.")
    reasoning.append("The scenario becomes a shock only if the response is slower than the disruption.")

    case_against: list[str] = []
    if not official_pressure:
        case_against.append("The trigger is not yet backed by an official primary source in the retained current evidence.")
    if len(primary_coupling) == 1:
        case_against.append("Only one primary retained record currently links the European capability directly to the outside pressure.")
    if len(coupling_sources) <= 1:
        case_against.append("The primary direct connection is concentrated in one source, so independent confirmation is still weak.")
    if len(pressure_sources) <= 1:
        case_against.append("The primary pressure side is concentrated in one source and could reflect a narrow reading rather than a broad change.")
    if counters:
        case_against.append(f"The primary corpus contains {len(counters)} strong sign(s) of substitution, resilience or policy response that could absorb the shock.")
    if weak_context_count:
        case_against.append("Recent media/weak-signal corroboration is intentionally down-weighted and cannot substitute for primary evidence.")
    case_against.append("The scenario still depends on the disruption arriving faster than Europe can respond.")
    case_against = _unique_text(case_against, 7)

    prevention_actions = _unique_text(
        ASSET_PREVENTION_ACTIONS.get(asset_id, []) + PRESSURE_PREVENTION_ACTIONS.get(pressure_id, []),
        4,
    )
    watch_for = _unique_text(PRESSURE_WATCH.get(pressure_id, []), 4)

    support = [_snapshot(x, role) for x, role in (chosen_primary + chosen_context)[:10]]
    against = [_snapshot(x, "Primary evidence that could absorb or prevent the shock") for x in counters]

    base_score = min(100.0, avg * 0.70 + max(qualities) * 0.20 + min(10, len(sources) * 2))
    # Context is deliberately bounded. Even several strong weak signals/history items can only
    # move the score a few points; they never affect the primary admission gates above.
    context_bonus = min(5.0, context_strength * 3.0)
    challenge_penalty = 0
    if not official_pressure:
        challenge_penalty += 5
    if len(primary_coupling) == 1:
        challenge_penalty += 5
    if len(coupling_sources) <= 1:
        challenge_penalty += 3
    challenge_penalty += min(10, len(counters) * 2)
    score = round(max(0.0, min(100.0, base_score + context_bonus - challenge_penalty)))
    if score >= 88 and official_pressure and len(primary_coupling) >= 2:
        net_assessment = "Well supported enough to watch closely, with contextual signals reinforcing rather than carrying the case."
    elif score >= 80:
        net_assessment = "Plausible, but important parts of the primary trigger or connection still need confirmation."
    else:
        net_assessment = "An early hypothesis. Keep it visible only as a watch item until the primary evidence strengthens."

    cid = f"emergent:{asset_id}:{pressure_id}"
    return {
        "id": cid,
        "asset_id": asset_id,
        "pressure_id": pressure_id,
        "title": title,
        "plainly": plainly,
        "second_order": second,
        "why_easy_to_miss": hidden,
        "reasoning": reasoning,
        "conditions": conditions,
        "case_against": case_against,
        "prevention_actions": prevention_actions,
        "watch_for": watch_for,
        "net_assessment": net_assessment,
        "inference_score": int(score),
        "support": support,
        "against": against,
        "prevention_evidence": against,
        "source_count": len(sources),
        "primary_source_count": len(sources),
        "pressure_source_count": len(pressure_sources),
        "coupling_count": len(primary_coupling),
        "context_coupling_count": len([x for x in coupling if not x.get("_primary_evidence")]),
        "weak_signal_context_count": weak_context_count,
        "historical_context_count": historical_context_count,
        "context_weight_total": round(context_weight_total, 2),
        "context_score_bonus": round(context_bonus, 1),
        "official_trigger_present": bool(official_pressure),
        "best_quality": max(qualities),
        "average_quality": round(avg),
        "fresh_coupling": bool(fresh_coupling),
        "fresh_context": any(x.get("new_this_scan") for x, _ in chosen_context),
    }


def _fingerprint(c: dict[str, Any]) -> str:
    payload = {
        "id": c.get("id"),
        "support": [(x.get("identity"), x.get("analytical_weight")) for x in c.get("support", [])],
        "against": [x.get("identity") for x in c.get("against", [])],
        "case_against": list(c.get("case_against", [])),
        "official_trigger_present": bool(c.get("official_trigger_present")),
        "coupling_count": int(c.get("coupling_count", 0) or 0),
        "weak_signal_context_count": int(c.get("weak_signal_context_count", 0) or 0),
        "historical_context_count": int(c.get("historical_context_count", 0) or 0),
        "context_weight_total": c.get("context_weight_total"),
        "score": c.get("inference_score"),
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def refresh_shock_inference(
    data: dict[str, Any],
    previous_state: dict[str, Any] | None = None,
    completed_iso: str | None = None,
) -> dict[str, Any]:
    """Return a persistent NEW/UPDATED emergent-shock registry.

    New hypotheses are admitted only when this scan contributes relevant evidence.
    Previously inferred hypotheses are retained and can be updated by later scans.
    """
    previous_state = previous_state if isinstance(previous_state, dict) else {}
    prev_list = previous_state.get("dynamic_shocks", []) if isinstance(previous_state.get("dynamic_shocks"), list) else []
    prev_by_id = {str(x.get("id")): dict(x) for x in prev_list if isinstance(x, dict) and x.get("id")}
    rows = _rows(data)
    now = completed_iso or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    touched_candidates: list[dict[str, Any]] = []
    for asset_id in ASSETS:
        for pressure_id in PRESSURES:
            c = _candidate(asset_id, pressure_id, rows)
            if c:
                touched_candidates.append(c)

    # Keep only the strongest genuinely new seams per scan. Existing IDs are never
    # crowded out by newly generated candidates.
    touched_candidates.sort(key=lambda x: (x.get("inference_score", 0), x.get("best_quality", 0)), reverse=True)
    existing_touched = [c for c in touched_candidates if c["id"] in prev_by_id]
    # A genuinely NEW shock needs a fresh row that itself links the capability to
    # the external mechanism. Later scans may UPDATE an existing shock with fresh
    # evidence on either side, but we do not create novelty from arbitrary cross-products.
    new_touched = [
        c for c in touched_candidates
        if c["id"] not in prev_by_id
        and c.get("fresh_coupling")
        and int(c.get("inference_score", 0) or 0) >= 80
    ][:6]
    selected = {c["id"]: c for c in existing_touched + new_touched}

    merged: dict[str, dict[str, Any]] = {}
    new_count = updated_count = 0
    for cid, old in prev_by_id.items():
        if cid not in selected:
            keep = dict(old)
            keep["status"] = "unchanged"
            keep["new_this_scan"] = False
            keep["updated_this_scan"] = False
            merged[cid] = keep
            continue
        cur = dict(selected[cid])
        fp = _fingerprint(cur)
        old_fp = _clean(old.get("fingerprint"))
        changed = fp != old_fp
        cur["first_inferred_at"] = _clean(old.get("first_inferred_at")) or now
        cur["last_updated_at"] = now if changed else (_clean(old.get("last_updated_at")) or now)
        cur["fingerprint"] = fp
        cur["status"] = "updated" if changed else "unchanged"
        cur["new_this_scan"] = False
        cur["updated_this_scan"] = bool(changed)
        if changed:
            updated_count += 1
        merged[cid] = cur

    for cid, cur0 in selected.items():
        if cid in prev_by_id:
            continue
        cur = dict(cur0)
        cur["first_inferred_at"] = now
        cur["last_updated_at"] = now
        cur["fingerprint"] = _fingerprint(cur)
        cur["status"] = "new"
        cur["new_this_scan"] = True
        cur["updated_this_scan"] = False
        merged[cid] = cur
        new_count += 1

    active = sorted(
        merged.values(),
        key=lambda x: (
            2 if x.get("status") == "new" else 1 if x.get("status") == "updated" else 0,
            int(x.get("inference_score", 0)),
            _clean(x.get("last_updated_at")),
        ),
        reverse=True,
    )
    # Persistent analytical memory: a newly inferred shock never deletes an older one merely
    # by crowding it out of a fixed-size registry. Reader layers may show only a sparse subset,
    # but the registry itself accumulates until evidence explicitly changes the hypothesis.
    unchanged_count = sum(1 for x in active if x.get("status") == "unchanged")
    return {
        "profile_version": PROFILE_VERSION,
        "evaluated_at": now,
        "new_count": new_count,
        "updated_count": updated_count,
        "unchanged_count": unchanged_count,
        "dynamic_shocks": active,
    }


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    ap = argparse.ArgumentParser()
    ap.add_argument("radar", nargs="?", default="radar.json")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    p = Path(args.radar)
    doc = json.loads(p.read_text(encoding="utf-8"))
    prev = doc.get("shock_inference") if isinstance(doc.get("shock_inference"), dict) else {}
    state = refresh_shock_inference(doc, prev, _clean(doc.get("run_completed_at") or doc.get("last_updated")))
    print(json.dumps({k: v for k, v in state.items() if k != "dynamic_shocks"}, indent=2))
    for s in state["dynamic_shocks"]:
        print(f"{s['status']:9s} {s['inference_score']:3d} {s['id']}: {s['title']}")
    if args.write:
        doc["shock_inference"] = state
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
