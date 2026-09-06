(function(g){
'use strict';

const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
const words=v=>clean(v).split(/\s+/).filter(Boolean);

// Surface pages use plain language. Specialist terms remain available in Glossary/Stuff,
// but common opaque abbreviations are expanded before a sentence is shown to readers.
function expandSurfaceTerms(v){
  let s=clean(v);
  const replacements=[
    [/\bHPC\b/g,'high-performance computing'],
    [/\bFP10\b/g,'the next EU research framework programme'],
    [/\bMFF\b/g,'the EU long-term budget'],
    [/\bMSCA\b/g,'Marie Skłodowska-Curie Actions'],
    [/\bFDI\b/g,'foreign direct investment'],
    [/\bTRLs?\b/g,'technology readiness levels'],
    [/\bLLMs?\b/g,'large language models'],
    [/\bGPUs?\b/g,'graphics processors'],
    [/\bSMEs?\b/g,'small and medium-sized firms'],
    [/\bR&D\b/g,'research and development'],
    [/\bIP\b/g,'intellectual property'],
    [/\bJRC\b/g,'Joint Research Centre'],
    [/\bERC\b/g,'European Research Council'],
    [/\bEIC\b/g,'European Innovation Council'],
    [/\bEIB\b/g,'European Investment Bank']
  ];
  for(const [re,to] of replacements)s=s.replace(re,to);
  s=s.replace(/\bR&I\b/g,'research and innovation');
  return clean(s);
}

function removeEllipsis(v){
  return clean(v)
    .replace(/\s*(?:\.{3,}|…)+\s*$/g,'')
    .replace(/(?:\.{3,}|…)/g,', ')
    .replace(/\s+,/g,',')
    .replace(/,\s*,+/g,',')
    .replace(/\s+/g,' ')
    .trim();
}

const TRAILING=/^(?:and|or|but|because|while|which|that|to|for|of|with|in|on|at|from|across|through|by|as|the|a|an)$/i;
function limit(v,n){
  const s=removeEllipsis(expandSurfaceTerms(v));
  const a=words(s);
  if(a.length<=n)return a.join(' ');

  // Prefer a complete first sentence/clause when it fits the budget.
  const clauses=s.split(/(?<=[.!?])\s+|;\s+|\s+[—–]\s+|,\s+(?=(?:but|while|whereas|although|because)\b)/i)
    .map(clean).filter(Boolean);
  if(clauses.length && words(clauses[0]).length>=5 && words(clauses[0]).length<=n){
    return clauses[0].replace(/[,:;—–-]+$/,'').trim();
  }

  let out=a.slice(0,n);
  while(out.length>5 && TRAILING.test(out[out.length-1]))out.pop();
  let clipped=out.join(' ').replace(/[,:;—–-]+$/,'').trim();
  if(clipped && !/[.!?)]$/.test(clipped))clipped+='.';
  return clipped;
}


function fieldText(v){
  if(Array.isArray(v))return v.map(clean).filter(Boolean).join(' ');
  return clean(v);
}

function whatFor(x){
  const nTitle=clean(x?.title||x?.headline||'').toLowerCase();
  const specialWhat=[
    [/targeted consultation.*dual-use regulation|evaluation of the dual-use regulation/, 'The Commission is consulting on the evaluation of EU dual-use export-control rules.'],
    [/management plan 2026.*research and innovation/, 'The Commission’s 2026 plan sets research and innovation priorities, actions and delivery targets.'],
    [/eic fund investment guidelines|eic accelerator.*step scaleup/, 'The Commission updated investment guidelines for EU deep-tech and scale-up financing.'],
    [/erc frontier research.*competitiveness/, 'European Research Council frontier research is presented as a source of European competitiveness.'],
    [/funding for democracy and governance/, 'EU funding supports research on democracy, governance and institutional resilience.'],
    [/european network of defence-related regions|endr/, 'A European network links defence-related regions around industrial and innovation cooperation.'],
    [/startup and scaleup strategy|startup.*scaleup/, 'The EU strategy targets better conditions for startups and scaleups to grow in Europe.'],
    [/hashtags and handshakes|diplomacy in the age of platforms/, 'The study examines how digital platforms reshape diplomatic practice and influence.'],
    [/environmental biotechnology/, 'The EU frames environmental biotechnology as a route to sustainable industrial competitiveness.'],
    [/fragmented europe.*china|china as a technology and innovation power/, 'The report compares how 22 European countries respond to China’s technology and innovation power.'],
    [/italy:.*china.*technological power|biopharma.*automotive.*telecom/, 'The analysis identifies Chinese technological pressure across Italian biopharma, automotive and telecommunications.'],
    [/study on cloud and ai development/, 'The study maps European cloud and artificial-intelligence capabilities, dependencies and development conditions.'],
    [/jrc security research and innovation campus/, 'The Joint Research Centre campus brings security research, testing and innovation capabilities together.'],
    [/uk research and innovation strategy 2026 to 2031/, 'The UK strategy sets priorities for research funding, capability building and innovation through 2031.']
  ];
  for(const [re,text] of specialWhat){if(re.test(nTitle))return text;}
  const candidates=[
    x?.core_message,x?.what,
    g.RadarInsights?.whatForEuRiGeo?.(x),g.RadarInsights?.signalWhat?.(x),g.RadarInsights?.pointFor?.(x),
    x?.headline,x?.title
  ].map(clean).filter(Boolean);
  const badStart=/^(?:source focus:|its eu relevance|this includes:|as ‘open|as 'open|and\b|or\b|but\b|because\b|with\b|using\b|based on\b)/i;
  const predicate=/\b(?:is|are|was|were|has|have|had|can|could|will|would|may|might|must|should|targets?|builds?|expands?|reduces?|increases?|limits?|restricts?|shifts?|changes?|remains?|depends?|drives?|links?|uses?|proposes?|shows?|finds?|creates?|supports?|funds?|strengthens?|weakens?|requires?|faces?|puts?|makes?|becomes?|reconfigures?|affects?|determines?|gives?|provides?|opens?|closes?|moves?|concentrates?|exposes?)\b/i;
  const scored=candidates.map((v,i)=>{
    const w=words(v).length;
    let score=100-i*4;
    if(w>=5&&w<=20)score+=25; else if(w<=28)score+=10; else score-=12;
    if(predicate.test(v))score+=16; else score-=14;
    if(badStart.test(v))score-=40;
    if(/^[A-Z0-9\s:–—-]{28,}$/.test(v))score-=25;
    if(/\.\s+[A-Z]/.test(v)&&w>20)score-=5;
    return {v,score};
  }).sort((a,b)=>b.score-a.score);
  return scored[0]?.v||'';
}
function whyFor(x){
  const raw=clean(g.RadarInsights?.whyFor?.(x)||g.RadarInsights?.whyYouShouldCare?.(x)||x?.why_it_matters||x?.relevance_note||x?.signal_note||'');
  const n=clean([x?.title,x?.headline,x?.core_message,fieldText(x?.ri_evidence),fieldText(x?.geo_evidence),fieldText(x?.eu_evidence)].join(' ')).toLowerCase();
  const knownGeneric=/^(?:European (?:research and innovation|R&I) is affected through|AI policy, capital and infrastructure affect|Partnership choices determine|Funding and eligibility rules determine|Infrastructure and data rules determine|Dual-use policy redirects|Industrial-policy choices affect|Technology-sovereignty choices trade off|EU–China technology ties matter because|Research-security rules change|Quantum capability affects|Rules and standards determine|Foresight methods matter because|Researcher mobility changes|Intellectual property rules affect|Economic-security policy matters because|Compute access determines|Digital and cyber choices affect)/i.test(raw);
  const consequence=/\b(?:affect|change|determin|shape|enable|allow|restrict|limit|constrain|reduce|increase|strengthen|weaken|expos|depend|access|control|capabil|capacity|fund|finance|scale|retain|collabor|cooperat|security|autonom|resilien|risk|pressure|transform|redirect|sustain|protect|narrow|widen|open|close)\w*/i.test(raw);
  const generic=knownGeneric||!raw||!consequence;

  // Very common current records get a direct consequence tied to the actual source topic.
  if(/targeted consultation.*dual-use regulation|evaluation of the dual-use regulation/.test(n))
    return 'The review can change export-control conditions for dual-use research, technology transfer and international partners.';
  if(/management plan 2026.*research and innovation/.test(n))
    return 'The plan steers Commission research priorities, budgets and delivery choices that build European capability.';
  if(/eic fund investment guidelines|eic accelerator|step scaleup/.test(n))
    return 'Investment rules affect which deep-tech firms can receive EU equity and scale their technology in Europe.';
  if(/erc frontier research.*competitiveness/.test(n))
    return 'Frontier-research funding affects whether Europe retains scientific leadership and converts discoveries into strategic capability.';
  if(/funding for democracy and governance/.test(n))
    return 'Funding choices shape European research capacity on democratic resilience, governance and foreign interference.';
  if(/european network of defence-related regions|endr/.test(n))
    return 'Regional defence networks can connect research, firms and public funding around dual-use industrial capability.';
  if(/startup and scaleup strategy|startup.*scaleup/.test(n))
    return 'Scale-up conditions affect whether European technology firms retain capital, talent and intellectual property in Europe.';
  if(/hashtags and handshakes|diplomacy in the age of platforms/.test(n))
    return 'Platform power can shift diplomatic influence toward technology firms and reshape channels for science diplomacy.';
  if(/environmental biotechnology/.test(n))
    return 'Biotechnology deployment can reduce resource dependencies while strengthening European industrial and research capability.';
  if(/fragmented europe.*china|china as a technology and innovation power/.test(n))
    return 'Divergent national approaches to China can weaken Europe’s coordination on technology security, investment and research ties.';
  if(/italy:.*china.*technological power|biopharma.*automotive.*telecom/.test(n))
    return 'Chinese technological strength exposes sector-specific European dependencies in biopharma, automotive and telecommunications.';

  if(!generic)return raw;

  // When the source-level WHY has fallen back to a reusable topic sentence, rebuild it
  // from the record's own object + mechanism. This keeps surface cards specific without
  // moving technical classifier language out of Glossary/Stuff.
  if(/eurocc|castiel|national competence cent/.test(n))
    return 'National competence centres give researchers local access to European supercomputers, training and specialist support.';
  if(/research.?security|security research|knowledge.?security|foreign interference|espionage/.test(n))
    return 'Security safeguards can change research partners, data access and knowledge transfer across European institutions.';
  if(/semiconductor|microchip|\bchip\b|foundry|lithograph|wafer/.test(n)){
    if(/supply|depend|chokepoint|shortage|export control|restriction/.test(n)) return 'Chip dependencies can constrain European research and production when external suppliers or governments restrict access.';
    if(/fund|invest|state aid|industrial policy|production|fab/.test(n)) return 'Chip investment determines how much semiconductor research and production capability Europe can build and retain.';
    return 'Semiconductor capability affects Europe’s access to critical hardware, production capacity and strategic technology know-how.';
  }
  if(/artificial intelligence|\bai\b|foundation model|large language model/.test(n)){
    if(/compute|supercomput|cloud|gpu|infrastructure/.test(n)) return 'Computing access determines which European teams can train advanced artificial-intelligence systems without relying on foreign providers.';
    if(/regulat|govern|standard|liability|rule/.test(n)) return 'Artificial-intelligence rules shape which models, data and deployment practices European researchers and firms can use.';
    if(/fund|capital|invest|scale|venture/.test(n)) return 'Finance determines whether European artificial-intelligence firms can scale capability at home rather than depend on foreign capital.';
    return 'Artificial-intelligence capability affects Europe’s ability to develop, govern and retain strategically important digital technology.';
  }
  if(/quantum/.test(n))
    return 'Quantum capability determines whether European researchers can access frontier facilities, expertise and strategic technology without external dependence.';
  if(/critical raw material|critical mineral|rare earth|lithium|cobalt|gallium|germanium|battery/.test(n))
    return 'Strategic-material access determines whether European research and manufacturing can scale without disruption from concentrated external suppliers.';
  if(/researcher|scientist|talent|brain drain|mobility|skills shortage|workforce|doctoral|postdoctoral/.test(n))
    return 'Research talent determines whether European laboratories and firms can build, operate and retain specialised scientific capability.';
  if(/horizon europe|framework programme|research funding|grant|funding programme|european research council|european innovation council/.test(n))
    return 'Funding choices determine which European research capabilities, infrastructures and international partnerships can be sustained.';
  if(/science diplomacy|research collaboration|scientific collaboration|international cooperation|collaborat|partnership|co-?author/.test(n))
    return 'Partnership choices change which expertise, facilities and research networks remain accessible to European teams.';
  if(/biotech|biopharma|pharma|life science|health research/.test(n))
    return 'Biotechnology and health capability affect European access to research data, production capacity and strategic supply chains.';
  if(/china|chinese/.test(n)&&/technology|innovation|research|science|telecom|automotive/.test(n))
    return 'Technology ties with China can create European dependencies while narrowing room for research and industrial cooperation.';
  if(/standard|regulat|directive|governance|export control|screening/.test(n))
    return 'Rules and standards change the conditions under which European technologies can be developed, shared and deployed.';
  if(/infrastructure|data space|interoperab|facility|testbed|pilot line/.test(n))
    return 'Shared infrastructure determines which European researchers can access scarce facilities, data and specialised technical capability.';
  if(/research assessment|open research information|open science|research data|data sharing|scientometric|bibliometric|composite indicator|topic model/.test(n))
    return 'Research-information and assessment rules shape incentives, transparency and Europe’s ability to evaluate its own research system.';
  if(/european research area|university alliance|widening countr|research participation|fifth freedom|research minister/.test(n))
    return 'Research-system coordination changes how funding, people and institutional capacity connect across Europe.';
  if(/spin-?off|entrepreneur|regional innovation|innovation system|innovation ecosystem|absorptive capacity|growth model/.test(n))
    return 'Conversion conditions affect whether European research becomes firms, regional capability, productivity and durable economic capacity.';
  if(/rare disease|clinical research|patient data|health research/.test(n))
    return 'Research-network and data access determine whether European health studies can reach sufficient scale and translate into capability.';
  if(/earth observation|satellite|space research/.test(n))
    return 'Shared Earth-observation capability can reduce fragmented access to data and strengthen European research infrastructure.';
  if(/industrial|manufactur|commerciali|scale.?up|startup|venture capital|procurement/.test(n))
    return 'Commercialisation conditions determine whether European research becomes domestic production, growing firms and strategic capability.';
  if(/economic security|de-risk|derisk|strategic autonom|sovereign|dependen/.test(n))
    return 'Economic-security choices trade external access against European control over strategic research and technology capability.';
  if(/dual.?use|defen[cs]e|military/.test(n))
    return 'Dual-use rules can redirect research funding and tighten access, publication, partnership and export conditions.';
  return raw;
}
function radarPair(x,opt={}){
  const w=limit(opt.what||whatFor(x),20);
  const y=limit(opt.why||whyFor(x)||'It changes a documented capability, dependency, rule or partnership in European research and innovation.',20);
  return {what:w,why:y};
}
function matrixPair(x,opt={}){
  const w=limit(opt.what||g.SovereigntyFrontier?.shortBullet?.(x)||whatFor(x),12);
  const y=limit(opt.why||x?.why||whyFor(x)||'It changes European control or capability in this part of the research and innovation system.',15);
  return {what:w,why:y,line:`${w} — ${y}`};
}
function pagePair(what,why,whatWords=20,whyWords=20){
  return {what:limit(what,whatWords),why:limit(why,whyWords)};
}
function wordCount(v){return words(v).length}

g.RadarReaderStyle={clean,limit,wordCount,whatFor,whyFor,radarPair,matrixPair,pagePair,expandSurfaceTerms,removeEllipsis};
})(globalThis);
