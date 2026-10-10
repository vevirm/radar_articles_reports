"""Narrative-first OFFLINE report. All assertions of events link to source notes.
No browser calls to remote API, and no false claim of independent fact checking.
"""
import json
from pathlib import Path

PAGE=r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Historical Trajectories | From expectations to outcomes</title>
<style>
:root{--bg:#f6f7f9;--ink:#1c2c3f;--sub:#52677b;--line:#dde4ea;--blue:#164e82;--gold:#97622b;--light:#fff}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;line-height:1.64;margin:0}
header{background:#102b46;color:white;padding:48px max(22px,calc((100vw - 1150px)/2)) 43px}
header h1{font-size:clamp(34px,5.4vw,60px);letter-spacing:-1.8px;line-height:1.08;max-width:850px;margin:10px 0 18px}header p{color:#d7e3f0;max-width:810px;font-size:18px;margin:0}
.kicker{font-size:12px;font-weight:750;letter-spacing:2px;text-transform:uppercase;color:#a6d7f2}
main{max-width:1150px;margin:auto;padding:20px 20px 90px}.intro{background:white;border:1px solid var(--line);border-radius:16px;padding:24px;margin:0 0 23px}
.summary{display:flex;gap:15px;flex-wrap:wrap}.stat{background:#edf3f7;border-radius:9px;padding:12px 16px;min-width:140px}.stat b{font-size:24px;display:block}.stat small{font-size:12px;color:var(--sub)}
.info{border-left:4px solid #ac7a43;background:#fff8ed;padding:12px 17px;margin:15px 0 0;border-radius:4px;font-size:14px}
h2{font-size:clamp(23px,3vw,31px);letter-spacing:-.5px;line-height:1.2;margin:0 0 7px}h3{font-size:16px;margin:0 0 7px}p{margin:5px 0 12px}
.topic{background:white;border:1px solid var(--line);border-radius:17px;padding:29px;margin:23px 0;box-shadow:0 6px 22px #102b4609;scroll-margin-top:16px}
.topic .head{display:flex;gap:12px;justify-content:space-between;align-items:flex-start;flex-wrap:wrap}
.meta{font-size:12px;color:var(--sub)}.tag{padding:4px 9px;background:#e8eef5;border-radius:8px;font-size:11px;color:#35536f;font-weight:750}
.journey{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;margin:20px 0}
.station{background:#f6f8fa;border:1px solid #e4eaf0;border-radius:12px;padding:15px;min-width:0}
.station h3{font-size:14px;text-transform:uppercase;letter-spacing:.08em;color:#285a89}.stage-meta{font-size:11px;color:var(--sub)}
.event{border-top:1px solid var(--line);padding:11px 0}.event:first-of-type{border:0}.event b{font-size:13px;line-height:1.4;display:block}.event p{font-size:13px;color:#364c62;line-height:1.5;margin:4px 0}.event a{font-size:12px;color:var(--blue);text-decoration:underline}
.verdict{padding:17px;border:1px solid #e8d7bd;background:#fffcf7;border-radius:11px;margin-top:16px}.verdict b{color:#67441e}
.actions{margin-top:16px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}button{cursor:pointer;font:inherit;border-radius:8px;border:1px solid #0c507d;background:#165587;color:white;padding:8px 14px;font-weight:650;font-size:13px}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #9ecafb;outline-offset:3px}button.secondary{background:white;color:var(--blue)}
details{margin:11px 0;border:1px solid var(--line);border-radius:9px;padding:10px 14px}summary{font-size:13px;font-weight:700;color:#285475;cursor:pointer}pre{max-height:230px;overflow:auto;background:#f0f4f8;border-radius:8px;white-space:pre-wrap;overflow-wrap:anywhere;font:11px/1.55 ui-monospace,monospace;padding:12px}
.notes{font-size:12px;color:var(--sub)}#topics-list{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 0}#topics-list a{font-size:12px;text-decoration:none;color:var(--blue);border:1px solid #c5d4e1;border-radius:20px;padding:6px 10px;background:#fff}
footer{font-size:12px;color:var(--sub);max-width:900px;margin:35px auto}
@media(max-width:790px){.journey{grid-template-columns:1fr}.topic{padding:20px}header{padding:38px 20px}.station{padding:13px}}
</style></head><body>
<header><div class="kicker">R&I RADAR · AUTOMATIC TOPIC DISCOVERY</div><h1>What was expected.<br>What happened.<br>How did we get here?</h1><p>Historical journeys discovered from your two source libraries, organised by subject. Each journey shows what the available records actually say, then gives a careful first comparison and links to the evidence.</p></header>
<main><div class="intro"><h2>Overview of the historical record</h2><p id="lead"></p><div class="summary" id="stats"></div><div class="info"><strong>How to read this:</strong> Topics are generated automatically from publication text. They are provisional groupings, not verified causal histories. Earlier publication ≠ earlier prediction; newer proposal ≠ success or failure. The report will explicitly say when the data cannot establish whether expectations came true.</div><div id="topics-list"></div></div>
<div id="journeys"></div><footer>Evidence provenance is preserved in report.json and the SQLite database. The publication date is shown for each record; an earlier event described in a later publication is not silently backdated. This report is built without a paid AI service. Deep comparative reasoning requires the optional research prompts or LLM workflow.</footer></main>
<script id="data" type="application/json">__DATA__</script><script>
const model=JSON.parse(document.getElementById('data').textContent),journeys=model.journeys;
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined&&text!==null)n.textContent=text;if(cls)n.className=cls;return n};
const at=(parent,node)=>{parent.appendChild(node);return node};
const stat=at(document.getElementById('stats'),el('div',undefined,'stat'));
const figures=[['Discovered topics',journeys.length],['Historical source records',model.oldCount],['Current source records',model.currentCount],['Earlier-year records',model.pre2026]];
for(const [name,value] of figures){const s=at(document.getElementById('stats'),el('div',undefined,'stat'));at(s,el('b',value.toLocaleString()));at(s,el('small',name))}stat.remove();
document.getElementById('lead').textContent='The available records cover '+(model.firstYear||'unknown')+' to '+(model.lastYear||'unknown')+'. The document collection is unevenly distributed across years. These are automatically discovered topic groups, not a representative history of everything that happened.';
function eventNode(e){const d=el('div',undefined,'event');at(d,el('div',(e.published||'Undated')+' · '+(e.origin==='Historical findings'?'Historical Radar':'Main Radar'),'stage-meta'));at(d,el('b',e.title));if(e.claim&&e.claim!==e.title)at(d,el('p',e.claim));const a=at(d,el('a',e.url?'Original source ↗':'No original link'));if(e.url){a.href=e.url;a.target='_blank';a.rel='noopener noreferrer'}else a.removeAttribute('href');return d}
function stage(outer,label,subtitle,records){const div=at(outer,el('section',undefined,'station'));at(div,el('h3',label));at(div,el('div',subtitle,'stage-meta'));if(!records.length)at(div,el('p','The available record does not establish this stage.','notes'));for(const e of records)div.appendChild(eventNode(e));return div}
journeys.forEach((x,i)=>{
 const article=at(document.getElementById('journeys'),el('article',undefined,'topic'));article.id=x.id;
 const head=at(article,el('div',undefined,'head')),hl=at(head,el('div'));
 at(hl,el('div','JOURNEY '+String(i+1).padStart(2,'0')+' · '+(x.span_start||'?')+' → '+(x.span_end||'?'),'meta'));
 at(hl,el('h2',x.title));at(hl,el('div',x.count+' source records · '+x.count_older+' published before 2026 · '+x.distinct_families+' source families','meta'));
 at(head,el('span','Automated topic grouping','tag'));
 const timeline=at(article,el('div',undefined,'journey'));
 stage(timeline,'1 · What was expected?','Earlier plans, forecasts or first historical references',x.earlier);
 stage(timeline,'2 · What developed?','Intermediate evidence — no cause assumed',x.through);
 stage(timeline,'3 · What happened?','Later records — distinguish new proposals from results',x.now);
 const vd=at(article,el('div',undefined,'verdict'));at(vd,el('b','Did it go approximately as expected? '+x.verdict+'.'));at(vd,el('p',x.reason));
 if(x.cautions.length)at(vd,el('div','Evidence limits: '+x.cautions.join(' '),'notes'));
 const sources=at(article,el('details'));at(sources,el('summary','Topic evidence and original links'));at(sources,el('p','All publication IDs for this group are preserved in report.json and historical_evidence.sqlite. Source samples are shown above. The match is thematic until verified against the original records.','notes'));
 at(sources,el('div','Themes found in the source text: '+x.keywords.slice(0,7).join(' · '),'notes'));
 const prompt=at(article,el('details'));at(prompt,el('summary','Optional: study this journey deeply with an LLM'));at(prompt,el('p','The prompt challenges the preliminary grouping. It does not assume shared words mean one event caused another.','notes'));
 const b=at(prompt,el('button','Copy detailed research prompt'));b.addEventListener('click',()=>{const fallback=()=>{const p=at(prompt,el('pre',x.prompt));p.scrollIntoView({block:'nearest'});b.textContent='Select and copy the prompt below';};if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(x.prompt).then(()=>b.textContent='Copied — paste into your LLM').catch(fallback);else fallback()});
 at(document.getElementById('topics-list'),(()=>{const a=el('a',x.title);a.href='#'+x.id;return a})());
});
</script></body></html>'''

def write_page(path,journeys,evidence):
    dates=[e['publication_date'][:4] for e in evidence if e['publication_date']]
    obj={'journeys':journeys,'oldCount':sum(x['origin_sheet']=='Historical findings' for x in evidence),
         'currentCount':sum(x['origin_sheet']=='All publication data' for x in evidence),
         'pre2026':sum(bool(x['publication_date'] and x['publication_date'][:4]<'2026') for x in evidence),
         'firstYear':min(dates) if dates else None,'lastYear':max(dates) if dates else None}
    raw=json.dumps(obj,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    Path(path).write_text(PAGE.replace('__DATA__',raw),encoding='utf8')
