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
  function historyText(x){return low([x.title,x.reader_title,x.reader_point,x.reader_what,x.reader_more,x.core_message,x.summary,x.relevance_note,x.source].join(' '))}
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
      const rw=Number(x.historical_reasoning_weight);
      if(Number.isFinite(rw)&&rw<=0)return;
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
    const trust=Number.isFinite(Number(x?.historical_reasoning_weight))?Math.max(0,Math.min(1,Number(x.historical_reasoning_weight))):0.35;
    // Historical context never qualifies the current trend, but Deep-Scan-kept
    // context should be chosen ahead of provisional/review material when both match.
    return trust*100000+merit*10+dateValue(x.date)/1e12;
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
      left:{title:'Europe is building more of its own capacity',plain:'Europe is putting more money and shared infrastructure into its own strategic technology capacity.',why:'More European-controlled capacity reduces exposure to outside suppliers and chokepoints.',historyAny:[/europe.*research infrastructure/,/europe.*supercomput/,/europe.*compute capacity/,/technology sovereignty/,/eurohpc/],roles:[
        {label:'AI compute investment',claimType:'action',spec:{any:[/ai gigafactor/],preferSource:/European Commission/}},
        {label:'Supercomputing capacity',claimType:'action',spec:{any:[/supercomput/,/eurohpc.*competence centre/,/federation platform/],preferSource:/EuroHPC/}},
        {label:'Quantum capacity',claimType:'action',spec:{any:[/quantum.*call/,/quantum-testing infrastructure/,/quantum experimental pilot lines/,/new quantum computer/],preferSource:/EuroHPC/}},
        {label:'Shared AI access',claimType:'action',spec:{any:[/resource for ai science in europe/,/raise.*ai science/]}},
        {label:'Sovereignty policy',claimType:'action',spec:{any:[/strengthening europe.*tech sovereignty/,/supercomputers.*europe.*technological sovereignty/,/quantum.*technological sovereignty/]}}
      ]},
      right:{title:'Europe still depends on foreign capacity',plain:'Europe still relies on outside cloud, advanced chips and technology layers that cannot be replaced quickly.',why:'Outside control can still shape European research access, cost and strategic freedom.',historyAny:[/dependenc/,/semiconductor/,/technology gap/,/global rivalry/,/supply chain/],roles:[
        {label:'Cloud and AI dependence',claimType:'effect',hostileWitness:true,hostileSource:/European Commission/,spec:{any:[/cloud and ai development/,/dependence on non-european suppliers/,/limited and geographically concentrated/],preferTitle:/Cloud and AI Development/}},
        {label:'Chip dependence',claimType:'diagnosis',spec:{any:[/semiconductor.*depend/,/supply chain dependencies.*china.*taiwan.*united states/,/geopolitics of ai chips/]}},
        {label:'Capability gap',claimType:'diagnosis',spec:{any:[/structural limitations.*european union.*ai/,/catching up.*strategic autonomy/,/technology gap/,/competitiveness.*ai model/]}},
        {label:'External technology pressure',claimType:'effect',spec:{any:[/chinese technology.*power/,/technology dependence.*eu/,/deeper us tech reliance/,/non-european supplier/]}}
      ]},
      flip:'The balance changes if European capacity clearly replaces outside use, or if new dependencies deepen faster than Europe builds.'
    },
    {
      id:'money_in_vs_capital_gap',
      left:{title:'Investment in European research is increasing',plain:'Europe is putting more public money and scale-up support behind research-intensive companies.',why:'More growth finance can keep valuable firms, jobs and know-how in Europe.',historyAny:[/scale-up/,/venture capital/,/innovation funding/,/startup/,/eic/],roles:[
        {label:'Scale-up strategy',claimType:'action',spec:{any:[/eu startup and scaleup strategy/],preferSource:/European Commission/}},
        {label:'Scale-up investment rules',claimType:'action',spec:{any:[/step scaleup/,/eic fund investment guidelines/],preferSource:/European Innovation Council/}},
        {label:'Public venture role',claimType:'action',spec:{any:[/government roles in venture capital/,/entrepreneurial state.*venture capital/]}},
        {label:'Deep-tech support',claimType:'action',spec:{any:[/deep tech.*funding/,/scale up tech leaders/,/european scale-ups/]}}
      ]},
      right:{title:'Funding gaps remain at the scale-up stage',plain:'Europe still shows weak growth finance and commercialisation gaps around successful technology firms.',why:'If firms cannot scale, public research support does not become durable European capability.',historyAny:[/venture capital gap/,/scale-up gap/,/foreign investor/,/startup relocation/,/capital market/],roles:[
        {label:'Growth-model gap',claimType:'diagnosis',spec:{any:[/eu.*need for a new growth model/,/growth model.*europe/],preferSource:/FIIA|Finnish Institute/}},
        {label:'Venture-capital weakness',claimType:'diagnosis',spec:{any:[/venture capital.*european countries/,/structural limitations.*venture/,/scale-up gap/,/late-stage.*capital/]}},
        {label:'Scaling friction',claimType:'effect',spec:{any:[/structural limitations and competitiveness challenges/,/innovation ecosystems and entrepreneurial venture capital/]}},
        {label:'Tech champion pressure',claimType:'diagnosis',spec:{any:[/tech champions/,/commercialisation gap/,/competitiveness challenges.*european union/]}}
      ]},
      flip:'It shifts toward scale if firms find enough growth money in Europe; toward the gap if strong firms still struggle to expand.'
    },
    {
      id:'open_vs_secure',
      left:{title:'Research collaboration is opening up',plain:'Europe is widening open research, shared data and access to research infrastructure.',why:'Wider access can increase collaboration, reuse and the reach of European research.',historyAny:[/open science/,/open research/,/open access.*research infrastructure/,/research data/],roles:[
        {label:'Open science push',claimType:'action',spec:{any:[/stronger action on open science/,/open science as a pillar/],preferSource:/ALLEA/}},
        {label:'Open infrastructure',claimType:'action',spec:{any:[/open access to jrc research infrastructures/,/european research infrastructures/],preferSource:/European Commission|Joint Research Centre/}},
        {label:'Shared research data',claimType:'action',spec:{any:[/data sharing.*open science/,/federated.*data access/,/public sharing of research data/]}},
        {label:'Open research information',claimType:'action',spec:{any:[/barcelona declaration on open research information/,/open research information/]}}
      ]},
      right:{title:'Sensitive research is facing tighter controls',plain:'Research-security and dual-use rules are adding more conditions around sensitive knowledge and collaboration.',why:'Controls can reduce leakage, but they also add friction to legitimate research.',historyAny:[/research security/,/knowledge security/,/dual-use/,/foreign interference/],roles:[
        {label:'Research-security rules',claimType:'action',spec:{any:[/national knowledge security guidelines/,/research security by roundtable/,/system leadership.*research security/]}},
        {label:'Dual-use controls',claimType:'action',spec:{any:[/evaluation of the dual-use regulation/,/dual-use regulation/],preferSource:/European Commission/}},
        {label:'Securitised cooperation',claimType:'effect',spec:{any:[/securitisation of knowledge/,/partial securitisation of science policy/,/research cooperation.*de-risking/]}},
        {label:'Foreign-interference concern',claimType:'diagnosis',spec:{any:[/counterintelligence battleground.*universit/,/foreign interference.*security-relevant research/,/espionage.*foreign interference/,/foreign interference.*knowledge security/]}}
      ]},
      flip:'It moves toward openness if security rules stay narrow in practice; toward closure if ordinary collaboration starts being restricted.'
    },
    {
      id:'collaborate_vs_derisk',
      left:{title:'Europe is adding research partners',plain:'Europe is widening formal science partnerships, research links and access beyond its borders.',why:'More partners can expand talent, capability and influence beyond Europe’s domestic base.',historyAny:[/science diplomacy/,/international cooperation/,/horizon association/,/research collaboration/],roles:[
        {label:'Science diplomacy',claimType:'action',spec:{any:[/framework for science diplomacy/,/first ever eu framework for science diplomacy/],preferSource:/Council of the European Union|European Commission/}},
        {label:'Horizon association',claimType:'action',spec:{any:[/japan officially joins horizon europe/,/eu and egypt strengthen research and innovation partnership.*horizon europe association/],preferSource:/European Commission|ERA Portal/}},
        {label:'Cross-border research',claimType:'action',spec:{any:[/fifth freedom/,/international cooperation in research and innovation/,/innovation beyond europe.*borders/]}},
        {label:'Partnership strategy',claimType:'action',spec:{any:[/autonomy through partnerships/,/shared gains, secure links/,/researchbridge/]}}
      ]},
      right:{title:'Research partnerships face tighter screening',plain:'The same system is becoming more selective where security and technology dependence are judged important.',why:'Selective access may protect capability, but it can fragment networks Europe still needs.',historyAny:[/de-risk.*research/,/research security/,/china.*research collaboration/,/restriction.*collaboration/,/knowledge security/],roles:[
        {label:'Knowledge-security controls',claimType:'action',spec:{any:[/national knowledge security guidelines/,/knowledge security/]}},
        {label:'EU-China de-risking',claimType:'effect',spec:{any:[/eu.?china research cooperation.*de-risking/,/securitisation of knowledge.*eu science policy/]}},
        {label:'Partner restrictions',claimType:'effect',spec:{any:[/restrictions.*international research collaboration/,/proposed restrictions on international research collaboration/,/science knows no borders/]}},
        {label:'Dual-use safeguards',claimType:'action',spec:{any:[/safeguards.*dual-use research/,/dual-use regulation/]}}
      ]},
      flip:'It moves toward partnership if controls stay limited to sensitive fields; toward selectivity if restrictions spread into ordinary research.'
    },
    {
      id:'talent_pull_vs_talent_friction',
      left:{title:'Europe is attracting research talent',plain:'Europe is treating research talent as strategic capacity and is building programmes to attract and retain people.',why:'Talent gains help turn new funding and infrastructure into actual research capability.',historyAny:[/talent/,/research career/,/doctoral workforce/,/researcher mobility/],roles:[
        {label:'Choose Europe',claimType:'action',spec:{any:[/choose europe for science/],preferSource:/Marie Skłodowska-Curie|European Commission/}},
        {label:'Attract and retain',claimType:'action',spec:{any:[/attract and retain research talent/,/research talent.*strategic advantage/]}},
        {label:'Researcher mobility',claimType:'action',spec:{any:[/the fifth freedom in the european research area/,/ecas report: insights from researchers on the fifth freedom/]}},
        {label:'Skills pipeline',claimType:'action',spec:{any:[/doctoral networks/],preferTitle:/Doctoral Networks/}}
      ]},
      right:{title:'Europe is struggling to retain research talent',plain:'Career insecurity, uneven opportunities and skills gaps still make it hard to keep scarce researchers.',why:'New facilities do little if the people needed to use them leave or cannot be hired.',historyAny:[/brain drain/,/precar/,/research career/,/skills shortage/,/talent shortage/],roles:[
        {label:'Brain drain',claimType:'effect',spec:{any:[/research careers, brain drain and policy lessons/,/which job offers may mitigate brain drain/]}},
        {label:'Career insecurity',claimType:'effect',spec:{any:[/precarity/,/temporary contracts/],preferTitle:/Choose Europe : Research Careers/}},
        {label:'Skills gap',claimType:'diagnosis',spec:{any:[/skills shortage/,/skills gap/,/human-capability.*gap/,/researcher shortage/]}},
        {label:'Uneven opportunity',claimType:'diagnosis',spec:{any:[/underrepresented european countries/,/widening country.*barrier/,/regional.*human capital/]}}
      ]},
      flip:'It moves toward attraction if strategic fields show net inflows and better careers; toward friction if departures and shortages persist.'
    },
    {
      id:'infrastructure_vs_bottlenecks',
      left:{title:'Europe is expanding research infrastructure',plain:'Europe is expanding shared laboratories, computing facilities and other research infrastructure.',why:'More capacity gives researchers places to test, compute and scale new ideas.',historyAny:[/europe.*research infrastructure/,/europe.*supercomput/,/europe.*compute capacity/,/open access.*infrastructure/,/eurohpc/],roles:[
        {label:'Research infrastructure',claimType:'action',spec:{any:[/^european research infrastructures/,/horizon europe: research infrastructures/]}},
        {label:'AI and compute',claimType:'action',spec:{any:[/ai gigafactor/,/supercomputer/,/resource for ai science in europe/]}},
        {label:'Quantum facilities',claimType:'action',spec:{any:[/quantum-testing infrastructure/,/quantum experimental pilot lines/,/new quantum computer/]}},
        {label:'Open facility access',claimType:'action',spec:{any:[/open access to jrc research infrastructures/,/federated.*infrastructure/]}}
      ]},
      right:{title:'Access to research infrastructure remains constrained',plain:'Access, concentration and bottlenecks still limit how easily researchers can use scarce facilities.',why:'A facility only adds capability when researchers can actually reach and use it.',historyAny:[/bottleneck/,/limited.*capacity/,/access.*research infrastructure/,/infrastructure.*gap/,/research infrastructure.*access/],roles:[
        {label:'Bottleneck resources',claimType:'effect',spec:{any:[/research infrastructures as bottleneck resources/],preferSource:/EPJ Research Infrastructures/}},
        {label:'Concentrated capacity',claimType:'effect',spec:{any:[/limited and geographically concentrated/,/cloud and ai computing capacity.*limited/],preferSource:/European Commission/}},
        {label:'Participation barriers',claimType:'effect',spec:{any:[/barriers and policy priorities.*underrepresented european countries/,/navigating eu research participation.*widening country/]}}
      ]},
      flip:'It moves toward capacity if access broadens as fast as construction; toward bottlenecks if demand and regional gaps grow faster.'
    },
    {
      id:'one_europe_vs_many_rulebooks',
      left:{title:'Europe is building common research rules',plain:'Europe is building common frameworks, shared programmes and cross-border rules for research.',why:'Common approaches can make collaboration and access more predictable across Europe.',historyAny:[/european research area/,/eu framework/,/fifth freedom/,/common.*research/,/science diplomacy/],roles:[
        {label:'EU science framework',claimType:'action',spec:{any:[/eu framework for science diplomacy/,/framework for science diplomacy/],preferSource:/Council of the European Union|European Commission/}},
        {label:'European Research Area',claimType:'action',spec:{any:[/^european research area$/, /european research area.*policy/],preferSource:/European Commission/}},
        {label:'Fifth Freedom',claimType:'action',spec:{any:[/fifth freedom in the european research area/,/fifth freedom.*research/]}},
        {label:'Shared infrastructure',claimType:'action',spec:{any:[/european research infrastructures/,/federat.*european.*research/]}}
      ]},
      right:{title:'National research rules still differ',plain:'National approaches still diverge on research security, access and strategic technology policy.',why:'Different national rules can turn one European research space into several practical systems.',historyAny:[/fragment/,/national.*research security/,/scandinavian/,/germany.*research security/,/ireland.*research security/],roles:[
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
      left:{title:'Defence and dual-use research are expanding',plain:'More European research funding and policy is opening toward defence and dual-use technology.',why:'That can connect research to security needs and new sources of funding.',historyAny:[/dual-use/,/defence innovation/,/research security/,/civil-military/],roles:[
        {label:'EIC opens to dual use',claimType:'action',spec:{any:[/european innovation council opens to defence and dual-use technologies/],preferSource:/European Innovation Council/}},
        {label:'Funding expands',claimType:'action',spec:{any:[/research and innovation funding expands to defence and dual-use/]}},
        {label:'Dual-use regulation review',claimType:'action',spec:{any:[/evaluation of the dual-use regulation/],preferSource:/European Commission/}},
        {label:'Defence regions',claimType:'action',spec:{any:[/european network of defence-related regions/]}}
      ]},
      right:{title:'Civilian and open research remain important',plain:'Universities and research groups are also pushing to keep European research open and research-led.',why:'Those safeguards can limit how far security priorities reshape ordinary research.',historyAny:[/academic freedom/,/open science/,/research-led/,/science knows no borders/],roles:[
        {label:'Keep FP10 research-led',claimType:'action',spec:{any:[/keep fp10 open and research-led/]}},
        {label:'Safeguards for dual use',claimType:'action',spec:{any:[/urges safeguards as fp10 opens to dual-use/,/requests safeguards for dual-use research/]}},
        {label:'Science without borders',claimType:'action',spec:{any:[/science knows no borders/],preferSource:/ALLEA/}},
        {label:'Open science push',claimType:'action',spec:{any:[/stronger action on open science/,/open science as a pillar/]}}
      ]},
      flip:'It shifts toward security if dual-use becomes routine across programmes; toward openness if safeguards keep most research outside that logic.'
    },
    {
      id:'rules_vs_race',
      left:{title:'Europe is expanding technology rules and standards',plain:'Europe keeps building rules, standards and safeguards around strategic technologies and research.',why:'Clear rules can protect trust and shape markets before technologies become harder to govern.',historyAny:[/standard/,/regulation/,/governance/,/research security/,/rules-standards/],roles:[
        {label:'AI rules',claimType:'action',spec:{any:[/ahead of the final agreement on the ai act/,/ai governance and geopolitics/]}},
        {label:'Quantum standards',claimType:'action',spec:{any:[/standards for quantum technologies/],preferSource:/EuroHPC/}},
        {label:'Dual-use rules',claimType:'action',spec:{any:[/evaluation of the dual-use regulation/],preferSource:/European Commission/}},
        {label:'Research-security guidance',claimType:'action',spec:{any:[/national knowledge security guidelines/,/research security by roundtable/]}}
      ]},
      right:{title:'Europe is under pressure to move faster on technology',plain:'The same evidence base keeps warning that Europe must close technology and growth gaps faster.',why:'Slow delivery can leave good rules governing markets and capabilities built elsewhere.',historyAny:[/competitiveness gap/,/technology gap/,/scale-up/,/catching up/,/growth model/],roles:[
        {label:'Growth pressure',claimType:'diagnosis',spec:{any:[/eu.*need for a new growth model/],preferSource:/FIIA|Finnish Institute/}},
        {label:'Defence catch-up',claimType:'action',spec:{any:[/catching up: europe.*strategic autonomy in the defence industry/]}},
        {label:'AI competitiveness gap',claimType:'diagnosis',spec:{any:[/structural limitations and competitiveness challenges.*european union.*ai/,/strategic competitiveness.*eu.*united states.*ai/]}},
        {label:'Scale-up push',claimType:'action',spec:{any:[/eu startup and scaleup strategy/,/step scaleup/],preferSource:/European Commission|European Innovation Council/}}
      ]},
      flip:'It moves toward rules if standards become an advantage; toward the race if capability gaps widen despite an expanding rulebook.'
    }
  ];

  function plainTrendTitle(value){
    const t=clean(value);
    const exact={
      'Green technology gains momentum':'Green technology is expanding',
      'Rules and costs rein green technology in':'Rules and costs are constraining green technology',
      'Build more European computing capacity':'Europe is expanding computing capacity',
      'Power, supply and access constrain the build-out':'Power, supply and access are constraining computing expansion',
      'Fresh commitments for strategic investment':'Strategic investment is increasing',
      'Friction grows around strategic investment':'Barriers to strategic investment are growing',
      'Scaling up research security':'Research-security measures are expanding',
      'Research security gets harder to do':'Research-security requirements are becoming harder to implement',
      'Europe bets bigger on AI':'Europe is increasing investment in AI',
      'The bill for AI keeps rising':'AI costs and requirements are increasing',
      'Europe pushes materials advanced forward':'Europe is expanding advanced-materials capacity',
      'Materials advanced runs into limits':'Advanced materials face growing constraints',
      'Horizon access: the build-out accelerates':'Horizon access is expanding',
      'Horizon access: the fine print tightens':'Conditions on Horizon access are tightening',
      'Europe doubles down on venture capital':'European venture capital is expanding',
      'Second thoughts slow venture capital':'Europe still has a venture-capital gap',
      'Build more strategic autonomy':'Europe is building more strategic autonomy',
      'Dependencies keep setting the terms':'Strategic dependencies are limiting autonomy',
      'Open more research partnerships':'Europe is opening more research partnerships',
      'Put more conditions around collaboration':'Research collaboration faces tighter conditions',
      'Critical infrastructure resilience is on the rise':'Europe is strengthening critical-infrastructure resilience',
      'Critical infrastructure resilience meets resistance':'Preparedness gaps are slowing resilience efforts',
      'Opening the throttle on energy supply':'Energy-supply capacity is expanding',
      'Pulling the handbrake on energy supply':'New constraints are emerging around energy supply',
      'Expand research-system capacity':'Europe is expanding research-system capacity',
      'Capacity is being stretched or made conditional':'Research-system capacity is being stretched or made conditional',
      'More money and moves behind defence R&I':'Funding and activity are increasing in defence R&I',
      'New conditions pile up around defence R&I':'Conditions around defence R&I are tightening',
      'Push harder on innovation performance':'Europe is strengthening innovation performance',
      'Structural bottlenecks keep holding performance back':'Structural bottlenecks are holding innovation performance back'
    };
    if(exact[t])return exact[t];
    const rules=[
      [/^Europe pushes (.+) forward$/i,(_,x)=>`Europe expands ${x}`],
      [/^(.+) runs into limits$/i,(_,x)=>`${x} faces growing constraints`],
      [/^More money and moves behind (.+)$/i,(_,x)=>`Investment and activity increase in ${x}`],
      [/^New conditions pile up around (.+)$/i,(_,x)=>`Conditions around ${x} are tightening`],
      [/^(.+) gains momentum$/i,(_,x)=>`${x} is expanding`],
      [/^Rules and costs rein (.+) in$/i,(_,x)=>`Rules and costs are constraining ${x}`],
      [/^Scaling up (.+)$/i,(_,x)=>`${x} is expanding`],
      [/^(.+) gets harder to do$/i,(_,x)=>`Barriers to ${x} are increasing`],
      [/^Europe doubles down on (.+)$/i,(_,x)=>`Europe is increasing support for ${x}`],
      [/^Second thoughts slow (.+)$/i,(_,x)=>`Constraints are slowing ${x}`],
      [/^(.+): the build-out accelerates$/i,(_,x)=>`${x} is expanding`],
      [/^(.+): the fine print tightens$/i,(_,x)=>`Conditions around ${x} are tightening`],
      [/^Fresh commitments for (.+)$/i,(_,x)=>`New commitments strengthen ${x}`],
      [/^Friction grows around (.+)$/i,(_,x)=>`Barriers around ${x} are growing`],
      [/^(.+) is on the rise$/i,(_,x)=>`${x} is expanding`],
      [/^(.+) meets resistance$/i,(_,x)=>`Resistance to ${x} is growing`],
      [/^Opening the throttle on (.+)$/i,(_,x)=>`Activity is increasing in ${x}`],
      [/^Pulling the handbrake on (.+)$/i,(_,x)=>`Constraints are slowing ${x}`],
      [/^(.+) finds new backers$/i,(_,x)=>`Support is growing for ${x}`],
      [/^(.+) faces new hurdles$/i,(_,x)=>`Barriers to ${x} are growing`],
      [/^Europe bets bigger on (.+)$/i,(_,x)=>`Europe is investing more in ${x}`],
      [/^The bill for (.+) keeps rising$/i,(_,x)=>`Costs of ${x} are rising`],
      [/^(.+) spreads$/i,(_,x)=>`Use of ${x} is expanding`],
      [/^(.+) gets fenced in$/i,(_,x)=>`Restrictions on ${x} are increasing`]
    ];
    for(const [re,fn] of rules){const m=t.match(re);if(m)return fn(...m);}
    return t;
  }


  function trendHeadlineFromPlain(title,plain){
    const t=plainTrendTitle(title),p=clean(plain),l=low(p);
    // Headline must be a compact statement actually supported by the sentence below it.
    // These rules describe the development in the sentence; they never broaden it back
    // to the controlled object merely because that object was used for candidate discovery.
    const rules=[
      [/environmental biotechnology offers routes to cleaner production/,()=> 'Environmental biotechnology is opening cleaner production routes'],
      [/persistent gaps in batteries and solar supply chains/,()=> 'Europe still has gaps in batteries and solar supply chains'],
      [/eurohpc opened a competitive call.*ai gigafactor/,()=> 'Europe is moving to build AI Gigafactories'],
      [/data-centre geography changing in response to power and land constraints/,()=> 'Power and land constraints are reshaping AI data-centre locations'],
      [/subsidies helped compensate for germany.s cost disadvantages/,()=> 'Subsidies are supporting strategic investment despite Germany’s cost disadvantages'],
      [/selective conditionality is narrowly targeted.*limited leverage over foreign investors/,()=> 'EU investment conditionality remains limited'],
      [/belgian authorities opened a concrete semiconductor-espionage case/,()=> 'Belgium has opened a semiconductor-espionage case'],
      [/research security self-assessment appendix is a mandatory/,()=> 'Finland has made research-security self-assessment mandatory'],
      [/commission proposes a regulation.*cloud and ai ecosystem/,()=> 'The EU is proposing new rules for its cloud and AI ecosystem'],
      [/legal clarity is associated with deeper, not necessarily broader.*ai adoption/,()=> 'AI legal clarity may deepen adoption without broadening it'],
      [/advanced-materials effort must be less fragmented/,()=> 'Europe’s advanced-materials effort remains fragmented'],
      [/mature substitutes can cut gallium.*germanium.*palladium/,()=> 'Mature substitutes can reduce some critical-material dependencies'],
      [/horizon europe initiatives launched to improve access, financing and industry collaboration/,()=> 'EU initiatives are widening access to research infrastructure'],
      [/hungary.s continued exclusion from horizon europe grants/,()=> 'Hungary’s Horizon exclusion is constraining research capacity'],
      [/mistral closed a eur 3 billion round/,()=> 'Mistral’s €3 billion round is boosting European venture capital'],
      [/eu leads globally in scientific output but underperforms markedly in patenting, venture capital and scale-up/,()=> 'Europe still lags in venture capital and scale-up'],
      [/pursuing greater sovereign space capability/,()=> 'Europe is pursuing more sovereign space capability'],
      [/reducing strategic dependencies and adapting to those that persist/,()=> 'Strategic dependencies continue to limit European resilience'],
      [/council adopted the first eu framework for science diplomacy/,()=> 'The EU has adopted a framework for science diplomacy'],
      [/security and sovereignty measures do not collapse the openness needed for science/,()=> 'Security measures can constrain research openness'],
      [/spain proposed a stronger eu climate-resilience framework/,()=> 'Spain is pushing for stronger EU climate-resilience rules'],
      [/preparedness and integration into corporate strategy remain uneven/,()=> 'European firms remain unevenly prepared for geopolitical risks'],
      [/google announced a major new ai-compute investment and energy arrangement in finland/,()=> 'Google is expanding AI compute and energy investment in Finland'],
      [/finnish opposition parties proposed a national permitting framework for data centres/,()=> 'Finland is considering a national permitting framework for data centres'],
      [/international coalition for science, research and innovation in ukraine.*gdansk declaration/,()=> 'International partners are coordinating support for Ukraine’s research system'],
      [/irish preparedness confidence fell.*vulnerability profiles/,()=> 'Preparedness remains uneven across countries'],
      [/agile.*€?115 million programme.*development, testing and uptake/,()=> 'EU institutions are funding faster defence-technology development'],
      [/defence readiness by 2030 depends on collaborative procurement, shared training/,()=> 'European defence readiness still depends on coordinated procurement and training'],
      [/commission proposed new eu legislation aimed at strengthening the single market for innovation/,()=> 'The Commission is proposing new EU innovation legislation'],
      [/eu27 improves but remains behind the us, south korea and japan/,()=> 'EU innovation performance still trails major global peers']
    ];
    for(const [re,fn] of rules){if(re.test(l))return fn();}
    // Fail conservative: if a generic generated title appears to speak more broadly
    // than the displayed evidence sentence, use a compact first-clause headline instead.
    const generic=/\b(expand|expanding|constraint|constrain|slow|strengthen|tighten|support|barrier|capacity|investment|autonomy|performance|resilience|energy supply)\b/i;
    if(generic.test(t)){
      let h=p.replace(/^(new market data show|the evidence shows|sources show|analysis shows)\s+/i,'')
             .split(/[.;]/)[0].trim();
      const words=h.split(/\s+/);
      if(words.length>16)h=words.slice(0,16).join(' ')+'…';
      if(h)return h.charAt(0).toUpperCase()+h.slice(1).replace(/[.!?]+$/,'');
    }
    return t;
  }

  function highOrderPairs(data){
    const state=data?.high_order_inference&&typeof data.high_order_inference==='object'?data.high_order_inference:{};
    const ids=Array.isArray(state?.publications?.trend)?state.publications.trend:[];
    const map=new Map((Array.isArray(state?.candidates)?state.candidates:[]).filter(x=>x&&typeof x==='object').map(x=>[clean(x.id),x]));
    return ids.map(id=>map.get(clean(id))).filter(Boolean).map(c=>{
      const b=c.trend_balance||{},lp=Number(b.left_pull),rp=Number(b.right_pull);
      if(!Number.isFinite(lp)||!Number.isFinite(rp)||Math.round(lp+rp)!==100)return null;
      const support=Array.isArray(c.support)?c.support:[];
      const leftRole=clean(b.left_role||'Concentrating action');
      const rightRole=clean(b.right_role||'Spreading action');
      const leftEvidence=support.filter(x=>clean(x?.role).startsWith(leftRole)).map(x=>({row:x}));
      const rightEvidence=support.filter(x=>clean(x?.role).startsWith(rightRole)).map(x=>({row:x}));
      if(leftEvidence.length<1||rightEvidence.length<1)return null;
      // v26: the engine's card writer heads each side with the trend itself and lists
      // the developments behind it; the page never swaps in a single anecdote.
      return {id:c.id,emergent:true,family:clean(b.family),objectKey:clean(b.object_key),support:Number(c.score)||0,
        pairTitle:clean(b.pair_title||c.reader_title||''),kindLabel:clean(c.reader_kind_label||'Tug of war'),wow:Number(c.wow)||0,
        left:{title:clean(b.left_title||'Pull A'),plain:clean(b.left_plain||''),why:'',pull:Math.round(lp),evidence:leftEvidence,history:[],sourceCount:Number(b.left_sources)||0},
        right:{title:clean(b.right_title||'Pull B'),plain:clean(b.right_plain||''),why:'',pull:Math.round(rp),evidence:rightEvidence,history:[],sourceCount:Number(b.right_sources)||0},
        pullRange:{left:b.left_range||[],right:b.right_range||[]},
        composition:clean(b.composition||''),flip:clean(b.flip_line||''),label:clean(b.label||''),
        actionStats:{leftActions:Number(b.left_actions)||0,rightActions:Number(b.right_actions)||0,leftSources:Number(b.left_sources)||0,rightSources:Number(b.right_sources)||0,rawLeft:Number(b.raw_left_pull),rawRight:Number(b.raw_right_pull)},
        currentEvidenceCount:Number(c.primary_records)||0,historicalContextCount:0};
    }).filter(Boolean);
  }

  function build(data,history){
    const state=data?.high_order_inference&&typeof data.high_order_inference==='object'?data.high_order_inference:{};
    if(state?.detector_backend==='claim_native'&&Number(state?.selection_stage||0)>=7){
      // Stage 7 already publishes the deliberate wow-cycle order (5,4,3,2,1 x3).
      // Do not re-sort the shelf in the browser.
      return highOrderPairs(data);
    }
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
    const semanticDuplicate=(x)=>{
      if(x.family==='open_protect'&&x.objectKey==='openness')return out.some(y=>y.id==='open_vs_secure');
      if(x.family==='attract_friction'&&x.objectKey==='talent')return out.some(y=>y.id==='talent_pull_vs_talent_friction');
      if(x.family==='capacity_access'&&x.objectKey==='infrastructure')return out.some(y=>y.id==='infrastructure_vs_bottlenecks');
      return false;
    };
    for(const x of highOrderPairs(data))if(!out.some(y=>y.id===x.id)&&!semanticDuplicate(x))out.push(x);
    return out.sort((a,b)=>b.support-a.support||Math.abs(50-a.left.pull)-Math.abs(50-b.left.pull)||a.id.localeCompare(b.id));
  }
  function stats(data,history){
    const hs=historicalCorpus(history);
    return {
      current:currentCorpus(data).length,historical:hs.length,
      historicalAuthoritative:hs.filter(x=>x?.historical_reasoning_status==='authoritative').length,
      historicalCautious:hs.filter(x=>x?.historical_reasoning_status&&x.historical_reasoning_status!=='authoritative').length,
      historicalExcluded:Number(history?.reasoning_stats?.not_retained)||0
    };
  }
  return {build,stats,pairs:PAIRS,reportingRole,quality,rowText,sideQualifies};
});
