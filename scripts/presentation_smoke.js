#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
function fail(message) { console.error(`FAIL: ${message}`); process.exitCode = 1; }
function ok(message) { console.log(`PASS: ${message}`); }
function read(rel) { return fs.readFileSync(path.join(root, rel), 'utf8'); }

let radar;
try {
  radar = JSON.parse(read('radar.json'));
  ok(`radar.json parses (${(radar.strand_a||[]).length} A / ${(radar.strand_b||[]).length} B / ${(radar.strand_c||[]).length} C)`);
} catch (e) {
  fail(`radar.json is not valid JSON: ${e.message}`);
  process.exit(1);
}

for (const rel of ['source_merit.js','glossary/glossary.js','briefing/insights.js','read/issues.js','frontier/frontier.js','priorities/priorities.js']) {
  try {
    new vm.Script(read(rel), {filename: rel});
    ok(`${rel} syntax`);
  } catch (e) {
    fail(`${rel} syntax: ${e.message}`);
  }
}


try {
  const ctx = {globalThis:{}};
  vm.createContext(ctx);
  vm.runInContext(read('glossary/glossary.js'), ctx, {filename:'glossary/glossary.js'});
  const G = ctx.globalThis.RadarGlossary;
  if (!G || !Array.isArray(G.terms) || G.terms.length !== 50) fail('shared glossary did not expose 50 terms');
  else if (!G.lookup('Dual-use')) fail('shared glossary is missing Dual-use');
  else if (!/glossary-inline/.test(G.annotate('dual-use research security', 2))) fail('shared glossary annotation helper failed');
  else ok('shared glossary exposes 50 terms and inline annotation');
} catch (e) {
  fail(`shared glossary runtime: ${e.stack || e.message}`);
}

try {
  globalThis.RadarSourceMerit = require(path.join(root, 'source_merit.js'));
  globalThis.RadarInsights = require(path.join(root, 'briefing/insights.js'));
  globalThis.SovereigntyFrontier = require(path.join(root, 'frontier/frontier.js'));
  const RadarPriorities = require(path.join(root, 'priorities/priorities.js'));
  vm.runInThisContext(read('read/issues.js'), {filename:'read/issues.js'});

  const sampleMerit=RadarSourceMerit.forItem((radar.strand_a||[])[0]||{});
  if(!sampleMerit||!Number.isFinite(sampleMerit.score)||!sampleMerit.label) fail('source merit helper did not score a radar item');
  else ok(`source merit helper scores radar items (${sampleMerit.label} ${sampleMerit.score}/100)`);

  const insights = RadarInsights.buildResearchInsights(radar);
  const weak = RadarInsights.buildSignals(radar);
  const frontier = SovereigntyFrontier.buildFrontier(radar);
  const priorities = RadarPriorities.buildPriorityView(radar);
  const liveIssues = globalThis.RadarIssues?.build?.([...(radar.strand_a||[]),...(radar.frontier_evidence||[]),...(radar.strand_c||[])], {minIssues:5,maxIssues:9}) || [];

  if (!Array.isArray(liveIssues) || liveIssues.length < 4) fail('Read at least this produced no usable live issue set');
  else ok(`Read at least this builds ${liveIssues.length} live issue maps from current material`);
  if (!Array.isArray(insights) || !insights.length) fail('Evidence browser produced no research groups');
  else ok(`Evidence browser builds ${insights.length} research groups`);
  if (!Array.isArray(weak)) fail('Weak signals builder did not return an array');
  else ok(`Evidence browser builds ${weak.length} weak signals`);
  if (!frontier || !Array.isArray(frontier.signals) || !frontier.signals.length) fail('Matrix produced no qualifying frontier signals');
  else if(!frontier.signals.some(x=>x.sourceMerit&&Number.isFinite(x.sourceMerit.score))) fail('Matrix signals are missing source-merit weights');
  else ok(`Matrix builds ${frontier.signals.length} qualifying signals with evidence weights`);
  if (!priorities || !Array.isArray(priorities.risks) || !Array.isArray(priorities.opportunities)) fail('Risks & opportunities builder failed');
  else ok(`Risks & opportunities builds ${priorities.opportunities.length} opportunities / ${priorities.risks.length} risks`);

  const genericRadar=/^(?:AI capacity and dependence are becoming strategic issues|Geopolitical competition is pushing Europe|Geopolitical rivalry is changing Europe|Foresight methods can test emerging strategic change|Research-security pressure is changing how Europe|Semiconductor dependence is constraining Europe|Security competition is pulling more European R&I|Geopolitical pressure is reshaping EU research funding|Strategic dependencies are changing Europe|Digital and cyber policy is shaping Europe|Quantum capability is becoming part of Europe|Critical raw materials shape Europe)/i;
  const metaRadar=/Its EU relevance is classified|Consult the linked publication|source text available at scan time|admitted to Strand|exact .*page reviewed|collected from researchers/i;
  const badClaims=[];
  for(const x of [...(radar.strand_a||[]),...(radar.strand_b||[]),...(radar.strand_c||[])]){
    const claim=RadarInsights.whatForEuRiGeo(x)||'';
    if(genericRadar.test(claim)||metaRadar.test(claim)||/This may affect European access, investment or capability-building/i.test(claim)) badClaims.push([x.title||x.headline,claim]);
  }
  if(badClaims.length) fail(`Main Radar still emits ${badClaims.length} generic/meta claim(s): ${JSON.stringify(badClaims.slice(0,3))}`);
  else ok('Main Radar emits source-specific claims without reusable topic slogans or scanner metadata');
} catch (e) {
  fail(`reader-layer runtime build: ${e.stack || e.message}`);
}

