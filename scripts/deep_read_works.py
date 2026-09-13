#!/usr/bin/env python3
"""Shared Deep Scan helpers.

Deep Scan is deliberately *offline from paid model APIs*.

The normal Radar scanner remains the source of truth in ``radar.json``. A manual
GitHub workflow packages records that need deeper reading into a ZIP. The user
can give that ZIP to any capable LLM subscription, then upload the returned
result file to ``deep_scan_inbox``. GitHub validates the result and writes only
the optional semantic sidecar ``reader_text.json``.

This module holds the common record identity, source-reading and reader-text
validation logic used by the package and import scripts. It makes no model/API
calls and needs no AI API key. A successfully deep-read work is considered done;
it is not automatically queued again just because the fast scanner later changes
its wording or metadata.
"""
from __future__ import annotations

import argparse
import difflib
import io
import json
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
STRANDS = ("strand_a", "strand_b", "strand_c")
WORD_CAP = {"what": 20, "why": 20, "title": 18}
MORE_WORD_CAP = 135
NEAR_DUPLICATE = 0.86
SOURCE_CHAR_CAP = 24000
PDF_PAGE_CAP = 10
HTTP_TIMEOUT = 12
USER_AGENT = "EU-RI-Radar-DeepScan-Packager/3.0 (+manual offline semantic pass)"
ACTIVE_DEEP_PROFILES = {
    "deep-reader-v2",
    "deep-reader-v2.1",
    "deep-reader-offline-v1",
}


def clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def record_key(r: dict[str, Any]) -> str:
    link = clean(r.get("link") or r.get("url"))
    if link:
        return f"link:{link}"
    doi = clean(r.get("doi")).lower()
    if doi:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
        return f"doi:{doi}"
    rid = clean(r.get("id") or r.get("record_id") or r.get("fingerprint"))
    return f"id:{rid}" if rid else ""


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
    for strand, r in iter_records(doc):
        key = record_key(r)
        if not key:
            continue
        old = table.get(key)
        h = source_hash(r)
        if not old or old.get("profile") not in ACTIVE_DEEP_PROFILES:
            # A missing entry or a legacy/light reader-language entry means this
            # work has never completed the Deep Scan process.
            out.append((strand, key, h, r, "never_deep_read"))

    # Research/report works are read before current-signal/news records. Within
    # each strand, newer never-read works go first. Completed works are absent.
    grouped: list[tuple[str, str, str, dict[str, Any], str]] = []
    for strand in ("strand_a", "strand_b", "strand_c"):
        rows = [x for x in out if x[0] == strand]
        rows.sort(key=lambda x: _date_key(x[3]), reverse=True)
        grouped.extend(rows)
    return grouped


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


def fetch_source(url: str) -> SourceRead:
    """Best-effort source retrieval. Failure never blocks package creation."""
    if not _safe_url(url):
        return SourceRead("stored_only", "", note="no usable http(s) source link")
    try:
        with requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.5"},
            timeout=HTTP_TIMEOUT,
            allow_redirects=True,
            stream=True,
        ) as resp:
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


def scanner_fields(r: dict[str, Any]) -> dict[str, Any]:
    """Material the fast scanner already knows and which helps deep reading."""
    keys = (
        "title", "headline", "authors", "date", "c_event_date", "source", "type",
        "signal_kind", "text_mode", "source_text_mode", "event_status", "realisation_status",
        "summary", "signal_note", "core_message", "what", "relevance_note", "why_it_matters",
        "bridge_sentence", "external_eu_bridge", "eu_evidence", "ri_evidence", "geo_evidence",
        "doi", "link", "url", "cluster", "theme", "topics", "keywords",
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
