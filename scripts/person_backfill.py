#!/usr/bin/env python3
"""Isolated one-time named-person backfill for the R&I × Geopolitics radar.

This script is deliberately NOT part of the normal scanner mechanism. It never writes
radar.json, never updates scan_state/cursors/backfill flags, and never edits query banks.
It discovers material involving one named person for a bounded historical window and
writes a standalone review JSON that can later be manually reviewed/ingested.

Discovery lanes (all optional/fail-soft):
  * OpenAlex exact author identity (preferred: OpenAlex author ID and/or ORCID)
  * Crossref exact author-name results
  * exact-name Google News RSS search for the bounded window
  * bounded DuckDuckGo HTML discovery + page verification
  * explicitly supplied seed URLs/files

The existing scanner's aboutness functions are reused only as read-only diagnostics.
No normal-scanner state is committed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import scan_radar as radar  # noqa: E402

PROFILE_VERSION = "v1-isolated-person-backfill"
DEFAULT_TIMEOUT = 15
UA = "RI-Geopolitics-Radar-Person-Backfill/1.0"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": UA,
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

INVOLVEMENT_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("author", ("author", "co-author", "coauthor", "written by", "chapter lead", "contributor")),
    ("panel_member", ("panel member", "member of the panel", "appointed to", "elected to", "selected for", "joins un", "scientific panel")),
    ("speaker", ("speaker", "speaks", "gave a public talk", "give a lecture", "gave a lecture", "keynote", "panellist", "panelist")),
    ("adviser", ("adviser", "advisor", "advisory panel", "senior adviser", "expert advisory")),
    ("founder_or_institution_builder", ("co-founder", "cofounder", "founding member", "helped establish", "support of the establishment")),
    ("signatory", ("signatory", "signed", "joint statement")),
    ("project_or_working_group", ("working group", "project member", "participant", "participated", "contributed to")),
    ("award_or_honour", ("honorary doctorate", "honorary doctor", "elected fellow", "award", "prize")),
]

WEB_DISCOVERY_QUERY_TEMPLATES = [
    '"{person}" AI Europe',
    '"{person}" panel OR keynote OR lecture OR advisory OR appointed',
    '"{person}" AI governance OR policy OR competitiveness OR research',
    '"{ascii_person}" AI Europe',
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean(value: Any) -> str:
    return radar.clean_text(value)


def german_transliteration(value: str) -> str:
    table = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"})
    return (value or "").translate(table)


def ascii_fold(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(c))


def norm_person(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", ascii_fold(value).lower()).strip()


def person_name_variants(person: str) -> list[str]:
    canonical = clean(person)
    vals = [canonical, german_transliteration(canonical), ascii_fold(canonical)]
    return list(dict.fromkeys(x for x in vals if x))


def parse_date(value: Any) -> dt.date | None:
    if not value:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dateparser.parse(clean(value), fuzzy=False).date()
    except Exception:
        pass
    m = re.search(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", clean(value))
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def in_window(value: dt.date | None, start: dt.date, end: dt.date) -> bool:
    return bool(value and start <= value <= end)


def extract_page_date(soup: BeautifulSoup, url: str = "") -> dt.date | None:
    candidates: list[str] = []
    for key in (
        "article:published_time", "article:modified_time", "date", "datePublished", "dateModified",
        "parsely-pub-date", "publish-date", "publication_date", "dc.date", "DC.date",
    ):
        node = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if node and node.get("content"):
            candidates.append(clean(node.get("content")))
    for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        try:
            data = json.loads(script.string or script.get_text() or "{}")
        except Exception:
            continue
        objs = data if isinstance(data, list) else [data]
        for obj in objs:
            if isinstance(obj, dict):
                for k in ("datePublished", "dateModified", "uploadDate"):
                    if obj.get(k):
                        candidates.append(clean(obj[k]))
    # Date-like URL paths are useful only as a fallback.
    m = re.search(r"/(20\d{2})/(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])(?:/|$)", url)
    if m:
        candidates.append("-".join(m.groups()))
    m2 = re.search(r"(20\d{2})-(0?[1-9]|1[0-2])-(0?[1-9]|[12]\d|3[01])", url)
    if m2:
        candidates.append("-".join(m2.groups()))
    for c in candidates:
        d = parse_date(c)
        if d:
            return d
    return None


def page_text(soup: BeautifulSoup, limit: int = 40000) -> str:
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    return clean(" ".join(soup.stripped_strings))[:limit]


def exact_person_in_text(text: str, variants: Iterable[str]) -> bool:
    folded = norm_person(text)
    return any(norm_person(v) in folded for v in variants if norm_person(v))


def nearby_excerpt(text: str, variants: Iterable[str], radius: int = 220) -> str:
    low = ascii_fold(text).lower()
    for v in variants:
        needle = ascii_fold(v).lower()
        pos = low.find(needle)
        if pos >= 0:
            start = max(0, pos - radius)
            end = min(len(text), pos + len(v) + radius)
            return clean(text[start:end])[:520]
    return clean(text)[:520]


def involvement_types(text: str, variants: Iterable[str], authors_confirmed: bool = False) -> list[str]:
    out: list[str] = []
    if authors_confirmed:
        out.append("author")
    excerpt = norm_person(nearby_excerpt(text, variants, radius=450))
    for label, terms in INVOLVEMENT_PATTERNS:
        if label == "author" and authors_confirmed:
            continue
        if any(norm_person(t) in excerpt for t in terms):
            out.append(label)
    if not out and exact_person_in_text(text, variants):
        out.append("named_in_source")
    return list(dict.fromkeys(out))


def source_tier_for_url(url: str) -> int:
    domain = radar.url_domain(url)
    hit = radar.institution_source_for_domain(domain)
    if hit:
        return int(hit[1])
    # Person backfill is review-only: unknown external institutional sources are not
    # promoted to Tier 1 automatically. Tier 2 keeps diagnostics conservative.
    return 2


def existing_radar_index(radar_json: dict[str, Any]) -> tuple[set[str], set[str]]:
    identities: set[str] = set()
    links: set[str] = set()
    for strand in ("strand_a", "strand_b", "strand_c"):
        for item in radar_json.get(strand, []) or []:
            title = clean(item.get("title") or item.get("headline"))
            link = clean(item.get("link"))
            if title:
                identities.add(radar.stable_item_identity(title, link))
                identities.add("title:" + radar.norm_title(title))
            if link:
                links.add(radar.normalized_link(link))
    return identities, links


def duplicate_status(record: dict[str, Any], identities: set[str], links: set[str]) -> dict[str, Any]:
    title = clean(record.get("title"))
    url = clean(record.get("url"))
    doi = clean(record.get("doi"))
    key = radar.stable_item_identity(title, doi or url)
    by_identity = key in identities or (title and ("title:" + radar.norm_title(title)) in identities)
    by_link = bool(url and radar.normalized_link(url) in links)
    return {"existing_corpus": bool(by_identity or by_link), "identity_match": by_identity, "link_match": by_link}


def gate_diagnostic(record: dict[str, Any]) -> dict[str, Any]:
    title = clean(record.get("title"))
    abstract = clean(record.get("abstract"))
    body = clean(record.get("body"))[:16000]
    source_kind = "scholarly" if record.get("record_kind") == "scholarly" else "general"
    tier = int(record.get("source_tier") or 2)
    text = clean(f"{title}. {abstract}. {body}")
    try:
        ev = radar.gate_scope(title, abstract, body, tier, source_kind=source_kind)
    except Exception as e:
        ev = {"a_pass": False, "b_pass": False, "aboutness_reason": f"diagnostic_error:{type(e).__name__}"}
    exclusion = ""
    try:
        exclusion = clean(radar.document_exclusion_reason(title, abstract or body))
    except Exception:
        pass
    signal = {
        "eu_scope": bool(radar.eu_news_scope(text)),
        "strong_watch_signal": bool(radar.strong_watch_signal_text(text)),
        "material_update": bool(radar.material_update_signal_text(text)),
        "reframing_evidence": bool(radar.reframing_signal_text(text)),
        "weak_signal_candidate": bool(radar.weak_signal_candidate_text(title, abstract or body)),
    }
    if record.get("dedupe", {}).get("existing_corpus"):
        recommendation = "already_in_radar"
    elif record.get("record_kind") == "scholarly" and (ev.get("a_pass") or ev.get("b_pass")) and not exclusion:
        recommendation = "manual_ingest_review_A_or_B"
    elif record.get("record_kind") != "scholarly" and signal["strong_watch_signal"] and (signal["material_update"] or signal["reframing_evidence"]):
        recommendation = "manual_review_C_signal"
    elif record.get("record_kind") != "scholarly" and not exclusion and (ev.get("a_pass") or ev.get("b_pass")):
        recommendation = "manual_ingest_review_A_or_B"
    elif not text or len(text.split()) < 25:
        recommendation = "defer_insufficient_text"
    else:
        recommendation = "context_only_or_reject"
    return {"ab_gate": ev, "document_exclusion_reason": exclusion, "signal_tests": signal, "recommendation": recommendation}


def make_id(record: dict[str, Any]) -> str:
    base = "|".join([clean(record.get("title")), clean(record.get("url")), clean(record.get("date"))])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def authors_from_openalex(work: dict[str, Any]) -> list[str]:
    out = []
    for a in work.get("authorships") or []:
        n = clean((a.get("author") or {}).get("display_name"))
        if n:
            out.append(n)
    return out


def resolve_openalex_author(person: str, orcid: str, explicit_id: str, warnings: list[str], timeout: int) -> str:
    if explicit_id:
        return explicit_id.rsplit("/", 1)[-1].upper()
    try:
        params = {"search": person, "per-page": 10}
        r = SESSION.get("https://api.openalex.org/authors", params=params, timeout=timeout)
        if r.status_code != 200:
            warnings.append(f"OpenAlex author resolution HTTP {r.status_code}")
            return ""
        wanted = norm_person(person)
        orcid_clean = orcid.replace("https://orcid.org/", "").lower().strip()
        candidates = []
        for a in r.json().get("results", []):
            score = 0
            if norm_person(clean(a.get("display_name"))) == wanted:
                score += 10
            a_orcid = clean(a.get("orcid")).replace("https://orcid.org/", "").lower()
            if orcid_clean and a_orcid == orcid_clean:
                score += 100
            if score:
                candidates.append((score, a))
        if not candidates:
            warnings.append("OpenAlex author resolution found no exact identity match")
            return ""
        candidates.sort(key=lambda x: x[0], reverse=True)
        return clean(candidates[0][1].get("id")).rsplit("/", 1)[-1].upper()
    except Exception as e:
        warnings.append(f"OpenAlex author resolution {type(e).__name__}")
        return ""


def discover_openalex(person: str, variants: list[str], author_id: str, orcid: str,
                      start: dt.date, end: dt.date, warnings: list[str], timeout: int,
                      max_records: int) -> list[dict[str, Any]]:
    author_id = resolve_openalex_author(person, orcid, author_id, warnings, timeout)
    if not author_id:
        return []
    records: list[dict[str, Any]] = []
    cursor = "*"
    attempts = 0
    # Both filter spellings have existed in OpenAlex examples; try the nested form first,
    # and automatically fall back to the shortcut on a 400.
    author_filters = [f"authorships.author.id:{author_id}", f"author.id:{author_id}"]
    selected_filter = author_filters[0]
    while len(records) < max_records and attempts < 20:
        attempts += 1
        params = {
            "filter": f"{selected_filter},from_publication_date:{start.isoformat()},to_publication_date:{end.isoformat()}",
            "per-page": min(100, max_records),
            "cursor": cursor,
        }
        try:
            r = SESSION.get("https://api.openalex.org/works", params=params, timeout=timeout)
            if r.status_code == 400 and selected_filter == author_filters[0]:
                selected_filter = author_filters[1]
                attempts -= 1
                continue
            if r.status_code != 200:
                warnings.append(f"OpenAlex works HTTP {r.status_code}")
                break
            data = r.json()
        except Exception as e:
            warnings.append(f"OpenAlex works {type(e).__name__}")
            break
        for work in data.get("results", []):
            d = parse_date(work.get("publication_date"))
            if not in_window(d, start, end):
                continue
            authors = authors_from_openalex(work)
            if not any(norm_person(a) == norm_person(person) for a in authors):
                # The ID filter is already strong identity evidence, but preserve the anomaly.
                warnings.append(f"OpenAlex author-ID hit lacked exact display name: {clean(work.get('display_name'))[:100]}")
            doi = clean(work.get("doi"))
            locations = radar.openalex_locations(work)
            url = doi or (locations[0] if locations else clean(work.get("id")))
            abstract = radar.openalex_abstract(work.get("abstract_inverted_index"))
            rec = {
                "record_kind": "scholarly",
                "discovery_lanes": ["openalex_exact_author_id"],
                "title": clean(work.get("display_name") or work.get("title")),
                "date": d.isoformat(),
                "url": url,
                "doi": doi,
                "source": clean(((work.get("primary_location") or {}).get("source") or {}).get("display_name")) or "OpenAlex",
                "source_tier": 2,
                "authors": authors,
                "abstract": abstract,
                "body": "",
                "person_involvement": {
                    "confirmed": True,
                    "types": ["author"],
                    "evidence": f"Exact OpenAlex author identity {author_id} is attached to the work.",
                },
                "external_ids": {"openalex_work_id": clean(work.get("id")), "openalex_author_id": author_id, "orcid": orcid},
            }
            records.append(rec)
            if len(records) >= max_records:
                break
        meta = data.get("meta") or {}
        next_cursor = clean(meta.get("next_cursor"))
        if not next_cursor or next_cursor == cursor or not data.get("results"):
            break
        cursor = next_cursor
    return records


def crossref_authors(item: dict[str, Any]) -> list[str]:
    out = []
    for a in item.get("author") or []:
        name = clean(" ".join(x for x in [a.get("given", ""), a.get("family", "")] if x))
        if name:
            out.append(name)
    return out


def discover_crossref(person: str, start: dt.date, end: dt.date, warnings: list[str], timeout: int,
                      max_records: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    offset = 0
    rows = min(100, max_records)
    wanted = norm_person(person)
    while len(out) < max_records and offset < 1000:
        params = {
            "query.author": person,
            "filter": f"from-pub-date:{start.isoformat()},until-pub-date:{end.isoformat()}",
            "rows": rows,
            "offset": offset,
            "select": "DOI,title,author,publisher,container-title,published-online,published-print,published,issued,type,URL,abstract,score",
        }
        try:
            r = SESSION.get("https://api.crossref.org/works", params=params, timeout=timeout)
            if r.status_code != 200:
                warnings.append(f"Crossref HTTP {r.status_code}")
                break
            items = (r.json().get("message") or {}).get("items", [])
        except Exception as e:
            warnings.append(f"Crossref {type(e).__name__}")
            break
        if not items:
            break
        for item in items:
            authors = crossref_authors(item)
            if wanted not in {norm_person(a) for a in authors}:
                continue
            d = radar.crossref_date(item)
            if not in_window(d, start, end):
                continue
            title_raw = item.get("title") or [""]
            title = clean(title_raw[0] if isinstance(title_raw, list) else title_raw)
            doi = clean(item.get("DOI"))
            url = "https://doi.org/" + doi if doi and not doi.lower().startswith("http") else (doi or clean(item.get("URL")))
            container = item.get("container-title") or []
            source = clean(container[0] if isinstance(container, list) and container else container) or clean(item.get("publisher")) or "Crossref"
            out.append({
                "record_kind": "scholarly",
                "discovery_lanes": ["crossref_exact_author_name"],
                "title": title,
                "date": d.isoformat(),
                "url": url,
                "doi": doi,
                "source": source,
                "source_tier": 2,
                "authors": authors,
                "abstract": clean(item.get("abstract")),
                "body": "",
                "person_involvement": {"confirmed": True, "types": ["author"], "evidence": "Exact normalized author-name match in Crossref metadata."},
                "external_ids": {"doi": doi},
            })
            if len(out) >= max_records:
                break
        offset += len(items)
        if len(items) < rows:
            break
    return out


def decode_ddg_url(href: str) -> str:
    href = html.unescape(clean(href))
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        qs = parse_qs(parsed.query)
        if qs.get("uddg"):
            return unquote(qs["uddg"][0])
    return href


def ddg_search(query: str, timeout: int, warnings: list[str]) -> list[str]:
    try:
        r = SESSION.get("https://html.duckduckgo.com/html/", params={"q": query}, timeout=timeout)
        if r.status_code != 200:
            warnings.append(f"DuckDuckGo HTTP {r.status_code}")
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        urls = []
        for a in soup.select("a.result__a, a.result-link"):
            u = decode_ddg_url(a.get("href", ""))
            if u.startswith("http") and u not in urls:
                urls.append(u)
        return urls
    except Exception as e:
        warnings.append(f"DuckDuckGo {type(e).__name__}")
        return []


def google_news_records(person: str, variants: list[str], start: dt.date, end: dt.date,
                        timeout: int, warnings: list[str], max_records: int) -> list[dict[str, Any]]:
    query = f'"{person}" after:{start.isoformat()} before:{(end + dt.timedelta(days=1)).isoformat()}'
    url = "https://news.google.com/rss/search?q=" + quote_plus(query) + "&hl=en-GB&gl=GB&ceid=GB:en"
    try:
        r = SESSION.get(url, timeout=timeout)
        if r.status_code != 200:
            warnings.append(f"Google News person query HTTP {r.status_code}")
            return []
        feed = radar.feedparser.parse(r.content)
    except Exception as e:
        warnings.append(f"Google News person query {type(e).__name__}")
        return []
    out = []
    for e in feed.entries[:max_records]:
        when = radar.parse_feed_time(e)
        if not when or not in_window(when.date(), start, end):
            continue
        title = clean(getattr(e, "title", ""))
        desc = clean(getattr(e, "summary", "") or getattr(e, "description", ""))
        text = f"{title}. {desc}"
        if not exact_person_in_text(text, variants):
            continue
        source_name, source_domain = radar.feed_source(e, "", "")
        kinds = involvement_types(text, variants)
        out.append({
            "record_kind": "web",
            "discovery_lanes": ["google_news_exact_name"],
            "title": title,
            "date": when.date().isoformat(),
            "url": clean(getattr(e, "link", "")),
            "source": source_name or source_domain or "Google News source",
            "source_tier": 2,
            "authors": [],
            "abstract": desc,
            "body": "",
            "person_involvement": {"confirmed": True, "types": kinds, "evidence": nearby_excerpt(text, variants)},
        })
    return out


def fetch_verified_web_record(url: str, variants: list[str], start: dt.date, end: dt.date,
                              timeout: int, warnings: list[str], lane: str) -> dict[str, Any] | None:
    try:
        r = SESSION.get(url, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            warnings.append(f"Web fetch HTTP {r.status_code}: {url[:140]}")
            return None
        ctype = clean(r.headers.get("Content-Type")).lower()
        if "html" not in ctype and not r.text.lstrip().startswith("<"):
            return None
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        warnings.append(f"Web fetch {type(e).__name__}: {url[:140]}")
        return None
    title = clean((soup.find("meta", attrs={"property": "og:title"}) or {}).get("content") if soup.find("meta", attrs={"property": "og:title"}) else "")
    if not title:
        title = clean(soup.title.get_text(" ", strip=True) if soup.title else "")
    body = page_text(soup)
    if not exact_person_in_text(body, variants):
        return None
    d = extract_page_date(soup, r.url)
    # Keep undated pages only as verification-required context; dated pages outside the
    # requested window are dropped.
    if d and not in_window(d, start, end):
        return None
    kinds = involvement_types(body, variants)
    if kinds == ["named_in_source"]:
        # A mere mention is not enough for a person-involvement backfill.
        return None
    domain = radar.url_domain(r.url)
    return {
        "record_kind": "web",
        "discovery_lanes": [lane],
        "title": title or r.url,
        "date": d.isoformat() if d else "",
        "url": r.url,
        "source": domain,
        "source_tier": source_tier_for_url(r.url),
        "authors": [],
        "abstract": "",
        "body": body[:16000],
        "person_involvement": {
            "confirmed": True,
            "types": kinds,
            "evidence": nearby_excerpt(body, variants),
            "date_verification_required": d is None,
        },
    }


def load_seed_urls(seed_files: list[Path], direct_urls: list[str], warnings: list[str]) -> list[str]:
    urls = list(direct_urls)
    for path in seed_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            warnings.append(f"Seed file {path.name}: {type(e).__name__}")
            continue
        vals = data.get("urls", data) if isinstance(data, dict) else data
        if not isinstance(vals, list):
            warnings.append(f"Seed file {path.name}: expected list or {{'urls': [...]}}")
            continue
        for x in vals:
            u = clean(x.get("url") if isinstance(x, dict) else x)
            if u:
                urls.append(u)
    return list(dict.fromkeys(u for u in urls if u.startswith("http")))


def discover_web(person: str, variants: list[str], start: dt.date, end: dt.date, warnings: list[str],
                 timeout: int, seed_urls: list[str], max_pages: int) -> list[dict[str, Any]]:
    out = google_news_records(person, variants, start, end, timeout, warnings, max_pages)
    ascii_person = ascii_fold(person)
    urls = list(seed_urls)
    for tmpl in WEB_DISCOVERY_QUERY_TEMPLATES:
        query = tmpl.format(person=person, ascii_person=ascii_person) + f" {start.year}..{end.year}"
        urls.extend(ddg_search(query, timeout, warnings))
    # Avoid social/profile/search pages and duplicate URLs before page fetching.
    blocked = ("linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com")
    unique = []
    for u in urls:
        if any(d in radar.url_domain(u) for d in blocked):
            continue
        if u not in unique:
            unique.append(u)
    for u in unique[:max_pages]:
        rec = fetch_verified_web_record(u, variants, start, end, timeout, warnings, "seed_or_web_exact_name")
        if rec:
            out.append(rec)
    return out


def merge_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for rec in records:
        key = radar.stable_item_identity(clean(rec.get("title")), clean(rec.get("doi")) or clean(rec.get("url")))
        if key in buckets:
            cur = buckets[key]
            cur["discovery_lanes"] = list(dict.fromkeys((cur.get("discovery_lanes") or []) + (rec.get("discovery_lanes") or [])))
            if len(clean(rec.get("abstract"))) > len(clean(cur.get("abstract"))):
                cur["abstract"] = rec.get("abstract", "")
            if len(clean(rec.get("body"))) > len(clean(cur.get("body"))):
                cur["body"] = rec.get("body", "")
            cur_types = (cur.get("person_involvement") or {}).get("types", [])
            new_types = (rec.get("person_involvement") or {}).get("types", [])
            cur.setdefault("person_involvement", {})["types"] = list(dict.fromkeys(cur_types + new_types))
            continue
        buckets[key] = rec
    return list(buckets.values())


def finalize_records(records: list[dict[str, Any]], identities: set[str], links: set[str],
                     start: dt.date, end: dt.date) -> list[dict[str, Any]]:
    out = []
    for rec in merge_records(records):
        d = parse_date(rec.get("date"))
        if d and not in_window(d, start, end):
            continue
        rec["dedupe"] = duplicate_status(rec, identities, links)
        rec["radar_review"] = gate_diagnostic(rec)
        rec["candidate_id"] = make_id(rec)
        rec.pop("body", None)  # review output stores only compact evidence, not copied page bodies
        out.append(rec)
    priority = {
        "manual_ingest_review_A_or_B": 0,
        "manual_review_C_signal": 1,
        "defer_insufficient_text": 2,
        "context_only_or_reject": 3,
        "already_in_radar": 4,
    }
    out.sort(key=lambda r: (priority.get((r.get("radar_review") or {}).get("recommendation"), 9), r.get("date") or "9999"))
    return out


def default_output(person: str, start: dt.date, end: dt.date) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_fold(person).lower()).strip("_")
    return ROOT / "manual_inputs" / f"person_backfill_{slug}_{start.isoformat()}_{end.isoformat()}.json"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Isolated one-time person-centric backfill. Never modifies radar.json.")
    p.add_argument("--person", required=True)
    p.add_argument("--from", dest="from_date", required=True, help="YYYY-MM-DD inclusive")
    p.add_argument("--to", dest="to_date", required=True, help="YYYY-MM-DD inclusive")
    p.add_argument("--openalex-author-id", default="")
    p.add_argument("--orcid", default="")
    p.add_argument("--no-openalex", action="store_true")
    p.add_argument("--no-crossref", action="store_true")
    p.add_argument("--web", action="store_true", help="Enable exact-name web/news discovery (fail-soft).")
    p.add_argument("--seed-file", action="append", default=[], help="JSON list/object of seed URLs; may be repeated.")
    p.add_argument("--seed-url", action="append", default=[], help="Explicit seed URL; may be repeated.")
    p.add_argument("--max-scholarly", type=int, default=200)
    p.add_argument("--max-web-pages", type=int, default=60)
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--output", default="")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    start = parse_date(args.from_date)
    end = parse_date(args.to_date)
    if not start or not end or start > end:
        raise SystemExit("Invalid --from/--to window")
    radar_path = ROOT / "radar.json"
    before_hash = sha256_file(radar_path)
    radar_json = json.loads(radar_path.read_text(encoding="utf-8"))
    identities, links = existing_radar_index(radar_json)
    warnings: list[str] = []
    variants = person_name_variants(args.person)
    records: list[dict[str, Any]] = []

    if not args.no_openalex:
        records.extend(discover_openalex(args.person, variants, args.openalex_author_id, args.orcid, start, end,
                                        warnings, args.timeout, args.max_scholarly))
    if not args.no_crossref:
        records.extend(discover_crossref(args.person, start, end, warnings, args.timeout, args.max_scholarly))

    seed_files = [Path(x).expanduser().resolve() for x in args.seed_file]
    seed_urls = load_seed_urls(seed_files, args.seed_url, warnings)
    if args.web or seed_urls:
        records.extend(discover_web(args.person, variants, start, end, warnings, args.timeout, seed_urls, args.max_web_pages))

    final = finalize_records(records, identities, links, start, end)
    after_hash = sha256_file(radar_path)
    unchanged = before_hash == after_hash
    if not unchanged:
        raise RuntimeError("Isolation invariant failed: radar.json changed during person backfill")

    counts = defaultdict(int)
    for rec in final:
        counts[(rec.get("radar_review") or {}).get("recommendation", "unknown")] += 1
    output = Path(args.output).expanduser().resolve() if args.output else default_output(args.person, start, end)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "profile_version": PROFILE_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "person": {
            "name": args.person,
            "name_variants": variants,
            "openalex_author_id": args.openalex_author_id,
            "orcid": args.orcid,
        },
        "window": {"from": start.isoformat(), "to": end.isoformat(), "inclusive": True},
        "isolation": {
            "writes_to_radar": False,
            "normal_scan_state_touched": False,
            "query_banks_modified": False,
            "radar_sha256_before": before_hash,
            "radar_sha256_after": after_hash,
            "radar_unchanged": unchanged,
        },
        "discovery": {
            "openalex_enabled": not args.no_openalex,
            "crossref_enabled": not args.no_crossref,
            "web_enabled": bool(args.web),
            "seed_urls": len(seed_urls),
            "records_after_dedupe": len(final),
            "recommendation_counts": dict(sorted(counts.items())),
            "warnings": list(dict.fromkeys(warnings))[:100],
        },
        "records": final,
        "review_note": (
            "This is a recovery/review artifact only. A named-person match is discovery evidence, not an admission rule. "
            "Only records that independently satisfy the radar's existing A/B/C criteria should be manually ingested."
        ),
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "records": len(final), "recommendations": dict(counts), "radar_unchanged": unchanged}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
