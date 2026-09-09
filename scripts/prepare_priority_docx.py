#!/usr/bin/env python3
"""Turn an APA7 reference-list DOCX into exact scanner priority candidates.

This does not admit anything.  It only extracts bibliographic clues (title, authors,
year, venue, DOI/URL) so the ordinary Radar scanner can resolve the underlying work and
apply its normal duplicate and A/B/C gates.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
YEAR_RE = re.compile(r"\((?P<year>(?:19|20)\d{2})(?:[a-z])?(?:,\s*[^)]*)?\)\.?\s*", re.I)
DOI_RE = re.compile(r"(?:https?://(?:dx\.)?doi\.org/)?(?P<doi>10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.I)
URL_RE = re.compile(r"https?://[^\s<>]+", re.I)


def clean(value: str) -> str:
    value = (value or "").replace("\u00a0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def docx_paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    out: list[str] = []
    for p in root.iter(f"{{{W_NS}}}p"):
        parts = [node.text or "" for node in p.iter(f"{{{W_NS}}}t")]
        text = clean("".join(parts))
        if text:
            out.append(text)
    return out



def looks_like_apa_reference_paragraph(text: str) -> bool:
    """Return True for a bibliographic APA-style paragraph, not section prose/headings.

    Priority DOCX is a discovery queue, so headings such as ``Evidence``/``Methods`` and
    scan notes must never become fake unresolved candidates. APA7 references in this
    workflow are expected to contain a parenthesised year/date plus bibliographic text.
    """
    text = clean(text)
    m = YEAR_RE.search(text)
    if not m:
        return False
    before = clean(text[:m.start()])
    after = clean(text[m.end():])
    # Require both an author/institution side and a plausible work-title side.
    return bool(before and len(after.split()) >= 3)

def strip_terminal_link(text: str) -> str:
    return clean(URL_RE.sub(" ", text))


def split_apa_after_year(rest: str) -> tuple[str, str]:
    """Best-effort APA7 title/venue split.

    APA journal/news references place the work title immediately after the date and end
    it with a period.  We deliberately keep this parser conservative: if the first
    sentence is implausibly short, the full post-year text is used as a search clue.
    """
    rest = strip_terminal_link(rest)
    rest = DOI_RE.sub(" ", rest)
    rest = clean(rest)
    if not rest:
        return "", ""
    parts = [clean(x) for x in re.split(r"\.\s+(?=[A-Z0-9\[\"'])", rest) if clean(x)]
    if not parts:
        return rest.rstrip("."), ""
    title = parts[0].rstrip(".")
    if len(title.split()) < 3 and len(parts) > 1:
        title = clean(parts[0] + ". " + parts[1]).rstrip(".")
        venue = parts[2] if len(parts) > 2 else ""
    else:
        venue = parts[1] if len(parts) > 1 else ""
    return title, venue.rstrip(".")


def domain_from_url(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def parse_reference(raw: str, idx: int) -> dict:
    text = clean(raw)
    doi_match = DOI_RE.search(text)
    doi = clean(doi_match.group("doi").rstrip(".,;")) if doi_match else ""
    urls = [clean(x.rstrip(".,;")) for x in URL_RE.findall(text)]
    url = ""
    if doi:
        url = f"https://doi.org/{doi}"
    elif urls:
        url = urls[-1]

    year_match = YEAR_RE.search(text)
    year = year_match.group("year") if year_match else ""
    date_value = f"{year}-01-01" if year else ""
    date_precision = "year" if year else ""
    if year_match:
        inside = text[year_match.start() + 1:text.find(")", year_match.start())]
        for fmt, precision in (("%Y, %B %d", "day"), ("%Y, %b %d", "day"), ("%Y, %B", "month"), ("%Y, %b", "month")):
            try:
                parsed = dt.datetime.strptime(inside.strip(), fmt)
                date_value = parsed.date().isoformat()
                date_precision = precision
                break
            except ValueError:
                pass
    authors = clean(text[: year_match.start()].rstrip(". ")) if year_match else ""
    rest = clean(text[year_match.end():]) if year_match else text
    title, venue = split_apa_after_year(rest)

    # Avoid turning the whole APA line into a fake title when parsing fails.
    if len(title.split()) < 3:
        title = ""
    source = venue
    domain = domain_from_url(url)
    source_kind = "scholarly" if doi else ""
    if not source_kind:
        scholarly_cues = r"\b(journal|review|research|futures|foresight|scientometrics|policy|technology|science|proceedings|quarterly|studies)\b"
        source_kind = "scholarly" if re.search(scholarly_cues, source, re.I) else "news_or_commentary"

    fingerprint = hashlib.sha1((title or text).lower().encode("utf-8")).hexdigest()[:12]
    return {
        "candidate_id": f"APA-{idx:03d}-{fingerprint}",
        "group_id": f"APA-{idx:03d}",
        "role_in_group": "primary",
        "title": title,
        "authors": authors,
        "source": source,
        "date": date_value,
        "date_precision": date_precision,
        "doi": doi,
        "url": url,
        "source_domain": domain,
        "source_kind": source_kind,
        "candidate_kind": "substantive_publication",
        "frontier_row_hint": "",
        "secondary_frontier_row_hints": [],
        "curator_note": "APA7 priority-scan reference; bibliographic clue only, never admission evidence.",
        "raw_reference": text,
        "parse_status": "ok" if title else "needs_resolution_from_full_reference",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("docx", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if not args.docx.is_file():
        raise SystemExit(f"DOCX not found: {args.docx}")
    refs = [ref for ref in docx_paragraphs(args.docx) if looks_like_apa_reference_paragraph(ref)]
    candidates = [parse_reference(ref, i + 1) for i, ref in enumerate(refs)]
    candidates = [x for x in candidates if x.get("raw_reference") and x.get("title")]
    parsed = sum(1 for x in candidates if x.get("title"))
    if not candidates:
        raise SystemExit("No non-empty APA references found in the DOCX")
    if parsed == 0:
        raise SystemExit("References were found, but no titles could be parsed. Use ordinary APA7 reference paragraphs (one work per paragraph).")

    payload = {
        "profile_version": "priority-docx-apa7-v1",
        "batch_id": f"priority-docx-{hashlib.sha1(args.docx.read_bytes()).hexdigest()[:12]}",
        "source_document": args.docx.name,
        "group_count": len(candidates),
        "work_count": len(candidates),
        "policy": {
            "admission": "APA7 references are discovery clues only. Every resolved work must pass ordinary Radar duplicate, source, language and A/B/C admission rules.",
            "force_admit": False,
        },
        "candidates": candidates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Parsed {len(candidates)} APA reference(s); {parsed} with usable title clues.")
    for row in candidates[:40]:
        print(f"- {row['candidate_id']}: {row.get('title') or '[title unresolved]'}")


if __name__ == "__main__":
    main()
