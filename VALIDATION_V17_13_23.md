# Validation V17.13.23

Validation targets for the two-tier window:

1. A/B dated inside four months is retained regardless of merit after admission.
2. A/B dated between four and six months is retained only at Highest source merit (>=93).
3. A/B older than six months is removed even if Highest.
4. Strand C and Matrix-only evidence older than four months are removed.
5. Normal discovery remains on the four-month core; only the bounded extended institutional lane uses the six-month floor.
6. Extended records are visibly marked and preservation logic protects them through month six.
7. Python compilation and synthetic boundary checks pass.

## Executed checks

- `scripts/scan_radar.py`, `manual_ingest.py`, `build_briefing.py`, and `person_backfill.py`: Python compilation PASS.
- GitHub Actions workflow YAML parse: PASS.
- Synthetic boundary test: core ordinary item kept; 4–6 month Highest item kept and marked; 4–6 month ordinary item removed; >6 month Highest item removed: PASS.
- Bundled live state dry prune: 227 A / 24 B / 14 C preserved, zero removals: PASS.
- Python Highest-merit scorer compared with `source_merit.js` on 15 current high-authority records: exact score match PASS.
- Extended discovery source pool: 24 configured institutional sources can potentially reach Highest merit; six rotate per scan after the normal four-month lane.
