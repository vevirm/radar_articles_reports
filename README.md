# R&I Geopolitics Radar V17.12.7

V17.12.7 keeps the global reader-first language rule and folds a curated set of 137 European R&I researchers and policy thinkers into the **ordinary scholarly discovery process**. Their names are backend search anchors only. There is no people page, people section, people badge, separate corpus, or separate admission process. Once a work is discovered, it is handled exactly like every other OpenAlex/Crossref candidate and appears only where its substance places it in the existing radar, matrix, briefing, or evidence views.

Sixteen researchers receive extra discovery attention per scheduled scan, balanced across fields. Exact-author lookup is tried first; when that yields nothing, a small affiliation/topic fallback helps the normal scholarly search find substantive adjacent work, including work by people not on the curated list. The ordinary topic, journal, institution, Frontier-gap, historical-exploration, method, and weak-signal rotations continue unchanged.

Reader-first wording remains global: prominent claims are simplified before storage and again at display time, while original titles, abstracts/summaries, authors, sources, dates, links, and bibliographic detail stay unchanged underneath.

## Scanner rotation

`.github/workflows/radar-scan.yml` is active on relevant pushes, every 12 hours, and by manual dispatch. Researcher attention is an internal part of scholarly discovery. A private persisted cursor and cached OpenAlex author IDs make coverage fair across the 137 names without altering the normal discovery cursors. A full pass takes about nine scheduled scans at 16 researchers per scan, then repeats.

## Read-this-first subpage

`read/` is a deliberately simpler progressive-disclosure view of the same bundled corpus. It shows the main conclusion first, then three structural points. Reasoning opens on demand, and source evidence sits one level deeper. Four live shifts and three slower conditions remain collapsed until requested. The page is editorial synthesis; `radar.json` and the detailed reader pages remain the traceable record.

## Manual candidate ingest

```bash
python scripts/manual_ingest.py path/to/candidates.docx --state radar.json
```

Accepted inputs: DOCX, PDF, CSV, JSON, YAML/YML, TXT and Markdown. `--links-validated` records curator-tested reachability without treating reachability as substantive verification. `--no-fetch` is safe for comparison/registration; reviewed evidence can also be supplied with `--review-evidence PATH.json` when it is cryptographically/reproducibly tied to the exact supplied record URLs.

The lane extracts bibliography and URLs, deduplicates conservatively, retrieves the exact supplied source where possible, and evaluates the same substantive requirement as automated discovery: **genuine EU/European R&I in geopolitical context**. Metadata-only material defers. Secondary, uncertain, forthcoming and context-only records remain distinguishable.

A reviewed evidence cache is not a free-form manual override: each review must be URL-bound to the curator-supplied URL, source-verified, and explicit about its evidence mode/status. Primary-source resolution is permitted only when the supplied record itself needs it, while preserving the original supplied URL in provenance.

## Matrix-oriented manual lists

Curator cell mappings are stored as hypotheses, not answers. A reviewed source can be admitted when its underlying evidence passes the substantive gate; matrix placement then comes from reviewed source evidence (`matrix_dimension`, `quadrant_claimed`, `quadrant_implied`). The frontend honors that reviewed row/column instead of re-inferring the row from topic keywords.

Earlier reviewed supplements remain intact. V17.12.2 additionally ingests the declared **58-item rounds IV–VI block** from `EU_RI_Found_Items_Rounds_IV-VI.docx`: **10** new substantive items enter the radar and **7** receive independently reviewed matrix placements. The detailed batch decisions are in `MANUAL_INGEST_REPORT_ROUNDS_IV_VI.md`; earlier supplement decisions remain in `MANUAL_INGEST_REPORT.md`.

## Recall diagnostics and provenance

Manual candidates are compared against the admitted corpus and saved seen-URL ledger. Missed high-value exact URLs may enter bounded recovery queues; future automated scans can retry them without weakening pass-1 precision. Public records expose `automated`, `manual`, or `both` provenance. Manual diagnostics preserve both the curator-supplied URL and any directly resolved primary/full-text URL, including the direct-link chain used during review.

## Source-aware aboutness and claims

- Full text may use strict recurrence/section-spread checks.
- Abstract-only sources are judged substantively without nonexistent-section requirements.
- Metadata-only records defer and trigger retrieval.
- Bare `EU` is not assumed to mean European Union without context.
- Display claims state what the source finds, argues, reports or projects without boilerplate prefixes.
- Directional keywords support matrix classification but are not mandatory gates.
- `quadrant_claimed` and `quadrant_implied` stay distinct; evidence-implied placement controls when available.

## Priority-people attention list

`priority_people.json` is the auditable watch list. Each record contains a name, field, affiliation hint, and topic hints. The scanner interleaves fields, resolves exact author identity where possible, scans recent/full-retained-window works through the same scholarly admission functions as ordinary discovery, and records its own cursor under `scan_state.priority_people_cursor`.

If exact-author discovery yields no metadata record, the scanner can run a bounded context query built from affiliation + expertise + field. That fallback is intentionally broader than the named person: it is a way to give the existing rotation more substance when author metadata is weak, not a whitelist mechanism.

## State integrity

Manual ingestion is not a live scan. V17.12.2 starts from the user-supplied 26 August 2026 state and preserves its scanner timestamp (`last_updated`: **2026-08-26T08:57Z**) and scan cursors. The rounds IV–VI review is recorded separately under `manual_ingest.last_ingested_at` / batch history; no live scanner run was claimed or performed.

## Validate

For the V17.12.7 embedded researcher-attention behavior and the regression-sensitive existing rotation + reader-first behavior:

```bash
PYTHONPATH=. python -m pytest -q tests/test_v17_12_6_priority_people_rotation.py tests/test_v17_12_7_integrated_researcher_attention.py tests/test_v17_6_4_true_rotation.py tests/test_v17_12_5_plain_language.py
```

See `VALIDATION_V17_12_7.md` for the current validation record, including the known stale legacy-suite mismatches that are unrelated to researcher attention.

## V17.12.6 site structure

Primary navigation remains limited to **Read at least this**, **Main radar**, **Matrix**, and **Risks & opportunities**. `briefing/` remains available only as a secondary evidence browser. The scanner workflow preserves its existing push, 12-hour schedule, and manual-dispatch triggers.

Reader-facing claims now use a shared plain-language layer across the Main radar, Matrix, Risks & opportunities, and secondary evidence views. New scanner and manual-ingest records pass through the same write-boundary normalizer. Original publication titles, abstracts/summaries, authors, sources, dates, links, and other bibliographic detail are preserved separately and shown underneath or behind progressive disclosure.

