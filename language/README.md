# Reader Language

This is a manual, non-blocking readability pass. The website never depends on it.

## Workflow

1. Run **Actions → Build reader-language batch → Run workflow**.
2. The action writes a JSON batch to `language-outbox/` (about 10,000 words by default).
3. Give that JSON file to an LLM together with the instructions already embedded in the file. Ask it to return the completed JSON only.
4. Put the returned JSON file in `language-inbox/` and commit it.
5. **Apply reader-language inbox** validates the return, applies safe matching edits, archives the returned batch, its original outbox copy, and a report, then opens a pull request.
6. Review the normal GitHub diff and merge if the language is better.

## What code decides vs. what the LLM decides

The collector decides only which text is eligible reader-facing prose. It does **not** try to judge whether the writing is bad.

The LLM decides for each item:

- `keep` — already readable;
- `rewrite` — clearer wording is possible without changing meaning;
- `skip` — rewriting would risk changing meaning.

## Safety / failure behaviour

- Publication is unrelated to this workflow.
- The canonical source remains usable whether or not a language batch is ever run.
- Every item contains a SHA-256 hash of the original text.
- A stale, malformed, or ambiguous item is rejected rather than forced into the source.
- Numbers and URLs have simple mechanical preservation checks.
- Returned changes go to a pull request, not directly to the published branch.
- Successfully reviewed hashes are recorded in `language/state.json`; future batches skip unchanged text unless **rescan** is selected.

## Selection rules

`language/config.json` controls eligible file patterns, excluded paths, data-field names, minimum item length, target batch size, and conservative (`light`) paths such as radar material.

The first implementation intentionally skips HTML blocks containing nested markup such as links or emphasis. This is conservative: it is better to miss a passage than to damage its markup. Those cases can be added later with a DOM-aware locator if useful.
