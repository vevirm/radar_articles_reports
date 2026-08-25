# R&I Geopolitics Radar V17.9.0

V17.9.0 repairs three linked problems in the radar: literal claim boilerplate, source-blind admission rules, and an under-populated Sovereignty Frontier matrix.

## What changed

### Informative claims, not “This says that”

Prominent radar and matrix lines now show the source-backed claim itself. `core_message` remains concise, but the UI no longer mechanically prefixes it with “This says that” or “It says”. Publication details remain available as bibliography/source metadata.

### Source-aware aboutness

The substantive pass-1 standard remains strict: a record must connect Europe/EU, an R&I dimension, and geopolitical context. The aboutness test now adapts to the text actually available:

- **Full text:** recurrence and spread across the document are valid evidence that the issue is central.
- **Abstract only:** the EU/R&I/geopolitical connection is judged inside the abstract; nonexistent document sections are not required.
- **Metadata only:** the record is **deferred / insufficient text**, not falsely labelled irrelevant. For DOI-bearing OpenAlex and Crossref records, the scanner makes a tightly bounded publisher-landing-page abstract recovery attempt before dropping the candidate.

The bare acronym `EU` is also contextual. If a paper explicitly defines `EU` as something else (for example “environmental uncertainty”), that token cannot establish European Union relevance.

### Honest rejection diagnostics

Admission diagnostics now preserve the actual failure cause—such as insufficient text, no direct EU relevance, no R&I content, no geopolitical context, or insufficient aboutness—instead of collapsing failed pass-1 candidates into “no direct EU”.

### Evidence-led 4×4 matrix

Core reports/papers are classified from the source-backed evidence carried in the radar record, not only from the shortened display point. Direction words are supporting evidence, not a second hard gate. Weak signals remain event/mechanism-gated.

On the bundled 2026-08-25 state, the repaired classifier identifies 69 qualifying matrix evidence items and populates all 16 cells. Counts are not artificially balanced; cells range from sparse to dense according to the evidence.

## Bundled state

This package uses the user's newer supplied `radar (20).json` state (`last_updated: 2026-08-25T01:54Z`) rather than the older state inside the previous ZIP. Two confirmed scope false positives were removed during the repair:

1. an Indonesia-centred defence-policy paper where EU strategic autonomy was only a comparator; and
2. a China construction paper where `EU` meant “environmental uncertainty”, not European Union.

The preserved data timestamp is the time of the supplied scan. V17.9.0 is a code/classifier/state-cleanup release, not a claim that a new live web scan was run during packaging.

## Run

Open `index.html` through a local/static web server as before. The scan implementation is in `scripts/scan_radar.py`; configuration is in `radar_config.json`, with the supplied design specification retained as `eu_ri_radar_config_v2.yaml`.

## Validation

Run:

```bash
pytest -q
```

The package includes regression tests for source-aware aboutness, contextual EU acronym handling, rejection diagnostics, informative claim rendering, and matrix coverage.
