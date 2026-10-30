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
 'EU external R&I partnerships / enlargement':r'\b(?:horizon europe|framework programme|european research area|EU[–-](?:africa|india|asean|latin america|balkan|australia)|european union|european commission|european research|european innovation)\b.{0,170}\b(?:partner\w*|cooperat\w*|collaborat\w*|enlarg\w*|accession|integration|talent|research infrastructur\w*|digital ties|science|technology|innovation)\b|\b(?:partner\w*|cooperat\w*|collaborat\w*|enlarg\w*|accession|integration|talent|research infrastructur\w*|digital ties)\b.{0,170}\b(?:horizon europe|european union|european research|european innovation|EU[–-](?:africa|india|asean|latin america|balkan|australia))\b',
 'EU-facing technology standards / regulatory alignment':r'\b(?:european union|european|EU)\b.{0,145}\b(?:AI regulation|AI governance|digital regulation|standards|standardisation|standardization|cybersecurity|supply.chain resilience|technology governance)\b|\b(?:AI regulation|AI governance|digital regulation|standards|standardisation|standardization|cybersecurity|supply.chain resilience|technology governance)\b.{0,145}\b(?:european union|european|EU)\b',
 'Equitable international research partnerships':r'\b(?:african.european|european.african|europe.africa|EU.africa|global south)\b.{0,140}\b(?:research|science|epistemic|collaborat|partnership|infrastructur)\b|\b(?:research|science|epistemic|collaborat|partnership|infrastructur)\b.{0,140}\b(?:african.european|european.african|europe.africa|EU.africa|global south)\b',
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
    eu_anchor = bool(re.search(r'\b(?:EU|Europe(?:an)?|Horizon Europe|European Research Area|Framework Programme)\b', text, re.I))
    eu_facing = {'EU external R&I partnerships / enlargement', 'EU-facing technology standards / regulatory alignment', 'Equitable international research partnerships'}
    if issues and set(issues).issubset(eu_facing) and not eu_anchor:
        return None
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


# Mechanism-led, EU-anchored searches derived from missed verified Radar evidence.
# These COMPLEMENT country coverage queries: neither search results nor geographic
# mentions bypass Main Radar source/quality/Europe/admission/Deep Scan checks.
EU_MECHANISM_SEARCHES = [
 ('Europe — enlargement', 'EU Western Balkans innovation ecosystems economic complexity accession'),
 ('Europe — enlargement', 'European Research Area enlargement candidates research integration'),
 ('Europe — enlargement', 'Horizon Europe association Ukraine Moldova Georgia Western Balkans research'),
 ('Europe — enlargement', 'EU enlargement partners digital cybersecurity research resilience'),
 ('Africa', 'EU Africa research infrastructure digital science capacity partnerships'),
 ('Africa', 'African European research collaboration epistemic inequalities equitable partnerships'),
 ('Africa', 'European Union Africa China technology research infrastructure competition'),
 ('Africa', 'EU Global Gateway Africa research innovation digital skills'),
 ('Americas', 'EU Latin America Caribbean high performance computing AI research partnership'),
 ('Americas', 'EU CELAC research infrastructures science technology cooperation'),
 ('Americas', 'Europe Brazil Mexico Chile research diplomacy technology governance'),
 ('Americas', 'EU Latin America China digital infrastructure innovation standards'),
 ('Asia & Pacific', 'EU ASEAN technology standards artificial intelligence governance comparison'),
 ('Asia & Pacific', 'European Union ASEAN research partnerships supply chain resilience'),
 ('Asia & Pacific', 'EU India health science diplomacy research talent mobility'),
 ('Asia & Pacific', 'EU Central Asia research connectivity critical minerals science diplomacy'),
 ('Asia & Pacific', 'EU Australia Horizon Europe science cooperation strategic partnership'),
 ('Middle East', 'European Union Gulf Saudi UAE Qatar research innovation universities partnerships'),
 ('Middle East', 'EU Israel Palestine Jordan regional research cooperation science diplomacy'),
 ('Middle East', 'EU Iran science technology diplomacy research restrictions'),
 ('Issue', 'European Union science diplomacy UNESCO WHO IPCC multilateral governance reform'),
 ('Issue', 'EU response US withdrawal global science organisations China influence'),
 ('Issue', 'European research diplomacy high seas BBNJ marine science governance'),
 ('Issue', 'Europe deep seabed mining critical minerals ocean science international regulation'),
 ('Issue', 'EU critical raw materials external research partnerships knowledge security'),
 ('Issue', 'EU science diplomacy faith based civil society universities industry ministries'),
 ('Issue', 'EU foreign affairs trade ministries international science technology diplomacy'),
]
SEARCHES.extend(EU_MECHANISM_SEARCHES)


