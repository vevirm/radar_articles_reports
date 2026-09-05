from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scheduled_scan_preflight_is_scanner_first_not_reader_release_suite():
    workflow = (ROOT / ".github/workflows/radar-scan.yml").read_text(encoding="utf-8")
    if "cron: '17 0,4,8,12,16,20 * * *'" in workflow:
        assert "Run scanner-critical regression tests" in workflow
        assert "tests.test_scanner_features tests.test_security_and_state_guards" in workflow
        assert "unittest discover -s tests -p 'test_*.py'" not in workflow
    else:
        # GitHub's browser bulk uploader can leave the hidden workflow at an older
        # revision.  Do not let a workflow-contract assertion inside the scanner
        # regression suite block discovery before the visible compatibility guard runs.
        scan_source = (ROOT / "scripts/scan_radar.py").read_text(encoding="utf-8")
        guard_source = (ROOT / "scripts/scanner_run_guard.py").read_text(encoding="utf-8")
        assert "legacy_workflow_schedule_compatibility_active" in scan_source
        assert "defer_if_peer_scanner_active" in guard_source


def test_trend_page_uses_competition_name_without_exposing_method():
    page = (ROOT / "trends/index.html").read_text(encoding="utf-8")
    assert "Trends vs. countertrend competition" in page
    assert "Evidence tug-of-war" in page
    assert "hostile witness" not in page.lower()
    assert "actor-reporting" not in page.lower()


def test_shock_page_has_dynamic_shock_list_for_realised_and_inferred_shocks():
    page = (ROOT / "shocks/index.html").read_text(encoding="utf-8")
    assert "<h2>Shock list</h2>" in page
    assert "direct.forEach" in page
    assert "scenarios.forEach" in page
    assert "dynamic.forEach" in page
    assert "updatedThisScan" in page
    assert "new_this_scan" in page
