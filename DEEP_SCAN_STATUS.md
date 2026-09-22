# Deep Scan V2 work status

This file is generated from the authoritative Deep Scan sidecar plus the persistent worker-assignment ledger.
It exists so a new chat or operator can see what has already been verified, what each worker owns, and what now needs hands-on verification.

Scheduling policy: preserve existing worker reservations; fill new slots with fresh **Main Radar first**; then use spare capacity for **Historical Radar**. Access-recovery retries are bounded and throttled so difficult works cannot consume every run.
A validated `defer` counts as one genuine recovery pass. After **3** unsuccessful passes, the work leaves the automatic queue and enters **Hands-on verification needed**.

- Authoritative V2 verified: **1748** (Main **871** + Historical **877**)
- Automatic queue still needing V2 verification: **29** (Main **8** + Historical **21**)
- Currently assigned to workers: **72** (Main **70** + Historical **2**)
- Bounded access-recovery retries still eligible: **0**
- Hands-on verification needed: **8**
- Automatic queue pending and not yet assigned: **19**

## Worker lanes

### Worker A
- Current package: `worker-a-20260922T080933Z-731b2be376e6`
- Assigned unresolved records: **36**
  1. `link:https://doi.org/10.1108/14636681211210341` — A case study on localising foresight in South Africa: using foresight in the context of local government participatory planning — recovery attempt 3/3
  2. `link:https://news.google.com/rss/articles/CBMirgFBVV95cUxOQUZFYldBemM1TGotSVFra1F1UkY5elJsMlBScWNqelRJb2Rnd1BGX3pURVRGNzdUQ2FfQWJvR1JrN1RnbVlQZ21Vbm54c0oydk9ySHpiRkwteGdXTzV1YjBWOVZ6VGNZSk5BZDg2eEhyWURuWmJNQ3RzWHJYeS1xWWVfLTVmNl9USm1iMUpYazNka2FZVHNYLV9RVHYwOFFHUFF4Y0VQbGwwQ3RDekE?oc=5` — EU antitrust chief would consider request from AI firms to coordinate on safety — recovery attempt 3/3
  3. `link:https://doi.org/10.1177/03400352261470844` — Global patterns and regional disparities in library and information science research productivity — recovery attempt 3/3
  4. `link:https://doi.org/10.1108/fs-06-2015-0036` — Strategic planning and foresight: the case of Smart Specialisation Strategy in Tuscany — recovery attempt 3/3
  5. `link:https://news.google.com/rss/articles/CBMimwFBVV95cUxOUWR1bzN3YkNacm5ZT3dwUGtzU3BsNnRBcUdyT3hZNkl3X0h1RWlFa2tEYkdTZUktRXFmeG02cGplNEhoYlg0ZlpZWkRJdU1lVTZGWWt0NHR6Q1JKdk1EN1JfSTJuYlpvQ1FFQm1EelpXZVBKV3dJRFZCOWtlN2hCaTEteGxKbW12NVNmY1pvVHE2ZjdyMDhyWXdpcw?oc=5` — Spanish vaccine maker urges broader EU incentives for innovation — recovery attempt 3/3
  6. `historical:id:9f7aa4b8571cb32b` — Science Diplomacy for Eastern Europe: A New Beginning — recovery attempt 3/3
  7. `historical:id:d436106c01077081` — Measuring the contribution of higher education to innovation capacity in the EU — recovery attempt 2/3
  8. `link:https://doi.org/10.1007/s13563-026-00696-x` — Hybrid development trajectories in former mining regions: collective memory, tourism, and social licence for mine reactivation
  - … plus 28 more in the package manifest

### Worker B
- Current package: `worker-b-20260922T080956Z-b755601da681`
- Assigned unresolved records: **36**
  1. `link:https://era.gv.at/news-items/ec-launches-security-research-and-innovation-campus-at-jrc/` — EC launches Security Research and Innovation Campus at JRC
  2. `link:https://era.gv.at/news-items/ec-launches-call-for-evidence-or-future-eit-regulation-and-strategic-innovation-agenda-2028-2034/` — EC launches call for evidence or future EIT Regulation and Strategic Innovation Agenda (2028-2034)
  3. `link:https://eic.ec.europa.eu/document/download/2c9a91d1-5d64-44ba-b772-6e3f3c1b48fe_en?filename=Chapter_4_EIC_Toolkit_new%20template_v.05%20%28draft%29.pdf` — EIC Innovation Procurement Toolkit
  4. `link:https://www.eit.europa.eu/` — EIT entrepreneurial education: Learn from leaders of European innovation
  5. `link:https://www.ellisinstitute.fi/PIs-2026` — ELLIS Institute Finland recruits 7 new principal investigators | ELLIS Institute Finland
  6. `link:https://www.clean-hydrogen.europa.eu/document/download/0fa1c244-a674-4899-bf4f-f2fc9ba43ae7_en?filename=H2Week_Agenda%20Innovation%20Forum%202026_HE_web%20%28002%29.pdf` — EU Hydrogen Innovation Forum 2026
  7. `link:https://era.gv.at/news-items/eu-launches-first-research-network-on-antisemitism-and-jewish-life/` — EU launches first research network on antisemitism and Jewish life
  8. `link:https://defence-industry-space.ec.europa.eu/eudis-defence-hackathon-spring-2026-meet-winning-teams-driving-innovation-airspace-defence-2026-03-30_en` — EUDIS Defence Hackathon Spring 2026: Meet the Winning Teams Driving Innovation in Airspace Defence
  - … plus 28 more in the package manifest

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
