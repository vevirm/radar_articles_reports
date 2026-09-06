(function(g){
  'use strict';

  /* Eight reader maps are chosen from deliberately different R&I systems.
     The labels are a hierarchy; the live corpus decides which maps are strongest now. */
  const HIERARCHIES=[
    {id:'ai_compute',label:'Artificial intelligence & advanced computing',subs:[
      {label:'European capacity',leaves:[
        {label:'AI factories & supercomputers',terms:['ai factory','ai factories','gigafactory','gigafactories','supercomputer','eurohpc','raise']},
        {label:'Research access to compute',terms:['access to quantum computers','access to supercomput','research access','computing capacity','compute capacity','research infrastructure']}
      ]},
      {label:'External dependencies',leaves:[
        {label:'Chips, cloud & control layers',terms:['cloud','non-european suppliers','chip dependence','semiconductor','gpu','extraterritorial','control layer']}
      ]}
    ]},
    {id:'chips_materials',label:'Chips & critical inputs',subs:[
      {label:'European production',leaves:[
        {label:'Chips Act & pilot lines',terms:['chips act','chip pilot line','semiconductor pilot','pilot lines']},
        {label:'Testing & strategic technology',terms:['quantum testing','quantum experimental','semiconductor research','microelectronics','advanced packaging']}
      ]},
      {label:'Supply exposure',leaves:[
        {label:'Critical materials & export restrictions',terms:['critical raw material','critical materials','rare earth','graphite','export restriction','export control']}
      ]}
    ]},
    {id:'research_security',label:'Research security',subs:[
      {label:'Protect knowledge',leaves:[
        {label:'Foreign interference & trusted research',terms:['foreign interference','trusted research','knowledge security','research security']},
        {label:'Sensitive & dual-use research',terms:['dual-use research','dual use research','sensitive research','dual-use','dual use']}
      ]},
      {label:'Keep collaboration open',leaves:[
        {label:'Screening without isolation',terms:['security screening','international collaboration','international research collaboration','academic freedom','science knows no borders']}
      ]}
    ]},
    {id:'talent',label:'Researchers & skills',subs:[
      {label:'Attract & retain',leaves:[
        {label:'Careers & mobility',terms:['research career','research careers','researcher mobility','mobility','fifth freedom','msca']},
        {label:'Global competition for talent',terms:['research talent','talent competition','lure scientists','attract researchers','retain research talent','brain drain']}
      ]},
      {label:'Capability fit',leaves:[
        {label:'Skills for strategic technologies',terms:['skills','ai skills','digital skills','quantum skills','semiconductor skills','human capital']}
      ]}
    ]},
    {id:'partnerships',label:'International research partnerships',subs:[
      {label:'Programme relationships',leaves:[
        {label:'Horizon association & next framework programme',terms:['horizon europe association','associated countries','association to horizon','fp10']},
        {label:'Science diplomacy & joint research',terms:['science diplomacy','international cooperation in research and innovation','joint research','bilateral research']}
      ]},
      {label:'External pressure',leaves:[
        {label:'Sanctions, coercion & legal reach',terms:['sanctions','economic coercion','extraterritorial','third-country laws','export control']}
      ]}
    ]},
    {id:'funding',label:'Funding & framework programmes',subs:[
      {label:'The next programme',leaves:[
        {label:'FP10 design & research autonomy',terms:['fp10','framework programme 10','next framework programme','horizon europe successor']},
        {label:'Budget & EU long-term funding',terms:['mff','multiannual financial framework','budget','competitiveness fund']}
      ]},
      {label:'Who benefits',leaves:[
        {label:'Widening, cohesion & excellence',terms:['widening','cohesion','widening countries','regional innovation','less developed regions']}
      ]}
    ]},
    {id:'measurement',label:'Research information & assessment',subs:[
      {label:'Measurement reform',leaves:[
        {label:'Responsible research assessment',terms:['responsible research assessment','research assessment reform','reforming research assessment','coara']},
        {label:'Open research information',terms:['open research information','barcelona declaration','openalex','open science']}
      ]},
      {label:'Measurement dependency',leaves:[
        {label:'Indicators, bibliometrics & data ownership',terms:['bibliometric','scopus','innovation scoreboard','indicator','research data','few hands']}
      ]}
    ]},
    {id:'firms',label:'Firms, innovation & scale-up',subs:[
      {label:'Build in Europe',leaves:[
        {label:'Start-ups, scale-ups & venture capital',terms:['startup','start-up','scale-up','scaleup','venture capital','high-growth']},
        {label:'Procurement & commercialisation',terms:['procurement','commercialisation','commercialization','public buying','technology transfer']}
      ]},
      {label:'Compete globally',leaves:[
        {label:'Productivity & innovation performance',terms:['productivity','competitiveness','innovation performance','innovation scoreboard']}
      ]}
    ]},
    {id:'health',label:'Biotech & health research',subs:[
      {label:'Research networks',leaves:[
        {label:'Clinical trials & health data',terms:['clinical trial','clinical trials','health data','european health data space','federated health']},
        {label:'Medicines & life-science innovation',terms:['medicines','pharma','biopharma','biotechnology','life science','life sciences']}
      ]},
      {label:'Security & control',leaves:[
        {label:'Biosecurity, data rules & dependencies',terms:['biosecurity','health data access','data protection','regulatory research','supply dependence']}
      ]}
    ]},
    {id:'quantum',label:'Quantum technologies',subs:[
      {label:'European capability',leaves:[
        {label:'Computers & shared infrastructure',terms:['quantum computer','quantum computers','quantum computing','quantum infrastructure']},
        {label:'Pilot lines & testing',terms:['quantum pilot','quantum experimental','quantum testing','quantum technologies']}
      ]},
      {label:'Geopolitical exposure',leaves:[
        {label:'Controls, supply & access',terms:['quantum export','export controls','supply chain','technology control','dual-use']}
      ]}
    ]},
    {id:'open_facilities',label:'Open science & shared facilities',subs:[
      {label:'Shared infrastructure',leaves:[
        {label:'Facilities & open access',terms:['research infrastructure','research infrastructures','open access to jrc','shared facility','shared facilities']},
        {label:'Federated research data',terms:['eosc','federated data','research data infrastructure','open research information','data space']}
      ]},
      {label:'Openness under pressure',leaves:[
        {label:'Open science & research security',terms:['open science','research security','knowledge security','international collaboration']}
      ]}
    ]},
    {id:'rules',label:'Rules, standards & technology governance',subs:[
      {label:'Shape emerging technology',leaves:[
        {label:'AI, data & digital rules',terms:['ai act','artificial intelligence act','data act','digital regulation','ai regulation']},
        {label:'Standards & regulatory capacity',terms:['standardisation','standardization','standards','regulatory capacity','regulatory framework']}
      ]},
      {label:'Rules as geopolitical leverage',leaves:[
        {label:'Extraterritorial law & market power',terms:['extraterritorial','third-country laws','market power','economic coercion','regulatory power']}
      ]}
    ]}
  ];

  const NODE_COPY={
    'Artificial intelligence & advanced computing':{
      what:'Current evidence links European computing capacity with access to chips, cloud services and shared infrastructure.',
      why:'Research capability increasingly depends on affordable computing power and reliable access to essential digital infrastructure.'
    },
    'European capacity':{
      what:'European programmes are expanding shared computing infrastructure and support for researchers who use it.',
      why:'Shared capacity lets more institutions run data-intensive research without building equivalent systems themselves.'
    },
    'External dependencies':{
      what:'European research still relies on important computing components and services supplied from outside Europe.',
      why:'External suppliers can affect availability, price, legal conditions and continuity for research infrastructure.'
    },
    'AI factories & supercomputers':{
      what:'Europe is building shared supercomputing facilities for artificial-intelligence and scientific workloads.',
      why:'Shared supercomputers widen access to advanced computing across universities, laboratories and smaller research teams.'
    },
    'Research access to compute':{
      what:'Access to large-scale computing remains uneven across European research organisations and firms.',
      why:'Computing access shapes who can train models, analyse large datasets and compete internationally.'
    },
    'Chips, cloud & control layers':{
      what:'European computing depends partly on foreign chips, cloud platforms and related control layers.',
      why:'Supplier concentration can constrain research access when trade, licensing or jurisdictional conditions change.'
    },
    'Chips & critical inputs':{
      what:'Semiconductor capacity and strategic materials remain central constraints on European technology development.',
      why:'Research and industrial scaling depend on inputs that Europe cannot always replace quickly.'
    },
    'European production':{
      what:'European policy is funding pilot lines, testing capacity and semiconductor production capabilities.',
      why:'Local production and testing reduce dependence while improving the route from research to manufacturing.'
    },
    'Supply exposure':{
      what:'Critical materials and technology inputs remain concentrated in a small number of external suppliers.',
      why:'Restrictions or shortages can interrupt experiments, manufacturing and strategic technology development.'
    },
    'Chips Act & pilot lines':{
      what:'EU semiconductor policy is creating pilot lines and facilities between research and commercial production.',
      why:'Pilot capacity helps European research move into manufacturable technologies without relying entirely on foreign facilities.'
    },
    'Testing & strategic technology':{
      what:'European programmes are expanding testing and experimental facilities for semiconductors and other strategic technologies.',
      why:'Testing infrastructure determines whether promising research can be validated and adopted by industry.'
    },
    'Critical materials & export restrictions':{
      what:'Material dependencies are increasingly shaped by export restrictions, supplier concentration and substitution efforts.',
      why:'Restricted inputs can slow European research and production even when scientific capability is strong.'
    },
    'Research security':{
      what:'European institutions are adding safeguards around sensitive research, collaboration and knowledge transfer.',
      why:'Security measures must protect valuable knowledge without unnecessarily weakening international scientific cooperation.'
    },
    'Protect knowledge':{
      what:'Research organisations are strengthening safeguards against interference, unwanted transfer and misuse of sensitive knowledge.',
      why:'Weak safeguards can expose strategic know-how, data and research relationships to external pressure.'
    },
    'Keep collaboration open':{
      what:'Research-security policy is being designed alongside commitments to international scientific collaboration.',
      why:'Overly broad restrictions can reduce access to partners, expertise, facilities and research networks.'
    },
    'Foreign interference & trusted research':{
      what:'European guidance increasingly treats foreign interference and trusted collaboration as research-management issues.',
      why:'Universities need practical safeguards that distinguish legitimate cooperation from coercion or covert influence.'
    },
    'Sensitive & dual-use research':{
      what:'More research areas are being assessed for civilian and security uses at the same time.',
      why:'Dual-use status can change funding, publication, export-control and partnership conditions for researchers.'
    },
    'Screening without isolation':{
      what:'European research organisations are testing screening approaches that preserve legitimate international collaboration.',
      why:'Proportionate screening can reduce security risks without cutting valuable scientific ties.'
    },
    'Researchers & skills':{
      what:'Talent attraction, mobility and shortages are becoming strategic constraints across several technology fields.',
      why:'European research capacity depends on keeping and attracting people with scarce scientific and engineering skills.'
    },
    'Attract & retain':{
      what:'European programmes are trying to improve research careers, mobility and retention across borders.',
      why:'Better career conditions help laboratories keep expertise and compete for internationally mobile researchers.'
    },
    'Capability fit':{
      what:'Skills shortages are concentrated in technologies where Europe is also trying to build strategic capability.',
      why:'Infrastructure and funding cannot create capability if qualified researchers and engineers are unavailable.'
    },
    'Careers & mobility':{
      what:'Research-career reforms aim to make movement between European institutions easier and more attractive.',
      why:'Portable careers can move expertise toward emerging research needs without permanently losing talent from Europe.'
    },
    'Global competition for talent':{
      what:'Europe competes with other research systems for scientists, engineers and specialised technology teams.',
      why:'Persistent outflows can weaken laboratories, startup formation and the transfer of strategic know-how.'
    },
    'Skills for strategic technologies':{
      what:'Artificial intelligence, quantum and semiconductor programmes report growing demand for specialised technical skills.',
      why:'Skills gaps can become the binding constraint on European investment in strategic technologies.'
    },
    'International research partnerships':{
      what:'European research partnerships are being reshaped by programme association, security concerns and geopolitical alignment.',
      why:'Partnership rules determine which expertise, facilities, funding and networks European researchers can access.'
    },
    'Programme relationships':{
      what:'Horizon Europe association and future framework-programme choices are redefining participation beyond EU membership.',
      why:'Association decisions directly change who can join consortia and compete for European research funding.'
    },
    'External pressure':{
      what:'Sanctions, export controls and foreign legal measures increasingly affect research and technology relationships.',
      why:'External restrictions can disrupt collaborations even when European institutions want them to continue.'
    },
    'Horizon association & next framework programme':{
      what:'Association agreements and the next EU research framework programme are shaping future participation rules.',
      why:'Eligibility choices affect Europe’s research networks, funding reach and access to partner capabilities.'
    },
    'Science diplomacy & joint research':{
      what:'Scientific cooperation remains a tool for maintaining relationships and sharing capability across political divides.',
      why:'Joint research can preserve access and influence when wider diplomatic relations become more difficult.'
    },
    'Sanctions, coercion & legal reach':{
      what:'Research partnerships can be affected by sanctions, coercive measures and laws applied beyond national borders.',
      why:'Legal reach outside Europe can restrict partners, technologies, finance or data available to European research.'
    },
    'Funding & framework programmes':{
      what:'EU research funding is being reshaped around competitiveness, strategic technologies and the next framework programme.',
      why:'Budget and eligibility choices determine which capabilities Europe can sustain over several research cycles.'
    },
    'The next programme':{
      what:'Debate over the next framework programme concerns autonomy, scale, priorities and links to industrial policy.',
      why:'Programme design will shape European research incentives and international cooperation for years.'
    },
    'Who benefits':{
      what:'Funding debates continue over excellence, widening participation and regional innovation capacity.',
      why:'Uneven participation can leave parts of Europe outside the networks building strategic capability.'
    },
    'FP10 design & research autonomy':{
      what:'Proposals for the next EU research framework programme differ on structure, autonomy and strategic focus.',
      why:'Governance choices affect whether research priorities remain scientific, industrial or politically directed.'
    },
    'Budget & EU long-term funding':{
      what:'Research spending competes with other priorities inside the EU long-term budget.',
      why:'Funding pressure can narrow programme ambition even when strategic technology goals are expanding.'
    },
    'Widening, cohesion & excellence':{
      what:'EU programmes continue balancing research excellence with wider participation across regions and member states.',
      why:'Broader capability reduces concentration and strengthens the resilience of Europe’s research system.'
    },
    'Research information & assessment':{
      what:'Research assessment and information systems are being redesigned around openness, responsibility and data access.',
      why:'Measurement rules influence careers, funding decisions and dependence on commercial research-information providers.'
    },
    'Measurement reform':{
      what:'European initiatives are changing how research quality, careers and institutional performance are assessed.',
      why:'Assessment incentives shape researcher behaviour and which forms of scientific contribution receive recognition.'
    },
    'Measurement dependency':{
      what:'Important research indicators still depend on concentrated databases, metrics and proprietary information systems.',
      why:'Control over research data can create strategic dependencies in evaluation and policy analysis.'
    },
    'Responsible research assessment':{
      what:'Assessment reform is reducing reliance on narrow publication metrics and encouraging broader evidence of contribution.',
      why:'Better assessment can reward useful research without reinforcing distorted publishing incentives.'
    },
    'Open research information':{
      what:'European initiatives are expanding openly governed data about publications, organisations and research activity.',
      why:'Open information reduces dependence on a small number of commercial research databases.'
    },
    'Indicators, bibliometrics & data ownership':{
      what:'Research policy still relies heavily on bibliometric indicators and externally controlled data sources.',
      why:'Data ownership affects transparency, reproducibility and Europe’s ability to assess its own research system.'
    },
    'Firms, innovation & scale-up':{
      what:'European policy is trying to improve the path from research results to growing technology companies.',
      why:'Strategic capability is lost when promising research scales commercially outside Europe.'
    },
    'Build in Europe':{
      what:'Funding, procurement and technology-transfer policies increasingly aim to keep more innovation activity in Europe.',
      why:'Domestic scaling retains intellectual property, skilled jobs and production capability near European research.'
    },
    'Compete globally':{
      what:'European innovation performance remains uneven when measured against leading global technology economies.',
      why:'Persistent scale and productivity gaps reduce Europe’s ability to convert research strength into market power.'
    },
    'Start-ups, scale-ups & venture capital':{
      what:'European technology firms still face financing gaps as they move from startup to large-scale growth.',
      why:'Insufficient growth capital can move ownership, headquarters and strategic know-how outside Europe.'
    },
    'Procurement & commercialisation':{
      what:'Public procurement and technology transfer are being used to create demand for research-based innovation.',
      why:'Early customers can help European technologies cross the gap between demonstration and commercial scale.'
    },
    'Productivity & innovation performance':{
      what:'Innovation indicators continue to show gaps in productivity, investment and commercial scaling across Europe.',
      why:'Weak conversion of research into productivity limits the economic base supporting future research investment.'
    },
    'Biotech & health research':{
      what:'Health research increasingly depends on cross-border data, trials, regulation and biotechnology capability.',
      why:'Access rules and supply dependencies can determine whether European discoveries become usable health technologies.'
    },
    'Research networks':{
      what:'Clinical, data and laboratory networks connect health research across European institutions and countries.',
      why:'Fragmented networks make studies slower and reduce access to sufficiently large datasets and patient groups.'
    },
    'Security & control':{
      what:'Biosecurity, data protection and supply dependencies increasingly shape health-research governance.',
      why:'Stronger controls can protect sensitive assets but also restrict legitimate cross-border research.'
    },
    'Clinical trials & health data':{
      what:'European health research is expanding shared approaches to trials and cross-border health-data use.',
      why:'Larger interoperable datasets improve research while increasing demands for trusted governance and access controls.'
    },
    'Medicines & life-science innovation':{
      what:'European life-science policy links research, manufacturing, regulation and access to medicines.',
      why:'Weak links between discovery and production can create dependence even when European science is strong.'
    },
    'Biosecurity, data rules & dependencies':{
      what:'Health and biotechnology research face tighter rules around sensitive data, biological risk and supply security.',
      why:'These rules affect which experiments, partners and infrastructures remain accessible to European researchers.'
    },
    'Quantum technologies':{
      what:'European quantum programmes are building computing, communications, sensing and experimental infrastructure.',
      why:'Early capability influences future standards, security applications and dependence on external technology providers.'
    },
    'European capability':{
      what:'European programmes are investing in shared facilities, testbeds and specialised technology infrastructure.',
      why:'Shared facilities let more researchers use expensive capabilities that individual institutions cannot build alone.'
    },
    'Geopolitical exposure':{
      what:'Quantum supply chains, export controls and access restrictions are becoming part of technology competition.',
      why:'Restricted components or partnerships can slow capability development in a strategically sensitive field.'
    },
    'Computers & shared infrastructure':{
      what:'European quantum-computing access is increasingly organised through shared research infrastructure and public programmes.',
      why:'Shared access broadens experimentation while reducing dependence on a small number of private providers.'
    },
    'Pilot lines & testing':{
      what:'Experimental and pilot facilities are being built to test quantum technologies before wider deployment.',
      why:'Testing capacity helps convert scientific results into reliable components, systems and industrial know-how.'
    },
    'Controls, supply & access':{
      what:'Quantum development is increasingly affected by technology controls, specialised suppliers and international access rules.',
      why:'Supply restrictions can limit European progress even when domestic research capability is strong.'
    },
    'Open science & shared facilities':{
      what:'European research increasingly uses shared facilities, federated data and open research-information systems.',
      why:'Shared access expands capability but also makes governance, security and interoperability more important.'
    },
    'Shared infrastructure':{
      what:'Research facilities and data services are increasingly shared across institutions and national borders.',
      why:'Shared infrastructure reduces duplication and widens access to scarce scientific assets.'
    },
    'Openness under pressure':{
      what:'Open-science commitments increasingly coexist with research-security and knowledge-protection requirements.',
      why:'Europe must protect sensitive work without weakening the openness that supports scientific collaboration.'
    },
    'Facilities & open access':{
      what:'European facilities are widening access to specialised instruments, laboratories and research infrastructure.',
      why:'Open facility access spreads capability beyond the organisations that own the equipment.'
    },
    'Federated research data':{
      what:'European initiatives are connecting research data while keeping it distributed across institutions and countries.',
      why:'Federation can improve reuse without requiring every dataset to move into one central system.'
    },
    'Open science & research security':{
      what:'Research organisations are defining where openness should give way to proportionate security safeguards.',
      why:'Poorly targeted restrictions can damage collaboration while failing to protect genuinely sensitive research.'
    },
    'Rules, standards & technology governance':{
      what:'European rules and standards increasingly shape how strategic technologies are developed and deployed.',
      why:'Rule-setting can create market influence when European requirements become widely adopted.'
    },
    'Shape emerging technology':{
      what:'European institutions are developing rules and standards while technologies are still evolving.',
      why:'Early rule-setting can influence technical design before global practices become difficult to change.'
    },
    'Rules as geopolitical leverage':{
      what:'Technology rules can affect market access, supply chains and firms beyond the jurisdiction that created them.',
      why:'External legal reach can constrain European choices even without direct control of European institutions.'
    },
    'AI, data & digital rules':{
      what:'European digital legislation is defining requirements for artificial intelligence, data use and online infrastructure.',
      why:'Implementation determines whether regulation supports trusted innovation or adds disproportionate barriers to research.'
    },
    'Standards & regulatory capacity':{
      what:'European organisations are investing in technical standards and the expertise needed to shape them.',
      why:'Standards influence interoperability, market access and whose technical choices become default.'
    },
    'Extraterritorial law & market power':{
      what:'Foreign laws and dominant technology providers can impose conditions on European organisations from outside Europe.',
      why:'External legal and market power can limit European autonomy over research infrastructure and technology choices.'
    }
  };
  const clean=s=>String(s||'').replace(/\s+/g,' ').trim();
  const escRx=s=>String(s).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const rowText=x=>[x?.title,x?.headline,x?.what,x?.core_message,x?.summary,x?.relevance_note,x?.why_it_matters,x?.source,...(x?.ri_evidence||[]),...(x?.geo_evidence||[])].map(v=>clean(v)).join(' ').toLowerCase();
  function hasTerm(h,t){const q=clean(t).toLowerCase();if(!q)return false;const p=escRx(q).replace(/\\ /g,'\\s+');return new RegExp('(^|[^a-z0-9])'+p+'([^a-z0-9]|$)','i').test(h)}
  function termHits(x,leaf){const h=rowText(x);let n=0;for(const t of leaf.terms||[])if(hasTerm(h,t))n++;return n}
  function stamp(x){const n=Date.parse(x?.date||0);return Number.isFinite(n)?n:0}

  function evaluate(items){
    const live=(items||[]).filter(x=>x&&typeof x==='object');
    return HIERARCHIES.map(h=>{
      const leaves=h.subs.flatMap(s=>s.leaves.map(l=>({...l,sub:s.label})));
      const matches=[];let supported=0,newRows=0,recency=0;
      const leafSupport=leaves.map(leaf=>{
        const ms=[];
        live.forEach((x,i)=>{const hits=termHits(x,leaf);if(hits){const m={x,i,hits,leaf};ms.push(m);matches.push(m);if(x.new_this_scan)newRows++}});
        if(ms.length)supported++;
        const newest=ms.reduce((n,m)=>Math.max(n,stamp(m.x)),0);recency=Math.max(recency,newest);
        return {leaf,matches:ms};
      });
      const score=matches.reduce((s,m)=>s+1+Math.min(3,m.hits-1)*.22+(m.x?.new_this_scan ? .12 : 0),0)+supported*6+(newRows?Math.min(3,newRows)*1.5:0)+(recency?recency/1e15:0);
      return {...h,matches,leafSupport,supported,score};
    }).filter(x=>x.supported>=2).sort((a,b)=>b.supported-a.supported||b.score-a.score||a.label.localeCompare(b.label));
  }

  function chooseMain(evals,count){
    const n=Math.max(1,Math.min(8,Number(count)||8));
    const pinned=['ai_compute','chips_materials','research_security','talent','partnerships','funding','measurement','firms'];
    const out=[];
    for(const id of pinned){const e=evals.find(x=>x.id===id);if(e&&!out.includes(e)&&out.length<n)out.push(e)}
    for(const e of evals){if(out.length>=n)break;if(!out.includes(e))out.push(e)}
    return out.slice(0,n);
  }

  function bestMatch(ms){
    return [...(ms||[])].sort((a,b)=>(b.hits-a.hits)||((b.x?.new_this_scan?1:0)-(a.x?.new_this_scan?1:0))||(stamp(b.x)-stamp(a.x)))[0]||null;
  }
  function nodeMeta(ms,query,label){
    const unique=new Map();for(const m of ms||[]){const key=clean(m.x?.link)||clean(m.x?.title)||String(m.i);if(!unique.has(key))unique.set(key,m)}
    const matches=[...unique.values()],best=bestMatch(matches),x=best?.x||{};
    const copy=NODE_COPY[label]||{};
    const whatRaw=copy.what||globalThis.RadarReaderStyle?.whatFor?.(x)||clean(x.core_message||x.what||x.title||'');
    const whyRaw=copy.why||globalThis.RadarReaderStyle?.whyFor?.(x)||clean(x.why_it_matters||x.relevance_note||'');
    const what=globalThis.RadarReaderStyle?.limit?.(whatRaw||`${label} is supported by current Radar evidence.`,18)||whatRaw;
    const why=globalThis.RadarReaderStyle?.limit?.(whyRaw||'It changes a specific European research capability, dependency, rule or partnership.',15)||whyRaw;
    return {query:clean(query),evidenceCount:matches.length,sourceLink:clean(x.link),sourceTitle:clean(x.title||x.headline),sourceName:clean(x.source),what,why};
  }
  function build(items,opt={}){
    const evals=evaluate(items),count=Math.max(1,Math.min(8,Number(opt.count)||8));
    const mains=chooseMain(evals,count);
    return mains.map((h,index)=>{
      const support=new Map(h.leafSupport.map(v=>[v.leaf.label,v.matches]));
      const subs=h.subs.map((sub,si)=>{
        const subMatches=sub.leaves.flatMap(l=>support.get(l.label)||[]);
        const query=sub.leaves[0]?.terms?.[0]||sub.label;
        return {id:`${h.id}-s${si+1}`,label:sub.label,...nodeMeta(subMatches,query,sub.label)};
      });
      const leaves=h.subs.flatMap((sub,si)=>sub.leaves.map((leaf,li)=>({
        id:`${h.id}-s${si+1}-l${li+1}`,label:leaf.label,...nodeMeta(support.get(leaf.label)||[],leaf.terms?.[0]||leaf.label,leaf.label)
      }))).slice(0,3);
      const mainQuery=h.subs[0]?.leaves?.[0]?.terms?.[0]||h.label;
      return {id:h.id,rank:index+1,main:{id:h.id,label:h.label,...nodeMeta(h.matches,mainQuery,h.label)},subs,leaves};
    });
  }

  g.RadarIssues={build,buildTrees:build,evaluate,chooseMain,hierarchies:HIERARCHIES};
})(globalThis);
