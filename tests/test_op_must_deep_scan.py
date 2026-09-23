import datetime as dt
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import scan_radar as sr
import deep_scan_work_state as dws


DEMOGRAPHIC_URL = "https://op.europa.eu/en/publication-detail/-/publication/6c154d71-d7d0-11f0-8da2-01aa75ed71a1/language-en"
AI_FUTURES_URL = "https://op.europa.eu/en/publication-detail/-/publication/52028928-482a-11f1-8095-01aa75ed71a1/language-en"


def test_two_curator_op_reports_are_explicit_must_deep_scan_targets():
    specs = sr.CONFIG.get("must_not_miss_primary_evidence_urls", [])
    by_url = {row.get("url"): row for row in specs if isinstance(row, dict)}
    for url in (DEMOGRAPHIC_URL, AI_FUTURES_URL):
        assert url in by_url
        row = by_url[url]
        assert row.get("main") is True
        assert row.get("must_deep_scan") is True
        assert int(row.get("lookback_months")) >= 12
        assert row.get("published")


def test_must_target_op_uses_cellar_fallback_when_landing_is_unavailable():
    spec = {
        "url": DEMOGRAPHIC_URL,
        "source": "European Commission — Directorate-General for Research and Innovation",
        "tier": 1,
        "label": "The demographic turn — Actions needed for research, innovation and policy in Europe",
        "published": "2025-12-10",
        "lookback_months": 12,
        "must_deep_scan": True,
    }
    recovered = {
        "title": "The demographic turn",
        "source": spec["source"],
        "date": "2025-12-10",
        "link": DEMOGRAPHIC_URL,
        "strand": "A",
        "source_integrity_basis": "institution_pdf_via_cellar",
    }
    with mock.patch.object(sr, "get", return_value=None), mock.patch.object(
        sr, "_op_catalogue_pdf_fallback", return_value=recovered.copy()
    ) as cellar:
        rows, status = sr._primary_evidence_from_landing(spec, [], None)

    assert status["status"] == "FOUND"
    assert status["reason"] == "op_cellar_pdf_fallback"
    assert len(rows) == 1
    assert rows[0]["must_deep_scan"] is True
    assert rows[0]["deep_scan_priority"] == "must"
    assert rows[0]["primary_evidence_target_label"] == spec["label"]
    # The exact-target lane is allowed a bounded 12-month recovery floor, rather than
    # inheriting the ordinary six-month OP catalogue discovery boundary.
    floor = cellar.call_args.args[5]
    assert isinstance(floor, dt.date)
    assert floor <= dt.date(2025, 12, 10)
    seeded = sr.OP_PUBLICATIONS_CATALOGUE_METADATA[sr.normalized_link(DEMOGRAPHIC_URL)]
    assert seeded["published"] == "2025-12-10"


def test_must_deep_scan_targets_run_before_other_primary_evidence_targets():
    normal = {
        "url": "https://example.eu/normal",
        "source": "Example",
        "tier": 1,
        "label": "Normal target",
        "main": True,
    }
    must = {
        "url": AI_FUTURES_URL,
        "source": "European Commission — Directorate-General for Research and Innovation",
        "tier": 1,
        "label": "AI futures final report",
        "main": True,
        "must_deep_scan": True,
    }
    seen = []

    def fake_read(spec, warnings, deadline):
        seen.append(spec["label"])
        return [], {"status": "RETRIEVED_NO_ADMISSION", "url": spec["url"]}

    with mock.patch.dict(
        sr.CONFIG,
        {"primary_evidence_lane_enabled": True, "must_not_miss_primary_evidence_urls": [normal, must]},
        clear=False,
    ), mock.patch.object(sr, "_primary_target_present", return_value=False), mock.patch.object(
        sr, "_primary_target_landing_only_record", return_value=None
    ), mock.patch.object(sr, "_primary_evidence_from_landing", side_effect=fake_read):
        sr.collect_must_not_miss_primary_evidence({}, [], None, {})

    assert seen == ["AI futures final report", "Normal target"]


def test_must_deep_scan_record_leads_deep_scan_queue():
    state = dws.empty_state()
    normal_key = "link:https://example.eu/normal-a"
    must_key = f"link:{AI_FUTURES_URL}"
    dws.update_record_metadata(
        state,
        normal_key,
        {"title": "Normal A", "strand": "A", "link": "https://example.eu/normal-a"},
    )
    dws.update_record_metadata(
        state,
        must_key,
        {
            "title": "The futures of artificial intelligence",
            "strand": "A",
            "link": AI_FUTURES_URL,
            "must_deep_scan": True,
            "deep_scan_priority": "must",
        },
    )
    ordered = dws.prioritize_pending_keys(state, [normal_key, must_key])
    assert ordered[:2] == [must_key, normal_key]
    assert state["records"][must_key]["queue_priority"] == "must_scan"
