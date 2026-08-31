# R&I Radar v17.17.4

This is a complete upload-ready repository.

## Source-family rotation: EU/institutions and journals both get real scan time
- Ordinary discovery now starts institutional/EU crawling in parallel with OpenAlex and Crossref instead of making institutional sources wait behind scholarly endpoints.
- EU/public-institution and journal families keep independent persisted cursors, so repeated runs move through each family rather than restarting at the same sources.
- The EU lane retains a protected official-EU slice while also rotating through broader high-quality institutions.
- The journal lane retains both preferred high-merit journals and a protected broad-journal share; preferred titles cannot consume the entire scholarly source rotation.
- These are search-allocation guarantees only. No source family has an output quota and source prestige never bypasses the substantive A/B/C gates.

## Topic rotation: the executed search prefix is diversified
- The main Strand-A scholarly query bank is now interleaved by coarse topic family before its persisted cursor is applied.
- Matrix-gap, finding-context, futures-method and exploratory query lanes are interleaved into the executed query prefix rather than appended at the end where a time-limited run might never reach them.
- Matrix specialist institutional sources continue to rotate by sparse-cell/theme with their own saved cursors.
- Result: repeated scans should move across both source families and R&I-geopolitics topics instead of repeatedly spending the budget on whichever endpoint/topic happened to come first.

## Matrix / “Read at least this” / Risks & Opportunities now use evidence quality in ranking
- Substantive admission remains first. Source merit can never make an otherwise irrelevant item qualify.
- After an item qualifies, the same source-merit rubric documented under Stuff -> Technical evidence materially affects how high it appears.
- The rubric is the existing 100-point evidence score: source authority + EU/R&I relevance + evidence strength + author transparency, with the existing Highest / Very strong / Strong / Useful / Supporting bands.
- The 4x4 Matrix now orders already-qualified findings using both finding strength and source merit, so stronger evidence normally appears higher within a cell.
- “Read at least this” now gives source merit more weight when choosing the best-supported items behind each issue while still requiring issue relevance.
- Risks & Opportunities still preserve substantive risk severity / opportunity relevance first, then use finding strength plus source merit to rank evidence within those categories.
- The page text has been updated so this quality-aware ordering is visible rather than hidden.

## Strand-C and integrity rules retained
- C remains a genuine weak-signal/reframing layer, not a feed of established EU programmes, offices or routine institutional activity.
- “European AI Office” and similar standing official activity cannot enter C merely because it is recent and relevant.
- Every published A/B/C item still needs a coherent title/source/link/date; unrelated cited PDFs and update/sitemap dates cannot masquerade as the source publication.
- Git-history recovery applies the same integrity and C-quality filters.

## Recall targets retained
- Search continues toward roughly 20 strict new A/B findings without padding.
- Historical continuation targets roughly 8 strict findings.
- Topic/source rotation changes where the scanner spends effort, not what is allowed through the evidence gates.

## Validation
- 39 main-scanner regression tests + 20 historical-scanner tests pass: 59/59 total.
- Additional Node sanity checks confirm that, for otherwise equivalent qualified findings, higher source-merit evidence ranks above lower-merit evidence on the Matrix and Risks/Opportunities surfaces.

---

# R&I Radar v17.17.3

This is a complete upload-ready repository.

## Strand C correction: weak signals are not routine EU institutional activity
- Strand C is now explicitly a weak-signal / reframing layer, not a second feed of Commission, agency or institutional pages.
- Established EU offices, programmes, strategies, services, standing initiatives, mature implementation notices, formal grant results and similar systematic public activity cannot enter C simply because they are recent or strategically relevant.
- EU-official material gets first claim on Strand A/B. If it passes the substantive A/B gate it appears there; otherwise it is omitted.
- EU-official material can enter C only when it is genuinely provisional, experimental or uncertain (for example a draft, consultation, proposal, pilot, trial, delay, pause, exception, waiver or opt-out) and it still has to reframe a substantive Strand-A issue.
- Institutional C candidates now need a real current change/finding in the headline or lead. Static overview/activity/event pages do not qualify because strategic words appear somewhere in the body.
- The exact regression case “European AI Office” is tested: it cannot enter C; when the normal A gate passes it is labelled as an official policy / institutional framework in A.
- Mature official items such as EIC investment-guideline updates and routine ERC grant-result announcements can no longer survive as C.
- Git-history recovery applies the same C-quality rule, so old institutional-as-C rows cannot be resurrected after a whole-repository upload.

## Bundled corpus cleanup
- The bundled Strand C corpus was revalidated under this rule.
- 6 old institutional/routine C rows were removed (including EIC/ ERC and generic ITU activity/event pages).
- The bundle now contains 228 A, 24 B and 2 retained C records before the next live scan/history merge.
- The first post-upload scan repeats the new C migration after merging any larger valid pre-upload snapshot from Git history.

## Earlier integrity/date repairs retained
- Every public A/B/C record must have a coherent title/headline, source, real http(s) source link and valid publication date.
- Unrelated cited PDFs cannot become another document's source link.
- Sitemap `lastmod` / webpage update time is never treated as publication date.
- Ongoing commissioned-study/project pages are not mislabelled as newly published research papers.

## Recall targets retained
- Search continues toward roughly 20 strict new A/B findings without padding.
- Historical continuation targets roughly 8 strict findings.
- C phrase rules remain retrieval/association aids only; they never admit a weak signal by themselves.
- Topic repetition is allowed in C only when the new fact changes the interpretation of an existing Strand-A issue.

## Validation
- 34 main-scanner regression tests + 20 historical-scanner tests pass: 54/54 total.
