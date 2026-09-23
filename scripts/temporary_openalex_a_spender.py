#!/usr/bin/env python3
"""Temporary paid OpenAlex Strand-A discovery.

This file is intentionally separate from the normal scanner. It:
- uses the existing scanner's *ordinary* OpenAlex -> Strand-A admission functions;
- never enables the private/wider Deep-A gate;
- never changes the normal scanner's cursors/state;
- spends only a bounded OpenAlex search budget saved in its own state file;
- appends only genuinely-new, ordinary-gate Strand-A findings to radar.json.

Delete this file, its workflow, and temporary_openalex_a_state.json when finished.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "temporary_openalex_a_state.json"
RADAR_PATH = ROOT / "radar.json"

# Import the current scanner itself.  This is the key safety property: admission is not
# reimplemented here, so source/language/document/A-gate/final-worthiness rules stay shared.
sys.path.insert(0, str(ROOT / "scripts"))
import scan_radar_deep_a as scanner  # noqa: E402


def clean(v: Any) -> str:
    return " ".join(str(v or "").split())


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def query_bank() -> list[str]:
    """Use existing A-oriented query banks only; do not use the private relaxed-gate bank."""
    rows: list[str] = []
    for key in ("queries_a", "evidence_first_queries", "crossref_priority_journal_queries"):
        value = scanner.CONFIG.get(key, [])
        if isinstance(value, list):
            rows.extend(clean(x) for x in value if clean(x))
    # Stable de-duplication, preserving the scanner/config order.
    return list(dict.fromkeys(rows))


def initialize_scanner_context(radar: dict[str, Any]) -> dt.date:
    today = dt.date.today()
    floor = scanner.bootstrap_floor(today)
    scanner.DATE_FLOOR = floor
    scanner.EXTENDED_DATE_FLOOR = scanner.extended_top_quality_floor(today)
    scanner.B_METHOD_DATE_FLOOR = dt.date(today.year - scanner.B_METHOD_LOOKBACK_YEARS, 1, 1)
    scanner.B_METHOD_RECENT_DATE_FLOOR = dt.date(today.year - scanner.B_METHOD_RECENT_LOOKBACK_YEARS, 1, 1)
    scanner.ACTIVE_EU_CONTEXT_ANCHORS = [dict(x) for x in radar.get("strand_a", []) if isinstance(x, dict)]
    ab_ids, ab_links, sig_ids, ab_doi_titles = scanner.known_sets_from_previous(radar)
    scanner.KNOWN_AB_IDENTITIES = ab_ids
    scanner.KNOWN_AB_LINKS = ab_links
    scanner.KNOWN_SIGNAL_IDENTITIES = sig_ids
    scanner.KNOWN_AB_DOI_TITLES = ab_doi_titles
    return floor


def remember_as_known(row: dict[str, Any]) -> None:
    ident = scanner.stable_item_identity(row.get("title", ""), row.get("link", ""))
    if ident and ident != "title:":
        scanner.KNOWN_AB_IDENTITIES.add(ident)
    title_id = "title:" + scanner.norm_title(row.get("title", ""))
    if title_id != "title:":
        scanner.KNOWN_AB_IDENTITIES.add(title_id)
        if ident.startswith("doi:"):
            scanner.KNOWN_AB_DOI_TITLES.add(title_id)
    link = scanner.normalized_link(row.get("link", ""))
    if link:
        scanner.KNOWN_AB_LINKS.add(link)


def main() -> int:
    api_key = clean(os.environ.get("OPENALEX_API_KEY"))
    if not api_key:
        raise SystemExit("OPENALEX_API_KEY is missing. The normal GitHub secret is expected here.")

    # Absolute API-cost ceiling, not a promise about prepaid deduction. OpenAlex may first
    # consume its daily free allowance. These defaults are intentionally easy to change in
    # the *temporary workflow only* without touching the scanner.
    total_cap = float(os.environ.get("TEMP_OPENALEX_TOTAL_USD", "11.00"))
    chunk_cap = float(os.environ.get("TEMP_OPENALEX_CHUNK_USD", "2.00"))
    per_page = max(1, min(100, int(os.environ.get("TEMP_OPENALEX_PER_PAGE", "100"))))
    max_minutes = max(5, int(os.environ.get("TEMP_OPENALEX_MAX_MINUTES", "75")))
    deadline = time.monotonic() + max_minutes * 60

    state = load_json(STATE_PATH, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("version", 1)
    state.setdefault("profile", "temporary-openalex-a-spender-v1")
    state.setdefault("spent_usd", 0.0)
    state.setdefault("query_index", 0)
    state.setdefault("page", 1)
    state.setdefault("accepted_total", 0)
    state.setdefault("requests_total", 0)
    state.setdefault("completed", False)

    spent_total = float(state.get("spent_usd", 0.0) or 0.0)
    if bool(state.get("completed")) or spent_total + 0.000999 >= total_cap:
        state["completed"] = True
        state["updated_at"] = utc_now()
        save_json(STATE_PATH, state)
        print(f"Temporary OpenAlex A spender already complete: ${spent_total:.4f} of ${total_cap:.2f} API cost used.")
        return 0

    radar = load_json(RADAR_PATH, {})
    if not isinstance(radar, dict):
        raise SystemExit("radar.json is not a JSON object")
    floor = initialize_scanner_context(radar)

    queries = query_bank()
    if not queries:
        raise SystemExit("No Strand-A query bank found in radar_config.json")

    qidx = int(state.get("query_index", 0) or 0) % len(queries)
    page = max(1, int(state.get("page", 1) or 1))
    run_spent = 0.0
    run_requests = 0
    run_seen_ids: set[str] = set()
    new_candidates: list[dict[str, Any]] = []
    session = requests.Session()

    print(
        f"Temporary OpenAlex A chunk: total ${spent_total:.4f}/${total_cap:.2f}; "
        f"this chunk <= ${chunk_cap:.2f}; {len(queries)} ordinary-A queries; start page-wave {page}."
    )

    while time.monotonic() < deadline:
        # Search calls currently cost $0.001. Guard *before* the request so the configured
        # ceiling cannot be exceeded by more than pricing-rounding differences.
        estimated_next = 0.001
        if spent_total + estimated_next > total_cap + 1e-12:
            break
        if run_spent + estimated_next > chunk_cap + 1e-12:
            break
        if page > 100:  # OpenAlex basic paging limit is 10,000 results/query at 100/page.
            break

        q = queries[qidx]
        params = {
            "api_key": api_key,
            "search": q,
            "filter": f"from_publication_date:{floor.isoformat()},to_publication_date:{dt.date.today().isoformat()},language:en",
            "sort": "publication_date:desc",
            "per_page": str(per_page),
            "page": str(page),
            "select": "id,display_name,abstract_inverted_index,publication_date,language,type,doi,primary_location,best_oa_location,locations,authorships",
        }

        response = None
        for attempt in range(5):
            try:
                response = session.get("https://api.openalex.org/works", params=params, timeout=30)
            except requests.RequestException as exc:
                if attempt == 4:
                    print(f"OpenAlex network error; ending this chunk safely: {exc}")
                    response = None
                    break
                time.sleep(min(30, 2 ** attempt))
                continue
            if response.status_code == 429:
                if attempt == 4:
                    print("OpenAlex rate limit persisted; ending this chunk safely.")
                    response = None
                    break
                time.sleep(min(60, 5 * (attempt + 1)))
                continue
            break
        if response is None:
            break
        if response.status_code != 200:
            print(f"OpenAlex HTTP {response.status_code}; ending this chunk safely.")
            break

        payload = response.json()
        meta = payload.get("meta") if isinstance(payload, dict) else {}
        call_cost = float((meta or {}).get("cost_usd", estimated_next) or estimated_next)
        spent_total += call_cost
        run_spent += call_cost
        run_requests += 1
        state["requests_total"] = int(state.get("requests_total", 0) or 0) + 1

        page_candidates: list[dict[str, Any]] = []
        results = payload.get("results", []) if isinstance(payload, dict) else []
        for work in results if isinstance(results, list) else []:
            if not isinstance(work, dict):
                continue
            wid = clean(work.get("id"))
            if wid and wid in run_seen_ids:
                continue
            if wid:
                run_seen_ids.add(wid)
            title = clean(work.get("display_name"))
            doi = clean(work.get("doi"))
            if scanner.known_ab_duplicate(title, doi):
                continue
            try:
                candidate = scanner.candidate_from_openalex(work, date_floor=floor, allow_strategic=False)
            except Exception as exc:
                print(f"Candidate gate skipped one malformed OpenAlex row: {exc}")
                continue
            if not candidate:
                continue
            # Explicit hard check: this temporary run may only publish the ordinary A gate.
            if not bool(candidate.get("ordinary_a_pass")):
                continue
            if clean(candidate.get("strand")).upper() not in {"A", "BOTH"}:
                continue
            if bool(candidate.get("deep_a_private_recall")):
                continue
            page_candidates.append(candidate)

        for candidate in scanner.genuinely_new_a_candidates(page_candidates):
            ident = scanner.identity(candidate)
            link = scanner.normalized_link(candidate.get("link", ""))
            if ident in {scanner.identity(x) for x in new_candidates}:
                continue
            if link and any(scanner.normalized_link(x.get("link", "")) == link for x in new_candidates):
                continue
            row = dict(candidate)
            # Match a focused Strand-A scan: a BOTH result is routed into A only.
            row["strand"] = "A"
            new_candidates.append(row)
            remember_as_known(row)

        # Breadth first: page 1 across the whole query bank, then page 2, etc.
        qidx += 1
        if qidx >= len(queries):
            qidx = 0
            page += 1

        # Persist spend/cursor frequently, so a cancelled Actions job resumes instead of
        # accidentally repeating a large paid block.
        state.update({
            "spent_usd": round(spent_total, 6),
            "query_index": qidx,
            "page": page,
            "updated_at": utc_now(),
        })
        if run_requests % 25 == 0:
            save_json(STATE_PATH, state)
            print(
                f"  {run_requests} paid-search calls this chunk; ${run_spent:.3f}; "
                f"ordinary new A found so far: {len(new_candidates)}; page-wave {page}."
            )

    # Publish ONLY the newly accepted rows. Do not run a corpus-wide merge/cleanup here:
    # even a well-intentioned cleanup could alter old Strand-A rows, and this temporary job
    # is required to leave the normal scanner/corpus behaviour alone. The candidate has
    # already passed the scanner's normal source/language/A/final-worthiness gates above.
    if new_candidates:
        now_iso = utc_now()
        previous_a = radar.get("strand_a", []) if isinstance(radar.get("strand_a"), list) else []
        public_new = [
            scanner.public_item(row, new_this_scan=True, first_seen=now_iso)
            for row in sorted(new_candidates, key=scanner.rank_candidate)
        ]
        radar["strand_a"] = public_new + previous_a
        save_json(RADAR_PATH, radar)

    state["accepted_total"] = int(state.get("accepted_total", 0) or 0) + len(new_candidates)
    state["spent_usd"] = round(spent_total, 6)
    state["query_index"] = qidx
    state["page"] = page
    state["updated_at"] = utc_now()
    state["last_chunk"] = {
        "requests": run_requests,
        "cost_usd": round(run_spent, 6),
        "new_strand_a": len(new_candidates),
        "finished_at": utc_now(),
    }
    state["completed"] = bool(spent_total + 0.000999 >= total_cap or page > 100)
    save_json(STATE_PATH, state)

    print(
        f"Temporary OpenAlex A chunk finished: {run_requests} search calls, ${run_spent:.4f} this chunk, "
        f"${spent_total:.4f}/${total_cap:.2f} total; {len(new_candidates)} new ordinary-gate A finding(s)."
    )
    if state["completed"]:
        print("TEMPORARY OPENALEX BUDGET COMPLETE. Future scheduled runs will spend nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
