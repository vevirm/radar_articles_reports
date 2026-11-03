#!/usr/bin/env python3
"""Manual-only, separate Global R&I Blind Spots discovery.

Nothing in this module writes radar.json, admissions, or existing Excel outputs.
Candidate status is deliberately 'needs_review'; official state sources are labeled
as primary *claims* rather than independent verification.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import csv
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / 'Global R&I Blind Spots'
UA = 'GlobalBlindSpots/1.0 (responsible research discovery; no bulk scraping)'


def norm(text):
    return ' '.join(re.sub(r'\s+', ' ', html.unescape(str(text or ''))).split())


def strip_html(text):
    return norm(re.sub(r'<[^>]+>', ' ', str(text or '')))


def valid_domain(url, domain):
    if not isinstance(url, str) or not url.startswith('https://'):
        return False
    host = (urlsplit(url).hostname or '').lower()
    return host == domain or host.endswith('.' + domain)


def find_terms(text, terms):
    """Precise phrase tokens, avoiding false US in 'thus', AI in 'said'."""
    text = norm(text).lower()
    return [t for t in terms if (t.lower() in text if re.search(r'[\u4e00-\u9fff]', t) else re.search(r'(?<![\w])' + re.escape(t.lower()) + r'(?![\w])', text))]


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def item_text(item):
    return ' '.join(str(item.get(k) or '') for k in ('title', 'reader_what', 'reader_why', 'core_message', 'summary'))


def usable_title(item):
    t = norm(item.get('title'))
    return len(t) >= 18 and not t.lower().startswith('http')


def extract_radar_anchors(radar, config, max_per_theme=8):
    """Issues are anchored in *actual* main Radar findings, not a fixed country news feed."""
    source = []
    for strand in ('strand_a', 'strand_b', 'strand_c'):
        for item in radar.get(strand, []):
            if isinstance(item, dict) and usable_title(item):
                source.append((strand[-1].upper(), item))
    source.sort(key=lambda p: (str(p[1].get('date') or '')[:10], p[0] == 'A'), reverse=True)
    result = {}
    for theme, detail in config['themes'].items():
        anchors = []
        for strand, item in source:
            # Anchor to actual main-Radar issue statements, not incidental words
            # buried in a long bibliographic summary.
            anchor_text = ' '.join(str(item.get(k) or '') for k in ('title', 'reader_what', 'core_message'))
            matched = find_terms(anchor_text, detail['terms'])
            if not matched:
                continue
            anchors.append({'title': norm(item['title']), 'date': str(item.get('date') or '')[:10],
                            'strand': strand, 'url': item.get('link') or item.get('url') or '',
                            'matched_terms': matched[:4]})
            if len(anchors) == max_per_theme:
                break
        result[theme] = anchors
    return result


def existing_coverage(radar, config):
    result = {}
    for region, aliases in config['regions'].items():
        for theme, detail in config['themes'].items():
            count = 0
            for strand in ('strand_a', 'strand_b', 'strand_c'):
                for item in radar.get(strand, []):
                    if isinstance(item, dict) and find_terms(item_text(item), aliases) and find_terms(item_text(item), detail['terms']):
                        count += 1
            result[f'{region} | {theme}'] = count
    return result


def get_bytes(url, timeout=18, max_bytes=1_500_000):
    req = Request(url, headers={'User-Agent': UA, 'Accept': 'application/json, application/xml, text/html, */*'})
    with urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f'HTTP {response.status}')
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RuntimeError('response too large')
    return data


def openalex_abstract(inverted):
    if not isinstance(inverted, dict):
        return ''
    words = []
    for word, positions in inverted.items():
        if not isinstance(positions, list):
            continue
        for i in positions:
            if isinstance(i, int) and 0 <= i < 800:
                words.append((i, word))
    return ' '.join(word for _, word in sorted(words))[:3600]


def source_quality(work, config):
    if work.get('type') not in ('article', 'review', 'book-chapter'):
        return None
    source = ((work.get('primary_location') or {}).get('source') or {})
    journal = norm(source.get('display_name'))
    if not journal:
        return None
    allowed = {x.casefold() for x in config['_journal_allowlist']}
    if journal.casefold() not in allowed:
        return None
    return {'source': journal, 'kind': 'trusted_scholarly_venue', 'confidence': 'candidate_not_peer_review_verified',
            'note': 'Journal appears on the main Radar trusted-venue list; article-level peer review and claims require checking.'}


def candidate_from_openalex(work, region, theme, config, anchors, query):
    quality = source_quality(work, config)
    if not quality:
        return None
    title = norm(work.get('display_name'))
    abstract = openalex_abstract(work.get('abstract_inverted_index'))
    text = f'{title} {abstract}'
    terms = find_terms(text, config['themes'][theme]['terms'])
    if not terms or not find_terms(text, config['regions'][region]):
        return None
    # Avoid a primarily EU-centred record that merely mentions a foreign country
    # somewhere in the abstract; comparative work naming both is still eligible.
    if find_terms(title, ['european union', 'european', 'europe', 'eu']) and not find_terms(title, config['regions'][region]):
        return None
    if len(title) < 22 or len(text) < 65:
        return None
    doi = str(work.get('doi') or '')
    url = doi if doi.startswith('https://doi.org/') else str(work.get('id') or '')
    if not (url.startswith('https://doi.org/') or valid_domain(url, 'openalex.org')):
        return None
    date = str(work.get('publication_date') or '')[:10]
    return {'title': title, 'date': date, 'region': region, 'theme': theme, 'url': url,
            'source': quality['source'], 'source_kind': quality['kind'], 'evidence_status': quality['confidence'],
            'evidence_note': quality['note'], 'abstract_or_context': abstract[:650],
            'issue_terms': terms[:5], 'query': query,
            'matched_main_radar_titles': [a['title'] for a in anchors[:3]],
            'review_status': 'needs_review', 'discovery_method': 'OpenAlex metadata'}


def discover_openalex(config, anchors, diagnostics, now, http_get=get_bytes):
    results = []
    date_min = (now - timedelta(days=config['max_days_old'])).date().isoformat()
    api_key = os.environ.get('OPENALEX_API_KEY', '').strip()
    for region in config['regions']:
        for theme, detail in config['themes'].items():
            if not anchors[theme]:
                diagnostics['skipped_no_main_radar_anchor'] += 1
                continue
            # Single theme-specific query/region, with the requested main Radar
            # terminology. Two rotations are used so smaller signals can surface.
            # Search topics are chosen from the *actual current Radar anchors*,
            # not only the static theme names. Fallback queries preserve recall.
            ranked_terms = Counter(t for a in anchors[theme] for t in a['matched_terms'])
            dynamic = [term for term, _ in ranked_terms.most_common(2)]
            query_phrases = [f'{term} research innovation' for term in dynamic]
            for fallback in detail['queries']:
                if len(query_phrases) >= 2:
                    break
                query_phrases.append(fallback)
            searches = [f'{region} {p}' for p in query_phrases]
            searches += config.get('native_searches', {}).get(region, {}).get(theme, [])
            for query in searches:
                params = {'search': query, 'filter': f'from_publication_date:{date_min}',
                          'per-page': min(50, int(config['max_results_per_search'])),
                          'select': 'id,doi,display_name,publication_date,primary_location,abstract_inverted_index,type',
                          'sort': 'publication_date:desc'}
                if api_key:
                    params['api_key'] = api_key
                url = 'https://api.openalex.org/works?' + urlencode(params)
                try:
                    response = json.loads(http_get(url, timeout=config['search_timeout_seconds']))
                    works = response.get('results', [])
                    diagnostics['openalex_requests_ok'] += 1
                    diagnostics['openalex_items_considered'] += len(works)
                    for work in works:
                        found = candidate_from_openalex(work, region, theme, config, anchors[theme], query)
                        if found:
                            results.append(found)
                        else:
                            diagnostics['scholarly_filtered_out'] += 1
                except (ValueError, RuntimeError, HTTPError, URLError, TimeoutError, OSError) as exc:
                    diagnostics['openalex_requests_failed'] += 1
                    diagnostics.setdefault('errors', []).append(f'OpenAlex {region}/{theme}: {type(exc).__name__}: {str(exc)[:120]}')
    return results


def xml_local_tag(tag):
    return tag.split('}', 1)[-1].lower()


def parse_feed(content):
    root = ET.fromstring(content)
    output = []
    for elem in root.iter():
        if xml_local_tag(elem.tag) not in ('entry', 'item'):
            continue
        fields = {'title': '', 'link': '', 'description': '', 'date': ''}
        for child in elem:
            kind = xml_local_tag(child.tag)
            val = norm(''.join(child.itertext()))
            if kind == 'title': fields['title'] = val
            elif kind == 'link': fields['link'] = (child.attrib.get('href') or val).strip()
            elif kind in ('description', 'summary', 'content'): fields['description'] = strip_html(val)
            elif kind in ('pubdate', 'published', 'updated', 'date'): fields['date'] = val
        output.append(fields)
    return output


def classify_feed_entry(entry, feed, config, anchors):
    if not valid_domain(entry.get('link'), feed['allowed_domain']):
        return []
    text = norm(entry.get('title', '') + ' ' + entry.get('description', ''))
    results = []
    regions = config['regions'] if feed['region_scope'] == 'global' else {feed['region_scope']: config['regions'][feed['region_scope']]}
    for region, aliases in regions.items():
        if feed['region_scope'] == 'global' and not find_terms(text, aliases):
            continue
        if feed['region_scope'] == 'global' and find_terms(entry.get('title', ''), ['european', 'europe', 'european union', 'eu']) and not find_terms(entry.get('title', ''), aliases):
            continue
        for theme, detail in config['themes'].items():
            matched = find_terms(text, detail['terms'])
            if not matched or not anchors[theme]:
                continue
            results.append({'title': norm(entry['title']), 'date': entry.get('date', '')[:32],
                'region': region, 'theme': theme, 'url': entry['link'], 'source': feed['name'],
                'source_kind': feed['kind'], 'evidence_status': 'official_claim_unverified' if feed['kind'] == 'official_primary' else 'editorial_report_unverified',
                'evidence_note': 'Agency announcement; independently corroborate outcomes.' if feed['kind'] == 'official_primary' else 'Editorial report; check linked article and underlying evidence.',
                'abstract_or_context': entry.get('description', '')[:650], 'issue_terms': matched[:5], 'query': 'curated RSS',
                'matched_main_radar_titles': [a['title'] for a in anchors[theme][:3]],
                'review_status': 'needs_review', 'discovery_method': 'allowlisted RSS'})
    return results


def recent_feed_date(text, now, max_days):
    if not text:
        return True  # Undated items retain explicit 'needs review' label.
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        try:
            parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed >= now - timedelta(days=max_days)


def discover_feeds(config, anchors, diagnostics, now, http_get=get_bytes):
    results = []
    for feed in config['feeds']:
        try:
            entries = parse_feed(http_get(feed['url'], timeout=config['search_timeout_seconds']))
            diagnostics['rss_requests_ok'] += 1
            for entry in entries[:120]:
                if not recent_feed_date(entry.get('date', ''), now, config['max_days_old']):
                    diagnostics['rss_entries_too_old'] += 1
                    continue
                results.extend(classify_feed_entry(entry, feed, config, anchors))
        except (ValueError, ET.ParseError, RuntimeError, HTTPError, URLError, TimeoutError, OSError) as exc:
            diagnostics['rss_requests_failed'] += 1
            diagnostics.setdefault('errors', []).append(f'RSS {feed["name"]}: {type(exc).__name__}: {str(exc)[:120]}')
    return results


class HubLinksParser(__import__('html.parser', fromlist=['HTMLParser']).HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.href, self.text_parts = [], None, []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.href = dict(attrs).get('href', '')
            self.text_parts = []
    def handle_data(self, data):
        if self.href is not None:
            self.text_parts.append(data)
    def handle_endtag(self, tag):
        if tag == 'a' and self.href is not None:
            self.links.append((norm(' '.join(self.text_parts)), self.href))
            self.href, self.text_parts = None, []


def discover_hubs(config, anchors, diagnostics, http_get=get_bytes):
    """Curated institutional link discovery, not unsupervised external crawling."""
    from urllib.parse import urljoin
    result = []
    for hub in config['trusted_hubs']:
        try:
            content = http_get(hub['url'], timeout=config['search_timeout_seconds'])
            parser = HubLinksParser()
            parser.feed(content.decode('utf-8', 'replace'))
            diagnostics['hub_requests_ok'] += 1
            seen = set()
            for title, href in parser.links:
                link = urljoin(hub['url'], href).split('#', 1)[0]
                if not valid_domain(link, hub['allowed_domain']) or not (22 <= len(title) <= 200) or link in seen:
                    continue
                seen.add(link)
                for theme, detail in config['themes'].items():
                    matched = find_terms(title, detail['terms'])
                    if not matched or not anchors[theme]:
                        continue
                    # Hub label is guaranteed geographical; linked article is NOT yet verified.
                    result.append({'title': title, 'date': '', 'region': hub['region'], 'theme': theme,
                        'url': link, 'source': hub['name'], 'source_kind': hub['kind'],
                        'evidence_status': 'official_claim_unverified' if hub['kind'] == 'official_primary' else 'institutional_claim_unverified',
                        'evidence_note': 'Hub headline only, article content and date have NOT been verified.',
                        'abstract_or_context': '', 'issue_terms': matched[:5], 'query': hub['url'],
                        'matched_main_radar_titles': [a['title'] for a in anchors[theme][:3]],
                        'review_status': 'needs_article_review', 'discovery_method': 'trusted institutional hub'})
                if len(seen) >= config['max_source_entries_per_hub']:
                    break
        except (ValueError, RuntimeError, HTTPError, URLError, TimeoutError, OSError) as exc:
            diagnostics['hub_requests_failed'] += 1
            diagnostics.setdefault('errors', []).append(f'Hub {hub["name"]}: {type(exc).__name__}: {str(exc)[:120]}')
    return result


def stable_key(item):
    # Exact URL path/case is preserved. DOI aliases normalized, but no lowercased URL paths.
    url = item['url'].strip().rstrip('/')
    if url.startswith('https://doi.org/'):
        url = url.lower()
    return hashlib.sha256((url + '\n' + item['region'] + '\n' + item['theme']).encode()).hexdigest()[:20]


def rank_and_dedupe(items, coverage, config):
    retained = {}
    priority = {'trusted_scholarly_venue': 3, 'independent_editorial': 2,
                'institutional_statistics': 1, 'official_primary': 1}
    for item in items:
        item['id'] = stable_key(item)
        cov = coverage.get(f'{item["region"]} | {item["theme"]}', 0)
        item['main_radar_existing_matches'] = cov
        item['blind_spot_priority'] = ('higher' if cov < 3 else 'normal')
        item['score'] = (70 if cov == 0 else 60 if cov < 3 else 40) + 3 * len(item['issue_terms']) + 5 * priority.get(item['source_kind'], 0)
        prev = retained.get(item['id'])
        if prev is None or (item['score'], len(item.get('abstract_or_context', ''))) > (prev['score'], len(prev.get('abstract_or_context', ''))):
            retained[item['id']] = item
    output = sorted(retained.values(), key=lambda x: (-x['score'], x['region'], x['theme'], x['title']))
    seen = Counter()
    bounded = []
    for item in output:
        key = (item['region'], item['theme'])
        if seen[key] >= config['max_candidates_per_region_theme']:
            continue
        seen[key] += 1
        bounded.append(item)
    return bounded


def write_results(outdir, config, anchors, coverage, items, diagnostics, now, offline=False):
    outdir.mkdir(parents=True, exist_ok=True)
    archive_path = outdir / 'archive.json'
    previous = {}
    if archive_path.exists():
        old = load_json(archive_path)
        if isinstance(old, dict):
            previous = {x['id']: x for x in old.get('items', []) if isinstance(x, dict) and x.get('id')}
    now_iso = now.isoformat()
    for row in items:
        old = previous.get(row['id'], {})
        row['first_seen'] = old.get('first_seen') or now_iso
        row['last_seen'] = now_iso
        row['new_this_run'] = row['id'] not in previous
        # Never overwrite previous human review decisions with machine 'needs_review'.
        if old.get('review_status') in ('accepted', 'rejected', 'investigate'):
            row['review_status'] = old['review_status']
    # Archive is bounded, retains previously discovered IDs, newest first, avoids churn.
    merged = {**previous, **{x['id']: x for x in items}}
    ordered = sorted(merged.values(), key=lambda x: (x.get('last_seen') or '', x['id']), reverse=True)
    archived = ordered[:config['max_stored_items']]
    archive_path.write_text(json.dumps({'schema_version': 1, 'items': archived}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = {'generated_at': now_iso, 'mode': 'offline_baseline_no_discovery' if offline else 'manual only', 'new_this_run': sum(x['new_this_run'] for x in items),
        'found_this_run': len(items), 'total_archive': len(archived), 'regions': list(config['regions']),
        'themes': list(config['themes']), 'existing_main_radar_coverage': coverage,
        'main_radar_anchors': anchors, 'diagnostics': dict(diagnostics), 'items': items}
    (outdir / 'latest.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    keys = ['new_this_run', 'region', 'theme', 'title', 'date', 'source', 'source_kind', 'evidence_status',
            'review_status', 'blind_spot_priority', 'main_radar_existing_matches', 'issue_terms',
            'matched_main_radar_titles', 'evidence_note', 'abstract_or_context', 'url']
    with (outdir / 'latest.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction='ignore')
        writer.writeheader()
        for row in items:
            flatten = dict(row)
            for key in ('issue_terms', 'matched_main_radar_titles'):
                flatten[key] = ' | '.join(row[key])
            # spreadsheet formula injection protection for external metadata
            for key, val in flatten.items():
                if isinstance(val, str) and val.lstrip().startswith(('=', '+', '-', '@')):
                    flatten[key] = "'" + val
            writer.writerow(flatten)
    lines = ['# Global R&I Blind Spots — ' + ('OFFLINE baseline (no live discovery)' if offline else 'latest manual scan'), '',
             f'Generated: {now_iso}. New: **{summary["new_this_run"]}**. Found: **{len(items)}**. Archive: **{len(archived)}**.', '',
             'Candidates are **not verified** and have **not been admitted to the main Radar**. Official source = evidence of an official statement, not proof of the outcome.', '',
             '## Existing main Radar issue × region coverage', '',
             '| Region | Theme | Main Radar matches | Newly discovered leads |', '|---|---|---:|---:|']
    for region in config['regions']:
        for theme in config['themes']:
            n = sum(x['region'] == region and x['theme'] == theme for x in items)
            lines.append(f'| {region} | {theme} | {coverage[f"{region} | {theme}"]} | {n} |')
    lines += ['', '## Highest priority leads', '']
    for x in items[:40]:
        clean_title = x['title'].replace('|', ' ')
        lines += [f'- **{x["region"]} · {x["theme"]}** — [{clean_title}]({x["url"]}) ({x["source"]}; {x["evidence_status"]}).',
                  f'  - Radar connection: {x["matched_main_radar_titles"][0] if x["matched_main_radar_titles"] else "none"}. Review: {x["review_status"]}.']
    lines += ['', '## Discovery diagnostics', '']
    for key in sorted(k for k in diagnostics if k != 'errors'):
        lines.append(f'- {key}: {diagnostics[key]}')
    for err in diagnostics.get('errors', [])[:20]:
        lines.append(f'- Source error: {err}')
    lines += ['', '## Method and limitations', '',
              '- Source admission: only main Radar trusted journals, explicitly allowlisted RSS and official/institutional websites.',
              '- All links require a substantive issue match and a specific external geographic lens (or explicitly country-scoped institutional feed).',
              '- Institutional homepage links can be unverified headlines; no claim is treated as confirmed without reading the source.',
              '- No LLM summarisation, translation, social media, press aggregation, automatic promotion, or change to the normal scanner.',
              '- If sources cannot be reached, errors are reported; zero results must not be mistaken for zero activity.', '']
    (outdir / 'LATEST.md').write_text('\n'.join(lines), encoding='utf-8')
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--offline', action='store_true', help='Generate a baseline coverage report without network or fabricated leads')
    p.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    p.add_argument('--radar', type=Path, default=ROOT / 'radar_active.json')
    p.add_argument('--config', type=Path, default=ROOT / 'global_blind_spots_config.json')
    args = p.parse_args(argv)
    config = load_json(args.config)
    radar = load_json(args.radar)
    radar_sources = load_json(ROOT / 'radar_config.json')
    config['_journal_allowlist'] = list(radar_sources['tier2_journals']) + list(radar_sources['tier2_comparable_journals'])
    anchors = extract_radar_anchors(radar, config)
    coverage = existing_coverage(radar, config)
    diagnostics = Counter()
    diagnostics['main_radar_items_considered'] = sum(len(radar.get(s, [])) for s in ('strand_a', 'strand_b', 'strand_c'))
    now = datetime.now(timezone.utc)
    leads = []
    if not args.offline:
        leads += discover_openalex(config, anchors, diagnostics, now)
        leads += discover_feeds(config, anchors, diagnostics, now)
        leads += discover_hubs(config, anchors, diagnostics)
        if diagnostics['openalex_requests_ok'] + diagnostics['rss_requests_ok'] + diagnostics['hub_requests_ok'] == 0:
            print('FAIL: Every configured discovery source failed. Refusing to overwrite latest report.', file=sys.stderr)
            for err in diagnostics.get('errors', [])[:8]:
                print(err, file=sys.stderr)
            return 2
    items = rank_and_dedupe(leads, coverage, config)
    report = write_results(args.output_dir, config, anchors, coverage, items, diagnostics, now, offline=args.offline)
    print(f'Global blind spots: {report["found_this_run"]} leads; {report["new_this_run"]} new; output={args.output_dir}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
