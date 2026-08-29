# R&I Geopolitics Radar V17.13.28

## Current release — source-specific Radar claims + source-summary Excel

V17.13.28 keeps the V17.13.26 Matrix semantic contract and V17.13.27 language hierarchy, but removes reusable topic slogans from the main Radar. The Radar now prefers a concrete source proposition — actor/instrument/dependency plus the specific consequence — and can use a longer policy-technical sentence when necessary. The Excel workbook now begins with a **What sources say** sheet and also carries source-summary bullets in the ranked and technical sheets.

The current evidence rules remain: public A/B evidence is English-publication only; inference-only external-shock bridges are disabled; normal evidence uses a four-calendar-month core; only A/B evidence in the existing Highest source-merit band may be discovered and retained to six months.

### Reader-language hierarchy

The same evidence is deliberately phrased at different levels.

1. **Read at least this — simplest.** Short, ordinary-language explanations. It translates policy vocabulary rather than expecting the reader to know it.
2. **Matrix and Risks & opportunities — simple analytical.** Short phrases about what Europe gains, loses, controls or relies on. The full Matrix keeps technical placement diagnostics behind a disclosure instead of putting them in the main reading path.
3. **Main Radar and Evidence browser — policy-technical.** Standard R&I-policy terms such as research security, strategic dependency, technological sovereignty, talent circulation, scale-up finance and research infrastructure are allowed when they are the clearest accurate terms. Record details remain available.
4. **Excel technical evidence workbook — most technical.** It now also tells the reader what each paper/report says in one to four source-grounded bullets (depending on stored source text), then carries source-merit components, admission/review notes, evidence families, Matrix criteria, placement confidence, screening score, provenance and technical source-review fields.

This hierarchy is a presentation rule only. It does not change admission, source merit or Matrix placement.

## What readers see

### 1. Read at least this

`read/` rebuilds the leading issue set from current admitted material. It is the easiest entry point: short issue trees and source-backed findings in the simplest language used anywhere on the site. The main Radar is the next step when a reader wants the policy terminology and full record detail.

### 2. Matrix and Risks & opportunities

The Matrix is intentionally easier to read than the main Radar. Its public rows are **People & knowledge**, **Tools & facilities**, **Firms & growth**, and **Rules & decisions**. Its columns are **More control, stronger**, **More control, some cost**, **Stronger, but reliant**, and **Less control, weaker**. Cell labels use direct outcome language such as **Build and keep talent**, **Useful outside access**, and **Value and scale move abroad**.

`frontier/quick/` is the shortest view. `frontier/` adds source detail, while technical classifier diagnostics are tucked under **Technical placement check**. `priorities/` presents ranked risks and opportunities as compact cards using the same simple analytical language.

Every Matrix placement must show the **row mechanism + control/dependence direction + performance direction** in source-supported evidence. Generic words such as “foreign”, “risk”, “capacity”, “investment” or “access” cannot create a cell. Sparse cells receive more discovery effort, never lower admission standards.

### 3. Main Radar and Evidence browser

The main Radar is accessible but deliberately more technical than Read or the Matrix. It keeps normal R&I-policy vocabulary when that vocabulary is precise, and gives the reader expandable record detail: original publication title, authors, source, date, source merit, full available summary, relevance/admission note, evidence, discovery route and Matrix material where present.

The Evidence browser uses the same policy-technical level as the main Radar, grouped by evidence type.

### 4. Technical Excel export

`stuff/source_merit_ranking.xlsx` is the technical evidence workbook. It opens with **What sources say**, a source-by-source bullet summary, followed by ranked sources, a detailed technical evidence sheet, the full 16-cell Matrix criteria contract and a method sheet explaining the language hierarchy, four-/six-month window and source-merit model. Where the saved radar does not contain substantive source text, the workbook says that explicitly instead of inventing findings.

## How discovery changed

### Literal “geopolitics” is not required

The **normal Strand-A route** still requires all three things:

- EU/European R&I as the subject;
- substantive research, science, innovation, technology or related-system evidence; and
- strategic context.

