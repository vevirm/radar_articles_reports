# Deep Scan V2 — authoritative, no-API verification rotation

Deep Scan V2 is the Radar's slow authoritative verification layer. The automatic scanner keeps running as the fast discovery path; Deep Scan verifies what each work really is, whether it belongs, what it actually says, and whether its bibliographic/source metadata is correct.

No Anthropic/OpenAI/pay-as-you-go API key is used in GitHub. GitHub prepares files and validates returned files. You give one ZIP at a time to a browsing-capable LLM subscription you already use.

## Trust model

- **Not yet V2 Deep-Scanned:** the automatic scanner record is provisional but remains usable so the Radar keeps updating.
- **V2 KEEP:** the Deep Scan interpretation and verified corrections become authoritative in the active Radar.
- **V2 REVIEW:** the record stays active but is visibly review-pending.
- **V2 DROP:** the raw scanner record is retained for audit, but it disappears from the active Radar and cannot support active rankings, Excel, Matrix/reasoning or derived conclusions.
- **V2 DROP_UNVERIFIABLE:** after the mandatory recovery ladder is exhausted and no defensible trace of the claimed work can be recovered, it is removed from the active Radar in the same way.

Raw scanner history remains in `radar.json`. The public/analytical corpus is generated as `radar_active.json` from raw evidence plus the validated Deep Scan/admission/correction sidecars.

## First run after installing the complete repository

1. Open **Actions** in GitHub.
2. Choose **Radar V2 — Initialise, Validate & Prepare Deep Scan**.
3. Choose **Run workflow**.
4. Wait for it to finish successfully.
5. Open the workflow run and download the artifact **radar-v2-migration-and-deep-scan**.
6. Unzip that artifact once. Inside is `deep_scan_package.zip` containing the first 12 works.

The initial migration does not destructively delete raw records. It validates the active-corpus layer, rebuilds active derived reasoning/Excel, produces a preview report, and prepares the first V2 verification group.

## The normal Deep Scan rotation

### 1. Give one package to the LLM

Upload `deep_scan_package.zip` to a browsing-capable LLM and say:

> Process this Deep Scan V2 package strictly according to INSTRUCTIONS.md. Go deeply and systematically. Do not cherry-pick. Do not stop early on difficult records. Exhaust the mandatory recovery ladder before declaring a work unverifiable. Return deep_scan_results.json or a ZIP containing it.

That is enough. The package itself contains the complete rules, manifest, source material and result structure.

Each package contains **at most 12 works**. Small groups are deliberate: depth is more important than throughput. Partial completion is safe; the LLM must return only carefully completed records and must not fabricate placeholders.

### 2. Upload the returned result

1. Open the repository in GitHub.
2. Open **`deep_scan_inbox`**.
3. Choose **Add file → Upload files**.
4. Upload the returned `deep_scan_results.json` or ZIP.
5. Commit directly to `main`.

That push automatically starts **Deep Scan V2 — Import Returned Results**.

GitHub then:

- validates the returned record identities and evidence audit;
- rejects lazy `DROP_UNVERIFIABLE` results that did not report the full recovery ladder;
- imports authoritative V2 interpretation;
- applies supported metadata/source corrections;
- applies KEEP / REVIEW / DROP / DROP_UNVERIFIABLE and confirmed duplicate status;
- rebuilds the active corpus;
- rebuilds downstream reasoning from active evidence only;
- rebuilds the active Excel snapshot;
- confirms raw A/B/C evidence was not destructively rewritten; and
- automatically prepares the **next 12-work package**.

When the workflow finishes, download its **next-deep-scan-package** artifact. That is the next group. Repeat the same upload-to-LLM → return-to-GitHub cycle.

You do not choose which works come next. The queue is FIFO. Legacy works with no discovery timestamp are treated as the oldest backlog; otherwise works are ordered by `first_seen`. New scanner discoveries enter the Radar provisionally but wait behind work already queued. The importer enforces this too: a returned file may be a carefully completed prefix of the package, but it cannot skip a hard earlier work and import an easier later one.

## Deep Scan is deliberately hard to satisfy

The automatic scanner and old Deep Scan V1 text are hypotheses only. V2 instructions require the LLM to verify bibliographic identity and read enough of the actual work to judge it.

For blocked, thin or difficult records, the package mandates this recovery ladder:

1. supplied URL / redirects;
2. DOI resolution/search, or explicit `not_applicable`;
3. exact-title search;
4. title + author/organisation/year search;
5. publisher/journal/issuing body, institutional repository, author/university page, legitimate preprint/repository or archived official copy;
6. bounded broader identity search using distinctive title fragments, DOI/report identifiers, authors or document numbers.

A failed URL is not a failed work. A search snippet is a locator, not substantive evidence. A related paper is not a substitute. A work may be declared `drop_unverifiable` only after all six steps are audited.

For a recovered work, V2 must provide substantive evidence, not merely scanner prose. KEEP/REVIEW also require a valid WHAT, explanatory reader text, main finding, method/basis and specific Radar relevance.

## What Deep Scan V2 can change

For a verified work it can authoritatively change the active interpretation and admission state, and can correct source-supported metadata such as title, authors, actual journal/publisher/issuing organisation, date, document type and EU relevance.

It cannot change the stable record key, URL identity or DOI identity. It cannot arbitrarily assign a prestigious source tier. When source provenance is corrected, old scanner source-quality fields are invalidated so a wrong label such as `OECD / Tier 1` cannot continue affecting ranking invisibly.

Once V2 is authoritative, old automatic EU/geopolitical evidence arrays, bridge text and strategic classifications are not allowed to continue feeding derived reasoning. The reasoning layer is regenerated from the verified active record instead.

## What happens to the old 300 Deep Scans?

They are preserved. They remain useful reader text while migration proceeds, but the historical corpus is intentionally queued once for V2 re-verification because the old format did not verify admission, provenance and retrieval depth strongly enough.

When V2 is imported, the previous interpretation is retained as audit history inside the reader sidecar rather than silently discarded.

## What happens to new scanner discoveries?

Nothing is blocked. The normal scanner continues to discover/admit material using the current A/B/C criteria and existing rotation/cadence. New records appear with automatic provisional interpretation immediately and join the Deep Scan FIFO queue.

After their V2 turn, the verified result becomes authoritative. If Deep Scan proves that a provisional item is bad or cannot be substantiated after exhaustive recovery, it leaves the active Radar and all active derived products, while raw history remains available for audit.

## Safety / fail-safe behavior

The V2 rebuild refuses to publish an empty or implausibly collapsed active corpus without an explicit override. Deep Scan import also asserts that raw A/B/C/frontier evidence arrays were not destructively modified by the rebuild.

A duplicate is suppressed only while its canonical record still exists. If the canonical raw record later disappears through legitimate retention/rotation, the duplicate fails open to REVIEW rather than silently losing both copies.

The browser prefers `radar_active.json`. If inactive decisions exist and active-corpus verification data cannot be loaded, the page refuses to fall back silently to raw dropped evidence.

## Cost

GitHub never calls an LLM API. No `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, Copilot token or similar billing credential is required. The actual deep reading happens only in the LLM subscription to which you manually give the prepared ZIP.

## Deprecated old one-time actions

The old `ONE-TIME Full Corpus Revalidation`, `ONE-TIME Corpus Cleanup`, `ONE-TIME Downstream Retrace`, and `RESTORE Corpus Backup` workflows are retained only so a full browser upload safely overwrites any previously runnable copies. In V25 their jobs are explicitly disabled. Do not use them. The V2 migration/import workflows perform the reversible active-corpus rebuild instead.
