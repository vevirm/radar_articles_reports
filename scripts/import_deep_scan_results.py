#!/usr/bin/env python3
"""Validate returned offline Deep Scan files and merge safe results into reader_text.json."""
from __future__ import annotations

import argparse
import json
import time
import zipfile
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.deep_read_works import (
        CORPUS, SIDECAR, clean, iter_records, load_sidecar, record_key, source_hash, validate,
    )
except ModuleNotFoundError:  # when run as: python scripts/import_deep_scan_results.py
    from deep_read_works import (  # type: ignore
        CORPUS, SIDECAR, clean, iter_records, load_sidecar, record_key, source_hash, validate,
    )

RESULT_FORMAT = "radar-deep-scan-results-v1"
PROFILE = "deep-reader-offline-v1"


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parse_result_doc(raw: bytes, label: str) -> dict[str, Any]:
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"{label}: not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"{label}: top level must be a JSON object")
    if obj.get("format") != RESULT_FORMAT:
        raise ValueError(f"{label}: format must be {RESULT_FORMAT!r}")
    if not isinstance(obj.get("results"), list):
        raise ValueError(f"{label}: results must be a JSON list")
    return obj


def docs_from_file(path: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    if path.suffix.lower() == ".json":
        yield path.name, parse_result_doc(path.read_bytes(), path.name)
        return
    if path.suffix.lower() != ".zip":
        return
    with zipfile.ZipFile(path) as zf:
        candidates = [n for n in zf.namelist() if n.lower().endswith(".json") and not n.endswith("/")]
        preferred = [n for n in candidates if Path(n).name == "deep_scan_results.json"]
        names = preferred or candidates
        if not names:
            raise ValueError(f"{path.name}: ZIP contains no JSON result file")
        # If several JSON files exist, import only those that identify as result docs.
        found = False
        errors = []
        for name in names:
            try:
                doc = parse_result_doc(zf.read(name), f"{path.name}:{name}")
            except ValueError as exc:
                errors.append(str(exc))
                continue
            found = True
            yield f"{path.name}:{name}", doc
        if not found:
            raise ValueError(f"{path.name}: no valid {RESULT_FORMAT} document found. " + " | ".join(errors[:3]))


def main() -> None:
    ap = argparse.ArgumentParser(description="Import returned offline Deep Scan results")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--sidecar", type=Path, default=SIDECAR)
    ap.add_argument("--inbox", type=Path, default=Path("deep_scan_inbox"))
    ap.add_argument("--files", nargs="*", type=Path, default=None)
    args = ap.parse_args()

    doc = json.loads(args.corpus.read_text(encoding="utf-8"))
    sidecar = load_sidecar(args.sidecar)
    current: dict[str, tuple[str, dict[str, Any], str]] = {}
    for strand, row in iter_records(doc):
        key = record_key(row)
        if key:
            current[key] = (strand, row, source_hash(row))

    if args.files:
        files = [p for p in args.files if p.exists()]
    else:
        files = sorted(p for p in args.inbox.glob("*") if p.is_file() and p.name != ".gitkeep" and p.suffix.lower() in {".json", ".zip"})
    if not files:
        print("No Deep Scan result files found in inbox.")
        return

    table = sidecar.setdefault("records", {})
    avoid_whys = [clean(v.get("reader_why")) for v in table.values() if isinstance(v, dict) and clean(v.get("reader_why"))]
    accepted_count = 0
    rejected_count = 0
    duplicate_count = 0
    stale_count = 0
    seen_pairs: set[tuple[str, str]] = set()
    imported_files: list[Path] = []
    file_failures: list[str] = []

    for path in files:
        file_had_valid_doc = False
        try:
            docs = list(docs_from_file(path))
        except Exception as exc:
            file_failures.append(f"{path.name}: {clean(exc)}")
            continue
        for label, result_doc in docs:
            file_had_valid_doc = True
            package_id = clean(result_doc.get("package_id")) or "unknown-package"
            for idx, raw in enumerate(result_doc.get("results", []), 1):
                if not isinstance(raw, dict):
                    print(f"REJECT {label} result {idx}: result is not an object")
                    rejected_count += 1
                    continue
                key = clean(raw.get("record_key"))
                h = clean(raw.get("source_hash"))
                if not key or not h:
                    print(f"REJECT {label} result {idx}: missing record_key/source_hash")
                    rejected_count += 1
                    continue
                pair = (key, h)
                if pair in seen_pairs:
                    duplicate_count += 1
                    continue
                seen_pairs.add(pair)
                cur = current.get(key)
                if not cur:
                    print(f"REJECT {label} result {idx}: record no longer exists: {key[:100]}")
                    rejected_count += 1
                    continue
                strand, _row, current_hash = cur
                if h != current_hash:
                    print(f"STALE {label} result {idx}: scanner material changed since package creation")
                    stale_count += 1
                    continue

                existing = table.get(key)
                if isinstance(existing, dict) and existing.get("profile") in {
                    "deep-reader-v2", "deep-reader-v2.1", "deep-reader-offline-v1"
                }:
                    # First valid Deep Scan completes the work. A late/duplicate
                    # package must not silently reread or overwrite it.
                    duplicate_count += 1
                    continue

                normalized = {
                    "reader_title": raw.get("reader_title"),
                    "reader_what": raw.get("reader_what"),
                    "reader_why": raw.get("reader_why"),
                    "reader_more": raw.get("reader_more"),
                    "deep_analysis": raw.get("deep_analysis"),
                }
                accepted, problems = validate(normalized, avoid_whys)
                if not accepted.get("reader_what"):
                    print(f"REJECT {label} result {idx}: no valid reader_what ({'; '.join(problems)})")
                    rejected_count += 1
                    continue

                now = utc_now()
                entry = {
                    "profile": PROFILE,
                    "strand": strand,
                    "source_hash": h,
                    **accepted,
                    "deep_read_mode": "offline_llm_package",
                    "reader_text_model": clean(raw.get("processor")) or "user-provided-llm-subscription",
                    "reader_text_written_at": now,
                    "deep_scan_package_id": package_id,
                }
                table[key] = entry
                if entry.get("reader_why"):
                    avoid_whys.append(entry["reader_why"])
                accepted_count += 1
                if problems:
                    print(f"ACCEPT {label} result {idx} with safeguards: {'; '.join(problems)}")
        if file_had_valid_doc:
            imported_files.append(path)

    if file_failures:
        print("Invalid result files:")
        for x in file_failures:
            print(" -", x)
        # Do not delete or silently ignore malformed user uploads.
        raise SystemExit(2)

    if accepted_count:
        now = utc_now()
        sidecar["version"] = 2
        sidecar["profile"] = PROFILE
        sidecar["generated_at"] = now
        args.sidecar.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Only remove files after their document structure was valid. A result can be
    # partially stale/rejected and still be safely consumed. Never-read/rejected
    # records remain pending; already completed Deep Scan works stay completed.
    for path in imported_files:
        try:
            path.unlink()
        except OSError as exc:
            raise SystemExit(f"Imported results but could not remove inbox file {path}: {exc}") from exc

    print(
        f"Deep Scan import: accepted {accepted_count}; stale {stale_count}; "
        f"rejected {rejected_count}; duplicates {duplicate_count}."
    )
    print("radar.json was not modified. Unfinished/rejected never-read works remain eligible for the next package.")


if __name__ == "__main__":
    main()
