from scripts.prepare_deep_scan_package import annotate_scan_attempts


def test_main_third_attempt_is_hard_final_only():
    jobs = [
        {"record_key": "main-third", "corpus_scope": "main"},
        {"record_key": "main-second", "corpus_scope": "main"},
        {"record_key": "hist-third", "corpus_scope": "historical"},
    ]
    state = {"records": {
        "main-third": {"scan_package_attempts": 2},
        "main-second": {"scan_package_attempts": 1},
        "hist-third": {"scan_package_attempts": 2},
    }}
    annotate_scan_attempts(jobs, state)
    assert jobs[0]["scan_attempt"] == 3
    assert jobs[0]["scan_mode"] == "hard_final"
    assert jobs[1]["scan_attempt"] == 2
    assert jobs[1]["scan_mode"] == "standard"
    assert jobs[2]["scan_attempt"] == 3
    assert jobs[2]["scan_mode"] == "standard"
