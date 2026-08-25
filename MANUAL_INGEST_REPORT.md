# Manual ingest and recall report — V17.11.0

## State integrity

- Authoritative starting state: supplied `radar (21).json`.
- Preserved live-scan timestamp: **2026-08-25T07:34Z**.
- No live scan is claimed by either manual-ingest batch.
- Current corpus after reviewed manual admission: **138 Strand A**, **23 Strand B**, **12 weak signals**.

## Two supplied manual files

### 1. `EU_RI_Key_Papers_May-Aug_2026-2.docx`

Parsed **53 records**: 38 current candidates, 6 forthcoming/unpublished, and 9 context-only records. Its packaging-time batch remains a candidate/recovery comparison: 1 existing corpus match, 1 exact URL seen by the scanner but not admitted, and 36 current candidates absent from the saved corpus/seen-URL ledger. V17.11.0 does **not** retroactively promote those records without reviewed underlying-source evidence.

### 2. `EU_RI_Additions_May-Aug_2026.docx`

Parsed **31 records**: 24 substantive records and 7 weak signals. The V17.11.0 repair re-reviewed this matrix-oriented supplement using evidence bound to the **exact URL supplied in the DOCX**. No search-engine discovery is part of the manual lane. A different resolved primary URL is allowed only when the supplied record itself explicitly needs primary/bibliographic resolution; the original supplied URL remains in provenance.

Latest reviewed batch (`d847131bfe7e-f9ba6538`):

- **17 substantive sources newly admitted**.
- **2 weak signals admitted**.
- **5 deferred** after review.
- **7 retained as context/outside-window**.
- **19 reviewed supplement records now appear in the Sovereignty Frontier matrix** (17 substantive + 2 weak signals).
- All curator cell assignments remain hypotheses (`curator_primary_cell` / `curator_cells`); reviewed source evidence supplies `matrix_dimension`, `quadrant_claimed`, and `quadrant_implied`.
- `quadrant_claimed` and `quadrant_implied` remain separate. Where they differ, the evidence-implied quadrant controls placement.

## Supplement decisions and matrix placement

