(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory(require('./scenarios.js'),require('../reader_rank.js'));
  else root.RadarShockVariants=factory(root.RadarShockScenarios,root.RadarReaderRank);
})(typeof globalThis!=='undefined'?globalThis:this,function(Scenarios,ReaderRank){
  'use strict';
  const clean=v=>String(v||'').replace(/\s+/g,' ').trim();
  const low=v=>clean(v).toLowerCase();
  const dateValue=v=>{const n=Date.parse(v||'');return Number.isFinite(n)?n:0};
  const qualityScore=x=>Math.max(0,Math.min(100,Number(x?._storedQuality??ReaderRank?.scoreFor?.(x))||0));
  const rx=v=>v instanceof RegExp?v:new RegExp(String(v),'i');
  function rowText(x){return low([x.title,x.headline,x.what,x.core_message,x.summary,x.relevance_note,x.why_it_matters,x.source].join(' '))}
  function matches(x,spec){
    const t=rowText(x);
    if(spec.all&&spec.all.some(p=>!rx(p).test(t)))return false;
    if(spec.any&&spec.any.length&&!spec.any.some(p=>rx(p).test(t)))return false;
    if(spec.none&&spec.none.some(p=>rx(p).test(t)))return false;
    return true;
  }
  function score(x,spec){
    const t=rowText(x);let n=qualityScore(x)*100;
    for(const p of spec.all||[])if(rx(p).test(t))n+=35;
    for(const p of spec.any||[])if(rx(p).test(t))n+=18;
    if(spec.preferSource&&rx(spec.preferSource).test(clean(x.source)))n+=220;
    if(spec.preferTitle&&rx(spec.preferTitle).test(clean(x.title||x.headline)))n+=260;
    if(x.new_this_scan)n+=12;
    n+=dateValue(x.date)/1e12;
    return n;
  }
  function corpus(data){
    const out=[],seen=new Set();
    for(const [key,prefix] of [['strand_a','A'],['strand_c','C'],['strategic_pathways','P']]){
      const xs=Array.isArray(data?.[key])?data[key]:[];
      xs.forEach((x,i)=>{if(!x||typeof x!=='object')return;const k=clean(x.link)||clean(x.title||x.headline).toLowerCase();if(k&&seen.has(k))return;if(k)seen.add(k);out.push({...x,_row:`${prefix}${String(i+1).padStart(3,'0')}`,_strand:prefix})});
    }
    return out;
  }
  function pick(rows,spec,used){
    const candidates=rows.filter(x=>!used.has(x._row)&&matches(x,spec)).sort((a,b)=>score(b,spec)-score(a,spec));
    const chosen=candidates[0];if(chosen)used.add(chosen._row);return chosen||null;
  }

  const PROFILES={
    direct_materials_cutoff:{
      variants:[
        {id:'contained',label:'Contained',title:'A narrow export-control squeeze is absorbed by substitution and stockpiles',text:'Controls bite, but only on inputs for which European programmes can qualify substitutes or draw on alternative suppliers before critical experiments stop.'},
        {id:'core',label:'Core shock',title:'A no-substitute material or chip disappears and strategic R&I programmes stall',text:'The restriction reaches a specialised input with no qualified replacement. Pilot work, qualification and high-end compute schedules slip even before factory output becomes the headline.'},
        {id:'compound',label:'Compound',title:'Materials and advanced-chip restrictions land together',text:'Two dependency layers fail at once. Europe cannot easily engineer around the missing material because the compute and chip capacity needed for redesign and qualification is constrained too.'}
      ],
      counterRoles:[
        ['European semiconductor capacity',{any:[/chips act 2\.0/,/semiconductor.*strategic autonomy/,/second semiconductor push/],preferTitle:/Chips Act|semiconductor/}],
        ['Tech-sovereignty investment',{any:[/tech sovereignty package/,/strengthening europe.*tech sovereignty/,/strategic autonomy and resilience/],preferSource:/European Commission/}],
        ['European compute build-out',{any:[/ai gigafactor/,/supercomput/,/eurohpc.*quantum/],preferSource:/European Commission|EuroHPC/}],
        ['Critical-material mitigation',{any:[/critical raw material.*dismantle/,/clean industrial future/,/resilien.*critical.*material/]}]
      ]
    },
    direct_cyber_infrastructure:{
      variants:[
        {id:'contained',label:'Contained',title:'A local outage is routed around through federation and spare capacity',text:'The attack disables one service, but alternative facilities, federated access and incident-response arrangements keep most projects running.'},
        {id:'core',label:'Core shock',title:'A shared compute or research infrastructure becomes unavailable to many projects at once',text:'The outage hits a bottleneck resource or common access layer. Even unaffected laboratories lose the capability they were depending on remotely.'},
        {id:'compound',label:'Compound',title:'The cyberattack also compromises the cloud or identity layer needed for recovery',text:'Recovery is no longer a simple restore. Third-party cloud, software or access dependencies become part of the incident and prolong the research outage.'}
      ],
      counterRoles:[
        ['Federated compute access',{any:[/federation platform.*supercomput/,/network of national competence centres for hpc/],preferSource:/EuroHPC/}],
        ['Software-vulnerability governance',{any:[/governing software vulnerabilities/,/cyber.*governance/,/cybersecurity challenges/],preferSource:/SIPRI|EUISS/}],
        ['Multiple European facilities',{any:[/open access to jrc research infrastructures/,/european research infrastructures/],preferSource:/Joint Research Centre|European Commission/}],
        ['Digital-autonomy measures',{any:[/digital autonomy and resilience/,/tech sovereignty package/,/autonomy through partnerships/]}]
      ]
    },
    direct_conflict_research_corridor:{
      variants:[
        {id:'contained',label:'Contained',title:'The corridor closes, but emergency integration keeps most research teams working',text:'People move and facilities are disrupted, yet host institutions, remote access and European support absorb a large share of the immediate loss.'},
        {id:'core',label:'Core shock',title:'Escalation removes people, facilities and collaborations from the same research corridor',text:'The system loses several kinds of capacity at once: laboratories, local data, project tasks and researchers who cannot simply be replaced by grant extensions.'},
        {id:'compound',label:'Compound',title:'The conflict shock becomes a long-term capability drain',text:'Temporary displacement becomes permanent migration, cohorts of young researchers are lost, and European partners inherit projects without the local infrastructure or tacit knowledge that made them work.'}
      ],
      counterRoles:[
        ['European support for Ukrainian science',{any:[/support.*ukrainian science/,/supporting the ukrainian research ecosystem/,/role of science in ukraine.*recovery/],preferSource:/ALLEA/}],
        ['Integration into European structures',{any:[/european integration.*r&d institutions.*ukraine/,/integration.*european.*research.*area.*ukraine/,/ukraine.*european research area/]}],
        ['Cross-border researcher mobility',{any:[/fifth freedom/,/researcher mobility/],preferSource:/European Citizen Action Service|European Commission/}],
        ['International collaboration capacity',{any:[/international cooperation in research and innovation/,/science diplomacy/],preferSource:/European Commission|European Research Council/}]
      ]
    },
    direct_collaboration_restriction:{
      variants:[
        {id:'contained',label:'Contained',title:'Restrictions stay limited to sensitive fields and most collaboration survives',text:'New security rules narrow the permissible perimeter but leave enough legal routes, programme association and mobility for ordinary research to continue.'},
        {id:'core',label:'Core shock',title:'A partner changes grant, participation or data rules and live projects become impossible',text:'The administrative rule change lands faster than consortia can redesign contracts, data flows or staffing.'},
        {id:'compound',label:'Compound',title:'Partner restrictions and European security screening reinforce each other into de facto decoupling',text:'Neither side formally ends cooperation, but reciprocal checks, delays and exclusions make collaboration too uncertain to design around.'}
      ],
      counterRoles:[
        ['EU science-diplomacy framework',{any:[/framework for science diplomacy/,/science diplomacy/],preferSource:/Council of the European Union|European Commission/}],
        ['Expanding Horizon associations',{any:[/successfully conclude horizon europe negotiations/,/horizon europe association/,/association joint committee/],preferSource:/European Commission/}],
        ['Global cooperation architecture',{any:[/global approach to research and innovation/,/international cooperation in research and innovation/],preferSource:/European Commission/}],
        ['Open-science / borderless-science norm',{any:[/science knows no borders/,/safeguard science as a global public good/],preferSource:/ALLEA|Royal Society/}]
      ]
    },
    measurement_mid_river:{
      variants:[
        {id:'contained',label:'Contained',title:'Open research-information infrastructure becomes load-bearing before the commercial layer fails',text:'OpenAlex, Barcelona Declaration infrastructure and reformed assessment practice mature quickly enough that Europe can switch measurement systems with disruption but without losing policy sight.'},
        {id:'core',label:'Core shock',title:'Europe loses its rented measurement layer while the replacement is still transitional',text:'The proprietary layer is repriced, restructured or constrained just as institutions have begun abandoning the old metric regime but have not yet made the open alternative operationally sovereign.'},
        {id:'compound',label:'Compound',title:'The measurement failure lands during FP10/MFF bargaining',text:'The shock reaches beyond bibliometrics: innovation, widening and programme-impact arguments become harder to defend precisely when comparative evidence is politically most valuable.'}
      ],
      counterRoles:[
        ['Barcelona Declaration / open information',{any:[/barcelona declaration on open research information/,/open research information/],preferTitle:/Barcelona Declaration/}],
        ['Open-science institutional push',{any:[/open science as a pillar/,/stronger action on open science/],preferSource:/ALLEA/}],
        ['Assessment reform implementation',{any:[/implementing responsible research assessment/,/progress in reforming research assessment/],preferSource:/Science Europe|European Commission|ERA Portal/}],
        ['Open bibliometric alternative',{any:[/openalex vs scopus/,/openalex/],preferTitle:/OpenAlex/}]
      ]
    },
    compute_control_plane:{
      variants:[
        {id:'contained',label:'Contained',title:'A foreign control-layer restriction is isolated and European federation keeps access alive',text:'One vendor or service becomes unavailable, but the workload can be shifted across European systems and alternative software or access paths.'},
        {id:'core',label:'Core shock',title:'Europe owns the machine but loses permission to use a critical software, cloud or chip layer',text:'Physical sovereignty is not operational sovereignty: a foreign-controlled dependency disables a European asset without damaging it.'},
        {id:'compound',label:'Compound',title:'Chip, cloud and software restrictions arrive as one coordinated control-plane shock',text:'Substitution becomes much harder because the layers needed to replace one dependency are themselves constrained by another.'}
      ],
      counterRoles:[
        ['EuroHPC federation',{any:[/federation platform.*supercomput/,/network of national competence centres for hpc/],preferSource:/EuroHPC/}],
        ['European tech-sovereignty package',{any:[/tech sovereignty package/,/strengthening europe.*tech sovereignty/],preferSource:/European Commission/}],
        ['European-owned compute expansion',{any:[/ai gigafactor/,/resource for ai science in europe/,/quantum computer.*sovereignty/],preferSource:/European Commission|EuroHPC/}],
        ['Open access to European infrastructures',{any:[/open access to jrc research infrastructures/,/european research infrastructures/],preferSource:/Joint Research Centre|European Commission/}]
      ]
    },
    pilot_lines_materials:{
      variants:[
        {id:'contained',label:'Contained',title:'Pilot lines ration scarce inputs and qualify substitutes before production is affected',text:'The research layer takes the first hit but also acts as a buffer: scarce material is prioritised for experiments that accelerate substitution.'},
        {id:'core',label:'Core shock',title:'Specialised material restrictions stop research pilot lines first',text:'Low-volume, high-specificity inputs disappear from experimentation and qualification, delaying the evidence needed to adapt industrial processes.'},
        {id:'compound',label:'Compound',title:'The pilot-line stoppage prevents Europe from engineering around the later factory shortage',text:'A supply shock and an innovation shock become the same event: the capability that should discover substitutes is itself starved of inputs.'}
      ],
      counterRoles:[
        ['Chips Act / semiconductor capacity',{any:[/chips act 2\.0/,/second semiconductor push/,/semiconductor.*strategic autonomy/]}],
        ['European pilot-line investment',{any:[/experimental pilot lines/,/quantum-testing infrastructure/,/pilot lines/],preferSource:/EuroHPC/}],
        ['Strategic-autonomy policy',{any:[/strategic autonomy and resilience/,/clean industrial future/,/tech sovereignty package/]}],
        ['Research infrastructure access',{any:[/open access to jrc research infrastructures/,/research infrastructures/],preferSource:/European Commission|Joint Research Centre/}]
      ]
    },
    association_sanctions:{
      variants:[
        {id:'contained',label:'Contained',title:'Association survives because projects can reroute payments, data and equipment',text:'The legal relationship is preserved and practical workarounds keep enough transaction channels open for most consortia.'},
        {id:'core',label:'Core shock',title:'Horizon association remains legally intact while operational layers stop working',text:'Payments, cloud access, data movement or equipment transfer fail underneath the formal agreement, leaving projects associated on paper but unusable in practice.'},
        {id:'compound',label:'Compound',title:'Sanctions, export controls and digital legal orders hollow out several association layers at once',text:'No single prohibition kills the programme. The combined frictions make normal project execution impossible and create a de facto suspension without a diplomatic decision.'}
      ],
      counterRoles:[
        ['EU science-diplomacy framework',{any:[/framework for science diplomacy/,/science diplomacy/],preferSource:/Council of the European Union|European Commission/}],
        ['Diversified association network',{any:[/horizon europe association/,/association joint committee/,/successfully conclude horizon europe negotiations/],preferSource:/European Commission/}],
        ['Global R&I cooperation policy',{any:[/global approach to research and innovation/,/international cooperation in research and innovation/],preferSource:/European Commission/}],
        ['Open strategic partnership logic',{any:[/shared gains, secure links/,/autonomy through partnerships/]}]
      ]
    },
    talent_security_collision:{
      variants:[
        {id:'contained',label:'Contained',title:'Europe’s talent offers and mobility reforms offset the extra security friction',text:'Screening becomes slower, but stronger career offers, Fifth Freedom measures and dedicated attraction programmes keep the net flow of researchers stable.'},
        {id:'core',label:'Core shock',title:'External talent pull and slower European trust decisions leave new facilities short of people',text:'The bottleneck moves from capital to labour. Europe has machines, grants and infrastructure but cannot staff them at the pace the investment plan assumed.'},
        {id:'compound',label:'Compound',title:'The talent shortage concentrates in AI, quantum and widening regions',text:'The most mobile specialists cluster in already-strong centres or leave Europe, while new strategic infrastructure and weaker regions compete for a shrinking pool.'}
      ],
      counterRoles:[
        ['Choose Europe / talent attraction',{any:[/choose europe for science/,/attract and retain research talent/,/research talent is europe.*strategic advantage/],preferSource:/European Commission|ALLEA/}],
        ['Researcher mobility reforms',{any:[/fifth freedom/,/researcher mobility/],preferSource:/European Citizen Action Service|European Commission/}],
        ['European training pipeline',{any:[/eumaster4hpc/,/postdoc and doctoral student positions/,/research careers/]}],
        ['Retention policy',{any:[/keep brightest tech talents at home/,/mitigate brain drain/],preferSource:/European Commission/}]
      ]
    },
    clinical_data_order:{
      variants:[
        {id:'contained',label:'Contained',title:'Federated health-data architecture routes around one blocked provider or jurisdiction',text:'The legal order hits a service, but data stays within a European federated design and trial teams can continue through alternative compliant access paths.'},
        {id:'core',label:'Core shock',title:'A third-country data order breaks the evidence chain of a multi-country trial',text:'Laboratories remain open, but lawful pooling and analysis stop. The trial continues physically while losing the cross-border evidence that makes it scientifically usable.'},
        {id:'compound',label:'Compound',title:'The data freeze lands in a rare-disease or small-population network with no national substitute',text:'The legal interruption becomes a capability loss because no single country has enough patients, observations or specialist infrastructure to recreate the dataset alone.'}
      ],
      counterRoles:[
        ['European Health Data Space alignment',{any:[/european health data space/,/federated health data access/],preferTitle:/federated health data|Health Data Space/}],
        ['Coordinated trial networks',{any:[/coordinated clinical trial networks/,/improving trial delivery/],preferSource:/Clinical Kidney Journal/}],
        ['Open-science data sharing',{any:[/data sharing in the open science landscape/,/open science/],preferTitle:/data sharing|Open Science/}],
        ['European digital autonomy',{any:[/digital autonomy and resilience/,/tech sovereignty package/,/cloud and ai development/],preferSource:/European Commission/}]
      ]
    }
  };

  function findScenario(data,id){
    const all=[...(Scenarios?.buildDirect?.(data)||[]),...(Scenarios?.build?.(data)||[]),...(Scenarios?.buildDynamic?.(data)||[])];
    return all.find(s=>s.id===id)||null;
  }
  function counterEvidence(data,scenario,profile){
    if(Array.isArray(scenario?.againstEvidence)&&scenario.againstEvidence.length)return scenario.againstEvidence.slice().sort((a,b)=>(b.quality||0)-(a.quality||0)).slice(0,5);
    const rows=corpus(data),used=new Set((scenario.evidence||[]).map(e=>e.row._row)),out=[];
    for(const [role,spec] of profile.counterRoles||[]){const row=pick(rows,spec,used);if(row)out.push({role,row,quality:qualityScore(row)})}
    // If a genuinely double-edged row is already part of the shock case, allow it
    // back only when the independent counter search found too little evidence.
    if(out.length<2){
      const used2=new Set();
      for(const [role,spec] of profile.counterRoles||[]){const row=pick(rows,spec,used2);if(row&&!out.some(e=>e.row._row===row._row))out.push({role,row,quality:qualityScore(row)})}
    }
    return out.sort((a,b)=>b.quality-a.quality).slice(0,5);
  }
  const GENERIC_COUNTER_ROLES=[
    ['European substitution / diversification',{any:[/diversif/,/substitut/,/alternative supplier/,/strategic autonomy/,/resilien/]}],
    ['Shared or federated European capacity',{any:[/federat/,/shared infrastructure/,/research infrastructure/,/eurohpc/,/open access/]}],
    ['European policy capacity',{any:[/european commission/,/framework programme/,/horizon europe/,/funding/,/procurement/,/regulatory sandbox/]}],
    ['Open or international cooperation channel',{any:[/science diplomacy/,/international cooperation/,/association/,/open science/,/research collaboration/]}],
    ['Talent / capability reinforcement',{any:[/attract and retain/,/research talent/,/skills/,/training/,/capacity building/]}]
  ];
  function genericProfile(scenario){
    return {
      variants:[
        {id:'contained',label:'Contained',title:`Contained: ${scenario.title}`,text:'The mechanism appears, but redundancy, substitution, workarounds or policy response keep it local and temporary.'},
        {id:'core',label:'Core shock',title:scenario.title,text:scenario.plainly||'The identified mechanism reaches the capability described by the supporting evidence.'},
        {id:'compound',label:'Compound',title:`Compound: ${scenario.title}`,text:`The same mechanism lands together with an adjacent dependency or policy failure. ${scenario.secondOrder||''}`.trim()}
      ],
      counterRoles:GENERIC_COUNTER_ROLES
    };
  }
  function build(data,id){
    const scenario=findScenario(data,id);
    if(!scenario)return null;
    const profile=PROFILES[id]||genericProfile(scenario);
    return {
      scenario,
      variants:profile.variants,
      forEvidence:(scenario.evidence||[]).slice(0,7),
      againstEvidence:counterEvidence(data,scenario,profile)
    };
  }
  function scenarioIdForRealised(x){
    const t=low([x?.title,x?.headline,x?.what,x?.core_message,x?.summary,x?.lens?.shock_family].join(' '));
    if(/cyber|software vulnerab|digital outage/.test(t))return 'direct_cyber_infrastructure';
    if(/armed conflict|war |war-|invasion|refugee|displac/.test(t))return 'direct_conflict_research_corridor';
    if(/research collaboration|grant restriction|participation ban|data exchange/.test(t))return 'direct_collaboration_restriction';
    if(/export|trade disruption|critical raw material|chip|semiconductor|dual-use/.test(t))return 'direct_materials_cutoff';
    return null;
  }
  return {build,profiles:PROFILES,scenarioIdForRealised};
});
