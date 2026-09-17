# Radar reasoning reform — canonical implementation decisions

This file resolves contradictions/underspecification in `radar_reasoning_spec (2).docx` for implementation. The source specification remains the conceptual basis; these are the engineering resolutions to use in code and tests.

## C-01 Distance bonus

Use:

- distant: `1.20`
- neutral: `1.10`
- familiar: `1.00`

Reason: the worked examples and required score fixtures (78, 89, 80, 73) use 1.20. The isolated `1.3` in R-10 is treated as a specification typo.

## C-02 Shock qualification

A shock qualifies only when all of the following hold:

- `shock_score >= 60`
- `wow >= 4`
- at least one falsifier has been executed
- the shock/risk classification rule is satisfied (the disruptive event itself is absent from the corpus)

The isolated `shocks 75` phrase in R-102 is treated as a typo. The worked 68-point shock, R-34/R-43 and the implementation map all require 60.

## C-03 Object vocabulary normalization

Use `compute.capacity` as the canonical object for the worked phrase `compute.capacity_in_europe`; Europe is represented by `scope`, not by a second object name.

Add the distinct objects used by the specification's own examples when claim backfill reaches them:

- `research_security.espionage_case` -> `research_security`
- `goal.strategic_autonomy` -> a new `strategic_goals` cluster
- `health.microbiome_project` -> `health` (needed to reject the false EUREKA bridge semantically)
- `energy.zinc_air_cell` -> `materials_energy` (needed to preserve the curiosity fixture)
- `funding.route` -> `funding_programme` (role/object class used by the latent-channel example)

No unknown object may be silently invented at runtime. Vocabulary extension is by reviewed file change only.

## C-04 Mechanism vocabulary completion

The initial controlled mechanism vocabulary must include mechanisms used by worked examples/grammars, including:

`regulates`, `requires`, `fast_tracks`, `refers`, `feeds_into`, `secures`, `pre_clears`.

Existing listed mechanisms remain unchanged. Unknown mechanisms fail validation rather than being coerced.

## C-05 Falsifier execution record

Generated text is not an executed falsifier. Store each falsifier as a structured record containing at least:

- `query_id`
- `candidate_id`
- `candidate_fingerprint`
- `query_text`
- `generated_at`
- `executed_at` (null until actually run)
- `result`: `not_yet_run | no_hit | hit`
- `support_record_keys`: list of admitted record keys supporting a hit

A candidate satisfies the executed-falsifier gate only when `executed_at` is set and result is `no_hit` or `hit`. A hit never strengthens a finding.

## C-06 Backfill execution model

Do not add an LLM/API runtime to GitHub. Backfill follows the existing offline Deep Scan operating model:

1. repository prepares a deterministic claims package from stored Deep Scan text;
2. external LLM processes the package;
3. repository validates/imports the returned claims;
4. importer refuses unknown vocabulary, bad record keys, stale fingerprints or invalid claim structure.

No web rebrowse is required for already deep-scanned records.

## C-07 Scanner isolation during migration

Do not implement provisional claims inside `scan_radar.py` during the initial migration. Use a downstream adapter that reads scanner records and emits provisional Level-1/2-only claims. This protects the discovery engine from the reasoning refactor.

## C-08 Publication/falsifier scope

- Level 1 factual strips do not require a falsifier.
- Level 2–5 reader findings require the verification/counter-evidence discipline appropriate to their grammar.
- Trend pairs use their own evidence-floor, composition and flip-line rules rather than being forced through a Level-5 falsifier schema.

## C-09 Cut-over

Reasoning v2 must run in shadow for at least two complete scans with diff reports. No reader surface may depend on v2 until the acceptance gate passes. Cut-over must be reversible without changing scanner evidence, Deep Scan state, or the active corpus.

## C-10 Record-key namespace

Use the repository's existing canonical record-key namespace, not the illustrative
`url:` prefix in the prose specification:

- current URL identity: `link:<url>`
- current DOI identity: `doi:<doi>`
- current fallback identity: `id:<id>`
- historical identities: `historical:link:`, `historical:doi:`, or `historical:id:`

This keeps claims join-compatible with `scripts/deep_read_works.py` and
`scripts/active_corpus.py`. A claims importer must reject `url:` rather than
silently creating a second identity for the same record.

## C-11 Corpus-driven vocabulary extension and methods isolation

The small Appendix-B/example vocabulary is not broad enough to encode the live Deep Scan corpus without forcing unrelated records onto the same object. Vocabulary may therefore be extended by reviewed repository changes when a live backfill batch exposes a genuine missing object. Extensions must remain controlled, clustered and test-validated; runtime invention is still forbidden.

`methods.*` objects belong to the `methods` cluster. They are storage claims for the Strand-B methods library and must never enter world-state graph expansion, trends, shocks, risks or opportunities. Backfill claims on `methods.*` set `attributes.world_reasoning = false`. The same flag is used for the occasional method-only record that was admitted outside Strand B.

## C-12 Self-contained backfill dates

A claim package must carry `record_metadata` from the repository record, including at least title, source, authors, date, type and link. `status_date` may use a more precise date stated in stored Deep Scan text; otherwise it uses `record_metadata.date` as the documented-by date. An extractor must not browse or invent a missing date.

## C-13 Partial source dates

Preserve the precision actually present in repository evidence. `status_date` may be
`YYYY-MM-DD`, `YYYY-MM`, or `YYYY`. Month/year claims must carry
`status_date_precision = "month" | "year"`; exact dates may omit the precision field
or set it to `day`. Never impute the first/last day of a month or year.

A partial date is valid for storage, corroboration and non-temporal reasoning, but it
must not satisfy a rule that requires exact day ordering or an exact scheduled trigger.
Those rules require day precision (or, in a future explicit interval comparison,
non-overlapping date bounds). `deadline` remains day-precision only.
