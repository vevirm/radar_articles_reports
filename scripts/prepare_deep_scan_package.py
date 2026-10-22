#!/usr/bin/env python3
"""Create a self-contained offline Deep Scan V2 ZIP for all non-V2 Radar works."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

try:
    from scripts.deep_read_works import (
        CORPUS, SIDECAR, SourceRead, clean, fetch_source_for_record, iter_records, load_sidecar,
        pending, historical_pending, record_key, identity_hash, scanner_fields,
    )
    from scripts.deep_scan_work_state import (
        DEFAULT_WORK_STATE, DEFAULT_LANE_SIZE, assigned_keys, fill_lane, load_state, manual_verification_keys,
        prioritize_pending_keys, register_package, save_state, sync_verified, update_record_metadata,
        write_status_markdown,
    )
except ModuleNotFoundError:
    from deep_read_works import (  # type: ignore
        CORPUS, SIDECAR, SourceRead, clean, fetch_source_for_record, iter_records, load_sidecar,
        pending, historical_pending, record_key, identity_hash, scanner_fields,
    )
    from deep_scan_work_state import (  # type: ignore
        DEFAULT_WORK_STATE, DEFAULT_LANE_SIZE, assigned_keys, fill_lane, load_state, manual_verification_keys,
        prioritize_pending_keys, register_package, save_state, sync_verified, update_record_metadata,
        write_status_markdown,
    )

FORMAT = "radar-deep-scan-package-v2"
RESULT_FORMAT = "radar-deep-scan-results-v2"
DEFAULT_BATCH_SIZE = 12
DEFAULT_MAX_RECORDS = 12
DEFAULT_WORKERS = 10
ROOT = Path(__file__).resolve().parents[1]
CLAIMS_VOCAB = ROOT / "claims_vocabulary.json"
CLAIMS_FORMAT = "radar-claims-v1"
# Same admission remit as the production scanner; verification remains independent.
EU_RI_SCOPE_POLICY = "eu-ri-scanner-parity-2026-10"

INSTRUCTIONS = r"""# Radar Deep Scan V2 — authoritative verification instructions

## Role

You are the Radar's **authoritative evidence verifier**, not a summariser and not a copy editor.
The automatic scanner is fast and provisional. It can be wrong about the work, source, strand,
European relevance, method contribution, metadata, or even whether the linked object is the work
it claims to be. Existing Deep Scan V1 text is also only prior evidence: check it rather than trust it.

A V2 result may change what the active Radar says and may remove a record from the active corpus.
Therefore every decision must be source-grounded and auditable.

## Scope contract — SAME "what we want" as the automatic Europe/EU R&I scanner

The mission is **European/EU research and innovation intelligence**, not general science, generic
European news, a technology-news feed, or a geopolitical-news filter. Use the **same target of
interest as the automatic scanner** for all strands; Deep Scan differs by verifying primary
sources more rigorously, not by inventing a second, narrower idea of relevance.

- **A / Evidence:** strong, substantive evidence *about* the European/EU R&I system and its
  strategic environment. There are **three independent positive admission routes**, detailed
  below. After common hard gates pass, **any one** qualifies. In particular, systemic European
  R&I evidence does **not** need a geopolitical hook, foreign rival, future-impact prediction,
  explicit sovereignty language, or a scenario. A European paper about R&I policy, research
  careers, researcher mobility, funding, innovation finance, open science, research
  assessment, research infrastructure, collaboration, technology transfer, or related
  European R&I-system mechanisms can qualify **as evidence in its own right**.
- **B / Methods:** a genuinely new, materially improved, scrutinised or newly useful
  **transferable futures, foresight or forward-looking R&I/technology-intelligence method**.
  B is deliberately geography-independent: **do not reject because Europe/EU is absent**.
  A domain-specific application of an existing method, or a generic prediction/AI algorithm
  without a futures/R&I-analysis contribution, is not B.
- **C / Changes:** a *verified new substantive development* that changes, or plausibly
  creates a **source-supported connection to**, Europe's/EU's R&I system or strategic
  research/technology position. Include genuine science/research policy, research funding,
  programmes/instruments, research infrastructure, technology/industrial capability,
  talent, international technological dependencies, regulations, standards and relevant
  external shocks **when their EU R&I connection is evidenced**. It need not already have
  measured effects; label a proposal, decision, announcement or outcome accurately. Exclude
  generic politics/business/tech headlines, routine press, promotional/event pages, and
  unrelated global developments even if someone could imagine an EU impact.

**Same exclusions for all strands:** an incidental EU mention, EU grant acknowledgement,
European address or comparator, geographic keyword, speculative EU bridge, untrusted source,
search snippet, generic sector/local consumer/service application, mere programme listing or
unverified claim does **not** establish admission. Trustworthy official announcements can
establish that an action was announced, not that claimed benefits occurred. Do not turn a
single news item into Strand A evidence merely by calling it a report; do not turn a
completed analytical EU R&I report into Strand C just because it is newly published.

**Decision discipline:** First verify the work and trustworthiness. Then test all applicable
routes for its correct strand against the **substance actually in the source**, not against
scanner keywords or earlier scanner guesses. If a putative A work fails Route 1 (geopolitics),
**explicitly test Route 2 (European R&I states/trajectories) and Route 3 (European R&I-system
research)** before DROP. A valid Route 3 is *not* rejected for missing Route 1/2 wording.
If C, distinguish a new substantive action from a static information page and explicitly
identify the evidenced EU R&I connection. If B, identify the transferable method contribution.

For DROP, the `admission.reason` must identify **which relevant positive route(s) were checked**
and the concrete gate that failed, using evidence from the recovered source; vague reasons
such as "not strategic enough", "no geopolitical significance", "doesn't predict the
future", or "not about European competitiveness" are not enough. If the *substantive*
evidence supports one qualifying route, choose KEEP (or REVIEW for a genuine interpretive
borderline) even if the original scanner chose the wrong strand. Do not rubber-stamp the
scanner either: its decisions remain provisional and weak evidence still fails.

This contract changes **neither** the mandatory retrieval ladder **nor** the bounded three-
pass recovery/terminal-unverifiable policy. Do not park unverified items in REVIEW forever.

## Non-negotiable working rules

1. Process records **in the supplied order**. Do not cherry-pick easy records.
2. Read deeply enough to understand the actual work. Prefer full text or a substantive primary/official
   source whenever it is legally accessible. Do not stop at an abstract if a legitimate full text is available.
3. Treat scanner interpretations and older Deep Scan text as hypotheses, never as ground truth. **But do not discard
   matching first-party source material merely because you cannot rediscover it through a separate web search.** When
   `source_material` was retrieved through `automatic_scanner.source_validation_url`, `source_access`, CELEX, an EP
   document URL, or another scanner source route, inspect that material as evidence. Deep Scan judges the work; it does
   not require the work to win a second discovery contest. Independently verify identity/provenance.
4. Verify bibliographic identity: title, authors/organisation, publication/outlet, year/date, DOI when present,
   and the relationship between the supplied URL and the underlying work.
5. Search snippets are navigation clues only. They are never substantive evidence.
6. Never substitute a related paper, programme page, or secondary story for the claimed work.
7. Preserve uncertainty. Do not turn proposals into outcomes, modelled scenarios into observed facts,
   correlations into causation, or policy intentions into effects.
8. Do not invent a European implication or a WHY.
9. If a record is difficult or blocked, **keep searching through the mandatory retrieval ladder below**.
   A failed URL is not permission to give up.
10. If the claimed work itself still cannot be substantiated after the full mandatory recovery ladder,
    return `drop_unverifiable`. If identity is confirmed but substantive evidence remains inaccessible after all required recovery steps,
    use `defer` rather than inventing a judgement. A defer is coordination-only and leaves the Radar record provisional.

## Hard source-integrity gate

Source trust is a precondition for every strand, not a scoring bonus. State-controlled media / influence outlets,
propaganda channels, anonymous advocacy material, deceptive pseudo-publications and equivalent low-integrity sources
may **never** establish a Radar claim or rescue an otherwise inadmissible record. This applies even when the title/content
looks relevant. Do not treat repetition across outlets from the same controlled information system as independent corroboration.

If the supplied URL is such a source, continue through the retrieval ladder and look for the underlying work or claim in
an independent peer-reviewed journal, a trusted research institution, an accountable international organisation, or another
credible primary/independent source. If the underlying work itself is only a blocked influence/propaganda product and no
trustworthy independent substantiation exists, return `drop`.

Official actor/government material can establish narrow facts about that actor's own formal action (for example the text of a
law, budget, programme, filing or announcement) when provenance is clear, but it must not be treated as independent evidence
that the actor's policy succeeded, that claimed effects occurred, or that contested factual assertions are true. For Strand A
Route 3, the substantive analytical work itself must be a trustworthy evidence product; propaganda/PR cannot qualify merely
because it contains data-like language.

## Mandatory retrieval ladder for difficult/thin/blocked records

For a record whose supplied material is not already a substantial matching primary source, attempt and
record each applicable step. For `drop_unverifiable`, all six standard steps must be reported, plus
`scanner_validation_route` whenever the job supplies one. Each attempt note must
state the actual URL/query/identifier used (or why a step is not applicable) and what happened; do not repeat
generic phrases such as "checked" across the ladder.

1. `supplied_url` — inspect the reader-facing URL.
1a. `scanner_validation_route` — **required whenever `automatic_scanner.source_validation_url`, `source_access`,
   CELEX, or an EP document URL is present.** Inspect that exact first-party scanner route and the package's
   `source_material`. If the package already contains substantial matching first-party text/PDF from that route,
   record this step as successful and cite the material in `recovered_sources`; do not demand rediscovery through
   a different web route. This step is omitted only when the job truly has no scanner-specific validation route.
