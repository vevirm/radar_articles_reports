#!/usr/bin/env python3
"""Persistent coordination state for parallel Deep Scan V2 worker lanes.

The authoritative verification itself still lives in reader_text.json / admission_state.json.
This file only coordinates *work assignment* so multiple browsing-capable LLMs do not
receive the same queue head and new chats can see what is assigned, verified, or deferred.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORK_STATE = ROOT / "deep_scan_work_state.json"
PROFILE = "radar-deep-scan-work-state-v1"
DEFAULT_LANES = ("A", "B")
DEFAULT_LANE_SIZE = 36


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def empty_state() -> dict[str, Any]:
    return {
        "version": 1,
        "profile": PROFILE,
        "updated_at": None,
        "lanes": {
            lane: {
                "target_size": DEFAULT_LANE_SIZE,
                "assigned": [],
                "current_package_id": "",
                "package_history": [],
            }
            for lane in DEFAULT_LANES
        },
        "records": {},
        "packages": {},
    }


def load_state(path: Path = DEFAULT_WORK_STATE) -> dict[str, Any]:
    if not path.exists():
        return empty_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Unreadable Deep Scan work state {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid Deep Scan work state root: {path}")
    data.setdefault("version", 1)
    data.setdefault("profile", PROFILE)
    data.setdefault("updated_at", None)
    lanes = data.setdefault("lanes", {})
    for lane in DEFAULT_LANES:
        row = lanes.setdefault(lane, {})
        row.setdefault("target_size", DEFAULT_LANE_SIZE)
        row.setdefault("assigned", [])
        row.setdefault("current_package_id", "")
        row.setdefault("package_history", [])
    data.setdefault("records", {})
    data.setdefault("packages", {})
    return data


def save_state(state: dict[str, Any], path: Path = DEFAULT_WORK_STATE) -> None:
    state["version"] = 1
    state["profile"] = PROFILE
    state["updated_at"] = utc_now()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _unique(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def sync_verified(state: dict[str, Any], reader: dict[str, Any]) -> None:
    """Mirror authoritative V2 completion into the human/audit coordination ledger."""
    records = state.setdefault("records", {})
    table = reader.get("records", {}) if isinstance(reader, dict) else {}
    verified = {
        key for key, row in table.items()
        if isinstance(row, dict) and row.get("profile") == "deep-reader-v2-authoritative"
    }
    for key in verified:
        entry = records.setdefault(key, {})
        entry["status"] = "verified"
        entry["verified_at"] = row_time = str(table[key].get("reader_text_written_at") or "")
        if not row_time:
            entry["verified_at"] = entry.get("verified_at") or utc_now()
        entry["verified_package_id"] = str(table[key].get("deep_scan_package_id") or entry.get("verified_package_id") or "")
    for lane_row in state.get("lanes", {}).values():
        assigned = lane_row.get("assigned", []) if isinstance(lane_row, dict) else []
        lane_row["assigned"] = [k for k in assigned if k not in verified]


def assigned_keys(state: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for lane_row in state.get("lanes", {}).values():
        if not isinstance(lane_row, dict):
            continue
        out.update(k for k in lane_row.get("assigned", []) if isinstance(k, str) and k)
    return out


def deferred_keys(state: dict[str, Any]) -> set[str]:
    return {
        key for key, row in state.get("records", {}).items()
        if isinstance(row, dict) and row.get("status") == "deferred"
    }


def fill_lane(
    state: dict[str, Any],
    lane: str,
    pending_keys: list[str],
    *,
    target_size: int = DEFAULT_LANE_SIZE,
) -> list[str]:
    """Keep existing unresolved lane order, then append oldest unassigned pending work."""
    lane = lane.upper()
    if lane not in state.setdefault("lanes", {}):
        state["lanes"][lane] = {
            "target_size": target_size,
            "assigned": [],
            "current_package_id": "",
            "package_history": [],
        }
    lane_row = state["lanes"][lane]
    lane_row["target_size"] = int(target_size)
    pending_set = set(pending_keys)
    deferred = deferred_keys(state)
    current = [k for k in lane_row.get("assigned", []) if k in pending_set and k not in deferred]
    current = _unique(current)
    occupied_elsewhere: set[str] = set()
    for other, row in state.get("lanes", {}).items():
        if other == lane or not isinstance(row, dict):
            continue
        occupied_elsewhere.update(k for k in row.get("assigned", []) if isinstance(k, str))
    occupied_elsewhere.update(deferred)
    need = max(0, int(target_size) - len(current))
    if need:
        for key in pending_keys:
            if key in current or key in occupied_elsewhere:
                continue
            current.append(key)
            rec = state.setdefault("records", {}).setdefault(key, {})
            rec["status"] = "assigned"
            rec["lane"] = lane
            rec.setdefault("assigned_at", utc_now())
            need -= 1
            if need <= 0:
                break
    lane_row["assigned"] = current
    # Keep the record audit in sync for retained assignments too.
    for key in current:
        rec = state.setdefault("records", {}).setdefault(key, {})
        rec["status"] = "assigned"
        rec["lane"] = lane
        rec.setdefault("assigned_at", utc_now())
    return current


def register_package(state: dict[str, Any], lane: str, package_id: str, record_keys: list[str]) -> None:
    lane = lane.upper()
    now = utc_now()
    state.setdefault("packages", {})[package_id] = {
        "lane": lane,
        "created_at": now,
        "record_keys": list(record_keys),
    }
    lane_row = state.setdefault("lanes", {}).setdefault(lane, {})
    lane_row["current_package_id"] = package_id
    hist = lane_row.setdefault("package_history", [])
    if package_id not in hist:
        hist.append(package_id)
    lane_row["package_history"] = hist[-40:]
    for key in record_keys:
        rec = state.setdefault("records", {}).setdefault(key, {})
        rec["status"] = "assigned"
        rec["lane"] = lane
        rec["last_package_id"] = package_id
        rec.setdefault("assigned_at", now)


def package_info(state: dict[str, Any], package_id: str) -> dict[str, Any] | None:
    row = state.get("packages", {}).get(package_id)
    return row if isinstance(row, dict) else None


def expected_remaining_for_package(
    state: dict[str, Any],
    package_id: str,
    reader: dict[str, Any],
) -> list[str] | None:
    pkg = package_info(state, package_id)
    if not pkg:
        return None
    verified = {
        key for key, row in reader.get("records", {}).items()
        if isinstance(row, dict) and row.get("profile") == "deep-reader-v2-authoritative"
    }
    deferred = deferred_keys(state)
    return [
        key for key in pkg.get("record_keys", [])
        if isinstance(key, str) and key not in verified and key not in deferred
    ]


def mark_verified(state: dict[str, Any], key: str, package_id: str, when: str | None = None) -> None:
    when = when or utc_now()
    rec = state.setdefault("records", {}).setdefault(key, {})
    lane = rec.get("lane")
    rec.update({
        "status": "verified",
        "verified_at": when,
        "verified_package_id": package_id,
    })
    if lane in state.get("lanes", {}):
        state["lanes"][lane]["assigned"] = [k for k in state["lanes"][lane].get("assigned", []) if k != key]


def mark_deferred(
    state: dict[str, Any],
    key: str,
    package_id: str,
    *,
    reason: str,
    verification: dict[str, Any],
    when: str | None = None,
) -> None:
    when = when or utc_now()
    rec = state.setdefault("records", {}).setdefault(key, {})
    lane = rec.get("lane")
    rec.update({
        "status": "deferred",
        "deferred_at": when,
        "deferred_package_id": package_id,
        "defer_reason": reason,
        "verification": verification,
    })
    if lane in state.get("lanes", {}):
        state["lanes"][lane]["assigned"] = [k for k in state["lanes"][lane].get("assigned", []) if k != key]


def status_counts(state: dict[str, Any], reader: dict[str, Any], pending_keys: list[str]) -> dict[str, Any]:
    verified = {
        key for key, row in reader.get("records", {}).items()
        if isinstance(row, dict) and row.get("profile") == "deep-reader-v2-authoritative"
    }
    deferred = deferred_keys(state)
    assigned = assigned_keys(state)
    return {
        "verified": len(verified),
        "pending_total": len(pending_keys),
        "assigned": len(assigned),
        "deferred": len(deferred),
        "unassigned_pending": len([k for k in pending_keys if k not in assigned and k not in deferred]),
    }


def write_status_markdown(
    state: dict[str, Any],
    reader: dict[str, Any],
    pending_keys: list[str],
    path: Path,
) -> None:
    counts = status_counts(state, reader, pending_keys)
    lines = [
        "# Deep Scan V2 work status",
        "",
        "This file is generated from the authoritative Deep Scan sidecar plus the persistent worker-assignment ledger.",
        "It exists so a new chat or operator can see what has already been verified and what each worker currently owns.",
        "",
        f"- Authoritative V2 verified: **{counts['verified']}**",
        f"- Still needing V2 verification: **{counts['pending_total']}**",
        f"- Currently assigned to workers: **{counts['assigned']}**",
        f"- Deferred after exhaustive recovery: **{counts['deferred']}**",
        f"- Pending and not yet assigned: **{counts['unassigned_pending']}**",
        "",
        "## Worker lanes",
        "",
    ]
    for lane in sorted(state.get("lanes", {})):
        row = state["lanes"][lane]
        assigned = row.get("assigned", []) if isinstance(row, dict) else []
        lines.extend([
            f"### Worker {lane}",
            f"- Current package: `{row.get('current_package_id') or 'none'}`",
            f"- Assigned unresolved records: **{len(assigned)}**",
        ])
        if assigned:
            for i, key in enumerate(assigned[:8], 1):
                lines.append(f"  {i}. `{key}`")
            if len(assigned) > 8:
                lines.append(f"  - … plus {len(assigned) - 8} more in the package manifest")
        lines.append("")
    deferred_rows = [
        (key, row) for key, row in state.get("records", {}).items()
        if isinstance(row, dict) and row.get("status") == "deferred"
    ]
    if deferred_rows:
        lines.extend(["## Deferred recovery queue", ""])
        for key, row in deferred_rows[:30]:
            lines.append(f"- `{key}` — {row.get('defer_reason') or 'access/recovery unresolved'}")
        if len(deferred_rows) > 30:
            lines.append(f"- … plus {len(deferred_rows) - 30} more")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
