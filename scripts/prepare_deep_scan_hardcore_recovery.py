#!/usr/bin/env python3
"""Prepare a terminal Deep Scan recovery package for access-blocked/manual cases.

This does not change the protected Deep Scan verifier.  It packages records that the
normal Deep Scan work-state has already moved to ``needs_manual_verification`` (or the
legacy ``deferred`` terminal status) and gives a browsing-capable LLM a much stronger,
auditable retrieval protocol.  Any recovered work must still satisfy the unchanged
Deep Scan V2 admission instructions.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

try:
    from scripts.deep_read_works import (
        CORPUS, SIDECAR, SourceRead, clean, fetch_source_for_record, identity_hash,
        iter_historical_records, iter_records, load_sidecar, record_key, source_hash,
    )
    from scripts.deep_scan_work_state import (
        DEFAULT_WORK_STATE, load_state, manual_verification_keys, sync_verified,
        update_record_metadata,
    )
    from scripts.prepare_deep_scan_package import (
        INSTRUCTIONS as STANDARD_DEEP_SCAN_INSTRUCTIONS,
        duplicate_index, same_key_variants, scanner_fields,
    )
except ModuleNotFoundError:
    from deep_read_works import (  # type: ignore
        CORPUS, SIDECAR, SourceRead, clean, fetch_source_for_record, identity_hash,
        iter_historical_records, iter_records, load_sidecar, record_key, source_hash,
    )
    from deep_scan_work_state import (  # type: ignore
        DEFAULT_WORK_STATE, load_state, manual_verification_keys, sync_verified,
        update_record_metadata,
    )
    from prepare_deep_scan_package import (  # type: ignore
        INSTRUCTIONS as STANDARD_DEEP_SCAN_INSTRUCTIONS,
        duplicate_index, same_key_variants, scanner_fields,
    )

ROOT = Path(__file__).resolve().parents[1]
CLAIMS_VOCAB = ROOT / "claims_vocabulary.json"
FORMAT = "radar-deep-scan-hardcore-package-v1"
RESULT_FORMAT = "radar-deep-scan-results-v2"
CLAIMS_FORMAT = "radar-claims-v1"
DEFAULT_MAX_RECORDS = 12
DEFAULT_WORKERS = 10

HARDCORE_ROUTES = [
    "prior_attempt_audit",
    "supplied_url_redirects",
    "doi_registry_publisher",
    "exact_title_variants",
    "title_author_year_identifiers",
    "open_access_resolvers",
    "institutional_repositories",
    "author_research_group_pages",
    "preprint_accepted_manuscript",
    "journal_issue_toc_supplements",
    "citation_graph_related_versions",
    "official_document_repositories",
    "alternate_formats_and_archives",
    "multilingual_acronym_report_number",
]

HARDCORE_PREAMBLE = r"""# Deep Scan terminal recovery — PUSH HARDER protocol

## Why this package exists

Every record here has already reached the normal Deep Scan terminal access-limited list.  The record was
considered important enough to enter the Radar, and earlier verification attempts could not recover enough
substantive evidence.  **Do not treat that earlier failure as evidence that the work is unavailable.**

This is the final automatic recovery stage.  The objective is to reproduce the useful behaviour of a human
operator saying **"try harder"**: when the obvious routes fail, stop, identify genuinely new routes, and search
again before concluding that access is exhausted.

The same route-parity rule as ordinary Deep Scan applies: matching first-party material supplied through a scanner
validation URL, Cellar, Parliament or another explicit source route remains valid evidence. A blocked reader-facing
page or failed rediscovery search must not erase source material the scanner already retrieved and packaged.

## Non-negotiable persistence rule

**You may not conclude that a record is unverifiable merely because the normal six-step Deep Scan ladder failed.**
A failed publisher URL, paywall, bot block, missing DOI landing page, thin abstract, or previous failed recovery
attempt is a reason to change retrieval strategy, not to stop.

For every record that remains unresolved, perform all applicable recovery-route categories below and log what
was actually attempted.  Do not bypass authentication, paywalls, robots controls, or other access restrictions.
Use only legitimate public/author/repository/archive access.

### Recovery-route categories

1. `prior_attempt_audit` — read the supplied previous recovery history first.  Identify what was already tried,
   which routes merely repeated each other, and what *new* routes remain.
