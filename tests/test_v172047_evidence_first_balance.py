import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_scan_v172047", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class EvidenceFirstBalanceTests(unittest.TestCase):
    def test_empirical_eu_ri_paper_can_pass_without_news_style_geopolitical_title(self):
        ev = scan.gate_scope(
            "Innovation performance across European regions: new evidence from patents",
            (
                "We use patent and publication data to evaluate innovation performance, R&D intensity, "
                "research productivity and technology transfer across EU member states. Results show "
                "persistent capability gaps in the European research and innovation system."
            ),
            "",
            1,
            source_kind="scholarly",
        )
        self.assertTrue(ev["a_pass"])
        self.assertIn(ev["a_route"], {"research-evidence", "eu-ri-system-relevance", "explicit-geopolitics", "triangulated-strategic-context"})

    def test_local_applied_ai_case_does_not_qualify_as_system_evidence(self):
        title = "How to customize generative artificial intelligence? Case Finnish hospital construction"
        abstract = (
            "This study analyses generative AI use in a Finnish hospital construction project "
            "using interviews and case evidence."
        )
        ev = scan.gate_scope(title, abstract, "", 1, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        item = {
            "title": title,
            "summary": abstract,
            "type": "peer-reviewed article",
            "source": "Aalto University",
            "date": "2026-08-17",
            "source_tier": "Tier 1",
            "eu_relevance": "direct",
            "_source_rank": 1.0,
            "_confidence": 3,
            "strand": "A",
        }
        self.assertFalse(scan.final_ab_candidate_worthiness(item))

    def test_completed_research_evidence_ranks_above_routine_funding_notice(self):
        paper = {
            "title": "European research collaboration and innovation performance",
            "summary": "Empirical evidence from publication and patent data.",
            "type": "peer-reviewed article",
            "source": "Research Policy",
            "date": "2026-09-01",
            "source_tier": "Tier 1",
            "eu_relevance": "direct",
            "_source_rank": 1.0,
            "_confidence": 4,
            "strand": "A",
        }
        notice = {
            "title": "Commission announces Horizon Europe funding awards for 2026",
            "summary": "The Commission announces new funding awards under Horizon Europe.",
            "type": "official notice / primary source",
            "source": "European Commission",
            "date": "2026-09-02",
            "source_tier": "Tier 1",
            "eu_relevance": "direct",
            "_source_rank": 1.0,
            "_confidence": 4,
            "strand": "A",
        }
        self.assertGreater(scan.evidence_product_priority_score(paper), scan.evidence_product_priority_score(notice))
        self.assertLess(scan.rank_candidate(paper), scan.rank_candidate(notice))

    def test_selection_reserves_slots_for_completed_evidence(self):
        cfg_target = int(scan.CONFIG.get("evidence_product_min_slots_per_scan", 0) or 0)
        self.assertGreaterEqual(cfg_target, 3)
        notices = [
            {
                "title": f"EU funding announcement {i}",
                "summary": "Routine programme announcement.",
                "type": "official notice / primary source",
                "source": "European Commission",
                "date": f"2026-09-0{i+1}",
                "source_tier": "Tier 1",
                "eu_relevance": "direct",
                "_source_rank": 1.0,
                "_confidence": 5,
                "strand": "A",
                "link": f"https://example.eu/notice/{i}",
            }
            for i in range(5)
        ]
        papers = [
            {
                "title": f"European R&I empirical paper {i}",
                "summary": "Empirical evidence and results.",
                "type": "peer-reviewed article",
                "source": "Research Policy",
                "date": f"2026-08-2{i+1}",
                "source_tier": "Tier 1",
                "eu_relevance": "direct",
                "_source_rank": 1.5,
                "_confidence": 3,
                "strand": "A",
                "link": f"https://doi.org/10.1234/evidence{i}",
            }
            for i in range(3)
        ]
        selected = scan.select_balanced_new_ab(notices + papers, 5)
        self.assertGreaterEqual(sum(scan.evidence_product_candidate(x) for x in selected), 3)

    def test_config_has_dedicated_evidence_queries_and_report_sources(self):
        cfg = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cfg.get("evidence_first_queries", [])), 20)
        self.assertGreaterEqual(int(cfg.get("evidence_first_queries_per_scan", 0)), 8)
        domains = set(cfg.get("evidence_report_priority_domains", []))
        for expected in ("publications.jrc.ec.europa.eu", "oecd.org", "europarl.europa.eu"):
            self.assertIn(expected, domains)


if __name__ == "__main__":
    unittest.main()
