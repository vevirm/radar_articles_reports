#!/usr/bin/env python3
"""Small, production-safe regression gate for Radar scan workflows.

The full development suite intentionally contains research/content checks against
live generated data. Those checks are useful during review, but they must not be
able to stop an automatic scan just because the corpus changed.

Production therefore uses an explicit allow-list of deterministic scanner,
workflow, state and safety tests. New development/content tests do not become
production blockers unless they are deliberately added here.
"""
from __future__ import annotations

import inspect
import re
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

# Explicit production gate. These cover scanner contracts, state safety,
# serialization, source transport/routing, upload-vs-scan separation, admission
# plumbing and the current C/event integrity path. The much larger full suite is
# still available manually for development/research-quality review.
PRODUCTION_TEST_FILES = (
    "test_security_and_state_guards.py",
    "test_scanner_features.py",
    "test_source_route_parity.py",
    "test_source_transport_repair.py",
    "test_deferred_metadata_fair_retries.py",
    "test_eu_ri_recall_and_publication_repair.py",
    "test_v172020_scanner_serialization.py",
    "test_v172031_uploads_are_not_scans.py",
    "test_v172037_plumbing_cleanup.py",
    "test_v172042_admission_and_workflow_repair.py",
    "test_v172046_metadata_resilience.py",
    "test_v172048_incremental_engine.py",
    "test_v172050_curated_core.py",
    "test_v231_primary_evidence_scheduler.py",
    "test_v240_admission_repair.py",
    "test_v242_scanner_admission_repair.py",
    "test_v2471_c_event_integrity_hotfix.py",
    "test_v2472_c_selection_dedup.py",
    "test_v2476_exceptional_c_release.py",
    "test_v247_system_scope_and_country_news.py",
)

# Even an allow-listed test can contain a live-corpus assertion. Those individual
# checks remain non-blocking because their values change as research accumulates.
LIVE_CONTENT_PATTERNS = (
    re.compile(r"\bradar\.json\b"),
    re.compile(r"\bradar_active\.json\b"),
    re.compile(r"\bhistorical[/\\\\]historical\.json\b"),
    re.compile(r"\bdeep_scan_work_state\.json\b"),
    re.compile(r"\bdeep_a_private_state\.json\b"),
    re.compile(r"\btemporary_openalex_a_state\.json\b"),
    re.compile(r"\breader_language[/\\\\]approved\.json\b"),
)
TEMP_FIXTURE_HINTS = (
    'tmp_path / "radar.json"', "tmp_path / 'radar.json'",
    'tmp / "radar.json"', "tmp / 'radar.json'",
    'td / "radar.json"', "td / 'radar.json'",
    'Path("radar.json")', "Path('radar.json')",
)

# Regression fixtures must never leak state into the real scan that follows.
PROTECTED_RUNTIME_PATHS = (
    "radar.json",
    "radar_active.json",
    "deep_scan_work_state.json",
    "deep_a_private_state.json",
    "temporary_openalex_a_state.json",
    "historical/historical.json",
    "reader_language/approved.json",
)


def _source(obj) -> str:
    try:
        return inspect.getsource(obj)
    except (OSError, TypeError):
        return ""


def _live_reference(source: str) -> bool:
    scrubbed = source or ""
    for hint in TEMP_FIXTURE_HINTS:
        scrubbed = scrubbed.replace(hint, "")
    return any(pattern.search(scrubbed) for pattern in LIVE_CONTENT_PATTERNS)


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


def _is_content_coupled(test: unittest.TestCase) -> bool:
    cls = test.__class__
    method = getattr(cls, getattr(test, "_testMethodName", ""), None)
    if method is not None and _live_reference(_source(method)):
        return True
    for name in ("setUpClass", "setUp"):
        obj = cls.__dict__.get(name)
        if obj is not None and _live_reference(_source(obj)):
            return True
    module = sys.modules.get(cls.__module__)
    obj = getattr(module, "setUpModule", None) if module is not None else None
    return bool(obj is not None and _live_reference(_source(obj)))


def _syntax_check() -> bool:
    """Compile production Python plus the selected preflight tests in memory."""
    files = []
    for base in (ROOT / "scripts", ROOT / "historical"):
        if base.is_dir():
            files.extend(base.rglob("*.py"))
    files.extend(TESTS / name for name in PRODUCTION_TEST_FILES)

    failures = []
    for path in sorted(set(files)):
        if not path.is_file():
            failures.append((path, "missing required production test/source file"))
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (SyntaxError, UnicodeError) as exc:
            failures.append((path, str(exc)))
    if failures:
        for path, exc in failures:
            try:
                label = path.relative_to(ROOT)
            except ValueError:
                label = path
            print(f"ERROR: production syntax/preflight check failed for {label}: {exc}", file=sys.stderr)
        return False
    return True


def _snapshot_runtime_files():
    return {
        ROOT / rel: (ROOT / rel).read_bytes() if (ROOT / rel).is_file() else None
        for rel in PROTECTED_RUNTIME_PATHS
    }


def _restore_runtime_files(snapshot) -> None:
    for path, original in snapshot.items():
        if original is None:
            if path.is_file():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file() or path.read_bytes() != original:
            path.write_bytes(original)


def _load_production_suite():
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for filename in PRODUCTION_TEST_FILES:
        discovered = loader.discover(str(TESTS), pattern=filename, top_level_dir=str(TESTS))
        suite.addTests(discovered)
    return suite


def main() -> int:
    if not _syntax_check():
        return 1

    blocking = unittest.TestSuite()
    nonblocking_ids = []
    for test in _flatten(_load_production_suite()):
        if _is_content_coupled(test):
            nonblocking_ids.append(test.id())
        else:
            blocking.addTest(test)

    print(f"Production preflight: running {blocking.countTestCases()} critical deterministic tests.")
    if nonblocking_ids:
        print(f"Production preflight: {len(nonblocking_ids)} live-content checks are non-blocking:")
        for test_id in nonblocking_ids:
            print(f"  live-content: {test_id}")

    snapshot = _snapshot_runtime_files()
    try:
        result = unittest.TextTestRunner(verbosity=1).run(blocking)
    finally:
        _restore_runtime_files(snapshot)

    if not result.wasSuccessful():
        print("ERROR: critical deterministic regression failed; production scan is blocked.")
        return 1

    print("Production preflight passed. Full research/content tests remain available for manual review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
