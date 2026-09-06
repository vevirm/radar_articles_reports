/* v17.20.17 — paired trends/countertrends inferred from retained Radar evidence.
   The analytical rules intentionally discount publication cadence and distinguish
   actor-reporting (strong for actions) from observer-reporting (stronger for effects). */
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
  function rowText(x){return low([x.title,x.headline,x.what,x.core_message,x.summary,x.relevance_note,x.why_it_matters,x.bridge_sentence,(x.geo_evidence||[]).join(' '),(x.ri_evidence||[]).join(' '),x.source].join(' '))}
  function source(x){return clean(x?.source||x?.journal||x?.institution||'')}
  const ACTOR=/\b(?:European Commission|European Innovation Council|European Research Council|European Investment Bank|EuroHPC|Council of the European Union|European Parliament|Joint Research Centre|JRC Publications Repository|ERA Portal|Marie Skłodowska-Curie Actions|Research Council of|Ministry|Agency for|Government of|Fusion for Energy)\b/i;
  const EU_POLICY_ACTOR=/\b(?:European Commission|European Innovation Council|European Research Council|EuroHPC|Council of the European Union|Joint Research Centre|JRC Publications Repository|ERA Portal|Marie Skłodowska-Curie Actions)\b/i;
  function reportingRole(x){return ACTOR.test(source(x))?'actor':'observer'}
  function corpus(data){
    const out=[],seen=new Set();
    for(const [key,prefix] of [['strand_a','A'],['strand_c','C'],['strategic_pathways','P']]){
      const xs=Array.isArray(data?.[key])?data[key]:[];
      xs.forEach((x,i)=>{if(!x||typeof x!=='object')return;const k=clean(x.link)||low(x.title||x.headline||x.what);if(k&&seen.has(k))return;if(k)seen.add(k);out.push({...x,_row:`${prefix}${String(i+1).padStart(3,'0')}`,_strand:prefix})});
    }
    return out;
  }
  function matches(x,spec){
    const t=rowText(x);
    if(spec.all&&spec.all.some(p=>!rx(p).test(t)))return false;
    if(spec.any&&spec.any.length&&!spec.any.some(p=>rx(p).test(t)))return false;
    if(spec.none&&spec.none.some(p=>rx(p).test(t)))return false;
    return true;
  }
  function hostileWitness(x,role){
    if(!role.hostileWitness)return false;
    if(role.hostileSource&& !rx(role.hostileSource).test(source(x)))return false;
    return EU_POLICY_ACTOR.test(source(x));
  }
  function candidateScore(x,role){
    let n=quality(x)*100;
    const t=rowText(x);
    for(const p of role.spec?.all||[])if(rx(p).test(t))n+=32;
    for(const p of role.spec?.any||[])if(rx(p).test(t))n+=15;
    if(role.spec?.preferSource&&rx(role.spec.preferSource).test(source(x)))n+=180;
    if(role.spec?.preferTitle&&rx(role.spec.preferTitle).test(clean(x.title||x.headline)))n+=220;
    if(hostileWitness(x,role))n+=360;
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
    if(type==='action')mult*=rr==='actor'?1.08:0.96;
    else if(type==='effect'||type==='outcome')mult*=rr==='actor'?0.68:1.08;
    else mult*=rr==='actor'?0.84:1.04;
    const hostile=hostileWitness(x,role);if(hostile)mult*=1.22;
    const src=source(x).toLowerCase();const count=sourceUse.get(src)||0;
    if(count===1)mult*=0.86;else if(count>=2)mult*=0.68;
    sourceUse.set(src,count+1);
    return {weight:q*mult,quality:q,reporting:rr,hostile};
  }
  function sideEvidence(rows,side){
    const used=new Set(),sourceUse=new Map(),evidence=[];
    for(const role of side.roles){
      const row=pick(rows,role,used);if(!row)continue;
      const w=claimWeight(row,role,sourceUse);
      evidence.push({role:role.label,row,...w,claimType:role.claimType||'diagnosis'});
    }
    const sum=evidence.reduce((a,e)=>a+e.weight,0);
    const avg=evidence.length?evidence.reduce((a,e)=>a+e.quality,0)/evidence.length:0;
    const sources=new Set(evidence.map(e=>source(e.row)).filter(Boolean));
    const observers=evidence.filter(e=>e.reporting==='observer').length;
    const hostile=evidence.filter(e=>e.hostile).length;
    // Distinct claims drive the score; row volume from a prolific publisher does not.
    const diversityBonus=Math.min(18,sources.size*3)+Math.min(10,observers*2)+hostile*5;
    evidence.sort((a,b)=>(b.hostile?1:0)-(a.hostile?1:0)||b.quality-a.quality);
    return {evidence,raw:sum+diversityBonus,averageQuality:Math.round(avg),bestQuality:evidence.length?Math.max(...evidence.map(e=>e.quality)):0,sourceCount:sources.size,observerCount:observers,hostileCount:hostile};
  }

  const PAIRS=[
    {
      id:'build_vs_rent',
      left:{title:'Building our own',plain:'Europe is putting real money, machines and shared infrastructure into its own compute and strategic-technology capacity.',why:'More European-controlled capacity reduces exposure to external compute and technology chokepoints.',roles:[
        {label:'AI-compute investment',claimType:'action',spec:{any:[/ai gigafactor/,/€30 billion.*ai/,/30 billion.*ai/],preferSource:/European Commission/}},
        {label:'Supercomputing capacity',claimType:'action',spec:{any:[/top500.*jupiter/,/supercomput.*europe/,/ai supercomputer/],preferSource:/EuroHPC/}},
        {label:'Quantum capacity',claimType:'action',spec:{any:[/quantum computer.*europe/,/six new quantum calls/,/quantum-testing infrastructure/,/quantum experimental pilot lines/],preferSource:/EuroHPC/}},
        {label:'Federated access',claimType:'action',spec:{any:[/federation platform.*supercomput/,/resource for ai science in europe/,/opens access to its quantum computers/]}},
        {label:'Sovereignty policy',claimType:'action',spec:{any:[/tech sovereignty package/,/strengthening europe.*tech sovereignty/,/digital autonomy and resilience/]}}
      ]},
      right:{title:'Renting theirs',plain:'European research and industry still depend on non-European cloud, frontier compute, chips and technology layers that cannot be substituted quickly.',why:'External control over critical layers can constrain European research access, cost and strategic freedom.',roles:[
        {label:'Cloud and AI dependence',claimType:'effect',hostileWitness:true,hostileSource:/European Commission/,spec:{any:[/cloud and ai development.*limited/,/dependence on non-european suppliers/,/cloud.*non-european supplier/],preferTitle:/Cloud and AI Development/}},
        {label:'Frontier-compute gap',claimType:'diagnosis',spec:{any:[/compute gap/,/purchas.*us.*compute/,/frontier compute/],preferSource:/Bruegel/}},
        {label:'Military-AI capability gap',claimType:'diagnosis',spec:{any:[/military ai.*10.?15 year/,/autonomy that cannot be bought/,/military ai.*capability gap/],preferSource:/VoxEU|CEPR/}},
        {label:'Chip dependence',claimType:'diagnosis',spec:{any:[/semiconductor.*depend/,/supply chain dependencies on china, taiwan and the united states/,/geopolitics of ai chips/]}},
        {label:'US-tech reliance',claimType:'diagnosis',spec:{any:[/deeper us tech reliance/,/reliance on us.*tech/,/american digital firms.*depend/]}}
      ]},
      flip:'It would move sharply with a measured foreign-compute dependency ratio, or with evidence that major European capacity has slipped or replaced foreign use at scale.'
    },
    {
      id:'money_in_vs_firms_out',
      left:{title:'Money coming in',plain:'EU institutions are putting more public capital and scale-up instruments behind European deep-tech firms.',why:'More scale-up finance can keep research-intensive firms and their capabilities inside Europe.',roles:[
        {label:'Large-scale investment alliance',claimType:'action',spec:{any:[/€80 billion investment alliance/,/80 billion investment alliance/],preferSource:/European Investment Bank/}},
        {label:'STEP scale-up capital',claimType:'action',spec:{any:[/step scale up investments/,/scale-up funding.*step scale up/],preferSource:/European Innovation Council/}},
        {label:'Startup and scale-up strategy',claimType:'action',spec:{any:[/eu startup and scaleup strategy/],preferSource:/European Commission/}},
        {label:'EIC investment capacity',claimType:'action',spec:{any:[/eic fund investment guidelines/,/eic impact report.*scaling hub/],preferSource:/European Innovation Council/}},
        {label:'Deep-tech support',claimType:'action',spec:{any:[/deep tech.*funding/,/scale up tech leaders/,/european scale-ups/]}}
      ]},
      right:{title:'Companies going out',plain:'The private-capital gap still gives successful European firms reasons to tap foreign markets, investors and sometimes foreign locations.',why:'Foreign financing and relocation can move ownership, know-how and future growth outside Europe.',roles:[
        {label:'Startup relocation',claimType:'effect',hostileWitness:true,hostileSource:/JRC|Joint Research Centre/,spec:{any:[/is europe losing its startups/,/virtual relocation.*vc markets abroad/],preferTitle:/losing its startups/}},
        {label:'Late-stage VC gap',claimType:'diagnosis',spec:{any:[/late-stage vc gap/,/venture capital gap.*high-growth/],preferSource:/European Central Bank/}},
        {label:'Reliance on non-EU investors',claimType:'effect',spec:{any:[/reliance on non-eu investors/,/non-eu investors.*relocation/],preferSource:/European Central Bank/}},
        {label:'Private-capital depth',claimType:'diagnosis',spec:{any:[/weak institutional-investor participation/,/institutional investor.*venture/,/pension.*venture capital/,/insurance.*venture capital/],preferSource:/European Central Bank/}},
        {label:'Foreign acquisition / ownership channel',claimType:'effect',spec:{any:[/foreign acquisition/,/foreign ownership/,/investment screening.*technology transfer/]}}
      ]},
      flip:'It would flip on a measured decline in relocation/foreign-financing dependence, or on a binding mechanism that redirects deep European institutional capital into scale-up finance.'
    },
    {
      id:'open_vs_secure',
      left:{title:'Opening the research system',plain:'Europe is expanding open research information, federated data, shared infrastructure and cross-border access.',why:'Wider access can strengthen collaboration, reuse and the effective reach of European research infrastructure.',roles:[
        {label:'Open research information',claimType:'action',spec:{any:[/barcelona declaration on open research information/,/open research information/]}},
        {label:'Open science implementation',claimType:'action',spec:{any:[/open science/,/open access.*research infrastructure/],preferSource:/European Commission|Science and Public Policy/}},
        {label:'Federated research data',claimType:'action',spec:{any:[/federated.*data/,/eosc/,/data sharing.*open science/]}},
        {label:'Shared research infrastructure',claimType:'action',spec:{any:[/european research infrastructures/,/open access to jrc research infrastructures/],preferSource:/European Commission|JRC/}}
      ]},
      right:{title:'Closing sensitive edges',plain:'Research-security, dual-use and knowledge-security rules are creating more conditions around who can access sensitive knowledge and collaboration.',why:'Tighter controls can reduce leakage while also adding friction to legitimate scientific cooperation.',roles:[
        {label:'Research-security rules',claimType:'action',spec:{any:[/research security/,/knowledge security/],preferSource:/ALLEA|Government of the Netherlands|Science and Public Policy/}},
        {label:'Dual-use safeguards',claimType:'action',spec:{any:[/dual-use.*safeguard/,/dual-use regulation/,/dual use.*research/]}},
        {label:'Foreign-interference concern',claimType:'diagnosis',spec:{any:[/foreign interference.*research/,/knowledge security.*foreign/]}},
        {label:'Securitised collaboration',claimType:'effect',spec:{any:[/research cooperation.*de-risking/,/securitisation of knowledge/,/as open as possible.*research security/]}}
      ]},
      flip:'It would move toward openness if security rules are shown to preserve broad access in practice; toward closure if major fields or infrastructures begin excluding partners or data at scale.'
    },
    {
      id:'collaborate_vs_derisk',
      left:{title:'More science through partnerships',plain:'Europe is widening formal science-diplomacy, Horizon association and international research links.',why:'Broader partnerships can expand capability, talent access and influence beyond Europe’s domestic research base.',roles:[
        {label:'Science-diplomacy framework',claimType:'action',spec:{any:[/framework for science diplomacy/],preferSource:/Council of the European Union|European Commission/}},
        {label:'New Horizon associations',claimType:'action',spec:{any:[/successfully conclude horizon europe negotiations/,/horizon europe association joint committee/,/association to horizon europe/],preferSource:/European Commission/}},
        {label:'International R&I cooperation',claimType:'action',spec:{any:[/international cooperation in research and innovation/],preferSource:/European Commission/}},
        {label:'Partnership strategy',claimType:'action',spec:{any:[/autonomy through partnerships/,/shared gains, secure links/]}}
      ]},
      right:{title:'More selective collaboration',plain:'The same system is narrowing or conditioning collaboration where security, technology dependence and strategic competition are judged material.',why:'Selective access can protect sensitive capability but fragment networks Europe still depends on.',roles:[
        {label:'Knowledge-security controls',claimType:'action',spec:{any:[/national knowledge security guidelines/,/knowledge security/]}},
        {label:'EU–China de-risking',claimType:'effect',spec:{any:[/eu.?china research cooperation.*de-risking/,/securitisation of knowledge.*eu science policy/]}},
        {label:'Dual-use restrictions',claimType:'action',spec:{any:[/dual-use regulation/,/safeguards for dual-use research/]}},
        {label:'Partner-side restrictions',claimType:'effect',spec:{any:[/restrictions.*international research collaboration/,/grant restrictions.*research collaboration/]}}
      ]},
      flip:'It would shift toward partnership if sensitive-field controls remain narrow while association grows; toward selectivity if restrictions spread into ordinary collaborative fields or data flows.'
    },
    {
      id:'talent_pull_vs_talent_friction',
      left:{title:'Trying harder to attract talent',plain:'European institutions are treating researchers and specialist skills as strategic capacity and are building programmes to attract, retain and train them.',why:'Talent gains increase the human capability needed to use new European research infrastructure and funding.',roles:[
        {label:'Choose Europe / attraction',claimType:'action',spec:{any:[/choose europe for science/,/attract and retain research talent/],preferSource:/European Commission|Marie Skłodowska-Curie/}},
        {label:'Strategic talent framing',claimType:'action',spec:{any:[/research talent is europe.*strategic advantage/],preferSource:/ALLEA/}},
        {label:'Researcher mobility',claimType:'action',spec:{any:[/fifth freedom/,/researcher mobility/]}},
        {label:'Specialist skills pipeline',claimType:'action',spec:{any:[/eumaster4hpc/,/hpc skills in europe/,/doctoral.*ai|postdoc.*ai/]}}
      ]},
      right:{title:'Talent frictions remain',plain:'Career precarity, stronger external offers and security/mobility frictions can still pull scarce researchers away from the places Europe is investing in.',why:'Infrastructure and funding cannot create capability if scarce researchers leave or cannot be recruited.',roles:[
        {label:'Career precarity / brain drain',claimType:'effect',hostileWitness:true,hostileSource:/European Commission|Marie Skłodowska-Curie/,spec:{any:[/precarity.*brain drain/,/researchers leaving europe.*brain drain/]}},
        {label:'External talent pull',claimType:'effect',spec:{any:[/lure scientists back/,/attract.*researchers.*abroad/,/talent.*competition/]}},
        {label:'Research-security friction',claimType:'diagnosis',spec:{any:[/research security.*mobility/,/knowledge security.*researcher/,/foreign interference.*researcher/]}},
        {label:'Regional / capability shortage',claimType:'diagnosis',spec:{any:[/skills shortage/,/talent shortage/,/human capital.*gap/,/researcher shortage/]}}
      ]},
      flip:'It would move toward attraction on evidence of net inflows into strategic fields; toward friction if vacancies, departures or concentration persist despite the new programmes.'
    }
  ];

  function build(data){
    const rows=corpus(data),out=[];
    for(const pair of PAIRS){
      const left=sideEvidence(rows,pair.left),right=sideEvidence(rows,pair.right);
      if(left.evidence.length<3||right.evidence.length<3)continue;
      if(left.evidence.filter(e=>e.quality>=85).length<2||right.evidence.filter(e=>e.quality>=85).length<2)continue;
      if(left.bestQuality<95||right.bestQuality<95)continue;
      const total=left.raw+right.raw;if(total<=0)continue;
      let leftOdds=Math.round(100*left.raw/total);leftOdds=Math.max(15,Math.min(85,leftOdds));
      const rightOdds=100-leftOdds;
      const support=Math.round((left.averageQuality+right.averageQuality)/2 + Math.min(10,(left.sourceCount+right.sourceCount)) + Math.min(6,left.hostileCount*3+right.hostileCount*3));
      out.push({...pair,left:{...pair.left,...left,odds:leftOdds},right:{...pair.right,...right,odds:rightOdds},support});
    }
    return out.sort((a,b)=>b.support-a.support||Math.abs(50-a.left.odds)-Math.abs(50-b.left.odds)||a.id.localeCompare(b.id));
  }
  return {build,pairs:PAIRS,reportingRole,quality,rowText};
});
