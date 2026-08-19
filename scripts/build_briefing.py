#!/usr/bin/env python3
"""Build a detailed, evidence-linked R&I × EU × geopolitics briefing.

The builder deliberately uses only material already admitted by ``radar.json``.
It does not call an LLM, fetch new sources, or alter the radar corpus.  Its job is
presentation and transparent synthesis: keep the big picture visible, while
surfacing concrete developments, implications, watchpoints and source evidence.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
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
        "summary": "Europe's R&I choices are increasingly tied to control over critical capabilities, suppliers and infrastructure. The practical policy problem is how to retain useful openness while reducing dependencies that can become geopolitical leverage.",
        "question": "Where does the EU need domestic capability, trusted partners, diversification, or explicit dependency management?",
        "implications": [
            "Map dependency at capability level, not only by country: components, cloud or compute, research infrastructure, data, skills and specialised suppliers can create different vulnerabilities.",
            "Use R&I funding together with procurement, scale-up finance and standards when the objective is an actual European capability rather than another isolated demonstration.",
            "Separate dependencies that require substitution from those better managed through diversification, stockpiles, interoperability or trusted-partner arrangements.",
        ],
        "watch": [
            "New EU or member-state lists of strategic dependencies and critical technology priorities.",
            "Funding or procurement instruments that move from pilot projects to manufacturing, infrastructure or deployment capacity.",
            "Changes in access to non-EU suppliers, platforms, data, components or research infrastructure.",
        ],
    },
    "Critical technologies, AI, chips & industrial capacity": {
        "terms": ["semiconductor", "chips", "artificial intelligence", " ai ", "quantum", "biotech", "critical technology", "critical technologies", "emerging technology", "digital infrastructure", "advanced technology", "smr", "nuclear"],
        "summary": "Critical-technology policy is converging with industrial, security and research policy. Capacity in AI, semiconductors, quantum, biotech and strategic infrastructure increasingly determines both competitiveness and geopolitical room for manoeuvre.",
        "question": "Are EU R&I instruments building scalable capability, or mainly funding isolated projects and pilots?",
        "implications": [
            "Assess the whole capability stack: scientific excellence alone does not guarantee access to compute, fabs, data, equipment, engineering talent, finance or deployment markets.",
            "Track where research programmes connect to industrial scale-up and where a hand-off gap still leaves promising technology dependent on non-EU capacity.",
            "Treat technology prioritisation as a portfolio choice: concentration can accelerate capability, but excessive narrowing can create blind spots and path dependence.",
        ],
        "watch": [
            "Scale-up milestones in European AI compute, semiconductor production, quantum, biotech and other designated critical technologies.",
            "Export-control or investment-screening changes that alter access to equipment, know-how or markets.",
            "Evidence that EU-funded research is translating into firms, infrastructure, manufacturing or public deployment inside Europe.",
        ],
    },
    "Research security, economic security & dual use": {
        "terms": ["research security", "knowledge security", "foreign interference", "economic security", "dual use", "dual-use", "export control", "security screening", "trusted research", "foreign influence", "sanction"],
        "summary": "Research openness is being rebalanced against security concerns. Universities, funders and firms face growing pressure to identify dual-use risks, sensitive collaborations and strategic technology leakage without undermining legitimate international science.",
        "question": "How can safeguards be risk-based enough to protect sensitive R&I without turning security policy into blanket disengagement?",
        "implications": [
            "Move screening upstream into proposal, partnership and data-access decisions instead of relying only on end-stage export-control checks.",
            "Differentiate risk by technology, partner, access level and intended use; broad country-level exclusions can sacrifice valuable collaboration without targeting the actual vulnerability.",
            "Give researchers usable guidance and escalation routes so compliance does not depend on each institution independently interpreting economic-security policy.",
        ],
        "watch": [
            "EU or national guidance on research security, knowledge security, foreign interference and dual-use research.",
            "New restrictions or conditions in Horizon Europe, national grants, research infrastructure access or international partnerships.",
            "Whether universities and funders adopt common risk frameworks or continue with fragmented institutional approaches.",
        ],
    },
    "EU–China / Asia cooperation and de-risking": {
        "terms": ["china", "chinese", "eu-china", "eu–china", "asia", "de-risk", "derisk", "global gateway", "indo-pacific", "japan", "south korea", "taiwan"],
        "summary": "The EU is trying to preserve useful scientific, digital and investment links with Asian partners while reducing strategic exposure to China and responding to US–China technology competition.",
        "question": "Which R&I relationships should be deepened, diversified, screened or redesigned under de-risking?",
        "implications": [
            "Distinguish collaboration fields where mutual scientific gain remains high from areas where technology transfer, data access or infrastructure dependence creates material security concerns.",
            "Diversification is not the same as disengagement: partnerships with Japan, South Korea, Taiwan and other actors can reduce concentration while keeping global science connected.",
            "Monitor indirect effects of US–China controls because European researchers and firms can be constrained by equipment, software, financing or supply chains governed elsewhere.",
        ],
        "watch": [
            "Changes in EU–China science and technology agreements, programme participation or sector-specific cooperation.",
            "New European partnerships in the Indo-Pacific that include research, critical technologies, talent or infrastructure.",
            "US or Chinese technology restrictions with spillovers into European research collaboration and industrial R&D.",
        ],
    },
    "Science diplomacy & international R&I partnerships": {
        "terms": ["science diplomacy", "research cooperation", "scientific cooperation", "research collaboration", "international research", "co-funding", "partnership", "global gateway", "international cooperation", "association agreement"],
        "summary": "R&I is becoming an instrument of external relations as well as knowledge creation. Partnerships, co-funding and research infrastructures can support influence and resilience, but geopolitical objectives can also reshape who cooperates with whom and on what terms.",
        "question": "Where can science diplomacy create durable strategic partnerships without subordinating research quality to short-term diplomacy?",
        "implications": [
            "Evaluate partnerships on both scientific value and strategic durability: funding continuity, reciprocity, data access, mobility and infrastructure access all matter.",
            "Use association and co-funding arrangements to deepen trusted networks, but avoid treating every international R&I relationship as a geopolitical loyalty test.",
            "Track whether diplomatic R&I initiatives create durable researcher-to-researcher and institution-to-institution links rather than only high-level declarations.",
        ],
        "watch": [
            "New Horizon Europe association, co-funding or science-diplomacy agreements.",
            "Partnerships tied to Global Gateway, critical raw materials, digital infrastructure, health, climate or security objectives.",
            "Evidence of reciprocity problems in access to data, infrastructure, markets, talent or intellectual property.",
        ],
    },
    "Horizon Europe, funding, talent & participation": {
        "terms": ["horizon europe", "fp10", "european research area", "erc", "research funding", "innovation funding", "talent mobility", "associated country", "third country", "third-country", "grant scheme", "framework programme", "framework program"],
        "summary": "EU research programmes are increasingly part of economic-security and geopolitical strategy. Funding rules, association, talent mobility and access to programmes can reinforce both scientific excellence and strategic alignment.",
        "question": "How should future EU R&I programmes balance excellence, openness, resilience and geopolitical conditionality?",
        "implications": [
            "Programme-access rules increasingly have strategic effects, so participation conditions should be assessed alongside scientific excellence and administrative simplicity.",
            "Talent policy is part of capability policy: attracting and retaining researchers can reduce strategic bottlenecks even where physical infrastructure already exists.",
            "FP10/Horizon design choices can either connect security objectives to mainstream R&I or create parallel instruments that fragment the funding landscape.",
        ],
        "watch": [
            "FP10 and Horizon Europe proposals affecting international participation, strategic technologies, dual use or economic security.",
            "Association decisions and restrictions affecting third countries, entities or particular technology areas.",
            "Researcher mobility, talent attraction and retention measures linked to critical technology capacity.",
        ],
    },
    "Foresight, anticipatory governance & policy preparedness": {
        "terms": ["foresight", "horizon scanning", "scenario", "anticipatory governance", "strategic intelligence", "weak signal", "future scenario", "backcasting", "delphi"],
        "summary": "Strategic foresight is moving from a peripheral analytical exercise toward a governance capability. The key challenge is connecting scenarios and weak signals to actual R&I priorities, budgets, regulation and institutional decisions.",
        "question": "Are foresight outputs changing decisions, or remaining separate from implementation and resource allocation?",
        "implications": [
            "Judge foresight methods by decision use, not novelty: a method is valuable when it changes priorities, options, timing or contingency plans.",
            "Combine weak signals with explicit thresholds or decision triggers so scanning does not become an ever-growing list of interesting observations.",
            "Stress-test R&I strategies across multiple plausible geopolitical conditions instead of building plans around one base-case future.",
        ],
        "watch": [
            "Evidence that foresight outputs are linked to budgets, portfolio choices, regulation, preparedness exercises or programme design.",
            "Methods for evaluating bias, uncertainty, participation and the quality of horizon-scanning or scenario processes.",
            "Institutional arrangements that make weak-signal review a recurring decision process rather than a one-off report.",
        ],
    },
    "Regulation, standards & geopolitical market access": {
        "terms": ["regulation", "standards", "standardisation", "standardization", "market access", "single market", "procurement", "industrial accelerator", "anti-deforestation", "rules", "regulatory"],
        "summary": "EU regulation and market rules increasingly shape global technology and innovation choices. Standards, procurement and compliance can create strategic leverage, but can also raise costs or fragment markets if poorly coordinated with R&I policy.",
        "question": "Where can EU rule-setting accelerate innovation and resilience rather than merely adding compliance burdens?",
        "implications": [
            "Align research priorities with upcoming standards and regulatory requirements so European innovators can shape markets rather than adapt after rules are fixed.",
            "Use public procurement as an early market where strategic capability matters, while preserving competition and avoiding permanent protection of weak solutions.",
            "Track cumulative compliance burdens on smaller R&I actors because strategic regulation can unintentionally favour incumbents with larger legal and reporting capacity.",
        ],
        "watch": [
            "Standards battles in AI, digital infrastructure, advanced manufacturing, energy and other strategic technology areas.",
            "Procurement rules or industrial-policy instruments that create lead markets for European technologies.",
            "Evidence that regulatory fragmentation between major markets is changing R&D location, product design or collaboration choices.",
        ],
    },
    "Resilience, energy, health & strategic infrastructure": {
        "terms": ["resilience", "preparedness", "energy", "nuclear", "health", "infrastructure", "connectivity", "critical infrastructure", "supply", "security of supply"],
        "summary": "Energy, health, connectivity and other strategic infrastructures are increasingly treated as R&I and geopolitical assets. Innovation policy is therefore being asked to deliver not only growth, but also resilience and continuity under external pressure.",
        "question": "Which R&I investments most directly reduce strategic vulnerability in essential systems?",
        "implications": [
            "Prioritise innovations that improve continuity, substitutability, repairability and surge capacity, not only peak efficiency in normal conditions.",
            "Connect research infrastructure planning to critical-infrastructure risk because laboratories, compute, energy and connectivity can share the same external dependencies.",
            "Measure resilience outcomes explicitly so strategic investment can be compared with conventional productivity or scientific-excellence objectives.",
        ],
        "watch": [
            "R&I programmes tied to energy security, health preparedness, critical infrastructure and security of supply.",
            "Stress tests or dependency assessments that identify technology gaps in essential systems.",
            "Cross-border infrastructure investments that change access to energy, compute, data, connectivity or research facilities.",
        ],
    },
}

STOP = {"the", "and", "for", "with", "from", "that", "this", "into", "under", "over", "are", "was", "were", "will", "has", "have", "its", "their", "our", "new", "european", "europe", "union", "policy", "research", "innovation", "report", "study"}


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


def evidence_note(item: dict[str, Any], limit: int = 520) -> str:
    note = clean(item.get("signal_note") or item.get("summary") or item.get("relevance_note"))
    if not note:
        return "No short source summary is available in the admitted radar record."
    if len(note) <= limit:
        return note
    cut = note[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"


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
    results: list[dict[str, Any]] = []
    for name, spec in THEMES.items():
        evidence: list[tuple[float, dict[str, Any], list[str]]] = []
        score = 0.0
        fresh_count = 0
        strands: set[str] = set()
        seen_labels: set[str] = set()
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
            evidence.sort(key=lambda z: (z[1]["_fresh"], z[0], clean(z[1].get("date"))), reverse=True)
            fresh_ab = sum(1 for _, item, _ in evidence if item["_fresh"] and item["_strand"] in {"A", "B"})
            signals = sum(1 for _, item, _ in evidence if item["_strand"] == "C")
            context = sum(1 for _, item, _ in evidence if not item["_fresh"])
            results.append({
                "name": name,
                "score": round(score, 2),
                "fresh_count": fresh_count,
                "fresh_ab": fresh_ab,
                "signals": signals,
                "context": context,
                "strands": sorted(strands),
                "summary": spec["summary"],
                "question": spec["question"],
                "implications": spec["implications"],
                "watch": spec["watch"],
                "evidence": evidence[:7],
            })
    results.sort(key=lambda x: (x["fresh_count"] > 0, x["score"], x["fresh_count"]), reverse=True)
    fresh = [x for x in results if x["fresh_count"] > 0]
    return (fresh[:6] if fresh else results[:6])


def current_read(issue: dict[str, Any]) -> str:
    parts = []
    if issue["signals"]:
        parts.append(f"{issue['signals']} current weak signal" + ("s" if issue["signals"] != 1 else ""))
    if issue["fresh_ab"]:
        parts.append(f"{issue['fresh_ab']} newly admitted A/B publication" + ("s" if issue["fresh_ab"] != 1 else ""))
    if issue["context"]:
        parts.append(f"{issue['context']} older corpus item" + ("s" if issue["context"] != 1 else "") + " used as context")
    if not parts:
        return "This theme is supported by the existing admitted corpus, but has no fresh evidence in the current scan."
    joined = ", ".join(parts[:-1]) + ((" and " + parts[-1]) if len(parts) > 1 else parts[0])
    if len(parts) == 1:
        joined = parts[0]
    return f"The current radar connects {joined}. This is an evidence concentration, not a claim that every item points in the same direction."


def public_evidence(item: dict[str, Any], hits: list[str]) -> dict[str, Any]:
    return {
        "title": label(item),
        "source": source_label(item),
        "link": item_link(item),
        "strand": item["_strand"],
        "fresh": item["_fresh"],
        "signal_type": clean(item.get("signal_type")),
        "anchor": clean(item.get("anchor")),
        "matched_terms": hits[:5],
        "note": evidence_note(item),
    }


def priority_developments(issues: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    # First pass: fresh developments from the highest-ranked themes.
    for fresh_only in (True, False):
        for issue in issues:
            for _, item, hits in issue["evidence"]:
                if fresh_only and not item["_fresh"]:
                    continue
                key = label(item).lower()
                if key in seen:
                    continue
                seen.add(key)
                e = public_evidence(item, hits)
                e["theme"] = issue["name"]
                out.append(e)
                if len(out) >= limit:
                    return out
    return out


def make_briefing(data: dict[str, Any]) -> dict[str, Any]:
    items = current_items(data)
    issues = score_themes(items)
    fresh_ab = [x for x in items if x["_strand"] in {"A", "B"} and x["_fresh"]]
    c = [x for x in items if x["_strand"] == "C"]
    total_ab = [x for x in items if x["_strand"] in {"A", "B"}]
    generated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes").replace("+00:00", "Z")

    top_names = [x["name"] for x in issues[:3]]
    if top_names:
        concentration = ", ".join(top_names[:-1]) + ((" and " + top_names[-1]) if len(top_names) > 1 else top_names[0])
        if len(top_names) == 1:
            concentration = top_names[0]
        big_picture = (
            f"The strongest evidence concentrations in the current radar are {concentration}. "
            "Read these as connected pressure points across the R&I system rather than as separate news topics: the detailed cards below show the admitted items, the policy implications and what would change the assessment."
        )
    else:
        big_picture = "The current radar contains too little matching evidence for a responsible cross-cutting synthesis. The page will deepen automatically when the admitted corpus grows."

    return {
        "generated_at": generated,
        "radar_last_updated": data.get("last_updated"),
        "scan_health": data.get("scan_health"),
        "counts": {"fresh_ab": len(fresh_ab), "current_c": len(c), "cumulative_ab": len(total_ab)},
        "big_picture": big_picture,
        "priority_developments": priority_developments(issues),
        "issues": [
            {
                "name": i["name"],
                "score": i["score"],
                "fresh_count": i["fresh_count"],
                "fresh_ab": i["fresh_ab"],
                "signals": i["signals"],
                "context": i["context"],
                "strands": i["strands"],
                "current_read": current_read(i),
                "summary": i["summary"],
                "question": i["question"],
                "implications": i["implications"],
                "watch": i["watch"],
                "evidence": [public_evidence(item, hits) for _, item, hits in i["evidence"]],
            }
            for i in issues
        ],
    }


def esc(s: Any) -> str:
    return html.escape(clean(s), quote=True)


def link_title(e: dict[str, Any]) -> str:
    title = esc(e["title"])
    href = esc(e.get("link"))
    return f'<a href="{href}" target="_blank" rel="noopener">{title}</a>' if href else title


def evidence_card(e: dict[str, Any], *, compact: bool = False) -> str:
    strand = esc(e.get("strand"))
    freshness = "fresh" if e.get("fresh") else "context"
    sig = clean(e.get("signal_type"))
    chips = [f'<span class="tag">Strand {strand}</span>', f'<span class="tag {"hot" if freshness == "fresh" else ""}">{freshness}</span>']
    if sig:
        chips.append(f'<span class="tag signal">{esc(sig)}</span>')
    anchor = clean(e.get("anchor"))
    anchor_html = f'<div class="anchor"><strong>Anchor:</strong> {esc(anchor)}</div>' if anchor else ""
    note = esc(e.get("note"))
    klass = "evidence-card compact" if compact else "evidence-card"
    return (
        f'<article class="{klass}">'
        f'<div class="chips">{"".join(chips)}</div>'
        f'<h3>{link_title(e)}</h3>'
        f'<div class="meta">{esc(e.get("source"))}</div>'
        f'<p>{note}</p>{anchor_html}'
        "</article>"
    )


def render_page(b: dict[str, Any]) -> str:
    counts = b["counts"]
    issues = b["issues"]
    developments = b.get("priority_developments", [])

    development_html = "".join(evidence_card(e, compact=True) for e in developments)
    if not development_html:
        development_html = '<div class="empty">No concrete priority development is available yet.</div>'

    issue_html: list[str] = []
    for idx, issue in enumerate(issues, start=1):
        evidence_html = "".join(evidence_card(e) for e in issue["evidence"][:4])
        more_html = "".join(evidence_card(e, compact=True) for e in issue["evidence"][4:])
        if more_html:
            more_html = f'<details><summary>Show {len(issue["evidence"]) - 4} more supporting item(s)</summary><div class="more-grid">{more_html}</div></details>'
        implications = "".join(f"<li>{esc(x)}</li>" for x in issue.get("implications", []))
        watch = "".join(f"<li>{esc(x)}</li>" for x in issue.get("watch", []))
        mix = []
        if issue.get("fresh_ab"):
            mix.append(f'{issue["fresh_ab"]} fresh A/B')
        if issue.get("signals"):
            mix.append(f'{issue["signals"]} current C')
        if issue.get("context"):
            mix.append(f'{issue["context"]} context')
        mix_text = " · ".join(mix) or "corpus-supported"
        issue_html.append(f"""
