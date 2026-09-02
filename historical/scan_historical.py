#!/usr/bin/env python3
"""Source-age historical scanner aligned with the live radar recall engine.

Operational isolation is strict: this script writes only historical/historical.json. It
reads historical/config.json plus the curated/manual historical evidence files. It does
not import radar.json, mutate the live matrix, weak signals, live cursors, or dispatch
the live workflow.

Historical means source age, not backward-looking content: eligible sources are older
than the live scanner’s six-month historical-discovery cutoff. Topic families rotate across the whole
eligible period, with recent historical evidence preferred when quality is comparable.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import html
import io
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from dateutil.relativedelta import relativedelta
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
HIST_DIR = ROOT / "historical"
CONFIG_PATH = HIST_DIR / "config.json"
OUT_PATH = HIST_DIR / "historical.json"
CURATED_SEED_PATH = HIST_DIR / "curated_seed_evidence.json"
MANUAL_EVIDENCE_PATH = HIST_DIR / "manual_evidence.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

DATE_FROM = dt.date.fromisoformat(CONFIG["date_from"])
MAIN_RADAR_WINDOW_MONTHS = max(1, int(CONFIG.get("main_radar_window_months", 6)))

def historical_cutoff_exclusive(today: dt.date | None = None) -> dt.date:
    """First date belonging to the live/main-radar window. Historical dates are earlier."""
    return (today or dt.date.today()) - relativedelta(months=MAIN_RADAR_WINDOW_MONTHS)

CUTOFF_EXCLUSIVE = historical_cutoff_exclusive()
DATE_TO = CUTOFF_EXCLUSIVE - dt.timedelta(days=1)
MIN_SCORE = int(CONFIG.get("minimum_admission_score", 93))
MAX_ITEMS = int(CONFIG.get("max_items", 350))
BUDGET_SECONDS = int(os.environ.get("HISTORICAL_SCAN_BUDGET_SECONDS", "1050"))
MIN_RUNTIME_SECONDS = int(os.environ.get("HISTORICAL_MIN_RUNTIME_SECONDS", str(CONFIG.get("minimum_runtime_seconds", 600))))
REQUEST_TIMEOUT = int(os.environ.get("HISTORICAL_REQUEST_TIMEOUT", "12"))
STARTED_MONO = time.monotonic()
DEADLINE = STARTED_MONO + max(120, BUDGET_SECONDS)
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()
RESCUE_MODE = os.environ.get("HISTORICAL_RESCUE_MODE", "").strip().lower() in {"1", "true", "yes", "on"}

UA = "RI-Geopolitics-Historical/2.0 (+https://vevirm.github.io/radar_articles_reports/historical/)"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": UA,
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/pdf,application/xml;q=0.9,*/*;q=0.8",
})

DIAG: collections.Counter[str] = collections.Counter()

EU_RE = re.compile(r"\b(EU|European Union|Europe|European|Horizon Europe|ERC|EIC|JRC|European Commission|European Parliament|Council of the EU)\b", re.I)
RI_RE = re.compile(
    r"\b(research|researcher|researchers|science|scientific|innovation|technology|technological|R&D|R&I|university|universities|"
    r"laborator(?:y|ies)|infrastructure|compute|computing|semiconductor|chip|chips|AI|artificial intelligence|quantum|data|"
    r"talent|skills|doctoral|patent|venture capital|scale-up|startup|industrial|manufacturing|foresight|future studies)\b", re.I)
STRATEGIC_RE = re.compile(
    r"\b(geopolit|strategic autonom|sovereign|sovereignty|dependen|reliance|security|economic security|research security|"
    r"knowledge security|competit|resilien|de-risk|derisk|China|Chinese|United States|US\b|American|Russia|export control|"
    r"sanction|dual-use|dual use|critical technolog|critical raw material|supply chain|standard|standards|regulation|"
    r"industrial policy|technology transfer|investment screening|science diplomacy|international cooperation|fragmentation|chokepoint)\b", re.I)
BAD_DOC_RE = re.compile(
    r"\b(call for proposals|call for tender|job vacancy|vacancies|event|webinar|conference registration|newsletter|press release|"
    r"speech|remarks|podcast|video|interview|award ceremony|grant results|funding opportunity|application deadline)\b", re.I)
ANALYTIC_RE = re.compile(
    r"\b(report|study|paper|analysis|assessment|review|outlook|foresight|forecast|strategy|strategic|policy brief|working paper|"
    r"research article|journal article|evidence|evaluation|impact assessment|communication|recommendation|framework)\b", re.I)
ADMIN_DOC_RE = re.compile(
    r"\b(privacy statement|privacy notice|cookie policy|terms of use|accessibility statement|legal notice|site map|sitemap|"
    r"contact us|subscription|newsletter archive|vacanc(?:y|ies)|procurement notice)\b", re.I)
SYSTEM_CAPACITY_RE = re.compile(
    r"\b(research workforce|research careers?|researcher careers?|research talent|talent attraction|talent retention|brain drain|brain gain|"
    r"researcher mobility|doctoral careers?|doctorate holders?|phd careers?|postdoc|precarity|fixed[- ]term|working conditions|"
    r"research assessment|research funding|academic freedom|research security|knowledge security|open science|research data|"
    r"research infrastructure|ai skills|artificial intelligence in science|scientific workforce|science workforce)\b", re.I)

ROW_TERMS = {
    "knowledge": re.compile(r"\b(researcher|researchers|scientist|scientists|talent|skills|university|universities|knowledge|brain drain|brain gain|mobility|research security|science diplomacy|collaboration)\b", re.I),
    "infrastructure": re.compile(r"\b(compute|computing|cloud|data centre|data center|semiconductor|chip|chips|quantum|research infrastructure|facility|facilities|critical raw material|critical mineral|energy|space|satellite|supply chain)\b", re.I),
    "conversion": re.compile(r"\b(firm|firms|company|companies|startup|start-up|scale-up|venture capital|investment|industrial|manufacturing|production|commerciali[sz]|market|patent|technology transfer)\b", re.I),
    "rules": re.compile(r"\b(regulation|regulatory|standard|standards|governance|export control|sanction|screening|law|directive|framework|funding|Horizon Europe|coordination|state aid|procurement)\b", re.I),
}
OUTCOME_TERMS = {
    "A": re.compile(r"\b(build|built|strengthen|strengthened|increase capacity|capacity building|leadership|autonomy|sovereignty|diversif|resilien|attract|retain|scale up|scaled up|common framework|coordination|investment)\b", re.I),
    "B": re.compile(r"\b(cost|trade-off|tradeoff|friction|burden|delay|restrict|screening|safeguard|protection|compliance|fragmentation|slower|barrier)\b", re.I),
    "C": re.compile(r"\b(reliance|dependen|outside|foreign|US|United States|China|Chinese|third countr|external supplier|foreign capital|foreign technology|import|access to)\b", re.I),
    "D": re.compile(r"\b(loss|lost|decline|weaken|shortage|chokepoint|cut off|restriction|brain drain|lag|behind|vulnerab|exposure|hollow|dependency risk|fragmentation|fail to scale)\b", re.I),
}

# Historical Matrix placement is evidence-driven, not a coverage target. These patterns
# require a directional mechanism, so generic actor/topic words cannot fill a cell.
A_REALIZED_RE = re.compile(r"\b(built|strengthened|increased|expanded|established|launched|implemented|adopted|secured|diversified|"
                           r"attracted|retained|scaled(?: up)?|grew|created|became operational|opened|invested)\b", re.I)
B_CONTROL_RE = re.compile(r"\b(screening|safeguard|protect(?:ion|ed)?|research security|knowledge security|export controls?|"
                          r"regulation|regulatory|compliance|localisation|localization|security checks?)\b", re.I)
B_FRICTION_RE = re.compile(r"\b(costs?|burden|delay|friction|slower|barrier|fragmentation|restrict(?:s|ed|ion)?|trade[- ]?off)\b", re.I)
C_EXTERNAL_RE = re.compile(r"\b(foreign|outside|non[- ]eu|third countr(?:y|ies)|united states|u\.?s\.?|american|china|chinese|"
                           r"foreign capital|foreign technology|external supplier|external access|import(?:s|ed)?)\b", re.I)
C_RELIANCE_RE = re.compile(r"\b(rely|relied|relies|reliance|depend(?:s|ed|ence|ency|ent)?|access to|using|through|supplied by|financed by|hosted by)\b", re.I)
D_LOSS_RE = re.compile(r"\b(brain drain|talent outflow|researcher outflow|lost|loss|declin(?:e|ed|ing)|weaken(?:ed|ing)?|shortage|"
                       r"chokepoint|cut off|blocked|lag(?:s|ged|ging)?|behind|vulnerab(?:le|ility)|exposure|hollow(?:ing)?|fail(?:ed|s)? to scale)\b", re.I)


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()


def phrase_present(normalized_text: str, phrase: str) -> bool:
    """Token/phrase match; avoids substring bugs such as ``ai`` matching ``brain``."""
    p = norm(phrase)
    return bool(p and f" {p} " in f" {normalized_text} ")


def log(msg: str) -> None:
    print(f"[historical +{time.monotonic()-STARTED_MONO:6.1f}s] {msg}", flush=True)


def budget_ok(reserve: int = 30) -> bool:
    return time.monotonic() < DEADLINE - reserve


def elapsed_seconds() -> float:
    return time.monotonic() - STARTED_MONO


def minimum_runtime_remaining() -> float:
    return max(0.0, float(MIN_RUNTIME_SECONDS) - elapsed_seconds())


def wait_until_minimum_runtime() -> None:
    """Honor the minimum historical scan window after useful rotations are exhausted.

    This is only a final floor. Normal behavior is to spend the time on additional
    topic/source/deeper-result rotations first. The sleep path is used only when the
    configured search space completes unusually quickly.
    """
    remaining = minimum_runtime_remaining()
    if remaining <= 0:
        return
    safe_remaining = max(0.0, DEADLINE - time.monotonic() - 45.0)
    wait_for = min(remaining, safe_remaining)
    if wait_for <= 0:
        return
    log(f"Useful configured rotations finished early; holding the historical scan open for {wait_for:.0f}s to satisfy the {MIN_RUNTIME_SECONDS}s minimum window")
    end = time.monotonic() + wait_for
    while time.monotonic() < end:
        time.sleep(min(5.0, max(0.0, end - time.monotonic())))


def parse_date(value: Any) -> dt.date | None:
    if not value:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dateparser.parse(str(value), fuzzy=False).date()
    except Exception:
        m = re.search(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", str(value))
        if m:
            try:
                return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return None
    return None


def domain_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def source_for(domain: str = "", venue: str = "", publisher: str = "") -> dict[str, Any] | None:
    d = clean(domain).lower().removeprefix("www.")
    for src in CONFIG.get("elite_sources", []):
        sd = clean(src.get("domain")).lower().removeprefix("www.")
        if d and sd and (d == sd or d.endswith("." + sd)):
            return dict(src)
    text = norm(f"{venue} {publisher}")
    aliases = {
        "european commission": "commission.europa.eu",
        "joint research centre": "joint-research-centre.ec.europa.eu",
        "joint research center": "joint-research-centre.ec.europa.eu",
        "european parliament": "europarl.europa.eu",
        "organisation for economic co operation and development": "oecd.org",
        "organization for economic co operation and development": "oecd.org",
        "oecd": "oecd.org",
        "bruegel": "bruegel.org",
        "centre for european policy studies": "ceps.eu",
        "mercator institute for china studies": "merics.org",
        "european university association": "eua.eu",
        "science europe": "scienceeurope.org",
        "cesaer": "cesaer.org",
        "eurodoc": "eurodoc.net",
        "cedefop": "cedefop.europa.eu",
        "european centre for the development of vocational training": "cedefop.europa.eu",
        "research executive agency": "rea.ec.europa.eu",
    }
    for alias, target in aliases.items():
        if alias in text:
            for src in CONFIG.get("elite_sources", []):
                if src.get("domain") == target:
                    return dict(src)
    for journal in CONFIG.get("top_journals", []):
        if norm(journal) and norm(journal) in text:
            return {"name": journal, "domain": "", "kind": "top_journal", "authority": 56}
    return None


def year_bonus(d: dt.date) -> int:
    latest = int(CONFIG.get("year_preference_latest_bonus", 12))
    decay = max(0, int(CONFIG.get("year_preference_decay_per_year", 2)))
    years_back = max(0, DATE_TO.year - d.year)
    return max(0, latest - years_back * decay)


def topic_matches(text: str) -> list[str]:
    n = norm(text)
    hits: list[str] = []
    for topic in CONFIG.get("topics", []):
        phrases = [clean(x) for x in topic.get("url_terms", [])]
        if any(phrase_present(n, p) for p in phrases):
            hits.append(str(topic.get("id")))
    return hits[:6]


def topic_label(topic_id: str) -> str:
    for t in CONFIG.get("topics", []):
        if t.get("id") == topic_id:
            return str(t.get("label"))
    return topic_id


def _matrix_contexts(text: str) -> list[str]:
    raw = clean(re.sub(r"<[^>]+>", " ", text or ""))
    sentences = [clean(x) for x in re.split(r"(?<=[.!?])\s+|\n+", raw) if clean(x)]
    contexts = sentences[:80]
    contexts.extend(clean(f"{sentences[i]} {sentences[i+1]}") for i in range(min(len(sentences)-1, 79)))
    return contexts


def _outcome_score(context: str, row: str) -> dict[str, int]:
    eu = bool(EU_RE.search(context))
    scores = {c: 0 for c in "ABCD"}
    if eu and A_REALIZED_RE.search(context):
        scores["A"] = 4 + len(A_REALIZED_RE.findall(context))
    if eu and B_CONTROL_RE.search(context) and B_FRICTION_RE.search(context):
        scores["B"] = 7 + len(B_FRICTION_RE.findall(context))
    # Outside actors alone are not Column C. The source must describe reliance/access.
    if eu and C_EXTERNAL_RE.search(context) and C_RELIANCE_RE.search(context):
        scores["C"] = 6 + len(C_RELIANCE_RE.findall(context))
    if eu and D_LOSS_RE.search(context):
        scores["D"] = 7 + len(D_LOSS_RE.findall(context))
    # Talent outflow is intrinsically a people/knowledge loss mechanism.
    if eu and row == "knowledge" and re.search(r"\b(brain drain|talent outflow|researcher outflow)\b", context, re.I):
        scores["D"] = max(scores["D"], 10)
    return scores


def matrix_classification(text: str) -> tuple[str, str, str]:
    best: tuple[int, str, str, str] | None = None
    for context in _matrix_contexts(text):
        row_scores = {k: len(v.findall(context)) for k, v in ROW_TERMS.items()}
        for row, rscore in row_scores.items():
            if rscore <= 0:
                continue
            # Generic research language is weak evidence; prefer concrete mechanisms.
            if row == "infrastructure" and not re.search(r"\b(compute|cloud|data cent(?:er|re)|semiconductor|chip|quantum|research infrastructure|facility|critical raw material|critical mineral|energy|supply chain)\b", context, re.I):
                continue
            for outcome, oscore in _outcome_score(context, row).items():
                if oscore <= 0:
                    continue
                score = rscore * 2 + oscore
                candidate = (score, row, outcome, context)
                if best is None or candidate[0] > best[0]:
                    best = candidate
    if best is None:
        return "", "", ""
    _, row, outcome, context = best
    basis = first_sentence(context, 360)
    return row, outcome, f"Source evidence: {basis}"


def first_sentence(text: str, limit: int = 330) -> str:
    t = clean(re.sub(r"<[^>]+>", " ", text or ""))
    if not t:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", t)
    s = parts[0].strip()
    if len(s) < 80 and len(parts) > 1:
        s = f"{s} {parts[1]}".strip()
    return s[:limit].rstrip(" ,;:-") + ("…" if len(s) > limit else "")


def why_it_matters(row: str, outcome: str) -> str:
    row_phrase = {"knowledge":"Europe's research workforce, skills and know-how","infrastructure":"the tools, facilities and strategic inputs European research depends on","conversion":"Europe's ability to turn research into firms, production and scale","rules":"the rules, funding and coordination that shape European research and innovation"}.get(row, "Europe's research and innovation position")
    outcome_phrase = {"A":"It is useful history for judging whether later policy really built durable European strength.","B":"It is useful history for judging when greater control also created costs, delay or friction.","C":"It is useful history for judging where European gains still depended on outside capital, technology, markets or access.","D":"It is useful history for judging whether the same weakness or exposure is still present now."}.get(outcome, "It is useful history for judging which earlier pressures still matter now.")
    return f"This bears on {row_phrase}. {outcome_phrase}"


def stable_id(title: str, url: str) -> str:
    basis = norm(url) or norm(title)
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def _diag(reason: str, n: int = 1) -> None:
    DIAG[reason] += n


def admit(raw: dict[str, Any], lane: str = "unknown") -> dict[str, Any] | None:
    _diag("raw_records")
    _diag(f"raw_{lane}")
    title = clean(raw.get("title"))
    abstract = clean(raw.get("abstract") or raw.get("summary") or raw.get("body"))
    url = clean(raw.get("url") or raw.get("doi"))
    date = parse_date(raw.get("date"))
    if not title:
        _diag("reject_no_title"); return None
    if ADMIN_DOC_RE.search(title):
        _diag("reject_administrative_document"); return None
    if date is None:
        _diag("reject_no_date"); return None
    if not (DATE_FROM <= date <= DATE_TO):
        _diag("reject_outside_window"); return None
    profile = source_for(domain_of(url), clean(raw.get("venue")), clean(raw.get("publisher")))
    if not profile:
        _diag("reject_source_not_elite"); return None
    _diag("source_eligible")
    text = clean(f"{title}. {abstract}")
    if abstract and len(abstract.split()) >= 20:
        _diag("enough_text")
    else:
        _diag("insufficient_text")
    if BAD_DOC_RE.search(title) and not ANALYTIC_RE.search(text):
        _diag("reject_document_exclusion"); return None
    official = profile.get("kind") == "official_eu"
    eu_direct = bool(EU_RE.search(text))
    if not official and not eu_direct:
        _diag("reject_no_direct_eu"); return None
    _diag("eu_scope")
    if not RI_RE.search(text):
        _diag("reject_no_ri"); return None
    _diag("ri_scope")
    if not (STRATEGIC_RE.search(text) or SYSTEM_CAPACITY_RE.search(text)):
        _diag("reject_no_strategic_context"); return None
    _diag("strategic_scope")
    if len(text.split()) < 28 and not ANALYTIC_RE.search(text):
        _diag("defer_insufficient_text"); return None
    topics = topic_matches(text)
    if not topics:
        _diag("reject_no_topic_match"); return None
    _diag("topic_match")
    authority = int(profile.get("authority", 0))
    score = authority + (17 if eu_direct else 14) + 10 + 10 + (4 if len(text.split()) >= 80 or ANALYTIC_RE.search(text) else 2) + year_bonus(date)
    score = min(100, score)
    if score < MIN_SCORE:
        _diag("reject_below_merit"); return None
    _diag("gate_passed")
    row, outcome, basis = matrix_classification(text)
    return {
        "id": stable_id(title, url), "title": title, "date": date.isoformat(), "year": date.year,
        "url": url, "authors": clean(raw.get("authors")), "source": clean(profile.get("name")),
        "source_kind": clean(profile.get("kind")), "venue": clean(raw.get("venue")), "publisher": clean(raw.get("publisher")),
        "source_merit_score": score, "source_merit_label": "Historical top tier",
        "topics": topics, "topic_labels": [topic_label(t) for t in topics],
        "reader_point": first_sentence(abstract) or title, "why_it_matters": why_it_matters(row, outcome),
        "matrix_dimension": row, "matrix_outcome": outcome, "matrix_basis": basis,
        "discovery": clean(raw.get("discovery")),
    }


def openalex_abstract(inv: dict[str, list[int]] | None) -> str:
    if not inv: return ""
    positions: list[tuple[int, str]] = []
    for word, ps in inv.items():
        for p in ps or []:
            positions.append((int(p), word))
    return clean(" ".join(w for _, w in sorted(positions)))


def crossref_date(item: dict[str, Any]) -> str:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        part = item.get(key) or {}; dp = part.get("date-parts") if isinstance(part, dict) else None
        if dp and dp[0]:
            bits = list(dp[0]) + [1, 1]
            try: return dt.date(int(bits[0]), int(bits[1]), int(bits[2])).isoformat()
            except Exception: pass
    return ""


def metadata_rescue_priority(title: str, query: str, source: dict[str, Any] | None, published: dt.date | None) -> int:
    text = clean(f"{title} {query}")
    score = 0
    if EU_RE.search(title): score += 8
    if RI_RE.search(title): score += 6
    if STRATEGIC_RE.search(title): score += 6
    if ANALYTIC_RE.search(title): score += 3
    if source:
        score += 5 if source.get("kind") == "official_eu" else 3
    if published: score += year_bonus(published) // 2
    return score


def fetch_text(url: str, timeout: int) -> str:
    if not url or not budget_ok(45): return ""
    try:
        r = SESSION.get(url, timeout=timeout, allow_redirects=True)
        if not r.ok: return ""
    except Exception:
        return ""
    ctype = (r.headers.get("Content-Type") or "").lower()
    if "pdf" in ctype or r.url.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(r.content))
            return clean(" ".join((p.extract_text() or "") for p in reader.pages[:10]))[:14000]
        except Exception:
            return ""
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        for bad in soup(["script", "style", "nav", "footer", "form", "noscript"]): bad.decompose()
        desc_tag = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", property="og:description")
        desc = clean(desc_tag.get("content") if desc_tag else "")
        return clean(f"{desc} {soup.get_text(' ', strip=True)}")[:14000]
    except Exception:
        return ""


def collect_openalex(queries: list[str], warnings: list[str], lane: str = "openalex", result_page: int = 1) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    scan_cap = int(CONFIG.get("openalex_missing_abstract_enrichment_per_scan", 24))
    per_query = int(CONFIG.get("openalex_missing_abstract_enrichment_per_query", 3))
    min_priority = int(CONFIG.get("metadata_rescue_priority_min_score", 10))
    used_rescue = 0
    for q in queries:
        if not budget_ok(90): break
        params = {"search":q,"filter":f"from_publication_date:{DATE_FROM.isoformat()},to_publication_date:{DATE_TO.isoformat()},language:en","per-page":int(CONFIG.get("openalex_per_query",50)),"page":max(1,int(result_page)),"sort":"relevance_score:desc"}
        if OPENALEX_API_KEY: params["api_key"] = OPENALEX_API_KEY
        try:
            r = SESSION.get("https://api.openalex.org/works", params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code == 429:
                warnings.append("OpenAlex rate limited (429)"); _diag("openalex_429"); time.sleep(1.2); continue
            r.raise_for_status(); works = r.json().get("results", [])
        except Exception as e:
            warnings.append(f"OpenAlex {type(e).__name__}: {e}"); continue
        _diag("openalex_api_results", len(works))
        raw_list: list[dict[str, Any]] = []
        rescue_queue: list[tuple[int, dict[str, Any]]] = []
        for w in works:
            loc=w.get("primary_location") or {}; src=loc.get("source") or {}; doi=clean(w.get("doi")); url=clean(loc.get("landing_page_url") or doi or w.get("id"))
            authors="; ".join(clean((a.get("author") or {}).get("display_name")) for a in w.get("authorships", [])[:12])
            raw={"title":w.get("title"),"abstract":openalex_abstract(w.get("abstract_inverted_index")),"date":w.get("publication_date"),"url":url,"doi":doi,"authors":authors,"venue":src.get("display_name"),"publisher":src.get("host_organization_name"),"discovery":f"OpenAlex · {q}"}
            raw_list.append(raw)
            if not raw["abstract"]:
                prof=source_for(domain_of(url), clean(raw.get("venue")), clean(raw.get("publisher")))
                p=metadata_rescue_priority(clean(raw.get("title")), q, prof, parse_date(raw.get("date")))
                if p >= min_priority: rescue_queue.append((p, raw))
        rescue_queue.sort(key=lambda x:x[0], reverse=True); _diag("openalex_metadata_rescue_queued",len(rescue_queue))
        for _, raw in rescue_queue[:max(0,min(per_query,scan_cap-used_rescue))]:
            text=fetch_text(clean(raw.get("url")), int(CONFIG.get("missing_abstract_enrichment_timeout_seconds",9)))
            used_rescue += 1; _diag("openalex_metadata_rescue_attempted")
            if text: raw["abstract"]=text; _diag("openalex_metadata_rescue_recovered")
        for raw in raw_list:
            item=admit(raw,lane)
            if item: out.append(item)
        log(f"OpenAlex: {q[:68]} -> {len(out)} admitted cumulative")
    return out


def collect_crossref(queries: list[str], warnings: list[str], lane: str = "crossref", result_page: int = 1) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    scan_cap=int(CONFIG.get("crossref_missing_abstract_enrichment_per_scan",36)); per_task=int(CONFIG.get("crossref_missing_abstract_enrichment_per_query",3)); min_priority=int(CONFIG.get("metadata_rescue_priority_min_score",10)); used_rescue=0
    query_key = "query.title" if clean(CONFIG.get("crossref_relevance_query_mode","title")).lower()=="title" else "query.bibliographic"
    for q in queries:
        if not budget_ok(90): break
        rows=int(CONFIG.get("crossref_per_query",50)); params={query_key:q,"filter":f"from-pub-date:{DATE_FROM.isoformat()},until-pub-date:{DATE_TO.isoformat()}","rows":rows,"offset":max(0,(max(1,int(result_page))-1)*rows),"sort":"relevance","order":"desc","select":"DOI,title,abstract,published-print,published-online,published,issued,created,author,container-title,publisher,URL,type"}
        try:
            r=SESSION.get("https://api.crossref.org/works",params=params,timeout=REQUEST_TIMEOUT)
            if r.status_code==429: warnings.append("Crossref rate limited (429)"); _diag("crossref_429"); continue
            r.raise_for_status(); works=((r.json().get("message") or {}).get("items") or [])
        except Exception as e:
            warnings.append(f"Crossref {type(e).__name__}: {e}"); continue
        _diag("crossref_api_results",len(works))
        raw_list=[]; rescue_queue=[]
        for w in works:
            title=clean(" ".join(w.get("title") or [])); venue=clean(" ".join(w.get("container-title") or [])); authors="; ".join(clean(f"{a.get('given','')} {a.get('family','')}") for a in (w.get("author") or [])[:12]); doi=clean(w.get("DOI")); url=clean(w.get("URL") or ("https://doi.org/"+doi if doi else ""))
            raw={"title":title,"abstract":clean(re.sub(r"<[^>]+>"," ",w.get("abstract") or "")),"date":crossref_date(w),"url":url,"doi":doi,"authors":authors,"venue":venue,"publisher":clean(w.get("publisher")),"discovery":f"Crossref · {q}"}
            raw_list.append(raw)
            if not raw["abstract"]:
                prof=source_for(domain_of(url),venue,clean(raw.get("publisher"))); p=metadata_rescue_priority(title,q,prof,parse_date(raw.get("date")))
                if p>=min_priority: rescue_queue.append((p,raw))
        rescue_queue.sort(key=lambda x:x[0],reverse=True); _diag("crossref_metadata_rescue_queued",len(rescue_queue))
        for _,raw in rescue_queue[:max(0,min(per_task,scan_cap-used_rescue))]:
            text=fetch_text(clean(raw.get("url")),int(CONFIG.get("missing_abstract_enrichment_timeout_seconds",9))); used_rescue+=1; _diag("crossref_metadata_rescue_attempted")
            if text: raw["abstract"]=text; _diag("crossref_metadata_rescue_recovered")
        for raw in raw_list:
            item=admit(raw,lane)
            if item: out.append(item)
        log(f"Crossref: {q[:68]} -> {len(out)} admitted cumulative")
    return out


def localname(tag: str) -> str: return tag.split("}")[-1].lower()


def xml_bytes(resp: requests.Response) -> bytes:
    data=resp.content
    if resp.url.endswith(".gz") or "gzip" in (resp.headers.get("Content-Type") or "").lower():
        try: data=gzip.decompress(data)
        except Exception: pass
    return data


def topic_score(text: str, active_topics: list[dict[str, Any]]) -> int:
    n=norm(text); score=0
    for t in active_topics:
        for term in t.get("url_terms",[]):
            if phrase_present(n, clean(term)): score += 3
    if re.search(r"\b(report|publication|study|analysis|paper|research|foresight|policy|strategy|brief|outlook)\b",n,re.I): score += 2
    return score


def source_adapter_candidates(src: dict[str, Any], active_topics: list[dict[str, Any]], warnings: list[str]) -> list[str]:
    domain=clean(src.get("domain")); profiles=CONFIG.get("source_adapters",{}); hubs=profiles.get(domain,[]) if isinstance(profiles,dict) else []
    if not hubs: return []
    max_hubs=int(CONFIG.get("source_adapter_max_hub_fetches",6)); max_pages=int(CONFIG.get("source_adapter_pages_per_source",20)); scored:dict[str,int]={}
    for path in hubs[:max_hubs]:
        if not budget_ok(90): break
        url=path if str(path).startswith("http") else f"https://{domain}{path}"
        try:
            r=SESSION.get(url,timeout=REQUEST_TIMEOUT,allow_redirects=True)
            if not r.ok: continue
            soup=BeautifulSoup(r.text,"html.parser")
        except Exception: continue
        for a in soup.find_all("a",href=True):
            href=urljoin(r.url,clean(a.get("href"))); d=domain_of(href)
            if not d or not (d==domain or d.endswith("."+domain) or domain.endswith("."+d)): continue
            label=clean(a.get_text(" ",strip=True)); s=topic_score(f"{urlparse(href).path} {label}",active_topics)
            if s>0: scored[href]=max(scored.get(href,0),s)
    if scored: _diag("institution_adapter_jobs",len(scored))
    else: warnings.append(f"Source adapter found no topic links: {domain}")
    return [u for u,_ in sorted(scored.items(),key=lambda kv:(-kv[1],kv[0]))[:max_pages]]


def sitemap_candidates(domain: str, active_topics: list[dict[str, Any]], warnings: list[str]) -> list[str]:
    roots=[f"https://{domain}/sitemap.xml",f"https://{domain}/sitemap_index.xml"]; queue=list(roots); seen_maps=set(); urls=[]
    while queue and len(seen_maps)<12 and budget_ok(90):
        sm=queue.pop(0)
        if sm in seen_maps: continue
        seen_maps.add(sm)
        try:
            r=SESSION.get(sm,timeout=REQUEST_TIMEOUT); 
            if not r.ok: continue
            root=ET.fromstring(xml_bytes(r))
        except Exception: continue
        if localname(root.tag)=="sitemapindex":
            for node in root.iter():
                if localname(node.tag)=="loc":
                    loc=clean(node.text)
                    if loc and loc not in seen_maps: queue.append(loc)
            continue
        for node in root.iter():
            if localname(node.tag)!="url": continue
            loc=""
            for ch in node:
                if localname(ch.tag)=="loc": loc=clean(ch.text)
            if not loc: continue
            s=topic_score(urlparse(loc).path,active_topics)
            if s>0: urls.append((s,loc))
    if not urls: warnings.append(f"No usable topic sitemap results: {domain}")
    return [u for _,u in sorted(urls,key=lambda x:(-x[0],x[1]))]


def page_date(soup: BeautifulSoup, text: str) -> dt.date | None:
    candidates=[]
    for tag in soup.find_all("meta"):
        key=clean(tag.get("property") or tag.get("name") or tag.get("itemprop")).lower()
        if key in {"article:published_time","date","datepublished","publication_date","dc.date","dcterms.date"}: candidates.append(clean(tag.get("content")))
    for t in soup.find_all("time")[:5]: candidates.append(clean(t.get("datetime") or t.get_text(" ",strip=True)))
    for c in candidates:
        d=parse_date(c)
        if d and DATE_FROM<=d<=DATE_TO: return d
    m=re.search(r"\b(202[3-5])[-/.](\d{1,2})[-/.](\d{1,2})\b",text[:7000]); return parse_date(m.group(0)) if m else None


def fetch_page_candidate(url: str, src: dict[str, Any], warnings: list[str], lane: str="direct") -> dict[str, Any] | None:
    if not budget_ok(50): return None
    try:
        r=SESSION.get(url,timeout=REQUEST_TIMEOUT,allow_redirects=True)
        if not r.ok: _diag("direct_fetch_failure"); return None
    except Exception: _diag("direct_fetch_failure"); return None
    ctype=(r.headers.get("Content-Type") or "").lower()
    if "pdf" in ctype or r.url.lower().endswith(".pdf"):
        try:
            reader=PdfReader(io.BytesIO(r.content)); body=clean(" ".join((p.extract_text() or "") for p in reader.pages[:10])); title=clean(reader.metadata.title if reader.metadata else "") or clean(urlparse(r.url).path.rsplit("/",1)[-1].replace("-"," ")); d=parse_date(reader.metadata.creation_date if reader.metadata else None)
        except Exception: return None
        if not d:
            m=re.search(r"\b(202[3-5])[-/.](\d{1,2})[-/.](\d{1,2})\b",body[:6000]); d=parse_date(m.group(0)) if m else None
        return admit({"title":title,"abstract":body[:10000],"date":d,"url":r.url,"venue":src.get("name"),"publisher":src.get("name"),"discovery":f"direct source · {src.get('name')}"},lane)
    try: soup=BeautifulSoup(r.text,"html.parser")
    except Exception: return None
    title_tag=soup.find("meta",property="og:title"); title=clean(title_tag.get("content") if title_tag else "")
    if not title and soup.title: title=clean(soup.title.get_text(" ",strip=True))
    desc_tag=soup.find("meta",attrs={"name":"description"}) or soup.find("meta",property="og:description"); desc=clean(desc_tag.get("content") if desc_tag else "")
    for bad in soup(["script","style","nav","footer","form","noscript"]): bad.decompose()
    content_root=soup.find("article") or soup.find("main") or soup
    body=clean(content_root.get_text(" ",strip=True))[:14000]; d=page_date(soup,body)
    return admit({"title":title,"abstract":clean(f"{desc} {body[:9000]}"),"date":d,"url":r.url,"venue":src.get("name"),"publisher":src.get("name"),"discovery":f"direct source · {src.get('name')}"},lane)


def collect_direct_sources(active_sources: list[dict[str, Any]], active_topics: list[dict[str, Any]], warnings: list[str]) -> list[dict[str, Any]]:
    out=[]; limit=int(CONFIG.get("direct_pages_per_source",16))
    for src in active_sources:
        if not budget_ok(120): break
        domain=clean(src.get("domain"));
        if not domain: continue
        adapter=source_adapter_candidates(src,active_topics,warnings); sitemap=sitemap_candidates(domain,active_topics,warnings)
        urls=[]; seen=set()
        for u in adapter+sitemap:
            k=u.lower().rstrip("/")
            if k not in seen: urls.append(u); seen.add(k)
        admitted=0
        for url in urls[:limit]:
            if not budget_ok(55): break
            item=fetch_page_candidate(url,src,warnings,"direct")
            if item: out.append(item); admitted+=1
        log(f"Direct source: {src.get('name')} -> {admitted} admitted")
    return out


def rotating(items: list[Any], cursor: int, count: int) -> tuple[list[Any], int]:
    if not items or count<=0: return [],0
    start=cursor%len(items); take=min(count,len(items)); return [items[(start+i)%len(items)] for i in range(take)],(start+take)%len(items)


def curated_seed_items() -> list[dict[str, Any]]:
    if not CURATED_SEED_PATH.exists():
        return []
    try:
        payload=json.loads(CURATED_SEED_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows=payload.get("items",[]) if isinstance(payload,dict) else []
    return [x for x in rows if isinstance(x,dict) and clean(x.get("title"))]


def manual_evidence_items() -> list[dict[str, Any]]:
    """Load manually reviewed geopolitical signals that must survive automated scans."""
    if not MANUAL_EVIDENCE_PATH.exists():
        return []
    try:
        payload=json.loads(MANUAL_EVIDENCE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows=payload.get("items",[]) if isinstance(payload,dict) else []
    out=[]
    for raw in rows:
        if not isinstance(raw,dict) or not clean(raw.get("title")):
            continue
        item=dict(raw)
        d=parse_date(item.get("date"))
        if not d or not (DATE_FROM <= d <= DATE_TO):
            continue
        item["manual_curated"]=True
        item["year"]=d.year
        out.append(item)
    return out


def refresh_existing_item(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Conservatively migrate persisted records produced by older, looser gates.

    Dubious records disappear from the static archive and can only return if a later
    scan rediscovers them with enough source text to pass the current gates.
    """
    item=dict(raw)
    if item.get("manual_curated"):
        return None
    title=clean(item.get("title")); text=clean(f"{title}. {item.get('reader_point','')}")
    if not title or ADMIN_DOC_RE.search(title):
        return None
    if not RI_RE.search(text):
        return None
    official=clean(item.get("source_kind"))=="official_eu"
    if not official and not EU_RE.search(text):
        return None
    if not (STRATEGIC_RE.search(text) or SYSTEM_CAPACITY_RE.search(text)):
        return None
    topics=topic_matches(text)
    if not topics:
        return None
    row,outcome,basis=matrix_classification(text)
    item["topics"]=topics
    item["topic_labels"]=[topic_label(t) for t in topics]
    item["matrix_dimension"],item["matrix_outcome"],item["matrix_basis"]=row,outcome,basis
    item["why_it_matters"]=why_it_matters(row,outcome)
    return item


