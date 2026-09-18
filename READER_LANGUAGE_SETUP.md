# Reader Language — simple manual use

Reader Language is optional. The website keeps publishing normally even if you never run it.
There is no AI connection to GitHub and no API key.

## What GitHub does by itself

The repository has a small non-AI prose checker. It only looks at approved reader-facing analytical
text. It ignores Main Radar evidence, Earlier Findings evidence, Sources, Stuff/Excel, scores,
dates, links, Deep Scan decisions and reasoning data.

It remembers exact text that has already been reviewed. Unchanged reviewed wording does not come
back again. If the analytical text changes, its fingerprint changes and the new wording can be
reviewed later. An old rewrite can never silently attach itself to changed analytical text.

## When you want a language review

You do **not** need to do this for every site update. Let the queue accumulate and run it whenever
you want.

1. Open **Actions** in GitHub.
2. Click **Reader Language — Prepare Review Package**.
3. Click **Run workflow**. Leave `flagged` and `40` as they are unless you have a reason to change them.
4. When the run is green, open it and download **reader-language-package**.
5. Give `reader_language_package.zip` to the LLM you use manually.
6. Say exactly:

   **Process this RADAR Reader Language package strictly according to INSTRUCTIONS.md and return reader_language_results.json.**

7. Download the returned `reader_language_results.json`.
8. In the repository open **reader_language_inbox** → **Add file** → **Upload files**.
9. Upload `reader_language_results.json` and commit directly to `main`.
10. GitHub validates it. If the import workflow is green, the approved wording is live after GitHub Pages refreshes.

## If some items are not imported

The import checks every item on its own. Good items are saved even if others fail.
An item is skipped (and simply comes back in a later package) when:

- its text is no longer on the site because the finding changed after the package was made;
- the rewrite would change meaning: numbers, adding/removing "not", adding/removing "may/could";
- the LLM edited the `source` or `display_text` fields instead of only `replacement`.

The run stays green. Open it to see a table of skipped items and why.

## What KEEP means

The LLM is explicitly told that **KEEP is normal**. It should not rewrite good text just to be busy.
A review can therefore contain many KEEP decisions and only a few rewrites.

## What happens if you do nothing

Nothing breaks. The page shows its normal generated wording. Reader Language is a polish layer, not
a dependency of scanning, Deep Scan, inference, Trends, Ongoing Phenomena, Matrix, Risks,
Opportunities or External Shocks.
