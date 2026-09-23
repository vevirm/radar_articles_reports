# Deep Scan V2 work status

This file is generated from the authoritative Deep Scan sidecar plus the persistent worker-assignment ledger.
It exists so a new chat or operator can see what has already been verified, what each worker owns, and what now needs hands-on verification.

Scheduling policy: preserve existing worker reservations; fill new slots with fresh **Main Radar first**; then use spare capacity for **Historical Radar**. Access-recovery retries are bounded and throttled so difficult works cannot consume every run.
A validated `defer` counts as one genuine recovery pass. After **3** unsuccessful passes, the work leaves the automatic queue and enters **Hands-on verification needed**.

- Authoritative V2 verified: **1862** (Main **944** + Historical **918**)
- Automatic queue still needing V2 verification: **97** (Main **59** + Historical **38**)
- Currently assigned to workers: **96** (Main **59** + Historical **37**)
- Bounded access-recovery retries still eligible: **0**
- Hands-on verification needed: **13**
- Automatic queue pending and not yet assigned: **1**

## Worker lanes

### Worker A
- Current package: `worker-a-20260923T111117Z-2c2436e144e4`
- Assigned unresolved records: **36**
  1. `historical:id:bc665999887802f2` — ALLEA Participates in EU-Funded Project to Support Reforms in Research Assessment - ALLEA
  2. `historical:id:7a6b1859e290bf8d` — Innovation Wars: How China Is Gaining on the United States in Corporate R&D
  3. `historical:id:975c2b201ea7d1ec` — How China Divides Europe and the United States
  4. `historical:id:df7334496eb36789` — A Compass to Guide EU Policy in Support of Business Competitiveness
  5. `historical:id:9c46d0586d96396f` — ALLEA Joins the European Commission Coalition on Research Assessment Reform - ALLEA
  6. `historical:id:d8cc69968937a4cd` — Europe’s dependence on Chinese semiconductor manufacturing - Digital Power China Report
  7. `historical:id:cef3cfdeb1591a87` — Explanatory models of regional innovation performance in Europe: policy implications for regions
  8. `link:https://doi.org/10.1080/10438599.2026.2693627` — Do wage pressure and government R&D stimulate business R&D? Regional level evidence from Europe — recovery attempt 3/3
  - … plus 28 more in the package manifest

### Worker B
- Current package: `worker-b-20260923T111141Z-28aea726fe9b`
- Assigned unresolved records: **60**
  1. `link:https://www.eit.europa.eu/` — EIT entrepreneurial education: Learn from leaders of European innovation
  2. `link:https://www.ellisinstitute.fi/PIs-2026` — ELLIS Institute Finland recruits 7 new principal investigators | ELLIS Institute Finland
  3. `link:https://www.clean-hydrogen.europa.eu/document/download/0fa1c244-a674-4899-bf4f-f2fc9ba43ae7_en?filename=H2Week_Agenda%20Innovation%20Forum%202026_HE_web%20%28002%29.pdf` — EU Hydrogen Innovation Forum 2026
  4. `link:https://era.gv.at/news-items/eu-launches-first-research-network-on-antisemitism-and-jewish-life/` — EU launches first research network on antisemitism and Jewish life
  5. `link:https://defence-industry-space.ec.europa.eu/eudis-defence-hackathon-spring-2026-meet-winning-teams-driving-innovation-airspace-defence-2026-03-30_en` — EUDIS Defence Hackathon Spring 2026: Meet the Winning Teams Driving Innovation in Airspace Defence
  6. `link:https://doi.org/10.1007/s10888-026-09737-5` — Earnings inequality patterns: A comparative analysis of France, Italy, Portugal and Spain
  7. `link:https://ellis.eu/publication/2025-enhancing-study-level-inference-from-clinical-trial-papers-via-reinfor` — Enhancing Study-Level Inference from Clinical Trial Papers via Reinforcement Learning-Based Numeric Reasoning
  8. `link:https://www.ellisinstitute.fi/entrepreneurial-postdoc-recruit-autumn-2026` — Entrepreneurial postdoc positions at ELLIS Institute Finland | ELLIS Institute Finland
  - … plus 52 more in the package manifest

## Hands-on verification needed

These works no longer consume automatic Deep Scan slots. Their identity is believed to be real, but substantive evidence could not be recovered automatically. Re-open one only when you have a new source, PDF, repository copy, or other materially new access route.

