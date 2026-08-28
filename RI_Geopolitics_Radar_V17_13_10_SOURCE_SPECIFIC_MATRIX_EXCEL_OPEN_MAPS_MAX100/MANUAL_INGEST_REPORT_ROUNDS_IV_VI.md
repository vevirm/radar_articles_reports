# Manual ingest & recall report — rounds IV–VI

Batch: `0f1a8c55c834-9b0296a6`  
Ingested: `2026-08-26T09:42Z`  
Manual source: `EU_RI_Found_Items_Rounds_IV-VI.docx`  
Review policy: exact curator-supplied URLs first; only redirects/direct links exposed by those pages; no broad search-engine or general title discovery.

## Batch outcome

| Measure | Count |
|---|---:|
| Parsed records | 58 |
| Already admitted by automation | 4 |
| Seen automatically but not admitted | 1 |
| Not found by saved automated discovery | 53 |
| New substantive radar items | 10 |
| New matrix items | 7 |
| Deferred | 40 |
| Reviewed core-gate rejects | 4 |
| Secondary/incomplete references | 3 |
| Context/outside-window | 0 |
| Forthcoming/unpublished | 0 |
| Weak signals admitted | 0 |

The scanner timestamp remains `2026-08-26T08:57Z`. The manual review is stored separately under `manual_ingest`; no scanner cursor was advanced by this batch.

## Newly admitted substantive items

- **K26** — Geopolitics in Science Policy: Dilemmas for the mobilisation of research
- **K28** — Science Knows No Borders: ALLEA condemns proposed restrictions on international research collaboration — matrix: knowledge B
- **K30** — Beyond Borders: Chinese Use of Foreign Interference Tactics in Dutch Strategic Industries — matrix: knowledge D
- **I23** — Beyond the European Chips Act: EU Supply Chain Dependencies on China, Taiwan and the United States — matrix: infrastructure D
- **I24** — The EU Semiconductor Geopolitical Risk Survey: Outlook for 2026–2031 — matrix: infrastructure D
- **C19** — Das Auto and the Second China Shock: Industrial Policy and the Disruption of Technological Incumbency — matrix: conversion D
- **C25** — Defence Research in European Universities: A Conceptual Framework
- **C26** — Europe Tackles Tech Sovereignty — matrix: infrastructure C
- **R30** — Cloud and AI Development Act — Council working document ST 10104/26
- **R31** — Chips Act 2.0, Part 1: Europe’s second semiconductor push — matrix: rules D

## Existing corpus matches (no duplicate)

- K25, R16, R17, R22

## Reviewed core-gate rejections

- **K18** — Beyond traditional destinations: exploring international scholars’ decision-making patterns for postdoctoral positions at Chinese universities
- **K29** — Science diplomacy: Sovereignty, strategy, and the global race
- **I25** — From catch-up to command: China’s 15th five-year plan and the strategic turn toward technological sovereignty
- **R29** — Call for evidence on future Joint Undertakings and Article 185 initiatives under Horizon Europe

These were rejected only after source review established that the retrieved item did not substantively concern EU/European R&I in geopolitical context; they were not rejected for retrieval failure.

## Deferred / retrieval-limited items

40 records remain deferred. Of these, **37** are exact-URL retrieval/insufficient-text cases and **3** are secondary/incomplete references (`I27, C27, R28`). Retrieval failure is retained as a limitation, not converted into an irrelevance decision.

Verification caveats remain active for: K31, I22, C14, C15, C23, R22.

## Matrix review: curator hypothesis vs independent evidence

| ID | Curator primary cell | Independent placement | Result |
|---|---|---|---|
| K28 | R-A | K-B; claimed A retained separately | changed |
| K30 | I-D | K-D | changed |
| I23 | I-D | I-D | survived |
| I24 | I-C | I-D | changed |
| C19 | C-D | C-D | survived |
| C26 | C-B | I-C | changed |
| R31 | R-D | R-D | survived |

Survived unchanged: **I23 → I-D, C19 → C-D, R31 → R-D**. Changed after source review: **K28 R-A → K-B** (with claimed A preserved separately), **K30 I-D → K-D**, **I24 I-C → I-D**, **C26 C-B → I-C**. The other three newly admitted sources (K26, C25, R30) were admitted to the radar but not forced into a matrix cell because the reviewed evidence did not support a sufficiently singular outcome classification.

## Recall diagnosis for the 10 high-quality recovered admissions

