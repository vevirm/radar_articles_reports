# Architecture — V17.8.1 broad evidence, ranked precision, risk-first matrix

V17.8.1 uses four distinct layers: discovery, admission, cumulative storage, and interpretation/ranking.

## Discovery

Persistent OpenAlex, Crossref, priority-journal, institutional, B-method and Frontier-gap cursors remain unchanged. English-language checks run at API/page ingestion. Broad peer-reviewed journals are discoverable again.

## Admission vs priority

Admission answers: “is this substantively valid evidence for the strand?” Priority answers: “how central is it to major EU R&I under geopolitical competition?” These are intentionally separate.

Strand A still requires substantive EU R&I plus geopolitical/external-position evidence and hard-rejects obvious sports/consumer contamination. `major_eu_ri_priority_score()` then promotes system-level R&I, research security, strategic technologies, economic security, talent, infrastructure, dependencies and EU strategic competition.

Source tier contributes to confidence/ordering but is not a hard gate.

## Historical migration

Profile upgrades use `surgical_precision_cleanup()` for an already accepted corpus. This avoids the V17.8.0 failure where concise saved summaries were treated as if they were full abstracts and large parts of the corpus were deleted. Only high-confidence hard failures are removed during migration.

## Strand B

Live B remains method-development-first and requires a policy/R&I/technology-system destination. Historical B is preserved unless it is an obvious false positive.

## Strand C

C is still selective. Direct European developments pass the normal topical/event gate. External developments have a narrow materiality route for strategic mechanisms such as export controls, chips/compute, quantum, critical inputs and research-system shocks; final display still requires an A anchor.

## Frontier

The Frontier remains risk-first. Ambiguity is neutral, not positive. Column A requires realised gains on both axes. B/C/D risk cells receive greater ranking weight and gap-search priority. Strand B is excluded from evidence classification.