2. `doi` — resolve/search the DOI when present; if no DOI exists, explicitly record `not_applicable`.
3. `exact_title` — search the exact title in quotation marks.
4. `title_author_year` — search title plus author/organisation/year or other identifying metadata.
5. `official_publisher_or_repository` — search publisher/journal/issuing body, institutional repository,
   author/university page, preprint/repository, EU/agency repository, or legitimate archived official copy.
6. `broader_identity_search` — a bounded final search using distinctive title fragments, DOI fragments,
   authors, report identifiers, programme/document numbers, or other identity clues.

Do not bypass authentication, paywalls or access controls. If full text is paywalled, look for legitimate
repository/author copies and use the strongest matching evidence available.


## Main Radar third actual research-attempt hard-final mode

Some jobs carry `scan_attempt = 3` and `scan_mode = "hard_final"` ONLY after two validated item-level full-recovery attempts have actually been returned and recorded. ZIP generation, downloads, cancellations, missing results and inbox rejection do NOT count as research attempts. This flag is used only for a **Main Radar** work on its third and final automatic Deep Scan issuance. For those jobs, do not repeat an ordinary pass. Before returning `drop_unverifiable`, `defer`, `drop`, or `review` for lack of evidence, perform a stronger final recovery pass:

- exhaust every applicable standard retrieval step and record concrete URLs/queries/results;
- run at least **two materially different broader identity searches** using distinctive title fragments, authors/organisation, DOI/report/document identifiers, or translated/variant title clues when relevant;
- check the most plausible **official publisher/issuing-body site and at least one legitimate repository/archive/author/institutional route** when such routes can exist;
- inspect cached/package-supplied substantive source material and scanner validation routes carefully rather than treating rediscovery failure as disproof;
- cross-check bibliographic identity against at least **two independent identity signals** where possible (for example DOI metadata + publisher page, repository record + author/institution page);
- if the main URL is blocked, broken, moved, or paywalled, actively look for an official mirror, repository copy, archived official copy, preprint/working-paper version, or the issuing body's document registry;
- state in `verification.verification_note` that the **third-attempt hard-final pass** was completed and summarize what extra routes were tried.

This is still bounded: attempt 3 is the last automatic pass. Do not invent evidence, bypass access controls, or relax admission/source-integrity standards merely to avoid a terminal outcome. Historical jobs and Main attempts 1–2 use the normal rules above.

## Admission decision

Return exactly one decision:

- `keep` — the recovered work clearly satisfies the current strand criteria.
- `drop` — the recovered work clearly exists but fails the current criteria **after the
  relevant A/B/C admission routes have been tested**. Record the actual failing gate and
  source-grounded reason; absence of a geopolitical hook alone is never an A failure.
- `review` — the work exists and has real evidence, but admission genuinely requires human judgement.
  REVIEW is not a refuge for laziness or failed retrieval.
- `drop_unverifiable` — after the complete retrieval ladder, the claimed work itself cannot be substantiated.
- `defer` — coordination-only, not an admission judgement. Use only when the work's identity is verified but, after all required recovery steps, substantive evidence remains inaccessible or too thin to support KEEP/REVIEW/DROP. Only each importer-validated complete evidence-recovery `defer` counts as one genuine item-level recovery pass; ZIP issuance or incomplete/invalid worker output NEVER counts. GitHub permits at most three such passes, throttles retries so they cannot dominate worker capacity, and after the third failed pass moves the work to the persistent **Hands-on verification needed** list.

### Strand A — substantive European R&I work

European relevance must be substantive and supported by the work/source. A non-European study does not
qualify merely because the EU is mentioned, used as one comparator, provides a framework/reference,
appears in references, or could have an imagined European implication. The work needs a genuine European
research, innovation, science, technology, industrial-capability, research-policy, research-security or
closely related connection.

Do **not** require the work to state its future importance or to use explicit geopolitical vocabulary.
A can qualify through any of three source-grounded routes:
1. a direct or clearly supported strategic/geopolitical R&I relationship;
2. evidence about a consequential European R&I state or trajectory (for example funding/capital,
   including private/corporate R&D and scale-up finance; capability/performance, including regional
   concentration, widening or intra-European gaps; talent/workforce; infrastructure/compute;
   collaboration/networks; technology transfer/scale-up; strategic-technology capacity in areas such
   as clean tech, critical materials, biotechnology/biomanufacturing; technology dependency/position,
   including distinct US/China dependency mechanisms; or standards/rule-setting); or
3. a high-quality completed evidence-led study/report whose substantive object is the European R&I
   system itself (for example research/innovation policy or governance, funding, careers, mobility,
   collaboration, infrastructure, transfer, assessment, open science, or comparable system mechanisms),
   even when it does not use one of the narrow state-variable relationship phrasings.

Route 3 is not a generic-Europe or generic-technology waiver. Local/service/consumer applications,
ordinary sector competitiveness, programme/event/promotional pages, R&I mentioned only as a covariate or
funding acknowledgement, and work where Europe is merely a comparator remain out. Generic studies of
research practice, researcher habits/attitudes, language use or multilingualism, teaching/learning practice,
or ordinary organisational behaviour also remain out unless the work actually measures a recognised
European R&I-system mechanism such as funding, careers/mobility, workforce/talent, collaboration networks,
infrastructure, transfer/scale-up, assessment/governance, open science, or a comparable system variable.
The point is to verify substantive present-day evidence about the European R&I system; downstream Radar
reasoning may assess why that evidence could matter later.

**Alignment rule with the automatic scanner:** after the common hard guards are satisfied (verified identity, trustworthy
source, substantive European scope, central R&I subject, and a substantive evidence product), **any one** of Routes 1, 2,
or 3 is sufficient for Strand A. Do **not** re-impose Route-1 or Route-2 language on a valid Route-3 work. In particular,
do not drop an otherwise qualifying Route-3 paper/report because it lacks explicit geopolitical vocabulary, does not state
its own future importance, or does not use the scanner's narrow structural state-variable relationship phrasing. Deep Scan
may still drop it for the common hard guards above, bad/weak provenance, local/applied contamination, incidental Europe/R&I,
non-substantive evidence, or identity failure — but not simply for failing the old narrower strategic wording.

### Strand B — reusable methods

B is geography-independent, but it requires a genuine reusable methodological contribution: a new or
materially improved method, transferable analytical framework, measurement/indicator approach, evaluation
design, foresight/scenario method, evidence-synthesis procedure, or similar technique. Merely applying an
existing method/index/framework/model/survey/clustering tool to a case is not enough.
A method focused on foresight, futures, horizon scanning, scenarios or forward-looking
technology/R&I intelligence can qualify without EU scope, but a new algorithm for an
unrelated operational task does not become a futures method by mentioning "forecast".

### Strand C — substantive CURRENT European R&I developments

A C record must establish **both** (a) a real, dateable change/development, and (b) a source-
supported link to Europe/EU R&I systems, research capability, technological/industrial
capacity, cross-border cooperation or research-security/strategic dependencies. The event
can be outside Europe if the external shock has a concrete supported European R&I bridge;
"this technology might someday matter to the EU" is not enough. A source-grounded policy
proposal, decision or announcement may qualify before implementation, but **state its actual
status**, do not report promised outcomes as measured impacts, and distinguish repeated
coverage of one event from a genuinely new development.

Generic institutional, programme, navigation, promotional, vacancy/recruitment,
seminar/event, generic fundraising/launch or listing pages do not qualify merely
because vocabulary matches. An otherwise generic page can qualify only when it
**reports a real new R&I-relevant decision, funding instrument, programme change,
legislative development, research-evidence release, strategic technology change or
comparable substantive event** and supports its European R&I connection. An analytical
study/report is evaluated under A, not pushed to C merely because it has a recent date.

## Historical archive jobs

Jobs with `corpus_scope = "historical"` come from the separate Historical Radar archive. They are reviewed
only after Main Radar work has priority for worker capacity. For these jobs:

- Treat the work as historical structural/context evidence, not as a current Strand C signal.
- A historical row may arrive as A, B, or legacy/unclassified. `keep` / `review` may target only **A** or **B**. Do not target C.
- Apply the same substantive A and reusable-method B standards as above; age is not a reason to keep weak evidence.
- Reader relevance should explain what the work established at the time and why it is useful historical context now,
  without pretending the historical finding is a fresh current development.
- A historical `drop` removes the work from the historical context used by downstream inference, while preserving the
  raw historical archive as an audit record.

## Metadata/provenance correction

Check the scanner's bibliographic/source claims. If a field is demonstrably wrong, return only the correction
that primary/authoritative evidence supports. In particular, do not preserve a prestigious organisation name
because the scanner guessed it. `source` means the actual journal/publisher/issuing organisation for this work.

Allowed corrected fields: `title`, `authors`, `source`, `date`, `type`, `eu_relevance`,
`text_mode`, `source_text_mode`, `event_status`. Never alter `record_key`, URL identity or DOI identity.
Do **not** invent or set `source_tier`; that is a Radar scoring concept, not bibliographic evidence. If the stored tier is unsupported, put `source_tier` in `metadata_correction.unset` so ranking is recomputed from verified provenance.
Any non-empty metadata correction must include a short evidence-grounded `reason`, and the verification block must cite at least one substantive recovered source actually used as evidence.

## Duplicate check

