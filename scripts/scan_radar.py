#!/usr/bin/env python3
"""R&I × Geopolitics + Foresight Methodology radar scanner (EU-first, balanced).

Key properties
--------------
* No API keys or paid services are required.
* Discovery is broad; admission is selective but not brittle.
* Strand A requires direct EU scope plus substantive R&I evidence and either explicit geopolitical/economic-security evidence or a bounded external-position mechanism (dependence/competition/capability/talent etc.).
* Strand B is a method-development library: a publication must contribute a new, adapted,
  extended, refined or otherwise explicitly developed futures/foresight method, or a genuinely
  forward-looking R&I/technology-analysis method, reusable for understanding the future of Strand A.
  Explicit development language is preferred; method-first papers with validation/transfer evidence can also qualify. Mere application is not enough.
* Strand C is not a general news feed: every admitted item must be a factual current development
  or new evidence/indicator capable of reframing Strand A, with a strong R&I/geopolitical bridge.
  It must be anchored to substantive Strand-A evidence;
  Strand-B methods never serve as weak-signal anchors.
  Once admitted, the signal is retained in the cumulative historical corpus.
* Calls, facility pages, project pages, press releases, news/blog pages, events,
  jobs and other non-analytical material are rejected for A/B.

The scanner aims for high-recall discovery with substantive admission: EU scope + R&I/related-system substance + geopolitics/economic security. It does not pad.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import gzip
import html
import io
import json
import os
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
INHERITED_CORPUS_AUDIT_ENABLED = bool(CONFIG.get("inherited_corpus_audit_enabled", True))
INHERITED_CORPUS_AUDIT_REFRESH = bool(CONFIG.get("inherited_corpus_audit_refresh_failures", True))
INHERITED_CORPUS_AUDIT_FAIL_CLOSED = bool(CONFIG.get("inherited_corpus_audit_fail_closed", True))
SIGNAL_DISCOVERY_VERSION = str(CONFIG.get("signal_discovery_version", "v16-weak-signals"))
SIGNAL_QUALITY_PROFILE_VERSION = str(CONFIG.get("signal_quality_profile_version", SIGNAL_DISCOVERY_VERSION))
SIGNAL_BACKFILL_HOURS = int(CONFIG.get("signal_backfill_hours", 720))
INCREMENTAL_STATE_VERSION = str(CONFIG.get("incremental_state_version", "v17.2-persistent-source-cursors"))
ROTATION_PROFILE_VERSION = str(CONFIG.get("rotation_profile_version", "v17.6.4-fresh-plus-historical-exploration"))
RECALL_PROFILE_VERSION = str(CONFIG.get("recall_profile_version", "v17.7.2-source-first-contextual-recall"))
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
ACTIVE_FRONTIER_GAP_URL_TERMS: list[str] = []
ADMISSION_DIAGNOSTICS: Counter = Counter()
ADMISSION_DIAGNOSTICS_LOCK = threading.Lock()
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
            "strand_b_method_cursor": 0,
            "institution_cursor": 0,
            "frontier_gap_cursor": 0,
            "openalex_explore_cursor": 0,
            "crossref_explore_cursor": 0,
            "frontier_gap_query_cursors": {},
            "frontier_gap_source_cursors": {},
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
    if not isinstance(state.get("frontier_gap_query_cursors"), dict):
        state["frontier_gap_query_cursors"] = {}
    if not isinstance(state.get("frontier_gap_source_cursors"), dict):
        state["frontier_gap_source_cursors"] = {}
    if not isinstance(state.get("result_depth"), dict):
        state["result_depth"] = {}
    for family in ("openalex", "crossref_broad", "crossref_priority"):
        if not isinstance(state["result_depth"].get(family), dict):
            state["result_depth"][family] = {}
    for key in ("openalex", "crossref_broad", "crossref_priority", "institutions"):
        state["backfill"].setdefault(key, False)
        state["completed_cycles"].setdefault(key, 0)
        state["cycle_failed"].setdefault(key, False)
    for key in ("openalex_cursor", "crossref_broad_cursor", "crossref_priority_cursor", "crossref_source_cursor", "strand_b_method_cursor", "institution_cursor", "frontier_gap_cursor"):
        state[key] = int(state.get(key, 0) or 0)

    # Admission recall expansions must re-search previously rejected material. Earlier builds
    # cached rejected institutional URLs and preserved query/depth cursors across gate changes,
    # so a wider classifier could never reconsider much of the corpus it was intended to rescue.
    recall_changed = bool(previous.get("last_updated")) and previous.get("recall_profile_version") != RECALL_PROFILE_VERSION
    if recall_changed:
        for key in ("openalex_cursor", "crossref_broad_cursor", "crossref_priority_cursor", "crossref_source_cursor",
                    "strand_b_method_cursor", "institution_cursor", "openalex_explore_cursor", "crossref_explore_cursor"):
            state[key] = 0
        state["result_depth"] = {"openalex": {}, "crossref_broad": {}, "crossref_priority": {}}
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
    """Allocate extra discovery budget to under-covered Frontier cells.

    Cell scarcity still determines *how much* attention a cell receives, but the
    concrete search formulations are now independently persistent per cell. This
    prevents a permanently sparse cell from restarting at variant 1 on every scan.
    """
    counts, qualifying, error = frontier_matrix_coverage(previous)
    start = int(state.get("frontier_gap_cursor", 0) or 0) % len(FRONTIER_CELL_ORDER)
    cyclic = FRONTIER_CELL_ORDER[start:] + FRONTIER_CELL_ORDER[:start]
    cyclic_rank = {key: i for i, key in enumerate(cyclic)}
    target_count = max(1, int(CONFIG.get("frontier_gap_target_count", 3) or 3))
    deficits = {key: max(0, target_count - counts.get(key, 0)) for key in FRONTIER_CELL_ORDER}
    scarcity_scores = {
        key: round(deficits[key] / target_count + (0.35 if counts.get(key, 0) == 0 else 0.0), 3)
        for key in FRONTIER_CELL_ORDER
    }
    sparse = [key for key in FRONTIER_CELL_ORDER if deficits[key] > 0]
    ordered = sorted(sparse, key=lambda key: (-deficits[key], cyclic_rank[key]))
    target_limit = max(0, min(len(ordered), int(CONFIG.get("frontier_gap_targets_per_scan", 8) or 0)))
    targets = ordered[:target_limit]

    weighted_targets: list[str] = []
    for level in range(target_count, 0, -1):
        for key in targets:
            if deficits[key] >= level:
                weighted_targets.append(key)
    if targets:
        last_index = FRONTIER_CELL_ORDER.index(targets[-1])
        state["frontier_gap_cursor"] = (last_index + 1) % len(FRONTIER_CELL_ORDER)

    query_cursors = state.setdefault("frontier_gap_query_cursors", {})
    if not isinstance(query_cursors, dict):
        query_cursors = {}
        state["frontier_gap_query_cursors"] = query_cursors

    # News gap queries: one formulation per selected cell per run, but resume from
    # that cell's own saved variant next time.
    profiles = CONFIG.get("frontier_gap_search_queries", {})
    news_limit = max(0, int(CONFIG.get("frontier_gap_queries_per_scan", 8) or 0))
    queries: list[str] = []
    news_used: dict[str, str] = {}
    for key in targets:
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
            news_used[key] = chosen[0]
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
    for key in weighted_targets:
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
        "deficits": deficits,
        "scarcity_scores": scarcity_scores,
        "targets": targets,
        "weighted_targets": weighted_targets,
        "queries": queries,
        "news_query_cells": news_used,
        "scholarly_queries": scholarly_queries,
        "scholarly_query_cells": scholarly_cells,
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
]
RESEARCH_TALENT_FLOW_EXPLICIT = [
    "research brain drain", "academic brain drain", "scientific brain drain", "brain drain",
    "research brain gain", "academic brain gain", "scientific brain gain", "brain gain",
    "researcher mobility", "researchers mobility", "scientist mobility", "scientific mobility",
    "research talent mobility", "scientific talent mobility",
    "researcher migration", "scientist migration",
    "research talent outflow", "scientific talent outflow", "researcher outflow",
    "research talent inflow", "scientific talent inflow", "researcher inflow",
]
RESEARCH_TALENT_FLOW_ACTIONS = [
    "attract research talent", "attract researchers", "attract scientists", "retain research talent",
    "retain researchers", "retain scientists", "researcher retention", "scientist retention",
    "recruit researchers", "recruit scientists", "return mobility", "returning researchers",
    "researchers leave", "researchers leaving", "scientists leave", "scientists leaving",
    "researchers relocate", "scientists relocate", "move abroad", "moving abroad",
    "work abroad", "emigrate", "emigration", "immigrate", "immigration",
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
NEWS_EXCLUDE = [
    "opinion", "commentary", "editorial", "analysis:", "analysis -", "column", "viewpoint",
    "podcast", "book review", "letter to the editor", "letters to the editor", "explainer",
    "interview", "comment:", "comment -",
    # V17.5.3: weak signals are developments, not individual career listings.
    "job with", "job opening", "job vacancy", "vacancy", "career opportunity",
    "doctoral researcher in", "phd position", "postdoctoral position", "postdoc position",
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
    "critical and emerging technologies": ["critical technology", "critical technologies", "emerging technology", "semiconductor", "chips", "quantum", "biotech", "artificial intelligence", " ai "],
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
    if has_eu_word(title):
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
        bare_eu = has_eu_word(sent)
        ri_here = bool(distinct_matches(sent, RI_STRONG + RI_GENERIC))
        geo_here = bool(distinct_matches(sent, GEO_STRONG)) or china_geo_signal(sent) or research_talent_flow_signal(sent)
        if sent_direct:
            return "direct", list(dict.fromkeys(sent_direct))[:4]
        if bare_eu and ri_here:
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
    eu_count = len(re.findall(r"\beu\b", normalized(full)))
    # Body-only scope must be explicit/repeated.  Merely mentioning two European
    # countries somewhere in a long document is no longer treated as EU scope.
    if strong_body_scope or eu_count >= 2:
        evidence = strong_body_scope + direct_body
        return "direct", list(dict.fromkeys(evidence))[:4]

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
        if contains_any(sent, EU_GENERIC) or bool(bounded_matches(sent, MEMBER_STATE_SCOPE)) or has_eu_word(sent):
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
    """Detect cross-border *research-workforce* allocation, not generic student mobility.

    Knowledge & people is about researchers/scientists and the research system.  Earlier
    builds treated phrases such as ``academic mobility`` in Erasmus/student papers as
    geopolitical research-talent evidence.  Require an explicit research-workforce cue
    whenever the wording could describe students or education generally.
    """
    low = normalized(text)
    explicit = distinct_matches(low, RESEARCH_TALENT_FLOW_EXPLICIT)
    actors = distinct_matches(low, RESEARCH_TALENT_ACTORS)
    actions = distinct_matches(low, RESEARCH_TALENT_FLOW_ACTIONS)
    research_workforce = bool(actors or contains_any(low, [
        "research career", "research careers", "research workforce", "scientific workforce",
        "research talent", "scientific talent", "postdoc", "postdoctoral", "doctoral researcher",
        "research staff", "academic staff", "faculty", "professor", "professors",
    ]))
    student_focused = contains_any(low, [
        "student mobility", "students mobility", "international students", "student migration",
        "erasmus student", "undergraduate", "master students", "masters students", "student experience",
    ])
    if student_focused and not research_workforce:
        return False
    if explicit:
        # Generic brain drain/gain needs a research-workforce actor.  Researcher/scientist
        # mobility/outflow/inflow is already specific enough by construction.
        generic_brain = any(x in explicit for x in ("brain drain", "brain gain"))
        specific_research_flow = any(
            x.startswith("researcher") or x.startswith("scientist") or
            x.startswith("research talent") or x.startswith("scientific talent") or
            x.startswith("research brain") or x.startswith("scientific brain")
            for x in explicit
        )
        if generic_brain and not specific_research_flow and not research_workforce:
            return False
        return True
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
        explicit_focus = bool(ri and geo and (ri_ta or geo_ta))

    # Secondary route: direct empirical mechanism of Europe's external R&I position. This route
    # deliberately does not accept generic competitiveness/capacity alone.
    context_text = ta if source_kind == 'scholarly' else lead
    external = distinct_matches(context_text, A_EXTERNAL_RELATION)
    outcomes = distinct_matches(context_text, A_STRATEGIC_RI_OUTCOME)
    contextual_focus = bool(ri_ta and external and outcomes) if source_kind == 'scholarly' else bool(ri and external and outcomes and ri_ta)
    # The contextual route is an expansion route, so page-type noise is fail-closed here.
    # This does not affect explicit A evidence or Strand B method papers whose abstracts may
    # legitimately mention workshops, calls, facilities or other methodological context.
    if contextual_focus and document_exclusion_reason(title, context_text):
        contextual_focus = False

    focus = bool(explicit_focus or contextual_focus)
    route = 'explicit-geopolitics' if explicit_focus else ('external-position-evidence' if contextual_focus else '')
    context_evidence = list(dict.fromkeys(external + outcomes))[:6] if contextual_focus else []
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

def gate_scope(title: str, abstract: str, body: str, source_tier: int, source_kind: str = 'general') -> dict[str, Any]:
    """Classify the three-layer radar model.

    A = substantive papers about EU R&I in a geopolitical/economic-security context.
    B = developed/adapted/extended/refined futures methods, plus forward-looking R&I/technology-analysis methods, reusable for understanding the future of A.
    C is handled separately in the current-development scanner and never admitted here.
    """
    title = clean_text(title)
    abstract = clean_text(abstract)
    body = clean_text(body)

    a_focus, ri_hits, geo_hits, a_bridge, a_route, a_context = _a_focus_ok(title, abstract, body, source_kind)
    eu_rel, eu_hits = eu_evidence(title, abstract, body)
    # A is precision-first: the paper must actually be Europe/EU/member-state scoped.
    a_pass = bool(a_focus and eu_rel == 'direct')

    b_pass, b_families, b_bridge, b_suitability, b_route = _b_method_evidence(
        title, abstract, body, source_kind, source_tier
    )

    return {
        'a_pass': a_pass,
        'b_pass': b_pass,
        'eu_relevance': eu_rel if a_pass else ('derived' if b_pass else None),
        'eu_evidence': eu_hits if a_pass else (['method suitable for analysing future EU R&I/geopolitics'] if b_pass else []),
        'ri_evidence': ri_hits[:5],
        'geo_evidence': geo_hits[:5],
        'bridge_sentence': a_bridge,
        'a_route': a_route if a_pass else '',
        'a_context_evidence': a_context if a_pass else [],
        'bridge_supported': bool(a_bridge or (ri_hits and geo_hits)),
        'bridge_mode': 'sentence' if a_bridge else ('title/abstract' if a_pass else ''),
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


def _diag_inc(key: str, amount: int = 1) -> None:
    with ADMISSION_DIAGNOSTICS_LOCK:
        ADMISSION_DIAGNOSTICS[key] += amount


def _record_ab_gate_diagnostic(prefix: str, ev: dict[str, Any]) -> None:
    _diag_inc(f"{prefix}_evaluated")
    if ev.get("a_pass") or ev.get("b_pass"):
        _diag_inc(f"{prefix}_admitted_gate")
        if ev.get("a_route"):
            _diag_inc(f"{prefix}_a_route_{ev.get('a_route')}")
        return
    if ev.get("eu_relevance") != "direct":
        _diag_inc(f"{prefix}_reject_no_direct_eu")
    elif not ev.get("ri_evidence"):
        _diag_inc(f"{prefix}_reject_no_ri")
    else:
        _diag_inc(f"{prefix}_reject_no_strategic_context")


def candidate_from_openalex(work: dict[str, Any], date_floor: dt.date | None = None) -> dict[str, Any] | None:
    title = clean_text(work.get("display_name"))
    abstract = openalex_abstract(work.get("abstract_inverted_index"))
    date = parse_date(work.get("publication_date"))
    effective_floor = date_floor or DATE_FLOOR
    if not title or not date or date < effective_floor or date > dt.date.today():
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
        text=full, doi=doi, preprint=is_preprint,
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

    def convert_works(works: list[dict[str, Any]], query_from: dt.date) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for work in works:
            if bool(CONFIG.get("skip_known_items_before_classification", True)):
                title0 = clean_text(work.get("title") or work.get("display_name"))
                doi0 = clean_text(work.get("doi"))
                if stable_item_identity(title0, doi0) in KNOWN_AB_IDENTITIES:
                    continue
            item = candidate_from_openalex(work, date_floor=min(DATE_FLOOR, query_from))
            if item:
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
                r = SESSION.get("https://api.openalex.org/works", params=params, timeout=timeout)
                if r.status_code == 200:
                    works = r.json().get("results", [])
                    return convert_works(works, query_from), None, len(works)
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


def candidate_from_crossref(item: dict[str, Any], date_floor: dt.date | None = None) -> dict[str, Any] | None:
    title = clean_text((item.get("title") or [""])[0])
    abstract = clean_text(item.get("abstract"))
    date = crossref_date(item)
    effective_floor = date_floor or DATE_FLOOR
    if not title or not date or date < effective_floor or date > dt.date.today():
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
        doi=doi, preprint=preprint,
    )


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

    def convert_items(works: list[dict[str, Any]], query_from: dt.date, q: str = "", journal: str = "") -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        task_key = f"{journal} || {q}" if journal else q
        for raw_item in works:
            item = raw_item
            if bool(CONFIG.get("skip_known_items_before_classification", True)):
                titles0 = item.get("title") or []
                title0 = clean_text(titles0[0] if isinstance(titles0, list) and titles0 else titles0)
                doi0 = clean_text(item.get("DOI"))
                if stable_item_identity(title0, doi0) in KNOWN_AB_IDENTITIES:
                    continue
            c = candidate_from_crossref(item, date_floor=min(DATE_FLOOR, query_from))
            if c:
                out.append(c)
                continue

            # Missing abstracts are a metadata problem, not substantive negative evidence.
            # Recover only a tiny number of relevance-ranked records per task so this cannot
            # turn into an uncontrolled publisher crawl or consume the Crossref stage budget.
            abstract0 = clean_text(item.get("abstract"))
            doi0 = clean_text(item.get("DOI"))
            title0 = clean_text((item.get("title") or [""])[0])
            if (
                not abstract0 and doi0 and title0 and enrichment_total[0] < enrichment_limit
                and enrichment_by_task[task_key] < 2
                and not document_exclusion_reason(title0, "")
            ):
                ok0, _, _, _, _, _ = quality_from_crossref(item)
                if ok0:
                    enrichment_total[0] += 1
                    enrichment_by_task[task_key] += 1
                    recovered = doi_landing_abstract(doi0, enrichment_timeout)
                    if recovered:
                        item = dict(item)
                        item["abstract"] = recovered
                        c = candidate_from_crossref(item, date_floor=min(DATE_FLOOR, query_from))
                        if c:
                            c["metadata_note"] = "Abstract recovered from DOI publisher metadata before admission."
                            out.append(c)
        return out

    def fetch_page(q: str, journal: str, offset: int, lane: str) -> tuple[list[dict[str, Any]], str | None, int]:
        if stage_deadline_reached(stage_deadline, int(CONFIG.get("network_reserve_seconds", 90))):
            return [], "budget", 0
        mark_executed(q, journal)
        query_from = (query_dates_override or {}).get(q, from_date) if not journal else from_date
        page_rows = priority_rows if journal else rows
        params = {
            "query.bibliographic": q,
            "filter": f"from-pub-date:{query_from.isoformat()},until-pub-date:{dt.date.today().isoformat()}",
            "rows": page_rows,
            "offset": max(0, int(offset)),
            "select": "DOI,title,author,publisher,container-title,published-online,published-print,published,issued,type,URL,abstract,score",
        }
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
    # Sparse Frontier cells also steer institutional discovery.  This is ranking,
    # not admission: a talent/brain-drain URL is fetched earlier but still has to
    # pass the same substantive A/B gate as every other page.
    gap_hits = sum(1 for term in ACTIVE_FRONTIER_GAP_URL_TERMS if normalized(term) in low)
    score += min(18, 6 * gap_hits)
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


def collect_institutions(from_date: dt.date, warnings: list[str], bootstrap: bool = False, sources_override: list[dict[str, Any]] | None = None, stage_deadline: float | None = None, execution_stats: dict[str, Any] | None = None) -> list[dict[str, Any]]:
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
            futs.append(ex.submit(_discover_domain, src, from_date, bootstrap, stage_deadline))
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
    if isinstance(execution_stats, dict):
        execution_stats.setdefault("institution_sources", set()).update(x for x in submitted_sources if x)
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


def relevance_note(evidence: dict[str, Any], strand: str) -> str:
    eu = (evidence.get("eu_relevance") or "unknown").capitalize()
    if strand == "A":
        ri = ", ".join(evidence.get("ri_evidence", [])[:2]) or "substantive R&I evidence"
        geo = ", ".join(evidence.get("geo_evidence", [])[:2]) or "substantive strategic evidence"
        bridge = evidence.get("bridge_mode") or "supported"
        eu_scope = ", ".join(evidence.get("eu_evidence", [])[:2]) or "scope established"
        return f"{eu} EU relevance ({eu_scope}); R&I evidence: {ri}; strategic evidence: {geo}; bridge: {bridge}."
    if strand == "B":
        method = ", ".join(evidence.get("method_evidence", [])[:2]) or "substantive foresight method"
        suitable = ', '.join(evidence.get('b_suitability_evidence', [])[:2]) or 'strategic/public-policy futures'
        return f"Method contribution for understanding the future of Strand A ({method}); suitable context: {suitable}."
    return f"Qualifies independently as Strand A evidence and as a Strand B future-method contribution ({eu} EU scope for A)."


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
            if not INHERITED_CORPUS_AUDIT_FAIL_CLOSED:
                keepers[strand_key].append(item)
                continue

        key = "strand_a_removed" if strand_key == "strand_a" else "strand_b_removed"
        stats[key] += 1

    out["strand_a"] = keepers["strand_a"]
    out["strand_b"] = keepers["strand_b"]
    if warnings is not None and stats["refresh_unavailable"]:
        warnings.append(
            f"Inherited-corpus audit could not refresh {stats['refresh_unavailable']} failed saved record(s); "
            + ("strict audit removed them" if INHERITED_CORPUS_AUDIT_FAIL_CLOSED else "they were conservatively retained")
        )
    return out, stats


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


def signals_near_duplicate(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ta, tb = _signal_tokens(a.get('headline','')), _signal_tokens(b.get('headline',''))
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    union = len(ta | tb)
    j = inter / max(1, union)
    containment = inter / max(1, min(len(ta), len(tb)))
    return j >= 0.72 or (inter >= 5 and containment >= 0.82)


def signal_identity(item: dict[str, Any]) -> str:
    """Stable event-level identity for Strand C, independent of publisher syndication."""
    if not isinstance(item, dict):
        return 'signal-link:'
    headline = canonical_signal_headline(item.get('headline', ''))
    if headline:
        return f'signal:{headline}'
    link = normalized(item.get('link', ''))
    return f'signal-link:{link}'


def merge_signal_corpus(previous: list[dict[str, Any]], new_items: list[dict[str, Any]], now_iso: str) -> list[dict[str, Any]]:
    """Keep cumulative C while collapsing repeated coverage of the same weak signal."""
    merged: list[dict[str, Any]] = []
    for old in previous:
        if not isinstance(old, dict):
            continue
        x = dict(old)
        x['new_this_scan'] = False
        if any(signals_near_duplicate(x, y) for y in merged):
            continue
        merged.append(x)

    new_ids: set[str] = set()
    for item in new_items:
        if not isinstance(item, dict):
            continue
        if any(signals_near_duplicate(item, y) for y in merged):
            continue
        x = dict(item)
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
    """Current C gate for saved records; B/watch-theme anchors are invalid in the ABC model."""
    if not isinstance(item, dict):
        return False
    headline=clean_text(item.get('headline',''))
    if not headline:
        return False
    if '(strand b)' in normalized(item.get('anchor','')) or normalized(item.get('anchor_basis','')) == 'watch-theme':
        return False
    desc=clean_text(item.get('signal_note','') or item.get('why_it_matters',''))
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
        "research program", "university research", "academic research",
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
        # Derived-Europe is only for empirical/reframing evidence, never for a generic foreign
        # technology launch. Specific A anchoring later in the pipeline is still mandatory.
        derived_themes = {
            "fragmentation of global science", "transatlantic / US–China S&T competition",
            "export controls / dual use", "critical and emerging technologies",
            "R&I competitiveness / technological capabilities", "supply chains / strategic dependencies",
            "economic security and R&I",
        }
        if not (reframing_signal_text(full) and core_ri and strategic_frame and (found & derived_themes)):
            return False

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
        "critical technology", "critical technologies",
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
]


def weak_signal_candidate_text(title: str, desc: str = '') -> bool:
    """A C item may be an early change indicator or new evidence that reframes Strand A."""
    full = normalized(f'{title} {desc}')
    early = contains_any(full, WEAK_SIGNAL_MARKERS)
    reframing = reframing_signal_text(full)
    if not (early or reframing):
        return False
    # Mature implementation is normally not a weak signal. New evidence/indicators are a separate
    # interpretive route, and counter-signals such as delays/opt-outs remain valid early signals.
    mature = contains_any(full, MATURE_SIGNAL_MARKERS)
    counter = contains_any(full, ['delay','delayed','postpone','pause','exception','waiver','limited to','targeted','opts out','declines to','does not include',"doesn't include"])
    if mature and not counter and not reframing:
        return False
    return True

def factual_news(title: str, desc: str) -> bool:
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
    signal updates. A signal can anchor to one A publication or to a recurring A theme.
    """
    internals = [internalize_previous(x) for x in a_corpus if isinstance(x, dict)]
    internals = [x for x in internals if identity(x) != 'title:']
    theme_counts = Counter(t for x in internals for t in x.get('_themes', []))
    recurring = {t for t,c in theme_counts.items() if c >= 2}
    anchored=[]
    for n in news:
        if not weak_signal_candidate_text(n.get('headline',''), n.get('_desc','')):
            continue
        nthemes=set(n.get('_themes',[])) & WATCH_SIGNAL_THEMES
        if not nthemes:
            continue
        ntok=tokens(n.get('headline','')+' '+n.get('_desc',''))
        nentities=set(n.get('_entities',[]))
        best=None
        for a in internals:
            athemes=set(a.get('_themes',[]))
            shared=nthemes & athemes
            if not shared:
                continue
            atok=tokens(a.get('title','')+' '+a.get('summary',''))
            jacc=len(ntok & atok)/max(1,len(ntok | atok))
            aentities=set(distinct_matches(a.get('title','')+' '+a.get('summary',''), ENTITY_TERMS+GEO_ACTORS))
            entity_overlap=len(nentities & aentities)
            broad_only=shared=={'critical and emerging technologies'}
            if broad_only and entity_overlap==0 and jacc<0.055:
                continue
            score=3.0*len(shared)+1.5*entity_overlap+8.0*jacc
            if any(t in SPECIFIC_ANCHOR_THEMES for t in shared): score+=1.0
            if best is None or score>best[0]: best=(score,a,sorted(shared))
        anchor=''; score=0.0; shared_themes=[]; anchor_basis=''
        if best and best[0] >= 2.45:
            score,a,shared_themes=best
            anchor=f"{a['title']} (Strand A)"
            anchor_basis='publication'
        else:
            common=sorted(nthemes & recurring)
            if common:
                theme=common[0]
                supporting=[x['title'] for x in internals if theme in x.get('_themes',[])][:2]
                if supporting:
                    shared_themes=[theme]
                    score=2.45+0.4*min(2,len(supporting))
                    anchor=f"Recurring Strand-A theme: {theme} — supported by {'; '.join(supporting)}"
                    anchor_basis='A-theme'
        if not anchor:
            continue
        text=n.get('headline','')+' '+n.get('_desc','')
        relation=signal_relation(text)
        kind=signal_kind(text)
        theme=shared_themes[0] if shared_themes else sorted(nthemes)[0]
        what=clean_text(n.get('headline',''))
        why=signal_why(theme,kind)
        item={k:v for k,v in n.items() if not k.startswith('_')}
        item.update({
            'anchor':anchor,
            'anchor_basis':anchor_basis,
            'watch_theme':theme,
            'signal_type':relation,
            'signal_kind':kind,
            'what':what,
            'why_it_matters':why,
            'signal_note':what.rstrip('. ')+'. '+why,
            '_anchor_score':score,
        })
        if any(signals_near_duplicate(item,x) for x in anchored):
            continue
        anchored.append(item)
    anchored.sort(key=lambda x:(x.get('_anchor_score',0),x.get('date','')),reverse=True)
    for x in anchored:x.pop('_anchor_score',None)
    return anchored[:MAX_C] if MAX_C>0 else anchored

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
    global DATE_FLOOR, SCAN_DEADLINE_MONO, KNOWN_AB_IDENTITIES, KNOWN_AB_LINKS, KNOWN_SIGNAL_IDENTITIES, INSTITUTION_SEEN_FINGERPRINTS, ACTIVE_FRONTIER_GAP_URL_TERMS, ADMISSION_DIAGNOSTICS
    started = time.time()
    log_progress.started = time.monotonic()
    budget_seconds = int(CONFIG.get("scan_budget_seconds", 1200))
    SCAN_DEADLINE_MONO = time.monotonic() + budget_seconds
    now = dt.datetime.now(dt.timezone.utc)
    now_iso = now.isoformat(timespec="minutes").replace("+00:00", "Z")
    warnings: list[str] = []
    with ADMISSION_DIAGNOSTICS_LOCK:
        ADMISSION_DIAGNOSTICS.clear()
    previous = load_previous()

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
        label = "First-run inherited-corpus audit" if inherited_audit else "Quality-profile regression cleanup"
        log_progress(f"{label}: checking current saved A/B material before discovery")
        # A changed admission profile can invalidate historical rows just as surely as
        # an inherited legacy corpus. Re-run the same fail-closed audit and refresh only
        # on profile migration; ordinary scans never re-audit accepted history.
        previous, inherited_audit_stats = audit_inherited_ab(previous, warnings)
        previous["inherited_corpus_audit_complete"] = True
        previous["precision_corpus_cleanup_complete"] = True
        log_progress(
            f"{label} complete: kept "
            f"{inherited_audit_stats['stored_pass']} on saved evidence + "
            f"{inherited_audit_stats['refreshed_pass']} after document refresh; removed "
            f"{inherited_audit_stats['strand_a_removed']} A and "
            f"{inherited_audit_stats['strand_b_removed']} B item(s)"
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
        f"{frontier_focus['empty_cells']}/16 empty; scarcity-priority "
        + (", ".join(f"{k}({frontier_focus.get('deficits', {}).get(k, 0)})" for k in frontier_focus["targets"]) if frontier_focus["targets"] else "no extra gap queries")
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
    gap_from = DATE_FLOOR if gap_lookback_months <= 0 else min(DATE_FLOOR, now.date() - relativedelta(months=gap_lookback_months))
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

    oa_reserved = len(gap_scholarly) + len(b_method_focus) + len(oa_explore)
    cr_reserved = len(gap_scholarly) + len(b_method_focus) + len(cr_explore)
    oa_base_cap = max(1, oa_cap - min(oa_reserved, max(0, oa_cap - 1)))
    cr_base_cap = max(1, cr_cap - min(cr_reserved, max(0, cr_cap - 1)))
    oa_cursor_before = int(state.get("openalex_cursor", 0) or 0)
    cr_broad_cursor_before = int(state.get("crossref_broad_cursor", 0) or 0)
    oa_base, _oa_planned_next, _oa_planned_wrapped = rotating_batch(
        all_queries, oa_cursor_before, oa_base_cap
    )
    cr_base, _cr_planned_next, _cr_planned_wrapped = rotating_batch(
        all_queries, cr_broad_cursor_before, cr_base_cap
    )
    oa_batch = list(dict.fromkeys(gap_scholarly + b_method_focus + oa_explore + oa_base))[:oa_cap]
    cr_batch = list(dict.fromkeys(gap_scholarly + b_method_focus + cr_explore + cr_base))[:cr_cap]
    oa_query_dates = {q: gap_from for q in gap_scholarly}
    cr_query_dates = {q: gap_from for q in gap_scholarly}
    oa_depth_lanes = {q: "gap" for q in gap_scholarly}
    cr_depth_lanes = {q: "gap" for q in gap_scholarly}
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
    source_journals_all = list(dict.fromkeys(CONFIG.get("crossref_priority_journals", [])))
    cr_source_cursor_before = int(state.get("crossref_source_cursor", 0) or 0)
    cr_source_batch, _cr_source_planned_next, _cr_source_planned_wrapped = rotating_batch(
        source_journals_all, cr_source_cursor_before, int(CONFIG.get("crossref_source_first_journals_per_scan", 8))
    )
    institution_sources_all = list(CONFIG.get("institution_sources", []))
    institution_cursor_before = int(state.get("institution_cursor", 0) or 0)
    inst_rotating, _inst_planned_next, _inst_planned_wrapped = rotating_batch(
        institution_sources_all,
        institution_cursor_before,
        int(CONFIG.get("institution_sources_per_scan", 18)),
    )
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
    inst_batch = inst_rotating + gap_sources

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
        f"Crossref {len(cr_batch)} broad + {len(cr_priority_batch)} priority task(s) + {len(cr_source_batch)} source-first journal(s) from {cr_from.isoformat()}, "
        f"institutions {len(inst_batch)} source(s) ({len(inst_rotating)} rotating + {len(gap_sources)} gap-specialist) from {inst_from.isoformat()}; "
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
    execution_stats: dict[str, Any] = {}
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
    state["crossref_source_cursor"], cr_source_wrapped, cr_source_executed = committed_rotation_cursor(
        source_journals_all, cr_source_cursor_before, cr_source_batch, executed_source_journals
    )
    method_executed = executed_oa | executed_cr
    state["strand_b_method_cursor"], b_method_wrapped, b_method_executed = committed_rotation_cursor(
        b_method_bank, b_method_cursor_before, b_method_focus, method_executed
    )
    state["openalex_explore_cursor"], _oa_explore_wrapped, oa_explore_executed = committed_rotation_cursor(
        explore_bank, oa_explore_cursor_before, oa_explore, executed_oa
    )
    state["crossref_explore_cursor"], _cr_explore_wrapped, cr_explore_executed = committed_rotation_cursor(
        explore_bank, cr_explore_cursor_before, cr_explore, executed_cr
    )

    # Quiet-scan rescue now runs BEFORE the slower institutional stage. This guarantees
    # that a zero-admission scholarly slice gets a second historical topic/depth slice
    # while meaningful budget still remains, rather than hoping 260s survive afterwards.
    quiet_rescue = {"attempted": False, "openalex_queries": [], "crossref_queries": [], "themes": []}
    rescue_enabled = bool(CONFIG.get("quiet_scan_rescue_enabled", True))
    rescue_min_remaining = int(CONFIG.get("quiet_scan_rescue_min_seconds_remaining", 180) or 180)
    scholarly_deduped = dedupe_candidates(oa + cr)
    if rescue_enabled and not scholarly_deduped and budget_remaining() > rescue_min_remaining and not (oa_failed and cr_failed):
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
                "Quiet-scan rescue before institutional stage: first scholarly slice admitted nothing; trying next historical slice: "
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
    inst = [x for x in inst if isinstance(x, dict)]
    inst_failed = source_stage_failed(warnings, "institution")
    institution_domains_all = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in institution_sources_all]
    inst_planned_domains = [clean_text(x.get("domain", "")).lower().removeprefix("www.") for x in inst_rotating]
    executed_inst = set(execution_stats.get("institution_sources", set()))
    state["institution_cursor"], inst_wrapped, inst_base_executed = committed_rotation_cursor(
        institution_domains_all, institution_cursor_before, inst_planned_domains, executed_inst
    )

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
    output_corpus_floor = DATE_FLOOR
    for item in strand_a + strand_b:
        if isinstance(item, dict):
            item_date = parse_date(item.get("date"))
            if item_date:
                output_corpus_floor = min(output_corpus_floor, item_date)

    current_c = anchor_news(news, strand_a)
    prev_c = previous.get("strand_c", []) if isinstance(previous.get("strand_c"), list) else []
    strand_c = merge_signal_corpus(prev_c, current_c, now_iso)

    previous_a_ids = {identity(internalize_previous(x)) for x in prev_a if isinstance(x, dict)}
    previous_b_ids = {identity(internalize_previous(x)) for x in prev_b if isinstance(x, dict)}
    new_a_count = sum(1 for x in strand_a if x.get("new_this_scan") and identity(internalize_previous(x)) not in previous_a_ids)
    new_b_count = sum(1 for x in strand_b if x.get("new_this_scan") and identity(internalize_previous(x)) not in previous_b_ids)
    new_c_count = sum(1 for x in strand_c if x.get("new_this_scan"))

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
    state["last_run"] = now_iso
    state["last_batches"] = {
        "openalex_queries": len(oa_batch),
        "openalex_exploration_queries": len(oa_explore),
        "crossref_broad_queries": len(cr_batch),
        "crossref_exploration_queries": len(cr_explore),
        "crossref_priority_tasks": len(cr_priority_batch),
        "institution_sources": len(inst_batch),
        "frontier_gap_queries": len(frontier_focus["queries"]),
        "frontier_gap_scholarly_queries": len(frontier_focus.get("scholarly_queries", [])),
    }
    state["frontier_coverage_before_scan"] = {
        "qualifying": frontier_focus["qualifying"],
        "empty_cells": frontier_focus["empty_cells"],
        "counts": frontier_focus["counts"],
        "target_count": frontier_focus.get("target_count", 3),
        "deficits": frontier_focus.get("deficits", {}),
        "scarcity_scores": frontier_focus.get("scarcity_scores", {}),
        "targets": frontier_focus["targets"],
    }

    data = {
        "last_updated": now_iso,
        "first_scan_complete": True,
        "corpus_start_date": output_corpus_floor.isoformat(),
        "source_expansion_version": expansion_marker,
        "quality_profile_version": QUALITY_PROFILE_VERSION,
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
        "signal_backfill_complete": signal_backfill_complete,
        "incremental_state_version": INCREMENTAL_STATE_VERSION,
        "rotation_profile_version": ROTATION_PROFILE_VERSION,
        "recall_profile_version": RECALL_PROFILE_VERSION,
        "scan_state": state,
        "zero_config_scan": True,
        "admission_profile": str(CONFIG.get("admission_profile", "balanced_relevance_v15_scan_repair")),
        "scan_health": health,
        "scan_window": {
            "ab_date_floor": DATE_FLOOR.isoformat(),
            "ab_discovery_from_this_run": min(oa_from, cr_from, inst_from).isoformat(),
            "frontier_gap_scholarly_from": gap_from.isoformat() if gap_scholarly else "",
            "frontier_gap_historical_lookback_months": gap_lookback_months if gap_scholarly else 0,
            "openalex_from": oa_from.isoformat(),
            "crossref_from": cr_from.isoformat(),
            "historical_exploration_from": DATE_FLOOR.isoformat(),
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
            "c_prefilter_candidates": len(news),
            "c_anchored_candidates": len(current_c),
            "b_method_queries_this_scan": len(b_method_focus),
            "note_a": f"This scan added {new_a_count} new Strand A item(s). Earlier accepted items remain in the corpus." if new_a_count < 3 else "",
            "note_b": f"This scan added {new_b_count} new Strand B item(s). Earlier accepted items remain in the corpus." if new_b_count < 3 else "",
            "note_c": f"This scan added {new_c_count} new weak signal(s). The scanner uses a seven-day rolling window and keeps all earlier signals." if new_c_count < 3 else "",
            "frontier_gap_targets": frontier_focus["targets"],
            "frontier_gap_deficits": {k: frontier_focus.get("deficits", {}).get(k, 0) for k in frontier_focus["targets"]},
            "frontier_gap_target_count": frontier_focus.get("target_count", 3),
            "frontier_empty_cells_before_scan": frontier_focus["empty_cells"],
            "rotation_note": (
                "Fresh-window scanning plus full-corpus exploration were both active. "
                "Historical exploration rotated through: " + ", ".join(exploration.get("themes", [])) + "."
                + (
                    " The first slice admitted nothing, so a second historical slice was also tried: "
                    + ", ".join(quiet_rescue.get("themes", [])) + "."
                    if quiet_rescue.get("attempted") else ""
                )
            ) if exploration.get("themes") else "Fresh-window scanning was active; no historical exploration query was configured.",
            "historical_exploration": {
                "from": DATE_FLOOR.isoformat(),
                "openalex_queries": oa_explore,
                "crossref_queries": cr_explore,
                "themes": exploration.get("themes", []),
            },
            "quiet_scan_rescue": quiet_rescue,
        },
        "strand_a": strand_a,
        "strand_b": strand_b,
        "strand_c": strand_c,
        "stats": {
            "openalex_admitted_before_dedupe": len(oa),
            "openalex_public_anonymous": True,
            "openalex_api_key_configured": False,
            "crossref_admitted_before_dedupe": len(cr),
            "crossref_public_anonymous": True,
            "institutional_admitted_before_dedupe": len(inst),
            "scholarly_queries_a": len(CONFIG.get("queries_a", [])),
            "scholarly_queries_b": len(CONFIG.get("queries_b", [])),
            "openalex_queries_this_run": len(oa_batch),
            "openalex_queries_executed": len(set(execution_stats.get("openalex_queries", set()))),
            "openalex_base_queries_executed": oa_base_executed,
            "openalex_exploration_queries_this_run": len(oa_explore),
            "openalex_exploration_queries_executed": oa_explore_executed + int(execution_stats.get("quiet_rescue_openalex_executed", 0)),
            "crossref_broad_queries_this_run": len(cr_batch),
            "crossref_broad_queries_executed": len(set(execution_stats.get("crossref_broad_queries", set()))),
            "crossref_base_queries_executed": cr_base_executed,
            "crossref_exploration_queries_this_run": len(cr_explore),
            "crossref_exploration_queries_executed": cr_explore_executed + int(execution_stats.get("quiet_rescue_crossref_executed", 0)),
            "quiet_scan_rescue_attempted": bool(quiet_rescue.get("attempted")),
            "quiet_scan_rescue_queries": len(quiet_rescue.get("openalex_queries", [])) + len(quiet_rescue.get("crossref_queries", [])),
            "crossref_priority_tasks_this_run": len(cr_priority_batch),
            "crossref_priority_tasks_executed": cr_priority_executed,
            "crossref_source_journals_this_run": len(cr_source_batch),
            "crossref_source_journals_executed": cr_source_executed,
            "recall_backfill_this_run": bool(state.get("recall_reset_this_run")),
            "crossref_missing_abstract_enrichment_attempted": int(execution_stats.get("crossref_abstracts_enrichment_attempted", 0)),
            "b_method_queries_executed": b_method_executed,
            "institution_sources_this_run": len(inst_batch),
            "institution_rotating_sources_executed": inst_base_executed,
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
            "frontier_coverage_classifier_ok": not bool(frontier_focus["classifier_error"]),
            "signal_recovery_backfill": signal_backfill,
            "signal_backfill_complete": signal_backfill_complete,
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
        },
        "scan_diagnostics": {
            "source_warning_count": len(warnings),
            "source_warnings": list(dict.fromkeys(warnings))[:100],
            "transport_failure_warning_count": transport_failure_count,
        },
    }
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
