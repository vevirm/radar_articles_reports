#!/usr/bin/env python3
"""Shared, non-LLM helpers for manually initiated research discovery.

The supplied JSON is untrusted navigation data. Only retrieved primary evidence is
used to establish publication identity, date, and substantive admission evidence.
"""
from __future__ import annotations

import datetime as dt
import html
import ipaddress
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote, urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 'eu-ri-llm-discovery-results-v1'
PACKAGE_FORMAT = 'eu-ri-llm-discovery-package-v1'
COLLECTIONS = ('strand_a', 'strand_b', 'strand_c', 'frontier_evidence', 'ab_archive', 'signal_archive')
MAX_FINDINGS = 24


def clean(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', html.unescape(clean(s)).casefold()).strip()


def doi(s):
    v = clean(s).lower()
    v = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:)', '', v)
    return v.rstrip('.,) ') if re.fullmatch(r'10\.\d{4,9}/\S+', v) else ''


def same_title(a, b, threshold=.88):
    x, y = norm(a), norm(b)
    return bool(x and y and (x == y or SequenceMatcher(None, x, y).ratio() >= threshold))


def host(url):
    try:
        p = urlparse(url)
        if p.scheme != 'https' or p.username or p.password or p.port not in (None, 443):
            return ''
        h = (p.hostname or '').strip('.').lower()
        if not h or h == 'localhost' or h.endswith(('.local', '.internal')):
            return ''
        try:
            ipaddress.ip_address(h)
            return ''
        except ValueError:
            pass
        if '.' not in h:
            return ''
        return h
    except (ValueError, TypeError):
        return ''


def domain_matches(domain, suffix):
    return domain == suffix or domain.endswith('.' + suffix)


def safe_http_url(url):
    return bool(host(url)) and len(url) <= 1600


def infer_miss_reason(row, deferred):
    candidate_doi = doi(row.get('doi') or row.get('_doi'))
    title = clean(row.get('title'))
    for entry in deferred:
        raw = entry.get('raw') if isinstance(entry.get('raw'), dict) else {}
        raw_title = raw.get('title') or raw.get('display_name') or ''
        if isinstance(raw_title, list):
            raw_title = raw_title[0] if raw_title else ''
        raw_doi = doi(raw.get('DOI') or raw.get('doi'))
        if candidate_doi and raw_doi == candidate_doi or title and same_title(title, raw_title, .94):
            return 'scanner_deferred_incomplete_metadata', clean(entry.get('key'))
    return 'not_determinable_from_saved_scanner_state', ''


def identities(corpus, pool=None):
    result = []
    for collection in COLLECTIONS:
        for row in corpus.get(collection, []) if isinstance(corpus.get(collection), list) else []:
            if isinstance(row, dict):
                result.append((row, collection))
    if isinstance(pool, dict):
        for bucket, label in (('candidates', 'private_deep_a'),
                              ('historical', 'historical_archive'),
                              ('rejected_history', 'previously_reviewed_deep_a')):
            for row in pool.get(bucket, []):
                if isinstance(row, dict):
                    result.append((row, label))
    return result


def duplicate_of(item, known):
    from scripts.scan_radar import identity
    d = doi(item.get('doi') or item.get('_doi') or item.get('link'))
    title = clean(item.get('title'))
    link = clean(item.get('link') or item.get('official_url')).lower().rstrip('/')
    ident = identity({'title': title, '_doi': d, 'link': link})
    for row, where in known:
        other_doi = doi(row.get('doi') or row.get('_doi') or row.get('link'))
        other_url = clean(row.get('link') or row.get('url')).lower().rstrip('/')
        other_title = clean(row.get('title') or row.get('headline'))
        # Do not allow different DOIs to alias by similar titles indiscriminately.
        if (d and other_doi == d) or (link and link == other_url) or (title and same_title(title, other_title, .945)) or (ident == identity(row) and ident != 'title:'):
            return where, other_title
    return None


def text_of_html(markup):
    soup = BeautifulSoup(markup, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'noscript']):
        tag.decompose()
    main = soup.find('article') or soup.find('main') or soup.body or soup
    return clean(main.get_text(' ', strip=True))[:110000]


def metadata_html(markup):
    soup = BeautifulSoup(markup, 'html.parser')
    meta = {}
    for m in soup.find_all('meta'):
        name = clean(m.get('name') or m.get('property') or m.get('itemprop')).lower()
        if name and m.get('content'):
            meta[name] = clean(m['content'])
    titles = [meta.get(x, '') for x in ('citation_title', 'dc.title', 'og:title')]
    h1 = soup.find('h1')
    if h1:
        titles.append(clean(h1.get_text(' ', strip=True)))
    if soup.title:
        titles.append(clean(soup.title.get_text(' ', strip=True)))
    dates = []
    for name in ('citation_publication_date', 'citation_online_date', 'article:published_time', 'datepublished', 'dc.date.issued', 'dc.date', 'dc.date.created'):
        if meta.get(name):
            dates.append((name, meta[name]))
    for script in soup.find_all('script', attrs={'type': re.compile(r'ld\+json', re.I)}):
        try:
            obj = json.loads(script.string or script.get_text())
        except (ValueError, TypeError):
            continue
        stack = [obj]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                if isinstance(node.get('datePublished'), str):
                    dates.append(('jsonld.datePublished', node['datePublished']))
                for x in ('@graph', 'mainEntity'):
                    if isinstance(node.get(x), (list, dict)):
                        stack.append(node[x])
    abstracts = [meta.get(x, '') for x in ('citation_abstract', 'dc.description', 'description', 'og:description')]
    return [t for t in titles if t], dates, [a for a in abstracts if len(a.split()) >= 25]


def exact_date(v):
    m = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:T|\s|$)', clean(v))
    if not m:
        return None
    try:
        return dt.date(*(int(x) for x in m.groups()))
    except ValueError:
        return None


def crossref_date(rec):
    for field in ('published-online', 'published', 'published-print', 'issued'):
        parts = (rec.get(field) or {}).get('date-parts') or []
        if parts and isinstance(parts[0], list) and len(parts[0]) >= 3:
            try:
                return dt.date(*[int(x) for x in parts[0][:3]]), field
            except ValueError:
                pass
    return None, ''


def passage_supported(passage, text):
    needle, hay = norm(passage), norm(text)
    return len(needle) >= 65 and len(passage.split()) >= 10 and needle in hay


def write_json(path: Path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
