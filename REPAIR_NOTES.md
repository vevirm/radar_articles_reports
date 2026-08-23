# V17.7.4 — dynamic stubborn-cell recovery

The supplied `radar (15).json` shows that V17.7.3 fixed the runtime-allocation problem: the scanner used about 19 minutes, executed 21 matrix-depth waves / 288 gap queries, added 15 Strand A items, 1 Strand B item and 5 Strand C signals. Yet five Frontier cells remain empty: Knowledge-C, Knowledge-D, Infrastructure-D, Conversion-D and Rules-C.

That means the remaining bottleneck is no longer raw depth. V17.7.4 changes *allocation, evidence horizon and source strategy* for stubborn cells without weakening the ordinary A/B corpus rules.

## 1. Matrix depth now reallocates during the scan

V17.7.3 froze the empty-cell list at scan start. If a cell filled in wave 3, later waves could still spend queries on it.

V17.7.4 recomputes the 4×4 Frontier matrix after every depth wave. A cell that fills drops out immediately. The next wave is rebuilt around whatever cells are still empty. Diagnostics record the reallocations and the empty-cell count after current-window depth.

## 2. Stubborn cells get a separate historical evidence lane

If current-window depth still leaves cells empty, up to four minutes are reserved for a matrix-only recovery search over the previous 12 months.

This does **not** change the main A/B corpus date floor. Older recovered items are stored in a separate `frontier_evidence` array and are used only by the Frontier 4×4 evidence classifier/page. They never become normal Strand A items simply because a cell is sparse.

This is especially important for structural questions such as research-talent outflow, foreign expertise dependence, infrastructure chokepoints, scale-up hollowing-out and rule-taking. Strong evidence can fall just outside the rolling corpus floor while remaining highly relevant to the structural matrix.

## 3. Knowledge-D / brain drain gets explicit recovery coverage

Knowledge-D now includes additional formulations around:

- Choose Europe / research careers / brain drain;
- researcher outflow and emigration;
- precarious research careers and retention;
- scientific-workforce loss and competitiveness;
- talent dependence and foreign-trained researchers.

The source plan explicitly includes CESAER, Interface Europe and the European Commission's Marie Skłodowska-Curie Actions / Choose Europe material. Interface and CESAER are also available to the current weak-signal news lane.

## 4. Other stubborn cells get similarly specific formulations

Infrastructure-D adds access-cutoff / no-substitute / compute-chip shortage formulations. Conversion-D adds scale-up relocation, acquisition and hollowing-out formulations. Rules-C adds foreign-rule / US export-rule / standards dependence formulations. Knowledge-C adds international-talent and expertise-dependence formulations.

## 5. Direct institutional weak signals

Recent substantive pages from curated institutions can now enter the same Strand-C candidate pipeline even when Google News does not index them. They still need the normal C topical gate, factual-change/evidence gate and Strand-A anchor. This is intended for things such as new research-talent measures, implementation changes, restrictions, funding commitments or capacity decisions—not generic institutional webpages.

The C discovery version changes to `v17.7.4-direct-institutional-signals`, so the first V17.7.4 run receives one 30-day recovery window and then returns to the normal rolling window.

## 6. State preservation

The bundled `radar.json` is byte-for-byte identical to the supplied `radar (15).json`: 81 Strand A, 20 Strand B and 10 Strand C. The V17.7.2 A/B recall profile is unchanged, so this patch does not trigger a general A/B corpus reset.
