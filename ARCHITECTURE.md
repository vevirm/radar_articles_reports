# Scanner architecture — V16

The radar is a zero-configuration Python scanner run by GitHub Actions every 12 hours.

## A/B discovery

OpenAlex and Crossref provide broad scholarly discovery, while a direct institutional crawler checks configured policy/research organisations. Candidate documents are deduplicated and passed through the balanced Strand A/B gates in `scripts/scan_radar.py`.

The initial/source-expansion A/B run can look back four calendar months. Later runs use a 14-day overlap. Accepted A/B items are merged into the existing cumulative `radar.json` and never disappear merely because they fall outside a later scan window.

## C weak-signal discovery

V16 starts weak-signal discovery **in parallel with OpenAlex and Crossref at the beginning of the run**. This prevents long A/B backfills from consuming the entire runtime budget before Strand C begins.

Discovery uses Google News RSS as a public transport layer across a curated set of major publishers/official sources plus cross-source topic queries. No user API key is required.

A candidate weak signal must be a factual event/change and pass a balanced R&I/geopolitics gate. It can connect to:

1. a specific accepted A/B publication;
2. a recurring A/B theme; or
3. a curated strategic watch theme.

The third route is intentionally available so sparse A/B evidence cannot suppress strong current signals. It still requires the full Strand-C relevance gate.

V16 performs a one-time 30-day C recovery scan, then uses a seven-day rolling window every 12 hours. Accepted C items are cumulative and deduplicated.

## Output and UI

`radar.json` is the authoritative cumulative state. The scanner writes it atomically. `/briefing/` reads that file directly and presents weak signals in a `WHAT CHANGED` / `WHY IT MATTERS FOR EU R&I` format, with research evidence available as a separate view.
