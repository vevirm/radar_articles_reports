#!/usr/bin/env python3
"""Best-effort runtime guard against overlapping Main/Historical scanners.

Primary serialization lives in the GitHub workflow concurrency group.  GitHub's web
bulk uploader has repeatedly left hidden ``.github/workflows`` files unchanged, so this
visible helper provides a safe fallback: on a legacy workflow, the later scanner run
exits cleanly before doing research rather than competing with the other scanner.

The helper does not alter scanner methodology, source rotation, admission, or output.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

SCANNER_WORKFLOW_SUFFIXES = (
    "/.github/workflows/radar-scan.yml",
    "/.github/workflows/historical-scan.yml",
)


def _log(message: str) -> None:
    print(f"[scanner-serialization] {message}", flush=True)


def _parse_time(raw: Any) -> dt.datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except Exception:
        return None


def _recent(path: Path, timestamp_key: str, *, minutes: int = 20) -> dict[str, Any] | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(doc, dict):
        return None
    stamp = _parse_time(doc.get(timestamp_key))
    if stamp is None:
        return None
    now = dt.datetime.now(dt.timezone.utc)
    if dt.timedelta(0) <= now - stamp <= dt.timedelta(minutes=minutes):
        return doc
    return None


def _main_rescue_pending(root: Path) -> bool:
    doc = _recent(root / "radar.json", "last_updated")
    if not doc:
        return False
    results = doc.get("scan_results") if isinstance(doc.get("scan_results"), dict) else {}
    mode = str(doc.get("scan_mode") or "").strip().lower()
    return bool(results.get("full_rescue_run_recommended")) and mode != "full_low_yield_rescue"



def deployment_only_push_event(role: str = "historical") -> bool:
    """Return True only when a GitHub push must be deployment-only for *role*.

    The repository is maintained through GitHub's browser bulk uploader. For this project a
    Main Radar upload is intentionally also a manual discovery trigger: the user expects the
    newly uploaded scanner to run immediately. Historical stays separate on push so the two
    research scanners cannot compete for the same runtime slot when a whole repository is
    uploaded. Scheduled and workflow_dispatch runs remain real scans for both roles.

    This role-aware fallback also works when the browser uploader leaves older hidden workflow
    YAML in place: legacy Main push runs are allowed to scan; legacy Historical push runs exit
    before source requests. Local/offline executions are unaffected.
    """
    if str(os.environ.get("GITHUB_ACTIONS") or "").strip().lower() != "true":
        return False
    raw = str(os.environ.get("RADAR_RUN_TRIGGER") or os.environ.get("GITHUB_EVENT_NAME") or "").strip().lower()
    role = str(role or "").strip().lower()
    return raw == "push" and role == "historical"

def _historical_rescue_pending(root: Path) -> bool:
    doc = _recent(root / "historical" / "historical.json", "last_updated")
    if not doc:
        return False
    last = doc.get("last_scan") if isinstance(doc.get("last_scan"), dict) else {}
    low = last.get("low_yield_rotation") if isinstance(last.get("low_yield_rotation"), dict) else {}
    return bool(low.get("full_rescue_run_should_dispatch")) and not bool(last.get("rescue_mode"))


def _active_scanner_runs(repo: str) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo}/actions/runs?status=in_progress&per_page=100"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ri-geopolitics-radar-runtime-serialization-guard",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = str(os.environ.get("GITHUB_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else []
    out: list[dict[str, Any]] = []
    for run in runs if isinstance(runs, list) else []:
        if not isinstance(run, dict):
            continue
        path = "/" + str(run.get("path") or "").lstrip("/")
        if any(path.endswith(suffix) for suffix in SCANNER_WORKFLOW_SUFFIXES):
            out.append(run)
    return out


def defer_if_peer_scanner_active(role: str, root: Path) -> bool:
    """Return True when this legacy-workflow run should exit before scanning.

    Correct current workflows never need this path: their shared concurrency group queues
    one complete normal+rescue cycle behind the other.  This fallback matters only when a
    browser upload left an older hidden workflow in place.
    """
    if str(os.environ.get("GITHUB_ACTIONS") or "").lower() != "true":
        return False

    repo = str(os.environ.get("GITHUB_REPOSITORY") or "").strip()
    run_id_raw = str(os.environ.get("GITHUB_RUN_ID") or "").strip()
    if not repo or not run_id_raw.isdigit():
        return False
    run_id = int(run_id_raw)
    role = str(role or "").strip().lower()

    # Preserve a complete rescue cycle even under an old workflow that dispatches rescue
    # as a second workflow run.  The other scanner defers during the short dispatch gap.
    if role == "historical" and _main_rescue_pending(root):
        _log("Main normal round has just recommended a rescue round; deferring Historical until the Main cycle is complete.")
        return True
    if role == "main" and _historical_rescue_pending(root):
        _log("Historical normal round has just recommended a rescue round; deferring Main until the Historical cycle is complete.")
        return True

    try:
        active = _active_scanner_runs(repo)
    except Exception as exc:
        # Workflow-level serialization is the primary mechanism.  If the public Actions
        # API is briefly unavailable, do not turn a healthy scanner into a hard failure.
        _log(f"Could not inspect active workflow runs ({exc}); continuing under workflow-level serialization.")
        return False

    peers = [r for r in active if int(r.get("id") or 0) != run_id]

    # Whole-repository browser uploads can trigger an old Historical workflow at the
    # same time as Main. Historical push discovery is intentionally suppressed by the
    # role-aware guard above, so that short deployment-only Historical run must never
    # steal the runtime slot from the real Main upload scan. GitHub's Actions API exposes
    # both the workflow path and triggering event, which lets us ignore exactly that peer.
    current_event = str(os.environ.get("RADAR_RUN_TRIGGER") or os.environ.get("GITHUB_EVENT_NAME") or "").strip().lower()
    if role == "main" and current_event == "push":
        peers = [
            r for r in peers
            if not (
                str(r.get("event") or "").strip().lower() == "push"
                and str(r.get("path") or "").endswith("/.github/workflows/historical-scan.yml")
            )
        ]
    if not peers:
        return False

    current = next((r for r in active if int(r.get("id") or 0) == run_id), None)
    if current is None:
        _log("Another research scanner is already active; deferring this legacy-workflow run.")
        return True

    def order_key(run: dict[str, Any]) -> tuple[str, int]:
        return (str(run.get("run_started_at") or run.get("created_at") or ""), int(run.get("id") or 0))

    owner = min(active, key=order_key)
    if int(owner.get("id") or 0) == run_id:
        return False

    _log(
        f"Another research scanner owns the runtime slot (run {owner.get('id')}); "
        "deferring this legacy-workflow run before any source requests are made."
    )
    return True
