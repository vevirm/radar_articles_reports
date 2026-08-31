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
