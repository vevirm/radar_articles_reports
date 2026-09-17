#!/usr/bin/env node
'use strict';
// Generate the repository snapshot from the authoritative active corpus plus the
// complete Historical scanner archive. Historical rows are never filtered out:
// Deep Scan/admission/correction sidecars are joined onto the matching archive row
// so the workbook evolves from "scanner finding" to "deep-scanned finding" without
// rewriting or deleting the original historical evidence.
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
const out=path.join(ROOT,'stuff','source_merit_ranking.xlsx');
const bytes=Workbook.buildXlsx(data,Merit,extras);
fs.writeFileSync(out,Buffer.from(bytes));
const hist=Workbook.buildHistoricalTable(extras.historical,extras.reader,extras.admission,extras.corrections);
console.log(`Wrote ${out} from ${path.basename(input)}: ${Workbook.buildRows(data,Merit).length} active ranked records + ${hist.total} historical scanner findings (${hist.deepScannedCount} Deep Scanned, ${hist.authoritativeCount} authoritative historical)`);
