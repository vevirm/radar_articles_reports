# Radar admission criteria — V17.13.3

## Strand A: substantive EU R&I in strategic context

The **subject of Strand A is EU/European research and innovation in geopolitical or strategic context**. EU relevance is therefore not a loose relevance filter. Normal admission must pass **all three** substantive tests:

1. **Europe/EU subject.** The evidence is about the EU, European institutions, Member States in a European-policy/R&I context, the European Research Area, Horizon Europe/FP10, or another clearly European R&I system.
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

### Exceptional external-shock route

A development outside Europe can still belong when it **materially changes the strategic position of European R&I**. This is deliberately narrow. All of the following are required:

- a major step-change, breakthrough, cutoff or comparable shock in a strategically important R&I capability (for example AI, chips, quantum, biotechnology, frontier compute);
- a major external actor such as the US, China or another relevant capability holder;
- a current admitted EU-context finding in the **same domain**; and
- a **specific one-sentence plain-language bridge** explaining what changes for Europe’s R&I capability, access, dependence or competitive position.

The bridge is stored as an **editorial radar inference**, not attributed to the source. Generic foreign technology news, ordinary product launches and “this matters to Europe” boilerplate do not pass.

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

English remains a hard **evidence** invariant, not a whole-publication invariant. A non-English publication may pass when a source-provided/indexed English abstract, executive summary or equivalent English description is substantive enough to establish the finding and admission bridge. Title-only English metadata is insufficient, and machine translation is not used as admission evidence. Reader-facing claims should state the source-backed point itself in plain language. Do not pad the claim with researcher biography, institutional boilerplate, method catalogues or generic “this paper examines…” language when the substantive finding can be stated directly.

Titles, authors, source, date, links, abstracts/summaries and review evidence remain available separately.

Reader-facing findings and “why it matters” points must be **complete sentences of at most 120 characters**. They must begin with an explicit actor, system or topic. Vague openers such as “this”, “these”, “it”, “they”, “the study”, “the findings” and “the developments” are not admissible display claims. Do not hard-cut a source sentence and do not use ellipses to meet the limit.

## Strand B

Strand B is for developed/adapted/extended/refined **reusable futures or forward-looking R&I/technology-analysis methods**. Ordinary method use, descriptive bibliometrics, generic reviews, trend reports and domain prediction systems do not qualify merely because they mention foresight or uncertainty.

## Strand C

Strand C contains externally observable weak signals/developments that can change how Strand-A evidence should be read. It is deliberately secondary. The public corpus applies a **15% maximum share** for C; this is not a quota to fill. Within the cap, a qualifying external strategic shock is prioritised over ordinary weak signals because the cap must not suppress a genuinely position-changing event.

## Time boundary

All public A/B/C evidence uses a hard rolling **four-calendar-month** floor. Saved historical rows or Matrix recovery cannot widen it.

## Matrix hand-off

Every Strand-A record that clears admission is handed to the Matrix classifier with its source-backed evidence. Direction words are classification evidence, not an extra Strand-A gate.


## Matrix-aware discovery rotation

Matrix imbalance changes **where the scanner looks**, not what it admits. Each run measures current 4×4 Matrix coverage with the production classifier. Cells below the bounded median coverage receive extra OpenAlex/Crossref and specialist-source attention; empty cells receive the strongest weight. The priority list is recomputed during depth waves as new evidence appears. A sparse cell never justifies admitting a weak or off-topic item.

## Source attention (V17.13.4)

Source quality changes **where the scanner looks first**, not what counts as relevant. Each scan reserves extra source-first attention for a verified SCImago Q1 journal shortlist and for official EU reports. At least 40% of source-first attention remains broad, and normal topic/gap rotation continues.

Admission remains source-neutral on substance: the item must still establish EU/European consequence, R&I substance and a geopolitical/strategic mechanism. Prestige can strengthen confidence in evidence, but it cannot replace any of those three links. Unknown journal quartile is never a rejection reason.
