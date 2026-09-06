#!/usr/bin/env python3
"""Post-scan security boundary for radar.json.

Allows the clean 200-item baseline to become a cumulative public A/B corpus. After bootstrap,
ordinary scans may keep the same count or increase it; they must not silently discard accepted
A/B evidence. Strand C retains its separate expiry policy.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RADAR = ROOT / "radar.json"


def parse(raw: bytes | str, label: str) -> dict:
    try:
        doc = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    except Exception as exc:
        raise SystemExit(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise SystemExit(f"{label} root is not a JSON object")
    return doc


def items(doc: dict, key: str) -> list[dict]:
    value = doc.get(key, [])
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def norm_title(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def identity_sets(rows: list[dict]) -> tuple[set[str], set[str]]:
    links: set[str] = set()
    titles: set[str] = set()
    for item in rows:
        link = str(item.get("link") or item.get("url") or "").strip().lower().rstrip("/")
        title = norm_title(item.get("title") or item.get("headline"))
        if link:
            links.add(link)
        if title:
            titles.add(title)
    return links, titles


def baseline_seed(doc: dict) -> bool:
    marker = doc.get("fresh_repository_seed")
    return bool(
        isinstance(marker, dict)
        and str(marker.get("version") or "").strip() == "v1"
        and len(items(doc, "strand_a")) == 190
        and len(items(doc, "strand_b")) == 10
        and not items(doc, "ab_archive")
        and not items(doc, "strand_c")
        and not doc.get("scan_state")
        and not doc.get("scan_history")
        and not doc.get("last_updated")
        and not doc.get("run_completed_at")
        and not doc.get("first_scan_complete")
    )


def preserve_accepted_history(old: dict, new: dict, *, allow_cleanup: bool) -> None:
    if allow_cleanup:
        return
    old_rows = items(old, "strand_a") + items(old, "strand_b") + items(old, "ab_archive")
    new_rows = items(new, "strand_a") + items(new, "strand_b") + items(new, "ab_archive")
    new_links, new_titles = identity_sets(new_rows)
    missing: list[str] = []
    for item in old_rows:
        link = str(item.get("link") or item.get("url") or "").strip().lower().rstrip("/")
        title = norm_title(item.get("title") or item.get("headline"))
        if (link and link in new_links) or (title and title in new_titles):
            continue
        missing.append(str(item.get("title") or link or "<untitled>"))
    if missing:
        raise SystemExit(
            f"accepted A/B history lost {len(missing)} item(s) across active+archive; "
            f"sample: {'; '.join(missing[:8])}"
        )


def main() -> int:
    if not RADAR.is_file():
        raise SystemExit("radar.json is missing after the scan")
    new_raw = RADAR.read_bytes()
    new = parse(new_raw, "new radar.json")
    try:
        old_raw = subprocess.check_output(["git", "show", "HEAD:radar.json"], cwd=ROOT)
    except Exception as exc:
        raise SystemExit(f"cannot read pre-scan radar.json from HEAD: {exc}") from exc
    old = parse(old_raw, "previous radar.json")
    fresh = baseline_seed(old)

    old_size, new_size = len(old_raw), len(new_raw)
    if fresh:
        if new_size <= old_size * 0.25 or new_size > 12_000_000:
            raise SystemExit(f"fresh-start radar.json size is abnormal: {old_size} -> {new_size}")
    else:
        if new_size <= old_size * 0.25 or new_size > old_size * 4:
            raise SystemExit(f"radar.json size is abnormal: {old_size} -> {new_size}")

    if fresh:
        if new.get("fresh_repository_seed"):
            raise SystemExit("first successful scan did not consume fresh_repository_seed")
        if not new.get("first_scan_complete"):
            raise SystemExit("first successful scan did not mark first_scan_complete")
        if not isinstance(new.get("scan_state"), dict) or not new.get("scan_state"):
            raise SystemExit("first successful scan did not create scan_state/cursors")
        history = new.get("scan_history")
        if not isinstance(history, list) or not history:
            raise SystemExit("first successful scan did not create scan_history")
        if len(items(new, "strand_a")) + len(items(new, "strand_b")) < 200:
            raise SystemExit("first successful scan lost part of the 200-item A+B baseline")
        if items(new, "ab_archive"):
            raise SystemExit("fresh cumulative run unexpectedly hid accepted A/B rows in ab_archive")
        preserve_accepted_history(old, new, allow_cleanup=False)
        print(
            "Fresh-start output accepted: baseline preserved, fresh marker consumed, "
            f"new scan_state created, scan_history began with {len(history)} run(s)."
        )
        return 0

    # Normal live-run continuity.
    if not new.get("first_scan_complete") or not isinstance(new.get("scan_state"), dict):
        raise SystemExit("live scanner output lost required incremental state")
    if not isinstance(new.get("scan_history"), list) or not new.get("scan_history"):
        raise SystemExit("live scanner output lost scan_history")

    old_total = sum(len(items(old, k)) for k in ("strand_a", "strand_b", "strand_c"))
    new_total = sum(len(items(new, k)) for k in ("strand_a", "strand_b", "strand_c"))
    if old_total >= 20 and (new_total <= old_total * 0.25 or new_total > old_total * 4):
        raise SystemExit(f"main radar corpus count is abnormal: {old_total} -> {new_total}")

    cleanup = bool(
        new.get("inherited_corpus_audit_this_run")
        or new.get("quality_migration_this_run")
        or (new.get("precision_corpus_cleanup_this_run") and not new.get("active_core_rebalance_this_run"))
    )
    old_public_ab = len(items(old, "strand_a")) + len(items(old, "strand_b"))
    new_public_ab = len(items(new, "strand_a")) + len(items(new, "strand_b"))
    if not cleanup and new_public_ab < old_public_ab:
        raise SystemExit(f"cumulative public A/B corpus shrank unexpectedly: {old_public_ab} -> {new_public_ab}")
    if not cleanup and items(new, "ab_archive"):
        raise SystemExit("cumulative mode unexpectedly moved accepted A/B rows into ab_archive")
    preserve_accepted_history(old, new, allow_cleanup=cleanup)
    print(
        "Live output accepted: incremental state/history present and accepted A/B continuity protected; "
        f"size {old_size}->{new_size}, main corpus {old_total}->{new_total}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
