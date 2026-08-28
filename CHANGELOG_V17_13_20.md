# V17.13.20 — source merit across the radar

- The source-merit logic behind `stuff/source_merit_ranking.xlsx` is now a shared reader layer across the principal radar pages.
- Every main Radar finding and weak signal shows a plain evidence-weight label: **Highest**, **Very strong**, **Strong**, **Useful**, or **Supporting**.
- `Read at least this` uses source merit after issue relevance when choosing the small set of current evidence shown under each issue.
- Matrix · short groups repeated findings as before, but stronger supporting sources are shown first and each bullet shows the combined evidence weight of its source group.
- Matrix · full shows evidence weight on takeaways, signal details and cell evidence. Source merit may break display-order ties, but it does **not** move a finding between Matrix cells.
- Risks & opportunities now uses source merit as a meaningful secondary factor in priority ordering after the Matrix risk/opportunity structure. A weak source therefore carries less decision weight than a strong source when the underlying signals are otherwise comparable.
- The Evidence browser sorts evidence within each topic by source merit and shows the same labels.
- Literature used remains alphabetical for lookup, but every source now shows its evidence weight.
- Stuff's live publication preview is ordered by the same source-merit rules as the workbook.
- The source-merit layer is a reader/priority weighting layer only. It does not change scanner admission, source discovery, source rotation, the A/B/C corpus, Matrix cell classification, or the six-hour scan schedule.
- V17.13.19 security limits and credential separation remain unchanged.
