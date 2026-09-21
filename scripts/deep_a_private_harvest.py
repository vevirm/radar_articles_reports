#!/usr/bin/env python3
"""Run the 24-minute Strand-A discovery scanner against a private working corpus.

The public ``radar.json`` is never passed to the Deep-A scanner as its output path.
New A candidates are harvested into ``deep_a_candidates.json`` and remain invisible
until authoritative Deep Scan V2 later returns KEEP.  A small private scan-state file
preserves anti-saturation/cursor memory without moving the main scanner's cursors.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "radar.json"
DEFAULT_POOL = ROOT / "deep_a_candidates.json"
DEFAULT_STATE = ROOT / "deep_a_private_state.json"


def clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def record_key(row: dict[str, Any]) -> str:
    link = clean(row.get("link") or row.get("url"))
    if link:
        return f"link:{link}"
    doi = clean(row.get("doi") or row.get("_doi")).lower()
    if doi:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi).removeprefix("doi:")
        return f"doi:{doi}"
    rid = clean(row.get("id") or row.get("record_id") or row.get("fingerprint"))
    if rid:
        return f"id:{rid}"
    title = re.sub(r"[^a-z0-9]+", " ", clean(row.get("title") or row.get("headline")).lower()).strip()
    return f"title:{title}" if title else ""


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Unreadable JSON {path}: {exc}") from exc


def _merge_probe_registry(base: dict[str, Any], private: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base if isinstance(base, dict) else {})
    for key, row in (private.items() if isinstance(private, dict) else []):
        if not isinstance(row, dict):
            continue
        old = out.get(key) if isinstance(out.get(key), dict) else {}
        if clean(row.get("last_executed_at")) >= clean(old.get("last_executed_at")):
            out[key] = copy.deepcopy(row)
    return out


def seed_working_corpus(base: dict[str, Any], private_state: dict[str, Any]) -> dict[str, Any]:
    work = copy.deepcopy(base)
    saved = private_state.get("scan_state") if isinstance(private_state, dict) else None
    current = work.get("scan_state") if isinstance(work.get("scan_state"), dict) else {}
    if isinstance(saved, dict):
        # The private scanner owns its continuation cursors, while the probe registry is
        # unioned with the main scanner's registry so Deep-A also avoids territory the main
        # scanner has just searched.
        merged = copy.deepcopy(saved)
        merged["probe_registry"] = _merge_probe_registry(
            current.get("probe_registry") if isinstance(current, dict) else {},
            saved.get("probe_registry") if isinstance(saved, dict) else {},
        )
        work["scan_state"] = merged
    # Keep private run history separate as well.  This affects Deep-A allocation only.
    if isinstance(private_state.get("scan_history"), list):
        work["scan_history"] = copy.deepcopy(private_state["scan_history"])
    for key in ("run_started_at", "run_completed_at", "latest_productive_scan", "last_updated"):
        if private_state.get(key):
            work[key] = private_state[key]
    return work


def save_private_state(work: dict[str, Any], path: Path) -> None:
    out = {
        "version": 1,
        "profile": "deep-a-private-state-v1",
        "updated_at": utc_now(),
        "scan_state": copy.deepcopy(work.get("scan_state") if isinstance(work.get("scan_state"), dict) else {}),
        "scan_history": copy.deepcopy(work.get("scan_history") if isinstance(work.get("scan_history"), list) else [])[-120:],
    }
    for key in ("run_started_at", "run_completed_at", "latest_productive_scan", "last_updated"):
        if work.get(key):
            out[key] = work[key]
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Private Strand-A candidate harvester")
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    ap.add_argument("--state", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--working", type=Path, default=ROOT / ".deep_a_working_radar.json")
    args = ap.parse_args()

    base = load_json(args.corpus, {})
    if not isinstance(base, dict):
        raise SystemExit("radar.json root must be an object")
    pool = load_json(args.pool, {"version": 1, "profile": "deep-a-private-candidate-pool-v1", "candidates": []})
    if not isinstance(pool, dict):
        pool = {"version": 1, "profile": "deep-a-private-candidate-pool-v1", "candidates": []}
    private_state = load_json(args.state, {})
    if not isinstance(private_state, dict):
        private_state = {}

    working = seed_working_corpus(base, private_state)
    args.working.write_text(json.dumps(working, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    env = os.environ.copy()
    env["RADAR_DEEP_A_WORK_CORPUS"] = str(args.working.resolve())
    env["RADAR_STRAND_A_PRIVATE_HARVEST"] = "true"
    try:
        rc = subprocess.call([sys.executable, str(ROOT / "scripts" / "scan_radar_deep_a.py")], cwd=ROOT, env=env)
        if rc != 0:
            return rc
        result = load_json(args.working, {})
        if not isinstance(result, dict):
            raise SystemExit("Deep-A working output is not a JSON object")

        public_keys: set[str] = set()
        for collection in ("strand_a", "strand_b", "strand_c", "frontier_evidence"):
            for row in base.get(collection, []) if isinstance(base.get(collection), list) else []:
                if isinstance(row, dict):
                    key = record_key(row)
                    if key:
                        public_keys.add(key)

        existing_candidates: dict[str, dict[str, Any]] = {}
        for row in pool.get("candidates", []) if isinstance(pool.get("candidates"), list) else []:
            if not isinstance(row, dict):
                continue
            key = record_key(row)
            if key and key not in public_keys:
                existing_candidates[key] = copy.deepcopy(row)

        discovered_at = utc_now()
        newly_staged = 0
        relaxed = 0
        ordinary = 0
        for row in result.get("strand_a", []) if isinstance(result.get("strand_a"), list) else []:
            if not isinstance(row, dict):
                continue
            key = record_key(row)
            if not key or key in public_keys or key in existing_candidates:
                continue
            staged = copy.deepcopy(row)
            staged["deep_a_private_candidate"] = True
            staged["deep_a_private_discovered_at"] = clean(staged.get("first_seen")) or discovered_at
            is_relaxed = bool(staged.get("deep_a_private_recall"))
            staged["deep_a_private_gate"] = "wider_private_recall" if is_relaxed else "ordinary_a_gate"
            staged["new_this_scan"] = False
            staged.setdefault("first_seen", discovered_at)
            existing_candidates[key] = staged
            newly_staged += 1
            if is_relaxed:
                relaxed += 1
            else:
                ordinary += 1

        ordered = list(existing_candidates.values())
        ordered.sort(key=lambda r: (clean(r.get("deep_a_private_discovered_at")), clean(r.get("title"))))
        pool_out = {
            "version": 1,
            "profile": "deep-a-private-candidate-pool-v1",
            "updated_at": discovered_at,
            "publication_policy": "private_until_authoritative_deep_scan_keep",
            "candidates": ordered,
        }
        args.pool.write_text(json.dumps(pool_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        save_private_state(result, args.state)
        print(
            f"Deep-A private harvest: staged {newly_staged} new candidate(s) "
            f"({ordinary} ordinary-gate, {relaxed} wider-private); pool now {len(ordered)}."
        )
        print("Public radar.json was not modified by the Deep-A harvest.")
        return 0
    finally:
        try:
            args.working.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
