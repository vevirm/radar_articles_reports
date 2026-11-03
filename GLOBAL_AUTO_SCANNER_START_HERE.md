# Global R&I blind spots — automatic scanner and Deep Scan

## What to install

Copy the contents of this install package into the root of your EXISTING Radar GitHub
repository. Keep the `.github/workflows/` paths unchanged. No existing Radar scan,
report, or cron must be replaced. Commit to `main`.

You will see two **manually triggered** actions:

1. **Global R&I Blind Spots — Manual Scan** — gathers tightly filtered leads,
   anchored in the existing `radar_active.json` without any user-uploaded input.
2. **Global R&I Deep Scan — Automatic (Manual Trigger)** — runs discovery first,
   then reads retrieved source documents, seeks independent evidence, and attempts
   to produce a short evidence-screened report. **Use this action for the full run.**

Neither runs on a timer, on a push, or after normal Radar scans.

## How the AI verification step works (IMPORTANT)

GitHub Models was **retired in July 2026**. This package does **not** use it.
Instead it uses the supported GitHub Copilot CLI, called from a manual GitHub
Action with `copilot-requests: write`. For eligible organization-owned GitHub
repos with Copilot CLI billing allowed, the built-in `GITHUB_TOKEN` is enough;
no API key needs adding. **Access and possible usage charges depend on your
GitHub organization subscription and policy.**

If your repository does not have that Copilot entitlement, you can instead add
**one** secret to the repository: `OPENAI_API_KEY` under Settings → Secrets and
variables → Actions. The scanner detects it and uses OpenAI API inference
instead of Copilot CLI (API billing applies). There is no repeated data upload,
JSON import, or reviewer-package cycle.

If neither Copilot access nor an OpenAI API key is available, the action will
still collect discovery leads and document availability, but **cannot honestly
produce AI-checked findings**. It reports zero findings and an audit, rather
than filling the report with unverified guesses. It does not automatically
upgrade source metadata or generic article titles into verified evidence.

## What is gathered

Existing Radar A, B, C records in `radar_active.json` are read on each run:
these supply themes, actual Radar overlap comparisons and starting sources.
Independent discovery then consults: OpenAlex (using the existing Radar
trusted-journal lists), curated Nature and NIH feeds, explicitly allowed
US NSF / Chinese Statistics / Russian HSE institution pages, and a maintained
set of identifiable public OECD, UNESCO UIS, WIPO, NSF/NCSES, Chinese R&D
statistics, HSE, Nature Index and scientific-publication starting documents.
Some OpenAlex searches additionally use Chinese and Russian phrases.

Country regions: **United States, China, Russia**.
Themes: **funding/institutions/talent; technological capacity; research
security/collaboration**. No arbitrary web-wide news crawls, opinion
aggregators, social media or unapproved publishers.

Every proposed Deep Scan finding must have substantive retrieved source text,
a second document from a distinct publisher group, a model assessment about
THE SAME specific R&I change, and **literal excerpts verified against both
retrieved documents**. Official source documents are primary claims, not
independent validation of their accuracy. Weak or uncorroborated candidates
are rejected/held in an audit rather than shown as findings. Pairing by
similarity does not prove corroboration; the model must assess that too.

Existing Radar items are eligible (they are not excluded), and each admitted
finding states whether it was **already covered / partially covered / not
identified by the automated comparison**. A claim of 'not identified' is not
proof that no related Radar work exists. Results remain completely separate
from the original Radar findings and downstream Excel reports.

## Result folder after pressing Run

- `Global R&I Blind Spots/LATEST.md` — all discovery statistics and candidate leads
- `Global R&I Blind Spots/deep_scan/AUTO_FINDINGS.md` — **only evidence-screened findings**, 0–10, with two source URLs, excerpts, context, limits, relationship to main Radar
- `Global R&I Blind Spots/deep_scan/AUTO_FINDINGS.json` — same structured report
- `Global R&I Blind Spots/deep_scan/audit.json` — short machine-check decisions, failed source reads, and model errors
- `Global R&I Blind Spots/deep_scan/auto_archive.json` — bounded cross-run archive

If no finding satisfies all safeguards, the report says so explicitly rather
than inventing filler. Source access, model quality, cross-publisher agreement
and AI judgements can all fail; this is an **automatic evidence-screening
system, not a human-certified fact checker**. The actual first GitHub run has
not been performed by the developer; test mocks are not live validation.

## Fixed limits and costs

Deep Scan reads at most **24** selected documents and investigates at most
**12 evidence pairs** by default, with no more than 10 report findings. The
manual Action inputs allow 8–40 documents and 4–20 pairs. Individual document
fetches are bounded; sources that block access are excluded with an audit
reason. The program won't require you to repair URLs manually to proceed.

## First run

Actions → **Global R&I Deep Scan — Automatic (Manual Trigger)** → Run workflow
→ keep the default limits. Read `AUTO_FINDINGS.md` after the action succeeds.
There is no second Import action and no separate package to upload.

## Files and tests

Scanner scripts: `scripts/global_blind_spots.py`,
`scripts/global_blind_spots_deep_scan.py` (shared Radar-overlap utilities),
`scripts/global_blind_spots_auto.py` (automatic source/deep assessment).
Configuration: `global_blind_spots_config.json` and
`global_deep_scan_source_leads.json`. Tests: `tests/test_global_blind_spots*.py`.

Run tests with `python -m unittest discover -s tests -p 'test_global_*.py'`.
Requires Python 3.12, beautifulsoup4 and pypdf. The workflow installs these
itself. It also installs the GitHub Copilot CLI; eligibility is determined by
GitHub at runtime. The scanner does not modify the original Radar Python
scripts, schedules, root findings, or Excel exports.
