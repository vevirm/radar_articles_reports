# Stage 3A — live-batch hardening

The first real 120-record backfill package exposed two implementation facts before any claim import reached Radar:

1. the package was not fully self-contained for the required `status_date` field because it omitted the source record date; and
2. the example-driven vocabulary was too narrow for the live corpus, especially general research-system, AI-governance, research-infrastructure, defence/dual-use, innovation, digital-governance and methods-library records.

This stage fixes both downstream-only issues. It adds repository metadata to future offline packages, expands the reviewed controlled vocabulary from the first live batch, and reserves a `methods` cluster whose claims are explicitly excluded from world reasoning. No scanner, Deep Scan admission, active-corpus, legacy inference or reader code changes here.

The six result files prepared alongside this stage contain one validated claim for each of the 120 packaged records. Their record/source/identity/job hashes are copied from the successful GitHub-generated packages. The first package lacked source dates, so `status_date` was taken by exact `record_key` from the user-supplied repository snapshot; no web access was used. Future packages no longer need that repair because they include `record_metadata.date` directly.
