"""Single-file offline HTML with expandable sources, period filter and audit trail."""
import html
import json
from collections import Counter
from pathlib import Path
from .storage import rows

def data_model(db,snapshot_id):
    snapshots=[x for x in rows(db,'snapshots') if x['snapshot_id']==snapshot_id]
    ev=[x for x in rows(db,'evidence') if x['snapshot_id']==snapshot_id]
    for e in ev:
        e['metadata']=json.loads(e.pop('metadata_json'))
    relations=[x for x in rows(db,'relations') if x['snapshot_id']==snapshot_id]
    for r in relations:r['evidence']=json.loads(r.pop('evidence_json'))
    chains=[x for x in rows(db,'chains') if x['snapshot_id']==snapshot_id]
    for c in chains:
        for key in ('evidence_ids_json','warnings_json'):
            c[key.removesuffix('_json')]=json.loads(c.pop(key))
    hyps=[x for x in rows(db,'hypotheses') if x['snapshot_id']==snapshot_id]
    for h in hyps:
        for key in ('support_json','against_json','expected_json','falsifier_json','missing_json','evaluation_json'):
            h[key.removesuffix('_json')]=json.loads(h.pop(key))
    assessments=[x for x in rows(db,'llm_assessments') if x['snapshot_id']==snapshot_id]
    for a in assessments:
        a['output']=json.loads(a.pop('output_json'))
        a['errors']=json.loads(a.pop('validation_errors_json'))
    summaries=[x for x in rows(db,'syntheses') if x['snapshot_id']==snapshot_id]
    for summary in summaries:
        summary['content']=json.loads(summary.pop('content_json'))
        summary['errors']=json.loads(summary.pop('errors_json'))
        summary['evidence_ids']=json.loads(summary.pop('evidence_ids_json'))
    raw=[x for x in rows(db,'raw_records') if x['snapshot_id']==snapshot_id]
    sheet_counts=dict(Counter(x['sheet'] for x in raw))
    years=dict(sorted(Counter(e['publication_date'][:4] for e in ev if e['publication_date']).items()))
    families=dict(Counter(e['source_family'] for e in ev).most_common(12))
    return {'snapshot':snapshots[0] if snapshots else {},'counts':{'raw_records':len(raw),'evidence':len(ev),'relations':len(relations),'chains':len(chains)},
            'sheets':sheet_counts,'years':years,'source_families':families,'evidence':ev,'relations':relations,
            'chains':chains,'hypotheses':hyps,'llm_assessments':assessments,'syntheses':summaries}

