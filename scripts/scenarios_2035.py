"""EU R&I in 2035: four scenario worlds, each with four variants (16 cards).

Method (a standard 2x2 scenario frame, grounded in the Radar's own findings):

* Two critical uncertainties form the axes. Both are read from the published
  Trends page each scan, so the frame moves with the evidence:
    - MORE CONNECTED <-> LESS CONNECTED: how strongly is Europe linked to global partners, markets, talent and infrastructure?
    - MORE RESOURCES <-> FEWER RESOURCES: how much money, capacity, energy, infrastructure and talent are available?
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
        "name": "Connected Growth",
        "tagline": "More resources, strong global links.",
        "story": (
            "Europe enters 2035 with more money, capacity and research infrastructure, while staying strongly connected to global partners. "
            "Researchers, firms and universities can work across borders easily, and Europe scales more of what it discovers."
        ),
        "cost": "The trade-off is exposure: deeper global links also leave Europe more dependent on decisions, suppliers and disruptions outside Europe.",
    },
    ("guarded", "scaling"): {
        "id": "fortress_frontier",
        "name": "Independent Scale",
        "tagline": "More resources, weaker global links.",
        "story": (
            "By 2035, strong European investment has built more research and technology capacity, but Europe works with a narrower set of global partners. "
            "Funding and infrastructure are strong, while security, resilience and European control shape who can take part."
        ),
        "cost": "The trade-off is reach: Europe has more control, but fewer outside connections and less access to some global talent, markets and ideas.",
    },
    ("open", "squeezed"): {
        "id": "brilliant_but_broke",
        "name": "Open Under Pressure",
        "tagline": "Fewer resources, strong global links.",
        "story": (
            "Global links remain strong in 2035, but European research and innovation operate with tight resources. "
            "Ideas and people move easily, while many European teams depend on outside capital, infrastructure or partners to scale their work."
        ),
        "cost": "The trade-off is dependence: Europe stays connected, but often relies on others to finance, host or scale what it creates.",
    },
    ("guarded", "squeezed"): {
        "id": "quiet_retreat",
        "name": "Constrained Europe",
        "tagline": "Fewer resources, weaker global links.",
        "story": (
            "In 2035, Europe has fewer resources and weaker global connections. "
            "Governments and institutions protect a smaller core of capabilities, while new projects, partnerships and large investments become harder to sustain."
        ),
        "cost": "The trade-off is ambition: Europe reduces exposure, but has less capacity to build, experiment and compete at scale.",
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
        "A research team in Tallinn books time on {asset} and works with partners in Seoul and São Paulo the same week.",
        "A start-up in Porto uses {asset}, European funding and overseas partners to scale without leaving Europe.",
    ),
    "fortress_frontier": (
        "A lab in Lisbon uses {asset} built with strong European funding, but access depends on trusted-partner rules.",
        "A company develops around {asset} with European suppliers and public backing, while working with fewer non-European partners.",
    ),
    "brilliant_but_broke": (
        "A team in Kraków develops a breakthrough around {asset}, then looks abroad for the money and capacity needed to scale it.",
        "A postdoc in Ghent keeps {asset} running with limited funding while working daily with better-resourced partners abroad.",
    ),
    "quiet_retreat": (
        "A research institute in Turin keeps {asset} running, but new projects are rare and international partnerships are harder to start.",
        "Work on {asset} continues in a smaller form because neither the resources nor the outside links exist for a larger programme.",
    ),
}

# Who wins and who loses, per world (researchers, universities, companies, funders).
_STAKE = {
    "big_commons": (
        ("Researchers", "Move easily across borders and use growing shared capacity, while competition for talent remains global."),
        ("Universities", "Gain from large international networks and stronger infrastructure, but depend on those networks staying open."),
        ("Companies", "Can scale faster with more capital, infrastructure and global partners, while facing strong outside competition."),
        ("Funders", "Have more room to invest, but must decide how much European capacity should remain open to global use."),
    ),
    "fortress_frontier": (
        ("Researchers", "Gain better funded European facilities, but face more limits on international collaboration and mobility."),
        ("Universities", "Build stronger European capacity while spending more time on security, access rules and trusted partnerships."),
        ("Companies", "Benefit from European investment and procurement, but have fewer easy links to some foreign suppliers and markets."),
        ("Funders", "Can build strategic capacity, but pay more for duplication, resilience and European control."),
    ),
    "brilliant_but_broke": (
        ("Researchers", "Keep strong international networks, but face tighter European funding and may move to where resources are better."),
        ("Universities", "Stay globally connected, while relying more on outside partners and shared infrastructure they do not control."),
        ("Companies", "Can reach global capital and markets, but European scale-up capacity remains uneven."),
        ("Funders", "Must choose carefully where limited resources can make the biggest difference."),
    ),
    "quiet_retreat": (
        ("Researchers", "Face fewer opportunities at home and fewer easy routes into global networks."),
        ("Universities", "Protect core strengths, merge or narrow priorities as both funding and international links weaken."),
        ("Companies", "Work with smaller markets and more limited research capacity, with fewer options outside Europe."),
        ("Funders", "Concentrate scarce resources on a smaller number of strategic capabilities."),
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
    t = _clean(c.get("reader_title") or c.get("topic_label"))
    # Shock cards are headed as questions ("What if X hit Y?"); a story needs the event.
    m = re.match(r"^What if (.+?) hit (.+?)\?$", t)
    if m:
        return f"{m.group(1)[:1].upper()}{m.group(1)[1:]} hit {m.group(2)}."
    return t


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
def _build_default_frame(publications: dict[str, Any], candidates: list[dict[str, Any]], evaluated_at: str = "") -> dict[str, Any]:
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
                    "big_commons": "For a well-resourced, globally connected Europe",
                    "fortress_frontier": "For a well-resourced Europe with weaker global links",
                    "brilliant_but_broke": "For a resource-constrained, globally connected Europe",
                    "quiet_retreat": "For a resource-constrained Europe with weaker global links",
                }.get(wid, "For this scenario")
                watch = f"{shape}, watch for new evidence on \u201c{drivers[0]['winning_side']}\u201d."
            else:
                watch = "Watch for new evidence that changes the balance."
        elif drivers and drivers[0].get("winning_side"):
            shape = {
                "big_commons": "For a well-resourced, globally connected Europe",
                "fortress_frontier": "For a well-resourced Europe with weaker global links",
                "brilliant_but_broke": "For a resource-constrained, globally connected Europe",
                "quiet_retreat": "For a resource-constrained Europe with weaker global links",
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
            "quadrant": {
                "connectedness": "more_connected" if quad[0] == "open" else "less_connected",
                "resources": "more_resources" if quad[1] == "scaling" else "fewer_resources",
                "openness": quad[0],
                "scale": quad[1],
            },
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
            "Two uncertainties define the frame: how many resources Europe has, and how strongly Europe is connected globally. "
            "The four worlds are scenarios, not forecasts. Each has four variants built from current shocks, risks and opportunities."
        ),
        "axes": {"horizontal": "Less globally connected ↔ More globally connected", "vertical": "Fewer resources ↔ More resources"},
        "scenarios": scenarios,
        "card_count": len(scenarios) + sum(len(x["variants"]) for x in scenarios),
    }


# ========================================================= multi-axis frames
# The original Resources × Global connectedness builder above is retained as the
# default frame for backward compatibility. Additional frames use the same live
# publications but are generated from the manual axis definitions in
# scenario_axes_2035.py. The top-level ``scenarios`` field remains an alias of
# the default frame so older pages and downstream consumers keep working.


def _public_axis(axis: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": _clean(axis.get("key")),
        "title": _clean(axis.get("title")),
        "low": dict(axis.get("low") or {}),
        "high": dict(axis.get("high") or {}),
    }


def _axis_relevance(c: dict[str, Any], axis: dict[str, Any]) -> int:
    """How directly a published finding belongs to one manually defined axis."""
    score = 0
    patterns = tuple(_clean(x) for x in axis.get("objects", ()) if _clean(x))
    for obj in _objects(c):
        bare = obj.replace("family:", "").replace("cluster:", "")
        for pat in patterns:
            pbare = pat.replace("family:", "").replace("cluster:", "")
            if obj == pat.rstrip(".") or obj.startswith(pat) or bare == pbare.rstrip(".") or bare.startswith(pbare):
                score += 5
                break
    hay = " ".join(
        _clean(c.get(k)) for k in ("reader_title", "reader_summary", "reader_why", "topic_label")
    ).lower()
    for kw in axis.get("keywords", ()):
        if _clean(kw).lower() in hay:
            score += 1
    return score


def _frame_relevance(c: dict[str, Any], frame: dict[str, Any]) -> int:
    return _axis_relevance(c, frame["horizontal"]) + _axis_relevance(c, frame["vertical"])


def _other_pole(pole: str) -> str:
    return "low" if pole == "high" else "high"


def _finding_affinity(c: dict[str, Any], axis: dict[str, Any]) -> str:
    """Return the pole a finding most naturally stresses, or empty if neutral.

    This is deliberately modest. Opportunities pull toward the axis's declared
    capacity/agency pole; risks and shocks stress the opposite pole. Trends and
    continuities remain usable on either side because they describe the tension
    itself rather than a forecast of which side wins.
    """
    if _axis_relevance(c, axis) <= 0:
        return ""
    product = _clean(c.get("product"))
    positive = _clean(axis.get("positive_pole")) or "high"
    if product == "opportunity":
        return positive
    if product in {"risk", "shock"}:
        return _other_pole(positive)
    return ""


def _quadrant_fit(c: dict[str, Any], frame: dict[str, Any], hpole: str, vpole: str) -> int:
    score = _frame_relevance(c, frame) * 10
    for axis, pole in ((frame["horizontal"], hpole), (frame["vertical"], vpole)):
        affinity = _finding_affinity(c, axis)
        if affinity:
            score += 8 if affinity == pole else -4
    # Prefer stronger presentational candidates when thematic fit ties.
    try:
        score += int(float(c.get("score", 0) or 0) // 10)
    except (TypeError, ValueError):
        pass
    return score


def _ranked_for_world(
    pool: list[dict[str, Any]],
    frame: dict[str, Any],
    hpole: str,
    vpole: str,
    seed: str,
    used: set[str] | None = None,
    require_relevant: bool = True,
) -> list[dict[str, Any]]:
    used = used if used is not None else set()
    rows = [c for c in pool if _clean(c.get("id")) and _clean(c.get("id")) not in used]
    if require_relevant:
        relevant = [c for c in rows if _frame_relevance(c, frame) > 0]
        if relevant:
            rows = relevant
    return sorted(rows, key=lambda c: (-_quadrant_fit(c, frame, hpole, vpole), _stable(seed + _clean(c.get("id")))))


def _choose_world_finding(
    pool: list[dict[str, Any]],
    frame: dict[str, Any],
    hpole: str,
    vpole: str,
    seed: str,
    used: set[str],
) -> dict[str, Any] | None:
    ranked = _ranked_for_world(pool, frame, hpole, vpole, seed, used, True)
    if not ranked:
        ranked = _ranked_for_world(pool, frame, hpole, vpole, seed, used, False)
    if not ranked:
        return None
    got = ranked[0]
    used.add(_clean(got.get("id")))
    return got


def _axis_driver(
    trends: list[dict[str, Any]],
    axis: dict[str, Any],
    pole: str,
    seed: str,
    used: set[str],
) -> dict[str, Any] | None:
    rows = [t for t in trends if _axis_relevance(t, axis) > 0]
    if not rows:
        return None
    fresh = [t for t in rows if _clean(t.get("id")) not in used] or rows
    fresh = sorted(fresh, key=lambda t: (-_axis_relevance(t, axis), _stable(seed + _clean(t.get("id")))))
    t = fresh[0]
    used.add(_clean(t.get("id")))
    b = t.get("trend_balance") if isinstance(t.get("trend_balance"), dict) else {}
    positive = _clean(axis.get("positive_pole")) or "high"
    side = _clean(b.get("left_title") if pole == positive else b.get("right_title"))
    return {**_ref(t), "winning_side": side, "watch": _clean(b.get("flip_line"))}


def _variant_next(c: dict[str, Any]) -> str:
    product = _clean(c.get("product"))
    if product == "shock":
        return _consequence(c)
    return _clean(c.get("reader_why") or c.get("reader_summary") or _title(c))


def _generic_variant(
    c: dict[str, Any],
    frame: dict[str, Any],
    hpole: str,
    vpole: str,
    world_id: str,
    used_evidence: set[str],
) -> dict[str, Any]:
    kind = _clean(c.get("product")) or "variant"
    h = frame["horizontal"][hpole]
    v = frame["vertical"][vpole]
    ref = _ref(c)
    bullets = [{"label": "Trigger", "text": _end(_title(c))}]
    hist = _history(c, role="external_driver" if kind == "shock" else "", used=used_evidence)
    if hist:
        bullets.append({"label": "Evidence today", "text": hist})
    nxt = _variant_next(c)
    if nxt:
        bullets.append({"label": "What happens next", "text": _end(nxt)})
    bullets.append({
        "label": "Where Europe ends up",
        "text": (
            f"The development plays out inside a 2035 Europe with {v['label'].lower()} and "
            f"{h['label'].lower()}. It changes the route through that world without changing the two uncertainties that define it."
        ),
    })
    return {
        "id": f"{world_id}:{kind}:{_clean(c.get('id'))[-12:]}",
        "kind": kind,
        "name": _title(c),
        "trigger": _title(c),
        "bullets": bullets,
        **{k: v for k, v in ref.items() if k in ("finding_id", "product", "sources")},
    }


def _build_axis_frame(
    spec: dict[str, Any],
    publications: dict[str, Any],
    candidates: list[dict[str, Any]],
    evaluated_at: str,
) -> dict[str, Any]:
    by_id = {_clean(c.get("id")): c for c in candidates if isinstance(c, dict) and _clean(c.get("id"))}
    pools = {p: _pub(publications, by_id, p) for p in ("trend", "continuity", "risk", "opportunity", "shock")}
    if not any(pools.values()):
        return {
            "id": spec["id"], "title": spec["title"], "question": spec["question"],
            "axes": {"horizontal": _public_axis(spec["horizontal"]), "vertical": _public_axis(spec["vertical"])},
            "scenarios": [], "card_count": 0,
        }

    frame = spec
    scenarios: list[dict[str, Any]] = []
    used_variants: set[str] = set()
    used_evidence: set[str] = set()

    # Matrix order: upper-left, upper-right, lower-left, lower-right.
    for vpole, hpole in (("high", "low"), ("high", "high"), ("low", "low"), ("low", "high")):
        h = frame["horizontal"][hpole]
        v = frame["vertical"][vpole]
        wid = f"{vpole}-{hpole}"
        seed = f"{frame['id']}:{wid}:"

        # Reuse the same strongest current tension for an axis across all four
        # quadrants; only the side carried forward changes. This makes the
        # matrix a coherent test of the same uncertainty rather than four
        # unrelated trend selections.
        vdriver = _axis_driver(pools["trend"], frame["vertical"], vpole, f"{frame['id']}:vertical", set())
        hdriver = _axis_driver(pools["trend"], frame["horizontal"], hpole, f"{frame['id']}:horizontal", set())
        drivers = [d for d in (vdriver, hdriver) if d]

        # Context findings may recur across quadrants when they are the best
        # evidence for the axis. Forcing uniqueness here quickly pushes later
        # quadrants toward off-topic evidence; uniqueness matters for the four
        # subscenario triggers, not for the shared evidence base.
        persists = _choose_world_finding(pools["continuity"], frame, hpole, vpole, seed + "continuity", set())
        opportunity = _choose_world_finding(pools["opportunity"], frame, hpole, vpole, seed + "opportunity", set())
        risk = _choose_world_finding(pools["risk"], frame, hpole, vpole, seed + "risk", set())

        name = f"{v['short']} · {h['short']}"
        tagline = f"{v['label']}; {h['label']}."
        picture = (
            f"In this 2035 world, Europe combines {v['label'].lower()} with {h['label'].lower()}. "
            "The world is a scenario frame, not a forecast; the details below are rebuilt from the Radar's current published findings."
        )
        bullets: list[dict[str, str]] = [{"label": "Picture", "text": picture}]
        sides = [f"“{d['winning_side']}”" for d in drivers if _clean(d.get("winning_side"))]
        if len(sides) >= 2:
            bullets.append({"label": "How we got here", "text": f"Two current tensions are carried forward into this world: {sides[0]} and {sides[1]}."})
        elif sides:
            bullets.append({"label": "How we got here", "text": f"One current tension carried forward into this world is {sides[0]}."})

        hist = _history(persists, used=used_evidence) if persists else ""
        if hist:
            bullets.append({"label": "Evidence today", "text": hist})
        if opportunity:
            bullets.append({"label": "Opportunity in the evidence", "text": _end(_clean(opportunity.get("reader_why") or opportunity.get("reader_summary") or _title(opportunity)))})
        if risk:
            bullets.append({"label": "Risk in the evidence", "text": _end(_clean(risk.get("reader_why") or risk.get("reader_summary") or _title(risk)))})

        watch = next((_clean(d.get("watch")) for d in drivers if _clean(d.get("watch")) and not _clean(d.get("watch")).startswith("Nothing")), "")
        if watch:
            bullets.append({"label": "Signpost", "text": watch})

        # Four subscenarios: two external shocks, one opportunity and one risk,
        # with thematic ranking first and graceful fallback if a pool is thin.
        variants: list[dict[str, Any]] = []
        for kind, count in (("shock", 2), ("opportunity", 1), ("risk", 1)):
            for n in range(count):
                c = _choose_world_finding(pools[kind], frame, hpole, vpole, seed + f"{kind}:{n}", used_variants)
                if c:
                    variants.append(_generic_variant(c, frame, hpole, vpole, wid, used_evidence))

        if len(variants) < 4:
            fallback = [*pools["shock"], *pools["opportunity"], *pools["risk"], *pools["continuity"], *pools["trend"]]
            while len(variants) < 4:
                c = _choose_world_finding(fallback, frame, hpole, vpole, seed + f"fallback:{len(variants)}", used_variants)
                if not c:
                    break
                variants.append(_generic_variant(c, frame, hpole, vpole, wid, used_evidence))

        signals = [x for x in drivers]
        for c in (persists, opportunity, risk):
            if c:
                signals.append(_ref(c))
        scenarios.append({
            "id": wid,
            "frame_id": frame["id"],
            "name": name,
            "tagline": tagline,
            "quadrant": {
                frame["horizontal"]["key"]: h["id"],
                frame["vertical"]["key"]: v["id"],
                "horizontal": h["id"],
                "vertical": v["id"],
            },
            "story": [picture],
            "bullets": bullets,
            "signals": signals,
            "watch": watch,
            "variants": variants[:4],
        })

    return {
        "id": frame["id"],
        "title": frame["title"],
        "question": frame["question"],
        "method": "The axis pair is curated by hand. The four quadrant scenarios and their four variants are rebuilt from the current published findings on each reasoning refresh; reader-language editing is separate.",
        "axes": {"horizontal": _public_axis(frame["horizontal"]), "vertical": _public_axis(frame["vertical"])},
        "scenarios": scenarios,
        "card_count": len(scenarios) + sum(len(x.get("variants", [])) for x in scenarios),
    }


def build_scenarios_2035(publications: dict[str, Any], candidates: list[dict[str, Any]], evaluated_at: str = "") -> dict[str, Any]:
    """Build all 2035 lenses while preserving the original top-level contract."""
    try:
        from scripts.scenario_axes_2035 import AXIS_FRAMES, DEFAULT_FRAME_ID
    except ImportError:  # pragma: no cover
        from scenario_axes_2035 import AXIS_FRAMES, DEFAULT_FRAME_ID  # type: ignore

    default = _build_default_frame(publications, candidates, evaluated_at)
    frames: list[dict[str, Any]] = []
    for spec in AXIS_FRAMES:
        if spec.get("legacy"):
            frame = {
                "id": spec["id"],
                "title": spec["title"],
                "question": spec["question"],
                "method": default.get("method", ""),
                "axes": {"horizontal": _public_axis(spec["horizontal"]), "vertical": _public_axis(spec["vertical"])},
                "scenarios": default.get("scenarios", []),
                "card_count": default.get("card_count", 0),
            }
        else:
            frame = _build_axis_frame(spec, publications, candidates, evaluated_at)
        frames.append(frame)

    return {
        **default,
        "default_frame_id": DEFAULT_FRAME_ID,
        "frames": frames,
        "frame_count": len(frames),
    }
