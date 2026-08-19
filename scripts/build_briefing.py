#!/usr/bin/env python3
"""Build the Radar insights topic digest from the existing radar corpus.

The insights page is deliberately a re-organisation layer, not a second analysis
engine. It reads only material already admitted to ``radar.json`` and groups each
item under one primary subject heading (Raw materials, Research, AI, etc.). The
source wording, links, dates, strands and anchors remain visible so every bullet
can be traced directly back to the main radar.
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

# Ordered for scanning/readability rather than by dynamic score.  Weights keep
# generic geopolitical words from overpowering a more concrete subject signal.
TOPICS: list[dict[str, Any]] = [
    {
        "key": "raw-materials",
        "name": "Raw materials & supply chains",
        "terms": {
            "critical raw material": 8, "critical raw materials": 8, "raw material": 7,
            "rare earth": 8, "rare earths": 8, "mineral": 5, "minerals": 5,
            "lithium": 7, "cobalt": 7, "nickel": 6, "graphite": 7, "copper": 5,
            "gallium": 8, "germanium": 8, "tungsten": 7, "magnesium": 6,
            "battery material": 7, "mining": 6, "refining": 5,
        },
    },
    {
        "key": "research",
        "name": "Research & science",
        "terms": {
            "horizon europe": 8, "framework programme": 7, "framework program": 7,
            "erc": 7, "european research area": 7, "research funding": 6,
            "research infrastructure": 6, "research security": 7, "knowledge security": 7,
            "science diplomacy": 7, "scientific cooperation": 6, "research cooperation": 6,
            "research collaboration": 6, "academic": 4, "academia": 5, "university": 5,
            "universities": 5, "scientific": 3, "researcher": 4, "researchers": 4,
        },
    },
    {
        "key": "ai",
        "name": "AI & compute",
        "terms": {
            "artificial intelligence": 9, " ai ": 8, "machine learning": 7,
            "foundation model": 8, "foundation models": 8, "large language model": 8,
            "llm": 8, "gpu": 7, "gpus": 7, "compute capacity": 7, "computing capacity": 7,
            "supercomputer": 6, "supercomputing": 6, "ai factory": 9, "ai factories": 9,
            "data centre": 4, "data center": 4,
        },
    },
    {
        "key": "chips-quantum",
        "name": "Chips, quantum & critical tech",
        "terms": {
            "semiconductor": 9, "semiconductors": 9, "microelectronics": 8,
            "chip": 7, "chips": 7, "quantum": 9, "photonics": 8,
            "critical technology": 6, "critical technologies": 6,
            "advanced technology": 4, "advanced technologies": 4,
        },
    },
    {
        "key": "energy",
        "name": "Energy & climate tech",
        "terms": {
            "energy security": 8, "energy": 4, "nuclear": 7, "smr": 8,
            "small modular reactor": 8, "hydrogen": 7, "renewable": 5, "renewables": 5,
            "electricity grid": 7, "power grid": 7, "grid": 4, "battery": 5,
            "clean tech": 6, "cleantech": 6, "climate technology": 6, "climate tech": 6,
            "carbon capture": 6, "fusion": 7,
        },
    },
    {
        "key": "security-defence",
        "name": "Security, defence & dual use",
        "terms": {
            "defence": 8, "defense": 8, "dual-use": 8, "dual use": 8,
            "military": 8, "nato": 7, "security screening": 6, "export control": 6,
            "export controls": 6, "foreign interference": 7, "knowledge leakage": 7,
            "cybersecurity": 6, "cyber security": 6, "economic coercion": 5,
        },
    },
    {
        "key": "trade-industry",
        "name": "Trade, industry & economic security",
        "terms": {
            "economic security": 7, "industrial policy": 7, "industrial competitiveness": 7,
            "competitiveness": 5, "manufacturing": 5, "supply chain": 4,
            "supply chains": 4, "trade": 4, "tariff": 6, "tariffs": 6,
            "investment screening": 7, "foreign direct investment": 6, "fdi": 5,
            "sanction": 5, "sanctions": 5, "strategic autonomy": 6,
            "strategic dependency": 6, "strategic dependencies": 6,
            "de-risking": 6, "derisking": 6, "de-risk": 6,
        },
    },
    {
        "key": "digital-cyber",
        "name": "Digital infrastructure & cyber",
        "terms": {
            "digital infrastructure": 8, "cloud": 5, "cloud infrastructure": 7,
            "telecom": 6, "telecommunications": 6, "5g": 6, "6g": 7,
            "submarine cable": 7, "subsea cable": 7, "data governance": 6,
            "data space": 6, "digital sovereignty": 7, "platform": 3,
            "cyber": 5, "network security": 6,
        },
    },
    {
        "key": "space",
        "name": "Space",
        "terms": {
            "space": 7, "satellite": 8, "satellites": 8, "launch vehicle": 8,
            "launcher": 7, "esa": 7, "copernicus": 8, "galileo": 8,
            "earth observation": 7, "orbital": 7,
        },
    },
    {
        "key": "health-biotech",
        "name": "Health & biotech",
        "terms": {
            "biotech": 8, "biotechnology": 8, "biological": 4, "life science": 6,
            "life sciences": 6, "health security": 7, "health": 4, "pharma": 6,
            "pharmaceutical": 6, "pharmaceuticals": 6, "vaccine": 7, "vaccines": 7,
            "biomedical": 7, "genomic": 7, "genomics": 7, "bioeconomy": 6,
        },
    },
    {
        "key": "talent",
        "name": "Talent, skills & mobility",
        "terms": {
            "talent": 7, "skills": 6, "researcher mobility": 8, "scientist mobility": 8,
            "brain drain": 8, "brain gain": 8, "visa": 6, "visas": 6,
            "education": 4, "doctoral": 5, "phd": 5, "migration": 4,
            "workforce": 5, "training": 4,
        },
    },
    {
        "key": "international",
        "name": "International partnerships & geopolitics",
        "terms": {
            "global gateway": 8, "indo-pacific": 7, "international cooperation": 6,
            "international partnership": 7, "international partnerships": 7,
            "association agreement": 7, "associated country": 6,
            "china": 3, "chinese": 3, "united states": 3, " u.s. ": 3, " us ": 2,
            "japan": 3, "south korea": 3, "korea": 2, "india": 3, "taiwan": 3,
            "ukraine": 3, "russia": 3, "africa": 3, "latin america": 3,
        },
    },
    {
        "key": "foresight",
        "name": "Foresight & methods",
        "terms": {
            "foresight": 9, "horizon scanning": 9, "scenario planning": 8,
            "scenario": 6, "scenarios": 6, "weak signal": 8, "weak signals": 8,
            "delphi": 8, "backcasting": 8, "anticipatory governance": 8,
            "strategic intelligence": 6, "futures literacy": 8,
        },
    },
]

OTHER_TOPIC = {"key": "other", "name": "Other strategic R&I"}


def clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def normalise(v: Any) -> str:
    s = clean(v).lower().replace("–", "-").replace("—", "-")
    return " " + re.sub(r"[^a-z0-9+.#/-]+", " ", s) + " "


def item_text(item: dict[str, Any]) -> str:
    return " ".join(clean(item.get(k)) for k in (
        "title", "headline", "summary", "relevance_note", "signal_note", "anchor", "source", "type"
    ))


def label(item: dict[str, Any]) -> str:
    return clean(item.get("title") or item.get("headline") or "Untitled item")


def source_label(item: dict[str, Any]) -> str:
    return clean(item.get("source"))


def note_for(item: dict[str, Any], limit: int = 620) -> str:
    # Keep this as source/radar wording. No generated interpretation is inserted.
    note = clean(item.get("signal_note") or item.get("summary") or item.get("relevance_note"))
    if not note:
        return "No short summary is available in the radar record."
    if len(note) <= limit:
        return note
    cut = note[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"


def relevance_for(item: dict[str, Any], limit: int = 360) -> str:
    rel = clean(item.get("relevance_note"))
    if not rel or rel == clean(item.get("summary")):
        return ""
    if len(rel) <= limit:
        return rel
    return rel[:limit].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def current_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for strand in ("strand_a", "strand_b"):
        vals = data.get(strand) if isinstance(data.get(strand), list) else []
        for raw in vals:
            x = dict(raw)
            x["_strand"] = "A" if strand.endswith("a") else "B"
            x["_fresh"] = bool(x.get("new_this_scan"))
            items.append(x)
    vals = data.get("strand_c") if isinstance(data.get("strand_c"), list) else []
    for raw in vals:
        x = dict(raw)
        x["_strand"] = "C"
        x["_fresh"] = True
        items.append(x)
    return items


def topic_scores(item: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    text = normalise(item_text(item))
    scores: list[tuple[int, dict[str, Any]]] = []
    for topic in TOPICS:
        score = 0
        for term, weight in topic["terms"].items():
            needle = normalise(term)
            if needle.strip() and needle in text:
                score += int(weight)
        if score:
            scores.append((score, topic))
    scores.sort(key=lambda x: x[0], reverse=True)
    return scores


def public_item(item: dict[str, Any], related_topics: list[str]) -> dict[str, Any]:
    return {
        "title": label(item),
        "source": source_label(item),
        "date": clean(item.get("date"))[:10],
        "link": clean(item.get("link")),
        "strand": item.get("_strand", ""),
        "fresh": bool(item.get("_fresh")),
        "type": clean(item.get("type")),
        "signal_type": clean(item.get("signal_type")),
        "note": note_for(item),
        "relevance": relevance_for(item),
        "anchor": clean(item.get("anchor")),
        "related_topics": related_topics,
    }


def make_briefing(data: dict[str, Any]) -> dict[str, Any]:
    items = current_items(data)
    buckets: dict[str, list[dict[str, Any]]] = {t["key"]: [] for t in TOPICS}
    buckets[OTHER_TOPIC["key"]] = []

    for item in items:
        scores = topic_scores(item)
        if scores:
            primary = scores[0][1]
            # Show secondary subject labels only when they are meaningful. The item
            # itself is still listed once, preventing repetitive topic sections.
            threshold = max(4, scores[0][0] // 2)
            related = [t["name"] for score, t in scores[1:4] if score >= threshold]
        else:
            primary = OTHER_TOPIC
            related = []
        buckets[primary["key"]].append(public_item(item, related))

    def sort_key(x: dict[str, Any]) -> tuple[int, str, str]:
        return (1 if x.get("fresh") else 0, clean(x.get("date")), clean(x.get("title")).lower())

    topics: list[dict[str, Any]] = []
    for topic in [*TOPICS, OTHER_TOPIC]:
        vals = sorted(buckets[topic["key"]], key=sort_key, reverse=True)
        if vals:
            topics.append({"key": topic["key"], "name": topic["name"], "items": vals, "count": len(vals)})

    generated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes").replace("+00:00", "Z")
    fresh_ab = sum(1 for x in items if x.get("_strand") in {"A", "B"} and x.get("_fresh"))
    current_c = sum(1 for x in items if x.get("_strand") == "C")
    cumulative_ab = sum(1 for x in items if x.get("_strand") in {"A", "B"})

    return {
        "generated_at": generated,
        "radar_last_updated": data.get("last_updated"),
        "scan_health": data.get("scan_health"),
        "counts": {
            "items": len(items),
            "fresh_ab": fresh_ab,
            "current_c": current_c,
            "cumulative_ab": cumulative_ab,
        },
        "topics": topics,
    }


def esc(v: Any) -> str:
    return html.escape(clean(v), quote=True)


def item_html(item: dict[str, Any]) -> str:
    href = esc(item.get("link"))
    title = esc(item.get("title"))
    title_html = f'<a href="{href}" target="_blank" rel="noopener">{title}</a>' if href else title
    chips = [f'<span class="chip">Strand {esc(item.get("strand"))}</span>']
    if item.get("fresh"):
        chips.append('<span class="chip fresh">NEW / CURRENT</span>')
    if item.get("signal_type"):
        chips.append(f'<span class="chip">{esc(item.get("signal_type"))}</span>')
    if item.get("type"):
        chips.append(f'<span class="chip">{esc(item.get("type"))}</span>')
    related = "".join(f'<span class="related">{esc(x)}</span>' for x in item.get("related_topics", []))
    related_html = f'<div class="related-row"><span>Also touches:</span>{related}</div>' if related else ""
    rel = esc(item.get("relevance"))
    rel_html = f'<div class="relevance"><strong>Radar relevance:</strong> {rel}</div>' if rel else ""
    anchor = esc(item.get("anchor"))
    anchor_html = f'<div class="anchor"><strong>Anchor:</strong> {anchor}</div>' if anchor else ""
    source_bits = [esc(item.get("source")), esc(item.get("date"))]
    source_line = " · ".join(x for x in source_bits if x)
    return f"""
