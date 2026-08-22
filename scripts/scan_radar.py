#!/usr/bin/env python3
"""R&I × Geopolitics + Foresight Methodology radar scanner (EU-first, balanced).

Key properties
--------------
* No API keys or paid services are required.
* Discovery is broad; admission is selective but not brittle.
* Strand A requires substantive R&I/related-system content + geopolitics/economic security + EU relevance.
  A same-sentence bridge is strong evidence, but a document-level bridge can also qualify.
* Strand B requires methodology to be substantive, while allowing high-quality transferable
  public-sector R&I/S&T methods even when the case study is not explicitly EU-focused.
* Strand C is not a general news feed: every admitted item must be a factual current development
  with a strong R&I/geopolitical bridge. It is linked to an A/B publication where possible, but can
  also enter through a curated strategic watch theme so a thin A/B corpus cannot suppress signals.
  Once admitted, the signal is retained in the cumulative historical corpus.
* Calls, facility pages, project pages, press releases, news/blog pages, events,
  jobs and other non-analytical material are rejected for A/B.

The scanner aims for high-recall discovery with substantive admission: EU scope + R&I/related-system substance + geopolitics/economic security. It does not pad.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import gzip
import io
import json
import re
import threading
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
from dateutil.relativedelta import relativedelta
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "radar_config.json"
OUT_PATH = ROOT / "radar.json"
FRONTIER_COVERAGE_SCRIPT = ROOT / "scripts" / "frontier_coverage.js"

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    CONFIG = json.load(f)

BOOTSTRAP_LOOKBACK_MONTHS = int(CONFIG.get("bootstrap_lookback_months", 4))
SOURCE_EXPANSION_VERSION = str(CONFIG.get("source_expansion_version", "v17-scholarly-substance"))
QUALITY_PROFILE_VERSION = str(CONFIG.get("quality_profile_version", "v17-eu-ri-geo-substance"))
SIGNAL_DISCOVERY_VERSION = str(CONFIG.get("signal_discovery_version", "v16-weak-signals"))
SIGNAL_BACKFILL_HOURS = int(CONFIG.get("signal_backfill_hours", 720))
INCREMENTAL_STATE_VERSION = str(CONFIG.get("incremental_state_version", "v17.2-persistent-source-cursors"))
FORCE_SOURCE_EXPANSION_BACKFILL = bool(CONFIG.get("force_backfill_on_source_expansion", True))
# Provisional floor for import-time helpers/tests. main() replaces this with the preserved
# corpus floor before discovery starts.
DATE_FLOOR = dt.date.today() - relativedelta(months=BOOTSTRAP_LOOKBACK_MONTHS)
NEWS_LOOKBACK_HOURS = int(CONFIG.get("news_lookback_hours", 168))
FIRST_NEWS_LOOKBACK_HOURS = int(CONFIG.get("first_news_lookback_hours", SIGNAL_BACKFILL_HOURS))
DISCOVERY_OVERLAP_DAYS = int(CONFIG.get("discovery_overlap_days", 14))
MAX_NEW_AB = int(CONFIG.get("max_new_ab_per_scan", 0))
MAX_C = int(CONFIG.get("max_c_per_scan", 0))
MAX_CORPUS = int(CONFIG.get("max_corpus_per_strand", 0))
REQUEST_TIMEOUT = int(CONFIG.get("request_timeout_seconds", 12))
SCAN_DEADLINE_MONO: float | None = None
SCAN_STAGE_DEADLINES: dict[str, float] = {}
KNOWN_AB_IDENTITIES: set[str] = set()
KNOWN_AB_LINKS: set[str] = set()
KNOWN_SIGNAL_IDENTITIES: set[str] = set()
INSTITUTION_SEEN_FINGERPRINTS: dict[str, str] = {}
UA = "RI-Geopolitics-Radar/3.0 (+https://vevirm.github.io/radar_articles_reports/)"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": UA,
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})


def log_progress(message: str) -> None:
    """Flush progress to Actions logs so a long scan never looks hung."""
    elapsed = 0.0
    try:
        elapsed = time.monotonic() - log_progress.started
    except Exception:
        pass
    print(f"[radar +{elapsed:6.1f}s] {message}", flush=True)


log_progress.started = time.monotonic()


def budget_remaining() -> float:
    if SCAN_DEADLINE_MONO is None:
        return float("inf")
    return SCAN_DEADLINE_MONO - time.monotonic()


def deadline_reached(reserve_seconds: int = 0) -> bool:
    return budget_remaining() <= reserve_seconds


def stage_deadline_reached(stage_deadline: float | None, reserve_seconds: int = 0) -> bool:
    """Respect both the overall scan budget and a source-family time slice."""
    if deadline_reached(reserve_seconds):
        return True
    return stage_deadline is not None and time.monotonic() >= stage_deadline


def stable_item_identity(title: str = "", doi_or_link: str = "") -> str:
    """Cheap DOI/title identity usable before expensive classification or page parsing."""
    raw = normalized(doi_or_link)
    m = re.search(r"10\.\d{4,9}/[^\s?#]+", raw)
    if m:
        return "doi:" + m.group(0).rstrip(".,)")
    return "title:" + norm_title(title)


def normalized_link(value: Any) -> str:
    return normalized(clean_text(value)).rstrip("/")


def institution_fingerprint(url: str, lastmod: dt.date | None) -> str:
    """Stable page fingerprint; a changed sitemap lastmod permits a revisit."""
    return f"{normalized_link(url)}|{lastmod.isoformat() if lastmod else ''}"


def rotating_batch(items: list[Any], cursor: int, limit: int) -> tuple[list[Any], int, bool]:
    """Return a bounded circular slice and the next cursor.

    The cursor is persisted in radar.json, so scheduled scans continue through the
    query/source universe instead of restarting at the first item every 12 hours.
    """
    seq = list(items)
    if not seq:
        return [], 0, True
    n = len(seq) if limit <= 0 else min(len(seq), max(1, int(limit)))
    start = int(cursor or 0) % len(seq)
    # Never wrap inside one run. The final batch in a cycle is simply shorter,
    # which avoids re-requesting the first queries before the checkpoint is saved.
    end = min(len(seq), start + n)
    batch = seq[start:end]
    wrapped = end >= len(seq)
    return batch, (0 if wrapped else end), wrapped


def initial_scan_state(previous: dict[str, Any]) -> dict[str, Any]:
    """Load or initialise persistent incremental-discovery cursors."""
    old = previous.get("scan_state") if isinstance(previous, dict) else None
    source_done = previous.get("source_expansion_version") == SOURCE_EXPANSION_VERSION if isinstance(previous, dict) else False
    state_matches = (
        isinstance(old, dict)
        and old.get("version") == INCREMENTAL_STATE_VERSION
        and old.get("source_expansion_version") == SOURCE_EXPANSION_VERSION
    )
    if state_matches:
        state = dict(old)
    else:
        state = {
            "version": INCREMENTAL_STATE_VERSION,
            "source_expansion_version": SOURCE_EXPANSION_VERSION,
            "openalex_cursor": 0,
            "crossref_broad_cursor": 0,
            "crossref_priority_cursor": 0,
            "institution_cursor": 0,
            "frontier_gap_cursor": 0,
            "backfill": {
                "openalex": bool(source_done),
                "crossref_broad": bool(source_done),
                "crossref_priority": bool(source_done),
                "institutions": bool(source_done),
            },
            "completed_cycles": {
                "openalex": 0, "crossref_broad": 0, "crossref_priority": 0, "institutions": 0
            },
            "cycle_failed": {
                "openalex": False, "crossref_broad": False, "crossref_priority": False, "institutions": False
            },
            "institution_seen_fingerprints": {},
        }
    state.setdefault("backfill", {})
    state.setdefault("completed_cycles", {})
    state.setdefault("cycle_failed", {})
    if not isinstance(state.get("institution_seen_fingerprints"), dict):
        state["institution_seen_fingerprints"] = {}
    for key in ("openalex", "crossref_broad", "crossref_priority", "institutions"):
        state["backfill"].setdefault(key, False)
        state["completed_cycles"].setdefault(key, 0)
        state["cycle_failed"].setdefault(key, False)
    for key in ("openalex_cursor", "crossref_broad_cursor", "crossref_priority_cursor", "institution_cursor", "frontier_gap_cursor"):
        state[key] = int(state.get(key, 0) or 0)
    state["version"] = INCREMENTAL_STATE_VERSION
    state["source_expansion_version"] = SOURCE_EXPANSION_VERSION
    return state


def known_sets_from_previous(previous: dict[str, Any]) -> tuple[set[str], set[str], set[str]]:
    ab_ids: set[str] = set()
    ab_links: set[str] = set()
    sig_ids: set[str] = set()
    for strand in ("strand_a", "strand_b"):
        for item in previous.get(strand, []) if isinstance(previous.get(strand), list) else []:
            if not isinstance(item, dict):
                continue
            key = stable_item_identity(item.get("title", ""), item.get("link", ""))
            if key != "title:":
                ab_ids.add(key)
            link = normalized_link(item.get("link", ""))
            if link:
                ab_links.add(link)
    for item in previous.get("strand_c", []) if isinstance(previous.get("strand_c"), list) else []:
        if not isinstance(item, dict):
            continue
        title = item.get("headline", "")
        source = item.get("source", "")
        link = normalized_link(item.get("link", ""))
        key = f"signal:{normalized(source)}:{norm_title(title)}" if title and source else f"signal-link:{link}"
        if key not in {"signal::", "signal-link:"}:
            sig_ids.add(key)
    return ab_ids, ab_links, sig_ids


FRONTIER_CELL_ORDER = [
    f"{row}-{column}"
    for row in ("knowledge", "infrastructure", "conversion", "rules")
    for column in ("A", "B", "C", "D")
]


def frontier_matrix_coverage(previous: dict[str, Any]) -> tuple[dict[str, int], int, str]:
    """Use the exact browser classifier to count current 4x4 matrix occupancy.

    The repository already requires Node for the Frontier self-tests. Calling the
    same module here avoids maintaining a second Python approximation that could
    disagree with the page. Failure is non-fatal: discovery falls back to an even
    rotation and the cumulative corpus is still preserved.
    """
    empty = {key: 0 for key in FRONTIER_CELL_ORDER}
    try:
        proc = subprocess.run(
            ["node", str(FRONTIER_COVERAGE_SCRIPT)],
            cwd=ROOT,
            input=json.dumps(previous, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        payload = json.loads(proc.stdout or "{}")
        raw_counts = payload.get("counts") if isinstance(payload, dict) else {}
        counts = {
            key: max(0, int(raw_counts.get(key, 0) or 0)) if isinstance(raw_counts, dict) else 0
            for key in FRONTIER_CELL_ORDER
        }
        qualifying = max(0, int(payload.get("qualifying", sum(counts.values())) or 0)) if isinstance(payload, dict) else sum(counts.values())
        return counts, qualifying, ""
    except Exception as exc:
        return empty, 0, f"{type(exc).__name__}: {str(exc)[:160]}"


def frontier_gap_plan(previous: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Select the sparsest Frontier cells for extra weak-signal discovery.

    Counts come from the exact Sovereignty-Frontier classifier. Empty cells are
    therefore first, followed by under-represented cells. A persisted cursor rotates
    ties so the same six zero-count cells are not searched forever while other gaps
    receive no attention. This changes discovery priority only; admission gates stay
    untouched and no corpus item is invented or reclassified.
    """
    counts, qualifying, error = frontier_matrix_coverage(previous)
    start = int(state.get("frontier_gap_cursor", 0) or 0) % len(FRONTIER_CELL_ORDER)
    cyclic_rank = {FRONTIER_CELL_ORDER[(start + i) % len(FRONTIER_CELL_ORDER)]: i for i in range(len(FRONTIER_CELL_ORDER))}
    ordered = sorted(FRONTIER_CELL_ORDER, key=lambda key: (counts.get(key, 0), cyclic_rank[key]))
    limit = max(0, min(len(ordered), int(CONFIG.get("frontier_gap_queries_per_scan", 6) or 0)))
    targets = ordered[:limit]
    if targets:
        last_index = FRONTIER_CELL_ORDER.index(targets[-1])
        state["frontier_gap_cursor"] = (last_index + 1) % len(FRONTIER_CELL_ORDER)
    profiles = CONFIG.get("frontier_gap_search_queries", {})
    queries = [clean_text(profiles.get(key, "")) for key in targets if isinstance(profiles, dict) and clean_text(profiles.get(key, ""))]
    return {
        "counts": counts,
        "qualifying": qualifying,
        "empty_cells": sum(1 for key in FRONTIER_CELL_ORDER if counts.get(key, 0) == 0),
        "targets": targets,
        "queries": queries,
        "classifier_error": error,
    }


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
    # V12: include the wider R&I system, not only texts that use explicit policy language.
    "research and development", "r&d", "science and technology", "science & technology",
    "scientific capacity", "research capacity", "innovation capacity", "innovation performance",
    "technological capacity", "technological capabilities", "technology capabilities",
    "technology development", "industrial research", "industrial innovation", "deep tech",
    "technology transfer", "knowledge transfer", "research infrastructure", "research infrastructures",
    "scientific infrastructure", "university research", "academic research", "higher education",
    "research-intensive", "research organisation", "research organization", "research-performing",
    # Strategic technology/industrial capability is part of the R&I-adjacent scope when
    # it is linked to geopolitics/economic security. This keeps relevant nuclear, digital,
    # semiconductor, AI, quantum, biotech and infrastructure analysis without admitting
    # generic politics or generic sector news.
    "critical technology", "critical technologies", "strategic technology", "strategic technologies",
    "technology vendors", "technology infrastructure", "digital transformation", "digital technology",
    "semiconductor", "semiconductors", "artificial intelligence", "ai infrastructure",
    "quantum technology", "biotechnology", "nuclear technology", "reactor technology",
    "space technology", "clean technology", "industrial technology", "technology ecosystem",
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
    # V12: geoeconomic channels that shape R&I capacity and technology ecosystems.
    "supply chain security", "supply-chain security", "supply chain resilience",
    "strategic supply chain", "foreign investment screening", "investment screening",
    "outbound investment", "foreign subsidies", "trade restrictions", "trade controls",
    "technology controls", "techno-nationalism", "technonationalism", "great power competition",
    "great-power competition", "friendshoring", "friend-shoring", "reshoring",
    "critical raw materials", "critical minerals", "strategic trade",
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
MEMBER_STATE_SCOPE = [
    "austria", "austrian", "belgium", "belgian", "bulgaria", "bulgarian", "croatia", "croatian",
    "cyprus", "cypriot", "czechia", "czech republic", "czech", "denmark", "danish", "estonia", "estonian",
    "finland", "finnish", "france", "french", "germany", "german", "greece", "greek", "hungary", "hungarian",
    "ireland", "irish", "italy", "italian", "latvia", "latvian", "lithuania", "lithuanian",
    "luxembourg", "malta", "maltese", "netherlands", "dutch", "poland", "polish", "portugal", "portuguese",
    "romania", "romanian", "slovakia", "slovak", "slovenia", "slovenian", "spain", "spanish", "sweden", "swedish",
]
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
    "adopt", "approve", "launch", "announce", "suspend", "ban", "restrict", "curb", "tighten",
    "fund", "funding", "invest", "investment", "award", "back", "sign", "agree", "deal",
    "partner", "partnership", "collaborat", "memorandum", "mou", "delay", "stall", "cancel",
    "scrap", "reverse", "withdraw", "open", "close", "create", "build", "expand", "scale",
    "plan", "propose", "seek", "target", "urge", "warn", "move", "set to", "rules",
    "regulation", "law", "policy", "programme", "program", "strategy", "framework",
    "dataset", "data show", "survey", "report finds", "finds", "shows", "rises", "falls",
    "increase", "decrease", "cuts", "joins", "sanction", "screening", "investigation", "probe",
    "blocks", "blocked", "agreement", "association", "factory", "plant", "facility", "lab",
    "centre", "center", "supercomputer", "data centre", "data center", "ai factory", "chips act",
    "export control", "licens", "visa", "researcher", "talent", "standard", "patent", "acquisition",
]

