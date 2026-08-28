# R&I Geopolitics Radar V17.13.6

V17.13.3 keeps the V17.13 reader-first design but tightens the subject rule and adds a bounded external-shock exception. The public evidence window remains a hard rolling **four calendar months**. A paper or report no longer has to say *geopolitics* explicitly: it may also qualify when genuine EU/European R&I is connected through a conservative, triangulated strategic mechanism such as technological dependence, capability competition, international coordination, research security, critical infrastructure, standard-setting/governance power, or research-talent competition.

This is not a looser relevance gate. The non-literal route needs at least **two independent strategic families**, including at least one relational/control family. A generic paper that merely says Europe should be more competitive still fails.

**The subject is EU/European R&I in geopolitical context.** EU relevance is not just one filter among many. Normally, the source itself must establish the European R&I subject. The exception is a major external R&I shock — for example a step-change in US or Chinese AI, quantum or chip capability — when it matches a current same-domain EU context anchor and its consequence for Europe can be written as one specific plain-language sentence. That bridge is marked as a radar inference, not source wording.

**English is required for the evidence, not necessarily the whole publication.** A non-English paper can qualify when the source/index exposes enough English abstract, executive-summary or equivalent text to verify the finding. A foreign-language title plus an English abstract can therefore pass; a title-only or tiny metadata stub cannot. The radar does not machine-translate an inaccessible foreign text and use that translation as evidence.

## What readers see

### 1. Read at least this = an issue tree

`read/` now starts with **eight stable main issues**, not a long briefing:

1. People & knowledge
2. Compute & research infrastructure
3. Chips, materials & supply chains
4. Firms & scale
5. Rules, standards & security
6. International partnerships
7. Strategic technology races
8. Funding & programmes

Each issue opens as a connected branch map: main issue → branches → individual subissues. The first map is open by default, and readers can open all maps at once. Current radar findings sit below each map.

### 2. Simpler Matrix

The reader-facing Matrix uses four plain rows:

- People & knowledge
- Tools & infrastructure
- Firms & scale
- Rules & coordination

and four plain outcomes:

- Stronger on both
- More control, more cost
- Faster, but dependent
- Weaker on both

`frontier/quick/` is the **“just see it”** version. It shows **every** qualifying Matrix finding in its cell as a subject-first bullet of 50 characters or fewer. `frontier/` keeps the full evidence and classification detail.

Every admitted Strand-A finding is sent to the Matrix classifier. There is no extra hidden “dynamic” pre-filter before classification. The classifier can still leave a finding out when its evidence does not support a defensible row and direction.

### 3. Easy radar keeps the full record reachable

The main radar remains the easy/reader-first view: plain claim first, then a short “why it matters” **only when the individual record supports a separate concise consequence**. Generic topic fillers are not used. Nothing important from the evidence record is discarded from the interface. Each card has **All record details**, and the toolbar has **Show all details** to open the detailed fields across the visible cards at once. That disclosure includes the original title, authors, source, date, type, source tier, EU relevance, discovery route, tracked-since date, full available summary, relevance/admission note, available R&I/strategic evidence, Matrix placement/evidence where present, and the external-Europe bridge when the exceptional route is used.

### 4. Reader-first claims

Reader-facing prose is shorter and concrete. Bibliographic and source detail is preserved separately instead of being stuffed into the finding itself. The write boundary includes explicit handling for the e-hryvnia, cyber-governance, AI-for-science, CEPS technology-mapping and EU–India/open-hardware examples. Biographical material such as a researcher's training or job title is not used as the finding unless it is itself relevant evidence.

The Risks & opportunities page is deliberately minimal: two ranked bullet lists, with source detail available on click.

The same plain-language layer is used by the main radar, Matrix, Risks & opportunities and secondary briefing view.

**Reader-point contract:** every displayed finding and “why it matters” point is one complete sentence of **120 characters or fewer**. “Why it matters” must be derived from that record’s summary, reviewed evidence, Matrix evidence or source-bound core message; if no separate consequence can be stated safely, the line is omitted rather than replaced with a generic theme sentence. It must start with an explicit actor, system or topic — never vague openers such as “this”, “these”, “it”, “they”, “the study”, “the findings” or “the developments”. The UI never truncates a sentence or adds an ellipsis to force the limit.

## How discovery changed

### Literal “geopolitics” is not required

The **normal Strand-A route** still requires all three things:

- EU/European R&I as the subject;
- substantive research, science, innovation, technology or related-system evidence; and
- strategic context.

Strategic context can be explicit (geopolitics, economic security, strategic competition, etc.) or triangulated from multiple mechanisms. The triangulated route is intentionally fail-closed for one-cue cases. The separate external-shock exception does not weaken this normal gate.

### Existing findings help form later searches