| ID | Saved automated status | Recall diagnosis |
|---|---|---|
| K26 | not_found | `covered_source_exact_item_not_observed_in_rotation` |
| K28 | scanner_seen_url_not_admitted | `seen_but_rejection_stage_unknown_from_saved_state` |
| K30 | not_found | `source_not_covered_prior_to_targeted_manual_recall_expansion` |
| I23 | not_found | `source_not_covered_prior_to_targeted_manual_recall_expansion` |
| I24 | not_found | `source_not_covered_prior_to_targeted_manual_recall_expansion` |
| C19 | not_found | `scholarly_index_item_not_observed` |
| C25 | not_found | `covered_source_but_saved_state_cannot_localise_item_miss` |
| C26 | not_found | `source_not_covered_prior_to_targeted_manual_recall_expansion` |
| R30 | not_found | `sitemap_or_feed_failure` |
| R31 | not_found | `source_not_covered_prior_to_targeted_manual_recall_expansion` |

Targeted recovery changes made without lowering the core gate:

- Added bounded direct-source coverage for `hcss.nl`, `iai.it`, `institutmontaigne.org`, and `gmfus.org`.
- Added specialist news coverage for `eenewseurope.com`.
- Preserved existing exact-URL recovery queues for unresolved supplied links.
- Did not broaden the relevance gate; the four reviewed non-core items were explicitly rejected and 40 unverified/incomplete items remain deferred.

## Bibliographic corrections from direct review

- **K25** — date: `2026-06-01` → `2026-06-02`
- **K26** — source: `Rathenau Instituut, The Hague (English edition; Dutch original January 2026).` → `Rathenau Instituut`
- **K28** — title: `Statement: Science Knows No Borders — ALLEA condemns proposed restrictions by the White House on international research collaboration` → `Science Knows No Borders: ALLEA condemns proposed restrictions on international research collaboration`; source: `Also: ALLEA Task Force on Integrating Research Security and Academic Freedom, meeting at the Royal Society, London, 15 June 2026; ALLEA and partners, joint statement on Open Scienc` → `ALLEA`
- **K29** — date: `2026-07-06` → `2026-07-07`; source: `Report of session 2025–26.` → `UK House of Commons Science, Innovation and Technology Committee`
- **K30** — title: `Chinese Foreign Interference in Dutch Strategic Industries` → `Beyond Borders: Chinese Use of Foreign Interference Tactics in Dutch Strategic Industries`; source: `HCSS (The Hague Centre for Strategic Studies) with the China Knowledge Network.` → `The Hague Centre for Strategic Studies (HCSS)`
- **I23** — source: `IAI, Rome.` → `Istituto Affari Internazionali (IAI)`
- **I24** — source: `Institut Montaigne, with EUISS, CEIAS and CSDS, under the EU-co-funded Chips Diplomacy Support Initiative (CHIPDIPLO).` → `Institut Montaigne / CHIPDIPLO`
- **I25** — date: `2026-06-01` → `2026-05-19`; authors: `Clingendael` → `Ruslan Bortnik; Gergely Salát`; source: `Listed in the Council of the EU Library’s Think Tank Review 142 (June 2026).` → `Hungarian Institute of International Affairs (HIIA)`
- **C19** — source: `Politics and Governance 14.` → `Politics and Governance`
- **C26** — title: `Europe Tackles Tech Sovereignty (monthly technology note; includes the GATT-C 2026 debate on whether European digital resilience excludes or cooperates with partners)` → `Europe Tackles Tech Sovereignty`; source: `` → `German Marshall Fund of the United States (GMF)`
- **C27** — date: `2026-01-01` → `2026-06-11`
- **R29** — title: `Call for evidence on future Joint Undertakings and Article 185 initiatives under Horizon Europe 2028–2034` → `Call for evidence on future Joint Undertakings and Article 185 initiatives under Horizon Europe`; date: `2026-07-14` → `2026-06-17`; source: `Stakeholder responses include the European Quantum Industry Consortium (10 July 2026), which describes the initiative as a Single Basic Act for Joint Undertakings` → `ERA-LEARN / European Commission`
- **R30** — title: `Working document ST 10104/26, TREE.2.B — first Council text on the Cloud and AI Development Act, circulated the day after the Commission proposal COM(2026) 502; contains placeholders for references to Chips Act 2.0 to be added once adopted` → `Cloud and AI Development Act — Council working document ST 10104/26`; source: `` → `Council of the European Union`
- **R31** — title: `Chips Act 2.0, Part 1: Europe’s second semiconductor push — legislative status as of 7 August (COM(2026) 504; file 2026/0139(COD); Parliament in preparatory phase); post-2027 funding for the Chips for Europe Initiative 2.0 and strategic projects contingent on the 2028–34 MFF; the ECA’s 2025 forecast of an 11.7% global share in 2030 against the 20% target` → `Chips Act 2.0, Part 1: Europe’s second semiconductor push`; date: `2026-08-07` → `2026-08-12`; source: `` → `eeNews Europe`