Strategic context can be explicit (geopolitics, economic security, strategic competition, etc.) or triangulated from multiple mechanisms. The triangulated route is intentionally fail-closed for one-cue cases. There is no inference-only external-shock exception: a non-EU development must contain its Europe/R&I strategic consequence in the source evidence itself.

### Existing findings help form later searches

A small `finding-context` lane turns recurring themes already present in Strand A into rotating scholarly searches. It does **not** auto-admit similar material. Search results return to the ordinary source, recency, EU/R&I and strategic-context gates.

This makes discovery iterative in a bounded way: the radar can learn where the live conversation is without turning yesterday's findings into tomorrow's admission rule.

### Researcher names are fallback attention

`priority_people.json` remains an auditable list of 137 researchers. Named-researcher discovery is not a separate corpus, badge or whitelist. In V17.13.3 it is mainly triggered when ordinary scholarly discovery is thin or Matrix coverage is very sparse. Exact-author works and any bounded context fallbacks still rejoin the normal OpenAlex/Crossref admission path.

### Strand C stays a minority

Weak signals no longer receive the protected follow-up query wave. After the A/B/C merge, Strand C is capped at **15% of all public findings**. This is a ceiling, not a quota: the scanner should not search merely to fill C. Within that cap, signals still require source-supported relevance; a generated Europe-impact bridge cannot create eligibility.

## Four-month core + Highest evidence to six months

The preferred/current evidence window is the latest four calendar months. On the bundled 29 August 2026 state the four-month floor is **2026-04-29**.

A/B has one narrow exception: a publication/report that scores **Highest (93–100)** under the shared source-merit model may be discovered in the 4–6 month band and retained until six calendar months. The extended floor is **2026-02-28** for the bundled state. All other A/B evidence, Strand C and Matrix-only recovery keep the four-month rule.

The extended lane is bounded and runs after current-window work so older high-quality material cannot crowd out fresh discovery. A record must actually reach the Highest band to use the extension.

The bundled `radar.json` is descended from the user-supplied post-scan `radar (38).json` state and the explicitly requested V17.13.24 precision cleanup; current counts are **182 A / 24 B / 14 C**. V17.13.28 removed four additional high-confidence legacy contaminants exposed by the source-specific claim audit; no discovery scan was run while packaging V17.13.28. See `CURRENT_CORPUS_INPUT.txt`.


## Scanner rotation

The existing OpenAlex, Crossref, journal/institutional, methods and matrix-gap rotations remain. V17.13.3 makes Matrix coverage an explicit input to rotation. The Matrix median becomes a bounded moving coverage target (minimum 3, maximum 10): cells below that level receive the reserved gap-search budget first, with zero cells weighted most heavily. Coverage is recomputed during matrix-depth waves, so attention moves as cells fill instead of stopping once an empty cell gets one item. This changes search effort only; admission standards remain unchanged and the scanner does not manufacture equal counts. The finding-context lane remains, and the main query families obey the four-month core floor. External-actor material is processed through the same direct source-evidence gate as everything else; no generated bridge can admit it. A separate bounded institutional lane checks months 4–6 only for sources capable of reaching the Highest merit band, and candidates must actually score Highest before admission.

The scheduler remains active on push and manual dispatch via `.github/workflows/radar-scan.yml`. Scheduled wake-ups occur hourly; a due-gate runs the expensive scanner only after at least six hours have elapsed since the last completed scan. This catch-up design is deliberate because hosted GitHub Actions cron triggers can be delayed or occasionally missed.

## Manual candidate ingest

```bash
python scripts/manual_ingest.py path/to/candidates.docx --state radar.json
```

Accepted inputs: DOCX, PDF, CSV, JSON, YAML/YML, TXT and Markdown. A curator list is a **candidate/recovery source**, not evidence by itself. A new item is admitted only when the underlying reviewed source clears the same substantive standard as automated discovery. Metadata-only material defers; secondary, forthcoming, context-only and unresolved records remain distinguishable.

Reviewed evidence caches must be tied to the exact curator-supplied URL and record their evidence mode/status. Curator Matrix cells are retained as hypotheses; reviewed source evidence determines final placement when available.

