#!/usr/bin/env python3
"""Create a self-contained offline Deep Scan V2 ZIP for all non-V2 Radar works."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

try:
    from scripts.deep_read_works import (
        CORPUS, SIDECAR, SourceRead, clean, fetch_source, iter_records, load_sidecar,
        pending, record_key, identity_hash, scanner_fields,
    )
except ModuleNotFoundError:
    from deep_read_works import (  # type: ignore
        CORPUS, SIDECAR, SourceRead, clean, fetch_source, iter_records, load_sidecar,
        pending, record_key, identity_hash, scanner_fields,
    )

FORMAT = "radar-deep-scan-package-v2"
RESULT_FORMAT = "radar-deep-scan-results-v2"
DEFAULT_BATCH_SIZE = 12
DEFAULT_MAX_RECORDS = 12
DEFAULT_WORKERS = 10

INSTRUCTIONS = r"""# Radar Deep Scan V2 — authoritative verification instructions

## Role

You are the Radar's **authoritative evidence verifier**, not a summariser and not a copy editor.
The automatic scanner is fast and provisional. It can be wrong about the work, source, strand,
European relevance, method contribution, metadata, or even whether the linked object is the work
it claims to be. Existing Deep Scan V1 text is also only prior evidence: check it rather than trust it.

A V2 result may change what the active Radar says and may remove a record from the active corpus.
Therefore every decision must be source-grounded and auditable.

## Non-negotiable working rules

1. Process records **in the supplied order**. Do not cherry-pick easy records.
2. Read deeply enough to understand the actual work. Prefer full text or a substantive primary/official
   source whenever it is legally accessible. Do not stop at an abstract if a legitimate full text is available.
3. Treat scanner fields and older Deep Scan text as hypotheses, never as ground truth.
4. Verify bibliographic identity: title, authors/organisation, publication/outlet, year/date, DOI when present,
   and the relationship between the supplied URL and the underlying work.
5. Search snippets are navigation clues only. They are never substantive evidence.
6. Never substitute a related paper, programme page, or secondary story for the claimed work.
7. Preserve uncertainty. Do not turn proposals into outcomes, modelled scenarios into observed facts,
   correlations into causation, or policy intentions into effects.
8. Do not invent a European implication or a WHY.
9. If a record is difficult or blocked, **keep searching through the mandatory retrieval ladder below**.
   A failed URL is not permission to give up.
10. If the claimed work still cannot be substantiated after the full mandatory recovery ladder,
    return `drop_unverifiable`. Unverifiable evidence does not remain in the active Radar.

## Mandatory retrieval ladder for difficult/thin/blocked records

For a record whose supplied material is not already a substantial matching primary source, attempt and
record each applicable step. For `drop_unverifiable`, all six steps must be reported. Each attempt note must
state the actual URL/query/identifier used (or why a step is not applicable) and what happened; do not repeat
generic phrases such as "checked" across the ladder.

1. `supplied_url` — open/follow redirects and inspect what the URL actually is.
2. `doi` — resolve/search the DOI when present; if no DOI exists, explicitly record `not_applicable`.
3. `exact_title` — search the exact title in quotation marks.
4. `title_author_year` — search title plus author/organisation/year or other identifying metadata.
5. `official_publisher_or_repository` — search publisher/journal/issuing body, institutional repository,
   author/university page, preprint/repository, EU/agency repository, or legitimate archived official copy.
6. `broader_identity_search` — a bounded final search using distinctive title fragments, DOI fragments,
   authors, report identifiers, programme/document numbers, or other identity clues.

Do not bypass authentication, paywalls or access controls. If full text is paywalled, look for legitimate
repository/author copies and use the strongest matching evidence available.

## Admission decision

Return exactly one decision:

- `keep` — the recovered work clearly satisfies the current strand criteria.
- `drop` — the recovered work clearly exists but fails the current criteria.
- `review` — the work exists and has real evidence, but admission genuinely requires human judgement.
  REVIEW is not a refuge for laziness or failed retrieval.
- `drop_unverifiable` — after the complete retrieval ladder, the claimed work cannot be substantiated.

