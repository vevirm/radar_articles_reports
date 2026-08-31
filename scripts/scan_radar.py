#!/usr/bin/env python3
"""R&I × Geopolitics + Foresight Methodology radar scanner (EU-first, balanced).

Key properties
--------------
* No API keys or paid services are required.
* Discovery is broad; admission is selective but not brittle.
* Strand A requires direct EU scope plus substantive R&I evidence and a strategic-context bridge. "Geopolitics" need not be named: technological sovereignty, dependence, competitiveness, capability, research security, talent competition, international coordination, critical infrastructure, standards and governance power can establish the strategic context when they triangulate.
* Strand B is a method-development library: a publication must contribute a new, adapted,
  extended, refined or otherwise explicitly developed futures/foresight method, or a genuinely
  forward-looking R&I/technology-analysis method, reusable for understanding the future of Strand A.
  Explicit development language is preferred; method-first papers with validation/transfer evidence can also qualify. Mere application is not enough.
* Strand C is not a general news feed: every admitted item must be a factual current development
  or new evidence/indicator capable of reframing Strand A, with a strong R&I/geopolitical bridge.
  It must be anchored to substantive Strand-A evidence; Strand-B methods never serve as weak-signal
  anchors. Once admitted, the signal is retained for six months and always remains low-evidence.
  An interesting C item that explicitly points to research, a report, data or another publication can
  trigger a bounded evidence follow-up. Any stronger source found is admitted separately through the
  ordinary A/B gates; the C record itself is never upgraded.
* Foresight-expert recall is author-led rather than institution-led: authors evidenced by admitted
  Strand-B foresight/method work receive a small rotating publication check. This changes recall only;
  their later work must still satisfy the ordinary EU R&I A/B criteria.
* Calls, facility pages, project pages, routine press/news/blog pages, events, jobs and other
  non-analytical material are rejected for A/B. A tightly bounded primary-notice route allows
  authoritative EU decisions/notifications into Strand A when the underlying source itself
  passes the normal substantive A gate.

The scanner aims for high-recall discovery with substantive admission: EU scope + R&I/related-system substance + explicit or triangulated strategic context. It does not pad.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import gzip
import html
import io
import json
import math
import os
import re
import threading
import unicodedata
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, quote_plus, urljoin, urlparse

try:
    import feedparser
except ModuleNotFoundError:  # lightweight offline/test fallback; normal installs use feedparser
    import email.utils
    import types
    class _FeedEntry(types.SimpleNamespace):
        pass
    class _FeedParserCompat:
        @staticmethod
        def parse(content):
            try:
                root = ET.fromstring(content)
            except Exception:
                return types.SimpleNamespace(entries=[])
            entries = []
            for node in root.iter():
                if localname(node.tag) not in {"item", "entry"}:
                    continue
                vals = {}
                src = None
                for ch in list(node):
                    key = localname(ch.tag)
                    txt = clean_text(" ".join(ch.itertext()))
                    if key in {"title", "link", "summary", "description", "published", "updated", "pubDate"}:
                        if key == "pubDate": key = "published"
                        if key == "link" and not txt:
                            txt = clean_text(ch.attrib.get("href"))
                        vals[key] = txt
                    elif key == "source":
                        src = types.SimpleNamespace(title=txt, href=clean_text(ch.attrib.get("url") or ch.attrib.get("href")))
                if src is not None:
                    vals["source"] = src
                entries.append(_FeedEntry(**vals))
            return types.SimpleNamespace(entries=entries)
    feedparser = _FeedParserCompat()
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from dateutil.relativedelta import relativedelta
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "radar_config.json"
OUT_PATH = ROOT / "radar.json"
FRONTIER_COVERAGE_SCRIPT = ROOT / "scripts" / "frontier_coverage.js"
PRIORITY_PEOPLE_PATH = ROOT / "priority_people.json"
CURATOR_CANDIDATE_TESTS_PATH = ROOT / "curator_candidate_tests.json"
PHRASE_RULES_PATH = ROOT / "radar_phrase_rules.json"

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    CONFIG = json.load(f)
try:
    with PHRASE_RULES_PATH.open("r", encoding="utf-8") as f:
        PHRASE_RULES = json.load(f)
except Exception:
    # The scanner remains runnable if an older checkout lacks the curator workbook export.
    PHRASE_RULES = {"strand_a": [], "strand_b": [], "strand_c_retrieval": []}

# V17.12.5 non-destructive recall repair.  Keep these additions in code rather than
# requiring a config migration: replacing this scanner file cannot reset persistent
# cursors or overwrite radar.json/config state.
RULE_FIX_INSTITUTION_SOURCES = [
    {"name": "Max Planck Institute for Intelligent Systems", "domain": "is.mpg.de", "tier": 1},
    {"name": "ELLIS Institute", "domain": "ellis.institute", "tier": 1},
    {"name": "ELLIS Network", "domain": "ellis.eu", "tier": 1},
    {"name": "ELLIS Institute Finland", "domain": "ellisinstitute.fi", "tier": 1},
    {"name": "Aalto University", "domain": "aalto.fi", "tier": 2},
    {"name": "ETH Zürich", "domain": "ethz.ch", "tier": 2},
    {"name": "United Nations", "domain": "un.org", "tier": 2},
    {"name": "International AI Safety Report", "domain": "internationalaisafetyreport.org", "tier": 2},
    {"name": "KE:SAI", "domain": "kesai.eu", "tier": 2},
    {"name": "International Telecommunication Union", "domain": "itu.int", "tier": 2},
    {"name": "Tech Europe", "domain": "tech-europe.org", "tier": 3},
    {"name": "European Commission — Migration and Home Affairs", "domain": "home-affairs.ec.europa.eu", "tier": 1},
    {"name": "European Education Area", "domain": "education.ec.europa.eu", "tier": 1},
]
RULE_FIX_FRONTIER_SOURCE_ADDITIONS = {
    "infrastructure-A": ["ellis.institute", "ellis.eu", "ellisinstitute.fi", "is.mpg.de", "kesai.eu", "aalto.fi", "ethz.ch"],
    "infrastructure-B": ["internationalaisafetyreport.org", "un.org", "itu.int", "ellis.institute", "is.mpg.de"],
    "infrastructure-C": ["kesai.eu", "ellis.institute", "ellisinstitute.fi", "is.mpg.de", "aalto.fi", "ethz.ch"],
    "infrastructure-D": ["kesai.eu", "ellis.institute", "internationalaisafetyreport.org", "un.org", "itu.int"],
    "conversion-A": ["ellis.institute", "is.mpg.de", "kesai.eu", "aalto.fi", "ethz.ch"],
    "conversion-C": ["kesai.eu", "ellis.institute", "ellisinstitute.fi"],
    "rules-B": ["internationalaisafetyreport.org", "un.org", "itu.int"],
    "rules-C": ["un.org", "itu.int", "internationalaisafetyreport.org", "ellis.institute"],
    "rules-D": ["un.org", "itu.int", "internationalaisafetyreport.org"],
    "knowledge-A": ["ellis.institute", "is.mpg.de", "ellisinstitute.fi", "aalto.fi", "ethz.ch"],
    "knowledge-C": ["home-affairs.ec.europa.eu", "education.ec.europa.eu", "euraxess.ec.europa.eu", "research-and-innovation.ec.europa.eu", "ellis.institute", "is.mpg.de", "ellisinstitute.fi", "aalto.fi"],
}

def _apply_rule_fix_source_extensions() -> None:
    sources = CONFIG.setdefault("institution_sources", [])
    existing = {
        clean_text(s.get("domain", "")).lower().removeprefix("www.")
        for s in sources if isinstance(s, dict)
    } if "clean_text" in globals() else {
        str(s.get("domain", "")).strip().lower().removeprefix("www.")
        for s in sources if isinstance(s, dict)
    }
    for src in RULE_FIX_INSTITUTION_SOURCES:
        if src["domain"] not in existing:
            sources.append(dict(src))
            existing.add(src["domain"])
    profiles = CONFIG.setdefault("frontier_gap_institution_sources", {})
    for cell, domains in RULE_FIX_FRONTIER_SOURCE_ADDITIONS.items():
        current = profiles.setdefault(cell, [])
        if not isinstance(current, list):
            current = [current] if current else []
            profiles[cell] = current
        for domain in domains:
            if domain not in current:
                current.append(domain)

_apply_rule_fix_source_extensions()

BOOTSTRAP_LOOKBACK_MONTHS = int(CONFIG.get("bootstrap_lookback_months", 4))
EXTENDED_TOP_QUALITY_LOOKBACK_MONTHS = int(CONFIG.get("extended_top_quality_lookback_months", 6))
WEAK_SIGNAL_RETENTION_MONTHS = int(CONFIG.get("weak_signal_retention_months", 6))
EXTENDED_TOP_QUALITY_SOURCES_PER_SCAN = int(CONFIG.get("extended_top_quality_sources_per_scan", 6))
EXTENDED_TOP_QUALITY_STAGE_SECONDS = int(CONFIG.get("extended_top_quality_stage_seconds", 150))
SOURCE_EXPANSION_VERSION = str(CONFIG.get("source_expansion_version", "v17-scholarly-substance"))
QUALITY_PROFILE_VERSION = str(CONFIG.get("quality_profile_version", "v17-eu-ri-geo-substance"))
INHERITED_CORPUS_AUDIT_ENABLED = bool(CONFIG.get("inherited_corpus_audit_enabled", True))
INHERITED_CORPUS_AUDIT_REFRESH = bool(CONFIG.get("inherited_corpus_audit_refresh_failures", True))
INHERITED_CORPUS_AUDIT_FAIL_CLOSED = bool(CONFIG.get("inherited_corpus_audit_fail_closed", True))
SIGNAL_DISCOVERY_VERSION = str(CONFIG.get("signal_discovery_version", "v17.17-relational-weak-signals"))
SIGNAL_QUALITY_PROFILE_VERSION = str(CONFIG.get("signal_quality_profile_version", SIGNAL_DISCOVERY_VERSION))
C_ADMISSION_PROFILE_VERSION = "v17.17.0-relational-C-new-point-not-new-topic"
SIGNAL_BACKFILL_HOURS = int(CONFIG.get("signal_backfill_hours", 720))
INCREMENTAL_STATE_VERSION = str(CONFIG.get("incremental_state_version", "v17.2-persistent-source-cursors"))
ROTATION_PROFILE_VERSION = str(CONFIG.get("rotation_profile_version", "v17.6.4-fresh-plus-historical-exploration"))
MATRIX_BALANCE_ROTATION_PROFILE_VERSION = str(CONFIG.get("matrix_balance_rotation_profile_version", "v17.13.26-balanced-reasoning-coverage"))
SOURCE_ATTENTION_PROFILE_VERSION = str(CONFIG.get("source_attention_profile_version", "v17.13.4-prefer-q1-and-official-eu-without-gate-tightening"))
PRIORITY_PEOPLE_PROFILE_VERSION = str(CONFIG.get("priority_people_profile_version", "v17.12.6-priority-people-recurring-rotation"))
RECALL_PROFILE_VERSION = str(CONFIG.get("recall_profile_version", "v17.13.32-citation-snowball-consensus"))
CITATION_SNOWBALL_PROFILE_VERSION = str(CONFIG.get("citation_snowball_profile_version", "v17.13.32-shared-reference-forward-snowball"))
RULE_FIX_PROFILE_VERSION = "v17.12.11-A-recall-strict-C-retirements-final"
RULE_FIX_SOURCE_RECOVERY_VERSION = "v17.12.9-new-institution-source-catchup-A-only"
A_RECALL_RECOVERY_VERSION = "v17.12.9-four-month-institution-A-recovery"
WINDOW_POLICY_VERSION = "v17.13.31-six-month-low-evidence-signals"
A_RECALL_RECOVERY_SOURCES_PER_SCAN = 6
RULE_FIX_SOURCE_RECOVERY_STAGE_SECONDS = 360
RULE_FIX_SOURCE_RECOVERY_PAGES_PER_DOMAIN = 28
RULE_FIX_SOURCE_RECOVERY_MAX_PAGES = 330
RULE_FIX_RECOVERY_SEED_URLS = {
    "is.mpg.de": [
        "https://is.mpg.de/en/news/bernhard-scholkopf-elected-for-un-ai-scientific-panel",
        "https://imprs.is.mpg.de/news/imprs-is-faculty-and-scholars-join-founding-team-of-new-european-physical-ai-lab",
    ],
    "ellis.institute": [
        "https://ellis.institute/news/bernhard-scholkopf-elected-fellow-of-the-royal-society",
    ],
    "ellis.eu": [
        "https://intue.ellis.eu/news/scientific-director-bernhard-scholkopf-joins-un-global-ai-panel",
        "https://intue.ellis.eu/news/ellis-institute-pis-contribute-to-the-international-ai-safety-report-2026",
    ],
    "ellisinstitute.fi": [
        "https://www.ellisinstitute.fi/bernhard-scholkopf-receives-honorary-doctorate",
        "https://www.ellisinstitute.fi/ellis-distinguished-lecture-bernhard-scholkopf",
    ],
    "aalto.fi": [
        "https://www.aalto.fi/en/news/seven-new-honorary-doctors-in-technology-at-aalto-university-in-2026",
    ],
    "ethz.ch": [
        "https://inf.ethz.ch/news-and-events/spotlights/infk-news-channel/2026/02/professors-menna-el-assady-and-bernhard-schoelkopf-recommended-for-un-ai-scientific-panel.html",
    ],
    "un.org": [
        "https://www.un.org/independent-international-scientific-panel-ai/en/preliminary-report",
        "https://www.un.org/independent-international-scientific-panel-ai/en/panel-members",
    ],
    "internationalaisafetyreport.org": [
        "https://internationalaisafetyreport.org/publication/international-ai-safety-report-2026",
    ],
    "kesai.eu": [
        "https://kesai.eu/blog/2026-05-20-kesai-launch/",
        "https://kesai.eu/team/",
    ],
    "itu.int": [
        "https://aiforgood.itu.int/event/ai-and-democracy-threats-safeguards-and-the-path-forward/",
    ],
    "tech-europe.org": [
        "https://www.tech-europe.org/session/panel-building-europes-ai-powered-innovation-economy",
    ],
}
RULE_FIX_FALLBACK_HUB_PATHS = [
    "", "/news", "/news/", "/publications", "/publications/", "/research", "/research/",
    "/reports", "/reports/", "/blog", "/blog/", "/articles", "/articles/", "/insights", "/insights/",
]
FORCE_SOURCE_EXPANSION_BACKFILL = bool(CONFIG.get("force_backfill_on_source_expansion", True))
# Provisional floor for import-time helpers/tests. main() replaces this with the preserved
# corpus floor before discovery starts.
DATE_FLOOR = dt.date.today() - relativedelta(months=BOOTSTRAP_LOOKBACK_MONTHS)
EXTENDED_DATE_FLOOR = dt.date.today() - relativedelta(months=EXTENDED_TOP_QUALITY_LOOKBACK_MONTHS)
SIGNAL_RETENTION_FLOOR = dt.date.today() - relativedelta(months=WEAK_SIGNAL_RETENTION_MONTHS)
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
# Sitemap ``lastmod`` dates are discovery evidence that should survive into the
# page parser.  Many high-value EU CMS pages omit article:published_time even when
# their sitemap provides a precise update date.  Keep this run-local map separate
# from the persisted seen-cache so it cannot become an admission shortcut.
INSTITUTION_DISCOVERED_DATES: dict[str, dt.date] = {}
INSTITUTION_SIGNAL_CANDIDATES: list[dict[str, Any]] = []
SIGNAL_WINDOW_START_DATE: dt.date | None = None
ACTIVE_FRONTIER_GAP_URL_TERMS: list[str] = []
ADMISSION_DIAGNOSTICS: Counter = Counter()
ADMISSION_DIAGNOSTICS_LOCK = threading.Lock()
ACTIVE_EU_CONTEXT_ANCHORS: list[dict[str, Any]] = []
UA = "RI-Geopolitics-Radar/3.0 (+https://vevirm.github.io/radar_articles_reports/)"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": UA,
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

# GitHub Actions already exposes an optional OPENALEX_API_KEY secret. Earlier
# scanner builds ignored it, which left every OpenAlex lane (including citation
# snowballing) on the anonymous allowance. Use the key when present, but preserve
# fully anonymous operation when it is absent. Never persist or log the key.
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()
RADAR_RESCUE_MODE = os.environ.get("RADAR_RESCUE_MODE", "").strip().lower() in {"1", "true", "yes", "on"}

def openalex_get(path: str, *, params: dict[str, Any] | None = None, timeout: int | float | None = None, **kwargs):
    query = dict(params or {})
    if OPENALEX_API_KEY:
        query.setdefault("api_key", OPENALEX_API_KEY)
    url = path if path.startswith("http") else "https://api.openalex.org/" + path.lstrip("/")
    return SESSION.get(url, params=query, timeout=timeout or REQUEST_TIMEOUT, **kwargs)


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


def source_stage_failed(warnings: list[str], label: str) -> bool:
    """True only when a source stage actually reported a failure.

    This is deliberately warning-based. The check is made after later stages have
    run, when earlier stage deadlines are naturally already in the past.
    """
    nlabel = normalized(label)
    relevant = [normalized(w) for w in warnings if nlabel in normalized(w)]
    # A normal per-stage time slice ending is not a source failure. It means the
    # remaining planned work must stay pending for a later scan; treating it as a
    # failure incorrectly poisons cycle/backfill state and disables rescue logic.
    return any(
        ("fatal stage error" in w) or ("public endpoint unavailable" in w)
        for w in relevant
    )


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




def interleaved_unique_batch(limit: int, *lanes: Iterable[Any]) -> list[Any]:
    """Compose a capped batch without letting the first lane crowd out the rest.

    Network collectors execute queued work in submission order and may hit a source or
    stage deadline before the tail of the queue starts. Round-robin composition therefore
    makes the *executed prefix* representative of broad rotation, exploration, Matrix gaps,
    methods and finding-context lanes instead of merely making those lanes present on paper.
    """
    cap = max(0, int(limit or 0))
    if cap <= 0:
        return []
    queues = [list(dict.fromkeys(lane)) for lane in lanes if lane]
    out: list[Any] = []
    seen: set[Any] = set()
    positions = [0] * len(queues)
    while len(out) < cap:
        progressed = False
        for idx, queue in enumerate(queues):
            while positions[idx] < len(queue):
                item = queue[positions[idx]]
                positions[idx] += 1
                if item in seen:
                    continue
                seen.add(item)
                out.append(item)
                progressed = True
                break
            if len(out) >= cap:
                break
        if not progressed:
            break
    return out


def committed_rotation_cursor(items: list[Any], original_cursor: int, planned: list[Any], executed: set[Any]) -> tuple[int, bool, int]:
    """Advance a persisted rotation only across the contiguous planned work actually executed.

    Planning a batch must not consume work. If a stage budget or endpoint stop prevents a
    queued query/task from making a request, that item remains the next rotation position.
    This intentionally prefers harmless repeat work over silently skipping a query for a cycle.
    """
    seq = list(items)
    if not seq:
        return 0, True, 0
    start = int(original_cursor or 0) % len(seq)
    consumed = 0
    for item in planned:
        if item not in executed:
            break
        consumed += 1
    end = min(len(seq), start + consumed)
    wrapped = bool(consumed and end >= len(seq))
    return (0 if wrapped else end), wrapped, consumed

def rotating_variants(items: list[Any], cursor: int, count: int = 1) -> tuple[list[Any], int]:
    """Take a circular per-topic slice and persist where that topic should resume.

    Unlike ``rotating_batch`` this helper may wrap inside a run because it is used
    for small variant/source lists belonging to one Frontier cell.
    """
    seq = list(dict.fromkeys(items))
    if not seq or count <= 0:
        return [], 0
    start = int(cursor or 0) % len(seq)
    take = min(len(seq), max(1, int(count)))
    out = [seq[(start + i) % len(seq)] for i in range(take)]
    return out, (start + take) % len(seq)


def query_theme(query: str) -> str:
    """Coarse topic label used only to diversify and explain scan rotation."""
    q = normalized(query)
    if any(x in q for x in ("brain drain", "talent", "researcher mobility", "research careers", "scientific talent", "academic")):
        return "talent and mobility"
    if any(x in q for x in ("research security", "foreign interference", "knowledge security", "trusted research")):
        return "research security"
    if any(x in q for x in ("china", "united states", " us ", "sanctions", "science diplomacy", "international cooperation", "collaboration")):
        return "international cooperation"
    if any(x in q for x in ("semiconductor", "quantum", "biotechnology", "artificial intelligence", " ai ", "critical technolog", "raw materials", "digital sovereignty")):
        return "critical technologies"
    if any(x in q for x in ("horizon europe", "fp10", "framework programme", "european research area")):
        return "EU research programmes"
    if any(x in q for x in ("infrastructure", "supply chain", "industrial", "dependencies", "technology transfer", "innovation ecosystem")):
        return "capacity and dependencies"
    if any(x in q for x in ("foresight", "horizon scanning", "weak signal", "scenario", "backcasting", "roadmapping", "cross impact")):
        return "foresight methods"
    return "R&I geopolitics"


def diversified_query_bank(queries: list[str]) -> list[str]:
    """Interleave topical families so one scan does not spend its whole budget on one cluster."""
    groups: dict[str, list[str]] = {}
    order: list[str] = []
    for q in list(dict.fromkeys(clean_text(x) for x in queries if clean_text(x))):
        theme = query_theme(q)
        if theme not in groups:
            groups[theme] = []
            order.append(theme)
        groups[theme].append(q)
    out: list[str] = []
    pos = 0
    while True:
        added = False
        for theme in order:
            vals = groups[theme]
            if pos < len(vals):
                out.append(vals[pos])
                added = True
        if not added:
            break
        pos += 1
    return out


def rotating_batch_excluding(items: list[Any], cursor: int, limit: int, excluded: Iterable[Any] | None = None) -> tuple[list[Any], int, bool]:
    """Take a circular fresh slice while skipping work already executed in this run.

    This is used by the low-yield second-pass rule. Unlike ``rotating_batch`` it may
    wrap while *planning* because the purpose is explicitly to find still-untried work
    rather than stop at the end of a persisted cycle. The returned cursor is committed
    only when the planned requests actually execute.
    """
    seq = list(dict.fromkeys(items))
    if not seq or int(limit or 0) <= 0:
        return [], 0, True
    blocked = set(excluded or [])
    start = int(cursor or 0) % len(seq)
    idx = start
    visited = 0
    out: list[Any] = []
    wrapped = False
    while visited < len(seq) and len(out) < int(limit):
        item = seq[idx]
        if item not in blocked:
            out.append(item)
        idx += 1
        visited += 1
        if idx >= len(seq):
            idx = 0
            wrapped = True
    return out, idx, wrapped


def commit_planned_cursor_if_executed(state: dict[str, Any], key: str, original_cursor: int, planned: list[Any], planned_next: int, executed: Iterable[Any]) -> int:
    """Commit a rescue-lane cursor only when its whole planned slice really ran.

    Partial execution intentionally leaves the cursor where it was. Repeating a few
    requests is safer than silently skipping a low-yield rotation slice after a deadline.
    """
    executed_set = set(executed or [])
    if planned and all(item in executed_set for item in planned):
        state[key] = int(planned_next or 0)
    else:
        state[key] = int(original_cursor or 0)
    return int(state[key])


def scholarly_exploration_plan(
    state: dict[str, Any],
    queries: list[str],
    oa_limit: int | None = None,
    cr_limit: int | None = None,
) -> dict[str, Any]:
    """Persist a full-corpus exploration lane independent of the fresh-window cursors.

    Normal incremental discovery intentionally looks back only a short overlap window.
    Without this lane, rotating query strings can still revisit only the same recent
    fortnight.  The exploration lane instead rotates across *topics* while searching
    from DATE_FLOOR; when a query returns a full page, its separate ``explore::``
    depth cursor advances the next time that query comes around.
    """
    bank = diversified_query_bank(queries)
    if not bank:
        return {"openalex": [], "crossref": [], "themes": []}
    if "openalex_explore_cursor" not in state:
        state["openalex_explore_cursor"] = int(state.get("openalex_cursor", 0) or 0) % len(bank)
    if "crossref_explore_cursor" not in state:
        base = int(state.get("crossref_broad_cursor", 0) or 0)
        state["crossref_explore_cursor"] = (base + max(1, len(bank) // 2)) % len(bank)
    oa_n = int(oa_limit if oa_limit is not None else CONFIG.get("openalex_exploration_queries_per_scan", 10))
    cr_n = int(cr_limit if cr_limit is not None else CONFIG.get("crossref_exploration_queries_per_scan", 8))
    if oa_n > 0:
        oa, state["openalex_explore_cursor"], _ = rotating_batch(
            bank, state.get("openalex_explore_cursor", 0), oa_n
        )
    else:
        oa = []
    if cr_n > 0:
        cr, state["crossref_explore_cursor"], _ = rotating_batch(
            bank, state.get("crossref_explore_cursor", 0), cr_n
        )
    else:
        cr = []
    themes = list(dict.fromkeys(query_theme(q) for q in oa + cr))
    return {"openalex": oa, "crossref": cr, "themes": themes}


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
            "crossref_source_cursor": 0,
            "crossref_preferred_journal_cursor": 0,
            "strand_b_method_cursor": 0,
            "institution_cursor": 0,
            "official_eu_source_cursor": 0,
            "frontier_gap_cursor": 0,
            "openalex_explore_cursor": 0,
            "crossref_explore_cursor": 0,
            "finding_context_cursor": 0,
            "priority_people_cursor": 0,
            "priority_people_completed_cycles": 0,
            "priority_people_openalex_author_ids": {},
            "frontier_gap_query_cursors": {},
            "frontier_gap_source_cursors": {},
            "frontier_recovery_query_cursors": {},
            "frontier_recovery_depth": {"openalex": {}, "crossref": {}},
            "result_depth": {"openalex": {}, "crossref_broad": {}, "crossref_priority": {}},
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
    state.setdefault("priority_people_cursor", 0)
    state.setdefault("priority_people_completed_cycles", 0)
    state.setdefault("foresight_author_cursor", 0)
    state.setdefault("foresight_author_completed_cycles", 0)
    if not isinstance(state.get("weak_signal_evidence_followup"), dict):
        state["weak_signal_evidence_followup"] = {}
    if not isinstance(state.get("priority_people_openalex_author_ids"), dict):
        state["priority_people_openalex_author_ids"] = {}
    if not isinstance(state.get("frontier_gap_query_cursors"), dict):
        state["frontier_gap_query_cursors"] = {}
    if not isinstance(state.get("frontier_gap_source_cursors"), dict):
        state["frontier_gap_source_cursors"] = {}
    if not isinstance(state.get("frontier_recovery_query_cursors"), dict):
        state["frontier_recovery_query_cursors"] = {}
    # Migration from V17.7.4: do not restart stubborn cells at formulation 1.
    # The ordinary per-cell scholarly cursor is the best persisted indication of
    # which query variants have already been cycled in earlier runs.
    legacy_gap_cursors = state.get("frontier_gap_query_cursors", {})
    if isinstance(legacy_gap_cursors, dict):
        for cell in FRONTIER_CELL_ORDER:
            state["frontier_recovery_query_cursors"].setdefault(
                cell, int(legacy_gap_cursors.get(f"scholarly:{cell}", 0) or 0)
            )
    if not isinstance(state.get("frontier_recovery_depth"), dict):
        state["frontier_recovery_depth"] = {"openalex": {}, "crossref": {}}
    for family in ("openalex", "crossref"):
        if not isinstance(state["frontier_recovery_depth"].get(family), dict):
            state["frontier_recovery_depth"][family] = {}
    if not isinstance(state.get("result_depth"), dict):
        state["result_depth"] = {}
    for family in ("openalex", "crossref_broad", "crossref_priority"):
        if not isinstance(state["result_depth"].get(family), dict):
            state["result_depth"][family] = {}
    for key in ("openalex", "crossref_broad", "crossref_priority", "institutions"):
        state["backfill"].setdefault(key, False)
        state["completed_cycles"].setdefault(key, 0)
        state["cycle_failed"].setdefault(key, False)
    for key in ("openalex_cursor", "crossref_broad_cursor", "crossref_priority_cursor", "crossref_source_cursor", "crossref_preferred_journal_cursor", "strand_b_method_cursor", "institution_cursor", "official_eu_source_cursor", "frontier_gap_cursor", "frontier_gap_depth_cursor", "finding_context_cursor"):
        state[key] = int(state.get(key, 0) or 0)
    state["a_recall_recovery_cursor"] = int(state.get("a_recall_recovery_cursor", 0) or 0)
    state.setdefault("a_recall_recovery_version", "")

    # Admission recall expansions must re-search previously rejected material. Earlier builds
    # cached rejected institutional URLs and preserved query/depth cursors across gate changes,
    # so a wider classifier could never reconsider much of the corpus it was intended to rescue.
    recall_changed = bool(previous.get("last_updated")) and previous.get("recall_profile_version") != RECALL_PROFILE_VERSION
    if recall_changed:
        for key in ("openalex_cursor", "crossref_broad_cursor", "crossref_priority_cursor", "crossref_source_cursor", "crossref_preferred_journal_cursor",
                    "strand_b_method_cursor", "institution_cursor", "official_eu_source_cursor", "openalex_explore_cursor", "crossref_explore_cursor", "finding_context_cursor"):
            state[key] = 0
        state["result_depth"] = {"openalex": {}, "crossref_broad": {}, "crossref_priority": {}}
        state["frontier_recovery_depth"] = {"openalex": {}, "crossref": {}}
        state["frontier_recovery_query_cursors"] = {}
        state["institution_seen_fingerprints"] = {}
        state["backfill"] = {"openalex": False, "crossref_broad": False, "crossref_priority": False, "institutions": False}
        state["completed_cycles"] = {"openalex": 0, "crossref_broad": 0, "crossref_priority": 0, "institutions": 0}
        state["cycle_failed"] = {"openalex": False, "crossref_broad": False, "crossref_priority": False, "institutions": False}
        state["recall_reset_this_run"] = True
    else:
        state["recall_reset_this_run"] = False

    state["version"] = INCREMENTAL_STATE_VERSION
    state["source_expansion_version"] = SOURCE_EXPANSION_VERSION
    state["recall_profile_version"] = RECALL_PROFILE_VERSION
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


def frontier_matrix_snapshot(previous: dict[str, Any]) -> tuple[dict[str, int], int, list[dict[str, Any]], str]:
    """Use the exact browser classifier for counts plus source-level placements."""
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
        placements = [dict(x) for x in (payload.get("placements") or []) if isinstance(x, dict)] if isinstance(payload, dict) else []
        return counts, qualifying, placements, ""
    except Exception as exc:
        return empty, 0, [], f"{type(exc).__name__}: {str(exc)[:160]}"


def frontier_matrix_coverage(previous: dict[str, Any]) -> tuple[dict[str, int], int, str]:
    """Count current 4x4 Matrix occupancy using the exact browser classifier.

    Failure is non-fatal: discovery falls back to an even rotation and the cumulative
    corpus is still preserved. ``frontier_matrix_snapshot`` additionally exposes
    source-level placements for curator-candidate audit/status reporting.
    """
    counts, qualifying, _placements, error = frontier_matrix_snapshot(previous)
    return counts, qualifying, error


def frontier_balance_snapshot(
    counts: dict[str, int],
    state: dict[str, Any] | None = None,
    *,
    advance_cursor: bool = False,
) -> dict[str, Any]:
    """Turn current Matrix occupancy into a distribution-aware rotation target.

    Matrix balance is a discovery-allocation rule, never an admission shortcut.
    The catch-up target follows both the upper quartile and a bounded share of
    the richest cell. Row and column scarcity then break ties so a thin row or
    direction is not hidden by a few very rich cells elsewhere.
    """
    floor = max(1, int(CONFIG.get("frontier_gap_target_count", 3) or 3))
    cap = max(floor, int(CONFIG.get("frontier_gap_balance_target_cap", 10) or 10))
    values = sorted(max(0, int(counts.get(key, 0) or 0)) for key in FRONTIER_CELL_ORDER)
    if values:
        mid = len(values) // 2
        if len(values) % 2:
            median_count = values[mid]
        else:
            median_count = (values[mid - 1] + values[mid] + 1) // 2
        q75_index = max(0, min(len(values) - 1, math.ceil(0.75 * len(values)) - 1))
        upper_quartile = values[q75_index]
    else:
        median_count = 0
        upper_quartile = 0
    max_count = max(values, default=0)
    catchup_ratio = max(0.0, min(1.0, float(CONFIG.get("frontier_gap_balance_rich_cell_ratio", 0.55) or 0.55)))
    rich_cell_floor = int(math.ceil(max_count * catchup_ratio)) if max_count else 0
    balance_enabled = bool(CONFIG.get("frontier_gap_balance_enabled", True))
    target_count = floor if not balance_enabled else max(
        floor, min(cap, max(upper_quartile, rich_cell_floor))
    )

    row_totals = {row: sum(counts.get(f"{row}-{col}", 0) for col in ("A", "B", "C", "D")) for row in ("knowledge", "infrastructure", "conversion", "rules")}
    col_totals = {col: sum(counts.get(f"{row}-{col}", 0) for row in ("knowledge", "infrastructure", "conversion", "rules")) for col in ("A", "B", "C", "D")}
    row_values = sorted(row_totals.values())
    col_values = sorted(col_totals.values())
    row_target = (row_values[1] + row_values[2] + 1) // 2 if len(row_values) == 4 else (max(row_values, default=0))
    col_target = (col_values[1] + col_values[2] + 1) // 2 if len(col_values) == 4 else (max(col_values, default=0))

    cursor_state = state if isinstance(state, dict) else {}
    start = int(cursor_state.get("frontier_gap_cursor", 0) or 0) % len(FRONTIER_CELL_ORDER)
    cyclic = FRONTIER_CELL_ORDER[start:] + FRONTIER_CELL_ORDER[:start]
    cyclic_rank = {key: i for i, key in enumerate(cyclic)}
    deficits = {key: max(0, target_count - counts.get(key, 0)) for key in FRONTIER_CELL_ORDER}
    scarcity_scores: dict[str, float] = {}
    for key in FRONTIER_CELL_ORDER:
        row, col = key.rsplit('-', 1)
        row_pressure = max(0.0, (row_target - row_totals.get(row, 0)) / max(1, row_target))
        col_pressure = max(0.0, (col_target - col_totals.get(col, 0)) / max(1, col_target))
        scarcity_scores[key] = round(
            deficits[key] / max(1, target_count)
            + (0.55 if counts.get(key, 0) == 0 else 0.0)
            + (0.20 if 0 < counts.get(key, 0) <= max(1, target_count // 3) else 0.0)
            + 0.35 * row_pressure
            + 0.35 * col_pressure,
            3,
        )

    sparse = [key for key in FRONTIER_CELL_ORDER if deficits[key] > 0]
    ordered = sorted(
        sparse,
        key=lambda key: (-scarcity_scores[key], -deficits[key], counts.get(key, 0), cyclic_rank[key]),
    )
    target_limit = max(0, min(len(ordered), int(CONFIG.get("frontier_gap_targets_per_scan", 8) or 0)))
    targets = ordered[:target_limit]
    empty_targets = [key for key in targets if counts.get(key, 0) == 0]

    # Repeat scarce targets in proportion to their balance pressure. This affects
    # query allocation only. The evidence gate stays identical for every cell.
    weighted_targets: list[str] = []
    repeat_scale = max(1.0, float(CONFIG.get("frontier_gap_balance_repeat_scale", 3.0) or 3.0))
    repeat_cap = max(1, int(CONFIG.get("frontier_gap_balance_repeat_cap", 8) or 8))
    for key in targets:
        repeats = max(1, min(repeat_cap, int(math.ceil(scarcity_scores[key] * repeat_scale))))
        weighted_targets.extend([key] * repeats)

    if advance_cursor and targets and isinstance(state, dict):
        last_index = FRONTIER_CELL_ORDER.index(targets[-1])
        state["frontier_gap_cursor"] = (last_index + 1) % len(FRONTIER_CELL_ORDER)

    return {
        "median_count": median_count,
        "upper_quartile": upper_quartile,
        "target_count": target_count,
        "row_totals": row_totals,
        "column_totals": col_totals,
        "row_target": row_target,
        "column_target": col_target,
        "deficits": deficits,
        "scarcity_scores": scarcity_scores,
        "targets": targets,
        "empty_targets": empty_targets,
        "weighted_targets": weighted_targets,
        "undercovered_cells": len(sparse),
        "max_count": max_count,
        "min_count": min(values, default=0),
    }


def frontier_gap_plan(previous: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Allocate extra discovery budget to under-covered Frontier cells.

    Coverage is evaluated relative to the current Matrix, not only against a fixed
    minimum. Search variants remain independently persistent per cell.
    """
    counts, qualifying, error = frontier_matrix_coverage(previous)
    balance = frontier_balance_snapshot(counts, state, advance_cursor=True)
    target_count = balance["target_count"]
    deficits = balance["deficits"]
    scarcity_scores = balance["scarcity_scores"]
    targets = balance["targets"]
    empty_targets = balance["empty_targets"]
    weighted_targets = balance["weighted_targets"]
    ordered = sorted(
        [key for key in FRONTIER_CELL_ORDER if deficits.get(key, 0) > 0],
        key=lambda key: (-deficits[key], counts.get(key, 0), FRONTIER_CELL_ORDER.index(key)),
    )
    nonempty_targets = [key for key in targets if counts.get(key, 0) > 0]

    query_cursors = state.setdefault("frontier_gap_query_cursors", {})
    if not isinstance(query_cursors, dict):
        query_cursors = {}
        state["frontier_gap_query_cursors"] = query_cursors

    # News gap queries: one formulation per selected cell per run, but resume from
    # that cell's own saved variant next time.
    profiles = CONFIG.get("frontier_gap_search_queries", {})
    news_limit = max(0, int(CONFIG.get("frontier_gap_queries_per_scan", 8) or 0))
    queries: list[str] = []
    news_used: dict[str, list[str]] = {}
    news_weight = max(1, int(CONFIG.get("frontier_gap_empty_news_weight", 2) or 2))
    news_targets: list[str] = []
    if empty_targets:
        for _ in range(news_weight):
            news_targets.extend(empty_targets)
        news_targets.extend(nonempty_targets)
    else:
        news_targets.extend(targets)
    for key in news_targets:
        raw = profiles.get(key, "") if isinstance(profiles, dict) else ""
        vals = raw if isinstance(raw, list) else [raw]
        vals = list(dict.fromkeys(clean_text(v) for v in vals if clean_text(v)))
        if not vals:
            continue
        cursor_key = f"news:{key}"
        chosen, next_cursor = rotating_variants(vals, query_cursors.get(cursor_key, 0), 1)
        query_cursors[cursor_key] = next_cursor
        if chosen and chosen[0] not in queries:
            queries.append(chosen[0])
            news_used.setdefault(key, []).append(chosen[0])
        if len(queries) >= news_limit:
            break

    # Scholarly gap queries: scarcity controls the number of slots, while each cell
    # advances through a larger formulation bank across scans.
    scholarly_profiles = CONFIG.get("frontier_gap_scholarly_queries", {})
    scholarly_limit = max(0, int(CONFIG.get("frontier_gap_scholarly_queries_per_scan", 12) or 0))
    max_variants = max(1, int(CONFIG.get("frontier_gap_scholarly_queries_per_target", 5) or 1))
    query_lists: dict[str, list[str]] = {}
    if isinstance(scholarly_profiles, dict):
        for key in FRONTIER_CELL_ORDER:
            raw = scholarly_profiles.get(key, "")
            vals = raw if isinstance(raw, list) else [raw]
            cleaned = list(dict.fromkeys(clean_text(v) for v in vals if clean_text(v)))
            if cleaned:
                query_lists[key] = cleaned[:max_variants]

    scholarly_queries: list[str] = []
    scholarly_cells: dict[str, list[str]] = {}
    local_cursor = {key: int(query_cursors.get(f"scholarly:{key}", 0) or 0) for key in FRONTIER_CELL_ORDER}
    # Give every sparse target one scholarly slot before scarcity repeats.
    # This prevents a few extreme deficits from hiding the rest of the thin Matrix.
    scholarly_target_sequence = list(targets) + list(weighted_targets)
    for key in scholarly_target_sequence:
        if len(scholarly_queries) >= scholarly_limit:
            break
        vals = query_lists.get(key, [])
        if not vals:
            continue
        chosen, next_cursor = rotating_variants(vals, local_cursor.get(key, 0), 1)
        local_cursor[key] = next_cursor
        if chosen and chosen[0] not in scholarly_queries:
            scholarly_queries.append(chosen[0])
            scholarly_cells.setdefault(key, []).append(chosen[0])

    # Fill unused slots by cycling sparse cells. This keeps available scan budget
    # productive even when weighted passes collided on duplicate formulations.
    fill_rounds = 0
    while len(scholarly_queries) < scholarly_limit and ordered and fill_rounds < max_variants:
        before = len(scholarly_queries)
        for key in ordered:
            vals = query_lists.get(key, [])
            if not vals:
                continue
            chosen, next_cursor = rotating_variants(vals, local_cursor.get(key, 0), 1)
            local_cursor[key] = next_cursor
            if chosen and chosen[0] not in scholarly_queries:
                scholarly_queries.append(chosen[0])
                scholarly_cells.setdefault(key, []).append(chosen[0])
            if len(scholarly_queries) >= scholarly_limit:
                break
        fill_rounds += 1
        if len(scholarly_queries) == before:
            break

    for key in FRONTIER_CELL_ORDER:
        if key in query_lists:
            query_cursors[f"scholarly:{key}"] = local_cursor.get(key, 0)

    return {
        "counts": counts,
        "qualifying": qualifying,
        "empty_cells": sum(1 for key in FRONTIER_CELL_ORDER if counts.get(key, 0) == 0),
        "target_count": target_count,
        "median_count": balance.get("median_count", 0),
        "upper_quartile": balance.get("upper_quartile", 0),
        "row_totals": balance.get("row_totals", {}),
        "column_totals": balance.get("column_totals", {}),
        "undercovered_cells": balance.get("undercovered_cells", 0),
        "max_count": balance.get("max_count", 0),
        "min_count": balance.get("min_count", 0),
        "deficits": deficits,
        "scarcity_scores": scarcity_scores,
        "targets": targets,
        "empty_targets": empty_targets,
        "weighted_targets": weighted_targets,
        "queries": queries,
        "news_query_cells": news_used,
        "scholarly_queries": scholarly_queries,
        "scholarly_query_cells": scholarly_cells,
        "classifier_error": error,
    }


def frontier_gap_depth_bank(frontier_focus: dict[str, Any], include_nonempty: bool = False) -> list[str]:
    """Return a balance-first bank for spare-time depth passes.

    Empty cells lead, but they no longer monopolise depth. All currently sparse
    cells remain in the interleaved bank, ordered by balance pressure. This is
    essential when an empty cell is intrinsically hard to populate.
    """
    profiles = CONFIG.get("frontier_gap_scholarly_queries", {})
    targets = list(frontier_focus.get("targets") or [])
    empties = list(frontier_focus.get("empty_targets") or [])
    scores = frontier_focus.get("scarcity_scores") or {}
    if include_nonempty:
        cells = targets
    else:
        nonempty = [c for c in targets if c not in empties]
        nonempty.sort(key=lambda c: (-float(scores.get(c, 0) or 0), targets.index(c)))
        cells = empties + nonempty
    per_cell: dict[str, list[str]] = {}
    for key in cells:
        raw = profiles.get(key, []) if isinstance(profiles, dict) else []
        vals = raw if isinstance(raw, list) else [raw]
        vals = list(dict.fromkeys(clean_text(v) for v in vals if clean_text(v)))
        if vals:
            per_cell[key] = vals
    bank: list[str] = []
    max_len = max((len(v) for v in per_cell.values()), default=0)
    for i in range(max_len):
        for key in cells:
            vals = per_cell.get(key, [])
            if i < len(vals) and vals[i] not in bank:
                bank.append(vals[i])
    return bank


def frontier_targets_for_query(query: str) -> list[str]:
    """Return Frontier cell(s) explicitly associated with a configured scholarly query."""
    q = clean_text(query)
    if not q:
        return []
    profiles = CONFIG.get("frontier_gap_scholarly_queries", {})
    out: list[str] = []
    if isinstance(profiles, dict):
        for cell in FRONTIER_CELL_ORDER:
            raw = profiles.get(cell, [])
            vals = raw if isinstance(raw, list) else [raw]
            if any(clean_text(v) == q for v in vals if clean_text(v)):
                out.append(cell)
    return out


def frontier_gap_recovery_plan(frontier_focus: dict[str, Any], state: dict[str, Any], limit: int) -> dict[str, Any]:
    """Round-robin stubborn-cell formulations with a persistent cursor per cell.

    V17.7.4 always sliced the first N entries of the interleaved recovery bank.  With
    more formulations than the recovery cap, later variants were therefore never
    requested, no matter how many scheduled runs elapsed.  This planner starts each
    empty cell at its own saved formulation cursor and advances only after a request
    actually reached OpenAlex or Crossref.
    """
    cells = list(frontier_focus.get("empty_targets") or frontier_focus.get("targets") or [])
    profiles = CONFIG.get("frontier_gap_scholarly_queries", {})
    cursors = state.setdefault("frontier_recovery_query_cursors", {})
    if not isinstance(cursors, dict):
        cursors = {}
        state["frontier_recovery_query_cursors"] = cursors
    per_cell: dict[str, list[str]] = {}
    starts: dict[str, int] = {}
    planned_by_cell: dict[str, list[str]] = {}
    for cell in cells:
        raw = profiles.get(cell, []) if isinstance(profiles, dict) else []
        vals = raw if isinstance(raw, list) else [raw]
        vals = list(dict.fromkeys(clean_text(v) for v in vals if clean_text(v)))
        if not vals:
            continue
        per_cell[cell] = vals
        starts[cell] = int(cursors.get(cell, 0) or 0) % len(vals)
        planned_by_cell[cell] = []

    cap = max(0, int(limit or 0))
    bank: list[str] = []
    round_no = 0
    while len(bank) < cap and per_cell:
        before = len(bank)
        for cell in cells:
            vals = per_cell.get(cell)
            if not vals or len(planned_by_cell[cell]) >= len(vals):
                continue
            idx = (starts[cell] + len(planned_by_cell[cell])) % len(vals)
            q = vals[idx]
            planned_by_cell[cell].append(q)
            if q not in bank:
                bank.append(q)
            if len(bank) >= cap:
                break
        round_no += 1
        if len(bank) == before or round_no > max((len(v) for v in per_cell.values()), default=0):
            break
    return {"queries": bank, "planned_by_cell": planned_by_cell, "starts": starts, "per_cell": per_cell}


def commit_frontier_recovery_plan(state: dict[str, Any], plan: dict[str, Any], executed: set[str]) -> dict[str, int]:
    """Advance each stubborn-cell formulation cursor across actually executed requests only."""
    cursors = state.setdefault("frontier_recovery_query_cursors", {})
    advanced: dict[str, int] = {}
    for cell, planned in (plan.get("planned_by_cell") or {}).items():
        vals = (plan.get("per_cell") or {}).get(cell, [])
        if not vals:
            continue
        cursor = int((plan.get("starts") or {}).get(cell, cursors.get(cell, 0)) or 0) % len(vals)
        consumed = 0
        for q in planned:
            if q not in executed:
                break
            cursor = (cursor + 1) % len(vals)
            consumed += 1
        cursors[cell] = cursor
        advanced[cell] = consumed
    return advanced


def provisional_frontier_document(previous: dict[str, Any], candidates: Iterable[dict[str, Any]],
                                  frontier_evidence: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build a lightweight corpus snapshot for in-run matrix reallocation.

    The matrix used to be frozen at scan start. If two empty cells were filled in wave 3,
    waves 4-20 still spent equal effort on those now-covered cells. This helper lets the
    depth phase re-run the exact Frontier classifier against accepted candidates collected
    so far and immediately concentrate on the cells that remain empty.
    """
    probe = {
        "strand_a": [dict(x) for x in previous.get("strand_a", []) if isinstance(x, dict)],
        "strand_b": [],
        "strand_c": [dict(x) for x in previous.get("strand_c", []) if isinstance(x, dict)],
        "frontier_evidence": [dict(x) for x in previous.get("frontier_evidence", []) if isinstance(x, dict)],
    }
    seen = {identity(internalize_previous(x)) for x in probe["strand_a"]}
    for item in dedupe_candidates([x for x in candidates if isinstance(x, dict)]):
        if item.get("strand") not in {"A", "both"}:
            continue
        key = identity(item)
        if key == "title:" or key in seen:
            continue
        probe["strand_a"].append(item)
        seen.add(key)
    fe_seen = {identity(internalize_previous(x)) for x in probe["frontier_evidence"]}
    for item in frontier_evidence or []:
        if not isinstance(item, dict) or item.get("strand") not in {"A", "both"}:
            continue
        key = identity(item)
        if key == "title:" or key in fe_seen or key in seen:
            continue
        probe["frontier_evidence"].append(item)
        fe_seen.add(key)
    return probe


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
    "european research area", "research system", "innovation system",
    "international research cooperation", "international scientific cooperation",
    "research governance", "innovation governance", "research excellence",
    "innovation ecosystem", "research infrastructure policy", "knowledge security",
    # V12: include the wider R&I system, not only texts that use explicit policy language.
    "research and development", "r&d", "science and technology", "science & technology",
    "scientific capacity", "research capacity", "innovation capacity", "innovation performance",
    "technological capacity", "technological capabilities", "technology capabilities",
    "technology development", "industrial research", "industrial innovation", "deep tech",
    "technology transfer", "knowledge transfer", "research infrastructure", "research infrastructures",
    "scientific infrastructure", "university research", "academic research",
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


# V17.7.2 bounded contextual route for Strand A. Many high-quality R&I papers describe the
# geopolitical mechanism empirically (external dependence, comparative capability, talent or
# market position) without using words such as "geopolitics" or "economic security". The route
# requires both an external/cross-border mechanism and a strategic R&I-system outcome, so a
# generic EU innovation or education paper still does not qualify.
A_EXTERNAL_RELATION = [
    "china", "chinese", "united states", "u.s.", "us-china", "american", "russia", "russian",
    "foreign", "non-eu", "non eu", "third country", "third countries", "international competition",
    "global competition", "cross-border", "cross border", "international collaboration",
    "international cooperation", "global supply chain", "global value chain", "foreign capital",
    "foreign investment", "external supplier", "external suppliers", "overseas", "abroad",
]
A_STRATEGIC_RI_OUTCOME = [
    "competitiveness", "competitive position", "research capacity", "scientific capacity",
    "innovation capacity", "technological capabilities", "technology capabilities", "capability gap",
    "capacity gap", "performance gap", "innovation gap", "funding gap", "investment gap",
    "scale-up gap", "scale up gap", "leadership", "technology lead", "research lead", "lagging",
    "falling behind", "catch up", "catch-up", "dependence", "dependency", "reliance", "resilience",
    "access", "bottleneck", "shortage", "research talent", "brain drain", "brain gain",
    "researcher outflow", "researcher inflow", "talent attraction", "talent retention",
    "commercialisation", "commercialization", "industrialisation", "industrialization",
    "scale-up", "scale up", "technology transfer", "knowledge transfer", "research infrastructure",
]

# V17.13 reader/recall repair: strategic context can be implied rather than literally labelled
# "geopolitics".  The implied route is deliberately triangulated: a generic paper about EU
# competitiveness, AI or capacity does not pass by itself.  At least two independent families
# must be present, and at least one must describe a relational/control mechanism.
A_IMPLIED_STRATEGIC_FAMILIES = {
    "dependence_control": [
        "dependence", "dependency", "reliance", "strategic autonomy", "technological sovereignty",
        "technology sovereignty", "control over", "access to", "bottleneck", "chokepoint",
        "vendor lock-in", "lock-in", "external supplier", "foreign supplier", "non-eu supplier",
        "supply security", "supply chain resilience", "resilience",
    ],
    "competition_capability": [
        "competitiveness", "competitive position", "global competition", "international competition",
        "leadership", "technology lead", "research lead", "falling behind", "catch up", "catch-up",
        "capability gap", "capacity gap", "innovation gap", "funding gap", "investment gap",
        "research capacity", "scientific capacity", "innovation capacity", "technological capabilities",
        "technology capabilities", "scale-up gap", "scale up gap",
    ],
    "international_coordination": [
        "international coordination", "international cooperation", "international collaboration",
        "research cooperation", "research collaboration", "scientific cooperation",
        "science diplomacy", "third country", "third countries", "non-eu", "foreign",
        "cross-border", "cross border", "global partnership", "international partnership",
    ],
    "security_resilience": [
        "research security", "knowledge security", "foreign interference", "security screening",
        "critical infrastructure", "infrastructure security", "economic security", "national security",
        "dual-use", "dual use", "export control", "supply chain security", "trusted research",
    ],
    "rules_power": [
        "standard-setting", "standard setting", "standards", "rule-setting", "rule setting",
        "regulatory power", "regulatory influence", "governance power", "agenda-setting",
        "agenda setting", "rule-taker", "rule taker", "rule-setter", "rule setter",
        "mutual recognition", "international governance", "technology governance",
    ],
    "talent_position": [
        "brain drain", "brain gain", "researcher outflow", "researcher inflow",
        "research talent", "scientific talent", "talent competition", "talent attraction",
        "talent retention", "researcher mobility", "scientist mobility", "research careers",
    ],
}
A_IMPLIED_RELATIONAL_FAMILIES = {
    "dependence_control", "international_coordination", "security_resilience", "rules_power", "talent_position"
}

def implied_strategic_context(text: str) -> tuple[bool, list[str], list[str]]:
    """Return a conservative, triangulated strategic-context decision.

    This is the non-literal-geopolitics route requested by the editorial design.  It uses
    multiple independent mechanisms rather than a single permissive keyword.
    """
    families: list[str] = []
    evidence: list[str] = []
    for family, terms in A_IMPLIED_STRATEGIC_FAMILIES.items():
        hits = distinct_matches(text, terms)
        if hits:
            families.append(family)
            evidence.extend(hits[:2])
    passes = len(set(families)) >= 2 and bool(set(families) & A_IMPLIED_RELATIONAL_FAMILIES)
    return passes, list(dict.fromkeys(families)), list(dict.fromkeys(evidence))[:8]
CHINA_CONTEXT = ["china", "chinese"]
CHINA_GEO_CONTEXT = [
    "de-risk", "derisk", "geopolit", "economic security", "national security",
    "strategic competition", "strategic dependency", "strategic dependencies",
    "technology competition", "export control", "dual use", "dual-use",
    "coercion", "foreign interference", "sanctions", "decoupling",
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

# Research-talent allocation is itself part of the R&I/geoeconomic system.  It is
# handled explicitly rather than by treating generic words such as ``migration`` or
# ``talent`` as geopolitical evidence.  This captures brain drain/gain into, out of
# and within Europe while excluding ordinary labour migration and student mobility.
RESEARCH_TALENT_ACTORS = [
    "researcher", "researchers", "scientist", "scientists", "academics", "academic staff", "faculty", "professor", "professors",
    "research workforce", "scientific workforce", "research talent", "scientific talent",
    "academic careers", "research careers", "postdoctoral researcher", "postdoctoral researchers",
    "postdoc", "postdocs", "doctoral researcher", "doctoral researchers", "research institution",
    "research institutions", "university researchers", "university research staff",
    "visiting researcher", "visiting researchers", "research visitor", "research visitors",
    "scientific visitor", "scientific visitors", "doctoral candidate", "doctoral candidates",
    "phd student", "phd students", "international doctoral candidate", "international doctoral candidates",
]
RESEARCH_TALENT_FLOW_EXPLICIT = [
    "research brain drain", "academic brain drain", "scientific brain drain", "brain drain",
    "research brain gain", "academic brain gain", "scientific brain gain", "brain gain",
    "researcher mobility", "researchers mobility", "scientist mobility", "scientific mobility",
    "research talent mobility", "scientific talent mobility",
    "researcher migration", "scientist migration",
    "research talent outflow", "scientific talent outflow", "researcher outflow",
    "research talent inflow", "scientific talent inflow", "researcher inflow",
    "international researcher mobility", "visiting researcher mobility", "research visits",
    "international doctoral mobility", "international doctoral candidates",
]
RESEARCH_TALENT_FLOW_ACTIONS = [
    "attract research talent", "attract researchers", "attract scientists", "retain research talent",
    "retain researchers", "retain scientists", "researcher retention", "scientist retention",
    "recruit researchers", "recruit scientists", "return mobility", "returning researchers",
    "researchers leave", "researchers leaving", "scientists leave", "scientists leaving",
    "researchers relocate", "scientists relocate", "move abroad", "moving abroad",
    "work abroad", "emigrate", "emigration", "immigrate", "immigration",
    "stay after study", "stay after studies", "stay after research", "post-study stay",
    "post study stay", "post-research stay", "post research stay", "stay to work",
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
# Strand-B method transfer is intentionally stricter than generic foresight detection.
# Bare words such as ``scenario`` (test scenario, stage scenario, simulation scenario)
# are too ambiguous to establish a transferable foresight method on their own.
FORESIGHT_TRANSFER_CORE = [
    "foresight", "strategic foresight", "foresight methodology", "foresight method", "foresight methods",
    "foresight practice", "foresight process", "horizon scanning", "weak signal", "weak signals",
    "delphi", "backcasting", "morphological analysis", "scenario planning", "scenario building",
    "scenario construction", "futures methodology", "futures method", "futures methods",
    "futures research", "futures literacy", "anticipatory governance", "foresight evaluation",
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
# For Strand B the method must be the contribution, not merely a tool used in a case study.
METHOD_CONTRIBUTION_CORE = [
    "methodology", "methodological", "method", "methods", "toolkit", "protocol",
    "evaluation of", "evaluating", "validation", "validating", "benchmark", "benchmarking",
    "comparison of methods", "compare methods", "method design", "method development",
    "foresight framework", "foresight approach", "horizon scanning framework",
    "scenario methodology", "scenario method", "scenario methods",
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
# These paths remain hard exclusions for A/B, but are valid discovery surfaces for
# Strand C because launches, institutional changes and capability investments are often
# published as news/event/project pages.  Jobs, calls, training and podcasts stay blocked.
C_DISCOVERY_URL_HINTS = [
    "/news/", "/events/", "/event/", "/press-release", "/press_releases", "/projects/",
]
NEWS_EXCLUDE = [
    "opinion", "commentary", "editorial", "analysis:", "analysis -", "column", "viewpoint",
    "podcast", "book review", "letter to the editor", "letters to the editor", "explainer",
    "interview", "comment:", "comment -", "company announcement",
    # V17.5.3: weak signals are developments, not individual career listings.
    "job with", "job opening", "job vacancy", "vacancy", "career opportunity",
    "doctoral researcher in", "phd position", "postdoctoral position", "postdoc position",
]
C_ROUTINE_EXCLUDE = [
    "honorary doctorate", "honorary degree", "elected fellow", "fellow of the",
    "medal", "prize", "award ceremony", "receives award", "wins award", "wins prize",
    "distinguished lecture", "guest lecture", "public lecture", "seminar", "webinar",
    "workshop", "conference programme", "conference program", "conference agenda",
    "postdoctoral position", "postdoc position", "phd position", "doctoral position",
    "doctoral researcher", "job vacancy", "vacancy", "career opportunity", "recruiting",
    "educational project", "student project", "summer school", "training course",
]
C_GENERIC_INDEX_TITLES = {
    "news", "news and events", "events", "latest news", "all news", "news archive",
    "publications", "research news", "press releases", "media",
}

def routine_signal_noise(title: str, desc: str = "") -> bool:
    """Reject routine institutional activity before Strand-C anchoring.

    C is external evidence that changes the interpretation of an existing A phenomenon;
    it is not an awards/jobs/events/project-news bucket.
    """
    ht = normalized(title)
    full = normalized(f"{title} {desc}")
    if ht.strip(" -:|/") in C_GENERIC_INDEX_TITLES:
        return True
    if contains_any(full, C_ROUTINE_EXCLUDE):
        return True
    # Award/honour headlines are routine prestige news even when the biography mentions
    # research capacity, Europe or competitiveness.
    if re.search(r"\b(?:award|awarded|medal|prize|honou?r(?:ed|ary)?|fellowship)\b", ht):
        return True
    # Event listings are not signals; a separate substantive report about an event can still pass.
    if re.search(r"\b(?:lecture|webinar|seminar|workshop|conference|symposium)\b", ht) and not re.search(r"\b(?:report|study|assessment|analysis|findings|evidence)\b", ht):
        return True
    return False

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
    "study", "research finds", "evidence", "reveals", "suggests", "indicates", "benchmark",
    "ranking", "gap", "outflow", "inflow", "overtake", "leads", "lags", "concentration",
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
    "research talent / mobility / brain drain",
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
    "critical and emerging technologies": ["critical technology", "critical technologies", "emerging technology", "semiconductor", "chips", "quantum", "biotech", "artificial intelligence", " ai ", "biomanufacturing", "fermentation capacity", "neuromorphic", "risc-v", "open-weight model", "open weights", "quantum error correction", "photonic interconnect", "critical technology list"],
    "economic security and R&I": ["economic security", "research funding", "innovation funding", "talent mobility", "strategic dependency", "strategic dependencies"],
    "R&I competitiveness / technological capabilities": ["innovation capacity", "innovation competitiveness", "technological capabilities", "scientific capacity", "research and development", "r&d", "deep tech", "industrial innovation"],
    "supply chains / strategic dependencies": ["supply chain security", "supply chain resilience", "strategic dependency", "strategic dependencies", "critical raw materials", "critical minerals", "friendshoring", "reshoring"],
    "Horizon Europe / FP10 international participation": ["horizon europe", "fp10", "association agreement", "third country", "third-country", "associated country"],
    "science diplomacy": ["science diplomacy", "scientific diplomacy"],
    "research talent / mobility / brain drain": ["research talent", "scientific talent", "researcher mobility", "researcher outflow", "researcher inflow", "scientists leaving", "brain drain", "brain gain", "talent retention", "talent attraction", "research careers"],
    "foresight / horizon scanning methodology": ["foresight methodology", "foresight method", "strategic foresight", "horizon scanning", "weak signal"],
    "scenario methods under uncertainty": ["scenario method", "scenario methodology", "scenario planning", "scenario design", "scenario construction", "uncertainty"],
    "anticipatory governance / strategic intelligence": ["anticipatory governance", "strategic intelligence", "anticipatory intelligence", "risk assessment"],
}
SPECIFIC_ANCHOR_THEMES = {
    "research security / foreign interference", "export controls / dual use",
    "Horizon Europe / FP10 international participation", "science diplomacy",
    "EU–China S&T cooperation / de-risking", "research talent / mobility / brain drain",
}
ENTITY_TERMS = [
    "china", "united states", "u.s.", "horizon europe", "fp10", "quantum", "semiconductor",
    "chips", "biotech", "artificial intelligence", "ai", "university", "research security",
    "export control", "dual use", "dual-use", "talent", "association",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    raw = str(value)
    # BeautifulSoup treats some bare ampersand sequences as entities (for example
    # ``R&D`` can collapse to ``RD``), which then creates dangerous substring
    # matches.  Only invoke the HTML parser when the value actually looks like
    # markup; otherwise preserve punctuation and decode normal HTML entities.
    if re.search(r"<[A-Za-z!/][^>]*>", raw):
        text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    else:
        text = html.unescape(raw)
    return re.sub(r"\s+", " ", text).strip()


def normalized(text: str) -> str:
    text = clean_text(text).lower().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text)


def folded_person_name(value: str) -> str:
    """Accent-insensitive person-name key used only for author identity matching."""
    folded = "".join(
        c for c in unicodedata.normalize("NFKD", clean_text(value))
        if not unicodedata.combining(c)
    ).lower()
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def load_priority_people(path: Path | None = None) -> list[dict[str, Any]]:
    """Load the curated recurring watch list fail-soft.

    The list changes discovery attention only; it never bypasses A/B admission. Keeping it
    in a standalone JSON file makes additions auditable without inflating the main query bank.
    """
    target = path or (ROOT / clean_text(CONFIG.get("priority_people_file", "priority_people.json")))
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return []
    raw = data.get("people") if isinstance(data, dict) else data
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = clean_text(item.get("name"))
        key = folded_person_name(name)
        if not name or not key or key in seen:
            continue
        seen.add(key)
        rec = dict(item)
        rec["name"] = name
        rec["category"] = clean_text(rec.get("category")) or "Other"
        rec["affiliation_hint"] = clean_text(rec.get("affiliation_hint"))
        topics = rec.get("topic_hints") if isinstance(rec.get("topic_hints"), list) else []
        rec["topic_hints"] = [clean_text(x) for x in topics if clean_text(x)]
        out.append(rec)
    return out


def diversified_priority_people(people: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Round-robin categories so each run spans several technical/policy domains."""
    groups: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for person in people:
        category = clean_text(person.get("category")) or "Other"
        if category not in groups:
            groups[category] = []
            order.append(category)
        groups[category].append(person)
    out: list[dict[str, Any]] = []
    pos = 0
    while True:
        added = False
        for category in order:
            vals = groups[category]
            if pos < len(vals):
                out.append(vals[pos])
                added = True
        if not added:
            break
        pos += 1
    return out


def priority_people_rotation_plan(
    state: dict[str, Any],
    people: list[dict[str, Any]] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Plan, but do not commit, the next additive named-person slice."""
    bank = diversified_priority_people(people if people is not None else load_priority_people())
    if not bank or not bool(CONFIG.get("priority_people_enabled", True)):
        return {"bank": [], "people": [], "cursor": 0, "wrapped": True, "categories": []}
    cursor = int(state.get("priority_people_cursor", 0) or 0)
    n = int(limit if limit is not None else CONFIG.get("priority_people_per_scan", 14))
    batch, next_cursor, wrapped = rotating_batch(bank, cursor, n)
    return {
        "bank": bank,
        "people": batch,
        "cursor": next_cursor,
        "wrapped": wrapped,
        "categories": list(dict.fromkeys(clean_text(x.get("category")) for x in batch if clean_text(x.get("category")))),
    }


def priority_person_context_query(person: dict[str, Any]) -> str:
    """Build a substantive fallback query from affiliation + expertise, not just a name."""
    affiliation = clean_text(person.get("affiliation_hint"))
    topics = person.get("topic_hints") if isinstance(person.get("topic_hints"), list) else []
    topic_text = " ".join(clean_text(x) for x in topics[:2] if clean_text(x))
    category = clean_text(person.get("category"))
    parts = [affiliation, topic_text, category, "Europe research innovation"]
    return clean_text(" ".join(x for x in parts if x))


def _likely_person_name(name: str) -> bool:
    """Conservative person-name filter for author-follow-up discovery."""
    n = clean_text(name)
    if not n or len(n) > 90:
        return False
    low = normalized(n)
    if any(term in low for term in [
        "commission", "council", "university", "institute", "institution", "organisation", "organization",
        "ministry", "department", "agency", "centre", "center", "laboratory", "laboratories", "consortium",
        "committee", "secretariat", "foundation", "bank", "office", "team", "project", "network",
    ]):
        return False
    parts = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+", n)
    return 2 <= len(parts) <= 6 and sum(1 for x in parts if len(x) >= 2) >= 2


def foresight_authors_from_corpus(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive a rotating expert-attention bank from admitted Strand-B authors.

    This intentionally avoids permanent source/domain privileges. Once the radar has
    admitted a genuine foresight/method publication, its human authors can receive a
    bounded exact-author check for later publications. Every resulting work still passes
    the ordinary A/B gates, so author attention changes recall, not evidential standards.
    """
    rows = data.get("strand_b") if isinstance(data, dict) and isinstance(data.get("strand_b"), list) else []
    min_items = max(1, int(CONFIG.get("foresight_author_followup_min_b_items", 1) or 1))
    counts: Counter = Counter()
    sources: dict[str, str] = {}
    topics: dict[str, list[str]] = {}
    names: dict[str, str] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        title = clean_text(item.get("title"))
        summary = clean_text(item.get("summary"))
        # Only use records that visibly belong to the futures/method lane; legacy B
        # noise should not create a watched author.
        evidence_text = normalized(f"{title} {summary} {item.get('relevance_note','')}")
        title_text = normalized(title)
        # Expert follow-up is narrower than Strand B itself. "Weak signal detection" can
        # describe engineering signal processing, and generic method papers are not enough
        # to establish a foresight-expert relationship. Require an explicit futures/foresight
        # marker in the publication title (or the scanner's explicit futures-method route).
        expert_markers = [
            "foresight", "futures", "horizon scanning", "scenario planning",
            "scenario building", "backcasting", "roadmapping", "anticipatory governance",
        ]
        explicit_future_route = "future-of-a-method" in evidence_text or "ri-futures-analytic-method" in evidence_text
        if not (contains_any(title_text, expert_markers) or explicit_future_route):
            continue
        if "weak signal detection" in title_text and not contains_any(title_text, ["foresight", "horizon scanning", "futures"]):
            continue
        author_text = clean_text(item.get("authors"))
        if not author_text:
            continue
        # Scanner output uses comma-separated full names. Semicolons are accepted too.
        raw_names = [clean_text(x) for x in re.split(r"\s*(?:;|,|\band\b)\s*", author_text) if clean_text(x)]
        raw_names = raw_names[:6]
        for raw in raw_names:
            raw = re.sub(r"\bet\s+al\.?$", "", raw, flags=re.I).strip()
            if not _likely_person_name(raw):
                continue
            key = folded_person_name(raw)
            if not key:
                continue
            counts[key] += 1
            names.setdefault(key, raw)
            sources.setdefault(key, clean_text(item.get("source")))
            topic = clean_text(title)
            if topic and topic not in topics.setdefault(key, []):
                topics[key].append(topic)
    ranked = [k for k, c in counts.most_common() if c >= min_items]
    derived = [
        {
            "name": names[k],
            "category": "foresight / futures methods",
            "affiliation_hint": sources.get(k, ""),
            "topic_hints": topics.get(k, [])[:2],
            "foresight_evidence_count": counts[k],
            "expert_basis": "admitted_foresight_publication",
        }
        for k in ranked
    ]

    # Optional curator-provided people are person-centric discovery seeds, not source
    # privileges. They receive the same bounded exact-author search and the same A/B gate.
    # This is the right place for known foresight/strategic-intelligence experts whose
    # high-value reports may appear outside normal journal/index routes.
    seeds = CONFIG.get("foresight_expert_seeds", [])
    seeded: list[dict[str, Any]] = []
    if isinstance(seeds, list):
        for raw in seeds:
            if isinstance(raw, str):
                raw = {"name": raw}
            if not isinstance(raw, dict):
                continue
            name = clean_text(raw.get("name"))
            if not _likely_person_name(name):
                continue
            seeded.append({
                "name": name,
                "category": clean_text(raw.get("category")) or "foresight / strategic intelligence",
                "affiliation_hint": clean_text(raw.get("affiliation_hint")),
                "topic_hints": [clean_text(x) for x in (raw.get("topic_hints") or []) if clean_text(x)][:4],
                "foresight_evidence_count": 0,
                "expert_basis": "curator_seed",
            })

    out: list[dict[str, Any]] = []
    seen_people: set[str] = set()
    for person in seeded + derived:
        key = folded_person_name(person.get("name", ""))
        if not key or key in seen_people:
            continue
        seen_people.add(key)
        out.append(person)
    return out


def foresight_author_rotation_plan(state: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    bank = foresight_authors_from_corpus(data)
    if not bank or not bool(CONFIG.get("foresight_author_followup_enabled", True)):
        return {"bank": [], "people": [], "cursor": 0, "wrapped": True}
    cursor = int(state.get("foresight_author_cursor", 0) or 0)
    n = max(0, int(CONFIG.get("foresight_author_followup_per_scan", 4) or 0))
    batch, next_cursor, wrapped = rotating_batch(bank, cursor, n)
    return {"bank": bank, "people": batch, "cursor": next_cursor, "wrapped": wrapped}


ENGLISH_LANGUAGE_CODES = {"en", "eng", "english", "en-us", "en-gb", "en_us", "en_gb"}
ENGLISH_FUNCTION_WORDS = {
    "the", "and", "of", "to", "in", "for", "with", "on", "as", "by", "from", "that",
    "this", "is", "are", "was", "were", "be", "an", "a", "at", "or", "which", "their",
    "between", "through", "under", "into", "across", "towards", "toward", "how", "what",
    "its", "it", "we", "our", "can", "could", "may", "more", "than", "but", "while",
    "using", "based", "among", "amid", "within", "without", "against", "after", "before",
}
NON_ENGLISH_FUNCTION_WORDS = {
    # Fail-closed language guard. A few words can also occur as names/abbreviations, so
    # rejection uses their balance against positive English evidence rather than one token.
    # German
    "und", "der", "die", "das", "den", "dem", "des", "mit", "für", "von", "zur", "zum",
    "im", "eine", "einer", "eines", "auf", "aus", "bei", "über", "durch", "zwischen",
    # French
    "et", "les", "une", "dans", "pour", "avec", "sur", "aux", "du", "de", "la", "le",
    "un", "des", "par", "vers", "entre", "sans", "sous", "au", "en", "dans", "que",
    # Spanish / Portuguese
    "y", "los", "las", "una", "para", "con", "del", "por", "sobre", "entre", "el",
    "os", "as", "uma", "das", "dos", "do", "da", "pela", "pelos", "nas", "nos", "em",
    # Italian
    "gli", "della", "delle", "per", "nel", "nella", "tra", "fra", "il", "lo", "dei",
    # Dutch
    "het", "een", "van", "voor", "met", "naar", "bij", "uit", "over", "als", "ook",
    # Nordic
    "og", "av", "til", "på", "och", "att", "som", "ett", "eller", "från", "med",
    # Polish / Romanian / Czech-Slovak
    "oraz", "dla", "przez", "jest", "czy", "și", "sau", "pentru", "din", "ale", "este", "sunt",
    "výzkum", "výzkumu", "pro", "se", "ve", "na", "z", "w", "od", "do",
}
ENGLISH_GENERAL_CUES = {"existing", "report", "weak", "signal", "new", "earlier", "today", "yesterday", "current", "study", "paper", "analysis"}
ENGLISH_DOMAIN_CUES = {
    "eu", "europe", "european", "research", "science", "scientific", "innovation", "innovative",
    "technology", "technological", "digital", "policy", "governance", "security", "strategic",
    "strategy", "competition", "competitive", "competitiveness", "cooperation", "collaboration",
    "investment", "industry", "industrial", "semiconductor", "semiconductors", "quantum", "ai",
    "artificial", "intelligence", "foresight", "scenario", "scenarios", "method", "methodology",
    "future", "futures", "supply", "chains", "dependency", "dependencies", "dependence", "autonomy",
    "sovereignty", "talent", "mobility", "knowledge", "capacity", "capability", "capabilities",
    "global", "international", "development", "economic", "economy", "geopolitical", "geopolitics",
    "geoeconomic", "regulation", "standards", "funding", "programme", "program", "framework",
    "universities", "university", "researchers", "researcher", "infrastructure", "compute", "cloud",
}


def _language_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", clean_text(text).lower())


def _contains_non_latin_script(text: str) -> bool:
    """Reject meaningful source prose in non-Latin scripts.

    Latin typographic ligatures (for example the fi ligature in PDF extraction) are allowed.
    The purpose is to block Cyrillic/Greek/CJK/Arabic/etc. publication text from the
    English public radar, not to punish OCR typography.
    """
    txt = clean_text(text)
    if not txt:
        return False
    # Explicit script blocks: Cyrillic, Greek, Hebrew, Arabic, Indic, Thai, CJK, Kana, Hangul.
    script_re = re.compile(
        r"[\u0370-\u052F\u0590-\u08FF\u0900-\u0D7F\u0E00-\u0E7F"
        r"\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uAC00-\uD7AF]"
    )
    letters = re.findall(r"[^\W\d_]", txt, flags=re.UNICODE)
    if not letters:
        return False
    foreign = sum(1 for ch in letters if script_re.match(ch))
    return foreign / len(letters) > 0.01


def _strong_non_english_evidence(text: str, *, title_mode: bool = False) -> bool:
    """Return True only for affirmative evidence that a Latin-script string is non-English.

    Short institutional titles, proper names and acronyms are often linguistically ambiguous.
    Ambiguity must not be treated as proof of a foreign language.  We still fail closed for
    non-Latin script and for clear foreign-language function-word dominance.
    """
    txt = clean_text(text)[:8000]
    if not txt:
        return False
    if _contains_non_latin_script(txt):
        return True
    words = _language_tokens(txt)
    if not words:
        return False
    en = sum(w in ENGLISH_FUNCTION_WORDS for w in words)
    other = sum(w in NON_ENGLISH_FUNCTION_WORDS for w in words)
    if title_mode:
        # One clear foreign function word in a 4+ word title with no English grammar is
        # meaningful (e.g. French/Dutch titles), while a two-word proper name stays neutral.
        return bool((other >= 2 and other > en) or (len(words) >= 4 and other >= 1 and en == 0))
    return bool(other >= 4 and other > en)


def probably_english(text: str, *, title_mode: bool = False) -> bool:
    """Positive English detector, with an ambiguity-safe mode for short titles.

    Long text still needs positive English evidence.  A short Latin-script title with no
    foreign-language evidence is allowed to remain *undetermined* rather than being rejected;
    the body or explicit source-language metadata then decides the record.
    """
    txt = clean_text(text)[:8000]
    if not txt or _strong_non_english_evidence(txt, title_mode=title_mode):
        return False
    words = _language_tokens(txt)
    if len(words) < 2:
        return False
    en = sum(w in ENGLISH_FUNCTION_WORDS for w in words)
    other = sum(w in NON_ENGLISH_FUNCTION_WORDS for w in words)
    domain = sum(w in ENGLISH_DOMAIN_CUES for w in words)
    general = sum(w in ENGLISH_GENERAL_CUES for w in words)

    if title_mode:
        if en >= 1 and en >= other:
            return True
        if domain >= 1 and other == 0:
            return True
        if general >= 1 and other == 0:
            return True
        # Ambiguous short proper-name/acronym headings are not positive English evidence,
        # but callers can accept them when the body is demonstrably English.
        return False

    if len(words) < 3:
        return False
    if en >= 2 and en >= other:
        return True
    if en >= 1 and domain >= 2 and other <= 1:
        return True
    # Institutional prose can be terse and noun-heavy.  A substantial all-Latin block
    # with several domain/general English cues and no foreign grammar is good evidence.
    if len(words) >= 8 and other == 0 and (domain + general) >= 3:
        return True
    return False


def substantive_english_evidence_block(text: str, min_words: int = 25) -> bool:
    """Detect a source-provided English abstract/summary inside otherwise non-English text.

    We inspect sentence windows rather than translating anything. This allows bilingual pages
    and foreign-language papers with an English abstract to qualify when that English block is
    long enough to support the actual finding.
    """
    txt = clean_text(text)[:16000]
    if not txt:
        return False
    sentences = split_sentences(txt, max_chars=16000)
    if not sentences:
        sentences = [txt]
    for i in range(len(sentences)):
        block = ''
        for j in range(i, min(len(sentences), i + 4)):
            block = clean_text(f"{block} {sentences[j]}")
            words = _language_tokens(block)
            if len(words) >= min_words and probably_english(block, title_mode=False):
                return True
            if len(words) > max(140, min_words * 5):
                break
    return False

def english_record_ok(text: str, metadata_language: Any = "", *, title: str = "") -> bool:
    """Fail closed to English-language publications for the public radar.

    V17.13.24 removes the old "English abstract rescues a foreign publication" rule.
    A/B evidence must be an English publication: explicit foreign language metadata rejects,
    publication titles must positively look English, and meaningful non-Latin source prose rejects.
    Unknown-language metadata may pass only when both title and available evidence are positively
    English. No translation is used for admission.
    """
    if not bool(CONFIG.get("english_only", True)):
        return True
    lang = normalized(metadata_language).replace("_", "-")
    primary = lang.split("-", 1)[0] if lang else ""
    explicit_english = bool(lang and (lang in ENGLISH_LANGUAGE_CODES or primary == "en"))
    explicit_foreign = bool(lang and not explicit_english)
    strict_publication = bool(CONFIG.get("english_publication_required", True))

    title = clean_text(title)
    txt = clean_text(text)
    if not title:
        return False
    if _contains_non_latin_script(title) or _strong_non_english_evidence(title, title_mode=True):
        return False
    if strict_publication and explicit_foreign:
        return False
    # Publication titles must be positively English, not merely "not obviously foreign".
    if strict_publication and not probably_english(title, title_mode=True):
        return False
    if _contains_non_latin_script(txt) or _strong_non_english_evidence(txt, title_mode=False):
        return False

    words = _language_tokens(txt)
    title_words = _language_tokens(title)
    effectively_title_only = len(words) <= max(8, len(title_words) + 2)
    if effectively_title_only:
        return bool(explicit_english or probably_english(title, title_mode=True))

    # For unknown language metadata require positive English evidence in the available source text.
    body_ok = probably_english(txt, title_mode=False)
    english_block = substantive_english_evidence_block(
        txt, min_words=int(CONFIG.get("foreign_language_english_evidence_min_words", 25) or 25)
    )
    if explicit_english:
        return bool(body_ok or english_block)
    return bool(body_ok and english_block)

def english_public_item_ok(item: dict[str, Any]) -> bool:
    """Publication-time guard for already-admitted public records.

    New candidates pass the stricter ``english_record_ok`` gate. For saved rows, avoid
    reinterpreting a shortened summary as language evidence: reject explicit foreign metadata,
    non-English/non-Latin titles, and meaningful non-Latin public prose.
    """
    if not bool(CONFIG.get("english_only", True)):
        return True
    if not isinstance(item, dict):
        return False
    title = clean_text(item.get("title") or item.get("headline") or "")
    body = clean_text(item.get("summary") or item.get("signal_note") or item.get("why_it_matters") or "")
    if not title:
        return False
    lang = normalized(item.get("language", "")).replace("_", "-")
    primary = lang.split("-", 1)[0] if lang else ""
    if lang and not (lang in ENGLISH_LANGUAGE_CODES or primary == "en"):
        return False
    if _contains_non_latin_script(title) or _strong_non_english_evidence(title, title_mode=True):
        return False
    if not probably_english(title, title_mode=True):
        return False
    if _contains_non_latin_script(body):
        return False
    return True

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
    """Return phrase hits while protecting short/ambiguous terms from substring noise.

    The radar vocabulary intentionally relies on some lexical-family matching
    (``technology``/``technologies``, ``research``/``researchers``).  Keep that
    high-recall behaviour for substantive phrases, but require token boundaries for
    short abbreviations and known nested phrases.  This prevents ``R&D`` from
    collapsing into an ``rd`` hit inside *regarding* and prevents ``national
    security`` from matching *international security*.
    """
    low = normalized(text)
    found = []
    boundary_only = {"national security"}
    for phrase in phrases:
        p = normalized(phrase)
        if not p:
            continue
        if p in {"geopolit"}:
            ok = p in low
        elif len(p) <= 4 or "&" in p or p in boundary_only:
            ok = bool(re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", low))
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


def _eu_defined_as_non_union(text: str) -> bool:
    """Return True when the document explicitly defines EU as another abbreviation.

    Scholarly abstracts frequently use ``EU`` for concepts such as *environmental
    uncertainty*.  Treating every bare EU token as European Union scope creates very
    damaging false positives.  An explicit local definition wins unless the expanded
    phrase itself is European Union.
    """
    raw = clean_text(text)
    for m in re.finditer(r"\b([A-Za-z][A-Za-z\- ]{2,90})\s*\(\s*EU\s*\)", raw):
        phrase = clean_text(m.group(1))
        # Keep only the tail of the noun phrase; long captures may include a sentence lead.
        words = phrase.split()
        tail = " ".join(words[-8:])
        low = normalized(tail)
        if "european union" not in low and not low.endswith("european union"):
            return True
    return False


def union_eu_word(text: str, document_text: str = "") -> bool:
    """Bare ``EU`` is a Union anchor only when it has not been redefined locally."""
    if not has_eu_word(text):
        return False
    return not _eu_defined_as_non_union(document_text or text)


def _aboutness_text_mode(abstract: str, body: str) -> str:
    """Choose an aboutness test that matches the amount of source text available."""
    aw = len(clean_text(abstract).split())
    bw = len(clean_text(body).split())
    modes = CONFIG.get("aboutness_text_modes", {}) if isinstance(CONFIG.get("aboutness_text_modes", {}), dict) else {}
    full_min = int((modes.get("full_text") or {}).get("min_body_words", 500))
    abstract_min = int((modes.get("abstract_only") or {}).get("min_abstract_words", 20))
    if bw >= full_min:
        return "full_text"
    if aw >= abstract_min or bw >= 80:
        return "abstract_only"
    return "metadata_only"


def _sentence_block_stats(text: str, hit_fn) -> tuple[int, list[str]]:
    sentences = split_sentences(text)
    hit_sentences = 0
    terms: list[str] = []
    for sent in sentences:
        hits = hit_fn(sent)
        if hits:
            hit_sentences += 1
            for h in hits:
                if h not in terms:
                    terms.append(h)
    return hit_sentences, terms


def aboutness_for_a(
    title: str, abstract: str, body: str, *, a_focus: bool, eu_rel: str | None, bridge: str,
    contextual_evidence: bool = False
) -> dict[str, Any]:
    """Apply source-length-aware aboutness for Strand A.

    Governing rule: reject incidental mentions, not short documents.  Full documents
    must show repeated/spread R&I and geopolitical evidence.  Abstract-only records
    are judged within the abstract and are never required to contain non-existent
    sections.  Metadata-only records are deferred rather than labelled irrelevant.
    """
    mode = _aboutness_text_mode(abstract, body)
    ta = clean_text(f"{title}. {abstract}")
    full = clean_text(f"{ta}. {body}")
    result = {
        "text_mode": mode, "pass": False, "reason": "",
        "ri_sentences": 0, "geo_sentences": 0, "ri_terms": [], "geo_terms": [],
    }
    if mode == "metadata_only":
        result["reason"] = "insufficient_text"
        return result
    if eu_rel != "direct":
        result["reason"] = "no_direct_eu"
        return result
    if not a_focus:
        # Keep the substantive failure reason visible to diagnostics.
        ri = _ri_hits(ta if mode == "abstract_only" else full)
        probe = ta if mode == "abstract_only" else full
        geo = _geo_hits(probe)
        implied_ok, _, implied_terms = implied_strategic_context(probe)
        result["ri_terms"], result["geo_terms"] = ri[:8], (geo or implied_terms)[:8]
        result["reason"] = "no_ri" if not ri else ("no_geopolitics" if not (geo or implied_ok) else "no_substantive_bridge")
        return result

    if mode == "abstract_only":
        # Short institutional papers often have no separate abstract: the available body
        # *is* the concise evidence unit. Earlier builds labelled body>=80 words as
        # abstract_only but then ignored that body here, silently rejecting good briefs.
        concise = ta if len(clean_text(abstract).split()) >= 8 else clean_text(f"{ta}. {body[:8000]}")
        ri = _ri_hits(concise)
        geo = _geo_hits(concise)
        result["ri_terms"], result["geo_terms"] = ri[:8], geo[:8]
        result["pass"] = bool(ri and (geo or contextual_evidence) and (bridge or a_focus))
        result["reason"] = "about" if result["pass"] else "no_substantive_bridge"
        return result

    # Full text: require the issue to recur across the document. Sentence spread is used
    # because many HTML/PDF extraction paths do not preserve reliable section headings.
    ri_sents, ri_terms = _sentence_block_stats(full, _ri_hits)
    geo_sents, geo_terms = _sentence_block_stats(full, _geo_hits)
    result.update({
        "ri_sentences": ri_sents, "geo_sentences": geo_sents,
        "ri_terms": ri_terms[:8], "geo_terms": geo_terms[:8],
    })
    modes = CONFIG.get("aboutness_text_modes", {}) if isinstance(CONFIG.get("aboutness_text_modes", {}), dict) else {}
    full_cfg = modes.get("full_text") or {}
    min_ri_sents = int(full_cfg.get("min_ri_hit_sentences", 2))
    min_geo_sents = int(full_cfg.get("min_geopolitics_hit_sentences", 2))
    repeated_ri = ri_sents >= min_ri_sents and (len(ri_terms) >= 2 or ri_sents >= max(3, min_ri_sents))
    repeated_geo = geo_sents >= min_geo_sents and (len(geo_terms) >= 2 or geo_sents >= max(3, min_geo_sents))
    # A source may express geopolitics as an external-position mechanism (dependence,
    # comparative capability, talent loss, foreign access) rather than repeat a GEO_STRONG
    # label. Require a source sentence that actually combines R&I + external actor/relation
    # + strategic outcome; this is evidence, not a keyword waiver.
    contextual_sentences = 0
    if contextual_evidence:
        for sent in split_sentences(full):
            implied_ok, _, _ = implied_strategic_context(sent)
            if _ri_hits(sent) and (
                implied_ok or (distinct_matches(sent, A_EXTERNAL_RELATION) and distinct_matches(sent, A_STRATEGIC_RI_OUTCOME))
            ):
                contextual_sentences += 1
    geo_supported = repeated_geo or contextual_sentences >= 1
    result["pass"] = bool(repeated_ri and geo_supported)
    if not repeated_ri:
        result["reason"] = "incidental_ri"
    elif not geo_supported:
        result["reason"] = "incidental_geopolitics"
    else:
        result["reason"] = "about"
    return result


def eu_evidence(title: str, abstract: str, body: str) -> tuple[str | None, list[str]]:
    """Classify EU relevance as *scope*, not as a passing geographic mention.

    Precision repair (V17.5.10): older builds treated any Europe/member-state name in
    title+abstract as direct EU relevance.  In comparative/global papers this allowed
    a single German/French/European study, affiliation or comparator to make an
    Indonesia/China/US-centred paper look EU-scoped.  Direct scope now requires one of:

    * EU/Europe/member-state scope in the title;
    * an explicit EU institution/programme/policy marker in the abstract; or
    * a Europe/member-state abstract sentence that itself carries both R&I and
      geopolitical/economic-security substance.

    Body-only evidence remains stricter still.  Derived relevance still requires an
    explicit implication-for-Europe sentence.
    """
    title = clean_text(title)
    abstract = clean_text(abstract)
    ta = f"{title}. {abstract}"

    title_direct = distinct_matches(title, EU_DIRECT)
    title_generic = distinct_matches(title, EU_GENERIC)
    title_member = bounded_matches(title, MEMBER_STATE_SCOPE)
    if union_eu_word(title, ta):
        title_direct.append("EU")
    if title_direct or title_generic or title_member:
        return "direct", list(dict.fromkeys(title_direct + title_generic + title_member))[:4]

    # Explicit EU institutional/programme/policy language in the abstract is strong
    # scope evidence.  A bare "EU" token is accepted only when the sentence is also
    # substantively about R&I, avoiding incidental footnote/comparator mentions.
    for sent in split_sentences(abstract):
        sent_direct = distinct_matches(sent, EU_DIRECT)
        sent_generic = distinct_matches(sent, EU_GENERIC)
        sent_member = bounded_matches(sent, MEMBER_STATE_SCOPE)
        bare_eu = union_eu_word(sent, ta)
        ri_here = bool(distinct_matches(sent, RI_STRONG + RI_GENERIC))
        implied_here, _, _ = implied_strategic_context(sent)
        geo_here = bool(distinct_matches(sent, GEO_STRONG)) or china_geo_signal(sent) or research_talent_flow_signal(sent) or implied_here
        # An abstract mentioning the European Union as one comparator/case is not
        # automatically EU-scoped.  Specific EU institutions/programmes can establish
        # scope directly; generic "European Union"/bare EU needs substantive R&I +
        # geopolitical content in the same sentence.
        institutional_direct = [h for h in sent_direct if normalized(h) not in {"european union"}]
        if institutional_direct:
            return "direct", list(dict.fromkeys(institutional_direct))[:4]
        if sent_direct and ri_here and geo_here:
            return "direct", list(dict.fromkeys(sent_direct))[:4]
        if bare_eu and ri_here and geo_here:
            return "direct", ["EU"]
        # Generic Europe/member-state names are not enough on their own in an
        # abstract; the same sentence must establish the R&I-geopolitical scope.
        if (sent_generic or sent_member) and ri_here and geo_here:
            return "direct", list(dict.fromkeys(sent_generic + sent_member))[:4]

    full = f"{ta}. {body[:50000]}"
    direct_body = distinct_matches(full, EU_DIRECT)
    strong_body_scope = distinct_matches(full, [
        "european commission", "european parliament", "horizon europe", "fp10",
        "european research area", "european economic security", "eu research",
        "eu innovation", "eu science", "eu technology",
    ])
    eu_count = 0 if _eu_defined_as_non_union(full) else len(re.findall(r"\beu\b", normalized(full)))
    # Body-only scope must be explicit/repeated.  Merely mentioning two European
    # countries somewhere in a long document is no longer treated as EU scope.
    if strong_body_scope or eu_count >= 2:
        evidence = strong_body_scope + direct_body
        return "direct", list(dict.fromkeys(evidence))[:4]

    # Europe is part of the governing scope, not just EU institutions. For full-text
    # institutional/research documents, a sentence that explicitly connects Europe or
    # a member state to R&I and a strategic/geopolitical mechanism is direct scope.
    for sent in split_sentences(body[:50000]):
        european_here = distinct_matches(sent, EU_GENERIC) + bounded_matches(sent, MEMBER_STATE_SCOPE)
        if european_here and _ri_hits(sent):
            implied_here, _, _ = implied_strategic_context(sent)
            contextual_here = bool(_geo_hits(sent)) or implied_here or bool(
                distinct_matches(sent, A_EXTERNAL_RELATION) and distinct_matches(sent, A_STRATEGIC_RI_OUTCOME)
            )
            if contextual_here:
                return "direct", list(dict.fromkeys(european_here))[:4]

    # Derived EU relevance requires an explicit implication/comparator sentence;
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
    for sent in split_sentences(full):
        if contains_any(sent, EU_GENERIC) or bool(bounded_matches(sent, MEMBER_STATE_SCOPE)) or union_eu_word(sent, full):
            if contains_any(sent, derived_cues):
                return "derived", [sent[:260]]
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
    """Recognise a China-specific geopolitical bridge without document-wide co-occurrence.

    Earlier builds treated any ``China`` mention plus any generic ``strategic`` or
    ``competition`` wording anywhere in the title/abstract as geopolitical evidence.
    That admitted systematic reviews where China was merely one study location and
    phrases such as ``strategic use of local languages`` occurred elsewhere.  Require
    bounded China wording and a genuinely strategic cue in the same sentence instead.
    """
    sentences = split_sentences(text) or [clean_text(text)]
    for snt in sentences:
        if not bounded_matches(snt, CHINA_CONTEXT):
            continue
        if contains_any(snt, CHINA_GEO_CONTEXT):
            return True
    return False


def research_talent_flow_signal(text: str) -> bool:
    """Detect cross-border research-workforce allocation and the research-talent pipeline.

    Generic student mobility remains out of scope. International/third-country students or
    graduates count only when the same source explicitly connects them to doctoral/STEM or
    research/innovation capacity AND to retention, post-study work, research careers or a
    transition into the innovation/research workforce. Visiting researchers and research
    visits are directly in scope because they are already research-workforce mobility.
    """
    low = normalized(text)
    explicit = distinct_matches(low, RESEARCH_TALENT_FLOW_EXPLICIT)
    actors = distinct_matches(low, RESEARCH_TALENT_ACTORS)
    actions = distinct_matches(low, RESEARCH_TALENT_FLOW_ACTIONS)

    pipeline_student = bool(re.search(
        r"\b(?:international|foreign|non eu|non-eu|third country|third-country|extra eu|extra-eu)\b.{0,45}"
        r"\b(?:doctoral candidates?|phd students?|doctoral students?|stem students?|international students?|graduates?)\b|"
        r"\b(?:doctoral candidates?|phd students?|doctoral students?|stem students?|international students?|graduates?)\b.{0,45}"
        r"\b(?:international|foreign|non eu|non-eu|third country|third-country|extra eu|extra-eu)\b",
        low,
    ))
    pipeline_ri = bool(re.search(
        r"\b(?:research|researcher|scientific|science|innovation|innovative|stem|doctoral|phd|r&d|innovation ecosystem|research workforce|scientific workforce)\b",
        low,
    ))
    pipeline_transition = bool(re.search(
        r"\b(?:retain|retention|stay|remain|post study|post-study|post research|post-research|job search|employment|career|workforce|labour market|labor market|recruit|attract)\w*\b",
        low,
    ))
    research_pipeline = pipeline_student and pipeline_ri and pipeline_transition
    visitor_pipeline = bool(re.search(
        r"\b(?:international|foreign|non eu|non-eu|third country|third-country|extra eu|extra-eu)\b.{0,45}"
        r"\b(?:visiting researchers?|research visitors?|scientific visitors?)\b|"
        r"\b(?:visiting researchers?|research visitors?|scientific visitors?)\b.{0,45}"
        r"\b(?:international|foreign|non eu|non-eu|third country|third-country|extra eu|extra-eu)\b",
        low,
    )) and bool(re.search(
        r"\b(?:expertise|capacity|capability|competitiveness|collaboration|cooperation|mobility|access|talent|innovation|research system|scientific capacity|research capacity)\b",
        low,
    ))

    research_workforce = bool(actors or research_pipeline or visitor_pipeline or contains_any(low, [
        "research career", "research careers", "research workforce", "scientific workforce",
        "research talent", "scientific talent", "postdoc", "postdoctoral", "doctoral researcher",
        "research staff", "academic staff", "faculty", "professor", "professors",
        "visiting researcher", "visiting researchers", "research visitor", "research visitors",
        "scientific visitor", "scientific visitors",
    ]))
    student_focused = contains_any(low, [
        "student mobility", "students mobility", "international students", "student migration",
        "erasmus student", "undergraduate", "master students", "masters students", "student experience",
    ])
    if student_focused and not research_pipeline and not any(x in low for x in [
        "doctoral researcher", "doctoral candidate", "phd student", "research workforce",
        "research talent", "scientific talent", "research career", "innovation ecosystem",
    ]):
        return False
    if explicit:
        generic_brain = any(x in explicit for x in ("brain drain", "brain gain"))
        specific_research_flow = any(
            x.startswith("researcher") or x.startswith("scientist") or
            x.startswith("research talent") or x.startswith("scientific talent") or
            x.startswith("research brain") or x.startswith("scientific brain") or
            x.startswith("international researcher") or x.startswith("visiting researcher") or
            x.startswith("research visits") or x.startswith("international doctoral")
            for x in explicit
        )
        if generic_brain and not specific_research_flow and not research_workforce:
            return False
        return True
    if research_pipeline or visitor_pipeline:
        return bool(has_eu_word(low) or bounded_matches(low, MEMBER_STATE_SCOPE) or contains_any(low, [
            "europe", "european", "european union", "eu competitiveness", "european research area"
        ]))
    if not (research_workforce and actions):
        return False
    return bool(
        contains_any(low, ["cross-border", "international", "abroad", "foreign", "overseas", "europe", "european union"])
        or has_eu_word(low)
        or bounded_matches(low, MEMBER_STATE_SCOPE)
    )


def geopolitical_matches(text: str) -> list[str]:
    """Return geopolitical/economic-security hits with ambiguous legal terms filtered."""
    matches = distinct_matches(text, GEO_STRONG)
    low = normalized(text)
    if "sanctions" in matches:
        local_legal = bool(re.search(r"\b(administrative|disciplinary|criminal|civil|traffic|parental|regulatory) sanctions\b", low))
        strategic_sanctions = bool(re.search(
            r"\b(economic|trade|financial|international|technology|sectoral|secondary) sanctions\b|"
            r"\bsanctions (?:against|on|regime|policy|package)\b|\brestrictive measures\b",
            low,
        ))
        if local_legal and not strategic_sanctions:
            matches = [m for m in matches if m != "sanctions"]
    return matches



def _strip_relevance_boilerplate(text: str) -> str:
    """Remove common funding/boilerplate sentences before topical admission.

    A Horizon-Europe acknowledgement does not make the *subject* of a paper EU R&I,
    and a copyright/navigation footer does not make an institutional page analytical.
    """
    kept = []
    for sent in split_sentences(text):
        low = normalized(sent)
        if any(x in low for x in [
            'funded by the european union', 'received funding from the european union',
            'horizon europe research and innovation programme under grant',
            'grant agreement no', 'grant agreement number', 'co-funded by the european union',
            'views and opinions expressed', 'neither the european union nor the granting authority',
            'the automated admission gate found', 'its eu relevance is classified as',
            'the publication examines',
        ]):
            continue
        # A paper does not become an R&I/geopolitics paper because its conclusion lists
        # generic topics for a future research agenda. Keep substantive findings, but
        # ignore agenda boilerplate when it is the only R&I-looking sentence.
        if ('future research' in low or 'research agenda' in low or 'avenues for future research' in low) and not any(x in low for x in [
            'research security', 'science diplomacy', 'horizon europe', 'fp10', 'european research area',
            'research funding', 'research collaboration', 'scientific collaboration', 'research policy',
            'innovation policy', 'science policy', 'r&d investment', 'research and development investment',
        ]):
            continue
        kept.append(sent)
    return ' '.join(kept) if kept else clean_text(text)


A_RI_CORE = [
    'research and innovation', 'research & innovation', 'r&i', 'research policy',
    'innovation policy', 'science policy', 'research security', 'knowledge security',
    'science diplomacy', 'research collaboration', 'scientific collaboration',
    'science and technology cooperation', 'scientific cooperation',
    'international research cooperation', 'international scientific cooperation',
    'research funding', 'research programme', 'research program', 'horizon europe', 'fp10',
    'european research area', 'research system', 'innovation system', 'research governance',
    'innovation governance', 'research excellence', 'innovation ecosystem',
    'research and development', 'r&d', 'scientific capacity', 'research capacity',
    'innovation capacity', 'innovation performance', 'technology development',
    'industrial research', 'industrial innovation', 'technological innovation', 'deep tech', 'technology transfer',
    'technological capabilities', 'technology capabilities', 'research infrastructure', 'research infrastructures',
    'scientific infrastructure', 'university research', 'academic research',
    'research-intensive', 'research organisation', 'research organization',
    'research-performing', 'research workforce', 'scientific workforce',
    'research talent', 'scientific talent', 'research careers', 'scientific careers',
    'doctoral candidates', 'doctoral training', 'international researchers', 'visiting researchers',
    'research visits', 'international doctoral candidates', 'post-study research careers',
]

A_TECH_DOMAINS = [
    'critical technology', 'critical technologies', 'strategic technology', 'strategic technologies',
    'semiconductor', 'semiconductors', 'artificial intelligence', ' ai ', 'quantum', 'biotechnology',
    'biotech', 'advanced materials', 'robotics', 'space technology', 'satellite technology',
    'nuclear technology', 'clean technology', 'clean tech', 'digital infrastructure',
    'compute infrastructure', 'supercomputer', 'data centre', 'data center', 'cloud infrastructure',
]

A_TECH_RI_MECHANISMS = [
    'research', 'r&d', 'research and development', 'innovation', 'innovative', 'science',
    'technology development', 'development programme', 'development program', 'funding',
    'research infrastructure', 'testbed', 'testing infrastructure', 'pilot line', 'prototype',
    'innovation ecosystem', 'startup', 'start-up', 'scale-up', 'scaleup', 'commercialisation',
    'commercialization', 'patent', 'scientific capacity', 'innovation capacity',
    'technological capability', 'technological capabilities', 'technology governance', 'technological leadership',
    'technology leadership', 'industrial policy', 'competitiveness', 'research capacity',
]

A_FOCUS_EXCLUDE_TITLE = [
    'annual activity report', 'annual activities report', 'activities report', 'annual management and performance report',
    'annual report on', 'guidelines on accessible communications',
]

# V17.8: Strand A is a radar for major EU R&I under geopolitical competition, not a
# catch-all for any European sector where R&D or competitiveness appears.  The major-focus
# gate keeps system-level R&I issues and strategically consequential technology/capability
# domains while excluding incidental consumer, education, health-service and sports topics.
A_MAJOR_RI_SYSTEM = [
    'research and innovation', 'research & innovation', 'r&i', 'research policy', 'innovation policy',
    'science policy', 'research security', 'knowledge security', 'science diplomacy',
    'horizon europe', 'fp10', 'framework programme', 'european research area',
    'research system', 'innovation system', 'research governance', 'innovation governance',
    'research infrastructure', 'research infrastructures', 'scientific infrastructure',
    'research funding', 'research programme', 'research program', 'international research cooperation',
    'scientific collaboration', 'research collaboration', 'research talent', 'scientific talent',
    'research workforce', 'scientific workforce', 'brain drain', 'brain gain', 'technology transfer',
    'industrial innovation', 'deep tech', 'technological sovereignty', 'technology sovereignty',
    'strategic autonomy', 'economic security', 'strategic dependency', 'strategic dependencies',
]
A_MAJOR_TECH_DOMAINS = [
    'semiconductor', 'semiconductors', 'microelectronics', 'artificial intelligence', ' ai ',
    'quantum', 'biotechnology', 'biotech', 'advanced materials', 'critical raw materials',
    'critical minerals', 'space technology', 'satellite', 'nuclear technology', 'reactor',
    'clean technology', 'clean tech', 'battery', 'batteries', 'digital infrastructure',
    'compute infrastructure', 'supercomputer', 'cloud infrastructure', 'cybersecurity',
    'dual-use', 'dual use', 'defence technology', 'defense technology', 'robotics',
]
A_OFFTOPIC_CONSUMER_OR_LOCAL = [
    'table tennis', 'basketball', 'football', 'soccer', 'tennis equipment', 'sports equipment',
    'sport equipment', 'hospital bed', 'hotel', 'hospitality branding', 'tourism', 'restaurant',
    'school teaching', 'smart teaching', 'classroom', 'agricultural marketing', 'marketing logistics',
]


def _major_a_focus(text: str, explicit_geo: bool) -> bool:
    """Require system-level or strategically consequential EU R&I centrality.

    Explicit geopolitical papers receive a little more latitude, but a low-stakes consumer/local
    sector still needs a recognised strategic technology or R&I-system mechanism to qualify.
    """
    low = normalized(text)
    system = bool(distinct_matches(low, A_MAJOR_RI_SYSTEM))
    strategic_tech = bool(distinct_matches(low, A_MAJOR_TECH_DOMAINS))
    off_topic = bool(distinct_matches(low, A_OFFTOPIC_CONSUMER_OR_LOCAL))
    if off_topic and not (system or strategic_tech):
        return False
    if system or strategic_tech:
        return True
    # Allow a genuinely geopolitical industrial-capability paper only when the text explicitly
    # concerns EU/European technology/innovation capability, not generic sector competitiveness.
    return bool(explicit_geo and re.search(
        r'\b(?:eu|europe|european)\b.{0,100}\b(?:technology|technological|innovation|research|r&d|industrial capability|production capacity)\b',
        low, re.I
    ))

B_METHOD_FAMILIES = [
    # Core futures/foresight methods. These are the methods Strand B is actually about.
    'strategic foresight', 'foresight methodology', 'foresight method', 'foresight methods',
    'horizon scanning', 'weak signal detection', 'weak signals detection', 'weak signal analysis',
    'scenario planning', 'scenario construction', 'scenario building', 'scenario development',
    'scenario methodology', 'backcasting', 'cross-impact analysis', 'cross impact analysis',
    'technology roadmapping', 'technology roadmap', 'roadmapping', 'wild cards', 'wild card',
    'futures wheel', 'causal layered analysis', 'emerging issue detection',
    # Auxiliary techniques can support a futures method, but never qualify by themselves.
    'delphi', 'real-time delphi', 'policy delphi', 'morphological analysis',
    'system dynamics', 'agent-based modelling', 'agent-based modeling', 'expert elicitation',
    'bibliometric forecasting', 'scientometric forecasting', 'patent landscaping', 'patent analytics',
    'technology intelligence', 'strategic intelligence', 'early warning',
]

# A publication must visibly develop/adapt/extend/refine a *futures method as such*.
# Domain prediction systems, assessment frameworks and ordinary Delphi applications are not B,
# even when they are technically novel or described as an "early-warning method".
B_CORE_FUTURES_METHODS = [
    'strategic foresight', 'foresight methodology', 'foresight method', 'foresight methods',
    'horizon scanning', 'weak signal detection', 'weak signals detection', 'weak signal analysis',
    'scenario planning', 'scenario construction', 'scenario building', 'scenario development',
    'scenario methodology', 'backcasting', 'cross-impact analysis', 'cross impact analysis',
    'technology roadmapping', 'technology roadmap', 'roadmapping', 'wild cards', 'wild card',
    'futures wheel', 'causal layered analysis', 'emerging issue detection',
]

B_AUXILIARY_METHODS = [
    'delphi', 'real-time delphi', 'policy delphi', 'morphological analysis',
    'system dynamics', 'agent-based modelling', 'agent-based modeling', 'expert elicitation',
    'bibliometric forecasting', 'scientometric forecasting', 'patent landscaping', 'patent analytics',
    'technology intelligence', 'strategic intelligence', 'early warning',
]

# V17.7 expansion route: methods developed to detect, map or forecast change in research,
# science, innovation and technology can be useful for studying R&I futures even when the paper
# does not label itself as generic "foresight". They still need an explicit method-development
# claim plus a forward-looking R&I/technology context, so ordinary bibliometrics, patent counts,
# Delphi applications and domain prediction systems remain outside B.
B_RI_FUTURES_METHODS = [
    'bibliometric forecasting', 'scientometric forecasting', 'patent landscaping', 'patent analytics',
    'technology intelligence', 'strategic intelligence', 'technology forecasting',
    'emerging technology detection', 'technology emergence detection', 'research front detection',
    'science mapping', 'technology mapping', 'innovation mapping', 'research landscape mapping',
    'technology trajectory analysis', 'technological trajectory analysis', 'topic evolution analysis',
    'technology convergence detection', 'science technology intelligence', 'science and technology intelligence',
    'robust decision making', 'adaptive pathways', 'research portfolio analysis', 'innovation portfolio analysis',
    'multi-criteria portfolio', 'multi criteria portfolio', 'innovation portfolio method', 'research portfolio method',
]
B_RI_FUTURES_FRAMING = [
    'forecast', 'forecasting', 'future', 'futures', 'forward-looking', 'forward looking', 'anticipatory',
    'emerging technology', 'emerging technologies', 'emerging research', 'emerging topic', 'emerging topics',
    'research front', 'research fronts', 'early detection', 'detect emergence', 'technology emergence',
    'technology trajectory', 'technological trajectory', 'innovation trajectory', 'topic evolution',
    'technology evolution', 'technological evolution', 'technology convergence', 'convergence',
    'long-term', 'long term', 'strategic intelligence', 'technology intelligence',
    'strategic uncertainty', 'deep uncertainty', 'robust decision', 'adaptive pathways', 'portfolio',
]
B_RI_METHOD_CONTEXT = [
    'research', 'science', 'scientific', 'innovation', 'technology', 'technological', 'r&d',
    'patent', 'patents', 'publication', 'publications', 'bibliometric', 'scientometric',
    'research policy', 'science policy', 'innovation policy', 'technology policy', 'industrial policy',
    'research system', 'innovation system', 'science system', 'technology ecosystem',
]

# Auxiliary techniques become B candidates only when the same title/abstract explicitly frames
# them as part of foresight/futures work. "Early warning" in medicine, engineering, finance,
# astronomy, infrastructure monitoring, etc. is deliberately outside Strand B.
B_EXPLICIT_FUTURES_FRAMING = [
    'strategic foresight', 'foresight', 'futures studies', 'futures research', 'future studies',
    'horizon scanning', 'weak signal', 'weak signals', 'scenario planning', 'scenario construction',
    'scenario building', 'backcasting', 'anticipatory', 'alternative futures', 'possible futures',
    'future scenarios', 'long-term futures', 'long term futures', 'strategic uncertainty',
    'emerging issues', 'emerging issue',
]

B_METHOD_CONTRIBUTION_CUES = [
    'new method', 'new methodology', 'new framework', 'new protocol', 'new toolkit',
    'novel method', 'novel methodology', 'novel framework', 'novel protocol', 'novel toolkit',
    'method development', 'methodological development', 'method design', 'methodological design',
    'adapted method', 'adapted methodology', 'extended method', 'extended methodology',
    'refined method', 'refined methodology', 'reusable method', 'transferable method',
    'generalizable method', 'generalisable method',
]

B_METHOD_CREATION_CUES = B_METHOD_CONTRIBUTION_CUES

# Creation must point to a method/framework/protocol/toolkit/approach AND the sentence must also
# contain a real futures/foresight family. This prevents "we develop an earthquake early-warning
# framework" or "we develop a Delphi assessment framework" from being treated as futures methods.
B_CREATION_VERBS = re.compile(
    r'\b(?:develop(?:s|ed|ing)?|propos(?:e|es|ed|ing)|introduc(?:e|es|ed|ing)|design(?:s|ed|ing)?|'
    r'adapt(?:s|ed|ing)?|extend(?:s|ed|ing)?|refin(?:e|es|ed|ing)|creat(?:e|es|ed|ing)|'
    r'construct(?:s|ed|ing)?|formulat(?:e|es|ed|ing)|operationali[sz](?:e|es|ed|ing))\b'
    r'.{0,140}\b(?:method|methodology|approach|framework|toolkit|protocol)\b',
    re.I,
)
B_CREATION_PASSIVE = re.compile(
    r'\b(?:method|methodology|approach|framework|toolkit|protocol)\b.{0,45}\b(?:is|was|were|has been|have been)\s+'
    r'(?:developed|proposed|introduced|designed|adapted|extended|refined|created|constructed|formulated|operationalised|operationalized)\b',
    re.I,
)

B_TRANSFERABILITY_CUES = [
    'transferable', 'reusable', 'generalizable', 'generalisable', 'adaptable', 'replicable',
    'across policy domains', 'across domains', 'across sectors', 'other policy contexts',
    'other contexts', 'general framework', 'generic framework', 'modular framework',
]

B_SUITABILITY_CONTEXT = [
    'research', 'science', 'innovation', 'technology', 'r&d', 'public policy', 'policy',
    'governance', 'geopolit', 'geoeconomic', 'economic security', 'strategic competition',
    'international relations', 'security policy', 'industrial policy', 'technology policy',
    'science policy', 'innovation policy', 'research policy', 'critical technology',
    'emerging technology', 'complex systems', 'systemic risk', 'uncertainty', 'strategy',
]

B_STRATEGIC_RI_RELEVANCE = [
    # A B-paper needs a policy/R&I/technology-system destination, not merely the word
    # 'foresight' or 'uncertainty' describing its own method.
    'research and innovation', 'research & innovation', 'r&i', 'research policy', 'innovation policy',
    'science policy', 'technology policy', 'science and technology policy', 'public policy',
    'policymaking', 'policy making', 'public decision-making', 'public decision making', 'strategic decision-making',
    'anticipatory governance', 'policy domains', 'emerging technology', 'emerging technologies',
    'critical technology', 'critical technologies', 'technology intelligence', 'strategic intelligence',
    'research front', 'research fronts', 'innovation trajectories', 'technology trajectories',
    'technology fields', 'industrial policy', 'geopolit', 'geoeconomic', 'economic security',
    'strategic competition', 'research portfolio', 'r&i portfolio',
]
B_OFFTOPIC_APPLICATION_DOMAINS = [
    'table tennis', 'basketball', 'football', 'soccer', 'sports equipment', 'sport equipment',
    'hospitality branding', 'hotel branding', 'tourism marketing', 'school teaching', 'smart teaching',
    'forest pest', 'forest pests', 'hospital bed', 'gold mining', 'patient education',
]

def _method_matches(text: str, terms: list[str]) -> list[str]:
    # Metadata frequently alternates between "horizon scanning" and "horizon-scanning".
    # Normalise separators before bounded matching so punctuation does not decide B admission.
    return distinct_matches(re.sub(r'[-–—/]+', ' ', clean_text(text)), terms)


def _ri_hits(text: str) -> list[str]:
    """R&I evidence for Strand A, keeping generic technology out unless an R&I mechanism is explicit."""
    txt = _strip_relevance_boilerplate(text)
    hits = distinct_matches(txt, A_RI_CORE)
    if research_talent_flow_signal(txt) and 'research-talent flow / brain drain' not in hits:
        hits.append('research-talent flow / brain drain')
    for sent in split_sentences(txt):
        if distinct_matches(sent, ['knowledge transfer']) and distinct_matches(sent, [
            'research', 'science', 'innovation', 'technology', 'r&d', 'university research', 'research collaboration'
        ]):
            if 'knowledge transfer' not in hits:
                hits.append('knowledge transfer')
    # Strategic technologies are in scope only when research/innovation/capability-building
    # is part of the same sentence. Bare AI/cyber/digital/security topics are not R&I.
    for sent in split_sentences(txt):
        domains = distinct_matches(sent, A_TECH_DOMAINS)
        mechanisms = distinct_matches(sent, A_TECH_RI_MECHANISMS)
        if domains and mechanisms:
            label = f"{domains[0]} + {mechanisms[0]}"
            if label not in hits:
                hits.append(label)
    return hits


def _geo_hits(text: str) -> list[str]:
    """Geopolitical/economic-security evidence with ambiguous organisational terms filtered."""
    hits = geopolitical_matches(text)
    low = normalized(text)
    if research_talent_flow_signal(text) and 'research-talent allocation / brain drain' not in hits:
        hits.append('research-talent allocation / brain drain')
    # 'Decoupling' is common in organisation/education literature. It is geopolitical only
    # with a cross-border strategic actor/trade/technology context.
    if 'decoupling' in hits and not (
        distinct_matches(low, GEO_ACTORS) or contains_any(low, [
            'trade', 'technology', 'supply chain', 'international', 'cross-border',
            'economic security', 'strategic competition', 'geopolit', 'china', 'united states', 'russia'
        ])
    ):
        hits = [x for x in hits if x != 'decoupling']
    return hits


def _bridge_sentence_for_a(text: str) -> str:
    for sent in split_sentences(text):
        if _ri_hits(sent) and _geo_hits(sent):
            return sent[:420]
    return ''


EXTERNAL_SHOCK_CUES = [
    'breakthrough', 'major breakthrough', 'first achieved', 'first demonstration', 'first demonstrated',
    'achieved artificial general intelligence', 'artificial general intelligence achieved', 'agi achieved',
    'step change', 'step-change', 'surpassed', 'world first', 'world-first', 'record performance',
    'frontier capability', 'frontier model', 'deployed at scale', 'deployment at scale',
    'export ban', 'export restriction', 'cut off access', 'supply cutoff', 'embargo',
    'dominant supplier', 'monopoly', 'controls the supply', 'controls supply',
]
EXTERNAL_SHOCK_ACTORS = [
    'china', 'chinese', 'united states', 'u.s.', 'american', 'russia', 'russian',
    'japan', 'south korea', 'korea', 'taiwan', 'india', 'united kingdom', 'britain', 'uk',
]
EXTERNAL_SHOCK_DOMAIN_LABELS = {
    'artificial intelligence': ['artificial intelligence', ' ai ', 'agi', 'foundation model', 'frontier model'],
    'semiconductors': ['semiconductor', 'semiconductors', 'chips', 'microelectronics'],
    'quantum': ['quantum'],
    'biotechnology': ['biotechnology', 'biotech', 'synthetic biology'],
    'advanced materials': ['advanced materials', 'critical materials'],
    'space': ['space technology', 'satellite', 'launch vehicle'],
    'compute': ['supercomputer', 'compute infrastructure', 'data centre', 'data center', 'cloud infrastructure'],
    'robotics': ['robotics', 'robot', 'autonomous system'],
}

def _external_shock_domain(text: str) -> str:
    low = f" {normalized(text)} "
    for label, terms in EXTERNAL_SHOCK_DOMAIN_LABELS.items():
        if distinct_matches(low, terms):
            return label
    return ''

def _anchor_supports_external_domain(anchor: dict[str, Any], domain: str) -> bool:
    if not isinstance(anchor, dict) or not domain:
        return False
    text = clean_text(' '.join(str(anchor.get(k, '')) for k in ('title','summary','core_message','relevance_note')))
    return _external_shock_domain(text) == domain and bool(eu_evidence(anchor.get('title',''), anchor.get('summary',''), anchor.get('relevance_note',''))[0] == 'direct')

def external_eu_bridge_sentence(text: str, anchors: list[dict[str, Any]] | None = None) -> tuple[bool, str, list[str]]:
    """Inference-only external admission is permanently disabled.

    External developments can still enter Strand A when the source itself establishes direct
    EU/European R&I + geopolitical/economic-security relevance; those records pass through
    ``eu_evidence`` and the ordinary source-supported A gate. This legacy helper remains only
    so old call sites fail closed instead of manufacturing a Europe-impact sentence.
    """
    return False, "", []

def _a_focus_ok(title: str, abstract: str, body: str, source_kind: str) -> tuple[bool, list[str], list[str], str, str, list[str]]:
    title = clean_text(title)
    abstract = _strip_relevance_boilerplate(abstract)
    body = _strip_relevance_boilerplate(body)
    ta = clean_text(f'{title}. {abstract}')
    lead = clean_text(f'{ta}. {body[:6000]}')
    title_low = normalized(title)
    if any(x in title_low for x in A_FOCUS_EXCLUDE_TITLE):
        return False, [], [], '', '', []

    evidence_text = ta if source_kind == 'scholarly' else lead
    ri = _ri_hits(evidence_text)
    geo = _geo_hits(evidence_text)
    bridge = _bridge_sentence_for_a(evidence_text)
    ri_ta = _ri_hits(ta)
    geo_ta = _geo_hits(ta)

    # Primary route: explicit R&I + geopolitical/economic-security evidence.
    if source_kind == 'scholarly':
        explicit_focus = bool(ri_ta and geo_ta)
    else:
        # Curated institutional analytical work may establish one side in title/description and
        # the other in the executive lead. Requiring a same-sentence bridge discarded reports
        # whose abstracts use neutral policy language before discussing the strategic mechanism.
        explicit_focus = bool(ri and geo)

    # Secondary route: direct empirical mechanism of Europe's external R&I position. This route
    # deliberately does not accept generic competitiveness/capacity alone.
    context_text = ta if source_kind == 'scholarly' else lead
    external = distinct_matches(context_text, A_EXTERNAL_RELATION)
    outcomes = distinct_matches(context_text, A_STRATEGIC_RI_OUTCOME)
    implied_ok, implied_families, implied_terms = implied_strategic_context(context_text)
    if source_kind == 'scholarly':
        contextual_focus = bool(ri_ta and (implied_ok or (external and outcomes)))
    else:
        contextual_focus = bool(ri and (implied_ok or (external and outcomes)))
    # The contextual route is an expansion route, so page-type noise is fail-closed here.
    # This does not affect explicit A evidence or Strand B method papers whose abstracts may
    # legitimately mention workshops, calls, facilities or other methodological context.
    if contextual_focus and document_exclusion_reason(title, context_text):
        contextual_focus = False

    focus = bool(explicit_focus or contextual_focus)
    # V17.8.1: major-EU-R&I is a ranking objective, not a blanket corpus gate.
    # Hard rejection is reserved for obvious contamination (sports/consumer/local topics)
    # that only happen to mention R&D/competition. Broad but genuinely relevant papers stay
    # available and are ranked below system-level/geostrategic work.
    if focus and bool(CONFIG.get('major_eu_ri_focus', True)):
        low = normalized(context_text)
        off_topic = bool(distinct_matches(low, A_OFFTOPIC_CONSUMER_OR_LOCAL))
        strategic_tech = bool(distinct_matches(low, A_MAJOR_TECH_DOMAINS))
        system = bool(distinct_matches(low, A_MAJOR_RI_SYSTEM))
        if off_topic and not (strategic_tech or system):
            focus = False
            explicit_focus = False
            contextual_focus = False
    route = 'explicit-geopolitics' if explicit_focus else ('triangulated-strategic-context' if contextual_focus else '')
    context_evidence = list(dict.fromkeys(implied_families + implied_terms + external + outcomes))[:8] if contextual_focus else []
    return focus, ri, geo, bridge, route, context_evidence


def _b_method_evidence(title: str, abstract: str, body: str, source_kind: str, source_tier: int) -> tuple[bool, list[str], str, list[str], str]:
    """Return whether a publication develops a reusable method for studying futures of Strand A.

    Two admission routes are allowed:
      1. a futures/foresight method as such (the V17.6 precision route); or
      2. a newly developed forward-looking method for detecting, mapping or forecasting change
         in research, science, innovation or technology (V17.7 R&I-futures transfer route).

    Both routes require a genuine method-development claim in title/abstract. Ordinary method
    use, reviews, domain early-warning systems, descriptive bibliometrics/patent studies and
    generic assessment frameworks still fail.
    """
    title = clean_text(title)
    abstract = clean_text(abstract)
    ta = clean_text(f'{title}. {abstract}')
    if not ta:
        return False, [], '', [], ''

    all_families = _method_matches(ta, B_METHOD_FAMILIES + B_RI_FUTURES_METHODS)
    core_families = _method_matches(ta, B_CORE_FUTURES_METHODS)
    auxiliary = _method_matches(ta, B_AUXILIARY_METHODS)
    ri_families = _method_matches(ta, B_RI_FUTURES_METHODS)
    futures_framing = distinct_matches(ta, B_EXPLICIT_FUTURES_FRAMING)
    ri_future_framing = distinct_matches(ta, B_RI_FUTURES_FRAMING)
    ri_context = distinct_matches(ta, B_RI_METHOD_CONTEXT)
    if not all_families:
        return False, [], '', [], ''

    classic_candidate = core_families or (auxiliary if futures_framing else [])
    ri_transfer_candidate = bool(ri_families and ri_future_framing and ri_context)
    candidate_families = core_families or (auxiliary if futures_framing else []) or (ri_families if ri_transfer_candidate else [])
    if not candidate_families:
        return False, all_families[:5], '', [], ''

    strategic_ri_context = distinct_matches(ta, B_STRATEGIC_RI_RELEVANCE)
    off_topic_application = distinct_matches(ta, B_OFFTOPIC_APPLICATION_DOMAINS)
    # Live Strand-B discovery remains precision-first: the method must have a policy/R&I/
    # technology-system destination. V17.8.1 only changes *historical migration*: older saved
    # B records are not mass-deleted from shortened summaries.
    if not strategic_ri_context:
        return False, candidate_families[:5], '', [], ''
    if off_topic_application and not distinct_matches(ta, [
        'research and innovation', 'innovation policy', 'research policy', 'science policy',
        'technology policy', 'public policy', 'policy domains', 'emerging technology',
        'critical technology', 'economic security', 'geopolit', 'strategic competition'
    ]):
        return False, candidate_families[:5], '', [], ''

    # "Scenario construction/building/development" is linguistically ambiguous: it can mean
    # constructing a simulated teaching/engineering scene rather than a future scenario. When
    # these are the only futures-family hits, require an independent temporal/strategic futures
    # cue. This keeps genuine scenario methodology while blocking false positives such as
    # smart-classroom scenario construction.
    ambiguous_scenario_only = bool(candidate_families) and all(
        f in {'scenario construction', 'scenario building', 'scenario development'} for f in candidate_families
    )
    if ambiguous_scenario_only and not re.search(
        r'\b(?:future|futures|foresight|anticipat\w*|long[- ]term|alternative futures|possible futures|strategic scenario\w*|scenario planning)\b',
        normalized(ta),
    ):
        return False, candidate_families[:5], '', [], ''

    def sentence_is_candidate(sent: str) -> bool:
        sent_core = _method_matches(sent, B_CORE_FUTURES_METHODS)
        sent_aux = _method_matches(sent, B_AUXILIARY_METHODS)
        sent_ri = _method_matches(sent, B_RI_FUTURES_METHODS)
        sent_futures = distinct_matches(sent, B_EXPLICIT_FUTURES_FRAMING)
        sent_ri_future = distinct_matches(sent, B_RI_FUTURES_FRAMING)
        sent_ri_context = distinct_matches(sent, B_RI_METHOD_CONTEXT)
        return bool(
            sent_core
            or (sent_aux and sent_futures)
            or (sent_ri and sent_ri_future and sent_ri_context)
        )

    creation_bridge = ''
    for sent in split_sentences(ta):
        if not sentence_is_candidate(sent):
            continue
        low = re.sub(r'[-–—/]+', ' ', normalized(sent))
        low = re.sub(r'^design\s+methodology\s+approach\s+', '', low)
        if re.search(r'\b(?:does not|do not|did not|not|without)\b.{0,120}\b(?:develop|propos|introduc|design|adapt|extend|refin|creat|construct|formulat|operationalis|operationaliz)\w*', low):
            continue
        creation_language = bool(
            _method_matches(sent, B_METHOD_CREATION_CUES)
            or B_CREATION_VERBS.search(low)
            or B_CREATION_PASSIVE.search(low)
            or re.search(
                r'\b(?:new|novel|adapted|extended|refined|reusable|transferable)\b.{0,110}'
                r'\b(?:foresight|horizon scanning|weak signal|scenario|backcasting|cross impact|roadmap|futures|'
                r'bibliometric|scientometric|patent|technology intelligence|technology forecasting|science mapping|'
                r'technology mapping|research front|emerging technology|trajectory|convergence|robust decision|adaptive pathways|portfolio)\b',
                low,
            )
        )
        if creation_language:
            creation_bridge = sent[:420]
            break

    title_norm = re.sub(r'[-–—/]+', ' ', normalized(title))
    title_candidate = sentence_is_candidate(title)
    title_creation = bool(
        title_candidate and (
            _method_matches(title, B_METHOD_CREATION_CUES)
            or re.search(
                r'\b(?:new|novel|developed|development|developing|design|adapted|adapting|adaptation|extended|extension|'
                r'refined|refinement|proposed|proposing)\b.{0,110}\b(?:foresight|horizon scanning|weak signal|scenario planning|'
                r'scenario construction|backcasting|cross impact|roadmapping|delphi|system dynamics|agent based|method|methodology|'
                r'framework|protocol|toolkit|approach|bibliometric|scientometric|patent|technology intelligence|technology forecasting|'
                r'science mapping|technology mapping|research front|emerging technology|trajectory|convergence|robust decision|adaptive pathways|portfolio)\b',
                title_norm,
            )
        )
    )

    # Method papers do not always use the performative verbs "we develop/propose". A method-first
    # title plus validation/comparison/transfer evidence is sufficient when the paper is clearly
    # about the reusable analytical method rather than merely applying one in a case study.
    method_first_title = bool(
        title_candidate
        and re.search(r'\b(?:method|methodology|framework|toolkit|protocol|approach)\b', title_norm)
        and not re.search(r'\b(?:using|application of|applications of|case study|case studies)\b', title_norm)
    )
    contribution_evidence = bool(re.search(
        r'\b(?:validat|benchmark|compar(?:e|es|ed|ing|ison)|evaluat|robust|accuracy|performance|transferab|reusab|generaliz|generalis|procedure|workflow)\w*',
        normalized(abstract),
    ))
    explicit_non_creation = bool(re.search(
        r'\b(?:does not|do not|did not|without)\b.{0,140}\b(?:develop|propos|introduc|design|adapt|extend|refin|creat|construct|formulat|operationalis|operationaliz)\w*',
        normalized(abstract),
    )) or contains_any(normalized(abstract), ['existing method', 'existing methodology', 'existing framework', 'existing protocol'])
    method_contribution = bool(method_first_title and contribution_evidence and not explicit_non_creation)

    if not (creation_bridge or title_creation or method_contribution):
        return False, candidate_families[:5], '', [], ''

    review_like = bool(re.search(r'\b(?:review|synthesis|overview|perspective|commentary|lessons from|using|application of|applications of)\b', title_norm))
    if review_like and not (creation_bridge or method_contribution):
        return False, candidate_families[:5], '', [], ''

    # The R&I-futures route must remain about a reusable analytical method, not a domain-specific
    # prediction system that happens to mention technology. Requiring R&I/science/technology-system
    # context in the bibliographic evidence unit is the key guardrail.
    route = 'future-of-A-method' if classic_candidate else 'ri-futures-analytic-method'
    if route == 'ri-futures-analytic-method' and not ri_transfer_candidate:
        return False, candidate_families[:5], '', [], ''

    suitability = distinct_matches(ta, B_SUITABILITY_CONTEXT + B_RI_METHOD_CONTEXT)
    transferability = distinct_matches(ta, B_TRANSFERABILITY_CUES)
    method_bridge = creation_bridge or (abstract[:420] if method_contribution else '')
    return True, candidate_families[:5], method_bridge, (suitability + transferability)[:6], route

def gate_scope(title: str, abstract: str, body: str, source_tier: int, source_kind: str = 'general', eu_context_anchors: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Classify the three-layer radar model.

    A = substantive papers about EU R&I in a geopolitical/economic-security context.
    B = developed/adapted/extended/refined futures methods, plus forward-looking R&I/technology-analysis methods, reusable for understanding the future of A.
    C is handled separately in the current-development scanner and never admitted here.
    """
    title = clean_text(title)
    abstract = clean_text(abstract)
    body = clean_text(body)

    if not english_record_ok(f"{title}. {abstract}. {body[:2500]}", title=title):
        return {
            'a_pass': False, 'b_pass': False, 'a_focus_pass': False,
            'aboutness_pass': False, 'aboutness_reason': 'language', 'text_mode': '',
            'aboutness_evidence': {}, 'eu_relevance': None, 'eu_evidence': [],
            'ri_evidence': [], 'geo_evidence': [], 'bridge_sentence': '', 'a_route': '',
            'a_context_evidence': [], 'external_eu_bridge': '', 'external_eu_bridge_is_inference': False, 'bridge_supported': False, 'bridge_mode': '',
            'foresight_evidence': [], 'method_evidence': [], 'method_bridge': '',
            'b_transferable': False, 'b_methodology_first': False, 'b_suitability_evidence': [],
            'b_route': '', 'trend_only': False, 'source_tier': source_tier,
            'language_rejected': True,
        }

    a_focus, ri_hits, geo_hits, a_bridge, a_route, a_context = _a_focus_ok(title, abstract, body, source_kind)
    eu_rel, eu_hits = eu_evidence(title, abstract, body)
    external_ok = False
    external_bridge = ''
    external_evidence: list[str] = []
    if eu_rel != 'direct':
        external_ok, external_bridge, external_evidence = external_eu_bridge_sentence(
            clean_text(f"{title}. {abstract}. {body[:6000]}"),
            eu_context_anchors,
        )
    aboutness = aboutness_for_a(
        title, abstract, body, a_focus=a_focus, eu_rel=eu_rel, bridge=a_bridge,
        contextual_evidence=bool(a_context)
    )
    # A admission is source-supported and EU-centred. Inference-only external admission is
    # disabled; an external development must itself establish direct European relevance.
    a_pass = bool(a_focus and eu_rel == 'direct' and aboutness.get('pass'))
    if external_ok:
        a_route = 'external-strategic-shock'
        a_context = external_evidence
        a_bridge = external_bridge
        eu_rel = 'material_external'
        eu_hits = [external_bridge]
        a_focus = True
        if not ri_hits:
            domain = _external_shock_domain(clean_text(f"{title}. {abstract}. {body[:6000]}"))
            ri_hits = [f"{domain} capability shock"] if domain else ['strategic R&I capability shock']
        geo_hits = list(dict.fromkeys(geo_hits + external_evidence))[:8]
        aboutness = {**aboutness, 'pass': True, 'reason': 'external_strategic_shock_bridge'}

    b_pass, b_families, b_bridge, b_suitability, b_route = _b_method_evidence(
        title, abstract, body, source_kind, source_tier
    )

    return {
        'a_pass': a_pass,
        'b_pass': b_pass,
        'a_focus_pass': bool(a_focus),
        'aboutness_pass': bool(aboutness.get('pass')),
        'aboutness_reason': aboutness.get('reason', ''),
        'text_mode': aboutness.get('text_mode', ''),
        'aboutness_evidence': {
            'ri_sentences': aboutness.get('ri_sentences', 0),
            'geo_sentences': aboutness.get('geo_sentences', 0),
            'ri_terms': aboutness.get('ri_terms', [])[:6],
            'geo_terms': aboutness.get('geo_terms', [])[:6],
        },
        # Preserve the evaluated EU scope even when another A gate fails. Diagnostics must
        # not rewrite a strategic/aboutness failure as "no direct EU".
        'eu_relevance': eu_rel if eu_rel else ('derived' if b_pass else None),
        'eu_evidence': eu_hits if eu_rel in {'direct', 'material_external'} else (['method suitable for analysing future EU R&I/geopolitics'] if b_pass else []),
        'ri_evidence': ri_hits[:5],
        'geo_evidence': geo_hits[:5],
        'bridge_sentence': a_bridge,
        'a_route': a_route if a_pass else '',
        'a_context_evidence': a_context if a_pass else [],
        'external_eu_bridge': external_bridge if external_ok else '',
        'external_eu_bridge_is_inference': bool(external_ok),
        'bridge_supported': bool(a_bridge or (ri_hits and geo_hits)),
        'bridge_mode': 'external-context-sentence' if external_ok else ('sentence' if a_bridge else ('title/abstract' if a_pass else '')),
        'foresight_evidence': b_families[:5],
        'method_evidence': b_families[:5],
        'method_bridge': b_bridge,
        'b_transferable': b_pass,
        'b_methodology_first': b_pass,
        'b_suitability_evidence': b_suitability,
        'b_route': (b_route or 'future-of-A-method') if b_pass else '',
        'trend_only': bool(contains_any(title, TREND_ONLY_HINTS) and not b_pass),
        'source_tier': source_tier,
    }

def themes_for(text: str) -> list[str]:
    low = f" {normalized(text)} "
    result = []
    for name, terms in THEMES.items():
        if name == "EU–China S&T cooperation / de-risking":
            # Plain "China" is not an EU–China R&I theme by itself. Require both an
            # EU/European scope and R&I/S&T substance, or explicit cooperation/de-risking
            # language. This prevents unrelated China stories from being anchored to the
            # EU–China watch theme.
            china = contains_any(low, ["china", "chinese"])
            eu = contains_any(low, EU_DIRECT + EU_GENERIC + MEMBER_STATE_SCOPE)
            ri = contains_any(low, RI_STRONG + RI_GENERIC)
            explicit = contains_any(low, [
                "eu-china", "eu china", "europe-china", "europe china",
                "de-risk", "derisk", "science cooperation", "research cooperation",
                "science and technology cooperation",
            ])
            if explicit or (china and eu and ri):
                result.append(name)
            continue
        if distinct_matches(low, terms):
            result.append(name)
    return result


FINDING_CONTEXT_QUERY_MAP = {
    "research security / foreign interference": [
        'Europe research security international collaboration universities',
        'EU knowledge security research capability international coordination',
    ],
    "technology sovereignty / strategic autonomy": [
        'Europe research technological sovereignty dependency capability',
        'EU innovation strategic autonomy control technology access',
    ],
    "EU–China S&T cooperation / de-risking": [
        'EU China research cooperation capability dependency',
        'Europe China science technology de-risking research security',
    ],
    "export controls / dual use": [
        'Europe research export controls dual use innovation capability',
        'EU technology transfer controls research competitiveness',
    ],
    "fragmentation of global science": [
        'Europe scientific collaboration fragmentation research capability',
        'EU research international coordination global science fragmentation',
    ],
    "transatlantic / US–China S&T competition": [
        'Europe research US China technology competition capability',
        'EU transatlantic science technology dependence competitiveness',
    ],
    "critical and emerging technologies": [
        'Europe critical technologies research capability dependency',
        'EU AI quantum semiconductor biotech research competitiveness',
    ],
    "economic security and R&I": [
        'Europe research innovation economic security dependency capability',
        'EU R&D competitiveness strategic capability international coordination',
    ],
    "R&I competitiveness / technological capabilities": [
        'Europe research innovation technological capabilities global competition',
        'EU R&D capability gap competitiveness dependency',
    ],
    "supply chains / strategic dependencies": [
        'Europe research technology supply chain dependency resilience',
        'EU innovation critical inputs supply security capability',
    ],
    "Horizon Europe / FP10 international participation": [
        'Horizon Europe international participation research security capability',
        'FP10 international cooperation research competitiveness Europe',
    ],
    "science diplomacy": [
        'EU science diplomacy research international coordination capability',
    ],
    "research talent / mobility / brain drain": [
        'Europe research talent competition mobility retention',
        'EU scientific talent brain drain research capability',
    ],
}

def finding_context_query_bank(previous: dict[str, Any], limit: int = 12) -> list[str]:
    """Turn recurring live findings into a small rotating discovery lane.

    This affects discovery only. Every result still has to clear the ordinary
    source, recency, EU-R&I and triangulated strategic-context gates.
    """
    counts: dict[str, int] = {}
    for item in previous.get('strand_a', []) if isinstance(previous.get('strand_a'), list) else []:
        if not isinstance(item, dict):
            continue
        blob = ' '.join(clean_text(item.get(k, '')) for k in ('title', 'summary', 'core_message', 'relevance_note'))
        for theme in themes_for(blob):
            counts[theme] = counts.get(theme, 0) + 1
    ranked = [name for name, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    # Add unmapped live themes at the end through a conservative generic formulation.
    queries: list[str] = []
    for theme in ranked:
        mapped = FINDING_CONTEXT_QUERY_MAP.get(theme, [])
        if mapped:
            queries.extend(mapped)
        elif theme:
            queries.append(f'Europe research innovation {theme} competitiveness dependency capability')
        if len(queries) >= limit:
            break
    return list(dict.fromkeys(q for q in queries if clean_text(q)))[:limit]


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

    # Broad discovery is useful, but publication type alone is not a quality guarantee.
    # Outside the curated journal list, require a trusted scholarly host/publisher rather
    # than promoting every OpenAlex journal to Tier 2.
    host = clean_text(src.get("host_organization_name") or src.get("publisher"))
    trusted_publishers = [normalized(x) for x in CONFIG.get("trusted_broad_journal_publishers", []) if clean_text(x)]
    if (
        CONFIG.get("accept_trusted_publisher_peer_reviewed_journals", True)
        and source_type == "journal" and typ in {"article", "review"}
        and host and any(p in normalized(host) for p in trusted_publishers)
    ):
        return True, 2, 2.75, source_name or host, "Tier 2 trusted-publisher journal"

    if CONFIG.get("accept_broad_peer_reviewed_journals", False) and source_type == "journal" and typ in {"article", "review"}:
        return True, 2, 2.9, source_name or "Scholarly journal", "Tier 2 broad journal"

    # Preprints are allowed only from arXiv and are ranked as Tier 3.
    if typ in {"preprint", "posted-content", "working-paper", "working paper"}:
        if any(url_domain(u).endswith("arxiv.org") for u in openalex_locations(work)):
            return True, 3, 3.2, "arXiv", "Tier 3 preprint"

    return False, 9, 9.0, source_name or "Unknown source", ""


def _diag_inc(key: str, amount: int = 1) -> None:
    with ADMISSION_DIAGNOSTICS_LOCK:
        ADMISSION_DIAGNOSTICS[key] += amount


def _record_ab_gate_diagnostic(prefix: str, ev: dict[str, Any]) -> None:
    """Record the actual admission failure instead of collapsing it to EU scope."""
    _diag_inc(f"{prefix}_evaluated")
    if ev.get("a_pass") or ev.get("b_pass"):
        _diag_inc(f"{prefix}_admitted_gate")
        if ev.get("a_route"):
            _diag_inc(f"{prefix}_a_route_{ev.get('a_route')}")
        return
    reason = clean_text(ev.get("aboutness_reason"))
    if reason == "insufficient_text":
        _diag_inc(f"{prefix}_defer_insufficient_text")
    elif ev.get("eu_relevance") != "direct":
        _diag_inc(f"{prefix}_reject_no_direct_eu")
    elif reason in {"no_ri", "incidental_ri"} or not ev.get("ri_evidence"):
        _diag_inc(f"{prefix}_reject_no_ri")
    elif reason in {"no_geopolitics", "incidental_geopolitics", "no_substantive_bridge"}:
        _diag_inc(f"{prefix}_reject_no_strategic_context")
    elif not ev.get("a_focus_pass"):
        _diag_inc(f"{prefix}_reject_no_strategic_context")
    else:
        _diag_inc(f"{prefix}_reject_aboutness")



def scholarly_metadata_rescue_priority(
    title: str,
    *,
    query: str = "",
    source: str = "",
    publisher: str = "",
    published: dt.date | None = None,
    tier: int | None = None,
) -> int:
    """Rank abstract-less scholarly metadata for expensive DOI text recovery.

    This is a *recall* priority only. A high score never admits a record: after text
    recovery the ordinary language, quality, EU, R&I and strategic-context gates run
    unchanged. The point is to spend the small publisher-fetch budget on records whose
    title/source metadata already looks plausibly European and R&I-strategic instead of
    whichever abstract-less result happened to arrive first.
    """
    title = clean_text(title)
    if not title or document_exclusion_reason(title, ""):
        return -100
    t = normalized(title)
    q = normalized(query)
    src = normalized(source)
    pub = normalized(publisher)
    score = 0
    if has_eu_word(t) or contains_any(t, EU_DIRECT):
        score += 12
    elif contains_any(t, EU_GENERIC) or bounded_matches(t, MEMBER_STATE_SCOPE):
        score += 8
    elif has_eu_word(q) or contains_any(q, EU_DIRECT + EU_GENERIC):
        score += 3

    ri_hits = _ri_hits(title)
    if ri_hits:
        score += 7 + min(4, len(ri_hits))
    elif contains_any(t, ["technology", "technological", "innovation", "science", "research", "r&d", "university", "universities"]):
        score += 5

    if contains_any(t, GEO_STRONG) or contains_any(t, [
        "economic security", "research security", "strategic autonomy", "technology sovereignty",
        "technological sovereignty", "dependency", "dependencies", "de-risk", "derisk",
        "export control", "foreign interference", "strategic competition", "critical technology",
        "critical technologies", "semiconductor", "quantum", "artificial intelligence", "compute",
        "science diplomacy", "research cooperation", "talent mobility", "brain drain",
    ]):
        score += 8
    elif contains_any(q, GEO_STRONG) or contains_any(q, ["security", "sovereignty", "geopolit", "competition", "dependency", "cooperation"]):
        score += 3

    if tier is not None:
        if tier <= 1:
            score += 5
        elif tier <= 2:
            score += 3
    priority_journals = {normalized(x) for x in CONFIG.get("preferred_q1_journals_sjr2024", [])}
    if src in priority_journals:
        score += 4
    if any(x in f"{src} {pub}" for x in ["european commission", "european union", "oecd", "research policy", "science and public policy"]):
        score += 3
    if published:
        age = (dt.date.today() - published).days
        if age <= 45:
            score += 3
        elif age <= 120:
            score += 2
    return score


def build_admission_rejection_funnel(unique_gate_candidates: int = 0, genuinely_new_candidates: int = 0) -> dict[str, Any]:
    """Compress detailed counters into the reader/debugger funnel requested for zero-yield scans."""
    def n(key: str) -> int:
        return int(ADMISSION_DIAGNOSTICS.get(key, 0) or 0)
    raw = n("openalex_raw_records") + n("crossref_raw_records") + n("institution_pages_queued")
    evaluated = n("openalex_evaluated") + n("crossref_evaluated") + n("institution_evaluated")
    insufficient = n("openalex_defer_insufficient_text") + n("crossref_defer_insufficient_text") + n("institution_defer_insufficient_text")
    no_eu = n("openalex_reject_no_direct_eu") + n("crossref_reject_no_direct_eu") + n("institution_reject_no_direct_eu")
    no_ri = n("openalex_reject_no_ri") + n("crossref_reject_no_ri") + n("institution_reject_no_ri")
    no_strategy = n("openalex_reject_no_strategic_context") + n("crossref_reject_no_strategic_context") + n("institution_reject_no_strategic_context")
    other_aboutness = n("openalex_reject_aboutness") + n("crossref_reject_aboutness") + n("institution_reject_aboutness")
    gate_passed = n("openalex_admitted_gate") + n("crossref_admitted_gate") + n("institution_admitted_gate")
    enough_text = max(0, evaluated - insufficient)
    direct_eu = max(0, enough_text - no_eu)
    ri_substantive = max(0, direct_eu - no_ri)
    strategic = max(0, ri_substantive - no_strategy - other_aboutness)
    return {
        "raw_records_seen": raw,
        "gate_evaluated": evaluated,
        "enough_text_to_judge": enough_text,
        "direct_eu_scope_remaining": direct_eu,
        "substantive_ri_remaining": ri_substantive,
        "strategic_context_remaining": strategic,
        "gate_passed_before_cross_source_dedupe": gate_passed,
        "unique_gate_candidates": max(0, int(unique_gate_candidates)),
        "duplicates_or_known_removed_after_gate": max(0, gate_passed - int(unique_gate_candidates)),
        "genuinely_new_unique_ab": max(0, int(genuinely_new_candidates)),
        "missing_text_deferred": insufficient,
        "rejected_no_direct_eu": no_eu,
        "rejected_no_ri": no_ri,
        "rejected_no_strategic_context": no_strategy,
        "rejected_other_aboutness": other_aboutness,
        "pre_gate_filters": {
            "non_english": n("openalex_reject_non_english") + n("crossref_reject_non_english") + n("institution_reject_non_english"),
            "institution_no_date": n("institution_reject_no_date"),
            "institution_fetch_or_nonhtml": n("institution_reject_fetch_or_nonhtml"),
            "institution_before_floor": n("institution_reject_before_floor"),
        },
        "metadata_text_rescue": {
            "queued": n("openalex_metadata_rescue_queued") + n("crossref_metadata_rescue_queued"),
            "attempted": n("openalex_metadata_rescue_attempted") + n("crossref_metadata_rescue_attempted"),
            "text_recovered": n("openalex_metadata_rescue_recovered") + n("crossref_metadata_rescue_recovered"),
            "admitted_after_recovery": n("openalex_metadata_rescue_admitted") + n("crossref_metadata_rescue_admitted"),
        },
        "institution_source_adapter_jobs": n("institution_adapter_jobs"),
    }

def candidate_from_openalex(work: dict[str, Any], date_floor: dt.date | None = None, frontier_targets: Iterable[str] | None = None) -> dict[str, Any] | None:
    title = clean_text(work.get("display_name"))
    abstract = openalex_abstract(work.get("abstract_inverted_index"))
    date = parse_date(work.get("publication_date"))
    effective_floor = date_floor or DATE_FLOOR
    if not title or not date or date < effective_floor or date > dt.date.today():
        return None
    if not english_record_ok(f"{title}. {abstract}", work.get("language", ""), title=title):
        _diag_inc("openalex_reject_non_english")
        return None
    if document_exclusion_reason(title, abstract):
        return None
    quality_ok, tier, source_rank, source, tier_label = quality_from_openalex(work)
    if not quality_ok:
        return None
    ev = gate_scope(title, abstract, "", tier, source_kind="scholarly")
    _record_ab_gate_diagnostic("openalex", ev)
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
        text=full, doi=doi, preprint=is_preprint, frontier_targets=frontier_targets,
    )


def collect_openalex(
    from_date: dt.date,
    warnings: list[str],
    queries_override: list[str] | None = None,
    stage_deadline: float | None = None,
    query_dates_override: dict[str, dt.date] | None = None,
    depth_state: dict[str, Any] | None = None,
    depth_lane_overrides: dict[str, str] | None = None,
    execution_stats: dict[str, Any] | None = None,
    depth_only: bool = False,
) -> list[dict[str, Any]]:
    """Keyless OpenAlex discovery with depth rotation.

    Every selected query checks page 1 for newly published work and one persisted
    deeper page. No API key, email tag, GitHub secret, or other credential is used.
    A 429 stops this source family quickly for the run instead of spending the
    stage budget on repeated retries; Crossref and the other sources then continue.
    """
    queries = list(dict.fromkeys(queries_override if queries_override is not None else (CONFIG["queries_a"] + CONFIG["queries_b"])))
    per_page = int(CONFIG.get("openalex_per_query", 60))
    depth_max = max(1, int(CONFIG.get("openalex_depth_pages_max", 6) or 1))
    workers = max(1, min(int(CONFIG.get("openalex_public_workers", 2)), 3))
    timeout = int(CONFIG.get("scholarly_api_timeout_seconds", 12))
    min_interval = float(CONFIG.get("openalex_public_min_interval_seconds", 0.30))
    retries = max(0, int(CONFIG.get("scholarly_public_retries", 2)))
    rate_lock = threading.Lock()
    depth_lock = threading.Lock()
    last_request = [0.0]
    stop_public = threading.Event()
    depth_state = depth_state if isinstance(depth_state, dict) else {}
    executed_queries: set[str] = set()
    execution_lock = threading.Lock()
    enrichment_limit = max(0, int(CONFIG.get("openalex_missing_abstract_enrichment_per_scan", 12) or 0))
    enrichment_timeout = max(3, int(CONFIG.get("openalex_missing_abstract_enrichment_timeout_seconds", 8) or 8))
    enrichment_total = [0]
    enrichment_by_query: Counter = Counter()

    def mark_executed(q: str) -> None:
        with execution_lock:
            executed_queries.add(q)

    def wait_slot() -> None:
        with rate_lock:
            now = time.monotonic()
            wait = min_interval - (now - last_request[0])
            if wait > 0:
                time.sleep(wait)
            last_request[0] = time.monotonic()

    enrichment_lock = threading.Lock()
    enrichment_per_query = max(1, int(CONFIG.get("openalex_missing_abstract_enrichment_per_query", 3) or 3))
    metadata_min_score = int(CONFIG.get("metadata_rescue_priority_min_score", 10) or 10)

    def convert_works(works: list[dict[str, Any]], query_from: dt.date, q: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        rescue_queue: list[tuple[int, dict[str, Any], str]] = []
        for raw_work in works:
            work = raw_work
            if bool(CONFIG.get("skip_known_items_before_classification", True)):
                title0 = clean_text(work.get("title") or work.get("display_name"))
                doi0 = clean_text(work.get("doi"))
                if stable_item_identity(title0, doi0) in KNOWN_AB_IDENTITIES:
                    continue
            title0 = clean_text(work.get("title") or work.get("display_name"))
            doi0 = clean_text(work.get("doi"))
            abstract0 = openalex_abstract(work.get("abstract_inverted_index"))
            if abstract0:
                item = candidate_from_openalex(work, date_floor=min(DATE_FLOOR, query_from), frontier_targets=frontier_targets_for_query(q))
                if item:
                    out.append(item)
                continue

            # Do not let an abstract-less record consume the gate as if missing text
            # were negative evidence. Queue only plausible metadata for DOI recovery,
            # and rank that queue before spending the bounded publisher-fetch budget.
            _diag_inc("openalex_metadata_missing_text")
            if not doi0 or not title0 or document_exclusion_reason(title0, ""):
                continue
            quality_ok, tier, _rank, source, _label = quality_from_openalex(work)
            if not quality_ok:
                continue
            published = parse_date(work.get("publication_date"))
            score = scholarly_metadata_rescue_priority(title0, query=q, source=source, published=published, tier=tier)
            if not bool(CONFIG.get("metadata_rescue_priority_enabled", True)) or score >= metadata_min_score:
                rescue_queue.append((score, work, doi0))

        rescue_queue.sort(key=lambda x: x[0], reverse=True)
        _diag_inc("openalex_metadata_rescue_queued", len(rescue_queue))
        for _score, raw_work, doi0 in rescue_queue[:enrichment_per_query]:
            with enrichment_lock:
                if enrichment_total[0] >= enrichment_limit:
                    break
                enrichment_total[0] += 1
                enrichment_by_query[q] += 1
            _diag_inc("openalex_metadata_rescue_attempted")
            if execution_stats is not None:
                execution_stats["openalex_abstracts_enrichment_attempted"] = int(execution_stats.get("openalex_abstracts_enrichment_attempted", 0)) + 1
            recovered = doi_landing_abstract(doi0, enrichment_timeout)
            if not recovered:
                continue
            _diag_inc("openalex_metadata_rescue_recovered")
            work = dict(raw_work)
            tokens = clean_text(recovered).split()
            inv: dict[str, list[int]] = {}
            for pos, token in enumerate(tokens):
                inv.setdefault(token, []).append(pos)
            work["abstract_inverted_index"] = inv
            item = candidate_from_openalex(work, date_floor=min(DATE_FLOOR, query_from), frontier_targets=frontier_targets_for_query(q))
            if item:
                _diag_inc("openalex_metadata_rescue_admitted")
                item["metadata_note"] = "Abstract recovered from DOI publisher metadata after high-potential metadata prioritisation."
                out.append(item)
        return out

    def fetch_page(q: str, query_from: dt.date, page: int) -> tuple[list[dict[str, Any]], str | None, int]:
        if stop_public.is_set():
            return [], "endpoint stopped for this run", 0
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            return [], "budget", 0
        mark_executed(q)
        params = {
            "search": q,
            "filter": f"from_publication_date:{query_from.isoformat()},to_publication_date:{dt.date.today().isoformat()}",
            "sort": "publication_date:desc",
            "per_page": str(per_page),
            "page": str(page),
        }
        for attempt in range(retries + 1):
            if stop_public.is_set():
                return [], "endpoint stopped for this run", 0
            wait_slot()
            try:
                r = openalex_get("works", params=params, timeout=timeout)
                if r.status_code == 200:
                    works = r.json().get("results", [])
                    _diag_inc("openalex_raw_records", len(works))
                    return convert_works(works, query_from, q), None, len(works)
                if r.status_code == 429:
                    stop_public.set()
                    return [], "HTTP 429 (keyless OpenAlex allowance/rate limit); source stopped for this run", 0
                if r.status_code in {401, 403, 409}:
                    stop_public.set()
                    return [], f"HTTP {r.status_code} from keyless OpenAlex; source stopped for this run", 0
                if r.status_code in {500, 502, 503, 504} and attempt < retries:
                    retry_after = clean_text(r.headers.get("Retry-After"))
                    try:
                        delay = min(8.0, max(1.0, float(retry_after))) if retry_after else min(8.0, 1.5 * (attempt + 1))
                    except Exception:
                        delay = min(8.0, 1.5 * (attempt + 1))
                    time.sleep(delay)
                    continue
                return [], f"HTTP {r.status_code}", 0
            except Exception as e:
                if attempt < retries:
                    time.sleep(min(6.0, 1.5 * (attempt + 1)))
                    continue
                return [], type(e).__name__, 0
        return [], "request failed", 0

    def fetch_query(q: str) -> tuple[list[dict[str, Any]], str | None]:
        query_from = (query_dates_override or {}).get(q, from_date)
        lane = clean_text((depth_lane_overrides or {}).get(q, ""))
        depth_key = f"{lane}::{q}" if lane else q
        if depth_only:
            with depth_lock:
                page = max(2, int(depth_state.get(depth_key, 2) or 2))
                if page > depth_max:
                    page = 2
            deep, deep_err, deep_count = fetch_page(q, query_from, page)
            if deep_err:
                return deep, deep_err
            exhausted = deep_count < per_page or page >= depth_max
            with depth_lock:
                depth_state[depth_key] = 2 if exhausted else page + 1
            if exhausted and isinstance(execution_stats, dict):
                execution_stats.setdefault("openalex_depth_exhausted", set()).add(q)
            return dedupe_candidates(deep), None
        latest, err, latest_count = fetch_page(q, query_from, 1)
        if err:
            return latest, err
        if depth_max <= 1 or latest_count < per_page:
            return latest, None
        with depth_lock:
            page = max(2, int(depth_state.get(depth_key, 2) or 2))
            if page > depth_max:
                page = 2
        deep, deep_err, deep_count = fetch_page(q, query_from, page)
        if deep_err == "budget":
            return latest, deep_err
        if deep_err:
            return latest, deep_err
        with depth_lock:
            depth_state[depth_key] = 2 if deep_count < per_page or page >= depth_max else page + 1
        return dedupe_candidates(latest + deep), None

    out: list[dict[str, Any]] = []
    budget_hits = 0
    endpoint_stop_reported = False
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(fetch_query, q) for q in queries]
        for fut in cf.as_completed(futs):
            try:
                items, err = fut.result()
                out.extend(items)
                if err == "budget":
                    budget_hits += 1
                elif err and ("source stopped" in err or "endpoint stopped" in err):
                    if not endpoint_stop_reported:
                        warnings.append(f"OpenAlex {err}; continuing with Crossref and direct publisher/institution scanning")
                        endpoint_stop_reported = True
                elif err:
                    warnings.append(f"OpenAlex {err}")
            except Exception as e:
                warnings.append(f"OpenAlex worker: {type(e).__name__}")
    if budget_hits:
        warnings.append(f"OpenAlex scan budget reached; {budget_hits} queued query/queries skipped")
    if isinstance(execution_stats, dict):
        execution_stats.setdefault("openalex_queries", set()).update(executed_queries)
    return dedupe_candidates(out)


def _snowball_seed_weight(item: dict[str, Any]) -> float:
    """Quality weight for bibliography seeds; it never changes admission."""
    tier = normalized(item.get("source_tier", ""))
    typ = normalized(item.get("type", ""))
    if "tier 1" in tier:
        return 1.50
    if "tier 2" in tier and "broad" not in tier:
        return 1.25
    if "tier 2" in tier:
        return 1.10
    if "peer reviewed" in typ or "peer-reviewed" in typ:
        return 1.05
    return 0.80


def _snowball_title_similarity(a: str, b: str) -> float:
    aa = set(norm_title(a).split())
    bb = set(norm_title(b).split())
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / max(1, len(aa | bb))


def _snowball_seed_pool(previous: dict[str, Any], live_candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Choose recent high-quality Strand-A publications as citation-network seeds.

    The lane is discovery-only. A seed can guide us to other work but can never make a
    cited/citing paper pass the ordinary EU + R&I + strategic-context gates.
    """
    pinned = {norm_title(x) for x in CONFIG.get("citation_snowball_pinned_seed_titles", []) if clean_text(x)}
    raw: list[dict[str, Any]] = []
    raw.extend(x for x in previous.get("strand_a", []) if isinstance(x, dict))
    raw.extend(x for x in live_candidates if isinstance(x, dict) and x.get("strand") in {"A", "both"})
    by_key: dict[str, dict[str, Any]] = {}
    for item in raw:
        title = clean_text(item.get("title"))
        if not title:
            continue
        d = parse_date(item.get("date"))
        if d and d < DATE_FLOOR:
            continue
        tier = normalized(item.get("source_tier", ""))
        typ = normalized(item.get("type", ""))
        is_pinned = norm_title(title) in pinned
        quality_ok = (
            "tier 1" in tier
            or "tier 2" in tier
            or "peer reviewed" in typ
            or "peer-reviewed" in typ
        )
        if not (quality_ok or is_pinned):
            continue
        # Keep the lane topical: only evidence already accepted for Strand A is a seed.
        if item.get("eu_relevance") not in {"direct", "material_external"} and not is_pinned:
            continue
        key = identity(internalize_previous(item))
        old = by_key.get(key)
        if old is None or (_snowball_seed_weight(item), d or dt.date.min) > (_snowball_seed_weight(old), parse_date(old.get("date")) or dt.date.min):
            x = dict(item)
            x["_snowball_pinned"] = is_pinned
            by_key[key] = x
    vals = list(by_key.values())
    vals.sort(key=lambda x: (
        0 if x.get("_snowball_pinned") else 1,
        -_snowball_seed_weight(x),
        -(parse_date(x.get("date")) or dt.date.min).toordinal(),
    ))
    return vals[:max(1, int(CONFIG.get("citation_snowball_seed_limit", 20) or 20))]




class OpenAlexRateLimit(RuntimeError):
    """Raised when OpenAlex explicitly rate-limits a bounded scanner lane."""

def _snowball_resolve_seed(seed: dict[str, Any], timeout: int) -> dict[str, Any] | None:
    title = clean_text(seed.get("title"))
    if not title:
        return None
    doi_match = re.search(r"10\.\d{4,9}/[^\s?#]+", clean_text(seed.get("link", "")), re.I)
    params: dict[str, Any]
    if doi_match:
        doi = doi_match.group(0).rstrip(".,)")
        params = {"filter": f"doi:https://doi.org/{doi}", "per-page": 3}
    else:
        params = {"search": title, "per-page": 5}
    r = openalex_get("works", params=params, timeout=timeout)
    if r.status_code == 429:
        raise OpenAlexRateLimit("OpenAlex HTTP 429 during seed resolution")
    if r.status_code != 200:
        return None
    results = (r.json() or {}).get("results") or []
    if not results:
        return None
    exact = [w for w in results if norm_title(w.get("display_name", "")) == norm_title(title)]
    if exact:
        return exact[0]
    ranked = sorted(results, key=lambda w: _snowball_title_similarity(title, w.get("display_name", "")), reverse=True)
    if ranked and _snowball_title_similarity(title, ranked[0].get("display_name", "")) >= 0.78:
        return ranked[0]
    return None


def _snowball_fetch_works(ids: list[str], timeout: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for start in range(0, len(ids), 100):
        chunk = [x.rsplit("/", 1)[-1] for x in ids[start:start + 100] if clean_text(x)]
        if not chunk:
            continue
        r = openalex_get(
            "works",
            params={"filter": "openalex:" + "|".join(chunk), "per-page": len(chunk)},
            timeout=timeout,
        )
        if r.status_code == 429:
            raise OpenAlexRateLimit("OpenAlex HTTP 429 during snowball reference fetch")
        if r.status_code == 200:
            out.extend((r.json() or {}).get("results") or [])
    return out


def collect_citation_snowball(
    previous: dict[str, Any],
    live_candidates: Iterable[dict[str, Any]],
    warnings: list[str],
    stage_deadline: float | None,
    execution_stats: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Backward + forward snowballing from high-quality accepted Strand-A publications.

    First, count references shared across the seed papers (bibliographic coupling in reverse):
    references cited by several good radar publications become consensus anchors. Then search
    *forward* from those anchors for recent papers that cite them. A tiny pinned-seed allowance
    lets an explicitly important seed contribute a few distinctive anchors even before another
    seed co-cites them. Every discovered work is still passed through candidate_from_openalex().
    """
    stats: dict[str, Any] = {
        "enabled": bool(CONFIG.get("citation_snowball_enabled", True)),
        "seeds_planned": 0, "seeds_resolved": 0, "references_observed": 0,
        "shared_references": 0, "anchors_selected": 0, "forward_queries": 0,
        "backward_admitted": 0, "forward_admitted": 0, "admitted_unique": 0,
        "anchors": [], "status": "pending", "rate_limited": False,
    }
    if not stats["enabled"]:
        return [], stats
    if stage_deadline is not None and time.monotonic() >= stage_deadline:
        return [], stats
    seeds = _snowball_seed_pool(previous, live_candidates)
    stats["seeds_planned"] = len(seeds)
    if not seeds:
        return [], stats

    timeout = max(4, int(CONFIG.get("scholarly_api_timeout_seconds", 12) or 12))
    min_interval = max(0.0, float(CONFIG.get("openalex_public_min_interval_seconds", 0.30) or 0.30))
    min_support = max(2, int(CONFIG.get("citation_snowball_min_seed_support", 2) or 2))
    anchor_limit = max(1, int(CONFIG.get("citation_snowball_anchor_limit", 12) or 12))
    pinned_slots = max(0, int(CONFIG.get("citation_snowball_pinned_reference_slots", 3) or 0))
    pool_limit = max(anchor_limit, int(CONFIG.get("citation_snowball_reference_pool_limit", 100) or 100))
    forward_rows = max(5, min(50, int(CONFIG.get("citation_snowball_forward_rows", 25) or 25)))

    ref_count: Counter = Counter()
    ref_weight: Counter = Counter()
    ref_seeds: dict[str, list[str]] = {}
    ref_pinned: set[str] = set()
    resolved_seed_titles: list[str] = []
    last_request = 0.0

    def wait_slot() -> bool:
        nonlocal last_request
        if stage_deadline is not None and time.monotonic() >= stage_deadline:
            return False
        wait = min_interval - (time.monotonic() - last_request)
        if wait > 0:
            time.sleep(wait)
        last_request = time.monotonic()
        return stage_deadline is None or time.monotonic() < stage_deadline

    try:
        for seed in seeds:
            if not wait_slot():
                break
            try:
                work = _snowball_resolve_seed(seed, timeout)
            except OpenAlexRateLimit:
                stats["status"] = "blocked_openalex_429"
                stats["rate_limited"] = True
                warnings.append("Citation snowball seed resolution OpenAlex HTTP 429; snowball lane stopped for this scan")
                break
            except requests.RequestException:
                continue
            if not work:
                continue
            refs = list(dict.fromkeys(clean_text(x) for x in (work.get("referenced_works") or []) if clean_text(x)))
            if not refs:
                continue
            stats["seeds_resolved"] += 1
            seed_title = clean_text(seed.get("title"))
            resolved_seed_titles.append(seed_title)
            weight = _snowball_seed_weight(seed)
            for rid in refs:
                ref_count[rid] += 1
                ref_weight[rid] += weight
                ref_seeds.setdefault(rid, []).append(seed_title)
                if seed.get("_snowball_pinned"):
                    ref_pinned.add(rid)
    except Exception as e:
        warnings.append(f"Citation snowball seed resolution: {type(e).__name__}")

    stats["resolved_seed_titles"] = resolved_seed_titles[:20]
    stats["references_observed"] = len(ref_count)
    shared = [rid for rid, n in ref_count.items() if n >= min_support]
    stats["shared_references"] = len(shared)
    pool = sorted(
        set(shared) | ref_pinned,
        key=lambda rid: (-ref_count[rid], -ref_weight[rid], 0 if rid in ref_pinned else 1, rid),
    )[:pool_limit]
    if not pool:
        if stats.get("status") == "pending":
            stats["status"] = "no_anchor_pool" if stats.get("seeds_resolved") else "no_seeds_resolved"
        return [], stats

    if not wait_slot():
        return [], stats
    try:
        metadata = _snowball_fetch_works(pool, timeout)
    except OpenAlexRateLimit:
        stats["status"] = "blocked_openalex_429"
        stats["rate_limited"] = True
        warnings.append("Citation snowball reference fetch OpenAlex HTTP 429; snowball lane stopped for this scan")
        return [], stats
    except requests.RequestException:
        metadata = []
    by_id = {clean_text(w.get("id")): w for w in metadata if clean_text(w.get("id"))}
    ranked = sorted(
        [rid for rid in pool if rid in by_id],
        key=lambda rid: (
            -ref_count[rid],
            -ref_weight[rid],
            -int(by_id[rid].get("cited_by_count") or 0),
            -(parse_date(by_id[rid].get("publication_date")) or dt.date.min).toordinal(),
        ),
    )

    anchors: list[str] = []
    pinned_used = 0
    for rid in ranked:
        if ref_count[rid] >= min_support:
            anchors.append(rid)
        elif rid in ref_pinned and pinned_used < pinned_slots:
            anchors.append(rid)
            pinned_used += 1
        if len(anchors) >= anchor_limit:
            break
    stats["anchors_selected"] = len(anchors)

    out: list[dict[str, Any]] = []
    for rid in anchors:
        work = by_id.get(rid) or {}
        anchor_title = clean_text(work.get("display_name")) or rid.rsplit("/", 1)[-1]
        seed_titles = list(dict.fromkeys(ref_seeds.get(rid, [])))[:8]
        anchor_info = {
            "openalex_id": rid,
            "title": anchor_title,
            "seed_support": int(ref_count[rid]),
            "weighted_support": round(float(ref_weight[rid]), 2),
            "cited_by_count": int(work.get("cited_by_count") or 0),
            "pinned_seed_reference": bool(rid in ref_pinned),
            "seed_titles": seed_titles,
        }
        stats["anchors"].append(anchor_info)

        # Backward candidate: only current-window references can enter the radar itself.
        backward = candidate_from_openalex(work, date_floor=DATE_FLOOR)
        if backward:
            backward["discovery_provenance"] = "citation_snowball"
            backward["provenance"] = list(dict.fromkeys(list(backward.get("provenance") or []) + ["citation_snowball_backward"]))
            backward["citation_snowball"] = {**anchor_info, "direction": "backward_shared_reference"}
            out.append(backward)
            stats["backward_admitted"] += 1

        if not wait_slot():
            break
        oid = rid.rsplit("/", 1)[-1]
        params = {
            "filter": f"cites:{oid},from_publication_date:{DATE_FLOOR.isoformat()},to_publication_date:{dt.date.today().isoformat()}",
            "sort": "publication_date:desc",
            "per-page": forward_rows,
        }
        try:
            r = openalex_get("works", params=params, timeout=timeout)
        except requests.RequestException:
            continue
        if r.status_code == 429:
            stats["status"] = "blocked_openalex_429"
            stats["rate_limited"] = True
            warnings.append("Citation snowball OpenAlex HTTP 429; snowball lane stopped for this scan")
            break
        if r.status_code != 200:
            continue
        stats["forward_queries"] += 1
        for citing in (r.json() or {}).get("results") or []:
            cand = candidate_from_openalex(citing, date_floor=DATE_FLOOR)
            if not cand:
                continue
            cand["discovery_provenance"] = "citation_snowball"
            cand["provenance"] = list(dict.fromkeys(list(cand.get("provenance") or []) + ["citation_snowball_forward"]))
            cand["citation_snowball"] = {**anchor_info, "direction": "forward_from_shared_reference"}
            out.append(cand)
            stats["forward_admitted"] += 1

    unique = dedupe_candidates(out)
    stats["admitted_unique"] = len(unique)
    if stats.get("status") == "pending":
        stats["status"] = "completed"
    if isinstance(execution_stats, dict):
        execution_stats["citation_snowball_seeds_resolved"] = stats["seeds_resolved"]
        execution_stats["citation_snowball_anchors"] = stats["anchors_selected"]
        execution_stats["citation_snowball_forward_queries"] = stats["forward_queries"]
        execution_stats["citation_snowball_admitted"] = stats["admitted_unique"]
    return unique, stats

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
    trusted_publishers = [normalized(x) for x in CONFIG.get("trusted_broad_journal_publishers", []) if clean_text(x)]
    if (
        CONFIG.get("accept_trusted_publisher_peer_reviewed_journals", True)
        and journal and typ in {"journal-article", "article", "review"}
        and publisher and any(p in normalized(publisher) for p in trusted_publishers)
    ):
        return True, 2, 2.75, journal, "Tier 2 trusted-publisher journal", "peer-reviewed article"
    if CONFIG.get("accept_broad_peer_reviewed_journals", False) and journal and typ in {"journal-article", "article", "review"}:
        return True, 2, 2.9, journal, "Tier 2 broad journal", "peer-reviewed article"
    if typ in {"report", "report-component", "book", "book-chapter", "posted-content"}:
        for p in CONFIG.get("crossref_institution_publishers", []):
            if normalized(p) in normalized(publisher + " " + journal):
                tier_guess = 3 if any(x in normalized(p) for x in ["rand", "brookings", "carnegie", "strategic and international"]) else 1
                return True, tier_guess, float(tier_guess), publisher or journal, f"Tier {tier_guess}", "institutional report"
    return False, 9, 9.0, journal or publisher or "Unknown source", "", typ or "publication"


def doi_landing_abstract(doi_raw: str, timeout: int = 8) -> str:
    """Best-effort abstract/description recovery from a DOI landing page.

    Crossref search records often omit abstracts even when the publisher landing page
    exposes one in citation/DC/OG metadata. This is deliberately bounded and only used
    for a small number of otherwise promising records before admission gating.
    """
    doi_raw = clean_text(doi_raw).removeprefix("https://doi.org/").removeprefix("http://doi.org/").removeprefix("doi:")
    if not doi_raw or deadline_reached(int(CONFIG.get("network_reserve_seconds", 90))):
        return ""
    try:
        r = SESSION.get(
            f"https://doi.org/{doi_raw}",
            timeout=timeout,
            headers={"Accept": "text/html,application/xhtml+xml"},
            allow_redirects=True,
        )
        if r.status_code != 200 or "html" not in normalized(r.headers.get("content-type", "text/html")):
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        text = meta_content(soup, [
            "citation_abstract", "dc.description", "DC.Description", "description",
            "og:description", "twitter:description", "abstract",
        ])
        if len(text.split()) >= 20:
            return text[:12000]
        for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
            try:
                data = json.loads(script.string or script.get_text())
            except Exception:
                continue
            for obj in jsonld_objects(data):
                desc = clean_text(obj.get("abstract") or obj.get("description")) if isinstance(obj, dict) else ""
                if len(desc.split()) >= 20:
                    return desc[:12000]
    except Exception:
        return ""
    return ""


def candidate_from_crossref(item: dict[str, Any], date_floor: dt.date | None = None, frontier_targets: Iterable[str] | None = None) -> dict[str, Any] | None:
    title = clean_text((item.get("title") or [""])[0])
    abstract = clean_text(item.get("abstract"))
    date = crossref_date(item)
    effective_floor = date_floor or DATE_FLOOR
    if not title or not date or date < effective_floor or date > dt.date.today():
        return None
    if not english_record_ok(f"{title}. {abstract}", item.get("language", ""), title=title):
        _diag_inc("crossref_reject_non_english")
        return None
    if document_exclusion_reason(title, abstract):
        return None
    ok, tier, source_rank, source, tier_label, item_type = quality_from_crossref(item)
    if not ok:
        return None
    ev = gate_scope(title, abstract, "", tier, source_kind="scholarly")
    _record_ab_gate_diagnostic("crossref", ev)
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
        doi=doi, preprint=preprint, frontier_targets=frontier_targets,
    )




def load_curator_candidate_tests() -> dict[str, Any]:
    """Load bounded curator-supplied publication candidates for source-level testing.

    The file is an input queue, not evidence. Titles, notes and Matrix row hints can
    focus exact resolution, but the ordinary source-derived admission gate remains
    authoritative and the browser classifier remains authoritative for Matrix cells.
    """
    try:
        raw = json.loads(CURATOR_CANDIDATE_TESTS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    if not isinstance(raw, dict) or not isinstance(raw.get("candidates"), list):
        return {}
    return raw


def _curator_candidate_known(entry: dict[str, Any]) -> bool:
    title = clean_text(entry.get("title"))
    doi = clean_text(entry.get("doi"))
    url = clean_text(entry.get("url")) or (f"https://doi.org/{doi}" if doi else "")
    if stable_item_identity(title, url) in KNOWN_AB_IDENTITIES:
        return True
    nurl = normalized_link(url)
    return bool(nurl and nurl in KNOWN_AB_LINKS)


def _curator_crossref_lookup(entry: dict[str, Any], timeout: int) -> tuple[dict[str, Any] | None, str]:
    doi = clean_text(entry.get("doi")).removeprefix("https://doi.org/").removeprefix("doi:")
    title = clean_text(entry.get("title"))
    try:
        if doi:
            r = SESSION.get(f"https://api.crossref.org/works/{quote(doi, safe='')}", timeout=timeout)
            if r.status_code == 429:
                return None, "crossref_rate_limited"
            if r.status_code != 200:
                return None, f"crossref_http_{r.status_code}"
            msg = (r.json() or {}).get("message") or {}
            return (msg if isinstance(msg, dict) else None), "crossref_doi"
        if not title:
            return None, "missing_title"
        r = SESSION.get(
            "https://api.crossref.org/works",
            params={
                "query.bibliographic": title,
                "rows": 6,
                "select": "DOI,title,author,publisher,container-title,published-online,published-print,published,issued,type,URL,abstract,score",
            },
            timeout=timeout,
        )
        if r.status_code == 429:
            return None, "crossref_rate_limited"
        if r.status_code != 200:
            return None, f"crossref_http_{r.status_code}"
        items = ((r.json() or {}).get("message") or {}).get("items") or []
        ranked = sorted(
            [x for x in items if isinstance(x, dict)],
            key=lambda x: _snowball_title_similarity(title, clean_text((x.get("title") or [""])[0])),
            reverse=True,
        )
        if not ranked:
            return None, "crossref_title_no_match"
        best = ranked[0]
        sim = _snowball_title_similarity(title, clean_text((best.get("title") or [""])[0]))
        if sim < 0.82:
            return None, "crossref_title_no_exact_match"
        return best, "crossref_title"
    except requests.RequestException:
        return None, "crossref_transport_error"


def _curator_crossref_gate_status(raw: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    title = clean_text((raw.get("title") or [""])[0])
    abstract = clean_text(raw.get("abstract"))
    date = crossref_date(raw)
    detail: dict[str, Any] = {"resolved_title": title, "resolved_date": date.isoformat() if date else ""}
    if not title or not date:
        return "deferred_incomplete_metadata", detail
    if date < EXTENDED_DATE_FLOOR or date > dt.date.today():
        return "outside_retention_window", detail
    if not english_record_ok(f"{title}. {abstract}", raw.get("language", ""), title=title):
        return "rejected_language", detail
    doc_reason = document_exclusion_reason(title, abstract)
    if doc_reason:
        detail["document_exclusion_reason"] = doc_reason
        return "rejected_document_type", detail
    ok, tier, _rank, source, _tier_label, _item_type = quality_from_crossref(raw)
    detail["resolved_source"] = source
    detail["source_tier_numeric"] = tier
    if not ok:
        return "rejected_source_quality", detail
    ev = gate_scope(title, abstract, "", tier, source_kind="scholarly")
    detail["gate"] = {
        "a_pass": bool(ev.get("a_pass")), "b_pass": bool(ev.get("b_pass")),
        "eu_relevance": ev.get("eu_relevance"), "aboutness_reason": ev.get("aboutness_reason"),
        "a_route": ev.get("a_route", ""),
    }
    if ev.get("a_pass") or ev.get("b_pass"):
        return "passed_gate", detail
    if clean_text(ev.get("aboutness_reason")) == "insufficient_text" or not abstract:
        return "deferred_insufficient_text", detail
    return "rejected_gate", detail


def _curator_openalex_gate_status(raw: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    title = clean_text(raw.get("display_name"))
    abstract = openalex_abstract(raw.get("abstract_inverted_index"))
    date = parse_date(raw.get("publication_date"))
    detail: dict[str, Any] = {"resolved_title": title, "resolved_date": date.isoformat() if date else ""}
    if not title or not date:
        return "deferred_incomplete_metadata", detail
    if date < EXTENDED_DATE_FLOOR or date > dt.date.today():
        return "outside_retention_window", detail
    if not english_record_ok(f"{title}. {abstract}", raw.get("language", ""), title=title):
        return "rejected_language", detail
    doc_reason = document_exclusion_reason(title, abstract)
    if doc_reason:
        detail["document_exclusion_reason"] = doc_reason
        return "rejected_document_type", detail
    ok, tier, _rank, source, _tier_label = quality_from_openalex(raw)
    detail["resolved_source"] = source
    detail["source_tier_numeric"] = tier
    if not ok:
        return "rejected_source_quality", detail
    ev = gate_scope(title, abstract, "", tier, source_kind="scholarly")
    detail["gate"] = {
        "a_pass": bool(ev.get("a_pass")), "b_pass": bool(ev.get("b_pass")),
        "eu_relevance": ev.get("eu_relevance"), "aboutness_reason": ev.get("aboutness_reason"),
        "a_route": ev.get("a_route", ""),
    }
    if ev.get("a_pass") or ev.get("b_pass"):
        return "passed_gate", detail
    if clean_text(ev.get("aboutness_reason")) == "insufficient_text" or not abstract:
        return "deferred_insufficient_text", detail
    return "rejected_gate", detail


def _tag_curator_candidate(item: dict[str, Any], entry: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    meta = {
        "profile_version": clean_text(batch.get("profile_version")),
        "batch_id": clean_text(batch.get("batch_id")),
        "candidate_id": clean_text(entry.get("candidate_id")),
        "group_id": clean_text(entry.get("group_id")),
        "role_in_group": clean_text(entry.get("role_in_group")),
        "frontier_row_hint": clean_text(entry.get("frontier_row_hint")),
        "secondary_frontier_row_hints": [clean_text(x) for x in (entry.get("secondary_frontier_row_hints") or []) if clean_text(x)],
    }
    out["curator_candidate_test"] = meta
    out["provenance"] = list(dict.fromkeys(list(out.get("provenance") or []) + ["curator_candidate_test"]))
    out["discovery_provenance"] = "curator_candidate_test"
    return out


def collect_curator_candidate_tests(
    previous: dict[str, Any],
    warnings: list[str],
    stage_deadline: float | None,
    execution_stats: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Resolve and test curator candidates without granting them evidential privilege.

    Exact DOI is preferred; title-only companion works fall back to exact-title Crossref
    and then OpenAlex resolution. A candidate is admitted only if the normal source-derived
    A/B gate passes. Matrix hints are carried only as audit metadata and never populate
    ``matrix_dimension``/``quadrant_implied``.
    """
    batch = load_curator_candidate_tests()
    prior = previous.get("curator_candidate_testing") if isinstance(previous.get("curator_candidate_testing"), dict) else {}
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    state: dict[str, Any] = {
        "profile_version": clean_text(batch.get("profile_version")),
        "batch_id": clean_text(batch.get("batch_id")),
        "source_document": clean_text(batch.get("source_document")),
        "last_tested_at": now_iso,
        "results": [],
    }
    candidates = [dict(x) for x in (batch.get("candidates") or []) if isinstance(x, dict)]
    state["candidates_total"] = len(candidates)
    if not candidates or not bool(CONFIG.get("curator_candidate_testing_enabled", True)):
        state["status"] = "disabled_or_empty"
        return [], state

    previous_results = {
        clean_text(x.get("candidate_id")): dict(x)
        for x in (prior.get("results") or []) if isinstance(x, dict) and clean_text(x.get("candidate_id"))
    }
    final_statuses = {
        "rejected_gate", "rejected_language", "rejected_document_type", "rejected_source_quality",
        "outside_retention_window", "passed_gate_outside_core_not_highest",
    }
    retest_rejected = bool(CONFIG.get("curator_candidate_retest_rejected", False))
    limit = max(1, int(CONFIG.get("curator_candidate_tests_per_scan", 30) or 30))
    timeout = max(4, int(CONFIG.get("scholarly_api_timeout_seconds", 12) or 12))
    enrichment_timeout = max(3, int(CONFIG.get("curator_candidate_enrichment_timeout_seconds", 8) or 8))
    attempted = 0
    admitted: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    for entry in candidates:
        cid = clean_text(entry.get("candidate_id"))
        title = clean_text(entry.get("title"))
        base = {
            "candidate_id": cid, "group_id": clean_text(entry.get("group_id")),
            "role_in_group": clean_text(entry.get("role_in_group")), "title": title,
            "frontier_row_hint": clean_text(entry.get("frontier_row_hint")),
        }
        if _curator_candidate_known(entry):
            results.append({**base, "status": "already_in_corpus", "attempted_this_scan": False})
            continue
        old = previous_results.get(cid, {})
        if old.get("status") in final_statuses and not retest_rejected:
            kept = dict(old)
            kept.update(base)
            kept["attempted_this_scan"] = False
            results.append(kept)
            continue
        if attempted >= limit or stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            kept = dict(old) if old else base
            kept.update(base)
            kept["status"] = clean_text(kept.get("status")) or "pending"
            kept["attempted_this_scan"] = False
            results.append(kept)
            continue

        attempted += 1
        result = {**base, "attempted_this_scan": True, "attempted_at": now_iso}
        raw_cr, resolution = _curator_crossref_lookup(entry, timeout)
        result["resolution"] = resolution
        candidate: dict[str, Any] | None = None
        status = "unresolved"
        detail: dict[str, Any] = {}

        if raw_cr:
            doi0 = clean_text(raw_cr.get("DOI"))
            if not clean_text(raw_cr.get("abstract")) and doi0:
                recovered = doi_landing_abstract(doi0, enrichment_timeout)
                if recovered:
                    raw_cr = dict(raw_cr)
                    raw_cr["abstract"] = recovered
                    result["abstract_recovered_from_doi"] = True
            candidate = candidate_from_crossref(raw_cr, date_floor=EXTENDED_DATE_FLOOR)
            status, detail = _curator_crossref_gate_status(raw_cr)

        # OpenAlex is a fallback for unresolved records and records whose bibliographic
        # metadata lacks enough text to make a substantive decision. It is not a second
        # chance after a genuine gate rejection.
        if candidate is None and (raw_cr is None or status in {"deferred_insufficient_text", "deferred_incomplete_metadata"}):
            try:
                seed = {"title": title, "link": clean_text(entry.get("url")) or (f"https://doi.org/{clean_text(entry.get('doi'))}" if clean_text(entry.get('doi')) else "")}
                raw_oa = _snowball_resolve_seed(seed, timeout)
            except OpenAlexRateLimit:
                raw_oa = None
                result["openalex_status"] = "rate_limited"
            except requests.RequestException:
                raw_oa = None
                result["openalex_status"] = "transport_error"
            if raw_oa:
                doi0 = clean_text(raw_oa.get("doi"))
                if doi0 and not openalex_abstract(raw_oa.get("abstract_inverted_index")):
                    recovered = doi_landing_abstract(doi0, enrichment_timeout)
                    if recovered:
                        patched = dict(raw_oa)
                        inv: dict[str, list[int]] = {}
                        for pos, token in enumerate(clean_text(recovered).split()):
                            inv.setdefault(token, []).append(pos)
                        patched["abstract_inverted_index"] = inv
                        raw_oa = patched
                        result["abstract_recovered_from_doi"] = True
                oa_candidate = candidate_from_openalex(raw_oa, date_floor=EXTENDED_DATE_FLOOR)
                oa_status, oa_detail = _curator_openalex_gate_status(raw_oa)
                result["openalex_status"] = "resolved"
                if oa_candidate is not None:
                    candidate = oa_candidate
                    status, detail = oa_status, oa_detail
                    result["resolution"] = "openalex_exact_fallback"
                elif status in {"unresolved", "deferred_insufficient_text", "deferred_incomplete_metadata"}:
                    status, detail = oa_status, oa_detail
                    result["resolution"] = "openalex_exact_fallback"

        result.update(detail)
        if candidate is not None:
            candidate = _tag_curator_candidate(candidate, entry, batch)
            d = parse_date(candidate.get("date"))
            retention_ok = bool(not d or d >= DATE_FLOOR or (d >= EXTENDED_DATE_FLOOR and highest_source_merit(candidate)))
            result["strand"] = clean_text(candidate.get("strand"))
            result["resolved_link"] = clean_text(candidate.get("link"))
            result["retention_eligible"] = retention_ok
            if retention_ok:
                admitted.append(candidate)
                result["status"] = "admitted_candidate"
            else:
                result["status"] = "passed_gate_outside_core_not_highest"
        else:
            result["status"] = status
        results.append(result)

    state["results"] = results
    state["attempted_this_scan"] = attempted
    state["admitted_candidates_this_scan"] = len(admitted)
    state["already_in_corpus"] = sum(1 for x in results if x.get("status") == "already_in_corpus")
    state["passed_or_existing"] = sum(1 for x in results if x.get("status") in {"already_in_corpus", "admitted_candidate"})
    state["deferred"] = sum(1 for x in results if clean_text(x.get("status")).startswith("deferred") or x.get("status") in {"unresolved", "pending"})
    state["rejected"] = sum(1 for x in results if clean_text(x.get("status")).startswith("rejected") or x.get("status") in {"outside_retention_window", "passed_gate_outside_core_not_highest"})
    state["status"] = "completed_slice" if attempted else "no_attempts"
    if isinstance(execution_stats, dict):
        execution_stats["curator_candidate_tests_attempted"] = attempted
        execution_stats["curator_candidate_tests_admitted"] = len(admitted)
    return dedupe_candidates(admitted), state


def apply_curator_matrix_placements(
    state: dict[str, Any],
    placements: list[dict[str, Any]],
    published: dict[str, Any],
) -> dict[str, Any]:
    """Attach actual browser-Matrix placement to curator test results after publication merge."""
    if not isinstance(state, dict):
        return {}
    by_title = {norm_title(x.get("title")): x for x in placements if isinstance(x, dict) and clean_text(x.get("title"))}
    by_link = {normalized_link(x.get("link")): x for x in placements if isinstance(x, dict) and normalized_link(x.get("link"))}
    corpus_items = [x for key in ("strand_a", "strand_b", "frontier_evidence") for x in (published.get(key) or []) if isinstance(x, dict)]
    corpus_by_title = {norm_title(x.get("title")): x for x in corpus_items if clean_text(x.get("title"))}
    results = []
    for raw in state.get("results") or []:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        title_key = norm_title(row.get("resolved_title") or row.get("title"))
        link_key = normalized_link(row.get("resolved_link"))
        place = by_link.get(link_key) if link_key else None
        if place is None:
            place = by_title.get(title_key)
        corpus_hit = corpus_by_title.get(title_key)
        if corpus_hit:
            row["published_strand"] = clean_text(corpus_hit.get("strand")) or ("A" if corpus_hit in (published.get("strand_a") or []) else "B")
        if place:
            row["matrix_cell"] = clean_text(place.get("cell"))
            row["matrix_row"] = clean_text(place.get("row"))
            row["matrix_column"] = clean_text(place.get("column"))
            row["matrix_placed"] = True
        else:
            row.pop("matrix_cell", None); row.pop("matrix_row", None); row.pop("matrix_column", None)
            row["matrix_placed"] = False
        results.append(row)
    state = dict(state)
    state["results"] = results
    state["matrix_placed"] = sum(1 for x in results if x.get("matrix_placed"))
    state["published_in_ab"] = sum(1 for x in results if x.get("published_strand") in {"A", "B", "both"})
    return state

def collect_crossref(
    from_date: dt.date,
    warnings: list[str],
    queries_override: list[str] | None = None,
    priority_tasks_override: list[tuple[str, str]] | None = None,
    source_sweep_journals_override: list[str] | None = None,
    stage_deadline: float | None = None,
    query_dates_override: dict[str, dt.date] | None = None,
    broad_depth_state: dict[str, Any] | None = None,
    priority_depth_state: dict[str, Any] | None = None,
    depth_lane_overrides: dict[str, str] | None = None,
    execution_stats: dict[str, Any] | None = None,
    depth_only: bool = False,
) -> list[dict[str, Any]]:
    """Crossref discovery using bounded relevance + recency + rotating depth lanes.

    Publication dates are bounded on both sides, so malformed future-dated records
    cannot monopolise a newest-first page. For every query we ask Crossref first for
    its relevance-ranked results, then for the newest bounded results, and finally
    rotate one deeper relevance page when the result set is full.
    """
    queries = list(dict.fromkeys(queries_override if queries_override is not None else (CONFIG["queries_a"] + CONFIG["queries_b"])))
    rows = int(CONFIG.get("crossref_rows_per_query", 50))
    priority_rows = int(CONFIG.get("crossref_priority_journal_rows", 35))
    depth_max = max(1, int(CONFIG.get("crossref_depth_pages_max", 6) or 1))
    priority_depth_max = max(1, int(CONFIG.get("crossref_priority_depth_pages_max", 4) or 1))
    priority_journals = list(dict.fromkeys(CONFIG.get("crossref_priority_journals", [])))
    priority_queries = list(dict.fromkeys(CONFIG.get("crossref_priority_journal_queries", [])))
    priority_tasks = priority_tasks_override if priority_tasks_override is not None else [(j, q) for j in priority_journals for q in priority_queries]
    source_sweep_journals = list(dict.fromkeys(source_sweep_journals_override or []))
    min_interval = float(CONFIG.get("crossref_public_min_interval_seconds", 0.80))
    timeout = int(CONFIG.get("scholarly_api_timeout_seconds", 12))
    retries = max(0, int(CONFIG.get("scholarly_public_retries", 2)))
    rate_lock = threading.Lock()
    last_request = [0.0]
    broad_depth_state = broad_depth_state if isinstance(broad_depth_state, dict) else {}
    priority_depth_state = priority_depth_state if isinstance(priority_depth_state, dict) else {}
    executed_broad_queries: set[str] = set()
    executed_priority_tasks: set[tuple[str, str]] = set()
    executed_source_journals: set[str] = set()
    execution_lock = threading.Lock()
    enrichment_limit = max(0, int(CONFIG.get("crossref_missing_abstract_enrichment_per_scan", 18) or 0))
    enrichment_timeout = max(3, int(CONFIG.get("crossref_missing_abstract_enrichment_timeout_seconds", 8) or 8))
    enrichment_total = [0]
    enrichment_by_task: Counter = Counter()

    def mark_executed(q: str, journal: str) -> None:
        with execution_lock:
            if journal:
                executed_priority_tasks.add((journal, q))
            else:
                executed_broad_queries.add(q)

    def wait_for_slot() -> None:
        with rate_lock:
            now = time.monotonic()
            wait = min_interval - (now - last_request[0])
            if wait > 0:
                time.sleep(wait)
            last_request[0] = time.monotonic()

    enrichment_lock = threading.Lock()
    enrichment_per_task = max(1, int(CONFIG.get("crossref_missing_abstract_enrichment_per_task", 3) or 3))
    metadata_min_score = int(CONFIG.get("metadata_rescue_priority_min_score", 10) or 10)

    def convert_items(works: list[dict[str, Any]], query_from: dt.date, q: str = "", journal: str = "") -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        task_key = f"{journal} || {q}" if journal else q
        rescue_queue: list[tuple[int, dict[str, Any], str]] = []
        for raw_item in works:
            item = raw_item
            titles0 = item.get("title") or []
            title0 = clean_text(titles0[0] if isinstance(titles0, list) and titles0 else titles0)
            doi0 = clean_text(item.get("DOI"))
            if bool(CONFIG.get("skip_known_items_before_classification", True)) and stable_item_identity(title0, doi0) in KNOWN_AB_IDENTITIES:
                continue
            abstract0 = clean_text(item.get("abstract"))
            if abstract0:
                c = candidate_from_crossref(item, date_floor=min(DATE_FLOOR, query_from), frontier_targets=frontier_targets_for_query(q))
                if c:
                    out.append(c)
                continue

            _diag_inc("crossref_metadata_missing_text")
            if not doi0 or not title0 or document_exclusion_reason(title0, ""):
                continue
            ok0, tier, _rank, source, _tier_label, _kind = quality_from_crossref(item)
            if not ok0:
                continue
            published = crossref_date(item)
            score = scholarly_metadata_rescue_priority(
                title0, query=q, source=source, publisher=clean_text(item.get("publisher")), published=published, tier=tier
            )
            if not bool(CONFIG.get("metadata_rescue_priority_enabled", True)) or score >= metadata_min_score:
                rescue_queue.append((score, item, doi0))

        rescue_queue.sort(key=lambda x: x[0], reverse=True)
        _diag_inc("crossref_metadata_rescue_queued", len(rescue_queue))
        for _score, raw_item, doi0 in rescue_queue[:enrichment_per_task]:
            with enrichment_lock:
                if enrichment_total[0] >= enrichment_limit or enrichment_by_task[task_key] >= enrichment_per_task:
                    break
                enrichment_total[0] += 1
                enrichment_by_task[task_key] += 1
            _diag_inc("crossref_metadata_rescue_attempted")
            recovered = doi_landing_abstract(doi0, enrichment_timeout)
            if not recovered:
                continue
            _diag_inc("crossref_metadata_rescue_recovered")
            item = dict(raw_item)
            item["abstract"] = recovered
            c = candidate_from_crossref(item, date_floor=min(DATE_FLOOR, query_from), frontier_targets=frontier_targets_for_query(q))
            if c:
                _diag_inc("crossref_metadata_rescue_admitted")
                c["metadata_note"] = "Abstract recovered from DOI publisher metadata after high-potential metadata prioritisation."
                out.append(c)
        return out

    def fetch_page(q: str, journal: str, offset: int, lane: str) -> tuple[list[dict[str, Any]], str | None, int]:
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            return [], "budget", 0
        mark_executed(q, journal)
        query_from = (query_dates_override or {}).get(q, from_date) if not journal else from_date
        page_rows = priority_rows if journal else rows
        params = {
            "filter": f"from-pub-date:{query_from.isoformat()},until-pub-date:{dt.date.today().isoformat()}",
            "rows": page_rows,
            "offset": max(0, int(offset)),
            "select": "DOI,title,author,publisher,container-title,published-online,published-print,published,issued,type,URL,abstract,score",
        }
        # Relevance pages are deliberately title-focused for broad discovery. Crossref's
        # bibliographic search is extremely fuzzy and previously returned thousands of
        # global records that could never pass direct-EU scope. The newest lane remains
        # bibliographic, preserving recall for records whose strategic context is mainly
        # in the abstract. Priority-journal tasks also keep bibliographic search.
        relevance_mode = clean_text(CONFIG.get("crossref_relevance_query_mode", "title")).lower()
        if lane == "relevance" and not journal and relevance_mode == "title":
            params["query.title"] = q
        else:
            params["query.bibliographic"] = q
        # Crossref query results are relevance ranked by default. Keep that as the
        # primary discovery lane. A separate bounded chronological lane catches
        # genuinely new records without letting future-dated metadata take over.
        if lane == "newest":
            params["sort"] = "published"
            params["order"] = "desc"
        if journal:
            params["query.container-title"] = journal
        for attempt in range(retries + 1):
            wait_for_slot()
            try:
                r = SESSION.get("https://api.crossref.org/works", params=params, timeout=timeout)
                if r.status_code == 200:
                    works = r.json().get("message", {}).get("items", [])
                    _diag_inc("crossref_raw_records", len(works))
                    return convert_items(works, query_from, q, journal), None, len(works)
                if r.status_code == 429:
                    if attempt < retries:
                        retry_after = clean_text(r.headers.get("Retry-After"))
                        try:
                            base = float(CONFIG.get("public_429_cooldown_seconds", 8) or 8)
                            cap = float(CONFIG.get("public_429_max_cooldown_seconds", 30) or 30)
                            delay = min(cap, max(base * (attempt + 1), float(retry_after))) if retry_after else min(cap, base * (attempt + 1))
                        except Exception:
                            delay = min(30.0, 8.0 * (attempt + 1))
                        time.sleep(delay)
                        continue
                    return [], "HTTP 429 rate limited after cooldown retries", 0
                if r.status_code in {500, 502, 503, 504} and attempt < retries:
                    retry_after = clean_text(r.headers.get("Retry-After"))
                    try:
                        delay = min(8.0, max(1.0, float(retry_after))) if retry_after else min(8.0, 1.5 * (attempt + 1))
                    except Exception:
                        delay = min(8.0, 1.5 * (attempt + 1))
                    time.sleep(delay)
                    continue
                return [], f"HTTP {r.status_code}", 0
            except Exception as e:
                if attempt < retries:
                    time.sleep(min(6.0, 1.5 * (attempt + 1)))
                    continue
                return [], type(e).__name__, 0
        return [], "request failed", 0

    def fetch_query(q: str, journal: str = "") -> tuple[list[dict[str, Any]], str | None]:
        page_rows = priority_rows if journal else rows
        state_map = priority_depth_state if journal else broad_depth_state
        max_pages = priority_depth_max if journal else depth_max
        lane = clean_text((depth_lane_overrides or {}).get(q, "")) if not journal else ""
        broad_key = f"{lane}::{q}" if lane else q
        key = f"{journal} || {q}" if journal else broad_key

        if depth_only and not journal:
            page = max(2, int(state_map.get(key, 2) or 2))
            if page > max_pages:
                page = 2
            deep, deep_err, deep_count = fetch_page(q, journal, (page - 1) * page_rows, "relevance")
            if deep_err:
                return deep, deep_err
            exhausted = deep_count < page_rows or page >= max_pages
            state_map[key] = 2 if exhausted else page + 1
            if exhausted and isinstance(execution_stats, dict):
                execution_stats.setdefault("crossref_depth_exhausted", set()).add(q)
            return dedupe_candidates(deep), None

        relevant, err, relevant_count = fetch_page(q, journal, 0, "relevance")
        if err:
            return relevant, err
        newest, newest_err, _ = fetch_page(q, journal, 0, "newest")
        if newest_err == "budget":
            return dedupe_candidates(relevant), newest_err
        if newest_err:
            return dedupe_candidates(relevant), newest_err

        combined = relevant + newest
        if max_pages <= 1 or relevant_count < page_rows:
            return dedupe_candidates(combined), None

        page = max(2, int(state_map.get(key, 2) or 2))
        if page > max_pages:
            page = 2
        deep, deep_err, deep_count = fetch_page(q, journal, (page - 1) * page_rows, "relevance")
        if deep_err:
            return dedupe_candidates(combined), deep_err
        state_map[key] = 2 if deep_count < page_rows or page >= max_pages else page + 1
        return dedupe_candidates(combined + deep), None

    def fetch_source_journal(journal: str) -> tuple[list[dict[str, Any]], str | None]:
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            return [], "budget"
        with execution_lock:
            executed_source_journals.add(journal)
        params = {
            "query.container-title": journal,
            "filter": f"from-pub-date:{DATE_FLOOR.isoformat()},until-pub-date:{dt.date.today().isoformat()}",
            "rows": int(CONFIG.get("crossref_source_first_rows", 60)),
            "sort": "published", "order": "desc",
            "select": "DOI,title,author,publisher,container-title,published-online,published-print,published,issued,type,URL,abstract,score",
        }
        for attempt in range(retries + 1):
            wait_for_slot()
            try:
                r = SESSION.get("https://api.crossref.org/works", params=params, timeout=timeout)
                if r.status_code == 200:
                    works = r.json().get("message", {}).get("items", [])
                    _diag_inc("crossref_raw_records", len(works))
                    # query.container-title is fuzzy; retain only the requested venue or a close punctuation variant.
                    target = re.sub(r'[^a-z0-9]+', '', normalized(journal))
                    exact = []
                    for w in works:
                        actual = clean_text((w.get("container-title") or [""])[0])
                        canon = re.sub(r'[^a-z0-9]+', '', normalized(actual))
                        if actual and (canon == target or canon.replace('and','') == target.replace('and','')):
                            exact.append(w)
                    return convert_items(exact, DATE_FLOOR, "source-first recent contents", journal), None
                if r.status_code == 429:
                    if attempt < retries:
                        retry_after = clean_text(r.headers.get("Retry-After"))
                        try:
                            base = float(CONFIG.get("public_429_cooldown_seconds", 8) or 8)
                            cap = float(CONFIG.get("public_429_max_cooldown_seconds", 30) or 30)
                            delay = min(cap, max(base * (attempt + 1), float(retry_after))) if retry_after else min(cap, base * (attempt + 1))
                        except Exception:
                            delay = min(30.0, 8.0 * (attempt + 1))
                        time.sleep(delay)
                        continue
                    return [], "HTTP 429 rate limited after cooldown retries"
                if r.status_code in {500, 502, 503, 504} and attempt < retries:
                    time.sleep(min(8.0, 1.5 * (attempt + 1))); continue
                return [], f"HTTP {r.status_code}"
            except Exception as e:
                if attempt < retries:
                    time.sleep(min(6.0, 1.5 * (attempt + 1))); continue
                return [], type(e).__name__
        return [], "request failed"

    out: list[dict[str, Any]] = []
    budget_hit = False

    if source_sweep_journals:
        log_progress(f"Crossref source-first journal sweep: {len(source_sweep_journals)} rotating journal(s) this run")
        for journal in source_sweep_journals:
            items, err = fetch_source_journal(journal)
            out.extend(items)
            if err == "budget":
                budget_hit = True; break
            if err:
                warnings.append(f"Crossref source-first {journal}: {err}")

    if priority_tasks and not budget_hit:
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
    if isinstance(execution_stats, dict):
        execution_stats.setdefault("crossref_broad_queries", set()).update(executed_broad_queries)
        execution_stats.setdefault("crossref_priority_tasks", set()).update(executed_priority_tasks)
        execution_stats.setdefault("crossref_source_journals", set()).update(executed_source_journals)
        execution_stats["crossref_abstracts_enrichment_attempted"] = int(execution_stats.get("crossref_abstracts_enrichment_attempted", 0)) + int(enrichment_total[0])
    return dedupe_candidates(out)


def _priority_affiliation_score(author_record: dict[str, Any], affiliation_hint: str) -> int:
    """Light disambiguation score for exact-name OpenAlex author candidates."""
    if not affiliation_hint:
        return 0
    hay = folded_person_name(json.dumps(author_record, ensure_ascii=False))
    stop = {"univ", "university", "institute", "institut", "center", "centre", "the", "and", "for"}
    tokens = [t for t in folded_person_name(affiliation_hint).split() if len(t) >= 4 and t not in stop]
    return sum(3 for t in dict.fromkeys(tokens) if t in hay)


def _resolve_priority_openalex_author(
    person: dict[str, Any],
    cache: dict[str, str],
    warnings: list[str],
    timeout: int,
) -> tuple[str, bool]:
    """Resolve an exact person name to an OpenAlex author ID, using affiliation hints to break ties."""
    name = clean_text(person.get("name"))
    key = folded_person_name(name)
    cached = clean_text(cache.get(key))
    if cached:
        return cached, False
    try:
        r = openalex_get("authors", params={"search": name, "per-page": 10}, timeout=timeout)
    except Exception as e:
        warnings.append(f"Priority people OpenAlex author resolution {name}: {type(e).__name__}")
        return "", True
    if r.status_code != 200:
        warnings.append(f"Priority people OpenAlex author resolution {name}: HTTP {r.status_code}")
        return "", True
    wanted = folded_person_name(name)
    ranked: list[tuple[int, int, str]] = []
    for author in r.json().get("results", []):
        if folded_person_name(clean_text(author.get("display_name"))) != wanted:
            continue
        score = 100 + _priority_affiliation_score(author, clean_text(person.get("affiliation_hint")))
        works_count = int(author.get("works_count", 0) or 0)
        author_id = clean_text(author.get("id")).rsplit("/", 1)[-1].upper()
        if author_id:
            ranked.append((score, works_count, author_id))
    if not ranked:
        return "", True
    ranked.sort(reverse=True)
    cache[key] = ranked[0][2]
    return ranked[0][2], True


def _tag_priority_candidate(item: dict[str, Any], person: dict[str, Any], origin: str) -> dict[str, Any]:
    """Keep researcher-attention provenance private to the scan process.

    Once admitted, a watched researcher's work must be indistinguishable from any other
    scholarly discovery in the public corpus.  Only the private origin marker is needed
    long enough to route the candidate back into the ordinary OpenAlex/Crossref pools.
    """
    tagged = dict(item)
    tagged["_priority_origin"] = origin
    tagged["_priority_person"] = clean_text(person.get("name"))
    return tagged


def collect_priority_people(
    people: list[dict[str, Any]],
    from_date: dt.date,
    warnings: list[str],
    stage_deadline: float | None = None,
    state: dict[str, Any] | None = None,
    execution_stats: dict[str, Any] | None = None,
    openalex_allowed: bool = True,
    crossref_allowed: bool = True,
    force_enabled: bool = False,
) -> list[dict[str, Any]]:
    """Give selected researchers extra discovery attention inside normal scholarly scanning.

    It never relaxes admission or creates a separate public content stream: OpenAlex/Crossref
    records still go through the same ``candidate_from_*`` functions as ordinary scholarly
    discovery. If both exact-author sources yield no record for a person, the caller receives
    one affiliation/topic context query for the normal scholarly collectors.
    """
    if not people or (not force_enabled and not bool(CONFIG.get("priority_people_enabled", True))):
        return []
    state = state if isinstance(state, dict) else {}
    cache = state.setdefault("priority_people_openalex_author_ids", {})
    if not isinstance(cache, dict):
        cache = {}
        state["priority_people_openalex_author_ids"] = cache
    timeout = max(4, int(CONFIG.get("scholarly_api_timeout_seconds", 12) or 12))
    rows = max(5, min(100, int(CONFIG.get("priority_people_rows_per_person", 40) or 40)))
    recover_remaining = max(0, int(CONFIG.get("priority_people_abstract_recovery_per_scan", 8) or 0))
    oa_enabled = bool(CONFIG.get("priority_people_openalex_enabled", True)) and bool(openalex_allowed)
    cr_enabled = bool(CONFIG.get("priority_people_crossref_enabled", True)) and bool(crossref_allowed)
    executed: set[str] = set()
    resolved: set[str] = set()
    context_queries: list[str] = []
    context_map: dict[str, str] = {}
    out: list[dict[str, Any]] = []
    raw_exact_hits = 0

    def near_deadline() -> bool:
        return bool(stage_deadline is not None and time.monotonic() >= stage_deadline - 10)

    for person in people:
        if near_deadline():
            warnings.append("Priority people stage budget reached; remaining people stay at the persisted cursor")
            break
        name = clean_text(person.get("name"))
        if not name:
            continue
        person_attempted = False
        person_raw_hits = 0

        if oa_enabled and not near_deadline():
            author_id, resolution_requested = _resolve_priority_openalex_author(person, cache, warnings, timeout)
            person_attempted = person_attempted or resolution_requested or bool(author_id)
            if author_id:
                resolved.add(name)
                filters = [f"authorships.author.id:{author_id}", f"author.id:{author_id}"]
                works: list[dict[str, Any]] = []
                for idx, author_filter in enumerate(filters):
                    params = {
                        "filter": f"{author_filter},from_publication_date:{from_date.isoformat()},to_publication_date:{dt.date.today().isoformat()}",
                        "sort": "publication_date:desc",
                        "per-page": rows,
                        "page": 1,
                    }
                    try:
                        r = openalex_get("works", params=params, timeout=timeout)
                    except Exception as e:
                        warnings.append(f"Priority people OpenAlex works {name}: {type(e).__name__}")
                        break
                    person_attempted = True
                    if r.status_code == 400 and idx == 0:
                        continue
                    if r.status_code != 200:
                        warnings.append(f"Priority people OpenAlex works {name}: HTTP {r.status_code}")
                        break
                    works = r.json().get("results", [])
                    break
                person_raw_hits += len(works)
                raw_exact_hits += len(works)
                for work in works:
                    item = candidate_from_openalex(work, date_floor=from_date)
                    if item is None and recover_remaining > 0:
                        doi = clean_text(work.get("doi"))
                        abstract = openalex_abstract(work.get("abstract_inverted_index"))
                        if doi and not abstract:
                            recovered = doi_landing_abstract(doi, timeout=min(timeout, 8))
                            if recovered:
                                recover_remaining -= 1
                                patched = dict(work)
                                inv: dict[str, list[int]] = {}
                                for pos, token in enumerate(clean_text(recovered).split()):
                                    inv.setdefault(token, []).append(pos)
                                patched["abstract_inverted_index"] = inv
                                item = candidate_from_openalex(patched, date_floor=from_date)
                    if item:
                        out.append(_tag_priority_candidate(item, person, "openalex"))

        if cr_enabled and not near_deadline():
            params = {
                "query.author": name,
                "filter": f"from-pub-date:{from_date.isoformat()},until-pub-date:{dt.date.today().isoformat()}",
                "rows": rows,
                "select": "DOI,title,author,publisher,container-title,published-online,published-print,published,issued,type,URL,abstract,score",
            }
            try:
                r = SESSION.get("https://api.crossref.org/works", params=params, timeout=timeout)
                person_attempted = True
                if r.status_code == 200:
                    items = (r.json().get("message") or {}).get("items", [])
                    wanted = folded_person_name(name)
                    exact_items = []
                    for raw in items:
                        author_names = [
                            clean_text(" ".join(x for x in [a.get("given"), a.get("family")] if clean_text(x)))
                            for a in (raw.get("author") or [])
                        ]
                        if wanted in {folded_person_name(x) for x in author_names if x}:
                            exact_items.append(raw)
                    person_raw_hits += len(exact_items)
                    raw_exact_hits += len(exact_items)
                    for raw in exact_items:
                        item = candidate_from_crossref(raw, date_floor=from_date)
                        if item is None and recover_remaining > 0:
                            doi = clean_text(raw.get("DOI"))
                            if doi and not clean_text(raw.get("abstract")):
                                recovered = doi_landing_abstract(doi, timeout=min(timeout, 8))
                                if recovered:
                                    recover_remaining -= 1
                                    patched = dict(raw)
                                    patched["abstract"] = recovered
                                    item = candidate_from_crossref(patched, date_floor=from_date)
                        if item:
                            out.append(_tag_priority_candidate(item, person, "crossref"))
                else:
                    warnings.append(f"Priority people Crossref {name}: HTTP {r.status_code}")
            except Exception as e:
                warnings.append(f"Priority people Crossref {name}: {type(e).__name__}")

        if person_attempted:
            executed.add(name)
        if person_attempted and person_raw_hits == 0:
            q = priority_person_context_query(person)
            if q and q not in context_queries:
                context_queries.append(q)
                context_map[q] = name

    if isinstance(execution_stats, dict):
        execution_stats.setdefault("priority_people_executed", set()).update(executed)
        execution_stats.setdefault("priority_people_openalex_resolved", set()).update(resolved)
        execution_stats["priority_people_raw_exact_hits"] = int(execution_stats.get("priority_people_raw_exact_hits", 0)) + raw_exact_hits
        execution_stats["priority_people_admitted"] = int(execution_stats.get("priority_people_admitted", 0)) + len(out)
        execution_stats["priority_people_context_queries"] = context_queries
        execution_stats["priority_people_context_map"] = context_map
        execution_stats["priority_people_abstract_recoveries_used"] = max(
            0, int(CONFIG.get("priority_people_abstract_recovery_per_scan", 8) or 0) - recover_remaining
        )
    return dedupe_candidates(out)


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
    try:
        parsed = urlparse(url)
        path_low = normalized(f"{parsed.path} {parsed.query}")
    except Exception:
        path_low = low
    hard_url_hits = [x for x in URL_HARD_EXCLUDE if x in path_low]
    c_discovery_surface = bool(hard_url_hits) and all(
        any(hit == allowed for allowed in C_DISCOVERY_URL_HINTS) for hit in hard_url_hits
    )
    if hard_url_hits and not c_discovery_surface:
        return -100
    if lastmod and lastmod < from_date - dt.timedelta(days=14):
        return -100
    # News/event/project paths receive a small ranking penalty, not a rejection.  Their
    # A/B exclusion is enforced after fetch; only qualifying C developments can survive.
    score = -2 if c_discovery_surface else 0
    if lastmod and lastmod >= from_date:
        score += 5
    hints = [
        "publication", "publications", "report", "reports", "paper", "policy-brief", "policy_brief",
        "study", "studies", "analysis", "research", "foresight", "horizon", "scenario", "security",
        "geopolit", "economic-security", "strategic-autonomy", "sovereignty", "science-diplomacy",
        "technology", "innovation", "working-paper", "discussion-paper", "insight", "briefing",
        "research-paper", "policy-paper", "download",
    ]
    score += min(12, 3 * sum(1 for h in hints if h in path_low))
    # Sparse Frontier cells also steer institutional discovery.  This is ranking,
    # not admission: a talent/brain-drain URL is fetched earlier but still has to
    # pass the same substantive A/B gate as every other page.
    gap_hits = sum(1 for term in ACTIVE_FRONTIER_GAP_URL_TERMS if normalized(term) in path_low)
    score += min(18, 6 * gap_hits)
    if re.search(r"/20\d{2}/", path_low):
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


def parse_institution_page(url: str, source: str, tier: int, stage_deadline: float | None = None, fingerprint: str = "", publication_floor: dt.date | None = None) -> dict[str, Any] | None:
    if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
        return None
    if bool(CONFIG.get("skip_known_institution_urls_before_fetch", True)) and normalized_link(url) in KNOWN_AB_LINKS:
        _diag_inc("institution_reject_known_before_fetch")
        return None
    r = get(url, timeout=int(CONFIG.get("institution_page_timeout_seconds", 12)))
    if not r or "html" not in r.headers.get("content-type", "text/html"):
        _diag_inc("institution_reject_fetch_or_nonhtml")
        return None
    if fingerprint:
        INSTITUTION_SEEN_FINGERPRINTS[fingerprint] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes").replace("+00:00", "Z")
    soup = BeautifulSoup(r.text, "html.parser")
    title = meta_content(soup, ["og:title", "twitter:title", "headline"]) or clean_text(soup.h1.get_text(" ", strip=True) if soup.h1 else "")
    page_type = meta_content(soup, ["og:type", "article:section", "type"])
    desc = meta_content(soup, ["description", "og:description", "twitter:description"])
    html_lang = clean_text((soup.html or {}).get("lang", "") if soup.html else "")
    # Early language rejection is allowed only with positive foreign-language evidence.
    # Short English institutional titles are often ambiguous until the body/PDF is read.
    lang_norm = normalized(html_lang).replace("_", "-")
    explicit_foreign_lang = bool(lang_norm and lang_norm not in ENGLISH_LANGUAGE_CODES and not lang_norm.startswith("en-"))
    # Do not reject a foreign-language page before reading it: it may expose a substantive
    # English abstract/executive summary lower in the page. Clear non-English metadata can still
    # reject here when the available title/description is already substantial and contains no
    # qualifying English evidence block.
    early_text = f"{title}. {desc}"
    if (not explicit_foreign_lang) and _strong_non_english_evidence(early_text, title_mode=False):
        _diag_inc("institution_reject_non_english")
        return None
    exclusion = document_exclusion_reason(title, desc, r.url, page_type)
    if not title:
        _diag_inc("institution_reject_no_title")
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
                published = parse_date(
                    obj.get("datePublished")
                    or obj.get("dateCreated")
                    or obj.get("uploadDate")
                    or obj.get("dateModified")
                )
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
    date_basis = "page"
    if not published:
        published = parse_date(meta_content(soup, [
            "article:published_time", "og:article:published_time", "datePublished", "dateCreated",
            "date", "DC.date", "DC.Date", "DC.date.issued", "DC.Date.issued", "dcterms.date",
            "dcterms.created", "dcterms.issued", "parsely-pub-date", "pubdate", "publication_date",
            "citation_publication_date", "citation_date", "release_date", "dateModified",
        ]))
    if not published:
        # Common institutional CMS fallback: semantic <time> elements.
        for tm in soup.find_all("time")[:8]:
            raw_time = clean_text(tm.get("datetime") or tm.get_text(" ", strip=True))
            published = parse_date(raw_time)
            if published:
                break
    if not published:
        # URL dates are reliable enough when all three components are explicit.
        m_url_date = re.search(r"/(20\d{2})/(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])(?:/|$)", urlparse(r.url).path)
        if m_url_date:
            try:
                published = dt.date(int(m_url_date.group(1)), int(m_url_date.group(2)), int(m_url_date.group(3)))
            except ValueError:
                published = None
    if not published:
        # Fail-closed body fallback: only parse an explicitly labelled published/date
        # phrase near the top of the page, never an arbitrary year mentioned in prose.
        top_text = clean_text((soup.find("article") or soup.find("main") or soup.body or soup).get_text(" ", strip=True))[:1800]
        m_labelled = re.search(r"\b(?:published|publication date|date)\s*[:\-]?\s*((?:[0-3]?\d[.\-/ ](?:0?\d|[A-Za-z]{3,9})[.\-/ ]20\d{2})|(?:[A-Za-z]{3,9}\s+[0-3]?\d,?\s+20\d{2})|(?:20\d{2}-\d{1,2}-\d{1,2}))", top_text, re.I)
        if m_labelled:
            published = parse_date(m_labelled.group(1))
    if not published and fingerprint:
        # Some authoritative institutional CMSs expose a precise sitemap lastmod but no
        # article publication meta tag. Accept it only for publication-like URLs that the
        # institutional scorer ranks positively; generic navigation pages remain ineligible.
        discovered = INSTITUTION_DISCOVERED_DATES.get(fingerprint)
        floor = publication_floor or DATE_FLOOR
        if discovered and institution_url_score(r.url, discovered, floor) >= 3:
            published = discovered
            date_basis = "sitemap_lastmod"
    if not published:
        _diag_inc("institution_reject_no_date")
        return None
    # A publication timestamp must not be an event date in the future. Some CMS pages
    # expose an upcoming event/deadline as their generic date field; treating that as
    # publication time creates future-dated weak signals and breaks retention semantics.
    if published > dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1):
        _diag_inc("institution_reject_future_date")
        return None
    effective_publication_floor = publication_floor or DATE_FLOOR
    if published < effective_publication_floor:
        _diag_inc("institution_reject_before_floor")
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
            # A report/paper linked from a /news/ wrapper must be judged as the underlying
            # document. Recalculate exclusions against the PDF rather than letting the
            # wrapper URL permanently block Strand A. Content-level exclusions still apply.
            exclusion = document_exclusion_reason(title, body[:1600], pdf_url, "")

    if not english_record_ok(f"{title}. {desc}. {body[:5000]}", html_lang, title=title):
        _diag_inc("institution_reject_non_english")
        return None

    # Short official pages are often poor Strand-A reports but excellent Strand-C
    # developments (for example a new research-talent measure, implementation decision,
    # restriction or capacity commitment). Preserve them for the weak-signal lane before
    # the report-length gate. They still have to pass the normal C topical gate and later
    # anchor to substantive Strand A, so this does not turn C into an institutional feed.
    if SIGNAL_WINDOW_START_DATE and published >= SIGNAL_WINDOW_START_DATE:
        signal_text = clean_text(f"{title}. {desc}. {body[:5000]}")
        signal_themes = themes_for(signal_text)
        if (
            weak_signal_candidate_text(title, f"{desc} {body[:3500]}")
            and strong_watch_signal_text(signal_text, signal_themes)
        ):
            signal_key = f"signal:{normalized(source)}:{norm_title(title)}"
            if signal_key not in KNOWN_SIGNAL_IDENTITIES:
                INSTITUTION_SIGNAL_CANDIDATES.append({
                    "headline": title,
                    "source": source,
                    "date": dt.datetime.combine(published, dt.time(12, 0), tzinfo=dt.timezone.utc).isoformat(timespec="minutes").replace("+00:00", "Z"),
                    "link": pdf_url or canonical or r.url,
                    "_desc": clean_text(f"{desc}. {body[:3500]}"),
                    "_themes": signal_themes,
                    "_entities": distinct_matches(signal_text, ENTITY_TERMS + GEO_ACTORS),
                    "_institutional_signal": True,
                })

    # A/B document-type exclusions are intentionally applied *after* the C discovery
    # opportunity above. Routine news/event/project/facility pages remain excluded.
    # Exception: an authoritative EU primary notice may itself be the evidence for a
    # material decision (formal adoption, restriction, funding/capacity commitment, etc.).
    # In that case, let the *underlying official source* try the normal substantive A gate.
    if exclusion:
        notice_exclusion = normalized(exclusion)
        notice_surface = any(x in notice_exclusion for x in [
            "press release", "news article", "news release",
            "hard exclusion url: /news/", "hard exclusion url: /press-release",
            "hard exclusion url: /press_releases",
        ])
        source_link = canonical or r.url
        full_notice_text = clean_text(f"{title}. {desc}. {body[:12000]}")
        notice_themes = themes_for(full_notice_text)
        notice_material = (
            contains_any(full_notice_text, MATURE_SIGNAL_MARKERS)
            or material_update_signal_text(full_notice_text)
            or reframing_signal_text(full_notice_text)
        )
        if (
            notice_surface
            and _source_merit_is_eu_official(source, source_link)
            and notice_material
            and strong_watch_signal_text(full_notice_text, notice_themes)
        ):
            notice_ev = gate_scope(title, desc, body, min(tier, 1), source_kind="institutional")
            _record_ab_gate_diagnostic("institution", notice_ev)
            if notice_ev.get("a_pass"):
                notice_strand = "both" if notice_ev.get("b_pass") else "A"
                result = build_item(
                    title=title, authors=", ".join(dict.fromkeys(a for a in authors if a)) or source,
                    source=source, date=published, link=pdf_url or canonical or r.url,
                    item_type="official notice / primary source", strand=notice_strand,
                    evidence=notice_ev, source_rank=float(tier), tier_label=f"Tier {tier}",
                    text=full_notice_text, doi="", preprint=False,
                )
                if date_basis != "page":
                    result["date_basis"] = date_basis
                return result
        _diag_inc("institution_reject_document_exclusion")
        return None

    # Retrieval sufficiency, not an admission-length rule. The written radar criterion is
    # "reject incidental mentions, not short documents"; source-aware aboutness below is
    # responsible for deciding substance. Only near-empty wrappers are stopped here.
    low_title = normalized(title)
    retrieval_floor = 100 if tier <= 2 else 180
    if word_count < retrieval_floor:
        _diag_inc("institution_reject_too_short")
        return None

    ev = gate_scope(title, desc, body, tier, source_kind="institutional")
    _record_ab_gate_diagnostic("institution", ev)
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
    result = build_item(
        title=title, authors=", ".join(dict.fromkeys(a for a in authors if a)) or source,
        source=source, date=published, link=pdf_url or canonical or r.url, item_type=item_type,
        strand=strand, evidence=ev, source_rank=float(tier), tier_label=f"Tier {tier}",
        text=f"{title}. {desc}. {body[:45000]}", doi="", preprint=False,
    )
    if date_basis != "page":
        result["date_basis"] = date_basis
    return result



def _source_adapter_domain_jobs(
    src: dict[str, Any],
    from_date: dt.date,
    stage_deadline: float | None = None,
    reconsider_seen: bool = False,
) -> list[tuple[str, str, int, str]]:
    """Bounded source-specific publication-hub discovery for the hardest EU/elite sites.

    Several high-value institutional domains either expose no usable sitemap or expose a
    sitemap that does not surface analytical publications reliably. Configuration provides
    a few known publication/research hubs per source. We crawl at most a couple of same-domain
    layers and still feed every discovered page through the ordinary parser/admission gates.
    This is not a search-engine shortcut and cannot directly admit anything.
    """
    if not bool(CONFIG.get("institution_source_adapter_enabled", True)):
        return []
    domain = clean_text(src.get("domain", "")).lower().removeprefix("www.")
    profiles = CONFIG.get("institution_source_adapters", {})
    profile = profiles.get(domain) if isinstance(profiles, dict) else None
    if not domain or not isinstance(profile, dict):
        return []
    source_name = clean_text(src.get("name")) or domain
    tier = int(src.get("tier", 2) or 2)
    base = f"https://{domain}"
    raw_hubs = profile.get("hub_paths") if isinstance(profile.get("hub_paths"), list) else []
    raw_seeds = profile.get("seed_urls") if isinstance(profile.get("seed_urls"), list) else []
    hubs = []
    for value in raw_hubs:
        raw = clean_text(value)
        if raw:
            hubs.append(raw if raw.startswith("http") else urljoin(base + "/", raw.lstrip("/")))
    hubs.extend(clean_text(x) for x in raw_seeds if clean_text(x))
    hubs = list(dict.fromkeys(hubs))
    if not hubs:
        return []

    path_hints = [normalized(x) for x in (profile.get("path_hints") or []) if clean_text(x)]
    max_fetches = max(1, int(CONFIG.get("institution_source_adapter_max_hub_fetches", 6) or 6))
    max_pages = max(1, int(CONFIG.get("institution_source_adapter_pages_per_domain", 20) or 20))
    max_depth = max(0, min(2, int(CONFIG.get("institution_source_adapter_crawl_depth", 2) or 2)))
    queue: list[tuple[str, int]] = [(u, 0) for u in hubs]
    fetched: set[str] = set()
    discovered: dict[str, int] = {}

    while queue and len(fetched) < max_fetches:
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            break
        hub, depth = queue.pop(0)
        nh = normalized_link(hub)
        if not nh or nh in fetched:
            continue
        fetched.add(nh)
        r = get(hub, timeout=int(CONFIG.get("institution_page_timeout_seconds", 12)))
        if not r or "html" not in r.headers.get("content-type", "text/html"):
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            u = urljoin(r.url, a.get("href", ""))
            pu = urlparse(u)
            host = (pu.hostname or "").lower().removeprefix("www.")
            if not host or not (host == domain or host.endswith("." + domain)):
                continue
            if pu.scheme not in {"http", "https"} or pu.fragment:
                continue
            low = normalized(u)
            path_probe = normalized(f"{pu.path} {pu.query}")
            if path_probe.endswith(".pdf") or any(path_probe.endswith(ext) for ext in (".doc", ".docx", ".xls", ".xlsx", ".zip")):
                continue
            label = normalized(a.get_text(" ", strip=True))
            # Hints apply to the path/anchor, not the host name. Otherwise a domain
            # such as research-and-innovation.ec.europa.eu would make every navigation
            # link look like a research publication.
            semantic_hits = sum(1 for hint in path_hints if hint and (hint in path_probe or hint in label))
            generic_score = institution_url_score(u, None, from_date)
            year_hit = bool(re.search(r"/(?:2025|2026)(?:/|-)" , path_probe))
            # Links from an explicitly configured publication hub get a modest trust
            # bonus, but generic navigation still needs a content/path signal.
            score = generic_score + min(12, semantic_hits * 4) + (3 if year_hit else 0)
            if semantic_hits or generic_score >= 3 or year_hit:
                discovered[u] = max(score, discovered.get(u, -100))
            if depth < max_depth and semantic_hits and generic_score >= -2 and normalized_link(u) not in fetched:
                queue.append((u, depth + 1))

    out: list[tuple[str, str, int, str]] = []
    for u, _score in sorted(discovered.items(), key=lambda kv: kv[1], reverse=True):
        nu = normalized_link(u)
        if bool(CONFIG.get("skip_known_institution_urls_before_fetch", True)) and nu in KNOWN_AB_LINKS:
            continue
        fp = institution_fingerprint(u, None)
        if fp in INSTITUTION_SEEN_FINGERPRINTS and not reconsider_seen:
            continue
        out.append((u, source_name, tier, fp))
        if len(out) >= max_pages:
            break
    _diag_inc("institution_adapter_jobs", len(out))
    return out


def _discover_domain(src: dict[str, Any], from_date: dt.date, bootstrap: bool = False, stage_deadline: float | None = None, reconsider_seen: bool = False) -> tuple[list[tuple[str, str, int, str]], str | None]:
    domain = src["domain"]
    adapter_jobs = _source_adapter_domain_jobs(src, from_date, stage_deadline, reconsider_seen)
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
        if adapter_jobs:
            return adapter_jobs, f"No usable sitemap: {domain}; using source-specific publication adapter ({len(adapter_jobs)} page(s))"
        # Trusted institutional sources without usable sitemaps still deserve bounded
        # source-local discovery. This follows only same-domain links from a few hubs;
        # it is not a global crawler or search-engine dependency.
        fallback = _rule_fix_fallback_domain_jobs(src, from_date, stage_deadline, reconsider_seen)
        if fallback:
            return fallback, f"No usable sitemap: {domain}; using bounded institutional HTML fallback ({len(fallback)} page(s))"
        return [], f"No usable sitemap: {domain}"
    seen = {normalized_link(u) for u, *_ in adapter_jobs}; jobs = list(adapter_jobs)
    limit_key = "institution_pages_per_domain_bootstrap" if bootstrap else "institution_pages_per_domain"
    limit = int(CONFIG.get(limit_key, CONFIG.get("institution_pages_per_domain", 24)))
    ranked = sorted(entries, key=lambda x: (institution_url_score(x[0], x[1], from_date), x[1] or dt.date.min), reverse=True)
    for u, last in ranked:
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            break
        if normalized_link(u) in seen or institution_url_score(u, last, from_date) < 0:
            continue
        if bool(CONFIG.get("skip_known_institution_urls_before_fetch", True)) and normalized_link(u) in KNOWN_AB_LINKS:
            continue
        fp = institution_fingerprint(u, last)
        if fp in INSTITUTION_SEEN_FINGERPRINTS and not reconsider_seen:
            continue
        if last:
            INSTITUTION_DISCOVERED_DATES[fp] = last
        seen.add(normalized_link(u))
        jobs.append((u, src["name"], int(src["tier"]), fp))
        if len(jobs) >= limit:
            break
    return jobs, None


def collect_institutions(from_date: dt.date, warnings: list[str], bootstrap: bool = False, sources_override: list[dict[str, Any]] | None = None, stage_deadline: float | None = None, execution_stats: dict[str, Any] | None = None, reconsider_seen: bool = False, publication_floor: dt.date | None = None) -> list[dict[str, Any]]:
    jobs = []
    sources = sources_override if sources_override is not None else CONFIG["institution_sources"]
    discovery_workers = int(CONFIG.get("institution_discovery_workers", 12))
    page_workers = int(CONFIG.get("institution_page_workers", 24))
    log_progress(f"Institutional discovery: {len(sources)} rotating source(s) this run")
    submitted_sources = []
    with cf.ThreadPoolExecutor(max_workers=max(1, discovery_workers)) as ex:
        futs = []
        for src in sources:
            if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
                break
            submitted_sources.append(clean_text(src.get("domain", "")).lower().removeprefix("www."))
            futs.append(ex.submit(_discover_domain, src, from_date, bootstrap, stage_deadline, reconsider_seen))
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
    _diag_inc("institution_pages_queued", len(jobs))
    log_progress(f"Institutional parsing: {len(jobs)} candidate page(s) queued")
    with cf.ThreadPoolExecutor(max_workers=max(1, page_workers)) as ex:
        futs = [ex.submit(parse_institution_page, u, s, t, stage_deadline, fp, publication_floor) for u, s, t, fp in jobs]
        for fut in cf.as_completed(futs):
            try:
                item = fut.result()
                if item:
                    out.append(item)
            except Exception as e:
                warnings.append(f"Institution page: {type(e).__name__}")
    if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
        warnings.append("Institutional report stage budget reached; remaining pages/sources will continue from the persisted cursor on later runs")
    if isinstance(execution_stats, dict):
        execution_stats.setdefault("institution_sources", set()).update(x for x in submitted_sources if x)
    return out


def _rule_fix_fallback_domain_jobs(
    src: dict[str, Any],
    from_date: dt.date,
    stage_deadline: float | None = None,
    reconsider_seen: bool = False,
) -> list[tuple[str, str, int, str]]:
    """Bounded same-domain HTML fallback for sources without a usable sitemap.

    This is deliberately source-local: no search engine, no global crawl.  It starts from
    a small set of institutional hubs plus verified recovery seeds, follows one same-domain
    link layer, and lets the normal page parser/admission rules decide what survives.
    """
    domain = clean_text(src.get("domain", "")).lower().removeprefix("www.")
    if not domain:
        return []
    source_name = clean_text(src.get("name")) or domain
    tier = int(src.get("tier", 2) or 2)
    seed_urls = list(RULE_FIX_RECOVERY_SEED_URLS.get(domain, []))
    base = f"https://{domain}"
    hubs = [base + path for path in RULE_FIX_FALLBACK_HUB_PATHS]
    queue = list(dict.fromkeys(seed_urls + hubs))
    seen_pages: set[str] = set()
    discovered: list[str] = list(seed_urls)
    max_hub_fetches = 8
    fetched_hubs = 0

    for hub in queue:
        if fetched_hubs >= max_hub_fetches or stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            break
        nh = normalized_link(hub)
        if nh in seen_pages:
            continue
        seen_pages.add(nh)
        r = get(hub, timeout=int(CONFIG.get("institution_page_timeout_seconds", 12)))
        fetched_hubs += 1
        if not r or "html" not in r.headers.get("content-type", "text/html"):
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            u = urljoin(r.url, a.get("href", ""))
            pu = urlparse(u)
            host = (pu.hostname or "").lower().removeprefix("www.")
            if not host or not (host == domain or host.endswith("." + domain)):
                continue
            if pu.scheme not in {"http", "https"}:
                continue
            low = normalized(u)
            if institution_url_score(u, None, from_date) < -2:
                continue
            if not (re.search(r"/20(?:25|26)/", low) or any(k in low for k in [
                "/news", "/publication", "/report", "/research", "/blog", "/article",
                "/insight", "/policy", "/session", "/event", "ai-safety", "scientific-panel",
            ])):
                continue
            discovered.append(u)

    out: list[tuple[str, str, int, str]] = []
    seen: set[str] = set()
    seed_norms = {normalized_link(u) for u in seed_urls}
    for u in discovered:
        nu = normalized_link(u)
        if not nu or nu in seen:
            continue
        seen.add(nu)
        if bool(CONFIG.get("skip_known_institution_urls_before_fetch", True)) and nu in KNOWN_AB_LINKS:
            continue
        fp = institution_fingerprint(u, None)
        # Direct recovery seeds are intentionally re-evaluated once under this new
        # repair version even if an earlier buggy pass fingerprinted them before
        # the relevant C/A-B logic was fixed. Ordinary hub-discovered pages still
        # respect the persisted seen cache.
        if fp in INSTITUTION_SEEN_FINGERPRINTS and nu not in seed_norms and not reconsider_seen:
            continue
        out.append((u, source_name, tier, fp))
        if len(out) >= max(8, int(RULE_FIX_SOURCE_RECOVERY_PAGES_PER_DOMAIN)):
            break
    return out


def _rule_fix_recovery_domain_jobs(
    src: dict[str, Any],
    from_date: dt.date,
    stage_deadline: float | None = None,
) -> tuple[list[tuple[str, str, int, str]], str | None]:
    """Discover a temporally balanced historical sample for a newly added source.

    Normal institutional rotation is intentionally incremental and must stay that way.
    This helper is only for the one-time V17.12.6 source catch-up.  It samples across
    months instead of taking only the newest sitemap URLs, so a newly introduced source
    can actually be checked back to the preserved corpus floor without resetting any
    normal cursor or global backfill flag.
    """
    domain = clean_text(src.get("domain", "")).lower().removeprefix("www.")
    if not domain:
        return [], None
    entries: list[tuple[str, dt.date | None]] = []
    max_entries = int(CONFIG.get("sitemap_max_entries", 800))
    for sm in discover_sitemaps(domain):
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            return [], f"Rule-fix source catch-up budget reached before finishing sitemap discovery: {domain}"
        entries.extend(sitemap_entries(sm))
        if len(entries) >= max_entries:
            break
    if not entries:
        fallback = _rule_fix_fallback_domain_jobs(src, from_date, stage_deadline)
        if fallback:
            return fallback, f"Rule-fix source catch-up: no usable sitemap for {domain}; used bounded HTML/seed fallback ({len(fallback)} page(s))"
        return [], f"Rule-fix source catch-up: no usable sitemap or fallback pages for {domain}"

    candidates: list[tuple[int, dt.date, str, str]] = []
    seen: set[str] = set()
    for u, last in entries:
        if u in seen:
            continue
        seen.add(u)
        score = institution_url_score(u, last, from_date)
        if score < 0:
            continue
        if bool(CONFIG.get("skip_known_institution_urls_before_fetch", True)) and normalized_link(u) in KNOWN_AB_LINKS:
            continue
        fp = institution_fingerprint(u, last)
        if fp in INSTITUTION_SEEN_FINGERPRINTS:
            continue
        # Missing sitemap dates remain eligible.  Dated URLs are sampled across months
        # below; using date.min for undated URLs keeps them from crowding out dated ones.
        candidates.append((score, last or dt.date.min, u, fp))

    if not candidates:
        return [], None

    per_domain = max(8, int(RULE_FIX_SOURCE_RECOVERY_PAGES_PER_DOMAIN))
    monthly: dict[tuple[int, int] | tuple[int, int], list[tuple[int, dt.date, str, str]]] = {}
    undated: list[tuple[int, dt.date, str, str]] = []
    for row in candidates:
        _score, last, _u, _fp = row
        if last == dt.date.min:
            undated.append(row)
        else:
            monthly.setdefault((last.year, last.month), []).append(row)

    selected: list[tuple[int, dt.date, str, str]] = []
    selected_urls: set[str] = set()
    # Round-robin across every observed month before taking extra pages.  This guarantees
    # that the oldest in-scope month is not crowded out by newer months when the per-domain
    # cap is reached (the exact failure mode the first repair exposed).
    month_rows = {
        ym: sorted(rows, key=lambda r: (r[0], r[1]), reverse=True)
        for ym, rows in monthly.items()
    }
    ordered_months = sorted(month_rows, reverse=True)
    depth = 0
    while len(selected) < per_domain and ordered_months:
        added_this_round = False
        for ym in ordered_months:
            rows = month_rows[ym]
            if depth >= len(rows):
                continue
            row = rows[depth]
            if row[2] not in selected_urls:
                selected.append(row); selected_urls.add(row[2])
                added_this_round = True
            if len(selected) >= per_domain:
                break
        if not added_this_round:
            break
        depth += 1

    # Fill remaining capacity with the strongest URLs overall, then a few undated URLs.
    for row in sorted(candidates, key=lambda r: (r[0], r[1]), reverse=True):
        if row[2] in selected_urls:
            continue
        selected.append(row); selected_urls.add(row[2])
        if len(selected) >= per_domain:
            break
    if len(selected) < per_domain:
        for row in sorted(undated, key=lambda r: r[0], reverse=True):
            if row[2] in selected_urls:
                continue
            selected.append(row); selected_urls.add(row[2])
            if len(selected) >= per_domain:
                break

    jobs = [(u, clean_text(src.get("name")) or domain, int(src.get("tier", 2) or 2), fp) for _s, _d, u, fp in selected[:per_domain]]
    # Verified source-local seeds guard against sitemap omissions and CMS archive gaps.
    seeded = _rule_fix_fallback_domain_jobs(src, from_date, stage_deadline)
    merged: list[tuple[str, str, int, str]] = []
    seen_jobs: set[str] = set()
    for row in seeded + jobs:
        nu = normalized_link(row[0])
        if not nu or nu in seen_jobs:
            continue
        seen_jobs.add(nu); merged.append(row)
        if len(merged) >= per_domain:
            break
    return merged, None


def collect_rule_fix_source_recovery(
    from_date: dt.date,
    warnings: list[str],
    stage_deadline: float | None = None,
    execution_stats: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """One-time, bounded catch-up for only the sources introduced by V17.12.5.

    This deliberately does *not* touch ``institution_cursor`` or any ordinary backfill
    marker.  The caller persists a separate completion marker only after every new
    source was attempted and this stage finished before its deadline.
    """
    sources = [dict(x) for x in RULE_FIX_INSTITUTION_SOURCES]
    discovery_workers = min(8, max(1, int(CONFIG.get("institution_discovery_workers", 12))))
    page_workers = min(18, max(1, int(CONFIG.get("institution_page_workers", 24))))
    submitted: list[str] = []
    jobs: list[tuple[str, str, int, str]] = []
    budget_hit = False
    log_progress(
        f"Targeted new-source catch-up: {len(sources)} source(s) from preserved corpus floor {from_date.isoformat()}"
    )
    sources_with_jobs: set[str] = set()
    with cf.ThreadPoolExecutor(max_workers=discovery_workers) as ex:
        futs: dict[Any, str] = {}
        for src in sources:
            if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
                budget_hit = True
                break
            domain = clean_text(src.get("domain", "")).lower().removeprefix("www.")
            if domain:
                submitted.append(domain)
            futs[ex.submit(_rule_fix_recovery_domain_jobs, src, from_date, stage_deadline)] = domain
        for fut in cf.as_completed(futs):
            domain = futs.get(fut, "")
            try:
                found, warn = fut.result()
                jobs.extend(found)
                if found and domain:
                    sources_with_jobs.add(domain)
                if warn:
                    warnings.append(warn)
            except Exception as e:
                warnings.append(f"Rule-fix source catch-up sitemap: {type(e).__name__}")

    # Keep this pass bounded even if a large institutional sitemap is unusually noisy.
    jobs = jobs[:max(1, int(RULE_FIX_SOURCE_RECOVERY_MAX_PAGES))]
    log_progress(f"Targeted new-source catch-up: parsing {len(jobs)} historical candidate page(s)")
    out: list[dict[str, Any]] = []
    with cf.ThreadPoolExecutor(max_workers=page_workers) as ex:
        futs = []
        for u, s, t, fp in jobs:
            if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
                budget_hit = True
                break
            futs.append(ex.submit(parse_institution_page, u, s, t, stage_deadline, fp))
        for fut in cf.as_completed(futs):
            try:
                item = fut.result()
                if item:
                    out.append(item)
            except Exception as e:
                warnings.append(f"Rule-fix source catch-up page: {type(e).__name__}")

    if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
        budget_hit = True
    if isinstance(execution_stats, dict):
        execution_stats.setdefault("rule_fix_recovery_sources", set()).update(x for x in submitted if x)
        execution_stats.setdefault("rule_fix_recovery_sources_with_jobs", set()).update(sources_with_jobs)
        execution_stats["rule_fix_recovery_budget_hit"] = bool(budget_hit)
        execution_stats["rule_fix_recovery_jobs"] = len(jobs)
        execution_stats["rule_fix_recovery_admitted_ab"] = len(out)
    if budget_hit:
        warnings.append("Targeted new-source catch-up budget reached; completion marker left pending for the next scan")
    return dedupe_candidates(out)


def manual_recovery_jobs(previous: dict[str, Any], limit: int | None = None) -> list[dict[str, Any]]:
    """Return a bounded exact-URL recovery queue created by manual candidate ingestion.

    The queue affects discovery only. Every recovered document must still pass the normal
    source-aware A/B substantive gate before it can enter the corpus.
    """
    manual = previous.get("manual_ingest") if isinstance(previous.get("manual_ingest"), dict) else {}
    queue = manual.get("recovery_queue") if isinstance(manual.get("recovery_queue"), list) else []
    cap = int(CONFIG.get("manual_recovery_urls_per_scan", 10) if limit is None else limit)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in queue:
        if not isinstance(entry, dict):
            continue
        if clean_text(entry.get("manual_candidate_kind") or "substantive") != "substantive":
            continue
        url = clean_text(entry.get("url"))
        title = clean_text(entry.get("title"))
        if not url or not title:
            continue
        nurl = normalized_link(url)
        if nurl in KNOWN_AB_LINKS or nurl in seen:
            continue
        seen.add(nurl)
        out.append(entry)
        if cap > 0 and len(out) >= cap:
            break
    return out


def collect_manual_recovery(previous: dict[str, Any], warnings: list[str], stage_deadline: float | None = None, execution_stats: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Retry exact URLs supplied through manual ingest using the scanner's normal gate."""
    jobs = manual_recovery_jobs(previous)
    if not jobs:
        return []
    out: list[dict[str, Any]] = []
    attempted = 0
    for entry in jobs:
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            warnings.append("Manual recovery scan budget reached; remaining exact URLs stay queued")
            break
        url = clean_text(entry.get("url"))
        title = clean_text(entry.get("title"))
        source = clean_text(entry.get("source")) or url_domain(url)
        tier = int(entry.get("tier", 2) or 2)
        attempted += 1
        item = None
        if url.lower().split("?", 1)[0].endswith(".pdf"):
            body, words = pdf_text(url)
            date = None
            # Manual ingest may store the first day of a year/month solely as a
            # sortable representation. Never turn a bare-year or explicitly
            # unverified bibliography date into evidence of an in-window PDF.
            if not entry.get("manual_verification_required") and clean_text(entry.get("date_precision")) in {"day", "month", ""}:
                date = parse_date(entry.get("date"))
            if body and words >= 120 and date and date >= DATE_FLOOR:
                ev = gate_scope(title, "", body, tier, source_kind=clean_text(entry.get("source_kind")) or "institutional")
                _record_ab_gate_diagnostic("manual_recovery", ev)
                if ev.get("a_pass") or ev.get("b_pass"):
                    strand = "both" if ev.get("a_pass") and ev.get("b_pass") else "A" if ev.get("a_pass") else "B"
                    item = build_item(
                        title=title, authors=source, source=source, date=date, link=url,
                        item_type="manual-recovered source", strand=strand, evidence=ev,
                        source_rank=float(tier), tier_label=f"Tier {tier}",
                        text=f"{title}. {body[:45000]}", doi=clean_text(entry.get("doi")), preprint=False,
                    )
        else:
            item = parse_institution_page(url, source, tier, stage_deadline=stage_deadline)
        if item:
            item["provenance"] = ["automated_discovery", "manual_candidate_ingestion"]
            item["discovery_provenance"] = "both"
            mid = clean_text(entry.get("manual_id"))
            if mid:
                item["manual_ingest_ids"] = [mid]
            item["manual_recovery"] = True
            out.append(item)
    if isinstance(execution_stats, dict):
        execution_stats["manual_recovery_urls_attempted"] = int(execution_stats.get("manual_recovery_urls_attempted", 0)) + attempted
        execution_stats["manual_recovery_admitted"] = int(execution_stats.get("manual_recovery_admitted", 0)) + len(out)
    return dedupe_candidates(out)

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


def frontier_target_sentence_score(sentence: str, targets: Iterable[str] | None) -> int:
    """Score a source sentence only when it states the mechanism of a targeted empty cell.

    This never adds claims.  It only prevents an abstract sentence that caused a gap query
    to match from being discarded by the generic three-sentence summary selector.
    """
    t = normalized(sentence)
    if not t:
        return 0
    target_set = set(targets or [])
    eu = bool(re.search(r"\b(eu|europe|european|member states|germany|france|italy|spain|netherlands|sweden|finland|denmark|poland|ireland|austria|belgium)\b", t))
    ext = bool(re.search(r"\b(foreign|non eu|third country|china|chinese|united states|american|international)\b", t))
    knowledge = bool(re.search(r"\b(researcher|researchers|scientist|scientists|research talent|scientific talent|research workforce|research collaboration|scientific collaboration|expertise|doctoral candidate|doctoral candidates|phd student|phd students|international student|international students|stem student|stem students|international graduate|international graduates|visiting researcher|visiting researchers|research visit|research visits)\b", t))
    infra = bool(re.search(r"\b(compute|cloud|semiconductor|chip|chips|infrastructure|supply chain|critical raw material|critical mineral|reactor|quantum|data cent(?:er|re))\b", t))
    conversion = bool(re.search(r"\b(firm|firms|company|companies|startup|scale up|scaleup|manufactur|production|factory|industrial)\b", t))
    rules = bool(re.search(r"\b(rule|rules|standard|standards|regulation|export control|licen[cs]|platform rules|governance)\b", t))
    autonomy_up = bool(re.search(r"strategic autonomy|sovereign|domestic capacity|european capacity|onshor|reshor|local production|reduce.{0,35}(depend|reliance)|diversif|de risk", t))
    autonomy_down = bool(re.search(r"dependence on|dependent on|reliance on|foreign (supplier|vendor|technology|expertise|talent|infrastructure|researchers|students|graduates)|international (researchers|research talent|doctoral candidates|students|graduates)|third country (researchers|students|graduates)|non eu (technology|vendor|supplier|researchers|students|graduates)|loss of access|restricted access|lock in", t))
    perf_up = bool(re.search(r"competit|excellence|leading|leader|advanced|capacity|capabilit|performance|benefit|strengthen|innovation|access to", t))
    perf_down = bool(re.search(r"lag|behind|costly|expensive|higher cost|shortage|bottleneck|delay|slow|declin|loss|hollow|gap|no substitute|disrupt|cut off|constraint", t))
    loss_people = bool(re.search(r"brain drain|researcher outflow|researchers? (leave|leaving|left)|scientists? (leave|leaving|left)|talent outflow|loss of (research|scientific) talent|unable to retain|moving abroad", t))
    firm_loss = bool(re.search(r"firm exit|firms exit|exit europe|move abroad|moving abroad|relocat|foreign acquisition|closure|shut down|hollow|lost production|loss of production|scale up gap|scaleup gap|funding gap|industrial decline", t))
    foreign_rules = bool(re.search(r"foreign standards|foreign rules|us rules|american rules|platform rules|non eu rules|non eu standards|us export control|export licen[cs]", t))

    scores=[]
    talent_pipeline = bool(re.search(r"(?:international|foreign|third country|non eu).{0,55}(?:researchers|scientists|doctoral candidates|phd students|students|graduates|visiting researchers)|(?:researchers|scientists|doctoral candidates|phd students|students|graduates|visiting researchers).{0,55}(?:international|foreign|third country|non eu)", t)) and bool(re.search(r"retain|retention|stay|post study|post research|career|employment|innovation|research capacity|scientific capacity|competitiveness|capability", t))
    if "knowledge-C" in target_set and knowledge and (ext or talent_pipeline) and (autonomy_down or talent_pipeline or re.search(r"foreign (expertise|talent)|international researchers", t)) and perf_up:
        scores.append(10 + int(eu))
    if "knowledge-D" in target_set and knowledge and loss_people and eu:
        scores.append(12)
    if "infrastructure-B" in target_set and infra and autonomy_up and perf_down:
        scores.append(11 + int(eu))
    if "infrastructure-D" in target_set and infra and (autonomy_down or re.search(r"loss of access|restricted access|supply disruption|shortage|cut off", t)) and perf_down:
        scores.append(11 + int(eu))
    if "conversion-D" in target_set and conversion and firm_loss and (perf_down or re.search(r"loss|declin|gap|hollow", t)):
        scores.append(11 + int(eu))
    if "rules-C" in target_set and rules and foreign_rules and (autonomy_down or ext) and perf_up:
        scores.append(11 + int(eu))
    return max(scores, default=0)


def make_summary(text: str, evidence: dict[str, Any], strand: str, title: str, frontier_targets: Iterable[str] | None = None) -> str:
    sents = split_sentences(text)
    selected = []
    # Prefer sentences that carry explicit gate evidence.
    for key in ("bridge_sentence", "method_bridge"):
        s = clean_text(evidence.get(key))
        if s and s not in selected:
            selected.append(s)
    # Preserve the strongest source sentence for the empty Frontier cell that caused
    # this record to be fetched. V17.7.4 often admitted the paper but then summarized
    # away the exact dependency/loss/cost mechanism, making the Frontier classifier
    # unable to use evidence the scanner had genuinely found.
    targeted = sorted(
        ((frontier_target_sentence_score(sent, frontier_targets), -i, sent) for i, sent in enumerate(sents[:80])),
        reverse=True,
    )
    if targeted and targeted[0][0] > 0 and targeted[0][2] not in selected:
        selected.append(targeted[0][2])
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
        f"The indexed record did not expose a complete abstract for {title.rstrip('.')}",
        f"The item was admitted to Strand {strand} from the source text available at scan time",
        "Consult the linked publication for the full argument, evidence and methods",
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



def _claim80(text: str) -> str:
    s = clean_text(text)
    s = re.sub(r"^(?:Abstract\s*[:.-]?\s*)", "", s, flags=re.I)
    s = re.sub(
        r"^(?:(?:this|the) (?:study|paper|article|report|analysis|results?) "
        r"(?:finds?|shows?|argues?|concludes?|demonstrates?|identifies?|reveals?|indicates?|suggests?)|"
        r"it (?:finds?|shows?|argues?|concludes?|demonstrates?|identifies?|reveals?|indicates?|suggests?))\s+(?:that\s+)?",
        "", s, flags=re.I,
    )
    s = re.sub(r"^(?:the results show|results show|we find|we show|we argue|we demonstrate|we identify)\s+(?:that\s+)?", "", s, flags=re.I)
    s = s.strip(" .:;–—-")
    ns = normalized(s)
    if "three enablers" in ns and all(x in ns for x in ["robustness", "appropriateness", "inclusivity"]):
        return "Foresight evidence improves with robustness, appropriateness and inclusivity"
    if "three strategic priorities" in ns and "brain drain" in ns and "research assessment" in ns and "co-funding" in ns:
        return "Europe can counter brain drain via monitoring, assessment reform and co-funding"
    if len(s) <= 80:
        return s.rstrip(".!?")
    cut = s[:80]
    # Prefer a complete clause when one exists before the hard limit.
    for sep in ("; ", ", while ", ", but ", ": "):
        i = cut.lower().rfind(sep.lower())
        if i >= 44:
            cut = cut[:i]
            break
    cut = re.sub(r"\s+\S*$", "", cut).rstrip(" ,:;–—-")
    if len(cut) < 42:
        cut = s[:79].rstrip()
    return (cut[:79].rstrip(" ,:;–—-.!?") + "…")[:80]


def _plain_claim_limit(text: str, max_chars: int = 120) -> str:
    """Return one complete, explicit reader point of at most ``max_chars`` characters."""
    s = clean_text(text).strip()
    if not s or "…" in s or "..." in s:
        return ""

    vague = re.compile(
        r"^(?:(?:this|these|those|it|they|such)\b|the "
        r"(?:study|paper|article|report|analysis|research|results?|findings?|developments?|changes?|trends?|issues?)\b)",
        re.I,
    )
    dependent_start = re.compile(r"^(?:to support (?:this|these)|with\b|since\b|because\b|while\b|although\b|building on\b|drawing on\b|based on\b)", re.I)
    predicate = re.compile(r"\b(?:is|are|was|were|has|have|had|can|could|may|might|will|would|should|must|show|find|argue|conclude|reveal|indicate|suggest|highlight|shape|treat|use|map|face|gain|lose|create|make|help|drive|constrain|allow|remain|become|depend|rely|change|shift|link|raise|cut|add|limit|fund|launch|open|close|adopt|propose|plan|build|develop|deploy|establish|agree|sign|join|withdraw|target|support|secure|protect|screen|coordinate|compete|reform|amend|extend|approve|reject|connect|urge|struggle|perform|serve|stress|need|trail|offer|respond|pivot|introduce|expand|reduce|increase|strengthen|weaken|move|pull|push|balance)\w*\b", re.I)

    def shrink(q: str) -> str:
        q = clean_text(q)
        q = re.sub(r"^(?:Finally|Moreover|However|Therefore|In addition|Accordingly|Rather|On the other hand|In conclusion),?\s+", "", q, flags=re.I)
        q = re.sub(r"\bthe European Union\b", "the EU", q, flags=re.I)
        q = re.sub(r"\bEuropean Union\b", "EU", q, flags=re.I)
        q = re.sub(r"\bUnited States\b", "US", q, flags=re.I)
        q = re.sub(r"\bartificial intelligence\b", "AI", q, flags=re.I)
        q = re.sub(r"\bresearch and innovation\b", "R&I", q, flags=re.I)
        q = re.sub(r"\btechnological sovereignty\b", "tech sovereignty", q, flags=re.I)
        q = re.sub(r"\bstrategic autonomy\b", "autonomy", q, flags=re.I)
        q = re.sub(r"\bin order to\b", "to", q, flags=re.I)
        q = re.sub(r"\bwith a view to\b", "to", q, flags=re.I)
        q = re.sub(r"\bcomparatively\b|\bparticularly\b", "", q, flags=re.I)
        return clean_text(q)

    def finish(q: str) -> str:
        q = shrink(q).strip(" ;:–—")
        if not q or vague.match(q) or dependent_start.match(q) or len(q) > max_chars:
            return ""
        if not predicate.search(q):
            return ""
        if q[-1:] not in ".!?":
            q += "."
        return q if len(q) <= max_chars else ""

    direct = finish(s)
    if direct:
        return direct

    sentence_list = [clean_text(x) for x in split_sentences(s) if clean_text(x)]
    for sent in sentence_list:
        out = finish(sent)
        if out:
            return out

    for candidate in [s, *sentence_list]:
        parts = re.split(
            r"\s*[;]\s*|\s+[–—]\s+|,\s+(?=(?:while|but|although|which|with|including|reflecting|raising|pushing|binding|and|as|increasing|reducing|broadening|expanding|creating|leaving|showing|giving|making|providing|allowing|helping|limiting|keeping|turning)\b)|\s+(?=without\b)|\s+(?=as\b)",
            shrink(candidate),
            flags=re.I,
        )
        for part in parts:
            if len(clean_text(part).split()) < 6:
                continue
            out = finish(part)
            if out:
                return out
    return ""


def plain_language_claim(summary: str, title: str, existing: str = "") -> str:
    """Return the reader-facing claim while leaving source/bibliographic text unchanged.

    This is the write-boundary counterpart of ``briefing/insights.js``. New automated
    discoveries and manual additions pass through it before ``core_message`` is stored.
    The transformation is deliberately source-bound: it simplifies wording and removes
    academic/list scaffolding, but it does not invent facts not present in the record.
    """
    t = clean_text(title)
    raw = clean_text(summary)
    prior = clean_text(existing)
    context = normalized(f"{t} {raw} {prior}")

    # Recurring dense constructions that need a semantic, not merely cosmetic, rewrite.
    if ("artificial intelligence act" in context or "eu ai act" in context or "ai act" in context) and "regulatory" in context and "ethical" in context:
        return "The EU AI Act creates a risk-based governance framework for AI systems."

    if (
        "ireland" in context
        and "pressure to diversify" in context
        and "current us administration" in context
        and "geopolitical instability" in context
    ):
        return "US–China tensions and US uncertainty are narrowing Ireland's room for science-tech cooperation with China."

    if (
        "semiconductor export controls" in context
        and "economic interests toward china" in context
        and "security relations with the united states" in context
    ):
        return "EU chip controls protect technology while Europe balances China trade and US security ties."

    if (
        "copernican academy" in context
        and "collegium intermarium" in context
        and "intermarium" in context
        and ("neo-nationalist" in context or "neo nationalist" in context)
    ):
        return "Polish research policy has been pulled into geopolitical and neo-nationalist projects."

    if (
        ("diffusion of dual-use technologies" in context or "diffusion of dual use technologies" in context)
        and ("cross-border knowledge transfer" in context or "cross border knowledge transfer" in context)
        and "dependencies in strategically important supply chains" in context
    ):
        return "EU research-security risks include dual-use spread, knowledge leakage and critical-supply dependence."

    if "e-hryvnia" in context and "bahamas" in context and "china" in context and ("cyber resilience" in context or "cyberresilience" in context):
        return "Ukraine's e-hryvnia puts unusual weight on transparency and cyber resilience."

    if "global cybersecurity governance" in context and "african union" in context and ("multistakeholder" in context or "gfce" in context or "igf" in context):
        return "Regional blocs such as the EU and African Union can move toward shared cyber rules."

    if "ai4s" in context and all(x in context for x in ["china", "japan", "united kingdom"]):
        return "The US, China, EU, UK and Japan treat AI for science as a tool for faster research and competitiveness."

    if "mapping of technology specialisation" in context and "venture capital" in context and "patent" in context:
        return "Patents, papers and venture capital show where the EU and global partners specialise."

    if "no one builds alone" in context and "open hardware" in context and "india" in context and ("ai chips" in context or "ai chip" in context):
        return "Open hardware could give Europe and India more control over AI-chip technology."

    # If a previous concise claim exists, preserve its proposition and simplify its wording.
    # The browser layer rejects chopped/ellipsised claims and re-extracts from source detail,
    # so the write boundary must not replace an established claim with a different sentence.
    s = prior or concise_core_message(raw, t)
    s = clean_text(s)
    if not s:
        return ""

    # General plain-language cleanup. Keep this conservative: the goal is shorter verbs,
    # named institutions/actors where already explicit, and less bureaucratic scaffolding.
    s = re.sub(r"^(?:First|Second|Third|Fourth|Finally),?\s+", "", s, flags=re.I)
    s = re.sub(
        r"^(?:Focusing on|Drawing on|Drawing upon|Based on|Using)\b[^,]{0,220},\s*"
        r"(?=(?:the|this) (?:study|paper|article|report)\b)",
        "", s, flags=re.I,
    )
    s = re.sub(
        r"^(?:the|this) (?:study|paper|article|report|analysis|research|results?) "
        r"(?:finds|shows|argues|concludes|demonstrates|identifies|reveals|indicates|suggests) (?:that\s+)?",
        "", s, flags=re.I,
    )
    s = re.sub(r"^These findings (?:show|reveal|indicate|suggest|underscore) (?:that\s+)?", "", s, flags=re.I)
    s = re.sub(r"^In the European Union\s*\(EU\)\s+Member States\b", "EU member states", s)
    s = re.sub(r"\bThe European Union\s*\(EU\)", "The EU", s)
    s = re.sub(r"\bthe European Union\s*\(EU\)", "the EU", s)
    s = re.sub(r"\bEuropean Union\s*\(EU\)", "EU", s)
    s = re.sub(r"\bThe European Union\b", "The EU", s)
    s = re.sub(r"\bthe European Union\b", "the EU", s)
    s = re.sub(r"\bUnited States\s*\(US\)", "US", s)
    s = re.sub(r"\bUnited States\b", "US", s)
    replacements = [
        (r"\bdemonstrates\b", "shows"),
        (r"\binstrumentali[sz]ed to advance\b", "used to support"),
        (r"\binstrumentali[sz]ed\b", "used"),
        (r"\bsemiconductor export controls\b", "chip export controls"),
        (r"\bsecurity relations\b", "security ties"),
        (r"\beconomic interests\b", "trade interests"),
        (r"\bgeopolitical instability\b", "global instability"),
        (r"\bstrategically important supply chains\b", "critical supply chains"),
        (r"\bthe emergence of dependencies in\b", "dependence on"),
        (r"\bthe diffusion of dual-use technologies\b", "dual-use tech spreading"),
        (r"\bcross-border knowledge transfer\b", "knowledge moving abroad"),
        (r"\bin order to\b", "to"),
        (r"\bwith a view to\b", "to"),
    ]
    for pat, repl in replacements:
        s = re.sub(pat, repl, s, flags=re.I)
    s = clean_text(s).strip(" ;:–—")
    out = _plain_claim_limit(s)
    if out:
        return out
    for sentence in split_sentences(raw):
        q = clean_text(sentence)
        q = re.sub(
            r"^(?:the|this) (?:study|paper|article|report|analysis|research|results?) "
            r"(?:finds|shows|argues|concludes|demonstrates|identifies|reveals|indicates|suggests|highlights) (?:that\s+)?",
            "", q, flags=re.I,
        )
        q = re.sub(r"^These findings (?:show|reveal|indicate|suggest|underscore) (?:that\s+)?", "", q, flags=re.I)
        out = _plain_claim_limit(q)
        if out:
            return out
    return ""


def concise_core_message(summary: str, title: str) -> str:
    """Extract a concrete source-backed claim for display; never return a generic topic slogan."""
    t = clean_text(title)
    raw = clean_text(summary)
    raw = re.sub(r"(?<=[a-z0-9])\.(?=[A-Z])", ". ", raw)
    # OCR/abstract feeds often concatenate section markers without punctuation. Recover the
    # findings sentence before ranking so "Results The results show ..." is not buried inside
    # a methodology sentence.
    raw = re.sub(r"\b(?:Results?|Findings?|Conclusions?)\s+(?=(?:The|We|Our|These|This)\b)", ". ", raw, flags=re.I)
    candidates = []
    for i, sent in enumerate(split_sentences(raw)[:24]):
        q = clean_text(sent)
        if not q:
            continue
        if t and (norm_title(q) == norm_title(t) or normalized(q).startswith(normalized(t)[:120])):
            continue
        # Remove a leading method/data clause when the same sentence then states the actual
        # finding or contribution: "Drawing on X, the article demonstrates that Y" -> Y.
        q = re.sub(
            r"^(?:drawing on|drawing upon|based on|using|through|building on|drawing from)\b[^,]{0,220},\s*",
            "", q, flags=re.I,
        )
        m = re.search(r"\b(we (?:develop|propose|find|show|identify)|the (?:study|paper|article|analysis) (?:finds|shows|argues|demonstrates|identifies|reveals|highlights))\b", q, flags=re.I)
        if m and m.start() > 20:
            q = q[m.start():]
        nq = normalized(q)
        if any(x in nq for x in [
            "the paper identifies best practices and policy gaps",
            "its eu relevance is classified", "the indexed record did not expose", "consult the linked publication",
            "the item was admitted to strand", "the purpose of this article", "the purpose of this paper",
            "the aim of the article", "the aim of this article", "this article examines", "this paper examines",
            "this study examines", "this research aimed", "table of contents", "references",
            "the relevance of the study", "the relevance of this study",
        ]):
            continue
        methodish = bool(re.search(
            r"\b(synthesi[sz]es?|is based on|are based on|comparative method|statistical method|analytical method|"
            r"systematic literature review|bibliometric|study was conducted|study is conducted|study examined if|"
            r"analysis also considered|we use the model to analyse|we use the model to analyze|reflect on|tries to explain)\b",
            nq,
        ))
        strong_result = bool(re.search(
            r"\b(results? show|findings? show|find|finds|found|show|shows|showed|argue|argues|conclude|concludes|"
            r"demonstrate|demonstrates|identify|identifies|reveal|reveals|indicate|indicates|highlight|highlights|"
            r"propose|proposes|recommend|recommends)\b",
            nq,
        ))
        if methodish and not strong_result:
            continue
        score = 0
        if re.search(r"\b(results? show|findings? show|find|finds|found|show|shows|showed|argue|argues|conclude|concludes|demonstrate|demonstrates|identify|identifies|reveal|reveals|indicate|indicates|highlight|highlights)\b", nq):
            score += 10
        if re.search(r"\b(propose|proposes|recommend|recommends|calls for|priorities)\b", nq):
            score += 7
        if re.search(r"\b(develop|develops|developed|adapt|adapts|adapted)\b", nq) and re.search(r"\b(framework|method|methodology|foresight|enablers?)\b", nq):
            score += 7
        if re.search(r"\b(is|are|has|have|becomes?|shifts?|strengthens?|weakens?|increases?|reduces?|limits?|depends?|concentrated|fragmented|unbalanced|transformation|gap|risk|risks|vulnerability|vulnerabilities|dependence|dependency|autonomy|competition|constraint|constraints)\b", nq):
            score += 4
        if contains_any(q, EU_DIRECT + EU_GENERIC) or has_eu_word(q):
            score += 2
        if re.search(r"\b(research|science|innovation|technology|semiconductor|ai|quantum|talent|security|collaboration|investment|foresight)\b", nq):
            score += 2
        if re.match(r"^(despite |although |against this background|in this article|in this study)", nq):
            score -= 6
        score -= i * 0.12
        candidates.append((score, -i, q))
    if candidates:
        candidates.sort(reverse=True)
        if candidates[0][0] > 0:
            best = _claim80(candidates[0][2])
            nb, nt_full = norm_title(best), norm_title(t)
            if best and not (nb and nt_full and (nt_full.startswith(nb) or nb.startswith(nt_full[:min(48, len(nt_full))]))):
                return best

    # Turn common title forms into concrete propositions rather than echoing an opaque
    # publication title. These rewrites use only information explicitly present in title/text.
    nt = normalized(t)
    if "semiconductor" in nt and "strategic autonomy" in nt and "technological leadership" in nt:
        return _claim80("Chips policy targets EU semiconductor autonomy and technological leadership")
    if "research security" in nt and "geopolitical" in nt and ("eu" in nt or "europe" in nt):
        return _claim80("EU research security is becoming part of Europe’s geopolitical strategy")
    if "expenditure on research and development" in nt and ("european union" in nt or "eu" in nt):
        return _claim80("EU business R&D spending is compared in an international context")
    if "international investment" in nt and "artificial intelligence" in nt and "technological dependence" in nt:
        return _claim80("AI investment asymmetry creates technological-dependence risks for EU countries")
    if "weak signal detection" in nt and "stochastic resonance" in nt:
        return _claim80("Stochastic resonance methods are advanced for weak-signal detection")
    if "backcasting" in nt and "urban mobility" in nt:
        return _claim80("Backcasting maps pathways toward just and sustainable urban mobility")
    if "roadmapping framework" in nt:
        return _claim80("A data-driven roadmapping method supports resilient disaster management")
    if "cbdc" in nt and "systemic risk" in nt:
        return _claim80("CBDCs bring strategic choices, systemic risks and regulatory constraints")
    if "impact of the eu ai act" in nt and "market access" in nt and "innovation" in nt:
        return _claim80("The study tests EU AI Act effects on market access and healthcare AI innovation")
    if "flanders" in nt and "investment priorities" in nt and "strategic technologies" in nt:
        return _claim80("Flanders prioritises investment in key strategic technologies")
    if "horizon scanning methodology" in nt and "early signal" in nt:
        return _claim80("Horizon scanning methods are developed for early-signal identification")
    if "forest pests" in nt and "horizon scanning" in nt and "climate" in nt:
        return _claim80("Horizon scanning is adapted to climate-driven forest-pest range expansion")
    if "bibliometric mapping of brand activism" in nt:
        return _claim80("Brand-activism research is mapped by trends, themes and trajectories")
    if "implementation of research security policies in germany" in nt:
        return _claim80("Germany implements research-security policy across governance levels")
    if "academic cooperation from the souths" in nt and "geopolitics" in nt:
        return _claim80("Academic cooperation is shaped by geopolitical and epistemic inequalities")
    # If the source exposes no usable abstract and no safe rewrite applies, retain a
    # specific title fragment rather than inventing a generic Europe-wide slogan.
    return _claim80(t)

def relevance_note(evidence: dict[str, Any], strand: str) -> str:
    eu = (evidence.get("eu_relevance") or "unknown").capitalize()
    if strand == "A":
        ri = ", ".join(evidence.get("ri_evidence", [])[:2]) or "substantive R&I evidence"
        geo = ", ".join(evidence.get("geo_evidence", [])[:2]) or "substantive strategic evidence"
        bridge = evidence.get("bridge_mode") or "supported"
        eu_scope = ", ".join(evidence.get("eu_evidence", [])[:2]) or "scope established"
        if evidence.get('eu_relevance') == 'material_external':
            return f"Major external R&I shock with a specific Europe-impact bridge ({eu_scope}); R&I evidence: {ri}; strategic context: {geo}; bridge is a radar inference."
        return f"{eu} EU relevance ({eu_scope}); R&I evidence: {ri}; strategic evidence: {geo}; bridge: {bridge}."
    if strand == "B":
        method = ", ".join(evidence.get("method_evidence", [])[:2]) or "substantive foresight method"
        suitable = ', '.join(evidence.get('b_suitability_evidence', [])[:2]) or 'strategic/public-policy futures'
        return f"Method contribution for understanding the future of Strand A ({method}); suitable context: {suitable}."
    return f"Qualifies independently as Strand A evidence and as a Strand B future-method contribution ({eu} EU scope for A)."


def build_item(*, title: str, authors: str, source: str, date: dt.date, link: str,
               item_type: str, strand: str, evidence: dict[str, Any], source_rank: float,
               tier_label: str, text: str, doi: str, preprint: bool,
               frontier_targets: Iterable[str] | None = None) -> dict[str, Any]:
    themes = themes_for(text)
    summary = make_summary(text, evidence, strand, title, frontier_targets)
    extracted_claim = concise_core_message(text, title)
    return {
        "title": title,
        "authors": authors,
        "source": source,
        "date": date.isoformat(),
        "link": link,
        "type": item_type,
        "strand": strand,
        "eu_relevance": evidence.get("eu_relevance"),
        "summary": summary,
        "core_message": plain_language_claim(text or summary, title, extracted_claim),
        "relevance_note": relevance_note(evidence, strand),
        "source_tier": tier_label,
        "a_route": evidence.get("a_route", ""),
        "bridge_sentence": evidence.get("bridge_sentence", ""),
        "external_eu_bridge": evidence.get("external_eu_bridge", ""),
        "external_eu_bridge_is_inference": bool(evidence.get("external_eu_bridge_is_inference")),
        "eu_evidence": evidence.get("eu_evidence", []),
        "ri_evidence": evidence.get("ri_evidence", []),
        "geo_evidence": evidence.get("geo_evidence", []),
        "text_mode": evidence.get("text_mode", ""),
        "_source_rank": source_rank,
        "_themes": themes,
        "_doi": normalized(doi).replace("https://doi.org/", ""),
        "_preprint": preprint,
        "_frontier_targets": list(dict.fromkeys(frontier_targets or [])),
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
            "methodology_first": bool(evidence.get("b_methodology_first")),
            "b_route": evidence.get("b_route", ""),
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


def genuinely_new_ab_candidates(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return unique gate-passing A/B candidates not already present in the saved corpus.

    Low-yield decisions must be based on actual potential admissions, not raw API hits,
    duplicates, or records already known to the radar.
    """
    candidates = dedupe_candidates([x for x in items if isinstance(x, dict) and x.get("strand") in {"A", "B", "both"}])
    out: list[dict[str, Any]] = []
    for item in candidates:
        if identity(item) in KNOWN_AB_IDENTITIES:
            continue
        link = normalized_link(item.get("link", ""))
        if link and link in KNOWN_AB_LINKS:
            continue
        out.append(item)
    return out


def major_eu_ri_priority_score(item: dict[str, Any]) -> int:
    """Priority, not admission: surface major EU R&I/geopolitical competition first.

    Saved summaries can contain noisy references/comparators, so the title carries most of
    the score. Summary/relevance text only adds small support when the title already shows
    a European or strategic R&I connection.
    """
    if not isinstance(item, dict):
        return -99
    title = normalized(str(item.get("title", "")))
    support = normalized(" ".join(str(item.get(k, "")) for k in ("summary", "relevance_note")))
    eu_t = bool(has_eu_word(title) or contains_any(title, EU_DIRECT + EU_GENERIC) or bounded_matches(title, MEMBER_STATE_SCOPE))
    system_t = bool(distinct_matches(title, A_MAJOR_RI_SYSTEM))
    tech_t = bool(distinct_matches(title, A_MAJOR_TECH_DOMAINS))
    geo_t = bool(distinct_matches(title, GEO_STRONG + GEO_ACTORS)) or contains_any(title, [
        "economic security", "strategic autonomy", "technology sovereignty", "technological sovereignty",
        "de-risk", "derisk", "export control", "investment screening", "geoeconomic", "techno-national",
        "geopolit", "strategic competition", "dependency", "dependence"
    ])
    score = (4 if eu_t else 0) + (5 if system_t else 0) + (4 if tech_t else 0) + (5 if geo_t else 0)
    if eu_t and (system_t or tech_t) and geo_t:
        score += 6
    # Limited supporting evidence: never let a noisy abstract/reference list manufacture
    # a high-priority paper whose title is unrelated to Europe or strategic R&I.
    if eu_t or geo_t or system_t:
        if distinct_matches(support, A_MAJOR_RI_SYSTEM): score += 2
        if distinct_matches(support, A_MAJOR_TECH_DOMAINS): score += 1
        if distinct_matches(support, GEO_STRONG): score += 2
    if normalized(item.get("a_route", "")) == "external-strategic-shock":
        score += 12
    if normalized(item.get("strand", "")) == "b":
        if distinct_matches(title + " " + support, B_STRATEGIC_RI_RELEVANCE): score += 4
        if _method_matches(title, B_METHOD_FAMILIES): score += 4
    if distinct_matches(title, A_OFFTOPIC_CONSUMER_OR_LOCAL): score -= 10
    if distinct_matches(title, B_OFFTOPIC_APPLICATION_DOMAINS): score -= 5
    tier = normalized(item.get("source_tier", ""))
    if "tier 1" in tier: score += 3
    elif "comparable" in tier: score += 1
    return score


def rank_candidate(item: dict[str, Any]):
    if not isinstance(item, dict):
        return (99, 9, 9.0, 0, 0)
    priority = major_eu_ri_priority_score(item)
    eu = 0 if item.get("eu_relevance") == "direct" else 1
    d = parse_date(item.get("date")) or dt.date.min
    return (-priority, eu, float(item.get("_source_rank", 9.0)), -d.toordinal(), -int(item.get("_confidence", 0)))


def public_item(item: dict[str, Any], *, new_this_scan: bool = False, first_seen: str | None = None) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    out = {
        k: v for k, v in item.items()
        if not k.startswith("_") and not k.startswith("priority_watch") and k != "priority_context_fallback"
    }
    title = clean_text(out.get("title") or out.get("headline") or "")
    if out.get("headline"):
        detail = clean_text(out.get("summary") or out.get("signal_note") or out.get("why_it_matters") or "")
        prior = clean_text(out.get("core_message") or out.get("what") or out.get("headline") or "")
        out["core_message"] = plain_language_claim(detail, title, prior)
    else:
        prior = clean_text(out.get("core_message") or concise_core_message(out.get("summary", ""), title))
        out["core_message"] = plain_language_claim(out.get("summary", ""), title, prior)
    out["new_this_scan"] = bool(new_this_scan)
    if first_seen:
        out["first_seen"] = first_seen
    return out


def normalize_reader_claims(data: dict[str, Any]) -> dict[str, Any]:
    """Apply the plain-language write boundary to every published corpus collection.

    Bibliographic/source fields are intentionally never changed here.  This catches records
    arriving through the normal scanner, manual ingestion, recovery/frontier lanes, or a
    future insertion path that appends directly to one of the published corpus arrays.
    """
    if not isinstance(data, dict):
        return data
    for key in ("strand_a", "strand_b", "strand_c", "frontier_evidence"):
        items = data.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            title = clean_text(item.get("title") or item.get("headline") or "")
            detail = clean_text(
                item.get("summary") or item.get("signal_note") or item.get("why_it_matters") or ""
            )
            prior = clean_text(item.get("core_message") or item.get("what") or "")
            claim = plain_language_claim(detail, title, prior)
            if claim:
                item["core_message"] = claim
                if key == "strand_c" and item.get("what") is not None:
                    item["what"] = claim
            else:
                item.pop("core_message", None)
                if key == "strand_c" and item.get("what") is not None:
                    item.pop("what", None)
    data["display_claim_profile_version"] = str(
        CONFIG.get("display_claim_profile_version", "v17.13.2-explicit-subject-120-char")
    )
    return data


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
    candidate with the largest saved A/B/C corpus, breaking ties by recency.
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
                    f"({before} -> {_saved_corpus_size(clean)} saved A/B/C rows).",
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


def _saved_item_passes(item: dict[str, Any], pass_key: str, *, title: str | None = None,
                       abstract: str | None = None, body: str = "") -> tuple[bool, dict[str, Any]]:
    """Apply the current admission rules to a saved A/B record.

    This is intentionally the same substantive gate used for newly discovered material.
    The first-run inherited-corpus audit can supplement thin saved summaries with freshly
    retrieved document text, but later scans never re-audit the accumulated corpus.
    """
    t = clean_text(item.get("title", "")) if title is None else clean_text(title)
    a = clean_text(item.get("summary", "")) if abstract is None else clean_text(abstract)
    link = clean_text(item.get("link", ""))
    # V17.8.1: source tier is a confidence/ranking input, never a blanket deletion rule.
    # A broad journal can contain directly relevant EU R&I/geopolitical evidence.
    if not t or document_exclusion_reason(t, a, link):
        return False, {}
    ev = gate_scope(t, a, clean_text(body), _saved_tier(item), source_kind=_saved_source_kind(item))
    return bool(ev.get(pass_key)), ev


def revalidate_saved_ab(previous: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    """Offline form of the one-time inherited A/B audit.

    It uses only the evidence already saved in radar.json.  ``audit_inherited_ab`` wraps
    this logic for the real first scanner run and may refresh failed records from their
    DOI/URL before deciding to remove them. Strand C is intentionally untouched.
    """
    out = dict(previous) if isinstance(previous, dict) else {}
    removed = {"strand_a": 0, "strand_b": 0}
    for strand_key, pass_key in (("strand_a", "a_pass"), ("strand_b", "b_pass")):
        kept = []
        for item in out.get(strand_key, []) if isinstance(out.get(strand_key), list) else []:
            if not isinstance(item, dict):
                continue
            passed, _ = _saved_item_passes(item, pass_key)
            if passed:
                kept.append(item)
            else:
                removed[strand_key] += 1
        out[strand_key] = kept
    return out, removed


def surgical_precision_cleanup(previous: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    """Remove only high-confidence legacy contamination at a quality-profile migration.

    V17.13.24 deliberately avoids re-running shortened saved summaries through the whole
    admission gate. It removes only records that violate the new non-negotiable invariants:
    inference-only external relevance, non-English/non-Latin publications, or a small set of
    unmistakable off-topic legacy artefacts.
    """
    out = dict(previous) if isinstance(previous, dict) else {}
    stats = {"strand_a_removed": 0, "strand_b_removed": 0, "stored_pass": 0, "refreshed_pass": 0, "refresh_unavailable": 0}
    unmistakable_noise = [
        'table tennis', 'basketball smart teaching', 'hospitality branding',
        'scenario-based financial planning in gold mining', 'educational administrative framework in nigeria'
    ]
    legacy_high_confidence_contamination = {
        normalized(x) for x in [
            'INTELLECTUAL PROPERTY GOVERNANCE IN THE AGE OF ARTIFICIAL INTELLIGENCE: REGULATORY FRAGMENTATION AND THE TRANSFORMATION OF DIGITAL AUTHORI',
            'Global Cybersecurity Governance: Challenges in Harmonizing International Cyber Laws',
            'The AI Implementation Gap: Policy–Audit Misalignment in the UAE and Egypt',
            'From Human Oversight to Cognitive Sovereignty: A Process-Based Governance Standard for AI-Assisted Legal Reasoning',
            'The Strategic Role of Artificial Intelligence Technologies in Advancing the Digital Economy',
            'DFAS-M&A: A Governance Doctrine for Ethical, Explainable, and Sovereign-Sensitive AI Governance in Mergers and Acquisitions',
            'Digital instruments of monetary and prudential policy in ensuring the cybersecurity of the financial space',
            'AI-Enabled Drug Discovery Platforms: Navigating the Confluence of Software, Medical Device, and Pharmaceutical Regulation in Sino-African Trade Relations',
            'Military AI and Intellectual Property Rights: Global Norms, International Treaties, and Emerging Legal Challenges',
            'Rethinking Patent Monopolies in the Age of Artificial Intelligence: Protection, Dysfunction, and the Case for Structural Reform',
            'Health Governance Review Volume 31, Issue 3: Evidence synthesis for health governance',
            'Sustaining the Future City Hub: Startup Ecosystem Governance in Jakarta–Berlin Sister City Paradiplomacy',
            'Detecting FIMI: A methodological framework for testing OSINT tools in TTPs detection',
            'AUKUS and the Nuclear-Free Norm in Southeast Asia: A Constructivist Analysis of ASEAN Responses (2023-2025)',
            'INTELLECTUAL SERVICES IN UKRAINE’S EXPORT MODEL: DYNAMICS, STRUCTURAL SHIFTS, AND INTERNATIONAL POSITIONING',
            'Governing Trust in Times of Disruption: Institutional Governance for Civic Resilience',
            'Integrating CBDCs into the Global Financial Architecture: Strategic Perspectives, Systemic Risks and Regulatory Constraints',
            'Reimagining paediatric care: technology, trust, and the global movement for child-centred innovation',
            'Cultural sustainability and civic society',
            'AGRICULTURAL MARKET INFRASTRUCTURE AND MARKETING AND LOGISTICS ACTIVITIES OF EXPORT-ORIENTED ENTERPRISES',
            'PATENT TROLLING: THE NATURE OF THE PHENOMENON, MECHANISMS OF INFLUENCE ON THE INNOVATIVE DEVELOPMENT OF TECHNOLOGY COMPANIES, AND COUNTERMEASURES',
            'Digital identity as payments infrastructure : Foundations, evolution, and research directions',
            'Comparative assessment of strategic resilience of integration blocs amid global economic fragmentation',
            'Legal Regulation of Genetically Modified Organisms in Agriculture: Risks and Opportunities for Food Security',
            'Statisticians at the Forefront of Health Technology Assessment: Aligning Regulatory and HTA Evidence Through Transdisciplinary Collaboration',
        ]
    }
    for strand_key in ("strand_a", "strand_b"):
        kept = []
        for item in out.get(strand_key, []) if isinstance(out.get(strand_key), list) else []:
            if not isinstance(item, dict):
                continue
            title = clean_text(item.get("title", ""))
            text = normalized(f"{title} {clean_text(item.get('summary', ''))}")
            hard_noise = False
            if not title:
                hard_noise = True
            elif normalized(item.get("a_route", "")) == "external-strategic-shock" or bool(item.get("external_eu_bridge_is_inference")):
                hard_noise = True
            elif not english_public_item_ok(item):
                hard_noise = True
            elif normalized(title) in legacy_high_confidence_contamination:
                hard_noise = True
            elif any(x in text for x in unmistakable_noise):
                hard_noise = True
            if hard_noise:
                stats[strand_key + "_removed"] += 1
            else:
                saved = dict(item)
                saved["new_this_scan"] = False
                kept.append(saved)
                stats["stored_pass"] += 1
        out[strand_key] = kept
    return out, stats

def cleanup_quality_profile_regressions(previous: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    """Target only records created by the two regressions corrected in V17.5.10.

    Do not re-audit the entire cumulative corpus from concise saved summaries: older
    legitimate records can have thinner summaries than the original abstract/body. The
    targeted migration removes (a) derived-EU Strand-B records that no longer satisfy the
    tightened R&I foresight-transfer route and (b) Strand-A records admitted solely through
    the old broad ``China + strategic`` shortcut when saved evidence lacks visible EU scope and fails the corrected A gate.
    """
    out = dict(previous) if isinstance(previous, dict) else {}
    removed = {"strand_a": 0, "strand_b": 0, "stored_pass": 0, "refreshed_pass": 0, "refresh_unavailable": 0}

    kept_a = []
    for item in out.get("strand_a", []) if isinstance(out.get("strand_a"), list) else []:
        if not isinstance(item, dict):
            continue
        note = normalized(item.get("relevance_note", ""))
        text = clean_text(f"{item.get('title','')} {item.get('summary','')}")
        old_china_bridge = "china + security/strategic context" in note
        visible_eu_scope = bool(
            has_eu_word(text)
            or contains_any(text, EU_DIRECT + EU_GENERIC)
            or bounded_matches(text, MEMBER_STATE_SCOPE)
        )
        # V17.5.5-era false positives often combined an incidental China mention with a
        # generic strategic word and separately inferred EU scope from a passing European
        # comparator.  If the saved evidence cannot visibly establish any EU/member-state
        # scope, re-run only this known regression class under the repaired gate.
        if old_china_bridge and not visible_eu_scope:
            passed, _ = _saved_item_passes(item, "a_pass")
            if not passed:
                removed["strand_a"] += 1
                continue
        kept_a.append(item)
        removed["stored_pass"] += 1

    kept_b = []
    for item in out.get("strand_b", []) if isinstance(out.get("strand_b"), list) else []:
        if not isinstance(item, dict):
            continue
        derived_transfer = normalized(item.get("eu_relevance", "")) == "derived"
        if derived_transfer:
            passed, _ = _saved_item_passes(item, "b_pass")
            if not passed:
                removed["strand_b"] += 1
                continue
        kept_b.append(item)
        removed["stored_pass"] += 1

    out["strand_a"] = kept_a
    out["strand_b"] = kept_b
    return out, removed


def _audit_refresh_document(item: dict[str, Any]) -> tuple[str, str, str] | None:
    """Best-effort evidence refresh for one inherited record.

    Returns ``(title, abstract/description, body)``. This is used only during the first
    inherited-corpus audit; it is never part of the normal recurring scan path.
    """
    link = clean_text(item.get("link", ""))
    if not link or deadline_reached(int(CONFIG.get("network_reserve_seconds", 90))):
        return None
    timeout = int(CONFIG.get("inherited_corpus_audit_timeout_seconds", 8))

    # Scholarly DOI records often expose a better abstract through Crossref than through
    # the publisher landing page, so try that first.
    m = re.search(r"10\.\d{4,9}/[^\s?#]+", normalized(link))
    if m:
        doi = m.group(0).rstrip(".,)")
        r = get(f"https://api.crossref.org/works/{quote_plus(doi)}", timeout=timeout)
        if r:
            try:
                msg = (r.json() or {}).get("message") or {}
                title = clean_text((msg.get("title") or [item.get("title", "")])[0])
                abstract = clean_text(msg.get("abstract"))
                if title and abstract:
                    return title, abstract, ""
            except Exception:
                pass

    # Then read the linked page/PDF itself. The audit only needs enough document-level
    # text to run the admission gate; it does not rebuild the whole record.
    if link.lower().split("?", 1)[0].endswith(".pdf"):
        body, words = pdf_text(link)
        if words:
            return clean_text(item.get("title", "")), "", body
        return None

    r = get(link, timeout=timeout)
    if not r:
        return None
    ctype = normalized(r.headers.get("content-type", ""))
    if "pdf" in ctype:
        body, words = pdf_text(r.url or link)
        if words:
            return clean_text(item.get("title", "")), "", body
        return None
    if "html" not in ctype and "xml" not in ctype:
        return None
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        title = (meta_content(soup, ["og:title", "twitter:title", "headline"]) or
                 clean_text(soup.h1.get_text(" ", strip=True) if soup.h1 else "") or
                 clean_text(item.get("title", "")))
        desc = meta_content(soup, ["description", "og:description", "twitter:description"])
        for bad in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
            bad.decompose()
        container = soup.find("article") or soup.find("main") or soup.body
        body = clean_text(container.get_text(" ", strip=True) if container else "")
        return title, desc, body
    except Exception:
        return None


def audit_inherited_ab(previous: dict[str, Any], warnings: list[str] | None = None) -> tuple[dict[str, Any], dict[str, int]]:
    """Audit saved A/B at an explicit quality-migration boundary.

    Saved evidence that already passes is retained immediately. A saved record that fails
    gets one best-effort document/abstract refresh so thin historical summaries do not
    create needless false negatives. If refresh is unavailable, fail-closed behavior is
    configurable; the default is strict because this migration exists to remove inherited
    false positives. Strand C is handled separately by its own one-time weak-signal cleanup.
    """
    out = dict(previous) if isinstance(previous, dict) else {}
    stats = {
        "strand_a_removed": 0, "strand_b_removed": 0,
        "stored_pass": 0, "refreshed_pass": 0, "refresh_unavailable": 0,
    }
    jobs: list[tuple[str, str, dict[str, Any]]] = []
    keepers: dict[str, list[dict[str, Any]]] = {"strand_a": [], "strand_b": []}

    for strand_key, pass_key in (("strand_a", "a_pass"), ("strand_b", "b_pass")):
        for item in out.get(strand_key, []) if isinstance(out.get(strand_key), list) else []:
            if not isinstance(item, dict):
                continue
            passed, _ = _saved_item_passes(item, pass_key)
            if passed:
                keepers[strand_key].append(item)
                stats["stored_pass"] += 1
            else:
                jobs.append((strand_key, pass_key, item))

    refresh_results: dict[int, tuple[str, str, str] | None] = {}
    if INHERITED_CORPUS_AUDIT_REFRESH and jobs:
        workers = max(1, int(CONFIG.get("inherited_corpus_audit_workers", 8)))
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_audit_refresh_document, item): i for i, (_, _, item) in enumerate(jobs)}
            for fut in cf.as_completed(futs):
                i = futs[fut]
                try:
                    refresh_results[i] = fut.result()
                except Exception:
                    refresh_results[i] = None

    for i, (strand_key, pass_key, item) in enumerate(jobs):
        refreshed = refresh_results.get(i)
        if refreshed:
            title, abstract, body = refreshed
            passed, ev = _saved_item_passes(item, pass_key, title=title, abstract=abstract, body=body)
            if passed:
                saved = dict(item)
                # Keep the original display summary, but refresh the explanation so the
                # retained legacy item records why it survives the new gate.
                strand = "A" if strand_key == "strand_a" else "B"
                saved["eu_relevance"] = ev.get("eu_relevance") or saved.get("eu_relevance")
                saved["relevance_note"] = relevance_note(ev, strand)
                keepers[strand_key].append(saved)
                stats["refreshed_pass"] += 1
                continue
        else:
            stats["refresh_unavailable"] += 1
            # "Insufficient text" is a defer state, not a substantive rejection. Never
            # destroy a live saved record solely because the network could not refresh it.
            _, deferred_ev = _saved_item_passes(item, pass_key)
            if deferred_ev.get("aboutness_reason") == "insufficient_text" or not INHERITED_CORPUS_AUDIT_FAIL_CLOSED:
                keepers[strand_key].append(item)
                continue

        key = "strand_a_removed" if strand_key == "strand_a" else "strand_b_removed"
        stats[key] += 1

    out["strand_a"] = keepers["strand_a"]
    out["strand_b"] = keepers["strand_b"]
    if warnings is not None and stats["refresh_unavailable"]:
        warnings.append(
            f"Inherited-corpus audit could not refresh {stats['refresh_unavailable']} failed saved record(s); "
            + "deferred records were retained; substantive hard failures may still be removed"
        )
    return out, stats


def merge_corpus(previous: list[dict[str, Any]], new_items: list[dict[str, Any]], strand_name: str, now_iso: str) -> list[dict[str, Any]]:
    """Merge admitted A/B items without deleting earlier accepted material.

    A rediscovered item is refreshed but is not labelled NEW again.  MAX_CORPUS is
    an optional safety cap; 0 means unlimited, which is the default for this build.
    """
    merged: dict[str, dict[str, Any]] = {}
    for old in previous:
        if not isinstance(old, dict) or signal_is_retired(old) or not english_public_item_ok(old):
            continue
        internal = internalize_previous(old)
        key = identity(internal)
        if key == "title:":
            continue
        internal["new_this_scan"] = False
        merged[key] = internal
    new_ids: set[str] = set()
    for item in new_items:
        if not isinstance(item, dict) or signal_is_retired(item) or not english_public_item_ok(item):
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



def canonical_signal_headline(value: str) -> str:
    """Normalise syndication/source suffixes so one event is not stored many times."""
    h = clean_text(value)
    h = re.sub(r'\s+[–—-]\s+(?:euronews\.com|euractiv\.com|ft\.com|politico\.eu|reuters|bloomberg|le monde\.fr|nikkei asia)\s*$', '', h, flags=re.I)
    h = re.sub(r'\s+[–—-]\s+company announcement\s*$', '', h, flags=re.I)
    return norm_title(h)


def _signal_tokens(value: str) -> set[str]:
    # Event-level normalisation: syndicators often paraphrase the same event as
    # "officially joins" / "formally joins ... as associated country".
    # Strip presentation words and collapse a few event morphology variants before
    # computing overlap. This remains deliberately conservative for unrelated stories.
    stop = {
        'the','and','for','with','from','into','over','under','a','an','to','of','in','on','as','is','are',
        'eu','europe','european','new','officially','formally','official','research','programme','program',
        'country','countries','member','members',
    }
    stems = {
        'joins':'join','joined':'join','joining':'join',
        'association':'associate','associated':'associate','associates':'associate',
        'launches':'launch','launched':'launch','launching':'launch',
        'partners':'partner','partnered':'partner','partnering':'partner',
        'delays':'delay','delayed':'delay','postponed':'delay','postpones':'delay',
        'expands':'expand','expanded':'expand','expanding':'expand',
    }
    out=set()
    for t in re.findall(r'[a-z0-9][a-z0-9-]{2,}', canonical_signal_headline(value)):
        if t in stop:
            continue
        out.add(stems.get(t,t))
    return out


def _signal_text_similarity(a: str, b: str) -> tuple[float, float, int]:
    ta, tb = _signal_tokens(a), _signal_tokens(b)
    if not ta or not tb:
        return 0.0, 0.0, 0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / max(1, union), inter / max(1, min(len(ta), len(tb))), inter


def signals_near_duplicate(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Collapse only substantially the same event/claim/implication.

    Strand C is allowed to revisit an established A topic whenever a new fact changes
    the interpretation.  Earlier versions used topic-heavy headline overlap and could
    erase a distinct point merely because both headlines said, for example, Europe +
    AI + compute.  Exact URLs still collapse immediately; otherwise both the headline
    and the substantive point must be very close.
    """
    la = normalized(a.get('link', ''))
    lb = normalized(b.get('link', ''))
    if la and lb and la == lb:
        return True

    hj, hc, hi = _signal_text_similarity(a.get('headline',''), b.get('headline',''))
    point_a = clean_text(a.get('what') or a.get('core_message') or a.get('signal_note') or a.get('_desc',''))
    point_b = clean_text(b.get('what') or b.get('core_message') or b.get('signal_note') or b.get('_desc',''))
    pj, pc, pi = _signal_text_similarity(point_a, point_b)

    # Near-identical syndication remains one signal.  Merely sharing a topic does not.
    if hj >= 0.90 or (hi >= 7 and hc >= 0.96):
        return not point_a or not point_b or pj >= 0.42 or pc >= 0.70
    return bool(hj >= 0.76 and hc >= 0.86 and pj >= 0.66 and pc >= 0.82 and pi >= 5)


def signal_identity(item: dict[str, Any]) -> str:
    """Stable event-level identity for Strand C, independent of publisher syndication."""
    if not isinstance(item, dict):
        return 'signal-link:'
    headline = canonical_signal_headline(item.get('headline', ''))
    if headline:
        return f'signal:{headline}'
    link = normalized(item.get('link', ''))
    return f'signal-link:{link}'



# V17.12.10: curator-directed weak-signal retirements.
# These tombstones are intentionally separate from automated quality migration.
MANUALLY_RETIRED_SIGNAL_HEADLINES = [
    "Prizes and related events",
    "Galaxy evolution and neutral hydrogen - ITU",
    "News | ELLIS Institute Finland",
    "News and events | Aalto University",
    "Prestigious Faraday Medal acknowledges circular economy trailblazer Mari Lundström | Aalto University",
    "Why data centers are a top issue in the 2026 midterms | Brookings",
    "Canada-Japan Funding Fuels Xanadu and Mitsubishi Chemical Partnership on Quantum Semiconductor Research",
    "Cosmology from the Moon in a radio-quiet environment - ITU",
    "Biological AI models: new paradigms to leverage the languages of life",
    "GÉANT and CERNET strengthen Europe-China academic collaboration with tenfold increase in interconnection capacity",
    "US widens AI-driven investment gap with Europe",
    "FirstFT: Europe trails as AI drives US investment",
    "Postdoc and doctoral student positions at ELLIS Institute Finland | ELLIS Institute Finland",
    "Flash report - General Working Group of the Health Security Committee Meeting (12 August 2026)",
    "China’s self-driving push gears up in Europe as Momenta, Pony.ai expand",
    "Japan's Rakuten to partner with German AI defense drone startup",
    "EU's first quantum tech regulation delayed by six months - euractiv.com",
    "EU-China research cooperation limited to ‘targeted areas’",
    "Funding Radar: G7 and Nordics jointly fund quantum research",
    "International educational project at Aalto University funded by the TFK Programme | Aalto University",
    "EU to co-fund seven AI Gigafactories in race for tech autonomy",
    "EU launches AI Gigafactories call to boost Europe's computing capacity and unlock more than €30 billion in investment - Shaping Europe’s digital future"
]

def _retired_signal_headlines(data: dict[str, Any] | None = None) -> set[str]:
    retired = {clean_text(x) for x in MANUALLY_RETIRED_SIGNAL_HEADLINES if clean_text(x)}
    if isinstance(data, dict):
        stored = data.get("retired_signal_headlines")
        if isinstance(stored, list):
            for x in stored:
                if clean_text(x):
                    retired.add(clean_text(x))
    return retired

def signal_is_retired(item: dict[str, Any], data: dict[str, Any] | None = None) -> bool:
    if not isinstance(item, dict):
        return False
    return clean_text(item.get("headline", "")) in _retired_signal_headlines(data)

def apply_retired_signal_filter(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    if not isinstance(data, dict):
        return {}, 0
    out = dict(data)
    retired = _retired_signal_headlines(out)
    raw = out.get("strand_c") if isinstance(out.get("strand_c"), list) else []
    kept = [
        dict(item) for item in raw
        if isinstance(item, dict) and clean_text(item.get("headline", "")) not in retired
    ]
    removed = len(raw) - len(kept)
    out["strand_c"] = kept
    out["retired_signal_headlines"] = sorted(retired)
    return out, removed

def merge_signal_corpus(previous: list[dict[str, Any]], new_items: list[dict[str, Any]], now_iso: str) -> list[dict[str, Any]]:
    """Keep cumulative C while collapsing repeated coverage of the same weak signal."""
    merged: list[dict[str, Any]] = []
    for old in previous:
        if not isinstance(old, dict) or signal_is_retired(old) or not english_public_item_ok(old):
            continue
        x = _low_evidence_signal(old)
        x['new_this_scan'] = False
        if any(signals_near_duplicate(x, y) for y in merged):
            continue
        merged.append(x)

    new_ids: set[str] = set()
    for item in new_items:
        if not isinstance(item, dict) or signal_is_retired(item) or not english_public_item_ok(item):
            continue
        if any(signals_near_duplicate(item, y) for y in merged):
            continue
        x = _low_evidence_signal(item)
        x['first_seen'] = x.get('first_seen') or now_iso
        x['new_this_scan'] = True
        new_ids.add(signal_identity(x))
        merged.append(x)

    merged.sort(key=lambda x: str(x.get('date','')), reverse=True)
    merged.sort(key=lambda x: not bool(x.get('new_this_scan')))
    if MAX_CORPUS > 0:
        merged = merged[:MAX_CORPUS]
    return [public_item(x, new_this_scan=signal_identity(x) in new_ids, first_seen=x.get('first_seen')) for x in merged]

def _saved_signal_passes(item: dict[str, Any]) -> bool:
    """Surgical saved-C precision gate.

    Direct European signals remain eligible. Non-European developments may remain only when
    they concern a narrow strategic R&I mechanism that can materially change Europe's
    relative capability/access and still anchor to Strand A. Generated Europe boilerplate
    is never enough on its own.
    """
    if not isinstance(item, dict):
        return False
    headline = clean_text(item.get('headline', ''))
    if not headline:
        return False
    desc = clean_text(item.get('signal_note', '') or item.get('why_it_matters', ''))
    if not english_record_ok(f"{headline}. {desc}", item.get('language', ''), title=headline):
        return False
    if '(strand b)' in normalized(item.get('anchor', '')) or normalized(item.get('anchor_basis', '')) == 'watch-theme':
        return False
    h = normalized(headline)
    if contains_any(h, [
        'table tennis', 'school ai councils', 'student agency', 'drug prices', 'rural america',
        'genocide', 'fiscal, ai, or monetary news', 'crypto firm', 'taiwan? the view from taipei'
    ]):
        return False
    if eu_news_scope(h):
        return factual_news(headline, desc)
    external_specific = contains_any(h, [
        'export control', 'semiconductor', 'advanced chip', 'compute', 'quantum',
        'research cooperation', 'research collaboration', 'research security', 'research talent',
        'scientific collaboration', 'critical raw material', 'critical mineral', 'ai investment gap'
    ])
    if not external_specific:
        return False
    return factual_news(headline, desc)


def revalidate_saved_c(previous: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    """Rebuild historical C under the A-only weak-signal relationship."""
    out=dict(previous) if isinstance(previous,dict) else {}
    raw=[]
    for item in out.get('strand_c',[]) if isinstance(out.get('strand_c'),list) else []:
        if not _saved_signal_passes(item):
            continue
        x=dict(item)
        desc=clean_text(x.get('signal_note','') or x.get('why_it_matters',''))
        text=f"{x.get('headline','')} {desc}"
        x['_desc']=desc
        x['_themes']=themes_for(text)
        x['_entities']=distinct_matches(text, ENTITY_TERMS+GEO_ACTORS)
        raw.append(x)
    rebuilt=anchor_news(raw, out.get('strand_a',[]) if isinstance(out.get('strand_a'),list) else [])
    # Preserve historical first_seen where event identity matches.
    old_by_id={signal_identity(x):x for x in out.get('strand_c',[]) if isinstance(x,dict)}
    for x in rebuilt:
        old=old_by_id.get(signal_identity(x))
        if old and old.get('first_seen'):
            x['first_seen']=old['first_seen']
        x['new_this_scan']=False
    old_count=len(out.get('strand_c',[]) if isinstance(out.get('strand_c'),list) else [])
    out['strand_c']=rebuilt
    return out, {'strand_c_removed':max(0,old_count-len(rebuilt)),'strand_c_kept':len(rebuilt)}

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


def _ontology_variants(row: dict[str, Any]) -> list[str]:
    phrase = clean_text(row.get("phrase"))
    rule = clean_text(row.get("match_rule"))
    vals = [phrase] if phrase else []
    # Curator workbook expresses common safe variants in quoted text after "also".
    for v in re.findall(r"['‘]([^'’]{2,80})['’]", rule):
        v = clean_text(v)
        if v and v not in vals:
            vals.append(v)
    return vals


def _ontology_phrase_present(text: str, row: dict[str, Any]) -> bool:
    """Conservative phrase matcher for the curator workbook.

    These rules are used for discovery/linkage only here. They never bypass the normal
    A/B substantive gates, and Strand-C rows never admit a signal on their own.
    """
    rule = clean_text(row.get("match_rule")).lower()
    case_sensitive = "case-sensitive" in rule or "case sensitive" in rule
    for phrase in _ontology_variants(row):
        hay = clean_text(text) if case_sensitive else normalized(text)
        needle = clean_text(phrase) if case_sensitive else normalized(phrase)
        if not needle:
            continue
        if "word boundar" in rule or (len(needle) <= 6 and re.fullmatch(r"[A-Za-z0-9&.-]+", needle)):
            flags = 0 if case_sensitive else re.I
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(clean_text(phrase)) + r"(?![A-Za-z0-9])", clean_text(text), flags=flags):
                return True
        elif needle in hay:
            return True
    return False


def ontology_phrase_hits(text: str, strand: str = "a", tiers: set[int] | None = None) -> list[dict[str, Any]]:
    key = {"a": "strand_a", "b": "strand_b", "c": "strand_c_retrieval"}.get(strand.lower(), strand)
    rows = PHRASE_RULES.get(key, []) if isinstance(PHRASE_RULES, dict) else []
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        try:
            tier = int(row.get("tier", 3))
        except Exception:
            tier = 3
        if tiers is not None and tier not in tiers:
            continue
        if _ontology_phrase_present(text, row):
            out.append(row)
    return out


def relationship_novelty_dimensions(text: str) -> list[str]:
    """Describe how a current fact could put an existing Strand-A issue in new light.

    A weak signal does not need a new topic. It needs a distinct new point: evidence,
    actor, magnitude, mechanism, timing, direction, consequence or geography.
    """
    full = normalized(text)
    dims: list[str] = []
    if contains_any(full, REFRAMING_SIGNAL_EVIDENCE + REFRAMING_SIGNAL_FINDINGS):
        dims.append("new evidence")
    if contains_any(full, ["announce", "launch", "sign", "partner", "acquire", "invest", "fund", "open", "build", "restrict", "ban", "approve", "adopt", "withdraw", "join", "propose", "plan", "pilot", "trial", "test", "seek"]):
        dims.append("new actor move")
    if re.search(r"(?:€|\$|£)\s?\d|\b\d+(?:[.,]\d+)?\s?(?:%|billion|million|bn|mn|gw|mw|petaflop|exaflop)", full) or contains_any(full, ["gap", "surge", "record", "doubl", "tripl", "increase", "decrease", "share of", "overtake", "outpace"]):
        dims.append("new magnitude")
    if contains_any(full, ["because", "due to", "driven by", "bottleneck", "constraint", "grid", "electricity", "licensing", "export control", "supply chain", "access to", "shortage", "dependency"]):
        dims.append("new mechanism")
    if contains_any(full, ["delay", "postpone", "accelerat", "fast-track", "deadline", "by 202", "earlier than", "later than", "months", "years"]):
        dims.append("new timing")
    if contains_any(full, ["expand", "scale", "cut", "decline", "fall", "rise", "tighten", "loosen", "suspend", "reverse", "shift", "relocat", "outflow", "inflow"]):
        dims.append("new direction")
    if contains_any(full, ["impact", "affect", "means", "could leave", "risk", "enable", "undermine", "strengthen", "weaken", "depend", "competitiveness", "capacity"]):
        dims.append("new consequence")
    return list(dict.fromkeys(dims))


def relational_signal_candidate_text(title: str, desc: str = "") -> bool:
    """Broad discovery gate for a possible new point on an existing A issue.

    This deliberately does *not* require novelty-of-topic wording. Final C admission still
    requires a substantive Strand-A anchor in ``anchor_news``.
    """
    if routine_signal_noise(title, desc):
        return False
    full = normalized(f"{title} {desc}")
    if not any(x in full for x in NEWS_EVENT_TERMS):
        return False
    ri = contains_any(full, MATERIAL_SIGNAL_RI)
    strategic = contains_any(full, MATERIAL_SIGNAL_STAKES) or bool(set(themes_for(full)) & WATCH_SIGNAL_THEMES)
    ontology = bool(ontology_phrase_hits(full, "a", {1, 2}))
    return bool((ri and strategic) and (relationship_novelty_dimensions(full) or ontology))


def strong_watch_signal_text(text: str, themes: Iterable[str] | None = None) -> bool:
    """Balanced Strand-C topical gate with an A-anchored derived-Europe evidence route.

    Ordinary event signals remain EU/European/member-state first. New empirical evidence may be
    global/comparative when it is explicitly about R&I/science/technology and strategic competition,
    because the later A-anchor step is what establishes why it changes the European interpretation.
    """
    full = normalized(text)
    found = set(themes or themes_for(full)) & WATCH_SIGNAL_THEMES
    if not found:
        return False

    core_ri = contains_any(full, [
        "research and innovation", "research & innovation", "research", "science",
        "scientific", "innovation", "r&d", "researcher", "researchers",
        "research talent", "horizon europe", "fp10", "european research area",
        "research security", "science diplomacy", "research cooperation",
        "scientific cooperation", "research funding", "research programme",
        "research program", "university research", "academic research", "technology",
        "technological", "semiconductor", "quantum", "biotech", "biomanufacturing",
        "compute", "neuromorphic", "risc-v", "open-weight model", "open weights",
        "quantum error correction", "photonic interconnect",
    ])
    geo = contains_any(full, GEO_STRONG)
    actors = bool(distinct_matches(full, GEO_ACTORS))
    strategic_frame = geo or actors or contains_any(full, [
        "sovereignty", "sovereign", "strategic autonomy", "competitiveness",
        "catch up", "dependency", "dependencies", "market fragmentation",
        "supply chain", "economic security", "de-risk", "derisk", "defence", "defense",
    ])

    eu_scope = eu_news_scope(full)
    if not eu_scope:
        # V17.8.1: external developments are allowed only through a narrow materiality
        # route. This keeps export-control/compute/quantum/research-system shocks that can
        # change Europe's relative position, while blocking generic foreign AI, health,
        # education, politics and consumer-sector stories. A specific A anchor is still
        # mandatory later in the pipeline.
        derived_themes = {
            "fragmentation of global science", "transatlantic / US–China S&T competition",
            "export controls / dual use", "critical and emerging technologies",
            "R&I competitiveness / technological capabilities", "supply chains / strategic dependencies",
            "economic security and R&I",
        }
        narrow_external = contains_any(full, [
            'export control', 'semiconductor', 'advanced chip', 'compute infrastructure', 'compute access',
            'quantum', 'research cooperation', 'research collaboration', 'research security',
            'research talent', 'scientific collaboration', 'critical raw material', 'critical mineral',
            'ai investment gap', 'frontier ai compute'
        ])
        hard_noise = contains_any(full, [
            'table tennis', 'school ai councils', 'student agency', 'drug prices', 'rural america',
            'genocide', 'crypto firm', 'monetary news', 'hospitality', 'sports equipment'
        ])
        external_shock, _, _ = external_eu_bridge_sentence(full)
        ontology_bridge = bool(ontology_phrase_hits(full, "a", {1, 2}))
        relational_external = relational_signal_candidate_text(full, "")
        if hard_noise or not (
            external_shock
            or (narrow_external and (reframing_signal_text(full) or material_update_signal_text(full)) and strategic_frame and (found & derived_themes))
            # Curator ontology can widen *discovery* beyond the old hard-coded tech list,
            # but only for a factual R&I/strategic update. A concrete Strand-A publication
            # anchor is still mandatory later, so a spreadsheet phrase never admits C alone.
            or (ontology_bridge and relational_external and strategic_frame and core_ri and (found & derived_themes))
        ):
            return False
        if external_shock:
            return True

    # International research cooperation/mobility is itself a valid geopolitical channel.
    if core_ri and (strategic_frame or bool(found & {
        "EU–China S&T cooperation / de-risking",
        "Horizon Europe / FP10 international participation",
        "research security / foreign interference",
        "science diplomacy",
        "research talent / mobility / brain drain",
    })):
        return True

    critical_tech = contains_any(full, [
        "artificial intelligence", " ai ", "semiconductor", "semiconductors", "chips",
        "quantum", "biotech", "biotechnology", "supercomputer", "cloud",
        "critical technology", "critical technologies", "biomanufacturing", "neuromorphic",
        "risc-v", "open-weight model", "open weights", "quantum error correction",
        "photonic interconnect",
    ])
    narrow_capacity_tech = contains_any(full, [
        "semiconductor", "semiconductors", "chips", "quantum", "supercomputer",
        "ai factory", "ai factories", "gigafactory", "gigafactories",
        "data centre", "data center", "critical raw materials", "critical minerals",
    ])
    capacity_or_policy_move = contains_any(full, [
        "launch", "invest", "fund", "funding", "factory", "facility", "build", "open",
        "expand", "scale", "strategy", "regulation", "rules", "code", "standard",
        "partner", "partnership", "association", "join", "market fragmentation",
        "control layer", "infrastructure",
    ])
    if eu_scope and narrow_capacity_tech and capacity_or_policy_move:
        return True
    return bool(eu_scope and critical_tech and strategic_frame and capacity_or_policy_move)



REFRAMING_SIGNAL_EVIDENCE = [
    'new data', 'latest data', 'new evidence', 'dataset', 'survey', 'study', 'research finds',
    'report finds', 'report shows', 'analysis finds', 'evidence', 'patent data', 'patent filings',
    'publication data', 'citation data', 'bibliometric', 'scientometric', 'scoreboard', 'benchmark',
    'ranking', 'index', 'figures show', 'data show', 'data shows',
]
REFRAMING_SIGNAL_FINDINGS = [
    'finds', 'found', 'shows', 'showed', 'reveals', 'revealed', 'suggests', 'suggested',
    'indicates', 'indicated', 'points to', 'documents', 'records', 'reports', 'estimates',
]
REFRAMING_SIGNAL_SHIFTS = [
    'gap', 'lead', 'leads', 'lag', 'lags', 'catch up', 'overtake', 'outpace', 'surge', 'rise', 'rises',
    'fall', 'falls', 'decline', 'drop', 'shift', 'diverge', 'concentration', 'dependency', 'dependence',
    'bottleneck', 'shortage', 'outflow', 'inflow', 'brain drain', 'brain gain', 'fragmentation',
    'slows', 'slowdown', 'accelerates', 'trajectory', 'share of', 'accounts for',
]


def reframing_signal_text(text: str) -> bool:
    """Detect new evidence that can strengthen, weaken or complicate the Strand-A picture.

    This is intentionally narrower than accepting any report or study. Evidence language must be
    paired with a finding/measurement or a directional shift. EU relevance and A anchoring are
    enforced separately, so this widens interpretive recall without turning C into a news feed.
    """
    full = normalized(text)
    evidence = contains_any(full, REFRAMING_SIGNAL_EVIDENCE)
    finding = contains_any(full, REFRAMING_SIGNAL_FINDINGS)
    shift = contains_any(full, REFRAMING_SIGNAL_SHIFTS)
    explicit_new = contains_any(full, ['new data', 'latest data', 'new evidence', 'new survey', 'new study'])
    return bool((evidence and (finding or shift)) or (explicit_new and shift))


MATERIAL_SIGNAL_CHANGE = [
    'announce', 'launch', 'approve', 'adopt', 'propose', 'restrict', 'tighten', 'ban',
    'suspend', 'delay', 'cancel', 'withdraw', 'sign', 'agree', 'partner', 'fund', 'invest',
    'open', 'close', 'build', 'expand', 'scale', 'cut', 'increase', 'decrease', 'join',
    'screening', 'export control', 'standard', 'regulation', 'strategy', 'programme', 'program',
    'acquisition', 'relocat', 'outflow', 'inflow', 'shortage', 'bottleneck', 'dependency',
]
MATERIAL_SIGNAL_RI = [
    'research', 'science', 'scientific', 'innovation', 'r&d', 'researcher', 'researchers',
    'university', 'horizon europe', 'fp10', 'technology', 'semiconductor', 'chips', 'quantum',
    'biotech', 'artificial intelligence', ' ai ', 'compute', 'cloud', 'data centre', 'data center',
    'critical raw materials', 'critical minerals', 'deep tech', 'patent', 'standards',
    'biomanufacturing', 'fermentation capacity', 'neuromorphic', 'risc-v', 'open-weight model',
    'open weights', 'quantum error correction', 'photonic interconnect', 'critical technology list',
]
MATERIAL_SIGNAL_STAKES = [
    'strategic', 'security', 'sovereignty', 'autonomy', 'competitiveness', 'capacity', 'capability',
    'dependence', 'dependency', 'supply chain', 'collaboration', 'cooperation', 'talent', 'mobility',
    'funding', 'investment', 'access', 'export', 'foreign', 'china', 'united states', 'u.s.', ' us ',
]

def material_update_signal_text(text: str) -> bool:
    """Current factual changes that can update an A claim even if they are not 'early'.

    Strand C is interpretive evidence, not only pilots and drafts. The later A-anchor
    gate remains mandatory, so this route can admit consequential policy/capability
    moves without turning C into a general technology-news feed. Generic analytical
    framings such as "building resilience" are not themselves an event.
    """
    full = normalized(text)
    if contains_any(full, [
        'building resilience', 'building research resilience', 'building capacity',
        'building capabilities', 'building competitiveness', 'building sovereignty',
    ]) and not contains_any(full, [
        'announce', 'launch', 'approve', 'adopt', 'propose', 'restrict', 'tighten', 'ban',
        'suspend', 'delay', 'cancel', 'withdraw', 'sign', 'agree', 'partner', 'fund', 'invest',
        'open', 'close', 'expand', 'scale', 'cut', 'increase', 'decrease', 'join',
        'export control', 'regulation', 'programme', 'program', 'acquisition', 'relocat',
        'outflow', 'inflow', 'shortage', 'bottleneck', 'dependency',
    ]):
        return False
    return bool(
        contains_any(full, MATERIAL_SIGNAL_CHANGE)
        and contains_any(full, MATERIAL_SIGNAL_RI)
        and contains_any(full, MATERIAL_SIGNAL_STAKES)
    )


WEAK_SIGNAL_MARKERS = [
    'pilot', 'trial', 'prototype', 'first to', 'first european', 'first eu', 'first national',
    'early-stage', 'early stage', 'emerging', 'experiment', 'testbed', 'limited to', 'targeted areas',
    'targeted cooperation', 'draft', 'proposal', 'proposes', 'proposed', 'consultation', 'explores',
    'considering', 'mulls', 'seeks', 'new partnership', 'partnership with', 'memorandum', 'mou',
    'startup', 'start-up', 'new entrant', 'delay', 'delayed', 'postpone', 'postponed', 'pause',
    'exception', 'waiver', 'does not include', "doesn't include", 'declines to', 'opts out',
    'gears up', 'begins testing', 'starts testing', 'expands into', 'quietly', 'small-scale',
]
MATURE_SIGNAL_MARKERS = [
    'officially joins', 'formally joins', 'enters into force', 'entered into force',
    'final regulation', 'adopts the regulation', 'adopted the regulation', 'approved the law',
    'signed the association agreement', 'full-scale rollout', 'nationwide rollout',
    'commits €', 'commits $', 'commits £',
]


def weak_signal_candidate_text(title: str, desc: str = '') -> bool:
    """Discovery gate for C: new point, not necessarily a new topic.

    Early indicators and reframing evidence still qualify, but so does an otherwise
    ordinary factual development when it can alter magnitude, mechanism, actor, timing,
    direction or consequence for a strategic R&I issue. Final admission remains relational
    and requires a substantive Strand-A publication anchor.
    """
    if routine_signal_noise(title, desc):
        return False
    full = normalized(f'{title} {desc}')
    early = contains_any(full, WEAK_SIGNAL_MARKERS)
    reframing = reframing_signal_text(full)
    material = material_update_signal_text(full)
    relational = relational_signal_candidate_text(title, desc)
    if not (early or reframing or material or relational):
        return False
    # Mature implementation is normally not a weak signal. New evidence/indicators are a separate
    # interpretive route, and counter-signals such as delays/opt-outs remain valid early signals.
    mature = contains_any(full, MATURE_SIGNAL_MARKERS)
    counter = contains_any(full, ['delay','delayed','postpone','pause','exception','waiver','limited to','targeted','opts out','declines to','does not include',"doesn't include"])
    # A material strategic move remains useful as a current signal even after formal
    # adoption/commitment.  Earlier code first recognised ``material`` and then
    # immediately rejected mature implementation, which systematically hid major-media
    # stories about EU capacity, funding, controls and infrastructure.  The material
    # route is still strict: it independently requires a concrete change + R&I object +
    # strategic stake, and ``anchor_news`` still requires a substantive Strand-A anchor.
    if mature and not counter and not reframing and not material and not relational:
        return False
    return True

def factual_news(title: str, desc: str) -> bool:
    if routine_signal_noise(title, desc):
        return False
    full = normalized(f'{title} {desc}')
    # Keep opinion/commentary exclusions, but do not discard a labelled news-analysis item
    # when it contains genuine new evidence/indicators. This is a common packaging label at
    # high-quality outlets and was unnecessarily hiding useful Strand-A reframing evidence.
    analysis_labels = {'analysis:', 'analysis -'}
    if any(x in full for x in NEWS_EXCLUDE if x not in analysis_labels):
        return False
    if any(x in full for x in analysis_labels) and not reframing_signal_text(full):
        return False
    # Opinion/advocacy headlines are not factual weak signals unless they report an
    # identifiable actor taking an action.
    if re.search(r'\bshould\b', normalized(title)) and not contains_any(full, ['says','said','calls for','urges','proposes']):
        return False
    if not any(x in full for x in NEWS_EVENT_TERMS):
        return False
    if not weak_signal_candidate_text(title, desc):
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
        f'site:{domain} (study OR report OR survey OR data OR evidence OR patents OR publications) (finds OR shows OR reveals OR suggests OR gap OR rise OR fall OR shift OR outflow OR inflow) (research OR science OR innovation OR technology OR researchers) (EU OR Europe OR European) {when}',
    ]


def global_news_queries(lookback_hours: int) -> list[str]:
    days = max(2, min(30, (int(lookback_hours) + 23) // 24))
    when = f"when:{days}d"
    base = [f"{q} {when}" for q in CONFIG.get("news_global_queries", []) if clean_text(q)]

    # Curator Strand-C phrases are retrieval seeds only. They widen what the news lane
    # notices (RISC-V, neuromorphic, biomanufacturing, etc.); they do not bypass the
    # factual-news, strategic-R&I or substantive Strand-A anchor gates.
    c_rows = PHRASE_RULES.get("strand_c_retrieval", []) if isinstance(PHRASE_RULES, dict) else []
    distinctive: list[str] = []
    for row in c_rows if isinstance(c_rows, list) else []:
        if not isinstance(row, dict):
            continue
        try:
            tier = int(row.get("tier", 3))
        except Exception:
            tier = 3
        phrase = clean_text(row.get("phrase"))
        if tier == 1 and phrase and phrase.lower() not in {"suspension of cooperation", "withdrawal from the programme"}:
            distinctive.append(phrase)
    ontology_queries = [
        f'("{p}") (Europe OR European OR EU) (research OR technology OR innovation OR strategic OR capacity OR security) {when}'
        for p in distinctive[:8]
    ]
    return list(dict.fromkeys(base + ontology_queries))


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


def collect_news(now: dt.datetime, warnings: list[str], lookback_hours: int | None = None, stage_deadline: float | None = None, coverage_queries: list[str] | None = None, include_base_queries: bool = True) -> list[dict[str, Any]]:
    lookback_hours = int(lookback_hours or NEWS_LOOKBACK_HOURS)
    start = now - dt.timedelta(hours=lookback_hours)
    workers = int(CONFIG.get("news_workers", 10))
    timeout = int(CONFIG.get("news_timeout_seconds", 10))
    per_feed = int(CONFIG.get("news_items_per_feed", 60))
    jobs: list[tuple[str, str, str, bool]] = []
    if include_base_queries:
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
            raw_desc = getattr(e, "summary", "") or getattr(e, "description", "")
            desc = clean_text(raw_desc)
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
                "_desc_html": str(raw_desc or ""),
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


_SIGNAL_EVIDENCE_CUES = [
    "study", "report", "paper", "working paper", "policy brief", "research", "researchers",
    "analysis", "survey", "dataset", "data show", "data shows", "findings", "evidence",
    "published", "publication", "journal", "preprint", "according to", "new data", "new research",
]
_SIGNAL_LINK_CUES = [
    "study", "report", "paper", "research", "analysis", "survey", "dataset", "publication",
    "working paper", "policy brief", "briefing", "preprint", "full text", "download", "doi",
]
_SIGNAL_LINK_EXCLUDE_DOMAINS = {
    "facebook.com", "x.com", "twitter.com", "linkedin.com", "instagram.com", "youtube.com",
    "youtu.be", "tiktok.com", "mailto", "wa.me", "whatsapp.com",
}


def signal_indicates_underlying_evidence(item: dict[str, Any]) -> bool:
    """Whether a C lead plausibly points beyond itself to stronger evidence."""
    if not isinstance(item, dict):
        return False
    title = clean_text(item.get("headline") or item.get("title"))
    detail = clean_text(item.get("_desc") or item.get("signal_note") or item.get("what") or item.get("why_it_matters"))
    text = clean_text(f"{title}. {detail}")
    if not text:
        return False
    themes = set(item.get("_themes") or themes_for(text)) & WATCH_SIGNAL_THEMES
    if not themes:
        return False
    # The follow-up lane is for research/report clues, not for every policy announcement.
    cue = contains_any(normalized(text), _SIGNAL_EVIDENCE_CUES)
    return bool(cue and weak_signal_candidate_text(title, detail) and strong_watch_signal_text(text, themes))


def _signal_followup_due(item: dict[str, Any], state: dict[str, Any], now: dt.datetime) -> bool:
    sid = signal_identity(item)
    hist = state.get("weak_signal_evidence_followup") if isinstance(state.get("weak_signal_evidence_followup"), dict) else {}
    rec = hist.get(sid) if isinstance(hist, dict) else None
    if not isinstance(rec, dict) or not rec.get("checked_at"):
        return True
    try:
        checked = dateparser.parse(str(rec.get("checked_at")))
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=dt.timezone.utc)
        days = max(1, int(CONFIG.get("weak_signal_evidence_followup_recheck_days", 21) or 21))
        return now - checked >= dt.timedelta(days=days)
    except Exception:
        return True


def _research_link_score(url: str, label: str) -> int:
    u = clean_text(url)
    if not u.startswith(("http://", "https://")):
        return -100
    try:
        domain = (urlparse(u).hostname or "").lower().removeprefix("www.")
    except Exception:
        return -100
    if not domain or any(domain == d or domain.endswith("." + d) for d in _SIGNAL_LINK_EXCLUDE_DOMAINS):
        return -100
    low_u = normalized(u)
    low_l = normalized(label)
    score = 0
    if domain == "doi.org" or domain.endswith(".doi.org"):
        score += 12
    if ".pdf" in low_u or low_u.endswith("/pdf"):
        score += 8
    if any(c in low_l for c in _SIGNAL_LINK_CUES):
        score += 6
    if any(c.replace(" ", "-") in low_u or c.replace(" ", "_") in low_u for c in _SIGNAL_LINK_CUES):
        score += 4
    if any(x in domain for x in ["arxiv.org", "ssrn.com", "zenodo.org", "researchsquare.com", "openreview.net"]):
        score += 5
    if any(x in low_u for x in ["/publication", "/publications", "/report", "/reports", "/paper", "/papers", "/research", "/study", "/studies"]):
        score += 3
    if low_l in {"read more", "more", "home", "homepage", "source", "website"}:
        score -= 4
    return score


def _extract_signal_research_links(item: dict[str, Any], stage_deadline: float | None = None) -> list[tuple[str, str]]:
    """Fetch a signal page and rank links that look like underlying research/report evidence."""
    candidates: dict[str, tuple[int, str, str]] = {}

    def add(url: str, label: str = "") -> None:
        u = clean_text(url)
        if not u:
            return
        score = _research_link_score(u, label)
        if score < 4:
            return
        key = normalized_link(u)
        if key in KNOWN_AB_LINKS:
            return
        old = candidates.get(key)
        if old is None or score > old[0]:
            candidates[key] = (score, u, clean_text(label))

    raw_html = item.get("_desc_html")
    if raw_html:
        try:
            soup = BeautifulSoup(str(raw_html), "html.parser")
            for a in soup.find_all("a", href=True):
                add(a.get("href", ""), a.get_text(" ", strip=True))
        except Exception:
            pass

    page_url = clean_text(item.get("link"))
    if page_url and page_url.startswith(("http://", "https://")) and not stage_deadline_reached(stage_deadline, 15):
        try:
            r = SESSION.get(page_url, timeout=min(12, int(CONFIG.get("institution_page_timeout_seconds", 12) or 12)), allow_redirects=True)
            if r.status_code == 200 and "html" in r.headers.get("content-type", "text/html").lower():
                soup = BeautifulSoup(r.text, "html.parser")
                base = r.url
                # A redirect that already left an aggregator is useful as the signal page,
                # but is not automatically treated as the stronger source.
                for a in soup.find_all("a", href=True):
                    href = urljoin(base, a.get("href", ""))
                    if normalized_link(href) == normalized_link(page_url):
                        continue
                    add(href, a.get_text(" ", strip=True))
        except Exception:
            pass

    ranked = sorted(((v[0], v[1], v[2]) for v in candidates.values()), reverse=True)
    cap = max(1, int(CONFIG.get("weak_signal_evidence_followup_links_per_signal", 5) or 5))
    return [(url, label) for _, url, label in ranked[:cap]]


def _known_source_for_url(url: str) -> tuple[str, int]:
    try:
        domain = (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        domain = ""
    for src in CONFIG.get("institution_sources", []):
        sd = clean_text(src.get("domain", "")).lower().removeprefix("www.")
        if sd and (domain == sd or domain.endswith("." + sd)):
            return clean_text(src.get("name")) or domain, int(src.get("tier", 3) or 3)
    return domain or "Linked publication", 3


def _explicit_date_from_text(text: str) -> dt.date | None:
    head = clean_text(text)[:3500]
    patterns = [
        r"\b(20\d{2}-[01]?\d-[0-3]?\d)\b",
        r"\b([0-3]?\d\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2})\b",
        r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+[0-3]?\d,?\s+20\d{2})\b",
    ]
    for pat in patterns:
        m = re.search(pat, head, re.I)
        if m:
            d = parse_date(m.group(1))
            if d:
                return d
    return None


def _linked_pdf_candidate(url: str, label: str, stage_deadline: float | None = None) -> dict[str, Any] | None:
    if stage_deadline_reached(stage_deadline, 15):
        return None
    try:
        r = SESSION.get(url, timeout=int(CONFIG.get("pdf_timeout_seconds", 14) or 14))
        if r.status_code != 200 or len(r.content) > 22_000_000:
            return None
        reader = PdfReader(io.BytesIO(r.content))
        texts = []
        for page in reader.pages[:55]:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                pass
        body = clean_text(" ".join(texts))
        if len(body.split()) < 120:
            return None
        meta = reader.metadata or {}
        meta_title = clean_text(getattr(meta, "title", "") or (meta.get("/Title") if hasattr(meta, "get") else ""))
        title = clean_text(label)
        if len(title.split()) < 4 or normalized(title) in {"pdf", "download", "download report", "download paper", "full text"}:
            title = meta_title
        if len(title.split()) < 4:
            return None
        published = None
        for raw in [getattr(meta, "creation_date", None), getattr(meta, "modification_date", None)]:
            published = parse_date(raw)
            if published:
                break
        published = published or _explicit_date_from_text(body)
        today = dt.datetime.now(dt.timezone.utc).date()
        if not published or published < EXTENDED_DATE_FLOOR or published > today + dt.timedelta(days=1):
            return None
        source, tier = _known_source_for_url(r.url or url)
        ev = gate_scope(title, "", body, tier, source_kind="institutional")
        _record_ab_gate_diagnostic("signal-linked-pdf", ev)
        if not (ev.get("a_pass") or ev.get("b_pass")):
            return None
        strand = "both" if ev.get("a_pass") and ev.get("b_pass") else "A" if ev.get("a_pass") else "B"
        return build_item(
            title=title, authors=source, source=source, date=published, link=r.url or url,
            item_type="linked report / paper", strand=strand, evidence=ev,
            source_rank=float(tier), tier_label=f"Tier {tier}", text=body, doi="", preprint=False,
        )
    except Exception:
        return None


def _linked_doi_candidate(url: str, stage_deadline: float | None = None) -> dict[str, Any] | None:
    if stage_deadline_reached(stage_deadline, 15):
        return None
    try:
        parsed = urlparse(url)
        if (parsed.hostname or "").lower().removeprefix("www.") != "doi.org":
            return None
        doi = parsed.path.lstrip("/")
        if not doi:
            return None
        r = SESSION.get("https://api.crossref.org/works/" + quote_plus(doi, safe="/()"), timeout=int(CONFIG.get("scholarly_api_timeout_seconds", 12) or 12))
        if r.status_code != 200:
            return None
        raw = (r.json().get("message") or {})
        return candidate_from_crossref(raw, date_floor=EXTENDED_DATE_FLOOR)
    except Exception:
        return None


def _linked_publication_candidate(url: str, label: str, stage_deadline: float | None = None) -> dict[str, Any] | None:
    try:
        domain = (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        domain = ""
    if domain == "doi.org":
        return _linked_doi_candidate(url, stage_deadline)
    if ".pdf" in normalized(url) or normalized(url).endswith("/pdf"):
        return _linked_pdf_candidate(url, label, stage_deadline)
    source, tier = _known_source_for_url(url)
    return parse_institution_page(url, source, tier, stage_deadline=stage_deadline, publication_floor=EXTENDED_DATE_FLOOR)


def _signal_evidence_query(item: dict[str, Any]) -> str:
    headline = clean_text(item.get("headline") or item.get("title"))
    detail = clean_text(item.get("_desc") or item.get("signal_note") or item.get("what"))
    evidence_sentence = ""
    for sent in split_sentences(detail, max_chars=3000):
        if contains_any(normalized(sent), _SIGNAL_EVIDENCE_CUES):
            evidence_sentence = sent
            break
    q = clean_text(f"{headline} {evidence_sentence}")
    words = q.split()
    return " ".join(words[:36])



def _signal_followup_related_candidate(candidate: dict[str, Any], signals: list[dict[str, Any]]) -> bool:
    """Keep scholarly follow-up results tied to at least one triggering C lead."""
    if not isinstance(candidate, dict):
        return False
    ctext = clean_text(f"{candidate.get('title','')} {candidate.get('summary','')} {candidate.get('relevance_note','')}")
    ctok = tokens(ctext)
    cthemes = set(themes_for(ctext))
    centities = set(distinct_matches(ctext, ENTITY_TERMS + GEO_ACTORS))
    for sig in signals:
        stext = clean_text(f"{sig.get('headline','')} {sig.get('_desc','')} {sig.get('signal_note','')} {sig.get('what','')}")
        stok = tokens(stext)
        if not stok or not ctok:
            continue
        shared_themes = cthemes & set(sig.get('_themes') or themes_for(stext))
        if not shared_themes:
            continue
        inter = len(stok & ctok)
        jacc = inter / max(1, len(stok | ctok))
        sentities = set(sig.get('_entities') or distinct_matches(stext, ENTITY_TERMS + GEO_ACTORS))
        entity_overlap = bool(centities & sentities)
        # The signal query may use different wording than the publication title, so a
        # modest lexical overlap plus the same watch theme is enough; named-entity overlap
        # provides a second route for terse titles.
        if jacc >= 0.035 or (inter >= 4 and entity_overlap) or (entity_overlap and len(shared_themes) >= 2):
            return True
    return False

def collect_weak_signal_evidence_followups(
    new_signals: list[dict[str, Any]],
    previous_signals: list[dict[str, Any]],
    state: dict[str, Any],
    warnings: list[str],
    now: dt.datetime,
    stage_deadline: float | None = None,
    openalex_allowed: bool = True,
    crossref_allowed: bool = True,
    stats: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Use interesting C items as bounded leads to independent A/B evidence.

    A C item never changes evidential status. We only follow explicit research/report clues,
    inspect likely outbound evidence links, and run a few targeted scholarly searches. Any
    stronger record must independently pass the normal A/B admission gate and is stored as a
    separate publication.
    """
    stats = stats if isinstance(stats, dict) else {}
    stats.update({"signals_checked": 0, "links_examined": 0, "direct_ab": 0, "queries": 0, "scholarly_ab": 0})
    if not bool(CONFIG.get("weak_signal_evidence_followup_enabled", True)):
        return []
    hist = state.setdefault("weak_signal_evidence_followup", {})
    if not isinstance(hist, dict):
        hist = {}
        state["weak_signal_evidence_followup"] = hist
    pool: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in list(new_signals) + list(previous_signals):
        if not isinstance(item, dict):
            continue
        sid = signal_identity(item)
        if sid in seen or not signal_indicates_underlying_evidence(item) or not _signal_followup_due(item, state, now):
            continue
        seen.add(sid)
        pool.append(item)
    cap = max(0, int(CONFIG.get("weak_signal_evidence_followup_per_scan", 6) or 0))
    pool = pool[:cap]
    out: list[dict[str, Any]] = []
    queries: list[str] = []
    now_iso = now.isoformat(timespec="minutes").replace("+00:00", "Z")
    for item in pool:
        if stage_deadline_reached(stage_deadline, 20):
            break
        sid = signal_identity(item)
        direct_before = len(out)
        links = _extract_signal_research_links(item, stage_deadline)
        stats["signals_checked"] += 1
        stats["links_examined"] += len(links)
        for url, label in links:
            if stage_deadline_reached(stage_deadline, 18):
                break
            cand = _linked_publication_candidate(url, label, stage_deadline)
            if cand and identity(cand) not in KNOWN_AB_IDENTITIES:
                out.append(cand)
        q = _signal_evidence_query(item)
        if q and q not in queries:
            queries.append(q)
        hist[sid] = {
            "checked_at": now_iso,
            "links_examined": len(links),
            "direct_candidates": max(0, len(out) - direct_before),
        }
    stats["direct_ab"] = len(out)

    qcap = max(0, int(CONFIG.get("weak_signal_evidence_followup_queries_per_scan", 4) or 0))
    queries = queries[:qcap]
    stats["queries"] = len(queries)
    if queries and not stage_deadline_reached(stage_deadline, 28) and (openalex_allowed or crossref_allowed):
        dates = {q: EXTENDED_DATE_FLOOR for q in queries}
        lanes = {q: "signal-evidence" for q in queries}
        exec_stats: dict[str, Any] = {}
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            futs: list[tuple[str, Any]] = []
            if openalex_allowed:
                futs.append(("oa", ex.submit(
                    collect_openalex, EXTENDED_DATE_FLOOR, warnings, queries, stage_deadline,
                    dates, {}, lanes, exec_stats, False
                )))
            if crossref_allowed:
                futs.append(("cr", ex.submit(
                    collect_crossref, EXTENDED_DATE_FLOOR, warnings, queries, [], [], stage_deadline,
                    dates, {}, {}, lanes, exec_stats, False
                )))
            scholarly: list[dict[str, Any]] = []
            for _, fut in futs:
                try:
                    scholarly.extend(x for x in fut.result() if isinstance(x, dict))
                except Exception as e:
                    warnings.append(f"Weak-signal evidence scholarly follow-up: {type(e).__name__}")
        scholarly = [x for x in scholarly if _signal_followup_related_candidate(x, pool)]
        scholarly = dedupe_candidates(scholarly)
        stats["scholarly_ab"] = len(scholarly)
        out.extend(scholarly)
    if len(hist) > 1200:
        newest = sorted(
            ((k, v) for k, v in hist.items() if isinstance(v, dict)),
            key=lambda kv: clean_text(kv[1].get("checked_at")), reverse=True
        )[:1200]
        state["weak_signal_evidence_followup"] = dict(newest)
    return dedupe_candidates(out)


def signal_relation(text: str) -> str:
    low = normalized(text)
    if any(w in low for w in ["stall", "delay", "cancel", "scrap", "reverse", "withdraw", "fail", "collapse", "reject", "block", "cut"]):
        return "contradicts"
    if reframing_signal_text(low) and contains_any(low, ["gap", "lag", "diverge", "shift", "concentration", "dependency", "dependence", "bottleneck", "shortage", "outflow", "brain drain", "fragmentation", "slowdown"]):
        return "reframes"
    if any(w in low for w in ["accelerat", "expand", "surge", "increase", "boost", "fast-track", "scale up", "intensif", "invest", "fund"]):
        return "accelerates"
    if reframing_signal_text(low) or any(w in low for w in ["dataset", "data show", "survey", "finds", "evidence", "shows", "rise", "fall", "measur"]):
        return "confirms"
    return "instantiates"


def signal_kind(text: str) -> str:
    low = normalized(text)
    if reframing_signal_text(low):
        return "evidence / indicator"
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
        "research talent / mobility / brain drain": "This can change Europe's ability to attract, retain and circulate researchers, with direct effects on research capacity and competitiveness.",
    }
    base = explanations.get(theme, f"This is a current {kind} development with a plausible effect on Europe's research, innovation or strategic technology position.")
    if kind == 'evidence / indicator':
        return "This is new evidence that may strengthen, weaken or complicate the current Strand-A picture. " + base
    return base


def anchor_news(news: list[dict[str, Any]], a_corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Anchor C only to substantive Strand-A evidence.

    B is a methods library and must never serve as the substantive claim that a weak
    signal updates. A signal must anchor to a concrete A publication; broad recurring
    themes alone are not sufficient.
    """
    internals = [internalize_previous(x) for x in a_corpus if isinstance(x, dict)]
    internals = [x for x in internals if identity(x) != 'title:']
    theme_counts = Counter(t for x in internals for t in x.get('_themes', []))
    recurring = {t for t,c in theme_counts.items() if c >= 2}
    anchored=[]
    for n in news:
        if not english_record_ok(f"{n.get('headline','')}. {n.get('_desc','')}", n.get('language',''), title=clean_text(n.get('headline',''))):
            continue
        if not weak_signal_candidate_text(n.get('headline',''), n.get('_desc','')):
            continue
        ntext=n.get('headline','')+' '+n.get('_desc','')
        nthemes=set(n.get('_themes',[])) & WATCH_SIGNAL_THEMES
        if not nthemes:
            continue
        novelty_dimensions=relationship_novelty_dimensions(ntext)
        if not novelty_dimensions:
            continue
        ntok=tokens(ntext)
        nentities=set(n.get('_entities',[]))
        n_a_ontology=ontology_phrase_hits(ntext, 'a', {1,2})
        n_c_retrieval=ontology_phrase_hits(ntext, 'c', {1,2})
        best=None
        for a in internals:
            athemes=set(a.get('_themes',[]))
            shared=nthemes & athemes
            # Named C technologies from the curator workbook are discovery/linkage clues,
            # never admission triggers.  They may connect to an A publication about
            # sovereignty/capability/dependencies even when the exact technology was not
            # named in that older A source.
            ontology_strategic_themes={
                'technology sovereignty / strategic autonomy',
                'R&I competitiveness / technological capabilities',
                'supply chains / strategic dependencies',
                'economic security and R&I',
                'critical and emerging technologies',
                'export controls / dual use',
            }
            ontology_bridge_themes=athemes & ontology_strategic_themes if n_c_retrieval else set()
            if not shared and ontology_bridge_themes:
                shared=set(ontology_bridge_themes)
            if not shared:
                continue
            atok=tokens(a.get('title','')+' '+a.get('summary',''))
            jacc=len(ntok & atok)/max(1,len(ntok | atok))
            aentities=set(distinct_matches(a.get('title','')+' '+a.get('summary',''), ENTITY_TERMS+GEO_ACTORS))
            entity_overlap=len(nentities & aentities)
            broad_themes={
                'critical and emerging technologies',
                'R&I competitiveness / technological capabilities',
                'economic security and R&I',
            }
            broad_only=bool(shared) and shared.issubset(broad_themes)
            # A generic AI/innovation theme is not enough. Broad-theme signals need a
            # concrete shared entity/mechanism and textual overlap with the A source.
            if broad_only and not n_c_retrieval and (entity_overlap==0 or jacc<0.025):
                continue
            score=3.0*len(shared)+1.5*entity_overlap+8.0*jacc
            if n_c_retrieval and ontology_bridge_themes:
                score += 1.75
            if n_a_ontology:
                score += min(1.5, 0.35*len(n_a_ontology))
            if any(t in SPECIFIC_ANCHOR_THEMES for t in shared): score+=1.0
            if best is None or score>best[0]: best=(score,a,sorted(shared))
        anchor=''; score=0.0; shared_themes=[]; anchor_basis=''; external_bridge=''
        if best and best[0] >= 4.0:
            score,a,shared_themes=best
            anchor=f"{a['title']} (Strand A)"
            anchor_basis='publication'
        text=ntext
        # Major external capability shocks get a tightly bounded same-domain fallback. This is
        # not a generic foreign-news route: the helper requires a current EU-context anchor and
        # produces the one-sentence Europe-position implication demanded by the editorial rule.
        if not anchor:
            ext_ok, external_bridge, _ = external_eu_bridge_sentence(text, a_corpus)
            if ext_ok:
                domain = _external_shock_domain(text)
                a = next((x for x in internals if _anchor_supports_external_domain(x, domain)), None)
                if a:
                    anchor=f"{a['title']} (Strand A)"
                    anchor_basis='publication-external-shock-context'
                    shared_themes=sorted(nthemes)[:1]
                    score=4.25
        if not anchor:
            continue
        relation=signal_relation(text)
        kind=signal_kind(text)
        theme=shared_themes[0] if shared_themes else sorted(nthemes)[0]
        source_headline=clean_text(n.get('headline',''))
        what=plain_language_claim(n.get('_desc',''), source_headline, source_headline)
        why=external_bridge or signal_why(theme,kind)
        item={k:v for k,v in n.items() if not k.startswith('_')}
        item.update({
            'anchor':anchor,
            'anchor_basis':anchor_basis,
            'watch_theme':theme,
            'signal_type':relation,
            'signal_kind':kind,
            'what':what,
            'core_message':what,
            'why_it_matters':why,
            'signal_note':what.rstrip('. ')+'. '+why,
            'external_eu_bridge': external_bridge,
            'external_eu_bridge_is_inference': bool(external_bridge),
            # C is a low-evidence early-warning record, never an evidentiary endpoint.
            # Stronger status is represented by a separate A/B report, publication or formal notice.
            'evidence_status': 'low',
            'evidence_role': 'weak_signal',
            'retention_window_months': WEAK_SIGNAL_RETENTION_MONTHS,
            'reframing_dimensions': novelty_dimensions,
            'strand_a_phrase_hits': [clean_text(x.get('phrase')) for x in n_a_ontology[:6]],
            'c_retrieval_phrase_hits': [clean_text(x.get('phrase')) for x in n_c_retrieval[:6]],
            'c_admission_rule': 'new point on a substantive Strand-A issue; topic repetition allowed',
            '_anchor_score':score,
        })
        if any(signals_near_duplicate(item,x) for x in anchored):
            continue
        anchored.append(item)
    anchored.sort(key=lambda x:(x.get('_anchor_score',0),x.get('date','')),reverse=True)
    for x in anchored:x.pop('_anchor_score',None)
    return anchored[:MAX_C] if MAX_C>0 else anchored


# V17.13.23: two-tier evidence window. The normal radar remains a four-month core,
# while only the existing UI's Highest source-merit band may survive/discover in months 4-6.
_SOURCE_MERIT_EU_NAMES = [
    "European Commission", "Council of the European Union", "European Central Bank",
    "European Innovation Council", "European Research Council", "European Investment Bank",
    "EuroHPC Joint Undertaking", "European Union Institute for Security Studies", "EUISS",
    "EFSA Supporting Publications",
]
_SOURCE_MERIT_PUBLIC_HIGH = {
    "OECD", "International Telecommunication Union",
    "National Contact Point for Knowledge Security, Government of the Netherlands",
    "Rathenau Instituut",
}

def _source_merit_domain(link: str) -> str:
    try:
        return (urlparse(clean_text(link)).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""

def _source_merit_is_eu_official(source: str, link: str) -> bool:
    src = clean_text(source).lower()
    domain = _source_merit_domain(link)
    if any(name.lower() in src for name in _SOURCE_MERIT_EU_NAMES):
        return True
    return domain.endswith(".europa.eu") or domain in {"ecb.europa.eu", "consilium.europa.eu", "data.consilium.europa.eu", "op.europa.eu"}

def source_merit_score(item: dict[str, Any]) -> int:
    """Python mirror of source_merit.js for the Highest-band retention decision."""
    if not isinstance(item, dict):
        return 0
    source = clean_text(item.get("source") or item.get("journal") or item.get("institution"))
    link = clean_text(item.get("link") or item.get("url"))
    typ = clean_text(item.get("type") or item.get("itemType") or "").lower()
    rel = clean_text(item.get("eu_relevance") or item.get("euRelevance") or "").lower()
    authors = clean_text(item.get("authors"))
    official = _source_merit_is_eu_official(source, link)
    if official:
        authority = 55
    elif source in _SOURCE_MERIT_PUBLIC_HIGH:
        authority = 48
    else:
        # No lower authority class can reach the UI's Highest threshold (93/100).
        return 0
    if rel == "direct":
        relevance = 25
    elif rel == "material_external":
        relevance = 20
    elif rel == "derived":
        relevance = 18
    elif official:
        relevance = 25
    else:
        relevance = 16
    if official:
        evidence = 15
    elif "peer-reviewed" in typ:
        evidence = 15
    elif "institutional report" in typ:
        evidence = 14
    elif "manual-verified" in typ:
        evidence = 14
    elif "research/policy paper" in typ:
        evidence = 13
    elif "preprint" in typ:
        evidence = 8
    else:
        evidence = 10
    if not authors:
        author_points = 2
    elif re.search(r"commission|council|institute|undertaking|bank|agency|organisation|organization|university|academies", authors, re.I):
        author_points = 4
    else:
        author_points = 5
    return max(0, min(100, authority + relevance + evidence + author_points))

def highest_source_merit(item: dict[str, Any]) -> bool:
    return source_merit_score(item) >= 93

def source_can_reach_highest(src: dict[str, Any]) -> bool:
    if not isinstance(src, dict):
        return False
    source = clean_text(src.get("name"))
    domain = clean_text(src.get("domain")).lower().removeprefix("www.")
    probe = f"https://{domain}/" if domain else ""
    return _source_merit_is_eu_official(source, probe) or source in _SOURCE_MERIT_PUBLIC_HIGH

def enforce_two_tier_ab_window(items: list[dict[str, Any]], preferred_floor: dt.date, extended_floor: dt.date) -> tuple[list[dict[str, Any]], int, int]:
    """Keep all A/B in the core four months and only Highest-merit evidence in months 4-6."""
    kept: list[dict[str, Any]] = []
    removed = 0
    extended_kept = 0
    for raw in items if isinstance(items, list) else []:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        d = parse_date(item.get("date"))
        if not d or d >= preferred_floor:
            item.pop("extended_retention", None)
            item.pop("retention_window_months", None)
            kept.append(item)
            continue
        if d >= extended_floor and highest_source_merit(item):
            item["extended_retention"] = True
            item["retention_window_months"] = EXTENDED_TOP_QUALITY_LOOKBACK_MONTHS
            extended_kept += 1
            kept.append(item)
            continue
        removed += 1
    return kept, removed, extended_kept

def bootstrap_floor(today: dt.date) -> dt.date:
    return today - relativedelta(months=BOOTSTRAP_LOOKBACK_MONTHS)


def preserved_corpus_floor(previous: dict[str, Any], today: dt.date) -> dt.date:
    """Return the preferred/core four-month floor."""
    return bootstrap_floor(today)

def extended_top_quality_floor(today: dt.date) -> dt.date:
    return today - relativedelta(months=EXTENDED_TOP_QUALITY_LOOKBACK_MONTHS)

def weak_signal_retention_floor(today: dt.date) -> dt.date:
    return today - relativedelta(months=WEAK_SIGNAL_RETENTION_MONTHS)

def _low_evidence_signal(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize the public evidentiary contract for Strand C."""
    x = dict(item)
    x["evidence_status"] = "low"
    x["evidence_role"] = "weak_signal"
    x["retention_window_months"] = WEAK_SIGNAL_RETENTION_MONTHS
    return x

def prune_public_window(
    data: dict[str, Any],
    floor: dt.date,
    extended_floor: dt.date | None = None,
    signal_floor: dt.date | None = None,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Apply independent A/B and weak-signal retention windows.

    A/B: four-month core, with only Highest source-merit evidence surviving to six months.
    C: every admitted weak signal survives for six months, but always at low evidential status.
    """
    out = dict(data) if isinstance(data, dict) else {}
    extended_floor = extended_floor or extended_top_quality_floor(dt.date.today())
    signal_floor = signal_floor or weak_signal_retention_floor(dt.date.today())
    removed: dict[str, int] = {}
    for strand in ("strand_a", "strand_b"):
        raw = out.get(strand) if isinstance(out.get(strand), list) else []
        kept, removed_count, _ = enforce_two_tier_ab_window(raw, floor, extended_floor)
        removed[strand] = removed_count
        out[strand] = kept

    raw_c = out.get("strand_c") if isinstance(out.get("strand_c"), list) else []
    kept_c = []
    signal_ceiling = signal_floor + relativedelta(months=WEAK_SIGNAL_RETENTION_MONTHS) + dt.timedelta(days=1)
    for item in raw_c:
        if not isinstance(item, dict):
            continue
        d = parse_date(item.get("date"))
        if d and (d < signal_floor or d > signal_ceiling):
            continue
        kept_c.append(_low_evidence_signal(item))
    removed["strand_c"] = max(0, len(raw_c) - len(kept_c))
    out["strand_c"] = kept_c

    raw_frontier = out.get("frontier_evidence") if isinstance(out.get("frontier_evidence"), list) else []
    kept_frontier = []
    for item in raw_frontier:
        if not isinstance(item, dict):
            continue
        d = parse_date(item.get("date"))
        if d and d < floor:
            continue
        kept_frontier.append(dict(item))
    removed["frontier_evidence"] = max(0, len(raw_frontier) - len(kept_frontier))
    out["frontier_evidence"] = kept_frontier

    # corpus_start_date stays the preferred/core A/B floor for backward-compatible reader logic.
    out["corpus_start_date"] = floor.isoformat()
    out["preferred_corpus_start_date"] = floor.isoformat()
    out["extended_top_quality_start_date"] = extended_floor.isoformat()
    out["weak_signal_retention_start_date"] = signal_floor.isoformat()
    return out, removed

def needs_source_expansion_backfill(previous: dict[str, Any]) -> bool:
    if not FORCE_SOURCE_EXPANSION_BACKFILL:
        return not bool(previous.get("last_updated"))
    if previous.get("source_expansion_version") != SOURCE_EXPANSION_VERSION:
        return True
    return False


def needs_inherited_corpus_audit(previous: dict[str, Any]) -> bool:
    """True only until the legacy A/B corpus has completed its one-time migration."""
    return INHERITED_CORPUS_AUDIT_ENABLED and not bool(previous.get("inherited_corpus_audit_complete"))


def needs_precision_corpus_cleanup(previous: dict[str, Any]) -> bool:
    """Re-audit A/B once whenever the substantive quality profile changes.

    A boolean-only marker could not repair a corpus after a later admission regression:
    repositories that had already completed an older cleanup would preserve newly polluted
    historical A/B forever.  The output quality-profile version is now the migration marker.
    """
    return previous.get("quality_profile_version") != QUALITY_PROFILE_VERSION


def needs_precision_signal_cleanup(previous: dict[str, Any]) -> bool:
    """Re-audit C whenever the weak-signal quality model changes."""
    return previous.get('signal_quality_profile_version') != SIGNAL_QUALITY_PROFILE_VERSION


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
    global DATE_FLOOR, EXTENDED_DATE_FLOOR, SIGNAL_RETENTION_FLOOR, SCAN_DEADLINE_MONO, KNOWN_AB_IDENTITIES, KNOWN_AB_LINKS, KNOWN_SIGNAL_IDENTITIES, INSTITUTION_SEEN_FINGERPRINTS, INSTITUTION_DISCOVERED_DATES, INSTITUTION_SIGNAL_CANDIDATES, SIGNAL_WINDOW_START_DATE, ACTIVE_FRONTIER_GAP_URL_TERMS, ADMISSION_DIAGNOSTICS, ACTIVE_EU_CONTEXT_ANCHORS
    started = time.time()
    log_progress.started = time.monotonic()
    budget_seconds = int(CONFIG.get("scan_budget_seconds", 1200))
    SCAN_DEADLINE_MONO = time.monotonic() + budget_seconds
    now = dt.datetime.now(dt.timezone.utc)
    now_iso = now.isoformat(timespec="minutes").replace("+00:00", "Z")
    warnings: list[str] = []
    INSTITUTION_DISCOVERED_DATES = {}
    INSTITUTION_SIGNAL_CANDIDATES = []
    SIGNAL_WINDOW_START_DATE = None
    with ADMISSION_DIAGNOSTICS_LOCK:
        ADMISSION_DIAGNOSTICS.clear()
    previous = load_previous()
    ACTIVE_EU_CONTEXT_ANCHORS = [dict(x) for x in previous.get('strand_a', []) if isinstance(x, dict)]
    DATE_FLOOR = bootstrap_floor(now.date())
    EXTENDED_DATE_FLOOR = extended_top_quality_floor(now.date())
    SIGNAL_RETENTION_FLOOR = weak_signal_retention_floor(now.date())
    previous, age_window_removed = prune_public_window(previous, DATE_FLOOR, EXTENDED_DATE_FLOOR, SIGNAL_RETENTION_FLOOR)
    if sum(age_window_removed.values()):
        log_progress(
            "Retention windows: removed expired/non-Highest public rows "
            + ", ".join(f"{k}={v}" for k, v in age_window_removed.items() if v)
        )
    previous, retired_c_removed = apply_retired_signal_filter(previous)
    if retired_c_removed:
        log_progress(
            f"Applied curator weak-signal retirements: removed {retired_c_removed} retired Strand-C item(s); "
            "A/B corpus and scan cursors untouched"
        )

    # A/B is audited only at migration boundaries: first inherited run, or when the
    # substantive quality-profile version changes. Normal recurring scans preserve the
    # cumulative corpus and never spend time re-auditing accepted history.
    inherited_audit = needs_inherited_corpus_audit(previous)
    precision_cleanup = (not inherited_audit) and needs_precision_corpus_cleanup(previous)
    inherited_audit_stats = {
        "strand_a_removed": 0, "strand_b_removed": 0,
        "stored_pass": 0, "refreshed_pass": 0, "refresh_unavailable": 0,
    }
    if inherited_audit or precision_cleanup:
        label = "First-run inherited-corpus audit" if inherited_audit else "Surgical quality-profile cleanup"
        log_progress(f"{label}: checking current saved A/B material before discovery")
        if inherited_audit:
            previous, inherited_audit_stats = audit_inherited_ab(previous, warnings)
        else:
            previous, inherited_audit_stats = surgical_precision_cleanup(previous)
        previous["inherited_corpus_audit_complete"] = True
        previous["precision_corpus_cleanup_complete"] = True
        log_progress(
            f"{label} complete: retained {inherited_audit_stats['stored_pass']} saved A/B item(s); removed only "
            f"{inherited_audit_stats['strand_a_removed']} A and {inherited_audit_stats['strand_b_removed']} B hard-failure item(s)"
        )

    signal_cleanup = needs_precision_signal_cleanup(previous)
    signal_cleanup_stats = {"strand_c_removed": 0, "strand_c_kept": len(previous.get("strand_c", []))}
    if signal_cleanup:
        log_progress("One-time corrective weak-signal cleanup: checking current Strand C before discovery")
        previous, signal_cleanup_stats = revalidate_saved_c(previous)
        previous["precision_signal_cleanup_complete"] = True
        log_progress(
            f"Weak-signal cleanup complete: kept {signal_cleanup_stats['strand_c_kept']} C; "
            f"removed {signal_cleanup_stats['strand_c_removed']} C item(s)"
        )

    DATE_FLOOR = preserved_corpus_floor(previous, now.date())
    KNOWN_AB_IDENTITIES, KNOWN_AB_LINKS, KNOWN_SIGNAL_IDENTITIES = known_sets_from_previous(previous)
    state = initial_scan_state(previous)
    INSTITUTION_SEEN_FINGERPRINTS = dict(state.get("institution_seen_fingerprints", {}))
    frontier_focus = frontier_gap_plan(previous, state)
    url_term_profiles = CONFIG.get("frontier_gap_institution_url_terms", {})
    ACTIVE_FRONTIER_GAP_URL_TERMS = list(dict.fromkeys(
        clean_text(term)
        for target in frontier_focus.get("weighted_targets", frontier_focus.get("targets", []))
        for term in ((url_term_profiles.get(target, []) if isinstance(url_term_profiles, dict) else []) or [])
        if clean_text(term)
    ))
    if frontier_focus["classifier_error"]:
        log_progress(f"Frontier coverage classifier unavailable; using rotating fallback: {frontier_focus['classifier_error']}")
    log_progress(
        f"Frontier coverage before scan: {frontier_focus['qualifying']} qualifying, "
        f"{frontier_focus['empty_cells']}/16 empty; balance target {frontier_focus.get('target_count', 3)} "
        f"(median {frontier_focus.get('median_count', 0)}, upper quartile {frontier_focus.get('upper_quartile', 0)}); under-covered "
        + (", ".join(f"{k}({frontier_focus.get('counts', {}).get(k, 0)})" for k in frontier_focus["targets"]) if frontier_focus["targets"] else "none")
    )

    try:
        last = dateparser.parse(previous.get("last_updated", "")).date()
        incremental_from = max(DATE_FLOOR, last - dt.timedelta(days=DISCOVERY_OVERLAP_DAYS))
    except Exception:
        incremental_from = bootstrap_floor(now.date())
    backfill_from = bootstrap_floor(now.date())

    # The broad lane is Strand A discovery. Strand B has its own strict method-
    # development lane below; mixing generic "method" queries into the broad bank
    # wastes rotation budget on papers that merely use a method.
    all_queries = list(dict.fromkeys(CONFIG.get("queries_a", [])))
    gap_scholarly = list(dict.fromkeys(frontier_focus.get("scholarly_queries", [])))
    gap_lookback_months = max(0, int(CONFIG.get("frontier_gap_historical_lookback_months", 0) or 0))
    # Gap priority must first exhaust the scanner's own live corpus window.  A sparse
    # cell is not evidence that recent literature is absent.  Historical rescue is
    # optional and disabled by default; when enabled it only broadens the scholarly
    # query window, never the institutional/new-signal date floor.
    gap_from = DATE_FLOOR  # Public radar and matrix never search outside the rolling four-month window.
    oa_cap = int(CONFIG.get("openalex_queries_per_scan", 40))
    cr_cap = int(CONFIG.get("crossref_broad_queries_per_scan", 35))

    # Keep a small, persisted future-method lane active every scan. This is
    # separate from the main A/B discovery cursor, so methods suitable for understanding A are
    # not delayed for several runs simply because the broad cursor is currently in
    # the Strand-A portion of the query bank.
    b_method_bank = list(dict.fromkeys(CONFIG.get("queries_b_method", [])))
    b_method_cursor_before = int(state.get("strand_b_method_cursor", 0) or 0)
    b_method_focus, _b_method_planned_next, _b_method_planned_wrapped = rotating_batch(
        b_method_bank,
        b_method_cursor_before,
        int(CONFIG.get("queries_b_method_per_scan", 6)),
    )

    # A separate persisted exploration lane searches the whole retained corpus
    # window, not just the short incremental overlap. This is the practical
    # rotation guarantee: every run moves to a different topic slice, and when a
    # topic comes around again its ``explore::`` depth page continues forward.
    explore_bank = diversified_query_bank(all_queries + b_method_bank)
    oa_explore_cursor_before = int(state.get("openalex_explore_cursor", state.get("openalex_cursor", 0)) or 0)
    cr_explore_cursor_before = int(state.get("crossref_explore_cursor", state.get("crossref_broad_cursor", 0)) or 0)
    exploration = scholarly_exploration_plan(state, all_queries + b_method_bank)
    oa_explore = exploration["openalex"]
    cr_explore = exploration["crossref"]
    # Planning is not progress. Restore the persisted positions until the collectors
    # report which queries actually made a network request.
    state["openalex_explore_cursor"] = oa_explore_cursor_before
    state["crossref_explore_cursor"] = cr_explore_cursor_before

    # Curated people are embedded discovery attention inside the scholarly rotation.
    # They do not create a separate corpus, page, section, or admission path. Category
    # round-robin keeps one run from spending all named-person budget on one field.
    priority_people_all = load_priority_people()
    priority_people_plan = priority_people_rotation_plan(state, priority_people_all)
    priority_people_bank = list(priority_people_plan.get("bank", []))
    priority_people_batch = list(priority_people_plan.get("people", []))
    priority_people_cursor_before = int(state.get("priority_people_cursor", 0) or 0)
    priority_people_names_all = [clean_text(x.get("name")) for x in priority_people_bank]
    priority_people_names_planned = [clean_text(x.get("name")) for x in priority_people_batch]

    # General foresight-expert recall: derive authors from already admitted Strand-B
    # method publications, then rotate a few exact-author checks. This follows people
    # demonstrated by the radar's own evidence instead of pinning any institution/domain.
    foresight_author_plan = foresight_author_rotation_plan(state, previous)
    foresight_author_bank = list(foresight_author_plan.get("bank", []))
    foresight_author_batch = list(foresight_author_plan.get("people", []))
    foresight_author_cursor_before = int(state.get("foresight_author_cursor", 0) or 0)
    foresight_author_names_all = [clean_text(x.get("name")) for x in foresight_author_bank]
    foresight_author_names_planned = [clean_text(x.get("name")) for x in foresight_author_batch]

    finding_context_bank = finding_context_query_bank(
        previous, max(1, int(CONFIG.get("finding_context_query_bank_size", 12) or 12))
    )
    finding_context_cursor_before = int(state.get("finding_context_cursor", 0) or 0)
    finding_context_focus, _fc_next, _fc_wrapped = rotating_batch(
        finding_context_bank, finding_context_cursor_before,
        max(0, int(CONFIG.get("finding_context_queries_per_scan", 4) or 0)),
    )

    # Guarantee a real broad rotation in the *executed prefix*. Earlier builds appended
    # base/exploration work after up to 32 Matrix-gap + 12 method queries, then truncated
    # the queue. Under ordinary stage deadlines this produced runs reporting a wide plan
    # while executing zero base, exploration or finding-context queries. Keep a minimum
    # broad slice and interleave every lane so partial execution remains genuinely broad.
    broad_min = max(1, int(CONFIG.get("scholarly_base_queries_per_scan", 12) or 12))
    oa_base_cap = min(oa_cap, broad_min)
    cr_base_cap = min(cr_cap, broad_min)
    oa_cursor_before = int(state.get("openalex_cursor", 0) or 0)
    cr_broad_cursor_before = int(state.get("crossref_broad_cursor", 0) or 0)
    oa_base, _oa_planned_next, _oa_planned_wrapped = rotating_batch(
        all_queries, oa_cursor_before, oa_base_cap
    )
    cr_base, _cr_planned_next, _cr_planned_wrapped = rotating_batch(
        all_queries, cr_broad_cursor_before, cr_base_cap
    )
    oa_batch = interleaved_unique_batch(
        oa_cap, oa_base, oa_explore, gap_scholarly, b_method_focus, finding_context_focus
    )
    cr_batch = interleaved_unique_batch(
        cr_cap, cr_base, cr_explore, gap_scholarly, b_method_focus, finding_context_focus
    )
    oa_query_dates = {q: gap_from for q in gap_scholarly}
    cr_query_dates = {q: gap_from for q in gap_scholarly}
    oa_depth_lanes = {q: "gap" for q in gap_scholarly}
    cr_depth_lanes = {q: "gap" for q in gap_scholarly}
    for q in finding_context_focus:
        oa_query_dates[q] = DATE_FLOOR
        cr_query_dates[q] = DATE_FLOOR
        oa_depth_lanes[q] = "finding-context"
        cr_depth_lanes[q] = "finding-context"
    for q in oa_explore:
        oa_query_dates[q] = DATE_FLOOR
        oa_depth_lanes[q] = "explore"
    for q in cr_explore:
        cr_query_dates[q] = DATE_FLOOR
        cr_depth_lanes[q] = "explore"
    priority_tasks_all = [
        (journal, query)
        for journal in list(dict.fromkeys(CONFIG.get("crossref_priority_journals", [])))
        for query in list(dict.fromkeys(CONFIG.get("crossref_priority_journal_queries", [])))
    ]
    cr_priority_cursor_before = int(state.get("crossref_priority_cursor", 0) or 0)
    cr_priority_batch, _cr_priority_planned_next, _cr_priority_planned_wrapped = rotating_batch(
        priority_tasks_all,
        cr_priority_cursor_before,
        int(CONFIG.get("crossref_priority_tasks_per_scan", 45)),
    )
    # V17.13.4 source attention: discovery gives extra slots to verified Q1 journals
    # and EU primary sources, but the broad rotating lanes are preserved. Source prestige
    # never bypasses or tightens the substantive admission gate.
    source_journals_all = list(dict.fromkeys(CONFIG.get("crossref_priority_journals", [])))
    preferred_q1 = [j for j in list(dict.fromkeys(CONFIG.get("preferred_q1_journals_sjr2024", []))) if j in source_journals_all]
    nonpreferred_journals = [j for j in source_journals_all if j not in preferred_q1]
    source_total = max(0, int(CONFIG.get("crossref_source_first_journals_per_scan", 10) or 0))
    preferred_n = min(source_total, max(0, int(CONFIG.get("preferred_q1_journals_per_scan", 5) or 0)))
    broad_floor = max(0.0, min(1.0, float(CONFIG.get("source_attention_floor_broad_share", 0.4) or 0.4)))
    broad_n = max(int(round(source_total * broad_floor)), source_total - preferred_n)
    broad_n = min(source_total, broad_n)
    preferred_n = min(preferred_n, max(0, source_total - broad_n)) if source_total else 0
    if preferred_q1 and source_total and preferred_n == 0:
        preferred_n = 1
        broad_n = max(0, source_total - 1)
    cr_preferred_cursor_before = int(state.get("crossref_preferred_journal_cursor", 0) or 0)
    cr_preferred_batch, _cr_pref_next, _cr_pref_wrapped = rotating_batch(
        preferred_q1, cr_preferred_cursor_before, preferred_n
    )
    cr_source_cursor_before = int(state.get("crossref_source_cursor", 0) or 0)
    cr_general_batch, _cr_source_planned_next, _cr_source_planned_wrapped = rotating_batch(
        nonpreferred_journals or source_journals_all, cr_source_cursor_before, broad_n
    )
    cr_source_batch = list(dict.fromkeys(cr_preferred_batch + cr_general_batch))

    institution_sources_all = list(CONFIG.get("institution_sources", []))
    official_domains = {clean_text(x).lower().removeprefix("www.") for x in CONFIG.get("official_eu_priority_domains", []) if clean_text(x)}
    official_sources = [
        src for src in institution_sources_all
        if clean_text(src.get("domain", "")).lower().removeprefix("www.") in official_domains
    ]
    general_sources = [
        src for src in institution_sources_all
        if clean_text(src.get("domain", "")).lower().removeprefix("www.") not in official_domains
    ]
    inst_total = max(0, int(CONFIG.get("institution_sources_per_scan", 18) or 0))
    official_n = min(inst_total, max(0, int(CONFIG.get("official_eu_priority_sources_per_scan", 8) or 0)))
    general_n = max(int(round(inst_total * broad_floor)), inst_total - official_n)
    general_n = min(inst_total, general_n)
    official_n = min(official_n, max(0, inst_total - general_n)) if inst_total else 0
    if official_sources and inst_total and official_n == 0:
        official_n = 1
        general_n = max(0, inst_total - 1)
    official_eu_cursor_before = int(state.get("official_eu_source_cursor", 0) or 0)
    official_rotating, _official_next, _official_wrapped = rotating_batch(
        official_sources, official_eu_cursor_before, official_n
    )
    institution_cursor_before = int(state.get("institution_cursor", 0) or 0)
    general_rotating, _inst_planned_next, _inst_planned_wrapped = rotating_batch(
        general_sources or institution_sources_all, institution_cursor_before, general_n
    )
    inst_rotating = list(dict.fromkeys([clean_text(x.get("domain", "")) for x in official_rotating + general_rotating]))
    inst_rotating = [
        next(src for src in official_rotating + general_rotating if clean_text(src.get("domain", "")) == domain)
        for domain in inst_rotating
    ]
    # Keep the persistent source rotation intact, then add specialist sources in
    # scarcity-weighted round-robin order across the selected cells. Source-list
    # ordering therefore cannot accidentally privilege one thematic cell forever.
    gap_source_profiles = CONFIG.get("frontier_gap_institution_sources", {})
    source_by_domain = {
        clean_text(src.get("domain", "")).lower().removeprefix("www."): src
        for src in institution_sources_all
        if isinstance(src, dict) and clean_text(src.get("domain", ""))
    }
    extra_cap = max(0, int(CONFIG.get("frontier_gap_institution_extra_sources_per_scan", 6) or 0))
    target_domain_lists: dict[str, list[str]] = {}
    if isinstance(gap_source_profiles, dict):
        for target in dict.fromkeys(frontier_focus.get("weighted_targets", frontier_focus.get("targets", []))):
            vals = gap_source_profiles.get(target, [])
            vals = vals if isinstance(vals, list) else [vals]
            target_domain_lists[target] = list(dict.fromkeys(
                clean_text(v).lower().removeprefix("www.") for v in vals if clean_text(v)
            ))

    gap_sources: list[dict[str, Any]] = []
    used_domains: set[str] = set()
    source_cursors = state.setdefault("frontier_gap_source_cursors", {})
    if not isinstance(source_cursors, dict):
        source_cursors = {}
        state["frontier_gap_source_cursors"] = source_cursors
    local_source_cursor = {k: int(source_cursors.get(k, 0) or 0) for k in target_domain_lists}
    for target in frontier_focus.get("weighted_targets", frontier_focus.get("targets", [])):
        domains = target_domain_lists.get(target, [])
        if not domains:
            continue
        # Try every configured specialist source at most once for this slot. The
        # saved cursor advances even when a source overlaps the base rotation.
        attempts = 0
        while attempts < len(domains):
            chosen, next_cursor = rotating_variants(domains, local_source_cursor.get(target, 0), 1)
            local_source_cursor[target] = next_cursor
            attempts += 1
            if not chosen:
                break
            domain = chosen[0]
            src = source_by_domain.get(domain)
            if src and domain not in used_domains and src not in inst_rotating:
                gap_sources.append(src)
                used_domains.add(domain)
                break
        if len(gap_sources) >= extra_cap:
            break
    for target, cursor in local_source_cursor.items():
        source_cursors[target] = cursor
    # Source-specific adapters for the hardest/highest-value EU publication domains get
    # their own small persisted rotation. This is additive to the broad institutional
    # source rotation, never a replacement for it. Adapter pages still pass the exact
    # same institutional parser and A/B admission gates.
    adapter_profiles = CONFIG.get("institution_source_adapters", {})
    adapter_domains_all = [
        clean_text(d).lower().removeprefix("www.")
        for d in (adapter_profiles.keys() if isinstance(adapter_profiles, dict) else [])
        if clean_text(d).lower().removeprefix("www.") in source_by_domain
    ]
    adapter_cursor_before = int(state.get("institution_source_adapter_cursor", 0) or 0)
    adapter_domain_batch, _adapter_next, _adapter_wrapped = rotating_batch(
        adapter_domains_all, adapter_cursor_before,
        max(0, int(CONFIG.get("institution_source_adapter_sources_per_scan", 4) or 4)),
    ) if adapter_domains_all else ([], 0, True)
    adapter_rotating = [source_by_domain[d] for d in adapter_domain_batch if d in source_by_domain]

    inst_batch_raw = inst_rotating + gap_sources + adapter_rotating
    inst_batch = []
    inst_batch_seen: set[str] = set()
    for src in inst_batch_raw:
        domain = clean_text(src.get("domain", "")).lower().removeprefix("www.")
        if not domain or domain in inst_batch_seen:
            continue
        inst_batch_seen.add(domain)
        inst_batch.append(src)
    extended_highest_sources_all = [src for src in institution_sources_all if source_can_reach_highest(src)]
    extended_highest_cursor_before = int(state.get("extended_highest_source_cursor", 0) or 0)
    extended_highest_batch, _extended_highest_next, _extended_highest_wrapped = rotating_batch(
        extended_highest_sources_all, extended_highest_cursor_before, EXTENDED_TOP_QUALITY_SOURCES_PER_SCAN
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
        f"Crossref {len(cr_batch)} broad + {len(cr_priority_batch)} priority task(s) + {len(cr_source_batch)} source-first journal(s) "
        f"({len(cr_preferred_batch)} preferred-Q1 + {len(cr_general_batch)} broad) from {cr_from.isoformat()}, "
        f"institutions {len(inst_batch)} source(s) ({len(official_rotating)} EU-primary + {len(general_rotating)} broad + {len(gap_sources)} gap-specialist + {len(adapter_rotating)} source-adapter, overlaps deduped) from {inst_from.isoformat()}; "
        f"hard budget {budget_seconds//60} min"
    )
    if gap_scholarly:
        log_progress(
            f"Frontier gap-rescue: {len(gap_scholarly)} scholarly query/queries search from "
            f"{gap_from.isoformat()} for the selected sparse cells; normal rotation remains incremental"
        )
    if b_method_focus:
        log_progress(
            f"Strand-B method lane: {len(b_method_focus)} rotating R&I foresight-method query/queries this scan"
        )
    if oa_explore or cr_explore:
        log_progress(
            "Historical exploration lane: "
            f"OpenAlex {len(oa_explore)} + Crossref {len(cr_explore)} query/queries from {DATE_FLOOR.isoformat()}; "
            "themes=" + ", ".join(exploration.get("themes", []))
        )
    if priority_people_batch:
        log_progress(
            f"Embedded researcher attention: {len(priority_people_batch)}/{len(priority_people_bank)} people checked inside scholarly discovery; "
            "categories=" + ", ".join(priority_people_plan.get("categories", []))
        )
    if foresight_author_batch:
        log_progress(
            f"Foresight-author recall: {len(foresight_author_batch)}/{len(foresight_author_bank)} admitted Strand-B author(s) in this rotation"
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
    SIGNAL_WINDOW_START_DATE = (now - dt.timedelta(hours=news_lookback)).date()
    log_progress(f"Weak-signal window: {news_lookback}h (recovery backfill={signal_backfill})")
    news_warnings: list[str] = []
    execution_stats: dict[str, Any] = {}
    # V17.12.6 activation repair: a version string alone is NOT proof that the
    # targeted catch-up actually ran.  The first V17.12.6 build could persist the
    # version/completed_at marker when the lane had been skipped.  Require a separate
    # verified-complete flag plus evidence that every configured recovery domain was
    # attempted.  These fields live only in scan_state and do not reset or move any
    # normal scanner cursor/backfill state.
    expected_rule_fix_sources = len({
        clean_text(x.get("domain", "")).lower().removeprefix("www.")
        for x in RULE_FIX_INSTITUTION_SOURCES
        if clean_text(x.get("domain", ""))
    })
    prior_rule_fix_state = previous.get("scan_state") if isinstance(previous.get("scan_state"), dict) else {}
    rule_fix_source_recovery_complete = bool(
        prior_rule_fix_state.get("rule_fix_source_recovery_verified_complete")
        and prior_rule_fix_state.get("rule_fix_source_recovery_version") == RULE_FIX_SOURCE_RECOVERY_VERSION
        and int(prior_rule_fix_state.get("rule_fix_source_recovery_sources_attempted", 0) or 0) >= expected_rule_fix_sources
        and int(prior_rule_fix_state.get("rule_fix_source_recovery_sources_with_jobs", 0) or 0) >= expected_rule_fix_sources
    )
    # V17.12.9 supersedes the special 11-source catch-up with the rotating four-month
    # institutional A-recovery lane below. That lane covers the *entire* trusted source
    # list, has its own cursor, and cannot widen Strand C. Keep old markers for audit
    # history, but do not spend another 6-minute stage on the obsolete special lane.
    rule_fix_source_recovery_complete = False
    rule_fix_source_recovery_needed = False
    rule_fix_source_recovery_attempted = False
    rule_fix_recovered: list[dict[str, Any]] = []
    phase_started = time.monotonic()
    news_deadline = phase_started + int(CONFIG.get("news_stage_seconds", 240))
    oa_deadline = phase_started + int(CONFIG.get("openalex_stage_seconds", 360))
    cr_deadline = phase_started + int(CONFIG.get("crossref_stage_seconds", 450))

    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        fut_news = ex.submit(
            safe_stage, "weak-signal news", collect_news, now, news_warnings, news_lookback, news_deadline, frontier_focus["queries"]
        )
        fut_oa = ex.submit(
            safe_stage, "OpenAlex", collect_openalex, oa_from, warnings, oa_batch, oa_deadline, oa_query_dates,
            state["result_depth"]["openalex"], oa_depth_lanes, execution_stats
        )
        fut_cr = ex.submit(
            safe_stage, "Crossref", collect_crossref, cr_from, warnings, cr_batch, cr_priority_batch, cr_source_batch, cr_deadline, cr_query_dates,
            state["result_depth"]["crossref_broad"], state["result_depth"]["crossref_priority"], cr_depth_lanes, execution_stats
        )
        news = fut_news.result()
        oa = fut_oa.result()
        cr = fut_cr.result()
    warnings.extend(news_warnings)

    oa = [x for x in oa if isinstance(x, dict)]
    cr = [x for x in cr if isinstance(x, dict)]
    oa_failed = source_stage_failed(warnings, "openalex")
    cr_failed = source_stage_failed(warnings, "crossref")

    # Curator candidate test lane. This is deliberately placed before lower-priority
    # recall/deepening work so supplied papers are actually tested, not merely stored
    # as notes. The lane resolves exact DOI/title records and then rejoins the ordinary
    # scholarly candidate pool; no curator hint can bypass admission or Matrix semantics.
    curator_candidate_testing_state = deepcopy(previous.get("curator_candidate_testing")) if isinstance(previous.get("curator_candidate_testing"), dict) else {}
    curator_test_candidates: list[dict[str, Any]] = []
    if bool(CONFIG.get("curator_candidate_testing_enabled", True)) and load_curator_candidate_tests() and budget_remaining() > 90:
        curator_seconds = min(
            int(CONFIG.get("curator_candidate_testing_stage_seconds", 240) or 240),
            max(30, int(budget_remaining() - int(CONFIG.get("network_reserve_seconds", 90)) - 45)),
        )
        if curator_seconds >= 30:
            log_progress("Curator candidate tests: exact DOI/title resolution through the normal A/B gate")
            try:
                curator_test_candidates, curator_candidate_testing_state = collect_curator_candidate_tests(
                    previous, warnings, time.monotonic() + curator_seconds, execution_stats
                )
            except Exception as e:
                warnings.append(f"Curator candidate testing fatal stage error: {type(e).__name__}: {str(e)[:160]}")
                curator_candidate_testing_state = dict(curator_candidate_testing_state or {})
                curator_candidate_testing_state["status"] = "stage_error"
                curator_candidate_testing_state["error"] = type(e).__name__
            cr.extend(curator_test_candidates)
    elif load_curator_candidate_tests():
        curator_candidate_testing_state = dict(curator_candidate_testing_state or {})
        curator_candidate_testing_state["status"] = "skipped_budget"

    # Commit rotation only for work that actually made a request. A stage deadline,
    # endpoint stop or queued-but-never-started task therefore remains pending instead
    # of disappearing for a whole rotation cycle.
    executed_oa = set(execution_stats.get("openalex_queries", set()))
    executed_cr = set(execution_stats.get("crossref_broad_queries", set()))
    executed_priority = set(execution_stats.get("crossref_priority_tasks", set()))
    state["openalex_cursor"], oa_wrapped, oa_base_executed = committed_rotation_cursor(
        all_queries, oa_cursor_before, oa_base, executed_oa
    )
    state["crossref_broad_cursor"], cr_broad_wrapped, cr_base_executed = committed_rotation_cursor(
        all_queries, cr_broad_cursor_before, cr_base, executed_cr
    )
    state["crossref_priority_cursor"], cr_priority_wrapped, cr_priority_executed = committed_rotation_cursor(
        priority_tasks_all, cr_priority_cursor_before, cr_priority_batch, executed_priority
    )
    executed_source_journals = set(execution_stats.get("crossref_source_journals", set()))
    state["crossref_preferred_journal_cursor"], cr_preferred_wrapped, cr_preferred_executed = committed_rotation_cursor(
        preferred_q1, cr_preferred_cursor_before, cr_preferred_batch, executed_source_journals
    )
    general_source_bank = nonpreferred_journals or source_journals_all
    state["crossref_source_cursor"], cr_source_wrapped, cr_source_executed = committed_rotation_cursor(
        general_source_bank, cr_source_cursor_before, cr_general_batch, executed_source_journals
    )
    method_executed = executed_oa | executed_cr
    state["strand_b_method_cursor"], b_method_wrapped, b_method_executed = committed_rotation_cursor(
        b_method_bank, b_method_cursor_before, b_method_focus, method_executed
    )
    state["finding_context_cursor"], finding_context_wrapped, finding_context_executed = committed_rotation_cursor(
        finding_context_bank, finding_context_cursor_before, finding_context_focus, method_executed
    )
    state["openalex_explore_cursor"], _oa_explore_wrapped, oa_explore_executed = committed_rotation_cursor(
        explore_bank, oa_explore_cursor_before, oa_explore, executed_oa
    )
    state["crossref_explore_cursor"], _cr_explore_wrapped, cr_explore_executed = committed_rotation_cursor(
        explore_bank, cr_explore_cursor_before, cr_explore, executed_cr
    )

    # Embedded recurring researcher attention. It has private persisted state for fair
    # cycling, but every admitted work immediately rejoins the ordinary scholarly pools.
    priority_people_executed_count = 0
    priority_context_queries: list[str] = []
    priority_context_oa_count = 0
    priority_context_cr_count = 0
    priority_people_trigger = max(0, int(CONFIG.get("priority_people_trigger_below_scholarly_candidates", 18) or 18))
    priority_people_needed = (len(oa) + len(cr) < priority_people_trigger) or frontier_focus.get("empty_cells", 0) >= 8
    if priority_people_batch and priority_people_needed and budget_remaining() > 90 and not (oa_failed and cr_failed):
        pp_deadline = time.monotonic() + min(
            int(CONFIG.get("priority_people_stage_seconds", 210) or 210),
            max(30, int(budget_remaining() - int(CONFIG.get("network_reserve_seconds", 90)) - 60)),
        )
        if pp_deadline > time.monotonic() + 20:
            priority_candidates = safe_stage(
                "embedded researcher exact-author check",
                collect_priority_people,
                priority_people_batch,
                DATE_FLOOR,
                warnings,
                pp_deadline,
                state,
                execution_stats,
                not oa_failed,
                not cr_failed,
            )
            for item in priority_candidates:
                if not isinstance(item, dict):
                    continue
                if item.get("_priority_origin") == "crossref":
                    cr.append(item)
                else:
                    oa.append(item)

        executed_people = set(execution_stats.get("priority_people_executed", set()))
        state["priority_people_cursor"], pp_wrapped, priority_people_executed_count = committed_rotation_cursor(
            priority_people_names_all,
            priority_people_cursor_before,
            priority_people_names_planned,
            executed_people,
        )
        if pp_wrapped and priority_people_executed_count:
            state["priority_people_completed_cycles"] = int(state.get("priority_people_completed_cycles", 0) or 0) + 1

        # Only people for whom both exact-author sources produced no record get a
        # bounded context fallback. These queries deliberately use affiliation and
        # expertise rather than merely repeating the person's name, so the lane can
        # find substantive adjacent work by other researchers too.
        priority_context_queries = list(dict.fromkeys(execution_stats.get("priority_people_context_queries", [])))[:
            max(0, int(CONFIG.get("priority_people_context_fallback_per_scan", 4) or 0))
        ]
        if priority_context_queries and budget_remaining() > 75:
            context_seconds = min(
                int(CONFIG.get("priority_people_context_stage_seconds", 90) or 90),
                max(25, int(budget_remaining() - int(CONFIG.get("network_reserve_seconds", 90)) - 45)),
            )
            context_deadline = time.monotonic() + context_seconds
            context_exec: dict[str, Any] = {}
            context_dates = {q: DATE_FLOOR for q in priority_context_queries}
            context_lanes = {q: "people-context" for q in priority_context_queries}
            context_oa: list[dict[str, Any]] = []
            context_cr: list[dict[str, Any]] = []
            with cf.ThreadPoolExecutor(max_workers=2) as ex:
                futs: list[tuple[str, Any]] = []
                if not oa_failed:
                    futs.append((
                        "oa",
                        ex.submit(
                            safe_stage,
                            "OpenAlex researcher-context fallback",
                            collect_openalex,
                            DATE_FLOOR, warnings, priority_context_queries, context_deadline,
                            context_dates, state["result_depth"]["openalex"], context_lanes, context_exec,
                        ),
                    ))
                if not cr_failed:
                    futs.append((
                        "cr",
                        ex.submit(
                            safe_stage,
                            "Crossref researcher-context fallback",
                            collect_crossref,
                            DATE_FLOOR, warnings, priority_context_queries, [], [], context_deadline,
                            context_dates, state["result_depth"]["crossref_broad"],
                            state["result_depth"]["crossref_priority"], context_lanes, context_exec,
                        ),
                    ))
                for family, fut in futs:
                    rows = [x for x in fut.result() if isinstance(x, dict)]
                    if family == "oa":
                        context_oa.extend(rows)
                    else:
                        context_cr.extend(rows)
            oa.extend(context_oa)
            cr.extend(context_cr)
            priority_context_oa_count = len(context_oa)
            priority_context_cr_count = len(context_cr)
            execution_stats["priority_people_context_openalex_queries_executed"] = len(set(context_exec.get("openalex_queries", set())))
            execution_stats["priority_people_context_crossref_queries_executed"] = len(set(context_exec.get("crossref_broad_queries", set())))
            execution_stats["priority_people_context_admitted"] = len(context_oa) + len(context_cr)

    # Bounded recurring attention to authors who have already produced admitted
    # foresight/method publications. This can discover a later A-relevant paper by the
    # same expert without creating a permanent source-specific publication lane.
    foresight_author_executed_count = 0
    foresight_author_candidates_count = 0
    if foresight_author_batch and budget_remaining() > 75 and not (oa_failed and cr_failed):
        fa_seconds = min(
            int(CONFIG.get("foresight_author_followup_stage_seconds", 90) or 90),
            max(25, int(budget_remaining() - int(CONFIG.get("network_reserve_seconds", 90)) - 45)),
        )
        fa_deadline = time.monotonic() + fa_seconds
        fa_exec: dict[str, Any] = {}
        fa_candidates = safe_stage(
            "foresight-author exact-author check",
            collect_priority_people,
            foresight_author_batch,
            DATE_FLOOR,
            warnings,
            fa_deadline,
            state,
            fa_exec,
            not oa_failed,
            not cr_failed,
            True,
        )
        foresight_author_candidates_count = len(fa_candidates)
        for item in fa_candidates:
            if not isinstance(item, dict):
                continue
            if item.get("_priority_origin") == "crossref":
                cr.append(item)
            else:
                oa.append(item)
        executed_fa = set(fa_exec.get("priority_people_executed", set()))
        state["foresight_author_cursor"], fa_wrapped, foresight_author_executed_count = committed_rotation_cursor(
            foresight_author_names_all, foresight_author_cursor_before, foresight_author_names_planned, executed_fa
        )
        if fa_wrapped and foresight_author_executed_count:
            state["foresight_author_completed_cycles"] = int(state.get("foresight_author_completed_cycles", 0) or 0) + 1

    # Before ordinary institutional rotation, give only the newly introduced V17.12.5
    # sources a one-time catch-up from the preserved corpus floor.  The first rule-fix
    # run correctly preserved all cursors, but that also meant these sources inherited
    # the 14-day incremental window and could not recover older May-July material.
    # This separate lane fixes that without resetting or moving any normal cursor.
    if rule_fix_source_recovery_needed and budget_remaining() > 210:
        rule_fix_source_recovery_attempted = True
        old_signal_window_start = SIGNAL_WINDOW_START_DATE
        # Historical source recovery is for missed A/B publications. Strand C remains
        # on its current-news window; otherwise old awards/jobs/events become fake signals.
        recovery_deadline = min(
            time.monotonic() + int(RULE_FIX_SOURCE_RECOVERY_STAGE_SECONDS),
            (SCAN_DEADLINE_MONO or (time.monotonic() + int(RULE_FIX_SOURCE_RECOVERY_STAGE_SECONDS)))
            - int(CONFIG.get("network_reserve_seconds", 90)) - 90,
        )
        recovery_execution: dict[str, Any] = {}
        if recovery_deadline > time.monotonic() + 30:
            rule_fix_recovered = safe_stage(
                "targeted new-source historical catch-up",
                collect_rule_fix_source_recovery,
                DATE_FLOOR,
                warnings,
                recovery_deadline,
                recovery_execution,
            )
        SIGNAL_WINDOW_START_DATE = old_signal_window_start
        expected_recovery_domains = {clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in RULE_FIX_INSTITUTION_SOURCES}
        attempted_recovery_domains = set(recovery_execution.get("rule_fix_recovery_sources", set()))
        recovery_domains_with_jobs = set(recovery_execution.get("rule_fix_recovery_sources_with_jobs", set()))
        recovery_budget_hit = bool(recovery_execution.get("rule_fix_recovery_budget_hit"))
        rule_fix_source_recovery_complete = bool(
            expected_recovery_domains
            and expected_recovery_domains.issubset(attempted_recovery_domains)
            and expected_recovery_domains.issubset(recovery_domains_with_jobs)
            and not recovery_budget_hit
        )
        execution_stats["rule_fix_source_recovery_attempted"] = True
        execution_stats["rule_fix_source_recovery_complete"] = rule_fix_source_recovery_complete
        execution_stats["rule_fix_source_recovery_sources_attempted"] = len(attempted_recovery_domains)
        execution_stats["rule_fix_source_recovery_sources_with_jobs"] = len(recovery_domains_with_jobs)
        execution_stats["rule_fix_source_recovery_jobs"] = int(recovery_execution.get("rule_fix_recovery_jobs", 0))
        execution_stats["rule_fix_source_recovery_admitted_ab"] = len(rule_fix_recovered)
        if rule_fix_source_recovery_complete:
            log_progress("Targeted new-source catch-up completed; normal institutional cursor remained untouched")
        else:
            log_progress("Targeted new-source catch-up remains pending; no normal cursor was reset or advanced by this lane")

    # Quiet-scan rescue runs BEFORE the slower institutional stage. If the early
    # scholarly slice is very sparse (currently three or fewer raw gate-passing
    # candidates), try another topic/depth slice while meaningful budget remains.
    quiet_rescue = {"attempted": False, "openalex_queries": [], "crossref_queries": [], "themes": []}
    rescue_enabled = bool(CONFIG.get("quiet_scan_rescue_enabled", True))
    rescue_min_remaining = int(CONFIG.get("quiet_scan_rescue_min_seconds_remaining", 180) or 180)
    scholarly_deduped = dedupe_candidates(oa + cr)
    rescue_trigger = max(1, int(CONFIG.get("quiet_scan_rescue_trigger_below_scholarly_candidates", 1) or 1))
    if (
        rescue_enabled and not rule_fix_source_recovery_attempted
        and len(scholarly_deduped) < rescue_trigger
        and budget_remaining() > rescue_min_remaining and not (oa_failed and cr_failed)
    ):
        rescue_n = max(1, int(CONFIG.get("quiet_scan_rescue_queries_per_source", 4) or 4))
        rescue_oa_cursor_before = int(state.get("openalex_explore_cursor", 0) or 0)
        rescue_cr_cursor_before = int(state.get("crossref_explore_cursor", 0) or 0)
        rescue_plan = scholarly_exploration_plan(
            state,
            all_queries + b_method_bank,
            oa_limit=rescue_n if not oa_failed else 0,
            cr_limit=rescue_n if not cr_failed else 0,
        )
        rescue_oa_queries = list(rescue_plan.get("openalex", []))
        rescue_cr_queries = list(rescue_plan.get("crossref", []))
        # Again, planning is not progress.
        state["openalex_explore_cursor"] = rescue_oa_cursor_before
        state["crossref_explore_cursor"] = rescue_cr_cursor_before
        quiet_rescue = {
            "attempted": bool(rescue_oa_queries or rescue_cr_queries),
            "openalex_queries": rescue_oa_queries,
            "crossref_queries": rescue_cr_queries,
            "themes": list(rescue_plan.get("themes", [])),
        }
        if quiet_rescue["attempted"]:
            log_progress(
                f"Low-yield rescue before institutional stage: first scholarly slice admitted {len(scholarly_deduped)} "
                f"candidate(s), below trigger {rescue_trigger}; trying next historical slice: "
                + ", ".join(quiet_rescue["themes"])
            )
            rescue_execution: dict[str, Any] = {}
            rescue_deadline = time.monotonic() + min(
                180,
                max(30, int(budget_remaining() - int(CONFIG.get("network_reserve_seconds", 150))))
            )
            with cf.ThreadPoolExecutor(max_workers=2) as ex:
                futs: list[tuple[str, Any]] = []
                if rescue_oa_queries:
                    futs.append((
                        "oa",
                        ex.submit(
                            safe_stage,
                            "OpenAlex quiet rescue",
                            collect_openalex,
                            DATE_FLOOR,
                            warnings,
                            rescue_oa_queries,
                            rescue_deadline,
                            {q: DATE_FLOOR for q in rescue_oa_queries},
                            state["result_depth"]["openalex"],
                            {q: "explore" for q in rescue_oa_queries},
                            rescue_execution,
                        ),
                    ))
                if rescue_cr_queries:
                    futs.append((
                        "cr",
                        ex.submit(
                            safe_stage,
                            "Crossref quiet rescue",
                            collect_crossref,
                            DATE_FLOOR,
                            warnings,
                            rescue_cr_queries,
                            [],
                            [],
                            rescue_deadline,
                            {q: DATE_FLOOR for q in rescue_cr_queries},
                            state["result_depth"]["crossref_broad"],
                            state["result_depth"]["crossref_priority"],
                            {q: "explore" for q in rescue_cr_queries},
                            rescue_execution,
                        ),
                    ))
                for family, fut in futs:
                    extra = [x for x in fut.result() if isinstance(x, dict)]
                    if family == "oa":
                        oa.extend(extra)
                    else:
                        cr.extend(extra)
            rescue_oa_executed = set(rescue_execution.get("openalex_queries", set()))
            rescue_cr_executed = set(rescue_execution.get("crossref_broad_queries", set()))
            state["openalex_explore_cursor"], _, rescue_oa_count = committed_rotation_cursor(
                explore_bank, rescue_oa_cursor_before, rescue_oa_queries, rescue_oa_executed
            )
            state["crossref_explore_cursor"], _, rescue_cr_count = committed_rotation_cursor(
                explore_bank, rescue_cr_cursor_before, rescue_cr_queries, rescue_cr_executed
            )
            execution_stats.setdefault("openalex_queries", set()).update(rescue_oa_executed)
            execution_stats.setdefault("crossref_broad_queries", set()).update(rescue_cr_executed)
            execution_stats["quiet_rescue_openalex_executed"] = rescue_oa_count
            execution_stats["quiet_rescue_crossref_executed"] = rescue_cr_count
            execution_stats["crossref_abstracts_enrichment_attempted"] = int(execution_stats.get("crossref_abstracts_enrichment_attempted", 0)) + int(rescue_execution.get("crossref_abstracts_enrichment_attempted", 0))

    # Citation snowballing is a recall lane, not an admission shortcut. It starts from
    # accepted/high-quality Strand-A publications, identifies references repeatedly cited
    # across those seeds, and follows those consensus references forward into the current
    # window. A small pinned-seed allowance supports curator-identified papers such as the
    # Radu national-AI-strategies paper without letting one bibliography dominate the lane.
    snowball_stats: dict[str, Any] = {"enabled": bool(CONFIG.get("citation_snowball_enabled", True))}
    snowball_candidates: list[dict[str, Any]] = []
    snowball_min_remaining = max(60, int(CONFIG.get("citation_snowball_min_seconds_remaining", 150) or 150))
    if snowball_stats["enabled"] and budget_remaining() > snowball_min_remaining and not oa_failed:
        snowball_seconds = min(
            int(CONFIG.get("citation_snowball_stage_seconds", 120) or 120),
            max(30, int(budget_remaining() - int(CONFIG.get("network_reserve_seconds", 90)) - 60)),
        )
        if snowball_seconds >= 30:
            log_progress("Citation snowball: ranking shared references across high-quality Strand-A seeds, then checking recent forward citations")
            try:
                snowball_candidates, snowball_stats = collect_citation_snowball(
                    previous, oa + cr, warnings, time.monotonic() + snowball_seconds, execution_stats
                )
            except Exception as e:
                warnings.append(f"Citation snowball fatal stage error: {type(e).__name__}: {str(e)[:160]}")
                snowball_candidates = []
                snowball_stats = {"enabled": True, "error": type(e).__name__, "admitted_unique": 0}
            oa.extend(snowball_candidates)

    # Exact URLs supplied through the curated manual lane are retried first. This is a
    # precision-preserving recall repair: only the supplied URL is fetched, and admission
    # still uses the normal source-aware A/B gate.
    manual_recovery_deadline = time.monotonic() + int(CONFIG.get("manual_recovery_stage_seconds", 120))
    manual_recovered = safe_stage(
        "manual exact-url recovery",
        collect_manual_recovery, previous, warnings, manual_recovery_deadline, execution_stats
    )

    # Reports retain a substantial independent slice, but no longer block the quiet
    # scholarly rescue from firing. High-quality institutional sources remain a core lane.
    inst_deadline = time.monotonic() + int(CONFIG.get("institution_stage_seconds", 480))
    inst = safe_stage(
        "institutional reports",
        collect_institutions,
        inst_from,
        warnings,
        bootstrap=inst_backfill,
        sources_override=inst_batch,
        stage_deadline=inst_deadline,
        execution_stats=execution_stats,
    )
    inst = dedupe_candidates([x for x in (manual_recovered + rule_fix_recovered + inst) if isinstance(x, dict)])

    # V17.13.23: bounded 4-6 month recovery only for sources capable of reaching the
    # existing Highest source-merit band. The normal four-month institutional stage runs
    # first, so freshness remains preferred. Older candidates are admitted only if their
    # computed source merit actually reaches Highest (>=93).
    extended_highest_candidates: list[dict[str, Any]] = []
    extended_highest_executed = 0
    if extended_highest_batch and budget_remaining() > max(120, EXTENDED_TOP_QUALITY_STAGE_SECONDS):
        extended_deadline = time.monotonic() + min(
            EXTENDED_TOP_QUALITY_STAGE_SECONDS,
            max(45, int(budget_remaining() - int(CONFIG.get("network_reserve_seconds", 150))))
        )
        extended_exec: dict[str, Any] = {}
        log_progress(
            f"Highest-merit 4-6 month recovery: {len(extended_highest_batch)} source(s) from {EXTENDED_DATE_FLOOR.isoformat()} "
            f"(core preference remains {DATE_FLOOR.isoformat()})"
        )
        recovered_extended = safe_stage(
            "Highest-merit extended recovery", collect_institutions, EXTENDED_DATE_FLOOR, warnings,
            False, extended_highest_batch, extended_deadline, extended_exec, False, EXTENDED_DATE_FLOOR
        )
        for item in recovered_extended:
            if not isinstance(item, dict):
                continue
            d = parse_date(item.get("date"))
            if d and EXTENDED_DATE_FLOOR <= d < DATE_FLOOR and highest_source_merit(item):
                item["extended_retention"] = True
                item["retention_window_months"] = EXTENDED_TOP_QUALITY_LOOKBACK_MONTHS
                extended_highest_candidates.append(item)
        all_extended_domains = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in extended_highest_sources_all]
        planned_extended_domains = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in extended_highest_batch]
        executed_extended_domains = set(extended_exec.get("institution_sources", set()))
        state["extended_highest_source_cursor"], _, extended_highest_executed = committed_rotation_cursor(
            all_extended_domains, extended_highest_cursor_before, planned_extended_domains, executed_extended_domains
        )
        execution_stats["extended_highest_sources_executed"] = extended_highest_executed
        execution_stats["extended_highest_candidates_admitted"] = len(extended_highest_candidates)
        inst = dedupe_candidates(inst + extended_highest_candidates)

    # V17.12.9: four-month A recall repair for institutional sources previously seen under
    # stricter/buggy admission rules. It uses its own cursor and ignores only the rejected-page
    # fingerprint cache; normal institution_cursor/backfill state is untouched. The lane rotates
    # across all configured institutions and completes over several scans.
    a_recall_complete = state.get("a_recall_recovery_version") == A_RECALL_RECOVERY_VERSION
    if (not a_recall_complete) and budget_remaining() > 210:
        recovery_cursor = int(state.get("a_recall_recovery_cursor", 0) or 0)
        recovery_sources, recovery_next, recovery_wrapped = rotating_batch(
            institution_sources_all, recovery_cursor, A_RECALL_RECOVERY_SOURCES_PER_SCAN
        )
        if recovery_sources:
            log_progress(
                f"Four-month institutional A-recall recovery: {len(recovery_sources)} source(s) from {DATE_FLOOR.isoformat()} "
                f"(normal institution cursor remains {state.get('institution_cursor', 0)})"
            )
            a_recovery_deadline = time.monotonic() + min(240, max(45, int(budget_remaining() - 150)))
            a_recovery_execution: dict[str, Any] = {}
            recovered_a = safe_stage(
                "institutional A-recall recovery", collect_institutions, DATE_FLOOR, warnings,
                False, recovery_sources, a_recovery_deadline, a_recovery_execution, True
            )
            inst = dedupe_candidates(inst + [x for x in recovered_a if isinstance(x, dict)])
            all_recovery_domains = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in institution_sources_all]
            planned_recovery_domains = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in recovery_sources]
            executed_recovery_domains = set(a_recovery_execution.get("institution_sources", set()))
            state["a_recall_recovery_cursor"], recovery_wrapped, recovery_executed = committed_rotation_cursor(
                all_recovery_domains, recovery_cursor, planned_recovery_domains, executed_recovery_domains
            )
            execution_stats["a_recall_recovery_sources_executed"] = int(execution_stats.get("a_recall_recovery_sources_executed", 0)) + recovery_executed
            execution_stats["a_recall_recovery_admitted_ab"] = int(execution_stats.get("a_recall_recovery_admitted_ab", 0)) + len(recovered_a)
            if recovery_wrapped:
                state["a_recall_recovery_version"] = A_RECALL_RECOVERY_VERSION
                log_progress("Four-month institutional A-recall recovery completed one full source rotation")

    if INSTITUTION_SIGNAL_CANDIDATES:
        # Direct institutional pages are frequently invisible to Google News. Merge
        # recent factual candidates into the same C pipeline; anchoring/dedupe later
        # applies the identical weak-signal quality rules.
        news.extend(dict(x) for x in INSTITUTION_SIGNAL_CANDIDATES if isinstance(x, dict))

    # C-to-evidence bridge: only actual C leads trigger this stage. Anchor the current
    # news/institutional candidates against the already-published A corpus first; this
    # prevents ordinary rejected news from consuming evidence-follow-up budget. Any linked
    # report/paper found here still has to pass the normal A/B gate independently.
    prev_a_for_signal_followup = previous.get("strand_a", []) if isinstance(previous.get("strand_a"), list) else []
    preliminary_c_for_followup = anchor_news(news, prev_a_for_signal_followup)
    signal_evidence_followup_stats: dict[str, Any] = {
        "signals_checked": 0, "links_examined": 0, "direct_ab": 0, "queries": 0, "scholarly_ab": 0
    }
    signal_evidence_candidates: list[dict[str, Any]] = []
    if bool(CONFIG.get("weak_signal_evidence_followup_enabled", True)) and budget_remaining() > 90:
        sef_seconds = min(
            int(CONFIG.get("weak_signal_evidence_followup_stage_seconds", 120) or 120),
            max(30, int(budget_remaining() - int(CONFIG.get("network_reserve_seconds", 90)) - 45)),
        )
        sef_deadline = time.monotonic() + sef_seconds
        signal_evidence_candidates = safe_stage(
            "weak-signal evidence follow-up",
            collect_weak_signal_evidence_followups,
            preliminary_c_for_followup,
            previous.get("strand_c", []) if isinstance(previous.get("strand_c"), list) else [],
            state,
            warnings,
            now,
            sef_deadline,
            not oa_failed,
            not cr_failed,
            signal_evidence_followup_stats,
        )
        inst.extend(signal_evidence_candidates)

    inst_failed = source_stage_failed(warnings, "institution")
    institution_domains_all = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in institution_sources_all]
    official_domains_all = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in official_sources]
    general_domains_all = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in (general_sources or institution_sources_all)]
    official_planned_domains = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in official_rotating]
    general_planned_domains = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in general_rotating]
    executed_inst = set(execution_stats.get("institution_sources", set()))
    state["official_eu_source_cursor"], official_wrapped, official_executed = committed_rotation_cursor(
        official_domains_all, official_eu_cursor_before, official_planned_domains, executed_inst
    )
    state["institution_cursor"], inst_wrapped, inst_base_executed = committed_rotation_cursor(
        general_domains_all, institution_cursor_before, general_planned_domains, executed_inst
    )
    state["institution_source_adapter_cursor"], adapter_wrapped, adapter_sources_executed = committed_rotation_cursor(
        adapter_domains_all, adapter_cursor_before, adapter_domain_batch, executed_inst
    ) if adapter_domains_all else (0, True, 0)

    # Target-driven low-yield rule: after the ordinary scholarly + institutional pass,
    # count only genuinely new, unique A/B records that already passed the normal gates.
    # If that count is below the discovery target, spend remaining time on a *different*
    # query/source slice rather than declaring the topic quiet. The target affects search
    # depth only: raw API hits, duplicates and marginal records never count toward it and
    # the substantive/quality gates remain unchanged. If the fresh four-month rotation is
    # still sparse, use a bounded 4-6 month extension and keep only Highest-merit evidence.
    target_new_ab = max(1, int(CONFIG.get("target_new_ab_per_scan", 20) or 20))
    low_yield_threshold = max(
        max(0, int(CONFIG.get("low_yield_fresh_rotation_trigger_max_new_ab", 3) or 3)),
        target_new_ab - 1,
    )
    low_yield_rotation = {
        "enabled": bool(CONFIG.get("low_yield_fresh_rotation_enabled", True)),
        "target_new_ab": target_new_ab,
        "trigger_max_new_ab": low_yield_threshold,
        "triggered": False,
        "new_ab_before": len(genuinely_new_ab_candidates(oa + cr + inst)),
        "new_ab_after_fresh_rotation": 0,
        "fresh_openalex_queries": [],
        "fresh_crossref_queries": [],
        "fresh_themes": [],
        "extended_fallback_attempted": False,
        "extended_openalex_queries": [],
        "extended_crossref_queries": [],
        "extended_institution_sources": [],
        "extended_highest_admitted": 0,
    }
    low_yield_rotation["new_ab_after_fresh_rotation"] = low_yield_rotation["new_ab_before"]
    fresh_min_remaining = max(30, int(CONFIG.get("low_yield_fresh_rotation_min_seconds_remaining", 180) or 180))
    fresh_query_n = max(1, int(CONFIG.get("low_yield_fresh_rotation_queries_per_source", 8) or 8))
    fresh_bank = diversified_query_bank(all_queries + b_method_bank + finding_context_bank)
    if (
        low_yield_rotation["enabled"]
        and low_yield_rotation["new_ab_before"] <= low_yield_threshold
        and budget_remaining() > fresh_min_remaining
        and not (oa_failed and cr_failed)
        and fresh_bank
    ):
        low_yield_rotation["triggered"] = True
        fresh_oa_cursor_before = int(state.get("low_yield_openalex_cursor", state.get("openalex_explore_cursor", 0)) or 0)
        fresh_cr_cursor_before = int(state.get("low_yield_crossref_cursor", state.get("crossref_explore_cursor", 0)) or 0)
        already_oa = set(execution_stats.get("openalex_queries", set()))
        already_cr = set(execution_stats.get("crossref_broad_queries", set()))
        fresh_oa_queries, fresh_oa_next, _ = rotating_batch_excluding(
            fresh_bank, fresh_oa_cursor_before, fresh_query_n if not oa_failed else 0, already_oa
        )
        fresh_cr_queries, fresh_cr_next, _ = rotating_batch_excluding(
            fresh_bank, fresh_cr_cursor_before, fresh_query_n if not cr_failed else 0, already_cr
        )
        low_yield_rotation["fresh_openalex_queries"] = fresh_oa_queries
        low_yield_rotation["fresh_crossref_queries"] = fresh_cr_queries
        low_yield_rotation["fresh_themes"] = list(dict.fromkeys(query_theme(q) for q in fresh_oa_queries + fresh_cr_queries))
        if fresh_oa_queries or fresh_cr_queries:
            log_progress(
                f"Low-yield fresh rotation: normal pass found {low_yield_rotation['new_ab_before']} genuinely new A/B item(s) "
                f"(trigger <= {low_yield_threshold}); trying unexecuted four-month query families: "
                + ", ".join(low_yield_rotation["fresh_themes"])
            )
            fresh_exec: dict[str, Any] = {}
            fresh_seconds = min(
                max(30, int(CONFIG.get("low_yield_fresh_rotation_stage_seconds", 180) or 180)),
                max(30, int(budget_remaining() - int(CONFIG.get("network_reserve_seconds", 90)) - 45)),
            )
            fresh_deadline = time.monotonic() + fresh_seconds
            with cf.ThreadPoolExecutor(max_workers=2) as ex:
                futs: list[tuple[str, Any]] = []
                if fresh_oa_queries:
                    futs.append(("oa", ex.submit(
                        safe_stage, "OpenAlex low-yield fresh rotation", collect_openalex, DATE_FLOOR, warnings,
                        fresh_oa_queries, fresh_deadline, {q: DATE_FLOOR for q in fresh_oa_queries},
                        state["result_depth"]["openalex"], {q: "low-yield-fresh" for q in fresh_oa_queries}, fresh_exec
                    )))
                if fresh_cr_queries:
                    futs.append(("cr", ex.submit(
                        safe_stage, "Crossref low-yield fresh rotation", collect_crossref, DATE_FLOOR, warnings,
                        fresh_cr_queries, [], [], fresh_deadline, {q: DATE_FLOOR for q in fresh_cr_queries},
                        state["result_depth"]["crossref_broad"], state["result_depth"]["crossref_priority"],
                        {q: "low-yield-fresh" for q in fresh_cr_queries}, fresh_exec
                    )))
                for family, fut in futs:
                    extra = [x for x in fut.result() if isinstance(x, dict)]
                    (oa if family == "oa" else cr).extend(extra)
            fresh_oa_executed = set(fresh_exec.get("openalex_queries", set()))
            fresh_cr_executed = set(fresh_exec.get("crossref_broad_queries", set()))
            commit_planned_cursor_if_executed(
                state, "low_yield_openalex_cursor", fresh_oa_cursor_before, fresh_oa_queries, fresh_oa_next, fresh_oa_executed
            )
            commit_planned_cursor_if_executed(
                state, "low_yield_crossref_cursor", fresh_cr_cursor_before, fresh_cr_queries, fresh_cr_next, fresh_cr_executed
            )
            execution_stats.setdefault("openalex_queries", set()).update(fresh_oa_executed)
            execution_stats.setdefault("crossref_broad_queries", set()).update(fresh_cr_executed)
            execution_stats["low_yield_fresh_openalex_executed"] = len(fresh_oa_executed)
            execution_stats["low_yield_fresh_crossref_executed"] = len(fresh_cr_executed)
            execution_stats["crossref_abstracts_enrichment_attempted"] = int(execution_stats.get("crossref_abstracts_enrichment_attempted", 0)) + int(fresh_exec.get("crossref_abstracts_enrichment_attempted", 0))
            low_yield_rotation["new_ab_after_fresh_rotation"] = len(genuinely_new_ab_candidates(oa + cr + inst))

    # A second low-yield fallback may look into months 4-6, but only the existing
    # Highest source-merit band is eligible for admission. This is extra recall, not
    # a relaxation of aboutness, EU scope, language, document-type or quality gates.
    extended_fallback_enabled = bool(CONFIG.get("low_yield_extended_fallback_enabled", True))
    extended_fallback_min_remaining = max(45, int(CONFIG.get("low_yield_extended_fallback_min_seconds_remaining", 150) or 150))
    if (
        extended_fallback_enabled
        and low_yield_rotation["new_ab_after_fresh_rotation"] <= low_yield_threshold
        and budget_remaining() > extended_fallback_min_remaining
        and (fresh_bank or extended_highest_sources_all)
    ):
        low_yield_rotation["extended_fallback_attempted"] = True
        ext_query_n = max(1, int(CONFIG.get("low_yield_extended_queries_per_source", 5) or 5))
        ext_oa_cursor_before = int(state.get("low_yield_extended_openalex_cursor", 0) or 0)
        ext_cr_cursor_before = int(state.get("low_yield_extended_crossref_cursor", max(0, len(fresh_bank) // 2)) or 0)
        if not oa_failed:
            ext_oa_queries, ext_oa_next, _ = rotating_batch(fresh_bank, ext_oa_cursor_before, ext_query_n)
        else:
            ext_oa_queries, ext_oa_next = [], ext_oa_cursor_before
        if not cr_failed:
            ext_cr_queries, ext_cr_next, _ = rotating_batch(fresh_bank, ext_cr_cursor_before, ext_query_n)
        else:
            ext_cr_queries, ext_cr_next = [], ext_cr_cursor_before
        low_yield_rotation["extended_openalex_queries"] = ext_oa_queries
        low_yield_rotation["extended_crossref_queries"] = ext_cr_queries
        ext_exec: dict[str, Any] = {}
        ext_seconds = min(
            max(45, int(CONFIG.get("low_yield_extended_fallback_stage_seconds", 150) or 150)),
            max(45, int(budget_remaining() - int(CONFIG.get("network_reserve_seconds", 90)) - 45)),
        )
        ext_deadline = time.monotonic() + ext_seconds
        raw_ext_oa: list[dict[str, Any]] = []
        raw_ext_cr: list[dict[str, Any]] = []
        if ext_oa_queries or ext_cr_queries:
            log_progress(
                f"Low-yield Highest-merit fallback: still only {low_yield_rotation['new_ab_after_fresh_rotation']} new A/B item(s); "
                f"checking scholarly/report evidence from {EXTENDED_DATE_FLOOR.isoformat()} to {DATE_FLOOR.isoformat()}"
            )
            with cf.ThreadPoolExecutor(max_workers=2) as ex:
                futs: list[tuple[str, Any]] = []
                if ext_oa_queries:
                    futs.append(("oa", ex.submit(
                        safe_stage, "OpenAlex low-yield 4-6 month fallback", collect_openalex, EXTENDED_DATE_FLOOR, warnings,
                        ext_oa_queries, ext_deadline, {q: EXTENDED_DATE_FLOOR for q in ext_oa_queries},
                        state["result_depth"]["openalex"], {q: "low-yield-extended" for q in ext_oa_queries}, ext_exec
                    )))
                if ext_cr_queries:
                    futs.append(("cr", ex.submit(
                        safe_stage, "Crossref low-yield 4-6 month fallback", collect_crossref, EXTENDED_DATE_FLOOR, warnings,
                        ext_cr_queries, [], [], ext_deadline, {q: EXTENDED_DATE_FLOOR for q in ext_cr_queries},
                        state["result_depth"]["crossref_broad"], state["result_depth"]["crossref_priority"],
                        {q: "low-yield-extended" for q in ext_cr_queries}, ext_exec
                    )))
                for family, fut in futs:
                    rows = [x for x in fut.result() if isinstance(x, dict)]
                    (raw_ext_oa if family == "oa" else raw_ext_cr).extend(rows)
        ext_oa_executed = set(ext_exec.get("openalex_queries", set()))
        ext_cr_executed = set(ext_exec.get("crossref_broad_queries", set()))
        commit_planned_cursor_if_executed(
            state, "low_yield_extended_openalex_cursor", ext_oa_cursor_before, ext_oa_queries, ext_oa_next, ext_oa_executed
        )
        commit_planned_cursor_if_executed(
            state, "low_yield_extended_crossref_cursor", ext_cr_cursor_before, ext_cr_queries, ext_cr_next, ext_cr_executed
        )
        execution_stats.setdefault("openalex_queries", set()).update(ext_oa_executed)
        execution_stats.setdefault("crossref_broad_queries", set()).update(ext_cr_executed)
        execution_stats["low_yield_extended_openalex_executed"] = len(ext_oa_executed)
        execution_stats["low_yield_extended_crossref_executed"] = len(ext_cr_executed)
        execution_stats["crossref_abstracts_enrichment_attempted"] = int(execution_stats.get("crossref_abstracts_enrichment_attempted", 0)) + int(ext_exec.get("crossref_abstracts_enrichment_attempted", 0))

        def keep_extended_highest(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
            kept: list[dict[str, Any]] = []
            for raw in rows:
                if not isinstance(raw, dict):
                    continue
                d = parse_date(raw.get("date"))
                if d and EXTENDED_DATE_FLOOR <= d < DATE_FLOOR and highest_source_merit(raw):
                    raw["extended_retention"] = True
                    raw["retention_window_months"] = EXTENDED_TOP_QUALITY_LOOKBACK_MONTHS
                    kept.append(raw)
            return kept

        ext_oa_kept = keep_extended_highest(raw_ext_oa)
        ext_cr_kept = keep_extended_highest(raw_ext_cr)
        oa.extend(ext_oa_kept)
        cr.extend(ext_cr_kept)

        # Also rotate a few additional Highest-capable official/public report sources.
        ext_source_n = max(0, int(CONFIG.get("low_yield_extended_sources_per_scan", 4) or 0))
        ext_source_cursor_before = int(state.get("low_yield_extended_source_cursor", 0) or 0)
        ext_source_batch, _ext_source_next, _ = rotating_batch(
            extended_highest_sources_all, ext_source_cursor_before, ext_source_n
        ) if ext_source_n and extended_highest_sources_all else ([], 0, True)
        low_yield_rotation["extended_institution_sources"] = [clean_text(x.get("domain")) for x in ext_source_batch]
        ext_inst_kept: list[dict[str, Any]] = []
        if ext_source_batch and time.monotonic() < ext_deadline - 20:
            ext_inst_exec: dict[str, Any] = {}
            ext_inst_rows = safe_stage(
                "institutional low-yield 4-6 month fallback", collect_institutions, EXTENDED_DATE_FLOOR, warnings,
                False, ext_source_batch, ext_deadline, ext_inst_exec, False, EXTENDED_DATE_FLOOR
            )
            ext_inst_kept = keep_extended_highest(ext_inst_rows)
            inst.extend(ext_inst_kept)
            ext_source_domains = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in extended_highest_sources_all]
            ext_planned_domains = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in ext_source_batch]
            ext_source_executed = set(ext_inst_exec.get("institution_sources", set()))
            state["low_yield_extended_source_cursor"], _, _ = committed_rotation_cursor(
                ext_source_domains, ext_source_cursor_before, ext_planned_domains, ext_source_executed
            )
            execution_stats.setdefault("institution_sources", set()).update(ext_source_executed)
        newly_kept_extended = dedupe_candidates(ext_oa_kept + ext_cr_kept + ext_inst_kept)
        low_yield_rotation["extended_highest_admitted"] = len(newly_kept_extended)
        extended_highest_candidates = dedupe_candidates(extended_highest_candidates + newly_kept_extended)
        low_yield_rotation["new_ab_after_extended_fallback"] = len(genuinely_new_ab_candidates(oa + cr + inst))
    else:
        low_yield_rotation["new_ab_after_extended_fallback"] = low_yield_rotation["new_ab_after_fresh_rotation"]

    full_rescue_threshold = max(0, int(CONFIG.get("low_yield_full_rescue_run_trigger_max_new_ab", low_yield_threshold) or low_yield_threshold))
    low_yield_rotation["full_rescue_run_enabled"] = bool(CONFIG.get("low_yield_full_rescue_run_enabled", True))
    low_yield_rotation["full_rescue_run_recommended"] = bool(
        low_yield_rotation["full_rescue_run_enabled"]
        and low_yield_rotation["new_ab_after_extended_fallback"] <= full_rescue_threshold
        and not RADAR_RESCUE_MODE
    )
    low_yield_rotation["scan_mode"] = "full_low_yield_rescue" if RADAR_RESCUE_MODE else "normal"

    # Spend otherwise-idle scan time on the actual gaps. Earlier versions finished
    # in 5-10 minutes even with a 20-minute scanner budget. This phase repeatedly
    # advances deeper result pages for zero-count Frontier cells and gives Strand C
    # a protected anchor-focused follow-up pass. It stops before the hard deadline so
    # radar.json can still be assembled and committed safely.
    deepening = {
        "attempted": False, "waves": 0, "gap_queries_executed": 0,
        "openalex_candidates": 0, "crossref_candidates": 0,
        "weak_signal_followup_candidates": 0,
        "empty_cells_start": len(frontier_focus.get("empty_targets", [])),
        "empty_cells_after_current_depth": len(frontier_focus.get("empty_targets", [])),
        "reallocations": [],
        "stubborn_recovery_attempted": False,
        "stubborn_recovery_queries_executed": 0,
        "stubborn_recovery_candidates": 0,
    }
    active_frontier_focus = dict(frontier_focus)
    gap_depth_bank = frontier_gap_depth_bank(active_frontier_focus)
    gap_depth_fallback_bank = frontier_gap_depth_bank(frontier_focus, include_nonempty=True)
    using_fallback_depth = not bool(frontier_focus.get("empty_targets"))
    deep_cursor = int(state.get("frontier_gap_depth_cursor", 0) or 0)
    deep_batch_size = max(1, int(CONFIG.get("frontier_gap_deepening_queries_per_wave", 14) or 14))
    deep_max_waves = max(0, int(CONFIG.get("frontier_gap_deepening_max_waves", 16) or 16))
    if not frontier_focus.get("empty_targets"):
        # Once every Matrix cell has evidence, balancing thin cells is useful but should
        # not consume the rest of a 20-minute run. Preserve most remaining time for the
        # wide recurring lanes and low-yield rescue instead of issuing 100+ gap queries.
        deep_max_waves = min(
            deep_max_waves,
            max(0, int(CONFIG.get("frontier_gap_deepening_max_waves_no_empty", 3) or 3)),
        )
    finalize_reserve = max(30, int(CONFIG.get("scan_finalize_reserve_seconds", 60) or 60))
    stubborn_enabled = bool(CONFIG.get("frontier_stubborn_recovery_enabled", True)) and bool(frontier_focus.get("empty_targets"))
    stubborn_reserve = max(0, int(CONFIG.get("frontier_stubborn_recovery_seconds", 240) or 0)) if stubborn_enabled else 0
    deep_stop_remaining = finalize_reserve + stubborn_reserve
    recompute_every = max(1, int(CONFIG.get("frontier_gap_recompute_every_n_waves", 1) or 1))
    deep_news_every = max(1, int(CONFIG.get("weak_signal_followup_every_n_waves", 2) or 2))
    deep_news_limit = max(0, int(CONFIG.get("weak_signal_followup_queries_per_wave", 10) or 10))
    deep_news_max_passes = max(0, int(CONFIG.get("weak_signal_followup_max_passes", 4) or 4))
    deep_news_passes = 0
    deep_oa_disabled = oa_failed
    deep_cr_disabled = cr_failed
    exhausted_oa: set[str] = set()
    exhausted_cr: set[str] = set()
    frontier_recovery_candidates: list[dict[str, Any]] = []
    while (
        gap_depth_bank and deepening["waves"] < deep_max_waves
        and budget_remaining() > deep_stop_remaining
        and not (deep_oa_disabled and deep_cr_disabled)
    ):
        available = [q for q in gap_depth_bank if not (q in exhausted_oa and q in exhausted_cr)]
        if not available and not using_fallback_depth:
            # Zero cells have been searched through the configured depth. Only now
            # spend remaining time on the next-thinnest cells.
            gap_depth_bank = gap_depth_fallback_bank
            using_fallback_depth = True
            deep_cursor = 0
            available = [q for q in gap_depth_bank if not (q in exhausted_oa and q in exhausted_cr)]
        if not available:
            break
        batch, planned_next, _ = rotating_batch(available, deep_cursor % len(available), min(deep_batch_size, len(available)))
        deepening["attempted"] = True
        deepening["waves"] += 1
        wave_no = deepening["waves"]
        wave_budget = min(150, max(25, int(budget_remaining() - deep_stop_remaining)))
        wave_deadline = time.monotonic() + wave_budget
        wave_exec: dict[str, Any] = {}
        log_progress(
            f"Matrix-first depth wave {wave_no}: {len(batch)} query/queries; "
            f"priority cells=" + ", ".join(active_frontier_focus.get("empty_targets") or active_frontier_focus.get("targets", []))
        )
        with cf.ThreadPoolExecutor(max_workers=3) as ex:
            futs: list[tuple[str, Any]] = []
            if not deep_oa_disabled:
                futs.append(("oa", ex.submit(
                    safe_stage, "OpenAlex matrix depth", collect_openalex, gap_from, warnings, batch, wave_deadline,
                    {q: gap_from for q in batch}, state["result_depth"]["openalex"], {q: "gap" for q in batch}, wave_exec, True
                )))
            if not deep_cr_disabled:
                futs.append(("cr", ex.submit(
                    safe_stage, "Crossref matrix depth", collect_crossref, gap_from, warnings, batch, [], [], wave_deadline,
                    {q: gap_from for q in batch}, state["result_depth"]["crossref_broad"], state["result_depth"]["crossref_priority"],
                    {q: "gap" for q in batch}, wave_exec, True
                )))
            # Protected C lane: do not make weak signals wait for whatever time A/B leaves.
            if deep_news_limit and deep_news_passes < deep_news_max_passes and wave_no % deep_news_every == 1:
                dynamic_signal_queries: list[str] = []
                news_profiles = CONFIG.get("frontier_gap_search_queries", {})
                for cell in active_frontier_focus.get("empty_targets") or active_frontier_focus.get("targets", []):
                    raw = news_profiles.get(cell, []) if isinstance(news_profiles, dict) else []
                    vals = raw if isinstance(raw, list) else [raw]
                    dynamic_signal_queries.extend(clean_text(v) for v in vals if clean_text(v))
                signal_queries = list(dict.fromkeys(dynamic_signal_queries + [
                    "EU Europe research innovation strategic shift new evidence",
                    "Europe research talent mobility brain drain new data",
                    "Europe research careers brain drain talent retention researchers new evidence",
                    "European scientists researcher outflow mobility survey new data",
                    "EU technology dependence foreign suppliers new restriction investment",
                    "European research cooperation China US new policy data",
                    "EU critical technology capability gap investment launch restriction",
                    "Europe science innovation competitiveness new report data",
                ]))[:deep_news_limit]
                deep_news_passes += 1
                futs.append(("news", ex.submit(
                    safe_stage, "weak-signal follow-up", collect_news, now, news_warnings, news_lookback, wave_deadline, signal_queries, False
                )))
            executed_this_wave: set[str] = set()
            for family, fut in futs:
                extra = [x for x in fut.result() if isinstance(x, dict)]
                if family == "oa":
                    oa.extend(extra); deepening["openalex_candidates"] += len(extra)
                    executed_this_wave.update(wave_exec.get("openalex_queries", set()))
                elif family == "cr":
                    cr.extend(extra); deepening["crossref_candidates"] += len(extra)
                    executed_this_wave.update(wave_exec.get("crossref_broad_queries", set()))
                else:
                    news.extend(extra); deepening["weak_signal_followup_candidates"] += len(extra)
        exhausted_oa.update(wave_exec.get("openalex_depth_exhausted", set()))
        exhausted_cr.update(wave_exec.get("crossref_depth_exhausted", set()))
        execution_stats.setdefault("openalex_queries", set()).update(wave_exec.get("openalex_queries", set()))
        execution_stats.setdefault("crossref_broad_queries", set()).update(wave_exec.get("crossref_broad_queries", set()))
        execution_stats["crossref_abstracts_enrichment_attempted"] = int(execution_stats.get("crossref_abstracts_enrichment_attempted", 0)) + int(wave_exec.get("crossref_abstracts_enrichment_attempted", 0))
        deepening["gap_queries_executed"] += len(executed_this_wave)
        # Advance only across query positions that actually reached a source.
        if executed_this_wave:
            # Do not skip queued formulations that never reached either endpoint.
            # Advance only across the contiguous executed prefix of this wave.
            consumed = 0
            for q in batch:
                if q not in executed_this_wave:
                    break
                consumed += 1
            deep_cursor = (deep_cursor + consumed) % max(1, len(gap_depth_bank))
        if not executed_this_wave:
            break
        # Recompute the matrix against candidates admitted so far. Once a zero cell
        # receives evidence, subsequent waves immediately stop spending scarce depth
        # on it and reallocate to the cells that remain empty.
        if wave_no % recompute_every == 0:
            probe = provisional_frontier_document(previous, oa + cr + inst, frontier_recovery_candidates)
            live_counts, live_qualifying, live_error = frontier_matrix_coverage(probe)
            if not live_error:
                live_balance = frontier_balance_snapshot(live_counts, state, advance_cursor=False)
                live_empty = list(live_balance.get("empty_targets") or [])
                deepening["empty_cells_after_current_depth"] = sum(1 for key in FRONTIER_CELL_ORDER if live_counts.get(key, 0) == 0)
                deepening["undercovered_cells_after_current_depth"] = int(live_balance.get("undercovered_cells", 0) or 0)
                old_signature = (
                    int(active_frontier_focus.get("target_count", 0) or 0),
                    tuple(active_frontier_focus.get("targets") or []),
                    tuple(active_frontier_focus.get("empty_targets") or []),
                )
                new_signature = (
                    int(live_balance.get("target_count", 0) or 0),
                    tuple(live_balance.get("targets") or []),
                    tuple(live_balance.get("empty_targets") or []),
                )
                if new_signature != old_signature:
                    deepening["reallocations"].append({
                        "wave": wave_no,
                        "from": list(active_frontier_focus.get("targets") or []),
                        "to": list(live_balance.get("targets") or []),
                        "target_count": int(live_balance.get("target_count", 0) or 0),
                    })
                    active_frontier_focus = dict(active_frontier_focus)
                    active_frontier_focus.update(live_balance)
                    active_frontier_focus["counts"] = live_counts
                    active_frontier_focus["qualifying"] = live_qualifying
                    gap_depth_bank = frontier_gap_depth_bank(active_frontier_focus)
                    using_fallback_depth = not bool(live_balance.get("empty_targets"))
                    if using_fallback_depth:
                        gap_depth_bank = frontier_gap_depth_bank(active_frontier_focus, include_nonempty=True)
                    deep_cursor = 0
                    log_progress(
                        "Matrix balance reallocated after wave " + str(wave_no) + ": target="
                        + str(live_balance.get("target_count", 0)) + "; priority="
                        + (", ".join(live_balance.get("targets") or []) if live_balance.get("targets") else "none")
                    )
        # Stop a family after a hard source failure; the other family can keep using depth time.
        if source_stage_failed(warnings, "openalex") or any("openalex http 429" in normalized(w) for w in warnings):
            deep_oa_disabled = True
        if source_stage_failed(warnings, "crossref") or any("crossref http 429" in normalized(w) or "crossref" in normalized(w) and "rate limited after cooldown" in normalized(w) for w in warnings):
            deep_cr_disabled = True

    # If current-window depth still leaves cells empty, use a bounded historical lane
    # *only for Frontier evidence*. This incorporates the useful part of the earlier
    # historical-lookback diagnosis without moving the main A/B corpus date floor.
    # Older items discovered here can populate the 4x4 structural evidence matrix but
    # are stored separately in `frontier_evidence` and never become ordinary Strand A.
    final_probe = provisional_frontier_document(previous, oa + cr + inst, frontier_recovery_candidates)
    live_counts, live_qualifying, live_error = frontier_matrix_coverage(final_probe)
    remaining_empty = [key for key in FRONTIER_CELL_ORDER if live_counts.get(key, 0) == 0] if not live_error else list(active_frontier_focus.get("empty_targets") or [])
    deepening["empty_cells_after_current_depth"] = len(remaining_empty)
    if (
        stubborn_enabled and remaining_empty and budget_remaining() > finalize_reserve + 25
        and not (deep_oa_disabled and deep_cr_disabled)
    ):
        recovery_months = max(1, int(CONFIG.get("frontier_stubborn_recovery_lookback_months", 4) or 4))
        recovery_from = DATE_FLOOR
        recovery_focus = dict(active_frontier_focus)
        recovery_focus["empty_targets"] = remaining_empty
        recovery_focus["targets"] = remaining_empty
        recovery_max_queries = max(1, int(CONFIG.get("frontier_stubborn_recovery_max_queries", 30) or 30))
        recovery_plan = frontier_gap_recovery_plan(recovery_focus, state, recovery_max_queries)
        recovery_bank = recovery_plan["queries"]
        if recovery_bank:
            recovery_deadline = time.monotonic() + min(
                max(25, int(CONFIG.get("frontier_stubborn_recovery_seconds", 240) or 240)),
                max(25, int(budget_remaining() - finalize_reserve)),
            )
            recovery_exec: dict[str, Any] = {}
            deepening["stubborn_recovery_attempted"] = True
            deepening["stubborn_recovery_from"] = recovery_from.isoformat()
            deepening["stubborn_recovery_window_note"] = "Same rolling four-month window as the public radar."
            deepening["stubborn_recovery_cells"] = remaining_empty
            log_progress(
                "Stubborn-cell recovery: " + ", ".join(remaining_empty)
                + f"; matrix-only evidence search from {recovery_from.isoformat()}"
            )
            with cf.ThreadPoolExecutor(max_workers=2) as ex:
                futs: list[tuple[str, Any]] = []
                if not deep_oa_disabled:
                    futs.append(("oa", ex.submit(
                        safe_stage, "OpenAlex stubborn-cell recovery", collect_openalex,
                        recovery_from, warnings, recovery_bank, recovery_deadline,
                        {q: recovery_from for q in recovery_bank}, state["frontier_recovery_depth"]["openalex"],
                        {q: "gap" for q in recovery_bank}, recovery_exec, True
                    )))
                if not deep_cr_disabled:
                    futs.append(("cr", ex.submit(
                        safe_stage, "Crossref stubborn-cell recovery", collect_crossref,
                        recovery_from, warnings, recovery_bank, [], [], recovery_deadline,
                        {q: recovery_from for q in recovery_bank}, state["frontier_recovery_depth"]["crossref"], {},
                        {q: "gap" for q in recovery_bank}, recovery_exec, True
                    )))
                for family, fut in futs:
                    extra = [x for x in fut.result() if isinstance(x, dict) and x.get("strand") in {"A", "both"}]
                    for item in extra:
                        item_date = parse_date(item.get("date"))
                        if item_date and item_date >= DATE_FLOOR:
                            (oa if family == "oa" else cr).append(item)
                        else:
                            item["_frontier_recovery"] = True
                            frontier_recovery_candidates.append(item)
                    deepening["stubborn_recovery_candidates"] += len(extra)
            recovery_executed = set(recovery_exec.get("openalex_queries", set())) | set(recovery_exec.get("crossref_broad_queries", set()))
            deepening["stubborn_recovery_queries_executed"] = len(recovery_executed)
            deepening["stubborn_recovery_query_cells"] = {k: list(v) for k, v in recovery_plan.get("planned_by_cell", {}).items()}
            deepening["stubborn_recovery_cursor_advanced"] = commit_frontier_recovery_plan(state, recovery_plan, recovery_executed)
            execution_stats["crossref_abstracts_enrichment_attempted"] = int(execution_stats.get("crossref_abstracts_enrichment_attempted", 0)) + int(recovery_exec.get("crossref_abstracts_enrichment_attempted", 0))
            post_probe = provisional_frontier_document(previous, oa + cr + inst, frontier_recovery_candidates)
            post_counts, _, post_error = frontier_matrix_coverage(post_probe)
            if not post_error:
                deepening["empty_cells_after_stubborn_recovery"] = sum(1 for k in FRONTIER_CELL_ORDER if post_counts.get(k, 0) == 0)
                deepening["stubborn_recovery_remaining_cells"] = [k for k in FRONTIER_CELL_ORDER if post_counts.get(k, 0) == 0]
    state["frontier_gap_depth_cursor"] = deep_cursor
    warnings.extend(x for x in news_warnings if x not in warnings)

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

    deduped = dedupe_candidates(oa + cr + inst)
    deduped.sort(key=rank_candidate)

    new_selected = deduped[:MAX_NEW_AB] if MAX_NEW_AB > 0 else deduped

    prev_a = previous.get("strand_a", []) if isinstance(previous.get("strand_a"), list) else []
    prev_b = previous.get("strand_b", []) if isinstance(previous.get("strand_b"), list) else []
    strand_a = merge_corpus(prev_a, new_selected, "A", now_iso)
    strand_b = merge_corpus(prev_b, new_selected, "B", now_iso)
    strand_a, expired_a_after_merge, extended_a_kept = enforce_two_tier_ab_window(strand_a, DATE_FLOOR, EXTENDED_DATE_FLOOR)
    strand_b, expired_b_after_merge, extended_b_kept = enforce_two_tier_ab_window(strand_b, DATE_FLOOR, EXTENDED_DATE_FLOOR)
    if expired_a_after_merge or expired_b_after_merge:
        log_progress(
            f"Two-tier retention after merge: removed A={expired_a_after_merge}, B={expired_b_after_merge}; "
            f"retained Highest-merit 4-6 month evidence A={extended_a_kept}, B={extended_b_kept}"
        )
    prev_frontier_evidence = previous.get("frontier_evidence", []) if isinstance(previous.get("frontier_evidence"), list) else []
    frontier_evidence = merge_corpus(prev_frontier_evidence, frontier_recovery_candidates, "A", now_iso)
    frontier_evidence = [
        x for x in frontier_evidence
        if isinstance(x, dict) and (parse_date(x.get("date")) is None or parse_date(x.get("date")) >= DATE_FLOOR)
    ]
    output_corpus_floor = DATE_FLOOR

    current_c = anchor_news(news, strand_a)
    prev_c = previous.get("strand_c", []) if isinstance(previous.get("strand_c"), list) else []
    strand_c = merge_signal_corpus(prev_c, current_c, now_iso)
    retired_signal_titles = _retired_signal_headlines(previous)
    strand_c = [
        item for item in strand_c
        if clean_text(item.get("headline", "")) not in retired_signal_titles
    ]
    # Retention is now a hard six-month contract for every admitted weak signal.
    # Do not delete C rows merely to enforce a presentation share ceiling; evidential
    # hierarchy is conveyed explicitly by evidence_status="low" instead.
    c_share_removed = 0

    # Recompute against exactly what will be published. A cell can change after the
    # final A/C merge even when the in-run provisional matrix looked stable.
    published_probe = {"strand_a": strand_a, "strand_b": strand_b, "strand_c": strand_c, "frontier_evidence": frontier_evidence}
    published_counts, published_qualifying, published_placements, published_matrix_error = frontier_matrix_snapshot(published_probe)
    curator_candidate_testing_state = apply_curator_matrix_placements(
        curator_candidate_testing_state, published_placements, published_probe
    ) if curator_candidate_testing_state else curator_candidate_testing_state
    if not published_matrix_error:
        deepening["empty_cells_published"] = sum(1 for k in FRONTIER_CELL_ORDER if published_counts.get(k, 0) == 0)
        deepening["published_empty_cells"] = [k for k in FRONTIER_CELL_ORDER if published_counts.get(k, 0) == 0]
        deepening["published_qualifying"] = published_qualifying

    previous_a_ids = {identity(internalize_previous(x)) for x in prev_a if isinstance(x, dict)}
    previous_b_ids = {identity(internalize_previous(x)) for x in prev_b if isinstance(x, dict)}
    new_a_count = sum(1 for x in strand_a if x.get("new_this_scan") and identity(internalize_previous(x)) not in previous_a_ids)
    new_b_count = sum(1 for x in strand_b if x.get("new_this_scan") and identity(internalize_previous(x)) not in previous_b_ids)
    new_c_count = sum(1 for x in strand_c if x.get("new_this_scan"))
    rejection_funnel = build_admission_rejection_funnel(
        unique_gate_candidates=len(deduped),
        genuinely_new_candidates=len(genuinely_new_ab_candidates(deduped)),
    )

    signal_backfill_ok = not (
        source_stage_failed(warnings, "weak-signal")
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
    if rule_fix_source_recovery_complete:
        # Persist completion only after the recovery lane itself proved that every
        # configured source was attempted without hitting its stage budget.
        state["rule_fix_source_recovery_version"] = RULE_FIX_SOURCE_RECOVERY_VERSION
        state["rule_fix_source_recovery_verified_complete"] = True
        state["rule_fix_source_recovery_sources_attempted"] = max(
            expected_rule_fix_sources,
            int(execution_stats.get("rule_fix_source_recovery_sources_attempted", 0) or 0),
            int(state.get("rule_fix_source_recovery_sources_attempted", 0) or 0),
        )
        state["rule_fix_source_recovery_sources_with_jobs"] = max(
            expected_rule_fix_sources,
            int(execution_stats.get("rule_fix_source_recovery_sources_with_jobs", 0) or 0),
            int(state.get("rule_fix_source_recovery_sources_with_jobs", 0) or 0),
        )
        state["rule_fix_source_recovery_completed_at"] = state.get("rule_fix_source_recovery_completed_at") or now_iso
    state["last_started_at"] = now_iso
    state["last_batches"] = {
        "openalex_queries": len(oa_batch),
        "openalex_exploration_queries": len(oa_explore),
        "finding_context_queries": len(finding_context_focus),
        "crossref_broad_queries": len(cr_batch),
        "crossref_exploration_queries": len(cr_explore),
        "crossref_priority_tasks": len(cr_priority_batch),
        "priority_people": len(priority_people_batch),
        "priority_people_context_queries": len(priority_context_queries),
        "foresight_authors": len(foresight_author_batch),
        "weak_signal_evidence_signals_checked": int(signal_evidence_followup_stats.get("signals_checked", 0)),
        "institution_sources": len(inst_batch),
        "rule_fix_new_source_recovery_sources": len(RULE_FIX_INSTITUTION_SOURCES) if rule_fix_source_recovery_needed else 0,
        "manual_recovery_urls": len(manual_recovery_jobs(previous)),
        "frontier_gap_queries": len(frontier_focus["queries"]),
        "frontier_gap_scholarly_queries": len(frontier_focus.get("scholarly_queries", [])),
    }
    state["frontier_coverage_before_scan"] = {
        "qualifying": frontier_focus["qualifying"],
        "empty_cells": frontier_focus["empty_cells"],
        "counts": frontier_focus["counts"],
        "target_count": frontier_focus.get("target_count", 3),
        "median_count": frontier_focus.get("median_count", 0),
        "upper_quartile": frontier_focus.get("upper_quartile", 0),
        "row_totals": frontier_focus.get("row_totals", {}),
        "column_totals": frontier_focus.get("column_totals", {}),
        "undercovered_cells": frontier_focus.get("undercovered_cells", 0),
        "max_count": frontier_focus.get("max_count", 0),
        "min_count": frontier_focus.get("min_count", 0),
        "deficits": frontier_focus.get("deficits", {}),
        "scarcity_scores": frontier_focus.get("scarcity_scores", {}),
        "targets": frontier_focus["targets"],
    }

    manual_ingest_state = deepcopy(previous.get("manual_ingest")) if isinstance(previous.get("manual_ingest"), dict) else {}
    if manual_ingest_state:
        queue = manual_ingest_state.get("recovery_queue") if isinstance(manual_ingest_state.get("recovery_queue"), list) else []
        live_items = [x for x in (strand_a + strand_b + frontier_evidence) if isinstance(x, dict)]
        live_links = {normalized_link(x.get("link", "")) for x in live_items if clean_text(x.get("link"))}
        live_titles = {norm_title(x.get("title", "")) for x in live_items if clean_text(x.get("title"))}
        manual_ingest_state["recovery_queue"] = [
            q for q in queue if isinstance(q, dict)
            and normalized_link(q.get("url", "")) not in live_links
            and norm_title(q.get("title", "")) not in live_titles
        ]
        manual_ingest_state["last_scan_recovery"] = {
            "scan_at": now_iso,
            "urls_attempted": int(execution_stats.get("manual_recovery_urls_attempted", 0)),
            "admitted": int(execution_stats.get("manual_recovery_admitted", 0)),
            "remaining_queue": len(manual_ingest_state.get("recovery_queue", [])),
        }

    completed = dt.datetime.now(dt.timezone.utc)
    completed_iso = completed.isoformat(timespec="minutes").replace("+00:00", "Z")
    state["last_run"] = completed_iso
    state["last_completed_at"] = completed_iso

    data = {
        "last_updated": completed_iso,
        "run_started_at": now_iso,
        "run_completed_at": completed_iso,
        "first_scan_complete": True,
        "corpus_start_date": output_corpus_floor.isoformat(),
        "preferred_corpus_start_date": DATE_FLOOR.isoformat(),
        "extended_top_quality_start_date": EXTENDED_DATE_FLOOR.isoformat(),
        "weak_signal_retention_start_date": SIGNAL_RETENTION_FLOOR.isoformat(),
        "corpus_window_policy": f"{BOOTSTRAP_LOOKBACK_MONTHS}-month A/B core; Highest source-merit A/B evidence retained/discovered to {EXTENDED_TOP_QUALITY_LOOKBACK_MONTHS} months; weak signals retained {WEAK_SIGNAL_RETENTION_MONTHS} months at low evidential status",
        "source_expansion_version": expansion_marker,
        "quality_profile_version": QUALITY_PROFILE_VERSION,
        "aboutness_profile_version": str(CONFIG.get("aboutness_profile_version", "")),
        "matrix_profile_version": str(CONFIG.get("matrix_profile_version", "")),
        "display_claim_profile_version": str(CONFIG.get("display_claim_profile_version", "")),
        "presentation_profile_version": str(CONFIG.get("presentation_profile_version", previous.get("presentation_profile_version", ""))),
        "reader_language_profile_version": str(CONFIG.get("reader_language_profile_version", previous.get("reader_language_profile_version", ""))),
        "manual_ingest_profile_version": str(CONFIG.get("manual_ingest_profile_version", previous.get("manual_ingest_profile_version", ""))),
        "manual_ingest": manual_ingest_state,
        "curator_candidate_testing_profile_version": clean_text((load_curator_candidate_tests() or {}).get("profile_version")),
        "curator_candidate_testing": curator_candidate_testing_state,
        "quality_migration_this_run": False,
        "inherited_corpus_audit_complete": bool(previous.get("inherited_corpus_audit_complete")) or inherited_audit,
        "inherited_corpus_audit_this_run": inherited_audit,
        "inherited_corpus_audit_stats": inherited_audit_stats if (inherited_audit or precision_cleanup) else {},
        "precision_corpus_cleanup_complete": bool(previous.get("precision_corpus_cleanup_complete")) or inherited_audit or precision_cleanup,
        "precision_corpus_cleanup_this_run": precision_cleanup,
        "precision_signal_cleanup_complete": bool(previous.get("precision_signal_cleanup_complete")) or signal_cleanup,
        "precision_signal_cleanup_this_run": signal_cleanup,
        "precision_signal_cleanup_stats": signal_cleanup_stats if signal_cleanup else {},
        "backfill_complete": backfill_complete,
        "signal_discovery_version": signal_marker,
        "signal_quality_profile_version": SIGNAL_QUALITY_PROFILE_VERSION,
        "c_admission_profile_version": C_ADMISSION_PROFILE_VERSION,
        "retired_signal_headlines": sorted(_retired_signal_headlines(previous)),
        "signal_backfill_complete": signal_backfill_complete,
        "incremental_state_version": INCREMENTAL_STATE_VERSION,
        "rotation_profile_version": ROTATION_PROFILE_VERSION,
        "matrix_balance_rotation_profile_version": MATRIX_BALANCE_ROTATION_PROFILE_VERSION,
        "source_attention_profile_version": SOURCE_ATTENTION_PROFILE_VERSION,
        "recall_profile_version": RECALL_PROFILE_VERSION,
        "main_recall_repair_version": str(CONFIG.get("main_recall_repair_version", "")),
        "scan_mode": "full_low_yield_rescue" if RADAR_RESCUE_MODE else "normal",
        "citation_snowball_profile_version": CITATION_SNOWBALL_PROFILE_VERSION,
        "window_policy_version": WINDOW_POLICY_VERSION,
        "rule_fix_profile_version": RULE_FIX_PROFILE_VERSION,
        "rule_fix_source_recovery_version": (
            RULE_FIX_SOURCE_RECOVERY_VERSION
            if rule_fix_source_recovery_complete
            else ""
        ),
        "allocation_profile_version": str(CONFIG.get("allocation_profile_version", "")),
        "scan_state": state,
        "zero_config_scan": True,
        "admission_profile": str(CONFIG.get("admission_profile", "balanced_relevance_v15_scan_repair")),
        "scan_health": health,
        "scan_window": {
            "ab_date_floor": DATE_FLOOR.isoformat(),
            "ab_preferred_floor": DATE_FLOOR.isoformat(),
            "ab_extended_highest_floor": EXTENDED_DATE_FLOOR.isoformat(),
            "extended_highest_sources_planned": len(extended_highest_batch),
            "extended_highest_sources_executed": extended_highest_executed,
            "ab_discovery_from_this_run": min(oa_from, cr_from, inst_from).isoformat(),
            "frontier_gap_scholarly_from": gap_from.isoformat() if gap_scholarly else "",
            "frontier_gap_historical_lookback_months": gap_lookback_months if gap_scholarly else 0,
            "openalex_from": oa_from.isoformat(),
            "crossref_from": cr_from.isoformat(),
            "historical_exploration_from": DATE_FLOOR.isoformat(),
            "institutions_from": inst_from.isoformat(),
            "rule_fix_new_source_recovery_from": DATE_FLOOR.isoformat() if rule_fix_source_recovery_attempted else "",
            "rule_fix_new_source_recovery_this_run": rule_fix_source_recovery_attempted,
            "ab_four_month_backfill_this_run": bootstrap_ab,
            "c_window_start": (now - dt.timedelta(hours=news_lookback)).isoformat(timespec="minutes").replace("+00:00", "Z"),
            "c_window_end": now_iso,
            "c_discovery_lookback_hours": news_lookback,
            "c_retention_floor": SIGNAL_RETENTION_FLOOR.isoformat(),
            "c_retention_months": WEAK_SIGNAL_RETENTION_MONTHS,
            "c_evidence_status": "low",
            "c_recovery_backfill_this_run": signal_backfill,
        },
        "scan_results": {
            "new_a": new_a_count,
            "new_b": new_b_count,
            "new_ab_unique": len(new_selected),
            "new_c": new_c_count,
            "aged_out_this_scan": {k: int(v) for k, v in age_window_removed.items()},
            "aged_out_total_this_scan": int(sum(age_window_removed.values())),
            "extended_highest_retained_a": int(extended_a_kept),
            "extended_highest_retained_b": int(extended_b_kept),
            "extended_highest_new_candidates": int(len(extended_highest_candidates)),
            "c_signals": new_c_count,
            "c_signals_total": len(strand_c),
            "c_prefilter_candidates": len(news),
            "c_anchored_candidates": len(current_c),
            "b_method_queries_this_scan": len(b_method_focus),
            "foresight_author_followup": {
                "bank": len(foresight_author_bank),
                "planned": len(foresight_author_batch),
                "executed": foresight_author_executed_count,
                "admitted_candidates": foresight_author_candidates_count,
            },
            "weak_signal_evidence_followup": dict(signal_evidence_followup_stats),
            "curator_candidate_testing": {
                "batch_id": clean_text(curator_candidate_testing_state.get("batch_id")) if isinstance(curator_candidate_testing_state, dict) else "",
                "attempted": int(curator_candidate_testing_state.get("attempted_this_scan", 0) or 0) if isinstance(curator_candidate_testing_state, dict) else 0,
                "admitted_candidates": int(curator_candidate_testing_state.get("admitted_candidates_this_scan", 0) or 0) if isinstance(curator_candidate_testing_state, dict) else 0,
                "matrix_placed": int(curator_candidate_testing_state.get("matrix_placed", 0) or 0) if isinstance(curator_candidate_testing_state, dict) else 0,
            },
            "citation_snowball": snowball_stats,
            "finding_context_queries_this_scan": finding_context_focus,
            "finding_context_queries_executed": finding_context_executed,
            "note_a": f"This scan added {new_a_count} new Strand A item(s). Earlier accepted items remain in the corpus." if new_a_count < 3 else "",
            "note_b": f"This scan added {new_b_count} new Strand B item(s). Earlier accepted items remain in the corpus." if new_b_count < 3 else "",
            "note_c": f"This scan added {new_c_count} new weak signal(s). Strand C remains low evidence and is retained for six months." if new_c_count < 3 else "",
            "frontier_gap_targets": frontier_focus["targets"],
            "frontier_gap_deficits": {k: frontier_focus.get("deficits", {}).get(k, 0) for k in frontier_focus["targets"]},
            "frontier_gap_target_count": frontier_focus.get("target_count", 3),
            "matrix_balance_rotation_mode": str(CONFIG.get("matrix_balance_rotation_mode", "recurring_every_scan")),
            "rotation_dimensions": list(CONFIG.get("rotation_dimensions", [])),
            "frontier_empty_cells_before_scan": frontier_focus["empty_cells"],
            "rotation_note": (
                "Fresh-window scanning, recurring Matrix-balance targeting and full-window exploration were active together. "
                "Full-window exploration rotated through: " + ", ".join(exploration.get("themes", [])) + "."
                + (
                    " The early scholarly slice was low-yield, so another full-window slice was tried: "
                    + ", ".join(quiet_rescue.get("themes", [])) + "."
                    if quiet_rescue.get("attempted") else ""
                )
                + (
                    " The completed normal pass still produced three or fewer genuinely new A/B items, so a fresh unexecuted query rotation was forced: "
                    + ", ".join(low_yield_rotation.get("fresh_themes", [])) + "."
                    if low_yield_rotation.get("triggered") else ""
                )
                + (
                    f" Yield remained at or below {low_yield_threshold}, so the 4-6 month Highest source-merit fallback was also attempted."
                    if low_yield_rotation.get("extended_fallback_attempted") else ""
                )
            ) if exploration.get("themes") else "Fresh-window scanning was active; no full-window exploration query was configured.",
            "historical_exploration": {
                "from": DATE_FLOOR.isoformat(),
                "openalex_queries": oa_explore,
                "crossref_queries": cr_explore,
                "themes": exploration.get("themes", []),
            },
            "quiet_scan_rescue": quiet_rescue,
            "low_yield_rotation": low_yield_rotation,
            "rejection_funnel": rejection_funnel,
            "full_rescue_run_recommended": bool(low_yield_rotation.get("full_rescue_run_recommended")),
            "matrix_first_deepening": deepening,
        },
        "strand_a": strand_a,
        "strand_b": strand_b,
        "strand_c": strand_c,
        "frontier_evidence": frontier_evidence,
        "stats": {
            "openalex_admitted_before_dedupe": len(oa),
            "openalex_public_anonymous": not bool(OPENALEX_API_KEY),
            "openalex_api_key_configured": bool(OPENALEX_API_KEY),
            "curator_candidate_tests_attempted": int(execution_stats.get("curator_candidate_tests_attempted", 0)),
            "curator_candidate_tests_admitted": int(execution_stats.get("curator_candidate_tests_admitted", 0)),
            "curator_candidate_tests_matrix_placed": int(curator_candidate_testing_state.get("matrix_placed", 0) or 0) if isinstance(curator_candidate_testing_state, dict) else 0,
            "crossref_admitted_before_dedupe": len(cr),
            "crossref_public_anonymous": True,
            "institutional_admitted_before_dedupe": len(inst),
            "manual_recovery_urls_attempted": int(execution_stats.get("manual_recovery_urls_attempted", 0)),
            "manual_recovery_admitted": int(execution_stats.get("manual_recovery_admitted", 0)),
            "manual_recovery_queue_remaining": len(manual_ingest_state.get("recovery_queue", [])) if manual_ingest_state else 0,
            "scholarly_queries_a": len(CONFIG.get("queries_a", [])),
            "scholarly_queries_b": len(CONFIG.get("queries_b", [])),
            "openalex_queries_this_run": len(oa_batch),
            "openalex_queries_executed": len(set(execution_stats.get("openalex_queries", set()))),
            "openalex_base_queries_executed": oa_base_executed,
            "openalex_exploration_queries_this_run": len(oa_explore),
            "finding_context_queries_this_run": len(finding_context_focus),
            "finding_context_queries_executed": finding_context_executed,
            "openalex_exploration_queries_executed": oa_explore_executed + int(execution_stats.get("quiet_rescue_openalex_executed", 0)),
            "openalex_missing_abstract_enrichment_attempted": int(execution_stats.get("openalex_abstracts_enrichment_attempted", 0)),
            "citation_snowball_seeds_resolved": int(snowball_stats.get("seeds_resolved", 0) or 0),
            "citation_snowball_shared_references": int(snowball_stats.get("shared_references", 0) or 0),
            "citation_snowball_anchors_selected": int(snowball_stats.get("anchors_selected", 0) or 0),
            "citation_snowball_forward_queries": int(snowball_stats.get("forward_queries", 0) or 0),
            "citation_snowball_admitted": int(snowball_stats.get("admitted_unique", 0) or 0),
            "crossref_broad_queries_this_run": len(cr_batch),
            "crossref_broad_queries_executed": len(set(execution_stats.get("crossref_broad_queries", set()))),
            "crossref_base_queries_executed": cr_base_executed,
            "crossref_exploration_queries_this_run": len(cr_explore),
            "crossref_exploration_queries_executed": cr_explore_executed + int(execution_stats.get("quiet_rescue_crossref_executed", 0)),
            "quiet_scan_rescue_attempted": bool(quiet_rescue.get("attempted")),
            "quiet_scan_rescue_queries": len(quiet_rescue.get("openalex_queries", [])) + len(quiet_rescue.get("crossref_queries", [])),
            "low_yield_rotation_triggered": bool(low_yield_rotation.get("triggered")),
            "low_yield_new_ab_before": int(low_yield_rotation.get("new_ab_before", 0)),
            "low_yield_new_ab_after_fresh_rotation": int(low_yield_rotation.get("new_ab_after_fresh_rotation", 0)),
            "low_yield_new_ab_after_extended_fallback": int(low_yield_rotation.get("new_ab_after_extended_fallback", 0)),
            "low_yield_fresh_openalex_queries_executed": int(execution_stats.get("low_yield_fresh_openalex_executed", 0)),
            "low_yield_fresh_crossref_queries_executed": int(execution_stats.get("low_yield_fresh_crossref_executed", 0)),
            "low_yield_extended_fallback_attempted": bool(low_yield_rotation.get("extended_fallback_attempted")),
            "low_yield_extended_openalex_queries_executed": int(execution_stats.get("low_yield_extended_openalex_executed", 0)),
            "low_yield_extended_crossref_queries_executed": int(execution_stats.get("low_yield_extended_crossref_executed", 0)),
            "low_yield_extended_highest_admitted": int(low_yield_rotation.get("extended_highest_admitted", 0)),
            "crossref_priority_tasks_this_run": len(cr_priority_batch),
            "crossref_priority_tasks_executed": cr_priority_executed,
            "crossref_source_journals_this_run": len(cr_source_batch),
            "crossref_source_journals_executed": cr_source_executed,
            "recall_backfill_this_run": bool(state.get("recall_reset_this_run")),
            "crossref_missing_abstract_enrichment_attempted": int(execution_stats.get("crossref_abstracts_enrichment_attempted", 0)),
            "b_method_queries_executed": b_method_executed,
            "institution_sources_this_run": len(inst_batch),
            "extended_highest_sources_planned": len(extended_highest_batch),
            "extended_highest_sources_executed": extended_highest_executed,
            "extended_highest_candidates_admitted": len(extended_highest_candidates),
            "institution_rotating_sources_executed": inst_base_executed,
            "institution_source_adapter_sources_planned": len(adapter_domain_batch),
            "institution_source_adapter_sources_executed": adapter_sources_executed,
            "institution_source_adapter_jobs_queued": int(ADMISSION_DIAGNOSTICS.get("institution_adapter_jobs", 0) or 0),
            "metadata_text_rescue_queued": int(rejection_funnel.get("metadata_text_rescue", {}).get("queued", 0)),
            "metadata_text_rescue_attempted": int(rejection_funnel.get("metadata_text_rescue", {}).get("attempted", 0)),
            "metadata_text_rescue_recovered": int(rejection_funnel.get("metadata_text_rescue", {}).get("text_recovered", 0)),
            "metadata_text_rescue_admitted": int(rejection_funnel.get("metadata_text_rescue", {}).get("admitted_after_recovery", 0)),
            "full_rescue_run_recommended": bool(low_yield_rotation.get("full_rescue_run_recommended")),
            "rule_fix_new_source_recovery_attempted": rule_fix_source_recovery_attempted,
            "rule_fix_new_source_recovery_complete": rule_fix_source_recovery_complete,
            "rule_fix_new_source_recovery_sources_attempted": int(execution_stats.get("rule_fix_source_recovery_sources_attempted", 0)),
            "rule_fix_new_source_recovery_jobs": int(execution_stats.get("rule_fix_source_recovery_jobs", 0)),
            "rule_fix_new_source_recovery_admitted_ab": int(execution_stats.get("rule_fix_source_recovery_admitted_ab", 0)),
            "known_ab_identities_loaded": len(KNOWN_AB_IDENTITIES),
            "known_ab_links_loaded": len(KNOWN_AB_LINKS),
            "known_signal_identities_loaded": len(KNOWN_SIGNAL_IDENTITIES),
            "institution_page_fingerprints_cached": len(INSTITUTION_SEEN_FINGERPRINTS),
            "institution_sources_configured": len(CONFIG.get("institution_sources", [])),
            "major_scholarly_publishers_tracked": len(CONFIG.get("major_scholarly_publishers", [])),
            "priority_journals_tracked": len(CONFIG.get("crossref_priority_journals", [])),
            "priority_journal_queries": len(CONFIG.get("crossref_priority_journal_queries", [])),
            "foresight_author_bank": len(foresight_author_bank),
            "foresight_author_planned": len(foresight_author_batch),
            "foresight_author_executed": foresight_author_executed_count,
            "foresight_author_candidates": foresight_author_candidates_count,
            "weak_signal_evidence_signals_checked": int(signal_evidence_followup_stats.get("signals_checked", 0)),
            "weak_signal_evidence_links_examined": int(signal_evidence_followup_stats.get("links_examined", 0)),
            "weak_signal_evidence_direct_ab": int(signal_evidence_followup_stats.get("direct_ab", 0)),
            "weak_signal_evidence_queries": int(signal_evidence_followup_stats.get("queries", 0)),
            "weak_signal_evidence_scholarly_ab": int(signal_evidence_followup_stats.get("scholarly_ab", 0)),
            "source_expansion_backfill": bootstrap_ab,
            "backfill_complete": backfill_complete,
            "unique_ab_candidates_before_scan_limit": len(deduped),
            "news_candidates_current_window": len(news),
            "news_admitted_current_window": len(current_c),
            "news_lookback_hours": news_lookback,
            "news_sources_configured": len(CONFIG.get("news_sources", [])),
            "news_global_queries_configured": len(CONFIG.get("news_global_queries", [])),
            "frontier_gap_queries_this_run": len(frontier_focus["queries"]),
            "frontier_gap_scholarly_queries_this_run": len(frontier_focus.get("scholarly_queries", [])),
            "frontier_gap_scholarly_from": gap_from.isoformat() if gap_scholarly else "",
            "frontier_gap_targets_this_run": len(frontier_focus["targets"]),
            "frontier_gap_query_cursor_cells": len(state.get("frontier_gap_query_cursors", {})),
            "frontier_gap_source_cursor_cells": len(state.get("frontier_gap_source_cursors", {})),
            "openalex_depth_queries_tracked": len(state.get("result_depth", {}).get("openalex", {})),
            "crossref_broad_depth_queries_tracked": len(state.get("result_depth", {}).get("crossref_broad", {})),
            "openalex_exploration_depth_queries_tracked": sum(1 for k in state.get("result_depth", {}).get("openalex", {}) if str(k).startswith("explore::")),
            "crossref_exploration_depth_queries_tracked": sum(1 for k in state.get("result_depth", {}).get("crossref_broad", {}) if str(k).startswith("explore::")),
            "crossref_priority_depth_tasks_tracked": len(state.get("result_depth", {}).get("crossref_priority", {})),
            "frontier_qualifying_before_scan": frontier_focus["qualifying"],
            "frontier_empty_cells_before_scan": frontier_focus["empty_cells"],
            "frontier_empty_cells_targeted": len(frontier_focus.get("empty_targets", [])),
            "frontier_gap_depth_waves": int(deepening.get("waves", 0)),
            "frontier_gap_depth_queries_executed": int(deepening.get("gap_queries_executed", 0)),
            "weak_signal_followup_candidates": int(deepening.get("weak_signal_followup_candidates", 0)),
            "institution_signal_candidates": len(INSTITUTION_SIGNAL_CANDIDATES),
            "frontier_stubborn_recovery_candidates": int(deepening.get("stubborn_recovery_candidates", 0)),
            "frontier_stubborn_recovery_queries_executed": int(deepening.get("stubborn_recovery_queries_executed", 0)),
            "frontier_evidence_total": len(frontier_evidence),
            "frontier_coverage_classifier_ok": not bool(frontier_focus["classifier_error"]),
            "signal_recovery_backfill": signal_backfill,
            "signal_backfill_complete": signal_backfill_complete,
            "age_window_removed_a": int(age_window_removed.get("strand_a", 0)),
            "age_window_removed_b": int(age_window_removed.get("strand_b", 0)),
            "age_window_removed_c": int(age_window_removed.get("strand_c", 0)),
            "age_window_removed_frontier": int(age_window_removed.get("frontier_evidence", 0)),
            "quality_removed_old_a": inherited_audit_stats.get("strand_a_removed", 0) if (inherited_audit or precision_cleanup) else 0,
            "quality_removed_old_b": inherited_audit_stats.get("strand_b_removed", 0) if (inherited_audit or precision_cleanup) else 0,
            "inherited_corpus_audit_this_run": inherited_audit,
            "precision_corpus_cleanup_this_run": precision_cleanup,
            "precision_signal_cleanup_this_run": signal_cleanup,
            "quality_removed_old_c": signal_cleanup_stats.get("strand_c_removed", 0) if signal_cleanup else 0,
            "precision_signal_cleanup_kept": signal_cleanup_stats.get("strand_c_kept", 0) if signal_cleanup else 0,
            "inherited_corpus_audit_stored_pass": inherited_audit_stats.get("stored_pass", 0) if (inherited_audit or precision_cleanup) else 0,
            "inherited_corpus_audit_refreshed_pass": inherited_audit_stats.get("refreshed_pass", 0) if (inherited_audit or precision_cleanup) else 0,
            "inherited_corpus_audit_refresh_unavailable": inherited_audit_stats.get("refresh_unavailable", 0) if (inherited_audit or precision_cleanup) else 0,
            "source_warnings": len(warnings),
            "transport_failure_warnings": transport_failure_count,
            "scan_budget_seconds": budget_seconds,
            "budget_reached": overall_budget_hit,
            "partial_stage_budget_reached": partial_budget_hit,
            "runtime_seconds": round(time.time() - started, 1),
            "admission_diagnostics": dict(sorted(ADMISSION_DIAGNOSTICS.items())),
            "admission_rejection_funnel": rejection_funnel,
        },
        "scan_diagnostics": {
            "source_warning_count": len(warnings),
            "source_warnings": list(dict.fromkeys(warnings))[:100],
            "transport_failure_warning_count": transport_failure_count,
        },
    }
    normalize_reader_claims(data)
    tmp_out = OUT_PATH.with_suffix(".json.tmp")
    tmp_out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_out.replace(OUT_PATH)
    log_progress(
        f"radar.json written: A={len(strand_a)} B={len(strand_b)} C={len(strand_c)} health={health}; "
        f"next cursors OA={state['openalex_cursor']} CR={state['crossref_broad_cursor']}/{state['crossref_priority_cursor']}/SRC{state['crossref_source_cursor']} INST={state['institution_cursor']}"
    )
    print(json.dumps(data["stats"], indent=2), flush=True)
    if warnings:
        print("Source warnings (first 40):", file=sys.stderr, flush=True)
        for w in warnings[:40]:
            print(" -", w, file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
