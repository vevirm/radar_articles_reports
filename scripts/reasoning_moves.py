"""Additional reasoning moves for the claim-native engine.

The original grammars (dependency pathways, latent channels, conflicting criteria,
split recurrences, future shocks, ...) join evidence through the controlled
object graph.  The moves here connect items in ways the object graph cannot see,
but always through an explicit mechanism, so that a surprising connection is
also an explainable one:

* magnitude_contrast   - money stated in separate sources, compared.  One private
                         project can outweigh a public programme; one deal can
                         dwarf a whole sector.  Nobody states the comparison;
                         the engine computes it.
* external_opening     - a restriction imposed abroad next to a European gain in
                         the flow it redirects (US grant restrictions -> US-based
                         ERC applicants).
* cross_pressure       - two European policies acting on the same people in
                         opposite directions (recruit foreign researchers /
                         screen foreign researchers).
* common_driver        - one outside dependency named in several unrelated
                         fields at once.
* national_convergence - member states building the same thing separately,
                         ahead of (or beside) a common EU approach.

Every move consumes the same active-corpus claim nodes as the other grammars,
uses only reviewed claims (Deep Scan / backfill origin) and emits ordinary
candidate dicts with role snapshots, so adapt_candidate, gates, selection and the
card writer treat them like any other finding.  Nothing here touches evidence,
admission or the scanner.
"""
from __future__ import annotations

import datetime as dt
import itertools
import re
from collections import defaultdict
from typing import Any, Iterable

try:
    from scripts.claim_reasoning_shadow import _snap, _claim_objects, _role_strength, clean
    from scripts import card_writer as CW
    from scripts import reader_labels as RL
except ImportError:  # pragma: no cover
    from claim_reasoning_shadow import _snap, _claim_objects, _role_strength, clean  # type: ignore
    import card_writer as CW  # type: ignore
    import reader_labels as RL  # type: ignore

REVIEWED = {"deep_scan", "backfill"}
RESTRICTIONS = {"restricts", "conditions", "excludes", "licenses", "regulates", "screens", "requires", "opposes"}
NEGATIVE = {"contracts", "becomes_conditional", "becomes_contested"}


def _current_reviewed(nodes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        n for n in nodes
        if n.get("_primary") and clean(n.get("era")) == "current" and clean(n.get("origin")) in REVIEWED
        and not ((n.get("attributes") or {}).get("world_reasoning") is False)
    ]


def _cluster(obj: str, vocab: dict[str, Any]) -> str:
    meta = (vocab.get("objects") or {}).get(clean(obj), {})
    return clean(meta.get("cluster")) if isinstance(meta, dict) else ""


def _date(n: dict[str, Any]) -> dt.date | None:
    v = clean(n.get("status_date"))
    for fmt, size in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return dt.datetime.strptime(v[:size], fmt).date()
        except ValueError:
            continue
    return None


def _scope(n: dict[str, Any]) -> dict[str, Any]:
    return n.get("scope") if isinstance(n.get("scope"), dict) else {}


def _actor(n: dict[str, Any]) -> dict[str, Any]:
    return n.get("actor") if isinstance(n.get("actor"), dict) else {}


def _countries(n: dict[str, Any]) -> list[str]:
    return [RL.country_name(c) for c in (_scope(n).get("countries") or []) if clean(c)]


def _text(n: dict[str, Any]) -> str:
    return clean(n.get("text"))


def _src(n: dict[str, Any]) -> str:
    return clean(n.get("_source")).lower()


def _score(*rows: dict[str, Any]) -> int:
    merits = [float(r.get("merit", 0) or 0) for r in rows if r]
    base = sum(merits) / len(merits) if merits else 0
    sources = len({_src(r) for r in rows if r and _src(r)})
    return int(max(0, min(99, round(base * (1.0 if sources >= 2 else 0.9)))))


def _candidate(grammar: str, product: str, level: int, wow: int, roles: dict[str, dict | None], **extra: Any) -> dict[str, Any]:
    snaps = {r: _snap(n, r) for r, n in roles.items() if n}
    rows = [n for n in roles.values() if n]
    score = _score(*rows)
    out = {
        "level": level, "grammar_id": grammar, "product": product, "roles": snaps,
        "missing_roles": [r for r, n in roles.items() if not n],
        "score": score, "floor_ok": bool(rows) and all(_role_strength(n, r) >= 0.20 for r, n in roles.items() if n),
        "wow_preliminary": wow, "score_gate_passes": score >= 60, "publication_gate_passes": False,
        "move": grammar,
    }
    out.update(extra)
    return out


