# v22.1 — browser-upload compatibility + honest corpus count

- Fixed GitHub Actions failure caused by stale old test files surviving browser uploads.
- Main workflow now discovers only `tests/test_all.py`; that loader runs the bundled current suite.
- Homepage count now covers both corpora: current radar + historical.
- Homepage labels the second number explicitly as **source organisations**, not publications.
- Topic cloud itself remains based on current radar evidence only, so "moving" topics stay genuinely current.

# v22.0 — reader navigation and layout reform

- Replaces the old landing hierarchy with a one-screen homepage: live evidence/source count, full menu and a source-weighted topic map.
- `Read at least this` is now the first red route everywhere.
- Adds one shared inner-page shell with a plain-language purpose sentence for every main page.
- Adds a single five-role type scale with a 14px minimum label size.
- Replaces horizontally disappearing mobile navigation with a visible grid.
- Collapses the Matrix into readable row/cell sections on phones instead of squeezing five columns.
- Adds persistent Top controls and Filters controls where a filter toolbar exists.
- Removes the visible `Matrix cell: …` internal plumbing text.
- Adds `topic_vocabulary.json`, `topic-cloud.js`, `home.css`, `reform.css`, `site-shell.js` and `DESIGN_CONTRACT.md`.
- Scanner admission, radar/historical corpora and analytical page engines are preserved.

# v21.22

- Ongoing Phenomena / Pattern Watch now leads every pattern card with one plain-language finding sentence.
- Tags, metrics, facets, why-it-matters, artefact check and evidence follow after the sentence.
- Main scanner, Historical scanner, workflows, evidence corpora and the v21.20 journal-diversity allocation are unchanged.

# v21.16 — workflow-upload compatibility repair

- Fixes the Main pre-scan regression gate when GitHub browser bulk upload leaves the older hidden `.github/workflows` YAML in place.
- Schedule tests now validate the intended current workflow semantically and explicitly accept the repository's known legacy workflow only when the scanner-side compatibility layer is present.
- Keeps the intended current workflows in the repository: Main every four hours, Historical two hours offset, shared non-cancelling concurrency queue.
- No Main discovery/admission methodology, Historical evidence, radar corpus, Ongoing Phenomena logic, or reader page logic changed.

## v21.18 — Ongoing Phenomena: pattern discovery layer

- Built on the user's latest uploaded repository and current radar data; no scanner or workflow logic changed.
- Ongoing Phenomena now leads with Pattern Watch: framing/vocabulary shifts and strengthening conjunctions across historical + current evidence.
- Adds a separate "Worth checking" candidate layer and an explicit "Could this be an artefact?" counter-case for every proposed pattern.
- Keeps established continuities as a secondary reference layer and reports current evidence outside the hand-written phenomenon matchers.
- Return/dormancy claims remain withheld when historical date precision is too weak.

## v21.20 — journal/source diversity + Pattern Watch heading polish

- Uses the user's latest downloaded repository as the base; Main/Historical workflows and evidence corpora are preserved.
- Pattern Watch now keeps the v21.19 sibling-pair clustering and capitalises generated finding headings at the analysis and render boundaries.
- Main scholarly discovery now interleaves Crossref priority tasks across journals instead of spending a partial priority slice on many queries from one venue.
- Within the existing Crossref source-first request budget, a persisted rotating lane targets configured journals with zero or one accepted A/B item. It is interleaved with policy, Q1 and broad journal lanes.
- Diversity changes discovery attention only. It does not create source quotas, relax EU/R&I relevance, or bypass quality/admission rules.
- The current corpus has 171 configured priority journals; 143 have no A/B representation, so the diversity lane has substantial unexplored scholarly territory to work through.
