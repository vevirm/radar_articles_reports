(function(root,factory){
  const api=factory(root.RadarInsights);
  if(typeof module==='object'&&module.exports) module.exports=api;
  root.SovereigntyFrontier=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(RadarInsights){
  'use strict';

  const ROWS=[
    {id:'knowledge',name:'Knowledge & people',short:'Knowledge & people',description:'Science, publication, collaboration, talent flows and training.'},
    {id:'infrastructure',name:'Infrastructure & inputs',short:'Infrastructure & inputs',description:'Compute, data, instruments, materials, energy and facilities.'},
    {id:'conversion',name:'Conversion',short:'Conversion',description:'Firms, products, capital, procurement, defence, dual-use and capability-building.'},
    {id:'rules',name:'Rules & institutions',short:'Rules & institutions',description:'Export controls, research security, standards, funding programmes and decision speed.'}
  ];
  const COLUMNS=[
    {id:'A',name:'Opening',direction:'more independent · more competitive',tone:'opportunity'},
    {id:'B',name:'Costly autonomy',direction:'more independent · less competitive',tone:'tradeoff'},
    {id:'C',name:'Productive dependence',direction:'less independent · more competitive',tone:'exposure'},
    {id:'D',name:'Double loss',direction:'less independent · less competitive',tone:'alarm'}
  ];
  const CELL_NAMES={
    knowledge:{A:['Talent windfall','inflow of people, ideas'],B:['Closed lab','security cuts collaboration'],C:['Borrowed brains','excellence via others'],D:['Brain drain','people and ideas leave']},
    infrastructure:{A:['Home chokepoint','EU holds a lever'],B:['Expensive mirror','own it, lag behind'],C:['Rented frontier',"fast, on others' terms"],D:['Cut supply','access lost, no substitute']},
    conversion:{A:['Home champion','EU firm sets pace'],B:['Protected niche','sovereign but subscale'],C:['Foreign exit','scale abroad, value too'],D:['Hollowing out','no firms, no capability']},
    rules:{A:['Rule-setter','EU standard adopted'],B:['Fortress rules','autonomy, slower system'],C:['Rule-taker',"adopts others' regimes"],D:['Gridlock','cannot decide in time']}
  };

  const ROW_TERMS={
    knowledge:['research','science','scientific','university','universities','academic','academia','researcher','researchers','scientist','scientists','talent','skills','training','doctoral','phd','publication','research collaboration','scientific collaboration','research cooperation','scientific cooperation','horizon europe','framework programme','erc','knowledge','visa','mobility','brain drain','brain gain','open science','research security'],
    infrastructure:['compute','computing','supercomputer','artificial intelligence','ai model','ai models','ai video model','ai system','ai systems','foundation model','foundation models','data center','data centre','cloud','semiconductor','chip','chips','microelectronics','quantum','reactor','nuclear','grid','electricity','energy','battery','batteries','lithium','critical mineral','critical minerals','critical raw material','critical raw materials','rare earth','materials','instrument','instruments','facility','facilities','infrastructure','telecom','5g','6g','satellite','cable','supply chain','supply chains','input','inputs'],
    conversion:['firm','firms','company','robot','robots','robotics','companies','startup','start-up','scale-up','manufacturer','manufacturing','industrial','industry','product','products','commercial','commercialisation','commercialization','market','capital','venture','investment','investor','procurement','patent','patents','defence','defense','military','dual-use','dual use','capability','capabilities','production','factory','factories'],
    rules:['export control','export controls','sanction','sanctions','regulation','regulatory','standard','standards','rule','rules','governance','institution','institutions','funding programme','funding program','programme','program','screening','research security','restriction','restrictions','ban','bans','law','laws','framework','decision','permit','permits','subsidy','subsidies','state aid']
  };

  const INDEPENDENCE_TERMS=['sovereign','sovereignty','autonomy','autonomous','strategic autonomy','dependence','dependency','dependencies','reliance','rely','non-eu','foreign supplier','external supplier','externally controlled','access','control','diversif','de-risk','derisk','self-suff','domestic capacity','european capacity','local capacity','own technology','own capability','supply security','vendor','partner','partnership','open-weight','open source','chinese firms','chinese companies','us firms','american firms','imported technology','technology vendor','lock-in','lock in'];
  const COMPETITIVENESS_TERMS=['competit','performance','frontier','leading','leader','best available','capacity','capability','capabilities','scale','scaling','productivity','innovation','investment','invest','patent','market share','advanced','high-tech','high tech','talent','compute','supercomputer','lag','behind','fragmentation','subscale','cost','costly','expensive','shortage','declin','slow','delay','miss the','hollowing','brain drain'];
  const FAILURE_TERMS=['fail','failure','risk','vulnerab','exposure','weaponis','weaponiz','restrict','restriction','ban','block','cut off','cutoff','loss of access','suspend','withdraw','sanction','shortage','chokepoint','bottleneck','dependency','reliance','brain drain','hollowing','gridlock','delay','cannot','unable','no substitute','security cut','fragmentation','coercion','retreat','curb','curbs','struggl','fail to adopt','failed to adopt','decoupl'];
  const EVENT_TERMS=['launch','launched','adopt','adopted','order','ordered','restrict','restricted','curb','curbs','ban','banned','suspend','suspended','withdraw','retreat','invest','investment','build','building','expand','expansion','shift','shifting','becoming','increase','increasing','decrease','decline','declining','cut','cuts','open','opened','close','closed','facilitat','approve','approved','reject','rejected','propos','sign','signed','join','joined','leave','left','losing','overtook','outpace','outpaced','fragment','lag','behind','depend','reliance','consolidat','scale','scaling','deploy','deployed','designat','mandat','require','warn','warning','fail','failed'];
  const INDIRECT_DOMAIN_TERMS=['artificial intelligence','ai model','ai models','supercomputer','compute','data center','data centre','cloud','semiconductor','chip','quantum','nuclear','reactor','solar','battery','critical mineral','critical raw material','robot','robotics','defence technology','defense technology','dual-use','dual use','patent','technology','research collaboration','scientific collaboration','research cooperation','scientific cooperation'];
  const GEOPOLITICAL_ACTORS=['china','chinese','united states',' us ','american','russia','russian','taiwan','india','japan','south korea','korea','uk','britain','canada'];

  const AUTONOMY_UP=['reduce strategic depend','reduce depend','reducing depend','diversif','sovereign control','digital sovereignty','strategic autonomy','self-suff','domestic capacity','european capacity','home-grown','homegrown','reshor','local production','own technology','own capability','control over','alternative supplier','alternative suppliers','open-weight','open source','eu-led','european infrastructure'];
  const AUTONOMY_DOWN=['more dependent','dependence on','dependent on','reliance on','rely on','non-eu technology','non-eu vendor','foreign supplier','foreign suppliers','external supplier','externally controlled','on others terms',"others' terms",'loss of access','access lost','brain drain','people and ideas leave','imported technology','foreign technology','chinese companies','restricted access','partner changes','vendor lock','lock-in','cut supply','hollowing out','chinese firms','us firms','american firms'];
  const PERFORMANCE_UP=['expand capabilities','expands capabilities','build capacity','capacity-building','capability-building','investment','invests','investing','supercomputer','frontier','leading','leader','outpace','overtook','scale','scaling','competitive','competitiveness','productivity','talent inflow','brain gain','open-weight','advanced technology','advanced technologies','fast','growth','innovation capacity','sets pace'];
  const PERFORMANCE_DOWN=['less competitive','lag behind','lagging','left behind','miss the','fragmentation','fragmented','subscale','costly','expensive','higher cost','cost increase','security cuts','cuts collaboration','brain drain','hollowing','no capability','no substitute','shortage','delay','slower','declining','loss of capacity','losing capacity','unable to','cannot decide','performance price','operational reasons','slow scientific','slow research','raise cost','raises cost','raising cost','struggl','cannot decide','fail to adopt','failed to adopt'];

  function clean(v){return String(v??'').replace(/\u00ad/g,'').replace(/[ \t]+/g,' ').replace(/\s*\n\s*/g,' ').trim()}
  function norm(v){return clean(v).toLowerCase().replace(/[–—]/g,'-').replace(/[^a-z0-9+.#/&'-]+/g,' ').replace(/\s+/g,' ').trim()}
  function dateFor(x){return clean(x.date||x.published||x.updated||x.first_seen||'')}
  function sourceFor(x){return clean(x.source||x.authors||'')}
  function titleFor(x){return clean(x.headline||x.title||x.what||x.point||'')}
  function candidateWhat(x){return x&&x._origin==='Weak signal'?clean(signalWhat(x)||titleFor(x)):titleFor(x)}
  function linkFor(x){return clean(x.link||'')}
  const PREFIX_TERMS=new Set(['competit','diversif','self-suff','reshor','declin','struggl','facilitat','propos','designat','mandat','depend','reliance','invest','fragment']);
  function escapeRe(v){return String(v).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
  function termMatchNorm(n,term){
    const q=norm(term); if(!q) return false;
    if(PREFIX_TERMS.has(q)) return n.includes(q);
    const body=escapeRe(q).replace(/\\ /g,'\\s+');
    const left=/^[a-z0-9]/.test(q)?'(^|[^a-z0-9])':'';
    const right=/[a-z0-9]$/.test(q)?'(?=$|[^a-z0-9])':'';
    return new RegExp(left+body+right,'i').test(n);
  }
  function has(text,term){return termMatchNorm(norm(text),term)}
  function hitCount(text,terms){const n=norm(text);let c=0;for(const t of terms){if(termMatchNorm(n,t))c++}return c}
  function weightedHits(parts,terms){let score=0;for(const p of parts){if(!p||!p.text)continue;score+=hitCount(p.text,terms)*(p.weight||1)}return score}
  function clamp(n,min,max){return Math.max(min,Math.min(max,n))}
  function uniq(arr){return [...new Set(arr.filter(Boolean))]}

  function anchorTitle(anchor){return clean(anchor).replace(/\s*\(Strand\s+[ABCboth]+\)\s*$/i,'').trim()}
  function buildEvidenceIndex(data){
    const map=new Map();
    for(const x of [...(Array.isArray(data?.strand_a)?data.strand_a:[]),...(Array.isArray(data?.strand_b)?data.strand_b:[])]){
      const title=clean(x.title||''); if(!title) continue;
      map.set(norm(title),x);
    }
    return map;
  }
  function evidenceFor(signal,index){
    const a=anchorTitle(signal.anchor||'');
    if(!a) return null;
    const exact=index.get(norm(a)); if(exact) return exact;
    const needle=norm(a);
    for(const [k,v] of index.entries()) if(k.includes(needle)||needle.includes(k)) return v;
    return null;
  }

  function signalTheme(x){
    if(RadarInsights&&RadarInsights.signalTheme) return clean(RadarInsights.signalTheme(x));
    return clean(x.watch_theme||'');
  }
  function signalWhy(x){
    if(RadarInsights&&RadarInsights.signalWhy) return clean(RadarInsights.signalWhy(x));
    return clean(x.why_it_matters||x.signal_note||'');
  }
  function signalWhat(x){
    if(RadarInsights&&RadarInsights.signalWhat) return clean(RadarInsights.signalWhat(x));
    return titleFor(x);
  }

  function evidenceCandidates(data){
    if(!RadarInsights||!RadarInsights.buildResearchInsights) return [];
    const out=[];
    for(const group of RadarInsights.buildResearchInsights(data)){
      for(const x of group.items){
        const text=`${x.point} ${x.title} ${x.watchTheme||''} ${x.why||''}`;
        const dynamic=hitCount(text,EVENT_TERMS)>0 || hitCount(text,INDEPENDENCE_TERMS)>=2 || hitCount(text,COMPETITIVENESS_TERMS)>=2;
        if(!dynamic) continue;
        out.push({
          headline:x.point||x.title,
          title:x.title,
          source:x.source,
          date:x.date,
          link:x.link,
          strand:x.strand,
          type:x.itemType,
          watch_theme:x.watchTheme||group.name,
          anchor:x.title,
          why_it_matters:x.why||'',
          signal_note:x.point,
          new_this_scan:!!x.newThisScan,
          _origin:'Evidence signal',
          _evidencePoint:x.point
        });
      }
    }
    return out;
  }

  function weakCandidates(data){
    return (Array.isArray(data?.strand_c)?data.strand_c:[]).filter(x=>x&&typeof x==='object').map(x=>({...x,_origin:'Weak signal'}));
  }

  function dedupeCandidates(items){
    const seen=new Set(),out=[];
    for(const x of items){
      const k=norm(linkFor(x)||candidateWhat(x)); if(!k||seen.has(k)) continue; seen.add(k);out.push(x);
    }
    return out;
  }

  function rowScores(x,evidence){
    const title=candidateWhat(x),theme=signalTheme(x),note=clean(x.signal_note||x._evidencePoint||''),anchor=clean(x.anchor||'');
    const support=clean([evidence?.title,evidence?.summary,evidence?.relevance_note].filter(Boolean).join(' '));
    const scores={};
    for(const row of ROWS){
      scores[row.id]=weightedHits([
        {text:title,weight:4},{text:theme,weight:3},{text:note,weight:1.2},{text:anchor,weight:.8},{text:support,weight:.45}
      ],ROW_TERMS[row.id]);
    }
    return scores;
  }

  function chooseRow(scores){
    const tieOrder=['knowledge','infrastructure','conversion','rules'];
    return tieOrder.map(id=>({id,score:scores[id]||0})).sort((a,b)=>b.score-a.score||tieOrder.indexOf(a.id)-tieOrder.indexOf(b.id))[0];
  }

  function questionScores(x,evidence){
    const title=candidateWhat(x),theme=signalTheme(x),note=clean(x.signal_note||x._evidencePoint||''),why=signalWhy(x),anchor=clean(x.anchor||'');
    const support=clean([evidence?.title,evidence?.summary,evidence?.relevance_note].filter(Boolean).join(' '));
    const parts=[{text:title,weight:3},{text:theme,weight:2},{text:note,weight:1},{text:why,weight:.55},{text:anchor,weight:.7},{text:support,weight:.55}];
    return {
      sustain:weightedHits(parts,INDEPENDENCE_TERMS),
      compete:weightedHits(parts,COMPETITIVENESS_TERMS),
      failure:weightedHits(parts,FAILURE_TERMS)
    };
  }

  function directionScores(x,evidence,row,questions){
    const title=candidateWhat(x),theme=signalTheme(x),note=clean(x.signal_note||x._evidencePoint||''),why=signalWhy(x),anchor=clean(x.anchor||'');
    const support=clean([evidence?.title,evidence?.summary].filter(Boolean).join(' '));
    const parts=[{text:title,weight:3},{text:theme,weight:1.8},{text:note,weight:1.2},{text:why,weight:.45},{text:anchor,weight:.55},{text:support,weight:.65}];
    let autonomyUp=weightedHits(parts,AUTONOMY_UP), autonomyDown=weightedHits(parts,AUTONOMY_DOWN);
    let performanceUp=weightedHits(parts,PERFORMANCE_UP), performanceDown=weightedHits(parts,PERFORMANCE_DOWN);
    const direct=norm(`${title} ${theme} ${note}`);

    if(/struggl(?:e|es|ing)? to adopt|fail(?:ed|s|ing)? to adopt|cannot decide/.test(direct)){autonomyDown+=2.4;performanceDown+=2.4}
    if(/(?:reduc|cut|lower)[a-z]*.{0,45}(?:depend|reliance)/.test(direct)) autonomyUp+=3;
    if(/(?:expand|build|increase|strengthen)[a-z]*.{0,35}(?:eu|european|domestic).{0,35}(?:capacity|capabilit|production|infrastructure|compute)/.test(direct)) autonomyUp+=2;
    if(/\beu\b|european|europe/.test(direct) && /(facilitat|invest|build|expand|fund|scale|develop)/.test(direct)) autonomyUp+=1.4;
    if(/china|chinese|united states|\bus\b|american|non-eu|foreign/.test(direct) && /(supplier|vendor|firm|technology|compute|model|infrastructure|capacity)/.test(direct)) autonomyDown+=1.4;
    if(questions.failure>=2 && autonomyUp<1 && autonomyDown<1) autonomyDown+=1.2;
    if(questions.failure>=2 && performanceUp<1 && performanceDown<1) performanceDown+=1.1;
    if(row.id==='rules' && /(export control|sanction|restriction|ban|research security|screening)/.test(direct) && autonomyUp<1) autonomyUp+=1.1;
    if(row.id==='knowledge' && /brain drain|researcher outflow|talent outflow|talent loss|researchers? (?:leave|leaving|left)|scientists? (?:leave|leaving|left)|unable to retain|failure to retain|retention crisis/.test(direct)){autonomyDown+=4;performanceDown+=4}
    if(row.id==='knowledge' && /brain gain|talent inflow|attract(?:ing|ion)?.{0,30}(?:researcher|scientist|talent)|retain(?:ing|ed)?.{0,30}(?:researcher|scientist|talent)|(?:researcher|scientist).{0,25}return/.test(direct)){autonomyUp+=3;performanceUp+=3}

    let autonomy=autonomyUp-autonomyDown;
    let performance=performanceUp-performanceDown;
    if(Math.abs(autonomy)<.55){
      if(performance>0.55 && /(foreign|non-eu|china|chinese|united states|american|partner|vendor|supplier|access)/.test(direct)) autonomy=-1;
      else if(performance<-.55 && questions.failure>=2) autonomy=-1;
      else if(/\beu\b|european|sovereign|autonomy|diversif|domestic/.test(direct)) autonomy=1;
      else autonomy=questions.failure>=2?-1:1;
    }
    if(Math.abs(performance)<.55){
      if(autonomy<0) performance=questions.failure>=2?-1:1;
      else performance=/(cost|lag|slow|cut|restrict|security|ban|fragment)/.test(direct)?-1:1;
    }
    return {autonomy,performance,autonomyUp,autonomyDown,performanceUp,performanceDown};
  }

  function columnFor(direction){
    if(direction.autonomy>=0&&direction.performance>=0) return COLUMNS[0];
    if(direction.autonomy>=0&&direction.performance<0) return COLUMNS[1];
    if(direction.autonomy<0&&direction.performance>=0) return COLUMNS[2];
    return COLUMNS[3];
  }

  function euLinkScore(x,evidence){
    const direct=norm(`${candidateWhat(x)} ${signalTheme(x)} ${clean(x.signal_note||'')} ${signalWhy(x)}`);
    const support=norm(`${clean(x.anchor||'')} ${clean(evidence?.title||'')} ${clean(evidence?.summary||'')}`);
    let s=0;
    if(/\beu\b|european union|european commission|europe\b|member states/.test(direct)) s+=3;
    if(/\beu\b|european union|european commission|europe\b|member states/.test(support)) s+=1.5;
    return s;
  }

  function materialityScore(x,evidence,row){
    const direct=norm(`${candidateWhat(x)} ${signalTheme(x)} ${clean(x.signal_note||x._evidencePoint||'')}`);
    const support=norm(`${clean(x.anchor||'')} ${clean(evidence?.title||'')} ${clean(evidence?.summary||'')}`);
    const directHits=hitCount(direct,ROW_TERMS[row.id]);
    const supportHits=hitCount(support,ROW_TERMS[row.id]);
    return directHits*2.4+Math.min(2,supportHits)*.6;
  }

  function questionFlags(q){return {sustain:q.sustain>=2,compete:q.compete>=2,failure:q.failure>=2}}

  function reachScore(rowScores){
    const active=Object.values(rowScores).filter(v=>v>=2.4).length;
    return clamp(1+Math.max(0,active-1),1,4);
  }
  function irreversibilityScore(x,row,column){
    const t=norm(`${candidateWhat(x)} ${signalTheme(x)} ${clean(x.signal_note||'')} ${signalWhy(x)}`);
    let s=1;
    if(/brain drain|talent loss|firm exit|hollow|closure|closed lab|loss of capacity/.test(t)) s+=2;
    if(/infrastructure|reactor|semiconductor|chip|grid|data center|data centre|supercomputer|facility|supply chain|factory|capital-intensive|capital intensive/.test(t)) s+=1;
    if(/standard|regulation|export control|sanction|lock-in|lock in|patent|procurement|institution/.test(t)) s+=1;
    if(column.id==='D') s+=.5;
    return clamp(Math.round(s),1,4);
  }
  function attentionGapScore(x){
    const src=norm(sourceFor(x));
    let s=2;
    if(x.new_this_scan) s+=1;
    if(!/european commission|eu council|council of the european union|european parliament/.test(src)) s+=1;
    if(/european commission|official journal|eu council|council of the european union|european parliament/.test(src)) s-=1;
    return clamp(s,1,4);
  }
  function actionabilityScore(x,row,evidence){
    const direct=norm(`${candidateWhat(x)} ${signalTheme(x)} ${clean(x.signal_note||'')} ${signalWhy(x)}`);
    const support=norm(`${clean(x.anchor||'')} ${clean(evidence?.title||'')} ${clean(evidence?.summary||'')}`);
    let s=1;
    if(/european commission|member states|\beu\b/.test(direct)) s=4;
    else if(/europe|european/.test(direct)) s=3;
    else if(/european commission|member states|\beu\b|european/.test(support)) s=2;
    if(row.id==='rules'&&/(regulation|standard|fund|programme|program|procurement|screening|export control|state aid)/.test(`${direct} ${support}`)) s=Math.max(s,3);
    return clamp(s,1,4);
  }
  function actorFor(row){
    if(row.id==='knowledge') return 'EU & national research ministries, funders and universities';
    if(row.id==='infrastructure') return 'European Commission, Member States and infrastructure funders';
    if(row.id==='conversion') return 'European Commission, Member States, public investors and procurers';
    return 'European Commission, Council and Member States';
  }

  function recencyScore(x,now){
    const d=new Date(dateFor(x)); if(Number.isNaN(d.getTime())) return 0;
    const days=Math.max(0,(now-d)/(86400000));
    if(days<=14) return 2;
    if(days<=45) return 1;
    if(days<=90) return .5;
    return 0;
  }

  function cellEvidencePass(x,evidence,row,column){
    // A Frontier cell is a substantive claim, not a keyword bucket.  The observed
    // sentence/headline must itself express the mechanism named by the cell.
    // Supporting abstracts can supply EU context, but cannot manufacture the cell.
    const d=norm(`${candidateWhat(x)} ${signalTheme(x)} ${clean(x.signal_note||x._evidencePoint||'')}`);
    const support=norm(`${clean(evidence?.title||'')} ${clean(evidence?.summary||'')}`);
    const t=`${d} ${support}`;
    const ext=/\b(china|chinese|united states|us|american|foreign|non-eu|taiwan|japan|south korea|korea|uk|britain|canada)\b/;
    const knowledge=/\b(researcher|researchers|scientist|scientists|academic|academics|faculty|doctoral|phd|research talent|scientific talent|research workforce|science workforce|research collaboration|scientific collaboration|knowledge flow|knowledge flows|skills)\b/;
    const infra=/\b(compute|computing|supercomputer|cloud|data center|data centre|semiconductor|semiconductors|chip|chips|microelectronics|quantum|reactor|nuclear|grid|electricity|energy|battery|batteries|lithium|critical mineral|critical minerals|critical raw material|critical raw materials|rare earth|materials|instrument|instruments|facility|facilities|infrastructure|telecom|5g|6g|satellite|cable|supply chain|supply chains)\b/;
    const conversion=/\b(firm|firms|company|companies|startup|start-up|scale-up|scaleup|manufacturer|manufacturing|industrial|industry|product|products|commercialisation|commercialization|market|capital|venture|investment|investor|procurement|patent|patents|production|factory|factories|defence|defense|dual-use|dual use)\b/;
    const rules=/\b(export control|export controls|regulation|regulatory|standard|standards|rule|rules|governance|funding programme|funding program|framework programme|framework program|screening|research security|restriction|restrictions|ban|bans|law|laws|decision|permit|permits|subsidy|subsidies|state aid|sanction|sanctions)\b/;

    if(row.id==='knowledge'){
      if(!knowledge.test(d)) return false;
      if(column.id==='A') return /brain gain|talent inflow|attract(?:ing|ion)?|retain(?:ing|ed)?|recruit(?:ing|ment)?|return(?:ing)? researchers?|researchers? return|scientists? return|inflow|arrival|mobility into|relocat(?:e|ing|ion).{0,35}(?:eu|europe)/.test(d);
      if(column.id==='B') return /research security|screening|restrict|barrier|closed lab|cut.{0,35}collabor|suspend.{0,35}collabor|exclude|visa restriction|security review/.test(d) && /cost|delay|burden|slower|fragment|reduce|cut|loss|declin|restrict|barrier|closed|suspend|exclude/.test(d);
      if(column.id==='C') return ext.test(d) && /depend|reliance|rely|access|collabor|mobility|recruit|expertise|foreign talent|international talent/.test(d) && /excellence|performance|capabilit|competitive|frontier|benefit|strength|access|quality/.test(d);
      return /brain drain|researcher outflow|researchers? (?:leave|leaving|left)|scientists? (?:leave|leaving|left)|academic(?:s)? (?:leave|leaving|left)|talent outflow|talent loss|loss of (?:research|scientific) talent|unable to retain|failure to retain|retention crisis|depart(?:ure|ing)|relocat(?:e|ing|ion).{0,35}(?:abroad|outside europe|united states|us)|moving abroad/.test(d);
    }
    if(row.id==='infrastructure'){
      if(!infra.test(d)) return false;
      if(column.id==='A') return /build|expand|invest|onshor|domestic|european capacity|eu-led|control over|alternative supplier|diversif|self-suff|sovereign/.test(d) && /capacity|capabilit|competitive|scale|leading|investment|access|resilien/.test(d);
      if(column.id==='B') return /sovereign|autonomy|locali|onshor|domestic|european|de-risk|derisk/.test(d) && /cost|delay|lag|slow|shortage|expensive|subscale|fragment|burden/.test(d);
      if(column.id==='C') return ext.test(d) && /depend|reliance|rely|access|vendor|supplier|import|foreign technology|non-eu/.test(d) && /scale|performance|capacity|frontier|advanced|fast|competitive|capabilit/.test(d);
      return /cut off|cutoff|loss of access|access lost|shortage|ban|block|disrupt|chokepoint|bottleneck|no substitute|unable to access|outage|supply cut|restricted access/.test(d) && /depend|reliance|access|capacity|capabilit|competitive|shortage|substitute/.test(d);
    }
    if(row.id==='conversion'){
      if(!conversion.test(d)) return false;
      if(column.id==='A') return /scale|lead|champion|expand|invest|procurement|commerciali|manufactur|production|factory|market share/.test(d) && /eu|europe|european|domestic|home-grown|homegrown|autonomy|sovereign/.test(d);
      if(column.id==='B') return /sovereign|autonomy|protect|locali|onshor|domestic|de-risk|derisk|regulat/.test(d) && /cost|subscale|delay|fragment|burden|slower|niche|expensive/.test(d);
      if(column.id==='C') return ext.test(d) && /foreign capital|foreign market|us market|american market|foreign platform|depend|reliance|rely|access|scale abroad/.test(d) && /scale|growth|performance|competitive|commerciali|market access/.test(d);
      return /firm exit|firms exit|exit europe|move abroad|moving abroad|relocat.{0,30}abroad|acquired by|foreign acquisition|closure|shut down|hollow|declin.{0,30}(?:firm|production|manufactur|capabilit)|lost production|loss of production|los(?:e|es|ing) (?:[^.]{0,35})?production capacity|loss of (?:[^.]{0,35})?production capacity|funding gap|scale-up gap|scaleup gap|fail.{0,20}scale|firms? fall behind/.test(d);
    }
    if(!rules.test(d)) return false;
    if(column.id==='A') return /adopted|sets? (?:a )?standard|standard adopted|global standard|funding programme|funding program|framework programme|framework program|procurement|state aid|subsid|rule-set|rule set/.test(d) && /lead|advantage|autonomy|scale|competitive|market|innovation|research|technology/.test(d);
    if(column.id==='B') return /research security|screening|restrict|export control|regulat|de-risk|derisk|sovereign|autonomy|ban/.test(d) && /cost|delay|burden|fragment|slower|collaboration|mobility|access/.test(d);
    if(column.id==='C') return /foreign standards|foreign rules|us rules|american rules|platform rules|export licen[cs]e|non-eu rules|non-eu standards/.test(d) && /follow|adopt|depend|reliance|rely|access/.test(d) && /performance|scale|competitive|access|innovation|research|technology/.test(d);
    return /gridlock|cannot decide|unable to decide|decision delay|blocked by|foreign rules|foreign standards|export controls|sanctions|exclusion/.test(d) && /blocked|loses? access|loss of access|declin|fall behind|delay|cannot|unable|depend|competitive|innovation|research|technology/.test(d);
  }

  function whyQualifies(flags,column,row){
    const parts=[];
    if(flags.sustain) parts.push('changes whether the EU could sustain the activity without non-EU reliance');
    if(flags.compete) parts.push('changes whether an independent EU position could remain competitive');
    if(flags.failure) parts.push('reveals a condition that could make access, capability or performance fail');
    let s=parts.length?parts.join('; '):'changes the EU independence–competitiveness position';
    return `${s}. It maps to ${row.name} / ${column.name}.`;
  }

  function classifySignal(x,data,index,now=new Date()){
    if(!x||typeof x!=='object') return null;
    const evidence=evidenceFor(x,index);
    const rows=rowScores(x,evidence);
    const questions=questionScores(x,evidence),flags=questionFlags(questions);
    const qCount=Object.values(flags).filter(Boolean).length;
    const euLink=euLinkScore(x,evidence);
    const primary=candidateWhat(x);
    const primaryQuestions={
      sustain:hitCount(primary,INDEPENDENCE_TERMS),
      compete:hitCount(primary,COMPETITIVENESS_TERMS),
      failure:hitCount(primary,FAILURE_TERMS)
    };
    const primaryMoves=Object.values(primaryQuestions).some(v=>v>0);
    const primaryNorm=norm(primary);
    const directEU=/\beu\b|european union|european commission|europe\b|member states/.test(primaryNorm);
    const strategicDomain=hitCount(primary,INDIRECT_DOMAIN_TERMS)>0||/\bai\b/.test(primaryNorm);
    const strategicActor=/\b(china|chinese|united states|us|american|russia|russian|taiwan|india|japan|south korea|korea|uk|britain|canada)\b/.test(primaryNorm);
    const strategicIndirect=strategicDomain&&strategicActor;
    const structuralTalentLoss=/brain drain|researcher outflow|research talent outflow|scientific talent outflow|talent loss/.test(primaryNorm);
    const dynamic=hitCount(`${primary} ${clean(x.signal_note||x._evidencePoint||'')}`,EVENT_TERMS)>0 || x._origin==='Weak signal' || structuralTalentLoss;
    const evidenceScopedEU=x._origin==='Evidence signal' && euLink>=3 && /\beu\b|european union|european commission|europe\b|member states/.test(norm(`${clean(evidence?.title||'')} ${clean(x.anchor||'')}`));

    if(qCount===0 || !primaryMoves || euLink<1.4 || (!directEU&&!strategicIndirect&&!evidenceScopedEU) || !dynamic) return null;

    // Try rows in evidence-score order and keep the first row/column whose observed
    // statement actually satisfies that cell's semantic contract.  This prevents
    // a stray acronym or generic word such as "research" from filling a sparse cell.
    const tieOrder=['knowledge','infrastructure','conversion','rules'];
    const rowOptions=tieOrder.map(id=>({id,score:rows[id]||0})).sort((a,b)=>b.score-a.score||tieOrder.indexOf(a.id)-tieOrder.indexOf(b.id));
    let row=null,rowPick=null,materiality=0,direction=null,column=null;
    for(const opt of rowOptions){
      const r=ROWS.find(v=>v.id===opt.id);
      const m=materialityScore(x,evidence,r);
      if(m<2.4) continue;
      const dir=directionScores(x,evidence,r,questions);
      const col=columnFor(dir);
      if(!cellEvidencePass(x,evidence,r,col)) continue;
      row=r; rowPick=opt; materiality=m; direction=dir; column=col; break;
    }
    if(!row||!column) return null;

    const reach=reachScore(rows),irreversibility=irreversibilityScore(x,row,column),attention=attentionGapScore(x),actionability=actionabilityScore(x,row,evidence);
    const triage=reach+irreversibility+attention+actionability;
    const multi=qCount>=2?1.5:0;
    const crossDirection=(flags.sustain&&flags.compete&&Math.sign(direction.autonomy)!==Math.sign(direction.performance))?1:0;
    const columnWeight=column.id==='D'?2:column.id==='A'?1.25:1;
    const recency=recencyScore(x,now)+(x.new_this_scan?1:0);
    const overall=triage+multi+crossDirection+columnWeight+recency;
    const cell=CELL_NAMES[row.id][column.id];
    return {
      id:norm(linkFor(x)||candidateWhat(x)),
      title:candidateWhat(x),
      source:sourceFor(x),
      date:dateFor(x),
      link:linkFor(x),
      origin:x._origin||'Weak signal',
      newThisScan:!!x.new_this_scan,
      theme:signalTheme(x),
      anchor:clean(x.anchor||''),
      evidenceTitle:clean(evidence?.title||''),
      row,rowScore:rowPick.score,column,cellName:cell[0],cellSubtitle:cell[1],
      questions,questionFlags:flags,questionCount:qCount,
      direction,triage:{reach,irreversibility,attentionGap:attention,actionability,total:triage},
      actor:actorFor(row),
      why:whyQualifies(flags,column,row),
      originalWhy:signalWhy(x),
      materiality,euLink,overall,
      strongCandidate:qCount>=2,
      confidence:clamp(Math.round((Math.min(6,materiality)/6*.35 + Math.min(6,euLink)/6*.2 + Math.min(3,qCount)/3*.25 + Math.min(8,Math.abs(direction.autonomy)+Math.abs(direction.performance))/8*.2)*100),35,96)
    };
  }

  function concentration(items,keyFn){
    const m=new Map();for(const x of items){const k=keyFn(x);m.set(k,(m.get(k)||0)+1)}
    return [...m.entries()].sort((a,b)=>b[1]-a[1]||String(a[0]).localeCompare(String(b[0])))[0]||['None',0];
  }

  function buildFrontier(data,opts={}){
    const now=opts.now?new Date(opts.now):new Date();
    const index=buildEvidenceIndex(data);
    const raw=dedupeCandidates([...weakCandidates(data),...evidenceCandidates(data)]);
    const signals=raw.map(x=>classifySignal(x,data,index,now)).filter(Boolean);
    signals.sort((a,b)=>b.overall-a.overall||b.triage.total-a.triage.total||String(b.date).localeCompare(String(a.date))||a.title.localeCompare(b.title));
    const cells={};for(const r of ROWS){cells[r.id]={};for(const c of COLUMNS)cells[r.id][c.id]=[]}
    for(const s of signals)cells[s.row.id][s.column.id].push(s);
    for(const r of ROWS)for(const c of COLUMNS)cells[r.id][c.id].sort((a,b)=>b.triage.total-a.triage.total||b.overall-a.overall);
    const top=signals.slice(0,7);
    const [topRow,topRowCount]=concentration(signals,x=>x.row.name);
    const [topColumn,topColumnCount]=concentration(signals,x=>`${x.column.id}. ${x.column.name}`);
    const weakTotal=Array.isArray(data?.strand_c)?data.strand_c.length:0;
    const evidenceTotal=(Array.isArray(data?.strand_a)?data.strand_a.length:0)+(Array.isArray(data?.strand_b)?data.strand_b.length:0);
    return {
      signals,cells,top,
      stats:{weakTotal,evidenceTotal,candidatePool:raw.length,qualifying:signals.length,strong:signals.filter(x=>x.strongCandidate).length,alarm:signals.filter(x=>x.column.id==='D').length,opening:signals.filter(x=>x.column.id==='A').length},
      pattern:{topRow,topRowCount,topColumn,topColumnCount},
      lastUpdated:clean(data?.last_updated||''),
      rows:ROWS,columns:COLUMNS,cellNames:CELL_NAMES
    };
  }

  return {ROWS,COLUMNS,CELL_NAMES,buildEvidenceIndex,classifySignal,buildFrontier,weakCandidates,evidenceCandidates,questionScores,rowScores};
});
