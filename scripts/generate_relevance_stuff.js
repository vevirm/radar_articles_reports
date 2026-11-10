#!/usr/bin/env node
'use strict';
// Target-only Excel; uses the established no-dependency OOXML writer from stuff/workbook.js.
const fs=require('fs'),path=require('path');
const Workbook=require('../stuff/workbook.js');
const root=path.resolve(__dirname,'..');
const input=process.argv[2]||process.env.RELEVANCE_REPORT_JSON;
if(!input)throw new Error('Usage: node scripts/generate_relevance_stuff.js <report.json> [output.xlsx]');
const output=process.argv[3]||path.join(root,'Relevance Stuff','relevance_stuff.xlsx');
const data=JSON.parse(fs.readFileSync(input,'utf8'));
const verified=Array.isArray(data.verified)?data.verified:[];
const pending=Array.isArray(data.pending)?data.pending:[];
const regionalLeads=Array.isArray(data.regional_leads)?data.regional_leads:[];
const globalVerified=Array.isArray(data.global_verified)?data.global_verified:[];
const awaiting=pending.filter(r=>r.workflow_state==='Deep Scan not complete');
const admissionReview=pending.filter(r=>r.workflow_state!=='Deep Scan not complete');
const headers=['Relevance score','Title','Date','Source','Source location','Strand','Countries / subregions','Geographic group','Matched emerging issues','Stakeholders','Why matched','What evidence says','Why it matters','Admission','Workflow stage','Deep Scan status','Deep Scan checked at','Deep Scan package','Authors','Original source URL'];
const keys=['score','title','date','source','source_location','strand','countries','regions','issues','stakeholders','match_reason','reader_what','reader_why','admission','workflow_state','verification','verified_at','deep_scan_package','authors','url'];
const widths=[15,52,14,28,19,12,39,27,57,38,57,65,65,16,42,32,22,35,40,64];
const toRows=arr=>arr.map(r=>keys.map(k=>k==='score'?Number(r[k]||0):String(r[k]??'')));
const coverage=[];
for(const [type,names] of Object.entries(data.catalogue||{})){
  for(const name of names){
    const inVerified=verified.filter(x=>x[type]&&x[type].split('; ').includes(name)).length;
    const inReview=admissionReview.filter(x=>x[type]&&x[type].split('; ').includes(name)).length;
    const inAwaiting=awaiting.filter(x=>x[type]&&x[type].split('; ').includes(name)).length;
    coverage.push([type,name,inVerified,inReview,inAwaiting]);
  }
}
const notes=[
  ['Purpose','Global R&I futures: Main Radar TOPICS × substantive places outside the EU/UK as the main study setting. Source origin is unrestricted. Global Deep Scan findings are separate from older Radar backfill.'],
  ['Created at (UTC)',String(data.generated_at||'')],
  ['Global verified + KEEP',globalVerified.length],
  ['Legacy Radar verified / retained rows',verified.length],
  ['Admission-review rows (Deep Scan completed)',admissionReview.length],
  ['Awaiting Deep Scan / source recovery rows',awaiting.length],
  ['Verified rule','Deep Scan work status=verified + authoritative reader identity verification + final admission KEEP.'],
  ['Admission review rule','Deep Scan identity verified, but final Admission decision is REVIEW. Requires human admission decision, not another normal Deep Scan package.'],
  ['Cumulative regional discovery leads',regionalLeads.length],
  ['Awaiting Deep Scan rule','Deep Scan not complete; items may already be assigned to existing packages or held for hands-on verification. Check DEEP_SCAN_STATUS.md before creating jobs.'],
  ['Prior workbook correction','The earlier 125-review export was invalid: lowercasing case-sensitive Deep Scan URL keys hid stored KEEP and DROP decisions. Exact-key joins restore those decisions.'],
  ['Source and scope','Only works published since 2025-01-01 from Main Radar A/B/C (including inactive) and stored Deep Scan/Reader decisions. The historical archive is not searched. Dropped/unverifiable/duplicate decisions are excluded.'],
  ['Relevance rule','Named emerging issue or substantive country/region R&I-policy focus in original title or leading Reader evidence. Stakeholder names alone never qualify.'],
  ['Score rule','A relevance-sorting signal, NOT an evidence-quality score or policy forecast.'],
  ['Independent global review','No EU relevance requirement. New global leads do NOT enter the ordinary EU Radar admission gate. Dedicated global Deep Scan verifies identity, topic, substantive geography, source integrity, propaganda risk and possible future R&I significance.'],
  ['Regional leads','Cumulative, DOI-deduplicated indexed discovery leads from all retained Relevance Focus runs are displayed separately. A lead is NOT an admitted, source-verified, or Deep-Scan-verified Radar record.'],
  ['Main Radar connection','A topic must be grounded in the active Radar. The reviewed work may be about India, Kenya, Taiwan or anywhere else without mentioning the EU.'],
  ['Regional balance','No EU/UK discovery quota or minimum: online global focus targets outside EU/UK. Research produced by EU/UK institutes on those places is fully eligible. Place tags come from aboutness, never publisher origin.'],
  ['Backfill','No internet calls or new Deep Scan. Examines existing Main Radar and Deep Scan/Reader evidence dated 2025-01-01 onward; EU/UK-only records are not included in this global output.'],
  ['Aboutness integrity','Legacy country tags without substantive title evidence are quarantined pending renewed discovery. No source/publisher country can create a country tag.'],
  ['Futures discipline','A topic–place possibility is a QUESTION, not a forecast. Global Deep Scan must distinguish observed evidence from potential R&I implications, uncertainty and propaganda risk. Venue counts indicate diversity, not reliability.'],
  ['Limit','A publisher anywhere in the world may publish on any region. Metadata and abstracts may mislead; only independent global Deep Scan KEEP reviews establish checked findings.'],
];
const stats=Object.entries(data.statistics||{}).sort((a,b)=>a[0].localeCompare(b[0]));
const gaps=[];
for(const name of data.catalogue?.countries||[]){
  if(!verified.concat(pending).some(x=>x.countries?.split('; ').includes(name)))gaps.push(['Missing retained evidence',name,0]);
}
const diagnostics=[
  ['Relevance extraction diagnostic','Value'],
  ['Distinct matching records',verified.length+pending.length],
  ['Deep Scan verified and KEEP',verified.length],
  ['Admission REVIEW — Deep Scan complete',admissionReview.length],
  ['Deep Scan not complete',awaiting.length],
  ['Unique works evaluated',data.statistics?.unique_works_evaluated||0],
  ['Stored Reader records evaluated',data.statistics?.stored_reader_records_evaluated||0],
  ['Missing focus geographies',gaps.length],
  ['',''],
  ...stats.map(([k,v])=>[k,v]),
  ['',''],
  ...gaps.map(([,place,value])=>['Zero coverage: '+place,value]),
];
const regionalHeaders=['Match score','Existing Radar issue/topic','Substantive country / region','World area','Aboutness status','Aboutness evidence','Future R&I question (not forecast)','Time perspective','Publication','Publication date','Publishing venue','Work type','Radar check status','DOI','Source URL'];
const regionalRows=regionalLeads.map(r=>[
  Number(r.focus_score||0), String(r.focus_issue||''), String(r.focus_region||''),
  String(r.focus_group||''), String(r.aboutness_status||''),
  String(r.geographic_evidence||''), String(r.future_ri_question||''),
  String(r.temporal_lens||''), String(r.title||''), String(r.date||''),
  String(r.source||''), String(r.publication_type||''),
  String(r.radar_check_status||'indexed_lead_not_verified'), String(r.doi||''),
  String(r.url||'')
]);
// Concise investigative roll-up: one entry per observed Radar-topic × place pair.
// All provisional columns are labeled as bibliographic leads rather than facts.
// Unlike counts by publisher headquarters, neither the venue string nor source
// nationality can populate a region. A topic/place with one source is still a
// legitimate possibility, but the thin evidence is made visible.
const possibilities=new Map();
function possibility(topic,place,area){
  const key=topic+'\u0000'+place;
  if(!possibilities.has(key))possibilities.set(key,{
    topic,place,area,ids:new Set(),venues:new Set(),verified:[],best:null});
  return possibilities.get(key);
}
for(const row of regionalLeads){
  if(!row.focus_region||!row.focus_issue||row.focus_group==='EU / UK')continue;
  const item=possibility(String(row.focus_issue),String(row.focus_region),String(row.focus_group||''));
  const id=String(row.doi||row.url||row.candidate_id||'');
  if(id)item.ids.add(id);
  if(row.source)item.venues.add(String(row.source).toLocaleLowerCase());
  const better=!item.best||Number(row.focus_score||0)>Number(item.best.focus_score||0);
  if(better)item.best=row;
}
for(const result of globalVerified){
  if(!result.focus_region||!result.focus_issue||result.focus_group==='EU / UK')continue;
  const item=possibility(String(result.focus_issue),String(result.focus_region),String(result.focus_group||''));
  item.verified.push(result);
}
const possibilityHeaders=[
  'Main Radar topic','Place actually studied','World area','Evidence status',
  'Verified global Deep Scans','Indexed publication leads','Different publishing venues',
  'Observed signal / source excerpt (provisional until reviewed)',
  'Why this place COULD matter to R&I futures','Main uncertainty / caveat',
  'Further investigation question','Example source URL'];
