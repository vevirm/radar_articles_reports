/* v21.7 — trend/counter-trend tug-of-war from the retained Radar corpus.
   Publication rule is intentionally simple:
   - a side needs at least three current records from at least two independent sources;
   - a pair therefore needs current evidence on both sides before it is published;
   - historical material older than the six-month boundary may add context,
     but it cannot make a current trend qualify.
   Weighting remains deliberately playful: stronger and more independent evidence
   pulls harder, repeated publication from the same source pulls less. */
(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory(require('../reader_rank.js'));
  else root.RadarTrends=factory(root.RadarReaderRank);
})(typeof globalThis!=='undefined'?globalThis:this,function(ReaderRank){
  'use strict';
  const clean=v=>String(v||'').replace(/\s+/g,' ').trim();
  const low=v=>clean(v).toLowerCase();
  const rx=v=>v instanceof RegExp?v:new RegExp(String(v),'i');
  const dateValue=v=>{const n=Date.parse(v||'');return Number.isFinite(n)?n:0};
  const quality=x=>Math.max(0,Math.min(100,Number(ReaderRank?.scoreFor?.(x))||0));
  function rowText(x){return low([x.title,x.headline,x.what,x.reader_point,x.core_message,x.summary,x.relevance_note,x.why_it_matters,x.bridge_sentence,(x.geo_evidence||[]).join(' '),(x.ri_evidence||[]).join(' '),(x.topics||[]).join(' '),(x.topic_labels||[]).join(' '),x.source].join(' '))}
  function source(x){return clean(x?.source||x?.journal||x?.institution||x?.venue||'')}
  function historyText(x){return low([x.title,x.reader_point,x.source].join(' '))}
  const HISTORY_EU=/\b(?:eu|europe|european|horizon|eurohpc|erc|eic|jrc|commission|member states)\b/i;
  const ACTOR=/\b(?:European Commission|European Innovation Council|European Research Council|European Investment Bank|EuroHPC|Council of the European Union|European Parliament|Joint Research Centre|JRC Publications Repository|ERA Portal|Marie Skłodowska-Curie Actions|Research Council of|Ministry|Agency for|Government of|Fusion for Energy)\b/i;
  const EU_POLICY_ACTOR=/\b(?:European Commission|European Innovation Council|European Research Council|EuroHPC|Council of the European Union|Joint Research Centre|JRC Publications Repository|ERA Portal|Marie Skłodowska-Curie Actions)\b/i;
  function reportingRole(x){return ACTOR.test(source(x))?'actor':'observer'}

  function currentCorpus(data){
    const out=[],seen=new Set();
    for(const [key,prefix] of [['strand_a','A'],['strand_c','C'],['strategic_pathways','P']]){
      const xs=Array.isArray(data?.[key])?data[key]:[];
      xs.forEach((x,i)=>{if(!x||typeof x!=='object')return;const k=clean(x.link)||low(x.title||x.headline||x.what);if(k&&seen.has(k))return;if(k)seen.add(k);out.push({...x,_row:`${prefix}${String(i+1).padStart(3,'0')}`,_strand:prefix,_historical:false})});
    }
    return out;
  }
  function historicalCorpus(history){
    const xs=Array.isArray(history?.items)?history.items:[];
    const cutoff=Date.parse(history?.cutoff_exclusive||history?.date_to||'');
    const seen=new Set(),out=[];
    xs.forEach((x,i)=>{
      if(!x||typeof x!=='object')return;
      const d=dateValue(x.date);
      if(Number.isFinite(cutoff)&&cutoff>0&&d>=cutoff)return;
      const k=clean(x.url||x.link)||low(x.title||x.reader_point);
      if(k&&seen.has(k))return;if(k)seen.add(k);
      out.push({...x,link:x.link||x.url||'',_row:`H${String(i+1).padStart(3,'0')}`,_strand:'H',_historical:true});
    });
    return out;
  }
  function matches(x,spec){
    const t=rowText(x);
    if(spec?.all&&spec.all.some(p=>!rx(p).test(t)))return false;
    if(spec?.any&&spec.any.length&&!spec.any.some(p=>rx(p).test(t)))return false;
    if(spec?.none&&spec.none.some(p=>rx(p).test(t)))return false;
    return true;
  }
  function hostileWitness(x,role){
    if(!role.hostileWitness)return false;
    if(role.hostileSource&&!rx(role.hostileSource).test(source(x)))return false;
    return EU_POLICY_ACTOR.test(source(x));
  }
  function candidateScore(x,role){
    let n=quality(x)*100;
    const t=rowText(x);
    for(const p of role.spec?.all||[])if(rx(p).test(t))n+=36;
    for(const p of role.spec?.any||[])if(rx(p).test(t))n+=14;
    if(role.spec?.preferSource&&rx(role.spec.preferSource).test(source(x)))n+=180;
    if(role.spec?.preferTitle&&rx(role.spec.preferTitle).test(clean(x.title||x.headline)))n+=220;
    if(hostileWitness(x,role))n+=300;
    if(x._strand==='C')n+=35; // a current observed change is useful in a trend tug-of-war
    n+=dateValue(x.date)/1e12;
    return n;
  }
  function pick(rows,role,usedRows){
    const candidates=rows.filter(x=>!usedRows.has(x._row)&&matches(x,role.spec||{})).sort((a,b)=>candidateScore(b,role)-candidateScore(a,role));
    const x=candidates[0]||null;if(x)usedRows.add(x._row);return x;
  }
  function claimWeight(x,role,sourceUse){
    const q=quality(x),rr=reportingRole(x),type=role.claimType||'diagnosis';
    let mult=1;
    if(type==='action')mult*=rr==='actor'?1.08:0.97;
    else if(type==='effect'||type==='outcome')mult*=rr==='actor'?0.72:1.08;
    else mult*=rr==='actor'?0.88:1.04;
    const hostile=hostileWitness(x,role);if(hostile)mult*=1.18;
    const src=source(x).toLowerCase(),count=sourceUse.get(src)||0;
    if(count===1)mult*=0.86;else if(count>=2)mult*=0.68;
    sourceUse.set(src,count+1);
    return {weight:q*mult,quality:q,reporting:rr,hostile};
  }
  function historyScore(x){
    const merit=Math.max(0,Math.min(100,Number(x?.source_merit_score)||0));
    return merit*10+dateValue(x.date)/1e12;
  }
  function pickHistory(rows,side,currentEvidence){
    const patterns=side.historyAny||[];
    if(!patterns.length)return [];
    const currentKeys=new Set(currentEvidence.map(e=>clean(e.row.link||e.row.url)||low(e.row.title)));
    const picked=[],seenSources=new Set();
    const candidates=rows.filter(x=>HISTORY_EU.test(historyText(x))&&patterns.some(p=>rx(p).test(historyText(x)))).sort((a,b)=>historyScore(b)-historyScore(a));
    for(const x of candidates){
      const k=clean(x.link||x.url)||low(x.title);if(k&&currentKeys.has(k))continue;
      const s=source(x).toLowerCase();if(s&&seenSources.has(s))continue;
      picked.push(x);if(s)seenSources.add(s);if(picked.length>=2)break;
    }
    return picked;
  }
  function sideEvidence(currentRows,historicalRows,side){
    const used=new Set(),sourceUse=new Map(),evidence=[];
    for(const role of side.roles){
      const row=pick(currentRows,role,used);if(!row)continue;
      const w=claimWeight(row,role,sourceUse);
      evidence.push({role:role.label,row,...w,claimType:role.claimType||'diagnosis'});
    }
    const sources=new Set(evidence.map(e=>source(e.row).toLowerCase()).filter(Boolean));
    const movements=evidence.filter(e=>e.claimType==='action'||e.claimType==='effect'||e.claimType==='outcome'||e.row._strand==='C').length;
    const avg=evidence.length?evidence.reduce((a,e)=>a+e.quality,0)/evidence.length:0;
    const observers=evidence.filter(e=>e.reporting==='observer').length;
    const hostile=evidence.filter(e=>e.hostile).length;
    const sum=evidence.reduce((a,e)=>a+e.weight,0);
    // Stronger evidence pulls harder; different sources add a small bonus; repetition is already discounted above.
    const diversityBonus=Math.min(18,sources.size*3)+Math.min(8,observers*2)+hostile*4;
    evidence.sort((a,b)=>(b.hostile?1:0)-(a.hostile?1:0)||b.quality-a.quality);
    const history=pickHistory(historicalRows,side,evidence);
    return {
      evidence,history,raw:sum+diversityBonus,averageQuality:Math.round(avg),
      bestQuality:evidence.length?Math.max(...evidence.map(e=>e.quality)):0,
      sourceCount:sources.size,movementCount:movements,observerCount:observers,hostileCount:hostile
    };
  }
  function sideQualifies(side){
    return side.evidence.length>=3&&side.sourceCount>=2&&side.bestQuality>=85&&side.averageQuality>=72;
  }

  const PAIRS=[
    {
      id:'build_vs_rent',
      left:{title:'Building our own',plain:'Europe is putting more money and shared infrastructure into its own strategic technology capacity.',why:'More European-controlled capacity reduces exposure to outside suppliers and chokepoints.',historyAny:[/europe.*research infrastructure/,/europe.*supercomput/,/europe.*compute capacity/,/technology sovereignty/,/eurohpc/],roles:[
        {label:'AI compute investment',claimType:'action',spec:{any:[/ai gigafactor/],preferSource:/European Commission/}},
        {label:'Supercomputing capacity',claimType:'action',spec:{any:[/supercomput/,/eurohpc.*competence centre/,/federation platform/],preferSource:/EuroHPC/}},
        {label:'Quantum capacity',claimType:'action',spec:{any:[/quantum.*call/,/quantum-testing infrastructure/,/quantum experimental pilot lines/,/new quantum computer/],preferSource:/EuroHPC/}},
        {label:'Shared AI access',claimType:'action',spec:{any:[/resource for ai science in europe/,/raise.*ai science/]}},
        {label:'Sovereignty policy',claimType:'action',spec:{any:[/strengthening europe.*tech sovereignty/,/supercomputers.*europe.*technological sovereignty/,/quantum.*technological sovereignty/]}}
      ]},
      right:{title:'Still renting theirs',plain:'Europe still relies on outside cloud, advanced chips and technology layers that cannot be replaced quickly.',why:'Outside control can still shape European research access, cost and strategic freedom.',historyAny:[/dependenc/,/semiconductor/,/technology gap/,/global rivalry/,/supply chain/],roles:[
        {label:'Cloud and AI dependence',claimType:'effect',hostileWitness:true,hostileSource:/European Commission/,spec:{any:[/cloud and ai development/,/dependence on non-european suppliers/,/limited and geographically concentrated/],preferTitle:/Cloud and AI Development/}},
        {label:'Chip dependence',claimType:'diagnosis',spec:{any:[/semiconductor.*depend/,/supply chain dependencies.*china.*taiwan.*united states/,/geopolitics of ai chips/]}},
        {label:'Capability gap',claimType:'diagnosis',spec:{any:[/structural limitations.*european union.*ai/,/catching up.*strategic autonomy/,/technology gap/,/competitiveness.*ai model/]}},
        {label:'External technology pressure',claimType:'effect',spec:{any:[/chinese technology.*power/,/technology dependence.*eu/,/deeper us tech reliance/,/non-european supplier/]}}
      ]},
      flip:'The balance changes if European capacity clearly replaces outside use, or if new dependencies deepen faster than Europe builds.'
    },
    {
      id:'money_in_vs_capital_gap',
      left:{title:'Money coming in',plain:'Europe is putting more public money and scale-up support behind research-intensive companies.',why:'More growth finance can keep valuable firms, jobs and know-how in Europe.',historyAny:[/scale-up/,/venture capital/,/innovation funding/,/startup/,/eic/],roles:[
        {label:'Scale-up strategy',claimType:'action',spec:{any:[/eu startup and scaleup strategy/],preferSource:/European Commission/}},
        {label:'Scale-up investment rules',claimType:'action',spec:{any:[/step scaleup/,/eic fund investment guidelines/],preferSource:/European Innovation Council/}},
        {label:'Public venture role',claimType:'action',spec:{any:[/government roles in venture capital/,/entrepreneurial state.*venture capital/]}},
        {label:'Deep-tech support',claimType:'action',spec:{any:[/deep tech.*funding/,/scale up tech leaders/,/european scale-ups/]}}
      ]},
      right:{title:'Still short at the top',plain:'Europe still shows weak growth finance and commercialisation gaps around successful technology firms.',why:'If firms cannot scale, public research support does not become durable European capability.',historyAny:[/venture capital gap/,/scale-up gap/,/foreign investor/,/startup relocation/,/capital market/],roles:[
        {label:'Growth-model gap',claimType:'diagnosis',spec:{any:[/eu.*need for a new growth model/,/growth model.*europe/],preferSource:/FIIA|Finnish Institute/}},
        {label:'Venture-capital weakness',claimType:'diagnosis',spec:{any:[/venture capital.*european countries/,/structural limitations.*venture/,/scale-up gap/,/late-stage.*capital/]}},
        {label:'Scaling friction',claimType:'effect',spec:{any:[/structural limitations and competitiveness challenges/,/innovation ecosystems and entrepreneurial venture capital/]}},
        {label:'Tech champion pressure',claimType:'diagnosis',spec:{any:[/tech champions/,/commercialisation gap/,/competitiveness challenges.*european union/]}}
      ]},
      flip:'It shifts toward scale if firms find enough growth money in Europe; toward the gap if strong firms still struggle to expand.'
    },
    {
      id:'open_vs_secure',
      left:{title:'Open the doors',plain:'Europe is widening open research, shared data and access to research infrastructure.',why:'Wider access can increase collaboration, reuse and the reach of European research.',historyAny:[/open science/,/open research/,/open access.*research infrastructure/,/research data/],roles:[
        {label:'Open science push',claimType:'action',spec:{any:[/stronger action on open science/,/open science as a pillar/],preferSource:/ALLEA/}},
        {label:'Open infrastructure',claimType:'action',spec:{any:[/open access to jrc research infrastructures/,/european research infrastructures/],preferSource:/European Commission|Joint Research Centre/}},
        {label:'Shared research data',claimType:'action',spec:{any:[/data sharing.*open science/,/federated.*data access/,/public sharing of research data/]}},
        {label:'Open research information',claimType:'action',spec:{any:[/barcelona declaration on open research information/,/open research information/]}}
      ]},
      right:{title:'Lock the sensitive rooms',plain:'Research-security and dual-use rules are adding more conditions around sensitive knowledge and collaboration.',why:'Controls can reduce leakage, but they also add friction to legitimate research.',historyAny:[/research security/,/knowledge security/,/dual-use/,/foreign interference/],roles:[
        {label:'Research-security rules',claimType:'action',spec:{any:[/national knowledge security guidelines/,/research security by roundtable/,/system leadership.*research security/]}},
        {label:'Dual-use controls',claimType:'action',spec:{any:[/evaluation of the dual-use regulation/,/dual-use regulation/],preferSource:/European Commission/}},
        {label:'Securitised cooperation',claimType:'effect',spec:{any:[/securitisation of knowledge/,/partial securitisation of science policy/,/research cooperation.*de-risking/]}},
        {label:'Foreign-interference concern',claimType:'diagnosis',spec:{any:[/counterintelligence battleground.*universit/,/foreign interference.*security-relevant research/,/espionage.*foreign interference/,/foreign interference.*knowledge security/]}}
      ]},
      flip:'It moves toward openness if security rules stay narrow in practice; toward closure if ordinary collaboration starts being restricted.'
    },
    {
      id:'collaborate_vs_derisk',
      left:{title:'Add partners',plain:'Europe is widening formal science partnerships, research links and access beyond its borders.',why:'More partners can expand talent, capability and influence beyond Europe’s domestic base.',historyAny:[/science diplomacy/,/international cooperation/,/horizon association/,/research collaboration/],roles:[
        {label:'Science diplomacy',claimType:'action',spec:{any:[/framework for science diplomacy/,/first ever eu framework for science diplomacy/],preferSource:/Council of the European Union|European Commission/}},
        {label:'Horizon association',claimType:'action',spec:{any:[/japan officially joins horizon europe/,/eu and egypt strengthen research and innovation partnership.*horizon europe association/],preferSource:/European Commission|ERA Portal/}},
        {label:'Cross-border research',claimType:'action',spec:{any:[/fifth freedom/,/international cooperation in research and innovation/,/innovation beyond europe.*borders/]}},
        {label:'Partnership strategy',claimType:'action',spec:{any:[/autonomy through partnerships/,/shared gains, secure links/,/researchbridge/]}}
      ]},
      right:{title:'Check the guest list',plain:'The same system is becoming more selective where security and technology dependence are judged important.',why:'Selective access may protect capability, but it can fragment networks Europe still needs.',historyAny:[/de-risk.*research/,/research security/,/china.*research collaboration/,/restriction.*collaboration/,/knowledge security/],roles:[
        {label:'Knowledge-security controls',claimType:'action',spec:{any:[/national knowledge security guidelines/,/knowledge security/]}},
        {label:'EU-China de-risking',claimType:'effect',spec:{any:[/eu.?china research cooperation.*de-risking/,/securitisation of knowledge.*eu science policy/]}},
        {label:'Partner restrictions',claimType:'effect',spec:{any:[/restrictions.*international research collaboration/,/proposed restrictions on international research collaboration/,/science knows no borders/]}},
        {label:'Dual-use safeguards',claimType:'action',spec:{any:[/safeguards.*dual-use research/,/dual-use regulation/]}}
      ]},
      flip:'It moves toward partnership if controls stay limited to sensitive fields; toward selectivity if restrictions spread into ordinary research.'
    },
    {
      id:'talent_pull_vs_talent_friction',
      left:{title:'Come to Europe',plain:'Europe is treating research talent as strategic capacity and is building programmes to attract and retain people.',why:'Talent gains help turn new funding and infrastructure into actual research capability.',historyAny:[/talent/,/research career/,/doctoral workforce/,/researcher mobility/],roles:[
        {label:'Choose Europe',claimType:'action',spec:{any:[/choose europe for science/],preferSource:/Marie Skłodowska-Curie|European Commission/}},
        {label:'Attract and retain',claimType:'action',spec:{any:[/attract and retain research talent/,/research talent.*strategic advantage/]}},
        {label:'Researcher mobility',claimType:'action',spec:{any:[/the fifth freedom in the european research area/,/ecas report: insights from researchers on the fifth freedom/]}},
        {label:'Skills pipeline',claimType:'action',spec:{any:[/doctoral networks/],preferTitle:/Doctoral Networks/}}
      ]},
      right:{title:'Please do not leave',plain:'Career insecurity, uneven opportunities and skills gaps still make it hard to keep scarce researchers.',why:'New facilities do little if the people needed to use them leave or cannot be hired.',historyAny:[/brain drain/,/precar/,/research career/,/skills shortage/,/talent shortage/],roles:[
        {label:'Brain drain',claimType:'effect',spec:{any:[/research careers, brain drain and policy lessons/,/which job offers may mitigate brain drain/]}},
        {label:'Career insecurity',claimType:'effect',spec:{any:[/precarity/,/temporary contracts/],preferTitle:/Choose Europe : Research Careers/}},
        {label:'Skills gap',claimType:'diagnosis',spec:{any:[/skills shortage/,/skills gap/,/human-capability.*gap/,/researcher shortage/]}},
        {label:'Uneven opportunity',claimType:'diagnosis',spec:{any:[/underrepresented european countries/,/widening country.*barrier/,/regional.*human capital/]}}
      ]},
      flip:'It moves toward attraction if strategic fields show net inflows and better careers; toward friction if departures and shortages persist.'
    },
    {
      id:'infrastructure_vs_bottlenecks',
      left:{title:'Build the machine',plain:'Europe is expanding shared laboratories, computing facilities and other research infrastructure.',why:'More capacity gives researchers places to test, compute and scale new ideas.',historyAny:[/europe.*research infrastructure/,/europe.*supercomput/,/europe.*compute capacity/,/open access.*infrastructure/,/eurohpc/],roles:[
        {label:'Research infrastructure',claimType:'action',spec:{any:[/^european research infrastructures/,/horizon europe: research infrastructures/]}},
        {label:'AI and compute',claimType:'action',spec:{any:[/ai gigafactor/,/supercomputer/,/resource for ai science in europe/]}},
        {label:'Quantum facilities',claimType:'action',spec:{any:[/quantum-testing infrastructure/,/quantum experimental pilot lines/,/new quantum computer/]}},
        {label:'Open facility access',claimType:'action',spec:{any:[/open access to jrc research infrastructures/,/federated.*infrastructure/]}}
      ]},
      right:{title:'Find a free slot',plain:'Access, concentration and bottlenecks still limit how easily researchers can use scarce facilities.',why:'A facility only adds capability when researchers can actually reach and use it.',historyAny:[/bottleneck/,/limited.*capacity/,/access.*research infrastructure/,/infrastructure.*gap/,/research infrastructure.*access/],roles:[
        {label:'Bottleneck resources',claimType:'effect',spec:{any:[/research infrastructures as bottleneck resources/],preferSource:/EPJ Research Infrastructures/}},
        {label:'Concentrated capacity',claimType:'effect',spec:{any:[/limited and geographically concentrated/,/cloud and ai computing capacity.*limited/],preferSource:/European Commission/}},
        {label:'Participation barriers',claimType:'effect',spec:{any:[/barriers and policy priorities.*underrepresented european countries/,/navigating eu research participation.*widening country/]}}
      ]},
      flip:'It moves toward capacity if access broadens as fast as construction; toward bottlenecks if demand and regional gaps grow faster.'
    },
    {
      id:'one_europe_vs_many_rulebooks',
      left:{title:'One Europe on paper',plain:'Europe is building common frameworks, shared programmes and cross-border rules for research.',why:'Common approaches can make collaboration and access more predictable across Europe.',historyAny:[/european research area/,/eu framework/,/fifth freedom/,/common.*research/,/science diplomacy/],roles:[
        {label:'EU science framework',claimType:'action',spec:{any:[/eu framework for science diplomacy/,/framework for science diplomacy/],preferSource:/Council of the European Union|European Commission/}},
        {label:'European Research Area',claimType:'action',spec:{any:[/^european research area$/, /european research area.*policy/],preferSource:/European Commission/}},
        {label:'Fifth Freedom',claimType:'action',spec:{any:[/fifth freedom in the european research area/,/fifth freedom.*research/]}},
        {label:'Shared infrastructure',claimType:'action',spec:{any:[/european research infrastructures/,/federat.*european.*research/]}}
      ]},
      right:{title:'Twenty-seven ways to do it',plain:'National approaches still diverge on research security, access and strategic technology policy.',why:'Different national rules can turn one European research space into several practical systems.',historyAny:[/fragment/,/national.*research security/,/scandinavian/,/germany.*research security/,/ireland.*research security/],roles:[
        {label:'Fragmented technology response',claimType:'effect',spec:{any:[/fragmented europe/],preferSource:/MERICS/}},
        {label:'Different security approaches',claimType:'effect',spec:{any:[/comparing scandinavian approaches to research security/]}},
        {label:'National securitisation',claimType:'effect',spec:{any:[/germany.*partial securitisation/,/research security by roundtable.*germany/]}},
        {label:'National security model',claimType:'action',spec:{any:[/research security in ireland/,/national knowledge security guidelines/]}},
        {label:'Regional inequality',claimType:'diagnosis',spec:{any:[/widening country.*barrier/,/core and peripher/,/underrepresented european countries/]}}
      ]},
      flip:'It moves toward one system if national practice converges; toward fragmentation if the same researcher or project gets different answers by country.'
    },
    {
      id:'dual_use_vs_open_research',
      left:{title:'Research gets a helmet',plain:'More European research funding and policy is opening toward defence and dual-use technology.',why:'That can connect research to security needs and new sources of funding.',historyAny:[/dual-use/,/defence innovation/,/research security/,/civil-military/],roles:[
        {label:'EIC opens to dual use',claimType:'action',spec:{any:[/european innovation council opens to defence and dual-use technologies/],preferSource:/European Innovation Council/}},
        {label:'Funding expands',claimType:'action',spec:{any:[/research and innovation funding expands to defence and dual-use/]}},
        {label:'Dual-use regulation review',claimType:'action',spec:{any:[/evaluation of the dual-use regulation/],preferSource:/European Commission/}},
        {label:'Defence regions',claimType:'action',spec:{any:[/european network of defence-related regions/]}}
      ]},
      right:{title:'Research keeps its lab coat',plain:'Universities and research groups are also pushing to keep European research open and research-led.',why:'Those safeguards can limit how far security priorities reshape ordinary research.',historyAny:[/academic freedom/,/open science/,/research-led/,/science knows no borders/],roles:[
        {label:'Keep FP10 research-led',claimType:'action',spec:{any:[/keep fp10 open and research-led/]}},
        {label:'Safeguards for dual use',claimType:'action',spec:{any:[/urges safeguards as fp10 opens to dual-use/,/requests safeguards for dual-use research/]}},
        {label:'Science without borders',claimType:'action',spec:{any:[/science knows no borders/],preferSource:/ALLEA/}},
        {label:'Open science push',claimType:'action',spec:{any:[/stronger action on open science/,/open science as a pillar/]}}
      ]},
      flip:'It shifts toward security if dual-use becomes routine across programmes; toward openness if safeguards keep most research outside that logic.'
    },
    {
      id:'rules_vs_race',
      left:{title:'Write the rulebook',plain:'Europe keeps building rules, standards and safeguards around strategic technologies and research.',why:'Clear rules can protect trust and shape markets before technologies become harder to govern.',historyAny:[/standard/,/regulation/,/governance/,/research security/,/rules-standards/],roles:[
        {label:'AI rules',claimType:'action',spec:{any:[/ahead of the final agreement on the ai act/,/ai governance and geopolitics/]}},
        {label:'Quantum standards',claimType:'action',spec:{any:[/standards for quantum technologies/],preferSource:/EuroHPC/}},
        {label:'Dual-use rules',claimType:'action',spec:{any:[/evaluation of the dual-use regulation/],preferSource:/European Commission/}},
        {label:'Research-security guidance',claimType:'action',spec:{any:[/national knowledge security guidelines/,/research security by roundtable/]}}
      ]},
      right:{title:'Run before the ink dries',plain:'The same evidence base keeps warning that Europe must close technology and growth gaps faster.',why:'Slow delivery can leave good rules governing markets and capabilities built elsewhere.',historyAny:[/competitiveness gap/,/technology gap/,/scale-up/,/catching up/,/growth model/],roles:[
        {label:'Growth pressure',claimType:'diagnosis',spec:{any:[/eu.*need for a new growth model/],preferSource:/FIIA|Finnish Institute/}},
        {label:'Defence catch-up',claimType:'action',spec:{any:[/catching up: europe.*strategic autonomy in the defence industry/]}},
        {label:'AI competitiveness gap',claimType:'diagnosis',spec:{any:[/structural limitations and competitiveness challenges.*european union.*ai/,/strategic competitiveness.*eu.*united states.*ai/]}},
        {label:'Scale-up push',claimType:'action',spec:{any:[/eu startup and scaleup strategy/,/step scaleup/],preferSource:/European Commission|European Innovation Council/}}
      ]},
      flip:'It moves toward rules if standards become an advantage; toward the race if capability gaps widen despite an expanding rulebook.'
    }
  ];

  function build(data,history){
    const currentRows=currentCorpus(data),historicalRows=historicalCorpus(history),out=[];
    for(const pair of PAIRS){
      const left=sideEvidence(currentRows,historicalRows,pair.left),right=sideEvidence(currentRows,historicalRows,pair.right);
      if(!sideQualifies(left)||!sideQualifies(right))continue;
      if(left.evidence.length+right.evidence.length<6)continue;
      const total=left.raw+right.raw;if(total<=0)continue;
      let leftPull=Math.round(100*left.raw/total);leftPull=Math.max(18,Math.min(82,leftPull));
      const rightPull=100-leftPull;
      // The score is deliberately a playful balance meter, not a probability estimate.
      const support=Math.round((left.averageQuality+right.averageQuality)/2+Math.min(10,left.sourceCount+right.sourceCount)+Math.min(4,left.history.length+right.history.length));
      out.push({...pair,left:{...pair.left,...left,pull:leftPull},right:{...pair.right,...right,pull:rightPull},support,currentEvidenceCount:left.evidence.length+right.evidence.length,historicalContextCount:left.history.length+right.history.length});
    }
    return out.sort((a,b)=>b.support-a.support||Math.abs(50-a.left.pull)-Math.abs(50-b.left.pull)||a.id.localeCompare(b.id));
  }
  function stats(data,history){
    return {current:currentCorpus(data).length,historical:historicalCorpus(history).length};
  }
  return {build,stats,pairs:PAIRS,reportingRole,quality,rowText,sideQualifies};
});
