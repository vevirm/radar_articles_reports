# V17.7.2 — source-first contextual recall

The supplied 2026-08-23T17:42Z state makes the latest zero-result scan diagnosable rather than ambiguous. It was not a healthy “nothing relevant exists” run: `scan_health` was degraded; OpenAlex executed only 4 of 32 planned queries and 0 base queries before a 429 stop; Crossref also produced repeated 429 warnings; and the whole run used only 254.7 of the 1200-second budget. At the same time, the preceding run had admitted an obviously irrelevant basketball-teaching paper into Strand B because “scenario construction” was interpreted as a futures method.

V17.7.2 therefore fixes recall and precision together.

## 1. Source-first priority-journal sweep

Eight rotating priority journals are scanned by recent contents each run, independently of keyword query wording. This gives the radar a direct route to high-quality journal output and makes rotation correspond more closely to the breadth of the configured source universe. The lane is execution-aware and bounded to 60 Crossref records per journal.

## 2. Contextual Strand-A route

The original explicit EU R&I + geopolitics/economic-security route remains. A second bounded route admits direct European R&I evidence when the bibliographic evidence unit contains both an external-position mechanism (comparison/dependence/access/competition/flows) and a strategic R&I outcome (capacity, competitiveness, talent, scale, capability, infrastructure, etc.). Generic EU innovation-performance papers still fail.

## 3. Better diagnostics

`stats.admission_diagnostics` records how many OpenAlex, Crossref and institutional records reached the substantive gate and whether they failed for no direct EU scope, no R&I evidence or no strategic context. A future zero scan can therefore be separated into retrieval failure versus classifier rejection.

## 4. Rate-limit resilience

The observed run was request-limited rather than time-limited. V17.7.2 slows anonymous traffic instead of spending the budget in a burst: OpenAlex uses one worker with a 1.0-second minimum request interval, Crossref a 1.2-second minimum interval. Crossref 429s receive bounded cooldown retries, while OpenAlex retains its established fail-fast-on-429 behavior after the slower pacing.

## 5. Strand-B false-positive guard

“Scenario construction”, “scenario building” and “scenario development” are ambiguous outside futures studies. If they are the only futures-family match, the item must also contain an independent future/foresight/anticipatory/long-term/strategic-scenario cue. This blocks teaching/simulation scenario papers while preserving genuine future-scenario methods.

## 6. State preservation

The bundled `radar.json` is byte-for-byte identical to the supplied `radar (13).json` (51 A / 12 B / 5 C). No existing accepted item is removed. The recall-profile reset affects only search progress/fingerprints so the widened routes get a real chance to inspect the four-month corpus.
