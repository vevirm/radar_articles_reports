# Deep Scan V2 work status

This file is generated from the authoritative Deep Scan sidecar plus the persistent worker-assignment ledger.
It exists so a new chat or operator can see what has already been verified, what each worker owns, and what now needs hands-on verification.

Scheduling policy: preserve existing worker reservations; fill new slots with fresh **Main Radar first**; then use spare capacity for **Historical Radar**. Access-recovery retries are bounded and throttled so difficult works cannot consume every run.
A validated `defer` counts as one genuine recovery pass. After **3** unsuccessful passes, the work leaves the automatic queue and enters **Hands-on verification needed**.

- Authoritative V2 verified: **1980** (Main **1019** + Historical **961**)
- Automatic queue still needing V2 verification: **58** (Main **22** + Historical **36**)
- Currently assigned to workers: **58** (Main **22** + Historical **36**)
- Bounded access-recovery retries still eligible: **0**
- Hands-on verification needed: **14**
- Automatic queue pending and not yet assigned: **0**

## Worker lanes

### Worker A
- Current package: `worker-a-20260924T115237Z-53a179411e7d`
- Assigned unresolved records: **11**
  1. `link:https://news.google.com/rss/articles/CBMifkFVX3lxTFB3X2lIVGxXMmR6YnJya2xIS2t0WGs0UWZlN0hCNFdQWDAzTVpZWGJVT2VaNnFHa0xDVXpaSG9CNlBWeXVLWXR2M3pNbGxYS0laSWdyN05ETFhCNEp0OEtlOXVSSlBPRDRSUFBPb242Z1JGdVJXZ2xQU1ZEUUxsQQ?oc=5` — THE HACK: EU progress on industrial AI push — recovery attempt 3/3
  2. `link:https://news.google.com/rss/articles/CBMiiAFBVV95cUxPd0hNY0hZU3UySUVzcXFVREJmT0lUQk5QZGJVcXVrck1lYl9BY1UzaDdUamtzbmpKNUNka216YXB6eEc4NTFka0hRR3p4dGFJQjZCdHJTYnNyRlFyUnV4UE0taXRlWWFQdU4ycUtSSVIzVDJwRXJWZTR2ZkJzb3R3M0dJcERGenAt?oc=5` — THE HACK: EU data centre push amid fossil fuel risk — recovery attempt 3/3
  3. `link:https://doi.org/10.1016/j.ejps.2026.107570` — European science for health research needs and priorities — recovery attempt 2/3
  4. `historical:id:9b579a1a37c6d632` — Consumer flash fiction: A methodology to support the early sensing of far-future innovation opportunities
  5. `historical:id:2084a8c4b9bba7a3` — Analysis of Smart Technologies Used in Smart Hotels
  6. `historical:id:256f788e05840f94` — Foresight and strategic decision-making framework from artificial intelligence technology development to utilization activities in small-and-medium-sized enterprises
  7. `historical:id:388a8f406be45f71` — A probabilistic cross‐impact methodology for explorative scenario analysis
  8. `link:https://op.europa.eu/o/opportal-service/download-handler?identifier=8baf21ed-b790-11f1-81de-01aa75ed71a1&format=pdf&language=en&productionSystem=cellar&part=` — DRAFT REPORT - on the proposal for a regulation of the European Parliament and of the Council on the European Union Agency for Cybersecurity (ENISA), the European cybersecurity certification framework, and ICT supply chain security and repealing Regulation (EU) 2019/881 (The Cybersecurity Act 2) - (COM(2026)0011 - C10-0015/2026 - 2026/0011(COD)) - Committee on Industry, Research and Energy - Rapporteur: Markéta Gregorová - Publications Office of the EU — recovery attempt 2/3
  - … plus 3 more in the package manifest

### Worker B
- Current package: `worker-b-20260924T115301Z-6828e4075d6a`
- Assigned unresolved records: **47**
  1. `link:https://doi.org/10.1080/23299460.2026.2731654` — Does the EU AI act align with responsible AI? An evaluation of the European Union’s artificial intelligence act in a responsible research and innovation framework
  2. `link:https://era.gv.at/news-items/ec-proposes-to-restore-full-access-to-horizon-europe-and-erasmus-for-hungary/` — EC proposes to restore full access to Horizon Europe and Erasmus+ for Hungary
  3. `link:https://era.gv.at/news-items/esfri-publishes-position-paper-on-infrastructure-ecosystem/` — ESFRI publishes position paper on infrastructure ecosystem
  4. `link:https://ellis.eu/publication/2025-enhancing-study-level-inference-from-clinical-trial-papers-via-rl-base` — Enhancing Study-Level Inference from Clinical Trial Papers via RL-based Numeric Reasoning
  5. `link:https://era.gv.at/news-items/expert-report-finds-progress-in-open-science-in-era-uneven-and-fragmented/` — Expert report finds progress in open science in ERA uneven and fragmented
  6. `link:https://ellis.eu/publication/2004-knowledge-representation-for-semantic-multimedia-content-analysis-and` — Knowledge Representation for Semantic Multimedia Content Analysis and Reasoning
  7. `link:https://ellis.eu/publication/2002-knowledge-based-multilingual-document-analysis` — Knowledge-Based Multilingual Document Analysis
  8. `link:https://doi.org/10.48550/arxiv.2609.20650` — Multi-center Medical Data Mining with FL-Net - A One-stop Shop for Federated Learning
  - … plus 39 more in the package manifest

### Worker SINGLE
- Current package: `20260923T211548Z-44619dd3ec29`
- Assigned unresolved records: **0**

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
- `link:https://doi.org/10.1080/10438599.2026.2693627` — **Do wage pressure and government R&D stimulate business R&D? Regional level evidence from Europe** — attempts: 3/3 — Economics of Innovation and New Technology — 2026-06-29 — Identity is verified, but only abstract/repository metadata was recoverable; substantive full evidence remained inaccessible. — https://doi.org/10.1080/10438599.2026.2693627
