# Radar Criteria: R&I × Geopolitics + Foresight Methodology (EU-first) — balanced operational version

## Purpose
The radar is selective, but it should not be so brittle that only items using the exact same vocabulary are admitted. Search/discovery is intentionally broad. Admission is based on substantive evidence in the publication as a whole, not on a keyword score or a single sentence.

## Date filter
- A/B: verified publication date >= 2026-04-01 (publication date, not indexing date).
- Preprints are allowed if dated in range; when a published version is clearly available, prefer it and drop the duplicate preprint.
- First scan: backfill A/B from 2026-04-01 to the present.
- Later A/B scans: search new material with a 14-day overlap to catch late indexing/corrected metadata; accepted A/B items remain in the cumulative corpus.
- Strand C: first scan uses a 7-day news lookback; later scans use a 48-hour overlap. C is a moving weak-signal layer, not a cumulative news archive.

## EU relevance rule
EU-first ranking applies to all strands.

**Direct**: the EU, member states, European R&I systems, Horizon Europe/FP10, or European strategic/policy choices are themselves an object of analysis.

**Derived**: the publication is not primarily EU-focused but explicitly draws implications for Europe/EU strategy. For Strand B only, a high-quality methodology-first paper can also be `derived` when its method is clearly transferable to public-sector R&I/S&T/strategic-policy foresight in Europe.

A passing mention of Europe is not enough.

---

## Strand A — R&I under geopolitical change

A qualifying item must satisfy all of A1–A4.

### A1 — substantive R&I-policy content
The publication must substantially concern research/innovation/science/technology policy or governance: research security, international S&T cooperation, R&I funding/programmes, science diplomacy, innovation systems, talent mobility, critical-technology policy, Horizon Europe/FP10, research governance, etc.

Merely being a scientific research paper, project, laboratory, or grant call is not enough.

### A2 — substantive geopolitics/economic-security content
The publication must substantially concern at least one geopolitical/economic-security mechanism: strategic competition, de-risking, foreign interference, export controls, dual use, technology sovereignty, strategic autonomy, strategic dependencies, economic security, sanctions, fragmentation/decoupling of science, national-security constraints, US–China competition, etc.

### A3 — supported R&I ↔ geopolitics connection
The two dimensions must genuinely interact. A same-sentence connection is strong evidence but is **not mandatory**. The bridge may be established across the title/abstract or across the document when the publication clearly analyses how geopolitical/economic-security change affects R&I policy/governance (or vice versa).

This prevents false negatives caused by wording while still rejecting documents where R&I and geopolitics are unrelated passing mentions.

### A4 — EU relevance and analytical publication
The item must pass the EU relevance rule and be an analytical publication: peer-reviewed article, working paper, policy study, institutional report, substantive policy brief, or comparable research output.

Eligible topics include:
- EU technology sovereignty / open strategic autonomy in R&I
- research security / foreign interference / trusted research
- de-risking of S&T cooperation and EU–China research relations
- export controls / dual-use rules affecting European research
- fragmentation of global science and European collaboration
- EU positioning in US–China S&T competition; transatlantic R&I relations
- critical/emerging technologies with geopolitical framing (chips, quantum, biotech, AI)
- economic-security measures affecting R&I funding, talent, Horizon Europe/FP10 participation and association
- science diplomacy under strategic competition

Exclude general geopolitics with no R&I-policy dimension and general innovation policy with no geopolitical/economic-security dimension.

---

## Strand B — Foresight methodology

B is methodology-first, but the case study does not need to be explicitly geopolitical if the method is genuinely useful for R&I/S&T/strategic-policy foresight.

A qualifying B item must satisfy B1–B4.

### B1 — foresight is substantive
The publication substantially concerns strategic foresight, horizon scanning, scenario methods, anticipatory governance, futures methods, weak-signal detection, or strategic intelligence.