<li class="insight-item">
  <div class="chips">{''.join(chips)}</div>
  <h3>{title_html}</h3>
  <div class="meta">{source_line}</div>
  <p>{esc(item.get('note'))}</p>
  {rel_html}{anchor_html}{related_html}
</li>"""


def render_page(briefing: dict[str, Any]) -> str:
    counts = briefing.get("counts", {})
    topics = briefing.get("topics", [])
    nav = "".join(
        f'<a href="#{esc(t["key"])}">{esc(t["name"])} <span>{t["count"]}</span></a>' for t in topics
    ) or '<span class="empty">No topic groups yet.</span>'
    sections = []
    for t in topics:
        items = "".join(item_html(x) for x in t.get("items", []))
        sections.append(f"""
<section class="topic" id="{esc(t['key'])}">
  <div class="topic-head"><div><div class="eyebrow">Topic</div><h2>{esc(t['name'])}</h2></div><div class="topic-count">{t['count']} item{'s' if t['count'] != 1 else ''}</div></div>
  <ul class="insight-list">{items}</ul>
</section>""")
    if not sections:
        sections.append('<section class="topic"><p class="empty">No radar items are available yet.</p></section>')

    updated = esc(briefing.get("radar_last_updated") or "not available")
    generated = esc(briefing.get("generated_at") or "")
    health = esc(briefing.get("scan_health") or "unknown")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>Radar insights — topic digest</title>
<style>
:root{{--bg:#f5f4ef;--panel:#fff;--text:#171716;--muted:#66645e;--line:#d9d6cd;--accent:#6d1f27;--accent-soft:#f4e8e9;--fresh:#0d6b47;--max:1080px}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.52 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}a{{color:inherit}}.wrap{{width:min(calc(100% - 34px),var(--max));margin:auto}}
header{{padding:38px 0 26px;border-bottom:1px solid var(--line);background:var(--panel)}}.kicker,.eyebrow{{font-size:.72rem;font-weight:850;letter-spacing:.13em;text-transform:uppercase;color:var(--accent)}}h1{{font-size:clamp(2.25rem,6vw,4.7rem);line-height:.96;letter-spacing:-.055em;margin:.15em 0 .22em}}.lede{{font-size:1.08rem;color:var(--muted);max-width:820px;margin:0}}.top-actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:19px}}.button{{text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:8px 12px;font-size:.84rem;font-weight:750;background:var(--bg)}}
main{{padding:22px 0 68px}}.stats{{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:17px}}.stat{{border:1px solid var(--line);background:var(--panel);border-radius:999px;padding:5px 9px;font-size:.75rem;color:var(--muted)}}.topic-nav{{display:flex;gap:8px;flex-wrap:wrap;padding:15px;background:var(--panel);border:1px solid var(--line);border-radius:16px;position:sticky;top:8px;z-index:3;box-shadow:0 6px 22px rgba(0,0,0,.04)}}.topic-nav a{{text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:6px 9px;font-size:.79rem;background:var(--bg)}}.topic-nav a span{{color:var(--accent);font-weight:800;margin-left:4px}}
.topic{{scroll-margin-top:90px;margin-top:22px;background:var(--panel);border:1px solid var(--line);border-radius:20px;overflow:hidden}}.topic-head{{display:flex;align-items:end;justify-content:space-between;gap:18px;padding:22px 24px 15px;border-bottom:1px solid var(--line)}}.topic h2{{font-size:clamp(1.55rem,3vw,2.15rem);letter-spacing:-.035em;line-height:1.05;margin:.16em 0 0}}.topic-count{{font-size:.77rem;color:var(--muted);white-space:nowrap}}.insight-list{{list-style:none;padding:0;margin:0}}.insight-item{{padding:19px 24px 20px;border-top:1px solid var(--line)}}.insight-item:first-child{{border-top:0}}.chips{{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:7px}}.chip{{border:1px solid var(--line);border-radius:999px;padding:2px 7px;font-size:.64rem;color:var(--muted);font-weight:700}}.chip.fresh{{color:var(--fresh);border-color:#9ecab8;background:#eef8f3}}.insight-item h3{{font-size:1.04rem;line-height:1.28;margin:0 0 4px}}.insight-item h3 a{{text-decoration-thickness:1px;text-underline-offset:3px}}.meta{{font-size:.76rem;color:var(--muted)}}.insight-item p{{margin:8px 0 0;max-width:900px}}.relevance,.anchor{{margin-top:7px;font-size:.82rem;color:var(--muted)}}.related-row{{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:9px;font-size:.72rem;color:var(--muted)}}.related{{border:1px solid var(--line);border-radius:999px;padding:2px 7px;background:var(--bg)}}.empty{{color:var(--muted)}}.method{{font-size:.8rem;color:var(--muted);padding:18px 2px 0}}footer{{border-top:1px solid var(--line);padding:20px 0 32px;color:var(--muted);font-size:.78rem}}
@media(max-width:680px){{.topic-nav{{position:static}}.topic-head{{align-items:start;flex-direction:column}}.insight-item,.topic-head{{padding-left:18px;padding-right:18px}}}}
</style>
</head>
<body id="top">
<header><div class="wrap">
  <div class="kicker">Radar insights · topical view of the main radar</div>
  <h1>The radar, sorted by subject</h1>
  <p class="lede">No second summary and no extra narrative layer. These are the same admitted radar items, reorganised into practical subject headings so you can quickly scan what the radar says about raw materials, research, AI, energy, security, trade, space and other areas.</p>
  <div class="top-actions"><a class="button" href="../">← Main radar</a></div>
</div></header>
<main class="wrap">
  <div class="stats"><span class="stat">{counts.get('items',0)} radar items</span><span class="stat">{counts.get('fresh_ab',0)} fresh A/B</span><span class="stat">{counts.get('current_c',0)} current C signals</span><span class="stat">scan health: {health}</span></div>
  <nav class="topic-nav" aria-label="Insight topics">{nav}</nav>
  {''.join(sections)}
  <div class="method"><strong>How this page works:</strong> each radar item is assigned to one primary subject heading using transparent keyword matching. It appears only once to avoid repetition. Secondary subject matches are shown as small “Also touches” tags. The wording in each bullet comes from the item already admitted to the main radar.</div>
</main>
<footer><div class="wrap">Radar updated: {updated} · Topic digest generated: {generated}. The builder only reads <code>radar.json</code> and does not modify the scanner corpus.</div></footer>
</body></html>"""


def main() -> int:
    if not RADAR.exists():
        raise SystemExit("radar.json not found")
    data = json.loads(RADAR.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    briefing = make_briefing(data)
    OUT_JSON.write_text(json.dumps(briefing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_HTML.write_text(render_page(briefing), encoding="utf-8")
    print(f"Built {OUT_HTML.relative_to(ROOT)} with {len(briefing['topics'])} populated topic(s) and {briefing['counts']['items']} radar item(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
