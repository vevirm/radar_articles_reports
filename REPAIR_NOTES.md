# V17.6.3 repair notes

- Tightened B from generic method-development to **futures/foresight method as such**.
- Removed standalone `early warning` as a sufficient futures-method family. Engineering, medicine, finance, infrastructure monitoring and similar predictive systems no longer enter B.
- Delphi, system dynamics, ABM, morphological analysis and similar techniques now need explicit futures/foresight framing plus a genuine method-development claim.
- Revalidated the supplied `radar (9).json`: B changed from 35 items to 1. A and C were left untouched.
- Preserved the complete persisted `scan_state` from the supplied JSON.
- Redesigned main radar cards: <=120-character core message first; source/date and simple why-it-matters second; bibliography after.
- Added a Go back control to Risks & Opportunities and replaced matrix-style wording with plain-language risk/opportunity statements.

## V17.6.3 message-card correction
- Added hard de-spacing for PDF/OCR artefacts in core messages (`E u r o p e`, `C E P S`, `A I`, `R & I`).
- A candidate still containing letter-spaced text is rejected and replaced by a clean semantic message.

- The main-card headline is never character-truncated.
- It must be a complete message of at most 120 characters.
- Ellipses are not used to force a message under the limit.
- If no source sentence fits, the UI constructs a short semantic message from the item’s R&I/geopolitical content.
- Bibliographic titles remain below the message and are not used as the main headline.
