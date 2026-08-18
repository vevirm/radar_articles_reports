#!/usr/bin/env python3
"""Build an executive R&I × EU × Geopolitics briefing from radar.json.

No external AI/API is required. The script performs a transparent, evidence-linked
synthesis: it scores cross-cutting themes using fresh A/B publications and current
Strand C signals, then writes briefing/briefing.json and briefing/index.html.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RADAR = ROOT / "radar.json"
OUT_DIR = ROOT / "briefing"
OUT_JSON = OUT_DIR / "briefing.json"
OUT_HTML = OUT_DIR / "index.html"

THEMES: dict[str, dict[str, Any]] = {
    "Technology sovereignty & strategic dependencies": {
        "terms": ["technological sovereignty", "technology sovereignty", "strategic autonomy", "open strategic autonomy", "strategic dependency", "strategic dependencies", "non-eu technology", "supply chain", "vendor", "industrial competitiveness"],
        "summary": "Europe's R&I choices are increasingly tied to control over critical capabilities, suppliers and infrastructure. The policy problem is how to retain openness while reducing dependencies that can become geopolitical leverage.",
        "question": "Where does the EU need domestic capability, trusted partners, diversification, or explicit dependency management?",
    },
    "Critical technologies, AI, chips & industrial capacity": {
        "terms": ["semiconductor", "chips", "artificial intelligence", " ai ", "quantum", "biotech", "critical technology", "critical technologies", "emerging technology", "digital infrastructure", "advanced technology", "smr", "nuclear"],
        "summary": "Critical-technology policy is converging with industrial, security and research policy. Capacity in AI, semiconductors, quantum, biotech and strategic infrastructure increasingly determines both competitiveness and geopolitical room for manoeuvre.",
        "question": "Are EU R&I instruments building scalable capability, or mainly funding isolated projects and pilots?",
    },
    "Research security, economic security & dual use": {
        "terms": ["research security", "knowledge security", "foreign interference", "economic security", "dual use", "dual-use", "export control", "security screening", "trusted research", "foreign influence", "sanction"],
        "summary": "Research openness is being rebalanced against security concerns. Universities, funders and firms face growing pressure to identify dual-use risks, sensitive collaborations and strategic technology leakage without undermining legitimate international science.",
        "question": "How can safeguards be made risk-based enough to protect sensitive R&I without turning security policy into blanket disengagement?",
    },
    "EU–China / Asia cooperation and de-risking": {
        "terms": ["china", "chinese", "eu-china", "eu–china", "asia", "de-risk", "derisk", "global gateway", "indo-pacific", "japan", "south korea", "taiwan"],
        "summary": "The EU is trying to preserve useful scientific, digital and investment links with Asian partners while reducing strategic exposure to China and responding to US–China technology competition.",
        "question": "Which R&I relationships should be deepened, diversified, screened or redesigned under de-risking?",
    },
    "Science diplomacy & international R&I partnerships": {
        "terms": ["science diplomacy", "research cooperation", "scientific cooperation", "research collaboration", "international research", "co-funding", "partnership", "global gateway", "international cooperation", "association agreement"],
        "summary": "R&I is becoming an instrument of external relations as well as knowledge creation. Partnerships, co-funding and research infrastructures can support influence and resilience, but geopolitical objectives can also reshape who cooperates with whom and on what terms.",
        "question": "Where can science diplomacy create durable strategic partnerships without subordinating research quality to short-term diplomacy?",
    },
    "Horizon Europe, funding, talent & participation": {
        "terms": ["horizon europe", "fp10", "european research area", "erc", "research funding", "innovation funding", "talent mobility", "associated country", "third country", "third-country", "grant scheme", "framework programme", "framework program"],
        "summary": "EU research programmes are increasingly part of economic-security and geopolitical strategy. Funding rules, association, talent mobility and access to programmes can reinforce both scientific excellence and strategic alignment.",
        "question": "How should future EU R&I programmes balance excellence, openness, resilience and geopolitical conditionality?",
    },
    "Foresight, anticipatory governance & policy preparedness": {
        "terms": ["foresight", "horizon scanning", "scenario", "anticipatory governance", "strategic intelligence", "weak signal", "future scenario", "backcasting", "delphi"],
        "summary": "Strategic foresight is moving from a peripheral analytical exercise toward a governance capability. The key challenge is connecting scenarios and weak signals to actual R&I priorities, budgets, regulation and institutional decisions.",
        "question": "Are foresight outputs changing decisions, or remaining separate from implementation and resource allocation?",
    },
    "Regulation, standards & geopolitical market access": {
        "terms": ["regulation", "standards", "standardisation", "standardization", "market access", "single market", "procurement", "industrial accelerator", "anti-deforestation", "rules", "regulatory"],
        "summary": "EU regulation and market rules increasingly shape global technology and innovation choices. Standards, procurement and compliance can create strategic leverage, but can also raise costs or fragment markets if they are poorly coordinated with R&I policy.",
        "question": "Where can EU rule-setting accelerate innovation and resilience rather than merely adding compliance burdens?",
    },
    "Resilience, energy, health & strategic infrastructure": {
        "terms": ["resilience", "preparedness", "energy", "nuclear", "health", "infrastructure", "connectivity", "critical infrastructure", "supply", "security of supply"],
        "summary": "Energy, health, connectivity and other strategic infrastructures are increasingly treated as R&I and geopolitical assets. Innovation policy is therefore being asked to deliver not only growth, but also resilience and continuity under external pressure.",
        "question": "Which R&I investments most directly reduce strategic vulnerability in essential systems?",
    },
}


ISSUE_BULLETS = {
    "Technology sovereignty & strategic dependencies":
        "EU R&I is increasingly being used to reduce strategic technology and supply-chain dependencies while preserving international openness.",
    "Critical technologies, AI, chips & industrial capacity":
        "AI, chips, quantum, biotech and strategic infrastructure are becoming central to EU competitiveness and geopolitical autonomy.",
    "Research security, economic security & dual use":
        "European research cooperation is facing tighter security, dual-use and knowledge-protection requirements.",
    "EU–China / Asia cooperation and de-risking":
        "EU research and technology cooperation with Asia is increasingly shaped by de-risking, diversification and competition with China.",
    "Science diplomacy & international R&I partnerships":
        "International R&I partnerships are increasingly being used as instruments of EU diplomacy, resilience and strategic influence.",
    "Horizon Europe, funding, talent & participation":
        "EU research funding, programme access and talent policy are becoming more closely linked to strategic and geopolitical priorities.",
    "Foresight, anticipatory governance & policy preparedness":
        "Strategic foresight is becoming more important for turning geopolitical change into concrete R&I priorities and preparedness.",
    "Regulation, standards & geopolitical market access":
        "EU regulation, standards and procurement are increasingly shaping global technology choices and the conditions for innovation.",
    "Resilience, energy, health & strategic infrastructure":
        "R&I policy is increasingly expected to strengthen European resilience in energy, health, connectivity and other strategic systems.",
}

STOP = {"the","and","for","with","from","that","this","into","under","over","are","was","were","will","has","have","its","their","our","new","european","europe","union","policy","research","innovation","report","study"}


def clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def low(v: Any) -> str:
    return " " + clean(v).lower().replace("–", "-").replace("—", "-") + " "


def item_text(item: dict[str, Any]) -> str:
    return " ".join(clean(item.get(k)) for k in ("title", "headline", "summary", "relevance_note", "signal_note", "anchor", "source"))


def label(item: dict[str, Any]) -> str:
    return clean(item.get("title") or item.get("headline") or "Untitled item")


def item_link(item: dict[str, Any]) -> str:
    return clean(item.get("link"))


def source_label(item: dict[str, Any]) -> str:
    s = clean(item.get("source"))
    d = clean(item.get("date"))[:10]
    return " · ".join(x for x in (s, d) if x)


def theme_hits(text: str, terms: list[str]) -> list[str]:
    t = low(text)
    return [term for term in terms if term in t]


def current_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for strand in ("strand_a", "strand_b"):
        for raw in data.get(strand, []) if isinstance(data.get(strand), list) else []:
            x = dict(raw)
            x["_strand"] = "A" if strand.endswith("a") else "B"
            x["_fresh"] = bool(x.get("new_this_scan"))
            # Fresh A/B drives the briefing; older corpus remains contextual evidence.
            x["_weight"] = 4.0 if x["_fresh"] else 1.0
            items.append(x)
    for raw in data.get("strand_c", []) if isinstance(data.get("strand_c"), list) else []:
        x = dict(raw)
        x["_strand"] = "C"
        x["_fresh"] = True
        x["_weight"] = 3.0
        items.append(x)
    return items


def score_themes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for name, spec in THEMES.items():
        evidence = []
        score = 0.0
        fresh_count = 0
        strands = set()
        seen_labels = set()
        for item in items:
            hits = theme_hits(item_text(item), spec["terms"])
            if not hits:
                continue
            strength = min(3, len(set(hits)))
            contribution = item["_weight"] * (1.0 + 0.28 * (strength - 1))
            score += contribution
            if item["_fresh"]:
                fresh_count += 1
            strands.add(item["_strand"])
            key = label(item).lower()
            if key not in seen_labels:
                seen_labels.add(key)
                evidence.append((contribution, item, hits))
        if evidence:
            evidence.sort(key=lambda z: (z[0], clean(z[1].get("date"))), reverse=True)
            results.append({
                "name": name,
                "score": round(score, 2),
                "fresh_count": fresh_count,
                "strands": sorted(strands),
                "summary": spec["summary"],
                "question": spec["question"],
                "evidence": evidence[:5],
            })
    results.sort(key=lambda x: (x["score"], x["fresh_count"]), reverse=True)
    # Avoid a weak old-corpus-only theme crowding out genuinely fresh topics.
    fresh = [x for x in results if x["fresh_count"] > 0]
    chosen = fresh[:6] if fresh else results[:6]
    return chosen


def issue_sentence(issue: dict[str, Any]) -> str:
    return ISSUE_BULLETS.get(
        issue["name"],
        issue["summary"].split(". ")[0].rstrip(".") + "."
    )


def make_briefing(data: dict[str, Any]) -> dict[str, Any]:
    items = current_items(data)
    issues = score_themes(items)
    fresh_ab = [x for x in items if x["_strand"] in {"A","B"} and x["_fresh"]]
    c = [x for x in items if x["_strand"] == "C"]
    total_ab = [x for x in items if x["_strand"] in {"A","B"}]
    generated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes").replace("+00:00", "Z")
    executive = []
    for issue in issues[:3]:
        executive.append({"title": issue["name"], "text": issue_sentence(issue)})
    if not executive:
        executive.append({"title": "No strong cross-cutting issue detected", "text": "The current radar contains too little matching evidence for a responsible thematic synthesis. The briefing will update after the next successful radar scan."})
    return {
        "generated_at": generated,
        "radar_last_updated": data.get("last_updated"),
        "scan_health": data.get("scan_health"),
        "counts": {"fresh_ab": len(fresh_ab), "current_c": len(c), "cumulative_ab": len(total_ab)},
        "executive_synthesis": executive,
        "issues": [
            {
                "name": i["name"], "score": i["score"], "fresh_count": i["fresh_count"], "strands": i["strands"],
                "bullet": issue_sentence(i), "summary": i["summary"], "question": i["question"],
                "evidence": [
                    {"title": label(item), "source": source_label(item), "link": item_link(item), "strand": item["_strand"], "fresh": item["_fresh"], "matched_terms": hits[:4], "note": clean(item.get("signal_note") or item.get("summary"))[:420]}
                    for _, item, hits in i["evidence"]
                ],
            }
            for i in issues
        ],
    }


def esc(s: Any) -> str:
    return html.escape(clean(s), quote=True)


def render_page(b: dict[str, Any]) -> str:
    counts = b["counts"]
    issues = b["issues"]

    bullets_html = []
    details_html = []

    for issue in issues:
        bullets_html.append(
            "<li><strong>" + esc(issue["name"]) + "</strong> — " +
            esc(issue.get("bullet") or issue["summary"]) + "</li>"
        )

        evidence_html = []
        for e in issue["evidence"]:
            title = esc(e["title"])
            href = esc(e["link"])
            title_html = (
                '<a href="' + href + '" target="_blank" rel="noopener">' + title + "</a>"
                if href else title
            )
            freshness = "fresh" if e["fresh"] else "context"
            evidence_html.append(
                '<li><span class="tag">Strand ' + esc(e["strand"]) + "</span> " +
                '<span class="tag">' + freshness + "</span> " + title_html +
                '<div class="meta">' + esc(e["source"]) + "</div></li>"
            )

        details_html.append(
            "<details><summary>" + esc(issue["name"]) + " — evidence (" +
            str(len(issue["evidence"])) + ")</summary>" +
            '<ul class="evidence">' + "".join(evidence_html) + "</ul></details>"
        )

    if not bullets_html:
        bullets_html.append(
            "<li>No sufficiently supported R&I × EU × geopolitics issue was identified in the current radar material.</li>"
        )

    updated = esc(b.get("radar_last_updated") or "not available")
    generated = esc(b.get("generated_at") or "")
    health = esc(b.get("scan_health") or "unknown")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>R&I × EU × Geopolitics — Issues</title>
<style>
:root{{--bg:#08111f;--panel:#101d2f;--text:#edf4ff;--muted:#a9bad0;--line:#28415f;--accent:#7fc7ff;--gold:#f2cc72}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
a{{color:var(--accent);text-decoration:none}} a:hover{{text-decoration:underline}}
.wrap{{max-width:960px;margin:auto;padding:36px 22px 70px}}
header{{border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:26px}}
.kicker{{color:var(--gold);font-size:.78rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase}}
h1{{font-size:clamp(2rem,5vw,3.4rem);line-height:1.05;margin:.15em 0}}
.lede{{color:var(--muted);max-width:760px}}
.back{{display:inline-block;margin-top:8px}}
.stats{{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0 28px}}
.stat{{border:1px solid var(--line);border-radius:999px;padding:7px 11px;color:var(--muted);font-size:.82rem}}
.issuebox{{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:22px}}
.issuebox h2{{margin-top:0}}
.issues{{margin:0;padding-left:24px}}
.issues li{{margin:14px 0;font-size:1.08rem}}
details{{border-top:1px solid var(--line);padding:13px 0}}
details:first-child{{margin-top:22px}}
summary{{cursor:pointer;color:var(--accent);font-weight:650}}
.evidence{{padding-left:22px}}
.evidence li{{margin:10px 0}}
.meta{{color:var(--muted);font-size:.8rem;margin-top:2px}}
.tag{{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 6px;font-size:.68rem;color:var(--muted)}}
footer{{margin-top:30px;color:var(--muted);font-size:.82rem}}
</style>
</head>
<body><div class="wrap">
<header>
<div class="kicker">Automated issue scan</div>
<h1>R&I × EU × Geopolitics</h1>
<p class="lede">Simple issues isolated from the material already admitted by the radar. The first run uses the existing corpus; later runs follow successful radar scans.</p>
<a class="back" href="../">← Main radar</a>
</header>

<div class="stats">
  <span class="stat">{counts['fresh_ab']} fresh A/B</span>
  <span class="stat">{counts['current_c']} current C signals</span>
  <span class="stat">{counts['cumulative_ab']} cumulative A/B</span>
  <span class="stat">scan health: {health}</span>
</div>

<section class="issuebox">
<h2>Issues identified</h2>
<ul class="issues">{''.join(bullets_html)}</ul>
</section>

<section>
<h2>Evidence</h2>
<p class="lede">Optional source trace; the issue list above is the main output.</p>
{''.join(details_html)}
</section>

<footer>Radar updated: {updated} · Issue scan generated: {generated}. The issue scan only reads radar material and does not modify the radar corpus.</footer>
</div></body></html>"""



def main() -> int:
    if not RADAR.exists():
        raise SystemExit("radar.json not found")
    data = json.loads(RADAR.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    briefing = make_briefing(data)
    OUT_JSON.write_text(json.dumps(briefing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_HTML.write_text(render_page(briefing), encoding="utf-8")
    print(f"Built {OUT_HTML.relative_to(ROOT)} with {len(briefing['issues'])} issue(s).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