for (const rel of ['index.html','read/index.html','briefing/index.html','frontier/index.html','frontier/quick/index.html','priorities/index.html','literature/index.html','stuff/index.html','glossary/index.html']) {
  const html = read(rel);
  const inline = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)].map(m => m[1]);
  try {
    for (const body of inline) new vm.Script(body, {filename: `${rel} inline script`});
    ok(`${rel} inline JavaScript syntax`);
  } catch (e) {
    fail(`${rel} inline JavaScript syntax: ${e.message}`);
  }
}

const readHtml = read('read/index.html');
const mainHtml = read('index.html');
const quickHtml = read('frontier/quick/index.html');
const prioritiesHtml = read('priorities/index.html');
const fullMatrixHtml = read('frontier/index.html');
const stuffHtml = read('stuff/index.html');

if (/const\s+ISSUE_MAP\s*=/.test(readHtml)) fail('Read at least this still contains a fixed ISSUE_MAP');
else if (!/RadarIssues\.build/.test(readHtml)) fail('Read at least this is not using the live issue builder');
else ok('Read at least this has no fixed public issue map');
if (!/read\/issues\.js/.test(mainHtml) || !/renderCurrentIssues/.test(mainHtml)) fail('Landing page is not using live issue discovery');
else ok('Landing page uses the same live issue discovery');

// V17.13.28 language hierarchy retained: Read < Matrix/Priorities < Main Radar < technical workbook.
if (/RadarGlossary|quick-terms/.test(readHtml)) fail('Read at least this still depends on contextual glossary help');
else if (!/readText/.test(readHtml)) fail('Read at least this is missing the simplest-language boundary');
else ok('Read at least this uses the simplest-language boundary');
if (!/matrixText/.test(quickHtml)) fail('Matrix short is missing the simple-analytical language boundary');
else ok('Matrix short uses simple analytical wording');
if (/RadarGlossary|quickGlossary/.test(prioritiesHtml)) fail('Risks & opportunities still depends on contextual glossary help');
else if (!/matrixText/.test(prioritiesHtml)) fail('Risks & opportunities is missing the simple-analytical language boundary');
else ok('Risks & opportunities uses simple analytical wording');
if (!/matrixText/.test(fullMatrixHtml) || !/Technical placement check/.test(fullMatrixHtml)) fail('Full Matrix does not separate simple wording from technical diagnostics');
else ok('Full Matrix keeps technical placement diagnostics secondary');
if (!/radarText/.test(mainHtml)) fail('Main Radar is missing the policy-technical wording boundary');
else ok('Main Radar keeps policy-technical wording');
if (!/Technical exports/.test(stuffHtml) || !/most technical|technical fields|technical evidence/i.test(stuffHtml)) fail('Stuff does not present Excel as the technical layer');
else ok('Stuff presents Excel as the technical evidence layer');

if (RadarInsights.fastReaderText('Frontier compute, research security, dual-use and procurement.') !== 'Top-end computing power, protecting sensitive research, usable for civilian and military purposes and buying.') fail('fastReaderText recurring-term rewrite failed');
else ok('fastReaderText recurring-term rewrite remains stable');
const languageSample='Strategic dependence on external research infrastructure can constrain European R&I autonomy.';
const readSample=RadarInsights.readText(languageSample);
const matrixSample=RadarInsights.matrixText(languageSample);
const radarSample=RadarInsights.radarText(languageSample);
if(!readSample || !matrixSample || !radarSample) fail('reader-language helpers did not return usable text');
else if(readSample===radarSample) fail('Read and Radar language boundaries collapse to the same wording');
else if(matrixSample===radarSample) fail('Matrix and Radar language boundaries collapse to the same wording');
else ok('Read, Matrix and Radar use distinct wording boundaries');

for(const rel of ['index.html','read/index.html','briefing/index.html','frontier/index.html','frontier/quick/index.html','priorities/index.html','literature/index.html','stuff/index.html']){
  const html=read(rel);
  if(!/source_merit\.js/.test(html)) fail(`${rel} is missing the shared source-merit layer`);
  else if(!/Source merit:|Source:|Top source|Strong source|Good source|Supporting source/.test(html)) fail(`${rel} does not surface source strength`);
  else ok(`${rel} surfaces source merit/source strength`);
}

const frontierHtml = read('frontier/index.html');
const claim = frontierHtml.match(/function\s+claimText\s*\([^)]*\)\s*\{[^}]*\}/);
if (!claim) fail('frontier/index.html claimText() not found');
else if (/\bclean\s*\(/.test(claim[0])) fail('frontier claimText() still calls undefined page-level clean()');
else ok('frontier claimText() is self-contained');

if (process.exitCode) process.exit(process.exitCode);
console.log('Presentation smoke check complete. No network discovery or scanner was run.');
