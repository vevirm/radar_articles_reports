# R&I × Geopolitics Radar — V17 evidence-quality + scholarly expansion

V17 keeps the working cumulative scanner and fixes three content problems together:

1. the Insights page was dominated by weak signals;
2. Strand A was too dependent on EU/institutional material and was not finding enough research publications;
3. Strand B admitted methodology papers whose subject matter was not actually EU + R&I + geopolitics.

## V17 scope

### Strand A — substantive evidence
A publication/report must substantively connect:

- **EU / Europe / an EU Member State**, and
- **R&I or a closely related strategic technology/science capability**, and
- **geopolitics, geoeconomics, economic security, strategic competition, dependencies, controls, de-risking, sovereignty or similar context**.

R&I-adjacent scope includes research systems, innovation policy, universities, science diplomacy, research security, critical technologies, semiconductors, AI/compute, quantum, biotech, nuclear/energy technology, digital infrastructure, technology ecosystems and related capability questions — but only when the geopolitical/economic-security connection is substantive.

Generic EU politics, elections, rule-of-law material, enlargement analysis, generic sustainability, general sector news and incidental technology mentions do not qualify.

### Strand B — methodology on the substance
Strand B is no longer a general foresight-methods library. A methods paper/report must contain substantive foresight methodology **and** the same EU + R&I + geopolitics/economic-security triangle.

Therefore papers such as **“PATHWAYS TO ZERO WASTE: PROSPECTIVE SCIENCE TEACHERS’ SOLUTIONS THROUGH EVERYDAY LIFE SCENARIOS”** are rejected. So are generic climate-scenario, household-futures or urban-participation methodology papers unless their actual subject is European R&I/strategic technology in geopolitical context.

## More research publications

V17 gives scholarly literature its own protected discovery path:

- 115 Strand-A scholarly queries;
- 30 substance-specific Strand-B queries;
- OpenAlex public anonymous discovery;
- Crossref public anonymous discovery;
- a dedicated Crossref sweep across 36 priority journals × 6 focused EU/R&I/geopolitics queries before the broad query universe;
- broad peer-reviewed-journal eligibility remains, but the admission gate is stricter and based on title/abstract substance.

The direct institutional crawler still monitors 57 major EU, European and international policy/research players. Institutional reports complement scholarly research instead of replacing it.

## Runtime

This repository is deliberately **30-minute safe**. The GitHub Actions job timeout is **30 minutes**, while the scanner has a **20-minute internal scan budget** (1,200 seconds). Network work winds down before that budget expires, leaving time to write `radar.json` and for GitHub Actions to commit and push it. The scanner no longer depends on raising GitHub's timeout above 30 minutes.

The first V17.1 run forces a new **four-month A/B backfill** under the scholarly/source profile. Institutional crawling is bounded to a smaller high-priority page set so the run can complete and save results inside the 30-minute job. Later scans continue every **12 hours** with the overlap logic already used by the radar.

Weak-signal scanning remains protected at the start of the run and remains cumulative.

## One-time quality migration

V17 revalidates the accumulated A/B corpus once under the corrected substance gate. Valid earlier material stays cumulative, but old false positives are removed. Strand C history is not pruned by this migration.

## Insights page

`/briefing/` now defaults to **All intelligence**, not Weak signals. It shows:

1. **Research publications**;
2. **EU & institutional reports**;
3. **Weak signals**.

Each category has its own filter, while search and “New only” work across the full evidence base.

## Complete repository upload

This package is the **whole repository**, including `radar.json` and the active `.github/workflows/radar-scan.yml`. It intentionally contains only the active workflow copy, so there is no backup YAML that can be uploaded by mistake.

Upload/extract everything to the repository root. No separate file preservation step is required. The bundled `radar.json` is marked as a repository seed; on the first scan, Git history recovery merges back a larger existing cumulative corpus if one exists before V17 revalidates and rescans it.

No API keys, custom secrets or email configuration are required.

## Tests

Run:

```bash
python -m unittest discover -s tests -v
```