### Strand A — substantive European R&I work

European relevance must be substantive and supported by the work/source. A non-European study does not
qualify merely because the EU is mentioned, used as one comparator, provides a framework/reference,
appears in references, or could have an imagined European implication. The work needs a genuine European
research, innovation, science, technology, industrial-capability, research-policy, research-security or
closely related connection.

### Strand B — reusable methods

B is geography-independent, but it requires a genuine reusable methodological contribution: a new or
materially improved method, transferable analytical framework, measurement/indicator approach, evaluation
design, foresight/scenario method, evidence-synthesis procedure, or similar technique. Merely applying an
existing method/index/framework/model/survey/clustering tool to a case is not enough.

### Strand C — substantive current developments

C requires a substantive current development with a defensible Radar connection. Generic institutional,
programme, navigation, promotional, vacancy/recruitment, seminar/event or listing pages do not qualify just
because vocabulary matches. An otherwise generic page may qualify only when the page itself reports a real
new policy decision, funding instrument, programme change, legislative development, evidence release or
comparable substantive event.

## Metadata/provenance correction

Check the scanner's bibliographic/source claims. If a field is demonstrably wrong, return only the correction
that primary/authoritative evidence supports. In particular, do not preserve a prestigious organisation name
because the scanner guessed it. `source` means the actual journal/publisher/issuing organisation for this work.

Allowed corrected fields: `title`, `authors`, `source`, `date`, `type`, `eu_relevance`,
`text_mode`, `source_text_mode`, `event_status`. Never alter `record_key`, URL identity or DOI identity.
Do **not** invent or set `source_tier`; that is a Radar scoring concept, not bibliographic evidence. If the stored tier is unsupported, put `source_tier` in `metadata_correction.unset` so ranking is recomputed from verified provenance.
Any non-empty metadata correction must include a short evidence-grounded `reason`, and the verification block must cite at least one substantive recovered source actually used as evidence.

## Duplicate check

The package may show possible duplicate records. Do not merge merely similar works. If two records are clearly
the same underlying work (same DOI/identical publication or another very high-confidence identity match), use
`duplicate.status = "duplicate"` and provide the exact canonical `record_key`. Ambiguous cases use `review`.

## Reader interpretation

After verification, explain what the recovered work actually says. Reader text limits:
- `reader_title`: max 18 words
- `reader_what`: max 20 words
- `reader_why`: max 20 words or empty
- `reader_more`: 2–5 short sentences, max 135 words

Plain educated English. Explain necessary technical language. WHY must describe a source-supported mechanism;
otherwise leave it blank and set `why_supported` false.

For a recovered work, `verification.evidence_depth` must be exactly one of:
- `full_text_primary`
- `full_text_repository_copy`
- `official_full_document`
- `full_text_or_substantive_primary`
- `substantive_primary_after_recovery`

Use `substantive_primary_after_recovery` only when full text could not legitimately be recovered after the entire
mandatory retrieval ladder, but a substantive matching primary source still supports a defensible decision.
`abstract_only`, `title_only`, snippets, scanner prose, and search-result text are never enough.

## Required result structure

Return exactly one UTF-8 file named `deep_scan_results.json` (or a ZIP containing it):

```json
{
  "format": "radar-deep-scan-results-v2",
  "package_id": "COPY EXACTLY FROM manifest.json",
  "results": [
    {
      "record_key": "COPY EXACTLY FROM JOB",
      "source_hash": "COPY EXACTLY FROM JOB",
      "identity_hash": "COPY EXACTLY FROM JOB",
      "verification": {
        "identity_verified": true,
        "evidence_depth": "full_text_or_substantive_primary",
        "retrieval_attempts": [
          {"step":"supplied_url","outcome":"success","note":"matching journal article page"},
          {"step":"doi","outcome":"success","note":"DOI matched title/authors"}
        ],
        "recovered_sources": [
          {"kind":"publisher_full_text","url":"https://...","title":"...","evidence_used":true}
        ],
        "verification_note": "short audit note"
      },
      "admission": {
        "decision": "keep",
        "target_strand": "A",
        "reason_code": "A_SUBSTANTIVE_EU_RI",
        "reason": "short evidence-grounded explanation"
      },
      "metadata_correction": {
        "fields": {},
        "unset": [],
        "reason": ""
      },
      "duplicate": {
        "status": "unique",
        "duplicate_of": "",
        "reason": ""
      },
      "reader_title": "plain heading",
      "reader_what": "central verified finding/argument/development",
      "reader_why": "supported significance or empty",
      "reader_more": "2–5 short explanatory sentences",
      "deep_analysis": {
        "work_kind": "empirical study / policy report / current development / etc.",
        "research_question": "or empty",
        "main_finding": "plain verified main finding/claim",
        "method_or_basis": "method and evidence actually used",
        "qualification": "important caveat/status/limit",
        "radar_relevance": "specific verified Radar relevance, or why it fails",
        "why_supported": true,
        "confidence": "high"
      }
    }
  ]
}
```

