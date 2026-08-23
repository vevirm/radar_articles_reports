# V17.7.1 — executed rotation + wider recall, without corpus loss

This patch builds on V17.7.0's wider weak-signal and R&I-futures-method recall. It addresses the remaining structural reasons a broad search universe could still produce artificially quiet scans.

## What was actually wrong

The supplied state shows a very wide configured universe: 125 Strand-A scholarly queries, 41 priority journals, 60 institutional sources, 30 weak-signal news sources and a persistent historical exploration lane. Repeatedly tiny yields therefore cannot be explained by topic scarcity alone.

The important execution defects were:

1. rotation cursors were advanced when a batch was planned, before the scanner knew which queued queries actually made a request;
2. a normal per-stage `budget reached` warning was treated as a source failure, poisoning cycle state and potentially suppressing rescue;
3. quiet-scan scholarly rescue ran only after the institutional stage, so it could miss its minimum remaining-time threshold;
4. Crossref records without abstracts were judged mostly from their titles even when a DOI publisher page exposed usable abstract metadata;
5. the full-corpus exploration and B-method lanes were still somewhat thin relative to the size of the query bank.

## V17.7.1 changes

### Execution-aware rotation

OpenAlex, Crossref broad, Crossref priority and institutional source cursors now advance only across contiguous planned work that actually started a network request. Queued work skipped by a stage deadline remains pending for the next scan. The scanner prefers harmless repetition over silent query loss.

The output now records planned-versus-executed counts, including:

- `openalex_queries_executed`
- `openalex_base_queries_executed`
- `crossref_broad_queries_executed`
- `crossref_base_queries_executed`
- `crossref_priority_tasks_executed`
- `institution_rotating_sources_executed`
- exploration executed counts
- B-method executed count

### Stage-budget semantics

A normal stage time slice ending is no longer classified as an OpenAlex/Crossref/institution source failure. Fatal stage errors and unavailable public endpoints still are failures.

### Rescue moved earlier

If OpenAlex + Crossref admit no new scholarly candidate, the quiet-scan rescue now runs immediately after the parallel scholarly/news phase and before institutional scanning. This preserves a meaningful opportunity to search a second historical topic/depth slice.

### Missing Crossref abstracts

For a bounded number of otherwise eligible Crossref records with no abstract, the scanner now follows the DOI and attempts to recover publisher abstract/description metadata before the A/B admission gate. It is capped at 18 attempts per scan and two per Crossref search task, so this cannot become an uncontrolled crawl.

### Slightly wider exploration

- OpenAlex historical exploration: 10 -> 12 queries/scan
- Crossref historical exploration: 8 -> 10 queries/scan
- dedicated Strand-B method lane: 8 -> 10 queries/scan
- Crossref stage slice: 450 -> 540 seconds
- institutional slice: 480 -> 390 seconds
- quiet-rescue remaining-time threshold: 260 -> 180 seconds

The total hard scan budget remains 1200 seconds and the GitHub job remains capped at 30 minutes.

## What was deliberately NOT changed

`frontier_gap_historical_lookback_months` remains `0`. Extending it to 12–24 months would alter the radar's retained temporal scope and could add older Strand-A literature simply to fill matrix cells. The present problem should first be solved by making the already-wide current corpus search execute correctly and classify useful evidence with sufficient recall.

The A/B/C quality-profile versions are unchanged, so no corpus cleanup migration is triggered. The supplied `radar.json` remains the starting state and is not rebuilt or pruned.
