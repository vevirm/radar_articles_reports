#!/usr/bin/env python3
"""Create one self-contained offline Deep Scan ZIP for all pending Radar works."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

try:
    from scripts.deep_read_works import (
        CORPUS, SIDECAR, SourceRead, clean, fetch_source, iter_records, load_sidecar, pending, scanner_fields,
    )
except ModuleNotFoundError:  # when run as: python scripts/prepare_deep_scan_package.py
    from deep_read_works import (  # type: ignore
        CORPUS, SIDECAR, SourceRead, clean, fetch_source, iter_records, load_sidecar, pending, scanner_fields,
    )

FORMAT = "radar-deep-scan-package-v1"
RESULT_FORMAT = "radar-deep-scan-results-v1"
DEFAULT_BATCH_SIZE = 15
DEFAULT_WORKERS = 10

INSTRUCTIONS = r"""# Radar Deep Scan — instructions for the LLM

## Your task

This package comes from an EU research-and-innovation Radar. A fast automatic scanner has already found and admitted these works. You are the slower **Deep Scan**.

This package contains works that have **not yet completed Deep Scan**. Once a valid Deep Scan interpretation is imported, that work is considered complete and is not automatically sent for Deep Scan again.

Your job is to **understand each work and improve the Radar's stored interpretation**. This is not merely copy-editing and not merely shortening an abstract.

For every work you process:

1. Read the automatic scanner material to understand why Radar selected it.
2. Read the supplied source material carefully. It may be an abstract, source page, PDF excerpt, or it may be unavailable.
3. Decide what the work actually studies, reports, argues, proposes or finds.
4. Check the automatic scanner's interpretation against the source. Treat the automatic interpretation as a useful hypothesis, not ground truth.
5. Identify the part that is genuinely relevant to this Radar.
6. Produce a clear reader-facing interpretation in ordinary educated English.
7. Preserve uncertainty and status. Do not turn a proposal into an outcome, correlation into causation, a model result into an observed fact, or a title into evidence of a result.

The original publication title is evidence and must **not** be rewritten in the source data. `reader_title` is only a plain-language heading for the Radar page.

## Evidence rules

- Prefer source material over the automatic scanner when they conflict.
- The supplied source text can be partial or noisy. Ignore cookie banners, navigation, references and unrelated page material.
- If source text appears to belong to a different document, ignore it.
- If only a title or thin source material is available, be cautious: say what the work *examines, argues, proposes or reports* rather than claiming a strong finding.
- Do not invent a European strategic consequence merely to fill `reader_why`.
- If a concrete WHY is not supported by the package, return an empty `reader_why` and set `why_supported` to false.
- Keep important limitations or scope conditions in `qualification` and, when useful, `reader_more`.

## Reader language

- Plain educated English.
- One idea per sentence.
- Explain necessary technical concepts in the sentence; otherwise prefer normal words.
- Avoid unexplained acronyms and specialist shorthand.
- Do not paste or lightly paraphrase awkward abstract fragments.
- Avoid generic phrases such as "this is important for innovation". Explain the actual mechanism or leave WHY empty.

Limits:
- `reader_title`: maximum 18 words.
- `reader_what`: maximum 20 words.
- `reader_why`: maximum 20 words, or empty string.
- `reader_more`: 2–5 short sentences, maximum 135 words.

## What to return

Process the numbered JSON files in `batches/`. You may work through them sequentially and use the files rather than trying to hold the entire corpus in conversational memory.

Return **one file** named `deep_scan_results.json` (a ZIP containing that file is also acceptable). It must be valid UTF-8 JSON with this structure:

```json
{
  "format": "radar-deep-scan-results-v1",
  "package_id": "COPY EXACTLY FROM manifest.json",
  "results": [
    {
      "record_key": "COPY EXACTLY FROM THE JOB",
      "source_hash": "COPY EXACTLY FROM THE JOB",
      "reader_title": "plain Radar heading",
      "reader_what": "central source-grounded finding/argument/proposal",
      "reader_why": "concrete supported Radar significance, or empty string",
      "reader_more": "2–5 short explanatory sentences",
      "deep_analysis": {
        "work_kind": "short label, e.g. empirical study, review, policy report, proposal, commentary, current development",
        "research_question": "what the work is trying to establish, or empty",
        "main_finding": "plain statement of the main relevant finding/claim",
        "method_or_basis": "brief description of method/evidence basis, or empty",
        "qualification": "most important caveat/status/limit, or empty",
        "radar_relevance": "specific reason it belongs in this Radar, or empty",
        "why_supported": true,
        "confidence": "high"
      }
    }
  ]
}
```

`confidence` must be `high`, `medium`, or `low`.

**Do not modify `record_key` or `source_hash`.** They are how GitHub safely matches your interpretation to the current scanner record.

## Large packages and partial completion

A package can contain hundreds of works. Do not pretend to have processed records you did not actually read.

If your environment cannot complete the whole package in one run, return a valid `deep_scan_results.json` containing **only the records you completed carefully**. GitHub will import those and automatically include unfinished records in the next package. Partial completion is expected and safe.

Do not fill unfinished records with placeholders.

## Final check before returning the file

For every result, verify:
- it matches the correct work;
- `record_key` and `source_hash` are copied exactly;
- the wording reflects the evidence rather than abstract jargon;
- claims are not stronger than the source;
- WHY is blank if its mechanism is not supported;
- the JSON is valid.

Return the completed file/package to the user. They will upload it to the repository's `deep_scan_inbox` folder; GitHub performs the final validation and import.
"""

START_HERE = r"""RADAR DEEP SCAN PACKAGE