`confidence` is `high`, `medium` or `low`. `target_strand` is `A`, `B` or `C` for KEEP/REVIEW.
For DROP/DROP_UNVERIFIABLE it may be the original strand or empty.

### Hard validation rules

- KEEP/REVIEW/DROP of a recovered work requires `identity_verified: true` and at least one recovered source
  actually used as evidence. `title_only` and `search_snippet` are not acceptable evidence depths.
- `drop_unverifiable` requires all six mandatory retrieval steps to be reported. If no DOI exists, the DOI step
  still appears with outcome `not_applicable`. Each step needs a specific audit note (what was searched/opened
  and what happened); repeated generic notes are rejected. A DROP_UNVERIFIABLE result cannot simultaneously
  claim a successful recovery step.
- If the supplied URL fails or is not the work, a recovered KEEP/REVIEW/DROP must explicitly report which
  later recovery-ladder step actually found the matching work.
- Do not return KEEP merely because scanner/legacy Deep Scan prose looks plausible.
- Do not return REVIEW merely because retrieval was hard. If the work cannot be substantiated after the ladder,
  it is `drop_unverifiable`.
- If `duplicate.status` is `duplicate`, the canonical key must be one of the supplied possible duplicate keys and
  admission must be DROP with an appropriate duplicate reason.
- Do not modify `record_key`, `identity_hash` or `source_hash`. V2 import uses the stable identity hash so ordinary scanner wording changes do not invalidate careful source verification.

## Partial completion

Partial completion is safe. If your session cannot finish the package, return only carefully completed records.
Do not add placeholders. GitHub will import them and the remaining records will appear in the next package.

Before returning the file, verify every result matches the correct work, the evidence trace is real, the admission
follows A/B/C criteria, corrections are supported, and the JSON is valid.
"""

START_HERE = r"""RADAR DEEP SCAN V2 PACKAGE

This is an authoritative re-verification package. Give the entire ZIP to a browsing-capable LLM and say:

    Process this Deep Scan V2 package strictly according to INSTRUCTIONS.md. Go deeply and systematically,
    process records in supplied order, exhaust the mandatory recovery ladder for difficult records, and return
    deep_scan_results.json (or a ZIP containing it). Do not cherry-pick and do not keep unverifiable records.

