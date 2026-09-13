#!/usr/bin/env python3
"""Generate a non-destructive Deep Scan V2 migration preview."""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.active_corpus import build_active_document, load_admission, load_corrections, load_reader, record_key


def clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def doi(row: dict[str, Any]) -> str:
    raw = clean(row.get("doi"))
    if not raw:
        m = re.search(r"doi\.org/(10\.\d{4,9}/[^?#\s]+)", clean(row.get("link") or row.get("url")), re.I)
        raw = m.group(1) if m else ""
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", raw, flags=re.I).lower().rstrip("/")


def norm_title(row: dict[str, Any]) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(row.get("title") or row.get("headline")).lower()).strip()


def main() -> int:
    raw = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
    admission = load_admission(ROOT / "admission_state.json")
    corrections = load_corrections(ROOT / "record_corrections.json")
    reader = load_reader(ROOT / "reader_text.json")
    active = build_active_document(raw, admission=admission, corrections=corrections, reader=reader)

    records = []
    for strand in ("strand_a", "strand_b", "strand_c"):
        for row in raw.get(strand, []) if isinstance(raw.get(strand), list) else []:
            if isinstance(row, dict):
                records.append((strand, row))

    keys = collections.defaultdict(list)
    dois = collections.defaultdict(list)
    titles = collections.defaultdict(list)
    for strand, row in records:
        k = record_key(row)
        if k:
            keys[k].append((strand, row))
        d = doi(row)
        if d:
            dois[d].append((strand, row))
        t = norm_title(row)
        if len(t) >= 24:
            titles[t].append((strand, row))

    v1 = v2 = 0
    legacy_concern = []
    table = reader.get("records", {})
    for k, entry in table.items():
        if not isinstance(entry, dict):
            continue
        profile = clean(entry.get("profile"))
        if profile == "deep-reader-v2-authoritative":
            v2 += 1
        elif profile.startswith("deep-reader"):
            v1 += 1
        deep = entry.get("deep_analysis") if isinstance(entry.get("deep_analysis"), dict) else {}
        relevance = clean(deep.get("radar_relevance"))
        if re.search(r"outside the eu|reference model|comparator|comparison only|not.*europe", relevance, re.I):
            legacy_concern.append({"record_key": k, "radar_relevance": relevance})

    decision_counts = collections.Counter()
    for state in admission.get("records", {}).values():
        if isinstance(state, dict):
            decision_counts[clean(state.get("decision")).lower() or "provisional"] += 1

    same_key = []
    for k, rows in keys.items():
        if len(rows) > 1:
            same_key.append({
                "record_key": k,
                "occurrences": len(rows),
                "records": [{"strand": s.replace("strand_", "").upper(), "title": clean(r.get("title") or r.get("headline")), "source": clean(r.get("source"))} for s, r in rows],
            })

    def distinct_key_groups(groups, reason):
        out=[]
        for identity, rows in groups.items():
            distinct={record_key(r) for _,r in rows if record_key(r)}
            if len(distinct)>1:
                out.append({"reason":reason,"identity":identity,"record_keys":sorted(distinct),"titles":[clean(r.get("title") or r.get("headline")) for _,r in rows]})
        return out

    report = {
        "profile": "radar-v2-migration-preview-v1",
        "destructive_changes": False,
        "raw_counts": {s: len(raw.get(s, [])) for s in ("strand_a", "strand_b", "strand_c")},
        "active_counts_now": {s: len(active.get(s, [])) for s in ("strand_a", "strand_b", "strand_c")},
        "raw_record_occurrences": len(records),
        "unique_record_keys": len(keys),
        "deep_scan_legacy_entries": v1,
        "deep_scan_v2_entries": v2,
        "deep_scan_v2_pending_unique_keys": sum(1 for k in keys if not (isinstance(table.get(k),dict) and table[k].get("profile")=="deep-reader-v2-authoritative")),
        "current_admission_decisions": dict(decision_counts),
        "metadata_corrections": len(corrections.get("records", {})),
        "same_record_key_variant_groups": same_key,
        "high_confidence_distinct_key_duplicate_candidates": distinct_key_groups(dois,"same_doi") + distinct_key_groups(titles,"exact_normalized_title"),
        "legacy_deep_scan_relevance_concerns": legacy_concern,
        "note": "Duplicate candidates and legacy concerns are preview flags only. No new DROP decision is applied by this report.",
    }
    out_json = ROOT / "migration-reports" / "v2-migration-preview.json"
    out_md = ROOT / "migration-reports" / "v2-migration-preview.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Radar V2 migration preview", "", "This report is non-destructive. It identifies the starting state before authoritative Deep Scan V2 verification.", "",
        f"- Raw records: **{len(records)}** occurrences / **{len(keys)}** stable record keys.",
        f"- Legacy Deep Scan interpretations retained: **{v1}**.",
        f"- Authoritative Deep Scan V2 completed: **{v2}**.",
        f"- Unique records still needing V2: **{report['deep_scan_v2_pending_unique_keys']}**.",
        f"- Current active counts: A **{report['active_counts_now']['strand_a']}**, B **{report['active_counts_now']['strand_b']}**, C **{report['active_counts_now']['strand_c']}**.",
        f"- Same-record-key variant groups requiring V2 canonical treatment: **{len(same_key)}**.",
        f"- High-confidence distinct-key duplicate candidates for inspection: **{len(report['high_confidence_distinct_key_duplicate_candidates'])}**.",
        f"- Existing metadata corrections: **{report['metadata_corrections']}**.",
        "", "## Safety", "", "No raw record is deleted by this preview. DROP/REVIEW/KEEP decisions enter the active corpus only through explicit sidecar state, normally after validated Deep Scan V2 results.", "",
    ]
    if legacy_concern:
        md += ["## Legacy Deep Scan relevance concerns", ""]
        for item in legacy_concern[:20]:
            md.append(f"- `{item['record_key']}` — {item['radar_relevance']}")
        md.append("")
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if not isinstance(v,list)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
