#!/usr/bin/env python3
"""Evidence-verified manual LLM discoveries -> live Main Radar Strand A.

NO model/API calls. No scanner searching. Crossref depositor metadata and publisher /
official primary source retrieval serve as independent evidence, not LLM assertions.
Deep Scan verification is NOT completed by this importer.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import re
import sys
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from scripts import scan_radar as radar
from scripts.llm_discovery_common import (
    ROOT, FORMAT, MAX_FINDINGS, clean, crossref_date, doi, domain_matches, duplicate_of,
    exact_date, host, identities, infer_miss_reason, metadata_html, norm,
    passage_supported, safe_http_url, same_title, text_of_html, write_json,
)

PROFILE = 'llm-assisted-discovery-pending-deep-scan-v1'
MAX_RESPONSE = 7 * 1024 * 1024
CROSSREF = 'https://api.crossref.org/works/'
OPENALEX = 'https://api.openalex.org/works'
TRUSTED_PUBLISHER_HOSTS = (
    'nature.com', 'science.org', 'pnas.org', 'sciencedirect.com', 'elsevier.com',
    'link.springer.com', 'springer.com', 'academic.oup.com', 'oup.com',
    'tandfonline.com', 'onlinelibrary.wiley.com', 'wiley.com',
    'journals.sagepub.com', 'sagepub.com', 'cambridge.org', 'cell.com',
    'plos.org', 'frontiersin.org', 'iopscience.iop.org', 'iop.org',
)
EXTRA_OFFICIAL_HOSTS = (
    'esfri.eu', 'espas.eu', 'eua.eu', 'scienceeurope.org', 'epc.eu', 'erc.europa.eu',
    'europarl.europa.eu', 'oecd.org', 'oecd-ilibrary.org', 'epo.org', 'cern.ch',
    'ec.europa.eu', 'europa.eu', 'eui.eu', 'eurofound.europa.eu',
)


class Reject(Exception):
    pass


def require(ok, msg):
    if not ok:
        raise Reject(msg)


def get_bytes(url, session, *, require_host=''):
    require(safe_http_url(url), 'unsafe or non-HTTPS source URL')
    if require_host:
        require(domain_matches(host(url), require_host), 'source domain differs from verified publisher')
    try:
        r = session.get(url, timeout=(6, 15), allow_redirects=False,
                        headers={'User-Agent': 'Europe-RI-Radar-evidence-audit/1.0',
                                 'Accept': 'text/html,application/pdf,application/json'})
        require(r.status_code == 200, f'primary evidence unavailable: HTTP {r.status_code}')
        payload = r.content
        require(0 < len(payload) <= MAX_RESPONSE, 'empty/oversized source response')
        return payload, r.headers.get('content-type', '').lower()
    except requests.RequestException as exc:
        raise Reject(f'primary source could not be retrieved: {type(exc).__name__}') from exc


def source_page(url, session, *, allowed_host=''):
    payload, ctype = get_bytes(url, session, require_host=allowed_host)
    if 'pdf' in ctype or payload.startswith(b'%PDF-'):
        try:
            reader = PdfReader(io.BytesIO(payload))
            text = clean(' '.join((p.extract_text() or '') for p in reader.pages[:18]))[:110000]
        except Exception as exc:
            raise Reject('official PDF could not be independently text-verified') from exc
        require(len(text.split()) >= 100, 'PDF text too short for substantive verification')
        return {'titles': [], 'dates': [], 'abstracts': [], 'text': text, 'pdf': True, 'url': url,
                'sha256': hashlib.sha256(payload).hexdigest()}
    require('html' in ctype or b'<html' in payload[:1200].lower(), 'unsupported primary source format')
    html = payload.decode('utf-8', errors='replace')
    titles, dates, abstracts = metadata_html(html)
    soup = BeautifulSoup(html, 'html.parser')
    citation_doi = ''
    for tag in soup.find_all('meta'):
        if clean(tag.get('name') or tag.get('property')).lower() in ('citation_doi', 'dc.identifier', 'dc.identifier.doi'):
            citation_doi = doi(tag.get('content')) or citation_doi
    return {'titles': titles, 'dates': dates, 'abstracts': abstracts, 'citation_doi': citation_doi,
            'text': text_of_html(html), 'pdf': False, 'url': url,
            'sha256': hashlib.sha256(payload).hexdigest()}


def trust_institution(url, source):
    domain = host(url)
    if not domain:
        return None
    # Identical source quality whitelist as production scanner, extended only for
    # authoritative research bodies explicitly named in the manual workflow.
    configured = radar.institution_source_for_domain(domain)
    if configured:
        return configured
    if any(domain_matches(domain, root) for root in EXTRA_OFFICIAL_HOSTS):
        return (source, 1 if 'europa.eu' in domain or domain_matches(domain, 'oecd.org') else 2)
    return None


def crossref_work(identifier, session):
    url = CROSSREF + requests.utils.quote(identifier, safe='')
    payload, ct = get_bytes(url, session)
    try:
        response = json.loads(payload)
        work = response['message']
        require(isinstance(work, dict) and doi(work.get('DOI')) == identifier, 'Crossref DOI identity mismatch')
        return work
    except (ValueError, KeyError, TypeError) as exc:
        raise Reject('Crossref metadata not verifiable') from exc


def openalex_indexed_abstract(identifier, article_title, session):
    """Direct DOI lookup, NOT scanner search; use only DOI-matched indexed text.

    This independently checkable abstract can rescue a publisher-blocked journal
    landing page when Crossref carries bibliography but no deposited abstract.
    No LLM claims are trusted in lieu of this indexed text.
    """
    from urllib.parse import urlencode
    url = OPENALEX + '?' + urlencode({'filter': 'doi:https://doi.org/' + identifier, 'per-page': '1'})
    try:
        payload, _ = get_bytes(url, session)
        results = json.loads(payload).get('results', [])
        row = results[0] if results else None
        if not isinstance(row, dict) or doi(row.get('doi')) != identifier:
            return '', ''
        if not same_title(article_title, row.get('title'), .90):
            return '', ''
        index = row.get('abstract_inverted_index')
        if not isinstance(index, dict):
            return '', ''
        words = []
        for word, positions in index.items():
            if isinstance(positions, list):
                for pos in positions:
                    if isinstance(pos, int) and 0 <= pos < 5000:
                        words.append((pos, word))
        words.sort()
        abstract = clean(' '.join(word for _, word in words))
        if len(abstract.split()) < 50:
            return '', ''
        return abstract, url
    except (Reject, ValueError, TypeError, KeyError, IndexError):
        return '', ''


def html_fragment_to_text(markup):
    return clean(BeautifulSoup(markup or '', 'html.parser').get_text(' ', strip=True))


def verify_journal(item, session):
    identifier = doi(item.get('doi'))
    require(bool(identifier), 'journal article must provide a valid DOI')
    meta = crossref_work(identifier, session)
    success, tier, source_rank, journal, tier_label, typ = radar.quality_from_crossref(meta)
    require(success and typ == 'peer-reviewed article', 'journal/publisher fails existing scanner source-quality gate')
    meta_title = clean((meta.get('title') or [''])[0])
    require(same_title(item['title'], meta_title, .90), 'title does not match Crossref depositor record')
    date, date_field = crossref_date(meta)
    require(date is not None, 'Crossref publication day/month/year not independently established')
    require(date.isoformat() == item['publication_date'], 'claimed date disagrees with verified Crossref publication date')
    authors = [clean(f"{a.get('given', '')} {a.get('family', '')}") for a in meta.get('author', []) if isinstance(a, dict)]
    authors = [a for a in authors if a]
    require(authors or meta.get('institution'), 'no Crossref-deposited authors or institution')
    if not authors:
        authors = [clean(a.get('name')) for a in meta.get('institution', []) if isinstance(a, dict)]
    crossref_abstract = html_fragment_to_text(meta.get('abstract'))
    checked = [{'url': CROSSREF + requests.utils.quote(identifier, safe=''),
                'kind': 'crossref_depositor_metadata', 'date_field': date_field}]
    texts = [crossref_abstract] if len(crossref_abstract.split()) >= 40 else []
    landing = clean(item.get('official_url'))
    require(safe_http_url(landing), 'missing or unsafe official URL')
    crossref_link = clean(meta.get('URL'))
    # The DOI itself is a valid official identifier URL. Any DIFFERENT publisher
    # page must be tied to the DOI record's deposited publication link.
    doi_url_ok = domain_matches(host(landing), 'doi.org') and doi(landing) == identifier
    publisher_host = host(crossref_link)
    if not publisher_host or domain_matches(publisher_host, 'doi.org'):
        for record in meta.get('link', []):
            candidate_host = host(clean(record.get('URL'))) if isinstance(record, dict) else ''
            if candidate_host and not domain_matches(candidate_host, 'doi.org'):
                publisher_host = candidate_host
                break
    if not doi_url_ok:
        # Crossref often deposits its generic doi.org resolver instead of the
        # publisher URL. Native article pages may still be verified if on a
        # trusted publisher host and carrying the exact citation DOI.
        host_deposited = bool(publisher_host and not domain_matches(publisher_host, 'doi.org')
                              and domain_matches(host(landing), publisher_host))
        host_trusted = any(domain_matches(host(landing), h) for h in TRUSTED_PUBLISHER_HOSTS)
        require(host_deposited or host_trusted,
                'official URL not on verified/deposited scholarly publisher host')
        try:
            page = source_page(landing, session, allowed_host=publisher_host if host_deposited else host(landing))
            require(any(same_title(meta_title, t, .85) for t in page['titles']) or
                    norm(meta_title) in norm(page['text'][:3500]),
                    'publisher page does not identify the submitted publication')
            if not host_deposited:
                require(page.get('citation_doi') == identifier or identifier in page['text'][:9000].lower(),
                        'non-deposited publisher page does not independently show the exact DOI')
            checked.append({'url': landing, 'kind': 'verified_publisher_page', 'sha256': page['sha256']})
            texts.extend(page['abstracts'])
            texts.append(page['text'])
        except Reject as exc:
            checked.append({'url': landing, 'kind': 'unavailable_publisher_page', 'reason': str(exc)})
            if host_trusted and not host_deposited:
                raise Reject('non-deposited publisher URL could not be verified to the article DOI: ' + str(exc))
            # Genuine Crossref abstract is still primary depositor-supplied evidence.
    if not any(len(t.split()) >= 40 for t in texts):
        # A bounded, direct DOI lookup of indexed abstract text can supply
        # independently checkable substance when the publisher is inaccessible.
        # Crossref continues to establish title, date and publisher quality.
        indexed, indexed_url = openalex_indexed_abstract(identifier, meta_title, session)
        if indexed:
            texts.append(indexed)
            checked.append({'url': indexed_url, 'kind': 'independent_doi_matched_abstract_index'})
    require(any(len(t.split()) >= 40 for t in texts),
            'no independently retrievable substantive publisher, depositor or DOI-matched indexed abstract')
    return {'title': meta_title, 'authors': ', '.join(authors[:12]), 'source': journal,
            'date': date, 'link': landing, 'doi': identifier, 'source_tier': tier_label,
            'source_rank': source_rank, 'kind': 'scholarly', 'type': typ,
            'texts': texts, 'checked': checked}


def verify_institution(item, session):
    link = clean(item.get('official_url'))
    trust = trust_institution(link, clean(item.get('source')))
    require(bool(trust), 'institutional URL is not in trusted official-source registry')
    source_name, tier = trust
    main = source_page(link, session, allowed_host=host(link))
    meta_url = clean(item.get('metadata_url'))
    landing = None
    if meta_url and meta_url != link:
        require(bool(trust_institution(meta_url, clean(item.get('source')))), 'metadata URL is not a trusted institutional source')
        landing = source_page(meta_url, session, allowed_host=host(meta_url))
    page = landing or main
    require(any(same_title(item['title'], t, .86) for t in page['titles']) or
            (main['pdf'] and norm(item['title']) in norm(main['text'][:4500])) or
            (not main['pdf'] and norm(item['title']) in norm(main['text'][:1400])),
            'official source does not independently establish exact publication identity')
    date_pairs = [(name, exact_date(value)) for name, value in page['dates']]
    date_pairs = [(name, date) for name, date in date_pairs if date is not None]
    require(date_pairs, 'original publication date not verified on official source (no update/crawl substitute)')
    require(any(d.isoformat() == item['publication_date'] for _, d in date_pairs),
            'submitted date differs from official source published date')
    require(len(main['text'].split()) >= 100 or any(len(a.split()) >= 60 for a in main['abstracts']),
            'official report text lacks sufficient substantive evidence')
    checked = [{'url': link, 'kind': 'official_institution_publication', 'sha256': main['sha256'],
                'date_field': next(n for n,d in date_pairs if d.isoformat() == item['publication_date'])}]
    if landing:
        checked.append({'url': meta_url, 'kind': 'official_institution_metadata', 'sha256': landing['sha256']})
    # Never store names asserted by the LLM as verified authors: retain only
    # author names visibly present in the official work; otherwise use its
    # verified institutional issuing body as the credited organisation.
    official_text = norm(main['text'] + ' ' + (landing['text'] if landing else ''))
    verified_authors = [clean(name) for name in item['authors']
                        if len(clean(name).split()) >= 2 and norm(name) in official_text]
    author_credit = ', '.join(verified_authors[:12]) or source_name
    return {'title': clean(item['title']), 'authors': author_credit,
            'source': source_name, 'date': exact_date(item['publication_date']), 'link': link,
            'doi': doi(item.get('doi')), 'source_tier': f'Tier {tier}', 'source_rank': float(tier),
            'kind': 'institutional', 'type': 'institutional report',
            'texts': main['abstracts'] + [main['text']], 'checked': checked}


def verify_candidate(item, session, today=None):
    today = today or dt.date.today()
    require(isinstance(item, dict), 'candidate must be a JSON object')
    required = ('title', 'authors', 'source', 'official_url', 'publication_date',
                'abstract_or_evidence', 'principal_findings', 'eu_ri_relevance',
                'evidence_quotes', 'source_references', 'verification_limitations', 'discovery_task_id')
    for field in required:
        require(field in item, f'missing {field}')
    require(isinstance(item['title'], str) and len(clean(item['title'])) >= 16, 'missing exact title')
    require(isinstance(item['authors'], list) and bool(item['authors']), 'authors must be a nonempty list')
    require(all(isinstance(a, str) and a.strip() for a in item['authors']), 'invalid author identities')
    require(isinstance(item['principal_findings'], list) and bool(item['principal_findings']), 'missing research findings')
    require(all(isinstance(x, str) and clean(x) for x in item['principal_findings']), 'invalid finding text')
    require(isinstance(item['source'], str) and len(clean(item['source'])) >= 3, 'invalid journal or institution name')
    require(isinstance(item['abstract_or_evidence'], str) and len(clean(item['abstract_or_evidence'])) >= 40, 'missing supplied research evidence')
    require(isinstance(item['eu_ri_relevance'], str) and len(clean(item['eu_ri_relevance'])) >= 30, 'missing EU R&I relevance explanation')
    require(isinstance(item['evidence_quotes'], list) and len(item['evidence_quotes']) >= 2, 'two direct substantive evidence quotes required')
    require(all(isinstance(q, str) and len(q.split()) >= 10 for q in item['evidence_quotes']), 'evidence quote too short')
    require(isinstance(item['source_references'], list) and item['source_references'], 'missing source references')
    require(all(isinstance(x, dict) and safe_http_url(clean(x.get('url'))) for x in item['source_references']), 'invalid source reference')
    require(any(clean(x['url']) == clean(item['official_url']) or
                (doi(item.get('doi')) and doi(x['url']) == doi(item.get('doi'))) for x in item['source_references']),
            'source references do not name the original official publication or DOI')
    require(re.fullmatch(r'(?:J|I|R)\d{2}', clean(item['discovery_task_id'])) is not None, 'invalid research task identifier')
    date = exact_date(item['publication_date'])
    require(date is not None and date.isoformat() == item['publication_date'], 'publication date must be real YYYY-MM-DD')
    require(date <= today, 'future publication dates not permitted')
    pubtype = clean(item.get('publication_type'))
    require(pubtype in {'journal_article', 'institutional_report'}, 'only Strand-A research publication types supported')
    verified = verify_journal(item, session) if pubtype == 'journal_article' else verify_institution(item, session)
    text = clean(' '.join(verified['texts']))
    matches = []
    for quotation in item['evidence_quotes'][:12]:
        if passage_supported(quotation, text):
            matches.append(clean(quotation))
    require(len(matches) >= 2 and len(set(norm(q) for q in matches)) >= 2,
            'fewer than two independently retrieved, distinct substantive source passages matched')
    # LLM-provided conclusions, relevance statements and abstract are NOT passed to
    # the substantive gate. Only material independently fetched from the source is.
    primary_abstract = clean(verified['texts'][0])[:14000]
    primary_body = clean(' '.join(verified['texts'][1:]))[:35000]
    require(len(primary_abstract.split()) + len(primary_body.split()) >= 80,
            'retrieved publication lacks substantive research evidence')
    candidate = {
        'title': verified['title'], 'source': verified['source'], 'link': verified['link'],
        'date': date.isoformat(), 'source_tier': verified['source_tier'], 'type': verified['type'],
        'summary': primary_abstract[:5000] or primary_body[:5000],
    }
    require(radar.final_ab_candidate_worthiness(candidate), 'failed existing scanner publication worthiness gate')
    # Shared live scanner gate, including EU focus, centrality, document exclusions.
    gate = radar.gate_scope(verified['title'], primary_abstract, primary_body,
                            radar._saved_tier(candidate), source_kind=verified['kind'])
    require(gate.get('a_pass'), f'existing Strand A substantive admission failed: {gate.get("aboutness_reason") or gate.get("centrality_reason") or "no evidence-backed EU R&I route"}')
    # Same exact two-tier new-discovery recency + quality exception as scanner.
    if date < radar.bootstrap_floor(today):
        require(date >= radar.extended_top_quality_floor(today) and
                radar.extended_high_quality_merit(candidate),
                'outside existing new-discovery publication-date window')
    # Build standard record from scanner's shared builder rather than a second schema.
    row = radar.build_item(title=verified['title'], authors=verified['authors'],
                           source=verified['source'], date=date, link=verified['link'],
                           item_type=verified['type'], strand='A', evidence=gate,
                           source_rank=verified['source_rank'], tier_label=verified['source_tier'],
                           text=primary_abstract or primary_body[:5000], doi=verified['doi'], preprint=False)
    row = radar.public_item(row, new_this_scan=False, first_seen=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'))
    row['doi'] = verified['doi']
    row['discovery_method'] = 'LLM-assisted discovery — Pending Deep Scan'
    row['deep_scan_status'] = 'pending'
    row['llm_discovery'] = {
        'profile': PROFILE, 'task_id': clean(item['discovery_task_id']),
        'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'primary_evidence': verified['checked'], 'source_supported_quotes': matches,
        'verified_date': date.isoformat(), 'provenance': 'manually initiated LLM research; source independently checked by GitHub importer',
        'llm_claims_not_authoritative': True,
        'llm_reported_limitations': clean(item.get('verification_limitations'))[:1400],
        'reported_scanner_miss': clean(item.get('suspected_scanner_miss'))[:500],
    }
    return row


def input_files(inbox):
    if not inbox.exists():
        return []
    return sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() == '.json' and not p.name.startswith('.'))


def process_file(path, *, corpus, pool, session, report_dir, today=None):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    report_path = report_dir / f'{digest[:24]}.json'
    if report_path.exists():
        return {'already_processed': True, 'file': path.name, 'report': str(report_path)}
    require(len(raw) <= 1024 * 1024, 'input file exceeds 1 MB')
    try:
        payload = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise Reject('input is not valid UTF-8 JSON') from exc
    require(isinstance(payload, dict) and payload.get('format') == FORMAT,
            f'wrong JSON format: expected {FORMAT}')
    require(re.fullmatch(r'llm-a-\d{8}T\d{6}Z', clean(payload.get('package_id'))) is not None,
            'invalid or missing package_id')
    findings = payload.get('findings')
    require(isinstance(findings, list) and len(findings) <= MAX_FINDINGS,
            f'findings must be a list with at most {MAX_FINDINGS} entries')
    known = identities(corpus, pool)
    deferred = corpus.get('scan_state', {}).get('deferred_metadata_queue', [])
    results = []
    admitted = []
    for index, finding in enumerate(findings):
        title = clean(finding.get('title')) if isinstance(finding, dict) else ''
        result = {'index': index, 'title': title[:400]}
        try:
            require(isinstance(finding, dict), 'finding must be an object')
            dup = duplicate_of(finding, known)
            if dup:
                result.update(status='duplicate', reason=f'already present in {dup[0]}: {dup[1][:150]}')
            else:
                candidate = verify_candidate(finding, session, today=today)
                dup = duplicate_of(candidate, known)
                if dup:
                    result.update(status='duplicate', reason=f'official verified identity already in {dup[0]}: {dup[1][:150]}')
                else:
                    reason, key = infer_miss_reason(candidate, deferred)
                    candidate['llm_discovery']['miss_reason'] = reason
                    candidate['llm_discovery']['scanner_deferred_key'] = key
                    candidate['llm_discovery']['package_id'] = payload['package_id']
                    candidate['llm_discovery']['submission_sha256'] = digest
                    candidate['llm_discovery']['source_references_as_submitted'] = finding['source_references'][:12]
                    candidate['llm_discovery']['llm_reported_findings_not_verified'] = [clean(s)[:350] for s in finding['principal_findings'][:4]]
                    candidate['llm_discovery']['llm_reported_abstract_not_verified'] = clean(finding['abstract_or_evidence'])[:1200]
                    corpus['strand_a'].append(candidate)
                    known.append((candidate, 'strand_a'))
                    admitted.append(candidate)
                    result.update(status='admitted_pending_deep_scan', date=candidate['date'],
                                  link=candidate['link'], doi=candidate['doi'],
                                  source_evidence_count=len(candidate['llm_discovery']['primary_evidence']))
        except (Reject, KeyError, TypeError, ValueError) as exc:
            result.update(status='rejected_insufficient_verification', reason=str(exc)[:500])
        results.append(result)
    report = {'profile': PROFILE, 'file': path.name, 'sha256': digest, 'package_id': payload['package_id'],
              'processed_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
              'admitted': len(admitted), 'duplicates': sum(x['status'] == 'duplicate' for x in results),
              'rejected': sum(x['status'] == 'rejected_insufficient_verification' for x in results),
              'results': results, 'policy': 'independent source proof + unchanged scanner substantive gate; Deep Scan pending'}
    write_json(report_path, report)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', type=Path, default=ROOT / 'radar.json')
    ap.add_argument('--pool', type=Path, default=ROOT / 'deep_a_candidates.json')
    ap.add_argument('--inbox', type=Path, default=ROOT / 'llm_discovery_inbox')
    ap.add_argument('--reports', type=Path, default=ROOT / 'llm_discovery_reports')
    args = ap.parse_args()
    if not args.corpus.exists():
        ap.error('radar corpus does not exist')
    corpus = json.loads(args.corpus.read_text(encoding='utf-8'))
    require(isinstance(corpus.get('strand_a'), list), 'Main Radar strand_a missing')
    pool = json.loads(args.pool.read_text(encoding='utf-8')) if args.pool.exists() else {}
    if not isinstance(pool, dict):
        pool = {}
    historical_path = ROOT / 'historical' / 'historical.json'
    if historical_path.exists():
        pool['historical'] = json.loads(historical_path.read_text(encoding='utf-8')).get('items', [])
    rejected_archive_path = ROOT / 'deep_a_candidate_archive.json'
    if rejected_archive_path.exists():
        pool['rejected_history'] = json.loads(rejected_archive_path.read_text(encoding='utf-8')).get('records', [])
    changed = False
    summary = []
    with requests.Session() as session:
        for path in input_files(args.inbox):
            result = process_file(path, corpus=corpus, pool=pool, session=session, report_dir=args.reports)
            summary.append(result)
            if result.get('admitted'):
                changed = True
    if changed:
        # Avoid replacing historical or secondary databases; only add to live A.
        write_json(args.corpus, corpus)
    print(json.dumps({'files_checked': len(summary), 'admitted': sum(r.get('admitted',0) for r in summary),
                      'duplicate': sum(r.get('duplicates',0) for r in summary),
                      'rejected': sum(r.get('rejected',0) for r in summary),
                      'corpus_changed': changed, 'reports': [r.get('file') for r in summary]}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
