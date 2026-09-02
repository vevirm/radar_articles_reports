from pathlib import Path
import json
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]

class V17200ReaderContractTests(unittest.TestCase):
    def test_read_at_least_this_builds_eight_topic_trees_from_live_corpus(self):
        code=r"""
global.RadarInsights={fastReaderText:x=>x};
require('./read/issues.js');
const D=require('./radar.json');
const trees=global.RadarIssues.buildTrees([...(D.strand_a||[]),...(D.strand_c||[])],{count:8});
if(trees.length!==8){console.error('trees',trees.length);process.exit(2)}
for(const t of trees){if(!t.main||t.subs.length!==2||t.leaves.length!==3)process.exit(3)}
"""
        subprocess.run(['node','-e',code],cwd=ROOT,check=True,timeout=20)

    def test_external_shock_reasoner_finds_aha_scenarios_and_realised_shock(self):
        code=r"""
const S=require('./shocks/scenarios.js');
const P=require('./priorities/priorities.js');
const D=require('./radar.json');
const direct=S.buildDirect(D);
if(direct.length<3){console.error('direct scenarios',direct.length);process.exit(2)}
const s=S.build(D);
if(s.length<4){console.error('scenarios',s.length);process.exit(2)}
if(!direct.some(x=>x.id==='direct_materials_cutoff'&&x.evidence.length>=4))process.exit(3);
if(!s.some(x=>x.id==='measurement_mid_river'&&x.evidence.length>=6))process.exit(4);
const v=P.buildPriorityView(D,{limit:50});
if(v.externalShocks.length<1)process.exit(5);
"""
        subprocess.run(['node','-e',code],cwd=ROOT,check=True,timeout=20)

    def test_main_scanner_has_24_minute_runtime_budget_and_safe_workflow_envelope(self):
        # The scanner's real runtime budget lives in radar_config.json.  Keep this
        # contract independent of cosmetic/workflow timeout wording so a GitHub
        # web "upload over the top" that leaves an older .github workflow in place
        # cannot block the scanner before it starts.
        cfg=json.loads((ROOT/'radar_config.json').read_text(encoding='utf-8'))
        self.assertEqual(cfg.get('scan_budget_seconds'),1440)
        wf=(ROOT/'.github/workflows/radar-scan.yml').read_text(encoding='utf-8')
        self.assertTrue(
            'timeout-minutes: 36' in wf or 'timeout-minutes: 30' in wf,
            'scan job must leave enough envelope for a 24-minute scanner run',
        )
        if '  publish:' in wf:
            publish=wf.split('  publish:',1)[1]
            self.assertTrue(
                'timeout-minutes: 6' in publish or 'timeout-minutes: 5' in publish,
                'publish job must retain a bounded GitHub Pages trigger window',
            )

if __name__=='__main__':
    unittest.main()
