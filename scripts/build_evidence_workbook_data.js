#!/usr/bin/env node
'use strict';
const fs=require('fs'),path=require('path');
const ROOT=path.resolve(__dirname,'..');
const radar=JSON.parse(fs.readFileSync(path.join(ROOT,'radar.json'),'utf8'));
globalThis.RadarInsights=require(path.join(ROOT,'briefing','insights.js'));
const Merit=require(path.join(ROOT,'source_merit.js'));
const Frontier=require(path.join(ROOT,'frontier','frontier.js'));
const frontier=Frontier.buildFrontier(radar);
const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
const norm=v=>clean(v).toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const canonicalTitle=v=>norm(clean(v).replace(/^(?:executive summary|event report|policy brief|research brief|briefing|report)\s*:\s*/i,'').replace(/\s+[–—-]\s+(?:company announcement\s+-\s+)?(?:ft\.com|reuters|bloomberg|euractiv\.com)$/i,''));
const arr=v=>Array.isArray(v)?v.filter(Boolean).map(clean).join(' · '):clean(v);
function quality(x){return (clean(x.summary).length?200:0)+Math.min(300,clean(x.summary).length)+(clean(x.authors)?40:0)+(clean(x.source)?20:0)+(clean(x.link)?10:0)}
function dedupe(raw){const groups=[],byKey=new Map();for(const x of raw){const u=clean(x.link).toLowerCase(),t=canonicalTitle(x.title||x.headline),keys=[];if(u)keys.push('u:'+u);if(t&&t.length>=28)keys.push('t:'+t);let idx=-1;for(const k of keys){if(byKey.has(k)){idx=byKey.get(k);break}}if(idx<0){idx=groups.length;groups.push(x)}else if(quality(x)>quality(groups[idx]))groups[idx]=x;for(const k of keys)byKey.set(k,idx)}return groups.filter(Boolean)}
const sigByLink=new Map(),sigByTitle=new Map();
for(const s of frontier.signals){const u=clean(s.link).toLowerCase(),t=canonicalTitle(s.bibliographicTitle||s.title);if(u&&!sigByLink.has(u))sigByLink.set(u,s);if(t&&!sigByTitle.has(t))sigByTitle.set(t,s)}
function matrixFor(x){const u=clean(x.link).toLowerCase(),t=canonicalTitle(x.title||x.headline);return sigByLink.get(u)||sigByTitle.get(t)||null}

