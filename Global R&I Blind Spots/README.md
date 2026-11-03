# Global R&I — Start here

**This is a manual, rotating, global non-EU research and innovation scanner.** It does not replace or update the main Radar.

## After a discovery scan

- **[LATEST.md](LATEST.md)** — scan summary and selected new source leads. These are **candidates, not verified findings**.
- **[latest.csv](latest.csv)** — spreadsheet-friendly current candidate list.
- **[archive.json](archive.json)** — persistent candidate history, including previously seen material.
- **[scan_state.json](scan_state.json)** — what countries were covered this run and which countries rotate next.
- Discovery candidates are grouped as **potential developments**, **trend evidence**, **structural context**, or **individual research outputs**. This is automated triage, not a verification verdict.
- Institutional programme pages remain useful as structural leads. They do **not** prove a trend on their own; `LATEST.md` supplies a specific follow-up question and, where available, related unverified leads.
- A source may be connected to more than one country or theme, but researcher affiliation alone is not proof a paper concerns that country's R&I system.

## After a manual LLM Deep Scan

1. GitHub Actions → **Global R&I Deep Scan — LLM Package / Import** → `operation = prepare`.
2. Open the completed run → **Artifacts** → download **global-ri-llm-review-package**.
3. Give the package to a browsing-capable LLM. Ask for a JSON results file named `global_deep_scan_results_<package-id>.json`, following `INSTRUCTIONS.md`. The package ID appears in `manifest.json`.
4. Upload the returned JSON to [`deep_scan/inbox/`](deep_scan/inbox/) on branch `main`. **Do not rename, delete or replace earlier files.** Both the historical `global_deep_scan_results.json` and Windows duplicate filenames such as `global_deep_scan_results (1).json` are supported. The importer checks the actual package ID in the file.
5. Uploading triggers validation and import. Accepted KEEP findings accumulate in **[deep_scan/VERIFIED_FINDINGS.md](deep_scan/VERIFIED_FINDINGS.md)**. After validation, imported inbox JSON files are moved automatically to `deep_scan/processed_inbox/` as a historical record. If an older file cannot be confirmed as previously imported, it remains in the inbox for safety, but it does not block a correctly matched new package.

**Already uploaded `global_deep_scan_results (1).json` while the previous file is still there?** Install the inbox update, go to Actions → **Global R&I Deep Scan — LLM Package / Import** → Run workflow → `operation=import`. This processes the files already on GitHub; no re-upload and no GitHub pencil icon are needed.

- **[deep_scan/QUEUE.md](deep_scan/QUEUE.md)** — package awaiting LLM review.
- **[deep_scan/REVIEW_ARCHIVE.md](deep_scan/REVIEW_ARCHIVE.md)** — retained KEEP, REVIEW and DROP decisions with reasons.
- **[deep_scan/verified_findings.json](deep_scan/verified_findings.json)** — machine-readable history of all reviewed decisions.

Files with names beginning `AUTO_FINDINGS` or `auto_archive` are historical artifacts from the earlier abandoned automatic-AI prototype. **They are not the outputs of the current two-workflow scanner.**

## Geography, duration and source quality

The current configuration rotates **28 countries across 10 world regions**. Each manual run covers 12 countries, all six research/innovation themes and selected global sources. Typical intended discovery time is **roughly 20–24 minutes**, subject to network access and early failure; 20 minutes alone does not establish source quality.

Discovery uses OpenAlex (with the repository's `OPENALEX_API_KEY`), journals from the main Radar's trusted list, selected independent editorial RSS and official/institutional source portals. Official announcements are labelled as uncorroborated claims; affiliation-only academic papers are labelled separately. The scanner is *not* a full web crawler or a substitute for the LLM source reading. Strict source review happens at the package stage.

The global scan is manual-only. The review **import** reacts to an explicit upload of a `global_deep_scan_results*.json` file in the inbox; that is not an automated discovery run.
