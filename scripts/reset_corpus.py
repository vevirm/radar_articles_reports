#!/usr/bin/env python3
"""Apply the V17.20.47 fresh-start corpus reset to radar.json offline.

This is exactly the reset the scanner performs on its next run when the saved radar
does not yet carry ``corpus_reset.version == corpus_reset_profile_version``. Running it
here lets a repository package ship already reset, so the very first GitHub scan starts
from the retained corpus and fresh discovery state instead of spending time pruning.

Usage:
    python scripts/reset_corpus.py            # rewrite radar.json in place
    python scripts/reset_corpus.py --dry-run  # print the report only
    python scripts/reset_corpus.py --show 40  # also list the top/bottom kept titles
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import scan_radar as scan  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="do not write radar.json")
    ap.add_argument("--force", action="store_true", help="re-apply even if the current marker already matches")
    ap.add_argument("--show", type=int, default=0, help="print N kept and N pruned titles with scores")
    args = ap.parse_args()

    path = ROOT / "radar.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not scan.CORPUS_RESET_PROFILE_VERSION:
        print("corpus_reset_profile_version is empty in radar_config.json; nothing to do.")
        return 0
    if not args.force and not scan.needs_corpus_reset(data):
        print(f"radar.json already carries corpus_reset {scan.corpus_reset_version_of(data)!r}; nothing to do (use --force to re-apply).")
        return 0

    now = dt.datetime.now(dt.timezone.utc)
    now_iso = now.isoformat(timespec="minutes").replace("+00:00", "Z")
    if args.show:
        cells = scan._corpus_reset_matrix_cells(data)
        usage = scan._corpus_reset_reader_usage(data)
        rows = []
        for strand in ("strand_a", "strand_b"):
            for item in data.get(strand, []) or []:
                rows.append((scan.corpus_reset_importance(item, now.date(), cells, usage), strand, item.get("title", "")[:90]))
        rows.sort(key=lambda r: -r[0])
        print("--- highest-importance ---")
        for r in rows[: args.show]:
            print(f"{r[0]:7.2f} {r[1][-1].upper()} {r[2]}")
        print("--- lowest-importance ---")
        for r in rows[-args.show:]:
            print(f"{r[0]:7.2f} {r[1][-1].upper()} {r[2]}")

    reset, report = scan.apply_corpus_reset(data, now_iso, today=now.date())
    reset["quality_migration_this_run"] = True
    reset["corpus_reset_this_run"] = True
    reset["corpus_reset_profile_version"] = scan.CORPUS_RESET_PROFILE_VERSION
    reset["backfill_complete"] = False
    summary = {k: v for k, v in report.items() if k not in {"pruned_identities", "pruned_titles"}}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.dry_run:
        return 0
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(reset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    print(f"Wrote {path} (A={len(reset['strand_a'])}, B={len(reset['strand_b'])}, C={len(reset.get('strand_c', []))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
