#!/usr/bin/env python3
"""Pre-scan state gate. A live radar.json is authoritative; otherwise validate radar_seed.json."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RADAR = ROOT / "radar.json"
SEED = ROOT / "radar_seed.json"

def load_json(path: Path) -> dict:
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Cannot read {path.name}: {exc}") from exc
    if not isinstance(value,dict): raise SystemExit(f"{path.name} must contain a JSON object")
    return value

def rows(doc,key):
    v=doc.get(key,[])
    return v if isinstance(v,list) else []

def seed_contract(doc: dict) -> tuple[bool,str]:
    marker=doc.get("fresh_repository_seed")
    if not isinstance(marker,dict) or str(marker.get("version") or "").strip()!="v1": return False,"seed marker is missing"
    a,b=rows(doc,"strand_a"),rows(doc,"strand_b")
    if (len(a),len(b))!=(190,10): return False,f"seed must be 190 A + 10 B, found {len(a)} A + {len(b)} B"
    if rows(doc,"ab_archive") or rows(doc,"strand_c"): return False,"seed must not contain archive or C"
    if doc.get("scan_state") or doc.get("scan_history"): return False,"seed must not contain scan state/history"
    if doc.get("last_updated") or doc.get("run_completed_at") or doc.get("first_scan_complete"): return False,"seed must not contain prior run completion"
    return True,""

def main()->int:
    if RADAR.exists():
        doc=load_json(RADAR)
        if doc.get("fresh_repository_seed"):
            raise SystemExit("Live radar.json must not carry the bootstrap seed marker")
        if not doc.get("first_scan_complete") or not isinstance(doc.get("scan_state"),dict):
            raise SystemExit("Live radar.json is missing completed incremental scanner state")
        if not isinstance(doc.get("scan_history"),list) or not doc.get("scan_history"):
            raise SystemExit("Live radar.json is missing its own scan_history")
        print(f"Live incremental state accepted: {len(doc['scan_history'])} completed run(s); cumulative A/B={len(rows(doc,'strand_a'))+len(rows(doc,'strand_b'))}.")
        return 0
    doc=load_json(SEED)
    ok,why=seed_contract(doc)
    if not ok: raise SystemExit(f"Fresh seed contract invalid: {why}")
    print("No live radar.json: clean 190 A + 10 B seed accepted. First 24-minute scan will create this repository's own state/history.")
    return 0

if __name__=='__main__': raise SystemExit(main())
