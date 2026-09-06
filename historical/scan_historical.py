#!/usr/bin/env python3
"""Source-age historical scanner aligned with the live radar recall engine.

Operational isolation is strict: this script writes only historical/historical.json. It
reads historical/config.json plus the curated/manual historical evidence files. It does
not import radar.json, mutate the live matrix, weak signals, live cursors, or dispatch
the live workflow.

Historical means source age, not backward-looking content: eligible sources are older
than the live scanner’s six-month historical-discovery cutoff. Discovery uses persistent
coverage rotation across topic families, source batches, publication-age bands and source
depth, so daily runs deliberately move away from already-harvested low-hanging fruit.
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
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from scanner_run_guard import defer_if_peer_scanner_active, deployment_only_push_event
from scan_radar import (
    gate_scope as main_gate_scope,
    final_ab_candidate_worthiness as main_final_ab_candidate_worthiness,
    diversified_query_bank as main_diversified_query_bank,
)
HIST_DIR = ROOT / "historical"
CONFIG_PATH = HIST_DIR / "config.json"
OUT_PATH = Path(os.environ.get("HISTORICAL_OUTPUT_PATH", str(HIST_DIR / "historical.json")))
SEED_PATH = HIST_DIR / "historical_seed.json"
CURATED_SEED_PATH = HIST_DIR / "curated_seed_evidence.json"
MANUAL_EVIDENCE_PATH = HIST_DIR / "manual_evidence.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
MAIN_CONFIG = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))

DATE_FROM = dt.date.fromisoformat(CONFIG["date_from"])
MAIN_RADAR_WINDOW_MONTHS = max(1, int(CONFIG.get("main_radar_window_months", 6)))

def historical_cutoff_exclusive(today: dt.date | None = None) -> dt.date:
    """First date belonging to the live/main-radar window. Historical dates are earlier."""
    return (today or dt.date.today()) - relativedelta(months=MAIN_RADAR_WINDOW_MONTHS)


def historical_time_bands(date_from: dt.date | None = None, date_to: dt.date | None = None) -> list[dict[str, Any]]:
    """Build stable publication-age bands that cover the eligible historical window.

    Bands are calendar-year based rather than rolling-day slices so saved cursors remain
    meaningful from one daily run to the next. The final band is clipped to the current
    rolling historical cutoff.
    """
    start = date_from or DATE_FROM
    end = date_to or DATE_TO
    width = max(1, int(CONFIG.get("historical_time_band_years", 2)))
    bands: list[dict[str, Any]] = []
    year = start.year
    while year <= end.year:
        band_start = max(start, dt.date(year, 1, 1))
        band_end = min(end, dt.date(year + width - 1, 12, 31))
        if band_start <= band_end:
            bands.append({
                "id": f"{band_start.year}-{band_end.year}",
                "label": f"{band_start.year}–{band_end.year}",
                "date_from": band_start,
                "date_to": band_end,
            })
        year += width
    return bands


def band_for_date(value: Any, bands: list[dict[str, Any]] | None = None) -> str:
    d = parse_date(value)
    if not d:
        return ""
    for band in bands or historical_time_bands():
        if band["date_from"] <= d <= band["date_to"]:
            return str(band["id"])
    return ""

CUTOFF_EXCLUSIVE = historical_cutoff_exclusive()
DATE_TO = CUTOFF_EXCLUSIVE - dt.timedelta(days=1)
MIN_SCORE = int(CONFIG.get("minimum_admission_score", 93))
MAX_ITEMS = int(CONFIG.get("max_items", 350))
# Production contract: every Historical research cycle gets exactly 10 minutes.
# Older hidden workflows may still export 1050 seconds; ignore that stale value.
BUDGET_SECONDS = 600 if str(os.environ.get("GITHUB_ACTIONS") or "").lower() == "true" else int(os.environ.get("HISTORICAL_SCAN_BUDGET_SECONDS", str(CONFIG.get("budget_seconds", 600))))
# The production contract is a real ten-minute research window.  Older builds treated
# 600 seconds as a ceiling while reserving 90-170 seconds inside most discovery stages,
# which could leave a large idle tail.  Historical now keeps rotating useful discovery
# until only a small local-finalisation margin remains.
MIN_RUNTIME_SECONDS = int(os.environ.get("HISTORICAL_MIN_RUNTIME_SECONDS", str(CONFIG.get("minimum_runtime_seconds", 600))))
FINALIZE_MARGIN_SECONDS = max(5, int(CONFIG.get("finalize_margin_seconds", 8) or 8))
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


def legacy_hidden_historical_workflow_active() -> bool:
    """Detect the retained pre-v21 hidden workflow used by browser-uploaded repos."""
    try:
        text=(ROOT / ".github" / "workflows" / "historical-scan.yml").read_text(encoding="utf-8")
    except Exception:
        return False
    return "cron: '41 3 * * *'" in text and "HISTORICAL_SCAN_BUDGET_SECONDS: '1050'" in text

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
    """Return True while useful research may still start.

    Historical used to honour each caller's very large reserve literally.  That made
    90-170 seconds of a ten-minute run unavailable to research.  The caller reserve is
    now capped by the small finalisation margin, so all discovery lanes can use almost
    the whole research window while JSON assembly/saving still has protected time.
    """
    effective_reserve = min(max(0, int(reserve)), FINALIZE_MARGIN_SECONDS)
    return time.monotonic() < DEADLINE - effective_reserve


def elapsed_seconds() -> float:
    return time.monotonic() - STARTED_MONO


def minimum_runtime_remaining() -> float:
    return max(0.0, float(MIN_RUNTIME_SECONDS) - elapsed_seconds())


def wait_until_minimum_runtime() -> None:
    """Compatibility no-op.

    v21.5 no longer fills an early-finished Historical run with idle sleep.  The main
    continuation loop spends the remaining research window on fresh rotations instead.
    """
    return


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


def _main_source_tier(profile: dict[str, Any]) -> int:
    authority=int(profile.get("authority",0) or 0)
    if authority >= 57: return 1
    if authority >= 54: return 2
    return 3

def admit(raw: dict[str, Any], lane: str = "unknown") -> dict[str, Any] | None:
    """Historical admission uses the live Main A/B gate; only the date/source universe differs."""
    _diag("raw_records"); _diag(f"raw_{lane}")
    title=clean(raw.get("title")); abstract=clean(raw.get("abstract") or raw.get("summary") or raw.get("body"))
    url=clean(raw.get("url") or raw.get("doi")); date=parse_date(raw.get("date"))
    if not title: _diag("reject_no_title"); return None
    if ADMIN_DOC_RE.search(title): _diag("reject_administrative_document"); return None
    if date is None: _diag("reject_no_date"); return None
    if not (DATE_FROM <= date <= DATE_TO): _diag("reject_outside_window"); return None
    profile=source_for(domain_of(url), clean(raw.get("venue")), clean(raw.get("publisher")))
    if not profile: _diag("reject_source_not_elite"); return None
    _diag("source_eligible")
    text=clean(f"{title}. {abstract}")
    if BAD_DOC_RE.search(title) and not ANALYTIC_RE.search(text): _diag("reject_document_exclusion"); return None
    source_kind="scholarly" if profile.get("kind")=="top_journal" else "institutional"
    tier=_main_source_tier(profile)
    evidence=main_gate_scope(title, abstract, "", tier, source_kind)
    a_pass=bool(evidence.get("a_pass")); b_pass=bool(evidence.get("b_pass"))
    if not (a_pass or b_pass):
        _diag("reject_main_ab_gate"); return None
    candidate_type="peer-reviewed article" if source_kind=="scholarly" else "institutional report"
    if not main_final_ab_candidate_worthiness({"title":title,"summary":abstract,"type":candidate_type,"link":url}):
        _diag("reject_main_final_worthiness"); return None
    topics=topic_matches(text)
    if not topics:
        if b_pass:
            method_text=norm(" ".join(evidence.get("foresight_evidence",[])+evidence.get("method_evidence",[])))
            topics=["computational-emergence" if any(x in method_text for x in ("topic","citation","semantic","network","novelty","change point","embedding")) else "foresight-methods"]
        else:
            topics=["main-a-evidence"]
    authority=int(profile.get("authority",0)); evidence_bonus=18 if a_pass else 16
    score=min(100, authority + evidence_bonus + (8 if abstract and len(abstract.split())>=28 else 4) + year_bonus(date))
    # Source eligibility plus the live Main A/B gate is the admission decision. The score is
    # retained for historical reader ordering/diagnostics, not as a second contradictory gate.
    _diag("gate_passed"); _diag("main_a_pass" if a_pass else "main_b_pass")
    row,outcome,basis=matrix_classification(text)
    strand="AB" if a_pass and b_pass else ("A" if a_pass else "B")
    return {
        "id":stable_id(title,url),"title":title,"date":date.isoformat(),"year":date.year,"url":url,
        "authors":clean(raw.get("authors")),"source":clean(profile.get("name")),"source_kind":clean(profile.get("kind")),
        "venue":clean(raw.get("venue")),"publisher":clean(raw.get("publisher")),"source_merit_score":score,"source_merit_label":"Historical top tier · Main A/B gate",
        "strand":strand,"a_route":clean(evidence.get("a_route")),"b_route":clean(evidence.get("b_route")),
        "eu_evidence":list(evidence.get("eu_evidence") or [])[:6],"ri_evidence":list(evidence.get("ri_evidence") or [])[:6],
        "geo_evidence":list(evidence.get("geo_evidence") or [])[:6],"method_evidence":list(evidence.get("method_evidence") or [])[:6],
        "topics":topics,"topic_labels":[topic_label(t) for t in topics],
        "reader_point":first_sentence(abstract) or title,"why_it_matters":why_it_matters(row,outcome),
        "matrix_dimension":row,"matrix_outcome":outcome,"matrix_basis":basis,"discovery":clean(raw.get("discovery")),
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


def collect_openalex(queries: list[str], warnings: list[str], lane: str = "openalex", result_page: int = 1, window_from: dt.date | None = None, window_to: dt.date | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    scan_cap = int(CONFIG.get("openalex_missing_abstract_enrichment_per_scan", 24))
    per_query = int(CONFIG.get("openalex_missing_abstract_enrichment_per_query", 3))
    min_priority = int(CONFIG.get("metadata_rescue_priority_min_score", 10))
    used_rescue = 0
    for q in queries:
        if not budget_ok(90): break
        wf=window_from or DATE_FROM; wt=window_to or DATE_TO
        params = {"search":q,"filter":f"from_publication_date:{wf.isoformat()},to_publication_date:{wt.isoformat()},language:en","per-page":int(CONFIG.get("openalex_per_query",50)),"page":max(1,int(result_page)),"sort":"relevance_score:desc"}
        if OPENALEX_API_KEY: params["api_key"] = OPENALEX_API_KEY
        try:
            r = SESSION.get("https://api.openalex.org/works", params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code == 429:
                warnings.append("OpenAlex rate limited (429); remaining Historical time reallocated to other sources")
                _diag("openalex_429")
                break
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


def collect_crossref(queries: list[str], warnings: list[str], lane: str = "crossref", result_page: int = 1, window_from: dt.date | None = None, window_to: dt.date | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    scan_cap=int(CONFIG.get("crossref_missing_abstract_enrichment_per_scan",36)); per_task=int(CONFIG.get("crossref_missing_abstract_enrichment_per_query",3)); min_priority=int(CONFIG.get("metadata_rescue_priority_min_score",10)); used_rescue=0
    query_key = "query.title" if clean(CONFIG.get("crossref_relevance_query_mode","title")).lower()=="title" else "query.bibliographic"
    for q in queries:
        if not budget_ok(90): break
        wf=window_from or DATE_FROM; wt=window_to or DATE_TO
        rows=int(CONFIG.get("crossref_per_query",50)); params={query_key:q,"filter":f"from-pub-date:{wf.isoformat()},until-pub-date:{wt.isoformat()}","rows":rows,"offset":max(0,(max(1,int(result_page))-1)*rows),"sort":"relevance","order":"desc","select":"DOI,title,abstract,published-print,published-online,published,issued,created,author,container-title,publisher,URL,type"}
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


def historical_date_from_text(text: str) -> dt.date | None:
    """Recover an eligible historical date from body text or opaque URLs.

    Older code only recognised 2023–2025 in this fallback, which systematically hurt
    discovery of 2015–2022 institutional material when structured metadata was absent.
    """
    for m in re.finditer(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", clean(text)[:12000]):
        d = parse_date(m.group(0))
        if d and DATE_FROM <= d <= DATE_TO:
            return d
    for m in re.finditer(r"\b(20\d{2})\b", clean(text)[:12000]):
        try:
            y = int(m.group(1))
            d = dt.date(y, 1, 1)
        except Exception:
            continue
        if DATE_FROM.year <= y <= DATE_TO.year:
            return d
    return None


def page_date(soup: BeautifulSoup, text: str) -> dt.date | None:
    candidates=[]
    for tag in soup.find_all("meta"):
        key=clean(tag.get("property") or tag.get("name") or tag.get("itemprop")).lower()
        if key in {"article:published_time","date","datepublished","publication_date","dc.date","dcterms.date"}: candidates.append(clean(tag.get("content")))
    for t in soup.find_all("time")[:8]: candidates.append(clean(t.get("datetime") or t.get_text(" ",strip=True)))
    for c in candidates:
        d=parse_date(c)
        if d and DATE_FROM<=d<=DATE_TO: return d
    return historical_date_from_text(text)


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
            d=historical_date_from_text(f"{r.url} {body[:10000]}")
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


def collect_direct_sources(active_sources: list[dict[str, Any]], active_topics: list[dict[str, Any]], warnings: list[str], depth_page: int = 1) -> list[dict[str, Any]]:
    out=[]; limit=max(1,int(CONFIG.get("direct_pages_per_source",10)))
    max_depth=max(1,int(CONFIG.get("direct_source_depth_pages",4)))
    requested_page=max(1,int(depth_page))
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
        if urls:
            available_pages=max(1,min(max_depth,(len(urls)+limit-1)//limit))
            page_index=(requested_page-1)%available_pages
            start=page_index*limit
            selected=urls[start:start+limit]
        else:
            page_index=0; selected=[]
        for url in selected:
            if not budget_ok(55): break
            item=fetch_page_candidate(url,src,warnings,"direct")
            if item: out.append(item); admitted+=1
        _diag("direct_source_depth_page_"+str(page_index+1))
        log(f"Direct source: {src.get('name')} depth {page_index+1} -> {admitted} admitted")
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
    """Preserve a record that was already accepted into the historical archive.

    Historical evidence is cumulative.  Current admission rules apply to *new*
    discoveries only; a normal scan must never silently evict an item merely because
    the gates, taxonomy or available metadata changed later.  We may enrich missing
    derived fields, but never require a previously accepted record to re-qualify.
    """
    if not isinstance(raw, dict):
        return None
    item=dict(raw)
    title=clean(item.get("title"))
    if not clean(item.get("id")):
        item["id"]=stable_id(title,clean(item.get("url")))
    d=parse_date(item.get("date"))
    if d and not item.get("year"):
        item["year"]=d.year
    text=clean(f"{title}. {item.get('reader_point','')}")
    if text:
        topics=list(item.get("topics") or [])
        if not topics:
            topics=topic_matches(text)
            if topics:
                item["topics"]=topics
                item["topic_labels"]=[topic_label(t) for t in topics]
        if not clean(item.get("matrix_dimension")) or not clean(item.get("matrix_outcome")):
            row,outcome,basis=matrix_classification(text)
            if row and outcome:
                item["matrix_dimension"],item["matrix_outcome"],item["matrix_basis"]=row,outcome,basis
                if not clean(item.get("why_it_matters")):
                    item["why_it_matters"]=why_it_matters(row,outcome)
    return item


def duplicate_keys(item: dict[str, Any]) -> set[str]:
    """Stable duplicate keys used only to stop *new* copies entering the archive."""
    keys=set()
    ident=clean(item.get("id"))
    title=norm(item.get("title"))
    url=clean(item.get("url")).lower().rstrip("/")
    if ident:
        keys.add("id:"+ident)
    if title:
        keys.add("title:"+title)
    if url:
        keys.add("url:"+url)
    return keys


def enrich_existing(existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Fill gaps in an accepted record without replacing or de-admitting it."""
    out=dict(existing)
    for key,value in candidate.items():
        if key in {"id","title","date","url"}:
            continue
        if key in {"topics","topic_labels"}:
            old=list(out.get(key) or [])
            add=list(value or []) if isinstance(value,list) else []
            if add:
                out[key]=list(dict.fromkeys(old+add))
            continue
        if key=="source_merit_score":
            try:
                out[key]=max(int(out.get(key,0) or 0),int(value or 0))
            except Exception:
                pass
            continue
        if (out.get(key) is None or out.get(key)=="" or out.get(key)==[]) and value not in (None,"",[]):
            out[key]=value
    return out


