# Deep Scan — simple no-API file rotation (one Deep Scan per work)

Deep Scan is the slower reader for works that the normal Radar scanner has already found.

It uses **no Anthropic/OpenAI API key and no pay-as-you-go model account inside GitHub**. GitHub only prepares and validates files. You give the prepared ZIP to an LLM subscription you already use, receive one result file back, and upload that result to GitHub.

The normal scanner keeps running exactly as before. New works appear immediately with the normal automatic wording. Deep Scan gradually upgrades existing works with a better interpretation in `reader_text.json`. **A successfully deep-scanned work is considered done and is not automatically sent back for another Deep Scan.** It never edits `radar.json`.

## One-time installation

If you received the Deep Scan patch ZIP:

1. Unzip it on your computer.
2. Open the main page of your GitHub repository.
3. Choose **Add file → Upload files**.
4. Drag the contents of the unzipped patch into the upload area. Keep the included folder structure (`.github/workflows`, `scripts`, `deep_scan_inbox`, etc.).
5. Commit the upload to `main`.

There are **no AI secrets to add**.

## The normal rotation

### 1. Ask GitHub to prepare everything that needs deeper reading

1. Open the repository's **Actions** tab.
2. Choose **Deep Scan — Prepare Package**.
3. Choose **Run workflow**.
4. Run it. There are no model/budget settings.
5. When it finishes, open the workflow run and download the **deep-scan-package** artifact.
6. Unzip that GitHub artifact once. Inside it is `deep_scan_package.zip`.

The package contains **all current works that need a Deep Scan**, not an arbitrary 20-item limit. Internally it is split into small numbered batches so an LLM can work through a large backlog safely.

### 2. Give that ZIP to your LLM

Upload `deep_scan_package.zip` to the LLM subscription you want to use and say:

> Process this Deep Scan package according to INSTRUCTIONS.md and return the completed result file.

That is enough. The ZIP contains `START_HERE.txt`, detailed `INSTRUCTIONS.md`, a manifest, a result template and the numbered work batches.

The LLM is told to read the work/source material, check the automatic scanner's interpretation, understand what the work actually says, and then produce clear Radar wording. It is also told not to invent unsupported conclusions.

For a very large backlog, partial completion is valid. The LLM should return only works it actually processed carefully. Unfinished works automatically remain in the next package.

### 3. Upload the returned file to GitHub

The LLM should return `deep_scan_results.json` (or a ZIP containing that file).

1. Open your GitHub repository.
2. Open the folder **`deep_scan_inbox`**.
3. Choose **Add file → Upload files**.
4. Upload the returned JSON/ZIP.
5. Commit the upload to `main`.

That upload automatically starts **Deep Scan — Import Returned Results**.

GitHub validates every returned interpretation and then updates `reader_text.json`. Successfully imported works disappear from the next Deep Scan package. The uploaded inbox file is removed automatically after a valid import, so the folder does not fill up.

## What happens to new works?

Nothing is blocked. The automatic scanner continues to admit new material and the site displays its normal lightweight wording immediately.

The next time you run **Deep Scan — Prepare Package**, GitHub includes works that have **not yet received a valid Deep Scan interpretation**. Once a work has been successfully deep-scanned, it stays complete and is not automatically read again just because time passes or the fast scanner later changes wording/metadata.

This means the initial historical backlog can be large, but after it is cleared the package naturally contains mostly the genuinely new works since your last Deep Scan.

A source hash is still carried in the package for one narrow safety reason: if a record changes **between package export and returned-file import**, GitHub rejects that returned result rather than attaching an interpretation to mismatched input. This does not create a future re-reading cycle.

## What is inside the package?

For each work, the package includes the useful material the automatic scanner already has, such as title, authors, source, date, type/status, automatic summary/finding/relevance and evidence tags.

GitHub also makes a best-effort attempt to read the linked source before creating the package. When accessible, it includes an abstract/source page or a bounded PDF excerpt. For PDFs it samples both early pages and final pages so the LLM has a better chance of seeing the abstract/introduction and discussion/conclusion. If a publisher blocks retrieval, the work is still included using the stored scanner material.

## Safety

The result file cannot overwrite scanner evidence. The importer writes only the optional reader sidecar and removes the consumed inbox file.

Each work carries a `record_key` and `source_hash`. The LLM is instructed to copy them unchanged. Before import, GitHub checks that the work still exists and that the record still matches the package that was exported. If it changed during that export→import window, that returned interpretation is skipped. A successfully imported Deep Scan result does **not** later expire or get automatically queued again.

The site continues to fall back to the automatic wording whenever no valid Deep Scan interpretation exists.

## Cost behavior

No LLM API is called by these workflows. There is no `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, Copilot token, or other model billing credential involved.

GitHub Actions itself performs ordinary file preparation/source retrieval and import validation. The actual reading is done only when **you manually give the package to an LLM subscription**.
