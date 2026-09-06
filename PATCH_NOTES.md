# Fresh-start overlay patch

This build adds a visible root-level `FRESH_START` declaration.

It is designed for the exact GitHub browser-upload situation where old files remain in the repository because upload overlays rather than deletes them.

- `radar.json` still contains the strict one-use `fresh_repository_seed` marker and the curated 200-item A+B baseline.
- The scanner detects that seed and ignores older Git `radar.json` history on the first run.
- The workflow uses `FRESH_START` to run only the maintained scanner/security suites.
- Same-path quarantine replacements are included for legacy `tests/test_v*.py` files, so even an old workflow that still runs `test_*.py` cannot make old archive/version/history assumptions block the fresh start.
- The scanner's write/security boundary is unchanged: the main scanner may persist only `radar.json`.
- After the first successful scan, the JSON fresh-seed marker disappears and scanning proceeds incrementally from that run onward.