| ID | Source | Decision | Automated comparison | Matrix placement | Claimed | Implied |
|---|---|---|---|---|---:|---:|
| K1 | Europe as science superpower: what it will take to rival the US and China | ADMITTED substantive | not_found | K-A — Talent windfall | A | A |
| K2 | Prestigious European science funder scraps stricter rules after researcher backlash | Deferred | not_found | — | — | — |
| K3 | European funder must increase capacity to meet the ambition of scientists | Deferred | not_found | — | — | — |
| K4 | Scientists fight back against far-right plans to restrict academic freedom in Germany | Deferred | not_found | — | — | — |
| K5 | Research security by roundtable: analysis of Germany’s committees for the ethics of security-relevant research | Context only | found_in_corpus | — | — | — |
| K6 | Challenges and recommendations for research security: Learning from research ethics and integrity | Context only | not_found | — | — | — |
| K7 | Fragmented Europe: Dealing with China as a technology and innovation power | ADMITTED substantive | scanner_seen_url_not_admitted | K-B — Closed lab | B | B |
| I1 | Europe needs a strategy to close the artificial intelligence compute gap | ADMITTED substantive | not_found | I-B — Expensive mirror | A | B |
| I2 | Revamping Europe’s chips strategy: indispensability, not self-sufficiency | ADMITTED substantive | not_found | I-A — Home chokepoint | A | A |
| I4 | Understanding U.S. Allies’ Current Legal Authority to Implement AI and Semiconductor Export Controls | Context only | not_found | — | — | — |
| I5 | AI export controls are not the best bargaining chip | Context only | not_found | — | — | — |
| C1 | Europe’s venture capital gap and the financing of high-growth firms | ADMITTED substantive | not_found | C-C — Foreign exit | C | C |
| C2 | Exploring the investor landscape for venture capital | ADMITTED substantive | not_found | C-C — Foreign exit | A | C |
| C3 | The European Innovation Council opens to defence and dual-use technologies — amended EIC Work Programme 2026 | ADMITTED substantive | not_found | C-A — Home champion | A | A |
| C4 | Dual-use and Defence Research in Europe | ADMITTED substantive | not_found | C-B — Protected niche | A | B |
| C5 | The growth of dual-use by design research in Europe: Export control risks and challenges | ADMITTED substantive | not_found | C-B — Protected niche | B | B |
| R1 | Council Recommendation on a European Union framework for science diplomacy | ADMITTED substantive | not_found | R-A — Rule-setter | A | A |
| R3 | Does Europe Really Have a Plan for Tech Sovereignty? Tech Policy Press (AI hype and European policymaking series) | ADMITTED substantive | not_found | R-C — Rule-taker | C | C |
| R4 | To achieve tech sovereignty, Europe must not mimic its rivals | ADMITTED substantive | not_found | R-B — Fortress rules | B | B |
| R5 | Simplifying European Union Policy: Tech Sovereignty Package — virtual discussion summary | ADMITTED substantive | not_found | R-B — Fortress rules | — | B |
| W1 | China places 14 EU entities on its export control list, barring dual-use exports with immediate effect — including Rheinmetall (DE), Vigo Photonics (PL), Tatra Trucks (CZ), IHC (NL) and Lafert (IT), plus several technology and research organisations | ADMITTED weak signal | not_found | I-D — Cut supply | — | D |
| W2 | China widens rare-earth and critical-mineral export controls — 10 US firms in June, 14 EU entities in July; IEA warning that full enforcement could place substantial downstream production at risk worldwide | Deferred | not_found | — | — | — |
| W3 | US Department of Commerce shifts NVIDIA H200 review for China from presumption of denial to case-by-case approval subject to a 25% tariff; AI Diffusion Rule rescinded; higher-tier exports approved | Context only | found_in_corpus | — | A | B |
| W4 | Tencent expands cloud computing presence in Europe with new data centres in Germany; Chinese firms reported to be training AI models in Southeast Asia and Europe to work around export controls | Context only | not_found | — | — | — |
| W7 | Mistral raises €830 million in debt for data-centre build-out in France and Sweden; Mistral Compute built in partnership with NVIDIA; flagship models trained on Microsoft Azure infrastructure; Palo Alto office opened to access engineers and Silicon Valley venture capital | Context only | not_found | — | — | — |
| C6 | Europe launches €80 billion investment alliance to scale up tech leaders | ADMITTED substantive | not_found | C-A — Home champion | A | A |
| C7 | Programme for agile and rapid defence innovation: Council and Parliament reach political agreement | ADMITTED substantive | not_found | C-A — Home champion | A | A |
| R2 | National Knowledge Security Guidelines 2026 | ADMITTED substantive | not_found | R-B — Fortress rules | B | B |
| R6 | European Tech Sovereignty | ADMITTED substantive | not_found | R-B — Fortress rules | B | B |
| W5 | ERC Advanced Grants: Nearly €840 million to support Europe’s leading researchers | ADMITTED weak signal | not_found | K-A — Talent windfall | — | A |
| W6 | New ERC Work Programme sets out 2027 funding opportunities | Deferred | not_found | — | — | A |

## Exact-link evidence policy

The manual lane follows this order:

1. Parse the bibliographic record and the exact supplied URL.
2. Deduplicate against admitted corpus and saved scanner history.
3. Retrieve the exact supplied URL when runtime networking is available, or use a reviewed evidence cache only when that review is explicitly bound to the same canonical supplied URL.
4. Resolve to a primary record only for an explicitly secondary/generic/wrong-reference case; preserve the original supplied URL alongside the resolved URL.
5. Apply the same substantive standard: genuine EU/European R&I in geopolitical context. Metadata-only records defer rather than fail relevance.
6. Use curator cells as candidate hypotheses, then classify from reviewed source evidence. Curator cells never force admission or placement.

## Recall diagnostic

The reviewed supplement confirms both discovery and gating gaps. In particular, K7 (`Fragmented Europe`) had been seen by the scanner but was not admitted; the reviewed underlying source now passes the substantive gate and enters K-B. Most other newly admitted supplement records were not found in the saved ledger, so they remain useful exact-URL recall targets for future automated discovery improvements.

The recovery queues remain bounded and do not lower pass-1 precision. A future live scanner run may retry queued exact URLs, but only that real scanner run may update live scan timestamps/cursors.
