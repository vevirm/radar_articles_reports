(function(g){
  'use strict';

  /* Eight reader maps are chosen from deliberately different R&I systems.
     The labels are a hierarchy; the live corpus decides which maps are strongest now. */
  const HIERARCHIES=[
    {id:'ai_compute',label:'AI & advanced computing',subs:[
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
        {label:'Horizon association & FP10',terms:['horizon europe association','associated countries','association to horizon','fp10']},
        {label:'Science diplomacy & joint research',terms:['science diplomacy','international cooperation in research and innovation','joint research','bilateral research']}
      ]},
      {label:'External pressure',leaves:[
        {label:'Sanctions, coercion & legal reach',terms:['sanctions','economic coercion','extraterritorial','third-country laws','export control']}
      ]}
    ]},
    {id:'funding',label:'Funding & framework programmes',subs:[
      {label:'The next programme',leaves:[
        {label:'FP10 design & research autonomy',terms:['fp10','framework programme 10','next framework programme','horizon europe successor']},
        {label:'Budget & MFF pressure',terms:['mff','multiannual financial framework','budget','competitiveness fund']}
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
  function nodeMeta(ms,query){
    const unique=new Map();for(const m of ms||[]){const key=clean(m.x?.link)||clean(m.x?.title)||String(m.i);if(!unique.has(key))unique.set(key,m)}
    const matches=[...unique.values()],best=bestMatch(matches),x=best?.x||{};
    const whyRaw=globalThis.RadarReaderStyle?.whyFor?.(x)||clean(x.why_it_matters||x.relevance_note||'');
    const why=globalThis.RadarReaderStyle?.limit?.(whyRaw||'This branch changes a documented capability, dependency, rule or partnership in European R&I.',15)||whyRaw;
    return {query:clean(query),evidenceCount:matches.length,sourceLink:clean(x.link),sourceTitle:clean(x.title||x.headline),sourceName:clean(x.source),why};
  }
  function build(items,opt={}){
    const evals=evaluate(items),count=Math.max(1,Math.min(8,Number(opt.count)||8));
    const mains=chooseMain(evals,count);
    return mains.map((h,index)=>{
      const support=new Map(h.leafSupport.map(v=>[v.leaf.label,v.matches]));
      const subs=h.subs.map((sub,si)=>{
        const subMatches=sub.leaves.flatMap(l=>support.get(l.label)||[]);
        const query=sub.leaves[0]?.terms?.[0]||sub.label;
        return {id:`${h.id}-s${si+1}`,label:sub.label,...nodeMeta(subMatches,query)};
      });
      const leaves=h.subs.flatMap((sub,si)=>sub.leaves.map((leaf,li)=>({
        id:`${h.id}-s${si+1}-l${li+1}`,label:leaf.label,...nodeMeta(support.get(leaf.label)||[],leaf.terms?.[0]||leaf.label)
      }))).slice(0,3);
      const mainQuery=h.subs[0]?.leaves?.[0]?.terms?.[0]||h.label;
      return {id:h.id,rank:index+1,main:{id:h.id,label:h.label,...nodeMeta(h.matches,mainQuery)},subs,leaves};
    });
  }

  g.RadarIssues={build,buildTrees:build,evaluate,chooseMain,hierarchies:HIERARCHIES};
})(globalThis);
