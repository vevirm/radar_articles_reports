#!/usr/bin/env python3
"""Apply the v24.7.4 Strand-C source policy to an existing radar.json safely.

This is deliberately narrower than full corpus revalidation. It only:
  1. removes active Strand-C rows whose publisher is no longer in the canonical C source universe;
  2. collapses event-level duplicate C coverage using the live scanner's duplicate predicate;
  3. archives removed rows rather than deleting their provenance.

Strands A and B are never modified. Historical data is never modified.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_cleanup_live", SCAN)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {SCAN}")
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)

# Prefer authoritative primary records and the strongest independent/specialist reporting
# when two allowed publishers describe the same event. Unlisted allowed sources still survive;
# this ordering is used only to choose a representative inside a duplicate cluster.
_SOURCE_PRIORITY = {
    "commission.europa.eu": 0,
    "research-and-innovation.ec.europa.eu": 0,
    "digital-strategy.ec.europa.eu": 0,
    "consilium.europa.eu": 0,
    "europarl.europa.eu": 0,
    "joint-research-centre.ec.europa.eu": 0,
    "oecd.org": 0,
    "nato.int": 0,
    "esa.int": 0,
    "cern.ch": 0,
    "epo.org": 0,
    "eib.org": 0,
    "unesco.org": 0,
    "worldbank.org": 0,
    "reuters.com": 10,
    "ft.com": 20,
    "bloomberg.com": 30,
    "politico.eu": 40,
    "sciencebusiness.net": 45,
    "researchprofessionalnews.com": 50,
    "euractiv.com": 55,
    "euobserver.com": 60,
    "euronews.com": 65,
    "economist.com": 70,
    "nature.com": 75,
    "science.org": 80,
}


def _domain(row: dict[str, Any]) -> str:
    d = S.clean_text(row.get("source_domain", "")).lower().removeprefix("www.")
    if d:
        return d
    link = S.clean_text(row.get("link", ""))
    try:
        return (S.urlparse(link).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def _rank(row: dict[str, Any]) -> int:
    domain = _domain(row)
    for configured, score in _SOURCE_PRIORITY.items():
        if domain == configured or domain.endswith("." + configured):
            return score
    return 500


def clean(data: dict[str, Any], now_iso: str) -> tuple[dict[str, Any], dict[str, Any]]:
    out = dict(data)
    original = [dict(x) for x in data.get("strand_c", []) if isinstance(x, dict)]

    trusted: list[tuple[int, dict[str, Any]]] = []
    disallowed: list[dict[str, Any]] = []
    for idx, row in enumerate(original):
        if S.trusted_europe_c_source(
            S.clean_text(row.get("source", "")),
            _domain(row),
            S.clean_text(row.get("link", "")),
        ):
            trusted.append((idx, row))
        else:
            disallowed.append(row)

    # Choose the strongest source as representative of each event cluster, while restoring
    # original site order afterwards. This is not a count cap: every distinct valid event stays.
    chosen: list[tuple[int, dict[str, Any]]] = []
    duplicate_losers: list[dict[str, Any]] = []
    for idx, row in sorted(trusted, key=lambda pair: (_rank(pair[1]), pair[0])):
        if any(S.signals_near_duplicate(row, kept) for _, kept in chosen):
            duplicate_losers.append(row)
        else:
            chosen.append((idx, row))
    chosen.sort(key=lambda pair: pair[0])
    out["strand_c"] = [row for _, row in chosen]

    archive = out.get(S.SIGNAL_ARCHIVE_KEY, []) if isinstance(out.get(S.SIGNAL_ARCHIVE_KEY), list) else []
    archive = S.archive_signal_rows(archive, disallowed, "c_source_policy_v24.7.4", now_iso)
    archive = S.archive_signal_rows(archive, duplicate_losers, "c_event_duplicate_v24.7.4", now_iso)
    out[S.SIGNAL_ARCHIVE_KEY] = archive
    out["c_source_policy_cleanup"] = {
        "version": "v24.7.4-elite-c-balanced",
        "applied_at": now_iso,
        "active_before": len(original),
        "active_after": len(out["strand_c"]),
        "archived_disallowed_source": len(disallowed),
        "archived_event_duplicate": len(duplicate_losers),
        "note": "Source-policy and event-dedup cleanup only; A/B and historical data were not revalidated or modified.",
    }
    return out, out["c_source_policy_cleanup"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=str(ROOT / "radar.json"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    path = Path(args.path)
    data = json.loads(path.read_text(encoding="utf-8"))
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes").replace("+00:00", "Z")
    cleaned, report = clean(data, now_iso)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not args.dry_run:
        path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