# ---------------------------------------------------------------------------
# 1. Magnitude contrast
# ---------------------------------------------------------------------------

_PURPOSES: tuple[tuple[str, str], ...] = (
    (r"defen[cs]e (?:procurement|industrial)|joint (?:defen[cs]e )?procurement", "defence procurement"),
    (r"defen[cs]e[- ]innovation|disruptive defen[cs]e|defen[cs]e technology research", "defence innovation"),
    (r"gigafactor", "AI gigafactories"),
    (r"data[- ]cent(?:re|er)|ai[- ]compute|compute infrastructure|supercomput", "AI compute"),
    (r"\bspace\b", "space"),
    (r"technology[- ]transfer|commerciali[sz]ation", "turning research into companies"),
    (r"start-?ups?|scale-?ups?", "start-ups"),
    (r"decarboni[sz]ation|clean technolog|green", "clean technology"),
    (r"postdoc|recruit|fellowship", "recruiting researchers"),
    (r"quantum", "quantum technology"),
    (r"horizon europe|framework programme|fp10", "EU research funding"),
)


def _purpose(n: dict[str, Any], vocab: dict[str, Any]) -> str:
    text = f"{_text(n)} {clean(n.get('_title'))}".lower()
    for rx, label in _PURPOSES:
        if re.search(rx, text):
            return label
    return RL.label(n.get("object"))


def _compare_key(n: dict[str, Any], vocab: dict[str, Any]) -> str:
    text = f"{_text(n)} {clean(n.get('_title'))}".lower()
    cl = _cluster(n.get("object"), vocab)
    if cl in {"compute_ai", "permitting_siting"} or re.search(r"gigafactor|data[- ]cent|ai[- ]compute", text):
        return "compute"
    if re.search(r"defen[cs]e|dual-use", text) or cl == "defence_dual_use":
        return "defence"
    if cl == "capital_markets" or re.search(r"venture|funding round|series [a-e]\b|valuation", text):
        return "capital"
    if cl in {"funding_programme", "research_system", "research_infrastructure", "talent"}:
        return "research"
    return cl or "other"


_SECTOR_TOTAL = re.compile(r"\b(?:attracted|raised|received|invested)\b.{0,60}\b(?:in|during) (20\d\d)\b|\b(?:in|during) (20\d\d)\b.{0,60}\b(?:attracted|raised)\b", re.I)
_SECTOR_SUBJECT = re.compile(r"([A-Za-z][\w\-]*(?:\s+(?:and|&)\s+[\w\-]+|\s+[\w\-]+){0,4})\s+start-?ups\b", re.I)
_DEAL = re.compile(r"\b(?:round|raised|series [a-e]|financing|funding round)\b", re.I)
_EXCLUDE_AMOUNT = re.compile(r"\b(?:valuation|gap|unfinanced|shortfall|worth about|between 20\d\d and)\b", re.I)


def _unit(n: dict[str, Any]) -> str:
    a = _actor(n)
    cls = clean(a.get("class"))
    level = clean(_scope(n).get("level"))
    kind = clean(n.get("kind"))
    text = _text(n)
    if kind == "diagnosis" and _SECTOR_TOTAL.search(text):
        return "sector"
    if kind not in {"action", "effect"}:
        return ""
    if cls == "company":
        return "deal" if _DEAL.search(text) else "company"
    if cls in {"member_state", "national_funder"} and level == "member_state":
        return "national"
    if cls in {"member_state", "national_funder"} and level == "eu":
        return "member_states"
    if cls == "eu_body" or level == "eu":
        return "programme"
    return ""


