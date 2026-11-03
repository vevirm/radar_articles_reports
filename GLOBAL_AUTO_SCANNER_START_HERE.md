# Global R&I: discovery scanner + LLM Deep Scan packages

This is a **correction patch** for the Global scanner you already uploaded to GitHub.
You do **not** need `OPENAI_API_KEY`, GitHub Copilot, or paid GitHub inference.
You do **not** need to upload research material to feed the discovery scanner.

## Install these five files

Open your existing GitHub Radar repository on `main`, and upload each file at its matching destination. **Replace the existing file with the same name** rather than adding a second copy.

| File in this patch | Destination in your current GitHub repository |
| --- | --- |
| `.github/workflows/global-ri-deep-scan-auto.yml` | `.github/workflows/global-ri-deep-scan-auto.yml` (replace) |
| `scripts/global_blind_spots_deep_scan.py` | `scripts/global_blind_spots_deep_scan.py` (replace) |
| `tests/test_global_blind_spots_deep_scan.py` | `tests/test_global_blind_spots_deep_scan.py` (replace) |
| `GLOBAL_AUTO_SCANNER_START_HERE.md` | `GLOBAL_AUTO_SCANNER_START_HERE.md` (replace outdated instructions) |
| `Global R&I Blind Spots/deep_scan/inbox/README.txt` | `Global R&I Blind Spots/deep_scan/inbox/README.txt` (new folder marker) |

The existing **Global R&I Blind Spots — Manual Scan** action, your discovery script,
configuration, main Radar, and all their normal workflows stay unchanged.
The old automatic-AI workflow is **replaced in place**, so no obsolete action
will attempt to use Copilot or OpenAI tokens.

## Your actual workflow

1. In GitHub Actions run **Global R&I Blind Spots — Manual Scan**. It reads
   `radar_active.json`, uses `OPENALEX_API_KEY` if present, and retrieves trusted
   international discovery leads. Review only `Global R&I Blind Spots/LATEST.md`
   if you want to see what it found. Research input uploads are not needed.
2. In GitHub Actions run **Global R&I Deep Scan — LLM Package / Import** with
   `operation=prepare`, `batch_size=12` (or 6 for a first test).
3. Open that workflow run > **Artifacts** > download
   `global-ri-llm-review-package`. GitHub downloads an artifact ZIP containing
   `global_ri_llm_package.zip` (the inner ZIP is the review package).
4. **Upload the inner ZIP to a browsing-capable LLM** and ask:

   > Read `INSTRUCTIONS.md` in the attached package. Verify the real source
   > material for each item, seek independent corroboration, compare against
   > existing Radar coverage, and return the complete
   > `global_deep_scan_results.json` matching the supplied template.
   > Where evidence is insufficient use REVIEW or DROP, not KEEP.

5. Download the returned `global_deep_scan_results.json`. In the repository,
   upload it to exactly:
   `Global R&I Blind Spots/deep_scan/inbox/global_deep_scan_results.json`.
   The **same Deep Scan workflow** automatically runs **import only** because
   that one exact file changed. It does not scan on a push.
   If automatic import is disabled, manually run **Global R&I Deep Scan — LLM Package / Import** with `operation=import`.
6. Read `Global R&I Blind Spots/deep_scan/VERIFIED_FINDINGS.md` and
   `verified_findings.csv`. The report includes only accepted KEEP findings;
   reviewed but unresolved records are not presented as established facts.
7. To get the next batch, run `operation=prepare` again. Unfinished packages
   are reused, so an accidental duplicate click does not invalidate an LLM
   review that is already underway.

## What the numbers mean

`batch_size=12` means **12 candidate source records per LLM review package**.
It is **not** a discovery limit; OpenAlex can return more candidates. This
manual review version does **not** use the old automatic settings of 24 documents
and 12 AI evidence pairs.

## Sources and reliability

Discovery uses curated journals through OpenAlex, the main Radar findings,
selected institutional sites and feeds, and international source leads
covering the US, China and Russia. It produces *candidate records*, not
verified conclusions. The review package contains source URLs, summaries,
current Radar links, exact IDs, instructions and a JSON result template;
**it does not contain full-text PDFs of the linked works**. The browsing-capable
reviewer must open the primary content and an independent corroboration
source before using KEEP.

A KEEP requires substantial evidence fields, a dated primary HTTPS source,
a distinct corroborating source, documented limitations and a main Radar
comparison. Validation checks format and source separation; it cannot by
itself prove that a remote webpage or an LLM's assessment is factually true.

## Nothing to clean up

You can leave the old empty `AUTO_FINDINGS.md`, `AUTO_FINDINGS.json`,
`audit.json` and `auto_archive.json` files in the Global folder; they are not
used by this manual workflow. Do not upload earlier installation ZIPs or
replace the full repository while other Radar scans are running.
