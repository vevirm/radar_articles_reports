# Radar admission criteria — V17.13.0

## Strand A: substantive EU R&I in strategic context

A paper/report must pass **all three** substantive tests:

1. **Direct Europe/EU relevance.** The evidence is about the EU, European institutions, Member States in a European-policy/R&I context, the European Research Area, Horizon Europe/FP10, or another clearly European R&I system.
2. **R&I substance.** Research, science, innovation, technology capability, research infrastructure, scientific talent, knowledge transfer, R&D funding/governance, or a closely connected R&I-system mechanism is part of what the source is actually about.
3. **Strategic context.** This can be explicit *or implied by triangulation*.

### Explicit strategic route

Direct language such as geopolitics, geoeconomics, economic/research security, strategic competition, strategic autonomy, export controls or a comparable mechanism can establish the strategic side when it is substantively connected to the R&I evidence.

### Triangulated strategic route — literal “geopolitics” not required

A source can pass without the word *geopolitics* when the evidence contains at least **two independent strategic families**, with at least one relational/control family. Current families include:

- dependence, control, sovereignty, access, chokepoints or supply resilience;
- capability gaps, global competition or technological/scientific leadership;
- international research/science coordination or third-country relationships;
- research security, foreign interference, critical infrastructure or dual-use/export-control concerns;
- standards, rule-setting, governance power or external methodologies;
- research-talent competition, brain drain/gain, attraction or retention.

A lone statement that Europe is “competitive”, “innovative”, “leading” or “lagging” is **not** enough.

## Aboutness is source-aware

**Reject incidental mentions, not short documents.** Aboutness must be judged against the text the source actually exposes.

- **Full/long text:** recurrence and section spread can help show that EU + R&I + strategic context is substantive rather than incidental.
- **Abstract only:** do not require nonexistent sections. A coherent title/abstract/keyword connection can be sufficient.
- **Metadata only:** return `insufficient_text` and defer. Missing evidence is not evidence of irrelevance.

A direct same-sentence bridge is helpful but not mandatory for analytical institutional material when the mechanism is established across the title/lead. The triangulated route remains fail-closed for obvious page-type/off-topic noise.

## EU acronym rule

A bare `EU` token is not enough when ambiguous. Prefer unambiguous anchors such as European Union, European Commission, Horizon Europe, European Research Area, or clearly European R&I context. If a source defines `EU` as something else, it cannot establish European Union relevance.

## Diagnostics

Keep the dominant failure/defer reason precise: `insufficient_text`, `no_direct_eu`, `no_ri`, `no_geopolitics`, or `no_substantive_bridge/aboutness` where those legacy codes apply. `no_geopolitics` means **no qualifying strategic context**, not merely “the literal word geopolitics was absent.”

## Publication quality and reader claims

English remains a hard publication invariant. Reader-facing claims should state the source-backed point itself in plain language. Do not pad the claim with researcher biography, institutional boilerplate, method catalogues or generic “this paper examines…” language when the substantive finding can be stated directly.

Titles, authors, source, date, links, abstracts/summaries and review evidence remain available separately.

## Strand B

Strand B is for developed/adapted/extended/refined **reusable futures or forward-looking R&I/technology-analysis methods**. Ordinary method use, descriptive bibliometrics, generic reviews, trend reports and domain prediction systems do not qualify merely because they mention foresight or uncertainty.

## Strand C

Strand C contains externally observable weak signals/developments that can change how Strand-A evidence should be read. It is deliberately secondary. The public corpus applies a **15% maximum share** for C; this is not a quota to fill.

## Time boundary

All public A/B/C evidence uses a hard rolling **four-calendar-month** floor. Saved historical rows or Matrix recovery cannot widen it.

## Matrix hand-off

Every Strand-A record that clears admission is handed to the Matrix classifier with its source-backed evidence. Direction words are classification evidence, not an extra Strand-A gate.
