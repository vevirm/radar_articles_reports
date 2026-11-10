# Relevance Focus global-regions surgical fix

This package changes only the automatic Relevance Focus scanner and its own independent Deep Scan handoff. It contains no replacement repository, no radar database, and no generated Excel workbook. The existing `Relevance Stuff/relevance_stuff.xlsx` is rebuilt automatically by GitHub Actions on the next run.

## Apply in GitHub

Extract this ZIP. Copy the relative paths into the ROOT of your existing `radar_articles_reports-main` repository, preserving folder paths and overwriting the corresponding existing source files. The two new workflow / Deep Scan files must be added at their indicated paths. Commit to `main`. Do NOT upload the ZIP itself into the repo; GitHub does not unpack it.

If using Git locally instead, use the companion `.patch`: `git apply --check relevance_focus_surgical_changes.patch` then `git apply relevance_focus_surgical_changes.patch`, commit and push. It was produced against the supplied original repository version.

## Review package round trip

1. Actions → `Relevance Focus — global aboutness + futures` → select latest successful scheduled run (or Run workflow with mode=scan).
2. Download the artifact `relevance-focus-global-deep-scan-review`. It contains `MANIFEST.json`, `INSTRUCTIONS.md`, `RESULTS_TEMPLATE.json` (up to 12 items per package).
3. Give these files to a browsing-capable LLM/reviewer and ask it to actually verify each original source. Do not treat indexed metadata or a plausible future as a verified outcome. Require JSON in the template schema, with the exact `package_id` and candidate IDs. Decision choices: `keep` / `review` / `drop`.
4. Save the finished JSON as e.g. `batch_review.json` in the existing repository at `Relevance Stuff/deep_scan/inbox/batch_review.json`. Commit/push to `main`.
5. The workflow `Relevance Focus — global Deep Scan reviewed import` runs automatically on the inbox JSON push. It checks structured evidence and review decisions, archives the input, and rebuilds `Relevance Stuff/relevance_stuff.xlsx`. The `Global verified futures` sheet contains KEEP decisions only. A validator cannot guarantee the reviewer's factual work; verification must really have been performed.

Scanner output: `Relevance Stuff/regional_discoveries.json` (candidate archive); `Relevance Stuff/relevance_stuff.xlsx` (workbook); `Relevance Stuff/deep_scan/pending_manifest.json` (current review assignment).

No EU/UK relevance test is applied to this global scanner. EU/UK publishers can report eligible research about locations elsewhere. Separate EU-focused Radar and its Deep Scan files remain untouched.

## Local checks

`python -m unittest discover -s tests -p 'test_relevance_focus*.py' -q`
