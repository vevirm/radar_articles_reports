# Stage 6 — claim-native detector switch

Stage 6 switches the live *detector backend* from legacy regex role-fillers to the verified claim graph after the required two clean scan-triggered shadow runs.

## What switches

- `scripts/high_order_inference.py` calls the claim-native detector backend when the claim authority and semantic-quality gates pass.
- `scripts/shock_inference.py` derives shock hypotheses from claim-native `dependency_pathway` candidates.
- `scripts/claim_reasoning_live.py` builds the authoritative active view in memory, overlays Deep Scan claims, adds conservative provisional claims for fresh claimless records, runs the claim grammars, and adapts them to the existing lifecycle shell.
- Claim-native missing-link/falsifier searches feed the existing bounded discovery query bank.

## What does not switch yet

Stage 7 owns wow/oddity/selection and reader publication. Therefore Stage 6 keeps a publication compatibility lock:

- claim-native candidates are never reader-eligible in Stage 6;
- no claim-native Level-5 candidate can publish without candidate-specific falsifier execution;
- only candidate IDs already published before the switch are carried temporarily for reader continuity;
- legacy regex detectors cannot create new candidates after a successful claim-native cut-over.

## Fresh-record anti-blindness

A newly admitted current record may arrive before Deep Scan has emitted authoritative claims. Stage 6 creates at most one conservative `origin=provisional` claim for such a record from its already-stored scanner text. Deep Scan remains authoritative and replaces this provisional representation.

- provisional Strand A/frontier claims may enter the primary frontier at conservative merit;
- provisional Strand C is context-only at 0.3 and can never become primary merely because its sentence looks like an event;
- Strand B never enters world reasoning.

## Failure behaviour

Before the first successful claim-native cut-over, legacy remains the rollback path if the claim authority gate is unavailable. Once a claim-native state has been written, a later claim-engine exception or missing authority gate freezes that last claim-native state (`claim_native_hold`) rather than re-entering regex detection. This prevents a transient failure from generating new legacy findings while still allowing the scanner and Deep Scan pipeline to complete.

## Stage boundary

Scanner discovery/admission and Deep Scan evidence authority are unchanged. Public trend split, wow computation, selection, reader labels and final retrace remain for Stages 7–8.
