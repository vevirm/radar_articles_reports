#!/usr/bin/env python3
"""Additional relevance lane: targeted OpenAlex discovery, standard Radar admission, verified backfill.

Standalone, non-destructive: existing scanners and Deep Scan decisions remain authoritative.
Discovery candidates are locator hints, NEVER directly inserted into the Radar corpus.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEEP_PROFILE = 'deep-reader-v2-authoritative'

# Exact requested countries and supra-national regions.  Europe as a whole is NOT a
# match: this avoids filling the workbook with ordinary EU-only publications.
GEOGRAPHY = {
 'Europe — enlargement': {
  'Albania':r'\balbani(?:a|an)\b', 'Bosnia and Herzegovina':r'\bbosni(?:a|an)\b|\bherzegovin(?:a|ian)\b',
  'Georgia':r'\bgeorgi(?:a|an)\b(?!\s+tech)', 'Kosovo':r'\bkosov(?:o|ar)\b',
  'Moldova':r'\bmoldov(?:a|an)\b', 'Montenegro':r'\bmontenegr(?:o|in)\b',
  'North Macedonia':r'\bnorth\s+macedoni(?:a|an)\b', 'Serbia':r'\bserbi(?:a|an)\b',
  'Ukraine':r'\bukrain(?:e|ian)\b', 'Türkiye':r'\bt[üu]rkiy(?:e|an)\b|\bturk(?:ey|ish)\b'},
 'Americas': {
  'United States':r'\bunited\s+states\b|\bU\.S\.A?\.?\b|\bUS[–-](?:China|EU|Europe)\b|\bamerican\b',
  'Canada':r'\bcanad(?:a|ian)\b', 'Brazil':r'\bbrazil(?:ian)?\b', 'Argentina':r'\bargentin(?:a|ian)\b',
  'Chile':r'\bchil(?:e|ean)\b', 'Mexico':r'\bmexic(?:o|an)\b',
  'Latin America and Caribbean':r'\blatin\s+america(?:n)?\b|\bcaribbean\b|\bLAC\b'},
 'Africa': {'Egypt':r'\begypt(?:ian)?\b', 'Ethiopia':r'\bethiopi(?:a|an)\b',
  'Kenya':r'\bkeny(?:a|an)\b', 'Morocco':r'\bmorocc(?:o|an)\b', 'Nigeria':r'\bnigeri(?:a|an)\b',
  'Rwanda':r'\brwand(?:a|an)\b', 'South Africa':r'\bsouth\s+afric(?:a|an)\b'},
 'Asia & Pacific': {'ASEAN':r'\bASEAN\b|\bsoutheast\s+asia(?:n)?\b', 'Indonesia':r'\bindonesi(?:a|an)\b',
  'Malaysia':r'\bmalaysi(?:a|an)\b', 'Singapore':r'\bsingapor(?:e|ean)\b',
  'Thailand':r'\bthai(?:land)?\b', 'Viet Nam':r'\bviet\s*nam(?:ese)?\b',
  'Australia':r'\baustrali(?:a|an)\b', 'Central Asia':r'\bcentral\s+asia(?:n)?\b|\bkazakhst(?:an|ani)\b|\buzbekist(?:an|ani)\b|\bkyrgyzst(?:an|ani)\b|\btajikist(?:an|ani)\b|\bturkmenist(?:an|ani)\b',
  'China':r'\bchin(?:a|ese)\b', 'India':r'\bindi(?:a|an)\b'},
 'Middle East': {'Iran':r'\biran(?:ian)?\b','Israel':r'\bisrael(?:i)?\b',
  'Palestine':r'\bpalestin(?:e|ian)\b','Jordan':r'\bjordan(?:ian)?\b',
  'Saudi Arabia':r'\bsaudi\b','UAE':r'\bUAE\b|\bunited\s+arab\s+emirates\b|\bemirati\b'},
}

ISSUES = {
 'Critical raw materials × R&I / technology':r'\bcritical\s+(?:raw\s+)?materials?\b|\brare\s+earths?\b|\bcritical\s+minerals?\b|\blithium\b|\bcobalt\b|\bgraphite\b|\bsemiconductor\s+supply\s+chain\b',
 'Research security / dual use':r'\bresearch\s+security\b|\bdual[ -]use\b|\bexport\s+controls?\b|\bknowledge\s+security\b|\bacademic\s+espionage\b|\btechnology\s+transfer\s+controls?\b',
 'Arabian Peninsula knowledge / technology power':r'\b(?:qatar|bahrain|kuwait|oman|saudi|emirat(?:es|i)|UAE|arabian\s+peninsula)\b.{0,115}\b(?:science|research|universit|knowledge|technolog|innovation|AI|digital)\b|\b(?:science|research|universit|knowledge|technolog|innovation)\b.{0,115}\b(?:qatar|bahrain|kuwait|oman|saudi|emirat(?:es|i)|UAE|arabian\s+peninsula)\b',
 'China in Africa / LAC':r'\bchin(?:a|ese)\b.{0,140}\b(?:africa|african|latin\s+america|caribbean|brazil|mexico|argentina|chile)\b|\b(?:africa|african|latin\s+america|caribbean|brazil|mexico|argentina|chile)\b.{0,140}\bchin(?:a|ese)\b',
 'Science diplomacy':r'\bscience\s+diplomac\w*\b|\bscientific\s+diplomac\w*\b|\bdiplomac\w*\s+(?:through\s+)?(?:science|research|innovation)\b|\bresearch\s+diplomac\w*\b',
 'Ocean / deep sea beyond national jurisdiction':r'\bbeyond\s+national\s+jurisdiction\b|\bBBNJ\b|\bdeep[ -]sea\b|\bdeep[ -]ocean\b|\bseabed\b|\bhigh\s+seas\b|\bocean\s+governance\b|\bmarine\s+biodiversity\b',
 'Science-based international organisations':r'\bUNESCO\b|\bIPCC\b|\bWorld\s+Health\s+Organi[sz]ation\b|\b(?-i:WHO)\b|\bintergovernmental\s+science\b|\bscience[ -]based\s+international\s+organi[sz]ations?\b',
 'Transnational R&I and innovation policy':r'\b(?:international|cross[ -]border|bilateral|multilateral|global)\s+(?:scientific\s+|science\s+|research\s+|innovation\s+|technolog\w*\s+)(?:collaboration|cooperation|partnership|policy|governance|diplomacy|networks?)\b|\b(?:research|science|technology|innovation)\s+(?:relations|partnerships|agreements|diplomacy|cooperation)\b|\bresearch\s+and\s+innovation\s+policy\b|\bR&I\s+policy\b',
 'Australia strategic reorientation to Europe':r'\baustrali(?:a|an)\b.{0,135}\b(?:europe|european|EU|UK|US|united\s+states)\b|\b(?:europe|european|EU)\b.{0,135}\baustrali(?:a|an)\b',
}
STAKEHOLDERS = {
 'Universities / research institutions':r'\buniversit\w*\b|\bacademi(?:c|a)\b|\bresearch\s+institut\w*\b',
 'NGOs / civil society':r'\bNGOs?\b|\bnon[ -]governmental\b|\bcivil\s+society\b',
 'Business / industry':r'\b(?:businesses|firms|industr(?:y|ies)|private\s+sector|companies|enterprises)\b',
 'Faith-based communities':r'\bfaith[ -]based\b|\breligious\s+(?:communit\w*|organi[sz]ations?)\b',
 'Foreign-affairs / trade / non-research ministries':r'\b(?:ministr(?:y|ies)|minister)\s+of\s+(?:foreign|trade|economic|industry|education|defen[cs]e|environment|health)\b|\bforeign\s+affairs\b|\btrade\s+ministr\w*\b',
}
RI = re.compile(r'\bresearch\b|\bscience\b|\bscientific\b|\binnovation\b|\btechnolog\w*\b|\bR&D\b|\bR&I\b|\bacademi\w*\b|\buniversit\w*\b|\bknowledge\b|\bforesight\b|\bsemiconductors?\b|\bAI\b',re.I)
POLICY = re.compile(r'\bpolic\w*\b|\bstrateg\w*\b|\bgeopolit\w*\b|\bgovern\w*\b|\bdiplomac\w*\b|\bcooperat\w*\b|\bcollaborat\w*\b|\bsecurity\b|\bcompetition\b|\bpartnership\w*\b|\bsovereign\w*\b|\bdevelopment\b|\bforesight\b|\bgeoeconom\w*\b|\btransform\w*\b|\btransition\b|\bfuture\b',re.I)
STRONG = set(ISSUES) - {'Transnational R&I and innovation policy','Australia strategic reorientation to Europe'}


def hits(text: str, dictionary: dict) -> list[str]:
    return [name for name, pat in dictionary.items() if re.search(pat,text,re.I)]


def clean(s):
    return re.sub(r'\s+',' ',str(s or '')).strip()


def matching(title: str, body: str) -> dict | None:
    title, body = clean(title), clean(body)
    text = f'{title}. {body}'[:14000]
    if not title or not RI.search(text):
        return None
    geo = [(group,place) for group,patterns in GEOGRAPHY.items() for place,pat in patterns.items() if re.search(pat,text,re.I)]
    issues = hits(text,ISSUES)
    people = hits(text, STAKEHOLDERS)
    if not issues: return None
    strong = [s for s in issues if s in STRONG]
    tgeo = [(g,p) for g,p in geo if re.search(GEOGRAPHY[g][p],title,re.I)]
    tiss = [s for s in issues if re.search(ISSUES[s],title,re.I)]
    # On general US/China/EU material a country name alone is not a relevance claim.
    qualifying = bool(strong and (geo or any(s in tiss for s in strong))) or bool(geo and POLICY.search(text) and 'Transnational R&I and innovation policy' in issues)
    if not qualifying: return None
    if 'Science-based international organisations' in issues and not (geo or any(re.search(r'\b(?:withdraw\w*|future|scenario|reform|funding|governance|influence|multilateral|geopolit\w*|leadership|institutional|cooperation|diplomac\w*)\b',text,re.I) for _ in [0])) and len(issues)==1:
        return None
    score = min(99, 40 + (17 if strong else 0) + (11 if geo else 0) + min(12, len(tiss)*7) + min(8,len(tgeo)*4) + min(9,len(issues)*3) + (5 if POLICY.search(title) else 0))
    # Explicit issue + region, or explicit title issue, is strongest.  Scores rank matches,
    # not scientific validity; verification remains exclusively Deep Scan/admission.
    reason = 'Region: ' + (', '.join(p for _,p in geo[:12]) or 'cross-regional / ABNJ') + '; issue: ' + ', '.join(issues[:6])
    return {'score':score,'regions':'; '.join(dict.fromkeys(g for g,_ in geo)),
            'countries':'; '.join(dict.fromkeys(p for _,p in geo)),
            'issues':'; '.join(issues),'stakeholders':'; '.join(people),'match_reason':reason}


def load(rel, default):
    p=ROOT/rel
    try: return json.loads(p.read_text(encoding='utf8'))
    except FileNotFoundError: return default


def link_key(x):
    url=clean(x.get('link') or x.get('url') or x.get('landing_page_url'))
    if url:
        return 'link:'+url.lower().rstrip('/')
    return ''


def related_record_keys(x, historical=False):
    base=[]
    if historical and x.get('id'): base.append('historical:id:'+str(x['id']))
    if historical and x.get('doi'):base.append('historical:doi:'+str(x['doi']).lower())
    if historical and x.get('url'):base.append('historical:link:'+str(x['url']))
    lk=link_key(x)
    if lk:base.extend([lk,lk.replace('https://doi.org/','https://dx.doi.org/')])
    return list(dict.fromkeys(base))


def compile_records():
    active=load('radar_active.json',{})
    if not active:active=load('radar.json',{})
    historical=load('historical/historical.json',{})
    deep=load('deep_scan_work_state.json',{}).get('records',{})
    admissions=load('admission_state.json',{}).get('records',{})
    reader=load('reader_text.json',{}).get('records',{})
    verified=[]; pending=[]; seen=set(); stats=Counter()
    collections=[(f'Main {letter}', active.get('strand_'+letter.lower(),[]),False) for letter in 'ABC']
    collections.append(('Historical',historical.get('items',[]),True))
    for source, items, is_hist in collections:
        for item in items:
            if not isinstance(item,dict):continue
            keys=related_record_keys(item,is_hist)
            rt=next((reader[k] for k in keys if k in reader),{})
            ad=next((admissions[k] for k in keys if k in admissions),{})
            ds=next((deep[k] for k in keys if k in deep),{})
            link=clean(item.get('link') or item.get('url') or item.get('landing_page_url'))
            title=clean(item.get('title') or item.get('headline'))
            identity=link.lower().rstrip('/') or re.sub(r'[^a-z0-9]','',title.lower())
            if not identity or identity in seen:continue
            seen.add(identity)
            analysis=rt.get('deep_analysis') if isinstance(rt.get('deep_analysis'),dict) else item.get('deep_analysis') or {}
            body=' '.join(clean(x) for x in [item.get('summary'),item.get('core_message'),item.get('reader_point'),item.get('why_it_matters'),item.get('relevance_note'),item.get('reader_what'),item.get('reader_why'),item.get('reader_more'),rt.get('reader_what'),rt.get('reader_why'),rt.get('reader_more'),analysis.get('main_finding'),analysis.get('radar_relevance'),analysis.get('method_or_basis')])
            match=matching(title, body)
            if match is None:continue
            decision=clean(ad.get('decision') or rt.get('admission',{}).get('decision') or item.get('admission_status')).lower()
            deep_ok=(ds.get('status')=='verified' and rt.get('profile')==DEEP_PROFILE and bool(rt.get('verification',{}).get('identity_verified')))
            # Deep Scan is an evidence status, not a free pass for rejected works.
            if decision in {'drop','drop_unverifiable','duplicate','needs_manual_verification'}:
                stats['excluded_not_retained']+=1
                continue
            record={'title':title,'date':clean(item.get('date')),'source':clean(item.get('source') or item.get('venue')),
              'authors':clean(item.get('authors')),'source_location':source,'url':link,
              'strand':clean(item.get('strand') or source.removeprefix('Main ')),
              'reader_what':clean(rt.get('reader_what') or item.get('reader_what') or item.get('reader_point')),
              'reader_why':clean(rt.get('reader_why') or item.get('reader_why') or item.get('why_it_matters')),
              'verification': 'Deep Scan verified — retained' if deep_ok and decision=='keep' else 'Review / awaiting authoritative retention',
              'admission':decision or 'not yet checked','verified_at':clean(ds.get('verified_at')),
              'deep_scan_package':clean(ds.get('verified_package_id') or rt.get('deep_scan_package_id')),
              **match}
            if deep_ok and decision=='keep':verified.append(record)
            else:pending.append(record)
    verified.sort(key=lambda a:(-a['score'],a['date'],a['title']))
    pending.sort(key=lambda a:(-a['score'],a['date'],a['title']))
    return {'generated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
     'verified':verified,'pending':pending,'statistics':dict(stats),
     'catalogue':{'countries':list(dict.fromkeys(k for group in GEOGRAPHY.values() for k in group)),
                  'regions':list(GEOGRAPHY),'issues':list(ISSUES),'stakeholders':list(STAKEHOLDERS)},
     'policy':'Matched by explicit requested geography and science-policy / issue context. Verified sheet requires Deep Scan identity verification and a KEEP admission decision. Other matches are separated for review; nothing is promoted by this workbook.'}


# Round-robin coverage across the entire supplied list (rather than focusing on
# only the largest OpenAlex publishing countries).  Subregional themes included.
SEARCHES = [
 ('Europe — enlargement',v+' research innovation science diplomacy European Union') for v in
 ('Albania','Bosnia Herzegovina','Georgia country','Kosovo','Moldova','Montenegro','North Macedonia','Serbia','Ukraine','Türkiye')
] + [
 ('Americas',v+' science diplomacy research technology Europe') for v in
 ('United States','Canada','Brazil','Argentina','Chile','Mexico','Latin America Caribbean')
] + [
 ('Africa',v+' science technology China cooperation research') for v in
 ('Egypt','Ethiopia','Kenya','Morocco','Nigeria','Rwanda','South Africa')
] + [
 ('Asia & Pacific',v+' innovation Europe science diplomacy policy') for v in
 ('ASEAN','Indonesia','Malaysia','Singapore','Thailand','Vietnam','Australia','Central Asia','China','India')
] + [
 ('Middle East',v+' research science diplomacy international relations') for v in
 ('Iran','Israel','Palestine','Jordan','Saudi Arabia','United Arab Emirates')
] + [
 ('Issue',q) for q in (
  'critical raw materials research security technology geopolitics',
  'critical minerals innovation policy research technology',
  'research security emerging technologies international collaboration',
  'Saudi Arabia Qatar UAE emerging science university technology knowledge',
  'China Africa science technology diplomacy innovation',
  'China Latin America research innovation infrastructure',
  'science diplomacy Central Asia research cooperation',
  'science diplomacy Latin America European Union',
  'science diplomacy Middle East universities',
  'UNESCO WHO IPCC US withdrawal Chinese influence science governance',
  'global science organisations funding US withdrawal China',
  'ocean high seas beyond national jurisdiction research policy',
  'deep sea seabed mining emerging technology research governance',
  'science diplomacy faith based NGOs business foreign affairs ministries',
  'Australia pivot UK US toward Europe science research',
 )
]


def openalex_abstract(index):
    if not isinstance(index,dict):return ''
    seq=[]
    for word, positions in index.items():
        if isinstance(positions,list):seq.extend((i,word) for i in positions if isinstance(i,int) and 0<=i<500)
    return ' '.join(w for _,w in sorted(seq))[:5000]


def discover(path: Path, max_seconds=125, max_searches=32, max_candidates=90):
    import requests  # no network dependency required for one-hit/backfill-only
    since='2025-01-01'
    session=requests.Session()
    session.headers.update({'User-Agent':'EU-RI-Relevance-Scanner/1.0 (public research discovery)'})
    api_key=clean(os.environ.get('OPENALEX_API_KEY'))
    now=datetime.now(timezone.utc)
    # Four-hour slot rotating sequentially, stable on reruns within a slot.
    slot=int(now.timestamp()//(4*3600))
    grouped={}
    for bucket, q in SEARCHES: grouped.setdefault(bucket,[]).append(q)
    order=[]
    for bucket, queries in grouped.items():
        offset=(slot*3)%len(queries)
        order.extend((bucket,queries[(offset+i)%len(queries)]) for i in range(min(5,len(queries))))
    # Append more rotating issue queries whenever budget permits.
    issue=grouped['Issue'];order += [('Issue',issue[(slot+ix)%len(issue)]) for ix in range(6)]
    order=order[:max_searches]
    known={clean(x.get('link') or x.get('url')).lower().rstrip('/') for area in ('strand_a','strand_b','strand_c') for x in load('radar.json',{}).get(area,[])}
    known.update(clean(x.get('url')).lower().rstrip('/') for x in load('historical/historical.json',{}).get('items',[]))
    picked={};stats=Counter();start=time.monotonic()
    for bucket,q in order:
        if time.monotonic()-start>max_seconds:break
        try:
            params={
             'search':q,'filter':f'from_publication_date:{since},to_publication_date:{now.date().isoformat()}',
             'per-page':8,'select':'id,display_name,doi,publication_date,primary_location,abstract_inverted_index,authorships,type',
            }
            if api_key: params['api_key']=api_key
            resp=session.get('https://api.openalex.org/works',params=params,timeout=12)
            if resp.status_code==429:
                stats['rate_limited']+=1;break
            if not resp.ok:
                stats['http_error']+=1;continue
            works=resp.json().get('results',[])
            stats['queries_completed']+=1
        except (requests.RequestException,ValueError):
            stats['network_error']+=1;continue
        for w in works:
            title=clean(w.get('display_name')); doi=clean(w.get('doi'))
            link=doi or clean(w.get('id'))
            if not title or (link.lower().rstrip('/') in known):continue
            matched=matching(title,openalex_abstract(w.get('abstract_inverted_index')))
            if not matched:continue
            canonical=doi.lower() if doi else title.casefold()
            if canonical in picked:continue
            source=(w.get('primary_location') or {}).get('source') or {}
            picked[canonical]={'candidate_id':'REL-'+hashlib.sha256(canonical.encode()).hexdigest()[:14],
             'group_id':'relevance-focus', 'role_in_group':'primary','candidate_kind':'substantive_publication',
             'title':title,'source':clean(source.get('display_name')),
             'date':clean(w.get('publication_date')),'doi':doi.removeprefix('https://doi.org/'),
             'url':link,'curator_note':'Relevance focus: '+matched['match_reason'],
             '_score':matched['score']}
            stats['candidate_matches']+=1
    candidates=sorted(picked.values(),key=lambda x:-x.pop('_score'))[:max_candidates]
    out={'profile_version':'v1-relevance-priority-discovery','batch_id':'relevance-'+now.strftime('%Y%m%dT%H%M%SZ'),
     'source_document':'OpenAlex focused literature discovery; candidate metadata only',
     'compiled_at':now.isoformat(),'policy':{'admission':'Normal Radar A/B/C source and relevance gates are mandatory; no automatic admission'},
     'candidates':candidates,'work_count':len(candidates),'discovery_stats':dict(stats)}
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
    print('Relevance discovery:',len(candidates),'new exact candidates;',dict(stats),'->',path,flush=True)


def scan(candidate_path:Path):
    # Reuse the existing priority scanner + all existing admission and dedupe gates.
    # Only time allocation is modified in memory for this one scan.
    os.environ['RADAR_PRIORITY_SCAN']='true'
    os.environ['RADAR_CURATOR_CANDIDATE_INPUTS']=str(candidate_path)
    os.environ.setdefault('RADAR_SCAN_BUDGET_SECONDS','1500')
    os.environ['RADAR_RESCUE_MODE']='false'
    import scan_radar
    seconds=int(os.environ['RADAR_SCAN_BUDGET_SECONDS'])
    scan_radar.CONFIG['curator_candidate_tests_per_scan']=110
    scan_radar.CONFIG['curator_candidate_testing_stage_seconds']=max(120,int(seconds*0.73))
    # Main scanner still works on all normal sources with the remaining allocation.
    print('Relevance priority scanner: standard gates; time budget',seconds,'seconds',flush=True)
    return scan_radar.main()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['discover','scan','export-json'])
    p.add_argument('--output',type=Path,default=Path(os.getenv('RUNNER_TEMP','/tmp'))/'relevance_candidates.json')
    p.add_argument('--candidates',type=Path,default=Path(os.getenv('RUNNER_TEMP','/tmp'))/'relevance_candidates.json')
    p.add_argument('--max-seconds',type=int,default=125)
    args=p.parse_args()
    if args.command=='discover': discover(args.output,max_seconds=args.max_seconds)
    elif args.command=='scan': return scan(args.candidates)
    else:
        data=compile_records();args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
        print('Relevance workbook:',len(data['verified']),'verified and retained,',len(data['pending']),'for review',flush=True)
    return 0


if __name__=='__main__':sys.exit(main())
