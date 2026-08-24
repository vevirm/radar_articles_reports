# V17.8.3 — English-only + informative claims

This repair keeps the V17.8.2 balanced frontier and fixes two output-quality failures.

## 1. English is now a hard invariant

The old fallback deliberately retained ambiguous Latin-script records when language metadata was missing. That allowed non-English papers through. V17.8.3 reverses that behavior: English must be positively established. The title is checked independently from the abstract/body, and the same gate is applied again to saved A/B/C/frontier records before publication.

In the supplied `radar (19).json`, this removes the Ukrainian-title record and the `Quantum Europe Strategy` record whose body is French.

## 2. Radar and matrix labels now state the message

The prominent label is no longer just the publication title or a generic slogan. Each published record receives a source-backed `core_message` capped at 80 characters. The UI renders it as `This says that …`; the original title, authors, source, date and type are shown as bibliography beneath it. The Sovereignty Frontier uses the same core message rather than wrapping the paper title.