A small `finding-context` lane turns recurring themes already present in Strand A into rotating scholarly searches. It does **not** auto-admit similar material. Search results return to the ordinary source, recency, EU/R&I and strategic-context gates.

This makes discovery iterative in a bounded way: the radar can learn where the live conversation is without turning yesterday's findings into tomorrow's admission rule.

### Researcher names are fallback attention

`priority_people.json` remains an auditable list of 137 researchers. Named-researcher discovery is not a separate corpus, badge or whitelist. In V17.13.3 it is mainly triggered when ordinary scholarly discovery is thin or Matrix coverage is very sparse. Exact-author works and any bounded context fallbacks still rejoin the normal OpenAlex/Crossref admission path.

### Strand C stays a minority

Weak signals no longer receive the protected follow-up query wave. After the A/B/C merge, Strand C is capped at **15% of all public findings**. This is a ceiling, not a quota: the scanner should not search merely to fill C. Within that cap, a qualifying major external strategic shock is ranked ahead of ordinary weak signals so the minority rule does not accidentally hide the kind of event that could abruptly reset Europe’s position.

## Four-month rule

`BOOTSTRAP_LOOKBACK_MONTHS = 4` is the public-window rule. Saved rows, recovery rows and matrix-only historical rows cannot widen it. On the bundled 28 August 2026 state the publication floor is therefore **2026-04-28**.

The bundled `radar.json` is the user-supplied **post-scan `radar (35).json`** state, timestamped **2026-08-28T13:43Z** and already using the exact **2026-04-28** public floor. V17.13.5 preserves its admitted records, evidence fields and scan cursors while retaining the current reader interface and scanner rules. **No additional discovery scan was run during packaging.**

## Scanner rotation

The existing OpenAlex, Crossref, journal/institutional, methods and matrix-gap rotations remain. V17.13.3 makes Matrix coverage an explicit input to rotation. The Matrix median becomes a bounded moving coverage target (minimum 3, maximum 10): cells below that level receive the reserved gap-search budget first, with zero cells weighted most heavily. Coverage is recomputed during matrix-depth waves, so attention moves as cells fill instead of stopping once an empty cell gets one item. This changes search effort only; admission standards remain unchanged and the scanner does not manufacture equal counts. The finding-context lane and bounded external-shock queries remain, and every query family obeys the same four-month date floor.

The scheduler remains active on push, every 12 hours, and manual dispatch via `.github/workflows/radar-scan.yml`.

## Manual candidate ingest

```bash
python scripts/manual_ingest.py path/to/candidates.docx --state radar.json
```

Accepted inputs: DOCX, PDF, CSV, JSON, YAML/YML, TXT and Markdown. A curator list is a **candidate/recovery source**, not evidence by itself. A new item is admitted only when the underlying reviewed source clears the same substantive standard as automated discovery. Metadata-only material defers; secondary, forthcoming, context-only and unresolved records remain distinguishable.

Reviewed evidence caches must be tied to the exact curator-supplied URL and record their evidence mode/status. Curator Matrix cells are retained as hypotheses; reviewed source evidence determines final placement when available.

## Useful files

- `read/index.html` — issue-tree entry point
- `frontier/quick/index.html` — simple Matrix
- `frontier/index.html` — evidence-rich Matrix
- `priorities/index.html` — risks & opportunities
- `literature/index.html` — alphabetical literature used
- `stuff/index.html` — exports + most important publications
- `stuff/radar_exports.xlsx` — packaged Matrix/literature export workbook
- `scripts/scan_radar.py` — discovery/admission scanner
- `radar_criteria.md` — admission rules
- `frontier_criteria.md` — Matrix rules and public/internal terminology mapping
- `CHANGELOG_V17_13_8.md` — this release's changes
- `VALIDATION_V17_13_8.md` — validation record
- `CURRENT_CORPUS_INPUT.txt` — exact input/bundled-state record

## Validate

Focused reader / Matrix regression checks:

```bash
PYTHONPATH=. python -m pytest -q \
  tests/test_v17_13_1_subject_language_easy_view.py \
  tests/test_v17_13_0_feedback_round.py \
  tests/test_v17_13_reader_scanner.py \
  tests/test_v17_12_5_plain_language.py \
  tests/test_v17_12_6_priority_people_rotation.py \
  tests/test_v17_12_7_integrated_researcher_attention.py \
  tests/test_v17_6_4_true_rotation.py \
  tests/test_v17_9_source_aware_matrix.py \
  tests/test_v17_7_3_matrix_first_depth.py \
  tests/test_v17_7_5_rotation_cell_fill.py \
  tests/test_v17_5_5_balanced_matrix_priorities.py
```

See `VALIDATION_V17_13_8.md` for the V17.13.8 record and its appended V17.13.9 reader-copy validation.


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
