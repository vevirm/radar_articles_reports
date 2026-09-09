#!/usr/bin/env python3
"""Generate optional plain-language reader text into reader_text.json.

Safety boundary:
- READS radar.json.
- NEVER writes radar.json.
- WRITES only reader_text.json.
- The scanner does not import this module or read the sidecar.
- Browser code ignores missing/stale/broken sidecar entries and falls back to
  the existing deterministic reader wording.

The generation step is manual. It uses Anthropic only when explicitly run with
ANTHROPIC_API_KEY configured. --dry-run requires no external service.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import time
from pathlib import Path

MODEL = os.environ.get("READER_TEXT_MODEL", "claude-sonnet-4-6")
CORPUS = Path("radar.json")
SIDECAR = Path("reader_text.json")
STRANDS = ("strand_a", "strand_b", "strand_c")
WORD_CAP = {"what": 20, "why": 20}
NEAR_DUPLICATE = 0.82

PROMPT = """You write plain-language reader text for an EU research-and-innovation geopolitics radar.

You receive only stored scanner material. Do not add facts, actors, dates, causal claims, or certainty that the material does not support.

Return JSON only with these keys:
- what: max 20 words. What this source specifically reports, finds, argues, proposes, or observes.
- why: max 20 words. The specific consequence for European research/innovation capability, dependency, security, partnership, funding, infrastructure, or strategic position. If the supplied material does not support a specific consequence, use an empty string.
- more: 1-3 short sentences, source-grounded, plain English. Preserve uncertainty and proposal/status language.
- confident: boolean; true only if the WHY is directly supported by the supplied material or AUTHOR BRIDGE.

