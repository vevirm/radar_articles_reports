(function(g){
  'use strict';

  // These are grouping lenses, not a fixed public issue list. The visible issue set,
  // order, branches and evidence are recomputed from the current radar on every load.
  const LENSES=[
    {id:'ai_compute',label:'AI & advanced computing',terms:['artificial intelligence','ai','machine learning','foundation model','compute','computing','supercomputer','gpu','gigafactory','data centre','data center']},
    {id:'chips',label:'Chips & semiconductors',terms:['semiconductor','semiconductors','chip','chips','microelectronics','processor','processors']},
    {id:'materials',label:'Critical materials & supply chains',terms:['critical raw materials','raw materials','critical material','critical materials','supply chain','supply chains','rare earth','graphite','lithium','export restriction']},
    {id:'research_security',label:'Protecting sensitive research',terms:['research security','knowledge security','foreign interference','sensitive research','espionage','security screening','trusted research']},
    {id:'talent',label:'Researchers, skills & careers',terms:['researcher','researchers','talent','skills','brain drain','mobility','career','careers','doctoral','phd','msca','human capital']},
    {id:'funding',label:'Funding & EU research programmes',terms:['horizon europe','fp10','framework programme','funding','grant','grants','erc','msca','eic','competitiveness fund','budget']},
    {id:'firms',label:'Firms, investment & growth',terms:['venture capital','scale-up','scaleup','startup','start-up','commercialisation','commercialization','high-growth','equity','stock market','listing','headquarters']},
    {id:'rules',label:'Rules, standards & regulation',terms:['regulation','regulations','standardisation','standardization','standards','governance','liability','legal framework','regulatory']},
    {id:'partnerships',label:'International research partnerships',terms:['partnership','partnerships','international cooperation','science diplomacy','association agreement','bilateral','transatlantic','eu-us','eu–us','eu-china','eu–china','india','china','united states']},
    {id:'control',label:'Control over key technology',terms:['sovereignty','sovereign','strategic autonomy','dependence','dependency','de-risk','derisk','technological independence','economic security']},
    {id:'quantum',label:'Quantum technologies',terms:['quantum']},
    {id:'biotech',label:'Biotechnology & life sciences',terms:['biotech','biotechnology','biology','genomic','health data','life science','biosecurity']},
    {id:'data_cloud',label:'Data, cloud & digital infrastructure',terms:['data infrastructure','data space','cloud','digital infrastructure','data centre','data center','federated data','data access']},
    {id:'defence',label:'Defence & civilian-military technology',terms:['defence','defense','dual-use','military','nato']},
    {id:'energy',label:'Energy for research & technology',terms:['energy','electricity','power grid','renewable','nuclear']},
    {id:'open',label:'Open science & open technology',terms:['open science','open source','open hardware','open research','research openness']},
    {id:'industry',label:'Production & public buying',terms:['procurement','public buying','manufacturing','production capacity','industrial capacity','factory','factories','gigafactory']},
    {id:'ip',label:'Patents, ownership & licensing',terms:['intellectual property','patent','patents','licensing','ownership']},
    {id:'facilities',label:'Research facilities & shared infrastructure',terms:['research infrastructure','research infrastructures','facility','facilities','laboratory','laboratories','telescope','synchrotron','eosc']},
    {id:'space_comms',label:'Space & communications',terms:['space','satellite','satellites','communications','telecom','telecommunications','6g','5g']},
    {id:'cyber',label:'Cybersecurity & digital resilience',terms:['cybersecurity','cyber security','cyber','digital resilience']},
    {id:'competition',label:'Economic competitiveness',terms:['competitiveness','productivity','economic growth','innovation performance']},
    {id:'diplomacy',label:'Science diplomacy & global influence',terms:['science diplomacy','diplomacy','global influence','soft power','international coordination']},
    {id:'controls',label:'Export controls & investment checks',terms:['export control','export controls','export restriction','investment screening','foreign investment','outbound investment','sanction','sanctions']}
  ];

  function clean(s){return String(s||'').replace(/\s+/g,' ').trim()}
  function textFor(x){return ['title','headline','what','core_message','relevance_note','watch_theme','why_it_matters','summary'].map(k=>clean(x&&x[k])).join(' ').toLowerCase()}
  function escRx(s){return s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
  function hasTerm(h,t){const p=escRx(String(t).toLowerCase()).replace(/\\ /g,'\\s+');return new RegExp('(^|[^a-z0-9])'+p+'([^a-z0-9]|$)','i').test(h)}
  function termHits(x,lens){const h=textFor(x);let n=0;for(const t of lens.terms)if(hasTerm(h,t))n++;return n}
  function merit(x){return Number(g.RadarSourceMerit?.scoreFor?.(x)||g.RadarSourceMerit?.forItem?.(x)?.score||55)}
  function stamp(x){const n=Date.parse(x?.date||0);return Number.isFinite(n)?n:0}
  function itemWeight(x,hits){return (1+Math.min(2,Math.max(0,hits-1))*.18) * (.65+.35*(merit(x)/100)) * (x?.new_this_scan?1.12:1)}
  function plain(s){return clean(g.RadarInsights?.fastReaderText?.(s)||s)}
  function point(x){return plain(g.RadarInsights?.pointFor?.(x)||x?.core_message||x?.why_it_matters||x?.title||x?.headline||x?.what||'')}
  function idFor(x,i){return clean(x?.link)||clean(x?.title)||clean(x?.headline)||('item-'+i)}
  function overlap(a,b){let n=0;for(const k of a)if(b.has(k))n++;return n}
  function jaccard(a,b){const o=overlap(a,b);return o/(a.size+b.size-o||1)}

  function evaluate(items){
    return LENSES.map(lens=>{
      const matches=[];let score=0;
      items.forEach((x,i)=>{const hits=termHits(x,lens);if(!hits)return;const w=itemWeight(x,hits);matches.push({x,i,hits,w,id:idFor(x,i)});score+=w});
      return {...lens,matches,score,set:new Set(matches.map(m=>m.id))};
    }).filter(x=>x.matches.length>=2).sort((a,b)=>b.score-a.score||b.matches.length-a.matches.length||a.label.localeCompare(b.label));
  }

  function chooseThemes(evals,opt){
    const max=Math.max(5,Math.min(10,Number(opt?.maxIssues)||8));
    const min=Math.max(4,Math.min(max,Number(opt?.minIssues)||6));
    if(!evals.length)return [];
    const top=evals[0].score||1, chosen=[];
    for(const e of evals){
      if(chosen.length>=max)break;
      if(chosen.length>=min && e.score<top*.16 && !e.matches.some(m=>m.x?.new_this_scan))continue;
      const near=chosen.some(c=>jaccard(c.set,e.set)>.72);
      if(near)continue;
      chosen.push(e);
    }
    for(const e of evals){if(chosen.length>=min)break;if(!chosen.includes(e))chosen.push(e)}
    return chosen;
  }

  function bestItems(matches,n){return [...matches].sort((a,b)=>b.hits-a.hits||merit(b.x)-merit(a.x)||stamp(b.x)-stamp(a.x)).slice(0,n).map(m=>m.x)}

  function branchesFor(theme,evals){
    const companions=evals.filter(e=>e.id!==theme.id).map(e=>{
      const ids=new Set(e.matches.map(m=>m.id));
      const shared=theme.matches.filter(m=>ids.has(m.id));
      const score=shared.reduce((s,m)=>s+m.w,0);
      return {e,shared,score,ratio:shared.length/(theme.matches.length||1)};
    }).filter(z=>z.shared.length>=2).sort((a,b)=>b.score-a.score||b.shared.length-a.shared.length);

    const branches=[];
    for(const c of companions){
      if(branches.length>=4)break;
      if(branches.some(b=>jaccard(b.e.set,c.e.set)>.78))continue;
      const evidence=bestItems(c.shared,2);
      if(!evidence.length)continue;
      branches.push({title:plain(c.e.label),evidence,e:c.e});
    }
    if(branches.length<2){
      const leftovers=bestItems(theme.matches,Math.min(4,theme.matches.length));
      leftovers.forEach((x,i)=>{if(branches.length<3)branches.push({title:i===0?'Leading finding':'Another current finding',evidence:[x],e:null})});
    }
    return branches;
  }

  function dynamicLabel(theme){return plain(theme.label)}
  function listPhrase(xs){
    const a=(xs||[]).filter(Boolean);
    if(a.length<2)return a[0]||'';
    if(a.length===2)return `${a[0]} and ${a[1]}`;
    return `${a.slice(0,-1).join(', ')}, and ${a[a.length-1]}`;
  }

  function build(items,opt){
    const live=(items||[]).filter(x=>x&&typeof x==='object');
    const evals=evaluate(live), selected=chooseThemes(evals,opt);
    return selected.map((theme,index)=>{
      const branches=branchesFor(theme,evals);
      const title=dynamicLabel(theme);
      const evidence=bestItems(theme.matches,3);
      const branchNames=branches.slice(0,3).map(b=>b.title.toLowerCase());
      const line=branchNames.length?`Current evidence centres on ${listPhrase(branchNames)}.`:`Current evidence is concentrated around ${title.toLowerCase()}.`;
      return {id:theme.id,title,line,score:theme.score,count:theme.matches.length,branches,evidence,rank:index+1};
    });
  }

  function summary(issues){
    const names=(issues||[]).slice(0,3).map(x=>plain(x.title));
    if(!names.length)return {title:'The current radar has not yet produced a stable issue pattern.',text:'Open the radar evidence while the next scan builds the picture.'};
    if(names.length===1)return {title:`The current radar is concentrated on ${names[0]}.`,text:'This issue has the strongest current evidence concentration.'};
    const final=names.pop();
    return {title:`The current radar is concentrated on ${names.join(', ')} and ${final}.`,text:'These are the strongest issue concentrations in the latest admitted material; they can change after the next successful scan.'};
  }

  g.RadarIssues={build,summary,lenses:LENSES};
})(globalThis);
