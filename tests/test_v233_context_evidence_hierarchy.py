import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shock_inference as si
import scan_radar as scanner


class ContextEvidenceHierarchyTests(unittest.TestCase):
    def row(self, title, source, *, new=False, strand="A", role=None, weight=None, merit=96):
        x = {
            "title": title,
            "source": source,
            "date": "2026-09-08",
            "link": f"https://{source.lower().replace(' ', '')}.example/{abs(hash((title, source))) % 1000000}",
            "source_tier": "Tier 1",
            "source_merit_score": merit,
            "new_this_scan": new,
        }
        if role is not None:
            x["evidence_role"] = role
        if weight is not None:
            x["analytical_weight"] = weight
        if strand:
            x["strand"] = strand
        return x

    def primary_fixture(self, fresh_coupling=False):
        # talent × security_reclassification is intentionally not in STATIC_OVERLAPS.
        return [
            self.row("Research talent exposed to research security screening in Europe", "Source One", new=fresh_coupling, merit=90),
            self.row("Europe seeks to retain research talent and researcher mobility", "Source Two", merit=98),
            self.row("Research careers and brain drain remain strategic European issues", "Source Three", merit=97),
            self.row("Research security and knowledge security rules are tightening", "European Commission", merit=99),
        ]

    def test_rows_exclude_b_and_weight_c_and_history(self):
        data = {
            "strand_a": [self.row("Research talent in Europe", "A Source")],
            "strand_b": [self.row("Strategic foresight methodology", "B Source", strand="B")],
            "strand_c": [self.row("Analysis: research talent security pressure is rising", "Reuters", new=True, strand="C", role="weak_signal", weight=.3)],
            "historical_context": [self.row("Earlier research talent security concerns", "Historical Source", strand="A")],
            "shock_inference_weights": {"weak_signal": .3, "historical_context": .45},
        }
        rows = si._rows(data)
        self.assertNotIn("B", {x["_strand"] for x in rows})
        c = next(x for x in rows if x["_strand"] == "C")
        h = next(x for x in rows if x["_strand"] == "H")
        self.assertEqual(c["_evidence_weight"], .3)
        self.assertFalse(c["_primary_evidence"])
        self.assertEqual(h["_evidence_weight"], .45)
        self.assertFalse(h["new_this_scan"])
        self.assertFalse(h["_primary_evidence"])

    def test_c_cannot_supply_missing_primary_coupling(self):
        a = [
            self.row("Europe seeks to retain research talent", "Source One"),
            self.row("Research careers and brain drain in Europe", "Source Two"),
            self.row("Research security and knowledge security rules are tightening", "European Commission"),
            self.row("Foreign interference raises research security concerns", "Source Four"),
        ]
        c = [self.row("Analysis: research talent faces research security screening", "Reuters", new=True, strand="C", role="weak_signal", weight=.3)]
        rows = si._rows({"strand_a": a, "strand_c": c})
        self.assertIsNone(si._candidate("talent", "security_reclassification", rows))

    def test_fresh_c_updates_but_does_not_make_existing_seam_new(self):
        a = self.primary_fixture(fresh_coupling=False)
        c = [self.row("Analysis: research talent faces research security screening pressure", "Reuters", new=True, strand="C", role="weak_signal", weight=.3)]
        h = [self.row("Historical research talent and research security tension", "Historical Institute", strand="A")]
        rows = si._rows({
            "strand_a": a,
            "strand_c": c,
            "historical_context": h,
            "shock_inference_weights": {"weak_signal": .3, "historical_context": .45},
        })
        cand = si._candidate("talent", "security_reclassification", rows)
        self.assertIsNotNone(cand)
        self.assertFalse(cand["fresh_coupling"])
        self.assertGreaterEqual(cand["weak_signal_context_count"], 1)
        self.assertGreaterEqual(cand["historical_context_count"], 1)
        self.assertLessEqual(cand["context_score_bonus"], 5.0)

        fresh_state = si.refresh_shock_inference({
            "strand_a": a,
            "strand_c": c,
            "historical_context": h,
            "shock_inference_weights": {"weak_signal": .3, "historical_context": .45},
        }, {}, "2026-09-08T20:00:00Z")
        self.assertEqual(fresh_state["new_count"], 0, "A fresh C item must not originate a new shock")

        old = dict(cand)
        old["fingerprint"] = "older-fingerprint"
        old["first_inferred_at"] = "2026-09-01T00:00:00Z"
        updated_state = si.refresh_shock_inference({
            "strand_a": a,
            "strand_c": c,
            "historical_context": h,
            "shock_inference_weights": {"weak_signal": .3, "historical_context": .45},
        }, {"dynamic_shocks": [old]}, "2026-09-08T20:00:00Z")
        self.assertEqual(updated_state["updated_count"], 1, "Fresh C may update an already-existing supported seam")

    def test_fresh_primary_coupling_can_originate_new_shock(self):
        a = self.primary_fixture(fresh_coupling=True)
        state = si.refresh_shock_inference({"strand_a": a}, {}, "2026-09-08T20:00:00Z")
        self.assertGreaterEqual(state["new_count"], 1)


    def test_c_discovery_really_uses_sixty_days_and_trusted_commentary_lane(self):
        self.assertTrue(all("when:60d" in q for q in scanner.news_queries("reuters.com", 1440)))
        self.assertGreaterEqual(int(scanner.CONFIG.get("b_method_lookback_years", 0)), 10)
        self.assertLessEqual(int(scanner.CONFIG.get("queries_b_method_per_scan", 99)), 12)
        self.assertAlmostEqual(float(scanner.CONFIG.get("weak_signal_context_weight", 0)), .30)
        self.assertTrue(scanner.trusted_analytical_commentary_candidate(
            "Analysis: Europe’s research security dilemma is changing",
            "New export controls could restrict European university access to advanced chips and research collaboration because evidence shows strategic dependencies are deepening.",
            "Reuters", "reuters.com", "https://reuters.com/example",
        ))

    def test_priorities_exclude_b_and_attach_c_only_as_context(self):
        js = r'''
const P=require('./priorities/priorities.js');
const lens=(type,passage)=>({primary:type,lenses:[{type,passage,components:{mechanism:'could restrict',carrier:'outside actor',asset:'research talent',forward:'could',loss:'loss'}}]});
const data={
  strand_a:[{title:'Research security pressure on European research talent',source:'Primary Institute',date:'2026-09-01',link:'https://primary.example/a',source_tier:'Tier 1',strategic_classification_source:'source_text',strategic_classification:lens('risk','Research security rules could restrict researcher mobility and research talent in Europe.')}],
  strand_b:[{title:'Research security foresight method',source:'Methods Journal',date:'2026-09-02',link:'https://methods.example/b',source_tier:'Tier 1',strategic_classification_source:'source_text',strategic_classification:lens('risk','Research security could restrict research talent in Europe.')}],
  strand_c:[{title:'Analysis: research security pressure on European research talent',source:'Reuters',date:'2026-09-08',link:'https://reuters.example/c',evidence_role:'weak_signal',evidence_status:'low',analytical_weight:.3,strategic_classification_source:'source_text',strategic_classification:lens('risk','Research security could restrict researcher mobility and research talent in Europe.')}]
};
const rows=P.lensRows(data);
const view=P.buildPriorityView(data,{limit:10});
console.log(JSON.stringify({rows:rows.map(x=>({source:x.source,contextOnly:x.contextOnly})),risks:view.risks.map(x=>({source:x.source,ctx:(x.weakSignalContext||[]).map(c=>c.source),weight:x.contextWeightTotal})),stats:view.stats}));
'''
        cp = subprocess.run(["node", "-e", js], cwd=ROOT, check=True, text=True, capture_output=True)
        out = json.loads(cp.stdout)
        self.assertFalse(any(r["source"] == "Methods Journal" for r in out["rows"]))
        self.assertEqual(len(out["risks"]), 1)
        self.assertEqual(out["risks"][0]["source"], "Primary Institute")
        self.assertEqual(out["risks"][0]["ctx"], ["Reuters"])
        self.assertEqual(out["risks"][0]["weight"], .3)


if __name__ == "__main__":
    unittest.main()
