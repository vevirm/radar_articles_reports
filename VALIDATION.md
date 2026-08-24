# V17.8.1 validation

Validated failure modes and regressions:

- English metadata is rejected for new scholarly/page evidence.
- The table-tennis industry paper is rejected from Strand A.
- Broad peer-reviewed journals are **not** blanket-rejected.
- Quality-profile migration preserves broad historical A/B evidence instead of re-auditing everything from shortened summaries.
- New generic/domain-only foresight papers without a policy/R&I destination remain rejected from Strand B.
- Generic foreign AI/business/health/education news is rejected from C.
- Narrow external strategic shocks may pass the prefilter but still require a Strand-A anchor.
- A plan/funding call does not qualify as a Sovereignty Frontier opening; realised gains can.
- Gap allocation avoids hunting column-A openings while risk cells remain sparse.
- The repeated generic paper-card fallback phrase is absent.
- Bundled corpus is 108 A / 23 B / 9 C / 19 Frontier-only records.

Run: `PYTHONPATH=. pytest -q`
