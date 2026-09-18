import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TrendsCurrentHistoryTests(unittest.TestCase):
    def run_node(self, source: str):
        proc = subprocess.run(
            ["node", "-e", source],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(proc.stdout)

    def test_published_pairs_pass_simple_current_gate(self):
        payload = self.run_node(
            """
const fs=require('fs');
const T=require('./trends/trends.js');
const d=JSON.parse(fs.readFileSync('radar.json','utf8'));
const h=JSON.parse(fs.readFileSync('historical/historical.json','utf8'));
const out=T.build(d,h);
console.log(JSON.stringify(out.map(p=>({
  id:p.id,
  left_n:p.left.evidence.length,
  right_n:p.right.evidence.length,
  left_sources:p.left.sourceCount,
  right_sources:p.right.sourceCount,
  older:[...p.left.history,...p.right.history].map(x=>x.date)
}))));
"""
        )
        radar = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        state = radar.get("high_order_inference") if isinstance(radar, dict) else {}
        state = state if isinstance(state, dict) else {}
        if state.get("detector_backend") == "claim_native" and int(state.get("selection_stage") or 0) >= 7:
            published = state.get("publications") if isinstance(state.get("publications"), dict) else {}
            expected_ids = [str(x) for x in (published.get("trend") or [])]
            self.assertEqual(sorted(p["id"] for p in payload), sorted(expected_ids))
        else:
            self.assertGreaterEqual(len(payload), 1)
        cutoff = json.loads((ROOT / "historical" / "historical.json").read_text(encoding="utf-8"))["cutoff_exclusive"]
        for pair in payload:
            self.assertGreaterEqual(pair["left_n"], 3, pair["id"])
            self.assertGreaterEqual(pair["right_n"], 3, pair["id"])
            self.assertGreaterEqual(pair["left_sources"], 2, pair["id"])
            self.assertGreaterEqual(pair["right_sources"], 2, pair["id"])
            for date in pair["older"]:
                self.assertLess(str(date)[:10], cutoff, pair["id"])

    def test_historical_context_cannot_create_a_current_trend(self):
        result = self.run_node(
            """
const fs=require('fs');
const T=require('./trends/trends.js');
const h=JSON.parse(fs.readFileSync('historical/historical.json','utf8'));
const empty={strand_a:[],strand_c:[],strategic_pathways:[]};
console.log(JSON.stringify({count:T.build(empty,h).length}));
"""
        )
        self.assertEqual(result["count"], 0)


if __name__ == "__main__":
    unittest.main()