The automatic scanner and any older Deep Scan text are provisional evidence only. V2 can correct metadata,
change admission, and remove bad/unverifiable evidence from the active Radar after GitHub validation.
Partial completion is safe; never fabricate unfinished records.
"""


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def package_id_for(rows: list[tuple[str, str, str, dict[str, Any], str]]) -> str:
    seed = "\n".join(f"{key}|{h}" for _strand, key, h, _r, _reason in rows)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{digest}"


def source_for(item: tuple[str, str, str, dict[str, Any], str]):
    strand, key, h, r, reason = item
    src = fetch_source(clean(r.get("link") or r.get("url")))
    return strand, key, h, r, reason, src


def _norm_title(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()


def _doi(row: dict[str, Any]) -> str:
    value = clean(row.get("doi"))
    if not value:
        link = clean(row.get("link") or row.get("url"))
        m = re.search(r"doi\.org/(10\.\d{4,9}/[^?#\s]+)", link, re.I)
        value = m.group(1) if m else ""
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I).lower().rstrip("/")


def duplicate_index(doc: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    rows = [(strand, r) for strand, r in iter_records(doc)]
    out: dict[str, list[dict[str, str]]] = {}
    for i, (strand, row) in enumerate(rows):
        key = record_key(row)
        if not key:
            continue
        doi = _doi(row)
        title = _norm_title(row.get("title") or row.get("headline"))
        matches: list[dict[str, str]] = []
        for j, (other_strand, other) in enumerate(rows):
            if i == j:
                continue
            other_key = record_key(other)
            if not other_key or other_key == key:
                continue
            other_doi = _doi(other)
            other_title = _norm_title(other.get("title") or other.get("headline"))
            reason = ""
            if doi and other_doi and doi == other_doi:
                reason = "same_doi"
            elif title and other_title and len(title) >= 24 and title == other_title:
                reason = "exact_normalized_title"
            if reason:
                matches.append({
                    "record_key": other_key,
                    "strand": other_strand.replace("strand_", "").upper(),
                    "title": clean(other.get("title") or other.get("headline")),
                    "source": clean(other.get("source")),
                    "reason": reason,
                })
        if matches:
            out[key] = matches[:8]
    return out



def same_key_variants(doc: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for strand, row in iter_records(doc):
        key = record_key(row)
        if not key:
            continue
        out.setdefault(key, []).append({
            "strand": strand.replace("strand_", "").upper(),
            "automatic_scanner": scanner_fields(row),
        })
    return {k: v for k, v in out.items() if len(v) > 1}

def build_job(row, ordinal: int, sidecar: dict[str, Any], dupes: dict[str, list[dict[str, str]]], variants: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    strand, key, h, r, reason, src = row
    existing = sidecar.get("records", {}).get(key)
    return {
        "job_number": ordinal,
        "record_key": key,
        "source_hash": h,
        "identity_hash": identity_hash(r),
        "strand": ("A" if strand == "frontier_evidence" else strand.replace("strand_", "").upper()),
        "queue_reason": reason,
        "automatic_scanner": scanner_fields(r),
        "same_record_key_variants": variants.get(key, []),
        "legacy_deep_scan": existing if isinstance(existing, dict) else None,
        "possible_duplicates": dupes.get(key, []),
        "source_material": {
            "read_mode": src.mode,
            "final_url": src.final_url,
            "retrieval_note": src.note,
            "text": src.text,
        },
        "required_output": {
            "record_key": key,
            "source_hash": h,
            "identity_hash": identity_hash(r),
            "verification": {
                "identity_verified": False,
                "evidence_depth": "",
                "retrieval_attempts": [],
                "recovered_sources": [],
                "verification_note": "",
            },
            "admission": {"decision": "", "target_strand": "", "reason_code": "", "reason": ""},
            "metadata_correction": {"fields": {}, "unset": [], "reason": ""},
            "duplicate": {"status": "unique", "duplicate_of": "", "reason": ""},
            "reader_title": "", "reader_what": "", "reader_why": "", "reader_more": "",
            "deep_analysis": {
                "work_kind": "", "research_question": "", "main_finding": "", "method_or_basis": "",
                "qualification": "", "radar_relevance": "", "why_supported": False, "confidence": "low",
            },
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Create an authoritative offline Deep Scan V2 ZIP")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--sidecar", type=Path, default=SIDECAR)
    ap.add_argument("--output-dir", type=Path, default=Path("deep_scan_out"))
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    ap.add_argument("--max-records", type=int, default=DEFAULT_MAX_RECORDS, help="Maximum records in one human Deep Scan session/package; default 12 for depth; 0 means all pending")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--no-fetch", action="store_true", help="Do not pre-retrieve linked source pages/PDFs")
    args = ap.parse_args()

    doc = json.loads(args.corpus.read_text(encoding="utf-8"))
    sidecar = load_sidecar(args.sidecar)
    todo_all = pending(doc, sidecar)
    pending_total = len(todo_all)
    limit = max(0, int(args.max_records or 0))
    todo = todo_all[:limit] if limit else todo_all
    total = sum(1 for _ in iter_records(doc))
    print(f"Radar records: {total}; needing authoritative Deep Scan V2: {pending_total}; packaged now: {len(todo)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not todo:
        summary = args.output_dir / "NO_DEEP_SCAN_NEEDED.txt"
        summary.write_text("All current Radar records already have authoritative Deep Scan V2 verification.\n", encoding="utf-8")
        print(summary)
        return

    pkg_id = package_id_for(todo)
    dupes = duplicate_index(doc)
    variants = same_key_variants(doc)
    workdir = Path(tempfile.mkdtemp(prefix="radar-deep-scan-v2-"))
    try:
        root = workdir / f"deep_scan_package_{pkg_id}"
        batches = root / "batches"
        batches.mkdir(parents=True)
        (root / "INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8")
        (root / "START_HERE.txt").write_text(START_HERE, encoding="utf-8")

        if args.no_fetch:
            fetched = [(*item, SourceRead("stored_only", "", note="source pre-retrieval disabled; LLM must use the retrieval ladder")) for item in todo]
        else:
            workers = max(1, min(args.workers, 20))
            ordered: dict[int, Any] = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(source_for, item): i for i, item in enumerate(todo)}
                done = 0
                for fut in concurrent.futures.as_completed(futures):
                    idx = futures[fut]
                    try:
                        ordered[idx] = fut.result()
                    except Exception as exc:
                        strand, key, h, r, reason = todo[idx]
                        ordered[idx] = (strand, key, h, r, reason, SourceRead("stored_only", "", note=f"packager error: {clean(exc)[:160]}"))
                    done += 1
                    if done % 25 == 0 or done == len(todo):
                        print(f"Prepared source material for {done}/{len(todo)} works")
            fetched = [ordered[i] for i in range(len(todo))]

        jobs = [build_job(row, i + 1, sidecar, dupes, variants) for i, row in enumerate(fetched)]
        batch_size = max(1, min(args.batch_size, 30))
        batch_files: list[dict[str, Any]] = []
        for start in range(0, len(jobs), batch_size):
            chunk = jobs[start:start + batch_size]
            number = start // batch_size + 1
            filename = f"batch_{number:03d}.json"
            payload = {"format": FORMAT, "package_id": pkg_id, "batch_number": number, "jobs": chunk}
            (batches / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            batch_files.append({"file": f"batches/{filename}", "jobs": len(chunk)})

        counts: dict[str, int] = {}
        source_modes: dict[str, int] = {}
        for job in jobs:
            counts[job["queue_reason"]] = counts.get(job["queue_reason"], 0) + 1
            mode = job["source_material"]["read_mode"]
            source_modes[mode] = source_modes.get(mode, 0) + 1
        manifest = {
            "format": FORMAT, "result_format": RESULT_FORMAT, "package_id": pkg_id, "created_at": utc_now(),
            "current_radar_records": total, "works_in_package": len(jobs), "queue_reasons": counts,
            "source_modes": source_modes, "possible_duplicate_records": len(dupes), "same_record_key_variant_groups": len(variants), "batch_size": batch_size,
            "batches": batch_files, "instructions": "INSTRUCTIONS.md", "expected_result_filename": "deep_scan_results.json",
        }
        (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (root / "RESULT_TEMPLATE.json").write_text(json.dumps({"format": RESULT_FORMAT, "package_id": pkg_id, "results": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        zip_path = args.output_dir / f"deep_scan_package_{pkg_id}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(root.parent))
        shutil.copy2(zip_path, args.output_dir / "deep_scan_package.zip")
        (args.output_dir / "PACKAGE_SUMMARY.txt").write_text(
            f"Deep Scan V2 package: {pkg_id}\nWorks needing authoritative verification: {len(jobs)}\nInternal batches: {len(batch_files)}\n\n"
            "Give deep_scan_package.zip to a browsing-capable LLM and ask it to follow INSTRUCTIONS.md strictly.\n",
            encoding="utf-8",
        )
        print(f"Created {zip_path} with {len(jobs)} works in {len(batch_files)} internal batches")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
