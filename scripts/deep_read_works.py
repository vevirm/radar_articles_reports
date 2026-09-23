#!/usr/bin/env python3
"""Shared Deep Scan helpers.

Deep Scan is deliberately *offline from paid model APIs*.

The automatic scanner stores provisional raw evidence in ``radar.json``. A manual
GitHub workflow packages records for a much stricter Deep Scan V2. The user can
give that ZIP to a capable browsing LLM subscription, then upload the returned
result file to ``deep_scan_inbox``. GitHub validates the result before allowing it
to affect reader language, admission, metadata or downstream reasoning.

This module holds shared record identity, source-reading and reader-text validation
logic. It makes no model/API calls and needs no AI API key. Only the authoritative
Deep Scan V2 profile counts as complete; older Deep Scan interpretations remain
available during migration but are deliberately queued once for V2 verification.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

CORPUS = Path("radar.json")
SIDECAR = Path("reader_text.json")
STRANDS = ("strand_a", "strand_b", "strand_c", "frontier_evidence")
WORD_CAP = {"what": 20, "why": 20, "title": 18}
MORE_WORD_CAP = 135
NEAR_DUPLICATE = 0.86
SOURCE_CHAR_CAP = 24000
PDF_PAGE_CAP = 10
HTTP_TIMEOUT = 12
USER_AGENT = "Mozilla/5.0 (compatible; RI-Geopolitics-Radar-DeepScan/3.1; +https://vevirm.github.io/radar_articles_reports/)"
OPENALEX_API_ROOT = "https://api.openalex.org"
OPENALEX_MAX_LOCATION_ROUTES = 10
ACTIVE_DEEP_PROFILES = {"deep-reader-v2-authoritative"}
LEGACY_DEEP_PROFILES = {"deep-reader-v2", "deep-reader-v2.1", "deep-reader-offline-v1"}


def clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def record_key(r: dict[str, Any]) -> str:
    # Historical Deep Scan rows carry an explicit namespaced identity so they can
    # never collide with a Main Radar record that happens to use the same URL/DOI.
    explicit = clean(r.get("_deep_scan_record_key"))
    if explicit:
        return explicit
    link = clean(r.get("link") or r.get("url"))
    if link:
        return f"link:{link}"
    doi = clean(r.get("doi")).lower()
    if doi:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
        return f"doi:{doi}"
    rid = clean(r.get("id") or r.get("record_id") or r.get("fingerprint"))
    return f"id:{rid}" if rid else ""


def historical_record_key(r: dict[str, Any]) -> str:
    """Stable, collision-proof Deep Scan identity for a Historical Radar row.

    Historical rows already have durable archive ids, so prefer those over URLs.
    Fallbacks exist for older/manual archive rows that may not have an id.
    """
    rid = clean(r.get("id") or r.get("record_id") or r.get("fingerprint"))
    if rid:
        return f"historical:id:{rid}"
    doi = clean(r.get("doi")).lower()
    if doi:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
        return f"historical:doi:{doi}"
    link = clean(r.get("link") or r.get("url"))
    return f"historical:link:{link}" if link else ""


def iter_historical_records(doc: dict[str, Any]):
    """Yield Historical Radar rows as non-mutating, namespaced Deep Scan rows."""
    rows = doc.get("items", []) if isinstance(doc, dict) else []
    for raw in rows if isinstance(rows, list) else []:
        if not isinstance(raw, dict):
            continue
        key = historical_record_key(raw)
        if not key:
            continue
        row = dict(raw)
        row["_deep_scan_record_key"] = key
        row["_deep_scan_scope"] = "historical"
        strand = clean(raw.get("strand")).upper()
        label = f"historical_{strand.lower()}" if strand in {"A", "B", "C"} else "historical_unclassified"
        yield label, row


def historical_pending(
    doc: dict[str, Any],
    sidecar: dict[str, Any],
) -> list[tuple[str, str, str, dict[str, Any], str]]:
    """Return Historical Radar works still needing authoritative Deep Scan V2.

    Historical work uses a separate key namespace and remains behind Main Radar in
    scheduling; the latter policy is enforced by ``deep_scan_work_state``.
    """
    out: list[tuple[str, str, str, dict[str, Any], str]] = []
    table = sidecar.get("records", {}) if isinstance(sidecar, dict) else {}
    seen_keys: set[str] = set()
    for strand, row in iter_historical_records(doc):
        key = record_key(row)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        old = table.get(key) if isinstance(table, dict) else None
        if isinstance(old, dict) and old.get("profile") in ACTIVE_DEEP_PROFILES:
            continue
        reason = (
            "upgrade_legacy_deep_scan_to_v2"
            if isinstance(old, dict) and old.get("profile") in LEGACY_DEEP_PROFILES
            else "never_deep_read"
        )
        out.append((strand, key, source_hash(row), row, reason))
    return out


def identity_hash(r: dict[str, Any]) -> str:
    """Stable hash of the record identity used by Deep Scan V2.

    V2 can take longer than an automatic scan interval, so semantic scanner wording
    is allowed to change while a package is being worked. The stable record key must
    still resolve to the same raw evidence object.
    """
    key = record_key(r)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16] if key else ""


def source_hash(r: dict[str, Any]) -> str:
    """FNV-1a over semantic source fields for export/import race protection.

    This is not a security hash and it does *not* make an already imported Deep
    Scan result expire. It is copied into an exported job so GitHub can reject a
    returned result if the underlying record changed between package creation and
    import. Once a Deep Scan result is imported, that work stays complete.
    """
    fields = (
        "title", "headline", "summary", "signal_note", "core_message", "what",
        "relevance_note", "why_it_matters", "bridge_sentence", "external_eu_bridge",
        "source", "type", "signal_kind", "event_status", "text_mode",
    )
    material = "\n".join(clean(r.get(k)) for k in fields)
    h = 0x811C9DC5
    raw = material.encode("utf-16le", "surrogatepass")
    for i in range(0, len(raw), 2):
        code_unit = raw[i] | (raw[i + 1] << 8)
        h ^= code_unit
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def iter_records(doc: dict[str, Any]):
    for strand in STRANDS:
        for r in doc.get(strand, []) or []:
            if isinstance(r, dict):
                yield strand, r


def load_sidecar(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 2, "profile": "deep-reader-offline-v1", "generated_at": None, "records": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Refusing to overwrite unreadable sidecar: {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("records"), dict):
        raise SystemExit(f"Invalid sidecar structure: {path}")
    return data


def _date_key(r: dict[str, Any]) -> str:
    return clean(r.get("date") or r.get("c_event_date") or r.get("first_seen"))


def pending(
    doc: dict[str, Any],
    sidecar: dict[str, Any],
    refresh_stale: bool | None = None,
) -> list[tuple[str, str, str, dict[str, Any], str]]:
    """Return works that have never received a valid Deep Scan interpretation.

    `refresh_stale` is retained only for compatibility with older local commands
    and is intentionally ignored. A work that already has an active Deep Scan
    profile is complete and will not be queued again automatically, even if the
    fast scanner later changes stored wording or metadata.
    """
    out: list[tuple[str, str, str, dict[str, Any], str]] = []
    table = sidecar.get("records", {})
    seen_keys: set[str] = set()
    for strand, r in iter_records(doc):
        key = record_key(r)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        old = table.get(key)
        h = source_hash(r)
        if not old or old.get("profile") not in ACTIVE_DEEP_PROFILES:
            # V2 is intentionally a one-time re-verification of the whole legacy
            # corpus. Existing V1 prose remains usable while migration proceeds,
            # but it is not authoritative for admission/provenance/reasoning.
            reason = "upgrade_legacy_deep_scan_to_v2" if isinstance(old, dict) and old.get("profile") in LEGACY_DEEP_PROFILES else "never_deep_read"
            out.append((strand, key, h, r, reason))

    # Deep Scan V2 is a FIFO verification queue. Legacy rows with no ``first_seen``
    # are deliberately treated as the oldest backlog. Rows with ``first_seen`` are
    # processed oldest-discovered first across A/B/C, so newly discovered scanner
    # records enter the Radar provisionally but wait behind work already queued.
    # Python's sort is stable, preserving repository order for equal timestamps.
    def queue_key(item: tuple[str, str, str, dict[str, Any], str]) -> tuple[int, str]:
        first_seen = clean(item[3].get("first_seen"))
        return (0, "") if not first_seen else (1, first_seen)

    out.sort(key=queue_key)
    return out


@dataclass
class SourceRead:
    mode: str
    text: str
    final_url: str = ""
    note: str = ""


def _safe_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in {"http", "https"} and bool(p.netloc)
    except Exception:
        return False


def _pdf_text(payload: bytes) -> str:
    """Take a balanced excerpt from the beginning and end of a PDF.

    The first pages usually contain the abstract/introduction; the final pages
    often contain discussion/conclusions. This is more useful to a deep reader
    than blindly taking only the first N pages, while keeping the package small.
    """
    reader = PdfReader(io.BytesIO(payload))
    n = len(reader.pages)
    if not n:
        return ""
    front_n = min(6, n)
    tail_n = min(4, max(0, n - front_n))
    indices = list(range(front_n))
    if tail_n:
        indices.extend(range(max(front_n, n - tail_n), n))
    chunks: list[str] = []
    for idx in indices[:PDF_PAGE_CAP]:
        try:
            text = clean(reader.pages[idx].extract_text() or "")
        except Exception:
            text = ""
        if text:
            chunks.append(f"[PDF page {idx + 1}] {text}")
        if sum(len(x) for x in chunks) >= SOURCE_CHAR_CAP:
            break
    return "\n\n".join(chunks)[:SOURCE_CHAR_CAP]


def _html_text(payload: bytes, encoding: str | None = None) -> str:
    soup = BeautifulSoup(payload, "html.parser", from_encoding=encoding)
    preferred: list[str] = []
    for attrs in (
        {"name": "citation_abstract"}, {"name": "dc.description"},
        {"name": "description"}, {"property": "og:description"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and clean(tag.get("content")):
            preferred.append(clean(tag.get("content")))
    for selector in ("abstract", "#abstract", ".abstract", "[class*='abstract']"):
        try:
            for node in soup.select(selector)[:4]:
                text = clean(node.get_text(" ", strip=True))
                if len(text) >= 120:
                    preferred.append(text)
        except Exception:
            pass
    for node in soup(["script", "style", "noscript", "nav", "footer", "header", "form", "svg"]):
        node.decompose()
    body_parts: list[str] = []
    total = sum(len(x) for x in preferred)
    for node in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = clean(node.get_text(" ", strip=True))
        if len(text) < 35:
            continue
        if re.search(r"cookie|privacy policy|accept all|sign in|subscribe|javascript", text, re.I):
            continue
        body_parts.append(text)
        total += len(text)
        if total >= SOURCE_CHAR_CAP:
            break
    return "\n".join(dict.fromkeys(preferred + body_parts))[:SOURCE_CHAR_CAP]


def fetch_source(url: str, *, extra_headers: dict[str, str] | None = None) -> SourceRead:
    """Best-effort source retrieval. Failure never blocks package creation."""
    if not _safe_url(url):
        return SourceRead("stored_only", "", note="no usable http(s) source link")
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.5"}
    if extra_headers:
        headers.update({str(k): str(v) for k, v in extra_headers.items() if clean(k) and clean(v)})
    try:
        with requests.get(url, headers=headers, timeout=HTTP_TIMEOUT, allow_redirects=True, stream=True) as resp:
            resp.raise_for_status()
            ctype = clean(resp.headers.get("content-type")).lower()
            chunks: list[bytes] = []
            total = 0
            max_bytes = 20 * 1024 * 1024
            for chunk in resp.iter_content(65536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    break
                chunks.append(chunk)
            payload = b"".join(chunks)
            final_url = clean(resp.url)
            if "pdf" in ctype or final_url.lower().split("?", 1)[0].endswith(".pdf") or payload[:5] == b"%PDF-":
                text = _pdf_text(payload)
                return SourceRead("pdf_excerpt" if len(text) >= 300 else "stored_only", text, final_url, "")
            text = _html_text(payload, resp.encoding)
            if len(text) >= 2500:
                mode = "substantial_web_text"
            elif len(text) >= 180:
                mode = "abstract_or_landing_page"
            else:
                mode = "stored_only"
            return SourceRead(mode, text, final_url, "")
    except Exception as exc:
        return SourceRead("stored_only", "", note=f"source retrieval failed: {clean(exc)[:180]}")


def _record_doi(r: dict[str, Any]) -> str:
    value = clean(r.get("doi"))
    if not value:
        link = clean(r.get("link") or r.get("url"))
        m = re.search(r"doi\.org/(10\.\d{4,9}/[^?#\s]+)", link, re.I)
        value = m.group(1) if m else ""
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I).strip().rstrip("/")


def _openalex_work_for_record(r: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Authenticated exact-DOI OpenAlex lookup used only by Deep Scan package preparation.

    The API key is read from the Actions environment and is never returned, logged,
    written to package files, or placed in a URL.  DOI-only matching deliberately
    avoids injecting a similarly titled but different work into authoritative review.
    """
    api_key = clean(os.environ.get("OPENALEX_API_KEY"))
    doi = _record_doi(r)
    if not api_key:
        return None, "OpenAlex recovery unavailable: OPENALEX_API_KEY not configured"
    if not doi:
        return None, "OpenAlex recovery not applicable: no DOI on record"
    try:
        resp = requests.get(
            f"{OPENALEX_API_ROOT}/works",
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            params={
                "filter": f"doi:https://doi.org/{doi}",
                "per_page": "1",
                "select": "id,doi,display_name,publication_year,primary_location,best_oa_location,locations,has_content,content_urls",
            },
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        rows = (resp.json() or {}).get("results") or []
        work = rows[0] if rows and isinstance(rows[0], dict) else None
        if not work:
            return None, f"OpenAlex authenticated DOI lookup found no work for {doi}"
        work_id = clean(work.get("id")).rsplit("/", 1)[-1]
        return work, f"OpenAlex authenticated DOI lookup matched {work_id or doi}"
    except Exception as exc:
        return None, f"OpenAlex authenticated DOI lookup failed: {clean(exc)[:180]}"


def _openalex_recovery_candidates(work: dict[str, Any]) -> list[tuple[str, dict[str, str] | None, str]]:
    """Return safe OpenAlex-assisted retrieval routes without exposing the API key."""
    api_key = clean(os.environ.get("OPENALEX_API_KEY"))
    auth = {"Authorization": f"Bearer {api_key}"} if api_key else None
    candidates: list[tuple[str, dict[str, str] | None, str]] = []
    content_urls = work.get("content_urls") if isinstance(work.get("content_urls"), dict) else {}
    pdf_url = clean(content_urls.get("pdf"))
    xml_url = clean(content_urls.get("grobid_xml"))
    if pdf_url:
        candidates.append((pdf_url, auth, "OpenAlex cached full-text PDF"))
    if xml_url:
        candidates.append((xml_url, auth, "OpenAlex cached full-text XML"))

    locations: list[dict[str, Any]] = []
    for loc in [work.get("best_oa_location"), work.get("primary_location")]:
        if isinstance(loc, dict):
            locations.append(loc)
    for loc in work.get("locations") or []:
        if isinstance(loc, dict):
            locations.append(loc)

    seen: set[str] = {url for url, _headers, _label in candidates}
    added = 0
    for loc in locations:
        # Prefer Open Access copies. best_oa_location is included even on older API
        # payloads where an explicit is_oa flag may be absent.
        is_oa = bool(loc.get("is_oa")) or loc is work.get("best_oa_location")
        if not is_oa:
            continue
        for field, suffix in (("pdf_url", "OA PDF/location"), ("landing_page_url", "OA landing/repository")):
            url = clean(loc.get(field))
            if not _safe_url(url) or url in seen:
                continue
            seen.add(url)
            candidates.append((url, None, f"OpenAlex {suffix}"))
            added += 1
            if added >= OPENALEX_MAX_LOCATION_ROUTES:
                return candidates
    return candidates


def fetch_source_for_record(r: dict[str, Any]) -> SourceRead:
    """Use scanner routes first, then authenticated OpenAlex recovery for scholarly DOI records."""
    provenance = clean(r.get("discovery_provenance")).lower()
    access = r.get("source_access") if isinstance(r.get("source_access"), dict) else {}
    candidates: list[tuple[str, dict[str, str] | None, str]] = []
    validation_url = clean(r.get("source_validation_url") or access.get("validation_url"))
    route_name = clean(access.get("route")).lower()
    cellar_route = bool(
        provenance == "eurlex_cellar" or route_name == "eurlex_cellar"
        or "publications.europa.eu/resource/celex/" in validation_url.lower()
    )
    if validation_url:
        headers = {"Accept": "application/xhtml+xml", "Accept-Language": "eng"} if cellar_route else None
        label = "EUR-Lex/Cellar first-party route" if cellar_route else "scanner validation route"
        candidates.append((validation_url, headers, label))
    celex = clean(r.get("celex") or access.get("celex"))
    if celex and (cellar_route or not validation_url):
        candidates.append((
            "https://publications.europa.eu/resource/celex/" + celex,
            {"Accept": "application/xhtml+xml", "Accept-Language": "eng"},
            "EUR-Lex/Cellar first-party route",
        ))
    ep_url = clean(r.get("ep_document_pdf") or access.get("document_pdf"))
    if ep_url and ep_url != validation_url:
        candidates.append((ep_url, None, "European Parliament first-party document route"))
    public_url = clean(r.get("link") or r.get("url"))
    if public_url:
        candidates.append((public_url, None, "reader-facing URL"))

    seen: set[str] = set()
    failures: list[str] = []
    best: SourceRead | None = None
    best_label = ""

    def try_candidates(routes: list[tuple[str, dict[str, str] | None, str]]) -> SourceRead | None:
        nonlocal best, best_label
        for url, headers, label in routes:
            if not _safe_url(url) or url in seen:
                continue
            seen.add(url)
            src = fetch_source(url, extra_headers=headers)
            if src.mode in {"substantial_web_text", "pdf_excerpt"} and clean(src.text):
                note = f"retrieved via {label}"
                if src.note:
                    note += f"; {src.note}"
                return SourceRead(src.mode, src.text, src.final_url or url, note)
            if src.mode != "stored_only" and clean(src.text):
                if best is None or len(clean(src.text)) > len(clean(best.text)):
                    best = src
                    best_label = label
                failures.append(f"{label}: only {src.mode}")
            else:
                failures.append(f"{label}: {src.note or 'no substantive text'}")
        return None

    direct = try_candidates(candidates)
    if direct is not None:
        return direct

    # If the ordinary source routes produced only a thin landing page or failed, use
    # the repository's OpenAlex key to recover an exact DOI match and legitimate OA
    # copies/full text before the package is handed to the LLM.
    work, oa_note = _openalex_work_for_record(r)
    if work is not None:
        recovered = try_candidates(_openalex_recovery_candidates(work))
        if recovered is not None:
            recovered.note = f"{oa_note}; {recovered.note}"
            return recovered
        failures.append(f"{oa_note}; no substantive OpenAlex-assisted source recovered")
    elif oa_note and "not applicable" not in oa_note.lower() and "not configured" not in oa_note.lower():
        failures.append(oa_note)

    if best is not None and clean(best.text):
        note = f"retrieved via {best_label}; strongest available package material was {best.mode}"
        if work is not None:
            note = f"{oa_note}; {note}"
        return SourceRead(best.mode, best.text, best.final_url, note)
    note = "; ".join(failures)[:900] if failures else "no usable scanner, public, or OpenAlex recovery route"
    return SourceRead("stored_only", "", (best.final_url if best else ""), note=note)


def scanner_fields(r: dict[str, Any]) -> dict[str, Any]:
    """Material the fast scanner already knows and which helps deep reading."""
    keys = (
        "title", "headline", "authors", "date", "c_event_date", "source", "type",
        "signal_kind", "text_mode", "source_text_mode", "event_status", "realisation_status",
        "summary", "signal_note", "core_message", "what", "relevance_note", "why_it_matters",
        "bridge_sentence", "external_eu_bridge", "eu_evidence", "ri_evidence", "geo_evidence",
        "doi", "link", "url", "cluster", "theme", "topics", "keywords",
        "discovery_provenance", "source_domain", "date_basis",
        "source_validation_url", "source_access", "celex", "ep_doc_id", "ep_document_pdf",
    )
    out: dict[str, Any] = {}
    for k in keys:
        v = r.get(k)
        if v in (None, "", [], {}):
            continue
        out[k] = v
    return out


def automatic_material(r: dict[str, Any]) -> str:
    """Human-readable version retained for compatibility/tests and diagnostics."""
    data = scanner_fields(r)
    labels = {
        "title": "ORIGINAL TITLE", "headline": "HEADLINE", "source": "PUBLISHER / SOURCE",
        "authors": "AUTHORS", "date": "DATE", "c_event_date": "EVENT DATE", "type": "TYPE",
        "signal_kind": "SIGNAL KIND", "text_mode": "TEXT MODE", "source_text_mode": "SOURCE TEXT MODE",
        "event_status": "EVENT STATUS", "realisation_status": "REALISATION STATUS",
        "summary": "AUTOMATIC SUMMARY / EXTRACT", "signal_note": "AUTOMATIC SIGNAL NOTE",
        "core_message": "AUTOMATIC CORE MESSAGE", "what": "AUTOMATIC WHAT",
        "relevance_note": "AUTOMATIC RELEVANCE", "why_it_matters": "AUTOMATIC WHY",
        "bridge_sentence": "SOURCE-SUPPORTED BRIDGE", "external_eu_bridge": "RADAR INFERENCE BRIDGE",
        "eu_evidence": "EU EVIDENCE TAGS", "ri_evidence": "R&I EVIDENCE TAGS",
        "geo_evidence": "STRATEGIC EVIDENCE TAGS",
    }
    lines = []
    for k, v in data.items():
        if isinstance(v, list):
            v = "; ".join(map(clean, v))
        lines.append(f"{labels.get(k, k.upper())}: {clean(v)}")
    return "\n".join(lines)


def _words(v: str) -> int:
    return len(clean(v).split())


def validate(obj: dict[str, Any], avoid_whys: list[str]) -> tuple[dict[str, Any], list[str]]:
    """Validate one LLM interpretation and convert it to sidecar field names."""
    problems: list[str] = []
    out: dict[str, Any] = {}
    title = clean(obj.get("reader_title"))
    what = clean(obj.get("what") if obj.get("what") is not None else obj.get("reader_what"))
    why = clean(obj.get("why") if obj.get("why") is not None else obj.get("reader_why"))
    more = clean(obj.get("more") if obj.get("more") is not None else obj.get("reader_more"))

    if title:
        if _words(title) <= WORD_CAP["title"] and not title.endswith(("...", "…")):
            out["reader_title"] = title
        else:
            problems.append("reader_title rejected: too long/ellipsis")
    if not what:
        problems.append("reader_what empty")
    elif _words(what) > WORD_CAP["what"] or what.endswith(("...", "…")):
        problems.append("reader_what rejected: too long/ellipsis")
    else:
        out["reader_what"] = what

    deep_in = obj.get("deep_analysis") if isinstance(obj.get("deep_analysis"), dict) else obj
    why_supported = bool(deep_in.get("why_supported", obj.get("why_supported", False)))
    if why and why_supported and _words(why) <= WORD_CAP["why"] and not why.endswith(("...", "…")):
        for prev in avoid_whys:
            if difflib.SequenceMatcher(None, why.lower(), prev.lower()).ratio() > NEAR_DUPLICATE:
                problems.append("reader_why withheld: near duplicate")
                break
        else:
            out["reader_why"] = why
    elif why:
        problems.append("reader_why withheld: unsupported or too long")

    if more:
        if _words(more) <= MORE_WORD_CAP:
            out["reader_more"] = more
        else:
            problems.append(f"reader_more rejected: over {MORE_WORD_CAP} words")

    deep = {
        "work_kind": clean(deep_in.get("work_kind")),
        "research_question": clean(deep_in.get("research_question")),
        "main_finding": clean(deep_in.get("main_finding")),
        "method_or_basis": clean(deep_in.get("method_or_basis")),
        "qualification": clean(deep_in.get("qualification")),
        "radar_relevance": clean(deep_in.get("radar_relevance")),
        "confidence": clean(deep_in.get("confidence")).lower(),
        "why_supported": why_supported,
    }
    if deep["confidence"] not in {"high", "medium", "low"}:
        deep["confidence"] = "low"
    out["deep_analysis"] = deep
    return out, problems


def main() -> None:
    """Compatibility CLI: preview queue only; never calls a model API."""
    ap = argparse.ArgumentParser(description="Preview works currently needing offline Deep Scan")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--sidecar", type=Path, default=SIDECAR)
    ap.add_argument("--refresh-stale", action="store_true", help="Deprecated and ignored; completed works are not re-queued")
    ap.add_argument("--dry-run", action="store_true")
    # Old API-era options are accepted but ignored so existing local commands fail safely.
    ap.add_argument("--budget-minutes", type=float, default=0.0)
    ap.add_argument("--max-items", type=int, default=0)
    args = ap.parse_args()
    doc = json.loads(args.corpus.read_text(encoding="utf-8"))
    sidecar = load_sidecar(args.sidecar)
    todo = pending(doc, sidecar)
    total = sum(1 for _ in iter_records(doc))
    by_reason: dict[str, int] = {}
    for *_, reason in todo:
        by_reason[reason] = by_reason.get(reason, 0) + 1
    print(f"Deep Scan coverage: {total} current records; {len(todo)} need deep reading ({by_reason})")
    print("No model API is called here. Use scripts/prepare_deep_scan_package.py to create the offline LLM package.")


if __name__ == "__main__":
    main()
