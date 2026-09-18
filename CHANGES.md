# Creative reserve and future-oriented generation rules

- Every product page fills 15 slots (3 per wow 1-5); a thin wow level borrows from the nearest level. Pages now keep the published order instead of re-bucketing (the shock page was dropping ~6 items).
- New records never take a slot automatically: they update candidate reasoning, and the shelf is re-decided each scan (swap margin 4 maturity points).
- Reserve = grounded runners-up + **creative reserve**: at least 18 (topped up toward 45 per category) relevant, uncontradicted hypotheses that are distant, cross-domain, emerging, weak-signal or partially grounded, rotated across wow levels with weight on surprise. They mature into page competition when grounded.
- Generation: domain-family and vocabulary-cluster scopes for trends and ongoing phenomena; external actors count as constraining pressure on European trends; reviewed Deep Scan/backfill primary tags count as grounding; curated topic phrasings; shock drivers prefer statements that visibly show the disruption; broader research-security wording.
- Context rows are never primary evidence (R-09 fix).

# v25.1 evidence-linked reader and discovery feedback

Conservative analytical/readability upgrade on top of the Deep Scan authoritative repository.

## What changed

- Preserved the manual Deep Scan worker-package → external LLM → manual `deep_scan_inbox/` → import workflow unchanged.
- Passed Deep Scan V2 semantics can now be the explicit provenance of regenerated strategic-pathway classifications instead of being relabelled as scanner source text.
- Risks and opportunities use pathway components before broad article text when choosing reader wording, preventing unrelated words such as “materials” or “investment” elsewhere in a source from selecting the wrong canned risk.
- Reader deduplication now consolidates a clear shared mechanism + exposed asset, while preserving distinct mechanisms and retaining every supporting source under Evidence. Identical visible wording is never repeated as separate cards.
- Higher-order Risks/Opportunities expose their reasoning roles, source links and counter-evidence/falsifier status under the existing Evidence disclosure.
- External Shocks keep the same compact list but now expose the reasoning chain, why the shock is easy to miss, source links, conditions, counter-evidence/absorbers and watch points under an optional Evidence & reasoning disclosure.
- Current risks/opportunities and dynamic shocks contribute bounded support-and-challenge searches to the existing finding-context discovery lane. The total query budget is unchanged and normal admission/Deep Scan rules still apply.
- Added regression tests for semantic reader consolidation, Deep Scan semantic provenance, and balanced support/falsifier discovery feedback.

## Protected behavior

No inference grammar, qualification threshold, evidence weight, denial test, Deep Scan queue/inbox workflow, scanner schedule or core visual system was simplified or replaced. Radar/record-level evidence remains uncollapsed.

# Professional visual system v27

Presentation-only rebuild based on the supplied professional-page manual.

## What changed

- Consolidated all 17 reader pages onto one stylesheet: `radar.css?v=27`.
- One shared persistent navigation shell (`site-shell.js`) on every page, including Radar and shock variants.
- Menu remains visible; current page and site brand use solid red blocks.
- Black/white is the default field; red is reserved for location, weak signals, risks, counter-trend quantity, filled Matrix evidence, and primary tree nodes.
- Reduced typography to six reader-facing sizes and three weights (400 / 600 / 800). Menu stays 600 per the latest design instruction.
- Reading text is capped to a 680px measure; metadata is separated by position rather than bolding.
- All margins and padding use the 4 / 8 / 16 / 24 / 40 / 64 / 96 spacing ladder. The only raw grid gap remaining is a 1px rule effect.
- Radar remains dense; conclusion pages use larger grouping gaps.
- Radar rows use a provenance column plus a reading column. Strand C weak signals carry red semantic markers; A/B remain black/white.
- Render-only Radar cleanup removes `Download` / `PDF` title noise, removes repeated What/Why labels, suppresses a What sentence when it merely restates the title, and uses quiet `Evidence`, `Source`, `Details` actions.
- Risks & Opportunities no longer inject the same generic consequence sentence on every card; a second sentence is shown only when evidence yields a specific one.
- Trend cards suppress duplicated title/explanation text and use black/red split bars for the two evidence pulls.
- Duplicate reader-path strips are hidden because the persistent menu already supplies navigation.
- Read At Least This is built as three-column box trees with a red root node, white child nodes, grey 1px connectors, auto-growing boxes, and no fixed-height clipping.
- Human-readable dates are used in Trends, Matrix state, and shock-variant evidence metadata.
- Earlier Findings is progressively disclosed rather than rendering the whole corpus at once.
- Topics, Glossary, Sources and Matrix presentation are normalized to the same type, spacing and colour system.

## Verification

- HTML pages: 17
- Pages linking `radar.css?v=27`: 17
- Other stylesheet links: 0
- `!important` in `radar.css`: 0
- Inline `<style>` blocks: 0
- Inline `style=` attributes: 0
- Font weights in `radar.css`: 400, 600, 800 only
- Hex colours in `radar.css`: `#111111`, `#6b6b6b`, `#c40018`, `#d9d9d9`, `#ffffff` only
- Reader-facing explicit font sizes below 14px: 0
- Red border/stroke/outline rules: 0
- Raw margin/padding pixel values outside the spacing tokens: 0
- Full repository regression suite: 168 tests, 0 failures (66 skipped legacy checks)

## Safety boundary

This upload contains presentation files only. It does not contain scanner code, Radar/History JSON, configuration, workflow files, scan state or tests.

The protected inline Radar application contract remains unchanged; the copy cleanup is performed by the presentation shell after render.
