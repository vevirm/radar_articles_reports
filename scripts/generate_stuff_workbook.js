#!/usr/bin/env node
'use strict';
// Generate the repository snapshot from the authoritative active corpus.
// radar_active.json is generated from raw radar.json + Deep Scan/admission sidecars.
// Falling back to raw radar.json is allowed only before the first V2 active build.
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
const out=path.join(ROOT,'stuff','source_merit_ranking.xlsx');
const bytes=Workbook.buildXlsx(data,Merit);
fs.writeFileSync(out,Buffer.from(bytes));
console.log(`Wrote ${out} from ${path.basename(input)}: ${Workbook.buildRows(data,Merit).length} active ranked records`);
