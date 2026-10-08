#!/usr/bin/env python3
"""Make a bounded, self-contained research assignment for a *manually used* LLM."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.llm_discovery_common import ROOT, PACKAGE_FORMAT, FORMAT, clean, doi, norm, write_json
from scripts.scan_radar import BOOTSTRAP_LOOKBACK_MONTHS, EXTENDED_TOP_QUALITY_LOOKBACK_MONTHS
from scripts.prepare_deep_scan_package import INSTRUCTIONS as SHARED_DEEP_SCAN_CRITERIA

PRIORITY_JOURNALS = [
    'Nature', 'Science', 'Nature Communications', 'Proceedings of the National Academy of Sciences',
    'Research Policy', 'Technovation', 'Science and Public Policy', 'Scientometrics',
    'Industrial and Corporate Change', 'Journal of Economic Geography',
    'Structural Change and Economic Dynamics', 'Research Evaluation',
    'Technological Forecasting and Social Change', 'Journal of Technology Transfer',
    'Science Advances', 'Minerva', 'Journal of Informetrics', 'Research in Higher Education',
]
PRIORITY_INSTITUTIONS = [
    ('European Commission, DG Research & Innovation', 'https://research-and-innovation.ec.europa.eu/'),
    ('Joint Research Centre', 'https://joint-research-centre.ec.europa.eu/'),
    ('OECD Science, Technology and Innovation', 'https://www.oecd.org/en/topics/science-technology-and-innovation.html'),
    ('European Strategy Forum on Research Infrastructures (ESFRI)', 'https://www.esfri.eu/'),
    ('European Parliament / STOA', 'https://www.europarl.europa.eu/stoa/en/home/highlights'),
    ('ESPAS', 'https://espas.eu/'),
    ('EU Publications Office', 'https://op.europa.eu/'),
    ('European Patent Office', 'https://www.epo.org/'),
    ('European University Association', 'https://www.eua.eu/'),
    ('Science Europe', 'https://scienceeurope.org/'),
    ('European Research Council', 'https://erc.europa.eu/'),
    ('Eurostat R&D and innovation evidence', 'https://ec.europa.eu/eurostat/'),
]
THEMES = [
    'R&D investment, financing and innovation performance',
    'research careers, mobility and collaboration networks',
    'research infrastructure, open science and knowledge transfer',
    'semiconductors, AI, quantum, biotechnology and European research capacity',
    'research evaluation, governance and policy effectiveness',
    'Europe-wide patterns and comparisons in patents, firms and innovation',
]

START = '''# START HERE — Manual European/EU Research & Innovation discovery

You are a *discovery researcher*, NOT the Radar's authoritative Deep Scan verifier.
Work only on the bounded, ordered tasks in `tasks.json` (max 20, not an unlimited search).
Strand A is the priority: primary scientific articles **and** authoritative analytical institutional reports.
Search actual recent publications through journal contents, publisher/DOI landing pages,
Crossref, official report collections and attached full text where legitimately available.
A journal's reputation alone never admits a work; a prestigious paper on general science
with an incidental European author, grant, or comparator is NOT evidence about European R&I.
A study published anywhere can qualify if its *research findings* substantively concern EU/European R&I.

Use `admission_policy.txt` for the existing authoritative scope/quality/exclusion contract.
`existing_radar_records.json` provides duplicate identities for ALL current Main Radar strands.
`candidate_leads.json` are unresolved scanner leads, NEVER verified publications.
`coverage_gaps.json` explains the source undercoverage and task prioritisation.

## Required return artifact
Return a single UTF-8 JSON FILE named `llm_research_results.json`, using precisely
`results_TEMPLATE.json` as your schema, with up to 24 findings. Upload that file yourself
through GitHub's browser into `llm_discovery_inbox/` (no Python/code edits).
Set `package_id` exactly as supplied. Do NOT wrap JSON in Markdown fences.
If nothing qualifies, return an empty `findings` list: no padding.

For each publication provide exact title, real authors, journal/institution, DOI when
present, exact YYYY-MM-DD *first* publication date (NOT website-update/crawl date),
official HTTPS URL, type `journal_article` or `institutional_report`, a substantial
source-backed abstract/evidence and principal research results, European R&I relevance,
and at least TWO non-trivial verbatim `evidence_quotes` (>= 10 words each) from the
publisher's own abstract/full text or the institution's official publication.
Those quotes must actually appear in verifiable source material.
Give `source_references` with URLs and explanation of what is directly verified;
`verification_limitations` must say precisely what is not independently established.
Never infer a date from search snippets or from the name of a file. Never fabricate
publication identities, abstracts, findings, quotations or European implications.

GitHub's importer will *independently retrieve/check* publisher/Crossref or official
institutional evidence and run the existing scanner's Strand-A admission gate.
If that first-party evidence cannot be verified, it will REJECT the candidate rather
than treating the LLM's claim as proof. GitHub will not use the scanner's search machinery
or call any LLM API. Once accepted, the existing Deep Scan V2 independently reviews it.

## Deliberate research allocation
Prioritise (1) the least-covered core scientific journals; (2) high-value authoritative
research publications; (3) genuinely relevant unresolved scanner leads. For each task
look for up to two genuinely important qualifying publications, but return NO MORE than
24 findings overall, ordered by task priority. Cover systems analysis,
research policy and technological research evidence, not general European news.
'''


def build(corpus, cfg, limit=18, today=None):
    today = today or dt.date.today()
    counts = Counter(norm(x.get('source')) for x in corpus.get('strand_a', []) if isinstance(x, dict))
    # The journal core is intentionally protected against count-only rotation:
    # otherwise already-successful Research Policy/Technovation disappear from
    # manual discovery just when users most want their newest real papers.
    journal_core = PRIORITY_JOURNALS[:11]
    all_journals = list(dict.fromkeys(PRIORITY_JOURNALS + cfg.get('priority_policy_journal_watchlist', []) + cfg.get('top_journal_watchlist', [])))
    journal_names = journal_core + sorted((j for j in all_journals if j not in journal_core), key=lambda x: (counts[norm(x)], x))
    config_inst = [(clean(row.get('name')), f"https://{clean(row.get('domain'))}/") for row in cfg.get('institution_sources', []) if isinstance(row, dict) and row.get('domain')]
    inst_core = PRIORITY_INSTITUTIONS[:7]
    insts = inst_core + sorted((i for i in list(dict.fromkeys(PRIORITY_INSTITUTIONS + config_inst)) if i not in inst_core), key=lambda x: (counts[norm(x[0])], x[0]))
    journal_count = min(11, max(3, round(limit * .61)))
    inst_count = min(6, max(2, round(limit * .33)))
    while journal_count + inst_count > limit:
        if journal_count > 3:
            journal_count -= 1
        else:
            inst_count -= 1
    tasks = []
    for i, name in enumerate(journal_names[:journal_count]):
        tasks.append({'id': f'J{i+1:02}', 'priority': 1 if i < 6 else 2,
                      'type': 'scientific_journal', 'target': name,
                      'existing_strand_a_count': counts[norm(name)],
                      'focus': THEMES[i % len(THEMES)],
                      'instructions': 'Inspect recent actual research papers, verify source and DOI; source prestige alone is not enough.'})
    for i, (name, url) in enumerate(insts[:inst_count]):
        tasks.append({'id': f'I{i+1:02}', 'priority': 1 if i < 3 else 2,
                      'type': 'institutional_research', 'target': name, 'starting_url': url,
                      'existing_strand_a_count': counts[norm(name)],
                      'focus': THEMES[(i+2) % len(THEMES)],
                      'instructions': 'Find DATED completed studies/reports and original evidence, not press releases, portals, calls or overview pages.'})
    deferred = corpus.get('scan_state', {}).get('deferred_metadata_queue', [])
    existing = {doi(row.get('_doi') or row.get('doi') or row.get('link')) for k in ('strand_a','strand_b','strand_c') for row in corpus.get(k,[]) if isinstance(row, dict)}
    leads = []
    for row in deferred if isinstance(deferred, list) else []:
        if not isinstance(row, dict):
            continue
        raw = row.get('raw') if isinstance(row.get('raw'), dict) else {}
        d = doi(raw.get('DOI') or raw.get('doi'))
        t = raw.get('title') or raw.get('display_name') or ''
        t = t[0] if isinstance(t, list) and t else t
        if not d or d in existing or not clean(t) or norm(t).startswith(('book review', 'editorial', 'corrigendum', 'retraction')):
            continue
        relevant = sum(word in norm(t) for word in ('research', 'innovation', 'science', 'europe', 'eu ', 'university', 'collaboration', 'semiconductor', 'patent', 'technology policy', 'scientific'))
        if relevant < 2:
            continue
        leads.append({'title_unverified': clean(t), 'doi_unverified': d, 'provider': row.get('provider'),
                      'scanner_state': 'deferred_metadata', 'reason': 'incomplete_metadata', 'research_task': 'Verify actual work; do NOT assume it qualifies.'})
        if len(leads) >= 12:
            break
    remaining = min(3, max(0, limit-len(tasks)))
    for i in range(min(remaining, len(leads))):
        tasks.append({'id': f'R{i+1:02}', 'priority': 2, 'type': 'unresolved_scanner_lead', **leads[i],
                      'instructions': 'Resolve publication identity, exact publication date and real substantive source, then independently test Strand A.'})
    tasks = tasks[:limit]
    gaps = {
        'scanner_diagnostics': {'scan_health': corpus.get('scan_health'), 'deferred_metadata_queue_size': len(deferred),
                                'last_scan_at': corpus.get('scan_state', {}).get('last_completed_at')},
        'priority': 'Strand A substantive European/EU R&I first; journals and institutions in parallel',
        'interpretation_note': 'Zero or low existing counts indicate under-coverage, NOT verified missed publications or HTTP failure.',
        'underrepresented_journals': [{'journal': j, 'strand_a_count': counts[norm(j)]} for j in journal_names[:25]],
        'underrepresented_institutions': [{'institution': n, 'strand_a_count': counts[norm(n)]} for n, _ in insts[:20]],
        'publication_window': {'normal_months': BOOTSTRAP_LOOKBACK_MONTHS, 'exceptional_tier_months': EXTENDED_TOP_QUALITY_LOOKBACK_MONTHS},
    }
    return tasks, leads, gaps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', type=Path, default=ROOT / 'radar.json')
    ap.add_argument('--config', type=Path, default=ROOT / 'radar_config.json')
    ap.add_argument('--output', type=Path, default=ROOT / 'llm_discovery_package.zip')
    ap.add_argument('--max-tasks', type=int, default=18)
    args = ap.parse_args()
    if not 5 <= args.max_tasks <= 20:
        ap.error('--max-tasks must be between 5 and 20')
    corpus = json.loads(args.corpus.read_text(encoding='utf-8'))
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    tasks, leads, gaps = build(corpus, cfg, args.max_tasks)
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    package_id = 'llm-a-' + now
    template = {'format': FORMAT, 'package_id': package_id, 'findings': [{
        'title': 'REPLACE — exact publication title', 'authors': ['Actual author/organisation'],
        'source': 'Actual journal or institution', 'publication_type': 'journal_article',
        'doi': '10.xxxx/example (or empty for an official report)',
        'official_url': 'https://official-publisher-or-institution.example/report',
        'metadata_url': '', 'publication_date': 'YYYY-MM-DD',
        'abstract_or_evidence': 'Actual substantive research evidence (not a made-up abstract)',
        'principal_findings': ['Source-grounded result, with caveats'],
        'eu_ri_relevance': 'European/EU research-and-innovation mechanism evidenced in original work',
        'evidence_quotes': ['Verbatim quote (at least 10 words) visible in official abstract or body',
                            'Second different substantive verbatim quotation from official source'],
        'source_references': [{'url': 'https://actual-source.example', 'supports': 'specific verified identity/date/findings'}],
        'verification_limitations': 'What could not be accessed or established',
        'discovery_task_id': 'J01', 'suspected_scanner_miss': 'Unverified hypothesis or empty',
    }]}
    records = []
    for k in ('strand_a', 'strand_b', 'strand_c', 'frontier_evidence', 'ab_archive', 'signal_archive'):
        for r in corpus.get(k, []) if isinstance(corpus.get(k), list) else []:
            if isinstance(r, dict):
                records.append({'strand': k, 'title': clean(r.get('title') or r.get('headline')), 'doi': doi(r.get('_doi') or r.get('doi') or r.get('link')),
                                'link': clean(r.get('link') or r.get('url')), 'date': clean(r.get('date'))})
    files = {
        'START_HERE.md': START,
        'tasks.json': json.dumps({'format': PACKAGE_FORMAT, 'package_id': package_id, 'tasks': tasks}, ensure_ascii=False, indent=2) + '\n',
        'coverage_gaps.json': json.dumps(gaps, ensure_ascii=False, indent=2) + '\n',
        'candidate_leads.json': json.dumps(leads, ensure_ascii=False, indent=2) + '\n',
        'existing_radar_records.json': json.dumps(records, ensure_ascii=False, indent=2) + '\n',
        'results_TEMPLATE.json': json.dumps(template, ensure_ascii=False, indent=2) + '\n',
        'admission_policy.txt': SHARED_DEEP_SCAN_CRITERIA + '\n\nImplementation reuses scripts.scan_radar.gate_scope(...), final_ab_candidate_worthiness(...), quality_from_crossref(...), bootstrap_floor(...), extended_top_quality_floor(...).\n',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    print(f'Prepared manual LLM research ZIP: {args.output}; package_id={package_id}; tasks={len(tasks)}; existing_records={len(records)}')


if __name__ == '__main__':
    main()
