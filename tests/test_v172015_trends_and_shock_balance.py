from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_trends_page_is_in_release_and_core_path():
    build = (ROOT / "scripts/build_release.py").read_text(encoding="utf-8")
    assert '"trends/index.html"' in build
    assert '"trends/trends.js"' in build
    for rel in ("index.html", "frontier/quick/index.html", "priorities/index.html", "shocks/index.html"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "Trends" in text
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "1</span><strong>Radar" in home
    assert "3</span><strong>Trends" in home
    assert "5</span><strong>External shocks" in home


def test_trend_pairs_are_two_sided_quality_anchored_and_sum_to_100():
    js = r"""
const fs=require('fs');
const T=require('./trends/trends.js');
const d=JSON.parse(fs.readFileSync('./radar.json','utf8'));
const xs=T.build(d);
if(xs.length<2) throw new Error('expected supported trend pairs');
for(const p of xs){
  if(p.left.odds+p.right.odds!==100) throw new Error('odds do not sum to 100');
  if(p.left.evidence.filter(e=>e.quality>=85).length<2) throw new Error('left lacks high-quality anchors');
  if(p.right.evidence.filter(e=>e.quality>=85).length<2) throw new Error('right lacks high-quality anchors');
  if(p.left.bestQuality<95||p.right.bestQuality<95) throw new Error('side lacks top-quality anchor');
  if(!p.left.evidence.every(e=>['actor','observer'].includes(e.reporting))) throw new Error('missing reporting role');
}
if(!xs.some(p=>[...p.left.evidence,...p.right.evidence].some(e=>e.hostile))) throw new Error('hostile-witness rule not exercised');
console.log(JSON.stringify(xs.map(p=>({id:p.id,l:p.left.odds,r:p.right.odds}))));
"""
    cp = subprocess.run(["node", "-e", js], cwd=ROOT, text=True, capture_output=True, check=True)
    rows = json.loads(cp.stdout.strip())
    assert rows


def test_shock_pages_show_for_and_against_arrows():
    index = (ROOT / "shocks/index.html").read_text(encoding="utf-8")
    variants = (ROOT / "shocks/variants.html").read_text(encoding="utf-8")
    assert "↑ What points toward it" in index
    assert "↓ What pushes against it" in index
    assert "↑ What points toward this shock family" in index
    assert "↓ What could contain or absorb it" in index
    assert "RadarShockVariants?.build" in index
    assert "↑ Speaks for the shock" in variants
    assert "↓ Pushes against it" in variants


def test_shock_counterevidence_is_quality_scored_and_sorted():
    text = (ROOT / "shocks/variants.js").read_text(encoding="utf-8")
    assert "quality:qualityScore(row)" in text
    assert "out.sort((a,b)=>b.quality-a.quality)" in text