Give this entire ZIP to the LLM you want to use and say:

    Process this Deep Scan package according to INSTRUCTIONS.md and return the completed deep_scan_results.json (or a ZIP containing it).

You do not need to copy prompts or edit the batch files yourself.

The package may contain hundreds of works. INSTRUCTIONS.md explicitly permits partial completion: GitHub will remember completed works and put unfinished ones into the next package.
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


def build_job(row, ordinal: int) -> dict[str, Any]:
    strand, key, h, r, reason, src = row
    return {
        "job_number": ordinal,
        "record_key": key,
        "source_hash": h,
        "strand": strand,
        "queue_reason": reason,
        "automatic_scanner": scanner_fields(r),
        "source_material": {
            "read_mode": src.mode,
            "final_url": src.final_url,
            "retrieval_note": src.note,
            "text": src.text,
        },
        "required_output": {
            "record_key": key,
            "source_hash": h,
            "reader_title": "",
            "reader_what": "",
            "reader_why": "",
            "reader_more": "",
            "deep_analysis": {
                "work_kind": "",
                "research_question": "",
                "main_finding": "",
                "method_or_basis": "",
                "qualification": "",
                "radar_relevance": "",
                "why_supported": False,
                "confidence": "low",
            },
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Create a self-contained offline Deep Scan ZIP")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--sidecar", type=Path, default=SIDECAR)
    ap.add_argument("--output-dir", type=Path, default=Path("deep_scan_out"))
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--no-fetch", action="store_true", help="Do not retrieve linked source pages/PDFs")
    args = ap.parse_args()

    doc = json.loads(args.corpus.read_text(encoding="utf-8"))
    sidecar = load_sidecar(args.sidecar)
    todo = pending(doc, sidecar)
    total = sum(1 for _ in iter_records(doc))
    print(f"Radar records: {total}; pending Deep Scan: {len(todo)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not todo:
        summary = args.output_dir / "NO_DEEP_SCAN_NEEDED.txt"
        summary.write_text("All current Radar records already have a valid Deep Scan interpretation.\n", encoding="utf-8")
        print(summary)
        return

    pkg_id = package_id_for(todo)
    workdir = Path(tempfile.mkdtemp(prefix="radar-deep-scan-"))
    try:
        root = workdir / f"deep_scan_package_{pkg_id}"
        batches = root / "batches"
        batches.mkdir(parents=True)
        (root / "INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8")
        (root / "START_HERE.txt").write_text(START_HERE, encoding="utf-8")

        if args.no_fetch:
            fetched = [(*item, SourceRead("stored_only", "", note="source retrieval disabled for this package")) for item in todo]
        else:
            fetched = []
            workers = max(1, min(args.workers, 20))
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(source_for, item): i for i, item in enumerate(todo)}
                ordered: dict[int, Any] = {}
                done = 0
                for fut in concurrent.futures.as_completed(futures):
                    idx = futures[fut]
                    try:
                        ordered[idx] = fut.result()
                    except Exception as exc:
                        # source_for/fetch_source is already fail-safe; this is a final guard.
                        strand, key, h, r, reason = todo[idx]
                        ordered[idx] = (
                            strand, key, h, r, reason,
                            SourceRead("stored_only", "", note=f"packager error: {clean(exc)[:160]}"),
                        )
                    done += 1
                    if done % 25 == 0 or done == len(todo):
                        print(f"Prepared source material for {done}/{len(todo)} works")
                fetched = [ordered[i] for i in range(len(todo))]

        jobs = [build_job(row, i + 1) for i, row in enumerate(fetched)]
        batch_size = max(1, min(args.batch_size, 50))
        batch_files: list[dict[str, Any]] = []
        for start in range(0, len(jobs), batch_size):
            chunk = jobs[start:start + batch_size]
            number = start // batch_size + 1
            filename = f"batch_{number:03d}.json"
            payload = {
                "format": FORMAT,
                "package_id": pkg_id,
                "batch_number": number,
                "jobs": chunk,
            }
            (batches / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            batch_files.append({"file": f"batches/{filename}", "jobs": len(chunk)})

        counts: dict[str, int] = {}
        source_modes: dict[str, int] = {}
        for job in jobs:
            counts[job["queue_reason"]] = counts.get(job["queue_reason"], 0) + 1
            mode = job["source_material"]["read_mode"]
            source_modes[mode] = source_modes.get(mode, 0) + 1

        manifest = {
            "format": FORMAT,
            "result_format": RESULT_FORMAT,
            "package_id": pkg_id,
            "created_at": utc_now(),
            "current_radar_records": total,
            "works_in_package": len(jobs),
            "queue_reasons": counts,
            "source_modes": source_modes,
            "batch_size": batch_size,
            "batches": batch_files,
            "instructions": "INSTRUCTIONS.md",
            "expected_result_filename": "deep_scan_results.json",
        }
        (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        template = {"format": RESULT_FORMAT, "package_id": pkg_id, "results": []}
        (root / "RESULT_TEMPLATE.json").write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        zip_path = args.output_dir / f"deep_scan_package_{pkg_id}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(root.parent))
        print(f"Created {zip_path} with {len(jobs)} works in {len(batch_files)} internal batches")

        # Fixed-name copy makes GitHub artifact download less confusing.
        fixed = args.output_dir / "deep_scan_package.zip"
        shutil.copy2(zip_path, fixed)
        summary = args.output_dir / "PACKAGE_SUMMARY.txt"
        summary.write_text(
            f"Deep Scan package: {pkg_id}\nWorks needing deep reading: {len(jobs)}\nInternal batches: {len(batch_files)}\n\n"
            "Give deep_scan_package.zip to your LLM and ask it to follow INSTRUCTIONS.md.\n",
            encoding="utf-8",
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