## Useful files

- `read/index.html` — issue-tree entry point
- `frontier/quick/index.html` — simple Matrix
- `frontier/index.html` — full Matrix with source detail; technical diagnostics are secondary
- `priorities/index.html` — risks & opportunities
- `literature/index.html` — alphabetical literature used
- `stuff/index.html` — technical evidence workbook + reference-manager exports
- `scripts/scan_radar.py` — discovery/admission scanner
- `radar_criteria.md` — admission rules
- `frontier_criteria.md` — Matrix rules and public/internal terminology mapping
- `CHANGELOG_V17_13_28.md` — current release changes
- `VALIDATION_V17_13_28.md` — current validation record
- `CURRENT_CORPUS_INPUT.txt` — exact input/bundled-state record

## Validate

Current release checks:

```bash
node scripts/presentation_smoke.js
node scripts/test_matrix_semantic_contract.js
python -m py_compile scripts/scan_radar.py scripts/manual_ingest.py scripts/build_briefing.py
```

`presentation_smoke.js` verifies the page/runtime and reader-language boundaries without running network discovery. `test_matrix_semantic_contract.js` covers all 16 Matrix cells plus false-positive cases. See `VALIDATION_V17_13_28.md`.


## Reader views

The reader shell links Radar, Matrix short/full, Risks & opportunities, Read at least this, and an alphabetical Literature used page.

## V17.13.4 — source attention without source gate inflation

Discovery now gives more scan budget to two source families: high-quality journal articles and official EU reports. A small verified SCImago SJR 2024 Q1 shortlist receives recurring source-first journal slots, while Commission, JRC, Publications Office, Parliament, Council and related EU-primary domains receive recurring institutional slots.

This is **attention, not admission**. The scanner keeps a broad source share of at least 40%, continues ordinary OpenAlex/Crossref and institutional rotation, and uses the same EU-R&I-geopolitical substantive gate for every source. A Q1 article does not get in because it is Q1; a lower-ranked or unranked source is not excluded if it contains strong evidence. This avoids the failure mode where prestige filters become so strict that recall collapses.


## V17.13.5 — stronger Matrix catch-up + front page

- Matrix rotation now catches up toward the upper quartile and 55% of the richest cell, capped at 12.
- Thin rows and columns add discovery pressure; rich cells keep normal broad discovery but lose gap-search priority.
- Empty cells lead depth searches but no longer monopolise them: other sparse cells are interleaved in every depth wave.
- Admission standards are unchanged. Balance changes search allocation only.
- Front page now opens with “R&I in EU: Geopolitical Context”, the eight recurring issues, and a clear map of all subpages.
- Reader palette is black, white and red; green/blue semantic colouring is removed from the main reader views.

## Front-page reader map (2026-08-28)
The landing page now shows the reader journey before the page chooser: Orient → Evidence → Position → Decisions → Sources. Each step says what the reader finds there and links to the corresponding page. The short-to-full relationship is stated explicitly, especially Matrix short → full evidence.


## V17.13.6 — Matrix semantic balance correction

- The Matrix now requires the cell's semantic contract for every non-reviewed source record, not only weak signals.
- A reviewed source-level Matrix decision remains authoritative and is not discarded by a second generic keyword check.
- Generic AI/regulation language no longer counts as infrastructure without a concrete compute, chip, data, materials, facility or supply mechanism.
- This reduces classifier pile-ups without hiding evidence: the Quick Matrix still shows every finding accepted by the full Matrix.
- Scanner rotation reads these corrected cell counts. Catch-up now aims at 75% of the richest cell (still capped) and gives sparse cells more scholarly/institutional search slots.
- Matrix balancing changes discovery allocation only. The EU-R&I-geopolitics admission gate is unchanged.
- The landing-page “What you find in the pages.” heading is enlarged.

### V17.13.7 rotation guarantee
Matrix balance is now explicitly permanent: every future scan recalculates cell coverage and gives thin cells extra discovery attention as one factor among the scanner's other rotations. It does not become a quota and does not weaken admission.


