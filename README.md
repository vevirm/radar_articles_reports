# R&I Geopolitics Radar — V17.6.5

This repository uses three deliberately separate layers:

- **A — EU R&I in geopolitical context.** Substantive evidence about European research or innovation where geopolitics, geoeconomics, economic security, strategic competition or international research relations materially affect the R&I system.
- **B — Futures methods for understanding A.** Publications that **develop, propose, adapt, extend or refine a futures/foresight method as such**. Merely using Delphi, modelling, forecasting, an early-warning system, scenarios or another method does not qualify.
- **C — Weak signals that may change how we see A.** Early, uncertain or surprising current developments linked back to A.

## B is intentionally narrow

A paper belongs in B only when the methodological contribution itself is the point of the publication. Domain-specific predictive systems and assessment tools are excluded unless the publication actually develops a futures/foresight method. For example, an earthquake early-warning model is not a foresight method; an explicit adaptation of horizon-scanning methodology can be.

Auxiliary techniques such as Delphi, system dynamics or agent-based modelling can qualify only when the publication develops them **as part of an explicit foresight/futures method**.

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
