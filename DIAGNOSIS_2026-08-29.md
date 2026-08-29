# Diagnosis — 29 August 2026

## 1. Why the six-hour automation looked missing

The V17.13.21 workflow used one fixed GitHub Actions cron: `17 */6 * * *`. That is not "six hours after the last scan"; it is a fixed UTC wall-clock schedule. Hosted scheduled workflows can also be delayed or occasionally missed. There was no catch-up mechanism.

V17.13.22 wakes hourly at minute 17 and checks the last completed scan timestamp. The expensive scanner runs only when at least six hours have elapsed. Manual and push runs still execute immediately. A missed scheduled wake-up therefore gets another opportunity on the next hourly wake-up.

## 2. Why the latest manual scan looked like a no-op

The supplied `radar (38).json` shows a real scan with a 953-second runtime. It evaluated thousands of OpenAlex/Crossref records, but admitted zero new A/B candidates. The run was marked degraded because both scholarly stages reached partial budget limits and several requests were rate-limited (HTTP 429).

The old code stamped `last_updated` at scan start, so the displayed time was not the completion time. V17.13.22 records both start and completion and makes `last_updated` the completion timestamp.

## 3. What was actually lost

Comparison of the V17.13.21 bundled state with the supplied latest JSON:

- Strand A: 224 -> 227
- Strand B: 25 -> 24
- Strand C: 14 -> 14

Exactly four old records disappeared, all dated 2026-04-28. The new rolling four-calendar-month floor is 2026-04-29, so these are expected age-outs rather than overwrite loss:

1. `Ownership changes in the pharmaceutical industry: understanding the 2023 pharma mergers and acquisitions landscape of Europe`
2. `Research security by roundtable: analysis of Germany’s committees for the ethics of security-relevant research`
3. `Beware of GeeksBearing Gifts: Building True EU Frontier AI Sovereignty`
4. `Bibliometric mapping of brand activism: trends, themes, and trajectories`

No still-in-window Strand A/B record from the older bundled state is missing in the supplied latest state.

V17.13.22 now records age-outs explicitly and the GitHub safety step refuses to commit a normal scan if a still-in-window A/B item disappears.

## 4. Separate admission-quality concern

The latest corpus contains some automatically admitted records whose generated "external strategic shock" bridge appears weakly connected to the underlying publication. Examples include an India superconductivity-collaboration paper being bridged to a United States quantum step-change and an Odia-language-processing paper being bridged to a China AI step-change.

This package does not silently delete or reclassify those existing records. That is a separate admission-rule/editorial cleanup issue and should be handled explicitly rather than bundled into a scheduler/data-preservation repair.