The package may show possible duplicate records. Do not merge merely similar works. If two records are clearly
the same underlying work (same DOI/identical publication or another very high-confidence identity match), use
`duplicate.status = "duplicate"` and provide the exact canonical `record_key`. Ambiguous cases use `review`.

## Reader interpretation

After verification, explain what the recovered work actually says. Reader text limits:
- `reader_title`: max 18 words
- `reader_what`: max 20 words
- `reader_why`: max 20 words or empty
- `reader_more`: 2–5 short sentences, max 135 words

Plain educated English. Explain necessary technical language. WHY must describe a source-supported mechanism;
otherwise leave it blank and set `why_supported` false.

For a recovered work, `verification.evidence_depth` must be exactly one of:
- `full_text_primary`
- `full_text_repository_copy`
- `official_full_document`
- `full_text_or_substantive_primary`
- `substantive_primary_after_recovery`

Use `substantive_primary_after_recovery` only when full text could not legitimately be recovered after the entire
mandatory retrieval ladder, but a substantive matching primary source still supports a defensible decision.
`abstract_only`, `title_only`, snippets, scanner prose, and search-result text are never enough.

## Structured claims for the reasoning layer

For every `keep` or `review` result, also return **1–3 structured claim drafts** in `claims`.
These claims are a machine-readable expression of the same verified Deep Scan finding; they do not
change admission and they must not add facts that are absent from the recovered evidence.

Use only vocabulary present in the supplied `claims_vocabulary.json`. Unknown objects, mechanisms,
actor classes, statuses, directions, scopes or kinds cause the whole result to be rejected. The first
claim is the main finding. A second claim is allowed only for a genuinely distinct object–mechanism
pair. A third is allowed only when a factual qualification/limit itself forms a useful claim.

Each claim draft must contain: `object`, `secondary_objects`, `actor` (`name`, `class`), `mechanism`,
`direction`, `status`, `status_date`, `scope` (`level`, `countries`), `kind`, `qualification`, `text`,
`confidence`, and optional `deadline`, `status_date_precision`, `attributes`. The importer owns and
adds `record_key`, stable `claim_id`, the repository's 0–100 `merit`, `origin=deep_scan`, `era`, and
`provisional=false`; do not invent those system fields.

Date discipline is strict. `status_date` may be `YYYY-MM-DD`, `YYYY-MM`, or `YYYY` only when that
precision is actually supported. For month/year precision add `status_date_precision: "month"` or
`"year"`. Never invent a missing day or month. `deadline`, when present, must be a full `YYYY-MM-DD`.
The first claim's `qualification` must reproduce `deep_analysis.qualification` exactly.

Strand B is the methods library: its claims are stored for provenance but must include
`attributes.world_reasoning=false`. For Strand C, factual event claims may be used as primary evidence;
interpretive/forecast content should be a separate claim with `attributes.reasoning_role="context"` and
`attributes.context_weight=0.3`. Historical claims keep their historical era automatically.

For `drop`, `drop_unverifiable`, or `defer`, return `claims: []`. Do not preserve claims from an earlier
interpretation when the current Deep Scan result does not support them.

## Required result structure

Return exactly one UTF-8 file named `deep_scan_results.json` (or a ZIP containing it):

```json
{
  "format": "radar-deep-scan-results-v2",
  "claims_format": "radar-claims-v1",
  "package_id": "COPY EXACTLY FROM manifest.json",
  "results": [
    {
      "record_key": "COPY EXACTLY FROM JOB",
      "source_hash": "COPY EXACTLY FROM JOB",
      "identity_hash": "COPY EXACTLY FROM JOB",
      "verification": {
        "identity_verified": true,
        "evidence_depth": "full_text_or_substantive_primary",
        "retrieval_attempts": [
          {"step":"supplied_url","outcome":"success","note":"matching journal article page"},
          {"step":"doi","outcome":"success","note":"DOI matched title/authors"}
        ],
        "recovered_sources": [
          {"kind":"publisher_full_text","url":"https://...","title":"...","evidence_used":true}
        ],
        "verification_note": "short audit note"
      },
      "admission": {
        "decision": "keep",
        "target_strand": "A",
        "reason_code": "A_SUBSTANTIVE_EU_RI",
        "reason": "short evidence-grounded explanation"
      },
      "metadata_correction": {
        "fields": {},
        "unset": [],
        "reason": ""
      },
      "duplicate": {
        "status": "unique",
        "duplicate_of": "",
        "reason": ""
      },
      "reader_title": "plain heading",
      "reader_what": "central verified finding/argument/development",
      "reader_why": "supported significance or empty",
      "reader_more": "2–5 short explanatory sentences",
      "deep_analysis": {
        "work_kind": "empirical study / policy report / current development / etc.",
        "research_question": "or empty",
        "main_finding": "plain verified main finding/claim",
        "method_or_basis": "method and evidence actually used",
        "qualification": "important caveat/status/limit",
        "radar_relevance": "specific verified Radar relevance, or why it fails",
        "why_supported": true,
        "confidence": "high"
      },
      "claims": [
        {
          "object": "from claims_vocabulary.json",
          "secondary_objects": [],
          "actor": {"name": "verified actor", "class": "from vocabulary"},
          "mechanism": "from vocabulary",
          "direction": "from vocabulary",
          "status": "from vocabulary",
          "status_date": "YYYY-MM-DD or supported partial date",
          "scope": {"level": "from vocabulary", "countries": []},
          "kind": "action/effect/diagnosis/advocacy",
          "qualification": "copy Deep Scan qualification on claim 1",
          "text": "one factual sentence",
          "confidence": "high/medium/low"
        }
      ]
    }
  ]
}
```

`confidence` is `high`, `medium` or `low`. `target_strand` is `A`, `B` or `C` for KEEP/REVIEW.
For DROP/DROP_UNVERIFIABLE/DEFER it may be the original strand or empty.
For DEFER use `reason_code: "EVIDENCE_ACCESS_LIMITED"`, set `verification.evidence_depth` to `identity_only_after_recovery`, report all required retrieval steps with specific notes, and do not invent reader interpretation.

### Hard validation rules

- KEEP/REVIEW/DROP of a recovered work requires `identity_verified: true` and at least one recovered source
  actually used as substantive evidence. `title_only` and `search_snippet` are not acceptable evidence depths.
- DEFER is allowed only after all required retrieval steps when identity is verified but substantive evidence is still unavailable/insufficient. It is not authoritative and must not contain invented reader prose or metadata corrections.
- `drop_unverifiable` requires all required retrieval steps to be reported. If no DOI exists, the DOI step
  still appears with outcome `not_applicable`. Each step needs a specific audit note (what was searched/opened
  and what happened); repeated generic notes are rejected. A DROP_UNVERIFIABLE result cannot simultaneously
  claim a successful recovery step.
- If the supplied URL fails or is not the work, a recovered KEEP/REVIEW/DROP must explicitly report which
  later recovery-ladder step actually found the matching work.
- Do not return KEEP merely because scanner/legacy Deep Scan prose looks plausible.
- Do not return REVIEW merely because retrieval was hard. If the work cannot be substantiated after the ladder,
  it is `drop_unverifiable`.
- If `duplicate.status` is `duplicate`, the canonical key must be one of the supplied possible duplicate keys and
  admission must be DROP with an appropriate duplicate reason.
- Do not modify `record_key`, `identity_hash` or `source_hash`. V2 import uses the stable identity hash so ordinary scanner wording changes do not invalidate careful source verification.

## Partial completion

A nonempty, properly verified CONSECUTIVE PREFIX is a valid inbox submission.
Return as much verified work as the session can genuinely complete; do not stop deliberately at one record.
Run CHECK_RESULTS.py before upload. GitHub keeps unsubmitted assignments in its queue.
Do not invent a decision to satisfy the count.

