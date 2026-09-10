# v24.7 — European R&I system semantics and country-news recall

This repair keeps the v24.6 principle that **keywords retrieve; relationships admit** and aligns the three strands with the radar's actual mission: observe the European R&I system as a strategic system.

## Strand A — European R&I system evidence

A remains completed research/report evidence. European scope must be source-backed. A can qualify either through a direct geopolitical/economic-security relationship or through a substantive European R&I state variable whose level, distribution, control or trajectory shapes system capacity and strategic position.

The structural route no longer admits a paper because a broad term such as `innovation performance`, `innovation ecosystem`, `R&D intensity` or `doctoral candidates` happens to occur. These support-only terms require a real title-level/study-object relationship. Capital/investment/financing and standards/rule-setting capacity are explicit state-variable families, again as relationships rather than standalone keywords.

## Strand B — methods as the object

B remains geography-independent and method-object first. Morphology for reviews/syntheses/approaches is repaired; method-performance grammar is separated from firm/organisational performance; application domains do not themselves veto a genuine methods paper. A study that merely applies foresight remains out.

## Strand C — dated changes that can move the system

C is a recent concrete event or specific new evidence capable of moving an A-type state variable. Internal member-state developments can qualify without saying `Europe` when their R&I-system materiality is source-backed. External developments still need a defensible transmission channel into European R&I.

Routine-noise filtering is now structural: a real job advertisement is excluded, but a report that another actor is recruiting European researchers is not discarded merely because it contains `recruiting`; likewise, a substantive policy story is not killed because its description mentions a workshop.

Formal proposals qualify only once an accountable institution has actually tabled/published/presented/unveiled them. Future intentions such as `Commission to present ... next week` remain precursors and stay out.

C claim extraction ranks source sentences for observable decisions, commitments and findings, rather than automatically publishing the first aspirational sentence. `Why` text names concrete state-variable consequences for compute, Horizon/FP10 timing, R&D procurement/IP, talent, standards, space and R&I financing where the source text supports those categories.

## European source architecture

The compact Europe/global news core remains separate from a national-media layer. `country_news_sources` is searched with domestic state-variable queries that do not require the article itself to say EU/Europe. This includes Yle News and other curated national/public-service sources. Yle and Euronews also have direct-source crawlers, with bounded lead-paragraph extraction so the C gate can see the actual event rather than only a meta teaser.

Source roles distinguish independent reporting, public-service media, specialist R&I reporting, research analysis and official primary sources. A separate `trusted_primary_c_sources` layer covers accountable international/European institutions already handled by the institutional crawler (OECD, NATO, ESA, CERN, EPO, EIB, UNESCO, World Bank) without spending duplicate Google-News query budget. Source prestige never bypasses relevance/event gates.

## Novelty and publication cap

`anchor_news` no longer truncates C to six candidates before comparison with the saved corpus. It keeps a bounded pre-novelty pool (30 by default); novelty/deduplication happens before the final publication selection. The public C ceiling remains 3. No failed candidate is promoted to fill a lane.

## Deliberately not included in this patch

This patch does **not** change `quality_profile_version` or `signal_quality_profile_version`, so deploying it does not trigger another automatic historical-corpus cleanup. The planned aggressive one-shot corpus + downstream-inference revalidation should be a separate, explicit migration after these criteria/source changes are accepted.

It also does not implement the rolling 8/1/3 discovery-allocation controller yet. That should be added after semantics/source recall are stable, so additional search effort cannot amplify a bad gate.

## Regression status

At packaging time:

- ordinary repository suite: **244 passed, 33 skipped**
- bundled `tests/all_tests.zip`: **255 passed, 33 skipped**

The bundled test archive was rebuilt so GitHub Actions will not repeat the stale-archive failure from the v24.6 deployment.
