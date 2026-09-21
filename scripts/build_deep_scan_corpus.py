#!/usr/bin/env python3
"""Build a temporary Deep Scan corpus containing public evidence + private Deep-A candidates."""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def record_key(row: dict[str, Any]) -> str:
    link = clean(row.get("link") or row.get("url"))
    if link:
        return f"link:{link}"
    doi = clean(row.get("doi") or row.get("_doi")).lower()
    if doi:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi).removeprefix("doi:")
        return f"doi:{doi}"
    rid = clean(row.get("id") or row.get("record_id") or row.get("fingerprint"))
    return f"id:{rid}" if rid else ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=ROOT / "radar.json")
    ap.add_argument("--pool", type=Path, default=ROOT / "deep_a_candidates.json")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    base = json.loads(args.corpus.read_text(encoding="utf-8"))
    if not isinstance(base, dict):
        raise SystemExit("radar corpus must be a JSON object")
    out = copy.deepcopy(base)
    pool = {"candidates": []}
    if args.pool.exists():
        pool = json.loads(args.pool.read_text(encoding="utf-8"))
        if not isinstance(pool, dict):
            pool = {"candidates": []}

    known: set[str] = set()
    for collection in ("strand_a", "strand_b", "strand_c", "frontier_evidence"):
        for row in out.get(collection, []) if isinstance(out.get(collection), list) else []:
            if isinstance(row, dict):
                key = record_key(row)
                if key:
                    known.add(key)

    added = 0
    target = out.setdefault("strand_a", [])
    if not isinstance(target, list):
        raise SystemExit("radar strand_a must be a list")
    for row in pool.get("candidates", []) if isinstance(pool.get("candidates"), list) else []:
        if not isinstance(row, dict):
            continue
        key = record_key(row)
        if not key or key in known:
            continue
        staged = copy.deepcopy(row)
        staged["strand"] = "A"
        staged["deep_a_private_candidate"] = True
        target.append(staged)
        known.add(key)
        added += 1

    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Deep Scan temporary corpus: {added} private Deep-A candidate(s) added to public corpus copy.")


if __name__ == "__main__":
    main()
