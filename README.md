# R&I Geopolitics Radar — V17.6.0 A/B/C redesign

This repository scans a cumulative evidence base using three deliberately different layers:

- **A — EU R&I in geopolitical context.** Papers and analytical reports in which European research/innovation and geopolitical, geoeconomic or economic-security dynamics are substantively connected.
- **B — Methods for understanding the future of A.** Methodological contributions for horizon scanning, foresight, weak-signal detection, scenario construction, Delphi, roadmapping, anticipatory analysis and related approaches. The method must be a contribution, not merely something used in an unrelated study.
- **C — Weak signals that may change how we see A.** Early, uncertain or surprising current developments. Every C item must connect back to Strand-A evidence; B methods and free-floating watch themes cannot justify C admission.

## Key separation

A is the substantive evidence layer. B is a methods library. C is the changing-current-context layer. The Sovereignty Frontier is therefore built from **A + C**, not B. Methods never fill geopolitical matrix cells.

## Scanning and rotation

The scanner preserves independent persistent cursors for OpenAlex, Crossref broad search, priority journals, institutions, the dedicated B-method lane, frontier gap queries, specialist gap sources and result-depth pages. A quality-profile change does not reset these source/query/page rotations.

Sparse Frontier cells can receive extra discovery effort, but they do not redefine admission: a paper must still pass A, and a method must still pass B.

## Precision rules

Funding acknowledgements do not create A relevance. Bare technology or generic education/administration does not create R&I relevance. B rejects application studies that merely say “we conducted a Delphi study” or “we use scenarios.” C rejects mature headline news and collapses near-duplicate coverage of the same event.

## Running

Upload the repository to GitHub and run the existing **Radar Scan** workflow. No secrets are required for the keyless scholarly discovery path. The bundled `radar.json` preserves the supplied live rotation cursors while cleaning the stored A/B/C corpus under the V17.6.0 model.

Run tests locally with:

```bash
python -m unittest discover -s tests -v
```