## V17.13.8 — Stuff / exports

A separate **Stuff** workbench keeps utility functions out of the main reading flow. It can export the live Matrix as CSV for the whole Matrix, one row, one column or one exact cell; the packaged XLSX contains all of those slices as tabs. The same page exports Literature used as CSV, BibTeX and RIS.

The page also isolates the publications worth opening first. This is an **attention ranking, not a gate**. Primary or official EU acts/reports rank above reporting about them when the primary document is present. Peer-reviewed research and strong strategic-policy sources follow, with evidence quality, materiality and freshness refining the order.

## V17.13.9 — source-bound “why it matters”

The reader no longer fills “why it matters” with reusable topic sentences. Each displayed consequence is taken from the individual record’s source summary, reviewed evidence, Matrix evidence or source-bound core message and kept within the 120-character reader limit. If no separate source-grounded consequence can be stated safely, the line is omitted instead of replaced with a generic implication. Radar data, Matrix placement, admission and rotation are unchanged.

## V17.13.10 — less repetition, usable spreadsheet exports, open maps

The Quick Matrix now describes the individual publication rather than repeating quadrant wording such as “raises EU control and capacity”. Exact duplicate publication-version points are grouped in the quick reader, while the full Matrix retains all 62 qualifying source records. Uneven cells remain visible and feed the permanent Matrix-balancing search rotation; this release does not manufacture balance by dropping or moving evidence.

`Read at least this` now arrives with all eight issue maps open. The Stuff page downloads live Matrix/literature/priority slices as Excel-friendly tab-separated files, and the packaged XLSX mirrors the same source-specific Matrix wording. `Why this cell` is shown only where a saved source-backed Matrix rationale exists; otherwise it stays blank instead of using generic prose.

This is a presentation/export repair only: no fresh scan, no Radar-data change, no Matrix admission/classifier change and no rotation-rule change.


## V17.13.11 — publication-specific reader cleanup

- `Read at least this` now renders all eight charts immediately rather than using collapsible issue panels.
- Matrix candidate input is deduplicated at publication level, including landing-page/PDF variants, before classification.
- Both Matrix views use source-specific publication points; the full Matrix also explains why each publication matters in that cell.
- `Why it matters` now has non-blank mechanism text and avoids echoing the displayed claim. Matrix signals use paper-specific mechanisms instead of generic cell language.
- `Risks & Opportunities` is capped and diversified by topic so one repeated subject cannot dominate either list; detail views add the publication and a concrete mechanism.
- `Stuff` now leads with a real `.xlsx` publication workbook and an on-page publication preview. The workbook contains deduplicated publications, what each says, why it matters, Matrix placement and source URLs. TSV remains available only where it is explicitly labelled TSV.
- Rotation logic itself is unchanged: recurring multifactor search rotation and sparse-Matrix targeting continue to advance only on executed work.


## V17.13.12 — historical test-suite migration

- Replaced the obsolete `test_findings.py` imports of retired `make_finding`, `backfill_finding` and `build_findings_data` helpers with tests of the current publication-record pipeline.
- Migrated older tests that hard-coded superseded UI text, version/profile names, manual-only scanning, old Matrix acceptance rules, and fixed corpus snapshots so they now test the current contracts rather than historical implementation details.
- Kept stricter source-specific Matrix behavior explicit in tests: unsupported generic opening/loss claims are not treated as evidence merely because they contain the right keywords.
- Updated reader tests to match the current design: all eight issue charts are rendered immediately, concise claims stay within the 120-character reader budget, and paper-specific “why it matters” explanations may be longer when needed to state the mechanism.
- Added `pytest.ini` so the full suite imports `scripts` correctly when invoked as plain `pytest`.
- No scanner, Matrix, reader, rotation, prioritisation, or corpus-data logic was changed in this test-maintenance release.


## V17.13.13 — explicit “what it says” + simple bibliography workbook