Rules:
- WHAT is source-grounded restatement, not Radar commentary.
- WHY may interpret strategic significance only when traceable to supplied evidence.
- Expand unexplained acronyms when practical.
- Avoid generic boilerplate such as 'this may affect European capability' unless the source gives the actual mechanism.
- Do not say a proposal happened; say it was proposed/tabled/announced.
- Do not turn correlation into causation.
- No markdown.
"""


def clean(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def record_key(r: dict) -> str:
    link = clean(r.get("link") or r.get("url"))
    if link:
        return f"link:{link}"
    doi = clean(r.get("doi")).lower()
    if doi:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
        return f"doi:{doi}"
    rid = clean(r.get("id") or r.get("record_id") or r.get("fingerprint"))
    return f"id:{rid}" if rid else ""


def source_hash(r: dict) -> str:
    """Match radar_data.js FNV-1a over JavaScript UTF-16 code units."""
    material = "\n".join(clean(r.get(k)) for k in ("title", "summary", "bridge_sentence", "source", "type"))
    h = 0x811C9DC5
    raw = material.encode("utf-16le", "surrogatepass")
    for i in range(0, len(raw), 2):
        code_unit = raw[i] | (raw[i + 1] << 8)
        h ^= code_unit
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def source_material(r: dict) -> str:
    title = clean(r.get("title") or r.get("headline"))
    extract = clean(r.get("summary") or r.get("signal_note") or r.get("core_message") or r.get("what"))
    bridge = clean(r.get("bridge_sentence") or r.get("external_eu_bridge"))
    why = clean(r.get("why_it_matters") or r.get("relevance_note"))
    return "\n".join(filter(None, [
        f"TITLE: {title}",
        f"PUBLISHER: {clean(r.get('source'))}",
        f"TYPE: {clean(r.get('type') or r.get('signal_type') or r.get('strand'))}",
        f"STATUS: {clean(r.get('event_status'))}" if r.get("event_status") else "",
        f"EXTRACT ({clean(r.get('text_mode')) or 'stored scanner text'}): {extract[:7000]}",
        f"AUTHOR BRIDGE: {bridge}" if bridge else "",
        f"SCANNER RELEVANCE NOTE: {why}" if why else "",
    ]))


def iter_records(doc: dict):
    for strand in STRANDS:
        for r in doc.get(strand, []) or []:
            if isinstance(r, dict):
                yield strand, r


def load_sidecar(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "profile": "safe-reader-sidecar-v1", "generated_at": None, "records": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise SystemExit(f"Refusing to overwrite unreadable sidecar: {path}")
    if not isinstance(data, dict) or not isinstance(data.get("records"), dict):
        raise SystemExit(f"Invalid sidecar structure: {path}")
    return data


def pending(doc: dict, sidecar: dict, refresh_stale: bool):
    out = []
    table = sidecar.get("records", {})
    for strand, r in iter_records(doc):
        key = record_key(r)
        if not key:
            continue
        old = table.get(key)
        h = source_hash(r)
        if not old:
            out.append((strand, key, h, r, "missing"))
        elif refresh_stale and old.get("source_hash") != h:
            out.append((strand, key, h, r, "stale"))
    return out


def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("response is not an object")
    return obj


def validate(obj: dict, avoid: list[str]) -> tuple[dict, list[str]]:
    problems: list[str] = []
    out: dict[str, str] = {}
    for field in ("what", "why"):
        v = clean(obj.get(field))
        if not v:
            if field == "what":
                problems.append("what empty")
            continue
        if len(v.split()) > WORD_CAP[field]:
            problems.append(f"{field} over {WORD_CAP[field]} words")
            continue
        if v.endswith(("...", "…")):
            problems.append(f"{field} ends in ellipsis")
            continue
        out[f"reader_{field}"] = v
    if not obj.get("confident", False):
        out.pop("reader_why", None)
        problems.append("WHY withheld: model not confident")
    why = out.get("reader_why")
    if why:
        for prev in avoid:
            if difflib.SequenceMatcher(None, why.lower(), prev.lower()).ratio() > NEAR_DUPLICATE:
                out.pop("reader_why", None)
                problems.append("WHY withheld: near duplicate")
                break
    more = clean(obj.get("more"))
    if more:
        out["reader_more"] = more
    return out, problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--sidecar", type=Path, default=SIDECAR)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--refresh-stale", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(args.corpus.read_text(encoding="utf-8"))
    sidecar = load_sidecar(args.sidecar)
    todo = pending(doc, sidecar, args.refresh_stale)
    total = sum(1 for _ in iter_records(doc))
    print(f"{total} current records; {len(todo)} sidecar entries need reader text")
    thin = sum(1 for _, _, _, r, _ in todo if len(clean(r.get("summary") or r.get("signal_note"))) < 200)
    print(f"{thin} pending records have under 200 characters of stored extract")
    if args.dry_run or not todo:
        return

    todo = todo[: max(0, args.limit)] if args.limit else todo
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not configured. Nothing was written.")

    import anthropic
    client = anthropic.Anthropic()
    table = sidecar.setdefault("records", {})
    avoid = [clean(v.get("reader_why")) for v in table.values() if isinstance(v, dict) and clean(v.get("reader_why"))]
    wrote = 0
    for i, (strand, key, h, r, reason) in enumerate(todo, 1):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=900,
                system=PROMPT,
                messages=[{"role": "user", "content": source_material(r)}],
            )
            accepted, problems = validate(parse_json(message.content[0].text), avoid)
        except Exception as exc:  # noqa: BLE001
            print(f"{i}/{len(todo)} ERROR {clean(r.get('title') or r.get('headline'))[:70]}: {exc}", file=sys.stderr)
            continue
        entry = {
            "strand": strand,
            "source_hash": h,
            **accepted,
            "reader_text_model": MODEL,
            "reader_text_written_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        table[key] = entry
        if entry.get("reader_why"):
            avoid.append(entry["reader_why"])
        wrote += 1
        note = "; ".join(problems) if problems else "ok"
        print(f"{i}/{len(todo)} {reason} {clean(r.get('title') or r.get('headline'))[:64]} — {note}", file=sys.stderr)

    sidecar["version"] = 1
    sidecar["profile"] = "safe-reader-sidecar-v1"
    sidecar["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    args.sidecar.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {wrote} reader entries to {args.sidecar}; radar.json was not modified.")


if __name__ == "__main__":
    main()