Before returning the file, verify every result matches the correct work, the evidence trace is real, the admission
follows A/B/C criteria, corrections are supported, and the JSON is valid.
"""

OFFLINE_CHECKER = '#!/usr/bin/env python3\n"""Offline preflight for a Radar Deep Scan V2 worker result; no network dependency.\nRun from the package root: python CHECK_RESULTS.py deep_scan_results.json\nAllows a nonempty consecutive prefix of assigned jobs; full lane is not mandatory. Substantive evidence\nand claims remain subject to the authoritative GitHub importer.\n"""\nimport json,sys,pathlib\nroot=pathlib.Path(__file__).resolve().parent\nproblems=[]\ntry:\n    path=pathlib.Path(sys.argv[1])\n    d=json.loads(path.read_text(encoding="utf-8"))\n    m=json.loads((root/\'manifest.json\').read_text(encoding="utf-8"))\n    jobs=[]\n    for b in m[\'batches\']:\n        jobs+=json.loads((root/b[\'file\']).read_text(encoding="utf-8"))[\'jobs\']\n    rows=d.get(\'results\',[])\n    if d.get(\'format\')!=\'radar-deep-scan-results-v2\' or d.get(\'package_id\')!=m[\'package_id\']:\n        problems.append(\'format or package_id mismatch\')\n    if d.get(\'claims_format\')!=\'radar-claims-v1\':\n        problems.append(\'claims_format must be radar-claims-v1\')\n    if not isinstance(rows,list): problems.append(\'results must be an array\'); rows=[]\n    if not (1 <= len(rows) <= len(jobs)): problems.append(f\'expected 1..{len(jobs)} results, received {len(rows)}\')\n    for i,r in enumerate(rows):\n        job=jobs[i] if i<len(jobs) else {}\n        expected=job.get(\'required_output\',{})\n        prefix=f\'results[{i}]\'\n        for k in (\'record_key\',\'source_hash\',\'identity_hash\'):\n            if r.get(k)!=expected.get(k): problems.append(f\'{prefix}: incorrect {k} or nonconsecutive order\')\n        v=r.get(\'verification\') or {}; a=r.get(\'admission\') or {}; du=r.get(\'duplicate\') or {}\n        decision=a.get(\'decision\'); depth=v.get(\'evidence_depth\')\n        attempts={x.get(\'step\'):x for x in v.get(\'retrieval_attempts\',[]) if isinstance(x,dict)}\n        if \'supplied_url\' not in attempts: problems.append(f\'{prefix}: missing supplied_url audit\')\n        if decision not in (\'keep\',\'review\',\'drop\',\'defer\',\'drop_unverifiable\'): problems.append(f\'{prefix}: bad decision\')\n        sources=[x for x in v.get(\'recovered_sources\',[]) if isinstance(x,dict) and x.get(\'evidence_used\') is True and x.get(\'url\') and x.get(\'title\')]\n        if decision in (\'keep\',\'review\',\'drop\'):\n            if depth not in (\'full_text_primary\',\'full_text_repository_copy\',\'official_full_document\',\'full_text_or_substantive_primary\',\'substantive_primary_after_recovery\'):problems.append(f\'{prefix}: invalid recovered depth\')\n            if not v.get(\'identity_verified\') or not sources: problems.append(f\'{prefix}: missing identity or substantive recovered source\')\n        if decision in (\'defer\',\'drop_unverifiable\') or depth==\'substantive_primary_after_recovery\':\n            needed={\'supplied_url\',\'doi\',\'exact_title\',\'title_author_year\',\'official_publisher_or_repository\',\'broader_identity_search\'}\n            auto=job.get(\'automatic_scanner\') or {}\n            if auto.get(\'source_validation_url\') or auto.get(\'source_access\') or job.get(\'source_material\',{}).get(\'final_url\'):\n                # A final_url alone is not proof of an explicit scanner-specific route.\n                if auto.get(\'source_validation_url\') or auto.get(\'source_access\'): needed.add(\'scanner_validation_route\')\n            miss=needed-set(attempts)\n            if miss:problems.append(f\'{prefix}: incomplete recovery ladder {sorted(miss)}\')\n            for k in needed&set(attempts):\n                if len(str(attempts[k].get(\'note\',\'\')).strip())<12:problems.append(f\'{prefix}: thin audit note {k}\')\n        if decision==\'defer\':\n            if depth!=\'identity_only_after_recovery\' or not v.get(\'identity_verified\') or a.get(\'reason_code\')!=\'EVIDENCE_ACCESS_LIMITED\':problems.append(f\'{prefix}: invalid defer fields\')\n            if any(r.get(k) for k in (\'reader_title\',\'reader_what\',\'reader_why\',\'reader_more\')):problems.append(f\'{prefix}: defer must not contain reader content\')\n            if (r.get(\'metadata_correction\') or {}).get(\'fields\'):problems.append(f\'{prefix}: defer metadata change\')\n            if any((r.get(\'deep_analysis\') or {}).get(k) for k in (\'work_kind\',\'research_question\',\'main_finding\',\'method_or_basis\',\'qualification\',\'radar_relevance\')):problems.append(f\'{prefix}: defer contains analysis\')\n        if decision==\'drop_unverifiable\' and (v.get(\'identity_verified\') or sources):problems.append(f\'{prefix}: invalid unverifiable evidence\')\n        if du.get(\'status\') not in (\'unique\',\'duplicate\',\'review\'):problems.append(f\'{prefix}: invalid duplicate status\')\n        if du.get(\'status\')==\'duplicate\':\n            keys={x.get(\'record_key\') for x in job.get(\'possible_duplicates\',[]) if isinstance(x,dict)}\n            if decision!=\'drop\' or not du.get(\'duplicate_of\') or du.get(\'duplicate_of\') not in keys:problems.append(f\'{prefix}: invalid canonical duplicate relation\')\n        elif du.get(\'duplicate_of\'):problems.append(f\'{prefix}: duplicate_of must be empty\')\n        claims=r.get(\'claims\')\n        if decision in (\'keep\',\'review\') and (not isinstance(claims,list) or not 1<=len(claims)<=3): problems.append(f\'{prefix}: expected 1–3 claims\')\n        if decision in (\'drop\',\'defer\',\'drop_unverifiable\') and claims!=[]:problems.append(f\'{prefix}: claims must be []\')\n        supplied=attempts.get(\'supplied_url\',{})\n        if decision in (\'keep\',\'review\',\'drop\') and supplied.get(\'outcome\') not in (\'success\',\'found\',\'matched\',\'recovered\',\'resolved\'):\n            recover={\'doi\',\'exact_title\',\'title_author_year\',\'official_publisher_or_repository\',\'broader_identity_search\',\'scanner_validation_route\',\'online_publisher_or_secondary_recovery\',\'package_source_material\',\'web_discovery\',\'publisher_or_alternate_source\',\'publisher_or_official_report\',\'publisher\',\'secondary_syndication_recovery\',\'title_search\',\'repository\',\'source_material\',\'live_source_page\',\'live_primary_source\'}\n            good={\'success\',\'found\',\'matched\',\'recovered\',\'resolved\',\'package_text_examined\',\'source_page_read\',\'source_content_read\'}\n            if not any(x.get(\'step\') in recover and x.get(\'outcome\') in good for x in v.get(\'retrieval_attempts\',[]) if isinstance(x,dict)):\n                problems.append(f\'{prefix}: no successful alternate recovery reported\')\nexcept Exception as e:\n    problems.append(f\'could not validate: {type(e).__name__}: {e}\')\nif problems:\n    print(f\'FAIL: {len(problems)} issue(s)\')\n    for x in problems:print(\' -\',x)\n    sys.exit(1)\nprint(f\'PASS: {len(rows)}/{len(jobs)} consecutive verified results; PARTIAL allowed; GitHub validates evidence and retains unfinished work.\')\n'

CHECKPOINT_TOOL = r'''#!/usr/bin/env python3
"""Durable, offline assignment checkpoint manager. Does NOT perform research."""
import argparse, json, pathlib, sys
root = pathlib.Path(__file__).resolve().parent
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
jobs = []
for b in manifest["batches"]:
    jobs.extend(json.loads((root / b["file"]).read_text(encoding="utf-8"))["jobs"])
expected = [j["required_output"]["record_key"] for j in jobs]
state_path = root / "WORK_PROGRESS.json"

def load():
    if not state_path.exists():
        return {"package_id": manifest["package_id"], "completed": {}}
    d = json.loads(state_path.read_text(encoding="utf-8"))
    if d.get("package_id") != manifest["package_id"]:
        raise ValueError("checkpoint belongs to different package")
    return d

def save(d):
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    tmp.replace(state_path)

parser = argparse.ArgumentParser(description=__doc__)
sub = parser.add_subparsers(dest="cmd", required=True)
sub.add_parser("status")
next_cmd = sub.add_parser("next", help="export only the next unfinished stage, up to six assigned items")
next_cmd.add_argument("--size", type=int, default=6)
next_cmd.add_argument("--output", default="NEXT_STAGE.json")
a = sub.add_parser("add", help="save one completed structured result as JSON")
a.add_argument("result_file")
a = sub.add_parser("assemble", help="create importer-ready JSON from consecutive completed assignments")
a.add_argument("output", nargs="?", default="deep_scan_results.json")
args = parser.parse_args()
try:
    d = load()
    if args.cmd == "add":
        raw = json.loads(pathlib.Path(args.result_file).read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "results" in raw:
            if raw.get("package_id") != manifest["package_id"]:
                raise ValueError("input package_id does not match")
            rows = raw["results"]
        elif isinstance(raw, list):
            rows = raw
        else:
            rows = [raw]
        if not isinstance(rows, list):
            raise ValueError("results must be an array")
        for row in rows:
            key = row.get("record_key")
            if key not in expected:
                raise ValueError(f"unassigned record_key: {key}")
            job = jobs[expected.index(key)]
            for field in ("record_key", "source_hash", "identity_hash"):
                if row.get(field) != job["required_output"].get(field):
                    raise ValueError(f"identity mismatch on {key}: {field}")
            old = d["completed"].get(key)
            if old is not None and old != row:
                raise ValueError(f"already saved with different content: {key}")
            d["completed"][key] = row
        save(d)
    missing = [key for key in expected if key not in d["completed"]]
    print(f"Completed: {len(expected)-len(missing)}/{len(expected)}; remaining: {len(missing)}")
    for i, key in enumerate(expected):
        if key in missing:
            print(f"  remaining position {i+1}: {key}")
    if args.cmd == "next":
        if not 1 <= args.size <= 12:
            raise ValueError("stage size must be between 1 and 12")
        pending = [job for job in jobs if job["required_output"]["record_key"] in missing]
        chosen = pending[:args.size]
        stage = {"package_id":manifest["package_id"], "worker_lane":manifest.get("worker_lane"),
                 "remaining_total":len(missing), "stage_size":len(chosen), "jobs":chosen,
                 "instruction":"Research EVERY job in this stage using the original ZIP recovery rules. Return only real verified results, preserve identities, and add them to CHECKPOINT.py. This stage is NOT inbox-ready."}
        (root / args.output).write_text(json.dumps(stage, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
        print(f"Wrote {args.output}: {len(chosen)} assigned works; {len(missing)} remaining in lane")
    if args.cmd == "assemble":
        prefix = []
        for key in expected:
            if key not in d["completed"]: break
            prefix.append(d["completed"][key])
        if not prefix:
            raise ValueError("No verified consecutive results yet; nothing to assemble")
        out = {"format":"radar-deep-scan-results-v2", "claims_format":"radar-claims-v1", "package_id":manifest["package_id"], "results":prefix}
        pathlib.Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
        print(f"Assembled {args.output}. NEXT: python CHECK_RESULTS.py {args.output}")
except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
    print("FAIL:",e,file=sys.stderr)
    sys.exit(1)
'''

INSTRUCTIONS += "\n\n## CONTINUATION IS MANDATORY, NOT A RESEARCH INVENTORY\n\nWork through EVERY assigned record, including older unresolved items. Never stop after counting or indexing the jobs and present an inventory as a completed scan. Save each real verified result with `python CHECKPOINT.py add one_result.json` and check remaining assignments with `python CHECKPOINT.py status`. If the execution budget ends, hand off `WORK_PROGRESS.json` and the original ZIP; a subsequent session resumes missing assignments only, with neither untouched jobs nor package creation counted as research attempts. Run `python CHECKPOINT.py assemble` after at least one verified consecutive assignment is represented. Then run `python CHECK_RESULTS.py deep_scan_results.json`. Both workers operate independently at the same time; the other lane is not an excuse to stop. Research may require several sessions: checkpoints cannot create autonomous background research.\n\n## IMPORTER-COMPATIBILITY CONTRACT (MANDATORY, checked mechanically)\n\nThese constraints take precedence over informal examples in this ZIP. The GitHub importer\nrejects whole records that violate them, even when the source analysis is useful.\n\n1. Copy `record_key`, `source_hash`, `identity_hash` directly from each job's\n   `required_output`. Never recompute or replace them. Return a verified consecutive prefix in original order. A nonempty prefix is valid; skipped identities or fabricated outputs FAIL.\n2. `verification.evidence_depth` for a recovered keep/drop/review must be EXACTLY one of:\n   `full_text_primary`, `full_text_repository_copy`, `official_full_document`,\n   `full_text_or_substantive_primary`, `substantive_primary_after_recovery`.\n   For `defer` use ONLY `identity_only_after_recovery`. For `drop_unverifiable`,\n   no invented successful recovery step or substantive recovered source is allowed.\n3. `retrieval_attempts` MUST contain `supplied_url` for every result. Every step has a\n   real `outcome` and a specific `note`. If supplied_url fails, record the ACTUAL\n   later successful step (use `success`, not ambiguous outcomes like `limited`,\n   `source_page_read`, `package_text_examined` or `available_in_prior_research_ledger`)\n   and its URL/query. An already retrieved first-party PDF is recorded under\n   `scanner_validation_route` with a truthful `success` only when actually inspected.\n   Also include at least one `recovered_sources` entry with `evidence_used: true`,\n   a non-empty true source URL and title. A bibliography-only page is not full text.\n4. For `defer` and `drop_unverifiable`, report all six steps: `supplied_url`, `doi`,\n   `exact_title`, `title_author_year`, `official_publisher_or_repository`,\n   `broader_identity_search`. If the job contains a scanner-specific validation route,\n   also report `scanner_validation_route`. Use `not_applicable` explicitly when\n   a route cannot apply (e.g. no DOI). Each attempt note must say specifically\n   what was tried and what happened; never invent steps merely to satisfy validation.\n   For `defer`: identity_verified=true, evidence_depth=identity_only_after_recovery,\n   reason_code=EVIDENCE_ACCESS_LIMITED, no corrections, no reader/deep_analysis\n   findings, and claims=[]. If a job cannot be verified, continue the evidence-recovery ladder honestly. Do not invent evidence or submit an incomplete file as complete. Unfinished assignments remain queued; submit verified work promptly and continue when possible.\n5. `duplicate.status` must be EXACTLY `unique`, `duplicate`, or `review`.\n   Use `duplicate` only with decision=`drop`, a nonempty `duplicate_of` equal to\n   an existing canonical key supplied in `possible_duplicates`, and the same DOI\n   or normalized exact title. Otherwise use `unique` with empty `duplicate_of`.\n   Do not label a record duplicate merely because its source_hash recurs or\n   two worker batches have overlapping themes.\n6. Every `keep`/`review` needs 1–3 substantive structured claims using\n   `claims_vocabulary.json`. Every `drop`/`defer`/`drop_unverifiable` must have\n   `claims: []`. Copy the first claim qualification from deep_analysis.qualification.\n7. Run the bundled offline `CHECK_RESULTS.py` against your final JSON before\n   returning it. If it fails, fix the reported errors; a validated consecutive prefix is allowed and must be honestly labeled PARTIAL. Passing this structural preflight is necessary, not\n   sufficient: do not fabricate a citation or recovery attempt to get a pass.\n8. Previously processed records (including old packages 04/06) are not requests to\n   reprocess them. Only complete the current ZIP's current assigned jobs; GitHub\n   handles already-verified and duplicate identities during import.\n"

INSTRUCTIONS += """

