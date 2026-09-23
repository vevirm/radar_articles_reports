from pathlib import Path
import datetime as dt
import importlib.util
import os
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
DEEP_PATH = ROOT / "scripts" / "deep_read_works.py"

spec = importlib.util.spec_from_file_location("radar_route_parity_scan", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)

spec2 = importlib.util.spec_from_file_location("radar_route_parity_deep", DEEP_PATH)
deep = importlib.util.module_from_spec(spec2)
assert spec2 and spec2.loader
sys.modules[spec2.name] = deep
spec2.loader.exec_module(deep)

spec3 = importlib.util.spec_from_file_location("radar_route_parity_import", ROOT / "scripts" / "import_deep_scan_results.py")
deep_import = importlib.util.module_from_spec(spec3)
assert spec3 and spec3.loader
sys.modules[spec3.name] = deep_import
spec3.loader.exec_module(deep_import)

spec4 = importlib.util.spec_from_file_location("radar_route_parity_hardcore_import", ROOT / "scripts" / "import_deep_scan_hardcore_recovery.py")
hardcore_import = importlib.util.module_from_spec(spec4)
assert spec4 and spec4.loader
sys.modules[spec4.name] = hardcore_import
spec4.loader.exec_module(hardcore_import)


class _Resp:
    def __init__(self, *, status_code=200, payload=None, text="", content=b""):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.content = content or text.encode("utf-8")
        self.url = ""
        self.headers = {}

    def json(self):
        return self._payload


