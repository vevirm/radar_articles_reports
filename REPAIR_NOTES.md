# V17.5.11 repair notes

This package is based on the supplied live radar state. It preserves the scan-state cursors and removes the 10 remaining saved Strand-B records because all 10 fail the V17.5.11 methodology-first gate on their stored evidence. The dedicated B-method discovery lane will refill Strand B with methodology papers that actually satisfy the new contract.

The bundled `radar.json` intentionally retains the previous `quality_profile_version` marker. On the first live V17.5.11 scan, the scanner therefore performs a one-time full inherited A/B quality migration under the repaired gates, using best-effort evidence refresh for thin saved records. This quality migration does not reset source/query/page rotation cursors.

After that migration, normal runs are incremental: the historical accepted corpus is preserved, new discovery rotates through its saved cursor families, and Frontier sparsity only adds bounded extra search budget.

Regression coverage includes the observed teaching/method-transfer false positives, topical papers that merely use scenarios, explicit R&I Delphi methodology, student-vs-researcher mobility, all four Knowledge & people cells, Member-State EU scope, cursor preservation and independent Strand-B method rotation.
