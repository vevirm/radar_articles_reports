from pathlib import Path
import datetime as dt
import importlib.util
import json
import sys
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_source_transport_repair", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class _Resp:
    def __init__(self, *, text="", content=None, status_code=200, payload=None):
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.status_code = status_code
        self._payload = payload

    def __bool__(self):
        return self.status_code == 200

    def json(self):
        return self._payload


class SourceTransportRepairTests(unittest.TestCase):
    def setUp(self):
        scan.INSTITUTION_SEEN_FINGERPRINTS.clear()
        scan.KNOWN_SIGNAL_IDENTITIES.clear()

    def test_sitemap_discovery_tries_bare_and_www_hosts(self):
        calls = []

        def fake_get(url, **kwargs):
            calls.append(url)
            if url == "https://example.org/robots.txt":
                return _Resp(text="Sitemap: https://example.org/custom.xml\n")
            if url == "https://www.example.org/robots.txt":
                return _Resp(text="Sitemap: https://www.example.org/custom.xml\n")
            return None

        with patch.object(scan, "get", side_effect=fake_get):
            urls = scan.discover_sitemaps("example.org")

        self.assertIn("https://example.org/robots.txt", calls)
        self.assertIn("https://www.example.org/robots.txt", calls)
        self.assertIn("https://example.org/custom.xml", urls)
        self.assertIn("https://www.example.org/custom.xml", urls)
        self.assertIn("https://www.example.org/sitemap.xml", urls)

    def test_institution_feed_is_discovery_only_and_same_domain(self):
        entry_ok = types.SimpleNamespace(
            link="https://www.bruegel.org/analysis/new-report",
            published_parsed=time.struct_time((2026, 9, 21, 0, 0, 0, 0, 0, -1)),
            updated_parsed=None,
        )
        entry_cross_domain = types.SimpleNamespace(
            link="https://other.example/report",
            published_parsed=time.struct_time((2026, 9, 21, 0, 0, 0, 0, 0, -1)),
            updated_parsed=None,
        )
        parsed = types.SimpleNamespace(entries=[entry_ok, entry_cross_domain])
        src = {
            "name": "Bruegel",
            "domain": "bruegel.org",
            "tier": 1,
            "feeds": ["https://www.bruegel.org/rss.xml"],
        }
        with patch.object(scan, "get", return_value=_Resp(text="feed")), patch.object(scan.feedparser, "parse", return_value=parsed):
            jobs = scan._institution_feed_jobs(src, dt.date(2026, 9, 20))

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0][0], entry_ok.link)
        self.assertEqual(jobs[0][1], "Bruegel")
        # A feed produces parser jobs, not admitted radar rows.
        self.assertEqual(len(jobs[0]), 4)

    def test_cellar_returns_first_party_text_with_reader_facing_eurlex_link(self):
        sparql_payload = {
            "results": {
                "bindings": [{
                    "celex": {"value": "32026R9999"},
                    "date": {"value": "2026-09-21"},
                    "title": {"value": "Regulation on artificial intelligence research and innovation capacity"},
                }]
            }
        }
        long_body = " ".join([
            "This adopted regulation establishes European research and innovation measures for artificial intelligence technology capacity."
        ] * 8)
        responses = [
            _Resp(payload=sparql_payload),
            _Resp(text=f"<html><body><main>{long_body}</main></body></html>"),
        ]
        with patch.object(scan.SESSION, "get", side_effect=responses):
            rows = scan.collect_eurlex_cellar(dt.datetime(2026, 9, 22, 12, 0), [])

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["source"], "EUR-Lex")
        self.assertEqual(row["celex"], "32026R9999")
        self.assertEqual(row["discovery_provenance"], "eurlex_cellar")
        self.assertTrue(row["link"].startswith("https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:"))
        self.assertIn("adopted regulation", row["_desc"].lower())

    def test_cellar_candidate_still_passes_existing_c_admission_gate(self):
        row = {
            "headline": "Regulation on artificial intelligence research and innovation capacity",
            "source": "EUR-Lex",
            "source_domain": "eur-lex.europa.eu",
            "date": "2026-09-21",
            "date_basis": "cellar_work_date_document",
            "link": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R9999",
            "language": "en",
            "celex": "32026R9999",
            "source_validation_url": "https://publications.europa.eu/resource/celex/32026R9999",
            "source_access": {
                "route": "eurlex_cellar",
                "celex": "32026R9999",
                "validation_url": "https://publications.europa.eu/resource/celex/32026R9999",
            },
            "_desc": (
                "The European Union adopted this regulation establishing binding measures for artificial intelligence "
                "research infrastructure, innovation capacity, research security, data governance and strategic "
                "technology capability in the European Research Area. The regulation enters into force and changes "
                "obligations for European research organisations and technology providers."
            ),
            "_desc_html": "",
            "_themes": list(scan.themes_for(
                "Regulation artificial intelligence research innovation capacity European Union strategic technology"
            )),
            "_entities": [],
            "_institutional_signal": True,
            "_trusted_europe_publication": True,
            "_formal_proposal_signal": True,
            "_strategic_source_text": "binding regulation research innovation artificial intelligence European Union",
        }
        diagnostics = []
        admitted = scan.anchor_news([row], [], diagnostics, allow_unanchored=True)
        self.assertEqual(len(admitted), 1, diagnostics)
        self.assertEqual(admitted[0].get("c_admission_basis"), "trusted_europe_publication")
        self.assertEqual(admitted[0].get("source_access", {}).get("route"), "eurlex_cellar")
        self.assertEqual(admitted[0].get("source_validation_url"), "https://publications.europa.eu/resource/celex/32026R9999")

    def test_cellar_transport_is_degraded_when_relevant_act_cannot_be_read(self):
        payload = {
            "results": {
                "bindings": [{
                    "celex": {"value": "32026R9999"},
                    "date": {"value": "2026-09-21"},
                    "title": {"value": "Regulation on artificial intelligence research and innovation capacity"},
                }]
            }
        }
        stats = {}
        warnings = []
        with patch.object(scan.SESSION, "get", side_effect=[_Resp(payload=payload), _Resp(status_code=403)]):
            rows = scan.collect_eurlex_cellar(dt.datetime(2026, 9, 22, 12, 0), warnings, execution_stats=stats)
        self.assertEqual(rows, [])
        self.assertEqual(stats["source_transport_attempts"]["eurlex_cellar"]["status"], "degraded")
        self.assertTrue(any("no substantive Cellar text" in w for w in warnings))

    def test_cellar_rejects_future_dated_records(self):
        payload = {
            "results": {
                "bindings": [{
                    "celex": {"value": "32029R9999"},
                    "date": {"value": "2029-01-01"},
                    "title": {"value": "Regulation on digital research and innovation"},
                }]
            }
        }
        with patch.object(scan.SESSION, "get", return_value=_Resp(payload=payload)) as mocked:
            rows = scan.collect_eurlex_cellar(dt.datetime(2026, 9, 22, 12, 0), [])
        self.assertEqual(rows, [])
        self.assertEqual(mocked.call_count, 1)  # no text fetch for impossible dates

    def test_crossref_mailto_is_attached_when_configured(self):
        old = scan.CROSSREF_MAILTO
        try:
            scan.CROSSREF_MAILTO = "radar@example.org"
            self.assertEqual(scan.crossref_params({"rows": 5}).get("mailto"), "radar@example.org")
            self.assertEqual(scan.crossref_params({"mailto": "explicit@example.org"}).get("mailto"), "explicit@example.org")
        finally:
            scan.CROSSREF_MAILTO = old

    def test_science_uses_exact_crossref_issn_configuration(self):
        self.assertEqual(scan.CONFIG.get("crossref_journal_issns", {}).get("Science"), "0036-8075")
        self.assertIn("Science", scan.CONFIG.get("crossref_priority_journals", []))
        source = SCAN_PATH.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count('f"issn:{issn}"'), 2)
        self.assertGreaterEqual(source.count('params.pop("query.container-title", None)'), 2)

    def test_partial_stage_budget_no_longer_forces_degraded_health(self):
        source = SCAN_PATH.read_text(encoding="utf-8")
        health_line = next(line for line in source.splitlines() if 'health = "degraded" if' in line)
        self.assertNotIn("partial_budget_hit", health_line)
        self.assertIn("overall_budget_hit", health_line)
        self.assertIn("fatal_stage_error", health_line)

    def test_inherited_audit_crossref_call_uses_session_not_get_helper(self):
        payload = {"message": {"title": ["European research security"], "abstract": "substantive abstract text"}}
        old = scan.CROSSREF_MAILTO
        scan.CROSSREF_MAILTO = "radar@example.org"
        try:
            with patch.object(scan.SESSION, "get", return_value=_Resp(payload=payload)) as mocked:
                refreshed = scan._audit_refresh_document({"link": "https://doi.org/10.1234/example", "title": "Old title"})
        finally:
            scan.CROSSREF_MAILTO = old
        self.assertEqual(refreshed, ("European research security", "substantive abstract text", ""))
        self.assertEqual(mocked.call_args.kwargs["params"].get("mailto"), "radar@example.org")

    def test_deep_a_inherited_audit_does_not_pass_params_to_small_get_helper(self):
        deep_a = (ROOT / "scripts" / "scan_radar_deep_a.py").read_text(encoding="utf-8")
        self.assertNotIn('r = get(f"https://api.crossref.org/works/{quote_plus(doi)}", params=', deep_a)

    def test_wild_a_scanner_keeps_normal_rand_prefix_route(self):
        deep_a = (ROOT / "scripts" / "scan_radar_deep_a.py").read_text(encoding="utf-8")
        self.assertIn("def collect_crossref_prefix_sources(", deep_a)
        self.assertIn("Crossref exact publisher prefix", deep_a)

    def test_rand_exact_prefix_discovery_uses_ordinary_crossref_admission(self):
        item = {
            "DOI": "10.7249/RRA9999-1",
            "title": ["European technology security and research capacity"],
            "abstract": "substantive metadata supplied by the publisher",
            "publisher": "RAND Corporation",
            "type": "report",
            "published": {"date-parts": [[2026, 9, 20]]},
            "URL": "https://doi.org/10.7249/RRA9999-1",
        }
        admitted = {"title": item["title"][0], "link": "https://doi.org/10.7249/RRA9999-1"}
        stats = {}
        prefix_cfg = [{
            "name": "RAND Corporation",
            "prefix": "10.7249",
            "enabled": True,
            "lookback_days": 30,
            "max_rows": 24,
            "missing_abstract_enrichment": 4,
        }]
        with patch.dict(scan.CONFIG, {"crossref_prefix_sources": prefix_cfg}, clear=False), \
             patch.object(scan.SESSION, "get", return_value=_Resp(payload={"message": {"items": [item]}})) as mocked, \
             patch.object(scan, "candidate_from_crossref", return_value=admitted) as converter:
            rows = scan.collect_crossref_prefix_sources(dt.date(2026, 9, 1), [], execution_stats=stats)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["discovery_provenance"], "crossref_doi_prefix")
        self.assertEqual(rows[0]["crossref_prefix"], "10.7249")
        self.assertIn("/prefixes/10.7249/works", mocked.call_args.args[0])
        self.assertIn("from-pub-date:", mocked.call_args.kwargs["params"]["filter"])
        converter.assert_called_once()
        self.assertEqual(stats["crossref_prefix_candidates"], 1)

    def test_prefix_lane_is_dormant_by_default(self):
        sources = scan.CONFIG.get("crossref_prefix_sources", [])
        enabled = {x.get("name"): x.get("prefix") for x in sources if isinstance(x, dict) and x.get("enabled", True)}
        self.assertEqual(enabled, {})

    def test_targeted_blocked_source_queries_are_configured(self):
        queries = set(scan.CONFIG.get("news_global_queries", []))
        expected = {
            "Council of the EU adopts research innovation",
            "OECD report science technology innovation",
            "IEA critical minerals Europe report",
            "Chatham House Europe technology",
            "UNCTAD technology report",
        }
        self.assertTrue(expected.issubset(queries))

    def test_rss_feeds_configured_for_bruegel_and_academy(self):
        sources = {row.get("name"): row for row in scan.CONFIG.get("institution_sources", [])}
        self.assertEqual(sources["Bruegel"].get("feeds"), ["https://www.bruegel.org/rss.xml"])
        self.assertEqual(
            sources["French Academy of Sciences"].get("feeds"),
            ["https://www.academie-sciences.fr/en/rss.xml"],
        )


if __name__ == "__main__":
    unittest.main()