def _money_rows(nodes: list[dict[str, Any]], vocab: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for n in nodes:
        text = _text(n)
        if _EXCLUDE_AMOUNT.search(text) and not _SECTOR_TOTAL.search(text):
            continue
        amts = CW.amounts(text) or CW.amounts(clean(n.get("_title")))
        unit = _unit(n)
        if not amts or not unit:
            continue
        rows.append({"node": n, "eur": amts[0]["eur"], "text": amts[0]["text"], "unit": unit,
                     "key": _compare_key(n, vocab), "purpose": _purpose(n, vocab)})
    # One deal reported by several outlets is one amount.  Keep the strongest report.
    best: dict[tuple[str, str, int], dict[str, Any]] = {}
    for r in rows:
        a = clean(_actor(r["node"]).get("name")).lower()
        k = (r["key"], a or clean(r["node"].get("_record_id")), int(round(r["eur"] / 1e7)))
        if k not in best or float(r["node"].get("merit", 0) or 0) > float(best[k]["node"].get("merit", 0) or 0):
            best[k] = r
    return list(best.values())


def _unit_label(r: dict[str, Any]) -> str:
    n = r["node"]
    actor = RL.short_name(_actor(n).get("name"))
    states = [c for c in _countries(n) if c in RL.EU_MEMBER_STATES]
    where = f" in {states[0]}" if len(states) == 1 else ""
    # Points about the system: no company, country or programme names.
    if r["unit"] == "deal":
        return "one funding round"
    if r["unit"] == "company":
        return "a single private project"
    if r["unit"] == "national":
        return f"one member state's {r['purpose']} plan"
    if r["unit"] == "member_states":
        return f"EU governments' combined pledge for {r['purpose']}"
    if r["unit"] == "sector":
        m = _SECTOR_SUBJECT.search(_text(n))
        subject = clean(m.group(1)) if m else r["purpose"]
        subject = re.sub(r"^(?:EU-27|EU|European)\s+", "", subject, flags=re.I)
        y = _SECTOR_TOTAL.search(_text(n))
        year = (y.group(1) or y.group(2)) if y else ""
        return f"what all EU {subject} start-ups raised{' in ' + year if year else ''}"
    text = _text(n).lower()
    if re.search(r"public funding|pledg", text):
        return f"the EU's entire public pledge for {r['purpose']}"
    if re.search(r"combined investment|target", text):
        return f"the EU's whole {r['purpose']} drive"
    return f"the EU's {r['purpose']} programme" if "programme" not in r["purpose"] else f"the EU's {r['purpose']}"


def magnitude_contrasts(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _money_rows(_current_reviewed(nodes), vocab)
    out: list[dict[str, Any]] = []
    public = {"programme", "member_states"}
    units = {"company", "deal", "national"}

    def make(big: dict[str, Any], small: dict[str, Any], frame: str, wow: int, subject: dict[str, Any],
             prog: dict[str, Any] | None = None) -> dict[str, Any]:
        ratio = big["eur"] / small["eur"] if small["eur"] else 0.0
        extra: dict[str, Any] = {}
        if prog is not None:
            extra = {"unit_label": _unit_label(subject), "unit_text": CW.display_amount(subject["text"], subject["eur"]),
                     "programme_label": _unit_label(prog), "programme_text": CW.display_amount(prog["text"], prog["eur"]),
                     "relation": "outweighs" if subject["eur"] >= prog["eur"] else "rivals"}
        return _candidate(
            "magnitude_contrast", "risk", 5, wow,
            {"larger_amount": big["node"], "smaller_amount": small["node"]},
            endpoint_objects=[clean(big["node"].get("object")), clean(small["node"].get("object"))],
            object=clean(subject["node"].get("object")),
            contrast_frame=frame, ratio=round(ratio, 3), compare_key=big["key"],
            larger_text=CW.display_amount(big["text"], big["eur"]), smaller_text=CW.display_amount(small["text"], small["eur"]),
            larger_label=(_unit_label(big) if frame != "priority_gap" else big["purpose"]),
            smaller_label=(_unit_label(small) if frame != "priority_gap" else small["purpose"]),
            subject_claim=clean(subject["node"].get("claim_id")), **extra,
        )

    # (a) One project, deal or country against a whole public programme.  The unit is
    # the story; compare it with the largest public programme it still outweighs, or
    # else the one it comes closest to.
    for u in [r for r in rows if r["unit"] in units]:
        progs = [p for p in rows if p["unit"] in public and p["key"] == u["key"] and p["key"] != "other"
                 and clean(p["node"].get("_record_id")) != clean(u["node"].get("_record_id"))]
        outweighed = [p for p in progs if u["eur"] >= p["eur"]]
        close = [p for p in progs if p["eur"] > u["eur"] and p["eur"] / u["eur"] <= 3]
        if outweighed:
            p = max(outweighed, key=lambda x: x["eur"])
            out.append(make(u, p, "unit_rivals_programme", 5, u, prog=p))
        elif close:
            p = min(close, key=lambda x: x["eur"])
            out.append(make(p, u, "unit_rivals_programme", 5, u, prog=p))
    # (b) One deal against a whole sector's annual total.
    for d in [r for r in rows if r["unit"] == "deal"]:
        for sec in [r for r in rows if r["unit"] == "sector" and r["key"] == d["key"] and r["purpose"] != d["purpose"]]:
            if d["eur"] >= 1.5 * sec["eur"]:
                out.append(make(d, sec, "deal_vs_sector", 4, d))
    # (c) Two EU programmes in one field whose sizes differ by an order of magnitude or more.
    progs = [r for r in rows if r["unit"] == "programme"]
    seen: set[tuple[str, str, int]] = set()
    for a, b in itertools.combinations(progs, 2):
        if a["key"] != b["key"] or a["key"] == "other" or a["purpose"] == b["purpose"]:
            continue
        big, small = (a, b) if a["eur"] >= b["eur"] else (b, a)
        if big["eur"] / small["eur"] < 20:
            continue
        k = (clean(big["node"].get("_record_id")), small["purpose"], int(round(small["eur"] / 1e6)))
        if k in seen:
            continue
        seen.add(k)
        out.append(make(big, small, "priority_gap", 4, big))
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for c in out:
        k = (c["contrast_frame"], c["subject_claim"])
        if k not in best or c["score"] > best[k]["score"]:
            best[k] = c
    return sorted(best.values(), key=lambda c: (c["wow_preliminary"], c["score"]), reverse=True)[:24]


# ---------------------------------------------------------------------------
# 2. External restriction -> European opening
# ---------------------------------------------------------------------------

_OPENING_MAP: dict[str, set[str]] = {
    "research.collaboration": {"talent.recruitment_abroad", "talent.retention", "horizon.association", "research.collaboration"},
    "research.openness": {"talent.recruitment_abroad", "research.collaboration"},
    "talent.recruitment_abroad": {"talent.recruitment_abroad", "talent.retention"},
    "funding.route": {"talent.recruitment_abroad", "horizon.association"},
    "finance.venture_capital": {"innovation.deep_tech_startups", "finance.venture_capital"},
    "innovation.deep_tech_startups": {"innovation.deep_tech_startups"},
}
_EXTERNAL_ACTOR = (
    (r"\b(?:US|U\.S\.|United States|American|Washington)\b", "US"),
    (r"\b(?:China|Chinese|Beijing)\b", "Chinese"),
    (r"\b(?:UK|United Kingdom|British)\b", "UK"),
)
_GAIN_PHRASES = {
    "talent.recruitment_abroad": "Europe's recruitment drive",
    "talent.retention": "keeping researchers in Europe",
    "horizon.association": "Horizon Europe's pull on partners",
    "research.collaboration": "Europe as a research partner",
    "innovation.deep_tech_startups": "European start-ups",
    "finance.venture_capital": "European capital",
}
_GAIN_MECH = {"recruits", "retains", "transfers", "associates", "collaborates", "funds", "invests", "launches", "supports"}


def _external_adjective(n: dict[str, Any]) -> str:
    blob = " ".join([_text(n), clean(_actor(n).get("name")), " ".join(_countries(n))])
    for rx, adj in _EXTERNAL_ACTOR:
        if re.search(rx, blob):
            return adj
    return ""


def external_openings(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any]) -> list[dict[str, Any]]:
    cur = _current_reviewed(nodes)
    ext = [
        n for n in cur
        if (clean(_scope(n).get("level")) in {"external", "third_country"} or clean(_actor(n).get("class")) == "third_country")
        and (clean(n.get("mechanism")) in RESTRICTIONS or clean(n.get("direction")) in NEGATIVE)
        and clean(n.get("object")) in _OPENING_MAP and _external_adjective(n)
    ]
    out: list[dict[str, Any]] = []
    for e in ext:
        adj = _external_adjective(e)
        targets = _OPENING_MAP[clean(e.get("object"))]
        ed = _date(e)
        gains = [
            n for n in cur
            if n is not e and clean(n.get("_record_id")) != clean(e.get("_record_id"))
            and clean(_scope(n).get("level")) in {"eu", "member_state", "company_in_eu"}
            and clean(n.get("direction")) == "expands" and clean(n.get("mechanism")) in _GAIN_MECH
            and bool(_claim_objects(n) & targets)
            and (not ed or not _date(n) or (_date(n) - ed).days >= -30)
        ]
        if not gains:
            continue
        # A gain that names the same outside actor is a visible link (less surprising);
        # otherwise the link is the engine's inference (more surprising).
        rx = next((r for r, a in _EXTERNAL_ACTOR if a == adj), "")
        named = [g for g in gains if rx and re.search(rx, _text(g))]
        pref = {"talent.recruitment_abroad": 4, "talent.retention": 3, "innovation.deep_tech_startups": 3,
                "research.collaboration": 2, "finance.venture_capital": 2, "horizon.association": 1}
        gains.sort(key=lambda g: (1 if g in named else 0, pref.get(clean(g.get("object")), 0), float(g.get("merit", 0) or 0)), reverse=True)
        g1 = gains[0]
        g2 = next((g for g in gains[1:] if _src(g) != _src(g1) and clean(g.get("object")) == clean(g1.get("object"))), None) \
            or next((g for g in gains[1:] if _src(g) != _src(g1)), None)
        wow = 3 if named else 4
        out.append(_candidate(
            "external_opening", "opportunity", 4, wow,
            {"external_constraint": e, "european_gain": g1, "european_gain_2": g2},
            endpoint_objects=[clean(e.get("object")), clean(g1.get("object"))],
            object=clean(g1.get("object")), external_actor=adj, gain_object=clean(g1.get("object")),
            gain_phrase=_GAIN_PHRASES.get(clean(g1.get("object")), f"Europe in {RL.label(g1.get('object'))}"),
        ))
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for c in out:
        k = (c["external_actor"], c["gain_object"])
        if k not in best or c["score"] > best[k]["score"]:
            best[k] = c
    return list(best.values())


# ---------------------------------------------------------------------------
# 3. Cross pressure: two European policies, same people, opposite directions
# ---------------------------------------------------------------------------

def _matches(n: dict[str, Any], spec: dict[str, Any]) -> bool:
    objs = _claim_objects(n)
    wanted = spec.get("objects", set())
    ok_obj = any(o in wanted or any(w.endswith(".*") and o.startswith(w[:-1]) for w in wanted) for o in objs)
    if not ok_obj:
        return False
    dirs = spec.get("directions")
    mechs = spec.get("mechanisms")
    if dirs and clean(n.get("direction")) in dirs:
        return True
    if mechs and clean(n.get("mechanism")) in mechs:
        return True
    return not dirs and not mechs


CROSS_PRESSURES: tuple[dict[str, Any], ...] = (
    {
        "id": "recruit_and_screen",
        "pull_text": r"screen\w*|security|self-assessment|admissib\w*|safeguard\w*|vetting",
        "push": {"objects": {"talent.recruitment_abroad"}, "directions": {"expands"}},
        "pull": {"objects": {"research_security.*", "grant.admissibility", "research.openness"},
                 "directions": {"becomes_conditional", "contracts"}, "mechanisms": {"screens", "requires", "conditions", "restricts"}},
        "population": "international researchers",
        "headline": "Europe is recruiting researchers from abroad while tightening the screening they must pass",
        "push_vp": "is inviting researchers from abroad", "pull_same": "adding security checks on them", "pull_fin": "adds security checks on them",
        "people": r"\b(?:researchers?|scientists?|postdoc\w*|PhD|doctoral|foreign|international staff|visas?|hiring|recruit\w*)\b",
        "so_what": "Both aims are legitimate; without coordination the screening can quietly undo the recruitment.",
    },
    {
        "id": "invite_and_constrain_datacentres",
        "pull_text": r"permit\w*|energy|water|power|grid|protest\w*|opposition|efficien\w*",
        "push": {"objects": {"compute.gigafactory", "compute.capacity", "compute.private_investment", "compute.gigafactory_cofinancing"}, "directions": {"expands"}},
        "pull": {"objects": {"datacentre.permitting", "datacentre.energy_supply", "datacentre.local_opposition", "datacentre.siting", "energy.grid"},
                 "directions": {"becomes_conditional", "contracts", "becomes_contested"}, "mechanisms": {"regulates", "requires", "opposes", "restricts"}},
        "population": "AI data-centre projects",
        "headline": "Europe is inviting AI data centres while the conditions to build them tighten",
        "push_vp": "is inviting AI data centres", "pull_same": "the conditions to build them tighten", "pull_fin": "tightens the conditions to build them",
        "so_what": "Compute plans move only as fast as the slowest permit, grid connection or local vote.",
    },
    {
        "id": "back_and_burden_ai",
        "pull_text": r"AI Act|requirement\w*|obligation\w*|\brules?\b|complian\w*|liabilit\w*|transparency|burden\w*",
        "push": {"objects": {"ai.adoption", "compute.gigafactory", "innovation.deep_tech_startups", "ai.public_sector_capacity"}, "directions": {"expands"}},
        "pull": {"objects": {"ai.governance", "digital.governance"}, "mechanisms": {"regulates", "requires", "restricts"}},
        "population": "European AI developers",
        "headline": "Europe is backing its AI developers while adding rules they must absorb",
        "push_vp": "is backing its AI developers", "pull_same": "adding rules they must absorb", "pull_fin": "adds rules they must absorb",
        "people": r"\b(?:developers?|compan\w*|firms?|start-?ups?|SMEs?|providers?|deployers?|businesses)\b",
        "so_what": "Large firms absorb compliance costs; small ones may build elsewhere or not at all.",
    },
    {
        "id": "partner_and_secure",
        "pull_text": r"security|screen\w*|export control\w*|safeguard\w*|condition\w*",
        "push": {"objects": {"horizon.association", "chips.international_cooperation", "digital.international_partnerships"}, "directions": {"expands"}},
        "pull": {"objects": {"research_security.*", "export_control.*", "research.openness", "grant.admissibility"},
                 "directions": {"becomes_conditional", "contracts"}, "mechanisms": {"screens", "restricts", "conditions", "licenses", "requires"}},
        "population": "international research partners",
        "headline": "Europe is widening research partnerships while raising the security bar for partners",
        "push_vp": "is widening research partnerships", "pull_same": "adding security conditions for partners", "pull_fin": "adds security conditions for partners",
        "people": r"\b(?:partners?|partnerships?|collaborat\w*|cooperat\w*|third[- ]countr\w*|foreign|associated countr\w*)\b",
        "so_what": "Partners read both signals at once; the stricter one tends to decide what they do.",
    },
    {
        "id": "draft_and_close",
        "pull_text": r"security|sensitive|safeguard\w*|restrict\w*|screen\w*|openness",
        "push": {"objects": {"innovation.dual_use", "defence.innovation_funding"}, "directions": {"expands"}},
        "pull": {"objects": {"research.openness", "research_security.*"}, "directions": {"becomes_conditional", "contracts"}},
        "population": "civilian researchers and start-ups",
        "headline": "Europe is drawing civilian researchers into defence work while narrowing what they may share",
        "push_vp": "is drawing civilian researchers into defence work", "pull_same": "limiting what they may share", "pull_fin": "limits what they may share",
        "people": r"\b(?:researchers?|scientists?|universit\w*|start-?ups?|civilian|academ\w*)\b",
        "so_what": "Dual-use money attracts civilian talent; security rules can then push the same people back out.",
    },
)


_STOP = {"european", "europe", "their", "which", "while", "about", "under", "these", "there", "where", "would", "could",
         "should", "other", "across", "including", "through", "between", "within", "without", "after", "before", "research",
         "national", "public", "policy", "policies", "support", "supports", "programme", "funding", "union"}


def _single_state(n: dict[str, Any]) -> str:
    sc = _scope(n)
    names = [RL.country_name(c) for c in (sc.get("countries") or []) if clean(c)]
    names = [x for x in names if x in RL.EU_MEMBER_STATES]
    return names[0] if clean(sc.get("level")) == "member_state" and len(names) == 1 else ""


def cross_pressures(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any]) -> list[dict[str, Any]]:
    cur = [n for n in _current_reviewed(nodes) if clean(_scope(n).get("level")) in {"eu", "member_state"}]
    out: list[dict[str, Any]] = []
    used_pulls: set[str] = set()

    def tokens(n: dict[str, Any]) -> set[str]:
        return {w for w in re.findall(r"[a-z][a-z\-]{4,}", _text(n).lower())} - _STOP

    for spec in CROSS_PRESSURES:
        push = [n for n in cur if clean(n.get("kind")) in {"action", "effect"} and _matches(n, spec["push"])]
        # Both sides must be policies in force or under way: the headline says Europe
        # (or a member state) does both, so a study's view cannot stand in for one side.
        pull = [n for n in cur if clean(n.get("kind")) in {"action", "effect"} and _matches(n, spec["pull"])]
        if not push or not pull:
            continue
        best_push = max(push, key=lambda n: (float(n.get("merit", 0) or 0), clean(n.get("status_date"))))
        rx_pull = spec.get("pull_text")
        # The pull must act on the same people as the push, not merely share a field.
        rx_people = spec.get("people")
        pulls = [n for n in pull if clean(n.get("_record_id")) != clean(best_push.get("_record_id"))
                 and (not rx_pull or re.search(rx_pull, _text(n), re.I))
                 and (not rx_people or re.search(rx_people, _text(n), re.I))]
        if not pulls:
            continue
        # Prefer a pull not already used by another cross-pressure, that shares vocabulary
        # with the push (same people, same field), that is a measure rather than an
        # opinion, then evidence strength.
        pt = tokens(best_push)
        best_pull = max(pulls, key=lambda n: (
            0 if clean(n.get("claim_id")) in used_pulls else 1,
            1 if clean(n.get("kind")) in {"action", "effect"} else 0,
            1 if clean(_scope(n).get("level")) == "eu" else 0,
            float(n.get("merit", 0) or 0),
            len(pt & tokens(n)),
        ))
        used_pulls.add(clean(best_pull.get("claim_id")))
        headline = f"Europe {spec['push_vp']} while {spec['pull_same']}"
        a_cl, b_cl = _cluster(best_push.get("object"), vocab), _cluster(best_pull.get("object"), vocab)
        joint = any(_matches(n, spec["push"]) and _matches(n, spec["pull"]) for n in cur)
        wow = 5 if a_cl != b_cl and not joint else 4
        out.append(_candidate(
            "cross_pressure", "risk", 4, wow,
            {"push": best_push, "pull": best_pull},
            endpoint_objects=[clean(best_push.get("object")), clean(best_pull.get("object"))],
            object=clean(best_push.get("object")), cross_id=spec["id"], population=spec["population"],
            headline=headline, so_what=spec["so_what"],
        ))
    return out


