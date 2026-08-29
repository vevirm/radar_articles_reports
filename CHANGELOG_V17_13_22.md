# V17.13.22

## Fixed

- Scheduled scanning is now catch-up based: the workflow wakes hourly and runs only when the last completed scan is at least six hours old.
- Scan timestamps distinguish start from completion, and `last_updated` means completion.
- Expected four-month age-outs are persisted in `scan_results.aged_out_this_scan`.
- Normal scheduled/manual scans cannot silently drop in-window Strand A/B records; the workflow blocks such a commit.
- The landing page reports completion time including clock time and marks a scan overdue after seven hours.