def openalex_abstract(index):
    if not isinstance(index,dict):return ''
    seq=[]
    for word, positions in index.items():
        if isinstance(positions,list):seq.extend((i,word) for i in positions if isinstance(i,int) and 0<=i<500)
    return ' '.join(w for _,w in sorted(seq))[:5000]


# Run a whole 25 minutes of *focused discovery*.  Candidate admission and the
# workbook generation happen AFTER this period; neither is charged to it.
FOCUSED_DISCOVERY_SECONDS = 25 * 60
FOCUSED_REQUEST_PACING_SECONDS = 5.0   # polite API use, also avoids rate-limit bursts
FOCUSED_PAGE_DEPTH = 24


def focused_search_plan(slot: int):
    """Interleave all regions and issues before going deeper (no repetitive page-1 loop)."""
    buckets = {}
    for bucket, query in SEARCHES:
        buckets.setdefault(bucket, []).append(query)
    for bucket, queries in buckets.items():
        rotate = slot % len(queries)
        buckets[bucket] = queries[rotate:] + queries[:rotate]
    order = []
    for position in range(max(map(len, buckets.values()))):
        for bucket, queries in buckets.items():
            if position < len(queries):
                order.append((bucket, queries[position]))
    # Unique endpoint/query/page combinations: search deeper instead of repeating
    # the same 32 searches when the first results are old/already known.
    for page in range(1, FOCUSED_PAGE_DEPTH + 1):
        for bucket, query in order:
            yield bucket, query, 'openalex', page
            yield bucket, query, 'crossref', page


def crossref_date(item):
    for field in ('published', 'published-online', 'published-print', 'created'):
        parts = (item.get(field) or {}).get('date-parts') or []
        if parts and parts[0]:
            try:
                return '-'.join(f'{int(n):0{4 if i == 0 else 2}d}' for i, n in enumerate(parts[0][:3]))
            except (TypeError, ValueError):
                pass
    return ''


def relevance_work(source, work):
    """Normalize locator metadata only; Main Radar alone judges source and admission."""
    if source == 'openalex':
        title = clean(work.get('display_name'))
        abstract = openalex_abstract(work.get('abstract_inverted_index'))
        doi = clean(work.get('doi'))
        link = doi or clean(work.get('id'))
        venue = clean(((work.get('primary_location') or {}).get('source') or {}).get('display_name'))
        published = clean(work.get('publication_date'))
    else:
        title = clean((work.get('title') or [''])[0])
        # Crossref abstracts can be JATS fragments; strip tags before matching.
        abstract = re.sub(r'<[^>]+>', ' ', clean(work.get('abstract')))
        doi = clean(work.get('DOI'))
        link = clean(work.get('URL')) or ('https://doi.org/' + doi if doi else '')
        venue = clean((work.get('container-title') or [''])[0])
        published = crossref_date(work)
    if not link or not title:
        return None
    match = matching(title, abstract)
    if not match:
        return None
    canonical = doi.casefold().removeprefix('https://doi.org/') if doi else title.casefold()
    candidate = {
        'candidate_id':'REL-'+hashlib.sha256(canonical.encode()).hexdigest()[:14],
        'group_id':'relevance-focus', 'role_in_group':'primary',
        'candidate_kind':'substantive_publication', 'title':title, 'source':venue,
        'date':published, 'doi':doi.removeprefix('https://doi.org/'),
        'url':link, 'curator_note':'Relevance focus: '+match['match_reason'],
    }
    return canonical, match['score'], candidate