# ---------------------------------------------------------------------------
# 4. Common driver across fields
# ---------------------------------------------------------------------------

COMMON_DRIVERS: tuple[dict[str, Any], ...] = (
    {
        "id": "us_dependence",
        "label": "Reducing dependence on the United States",
        "headline": "Cutting reliance on the United States now runs through European {fields}",
        "rx": re.compile(r"\b(?:reliance|relian\w*|dependen\w*|reliant|depend\w*)\b.{0,40}\b(?:US|U\.S\.|United States|American)\b|"
                         r"\b(?:US|U\.S\.|American)\b.{0,30}\b(?:cloud|infrastructure|providers?|platforms?|grant[- ]policy|restrictions?)\b", re.I),
    },
    {
        "id": "china_lead",
        "label": "China's industrial lead",
        "headline": "China's lead is now felt across European {fields}",
        "rx": re.compile(r"\bChin(?:a|ese)(?:'s|’s)?\b.{0,80}\b(?:dominan\w*|lead\w*|locali[sz]\w*|pressure\w*|scale|export[- ]control\w*|strategy)\b|"
                         r"\blosing ground to China\b|\bChinese (?:critical[- ]material )?dependenc\w*", re.I),
    },
    {
        "id": "non_european_supply",
        "label": "Dependence on non-European suppliers",
        "headline": "Dependence on non-European suppliers now runs through {fields}",
        "rx": re.compile(r"\bnon-European (?:suppliers?|providers?|services?)\b|\bexternally sourced\b|\bforeign (?:suppliers?|providers?|technology firms?)\b|\btechnology firms\b.{0,20}\bdependenc", re.I),
    },
)

