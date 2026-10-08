"""Deep Scan must apply the scanner's EU R&I remit, not a second geopolitics filter.

This checks the actual instructions shipped to Deep Scan workers, including the
terminal recovery path. It does not change the automatic scanner's heuristics.
"""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

from scripts.prepare_deep_scan_package import EU_RI_SCOPE_POLICY, INSTRUCTIONS
from scripts.prepare_deep_scan_hardcore_recovery import STANDARD_DEEP_SCAN_INSTRUCTIONS

ROOT = Path(__file__).resolve().parents[1]


def test_deep_scan_instructions_match_three_scanner_strands():
    compact = " ".join(INSTRUCTIONS.split())
    assert "European/EU research and innovation intelligence" in INSTRUCTIONS
    assert "three independent positive admission routes" in INSTRUCTIONS
    assert "Route 3" in INSTRUCTIONS
    assert "European R&I-system" in INSTRUCTIONS
    assert "research careers" in compact
    assert "research infrastructure" in compact
    assert "open science" in compact
    assert "source-grounded" in INSTRUCTIONS
    assert "do not reject because Europe/EU is absent" in compact
    assert "transferable method contribution" in compact
    assert "Europe/EU R&I systems" in compact and "source-" in INSTRUCTIONS
    assert "genuinely new development" in compact
    assert "vague reasons" in INSTRUCTIONS
    assert "three-" in INSTRUCTIONS and "recovery/terminal-unverifiable policy" in compact
    assert "DROP" in INSTRUCTIONS
    assert "DROP_UNVERIFIABLE" in INSTRUCTIONS.upper()


def test_hardcore_scan_uses_same_admission_contract():
    assert STANDARD_DEEP_SCAN_INSTRUCTIONS == INSTRUCTIONS
    assert "Route 3" in STANDARD_DEEP_SCAN_INSTRUCTIONS
    assert "same target of" in STANDARD_DEEP_SCAN_INSTRUCTIONS


def test_new_worker_package_embeds_contract_and_policy_id(tmp_path):
    row = {
        "title": "Research careers and researcher mobility across EU member states",
        "date": "2026-09-01",
        "link": "https://example.org/ri-work",
        "source": "Example Journal",
        "type": "peer-reviewed research",
        "summary": "European panel study of researcher mobility and research workforce across countries.",
        "relevance_note": "R&I workforce is the subject of the study.",
    }
    corpus = tmp_path / "radar.json"
    corpus.write_text(json.dumps({"strand_a": [row], "strand_b": [], "strand_c": []}), encoding="utf-8")
    sidecar = tmp_path / "reader_text.json"
    sidecar.write_text(json.dumps({"records": {}}), encoding="utf-8")
    dest = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, "scripts/prepare_deep_scan_package.py", "--corpus", str(corpus),
         "--sidecar", str(sidecar), "--output-dir", str(dest), "--no-fetch"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    with zipfile.ZipFile(dest / "deep_scan_package.zip") as z:
        basename = next(n.split("/", 1)[0] for n in z.namelist() if "/manifest.json" in n)
        manifest = json.loads(z.read(f"{basename}/manifest.json"))
        instructions = z.read(f"{basename}/INSTRUCTIONS.md").decode("utf-8")
    assert manifest["admission_scope_policy"] == EU_RI_SCOPE_POLICY
    assert manifest["works_in_package"] == 1
    assert "Scope contract — SAME" in instructions
    assert "A valid Route 3" in instructions
    assert "Strand C — substantive CURRENT European R&I developments" in instructions
