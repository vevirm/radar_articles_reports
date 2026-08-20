# Radar Criteria: R&I × Geopolitics + Foresight Methodology — V11

## Date/discovery policy

- **A/B first V11 scan:** search the previous four calendar months through the present. This one-time source-expansion backfill also runs when upgrading an older radar that has not yet recorded the V11 source-expansion marker.
- **A/B later scans:** search from the previous scan with a 14-day overlap to catch late indexing/corrected metadata.
- **A/B corpus:** cumulative. Accepted publications are retained and deduplicated; later discovery windows do not prune history.
- **C first-ever scan:** 7-day news lookback.
- **C later scans:** 48-hour discovery overlap.
- **C corpus:** cumulative after admission. The current window determines what can be newly discovered; previously admitted signals remain visible.

## EU relevance

**Direct:** the EU, member states, European R&I systems, Horizon Europe/FP10, or European strategic/policy choices are an object of analysis.

**Derived:** the publication is not primarily EU-focused but explicitly draws implications for Europe/EU strategy. For Strand B, strong transferable public-sector R&I/S&T/strategic-policy methodology may also qualify as derived.

A passing mention of Europe is insufficient.

## Strand A — R&I under geopolitical change

All four gates must pass:

1. substantive R&I/science/technology **policy or governance** content;
2. substantive geopolitics/economic-security content;
3. a supported R&I ↔ geopolitics/economic-security connection at sentence or document level;
4. direct/derived EU relevance plus an analytical publication type.

Eligible material includes peer-reviewed articles, working papers, policy studies, institutional reports, research papers and substantive policy briefs. Calls, funding notices, project/facility pages, ordinary institutional news, events, jobs, marketing, blogs and opinion are excluded.

Typical A themes include research security/foreign interference, technology sovereignty, economic security, de-risking of S&T cooperation, EU–China research relations, export controls/dual use, fragmentation of global science, transatlantic and US–China technology competition, critical/emerging technologies, Horizon Europe/FP10 participation, research talent and science diplomacy.

## Strand B — foresight methodology

B is methodology-first. The publication must substantially discuss how foresight is designed, conducted, evaluated, institutionalised or integrated with other methods.

Qualifying methods include horizon scanning and weak-signal detection; scenario construction; Delphi and real-time Delphi; backcasting; morphological/cross-impact analysis; participatory foresight; bias/uncertainty/robustness; foresight evaluation and quality criteria; institutional capability; anticipatory governance; strategic intelligence and risk integration.

A trend report, outlook or scenario output alone does not qualify without substantive methodological reflection.

## Strand C — weak signals anchored to A/B

A new signal requires trusted factual reporting, a genuinely new development, European relevance, and a clear anchor to an accepted A/B publication or recurring accepted theme. Relationship labels are `confirms`, `contradicts`, `accelerates`, or `instantiates`.

No anchor = no inclusion.

## Source policy

### Scholarly discovery

OpenAlex and Crossref are queried broadly across the literature. Core R&I/foresight journals rank highest, but relevant journal papers can qualify from other scholarly journals when the substantive A/B gates pass. This avoids recall failures caused by a small hand-maintained journal whitelist.

### Institutional/report discovery

Direct crawling is restricted to a curated source universe in `radar_config.json`: EU institutions and European R&I bodies; major European think tanks and foresight organisations; OECD/comparable organisations; and selected major non-EU policy/research institutions. Recent pages are considered even if their URL does not contain `report`, `paper` or another publication keyword; those URL hints affect priority, not eligibility.

### Quality floor

The scanner still rejects hard-excluded document types and requires substantive content. Standard institutional outputs normally need roughly 1,200+ words; concise Tier-1 analytical briefs can qualify from about 650 words when their publication type and substantive gates are strong.

## Ranking and limits

There is no default post-admission numerical cap (`0 = unlimited`). Ranking is direct EU > derived EU; Tier 1 > core Tier 2 > broad Tier 2 > Tier 3; then publication date. The scanner does not pad a strand with weakly related material merely to reach a target count.
