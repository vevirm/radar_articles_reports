# R&I Geopolitics Radar V17.13.3

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

The main radar remains the easy/reader-first view: plain claim first, then a short “why it matters”. Nothing important from the evidence record is discarded from the interface. Each card has **All record details**, and the toolbar has **Show all details** to open the detailed fields across the visible cards at once. That disclosure includes the original title, authors, source, date, type, source tier, EU relevance, discovery route, tracked-since date, full available summary, relevance/admission note, available R&I/strategic evidence, Matrix placement/evidence where present, and the external-Europe bridge when the exceptional route is used.

### 4. Reader-first claims

Reader-facing prose is shorter and concrete. Bibliographic and source detail is preserved separately instead of being stuffed into the finding itself. The write boundary includes explicit handling for the e-hryvnia, cyber-governance, AI-for-science, CEPS technology-mapping and EU–India/open-hardware examples. Biographical material such as a researcher's training or job title is not used as the finding unless it is itself relevant evidence.

The Risks & opportunities page is deliberately minimal: two ranked bullet lists, with source detail available on click.

The same plain-language layer is used by the main radar, Matrix, Risks & opportunities and secondary briefing view.

**Reader-point contract:** every finding and “why it matters” point is one complete sentence of **120 characters or fewer**. It must start with an explicit actor, system or topic — never vague openers such as “this”, “these”, “it”, “they”, “the study”, “the findings” or “the developments”. The UI never truncates a sentence or adds an ellipsis to force the limit.

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

The bundled `radar.json` was produced from the newer uploaded state, then pruned to that exact floor. Its existing reader claims are retained; V17.13.3 keeps that admission contract, evidence fields and disclosure UI rather than pretending to have re-scanned old records under the new external-shock route. **No fresh external discovery scan was run during packaging**, so the source state's `last_updated` timestamp is preserved.

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
- `scripts/scan_radar.py` — discovery/admission scanner
- `radar_criteria.md` — admission rules
- `frontier_criteria.md` — Matrix rules and public/internal terminology mapping
- `CHANGELOG_V17_13_3.md` — this release's changes
- `VALIDATION_V17_13_3.md` — validation record
- `CURRENT_CORPUS_INPUT.txt` — exact input/bundled-state record

## Validate

Focused V17.13.3 + regression checks:

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

See `VALIDATION_V17_13_3.md` for the exact results packaged with this release.


## Reader views

The reader shell links Radar, Matrix short/full, Risks & opportunities, Read at least this, and an alphabetical Literature used page.
