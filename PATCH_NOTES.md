# R&I Radar v17.17.2

This is a complete upload-ready repository.

## Integrity repair
- Every public A/B/C record must now have a title/headline, a named source, a real http(s) source link, and a valid date.
- A record with a missing source link is rejected rather than displayed linkless.
- Configured institutional/news sources must point to their own host family, unless an external document URL clearly identifies the same document.
- Unconfigured third-party PDF links must still match the displayed document title; an unrelated cited PDF cannot become the record source.
- The source-integrity gate now runs on Strand C as well as A/B.
- The same integrity gate runs while loading saved radar.json, while merging a whole-repository upload with Git history, and while restoring older snapshots. Bad rows cannot be resurrected by upload recovery.
- The bundled radar.json was proactively cleaned: 5 A rows and 1 C row with incoherent source/link identity were removed.

## Date/document repair
- Sitemap `lastmod` is now a discovery/crawl hint only. It is never used as a publication date.
- Legacy records whose date was explicitly based on `sitemap_lastmod` are purged during saved-corpus cleanup.
- An ongoing webpage about a commissioned study (for example, a page saying the study “aims to”, is “collecting evidence”, or “will provide” outputs) is not labelled as a newly published research/policy paper unless it actually exposes a final report/findings.
- This removes the false-new Commission “Study to identify key strategic digital technologies for EU research and innovation funding beyond 2027” card that was dated from a 31 July webpage update.

## Whole-repository upload safety
- This package carries a one-run repository-bundle marker.
- After upload, the scanner unions the pre-upload Git snapshot with the package after applying the new integrity filters, instead of blindly restoring old corrupt rows or losing newer good rows.

## Existing radar behaviour retained
- Search continues toward roughly 20 strict new A/B findings without padding.
- Historical continuation targets roughly 8 strict findings.
- Weak signals remain relational to Strand A: an already-known topic can produce a new C item when the new fact genuinely changes the interpretation.
- C phrase rules are retrieval/association aids, never standalone admission rules.

## Validation
- 48 automated tests pass in the packaged repository.
