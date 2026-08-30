#!/usr/bin/env python3
"""Historical 2023–2025 top-tier scanner aligned with the live radar recall engine.

Operational isolation is strict: this script reads/writes only historical/config.json and
historical/historical.json. It does not import radar.json, mutate the live matrix, weak
signals, live cursors, or dispatch the live workflow.

The historical mission differs only in scope: 2023–2025, elite sources, stricter merit,
topic rotation (not year rotation), and a modest 2025 > 2024 > 2023 ranking preference.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import html
import io
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
HIST_DIR = ROOT / "historical"
CONFIG_PATH = HIST_DIR / "config.json"
OUT_PATH = HIST_DIR / "historical.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

DATE_FROM = dt.date.fromisoformat(CONFIG["date_from"])
DATE_TO = dt.date.fromisoformat(CONFIG["date_to"])
MIN_SCORE = int(CONFIG.get("minimum_admission_score", 93))
MAX_ITEMS = int(CONFIG.get("max_items", 350))
BUDGET_SECONDS = int(os.environ.get("HISTORICAL_SCAN_BUDGET_SECONDS", "1050"))
REQUEST_TIMEOUT = int(os.environ.get("HISTORICAL_REQUEST_TIMEOUT", "12"))
STARTED_MONO = time.monotonic()
DEADLINE = STARTED_MONO + max(120, BUDGET_SECONDS)
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()
RESCUE_MODE = os.environ.get("HISTORICAL_RESCUE_MODE", "").strip().lower() in {"1", "true", "yes", "on"}

UA = "RI-Geopolitics-Historical/2.0 (+https://vevirm.github.io/radar_articles_reports/historical/)"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": UA,
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/pdf,application/xml;q=0.9,*/*;q=0.8",
})

DIAG: collections.Counter[str] = collections.Counter()

EU_RE = re.compile(r"\b(EU|European Union|Europe|European|Horizon Europe|ERC|EIC|JRC|European Commission|European Parliament|Council of the EU)\b", re.I)
RI_RE = re.compile(
    r"\b(research|researcher|researchers|science|scientific|innovation|technology|technological|R&D|R&I|university|universities|"
    r"laborator(?:y|ies)|infrastructure|compute|computing|semiconductor|chip|chips|AI|artificial intelligence|quantum|data|"
    r"talent|skills|doctoral|patent|venture capital|scale-up|startup|industrial|manufacturing|foresight|future studies)\b", re.I)
STRATEGIC_RE = re.compile(
    r"\b(geopolit|strategic autonom|sovereign|sovereignty|dependen|reliance|security|economic security|research security|"
    r"knowledge security|competit|resilien|de-risk|derisk|China|Chinese|United States|US\b|American|Russia|export control|"
    r"sanction|dual-use|dual use|critical technolog|critical raw material|supply chain|standard|standards|regulation|"
    r"industrial policy|technology transfer|investment screening|science diplomacy|international cooperation|fragmentation|chokepoint)\b", re.I)
BAD_DOC_RE = re.compile(
    r"\b(call for proposals|call for tender|job vacancy|vacancies|event|webinar|conference registration|newsletter|press release|"
    r"speech|remarks|podcast|video|interview|award ceremony|grant results|funding opportunity|application deadline)\b", re.I)
ANALYTIC_RE = re.compile(
    r"\b(report|study|paper|analysis|assessment|review|outlook|foresight|forecast|strategy|strategic|policy brief|working paper|"
    r"research article|journal article|evidence|evaluation|impact assessment|communication|recommendation|framework)\b", re.I)

ROW_TERMS = {
    "knowledge": re.compile(r"\b(researcher|researchers|scientist|scientists|talent|skills|university|universities|knowledge|brain drain|brain gain|mobility|research security|science diplomacy|collaboration)\b", re.I),
    "infrastructure": re.compile(r"\b(compute|computing|cloud|data centre|data center|semiconductor|chip|chips|quantum|research infrastructure|facility|facilities|critical raw material|critical mineral|energy|space|satellite|supply chain)\b", re.I),
    "conversion": re.compile(r"\b(firm|firms|company|companies|startup|start-up|scale-up|venture capital|investment|industrial|manufacturing|production|commerciali[sz]|market|patent|technology transfer)\b", re.I),
    "rules": re.compile(r"\b(regulation|regulatory|standard|standards|governance|export control|sanction|screening|law|directive|framework|funding|Horizon Europe|coordination|state aid|procurement)\b", re.I),
}
OUTCOME_TERMS = {
    "A": re.compile(r"\b(build|built|strengthen|strengthened|increase capacity|capacity building|leadership|autonomy|sovereignty|diversif|resilien|attract|retain|scale up|scaled up|common framework|coordination|investment)\b", re.I),
    "B": re.compile(r"\b(cost|trade-off|tradeoff|friction|burden|delay|restrict|screening|safeguard|protection|compliance|fragmentation|slower|barrier)\b", re.I),
    "C": re.compile(r"\b(reliance|dependen|outside|foreign|US|United States|China|Chinese|third countr|external supplier|foreign capital|foreign technology|import|access to)\b", re.I),
    "D": re.compile(r"\b(loss|lost|decline|weaken|shortage|chokepoint|cut off|restriction|brain drain|lag|behind|vulnerab|exposure|hollow|dependency risk|fragmentation|fail to scale)\b", re.I),
}


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()


def log(msg: str) -> None:
    print(f"[historical +{time.monotonic()-STARTED_MONO:6.1f}s] {msg}", flush=True)


def budget_ok(reserve: int = 30) -> bool:
    return time.monotonic() < DEADLINE - reserve


def parse_date(value: Any) -> dt.date | None:
    if not value:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dateparser.parse(str(value), fuzzy=False).date()
    except Exception:
        m = re.search(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", str(value))
        if m:
            try:
                return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return None
    return None


def domain_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def source_for(domain: str = "", venue: str = "", publisher: str = "") -> dict[str, Any] | None:
    d = clean(domain).lower().removeprefix("www.")
    for src in CONFIG.get("elite_sources", []):
        sd = clean(src.get("domain")).lower().removeprefix("www.")
        if d and sd and (d == sd or d.endswith("." + sd)):
            return dict(src)
    text = norm(f"{venue} {publisher}")
    aliases = {
        "european commission": "commission.europa.eu",
        "joint research centre": "joint-research-centre.ec.europa.eu",
        "joint research center": "joint-research-centre.ec.europa.eu",
        "european parliament": "europarl.europa.eu",
        "organisation for economic co operation and development": "oecd.org",
        "organization for economic co operation and development": "oecd.org",
        "oecd": "oecd.org",
        "bruegel": "bruegel.org",
        "centre for european policy studies": "ceps.eu",
        "mercator institute for china studies": "merics.org",
    }
    for alias, target in aliases.items():
        if alias in text:
            for src in CONFIG.get("elite_sources", []):
                if src.get("domain") == target:
                    return dict(src)
    for journal in CONFIG.get("top_journals", []):
        if norm(journal) and norm(journal) in text:
            return {"name": journal, "domain": "", "kind": "top_journal", "authority": 56}
    return None


def year_bonus(d: dt.date) -> int:
    return int(CONFIG.get("year_preference", {}).get(str(d.year), 0))


def topic_matches(text: str) -> list[str]:
    n = norm(text)
    hits: list[str] = []
    for topic in CONFIG.get("topics", []):
        phrases = [norm(x.replace("-", " ")) for x in topic.get("url_terms", [])]
        if any(p and p in n for p in phrases):
            hits.append(str(topic.get("id")))
    return hits[:4]


def topic_label(topic_id: str) -> str:
    for t in CONFIG.get("topics", []):
        if t.get("id") == topic_id:
            return str(t.get("label"))
    return topic_id


def matrix_classification(text: str) -> tuple[str, str, str]:
    row_scores = {k: len(v.findall(text)) for k, v in ROW_TERMS.items()}
    row = max(row_scores, key=row_scores.get) if max(row_scores.values(), default=0) else ""
    outcome_scores = {k: len(v.findall(text)) for k, v in OUTCOME_TERMS.items()}
    outcome = max(outcome_scores, key=outcome_scores.get) if max(outcome_scores.values(), default=0) else ""
    if not row or not outcome:
        return row, outcome, ""
    row_name = {"knowledge":"people and knowledge","infrastructure":"tools and facilities","conversion":"firms and growth","rules":"rules and decisions"}[row]
    col_name = {"A":"stronger European capacity or control","B":"protection or control with costs or friction","C":"gains that still relied on outside actors or inputs","D":"lost ground, weaker capability or continuing exposure"}[outcome]
    return row, outcome, f"The source concerns {row_name} and gives evidence of {col_name}."


def first_sentence(text: str, limit: int = 330) -> str:
    t = clean(re.sub(r"<[^>]+>", " ", text or ""))
    if not t:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", t)
    s = parts[0].strip()
    if len(s) < 80 and len(parts) > 1:
        s = f"{s} {parts[1]}".strip()
    return s[:limit].rstrip(" ,;:-") + ("…" if len(s) > limit else "")


def why_it_matters(row: str, outcome: str) -> str:
    row_phrase = {"knowledge":"Europe's research workforce, skills and know-how","infrastructure":"the tools, facilities and strategic inputs European research depends on","conversion":"Europe's ability to turn research into firms, production and scale","rules":"the rules, funding and coordination that shape European research and innovation"}.get(row, "Europe's research and innovation position")
    outcome_phrase = {"A":"It is useful history for judging whether later policy really built durable European strength.","B":"It is useful history for judging when greater control also created costs, delay or friction.","C":"It is useful history for judging where European gains still depended on outside capital, technology, markets or access.","D":"It is useful history for judging whether the same weakness or exposure is still present now."}.get(outcome, "It is useful history for judging which earlier pressures still matter now.")
    return f"This bears on {row_phrase}. {outcome_phrase}"


def stable_id(title: str, url: str) -> str:
    basis = norm(url) or norm(title)
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def _diag(reason: str, n: int = 1) -> None:
    DIAG[reason] += n


def admit(raw: dict[str, Any], lane: str = "unknown") -> dict[str, Any] | None:
    _diag("raw_records")
    _diag(f"raw_{lane}")
    title = clean(raw.get("title"))
    abstract = clean(raw.get("abstract") or raw.get("summary") or raw.get("body"))
    url = clean(raw.get("url") or raw.get("doi"))
    date = parse_date(raw.get("date"))
    if not title:
        _diag("reject_no_title"); return None
    if date is None:
        _diag("reject_no_date"); return None
    if not (DATE_FROM <= date <= DATE_TO):
        _diag("reject_outside_window"); return None
    profile = source_for(domain_of(url), clean(raw.get("venue")), clean(raw.get("publisher")))
    if not profile:
        _diag("reject_source_not_elite"); return None
    _diag("source_eligible")
    text = clean(f"{title}. {abstract}")
    if abstract and len(abstract.split()) >= 20:
        _diag("enough_text")
    else:
        _diag("insufficient_text")
    if BAD_DOC_RE.search(title) and not ANALYTIC_RE.search(text):
        _diag("reject_document_exclusion"); return None
    official = profile.get("kind") == "official_eu"
    eu_direct = bool(EU_RE.search(text))
    if not official and not eu_direct:
        _diag("reject_no_direct_eu"); return None
    _diag("eu_scope")
    if not RI_RE.search(text):
        _diag("reject_no_ri"); return None
    _diag("ri_scope")
    if not STRATEGIC_RE.search(text):
        _diag("reject_no_strategic_context"); return None
    _diag("strategic_scope")
    if len(text.split()) < 28 and not ANALYTIC_RE.search(text):
        _diag("defer_insufficient_text"); return None
    topics = topic_matches(text)
    if not topics:
        _diag("reject_no_topic_match"); return None
    _diag("topic_match")
    authority = int(profile.get("authority", 0))
    score = authority + (17 if eu_direct else 14) + 10 + 10 + (4 if len(text.split()) >= 80 or ANALYTIC_RE.search(text) else 2) + year_bonus(date)
    score = min(100, score)
    if score < MIN_SCORE:
        _diag("reject_below_merit"); return None
    _diag("gate_passed")
    row, outcome, basis = matrix_classification(text)
    return {
        "id": stable_id(title, url), "title": title, "date": date.isoformat(), "year": date.year,
        "url": url, "authors": clean(raw.get("authors")), "source": clean(profile.get("name")),
        "source_kind": clean(profile.get("kind")), "venue": clean(raw.get("venue")), "publisher": clean(raw.get("publisher")),
        "source_merit_score": score, "source_merit_label": "Historical top tier",
        "topics": topics, "topic_labels": [topic_label(t) for t in topics],
        "reader_point": first_sentence(abstract) or title, "why_it_matters": why_it_matters(row, outcome),
        "matrix_dimension": row, "matrix_outcome": outcome, "matrix_basis": basis,
        "discovery": clean(raw.get("discovery")),
    }


def openalex_abstract(inv: dict[str, list[int]] | None) -> str:
    if not inv: return ""
    positions: list[tuple[int, str]] = []
    for word, ps in inv.items():
        for p in ps or []:
            positions.append((int(p), word))
    return clean(" ".join(w for _, w in sorted(positions)))


def crossref_date(item: dict[str, Any]) -> str:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        part = item.get(key) or {}; dp = part.get("date-parts") if isinstance(part, dict) else None
        if dp and dp[0]:
            bits = list(dp[0]) + [1, 1]
            try: return dt.date(int(bits[0]), int(bits[1]), int(bits[2])).isoformat()
            except Exception: pass
    return ""


def metadata_rescue_priority(title: str, query: str, source: dict[str, Any] | None, published: dt.date | None) -> int:
    text = clean(f"{title} {query}")
    score = 0
    if EU_RE.search(title): score += 8
    if RI_RE.search(title): score += 6
    if STRATEGIC_RE.search(title): score += 6
    if ANALYTIC_RE.search(title): score += 3
    if source:
        score += 5 if source.get("kind") == "official_eu" else 3
    if published: score += year_bonus(published) // 2
    return score


def fetch_text(url: str, timeout: int) -> str:
    if not url or not budget_ok(45): return ""
    try:
        r = SESSION.get(url, timeout=timeout, allow_redirects=True)
        if not r.ok: return ""
    except Exception:
        return ""
    ctype = (r.headers.get("Content-Type") or "").lower()
    if "pdf" in ctype or r.url.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(r.content))
            return clean(" ".join((p.extract_text() or "") for p in reader.pages[:10]))[:14000]
        except Exception:
            return ""
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        for bad in soup(["script", "style", "nav", "footer", "form", "noscript"]): bad.decompose()
        desc_tag = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", property="og:description")
        desc = clean(desc_tag.get("content") if desc_tag else "")
        return clean(f"{desc} {soup.get_text(' ', strip=True)}")[:14000]
    except Exception:
        return ""


def collect_openalex(queries: list[str], warnings: list[str], lane: str = "openalex") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    scan_cap = int(CONFIG.get("openalex_missing_abstract_enrichment_per_scan", 24))
    per_query = int(CONFIG.get("openalex_missing_abstract_enrichment_per_query", 3))
    min_priority = int(CONFIG.get("metadata_rescue_priority_min_score", 10))
    used_rescue = 0
    for q in queries:
        if not budget_ok(90): break
        params = {"search":q,"filter":f"from_publication_date:{DATE_FROM.isoformat()},to_publication_date:{DATE_TO.isoformat()},language:en","per-page":int(CONFIG.get("openalex_per_query",50)),"sort":"relevance_score:desc"}
        if OPENALEX_API_KEY: params["api_key"] = OPENALEX_API_KEY
        try:
            r = SESSION.get("https://api.openalex.org/works", params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code == 429:
                warnings.append("OpenAlex rate limited (429)"); _diag("openalex_429"); time.sleep(1.2); continue
            r.raise_for_status(); works = r.json().get("results", [])
        except Exception as e:
            warnings.append(f"OpenAlex {type(e).__name__}: {e}"); continue
        _diag("openalex_api_results", len(works))
        raw_list: list[dict[str, Any]] = []
        rescue_queue: list[tuple[int, dict[str, Any]]] = []
        for w in works:
            loc=w.get("primary_location") or {}; src=loc.get("source") or {}; doi=clean(w.get("doi")); url=clean(loc.get("landing_page_url") or doi or w.get("id"))
            authors="; ".join(clean((a.get("author") or {}).get("display_name")) for a in w.get("authorships", [])[:12])
            raw={"title":w.get("title"),"abstract":openalex_abstract(w.get("abstract_inverted_index")),"date":w.get("publication_date"),"url":url,"doi":doi,"authors":authors,"venue":src.get("display_name"),"publisher":src.get("host_organization_name"),"discovery":f"OpenAlex · {q}"}
            raw_list.append(raw)
            if not raw["abstract"]:
                prof=source_for(domain_of(url), clean(raw.get("venue")), clean(raw.get("publisher")))
                p=metadata_rescue_priority(clean(raw.get("title")), q, prof, parse_date(raw.get("date")))
                if p >= min_priority: rescue_queue.append((p, raw))
        rescue_queue.sort(key=lambda x:x[0], reverse=True); _diag("openalex_metadata_rescue_queued",len(rescue_queue))
        for _, raw in rescue_queue[:max(0,min(per_query,scan_cap-used_rescue))]:
            text=fetch_text(clean(raw.get("url")), int(CONFIG.get("missing_abstract_enrichment_timeout_seconds",9)))
            used_rescue += 1; _diag("openalex_metadata_rescue_attempted")
            if text: raw["abstract"]=text; _diag("openalex_metadata_rescue_recovered")
        for raw in raw_list:
            item=admit(raw,lane)
            if item: out.append(item)
        log(f"OpenAlex: {q[:68]} -> {len(out)} admitted cumulative")
    return out


def collect_crossref(queries: list[str], warnings: list[str], lane: str = "crossref") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    scan_cap=int(CONFIG.get("crossref_missing_abstract_enrichment_per_scan",36)); per_task=int(CONFIG.get("crossref_missing_abstract_enrichment_per_query",3)); min_priority=int(CONFIG.get("metadata_rescue_priority_min_score",10)); used_rescue=0
    query_key = "query.title" if clean(CONFIG.get("crossref_relevance_query_mode","title")).lower()=="title" else "query.bibliographic"
    for q in queries:
        if not budget_ok(90): break
        params={query_key:q,"filter":f"from-pub-date:{DATE_FROM.isoformat()},until-pub-date:{DATE_TO.isoformat()}","rows":int(CONFIG.get("crossref_per_query",50)),"sort":"relevance","order":"desc","select":"DOI,title,abstract,published-print,published-online,published,issued,created,author,container-title,publisher,URL,type"}
        try:
            r=SESSION.get("https://api.crossref.org/works",params=params,timeout=REQUEST_TIMEOUT)
            if r.status_code==429: warnings.append("Crossref rate limited (429)"); _diag("crossref_429"); continue
            r.raise_for_status(); works=((r.json().get("message") or {}).get("items") or [])
        except Exception as e:
            warnings.append(f"Crossref {type(e).__name__}: {e}"); continue
        _diag("crossref_api_results",len(works))
        raw_list=[]; rescue_queue=[]
        for w in works:
            title=clean(" ".join(w.get("title") or [])); venue=clean(" ".join(w.get("container-title") or [])); authors="; ".join(clean(f"{a.get('given','')} {a.get('family','')}") for a in (w.get("author") or [])[:12]); doi=clean(w.get("DOI")); url=clean(w.get("URL") or ("https://doi.org/"+doi if doi else ""))
            raw={"title":title,"abstract":clean(re.sub(r"<[^>]+>"," ",w.get("abstract") or "")),"date":crossref_date(w),"url":url,"doi":doi,"authors":authors,"venue":venue,"publisher":clean(w.get("publisher")),"discovery":f"Crossref · {q}"}
            raw_list.append(raw)
            if not raw["abstract"]:
                prof=source_for(domain_of(url),venue,clean(raw.get("publisher"))); p=metadata_rescue_priority(title,q,prof,parse_date(raw.get("date")))
                if p>=min_priority: rescue_queue.append((p,raw))
        rescue_queue.sort(key=lambda x:x[0],reverse=True); _diag("crossref_metadata_rescue_queued",len(rescue_queue))
        for _,raw in rescue_queue[:max(0,min(per_task,scan_cap-used_rescue))]:
            text=fetch_text(clean(raw.get("url")),int(CONFIG.get("missing_abstract_enrichment_timeout_seconds",9))); used_rescue+=1; _diag("crossref_metadata_rescue_attempted")
            if text: raw["abstract"]=text; _diag("crossref_metadata_rescue_recovered")
        for raw in raw_list:
            item=admit(raw,lane)
            if item: out.append(item)
        log(f"Crossref: {q[:68]} -> {len(out)} admitted cumulative")
    return out


def localname(tag: str) -> str: return tag.split("}")[-1].lower()


def xml_bytes(resp: requests.Response) -> bytes:
    data=resp.content
    if resp.url.endswith(".gz") or "gzip" in (resp.headers.get("Content-Type") or "").lower():
        try: data=gzip.decompress(data)
        except Exception: pass
    return data


def topic_score(text: str, active_topics: list[dict[str, Any]]) -> int:
    n=norm(text); score=0
    for t in active_topics:
        for term in t.get("url_terms",[]):
            p=norm(term.replace("-"," "))
            if p and p in n: score += 3
    if re.search(r"report|publication|study|analysis|paper|research|foresight|policy|strategy|brief|outlook",n,re.I): score += 2
    return score


def source_adapter_candidates(src: dict[str, Any], active_topics: list[dict[str, Any]], warnings: list[str]) -> list[str]:
    domain=clean(src.get("domain")); profiles=CONFIG.get("source_adapters",{}); hubs=profiles.get(domain,[]) if isinstance(profiles,dict) else []
    if not hubs: return []
    max_hubs=int(CONFIG.get("source_adapter_max_hub_fetches",6)); max_pages=int(CONFIG.get("source_adapter_pages_per_source",20)); scored:dict[str,int]={}
    for path in hubs[:max_hubs]:
        if not budget_ok(90): break
        url=path if str(path).startswith("http") else f"https://{domain}{path}"
        try:
            r=SESSION.get(url,timeout=REQUEST_TIMEOUT,allow_redirects=True)
            if not r.ok: continue
            soup=BeautifulSoup(r.text,"html.parser")
        except Exception: continue
        for a in soup.find_all("a",href=True):
            href=urljoin(r.url,clean(a.get("href"))); d=domain_of(href)
            if not d or not (d==domain or d.endswith("."+domain) or domain.endswith("."+d)): continue
            label=clean(a.get_text(" ",strip=True)); s=topic_score(f"{urlparse(href).path} {label}",active_topics)
            if s>0: scored[href]=max(scored.get(href,0),s)
    if scored: _diag("institution_adapter_jobs",len(scored))
    else: warnings.append(f"Source adapter found no topic links: {domain}")
    return [u for u,_ in sorted(scored.items(),key=lambda kv:(-kv[1],kv[0]))[:max_pages]]


def sitemap_candidates(domain: str, active_topics: list[dict[str, Any]], warnings: list[str]) -> list[str]:
    roots=[f"https://{domain}/sitemap.xml",f"https://{domain}/sitemap_index.xml"]; queue=list(roots); seen_maps=set(); urls=[]
    while queue and len(seen_maps)<12 and budget_ok(90):
        sm=queue.pop(0)
        if sm in seen_maps: continue
        seen_maps.add(sm)
        try:
            r=SESSION.get(sm,timeout=REQUEST_TIMEOUT); 
            if not r.ok: continue
            root=ET.fromstring(xml_bytes(r))
        except Exception: continue
        if localname(root.tag)=="sitemapindex":
            for node in root.iter():
                if localname(node.tag)=="loc":
                    loc=clean(node.text)
                    if loc and loc not in seen_maps: queue.append(loc)
            continue
        for node in root.iter():
            if localname(node.tag)!="url": continue
            loc=""
            for ch in node:
                if localname(ch.tag)=="loc": loc=clean(ch.text)
            if not loc: continue
            s=topic_score(urlparse(loc).path,active_topics)
            if s>0: urls.append((s,loc))
    if not urls: warnings.append(f"No usable topic sitemap results: {domain}")
    return [u for _,u in sorted(urls,key=lambda x:(-x[0],x[1]))]


def page_date(soup: BeautifulSoup, text: str) -> dt.date | None:
    candidates=[]
    for tag in soup.find_all("meta"):
        key=clean(tag.get("property") or tag.get("name") or tag.get("itemprop")).lower()
        if key in {"article:published_time","date","datepublished","publication_date","dc.date","dcterms.date"}: candidates.append(clean(tag.get("content")))
    for t in soup.find_all("time")[:5]: candidates.append(clean(t.get("datetime") or t.get_text(" ",strip=True)))
    for c in candidates:
        d=parse_date(c)
        if d and DATE_FROM<=d<=DATE_TO: return d
    m=re.search(r"\b(202[3-5])[-/.](\d{1,2})[-/.](\d{1,2})\b",text[:7000]); return parse_date(m.group(0)) if m else None


def fetch_page_candidate(url: str, src: dict[str, Any], warnings: list[str], lane: str="direct") -> dict[str, Any] | None:
    if not budget_ok(50): return None
    try:
        r=SESSION.get(url,timeout=REQUEST_TIMEOUT,allow_redirects=True)
        if not r.ok: _diag("direct_fetch_failure"); return None
    except Exception: _diag("direct_fetch_failure"); return None
    ctype=(r.headers.get("Content-Type") or "").lower()
    if "pdf" in ctype or r.url.lower().endswith(".pdf"):
        try:
            reader=PdfReader(io.BytesIO(r.content)); body=clean(" ".join((p.extract_text() or "") for p in reader.pages[:10])); title=clean(reader.metadata.title if reader.metadata else "") or clean(urlparse(r.url).path.rsplit("/",1)[-1].replace("-"," ")); d=parse_date(reader.metadata.creation_date if reader.metadata else None)
        except Exception: return None
        if not d:
            m=re.search(r"\b(202[3-5])[-/.](\d{1,2})[-/.](\d{1,2})\b",body[:6000]); d=parse_date(m.group(0)) if m else None
        return admit({"title":title,"abstract":body[:10000],"date":d,"url":r.url,"venue":src.get("name"),"publisher":src.get("name"),"discovery":f"direct source · {src.get('name')}"},lane)
    try: soup=BeautifulSoup(r.text,"html.parser")
    except Exception: return None
    title_tag=soup.find("meta",property="og:title"); title=clean(title_tag.get("content") if title_tag else "")
    if not title and soup.title: title=clean(soup.title.get_text(" ",strip=True))
    desc_tag=soup.find("meta",attrs={"name":"description"}) or soup.find("meta",property="og:description"); desc=clean(desc_tag.get("content") if desc_tag else "")
    for bad in soup(["script","style","nav","footer","form","noscript"]): bad.decompose()
    body=clean(soup.get_text(" ",strip=True))[:14000]; d=page_date(soup,body)
    return admit({"title":title,"abstract":clean(f"{desc} {body[:9000]}"),"date":d,"url":r.url,"venue":src.get("name"),"publisher":src.get("name"),"discovery":f"direct source · {src.get('name')}"},lane)


def collect_direct_sources(active_sources: list[dict[str, Any]], active_topics: list[dict[str, Any]], warnings: list[str]) -> list[dict[str, Any]]:
    out=[]; limit=int(CONFIG.get("direct_pages_per_source",16))
    for src in active_sources:
        if not budget_ok(120): break
        domain=clean(src.get("domain"));
        if not domain: continue
        adapter=source_adapter_candidates(src,active_topics,warnings); sitemap=sitemap_candidates(domain,active_topics,warnings)
        urls=[]; seen=set()
        for u in adapter+sitemap:
            k=u.lower().rstrip("/")
            if k not in seen: urls.append(u); seen.add(k)
        admitted=0
        for url in urls[:limit]:
            if not budget_ok(55): break
            item=fetch_page_candidate(url,src,warnings,"direct")
            if item: out.append(item); admitted+=1
        log(f"Direct source: {src.get('name')} -> {admitted} admitted")
    return out


def rotating(items: list[Any], cursor: int, count: int) -> tuple[list[Any], int]:
    if not items or count<=0: return [],0
    start=cursor%len(items); take=min(count,len(items)); return [items[(start+i)%len(items)] for i in range(take)],(start+take)%len(items)


def dedupe(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    best={}; title_best={}
    for item in items:
        if not isinstance(item,dict): continue
        key=clean(item.get("id")) or stable_id(clean(item.get("title")),clean(item.get("url"))); tkey=norm(item.get("title")); target=title_best.get(tkey,key) if tkey else key; old=best.get(target)
        if old is None or int(item.get("source_merit_score",0))>int(old.get("source_merit_score",0)):
            best[target]=item
            if tkey: title_best[tkey]=target
    return list(best.values())


def query_plan_for(topics: list[dict[str, Any]]) -> list[str]:
    qpt=int(CONFIG.get("queries_per_topic",2)); q=[]
    for t in topics: q.extend(list(t.get("queries",[]))[:qpt])
    return list(dict.fromkeys(clean(x) for x in q if clean(x)))


def rejection_funnel(new_items: int, unique_gate_candidates: int) -> dict[str, Any]:
    return {
        "raw_records": int(DIAG["raw_records"]),
        "source_eligible": int(DIAG["source_eligible"]),
        "enough_text": int(DIAG["enough_text"]),
        "eu_scope": int(DIAG["eu_scope"]),
        "ri_scope": int(DIAG["ri_scope"]),
        "strategic_scope": int(DIAG["strategic_scope"]),
        "topic_match": int(DIAG["topic_match"]),
        "gate_passed_before_dedupe": int(DIAG["gate_passed"]),
        "unique_gate_candidates": int(unique_gate_candidates),
        "genuinely_new_items": int(new_items),
        "metadata_text_rescue": {
            "queued": int(DIAG["openalex_metadata_rescue_queued"]+DIAG["crossref_metadata_rescue_queued"]),
            "attempted": int(DIAG["openalex_metadata_rescue_attempted"]+DIAG["crossref_metadata_rescue_attempted"]),
            "text_recovered": int(DIAG["openalex_metadata_rescue_recovered"]+DIAG["crossref_metadata_rescue_recovered"]),
        },
        "source_adapter_jobs": int(DIAG["institution_adapter_jobs"]),
        "rejections": {k:int(v) for k,v in sorted(DIAG.items()) if k.startswith("reject_") or k.startswith("defer_") or k=="insufficient_text"},
    }


def run_rotation(active_topics: list[dict[str, Any]], active_sources: list[dict[str, Any]], warnings: list[str], suffix: str="normal") -> tuple[list[dict[str, Any]], list[str]]:
    queries=query_plan_for(active_topics); candidates=[]
    candidates.extend(collect_openalex(queries,warnings,f"openalex_{suffix}"))
    candidates.extend(collect_crossref(queries,warnings,f"crossref_{suffix}"))
    candidates.extend(collect_direct_sources(active_sources,active_topics,warnings))
    return candidates,queries


def main() -> int:
    try: previous=json.loads(OUT_PATH.read_text(encoding="utf-8")) if OUT_PATH.exists() else {}
    except Exception: previous={}
    state=previous.get("scan_state") if isinstance(previous.get("scan_state"),dict) else {}
    topics=list(CONFIG.get("topics",[])); sources=list(CONFIG.get("elite_sources",[]))
    topic_cursor=int(state.get("topic_cursor",0)); source_cursor=int(state.get("source_cursor",0))
    active_topics,next_topic=rotating(topics,topic_cursor,int(CONFIG.get("topics_per_scan",4)))
    active_sources,next_source=rotating(sources,source_cursor,int(CONFIG.get("sources_per_scan",8)))
    warnings=[]; log("Historical scan starts: full 2023–2025 window, topic rotation only")
    log("Topics: "+" | ".join(str(t.get("label")) for t in active_topics))
    candidates,queries=run_rotation(active_topics,active_sources,warnings,"normal")
    old_items=[x for x in previous.get("items",[]) if isinstance(x,dict)]; old_ids={clean(x.get("id")) for x in old_items}
    unique_initial=dedupe(candidates); initial_new=sum(1 for x in unique_initial if clean(x.get("id")) not in old_ids)
    low_threshold=int(CONFIG.get("low_yield_trigger_max_new_items",3)); low_triggered=initial_new<=low_threshold
    rescue_topics=[]; rescue_sources=[]; rescue_queries=[]; rescue_candidates=[]
    if low_triggered and budget_ok(220):
        rescue_topics,rescue_next_topic=rotating(topics,next_topic,int(CONFIG.get("low_yield_fresh_topics",4)))
        rescue_sources,rescue_next_source=rotating(sources,next_source,int(CONFIG.get("low_yield_fresh_sources",8)))
        log(f"Low yield ({initial_new}); forcing fresh historical topic/source rotation inside this run")
        rescue_candidates,rescue_queries=run_rotation(rescue_topics,rescue_sources,warnings,"fresh")
        candidates.extend(rescue_candidates); next_topic=rescue_next_topic; next_source=rescue_next_source
    unique_gate=dedupe(candidates); merged=dedupe(old_items+unique_gate)
    merged=[x for x in merged if (d:=parse_date(x.get("date"))) and DATE_FROM<=d<=DATE_TO]
    merged.sort(key=lambda x:(int(x.get("source_merit_score",0)),int(x.get("year",0)),x.get("date","")),reverse=True)
    if MAX_ITEMS>0: merged=merged[:MAX_ITEMS]
    new_count=sum(1 for x in merged if clean(x.get("id")) not in old_ids)
    matrix_counts={r:{c:0 for c in "ABCD"} for r in ROW_TERMS}
    for x in merged:
        r,c=clean(x.get("matrix_dimension")),clean(x.get("matrix_outcome"))
        if r in matrix_counts and c in matrix_counts[r]: matrix_counts[r][c]+=1
    now=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    full_rescue_enabled=bool(CONFIG.get("full_rescue_run_enabled",True)); full_rescue_threshold=int(CONFIG.get("full_rescue_run_trigger_max_new_items",3)); should_dispatch=(full_rescue_enabled and not RESCUE_MODE and new_count<=full_rescue_threshold)
    data={
        "profile_version":CONFIG.get("profile_version"),"last_updated":now,"date_from":DATE_FROM.isoformat(),"date_to":DATE_TO.isoformat(),
        "scope_note":"Separate historical archive. It does not feed the live radar, live Matrix, weak signals or live scan scheduling.",
        "ranking_note":"Every run searches the whole 2023–2025 period. Topic families rotate; years do not. When otherwise comparable, 2025 is preferred to 2024 and 2024 to 2023.",
        "source_policy":"Only official EU sources, a small elite institute list and a short list of top political, innovation and technology-foresight journals are eligible.",
        "items":merged,"matrix_counts":matrix_counts,
        "scan_state":{"topic_cursor":next_topic,"source_cursor":next_source,"completed_runs":int(state.get("completed_runs",0))+1,"last_completed_at":now},
        "last_scan":{
            "status":"ok" if not warnings else "completed_with_warnings","rescue_mode":RESCUE_MODE,
            "topics":[str(t.get("label")) for t in active_topics],"sources":[str(s.get("name")) for s in active_sources],"queries":queries,
            "low_yield_rotation":{"triggered":low_triggered,"new_items_after_normal_rotation":initial_new,"fresh_topics":[str(t.get("label")) for t in rescue_topics],"fresh_sources":[str(s.get("name")) for s in rescue_sources],"fresh_queries":rescue_queries,"new_items_after_all_in_run_rotations":new_count,"full_rescue_run_enabled":full_rescue_enabled,"full_rescue_run_should_dispatch":should_dispatch},
            "new_items":new_count,"candidates_seen":len(candidates),"unique_gate_candidates":len(unique_gate),"total_items":len(merged),"runtime_seconds":round(time.monotonic()-STARTED_MONO,1),
            "openalex_api_key_configured":bool(OPENALEX_API_KEY),"rejection_funnel":rejection_funnel(new_count,len(unique_gate)),"diagnostics":{k:int(v) for k,v in sorted(DIAG.items())},"warnings":list(dict.fromkeys(warnings))[:50],
        },
    }
    tmp=OUT_PATH.with_suffix(".json.tmp"); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); tmp.replace(OUT_PATH)
    log(f"historical.json written: {len(merged)} total, {new_count} new; full-rescue-dispatch={should_dispatch}")
    for w in warnings[:20]: print("WARNING:",w,file=sys.stderr)
    return 0


if __name__=="__main__": raise SystemExit(main())
