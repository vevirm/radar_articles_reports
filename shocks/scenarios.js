(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.RadarShockScenarios=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const clean=v=>String(v||'').replace(/\s+/g,' ').trim();
  const low=v=>clean(v).toLowerCase();
  const dateValue=v=>{const n=Date.parse(v||'');return Number.isFinite(n)?n:0};
  function rowText(x){return low([x.title,x.headline,x.what,x.core_message,x.summary,x.relevance_note,x.why_it_matters,x.source].join(' '))}
  function rx(v){return v instanceof RegExp?v:new RegExp(String(v),'i')}
  function matches(x,spec){
    const t=rowText(x);
    if(spec.all&&spec.all.some(p=>!rx(p).test(t)))return false;
    if(spec.any&&spec.any.length&&!spec.any.some(p=>rx(p).test(t)))return false;
    if(spec.none&&spec.none.some(p=>rx(p).test(t)))return false;
    return true;
  }
  function score(x,spec){
    const t=rowText(x);let n=dateValue(x.date)/86400000;
    for(const p of spec.all||[])if(rx(p).test(t))n+=35;
    for(const p of spec.any||[])if(rx(p).test(t))n+=18;
    if(spec.preferSource&&rx(spec.preferSource).test(clean(x.source)))n+=80;
    if(spec.preferTitle&&rx(spec.preferTitle).test(clean(x.title||x.headline)))n+=120;
    if(x.new_this_scan)n+=8;
    return n;
  }
  function corpus(data){
    const out=[];
    for(const [key,prefix] of [['strand_a','A'],['strand_c','C']]){
      const xs=Array.isArray(data?.[key])?data[key]:[];
      xs.forEach((x,i)=>{if(x&&typeof x==='object')out.push({...x,_row:`${prefix}${String(i+1).padStart(3,'0')}`,_strand:prefix})});
    }
    return out;
  }
  function pick(rows,spec,used){
    const candidates=rows.filter(x=>!used.has(x._row)&&matches(x,spec)).sort((a,b)=>score(b,spec)-score(a,spec));
    const chosen=candidates[0];if(chosen)used.add(chosen._row);return chosen||null;
  }

  const DIRECT_TEMPLATES=[
    {
      id:'direct_materials_cutoff',direct:true,
      title:'A critical-material or advanced-chip cutoff suddenly removes inputs Europe cannot replace fast enough',
      plainly:'An export restriction does not need to hit every product: a small set of controlled materials or advanced chips can stop strategic R&I programmes that have no qualified substitute.',
      secondOrder:'The damage moves upstream from production into experimentation: prototypes, qualification runs and scale-up schedules slip before headline industrial output does.',
      minEvidence:4,
      roles:[
        ['Critical-material coercion',{any:[/critical raw material weapon/,/critical.raw.material.*export control/,/critical materials.*depend/],preferSource:/EUISS|JRC|Carnegie/}],
        ['Semiconductor dependence',{any:[/supply chain dependencies on china, taiwan and the united states/,/semiconductor geopolitical risk/,/geopolitics of ai chips/],preferSource:/IAI|Institut Montaigne|MIT/}],
        ['European compute / strategic-tech build-out',{any:[/ai gigafactor/,/resource for ai science in europe/,/supercomput/,/quantum computer/],preferSource:/European Commission|EuroHPC/}],
        ['Export-control exposure',{any:[/export control risks/,/dual-use.*export control/,/economic coercion/,/export restriction/],preferSource:/SIPRI|ECFR|EUISS/}],
      ],
      reasoning:[
        'Europe is expanding compute, semiconductor and other strategic-technology capacity.',
        'The corpus simultaneously documents hard dependencies on imported chips and critical materials.',
        'Export controls and economic coercion provide a direct external mechanism for cutting those inputs quickly.',
        'The immediate shock is therefore straightforward: programmes with no qualified substitute stop or slow until a new input is certified.'
      ]
    },
    {
      id:'direct_cyber_infrastructure',direct:true,
      title:'A major cyberattack takes a shared European research infrastructure or compute service offline',
      plainly:'A shared facility can become a single point of failure: if its software, cloud layer or access system is disabled, many projects lose capability at once.',
      secondOrder:'Teams with no local substitute lose experimental time first, and the queue created during the outage continues long after the systems return.',
      minEvidence:4,
      roles:[
        ['Software-vulnerability / cyber risk',{any:[/software vulnerabilities/,/cybersecurity challenges/,/cybersecurity risks/],preferSource:/SIPRI|EUISS/}],
        ['Cloud and digital dependence',{any:[/cloud and ai development/,/non-european suppliers/,/digital infrastructure.*innovation capacity/],preferSource:/European Commission|Economics of Innovation/}],
        ['Shared research infrastructure',{any:[/research infrastructures as bottleneck resources/,/open access to jrc research infrastructures/,/european research infrastructures/],preferSource:/EPJ Research Infrastructures|Joint Research Centre|European Commission/}],
        ['Compute concentration / access',{any:[/supercomput/,/resource for ai science in europe/,/ai gigafactor/],preferSource:/EuroHPC|European Commission|Bruegel/}],
      ],
      reasoning:[
        'European R&I increasingly relies on shared compute, data and specialised facilities.',
        'The corpus treats some of those infrastructures explicitly as bottleneck resources.',
        'It also documents software-vulnerability governance, cybersecurity exposure and cloud dependence.',
        'A serious cyber incident can therefore create an immediate multi-project outage without destroying any laboratory building.'
      ]
    },
    {
      id:'direct_conflict_research_corridor',direct:true,
      title:'An armed-conflict escalation closes a research corridor and displaces people, facilities and collaborations',
      plainly:'War can remove research capacity in one move: laboratories become inaccessible, researchers move, and international partners inherit projects they were not designed to carry alone.',
      secondOrder:'Temporary emergency support becomes a structural part of the European research system, while affected fields lose cohorts of early-career researchers and locally held data.',
      minEvidence:4,
      roles:[
        ['War-damaged research ecosystem',{any:[/ukrainian research ecosystem/,/impact of the war.*research infrastructure/,/war-related risks.*research/],preferSource:/ALLEA|International Science Journal/}],
        ['European integration of affected science',{any:[/integration into the european research area/,/ukraine.*european research area/,/supporting ukrainian science/],preferSource:/ALLEA|ERA Portal/}],
        ['Researcher mobility dependence',{any:[/fifth freedom/,/researcher mobility/,/cross-border mobility/],preferSource:/European Citizen Action Service|European Commission/}],
        ['International collaboration dependence',{any:[/international research collaboration/,/international cooperation.*research/,/science diplomacy/],preferSource:/ALLEA|European Commission|European Research Council/}],
      ],
      reasoning:[
        'The corpus already shows that armed conflict can damage research infrastructure and force support for displaced scientific capacity.',
        'European programmes increasingly integrate that capacity through shared facilities, mobility and collaborative projects.',
        'A further escalation can abruptly close physical and institutional access even when grants remain legally alive.',
        'The shock is obvious but consequential: the network has to absorb missing people, facilities and project tasks at the same time.'
      ]
    },
    {
      id:'direct_collaboration_restriction',direct:true,
      title:'A major partner abruptly restricts international grants, researcher participation or data exchange',
      plainly:'Research collaboration can be broken by administrative rules rather than a diplomatic rupture: a grant condition, participation ban or data rule can make joint work impossible almost immediately.',
      secondOrder:'European teams become more cautious about designing projects around partners whose domestic rules can change the collaboration after awards are made.',
      minEvidence:4,
      roles:[
        ['External restriction on collaboration',{any:[/restrictions.*international research collaboration/,/white house.*international research collaboration/,/grant restrictions/],preferSource:/ALLEA/}],
        ['EU dependence on mobility',{any:[/fifth freedom/,/researcher mobility/,/free circulation of knowledge/],preferSource:/European Citizen Action Service|ERA Portal/}],
        ['International programme architecture',{any:[/horizon europe.*association/,/international cooperation in research and innovation/,/science diplomacy/],preferSource:/European Commission|European Research Council/}],
        ['Research-security friction',{any:[/research security/,/knowledge security/,/dual-use/],preferSource:/ALLEA|SIPRI|HCSS/}],
      ],
      reasoning:[
        'The corpus contains a live example of proposed third-country restrictions on international research collaboration.',
        'European strategy at the same time depends on researcher mobility, programme association and cross-border science diplomacy.',
        'Research-security rules add another layer of participation and trust conditions.',
        'A sudden external rule change can therefore stop a collaboration even when neither government formally ends the partnership.'
      ]
    }
  ];

  const TEMPLATES=[
    {
      id:'measurement_mid_river',
      title:'Europe loses the ability to measure its own research system — mid-transition',
      plainly:'Europe agreed to stop trusting the old ruler before it finished building the new one — and the old ruler is rented from someone else.',
      secondOrder:'Widening countries, whose case for funding rests heavily on comparative indicators, lose their argument first.',
      hidden:'Assessment reform, research-information infrastructure and geopolitical dependency are filed as different problems. The exposure only appears when the transition timing is treated as part of the dependency.',
      minEvidence:6,
      roles:[
        ['Research-information concentration',{any:[/world of data in a few hands/,/research information.*few hands/,/data.*few hands/],preferSource:/European Research Council/}],
        ['Open replacement still being benchmarked',{any:[/openalex.*scopus/,/barcelona declaration.*open research information/]}],
        ['Assessment reform moving into implementation',{any:[/reforming research assessment/,/responsible research assessment/,/research assessment reform/]}],
        ['Third-country legal leverage over digital dependencies',{any:[/extraterritorial/,/economic coercion/,/non-european suppliers/]}],
        ['Indicator-dependent EU monitoring',{any:[/innovation scoreboard/,/widening.*indicator/,/indicator.*widening/],preferSource:/European Commission|ERA Portal/}],
        ['Budget / FP10 timing pressure',{any:[/next mff/,/fp10/,/framework programme/]}],
      ],
      reasoning:[
        'Assessment reform and research-information reform are moving at the same time, but they are normally treated as separate files.',
        'The replacement information layer exists, yet the corpus still contains direct OpenAlex-versus-Scopus benchmarking and open-information mobilisation: substitution is not finished.',
        'Elsewhere, the corpus shows that third-country legal orders and commercial dependencies can become geopolitical leverage over European digital infrastructure.',
        'EU monitoring, widening arguments and programme defence still depend on comparative indicators during the next budget fight.',
        'Join the timing, not just the topics: the shock is simultaneous failure of the rented old measurement layer and the not-yet-load-bearing replacement.'
      ]
    },
    {
      id:'compute_control_plane',
      title:'Europe owns the AI factory — but a foreign control layer makes it unusable overnight',
      plainly:'Owning the building is not sovereignty if the accelerators, cloud layer or legal permission to run them can still be switched off elsewhere.',
      secondOrder:'Smaller universities and widening-region users are pushed out first because they have the least bargaining power and the fewest substitute routes.',
      hidden:'Compute ownership is usually counted as sovereignty, while cloud, chips and legal jurisdiction are counted elsewhere. The seam between physical ownership and operational control is easy to miss.',
      minEvidence:5,
      roles:[
        ['EU compute build-out',{any:[/ai gigafactor/,/resource for ai science in europe/,/eurohpc.*supercomputer/,/compute gap/],preferSource:/European Commission|EuroHPC|Bruegel/,preferTitle:/RAISE|AI gigafactor|compute gap|supercomputer/}],
        ['Cloud / supplier dependence',{any:[/cloud and ai development/,/non-european suppliers/,/deeper us tech reliance/,/cloud.*depend/]}],
        ['Chip supply dependence',{any:[/supply chain dependencies on china, taiwan and the united states/,/geopolitics of ai chips/,/chips.*depend/],preferSource:/IAI|MIT|Bruegel/}],
        ['External coercive mechanism',{any:[/economic coercion/,/extraterritorial/,/export control/,/export restriction/]}],
        ['Research access layer',{any:[/opens access to its quantum computers/,/federation platform.*supercomput/,/open access.*research infrastructures/],preferSource:/EuroHPC|Joint Research Centre/}],
      ],
      reasoning:[
        'The corpus treats sovereign compute, cloud dependence and chip dependence as adjacent but separate policy problems.',
        'The infrastructure build-out increases the amount of European research routed through a small number of high-value compute systems.',
        'Those systems still rely on imported chips, software and cloud/control layers that can sit under third-country law.',
        'The coercion evidence supplies the missing mechanism: access can become conditional without any physical damage to the European facility.',
        'The shock therefore lands as an access failure inside an asset Europe still physically owns.'
      ]
    },
    {
      id:'pilot_lines_materials',
      title:'A raw-material restriction stops Europe’s research pilot lines before it stops its factories',
      plainly:'The first broken production line may be a research line: tiny-volume, specialised inputs are easy to deprioritise and hard to substitute.',
      secondOrder:'Standards, prototypes and qualification evidence arrive late, so the industrial shortage becomes harder to fix even after material supply recovers.',
      hidden:'Critical-material analysis looks at factories; research-infrastructure analysis looks at access and capacity. The pilot line that links the two rarely appears in either risk register.',
      minEvidence:5,
      roles:[
        ['Material coercion',{any:[/critical raw material weapon/,/critical raw materials.*china/,/export restriction/]}],
        ['Semiconductor dependence',{any:[/chips act/,/semiconductor.*depend/,/semiconductor geopolitical risk/],preferSource:/IAI|Institut Montaigne|Bruegel/}],
        ['Quantum / chip pilot infrastructure',{any:[/pilot lines/,/quantum-testing infrastructure/,/quantum experimental pilot lines/]}],
        ['Research-infrastructure bottleneck',{any:[/research infrastructures as bottleneck resources/,/research infrastructure/]}],
        ['Dual-use / export-control coupling',{any:[/dual-use.*export control/,/export controls?.*dual-use/,/export control risks/]}],
      ],
      reasoning:[
        'Raw-material risk is usually framed around industrial production, while research infrastructure is framed around access and capacity.',
        'The corpus also shows Europe building pilot lines and test infrastructure precisely to shorten the path from research to production.',
        'Specialised research inputs are lower-volume than factory inputs and often have fewer qualified substitutes.',
        'An export restriction can therefore hit the experimentation and qualification layer first.',
        'That makes the later factory shortage worse: Europe loses the capability needed to engineer around the missing input.'
      ]
    },
    {
      id:'association_sanctions',
      title:'A partner stays “associated” to Horizon Europe on paper while sanctions make the partnership unusable in practice',
      plainly:'The treaty can survive while payments, cloud access, data exchange or equipment transfer stop working underneath it.',
      secondOrder:'Projects with the most international division of labour become the least resilient precisely because they were designed to pool scarce capabilities.',
      hidden:'Association is tracked as a legal programme status, while sanctions, payment rails, cloud access and export controls are tracked as separate operational risks. A project can therefore fail while every diplomatic status page still looks normal.',
      minEvidence:5,
      roles:[
        ['Association expansion',{any:[/horizon europe.{0,60}association/,/association.{0,60}horizon europe/,/associated countries.{0,80}fp10/],preferSource:/European Commission|ERA Portal/,preferTitle:/Horizon Europe.*association|association.*Horizon Europe|Associated Countries.*FP10/}],
        ['Science-diplomacy architecture',{any:[/science diplomacy/,/international cooperation in research and innovation/]}],
        ['Sanctions / coercion mechanism',{any:[/sanctions/,/economic coercion/,/export control/]}],
        ['Digital legal dependency',{any:[/extraterritorial/,/cloud and ai development/,/non-european suppliers/]}],
        ['Research-security / dual-use friction',{any:[/research security/,/dual-use/,/knowledge security/],preferSource:/ALLEA|European Security|SIPRI|ERA Portal/}],
      ],
      reasoning:[
        'Association is discussed as a legal and programme status; sanctions and export controls are discussed as security instruments.',
        'Actual collaboration depends on mundane transaction layers: money, data, software, equipment and researcher movement.',
        'Those layers can be governed by jurisdictions that are not parties to the research agreement.',
        'A third-country legal order can therefore hollow out a formally intact association overnight.',
        'The surprising part is that the failure appears operational, not diplomatic: the agreement is still there when the collaboration stops.'
      ]
    },
    {
      id:'talent_security_collision',
      title:'A major science partner starts pulling researchers home just as Europe tightens research-security screening',
      plainly:'Europe can lose people without a visa ban: stronger pull abroad plus slower trust decisions at home can create the same result.',
      secondOrder:'New AI, quantum and research-infrastructure investments become capital-rich but researcher-poor.',
      hidden:'Talent attraction and research security are both monitored, but normally as independent policy goals. The shock sits in their timing interaction, where small frictions can change mobile researchers’ choices.',
      minEvidence:5,
      roles:[
        ['External talent pull',{any:[/lure scientists back/,/attract.*researchers.*abroad/,/talent.*competition/],preferSource:/Nature/}],
        ['EU talent-retention push',{any:[/attract and retain research talent/,/research talent is europe/,/keep brightest tech talents at home/]}],
        ['Research-security tightening',{any:[/research security/,/knowledge security/,/foreign interference/],preferSource:/European Security|ALLEA|HCSS/,preferTitle:/research security|knowledge security|foreign interference/}],
        ['International mobility dependence',{any:[/researcher mobility/,/fifth freedom/,/international.*research collaboration/],preferSource:/ECAS|European Commission|ALLEA/,preferTitle:/Fifth Freedom|mobility|international research collaboration/}],
        ['New capability build-out',{any:[/resource for ai science in europe/,/eurohpc/,/quantum computer/,/research infrastructures/],preferSource:/EuroHPC|European Commission/}],
      ],
      reasoning:[
        'Talent policy and research-security policy are both rational when viewed separately.',
        'The corpus now contains stronger external efforts to reclaim scientists at the same time Europe is trying to attract and retain them.',
        'Security screening adds time and uncertainty at the exact points where mobile researchers choose between competing offers.',
        'Infrastructure policy assumes that people will arrive to use the new capacity.',
        'The shock is a coupled labour-market move: no formal closure is required for Europe to discover that its expensive new capacity cannot be staffed.'
      ]
    },
    {
      id:'clinical_data_order',
      title:'A third-country data order freezes a pan-European clinical research network without touching a single laboratory',
      plainly:'The experiments can keep running while the evidence chain breaks: no lawful data movement means no usable multi-country trial.',
      secondOrder:'Rare-disease and small-population research is hit first because it depends most on pooling patients and data across borders.',
      hidden:'Clinical capacity is usually counted in laboratories and trial networks, while digital sovereignty is counted in cloud and data policy. The research capability disappears in the transaction between them.',
      minEvidence:4,
      roles:[
        ['Federated European health data',{any:[/federated health data/,/european health data space/,/health data access/]}],
        ['Clinical-trial network dependence',{any:[/clinical trial networks/,/trial delivery/,/pan-european.*research infrastructure/]}],
        ['Third-country digital legal exposure',{any:[/extraterritorial/,/third-country laws/,/cloud and ai development/]}],
        ['Pharma / health innovation layer',{any:[/pharma/,/medicines/,/biopharma/,/global health/]}],
      ],
      reasoning:[
        'Clinical research infrastructure is increasingly a data network rather than only a collection of laboratories.',
        'The corpus separately documents federated health-data architectures and coordinated trial networks.',
        'It also documents third-country legal exposure in the digital layer Europe relies on.',
        'Join them and the external shock is legal/technical rather than medical: data can no longer move through the infrastructure on which the trial design depends.',
        'The laboratories remain open, which is why the loss of research capability can be missed until the trial evidence fails.'
      ]
    }
  ];

  function buildFromTemplates(data,templates){
    const rows=corpus(data),out=[];
    for(const t of templates){
      const used=new Set(),evidence=[];
      for(const [role,spec] of t.roles){const row=pick(rows,spec,used);if(row)evidence.push({role,row})}
      if(evidence.length<(t.minEvidence||t.roles.length))continue;
      out.push({...t,evidence,coverage:evidence.length+'/'+t.roles.length});
    }
    return out;
  }
  function build(data){return buildFromTemplates(data,TEMPLATES)}
  function buildDirect(data){return buildFromTemplates(data,DIRECT_TEMPLATES)}
  return {build,buildDirect,templates:TEMPLATES,directTemplates:DIRECT_TEMPLATES,rowText};
});
