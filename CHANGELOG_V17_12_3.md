# Changelog — V17.12.3

## Site information architecture

- Reduced the primary site navigation to four components: **Read at least this**, **Main radar**, **Matrix**, and **Risks & opportunities**.
- Renamed the former **Insight Summary** page to **Matrix** and made its one-look block the page-specific “Read at least this” layer.
- Demoted **Radar Insights** to a secondary **Evidence browser**. The route is retained, but it is explicitly described as a view of the Main Radar rather than a fifth component.
- Moved **Latest weak signals** out of top-level navigation; it remains a local jump within the Main Radar.

## Progressive disclosure

- Extended the “Read at least this” pattern beyond the standalone synthesis page.
- Main Radar now opens with a minimum-useful-read callout and a four-component site guide.
- Matrix starts with a dynamic minimum-useful interpretation before the full 4×4 map.
- Risks & opportunities starts with the highest-ranked risk and opening before the full lists.
- The Read at least this page now includes a live layer derived from the same Matrix/Risks builders and links directly into the other three primary components.

## Scanner status wording

- Corrected the homepage status from “Automatic scan · every 12 hours” to **“Scanner · manual run only”**, matching the workflow-dispatch-only GitHub Action.
- Relabeled dynamic scanner condition as **Last run health** to separate execution mode from scan quality.

No scanner run or corpus mutation was performed for this presentation-only release.