const possibilityRows=Array.from(possibilities.values()).sort((a,b)=>
  b.verified.length-a.verified.length||b.venues.size-a.venues.size||
  b.ids.size-a.ids.size||a.topic.localeCompare(b.topic)||a.place.localeCompare(b.place))
  .map(item=>{
    const v=item.verified[0],lead=item.best;
    return [item.topic,item.place,item.area,
      item.verified.length?'Some verified, others may remain provisional':'Indexed lead / NOT verified',
      item.verified.length,item.ids.size,item.venues.size,
      String(v?.aboutness?.verified_excerpt||lead?.geographic_evidence||''),
      String(v?.futures?.why_could_matter||lead?.future_ri_question||''),
      String(v?.futures?.uncertainty||'Source validity and future significance not yet assessed by global Deep Scan.'),
      String(v?.futures?.research_question||lead?.future_ri_question||''),
      String(v?.source_verification?.primary_url||lead?.url||'')];
  });
const globalHeaders=['Radar topic','Substantive geography','World area','Title','Evidence date','Publisher','Source integrity','Independent review of aboutness','Observed or possible','Mechanism','Why it COULD matter for R&I futures','Uncertainties / alternatives','Further research question','Primary evidence URL','Publication DOI','Reviewed at'];
const globalRows=globalVerified.map(r=>[
  String(r.focus_issue||''),String(r.focus_region||''),String(r.focus_group||''),
  String(r.title||''),String(r.date||''),String(r.source||''),
  String(r.source_verification?.source_integrity||''),String(r.aboutness?.basis||''),
  String(r.futures?.classification||''),String(r.futures?.mechanism||''),
  String(r.futures?.why_could_matter||''),String(r.futures?.uncertainty||''),
  String(r.futures?.research_question||''),String(r.source_verification?.primary_url||''),
  String(r.url||''),String(r.verified_at||'')
]);
const questionsHeaders=['Main Radar topic','Place genuinely studied','Area','Aboutness evidence','Possible R&I futures question (NOT verified)','Review status','Original publication','Source URL'];
const questionsRows=regionalLeads.filter(r=>r.focus_region&&r.future_ri_question).map(r=>[
  String(r.focus_issue||''),String(r.focus_region||''),String(r.focus_group||''),
  String(r.geographic_evidence||''),String(r.future_ri_question||''),
  String(r.aboutness_status||''),String(r.title||''),String(r.url||'')
]);
const specs=[
  ['Global topic–place signals',possibilityHeaders,possibilityRows,[32,29,24,33,22,24,25,76,84,70,80,60]],
  ['Global verified futures',globalHeaders,globalRows,[32,24,23,56,16,36,27,78,24,66,80,65,75,60,50,25]],
  ['Radar verified backfill',headers,toRows(verified),widths],
  ['Radar admission review',headers,toRows(admissionReview),widths],
  ['Radar awaiting Deep Scan',headers,toRows(awaiting),widths],
  ['Focus coverage',['Dimension','Requested country / issue / stakeholder','Verified','Admission review','Awaiting Deep Scan'],coverage,[26,55,16,18,20]],
  ['Read me',['Field','Notes'],notes,[26,110]],
  ['Coverage audit',['Metric','Count / value'],diagnostics,[56,25]],
  ['R&I futures questions',questionsHeaders,questionsRows,[34,27,23,75,85,32,62,60]],
  ['Regional publication leads',regionalHeaders,regionalRows,[14,36,29,25,32,67,85,32,59,16,37,20,27,34,56]],
];
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const sheetType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml';
const sheetRel='http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet';
const files={
 '[Content_Types].xml':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>${specs.map((_,i)=>`<Override PartName="/xl/worksheets/sheet${i+1}.xml" ContentType="${sheetType}"/>`).join('')}<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>`,
 '_rels/.rels':'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
 'xl/workbook.xml':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>${specs.map(([n],i)=>`<sheet name="${esc(n)}" sheetId="${i+1}" r:id="rId${i+1}"/>`).join('')}</sheets></workbook>`,
 'xl/_rels/workbook.xml.rels':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${specs.map((_,i)=>`<Relationship Id="rId${i+1}" Type="${sheetRel}" Target="worksheets/sheet${i+1}.xml"/>`).join('')}<Relationship Id="rId${specs.length+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`,
 'xl/styles.xml':'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="10"/><name val="Arial"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Arial"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF193B40"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'
};
for(let i=0;i<specs.length;i++)files[`xl/worksheets/sheet${i+1}.xml`]=Workbook.sheetXml(specs[i][1],specs[i][2],specs[i][3]);
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,Buffer.from(Workbook.zip(files)));
console.log(`Wrote ${output}: ${verified.length} Deep Scan verified + retained, ${admissionReview.length} admission review, ${awaiting.length} Deep Scan unfinished. Coverage rows=${coverage.length}`);
