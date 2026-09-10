# v24.6 shadow validation

This validation separates three questions: whether the semantic gates behave, whether the saved corpus migrates safely, and whether the current C gate can admit real contemporary signals rather than merely rejecting noise.

## Test suite

- Curator + expanded v24.6 A/B/C gold/architecture tests: **82 passed**.
- Full repository suite: **209 passed, 33 skipped, 0 failed**.

The gold set includes the 12 curator-supplied YES/NO benchmarks plus additional C cases covering Horizon association, EU compute-capacity investment, research-security restrictions, international research-collaboration restrictions, EU budget decisions, foreign quantum product/deal noise, generic foreign data-centre expansion, archive pages, event landing pages, and operational procurement/tender documents.

## Saved-corpus dry migration

No production corpus file was mutated.

| Stage | A | B | C |
|---|---:|---:|---:|
| Bundled `radar.json` | 426 | 133 | 15 |
| After v24.6 A/B cleanup | 426 | 34 | 15 |
| After v24.6 C revalidation | 426 | 34 | 4 |

The B cleanup revalidates the saved B library once under the repaired method-object contract and removes **99 of 133** rows. This includes **94 of 105** rows in the known v24.5 flood window plus five older/null-timestamp application/homonym contaminants. Historical A is not globally replayed from concise saved summaries.

The four saved C rows that survive are:

1. Japan and EU sign off Horizon Europe association
2. Moves to cut FP10 budget ‘threaten Europe’s competitiveness’
3. Europe commits €5 billion to fund seven AI megafactories and catch up with the US and China
4. US politicians push agencies to restrict research collaboration with China

Rows revalidated out of C are archived as `quality_revalidated_out`, not silently destroyed.

## Current-signal shadow sample

The real scanner entry point was also launched in an isolated repository copy with the quick-scan profile and a 120-second budget. Before any discovery, the actual orchestration path performed the intended migrations: **A 426 / B 133 / C 15 -> A 426 / B 34 / C 4**. The packaging runtime then stalled in an outbound network operation and was killed by the outer sandbox timeout; it never wrote the shadow `radar.json`, so no production corpus was touched. This is an environment/network limitation of the local packaging run, not evidence that the semantic gates failed.

To test current C admission independently of that collector limitation, fresh 2026-09-08--10 news examples were replayed through the exact local `anchor_news` gate. It accepted: Google's large AI-infrastructure investment in Finland; Mistral's large European AI funding round; and the Germany-UAE technology-collaboration package involving researchers/investors. It rejected a generic global AI-financial-stability story with no Europe/R&I materiality channel, and also rejected a minor ENISA model-access item because it did not satisfy the concrete-event/specific-analysis rule.

The expanded controls continue to reject foreign vendor/product announcements, ordinary enterprise quantum deals, generic foreign data centres, archive/index pages, event pages, and operational tenders.

## Release boundary

The final publication envelope remains **up to 8 A / 1 B / 3 C new rows per scan** after substantive gates and novelty checks. A short lane stays short. No quota can rescue a failed candidate or consume another lane's unused capacity.
