# GLOBAL R&I SCANNER — Corrected, 20–24-minute rotating manual discovery + LLM Deep Scan

This file supersedes earlier instructions for the abandoned automatic AI/GitHub Copilot scanner. Do not run any old automatic AI Deep Scan workflow; the existing workflow filename `global-ri-deep-scan-auto.yml` now identifies the **LLM Package / Import** action.

## What to upload (merge only these paths into existing repository main)

- `.github/workflows/global-ri-blind-spots.yml` — **replace existing** manual scanner workflow
- `.github/workflows/global-ri-deep-scan-auto.yml` — **replace existing**; now creates packages and imports JSON, no GitHub AI inference
- `scripts/global_blind_spots.py` — **replace existing** scanner script
- `scripts/global_blind_spots_deep_scan.py` — **replace existing** package/import script
- `global_blind_spots_config.json` — **replace existing** with worldwide configuration
- `global_deep_scan_source_leads.json` — **replace existing** curated source leads
- `tests/test_global_blind_spots.py` — **replace existing**
- `tests/test_global_blind_spots_deep_scan.py` — **replace existing**
- `Global R&I Blind Spots/README.md` — **add new** (easy links to results)

**Do not upload** an old whole-repository ZIP, an old `radar_active.json`, historical `latest.json` results, or any automatically generated `scan_state.json` from this patch. Keep all existing main-Radar data and ongoing scan results.

## Workflow A — Discovery: one click

GitHub → Actions → **Global R&I Blind Spots — Manual Scan** → Run workflow (`main`). This runs OpenAlex and curated sources, paced across selected world countries and 6 topic families. Budget: approximately **20–24 minutes** of real searches, not a quick 20-second sample. It uses `OPENALEX_API_KEY` already configured for the Radar. It makes at most 156 OpenAlex searches. Those requests consume your OpenAlex API allowance, which is shared with your other scanners. Check your OpenAlex account usage and billing settings; the scanner itself does not initiate any paid AI service.

Results are committed to `Global R&I Blind Spots/` (never into `radar.json` or `radar_active.json`).

- Easy to read: `Global R&I Blind Spots/LATEST.md` (discovery leads, **not** findings)
- All past leads: `Global R&I Blind Spots/archive.json`
- Rotation state: `Global R&I Blind Spots/scan_state.json`
- Folder navigation: `Global R&I Blind Spots/README.md`

## Workflow B — Deep Scan: GitHub package → browsing LLM → inbox

1. **Actions → Global R&I Deep Scan — LLM Package / Import**.
2. **Run workflow**, `operation=prepare`, `batch_size=12` (12 assigned source documents; adjust 1–24).
3. In the completed action run, scroll to **Artifacts** and download `global-ri-llm-review-package`.
4. Give the ZIP to a browsing-capable LLM and ask it to follow `INSTRUCTIONS.md`. It should return **`global_deep_scan_results_<package-id>.json`**, matching the package ID in `manifest.json`. All assigned IDs should get KEEP/REVIEW/DROP; it must not fabricate information to create KEEP findings.
5. Upload the resulting JSON to **`Global R&I Blind Spots/deep_scan/inbox/`** on `main`. Both the historical fixed filename and Windows `(1)` versions are accepted, so **do not replace, rename or delete old inbox files**. The importer checks the package ID inside each file and automatically moves successfully imported inputs to `deep_scan/processed_inbox/`.
6. Find results in **`Global R&I Blind Spots/deep_scan/VERIFIED_FINDINGS.md`**. A separate **`REVIEW_ARCHIVE.md`** stores all review decisions, including drops/uncertain ones. Structured history: `verified_findings.json`.

The scanner never automatically sends the package to a paid LLM. Its input is the current Radar plus curated source discovery. Previously covered Radar items remain eligible, and the Deep Scan explicitly identifies whether an item confirms, extends or changes an existing Radar finding.

## Source protection

- Trusted-journal allowlist comes from main `radar_config.json` and is applied to OpenAlex papers.
- Editorial and official feeds/hubs are explicitly allowlisted by hostname.
- Government and institutional claims are clearly separated from independent corroboration.
- Academic country attribution based only on an author's affiliation is downgraded and never described as national research policy evidence.
- Candidates must be source-reviewed by the LLM to appear in `VERIFIED_FINDINGS.md`. Imports check for substantive evidence fields and independent-domain citations, but these structural checks cannot themselves prove truth.

The **discovery** and **package preparation** workflows have no cron schedules; only a result JSON upload triggers automatic **import**. You can also run `operation=import` manually to process files already in the inbox after a code update.

## Discovery-quality update: programme pages and trends

The discovery report now groups leads into dated developments, multi-year evidence leads, institutional/structural context, and research outputs. Institutional programme pages are **retained**, not blanket rejected. Each lead gets an investigation question and, where available, related sources to check. No links are counted as independently corroborating evidence until Deep Scan has opened them.

The scanner caps undated structural leads and country-affiliation-only scholarly leads in each country/theme cell so they cannot dominate the report. A paper explicitly about a different country is excluded from affiliation-only country matching. Deep Scan packages include the questions and cross-source leads and favour current discoveries without excluding good existing Radar records.

**What 144 means:** 12 countries selected per run × six R&I themes × two OpenAlex query approaches = 144 requests, each allowing up to 25 returned records. Pacing produces much of the ~20-minute runtime; this is source *discovery*, not full-document reading. The separate LLM package is the deep-reading stage.