- `link:https://news.google.com/rss/articles/CBMi0AFBVV95cUxOYjVKaVdVX2cwZHBpWE5KQlVpRnFFeVFvT2JwTWVuWTlfQ0lUeGpaZWkzaUxDMTZKUHZRU2d6OVVMYWUwSEk4VGN0N0pNWUYyXzZfNDFOTWxqenFwakNMbmpZd2h1ZDFrT2VfVlpwNjJVaDl1elZ2YXBSYWU0TG9JSkstVjdPMW03LUI4X1VWdU1nYzV4WmcxUkg3WE16WUlIb0RzNHU5N3lTX19COWRCdE1DaWhmOHBHekpua0RMVEh2WGFDcl9HSGVIWk90N3ZU?oc=5` — **Moves to cut FP10 budget ‘threaten Europe’s competitiveness’** — attempts: legacy terminal — Research Professional News — 2026-09-09T12:46Z — Identity is established, but substantive evidence remains insufficient after all six mandated recovery steps, so KEEP/REVIEW/DROP cannot be made responsibly. — https://news.google.com/rss/articles/CBMi0AFBVV95cUxOYjVKaVdVX2cwZHBpWE5KQlVpRnFFeVFvT2JwTWVuWTlfQ0lUeGpaZWkzaUxDMTZKUHZRU2d6OVVMYWUwSEk4VGN0N0pNWUYyXzZfNDFOTWxqenFwakNMbmpZd2h1ZDFrT2VfVlpwNjJVaDl1elZ2YXBSYWU0TG9JSkstVjdPMW03LUI4X1VWdU1nYzV4WmcxUkg3WE16WUlIb0RzNHU5N3lTX19COWRCdE1DaWhmOHBHekpua0RMVEh2WGFDcl9HSGVIWk90N3ZU?oc=5
- `link:https://news.google.com/rss/articles/CBMixwFBVV95cUxQR1JiOFNtQlZBYUJUUThOYXVYSjFad2h0TG5OSm9ZdDBaY0NrbVk3UkkxUlZJMWFPczJySWd5RmwtYmZsdFE2bS1iOGJnMHFacHBtWE5GUWpqRTN3QXR4SHVtdE1ZRktGY3V6SUc0OWtIQVhSMUp5QVk2ZjE0N29TdFp6ZzgwTmx0aXpkMFpsM2lfb2xrWUtyWXJLY1hlYnRqNEhQWHNZLUhZZThpeklQU3NHWXQ2SGZhNkpmTllLU1JCN1NMU2Jv?oc=5` — **EU-China research cooperation limited to ‘targeted areas’** — attempts: legacy terminal — Research Professional News — 2026-08-10T07:00Z — Identity is confirmed against the publisher's own article page, but the reporting itself is subscriber-gated; making a strand C admission judgement would require substituting Commission background pages for the claimed work, which is not permitted. — https://news.google.com/rss/articles/CBMixwFBVV95cUxQR1JiOFNtQlZBYUJUUThOYXVYSjFad2h0TG5OSm9ZdDBaY0NrbVk3UkkxUlZJMWFPczJySWd5RmwtYmZsdFE2bS1iOGJnMHFacHBtWE5GUWpqRTN3QXR4SHVtdE1ZRktGY3V6SUc0OWtIQVhSMUp5QVk2ZjE0N29TdFp6ZzgwTmx0aXpkMFpsM2lfb2xrWUtyWXJLY1hlYnRqNEhQWHNZLUhZZThpeklQU3NHWXQ2SGZhNkpmTllLU1JCN1NMU2Jv?oc=5
- `link:https://doi.org/10.1108/fs-11-2021-0228` — **Iran’s approach to energy policy towards 2040: a participatory scenario method** — attempts: legacy terminal — foresight — 2023-03-03 — Identity is verified, but accessible evidence remained abstract/metadata-level after all six recovery steps; a defensible Strand B judgement would require substantive text. — https://doi.org/10.1108/fs-11-2021-0228
- `link:https://news.google.com/rss/articles/CBMihAFBVV95cUxOR3p4SXpZMVhsZk0yN3V0TDZXT3pnV1VaWkNrc2hOYXpaT3RDaGZzVUhZclRKMHVDbHNIMG5vQjFmY21GQk5lcDFhWlcxaHZZekVqQkk4Z28yU2FkeGNYbVB4eUFIZkwzQTFEMnZiOFdrdGdnWFZTNkxFeUNaWklSbVRTbHE?oc=5` — **Data centres drive Ireland to reopen nuclear power debate** — attempts: 3/3 — Financial Times — 2026-08-22T07:00Z — FT article identity confirmed via headline search, but primary text is paywalled; secondary reposts cannot substitute. — https://news.google.com/rss/articles/CBMihAFBVV95cUxOR3p4SXpZMVhsZk0yN3V0TDZXT3pnV1VaWkNrc2hOYXpaT3RDaGZzVUhZclRKMHVDbHNIMG5vQjFmY21GQk5lcDFhWlcxaHZZekVqQkk4Z28yU2FkeGNYbVB4eUFIZkwzQTFEMnZiOFdrdGdnWFZTNkxFeUNaWklSbVRTbHE?oc=5
- `historical:id:5f02392522b6f284` — **US research-policy instability created an observable opportunity for Europe to attract mobile scientific talent.** — attempts: 3/3 — Nature — 2025-05-13 — Paywalled news feature; accessible text is a one-line standfirst, insufficient for KEEP/REVIEW/DROP. — https://www.nature.com/articles/d41586-025-01489-y
- `historical:id:429b7fb8a4fd8c00` — **Fumbling Toward Foresight** — attempts: 3/3 — Futures — 2020-12-01 — Identity is verified, but substantive matching evidence remained inaccessible or insufficient after all six mandatory recovery steps. — https://doi.org/10.1177/1946756720976713
- `historical:id:b6502660dc2a056b` — **Russia’s energy in 2030: future trends and technology priorities** — attempts: 3/3 — Foresight — 2017-04-10 — Identity is verified, but substantive matching evidence remained inaccessible or insufficient after all six mandatory recovery steps. — https://doi.org/10.1108/fs-07-2016-0034
- `historical:id:0fa9a045c44ef264` — **A Three-Level Evaluation Process of Cultural Readiness for Strategic Foresight Projects** — attempts: 3/3 — Futures — 2019-12-01 — Identity confirmed via Crossref/OpenAlex and publisher abstract; no legitimate full text found after all six steps, so no admission judgement is made. — https://doi.org/10.1177/1946756719862115
- `link:https://doi.org/10.1108/14636681211210341` — **A case study on localising foresight in South Africa: using foresight in the context of local government participatory planning** — attempts: 3/3 — Foresight — 2012-02-24 — Identity is verified, but only publisher structured-abstract material was recoverable; the required substantive text was not accessible. — https://doi.org/10.1108/14636681211210341
- `link:https://doi.org/10.1177/03400352261470844` — **Global patterns and regional disparities in library and information science research productivity** — attempts: 3/3 — IFLA Journal — 2026-08-06 — The article identity is verified, but the recoverable publisher material is restricted to the abstract and references; no substantive copy was found. — https://doi.org/10.1177/03400352261470844
- `historical:id:9f7aa4b8571cb32b` — **Science Diplomacy for Eastern Europe: A New Beginning** — attempts: 3/3 — Science Diplomacy — 2022-01-01 — Identity is verified, but all recovery routes led only to metadata or request-a-copy pages, not substantive evidence. — https://doi.org/10.1126/scidip.adf8092
- `link:https://doi.org/10.1108/fs-06-2015-0036` — **Strategic planning and foresight: the case of Smart Specialisation Strategy in Tuscany** — attempts: 3/3 — foresight — 2016-09-12 — The article identity is verified, but the full paper could not be recovered; available sources expose only structured-abstract material and citations. — https://doi.org/10.1108/fs-06-2015-0036
- `link:https://news.google.com/rss/articles/CBMimwFBVV95cUxOUWR1bzN3YkNacm5ZT3dwUGtzU3BsNnRBcUdyT3hZNkl3X0h1RWlFa2tEYkdTZUktRXFmeG02cGplNEhoYlg0ZlpZWkRJdU1lVTZGWWt0NHR6Q1JKdk1EN1JfSTJuYlpvQ1FFQm1EelpXZVBKV3dJRFZCOWtlN2hCaTEteGxKbW12NVNmY1pvVHE2ZjdyMDhyWXdpcw?oc=5` — **Spanish vaccine maker urges broader EU incentives for innovation** — attempts: 3/3 — Euractiv — 2026-07-28T07:00Z — The Euractiv report is identifiable, but the article body is paywalled and no substantive matching copy was recovered. — https://news.google.com/rss/articles/CBMimwFBVV95cUxOUWR1bzN3YkNacm5ZT3dwUGtzU3BsNnRBcUdyT3hZNkl3X0h1RWlFa2tEYkdTZUktRXFmeG02cGplNEhoYlg0ZlpZWkRJdU1lVTZGWWt0NHR6Q1JKdk1EN1JfSTJuYlpvQ1FFQm1EelpXZVBKV3dJRFZCOWtlN2hCaTEteGxKbW12NVNmY1pvVHE2ZjdyMDhyWXdpcw?oc=5
