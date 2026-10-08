# Manual Strand A LLM Research Discovery — GitHub browser setup

**Purpose:** A second, manually initiated research discovery route, complementary to the automatic scanner. **No LLM API key, automated LLM invocation, subscription, or background AI agent is required or used.** You initiate both the GitHub research-packaging Action and the LLM research session. The GitHub importer performs deterministic HTTPS source verification; that is not an LLM call.

## Installation (GitHub website only)

Use the separate `LLM_DISCOVERY_UPLOAD.zip` installation archive. Unzip it **on your computer** and use **Add file → Upload files** in GitHub at the exact indicated folder; make or navigate to each folder in the repository first. GitHub does not unzip uploaded archives by itself. Files inside the installation ZIP are relative to the repository root; **do not upload the outer folder itself**. Commit the uploads to the `main` branch.

All installation files are **new**; none of the protected production scanner, historic corpus, Deep Scan scripts, Main Radar data, existing JSON sidecars, or installed Actions is replaced.

| Exact repository path | Upload type |
| --- | --- |
| `.github/workflows/strand-a-llm-research-prepare.yml` | New Action |
| `.github/workflows/strand-a-llm-research-import.yml` | New Action |
| `scripts/llm_discovery_common.py` | New common evidence/identity helpers |
| `scripts/prepare_llm_discovery.py` | New research-package generator |
| `scripts/import_llm_discovery.py` | New evidence-based importer |
| `tests/test_llm_discovery.py` | New offline integration regression suite |
| `LLM_DISCOVERY_SETUP.md` | New manual/documentation |
| `llm_discovery_inbox/README.md` | New upload inbox and instructions |
| `llm_discovery_reports/README.md` | New audit/report directory instructions |

The included visible `README.md` placeholders create both new folders and explain their roles. Upload those README files as ordinary files; no hidden-file workaround is required.

## Step 1 — You prepare a manual research package

Navigate to **Actions → Strand A — Prepare LLM Research Discovery → Run workflow** (branch `main`). The optional `task_count` defaults to 18; permitted 5–20. When it finishes, open that Actions run's **Artifacts** section and download **strand-a-llm-research-package**. Extract the artifact to obtain `llm-discovery-research-package.zip` (the nested real research ZIP).

That ZIP contains `START_HERE.md`, `tasks.json` with bounded priorities, `coverage_gaps.json` with actual under-coverage counts, `candidate_leads.json` with unresolved scanner metadata (unverified!), all known Main Radar identities in `existing_radar_records.json`, the official Deep Scan scanner-parity scope criteria in `admission_policy.txt`, and `results_TEMPLATE.json` with the exact return schema. The specific journal and institutional tasks are generated from repository source configuration and existing Radar counts; low counts are coverage prompts, *not* proven scanner failures.

## Step 2 — You work with a browsing-capable LLM manually

Upload the complete research ZIP into a new browsing-capable LLM conversation. Ask it to **follow START_HERE.md, investigate the 18 ranked scientific/institutional tasks using real primary publications, and return only a downloadable UTF-8 `llm_research_results.json`**. Do not supply API keys or configure background tasks. Keep the task list manageable; if fewer publications actually qualify, returning few/zero findings is correct.

**Required fields per finding:** exact title, authors/organisation, journal or institution, DOI when available, official HTTPS publication URL, original publication date `YYYY-MM-DD` (not a website update), `journal_article` or `institutional_report`, substantive research abstract/evidence, principal findings, EU/European R&I relevance, **at least two distinct verbatim quotes** (10+ words each) from a first-party abstract/body, source-reference URLs with their claimed support, verification limitations, and a research task ID. For official PDFs, provide `metadata_url` pointing to an official landing page displaying the original publication date. The JSON must include the package ID. **All unsupported claims must be explicitly marked uncertain in the returned evidence.** See the template for exact keys.

## Step 3 — You upload the LLM's structured result in GitHub

Go to `llm_discovery_inbox/` in the GitHub repository, then **Add file → Upload files → choose `llm_research_results.json` → Commit changes** to `main`. The push automatically triggers **Actions → Strand A — Import LLM Research Discoveries**. Alternatively, run this import Action manually; both are deterministic, without any AI calls. For successive research packages, use unique uploaded filenames such as `llm_results_2026_10_08.json` to avoid overwriting prior originals. The file must be `.json` and no larger than 1 MB, up to 24 entries.

