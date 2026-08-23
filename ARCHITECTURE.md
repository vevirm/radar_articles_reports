# Architecture — V17.6.1 A/B/C semantic separation

The radar has four stages: discovery, admission, cumulative storage, and interpretation.

## Discovery and persistent rotation

`scripts/scan_radar.py` stores rotation state in `radar.json::scan_state`. Independent cursors cover OpenAlex, Crossref broad queries, priority-journal tasks, institutional sources, a dedicated B-method query bank, frontier-gap queries, frontier specialist sources and deeper result pages. These cursors survive quality-profile changes.

Gap scanning can allocate extra effort to sparse Frontier cells, but it cannot relax the A gate. The dedicated B lane rotates method-focused searches independently so method discovery does not depend on the topical A cursor.

## A — evidence

A is precision-first. Admission requires direct EU/European/Member-State scope plus substantive R&I content and a real geopolitical/economic-security connection. R&I includes research policy/security/collaboration/funding, science diplomacy, R&D and innovation systems/capability, infrastructures, talent flows, and strategic technologies when research/innovation/capability-building is actually part of the document.

Boilerplate such as Horizon Europe funding acknowledgements is stripped before admission. Deep-body mentions cannot rescue an unrelated institutional page.

## B — methods

B is not another evidence strand. It is a **method-development library** for understanding the future of A. A source qualifies when the reusable futures/R&I-futures method is itself the contribution: either it explicitly develops/adapts/extends/refines/designs the method, or a method-first paper provides validation/benchmark/transfer evidence showing that the analytical workflow is the contribution. Mere application of an existing method does not qualify. Generic techniques such as Delphi, system dynamics or agent-based modelling also require an explicit futures/foresight purpose.

A domain study that merely applies Delphi, scenarios, system dynamics or another technique does not qualify. Ambiguous “scenario construction/building/development” language also needs an independent future/foresight/anticipatory/strategic cue, preventing teaching or simulation scenes from being mistaken for futures methods.

## C — weak signals

C contains early/uncertain developments, not a generic news feed. Signals must have weak-signal character such as pilots, trials, proposals, delays, targeted/limited arrangements, new entrants or early partnerships. Mature final implementation is excluded unless it contains a genuine counter-signal.

Every C item is anchored to A. B and generic watch themes are not valid anchors. Event-level headline normalisation collapses syndicated or paraphrased coverage of the same signal.

## Frontier

`frontier/frontier.js` uses Strand A as its substantive evidence corpus and Strand C as current contextual change. Strand B is deliberately excluded from evidence indexing and matrix occupancy.

The Frontier retains semantic row/cell logic, including explicit Knowledge & people mechanisms and recognition of individual EU Member States. Sparse cells guide discovery rotation; they do not manufacture evidence.