## TWO-LANE PARALLEL OPERATING CONTRACT — ALWAYS APPLIES

The GitHub workflow prepares TWO independent worker ZIPs, Worker A and Worker B, for SIMULTANEOUS execution in separate research sessions/agents. A worker must NEVER wait for the other, never perform the other lane's assignments, and never claim the other lane is complete. The full run is only accounted for when BOTH lane submissions independently pass their checks. For the standard 36+36 run this means TWO validated JSON files, each containing exactly 36 results: 72 source-researched decisions in total. Each lane ZIP is self-contained; the other lane must receive its OWN ZIP.

Start at job 1 and proceed through EVERY job across all manifest batch files in order. A session stopping early is an interruption, not completion: save source notes and verified partial JSON, resume where it stopped, and submit a verified consecutive prefix to the GitHub inbox. An inaccessible source is not grounds to invent a DROP/DEFER: exhaust all applicable legitimate retrieval routes and record actual outcomes. Never manufacture successful attempts. A research item is attempted only when genuine documented verification work occurs on THAT item; ZIP issuance, queue placement, an interrupted task, or an untouched item does not count toward the three-attempt ceiling.

For EACH research item, pursue, where applicable: the supplied link/redirect; DOI and identifier lookup; exact title search; title+author+year search; official publisher or institutional repository; scanner-supplied/cached primary text or PDF cross-checked to bibliographic identity; alternate full text/preprint/open repository; trusted syndication/secondary corroboration; and broader discovery if earlier steps fail. Check the actual substantive source, not merely a landing page, before asserting results. Document which routes were tried, their truthful outcome, and why available evidence does or does not support the chosen decision. A blocked route does not authorize a fabricated final conclusion. Never bypass permissions, paywalls, or access controls.

Before returning, execute CHECK_RESULTS.py on the FINAL results file and independently verify the prefix length and identities. A validated nonempty consecutive prefix may be submitted; retain unattempted jobs in the queue. Submit verified consecutive-prefix results passing structural checks and substantive evidence rules. The GitHub importer remains authoritative for final admission.
"""

INSTRUCTIONS += """

## TWO-LANE PARALLEL OPERATING CONTRACT — ALWAYS APPLIES

The GitHub workflow prepares TWO independent worker ZIPs, Worker A and Worker B, for SIMULTANEOUS execution in separate research sessions/agents. A worker must NEVER wait for the other, never perform the other lane's assignments, and never claim the other lane is complete. The full run is only accounted for when BOTH lane submissions independently pass their checks. For the standard 36+36 run this means TWO validated JSON files, each containing exactly 36 results: 72 source-researched decisions in total. Each lane ZIP is self-contained; the other lane must receive its OWN ZIP.

Start at job 1 and proceed through EVERY job across all manifest batch files in order. A session stopping early is an interruption, not completion: save source notes and verified partial JSON, resume where it stopped, and submit a verified consecutive prefix to the GitHub inbox. An inaccessible source is not grounds to invent a DROP/DEFER: exhaust all applicable legitimate retrieval routes and record actual outcomes. Never manufacture successful attempts. A research item is attempted only when genuine documented verification work occurs on THAT item; ZIP issuance, queue placement, an interrupted task, or an untouched item does not count toward the three-attempt ceiling.

For EACH research item, pursue, where applicable: the supplied link/redirect; DOI and identifier lookup; exact title search; title+author+year search; official publisher or institutional repository; scanner-supplied/cached primary text or PDF cross-checked to bibliographic identity; alternate full text/preprint/open repository; trusted syndication/secondary corroboration; and broader discovery if earlier steps fail. Check the actual substantive source, not merely a landing page, before asserting results. Document which routes were tried, their truthful outcome, and why available evidence does or does not support the chosen decision. A blocked route does not authorize a fabricated final conclusion. Never bypass permissions, paywalls, or access controls.

Before returning, execute CHECK_RESULTS.py on the FINAL results file and independently verify the prefix length and identities. A validated nonempty consecutive prefix may be submitted; retain unattempted jobs in the queue. Submit verified consecutive-prefix results passing structural checks and substantive evidence rules. The GitHub importer remains authoritative for final admission.
"""

INSTRUCTIONS += r"""

## PRIMARY MISSION — PRACTICAL RADAR QUALITY CHECK (READ FIRST)

THIS ZIP IS A RESEARCH EXECUTION TASK, NOT AN INVENTORY OR ANOTHER HANDOFF.
For EVERY assigned record, do your BEST reasonable verification of (1) bibliographic identity
(title, author/issuer, year, publisher, DOI/URL when available), (2) whether the actual
source content broadly supports its described topic, summary and important claims, and
(3) whether it qualifies for Radar's relevant strand. This is APPROXIMATE, source-grounded
quality control, NOT an exhaustive independent academic review of every work.

