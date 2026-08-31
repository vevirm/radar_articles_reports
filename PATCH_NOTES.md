# R&I Radar v17.17.1

This is a complete upload-ready repository.

## Included fixes
- Keeps the v17.17.0 strict-recall changes: deeper search toward ~20 high-quality daily A/B findings and ~8 historical findings, without padding.
- Weak signals are proposition-level: an old topic can yield a new C signal when the new fact changes the interpretation of Strand A.
- C phrases are discovery/association aids, not standalone admission rules.
- Historical GitHub Actions no longer forces a 600-second minimum runtime.
- Institutional publication parsing no longer treats the first PDF link on a page as the publication itself.
- A linked PDF is used only when it strongly matches the page/document identity.
- Explicit publication dates outrank sitemap/update timestamps; dateModified is not treated as datePublished.
- Existing weak-signal records with broken source↔URL identity can be purged on a subsequent scan.
- Boilerplate extraction is not accepted as a substantive weak-signal proposition.