def dedupe(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    best={}; title_best={}
    for item in items:
        if not isinstance(item,dict): continue
        key=clean(item.get("id")) or stable_id(clean(item.get("title")),clean(item.get("url"))); tkey=norm(item.get("title")); target=title_best.get(tkey,key) if tkey else key; old=best.get(target)
        if old is None or int(item.get("source_merit_score",0))>int(old.get("source_merit_score",0)):
            best[target]=item
            if tkey: title_best[tkey]=target
    return list(best.values())


def query_plan_for(topics: list[dict[str, Any]]) -> list[str]:
    qpt=int(CONFIG.get("queries_per_topic",2)); q=[]
    for t in topics: q.extend(list(t.get("queries",[]))[:qpt])
    return list(dict.fromkeys(clean(x) for x in q if clean(x)))


def rejection_funnel(new_items: int, unique_gate_candidates: int) -> dict[str, Any]:
    return {
        "raw_records": int(DIAG["raw_records"]),
        "source_eligible": int(DIAG["source_eligible"]),
        "enough_text": int(DIAG["enough_text"]),
        "eu_scope": int(DIAG["eu_scope"]),
        "ri_scope": int(DIAG["ri_scope"]),
        "strategic_scope": int(DIAG["strategic_scope"]),
        "topic_match": int(DIAG["topic_match"]),
        "gate_passed_before_dedupe": int(DIAG["gate_passed"]),
        "unique_gate_candidates": int(unique_gate_candidates),
        "genuinely_new_items": int(new_items),
        "metadata_text_rescue": {
            "queued": int(DIAG["openalex_metadata_rescue_queued"]+DIAG["crossref_metadata_rescue_queued"]),
            "attempted": int(DIAG["openalex_metadata_rescue_attempted"]+DIAG["crossref_metadata_rescue_attempted"]),
            "text_recovered": int(DIAG["openalex_metadata_rescue_recovered"]+DIAG["crossref_metadata_rescue_recovered"]),
        },
        "source_adapter_jobs": int(DIAG["institution_adapter_jobs"]),
        "rejections": {k:int(v) for k,v in sorted(DIAG.items()) if k.startswith("reject_") or k.startswith("defer_") or k=="insufficient_text"},
    }


def run_rotation(active_topics: list[dict[str, Any]], active_sources: list[dict[str, Any]], warnings: list[str], suffix: str="normal", result_page: int = 1, extra_queries: list[str] | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    queries=list(dict.fromkeys(query_plan_for(active_topics) + [clean(x) for x in (extra_queries or []) if clean(x)])); candidates=[]
    candidates.extend(collect_openalex(queries,warnings,f"openalex_{suffix}",result_page=result_page))
    candidates.extend(collect_crossref(queries,warnings,f"crossref_{suffix}",result_page=result_page))
    candidates.extend(collect_direct_sources(active_sources,active_topics,warnings))
    return candidates,queries


def main() -> int:
    try: previous=json.loads(OUT_PATH.read_text(encoding="utf-8")) if OUT_PATH.exists() else {}
    except Exception: previous={}
    state=previous.get("scan_state") if isinstance(previous.get("scan_state"),dict) else {}
    topics=list(CONFIG.get("topics",[])); sources=list(CONFIG.get("elite_sources",[])); seeds=curated_seed_items(); manual_items=manual_evidence_items()
    topic_cursor=int(state.get("topic_cursor",0)); source_cursor=int(state.get("source_cursor",0)); seed_cursor=int(state.get("seed_cursor",0))
    active_topics,next_topic=rotating(topics,topic_cursor,int(CONFIG.get("topics_per_scan",4)))
    active_sources,next_source=rotating(sources,source_cursor,int(CONFIG.get("sources_per_scan",8)))
    active_seeds,next_seed=rotating(seeds,seed_cursor,int(CONFIG.get("curated_seed_queries_per_scan",12)))
    seed_queries=[clean(x.get("title")) for x in active_seeds if clean(x.get("title"))]
    warnings=[]; log(f"Historical scan starts: {DATE_FROM.isoformat()} through {DATE_TO.isoformat()} (sources before {CUTOFF_EXCLUSIVE.isoformat()}); content may be future-facing")
    log("Topics: "+" | ".join(str(t.get("label")) for t in active_topics))
    if seed_queries: log(f"Curated workbook backfill: {len(seed_queries)} title seed(s)")
    candidates,queries=run_rotation(active_topics,active_sources,warnings,"normal",extra_queries=seed_queries)
    old_items=[]
    previous_ids={clean(x.get("id")) for x in previous.get("items",[]) if isinstance(x,dict)}
    for raw in previous.get("items",[]):
        if isinstance(raw,dict) and (item:=refresh_existing_item(raw)) is not None:
            old_items.append(item)
    old_ids={clean(x.get("id")) for x in old_items}
    unique_initial=dedupe(candidates); initial_new=sum(1 for x in unique_initial if clean(x.get("id")) not in old_ids)
    target_new=max(1,int(CONFIG.get("target_new_items_per_scan",8) or 8))
    low_threshold=max(int(CONFIG.get("low_yield_trigger_max_new_items",3)), target_new-1); low_triggered=initial_new<=low_threshold
    rescue_topics=[]; rescue_sources=[]; rescue_queries=[]; rescue_candidates=[]
    if low_triggered and budget_ok(220):
        rescue_topics,rescue_next_topic=rotating(topics,next_topic,int(CONFIG.get("low_yield_fresh_topics",4)))
        rescue_sources,rescue_next_source=rotating(sources,next_source,int(CONFIG.get("low_yield_fresh_sources",8)))
        log(f"Low yield ({initial_new}); forcing fresh historical topic/source rotation inside this run")
        rescue_candidates,rescue_queries=run_rotation(rescue_topics,rescue_sources,warnings,"fresh",result_page=1)
        candidates.extend(rescue_candidates); next_topic=rescue_next_topic; next_source=rescue_next_source

    # Target-driven continuation: keep searching while the strict-gate yield is below the
    # configured target.  The target controls search depth only; it never bypasses source,
    # text, EU, R&I, strategic-context or topic gates.
    continuation_waves=[]
    topics_per_wave=max(1,int(CONFIG.get("minimum_runtime_topics_per_wave",CONFIG.get("topics_per_scan",4))))
    sources_per_wave=max(1,int(CONFIG.get("minimum_runtime_sources_per_wave",CONFIG.get("sources_per_scan",8))))
    max_extra=max(0,int(CONFIG.get("minimum_runtime_max_extra_waves",12)))
    blocks_per_topic_sweep=max(1,(len(topics)+topics_per_wave-1)//topics_per_wave)
    blocks_already=1 + (1 if rescue_topics else 0)
    current_unique=dedupe(candidates)
    current_new=sum(1 for x in current_unique if clean(x.get("id")) not in old_ids)
    while current_new<target_new and budget_ok(150) and len(continuation_waves)<max_extra:
        wave_no=len(continuation_waves)+1
        wave_topics,wave_next_topic=rotating(topics,next_topic,topics_per_wave)
        wave_sources,wave_next_source=rotating(sources,next_source,sources_per_wave)
        result_page=1 + (blocks_already // blocks_per_topic_sweep)
        log(f"Minimum-runtime continuation wave {wave_no}: page {result_page}; topics: "+" | ".join(str(t.get("label")) for t in wave_topics))
        wave_candidates,wave_queries=run_rotation(wave_topics,wave_sources,warnings,f"minimum_runtime_{wave_no}",result_page=result_page)
        candidates.extend(wave_candidates)
        continuation_waves.append({"wave":wave_no,"result_page":result_page,"topics":[str(t.get("label")) for t in wave_topics],"sources":[str(s.get("name")) for s in wave_sources],"queries":wave_queries,"candidates":len(wave_candidates)})
        next_topic=wave_next_topic; next_source=wave_next_source; blocks_already+=1
        current_unique=dedupe(candidates)
        current_new=sum(1 for x in current_unique if clean(x.get("id")) not in old_ids)

    wait_until_minimum_runtime()
    unique_gate=dedupe(candidates); merged=dedupe(manual_items+old_items+unique_gate)
    merged=[x for x in merged if (d:=parse_date(x.get("date"))) and DATE_FROM<=d<=DATE_TO]
    merged.sort(key=lambda x:(int(x.get("year",0)),x.get("date",""),clean(x.get("title"))),reverse=True)
    if MAX_ITEMS>0 and len(merged)>MAX_ITEMS:
        manual_keep=[x for x in merged if x.get("manual_curated")]
        other_keep=[x for x in merged if not x.get("manual_curated")][:max(0,MAX_ITEMS-len(manual_keep))]
        merged=manual_keep+other_keep
        merged.sort(key=lambda x:(int(x.get("year",0)),x.get("date",""),clean(x.get("title"))),reverse=True)
    new_count=sum(1 for x in merged if not x.get("manual_curated") and clean(x.get("id")) not in previous_ids)
    matrix_counts={r:{c:0 for c in "ABCD"} for r in ROW_TERMS}
    for x in merged:
        r,c=clean(x.get("matrix_dimension")),clean(x.get("matrix_outcome"))
        if r in matrix_counts and c in matrix_counts[r]: matrix_counts[r][c]+=1
    now=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    full_rescue_enabled=bool(CONFIG.get("full_rescue_run_enabled",True)); full_rescue_threshold=int(CONFIG.get("full_rescue_run_trigger_max_new_items",3)); should_dispatch=(full_rescue_enabled and not RESCUE_MODE and new_count<=full_rescue_threshold)
    data={
        "profile_version":CONFIG.get("profile_version"),"last_updated":now,"date_from":DATE_FROM.isoformat(),"date_to":DATE_TO.isoformat(),"cutoff_exclusive":CUTOFF_EXCLUSIVE.isoformat(),"main_radar_window_months":MAIN_RADAR_WINDOW_MONTHS,
        "scope_note":"Separate source-age historical archive. A source is historical here because it predates the live scanner’s six-month historical-discovery cutoff; accepted live A/B evidence itself is cumulative. Historical content may be backward- or forward-looking. This archive does not feed the live radar, live Matrix, weak signals or live scan scheduling.",
        "ranking_note":f"Every run searches the eligible period from {DATE_FROM.isoformat()} through {DATE_TO.isoformat()}. Topic families rotate; years do not. Reader/corpus ordering is chronological after admission; source quality is used only by the upstream evidence gate and duplicate resolution.",
        "source_policy":clean(CONFIG.get("source_policy_note")) or "High-quality historical research-system evidence; curated seeds still pass the same admission gates.",
        "items":merged,"matrix_counts":matrix_counts,
        "scan_state":{"topic_cursor":next_topic,"source_cursor":next_source,"seed_cursor":next_seed,"completed_runs":int(state.get("completed_runs",0))+1,"last_completed_at":now},
        "last_scan":{
            "status":"ok" if not warnings else "completed_with_warnings","rescue_mode":RESCUE_MODE,
            "topics":[str(t.get("label")) for t in active_topics],"sources":[str(s.get("name")) for s in active_sources],"queries":queries,
            "curated_backfill":{"available":len(seeds),"queried_this_run":len(seed_queries),"workbook_ids":[x.get("workbook_id") for x in active_seeds]},
            "manual_evidence":{"available":len(manual_items),"included":sum(1 for x in merged if x.get("manual_curated"))},
            "low_yield_rotation":{"triggered":low_triggered,"new_items_after_normal_rotation":initial_new,"fresh_topics":[str(t.get("label")) for t in rescue_topics],"fresh_sources":[str(s.get("name")) for s in rescue_sources],"fresh_queries":rescue_queries,"new_items_after_all_in_run_rotations":new_count,"full_rescue_run_enabled":full_rescue_enabled,"full_rescue_run_should_dispatch":should_dispatch},
            "minimum_runtime":{"configured_seconds":MIN_RUNTIME_SECONDS,"satisfied":elapsed_seconds()>=MIN_RUNTIME_SECONDS,"continuation_waves":continuation_waves},
            "target_new_items":target_new,
            "new_items":new_count,"candidates_seen":len(candidates),"unique_gate_candidates":len(unique_gate),"total_items":len(merged),"runtime_seconds":round(time.monotonic()-STARTED_MONO,1),
            "openalex_api_key_configured":bool(OPENALEX_API_KEY),"rejection_funnel":rejection_funnel(new_count,len(unique_gate)),"diagnostics":{k:int(v) for k,v in sorted(DIAG.items())},"warnings":list(dict.fromkeys(warnings))[:50],
        },
    }
    tmp=OUT_PATH.with_suffix(".json.tmp"); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); tmp.replace(OUT_PATH)
    log(f"historical.json written: {len(merged)} total, {new_count} new; full-rescue-dispatch={should_dispatch}")
    for w in warnings[:20]: print("WARNING:",w,file=sys.stderr)
    return 0


if __name__=="__main__": raise SystemExit(main())