2. `supplied_url_redirects` — inspect the supplied URL, redirects, canonical links, download links, HTML/PDF
   variants, issue pages and attachment links.
3. `doi_registry_publisher` — DOI resolver plus bibliographic registry/publisher identity routes; inspect useful
   metadata links rather than stopping at a blocked landing page.
4. `exact_title_variants` — exact title plus punctuation/subtitle variants and distinctive title fragments.
5. `title_author_year_identifiers` — title + author/organisation/year; report numbers, ISBN/ISSN, article number,
   grant/project IDs, conference identifiers and other identity clues where applicable.
6. `open_access_resolvers` — legitimate OA-location services/metadata routes and links they expose.
7. `institutional_repositories` — university, funder, agency, national or discipline repositories; search both
   publication title and author/identifier.
8. `author_research_group_pages` — author CV/publication pages, lab/group pages and issuing-organisation pages.
9. `preprint_accepted_manuscript` — legitimate preprint, accepted manuscript, working-paper or repository version
   (for example HAL, Zenodo, arXiv, SSRN, OSF, RePEc, Europe PMC/PMC when relevant).
10. `journal_issue_toc_supplements` — issue table of contents, supplementary files, article XML/HTML endpoints,
    downloadable appendices or publisher mirrors that legitimately expose the same work.
11. `citation_graph_related_versions` — use references/citations/related-version clues to locate a conference,
    working-paper, report or repository version of the *same underlying work*.  Never substitute a merely related work.
12. `official_document_repositories` — for institutional reports/policy material, search the issuing body, EU/agency
    document repositories, publication offices and document-number systems.
13. `alternate_formats_and_archives` — legitimate archived official/publisher/repository copies and alternate
    public formats (HTML/PDF/DOCX/text).  No paywall bypass.
14. `multilingual_acronym_report_number` — translated/variant title searches, acronyms, report/document numbers,
    author-name variants and distinctive phrases.

A route may be `not_applicable`, but the note must explain why.  Do not write fourteen copies of "not found".
Each route needs a specific query/URL/identifier and a specific outcome.

## Mandatory TRY HARDER challenge passes

If the work is still unresolved after the route categories above, **do not finish yet**.

### TRY HARDER pass 1

Assume a legitimate copy or sufficiently substantive primary source probably exists somewhere you have not
looked.  Review your own audit and identify at least **three genuinely new retrieval ideas**.  Execute them.
Examples: a different repository family, an author's older/newer publication page, a report number rather than
title, issue-level navigation, a cited working-paper title, an institutional handle, or a different language/title variant.

### TRY HARDER pass 2

Challenge the first challenge pass.  Ask: **"If a person told me to try harder one more time, what would I do
that I still have not done?"**  Identify at least **two additional non-duplicate actions** and execute them.
Do not satisfy this by rephrasing the same web search.

## Final exhaustion audit

Only after both challenge passes may you close a record as `drop_unverifiable`.  Before doing so, verify that:

- every applicable recovery-route category above has a specific logged attempt or a defensible `not_applicable` note;
- both TRY HARDER passes contain new actions and actual outcomes;
- the original six mandatory Deep Scan retrieval steps are also fully logged in `verification.retrieval_attempts`;
- no substantive matching primary/repository/author copy was recovered;
- no reader interpretation, metadata correction or claims are being invented from title/abstract/snippets;
- you are not stopping merely because access was inconvenient or because previous attempts failed.

For this special terminal recovery mode, `drop_unverifiable` may be used when bibliographic identity is credible
but **substantive evidence remains inaccessible after the entire hardcore protocol**.  Set
`verification.evidence_depth` to `identity_only_after_hardcore_recovery` when identity is established, or
`unverified_after_hardcore_recovery` when even identity cannot be established.  The GitHub recovery importer
will remove the record from the active Radar rather than send it back to a human queue.

## Deep Scan standard is NOT loosened

The persistence protocol above changes only *how hard you search*.  If substantive evidence is recovered, use
the ordinary Deep Scan V2 KEEP / REVIEW / DROP criteria below **exactly as written**.  Do not keep a work because
it was difficult to retrieve, seemed important from its title, or survived earlier scanner filtering.

`defer` is **not allowed in this terminal recovery package**.  Either recover substantive evidence and make the
normal Deep Scan judgement, or exhaust the full protocol and return `drop_unverifiable`.

