# V17.12 — reader-first intelligence display

- Reworked card hierarchy: message/idea first, bibliographic details second.
- Clicking a main claim now reveals the abstract/evidence text in place.
- Replaced clipped stored `core_message` fragments with complete evidence-backed propositions.
- Added reader-first rewrites for CRMA/Bulgaria and EU green-trade protectionism cases.
- Risks & Opportunities now shows specific source claims instead of generic quadrant boilerplate.
- Reduced visual density and limited the priority page to the strongest eight risks and opportunities by default.
- Added a display-language guard so non-English prose is not promoted as a headline; non-English bibliographic titles are suppressed while source metadata remains available.
- Replaced packaged `radar.json` with the user-supplied 26 Aug 2026 radar state.

### Repository hold-mode packaging
- Automatic scanning is paused for the current presentation-only phase.
- `.github/workflows/radar-scan.yml` now has `workflow_dispatch` only; `push` and `schedule` triggers are removed.
- `radar.json` remains at repository root and is not regenerated on upload.
- Legacy state-freezing tests were updated so future deliberate scans can evolve the corpus without making the pre-scan self-test fail.
