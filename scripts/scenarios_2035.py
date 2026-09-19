"""EU R&I in 2035: four scenario worlds, each with four variants (16 cards).

Method (a standard 2x2 scenario frame, grounded in the Radar's own findings):

* Two critical uncertainties form the axes.  Both are read from the published
  Trends page each scan, so the frame moves with the evidence:
    - OPEN <-> GUARDED: does European research stay open, or does security close it?
    - SCALING <-> SQUEEZED: do money and capacity grow, or get squeezed?
* Each quadrant is one 2035 world.  Its story is assembled from the published
  trends pulling toward it, ongoing phenomena that persist in it, and the risk and
  opportunity that play out in it.
* Each world has four variants, each triggered by one specific published finding:
  two external shocks, one opportunity seized and one risk realised.  No finding
  triggers more than one variant, so the 16 cards stay distinct.

Everything imaginative (names, 2035 framing) is labelled as scenario; every
concrete element points back to a published finding and its sources.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable

HORIZON = 2035


def _clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


# ---------------------------------------------------------------- axis tagging
_OPEN_OBJECTS = (
    "research.collaboration", "research.openness", "research.open_access", "horizon.association",
    "horizon.access", "talent.", "digital.international_partnerships", "chips.international_cooperation",
    "research.infrastructure_access",
)
_GUARD_OBJECTS = (
    "research_security.", "export_control.", "innovation.dual_use", "defence.", "eu_entities.",
    "quantum.governance", "digital.sovereignty", "goal.strategic_autonomy",
)
_SCALE_OBJECTS = (
    "compute.", "finance.", "funding.", "horizon.budget", "chips.", "quantum.", "innovation.",
    "industrial.", "research.system_capacity", "research.infrastructure", "datacentre.", "ai.",
    "green.", "health.", "materials.",
)
_GUARD_DRIVERS = {"export_control", "security_reclassification", "sanctions", "conflict", "acquisition", "data_access", "info_manipulation"}
_SQUEEZE_DRIVERS = {"funding_cut", "energy", "chokepoint", "critical_input", "talent_flight", "hazard", "external_finance", "commercial", "political_shift"}
_OPEN_DRIVERS = {"tech_leap", "regulatory_shift", "cyber"}


def _objects(c: dict[str, Any]) -> list[str]:
    eps = [_clean(x) for x in (c.get("endpoint_objects") or []) if _clean(x)]
    obj = _clean(c.get("object"))
    return [x for x in [obj, *eps] if x]


def _driver(c: dict[str, Any]) -> str:
    pid = _clean(c.get("pressure_id"))
    if pid:
        return pid
    for x in _objects(c):
        if x.startswith("shock_pressure."):
            return x.split(".", 1)[1]
    return ""


def _starts(obj: str, prefixes: Iterable[str]) -> bool:
    obj = obj.replace("family:", "").replace("cluster:", "")
    return any(obj == p.rstrip(".") or obj.startswith(p) for p in prefixes)


def _tags(c: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for o in _objects(c):
        if _starts(o, _OPEN_OBJECTS):
            out.add("open")
        if _starts(o, _GUARD_OBJECTS):
            out.add("guard")
        if _starts(o, _SCALE_OBJECTS):
            out.add("scale")
    d = _driver(c)
    if d in _GUARD_DRIVERS:
        out.add("guard")
    if d in _SQUEEZE_DRIVERS:
        out.add("squeeze")
    if d in _OPEN_DRIVERS:
        out.add("open")
    return out


# ------------------------------------------------------------------ the worlds
_WORLDS = {
    ("open", "scaling"): {
        "id": "big_commons",
        "name": "The Big Commons",
        "tagline": "Open doors, deep pockets.",
        "story": (
            "By 2035 Europe has chosen scale over suspicion. Shared computing, joint programmes and "
            "easy researcher mobility have turned the continent into the world's largest open lab, "
            "and partners queue to plug in."
        ),
        "cost": "The price is exposure: what is shared this freely can also be copied, bought or switched off by others.",
    },
    ("guarded", "scaling"): {
        "id": "fortress_frontier",
        "name": "Fortress Frontier",
        "tagline": "Big money, high walls.",
        "story": (
            "By 2035 Europe spends heavily on its own capabilities, but behind screening, export lists "
            "and trusted-partner clubs. Flagship facilities are built and filled, yet who may use them "
            "is decided as much by security offices as by scientists."
        ),
        "cost": "The price is reach: fewer partners, slower exchange and a growing talent bill to staff the walls.",
    },
    ("open", "squeezed"): {
        "id": "brilliant_but_broke",
        "name": "Brilliant but Broke",
        "tagline": "Open minds, empty wallets.",
        "story": (
            "By 2035 European science is still open and well connected, but chronically underfunded. "
            "Ideas travel freely, and so do the people who have them, often to wherever the money and "
            "the machines are."
        ),
        "cost": "The price is ownership: Europe discovers, others scale, and the returns flow out.",
    },
    ("guarded", "squeezed"): {
        "id": "quiet_retreat",
        "name": "The Quiet Retreat",
        "tagline": "Fewer partners, less money.",
        "story": (
            "By 2035 tight budgets and tight security have met. Europe protects what it already has "
            "rather than building what comes next, and research becomes a matter of managing risk "
            "more than chasing discovery."
        ),
        "cost": "The price is the future: a smaller, safer system that falls further behind each year.",
    },
}

_SHOCK_AFFINITY = {
    "big_commons": ("tech_leap", "info_manipulation", "regulatory_shift", "cyber", "acquisition", "data_access"),
    "fortress_frontier": ("export_control", "security_reclassification", "conflict", "sanctions", "chokepoint", "critical_input"),
    "brilliant_but_broke": ("funding_cut", "talent_flight", "energy", "political_shift", "external_finance", "commercial"),
    "quiet_retreat": ("conflict", "sanctions", "energy", "funding_cut", "political_shift", "hazard"),
}

_TWIST = {
    "export_control": "after the export lists",
    "security_reclassification": "behind the security labels",
    "sanctions": "in the sanctions years",
    "conflict": "in the shadow of war",
    "acquisition": "after the takeovers",
    "data_access": "when the data stopped flowing",
    "cyber": "after the big breach",
    "energy": "in the power squeeze",
    "chokepoint": "held by a single supplier",
    "critical_input": "short of materials",
    "funding_cut": "after the budget axe",
    "talent_flight": "after the brain drain",
    "political_shift": "after the political turn",
    "regulatory_shift": "after the rulebook rewrite",
    "tech_leap": "after someone else's breakthrough",
    "info_manipulation": "in the disinformation fog",
    "hazard": "after the emergency",
    "commercial": "when the provider walked",
    "external_finance": "when foreign money left",
}

_VARIANT_SHOCK_TEXT = {
    "big_commons": "The open system absorbs the blow by sharing the load across many partners, but it learns how much it had left unguarded.",
    "fortress_frontier": "The walls go up faster and higher; what was a precaution in the 2020s becomes the default by 2035.",
    "brilliant_but_broke": "With no reserves to cushion it, the hit lands on people and projects directly, and some never come back.",
    "quiet_retreat": "It confirms the retreat: each shock is answered by protecting less, more tightly.",
}
_VARIANT_OPP_TEXT = {
    "big_commons": "Europe moves early and turns it into a shared platform others build on.",
    "fortress_frontier": "Europe seizes it, but keeps it inside the trusted club.",
    "brilliant_but_broke": "Europe spots it first, but has to find a partner with money to make it real.",
    "quiet_retreat": "It is the one bright spot, carefully protected and slow to grow.",
}
_VARIANT_RISK_TEXT = {
    "big_commons": "Openness makes it spread fast before anyone notices.",
    "fortress_frontier": "Security rules turn a manageable problem into a structural one.",
    "brilliant_but_broke": "With no money to fix it, it quietly becomes permanent.",
    "quiet_retreat": "Nobody has the budget or the partners to reverse it.",
}

# ------------------------------------------------------------- phrase pools
# Every recurring sentence has several forms.  A page-wide picker hands them out
# so no phrasing appears twice on the page; the choice depends only on the
# findings, so the same findings always give the same text.
_POOL = {
    "drivers": (
        "It is the world where today's evidence toward {a} and {b} continues.",
        "Two pulls visible today carried it here: {a}, and {b}.",
        "Trace it back and you find two of today's tugs of war settled one way: {a}; {b}.",
        "It grew out of two arguments the 2020s never resolved, until they were: {a} and {b}.",
    ),
    "driver_one": (
        "It is the world where today's pull toward {a} wins out.",
        "One of today's tugs of war settled here: {a}.",
        "Its seed is already visible: {a}.",
        "It is what happens if {a} keeps winning.",
    ),
    "persists": (
        "Some things never changed. In the 2020s the Radar noted: {q} In 2035 it still does.",
        "A familiar pattern survived the decade: {q}",
        "Old habits held. Back then the Radar kept seeing {q} It never went away.",
        "Not everything moved. {q} That was true in the 2020s and it is true now.",
    ),
    "opportunity": (
        "One early bet paid off. The 2020s signal was {q} In this world, it came true.",
        "Someone read the signs early: {q} The bet worked.",
        "The lucky break was visible years ahead: {q}",
        "One door that looked half-open in the 2020s swung wide: {q}",
    ),
    "risk": (
        "And one warning was not heeded: {q} By 2035 it is simply how things work.",
        "The warning came early and was filed away: {q} It is now the norm.",
        "One risk quietly became routine: {q}",
        "Nobody acted on this 2020s red flag: {q} Now everyone lives with it.",
    ),
    "watch": (
        "A decision to follow: {d}.",
        "An early marker on this road: {d}.",
        "Pending today and relevant here: {d}.",
        "One open file from the 2020s that this story turns on: {d}.",
    ),
    "shock_open": (
        "Same world, one jolt: {t}",
        "Now add a shock: {t}",
        "Picture the same 2035, but somewhere along the way: {t}",
        "Then the unexpected happened: {t}",
        "Go back to the late 2020s: {t}",
        "One bad year changes the story: {t}",
        "The trigger arrives without warning: {t}",
        "It starts with a single headline: {t}",
    ),
    "opp_open": (
        "Same world, one door opens. The 2020s signal {q} becomes real.",
        "Here, a long shot lands: {q}",
        "In this version Europe spots the opening in time: {q}",
        "A quiet signal from the 2020s turns into a turning point: {q}",
    ),
    "risk_open": (
        "Same world, one thing goes wrong. The 2020s warning {q} comes true.",
        "In this version a known weakness gives way: {q}",
        "The crack everyone saw in the 2020s finally splits open: {q}",
        "Here the slow problem wins: {q}",
    ),
}
_SHOCK_AFTER = {
    "big_commons": (
        "The open system absorbs the blow by sharing the load across many partners, but it learns how much it had left unguarded.",
        "Partners rally round, and the repair is fast, but the idea that openness is automatically safe does not survive.",
        "The commons bends rather than breaks; the bill arrives later as new locks on doors that used to stand open.",
    ),
    "fortress_frontier": (
        "The walls go up faster and higher; what was a precaution in the 2020s becomes the default by 2035.",
        "Each new wall feels justified at the time; together they turn a research system into a security system.",
        "The fortress holds, at the cost of the partners who used to come and go freely.",
    ),
    "brilliant_but_broke": (
        "With no reserves to cushion it, the hit lands on people and projects directly, and some never come back.",
        "The ideas survive; the teams and machines behind them often do not.",
        "Europe notices the damage first and repairs it last, because the money is always somewhere else.",
    ),
    "quiet_retreat": (
        "It confirms the retreat: each shock is answered by protecting less, more tightly.",
        "The response is caution on caution, and the circle of what Europe still does shrinks again.",
        "Nobody decides to give up; the system simply stops trying new things.",
    ),
}


# A concrete scene per world, anchored on one of its real findings ({asset}).
_SCENES = {
    "big_commons": (
        "A doctoral student in Tallinn books time on {asset} in minutes and runs it alongside partners in Seoul and S\u00e3o Paulo.",
        "A start-up in Porto trains its first model on {asset} for the price of a coffee subscription; half its team moved from abroad.",
    ),
    "fortress_frontier": (
        "A lab in Lisbon waits six months for a security clearance before it may use {asset}; the equipment itself is world-class.",
        "Access to {asset} starts at a badge gate: a trusted-partner list decides who gets in, and the list is shorter every year.",
    ),
    "brilliant_but_broke": (
        "A team in Krak\u00f3w designs a breakthrough around {asset}, then licenses it abroad because nobody in Europe can fund the scale-up.",
        "A postdoc in Ghent keeps {asset} running on a shoestring and answers job offers from three other continents every month.",
    ),
    "quiet_retreat": (
        "A half-empty institute in Turin still maintains {asset}, but new projects need three sign-offs and rarely start.",
        "Work on {asset} continues in a smaller, safer form; the ambitious version was shelved in 2029 and never revived.",
    ),
}

# Who wins and who loses, per world (researchers, universities, companies, funders).
_STAKE = {
    "big_commons": (
        ("Researchers", "Move freely and plug into shared machines anywhere in Europe; competition for the best people is global and fierce."),
        ("Universities", "Become nodes in continental networks; the ones that share infrastructure well pull ahead."),
        ("Companies", "Scale fast on public computing and open data, but know their edge can be copied just as fast."),
        ("Funders", "Pay for the commons and spend the decade arguing about who free-rides on it."),
    ),
    "fortress_frontier": (
        ("Researchers", "Get excellent kit and generous budgets, in exchange for clearances, screening and fewer foreign co-authors."),
        ("Universities", "Split into trusted and ordinary tiers; security offices become as powerful as research offices."),
        ("Companies", "Win secure public contracts, lose easy access to non-European markets and suppliers."),
        ("Funders", "Spend more than ever, much of it on compliance, vetting and duplicating what used to be shared."),
    ),
    "brilliant_but_broke": (
        ("Researchers", "Keep their freedom and their networks, lose their contracts; the best leave for better-funded labs."),
        ("Universities", "Publish brilliantly and patch buildings; many survive on partnerships with foreign money."),
        ("Companies", "Find great ideas cheaply in Europe and scale them somewhere else."),
        ("Funders", "Ration shrinking budgets and fund many small bets instead of a few big ones."),
    ),
    "quiet_retreat": (
        ("Researchers", "Face fewer openings, more paperwork and slower careers; mobility turns one-way, outward."),
        ("Universities", "Consolidate and merge; risk management replaces ambition in the strategy documents."),
        ("Companies", "Lean on protected home markets and trusted suppliers, and stop expecting research to lead."),
        ("Funders", "Protect a shrinking core and cut everything that looks optional."),
    ),
}

_OPP_END = {
    "big_commons": "The standard others adopt is European, and so are the network benefits.",
    "fortress_frontier": "The capability is owned outright, but shared with only a handful of allies.",
    "brilliant_but_broke": "The credit stays in Europe; the scale-up and most of the returns do not.",
    "quiet_retreat": "It becomes a protected success story nobody dares to grow.",
}
_RISK_END = {
    "big_commons": "Openness survives, with a permanent tax attached for the gap it ignored.",
    "fortress_frontier": "The problem is locked in by the very rules meant to prevent it.",
    "brilliant_but_broke": "It becomes part of the landscape, because fixing it was never funded.",
    "quiet_retreat": "Plans get built around it instead of fixing it.",
}

_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def _when(date: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})", _clean(date))
    if not m:
        return "In the 2020s"
    return f"{_MONTHS[int(m.group(2)) - 1]} {m.group(1)}"


def _history(c: dict[str, Any] | None, words: int = 24, role: str = "", used: set[str] | None = None) -> str:
    """Retell a finding as dated history: when, who, what they reported.

    ``used`` holds statements already quoted on the page; another supporting
    source is preferred so the same dated line never appears twice."""
    if not c:
        return ""
    rows = [r for r in (c.get("support") or []) if isinstance(r, dict) and _clean(r.get("source_statement"))]
    if role and any(_clean(r.get("role")) == role for r in rows):
        rows = [r for r in rows if _clean(r.get("role")) == role] + [r for r in rows if _clean(r.get("role")) != role]
    if used is not None:
        fresh = [r for r in rows if _clean(r.get("source_statement")) not in used]
        if not fresh:
            return ""
        rows = fresh[:1] if role else fresh
    if not rows:
        return _clean(_title(c)).rstrip(".") + "."
    r = rows[0] if (role and used is not None) else max(rows, key=lambda x: (float(x.get("quality", 0) or 0), _clean(x.get("date"))))
    if used is not None:
        used.add(_clean(r.get("source_statement")))
    parts = _clean(r.get("source_statement")).split()
    text = " ".join(parts[:words]).rstrip(",;:") + ("\u2026" if len(parts) > words else "")
    text = text.rstrip(".") + ("" if text.endswith("\u2026") else ".")
    return text


_FACILITIES = {
    "quantum.pilot_line": "the quantum pilot line",
    "quantum.testing_infrastructure": "an open quantum test bed",
    "quantum.machine": "a European quantum computer",
    "compute.capacity": "a shared European supercomputer",
    "compute.gigafactory": "an AI gigafactory",
    "compute.public_procurement": "a public AI factory",
    "compute.access_time": "shared supercomputer time",
    "chips.fab": "a new chip fab",
    "chips.pilot_line": "a chip pilot line",
    "research.infrastructure": "a flagship research facility",
    "research.infrastructure_access": "a flagship research facility",
    "datacentre.energy_supply": "a research data centre",
    "defence.drone_capability": "a drone test range",
    "health.data_infrastructure": "a pan-European health-data platform",
    "space.capability": "a European satellite platform",
}


_FALLBACK_FACILITIES = (
    "a shared European research facility",
    "a university research lab",
    "a cross-border research network",
    "a national research centre",
)


def _asset(c: dict[str, Any] | None) -> str:
    """A concrete, facility-like noun for the day-in-2035 scene."""
    for o in _objects(c) if c else []:
        if o in _FACILITIES:
            return _FACILITIES[o]
    return "a shared European research facility"


class _Picker:
    def __init__(self) -> None:
        self.used: dict[str, set[int]] = {}

    def __call__(self, pool: str, seed: str, options: tuple[str, ...] | None = None) -> str:
        opts = options if options is not None else _POOL[pool]
        taken = self.used.setdefault(pool, set())
        start = _stable(pool + seed) % len(opts)
        for k in range(len(opts)):
            i = (start + k) % len(opts)
            if i not in taken:
                taken.add(i)
                return opts[i]
        return opts[start]




# --------------------------------------------------------------------- helpers
def _pub(state_pubs: dict[str, Any], by_id: dict[str, dict[str, Any]], product: str) -> list[dict[str, Any]]:
    ids = state_pubs.get(product) if isinstance(state_pubs.get(product), list) else []
    return [by_id[_clean(i)] for i in ids if _clean(i) in by_id]


def _title(c: dict[str, Any]) -> str:
    if _clean(c.get("product")) == "trend":
        b = c.get("trend_balance") if isinstance(c.get("trend_balance"), dict) else {}
        return _clean(b.get("left_title")) + " vs " + _clean(b.get("right_title"))
    return _clean(c.get("reader_title") or c.get("topic_label"))


def _sources(c: dict[str, Any], n: int = 3) -> list[dict[str, str]]:
    out, seen = [], set()
    for r in c.get("support") or []:
        if not isinstance(r, dict):
            continue
        src = _clean(r.get("source"))
        if not src or src.lower() in seen:
            continue
        seen.add(src.lower())
        out.append({"source": src, "title": _clean(r.get("title")), "link": _clean(r.get("link")), "date": _clean(r.get("date"))[:10]})
        if len(out) >= n:
            break
    return out


def _ref(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "finding_id": _clean(c.get("id")),
        "product": _clean(c.get("product")),
        "title": _title(c),
        "sources": _sources(c),
    }


def _stable(key: str) -> int:
    return int(hashlib.sha1(key.encode()).hexdigest(), 16)


_PROPER = re.compile(r"^(?:Europe|European|EU|Horizon|AI|Euro|EuroHPC|Germany|German|France|French|China|Chinese|US|UK|Finland|Finnish|Japan|India|Italy|Belgian|Belgium|Mistral|MSCA|ERC|EIC|NATO|Ukraine|Taiwan|Denmark|Hungary|Poland)\b")


def _lower_first(s: str) -> str:
    """Fit a finding title into a sentence: keep proper nouns, drop the full stop."""
    s = _clean(s).rstrip(".")
    if not s or _PROPER.match(s) or (len(s) > 1 and s[1].isupper()):
        return s
    return s[:1].lower() + s[1:]


def _sentence(prefix: str, title: str) -> str:
    body = _lower_first(title)
    end = "" if body.endswith(("?", "!")) else "."
    return f"{prefix}{body}{end}"


def _quote(title: str, end: bool = False) -> str:
    t = _clean(title).rstrip(".")
    if end and not t.endswith(("?", "!")):
        t += "."
    return f"\u201c{t}\u201d"


def _end(text: str) -> str:
    """Close a sentence that may end in a quotation."""
    t = _clean(text)
    if t.endswith("\u201d"):
        inner = t[:-1]
        return t if inner.endswith((".", "?", "!")) else inner + ".\u201d"
    return t if t.endswith((".", "?", "!")) else t + "."


def _consequence(c: dict[str, Any]) -> str:
    # The shock card's own explanation, without the shocks-page sourcing note.
    t = _clean(c.get("reader_consequence"))
    return _clean(t.split(" Signal behind it:")[0])


# ----------------------------------------------------------------------- axes
def _axes(trends: list[dict[str, Any]]) -> dict[str, Any]:
    open_votes: list[float] = []
    scale_votes: list[float] = []
    basis: list[str] = []
    for t in trends:
        b = t.get("trend_balance") if isinstance(t.get("trend_balance"), dict) else {}
        try:
            push = float(b.get("left_pull"))
        except (TypeError, ValueError):
            continue
        tags = _tags(t)
        used = False
        if "open" in tags:
            open_votes.append(push); used = True          # more openness pushed
        if "guard" in tags:
            open_votes.append(100.0 - push); used = True  # more security pushed = less open
        if "scale" in tags:
            scale_votes.append(push); used = True
        if used:
            basis.append(_clean(t.get("id")))
    openness = round(sum(open_votes) / len(open_votes), 1) if open_votes else 50.0
    scale = round(sum(scale_votes) / len(scale_votes), 1) if scale_votes else 50.0

    def lean(v: float, hi: str, lo: str) -> str:
        if v >= 58:
            return f"leaning {hi}"
        if v <= 42:
            return f"leaning {lo}"
        return "balanced"

    return {
        "openness": {"score": openness, "reading": lean(openness, "open", "guarded"), "votes": len(open_votes)},
        "scale": {"score": scale, "reading": lean(scale, "scaling", "squeezed"), "votes": len(scale_votes)},
        "basis_trend_ids": basis,
    }


# ------------------------------------------------------------------- builder
def build_scenarios_2035(publications: dict[str, Any], candidates: list[dict[str, Any]], evaluated_at: str = "") -> dict[str, Any]:
    by_id = {_clean(c.get("id")): c for c in candidates if isinstance(c, dict) and _clean(c.get("id"))}
    trends = _pub(publications, by_id, "trend")
    shocks = _pub(publications, by_id, "shock")
    continuities = _pub(publications, by_id, "continuity")
    risks = _pub(publications, by_id, "risk")
    opps = _pub(publications, by_id, "opportunity")
    if not (shocks or trends or risks or opps):
        return {"horizon": HORIZON, "evaluated_at": evaluated_at, "scenarios": [], "axes": {}}

    used: set[str] = set()
    used_drivers: set[str] = set()
    used_evidence: set[str] = set()
    used_facilities: set[str] = set()
    pick_phrase = _Picker()

    def topic(c: dict[str, Any]) -> str:
        objs = [o for o in _objects(c) if not o.startswith("shock_pressure.")]
        return objs[0] if objs else ""

    world_topics: set[str] = set()

    def take(pool: list[dict[str, Any]], want: set[str], avoid_tags: set[str] = frozenset(), prefer: tuple[str, ...] = (), skip_drivers: set[str] = frozenset()) -> dict[str, Any] | None:
        # First try without repeating a topic already told in this world; only
        # fall back to a repeat when nothing else is left.
        for strict in (True, False):
            got = _take(pool, want, avoid_tags, prefer, skip_drivers, strict)
            if got is not None:
                world_topics.add(topic(got))
                return got
        return None

    def _take(pool, want, avoid_tags, prefer, skip_drivers, strict):
        best, best_key = None, None
        for idx, c in enumerate(pool):
            cid = _clean(c.get("id"))
            if not cid or cid in used:
                continue
            if skip_drivers and _driver(c) in skip_drivers:
                continue
            if strict and topic(c) and topic(c) in world_topics:
                continue
            tags = _tags(c)
            d = _driver(c)
            key = (
                prefer.index(d) if d in prefer else len(prefer),   # preferred shock family first
                -len(tags & want),                                 # matches the world
                len(tags & avoid_tags),                            # does not pull the other way
                idx,                                               # page order (wow cycle)
            )
            if best_key is None or key < best_key:
                best, best_key = c, key
        if best is not None:
            used.add(_clean(best.get("id")))
        return best

    scenarios = []
    page_drivers: set[str] = set()
    for quad in (("open", "scaling"), ("guarded", "scaling"), ("open", "squeezed"), ("guarded", "squeezed")):
        world = _WORLDS[quad]
        wid = world["id"]
        world_topics.clear()
        want = {"open" if quad[0] == "open" else "guard", "scale" if quad[1] == "scaling" else "squeeze"}
        avoid = {"guard" if quad[0] == "open" else "open"}

        # Drivers: one trend on each axis, told from the side that wins in this
        # world (for a squeezed world, the pushback wins on scale topics).
        axis_tag = "open" if quad[0] == "open" else "guard"

        def driver_ref(t: dict[str, Any], expand_wins: bool) -> dict[str, Any]:
            b = t.get("trend_balance") if isinstance(t.get("trend_balance"), dict) else {}
            return {**_ref(t), "winning_side": _clean(b.get("left_title") if expand_wins else b.get("right_title")),
                    "watch": _clean(b.get("flip_line"))}

        drivers = []
        axis_pool = sorted([t for t in trends if axis_tag in _tags(t)], key=lambda t: _stable(wid + _clean(t.get("id"))))
        # Openness axis: a trend on an open topic wins by expanding; on a guard
        # topic it also wins by expanding (more security).
        pick = next((t for t in axis_pool if _clean(t.get("id")) not in used_drivers), axis_pool[0] if axis_pool else None)
        if pick is not None:
            drivers.append(driver_ref(pick, True)); used_drivers.add(_clean(pick.get("id")))
        scale_pool = sorted([t for t in trends if "scale" in _tags(t) and not ({"open", "guard"} & _tags(t))],
                            key=lambda t: _stable(wid + _clean(t.get("id"))))
        pick = next((t for t in scale_pool if _clean(t.get("id")) not in used_drivers), scale_pool[0] if scale_pool else None)
        if pick is not None:
            drivers.append(driver_ref(pick, quad[1] == "scaling")); used_drivers.add(_clean(pick.get("id")))

        persists = take(continuities, want, avoid)
        opportunity = take(opps, want, avoid)
        risk = take(risks, want, avoid)

        story = [world["story"]]
        sides = [f"\u201c{d['winning_side']}\u201d" for d in drivers if d["winning_side"]]
        if len(sides) >= 2:
            story.append(pick_phrase("drivers", wid).format(a=sides[0], b=sides[1]))
        elif sides:
            story.append(pick_phrase("driver_one", wid).format(a=sides[0]))
        if persists:
            story.append(pick_phrase("persists", wid).format(q=_quote(_title(persists), True)))
        if opportunity:
            story.append(pick_phrase("opportunity", wid).format(q=_quote(_title(opportunity), True)))
        if risk:
            story.append(pick_phrase("risk", wid).format(q=_quote(_title(risk), True)))
        story.append(world["cost"])

        signals = [x for x in [*drivers, _ref(persists) if persists else None, _ref(opportunity) if opportunity else None, _ref(risk) if risk else None] if x]
        pending_watch = [d["watch"] for d in drivers if d.get("watch") and not d["watch"].startswith("Nothing")]
        if not pending_watch:
            # Any trend pulling toward this world with a real decision pending.
            for t in trends:
                b = t.get("trend_balance") if isinstance(t.get("trend_balance"), dict) else {}
                fl = _clean(b.get("flip_line"))
                if (_tags(t) & want) and fl and not fl.startswith("Nothing"):
                    pending_watch.append(fl)
                    break
        if pending_watch:
            m_q = re.search(r"\u201c([^\u201d]+)\u201d", pending_watch[0])
            if m_q:
                watch = pick_phrase("watch", wid).format(d=f"\u201c{m_q.group(1)}\u201d")
            elif drivers and drivers[0].get("winning_side"):
                shape = {
                    "big_commons": "For an open, scaling Europe",
                    "fortress_frontier": "For a guarded, scaling Europe",
                    "brilliant_but_broke": "For an open, squeezed Europe",
                    "quiet_retreat": "For a guarded, squeezed Europe",
                }.get(wid, "For this scenario")
                watch = f"{shape}, watch for new evidence on \u201c{drivers[0]['winning_side']}\u201d."
            else:
                watch = "Watch for new evidence that changes the balance."
        elif drivers and drivers[0].get("winning_side"):
            shape = {
                "big_commons": "For an open, scaling Europe",
                "fortress_frontier": "For a guarded, scaling Europe",
                "brilliant_but_broke": "For an open, squeezed Europe",
                "quiet_retreat": "For a guarded, squeezed Europe",
            }.get(wid, "For this scenario")
            watch = f"{shape}, watch for the first adopted measure behind \u201c{drivers[0]['winning_side']}\u201d."
        else:
            watch = ""

        # ---- four variants
        variants = []
        prefer = _SHOCK_AFFINITY[wid]
        world_drivers: set[str] = set()
        for _ in range(2):
            # A kind of shock appears once per page where possible, never twice in a world.
            sh = (take(shocks, want, avoid, prefer, world_drivers | page_drivers)
                  or take(shocks, want, avoid, prefer, world_drivers)
                  or take(shocks, want, avoid, prefer))
            if not sh:
                continue
            d = _driver(sh)
            world_drivers.add(d)
            page_drivers.add(d)
            variants.append({
                "id": f"{wid}:shock:{_clean(sh.get('id'))[-10:]}",
                "kind": "shock",
                "name": f"{world['name']}, {_TWIST.get(d, 'after the shock')}",
                "trigger": _title(sh),
                "story": [
                    _sentence(pick_phrase("shock_open", wid + _clean(sh.get("id"))).replace("{t}", ""), _title(sh)),
                    _consequence(sh),
                    pick_phrase("after:" + wid, _clean(sh.get("id")), _SHOCK_AFTER[wid]),
                ],
                **{k: v for k, v in _ref(sh).items() if k in ("finding_id", "product", "sources")},
            })
        op2 = take(opps, want, avoid)
        if op2:
            variants.append({
                "id": f"{wid}:opportunity:{_clean(op2.get('id'))[-10:]}",
                "kind": "opportunity",
                "name": f"{world['name']}, with a lucky break",
                "trigger": _title(op2),
                "story": [_end(pick_phrase("opp_open", wid).format(q=_quote(_title(op2)))), _VARIANT_OPP_TEXT[wid]],
                **{k: v for k, v in _ref(op2).items() if k in ("finding_id", "product", "sources")},
            })
        rk2 = take(risks, want, avoid)
        if rk2:
            variants.append({
                "id": f"{wid}:risk:{_clean(rk2.get('id'))[-10:]}",
                "kind": "risk",
                "name": f"{world['name']}, with a slow leak",
                "trigger": _title(rk2),
                "story": [_end(pick_phrase("risk_open", wid).format(q=_quote(_title(rk2)))), _VARIANT_RISK_TEXT[wid]],
                **{k: v for k, v in _ref(rk2).items() if k in ("finding_id", "product", "sources")},
            })
        # Keep four cards even when a pool runs dry: fall back to any unused shock.
        while len(variants) < 4:
            sh = (take(shocks, set(), set(), (), world_drivers | page_drivers)
                  or take(shocks, set(), set(), (), world_drivers) or take(shocks, set(), set()))
            if not sh:
                break
            d = _driver(sh)
            world_drivers.add(d)
            page_drivers.add(d)
            variants.append({
                "id": f"{wid}:shock:{_clean(sh.get('id'))[-10:]}",
                "kind": "shock",
                "name": f"{world['name']}, {_TWIST.get(d, 'after the shock')}",
                "trigger": _title(sh),
                "story": [
                    _sentence(pick_phrase("shock_open", wid + _clean(sh.get("id"))).replace("{t}", ""), _title(sh)),
                    _consequence(sh),
                    pick_phrase("after:" + wid, _clean(sh.get("id")), _SHOCK_AFTER[wid]),
                ],
                **{k: v for k, v in _ref(sh).items() if k in ("finding_id", "product", "sources")},
            })
        for v in variants:
            v["story"] = [x for x in v["story"] if x]

        # Prefer a finding about an actual facility for the scene.
        anchors = [by_id[v["finding_id"]] for v in variants if v["finding_id"] in by_id] + [x for x in (persists, opportunity, risk) if x]
        def facility(a: dict[str, Any]) -> str:
            return next((_FACILITIES[o] for o in _objects(a) if o in _FACILITIES), "")
        # Each world's scene gets its own facility; never reuse one across worlds.
        scene_anchor = next((a for a in anchors if facility(a) and facility(a) not in used_facilities), None)
        if scene_anchor is not None:
            scene_asset = facility(scene_anchor)
        else:
            scene_asset = next((f for f in _FALLBACK_FACILITIES if f not in used_facilities), _FALLBACK_FACILITIES[0])
        used_facilities.add(scene_asset)
        bullets = [
            {"label": "Picture", "text": world["story"]},
            {"label": "A day in 2035", "text": pick_phrase("scene:" + wid, wid, _SCENES[wid]).format(asset=scene_asset)},
        ]
        if len(story) > 1 and drivers:
            bullets.append({"label": "How we got here", "text": story[1]})
        h = _history(persists, used=used_evidence) if persists else ""
        if h:
            bullets.append({"label": "Evidence today", "text": h})
        h = _history(opportunity, used=used_evidence) if opportunity else ""
        if h:
            bullets.append({"label": "The bet that paid off", "text": h + " Europe acted on it."})
        h = _history(risk, used=used_evidence) if risk else ""
        if h:
            bullets.append({"label": "The warning ignored", "text": h + " Nobody fixed it."})
        bullets += [{"label": who, "text": line} for who, line in _STAKE[wid]]
        price = re.sub(r"^The price is ([^:]+):\s*", lambda m: m.group(1)[:1].upper() + m.group(1)[1:] + ": ", world["cost"])
        bullets.append({"label": "The price", "text": price})
        if watch:
            bullets.append({"label": "Signpost", "text": watch})

        for v in variants:
            src = by_id.get(v["finding_id"])
            kind = v["kind"]
            vb = [{"label": "Trigger", "text": _end(_title(src)) if src else _end(v["trigger"])}]
            # For a shock, the evidence is the disruption itself, not the asset.
            hist = _history(src, role="external_driver" if kind == "shock" else "", used=used_evidence)
            if hist:
                vb.append({"label": "Evidence today", "text": hist})
            if kind == "shock":
                vb.append({"label": "What happens next", "text": _consequence(src) if src else ""})
                vb.append({"label": "Where Europe ends up", "text": v["story"][-1]})
            elif kind == "opportunity":
                vb.append({"label": "What happens next", "text": _VARIANT_OPP_TEXT[wid]})
                vb.append({"label": "Where Europe ends up", "text": _OPP_END[wid]})
            else:
                vb.append({"label": "What happens next", "text": _VARIANT_RISK_TEXT[wid]})
                vb.append({"label": "Where Europe ends up", "text": _RISK_END[wid]})
            v["bullets"] = [b for b in vb if _clean(b["text"])]

        scenarios.append({
            "id": wid,
            "name": world["name"],
            "tagline": world["tagline"],
            "quadrant": {"openness": quad[0], "scale": quad[1]},
            "story": story,
            "bullets": bullets,
            "signals": signals,
            "watch": watch,
            "variants": variants,
        })

    return {
        "horizon": HORIZON,
        "evaluated_at": evaluated_at,
        "method": (
            "Two uncertainties read from today's published trends (open vs guarded; scaling vs squeezed) "
            "define four 2035 worlds. Each world is assembled from published trends, ongoing phenomena, risks "
            "and opportunities; each of its four variants is triggered by one published shock, opportunity or "
            "risk. They are scenarios, not forecasts: none is ranked as more likely. Every trigger and signal is a "
            "current finding with sources."
        ),
        "axes": {"horizontal": "Guarded \u2194 Open", "vertical": "Squeezed \u2194 Scaling"},
        "scenarios": scenarios,
        "card_count": len(scenarios) + sum(len(x["variants"]) for x in scenarios),
    }