def cumulative_merge(previous_items: Iterable[dict[str, Any]], manual_items: Iterable[dict[str, Any]], new_items: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Append-only merge for normal historical scans.

    Every previously accepted row survives.  Manual and newly discovered rows are
    appended only when they are not duplicates of something already retained.  A
    duplicate may enrich the retained row, but it can never reduce the archive size.
    Returns ``(merged_items, genuinely_new_scan_items)``.
    """
    merged=[]
    key_to_index={}

    # Preserve every previous row, including any legacy duplicates.  We deliberately
    # do not deduplicate this layer during an ordinary scan because that would make the
    # historical count fall.
    for raw in previous_items:
        item=refresh_existing_item(raw)
        if item is None:
            continue
        idx=len(merged)
        merged.append(item)
        for key in duplicate_keys(item):
            key_to_index.setdefault(key,idx)

    def add_or_enrich(raw: dict[str, Any], *, count_as_new: bool) -> int:
        if not isinstance(raw,dict):
            return 0
        item=dict(raw)
        keys=duplicate_keys(item)
        match=next((key_to_index[k] for k in keys if k in key_to_index),None)
        if match is not None:
            merged[match]=enrich_existing(merged[match],item)
            for key in duplicate_keys(merged[match]):
                key_to_index.setdefault(key,match)
            return 0
        idx=len(merged)
        merged.append(item)
        for key in keys:
            key_to_index.setdefault(key,idx)
        return 1 if count_as_new else 0

    for item in manual_items:
        add_or_enrich(item,count_as_new=False)
    new_count=0
    for item in new_items:
        new_count+=add_or_enrich(item,count_as_new=True)
    return merged,new_count


def count_new_against_retained(items: Iterable[dict[str, Any]], retained_items: Iterable[dict[str, Any]]) -> int:
    retained_keys=set()
    for item in retained_items:
        if isinstance(item,dict):
            retained_keys.update(duplicate_keys(item))
    count=0
    local=set(retained_keys)
    for item in items:
        if not isinstance(item,dict):
            continue
        keys=duplicate_keys(item)
        if keys and keys & local:
            continue
        count+=1
        local.update(keys)
    return count


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


def run_rotation(active_topics: list[dict[str, Any]], active_sources: list[dict[str, Any]], warnings: list[str], suffix: str="normal", result_page: int = 1, extra_queries: list[str] | None = None, window_from: dt.date | None = None, window_to: dt.date | None = None, direct_depth_page: int = 1, include_direct: bool = True) -> tuple[list[dict[str, Any]], list[str]]:
    queries=list(dict.fromkeys(query_plan_for(active_topics) + [clean(x) for x in (extra_queries or []) if clean(x)])); candidates=[]
    candidates.extend(collect_openalex(queries,warnings,f"openalex_{suffix}",result_page=result_page,window_from=window_from,window_to=window_to))
    candidates.extend(collect_crossref(queries,warnings,f"crossref_{suffix}",result_page=result_page,window_from=window_from,window_to=window_to))
    if include_direct:
        candidates.extend(collect_direct_sources(active_sources,active_topics,warnings,depth_page=direct_depth_page))
    return candidates,queries


def archive_cell_counts(items: Iterable[dict[str, Any]], bands: list[dict[str, Any]] | None = None) -> dict[tuple[str,str], int]:
    """Count retained evidence by topic × publication-age band for gap seeking."""
    use_bands=bands or historical_time_bands(); counts: collections.Counter[tuple[str,str]] = collections.Counter()
    for item in items:
        if not isinstance(item,dict): continue
        bid=band_for_date(item.get("date"),use_bands)
        if not bid: continue
        for topic in item.get("topics") or []:
            if clean(topic): counts[(clean(topic),bid)] += 1
    return dict(counts)


def select_gap_cells(items: Iterable[dict[str, Any]], bands: list[dict[str, Any]], cursor: int, count: int) -> tuple[list[tuple[dict[str,Any],dict[str,Any],int]], int]:
    """Select under-covered topic × time-band cells without getting stuck on one hole."""
    topics=[t for t in CONFIG.get("topics",[]) if clean(t.get("id"))]
    counts=archive_cell_counts(items,bands)
    cells=[(t,b,int(counts.get((clean(t.get("id")),clean(b.get("id"))),0))) for t in topics for b in bands]
    cells.sort(key=lambda x:(x[2],clean(x[1].get("id")),clean(x[0].get("id"))))
    if not cells or count<=0: return [],0
    # Work inside the least-covered half, but rotate within it so a permanently empty
    # cell cannot monopolise every daily run.
    pool=cells[:max(count,min(len(cells),max(12,len(cells)//2)))]
    chosen,next_cursor=rotating(pool,cursor,count)
    return chosen,next_cursor


def author_seed_pool(items: Iterable[dict[str, Any]]) -> list[str]:
    """Known-good first authors, used only to discover earlier work by trusted researchers."""
    out=[]; seen=set()
    for item in items:
        authors=clean(item.get("authors"))
        if not authors: continue
        first=clean(authors.split(";")[0])
        key=norm(first)
        if len(first.split())<2 or key in seen: continue
        seen.add(key); out.append(first)
    return out


def collect_crossref_authors(authors: list[str], warnings: list[str], window_from: dt.date, window_to: dt.date) -> list[dict[str, Any]]:
    """Backtrack earlier work by authors already present in high-quality historical evidence."""
    if not bool(CONFIG.get("historical_author_backfill_enabled",True)): return []
    out=[]; rows=max(5,int(CONFIG.get("historical_author_results_per_query",30)))
    for author in authors:
        if not budget_ok(90): break
        params={"query.author":author,"filter":f"from-pub-date:{window_from.isoformat()},until-pub-date:{window_to.isoformat()}","rows":rows,"sort":"relevance","order":"desc","select":"DOI,title,abstract,published-print,published-online,published,issued,created,author,container-title,publisher,URL,type"}
        try:
            r=SESSION.get("https://api.crossref.org/works",params=params,timeout=REQUEST_TIMEOUT)
            if r.status_code==429: warnings.append("Crossref author backfill rate limited (429)"); _diag("crossref_author_429"); continue
            r.raise_for_status(); works=((r.json().get("message") or {}).get("items") or [])
        except Exception as e:
            warnings.append(f"Crossref author backfill {type(e).__name__}: {e}"); continue
        _diag("crossref_author_results",len(works))
        for w in works:
            title=clean(" ".join(w.get("title") or [])); venue=clean(" ".join(w.get("container-title") or [])); names="; ".join(clean(f"{a.get('given','')} {a.get('family','')}") for a in (w.get("author") or [])[:12]); doi=clean(w.get("DOI")); url=clean(w.get("URL") or ("https://doi.org/"+doi if doi else ""))
            raw={"title":title,"abstract":clean(re.sub(r"<[^>]+>"," ",w.get("abstract") or "")),"date":crossref_date(w),"url":url,"doi":doi,"authors":names,"venue":venue,"publisher":clean(w.get("publisher")),"discovery":f"Crossref author backtrack · {author}"}
            item=admit(raw,"author_backtrack")
            if item: out.append(item)
    return out


def main() -> int:
    try:
        previous=json.loads(OUT_PATH.read_text(encoding="utf-8")) if OUT_PATH.exists() else json.loads(SEED_PATH.read_text(encoding="utf-8"))
        if not OUT_PATH.exists(): log("No live historical.json yet; bootstrapping from historical_seed.json")
    except Exception:
        previous={}
    state=previous.get("scan_state") if isinstance(previous.get("scan_state"),dict) else {}
    previous_items=[x for x in previous.get("items",[]) if isinstance(x,dict)]
    topics=list(CONFIG.get("topics",[])); sources=list(CONFIG.get("elite_sources",[])); seeds=curated_seed_items(); manual_items=manual_evidence_items()
    bands=historical_time_bands()

    topic_cursor=int(state.get("topic_cursor",0)); source_cursor=int(state.get("source_cursor",0)); seed_cursor=int(state.get("seed_cursor",0))
    band_cursor=int(state.get("time_band_cursor",0)); source_depth_cursor=int(state.get("source_depth_cursor",0)); gap_cursor=int(state.get("gap_cursor",0)); author_cursor=int(state.get("author_cursor",0)); api_depth_cursor=int(state.get("api_depth_cursor",0))
    main_query_cursor=int(state.get("main_query_cursor",0) or 0)
    dimensional=[]
    for vals in (MAIN_CONFIG.get("precision_recall_query_families",{}) or {}).values():
        dimensional.extend(vals if isinstance(vals,list) else [vals])
    main_query_bank=main_diversified_query_bank(list(dict.fromkeys(
        [clean(x) for x in MAIN_CONFIG.get("queries_a",[]) + MAIN_CONFIG.get("queries_b_method",[]) + dimensional if clean(x)]
    )))
    main_query_batch,next_main_query=rotating(main_query_bank,main_query_cursor,max(0,int(CONFIG.get("shared_main_queries_per_scan",18))))

    active_topics,next_topic=rotating(topics,topic_cursor,int(CONFIG.get("topics_per_scan",4)))
    active_sources,next_source=rotating(sources,source_cursor,int(CONFIG.get("sources_per_scan",8)))
    active_seeds,next_seed=rotating(seeds,seed_cursor,int(CONFIG.get("curated_seed_queries_per_scan",8)))
    active_bands,next_band=rotating(bands,band_cursor,max(1,int(CONFIG.get("time_bands_per_scan",1))))
    active_band=active_bands[0] if active_bands else {"id":"all","label":"all years","date_from":DATE_FROM,"date_to":DATE_TO}
    max_source_depth=max(1,int(CONFIG.get("direct_source_depth_pages",4)))
    source_depth_page=1+(source_depth_cursor%max_source_depth)
    max_api_depth=max(1,int(CONFIG.get("api_result_depth_pages",3)))
    api_result_page=1+(api_depth_cursor%max_api_depth)

    # Historical retention is append-only: current gates determine what may be added,
    # never what is allowed to remain. Manual evidence is part of the retained baseline.
    retained_baseline=previous_items+manual_items
    warnings=[]
    log(f"Historical coverage scan: {DATE_FROM.isoformat()} through {DATE_TO.isoformat()} (sources before {CUTOFF_EXCLUSIVE.isoformat()})")
    log(f"Primary publication band: {active_band['label']} · API page {api_result_page} · direct-source depth {source_depth_page}")
    log("Topics: "+" | ".join(str(t.get("label")) for t in active_topics))

    # 1) Primary rotating coverage block. Topic, source, time band, API depth and
    # direct-source depth all advance persistently between daily runs.
    candidates,queries=run_rotation(
        active_topics,active_sources,warnings,"coverage",
        result_page=api_result_page,
        extra_queries=main_query_batch,
        window_from=active_band["date_from"],window_to=active_band["date_to"],
        direct_depth_page=source_depth_page,
    )

    # 2) Curated known-good titles remain a separate backfill lane. Search them across
    # their own likely publication years rather than wasting the current band on a seed
    # known to belong elsewhere.
    seed_queries=[clean(x.get("title")) for x in active_seeds if clean(x.get("title"))]
    seed_candidates=[]
    for seed in active_seeds:
        if not budget_ok(150): break
        title=clean(seed.get("title"))
        if not title: continue
        try: sy=int(seed.get("year") or 0)
        except Exception: sy=0
        if sy and DATE_FROM.year<=sy<=DATE_TO.year:
            sf=max(DATE_FROM,dt.date(sy,1,1)); st=min(DATE_TO,dt.date(sy,12,31))
        else:
            sf,st=DATE_FROM,DATE_TO
        c,_=run_rotation([],[],warnings,"curated_seed",result_page=1,extra_queries=[title],window_from=sf,window_to=st,include_direct=False)
        seed_candidates.extend(c)
    candidates.extend(seed_candidates)
    if seed_queries: log(f"Curated backfill: {len(seed_queries)} title seed(s), year-scoped where possible")

    # 3) Gap seeking. Always spend a small part of the daily budget on the thinnest
    # topic × publication-band cells, but rotate within the under-covered pool so one
    # permanently empty cell cannot monopolise every run.
    gap_count=max(0,int(CONFIG.get("gap_cells_per_scan",2)))
    gap_cells,next_gap=select_gap_cells(retained_baseline,bands,gap_cursor,gap_count)
    gap_details=[]
    for idx,(gap_topic,gap_band,prior_count) in enumerate(gap_cells,1):
        if not budget_ok(170): break
        log(f"Gap cell {idx}: {gap_topic.get('label')} × {gap_band.get('label')} (retained={prior_count})")
        gc,gq=run_rotation([gap_topic],[],warnings,f"gap_{idx}",result_page=1,window_from=gap_band["date_from"],window_to=gap_band["date_to"],include_direct=False)
        candidates.extend(gc)
        gap_details.append({"topic":str(gap_topic.get("label")),"topic_id":str(gap_topic.get("id")),"band":str(gap_band.get("label")),"band_id":str(gap_band.get("id")),"retained_before":prior_count,"queries":gq,"candidates":len(gc)})

    # 4) Author backtracking. Rotate first authors from already admitted high-quality
    # evidence and look for their earlier work in the current age band. Admission gates
    # still decide whether any result belongs in this archive.
    authors=author_seed_pool(retained_baseline)
    active_authors,next_author=rotating(authors,author_cursor,max(0,int(CONFIG.get("historical_authors_per_scan",4))))
    author_candidates=[]
    if active_authors and budget_ok(170):
        author_candidates=collect_crossref_authors(active_authors,warnings,active_band["date_from"],active_band["date_to"])
        candidates.extend(author_candidates)
        log(f"Known-good author backtrack: {len(active_authors)} author(s) in {active_band['label']}")

    unique_initial=dedupe(candidates)
    initial_new=count_new_against_retained(unique_initial,retained_baseline)
    target_new=max(1,int(CONFIG.get("target_new_items_per_scan",8) or 8))
    low_threshold=max(int(CONFIG.get("low_yield_trigger_max_new_items",3)),target_new-1)
    low_triggered=initial_new<=low_threshold

    # 5) Full-window continuation inside this same GitHub job. Every continuation
    # advances to fresh topic/source/band/depth territory. Reaching the new-item target
    # never ends research early; the scanner keeps using the ten-minute window. Source
    # quality and EU/R&I/geopolitical admission gates never change.
    continuation_waves=[]
    topics_per_wave=max(1,int(CONFIG.get("minimum_runtime_topics_per_wave",2)))
    sources_per_wave=max(1,int(CONFIG.get("minimum_runtime_sources_per_wave",4)))
    max_extra=max(1,int(CONFIG.get("minimum_runtime_max_extra_waves",200)))
    next_source_depth=source_depth_cursor+1
    next_api_depth=api_depth_cursor+1
    current_unique=dedupe(candidates)
    current_new=count_new_against_retained(current_unique,retained_baseline)
    while budget_ok(FINALIZE_MARGIN_SECONDS) and len(continuation_waves)<max_extra:
        wave_no=len(continuation_waves)+1
        wave_topics,wave_next_topic=rotating(topics,next_topic,topics_per_wave)
        wave_sources,wave_next_source=rotating(sources,next_source,sources_per_wave)
        wave_bands,wave_next_band=rotating(bands,next_band,1)
        wave_band=wave_bands[0] if wave_bands else active_band
        wave_source_page=1+(next_source_depth%max_source_depth)
        wave_api_page=1+(next_api_depth%max_api_depth)
        log(f"Continuation {wave_no}: {wave_band['label']} · API page {wave_api_page} · source depth {wave_source_page} · "+" | ".join(str(t.get("label")) for t in wave_topics))
        wc,wq=run_rotation(wave_topics,wave_sources,warnings,f"continuation_{wave_no}",result_page=wave_api_page,window_from=wave_band["date_from"],window_to=wave_band["date_to"],direct_depth_page=wave_source_page)
        candidates.extend(wc)
        continuation_waves.append({"wave":wave_no,"band":str(wave_band.get("label")),"band_id":str(wave_band.get("id")),"api_result_page":wave_api_page,"direct_source_depth_page":wave_source_page,"topics":[str(t.get("label")) for t in wave_topics],"sources":[str(s.get("name")) for s in wave_sources],"queries":wq,"candidates":len(wc)})
        next_topic=wave_next_topic; next_source=wave_next_source; next_band=wave_next_band; next_source_depth+=1; next_api_depth+=1
        current_unique=dedupe(candidates)
        current_new=count_new_against_retained(current_unique,retained_baseline)

    wait_until_minimum_runtime()
    unique_gate=dedupe(candidates)
    merged,new_count=cumulative_merge(previous_items,manual_items,unique_gate)
    merged.sort(key=lambda x:(int(x.get("year",0) or 0),clean(x.get("date")),clean(x.get("title"))),reverse=True)

    matrix_counts={r:{c:0 for c in "ABCD"} for r in ROW_TERMS}
    for x in merged:
        r,c=clean(x.get("matrix_dimension")),clean(x.get("matrix_outcome"))
        if r in matrix_counts and c in matrix_counts[r]: matrix_counts[r][c]+=1

    cell_counts=archive_cell_counts(merged,bands)
    band_counts={str(b.get("id")):sum(1 for x in merged if band_for_date(x.get("date"),bands)==str(b.get("id"))) for b in bands}
    thinnest=[]
    for (topic_id,band_id),count in sorted(cell_counts.items(),key=lambda kv:(kv[1],kv[0]))[:12]:
        thinnest.append({"topic_id":topic_id,"band_id":band_id,"count":int(count)})

    now=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    data={
        "profile_version":CONFIG.get("profile_version"),"last_updated":now,"date_from":DATE_FROM.isoformat(),"date_to":DATE_TO.isoformat(),"cutoff_exclusive":CUTOFF_EXCLUSIVE.isoformat(),"main_radar_window_months":MAIN_RADAR_WINDOW_MONTHS,
        "scope_note":"Separate, cumulative source-age historical archive. A source is historical here because it predates the live scanner’s six-month historical-discovery cutoff. Once historical evidence is accepted, normal scans keep it; current admission gates apply only to newly discovered material. Historical content may be backward- or forward-looking. This archive does not feed the live radar, live Matrix, weak signals or live scan scheduling.",
        "ranking_note":f"Historical discovery deliberately rotates across topic families, source batches, publication-age bands and result/source depth from {DATE_FROM.isoformat()} through {DATE_TO.isoformat()}. It also probes under-covered topic × time-band cells and earlier work by known-good authors. Reader/corpus ordering is chronological after admission; source quality is used only by the upstream evidence gate and duplicate resolution.",
        "source_policy":clean(CONFIG.get("source_policy_note")) or "High-quality historical research-system evidence; curated seeds still pass the same admission gates.",
        "items":merged,"matrix_counts":matrix_counts,
        "coverage_map":{"bands":[{"id":str(b.get("id")),"label":str(b.get("label")),"date_from":b["date_from"].isoformat(),"date_to":b["date_to"].isoformat(),"items":int(band_counts.get(str(b.get("id")),0))} for b in bands],"thinnest_populated_cells":thinnest},
        "scan_state":{"topic_cursor":next_topic,"source_cursor":next_source,"seed_cursor":next_seed,"time_band_cursor":next_band,"source_depth_cursor":next_source_depth%max_source_depth,"api_depth_cursor":next_api_depth%max_api_depth,"gap_cursor":next_gap,"author_cursor":next_author,"main_query_cursor":next_main_query,"completed_runs":int(state.get("completed_runs",0))+1,"last_completed_at":now},
        "last_scan":{
            "status":"ok" if not warnings else "completed_with_warnings","rescue_mode":False,
            "topics":[str(t.get("label")) for t in active_topics],"sources":[str(s.get("name")) for s in active_sources],"queries":queries,"shared_main_queries":main_query_batch,
            "coverage_rotation":{"primary_band":str(active_band.get("label")),"primary_band_id":str(active_band.get("id")),"api_result_page":api_result_page,"direct_source_depth_page":source_depth_page,"gap_cells":gap_details,"known_good_authors":active_authors,"author_candidates":len(author_candidates)},
            "curated_backfill":{"available":len(seeds),"queried_this_run":len(seed_queries),"workbook_ids":[x.get("workbook_id") for x in active_seeds]},
            "manual_evidence":{"available":len(manual_items),"included":sum(1 for x in merged if x.get("manual_curated"))},
            "low_yield_rotation":{"triggered":low_triggered,"new_items_before_continuations":initial_new,"new_items_after_all_in_run_rotations":new_count,"separate_rescue_run_enabled":False},
            "minimum_runtime":{"configured_seconds":MIN_RUNTIME_SECONDS,"research_window_seconds":BUDGET_SECONDS,"finalize_margin_seconds":FINALIZE_MARGIN_SECONDS,"satisfied":elapsed_seconds()>=max(0,MIN_RUNTIME_SECONDS-FINALIZE_MARGIN_SECONDS),"continuation_waves":continuation_waves},
            "target_new_items":target_new,
            "cumulative_retention":{"enabled":True,"previous_items":len(previous_items),"retained_previous_items":len(previous_items),"normal_scan_deletions":0,"legacy_max_items":MAX_ITEMS},
            "new_items":new_count,"candidates_seen":len(candidates),"unique_gate_candidates":len(unique_gate),"total_items":len(merged),"runtime_seconds":round(time.monotonic()-STARTED_MONO,1),
            "openalex_api_key_configured":bool(OPENALEX_API_KEY),"rejection_funnel":rejection_funnel(new_count,len(unique_gate)),"diagnostics":{k:int(v) for k,v in sorted(DIAG.items())},"warnings":list(dict.fromkeys(warnings))[:50],
        },
    }
    tmp=OUT_PATH.with_suffix(".json.tmp"); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); tmp.replace(OUT_PATH)
    log(f"historical.json written: {len(merged)} total, {new_count} new; one self-contained four-hour cycle")
    for w in warnings[:20]: print("WARNING:",w,file=sys.stderr)
    return 0


def refresh_window_metadata_only(reason: str = "peer scanner owns the slot") -> None:
    """Keep legacy workflow verification truthful without doing Historical research.

    Current workflows share one GitHub concurrency group and therefore queue before this
    code is reached. Older hidden workflow YAML can survive a browser bulk upload, though.
    In that compatibility case the runtime guard deliberately performs no source requests.
    The old workflow's next safety step still expects today's historical window metadata,
    so refresh only those date-window fields (plus a diagnostic) and preserve the accepted
    corpus, scan cursors, last completed scan, and evidence counts unchanged.
    """
    try:
        data = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return
    if not isinstance(data, dict):
        return
    data["date_from"] = DATE_FROM.isoformat()
    data["cutoff_exclusive"] = CUTOFF_EXCLUSIVE.isoformat()
    data["date_to"] = DATE_TO.isoformat()
    data["main_radar_window_months"] = MAIN_RADAR_WINDOW_MONTHS
    compat = data.get("workflow_compatibility") if isinstance(data.get("workflow_compatibility"), dict) else {}
    compat["metadata_only_without_source_requests"] = True
    compat["metadata_only_reason"] = str(reason)
    compat["metadata_only_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data["workflow_compatibility"] = compat
    tmp = OUT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT_PATH)
    log(f"{reason}; refreshed historical window metadata only. No source requests were made and no accepted evidence was removed.")


if __name__=="__main__":
    event=str(os.environ.get("GITHUB_EVENT_NAME") or os.environ.get("RADAR_RUN_TRIGGER") or "").strip().lower()
    if deployment_only_push_event("historical"):
        refresh_window_metadata_only("Repository push/upload event is deployment-only for Historical")
        raise SystemExit(0)
    # Under the old hidden daily workflow, automatic Historical work is supplied by the
    # Main workflow's sequential follow-up compatibility run every four hours. Skip the
    # obsolete daily schedule so it cannot duplicate or overlap research. Manual runs remain valid.
    if event == "schedule" and legacy_hidden_historical_workflow_active():
        log("Legacy daily Historical schedule detected; skipping. Four-hour Historical work is chained after Main.")
        raise SystemExit(0)
    if defer_if_peer_scanner_active("historical", ROOT):
        refresh_window_metadata_only("Peer scanner owns the runtime slot")
        raise SystemExit(0)
    raise SystemExit(main())
