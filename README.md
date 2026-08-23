# R&I Geopolitics Radar — V17.7.2

This repository uses three deliberately separate layers:

- **A — EU R&I in geopolitical context.** Substantive European R&I evidence with either explicit geopolitics/economic-security framing or a bounded external-position mechanism (for example foreign dependence/comparison plus a capacity, competitiveness, talent, access or scale outcome).
- **B — Futures methods for understanding A.** Publications that develop/adapt/extend/refine a futures/foresight or forward-looking R&I method. Method-first papers can also qualify when validation/benchmark/transfer evidence shows the reusable method is itself the contribution. Mere application does not qualify.
- **C — Weak signals that may change how we see A.** Early/uncertain developments **and new evidence or indicators** that can confirm, contradict or complicate the Strand-A picture, always linked back to A.

## B is selective, but no longer literal-label narrow

A paper belongs in B only when the methodological contribution itself is the point of the publication. The original explicit foresight route remains. V17.7 also admits a second route for newly developed methods that are visibly forward-looking and designed to detect, map or forecast change in R&I/science/technology systems (for example emerging-technology detection, research-front detection, bibliometric/scientometric forecasting, patent analytics, technology mapping or trajectory methods).

Generic method use, descriptive bibliometrics, ordinary Delphi applications and domain prediction/early-warning systems still fail. Auxiliary techniques such as Delphi, system dynamics or agent-based modelling still need explicit futures framing.

## Display

The main radar is message-first:

1. a core message of at most 120 characters;
2. **From:** source and date;
3. **Why it matters:** in short, simple language;
4. bibliographic/source details.

Paper titles are therefore not used as the main card headline.

The **Risks & opportunities** page has a Go back control and states risks/opportunities in plain language. Detailed evidence remains underneath each statement.

## Rotation

The scanner keeps independent persistent cursors for OpenAlex, Crossref broad search, priority journals, institutions, the dedicated B-method lane, Frontier gap queries, specialist gap sources and result-depth pages. A quality-profile migration does not reset these rotations.

## Running

Run the existing **Radar Scan** GitHub Actions workflow. The keyless scholarly path requires no secrets.

Local tests:

```bash
python -m unittest discover -s tests -v
```

- Main messages also repair PDF/OCR letter-spacing artefacts (for example `E u r o p e` → `Europe`) before display.
- Letter-spaced text is never accepted as a 120-character core message.


## V17.6.4 rotation behavior

Each scan now has two scholarly lanes: a recent-publication lane and a persisted full-corpus exploration lane. The exploration lane rotates across diversified topics and separate historical depth pages. A quiet first slice can trigger a small second-slice rescue when runtime remains. The main radar displays the topics explored in the last run.


## V17.6.5 rotation-rescue fix

- Fixes false scholarly-stage failure detection after institutional scanning.
- A quiet run now performs its next historical-slice rescue when at least one scholarly source actually completed and sufficient runtime remains.
- Persistent source, topic, and depth cursors are preserved; the supplied current `radar.json` is carried forward unchanged as the starting state.


## V17.7.1 executed-rotation + wider-recall repair

V17.7.1 additionally makes rotation execution-aware: queued queries skipped by source time slices no longer consume cursor positions, stage-budget endings are not treated as source failures, quiet scholarly rescue runs before the institutional stage, and a bounded DOI metadata fallback can recover missing Crossref abstracts. Historical exploration is modestly wider, while the live corpus horizon is intentionally unchanged.

- Strand C no longer requires every candidate to contain an early-stage word such as `pilot`, `draft`, `proposal` or `delay`. Curated-source reports, studies, surveys and data can qualify when they contain a real finding/indicator, remain tightly R&I/geopolitics relevant, and anchor to Strand A.
- A tightly guarded derived-Europe route allows global/comparative empirical evidence to update A; ordinary foreign technology launches still fail.
- Strand B gains the R&I-futures analytic-method route described above. The method must be newly developed/adapted/etc.; descriptive or merely applied methods still fail.
- The method query lane is wider (8 rotating queries per scan), evidence/reframing news queries were added, and the news worker pool was increased.
- The supplied current `radar.json` is bundled exactly as the starting state. A/B and C quality-profile versions are deliberately unchanged, so this recall expansion does **not** trigger a cleanup audit. The changed signal-discovery version triggers one 30-day C recovery pass, then returns to the normal seven-day window.
- `scan_results` now records prefilter C candidates, anchored C candidates and B-method queries used, making future “too strict / too noisy” tuning easier to diagnose.


## V17.7.2 zero-scan repair

V17.7.2 separates accepted-corpus persistence from rejection/search persistence. A one-time `recall_profile_version` migration reopens the four-month discovery universe, clears previously rejected institutional fingerprints and resets scholarly/query depth progress without deleting accepted A/B/C items. Crossref also gains a rotating source-first sweep of priority journals, so high-quality journal coverage no longer depends entirely on pre-written topic queries. Strand A gains the bounded external-position evidence route described above, and Strand B can accept method-first contribution papers without requiring a literal “we develop” sentence. `stats.admission_diagnostics` shows where future zero scans are being rejected.


## V17.7.2 source-first recall

V17.7.2 responds to the observed degraded zero-result run. It adds a bounded source-first recent-contents sweep across rotating priority journals, a contextual Strand-A route for direct European R&I external-position evidence that does not need literal geopolitical vocabulary, and explicit admission diagnostics. Anonymous API pacing is more conservative (OpenAlex one worker / 1.0 s minimum interval; Crossref 1.2 s minimum interval), while Crossref uses bounded cooldown retries on 429 responses. Ambiguous “scenario construction/building/development” language now needs an independent futures/strategic cue, preventing classroom or simulation “scenario” papers from entering Strand B.

The bundled `radar.json` is the user-supplied 2026-08-23T17:42Z state byte-for-byte. No accepted A/B/C item is deleted by this patch.
