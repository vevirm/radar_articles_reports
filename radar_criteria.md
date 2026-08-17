# Radar Criteria: R&I × Geopolitics + Foresight Methodology (EU-first)

## Operating principle

The radar separates **discovery** from **admission**.

- Discovery is deliberately broad and may use keywords.
- Admission is deliberately narrow and uses explicit gates below.
- A keyword match is never enough on its own.
- The radar prefers false negatives to false positives and never pads a strand.

## Date filter

- Strands A/B: verified publication date must be **2026-04-01 or later**. Publication date means the date supplied by the publisher, DOI metadata, or publication-page metadata — not an indexing date.
- Preprints are allowed if dated in range. If a published version of the same work is found, the preprint is dropped.
- Strand C: only items from the current scan window are eligible. The automated scanner uses a 13-hour lookback for a 12-hour schedule to avoid gaps if a workflow starts late.

## EU relevance rule

Every admitted item must have a clear EU/European angle.

- **Direct**: the EU, member states, European institutions, Horizon Europe/FP10, or the European R&I system is itself an object of analysis.
- **Derived**: the main case may be outside Europe, but the publication explicitly states implications, consequences, or recommendations for Europe/EU policy.
- A passing mention of “Europe” is not sufficient.
- Tier 3 non-EU sources require an explicit EU/European implication.

Rank direct EU relevance above derived EU relevance.

---

## Strand A — R&I under geopolitical change

An item enters Strand A **only if all four gates pass**.

### A1 — Substantive R&I-policy gate

The item must substantially concern research/innovation policy, science/technology policy, or the governance/organisation of R&I. Examples include:

- research and innovation policy
- research security / knowledge security
- international scientific cooperation or science diplomacy
- research funding, Horizon Europe, FP10, association arrangements
- innovation systems / research systems
- technology policy and critical/emerging technologies where policy/governance is central
- talent mobility and internationalisation of research

Being a scientific or technological research item is not enough. A laboratory study, facility description, project page, or technical paper does not qualify merely because it concerns science or technology.

### A2 — Substantive geopolitics/economic-security gate

The item must also substantially concern at least one of:

- geopolitics / geoeconomics
- economic security
- technological sovereignty / open strategic autonomy
- research security / foreign interference / trusted research
- de-risking or decoupling
- export controls / dual-use restrictions
- strategic dependencies / weaponisation of dependencies
- US–China or other strategic S&T competition
- sanctions, national-security controls, or security screening affecting R&I
- geopolitical fragmentation of international science

“Third country”, “international”, or “China” alone does not satisfy this gate.

### A3 — Explicit bridge gate

The publication must explicitly connect the R&I-policy issue to the geopolitical/economic-security issue. The scanner looks for this connection in the title, abstract, executive summary, or substantive text.

Examples of valid bridges:

- research security as a response to strategic rivalry
- Horizon Europe participation under economic-security restrictions
- science cooperation with China under de-risking policy
- export controls affecting university or research collaboration
- technology sovereignty as a research/innovation policy objective

If R&I and geopolitics appear only as unrelated mentions, reject the item.

### A4 — Analytical publication gate

The item must be a substantive analytical publication: peer-reviewed article, working paper, policy study, institutional report, or comparable research output.

Automatically reject for Strand A/B:

- calls for proposals / funding opportunities
- tenders / procurement notices
- project pages or project descriptions
- laboratory/facility/access pages
- press releases and ordinary institutional news
- blog posts, op-eds, commentary, editorials
- events, webinars, conference pages
- jobs/vacancies
- consultancy marketing or advocacy without analysis
- student theses

### Strand A topic examples

Subject to A1–A4, eligible topics include:

- EU technology sovereignty / open strategic autonomy in R&I
- research security and foreign-interference policy
- de-risking of S&T cooperation, including EU–China research relations
- export controls / dual-use rules affecting European research
- fragmentation of global science affecting European collaboration patterns
- EU positioning in US–China S&T competition and transatlantic R&I relations
- critical/emerging technologies with geopolitical framing: chips, quantum, biotech, AI, etc.
- economic-security measures affecting R&I funding, talent mobility, Horizon Europe/FP10 participation and association agreements

Exclude general geopolitics with no R&I-policy content, general innovation policy with no geopolitical/economic-security content, and single-country analyses outside Europe with no explicit EU implications.

---

## Strand B — Foresight on these issues (methodology-first)

Strand B is about **HOW foresight is or should be done**, not simply about future trends.

An item enters Strand B only if all of the following pass.

### B1 — Foresight is substantive

The publication substantially concerns foresight, horizon scanning, scenarios, anticipatory governance, futures methods, weak-signal detection, or strategic intelligence.

### B2 — Methodology is central

The publication must discuss or evaluate methodological design, not merely report the output of a foresight exercise. Qualifying methodological content includes:

