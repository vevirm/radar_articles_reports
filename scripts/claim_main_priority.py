#!/usr/bin/env python3
"""Claim the research slot for Main before it makes any source requests.

Current workflows already share one GitHub concurrency group.  This extra visible-code
fallback exists because GitHub browser uploads can leave an older hidden Historical workflow
with a different concurrency group. Main is the priority scanner: before Main research starts,
cancel any active/queued Historical workflow run and wait briefly for it to stop.

No repository content is modified by this helper.
"""
from __future__ import annotations

import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = "https://api.github.com"
HIST_SUFFIX = "/.github/workflows/historical-scan.yml"


def request(url: str, method: str = "GET") -> dict:
    token = str(os.environ.get("GITHUB_TOKEN") or "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ri-geopolitics-radar-main-priority",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, method=method, headers=headers)
    with urlopen(req, timeout=10) as r:
        raw = r.read()
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def active_historical(repo: str, current_run: int) -> list[dict]:
    found: list[dict] = []
    for status in ("in_progress", "queued"):
        payload = request(f"{API}/repos/{repo}/actions/runs?status={status}&per_page=100")
        for run in payload.get("workflow_runs", []) if isinstance(payload, dict) else []:
            if not isinstance(run, dict):
                continue
            if int(run.get("id") or 0) == current_run:
                continue
            path = "/" + str(run.get("path") or "").lstrip("/")
            if path.endswith(HIST_SUFFIX):
                found.append(run)
    return found


def main() -> int:
    if str(os.environ.get("GITHUB_ACTIONS") or "").lower() != "true":
        print("Main-priority claim: local run; nothing to cancel.")
        return 0
    repo = str(os.environ.get("GITHUB_REPOSITORY") or "").strip()
    rid = str(os.environ.get("GITHUB_RUN_ID") or "").strip()
    if not repo or not rid.isdigit():
        print("Main-priority claim: Actions identity unavailable; relying on workflow concurrency.")
        return 0
    current = int(rid)
    try:
        peers = active_historical(repo, current)
        if not peers:
            print("Main-priority claim: no Historical scanner is active or queued.")
            return 0
        for run in peers:
            run_id = int(run.get("id") or 0)
            print(f"Main-priority claim: cancelling Historical run {run_id} before Main research starts.")
            try:
                request(f"{API}/repos/{repo}/actions/runs/{run_id}/cancel", method="POST")
            except HTTPError as exc:
                # 409 commonly means it finished between listing and cancellation.
                if exc.code != 409:
                    raise
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            remaining = active_historical(repo, current)
            if not remaining:
                print("Main-priority claim: research slot is clear for Main.")
                return 0
            time.sleep(3)
        print("::error::Historical workflow did not yield within 60 seconds; refusing to overlap Main research.")
        return 1
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        # The shared concurrency group is the primary guarantee in the current workflow.
        # Do not fail a healthy current workflow solely because the API fallback is unavailable.
        print(f"::warning::Main-priority fallback API unavailable ({exc}); relying on shared workflow concurrency.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
