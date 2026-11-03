#!/usr/bin/env python3
"""Prepare and import evidence-first Global R&I Deep Scan packages.

A package queues REAL linked documents (discovery leads and/or existing main-Radar
works). It is NOT itself verification. A browsing-capable reviewer must return
source-checked results. Only a validated KEEP becomes a verified global finding.
All persistent writes remain under Global R&I Blind Spots/deep_scan/.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone, date
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import zipfile

try:
    from scripts import global_blind_spots as g
except ImportError:
    import global_blind_spots as g

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'Global R&I Blind Spots'
DEEP = BASE / 'deep_scan'
SCHEMA = 'global-ri-deep-scan-v1'
STRANDS = {'strand_a': 'A', 'strand_b': 'B', 'strand_c': 'C'}
MIN_KEEP = {'finding': 85, 'evidence': 70, 'relevance': 65, 'limitations': 35}


def https_url(value):
    if not isinstance(value, str) or len(value) > 1800 or '\\' in value or any(ord(c) < 32 for c in value):
        return False
    try:
        p = urlsplit(value)
        return p.scheme == 'https' and bool(p.hostname) and not p.username and not p.password and (p.port is None or p.port == 443)
    except ValueError:
        return False


def canonical_url(url):
    if not https_url(url):
        return ''
    p = urlsplit(url)
    host = (p.hostname or '').lower()
    path = p.path.rstrip('/') or '/'
    if host in ('doi.org', 'www.doi.org', 'dx.doi.org'):
        return 'https://doi.org/' + path.lstrip('/').casefold()
    # Tracking parameters are not part of an item's identity, but non-tracking
    # parameters may distinguish legitimate pages (e.g. repository works).
    query = urlencode(sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                           if not (k.lower().startswith('utm_') or k.lower() in ('fbclid', 'gclid'))))
    return urlunsplit(('https', host, path, query, ''))


def text_id(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:24]


def clean_title(text):
    return g.norm(text).strip()


def title_key(text):
    return re.sub(r'[^a-z0-9]+', '', clean_title(text).casefold())


def document_key(url, title):
    uri = canonical_url(url)
    if uri:
        return text_id('link|' + uri)
    return text_id('title|' + title_key(title))


def record_url(item):
    for k in ('link', 'url', 'doi'):
        u = str(item.get(k) or '')
        if https_url(u):
            return u
    return ''


def main_radar_matches(radar, config):
    """Ground candidate records in actual works, not country mentions in generic summaries.

    Country must occur in a *substantive* field (title, main message, WHAT,
    relevance note). Summary-only country matches can occur incidentally and
    therefore do not qualify without stronger bibliographic identification.
    """
    output = {}
    for strand, mark in STRANDS.items():
        for item in radar.get(strand, []):
            if not isinstance(item, dict):
                continue
            title, url = clean_title(item.get('title')), record_url(item)
            if len(title) < 25 or not url or 'news.google.com/' in url:
                continue
            subject = ' '.join(str(item.get(x) or '') for x in ('title', 'core_message', 'reader_what', 'relevance_note'))
            detailed = subject + ' ' + str(item.get('summary') or '')[:1000]
            for region, aliases in config['regions'].items():
                if not g.find_terms(subject, aliases):
                    continue
                for theme, d in config['themes'].items():
                    matched = g.find_terms(detailed, d['terms'])
                    if not matched:
                        continue
                    # Explicitly geo-named works are preferred over incidental references.
                    named = bool(g.find_terms(title, aliases))
                    subject_theme = bool(g.find_terms(subject, d['terms']))
                    if not (named or subject_theme):
                        continue
                    key = document_key(url, title)
                    entity = {'candidate_id': text_id(key + '|' + region + '|' + theme),
                              'document_key': key, 'title': title, 'url': url,
                              'date': str(item.get('date') or '')[:10], 'region': region,
                              'theme': theme, 'source': str(item.get('source') or ''),
                              'source_kind': 'existing_main_radar_record',
                              'provenance': 'main_radar',
                              'main_radar_links': [{'strand': mark, 'title': title, 'url': url,
                                                    'deep_scan_authoritative': item.get('deep_scan_authoritative') is True}],
                              'original_context': g.norm(item.get('core_message') or item.get('reader_what') or item.get('summary'))[:1100],
                              'radar_overlap': 'exact',
                              'assessment_status': 'not_independently_verified_by_global_deep_scan',
                              'theme_terms': matched[:5], 'region_in_title': named}
                    # One document can be relevant to more than one theme, but
                    # deep reading is once per document/region. Keep the better match.
                    pair = (key, region)
                    prev = output.get(pair)
                    weight = (4 if named else 0) + (3 if subject_theme else 0) + len(matched)
                    if prev is None or weight > prev[0]:
                        output[pair] = (weight, entity)
    return [pair[1] for pair in sorted(output.values(), key=lambda x: (-x[0], x[1]['region'], x[1]['title']))]


def main_radar_index(radar):
    # Exact identity check across ALL active main-Radar entries, including works
    # that did not pass our deliberately narrow Global seed filter.
    by_url, by_title = {}, {}
    for strand, mark in STRANDS.items():
        for original in radar.get(strand, []):
            if not isinstance(original, dict):
                continue
            url = record_url(original)
            title = clean_title(original.get('title'))
            if not url or len(title) < 25:
                continue
            obj = {'main_radar_links': [{'strand': mark, 'title': title, 'url': url,
                    'deep_scan_authoritative': original.get('deep_scan_authoritative') is True}]}
            by_url[canonical_url(url)] = obj
            by_title[title_key(title)] = obj
    return by_url, by_title


def discoverable_candidates(base, config, radar_candidates, radar=None):
    items = []
    paths = [base / 'archive.json', base / 'latest.json']
    seen = set()
    radar_by_url, radar_by_title = main_radar_index(radar) if radar is not None else (
        {canonical_url(x['url']): x for x in radar_candidates},
        {title_key(x['title']): x for x in radar_candidates})
    for path in paths:
        if not path.exists():
            continue
        doc = g.load_json(path)
        for original in doc.get('items', []):
            if not isinstance(original, dict):
                continue
            url = original.get('url') or ''
            title = clean_title(original.get('title'))
            region, theme = original.get('region'), original.get('theme')
            if not https_url(url) or len(title) < 25 or region not in config['regions'] or theme not in config['themes']:
                continue
            canon = canonical_url(url)
            marker = (canon, region)
            if marker in seen:
                continue
            seen.add(marker)
            exact = radar_by_url.get(canon) or radar_by_title.get(title_key(title))
            key = document_key(url, title)
            items.append({'candidate_id': text_id(key + '|' + region + '|' + theme),
                          'document_key': key, 'title': title, 'url': url,
                          'date': original.get('date') or '', 'region': region, 'theme': theme,
                          'source': original.get('source') or '',
                          'source_kind': original.get('source_kind') or 'discovery',
                          'provenance': 'global_discovery',
                          'main_radar_links': exact['main_radar_links'] if exact else [],
                          'original_context': (original.get('abstract_or_context') or '')[:1100],
                          'radar_overlap': 'exact' if exact else 'not_identified',
                          'assessment_status': 'discovery_candidate_not_verified',
                          'theme_terms': original.get('issue_terms') or [],
                          'region_in_title': bool(g.find_terms(title, config['regions'][region]))})
    return items


def curated_source_candidates(config, radar_candidates, path=ROOT / 'global_deep_scan_source_leads.json', radar=None):
    if not path.exists():
        return []
    obj = g.load_json(path)
    radar_by_url, radar_by_title = main_radar_index(radar) if radar is not None else (
        {canonical_url(x['url']): x for x in radar_candidates},
        {title_key(x['title']): x for x in radar_candidates})
    result = []
    for row in obj.get('items', []):
        region, theme = row.get('region'), row.get('theme')
        title, url = clean_title(row.get('title')), row.get('url') or ''
        if region not in config['regions'] or theme not in config['themes'] or len(title) < 25 or not https_url(url):
            continue
        key = document_key(url, title)
        exact = radar_by_url.get(canonical_url(url)) or radar_by_title.get(title_key(title))
        result.append({'candidate_id': text_id(key + '|' + region + '|' + theme),
                       'document_key': key, 'title': title, 'url': url,
                       'date': row.get('date') or '', 'region': region, 'theme': theme,
                       'source': row.get('source') or '', 'source_kind': row.get('source_kind') or 'curated_source',
                       'provenance': 'curated_high_quality_source',
                       'main_radar_links': exact['main_radar_links'] if exact else [],
                       'original_context': row.get('context') or '',
                       'radar_overlap': 'exact' if exact else 'not_identified',
                       'assessment_status': 'verified_source_identity_not_yet_verified_finding',
                       'theme_terms': [], 'region_in_title': True})
    return result


def load_completed(deep):
    path = deep / 'verified_findings.json'
    if not path.exists():
        return set()
    doc = g.load_json(path)
    return {(row['document_key'], row.get('region', '')) for row in doc.get('items', [])
            if row.get('decision') in ('KEEP', 'DROP', 'REVIEW') and row.get('document_key')}


def plan_queue(radar, config, base=BASE, deep=DEEP, batch_size=12):
    main = main_radar_matches(radar, config)
    new = discoverable_candidates(base, config, main, radar=radar)
    curated = curated_source_candidates(config, main, radar=radar)
    completed = load_completed(deep)
    # A discovery record representing a work already in main Radar is one
    # package item with both provenances, never a 'new finding' by default.
    merged = {}
    for row in curated + new + main:
        doc = (row['document_key'], row['region'])
        if doc in completed:
            continue
        prev = merged.get(doc)
        if not prev:
            merged[doc] = dict(row)
        else:
            prev['main_radar_links'] = prev['main_radar_links'] or row['main_radar_links']
            prev['radar_overlap'] = 'exact' if prev['main_radar_links'] else 'not_identified'
            if prev['provenance'] == 'main_radar' and row['provenance'] == 'global_discovery':
                prev['provenance'] = 'both_main_radar_and_global_discovery'
                if row['original_context']:
                    prev['discovery_context'] = row['original_context']
            elif prev['provenance'] == 'global_discovery' and row['provenance'] == 'main_radar':
                prev['provenance'] = 'both_main_radar_and_global_discovery'
        # Prefer distinct country subject rather than generic comparative prose.
    rows = list(merged.values())
    def score(x):
        origin_bonus = {'curated_high_quality_source': 40, 'global_discovery': 30,
                        'both_main_radar_and_global_discovery': 31}.get(x['provenance'], 12)
        return origin_bonus + (10 if x.get('region_in_title') else 0) + (5 if x['radar_overlap'] == 'exact' else 0)
    rows.sort(key=lambda r: (-score(r), r['region'], r['theme'], r.get('date', ''), r['document_key']))
    # Balanced country × theme rotation; do not invent an empty cell.
    cells = [(region, theme) for region in config['regions'] for theme in config['themes']]
    by_cell = {(r, t): [] for r, t in cells}
    for row in rows:
        by_cell[(row['region'], row['theme'])].append(row)
    selected = []
    while len(selected) < batch_size and any(by_cell.values()):
        for cell in cells:
            if by_cell[cell] and len(selected) < batch_size:
                selected.append(by_cell[cell].pop(0))
    return selected, {'main_radar_eligible': len(main), 'global_discovery_eligible': len(new), 'curated_source_eligible': len(curated),
                      'distinct_pending_documents': len(rows), 'previously_reviewed_documents': len(completed),
                      'selected': len(selected),
                      'by_region': dict(Counter(r['region'] for r in selected))}


INSTRUCTIONS = r'''# Global R&I Deep Scan — source-grounded verification

**Mission:** Find what an EU-focused Radar might have missed in US, China or
Russia R&I. A finding can ALREADY be present in the main Radar. Never drop a
relevant work merely because it is covered, and never fabricate an omitted one.

This GitHub action PREPARES candidate documents. The substantive deep reading
is done separately using a browsing-capable researcher/LLM with this package.
The original Radar text is a hypothesis, not source confirmation. This worker
MUST open the real linked source and establish its identity, actual content,
date, mechanism and relevance. Search for independent support or counterevidence.
Use original-language material where accessible, with careful translation and
uncertainty. Do not treat press releases from any country as independent proof.

**Work through every assigned item:** Check the primary URL, DOI and title,
publisher or institutional repository, date, full accessible article/report or
substantive sections, methods and limitations, and corroboration. If a source
is blocked, search by exact title, author, DOI, publisher repository and
archival editions. No guessing from headlines, snippets or metadata. A related
work is not a substitute for the assigned one. For contested national
performance claims (particularly China and Russia), identify independent
verification or explicitly return REVIEW and describe what remains uncertain.

For each item, choose:
- `KEEP`: verified substantive R&I development, evidence-based trend or
  meaningful method; full detailed analysis + at least one independently
  sourced corroborating document on a DIFFERENT domain.
- `REVIEW`: real candidate but source, meaning or corroboration unresolved;
  explain exactly why. Never promote to verified findings.
- `DROP`: unsupported, untraceable, not substantive R&I, duplicate or not
  about stated region; explain why. This does not modify the main Radar.

Check any existing main Radar entry independently. Record whether the new
analysis **confirms**, **changes**, or **extends** that entry. If not in main
Radar, label **not_in_main_radar**. This is a *coverage comparison*, not a
validity verdict. The only `verified_findings` are source-grounded `KEEP`s.

The `source_identity_basis` field must explain how the opened primary-source
content, authors/issuing organisation and date match the assigned work.
A DOI redirect or new publisher URL is acceptable ONLY when its identity
is independently established in that field.

**Output:** a JSON file named `global_deep_scan_results.json` with the SAME
`package_id` and candidate IDs as `manifest.json`, shaped as `RESULT_TEMPLATE.json`.
Use only exact source URLs that you actually opened. Include an independent
corroborating URL, evidence page/section/table, concrete finding, mechanism,
limitations, regional R&I significance and a sober EU comparison. If you lack
credible source access, do not return KEEP. Other optional metadata is fine;
the importer rejects missing required evidence. No API payment is required in
GitHub. Only validated, explicitly reviewed results are imported manually.
'''


def result_template(manifest):
    results = []
    for x in manifest['items']:
        results.append({'candidate_id': x['candidate_id'], 'decision': 'REVIEW',
                        'verified_title': '', 'verified_primary_url': '', 'source_identity_basis': '', 'source_date': '',
                        'source_type': '', 'evidence_location': '',
                        'specific_finding': '', 'primary_evidence_summary': '',
                        'corroboration_urls': [], 'corroboration_assessment': '',
                        'mechanism_and_ri_importance': '', 'eu_radar_comparison': '',
                        'comparison_type': 'not_in_main_radar',
                        'method_and_limitations': '', 'confidence': 'low',
                        'reason_for_review_or_drop': 'UNFINISHED — replace with actual checked evidence',
                        'reviewer_notes': ''})
    return {'schema': SCHEMA, 'package_id': manifest['package_id'], 'results': results}


def prepare(base=BASE, deep=DEEP, radar_file=ROOT / 'radar_active.json', config_file=ROOT / 'global_blind_spots_config.json', batch_size=12, artifact=None):
    if not 1 <= batch_size <= 24:
        raise ValueError('batch size must be from 1 to 24')
    radar, config = g.load_json(radar_file), g.load_json(config_file)
    # Reuse any pending work so an accidental second Prepare cannot invalidate
    # the JSON a reviewer is already preparing for a previous package.
    pending_path = deep / 'pending_manifest.json'
    completed = load_completed(deep)
    prior = g.load_json(pending_path) if pending_path.exists() else None
    unfinished = [x for x in (prior or {}).get('items', [])
                  if (x['document_key'], x.get('region', '')) not in completed]
    if prior and prior.get('schema') == SCHEMA and unfinished:
        manifest = prior
        selected = prior['items']
        package_id = prior['package_id']
        print(f'Reusing pending package {package_id}: {len(unfinished)} records still awaiting review.')
    else:
        selected, diagnostics = plan_queue(radar, config, base, deep, batch_size)
        if not selected:
            raise ValueError('No eligible source-backed candidate documents available; run Global discovery or inspect Radar data.')
        batch_key = '|'.join(x['candidate_id'] for x in selected)
        package_id = 'gri-' + text_id(batch_key)
        manifest = {'schema': SCHEMA, 'package_id': package_id,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'mission': 'Verify global R&I developments and compare them with actual main Radar coverage',
                    'review_protocol': 'source_grounded_with_independent_corroboration',
                    'items': selected, 'diagnostics': diagnostics}
    deep.mkdir(parents=True, exist_ok=True)
    (deep / 'pending_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (deep / 'QUEUE.md').write_text('# Global R&I Deep Scan — pending verification\n\n'
         + f'Package: `{package_id}`. {len(selected)} documents. **These are unverified candidates**, not confirmed findings.\n\n'
         + '| Country | Theme | Work | Already in Radar? |\n|---|---|---|---|\n'
         + '\n'.join(f'| {x["region"]} | {x["theme"]} | [{x["title"].replace("|", " ")}]({x["url"]}) | '
                    f'{"Yes" if x["radar_overlap"] == "exact" else "Not identified"} |' for x in selected) + '\n', encoding='utf-8')
    path = Path(artifact) if artifact is not None else deep / 'global_deep_scan_package.zip'
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('INSTRUCTIONS.md', INSTRUCTIONS)
        z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        z.writestr('RESULT_TEMPLATE.json', json.dumps(result_template(manifest), ensure_ascii=False, indent=2) + '\n')
        z.writestr('HOW_TO_RETURN.md', 'Complete actual source checks as required by INSTRUCTIONS.md.\n'
                   'Upload `global_deep_scan_results.json` to `Global R&I Blind Spots/deep_scan/inbox/` '
                   'in the main branch. The import then runs automatically, or use the Deep Scan action with operation `import`.\n'
                   'Do not present the package or template as verified findings.\n')
    return manifest, path


def check_sensible_text(value, min_len=0, max_len=12000):
    return isinstance(value, str) and min_len <= len(value.strip()) <= max_len


def source_family(url):
    host = (urlsplit(url).hostname or '').lower()
    parts = host.split('.')
    if len(parts) < 2:
        return host
    if len(parts) >= 3 and parts[-2] in ('co', 'com', 'gov', 'org', 'ac') and parts[-1] in ('uk', 'au', 'nz', 'jp', 'cn'):
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:])


def validate_result(raw, manifest_row):
    errors = []
    rid = manifest_row['candidate_id']
    decision = raw.get('decision')
    if raw.get('candidate_id') != rid:
        errors.append('candidate_id does not match')
    if decision not in ('KEEP', 'REVIEW', 'DROP'):
        errors.append('decision must be KEEP, REVIEW or DROP')
    if decision == 'KEEP':
        for key, n in (('verified_title', 20), ('source_identity_basis', 60), ('source_type', 5), ('evidence_location', 10),
                       ('specific_finding', MIN_KEEP['finding']),
                       ('primary_evidence_summary', MIN_KEEP['evidence']),
                       ('mechanism_and_ri_importance', MIN_KEEP['relevance']),
                       ('method_and_limitations', MIN_KEEP['limitations']),
                       ('eu_radar_comparison', 45), ('corroboration_assessment', 50)):
            if not check_sensible_text(raw.get(key), n):
                errors.append(f'{key} requires substantive source-checked text (>= {n} characters)')
        if not https_url(raw.get('verified_primary_url')):
            errors.append('verified_primary_url must be a real HTTPS primary source')
        try:
            sourced = date.fromisoformat(str(raw.get('source_date') or ''))
            if sourced > datetime.now(timezone.utc).date():
                raise ValueError('future date')
        except ValueError:
            errors.append('source_date must be a valid past/present YYYY-MM-DD; otherwise REVIEW')
        if raw.get('confidence') not in ('high', 'medium'):
            errors.append('KEEP confidence must be high or medium')
        if raw.get('comparison_type') not in ('confirms_main_radar', 'changes_main_radar',
                                              'extends_main_radar', 'not_in_main_radar'):
            errors.append('comparison_type is invalid')
        if manifest_row['radar_overlap'] == 'exact' and raw.get('comparison_type') == 'not_in_main_radar':
            errors.append('record is already in main Radar; compare and classify it')
        evidence = raw.get('corroboration_urls')
        if not isinstance(evidence, list) or not evidence or len(evidence) > 6:
            errors.append('KEEP needs at least one independent corroboration URL')
        else:
            if not all(https_url(u) for u in evidence):
                errors.append('all corroboration_urls must be HTTPS')
            elif canonical_url(raw.get('verified_primary_url')) in [canonical_url(u) for u in evidence]:
                errors.append('corroboration cannot be the same article as primary')
            elif source_family(raw.get('verified_primary_url')) in {source_family(u) for u in evidence}:
                errors.append('corroboration must not be on the same host or source family as the primary source')
    elif decision in ('REVIEW', 'DROP'):
        if not check_sensible_text(raw.get('reason_for_review_or_drop'), 65):
            errors.append(f'{decision} needs a concrete explanation (>=65 characters)')
    return errors


def safe_markdown(text):
    return str(text or '').replace('<', '&lt;').replace('>', '&gt;').replace('|', '\\|').replace('\n', ' ').strip()


def import_results(results_path, deep=DEEP):
    manifest = g.load_json(deep / 'pending_manifest.json')
    results = g.load_json(results_path)
    if results.get('schema') != SCHEMA or manifest.get('schema') != SCHEMA:
        raise ValueError('schema mismatch')
    if results.get('package_id') != manifest['package_id']:
        raise ValueError('package_id does not match pending manifest')
    incoming = results.get('results')
    if not isinstance(incoming, list) or not incoming or len(incoming) > len(manifest['items']):
        raise ValueError('results must be a nonempty subset of pending manifest')
    work = {x['candidate_id']: x for x in manifest['items']}
    checked = []
    unique = set()
    failures = []
    for i, item in enumerate(incoming):
        if not isinstance(item, dict):
            failures.append(f'index {i}: not an object')
            continue
        ident = item.get('candidate_id')
        if not isinstance(ident, str) or ident not in work or ident in unique:
            failures.append(f'index {i}: unknown/duplicate candidate_id')
            continue
        unique.add(ident)
        errors = validate_result(item, work[ident])
        if errors:
            failures.append(f'{ident}: ' + '; '.join(errors))
        checked.append((work[ident], item))
    if failures:
        raise ValueError('Import REJECTED, nothing changed:\n' + '\n'.join(failures))
    existing_path = deep / 'verified_findings.json'
    existing = g.load_json(existing_path) if existing_path.exists() else {'schema': SCHEMA, 'items': []}
    archived = {(r['document_key'], r.get('region', '')): r for r in existing.get('items', [])}
    timestamp = datetime.now(timezone.utc).isoformat()
    for c, result in checked:
        # Reject the false notion that merely 'REVIEW' is a verified finding.
        row = {**c, **result, 'package_id': manifest['package_id'],
               'reviewed_at': timestamp,
               'verification_status': 'verified_with_reported_sources' if result['decision'] == 'KEEP' else 'unverified_or_excluded'}
        archived[(c['document_key'], c['region'])] = row
    archive = {'schema': SCHEMA, 'updated_at': timestamp,
               'items': sorted(archived.values(), key=lambda x: (x.get('reviewed_at') or '', x['document_key']), reverse=True)}
    kept = [r for r in archive['items'] if r.get('decision') == 'KEEP']
    # Construct all outputs in memory before any write, and do not mutate
    # pending manifest / results or any file from the main Radar.
    lines = ['# Global R&I Deep Scan — verified findings', '',
             f'Imported: {timestamp}. **{len(kept)} verified KEEP** findings, '
             f'**{sum(r.get("decision") == "REVIEW" for r in archive["items"])} REVIEW**, '
             f'**{sum(r.get("decision") == "DROP" for r in archive["items"])} DROP**.', '',
             'A KEEP records a source-checked reviewer assessment; the GitHub importer validates '
             'evidence structure but does not itself browse or certify truth.', '']
    for row in kept:
        lines += [f'## {safe_markdown(row["title"])}', '',
                  f'**{row["region"]} · {row["theme"]}** | {row["source_date"]} | confidence {row["confidence"]}', '',
                  f'**Verified finding:** {safe_markdown(row["specific_finding"])}', '',
                  f'**Evidence:** [{safe_markdown(row["verified_title"])}]({row["verified_primary_url"]}) '
                  f'— {safe_markdown(row["evidence_location"])}.', '',
                  f'**Independent check:** {safe_markdown(row["corroboration_assessment"])} '
                  + ' '.join(f'[{i+1}]({u})' for i, u in enumerate(row['corroboration_urls'])), '',
                  f'**Why global R&I matters:** {safe_markdown(row["mechanism_and_ri_importance"])}', '',
                  f'**Main Radar comparison ({row["comparison_type"]}):** {safe_markdown(row["eu_radar_comparison"])}', '',
                  f'**Limitations:** {safe_markdown(row["method_and_limitations"])}', '']
        for match in row['main_radar_links']:
            lines.append(f'- Existing main Radar {match["strand"]}: [{safe_markdown(match["title"])}]({match["url"]})')
        lines.append('')
    if not kept:
        lines += ['No verified findings have been admitted yet. REVIEW and DROP are not presented as findings.', '']
    csv_keys = ['region', 'theme', 'title', 'date', 'decision', 'verification_status', 'source_date',
                'source_type', 'specific_finding', 'mechanism_and_ri_importance',
                'comparison_type', 'eu_radar_comparison', 'confidence', 'verified_primary_url',
                'corroboration_urls', 'radar_overlap', 'provenance', 'package_id']
    import io
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=csv_keys, extrasaction='ignore')
    writer.writeheader()
    for row in kept:
        flattened = {**row, 'corroboration_urls': ' | '.join(row['corroboration_urls'])}
        writer.writerow({k: "'" + str(flattened.get(k, '')) if isinstance(flattened.get(k), str) and
                        flattened[k].lstrip().startswith(('=', '+', '-', '@')) else flattened.get(k, '') for k in csv_keys})
    deep.mkdir(parents=True, exist_ok=True)
    existing_path.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (deep / 'VERIFIED_FINDINGS.md').write_text('\n'.join(lines), encoding='utf-8')
    (deep / 'verified_findings.csv').write_text('\ufeff' + buffer.getvalue(), encoding='utf-8')
    (deep / 'last_import.json').write_text(json.dumps({'schema': SCHEMA, 'package_id': manifest['package_id'],
                                'processed': len(checked), 'kept_this_import': sum(x['decision'] == 'KEEP' for _, x in checked),
                                'review_this_import': sum(x['decision'] == 'REVIEW' for _, x in checked),
                                'drop_this_import': sum(x['decision'] == 'DROP' for _, x in checked),
                                'total_verified_keep': len(kept), 'imported_at': timestamp}, indent=2) + '\n', encoding='utf-8')
    return {'processed': len(checked), 'verified_keep': len(kept)}


def cli(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--batch-size', type=int, default=12)
    prep.add_argument('--artifact', type=Path)
    prep.add_argument('--radar', type=Path, default=ROOT / 'radar_active.json')
    prep.add_argument('--base', type=Path, default=BASE)
    prep.add_argument('--deep', type=Path, default=DEEP)
    imp = sub.add_parser('import')
    imp.add_argument('--results', type=Path, default=DEEP / 'inbox' / 'global_deep_scan_results.json')
    imp.add_argument('--deep', type=Path, default=DEEP)
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare':
            manifest, path = prepare(base=args.base, deep=args.deep, radar_file=args.radar,
                                     batch_size=args.batch_size, artifact=args.artifact)
            print(f'Prepared {len(manifest["items"])} actual linked candidates, package={manifest["package_id"]}, artifact={path}')
            print('Source-review package only: zero new verified findings.')
        else:
            print('Global deep scan import:', import_results(args.results, deep=args.deep))
        return 0
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f'GLOBAL DEEP SCAN FAILED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(cli())
