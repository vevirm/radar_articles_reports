#!/usr/bin/env python3
"""Run the fast safety suite used before each reasoning-reform stage."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = [
    "tests/test_active_corpus_v2.py",
    "tests/test_deep_reader.py",
    "tests/test_deep_scan_historical_queue.py",
    "tests/test_deep_scan_offline.py",
    "tests/test_scanner_features.py",
    "tests/test_security_and_state_guards.py",
    "tests/test_reader_language_pipeline.py",
    "tests/test_reader_evidence_feedback.py",
    "tests/test_reasoning_reform_claim_schema.py",
    "tests/test_reasoning_reform_claim_backfill.py",
    "tests/test_reasoning_reform_future_deep_scan_claims.py",
    "tests/test_reasoning_reform_claim_shadow.py",
]


def main() -> int:
    cmd = [sys.executable, "-m", "pytest", "-q", *TESTS]
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
