#!/usr/bin/env node
'use strict';
const fs=require('fs');
const path=require('path');
const root=path.resolve(__dirname,'..');
const phenomena=require(path.join(root,'phenomena','phenomena.js'));
const continuity=require(path.join(root,'phenomena','continuity.js'));
function read(rel){return JSON.parse(fs.readFileSync(path.join(root,rel),'utf8'))}
const data=read('radar.json'),fileHistory=read('historical/historical.json'),config=read('historical/config.json');
const history=phenomena.mergeHistories(fileHistory,data.historical_archive);
const report=continuity.build(data,history,config,phenomena.phenomena);
if(process.argv.includes('--json')){
  const arg=process.argv[process.argv.indexOf('--json')+1];
  const out=JSON.stringify(report,null,2);
  if(arg&&arg!=='-'){fs.writeFileSync(arg,out+'\n');console.log(`Wrote ${arg}`)}else console.log(out);
  process.exit(0);
}
console.log(`Pattern watch: ${report.findings.length} strong · ${report.candidates.length} candidates · ${report.meta.darkCurrent} current records outside named buckets`);
for(const [i,x] of report.findings.entries())console.log(`${i+1}. [${x.shape}] ${x.title} — score ${x.score}`);
if(report.candidates.length){
  console.log('\nCandidates');
  for(const [i,x] of report.candidates.entries())console.log(`${i+1}. [${x.shape}] ${x.title} — score ${x.score}`);
}
const q=report.meta.dateQuality;
console.log(`\nHistorical date quality: precision on ${q.known}/${q.total}; Jan-1 dates ${q.jan1}/${q.total}; return/dormancy detectors ${report.meta.returnDetectorsEnabled?'enabled':'withheld'}.`);
