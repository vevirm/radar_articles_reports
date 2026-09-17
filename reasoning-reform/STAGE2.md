# Stage 2 — claim vocabulary and validator

Stage 2 adds a downstream claim contract only. It does **not** change scanner
behaviour, Deep Scan decisions, active-corpus construction, legacy inference or
reader pages.

Added:

- `claims_vocabulary.json` — reviewed objects, clusters, mechanisms, absorbers,
  actor/status/direction/kind vocabularies and the role→expected-kind table.
- `scripts/claims_schema.py` — fail-closed validator for individual claims and
  `radar-claims-v1` documents.
- `reasoning-reform/claim_fixtures.json` — the eleven hand-worked records from
  specification section 1.3 represented as 13 claims (two records yield a second
  claim).
- `tests/test_reasoning_reform_claim_schema.py` — positive and negative schema
  tests.

Canonical implementation decision C-10 was added because the prose spec uses an
illustrative `url:` record key while the repository's real stable identity is
`link:` (plus `doi:`, `id:` and historical namespaces). No core file was changed.

Acceptance gate:

1. protected-core hash check passes;
2. original 65-test safety suite passes;
3. Stage-2 claim tests pass;
4. the fixture document validates via the command-line validator.

No production data is written in this stage.
