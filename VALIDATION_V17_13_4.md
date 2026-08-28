# V17.13.4 validation

## Static/source-attention checks

- preferred_q1_nonempty: PASS
- preferred_q1_subset_of_scholarly_source_bank: PASS
- official_eu_domains_configured: PASS
- broad_source_share_at_least_40pct: PASS
- preferred_q1_slots_less_than_total_source_slots: PASS
- official_eu_slots_less_than_total_institution_slots: PASS

- `scripts/scan_radar.py` parses successfully.
- Preferred-journal and official-EU lanes have separate persisted cursors.
- General journal and general institution lanes remain active.
- The configured broad source-first floor is 40%.
- Admission rules were not raised as part of this change.

## Existing focused regression run

`PYTHONPATH=. pytest -q tests/test_v17_13_reader_scanner.py tests/test_v17_5_5_balanced_matrix_priorities.py tests/test_v17_6_4_true_rotation.py tests/test_v17_7_2_source_first_recall.py`

Result: **26 passed, 2 failed**. Both failures are old assertions for superseded V17.7.2 route/version strings; neither concerns V17.13.4 source weighting.

No fresh external radar scan was run for this release.
