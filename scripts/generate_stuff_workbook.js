#!/usr/bin/env node
'use strict';
// Generate the repository snapshot of the Stuff audit workbook from radar.json.
// The public Stuff page can also generate the same workbook live in-browser, so
// a legacy GitHub workflow that persists only radar.json cannot make the Excel stale.
const fs=require('fs');
const path=require('path');
const Merit=require('../source_merit.js');
const Workbook=require('../stuff/workbook.js');
const ROOT=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(ROOT,'radar.json'),'utf8'));
const out=path.join(ROOT,'stuff','source_merit_ranking.xlsx');
const bytes=Workbook.buildXlsx(data,Merit);
fs.writeFileSync(out,Buffer.from(bytes));
console.log(`Wrote ${out}: ${Workbook.buildRows(data,Merit).length} ranked records`);
