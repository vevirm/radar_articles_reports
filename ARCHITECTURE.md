# Architecture — V17.7.4 A/B/C semantic separation and matrix-first allocation

The radar has four stages: discovery, admission, cumulative storage, and interpretation.

## Discovery and persistent rotation

`scripts/scan_radar.py` stores rotation state in `radar.json::scan_state`. Independent cursors cover OpenAlex, Crossref broad queries, priority-journal tasks, institutional sources, a dedicated B-method query bank, frontier-gap queries, frontier specialist sources and deeper result pages. These cursors survive quality-profile changes.

Gap scanning allocates first claim on spare discovery capacity to the sparsest Frontier cells without relaxing the A gate. Zero-count cells are searched repeatedly before near-empty cells. After the normal source stages, a matrix-first depth phase advances deeper scholarly result pages until the scan approaches its hard runtime budget. The dedicated B lane still rotates independently so method discovery does not depend on the topical A cursor.

## A — evidence

A is precision-first. Admission requires direct EU/European/Member-State scope plus substantive R&I content and a real geopolitical/economic-security connection. R&I includes research policy/security/collaboration/funding, science diplomacy, R&D and innovation systems/capability, infrastructures, talent flows, and strategic technologies when research/innovation/capability-building is actually part of the document.

Boilerplate such as Horizon Europe funding acknowledgements is stripped before admission. Deep-body mentions cannot rescue an unrelated institutional page.

## B — methods

B is not another evidence strand. It is a **method-development library** for understanding the future of A. A source qualifies when the reusable futures/R&I-futures method is itself the contribution: either it explicitly develops/adapts/extends/refines/designs the method, or a method-first paper provides validation/benchmark/transfer evidence showing that the analytical workflow is the contribution. Mere application of an existing method does not qualify. Generic techniques such as Delphi, system dynamics or agent-based modelling also require an explicit futures/foresight purpose.

A domain study that merely applies Delphi, scenarios, system dynamics or another technique does not qualify. Ambiguous “scenario construction/building/development” language also needs an independent future/foresight/anticipatory/strategic cue, preventing teaching or simulation scenes from being mistaken for futures methods.

## C — weak signals

C is an interpretive update layer, not a generic news feed. It accepts three bounded forms of current evidence: early/uncertain developments; new empirical findings/indicators; and consequential R&I changes such as investments, restrictions, standards, collaboration/talent moves or infrastructure/capability shifts. The third route does not require pilot/draft wording, but it must contain R&I substance plus strategic stakes.

Every C item is anchored to A. B and generic watch themes are not valid anchors. External US/China/global developments can reach the prefilter when materially relevant, but are discarded unless a specific or recurring Strand-A anchor explains the European significance. Event-level headline normalisation collapses syndicated or paraphrased coverage of the same signal.

## Frontier

`frontier/frontier.js` uses Strand A as its substantive evidence corpus and Strand C as current contextual change. Strand B is deliberately excluded from evidence indexing and matrix occupancy.

The Frontier retains semantic row/cell logic, including explicit Knowledge & people mechanisms and recognition of individual EU Member States. Sparse cells guide discovery rotation; they do not manufacture evidence.