HTML=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Historical Trajectory — Evidence Review</title><style>
:root{color-scheme:light;--navy:#172c43;--ink:#263b52;--muted:#667b8d;--line:#dce5ea;--pale:#f4f7fa;--light:#fff;--accent:#255f9b}
*{box-sizing:border-box}body{background:var(--pale);color:var(--ink);margin:0;font:15px/1.65 system-ui,-apple-system,Segoe UI,Arial}
main{max-width:1160px;margin:auto;padding:28px 20px 70px}h1{font-size:clamp(29px,5vw,52px);color:var(--navy);line-height:1.11;margin:12px 0}h2{font-size:23px;color:var(--navy)}h3{font-size:17px;color:var(--navy);margin:0 0 6px}
.kicker{font-size:12px;font-weight:800;letter-spacing:.13em;text-transform:uppercase;color:#4b6680}.lede{font-size:18px;max-width:850px;color:#506981}
.panel{background:white;border:1px solid var(--line);border-radius:18px;padding:24px;margin:20px 0;box-shadow:0 6px 20px #172c4310}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px}.stat{background:#eef4f9;border-radius:12px;padding:12px 16px}.stat strong{display:block;font-size:27px;color:var(--navy)}
.note{border-left:4px solid #bf8237;padding:10px 15px;background:#fffbf3;margin:14px 0;border-radius:8px}
.badge{display:inline-block;background:#eaf0f6;padding:2px 9px;border-radius:7px;color:#35536b;font-size:12px;font-weight:700}
.row{padding:12px 0;border-bottom:1px solid var(--line)}.sub{color:var(--muted);font-size:13px}a{color:var(--accent)}
select,input{padding:10px;border:1px solid #cad7e2;border-radius:9px;background:white;color:var(--navy);font:inherit;max-width:100%}
.filter{display:flex;flex-wrap:wrap;gap:10px;align-items:center}.filter input{flex:1;min-width:170px}button{background:var(--accent);color:white;padding:10px 14px;border:0;border-radius:8px;cursor:pointer}
summary{cursor:pointer;color:var(--navy);font-weight:700}details{background:#fbfcfe;border:1px solid var(--line);border-radius:11px;margin:10px 0;padding:12px 15px}
.timeline{border-left:3px solid #c7d6e7;margin-left:8px;padding-left:18px}.timeline .row{position:relative}.timeline .row:before{content:' ';position:absolute;left:-25px;top:20px;background:#6c98c2;width:11px;height:11px;border-radius:50%}
pre{white-space:pre-wrap;word-break:break-word;background:#f2f6f9;padding:10px;border-radius:9px;font:12px/1.6 ui-monospace,Consolas,monospace}
small{color:var(--muted)}.hidden{display:none!important}footer{font-size:13px;color:#52677b}
@media(max-width:650px){.panel{padding:17px}main{padding:17px 12px}}
</style></head><body><main>
<div class="kicker">Historical evidence · offline audit · R&amp;I</div><h1>How did we get from there to here?</h1>
<p class="lede">A source-first historical view of the supplied knowledge base. Development chains are candidates for investigation—not automatic proof that one event caused another.</p>
<div class="panel"><h2>What the evidence establishes</h2><div id="stats" class="grid"></div><p id="snapshot" class="sub"></p>
<div class="note"><b>Interpretation status:</b> Without an LLM, this report gives conservative chronology, data-derived groups and tests of candidate explanations. It <b>does not</b> claim to have discovered verified turning points or causal narratives. Source verification labels are inherited from the database, not independently rechecked.</div>
<div id="coverage"></div></div>
<div class="panel"><h2>Overall historical interpretation</h2><div id="synthesis"></div></div>
<div class="panel"><h2>The historical journey</h2><p>Look at the chronological evidence first. The filter affects the visible record—not the original workbook or database.</p>
<div class="filter"><label for="from">From</label><select id="from"></select><label for="to">To</label><select id="to"></select><input id="query" placeholder="Find developments, organisations, claims…"></div>
<div id="timeline" class="timeline"></div></div>
<div class="panel"><h2>Possible historical development chains</h2><p>Groups below are discovered from workbook subject labels or repeated terminology. Read their evidence before treating them as one story.</p><div id="chains"></div></div>
<div class="panel"><h2>Competing explanations &amp; challenges</h2><p>Every candidate interpretation is checked for independent evidence, alternative explanations, metadata verification and source-family dependence. These are tests of documentary support, not mathematical proof of history.</p><div id="hypotheses"></div></div>
<div class="panel"><h2>Optional model reasoning</h2><p>When a local LLM is enabled, the report may include a first pass and a separate adversarial pass. Neither is accepted unless it cites existing evidence identifiers.</p><div id="llm"></div></div>
<div class="panel"><h2>Audit and source inspection</h2><div class="filter"><input id="searchEvidence" placeholder="Filter original source records…"></div><div id="sources"></div></div>
<footer>Privacy: all searches on this page run inside your browser. This HTML embeds source notes and must be treated as private if the workbook contains private material. Original publication date and event date remain distinct. No network access is made by this page except if you open a linked source.</footer>
</main><script id="data" type="application/json">__JSON__</script>
<script>
const data=JSON.parse(document.getElementById('data').textContent), E=Object.fromEntries(data.evidence.map(e=>[e.evidence_id,e]));
const $=x=>document.getElementById(x), el=(name,text,cls)=>{const x=document.createElement(name);if(text!==undefined)x.textContent=String(text);if(cls)x.className=cls;return x};
const add=(node,child)=>{node.appendChild(child);return child};
function linkFor(e){if(!e.source_url)return el('span','No original link in data','sub');const a=el('a','Original source ↗');a.href=e.source_url;a.target='_blank';a.rel='noopener noreferrer';return a}
function evidenceNode(e,brief=false){const d=el('div',undefined,'row');add(d,el('b',(e.publication_date||'Undated')+' · '+(e.title||'(untitled)')));add(d,el('div',e.claim_text.slice(0,brief?260:1100)));const s=add(d,el('div',undefined,'sub'));s.append(linkFor(e),el('span',' · '+e.evidence_type+' · '+e.source_quality+' · '+e.evidence_id));if(!brief){add(d,el('div','Event date: '+(e.event_date||'not supplied')+' · Published: '+(e.publication_date||'not supplied')+' · Original sheet: '+e.origin_sheet+' · Row: '+e.metadata.raw_row,'sub')); if(e.qualifications)add(d,el('div','Qualifications: '+e.qualifications,'sub'));}return d}
[['Original rows',data.counts.raw_records],['Unique source records',data.counts.evidence],['Candidate links',data.counts.relations],['Candidate chains',data.counts.chains]].forEach(([a,b])=>{const div=add($('stats'),el('div',undefined,'stat'));add(div,el('strong',b));add(div,el('span',a))});
$('snapshot').textContent='Workbook: '+data.snapshot.workbook_name+' · '+data.snapshot.generated_utc+' · Snapshot '+data.snapshot.snapshot_id;
const synth=$('synthesis'), meta=data.syntheses.find(x=>x.pass_type==='adversarial_synthesis'&&x.accepted);
if(!meta){add(synth,el('p','No independently challenged overall LLM narrative is available. The evidence may establish parallel trajectories, or too little basis for one overarching explanation.'));}
else{add(synth,el('div','Model-assisted, source-reference-validated interpretation. Linked original sources have NOT automatically been checked.','note'));add(synth,el('p',meta.content.overview));
for(const section of ['trajectories','turning_points','connections']){const arr=meta.content[section]||[];if(arr.length)add(synth,el('h3',section.replace('_',' ')));for(const entry of arr){const d=add(synth,el('details'));add(d,el('summary',entry.interpretation));add(d,el('div',entry.assessment+' · supporting records '+entry.support_ids.length,'sub'));for(const id of entry.support_ids){if(E[id])d.append(evidenceNode(E[id],true));}}}}
const cov=$('coverage');add(cov,el('h3','Coverage is not a measure of real-world activity'));
add(cov,el('div',Object.entries(data.sheets).map(([k,v])=>k+': '+v+' rows').join(' · '),'sub'));
add(cov,el('div','Publication-year coverage: '+Object.entries(data.years).map(([k,v])=>k+' ('+v+')').join(', '),'sub'));
const years=Object.keys(data.years), low=years[0]||'All', high=years.at(-1)||'All';
for(const selector of ['from','to']){const node=$(selector);for(const yr of years){const op=el('option',yr);op.value=yr;node.append(op)}node.value=selector==='from'?low:high}
function rerender(){const from=$('from').value,to=$('to').value,q=$('query').value.toLowerCase();const eligible=data.evidence.filter(e=>e.publication_date&&e.publication_date.slice(0,4)>=from&&e.publication_date.slice(0,4)<=to&&((e.title+' '+e.claim_text+' '+e.subject).toLowerCase().includes(q))).sort((a,b)=>(a.publication_date||'').localeCompare(b.publication_date||''));
const mount=$('timeline');mount.replaceChildren();for(const e of eligible.slice(0,250))mount.append(evidenceNode(e,true));add(mount,el('div','Showing '+Math.min(250,eligible.length)+' of '+eligible.length+' matching dated source records. Dates shown are publication dates, NOT event dates.','sub'))}
['from','to','query'].forEach(id=>$(id).addEventListener(id==='query'?'input':'change',rerender));rerender();
const cdiv=$('chains');if(!data.chains.length)cdiv.append(el('p','The records do not establish sufficient shared subjects for development chains.'));
for(const c of data.chains.sort((a,b)=>b.evidence_ids.length-a.evidence_ids.length).slice(0,60)){const d=add(cdiv,el('details'));const s=add(d,el('summary',c.subject.replace(/^\w+: /,'')+' · '+c.evidence_ids.length+' records · '+(c.period_start||'?')+'–'+(c.period_end||'?')));add(d,el('p',c.description));for(const warn of c.warnings)add(d,el('p',warn,'sub'));for(const id of c.evidence_ids.slice(0,80))if(E[id])d.append(evidenceNode(E[id],true));}
const hdiv=$('hypotheses');const group={};for(const h of data.hypotheses)(group[h.chain_id]??=[]).push(h);
for(const c of data.chains.slice(0,60)){const hs=group[c.chain_id]||[];if(!hs.length)continue;const d=add(hdiv,el('details'));add(d,el('summary',c.subject.replace(/^\w+: /,'')+' — '+hs.length+' competing candidate explanations'));
for(const h of hs){add(d,el('h3',h.claim));add(d,el('span',h.status,'badge'));add(d,el('div','Alternative: '+h.alternative));add(d,el('div','Support IDs: '+h.support.join(', '),'sub'));add(d,el('div','Missing / contrary considerations: '+(h.missing.join(' · ')||'Not recorded'),'sub'));add(d,el('div','If correct, one would expect: '+h.expected.join(' · '),'sub'));add(d,el('div','Robustness: leave-source-family-out '+(h.evaluation.survives_leave_family_out?'survived':'fragile')+', verified-only '+(h.evaluation.verified_only_survives?'survived':'fragile'),'sub'));}}
const ldiv=$('llm');if(!data.llm_assessments.length)add(ldiv,el('p','No LLM was run. The deterministic analysis remains available without a paid API. Use the documented local Ollama command to add separate generation and challenge passes.'));
for(const a of data.llm_assessments){const d=add(ldiv,el('details'));add(d,el('summary',a.pass_type+' · '+(a.accepted?'validated references':'rejected output')+' · '+a.chain_id));add(d,el('pre',JSON.stringify(a.output,null,2)));if(a.errors.length)add(d,el('div','Validation problems: '+a.errors.join('; '),'sub'))}
const sdiv=$('sources');function sourceFilter(){sdiv.replaceChildren();const q=$('searchEvidence').value.toLowerCase();const found=data.evidence.filter(e=>(e.claim_text+' '+e.title+' '+e.source_url+' '+e.evidence_id).toLowerCase().includes(q));for(const e of found.slice(0,120))sdiv.append(evidenceNode(e));add(sdiv,el('div','Showing '+Math.min(found.length,120)+' / '+found.length+' sources. All original source records and raw workbook rows are retained in the SQLite export.','sub'))}
$('searchEvidence').addEventListener('input',sourceFilter);sourceFilter();
</script></body></html>'''

def render(db,snapshot_id,destination):
    model=data_model(db,snapshot_id)
    payload=json.dumps(model,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    Path(destination).write_text(HTML.replace('__JSON__',payload),encoding='utf-8')
    return model
