# Manual ingest and recall report — V17.11.1

## State integrity

- Authoritative starting state: supplied `radar (22).json`.
- Preserved live-scan timestamp: **2026-08-25T10:58Z**.
- No live scan was run or claimed during this manual review.
- Final corpus: **141 Strand A**, **23 Strand B**, **14 weak signals**.
- Frontier matrix: existing evidence retained, with **5 new Additions III entries**.

## Existing manual-ingest history retained

The newer supplied state already contained three earlier manual batches: the 53-record key-papers list, an initial 31-record Additions batch, and the reviewed 31-record Additions batch that admitted 17 substantive sources and 2 weak signals. Those batches and their timestamps were preserved rather than replayed or rewritten.

## Additions III batch

Input: `EU_RI_Additions_III_May-Aug_2026.docx` (12 records). The DOCX is explicitly matrix-oriented and supplies candidate cell mappings. The manual lane used the curator-supplied URLs as the retrieval manifest. Only ordinary redirects and direct links exposed by those pages were followed; no broad web search, title search, or alternative-version discovery was used.

Batch result:

- **12** records parsed.
- **0** prior admitted-corpus matches in the authoritative pre-ingest state.
- **0** scanner-seen URLs that were not admitted.
- **12** automated discovery misses in the saved state.
- **1** same-batch duplicate (`W18` reuses the `R14` supplied URL after `R14` is admitted); it is not counted as an automated hit.
- **3** new substantive radar admissions.
- **2** new weak-signal admissions.
- **5** new Frontier matrix entries.
- **4** deferred records.
- **1** verified source-based core-gate rejection.
- **1** context/outside-window record.
- **0** forthcoming/unpublished records.

### Item-level decisions

| ID | Decision | Automated comparison | Evidence status | Curator primary cell | Independent matrix result |
|---|---|---|---|---|---|
| I12 | Deferred: primary resolution still required | not found | secondary reference | I-A | — |
| I13 | Deferred: cited secondhand; IRIS primary not directly reachable | not found | secondary reference | C-B | — |
| C11 | **Admitted substantive** | not found | verified primary full text | C-A | **C-C**, claimed A / implied C |
| C12 | **Rejected core gate**: intra-European innovation diffusion, not a substantive external geopolitical/economic-security mechanism | not found | verified primary full text | C-D | — |
| C13 | **Admitted substantive** | not found | verified primary full text | R-C | **I-C**, claimed A / implied C |
| R14 | **Admitted substantive** | not found | verified primary full text | R-D | **R-D**, claimed C / implied D |
| R15 | Deferred: supplied Council PDF could not be retrieved in the environment | not found | metadata only / retrieval limitation | R-D | — |
| W15 | Deferred: Federal Prosecutor primary release not directly exposed by supplied page | not found | secondary reference | K-B | — |
| W16 | **Admitted weak signal** after direct Belgian Federal Prosecutor corroboration from supplied page | not found | verified primary + supplied-page corroboration | K-B | **K-B** |
| W17 | **Admitted weak signal** after direct Helsing/Quantum Systems primary links from supplied page | not found | verified primary + supplied-page corroboration | C-C | **C-A** |
| W18 | Same-batch duplicate of admitted R14 source; no duplicate public item | not found | secondary synthesis | R-C | inherits no forced curator placement |
| W19 | Context only: supplied article predates the primary window | not found | reviewed source | R-D | — |

## New admissions

Substantive radar items:

1. **C11 — European Biotech Act — Commission Staff Working Document C(2026) 3375 final (impact assessment).** The Commission finds a gap between the EU's world-class biotech science and development/market/manufacturing scale, with economic-security, strategic-autonomy and investment implications. Matrix: **Conversion / Productive dependence (C-C)**; claimed destination A, implied observed condition C.
2. **C13 — Europe’s ungoverned space: Military AI and the autonomy that cannot be bought.** The source argues European defence/intelligence users depend on US-controlled AI/cloud infrastructure and estimates a 10–15 year capability gap. Matrix: **Infrastructure / Productive dependence (I-C)**; claimed A, implied C.
3. **R14 — Europe's regulatory double bind.** The source links delayed implementation/assessment capacity and external testing methodologies to regulatory dependence, while enforcement can trigger trade retaliation. Matrix: **Rules / Double loss (R-D)**; claimed C, implied D.

Weak signals:

1. **W16 — SHAPE espionage investigation involving an AI researcher with prior European Space Agency research-centre experience.** Matrix: **Knowledge / Costly autonomy (K-B)**.
2. **W17 — Helsing and Quantum Systems mega-rounds.** Direct company releases verify $1.8bn and $1.2bn rounds used to scale European defence AI/autonomy. Matrix: **Conversion / Opening (C-A)**.

## Curator cell review

The curator's proposed cells were retained as hypotheses and independently checked against source evidence.

- **Survived unchanged:** `R14` **R-D**; `W16` **K-B**.
- **Changed after evidence review:** `C11` **C-A → C-C** (advocated destination A, observed/implied conversion condition C); `C13` **R-C → I-C** (the dominant mechanism is infrastructure dependence); `W17` **C-C → C-A** (observed firms remain European and scale in Europe; foreign capital is retained as a competing interpretation, not the observed outcome).
- **No matrix admission:** I12, I13, C12, R15, W15, W18, W19. Their curator mappings remain stored but do not force placement.

## Recall diagnostic

Five high-quality records were true discovery misses and became new admissions: **C11, C13, R14, W16, W17**. `C12` was also a discovery miss, but direct source review showed that it fails the core pass-1 requirement; this is a **gating outcome after manual recovery**, not a reason to weaken automated precision. `R15` remains a retrieval/environment limitation. I12, I13, W15 and W18 require primary verification from the supplied-link chain and remain deferred/secondary rather than being treated as irrelevant. W19 is context, not a scanner recall target.

The exact-URL recovery queues remain bounded. Reviewed core-gate rejections are not queued, and no live scan cursors/timestamps were advanced.