- Radar publication cards now show the actual publication title as the card heading, followed by **What it says for EU R&I geopolitics** and then **Why it matters**.
- The new “what it says” line is a complete sentence, never hard-cut or ellipsised, and has a hard **150-character maximum**.
- The Stuff page is no longer a Matrix/export workbench. Its main action is one button: **Download bibliography + summaries (.xlsx)**.
- The workbook opens directly on a single `Bibliography` sheet. There is no cover/read-me sheet, Matrix codes, scores or setup page.
- Workbook columns are limited to publication, authors, date, publisher/channel, type, what it says for EU R&I geopolitics, why the reader should care, and source link.
- The deployment bundle contains one Excel download only: `stuff/bibliography_and_summaries.xlsx`.
- BibTeX and RIS remain available for reference-manager use. Scanner admission, Matrix placement and rotation are unchanged.

## V17.13.14 — plain-English glossary

`glossary/` adds a searchable 50-term plain-English glossary for recurring jargon across the Radar. Each term has a short definition and a separate explanation of why it matters for EU R&I in geopolitical context. The Glossary is linked from the main Radar toolbar/page chooser and all principal reader pages. Scanner and rotation logic are unchanged.

## V17.13.18 — source merit ranking in Stuff

- Bundled `radar.json` is refreshed to the user-supplied scan state from 2026-08-28T20:50Z (A=224, B=25, C=14).
- `Stuff` now leads with `source_merit_ranking.xlsx`, a ranked publication/report workbook showing journal or institution, author, source quality/reputation, technical evidence, source-merit components, Matrix fields and source links.
- Official EU primary sources are deliberately ranked highest for this EU R&I geopolitics use case. The score is transparent and documented on the workbook's `Method` sheet.
- The workbook is not an input to the scanner. Scanner admission, scoring, Matrix classification, source rotation and evidence logic are unchanged.
- V17.13.17 workflow security hardening and the 6-hour scan schedule remain unchanged.


## V17.13.20 — source merit becomes a shared evidence-weight layer


### V17.13.21 — live issue discovery

`Read at least this` and the landing-page issue strip now rebuild their issue list from the current radar material. The fixed eight-issue public structure is removed. The scanner admission rules are unchanged; this is a downstream reader reorganisation only.

The source-merit ranking is no longer confined to Stuff. The main Radar, Read at least this, Evidence browser, both Matrix views, Risks & opportunities, Literature used and Stuff now expose the same plain evidence-weight labels: **Highest**, **Very strong**, **Strong**, **Useful** and **Supporting**.

The weighting is deliberately downstream of the scanner. It does not decide admission and it does not change a Matrix cell. It helps the reader judge how hard to lean on a finding. In the fast decision views it also helps stronger evidence outrank weaker evidence when the underlying Matrix severity/relevance is otherwise comparable. Read at least this still selects by issue fit first, then source merit; Literature used remains alphabetical but shows the weight beside each source.

The six-hour due interval remains, with V17.13.22 hourly catch-up checks, security credential separation and strengthened in-window preservation hard stops.


## V17.13.23 — four-month core with Highest evidence to six months

The radar now uses a two-tier time policy. The preferred/current corpus is still the latest four calendar months. A/B records that score **Highest (93–100)** under the same source-merit model used in the reader may be discovered in the 4–6 month band and are retained until they reach six calendar months. This exception does not apply to Strand C or Matrix-only recovery. Normal discovery runs first; the extended lane is bounded and source-selective so older material cannot crowd out current scanning.


## V17.13.24 — source-supported relevance + English-publication boundary

- Disables inference-only `external-strategic-shock` admission for A and C. A non-EU development must itself state a substantive EU/European R&I strategic consequence.
- Makes public A/B evidence English-publication only. Foreign-language titles/metadata and meaningful non-Latin source prose fail closed; an English abstract no longer rescues a foreign-language publication.
- Adds a presentation fail-safe so a non-English title cannot render on the main page even if a malformed legacy row reaches `radar.json`.
- Migrates the bundled corpus conservatively: removes 15 legacy inference-only external A records, 2 non-English A publications, and 25 audited high-confidence legacy direct-route contaminants; no discovery scan is run during packaging.
- Keeps the V17.13.23 time policy unchanged: four-month core, Highest-merit A/B eligible to six months.
