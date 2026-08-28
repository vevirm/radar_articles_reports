(function(root,factory){
  const api=factory(root.RadarInsights);
  if(typeof module==='object'&&module.exports) module.exports=api;
  root.SovereigntyFrontier=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(RadarInsights){
  'use strict';

  const ROWS=[
    {id:'knowledge',name:'People & knowledge',short:'People & knowledge',description:'Researchers, skills, collaboration and knowledge flows.'},
    {id:'infrastructure',name:'Tools & infrastructure',short:'Tools & infrastructure',description:'Compute, data, chips, materials, energy and facilities.'},
    {id:'conversion',name:'Firms & scale',short:'Firms & scale',description:'Turning research into firms, products, procurement and industrial capacity.'},
    {id:'rules',name:'Rules & coordination',short:'Rules & coordination',description:'Standards, security rules, funding programmes and decision speed.'}
  ];
  const COLUMNS=[
    {id:'A',name:'Stronger on both',direction:'more control · more competitive',tone:'opportunity'},
    {id:'B',name:'More control, more cost',direction:'more control · less competitive',tone:'tradeoff'},
    {id:'C',name:'Faster, but dependent',direction:'less control · more competitive',tone:'exposure'},
    {id:'D',name:'Weaker on both',direction:'less control · less competitive',tone:'alarm'}
  ];
  const CELL_NAMES={
    knowledge:{A:['Attract and keep talent','people and knowledge strengthen Europe'],B:['Protection slows exchange','more control, less collaboration'],C:['Capability from outside','stronger work, but reliant on others'],D:['Talent and knowledge leave','Europe loses people and capability']},
    infrastructure:{A:['European capacity','Europe owns an important tool or input'],B:['Own capacity, higher cost','more control, but performance or cost suffers'],C:['Access without control',"frontier access depends on others"],D:['Access lost','dependency becomes a capability loss']},
    conversion:{A:['European firms scale','research becomes European industrial strength'],B:['Protected but small','more control, but firms remain subscale'],C:['Scale with outside dependence','growth relies on foreign capital, markets or platforms'],D:['Research does not scale here','firms, value or production move away']},
    rules:{A:['Europe shapes the rules','European standards or decisions improve both position and performance'],B:['Protection adds friction','security or autonomy rules slow the system'],C:['Europe follows outside rules','performance depends on external regimes'],D:['Rules arrive too late','fragmentation or delay weakens both control and competitiveness']}
  };

  const ROW_TERMS={
    knowledge:['research','science','scientific','university','universities','academic','academia','researcher','researchers','scientist','scientists','talent','skills','training','doctoral','phd','publication','research collaboration','scientific collaboration','research cooperation','scientific cooperation','horizon europe','framework programme','erc','knowledge','visa','mobility','brain drain','brain gain','open science','research security'],
    infrastructure:['compute','computing','supercomputer','artificial intelligence','ai model','ai models','ai video model','ai system','ai systems','foundation model','foundation models','data center','data centre','cloud','semiconductor','chip','chips','microelectronics','quantum','reactor','nuclear','grid','electricity','energy','battery','batteries','lithium','critical mineral','critical minerals','critical raw material','critical raw materials','rare earth','materials','instrument','instruments','facility','facilities','infrastructure','telecom','5g','6g','satellite','cable','supply chain','supply chains','strategic resource','strategic resources','critical technology','critical technologies','technology value chain','technology value chains','input','inputs'],
    conversion:['firm','firms','company','robot','robots','robotics','companies','startup','start-up','scale-up','manufacturer','manufacturing','industrial','industry','product','products','commercial','commercialisation','commercialization','market','capital','venture','investment','investor','procurement','patent','patents','defence','defense','military','dual-use','dual use','capability','capabilities','production','factory','factories'],
    rules:['export control','export controls','sanction','sanctions','regulation','regulatory','standard','standards','rule','rules','governance','institution','institutions','funding programme','funding program','programme','program','screening','research security','restriction','restrictions','ban','bans','law','laws','framework','decision','permit','permits','subsidy','subsidies','state aid']
  };

  const INFRA_CONCRETE_RE=/\b(compute|computing|supercomputer|data cent(?:er|re)|cloud|semiconductor|chip|microelectronics|quantum|reactor|nuclear|grid|electricity|energy|battery|lithium|critical mineral|critical raw material|rare earth|materials|facility|infrastructure|telecom|5g|6g|satellite|cable|supply chain|strategic resource|research infrastructure|ai factory|gigafactory)\b/i;
  const RULES_CONCRETE_RE=/\b(regulation|regulatory|governance|law|act|directive|standard|standards|framework|liability|compliance|screening|export control|sanction|state aid|procurement rule|funding programme|funding program|decision process|permit|licen[cs]e)\b/i;

  const INDEPENDENCE_TERMS=['sovereign','sovereignty','autonomy','autonomous','strategic autonomy','dependence','dependency','dependencies','reliance','rely','non-eu','foreign supplier','external supplier','externally controlled','access','control','diversif','de-risk','derisk','self-suff','domestic capacity','european capacity','local capacity','own technology','own capability','supply security','vendor','partner','partnership','open-weight','open source','chinese firms','chinese companies','us firms','american firms','imported technology','technology vendor','lock-in','lock in'];
  const COMPETITIVENESS_TERMS=['competit','performance','frontier','leading','leader','leadership','technological leadership','technology leadership','best available','capacity','capability','capabilities','scale','scaling','productivity','innovation','investment','invest','patent','market share','advanced','high-tech','high tech','talent','compute','supercomputer','lag','behind','fragmentation','subscale','cost','costly','expensive','shortage','declin','slow','delay','miss the','hollowing','brain drain'];
  const FAILURE_TERMS=['fail','failure','risk','vulnerab','exposure','weaponis','weaponiz','restrict','restriction','ban','block','cut off','cutoff','loss of access','suspend','withdraw','sanction','shortage','chokepoint','bottleneck','dependency','reliance','brain drain','hollowing','gridlock','delay','cannot','unable','no substitute','security cut','fragmentation','coercion','retreat','curb','curbs','struggl','fail to adopt','failed to adopt','decoupl'];
  const EVENT_TERMS=['launch','launched','adopt','adopted','order','ordered','restrict','restricted','curb','curbs','ban','banned','suspend','suspended','withdraw','retreat','invest','investment','build','building','expand','expansion','shift','shifting','becoming','increase','increasing','decrease','decline','declining','cut','cuts','open','opened','close','closed','facilitat','approve','approved','reject','rejected','propos','sign','signed','join','joined','leave','left','losing','overtook','outpace','outpaced','fragment','lag','behind','depend','reliance','consolidat','scale','scaling','deploy','deployed','designat','mandat','require','warn','warning','fail','failed'];
  const INDIRECT_DOMAIN_TERMS=['artificial intelligence','ai model','ai models','supercomputer','compute','data center','data centre','cloud','semiconductor','chip','quantum','nuclear','reactor','solar','battery','critical mineral','critical raw material','robot','robotics','defence technology','defense technology','dual-use','dual use','patent','technology','research collaboration','scientific collaboration','research cooperation','scientific cooperation'];
  const GEOPOLITICAL_ACTORS=['china','chinese','united states',' us ','american','russia','russian','taiwan','india','japan','south korea','korea','uk','britain','canada'];
  const EU_SCOPE_RE=/\b(eu|europe|european|european union|european commission|member states|austria|austrian|belgium|belgian|bulgaria|bulgarian|croatia|croatian|cyprus|cypriot|czechia|czech|denmark|danish|estonia|estonian|finland|finnish|france|french|germany|german|greece|greek|hungary|hungarian|ireland|irish|italy|italian|latvia|latvian|lithuania|lithuanian|luxembourg|malta|maltese|netherlands|dutch|poland|polish|portugal|portuguese|romania|romanian|slovakia|slovak|slovenia|slovenian|spain|spanish|sweden|swedish)\b/;

  const AUTONOMY_UP=['reduce strategic depend','reduce depend','reducing depend','diversif','sovereign control','digital sovereignty','strategic autonomy','self-suff','domestic capacity','european capacity','home-grown','homegrown','reshor','local production','own technology','own capability','control over','alternative supplier','alternative suppliers','open-weight','open source','eu-led','european infrastructure'];
  const AUTONOMY_DOWN=['more dependent','dependence on','dependent on','strategic dependency','strategic dependencies','external dependency','external dependencies','critical dependency','critical dependencies','reliance on','rely on','non-eu technology','non-eu vendor','foreign supplier','foreign suppliers','external supplier','externally controlled','on others terms',"others' terms",'loss of access','access lost','brain drain','people and ideas leave','imported technology','foreign technology','chinese companies','restricted access','partner changes','vendor lock','lock-in','cut supply','hollowing out','chinese firms','us firms','american firms'];
  const PERFORMANCE_UP=['expand capabilities','expands capabilities','build capacity','capacity-building','capability-building','investment','invests','investing','supercomputer','frontier','leading','leader','leadership','technological leadership','technology leadership','outpace','overtook','scale','scaling','competitive','competitiveness','productivity','talent inflow','brain gain','open-weight','advanced technology','advanced technologies','fast','growth','innovation capacity','sets pace'];
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
    const evidence=[...(Array.isArray(data?.strand_a)?data.strand_a:[]),...(Array.isArray(data?.frontier_evidence)?data.frontier_evidence:[])];
    for(const x of evidence){
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
    const evidence=[...(Array.isArray(data?.strand_a)?data.strand_a:[]),...(Array.isArray(data?.frontier_evidence)?data.frontier_evidence:[])];
    // Insight points are useful display compression, but matrix classification must not lose
    // the report/abstract that supports them. Build a lookup, then classify from the full
    // source-backed evidence record while still displaying a concise claim.
    const insightMap=new Map();
    for(const group of RadarInsights.buildInsights({strand_a:evidence,strand_b:[],strand_c:[]})){
      for(const i of group.items){
        const key=norm(i.link||i.title||'');
        if(key) insightMap.set(key,{...i,_group:group.name});
      }
    }
    for(const e of evidence){
      if(!e||typeof e!=='object') continue;
      const key=norm(e.link||e.title||'');
      const i=insightMap.get(key)||{};
      const claim=clean(i.point||RadarInsights?.completeCoreMessage?.(e.core_message||'')||e.title||'');
      const theme=clean(i.watchTheme||e.watch_theme||i._group||'');
      const fullText=clean(`${claim} ${e.title||''} ${e.summary||''} ${e.relevance_note||''} ${e.bridge_sentence||''} ${e.external_eu_bridge||''} ${theme}`);
      const strategicKnowledge=/research security|knowledge security|science diplomacy|research collaboration|scientific collaboration|research cooperation|scientific cooperation|researcher mobility|research mobility|research talent|brain drain|brain gain|talent inflow|talent outflow/i.test(fullText);
      const dynamic=hitCount(fullText,EVENT_TERMS)>0 || hitCount(fullText,INDEPENDENCE_TERMS)>=1 || hitCount(fullText,COMPETITIVENESS_TERMS)>=1 || strategicKnowledge;
      // Every admitted radar finding reaches the matrix classifier. The classifier can still reject it
      // when the evidence does not support a row/direction; we no longer drop it in a hidden pre-filter.
      void dynamic;
      out.push({
        headline:claim||clean(e.title||''),
        title:clean(e.title||''),
        source:clean(e.source||i.source||''),
        date:clean(e.date||i.date||''),
        link:clean(e.link||i.link||''),
        strand:clean(e.strand||i.strand||'A'),
        type:clean(e.type||i.itemType||''),
        watch_theme:theme,
        anchor:clean(e.title||''),
        why_it_matters:clean(i.why||e.relevance_note||''),
        signal_note:claim,
        core_message:claim,
        new_this_scan:!!e.new_this_scan,
        _origin:'Evidence signal',
        _evidencePoint:claim,
        _evidenceSummary:clean(e.summary||''),
        _matrixDimension:clean(e.matrix_dimension||''),
        _matrixQuadrant:clean(e.quadrant_implied||e.matrix_quadrant||''),
        _matrixClaimed:clean(e.quadrant_claimed||''),
        _matrixSource:clean(e.matrix_classification_source||''),
        _matrixBasis:clean(e.matrix_evidence_basis||''),
        _provenance:clean(e.discovery_provenance||'')
      });
    }
    return out;
  }

  function weakCandidates(data){
    return (Array.isArray(data?.strand_c)?data.strand_c:[]).filter(x=>x&&typeof x==='object').map(x=>({
      ...x,
      _origin:'Weak signal',
      _matrixDimension:clean(x.matrix_dimension||''),
      _matrixQuadrant:clean(x.quadrant_implied||x.matrix_quadrant||''),
      _matrixClaimed:clean(x.quadrant_claimed||''),
      _matrixSource:clean(x.matrix_classification_source||''),
      _matrixBasis:clean(x.matrix_evidence_basis||''),
      _provenance:clean(x.discovery_provenance||'')
    }));
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
        {text:title,weight:4},{text:theme,weight:3},{text:note,weight:1.2},{text:anchor,weight:.8},{text:support,weight:x._origin==='Evidence signal'?1.15:.45}
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
    const parts=[{text:title,weight:3},{text:theme,weight:2},{text:note,weight:1},{text:why,weight:.55},{text:anchor,weight:.7},{text:support,weight:x._origin==='Evidence signal'?1.2:.55}];
    return {
      sustain:weightedHits(parts,INDEPENDENCE_TERMS),
      compete:weightedHits(parts,COMPETITIVENESS_TERMS),
      failure:weightedHits(parts,FAILURE_TERMS)
    };
  }

  function directionScores(x,evidence,row,questions){
    const title=candidateWhat(x),theme=signalTheme(x),note=clean(x.signal_note||x._evidencePoint||''),why=signalWhy(x),anchor=clean(x.anchor||'');
    const support=clean([evidence?.title,evidence?.summary].filter(Boolean).join(' '));
    const parts=[{text:title,weight:3},{text:theme,weight:1.8},{text:note,weight:1.2},{text:why,weight:.45},{text:anchor,weight:.55},{text:support,weight:x._origin==='Evidence signal'?1.25:.65}];
    let autonomyUp=weightedHits(parts,AUTONOMY_UP), autonomyDown=weightedHits(parts,AUTONOMY_DOWN);
    let performanceUp=weightedHits(parts,PERFORMANCE_UP), performanceDown=weightedHits(parts,PERFORMANCE_DOWN);
    const direct=norm(`${title} ${theme} ${note} ${x._origin==='Evidence signal'?support:''}`);

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
    if(x._origin==='Evidence signal'){
      // Read directional claims from the EU/Europe subject, not from a foreign actor that
      // happens to be described as competitive or leading in the same abstract.
      const et=norm(`${title} ${support}`);
      const euLoss=/(?:eu|europe|european).{0,120}(?:risk(?:s|ed|ing)?|lag(?:s|ging)?|fall(?:s|ing)? behind|los(?:e|es|ing)|ced(?:e|es|ing)|hollow|shortage|bottleneck|depend(?:s|ent|ence|ency)|reliance|vulnerab|gap)|(?:risk(?:s|ed|ing)?|lag(?:s|ging)?|fall(?:s|ing)? behind|los(?:e|es|ing)|ced(?:e|es|ing)|hollow|shortage|bottleneck|depend(?:s|ent|ence|ency)|reliance|vulnerab|gap).{0,120}(?:eu|europe|european)/.test(et);
      const euCeding=/europe.{0,140}(?:ceding|cede|risks repeating|repeating the mistakes|losing|falling behind)|(?:ceding|cede).{0,100}(?:european|europe)/.test(et);
      if(euLoss){performanceDown+=2.8;autonomyDown+=1.4}
      if(euCeding){performanceDown+=3.5;autonomyDown+=2.2}
      const foreignLead=/(?:china|chinese|united states|american|us).{0,100}(?:globally competitive|dominant|lead(?:s|ing|er)|outpac|frontier)|(?:globally competitive|dominant|lead(?:s|ing|er)|outpac|frontier).{0,100}(?:china|chinese|united states|american|us)/.test(et);
      if(foreignLead&&euLoss) performanceUp=Math.max(0,performanceUp-2.5);
    }

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
    const storedQuadrant=clean(x._matrixQuadrant||evidence?.quadrant_implied||evidence?.matrix_quadrant||'').toUpperCase();
    const reviewedMatrix=clean(x._matrixSource||evidence?.matrix_classification_source||'')==='reviewed_underlying_source';
    if((x._origin==='Evidence signal'||reviewedMatrix) && ['A','B','C','D'].includes(storedQuadrant)){
      autonomy=storedQuadrant==='A'||storedQuadrant==='B'?3:-3;
      performance=storedQuadrant==='A'||storedQuadrant==='C'?3:-3;
    }
    // V17.8: ambiguity is not an opening. The old fallback silently turned weak/neutral
    // evidence into +/+ and inflated the optimistic column. Keep a direction neutral unless
    // the record actually supports it; failure evidence may still resolve ambiguity downward.
    if(Math.abs(autonomy)<.55){
      if(performance>0.55 && /(foreign|non-eu|china|chinese|united states|american|partner|vendor|supplier|access)/.test(direct)) autonomy=-1;
      else if(performance<-.55 && questions.failure>=2) autonomy=-1;
      else autonomy=questions.failure>=2?-1:0;
    }
    if(Math.abs(performance)<.55){
      if(autonomy<0 && questions.failure>=2) performance=-1;
      else if(/(cost|lag|slow|cut|restrict|security|ban|fragment|shortage|gap|declin)/.test(direct)) performance=-1;
      else performance=0;
    }
    return {autonomy,performance,autonomyUp,autonomyDown,performanceUp,performanceDown};
  }

  function columnFor(direction){
    // A matrix cell needs evidence on both axes. Neutral/underspecified records remain in the
    // broader radar instead of being forced into a sovereignty-frontier quadrant.
    if(Math.abs(direction.autonomy)<.55||Math.abs(direction.performance)<.55) return null;
    if(direction.autonomy>0&&direction.performance>0) return COLUMNS[0];
    if(direction.autonomy>0&&direction.performance<0) return COLUMNS[1];
    if(direction.autonomy<0&&direction.performance>0) return COLUMNS[2];
    return COLUMNS[3];
  }

  function euLinkScore(x,evidence){
    const direct=norm(`${candidateWhat(x)} ${signalTheme(x)} ${clean(x.signal_note||'')} ${signalWhy(x)}`);
    const support=norm(`${clean(x.anchor||'')} ${clean(evidence?.title||'')} ${clean(evidence?.summary||'')} ${clean(evidence?.relevance_note||'')} ${clean(evidence?.bridge_sentence||'')} ${clean(evidence?.external_eu_bridge||'')}`);
    let s=0;
    if(EU_SCOPE_RE.test(direct)) s+=3;
    if(EU_SCOPE_RE.test(support)) s+=1.5;
    // Scanner-level EU relevance may come from abstract/body evidence that is not
    // repeated in the concise summary. Preserve that vetted scope downstream.
    if(clean(evidence?.eu_relevance||'').toLowerCase()==='direct') s=Math.max(s,3);
    else if(clean(evidence?.eu_relevance||'').toLowerCase()==='material_external' && clean(evidence?.external_eu_bridge||'')) s=Math.max(s,3);
    else if(clean(evidence?.eu_relevance||'').toLowerCase()==='derived') s=Math.max(s,1.5);
    return s;
  }

  function materialityScore(x,evidence,row){
    const direct=norm(`${candidateWhat(x)} ${signalTheme(x)} ${clean(x.signal_note||x._evidencePoint||'')}`);
    const support=norm(`${clean(x.anchor||'')} ${clean(evidence?.title||'')} ${clean(evidence?.summary||'')} ${clean(evidence?.relevance_note||'')} ${clean(evidence?.bridge_sentence||'')} ${clean(evidence?.external_eu_bridge||'')}`);
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
    const support=norm(`${clean(evidence?.title||'')} ${clean(evidence?.summary||'')} ${clean(evidence?.relevance_note||'')} ${clean(evidence?.bridge_sentence||'')} ${clean(evidence?.external_eu_bridge||'')}`);
    const t=`${d} ${support}`;
    const evidenceSignal=x._origin==='Evidence signal';
    const ext=/\b(china|chinese|united states|us|american|foreign|non-eu|third-country|third country|taiwan|japan|south korea|korea|uk|britain|canada)\b/;
    const eu=EU_SCOPE_RE;
    const euScoped=eu.test(t) || (evidenceSignal && ['direct','material_external'].includes(clean(evidence?.eu_relevance||'').toLowerCase()));

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
    const autonomyUp=/strategic autonomy|technological autonomy|technology autonomy|tech autonomy|technological sovereignty|digital sovereignty|sovereign|independence|reduce.{0,45}(?:depend|reliance)|reduc(?:ing|tion).{0,45}strategic depend|diversif|de-risk|derisk|self-suff|domestic capacity|european capacity|eu-led|european infrastructure|local production|onshor|reshor|secure supply|supply security|material security|resilien|alternative supplier|own (?:technology|capability|infrastructure)|control over|strengthen.{0,35}(?:eu|european).{0,35}(?:capacity|capabilit)|eu.{0,30}(?:fund|programme|program|instrument|strategy).{0,45}(?:build|strengthen|support|boost|develop|scale)/.test(t);
    const autonomyDown=/strategic depend|critical external depend|external depend|dependence on|dependent on|dependencies|reliance on|rely on|non-eu (?:technology|vendor|supplier|provider)|foreign (?:supplier|vendor|technology|platform|capital|market|infrastructure|expertise|talent)|external (?:supplier|vendor)|import dependence|imported technology|vendor lock|lock-in|loss of access|restricted access|on others(?:'|’) terms|ceding.{0,40}(?:value|profits|leverage|technology)|foreign-controlled/.test(t);
    const performanceUp=/competit|performance|frontier|leading|leader|advanced|scale|scaling|growth|productivity|innovation|investment|market access|access to|capacity|capabilit|excellence|quality|benefit|strengthen|expand|build|deploy|commerciali|sets? pace|industrial leadership|value creation|resilien/.test(t);
    const performanceDown=/less competitive|lag|behind|shortage|bottleneck|chokepoint|vulnerab|exposure|risk|costly|expensive|higher cost|delay|slow|fragment|subscale|declin|loss|losing|hollow|gap|cannot|unable|no substitute|disrupt|cut off|cutoff|blocked|constraint|barrier|threat|weakness|shortcoming|ceding|two-speed|two speed/.test(t);

    // V17.8.2 balanced opening gate. Column A is not a quota and it is not a reward for
    // optimistic language. It can be supported by either a realised gain OR a concrete,
    // committed implementation step (launched programme/call with resources, awarded funding,
    // approved project, signed partnership, adopted rule/standard, facility build/deployment).
    // Pure aspirations and recommendations still do not qualify.
    const openingDomain=/\b(?:research|science|scientific|researcher|scientist|talent|innovation|technology|technological|ai|compute|computing|cloud|semiconductor|chip|quantum|biotech|biotechnology|infrastructure|capacity|factory|gigafactor|manufacturing|production|industrial|standard|regulation|framework|procurement|market|commerciali|funding|programme|program|project|facility)\b/.test(d);
    const openingRealizedAction=/\b(?:operational|operates?|deployed|deploys?|deployment|opened|opens?|completed|completes?|secured|secures?|attracted|attracts?|retained|retains?|recruited|recruits?|expanded capacity|expands?\s+(?:european\s+|eu\s+)?(?:research\s+|compute\s+|production\s+|industrial\s+|manufacturing\s+)?capacity|increased capacity|increases?\s+(?:european\s+|eu\s+)?(?:research\s+|compute\s+|production\s+|industrial\s+|manufacturing\s+)?capacity|capacity increased|production increased|production increases?|market share (?:rose|increased|rises?)|overtook|outpaced|became a leader|is a leader|sets? the pace|adopted by|internationally adopted|global adoption|reduced dependence|reduces? dependence|reduced reliance|reduces? reliance|cut dependence|cuts? dependence|cut reliance|cuts? reliance|diversified suppliers|diversifies? suppliers|new european supplier|new eu supplier|built and operating|now produces|now provides)\b/.test(d)
      || /\b(?:researchers?|scientists?|research talent|scientific talent).{0,25}(?:returned|returns?|returning)\b|\b(?:returned|returning).{0,25}(?:researchers?|scientists?|research talent|scientific talent)\b/.test(d);
    const openingRealized=openingRealizedAction&&openingDomain;
    const openingCommitted=/\b(?:launch(?:es|ed|ing)?|co-fund(?:s|ed|ing)?|jointly fund(?:s|ed|ing)?|fund(?:s|ed|ing)?|award(?:s|ed|ing)?|approve(?:s|d|ing)?|select(?:s|ed|ing)?|establish(?:es|ed|ing)?|create(?:s|d|ing)?|sign(?:s|ed|ing)?|adopt(?:s|ed|ing)?|enact(?:s|ed|ing)?|enter(?:s|ed|ing)? into force|begin(?:s|ning)? construction|under construction|commence(?:s|d|ment)?|procure(?:s|d|ment)?|invest(?:s|ed|ing)?|commits?\s+(?:€|\$|£|[0-9])|backs?\s+(?:€|\$|£|[0-9]))\b/.test(d)
      && openingDomain;
    const openingAspirational=/\b(?:aims? to|plans? to|proposal|proposed|roadmap|strategy to|could|would|should|needs? to|must|potential to|prospects? for|recommend(?:s|ed|ation)|intends? to|seeks? to|calls? for)\b/.test(d);
    const dependenceReduction=/\b(?:reduc(?:e|es|ed|ing)|cut(?:s|ting)?|lower(?:s|ed|ing)?).{0,35}(?:dependence|dependency|reliance)\b/.test(d);
    const directAutonomyDown=/strategic depend|critical external depend|external depend|dependence on|dependent on|dependencies|reliance on|rely on|non-eu (?:technology|vendor|supplier|provider)|foreign (?:supplier|vendor|technology|platform|capital|market|infrastructure|expertise|talent)|external (?:supplier|vendor)|import dependence|imported technology|vendor lock|lock-in|loss of access|restricted access|on others(?:'|’) terms|foreign-controlled/.test(d);
    const directPerformanceDown=/less competitive|\btrails?\b|\blag(?:s|ging)?\b|behind|shortage|bottleneck|chokepoint|vulnerab|exposure|risk|costly|expensive|higher cost|delay|slow|fragment|subscale|declin|loss|losing|hollow|\bgap\b|cannot|unable|no substitute|disrupt|cut off|cutoff|blocked|constraint|barrier|threat|weakness|shortcoming|ceding|two-speed|two speed/.test(d);
    const externalPartnership=ext.test(d)&&/\b(?:partner|partnership|supplier|vendor|foreign capital|joint venture|licen[cs]e from|technology from)\b/.test(d);
    const euCapabilityBuild=eu.test(d)
      && /\b(?:launch|co-fund|fund|award|approve|select|establish|create|build|expand|deploy|open|procure|invest|adopt|enact)\w*\b/.test(d)
      && /\b(?:research|science|innovation|technology|ai|compute|computing|cloud|semiconductor|chip|quantum|biotech|infrastructure|capacity|factory|gigafactor|manufacturing|production|industrial|standard|regulation|framework|procurement|facility)\b/.test(d);
    const openingDependenceHarm=(directAutonomyDown||externalPartnership)&&!dependenceReduction;
    const cleanOpening=(openingRealized||openingCommitted)&&!openingAspirational&&!openingDependenceHarm&&!directPerformanceDown;


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
      if(column.id==='A') return cleanOpening && performanceUp && (autonomyUp || euCapabilityBuild || /brain gain|talent inflow|attract|retain|recruit|return/.test(d)) && euScoped;
      if(column.id==='B') return performanceDown && /research security|screening|visa|restrict|barrier|exclude|suspend|closed lab|collabor|mobility|openness/.test(t) && (autonomyUp||/security|sovereign|protect/.test(t));
      return performanceUp && (autonomyDown || (ext.test(t)&&/collabor|cooperat|mobility|recruit|expertise|foreign talent|international talent|science diplomacy|knowledge flow|access/.test(t)));
    }

    if(row.id==='infrastructure'){
      if(column.id==='A') return cleanOpening && (autonomyUp||euCapabilityBuild) && performanceUp;
      if(column.id==='B') return autonomyUp && performanceDown;
      if(column.id==='C') return (autonomyDown || (ext.test(t)&&/supplier|vendor|technology|compute|cloud|material|input|supply chain|reactor|semiconductor|chip|infrastructure/.test(t))) && performanceUp;
      return (autonomyDown||/access|supply|dependency/.test(t)) && performanceDown;
    }

    if(row.id==='conversion'){
      if(column.id==='A') return cleanOpening && (autonomyUp||euCapabilityBuild) && performanceUp;
      if(column.id==='B') return (autonomyUp||/protect|locali|onshor|domestic|de-risk|derisk/.test(t)) && performanceDown;
      if(column.id==='C') return (autonomyDown||ext.test(t)) && performanceUp && /foreign capital|foreign market|market access|foreign platform|scale abroad|investment|supplier|partner|global market|china exposure/.test(t);
      return performanceDown && /firm exit|firms exit|exit europe|move abroad|moving abroad|relocat|foreign acquisition|closure|shut down|hollow|lost production|loss of production|production capacity|funding gap|scale-up gap|scaleup gap|fail.{0,20}scale|firms? fall behind|industrial decline|ceding profits|ceding value|displaced competition|two-speed|two speed/.test(t);
    }

    // Rules/institutions are broader than a single named regulation: EU-created
    // frameworks can be openings; foreign regimes can create productive dependence;
    // fragmentation/delay can create double loss.
    if(column.id==='A') return cleanOpening && (autonomyUp||euCapabilityBuild) && performanceUp && /adopted by|internationally adopted|global adoption|reduced depend|reduced reliance|faster decision|shorter approval|mutual recognition|market access|launch|fund|award|approve|adopt|enact|procurement/.test(d);
    if(column.id==='B') return performanceDown && (autonomyUp||/research security|screening|de-risk|derisk|sovereign|protect/.test(t)) && /restrict|export control|regulat|ban|sanction|screening|security|licen|compliance|burden/.test(t);
    if(column.id==='C') return performanceUp && (autonomyDown||/foreign standards|foreign rules|us rules|american rules|platform rules|export licen[cs]e|non-eu rules|non-eu standards|us export-control|us export control/.test(t));
    return performanceDown && /gridlock|cannot decide|unable to decide|decision delay|blocked by|institutional constraint|fragmented governance|foreign rules|foreign standards|export controls|sanctions|exclusion|regulatory fragmentation|regulatory delay|delayed/.test(t);
  }

  function whyQualifies(flags,column,row){
    const parts=[];
    if(flags.sustain) parts.push('changes how much control Europe has');
    if(flags.compete) parts.push('changes how well Europe can compete');
    if(flags.failure) parts.push('shows a concrete way access or capability can fail');
    const s=parts.length?parts.join('; '):'changes Europe’s control and competitive position';
    return `${s}. Matrix cell: ${row.name} / ${column.name}.`;
  }

  function classifySignal(x,data,index,now=new Date()){
    if(!x||typeof x!=='object') return null;
    const evidence=evidenceFor(x,index);
    const reviewedMatrix=clean(x._matrixSource||evidence?.matrix_classification_source||'')==='reviewed_underlying_source';
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
    const supportNorm=norm(`${clean(evidence?.title||'')} ${clean(evidence?.summary||'')} ${clean(evidence?.relevance_note||'')} ${clean(evidence?.bridge_sentence||'')} ${clean(evidence?.external_eu_bridge||'')}`);
    const evidenceScope=clean(evidence?.eu_relevance||'').toLowerCase();
    const evidenceScopedEU=x._origin==='Evidence signal' && euLink>=3 && (
      evidenceScope==='direct' ||
      (evidenceScope==='material_external' && !!clean(evidence?.external_eu_bridge||'')) ||
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

    // Core reports/papers populate the structural 4×4 matrix even when they describe a
    // condition rather than a discrete event. Weak signals remain event/movement-gated.
    // This mirrors the radar design: pass 1 establishes the phenomenon/quadrant; pass 2
    // supplies external developments that may move it.
    if(x._origin==='Evidence signal'){
      if(euLink<1.4 || (!directEU&&!strategicIndirect&&!evidenceScopedEU)) return null;
    }else if(reviewedMatrix){
      // Reviewed weak-signal evidence has already been substantively adjudicated. Keep
      // the EU scope and movement checks, but do not require the generic question-keyword
      // prefilter to rediscover the same mechanism.
      if(euLink<1.4 || (!directEU&&!strategicIndirect&&!evidenceScopedEU) || !dynamic) return null;
    }else{
      if((qCount===0&&!knowledgeStructuralEvidence) || !movementSupported || euLink<1.4 || (!directEU&&!strategicIndirect&&!evidenceScopedEU) || !dynamic) return null;
    }

    // Try rows in evidence-score order and keep the first row/column whose observed
    // statement actually satisfies that cell's semantic contract.  This prevents
    // a stray acronym or generic word such as "research" from filling a sparse cell.
    const tieOrder=['knowledge','infrastructure','conversion','rules'];
    const storedRow={d1:'knowledge',d2:'infrastructure',d3:'conversion',d4:'rules',knowledge:'knowledge',infrastructure:'infrastructure',conversion:'conversion',rules:'rules'}[clean(x._matrixDimension||evidence?.matrix_dimension||'').toLowerCase()]||'';
    const rowOptions=tieOrder.map(id=>({id,score:(rows[id]||0)+(id===storedRow?20:0)})).sort((a,b)=>b.score-a.score||tieOrder.indexOf(a.id)-tieOrder.indexOf(b.id));
    let row=null,rowPick=null,materiality=0,direction=null,column=null;
    for(const opt of rowOptions){
      // A reviewed source-evidence row is an adjudicated matrix result, not a keyword
      // hint. Curator cells never populate _matrixDimension, so this cannot force a
      // row merely because the manual list proposed one.
      if(reviewedMatrix&&storedRow&&opt.id!==storedRow) continue;
      const r=ROWS.find(v=>v.id===opt.id);
      const rowEvidenceText=clean(`${candidateWhat(x)} ${clean(evidence?.title||'')} ${clean(evidence?.summary||'')} ${clean(x._evidenceSummary||'')}`);
      // Generic AI or technology language is not infrastructure by itself. A non-reviewed
      // source needs a concrete compute/chip/data/material/facility/supply mechanism.
      if(r.id==='infrastructure' && !reviewedMatrix && storedRow!=='infrastructure' && !INFRA_CONCRETE_RE.test(rowEvidenceText)) continue;
      // Governance-heavy AI papers should not fall into infrastructure merely because
      // they mention AI systems; the rules row gets the first defensible chance.
      if(r.id==='infrastructure' && !reviewedMatrix && RULES_CONCRETE_RE.test(rowEvidenceText) && !INFRA_CONCRETE_RE.test(rowEvidenceText)) continue;
      let m=materialityScore(x,evidence,r);
      if(reviewedMatrix&&storedRow===r.id&&clean(x._matrixBasis||evidence?.matrix_evidence_basis||'')) m=Math.max(m,3);
      if(m<2.4) continue;
      const dir=directionScores(x,evidence,r,questions);
      const col=columnFor(dir);
      if(!col) continue;
      // For vetted pass-1 evidence, row materiality + two-axis direction is the matrix
      // rubric. Do not re-gate the result with a second literal phrase contract. That
      // contract is retained for external weak signals, where the event statement itself
      // must carry the mechanism.
      if(!reviewedMatrix && !cellEvidencePass(x,evidence,r,col)) continue;
      // Brain-drain evidence is subject-sensitive: a Europe-related paper discussing
      // talent loss in China must not become European brain drain.
      if(x._origin==='Evidence signal' && !reviewedMatrix && r.id==='knowledge' && col.id==='D' && !cellEvidencePass(x,evidence,r,col)) continue;
      row=r; rowPick=opt; materiality=m; direction=dir; column=col; break;
    }
    if(!row||!column) return null;

    const reach=reachScore(rows),irreversibility=irreversibilityScore(x,row,column),attention=attentionGapScore(x),actionability=actionabilityScore(x,row,evidence);
    const triage=reach+irreversibility+attention+actionability;
    const multi=qCount>=2?1.5:0;
    const crossDirection=(flags.sustain&&flags.compete&&Math.sign(direction.autonomy)!==Math.sign(direction.performance))?1:0;
    const columnWeight=1; // balanced matrix: no quadrant gets an automatic ranking bonus
    const recency=recencyScore(x,now)+(x.new_this_scan?1:0);
    const overall=triage+multi+crossDirection+columnWeight+recency;
    const cell=CELL_NAMES[row.id][column.id];
    return {
      id:norm(linkFor(x)||candidateWhat(x)),
      title:candidateWhat(x),
      coreMessage:clean(x._origin==='Evidence signal' ? (x.core_message||evidence?.core_message||x._evidencePoint||candidateWhat(x)) : candidateWhat(x)),
      bibliographicTitle:clean(x._origin==='Evidence signal' ? (evidence?.title||x.title||candidateWhat(x)) : (x.headline||x.title||candidateWhat(x))),
      authors:clean(x._origin==='Evidence signal' ? (evidence?.authors||'') : (x.authors||'')),
      itemType:clean(x._origin==='Evidence signal' ? (evidence?.type||x.type||'') : (x.type||x.signal_kind||x.signal_type||'')),
      source:sourceFor(x),
      date:dateFor(x),
      link:linkFor(x),
      origin:x._origin||'Weak signal',
      newThisScan:!!x.new_this_scan,
      theme:signalTheme(x),
      anchor:clean(x.anchor||''),
      evidenceTitle:clean(evidence?.title||''),
      abstract:clean(evidence?.summary||x._evidenceSummary||x.summary||''),
      matrixEvidenceBasis:clean(evidence?.matrix_evidence_basis||x.matrix_evidence_basis||''),
      row,rowScore:rowPick.score,column,cellName:cell[0],cellSubtitle:cell[1],
      questions,questionFlags:flags,questionCount:qCount,
      direction,triage:{reach,irreversibility,attentionGap:attention,actionability,total:triage},
      actor:actorFor(row),
      why:whyQualifies(flags,column,row),
      originalWhy:signalWhy(x),
      materiality,euLink,overall,
      strongCandidate:qCount>=2,
      confidence:clamp(Math.round((Math.min(6,materiality)/6*.35 + Math.min(6,euLink)/6*.2 + Math.min(3,qCount)/3*.25 + Math.min(8,Math.abs(direction.autonomy)+Math.abs(direction.performance))/8*.2)*100),35,96),
      discoveryProvenance:clean(x._provenance||evidence?.discovery_provenance||''),
      quadrantClaimed:clean(x._matrixClaimed||evidence?.quadrant_claimed||''),
      quadrantImplied:clean(x._matrixQuadrant||evidence?.quadrant_implied||column.id||'')
    };
  }

  function shortBullet(x){
    // Keep Quick Matrix bullets tied to the individual publication. The column
    // heading already states the control/competitiveness direction, so repeating
    // that template in every bullet hides what each source actually says.
    const rawTitle=clean(x?.bibliographicTitle||x?.title||x?.coreMessage||'');
    const rawCore=clean(x?.coreMessage||'');
    const n=norm(`${rawTitle} ${rawCore}`);
    const fixed=[
      [/erc advanced grants|€840 million/, 'ERC adds €840m for leading researchers.'],
      [/allea general assembly 2026/, 'ALLEA links open science to research security.'],
      [/science superpower.*rival the us and china/, 'Europe could attract US research talent.'],
      [/arrested at nato.*espionage|suspicion of espionage/, 'NATO espionage case exposes research-security risk.'],
      [/science knows no borders/, 'ALLEA warns against research-collaboration curbs.'],
      [/scandinavian approaches to research security/, 'Scandinavian research-security models differ on openness.'],
      [/fragmented europe.*china as a technology/, 'Europe remains fragmented on China tech policy.'],
      [/research security by roundtable/, 'Germany uses ethics committees for research security.'],
      [/fifth freedom in europe/, 'Researchers flag barriers to EU mobility.'],
      [/chinese use of foreign interference tactics/, 'Chinese interference targets Dutch knowledge flows.'],
      [/revamping europe.?s chips strategy/, 'EU chips strategy should target indispensability.'],
      [/made in china powered by europe/, 'EU technology gives Europe leverage over China.'],
      [/close the artificial intelligence compute gap/, 'Europe still depends on US frontier compute.'],
      [/sovereign by necessity.*frontier ai export controls/, 'AI export controls can deepen Europe’s compute dependence.'],
      [/evolving radio astronomy.*africa/, 'African radio astronomy reshapes EU infrastructure access.'],
      [/new growth model.*strategic capitalism/, 'EU growth remains exposed to external tech dependence.'],
      [/ungoverned space.*military ai/, 'Europe cannot buy military-AI autonomy from outside.'],
      [/strengthening u\.s\. global leadership.*electric vehicle/, 'US EV strategy intensifies competition with Europe.'],
      [/european autonomy in orbit/, 'Europe still relies on outside space capability.'],
      [/europe tackles tech sovereignty/, 'EU tech-sovereignty policy targets critical dependence.'],
      [/china places 14 eu entities/, 'China cuts dual-use access for 14 EU entities.'],
      [/geopolitical risk mitigation in information governance/, 'AI supply-chain governance exposes EU dependency risks.'],
      [/battery cell production machinery/, 'Europe lacks battery-production machinery sovereignty.'],
      [/beyond the european chips act/, 'EU chips remain dependent on China, Taiwan and the US.'],
      [/technological dependencies of the european union/, 'EU tech dependence has risen, especially in digital tech.'],
      [/semiconductor geopolitical risk survey/, 'EU chip supply remains exposed to geopolitical shocks.'],
      [/beijing.?s critical raw material weapon/, 'China can weaponise raw-material access against Europe.'],
      [/venture capital gap/, 'Europe’s VC gap increases outside-investor reliance.'],
      [/helsing and quantum systems raise/, 'European defence-tech firms raise $3bn to scale.'],
      [/80 billion investment alliance/, 'Europe launches €80bn tech scale-up alliance.'],
      [/geo-industrial deal/, 'EU geo-industrial policy links scale with resilience.'],
      [/driving defence.*automotive/, 'Europe can reuse automotive capacity for defence scale.'],
      [/agile and rapid defence innovation/, 'EU agrees an agile defence-innovation programme.'],
      [/european innovation council opens to defence/, 'EIC opens funding to defence and dual-use tech.'],
      [/reconfigurability.*digitisation/, 'EU manufacturing resilience depends on reconfigurable digital systems.'],
      [/strategic procurement in global europe/, 'EU procurement preferences can raise deployment costs.'],
      [/dual-use by design research/, 'Dual-use research creates new export-control risks.'],
      [/industrial accelerator act and how to fix/, 'Industrial Accelerator Act may raise EU costs.'],
      [/dual-use and defence research in europe/, 'EU defence R&D can build capability but add controls.'],
      [/structural limitations.*eu.?s ai model/, 'EU AI competitiveness is constrained by capital and compute gaps.'],
      [/selective conditionality.*foreign investment/, 'EU ties foreign investment to strategic conditions.'],
      [/investor landscape for venture capital/, 'EU scale-ups lack deep institutional capital.'],
      [/investment screening and technology transfers/, 'EU investment screening limits sensitive tech transfer.'],
      [/circular economy.*industrial sovereignty/, 'Circular economy can reduce EU industrial dependencies.'],
      [/china.?s dual circulation strategy/, 'China’s dual circulation pressures EU EV industry.'],
      [/portugal.?s productivity gap/, 'Europe’s productivity gap tracks weak R&D and equity.'],
      [/reshaping europe.?s industrial future/, 'CEE industry faces new geopolitical scale pressures.'],
      [/das auto and the second china shock/, 'China’s EV shift exposed weak EU industrial coordination.'],
      [/council recommendation.*science diplomacy/, 'EU Council sets a framework for science diplomacy.'],
      [/tech sovereignty package.*discussion summary/, 'EU sovereignty rules trade autonomy for extra friction.'],
      [/integrating cbdcs.*global financial architecture/, 'CBDCs shift state control over monetary infrastructure.'],
      [/tech sovereignty.*mimic its rivals/, 'Tech sovereignty can raise costs if Europe copies rivals.'],
      [/national knowledge security guidelines 2026/, 'Dutch 2026 guidance tightens research safeguards.'],
      [/digital instruments of monetary.*cybersecurity/, 'E-hryvnia design stresses transparency and cyber resilience.'],
      [/from openness to deterrence/, 'EU economic-security policy is moving from openness to deterrence.'],
      [/^european tech sovereignty\b/, 'EU tech-sovereignty policy combines protection and capacity-building.'],
      [/mitigate deter escalate/, 'US coercion exposes Europe’s dependence on digital firms.'],
      [/does europe really have a plan for tech sovereignty/, 'EU tech sovereignty still relies on US platforms.'],
      [/intellectual property governance.*artificial intelligence/, 'AI rule fragmentation weakens EU control over digital power.'],
      [/chips act 2\.0/, 'Chips Act 2.0 tests Europe’s second semiconductor push.'],
      [/industrial accelerator act count/, 'Industrial Accelerator Act risks weak implementation.']
    ];
    for(const [re,label] of fixed){if(re.test(n))return label}

    const abbreviate=v=>clean(v)
      .replace(/^Executive Summary:\s*/i,'')
      .replace(/^Event Report:\s*/i,'')
      .replace(/\bthe European Union\b/gi,'the EU')
      .replace(/\bEuropean Union\b/gi,'EU')
      .replace(/\bUnited States\b/gi,'US')
      .replace(/\bartificial intelligence\b/gi,'AI')
      .replace(/\bresearch and innovation\b/gi,'R&I')
      .replace(/\btechnological\b/gi,'tech')
      .replace(/\s+/g,' ')
      .trim();
    const finish=v=>{
      let q=abbreviate(v).replace(/[;:,]+$/,'').trim();
      if(!q)return '';
      if(!/[.!?]$/.test(q))q+='.';
      return q;
    };
    let title=abbreviate(rawTitle);
    if(title.length<=72)return finish(title);
    const parts=title.split(/\s+[–—]\s+|:\s+/).map(clean).filter(Boolean);
    if(parts.length>1){
      const first=parts[0],pair=`${parts[0]}: ${parts[1]}`;
      if(pair.length<=72)return finish(pair);
      if(first.length>=24&&first.length<=72)return finish(first);
    }
    const core=RadarInsights&&RadarInsights.readerPoint?RadarInsights.readerPoint(rawCore,72):'';
    if(core)return core;
    const comma=title.split(/,\s+/)[0];
    if(comma.length>=24&&comma.length<=72)return finish(comma);
    const words=title.split(/\s+/);let out='';
    for(const w of words){const next=out?`${out} ${w}`:w;if(next.length>68)break;out=next}
    out=out.replace(/\b(?:and|or|of|for|to|in|on|with|through|the|a|an)$/i,'').trim();
    return finish(out||title.slice(0,68));
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

  return {ROWS,COLUMNS,CELL_NAMES,buildEvidenceIndex,classifySignal,buildFrontier,weakCandidates,evidenceCandidates,questionScores,rowScores,shortBullet};
});
