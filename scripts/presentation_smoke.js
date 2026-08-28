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

for (const rel of ['glossary/glossary.js','briefing/insights.js','frontier/frontier.js','priorities/priorities.js']) {
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
  globalThis.RadarInsights = require(path.join(root, 'briefing/insights.js'));
  globalThis.SovereigntyFrontier = require(path.join(root, 'frontier/frontier.js'));
  const RadarPriorities = require(path.join(root, 'priorities/priorities.js'));

  const insights = RadarInsights.buildResearchInsights(radar);
  const weak = RadarInsights.buildSignals(radar);
  const frontier = SovereigntyFrontier.buildFrontier(radar);
  const priorities = RadarPriorities.buildPriorityView(radar);

  if (!Array.isArray(insights) || !insights.length) fail('Evidence browser produced no research groups');
  else ok(`Evidence browser builds ${insights.length} research groups`);
  if (!Array.isArray(weak)) fail('Weak signals builder did not return an array');
  else ok(`Evidence browser builds ${weak.length} weak signals`);
  if (!frontier || !Array.isArray(frontier.signals) || !frontier.signals.length) fail('Matrix produced no qualifying frontier signals');
  else ok(`Matrix builds ${frontier.signals.length} qualifying signals`);
  if (!priorities || !Array.isArray(priorities.risks) || !Array.isArray(priorities.opportunities)) fail('Risks & opportunities builder failed');
  else ok(`Risks & opportunities builds ${priorities.opportunities.length} opportunities / ${priorities.risks.length} risks`);
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
const prioritiesHtml = read('priorities/index.html');
if (!/quick-terms/.test(readHtml) || !/RadarGlossary/.test(readHtml)) fail('Read at least this is missing contextual glossary help');
else ok('Read at least this includes contextual glossary help');
if (!/quickGlossary/.test(prioritiesHtml) || !/RadarGlossary/.test(prioritiesHtml)) fail('Risks & opportunities is missing contextual glossary help');
else ok('Risks & opportunities includes contextual glossary help');

const frontierHtml = read('frontier/index.html');
const claim = frontierHtml.match(/function\s+claimText\s*\([^)]*\)\s*\{[^}]*\}/);
if (!claim) fail('frontier/index.html claimText() not found');
else if (/\bclean\s*\(/.test(claim[0])) fail('frontier claimText() still calls undefined page-level clean()');
else ok('frontier claimText() is self-contained');

if (process.exitCode) process.exit(process.exitCode);
console.log('Presentation smoke check complete. No network discovery or scanner was run.');
