# Main Radar claim audit — V17.13.28

## Problem addressed

Earlier versions could show a correct but low-information thematic sentence repeatedly across unrelated sources, for example “Geopolitical competition is pushing Europe to link innovation policy more closely to resilience.” That wording describes a topic rather than telling the reader what an individual paper/report actually found.

## New rule

A main-Radar claim should normally contain:

1. the relevant actor, institution, instrument, capability or dependency;
2. the concrete change/finding described in this source; and
3. the consequence or mechanism relevant to EU R&I geopolitics.

The main Radar is allowed more technical detail than Read or the Matrix. It therefore uses a longer complete-sentence budget when necessary rather than collapsing different papers into the same generic slogan.

## Fail-closed presentation

The display layer rejects reusable thematic slogans, scanner/review scaffolding, method boilerplate and obvious document debris. If the saved radar state does not contain a substantive finding, the system does not fabricate one from a broad topic label.

## Legacy migration

50 stored generic claims were replaced with source-specific propositions where supported by the saved evidence. Four additional legacy records were removed because the attempt to state a source-specific geopolitical R&I proposition exposed that their saved evidence did not substantiate the admission mechanism. The exact removals are recorded in `QUALITY_CLEANUP_V17_13_28.json`.
