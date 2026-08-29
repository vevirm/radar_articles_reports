#!/usr/bin/env node
/* V17.13.26 regression tests for the 4x4 Matrix semantic contract. */
const path=require('path');
const ROOT=path.resolve(__dirname,'..');
global.RadarInsights=require(path.join(ROOT,'briefing','insights.js'));
const Frontier=require(path.join(ROOT,'frontier','frontier.js'));

function classify(text,title='Synthetic EU R&I evidence'){
  const rec={
    title,authors:'Regression fixture',source:'Regression fixture',date:'2026-08-20',
    link:'https://example.invalid/'+Math.random(),type:'institutional report',strand:'A',
    eu_relevance:'direct',summary:text,core_message:text,
    relevance_note:'Direct European R&I geopolitical mechanism supported by source.'
  };
  const out=Frontier.buildFrontier({strand_a:[rec],strand_b:[],strand_c:[]},{now:new Date('2026-08-29T10:40:00+03:00')});
  return out.signals[0] ? `${out.signals[0].row.id}-${out.signals[0].column.id}` : null;
}

const fixtures=[
  ['knowledge-A','The EU retained European researchers through new research-career grants, strengthening the European research workforce and scientific capacity.'],
  ['knowledge-A','Researcher mobility within Europe increased after cross-border career barriers were removed, strengthening the European Research Area research workforce and scientific capacity.'],
  ['knowledge-B','EU knowledge-security screening protects sensitive research but delays international collaboration and researcher mobility.'],
  ['knowledge-C','International researchers and third-country doctoral graduates who stay in the EU strengthen research capacity and innovation, while Europe depends on continued attraction and retention of this external talent.'],
  ['knowledge-D','European universities are losing researchers abroad and the brain drain is reducing scientific capacity and competitiveness.'],
  ['knowledge-D','European laboratories lost access to an international research network after foreign partners suspended collaboration, reducing scientific capability and expertise.'],

  ['infrastructure-A','The EU built shared European compute infrastructure and diversified chip suppliers, reducing reliance on a single foreign vendor while expanding research capacity.'],
  ['infrastructure-A','European researchers adopted EU-sourced substitutes for imported advanced materials with comparable performance, reducing import dependence while preserving research capability.'],
  ['infrastructure-B','Europe is localising sovereign cloud and compute infrastructure to increase control, but duplication and higher cost slow research deployment.'],
  ['infrastructure-C','European AI laboratories rely on US cloud GPU infrastructure for frontier compute access that enables research scale, leaving Europe dependent on foreign vendors.'],
  ['infrastructure-C','European laboratories rely on a US scientific data repository whose datasets enable frontier biomedical research, leaving continued research capability dependent on foreign access.'],
  ['infrastructure-D','US export controls cut European access to advanced GPUs; the foreign supplier dependence causes research delays and loss of AI compute capacity.'],

  ['conversion-A','European deep-tech scale-ups received growth capital and procurement contracts to expand manufacturing in Europe and increase industrial capacity.'],
  ['conversion-A','European deep-tech firms expanded sales across the EU single market and scaled production in Europe, increasing European value capture and industrial capacity.'],
  ['conversion-B','EU local-content requirements keep strategic manufacturing in Europe but raise costs and fragment the market, leaving technology firms subscale.'],
  ['conversion-C','European startups rely on US venture capital and the US market to scale and commercialise, so growth improves while dependence on foreign capital and markets remains.'],
  ['conversion-D','European startups are relocating R&D and production abroad after a funding gap, moving value capture and industrial capability out of Europe.'],
  ['conversion-D','A foreign acquisition moved a European technology firm’s R&D and intellectual property abroad, reducing European industrial and innovation capability.'],

  ['rules-A','The EU adopted a common technology standard and mutual-recognition framework that reduces fragmentation and improves market access for European innovation.'],
  ['rules-A','The EU and member states implemented mutual recognition of technology approvals, reducing fragmentation and enabling European innovators to enter the single market faster.'],
  ['rules-B','EU research-security and export-control rules protect sensitive technology but add licensing burden and slow research collaboration.'],
  ['rules-C','European firms comply with US export licences to preserve access to advanced technology and markets, improving access while operating on outside rules.'],
  ['rules-C','European research teams comply with US platform licensing terms to maintain access to a scientific computing service that enables their work, leaving access governed by outside rules.'],
  ['rules-D','Fragmented national approval rules delay European technology projects and weaken both EU control and innovation performance.'],

  [null,'A new radio astronomy facility in Africa will improve African scientific capacity and international collaboration.'],
  [null,'The United States is leading electric vehicle supply chains through AI and fintech innovation; the European Union is mentioned as a competitor.'],
  [null,'European technology firms received investment and foreign partners were present in the market.'],
  [null,'EU policymakers discussed risks and vulnerabilities in technology without identifying any restriction, dependency or capability consequence.'],
  [null,'A suspected spy once worked in a European research organisation; the incident may lead policymakers to consider screening in the future.'],
  [null,'European startups face a funding gap and may seek foreign investors, but the source does not show that foreign capital currently enables scaling.'],
  [null,'Europe depends on American digital firms and could face political pressure, but the source does not establish that a foreign rule or licence preserves research or technology access.']
];

let failed=0;
for(const [expected,text] of fixtures){
  const got=classify(text);
  const ok=got===expected;
  console.log(`${ok?'PASS':'FAIL'} ${String(expected).padEnd(16)} -> ${got}`);
  if(!ok){ console.log('  '+text); failed++; }
}
console.log(`\n${fixtures.length-failed}/${fixtures.length} Matrix semantic fixtures passed.`);
process.exitCode=failed?1:0;
