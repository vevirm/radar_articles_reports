from pathlib import Path
import json
import subprocess
import sys
import types
import unittest

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules["feedparser"] = types.ModuleType("feedparser")

from scripts import scan_radar as scanner

ROOT = Path(__file__).resolve().parents[1]


class V17510PrecisionRepairTests(unittest.TestCase):
    def test_china_plus_generic_strategic_word_is_not_geopolitics(self):
        title = "Linguistically responsive pedagogies in undergraduate biology education in Zambian universities"
        abstract = (
            "This higher education review includes studies from China and several European universities. "
            "Success depends on professional development for lecturers and strategic use of local languages in teaching. "
            "The review discusses assessment practices and student learning outcomes."
        )
        ev = scanner.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertNotIn("China + security/strategic context", ev["geo_evidence"])


    def test_passing_european_comparator_does_not_create_direct_eu_scope(self):
        title = "Global collaboration and geopolitical competition in Indonesian forestry research"
        abstract = (
            "The study maps scientific collaboration in Indonesia and compares publications from China, Germany and Japan. "
            "It discusses geopolitics of research and strategic competition in global climate governance. "
            "The policy recommendations concern Indonesia's research capacity and international standing."
        )
        ev = scanner.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertIsNone(ev["eu_relevance"])
        self.assertFalse(ev["a_pass"])

    def test_true_china_strategic_competition_still_qualifies(self):
        title = "Germany research and innovation under strategic competition with China"
        abstract = (
            "Germany's research and innovation system faces strategic competition with China and technology controls. "
            "The study examines university research, R&D cooperation and technological capabilities in Europe."
        )
        ev = scanner.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertTrue(ev["a_pass"])

    def test_generic_education_scenario_method_is_not_transferable_strand_b(self):
        title = "Innovation in higher education teaching through stage-scenario practice"
        abstract = (
            "The study evaluates a teaching framework using scenario practice, digital feedback and assessment methods. "
            "It reports student learning outcomes and curriculum design in a university course."
        )
        ev = scanner.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["b_pass"])
        self.assertFalse(ev["b_transferable"])

    def test_explicit_ri_delphi_method_remains_transferable(self):
        title = "A new Delphi methodology for R&I foresight"
        abstract = (
            "This paper develops and evaluates a Delphi method for research and innovation foresight. "
            "It compares expert-selection, bias-control and weak-signal aggregation procedures for innovation policy."
        )
        ev = scanner.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertTrue(ev["b_pass"])
        self.assertTrue(ev["b_transferable"])
        self.assertEqual(ev["b_route"], "transfer")

    def test_targeted_cleanup_removes_transfer_pollution_and_zambia_false_positive(self):
        data = {
            "strand_a": [{
                "title": "Linguistically responsive pedagogies in undergraduate biology education",
                "summary": "Success requires lecturers to use local languages strategically in higher education teaching.",
                "type": "peer-reviewed article", "source_tier": "Tier 2 broad journal",
                "eu_relevance": "direct",
                "relevance_note": "Direct EU relevance; R&I evidence: higher education; strategic evidence: China + security/strategic context; bridge: title/abstract."
            }],
            "strand_b": [{
                "title": "Teaching model innovation in higher education",
                "summary": "The study evaluates scenario practice and assessment methods in a university course.",
                "type": "peer-reviewed article", "source_tier": "Tier 2 broad journal",
                "eu_relevance": "derived",
                "relevance_note": "Derived EU relevance; foresight methodology is substantive (methods, framework)."
            }],
        }
        cleaned, stats = scanner.cleanup_quality_profile_regressions(data)
        self.assertEqual(stats["strand_a"], 1)
        self.assertEqual(stats["strand_b"], 1)
        self.assertEqual(cleaned["strand_a"], [])
        self.assertEqual(cleaned["strand_b"], [])

    def test_frontier_uses_scanner_eu_scope_for_knowledge_research_security(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data={strand_a:[{
 title:'Research security and collaboration safeguards', source:'European research body', date:'2026-08-20', strand:'A', eu_relevance:'direct',
 summary:'Research security screening restricts international scientific collaboration, creates barriers and raises delay risks for universities while protecting sensitive research.'
}],strand_b:[],strand_c:[]};
const v=F.buildFrontier(data,{now:'2026-08-23T06:22:00Z'});
console.log(JSON.stringify({a:v.cells.knowledge.A.length,b:v.cells.knowledge.B.length,c:v.cells.knowledge.C.length,d:v.cells.knowledge.D.length}));
'''
        out = json.loads(subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True).stdout)
        self.assertGreaterEqual(out["b"], 1)


if __name__ == "__main__":
    unittest.main()
