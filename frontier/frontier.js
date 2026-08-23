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
    infrastructure:['compute','computing','supercomputer','artificial intelligence','ai model','ai models','ai video model','ai system','ai systems','foundation model','foundation models','data center','data centre','cloud','semiconductor','chip','chips','microelectronics','quantum','reactor','nuclear','grid','electricity','energy','battery','batteries','lithium','critical mineral','critical minerals','critical raw material','critical raw materials','rare earth','materials','instrument','instruments','facility','facilities','infrastructure','telecom','5g','6g','satellite','cable','supply chain','supply chains','strategic resource','strategic resources','critical technology','critical technologies','technology value chain','technology value chains','input','inputs'],
    conversion:['firm','firms','company','robot','robots','robotics','companies','startup','start-up','scale-up','manufacturer','manufacturing','industrial','industry','product','products','commercial','commercialisation','commercialization','market','capital','venture','investment','investor','procurement','patent','patents','defence','defense','military','dual-use','dual use','capability','capabilities','production','factory','factories'],
    rules:['export control','export controls','sanction','sanctions','regulation','regulatory','standard','standards','rule','rules','governance','institution','institutions','funding programme','funding program','programme','program','screening','research security','restriction','restrictions','ban','bans','law','laws','framework','decision','permit','permits','subsidy','subsidies','state aid']
  };

  const INDEPENDENCE_TERMS=['sovereign','sovereignty','autonomy','autonomous','strategic autonomy','dependence','dependency','dependencies','reliance','rely','non-eu','foreign supplier','external supplier','externally controlled','access','control','diversif','de-risk','derisk','self-suff','domestic capacity','european capacity','local capacity','own technology','own capability','supply security','vendor','partner','partnership','open-weight','open source','chinese firms','chinese companies','us firms','american firms','imported technology','technology vendor','lock-in','lock in'];
  const COMPETITIVENESS_TERMS=['competit','performance','frontier','leading','leader','best available','capacity','capability','capabilities','scale','scaling','productivity','innovation','investment','invest','patent','market share','advanced','high-tech','high tech','talent','compute','supercomputer','lag','behind','fragmentation','subscale','cost','costly','expensive','shortage','declin','slow','delay','miss the','hollowing','brain drain'];
  const FAILURE_TERMS=['fail','failure','risk','vulnerab','exposure','weaponis','weaponiz','restrict','restriction','ban','block','cut off','cutoff','loss of access','suspend','withdraw','sanction','shortage','chokepoint','bottleneck','dependency','reliance','brain drain','hollowing','gridlock','delay','cannot','unable','no substitute','security cut','fragmentation','coercion','retreat','curb','curbs','struggl','fail to adopt','failed to adopt','decoupl'];
  const EVENT_TERMS=['launch','launched','adopt','adopted','order','ordered','restrict','restricted','curb','curbs','ban','banned','suspend','suspended','withdraw','retreat','invest','investment','build','building','expand','expansion','shift','shifting','becoming','increase','increasing','decrease','decline','declining','cut','cuts','open','opened','close','closed','facilitat','approve','approved','reject','rejected','propos','sign','signed','join','joined','leave','left','losing','overtook','outpace','outpaced','fragment','lag','behind','depend','reliance','consolidat','scale','scaling','deploy','deployed','designat','mandat','require','warn','warning','fail','failed'];
  const INDIRECT_DOMAIN_TERMS=['artificial intelligence','ai model','ai models','supercomputer','compute','data center','data centre','cloud','semiconductor','chip','quantum','nuclear','reactor','solar','battery','critical mineral','critical raw material','robot','robotics','defence technology','defense technology','dual-use','dual use','patent','technology','research collaboration','scientific collaboration','research cooperation','scientific cooperation'];
  const GEOPOLITICAL_ACTORS=['china','chinese','united states',' us ','american','russia','russian','taiwan','india','japan','south korea','korea','uk','britain','canada'];
  const EU_SCOPE_RE=/\b(eu|europe|european|european union|european commission|member states|austria|austrian|belgium|belgian|bulgaria|bulgarian|croatia|croatian|cyprus|cypriot|czechia|czech|denmark|danish|estonia|estonian|finland|finnish|france|french|germany|german|greece|greek|hungary|hungarian|ireland|irish|italy|italian|latvia|latvian|lithuania|lithuanian|luxembourg|malta|maltese|netherlands|dutch|poland|polish|portugal|portuguese|romania|romanian|slovakia|slovak|slovenia|slovenian|spain|spanish|sweden|swedish)\b/;

  const AUTONOMY_UP=['reduce strategic depend','reduce depend','reducing depend','diversif','sovereign control','digital sovereignty','strategic autonomy','self-suff','domestic capacity','european capacity','home-grown','homegrown','reshor','local production','own technology','own capability','control over','alternative supplier','alternative suppliers','open-weight','open source','eu-led','european infrastructure'];
  const AUTONOMY_DOWN=['more dependent','dependence on','dependent on','strategic dependency','strategic dependencies','external dependency','external dependencies','critical dependency','critical dependencies','reliance on','rely on','non-eu technology','non-eu vendor','foreign supplier','foreign suppliers','external supplier','externally controlled','on others terms',"others' terms",'loss of access','access lost','brain drain','people and ideas leave','imported technology','foreign technology','chinese companies','restricted access','partner changes','vendor lock','lock-in','cut supply','hollowing out','chinese firms','us firms','american firms'];
  const PERFORMANCE_UP=['expand capabilities','expands capabilities','build capacity','capacity-building','capability-building','investment','invests','investing','supercomputer','frontier','leading','leader','outpace','overtook','scale','scaling','competitive','competitiveness','productivity','talent inflow','brain gain','open-weight','advanced technology','advanced technologies','fast','growth','innovation capacity','sets pace'];
  const PERFORMANCE_DOWN=['less competitive','lag behind','lagging','left behind','miss the','fragmentation','fragmented','subscale','costly','expensive','higher cost','cost increase','security cuts','cuts collaboration','brain drain','hollowing','no capability','no substitute','shortage','bottleneck','chokepoint','vulnerability','vulnerabilities','exposure','delay','slower','declining','loss of capacity','losing capacity','unable to','cannot decide','performance price','operational reasons','slow scientific','slow research','raise cost','raises cost','raising cost','struggl','cannot decide','fail to adopt','failed to adopt'];

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
    for(const x of (Array.isArray(data?.strand_a)?data.strand_a:[])){
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
    for(const group of RadarInsights.buildInsights({strand_a:Array.isArray(data?.strand_a)?data.strand_a:[],strand_b:[],strand_c:[]})){
      for(const x of group.items){
        const text=`${x.point} ${x.title} ${x.watchTheme||''} ${x.why||''}`;
        const strategicKnowledge=/research security|knowledge security|science diplomacy|research collaboration|scientific collaboration|research cooperation|scientific cooperation|researcher mobility|research mobility|research talent|brain drain|brain gain|talent inflow|talent outflow/i.test(text);
        const dynamic=hitCount(text,EVENT_TERMS)>0 || hitCount(text,INDEPENDENCE_TERMS)>=2 || hitCount(text,COMPETITIVENESS_TERMS)>=2 || strategicKnowledge;
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
    // Knowledge-B is explicitly the research-security/openness trade-off: safeguards can
    // increase control over sensitive research while imposing collaboration/mobility costs.
    // Without this directional rule, generic failure words (restrict/delay/risk) push the
    // same evidence into D before the semantic B-cell test gets a chance to evaluate it.
    if(row.id==='knowledge' && /research security|knowledge security|security screening|research screening/.test(direct)){
      if(/protect|safeguard|sensitive|security|screening|interference|espionage|restrict/.test(direct)) autonomyUp+=2.2;
      if(/restrict|barrier|delay|slow|exclude|suspend|cut|collabor|mobility|openness/.test(direct)) performanceDown+=2.2;
    }
    if(row.id==='knowledge' && /brain drain|researcher outflow|talent outflow|talent loss|researchers? (?:leave|leaving|left)|scientists? (?:leave|leaving|left)|unable to retain|failure to retain|retention crisis/.test(direct)){autonomyDown+=4;performanceDown+=4}
    if(row.id==='knowledge' && /brain gain|talent inflow|attract(?:ing|ion)?.{0,30}(?:researcher|scientist|talent)|retain(?:ing|ed)?.{0,30}(?:researcher|scientist|talent)|(?:researcher|scientist).{0,25}return/.test(direct)){autonomyUp+=3;performanceUp+=3}
    if(row.id==='knowledge'){
      const kt=norm(`${direct} ${support}`);
      const externalKnowledge=/(?:foreign|non-eu|third-country|third country|china|chinese|united states|american).{0,55}(?:researcher|scientist|research talent|scientific talent|expertise|research collaboration|scientific collaboration|research cooperation)|(?:researcher|scientist|research talent|scientific talent|expertise|research collaboration|scientific collaboration|research cooperation).{0,55}(?:foreign|non-eu|third-country|third country|china|chinese|united states|american)/.test(kt);
      const knowledgeGain=/benefit|strengthen|boost|improve|excellence|leading|competitive|competitiveness|capacity|capability|access to|fill(?:s|ing)? gap|critical expertise/.test(kt);
      if(externalKnowledge && knowledgeGain){autonomyDown+=3;performanceUp+=2.8}
      const euTalentBuild=EU_SCOPE_RE.test(kt) && /brain gain|talent inflow|attract(?:ing|ion)?|retain(?:ing|ed)?|recruit|returning researchers|researchers return/.test(kt);
      if(euTalentBuild && /researcher|scientist|research talent|scientific talent|research workforce/.test(kt)){autonomyUp+=2.6;performanceUp+=2.6}
    }

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
    if(EU_SCOPE_RE.test(direct)) s+=3;
    if(EU_SCOPE_RE.test(support)) s+=1.5;
    // Scanner-level EU relevance may come from abstract/body evidence that is not
    // repeated in the concise summary. Preserve that vetted scope downstream.
    if(clean(evidence?.eu_relevance||'').toLowerCase()==='direct') s=Math.max(s,3);
    else if(clean(evidence?.eu_relevance||'').toLowerCase()==='derived') s=Math.max(s,1.5);
    return s;
  }

  function materialityScore(x,evidence,row){
    const direct=norm(`${candidateWhat(x)} ${signalTheme(x)} ${clean(x.signal_note||x._evidencePoint||'')}`);
    const support=norm(`${clean(x.anchor||'')} ${clean(evidence?.title||'')} ${clean(evidence?.summary||'')}`);
    const directHits=hitCount(direct,ROW_TERMS[row.id]);
    const supportHits=hitCount(support,ROW_TERMS[row.id]);
    return directHits*2.4+Math.min(3,supportHits)*(x._origin==='Evidence signal'?1.2:.6);
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
    // The matrix is not a literal-label matcher.  A signal qualifies when the
    // document establishes (1) the row mechanism and (2) the two directional
    // dimensions represented by the column.  Supporting abstracts may supply
    // those relationships for evidence-derived signals; weak signals must carry
    // the mechanism in their own headline/statement.
    const d=norm(`${candidateWhat(x)} ${signalTheme(x)} ${clean(x.signal_note||x._evidencePoint||'')}`);
    const support=norm(`${clean(evidence?.title||'')} ${clean(evidence?.summary||'')}`);
    const t=`${d} ${support}`;
    const evidenceSignal=x._origin==='Evidence signal';
    const ext=/\b(china|chinese|united states|us|american|foreign|non-eu|third-country|third country|taiwan|japan|south korea|korea|uk|britain|canada)\b/;
    const eu=EU_SCOPE_RE;
    const euScoped=eu.test(t) || (evidenceSignal && clean(evidence?.eu_relevance||'').toLowerCase()==='direct');

    const rowPatterns={
      knowledge:/\b(researcher|researchers|scientist|scientists|academic|academics|faculty|doctoral|phd|research talent|scientific talent|research workforce|science workforce|research collaboration|scientific collaboration|research cooperation|scientific cooperation|knowledge flow|knowledge flows|skills|research careers?|research mobility|researcher mobility|science diplomacy|open science|research security|higher education)\b/,
      infrastructure:/\b(compute|computing|supercomputer|cloud|data center|data centre|semiconductor|semiconductors|chip|chips|microelectronics|quantum|reactor|reactors|nuclear|grid|electricity|energy|battery|batteries|lithium|critical mineral|critical minerals|critical raw material|critical raw materials|rare earth|materials|instrument|instruments|facility|facilities|infrastructure|telecom|telecommunications|5g|6g|satellite|cable|supply chain|supply chains|input|inputs|technology vendor|technology vendors|value chain|value chains)\b/,
      conversion:/\b(firm|firms|company|companies|startup|start-up|scale-up|scaleup|manufacturer|manufacturing|industrial|industry|product|products|commercialisation|commercialization|market|capital|venture|investment|investor|procurement|patent|patents|production|factory|factories|defence|defense|dual-use|dual use|industrial capacity|production capacity|competitiveness fund)\b/,
      rules:/\b(export control|export controls|regulation|regulatory|standard|standards|rule|rules|governance|funding programme|funding program|framework programme|framework program|screening|research security|restriction|restrictions|ban|bans|law|laws|decision|permit|permits|subsidy|subsidies|state aid|sanction|sanctions|licensing|licence|license|policy framework|institutional)\b/
    };
    const rowRe=rowPatterns[row.id];
    const rowDirect=rowRe.test(d),rowSupport=rowRe.test(support);
    if(!rowDirect && !(evidenceSignal&&rowSupport)) return false;

    // Directional cues are intentionally semantic and broad.  They capture
    // dependencies, bottlenecks, capability-building, costs and gains without
    // requiring the exact words used in the cell nickname.
    const autonomyUp=/strategic autonomy|technological sovereignty|digital sovereignty|sovereign|independence|reduce.{0,45}(?:depend|reliance)|reduc(?:ing|tion).{0,45}strategic depend|diversif|de-risk|derisk|self-suff|domestic capacity|european capacity|eu-led|european infrastructure|local production|onshor|reshor|secure supply|supply security|material security|resilien|alternative supplier|own (?:technology|capability|infrastructure)|control over|strengthen.{0,35}(?:eu|european).{0,35}(?:capacity|capabilit)|eu.{0,30}(?:fund|programme|program|instrument|strategy).{0,45}(?:build|strengthen|support|boost|develop|scale)/.test(t);
    const autonomyDown=/strategic depend|critical external depend|external depend|dependence on|dependent on|dependencies|reliance on|rely on|non-eu (?:technology|vendor|supplier|provider)|foreign (?:supplier|vendor|technology|platform|capital|market|infrastructure|expertise|talent)|external (?:supplier|vendor)|import dependence|imported technology|vendor lock|lock-in|loss of access|restricted access|on others(?:'|’) terms|ceding.{0,40}(?:value|profits|leverage|technology)|foreign-controlled/.test(t);
    const performanceUp=/competit|performance|frontier|leading|leader|advanced|scale|scaling|growth|productivity|innovation|investment|market access|access to|capacity|capabilit|excellence|quality|benefit|strengthen|expand|build|deploy|commerciali|sets? pace|industrial leadership|value creation|resilien/.test(t);
    const performanceDown=/less competitive|lag|behind|shortage|bottleneck|chokepoint|vulnerab|exposure|risk|costly|expensive|higher cost|delay|slow|fragment|subscale|declin|loss|losing|hollow|gap|cannot|unable|no substitute|disrupt|cut off|cutoff|blocked|constraint|barrier|threat|weakness|shortcoming|ceding|two-speed|two speed/.test(t);

    if(row.id==='knowledge'){
      if(column.id==='D'){
        // Keep the specific cell specific: the loss must concern Europe/an EU member,
        // not merely appear somewhere in a Europe-related document.
        const strongLoss=/brain drain|researcher outflow|researchers? (?:leave|leaving|left)|scientists? (?:leave|leaving|left)|academics? (?:leave|leaving|left)|talent outflow|loss of (?:research|scientific) talent|unable to retain|failure to retain|retention crisis|moving abroad/.test(d);
        if(strongLoss && eu.test(`${d} ${norm(evidence?.title||'')}`)) return true;
        // Generic "talent loss" is too ambiguous on its own; require the EU/member-state
        // subject to be close to the loss statement.
        const euPhrase='(?:eu|europe|european|member states|austria|belgium|bulgaria|croatia|cyprus|czech|denmark|estonia|finland|france|germany|greece|hungary|ireland|italy|latvia|lithuania|luxembourg|malta|netherlands|poland|portugal|romania|slovakia|slovenia|spain|sweden)';
        return new RegExp(`(?:${euPhrase}).{0,55}talent loss|talent loss.{0,55}(?:${euPhrase})`).test(d);
      }
      if(column.id==='A') return performanceUp && (autonomyUp || /brain gain|talent inflow|attract|retain|recruit|return|research collaboration|scientific collaboration|research cooperation|science diplomacy|knowledge flow/.test(t)) && euScoped;
      if(column.id==='B') return performanceDown && /research security|screening|visa|restrict|barrier|exclude|suspend|closed lab|collabor|mobility|openness/.test(t) && (autonomyUp||/security|sovereign|protect/.test(t));
      return performanceUp && (autonomyDown || (ext.test(t)&&/collabor|cooperat|mobility|recruit|expertise|foreign talent|international talent|science diplomacy|knowledge flow|access/.test(t)));
    }

    if(row.id==='infrastructure'){
      if(column.id==='A') return autonomyUp && performanceUp;
      if(column.id==='B') return autonomyUp && performanceDown;
      if(column.id==='C') return (autonomyDown || (ext.test(t)&&/supplier|vendor|technology|compute|cloud|material|input|supply chain|reactor|semiconductor|chip|infrastructure/.test(t))) && performanceUp;
      return (autonomyDown||/access|supply|dependency/.test(t)) && performanceDown;
    }

    if(row.id==='conversion'){
      if(column.id==='A') return (autonomyUp||/\b(eu|european|europe)\b.{0,45}(?:invest|scale|manufactur|procurement|industrial|production)/.test(t)) && performanceUp;
      if(column.id==='B') return (autonomyUp||/protect|locali|onshor|domestic|de-risk|derisk/.test(t)) && performanceDown;
      if(column.id==='C') return (autonomyDown||ext.test(t)) && performanceUp && /foreign capital|foreign market|market access|foreign platform|scale abroad|investment|supplier|partner|global market|china exposure/.test(t);
      return performanceDown && /firm exit|firms exit|exit europe|move abroad|moving abroad|relocat|foreign acquisition|closure|shut down|hollow|lost production|loss of production|production capacity|funding gap|scale-up gap|scaleup gap|fail.{0,20}scale|firms? fall behind|industrial decline|ceding profits|ceding value|displaced competition|two-speed|two speed/.test(t);
    }

    // Rules/institutions are broader than a single named regulation: EU-created
    // frameworks can be openings; foreign regimes can create productive dependence;
    // fragmentation/delay can create double loss.
    if(column.id==='A') return performanceUp && (autonomyUp || /\b(eu|european)\b.{0,35}(?:framework|programme|program|regulation|standard|strategy|fund|governance|procurement|instrument)/.test(t));
    if(column.id==='B') return performanceDown && (autonomyUp||/research security|screening|de-risk|derisk|sovereign|protect/.test(t)) && /restrict|export control|regulat|ban|sanction|screening|security|licen|compliance|burden/.test(t);
    if(column.id==='C') return performanceUp && (autonomyDown||/foreign standards|foreign rules|us rules|american rules|platform rules|export licen[cs]e|non-eu rules|non-eu standards|us export-control|us export control/.test(t));
    return performanceDown && /gridlock|cannot decide|unable to decide|decision delay|blocked by|institutional constraint|fragmented governance|foreign rules|foreign standards|export controls|sanctions|exclusion|regulatory fragmentation|regulatory delay|delayed/.test(t);
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
    const directEU=EU_SCOPE_RE.test(primaryNorm);
    const strategicDomain=hitCount(primary,INDIRECT_DOMAIN_TERMS)>0||/\bai\b/.test(primaryNorm);
    const strategicActor=/\b(china|chinese|united states|us|american|russia|russian|taiwan|india|japan|south korea|korea|uk|britain|canada)\b/.test(primaryNorm);
    const strategicIndirect=strategicDomain&&strategicActor;
    const structuralTalentLoss=/brain drain|researcher outflow|research talent outflow|scientific talent outflow|talent loss/.test(primaryNorm);
    const supportNorm=norm(`${clean(evidence?.title||'')} ${clean(evidence?.summary||'')}`);
    const evidenceScopedEU=x._origin==='Evidence signal' && euLink>=3 && (
      clean(evidence?.eu_relevance||'').toLowerCase()==='direct' ||
      EU_SCOPE_RE.test(norm(`${sourceFor(x)} ${clean(evidence?.source||'')} ${clean(evidence?.title||'')} ${clean(x.anchor||'')} ${supportNorm}`))
    );
    // Analytical reports often describe structural dependencies/capability shifts rather than
    // discrete "events".  Treat a supported document-level movement as dynamic enough for
    // Frontier classification; weak signals still have to move in their own headline.
    const structuralEvidence=x._origin==='Evidence signal' && qCount>=1 && (
      hitCount(`${primary} ${supportNorm}`,INDEPENDENCE_TERMS)>=1 ||
      hitCount(`${primary} ${supportNorm}`,COMPETITIVENESS_TERMS)>=2 ||
      hitCount(`${primary} ${supportNorm}`,FAILURE_TERMS)>=1
    );
    const knowledgeStructuralEvidence=x._origin==='Evidence signal' && /research security|knowledge security|science diplomacy|research collaboration|scientific collaboration|research cooperation|scientific cooperation|researcher mobility|research mobility|research talent|brain drain|brain gain|talent inflow|talent outflow/.test(norm(`${primary} ${supportNorm}`));
    const dynamic=hitCount(`${primary} ${clean(x.signal_note||x._evidencePoint||'')}`,EVENT_TERMS)>0 || x._origin==='Weak signal' || structuralTalentLoss || structuralEvidence || knowledgeStructuralEvidence;
    const movementSupported=primaryMoves || (x._origin==='Evidence signal'&&(qCount>=1||knowledgeStructuralEvidence));

    if((qCount===0&&!knowledgeStructuralEvidence) || !movementSupported || euLink<1.4 || (!directEU&&!strategicIndirect&&!evidenceScopedEU) || !dynamic) return null;

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
    const evidenceTotal=(Array.isArray(data?.strand_a)?data.strand_a.length:0);
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
