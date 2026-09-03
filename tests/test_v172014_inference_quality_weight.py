import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InferenceQualityWeightTests(unittest.TestCase):
    def test_supported_shocks_are_inferred_and_ranked_by_evidence_strength(self):
        js = r"""
const fs=require('fs');
const S=require('./shocks/scenarios.js');
const D=JSON.parse(fs.readFileSync('radar.json','utf8'));
const xs=S.build(D);
if(xs.length<4) process.exit(2);
for(let i=1;i<xs.length;i++) if(xs[i-1].inferenceScore<xs[i].inferenceScore) process.exit(3);
if(!xs.every(x=>Number.isFinite(x.inferenceScore)&&x.inferenceScore>=0&&x.inferenceScore<=100)) process.exit(4);
if(!xs.some(x=>x.id==='measurement_mid_river')) process.exit(5);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_quality_is_a_weight_not_a_hard_inference_kill_switch(self):
        shocks = (ROOT / "shocks" / "scenarios.js").read_text(encoding="utf-8")
        priorities = (ROOT / "priorities" / "priorities.js").read_text(encoding="utf-8")
        self.assertIn("Inference is recall-first", shocks)
        self.assertIn("inferenceScore", shocks)
        self.assertNotIn("best<82||avg<68", shocks)
        self.assertIn("Publication quality is the dominant ordering", priorities)
        self.assertNotIn("quality<68", priorities)

    def test_current_corpus_still_has_direct_and_reasoned_inference(self):
        js = r"""
const fs=require('fs');
const S=require('./shocks/scenarios.js');
const D=JSON.parse(fs.readFileSync('radar.json','utf8'));
if(S.buildDirect(D).length<3) process.exit(2);
if(S.build(D).length<4) process.exit(3);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)


if __name__ == '__main__':
    unittest.main()
