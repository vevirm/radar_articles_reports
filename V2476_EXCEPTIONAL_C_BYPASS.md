# v24.7.6 — exceptional Strand-C urgency bypass

This patch keeps the normal A:B:C publication balance at 8:1:3, but prevents a genuinely major current event from being hidden only because Strand C has no ordinary release slot.

## What counts as exceptional

The bypass is intentionally much stricter than ordinary Strand-C admission. A C item may publish immediately only when all of the following hold:

1. **Something actually happened.** The item is a realised or observed event, not commentary, a forecast, a consultation, a proposal, a call, a warning, a plan or an aspiration.
2. **The source is strong.** It comes from an authoritative primary institution or a configured top-tier independent/specialist reporting source.
3. **The European R&I connection is direct and substantial.** Normal member-state stories do not qualify merely for being large headlines; the narrow member-state exception is for unusually large strategic capital/control moves or severe capacity disruptions.
4. **The event falls into a strict materiality class:**
   - major access/participation change in Horizon Europe or another major European research programme;
   - a binding rule, sanction, export-control, research-security or critical-access restriction actually adopted/imposed;
   - a realised strategic capital/control move at roughly EUR/USD/GBP 1 billion scale or larger;
   - a major strategic research/technology capability actually becoming operational;
   - a severe disruption that removes or interrupts European R&I access/capacity;
   - an exceptionally large measured Europe-wide R&I system shift.

## Balance remains intact

Exceptional C is **not free extra C**. It is added to the same publication ledger. If it pushes C temporarily above 8:1:3, ordinary C stays deferred until A catches up again.

Exceptional status changes **publication timing only**. It does not increase C's analytical weight and does not let C replace primary A evidence in shocks, risks/opportunities or higher-order reasoning.

## Backlog behaviour

The test is re-applied to the pending-C queue on later mixed scans. This means a genuinely exceptional C item that is already waiting can be released without having to be rediscovered.

Event-level deduplication remains in force, so several stories about the same development do not create several emergency releases.

## Regression coverage

The patch adds tests for:
- major Horizon-access changes;
- billion-scale strategic capital moves;
- no bypass for proposals/open calls;
- no bypass for forecasts, warnings or commentary;
- no bypass from untrusted sources;
- use of an ordinary C slot before invoking the bypass;
- multiple exceptional events creating future C balance debt;
- unchanged weak-signal analytical weight.

Full local regression run: **462 tests passed, 33 intentionally skipped**.
