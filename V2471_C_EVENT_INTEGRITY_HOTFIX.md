# v24.7.1 — Strand C event-integrity hotfix

This is a narrow repair on top of v24.7 European-system/source recall. It does not change
Strand A or Strand B admission and does not modify `radar.json` in the deployment package.

## What this fixes

- A sitemap `lastmod` timestamp may retrieve a page but can no longer establish the date of a
  public Strand-C event.
- Standing Horizon/funding/call/topic/application pages are rejected from C even when they
  contain launch/budget/proposal vocabulary.
- A previously watched proposal cannot be promoted to realised/committed status without an
  explicit source-backed realisation cue such as adoption, approval, signing, award or
  construction start.
- Direct European R&I changes involving quantum, semiconductors/chips, compute, research
  collaboration, defence/dual-use innovation, biotech and space can satisfy the internal C
  R&I-object test without requiring geopolitical wording.
- Curated national media can establish member-state scope for a hard, quantified or physical
  R&I-capacity move when a local-city headline omits the country name. Explicit foreign-location
  stories are not localised to the outlet's home country.
- `EU Digital Strategy` / `Shaping Europe’s digital future` are recognised as EU-official source
  aliases even when discovery arrives through a Google News URL.
- Saved external C rows whose old `what` field accidentally contains `Radar inference:` recover
  the source-backed proposition from `signal_note` before revalidation.

## One-time C cleanup

The patch introduces `c_event_integrity_profile_version = v24.7.1-c-event-integrity-hotfix`.
On the first scan after deployment, the normal weak-signal precision cleanup runs once against
saved Strand C. This does **not** trigger the A/B quality-profile migration.

Against the uploaded production `radar.json` from 10 September 2026, the local dry run keeps
5 of 10 current C rows and removes 5. The three REA standing/call pages are removed. The MERICS
LineShine signal is preserved by recovering its original source proposition rather than judging
its generated Radar-inference text.

## Regression examples

Positive C regressions include:

- EU-China research cooperation limited to targeted areas;
- six-month delay to EU quantum-tech regulation;
- Intel €5bn Leixlip next-generation-chip investment via The Irish Times;
- formal European Innovation Act proposal reported by EU Digital Strategy.

Negative C regressions include:

- REA INFRATECH standing call page;
- REA 'Reforming and enhancing the EU research and innovation system' standing call page;
- any candidate whose only event date is `sitemap_lastmod_approximate`.

## Tests

- targeted v24.7 + v24.7.1 tests: 46 passed;
- full pytest suite: 255 passed, 33 skipped;
- GitHub-workflow-style unittest discovery: 532 tests, all OK, 66 skipped.
