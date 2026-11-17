# Relevance Focus — independent GLOBAL R&I futures Deep Scan

This directory belongs to the **automatic Relevance Focus** scanner, NOT the separate Global R&I Blind Spots lane and NOT the EU-focused ordinary Radar Deep Scan.

## Scope

For **new discoveries**, Relevance Focus uses a fixed policy selection, not topics extracted from current Main Radar publications. A publication qualifies through **either** track:

- All **10 critical technology areas** in Commission Recommendation (EU) 2023/2113: advanced semiconductors; artificial intelligence; quantum technologies; biotechnologies; advanced connectivity, navigation and digital technologies; advanced sensing technologies; space and propulsion technologies; energy technologies; robotics and autonomous systems; advanced materials, manufacturing and recycling technologies. All 10 are searched, not only the four identified for the EU's initial highest-priority risk assessments.
- **Four regional R&I agendas**, restricted to the regions they concern: **CELAC** (climate change/environmental sustainability/energy transition; AI in Science; health); **Union for the Mediterranean** (climate change; renewable energies; health); **Africa** (innovation and technology; green transition; public health; science and higher-education capacity); **ASEAN** (green technologies; space cooperation; marine science; mobility).

The scanner includes new-scan-only coverage of **all 33 CELAC countries, the 16 non-EU UfM member states, 54 African countries and 11 ASEAN members**. These member-country patterns do not alter historical Radar backfill. Libya is a UfM observer rather than a full member, and Timor-Leste joined ASEAN in October 2025. The search still uses the original scanner's **non-EU/UK primary research setting** rule, does not require an EU connection, and never infers a work's subject geography from where it was published.

New candidate records have `focus_scope_id: critical-technologies-regional-priorities-2026-v1` and `focus_priority_track`. Topics and their geographical settings must be supported together in the publication's title/abstract, not merely in the query; the independent Deep Scan must verify them from accessible primary evidence. Historic leads, decisions, packages, reviewer assignments and Main Radar data are **not reclassified or edited**.

Source discovery is bibliographic, **not** source validation. Candidate questions are hypothetical; even a strong match is not yet a verified forecast or a scientific claim.

## Automatic discovery → source-reviewed global Deep Scan

1. `.github/workflows/relevance-focus-scan.yml` automatically runs a dedicated 25-minute OpenAlex/Crossref discovery (six times a day). It updates `../regional_discoveries.json` and `../relevance_stuff.xlsx`, **without** submitting those leads through the ordinary EU Radar admission gate.
2. The run automatically creates an artifact named `relevance-focus-global-deep-scan-review`. Download the `.zip` and give `INSTRUCTIONS.md` and `MANIFEST.json` to a browsing-capable researcher/reviewer or LLM that genuinely accesses each primary source. For the new scope, `INSTRUCTIONS.md` explicitly verifies the assigned technology **or** the relevant regional agenda and substantive geography. This is a **review handoff**, not proof that a Deep Scan was completed. New-scope manifests are saved under `packages/` and are recognized by the existing importer. **Existing `pending_manifest.json`, all older `packages/*.json` and imported results are preserved**; an unfinished older package cannot block the new-focus review handoff.
3. Submit `relevance-focus-deep-scan-v1` JSON review results to `inbox/`. A push to `main` automatically runs `.github/workflows/relevance-focus-deep-scan-import.yml`. The importer checks assignment and structured verification before creating `verified_findings.json` or `review_archive.json`, archives the reviewed JSON to `processed_inbox/`, and rebuilds the workbook.
4. The workbook's `Global verified futures` tab displays only actual KEEP results from this global evidence-review process. `R&I futures questions` contains **unverified investigative hypotheses**. Legacy EU Radar results remain separately labeled `Radar verified backfill`. The `Regional publication leads` sheet quarantines legacy publisher-related country tags that have no renewed evidence.

If a **new-scope** Deep Scan package has not been fully reviewed, later automatic runs reuse its same package ID, while old historical packages remain importable with their own IDs. Neither selection path silently invalidates outstanding work. The manually triggered catch-up workflow still prioritizes older unfinished assignments under its pre-existing behavior.

## Source integrity and uncertainty

A global KEEP requires accessed source identity, relevant topical evidence, substantive setting evidence, publisher-country-only=false, a credible source-integrity assessment, no suspected propaganda/influence operations, and a conditional, qualified R&I futures mechanism. A propagandistic or unverifiable source can never be marked KEEP. Peer-reviewed analysis and credible official declarations are different kinds of evidence: an announcement verifies *that a decision was announced*, not that its expected benefits occurred. Source-country politics never automatically disqualify an otherwise independent credible study.

If a primary source cannot be verified, use REVIEW or DROP with a substantive explanation. No source snippets, location-based guesses or hypothesised EU bridges grant verified status. Independent reviews do not modify ordinary Radar A/B/C, its admission sidecars or its existing Deep Scan files.

## Reproduce locally

```bash
python -m unittest discover -s tests -p 'test_relevance_focus*.py' -q
python scripts/relevance_focus.py export-json --output /tmp/relevance_report.json
node scripts/generate_relevance_stuff.js /tmp/relevance_report.json
python scripts/relevance_focus_deep_scan.py prepare --batch-size 12 --artifact /tmp/relevance_focus_global_review.zip
# After genuinely source-reviewed results are put into inbox/:
python scripts/relevance_focus_deep_scan.py import-inbox
```

A full online discovery normally runs for 1500 seconds and requires working OpenAlex/Crossref access. The command above for local reproduction deliberately does not make online calls.

## Request additional packages without overwriting the original 30

From **Actions → Relevance Focus — Prepare Next Deep Scan Package → Run workflow**,
choose `package_size` (1–60). Download the run artifact named
`relevance-focus-next-deep-scan-*`. Each click reserves the next batch from the
existing discovery archive, excluding completed reviews and every candidate
already reserved by the original package or any earlier additional package.
The resulting manifest is saved in `packages/<package_id>.json`, so multiple
independent packages may be imported through the same inbox without overwriting
`pending_manifest.json`. Each reviewer must return their matching `package_id`.
No new discovery is performed by this button; use the main Relevance Focus
scanner for discovery. Packages can be generated until no eligible unassigned
leads remain. An empty package means no additional eligible leads are available.

## Policy sources

- [Commission Recommendation (EU) 2023/2113 — 10 critical technologies](https://eur-lex.europa.eu/eli/reco/2023/2113)
- [EU–CELAC New Agenda for Research and Innovation](https://research-and-innovation.ec.europa.eu/document/download/c46b61b5-753f-424b-8cda-e2e8b3a626a5_en?filename=ec_rtd_new-agenda-eu-celac-cooperation-ri.pdf)
- [Union for the Mediterranean R&I platform](https://ufmsecretariat.org/platform/ufm-regional-platform-on-research-and-innovation/) and [member states](https://ufmsecretariat.org/who-we-are/member-states/)
- [EU–Africa R&I cooperation](https://research-and-innovation.ec.europa.eu/strategy/strategy-research-and-innovation/europe-world/international-cooperation/regional-dialogues-and-international-organisations/eu-africa-cooperation_en)
- [ASEAN–EU Plan of Action 2023–2027](https://asean.org/wp-content/uploads/2022/08/ASEAN-EU-Plan-of-Action-2023-2027-FINAL.pdf)
