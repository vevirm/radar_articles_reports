#!/usr/bin/env python3
"""Independent, preview-only PDF hunter for known R&I publishers.

Never writes to radar.json, candidate intake or reasoning files.
"""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import io
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'research-and-innovation.ec.europa.eu':'European Commission R&I',
    'joint-research-centre.ec.europa.eu':'JRC',
    'publications.jrc.ec.europa.eu':'JRC Publications',
    'oecd.org':'OECD',
    'eib.org':'European Investment Bank',
    'eic.ec.europa.eu':'European Innovation Council',
    'fraunhofer.de':'Fraunhofer',
    'isi.fraunhofer.de':'Fraunhofer ISI',
    'vttresearch.com':'VTT',
    'scienceeurope.org':'Science Europe',
    'bruegel.org':'Bruegel',
    'ceps.eu':'CEPS',
    'bertelsmann-stiftung.de':'Bertelsmann Stiftung',
    'eua.eu':'European University Association',
    'ec.europa.eu':'European Commission',
    'op.europa.eu':'EU Publications Office',
}
ANCHORS = ('research','innovation','science','technology','technological','digital','industrial','competitiveness','semiconductor','quantum','artificial intelligence','r&d','university','universities','infrastructure','knowledge','scientific')
EU = ('europe','european','eu ','union','member state','horizon europe','framework programme','european commission')
REJECT = ('invitation to tender','call for tender','vacancy','job opportunity','annual accounts','financial statements','procurement notice','privacy policy','terms of use','event invitation','webinar registration','newsletter subscribe')
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; RIRadarPDFHunter/1.0; publication discovery)', 'Accept':'application/pdf,application/xml,text/xml,*/*'}

def normal(url):
    p=urllib.parse.urlsplit(url.strip())
    if p.scheme not in ('http','https') or not p.hostname:return ''
    return urllib.parse.urlunsplit(('https',p.hostname.lower().removeprefix('www.'),p.path.rstrip('/'),'', ''))

def known_links(path):
    result=set()
    if not path.exists():return result
    try:data=json.loads(path.read_text())
    except Exception:return result
    def visit(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k in ('link','url','pdf_url') and isinstance(v,str):result.add(normal(v))
                else:visit(v)
        elif isinstance(x,list):
            for y in x:visit(y)
    visit(data)
    return result

def allowed(url,domain):
    host=urllib.parse.urlsplit(url).hostname or ''
    return host==domain or host.endswith('.'+domain)

def request(url,timeout=10,max_bytes=4500000):
    req=urllib.request.Request(url,headers=HEADERS)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            return r.read(max_bytes),r.headers.get('Content-Type',''),r.geturl()
    except Exception:return b'','',url

def extract_pdf(b):
    try:
        import fitz
        pdf=fitz.open(stream=b,filetype='pdf')
        if not 2<=len(pdf)<=500:return None
        text=' '.join(p.get_text(sort=True) for p in list(pdf)[:min(5,len(pdf))])
        text=re.sub(r'\s+',' ',text).strip()
        meta=pdf.metadata or {}
        return (text,meta.get('title',''),len(pdf)) if len(text)>=900 else None
    except Exception:return None

def score(text,title,url):
    excerpt=(title+' '+text[:11000]).lower()
    if any(word in excerpt[:1500] for word in REJECT):return -1
    topical=sum(bool(re.search(r'(?<!\w)'+re.escape(word)+r'(?!\w)',excerpt)) for word in ANCHORS)
    europe=sum(bool(re.search(r'(?<!\w)'+re.escape(word)+r'(?!\w)',excerpt)) for word in EU)
    if topical<2 or europe<1:return -1
    return topical*2+min(europe,3)+min(len(text)//2500,3)

def sitemap_urls(domain,deadline,max_urls=400):
    from collections import deque
    q=deque([f'https://{domain}/sitemap.xml', f'https://{domain}/sitemap_index.xml'])
    seen=set(); results=[]
    while q and len(seen)<12 and len(results)<max_urls and time.monotonic()<deadline:
        url=q.popleft()
        if url in seen:continue
        seen.add(url)
        b,typ,_=request(url,timeout=7,max_bytes=1400000)
        if not b:continue
        try:root=ET.fromstring(b)
        except ET.ParseError:continue
        locs=[e.text.strip() for e in root.iter() if e.tag.endswith('loc') and e.text]
        for loc in locs:
            if not allowed(loc,domain):continue
            if loc.lower().endswith('.xml') and len(seen)+len(q)<12:q.append(loc)
            elif '.pdf' in urllib.parse.urlsplit(loc).path.lower():results.append(loc)
    return results

def search_urls(domain,year,deadline):
    # Search-engine RSS is an optional discovery lane; no reliance on it for verification.
    q=f'site:{domain} filetype:pdf ("research" OR "innovation" OR "technology") {year}'
    url='https://www.bing.com/search?'+urllib.parse.urlencode({'q':q,'format':'rss','count':'50'})
    b,_,_=request(url,timeout=8,max_bytes=300000)
    if not b:return []
    try:
        root=ET.fromstring(b)
        return [node.text.strip() for node in root.findall('.//item/link') if node.text and allowed(node.text.strip(),domain) and '.pdf' in urllib.parse.urlsplit(node.text).path.lower()]
    except ET.ParseError:return []

def run(args):
    start=time.monotonic(); deadline=start+args.max_seconds; min_end=start+args.min_seconds
    known=known_links(ROOT/'radar.json')
    preview={}; rejected={'non_pdf':0,'invalid_pdf':0,'irrelevant':0,'known':0,'error':0}; seen=set()
    statepath=ROOT/'pdf_hunter_state.json'
    try:state=json.loads(statepath.read_text()) if statepath.exists() else {}
    except Exception:state={}
    sources=list(SOURCES)
    cursor=state.get('cursor',0)%len(sources)
    # Rotate sources, not unbounded web crawling. Continue focused passes for minimum runtime.
    pass_id=0
    while time.monotonic()<deadline-12:
        domain=sources[(cursor+pass_id)%len(sources)]
        year=dt.datetime.now(dt.timezone.utc).year
        urls=sitemap_urls(domain,deadline,max_urls=500)+search_urls(domain,year,deadline)+search_urls(domain,year-1,deadline)
        for url in urls:
            if time.monotonic()>deadline-12:break
            url=normal(url)
            if not url or url in seen:continue
            seen.add(url)
            if url in known:
                rejected['known']+=1;continue
            if not url.lower().endswith('.pdf'):
                rejected['non_pdf']+=1;continue
            b,ctype,final=request(url,timeout=12,max_bytes=args.pdf_max_bytes)
            if not b.startswith(b'%PDF'):
                rejected['invalid_pdf']+=1;continue
            doc=extract_pdf(b)
            if not doc:
                rejected['invalid_pdf']+=1;continue
            text,title,pages=doc
            title=(title or '').strip()
            if not title or len(title)>220 or title.lower() in ('untitled','document','microsoft word'):
                title=' '.join(text[:160].split())[:140]
            quality=score(text,title,url)
            if quality<0:
                rejected['irrelevant']+=1;continue
            candidate={'title':title,'link':final,'source':SOURCES[domain], 'source_domain':domain,'type':'verified_pdf', 'page_count':pages,'score':quality,'excerpt':text[:800], 'sha256':hashlib.sha256(b).hexdigest()}
            preview[candidate['sha256']]=candidate
        pass_id+=1
        if time.monotonic()>=min_end:break
        # If all sources have been swept, delay before retrying: no busy looping.
        if pass_id%len(sources)==0:time.sleep(min(20,max(0,min_end-time.monotonic())))
    results=sorted(preview.values(),key=lambda c:c['score'],reverse=True)[:args.max_results]
    output={'mode':'preview_only_no_radar_writes','generated_at':dt.datetime.now(dt.timezone.utc).isoformat(), 'discovered_pdf_count':len(preview),'selected_count':len(results), 'rejected':rejected,'candidates':results,'elapsed_seconds':round(time.monotonic()-start,1)}
    (ROOT/'ri_pdf_hunter_preview.json').write_text(json.dumps(output,indent=2,ensure_ascii=False))
    statepath.write_text(json.dumps({'cursor':(cursor+pass_id)%len(sources),'last_run':output['generated_at']},indent=2))
    print(json.dumps({'selected':len(results),'verified_unique':len(preview),'rejected':rejected,'elapsed_seconds':output['elapsed_seconds']}))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--min-seconds',type=int,default=840)
    p.add_argument('--max-seconds',type=int,default=960)
    p.add_argument('--max-results',type=int,default=10)
    p.add_argument('--pdf-max-bytes',type=int,default=6500000)
    args=p.parse_args()
    if not 0<=args.min_seconds<=args.max_seconds: p.error('invalid duration')
    run(args)
