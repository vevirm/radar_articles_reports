# R&I Geopolitics Radar V17.13.0

V17.13.0 changes both **how the radar finds material** and **how a reader sees it**. The public evidence window remains a hard rolling **four calendar months**. A paper or report no longer has to say *geopolitics* explicitly: it may also qualify when genuine EU/European R&I is connected through a conservative, triangulated strategic mechanism such as technological dependence, capability competition, international coordination, research security, critical infrastructure, standard-setting/governance power, or research-talent competition.

This is not a looser relevance gate. The non-literal route needs at least **two independent strategic families**, including at least one relational/control family. A generic paper that merely says Europe should be more competitive still fails.

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

Each issue opens into branches and subissues. Current radar findings are attached underneath, so the professional mental map can stay stable while evidence changes scan by scan.

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

`frontier/quick/` is the **“just see it”** version: claims and counts only. `frontier/` keeps the fuller evidence, source links and classification detail.

Every admitted Strand-A finding is sent to the Matrix classifier. There is no extra hidden “dynamic” pre-filter before classification. The classifier can still leave a finding out when its evidence does not support a defensible row and direction.

### 3. Reader-first claims

Reader-facing prose is shorter and concrete. Bibliographic and source detail is preserved separately instead of being stuffed into the finding itself. The write boundary includes explicit handling for the e-hryvnia, cyber-governance, AI-for-science, CEPS technology-mapping and EU–India/open-hardware examples. Biographical material such as a researcher's training or job title is not used as the finding unless it is itself relevant evidence.

The same plain-language layer is used by the main radar, Matrix, Risks & opportunities and secondary briefing view.

## How discovery changed

### Literal “geopolitics” is not required

Strand A still requires all three things:

- direct EU/European relevance;
- substantive research, science, innovation, technology or related system evidence; and
- strategic context.

Strategic context can be explicit (geopolitics, economic security, strategic competition, etc.) or triangulated from multiple mechanisms. The triangulated route is intentionally fail-closed for one-cue cases.

### Existing findings help form later searches

A small `finding-context` lane turns recurring themes already present in Strand A into rotating scholarly searches. It does **not** auto-admit similar material. Search results return to the ordinary source, recency, EU/R&I and strategic-context gates.

This makes discovery iterative in a bounded way: the radar can learn where the live conversation is without turning yesterday's findings into tomorrow's admission rule.

### Researcher names are fallback attention

`priority_people.json` remains an auditable list of 137 researchers. Named-researcher discovery is not a separate corpus, badge or whitelist. In V17.13 it is mainly triggered when ordinary scholarly discovery is thin or Matrix coverage is very sparse. Exact-author works and any bounded context fallbacks still rejoin the normal OpenAlex/Crossref admission path.

### Strand C stays a minority

Weak signals no longer receive the protected follow-up query wave. After the A/B/C merge, Strand C is capped at **15% of all public findings**. This is a ceiling, not a quota: the scanner should not search merely to fill C.

## Four-month rule

`BOOTSTRAP_LOOKBACK_MONTHS = 4` is the public-window rule. Saved rows, recovery rows and matrix-only historical rows cannot widen it. On the bundled 28 August 2026 state the publication floor is therefore **2026-04-28**.

The bundled `radar.json` was produced from the newer uploaded state, then pruned to that exact floor and passed through the V17.13 reader-claim normalizer. **No fresh external discovery scan was run during packaging**, so the source state's `last_updated` timestamp is preserved.

## Scanner rotation

The existing OpenAlex, Crossref, journal/institutional, methods and matrix-gap rotations remain. V17.13 adds the finding-context queries to those bounded rotations. All query families obey the same date floor.

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
- `CHANGELOG_V17_13_0.md` — this release's changes
- `VALIDATION_V17_13_0.md` — validation record
- `CURRENT_CORPUS_INPUT.txt` — exact input/bundled-state record

## Validate

Focused V17.13 + regression checks:

```bash
PYTHONPATH=. python -m pytest -q \
  tests/test_v17_13_0_feedback_round.py \
  tests/test_v17_13_reader_scanner.py \
  tests/test_v17_12_5_plain_language.py \
  tests/test_v17_12_6_priority_people_rotation.py \
  tests/test_v17_12_7_integrated_researcher_attention.py \
  tests/test_v17_6_4_true_rotation.py \
  tests/test_v17_9_source_aware_matrix.py
```

See `VALIDATION_V17_13_0.md` for the exact results packaged with this release.
