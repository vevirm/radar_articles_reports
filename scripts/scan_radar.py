#!/usr/bin/env python3
"""Keyless, conservative scanner for the R&I × Geopolitics radar.

Discovery layers:
1) Crossref metadata for the whitelisted peer-reviewed journals.
2) Sitemaps + verified page metadata/PDF text for whitelisted institutions.
3) Google News RSS searches restricted to the Strand C news whitelist.

The scanner intentionally prefers false negatives over false positives. It does not
pad the radar. Optional OPENALEX_API_KEY support is included for extra scholarly
coverage, but the scanner does not require any secret to run.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import gzip
import io
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus, urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "radar.json"
DATE_FLOOR = dt.date(2026, 4, 1)
SCAN_HOURS = 12
NEWS_LOOKBACK_HOURS = 13  # one-hour overlap avoids gaps if a scheduled job is delayed
MAX_AB_UNIQUE = 15
MAX_C = 5
REQUEST_TIMEOUT = 12
UA = "RI-Geopolitics-Radar/1.0 (+https://vevirm.github.io/radar_articles_reports/)"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": UA,
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

# Tier 1 + Tier 3 institutions. "extend by analogy" is intentionally not automated
# too broadly; comparable sources can be added here without changing the scanner.
INSTITUTIONS = [
    ("European Commission — Research & Innovation", "research-and-innovation.ec.europa.eu", 1),
    ("European Commission", "commission.europa.eu", 1),
    ("Joint Research Centre", "joint-research-centre.ec.europa.eu", 1),
    ("Bruegel", "bruegel.org", 1),
    ("CEPS", "ceps.eu", 1),
    ("MERICS", "merics.org", 1),
    ("SWP", "swp-berlin.org", 1),
    ("IFRI", "ifri.org", 1),
    ("EUISS", "iss.europa.eu", 1),
    ("Clingendael", "clingendael.org", 1),
    ("Chatham House", "chathamhouse.org", 1),
    ("Fraunhofer ISI", "isi.fraunhofer.de", 1),
    ("Rathenau Instituut", "rathenau.nl", 1),
    ("Nesta", "nesta.org.uk", 1),
    ("OECD", "oecd.org", 1),
    ("RAND", "rand.org", 3),
    ("CSIS", "csis.org", 3),
    ("Brookings", "brookings.edu", 3),
    ("Carnegie", "carnegieendowment.org", 3),
    ("CSET", "cset.georgetown.edu", 3),
    ("ASPI", "aspi.org.au", 3),
    ("NBER", "nber.org", 3),
]

JOURNALS = {
    "research policy",
    "science and public policy",
    "technological forecasting and social change",
    "technological forecasting & social change",
    "futures",
    "foresight",
    "minerva",
    "technology in society",
    "issues in science and technology",
}

NEWS_SOURCES = [
    ("Science|Business", "sciencebusiness.net"),
    ("Research Professional News", "researchprofessionalnews.com"),
    ("Table.Media", "table.media"),
    ("Nature", "nature.com"),
    ("Science", "science.org"),
    ("Times Higher Education", "timeshighereducation.com"),
    ("Financial Times", "ft.com"),
    ("Politico Europe", "politico.eu"),
    ("The Economist", "economist.com"),
    ("Reuters", "reuters.com"),
    ("Handelsblatt", "handelsblatt.com"),
    ("Le Monde", "lemonde.fr"),
    ("NRC", "nrc.nl"),
    ("El País", "elpais.com"),
]

CROSSREF_QUERIES = [
    "European research security foreign interference trusted research",
    "EU technology sovereignty strategic autonomy research innovation",
    "Europe science technology cooperation China de-risking",
    "European research export controls dual use science",
    "EU economic security research innovation critical technologies",
    "Horizon Europe FP10 international cooperation geopolitics",
    "foresight methodology research innovation geopolitical uncertainty Europe",
    "horizon scanning anticipatory governance science technology Europe",
    "scenario methods research innovation policy geopolitical uncertainty",
]

OPENALEX_QUERIES = CROSSREF_QUERIES[:5]

EU_DIRECT = [
    "european union", " eu ", "eu-", "horizon europe", "fp10", "member state",
    "european commission", "european parliament", "joint research centre", " jrc ",
    "european research area", "open strategic autonomy", "strategic autonomy",
    "european economic security", "european innovation", "european research",
    "european science", "erc", "era policy", "step regulation",
]
EU_DERIVED = ["europe", "european", "europe's", "european countries"]
RI_TERMS = [
    "research policy", "innovation policy", "research and innovation", "r&i", "science policy",
    "science and technology", "s&t", "research collaboration", "scientific collaboration",
    "research funding", "horizon europe", "fp10", "research system", "innovation system",
    "technology policy", "critical technology", "emerging technology", "research security",
    "academic research", "university research", "talent mobility", "science diplomacy",
]
GEO_TERMS = [
    "geopolit", "economic security", "strategic autonomy", "sovereignty", "de-risk",
    "foreign interference", "research security", "export control", "dual-use", "dual use",
    "us-china", "u.s.-china", "china", "transatlantic", "fragmentation", "national security",
    "technology competition", "strategic competition", "sanctions", "trusted research",
    "third-country", "third country", "association agreement",
]
FORESIGHT_TERMS = [
    "foresight method", "strategic foresight", "horizon scanning", "scenario method",
    "scenario planning", "scenario design", "anticipatory governance", "anticipatory intelligence",
    "futures method", "foresight evaluation", "foresight practice", "foresight process",
    "foresight methodology", "scenario methodology", "weak signal", "anticipation system",
    "strategic intelligence", "risk assessment", "uncertainty", "wild card", "wind tunnelling",
]
METHOD_TERMS = [
    "method", "methodology", "design", "evaluation", "institutional", "framework", "process",
    "practice", "approach", "bias", "limitation", "governance", "integration", "assessment",
]
EXCLUDE_AB = [
    "op-ed", "op ed", "opinion", "commentary", "editorial", "blog", "podcast", "student thesis",
    "master's thesis", "masters thesis", "doctoral thesis", "phd thesis", "advertorial", "sponsored",
]
EXCLUDE_C = [
    "opinion", "commentary", "editorial", "analysis:", "analysis -", "column", "viewpoint",
    "podcast", "book review", "letters to the editor", "explainer", "interview",
]

THEMES = {
    "research security / foreign interference": ["research security", "foreign interference", "trusted research", "security screening"],
    "technology sovereignty / strategic autonomy": ["technology sovereignty", "technological sovereignty", "strategic autonomy", "sovereignty"],
    "EU–China S&T cooperation / de-risking": ["china", "eu-china", "de-risk", "research cooperation", "science cooperation"],
    "export controls / dual use": ["export control", "dual use", "dual-use", "technology transfer"],
    "fragmentation of global science": ["fragmentation", "scientific collaboration", "research collaboration", "decoupling"],
    "transatlantic / US–China S&T competition": ["us-china", "u.s.-china", "transatlantic", "strategic competition", "technology competition"],
    "critical and emerging technologies": ["critical technology", "emerging technology", "semiconductor", "chips", "quantum", "biotech", "artificial intelligence", " ai "],
    "economic security and R&I": ["economic security", "research funding", "innovation funding", "talent mobility"],
    "Horizon Europe / FP10 international participation": ["horizon europe", "fp10", "association agreement", "third country", "third-country"],
    "foresight / horizon scanning methodology": ["foresight method", "foresight methodology", "horizon scanning", "weak signal"],
    "scenario methods under uncertainty": ["scenario method", "scenario planning", "scenario design", "uncertainty"],
    "anticipatory governance / strategic intelligence": ["anticipatory governance", "strategic intelligence", "anticipatory intelligence", "risk assessment"],
}


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def norm_title(s: str) -> str:
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str) -> set[str]:
    stop = {"the","a","an","and","or","of","to","in","for","on","with","from","by","as","at","is","are","be","this","that","how","its","into","under","new","eu","european","europe"}
    return {w for w in re.findall(r"[a-z][a-z0-9-]{2,}", s.lower()) if w not in stop}


def parse_date(value: Any) -> dt.date | None:
    if not value:
        return None
    try:
        if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
            parts = value[0]
            return dt.date(int(parts[0]), int(parts[1] if len(parts) > 1 else 1), int(parts[2] if len(parts) > 2 else 1))
        if isinstance(value, dict) and "date-parts" in value:
            return parse_date(value["date-parts"])
        if isinstance(value, dt.date):
            return value
        return dateparser.parse(str(value), fuzzy=False).date()
    except Exception:
        return None


def phrase_score(text: str, phrases: Iterable[str]) -> float:
    low = f" {text.lower()} "
    score = 0.0
    for p in phrases:
        if p.startswith(" ") or p.endswith(" "):
            if p in low:
                score += 1.0
        elif p.endswith("it") and p in low:  # e.g. geopolit fragment
            score += 1.0
        elif p in low:
            score += 1.0
    return score


def eu_relevance(title: str, text: str, source_tier: int) -> tuple[str | None, float]:
    t = f" {title.lower()} "
    body = f" {text.lower()} "
    direct_title = phrase_score(t, EU_DIRECT + EU_DERIVED)
    direct_body = phrase_score(body, EU_DIRECT)
    derived_body = phrase_score(body, EU_DERIVED)
    if direct_title >= 1 or direct_body >= 1.5 or (source_tier == 1 and (direct_body + derived_body) >= 1):
        return "direct", 3.0 + direct_title + min(direct_body, 2)
    if derived_body >= 1:
        return "derived", 1.5 + derived_body
    return None, 0.0


def classify(title: str, text: str, source_tier: int) -> tuple[str | None, str | None, dict[str, float]]:
    full = f"{title}. {text}"
    eu, eu_s = eu_relevance(title, full, source_tier)
    if not eu:
        return None, None, {}
    ri = phrase_score(full, RI_TERMS)
    geo = phrase_score(full, GEO_TERMS)
    foresight = phrase_score(full, FORESIGHT_TERMS)
    method = phrase_score(full, METHOD_TERMS)
    # Strand A requires both R&I and geopolitics.
    a = ri >= 1.5 and geo >= 1.5
    # Strand B is methodology-first, not merely a scenario/trend output.
    b = foresight >= 1.5 and method >= 1.0 and (ri >= 0.8 or geo >= 0.8)
    strand = "both" if a and b else "A" if a else "B" if b else None
    return strand, eu, {"eu": eu_s, "ri": ri, "geo": geo, "foresight": foresight, "method": method}


def themes_for(text: str) -> list[str]:
    low = f" {text.lower()} "
    out = []
    for name, terms in THEMES.items():
        if any(term in low for term in terms):
            out.append(name)
    return out


def sentence_list(text: str) -> list[str]:
    text = clean_text(text)
    chunks = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [c.strip() for c in chunks if 35 <= len(c.strip()) <= 520]


def summary_three(title: str, text: str, strand: str, themes: list[str]) -> str:
    sents = sentence_list(text)
    if sents:
        key_terms = tokens(title + " " + " ".join(themes))
        ranked = sorted(enumerate(sents[:40]), key=lambda x: (len(tokens(x[1]) & key_terms), -x[0]), reverse=True)
        chosen_idx = sorted(i for i, _ in ranked[:2])
        chosen = [sents[i] for i in chosen_idx]
    else:
        chosen = []
    while len(chosen) < 2:
        if len(chosen) == 0:
            chosen.append(f"The item examines {title.rstrip('.')}.")
        else:
            theme = themes[0] if themes else "research and innovation policy under geopolitical uncertainty"
            chosen.append(f"Its substantive focus is {theme}.")
    theme_txt = ", ".join(themes[:2]) if themes else "the radar's R&I–geopolitics scope"
    chosen.append(f"It is classified in Strand {strand} because its verified content connects to {theme_txt} in a European policy context.")
    return " ".join(s.rstrip() + ("" if s.rstrip().endswith(('.', '!', '?')) else ".") for s in chosen[:3])


def relevance_note(strand: str, eu: str, themes: list[str]) -> str:
    t = "; ".join(themes[:2]) if themes else "R&I–geopolitics / foresight methodology"
    return f"{eu.capitalize()} EU relevance; useful for tracking {t}."


def excluded(text: str, terms: list[str]) -> bool:
    low = text.lower()
    return any(t in low for t in terms)


def get(url: str, **kwargs) -> requests.Response | None:
    try:
        r = SESSION.get(url, timeout=kwargs.pop("timeout", REQUEST_TIMEOUT), allow_redirects=True, **kwargs)
        if r.status_code == 200:
            return r
    except requests.RequestException:
        return None
    return None


def crossref_date(item: dict) -> dt.date | None:
    for key in ("published-online", "published-print", "published", "issued"):
        d = parse_date(item.get(key))
        if d:
            return d
    return None


def crossref_authors(item: dict) -> str:
    names = []
    for a in item.get("author", [])[:8]:
        name = " ".join(x for x in [a.get("given", ""), a.get("family", "")] if x).strip()
        if name:
            names.append(name)
    if len(item.get("author", [])) > 8:
        names.append("et al.")
    return ", ".join(names)


def collect_crossref(errors: list[str]) -> list[dict]:
    out: list[dict] = []
    for q in CROSSREF_QUERIES:
        params = {
            "query.bibliographic": q,
            "filter": f"from-pub-date:{DATE_FLOOR.isoformat()}",
            "rows": 45,
            "sort": "published",
            "order": "desc",
        }
        try:
            r = SESSION.get("https://api.crossref.org/works", params=params, timeout=20)
            if r.status_code != 200:
                errors.append(f"Crossref HTTP {r.status_code}")
                continue
            items = r.json().get("message", {}).get("items", [])
        except Exception as e:
            errors.append(f"Crossref: {type(e).__name__}")
            continue
        for it in items:
            title = clean_text((it.get("title") or [""])[0])
            if not title or excluded(title, EXCLUDE_AB):
                continue
            journal = clean_text((it.get("container-title") or [""])[0])
            if journal.lower().strip() not in JOURNALS:
                continue
            date = crossref_date(it)
            if not date or date < DATE_FLOOR:
                continue
            abstract = clean_text(it.get("abstract", ""))
            # Crossref searches bibliographic metadata; require the title/abstract itself to pass scope.
            strand, eu, scores = classify(title, abstract, 2)
            if not strand:
                continue
            typ = "peer-reviewed article" if it.get("type") == "journal-article" else clean_text(it.get("type", "publication"))
            if "thesis" in typ.lower():
                continue
            doi = it.get("DOI")
            link = f"https://doi.org/{doi}" if doi else it.get("URL", "")
            th = themes_for(title + " " + abstract)
            out.append({
                "title": title,
                "authors": crossref_authors(it),
                "source": journal,
                "date": date.isoformat(),
                "link": link,
                "type": typ,
                "strand": strand,
                "eu_relevance": eu,
                "source_tier": 2,
                "summary": summary_three(title, abstract, strand, th),
                "relevance_note": relevance_note(strand, eu, th),
                "_themes": th,
                "_score": scores,
                "_doi": (doi or "").lower(),
                "_preprint": it.get("type") in {"posted-content", "preprint"},
            })
    return out


def openalex_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pairs = []
    for word, positions in inv.items():
        for pos in positions:
            pairs.append((pos, word))
    return " ".join(w for _, w in sorted(pairs))


def collect_openalex(errors: list[str]) -> list[dict]:
    """Optional extra scholarly coverage. Anonymous mode stays deliberately small."""
    key = os.getenv("OPENALEX_API_KEY", "").strip()
    out: list[dict] = []
    queries = OPENALEX_QUERIES if key else OPENALEX_QUERIES[:2]
    for q in queries:
        params = {
            "search": q,
            "filter": f"from_publication_date:{DATE_FLOOR.isoformat()}",
            "per-page": 25,
            "sort": "publication_date:desc",
        }
        if key:
            params["api_key"] = key
        try:
            r = SESSION.get("https://api.openalex.org/works", params=params, timeout=20)
            if r.status_code != 200:
                errors.append(f"OpenAlex HTTP {r.status_code}")
                continue
            works = r.json().get("results", [])
        except Exception as e:
            errors.append(f"OpenAlex: {type(e).__name__}")
            continue
        for w in works:
            title = clean_text(w.get("display_name", ""))
            src = clean_text(((w.get("primary_location") or {}).get("source") or {}).get("display_name", ""))
            if src.lower().strip() not in JOURNALS or excluded(title, EXCLUDE_AB):
                continue
            date = parse_date(w.get("publication_date"))
            if not date or date < DATE_FLOOR:
                continue
            abstract = clean_text(openalex_abstract(w.get("abstract_inverted_index")))
            strand, eu, scores = classify(title, abstract, 2)
            if not strand:
                continue
            authors = ", ".join(clean_text((a.get("author") or {}).get("display_name", "")) for a in w.get("authorships", [])[:8])
            doi = clean_text(w.get("doi", ""))
            link = doi if doi.startswith("http") else clean_text((w.get("primary_location") or {}).get("landing_page_url", ""))
            th = themes_for(title + " " + abstract)
            out.append({
                "title": title, "authors": authors, "source": src, "date": date.isoformat(), "link": link,
                "type": "peer-reviewed article", "strand": strand, "eu_relevance": eu, "source_tier": 2,
                "summary": summary_three(title, abstract, strand, th), "relevance_note": relevance_note(strand, eu, th),
                "_themes": th, "_score": scores, "_doi": doi.replace("https://doi.org/", "").lower(), "_preprint": False,
            })
    return out


def decompress_xml(content: bytes) -> bytes:
    if content[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(content)
        except Exception:
            pass
    return content


def localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def discover_sitemaps(domain: str) -> list[str]:
    base = f"https://{domain}"
    urls: list[str] = []
    r = get(base + "/robots.txt")
    if r:
        for line in r.text.splitlines():
            if line.lower().startswith("sitemap:"):
                urls.append(line.split(":", 1)[1].strip())
    urls.extend([base + "/sitemap.xml", base + "/sitemap_index.xml"])
    seen, unique = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u); unique.append(u)
    return unique[:8]


def sitemap_entries(url: str, depth: int = 0, budget: int = 4) -> list[tuple[str, dt.date | None]]:
    if depth > 2 or budget <= 0:
        return []
    r = get(url, timeout=15)
    if not r or len(r.content) > 12_000_000:
        return []
    try:
        root = ET.fromstring(decompress_xml(r.content))
    except Exception:
        return []
    kind = localname(root.tag)
    if kind == "sitemapindex":
        kids = []
        for sm in list(root):
            loc = None; last = None
            for ch in list(sm):
                if localname(ch.tag) == "loc": loc = (ch.text or "").strip()
                if localname(ch.tag) == "lastmod": last = parse_date((ch.text or "").strip())
            if loc:
                priority = 0
                low = loc.lower()
                if any(k in low for k in ["post", "publication", "article", "research", "news", "2026"]): priority += 3
                if last and last >= DATE_FLOOR: priority += 2
                kids.append((priority, last or dt.date.min, loc))
        kids.sort(reverse=True)
        out = []
        for _, _, child in kids[:budget]:
            out.extend(sitemap_entries(child, depth + 1, max(1, budget - 1)))
            if len(out) >= 220:
                break
        return out[:220]
    if kind == "urlset":
        out = []
        for node in list(root):
            loc = None; last = None
            for ch in node.iter():
                ln = localname(ch.tag)
                if ln == "loc" and loc is None: loc = (ch.text or "").strip()
                elif ln in {"lastmod", "publication_date"} and last is None: last = parse_date((ch.text or "").strip())
            if loc:
                out.append((loc, last))
        out.sort(key=lambda x: x[1] or dt.date.min, reverse=True)
        return out[:300]
    return []


def page_candidate(url: str, last: dt.date | None) -> bool:
    if last and last < DATE_FLOOR - dt.timedelta(days=30):
        return False
    low = url.lower()
    path_hits = ["publication", "research", "report", "policy", "paper", "brief", "analysis", "foresight", "science", "technology", "innovation", "security", "geopolit", "horizon", "future"]
    return any(k in low for k in path_hits)


def jsonld_objects(obj: Any) -> Iterable[dict]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from jsonld_objects(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from jsonld_objects(v)


def meta_content(soup: BeautifulSoup, keys: list[str]) -> str:
    for key in keys:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key}) or soup.find("meta", attrs={"itemprop": key})
        if tag and tag.get("content"):
            return clean_text(tag.get("content"))
    return ""


def pdf_text(url: str) -> tuple[str, int]:
    try:
        r = SESSION.get(url, timeout=20)
        if r.status_code != 200 or len(r.content) > 18_000_000:
            return "", 0
        reader = PdfReader(io.BytesIO(r.content))
        texts = []
        for page in reader.pages[:45]:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                pass
        txt = clean_text(" ".join(texts))
        return txt, len(txt.split())
    except Exception:
        return "", 0


def parse_institution_page(url: str, source: str, tier: int) -> dict | None:
    r = get(url, timeout=16)
    if not r or "text/html" not in r.headers.get("content-type", "text/html"):
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    title = meta_content(soup, ["og:title", "twitter:title", "headline"]) or clean_text(soup.h1.get_text(" ", strip=True) if soup.h1 else "")
    if not title or excluded(title + " " + url, EXCLUDE_AB):
        return None
    published: dt.date | None = None
    authors: list[str] = []
    description = meta_content(soup, ["description", "og:description", "twitter:description"])
    body_ld = ""
    for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        try:
            data = json.loads(script.string or script.get_text())
        except Exception:
            continue
        for obj in jsonld_objects(data):
            if not published:
                published = parse_date(obj.get("datePublished"))
            if not body_ld and obj.get("articleBody"):
                body_ld = clean_text(obj.get("articleBody"))
            a = obj.get("author")
            if isinstance(a, dict) and a.get("name"): authors.append(clean_text(a["name"]))
            elif isinstance(a, list):
                for au in a:
                    if isinstance(au, dict) and au.get("name"): authors.append(clean_text(au["name"]))
                    elif isinstance(au, str): authors.append(clean_text(au))
    if not published:
        published = parse_date(meta_content(soup, ["article:published_time", "datePublished", "date", "DC.date", "parsely-pub-date", "pubdate"]))
    # Publication date must be verified from page metadata; sitemap lastmod/URL date is not enough.
    if not published or published < DATE_FLOOR:
        return None
    canonical = ""
    can = soup.find("link", rel=lambda v: v and "canonical" in v)
    if can and can.get("href"): canonical = urljoin(r.url, can["href"])
    for bad in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        bad.decompose()
    container = soup.find("article") or soup.find("main") or soup.body
    page_text = body_ld or clean_text(container.get_text(" ", strip=True) if container else "")
    word_count = len(page_text.split())
    pdf_url = ""
    if word_count < 1900:
        for a in soup.find_all("a", href=True):
            href = urljoin(r.url, a["href"])
            label = clean_text(a.get_text(" ", strip=True)).lower()
            if ".pdf" in href.lower() or "download pdf" in label or label == "pdf":
                pdf_url = href; break
        if pdf_url:
            ptxt, pwords = pdf_text(pdf_url)
            if pwords > word_count:
                page_text, word_count = ptxt, pwords
    # Hard exclusion: verified short pieces are dropped, except unusually substantive institutional briefs.
    if word_count and word_count < 1800 and not (tier == 1 and word_count >= 1200):
        return None
    strand, eu, scores = classify(title, description + " " + page_text[:50000], tier)
    if not strand:
        return None
    if tier == 3 and scores.get("eu", 0) < 2.0:
        return None
    th = themes_for(title + " " + description + " " + page_text[:25000])
    typ = "institutional report"
    low = (title + " " + url).lower()
    if "policy brief" in low or "/brief" in low: typ = "policy brief"
    elif "working paper" in low or "discussion paper" in low: typ = "working paper"
    elif "report" not in low and word_count < 3500: typ = "research/policy paper"
    return {
        "title": title,
        "authors": ", ".join(dict.fromkeys(a for a in authors if a)) or source,
        "source": source,
        "date": published.isoformat(),
        "link": pdf_url or canonical or r.url,
        "type": typ,
        "strand": strand,
        "eu_relevance": eu,
        "source_tier": tier,
        "summary": summary_three(title, description + " " + page_text[:30000], strand, th),
        "relevance_note": relevance_note(strand, eu, th),
        "_themes": th,
        "_score": scores,
        "_doi": "",
        "_preprint": False,
    }


def _institution_discovery(source: str, domain: str, tier: int) -> tuple[list[tuple[str, str, int]], str | None]:
    entries: list[tuple[str, dt.date | None]] = []
    for sm in discover_sitemaps(domain):
        got = sitemap_entries(sm)
        if got:
            entries.extend(got)
        if len(entries) >= 120:
            break
    if not entries:
        return [], f"No sitemap: {domain}"
    seen = set()
    chosen: list[tuple[str, str, int]] = []
    for u, last in sorted(entries, key=lambda x: x[1] or dt.date.min, reverse=True):
        if u in seen or not page_candidate(u, last):
            continue
        seen.add(u); chosen.append((u, source, tier))
        if len(chosen) >= 12:
            break
    return chosen, None


def collect_institutions(errors: list[str]) -> list[dict]:
    jobs: list[tuple[str, str, int]] = []
    # Discover sitemaps in parallel so a slow institution does not hold up the first scan.
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(_institution_discovery, source, domain, tier) for source, domain, tier in INSTITUTIONS]
        for fut in cf.as_completed(futs):
            try:
                discovered, err = fut.result()
                jobs.extend(discovered)
                if err: errors.append(err)
            except Exception as e:
                errors.append(f"Institution sitemap: {type(e).__name__}")
    out: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(parse_institution_page, u, s, t):(u,s) for u,s,t in jobs[:220]}
        for fut in cf.as_completed(futs):
            try:
                item = fut.result()
                if item: out.append(item)
            except Exception as e:
                errors.append(f"Institution page: {type(e).__name__}")
    return out


def dedupe_ab(items: list[dict]) -> list[dict]:
    # Prefer DOI identity; otherwise normalized title. Prefer published version over preprint.
    by_key: dict[str, dict] = {}
    for x in items:
        key = x.get("_doi") or norm_title(x.get("title", ""))
        if not key: continue
        old = by_key.get(key)
        if not old:
            by_key[key] = x; continue
        old_pre = bool(old.get("_preprint")); new_pre = bool(x.get("_preprint"))
        if old_pre and not new_pre:
            by_key[key] = x; continue
        # Prefer lower source tier, then richer summary metadata.
        if (x.get("source_tier", 9), -len(x.get("summary", ""))) < (old.get("source_tier", 9), -len(old.get("summary", ""))):
            by_key[key] = x
    # Also drop title-matched preprints when a published version exists under a different DOI.
    pub_titles = {norm_title(x["title"]) for x in by_key.values() if not x.get("_preprint")}
    vals = [x for x in by_key.values() if not (x.get("_preprint") and norm_title(x["title"]) in pub_titles)]
    def rank(x: dict):
        eu_rank = 0 if x.get("eu_relevance") == "direct" else 1
        d = parse_date(x.get("date")) or dt.date.min
        return (eu_rank, int(x.get("source_tier", 9)), -d.toordinal(), -sum(x.get("_score", {}).values()))
    vals.sort(key=rank)
    return vals[:MAX_AB_UNIQUE]


def source_query_name(name: str) -> str:
    return name.replace("|", " ")


def news_queries(domain: str) -> list[str]:
    topic1 = '("research security" OR "economic security" OR "Horizon Europe" OR "research cooperation" OR "science policy" OR "innovation policy")'
    topic2 = '("export controls" OR "dual use" OR "critical technology" OR quantum OR semiconductor OR biotech OR "artificial intelligence" OR foresight)'
    return [f"site:{domain} {topic1} when:1d", f"site:{domain} {topic2} when:1d"]


def factual_news(title: str, desc: str) -> bool:
    if excluded(title, EXCLUDE_C):
        return False
    event_words = [
        "adopt", "approve", "launch", "announce", "suspend", "ban", "restrict", "fund", "invest",
        "sign", "agree", "deal", "delay", "stall", "cancel", "open", "close", "create", "set to",
        "rules", "regulation", "law", "policy", "programme", "program", "data", "survey", "report finds",
        "rises", "falls", "increase", "decrease", "cuts", "expands", "joins", "withdraw", "sanction",
    ]
    full = (title + " " + desc).lower()
    return any(w in full for w in event_words)


def parse_feed_time(entry: Any) -> dt.datetime | None:
    st = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if st:
        return dt.datetime(*st[:6], tzinfo=dt.timezone.utc)
    raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if raw:
        try:
            d = dateparser.parse(raw)
            if d.tzinfo is None: d = d.replace(tzinfo=dt.timezone.utc)
            return d.astimezone(dt.timezone.utc)
        except Exception:
            pass
    return None


def collect_news(now: dt.datetime, errors: list[str]) -> list[dict]:
    start = now - dt.timedelta(hours=NEWS_LOOKBACK_HOURS)
    out = []
    for name, domain in NEWS_SOURCES:
        for q in news_queries(domain):
            url = "https://news.google.com/rss/search?q=" + quote_plus(q) + "&hl=en-GB&gl=GB&ceid=GB:en"
            try:
                r = SESSION.get(url, timeout=15)
                if r.status_code != 200:
                    errors.append(f"Google News {domain}: HTTP {r.status_code}")
                    continue
                feed = feedparser.parse(r.content)
            except Exception as e:
                errors.append(f"Google News {domain}: {type(e).__name__}")
                continue
            for e in feed.entries[:25]:
                when = parse_feed_time(e)
                if not when or when < start or when > now + dt.timedelta(minutes=30):
                    continue
                title = clean_text(getattr(e, "title", ""))
                desc = clean_text(getattr(e, "summary", "") or getattr(e, "description", ""))
                # Google News often appends " - Source" to the title; strip only an exact source suffix.
                for suffix in [name, source_query_name(name)]:
                    if title.lower().endswith(" - " + suffix.lower()):
                        title = title[:-(len(suffix)+3)].strip()
                if not title or not factual_news(title, desc):
                    continue
                out.append({
                    "headline": title,
                    "source": name,
                    "date": when.isoformat(timespec="minutes").replace("+00:00", "Z"),
                    "link": clean_text(getattr(e, "link", "")),
                    "_desc": desc,
                    "_themes": themes_for(title + " " + desc),
                })
    # de-duplicate headline/source combinations
    seen = set(); unique = []
    for x in sorted(out, key=lambda z: z["date"], reverse=True):
        k = (norm_title(x["headline"]), x["source"])
        if k not in seen:
            seen.add(k); unique.append(x)
    return unique


def anchor_news(news: list[dict], ab: list[dict]) -> list[dict]:
    if not ab:
        return []
    theme_counts = Counter(t for x in ab for t in x.get("_themes", []))
    recurring = {t for t, c in theme_counts.items() if c >= 2}
    anchored = []
    for n in news:
        nthemes = set(n.get("_themes", []))
        if not nthemes:
            continue
        ntok = tokens(n["headline"] + " " + n.get("_desc", ""))
        best = None
        for a in ab:
            shared = nthemes & set(a.get("_themes", []))
            if not shared:
                continue
            atok = tokens(a["title"] + " " + a.get("summary", ""))
            j = len(ntok & atok) / max(1, len(ntok | atok))
            score = 2.2 * len(shared) + 5.0 * j
            if best is None or score > best[0]:
                best = (score, a, sorted(shared))
        anchor = ""; score = 0.0; shared_themes: list[str] = []
        if best and best[0] >= 2.25:
            score, a, shared_themes = best
            anchor = f"{a['title']} (Strand {a['strand']})"
        else:
            common = sorted(nthemes & recurring)
            if common:
                score = 2.0 + 0.5 * len(common)
                shared_themes = common
                anchor = f"Recurring A/B theme: {common[0]}"
        if not anchor:
            continue
        low = (n["headline"] + " " + n.get("_desc", "")).lower()
        if any(w in low for w in ["stall", "delay", "cancel", "reverse", "withdraw", "fail", "collapse", "reject"]):
            sig = "contradicts"
        elif any(w in low for w in ["accelerat", "expand", "surge", "increase", "boost", "fast-track", "scale up"]):
            sig = "accelerates"
        elif any(w in low for w in ["data", "survey", "finds", "evidence", "shows", "rise", "fall", "measur"]):
            sig = "confirms"
        else:
            sig = "instantiates"
        desc_sents = sentence_list(n.get("_desc", ""))
        what = desc_sents[0] if desc_sents else n["headline"]
        theme = shared_themes[0] if shared_themes else "the anchored claim"
        why = f"This {sig} the anchor by providing a current empirical development in {theme}."
        item = {k:v for k,v in n.items() if not k.startswith("_")}
        item.update({"anchor": anchor, "signal_type": sig, "signal_note": what.rstrip(". ") + ". " + why, "_anchor_score": score})
        anchored.append(item)
    anchored.sort(key=lambda x: (-x.get("_anchor_score", 0), x.get("date", "")), reverse=False)
    # score descending, then date descending
    anchored = sorted(anchored, key=lambda x: (x.get("_anchor_score", 0), x.get("date", "")), reverse=True)
    for x in anchored:
        x.pop("_anchor_score", None)
    return anchored[:MAX_C]


def public_item(x: dict) -> dict:
    return {k:v for k,v in x.items() if not k.startswith("_")}


def load_previous() -> dict:
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    started = time.time()
    now = dt.datetime.now(dt.timezone.utc)
    errors: list[str] = []
    previous = load_previous()

    crossref = collect_crossref(errors)
    openalex = collect_openalex(errors)
    institutional = collect_institutions(errors)
    raw_ab = crossref + openalex + institutional
    selected = dedupe_ab(raw_ab)

    # If all A/B discovery layers fail at once, keep the prior radar rather than wipe it.
    if not raw_ab and errors and (previous.get("strand_a") or previous.get("strand_b")):
        prior_map: dict[str, dict] = {}
        for x in previous.get("strand_a", []) + previous.get("strand_b", []):
            prior_map[norm_title(x.get("title", ""))] = dict(x)
        selected = list(prior_map.values())[:MAX_AB_UNIQUE]
        for x in selected:
            x.setdefault("_themes", themes_for(x.get("title", "") + " " + x.get("summary", "")))

    strand_a = [public_item(x) for x in selected if x.get("strand") in {"A", "both"}]
    strand_b = [public_item(x) for x in selected if x.get("strand") in {"B", "both"}]

    news_raw = collect_news(now, errors)
    strand_c = anchor_news(news_raw, selected)

    health = "ok"
    # Network/source failures are normal on the open web; mark degraded only if coverage is materially thin.
    if len(raw_ab) == 0 or (len(errors) >= 20 and len(selected) < 3):
        health = "degraded"

    data = {
        "last_updated": now.isoformat(timespec="minutes").replace("+00:00", "Z"),
        "scan_health": health,
        "scan_window": {
            "ab_date_floor": DATE_FLOOR.isoformat(),
            "c_window_start": (now - dt.timedelta(hours=NEWS_LOOKBACK_HOURS)).isoformat(timespec="minutes").replace("+00:00", "Z"),
            "c_window_end": now.isoformat(timespec="minutes").replace("+00:00", "Z"),
        },
        "strand_a": strand_a,
        "strand_b": strand_b,
        "strand_c": strand_c,
        "stats": {
            "ab_candidates_before_ranking": len(raw_ab),
            "ab_unique_selected": len(selected),
            "crossref_candidates": len(crossref),
            "openalex_candidates": len(openalex),
            "institutional_candidates": len(institutional),
            "news_candidates_current_window": len(news_raw),
            "source_errors": len(errors),
            "runtime_seconds": round(time.time() - started, 1),
        },
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data["stats"], indent=2))
    if errors:
        print("Source warnings (first 20):", file=sys.stderr)
        for e in errors[:20]:
            print(" -", e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
