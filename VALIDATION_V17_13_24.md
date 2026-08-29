# Validation V17.13.24

Validation targets:

1. Inference-only external-shock helper returns no admission when the new policy is active.
2. India superconductivity and Odia-language examples are removed from the bundled public corpus.
3. Indonesian `Strategi Uni Eropa...` and Cyrillic `РОЗВИТОК...` publications are removed and fail the English publication guard.
4. A legitimate English CEPS title containing the typographic `ﬁ` ligature remains eligible.
5. Existing Strand B and Strand C counts are unchanged by the migration.
6. Main-page display logic checks the publication title as well as the reader claim.
7. Four-month core / Highest-to-six-month window logic remains unchanged.
8. Python/JS presentation validation passes.

Expected bundled counts after migration: 185 A / 24 B / 14 C.

## Executed checks

- Bundled migration result: 185 A / 24 B / 14 C: PASS.
- Removed inference-only external A rows: 15; remaining `external_eu_bridge_is_inference` A rows: 0: PASS.
- Removed non-English public A publications: 2; removed audited high-confidence legacy direct-route contaminants: 25; all 209 remaining A/B records pass the publication-time English invariant: PASS.
- Named India superconductivity, Odia-language, Indonesian-title and Cyrillic-title examples absent from public corpus: PASS.
- External inference helper hard-disabled: PASS.
- English CEPS record containing the typographic `ﬁ` ligature remains eligible: PASS.
- Python compilation for scanner: PASS.
- `scripts/presentation_smoke.js`: PASS across main radar, Read, evidence browser, Matrix, priorities, literature, Stuff and glossary.
- No discovery scan was run during this migration.
- Audited direct-route cleanup removed only the explicit 25-title high-confidence legacy set; no blanket revalidation of shortened saved summaries was used: PASS.
