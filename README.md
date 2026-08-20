# R&I × Geopolitics Radar — V15 scan repair

V15 is a targeted runtime repair for the GitHub Actions scan. It keeps the balanced relevance criteria, four-month A/B backfill, 12-hour schedule, cumulative A/B/C corpus and zero-config operation.

## What V15 fixes

- The live `radar.json` is now the authoritative cumulative corpus during normal runs. The scanner no longer walks and unions many historical `radar.json` revisions before every scan.
- Malformed/null legacy rows are skipped safely instead of being able to terminate the process before source collection starts.
- Existing A/B/C items are preserved even when all network sources are temporarily unavailable.
- Collector output is structure-validated before deduplication and merge.
- `radar.json` is written atomically.
- The internal network budget is 20 minutes, so the scanner fits inside the currently deployed 30-minute Action.
- No API keys or custom repository secrets are required.
- The active workflow copy has no OpenAlex secret reference; Pages refresh is non-fatal.

## Critical deployment note

This full-repository distribution already includes the active workflow at `.github/workflows/radar-scan.yml` and a visible backup at `RADAR_SCAN_WORKFLOW_COPY.yml`. When replacing the repository, make sure the hidden `.github` folder is included.

## Admission profile

The balanced-relevance policy is retained. Strand A accepts serious research/reports on EU/European R&I and related systems — R&D and scientific capacity, universities, research infrastructures, talent, innovation ecosystems, deep tech, technology development/transfer, technological capabilities and related areas — when there is a substantive geopolitical or geoeconomic connection.

Relevant geopolitical channels include research security, strategic dependencies, supply-chain security/resilience, investment screening, technology/export controls, critical raw materials, techno-nationalism, sanctions/de-risking, strategic autonomy, science diplomacy and great-power technology competition.

Safeguards remain against generic geopolitics, generic innovation/business, pure technical papers, calls, project pages, events, press releases and other non-analytical material.

## Discovery schedule

- **First V15 run:** four-calendar-month A/B backfill under the balanced criteria.
- **Later runs:** every 12 hours with a 14-day A/B overlap.
- **Corpus:** A, B and C remain cumulative and deduplicated.
- **Zero configuration:** no keys/secrets need to be created in GitHub.

## Full-repository upload

This ZIP includes the current cumulative `radar.json` snapshot together with the complete V15 code, site, tests and active GitHub Actions workflow. Extract the ZIP and replace the repository contents with all files and folders, including `.github`. Commit to `main`; the push starts the V15 four-month backfill. Later scans run every 12 hours.

## Local tests

```bash
python -m unittest discover -s tests -v
```
