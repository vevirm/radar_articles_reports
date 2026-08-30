# Historical radar: source-age rule

This historical layer is **not** a radar about the past. It is a separate evidence layer for sources that are older than the main radar's rolling six-month window.

- Historical status is decided by the **publication date of the paper/report**, not by whether its content looks backward or forward.
- The scanner computes the cutoff as **today minus six months** and includes sources strictly before that boundary.
- The lower bound is 1 January 2015, matching the literature base used for the consolidated workforce repository.
- `manual_evidence.json` contains deliberately reviewed EU R&I geopolitical signals. These are persistent and are not overwritten by automated reclassification.
- `curated_seed_evidence.json` is a discovery/backfill queue. Seed entries still need to pass the automated source-quality and relevance gates.
- `Research_Workforce_Consolidated_25_2_historical_geopolitical_manual.xlsx` is the workbook provenance for the manual review layer.

As of 30 August 2026, the rolling six-month boundary is **28 February 2026**, so historical sources are dated no later than **27 February 2026**. This date advances automatically on future scanner runs.
