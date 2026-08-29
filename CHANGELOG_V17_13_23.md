# V17.13.23

- Keeps the normal radar as a rolling four-calendar-month core.
- Adds a bounded 4–6 month discovery lane for sources capable of reaching the existing **Highest** source-merit band.
- A 4–6 month A/B candidate is admitted/retained only when its computed source-merit score is at least 93/100.
- Strand C and Matrix-only `frontier_evidence` remain four-month windows.
- Extended A/B rows are marked `extended_retention: true` and `retention_window_months: 6`.
- The normal four-month scan runs before the extended lane, preserving freshness preference.
- Adds separate scan metadata for the preferred floor, six-month Highest floor, extended-source execution and retained extended counts.
- Updates the workflow preservation rule so core A/B cannot disappear before month 4 and Highest extended A/B cannot disappear before month 6.
