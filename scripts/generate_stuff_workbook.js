#!/usr/bin/env node
'use strict';
// Keep two distinct, continuously regenerated Excel snapshots:
// main_radar_stuff.xlsx = Main Radar only (every available current field)
// source_merit_ranking.xlsx = Main Radar + every Historical scanner finding.
// The second name is retained for trajectory-engine and existing link compatibility.
// Deep Scan/admission/correction details are joined without deleting historical rows.
const fs=require('fs');
const path=require('path');
const Merit=require('../source_merit.js');
const Workbook=require('../stuff/workbook.js');
const ROOT=path.resolve(__dirname,'..');
const active=path.join(ROOT,'radar_active.json');
const raw=path.join(ROOT,'radar.json');
const input=fs.existsSync(active)?active:raw;
const data=JSON.parse(fs.readFileSync(input,'utf8'));
if(input===raw&&Number(data?.active_corpus?.decision_counts?.drop||0)+Number(data?.active_corpus?.decision_counts?.drop_unverifiable||0)+Number(data?.active_corpus?.decision_counts?.duplicate||0)>0){throw new Error('Refusing to generate active workbook from raw radar.json while inactive decisions exist');}
const readJson=(rel,fallback={})=>{const p=path.join(ROOT,rel);return fs.existsSync(p)?JSON.parse(fs.readFileSync(p,'utf8')):fallback;};
const extras={
  historical:readJson('historical/historical.json',{items:[]}),
  reader:readJson('reader_text.json',{records:{}}),
  admission:readJson('admission_state.json',{records:{}}),
  corrections:readJson('record_corrections.json',{records:{}})
};
const ranked=Workbook.buildRows(data,Merit).length;
const mainOut=path.join(ROOT,'stuff','main_radar_stuff.xlsx');
fs.writeFileSync(mainOut,Buffer.from(Workbook.buildXlsx(data,Merit,extras,{includeHistorical:false})));
console.log(`Wrote ${mainOut} from ${path.basename(input)}: ${ranked} active ranked records, Main Radar only`);

const bothOut=path.join(ROOT,'stuff','source_merit_ranking.xlsx');
fs.writeFileSync(bothOut,Buffer.from(Workbook.buildXlsx(data,Merit,extras,{includeHistorical:true})));
const hist=Workbook.buildHistoricalTable(extras.historical,extras.reader,extras.admission,extras.corrections);
console.log(`Wrote ${bothOut} from ${path.basename(input)}: ${ranked} active ranked records + ${hist.total} historical scanner findings (${hist.deepScannedCount} Deep Scanned, ${hist.authoritativeCount} authoritative historical)`);
