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
  ['Purpose','Relevance-only evidence subset for the specified country/region, emerging-issue and stakeholder foresight priorities.'],
  ['Created at (UTC)',String(data.generated_at||'')],
  ['Verified / retained rows',verified.length],
  ['Admission-review rows (Deep Scan completed)',admissionReview.length],
  ['Awaiting Deep Scan / source recovery rows',awaiting.length],
  ['Verified rule','Deep Scan work status=verified + authoritative reader identity verification + final admission KEEP.'],
  ['Admission review rule','Deep Scan identity verified, but final Admission decision is REVIEW. Requires human admission decision, not another normal Deep Scan package.'],
  ['Awaiting Deep Scan rule','Deep Scan not complete; items may already be assigned to existing packages or held for hands-on verification. Check DEEP_SCAN_STATUS.md before creating jobs.'],
  ['Prior workbook correction','The earlier 125-review export was invalid: lowercasing case-sensitive Deep Scan URL keys hid stored KEEP and DROP decisions. Exact-key joins restore those decisions.'],
  ['Source and scope','Main Radar A/B/C (including inactive), Historical, and all stored Deep Scan/Reader decisions. Original provenance is shown per row; dropped/unverifiable/duplicate decisions are excluded.'],
  ['Relevance rule','Named emerging issue or substantive country/region R&I-policy focus in original title or leading Reader evidence. Stakeholder names alone never qualify.'],
  ['Score rule','A relevance-sorting signal, NOT an evidence-quality score or policy forecast.'],
  ['Normal Radar output','Focused discovery candidates are sent through the existing priority-candidate adapter and all ordinary source, A/B/C, duplicate and admission gates.'],
  ['Backfill','No internet calls or new Deep Scan. Examines existing stored evidence from all four source pools.'],
  ['Limit','Keyword matching of titles and existing reader evidence can miss indirect references and can include some imperfect matches. Read original linked source before interpretation.'],
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
const specs=[
  ['Verified and retained',headers,toRows(verified),widths],
  ['Admission review',headers,toRows(admissionReview),widths],
  ['Awaiting Deep Scan',headers,toRows(awaiting),widths],
  ['Focus coverage',['Dimension','Requested country / issue / stakeholder','Verified','Admission review','Awaiting Deep Scan'],coverage,[26,55,16,18,20]],
  ['Read me',['Field','Notes'],notes,[26,110]],
  ['Coverage audit',['Metric','Count / value'],diagnostics,[56,25]],
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
