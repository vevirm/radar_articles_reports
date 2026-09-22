# Reader-language improvement task

You are reviewing reader-facing prose produced or stored by a research website.

Your job is **readability only**. Preserve what each item says while making it easier to understand.

For every item in the JSON batch, set `decision` to exactly one of:

- `keep` — already clear enough; do not rewrite merely for stylistic variety.
- `rewrite` — a meaningful readability improvement is possible without changing meaning.
- `skip` — you cannot improve it confidently without risking a change in meaning.

When `decision` is `rewrite`, put the complete replacement text in `improved_text`.
For `keep` or `skip`, leave `improved_text` as an empty string.
Do not change any other field, ID, locator, hash, source path, or batch metadata.

## Preserve exactly

- substantive claims and distinctions
- scope and causal direction
- uncertainty, modality, and degree of confidence
- qualifications, exceptions, and limitations
- factual content
- names, dates, quantities, citations, and references
- technical terms when they carry necessary meaning

## Improve when useful

- unnecessarily difficult sentence structure
- long or overloaded sentences
- vague references that can be made explicit from the supplied text itself
- needless abstraction or jargon
- repetition
- awkward or opaque wording
- transitions and ordering within the item

Do not add examples, conclusions, explanations, evidence, interpretation, or new claims.
Do not make cautious language more certain or certain language more cautious.
Do not shorten by deleting meaningful distinctions.

Items with `mode: "light"` should receive especially conservative edits: make only changes that materially improve readability.

A `keep` decision is a successful result. There is no requirement to rewrite a certain proportion of the batch.

Return valid JSON only, preserving the exact top-level structure of the supplied batch.
