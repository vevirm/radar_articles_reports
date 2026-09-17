# Reader Language layer

This is a presentation-only language layer for reader-facing analytical pages.

It deliberately does **not** rewrite Main Radar records, Earlier Findings records, source records,
Deep Scan decisions, Excel/Stuff data, scores, dates, links, or reasoning objects.

`approved.json` stores exact-text display alternatives. Every alternative is tied to the SHA-256
fingerprint of the original wording. If the underlying wording changes, the old alternative no
longer matches and is ignored automatically.

Normal publishing never waits for this system. The site always has its original wording as a
fallback. The manual LLM review is optional and can be run whenever the queue is worth reviewing.