WATCH_SIGNAL_THEMES = {
    "research security / foreign interference",
    "technology sovereignty / strategic autonomy",
    "EU–China S&T cooperation / de-risking",
    "export controls / dual use",
    "fragmentation of global science",
    "transatlantic / US–China S&T competition",
    "critical and emerging technologies",
    "economic security and R&I",
    "R&I competitiveness / technological capabilities",
    "supply chains / strategic dependencies",
    "Horizon Europe / FP10 international participation",
    "science diplomacy",
}
GEO_ACTORS = [
    "china", "chinese", "united states", "u.s.", " us ", "russia", "russian", "japan",
    "south korea", "korea", "taiwan", "india", "nato", "g7", "g20", "united kingdom", "uk",
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
    "R&I competitiveness / technological capabilities": ["innovation capacity", "innovation competitiveness", "technological capabilities", "scientific capacity", "research and development", "r&d", "deep tech", "industrial innovation"],
    "supply chains / strategic dependencies": ["supply chain security", "supply chain resilience", "strategic dependency", "strategic dependencies", "critical raw materials", "critical minerals", "friendshoring", "reshoring"],
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


def bounded_matches(text: str, phrases: Iterable[str]) -> list[str]:
    """Match scope terms as whole words/phrases, avoiding e.g. German in germanium."""
    low = normalized(text)
    found = []
    for phrase in phrases:
        p = normalized(phrase)
        if not p:
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", low) and phrase not in found:
            found.append(phrase)
    return found


def has_eu_word(text: str) -> bool:
    return bool(re.search(r"\beu\b", normalized(text)))


def eu_evidence(title: str, abstract: str, body: str) -> tuple[str | None, list[str]]:
    """Classify EU/European relevance without requiring literal 'EU' wording everywhere.

    V12 treats Europe and EU member states as first-order scope when they are part of
    the title/abstract. This is intentionally broader than V11, which missed relevant
    work phrased as 'European innovation', 'German research', etc. The substantive
    R&I + geopolitical gates still have to pass, so a bare Europe mention cannot admit
    an item by itself.
    """
    ta = f"{title}. {abstract}"
    direct = distinct_matches(ta, EU_DIRECT)
    generic = distinct_matches(ta, EU_GENERIC)
    member = bounded_matches(ta, MEMBER_STATE_SCOPE)
    if has_eu_word(ta):
        direct.append("EU")
    if direct or generic or member:
        evidence = direct + generic + member
        return "direct", list(dict.fromkeys(evidence))[:4]

    full = f"{ta}. {body[:50000]}"
    direct_body = distinct_matches(full, EU_DIRECT)
    generic_body = distinct_matches(full, EU_GENERIC)
    member_body = bounded_matches(full, MEMBER_STATE_SCOPE)
    strong_body_scope = distinct_matches(full, [
        "european commission", "european parliament", "horizon europe", "fp10",
        "european research area", "european economic security", "eu research",
        "eu innovation", "eu science", "eu technology",
    ])
    eu_count = len(re.findall(r"\beu\b", normalized(full)))
    # Body-only scope remains stricter than title/abstract scope: one passing 'EU'
    # mention is not enough. A specific R&I/EU institution/programme can be enough,
    # otherwise require repeated or multiple European scope signals.
    combined_body = direct_body + generic_body + member_body
    if strong_body_scope or eu_count >= 2 or len(set(combined_body)) >= 2:
        evidence = strong_body_scope + combined_body
        return "direct", list(dict.fromkeys(evidence))[:4]

    # Derived EU relevance still requires an explicit implication/comparator sentence;
    # generic words such as 'policy' or 'strategy' alone do not establish relevance.
    derived_cues = [
        "implication for", "implications for", "consequence for", "consequences for",
        "for europe", "for the eu", "for european policymakers", "for eu policymakers",
        "europe should", "eu should", "europe needs", "eu needs", "europe must", "eu must",
        "lessons for europe", "lessons for the eu", "relevant for europe", "relevant for the eu",
        "affects europe", "affects the eu", "matters for europe", "matters for the eu",
        "what this means for europe", "what this means for the eu",
        "policy options for europe", "policy options for the eu", "strategy for europe",
        "strategy for the eu", "recommendations for europe", "recommendations for the eu",
    ]
    for s in split_sentences(full):
        if contains_any(s, EU_GENERIC) or bool(bounded_matches(s, MEMBER_STATE_SCOPE)) or has_eu_word(s):
            if contains_any(s, derived_cues):
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


def gate_scope(title: str, abstract: str, body: str, source_tier: int, source_kind: str = "general") -> dict[str, Any]:
    """Return balanced strand evidence.

    Discovery keywords never admit an item on their own.  Strand A still requires
    substantive R&I/related-system evidence, substantive geopolitical/economic-security
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

    # V17: relevance must be substantive, not incidental.  Bare occurrences of words
    # such as technology, research or policy in a long political document cannot create
    # Strand A by themselves.  Scholarly items are judged on title+abstract, while
    # institutional reports may establish one side deeper in the document if the other
    # side is explicit and a supported bridge exists.
    ri_substantive = bool(ri_ta) or len(set(ri_full)) >= 2 or (
        source_tier <= 2 and bool(ri_full) and bool(policy_full)
    ) or (len(set(ri_generic_ta)) >= 2 and len(set(policy_ta)) >= 2)
    geo_substantive = bool(geo_ta) or len(set(geo_full)) >= 2 or (
        source_tier <= 2 and bool(geo_full)
    )
    if source_kind == "scholarly":
        # Crossref/OpenAlex records often expose only title+abstract.  Requiring both
        # substantive families there sharply improves precision and prevents unrelated
        # education/environmental futures papers from slipping in through generic terms.
        ri_substantive = bool(ri_ta)
        geo_substantive = bool(geo_ta)

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
        and evidence_total >= 2
        and (ri_ta or geo_ta)
        and ri_substantive
        and geo_substantive
    )
    if source_kind == "scholarly":
        mixed_bridge = bool(eu_rel and ri_ta and geo_ta)
    elif source_kind == "institutional":
        # For reports, do not let generic body text rescue a political document.  One
        # substantive side must be visible in the title/description and the other side
        # must either be explicit there too or strongly repeated in the report body.
        mixed_bridge = bool(
            eu_rel and ri_substantive and geo_substantive and (
                (ri_ta and geo_ta) or
                (ri_ta and len(set(geo_full)) >= 1) or
                (geo_ta and len(set(ri_full)) >= 2)
            )
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
    early_method_body = method_bridge_index < 32 and len(set(method_full)) >= 2
    # Tier-1 reports often put their methodology after an executive summary. Let a
    # genuine foresight+method bridge deeper in the report qualify, while keeping the
    # scholarly abstract-only path unchanged.
    tier1_deep_method = bool(source_tier == 1 and method_bridge and len(set(method_full)) >= 2)
    method_substantive = bool(explicit_method_title or method_in_ta or early_method_body or tier1_deep_method)

    # B must still be useful to R&I/S&T/strategic-policy practice.  Generic academic
    # "research" is not enough, which keeps unrelated futures papers out.
    b_context_terms = [
        "research and innovation", "research policy", "innovation policy", "science policy",
        "technology policy", "science and technology", "research and development", "r&d",
        "research security", "technology governance", "innovation governance", "public policy",
        "public sector", "government", "regulation", "strategic policy", "economic security",
        "research funding", "innovation system", "research system", "higher education",
        "university research", "research organisation", "research organization", "technology assessment",
        "industrial innovation", "deep tech", "critical technology", "critical technologies",
        "emerging technology", "artificial intelligence", "semiconductor", "quantum", "biotechnology",
    ]
    b_context = bool(ri_substantive or geo_substantive or contains_any(ta, b_context_terms) or contains_any(full[:12000], b_context_terms))

    trend_only = contains_any(title, TREND_ONLY_HINTS) and not (explicit_method_title or method_in_ta or method_bridge)

    # V17: Strand B is methodology *on the substance*, not a generic methods library.
    # It therefore requires the same EU + R&I + geopolitical/economic-security triangle
    # as Strand A, plus substantive foresight methodology.  Transferability alone is no
    # longer enough.
    b_eu_rel = eu_rel
    b_transferable = False

    a_pass = bool(ri_substantive and geo_substantive and eu_rel and bridge_supported)
    b_pass = bool(
        foresight_substantive and method_substantive and not trend_only
        and ri_substantive and geo_substantive and eu_rel and bridge_supported
    )

    overall_eu = eu_rel

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
    if deadline_reached(int(CONFIG.get("network_reserve_seconds", 90))):
        return None
    try:
        timeout = min(int(timeout), int(CONFIG.get("request_timeout_seconds", 12)))
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

    # Broad scholarly discovery: OpenAlex already classifies the venue as a journal.
    # The substantive Strand A/B gates remain the admission control, so relevant papers
    # are not lost merely because their journal was missing from a short hand-maintained list.
    if CONFIG.get("accept_broad_peer_reviewed_journals", True) and source_type == "journal" and typ in {"article", "review"}:
        return True, 2, 2.8, source_name or "Scholarly journal", "Tier 2 broad journal"

    # Preprints are allowed only from arXiv and are ranked as Tier 3.
    if typ in {"preprint", "posted-content", "working-paper", "working paper"}:
        if any(url_domain(u).endswith("arxiv.org") for u in openalex_locations(work)):
            return True, 3, 3.2, "arXiv", "Tier 3 preprint"

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
    ev = gate_scope(title, abstract, "", tier, source_kind="scholarly")
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


def collect_openalex(from_date: dt.date, warnings: list[str], queries_override: list[str] | None = None, stage_deadline: float | None = None) -> list[dict[str, Any]]:
    """Zero-config OpenAlex discovery.

    Uses the public endpoint anonymously, as earlier radar versions did.  There is
    deliberately no API-key/secret branch.  Requests are paced and retried, and
    if anonymous access is unavailable the stage stops quickly while Crossref and
    direct institutional scanning continue.
    """
    queries = list(dict.fromkeys(queries_override if queries_override is not None else (CONFIG["queries_a"] + CONFIG["queries_b"])))
    per_page = int(CONFIG.get("openalex_per_query", 60))
    workers = max(1, min(int(CONFIG.get("openalex_public_workers", 2)), 3))
    timeout = int(CONFIG.get("scholarly_api_timeout_seconds", 12))
    min_interval = float(CONFIG.get("openalex_public_min_interval_seconds", 0.30))
    retries = max(0, int(CONFIG.get("scholarly_public_retries", 2)))
    rate_lock = threading.Lock()
    last_request = [0.0]
    stop_public = threading.Event()

    def wait_slot() -> None:
        with rate_lock:
            now = time.monotonic()
            wait = min_interval - (now - last_request[0])
            if wait > 0:
                time.sleep(wait)
            last_request[0] = time.monotonic()

    def fetch_query(q: str) -> tuple[list[dict[str, Any]], str | None]:
        if stop_public.is_set():
            return [], "public endpoint unavailable"
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            return [], "budget"
        params = {
            "search": q,
            "filter": f"from_publication_date:{from_date.isoformat()}",
            "sort": "publication_date:desc",
            "per-page": str(per_page),
        }
        for attempt in range(retries + 1):
            if stop_public.is_set():
                return [], "public endpoint unavailable"
            wait_slot()
            try:
                r = SESSION.get("https://api.openalex.org/works", params=params, timeout=timeout)
                if r.status_code == 200:
                    works = r.json().get("results", [])
                    out = []
                    for work in works:
                        if bool(CONFIG.get("skip_known_items_before_classification", True)):
                            title0 = clean_text(work.get("title") or work.get("display_name"))
                            doi0 = clean_text(work.get("doi"))
                            if stable_item_identity(title0, doi0) in KNOWN_AB_IDENTITIES:
                                continue
                        item = candidate_from_openalex(work)
                        if item:
                            out.append(item)
                    return out, None
                if r.status_code in {401, 403, 409}:
                    stop_public.set()
                    return [], f"HTTP {r.status_code}; continuing with other zero-config sources"
                if r.status_code in {429, 500, 502, 503, 504} and attempt < retries:
                    retry_after = clean_text(r.headers.get("Retry-After"))
                    try:
                        delay = min(8.0, max(1.0, float(retry_after))) if retry_after else min(8.0, 1.5 * (attempt + 1))
                    except Exception:
                        delay = min(8.0, 1.5 * (attempt + 1))
                    time.sleep(delay)
                    continue
                return [], f"HTTP {r.status_code}"
            except Exception as e:
                if attempt < retries:
                    time.sleep(min(6.0, 1.5 * (attempt + 1)))
                    continue
                return [], type(e).__name__
        return [], "request failed"

    out: list[dict[str, Any]] = []
    budget_hits = 0
    endpoint_unavailable_reported = False
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(fetch_query, q) for q in queries]
        for fut in cf.as_completed(futs):
            try:
                items, err = fut.result()
                out.extend(items)
                if err == "budget":
                    budget_hits += 1
                elif err and "public endpoint unavailable" in err:
                    if not endpoint_unavailable_reported:
                        warnings.append("OpenAlex public endpoint unavailable; continuing with Crossref and direct publisher/institution scanning")
                        endpoint_unavailable_reported = True
                elif err:
                    warnings.append(f"OpenAlex {err}")
            except Exception as e:
                warnings.append(f"OpenAlex worker: {type(e).__name__}")
    if budget_hits:
        warnings.append(f"OpenAlex scan budget reached; {budget_hits} queued query/queries skipped")
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
    if CONFIG.get("accept_broad_peer_reviewed_journals", True) and journal and typ in {"journal-article", "article", "review"}:
        return True, 2, 2.9, journal, "Tier 2 broad journal", "peer-reviewed article"
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
    ev = gate_scope(title, abstract, "", tier, source_kind="scholarly")
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


def collect_crossref(from_date: dt.date, warnings: list[str], queries_override: list[str] | None = None, priority_tasks_override: list[tuple[str, str]] | None = None, stage_deadline: float | None = None) -> list[dict[str, Any]]:
    """Zero-config Crossref discovery using only the anonymous public pool.

    V17 gives scholarly literature a dedicated priority sweep. Before the broad
    query universe, it searches a curated set of journals with compact queries
    focused on the EU + R&I + geopolitics triangle. This increases recall of
    peer-reviewed work without loosening the admission gate.
    """
    queries = list(dict.fromkeys(queries_override if queries_override is not None else (CONFIG["queries_a"] + CONFIG["queries_b"])))
    rows = int(CONFIG.get("crossref_rows_per_query", 50))
    priority_rows = int(CONFIG.get("crossref_priority_journal_rows", 35))
    priority_journals = list(dict.fromkeys(CONFIG.get("crossref_priority_journals", [])))
    priority_queries = list(dict.fromkeys(CONFIG.get("crossref_priority_journal_queries", [])))
    priority_tasks = priority_tasks_override if priority_tasks_override is not None else [(j, q) for j in priority_journals for q in priority_queries]
    min_interval = float(CONFIG.get("crossref_public_min_interval_seconds", 0.80))
    timeout = int(CONFIG.get("scholarly_api_timeout_seconds", 12))
    retries = max(0, int(CONFIG.get("scholarly_public_retries", 2)))
    rate_lock = threading.Lock()
    last_request = [0.0]

    def wait_for_slot() -> None:
        with rate_lock:
            now = time.monotonic()
            wait = min_interval - (now - last_request[0])
            if wait > 0:
                time.sleep(wait)
            last_request[0] = time.monotonic()

    def fetch_query(q: str, journal: str = "") -> tuple[list[dict[str, Any]], str | None]:
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            return [], "budget"
        params = {
            "query.bibliographic": q,
            "filter": f"from-pub-date:{from_date.isoformat()}",
            "rows": priority_rows if journal else rows,
            "sort": "published",
            "order": "desc",
            "select": "DOI,title,author,publisher,container-title,published-online,published-print,published,issued,type,URL,abstract",
        }
        if journal:
            params["query.container-title"] = journal
        for attempt in range(retries + 1):
            wait_for_slot()
            try:
                r = SESSION.get("https://api.crossref.org/works", params=params, timeout=timeout)
                if r.status_code == 200:
                    works = r.json().get("message", {}).get("items", [])
                    out = []
                    for item in works:
                        if bool(CONFIG.get("skip_known_items_before_classification", True)):
                            titles0 = item.get("title") or []
                            title0 = clean_text(titles0[0] if isinstance(titles0, list) and titles0 else titles0)
                            doi0 = clean_text(item.get("DOI"))
                            if stable_item_identity(title0, doi0) in KNOWN_AB_IDENTITIES:
                                continue
                        c = candidate_from_crossref(item)
                        if c:
                            out.append(c)
                    return out, None
                if r.status_code in {429, 500, 502, 503, 504} and attempt < retries:
                    retry_after = clean_text(r.headers.get("Retry-After"))
                    try:
                        delay = min(8.0, max(1.0, float(retry_after))) if retry_after else min(8.0, 1.5 * (attempt + 1))
                    except Exception:
                        delay = min(8.0, 1.5 * (attempt + 1))
                    time.sleep(delay)
                    continue
                return [], f"HTTP {r.status_code}"
            except Exception as e:
                if attempt < retries:
                    time.sleep(min(6.0, 1.5 * (attempt + 1)))
                    continue
                return [], type(e).__name__
        return [], "request failed"

    out: list[dict[str, Any]] = []
    budget_hit = False

    if priority_tasks:
        log_progress(f"Crossref priority journal sweep: {len(priority_tasks)} rotating task(s) this run")
        for journal, q in priority_tasks:
            if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
                budget_hit = True
                break
            items, err = fetch_query(q, journal)
            out.extend(items)
            if err == "budget":
                budget_hit = True
                break
            if err:
                warnings.append(f"Crossref priority {journal}: {err}")

    if not budget_hit:
        log_progress(f"Crossref broad scholarly sweep: {len(queries)} queries")
        for q in queries:
            if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
                budget_hit = True
                break
            items, err = fetch_query(q)
            out.extend(items)
            if err == "budget":
                budget_hit = True
                break
            if err:
                warnings.append(f"Crossref {err}")

    if budget_hit:
        warnings.append("Crossref scan budget reached; remaining queued scholarly queries skipped")
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
    r = get(base + "/robots.txt", timeout=int(CONFIG.get("sitemap_timeout_seconds", 10)))
    if r:
        for line in r.text.splitlines():
            if line.lower().startswith("sitemap:"):
                urls.append(line.split(":", 1)[1].strip())
    urls.extend([base + "/sitemap.xml", base + "/sitemap_index.xml", base + "/sitemap-index.xml"])
    return list(dict.fromkeys(u for u in urls if u))[:8]


def sitemap_entries(url: str, depth: int = 0, child_budget: int | None = None) -> list[tuple[str, dt.date | None]]:
    if child_budget is None:
        child_budget = int(CONFIG.get("sitemap_child_budget", 8))
    if depth > 2 or child_budget <= 0:
        return []
    r = get(url, timeout=int(CONFIG.get("sitemap_timeout_seconds", 10)))
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
            if len(out) >= int(CONFIG.get("sitemap_max_entries", 800)):
                break
        return out[:int(CONFIG.get("sitemap_max_entries", 800))]
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


def institution_url_score(url: str, lastmod: dt.date | None, from_date: dt.date) -> int:
    """Prioritise analytical/publication pages without requiring a keyword in the URL.

    Many institutional CMSs use opaque slugs.  V10 filtered those out before reading the
    page, which was a major recall bottleneck.  Recent pages from whitelisted institutions
    now remain eligible; publication-like paths simply rank first.
    """
    low = normalized(url)
    if any(x in low for x in URL_HARD_EXCLUDE):
        return -100
    if lastmod and lastmod < from_date - dt.timedelta(days=14):
        return -100
    score = 0
    if lastmod and lastmod >= from_date:
        score += 5
    hints = [
        "publication", "publications", "report", "reports", "paper", "policy-brief", "policy_brief",
        "study", "studies", "analysis", "research", "foresight", "horizon", "scenario", "security",
        "geopolit", "economic-security", "strategic-autonomy", "sovereignty", "science-diplomacy",
        "technology", "innovation", "working-paper", "discussion-paper", "insight", "briefing",
        "research-paper", "policy-paper", "download",
    ]
    score += min(12, 3 * sum(1 for h in hints if h in low))
    if re.search(r"/20\d{2}/", low):
        score += 1
    return score


def institution_url_candidate(url: str, lastmod: dt.date | None, from_date: dt.date) -> bool:
    return institution_url_score(url, lastmod, from_date) >= 0


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
    if deadline_reached(int(CONFIG.get("network_reserve_seconds", 90))):
        return "", 0
    try:
        r = SESSION.get(url, timeout=int(CONFIG.get("pdf_timeout_seconds", 14)))
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


def parse_institution_page(url: str, source: str, tier: int, stage_deadline: float | None = None, fingerprint: str = "") -> dict[str, Any] | None:
    if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
        return None
    if bool(CONFIG.get("skip_known_institution_urls_before_fetch", True)) and normalized_link(url) in KNOWN_AB_LINKS:
        return None
    r = get(url, timeout=int(CONFIG.get("institution_page_timeout_seconds", 12)))
    if not r or "html" not in r.headers.get("content-type", "text/html"):
        return None
    if fingerprint:
        INSTITUTION_SEEN_FINGERPRINTS[fingerprint] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes").replace("+00:00", "Z")
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
    min_words = int(CONFIG.get("institution_min_words", 900))
    tier1_brief_min = int(CONFIG.get("institution_tier1_brief_min_words", 500))
    tier3_min = int(CONFIG.get("institution_tier3_min_words", 1200))
    effective_min = tier3_min if tier >= 3 else min_words
    if word_count < effective_min:
        brief_exception = tier == 1 and word_count >= tier1_brief_min and any(x in low_title for x in [
            "policy brief", "briefing", "working paper", "discussion paper", "policy paper",
            "report", "study", "analysis", "strategic", "security", "foresight", "research",
            "innovation", "technology", "science", "assessment"
        ])
        if not brief_exception:
            return None

    ev = gate_scope(title, desc, body, tier, source_kind="institutional")
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


def _discover_domain(src: dict[str, Any], from_date: dt.date, bootstrap: bool = False, stage_deadline: float | None = None) -> tuple[list[tuple[str, str, int, str]], str | None]:
    domain = src["domain"]
    entries = []
    max_entries = int(CONFIG.get("sitemap_max_entries", 800))
    if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
        return [], f"Institution discovery budget reached before {domain}"
    for sm in discover_sitemaps(domain):
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            break
        entries.extend(sitemap_entries(sm))
        if len(entries) >= max_entries:
            break
    if not entries:
        return [], f"No usable sitemap: {domain}"
    seen = set(); jobs = []
    limit_key = "institution_pages_per_domain_bootstrap" if bootstrap else "institution_pages_per_domain"
    limit = int(CONFIG.get(limit_key, CONFIG.get("institution_pages_per_domain", 24)))
    ranked = sorted(entries, key=lambda x: (institution_url_score(x[0], x[1], from_date), x[1] or dt.date.min), reverse=True)
    for u, last in ranked:
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            break
        if u in seen or institution_url_score(u, last, from_date) < 0:
            continue
        if bool(CONFIG.get("skip_known_institution_urls_before_fetch", True)) and normalized_link(u) in KNOWN_AB_LINKS:
            continue
        fp = institution_fingerprint(u, last)
        if fp in INSTITUTION_SEEN_FINGERPRINTS:
            continue
        seen.add(u)
        jobs.append((u, src["name"], int(src["tier"]), fp))
        if len(jobs) >= limit:
            break
    return jobs, None


def collect_institutions(from_date: dt.date, warnings: list[str], bootstrap: bool = False, sources_override: list[dict[str, Any]] | None = None, stage_deadline: float | None = None) -> list[dict[str, Any]]:
    jobs = []
    sources = sources_override if sources_override is not None else CONFIG["institution_sources"]
    discovery_workers = int(CONFIG.get("institution_discovery_workers", 12))
    page_workers = int(CONFIG.get("institution_page_workers", 24))
    log_progress(f"Institutional discovery: {len(sources)} rotating source(s) this run")
    with cf.ThreadPoolExecutor(max_workers=max(1, discovery_workers)) as ex:
        futs = [ex.submit(_discover_domain, src, from_date, bootstrap, stage_deadline) for src in sources]
        for fut in cf.as_completed(futs):
            try:
                found, warn = fut.result()
                jobs.extend(found)
                if warn:
                    warnings.append(warn)
            except Exception as e:
                warnings.append(f"Institution sitemap: {type(e).__name__}")
    out = []
    default_max = 1200 if bootstrap else 700
    max_key = "institution_max_pages_bootstrap" if bootstrap else "institution_max_pages"
    max_jobs = int(CONFIG.get(max_key, default_max))
    jobs = jobs[:max_jobs]
    log_progress(f"Institutional parsing: {len(jobs)} candidate page(s) queued")
    with cf.ThreadPoolExecutor(max_workers=max(1, page_workers)) as ex:
        futs = [ex.submit(parse_institution_page, u, s, t, stage_deadline, fp) for u, s, t, fp in jobs]
        for fut in cf.as_completed(futs):
            try:
                item = fut.result()
                if item:
                    out.append(item)
            except Exception as e:
                warnings.append(f"Institution page: {type(e).__name__}")
    if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
        warnings.append("Institutional report stage budget reached; remaining pages/sources will continue from the persisted cursor on later runs")
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
        return f"{eu} EU relevance; admitted after substantive R&I/related-system and geopolitics/economic-security gates passed with a supported document-level connection."
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
    if not isinstance(item, dict):
        return "title:"
    doi = normalized(item.get("_doi") or item.get("link", ""))
    m = re.search(r"10\.\d{4,9}/[^\s?#]+", doi)
    if m:
        return "doi:" + m.group(0).rstrip(".,)")
    return "title:" + norm_title(item.get("title", ""))


def dedupe_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
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
    if not isinstance(item, dict):
        return (9, 9.0, 0, 0)
    eu = 0 if item.get("eu_relevance") == "direct" else 1
    d = parse_date(item.get("date")) or dt.date.min
    return (eu, float(item.get("_source_rank", 9.0)), -d.toordinal(), -int(item.get("_confidence", 0)))


def public_item(item: dict[str, Any], *, new_this_scan: bool = False, first_seen: str | None = None) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
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
    c = data.get("strand_c") if isinstance(data.get("strand_c"), list) else []
    return bool(data.get("first_scan_complete") or data.get("last_updated") or a or b or c)


def _recover_radar_from_git(max_commits: int = 80) -> dict[str, Any]:
    """Find the strongest recent saved radar in Git history.

    This protects the cumulative A/B corpus when an upgrade ZIP contains a
    reset/pending radar.json.  We inspect recent ancestors and prefer the
    candidate with the largest saved A+B+C corpus, breaking ties by recency.
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
        c = data.get("strand_c") if isinstance(data.get("strand_c"), list) else []
        score = len(a) + len(b) + len(c)
        candidate = (score, -recency_index, data)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return best[2] if best else {}


def _augment_with_git_history(current: dict[str, Any], max_commits: int = 120) -> dict[str, Any]:
    """Union the live corpus with earlier radar.json versions in Git history.

    Earlier V9 scans replaced Strand C on every run, so simply preserving the current
    file would not restore signals that disappeared yesterday.  This history union
    repairs that earlier loss and keeps the corpus monotonic afterwards.
    Current copies win when an item is rediscovered; missing historical items are added.
    """
    if not _valid_saved_radar(current):
        return current
    try:
        revs = subprocess.run(
            ["git", "rev-list", f"--max-count={max_commits}", "HEAD", "--", "radar.json"],
            cwd=ROOT, capture_output=True, text=True, timeout=12, check=True,
        ).stdout.splitlines()
    except Exception:
        return current

    out = dict(current)
    maps: dict[str, dict[str, dict[str, Any]]] = {"strand_a": {}, "strand_b": {}, "strand_c": {}}
    for strand in ("strand_a", "strand_b"):
        for item in current.get(strand, []) if isinstance(current.get(strand), list) else []:
            maps[strand][identity(internalize_previous(item))] = dict(item)
    for item in current.get("strand_c", []) if isinstance(current.get("strand_c"), list) else []:
        maps["strand_c"][signal_identity(item)] = dict(item)

    for rev in revs:
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
        for strand in ("strand_a", "strand_b", "strand_c"):
            items = data.get(strand) if isinstance(data.get(strand), list) else []
            for item in items:
                key = signal_identity(item) if strand == "strand_c" else identity(internalize_previous(item))
                if not key or key in {"title:", "signal::", "signal-link:"}:
                    continue
                existing = maps[strand].get(key)
                if existing is None:
                    restored = dict(item)
                    restored["new_this_scan"] = False
                    maps[strand][key] = restored
                else:
                    # Preserve the earliest known first_seen timestamp when available.
                    old_seen = str(item.get("first_seen") or "")
                    cur_seen = str(existing.get("first_seen") or "")
                    if old_seen and (not cur_seen or old_seen < cur_seen):
                        existing["first_seen"] = old_seen

    out["strand_a"] = list(maps["strand_a"].values())
    out["strand_b"] = list(maps["strand_b"].values())
    out["strand_c"] = sorted(maps["strand_c"].values(), key=lambda x: str(x.get("date", "")), reverse=True)
    return out


def _sanitize_saved_radar(data: Any) -> tuple[dict[str, Any], dict[str, int]]:
    """Return a safe cumulative radar and counts of malformed rows removed.

    A scanner run must never die because an older radar.json (or an older Git
    revision) contains a null/string/list entry where a publication object is
    expected.  V15 sanitises only structure; it does not delete valid content.
    """
    out = dict(data) if isinstance(data, dict) else {}
    removed: dict[str, int] = {}
    for strand in ("strand_a", "strand_b", "strand_c"):
        raw = out.get(strand) if isinstance(out.get(strand), list) else []
        clean = [dict(item) for item in raw if isinstance(item, dict)]
        removed[strand] = len(raw) - len(clean)
        out[strand] = clean
    return out, removed


def _saved_corpus_size(data: Any) -> int:
    if not isinstance(data, dict):
        return 0
    return sum(
        len(data.get(k, [])) if isinstance(data.get(k), list) else 0
        for k in ("strand_a", "strand_b", "strand_c")
    )


def _merge_saved_snapshots(current: dict[str, Any], recovered: dict[str, Any]) -> dict[str, Any]:
    """Union two saved snapshots, keeping current metadata but never losing corpus rows.

    This is intentionally limited to the strongest recovered snapshot rather than
    walking/unioning every historical radar on every scan.  It makes a complete
    repository ZIP safe to upload over an existing repository even when the ZIP's
    bundled radar.json is older than the live one: the immediately preceding,
    larger Git snapshot is recovered automatically on the next scan.
    """
    cur, _ = _sanitize_saved_radar(current)
    rec, _ = _sanitize_saved_radar(recovered)
    out = dict(cur)

    for strand in ("strand_a", "strand_b"):
        merged: dict[str, dict[str, Any]] = {}
        # Recovered first, current second so current copy wins on rediscovery.
        for item in rec.get(strand, []) + cur.get(strand, []):
            if not isinstance(item, dict):
                continue
            key = identity(internalize_previous(item))
            if not key or key == "title:":
                continue
            saved = dict(item)
            saved["new_this_scan"] = False
            merged[key] = saved
        out[strand] = list(merged.values())

    merged_c: dict[str, dict[str, Any]] = {}
    for item in rec.get("strand_c", []) + cur.get("strand_c", []):
        if not isinstance(item, dict):
            continue
        key = signal_identity(item)
        if not key or key in {"signal::", "signal-link:"}:
            continue
        saved = dict(item)
        saved["new_this_scan"] = False
        merged_c[key] = saved
    out["strand_c"] = sorted(merged_c.values(), key=lambda x: str(x.get("date", "")), reverse=True)

    # If this is a repeated V17.2 whole-repository upload, keep the newer live
    # incremental checkpoint as well as its corpus. A bundle seed must not reset
    # already-advanced source cursors back to zero. Future state versions do not
    # cross this boundary because their version marker will differ.
    rec_state = rec.get("scan_state") if isinstance(rec, dict) else None
    if isinstance(rec_state, dict) and rec_state.get("version") == INCREMENTAL_STATE_VERSION:
        out["scan_state"] = dict(rec_state)
        out["incremental_state_version"] = INCREMENTAL_STATE_VERSION

    return out


def load_previous() -> dict[str, Any]:
    """Load the cumulative corpus and protect it from an older full-repository upload.

    Normal scans trust the live radar.json.  We also inspect recent Git history for
    one strongest snapshot.  Only when that snapshot contains a larger corpus than
    the bundled/current file do we merge it back.  This keeps normal scans fast while
    allowing a true *whole repository* ZIP (including radar.json) to be uploaded
    without erasing a newer A/B/C corpus already present in the repository history.
    """
    try:
        current = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    except Exception:
        current = {}

    if _valid_saved_radar(current):
        clean, removed = _sanitize_saved_radar(current)
        bad = sum(removed.values())
        if bad:
            print(f"Ignored {bad} malformed historical radar row(s) safely: {removed}.", flush=True)

        # A complete repository ZIP carries an explicit one-run seed marker.
        # Only that upgrade case checks Git history; ordinary valid live radars
        # retain the V15 fast path and never walk history on every scan.
        if bool(current.get("repository_bundle_seed")):
            recovered = _recover_radar_from_git(max_commits=40)
            if recovered and _saved_corpus_size(recovered) > _saved_corpus_size(clean):
                before = _saved_corpus_size(clean)
                clean = _merge_saved_snapshots(clean, recovered)
                print(
                    "Recovered a larger pre-upload radar corpus from Git history "
                    f"({before} -> {_saved_corpus_size(clean)} saved A+B+C rows).",
                    flush=True,
                )
        clean.pop("repository_bundle_seed", None)
        return clean

    recovered = _recover_radar_from_git(max_commits=40)
    if recovered:
        clean, removed = _sanitize_saved_radar(recovered)
        print(
            "Recovered prior cumulative radar corpus from Git history "
            f"(A={len(clean.get('strand_a', []))}, "
            f"B={len(clean.get('strand_b', []))}, "
            f"C={len(clean.get('strand_c', []))}).",
            flush=True,
        )
        if sum(removed.values()):
            print(f"Ignored malformed recovered rows safely: {removed}.", flush=True)
        return clean

    clean, _ = _sanitize_saved_radar(current)
    return clean


def internalize_previous(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    x = dict(item)
    x["_themes"] = themes_for(f"{x.get('title','')} {x.get('summary','')}")
    tier = str(x.get("source_tier") or "")
    x["_source_rank"] = 1.0 if "Tier 1" in tier else 2.4 if "comparable" in tier else 2.0 if "Tier 2" in tier else 3.0
    x["_confidence"] = 0
    x["_doi"] = normalized(x.get("link", ""))
    x["_preprint"] = x.get("type") == "preprint"
    return x


def _saved_source_kind(item: dict[str, Any]) -> str:
    typ = normalized(item.get("type", ""))
    if any(x in typ for x in ["peer-reviewed", "journal", "preprint", "article"]):
        return "scholarly"
    return "institutional"


def _saved_tier(item: dict[str, Any]) -> int:
    tier = normalized(item.get("source_tier", ""))
    if "tier 1" in tier:
        return 1
    if "tier 2" in tier or "comparable" in tier:
        return 2
    return 3


def revalidate_saved_ab(previous: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    """One-time V17 quality migration for the cumulative A/B corpus.

    The radar remains cumulative for valid material, but items admitted by older, looser
    rules are removed when their stored title+summary no longer establishes the required
    EU + R&I + geopolitical substance.  Strand C is untouched.
    """
    out = dict(previous) if isinstance(previous, dict) else {}
    removed = {"strand_a": 0, "strand_b": 0}
    for strand_key, pass_key in (("strand_a", "a_pass"), ("strand_b", "b_pass")):
        kept = []
        for item in out.get(strand_key, []) if isinstance(out.get(strand_key), list) else []:
            if not isinstance(item, dict):
                continue
            title = clean_text(item.get("title", ""))
            summary = clean_text(item.get("summary", ""))
            if not title:
                removed[strand_key] += 1
                continue
            ev = gate_scope(title, summary, "", _saved_tier(item), source_kind=_saved_source_kind(item))
            if ev.get(pass_key):
                kept.append(item)
            else:
                removed[strand_key] += 1
        out[strand_key] = kept
    return out, removed


def merge_corpus(previous: list[dict[str, Any]], new_items: list[dict[str, Any]], strand_name: str, now_iso: str) -> list[dict[str, Any]]:
    """Merge admitted A/B items without deleting earlier accepted material.

    A rediscovered item is refreshed but is not labelled NEW again.  MAX_CORPUS is
    an optional safety cap; 0 means unlimited, which is the default for this build.
    """
    merged: dict[str, dict[str, Any]] = {}
    for old in previous:
        if not isinstance(old, dict):
            continue
        internal = internalize_previous(old)
        key = identity(internal)
        if key == "title:":
            continue
        internal["new_this_scan"] = False
        merged[key] = internal
    new_ids: set[str] = set()
    for item in new_items:
        if not isinstance(item, dict):
            continue
        if item.get("strand") not in {strand_name, "both"}:
            continue
        key = identity(item)
        if key == "title:":
            continue
        existing = merged.get(key)
        if existing is None:
            new_ids.add(key)
        first_seen = existing.get("first_seen") if existing else now_iso
        merged[key] = {**item, "first_seen": first_seen, "new_this_scan": key in new_ids}
    vals = list(merged.values())
    vals.sort(key=lambda x: (not bool(x.get("new_this_scan")),) + rank_candidate(x))
    if MAX_CORPUS > 0:
        vals = vals[:MAX_CORPUS]
    return [public_item(x, new_this_scan=identity(x) in new_ids, first_seen=x.get("first_seen")) for x in vals]


def signal_identity(item: dict[str, Any]) -> str:
    """Stable identity for Strand C news signals."""
    if not isinstance(item, dict):
        return "signal-link:"
    headline = norm_title(item.get("headline", ""))
    source = normalized(item.get("source", ""))
    if headline:
        return f"signal:{source}:{headline}"
    link = normalized(item.get("link", ""))
    return f"signal-link:{link}"


def merge_signal_corpus(previous: list[dict[str, Any]], new_items: list[dict[str, Any]], now_iso: str) -> list[dict[str, Any]]:
    """Keep every previously admitted weak signal and append newly admitted ones."""
    merged: dict[str, dict[str, Any]] = {}
    for old in previous:
        if not isinstance(old, dict):
            continue
        x = dict(old)
        key = signal_identity(x)
        if key in {"signal::", "signal-link:"}:
            continue
        x["new_this_scan"] = False
        merged[key] = x

    new_ids: set[str] = set()
    for item in new_items:
        if not isinstance(item, dict):
            continue
        key = signal_identity(item)
        if key in {"signal::", "signal-link:"}:
            continue
        existing = merged.get(key)
        if existing is None:
            new_ids.add(key)
        first_seen = existing.get("first_seen") if existing else now_iso
        merged[key] = {**item, "first_seen": first_seen, "new_this_scan": key in new_ids}

    vals = list(merged.values())
    # New items first, then newest publication date first. Stable sorts keep date order within each group.
    vals.sort(key=lambda x: str(x.get("date", "")), reverse=True)
    vals.sort(key=lambda x: not bool(x.get("new_this_scan")))
    if MAX_CORPUS > 0:
        vals = vals[:MAX_CORPUS]
    return [public_item(x, new_this_scan=signal_identity(x) in new_ids, first_seen=x.get("first_seen")) for x in vals]


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


def eu_news_scope(text: str) -> bool:
    full = normalized(text)
    return bool(has_eu_word(full) or contains_any(full, EU_DIRECT + EU_GENERIC) or bounded_matches(full, MEMBER_STATE_SCOPE))


def strong_watch_signal_text(text: str, themes: Iterable[str] | None = None) -> bool:
    """Balanced Strand-C gate.

    EU/member-state developments can qualify with a clear R&I + strategic theme bridge.
    Non-EU developments need both R&I and geopolitical/economic-security evidence plus a
    salient actor. This lets the radar catch external moves that can affect Europe without
    turning Strand C into a general technology-news feed.
    """
    full = normalized(text)
    found = set(themes or themes_for(full)) & WATCH_SIGNAL_THEMES
    if not found:
        return False
    ri = contains_any(full, RI_STRONG + RI_GENERIC) or bool(found & {
        "research security / foreign interference",
        "critical and emerging technologies",
        "economic security and R&I",
        "R&I competitiveness / technological capabilities",
        "Horizon Europe / FP10 international participation",
        "science diplomacy",
    })
    geo = contains_any(full, GEO_STRONG) or bool(found & {
        "research security / foreign interference",
        "technology sovereignty / strategic autonomy",
        "EU–China S&T cooperation / de-risking",
        "export controls / dual use",
        "fragmentation of global science",
        "transatlantic / US–China S&T competition",
        "supply chains / strategic dependencies",
    })
    if eu_news_scope(full):
        # For an EU/member-state event, strategic capacity building in critical technologies
        # is sufficient even when a headline does not use the word "geopolitics".
        strategic_capacity = any(x in full for x in [
            "critical technology", "semiconductor", "chips", "quantum", "biotech",
            "artificial intelligence", " ai ", "supercomputer", "ai factory", "cloud",
            "critical raw materials", "research security", "horizon europe", "economic security",
            "strategic autonomy", "sovereignty", "dependency", "supply chain",
        ])
        return ri and (geo or strategic_capacity)
    actors = distinct_matches(full, GEO_ACTORS)
    return ri and geo and bool(actors)


def factual_news(title: str, desc: str) -> bool:
    full = normalized(f"{title} {desc}")
    if any(x in full for x in NEWS_EXCLUDE):
        return False
    if not any(x in full for x in NEWS_EVENT_TERMS):
        return False
    themes = themes_for(full)
    return strong_watch_signal_text(full, themes)


def news_queries(domain: str, lookback_hours: int) -> list[str]:
    days = max(2, min(30, (int(lookback_hours) + 23) // 24))
    when = f"when:{days}d"
    return [
        f'site:{domain} (research OR science OR innovation OR university OR researchers OR "Horizon Europe") (security OR cooperation OR funding OR talent OR China) (EU OR Europe OR European) {when}',
        f'site:{domain} ("economic security" OR "strategic autonomy" OR sovereignty OR "export controls" OR "dual use" OR "supply chain" OR "critical raw materials") (technology OR research OR innovation) {when}',
        f'site:{domain} (semiconductor OR chips OR quantum OR biotech OR "artificial intelligence" OR "AI factory" OR supercomputer OR cloud OR "deep tech") (invest OR fund OR restrict OR partnership OR strategy OR security) (EU OR Europe OR European) {when}',
    ]


def global_news_queries(lookback_hours: int) -> list[str]:
    days = max(2, min(30, (int(lookback_hours) + 23) // 24))
    when = f"when:{days}d"
    return [f"{q} {when}" for q in CONFIG.get("news_global_queries", []) if clean_text(q)]


def feed_source(entry: Any, fallback_name: str = "", fallback_domain: str = "") -> tuple[str, str]:
    if fallback_name:
        return fallback_name, fallback_domain
    src = getattr(entry, "source", None)
    title = clean_text(getattr(src, "title", "") if src is not None else "")
    href = clean_text(getattr(src, "href", "") if src is not None else "")
    domain = urlparse(href).netloc.lower().removeprefix("www.") if href else ""
    return title, domain


def allowed_global_news_source(name: str, domain: str) -> tuple[bool, str]:
    nd = (domain or "").lower().removeprefix("www.")
    nn = norm_title(name)
    sources = CONFIG.get("news_sources", [])
    # Prefer the publisher URL. This avoids ambiguous title matches such as
    # "Science" versus "Science|Business".
    for src in sources:
        sd = str(src.get("domain", "")).lower().removeprefix("www.")
        if sd and (nd == sd or nd.endswith("." + sd)):
            return True, str(src.get("name", name))
    for src in sources:
        sn = norm_title(str(src.get("name", "")))
        if nn and sn and nn == sn:
            return True, str(src.get("name", name))
    return False, name


def collect_news(now: dt.datetime, warnings: list[str], lookback_hours: int | None = None, stage_deadline: float | None = None, coverage_queries: list[str] | None = None) -> list[dict[str, Any]]:
    lookback_hours = int(lookback_hours or NEWS_LOOKBACK_HOURS)
    start = now - dt.timedelta(hours=lookback_hours)
    workers = int(CONFIG.get("news_workers", 10))
    timeout = int(CONFIG.get("news_timeout_seconds", 10))
    per_feed = int(CONFIG.get("news_items_per_feed", 60))
    jobs: list[tuple[str, str, str, bool]] = []
    for src in CONFIG["news_sources"]:
        for q in news_queries(src["domain"], lookback_hours):
            jobs.append((src["name"], src["domain"], q, False))
    for q in global_news_queries(lookback_hours):
        jobs.append(("", "", q, True))
    days = max(2, min(30, (int(lookback_hours) + 23) // 24))
    for q in coverage_queries or []:
        if clean_text(q):
            jobs.append(("", "", f"{clean_text(q)} when:{days}d", True))

    def fetch_job(job: tuple[str, str, str, bool]) -> tuple[list[dict[str, Any]], str | None]:
        name, domain, q, is_global = job
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            return [], "budget"
        url = "https://news.google.com/rss/search?q=" + quote_plus(q) + "&hl=en-GB&gl=GB&ceid=GB:en"
        try:
            r = SESSION.get(url, timeout=timeout)
            if r.status_code != 200:
                label = domain or "global"
                return [], f"Google News {label}: HTTP {r.status_code}"
            feed = feedparser.parse(r.content)
        except Exception as e:
            label = domain or "global"
            return [], f"Google News {label}: {type(e).__name__}"
        items = []
        for e in feed.entries[:per_feed]:
            when = parse_feed_time(e)
            if not when or when < start or when > now + dt.timedelta(minutes=30):
                continue
            source_name, source_domain = feed_source(e, name, domain)
            if is_global:
                ok, canonical = allowed_global_news_source(source_name, source_domain)
                if not ok:
                    continue
                source_name = canonical
            if not source_name:
                continue
            title = clean_text(getattr(e, "title", ""))
            desc = clean_text(getattr(e, "summary", "") or getattr(e, "description", ""))
            for suffix in [source_name, source_name.replace("|", " ")]:
                if suffix and title.lower().endswith(" - " + suffix.lower()):
                    title = title[:-(len(suffix) + 3)].strip()
            if not title or not factual_news(title, desc):
                continue
            signal_key = f"signal:{normalized(source_name)}:{norm_title(title)}"
            if signal_key in KNOWN_SIGNAL_IDENTITIES:
                continue
            text = f"{title}. {desc}"
            items.append({
                "headline": title,
                "source": source_name,
                "date": when.isoformat(timespec="minutes").replace("+00:00", "Z"),
                "link": clean_text(getattr(e, "link", "")),
                "_desc": desc,
                "_themes": themes_for(text),
                "_entities": distinct_matches(text, ENTITY_TERMS + GEO_ACTORS),
            })
        return items, None

    out: list[dict[str, Any]] = []
    budget_hits = 0
    with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = [ex.submit(fetch_job, j) for j in jobs]
        for fut in cf.as_completed(futs):
            try:
                items, err = fut.result()
                out.extend(items)
                if err == "budget":
                    budget_hits += 1
                elif err:
                    warnings.append(err)
            except Exception as e:
                warnings.append(f"Google News worker: {type(e).__name__}")
    if budget_hits:
        warnings.append(f"News scan budget reached; {budget_hits} queued query/queries skipped")
    seen = set(); unique = []
    for x in sorted(out, key=lambda z: z["date"], reverse=True):
        key = (norm_title(x["headline"]), norm_title(x["source"]))
        if key not in seen:
            seen.add(key); unique.append(x)
    return unique


def signal_relation(text: str) -> str:
    low = normalized(text)
    if any(w in low for w in ["stall", "delay", "cancel", "scrap", "reverse", "withdraw", "fail", "collapse", "reject", "block", "cut"]):
        return "contradicts"
    if any(w in low for w in ["accelerat", "expand", "surge", "increase", "boost", "fast-track", "scale up", "intensif", "invest", "fund"]):
        return "accelerates"
    if any(w in low for w in ["dataset", "data show", "survey", "finds", "evidence", "shows", "rise", "fall", "measur"]):
        return "confirms"
    return "instantiates"


def signal_kind(text: str) -> str:
    low = normalized(text)
    if any(w in low for w in ["ban", "restrict", "sanction", "export control", "screening", "probe", "investigation", "security rule", "licens"]):
        return "restriction / security"
    if any(w in low for w in ["invest", "fund", "factory", "plant", "facility", "supercomputer", "ai factory", "capacity", "build"]):
        return "investment / capacity"
    if any(w in low for w in ["partner", "cooperat", "collaborat", "agreement", "association", "memorandum", "mou", "join"]):
        return "cooperation / alignment"
    if any(w in low for w in ["researcher", "talent", "visa", "university", "academic", "mobility"]):
        return "research / talent"
    if any(w in low for w in ["supply chain", "critical raw material", "critical mineral", "acquisition", "market", "deal"]):
        return "market / supply chain"
    return "policy / strategy"


def signal_why(theme: str, kind: str) -> str:
    explanations = {
        "research security / foreign interference": "This could change how European research organisations manage international collaboration, access, openness and security.",
        "technology sovereignty / strategic autonomy": "This affects Europe's ability to build, access and control strategic technology capacity rather than depend on external suppliers.",
        "EU–China S&T cooperation / de-risking": "This may shift the risk–reward balance of EU–China research, technology and innovation cooperation.",
        "export controls / dual use": "This can alter access to technologies, equipment, knowledge and collaboration channels that matter for European R&I.",
        "fragmentation of global science": "This is evidence that international science is becoming more segmented, raising collaboration and access risks for Europe.",
        "transatlantic / US–China S&T competition": "This may reshape Europe's room for manoeuvre between US technology-security rules and Chinese capabilities, markets and partnerships.",
        "critical and emerging technologies": "This may affect European access, investment or capability-building in a technology that is becoming strategically important.",
        "economic security and R&I": "This links research and innovation capacity more directly to economic-security policy, funding and strategic dependencies.",
        "R&I competitiveness / technological capabilities": "This may change Europe's relative research and innovation capacity in technologies that increasingly shape geopolitical power.",
        "supply chains / strategic dependencies": "This could alter Europe's exposure to strategic inputs, infrastructure or technology supply chains.",
        "Horizon Europe / FP10 international participation": "This could change participation, funding or international cooperation in EU research programmes.",
        "science diplomacy": "This may create, narrow or redirect channels for scientific cooperation in a more geopolitical environment.",
    }
    return explanations.get(theme, f"This is a current {kind} development with a plausible effect on Europe's research, innovation or strategic technology position.")


def anchor_news(news: list[dict[str, Any]], ab_corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    internals = [internalize_previous(x) for x in ab_corpus if isinstance(x, dict)]
    internals = [x for x in internals if identity(x) != "title:"]
    theme_counts = Counter(t for x in internals for t in x.get("_themes", []))
    recurring = {t for t, c in theme_counts.items() if c >= 2}
    supported_specific = {t for t, c in theme_counts.items() if c >= 1 and t in SPECIFIC_ANCHOR_THEMES}
    anchored = []
    for n in news:
        nthemes = set(n.get("_themes", [])) & WATCH_SIGNAL_THEMES
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
            aentities = set(distinct_matches(a.get("title", "") + " " + a.get("summary", ""), ENTITY_TERMS + GEO_ACTORS))
            entity_overlap = len(nentities & aentities)
            broad_only = shared == {"critical and emerging technologies"}
            if broad_only and entity_overlap == 0 and jacc < 0.045:
                continue
            score = 3.0 * len(shared) + 1.4 * entity_overlap + 8.0 * jacc
            if any(t in SPECIFIC_ANCHOR_THEMES for t in shared):
                score += 1.0
            if best is None or score > best[0]:
                best = (score, a, sorted(shared))
        anchor = ""; score = 0.0; shared_themes: list[str] = []; anchor_basis = ""
        if best and best[0] >= 2.35:
            score, a, shared_themes = best
            anchor = f"{a['title']} (Strand {a['strand']})"
            anchor_basis = "publication"
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
                anchor_basis = "evidence-theme"
        # V16: A thin A/B corpus must not suppress genuine weak signals. A strong event can
        # enter through a curated strategic watch theme; the UI clearly labels this basis.
        if not anchor and strong_watch_signal_text(n["headline"] + " " + n.get("_desc", ""), nthemes):
            priority = [
                "research security / foreign interference", "export controls / dual use",
                "EU–China S&T cooperation / de-risking", "Horizon Europe / FP10 international participation",
                "technology sovereignty / strategic autonomy", "supply chains / strategic dependencies",
                "economic security and R&I", "transatlantic / US–China S&T competition",
                "R&I competitiveness / technological capabilities", "critical and emerging technologies",
                "fragmentation of global science", "science diplomacy",
            ]
            theme = next((t for t in priority if t in nthemes), sorted(nthemes)[0])
            shared_themes = [theme]
            anchor = f"Strategic watch theme: {theme}"
            anchor_basis = "watch-theme"
            score = 2.15
        if not anchor:
            continue
        text = n["headline"] + " " + n.get("_desc", "")
        sig = signal_relation(text)
        kind = signal_kind(text)
        theme = shared_themes[0] if shared_themes else sorted(nthemes)[0]
        what = clean_text(n["headline"])
        why = signal_why(theme, kind)
        item = {k: v for k, v in n.items() if not k.startswith("_")}
        item.update({
            "anchor": anchor,
            "anchor_basis": anchor_basis,
            "watch_theme": theme,
            "signal_type": sig,
            "signal_kind": kind,
            "what": what,
            "why_it_matters": why,
            "signal_note": what.rstrip(". ") + ". " + why,
            "_anchor_score": score,
        })
        anchored.append(item)
    anchored.sort(key=lambda x: (x.get("_anchor_score", 0), x.get("date", "")), reverse=True)
    for x in anchored:
        x.pop("_anchor_score", None)
    return anchored[:MAX_C] if MAX_C > 0 else anchored


def bootstrap_floor(today: dt.date) -> dt.date:
    return today - relativedelta(months=BOOTSTRAP_LOOKBACK_MONTHS)


def preserved_corpus_floor(previous: dict[str, Any], today: dt.date) -> dt.date:
    """Keep the earliest established corpus date while bootstrapping new installs for four months."""
    candidates = [bootstrap_floor(today)]
    saved = parse_date(previous.get("corpus_start_date"))
    if saved:
        candidates.append(saved)
    for strand in ("strand_a", "strand_b"):
        for item in previous.get(strand, []) if isinstance(previous.get(strand), list) else []:
            if not isinstance(item, dict):
                continue
            d = parse_date(item.get("date"))
            if d:
                candidates.append(d)
    return min(candidates)


def needs_source_expansion_backfill(previous: dict[str, Any]) -> bool:
    if not FORCE_SOURCE_EXPANSION_BACKFILL:
        return not bool(previous.get("last_updated"))
    if previous.get("source_expansion_version") != SOURCE_EXPANSION_VERSION:
        return True
    return False


def needs_signal_backfill(previous: dict[str, Any]) -> bool:
    """Run one wider weak-signal recovery window whenever Strand-C discovery changes."""
    return previous.get("signal_discovery_version") != SIGNAL_DISCOVERY_VERSION


def scan_from_date(previous: dict[str, Any], today: dt.date) -> tuple[dt.date, bool]:
    bootstrap = needs_source_expansion_backfill(previous)
    if bootstrap or not previous.get("last_updated"):
        # A/B source expansion always gets one full four-calendar-month pass.
        return bootstrap_floor(today), True
    try:
        last = dateparser.parse(previous["last_updated"]).date()
        return max(DATE_FLOOR, last - dt.timedelta(days=DISCOVERY_OVERLAP_DAYS)), False
    except Exception:
        return bootstrap_floor(today), True


def main() -> int:
    global DATE_FLOOR, SCAN_DEADLINE_MONO, KNOWN_AB_IDENTITIES, KNOWN_AB_LINKS, KNOWN_SIGNAL_IDENTITIES, INSTITUTION_SEEN_FINGERPRINTS
    started = time.time()
    log_progress.started = time.monotonic()
    budget_seconds = int(CONFIG.get("scan_budget_seconds", 1200))
    SCAN_DEADLINE_MONO = time.monotonic() + budget_seconds
    now = dt.datetime.now(dt.timezone.utc)
    now_iso = now.isoformat(timespec="minutes").replace("+00:00", "Z")
    warnings: list[str] = []
    previous = load_previous()

    quality_migration = previous.get("quality_profile_version") != QUALITY_PROFILE_VERSION
    quality_removed = {"strand_a": 0, "strand_b": 0}
    if quality_migration:
        previous, quality_removed = revalidate_saved_ab(previous)
        log_progress(
            "V17 quality migration: removed "
            f"{quality_removed['strand_a']} old A and {quality_removed['strand_b']} old B item(s) "
            "that no longer meet the EU + R&I + geopolitics substance gate"
        )

    DATE_FLOOR = preserved_corpus_floor(previous, now.date())
    KNOWN_AB_IDENTITIES, KNOWN_AB_LINKS, KNOWN_SIGNAL_IDENTITIES = known_sets_from_previous(previous)
    state = initial_scan_state(previous)
    INSTITUTION_SEEN_FINGERPRINTS = dict(state.get("institution_seen_fingerprints", {}))
    frontier_focus = frontier_gap_plan(previous, state)
    if frontier_focus["classifier_error"]:
        log_progress(f"Frontier coverage classifier unavailable; using rotating fallback: {frontier_focus['classifier_error']}")
    log_progress(
        f"Frontier coverage before scan: {frontier_focus['qualifying']} qualifying, "
        f"{frontier_focus['empty_cells']}/16 empty; prioritising "
        + (", ".join(frontier_focus["targets"]) if frontier_focus["targets"] else "no extra gap queries")
    )

    try:
        last = dateparser.parse(previous.get("last_updated", "")).date()
        incremental_from = max(DATE_FLOOR, last - dt.timedelta(days=DISCOVERY_OVERLAP_DAYS))
    except Exception:
        incremental_from = bootstrap_floor(now.date())
    backfill_from = bootstrap_floor(now.date())

    all_queries = list(dict.fromkeys(CONFIG.get("queries_a", []) + CONFIG.get("queries_b", [])))
    oa_batch, state["openalex_cursor"], oa_wrapped = rotating_batch(
        all_queries, state.get("openalex_cursor", 0), int(CONFIG.get("openalex_queries_per_scan", 40))
    )
    cr_batch, state["crossref_broad_cursor"], cr_broad_wrapped = rotating_batch(
        all_queries, state.get("crossref_broad_cursor", 0), int(CONFIG.get("crossref_broad_queries_per_scan", 35))
    )
    priority_tasks_all = [
        (journal, query)
        for journal in list(dict.fromkeys(CONFIG.get("crossref_priority_journals", [])))
        for query in list(dict.fromkeys(CONFIG.get("crossref_priority_journal_queries", [])))
    ]
    cr_priority_batch, state["crossref_priority_cursor"], cr_priority_wrapped = rotating_batch(
        priority_tasks_all,
        state.get("crossref_priority_cursor", 0),
        int(CONFIG.get("crossref_priority_tasks_per_scan", 45)),
    )
    institution_sources_all = list(CONFIG.get("institution_sources", []))
    inst_batch, state["institution_cursor"], inst_wrapped = rotating_batch(
        institution_sources_all,
        state.get("institution_cursor", 0),
        int(CONFIG.get("institution_sources_per_scan", 18)),
    )

    oa_backfill = not bool(state["backfill"].get("openalex"))
    cr_backfill = not (
        bool(state["backfill"].get("crossref_broad"))
        and bool(state["backfill"].get("crossref_priority"))
    )
    inst_backfill = not bool(state["backfill"].get("institutions"))
    bootstrap_ab = oa_backfill or cr_backfill or inst_backfill
    oa_from = backfill_from if oa_backfill else incremental_from
    cr_from = backfill_from if cr_backfill else incremental_from
    inst_from = backfill_from if inst_backfill else incremental_from

    log_progress(
        "Scan start: persistent incremental mode; "
        f"OpenAlex {len(oa_batch)}/{len(all_queries)} query(s) from {oa_from.isoformat()}, "
        f"Crossref {len(cr_batch)} broad + {len(cr_priority_batch)} priority task(s) from {cr_from.isoformat()}, "
        f"institutions {len(inst_batch)}/{len(institution_sources_all)} source(s) from {inst_from.isoformat()}; "
        f"hard budget {budget_seconds//60} min"
    )
    log_progress(
        f"Known corpus loaded before discovery: {len(KNOWN_AB_IDENTITIES)} A/B identities, "
        f"{len(KNOWN_AB_LINKS)} known A/B links, {len(KNOWN_SIGNAL_IDENTITIES)} weak-signal identities"
    )

    def safe_stage(name: str, fn, *args, **kwargs):
        try:
            log_progress(f"Starting {name}")
            result = fn(*args, **kwargs)
            log_progress(f"Finished {name}: {len(result)} admitted NEW candidate(s)")
            return result
        except Exception as e:
            warnings.append(f"{name} fatal stage error: {type(e).__name__}: {str(e)[:180]}")
            log_progress(f"{name} failed safely; preserving existing corpus and persisted cursor")
            return []

    # Weak signals, OpenAlex and Crossref start together. Each family has its own
    # time slice, so no one family can consume the complete scan runtime.
    signal_backfill = needs_signal_backfill(previous)
    first_run = not bool(previous.get("first_scan_complete"))
    news_lookback = SIGNAL_BACKFILL_HOURS if signal_backfill else (FIRST_NEWS_LOOKBACK_HOURS if first_run else NEWS_LOOKBACK_HOURS)
    log_progress(f"Weak-signal window: {news_lookback}h (recovery backfill={signal_backfill})")
    news_warnings: list[str] = []
    phase_started = time.monotonic()
    news_deadline = phase_started + int(CONFIG.get("news_stage_seconds", 240))
    oa_deadline = phase_started + int(CONFIG.get("openalex_stage_seconds", 360))
    cr_deadline = phase_started + int(CONFIG.get("crossref_stage_seconds", 450))

    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        fut_news = ex.submit(
            safe_stage, "weak-signal news", collect_news, now, news_warnings, news_lookback, news_deadline, frontier_focus["queries"]
        )
        fut_oa = ex.submit(
            safe_stage, "OpenAlex", collect_openalex, oa_from, warnings, oa_batch, oa_deadline
        )
        fut_cr = ex.submit(
            safe_stage, "Crossref", collect_crossref, cr_from, warnings, cr_batch, cr_priority_batch, cr_deadline
        )
        news = fut_news.result()
        oa = fut_oa.result()
        cr = fut_cr.result()
    warnings.extend(news_warnings)

    # Reports get a separate source rotation and time slice after the parallel phase.
    inst_deadline = time.monotonic() + int(CONFIG.get("institution_stage_seconds", 480))
    inst = safe_stage(
        "institutional reports",
        collect_institutions,
        inst_from,
        warnings,
        bootstrap=inst_backfill,
        sources_override=inst_batch,
        stage_deadline=inst_deadline,
    )

    def stage_failed(label: str, deadline: float | None = None) -> bool:
        nlabel = normalized(label)
        relevant = [normalized(w) for w in warnings if nlabel in normalized(w)]
        warning_failure = any(
            ("fatal stage error" in w) or ("budget reached" in w) or ("public endpoint unavailable" in w)
            for w in relevant
        )
        local_deadline_hit = deadline is not None and time.monotonic() >= deadline
        return warning_failure or local_deadline_hit

    oa_failed = stage_failed("openalex", oa_deadline)
    cr_failed = stage_failed("crossref", cr_deadline)
    inst_failed = stage_failed("institution", inst_deadline)

    def finish_cycle(key: str, wrapped: bool, failed: bool) -> None:
        state["cycle_failed"][key] = bool(state["cycle_failed"].get(key)) or bool(failed)
        if wrapped:
            state["completed_cycles"][key] = int(state["completed_cycles"].get(key, 0)) + 1
            if not state["cycle_failed"][key]:
                state["backfill"][key] = True
            state["cycle_failed"][key] = False

    finish_cycle("openalex", oa_wrapped, oa_failed)
    finish_cycle("crossref_broad", cr_broad_wrapped, cr_failed)
    finish_cycle("crossref_priority", cr_priority_wrapped, cr_failed)
    finish_cycle("institutions", inst_wrapped, inst_failed)

    oa = [x for x in oa if isinstance(x, dict)]
    cr = [x for x in cr if isinstance(x, dict)]
    inst = [x for x in inst if isinstance(x, dict)]
    deduped = dedupe_candidates(oa + cr + inst)
    deduped.sort(key=rank_candidate)
    new_selected = deduped[:MAX_NEW_AB] if MAX_NEW_AB > 0 else deduped

    prev_a = previous.get("strand_a", []) if isinstance(previous.get("strand_a"), list) else []
    prev_b = previous.get("strand_b", []) if isinstance(previous.get("strand_b"), list) else []
    strand_a = merge_corpus(prev_a, new_selected, "A", now_iso)
    strand_b = merge_corpus(prev_b, new_selected, "B", now_iso)

    all_ab_map = {}
    for x in strand_a + strand_b:
        if not isinstance(x, dict):
            continue
        key = identity(internalize_previous(x))
        if key != "title:":
            all_ab_map[key] = x
    ab_corpus = list(all_ab_map.values())
    current_c = anchor_news(news, ab_corpus)
    prev_c = previous.get("strand_c", []) if isinstance(previous.get("strand_c"), list) else []
    strand_c = merge_signal_corpus(prev_c, current_c, now_iso)

    previous_a_ids = {identity(internalize_previous(x)) for x in prev_a if isinstance(x, dict)}
    previous_b_ids = {identity(internalize_previous(x)) for x in prev_b if isinstance(x, dict)}
    new_a_count = sum(1 for x in strand_a if x.get("new_this_scan") and identity(internalize_previous(x)) not in previous_a_ids)
    new_b_count = sum(1 for x in strand_b if x.get("new_this_scan") and identity(internalize_previous(x)) not in previous_b_ids)
    new_c_count = sum(1 for x in strand_c if x.get("new_this_scan"))

    signal_backfill_ok = not (
        stage_failed("weak-signal", news_deadline)
        or any("news scan budget reached" in normalized(w) for w in warnings)
    )
    overall_budget_hit = deadline_reached(0)
    partial_budget_hit = any("budget reached" in normalized(w) for w in warnings)
    total_ab_live = len(oa) + len(cr) + len(inst)
    transport_failure_count = sum(
        1 for w in warnings
        if any(x in normalized(w) for x in ["connection", "timeout", "httperror", "name resolution", "http 429", "http 5"])
    )
    fatal_stage_error = any("fatal stage error" in normalized(w) for w in warnings)
    health = "degraded" if overall_budget_hit or fatal_stage_error or partial_budget_hit or (total_ab_live == 0 and len(warnings) >= 10) else "ok"
    if overall_budget_hit:
        warnings.append("Overall scan runtime budget reached; queued work was skipped safely and persisted cursors prevent restarting from query 1")

    backfill_complete = all(bool(state["backfill"].get(k)) for k in ("openalex", "crossref_broad", "crossref_priority", "institutions"))
    expansion_marker = SOURCE_EXPANSION_VERSION if backfill_complete else previous.get("source_expansion_version", "")

    if signal_backfill and not signal_backfill_ok:
        signal_marker = previous.get("signal_discovery_version", "")
        signal_backfill_complete = False
    else:
        signal_marker = SIGNAL_DISCOVERY_VERSION
        signal_backfill_complete = True

    cache_max = int(CONFIG.get("institution_seen_cache_max", 5000))
    if cache_max > 0 and len(INSTITUTION_SEEN_FINGERPRINTS) > cache_max:
        newest = sorted(INSTITUTION_SEEN_FINGERPRINTS.items(), key=lambda kv: kv[1], reverse=True)[:cache_max]
        INSTITUTION_SEEN_FINGERPRINTS = dict(newest)
    state["institution_seen_fingerprints"] = dict(INSTITUTION_SEEN_FINGERPRINTS)
    state["last_run"] = now_iso
    state["last_batches"] = {
        "openalex_queries": len(oa_batch),
        "crossref_broad_queries": len(cr_batch),
        "crossref_priority_tasks": len(cr_priority_batch),
        "institution_sources": len(inst_batch),
        "frontier_gap_queries": len(frontier_focus["queries"]),
    }
    state["frontier_coverage_before_scan"] = {
        "qualifying": frontier_focus["qualifying"],
        "empty_cells": frontier_focus["empty_cells"],
        "counts": frontier_focus["counts"],
        "targets": frontier_focus["targets"],
    }

    data = {
        "last_updated": now_iso,
        "first_scan_complete": True,
        "corpus_start_date": DATE_FLOOR.isoformat(),
        "source_expansion_version": expansion_marker,
        "quality_profile_version": QUALITY_PROFILE_VERSION,
        "quality_migration_this_run": quality_migration,
        "backfill_complete": backfill_complete,
        "signal_discovery_version": signal_marker,
        "signal_backfill_complete": signal_backfill_complete,
        "incremental_state_version": INCREMENTAL_STATE_VERSION,
        "scan_state": state,
        "zero_config_scan": True,
        "admission_profile": str(CONFIG.get("admission_profile", "balanced_relevance_v15_scan_repair")),
        "scan_health": health,
        "scan_window": {
            "ab_date_floor": DATE_FLOOR.isoformat(),
            "ab_discovery_from_this_run": min(oa_from, cr_from, inst_from).isoformat(),
            "openalex_from": oa_from.isoformat(),
            "crossref_from": cr_from.isoformat(),
            "institutions_from": inst_from.isoformat(),
            "ab_four_month_backfill_this_run": bootstrap_ab,
            "c_window_start": (now - dt.timedelta(hours=news_lookback)).isoformat(timespec="minutes").replace("+00:00", "Z"),
            "c_window_end": now_iso,
            "c_recovery_backfill_this_run": signal_backfill,
        },
        "scan_results": {
            "new_a": new_a_count,
            "new_b": new_b_count,
            "new_ab_unique": len(new_selected),
            "new_c": new_c_count,
            "c_signals": new_c_count,
            "c_signals_total": len(strand_c),
            "note_a": f"This scan added {new_a_count} new Strand A item(s). Earlier accepted items remain in the corpus." if new_a_count < 3 else "",
            "note_b": f"This scan added {new_b_count} new Strand B item(s). Earlier accepted items remain in the corpus." if new_b_count < 3 else "",
            "note_c": f"This scan added {new_c_count} new weak signal(s). The scanner uses a seven-day rolling window and keeps all earlier signals." if new_c_count < 3 else "",
            "frontier_gap_targets": frontier_focus["targets"],
            "frontier_empty_cells_before_scan": frontier_focus["empty_cells"],
        },
        "strand_a": strand_a,
        "strand_b": strand_b,
        "strand_c": strand_c,
        "stats": {
            "openalex_admitted_before_dedupe": len(oa),
            "openalex_public_anonymous": True,
            "crossref_admitted_before_dedupe": len(cr),
            "crossref_public_anonymous": True,
            "institutional_admitted_before_dedupe": len(inst),
            "scholarly_queries_a": len(CONFIG.get("queries_a", [])),
            "scholarly_queries_b": len(CONFIG.get("queries_b", [])),
            "openalex_queries_this_run": len(oa_batch),
            "crossref_broad_queries_this_run": len(cr_batch),
            "crossref_priority_tasks_this_run": len(cr_priority_batch),
            "institution_sources_this_run": len(inst_batch),
            "known_ab_identities_loaded": len(KNOWN_AB_IDENTITIES),
            "known_ab_links_loaded": len(KNOWN_AB_LINKS),
            "known_signal_identities_loaded": len(KNOWN_SIGNAL_IDENTITIES),
            "institution_page_fingerprints_cached": len(INSTITUTION_SEEN_FINGERPRINTS),
            "institution_sources_configured": len(CONFIG.get("institution_sources", [])),
            "major_scholarly_publishers_tracked": len(CONFIG.get("major_scholarly_publishers", [])),
            "priority_journals_tracked": len(CONFIG.get("crossref_priority_journals", [])),
            "priority_journal_queries": len(CONFIG.get("crossref_priority_journal_queries", [])),
            "source_expansion_backfill": bootstrap_ab,
            "backfill_complete": backfill_complete,
            "unique_ab_candidates_before_scan_limit": len(deduped),
            "news_candidates_current_window": len(news),
            "news_admitted_current_window": len(current_c),
            "news_lookback_hours": news_lookback,
            "news_sources_configured": len(CONFIG.get("news_sources", [])),
            "news_global_queries_configured": len(CONFIG.get("news_global_queries", [])),
            "frontier_gap_queries_this_run": len(frontier_focus["queries"]),
            "frontier_gap_targets_this_run": len(frontier_focus["targets"]),
            "frontier_qualifying_before_scan": frontier_focus["qualifying"],
            "frontier_empty_cells_before_scan": frontier_focus["empty_cells"],
            "frontier_coverage_classifier_ok": not bool(frontier_focus["classifier_error"]),
            "signal_recovery_backfill": signal_backfill,
            "signal_backfill_complete": signal_backfill_complete,
            "quality_removed_old_a": quality_removed.get("strand_a", 0),
            "quality_removed_old_b": quality_removed.get("strand_b", 0),
            "source_warnings": len(warnings),
            "transport_failure_warnings": transport_failure_count,
            "scan_budget_seconds": budget_seconds,
            "budget_reached": overall_budget_hit,
            "partial_stage_budget_reached": partial_budget_hit,
            "runtime_seconds": round(time.time() - started, 1),
        },
    }
    tmp_out = OUT_PATH.with_suffix(".json.tmp")
    tmp_out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_out.replace(OUT_PATH)
    log_progress(
        f"radar.json written: A={len(strand_a)} B={len(strand_b)} C={len(strand_c)} health={health}; "
        f"next cursors OA={state['openalex_cursor']} CR={state['crossref_broad_cursor']}/{state['crossref_priority_cursor']} INST={state['institution_cursor']}"
    )
    print(json.dumps(data["stats"], indent=2), flush=True)
    if warnings:
        print("Source warnings (first 40):", file=sys.stderr, flush=True)
        for w in warnings[:40]:
            print(" -", w, file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
