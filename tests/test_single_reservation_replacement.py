import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reserve_single_deep_scan_package.py"


def test_release_existing_single_preserves_worker_lanes_and_requeues_records(tmp_path):
    state_path = tmp_path / "deep_scan_work_state.json"
    state = {
        "version": 1,
        "profile": "radar-deep-scan-work-state-v1",
        "updated_at": None,
        "lanes": {
            "A": {"target_size": 1, "assigned": ["a-key"], "current_package_id": "a-pkg", "package_history": ["a-pkg"]},
            "B": {"target_size": 1, "assigned": ["b-key"], "current_package_id": "b-pkg", "package_history": ["b-pkg"]},
            "SINGLE": {"target_size": 2, "assigned": ["old-1", "old-2"], "current_package_id": "old-single", "package_history": ["old-single"]},
        },
        "records": {
            "a-key": {"status": "assigned", "lane": "A"},
            "b-key": {"status": "assigned", "lane": "B"},
            "old-1": {"status": "assigned", "lane": "SINGLE", "last_package_id": "old-single"},
            "old-2": {"status": "assigned", "lane": "SINGLE", "last_package_id": "old-single"},
        },
        "packages": {
            "old-single": {"lane": "SINGLE", "created_at": "2026-09-29T05:34:36Z", "record_keys": ["old-1", "old-2"]},
        },
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")

    subprocess.run(
        [sys.executable, str(SCRIPT), "--release-existing", "--work-state", str(state_path)],
        cwd=ROOT,
        check=True,
    )

    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["lanes"]["A"]["assigned"] == ["a-key"]
    assert saved["lanes"]["B"]["assigned"] == ["b-key"]
    assert saved["lanes"]["SINGLE"]["assigned"] == []
    assert saved["lanes"]["SINGLE"]["current_package_id"] == ""
    assert saved["records"]["old-1"]["status"] == "pending"
    assert "lane" not in saved["records"]["old-1"]
    assert saved["packages"]["old-single"]["status"] == "superseded"
