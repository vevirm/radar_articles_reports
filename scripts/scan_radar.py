#!/usr/bin/env python3
"""R&I × Geopolitics + Foresight Methodology radar scanner (EU-first, balanced).

Key properties
--------------
* No API keys or paid services are required.
* Discovery is broad; admission is selective but not brittle.
* Strand A requires substantive R&I policy + geopolitics/economic security + EU relevance.
  A same-sentence bridge is strong evidence, but a document-level bridge can also qualify.
* Strand B requires methodology to be substantive, while allowing high-quality transferable
  public-sector R&I/S&T methods even when the case study is not explicitly EU-focused.
* Strand C is not a general news feed: every item must be factual current-window
  reporting and must anchor to an accepted A/B publication or recurring A/B theme.
* Calls, facility pages, project pages, press releases, news/blog pages, events,
  jobs and other non-analytical material are rejected for A/B.

The scanner aims for a balanced precision/recall trade-off. It does not pad.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import gzip
import io
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus, urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "radar_config.json"
OUT_PATH = ROOT / "radar.json"

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    CONFIG = json.load(f)

DATE_FLOOR = dt.date.fromisoformat(CONFIG["date_floor"])
NEWS_LOOKBACK_HOURS = int(CONFIG.get("news_lookback_hours", 48))
FIRST_NEWS_LOOKBACK_HOURS = int(CONFIG.get("first_news_lookback_hours", 168))
DISCOVERY_OVERLAP_DAYS = int(CONFIG.get("discovery_overlap_days", 14))
MAX_NEW_AB = int(CONFIG.get("max_new_ab_per_scan", 15))
MAX_C = int(CONFIG.get("max_c_per_scan", 5))
MAX_CORPUS = int(CONFIG.get("max_corpus_per_strand", 60))
REQUEST_TIMEOUT = 16
UA = "RI-Geopolitics-Radar/2.0 (+https://vevirm.github.io/radar_articles_reports/)"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": UA,
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

# ---------------------------------------------------------------------------
# Admission vocabulary. These are evidence families, not a keyword score.
# Discovery can use loose terms; admission requires the gates below.
# ---------------------------------------------------------------------------
RI_STRONG = [
    "research and innovation", "research & innovation", "r&i policy", "research policy",
    "innovation policy", "science policy", "technology policy", "research security",
    "science diplomacy", "research collaboration", "scientific collaboration",
    "science and technology cooperation", "scientific cooperation", "research funding",
    "research programme", "research program", "horizon europe", "fp10",
    "european research area", "research system", "innovation system", "talent mobility",
    "international research cooperation", "international scientific cooperation",
    "research governance", "innovation governance", "research excellence",
    "innovation ecosystem", "research infrastructure policy", "knowledge security",
]
RI_GENERIC = ["research", "science", "innovation", "technology", "university", "academic"]
POLICY_CONTEXT = [
    "policy", "strategy", "governance", "funding", "cooperation", "collaboration",
    "programme", "program", "framework", "regulation", "recommendation", "government",
    "ministry", "commission", "council", "system", "institution", "security",
    "diplomacy", "mobility", "participation", "association", "internationalisation",
    "internationalization", "screening", "controls", "restrictions",
]
GEO_STRONG = [
    "geopolit", "geoeconomic", "economic security", "strategic autonomy",
    "open strategic autonomy", "technological sovereignty", "technology sovereignty",
    "strategic sovereignty", "de-risk", "derisk", "foreign interference",
    "foreign influence", "export control", "dual-use", "dual use", "strategic competition",
    "technology competition", "u.s.-china", "us-china", "us–china", "sino-american",
    "national security", "research security", "trusted research", "strategic dependency",
    "strategic dependencies", "weaponization", "weaponisation", "sanctions", "decoupling",
    "science diplomacy", "security screening", "knowledge security", "economic coercion",
    "strategic rivalry", "technology rivalry", "scientific rivalry",
]
CHINA_CONTEXT = ["china", "chinese"]
CHINA_GEO_CONTEXT = [
    "de-risk", "security", "strategic", "geopolit", "export control", "dual use",
    "dual-use", "competition", "dependency", "coercion", "foreign interference",
]
EU_DIRECT = [
    "european union", "european commission", "european parliament", "member state",
    "member states", "horizon europe", "fp10", "european research area", "dg rtd",
    "joint research centre", "joint research center", "jrc", "euiss", "european council",
    "european economic security", "eu research", "eu innovation", "eu science",
    "eu technology", "eu policy", "eu strategy", "eu framework", "eu regulation",
]
EU_GENERIC = ["europe", "european", "europe's", "european countries"]
IMPLICATION_WORDS = [
    "implication", "consequence", "for europe", "for the eu", "europe should", "eu should",
    "europe needs", "eu needs", "europe must", "eu must", "european strategy",
    "european policy", "eu policy", "eu strategy", "for european", "affects europe",
]
FORESIGHT_CORE = [
    "foresight", "scenario", "strategic foresight", "foresight methodology", "foresight method", "foresight methods",
    "foresight practice", "foresight process", "horizon scanning", "scenario method",
    "scenario methods", "scenario methodology", "scenario planning", "scenario design",
    "scenario construction", "scenario development", "anticipatory governance",
    "anticipatory intelligence", "futures methodology", "futures method", "futures methods",
    "foresight evaluation", "weak signal", "weak signals", "strategic intelligence",
]
METHOD_CORE = [
    "methodology", "methods", "method", "design", "evaluation", "evaluate", "framework",
    "process", "practice", "institutional design", "institutionalisation", "institutionalization",
    "bias", "biases", "limitation", "limitations", "participatory", "delphi",
    "morphological analysis", "backcasting", "wind tunnelling", "wind-tunnelling",
    "stress testing", "stress-test", "robustness", "wild card", "wild cards",
    "scenario construction", "scenario development", "scenario building", "sensemaking",
    "sense-making", "integration", "assessment", "governance", "toolkit", "protocol",
]
TREND_ONLY_HINTS = ["megatrends", "trend report", "trends report", "outlook", "future of "]

AB_HARD_EXCLUDE = [
    "op-ed", "op ed", "opinion", "commentary", "editorial", "blog post", "blog",
    "podcast", "student thesis", "master's thesis", "masters thesis", "phd thesis",
    "doctoral thesis", "advertorial", "sponsored", "press release", "news article",
    "news release", "call for proposals", "call for proposal", "funding opportunity",
    "grant opportunity", "tender", "procurement", "vacancy", "job opening", "job vacancy",
    "webinar", "workshop", "conference programme", "conference program", "event page",
    "course page", "training course", "project page", "project description", "facility page",
    "laboratory facility", "lab access", "user access programme", "user access program",
]
URL_HARD_EXCLUDE = [
    "/news/", "/blog/", "/blogs/", "/events/", "/event/", "/jobs/", "/vacancies/",
    "/press-release", "/press_releases", "/podcast", "/webinar", "/training/",
    "/funding-opportunities/", "/calls/", "/call-for", "/projects/",
]
NEWS_EXCLUDE = [
    "opinion", "commentary", "editorial", "analysis:", "analysis -", "column", "viewpoint",
    "podcast", "book review", "letter to the editor", "letters to the editor", "explainer",
    "interview", "comment:", "comment -",
]
NEWS_EVENT_TERMS = [
    "adopt", "approve", "launch", "announce", "suspend", "ban", "restrict", "fund",
    "invest", "sign", "agree", "deal", "delay", "stall", "cancel", "open", "close",
    "create", "set to", "rules", "regulation", "law", "policy", "programme", "program",
    "dataset", "data show", "survey", "report finds", "rises", "falls", "increase",
    "decrease", "cuts", "expands", "joins", "withdraw", "sanction", "screening",
    "investigation", "probe", "blocks", "blocked", "review", "framework", "agreement",
]

THEMES = {
    "research security / foreign interference": ["research security", "foreign interference", "trusted research", "knowledge security", "security screening"],
    "technology sovereignty / strategic autonomy": ["technology sovereignty", "technological sovereignty", "strategic autonomy", "open strategic autonomy"],
    "EU–China S&T cooperation / de-risking": ["eu-china", "china", "chinese", "de-risk", "derisk", "science cooperation", "research cooperation"],
    "export controls / dual use": ["export control", "dual use", "dual-use", "technology transfer"],
    "fragmentation of global science": ["fragmentation", "decoupling", "scientific collaboration", "research collaboration"],
    "transatlantic / US–China S&T competition": ["us-china", "u.s.-china", "us–china", "transatlantic", "strategic competition", "technology competition"],
    "critical and emerging technologies": ["critical technology", "critical technologies", "emerging technology", "semiconductor", "chips", "quantum", "biotech", "artificial intelligence", " ai "],
    "economic security and R&I": ["economic security", "research funding", "innovation funding", "talent mobility", "strategic dependency", "strategic dependencies"],
    "Horizon Europe / FP10 international participation": ["horizon europe", "fp10", "association agreement", "third country", "third-country", "associated country"],
    "science diplomacy": ["science diplomacy", "scientific diplomacy"],
    "foresight / horizon scanning methodology": ["foresight methodology", "foresight method", "strategic foresight", "horizon scanning", "weak signal"],
    "scenario methods under uncertainty": ["scenario method", "scenario methodology", "scenario planning", "scenario design", "scenario construction", "uncertainty"],
    "anticipatory governance / strategic intelligence": ["anticipatory governance", "strategic intelligence", "anticipatory intelligence", "risk assessment"],
}
SPECIFIC_ANCHOR_THEMES = {
    "research security / foreign interference", "export controls / dual use",
    "Horizon Europe / FP10 international participation", "science diplomacy",
    "EU–China S&T cooperation / de-risking",
}
ENTITY_TERMS = [
    "china", "united states", "u.s.", "horizon europe", "fp10", "quantum", "semiconductor",
    "chips", "biotech", "artificial intelligence", "ai", "university", "research security",
    "export control", "dual use", "dual-use", "talent", "association",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def normalized(text: str) -> str:
    text = clean_text(text).lower().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text)


def norm_title(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", normalized(text))).strip()


def tokens(text: str) -> set[str]:
    stop = {"the","and","for","with","from","that","this","into","under","over","are","was","were","will","has","have","its","their","our","new","european","europe","union","policy","research","innovation"}
    return {w for w in re.findall(r"[a-z][a-z0-9-]{2,}", normalized(text)) if w not in stop}


def parse_date(value: Any) -> dt.date | None:
    if not value:
        return None
    try:
        if isinstance(value, dt.datetime):
            return value.date()
        if isinstance(value, dt.date):
            return value
        if isinstance(value, dict) and "date-parts" in value:
            return parse_date(value["date-parts"])
        if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
            p = value[0]
            return dt.date(int(p[0]), int(p[1] if len(p) > 1 else 1), int(p[2] if len(p) > 2 else 1))
        return dateparser.parse(str(value), fuzzy=False).date()
    except Exception:
        return None


def split_sentences(text: str, max_chars: int = 60000) -> list[str]:
    text = clean_text(text)[:max_chars]
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [p.strip() for p in parts if 35 <= len(p.strip()) <= 700]


def distinct_matches(text: str, phrases: Iterable[str]) -> list[str]:
    low = f" {normalized(text)} "
    found = []
    for phrase in phrases:
        p = normalized(phrase)
        if not p:
            continue
        if p == "eu":
            ok = bool(re.search(r"\beu\b", low))
        elif p.endswith("it") and p in {"geopolit"}:
            ok = p in low
        else:
            ok = p in low
        if ok and phrase not in found:
            found.append(phrase)
    return found


def contains_any(text: str, phrases: Iterable[str]) -> bool:
    return bool(distinct_matches(text, phrases))


def has_eu_word(text: str) -> bool:
    return bool(re.search(r"\beu\b", normalized(text)))


def eu_evidence(title: str, abstract: str, body: str) -> tuple[str | None, list[str]]:
    ta = f"{title}. {abstract}"
    direct = distinct_matches(ta, EU_DIRECT)
    if has_eu_word(ta):
        direct.append("EU")
    if direct:
        return "direct", list(dict.fromkeys(direct))[:4]

    full = f"{ta}. {body[:50000]}"
    direct_body = distinct_matches(full, EU_DIRECT)
    if has_eu_word(full):
        direct_body.append("EU")
    # Require multiple body-level direct signals if the title/abstract did not establish EU scope.
    if len(set(direct_body)) >= 2:
        return "direct", list(dict.fromkeys(direct_body))[:4]

    # Derived EU relevance must be an explicit implication sentence, not a passing Europe mention.
    for s in split_sentences(full):
        if contains_any(s, EU_GENERIC) or has_eu_word(s):
            if contains_any(s, IMPLICATION_WORDS) or contains_any(s, ["strategy", "policy", "implications", "consequences", "should", "needs to", "must", "for europe", "for the eu"]):
                return "derived", [s[:260]]
    return None, []


def document_exclusion_reason(title: str, text: str = "", url: str = "", page_type: str = "") -> str | None:
    low = normalized(f"{title} {page_type} {text[:1200]}")
    url_low = normalized(url)
    for marker in AB_HARD_EXCLUDE:
        if marker in low:
            return f"hard exclusion: {marker}"
    for marker in URL_HARD_EXCLUDE:
        if marker in url_low:
            return f"hard exclusion URL: {marker}"
    # High-risk false-positive document types, especially the kind that admitted the PAMEC item.
    title_low = normalized(title)
    if re.search(r"\b(call|calls)\b.*\b(proposal|proposals|application|applications|topic|topics)\b", title_low):
        return "hard exclusion: call/funding page"
    if (re.search(r"\b(facility|laboratory|lab)\b", title_low) or re.search(r"\b(facility|laboratory)\b", low)) and not re.search(r"\b(policy|governance|security|geopolit|strategy|foresight|economic security)\b", title_low):
        return "hard exclusion: facility/laboratory page"
    if "project" in title_low and not re.search(r"\b(report|paper|analysis|study|foresight|policy)\b", title_low):
        return "hard exclusion: project page"
    return None


def china_geo_signal(text: str) -> bool:
    low = normalized(text)
    if not any(x in low for x in CHINA_CONTEXT):
        return False
    return any(x in low for x in CHINA_GEO_CONTEXT)


def gate_scope(title: str, abstract: str, body: str, source_tier: int) -> dict[str, Any]:
    """Return balanced strand evidence.

    Discovery keywords never admit an item on their own.  Strand A still requires
    substantive R&I-policy evidence, substantive geopolitical/economic-security
    evidence and EU relevance.  Unlike the previous strict version, the R&I↔geo
    bridge may be established at document level when the title/abstract and the
    evidence families make the relationship clear.

    Strand B remains methodology-first, but a high-quality non-EU method paper can
    be classed as derived EU relevance when it is clearly transferable to public-
    sector R&I / S&T / strategic-policy foresight.
    """
    ta = clean_text(f"{title}. {abstract}")
    full = clean_text(f"{ta}. {body[:60000]}")
    sentences = split_sentences(full)

    ri_ta = distinct_matches(ta, RI_STRONG)
    ri_full = distinct_matches(full, RI_STRONG)
    ri_generic_ta = distinct_matches(ta, RI_GENERIC)
    policy_ta = distinct_matches(ta, POLICY_CONTEXT)
    policy_full = distinct_matches(full, POLICY_CONTEXT)

    geo_ta = distinct_matches(ta, GEO_STRONG)
    geo_full = distinct_matches(full, GEO_STRONG)
    if china_geo_signal(ta) and "China + security/strategic context" not in geo_ta:
        geo_ta.append("China + security/strategic context")
    if china_geo_signal(full) and "China + security/strategic context" not in geo_full:
        geo_full.append("China + security/strategic context")

    # One strong R&I-policy phrase in title/abstract is enough.  In body-only cases,
    # require either two strong phrases or a strong phrase plus broader policy context.
    ri_substantive = bool(ri_ta) or len(set(ri_full)) >= 2 or (
        bool(ri_full) and len(set(policy_full)) >= 2
    ) or (len(set(ri_generic_ta)) >= 2 and len(set(policy_ta)) >= 2)
    geo_substantive = bool(geo_ta) or len(set(geo_full)) >= 2

    # Strongest bridge: R&I and geopolitical evidence in the same sentence.
    bridge_sentence = ""
    for snt in sentences:
        ri_here = distinct_matches(snt, RI_STRONG)
        if not ri_here:
            generic_here = distinct_matches(snt, RI_GENERIC)
            policy_here = distinct_matches(snt, POLICY_CONTEXT)
            ri_here = ["generic R&I + policy context"] if generic_here and policy_here else []
        geo_here = distinct_matches(snt, GEO_STRONG)
        if not geo_here and china_geo_signal(snt):
            geo_here = ["China + security/strategic context"]
        if ri_here and geo_here:
            bridge_sentence = snt[:420]
            break

    eu_rel, eu_hits = eu_evidence(title, abstract, body)

    # Balanced document-level bridge.  This is deliberately unavailable to weak
    # Tier-3 material unless the title/abstract itself establishes both sides.
    evidence_total = len(set(ri_ta or ri_full)) + len(set(geo_ta or geo_full))
    ta_bridge = bool(ri_ta and geo_ta)
    mixed_bridge = bool(
        source_tier <= 2
        and eu_rel
        and evidence_total >= 3
        and (ri_ta or geo_ta)
        and ri_substantive
        and geo_substantive
    )
    inherent_bridge = contains_any(full, [
        "research security", "knowledge security", "science diplomacy",
        "technology sovereignty", "technological sovereignty",
        "economic security", "strategic autonomy", "open strategic autonomy",
        "export control", "dual-use", "dual use", "de-risk", "derisk",
    ]) and ri_substantive and geo_substantive
    bridge_supported = bool(bridge_sentence or ta_bridge or mixed_bridge or inherent_bridge)
    bridge_mode = "sentence" if bridge_sentence else "title/abstract" if ta_bridge else "document-level" if (mixed_bridge or inherent_bridge) else ""

    # Foresight methodology evidence.
    foresight_ta = distinct_matches(ta, FORESIGHT_CORE)
    foresight_full = distinct_matches(full, FORESIGHT_CORE)
    method_ta = distinct_matches(ta, METHOD_CORE)
    method_full = distinct_matches(full, METHOD_CORE)
    method_bridge = ""
    method_bridge_index = 999
    for idx, snt in enumerate(sentences):
        low_s = normalized(snt)
        negated = any(x in low_s for x in [
            "does not discuss", "does not address", "does not evaluate", "does not explain",
            "not discuss", "not address", "without discussing", "without methodological",
            "no methodological", "lacks methodological", "lack methodological",
        ])
        if not negated and distinct_matches(snt, FORESIGHT_CORE) and distinct_matches(snt, METHOD_CORE):
            method_bridge = snt[:420]
            method_bridge_index = idx
            break

    explicit_method_title = (
        contains_any(title, ["methodology", "methods", "method", "evaluation", "design", "framework", "approach"])
        and contains_any(title, FORESIGHT_CORE)
    )
    foresight_substantive = bool(foresight_ta) or len(set(foresight_full)) >= 2

    # The strict version required foresight+method evidence in one sentence.  Here
    # substantial title/abstract coverage across adjacent sentences is sufficient.
    ta_method_negated = any(x in normalized(ta) for x in [
        "does not discuss", "does not address", "does not evaluate", "does not explain",
        "without methodological", "no methodological", "lacks methodological", "lack methodological",
    ])
    method_in_ta = bool(foresight_ta and method_ta and not ta_method_negated)
    early_method_body = method_bridge_index < 18 and len(set(method_full)) >= 2
    method_substantive = bool(explicit_method_title or method_in_ta or early_method_body)

    # B must still be useful to R&I/S&T/strategic-policy practice.  Generic academic
    # "research" is not enough, which keeps unrelated futures papers out.
    b_context_terms = [
        "research and innovation", "research policy", "innovation policy", "science policy",
        "technology policy", "science and technology", "research security",
        "technology governance", "innovation governance", "public policy", "public sector",
        "government", "regulation", "strategic policy", "economic security",
        "critical technology", "critical technologies", "emerging technology",
        "artificial intelligence", "semiconductor", "quantum", "biotechnology",
    ]
    b_context = bool(ri_substantive or geo_substantive or contains_any(ta, b_context_terms) or contains_any(full[:12000], b_context_terms))

    trend_only = contains_any(title, TREND_ONLY_HINTS) and not (explicit_method_title or method_in_ta or method_bridge)

    # Direct/explicit EU relevance remains the normal B path.  For genuinely
    # methodology-first high-quality work, derived relevance may be assigned on
    # transferability grounds when the context is public-sector R&I/S&T policy.
    b_eu_rel = eu_rel
    b_transferable = False
    if not b_eu_rel and source_tier <= 2 and foresight_substantive and method_substantive and b_context:
        if explicit_method_title or (len(set(method_ta)) >= 2 and bool(foresight_ta)):
            b_eu_rel = "derived"
            b_transferable = True

    a_pass = bool(ri_substantive and geo_substantive and eu_rel and bridge_supported)
    b_pass = bool(foresight_substantive and method_substantive and b_context and b_eu_rel and not trend_only)

    # A must never borrow B's transferability-only EU label.
    overall_eu = eu_rel or (b_eu_rel if b_pass else None)

    return {
        "a_pass": a_pass,
        "b_pass": b_pass,
        "eu_relevance": overall_eu,
        "eu_evidence": eu_hits or (["transferable to EU public-sector R&I/S&T foresight"] if b_transferable else []),
        "ri_evidence": (ri_ta or ri_full)[:5],
        "geo_evidence": (geo_ta or geo_full)[:5],
        "bridge_sentence": bridge_sentence,
        "bridge_supported": bridge_supported,
        "bridge_mode": bridge_mode,
        "foresight_evidence": (foresight_ta or foresight_full)[:5],
        "method_evidence": (method_ta or method_full)[:6],
        "method_bridge": method_bridge,
        "b_transferable": b_transferable,
        "trend_only": trend_only,
        "source_tier": source_tier,
    }

def themes_for(text: str) -> list[str]:
    low = f" {normalized(text)} "
    result = []
    for name, terms in THEMES.items():
        if any(normalized(t) in low for t in terms):
            result.append(name)
    return result


def get(url: str, timeout: int = REQUEST_TIMEOUT) -> requests.Response | None:
    try:
        r = SESSION.get(url, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return r
    except requests.RequestException:
        pass
    return None


def openalex_abstract(inv: dict[str, list[int]] | None) -> str:
    if not inv:
        return ""
    pairs = []
    for word, positions in inv.items():
        for pos in positions:
            pairs.append((pos, word))
    return clean_text(" ".join(w for _, w in sorted(pairs)))


def url_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def source_rank_for_journal(name: str) -> tuple[int | None, float, str]:
    n = normalized(name)
    exact = {normalized(x) for x in CONFIG["tier2_journals"]}
    comparable = {normalized(x) for x in CONFIG.get("tier2_comparable_journals", [])}
    if n in exact:
        return 2, 2.0, "Tier 2"
    if n in comparable:
        return 2, 2.4, "Tier 2 comparable"
    return None, 9.0, ""


def institution_source_for_domain(domain: str) -> tuple[str, int] | None:
    d = domain.removeprefix("www.")
    for src in CONFIG["institution_sources"]:
        allowed = src["domain"].lower().removeprefix("www.")
        if d == allowed or d.endswith("." + allowed):
            return src["name"], int(src["tier"])
    return None


def openalex_locations(work: dict[str, Any]) -> list[str]:
    urls = []
    for loc in [work.get("primary_location") or {}, work.get("best_oa_location") or {}] + list(work.get("locations") or []):
        for key in ("landing_page_url", "pdf_url"):
            u = clean_text(loc.get(key))
            if u and u not in urls:
                urls.append(u)
    return urls


def openalex_authors(work: dict[str, Any]) -> str:
    names = []
    for a in (work.get("authorships") or [])[:8]:
        n = clean_text((a.get("author") or {}).get("display_name"))
        if n:
            names.append(n)
    if len(work.get("authorships") or []) > 8:
        names.append("et al.")
    return ", ".join(names) or "Unknown author(s)"


def quality_from_openalex(work: dict[str, Any]) -> tuple[bool, int, float, str, str]:
    typ = normalized(work.get("type"))
    src = (work.get("primary_location") or {}).get("source") or {}
    source_name = clean_text(src.get("display_name"))
    source_type = normalized(src.get("type"))

    tier, rank, tier_label = source_rank_for_journal(source_name)
    if tier:
        return True, tier, rank, source_name, tier_label

    # Whitelisted institutional output indexed in OpenAlex.
    for u in openalex_locations(work):
        hit = institution_source_for_domain(url_domain(u))
        if hit:
            source, source_tier = hit
            return True, source_tier, float(source_tier), source, f"Tier {source_tier}"

    # Preprints are allowed only from arXiv and are ranked as Tier 3.
    if typ in {"preprint", "posted-content", "working-paper", "working paper"}:
        if any(url_domain(u).endswith("arxiv.org") for u in openalex_locations(work)):
            return True, 3, 3.2, "arXiv", "Tier 3 preprint"

    # Do not infer peer review from an arbitrary journal record: the automated radar is conservative.
    return False, 9, 9.0, source_name or "Unknown source", ""


def candidate_from_openalex(work: dict[str, Any]) -> dict[str, Any] | None:
    title = clean_text(work.get("display_name"))
    abstract = openalex_abstract(work.get("abstract_inverted_index"))
    date = parse_date(work.get("publication_date"))
    if not title or not date or date < DATE_FLOOR:
        return None
    if document_exclusion_reason(title, abstract):
        return None
    quality_ok, tier, source_rank, source, tier_label = quality_from_openalex(work)
    if not quality_ok:
        return None
    ev = gate_scope(title, abstract, "", tier)
    if not (ev["a_pass"] or ev["b_pass"]):
        return None
    if tier == 3 and ev["eu_relevance"] is None:
        return None

    doi = clean_text(work.get("doi"))
    if doi and not doi.startswith("http"):
        doi = "https://doi.org/" + doi.removeprefix("doi:")
    link = doi or next((u for u in openalex_locations(work) if u), "")
    typ = normalized(work.get("type")) or "publication"
    is_preprint = typ in {"preprint", "posted-content", "working-paper", "working paper"}
    strand = "both" if ev["a_pass"] and ev["b_pass"] else "A" if ev["a_pass"] else "B"
    full = f"{title}. {abstract}"
    return build_item(
        title=title, authors=openalex_authors(work), source=source, date=date, link=link,
        item_type="preprint" if is_preprint else "peer-reviewed article",
        strand=strand, evidence=ev, source_rank=source_rank, tier_label=tier_label,
        text=full, doi=doi, preprint=is_preprint,
    )


def collect_openalex(from_date: dt.date, warnings: list[str]) -> list[dict[str, Any]]:
    out = []
    queries = list(dict.fromkeys(CONFIG["queries_a"] + CONFIG["queries_b"]))
    per_page = int(CONFIG.get("openalex_per_query", 45))
    for q in queries:
        params = {
            "search": q,
            "filter": f"from_publication_date:{from_date.isoformat()}",
            "sort": "publication_date:desc",
            "per-page": str(per_page),
        }
        try:
            r = SESSION.get("https://api.openalex.org/works", params=params, timeout=22)
            if r.status_code != 200:
                warnings.append(f"OpenAlex HTTP {r.status_code}")
                continue
            works = r.json().get("results", [])
        except Exception as e:
            warnings.append(f"OpenAlex: {type(e).__name__}")
            continue
        for work in works:
            item = candidate_from_openalex(work)
            if item:
                out.append(item)
    return out


def crossref_date(item: dict[str, Any]) -> dt.date | None:
    for key in ("published-online", "published-print", "published", "issued"):
        d = parse_date(item.get(key))
        if d:
            return d
    return None


def crossref_authors(item: dict[str, Any]) -> str:
    names = []
    for a in (item.get("author") or [])[:8]:
        n = " ".join(x for x in [clean_text(a.get("given")), clean_text(a.get("family"))] if x).strip()
        if n:
            names.append(n)
    if len(item.get("author") or []) > 8:
        names.append("et al.")
    return ", ".join(names) or clean_text(item.get("publisher")) or "Unknown author(s)"


def quality_from_crossref(item: dict[str, Any]) -> tuple[bool, int, float, str, str, str]:
    journal = clean_text((item.get("container-title") or [""])[0])
    typ = normalized(item.get("type"))
    tier, rank, tier_label = source_rank_for_journal(journal)
    if tier and typ in {"journal-article", "article", "review", "proceedings-article"}:
        return True, tier, rank, journal, tier_label, "peer-reviewed article"
    publisher = clean_text(item.get("publisher"))
    if typ in {"report", "report-component", "book", "book-chapter", "posted-content"}:
        for p in CONFIG.get("crossref_institution_publishers", []):
            if normalized(p) in normalized(publisher + " " + journal):
                tier_guess = 3 if any(x in normalized(p) for x in ["rand", "brookings", "carnegie", "strategic and international"]) else 1
                return True, tier_guess, float(tier_guess), publisher or journal, f"Tier {tier_guess}", "institutional report"
    return False, 9, 9.0, journal or publisher or "Unknown source", "", typ or "publication"


def candidate_from_crossref(item: dict[str, Any]) -> dict[str, Any] | None:
    title = clean_text((item.get("title") or [""])[0])
    abstract = clean_text(item.get("abstract"))
    date = crossref_date(item)
    if not title or not date or date < DATE_FLOOR:
        return None
    if document_exclusion_reason(title, abstract):
        return None
    ok, tier, source_rank, source, tier_label, item_type = quality_from_crossref(item)
    if not ok:
        return None
    ev = gate_scope(title, abstract, "", tier)
    if not (ev["a_pass"] or ev["b_pass"]):
        return None
    if tier == 3 and ev["eu_relevance"] is None:
        return None
    doi_raw = clean_text(item.get("DOI"))
    doi = f"https://doi.org/{doi_raw}" if doi_raw else ""
    link = doi or clean_text(item.get("URL"))
    typ = normalized(item.get("type"))
    preprint = typ in {"posted-content", "preprint"}
    strand = "both" if ev["a_pass"] and ev["b_pass"] else "A" if ev["a_pass"] else "B"
    return build_item(
        title=title, authors=crossref_authors(item), source=source, date=date, link=link,
        item_type="preprint" if preprint else item_type, strand=strand, evidence=ev,
        source_rank=source_rank, tier_label=tier_label, text=f"{title}. {abstract}",
        doi=doi, preprint=preprint,
    )


def collect_crossref(from_date: dt.date, warnings: list[str]) -> list[dict[str, Any]]:
    out = []
    queries = list(dict.fromkeys(CONFIG["queries_a"] + CONFIG["queries_b"]))
    rows = int(CONFIG.get("crossref_rows_per_query", 35))
    for q in queries:
        params = {
            "query.bibliographic": q,
            "filter": f"from-pub-date:{from_date.isoformat()}",
            "rows": rows,
            "sort": "published",
            "order": "desc",
            "select": "DOI,title,author,publisher,container-title,published-online,published-print,published,issued,type,URL,abstract",
        }
        try:
            r = SESSION.get("https://api.crossref.org/works", params=params, timeout=22)
            if r.status_code != 200:
                warnings.append(f"Crossref HTTP {r.status_code}")
                continue
            works = r.json().get("message", {}).get("items", [])
        except Exception as e:
            warnings.append(f"Crossref: {type(e).__name__}")
            continue
        for item in works:
            c = candidate_from_crossref(item)
            if c:
                out.append(c)
    return out


def decompress_xml(content: bytes) -> bytes:
    if content[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(content)
        except Exception:
            return content
    return content


def localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def discover_sitemaps(domain: str) -> list[str]:
    base = f"https://{domain}"
    urls = []
    r = get(base + "/robots.txt", timeout=12)
    if r:
        for line in r.text.splitlines():
            if line.lower().startswith("sitemap:"):
                urls.append(line.split(":", 1)[1].strip())
    urls.extend([base + "/sitemap.xml", base + "/sitemap_index.xml", base + "/sitemap-index.xml"])
    return list(dict.fromkeys(u for u in urls if u))[:8]


def sitemap_entries(url: str, depth: int = 0, child_budget: int = 5) -> list[tuple[str, dt.date | None]]:
    if depth > 2 or child_budget <= 0:
        return []
    r = get(url, timeout=18)
    if not r or len(r.content) > 15_000_000:
        return []
    try:
        root = ET.fromstring(decompress_xml(r.content))
    except Exception:
        return []
    kind = localname(root.tag)
    if kind == "sitemapindex":
        children = []
        for sm in list(root):
            loc = None; last = None
            for ch in list(sm):
                if localname(ch.tag) == "loc": loc = (ch.text or "").strip()
                elif localname(ch.tag) == "lastmod": last = parse_date((ch.text or "").strip())
            if loc:
                low = normalized(loc)
                pr = 0
                if any(k in low for k in ["publication", "research", "report", "paper", "2026", "article"]): pr += 3
                if last and last >= DATE_FLOOR: pr += 2
                children.append((pr, last or dt.date.min, loc))
        children.sort(reverse=True)
        out = []
        for _, _, child in children[:child_budget]:
            out.extend(sitemap_entries(child, depth + 1, max(1, child_budget - 1)))
            if len(out) >= 350:
                break
        return out[:350]
    if kind == "urlset":
        out = []
        for node in list(root):
            loc = None; last = None
            for ch in list(node):
                if localname(ch.tag) == "loc": loc = (ch.text or "").strip()
                elif localname(ch.tag) == "lastmod": last = parse_date((ch.text or "").strip())
            if loc:
                out.append((loc, last))
        return out
    return []


def institution_url_candidate(url: str, lastmod: dt.date | None, from_date: dt.date) -> bool:
    low = normalized(url)
    if any(x in low for x in URL_HARD_EXCLUDE):
        return False
    if lastmod and lastmod < from_date - dt.timedelta(days=10):
        return False
    hints = [
        "publication", "report", "paper", "policy-brief", "policy_brief", "study", "analysis",
        "research", "foresight", "horizon", "scenario", "security", "geopolit", "economic-security",
        "strategic-autonomy", "sovereignty", "science-diplomacy", "technology", "innovation",
        "working-paper", "discussion-paper", "insight", "commentary-paper", "2026",
    ]
    return any(h in low for h in hints)


def meta_content(soup: BeautifulSoup, keys: Iterable[str]) -> str:
    for key in keys:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key}) or soup.find("meta", attrs={"itemprop": key})
        if tag and tag.get("content"):
            return clean_text(tag.get("content"))
    return ""


def jsonld_objects(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from jsonld_objects(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from jsonld_objects(v)


def pdf_text(url: str) -> tuple[str, int]:
    try:
        r = SESSION.get(url, timeout=24)
        if r.status_code != 200 or len(r.content) > 22_000_000:
            return "", 0
        reader = PdfReader(io.BytesIO(r.content))
        texts = []
        for page in reader.pages[:55]:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                pass
        txt = clean_text(" ".join(texts))
        return txt, len(txt.split())
    except Exception:
        return "", 0


def parse_institution_page(url: str, source: str, tier: int) -> dict[str, Any] | None:
    r = get(url, timeout=20)
    if not r or "html" not in r.headers.get("content-type", "text/html"):
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    title = meta_content(soup, ["og:title", "twitter:title", "headline"]) or clean_text(soup.h1.get_text(" ", strip=True) if soup.h1 else "")
    page_type = meta_content(soup, ["og:type", "article:section", "type"])
    desc = meta_content(soup, ["description", "og:description", "twitter:description"])
    exclusion = document_exclusion_reason(title, desc, r.url, page_type)
    if not title or exclusion:
        return None

    published = None
    authors: list[str] = []
    article_body = ""
    for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        try:
            data = json.loads(script.string or script.get_text())
        except Exception:
            continue
        for obj in jsonld_objects(data):
            if not published:
                published = parse_date(obj.get("datePublished"))
            if not article_body and obj.get("articleBody"):
                article_body = clean_text(obj.get("articleBody"))
            a = obj.get("author")
            if isinstance(a, dict) and a.get("name"):
                authors.append(clean_text(a["name"]))
            elif isinstance(a, list):
                for au in a:
                    if isinstance(au, dict) and au.get("name"):
                        authors.append(clean_text(au["name"]))
                    elif isinstance(au, str):
                        authors.append(clean_text(au))
    if not published:
        published = parse_date(meta_content(soup, ["article:published_time", "datePublished", "date", "DC.date", "parsely-pub-date", "pubdate", "publication_date"]))
    if not published or published < DATE_FLOOR:
        return None

    canonical = ""
    can = soup.find("link", rel=lambda v: v and "canonical" in v)
    if can and can.get("href"):
        canonical = urljoin(r.url, can["href"])

    for bad in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        bad.decompose()
    container = soup.find("article") or soup.find("main") or soup.body
    body = article_body or clean_text(container.get_text(" ", strip=True) if container else "")
    word_count = len(body.split())
    pdf_url = ""
    for a in soup.find_all("a", href=True):
        href = urljoin(r.url, a["href"])
        label = clean_text(a.get_text(" ", strip=True)).lower()
        if ".pdf" in href.lower() or "download pdf" in label or label in {"pdf", "download report", "download paper"}:
            pdf_url = href
            break
    if pdf_url and word_count < 2500:
        ptxt, pwords = pdf_text(pdf_url)
        if pwords > word_count:
            body, word_count = ptxt, pwords

    # Substantive-length rule.  Long analytical work is preferred, but concise
    # Tier-1 policy papers can qualify when the topic gates themselves are strong.
    low_title = normalized(title)
    if word_count < 1500:
        brief_exception = tier == 1 and word_count >= 900 and any(x in low_title for x in [
            "policy brief", "briefing", "working paper", "discussion paper", "policy paper",
            "report", "study", "analysis", "strategic", "security", "foresight"
        ])
        if not brief_exception:
            return None

    ev = gate_scope(title, desc, body, tier)
    if not (ev["a_pass"] or ev["b_pass"]):
        return None
    if tier == 3 and ev["eu_relevance"] is None:
        return None

    strand = "both" if ev["a_pass"] and ev["b_pass"] else "A" if ev["a_pass"] else "B"
    item_type = "institutional report"
    if "policy brief" in low_title or "briefing" in low_title:
        item_type = "policy brief"
    elif "working paper" in low_title or "discussion paper" in low_title:
        item_type = "working paper"
    elif word_count < 3500:
        item_type = "research/policy paper"
    return build_item(
        title=title, authors=", ".join(dict.fromkeys(a for a in authors if a)) or source,
        source=source, date=published, link=pdf_url or canonical or r.url, item_type=item_type,
        strand=strand, evidence=ev, source_rank=float(tier), tier_label=f"Tier {tier}",
        text=f"{title}. {desc}. {body[:45000]}", doi="", preprint=False,
    )


def _discover_domain(src: dict[str, Any], from_date: dt.date) -> tuple[list[tuple[str, str, int]], str | None]:
    domain = src["domain"]
    entries = []
    for sm in discover_sitemaps(domain):
        entries.extend(sitemap_entries(sm))
        if len(entries) >= 180:
            break
    if not entries:
        return [], f"No usable sitemap: {domain}"
    seen = set(); jobs = []
    limit = int(CONFIG.get("institution_pages_per_domain", 14))
    for u, last in sorted(entries, key=lambda x: x[1] or dt.date.min, reverse=True):
        if u in seen or not institution_url_candidate(u, last, from_date):
            continue
        seen.add(u)
        jobs.append((u, src["name"], int(src["tier"])))
        if len(jobs) >= limit:
            break
    return jobs, None


def collect_institutions(from_date: dt.date, warnings: list[str]) -> list[dict[str, Any]]:
    jobs = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(_discover_domain, src, from_date) for src in CONFIG["institution_sources"]]
        for fut in cf.as_completed(futs):
            try:
                found, warn = fut.result()
                jobs.extend(found)
                if warn:
                    warnings.append(warn)
            except Exception as e:
                warnings.append(f"Institution sitemap: {type(e).__name__}")
    out = []
    with cf.ThreadPoolExecutor(max_workers=14) as ex:
        futs = [ex.submit(parse_institution_page, u, s, t) for u, s, t in jobs[:300]]
        for fut in cf.as_completed(futs):
            try:
                item = fut.result()
                if item:
                    out.append(item)
            except Exception as e:
                warnings.append(f"Institution page: {type(e).__name__}")
    return out


def evidence_summary(evidence: dict[str, Any], strand: str) -> str:
    parts = []
    if strand in {"A", "both"}:
        if evidence.get("ri_evidence"):
            parts.append("R&I: " + ", ".join(evidence["ri_evidence"][:2]))
        if evidence.get("geo_evidence"):
            parts.append("geopolitics: " + ", ".join(evidence["geo_evidence"][:2]))
    if strand in {"B", "both"}:
        if evidence.get("foresight_evidence"):
            parts.append("foresight: " + ", ".join(evidence["foresight_evidence"][:2]))
        if evidence.get("method_evidence"):
            parts.append("method: " + ", ".join(evidence["method_evidence"][:2]))
    return "; ".join(parts)


def make_summary(text: str, evidence: dict[str, Any], strand: str, title: str) -> str:
    sents = split_sentences(text)
    selected = []
    # Prefer sentences that carry explicit gate evidence.
    for key in ("bridge_sentence", "method_bridge"):
        s = clean_text(evidence.get(key))
        if s and s not in selected:
            selected.append(s)
    # Then prefer EU-scope and method/geo/R&I evidence sentences.
    evidence_terms = (
        evidence.get("ri_evidence", []) + evidence.get("geo_evidence", []) +
        evidence.get("foresight_evidence", []) + evidence.get("method_evidence", [])
    )
    scored = []
    for i, s in enumerate(sents[:60]):
        score = len(distinct_matches(s, evidence_terms)) * 3
        if contains_any(s, EU_DIRECT + EU_GENERIC) or has_eu_word(s): score += 2
        if i == 0: score += 1
        scored.append((score, -i, s))
    for _, _, s in sorted(scored, reverse=True):
        if s not in selected:
            selected.append(s)
        if len(selected) >= 3:
            break
    synthetic = [
        f"The publication examines {title.rstrip('.')}",
        f"The automated admission gate found {evidence_summary(evidence, strand) or 'substantive evidence matching the strand criteria'}",
        f"Its EU relevance is classified as {evidence.get('eu_relevance') or 'not established'} based on explicit EU/European policy content",
    ]
    while len(selected) < 3:
        selected.append(synthetic[len(selected)])
    out = []
    for s in selected[:3]:
        s = s.strip()
        if not s.endswith((".", "!", "?")):
            s += "."
        out.append(s)
    return " ".join(out)


def relevance_note(evidence: dict[str, Any], strand: str) -> str:
    eu = (evidence.get("eu_relevance") or "unknown").capitalize()
    if strand == "A":
        return f"{eu} EU relevance; admitted after substantive R&I-policy and geopolitics/economic-security gates passed with a supported document-level connection."
    if strand == "B":
        return f"{eu} EU relevance; admitted because foresight methodology is substantive and relevant to R&I/S&T or strategic-policy practice, not merely a trend/scenario output."
    return f"{eu} EU relevance; independently passes both Strand A and Strand B admission gates."


def build_item(*, title: str, authors: str, source: str, date: dt.date, link: str,
               item_type: str, strand: str, evidence: dict[str, Any], source_rank: float,
               tier_label: str, text: str, doi: str, preprint: bool) -> dict[str, Any]:
    themes = themes_for(text)
    return {
        "title": title,
        "authors": authors,
        "source": source,
        "date": date.isoformat(),
        "link": link,
        "type": item_type,
        "strand": strand,
        "eu_relevance": evidence.get("eu_relevance"),
        "summary": make_summary(text, evidence, strand, title),
        "relevance_note": relevance_note(evidence, strand),
        "source_tier": tier_label,
        "_source_rank": source_rank,
        "_themes": themes,
        "_doi": normalized(doi).replace("https://doi.org/", ""),
        "_preprint": preprint,
        "_confidence": (
            len(evidence.get("ri_evidence", [])) + len(evidence.get("geo_evidence", [])) +
            len(evidence.get("foresight_evidence", [])) + len(evidence.get("method_evidence", [])) +
            (2 if evidence.get("bridge_sentence") else 0) + (2 if evidence.get("method_bridge") else 0)
        ),
        "_gate_evidence": {
            "ri": evidence.get("ri_evidence", []),
            "geopolitics": evidence.get("geo_evidence", []),
            "bridge": evidence.get("bridge_sentence", ""),
            "foresight": evidence.get("foresight_evidence", []),
            "method": evidence.get("method_evidence", []),
            "method_bridge": evidence.get("method_bridge", ""),
            "eu": evidence.get("eu_evidence", []),
        },
    }


def identity(item: dict[str, Any]) -> str:
    doi = normalized(item.get("_doi") or item.get("link", ""))
    m = re.search(r"10\.\d{4,9}/[^\s?#]+", doi)
    if m:
        return "doi:" + m.group(0).rstrip(".,)")
    return "title:" + norm_title(item.get("title", ""))


def dedupe_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for item in items:
        key = identity(item)
        if key == "title:":
            continue
        old = by_key.get(key)
        if old is None:
            by_key[key] = item
            continue
        # Prefer a published version over a preprint, then better source rank, then richer evidence.
        candidate_key = (bool(item.get("_preprint")), item.get("_source_rank", 9.0), -item.get("_confidence", 0))
        old_key = (bool(old.get("_preprint")), old.get("_source_rank", 9.0), -old.get("_confidence", 0))
        if candidate_key < old_key:
            by_key[key] = item
    # Title-level preprint cleanup even if identifiers differ.
    published_titles = {norm_title(x["title"]) for x in by_key.values() if not x.get("_preprint")}
    out = [x for x in by_key.values() if not (x.get("_preprint") and norm_title(x["title"]) in published_titles)]
    return out


def rank_candidate(item: dict[str, Any]):
    eu = 0 if item.get("eu_relevance") == "direct" else 1
    d = parse_date(item.get("date")) or dt.date.min
    return (eu, float(item.get("_source_rank", 9.0)), -d.toordinal(), -int(item.get("_confidence", 0)))


def public_item(item: dict[str, Any], *, new_this_scan: bool = False, first_seen: str | None = None) -> dict[str, Any]:
    out = {k: v for k, v in item.items() if not k.startswith("_")}
    out["new_this_scan"] = bool(new_this_scan)
    if first_seen:
        out["first_seen"] = first_seen
    return out


def _valid_saved_radar(data: Any) -> bool:
    """True for a completed/populated radar worth preserving across package uploads."""
    if not isinstance(data, dict):
        return False
    a = data.get("strand_a") if isinstance(data.get("strand_a"), list) else []
    b = data.get("strand_b") if isinstance(data.get("strand_b"), list) else []
    return bool(data.get("first_scan_complete") or data.get("last_updated") or a or b)


def _recover_radar_from_git(max_commits: int = 80) -> dict[str, Any]:
    """Find the strongest recent saved radar in Git history.

    This protects the cumulative A/B corpus when an upgrade ZIP contains a
    reset/pending radar.json.  We inspect recent ancestors and prefer the
    candidate with the largest saved A+B corpus, breaking ties by recency.
    GitHub Actions checks out full history (fetch-depth: 0), so this works in
    the normal scanner workflow and also tolerates several upload commits in a
    row before a scan runs.
    """
    try:
        revs = subprocess.run(
            ["git", "rev-list", f"--max-count={max_commits}", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=12, check=True,
        ).stdout.splitlines()
    except Exception:
        return {}

    best: tuple[int, int, dict[str, Any]] | None = None
    for recency_index, rev in enumerate(revs):
        try:
            raw = subprocess.run(
                ["git", "show", f"{rev}:radar.json"],
                cwd=ROOT, capture_output=True, text=True, timeout=8, check=True,
            ).stdout
            data = json.loads(raw)
        except Exception:
            continue
        if not _valid_saved_radar(data):
            continue
        a = data.get("strand_a") if isinstance(data.get("strand_a"), list) else []
        b = data.get("strand_b") if isinstance(data.get("strand_b"), list) else []
        score = len(a) + len(b)
        candidate = (score, -recency_index, data)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return best[2] if best else {}


def load_previous() -> dict[str, Any]:
    try:
        current = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    except Exception:
        current = {}

    # Normal scans use the current radar exactly as written.  Recovery is only
    # invoked for a reset/pending template (or a missing/corrupt file).
    if _valid_saved_radar(current):
        return current

    recovered = _recover_radar_from_git()
    if recovered:
        print(
            "Recovered prior cumulative radar corpus from Git history "
            f"(A={len(recovered.get('strand_a', []))}, "
            f"B={len(recovered.get('strand_b', []))})."
        )
        return recovered
    return current if isinstance(current, dict) else {}


def internalize_previous(item: dict[str, Any]) -> dict[str, Any]:
    x = dict(item)
    x["_themes"] = themes_for(f"{x.get('title','')} {x.get('summary','')}")
    x["_source_rank"] = 1.0 if "Tier 1" in x.get("source_tier", "") else 2.4 if "comparable" in x.get("source_tier", "") else 2.0 if "Tier 2" in x.get("source_tier", "") else 3.0
    x["_confidence"] = 0
    x["_doi"] = normalized(x.get("link", ""))
    x["_preprint"] = x.get("type") == "preprint"
    return x


def merge_corpus(previous: list[dict[str, Any]], new_items: list[dict[str, Any]], strand_name: str, now_iso: str) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for old in previous:
        internal = internalize_previous(old)
        internal["new_this_scan"] = False
        merged[identity(internal)] = internal
    new_ids = set()
    for item in new_items:
        if item.get("strand") not in {strand_name, "both"}:
            continue
        key = identity(item)
        new_ids.add(key)
        existing = merged.get(key)
        first_seen = existing.get("first_seen") if existing else now_iso
        merged[key] = {**item, "first_seen": first_seen, "new_this_scan": True}
    vals = list(merged.values())
    vals.sort(key=lambda x: (not bool(x.get("new_this_scan")),) + rank_candidate(x))
    out = []
    for x in vals[:MAX_CORPUS]:
        p = public_item(x, new_this_scan=identity(x) in new_ids, first_seen=x.get("first_seen"))
        out.append(p)
    return out


def parse_feed_time(entry: Any) -> dt.datetime | None:
    st = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if st:
        return dt.datetime(*st[:6], tzinfo=dt.timezone.utc)
    raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if raw:
        try:
            d = dateparser.parse(raw)
            if d.tzinfo is None:
                d = d.replace(tzinfo=dt.timezone.utc)
            return d.astimezone(dt.timezone.utc)
        except Exception:
            pass
    return None


def factual_news(title: str, desc: str) -> bool:
    full = normalized(f"{title} {desc}")
    if any(x in full for x in NEWS_EXCLUDE):
        return False
    if not (has_eu_word(full) or contains_any(full, EU_DIRECT + EU_GENERIC)):
        return False
    return any(x in full for x in NEWS_EVENT_TERMS)


def news_queries(domain: str, lookback_hours: int) -> list[str]:
    days = 7 if lookback_hours > 72 else 2
    when = f"when:{days}d"
    return [
        f'site:{domain} ("research security" OR "foreign interference" OR "science policy" OR "research cooperation" OR "Horizon Europe" OR "science diplomacy") Europe {when}',
        f'site:{domain} ("economic security" OR "technology sovereignty" OR "strategic autonomy" OR "de-risking" OR "de-risk") (research OR innovation OR technology) Europe {when}',
        f'site:{domain} ("export controls" OR "dual use" OR "technology transfer" OR semiconductor OR quantum OR biotech OR "artificial intelligence") (EU OR Europe) {when}',
        f'site:{domain} (China OR US-China OR transatlantic) (research OR science OR technology OR innovation) (EU OR Europe) {when}',
        f'site:{domain} ("third country" OR association OR talent OR researchers OR universities) ("Horizon Europe" OR EU OR European) {when}',
    ]


def collect_news(now: dt.datetime, warnings: list[str], lookback_hours: int | None = None) -> list[dict[str, Any]]:
    lookback_hours = int(lookback_hours or NEWS_LOOKBACK_HOURS)
    start = now - dt.timedelta(hours=lookback_hours)
    out = []
    for src in CONFIG["news_sources"]:
        name, domain = src["name"], src["domain"]
        for q in news_queries(domain, lookback_hours):
            url = "https://news.google.com/rss/search?q=" + quote_plus(q) + "&hl=en-GB&gl=GB&ceid=GB:en"
            try:
                r = SESSION.get(url, timeout=16)
                if r.status_code != 200:
                    warnings.append(f"Google News {domain}: HTTP {r.status_code}")
                    continue
                feed = feedparser.parse(r.content)
            except Exception as e:
                warnings.append(f"Google News {domain}: {type(e).__name__}")
                continue
            for e in feed.entries[:45]:
                when = parse_feed_time(e)
                if not when or when < start or when > now + dt.timedelta(minutes=30):
                    continue
                title = clean_text(getattr(e, "title", ""))
                desc = clean_text(getattr(e, "summary", "") or getattr(e, "description", ""))
                for suffix in [name, name.replace("|", " ")]:
                    if title.lower().endswith(" - " + suffix.lower()):
                        title = title[:-(len(suffix) + 3)].strip()
                if not title or not factual_news(title, desc):
                    continue
                text = f"{title}. {desc}"
                out.append({
                    "headline": title,
                    "source": name,
                    "date": when.isoformat(timespec="minutes").replace("+00:00", "Z"),
                    "link": clean_text(getattr(e, "link", "")),
                    "_desc": desc,
                    "_themes": themes_for(text),
                    "_entities": distinct_matches(text, ENTITY_TERMS),
                })
    seen = set(); unique = []
    for x in sorted(out, key=lambda z: z["date"], reverse=True):
        key = (norm_title(x["headline"]), x["source"])
        if key not in seen:
            seen.add(key); unique.append(x)
    return unique

def anchor_news(news: list[dict[str, Any]], ab_corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not ab_corpus:
        return []
    internals = [internalize_previous(x) for x in ab_corpus]
    theme_counts = Counter(t for x in internals for t in x.get("_themes", []))
    recurring = {t for t, c in theme_counts.items() if c >= 2}
    supported_specific = {t for t, c in theme_counts.items() if c >= 1 and t in SPECIFIC_ANCHOR_THEMES}
    anchored = []
    for n in news:
        nthemes = set(n.get("_themes", []))
        if not nthemes:
            continue
        ntok = tokens(n["headline"] + " " + n.get("_desc", ""))
        nentities = set(n.get("_entities", []))
        best = None
        for a in internals:
            athemes = set(a.get("_themes", []))
            shared = nthemes & athemes
            if not shared:
                continue
            atok = tokens(a.get("title", "") + " " + a.get("summary", ""))
            jacc = len(ntok & atok) / max(1, len(ntok | atok))
            aentities = set(distinct_matches(a.get("title", "") + " " + a.get("summary", ""), ENTITY_TERMS))
            entity_overlap = len(nentities & aentities)
            # A single broad "critical technologies" theme is too weak without another overlap.
            broad_only = shared == {"critical and emerging technologies"}
            if broad_only and entity_overlap == 0 and jacc < 0.055:
                continue
            score = 3.0 * len(shared) + 1.4 * entity_overlap + 8.0 * jacc
            if any(t in SPECIFIC_ANCHOR_THEMES for t in shared):
                score += 1.0
            if best is None or score > best[0]:
                best = (score, a, sorted(shared))
        anchor = ""; score = 0.0; shared_themes = []
        if best and best[0] >= 2.45:
            score, a, shared_themes = best
            anchor = f"{a['title']} (Strand {a['strand']})"
        else:
            common = sorted(nthemes & recurring)
            specific = sorted(nthemes & supported_specific)
            chosen = common or specific
            if chosen and (chosen[0] in SPECIFIC_ANCHOR_THEMES or len(chosen) >= 2):
                shared_themes = chosen
                score = 2.35 + 0.55 * len(chosen)
                supporting = [x["title"] for x in internals if chosen[0] in x.get("_themes", [])][:2]
                label = "Recurring A/B theme" if chosen[0] in recurring else "A/B theme"
                anchor = f"{label}: {chosen[0]}" + (f" — supported by {'; '.join(supporting)}" if supporting else "")
        if not anchor:
            continue
        low = normalized(n["headline"] + " " + n.get("_desc", ""))
        if any(w in low for w in ["stall", "delay", "cancel", "reverse", "withdraw", "fail", "collapse", "reject", "block"]):
            sig = "contradicts"
        elif any(w in low for w in ["accelerat", "expand", "surge", "increase", "boost", "fast-track", "scale up", "intensif"]):
            sig = "accelerates"
        elif any(w in low for w in ["dataset", "data show", "survey", "finds", "evidence", "shows", "rise", "fall", "measur"]):
            sig = "confirms"
        else:
            sig = "instantiates"
        desc_sents = split_sentences(n.get("_desc", ""), max_chars=4000)
        what = desc_sents[0] if desc_sents else n["headline"]
        theme = shared_themes[0] if shared_themes else "the anchored claim"
        why = f"This {sig} the anchor by providing a current empirical development in {theme}."
        item = {k: v for k, v in n.items() if not k.startswith("_")}
        item.update({"anchor": anchor, "signal_type": sig, "signal_note": what.rstrip(". ") + ". " + why, "_anchor_score": score})
        anchored.append(item)
    anchored.sort(key=lambda x: (x.get("_anchor_score", 0), x.get("date", "")), reverse=True)
    for x in anchored:
        x.pop("_anchor_score", None)
    return anchored[:MAX_C]


def scan_from_date(previous: dict[str, Any]) -> dt.date:
    if not previous.get("last_updated"):
        return DATE_FLOOR
    try:
        last = dateparser.parse(previous["last_updated"]).date()
        # Seven-day overlap catches late indexing and corrected metadata.
        return max(DATE_FLOOR, last - dt.timedelta(days=DISCOVERY_OVERLAP_DAYS))
    except Exception:
        return DATE_FLOOR


def main() -> int:
    started = time.time()
    now = dt.datetime.now(dt.timezone.utc)
    now_iso = now.isoformat(timespec="minutes").replace("+00:00", "Z")
    warnings: list[str] = []
    previous = load_previous()
    from_date = scan_from_date(previous)

    oa = collect_openalex(from_date, warnings)
    cr = collect_crossref(from_date, warnings)
    inst = collect_institutions(from_date, warnings)
    deduped = dedupe_candidates(oa + cr + inst)
    deduped.sort(key=rank_candidate)
    new_selected = deduped[:MAX_NEW_AB]

    prev_a = previous.get("strand_a", []) if isinstance(previous.get("strand_a"), list) else []
    prev_b = previous.get("strand_b", []) if isinstance(previous.get("strand_b"), list) else []
    strand_a = merge_corpus(prev_a, new_selected, "A", now_iso)
    strand_b = merge_corpus(prev_b, new_selected, "B", now_iso)

    # C anchors to the accepted cumulative A/B literature, not merely this scan's candidates.
    all_ab_map = {}
    for x in strand_a + strand_b:
        all_ab_map[identity(internalize_previous(x))] = x
    ab_corpus = list(all_ab_map.values())
    # First run gets a seven-day weak-signal backfill so C is not structurally empty
    # before the A/B anchor corpus has had time to accumulate.  Later scans use a
    # 48-hour overlap and dedupe by headline/source.
    first_run = not bool(previous.get("first_scan_complete"))
    news_lookback = FIRST_NEWS_LOOKBACK_HOURS if first_run else NEWS_LOOKBACK_HOURS
    news = collect_news(now, warnings, news_lookback)
    strand_c = anchor_news(news, ab_corpus)

    new_a_count = sum(1 for x in new_selected if x.get("strand") in {"A", "both"})
    new_b_count = sum(1 for x in new_selected if x.get("strand") in {"B", "both"})
    health = "ok"
    if not (oa or cr or inst):
        health = "degraded"
    elif len(warnings) >= 20 and len(new_selected) < 2:
        health = "degraded"

    data = {
        "last_updated": now_iso,
        "first_scan_complete": True,
        "scan_health": health,
        "scan_window": {
            "ab_date_floor": DATE_FLOOR.isoformat(),
            "ab_discovery_from_this_run": from_date.isoformat(),
            "c_window_start": (now - dt.timedelta(hours=news_lookback)).isoformat(timespec="minutes").replace("+00:00", "Z"),
            "c_window_end": now_iso,
        },
        "scan_results": {
            "new_a": new_a_count,
            "new_b": new_b_count,
            "new_ab_unique": len(new_selected),
            "c_signals": len(strand_c),
            "note_a": f"This scan found {new_a_count} qualifying Strand A item(s). The radar does not pad results." if new_a_count < 3 else "",
            "note_b": f"This scan found {new_b_count} qualifying Strand B item(s). The radar does not pad results." if new_b_count < 3 else "",
            "note_c": "This scan found 0 qualifying anchored Strand C signals. The radar does not pad results." if not strand_c else "",
        },
        "strand_a": strand_a,
        "strand_b": strand_b,
        "strand_c": strand_c,
        "stats": {
            "openalex_admitted_before_dedupe": len(oa),
            "crossref_admitted_before_dedupe": len(cr),
            "institutional_admitted_before_dedupe": len(inst),
            "unique_ab_candidates_before_scan_limit": len(deduped),
            "news_candidates_current_window": len(news),
            "news_lookback_hours": news_lookback,
            "source_warnings": len(warnings),
            "runtime_seconds": round(time.time() - started, 1),
        },
    }
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data["stats"], indent=2))
    if warnings:
        print("Source warnings (first 25):", file=sys.stderr)
        for w in warnings[:25]:
            print(" -", w, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
