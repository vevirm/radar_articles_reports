# V17.13.17 — workflow security hardening without scanner-logic changes

- Kept the scanner logic and `radar.json` unchanged from V17.13.16.
- Pinned every GitHub Action used by the package to an exact verified commit instead of a movable major-version tag.
- Disabled checkout credential persistence, so the working copy has no stored GitHub repository credential while the scanner is running.
- Added a pre-scan check that refuses to run if a repository credential is unexpectedly present.
- Added a post-scan safety gate: only `radar.json` may change; the file must remain valid JSON and stay within deliberately wide catastrophic-size bounds.
- Introduced the GitHub write credential only in the final commit/push step and remove it automatically afterward.
- Split GitHub Pages publication into its own job so page-publishing permission is not present during scanning.
- Kept the 6-hour schedule (`17 */6 * * *`).
- Pinned and de-credentialed the separate one-time person-backfill workflow as well.
- Corrected the README's stale text from 12-hour to 6-hour scheduling.
