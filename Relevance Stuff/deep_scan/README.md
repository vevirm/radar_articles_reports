# Relevance Focus — independent GLOBAL R&I futures Deep Scan

This directory belongs to the **automatic Relevance Focus** scanner, NOT the separate Global R&I Blind Spots lane and NOT the EU-focused ordinary Radar Deep Scan.

## Scope

Each scheduled, manual scan-mode, or successful upstream-triggered Relevance Focus run extracts **active Main Radar topic interests** (including biodiversity and semiconductors when present) and searches worldwide for **publications actually about those topics in those regions**. The search targets substantive settings outside the EU/UK, without restricting where evidence is published. The current country of the publishing journal, portal, institution, host or author is never evidence that the topic is *about* that country. A place and subject must appear as a substantive connected pair in the work's title/abstract; incidental citations, boilerplate, grant acknowledgements and affiliations do not count. A country can matter in one topic area and not another.

Source discovery is bibliographic, **not** source validation. Candidate questions are hypothetical; even a strong match is not yet a verified forecast or a scientific claim.

## Automatic discovery → source-reviewed global Deep Scan

1. `.github/workflows/relevance-focus-scan.yml` automatically runs a dedicated 25-minute OpenAlex/Crossref discovery (six times a day). It updates `../regional_discoveries.json` and `../relevance_stuff.xlsx`, **without** submitting those leads through the ordinary EU Radar admission gate.
2. The run automatically creates an artifact named `relevance-focus-global-deep-scan-review`. Download the `.zip` and give `INSTRUCTIONS.md` and `MANIFEST.json` to a browsing-capable researcher/reviewer or LLM that genuinely accesses each primary source. This is a **review handoff**, not proof that a Deep Scan was completed.
3. Submit `relevance-focus-deep-scan-v1` JSON review results to `inbox/`. A push to `main` automatically runs `.github/workflows/relevance-focus-deep-scan-import.yml`. The importer checks assignment and structured verification before creating `verified_findings.json` or `review_archive.json`, archives the reviewed JSON to `processed_inbox/`, and rebuilds the workbook.
4. The workbook's `Global verified futures` tab displays only actual KEEP results from this global evidence-review process. `R&I futures questions` contains **unverified investigative hypotheses**. Legacy EU Radar results remain separately labeled `Radar verified backfill`. The `Regional publication leads` sheet quarantines legacy publisher-related country tags that have no renewed evidence.

If an assigned Deep Scan package has not been fully reviewed, later automatic runs **reuse the same package ID**; they do not silently invalidate outstanding work.

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
choose `package_size` (1–30). Download the run artifact named
`relevance-focus-next-deep-scan-*`. Each click reserves the next batch from the
existing discovery archive, excluding completed reviews and every candidate
already reserved by the original package or any earlier additional package.
The resulting manifest is saved in `packages/<package_id>.json`, so multiple
independent packages may be imported through the same inbox without overwriting
`pending_manifest.json`. Each reviewer must return their matching `package_id`.
No new discovery is performed by this button; use the main Relevance Focus
scanner for discovery. Packages can be generated until no eligible unassigned
leads remain. An empty package means no additional eligible leads are available.