- design of foresight / horizon scanning
- scenario construction or scenario-method choices
- evaluation of foresight
- biases, limits, robustness, or uncertainty handling
- institutional design of foresight functions
- participatory methods / Delphi / backcasting / morphological analysis
- weak-signal methods
- integration with strategic intelligence, risk assessment, or economic-security analysis
- how foresight is embedded in policy cycles or organisations

A report that only presents trends, scenarios, forecasts, or “the future of X” does **not** qualify unless it contains substantive methodological reflection.

### B3 — Relevant R&I / S&T / geopolitical context

The methodological discussion must relate to research, innovation, science/technology policy, contested technologies, geopolitical uncertainty, economic security, or a directly transferable public-sector R&I context.

### B4 — EU relevance

EU practice is prioritised: JRC, ESPAS, DG RTD, EU Policy Lab, member-state foresight units, European research institutes, etc. Non-EU methodological work is admitted only when the publication itself establishes a clear European/EU relevance or application.

### B5 — Quality gate

The item must pass the same publication/quality standards as Strand A.

### Both A and B

Use `both` only when an item independently passes every mandatory Strand A gate and every mandatory Strand B gate.

---

## Strand C — Weak signals (current news, anchored to A/B)

Purpose: identify early empirical developments that instantiate, confirm, accelerate, or contradict claims/themes already present in accepted A/B literature.

Every Strand C item must pass **all** of these rules:

1. Source is on the news whitelist or a clearly comparable high-quality outlet.
2. Item is factual reporting about a new event, decision, dataset, incident, funding move, policy step, agreement, restriction, or measurable development.
3. Item is from the current scan window.
4. Item has a clear EU/member-state/European relevance.
5. Item connects to at least one accepted A/B publication or a recurring theme supported by accepted A/B publications.
6. The connection can be stated explicitly in the `anchor` field.
7. The relationship is one of: `confirms`, `contradicts`, `accelerates`, `instantiates`.

**No anchor = no Strand C inclusion.**

Exclude opinion, editorials, commentary, analysis columns, explainers, interviews, routine coverage with no new development, and press-release repetition.

### News whitelist

S&T-policy press:

- Science|Business
- Research Professional News
- Table.Media (Research)
- Nature news
- Science news
- Times Higher Education

General quality press, only for S&T/economic-security reporting:

- Financial Times
- Politico Europe
- The Economist
- Reuters
- Handelsblatt
- Le Monde
- NRC
- El País

---

## Source priority for A/B

### Tier 1 — EU and European institutional

- European Commission: DG RTD, JRC, EU Policy Lab, relevant Commission services
- ESPAS
- Scientific Advice Mechanism, ESIR, ERC, ERA-related expert groups
- Parliamentary technology assessment: STOA, TAB, Rathenau Instituut, POST and peers
- Bruegel, CEPS, MERICS, SWP, IFRI, EUISS, Clingendael, Chatham House
- Fraunhofer ISI, SPRU, MIoIR, TIK, CWTS, Nesta and comparable research institutes
- national academies / R&I councils
- OECD STI

### Tier 2 — Peer-reviewed journals

Priority journals:

- Research Policy
- Science and Public Policy
- Technological Forecasting & Social Change
- Futures
- Foresight
- Minerva
- Technology in Society
- Issues in Science and Technology

The automated scanner also admits a small explicit list of comparable peer-reviewed policy/futures journals defined in `radar_config.json`.

### Tier 3 — Non-EU sources

- RAND
- CSIS
- Brookings
- Carnegie
- CSET
- ASPI
- NBER
- arXiv / policy-relevant preprints

Tier 3 requires explicit EU implications.

---

## Quality gates for A/B

At least one of the following must be verifiable:

- publication is in a whitelisted/comparable peer-reviewed venue
- publication comes from a whitelisted/comparable institution
- preprint comes from a recognised research source and otherwise passes the strict topic gates

For institutional web/PDF publications, the scanner normally requires roughly 1,800+ words. A narrow Tier-1 policy-brief exception is allowed from about 1,200 words when the document is clearly analytical. This operationalises the “~2,000 words unless exceptionally substantive” rule.

---

## Output per item

### Strands A/B

`title | authors | source | date | link (DOI preferred) | type | strand (A/B/both) | EU-relevance (direct/derived) | 3-sentence summary | 1-line relevance note`

The page additionally shows source tier and whether the item is new in the current scan.

### Strand C

`headline | source | date | link | anchor | signal type (confirms / contradicts / accelerates / instantiates) | 2-sentence signal note`

---

## Ranking and limits

- A/B: maximum **15 newly admitted unique publications per scan** across the A/B pipeline.
- Rank by EU relevance (`direct > derived`), then source priority (`Tier 1 > Tier 2 > Tier 3`), then date descending.
- Previously accepted A/B publications remain in the cumulative radar corpus; later scans mainly add new items with a 7-day discovery overlap to catch late indexing.
- C: maximum **5 items per scan**, ranked by strength of anchor connection rather than prominence.
- If a scan finds fewer than 3 A items, fewer than 3 B items, or zero C items, the site states that explicitly. It never fills a quota with weaker material.
