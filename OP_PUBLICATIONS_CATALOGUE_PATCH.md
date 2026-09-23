# EU Publications Office / Cellar catalogue discovery patch

## Why this patch exists

`op.europa.eu` publication-detail records are catalogue entries, not ordinary article pages. The previous scanner mostly discovered institutional material by walking sitemaps and a few publication hubs. That can miss highly relevant EU Publications Office reports that exist in the catalogue but are not linked from those hub neighborhoods.

Two motivating records:

- `https://op.europa.eu/en/publication-detail/-/publication/6c154d71-d7d0-11f0-8da2-01aa75ed71a1/language-en` — *The demographic turn: Actions needed for research, innovation and policy in Europe*.
- `https://op.europa.eu/en/publication-detail/-/publication/52028928-482a-11f1-8095-01aa75ed71a1/language-en` — *The futures of artificial intelligence: Implications for Europe’s R&I ecosystem. Part 5, Final report*.

## What changed

1. **Cellar catalogue discovery.** For the Publications Office source, the scanner queries the official Cellar SPARQL endpoint for recent English works matching broad R&I, technology, foresight, capability, competitiveness, talent and strategic-autonomy themes. Cellar work UUIDs are converted to normal human-facing `op.europa.eu/.../publication/<uuid>/language-en` pages and then go through the existing institutional parser and A/B admission gate.

2. **Exact OP release dates.** Publication-detail pages now read the explicit `Released on EU publications website: YYYY-MM-DD` field before weaker date fallbacks. Cellar `work_date_document` metadata is retained as first-party date evidence for catalogue-discovered records.

3. **Full-document scanning.** Once an OP record is reached, the existing OP download-handler fallback remains available, and a second official route now fetches the English PDF directly from Cellar with `Accept: application/pdf` and `Accept-Language: eng`. The report text is run through the same substantive relevance gate as other institutional PDFs.

4. **429 / JS-page resilience.** If the OP landing page is throttled, non-HTML, or unusable, the scanner can still read the publication from Cellar while retaining the reader-friendly OP publication-detail URL as the public source link.

5. **Exact UUID identity.** A landing page, OP download-handler URL and Cellar resource carrying the same publication UUID are treated as the same document. This allows safe full-PDF reading even for very short titles such as *The demographic turn*, which would otherwise fail the generic two-title-token attachment check.

6. **Narrow Strand A foresight-report recognition.** Completed Tier-1/2 institutional foresight/scenario analyses can now satisfy the evidence-led Strand A route when they also contain a recognised R&I-system mechanism and pass the existing European-scope, aboutness and centrality checks. This is not a generic future/scenario waiver. Strand B remains methods-only.

7. **OP subtitle preservation and R&I punctuation normalisation.** The parser carries substantive publication subtitles into relevance analysis and recognises institutional wording such as `research, innovation and policy` as the explicit research+innovation pair. This is important for terse series titles whose actual R&I subject is expressed below the H1.

## Configuration added

The new settings are in `radar_config.json`:

- `op_publications_catalogue_enabled`
- `op_publications_catalogue_lookback_months`
- `op_publications_catalogue_max_pages`
- `op_publications_catalogue_terms_per_query`
- `op_publications_catalogue_results_per_query`
- `op_publications_catalogue_timeout_seconds`
- `op_publications_catalogue_title_terms`

The catalogue lookback is currently 6 months, matching the repository's extended top-quality active window. As of 23 September 2026, the May 2026 AI report is inside that window. The December 2025 demographic report is outside the current active six-month publication window; it is a motivating example of the page/report class and would have been discoverable while current. This patch deliberately does not silently widen the repository's retention/admission window.

## Files changed

- `scripts/scan_radar.py`
- `scripts/scan_radar_deep_a.py`
- `radar_config.json`
- `tests/test_op_publications_catalogue.py` (new)

## Validation

- Python compilation succeeds for both scanner entry points.
- `radar_config.json` parses successfully.
- OP/source-path focused regression suite: **61/61 tests passed**.
- Admission/relevance regression suites covering the current A/B/C gate family: **217/217 tests passed**.
- A repository-wide run was exercised as well, but long-running end-to-end state/reasoning tests exceeded the execution ceiling. No full-suite pass is claimed.

The OP-specific tests cover exact release-date parsing, subtitle extraction, Cellar SPARQL discovery, catalogue discovery when editorial hubs are empty, detail/download/Cellar UUID translation, documented English-PDF content negotiation, throttled-page fallback, preservation of the human-facing OP source URL, positive admission of both motivating report patterns into Strand A, and a negative generic-scenario control that remains rejected.
