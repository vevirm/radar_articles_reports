#!/usr/bin/env python3
"""Independent, source-reviewed global Relevance Focus Deep Scan handoff.

This is intentionally NOT normal Radar/European admission. An indexed DOI lead
is never a verified result; human/LLM research with accessed primary evidence is
required. Importer checks the structured proof and keeps its decisions in the
Relevance Stuff namespace, without mutating radar.json or Radar admission.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import zipfile

from relevance_focus import (excluded_future_relevance_lead, FOCUS_SCOPE_ID,
                             FOCUS_TRACK, priority_region_match)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'Relevance Stuff' / 'deep_scan'
ARCHIVE = ROOT / 'Relevance Stuff' / 'regional_discoveries.json'
MANIFEST = BASE / 'pending_manifest.json'
PACKAGES = BASE / 'packages'  # Independently reserved additional review manifests
VERIFIED = BASE / 'verified_findings.json'
REVIEW = BASE / 'review_archive.json'
INBOX = BASE / 'inbox'
PROCESSED = BASE / 'processed_inbox'
RESULT_FORMAT = 'relevance-focus-deep-scan-v1'
DECISIONS = {'keep', 'review', 'drop'}
INTEGRITIES = {'independent_credible', 'credible_primary_claim_only', 'unverified', 'unreliable'}
RISKS = {'none_identified', 'suspected', 'confirmed'}

INSTRUCTIONS = '''# Relevance Focus: Global R&I Futures Deep Scan

MISSION: Independently verify a publication's **aboutness**, source integrity,
the assigned policy PRIORITY connection, and *possible* future R&I significance for its own
country/region. This is NOT the EU-centered Radar Deep Scan: **no European/EU
relevance, European comparison, or EU impact is required or preferred**.

Use MANIFEST.json. Research EACH listed DOI and source yourself, using publicly
accessible publisher/repository full text or substantive primary material (or
credible official documents), checking bibliographic identity. Search snippets,
source names, institutional address, publisher country, citation country, author
nationality, affiliations and URL country-code domains never establish aboutness.
Country tags require substantive evidence about that place in the actual work;
review a wrong tag as DROP (or REVIEW if uncertain). Do not make predictions:
provide conditional R&I futures questions, distinguishing observed evidence,
possible trajectories, and uncertainty. Where possible identify concrete
mechanisms—ecological data and biodiversity infrastructures, chip research and
skills, research partnerships, policy instruments, scientific capacity, etc.
Do NOT assume all regions are interesting for all topics: reject non-connections.


FOCUS RULES FOR NEWLY DISCOVERED CANDIDATES:
A candidate with `focus_scope_id: critical-technologies-regional-priorities-2026-v1`
must demonstrably fit at least ONE assigned track:
- `Critical technology: ...`: the publication must actually concern the named
  technology area from the TEN EU economic-security critical-technology areas.
  The research subject can be any substantive external country/region already
  covered by this Relevance Focus scanner; an EU impact claim is NOT required.
- `CELAC: ...`, `Union for the Mediterranean: ...`, `Africa: ...`, or `ASEAN: ...`:
  the work must actually concern the named R&I priority IN the assigned region.
  A publication on an ASEAN country and an unrelated CELAC priority is NOT a match.
  Confirm both the substantive priority and the region/country setting. For
  space cooperation, verify cooperation rather than unrelated satellite mentions;
  for AI in Science, verify AI is used for science, not generic AI news.

Technology and regional tracks are ALTERNATIVES, not an AND condition. Check the
EXACT manifest `focus_issue` even when another track might also fit the paper.
The four geographic tracks are CELAC (climate/environment/energy transition,
AI in Science, health); Union for the Mediterranean (climate change, renewable
energies, health); Africa (innovation/technology, green transition, public health,
science/higher-education capacity); ASEAN (green technologies, space cooperation,
marine science, mobility). All TEN technologies, not merely the EU's four
initial risk-assessment priorities, are in scope.

HISTORICAL COMPATIBILITY: A lead without the new focus_scope_id belongs to an
OLDER discovery package. Review its already assigned focus_issue under that
package's original rules; do not apply new criteria retroactively, change old
KEEP/REVIEW/DROP decisions, or relabel an existing finding. The source-integrity,
aboutness, and conditional-futures standards remain unchanged for everyone.

INTEGRITY GATE: Reject propaganda, deceptive pseudo-journals, influence outlets,
source laundering, fabricated science, retracted material, and uncorroborated
advocacy assertions. Do not blacklist entire countries or governments. A credible
primary official announcement can prove that an action was announced, not that
its claimed outcomes occurred. Confirm independent scholarly evaluation when
asserting research findings. Record source quality, outlet control or conflict
of interest, and whether allegedly independent sources share one owner.
Repetitions within the same influence network are not corroboration.

Each result must contain candidate_id and decision (keep / review / drop), plus:
source_verification: identity_verified boolean, primary_url (accessible URL),
source_type (scholarly_article, academic_book, institutional_report,
official_announcement or other), source_integrity (independent_credible,
credible_primary_claim_only, unverified, unreliable), propaganda_or_influence_risk
(none_identified, suspected, confirmed), basis (specific accessible evidence),
and independent_corrob_urls (array, possibly empty).
aboutness: place (EXACT manifest focus_region), is_substantive boolean,
publisher_country_only boolean, basis (substantive research object, NOT outlet),
verified_excerpt (short verifiable paraphrase/quote, NOT fabricated).
topic: label (EXACT manifest focus_issue), is_relevant boolean, basis.
futures: classification (observed / possible / mixed), mechanism (which R&I
system or science/technology development is at stake), why_could_matter
(conditional, not a predicted outcome), uncertainty (what is not known),
research_question (one investigable question, preferably ending '?').

IMPORTANT OUTPUT REQUIREMENT: For every REVIEW or DROP, include a detailed
"review_reason" (at least 20 characters). You may also include "decision_basis"
as a more general explanation; the importer accepts decision_basis as a fallback
if review_reason is missing, but review_reason is preferred. Every KEEP still
requires all four substantive evidence sections.

KEEP only when ALL identity, credible source, assigned priority, geography and evidence
conditions pass. If only a state-controlled press statement is available,
DO NOT treat that as independent confirmation of a claimed technological
breakthrough. REVIEW unresolved source access/conflicts/identity and explicitly
explain why; DROP demonstrable false relevance, source manipulation or
non-substantive geography. Note review is never shown as verified.

Results file format: {"format":"relevance-focus-deep-scan-v1",
"package_id":"<exact package_id from MANIFEST.json>","results":[...]}
Do not invent source access, quotes, corroboration, or verification steps.
No changes to ordinary Radar acceptance or its Deep Scan rules.
'''


def read(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf8'))


def atomic_write(path: Path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    os.replace(temp, path)


def valid_v4_lead(row):
    if not (isinstance(row, dict) and not excluded_future_relevance_lead(row)
            and isinstance(row.get('candidate_id'), str)
            and row['candidate_id'].startswith('REL-') and row.get('aboutness_basis')
            in {'title', 'substantive abstract / reader claim'} and row.get('geographic_evidence')
            and row.get('focus_region') and row.get('focus_issue')
            # Preserve the existing non-EU/UK primary research setting.
            and row.get('focus_group') != 'EU / UK'
            and re.fullmatch(r'https://doi\.org/10\.\d{4,9}/\S+', str(row.get('url') or ''), re.I)):
        return False
    if row.get('focus_scope_id') == FOCUS_SCOPE_ID:
        return (row['focus_issue'] in FOCUS_TRACK and
                row.get('focus_priority_track') == FOCUS_TRACK[row['focus_issue']] and
                priority_region_match(row['focus_issue'], row['focus_group'], row['focus_region']))
    # Do not retrofit the new policy to historical, already assigned material.
    return True


def all_manifests():
    """Return original and additional packages, rejecting conflicting package IDs."""
    manifests = [read(MANIFEST, {})]
    for path in sorted(PACKAGES.glob('*.json')) if PACKAGES.exists() else []:
        manifests.append(read(path, {}))
    by_id = {}
    for manifest in manifests:
        package_id = manifest.get('package_id')
        if not package_id:
            continue
        if package_id in by_id and by_id[package_id] != manifest:
            raise ValueError(f'Conflicting manifests for package {package_id}')
        by_id[package_id] = manifest
    return by_id



def write_review_artifact(manifest, artifact):
    if not artifact:
        return
    artifact = Path(artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(artifact, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('INSTRUCTIONS.md', INSTRUCTIONS)
        z.writestr('MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        z.writestr('RESULTS_TEMPLATE.json', json.dumps({'format': RESULT_FORMAT,
            'package_id': manifest['package_id'], 'results': [],
            '_guidance': ('Supply all assigned candidate results. For review/drop, '
                          'provide review_reason (20+ chars); decision_basis is '
                          'also accepted as a fallback. Keep requires complete '
                          'source_verification, aboutness, topic and futures.')}, indent=2))


def balanced_review_jobs(available, size):
    """Balance priority areas and places without changing old assignments."""
    available.sort(key=lambda x: (-int(x.get('focus_score') or 0), x['candidate_id']))
    buckets = {}
    for row in available:
        buckets.setdefault((row['focus_issue'], row['focus_region']), []).append(row)
    jobs = []
    while len(jobs) < size and any(buckets.values()):
        for key in sorted(buckets):
            if buckets[key] and len(jobs) < size:
                jobs.append(buckets[key].pop(0))
    return jobs

def prepare(*, batch_size=30, artifact=None, additional=False):
    limit = 60 if additional else 30
    if not 1 <= batch_size <= limit:
        raise ValueError(f'batch_size must be 1..{limit}')
    archive = read(ARCHIVE, {})
    verified = read(VERIFIED, {}).get('records', [])
    decisions = read(REVIEW, {}).get('records', [])
    finished = {x['candidate_id'] for x in [*verified, *decisions]
                if isinstance(x, dict) and x.get('candidate_id')}
    existing = all_manifests()
    reserved = {row['candidate_id'] for manifest in existing.values()
                for row in manifest.get('jobs', []) if row.get('candidate_id') not in finished}
    prior_manifest = read(MANIFEST, {})
    outstanding = prior_manifest.get('jobs', [])
    pending_ids = {row.get('candidate_id') for row in outstanding}
    if not additional:
        # Old pending_manifest.json and packages remain untouched, even if they
        # are still awaiting review or were just imported in the live repository.
        # New-policy packages are reserved in the existing packages/ namespace,
        # which all_manifests()/import-inbox already understand.  This prevents
        # legacy unfinished reviews from blocking future policy-focused reviews.
        current_scope_outstanding = sorted((m for m in existing.values()
            if m.get('focus_scope_id') == FOCUS_SCOPE_ID
            and any(row.get('candidate_id') not in finished for row in m.get('jobs', []))),
            key=lambda m: (m.get('generated_at') or '', m.get('package_id') or ''))
        if current_scope_outstanding:
            manifest = current_scope_outstanding[0]
            write_review_artifact(manifest, artifact)
            print(f'Current-policy Relevance Focus Deep Scan package: '
                  f'{len(manifest["jobs"])} cases, {manifest["package_id"]}')
            return manifest
        new_scope_available = [x for x in archive.get('candidates', [])
            if isinstance(x, dict) and x.get('focus_scope_id') == FOCUS_SCOPE_ID
            and valid_v4_lead(x) and x['candidate_id'] not in finished
            and x['candidate_id'] not in reserved]
        if new_scope_available:
            jobs = balanced_review_jobs(new_scope_available, batch_size)
            key = '|'.join(x['candidate_id'] for x in jobs)
            package_id = 'rfds-' + hashlib.sha256(key.encode()).hexdigest()[:18]
            if package_id in existing:
                raise ValueError('New policy package identifier already reserved')
            manifest = {'format': RESULT_FORMAT, 'package_id': package_id,
                        'generated_at': datetime.now(timezone.utc).isoformat(),
                        'focus_scope_id': FOCUS_SCOPE_ID,
                        'global_scope': 'All 10 critical technologies OR geographically targeted regional R&I priorities; no EU relevance required',
                        'jobs': jobs}
            atomic_write(PACKAGES / f'{package_id}.json', manifest)
            write_review_artifact(manifest, artifact)
            print(f'Current-policy Relevance Focus Deep Scan package: '
                  f'{len(jobs)} cases, {package_id}')
            return manifest
    if additional:
        # Catch-up mode for Relevance Focus ONLY: an assignment is not a scan.
        # Revisit unfinished jobs from the oldest registered manifests, even if
        # they are no longer present in the current discovery archive.
        candidates = []
        seen = set()
        oldest_first = sorted(existing.values(), key=lambda m: (
            m.get('generated_at') or '', m.get('package_id') or ''))
        for old in oldest_first:
            for row in old.get('jobs', []):
                cid = row.get('candidate_id')
                if cid and cid not in finished and cid not in seen and valid_v4_lead(row):
                    candidates.append(row)
                    seen.add(cid)
        # Fill remaining capacity using never-assigned discoveries.
        fresh = [x for x in archive.get('candidates', [])
                 if valid_v4_lead(x) and x['candidate_id'] not in finished
                 and x['candidate_id'] not in seen]
        fresh.sort(key=lambda x: (-int(x.get('focus_score') or 0), x['candidate_id']))
        candidates.extend(fresh)
        jobs = candidates[:batch_size]
    elif outstanding and pending_ids - finished:
        # Preserve original Relevance Focus scan behavior and package identity.
        jobs = outstanding
    else:
        available = [x for x in archive.get('candidates', [])
                     if valid_v4_lead(x) and x['candidate_id'] not in finished
                     and x['candidate_id'] not in (reserved - pending_ids)]
        jobs = balanced_review_jobs(available, batch_size)
    jobs = jobs[:batch_size]
    key = '|'.join(x['candidate_id'] for x in jobs)
    package_id = ('rfds-' + hashlib.sha256(key.encode()).hexdigest()[:18])
    if not additional and outstanding and pending_ids - finished:
        package_id = prior_manifest['package_id']
    manifest = {'format': RESULT_FORMAT, 'package_id': package_id,
                'generated_at': (prior_manifest.get('generated_at') if not additional and outstanding and pending_ids - finished
                                 else datetime.now(timezone.utc).isoformat()),
                'global_scope': 'No EU relevance required; topical aboutness and R&I futures only',
                'jobs': jobs}
    if additional:
        # Do not overwrite an active original package or other extra package.
        # An empty queue is reported to the caller without creating a reservation.
        if jobs:
            previous = existing.get(package_id)
            if previous:
                if previous.get('jobs') != jobs:
                    raise ValueError('Package identifier collision')
                # Package IDs depend on ordered candidate IDs. Re-running catch-up
                # must keep the original timestamp/metadata, not rewrite history.
                manifest = previous
            else:
                atomic_write(PACKAGES / f'{package_id}.json', manifest)
    else:
        atomic_write(MANIFEST, manifest)
    write_review_artifact(manifest, artifact)
    print(f'Global Relevance Focus Deep Scan package: {len(jobs)} cases, {package_id}')
    return manifest


def text_field(value, field, *, minimum=20):
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValueError(f'Missing substantive reviewer evidence in {field}')
    return value.strip()


def safe_url(value):
    return isinstance(value, str) and bool(re.fullmatch(r'https?://[^\s/]+/[^\s]+', value))


def validate_result(result, lead):
    if not isinstance(result, dict) or result.get('candidate_id') != lead['candidate_id']:
        raise ValueError('Result identity does not match manifest candidate')
    decision = result.get('decision')
    if decision not in DECISIONS:
        raise ValueError('Unknown review decision')
    # Scope metadata belongs to NEW decisions only.  Old imports retain their
    # original schema and will not be reclassified or rewritten.
    policy_metadata = ({
        'focus_scope_id': lead['focus_scope_id'],
        'focus_priority_track': lead['focus_priority_track']
    } if lead.get('focus_scope_id') == FOCUS_SCOPE_ID else {})
    if decision != 'keep':
        # The Deep Scan template historically taught models to supply a detailed
        # decision_basis, while the importer only accepted review_reason. Accept
        # either substantive explanation; keep a canonical review_reason for
        # downstream consumers. Do not reduce the evidence-length requirement.
        reason = result.get('review_reason')
        if not isinstance(reason, str) or len(reason.strip()) < 20:
            reason = result.get('decision_basis')
        reason = text_field(reason, 'review_reason or decision_basis')
        return {**result, **policy_metadata, 'review_reason': reason,
                'title': lead['title'], 'focus_region': lead['focus_region'],
                'focus_issue': lead['focus_issue'], 'url': lead['url']}
    src, geo, topic, fut = (result.get(k) for k in
                            ('source_verification','aboutness','topic','futures'))
    if any(not isinstance(x, dict) for x in (src, geo, topic, fut)):
        raise ValueError('KEEP requires four independently reviewed evidence sections')
    if (src.get('identity_verified') is not True or not safe_url(src.get('primary_url'))
            or src.get('source_integrity') not in INTEGRITIES
            or src.get('propaganda_or_influence_risk') not in RISKS
            or not src.get('source_type')):
        raise ValueError('KEEP lacks verified primary source, integrity or risk audit')
    if src['source_integrity'] not in {'independent_credible', 'credible_primary_claim_only'} or src['propaganda_or_influence_risk'] != 'none_identified':
        raise ValueError('KEEP prohibited by unverified/unreliable or propaganda-risk source')
    text_field(src.get('basis'), 'source_verification.basis', minimum=50)
    if not isinstance(src.get('independent_corrob_urls'), list) or any(
            not safe_url(u) for u in src['independent_corrob_urls']):
        raise ValueError('Corroboration links must be a list of genuine URLs')
    if (geo.get('is_substantive') is not True or geo.get('publisher_country_only') is not False
            or geo.get('place') != lead['focus_region']):
        raise ValueError('KEEP must establish the substantive manifest geography, not publisher nationality')
    text_field(geo.get('basis'), 'aboutness.basis')
    text_field(geo.get('verified_excerpt'), 'aboutness.verified_excerpt')
    if topic.get('is_relevant') is not True or topic.get('label') != lead['focus_issue']:
        raise ValueError('KEEP must independently confirm the assigned focus priority')
    if lead.get('focus_scope_id') == FOCUS_SCOPE_ID and not valid_v4_lead(lead):
        raise ValueError('KEEP cannot admit a new-policy theme outside its technology/region scope')
    text_field(topic.get('basis'), 'topic.basis')
    if fut.get('classification') not in {'observed', 'possible', 'mixed'}:
        raise ValueError('Future status must separate observed from possible')
    for name in ('mechanism','why_could_matter','uncertainty','research_question'):
        text_field(fut.get(name), 'futures.' + name)
    if not str(fut['research_question']).strip().endswith('?'):
        raise ValueError('Futures investigation must be framed as a question')
    return {**result, **policy_metadata, 'title': lead['title'], 'date': lead['date'],
            'source': lead['source'], 'focus_region': lead['focus_region'],
            'focus_group': lead['focus_group'], 'focus_issue': lead['focus_issue'],
            'url': lead['url'], 'doi': lead['doi'],
            'verified_at': datetime.now(timezone.utc).isoformat()}


def import_inbox():
    manifests = all_manifests()
    verified = read(VERIFIED, {'format': RESULT_FORMAT, 'records': []})
    review = read(REVIEW, {'format': RESULT_FORMAT, 'records': []})
    done = {r['candidate_id'] for r in verified['records'] + review['records']}
    changed = 0
    staged = []
    all_new = set()
    for file in sorted(INBOX.glob('*.json')) if INBOX.exists() else []:
        data = read(file, {})
        manifest = manifests.get(data.get('package_id'))
        if data.get('format') != RESULT_FORMAT or manifest is None:
            raise ValueError(f'{file.name}: unknown/replayed package or format')
        indexed = {x['candidate_id']: x for x in manifest.get('jobs', [])}
        if not isinstance(data.get('results'), list) or not data['results']:
            raise ValueError(f'{file.name}: empty/malformed results')
        local_seen = set()
        accepted = []
        for result in data['results']:
            cid = result.get('candidate_id') if isinstance(result, dict) else None
            if cid not in indexed or cid in local_seen:
                raise ValueError(f'{file.name}: unassigned/duplicate candidate')
            local_seen.add(cid)
            if cid not in done:
                if cid in all_new:
                    raise ValueError(f'{file.name}: duplicate review submitted in another inbox file')
                accepted.append(validate_result(result, indexed[cid]))
                all_new.add(cid)
        stamp = hashlib.sha256(file.read_bytes()).hexdigest()[:12]
        dest_path = PROCESSED / f'{file.stem}_{stamp}.json'
        if dest_path.exists():
            raise ValueError('Already processed inbox submission')
        staged.append((file, dest_path, accepted, manifest['package_id']))
    # Fail closed for the ENTIRE inbox before persisting any review result.
    for _file, _dest, accepted, package_id in staged:
        for item in accepted:
            dest = verified if item['decision'] == 'keep' else review
            dest['records'].append({**item, 'verified_package_id': package_id})
            changed += 1
    if changed:
        atomic_write(VERIFIED, verified)
        atomic_write(REVIEW, review)
    if staged:
        PROCESSED.mkdir(parents=True, exist_ok=True)
    for file, dest_path, _accepted, _package_id in staged:
        shutil.move(str(file), str(dest_path))
    print(f'Imported {changed} independently reviewed global R&I relevance decisions')
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare','import-inbox'])
    parser.add_argument('--batch-size', type=int, default=30)
    parser.add_argument('--artifact', type=Path)
    parser.add_argument('--additional', action='store_true', help='Prepare a catch-up Relevance Focus package, including unfinished older assignments (up to 60)')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(batch_size=args.batch_size, artifact=args.artifact, additional=args.additional)
    else:
        import_inbox()


if __name__ == '__main__':
    main()
