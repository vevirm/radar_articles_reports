# Global R&I — Start here

**This is a manual, rotating, global non-EU research and innovation scanner.** It does not replace or update the main Radar.

## After a discovery scan

- **[LATEST.md](LATEST.md)** — scan summary and selected new source leads. These are **candidates, not verified findings**.
- **[latest.csv](latest.csv)** — spreadsheet-friendly current candidate list.
- **[archive.json](archive.json)** — persistent candidate history, including previously seen material.
- **[scan_state.json](scan_state.json)** — what countries were covered this run and which countries rotate next.

## After a manual LLM Deep Scan

1. GitHub Actions → **Global R&I Deep Scan — LLM Package / Import** → `operation = prepare`.
2. Open the completed run → **Artifacts** → download **global-ri-llm-review-package**.
3. Supply the package to a browsing-capable LLM, requesting a complete `global_deep_scan_results.json` that follows `INSTRUCTIONS.md`.
4. Upload the returned JSON to [`deep_scan/inbox/`](deep_scan/inbox/) with exact filename `global_deep_scan_results.json` on branch `main`.
5. Uploading triggers validation and import. Check **[deep_scan/VERIFIED_FINDINGS.md](deep_scan/VERIFIED_FINDINGS.md)** for accepted KEEP findings.

- **[deep_scan/QUEUE.md](deep_scan/QUEUE.md)** — package awaiting LLM review.
- **[deep_scan/REVIEW_ARCHIVE.md](deep_scan/REVIEW_ARCHIVE.md)** — retained KEEP, REVIEW and DROP decisions with reasons.
- **[deep_scan/verified_findings.json](deep_scan/verified_findings.json)** — machine-readable history of all reviewed decisions.

Files with names beginning `AUTO_FINDINGS` or `auto_archive` are historical artifacts from the earlier abandoned automatic-AI prototype. **They are not the outputs of the current two-workflow scanner.**

## Geography, duration and source quality

The current configuration rotates **28 countries across 10 world regions**. Each manual run covers 12 countries, all six research/innovation themes and selected global sources. Typical intended discovery time is **roughly 20–24 minutes**, subject to network access and early failure; 20 minutes alone does not establish source quality.

Discovery uses OpenAlex (with the repository's `OPENALEX_API_KEY`), journals from the main Radar's trusted list, selected independent editorial RSS and official/institutional source portals. Official announcements are labelled as uncorroborated claims; affiliation-only academic papers are labelled separately. The scanner is *not* a full web crawler or a substitute for the LLM source reading. Strict source review happens at the package stage.

The global scan is manual-only. The review **import** reacts to an explicit upload to the exact inbox filename; that is not an automated discovery run.
