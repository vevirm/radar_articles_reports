(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory(require('../reader_rank.js'));
  else root.RadarShockScenarios=factory(root.RadarReaderRank);
})(typeof globalThis!=='undefined'?globalThis:this,function(ReaderRank){
  'use strict';
  const clean=v=>String(v||'').replace(/\s+/g,' ').trim();
  const low=v=>clean(v).toLowerCase();
  const dateValue=v=>{const n=Date.parse(v||'');return Number.isFinite(n)?n:0};
  const qualityScore=x=>Math.max(0,Math.min(100,Number(ReaderRank?.scoreFor?.(x))||0));
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
    },
    {
      id:'energy_compute_rationing',
      title:'An external energy shock turns Europe’s new AI and supercomputing capacity into rationed research access',
      plainly:'Owning compute does not guarantee usable compute if electricity becomes the scarce imported input and research workloads are the easiest demand to postpone.',
      secondOrder:'The projects most dependent on repeated high-end runs lose time non-linearly: queues grow, model-training cycles stretch, and smaller teams are crowded out first.',
      hidden:'Energy security and research infrastructure are usually monitored in different systems. The coupling appears only when sovereign compute becomes large enough for power availability and price to determine scientific access.',
      minEvidence:4,
      roles:[
        ['European compute build-out',{any:[/ai gigafactor/,/supercomput/,/resource for ai science in europe/,/eurohpc/],preferSource:/European Commission|EuroHPC/}],
        ['Research access dependency',{any:[/research access.*compute/,/access to.*supercomput/,/research infrastructure/,/computing capacity/]}],
        ['Energy / grid exposure',{any:[/energy supply/,/electricity/,/grid /,/power supply/,/energy security/,/data cent(?:er|re).*energy/]}],
        ['External shock mechanism',{any:[/commodity price shock/,/price spike/,/supply disruption/,/energy supply disruption/,/blackout/,/power outage/]}],
        ['Strategic dependency',{any:[/strategic depend/,/external depend/,/non-european suppliers/,/import dependence/]}],
      ],
      reasoning:[
        'Europe is deliberately concentrating more research capability in AI factories, supercomputers and shared compute.',
        'That capacity converts electricity into research throughput; access is therefore partly an energy-allocation question.',
        'The corpus separately treats energy supply, grids and external dependence as resilience issues rather than research issues.',
        'Join the layers and an external energy shock can leave the machines physically intact but make scientific access economically or operationally rationed.',
        'The loss is initially invisible in capital-stock measures because Europe still owns the infrastructure.'
      ]
    },
    {
      id:'scaleup_acquisition_drain',
      title:'Europe finances a strategic deep-tech scale-up, then loses the capability through acquisition rather than failure',
      plainly:'A company can remain successful while Europe loses control: foreign acquisition can move key IP, product decisions, data and high-value R&D out of the European innovation system.',
      secondOrder:'Public R&D and scale-up support can end up increasing the quality of assets available for acquisition unless ownership, procurement and European demand scale together.',
      hidden:'Innovation policy counts a funded scale-up as a success; economic-security policy watches hostile or sensitive investment. The seam is the ordinary successful acquisition that is legal, commercial and strategically consequential.',
      minEvidence:4,
      roles:[
        ['European scale-up ambition',{any:[/scale-?up/,/startup/,/venture capital/,/deep tech/]}],
        ['Foreign capital / acquisition channel',{any:[/foreign investment/,/acquisition/,/foreign ownership/,/foreign capital/]}],
        ['Research-to-market conversion',{any:[/commerciali[sz]ation/,/technology transfer/,/procurement/,/innovation ecosystem/]}],
        ['Strategic technology capability',{any:[/critical technolog/,/strategic technolog/,/semiconductor/,/quantum/,/artificial intelligence/]}],
        ['Economic-security / screening layer',{any:[/investment screening/,/economic security/,/strategic autonomy/,/technology sovereignty/]}],
      ],
      reasoning:[
        'The corpus treats R&D, scale-up finance and commercialisation as a pathway to European capability.',
        'It separately treats foreign investment and screening as a security issue.',
        'A successful company can cross from one policy file to the other without any operational failure.',
        'If the acquisition moves control over IP, product roadmaps or R&D location, Europe can lose the capability after paying to create it.',
        'The shock is therefore a success event in company statistics but a loss event in system capability.'
      ]
    },
    {
      id:'standards_interoperability_split',
      title:'A standards split makes a European research network technically open but practically unable to collaborate',
      plainly:'No border closes and no grant is cancelled; incompatible standards, certification or data rules can make equipment and research outputs stop fitting together.',
      secondOrder:'European teams spend scarce research time maintaining parallel compliance and conversion layers, while smaller institutions quietly exit international networks.',
      hidden:'Standards are usually treated as market governance and collaboration as science policy. Interoperability is the hidden infrastructure connecting them.',
      minEvidence:4,
      roles:[
        ['Standards / regulatory layer',{any:[/standardisation/,/standardization/,/technology standards/,/regulatory framework/,/standards and geopolitics/]}],
        ['International collaboration',{any:[/international research collaboration/,/scientific collaboration/,/science diplomacy/,/research cooperation/]}],
        ['Shared data / infrastructure',{any:[/research data/,/data infrastructure/,/research infrastructure/,/shared facilit/]}],
        ['External legal or technology pressure',{any:[/third-country laws/,/extraterritorial/,/technology competition/,/strategic competition/]}],
        ['European strategic capability',{any:[/strategic autonomy/,/technology sovereignty/,/critical technolog/,/economic security/]}],
      ],
      reasoning:[
        'Research collaboration increasingly depends on technical standards for data, equipment, software and certification.',
        'The corpus separately shows standards and regulation becoming instruments of geopolitical competition.',
        'A standards split can therefore break collaboration without a formal political rupture.',
        'Projects remain funded and institutions remain partnered, but data and equipment require parallel conversion or cannot be mutually recognised.',
        'That makes interoperability itself a strategic research capability.'
      ]
    },
    {
      id:'open_science_security_collision',
      title:'Europe’s open-science architecture and research-security rules collide in a strategically sensitive field',
      plainly:'The same openness that makes a European network scientifically valuable can become the reason access is restricted once the field is reclassified as sensitive or dual-use.',
      secondOrder:'Institutions pre-emptively narrow collaboration beyond what the rules require, producing a chilling effect that is larger than the formal restriction.',
      hidden:'Open science is managed as an access and values agenda; research security is managed as a protection agenda. The shock appears when one dataset, facility or field suddenly belongs to both.',
      minEvidence:4,
      roles:[
        ['Open-science / shared-information architecture',{any:[/open science/,/open research information/,/open access/,/data sharing/]}],
        ['Research-security tightening',{any:[/research security/,/knowledge security/,/foreign interference/]}],
        ['Sensitive or dual-use field',{any:[/dual-use/,/dual use/,/critical technolog/,/sensitive research/]}],
        ['International collaboration dependence',{any:[/international research collaboration/,/research cooperation/,/science diplomacy/]}],
        ['European shared infrastructure',{any:[/research infrastructure/,/shared facilit/,/eosc/,/federated data/]}],
      ],
      reasoning:[
        'Europe is building research systems around openness, federation and cross-border reuse.',
        'At the same time, security policy is expanding screening around sensitive knowledge and dual-use technologies.',
        'Those agendas can coexist until a previously open field is recategorised as strategically sensitive.',
        'The same shared infrastructure then has to support openness and restriction at once, creating abrupt access and collaboration changes.',
        'The largest effect may come from institutional over-compliance rather than the formal rule itself.'
      ]
    }
  ];

  function buildFromTemplates(data,templates){
    const rows=corpus(data),out=[];
    for(const t of templates){
      const used=new Set(),evidence=[];
      for(const [role,spec] of t.roles){const row=pick(rows,spec,used);if(row)evidence.push({role,row,quality:qualityScore(row)})}
      if(evidence.length<(t.minEvidence||t.roles.length))continue;
      const qs=evidence.map(e=>e.quality),best=Math.max(...qs),avg=qs.reduce((a,b)=>a+b,0)/qs.length;
      // A cross-evidence shock must be anchored in at least one very strong source and
      // supported by a credible evidence set. Low-ranked rows can corroborate, not lead.
      if(best<82||avg<68)continue;
      evidence.sort((a,b)=>b.quality-a.quality);
      out.push({...t,evidence,coverage:evidence.length+'/'+t.roles.length,evidenceQuality:{best,average:Math.round(avg)}});
    }
    return out;
  }
  function build(data){return buildFromTemplates(data,TEMPLATES)}
  function buildDirect(data){return buildFromTemplates(data,DIRECT_TEMPLATES)}
  return {build,buildDirect,templates:TEMPLATES,directTemplates:DIRECT_TEMPLATES,rowText};
});
