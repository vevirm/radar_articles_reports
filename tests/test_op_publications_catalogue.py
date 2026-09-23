import datetime as dt
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import scan_radar as sr


class _JsonResponse:
    status_code = 200

    def __init__(self, bindings):
        self._bindings = bindings

    def json(self):
        return {"results": {"bindings": self._bindings}}


class OpPublicationsCatalogueTests(unittest.TestCase):
    def test_op_portal_release_date_is_read_from_visible_catalogue_metadata(self):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(
            """
            <html><body><main>
              <h1>The demographic turn</h1>
              <div>Published: 2025</div>
              <div>Released on EU publications website: 2025-12-10</div>
            </main></body></html>
            """,
            "html.parser",
        )
        got = sr._op_portal_publication_date(
            soup,
            "https://op.europa.eu/en/publication-detail/-/publication/6c154d71-d7d0-11f0-8da2-01aa75ed71a1/language-en",
        )
        self.assertEqual(got, dt.date(2025, 12, 10))

    def test_op_portal_subtitle_keeps_substantive_report_semantics(self):
        from bs4 import BeautifulSoup

        page = "https://op.europa.eu/en/publication-detail/-/publication/52028928-482a-11f1-8095-01aa75ed71a1/language-en"
        soup = BeautifulSoup(
            """
            <html><body><main>
              <h1>The futures of artificial intelligence</h1>
              <h2>Implications for Europe’s R&amp;I ecosystem. Part 5, Final report</h2>
              <h2>Publication metadata</h2>
            </main></body></html>
            """,
            "html.parser",
        )
        self.assertEqual(
            sr._op_portal_subtitle(soup, page),
            "Implications for Europe’s R&I ecosystem. Part 5, Final report",
        )

    def test_demographic_turn_is_admitted_as_completed_institutional_foresight_analysis(self):
        gate = sr.gate_scope(
            "The demographic turn",
            "Actions needed for research, innovation and policy in Europe",
            (
                "Demographic change is reshaping Europe. This foresight analysis reveals "
                "implications for scientific competitiveness. Policymakers can build an R&I "
                "system with protected funding and renewal of the workforce."
            ),
            1,
            "institutional",
        )
        self.assertTrue(gate["a_pass"])
        self.assertFalse(gate["b_pass"])
        self.assertEqual(gate["a_route"], "research-evidence")
        self.assertEqual(gate["eu_relevance"], "supported")

    def test_ai_futures_final_report_is_a_not_methods_library_b(self):
        gate = sr.gate_scope(
            "The futures of artificial intelligence",
            "Implications for Europe’s R&I ecosystem. Part 5, Final report",
            (
                "This report explores possible futures for artificial intelligence in Europe "
                "through three scenarios. It examines AI adoption constraints and strategic "
                "priorities for Europe's research and innovation ecosystem and scientific competitiveness."
            ),
            1,
            "institutional",
        )
        self.assertTrue(gate["a_pass"])
        self.assertFalse(gate["b_pass"])
        self.assertIn(gate["a_route"], {"research-evidence", "eu-ri-system-relevance"})
        self.assertEqual(gate["eu_relevance"], "supported")

    def test_generic_scenario_page_does_not_gain_institutional_foresight_waiver(self):
        gate = sr.gate_scope(
            "Possible futures of AI",
            "A workshop in Europe discusses possible futures",
            "Participants discuss three scenarios for AI adoption by a local company.",
            1,
            "institutional",
        )
        self.assertFalse(gate["a_pass"])
        self.assertFalse(gate["b_pass"])
        evidence_ok, _ = sr.research_evidence_route_ok(
            "Possible futures of AI",
            "A workshop in Europe discusses possible futures",
            "Participants discuss three scenarios for AI adoption by a local company.",
            "institutional",
            1,
        )
        self.assertFalse(evidence_ok)

    def test_cellar_catalogue_discovers_reader_facing_op_publication_page(self):
        uuid = "52028928-482a-11f1-8095-01aa75ed71a1"
        binding = {
            "w": {"value": f"http://publications.europa.eu/resource/cellar/{uuid}"},
            "date": {"value": "2026-05-04"},
            "title": {"value": "The futures of artificial intelligence"},
        }

        def fake_get(_url, *, params=None, **_kwargs):
            query = (params or {}).get("query", "")
            # Behave like the endpoint: only the thematic batch containing the relevant
            # phrase returns this work.
            return _JsonResponse([binding] if "artificial intelligence" in query else [])

        old_config = dict(sr.CONFIG)
        old_seen = set(sr.INSTITUTION_SEEN_FINGERPRINTS)
        old_dates = dict(sr.INSTITUTION_DISCOVERED_DATES)
        old_meta = dict(sr.OP_PUBLICATIONS_CATALOGUE_METADATA)
        try:
            sr.CONFIG["op_publications_catalogue_enabled"] = True
            sr.CONFIG["op_publications_catalogue_lookback_months"] = 6
            sr.CONFIG["op_publications_catalogue_title_terms"] = [
                "research", "innovation", "artificial intelligence", "foresight"
            ]
            sr.CONFIG["op_publications_catalogue_terms_per_query"] = 4
            sr.CONFIG["op_publications_catalogue_max_pages"] = 10
            sr.INSTITUTION_SEEN_FINGERPRINTS.clear()
            sr.INSTITUTION_DISCOVERED_DATES.clear()
            sr.OP_PUBLICATIONS_CATALOGUE_METADATA.clear()
            with mock.patch.object(sr.SESSION, "get", side_effect=fake_get), \
                 mock.patch.object(sr, "stage_deadline_reached", return_value=False), \
                 mock.patch.object(sr, "_known_institution_url_should_skip", return_value=False):
                jobs = sr._op_publications_catalogue_jobs(
                    {"name": "EU Publications Office", "domain": "op.europa.eu", "tier": 1},
                    dt.date(2026, 3, 23),
                )
        finally:
            sr.CONFIG.clear()
            sr.CONFIG.update(old_config)
            sr.INSTITUTION_SEEN_FINGERPRINTS.clear()
            sr.INSTITUTION_SEEN_FINGERPRINTS.update(old_seen)
            sr.INSTITUTION_DISCOVERED_DATES.clear()
            sr.INSTITUTION_DISCOVERED_DATES.update(old_dates)
            catalogue_meta = dict(sr.OP_PUBLICATIONS_CATALOGUE_METADATA)
            sr.OP_PUBLICATIONS_CATALOGUE_METADATA.clear()
            sr.OP_PUBLICATIONS_CATALOGUE_METADATA.update(old_meta)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(
            jobs[0][0],
            f"https://op.europa.eu/en/publication-detail/-/publication/{uuid}/language-en",
        )
        self.assertEqual(jobs[0][1], "EU Publications Office")
        self.assertEqual(jobs[0][2], 1)
        self.assertTrue(jobs[0][3].endswith("|2026-05-04"))
        self.assertEqual(catalogue_meta[sr.normalized_link(jobs[0][0])]["published"], "2026-05-04")
        self.assertEqual(catalogue_meta[sr.normalized_link(jobs[0][0])]["title"], "The futures of artificial intelligence")

    def test_op_adapter_keeps_catalogue_discovery_when_editorial_hubs_are_empty(self):
        url = "https://op.europa.eu/en/publication-detail/-/publication/52028928-482a-11f1-8095-01aa75ed71a1/language-en"
        src = {"name": "EU Publications Office", "domain": "op.europa.eu", "tier": 1}
        with mock.patch.object(
            sr,
            "_op_publications_catalogue_jobs",
            return_value=[(url, "EU Publications Office", 1, "catalogue-fp")],
        ), mock.patch.object(sr, "get", return_value=None), \
             mock.patch.object(sr, "stage_deadline_reached", return_value=False), \
             mock.patch.object(sr, "_known_institution_url_should_skip", return_value=False):
            jobs = sr._source_adapter_domain_jobs(src, dt.date(2026, 3, 23))
        match = next(row for row in jobs if row[0] == url)
        self.assertEqual(match[3], "catalogue-fp")

    def test_op_catalogue_discovery_does_not_depend_on_editorial_hub_profile(self):
        url = "https://op.europa.eu/en/publication-detail/-/publication/52028928-482a-11f1-8095-01aa75ed71a1/language-en"
        src = {"name": "EU Publications Office", "domain": "op.europa.eu", "tier": 1}
        old_config = dict(sr.CONFIG)
        try:
            profiles = dict(sr.CONFIG.get("institution_source_adapters", {}))
            profiles.pop("op.europa.eu", None)
            sr.CONFIG["institution_source_adapters"] = profiles
            with mock.patch.object(
                sr, "_op_publications_catalogue_jobs",
                return_value=[(url, "EU Publications Office", 1, "catalogue-fp")],
            ):
                jobs = sr._source_adapter_domain_jobs(src, dt.date(2026, 3, 23))
        finally:
            sr.CONFIG.clear()
            sr.CONFIG.update(old_config)
        self.assertEqual(jobs, [(url, "EU Publications Office", 1, "catalogue-fp")])

    def test_op_cellar_fallback_prefers_catalogue_date_over_pdf_metadata(self):
        body = (
            "The futures of artificial intelligence. Europe research and innovation policy "
            "foresight scenarios strategic technology competitiveness resilience. " * 30
        )
        with mock.patch.object(sr, "stage_deadline_reached", return_value=False), \
             mock.patch.object(sr, "_known_institution_url_should_skip", return_value=False), \
             mock.patch.object(sr, "_pdf_payload", return_value=(body, len(body.split()), {
                 "title": "The futures of artificial intelligence",
                 "author": "European Commission",
                 "creation_date": "D:20260401000000",
                 "modification_date": "",
             })), \
             mock.patch.object(sr, "english_record_ok", return_value=True), \
             mock.patch.object(sr, "document_exclusion_reason", return_value=""), \
             mock.patch.object(sr, "gate_scope", return_value={
                 "a_pass": True, "b_pass": False, "eu_relevance": "EU",
                 "ri_evidence": ["research"], "geo_evidence": [],
                 "foresight_evidence": [], "method_evidence": [],
             }), \
             mock.patch.object(sr, "_record_ab_gate_diagnostic"), \
             mock.patch.object(sr, "build_item", side_effect=lambda **kw: {
                 "date": kw["date"].isoformat(), "title": kw["title"], "link": kw["link"]
             }), \
             mock.patch.object(sr, "_mark_institution_seen"):
            row = sr.parse_institution_pdf(
                "https://publications.europa.eu/resource/cellar/52028928-482a-11f1-8095-01aa75ed71a1",
                "EU Publications Office",
                1,
                fallback_publication_date=dt.date(2026, 5, 4),
                fallback_date_basis="op_catalogue_work_date",
                prefer_fallback_publication_date=True,
            )
        self.assertEqual(row["date"], "2026-05-04")
        self.assertEqual(row["date_basis"], "op_catalogue_work_date")


    def test_op_uuid_and_cellar_resource_translation_cover_detail_and_download_urls(self):
        uuid = "52028928-482a-11f1-8095-01aa75ed71a1"
        detail = f"https://op.europa.eu/en/publication-detail/-/publication/{uuid}/language-en"
        handler = (
            "https://op.europa.eu/o/opportal-service/download-handler"
            f"?identifier={uuid}&format=pdf&language=en&productionSystem=cellar&part="
        )
        cellar = f"https://publications.europa.eu/resource/cellar/{uuid}"
        self.assertEqual(sr._op_publication_uuid(detail), uuid)
        self.assertEqual(sr._op_publication_uuid(handler), uuid)
        self.assertEqual(sr._op_publication_uuid(cellar), uuid)
        self.assertEqual(sr._op_cellar_resource_url(detail), cellar)
        self.assertTrue(sr._same_op_publication_identity(detail, handler))
        self.assertTrue(sr._same_op_publication_identity(detail, cellar))
        self.assertFalse(sr._same_op_publication_identity(detail, "https://example.org/report.pdf"))

    def test_cellar_pdf_request_uses_documented_english_pdf_negotiation(self):
        uuid = "52028928-482a-11f1-8095-01aa75ed71a1"
        detail = f"https://op.europa.eu/en/publication-detail/-/publication/{uuid}/language-en"
        expected = f"https://publications.europa.eu/resource/cellar/{uuid}"
        response = mock.Mock(status_code=200, content=b"%PDF-test")
        with mock.patch.object(sr, "deadline_reached", return_value=False), \
             mock.patch.object(sr.SESSION, "get", return_value=response) as mocked_get:
            got = sr._op_cellar_pdf_response(detail, 11)
        self.assertIs(got, response)
        args, kwargs = mocked_get.call_args
        self.assertEqual(args[0], expected)
        self.assertEqual(kwargs["headers"]["Accept"], "application/pdf")
        self.assertEqual(kwargs["headers"]["Accept-Language"], "eng")
        self.assertEqual(kwargs["headers"]["Accept-Max-Cs-Size"], "22000000")

    def test_throttled_op_landing_page_falls_back_to_catalogue_cellar_pdf(self):
        uuid = "52028928-482a-11f1-8095-01aa75ed71a1"
        page = f"https://op.europa.eu/en/publication-detail/-/publication/{uuid}/language-en"
        cellar = f"https://publications.europa.eu/resource/cellar/{uuid}"
        title = "The futures of artificial intelligence"
        old_meta = dict(sr.OP_PUBLICATIONS_CATALOGUE_METADATA)
        try:
            sr.OP_PUBLICATIONS_CATALOGUE_METADATA.clear()
            sr.OP_PUBLICATIONS_CATALOGUE_METADATA[sr.normalized_link(page)] = {
                "title": title,
                "published": dt.date(2026, 5, 4),
                "cellar_id": uuid,
            }
            parsed = {"title": title, "link": cellar, "source": "EU Publications Office"}
            with mock.patch.object(sr, "parse_institution_pdf", return_value=parsed.copy()) as parse_pdf:
                got = sr._op_catalogue_pdf_fallback(
                    page, "EU Publications Office", 1, fingerprint="fp", publication_floor=dt.date(2026, 3, 23)
                )
            self.assertIsNotNone(got)
            self.assertEqual(got["link"], page)
            self.assertEqual(got["source_validation_url"], cellar)
            self.assertEqual(got["source_access"]["route"], "op_cellar_catalogue_pdf")
            kwargs = parse_pdf.call_args.kwargs
            self.assertEqual(parse_pdf.call_args.args[0], cellar)
            self.assertEqual(kwargs["title_hint"], title)
            self.assertEqual(kwargs["fallback_publication_date"], dt.date(2026, 5, 4))
            self.assertEqual(kwargs["landing_page_url"], page)
            self.assertTrue(kwargs["prefer_fallback_publication_date"])
        finally:
            sr.OP_PUBLICATIONS_CATALOGUE_METADATA.clear()
            sr.OP_PUBLICATIONS_CATALOGUE_METADATA.update(old_meta)

    def test_page_parser_invokes_cellar_fallback_when_portal_fetch_is_throttled(self):
        page = "https://op.europa.eu/en/publication-detail/-/publication/52028928-482a-11f1-8095-01aa75ed71a1/language-en"
        expected = {"title": "The futures of artificial intelligence", "link": page}
        with mock.patch.object(sr, "stage_deadline_reached", return_value=False), \
             mock.patch.object(sr, "_known_institution_url_should_skip", return_value=False), \
             mock.patch.object(sr, "get", return_value=None), \
             mock.patch.object(sr, "_op_catalogue_pdf_fallback", return_value=expected) as fallback:
            got = sr.parse_institution_page(page, "EU Publications Office", 1)
        self.assertIs(got, expected)
        fallback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