The importer verifies every candidate **directly** from primary publication evidence:

- Scholarly articles: Crossref-deposited DOI/title/original date/journal-quality metadata, primary depositor abstract and/or independently DOI-matched OpenAlex indexed original abstract, plus (when available) publisher publication page. A DOI without substantive independently verifiable publication text (depositor/publisher or corroborated indexed abstract) will **not** pass. The DOI URL is a valid official publication locator.
- Institutional reports: trusted original official institution site, matching report title, precise original `datePublished`/citation date and actual report text or abstract (for PDFs, an official dated companion metadata URL may be required). Generic portal/press/crawl dates are not sufficient.
- Every admitted finding requires **two distinct provided passages actually found in the independently retrieved publication evidence**, substantive readable primary research material, and success at the repository's **existing** `quality_from_crossref` / institution-source integrity checks, `final_ab_candidate_worthiness`, `gate_scope(...).a_pass` and configured 4-month or quality-limited 6-month new-discovery window. The LLM's self-written findings, abstract and EU relevance statement are **not used** as source proof or as gate input.
- It checks DOI, normalized title and direct URL identity against Main Radar A/B/C, archives, the private Deep-A pool, and the historical evidence archive. Rejected/duplicate/inaccessible submissions are reported but **never appended**. Unknown scanner miss causes are marked “not determinable”; a matching deferred-metadata item is explicitly identified.

The import Action writes a report for each unique submitted JSON content under `llm_discovery_reports/<sha256-prefix>.json`, recording admission or rejection and the reason. It is replay-safe: uploading the same byte-identical result again does not duplicate items. New qualified evidence is appended **directly to `radar.json` → `strand_a`**, with `discovery_method: "LLM-assisted discovery — Pending Deep Scan"`, `deep_scan_status: "pending"`, and sourced `llm_discovery` verification/provenance. It is **not** handed back to Crossref/OpenAlex discovery search or an additional private candidates database. The Action rebuilds `radar_active.json` and downstream reader-facing products via the existing project scripts; no historical corpus or authoritative Deep Scan state is reclassified.

**Limitations / conservative tradeoff:** Some publisher sites, image-based PDFs, incomplete Crossref abstracts, date-only-year records or official reports without strong publication metadata will remain rejected. The route is a **direct evidence importer**, not a blanket bypass of publication verification. Its independent checks use ordinary HTTPS requests to original sources (they are not scanner discovery searches). Review detailed failed-source reasons and improve the LLM's source references or locate a verified official copy; never invent missing evidence.

## Step 4 — Normal Deep Scan retains authority

After the import has committed, use the *existing* **Deep Scan V2 — Prepare Parallel Worker Packages** GitHub Action. The unchanged `scripts/deep_read_works.py` considers each newly appended Main Radar record without an authoritative reader entry as pending. The existing work-state coordination selects Main Radar Strand A ahead of later lanes, subject to previous reservations and bounded retries. Download `deep-scan-worker-A`/`deep-scan-worker-B` from the existing Action; process them with browsing-capable LLMs manually; upload the exact existing Deep Scan result format into `deep_scan_inbox/`. Deep Scan's standard import Action determines **KEEP / REVIEW / DROP / DROP_UNVERIFIABLE**. No Deep Scan instruction, selection, retry limit, admission sidecar, authoritative decision rule, or verification attempt limit has been modified by this installation.

## Important operational notes

- The initial installation does **not** rewrite `radar.json`, `radar_active.json`, `historical/historical.json`, `admission_state.json`, `reader_text.json` or any research database.
- Imports run with the same GitHub Actions concurrency lock as the existing scanner and Deep Scan to prevent simultaneous corpus writes. Upload is manual; processing happens automatically after that manual commit.
- Rejections are non-destructive; the original LLM response remains in the inbox as submitted and the report explains the failed evidence requirement. Correct a returned results file locally by asking the LLM for a **new** research JSON file and upload with a distinct filename.
- Source/coverage failures are audited in the per-result report and each admitted row's `llm_discovery.miss_reason`, helping later improvement of automatic scanner source routing without changing scan schedules.
- If GitHub Actions are disabled or `GITHUB_TOKEN` lacks **Read and write permissions**, repository settings must permit actions to commit. The importer Action declares `contents: write` explicitly, like your current Deep Scan Action.
- Before processing any real report, inspect the separate source proofs; errors fail closed. No LLM-generated content becomes a final Deep Scan decision.
