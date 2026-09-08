# Reader design contract — v25

This contract governs presentation only. The scanner, admission rules, scoring, corpus, update cycle, schedules, historical scanner and snowballing are outside its scope.

## Three weights

1. **Stuff — workbooks and checking material.** Full technical volume lives here.
2. **Radar — what and why.** Publication-level evidence belongs here. Each record gives the source, what it says and why it matters.
3. **Reader views — light conclusions.** Trends and counter-trends, Ongoing phenomena, Matrix, Risks and opportunities, External shocks, Topics and the quick read show conclusions drawn from the Radar rather than repeating it.

## Every page must explain itself

Invented product names stay. Directly under the page name, the page gives:

- the reader's question;
- one or two sentences saying what qualifies for that view;
- the findings.

The method can remain closed. The reading cannot. A reader must know what a number is a number of and what a page category means without seeing weights, formulas or admission internals.

## One map everywhere

The full site map is available from every page. Desktop uses the same complete side map. Small screens use the same complete map in a drawer behind one Menu button. Menu labels are names only; explanations live on their pages.

## Live scale

Reader pages show the size and freshness of the instrument at reading size: records, new items, sources and last scan. Internal scanner scores and statuses stay hidden.

Historical evidence uses the same fact-strip shape as the live Radar, but reads from its own corpus and scan.

## Type, spacing and weight ladders

Nothing sizes itself independently.

### Type — five roles

1. page name
2. section heading / navigation block
3. claim
4. reading text
5. labels, dates and counts

Role 5 never goes below 14px.

### Spacing

All gaps, margins and padding come from a small shared spacing ladder.

### Weight

Rules and borders use three levels only: hairline, structural and emphatic.

Square corners are the default. Black, white and `#c40018` red are the visual system.

## Radar

Radar carries the most reader-facing text. Search and filters stay prominent. Publication cards keep source/date, title, WHAT, WHY and access to the publication. Technical detail can stay behind disclosure.

## Light pages

Light does not mean unexplained. A light page contains only what it cannot be understood without: its name, question, qualification sentence(s), live fact strip and findings.

Trend balance numbers are explicitly labelled **Evidence pull** and are not probabilities.

## Homepage

The homepage states what the instrument is, shows live scale, exposes the complete map and keeps the live topic index. It is not constrained to one viewport.

## Mobile

- Complete navigation lives in one drawer.
- Matrix column meaning is repeated at cell level when columns collapse.
- Long pages keep a Top control.
- No reader-facing label, date or count is shrunk below 14px to make a layout fit.

## Protected boundary

Presentation work must not alter `radar.json`, `historical/historical.json`, scanner scripts, scanner configuration, admission logic, workflow schedules, scan state, citation-snowball state or tests intended to protect scanner behavior.
