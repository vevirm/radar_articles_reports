# Radar V25 — handoff for a new chat

This repository is the completed **Deep Scan V2 authoritative-corpus migration**.

## Trust model

- Automatic scanner = fast provisional discovery/interpretation.
- Deep Scan V2 = authoritative verification once imported successfully.
- Raw scanner records are preserved in `radar.json`.
- `admission_state.json` stores V2 active/inactive/review/duplicate decisions.
- `record_corrections.json` stores validated metadata corrections.
- `radar_active.json` is the public/analytical active corpus.
- `reader_text.json` preserves existing interpretations; V2 entries supersede provisional semantics once verified.

## Critical behavior

Deep Scan packages contain at most 12 works and are FIFO. The LLM must process in supplied order, cannot cherry-pick, must exhaust a six-step retrieval ladder on difficult records, and cannot use snippets/title-only/scanner prose as substantive evidence. The importer enforces a consecutive FIFO prefix, so later easy records cannot be accepted while an earlier hard record is skipped. `DROP_UNVERIFIABLE` is accepted only after the mandatory recovery audit. Recovered KEEP/REVIEW/DROP decisions require substantive matching primary/repository evidence.

New discoveries continue appearing provisionally while they wait for Deep Scan. After V2 import, corrected interpretation/admission/provenance flow into the active corpus, and rankings/Excel/downstream reasoning are rebuilt from active evidence only.

## First GitHub action

Run **Radar V2 — Initialise, Validate & Prepare Deep Scan** once after the full repository upload. Download its artifact and give `deep_scan_package.zip` to the browsing LLM. Upload the returned result to `deep_scan_inbox`; the import workflow rebuilds the Radar and automatically creates the next package.

See `START_HERE_AFTER_UPLOAD.txt` and `DEEP_SCAN_SETUP.md` for exact steps.