Start from the scanner-supplied primary excerpts, official source pages, publisher
abstracts, executive summaries and accessible full text. Use the strongest readily
available matching evidence; cross-check identity against an independent official or
publisher listing when practical. Read full text when easily available, but do not
spend a whole assignment budget chasing every paywalled PDF. Use the 14 discovery
routes as a TOOLBOX for difficult cases, not as mandatory searches for every item.
Escalate only when identity, content or relevance cannot reasonably be judged.

Make a truthful KEEP/DROP/REVIEW decision as soon as adequate substantive matching
evidence supports it. Preserve limitations and label proposals as proposals.
Do not invent citations, claims, full-text access, or completed searches. If evidence
remains inadequate, use the strict DEFER/DROP_UNVERIFIABLE importer fields and required
recovery audit, or save the assignment as unfinished for continuation. Do not pad counts.

IMPORTANT IMPORTER REALITY: The importer still demands a matching substantive primary
source and controlled claims for KEEP/REVIEW. A bare headline or unsupported abstract
is not automatically sufficient for a KEEP; prefer meaningful abstract + substantive
methods/findings or official summary, and record the actual evidence read accurately.
The canonical evidence_depth enum and verification audit below remain binding.

PROCESS ALL WORK, NOT JUST THE FIRST ARTICLE: finish each of the 6-record internal
stages, save verified records, then immediately continue to the next stage. Each worker
returns EXACTLY the assigned manifest count in one radar-deep-scan-results-v2 JSON
with claims_format radar-claims-v1, correct job identities and order. Run CHECK_RESULTS.py
before return. Worker A and Worker B process their distinct ZIPs simultaneously when
external execution supports parallel work. A ZIP alone cannot run background agents.

Older queued research is legitimate. The per-item three-attempt rule counts only real,
documented substantive recovery attempts; ZIP issuance, skipped items and interrupted
sessions do not count.

## NORMAL DEEP SCAN: EXPANDED SOURCE RECOVERY (inspired by PUSH HARDER)

These are FALLBACK recovery options for ordinary Worker A and Worker B research, not a per-item mandatory 14-search checklist. A meaningful matching primary excerpt, published abstract with substantive methods/findings, or official summary can support a proportionate decision when the importer evidence requirements are met. Use the first reliable, substantively sufficient matching primary source when available; do not waste effort on irrelevant routes after a source is verified. When primary evidence remains unavailable or too thin, pursue and document **every applicable** category below before a terminal access-limited decision. Record queries/URLs and real outcomes, including why a category cannot apply:

1. `prior_attempt_audit`: inspect scanner-supplied text and previous research notes; distinguish real completed research from ZIP issuance or untouched queue entries.
2. `supplied_url_redirects`: follow supplied URL, legitimate redirects, canonical URL, attachment, HTML/PDF links.
3. `doi_registry_publisher`: DOI resolver and bibliographic registry, original publisher, article or report landing page.
4. `exact_title_variants`: exact title and distinctive fragments, punctuation or translated variants.
5. `title_author_year_identifiers`: author, organisation, year, report/article numbers, grant/project ID, ISBN/ISSN if applicable.
6. `open_access_resolvers`: legitimate OA metadata and available official or deposited copies.
7. `institutional_repositories`: university, EU, funder, national and discipline repositories.
8. `author_research_group_pages`: author or laboratory publication lists and research group websites.
9. `preprint_accepted_manuscript`: lawfully public preprints, accepted manuscripts, working papers or deposited versions of the SAME work.
10. `journal_issue_toc_supplements`: journal issue contents, HTML/XML, supplementary files, attachments.
11. `citation_graph_related_versions`: bibliographies/citation index routes identifying another genuine version of the SAME work, not a superficially related study.
12. `official_document_repositories`: EU institutional/document registers, publication offices and issuing-body registers when relevant.
13. `alternate_formats_and_archives`: public official archives, existing cached primary text, legitimate PDF/HTML/DOCX mirrors.
14. `multilingual_acronym_report_number`: translated titles, alternate acronyms, report numbers and regional-language variants.

If all applicable categories still leave source identity or substance unresolved, do TWO further nonduplicative search challenges: (A) identify and actually pursue at least three genuinely new targeted retrieval strategies, then (B) identify and pursue at least two more different strategies. These challenge passes apply to a difficult item, not automatically to all easily verified works. Preserve a concrete audit of routes actually tried; never claim imaginary success or use fabricated `not_applicable` notes to satisfy schema. Do not bypass authentication, paywalls, robots exclusions or access controls.

**Importer audit translation:** the canonical six-step `verification.retrieval_attempts` ladder in this ZIP remains MANDATORY for `defer` and `drop_unverifiable`. The fourteen search categories above are deeper research guidance, NOT new required JSON enum keys; record concrete actions in the existing audit step notes, add factual retrieval attempts where supported and explain any extra routes in `verification.verification_note`. Do not invent new evidence-depth, decision, actor, mechanism or duplicate enum values. If an official primary source is already recovered and substantively read, proceed to the justified KEEP/DROP decision without pretending to exhaust irrelevant routes.

**Checkpoint discipline:** process ALL assigned jobs, saving completed verified JSON records and open research notes across internal batches. Resume from the first unfinished job as capacity allows. Verified nonempty consecutive-prefix output IS `deep_scan_results.json` ready for inbox after validation. No padding with unsupported DROP/DEFER; continue to research as many records as possible. When both concurrent lanes are assigned, A and B may submit verified partial outputs independently; the queue retains unfinished assignments.
"""

INSTRUCTIONS += "\n\n## BEST-EFFORT CONSECUTIVE PREFIX — IMPORT-READY\n\nResearch as many assignments as possible in order (up to the whole 36-item lane). A nonempty, well-supported consecutive prefix is a VALID inbox submission. Aim to cover the full lane but never invent evidence or pad results. Do not waste your session on another handoff/inventory: do the bibliographic and content plausibility checks. Run CHECK_RESULTS.py; a PASS for e.g. 7/36 is a valid PARTIAL submission, not 36/36 completion. GitHub preserves unsubmitted assignments for later scanning.\n"


START_HERE = r"""RADAR DEEP SCAN V2 — EXECUTE THE RESEARCH (NOT A HANDOFF)