class RouteParityTests(unittest.TestCase):
    def setUp(self):
        scan.KNOWN_SIGNAL_IDENTITIES.clear()

    def test_ep_jsonld_extractor_accepts_flat_portal_shape(self):
        payload = {
            "data": [{
                "document_identifier": "TA-10-2026-0123",
                "document_title": "European research and innovation capacity for artificial intelligence",
                "document_date": "2026-09-21",
                "document_URI": "https://data.europarl.europa.eu/eli/dl/doc/TA-10-2026-0123",
                "document_pdf": "https://data.europarl.europa.eu/distribution/doc/TA-10-2026-0123_en.pdf",
            }]
        }
        rows = scan._ep_document_records(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["doc_id"], "TA-10-2026-0123")
        self.assertEqual(rows[0]["title"], "European research and innovation capacity for artificial intelligence")
        self.assertEqual(rows[0]["date"], dt.date(2026, 9, 21))
        self.assertTrue(any(url.endswith("_en.pdf") for url in rows[0]["urls"]))

    def test_parliament_lane_persists_first_party_validation_route(self):
        payload = {
            "data": [{
                "document_identifier": "TA-10-2026-0123",
                "document_title": "European research and innovation capacity for artificial intelligence",
                "document_date": "2026-09-21",
                "document_URI": "https://data.europarl.europa.eu/eli/dl/doc/TA-10-2026-0123",
                "document_pdf": "https://data.europarl.europa.eu/distribution/doc/TA-10-2026-0123_en.pdf",
            }]
        }
        responses = [
            _Resp(payload=payload),
            _Resp(content=b"%PDF-fake"),
        ]
        body = " ".join([
            "The European Parliament adopted measures concerning European research innovation artificial intelligence technology capacity and strategic infrastructure."
        ] * 10)
        with patch.object(scan.SESSION, "get", side_effect=responses), patch.object(scan, "_ep_pdf_text", return_value=body):
            rows = scan.collect_europarl_adopted_texts(dt.datetime(2026, 9, 22, 12, 0), [])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["discovery_provenance"], "europarl_open_data_adopted_text")
        self.assertEqual(row["ep_doc_id"], "TA-10-2026-0123")
        self.assertTrue(row["source_validation_url"].endswith("_en.pdf"))
        self.assertEqual(row["source_access"]["validation_url"], row["source_validation_url"])
        self.assertTrue(row["link"].endswith("TA-10-2026-0123"))

    def test_parliament_incremental_feed_is_tried_before_list_endpoint(self):
        payload = {
            "data": [{
                "document_identifier": "TA-10-2026-0123",
                "document_title": "European research and innovation capacity for artificial intelligence",
                "document_date": "2026-09-21",
                "document_URI": "https://data.europarl.europa.eu/eli/dl/doc/TA-10-2026-0123",
                "document_pdf": "https://data.europarl.europa.eu/distribution/doc/TA-10-2026-0123_en.pdf",
            }]
        }
        body = " ".join([
            "The European Parliament adopted measures concerning European research innovation artificial intelligence technology capacity and strategic infrastructure."
        ] * 10)
        calls = []

        def fake_get(url, **kwargs):
            calls.append((url, kwargs.get("params") or {}))
            if url.endswith("/feed"):
                return _Resp(payload=payload)
            return _Resp(content=b"%PDF-fake")

        with patch.object(scan.SESSION, "get", side_effect=fake_get), patch.object(scan, "_ep_pdf_text", return_value=body):
            rows = scan.collect_europarl_adopted_texts(dt.datetime(2026, 9, 22, 12, 0), [])
        self.assertEqual(len(rows), 1)
        self.assertTrue(calls[0][0].endswith("/adopted-texts/feed"))
        self.assertEqual(calls[0][1].get("timeframe"), "custom")
        self.assertEqual(calls[0][1].get("start-date"), "2026-09-15")

    def test_parliament_candidate_still_uses_existing_c_gate(self):
        row = {
            "headline": "European research and innovation capacity for artificial intelligence",
            "source": "European Parliament",
            "source_domain": "data.europarl.europa.eu",
            "date": "2026-09-21",
            "date_basis": "ep_adopted_text_document_date",
            "link": "https://data.europarl.europa.eu/eli/dl/doc/TA-10-2026-0123",
            "language": "en",
            "discovery_provenance": "europarl_open_data_adopted_text",
            "source_validation_url": "https://data.europarl.europa.eu/distribution/doc/TA-10-2026-0123_en.pdf",
            "source_access": {
                "route": "europarl_open_data_adopted_text",
                "ep_doc_id": "TA-10-2026-0123",
                "validation_url": "https://data.europarl.europa.eu/distribution/doc/TA-10-2026-0123_en.pdf",
            },
            "_desc": (
                "The European Parliament adopted a resolution on European Union research and innovation capacity, "
                "artificial intelligence infrastructure, research security and strategic technology capability. "
                "The adopted text sets out current European policy action and implementation requirements."
            ),
            "_desc_html": "",
            "_themes": list(scan.themes_for("European Union research innovation artificial intelligence strategic technology")),
            "_entities": [],
            "_institutional_signal": True,
            "_trusted_europe_publication": True,
            "_formal_proposal_signal": False,
            "_strategic_source_text": "European Parliament adopted research innovation artificial intelligence strategic technology",
        }
        diagnostics = []
        admitted = scan.anchor_news([row], [], diagnostics, allow_unanchored=True)
        self.assertEqual(len(admitted), 1, diagnostics)
        self.assertEqual(admitted[0].get("c_admission_basis"), "trusted_europe_publication")
        self.assertEqual(admitted[0].get("source_validation_url"), row["source_validation_url"])
        self.assertEqual(admitted[0].get("source_access"), row.get("source_access"))
        self.assertEqual(admitted[0].get("discovery_provenance"), "europarl_open_data_adopted_text")

    def test_parliament_transport_is_degraded_when_relevant_document_cannot_be_read(self):
        payload = {
            "data": [{
                "document_identifier": "TA-10-2026-0123",
                "document_title": "European research and innovation capacity for artificial intelligence",
                "document_date": "2026-09-21",
                "document_URI": "https://data.europarl.europa.eu/eli/dl/doc/TA-10-2026-0123",
                "document_pdf": "https://data.europarl.europa.eu/distribution/doc/TA-10-2026-0123_en.pdf",
            }]
        }
        stats = {}
        warnings = []
        with patch.object(scan.SESSION, "get", side_effect=[_Resp(payload=payload), _Resp(status_code=403)]):
            rows = scan.collect_europarl_adopted_texts(
                dt.datetime(2026, 9, 22, 12, 0), warnings, execution_stats=stats
            )
        self.assertEqual(rows, [])
        self.assertEqual(stats["source_transport_attempts"]["europarl_open_data"]["status"], "degraded")
        self.assertTrue(any("no substantive first-party document" in w for w in warnings))

    def test_deep_scan_prefers_scanner_validation_route_before_reader_url(self):
        record = {
            "link": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R9999",
            "discovery_provenance": "eurlex_cellar",
            "celex": "32026R9999",
            "source_validation_url": "https://publications.europa.eu/resource/celex/32026R9999",
        }
        calls = []

        def fake_fetch(url, *, extra_headers=None):
            calls.append((url, extra_headers))
            if "publications.europa.eu" in url:
                return deep.SourceRead("substantial_web_text", "verified first party text " * 30, url, "")
            return deep.SourceRead("stored_only", "", url, "blocked")

        with patch.object(deep, "fetch_source", side_effect=fake_fetch):
            result = deep.fetch_source_for_record(record)
        self.assertEqual(result.mode, "substantial_web_text")
        self.assertEqual(len(calls), 1)
        self.assertIn("publications.europa.eu", calls[0][0])
        self.assertEqual((calls[0][1] or {}).get("Accept-Language"), "eng")
        self.assertIn("first-party route", result.note)

    def test_deep_scan_openalex_key_recovers_cached_fulltext_without_leaking_secret(self):
        secret = "test-openalex-secret"
        record = {
            "title": "A scholarly work",
            "doi": "10.1234/example.1",
            "link": "https://doi.org/10.1234/example.1",
        }

        class OAResp:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "results": [{
                        "id": "https://openalex.org/W123456789",
                        "doi": "https://doi.org/10.1234/example.1",
                        "content_urls": {
                            "pdf": "https://content.openalex.org/works/W123456789.pdf",
                        },
                        "best_oa_location": {
                            "is_oa": True,
                            "landing_page_url": "https://repository.example/work",
                        },
                        "locations": [],
                    }]
                }

        fetch_calls = []

        def fake_fetch(url, *, extra_headers=None):
            fetch_calls.append((url, extra_headers or {}))
            if url.startswith("https://doi.org/"):
                return deep.SourceRead("stored_only", "", url, "publisher blocked")
            if url.startswith("https://content.openalex.org/"):
                return deep.SourceRead("pdf_excerpt", "verified scholarly full text " * 80, url, "")
            return deep.SourceRead("stored_only", "", url, "unused")

        with patch.dict(os.environ, {"OPENALEX_API_KEY": secret}, clear=False), \
             patch.object(deep.requests, "get", return_value=OAResp()) as oa_get, \
             patch.object(deep, "fetch_source", side_effect=fake_fetch):
            result = deep.fetch_source_for_record(record)

        self.assertEqual(result.mode, "pdf_excerpt")
        self.assertIn("OpenAlex authenticated DOI lookup matched W123456789", result.note)
        self.assertNotIn(secret, result.note)
        self.assertNotIn(secret, result.final_url)
        auth_header = oa_get.call_args.kwargs["headers"].get("Authorization")
        self.assertEqual(auth_header, f"Bearer {secret}")
        content_call = next(call for call in fetch_calls if call[0].startswith("https://content.openalex.org/"))
        self.assertEqual(content_call[1].get("Authorization"), f"Bearer {secret}")

    def test_deep_scan_preparation_workflows_expose_openalex_secret(self):
        workflows = [
            ".github/workflows/deep-scan-prepare-workers.yml",
            ".github/workflows/deep-scan-prepare-single.yml",
            ".github/workflows/deep-scan-import.yml",
            ".github/workflows/deep-scan-hardcore-recovery-prepare.yml",
            ".github/workflows/radar-v2-migration.yml",
        ]
        for rel in workflows:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("OPENALEX_API_KEY: ${{ secrets.OPENALEX_API_KEY }}", text, rel)

    def test_deep_scan_ep_route_uses_pdf_even_if_public_uri_is_blocked(self):
        pdf = "https://data.europarl.europa.eu/distribution/doc/TA-10-2026-0123_en.pdf"
        record = {
            "link": "https://data.europarl.europa.eu/eli/dl/doc/TA-10-2026-0123",
            "discovery_provenance": "europarl_open_data_adopted_text",
            "source_validation_url": pdf,
            "ep_document_pdf": pdf,
        }
        calls = []

        def fake_fetch(url, *, extra_headers=None):
            calls.append(url)
            if url == pdf:
                return deep.SourceRead("pdf_excerpt", "parliament adopted text " * 80, url, "")
            return deep.SourceRead("stored_only", "", url, "blocked")

        with patch.object(deep, "fetch_source", side_effect=fake_fetch):
            result = deep.fetch_source_for_record(record)
        self.assertEqual(result.mode, "pdf_excerpt")
        self.assertEqual(calls, [pdf])


    def test_parliament_budget_expiry_before_request_is_neutral(self):
        stats = {}
        warnings = []
        with patch.object(scan, "stage_deadline_reached", side_effect=[False, True]):
            rows = scan.collect_europarl_adopted_texts(
                dt.datetime(2026, 9, 22, 12, 0), warnings, stage_deadline=123.0, execution_stats=stats
            )
        self.assertEqual(rows, [])
        attempt = stats["source_transport_attempts"]["europarl_open_data"]
        self.assertEqual(attempt["status"], "skipped_budget")
        self.assertEqual(warnings, [])

    def test_quiet_successful_institution_feed_is_not_reported_as_failed(self):
        src = {"name": "Quiet Institute", "domain": "quiet.example", "tier": 1, "feeds": ["https://quiet.example/feed.xml"]}
        parsed = type("Parsed", (), {"entries": []})()
        with patch.object(scan, "get", return_value=_Resp(text="feed")), \
             patch.object(scan.feedparser, "parse", return_value=parsed), \
             patch.object(scan, "discover_sitemaps", return_value=[]):
            jobs, warning = scan._discover_domain(src, dt.date(2026, 9, 20))
        self.assertEqual(jobs, [])
        self.assertIsNone(warning)

    def test_source_health_does_not_count_unscheduled_source_as_new_failure(self):
        previous = {
            "scan_diagnostics": {
                "source_transport_health": {
                    "bruegel.org": {
                        "source": "Bruegel", "domain": "bruegel.org", "tier": 1,
                        "route": "institution_discovery", "last_status": "failed",
                        "failure_since": "2026-09-21T12:00Z", "consecutive_failures": 2,
                    }
                }
            }
        }
        warnings = []
        rolled = scan._roll_source_transport_health(previous, {}, dt.datetime(2026, 9, 22, 12, 0, tzinfo=dt.timezone.utc), warnings)
        self.assertEqual(rolled["bruegel.org"]["consecutive_failures"], 2)
        self.assertEqual(rolled["bruegel.org"]["failure_since"], "2026-09-21T12:00Z")
        self.assertEqual(warnings, [])

    def test_source_health_budget_skip_preserves_prior_failure_state(self):
        previous = {
            "scan_diagnostics": {
                "source_transport_health": {
                    "bruegel.org": {
                        "source": "Bruegel", "domain": "bruegel.org", "tier": 1,
                        "route": "institution_discovery", "last_status": "failed",
                        "failure_since": "2026-09-21T12:00Z", "consecutive_failures": 2,
                    }
                }
            }
        }
        attempts = {
            "bruegel.org": {
                "source": "Bruegel", "domain": "bruegel.org", "tier": 1,
                "route": "institution_discovery", "status": "skipped_budget", "jobs_found": 0, "note": "",
            }
        }
        rolled = scan._roll_source_transport_health(
            previous, attempts, dt.datetime(2026, 9, 22, 12, 0, tzinfo=dt.timezone.utc), []
        )
        self.assertEqual(rolled["bruegel.org"]["last_status"], "failed")
        self.assertEqual(rolled["bruegel.org"]["last_schedule_status"], "skipped_budget")
        self.assertEqual(rolled["bruegel.org"]["consecutive_failures"], 2)
        self.assertEqual(rolled["bruegel.org"]["failure_since"], "2026-09-21T12:00Z")

    def test_source_health_warns_only_after_persistent_tier1_failure(self):
        previous = {
            "scan_diagnostics": {
                "source_transport_health": {
                    "bruegel.org": {
                        "source": "Bruegel", "domain": "bruegel.org", "tier": 1,
                        "route": "institution_discovery", "last_status": "failed",
                        "failure_since": "2026-09-10T12:00Z", "consecutive_failures": 4,
                    }
                }
            }
        }
        attempts = {
            "bruegel.org": {
                "source": "Bruegel", "domain": "bruegel.org", "tier": 1,
                "route": "institution_discovery", "status": "failed", "jobs_found": 0, "note": "HTTP 503",
            }
        }
        warnings = []
        with patch("builtins.print"):
            scan._roll_source_transport_health(
                previous, attempts, dt.datetime(2026, 9, 22, 12, 0, tzinfo=dt.timezone.utc), warnings
            )
        self.assertTrue(any("Tier-1 source transport unhealthy" in w for w in warnings))
        source = SCAN_PATH.read_text(encoding="utf-8")
        self.assertIn("critical_source_transport_unhealthy", source)
        self.assertIn('health = "degraded"', source)

    def test_source_health_budget_skip_does_not_extend_or_clear_failure(self):
        previous = {
            "scan_diagnostics": {
                "source_transport_health": {
                    "bruegel.org": {
                        "source": "Bruegel", "domain": "bruegel.org", "tier": 1,
                        "route": "institution_discovery", "last_status": "failed",
                        "failure_since": "2026-09-21T12:00Z", "consecutive_failures": 2,
                    }
                }
            }
        }
        attempts = {
            "bruegel.org": {
                "source": "Bruegel", "domain": "bruegel.org", "tier": 1,
                "route": "institution_discovery", "status": "skipped_budget", "jobs_found": 0, "note": "",
            }
        }
        warnings = []
        rolled = scan._roll_source_transport_health(previous, attempts, dt.datetime(2026, 9, 22, 12, 0, tzinfo=dt.timezone.utc), warnings)
        self.assertEqual(rolled["bruegel.org"]["consecutive_failures"], 2)
        self.assertEqual(rolled["bruegel.org"]["failure_since"], "2026-09-21T12:00Z")
        self.assertEqual(rolled["bruegel.org"]["last_status"], "failed")
        self.assertEqual(rolled["bruegel.org"]["last_schedule_status"], "skipped_budget")
        self.assertEqual(warnings, [])

    def test_source_health_success_clears_failure_streak(self):
        previous = {
            "scan_diagnostics": {
                "source_transport_health": {
                    "bruegel.org": {
                        "source": "Bruegel", "domain": "bruegel.org", "tier": 1,
                        "route": "institution_discovery", "last_status": "failed",
                        "failure_since": "2026-09-10T12:00Z", "consecutive_failures": 4,
                    }
                }
            }
        }
        attempts = {
            "bruegel.org": {
                "source": "Bruegel", "domain": "bruegel.org", "tier": 1,
                "route": "institution_discovery", "status": "ok_empty", "jobs_found": 0, "note": "",
            }
        }
        warnings = []
        rolled = scan._roll_source_transport_health(previous, attempts, dt.datetime(2026, 9, 22, 12, 0, tzinfo=dt.timezone.utc), warnings)
        self.assertEqual(rolled["bruegel.org"]["consecutive_failures"], 0)
        self.assertEqual(rolled["bruegel.org"]["failure_since"], "")
        self.assertEqual(rolled["bruegel.org"]["last_status"], "ok_empty")
        self.assertEqual(warnings, [])

    def test_deep_reader_uses_same_honest_compatible_crawler_identity(self):
        self.assertIn("Mozilla/5.0 (compatible;", deep.USER_AGENT)
        self.assertIn("RI-Geopolitics-Radar-DeepScan", deep.USER_AGENT)
        self.assertIn("vevirm.github.io/radar_articles_reports", deep.USER_AGENT)


    def test_deep_scan_drop_unverifiable_must_audit_scanner_validation_route(self):
        attempts = [
            {"step": step, "outcome": "failed", "note": f"Concrete failed attempt for {step} using the supplied identity metadata."}
            for step in sorted(deep_import.REQUIRED_UNVERIFIABLE_STEPS)
        ]
        raw = {
            "verification": {
                "identity_verified": False, "evidence_depth": "",
                "retrieval_attempts": attempts, "recovered_sources": [],
                "verification_note": "The work could not be substantiated after the standard recovery ladder.",
            },
            "admission": {
                "decision": "drop_unverifiable", "target_strand": "",
                "reason_code": "UNVERIFIABLE", "reason": "The claimed work could not be substantiated after concrete retrieval attempts.",
            },
            "metadata_correction": {"fields": {}, "unset": [], "reason": ""},
            "duplicate": {"status": "unique", "duplicate_of": "", "reason": ""},
            "claims": [],
        }
        row = {
            "link": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R1234",
            "source_validation_url": "https://publications.europa.eu/resource/celex/32026R1234",
            "source_access": {"route": "eurlex_cellar", "validation_url": "https://publications.europa.eu/resource/celex/32026R1234"},
        }
        problems = deep_import.validate_v2_result(raw, key="x", current_keys={"x"}, current_row=row)
        self.assertTrue(any("scanner_validation_route" in p for p in problems), problems)

    def test_deep_scan_drop_unverifiable_rejects_successful_scanner_route(self):
        attempts = [
            {"step": step, "outcome": "failed", "note": f"Concrete failed attempt for {step} using the supplied identity metadata."}
            for step in sorted(deep_import.REQUIRED_UNVERIFIABLE_STEPS)
        ]
        attempts.append({
            "step": "scanner_validation_route", "outcome": "success",
            "note": "Retrieved the matching first-party Cellar document through the scanner validation URL.",
        })
        raw = {
            "verification": {
                "identity_verified": False, "evidence_depth": "",
                "retrieval_attempts": attempts, "recovered_sources": [],
                "verification_note": "The standard ladder was recorded including the scanner validation route.",
            },
            "admission": {
                "decision": "drop_unverifiable", "target_strand": "",
                "reason_code": "UNVERIFIABLE", "reason": "Attempted to close the item despite a successful first-party route.",
            },
            "metadata_correction": {"fields": {}, "unset": [], "reason": ""},
            "duplicate": {"status": "unique", "duplicate_of": "", "reason": ""},
            "claims": [],
        }
        row = {"source_validation_url": "https://publications.europa.eu/resource/celex/32026R1234"}
        problems = deep_import.validate_v2_result(raw, key="x", current_keys={"x"}, current_row=row)
        self.assertTrue(any("successful recovery step: scanner_validation_route" in p for p in problems), problems)

    def test_terminal_recovery_also_requires_scanner_validation_route(self):
        raw = {
            "verification": {
                "retrieval_attempts": [
                    {"step": step, "outcome": "failed", "note": f"Concrete terminal attempt for {step}."}
                    for step in sorted(hardcore_import.REQUIRED_NORMAL_STEPS)
                ]
            },
            "hardcore_recovery": {
                "routes": [], "try_harder_passes": [],
                "all_routes_exhausted": False, "terminal_reason": "Not yet exhausted for this regression test.",
            },
        }
        row = {"source_validation_url": "https://data.europarl.europa.eu/distribution/doc/TA-10-2026-0123_en.pdf"}
        problems = hardcore_import.validate_hardcore_audit(raw, exhausted=True, current_row=row)
        self.assertTrue(any("scanner_validation_route" in p for p in problems), problems)

    def test_deep_scan_package_instructions_protect_route_parity(self):
        text = (ROOT / "scripts" / "prepare_deep_scan_package.py").read_text(encoding="utf-8")
        self.assertIn("do not discard", text.lower())
        self.assertIn("source_validation_url", text)
        self.assertIn("fetch_source_for_record", text)
        self.assertIn("scanner_validation_route", text)


if __name__ == "__main__":
    unittest.main()