_FIELD_WORDS: tuple[tuple[str, str], ...] = (
    (r"\bspace\b|satellite|earth observation", "space"),
    (r"\bcloud\b", "cloud"),
    (r"comput|supercomput|data cent", "computing"),
    (r"\bchips?\b|semiconductor", "chips"),
    (r"\bAI\b|artificial intelligence|model", "AI"),
    (r"rare[- ]earth|critical[- ]raw|critical[- ]material|mineral", "critical materials"),
    (r"\bEVs?\b|electric[- ]vehicle", "electric vehicles"),
    (r"robot", "robotics"),
    (r"biomanufactur|biotech", "biotechnology"),
    (r"drone", "drones"),
    (r"grant|research collaboration|research cooperation", "research funding"),
    (r"diplomac|platforms", "digital diplomacy"),
    (r"growth model|industrial", "industry"),
)


def _field(n: dict[str, Any], vocab: dict[str, Any]) -> str:
    text = _text(n)
    for rx, name in _FIELD_WORDS:
        if re.search(rx, text, re.I):
            return name
    return RL.cluster_label(_cluster(n.get("object"), vocab))


def common_drivers(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any]) -> list[dict[str, Any]]:
    cur = _current_reviewed(nodes)
    out: list[dict[str, Any]] = []
    for spec in COMMON_DRIVERS:
        hits = [
            n for n in cur if spec["rx"].search(_text(n))
            and (clean(_scope(n).get("level")) in {"eu", "member_state", "company_in_eu"}
                 or re.search(r"\b(?:Europe\w*|EU)\b", _text(n)))
        ]
        by_field: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for n in hits:
            by_field[_field(n, vocab)].append(n)
        if len(by_field) < 3 or len({_src(n) for n in hits}) < 3:
            continue
        reps = []
        for field, rows in sorted(by_field.items(), key=lambda kv: -max(float(r.get("merit", 0) or 0) for r in kv[1])):
            reps.append((field, max(rows, key=lambda r: float(r.get("merit", 0) or 0))))
        roles = {f"field_{i + 1}": n for i, (_f, n) in enumerate(reps[:4])}
        fields = [f for f, _n in reps]
        wow = 4 if len(fields) >= 4 else 3
        out.append(_candidate(
            "common_driver", "continuity", 4, wow, roles,
            endpoint_objects=[f"driver:{spec['id']}"], object=f"driver:{spec['id']}",
            driver_id=spec["id"], driver_label=spec["label"], field_labels=fields[:5],
            headline=spec["headline"].format(fields=RL.join_names(fields[:4])),
        ))
    return out


