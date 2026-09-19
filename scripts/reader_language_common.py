#!/usr/bin/env python3
"""Shared collection and linting for the optional Reader Language layer.

The collector is intentionally conservative.  It only looks at reader-facing analytical
pages and selected reader-facing inference fields.  It never edits or queues Main Radar
records, Earlier Findings records, source records, Stuff/Excel, scores, dates, links or
Deep Scan decisions.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parents[1]

HTML_ROUTES = {
    "index.html": "start",
    "read/index.html": "read",
    "frontier/index.html": "frontier",
    "frontier/quick/index.html": "frontier-quick",
    "trends/index.html": "trends",
    "phenomena/index.html": "phenomena",
    "priorities/index.html": "priorities",
    "shocks/index.html": "shocks",
    "shocks/variants.html": "shocks-variants",
    "2035/index.html": "future",
    "briefing/index.html": "briefing",
    "glossary/index.html": "glossary",
    "explore/index.html": "explore",
    "literature/index.html": "literature",
}

# Only scripts whose prose is still rendered on the live site.  The legacy fallback
# readers (trends.js pairs, phenomena.js, continuity.js, priorities.js lenses and
# shocks/scenarios.js) are not shown after the Stage-7 claim-native cutover; queueing
# their text would spend review effort on wording no visitor sees.
JS_ROUTES = {
    "briefing/insights.js": ["briefing", "read", "priorities"],
    "reader_style.js": ["briefing", "read", "frontier", "frontier-quick", "trends", "phenomena", "priorities", "shocks"],
}

META_PATTERNS = [

    (re.compile(r"\bthe Radar[’']s (?:hypothesis|synthesis|inference)\b", re.I), "internal Radar language"),
    (re.compile(r"\b(?:push|pushback) (?:gains|wins|is more concrete)\b", re.I), "analyst shorthand"),
    (re.compile(r"\bconcrete (?:action|move)s?\b", re.I), "analyst shorthand"),
    (re.compile(r"\badmissibility-relevant\b", re.I), "bureaucratic jargon"),
    (re.compile(r"\bselective conditionality\b", re.I), "policy jargon"),
    (re.compile(r"\bif it goes ahead, the push\b", re.I), "repetitive template"),
    (re.compile(r"\bqualifying (?:current )?(?:primary )?records?\b", re.I), "analysis machinery"),
    (re.compile(r"\brepeated[- ]source (?:evidence|actions?)\b", re.I), "analysis machinery"),
    (re.compile(r"\bcounter[- ]force\b", re.I), "analysis machinery"),
    (re.compile(r"\bevidence pull\b", re.I), "analysis machinery"),
    (re.compile(r"\bhow this was inferred\b", re.I), "analysis machinery"),
    (re.compile(r"\binference engine\b", re.I), "analysis machinery"),
    (re.compile(r"\breasoning roles?\b", re.I), "analysis machinery"),
    (re.compile(r"\bdenial(?:/| and )falsifier\b", re.I), "analysis machinery"),
    (re.compile(r"\bcross[- ]evidence inference\b", re.I), "analysis machinery"),
    (re.compile(r"\bretained evidence\b", re.I), "analysis machinery"),
    (re.compile(r"\bcurrent Radar records? (?:drive|support)\b", re.I), "analysis machinery"),
    (re.compile(r"\bDeep[- ]Scan[- ]kept\b", re.I), "analysis machinery"),
    (re.compile(r"\baudit[- ]only\b", re.I), "analysis machinery"),
    (re.compile(r"\bsupported strongly enough\b", re.I), "analysis machinery"),
    (re.compile(r"\bthe (?:candidate|corpus)\b", re.I), "analysis machinery"),
    (re.compile(r"\bprimary records? from \d+ sources?\b", re.I), "analysis machinery"),
]

AWKWARD_PATTERNS = [
    (re.compile(r"\bis widening around\b", re.I), "awkward phrase"),
    (re.compile(r"\bforward[- ]looking pathways? to (?:loss|gain)\b", re.I), "bureaucratic phrase"),
    (re.compile(r"\bstrategic dependencies research security\b", re.I), "noun pile-up"),
    (re.compile(r"\bpartnership, association or cross[- ]border cooperation\b", re.I), "stacked abstractions"),
]

ABSTRACT_WORDS = {
    "architecture", "association", "capability", "capacity", "collaboration", "cooperation",
    "coordination", "dependence", "dependencies", "dependency", "framework", "governance",
    "implementation", "infrastructure", "integration", "interoperability", "mechanism", "pathway",
    "partnership", "resilience", "security", "sovereignty", "strategy", "strategic", "institutional",
    "operational", "configuration", "alignment", "accessibility", "fragmentation", "competitiveness",
}


READER_STYLE_ROUTES = {"briefing", "read", "trends", "priorities", "frontier", "frontier-quick"}


def _surface_approx(text: str) -> str:
    """Mirror the stable, presentation-only substitutions used by reader_style.js.

    This is not an analytical rewrite.  It only gives the browser overlay extra exact-match
    variants for text that the existing reader-style layer expands before display.
    """
    s = clean(text)
    s = re.sub(r"^de[- ]risking\s+(.+)$", r"Reducing risks around \1", s, flags=re.I)
    s = re.sub(r"^Partnership, association or cross-border cooperation is widening around (.+)\.$", r"Cross-border cooperation on \1 is increasing.", s, flags=re.I)
    s = re.sub(r"^Security, export-control or de[- ]risking conditions are tightening around (.+)\.$", r"Security and export-control conditions around \1 are getting tighter.", s, flags=re.I)
    reps = [
        (r"\bHPC\b", "high-performance computing"),
        (r"\bEuroHPC\b", "the European shared computing programme"),
        (r"\bFP10\b", "the next EU research framework programme"),
        (r"\bMFF\b", "the EU long-term budget"),
        (r"\bMSCA\b", "Marie Skłodowska-Curie Actions"),
        (r"\bFDI\b", "foreign direct investment"),
        (r"\bTRLs?\b", "technology readiness levels"),
        (r"\bLLMs?\b", "large language models"),
        (r"\bGPUs?\b", "graphics processors"),
        (r"\bSMEs?\b", "small and medium-sized firms"),
        (r"\bR&D\b", "research and development"),
        (r"\bAI\b", "artificial intelligence"),
        (r"\bR&I\b", "research and innovation"),
        (r"\bdual[- ]use\b", "civilian and defence"),
        (r"\bcompute access\b", "access to computing power"),
        (r"\bcompute capacity\b", "computing capacity"),
        (r"\bcompute infrastructure\b", "computing infrastructure"),
        (r"\bchokepoints?\b", "critical bottlenecks"),
        (r"\binteroperability\b", "ability of systems to work together"),
        (r"\bpilot lines?\b", "test production lines"),
        (r"\btestbeds?\b", "test facilities"),
        (r"\bdeep[- ]tech\b", "advanced technology"),
        (r"\bde[- ]risking\b", "risk-reduction"),
        (r"\btechnology sovereignty\b", "control over critical technology"),
        (r"\bfrontier research\b", "cutting-edge research"),
        (r"\bscale[- ]ups?\b", "growing technology firms"),
        (r"\bexport controls?\b", "rules limiting technology exports"),
    ]
    for pat, repl in reps:
        s = re.sub(pat, repl, s, flags=re.I if pat not in {r"\bAI\b", r"\bR&I\b"} else 0)
    return clean(s)


def _limit_approx(text: str, n: int) -> str:
    words = clean(text).split()
    if len(words) <= n:
        return clean(text)
    out = words[:n]
    while len(out) > 5 and re.fullmatch(r"(?:and|or|but|because|while|which|that|to|for|of|with|in|on|at|from|across|through|by|as|the|a|an)", out[-1], flags=re.I):
        out.pop()
    s = " ".join(out).rstrip(" ,:;—–-")
    if s and s[-1] not in ".!?)]":
        s += "."
    return s


def display_variants(text: str, routes: Iterable[str]) -> list[str]:
    vals = [clean(text)]
    if any(r in READER_STYLE_ROUTES for r in routes):
        surfaced = _surface_approx(text)
        vals.extend([surfaced, _limit_approx(surfaced, 20), _limit_approx(surfaced, 24)])
    return list(dict.fromkeys(v for v in vals if v))

CODEISH = re.compile(r"(?:=>|===|!==|\$\{|</?[A-Za-z]|https?://|\bfunction\b|\bconst\b|\blet\b|\breturn\b|\bRegExp\b)")


def clean(v: object) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def item_id(text: str) -> str:
    return "rl_" + fingerprint(text)[:16]


@dataclass
class Candidate:
    source: str
    routes: set[str] = field(default_factory=set)
    origins: set[str] = field(default_factory=set)

    def as_dict(self) -> dict:
        routes = sorted(self.routes)
        display_text = _surface_approx(self.source) if routes and all(r in READER_STYLE_ROUTES for r in routes) else self.source
        return {
            "id": item_id(self.source),
            "source": self.source,
            "display_text": display_text,
            "source_sha256": fingerprint(self.source),
            "routes": routes,
            "origins": sorted(self.origins),
            "match_variants": display_variants(self.source, routes),
        }


def add_candidate(store: dict[str, Candidate], text: object, routes: Iterable[str], origin: str) -> None:
    s = clean(text)
    if not s or len(s) < 5:
        return
    # Source/article titles and short interface labels are not useful language-review targets.
    if CODEISH.search(s):
        return
    key = fingerprint(s)
    c = store.get(key)
    if c is None:
        c = store[key] = Candidate(source=s)
    c.routes.update(r for r in routes if r)
    c.origins.add(origin)


def collect_html(store: dict[str, Candidate]) -> None:
    for rel, route in HTML_ROUTES.items():
        p = ROOT / rel
        if not p.exists():
            continue
        soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
        for tag in soup(["script", "style", "noscript", "template"]):
            tag.decompose()
        for node in soup.find_all(string=True):
            if isinstance(node, Comment):
                continue
            text = clean(node)
            if text:
                add_candidate(store, text, [route], rel)


# Conservative reader-field finder for hand-authored JavaScript objects.  We do not try to
# parse every JavaScript string: doing so would accidentally queue regexes and implementation
# code.  These named fields are the ones used as prose on the reader-facing analytical pages.
JS_FIELD_RE = re.compile(
    r"\b(?:title|plain|why|plainly|secondOrder|hidden|summary|what|explanation)\s*:\s*(?P<q>['\"])(?P<text>(?:\\.|(?!(?P=q)).)*?)(?P=q)"
)
JS_RETURN_RE = re.compile(r"\breturn\s+(?P<q>['\"])(?P<text>(?:\\.|(?!(?P=q)).){18,}?)(?P=q)\s*;")


def _decode_js_string(raw: str) -> str:
    raw = raw.replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
    raw = raw.replace("\\'", "'").replace('\\"', '"')
    raw = raw.replace("\\u2019", "\u2019").replace("\\u2013", "\u2013").replace("\\u2014", "\u2014")
    raw = raw.replace("\\\\", "\\")
    return clean(raw)


def collect_js(store: dict[str, Candidate]) -> None:
    for rel, routes in JS_ROUTES.items():
        p = ROOT / rel
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8")
        for rx in (JS_FIELD_RE, JS_RETURN_RE):
            for m in rx.finditer(src):
                text = _decode_js_string(m.group("text"))
                if "${" in text or len(text.split()) < 4 or CODEISH.search(text):
                    continue
                line = src.count("\n", 0, m.start()) + 1
                add_candidate(store, text, routes, f"{rel}:{line}")


def _reader_reasoning_document() -> tuple[Path | None, dict | None]:
    """Return the same reasoning snapshot the public reader prefers.

    The live site loads radar_active.json first when it is a generated active-corpus
    snapshot, and falls back to radar.json otherwise. Reader Language must inspect
    that same text or a review package can target wording that is not actually live.
    """
    active = ROOT / "radar_active.json"
    if active.exists():
        try:
            data = json.loads(active.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("active_corpus_snapshot"):
                return active, data
        except Exception:
            pass

    raw = ROOT / "radar.json"
    if raw.exists():
        try:
            data = json.loads(raw.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return raw, data
        except Exception:
            pass
    return None, None


def collect_radar_reader_fields(store: dict[str, Candidate]) -> None:
    p, data = _reader_reasoning_document()
    if p is None or not isinstance(data, dict):
        return
    hi = data.get("high_order_inference") if isinstance(data, dict) else None
    hi = hi if isinstance(hi, dict) else {}
    candidates = {clean(x.get("id")): x for x in hi.get("candidates", []) if isinstance(x, dict) and clean(x.get("id"))}
    publications = hi.get("publications") if isinstance(hi.get("publications"), dict) else {}
    route_for = {
        "trend": "trends",
        "continuity": "phenomena",
        "risk": "priorities",
        "opportunity": "priorities",
        "shock": "shocks",
    }
    for product, route in route_for.items():
        for cid in publications.get(product, []) if isinstance(publications.get(product), list) else []:
            c = candidates.get(clean(cid))
            if not c:
                continue
            origin = f"{p.name}:high_order:{clean(cid)}"
            for key in ("reader_title", "reader_summary", "reader_why"):
                add_candidate(store, c.get(key), [route], f"{origin}:{key}")
            if product == "trend" and isinstance(c.get("trend_balance"), dict):
                b = c["trend_balance"]
                for key in ("left_title", "right_title", "left_plain", "right_plain", "composition", "flip_line"):
                    add_candidate(store, b.get(key), [route], f"{origin}:trend_balance.{key}")
            if product == "shock":
                add_candidate(store, c.get("why_easy_to_miss"), [route], f"{origin}:why_easy_to_miss")
                # The shock card explanation shown to readers.
                add_candidate(store, c.get("reader_consequence"), [route], f"{origin}:reader_consequence")

    sc = hi.get("scenarios_2035") if isinstance(hi.get("scenarios_2035"), dict) else {}
    for w in sc.get("scenarios", []) if isinstance(sc.get("scenarios"), list) else []:
        if not isinstance(w, dict):
            continue
        origin = f"{p.name}:scenarios_2035:{clean(w.get('id'))}"
        for key in ("name", "tagline", "watch"):
            add_candidate(store, w.get(key), ["future"], f"{origin}:{key}")
        for j, b in enumerate(w.get("bullets") or []):
            if isinstance(b, dict):
                add_candidate(store, b.get("text"), ["future"], f"{origin}:bullets[{j}]")
        for v in w.get("variants") or []:
            if not isinstance(v, dict):
                continue
            vo = f"{origin}:variant:{clean(v.get('id'))}"
            add_candidate(store, v.get("name"), ["future"], f"{vo}:name")
            for j, b in enumerate(v.get("bullets") or []):
                if isinstance(b, dict):
                    add_candidate(store, b.get("text"), ["future"], f"{vo}:bullets[{j}]")

    shock = data.get("shock_inference") if isinstance(data, dict) else None
    shock = shock if isinstance(shock, dict) else {}
    for i, s in enumerate(shock.get("dynamic_shocks", []) if isinstance(shock.get("dynamic_shocks"), list) else []):
        if not isinstance(s, dict):
            continue
        origin = f"{p.name}:shock_inference.dynamic_shocks[{i}]"
        for key in ("title", "plainly", "second_order", "why_easy_to_miss", "net_assessment"):
            add_candidate(store, s.get(key), ["shocks"], f"{origin}:{key}")
        for key in ("conditions", "case_against", "prevention_actions", "watch_for"):
            vals = s.get(key)
            if isinstance(vals, list):
                for j, v in enumerate(vals):
                    add_candidate(store, v, ["shocks"], f"{origin}:{key}[{j}]")


def collect_candidates() -> list[dict]:
    store: dict[str, Candidate] = {}
    collect_html(store)
    collect_js(store)
    collect_radar_reader_fields(store)
    return sorted((c.as_dict() for c in store.values()), key=lambda x: (x["routes"], x["source"].lower()))


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE))


def _syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = max(1, len(groups))
    if w.endswith("e") and n > 1 and not w.endswith(("le", "ye")):
        n -= 1
    return max(1, n)


def flesch(text: str) -> float:
    words = re.findall(r"\b[A-Za-z]+\b", text)
    if not words:
        return 100.0
    sentences = max(1, len(re.findall(r"[.!?]+(?:\s|$)", text)))
    syllables = sum(_syllables(w) for w in words)
    return 206.835 - 1.015 * (len(words) / sentences) - 84.6 * (syllables / len(words))


def lint_reasons(text: str) -> list[str]:
    s = clean(text)
    wc = word_count(s)
    reasons: list[str] = []
    for rx, label in META_PATTERNS + AWKWARD_PATTERNS:
        if rx.search(s):
            reasons.append(label)
    if wc >= 29:
        reasons.append("long sentence")
    tokens = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z-]+", s)]
    abstract = sum(1 for w in tokens if w in ABSTRACT_WORDS)
    if wc >= 16 and abstract >= 5:
        reasons.append("many abstract terms")
    if wc >= 16 and flesch(s) < 32:
        reasons.append("hard-to-read sentence")
    # Dense punctuation is often a sign of compressed analyst prose.
    if wc >= 16 and (s.count(";") + s.count(":") + s.count("—")) >= 2:
        reasons.append("dense sentence structure")
    # Preserve order while deduplicating labels.
    return list(dict.fromkeys(reasons))


def numeric_tokens(text: str) -> Counter:
    # Years, percentages, decimal values, counts and currency-like numbers are semantic facts.
    return Counter(re.findall(r"(?<![A-Za-z])(?:€|\$|£)?\d+(?:[.,]\d+)*(?:%|bn|m|k)?", text, flags=re.I))


def load_approved(path: Path | None = None) -> dict:
    p = path or ROOT / "reader_language" / "approved.json"
    if not p.exists():
        return {"schema": "radar-reader-language-approved-v1", "updated_at": "", "items": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("items"), dict):
        raise ValueError("reader_language/approved.json has an invalid shape")
    return data
