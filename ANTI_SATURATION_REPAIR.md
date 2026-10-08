# Metadata recovery anti-starvation repair (8 October 2026)

## Problem addressed

The persistent scholarly metadata queue was processed in storage order. With a per-scan retrieval limit, failing older records repeatedly occupied the same network slots and prevented later records from receiving recovery attempts. Inadequate text was a prominent rejection/defer category in recent scans. This is a **real mechanism that can suppress new discoveries**, but not a demonstration that all zero-yield scans have the same cause.

## Changes

- Retry candidates with fewer previous failures first; process old retries after new records.
- Apply a 1-hour to 7-day exponential cooldown following unsuccessful retrievals.
- Preserve deferred records during cooldown and after a scan exceeds its network budget.
- Record `deferred_metadata_retry_stats` in scan state/stats for observability.
- Do **not** change A/B/C admission criteria or force publication of low-quality records.

## Validation

`python -m unittest discover -s tests -p test_deferred_metadata_fair_retries.py -v`

## Not solved by this patch

This does **not** restore blocked institution URLs, raise external API quotas, recover all missing full text, or prove comprehensive search coverage. A live scanner run is needed to measure incremental discovery yield following installation. The present copy has not been run against external services and no zero-result streak can responsibly be declared fixed yet.

## Installation

Replace `scripts/scan_radar.py` with the patched version; optionally add the accompanying regression test and this note. Alternatively replace your repository using the full repaired archive after backing up live data and credentials. Commit and deploy through your existing workflow; the ZIP is not a live installation.
