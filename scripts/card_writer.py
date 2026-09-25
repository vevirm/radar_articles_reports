"""The reasoning engine's card writer.

Turns a finished reasoning candidate into reader copy: a headline that states the
finding, a lead that shows the evidence behind it in the sources' own words, a
"so what" line and a plain chip naming the kind of reasoning.

Design rules (see STYLE.md and reasoning-reform/CARD_WRITER.md):

* The headline states the *finding* at the level the reasoning supports: a trend
  is headed by the trend, never by one of its anecdotes; a single-source signal is
  headed with its topic so it carries its own context.
* Concrete detail (countries, actors, amounts, timing) comes from the structured
  claim fields and from the Deep-Scan claim statements, never from invention.
* Every sentence is either a sourced statement (with its source and month) or a
  frame sentence built from structured data, grammatical by construction.
* What the Radar infers is marked as the Radar's inference.  Sources are never
  made to say the synthesis.
* Nothing is truncated with an ellipsis; long statements are cut at a clause.

Deterministic and dependency-free: it runs inside the GitHub scan.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any, Iterable

try:
    from scripts import reader_labels as RL
except ImportError:  # pragma: no cover - direct script execution
    import reader_labels as RL  # type: ignore

clean = RL.clean
cap = RL.cap
label = RL.label

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

KIND_LABELS: dict[str, str] = {
    "corroborated": "Confirmed by several sources",
    "several_places": "Seen in several places",
    "early_sign": "Early sign",
    "single_signal": "Single strong signal",
    "continuity": "Keeps coming back",
    "split_recurrence": "An old link returns",
    "era_conjunction": "Issues merging",
    "practice_before_doctrine": "Practice before rules",
    "deployment_before_rules": "Running before rules",
    "clock_before_rule": "Deadline before rules",
    "goal_without_measure": "Goal without a yardstick",
    "success_metric_gap": "Money without a yardstick",
    "stalled_proposal": "Stalled proposal",
    "conflicting_criteria": "Rules in collision",
    "dependency_pathway": "Chain reaction",
    "latent_channel": "Unused lever",
    "anchor_demand": "Ready-made customer",
    "future_shock": "What if",
    "trend": "Tug of war",
    "magnitude_contrast": "Scale check",
    "external_opening": "Opening from abroad",
    "cross_pressure": "Policies at cross purposes",
    "common_driver": "One cause, many fields",
    "national_convergence": "Country by country",
}

# ---------------------------------------------------------------------------
# Small language helpers
# ---------------------------------------------------------------------------

_LOWERABLE_FIRST = {
    "Fresh", "Big", "Europe's", "More", "A", "New",
    "The", "A", "An", "This", "These", "Those", "Several", "Some", "Many", "Most", "New",
    "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "Eighteen", "Current", "Across", "Although", "While", "More", "Major", "Local",
    "Proposed", "Selective", "Implementation", "Research", "National", "Dedicated",
    "Differences", "Different", "Global", "Public", "Private", "Emissions", "Respondents",
    "Participants", "Signatories", "Analysis", "Reduced", "Social", "Security", "Only", "Just", "About", "Around",
}

_REPORTING_PREFIX = re.compile(
    r"^(?:(?:the|this|a|an)\s+)?(?:[A-Z][\w&.’'\-]*\s+){0,5}?"
    r"(?:study|paper|article|report|analysis|brief|review|issue|survey|authors?|researchers?|signatories|"
    r"experts?|respondents|participants|[A-Z]{2,}[\w\-]*)?\s*"
    r"(?:finds?|found|argues?|argued|shows?|showed|reports?|reported|says?|said|concludes?|notes?|warns?|"
    r"estimates?|identifies|identified|proposes?|advocates?|recommends?|documents?|maps?|characterises|"
    r"characterizes|contrasts)\s+(?:that\s+)?",
    re.I,
)

_AMOUNT = re.compile(
    r"(?:(?P<cur1>€|EUR|USD|US\$|\$|£|GBP|DKK|SEK|NOK|CHF)\s?(?P<num1>\d[\d.,]*)\s*(?P<mag1>trillion|billion|million|bn|m)\b"
    r"|(?P<num2>\d[\d.,]*)\s*(?P<mag2>trillion|billion|million|bn)\s*(?P<cur2>euros?|EUR|dollars?|USD|kroner|DKK|SEK|NOK|CHF)\b)",
    re.I,
)
_TO_EUR = {"€": 1.0, "eur": 1.0, "euro": 1.0, "euros": 1.0, "usd": 0.92, "us$": 0.92, "$": 0.92,
           "dollar": 0.92, "dollars": 0.92, "£": 1.17, "gbp": 1.17, "dkk": 0.134, "kroner": 0.134,
           "sek": 0.088, "nok": 0.086, "chf": 1.05}
_MAG = {"trillion": 1e12, "billion": 1e9, "bn": 1e9, "million": 1e6, "m": 1e6}


_SINGULAR_S = {"analysis", "access", "business", "process", "progress", "success", "status", "sovereignty", "focus",
               "consensus", "basis", "crisis", "emphasis", "physics", "economics", "politics", "semiconductors?"}


def is_plural(x: str) -> bool:
    last = clean(x).split(" ")[-1].lower() if clean(x) else ""
    return bool(last) and last.endswith("s") and not last.endswith(("ss", "is", "us")) and last not in _SINGULAR_S


def be(x: str) -> str:
    return "are" if is_plural(x) else "is"


def its(x: str) -> str:
    return "their" if is_plural(x) else "its"


def verb_s(x: str, verb: str) -> str:
    return verb if is_plural(x) else verb + "s"


def words(text: str) -> list[str]:
    return clean(text).split()


def sentence(text: Any) -> str:
    """Clean a statement into one complete sentence ending with a full stop."""
    t = clean(text)
    t = re.sub(r"\s*(?:\.{3,}|…)+\s*$", "", t)
    t = t.rstrip(" ,;:")
    if not t:
        return ""
    if t[-1] not in ".!?":
        t += "."
    return t[0].upper() + t[1:] if t[0].islower() else t


def lower_first(text: str) -> str:
    t = clean(text)
    if not t:
        return t
    first = t.split(" ", 1)[0]
    if first in _LOWERABLE_FIRST or (first.endswith("ing") and first[:1].isupper() and first[1:].islower()
                                     and first not in {"Beijing", "Nanjing", "Reading", "Wuling"}):
        return first.lower() + t[len(first):]
    return t


def clause_cut(text: Any, max_words: int = 30) -> str:
    """Shorten at a clause boundary; never with an ellipsis."""
    t = sentence(text)
    if len(words(t)) <= max_words:
        return t
    for sep in ("; ", ", while ", ", whereas ", ", but ", " — ", ", although ", ", which ", ", with ", ", and "):
        if sep in t:
            head = t.split(sep, 1)[0].rstrip(" ,;:")
            if 6 <= len(words(head)) <= max_words:
                return sentence(head)
    # Last resort: first sentence if it fits, else the whole statement (a complete
    # long sentence is better than a broken short one).
    first = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)[0]
    return sentence(first) if len(words(first)) <= max_words else t


_CLAUSE_SPLIT = re.compile(r";\s+|,\s+(?=(?:while|whereas|but|although|and|which|with)\b)|\s+[—–]\s+")


def focus_clause(text: Any, pattern: str, max_words: int = 28) -> str:
    """The clause of a statement that carries the matched idea, as a sentence."""
    t = sentence(text)
    if not pattern or len(words(t)) <= max_words:
        return clause_cut(t, max_words)
    clauses = [c.strip(" ,;.") for c in _CLAUSE_SPLIT.split(t) if c.strip(" ,;.")]
    for c in clauses:
        if re.search(pattern, c, re.I) and len(words(c)) >= 5:
            c = re.sub(r"^(?:and|but|while|whereas|which|with|although)\s+", "", c, flags=re.I)
            return sentence(c)
    return clause_cut(t, max_words)


def strip_reporting(text: Any) -> str:
    t = clean(text)
    out = _REPORTING_PREFIX.sub("", t, count=1)
    if out != t and len(words(out)) >= 5:
        return out[0].upper() + out[1:]
    return t


def headline_from_statement(text: Any, max_words: int = 16) -> str:
    """A headline-shaped version of one statement, or '' when it will not fit."""
    t = strip_reporting(clause_cut(text, max_words + 6)).rstrip(".")
    return t if 4 <= len(words(t)) <= max_words else ""


def month_year(value: Any) -> str:
    v = clean(value)
    m = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", v)
    if not m:
        return ""
    y, mo = m.group(1), m.group(2)
    if mo and 1 <= int(mo) <= 12:
        return f"{MONTHS[int(mo) - 1]} {y}"
    return y


def exact_day(value: Any) -> dt.date | None:
    v = clean(value)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        try:
            return dt.date.fromisoformat(v)
        except ValueError:
            return None
    return None


def year_of(value: Any) -> str:
    m = re.match(r"^(\d{4})", clean(value))
    return m.group(1) if m else ""


def gap_phrase(first: Any, second: Any) -> str:
    """'The next day', 'Three weeks later', ... between two day-precision dates."""
    a, b = exact_day(first), exact_day(second)
    if not a or not b or b < a:
        return "Later"
    d = (b - a).days
    if d == 0:
        return "The same day"
    if d == 1:
        return "The next day"
    if d <= 6:
        return f"{_number_word(d).capitalize()} days later"
    if d <= 10:
        return "A week later"
    if d <= 45:
        return f"{_number_word(round(d / 7)).capitalize()} weeks later"
    if d <= 330:
        return f"{_number_word(round(d / 30)).capitalize()} months later"
    return "More than a year later"


def _number_word(n: int) -> str:
    table = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
             8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
    return table.get(int(n), str(int(n)))


def amounts(text: Any) -> list[dict[str, Any]]:
    """Money amounts stated in a text, with an approximate euro value."""
    out: list[dict[str, Any]] = []
    for m in _AMOUNT.finditer(clean(text)):
        cur = (m.group("cur1") or m.group("cur2") or "").lower()
        num = m.group("num1") or m.group("num2") or ""
        mag = (m.group("mag1") or m.group("mag2") or "").lower()
        try:
            value = float(num.replace(",", ""))
        except ValueError:
            continue
        rate = _TO_EUR.get(cur, _TO_EUR.get(cur.rstrip("s"), 0.0))
        factor = _MAG.get(mag, 1.0)
        if not rate or value <= 0:
            continue
        out.append({"text": clean(m.group(0)), "eur": value * factor * rate, "currency": cur})
    return out


def money(eur: float) -> str:
    if eur >= 1e9:
        v = eur / 1e9
        return f"€{v:.0f} billion" if v >= 10 else f"€{v:.1f} billion".replace(".0 ", " ")
    v = eur / 1e6
    return f"€{v:.0f} million"


def display_amount(original: str, eur: float) -> str:
    o = clean(original)
    if re.match(r"^(?:€|EUR\b|\d[\d.,]*\s*(?:trillion|billion|million|bn)\s*euros?)", o, re.I):
        return money(eur)
    return f"{o}, about {money(eur)}"


def ratio_phrase(r: float) -> str:
    if r >= 100:
        return f"more than {int(r // 100) * 100:,} times"
    if r >= 10:
        return f"about {int(round(r))} times"
    if r >= 2:
        return f"about {r:.0f} times" if abs(r - round(r)) < 0.25 else f"about {r:.1f} times"
    if r >= 1.1:
        return "more than"
    return "about as much as"


# ---------------------------------------------------------------------------
# Evidence view
# ---------------------------------------------------------------------------

_ACRONYM_STOP = {"EU", "US", "UK", "AI", "R&D", "R&I", "EEA", "OECD", "UN", "USA", "SME", "SMEs", "GW", "MW",
                 "TRL", "HPC", "COST", "CEO", "IP", "GDP", "EPRS", "CNM", "IMB", "ICT", "EUR", "USD", "DKK",
                 "SEK", "NOK", "CHF", "GBP", "TWh", "MWh", "GWh", "PhD", "CRM", "CRMs", "EEA", "ERA", "KEF"}


_COUNTRY_WORDS = {name: r"\b" + re.escape(name.replace("the ", "")) + r"(?:'s|’s)?\b" for name in sorted(RL.EU_MEMBER_STATES)}
_COUNTRY_WORDS.update({"Ukraine": r"\bUkrain(?:e|ian)\b"})
_COUNTRY_ADJ = {"Bulgaria": r"\bBulgarian\b", "Romania": r"\bRomanian\b", "Finland": r"\bFinnish\b", "Germany": r"\bGerman\b",
                "France": r"\bFrench\b", "Spain": r"\bSpanish\b", "Italy": r"\bItalian\b", "Belgium": r"\bBelgian\b",
                "Poland": r"\bPolish\b", "Denmark": r"\bDanish\b", "Sweden": r"\bSwedish\b", "Austria": r"\bAustrian\b",
                "Hungary": r"\bHungarian\b", "Ireland": r"\bIrish\b", "the Netherlands": r"\bDutch\b", "Portugal": r"\bPortuguese\b"}
for _k, _v in _COUNTRY_ADJ.items():
    _COUNTRY_WORDS[_k] = _COUNTRY_WORDS.get(_k, r"$^") + "|" + _v


class Ev:
    """Reader view of one supporting claim."""

    def __init__(self, ref: dict[str, Any], node: dict[str, Any] | None = None):
        node = node or {}
        self.ref = ref
        self.role = clean(ref.get("role"))
        self.statement = sentence(ref.get("source_statement") or node.get("text") or ref.get("title"))
        self.title = clean(ref.get("title") or node.get("_title"))
        self.source = RL.short_name(ref.get("source") or node.get("_source"))
        self.date = clean(ref.get("date") or node.get("status_date"))
        self.when = month_year(self.date)
        actor = node.get("actor") if isinstance(node.get("actor"), dict) else {}
        scope = node.get("scope") if isinstance(node.get("scope"), dict) else {}
        self.actor = RL.short_name(actor.get("name"))
        self.actor_class = clean(actor.get("class"))
        self.scope = clean(scope.get("level"))
        self._scope_countries = [RL.country_name(c) for c in (scope.get("countries") or []) if clean(c)]
        self.countries = list(self._scope_countries)
        for name in _COUNTRY_WORDS:
            if name not in self.countries and re.search(_COUNTRY_WORDS[name], self.statement):
                self.countries.append(name)
        self.kind = clean(ref.get("claim_kind") or node.get("kind"))
        self.status = clean(ref.get("claim_status") or node.get("status"))
        self.mechanism = clean(ref.get("mechanism") or node.get("mechanism"))
        self.object = clean(ref.get("object") or node.get("object"))
        self.direction = clean(node.get("direction"))
        self.qualification = clean(node.get("qualification"))
        self.identity = clean(ref.get("identity"))
        self.amounts = amounts(self.statement) or amounts(self.title)

    # -- classification -------------------------------------------------------
    @property
    def is_measure(self) -> bool:
        return self.kind in {"action", "effect"} and self.status in {
            "operating", "in_force", "adopted", "delivered", "call_open", "under_construction"}

    @property
    def is_plan(self) -> bool:
        return self.kind == "action" and self.status in {"proposed", "announced", "intention", "in_negotiation"}

    @property
    def is_analysis(self) -> bool:
        return self.kind in {"diagnosis", "advocacy"}

    @property
    def sector(self) -> str:
        if self.actor_class == "company":
            return "private"
        if self.actor_class in {"eu_body", "member_state", "national_funder"}:
            return "public"
        return "analysis" if self.is_analysis else "other"

    @property
    def member_states(self) -> list[str]:
        return [c for c in self.countries if c in RL.EU_MEMBER_STATES]

    def cite(self) -> str:
        bits = [b for b in (self.source, self.when) if b]
        return f"({', '.join(bits)})" if bits else ""

    def said(self, max_words: int = 30) -> str:
        body = clause_cut(self.statement, max_words)
        c = self.cite()
        return f"{body[:-1]} {c}." if c and body.endswith(".") else (f"{body} {c}" if c else body)

    def named_instrument(self) -> str:
        """A proper name for the instrument or actor in the statement, if any."""
        text = f"{self.statement} {self.title}"
        for m in re.finditer(r"\b[A-Z][A-Za-z]*[A-Z][A-Za-z0-9\-]*\b|\b[A-Z]{3,}(?:-[A-Z0-9]+)?\b", text):
            tok = m.group(0)
            if tok not in _ACRONYM_STOP and not tok.isdigit():
                return tok
        return ""


def evidence(refs: Iterable[dict[str, Any]], node_by_claim: dict[str, dict[str, Any]], role: str | None = None) -> list[Ev]:
    out: list[Ev] = []
    seen: set[str] = set()
    for ref in refs or []:
        if not isinstance(ref, dict):
            continue
        if role and clean(ref.get("role")) != role:
            continue
        key = clean(ref.get("identity")) or clean(ref.get("claim_id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(Ev(ref, node_by_claim.get(clean(ref.get("claim_id")), {})))
    return out


def by_role(evs: list[Ev]) -> dict[str, list[Ev]]:
    out: dict[str, list[Ev]] = {}
    for e in evs:
        out.setdefault(e.role, []).append(e)
    return out


def distinct_sources(evs: list[Ev]) -> int:
    return len({e.source.lower() for e in evs if e.source})


def member_states(evs: list[Ev]) -> list[str]:
    seen: list[str] = []
    for e in evs:
        for c in e.member_states:
            if c not in seen:
                seen.append(c)
    return seen


def lead_from(evs: list[Ev], limit: int = 2, max_words: int = 28, joiner: str = " ") -> str:
    parts = [e.said(max_words) for e in evs[:limit] if e.statement]
    return joiner.join(parts)


def cluster_of(obj: str, vocab: dict[str, Any] | None) -> str:
    meta = ((vocab or {}).get("objects") or {}).get(clean(obj), {})
    if isinstance(meta, dict) and clean(meta.get("cluster")):
        return clean(meta.get("cluster"))
    if clean(obj).startswith("cluster:"):
        return clean(obj).split(":", 1)[1]
    return ""


def stake_line(obj: str, vocab: dict[str, Any] | None, fallback_label: str = "") -> str:
    s = RL.stake(cluster_of(obj, vocab))
    if s:
        return f"At stake: {s}."
    if fallback_label:
        return f"At stake: what Europe can do with {fallback_label}."
    return ""


def card(kind: str, headline: str, lead: str, so_what: str, basis: str = "", kind_label: str = "") -> dict[str, str]:
    h = clean(headline).rstrip(".")
    return {
        "kind": kind,
        "kind_label": kind_label or KIND_LABELS.get(kind, ""),
        "headline": cap(h) + ("" if h.endswith("?") else "."),
        "lead": clean(lead),
        "so_what": clean(so_what),
        "basis": clean(basis),
    }


# ---------------------------------------------------------------------------
# Level 2: corroborated claims (risks and opportunities)
# ---------------------------------------------------------------------------

_OPPORTUNITY_FRAMES: dict[str, tuple[str, str]] = {
    # mechanism -> (single-development headline, condition that makes it count)
    "funds": ("{X} {be} starting to get dedicated money", "the money turning into working facilities, teams and users"),
    "invests": ("Serious money is starting to move into {x}", "the investment staying and scaling in Europe"),
    "builds": ("{X} {be} starting to be built out", "the new capacity reaching the researchers and firms who need it"),
    "adds_capacity": ("{X} {be} starting to be built out", "the new capacity reaching the researchers and firms who need it"),
    "procures": ("Europe is starting to buy its way into {x}", "the purchases reaching users on fair terms"),
    "collaborates": ("{X} {be} starting to rest on new alliances", "the partnership lasting beyond its launch"),
    "associates": ("Horizon Europe's circle of partners is widening", "equal-terms participation turning into joint projects"),
    "recruits": ("Europe is starting to recruit for {x}", "recruits finding careers that make them stay"),
    "retains": ("New schemes are testing how to improve {x}", "people actually staying once the scheme runs"),
    "launches": ("{X} {be} getting instruments of its own", "the instrument delivering beyond its first call"),
    "supports": ("{X} {be} getting new public support", "support reaching the organisations that need it most"),
    "coordinates": ("{X} {be} starting to be coordinated across borders", "coordination producing joint decisions, not just meetings"),
    "prioritises": ("{X} {be} moving up Europe's priority list", "priorities being matched by budgets"),
    "adopts": ("{X} {be} getting a formal basis", "the adopted measure being implemented on time"),
    "standardises": ("Europe is helping write the rules for {x}", "European work shaping the international standard"),
    "transfers": ("{X} {be} starting to move toward Europe", "others following the same route"),
}

_FUNDING_WORDS = re.compile(r"\b(?:funding|finance|financing|investment|capital|budget|money)\b", re.I)


def _opportunity_single(e: Ev, x: str) -> str:
    if e.object.endswith(".standards") or re.search(r"\bstandards?\b", e.statement) and e.mechanism in {"funds", "standardises"}:
        domain = x.replace(" standards", "").replace("standards", "").strip() or "this technology"
        return f"Europe is paying to shape {domain} standards before others set them"
    frame, _ = _OPPORTUNITY_FRAMES.get(e.mechanism, ("{X} {be} gaining momentum", ""))
    if e.mechanism in {"funds", "invests"} and _FUNDING_WORDS.search(x):
        frame = "{X} {be} growing"
    return frame.format(x=x, X=cap(x), be=be(x))


_RISK_EVENT_FRAMES = (
    (frozenset({"regulates", "requires", "restricts", "conditions", "screens", "licenses", "excludes"}), "{X} {be} starting to come with conditions"),
    (frozenset({"opposes"}), "{X} {be} meeting resistance"),
    (frozenset({"cuts", "withdraws", "reduces"}), "{X} {be} starting to lose support"),
)


def _risk_event_headline(e: Ev, x: str) -> str:
    for mechs, frame in _RISK_EVENT_FRAMES:
        if e.mechanism in mechs:
            return frame.format(X=cap(x), x=x, be=be(x))
    if e.direction == "contracts":
        return f"{cap(x)} {be(x)} starting to lose ground"
    if e.direction == "becomes_contested":
        return f"{cap(x)} could become more contested"
    return f"{cap(x)} {be(x)} coming under pressure"


_CONSTRAINT_TERMS: tuple[tuple[str, str], ...] = (
    (r"\bbarriers?\b", "barriers"), (r"\bweak(?:er|ness|nesses)?\b", "weak spots"), (r"\bgaps?\b", "gaps"),
    (r"\bfragment\w*", "fragmentation"), (r"\bdependen\w*|\breliance\b", "dependence"), (r"\bbottlenecks?\b", "bottlenecks"),
    (r"\buneven\w*", "unevenness"), (r"\bshortages?\b|\bscarc\w*", "shortages"),
    (r"\bconstrain\w*|\bconstraints?\b", "constraints"), (r"\blags?\b|\blagging\b|\bbehind\b", "a gap to rivals"),
)


# What exactly is weak.  "Weak spots" says nothing; "scale-up and exit markets"
# says what the studies found.  Phrases are pulled from the statements with a few
# grammatical patterns and mapped onto R&I system concepts; a concept that several
# statements share comes first.
_WEAK_PATTERNS = (
    r"\bweak(?:er|ening)?\s+((?:[a-z][\w\-]*\s+){0,3}[a-z][\w\-]*)",
    r"\b(?:gaps?|constraints?|bottlenecks?|barriers?|shortages?|shortfalls?)\s+(?:persist\s+)?(?:in|for|to|on|around)\s+((?:[a-z][\w\-]*[\s,]+){0,6}[a-z][\w\-]*)",
    r"\bunderperforms?\s+(?:\w+ly\s+)?in\s+((?:[a-z][\w\-]*[\s,]+){0,6}[a-z][\w\-]*)",
    r"\b((?:[a-z][\w\-]*\s+){0,2}[a-z][\w\-]*)\s+lags?\b",
    r"\b((?:[a-z][\w\-]*[\s,]+){0,6}[a-z][\w\-]*)\s+(?:are\s+|were\s+)?identified as (?:persistent\s+)?gaps",
    r"\b(?:lack|lacks|lacking|absence) of\s+((?:[a-z][\w\-]*\s+){0,3}[a-z][\w\-]*)",
)
_WEAK_CANON = (
    (r"scale-?ups?|scaling|scaleup", "scale-up"),
    (r"commerciali[sz]\w*", "commercialisation"),
    (r"venture (?:capital|investment)|\bvc\b", "venture capital"),
    (r"public[- ]equity|\bipos?\b|\bexits?\b", "exit markets"),
    (r"procurement", "public procurement"),
    (r"patent\w*", "patenting"),
    (r"deployment|market uptake|\bdemand\b", "market demand"),
    (r"entrepreneur\w* education|\bskills?\b|human capital", "skills"),
    (r"\bclusters?\b", "clusters"),
    (r"technology transfer|knowledge transfer", "knowledge transfer"),
    (r"supply chains?", "supply chains"),
    (r"participation|visibility", "equal participation"),
    (r"coordination|fragment\w*", "coordination"),
    (r"legal framework|regulat\w*|\brules\b", "the rules"),
    (r"financ\w*|\bfunding\b|\bcapital\b", "finance"),
)
_WEAK_DROP = {"the", "a", "an", "and", "or", "of", "in", "for", "to", "on", "its", "their", "this", "that", "these", "more",
              "specific", "persistent", "pillars", "indicators", "incentives", "links", "performance", "capacity", "conditions",
              "constraints", "constraint", "gaps", "gap", "barriers", "barrier", "bottlenecks", "shortages", "limits", "weaknesses",
              "problems", "issues", "practical"}


def weak_spots(evs: list[Ev], exclude: str = "") -> tuple[list[str], bool]:
    """(concepts that are weak, whether the first is shared by several statements)."""
    skip = {w for w in re.findall(r"[a-z]+", exclude.lower()) if len(w) > 3}
    seen: dict[str, set[int]] = {}
    order: list[str] = []
    for i, e in enumerate(evs):
        text = e.statement.lower()
        for rx in _WEAK_PATTERNS:
            for m in re.finditer(rx, text):
                phrase = re.split(r"\b(?:while|despite|with|as|because|that|which|than|compared|across)\b", m.group(1))[0]
                for item in re.split(r",|\band\b|\bor\b", phrase):
                    words = [w for w in re.findall(r"[a-z][\w\-]*", item) if w not in _WEAK_DROP]
                    if not words:
                        continue
                    bit = " ".join(words)
                    canon = next((c for rx2, c in _WEAK_CANON if re.search(rx2, bit)), "")
                    if not canon:
                        # Keep only short, clean phrases that read as a thing ("equal participation").
                        if len(words) > 3 or all(w in skip for w in words) or re.search(r"\d", bit) or not re.search(re.escape(bit), text):
                            continue
                        canon = bit
                    if canon in skip or all(w in skip for w in canon.split()):
                        continue
                    seen.setdefault(canon, set()).add(i)
                    if canon not in order:
                        order.append(canon)
    if "finance" in seen and ({"venture capital", "exit markets", "scale-up"} & set(seen)):
        seen.pop("finance"); order.remove("finance")
    ranked = sorted(order, key=lambda c: (-len(seen[c]), order.index(c)))
    return ranked[:3], bool(ranked) and len(seen[ranked[0]]) >= 2


def _weak_phrase(terms: list[str]) -> str:
    return RL.join_names(terms)


def _stay(terms: list[str]) -> str:
    return "stay" if len(terms) > 1 or is_plural(terms[0]) else "stays"


def _shared_constraint(evs: list[Ev]) -> str:
    for rx, term in _CONSTRAINT_TERMS:
        if sum(1 for e in evs if re.search(rx, e.statement, re.I)) >= 2:
            return term
    return ""


def _single_headline(e: Ev, x: str) -> str:
    """Headline for a one-source risk: the finding itself, with its topic as context."""
    # Drop study scaffolding ("Mapping 92 initiatives ... reveals") so the finding leads.
    core = re.sub(r"^(?:mapping|analysing|analyzing|reviewing|surveying|a (?:review|survey|mapping) of|an analysis of)\b[^.]*?\b(?:reveals?|shows?|finds?|suggests?|indicates?)\s+(?:that\s+)?",
                  "", e.statement, flags=re.I)
    stmt = headline_from_statement(cap(core) if core != e.statement else e.statement, 18)
    if not stmt:
        return f"{cap(x)} {be(x)} under strain"
    first = [w.lower() for w in re.findall(r"[A-Za-z]+", stmt)[:4]]
    topic = [w.lower() for w in re.findall(r"[A-Za-z]+", x) if len(w) > 3]
    if topic and any(t in first for t in topic):
        return stmt  # the statement already names its topic up front
    return f"{cap(x)}: {lower_first(stmt)}"


def write_corroborated(product: str, raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    obj = clean(raw.get("object") or cand.get("object"))
    x = label(obj)
    evs = evidence(cand.get("support") or [], node_by_claim)
    n_src = distinct_sources(evs)
    kind = "corroborated" if n_src >= 2 else "single_signal"
    states = member_states(evs)
    direction = clean(raw.get("direction") or cand.get("direction"))
    lead = lead_from(evs, 2)

    places = ""
    event = n_src < 2 and bool(evs) and not any(e.is_analysis for e in evs)
    if product == "risk" and event:
        # One source reporting one event: an early sign, stated about the system.
        head = _risk_event_headline(evs[0], x)
        return card(kind, head, lead, stake_line(obj, vocab, x),
                    "One source so far: an early sign, not yet a pattern.", kind_label=KIND_LABELS["early_sign"])
    if product == "risk":
        analysis = sum(1 for e in evs if e.is_analysis) >= max(1, len(evs) / 2)
        # One source is a signal, not an established pattern: its headline is modal.
        if direction == "becomes_conditional":
            head = (f"{cap(x)} increasingly {verb_s(x, 'come')} with strings attached" if n_src >= 2
                    else _single_headline(evs[0], x) if evs else f"{cap(x)} could come with more strings attached")
        elif direction == "becomes_contested":
            head = (f"{cap(x)} {be(x)} now openly contested" if n_src >= 2
                    else f"{cap(x)} could become more contested")
        else:
            term = _shared_constraint(evs)
            weak, shared = weak_spots(evs, x) if term else ([], False)
            if weak:
                head = (f"{cap(x)} keeps falling short on {_weak_phrase(weak[:1])}" + (f", and on {_weak_phrase(weak[1:])}" if len(weak) > 1 else "")
                        if shared else f"{cap(x)} falls short on {_weak_phrase(weak)}")
            elif len(states) >= 2:
                head = (f"{cap(x)} keeps hitting the same {term} in several member states" if term
                        else f"{cap(x)} {be(x)} under strain in several member states")
            elif n_src >= 2 and analysis:
                head = (f"Independent studies keep finding {term} in {x}" if term
                        else f"Independent studies agree: {x} is falling short")
            elif n_src >= 2:
                head = f"{cap(x)} {be(x)} being squeezed by measures already in force"
            else:
                head = _single_headline(evs[0], x) if evs else f"{cap(x)} is under strain"
        so = stake_line(obj, vocab, x)
        if n_src >= 2:
            basis = "Several independent sources show this directly."
        elif direction == "becomes_contested":
            basis = "One source shows this directly; whether the contestation widens or hardens is the Radar's inference."
        elif direction == "becomes_conditional":
            basis = "One source shows this directly; whether access or participation becomes harder is the Radar's inference."
        else:
            basis = "One source shows this directly; whether it lasts or spreads is the Radar's inference."
        if "member states" in head:
            places = KIND_LABELS["several_places"]
        return card(kind, head, lead, so, basis, kind_label=places)

    # opportunity
    public = any(e.sector == "public" for e in evs)
    private = any(e.sector == "private" for e in evs)
    records = len({e.identity for e in evs if e.identity})
    actors = {e.actor for e in evs if e.actor}
    eu_level = any(e.scope == "eu" for e in evs)
    if records >= 2 and public and private:
        head = f"{cap(x)} {be(x)} growing on two fronts: public and private"
    elif records >= 2 and len(states) >= 2:
        head = f"{cap(x)} {be(x)} expanding in several member states at once"
    elif records >= 2 and eu_level and states:
        head = f"{cap(x)} {be(x)} being pushed at EU level and nationally at once"
    elif records >= 2 and len(actors) == 1:
        head = f"{cap(x)} {be(x)} expanding on {_number_word(records)} fronts at once"
    elif records >= 2:
        head = f"Several separate moves are expanding {x}"
    else:
        head = _opportunity_single(evs[0], x) if evs else f"New momentum for {x}"
    cond = _OPPORTUNITY_FRAMES.get(evs[0].mechanism, ("", ""))[1] if evs else ""
    if head.startswith("Europe is paying to shape"):
        cond = _OPPORTUNITY_FRAMES["standardises"][1]
    so = f"What would make it count: {cond}." if cond else stake_line(obj, vocab, x)
    basis = ("Several independent sources show this directly." if n_src >= 2
             else "One source shows the move; whether it scales is the open question.")
    if "member states" in head or "nationally" in head:
        places = KIND_LABELS["several_places"]
    elif event:
        places = KIND_LABELS["early_sign"]
    return card(kind, head, lead, so, basis, kind_label=places)


# ---------------------------------------------------------------------------
# Continuity (ongoing phenomena)
# ---------------------------------------------------------------------------

_CONTINUITY_TITLES = {
    "research.collaboration": "Research collaboration keeps changing shape, not disappearing",
    "innovation.system_performance": "Europe keeps returning to the same problem: turning research into companies",
    "ai.governance": "AI governance keeps moving from principles into operating rules",
    "research.system_governance": "Research governance keeps being pulled toward competitiveness",
    "goal.strategic_autonomy": "Strategic autonomy keeps spreading through research and technology policy",
    "research.infrastructure": "Research infrastructure keeps becoming a strategic asset in its own right",
    "talent.retention": "Keeping researchers keeps returning as Europe's capacity limit",
    "talent.recruitment_abroad": "Europe keeps trying to recruit researchers from abroad",
    "research_security.screening": "Research security keeps moving into ordinary research administration",
    "chips.international_cooperation": "Europe keeps looking abroad for chip partnerships",
    "funding.route": "Where Europe's research money should go keeps coming back as a question",
    "family:innovation": "The innovation gap keeps coming back in new forms",
    "family:digital": "Digital policy keeps merging rules, infrastructure and security",
    "family:industrial": "Europe keeps rediscovering that research does not automatically become industry",
    "family:research": "The research system keeps being asked to deliver more than research",
    "family:talent": "The contest for research talent keeps returning",
    "family:compute": "Compute keeps coming back as the limit on European AI",
}

_KIND_WORD = {"action": "action", "effect": "measured effects", "diagnosis": "analysis", "advocacy": "calls to act"}

# What the persistence means, per object (curated pattern statements, formerly
# hard-wired in phenomena/index.html; now the engine's so-what for continuity).
_OPENNESS = "Europe is still balancing open research against protecting sensitive knowledge, data and partnerships."
_TALENT = "Skills, mobility and career conditions decide whether Europe keeps the specialised scientific capability it trains."
_INDUSTRY = "Strong research still does not automatically become globally competitive firms or production capacity in Europe."
_SYSTEM = "Funding, careers, infrastructure and governance keep deciding how resilient and productive European research is as a whole."
_CONTINUITY_PATTERNS = {
    "talent.recruitment_abroad": "Europe's pull on researchers still depends on mobility, career conditions and the competition for specialised talent.",
    "talent.retention": _TALENT,
    "talent.career_structure": _TALENT,
    "innovation.system_performance": "Europe still produces strong research but struggles to turn it into scaled firms, products and industrial capacity.",
    "innovation.deep_tech_startups": "Deep-tech start-ups still have to turn research breakthroughs into firms that can finance, scale and stay in Europe.",
    "industrial.competitiveness": _INDUSTRY,
    "goal.strategic_autonomy": "More research and technology decisions are shaped by whether Europe can act without critical outside dependencies.",
    "research.system_governance": _SYSTEM,
    "research.system_capacity": _SYSTEM,
    "funding.route": "Public research money is increasingly tied to capabilities Europe considers strategically important.",
    "research.collaboration": "Collaboration continues, but security, funding and strategic interests are reshaping how partnerships work.",
    "research.openness": _OPENNESS,
    "research.open_access": _OPENNESS,
    "research.infrastructure": "Shared facilities and computing systems now matter directly to European resilience and strategic capability.",
    "research.infrastructure_access": "Shared facilities and computing systems now matter directly to European resilience and strategic capability.",
    "research_security.screening": "Collaboration remains important, but partners, data and knowledge flows face tighter security conditions.",
    "materials.critical_raw": "Access to critical raw materials remains a constraint on European research, manufacturing and strategic technologies.",
    "family:chips": "European chip ambitions still depend on fabs, supply chains, investment and access to specialised technology.",
    "family:digital": "Digital policy increasingly links regulation, infrastructure, security and industrial competitiveness rather than treating them separately.",
    "family:ai": "AI policy increasingly connects computing capacity, skills, research access, industrial capability and strategic dependence.",
    "family:compute": "Access to large computing systems decides which technologies European researchers and firms can develop on their own terms.",
    "family:export_control": "Technology competition increasingly decides which partnerships, inputs and markets stay open to European research.",
    "family:research_security": "Collaboration remains important, but partners, data and knowledge flows face tighter security conditions.",
    "family:innovation": "The recurring challenge is turning research strength into productivity, commercialisation and competitive growth.",
    "family:industrial": _INDUSTRY,
    "family:methods": "Long-term planning is being pulled closer to decisions about security, capability and international dependence.",
    "family:energy": "Research and production stay exposed when essential inputs come from concentrated outside suppliers.",
    "family:materials": "Research and production stay exposed when essential inputs come from concentrated outside suppliers.",
    "family:research": _SYSTEM,
    "family:talent": _TALENT,
    "family:funding": "Public research money is increasingly tied to capabilities Europe considers strategically important.",
    "family:horizon": "Public research money is increasingly tied to capabilities Europe considers strategically important.",
    "family:defence": "European research policy keeps being asked how close it should come to defence, and each instrument answers separately.",
    "family:quantum": "Quantum keeps moving from laboratory promise toward infrastructure that someone has to build, pay for and secure.",
    "family:datacentre": "Where compute can physically be built is becoming as decisive as how much of it Europe can afford.",
    "family:green": "Clean technology keeps testing whether Europe can turn research leadership into manufacturing at scale.",
    "family:health": "Health research keeps depending on data and infrastructure that cross national borders more easily than the rules do.",
    "family:finance": "Europe keeps producing ideas faster than the capital that could scale them.",
    "family:goal": "More research and technology decisions are shaped by whether Europe can act without critical outside dependencies.",
}


def continuity_pattern(obj: str) -> str:
    obj = clean(obj)
    return _CONTINUITY_PATTERNS.get(obj) or _CONTINUITY_PATTERNS.get("family:" + obj.split(".", 1)[0], "")


def write_named_continuity(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    obj = clean(raw.get("object") or cand.get("object"))
    x = label(obj)
    now = evidence(cand.get("support") or [], node_by_claim)
    then = evidence(cand.get("continuity_history") or [], node_by_claim)
    keys = [w for w in re.findall(r"[a-z]{4,}", x.lower()) if w not in {"european", "europe", "research", "access", "public"}]
    syn = {"chip": "semiconductor", "chips": "semiconductor", "compute": "comput", "computing": "comput"}
    keys += [syn[k] for k in keys if k in syn]

    def relevance(e: Ev) -> int:
        t = e.statement.lower()
        return sum(1 for k in keys if k[:6] in t)
    then = sorted(then, key=lambda e: (-relevance(e), e.date))
    then = [e for e in then if relevance(e) > 0] or then
    then.sort(key=lambda e: e.date)  # earliest relevant first
    now = sorted(now, key=lambda e: -relevance(e))
    since = year_of(then[0].date) if then else ""
    head = _CONTINUITY_TITLES.get(obj) or (f"{cap(x)} is still on Europe's agenda, as it was in {since}" if since else f"{cap(x)} keeps coming back")
    parts = []
    if then:
        e = then[0]
        parts.append(f"Earlier: {lower_first(clause_cut(e.statement, 24))[:-1]} {e.cite()}.".replace("  ", " "))
    if now:
        e = now[0]
        parts.append(f"Now: {lower_first(clause_cut(e.statement, 24))[:-1]} {e.cite()}.".replace("  ", " "))
        if len(now) > 1:
            parts.append(now[1].said(24))
    # Shape change: what kind of evidence dominates now versus before.
    def dominant(evs: list[Ev]) -> str:
        counts: dict[str, int] = {}
        for e in evs:
            counts[e.kind] = counts.get(e.kind, 0) + 1
        return max(counts, key=counts.get) if counts else ""
    dn, dt_ = dominant(now), dominant(then)
    form = ""
    if dn and dt_ and dn != dt_ and _KIND_WORD.get(dn) and _KIND_WORD.get(dt_):
        form = f"What has changed is the form: the earlier record is mostly {_KIND_WORD[dt_]}, the current one mostly {_KIND_WORD[dn]}."
    pattern = continuity_pattern(obj)
    so = " ".join(p for p in (pattern, form) if p) or "An issue that survives several policy cycles is structural; expect it in the next programme too."
    return card("continuity", head, " ".join(parts), so, "Recurrence across the historical and current record; no single source says it persists.")


def write_split_recurrence(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    eps = [clean(v) for v in (raw.get("endpoint_objects") or []) if clean(v)]
    a, b = (label(eps[0]), label(eps[1])) if len(eps) >= 2 else ("one issue", "another")
    evs = evidence((cand.get("support") or []) + (cand.get("context") or []), node_by_claim)
    roles = by_role(evs)
    hist = (roles.get("historical_relation") or [None])[0]
    side_a = (roles.get("side_a") or [None])[0]
    side_b = (roles.get("side_b") or [None])[0]
    head = f"{cap(a)} and {b} were linked before, and both are moving again"
    parts = []
    if hist:
        yr = year_of(hist.date)
        parts.append(f"{'In ' + yr + ', ' if yr else 'Earlier, '}{lower_first(clause_cut(hist.statement, 26))[:-1]} {hist.cite()}.".replace("  ", " "))
    if side_a:
        parts.append(f"Now: {lower_first(side_a.said(22))}")
    if side_b:
        parts.append(side_b.said(22))
    so = "No current source joins the two yet. The Radar flags the link because it mattered before and both sides are active again."
    return card("split_recurrence", head, " ".join(parts), so, "Radar inference from a historical link plus current movement on both sides.")


def write_era_conjunction(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    eps = [clean(v) for v in (raw.get("endpoint_objects") or []) if clean(v)]
    a, b = (label(eps[0]), label(eps[1])) if len(eps) >= 2 else ("two issues", "each other")
    evs = evidence(cand.get("support") or [], node_by_claim)
    head = f"{cap(a)} and {b} are turning into one story"
    so = "They now appear together far more often than in the historical record, so decisions on one will increasingly shape the other."
    return card("era_conjunction", head, lead_from(evs, 2), so, "Radar comparison of current and historical co-occurrence.")


# ---------------------------------------------------------------------------
# Level 3: timing and gap findings (risks)
# ---------------------------------------------------------------------------

def _where(e: Ev | None) -> str:
    if not e:
        return ""
    ms = e.member_states
    return f" in {RL.join_names(ms)}" if ms and len(ms) <= 2 else ""


def write_sequence(grammar: str, raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    obj = clean(raw.get("object") or cand.get("object"))
    x = label(obj)
    evs = evidence(cand.get("support") or [], node_by_claim)
    roles = by_role(evs)
    if grammar == "practice_before_doctrine":
        first = (roles.get("practice") or evs[:1] or [None])[0]
        later = (roles.get("doctrine") or evs[1:2] or [None])[0]
        head = f"{cap(x)} {be(x)} moving faster than {its(x)} rules{_where(first)}"
        so = "What gets built first tends to set the terms that the later rules have to accept."
        basis = "Dated sources show the practice before the framework; the lock-in risk is the Radar's inference."
    elif grammar == "deployment_before_rules":
        first = (roles.get("deployment") or evs[:1] or [None])[0]
        later = (roles.get("first_rule") or evs[1:2] or [None])[0]
        head = f"{cap(x)} {be(x)} operating before {its(x)} rules are settled{_where(first)}"
        so = "Operations that start first can lock in choices the rules then have to accommodate."
        basis = "Dated sources show operation before adoption; the lock-in risk is the Radar's inference."
    else:  # clock_before_rule
        first = (roles.get("commitment") or evs[:1] or [None])[0]
        later = (roles.get("rule") or evs[1:2] or [None])[0]
        head = f"{cap(x)} {be(x)} on a deadline {its(x)} rules have not caught up with"
        so = "A running clock can force choices on sites, power or eligibility before the rules for them exist."
        basis = "Sources show the deadline and the unsettled rules; the squeeze is the Radar's inference."
    parts = []
    if first:
        parts.append(first.said(28))
    if later:
        gap = gap_phrase(first.date if first else "", later.date)
        parts.append(f"{gap}, {lower_first(clause_cut(later.statement, 28))[:-1]} {later.cite()}.".replace("  ", " "))
    return card(grammar, head, " ".join(parts), so, basis)


def write_success_gap(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    objective = label(raw.get("objective_object") or cand.get("object"))
    delivery = label(raw.get("delivery_object") or raw.get("objective_object") or cand.get("object"))
    evs = evidence(cand.get("support") or [], node_by_claim)
    roles = by_role(evs)
    d = (roles.get("delivery_instrument") or evs[:1] or [None])[0]
    s = (roles.get("success_condition") or evs[1:2] or [None])[0]
    head = (f"Money for {delivery} is flowing; proof that it improves {objective} is not" if delivery != objective
            else f"Money for {objective} is flowing; proof that it works is not")
    parts = [e.said(26) for e in (d, s) if e]
    parts.append(f"None of the evidence yet measures whether {objective} is actually improving.")
    return card("success_metric_gap", head, " ".join(parts), "Spending can grow for years without anyone knowing whether it works.",
                "The missing measure is the Radar's reading of the evidence, not proof that no metric exists.")


def write_goal_without_measure(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    x = label(raw.get("object") or cand.get("object"))
    inv = int(raw.get("invocations", 0) or 0)
    meas = int(raw.get("measurements", 0) or 0)
    evs = evidence(cand.get("support") or [], node_by_claim)
    head = f"Everyone invokes {x}; almost no one measures it"
    lead = f"The current evidence invokes {x} {inv} times but measures an outcome {meas} times. " + lead_from(evs, 1)
    return card("goal_without_measure", head, lead, "A goal that is never measured can justify almost any spending.",
                "Counts from the Radar's current evidence base.")


def write_stalled(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    x = label(raw.get("object") or cand.get("object"))
    evs = evidence(cand.get("support") or [], node_by_claim)
    since = evs[0].when if evs else ""
    head = f"A proposal on {x} has not moved{' since ' + since if since else ''}"
    return card("stalled_proposal", head, lead_from(evs, 1) + " Nothing in the evidence shows a decision since.",
                "A proposal that ages without a decision leaves everyone planning around an open question.",
                "Status tracking across the Radar's evidence.")


# ---------------------------------------------------------------------------
# Level 4/5: collisions, chains, levers
# ---------------------------------------------------------------------------

def write_conflicting(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    eps = [clean(v) for v in (raw.get("endpoint_objects") or []) if clean(v)]
    a = label(eps[0]) if eps else "one rule"
    b = label(eps[1]) if len(eps) > 1 else "another"
    evs = evidence(cand.get("support") or [], node_by_claim)
    roles = by_role(evs)
    ca = (roles.get("criterion_a") or [None])[0]
    cb = (roles.get("criterion_b") or [None])[0]
    gap = (roles.get("arbitration_gap") or [None])[0]
    head = f"{cap(a)} and {b} pull the same projects in opposite directions" if a != b else f"Two rules on {a} pull in opposite directions"
    parts = []
    if ca:
        parts.append(f"One pull: {lower_first(ca.said(24))}")
    if cb:
        parts.append(f"The other: {lower_first(cb.said(24))}")
    if gap:
        parts.append(gap.said(24))
    return card("conflicting_criteria", head, " ".join(parts),
                "Without a tie-break, the same project can get different answers depending on which rule is applied first.",
                "Each requirement is sourced; the collision is the Radar's inference.")


def write_dependency(product: str, raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    eps = [clean(v) for v in (raw.get("endpoint_objects") or []) if clean(v)]
    capability = clean(raw.get("capability_object") or (eps[0] if eps else ""))
    dependency = clean(raw.get("dependency_object") or (eps[1] if len(eps) > 1 else ""))
    c_label, d_label = label(capability), label(dependency)
    evs = evidence(cand.get("support") or [], node_by_claim)
    roles = by_role(evs)
    commit = (roles.get("commitment") or [None])[0]
    couple = (roles.get("coupling") or [None])[0]
    expo = (roles.get("exposure") or roles.get("propagation") or [None])[0]
    if product == "shock":
        head = f"If {d_label} breaks, {c_label} goes with it"
    else:
        head = f"{cap(c_label)} {be(c_label)} only as strong as {d_label}"
    parts = []
    if commit:
        parts.append(commit.said(26))
    if couple:
        parts.append(f"But {lower_first(couple.said(26))}")
    keys = {w for l in (c_label, d_label) for w in re.findall(r"[a-z]{4,}", l.lower())} - {
        "european", "europe", "research", "public", "access", "capacity", "joint"}
    if expo and expo is not commit and any(k[:6] in expo.statement.lower() for k in keys):
        parts.append(expo.said(24))
    so = f"A failure in {d_label} would reach {c_label} before Europe could substitute."
    return card("dependency_pathway", head, " ".join(parts), so, "Each link is sourced; the chain as a whole is the Radar's inference.")


_LEVER_KIND = {
    "procures": ("buys at scale", "Whoever buys at this scale can attach conditions to access, a way to act on {need} without new law."),
    "funds": ("funds", "Funding conditions can steer {need} faster than new regulation."),
    "invests": ("invests", "Investment terms can steer {need} faster than new regulation."),
    "standardises": ("sets standards", "Standards written now decide who can compete later."),
    "certifies": ("certifies", "Certification decides who may take part, which makes it a lever for {need}."),
    "coordinates": ("coordinates", "An existing network can carry {need} without building new institutions."),
    "collaborates": ("partners", "An existing partnership can carry {need} without building new institutions."),
    "associates": ("associates partners", "Association terms can carry {need} to partners outside the EU."),
    "regulates": ("regulates", "Rules already in force can be extended to {need} faster than new ones can be written."),
    "prioritises": ("sets priorities", "Existing priorities can be re-aimed at {need} without a new programme."),
    "builds": ("builds", "What Europe builds for one purpose can be opened to serve {need}."),
    "launches": ("runs", "A running instrument can take on {need} faster than a new one can be set up."),
    "supports": ("supports", "A running support scheme can take on {need} faster than a new one can be set up."),
}


def write_latent(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    eps = [clean(v) for v in (raw.get("endpoint_objects") or []) if clean(v)]
    need_obj = eps[0] if eps else clean(raw.get("objective_object"))
    tool_obj = eps[1] if len(eps) > 1 else clean(raw.get("delivery_object"))
    need, tool = label(need_obj), label(tool_obj)
    evs = evidence(cand.get("support") or [], node_by_claim)
    roles = by_role(evs)
    gap = (roles.get("unresolved_need") or [None])[0]
    lever = (roles.get("existing_structure") or [None])[0]
    recv = (roles.get("receiving_instrument") or roles.get("live_connection") or [None])[0]
    prec = (roles.get("precedent") or [None])[0]
    head = f"{cap(tool)} could double as a lever for {need}"
    parts = []
    if gap:
        parts.append(f"The gap: {lower_first(gap.said(26))}")
    if lever:
        parts.append(f"The lever: {lower_first(lever.said(26))}")
    if recv and recv is not gap:
        parts.append(f"Already in place: {lower_first(recv.said(22))}")
    elif prec:
        parts.append(f"A precedent: {lower_first(prec.said(22))}")
    mech = lever.mechanism if lever else ""
    so = _LEVER_KIND.get(mech, ("", "It would use something Europe already runs instead of building from scratch."))[1].format(need=need)
    return card("latent_channel", head, " ".join(parts), so, "No source makes this connection yet; it is the Radar's inference.")


def write_anchor_demand(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    eps = [clean(v) for v in (raw.get("endpoint_objects") or []) if clean(v)]
    a = label(eps[0]) if eps else "a European commitment"
    b = label(eps[1]) if len(eps) > 1 else "European suppliers"
    evs = evidence(cand.get("support") or [], node_by_claim)
    head = f"{cap(a)} could become a steady customer for {b}"
    return card("anchor_demand", head, lead_from(evs, 2),
                "Reliable public demand is what turns research support into lasting production.",
                "The demand link is the Radar's inference.")


# ---------------------------------------------------------------------------
# Future shocks
# ---------------------------------------------------------------------------

_SHOCK_EVENT = {
    "export_control": "new export controls",
    "critical_input": "a critical-materials squeeze",
    "security_reclassification": "a sudden security reclassification",
    "acquisition": "a foreign takeover",
    "conflict": "a wider war",
    "sanctions": "new sanctions",
    "data_access": "a data-transfer ban",
    "cyber": "a major cyberattack",
    "energy": "a power squeeze",
    "commercial": "a key supplier pulling out",
    "external_finance": "foreign capital pulling back",
    "funding_cut": "a budget cut",
    "talent_flight": "a researcher exodus",
    "political_shift": "a political U-turn",
    "regulatory_shift": "an abrupt rule change",
    "tech_leap": "a rival's breakthrough",
    "info_manipulation": "a disinformation campaign",
    "chokepoint": "a supplier chokepoint",
    "hazard": "a climate or health emergency",
}

_SHOCK_EVENT_SPECIAL: tuple[tuple[str, str, str], ...] = (
    ("export_control", r"rare[- ]earth", "rare-earth export controls"),
    ("export_control", r"\bchips?\b|semiconductor", "chip export controls"),
    ("critical_input", r"rare[- ]earth", "a rare-earth squeeze"),
    ("funding_cut", r"against higher (?:total )?(?:eu )?spending", "the push against higher EU spending"),
    ("cyber", r"\bagents?\b", "rogue AI agents"),
)

# How the pressure would reach the asset, per asset cluster.  A pairing without an
# entry here is kept in stock but not published: the engine must be able to say
# *how* a shock would bite before it shows the scenario.
EXPOSURE_MECHANISMS: dict[str, dict[str, str]] = {
    "export_control": {
        "compute_ai": "European AI hardware depends on chips and tools that export licences can withhold.",
        "chips": "Chipmaking in Europe depends on tools and materials that export licences can withhold.",
        "quantum": "Quantum hardware depends on components that are increasingly export-controlled.",
        "defence_dual_use": "Defence production depends on components and materials that export licences can withhold.",
        "industrial_competitiveness": "Industrial production depends on imported materials and components that export licences can withhold.",
        "materials_energy": "Europe imports most of the processed materials that export licences can withhold.",
        "ai_governance": "Access to frontier AI models and chips is increasingly decided by export rules set elsewhere.",
    },
    "critical_input": {
        "compute_ai": "Data centres and AI hardware need materials Europe mostly imports.",
        "chips": "Chipmaking needs gallium, germanium and other materials Europe mostly imports.",
        "quantum": "Quantum devices need rare materials with few suppliers.",
        "defence_dual_use": "Defence production runs on critical materials Europe mostly imports.",
        "industrial_competitiveness": "Industrial production runs on critical materials Europe mostly imports.",
        "research_infrastructure": "Large facilities need specialised materials with few suppliers.",
        "critical_infrastructure": "Grids and networks need critical materials Europe mostly imports.",
        "health": "Medical production needs inputs with few suppliers.",
    },
    "energy": {
        "compute_ai": "AI compute needs firm power, and data centres compete with everyone else for it.",
        "chips": "Fabs need large, stable power supplies.",
        "research_infrastructure": "Big facilities are among the largest single power users in research.",
        "critical_infrastructure": "Critical systems fail first when power is rationed.",
        "industrial_competitiveness": "Energy-intensive production is the first to pause when power is short.",
        "materials_energy": "Materials processing is energy-intensive.",
        "quantum": "Quantum machines need stable power and cooling.",
        "defence_dual_use": "Defence production needs secure power supplies.",
    },
    "cyber": {
        "compute_ai": "Shared compute is a single point that many teams depend on.",
        "chips": "Chip design and production run on connected systems.",
        "research_infrastructure": "Facilities run on connected control systems and shared data.",
        "health": "Health research runs on sensitive data systems.",
        "critical_infrastructure": "Critical systems are prime cyber targets.",
        "digital_governance": "Digital services are the attack surface.",
        "cybersecurity": "Small firms rarely have backup systems to switch to.",
        "research_system": "Universities run large, open networks that are hard to defend.",
        "ai_governance": "AI systems can be manipulated or turned against their users.",
        "funding_programme": "Programme systems hold applications and payments for thousands of teams.",
        "industrial_competitiveness": "Production lines run on connected control systems.",
        "capital_markets": "Financial infrastructure is a prime target.",
        "materials_energy": "Energy systems run on connected controls.",
        "innovation_ecosystem": "Young firms rarely have the security budget of their attackers.",
    },
    "commercial": {
        "compute_ai": "European compute relies on a few non-European vendors for hardware and software.",
        "chips": "Key chip tools and designs come from a handful of vendors.",
        "research_infrastructure": "Facilities rely on proprietary equipment and service contracts.",
        "health": "Health research relies on proprietary platforms and data services.",
        "critical_infrastructure": "Operators rely on a few vendors for key systems.",
        "capital_markets": "European start-ups rely on a few large investors and platforms.",
        "digital_governance": "Public digital services run on a few non-European platforms.",
        "cybersecurity": "Small firms depend on a few security vendors.",
        "materials_energy": "Supply contracts can be repriced or withdrawn.",
        "innovation_ecosystem": "Young firms depend on a few platforms and investors.",
        "industrial_competitiveness": "Producers depend on a few suppliers for key parts.",
        "research_system": "Research depends on commercial databases and software licences.",
        "funding_programme": "Programmes depend on commercial systems and data.",
        "talent": "Research careers depend on commercial platforms for publishing and collaboration.",
        "quantum": "Quantum work depends on a few specialised suppliers.",
        "defence_dual_use": "Defence production depends on a few specialised suppliers.",
        "ai_governance": "AI governance depends on access to a few model providers.",
    },
    "sanctions": {
        "compute_ai": "Sanctions can cut suppliers, payments or partners for compute projects.",
        "chips": "Sanctions can cut supply chains that run through third countries.",
        "quantum": "Sanctions can cut suppliers and research partners.",
        "research_infrastructure": "International facilities have members on both sides of sanctions lines.",
        "health": "Clinical and data partnerships cross sanctions lines.",
        "talent": "Sanctions can bar researchers or payments.",
        "funding_programme": "Programme payments and partners can fall under sanctions.",
        "defence_dual_use": "Dual-use supply chains are the first to be sanctioned.",
        "critical_infrastructure": "Suppliers and payments can fall under sanctions.",
        "capital_markets": "Sanctions can freeze investors or assets.",
        "digital_governance": "Sanctions can cut digital service providers.",
        "cybersecurity": "Sanctions can cut security vendors.",
        "industrial_competitiveness": "Sanctions can cut supply chains and export markets.",
        "materials_energy": "Materials and energy flows are frequent sanctions targets.",
        "research_system": "Research partnerships cross sanctions lines.",
        "innovation_ecosystem": "Investors and partners can fall under sanctions.",
        "ai_governance": "Model providers or chips can fall under sanctions.",
    },
    "conflict": {
        "quantum": "Conflict diverts budgets and cuts research partners.",
        "research_infrastructure": "Facilities near or linked to conflict zones can close.",
        "health": "Conflict diverts health research to emergency needs.",
        "talent": "Conflict displaces researchers and diverts money.",
        "funding_programme": "Conflict pulls budget toward defence and reconstruction.",
        "defence_dual_use": "Conflict changes priorities and supply chains overnight.",
        "critical_infrastructure": "Critical infrastructure is a target in conflict.",
        "capital_markets": "Investors pull back when conflict spreads.",
        "cybersecurity": "Conflict comes with cyber campaigns.",
        "materials_energy": "Conflict disrupts energy and materials flows.",
        "research_system": "Conflict cuts partnerships and diverts budgets.",
        "innovation_ecosystem": "Investors pull back when conflict spreads.",
        "compute_ai": "Conflict disrupts supply chains for compute hardware.",
        "chips": "Conflict around key producers would cut chip supply.",
        "industrial_competitiveness": "Conflict disrupts supply chains and markets.",
        "ai_governance": "Conflict shifts AI policy toward security.",
    },
    "data_access": {
        "compute_ai": "Training and serving AI needs data that can cross borders.",
        "quantum": "Cross-border research data flows can be restricted.",
        "research_infrastructure": "Facilities share data with partners abroad.",
        "health": "Health research depends on cross-border data use.",
        "talent": "Mobile researchers need access to their data wherever they work.",
        "funding_programme": "Joint projects depend on sharing data across borders.",
        "digital_governance": "Digital services depend on cross-border data.",
        "research_system": "Research depends on sharing data across borders.",
        "ai_governance": "AI rules and data rules are tightly linked.",
        "capital_markets": "Financial services depend on data flows.",
        "critical_infrastructure": "Operators share data across borders.",
        "innovation_ecosystem": "Start-ups depend on cross-border data.",
        "chips": "Chip design collaboration depends on data exchange.",
    },
    "security_reclassification": {
        "compute_ai": "AI compute is increasingly treated as security-relevant.",
        "chips": "Chip know-how is increasingly treated as security-relevant.",
        "quantum": "Quantum is increasingly treated as a security technology.",
        "research_infrastructure": "Facilities host foreign users who could be excluded.",
        "health": "Biotech know-how is increasingly treated as security-relevant.",
        "talent": "Reclassification changes who may be hired and on what.",
        "funding_programme": "Reclassification changes who may be funded and with whom.",
        "defence_dual_use": "Dual-use work attracts civilian researchers who may leave if it is reclassified.",
        "digital_governance": "Digital infrastructure is increasingly treated as security-relevant.",
        "capital_markets": "Security screening can block investors.",
        "research_system": "Reclassification changes who may collaborate on what.",
        "ai_governance": "AI governance is shifting toward security framing.",
        "innovation_ecosystem": "Security framing can deter partners and investors.",
    },
    "acquisition": {
        "compute_ai": "Promising European AI and compute firms are takeover targets.",
        "chips": "European chip firms are strategic takeover targets.",
        "quantum": "European quantum start-ups are takeover targets.",
        "health": "Biotech firms are frequent takeover targets.",
        "capital_markets": "Scale-ups that cannot raise money at home sell abroad.",
        "critical_infrastructure": "Infrastructure operators can be bought.",
        "research_infrastructure": "Spin-offs from facilities can be bought.",
        "innovation_ecosystem": "Young firms that cannot scale at home sell abroad.",
        "industrial_competitiveness": "Industrial firms with key know-how can be bought.",
        "defence_dual_use": "Dual-use firms can be bought through intermediaries.",
        "digital_governance": "Digital service providers can be bought.",
        "materials_energy": "Processing capacity can be bought.",
        "cybersecurity": "Security firms can be bought.",
    },
    "external_finance": {
        "compute_ai": "European AI build-outs lean on foreign capital.",
        "capital_markets": "Late-stage rounds for European firms lean on foreign investors.",
        "innovation_ecosystem": "European start-ups lean on foreign investors for growth rounds.",
    },
    "funding_cut": {
        "funding_programme": "Programme budgets are decided in the same negotiation as every other spending line.",
        "research_system": "Research budgets are often the first discretionary line to be cut.",
        "research_infrastructure": "Facilities need long-term operating money that budget cuts hit first.",
        "talent": "Fellowships and positions are among the first lines to be cut.",
        "health": "Health research budgets compete with care budgets.",
        "quantum": "Quantum programmes need years of steady money to pay off.",
        "innovation_ecosystem": "Public co-investment is often cut before private money follows.",
        "compute_ai": "Public compute projects need multi-year money.",
        "defence_dual_use": "Defence research competes with procurement for the same money.",
    },
    "talent_flight": {
        "talent": "Researchers move when careers are better elsewhere.",
        "research_system": "Research depends on people who can leave.",
        "research_infrastructure": "Facilities depend on a few specialists who are hard to replace.",
        "quantum": "The quantum field is small and specialists are heavily recruited.",
        "compute_ai": "AI specialists are heavily recruited by non-European firms.",
        "health": "Clinical researchers are heavily recruited abroad.",
        "innovation_ecosystem": "Founders move where capital is.",
        "chips": "Chip engineers are scarce and heavily recruited.",
    },
    "political_shift": {
        "funding_programme": "Programme budgets and eligibility rules are political choices.",
        "research_system": "Academic freedom and funding depend on the government of the day.",
        "talent": "Visa and hiring rules change with governments.",
        "digital_governance": "Digital rules change with political majorities.",
        "ai_governance": "AI rules change with political majorities.",
        "research_infrastructure": "Hosting commitments depend on national governments.",
        "health": "Health research priorities change with governments.",
    },
    "regulatory_shift": {
        "ai_governance": "AI rules are still being written and can change quickly.",
        "digital_governance": "Digital rules are still being written and can change quickly.",
        "health": "Health-data and trial rules can change quickly.",
        "compute_ai": "Energy, siting and AI rules for compute are still being written.",
        "capital_markets": "Investment screening and financial rules can change quickly.",
        "innovation_ecosystem": "Start-ups have the least capacity to absorb rule changes.",
        "research_system": "Research rules change through court rulings and new laws.",
        "chips": "Subsidy and export rules for chips are still being written.",
    },
    "tech_leap": {
        "compute_ai": "European AI investment is justified by catching up; a rival leap resets the target.",
        "chips": "Chip investments bet on a technology generation that a rival leap can skip.",
        "quantum": "Quantum programmes bet on one hardware route; a rival breakthrough can make it obsolete.",
        "industrial_competitiveness": "Industrial strategies bet on today's technology generation.",
        "defence_dual_use": "Defence plans bet on today's technology generation.",
        "ai_governance": "AI rules are written for today's capabilities.",
        "innovation_ecosystem": "Start-ups can be overtaken overnight by a better-funded rival.",
        "research_system": "Research priorities can be overtaken by a breakthrough elsewhere.",
    },
    "info_manipulation": {
        "digital_governance": "Digital policy depends on public trust.",
        "cybersecurity": "Information attacks accompany cyber campaigns.",
        "ai_governance": "AI can scale manipulation.",
        "research_system": "Public trust in science can be targeted.",
        "health": "Health research is a frequent disinformation target.",
        "funding_programme": "Programmes depend on political support that campaigns can erode.",
    },
    "chokepoint": {
        "compute_ai": "European compute relies on a handful of non-European suppliers.",
        "chips": "Chipmaking relies on a few irreplaceable suppliers.",
        "digital_governance": "Digital services rely on a few platforms.",
        "critical_infrastructure": "Critical systems rely on a few suppliers.",
        "industrial_competitiveness": "Production relies on a few suppliers for key parts.",
        "materials_energy": "Processed materials come from a few suppliers.",
        "health": "Medical inputs come from a few suppliers.",
        "quantum": "Quantum hardware relies on a few specialised suppliers.",
        "research_infrastructure": "Facilities rely on a few specialised suppliers.",
    },
    "hazard": {
        "research_infrastructure": "Facilities are fixed in place and exposed to extreme weather.",
        "critical_infrastructure": "Critical systems are exposed to extreme weather.",
        "materials_energy": "Energy and materials production is exposed to extreme weather.",
        "health": "Health emergencies divert research capacity.",
        "compute_ai": "Data centres need cooling and water that heatwaves strain.",
    },
}

_SHOCK_CONSEQUENCE = {
    "cyber": "{X} could go offline or be compromised, with little ready backup to switch to.",
    "energy": "{X} could be slowed or paused while power goes to other essential uses.",
    "export_control": "{X} could be cut off from equipment, components or partners it relies on.",
    "security_reclassification": "{X} could lose partners, people or openness almost overnight.",
    "conflict": "Money, people and supply routes behind {x} could be diverted or cut.",
    "critical_input": "{X} could halt where there is no fast substitute.",
    "sanctions": "The money and partnerships behind {x} could be frozen.",
    "acquisition": "Control of {x}, and its know-how, could move outside Europe.",
    "data_access": "{X} could lose lawful access to the data it needs.",
    "commercial": "{X} could lose a service it cannot quickly replace.",
    "external_finance": "{X} could lose the capital it has been counting on.",
    "funding_cut": "{X} could stop mid-course, with teams and equipment stranded.",
    "talent_flight": "{X} could lose expertise it cannot hire back quickly.",
    "political_shift": "Support for {x} could be withdrawn or its rules rewritten.",
    "regulatory_shift": "{X} could have to pause, redesign or seek fresh approval.",
    "tech_leap": "The case for {x} could collapse and money could move elsewhere.",
    "info_manipulation": "Public and political trust in {x} could erode.",
    "chokepoint": "{X} could stall with no ready alternative.",
    "hazard": "Facilities could close and work on {x} halt.",
}


# Where the generic consequence would misdescribe how the asset fails.
_SHOCK_CONSEQUENCE_BY_CLUSTER = {
    ("funding_cut", "talent"): "Fellowships and early-career positions are usually cut first, and the researchers they hold leave for better-funded systems.",
    ("funding_cut", "funding_programme"): "Planned growth in {x} could turn into a freeze, with calls cancelled or shrunk mid-programme.",
    ("funding_cut", "research_infrastructure"): "Facilities would keep their running costs but lose the money for upgrades and staff, and users would move elsewhere.",
    ("energy", "compute_ai"): "{X} would be among the first loads throttled when grids run short, since data centres draw power around the clock.",
    ("talent_flight", "chips"): "Fabs and pilot lines could stand half-staffed: specialised process engineers take years to train.",
    ("political_shift", "funding_programme"): "{X} could be renegotiated in the next budget round, with research competing against louder priorities.",
}


def shock_event(pid: str, driver: Ev | None) -> str:
    text = clean(driver.statement if driver else "")
    for p, rx, phrase in _SHOCK_EVENT_SPECIAL:
        if p == pid and re.search(rx, text, re.I):
            return phrase
    return _SHOCK_EVENT.get(pid, "an external disruption")


def exposure_mechanism(pid: str, asset_cluster: str) -> str:
    return EXPOSURE_MECHANISMS.get(clean(pid), {}).get(clean(asset_cluster), "")


def write_shock(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    eps = [clean(v) for v in (raw.get("endpoint_objects") or cand.get("endpoint_objects") or []) if clean(v)]
    pid = clean(raw.get("pressure_id") or cand.get("pressure_id")) or next((v.split(".", 1)[1] for v in eps if v.startswith("shock_pressure.")), "")
    asset_obj = clean(raw.get("capability_object") or cand.get("capability_object")) or next((v for v in eps if not v.startswith("shock_pressure.")), "")
    asset = label(asset_obj)
    evs = evidence(cand.get("support") or [], node_by_claim)
    roles = by_role(evs)
    commit = (roles.get("commitment") or [None])[0]
    driver = (roles.get("external_driver") or [None])[0]
    bridge = (roles.get("bridge") or [None])[0]
    event = shock_event(pid, driver)
    head = f"What if {event} hit {asset}?"
    parts = []
    if driver:
        parts.append(f"The pressure is real: {lower_first(driver.said(26))}")
    if commit:
        parts.append(f"What is exposed: {lower_first(commit.said(26))}")
    mech = exposure_mechanism(pid, cluster_of(asset_obj, vocab))
    if bridge:
        parts.append(f"Already linked: {lower_first(bridge.said(24))}")
    elif mech:
        parts.append(f"How it would bite: {lower_first(mech)}")
    tpl = (_SHOCK_CONSEQUENCE_BY_CLUSTER.get((pid, cluster_of(asset_obj, vocab)))
           or _SHOCK_CONSEQUENCE.get(pid, "The disruption could remove something {x} depends on before Europe can replace it."))
    so = tpl.format(x=asset, X=cap(asset))
    return card("future_shock", head, " ".join(parts), so, "The connection is the Radar's future hypothesis, built from separate sources, not a forecast made by any of them.")


# ---------------------------------------------------------------------------
# New reasoning moves (scripts/reasoning_moves.py)
# ---------------------------------------------------------------------------

def write_magnitude(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    evs = evidence(cand.get("support") or [], node_by_claim)
    roles = by_role(evs)
    big = (roles.get("larger_amount") or [None])[0]
    small = (roles.get("smaller_amount") or [None])[0]
    frame = clean(raw.get("contrast_frame"))
    big_amt, small_amt = clean(raw.get("larger_text")), clean(raw.get("smaller_text"))
    big_what, small_what = clean(raw.get("larger_label")), clean(raw.get("smaller_label"))
    r = float(raw.get("ratio", 0) or 0)
    if frame == "unit_rivals_programme":
        head = (f"{cap(clean(raw.get('unit_label')))} ({clean(raw.get('unit_text'))}) {clean(raw.get('relation')) or 'rivals'} "
                f"{clean(raw.get('programme_label'))} ({clean(raw.get('programme_text'))})")
        if clean(raw.get("relation")) == "outweighs":
            so = ("When one project outweighs a whole public programme, the larger investor sets the terms for sites, power and people, "
                  "and in this case that is not the programme.")
        else:
            so = "When a single plan comes close to a whole EU programme, the programme no longer sets the direction on its own."
    elif frame == "deal_vs_sector":
        head = f"{cap(big_what)} ({big_amt}) is {ratio_phrase(r)} {small_what} ({small_amt})"
        so = "Money is concentrating on a few champions; the rest of the field competes for a much smaller pool."
    else:  # priority_gap
        head = f"{big_amt} for {big_what}, {small_amt} for {small_what}"
        so = (f"That is {ratio_phrase(r).replace('times', 'to one').replace('about ', 'about ')}. "
              f"At that ratio, {big_what} sets the pace and {small_what} struggles to keep up.")
    parts = []
    for e in (big, small):
        if not e:
            continue
        # Show the sentence that actually carries the amount (often the title).
        if e.amounts and not amounts(e.statement) and e.title:
            parts.append(f"{sentence(e.title)[:-1]} {e.cite()}.")
        else:
            parts.append(e.said(26))
    basis = ("The Radar's comparison of two amounts the sources state. Other instruments also fund these fields, "
             "so the ratio compares these two programmes, not total spending." if frame not in {"unit_rivals_programme", "deal_vs_sector"}
             else "The Radar's comparison of amounts the sources state; the instruments differ in form and timing, so the ratio is indicative.")
    return card("magnitude_contrast", head, " ".join(parts), so, basis)


def write_external_opening(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    evs = evidence(cand.get("support") or [], node_by_claim)
    roles = by_role(evs)
    ext = (roles.get("external_constraint") or [None])[0]
    gains = roles.get("european_gain") or []
    who = clean(raw.get("external_actor"))
    phrase = clean(raw.get("gain_phrase")) or f"Europe in {label(raw.get('gain_object'))}"
    head = f"{who + ' ' if who else 'Outside '}restrictions open a window for {phrase}"
    parts = []
    if ext:
        parts.append(f"Abroad: {lower_first(ext.said(24))}")
    if gains:
        parts.append(f"In Europe: {lower_first(gains[0].said(24))}")
        if len(gains) > 1:
            parts.append(gains[1].said(22))
    so = "What others close can be Europe's to take, but only if the offer is ready before the window shuts."
    return card("external_opening", head, " ".join(parts), so,
                "Each move is sourced; that one opens room for the other is the Radar's inference, not a cause any source reports.")


def write_cross_pressure(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    evs = evidence(cand.get("support") or [], node_by_claim)
    roles = by_role(evs)
    push = (roles.get("push") or [None])[0]
    pull = (roles.get("pull") or [None])[0]
    who = clean(raw.get("population")) or "the same people"
    head = clean(raw.get("headline")) or f"Europe is pulling {who} in two directions at once"
    parts = []
    if push:
        parts.append(f"One policy: {lower_first(push.said(24))}")
    if pull:
        parts.append(f"Another: {lower_first(pull.said(24))}")
    so = clean(raw.get("so_what")) or f"Each policy may work on its own; together they send {who} mixed signals."
    return card("cross_pressure", head, " ".join(parts), so, "Both policies are sourced; that they work against each other is the Radar's inference.")


def write_common_driver(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    evs = evidence(cand.get("support") or [], node_by_claim)
    driver = clean(raw.get("driver_label")) or "one outside dependency"
    fields = [clean(x) for x in (raw.get("field_labels") or []) if clean(x)]
    head = clean(raw.get("headline")) or f"{cap(driver)} now shapes European plans in {RL.join_names(fields[:4])} at once"
    parts = [e.said(20) for e in evs[:3]]
    so = "When one dependency drives several fields, a single outside decision can move them all together; a joint response is also possible."
    return card("common_driver", head, " ".join(parts), so, "Each field is sourced separately; the common driver is the Radar's synthesis.")


def write_national_convergence(raw: dict[str, Any], cand: dict[str, Any], node_by_claim: dict, vocab: dict | None) -> dict[str, str]:
    evs = evidence(cand.get("support") or [], node_by_claim)
    x = clean(raw.get("group_label")) or label(raw.get("object") or cand.get("object"))
    countries = [clean(c) for c in (raw.get("countries") or []) if clean(c)]
    head = f"{cap(x)} {be(x)} being built country by country, not as one European effort"
    parts = [e.said(20) for e in evs[:3]]
    eu = clean(raw.get("eu_state"))
    so = ("National moves are running ahead of a common EU approach; 27 designs are harder to align later than one."
          if eu != "adopted" else "National moves now sit alongside an EU framework; the test is whether they converge on it.")
    return card("national_convergence", head, " ".join(parts), so, "Each national move is sourced; the pattern is the Radar's synthesis.")


# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------

_BUILD = {"builds", "adds_capacity", "procures", "supplies"}
_MONEY = {"funds", "invests", "allocates"}
_PARTNER = {"collaborates", "associates", "coordinates"}
_POLICY = {"adopts", "regulates", "prioritises", "launches", "supports", "proposes", "requires", "standardises", "harmonises"}
_RESTRICT = {"restricts", "excludes", "conditions", "licenses", "screens", "requires", "regulates"}


def _majority(evs: list[Ev], pred) -> bool:
    return bool(evs) and sum(1 for e in evs if pred(e)) >= max(1, (len(evs) + 1) // 2)


def _scope_states(evs: list[Ev]) -> list[str]:
    """Member states named in the *scope* of measures or plans (not merely mentioned)."""
    seen: list[str] = []
    for e in evs:
        if not (e.is_measure or e.is_plan):
            continue
        for c in (e._scope_countries or []):
            if c in RL.EU_MEMBER_STATES and c not in seen:
                seen.append(c)
    return seen


def _state_examples(evs: list[Ev], states: list[str], limit: int = 3) -> tuple[list[Ev], list[str]]:
    """Order examples so the first `limit` cover as many scope states as possible;
    return them with the states those shown examples actually carry."""
    picked: list[Ev] = []
    for c in states:
        if len(picked) >= limit:
            break
        e = next((e for e in evs if c in (e._scope_countries or []) and e not in picked), None)
        if e is not None:
            picked.append(e)
    ordered = picked + [e for e in evs if e not in picked]
    shown = ordered[:limit]
    covered = [c for c in states if any(c in (e._scope_countries or []) for e in shown)]
    return ordered, covered


def _left_side(evs: list[Ev], x: str) -> tuple[str, str, list[Ev]]:
    """(side title, pair-headline phrase, examples that support that title)."""
    concrete_first = sorted(evs, key=lambda e: 0 if e.is_measure else 1 if e.is_plan else 2)
    firms = _majority(evs, lambda e: e.sector == "private")
    states = _scope_states(evs)
    money_label = bool(re.search(r"capital|investment|financ|funding", x))
    if firms and money_label:
        ex, shown_states = _state_examples(concrete_first, states)
        return "Big funding rounds are landing", "big rounds land", ex
    ex, shown_states = _state_examples(concrete_first, states)
    if len(shown_states) >= 2:
        states = shown_states
        who = RL.join_names(states[:3])
        carriers = [e for e in evs if set(e._scope_countries) & set(states)]
        if firms or _majority(carriers, lambda e: e.sector == "private"):
            if _majority(carriers, lambda e: e.mechanism in _MONEY | _BUILD):
                return f"Firms are investing in {x}", "firms invest", ex
            return f"Firms are moving on {x}", "firms move", ex
        return f"Governments are acting on {x}", "governments act", ex
    if firms:
        return f"Private money is moving into {x}", "private money moves in", sorted(evs, key=lambda e: e.sector != "private")
    if _majority(evs, lambda e: e.mechanism in _MONEY) and not money_label:
        return f"Money is flowing into {x}", "money flows in", sorted(evs, key=lambda e: e.mechanism not in _MONEY)
    if _majority(evs, lambda e: e.mechanism in _BUILD):
        return f"Capacity for {x} is being built", "capacity is being built", sorted(evs, key=lambda e: e.mechanism not in _BUILD)
    if _majority(evs, lambda e: e.mechanism in _PARTNER):
        if "partnership" in x or "cooperation" in x or "collaboration" in x:
            return f"{cap(x)} are multiplying" if x.endswith("s") else f"{cap(x)} is widening", "partnerships multiply", concrete_first
        return f"Partnerships on {x} are multiplying", "partnerships multiply", sorted(evs, key=lambda e: e.mechanism not in _PARTNER)
    if len(evs) >= 2 and _majority(evs, lambda e: e.mechanism in _POLICY and e.scope == "eu"):
        return f"EU measures on {x} are multiplying", "EU measures multiply", sorted(evs, key=lambda e: not (e.mechanism in _POLICY and e.scope == "eu"))
    if _majority(evs, lambda e: e.is_analysis):
        return f"Studies see {x} gaining ground", "studies see momentum", sorted(evs, key=lambda e: not e.is_analysis)
    if len(evs) == 1 and evs[0].is_measure:
        return f"A new measure is widening {x}", "a new measure widens it", evs
    return f"{cap(x)} is growing", "it grows", concrete_first


def _right_side(evs: list[Ev], x: str) -> tuple[str, str, list[Ev]]:
    def share(pred) -> bool:
        return _majority(evs, pred)
    term = _shared_constraint(evs)
    if share(lambda e: e.is_analysis):
        ex = sorted(evs, key=lambda e: not e.is_analysis)
        if term:
            return f"Studies keep finding {term} in {x}", f"studies keep finding {term}", ex
        return f"Studies warn of limits to {x}", "studies warn of limits", ex
    if share(lambda e: e.mechanism == "opposes" or re.search(r"protest|opposition|resist", e.statement, re.I)):
        return f"Resistance to {x} is growing", "resistance grows", evs
    if share(lambda e: e.mechanism in _RESTRICT and e.is_measure):
        return f"Restrictions on {x} are in force", "restrictions bite", sorted(evs, key=lambda e: not (e.mechanism in _RESTRICT and e.is_measure))
    if share(lambda e: e.direction == "becomes_conditional"):
        return f"Conditions on {x} are tightening", "conditions tighten", sorted(evs, key=lambda e: e.direction != "becomes_conditional")
    if share(lambda e: e.direction == "becomes_contested"):
        return f"The terms of {x} are disputed", "the terms are disputed", sorted(evs, key=lambda e: e.direction != "becomes_contested")
    if share(lambda e: e.scope in {"external", "third_country"}):
        return f"Outside pressure on {x} is growing", "outside pressure grows", evs
    if term:
        return f"{cap(term)} are showing in {x}" if term.endswith("s") else f"{cap(term)} is showing in {x}", f"{term} show", evs
    return f"Limits to {x} are showing", "limits show", evs


def _character(evs: list[Ev]) -> dict[str, Any]:
    n = max(1, len(evs))
    return {
        "measures": sum(1 for e in evs if e.is_measure),
        "plans": sum(1 for e in evs if e.is_plan),
        "analysis": sum(1 for e in evs if e.is_analysis),
        "n": n,
    }


def _examples(evs: list[Ev], limit: int = 3) -> list[dict[str, str]]:
    out = []
    for e in evs[:limit]:
        out.append({"text": clean(e.title).rstrip(".") or clause_cut(e.statement, 24), "source": e.source, "when": e.when})
    return out


_L_CLASS = {"big rounds land": "money", "firms invest": "money", "private money moves in": "money", "money flows in": "money",
            "capacity is being built": "build", "governments act": "policy", "EU measures multiply": "policy",
            "a new measure widens it": "policy", "firms move": "policy", "partnerships multiply": "partner",
            "studies see momentum": "momentum", "it grows": "grow"}


def _r_class(rp: str) -> str:
    if rp.startswith("studies"):
        return "evidence"
    return {"resistance grows": "resist", "restrictions bite": "rules", "conditions tighten": "rules",
            "the terms are disputed": "dispute", "outside pressure grows": "outside"}.get(rp, "limits")


def _trend_idea(x: str, lp: str, rp: str, term: str, split: bool, r_analysis: bool, weak: list[str] | None = None) -> str:
    """The trend as one idea about the system, not a list of who did what."""
    X = cap(x)
    L, R = _L_CLASS.get(lp, "grow"), _r_class(rp)
    if weak and R in {"evidence", "limits"} and not split and not (L == "partner" and term == "fragmentation"):
        more = {"money": "more money", "build": "more capacity", "policy": "more measures", "partner": "more partnerships"}.get(L)
        if more:
            return f"{X}: {more}, but {_weak_phrase(weak)} {_stay(weak)} weak"
    t = (term or "limits").replace("a gap to rivals", "gap to rivals")
    if split:
        return f"{X}: the evidence points both ways"
    def pick(options: list[str]) -> str:
        return options[sum(map(ord, x)) % len(options)]
    policy_doubt = pick([f"{X}: measures are multiplying faster than evidence that they work",
                         f"{X}: policy is running ahead of proof",
                         f"{X}: the rulebook grows, the doubts stay",
                         f"{X}: governments are acting before the evidence says what works"])
    money_doubt = pick([f"{X}: the money is flowing, the warnings are not fading",
                        f"{X}: more money has not settled the doubts"])
    ideas = {
        ("money", "evidence"): f"{X}: more money, same {t}" if term else money_doubt,
        ("money", "limits"): f"{X}: more money, same {t}" if term else money_doubt,
        ("money", "rules"): f"{X}: money is arriving faster than the rules on how it can be used",
        ("money", "resist"): f"{X}: money is moving faster than local consent",
        ("money", "dispute"): f"{X}: investment is racing ahead of agreement on the terms",
        ("money", "outside"): f"{X}: European money is growing under rising outside pressure",
        ("build", "rules"): f"{X}: capacity is being built before the conditions are settled",
        ("build", "resist"): f"{X}: capacity is being built into growing local resistance",
        ("build", "evidence"): f"{X}: more capacity, same {t}" if term else f"{X}: capacity is growing faster than the case for it",
        ("build", "limits"): f"{X}: more capacity, same {t}" if term else f"{X}: capacity is growing faster than the case for it",
        ("build", "dispute"): f"{X}: capacity is being built while its terms are still disputed",
        ("policy", "evidence"): f"{X}: more measures, same {t}" if term else policy_doubt,
        ("policy", "limits"): f"{X}: measures are multiplying, but the {t} persist" if t.endswith("s") else f"{X}: measures are multiplying, but the {t} persists",
        ("policy", "rules"): f"{X}: support and restrictions are growing at the same time",
        ("policy", "resist"): f"{X}: policy is pushing ahead into growing resistance",
        ("policy", "dispute"): f"{X}: measures are multiplying while their terms are still disputed",
        ("policy", "outside"): f"{X}: Europe is acting under rising outside pressure",
        ("partner", "evidence"): f"{X}: more partnerships, {'more' if t == 'fragmentation' else 'same'} {t}",
        ("partner", "limits"): f"{X}: more partnerships, {'more' if t == 'fragmentation' else 'same'} {t}",
        ("partner", "rules"): f"{X}: partnerships are widening as the conditions for them tighten",
        ("partner", "dispute"): f"{X}: more partners, less agreement on terms",
        ("momentum", "dispute"): f"{X}: studies see momentum, but the terms are disputed",
    }
    if (L, R) in ideas:
        return ideas[(L, R)]
    return f"{X}: {lp}, {'but' if r_analysis else 'while'} {rp}"


_PENDING_WORD = {"proposed": "proposed, not yet adopted", "in_negotiation": "still in negotiation",
                 "intention": "announced, not yet decided", "call_open": "call open now"}


def write_trend(object_key: str, left_refs: list[dict], right_refs: list[dict], node_by_claim: dict,
                *, left_pull: float, right_pull: float) -> dict[str, Any]:
    x = label(object_key)
    left = evidence(left_refs, node_by_claim)
    right = evidence(right_refs, node_by_claim)
    lc, rc = _character(left), _character(right)
    lt, lp, left = _left_side(left, x)
    rt, rp, right = _right_side(right, x)
    # "Studies disagree" only when the examples shown on both sides are studies.
    l_analysis = lp == "studies see momentum" and all(e.is_analysis for e in left[:2])
    r_analysis = rc["analysis"] >= max(1, (rc["n"] + 1) // 2) and all(e.is_analysis for e in right[:2])
    if l_analysis and r_analysis:
        lt = f"Some see {x} gaining ground"
        rt = f"Others keep finding {_shared_constraint(right)}" if _shared_constraint(right) else "Others see limits"
    weak, _shared = weak_spots(right, x)
    if weak and rp.startswith("studies"):
        rt = f"Studies keep finding {_weak_phrase(weak)} too weak"
    pair_title = _trend_idea(x, lp, rp, _shared_constraint(right), l_analysis and r_analysis, r_analysis, weak)

    def plain(evs: list[Ev], side: str, phrase: str) -> str:
        # What the side adds up to, not a chain of who-did-what.  Only the kinds of
        # action that fit the side's own title are listed.
        if not evs:
            return ""
        span, where, acts = _span(evs), _places(evs), _acts(evs)
        fit = {"money": {"new money", "new capacity"}, "partner": {"new partnerships"},
               "tighten": {"new rules", "local opposition"}, "restrict": {"new rules"}}
        key = next((k for k, words in (("money", ("invest", "rounds", "money", "capacity")), ("partner", ("partnership",)),
                                       ("tighten", ("tighten", "resistance")), ("restrict", ("restriction",)))
                    if any(w in phrase for w in words)), "")
        if key:
            acts = [a for a in acts if a in fit[key]]
        if acts and not all(e.is_analysis for e in evs[:2]):
            return sentence(f"{cap(_count(len(evs), 'finding', 'findings'))}{' ' + span if span else ''}: "
                            f"{RL.join_names(acts)}{', ' + where if where else ''}")
        who, plural = _mix(evs)
        if side == "left":
            return sentence(f"{cap(who)} {'see' if plural else 'sees'} momentum{' ' + span if span else ''}")
        term = _shared_constraint(evs)
        verb = ("find" if plural else "finds") + (f" {term}" if term else " limits")
        return sentence(f"{cap(who)} {verb}{' ' + span if span else ''}")

    # Composition: what kind of evidence carries each side.
    def weight(ch: dict[str, Any]) -> str:
        if ch["measures"] >= max(2, ch["n"] / 3) or ch["measures"] >= max(1, ch["n"] / 2):
            return "measures already under way"
        if ch["plans"] >= max(1, ch["n"] / 2):
            return "plans and announcements"
        if ch["analysis"] >= max(1, ch["n"] / 2):
            return "analysis"
        return "a mix of measures and analysis"

    lw, rw = weight(lc), weight(rc)
    if lw == rw == "measures already under way":
        composition = "Both sides are backed by measures already under way: a real tug of war, not just a debate."
    elif lw == rw:
        composition = f"Both sides rest mainly on {lw}; the first binding decision will tell which way this goes."
    else:
        composition = f"The pull toward expansion rests mainly on {lw}; the pull against rests mainly on {rw}."
        if rw == "analysis" and lw == "measures already under way":
            composition += " The warnings could still turn into rules."
        elif lw == "analysis" and rw == "measures already under way":
            composition += " The momentum is still mostly on paper."

    pend_l = [e for e in left if e.status in _PENDING_WORD]
    pend_r = [e for e in right if e.status in _PENDING_WORD]
    if pend_l or pend_r:
        def what(evs: list[Ev]) -> str:
            n = len(evs)
            return "a pending decision" if n == 1 else f"{_number_word(n)} pending decisions"
        if pend_l and pend_r:
            flip = f"What could tip it: {what(pend_l)} would add to the push and {what(pend_r)} to the limits."
        elif pend_l:
            flip = f"What could tip it: {what(pend_l)} would add to the push; nothing pending on the other side."
        else:
            flip = f"What could tip it: {what(pend_r)} would add to the limits; nothing pending on the other side."
    else:
        flip = "No decision is pending in the evidence; watch for the next binding measure on either side."
    lead_side = "expanding" if left_pull > right_pull + 4 else "constraining" if right_pull > left_pull + 4 else ""
    return {
        "pair_title": pair_title,
        "left_title": lt,
        "right_title": rt,
        "left_plain": plain(left, "left", lp),
        "right_plain": plain(right, "right", rp),
        "left_examples": _examples(left),
        "right_examples": _examples(right),
        "composition": composition,
        "flip_line": flip,
        "kind_label": KIND_LABELS["trend"],
        "leading_side": lead_side,
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# The point: what the evidence adds up to, in the engine's own words
# ---------------------------------------------------------------------------
# A card opens with its point, not with a chain of "X did this, Y did that".
# The point is synthesised from the structured evidence (how many sources, what
# kind, where, since when, what kind of action); the individual records are
# listed under the card as sources.

_FULL_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
                "September", "October", "November", "December")
_ACT_NOUNS: tuple[tuple[frozenset, str], ...] = (
    (frozenset({"funds", "invests", "allocates"}), "new money"),
    (frozenset({"builds", "adds_capacity", "supplies"}), "new capacity"),
    (frozenset({"procures"}), "joint purchasing"),
    (frozenset({"regulates", "requires", "restricts", "conditions", "screens", "licenses", "standardises", "harmonises", "governs"}), "new rules"),
    (frozenset({"collaborates", "associates", "coordinates"}), "new partnerships"),
    (frozenset({"recruits", "retains"}), "recruitment"),
    (frozenset({"launches", "supports", "adopts", "prioritises", "proposes"}), "new programmes"),
    (frozenset({"opposes"}), "local opposition"),
)


def _count(n: int, one: str, many: str) -> str:
    return f"one {one}" if n == 1 else f"{_number_word(n)} {many}"


def _ymd(v: Any) -> tuple[int, int] | None:
    m = re.match(r"^(\d{4})-(\d{2})", clean(v))
    return (int(m.group(1)), int(m.group(2))) if m else None


def _span(evs: list[Ev]) -> str:
    ds = sorted(d for d in (_ymd(e.date) for e in evs) if d)
    if not ds:
        return ""
    (ya, ma), (yb, mb) = ds[0], ds[-1]
    if (ya, ma) == (yb, mb):
        return f"in {_FULL_MONTHS[ma - 1]} {ya}"
    if ya == yb:
        return f"since {_FULL_MONTHS[ma - 1]}"
    return f"since {ya}"


def _acts(evs: list[Ev]) -> list[str]:
    out: list[str] = []
    for e in evs:
        if e.is_analysis:
            continue
        for mechs, noun in _ACT_NOUNS:
            if e.mechanism in mechs:
                if noun not in out:
                    out.append(noun)
                break
    return out


def _mix(evs: list[Ev]) -> tuple[str, bool]:
    """('three studies and two national governments', plural?)"""
    gov = {e.actor or e.source for e in evs if e.actor_class in {"member_state", "national_funder"}}
    eu = any(e.actor_class == "eu_body" for e in evs)
    firms = {e.actor or e.source for e in evs if e.actor_class == "company"}
    studies = {e.source for e in evs if e.is_analysis and e.actor_class not in {"member_state", "national_funder", "eu_body", "company"}}
    parts = []
    if studies:
        parts.append(_count(len(studies), "study", "studies"))
    if gov:
        parts.append(_count(len(gov), "national government", "national governments"))
    if eu:
        parts.append("the EU")
    if firms:
        parts.append(_count(len(firms), "company", "companies"))
    if not parts:
        n = distinct_sources(evs)
        parts.append(_count(n, "source", "sources"))
    plural = len(parts) > 1 or not (parts[0].startswith("one ") or parts[0] == "the EU")
    return RL.join_names(parts), plural


def _places(evs: list[Ev]) -> str:
    states: list[str] = []
    for e in evs:
        for c in e.member_states:
            if c not in states:
                states.append(c)
    eu = any(e.scope == "eu" for e in evs)
    where = f"in {_count(len(states), 'member state', 'member states')}" if states else ""
    if eu and where:
        return f"at EU level and {where}"
    return where


def _join_clauses(*bits: str) -> str:
    return ", ".join(b for b in bits if b)


def point_for(grammar: str, product: str, raw: dict[str, Any], cand: dict[str, Any], evs: list[Ev],
              node_by_claim: dict, vocab: dict | None) -> str:
    """One or two plain sentences stating what the evidence adds up to ('' = none)."""
    g = clean(grammar)
    obj = clean(raw.get("object") or cand.get("object"))
    x = label(obj)
    roles = by_role(evs)
    n_src = distinct_sources(evs)
    eps = [clean(v) for v in (raw.get("endpoint_objects") or []) if clean(v)]
    if g == "corroborated_claim":
        if n_src < 2:
            return ""  # a single signal: the headline and the stake say it
        if product == "risk":
            direction = clean(raw.get("direction") or cand.get("direction"))
            term = _shared_constraint(evs) or {"becomes_conditional": "tightening conditions", "becomes_contested": "open disagreement",
                                              "contracts": "cutbacks"}.get(direction, "")
            who, plural = _mix(evs)
            what = f"the same {term} in {x}" if term else f"trouble in {x}"
            return sentence(f"{cap(who)} {'report' if plural else 'reports'} {what}" + "".join(
                f" {b}" for b in (_places(evs), _span(evs)) if b))
        acts = _acts(evs)
        records = len({e.identity for e in evs if e.identity}) or len(evs)
        if acts:
            return sentence(f"{cap(_count(records, 'separate move', 'separate moves'))}{' ' + _span(evs) if _span(evs) else ''}: "
                            f"{RL.join_names(acts)}{', ' + _places(evs) if _places(evs) else ''}")
        who, plural = _mix(evs)
        return sentence(f"{cap(who)} {'see' if plural else 'sees'} momentum in {x}{' ' + _span(evs) if _span(evs) else ''}")
    if g == "named_continuity":
        then = evidence(cand.get("continuity_history") or [], node_by_claim)
        yrs = sorted(y for y in (year_of(e.date) for e in then) if y)
        now = _count(len(evs), "current finding", "current findings")
        if yrs:
            return sentence(f"In the record since {yrs[0]}; {now} {_span(evs)} show it is still open".replace("  ", " "))
        return sentence(f"{cap(now)} {_span(evs)} keep it open".replace("  ", " "))
    if g == "split_recurrence":
        a, b = (label(eps[0]), label(eps[1])) if len(eps) >= 2 else (x, "a second issue")
        allv = evidence((cand.get("support") or []) + (cand.get("context") or []), node_by_claim)
        r = by_role(allv)
        hist = (r.get("historical_relation") or [None])[0]
        na, nb = len(r.get("side_a") or []), len(r.get("side_b") or [])
        yr = year_of(hist.date) if hist else ""
        return sentence(f"{'The link was made in ' + yr + '. ' if yr else ''}Now both sides are moving again: "
                        f"{_count(na or 1, 'finding', 'findings')} on {a}, {_count(nb or 1, 'finding', 'findings')} on {b}")
    if g == "era_conjunction":
        return sentence(f"{cap(_count(len(evs), 'current finding', 'current findings'))} from "
                        f"{_count(n_src, 'source', 'sources')} tie them together {_span(evs)}".replace("  ", " "))
    if g in {"practice_before_doctrine", "deployment_before_rules", "clock_before_rule"}:
        first = (roles.get("practice") or roles.get("deployment") or roles.get("commitment") or evs[:1] or [None])[0]
        later = (roles.get("doctrine") or roles.get("first_rule") or roles.get("rule") or evs[1:2] or [None])[0]
        if not first or not later:
            return ""
        gap = gap_phrase(first.date, later.date).lower()
        pending = {"proposed": ", and it is still only a proposal", "in_negotiation": ", and it is still being negotiated",
                   "intention": ", and it is still only an intention"}.get(later.status, "")
        if g == "clock_before_rule":
            return sentence(f"The deadline was set in {first.when}; the rules it depends on came {gap}{pending}")
        doing = "already happening" if g == "practice_before_doctrine" else "already operating"
        return sentence(f"{cap(x)} {'were' if is_plural(x) else 'was'} {doing} in {first.when}; the first rule covering it came {gap}{pending}")
    if g == "success_metric_gap":
        objective = label(raw.get("objective_object") or obj)
        acts = _acts(evs) or ["new money"]
        return sentence(f"The evidence shows {RL.join_names(acts)} {_span(evs)}, but nothing yet measures whether {objective} improves".replace("  ", " "))
    if g == "goal_without_measure":
        inv = int(raw.get("invocations", 0) or 0)
        meas = int(raw.get("measurements", 0) or 0)
        return sentence(f"The current evidence invokes {x} {inv} times and measures an outcome {meas} times")
    if g == "stalled_proposal":
        return sentence(f"Proposed {_span(evs[:1]) or 'earlier'}; nothing in the evidence shows a decision since")
    if g == "conflicting_criteria":
        a = label(eps[0]) if eps else "one requirement"
        b = label(eps[1]) if len(eps) > 1 else "another"
        return sentence(f"One requirement comes from {a}, the other from {b}, and nothing in the evidence says which one wins")
    if g == "dependency_pathway":
        c_label = label(raw.get("capability_object") or (eps[0] if eps else ""))
        d_label = label(raw.get("dependency_object") or (eps[1] if len(eps) > 1 else ""))
        strain = [e for e in evs if e.role in {"coupling", "exposure", "propagation"}]
        if strain:
            return sentence(f"{cap(c_label)} {'rest' if is_plural(c_label) else 'rests'} on {d_label}, and "
                            f"{_count(len(strain), 'finding', 'findings')} {_span(strain)} show {d_label} under strain".replace("  ", " "))
        return sentence(f"{cap(c_label)} {'rest' if is_plural(c_label) else 'rests'} on {d_label}")
    if g == "latent_channel":
        need = label(eps[0] if eps else raw.get("objective_object"))
        tool = label(eps[1] if len(eps) > 1 else raw.get("delivery_object"))
        return sentence(f"{cap(need)} {'have' if is_plural(need) else 'has'} a documented gap, and {tool} "
                        f"{'are' if is_plural(tool) else 'is'} already running; no source connects the two yet")
    if g == "anchor_demand":
        return ""
    if g == "future_shock_hypothesis":
        driver = (roles.get("external_driver") or [None])[0]
        pid = clean(raw.get("pressure_id") or cand.get("pressure_id")) or next((v.split(".", 1)[1] for v in eps if v.startswith("shock_pressure.")), "")
        asset_obj = clean(raw.get("capability_object") or cand.get("capability_object")) or next((v for v in eps if not v.startswith("shock_pressure.")), "")
        mech = exposure_mechanism(pid, cluster_of(asset_obj, vocab))
        return sentence(mech) if mech else ""
    if g == "magnitude_contrast":
        return ""
    if g == "external_opening":
        gains = roles.get("european_gain") or []
        who = clean(raw.get("external_actor"))
        verbs = {"recruitment": "stepping up recruitment", "new money": "putting in new money", "new partnerships": "opening new partnerships",
                 "new programmes": "launching new programmes", "new capacity": "building capacity", "new rules": "adjusting its rules",
                 "joint purchasing": "buying jointly", "local opposition": "meeting local opposition"}
        acts = [verbs.get(a, a) for a in _acts(gains)] or ["making new offers"]
        return sentence(f"While {who + ' rules' if who else 'rules abroad'} tighten, Europe is {RL.join_names(acts[:2])} ({_span(gains).replace('in ', '').replace('since ', 'since ')})".replace(" ()", ""))
    if g == "cross_pressure":
        push = roles.get("push") or []
        pull = roles.get("pull") or []
        pa = (_acts(push) or ["support"])[0]
        pb = (_acts(pull) or ["new rules"])[0]
        return sentence(f"Both are live: {pa} {_span(push)}, {pb} {_span(pull)}".replace("  ", " "))
    if g == "common_driver":
        fields = [clean(v) for v in (raw.get("field_labels") or []) if clean(v)]
        return sentence(f"The same dependence shows up in {_count(len(fields) or len(evs), 'field', 'fields')} and "
                        f"{_count(n_src, 'source', 'sources')} {_span(evs)}".replace("  ", " "))
    if g == "national_convergence":
        countries = [clean(c) for c in (raw.get("countries") or []) if clean(c)]
        eu = clean(raw.get("eu_state"))
        return sentence(f"{cap(_count(len(countries), 'member state', 'member states'))} took the same step {_span(evs)}"
                        f"{', without a common EU rule' if eu != 'adopted' else ''}".replace("  ", " "))
    return ""


def _source_list(evs: list[Ev], limit: int = 4) -> list[dict[str, str]]:
    out, seen = [], set()
    for e in evs:
        t = clean(e.title) or headline_from_statement(e.statement)
        if not t or t.lower() in seen:
            continue
        seen.add(t.lower())
        out.append({"title": t.rstrip("."), "source": e.source, "when": e.when})
        if len(out) >= limit:
            break
    return out


def write_card(grammar: str, product: str, raw: dict[str, Any], cand: dict[str, Any],
               node_by_claim: dict[str, dict[str, Any]], vocab: dict[str, Any] | None = None) -> dict[str, str]:
    c = _write_card(grammar, product, raw, cand, node_by_claim, vocab)
    if c.get("kind") == "error":
        return c
    try:
        g = clean(grammar)
        evs = evidence(cand.get("support") or [], node_by_claim)
        point = point_for(grammar, product, raw, cand, evs, node_by_claim, vocab)
        so, basis = clean(c.get("so_what")), clean(c.get("basis"))
        note = _evidence_note(evs)
        if g == "future_shock_hypothesis":
            c["lead"] = point                      # how it would bite; the consequence stays as so_what
            c["basis"] = " ".join(b for b in (note, basis) if b)
        elif g in _REASONED:
            c["lead"] = " ".join(b for b in (point, so) if b)
            c["so_what"] = ""
            c["basis"] = " ".join(b for b in (note, basis) if b)
        else:
            c["lead"] = so or point
            if g == "corroborated_claim" and distinct_sources(evs) < 2 and " could " in clean(c.get("headline")) and evs:
                # A modal one-source headline needs its content: the finding itself.
                gist = sentence(clause_cut(strip_reporting(evs[0].statement), 24))
                c["lead"] = " ".join(b for b in (gist, so) if b)
            c["so_what"] = ""
            c["basis"] = " ".join(b for b in ((point if so else note), basis) if b)
        c["evidence"] = _source_list(evs)
    except Exception:  # pragma: no cover - fail-safe
        pass
    return c


_REASONED = {"practice_before_doctrine", "deployment_before_rules", "clock_before_rule", "success_metric_gap", "goal_without_measure",
             "stalled_proposal", "conflicting_criteria", "dependency_pathway", "latent_channel", "split_recurrence"}


def _evidence_note(evs: list[Ev]) -> str:
    if not evs:
        return ""
    who, _ = _mix(evs)
    span = _span(evs)
    return f"Evidence: {who}{', ' + span if span else ''}."


def _write_card(grammar: str, product: str, raw: dict[str, Any], cand: dict[str, Any],
                node_by_claim: dict[str, dict[str, Any]], vocab: dict[str, Any] | None = None) -> dict[str, str]:
    g = clean(grammar)
    try:
        if g == "corroborated_claim":
            return write_corroborated(product, raw, cand, node_by_claim, vocab)
        if g == "named_continuity":
            return write_named_continuity(raw, cand, node_by_claim, vocab)
        if g == "split_recurrence":
            return write_split_recurrence(raw, cand, node_by_claim, vocab)
        if g == "era_conjunction":
            return write_era_conjunction(raw, cand, node_by_claim, vocab)
        if g in {"practice_before_doctrine", "deployment_before_rules", "clock_before_rule"}:
            return write_sequence(g, raw, cand, node_by_claim, vocab)
        if g == "success_metric_gap":
            return write_success_gap(raw, cand, node_by_claim, vocab)
        if g == "goal_without_measure":
            return write_goal_without_measure(raw, cand, node_by_claim, vocab)
        if g == "stalled_proposal":
            return write_stalled(raw, cand, node_by_claim, vocab)
        if g == "conflicting_criteria":
            return write_conflicting(raw, cand, node_by_claim, vocab)
        if g == "dependency_pathway":
            return write_dependency(product, raw, cand, node_by_claim, vocab)
        if g == "latent_channel":
            return write_latent(raw, cand, node_by_claim, vocab)
        if g == "anchor_demand":
            return write_anchor_demand(raw, cand, node_by_claim, vocab)
        if g == "future_shock_hypothesis":
            return write_shock(raw, cand, node_by_claim, vocab)
        if g == "magnitude_contrast":
            return write_magnitude(raw, cand, node_by_claim, vocab)
        if g == "external_opening":
            return write_external_opening(raw, cand, node_by_claim, vocab)
        if g == "cross_pressure":
            return write_cross_pressure(raw, cand, node_by_claim, vocab)
        if g == "common_driver":
            return write_common_driver(raw, cand, node_by_claim, vocab)
        if g == "national_convergence":
            return write_national_convergence(raw, cand, node_by_claim, vocab)
    except Exception as exc:  # pragma: no cover - fail-safe: never break a scan on copy
        return card("error", label(raw.get("object") or cand.get("object")), "", "", f"card writer fallback: {type(exc).__name__}")
    x = label(raw.get("object") or cand.get("object"))
    evs = evidence(cand.get("support") or [], node_by_claim)
    return card(g or "finding", cap(x), lead_from(evs, 2), stake_line(clean(raw.get("object") or cand.get("object")), vocab, x))
