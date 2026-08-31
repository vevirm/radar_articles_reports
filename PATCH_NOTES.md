# v17.18.1 — workflow unjam + safety-preserving decoupling

- Fixed the immediate 12–24 second failures seen on GitHub Actions. The live repository had new scanner tests that asserted a four-hour YAML schedule, while the live workflow YAML was still the old daily/hourly version. That made tests stop both scanners before evidence discovery began.
- Scanner regression tests now test scanner/evidence behavior only. They no longer fail because a workflow schedule file is stale or partially uploaded.
- Added `scripts/check_workflow_contract.py` as a separate deployment sanity checker. Both workflows run it with `continue-on-error: true`: a cadence/config mismatch is visible as a warning but cannot jam evidence scanning.
- Main workflow remains a true four-hour rotation at 00:17/04:17/08:17/12:17/16:17/20:17 UTC. Historical remains a true four-hour rotation, offset at 02:41/06:41/10:41/14:41/18:41/22:41 UTC.
- Historical minimum runtime remains 0: it searches toward the ~8 finding target instead of padding to ten minutes.
- Persistence safety is retained: Main can stage/commit only `radar.json`; Historical can stage/commit only `historical/historical.json`.
- Historical safety is strengthened with before/after file-size and corpus-count checks plus preservation of curated manual evidence.
- Reader pages remain live views of `radar.json`; Matrix, Read at least this, Risks & opportunities, briefing, Sources and Stuff continue ranking admitted findings with the shared source-merit/evidence-quality model.
- No relevance, A/B/C, document-integrity, date-integrity, journal-quality or source-rotation gates were loosened.