# ---------------------------------------------------------------------------
# 5. National convergence
# ---------------------------------------------------------------------------

_CONVERGENCE_GROUPS: dict[str, tuple[str, ...]] = {
    "research_security": ("research_security.", "grant.admissibility", "export_control.competence"),
    "compute": ("compute.", "datacentre."),
    "defence": ("defence.", "innovation.dual_use"),
    "talent": ("talent.",),
    "chips": ("chips.",),
    "quantum": ("quantum.",),
    "clean_tech": ("green.", "innovation.green_technology", "energy."),
}
_CONVERGENCE_LABELS = {
    "research_security": "research security", "compute": "AI compute", "defence": "defence R&I",
    "talent": "the contest for researchers", "chips": "chipmaking", "quantum": "quantum technology",
    "clean_tech": "clean technology",
}


def _convergence_group(obj: str) -> str:
    for name, prefixes in _CONVERGENCE_GROUPS.items():
        if any(obj == p or (p.endswith(".") and obj.startswith(p)) for p in prefixes):
            return name
    return ""


_BUILD_MECH = {"builds", "funds", "launches", "requires", "screens", "regulates", "invests", "recruits",
               "adds_capacity", "trains", "procures", "prioritises", "adopts", "proposes"}


def national_convergences(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any], evaluated_on: dt.date | None = None) -> list[dict[str, Any]]:
    cur = _current_reviewed(nodes)
    evaluated_on = evaluated_on or dt.date.today()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in cur:
        if clean(_scope(n).get("level")) != "member_state" or clean(n.get("kind")) not in {"action", "effect"}:
            continue
        if clean(n.get("mechanism")) not in _BUILD_MECH:
            continue
        d = _date(n)
        if d and (evaluated_on - d).days > 365:
            continue
        grp = _convergence_group(clean(n.get("object")))
        if grp:
            groups[grp].append(n)
    out: list[dict[str, Any]] = []
    for fam, rows in groups.items():
        by_country: dict[str, dict[str, Any]] = {}
        for n in sorted(rows, key=lambda r: float(r.get("merit", 0) or 0), reverse=True):
            for c in _countries(n):
                if c in RL.EU_MEMBER_STATES and c not in by_country:
                    by_country[c] = n
        if len(by_country) < 3:
            continue
        eu_rows = [n for n in cur if clean(_scope(n).get("level")) == "eu" and _convergence_group(clean(n.get("object"))) == fam and clean(n.get("kind")) == "action"]
        eu_state = "adopted" if any(clean(n.get("status")) in {"adopted", "in_force", "operating"} for n in eu_rows) else ("proposed" if eu_rows else "none")
        countries = list(by_country)[:5]
        roles = {f"country_{i + 1}": by_country[c] for i, c in enumerate(countries)}
        out.append(_candidate(
            "national_convergence", "continuity", 3, 3 if len(by_country) >= 4 else 2, roles,
            endpoint_objects=[f"convergence:{fam}"], object=f"convergence:{fam}", countries=countries, eu_state=eu_state,
            group_label=_CONVERGENCE_LABELS.get(fam, fam),
        ))
    return out


def detect_moves(nodes: Iterable[dict[str, Any]], vocab: dict[str, Any], evaluated_on: dt.date | None = None) -> dict[str, list[dict[str, Any]]]:
    nodes = list(nodes)
    return {
        "move_magnitude_contrast": magnitude_contrasts(nodes, vocab),
        "move_external_opening": external_openings(nodes, vocab),
        "move_cross_pressure": cross_pressures(nodes, vocab),
        "move_common_driver": common_drivers(nodes, vocab),
        "move_national_convergence": national_convergences(nodes, vocab, evaluated_on),
    }
