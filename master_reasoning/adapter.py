"""Read the TWO supplied xlsx schemas without mutating a workbook.

This is a bounded streaming OOXML adapter, not a general spreadsheet engine.
It respects review/verification status and never admits preliminary leads.
"""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse, urlunparse
from ._xlsx_rows import as_dicts


def _slug(x: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', x.casefold()).strip()


def _url(x: str) -> str:
    x=(x or '').strip()
    if not x: return ''
    try:
        p=urlparse(x)
        return urlunparse((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),'', '', ''))
    except ValueError: return x


def _id(*parts: str) -> str:
    return hashlib.sha256('|'.join(parts).encode('utf8')).hexdigest()[:20]


def _json(x: str, fallback):
    try: return json.loads(x) if x else fallback
    except (ValueError, TypeError): return fallback


@dataclass(frozen=True)
class Evidence:
    id: str
    source_type: str
    title: str
    publisher: str
    url: str
    date: str
    source_family: str
    quality_class: str
    admission: str
    aboutness: str
    geography: str
    confidence: str
    qualification: str
    source_key: str
    claims: tuple[dict, ...]
    context: str = ''
    observation_status: str = ''

    def as_json(self) -> dict:
        d=asdict(self)
        d['claims']=list(self.claims)
        return d


def _key(r: dict, title: str, url: str, date: str) -> str:
    doi=(r.get('doi') or r.get('Publication DOI') or r.get('DOI') or '').strip().casefold()
    if doi: return 'doi:'+doi.replace('https://doi.org/','').replace('doi:','')
    if url and 'news.google.com' not in url: return 'url:'+_url(url)
    return 'work:'+_id(_slug(title), date[:4])


def _family(publisher: str, source_domain: str = '') -> str:
    # This is only a *possible* common-source grouping, not proof of independence.
    return _slug(source_domain or publisher) or 'unknown'


def read_all(source_xlsx: str, global_xlsx: str) -> tuple[list[Evidence],dict[str,int]]:
    raw=[]
    cnt={'live_kept':0,'live_not_admitted':0,'historical_authoritative':0,
         'historical_not_authoritative':0,'global_verified':0,'global_review':0,
         'global_provisional':0,'regional_leads_quarantined':0}
    for r in as_dicts(source_xlsx,1):
        keep=r.get('admission_status','').lower()=='keep' and r.get('deep_scan_authoritative','').lower()=='true'
        if not keep:
            cnt['live_not_admitted']+=1
            continue
        cnt['live_kept']+=1
        title=r.get('title') or r.get('headline','')
        url=r.get('link') or r.get('review_resolved_url','')
        claims=_json(r.get('claims',''),[])
        claims=tuple(c for c in claims if isinstance(c,dict) and not c.get('provisional',False))
        date=r.get('date','')
        raw.append(Evidence(id='live:'+_id(_key(r,title,url,date)),source_type='live',title=title,
            publisher=r.get('source',''),url=url,date=date,source_family=_family(r.get('source',''),r.get('source_domain','')),
            quality_class='deep_scan_authoritative_keep',admission='keep',aboutness='eu_radar',geography='eu_or_report_scope',
            confidence=r.get('deep_analysis.confidence',''),qualification=r.get('deep_analysis.qualification',''),
            source_key=_key(r,title,url,date),claims=claims,context=r.get('deep_analysis.main_finding','')))
    for r in as_dicts(source_xlsx,2):
        keep=r.get('Authoritative historical','').lower()=='yes' and r.get('Deep Scan decision','').lower()=='keep' and r.get('deep_scan.verification.identity_verified','').lower()=='true'
        if not keep:
            cnt['historical_not_authoritative']+=1
            continue
        cnt['historical_authoritative']+=1
        title=r.get('scanner.title','')
        url=r.get('scanner.url','')
        date=r.get('scanner.date','')
        claims=tuple(c for c in _json(r.get('deep_scan.claims',''),[]) if isinstance(c,dict) and not c.get('provisional',False))
        raw.append(Evidence(id='historical:'+_id(r.get('Historical record key','')),source_type='historical',title=title,
            publisher=r.get('scanner.source',''),url=url,date=date,source_family=_family(r.get('scanner.source','')),
            quality_class='historical_authoritative_keep',admission='keep',aboutness='eu_radar',geography='eu_or_report_scope',
            confidence=r.get('deep_scan.deep_analysis.confidence',''),qualification=r.get('deep_scan.deep_analysis.qualification',''),
            source_key=_key(r,title,url,date),claims=claims,context=r.get('deep_scan.deep_analysis.main_finding','')))
    for r in as_dicts(global_xlsx,2):
        # Workbook Read me explicitly states this sheet is globally Deep Scan verified + KEEP.
        cnt['global_verified']+=1
        title=r.get('Title','')
        url=r.get('Primary evidence URL','')
        date=r.get('Evidence date','')
        raw.append(Evidence(id='global:'+_id(_key(r,title,url,date)),source_type='global_verified',title=title,
            publisher=r.get('Publisher',''),url=url,date=date,source_family=_family(r.get('Publisher','')),
            quality_class=r.get('Source integrity',''),admission='keep',aboutness=r.get('Radar topic',''),
            geography=r.get('Substantive geography',''),confidence='not_quantified',
            qualification=r.get('Uncertainties / alternatives',''),source_key=_key(r,title,url,date),
            claims=(), context=r.get('Mechanism',''),
            observation_status=r.get('Observed or possible','')))
    cnt['global_review']=sum(1 for _ in as_dicts(global_xlsx,4))
    cnt['global_provisional']=sum(1 for _ in as_dicts(global_xlsx,5))
    cnt['regional_leads_quarantined']=sum(1 for _ in as_dicts(global_xlsx,10))
    # Cross-table duplicates are observations of one work, NOT independent publications.
    # Prefer a live authoritative record over a historical or global duplicate.
    precedence={'live':0,'historical':1,'global_verified':2}
    raw.sort(key=lambda e:(precedence.get(e.source_type,99),e.id))
    seen=set(); deduped=[]
    for e in raw:
        if e.source_key in seen:continue
        seen.add(e.source_key)
        deduped.append(e)
    cnt['distinct_admitted_works']=len(deduped)
    cnt['admitted_structured_claims']=sum(len(e.claims) for e in deduped)
    return deduped,cnt


def write_jsonl(rows: Iterator[dict],path: str) -> None:
    with Path(path).open('w',encoding='utf8') as f:
        for x in rows:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
