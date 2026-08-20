# Scanner architecture — V17

## 1. Cumulative state

`radar.json` is the authoritative cumulative dataset. A/B/C are deduplicated and retained across scans. V17 performs one versioned A/B quality migration to remove historical false positives admitted by older criteria; this is not a rolling deletion policy.

## 2. Strand A discovery

Three discovery channels run without user credentials:

- **OpenAlex** public anonymous scholarly search;
- **Crossref** public anonymous scholarly search;
- **direct institutional crawling** across configured EU, research-policy and geopolitical institutions.

Crossref now starts with a protected priority-journal sweep, then runs the broad query universe. This prevents long institutional crawling from producing a corpus dominated by reports simply because scholarly discovery was too shallow.

## 3. Strand A admission

A must establish substantive:

- EU/European scope;
- R&I / science / innovation / strategic-technology capability;
- geopolitics / geoeconomics / economic security / strategic competition.

For scholarly records, the title+abstract must establish the substantive R&I and geopolitical sides. For institutional reports, one side may be deeper in the body, but the document must contain a supported bridge and cannot be rescued by incidental terms in a generic political report.

## 4. Strand B admission

B requires substantive foresight/horizon-scanning/scenario methodology **plus the same EU + R&I + geopolitical triangle**. Generic transferable methods are no longer sufficient.

## 5. Strand C

Weak-signal discovery starts at the beginning of the scan in parallel with scholarly discovery. Signals remain cumulative and retain the WHAT / WHY / watch-theme structure introduced in V16.

## 6. Runtime

- GitHub job timeout: 70 minutes
- scanner internal budget: 55 minutes
- scheduled cadence: every 12 hours
- A/B V17 upgrade backfill: four months
- later A/B overlap: 14 days
- C rolling window: seven days after the recovery backfill

## 7. Insights UI

The Insights page is evidence-balanced by default. Research publications and institutional reports are distinct sections, with weak signals as a third section rather than the sole default view.
