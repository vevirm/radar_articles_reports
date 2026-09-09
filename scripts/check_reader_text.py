#!/usr/bin/env python3
"""Validate the optional reader_text.json sidecar only."""
import collections
import difflib
import json
import re
import sys
from pathlib import Path

SIDE = Path("reader_text.json")
MAX_REPEATS = 3
NEAR = 0.82
CAP = {"reader_what": 20, "reader_why": 20}
JARGON = [
    "bibliographic coupling", "citation burst", "change-point detection",
    "semantic shift", "dynamic topic model", "graph anomaly detection",
    "technology intelligence", "MFF", "HPC", "TRL", "chokepoint",
]

def clean(v): return re.sub(r"\s+", " ", str(v or "")).strip()

def main():
    if not SIDE.exists():
        print("reader_text.json absent: reader layer is safely disabled")
        return
    doc = json.loads(SIDE.read_text(encoding="utf-8"))
    records = doc.get("records", {}) if isinstance(doc, dict) else {}
    if not isinstance(records, dict):
        print("FAIL: sidecar records is not an object")
        sys.exit(1)
    entries = [v for v in records.values() if isinstance(v, dict)]
    fails, warns = [], []
    whys = [clean(v.get("reader_why")) for v in entries if clean(v.get("reader_why"))]
    for text, n in collections.Counter(whys).items():
        if n > MAX_REPEATS:
            fails.append(f"WHY repeats {n} times: {text[:70]}")
    seen=[]
    for w in whys:
        for prev in seen:
            if difflib.SequenceMatcher(None,w.lower(),prev.lower()).ratio()>NEAR:
                warns.append(f"WHY near duplicate: {w[:60]}")
                break
        seen.append(w)
    for v in entries:
        if not clean(v.get("source_hash")):
            fails.append("entry missing source_hash")
        for field,cap in CAP.items():
            text=clean(v.get(field))
            if text and len(text.split())>cap:
                fails.append(f"{field} over {cap} words: {text[:60]}")
            if text.endswith(("...","…")):
                fails.append(f"{field} ends in ellipsis: {text[:60]}")
            for term in JARGON:
                if text and re.search(rf"\b{re.escape(term)}\b",text,re.I):
                    fails.append(f"{field} uses '{term}': {text[:60]}")
    print(f"reader entries {len(entries)} | WHY {len(whys)} | distinct WHY {len(set(whys))}")
    for x in warns[:30]: print("warn:",x)
    for x in fails: print("FAIL:",x)
    print(f"{len(fails)} failures, {len(warns)} warnings")
    sys.exit(1 if fails else 0)

if __name__ == "__main__": main()
