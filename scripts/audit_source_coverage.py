#!/usr/bin/env python3
"""Read-only report of configured institutional discovery vs last observed scan.

This file is deliberately outside scanner execution: it cannot change discovery,
admission, corpus, cursors, or retry history. See EUROPE_DISCOVERY_REUSE_PATCH.md.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WATCH = ("consilium.europa.eu", "cordis.europa.eu", "epo.org", "oecd.org", "chathamhouse.org")


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def audit(config: dict, radar: dict) -> dict:
    sources = [s for s in config.get("institution_sources", []) if isinstance(s, dict) and s.get("domain")]
    profiles = _as_dict(config.get("institution_source_adapters"))
    diag = _as_dict(radar.get("scan_diagnostics"))
    state = _as_dict(radar.get("scan_state"))
    attempts = _as_dict(diag.get("source_transport_attempts"))
    health = _as_dict(diag.get("source_transport_health"))
    routes = _as_dict(diag.get("institution_discovery_routes"))
    domains = {}
    for src in sources:
        domain = str(src["domain"]).lower().removeprefix("www.")
        profile = _as_dict(profiles.get(domain))
        attempt = _as_dict(attempts.get(domain))
        last = _as_dict(health.get(domain))
        route = _as_dict(routes.get(domain))
        status = attempt.get("status") or last.get("last_status") or "never_reported"
        domains[domain] = {
            "name": src.get("name"), "tier": src.get("tier"),
            "configured_feeds": len(src.get("feeds") or []),
            "configured_hubs": len(profile.get("hub_paths") or []) + len(profile.get("seed_urls") or []),
            "latest_status": status,
            "latest_attempt_at": last.get("last_attempt_at"),
            "latest_jobs_found": attempt.get("jobs_found", last.get("last_jobs_found")),
            "latest_route_details": route if route else None,
            "source_was_checked_last_scan": domain in attempts,
            "consecutive_failures": last.get("consecutive_failures", 0),
        }
    status_counts = Counter(v["latest_status"] for v in domains.values())
    unhealthy = [k for k, v in domains.items() if v["latest_status"] in {"failed", "degraded", "unknown", "attempting"}]
    return {
        "last_scan_completed_at": radar.get("run_completed_at") or radar.get("last_updated"),
        "configured_institutional_sources": len(sources),
        "configured_institutional_domains": len(domains),
        "adapter_profiles_configured": len(profiles),
        "domains_reported_in_latest_scan": sum(v["source_was_checked_last_scan"] for v in domains.values()),
        "institution_cursor": state.get("institution_cursor"),
        "institution_adapter_cursor": state.get("institution_source_adapter_cursor"),
        "completed_institution_cycles": state.get("institution_completed_cycles", "not_recorded"),
        "current_or_last_status_counts": dict(sorted(status_counts.items())),
        "unhealthy_domains": unhealthy,
        "watch_domains": {d: domains.get(d) for d in WATCH},
        "domains": domains,
        "notes": [
            "A configured URL or hub is not evidence that GitHub fetched it successfully.",
            "A healthy transport or candidate job is not a successful research admission.",
            "Only the most recent reported scan has per-route detail; historical diagnostics may predate the patch.",
            "Not scheduled in the current scan is not a new transport failure.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "radar_config.json")
    parser.add_argument("--radar", type=Path, default=ROOT / "radar.json")
    parser.add_argument("--json", action="store_true", help="Write full structured report to stdout")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    radar = json.loads(args.radar.read_text(encoding="utf-8"))
    report = audit(config, radar)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    print("EUROPE RADAR — INSTITUTIONAL SOURCE COVERAGE (read-only)")
    print(f"Last completed scan: {report['last_scan_completed_at']}")
    print(f"Configured sources/domains: {report['configured_institutional_sources']}/{report['configured_institutional_domains']}")
    print(f"Configured adapter profiles: {report['adapter_profiles_configured']}")
    print(f"Domains attempted in latest scan: {report['domains_reported_in_latest_scan']}")
    print(f"Rotation cursor: {report['institution_cursor']} | Adapter cursor: {report['institution_adapter_cursor']}")
    print(f"Completed institution cycles: {report['completed_institution_cycles']}")
    print(f"Reported status counts (including carried-forward): {report['current_or_last_status_counts']}")
    print(f"Unhealthy domains: {', '.join(report['unhealthy_domains']) or '(none reported)'}")
    print("\nFOCUS SOURCES")
    for domain, info in report["watch_domains"].items():
        if not info:
            print(f"  {domain}: NOT CONFIGURED")
            continue
        route = info.get("latest_route_details") or {}
        print(f"  {domain}: tier={info['tier']} status={info['latest_status']} "
              f"feeds={info['configured_feeds']} hubs={info['configured_hubs']} "
              f"last_jobs={info['latest_jobs_found']} "
              f"route_jobs(adapter/feed/sitemap/fallback)="
              f"{route.get('adapter_candidate_jobs', '-')}/{route.get('feed_candidate_jobs', '-')}/"
              f"{route.get('sitemap_entry_urls', '-')}/{route.get('fallback_candidate_jobs', '-')}")
    print("\nInterpretation: source transport, candidate discovery, readable extraction and admission are different stages.")
    print("Neither a configured route nor a quiet scan proves live reachability or research saturation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