## Extra required audit object

Every result must additionally contain:

```json
"hardcore_recovery": {
  "routes": [
    {"route":"prior_attempt_audit","outcome":"completed","query_or_url":"...","note":"..."}
  ],
  "try_harder_passes": [
    {"pass":1,"new_routes_identified":["...","...","..."],"actions_taken":["..."],"result":"..."},
    {"pass":2,"new_routes_identified":["...","..."],"actions_taken":["..."],"result":"..."}
  ],
  "all_routes_exhausted": false,
  "terminal_reason": ""
}
```

If substantive evidence is recovered, `all_routes_exhausted` is false and you do not need to continue unused
routes.  If decision is `drop_unverifiable`, `all_routes_exhausted` must be true and the complete route/challenge
audit is mandatory.

---

# Unchanged authoritative Deep Scan V2 standard follows

"""

START_HERE = r"""RADAR DEEP SCAN — TERMINAL PUSH HARDER RECOVERY

Give this entire ZIP to a browsing-capable LLM and say:

    Process this terminal Deep Scan recovery package strictly according to INSTRUCTIONS.md.
    These records already defeated normal recovery. Do not give up at the ordinary retrieval ladder.
    Perform the mandatory PUSH HARDER route audit and both TRY HARDER challenge passes before declaring
    anything unverifiable. If substantive evidence is recovered, apply the unchanged normal Deep Scan
    standard. Return deep_scan_hardcore_results.json (or a ZIP containing it).