### B2 — methodology is substantive
The publication discusses **how** foresight is designed, conducted, evaluated, institutionalised, made robust, or integrated with other methods. Qualifying content includes:
- horizon-scanning design and weak-signal methods
- scenario construction / scenario-method choices
- evaluation and quality criteria
- uncertainty, bias, limitations and robustness
- Delphi, backcasting, morphological analysis, participatory methods
- institutional design/capability for foresight
- integration with strategic intelligence, risk assessment or economic-security analysis

The method can be established across multiple title/abstract sentences; it does not need to be described in one sentence.

### B3 — relevant practice context
The methodological contribution must be useful for R&I, S&T, technology governance, public/strategic policy, government foresight, critical/emerging technologies, economic security, or a closely related public-sector anticipatory context.

Generic futures work on an unrelated topic does not qualify merely because it contains the word “research”.

### B4 — EU relevance / transferability and quality
Direct EU practice is prioritised. High-quality non-EU methodology may enter as `derived` when clearly transferable to EU public-sector R&I/S&T/strategic-policy practice.

Pure trend reports, “future of X” outputs and scenario sets are excluded unless they contain substantive methodological reflection.

### Both A and B
Use `both` only when the publication independently satisfies all A gates and all B gates.

---

## Strand C — Weak signals, anchored to A/B

Purpose: catch early empirical indications of developments theorised, anticipated or warned about by accepted A/B literature.

All rules must hold:
1. trusted/comparable news source;
2. factual reporting of a new event, decision, dataset, incident, funding move, policy step, agreement, restriction or measurable development;
3. within the current C window (7 days on the first run, 48-hour overlap thereafter);
4. clear EU/member-state/European relevance;
5. connection to at least one accepted A/B publication **or** a specific A/B theme supported by the accepted corpus;
6. explicit anchor can be written;
7. relationship is `confirms`, `contradicts`, `accelerates`, or `instantiates`.

No anchor = no inclusion.

The anchor threshold is deliberately moderate: a strong thematic match to one accepted publication can qualify; a very broad theme (e.g. “critical technologies”) still needs an additional entity/text overlap.

Exclude opinion, editorials, commentary, analysis columns, explainers, interviews, routine process coverage with no new development, and press-release repetition.

### News whitelist (extend by analogy)
Science|Business; Research Professional News; Table.Media (Research); Nature news; Science news; Times Higher Education; Financial Times; Politico Europe; The Economist; Reuters; Handelsblatt; Le Monde; NRC; El País — S&T/economic-security reporting only.

---

## Source priority for A/B

### Tier 1 — EU and European institutional
European Commission/DG RTD/JRC/EU Policy Lab; ESPAS; EU advisory bodies; STOA/TAB/Rathenau/POST; Bruegel; CEPS; MERICS; SWP; IFRI; EUISS; Clingendael; Chatham House; Fraunhofer ISI; SPRU; MIoIR; TIK; CWTS; Nesta; national academies/R&I councils; OECD STI and comparable sources.

### Tier 2 — peer-reviewed journals
Research Policy; Science and Public Policy; Technological Forecasting & Social Change; Futures; Foresight; Minerva; Technology in Society; Issues in Science and Technology, plus a small explicit set of comparable policy/futures journals in `radar_config.json`.

### Tier 3 — non-EU sources
RAND; CSIS; Brookings; Carnegie; CSET; ASPI; NBER; policy-relevant SSRN/arXiv and comparable sources. A requires explicit EU implications; B can qualify as derived only when the methodological contribution is clearly transferable.

## Quality gates
At least one:
- peer-reviewed/comparable journal;
- whitelisted/comparable institution;
- recognised research/preprint source with the substantive gates satisfied.

Institutional publications normally need ~1,500+ words. Concise Tier-1 analytical briefs/reports can qualify from ~900 words when document type and substantive gates are strong. Calls, facility/project pages, news releases, events and marketing remain hard exclusions.

## Ranking and limits
- A/B: max 15 newly admitted unique publications per scan; cumulative accepted corpus is retained.
- Rank: direct EU > derived EU; Tier 1 > Tier 2 > Tier 3; then publication date descending.
- C: max 5 per scan, ranked by strength of anchor connection, not news prominence.
- If fewer than 3 A, fewer than 3 B, or zero C are found, report that explicitly; do not pad.
