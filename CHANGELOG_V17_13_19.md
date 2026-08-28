# V17.13.19 — tolerant hard safety limits

- Kept the 6-hour scan schedule, scanner logic, source rules, reader logic, security credential separation, current `radar.json`, and Stuff source-merit workbook unchanged.
- Changed only the post-scan safety guard so normal large corpus changes do not stop a run.
- Warnings do **not** block saving. They appear when file size or total corpus changes substantially but remains plausible.
- A run is blocked only for clearly abnormal output: invalid/missing JSON; an unexpected file change outside `radar.json`; a `radar.json` size collapse of 75% or more; growth beyond 4x; a main-corpus collapse of 75% or more; main-corpus growth beyond 4x; or an established main strand with at least 10 prior items disappearing completely.
- No new password, lockout mechanism, source filter, admission rule, scoring rule, or content rule was added.
