#!/usr/bin/env python3
"""Independent, bounded institutional discovery: feeds, hubs, sitemaps and search RSS.

Produces a private discovery queue, NOT authoritative radar admissions. Standard library
networking; existing repo requirements supply BeautifulSoup and feedparser.
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import re
import time
import urllib.parse as up
import urllib.request as ur
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = 'RI-Radar-AlternateDiscovery/1.0 (research publication indexing)'
HUBS = ('/en/publications/', '/en/publications-and-studies/', '/publications/', '/publikationen/', '/en/studies/', '/publications-and-resources/', '/en/research/', '/en/news/', '/en/publications-and-resources/')
HINTS = ('policy','brief','report','study','studie','publication','paper','research','analysis','digital','technology','innovation','sovereign','europe','2026','pdf')
FOCUS = ('europe','european','eu ','digital','sovereign','research','innovation','technology','science','strategic','security','competitiveness','ai ','artificial intelligence','industrial','quantum','semiconductor','geopolitic','infrastructure','survey')


def normalize(url):
    try:
        p = up.urlsplit(url.strip())
        if p.scheme not in ('http','https') or not p.hostname: return ''
        host = (p.hostname or '').lower().removeprefix('www.')
        path = re.sub('/+', '/', up.unquote(p.path or '/')).rstrip('/') or '/'
        # Drop query trackers, retain potentially content-bearing ids.
        qs = up.parse_qsl(p.query, keep_blank_values=False)
        qs = [(k,v) for k,v in qs if not (k.lower().startswith('utm_') or k.lower() in ('fbclid','gclid','ref','source'))]
        return up.urlunsplit(('https',host,up.quote(path, safe='/%:@+~!$&\'()*;,='),up.urlencode(sorted(qs)),''))
    except Exception: return ''


def load(path, default):
    if not path.exists(): return default
    return json.loads(path.read_text(encoding='utf-8'))


def existing_keys(corpus, queue):
    out = set()
    for arr in [corpus.get(k,[]) for k in ('strand_a','strand_b','strand_c','ab_archive','signal_archive')] + [queue.get('candidates',[])]:
        for x in arr if isinstance(arr,list) else []:
            if not isinstance(x,dict): continue
            for f in ('link','url','pdf_url'):
                if x.get(f): out.add('url:'+normalize(str(x[f])))
            title = re.sub(r'\W+', ' ',str(x.get('title','')).lower()).strip()
            if title:out.add('title:'+title)
    return out


def fetch(url, deadline, size=1300000):
    if time.monotonic() >= deadline: return '', '', ''
    req=ur.Request(url, headers={'User-Agent':USER_AGENT,'Accept':'text/html, application/xml, application/rss+xml, application/atom+xml, */*'})
    try:
        with ur.urlopen(req,timeout=min(9,max(1,deadline-time.monotonic()))) as r:
            final=r.geturl(); typ=r.headers.get('Content-Type','')
            raw=r.read(size)
            if 'pdf' in typ.lower() or raw.startswith(b'%PDF'): return '',final,'pdf'
            return raw.decode('utf-8',errors='replace'),final,typ.lower()
    except Exception: return '','',''


def extract_links(body, base, typ):
    if not body:return []
    links=[]
    if 'xml' in typ or 'rss' in typ or 'atom' in typ or body.lstrip().startswith('<?xml'):
        soup=BeautifulSoup(body,'xml')
        for e in soup.find_all(['item','entry']):
            a=e.find('link'); u=(a.get('href') or a.get_text(' ',strip=True)) if a else ''
            title=e.find('title')
            if u: links.append((u,title.get_text(' ',strip=True) if title else ''))
        for x in soup.find_all(['loc','link']):
            target=(x.get('href') or x.get_text(' ',strip=True)).strip()
            if target.startswith('http'):links.append((target,''))
    else:
        soup=BeautifulSoup(body,'html.parser')
        for a in soup.select('a[href]'):
            u=up.urljoin(base,a.get('href',''))
            title=a.get_text(' ',strip=True) or a.get('title','') or ''
            links.append((u,title))
    return links


def relevance(title, url):
    text=(title+' '+up.unquote(up.urlsplit(url).path)).lower().replace('-',' ').replace('_',' ')
    n=sum(bool(re.search(r'(?<!\w)'+re.escape(word.strip())+r'(?!\w)',text)) for word in FOCUS)
    doc=any(w in text for w in HINTS)
    return n + (1 if doc else 0) + (1 if url.lower().split('?')[0].endswith('.pdf') else 0)


def domain_match(url, domain):
    try: h=(up.urlsplit(url).hostname or '').lower(); return h==domain or h.endswith('.'+domain)
    except Exception:return False


def source_scan(source, deadline, per_source):
    domain=source['domain']; name=source.get('name',domain)
    root='https://'+domain
    routes=[root+'/robots.txt',root+'/sitemap.xml',root+'/sitemap_index.xml',root+'/feed',root+'/rss',root+'/en/rss',root+'/en/publications',root+'/en/publications/',root+'/fileadmin/',root]
    routes += [root+p for p in HUBS]
    if 'bertelsmann-stiftung.de' in domain:
        routes = [root+'/en/our-projects/eupinions/',root+'/en/publications/',root+'/fileadmin/files/Projekte/eupinions/',*routes]
    # Public search index is a complementary path, not the only discovery method.
    routes += ['https://www.google.com/search?'+up.urlencode({'q':f'site:{domain} filetype:pdf (2026 OR 2025) report policy brief'}),
               'https://www.google.com/search?'+up.urlencode({'q':f'site:{domain} publications research innovation europe'})]
    seen=set(); found={}; scanned=0; sitemap_children=[]; hub_children=[]; errors=0
    for route in routes:
        if time.monotonic()>=deadline or scanned>=34: break
        url=normalize(route)
        if not url or url in seen:continue
        seen.add(url); body,final,typ=fetch(route,deadline); scanned+=1
        if not body: errors+=1;continue
        if route.endswith('robots.txt'):
            for s in re.findall(r'(?im)^sitemap:\s*(\S+)',body):sitemap_children.append(s)
            continue
        for link,title in extract_links(body, final or route,typ):
            link=normalize(link)
            if not link or not domain_match(link,domain):continue
            if link.endswith('.xml') or 'sitemap' in link.lower():
                if len(sitemap_children)<12:sitemap_children.append(link)
                continue
            score=relevance(title,link)
            if (score>=2 and not link.lower().endswith('.pdf') and len(hub_children)<12
                    and any(w in link.lower() for w in ('publication','publikation','studie','studies','project','eupinions'))):
                hub_children.append(link)
            if score < 2:continue
            if link not in found or score>found[link]['discovery_score']:
                found[link]={'title':re.sub(r'\s+',' ',title).strip()[:250] or up.unquote(up.urlsplit(link).path.rsplit('/',1)[-1])[:250],
                    'link':link,'source':name,'source_domain':domain,'discovery_score':score,'discovery_path':'institutional_alternate_paths','discovered_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    # Follow selected publication/project pages one hop beyond the homepage/hub.
    for route in list(dict.fromkeys(hub_children))[:8]:
        if time.monotonic()>=deadline or route in seen:break
        seen.add(route);body,final,typ=fetch(route,deadline);scanned+=1
        for link,title in extract_links(body,final or route,typ):
            link=normalize(link)
            if not link or not domain_match(link,domain):continue
            score=relevance(title,link)
            if score<2:continue
            found.setdefault(link,{'title':title[:250] or up.unquote(up.urlsplit(link).path.rsplit('/',1)[-1])[:250],
                    'link':link,'source':name,'source_domain':domain,'discovery_score':score,'discovery_path':'hub_second_hop','discovered_at':dt.datetime.now(dt.timezone.utc).isoformat()})
    # Sitemaps are often huge; bound the XML parse and total work.
    for route in list(dict.fromkeys(sitemap_children))[:8]:
        if time.monotonic()>=deadline:break
        body,final,typ=fetch(route,deadline,size=2400000);scanned+=1
        if not body:continue
        for link,title in extract_links(body,final or route,'application/xml'):
            link=normalize(link)
            if not link or not domain_match(link,domain):continue
            score=relevance(title,link)
            if score<2:continue
            found.setdefault(link,{'title':title[:250] or up.unquote(up.urlsplit(link).path.rsplit('/',1)[-1])[:250],
                    'link':link,'source':name,'source_domain':domain,'discovery_score':score,'discovery_path':'sitemap_alternate','discovered_at':dt.datetime.now(dt.timezone.utc).isoformat()})
    ranked=sorted(found.values(),key=lambda x:(-x['discovery_score'],x['link']))[:per_source]
    return ranked,{'source':name,'routes_attempted':scanned,'failed_or_empty_routes':errors,'candidates':len(found)}


def run(args):
    config=load(ROOT/'radar_config.json',{})
    sources=[s for s in config.get('institution_sources',[]) if isinstance(s,dict) and s.get('domain')]
    queue_path=Path(args.queue);state_path=Path(args.state)
    queue=load(queue_path,{'version':1,'profile':'alternate-discovery-private-v1','candidates':[]})
    state=load(state_path,{'version':1,'cursor':0})
    corpus=load(Path(args.corpus),{})
    if not sources:raise SystemExit('No institution_sources configured')
    seeds=[s for s in sources if 'bertelsmann' in s['domain']]
    other=[s for s in sources if s not in seeds]
    offset=int(state.get('cursor',0))%max(len(other),1)
    selected=(seeds+ (other[offset:]+other[:offset])[:max(0,args.sources-len(seeds))])[:args.sources]
    started=time.monotonic()
    minimum_end=started+args.min_seconds
    deadline=started+args.max_seconds
    existing=existing_keys(corpus,queue)
    additions=[]; stats=[]
    batches=0
    # Continue actual discovery across rotating institutions until the minimum runtime.
    # Keep every request bound by the 16-minute hard deadline.
    while time.monotonic()<minimum_end and time.monotonic()<deadline:
        batch=(seeds+(other[offset:]+other[:offset])[:max(0,args.sources-len(seeds))])[:args.sources]
        with cf.ThreadPoolExecutor(max_workers=min(args.workers,len(batch))) as executor:
            futures=[executor.submit(source_scan,s,deadline,args.per_source) for s in batch]
            for future in cf.as_completed(futures):
                try: rows,stat=future.result()
                except Exception as exc:
                    stats.append({'error':str(exc)[:300]});continue
                stats.append(stat)
                for row in rows:
                    key='url:'+normalize(row['link'])
                    title='title:'+re.sub(r'\W+',' ',row['title'].lower()).strip()
                    if key in existing or (len(row['title'])>=18 and title in existing):continue
                    existing.add(key);existing.add(title);row['review_status']='unreviewed';additions.append(row)
        batches+=1
        offset=(offset+max(1,len(batch)-len(seeds)))%max(len(other),1)
        # Do not repeatedly hammer institutions when all routes return quickly.
        if time.monotonic()<minimum_end:
            time.sleep(min(20, max(0,minimum_end-time.monotonic())))
    queue['version']=1;queue['profile']='alternate-discovery-private-v1';queue['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat()
    queue['candidates']=(queue.get('candidates',[])+additions)[-args.queue_limit:]
    state['version']=1;state['cursor']=offset
    state['last_scan_at']=queue['updated_at'];state['last_scan_sources']=[x['domain'] for x in selected]
    state['last_scan_new']=len(additions);state['last_scan_diagnostics']=stats;state['last_scan_batches']=batches
    if not args.dry_run:
        queue_path.parent.mkdir(parents=True,exist_ok=True);state_path.parent.mkdir(parents=True,exist_ok=True)
        for path,body in ((queue_path,queue),(state_path,state)):
            tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(body,indent=2,ensure_ascii=False)+'\n');tmp.replace(path)
    print(json.dumps({'sources_per_batch':len(selected),'batches':batches,'new_private_candidates':len(additions),'private_queue_total':len(queue['candidates']),'elapsed_seconds':round(time.monotonic()-started,1),'dry_run':args.dry_run,'sample_new':additions[:5]},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--min-seconds',type=int,default=840)
    p.add_argument('--max-seconds',type=int,default=960)
    p.add_argument('--sources',type=int,default=18)
    p.add_argument('--per-source',type=int,default=45)
    p.add_argument('--workers',type=int,default=5)
    p.add_argument('--queue-limit',type=int,default=3000)
    p.add_argument('--queue',default=str(ROOT/'alternate_discovery_candidates.json'))
    p.add_argument('--state',default=str(ROOT/'alternate_discovery_state.json'))
    p.add_argument('--corpus',default=str(ROOT/'radar.json'))
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args()
    if not 1<=a.min_seconds<=a.max_seconds<=960 or a.sources<1 or a.workers<1: p.error('invalid limits')
    run(a)