Important: this package deliberately has no DEFER/manual outcome.  After exhaustive recovery, genuinely
unrecoverable evidence is closed as DROP_UNVERIFIABLE instead of returning to a human queue.
"""


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _priority(strand: str, status: str) -> tuple[int, int]:
    s = strand.lower()
    if s == "strand_a": rank = 0
    elif s == "historical_a": rank = 1
    elif s == "strand_b": rank = 2
    elif s == "historical_b": rank = 3
    elif s == "strand_c": rank = 4
    else: rank = 5
    # True three-pass terminal cases before legacy one-pass/deferred rows within a strand.
    status_rank = 0 if status == "needs_manual_verification" else 1
    return rank, status_rank


def current_rows(doc: dict[str, Any], historical: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    out: dict[str, tuple[str, dict[str, Any]]] = {}
    for strand, row in iter_records(doc):
        key = record_key(row)
        if key:
            out[key] = (strand, row)
    for strand, row in iter_historical_records(historical):
        key = record_key(row)
        if key:
            out[key] = (strand, row)
    return out


def fetch_one(item: tuple[str, str, dict[str, Any], dict[str, Any]]):
    key, strand, row, state_row = item
    url = clean(row.get("link") or row.get("url") or row.get("doi"))
    src = fetch_source_for_record(row)
    return key, strand, row, state_row, src


def build_job(
    ordinal: int,
    key: str,
    strand: str,
    row: dict[str, Any],
    state_row: dict[str, Any],
    src: SourceRead,
    sidecar: dict[str, Any],
    dupes: dict[str, list[dict[str, str]]],
    variants: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    scope = "historical" if strand.startswith("historical_") else "main"
    strand_label = strand.rsplit("_", 1)[-1].upper() if strand.startswith("historical_") else ("A" if strand == "frontier_evidence" else strand.replace("strand_", "").upper())
    previous_history = state_row.get("recovery_history") if isinstance(state_row.get("recovery_history"), list) else []
    previous_verification = state_row.get("verification") if isinstance(state_row.get("verification"), dict) else {}
    return {
        "job_number": ordinal,
        "record_key": key,
        "source_hash": source_hash(row),
        "identity_hash": identity_hash(row),
        "corpus_scope": scope,
        "strand": strand_label,
        "terminal_status": clean(state_row.get("status")),
        "previous_recovery_attempts": int(state_row.get("recovery_attempts") or 0),
        "previous_recovery_reason": clean(state_row.get("manual_verification_reason") or state_row.get("defer_reason") or state_row.get("recovery_reason")),
        "previous_recovery_history": previous_history,
        "previous_verification": previous_verification,
        "automatic_scanner": scanner_fields(row),
        "same_record_key_variants": variants.get(key, []),
        "legacy_deep_scan": sidecar.get("records", {}).get(key) if isinstance(sidecar.get("records", {}).get(key), dict) else None,
        "possible_duplicates": dupes.get(key, []),
        "source_material": {
            "read_mode": src.mode,
            "final_url": src.final_url,
            "retrieval_note": src.note,
            "text": src.text,
        },
        "required_output_addition": {
            "hardcore_recovery": {
                "routes": [],
                "try_harder_passes": [],
                "all_routes_exhausted": False,
                "terminal_reason": "",
            }
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare terminal PUSH HARDER Deep Scan recovery package")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--historical", type=Path, default=None)
    ap.add_argument("--sidecar", type=Path, default=SIDECAR)
    ap.add_argument("--work-state", type=Path, default=DEFAULT_WORK_STATE)
    ap.add_argument("--output-dir", type=Path, default=Path("deep_scan_hardcore_recovery"))
    ap.add_argument("--max-records", type=int, default=DEFAULT_MAX_RECORDS)
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()
    if args.historical is None:
        args.historical = args.corpus.parent / "historical" / "historical.json"

    doc = json.loads(args.corpus.read_text(encoding="utf-8"))
    historical: dict[str, Any] = {}
    if args.historical.exists():
        loaded = json.loads(args.historical.read_text(encoding="utf-8"))
        historical = loaded if isinstance(loaded, dict) else {}
    sidecar = load_sidecar(args.sidecar)
    state = load_state(args.work_state)
    sync_verified(state, sidecar)
    rows = current_rows(doc, historical)
    for key, (_strand, row) in rows.items():
        update_record_metadata(state, key, row)
    manual = manual_verification_keys(state)

    candidates: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
    for key in manual:
        if key not in rows:
            continue
        strand, row = rows[key]
        st = state.get("records", {}).get(key, {}) if isinstance(state.get("records", {}).get(key), dict) else {}
        candidates.append((key, strand, row, st))
    candidates.sort(key=lambda x: (_priority(x[1], clean(x[3].get("status"))), clean(x[3].get("manual_verification_since") or x[3].get("deferred_at") or x[3].get("last_recovery_at")), x[0]))
    limit = max(1, min(int(args.max_records or DEFAULT_MAX_RECORDS), 24))
    todo = candidates[:limit]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not todo:
        (args.output_dir / "NO_HARDCORE_RECOVERY_NEEDED.txt").write_text(
            "No terminal hands-on/deferred Deep Scan records remain.\n", encoding="utf-8"
        )
        print("No terminal Deep Scan recovery work remains.")
        return

    seed = "\n".join(f"{key}|{source_hash(row)}" for key, _s, row, _st in todo)
    pkg_id = f"hardcore-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{hashlib.sha256(seed.encode()).hexdigest()[:12]}"
    dupes = duplicate_index(doc)
    variants = same_key_variants(doc)

    if args.no_fetch:
        fetched = [(key, strand, row, st, SourceRead("stored_only", "", note="pre-retrieval disabled")) for key, strand, row, st in todo]
    else:
        ordered: dict[int, tuple[str, str, dict[str, Any], dict[str, Any], SourceRead]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(int(args.workers), 20))) as ex:
            futs = {ex.submit(fetch_one, item): i for i, item in enumerate(todo)}
            for fut in concurrent.futures.as_completed(futs):
                i = futs[fut]
                try:
                    ordered[i] = fut.result()
                except Exception as exc:
                    key, strand, row, st = todo[i]
                    ordered[i] = (key, strand, row, st, SourceRead("stored_only", "", note=f"packager error: {clean(exc)[:180]}"))
        fetched = [ordered[i] for i in range(len(todo))]

    workdir = Path(tempfile.mkdtemp(prefix="radar-hardcore-recovery-"))
    try:
        root = workdir / f"deep_scan_hardcore_{pkg_id}"
        root.mkdir(parents=True)
        jobs = [build_job(i + 1, key, strand, row, st, src, sidecar, dupes, variants) for i, (key, strand, row, st, src) in enumerate(fetched)]
        standard = STANDARD_DEEP_SCAN_INSTRUCTIONS
        standard = standard.replace(
            "10. If the claimed work itself still cannot be substantiated after the full mandatory recovery ladder,\n    return `drop_unverifiable`. If identity is confirmed but substantive evidence remains inaccessible after all required recovery steps,\n    use `defer` rather than inventing a judgement. A defer is coordination-only and leaves the Radar record provisional.",
            "10. In this terminal recovery package, do not DEFER. If substantive evidence is recovered, apply the unchanged admission standard. If the complete PUSH HARDER protocol is exhausted without substantive evidence, return `drop_unverifiable` with the mandatory hardcore audit.",
        )
        standard = standard.replace(
            "- `defer` — coordination-only, not an admission judgement. Use only when the work's identity is verified but, after all required recovery steps, substantive evidence remains inaccessible or too thin to support KEEP/REVIEW/DROP. Each validated defer counts as one genuine recovery pass. GitHub permits at most three such passes, throttles retries so they cannot dominate worker capacity, and after the third failed pass moves the work to the persistent **Hands-on verification needed** list.",
            "- `defer` — **NOT AVAILABLE IN THIS TERMINAL RECOVERY PACKAGE.** Recover substantive evidence and decide KEEP/REVIEW/DROP, or exhaust PUSH HARDER and use `drop_unverifiable`.",
        )
        standard = standard.replace("For `drop`, `drop_unverifiable`, or `defer`, return `claims: []`.", "For `drop` or `drop_unverifiable`, return `claims: []`.")
        standard = standard.replace("For DROP/DROP_UNVERIFIABLE/DEFER it may be the original strand or empty.", "For DROP/DROP_UNVERIFIABLE it may be the original strand or empty.")
        standard = standard.replace(
            "For DEFER use `reason_code: \"EVIDENCE_ACCESS_LIMITED\"`, set `verification.evidence_depth` to `identity_only_after_recovery`, report all required retrieval steps with specific notes, and do not invent reader interpretation.",
            "DEFER is not permitted in this terminal recovery package.",
        )
        standard = standard.replace(
            "- DEFER is allowed only after all required retrieval steps when identity is verified but substantive evidence is still unavailable/insufficient. It is not authoritative and must not contain invented reader prose or metadata corrections.",
            "- DEFER is not allowed in terminal recovery. Identity-confirmed but substantively inaccessible work must continue through PUSH HARDER; only after exhaustion may it use terminal `drop_unverifiable`.",
        )
        instructions = HARDCORE_PREAMBLE + standard
        (root / "INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")
        (root / "START_HERE.txt").write_text(START_HERE, encoding="utf-8")
        (root / "claims_vocabulary.json").write_bytes(CLAIMS_VOCAB.read_bytes())
        payload = {
            "format": FORMAT,
            "result_format": RESULT_FORMAT,
            "claims_format": CLAIMS_FORMAT,
            "package_id": pkg_id,
            "created_at": utc_now(),
            "hardcore_routes": HARDCORE_ROUTES,
            "works_in_package": len(jobs),
            "jobs": jobs,
        }
        (root / "jobs.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        template = {
            "format": RESULT_FORMAT,
            "claims_format": CLAIMS_FORMAT,
            "recovery_mode": "hardcore-terminal-v1",
            "package_id": pkg_id,
            "results": [],
        }
        (root / "RESULT_TEMPLATE.json").write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest = {
            "format": FORMAT,
            "result_format": RESULT_FORMAT,
            "recovery_mode": "hardcore-terminal-v1",
            "package_id": pkg_id,
            "created_at": utc_now(),
            "works_in_package": len(jobs),
            "record_keys": [j["record_key"] for j in jobs],
            "strand_counts": {},
            "expected_result_filename": "deep_scan_hardcore_results.json",
        }
        for job in jobs:
            manifest["strand_counts"][job["strand"]] = manifest["strand_counts"].get(job["strand"], 0) + 1
        (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        zip_path = args.output_dir / "deep_scan_hardcore_recovery.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(root.parent))
        (args.output_dir / "PACKAGE_SUMMARY.txt").write_text(
            f"Terminal Deep Scan PUSH HARDER package: {pkg_id}\n"
            f"Records: {len(jobs)}\n"
            f"Priority: Main A -> Historical A -> Main B -> Historical B -> C/other.\n\n"
            "Give deep_scan_hardcore_recovery.zip to one browsing-capable LLM. The package requires the normal Deep Scan standard plus a mandatory exhaustive recovery protocol and two TRY HARDER challenge passes before DROP_UNVERIFIABLE.\n",
            encoding="utf-8",
        )
        print(f"Created {zip_path} with {len(jobs)} terminal recovery records")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