function sourceTakeaways(x){
  const bullets=[];
  const savedSummary=clean(x.summary||'');
  const metadataOnly=/item was admitted to Strand|consult the linked publication for the full argument|source text available at scan time/i.test(savedSummary);
  const seen=[];
  const add=v=>{let q=clean(v).replace(/^Abstract\s*/i,'').replace(/^Practical implications\s+/i,'').replace(/^Geographical scope\s+\d+(?:\.\d+)?\s*/i,'').replace(/^Target company development stage:\s*/i,'').replace(/\.{2,}$/,'.').replace(/\bthis Analysis\b/g,'the analysis').trim();if(!q||/^Source focus:/i.test(q)||/^\d+(?:\s+\d+){2,}\s+[A-Z]/.test(q)||/its EU relevance is classified|consult the linked publication|item was admitted to Strand|source text available at scan time|collected from researchers/i.test(q))return;const n=norm(q);if(!n||seen.some(z=>n===z||n.includes(z)||z.includes(n)))return;if(/^(?:this|the) (?:study|paper|article|report|research) (?:aims|examines|uses|is based on)|\bmethodology\b|\bpurpose\b/i.test(q))return;if(q.length>330)return;seen.push(n);bullets.push(q.replace(/[;:,]+$/,'').replace(/([^.!?])$/,'$1.'));};
  if(!metadataOnly)add(globalThis.RadarInsights?.whatForEuRiGeo?.(x)||x.core_message||'');
  let summary=savedSummary.replace(/(?<=[a-z0-9])\.(?=[A-Z])/g,'. ');
  const title=clean(x.title||x.headline||'');
  if(title&&summary.toLowerCase().startsWith(title.toLowerCase()))summary=summary.slice(title.length).replace(/^[\s.:;–—-]+/,'');
  const ss=summary.split(/(?<=[.!?])\s+(?=[A-Z0-9“"'‘])/).map(clean).filter(Boolean);
  const scored=ss.map((q,i)=>{let score=0;if(/\b(show|find|argu|conclud|reveal|indicat|suggest|highlight|demonstrat|rank|depend|rely|increase|reduce|shift|change|constrain|enable|strengthen|weaken|concentrat|retain|attract|exclude|require|propos|adopt|fund|invest|link|reconfigur|reshape)\w*/i.test(q))score+=8;if(/[€$£]\s?\d|\b\d+(?:\.\d+)?\s?(?:%|bn|billion|million|GW|MW|years?|months?)\b/i.test(q))score+=4;if(/\b(EU|Europe|European|China|US|United States|Ukraine|Russia|India|Japan|Taiwan|Commission|Council|Horizon Europe|ERC|MSCA)\b/i.test(q))score+=3;if(/^(?:this|the) (?:study|paper|article|report|research) (?:aims|examines|uses|is based on)|\bmethodology\b|\bpurpose\b/i.test(q))score-=12;score-=i*.1;return {q,score};}).sort((a,b)=>b.score-a.score);
  for(const o of scored){if(bullets.length>=4)break;if(o.score>0)add(o.q);}
  if(!metadataOnly&&bullets.length<2){for(const q of [...(Array.isArray(x.eu_evidence)?x.eu_evidence:[]),...(Array.isArray(x.ri_evidence)?x.ri_evidence:[]),...(Array.isArray(x.geo_evidence)?x.geo_evidence:[])]){if(bullets.length>=3)break;add(q);}}
  if(!bullets.length)bullets.push('The saved radar state does not contain a substantive source finding for this record; use the source link for the full argument and evidence.');
  return bullets.slice(0,4);
}

function windowClass(x,m){const d=clean(x.date).slice(0,10),core=clean(radar.preferred_corpus_start_date||radar.corpus_start_date),ext=clean(radar.extended_top_quality_start_date);if(!d)return 'Date unavailable';if(core&&d>=core)return '4-month core';if(ext&&d>=ext&&m.score>=93)return '4–6 month Highest-quality extension';return 'Outside active public window / retained metadata';}
const raw=[...(radar.strand_a||[]),...(radar.strand_b||[]),...(radar.strand_c||[]),...(radar.frontier_evidence||[])];
const records=dedupe(raw).map(x=>{
  const m=Merit.forItem(x),comp=Merit.componentsFor(x),mx=matrixFor(x);
  return {
    record:x, merit:m, components:comp, matrix:mx,
    technicalWhat:clean(globalThis.RadarInsights?.whatForEuRiGeo?.(x)||x.core_message||''),
    sourceTakeaways:sourceTakeaways(x),
    sourceSummary:clean(x.summary||''),
    technicalWhy:clean(x.relevance_note||globalThis.RadarInsights?.whyFor?.(x)||x.why_it_matters||''),
    windowClass:windowClass(x,m)
  };
}).sort((a,b)=>b.merit.score-a.merit.score||clean(b.record.date).localeCompare(clean(a.record.date))||clean(a.record.title||a.record.headline).localeCompare(clean(b.record.title||b.record.headline)));
const rows=records.map((o,i)=>{const x=o.record,m=o.merit,c=o.components,mx=o.matrix;return {
  rank:i+1,
  merit_score:m.score,
  merit_band:`${m.code} — ${m.long}`,
  publication:clean(x.title||x.headline)||'Untitled',
  date:clean(x.date).slice(0,10),
  strand:clean(x.strand)|| (x.headline?'C':''),
  journal_outlet: clean(x.source),
  institution_source: clean(x.source),
  authors: clean(x.authors),
  authority_class:c.authority,
  relevance_class:c.relevance,
  evidence_class:c.evidence,
  scanner_source_tier:clean(x.source_tier||x.sourceTier),
  source_link:clean(x.link),
  authority_pts:c.authorityPoints,
  relevance_pts:c.relevancePoints,
  evidence_pts:c.evidencePoints,
  author_transparency_pts:c.authorTransparencyPoints,
  window_class:o.windowClass,
  admission_decision:clean(x.decision||x.source_review_status||x.manual_record_status||''),
  technical_radar_claim:o.technicalWhat,
  what_source_says:o.sourceTakeaways,
  source_summary:o.sourceSummary,
  relevance_admission_note:clean(x.relevance_note),
  eu_evidence:arr(x.eu_evidence),
  ri_evidence:arr(x.ri_evidence),
  strategic_evidence:arr(x.geo_evidence),
  matrix_row:mx?mx.row.name:'',
  matrix_column:mx?`${mx.column.id} — ${mx.column.name}`:'',
  matrix_cell:mx?mx.cellName:'',
  matrix_evidence_basis:clean(x.matrix_evidence_basis||mx?.matrixEvidenceBasis||''),
  matrix_placement_confidence:mx?mx.confidence:'',
  matrix_screening_score:mx?mx.triage.total:'',
  matrix_questions:mx?[mx.questionFlags.sustain?'keep access':'',mx.questionFlags.compete?'stay strong':'',mx.questionFlags.failure?'what could fail':''].filter(Boolean).join(' · '):'',
  discovery_provenance:clean(x.discovery_provenance||mx?.discoveryProvenance),
  provenance:arr(x.provenance),
  first_seen:clean(x.first_seen),
  source_text_mode:clean(x.source_text_mode||x.text_mode),
  source_review_basis:clean(x.source_review_basis),
  source_reviewed_at:clean(x.source_reviewed_at),
  source_merit_explanation:Merit.explanation(x)
};});
const payload={
  generated_from:{last_updated:radar.last_updated,preferred_corpus_start_date:radar.preferred_corpus_start_date,extended_top_quality_start_date:radar.extended_top_quality_start_date,window_policy:radar.corpus_window_policy,a:(radar.strand_a||[]).length,b:(radar.strand_b||[]).length,c:(radar.strand_c||[]).length,matrix_findings:frontier.signals.length},
  rows
};
const out=process.argv[2]||path.join(ROOT,'stuff','evidence_workbook_data.json');
fs.writeFileSync(out,JSON.stringify(payload,null,2));
console.log(`Wrote ${rows.length} deduplicated records to ${out}`);