Research all assigned records you can reasonably check in this session. Aim for the full lane,
but if time is limited, SUBMIT THE GENUINELY COMPLETED CONSECUTIVE PREFIX of records.
Do not stop after one record just to produce a checkpoint; keep researching while able.
Check bibliographic identity, substance and Radar relevance using credible available sources.
Apply additional recovery methods when necessary, not exhaustively to every easy record.
Return `deep_scan_results.json` in the exact V2 schema and original assignment order.
Run `python CHECK_RESULTS.py deep_scan_results.json` before returning.
A PASS showing N/36 permits an importer-ready PARTIAL result; it is not falsely called 36/36.
GitHub tracks and reassigns unfinished records. Never invent evidence or research attempts.
"""


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def package_id_for(rows: list[tuple[str, str, str, dict[str, Any], str]], lane: str = "") -> str:
    seed = "\n".join(f"{key}|{h}" for _strand, key, h, _r, _reason in rows)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    prefix = f"worker-{lane.lower()}-" if lane else ""
    return f"{prefix}{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{digest}"


def source_for(item: tuple[str, str, str, dict[str, Any], str]):
    strand, key, h, r, reason = item
    src = fetch_source_for_record(r)
    return strand, key, h, r, reason, src


def _norm_title(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()


def _doi(row: dict[str, Any]) -> str:
    value = clean(row.get("doi"))
    if not value:
        link = clean(row.get("link") or row.get("url"))
        m = re.search(r"doi\.org/(10\.\d{4,9}/[^?#\s]+)", link, re.I)
        value = m.group(1) if m else ""
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I).lower().rstrip("/")


def duplicate_index(doc: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    """Find exact DOI/title duplicates without a quadratic full-corpus scan.

    Preserve the old ordering, same-key exclusion, DOI-before-title reason and
    eight-match cap; indexing only removes unrelated candidate comparisons.
    """
    rows = [(strand, r) for strand, r in iter_records(doc)]
    details = [(record_key(row), _doi(row), _norm_title(row.get("title") or row.get("headline")))
               for _strand, row in rows]
    by_doi: dict[str, list[int]] = {}
    by_title: dict[str, list[int]] = {}
    for i, (key, doi, title) in enumerate(details):
        if not key:
            continue
        if doi:
            by_doi.setdefault(doi, []).append(i)
        if len(title) >= 24:
            by_title.setdefault(title, []).append(i)

    out: dict[str, list[dict[str, str]]] = {}
    for i, (_strand, row) in enumerate(rows):
        key, doi, title = details[i]
        if not key:
            continue
        matching_positions = set(by_doi.get(doi, [])) if doi else set()
        if title and len(title) >= 24:
            matching_positions.update(by_title.get(title, []))
        matches: list[dict[str, str]] = []
        for j in sorted(matching_positions):
            if i == j:
                continue
            other_key, other_doi, other_title = details[j]
            if not other_key or other_key == key:
                continue
            reason = "same_doi" if doi and other_doi and doi == other_doi else (
                "exact_normalized_title" if title and other_title and len(title) >= 24 and title == other_title else ""
            )
            if reason:
                other_strand, other = rows[j]
                matches.append({
                    "record_key": other_key,
                    "strand": other_strand.replace("strand_", "").upper(),
                    "title": clean(other.get("title") or other.get("headline")),
                    "source": clean(other.get("source")),
                    "reason": reason,
                })
            if len(matches) >= 8:
                break
        if matches:
            out[key] = matches
    return out

def same_key_variants(doc: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for strand, row in iter_records(doc):
        key = record_key(row)
        if not key:
            continue
        out.setdefault(key, []).append({
            "strand": strand.replace("strand_", "").upper(),
            "automatic_scanner": scanner_fields(row),
        })
    return {k: v for k, v in out.items() if len(v) > 1}

def annotate_scan_attempts(jobs: list[dict[str, Any]], state: dict[str, Any] | None) -> None:
    """Annotate from validated actual failed research passes, never ZIP issuance."""
    state_records = state.get("records", {}) if isinstance(state, dict) else {}
    for job in jobs:
        row_state = state_records.get(job["record_key"], {}) if isinstance(state_records, dict) else {}
        try:
            previous_package_attempts = max(0, int((row_state or {}).get("recovery_attempts") or 0))
        except (TypeError, ValueError):
            previous_package_attempts = 0
        scan_attempt = min(3, previous_package_attempts + 1)
        job["scan_attempt"] = scan_attempt
        job["scan_mode"] = "hard_final" if job.get("corpus_scope") == "main" and scan_attempt == 3 else "standard"


def build_job(row, ordinal: int, sidecar: dict[str, Any], dupes: dict[str, list[dict[str, str]]], variants: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    strand, key, h, r, reason, src = row
    existing = sidecar.get("records", {}).get(key)
    scope = "historical" if clean(r.get("_deep_scan_scope")).lower() == "historical" else "main"
    if strand.startswith("historical_"):
        strand_label = strand.rsplit("_", 1)[-1].upper()
    else:
        strand_label = "A" if strand == "frontier_evidence" else strand.replace("strand_", "").upper()
    return {
        "job_number": ordinal,
        "record_key": key,
        "source_hash": h,
        "identity_hash": identity_hash(r),
        "corpus_scope": scope,
        "strand": strand_label,
        "queue_reason": reason,
        "automatic_scanner": scanner_fields(r),
        "same_record_key_variants": variants.get(key, []),
        "legacy_deep_scan": existing if isinstance(existing, dict) else None,
        "possible_duplicates": dupes.get(key, []),
        "source_material": {
            "read_mode": src.mode,
            "final_url": src.final_url,
            "retrieval_note": src.note,
            "text": src.text,
        },
        "required_output": {
            "record_key": key,
            "source_hash": h,
            "identity_hash": identity_hash(r),
            "verification": {
                "identity_verified": False,
                "evidence_depth": "",
                "retrieval_attempts": [],
                "recovered_sources": [],
                "verification_note": "",
            },
            "admission": {"decision": "", "target_strand": "", "reason_code": "", "reason": ""},
            "metadata_correction": {"fields": {}, "unset": [], "reason": ""},
            "duplicate": {"status": "unique", "duplicate_of": "", "reason": ""},
            "reader_title": "", "reader_what": "", "reader_why": "", "reader_more": "",
            "deep_analysis": {
                "work_kind": "", "research_question": "", "main_finding": "", "method_or_basis": "",
                "qualification": "", "radar_relevance": "", "why_supported": False, "confidence": "low",
            },
            "claims": [],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Create an authoritative offline Deep Scan V2 ZIP")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--historical", type=Path, default=None, help="Historical archive used to fill spare worker capacity after Main Radar priority")
    ap.add_argument("--sidecar", type=Path, default=SIDECAR)
    ap.add_argument("--output-dir", type=Path, default=Path("deep_scan_out"))
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    ap.add_argument("--max-records", type=int, default=DEFAULT_MAX_RECORDS, help="Maximum records in a legacy single package; default 12; 0 means all pending")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--no-fetch", action="store_true", help="Do not pre-retrieve linked source pages/PDFs")
    ap.add_argument("--lane", choices=["A", "B", "a", "b"], default="", help="Prepare one persistent parallel worker lane")
    ap.add_argument("--lane-size", type=int, default=DEFAULT_LANE_SIZE, help="Target unresolved records assigned to a worker lane")
    ap.add_argument("--work-state", type=Path, default=DEFAULT_WORK_STATE)
    ap.add_argument("--status-file", type=Path, default=Path("DEEP_SCAN_STATUS.md"))
    ap.add_argument("--write-work-state", action="store_true", help="Persist lane assignments and package history in the repository")
    args = ap.parse_args()
    if args.historical is None:
        args.historical = args.corpus.parent / "historical" / "historical.json"

    doc = json.loads(args.corpus.read_text(encoding="utf-8"))
    sidecar = load_sidecar(args.sidecar)
    historical_doc: dict[str, Any] = {}
    if args.historical.exists():
        try:
            loaded_historical = json.loads(args.historical.read_text(encoding="utf-8"))
            historical_doc = loaded_historical if isinstance(loaded_historical, dict) else {}
        except Exception as exc:
            raise SystemExit(f"Unreadable historical archive {args.historical}: {exc}") from exc
    main_todo = pending(doc, sidecar)
    historical_todo = historical_pending(historical_doc, sidecar)
    todo_all = main_todo + historical_todo
    total = sum(1 for _ in iter_records(doc))
    historical_total = len([x for x in historical_doc.get("items", []) if isinstance(x, dict)]) if isinstance(historical_doc, dict) else 0
    lane = args.lane.upper()

    # Work-state is consulted even for a legacy one-off package so terminal hands-on
    # items can never be silently resurrected. Metadata is mirrored into the ledger
    # so DEEP_SCAN_STATUS.md becomes a usable manual-verification work list.
    state = load_state(args.work_state)
    sync_verified(state, sidecar)
    for _strand, key, _h, row, _reason in todo_all:
        update_record_metadata(state, key, row)
    terminal = manual_verification_keys(state)
    queue_items = [item for item in todo_all if item[1] not in terminal]
    queue_by_key = {item[1]: item for item in queue_items}
    prioritized_keys = prioritize_pending_keys(state, [item[1] for item in queue_items])
    prioritized_items = [queue_by_key[key] for key in prioritized_keys if key in queue_by_key]
    pending_total = len(prioritized_items)
    main_pending_total = len([x for x in prioritized_items if not x[1].startswith("historical:")])
    historical_pending_total = pending_total - main_pending_total

    if lane:
        assigned = fill_lane(state, lane, [item[1] for item in queue_items], target_size=max(1, int(args.lane_size)))
        todo = [queue_by_key[key] for key in assigned if key in queue_by_key]
        assigned_main = len([x for x in todo if not x[1].startswith("historical:")])
        assigned_historical = len(todo) - assigned_main
        print(
            f"Main Radar: {total} records / {main_pending_total} automatic pending; "
            f"Historical: {historical_total} records / {historical_pending_total} automatic pending; "
            f"hands-on terminal: {len(terminal)}; worker {lane} assigned now: {len(todo)} "
            f"({assigned_main} main + {assigned_historical} historical)"
        )
    else:
        # A legacy/manual SINGLE package must never steal work already reserved to a
        # persistent worker lane (or another unresolved SINGLE package).  Older
        # versions sliced the live priority queue directly, which allowed the same
        # records to be reserved by SINGLE and A/B at the same time.
        occupied = assigned_keys(state)
        single_candidates = [item for item in prioritized_items if item[1] not in occupied]
        limit = max(0, int(args.max_records or 0))
        todo = single_candidates[:limit] if limit else single_candidates
        packaged_main = len([x for x in todo if not x[1].startswith("historical:")])
        packaged_historical = len(todo) - packaged_main
        print(
            f"Main Radar: {total} records / {main_pending_total} automatic pending; "
            f"Historical: {historical_total} records / {historical_pending_total} automatic pending; "
            f"hands-on terminal: {len(terminal)}; packaged now: {len(todo)} "
            f"({packaged_main} main + {packaged_historical} historical)"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not todo:
        summary = args.output_dir / "NO_DEEP_SCAN_NEEDED.txt"
        if lane and pending_total:
            summary.write_text(f"Worker {lane} currently has no assignable Deep Scan work.\n", encoding="utf-8")
        else:
            summary.write_text("All current Main Radar and Historical Radar records already have authoritative Deep Scan V2 verification.\n", encoding="utf-8")
        if lane and state is not None and args.write_work_state:
            save_state(state, args.work_state)
            write_status_markdown(state, sidecar, [item[1] for item in todo_all], args.status_file)
        print(summary)
        return

    pkg_id = package_id_for(todo, lane=lane)
    dupes = duplicate_index(doc)
    variants = same_key_variants(doc)
    workdir = Path(tempfile.mkdtemp(prefix="radar-deep-scan-v2-"))
    try:
        root = workdir / f"deep_scan_package_{pkg_id}"
        batches = root / "batches"
        batches.mkdir(parents=True)
        instructions = INSTRUCTIONS
        if lane:
            instructions = (
                f"# Worker lane {lane}\n\n"
                "This is ONE of TWO ZIPs produced for concurrent Worker A + Worker B research. Start BOTH lanes at the same time in separate systems. "
                "This ZIP is a reserved, non-overlapping worker lane from the Radar's persistent Deep Scan queue. "
                "Process only the records in this ZIP, in their supplied order. Other worker lanes contain different records.\n\n"
                + instructions
            )
        (root / "INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")
        (root / "CHECKPOINT.py").write_text(CHECKPOINT_TOOL, encoding="utf-8")
        (root / "STAGED_EXECUTION.md").write_text(
            "# EXECUTE RESEARCH — NOT A HANDOFF INVENTORY\n\n"
            "This lane has 36 assignments (or the exact manifest count), but work is executed in "
            "stages of up to SIX source-verified records. Worker A and B can operate concurrently.\n\n"
            "1. Run `python CHECKPOINT.py next` to write NEXT_STAGE.json.\n"
            "2. CHECK each record for approximately correct bibliography, content and Radar relevance using "
            "substantive available source evidence. Escalate via applicable discovery routes only if needed; a failed link alone is not a DEFER.\n"
            "3. Write actual verified result JSON (one object, list, or package-style file). "
            "Run `python CHECKPOINT.py add STAGE_RESULTS.json`.\n"
            "4. Save WORK_PROGRESS.json; repeat `next` until no assignments remain. "
            "If the session stops, carry the original ZIP and WORK_PROGRESS.json "
            "into a new session and continue unfinished items.\n"
            "5. After at least one consecutive verified record run `python CHECKPOINT.py assemble` and "
            "`python CHECK_RESULTS.py deep_scan_results.json`.\n\n"
            "Do not stop at a source inventory or claim autonomous background execution. "
            "Do not fabricate outcomes to fill a stage. Package issuance and unstarted "
            "items are not research attempts; preserve the per-item three-real-attempt rule. "
            "Stage files are not inbox-ready, but assembled verified prefixes are.\n", encoding="utf-8")
        start_here = START_HERE
        if lane:
            start_here = (
                f"RADAR DEEP SCAN V2 — WORKER {lane}\n\n"
                "START BOTH Worker A and Worker B ZIPs SIMULTANEOUSLY if the external system supports independent agents; do not wait for the other lane. This package is already reserved to this worker lane in GitHub. It does not overlap the other active lane. Finish EVERY assignment (36 when 36 assigned); do not deliver one record as the whole batch.\n"
                "A new chat needs no prior conversation history: read INSTRUCTIONS.md and process this ZIP in order. If capacity/time runs short, save your partial work and CONTINUE; a validated, verified consecutive prefix is also ready for inbox.\n\n"
                + START_HERE
            )
        start_here += "\nSTAGED EXECUTION (READ FIRST): Read STAGED_EXECUTION.md. Run python CHECKPOINT.py next for the next 6 unfinished assignments, research them fully, save via python CHECKPOINT.py add STAGE_RESULTS.json, then repeat. The original 36-assignment lane remains intact. An inventory is not a result; a checked consecutive prefix assembled as a V2 JSON is inbox-ready.\n"
        start_here += (
            "\nCHECKPOINT / RESUME: When a record is genuinely verified, save its exact result as one_result.json and run python CHECKPOINT.py add one_result.json. "
            "Run python CHECKPOINT.py status to list missing assignments; continue those in future sessions using this SAME ZIP plus WORK_PROGRESS.json. "
            "Once a verified consecutive prefix is done run python CHECKPOINT.py assemble, THEN run CHECK_RESULTS.py. "
            "An inventory is not a scan. A verified consecutive prefix is a valid partial submission. No fabricated decisions or scan-attempt counters.\n"
        )
        start_here += "\nIMPORTANT: Run python CHECK_RESULTS.py deep_scan_results.json before upload. It MUST report PASS for the verified consecutive prefix (for example 5/36). Fix errors; never invent evidence.\n"
        (root / "START_HERE.txt").write_text(start_here, encoding="utf-8")
        (root / "FINAL_CHECK.txt").write_text(
            "BEFORE RETURNING deep_scan_results.json:\n"
            "1. Research as many as reasonably possible in order; a verified nonempty consecutive prefix is valid.\n"
            "2. KEEP/REVIEW: 1-3 complete controlled-vocabulary claims.\n"
            "3. DROP/DEFER/DROP_UNVERIFIABLE: claims: [].\n"
            "4. EXACT evidence_depth values in INSTRUCTIONS.md; never invent synonyms.\n"
            "5. Report the actual recovery ladder step if supplied_url failed.\n"
            "6. Keep reader_title <=18 words and reader_what <=20 words.\n"
            "7. No invented verification or metadata correction.\n"
            "8. Valid verified prefix files CAN enter inbox; never mislabel N/36 as full completion.\n"
            "9. RUN CHECK_RESULTS.py before returning: nonempty consecutive partial output MUST PASS.\n"
            "10. A and B work independently; each may return verified partial results for GitHub to track.\n"
            "11. RESUME: save verified records, assemble the consecutive prefix for inbox, and continue unfinished work later.\n",
            encoding="utf-8",
        )

        if args.no_fetch:
            fetched = [(*item, SourceRead("stored_only", "", note="source pre-retrieval disabled; LLM must use the retrieval ladder")) for item in todo]
        else:
            workers = max(1, min(args.workers, 20))
            ordered: dict[int, Any] = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(source_for, item): i for i, item in enumerate(todo)}
                done = 0
                for fut in concurrent.futures.as_completed(futures):
                    idx = futures[fut]
                    try:
                        ordered[idx] = fut.result()
                    except Exception as exc:
                        strand, key, h, r, reason = todo[idx]
                        ordered[idx] = (strand, key, h, r, reason, SourceRead("stored_only", "", note=f"packager error: {clean(exc)[:160]}"))
                    done += 1
                    if done % 25 == 0 or done == len(todo):
                        print(f"Prepared source material for {done}/{len(todo)} works")
            fetched = [ordered[i] for i in range(len(todo))]

        jobs = [build_job(row, i + 1, sidecar, dupes, variants) for i, row in enumerate(fetched)]
        # Make the next issuance explicit in every job. Main Radar attempt 3 is
        # a deliberately stronger final automatic verification pass.
        annotate_scan_attempts(jobs, state)
        batch_size = max(1, min(args.batch_size, 30))
        batch_files: list[dict[str, Any]] = []
        for start in range(0, len(jobs), batch_size):
            chunk = jobs[start:start + batch_size]
            number = start // batch_size + 1
            filename = f"batch_{number:03d}.json"
            payload = {"format": FORMAT, "package_id": pkg_id, "worker_lane": lane or None, "batch_number": number, "jobs": chunk}
            (batches / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            batch_files.append({"file": f"batches/{filename}", "jobs": len(chunk)})

        counts: dict[str, int] = {}
        source_modes: dict[str, int] = {}
        for job in jobs:
            counts[job["queue_reason"]] = counts.get(job["queue_reason"], 0) + 1
            mode = job["source_material"]["read_mode"]
            source_modes[mode] = source_modes.get(mode, 0) + 1
        scope_counts = {"main": 0, "historical": 0}
        for job in jobs:
            scope = clean(job.get("corpus_scope")).lower() or "main"
            scope_counts[scope] = scope_counts.get(scope, 0) + 1
        manifest = {
            "format": FORMAT, "result_format": RESULT_FORMAT, "package_id": pkg_id, "worker_lane": lane or None,
            "created_at": utc_now(), "current_radar_records": total, "historical_radar_records": historical_total,
            "main_pending_total": main_pending_total, "historical_pending_total": historical_pending_total,
            "works_in_package": len(jobs), "scope_counts": scope_counts, "queue_reasons": counts,
            "source_modes": source_modes, "possible_duplicate_records": len(dupes), "same_record_key_variant_groups": len(variants), "batch_size": batch_size,
            "hard_final_main_jobs": sum(1 for job in jobs if job.get("scan_mode") == "hard_final"),
            "batches": batch_files, "instructions": "INSTRUCTIONS.md", "claims_vocabulary": "claims_vocabulary.json",
            "claims_format": CLAIMS_FORMAT, "admission_scope_policy": EU_RI_SCOPE_POLICY, "expected_result_filename": "deep_scan_results.json",
        }
        (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if not CLAIMS_VOCAB.exists():
            raise FileNotFoundError(f"Claims vocabulary missing: {CLAIMS_VOCAB}")
        shutil.copy2(CLAIMS_VOCAB, root / "claims_vocabulary.json")
        (root / "CHECK_RESULTS.py").write_text(OFFLINE_CHECKER, encoding="utf-8")
        (root / "RESULT_TEMPLATE.json").write_text(json.dumps({"format": RESULT_FORMAT, "claims_format": CLAIMS_FORMAT, "package_id": pkg_id, "results": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        zip_path = args.output_dir / f"deep_scan_package_{pkg_id}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(root.parent))
        shutil.copy2(zip_path, args.output_dir / "deep_scan_package.zip")
        pkg_main = sum(1 for job in jobs if job.get("corpus_scope") == "main")
        pkg_hist = len(jobs) - pkg_main
        (args.output_dir / "PACKAGE_SUMMARY.txt").write_text(
            f"Deep Scan V2 package: {pkg_id}\nWorker lane: {lane or 'legacy single queue'}\n"
            f"Works needing authoritative verification: {len(jobs)} ({pkg_main} main + {pkg_hist} historical)\n"
            f"Internal batches: {len(batch_files)}\n\n"
            "Scheduling policy: preserve existing reservations; fill newly free slots with Main Radar first, then Historical Radar.\n"
            "Give deep_scan_package.zip to a browsing-capable LLM and ask it to follow INSTRUCTIONS.md strictly.\n",
            encoding="utf-8",
        )
        if lane and state is not None:
            register_package(state, lane, pkg_id, [job["record_key"] for job in jobs])
            if args.write_work_state:
                save_state(state, args.work_state)
                write_status_markdown(state, sidecar, [item[1] for item in todo_all], args.status_file)
        print(f"Created {zip_path} with {len(jobs)} works in {len(batch_files)} internal batches")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()

# Item-level retry budgets are enforced by deep_scan_work_state.py using validated
# recovery_attempts. Never derive them from scan_package_attempts (ZIP issuance).