def discover(path: Path, max_seconds=FOCUSED_DISCOVERY_SECONDS, max_candidates=110,
             *, session=None, clock=None, pause=None):
    """Sustained focused search, not an optional two-minute preflight.

    `max_seconds` bounds the research-discovery period, NOT validation, admission,
    rebuilding the corpus, workbook generation or the GitHub job.  Empty candidate
    sets do not terminate discovery.  If all providers fail, fail visibly rather
    than reporting a green two-minute scan or idling to disguise the problem.
    """
    import requests  # no network dependency for backfill-only
    if session is None:
        session = requests.Session()
    session.headers.update({'User-Agent':'EU-RI-Relevance-Scanner/2.0 (public research discovery)'})
    clock = clock or time.monotonic
    pause = pause or time.sleep
    max_seconds = float(max_seconds)
    if max_seconds <= 0:
        raise ValueError('Focused discovery duration must be positive')
    now = datetime.now(timezone.utc)
    slot = int(now.timestamp() // (4*3600))
    api_key = clean(os.environ.get('OPENALEX_API_KEY'))
    crossref_mailto = clean(os.environ.get('CROSSREF_MAILTO'))
    known = {clean(x.get('link') or x.get('url')).lower().rstrip('/')
             for area in ('strand_a','strand_b','strand_c')
             for x in load('radar.json',{}).get(area,[])}
    known.update(clean(x.get('url')).lower().rstrip('/')
                 for x in load('historical/historical.json',{}).get('items',[]))
    picked = {}
    per_bucket = {}
    stats = Counter()
    blocked = set()
    cooldown_until = {'openalex': 0.0, 'crossref': 0.0}
    failures = {'openalex': 0, 'crossref': 0}
    start = clock()
    deadline = start + max_seconds
    last_progress = start
    # Iterable covers far more distinct queries/pages than one 25-minute window
    # can consume. Rotate region/issue focus and never reuse a completed search.
    plan = iter(focused_search_plan(slot))
    successful_requests = 0
    while (remaining := deadline - clock()) > 0:
        if len(blocked) == 2:
            raise RuntimeError('Both focused discovery providers unavailable: '+str(dict(stats)))
        try:
            bucket, query, provider, page = next(plan)
        except StopIteration:
            raise RuntimeError('All focused searches exhausted before 25-minute window')
        if provider in blocked:
            continue
        now_mono = clock()
        if now_mono < cooldown_until[provider]:
            # Do not spin past hundreds of distinct queries while both services
            # are in a 429 cooldown. Back off before the next attempt.
            pause(min(5.0, cooldown_until[provider] - now_mono,
                      max(0.0, deadline - now_mono)))
            continue
        remaining = deadline - now_mono
        if remaining <= 0:
            break
        # Every attempt has a bounded deadline so no one HTTP call extends the
        # discovery window into the downstream processing time.
        timeout = min(12.0, max(0.25, remaining - 0.2))
        try:
            if provider == 'openalex':
                params = {
                    'search':query,
                    'filter':'from_publication_date:2024-01-01,to_publication_date:'+now.date().isoformat(),
                    'per-page':25, 'page':page,
                    'select':'id,display_name,doi,publication_date,primary_location,abstract_inverted_index',
                }
                if api_key: params['api_key'] = api_key
                resp = session.get('https://api.openalex.org/works', params=params, timeout=timeout)
            else:
                params = {
                    'query.bibliographic':query, 'rows':20, 'offset':(page-1)*20,
                    'filter':'from-pub-date:2024-01-01,until-pub-date:'+now.date().isoformat(),
                    'select':'DOI,title,published,published-online,published-print,created,container-title,abstract,URL',
                }
                if crossref_mailto: params['mailto'] = crossref_mailto
                resp = session.get('https://api.crossref.org/works', params=params, timeout=timeout)
            stats['requests'] += 1
            if resp.status_code in (401, 403):
                stats[provider+'_auth_or_access_error'] += 1
                blocked.add(provider)
                print('Focused search provider denied access:',provider,resp.status_code,flush=True)
                continue
            if resp.status_code == 429:
                stats[provider+'_rate_limited'] += 1
                # Switch providers for now; retry this one at a controlled pace.
                cooldown_until[provider] = clock() + 90
                failures[provider] += 1
                if failures[provider] >= 6:
                    blocked.add(provider)
                continue
            if not resp.ok:
                stats[provider+'_http_error'] += 1
                failures[provider] += 1
                if failures[provider] >= 6:
                    blocked.add(provider)
                continue
            results = (resp.json().get('results',[]) if provider=='openalex'
                       else resp.json().get('message',{}).get('items',[]))
            successful_requests += 1
            stats[provider+'_queries_completed'] += 1
            failures[provider] = 0
            if not results:
                stats['empty_results'] += 1
            for work in results:
                if not isinstance(work, dict):
                    stats['malformed_work'] += 1
                    continue
                try:
                    rec = relevance_work(provider, work)
                except (ValueError, TypeError, AttributeError):
                    stats['malformed_work'] += 1
                    continue
                if rec is None:
                    continue
                canonical, score, candidate = rec
                if canonical in picked or candidate['url'].lower().rstrip('/') in known:
                    continue
                picked[canonical] = (score, bucket, candidate)
                per_bucket[bucket] = per_bucket.get(bucket, 0) + 1
                stats['candidate_matches'] += 1
        except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as exc:
            stats[provider+'_network_or_payload_error'] += 1
            failures[provider] += 1
            if failures[provider] >= 6:
                blocked.add(provider)
            print('Focused search retryable error:',provider,type(exc).__name__,flush=True)
        if clock()-last_progress >= 60:
            print(f'Focused discovery +{clock()-start:.0f}s / {max_seconds:.0f}s: '
                  f'{successful_requests} successful queries, {len(picked)} relevance candidates',flush=True)
            last_progress = clock()
        # Per-request pacing is part of live discovery; it protects external APIs.
        if deadline-clock() > 0:
            pause(min(FOCUSED_REQUEST_PACING_SECONDS, deadline-clock()))
    if not successful_requests:
        raise RuntimeError('No successful focused discovery queries; no 25-minute scan can be claimed')
    # Do not let China/US-heavy source volume crowd out countries/regions with
    # smaller publishing systems; take best scores in interleaved geography buckets.
    buckets = {}
    for score, bucket, row in picked.values():
        buckets.setdefault(bucket,[]).append((score,row))
    for bucket in buckets:
        buckets[bucket].sort(key=lambda pair: -pair[0])
    candidates=[]
    while len(candidates) < max_candidates and any(buckets.values()):
        for bucket in list(buckets):
            if buckets[bucket] and len(candidates) < max_candidates:
                candidates.append(buckets[bucket].pop(0)[1])
    stats['seconds_spent_discovering'] = round(clock()-start,2)
    stats['successful_requests'] = successful_requests
    stats['coverage_buckets'] = len(per_bucket)
    out={'profile_version':'v2-relevance-sustained-25m',
         'batch_id':'relevance-'+now.strftime('%Y%m%dT%H%M%SZ'),
         'source_document':'OpenAlex and Crossref focused literature discovery; candidate metadata only',
         'compiled_at':datetime.now(timezone.utc).isoformat(),
         'policy':{'admission':'Normal Radar A/B/C source and relevance gates are mandatory; no automatic admission',
                   'discovery_seconds_target':max_seconds,
                   'processing_after_discovery':True},
         'candidates':candidates,'work_count':len(candidates),
         'discovery_stats':dict(stats)}
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
    print('Focused discovery complete:',len(candidates),'new candidates;',dict(stats),'->',path,flush=True)


def scan(candidate_path: Path):
    """Admit the *already discovered* batch; do not launch a second discovery scan.

    The Main Radar engine has no native candidate-only CLI. In this dedicated
    process, its broad-source collectors are replaced with empty collection
    results, while exact DOI/title resolution and all ordinary admission,
    duplicate, selection and publication logic remain the Main Radar's own.
    No change is made to scan_radar.py or to the normal scanner's workflows.
    """
    if not candidate_path.is_file():
        raise FileNotFoundError(f'Missing focused candidate file: {candidate_path}')
    batch = json.loads(candidate_path.read_text(encoding='utf8'))
    if not isinstance(batch, dict) or not isinstance(batch.get('candidates'), list):
        raise ValueError('Invalid relevance candidate batch; refusing broad Radar fallback')
    candidates = batch['candidates']
    if not candidates:
        print('Focused discovery returned no novel candidates; admission stage skipped (no second scan).', flush=True)
        return 0
    if any(not isinstance(row, dict) or not clean(row.get('title')) for row in candidates):
        raise ValueError('Invalid relevance candidate entry')

    os.environ['RADAR_PRIORITY_SCAN'] = 'true'
    os.environ['RADAR_CURATOR_CANDIDATE_INPUTS'] = str(candidate_path.resolve())
    # 15 minutes is an UPPER LIMIT for candidate checking + publication, not a
    # required scan duration. The discovery phase already ran for 1500 seconds.
    os.environ['RADAR_SCAN_BUDGET_SECONDS'] = '900'
    os.environ['RADAR_RESCUE_MODE'] = 'false'
    import scan_radar

    # Reuse the exact existing source-derived tests and strict A/B/C admission.
    # Allocate nearly all available work time to this batch, rather than other
    # sources, and leave some time for corpus reconciliation and serialization.
    cfg = scan_radar.CONFIG
    cfg['curator_candidate_testing_enabled'] = True
    cfg['curator_candidate_tests_per_scan'] = len(candidates)
    cfg['curator_candidate_testing_stage_seconds'] = 750
    cfg['network_reserve_seconds'] = 25
    cfg['scan_finalize_reserve_seconds'] = 35

    # No recall, secondary discovery, news rescue, Matrix expansion or journal
    # rotation. These belong to ordinary Radar runs, which remain unaffected.
    for flag in (
        'priority_people_enabled', 'foresight_author_followup_enabled',
        'quiet_scan_rescue_enabled', 'citation_snowball_enabled',
        'source_failure_reallocation_enabled', 'legacy_a_recall_recovery_enabled',
        'low_yield_fresh_rotation_enabled', 'low_yield_extended_fallback_enabled',
        'low_yield_full_rescue_run_enabled', 'full_budget_continuation_enabled',
        'weak_signal_evidence_followup_enabled', 'c_floor_rescue_enabled',
        'c_floor_final_reserve_enabled', 'frontier_stubborn_recovery_enabled',
        'journal_depth_enabled', 'crossref_full_source_census_each_scan',
        'institution_full_census_each_scan', 'direct_top_journal_enabled',
    ):
        cfg[flag] = False
    cfg['frontier_gap_deepening_max_waves'] = 0
    cfg['frontier_gap_deepening_max_waves_no_empty'] = 0
    cfg['low_yield_reserved_seconds'] = 0
    cfg['c_min_new_per_successful_scan'] = 0

    # Critical isolation: the Radar main pipeline otherwise ALWAYS starts broad
    # collection even with the priority flag set. Stub just those collectors in
    # memory, so final admissibility, cumulative deduplication and serialization
    # still use unmodified Radar code. Never monkeypatch the actual exact-record
    # resolver or its Crossref/OpenAlex gates.
    blocked_calls = Counter()

    def no_general_discovery(*args, **kwargs):
        blocked_calls['broad_collector_invocations_skipped'] += 1
        return []

    def no_general_journal_discovery(*args, **kwargs):
        blocked_calls['broad_journal_invocations_skipped'] += 1
        return [], []

    broad_collectors = (
        'collect_news', 'collect_openalex', 'collect_crossref',
        'collect_institutions', 'collect_must_not_miss_primary_evidence',
        'collect_eurlex_cellar', 'collect_europarl_adopted_texts',
        'collect_crossref_prefix_sources', 'collect_priority_news_references',
        'collect_priority_people', 'collect_rule_fix_source_recovery',
        'collect_manual_recovery', 'collect_weak_signal_evidence_followups',
    )
    # Fail loudly if the upstream Radar API changes. Silently failing to stub a
    # renamed collector would bring back a second broad scanning phase.
    for name in broad_collectors + ('collect_direct_top_journals',):
        if not callable(getattr(scan_radar, name, None)):
            raise RuntimeError(f'Candidate-only isolation needs updated Radar adapter: {name}')
    for name in broad_collectors:
        setattr(scan_radar, name, no_general_discovery)
    scan_radar.collect_direct_top_journals = no_general_journal_discovery

    print(f'Relevance ADMISSION-ONLY: {len(candidates)} exact candidates; '
          'no broad Radar discovery; candidate processing budget up to 900s '
          '(not a second 25-minute scan).', flush=True)
    result = scan_radar.main()
    print('Relevance admission complete; extra discovery collectors blocked:',
          dict(blocked_calls), flush=True)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['discover','scan','export-json'])
    p.add_argument('--output',type=Path,default=Path(os.getenv('RUNNER_TEMP','/tmp'))/'relevance_candidates.json')
    p.add_argument('--candidates',type=Path,default=Path(os.getenv('RUNNER_TEMP','/tmp'))/'relevance_candidates.json')
    p.add_argument('--max-seconds',type=int,default=FOCUSED_DISCOVERY_SECONDS)
    args=p.parse_args()
    if args.command=='discover': discover(args.output,max_seconds=args.max_seconds)
    elif args.command=='scan': return scan(args.candidates)
    else:
        data=compile_records();args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
        print('Relevance workbook:',len(data['verified']),'verified and retained,',len(data['pending']),'for review',flush=True)
    return 0


if __name__=='__main__':sys.exit(main())