<section class="theme-card" id="theme-{idx}">
  <div class="theme-top">
    <div>
      <div class="eyebrow">Issue {idx} · {esc(mix_text)}</div>
      <h2>{esc(issue['name'])}</h2>
    </div>
    <a class="mini-link" href="#top">Back to overview ↑</a>
  </div>
  <p class="current-read">{esc(issue['current_read'])}</p>

  <div class="two-col">
    <div class="analysis-block">
      <h3>Why it matters</h3>
      <p>{esc(issue['summary'])}</p>
    </div>
    <div class="analysis-block question-block">
      <h3>Decision question</h3>
      <p>{esc(issue['question'])}</p>
    </div>
  </div>

  <div class="section-label">Specific developments in the admitted radar</div>
  <div class="evidence-grid">{evidence_html}</div>
  {more_html}

  <div class="two-col action-grid">
    <div class="analysis-block">
      <h3>Implications for R&I decisions</h3>
      <ul>{implications}</ul>
    </div>
    <div class="analysis-block">
      <h3>What to watch next</h3>
      <ul>{watch}</ul>
    </div>
  </div>
</section>""")

    if not issue_html:
        issue_html.append('<section class="theme-card"><h2>No strong cross-cutting issue detected</h2><p class="current-read">The radar does not currently contain enough matching admitted evidence for a responsible thematic synthesis. No topic has been padded in to fill the page.</p></section>')

    issue_links = "".join(
        f'<a href="#theme-{i}"><span>{i}</span>{esc(issue["name"])}</a>'
        for i, issue in enumerate(issues, start=1)
    )
    if not issue_links:
        issue_links = '<div class="empty">No ranked issue links yet.</div>'

    updated = esc(b.get("radar_last_updated") or "not available")
    generated = esc(b.get("generated_at") or "")
    health = esc(b.get("scan_health") or "unknown")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>Radar insights — EU R&I × Geopolitics</title>
<style>
:root{{--bg:#07101d;--panel:#0e1a2a;--panel2:#132338;--text:#edf4ff;--muted:#aab9cb;--line:#29405c;--accent:#86ccff;--gold:#f2cc72;--hot:#ffb38a;--max:1180px}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.58 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
a{{color:var(--accent);text-decoration:none}}a:hover{{text-decoration:underline}}.wrap{{width:min(calc(100% - 36px),var(--max));margin:auto}}
header{{padding:42px 0 30px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,#0b1930 0%,var(--bg) 100%)}}.kicker,.eyebrow,.section-label{{color:var(--gold);font-size:.76rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}}
h1{{font-size:clamp(2.35rem,6vw,4.8rem);line-height:.98;letter-spacing:-.055em;margin:.16em 0 .22em;max-width:950px}}.lede{{font-size:1.12rem;color:var(--muted);max-width:880px;margin:0}}.header-actions{{display:flex;gap:12px;flex-wrap:wrap;margin-top:22px}}.button{{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);border-radius:999px;padding:9px 13px;font-weight:700}}.button.primary{{background:var(--text);color:var(--bg);border-color:var(--text)}}
main{{padding:28px 0 78px}}.stats{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:24px}}.stat,.tag{{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:5px 9px;color:var(--muted);font-size:.76rem}}.tag{{padding:2px 7px;font-size:.67rem}}.tag.hot{{color:var(--hot);border-color:#7a5145}}.tag.signal{{color:var(--gold)}}
.overview{{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(260px,.75fr);gap:18px;margin-bottom:24px}}.big-picture,.issue-nav{{background:var(--panel);border:1px solid var(--line);border-radius:22px;padding:24px}}.big-picture h2,.issue-nav h2{{margin:.12em 0 .4em;font-size:1.35rem}}.big-picture p{{font-size:1.14rem;margin:0;color:#dce8f7}}.issue-nav{{background:var(--panel2)}}.issue-nav a{{display:grid;grid-template-columns:28px 1fr;gap:8px;padding:9px 0;border-top:1px solid var(--line);color:var(--text);font-size:.9rem}}.issue-nav a:first-of-type{{border-top:0}}.issue-nav a span{{color:var(--gold);font-weight:800}}
.priority{{margin:36px 0 44px}}.priority-head{{display:flex;justify-content:space-between;gap:20px;align-items:end;margin-bottom:14px}}.priority h2{{margin:0;font-size:1.65rem}}.priority .sub{{color:var(--muted);max-width:720px;margin:4px 0 0}}.priority-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}
.theme-card{{margin-top:26px;background:var(--panel);border:1px solid var(--line);border-radius:24px;padding:26px;box-shadow:0 16px 50px rgba(0,0,0,.12)}}.theme-top{{display:flex;justify-content:space-between;gap:18px;align-items:start}}.theme-top h2{{font-size:clamp(1.65rem,3vw,2.35rem);line-height:1.08;letter-spacing:-.035em;margin:.18em 0}}.mini-link{{font-size:.76rem;white-space:nowrap;color:var(--muted)}}.current-read{{margin:10px 0 22px;font-size:1.03rem;color:#dce8f7;border-left:3px solid var(--gold);padding-left:13px}}
.two-col{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:16px 0 24px}}.analysis-block{{background:#0a1524;border:1px solid var(--line);border-radius:16px;padding:17px}}.analysis-block h3{{font-size:.96rem;margin:0 0 7px;color:var(--gold)}}.analysis-block p{{margin:0;color:#dbe6f4}}.analysis-block ul{{margin:0;padding-left:20px}}.analysis-block li{{margin:8px 0}}.question-block p{{font-size:1.04rem;font-weight:650}}
.section-label{{margin:24px 0 10px}}.evidence-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}.evidence-card{{border:1px solid var(--line);border-radius:16px;padding:16px;background:var(--panel2)}}.evidence-card.compact{{background:#0a1524}}.chips{{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:9px}}.evidence-card h3{{font-size:1rem;line-height:1.3;margin:0 0 5px}}.evidence-card p{{font-size:.89rem;color:#c7d5e5;margin:10px 0 0}}.meta{{color:var(--muted);font-size:.76rem}}.anchor{{color:var(--muted);font-size:.78rem;margin-top:9px}}.action-grid{{margin-top:18px;margin-bottom:0}}
details{{margin-top:12px;border-top:1px solid var(--line);padding-top:11px}}summary{{cursor:pointer;color:var(--accent);font-weight:700;font-size:.88rem}}.more-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px}}.empty{{color:var(--muted);padding:12px 0}}
.method{{margin-top:30px;padding:17px 0;border-top:1px solid var(--line);color:var(--muted);font-size:.82rem}}footer{{border-top:1px solid var(--line);padding:20px 0 34px;color:var(--muted);font-size:.78rem}}
@media(max-width:820px){{.overview,.priority-grid,.two-col,.evidence-grid,.more-grid{{grid-template-columns:1fr}}.theme-top,.priority-head{{align-items:start;flex-direction:column}}.mini-link{{white-space:normal}}.theme-card{{padding:20px}}}}
</style>
</head>
<body id="top">
<header><div class="wrap">
  <div class="kicker">Radar insights · evidence-linked analytical briefing</div>
  <h1>What is changing, why it matters, and what to watch</h1>
  <p class="lede">A detailed but readable synthesis of the papers, reports and current weak signals already admitted by the radar. The page keeps the system-level picture visible while letting you inspect concrete developments and their R&I implications.</p>
  <div class="header-actions"><a class="button primary" href="../">← Main radar</a><a class="button" href="#priority">Jump to specific developments ↓</a></div>
</div></header>

<main class="wrap">
  <div class="stats">
    <span class="stat">{counts['fresh_ab']} fresh A/B</span>
    <span class="stat">{counts['current_c']} current C signals</span>
    <span class="stat">{counts['cumulative_ab']} cumulative A/B</span>
    <span class="stat">scan health: {health}</span>
  </div>

  <section class="overview">
    <div class="big-picture"><div class="eyebrow">Big picture</div><h2>Where the radar is concentrating now</h2><p>{esc(b.get('big_picture'))}</p></div>
    <nav class="issue-nav" aria-label="Ranked radar issues"><div class="eyebrow">Issue map</div><h2>Explore the detail</h2>{issue_links}</nav>
  </section>

  <section class="priority" id="priority">
    <div class="priority-head"><div><div class="eyebrow">Concrete evidence first</div><h2>Priority developments in the current radar</h2><p class="sub">These are admitted source items, not generated news claims. Fresh material is shown first; older corpus items appear only when needed for context.</p></div></div>
    <div class="priority-grid">{development_html}</div>
  </section>

  {''.join(issue_html)}

  <div class="method"><strong>How to read this page:</strong> theme ranking is a transparent term-and-evidence concentration over admitted radar material. It helps organise the corpus; it does not replace source reading and it does not infer facts that are absent from the admitted records. Strand C remains anchored to A/B literature by the scanner.</div>
</main>
<footer><div class="wrap">Radar updated: {updated} · Insights generated: {generated}. The insights builder only reads <code>radar.json</code> and does not modify the scanner corpus.</div></footer>
</body></html>"""


def main() -> int:
    if not RADAR.exists():
        raise SystemExit("radar.json not found")
    data = json.loads(RADAR.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    briefing = make_briefing(data)
    OUT_JSON.write_text(json.dumps(briefing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_HTML.write_text(render_page(briefing), encoding="utf-8")
    print(f"Built {OUT_HTML.relative_to(ROOT)} with {len(briefing['issues'])} issue(s) and {len(briefing['priority_developments'])} priority development(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
