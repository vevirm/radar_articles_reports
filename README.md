# R&I Geopolitics Radar — V17.5.11 Scanner + Frontier Repair

This repository scans for **EU research & innovation in geopolitical/economic-security context**, classifies evidence into the radar and Sovereignty Frontier, and persists source/query rotation across runs.

## What this build enforces

- **Strand A is topical evidence.** It requires meaningful EU/European scope, substantive R&I/capability content, and a real geopolitical/economic-security connection. Generic education, administration, politics or technology papers are not admitted from loose word overlap.
- **Strand B is methodology-only.** B is for methodology-first foresight/scanning/anticipation work that is genuinely transferable to European R&I: e.g. Delphi design, horizon-scanning methods, weak-signal methods, scenario-construction methodology, backcasting, morphological analysis, foresight evaluation and related methodological contributions. A topical paper does not enter B merely because it *uses* scenarios, a framework or an assessment method.
- **Knowledge & people is classified semantically.** Research collaboration/security, scientific talent, researcher mobility, attraction/retention and brain drain can reach the correct A/B/C/D cell; individual EU Member States and their adjectival forms remain recognised as European scope.
- **Scanning rotates persistently.** OpenAlex, Crossref broad, priority journals, institutions, per-cell gap queries/sources, result-depth pages and the dedicated B-method lane each keep independent cursors in `radar.json`.
- **Sparse cells get extra discovery, not a reset.** Frontier deficits allocate extra scan budget while the normal rotations continue from their saved positions.
- **Quality migration is fail-closed.** When the quality profile changes, inherited A/B evidence is re-audited under the repaired gates with best-effort evidence refresh; scan cursors are retained.
- **No secrets are required.** OpenAlex runs keyless and the GitHub Actions workflow does not require repository secrets.

Upload the repository to GitHub and run the existing **Radar Scan** workflow. The included state preserves the supplied live scan cursors; the first V17.5.11 run performs the quality-profile migration and continues rotating from those positions.
