(function(root,factory){
  const merit=(typeof module==='object'&&module.exports)?require('../source_merit.js'):root.RadarSourceMerit;
  const api=factory(root.RadarInsights,merit);
  if(typeof module==='object'&&module.exports) module.exports=api;
  root.SovereigntyFrontier=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(RadarInsights,SourceMerit){
  'use strict';

  const ROWS=[
    {id:'knowledge',name:'People & knowledge',short:'People & knowledge',description:'Researchers, skills, partnerships and know-how moving into, within or out of Europe.'},
    {id:'infrastructure',name:'Tools & facilities',short:'Tools & facilities',description:'Computing, data, chips, materials, energy and research facilities.'},
    {id:'conversion',name:'Firms & growth',short:'Firms & growth',description:'Turning research into companies, products, production and market scale.'},
    {id:'rules',name:'Rules & decisions',short:'Rules & decisions',description:'Standards, security checks, funding rules and how quickly Europe can act.'}
  ];
  const COLUMNS=[
    {id:'A',name:'More control, stronger',direction:'Europe gains control · capability improves',tone:'opportunity'},
    {id:'B',name:'More control, some cost',direction:'Europe gains control · capability pays a price',tone:'tradeoff'},
    {id:'C',name:'Stronger, but reliant',direction:'capability improves · Europe still relies on others',tone:'exposure'},
    {id:'D',name:'Less control, weaker',direction:'Europe loses control · capability also weakens',tone:'alarm'}
  ];
  const CELL_NAMES={
    knowledge:{A:['Build and keep talent','Europe strengthens its own research workforce, skills and knowledge base'],B:['Protection slows exchange','European safeguards protect knowledge but make some collaboration or mobility harder'],C:['Strength from outside','international researchers, expertise or research networks strengthen European work while the input still comes from outside'],D:['People or know-how are lost','Europe loses researchers, knowledge, network access or protected know-how']},
    infrastructure:{A:['More secure European capacity','Europe builds, shares or diversifies access to important research tools and inputs'],B:['More control, higher cost','Europe gains more control over tools or infrastructure, but pays in cost, delay or performance'],C:['Useful outside access','outside tools, facilities or inputs strengthen European work while access still depends on others'],D:['Outside limits hurt capability','shortages, restrictions or chokepoints outside Europe reduce research or technology capability']},
    conversion:{A:['European firms grow at home','European research becomes firms, production, market position or industrial capacity in Europe'],B:['More control, less scale','localisation or security keeps more control in Europe but raises cost, delay or fragmentation'],C:['Growth using outside capital or markets','European firms grow through foreign capital, markets, platforms or production while reliance remains'],D:['Value and scale move abroad','research, firms, IP, production or value creation move out of Europe or fail to scale here']},
    rules:{A:['Europe aligns rules and action','common European rules, standards, funding or coordination improve control and performance'],B:['Protection adds friction','European safeguards protect control but slow research, innovation or collaboration'],C:['Access on outside rules','European performance benefits from access that is governed by foreign rules, licences, standards or platforms'],D:['Rules split or block Europe','foreign restrictions or European fragmentation and delay weaken control and performance']}
  };

  const ROW_TERMS={
    knowledge:['research','science','scientific','university','universities','academic','academia','researcher','researchers','scientist','scientists','talent','skills','training','doctoral','phd','publication','research collaboration','scientific collaboration','research cooperation','scientific cooperation','horizon europe','framework programme','erc','knowledge','visa','mobility','brain drain','brain gain','open science','research security'],
    infrastructure:['compute','computing','gpu','gpus','supercomputer','artificial intelligence','ai model','ai models','ai video model','ai system','ai systems','foundation model','foundation models','data center','data centre','cloud','semiconductor','chip','chips','microelectronics','quantum','reactor','nuclear','grid','electricity','energy','battery','batteries','lithium','critical mineral','critical minerals','critical raw material','critical raw materials','rare earth','materials','advanced material','advanced materials','instrument','instruments','facility','facilities','infrastructure','research data','scientific data','database','data repository','biobank','telecom','5g','6g','satellite','cable','supply chain','supply chains','strategic resource','strategic resources','critical technology','critical technologies','technology value chain','technology value chains','input','inputs'],
    conversion:['firm','firms','company','robot','robots','robotics','companies','startup','start-up','scale-up','manufacturer','manufacturing','industrial','industry','product','products','commercial','commercialisation','commercialization','market','capital','venture','investment','investor','procurement','patent','patents','defence','defense','military','dual-use','dual use','capability','capabilities','production','factory','factories'],
    rules:['export control','export controls','export-control','export-controls','sanction','sanctions','regulation','regulatory','standard','standards','rule','rules','governance','institution','institutions','funding programme','funding program','programme','program','screening','research security','research-security','knowledge security','knowledge-security','restriction','restrictions','ban','bans','law','laws','framework','decision','approval','approvals','permit','permits','licence','licences','license','licenses','licensing','mutual recognition','coordination','harmonisation','harmonization','subsidy','subsidies','state aid']
  };

  const INFRA_CONCRETE_RE=/\b(compute|computing|supercomputer|data cent(?:er|re)|cloud|semiconductor|chip|microelectronics|quantum|reactor|nuclear|grid|electricity|energy|battery|lithium|critical mineral|critical raw material|rare earth|materials|facility|infrastructure|telecom|5g|6g|satellite|cable|supply chain|strategic resource|research infrastructure|research data|scientific data|research database|scientific database|data repository|biobank|ai factory|gigafactory)\b/i;
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

  function canonicalPublicationTitle(v){
    let t=clean(v).replace(/^(?:executive summary|event report|policy brief|research brief|briefing|report)\s*:\s*/i,'');
    t=t.replace(/\s+[–—-]\s+(?:company announcement\s+-\s+)?(?:ft\.com|reuters|bloomberg|euractiv\.com)$/i,'');
    return norm(t);
  }

  function candidateQuality(x){
    const basis=clean(x?._matrixBasis||x?.matrix_evidence_basis||'');
    const summary=clean(x?._evidenceSummary||x?.summary||x?.signal_note||'');
    const core=clean(x?.core_message||x?._evidencePoint||'');
    return (basis?500:0)+Math.min(250,summary.length)+Math.min(120,core.length)+(clean(x?.link)?25:0);
  }

  function dedupeCandidates(items){
    // Collapse alternate landing-page/PDF versions and repeated DOI versions before
    // classification.  The best-evidenced record wins, so duplicate publications do
    // not occupy multiple Matrix slots or reappear in priorities.
    const groups=[],byKey=new Map();
    for(const x of items){
      const linkKey=norm(linkFor(x));
      const titleKey=canonicalPublicationTitle(x?.title||x?.headline||candidateWhat(x));
      const keys=[];
      if(linkKey) keys.push(`u:${linkKey}`);
      if(titleKey && titleKey.length>=28) keys.push(`t:${titleKey}`);
      let idx=-1;
      for(const k of keys){if(byKey.has(k)){idx=byKey.get(k);break}}
      if(idx<0){idx=groups.length;groups.push(x)}
      else if(candidateQuality(x)>candidateQuality(groups[idx])) groups[idx]=x;
      for(const k of keys) byKey.set(k,idx);
    }
    return groups.filter(Boolean);
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
    const all=norm(`${title} ${theme} ${note} ${anchor} ${support}`);
    // Semantic row disambiguation: identify the mechanism being affected, not just the
    // policy instrument named in the same sentence.
    if(/\b(gpu|gpus|compute|cloud|chip|semiconductor|research infrastructure|research facility|research data|scientific data|database|data repository|biobank|critical raw material|critical mineral|advanced material)\b/.test(all) && /access|supplier|vendor|shortage|capacity|infrastructure|supply|repository|dataset|export[- ]control|licen[cs]e/.test(all)) scores.infrastructure+=4.5;
    if(/\b(startup|start-up|scale-up|scaleup|venture capital|growth capital|manufactur|commerciali|production|value capture|r&d moved|relocat)\b/.test(all)) scores.conversion+=4.5;
    if(/\b(export[- ]controls?|regulation|standard|mutual[- ]recognition|licen[cs]ing|licen[cs]e|approval rules?|regulatory fragmentation|joint funding|coordinated procurement)\b/.test(all)) scores.rules+=4.5;
    if(/\b(researcher mobility|research collaboration|scientific collaboration|international collaboration|research workforce|brain drain|talent outflow|visiting researchers?|international researchers?)\b/.test(all)) scores.knowledge+=4.5;
    // When a rule acts mainly by cutting access to a concrete technical input, classify
    // the observed consequence as infrastructure rather than the legal instrument itself.
    if(/export[- ]controls?|licen[cs]e denied|sanction/.test(all) && /\b(gpu|compute|chip|semiconductor|cloud|critical raw material|critical mineral|research facility)\b/.test(all) && /access|supply|shortage|cut|blocked|denied/.test(all)) scores.infrastructure+=5;
    // Conversely, licensing/standard/compliance burdens are rules when the rule itself is
    // the mechanism, even if firms or markets are mentioned.
    if(/\b(rule|rules|regulation|standard|export[- ]licen[cs]es?|licen[cs]ing|compliance|mutual[- ]recognition|approval rules?)\b/.test(all) && /burden|comply|access|fragment|delay|market/.test(all)) scores.rules+=3;
    if(/export[- ]controls?.{0,30}rules?|licen[cs]ing burden|compliance burden/.test(all)) scores.rules+=8;
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
    if(row.id==='rules'){
      const euRuleSelf=/(?:eu|europe|european|member states).{0,90}(?:export control|sanction|restriction|ban|research security|knowledge security|screening)|(?:eu|european).{0,40}(?:rule|regulation|screening|security)/.test(direct);
      const foreignRulePressure=/(?:united states|american|china|chinese|foreign|non-eu).{0,90}(?:export control|sanction|restriction|ban|rule|standard|licen[cs]e)/.test(direct);
      if(euRuleSelf && autonomyUp<1) autonomyUp+=1.1;
      if(foreignRulePressure) autonomyDown+=1.6;
    }
    // Knowledge-B is explicitly the research-security/openness trade-off: safeguards can
    // increase control over sensitive research while imposing collaboration/mobility costs.
    // Without this directional rule, generic failure words (restrict/delay/risk) push the
    // same evidence into D before the semantic B-cell test gets a chance to evaluate it.
    if(row.id==='knowledge' && /research[- ]security|knowledge[- ]security|security screening|research screening/.test(direct)){
      if(/protect|safeguard|sensitive|security|screening|interference|espionage|restrict/.test(direct)) autonomyUp+=2.2;
      if(/restrict|barrier|delay|slow|exclude|suspend|cut|collabor|mobility|openness/.test(direct)) performanceDown+=2.2;
    }
    if(row.id==='knowledge' && /brain drain|researcher outflow|talent outflow|talent loss|researchers? (?:leave|leaving|left)|scientists? (?:leave|leaving|left)|unable to retain|failure to retain|retention crisis/.test(direct)){autonomyDown+=4;performanceDown+=4}
    if(row.id==='knowledge' && /brain gain|talent inflow|attract(?:ing|ion)?.{0,30}(?:researcher|scientist|talent)|retain(?:ing|ed)?.{0,30}(?:researcher|scientist|talent)|(?:researcher|scientist).{0,25}return/.test(direct)){autonomyUp+=3;performanceUp+=3}
    if(x._origin==='Evidence signal'){
      // Read directional claims from the EU/Europe subject, not from a foreign actor that
      // happens to be described as competitive or leading in the same abstract.
      const et=norm(`${title} ${support}`);
      const euLoss=/(?:eu|europe|european).{0,120}(?:lag(?:s|ging)?|fall(?:s|ing)? behind|los(?:e|es|ing)|ced(?:e|es|ing)|hollow|shortage|bottleneck|vulnerab.{0,40}(?:harm|constraint|loss)|capability gap|capacity gap|performance gap)|(?:lag(?:s|ging)?|fall(?:s|ing)? behind|los(?:e|es|ing)|ced(?:e|es|ing)|hollow|shortage|bottleneck|capability gap|capacity gap|performance gap).{0,120}(?:eu|europe|european)/.test(et);
      const euDependence=/(?:eu|europe|european).{0,120}(?:depend(?:s|ent|ence|ency)|reliance|rely on)|(?:depend(?:s|ent|ence|ency)|reliance|rely on).{0,120}(?:eu|europe|european)/.test(et);
      const euCeding=/europe.{0,140}(?:ceding|cede|risks repeating|repeating the mistakes|losing|falling behind)|(?:ceding|cede).{0,100}(?:european|europe)/.test(et);
      if(euLoss){performanceDown+=2.8;autonomyDown+=1.4}
      if(euDependence) autonomyDown+=1.8;
      if(euCeding){performanceDown+=3.5;autonomyDown+=2.2}
      const foreignLead=/(?:china|chinese|united states|american|us).{0,100}(?:globally competitive|dominant|lead(?:s|ing|er)|outpac|frontier)|(?:globally competitive|dominant|lead(?:s|ing|er)|outpac|frontier).{0,100}(?:china|chinese|united states|american|us)/.test(et);
      if(foreignLead&&euLoss) performanceUp=Math.max(0,performanceUp-2.5);
    }

    if(row.id==='knowledge'){
      const kt=norm(`${direct} ${support}`);
      const externalKnowledge=/(?:foreign|non-eu|third-country|third country|international|china|chinese|united states|american).{0,70}(?:researcher|scientist|research talent|scientific talent|expertise|research collaboration|scientific collaboration|research cooperation|doctoral candidate|phd student|stem student|international graduate|visiting researcher)|(?:researcher|scientist|research talent|scientific talent|expertise|research collaboration|scientific collaboration|research cooperation|doctoral candidate|phd student|stem student|international graduate|visiting researcher).{0,70}(?:foreign|non-eu|third-country|third country|international|china|chinese|united states|american)/.test(kt);
      const externalTalentPipeline=/(?:international|foreign|non-eu|third-country|third country|extra-eu).{0,65}(?:students?|graduates?|doctoral candidates?|phd students?|researchers?|scientists?|visiting researchers?|research visitors?)|(?:students?|graduates?|doctoral candidates?|phd students?|researchers?|scientists?|visiting researchers?|research visitors?).{0,65}(?:international|foreign|non-eu|third-country|third country|extra-eu)/.test(kt)
        && /retain|retention|stay|post-study|post study|post-research|post research|job search|employment|career|research|innovation|stem|skills|workforce|competitiveness|capacity|capability/.test(kt);
      const knowledgeGain=/benefit|strengthen|boost|improve|excellence|leading|competitive|competitiveness|capacity|capability|access to|fill(?:s|ing)? gap|critical expertise|innovation ecosystem|technological leadership|economic growth|prosperity/.test(kt);
      const pipelineBenefit=/research capacity|scientific capacity|innovation|competitiveness|skills? shortage|workforce|technological leadership|critical expertise|research excellence/.test(kt);
      const knowledgeSecurityTradeoff=/research[- ]security|knowledge[- ]security|security screening|research screening/.test(kt) && /restrict|screening|delay|barrier|collaboration|mobility|openness/.test(kt);
      const externalKnowledgeLoss=/lost access|los(?:e|es|ing) access|access lost|cut off|collaboration suspended|suspended collaboration|network loss|excluded from/.test(kt);
      if(!knowledgeSecurityTradeoff && !externalKnowledgeLoss && ((externalKnowledge && knowledgeGain) || (externalTalentPipeline && EU_SCOPE_RE.test(kt) && pipelineBenefit))){autonomyDown+=3;performanceUp+=2.8}
      const euTalentBuild=EU_SCOPE_RE.test(kt) && /brain gain|retain(?:ing|ed)?.{0,30}(?:eu|european|domestic)?\s*(?:researcher|scientist|talent)|recruit(?:ing|ed)?.{0,30}(?:eu|european|domestic)?\s*(?:researcher|scientist|talent)|returning researchers|researchers return/.test(kt);
      if(euTalentBuild && !externalKnowledge && !externalTalentPipeline && /researcher|scientist|research talent|scientific talent|research workforce/.test(kt)){autonomyUp+=2.6;performanceUp+=2.6}
      const internalEuMobility=EU_SCOPE_RE.test(kt) && /researcher mobility within europe|intra-eu researcher mobility|free movement of researchers|fifth freedom|brain circulation|cross-border career|career portability/.test(kt) && /increase|improve|strengthen|remove.{0,25}barrier|reduce.{0,25}barrier|free movement|circulation|capacity|competit/.test(kt);
      if(internalEuMobility && !externalTalentPipeline){autonomyUp+=2.6;performanceUp+=2.5}
    }

    // Row-specific causal direction. These rules encode mechanisms that generic
    // positive/negative word lists cannot handle reliably (for example "reduces
    // fragmentation" is positive, and productive dependence is not itself a performance loss).
    if(row.id==='knowledge'){
      const kt=norm(`${direct} ${support}`);
      if(/(?:eu|europe|european).{0,70}(?:retain|retained|returning|research careers?|doctoral training).{0,70}(?:researcher|scientist|talent|workforce)|(?:retain|retained|returning).{0,45}(?:european|eu).{0,35}(?:researcher|scientist|talent)/.test(kt)){autonomyUp+=2.4;performanceUp+=2.2}
      if(/research[- ]security|knowledge[- ]security/.test(kt) && /protect|safeguard|screening/.test(kt) && /delay|burden|restrict|friction|slow|collaboration|mobility|openness/.test(kt)){autonomyUp+=2.2;performanceDown+=2.2}
      if(/lost access|los(?:e|es|ing) access|access lost|cut off|collaboration suspended|suspended collaboration|network loss|excluded from/.test(kt) && /research|scientific|knowledge|expertise|network|collaboration/.test(kt)){autonomyDown+=3.0;performanceDown+=3.0;performanceUp=Math.max(0,performanceUp-2.0)}
    }
    if(row.id==='infrastructure'){
      const it=norm(`${direct} ${support}`);
      if(/(?:build|built|deploy|deployed|expand|expanded|diversif|secure|shared|joint|substitut|switch|adopt).{0,80}(?:compute|cloud|chip|semiconductor|research infrastructure|facility|critical raw material|critical mineral|advanced material|research data|database|repository|supplier)/.test(it)){autonomyUp+=2.4;performanceUp+=2.0}
      if(/(?:restricted access|loss of access|access cut|cut off|shortage|outage|supply disruption|licen[cs]e denied|vendor withdrawal).{0,80}(?:compute|gpu|chip|cloud|facility|critical input|research data|database|repository)|(?:compute|gpu|chip|cloud|facility|critical input|research data|database|repository).{0,80}(?:restricted|shortage|cut off|unavailable)/.test(it)){autonomyDown+=2.6;performanceDown+=2.6}
      if(/(?:locali|sovereign|domestic|european).{0,65}(?:compute|cloud|chip|infrastructure).{0,80}(?:higher cost|costly|duplication|delay|slower|performance penalty)/.test(it)){autonomyUp+=2;performanceDown+=2}
    }
    if(row.id==='conversion'){
      const ct=norm(`${direct} ${support}`);
      if(/(?:european|eu).{0,60}(?:startup|scale-up|technology firm|deep tech|manufactur).{0,90}(?:scale|expand|manufactur|production|commerciali|growth capital|procurement)|(?:scale|expand|manufactur|production|commerciali).{0,90}(?:european|eu).{0,50}(?:firm|startup|industry)/.test(ct)){autonomyUp+=2.2;performanceUp+=2.4}
      if(/(?:local[- ]content|european preference|locali|onshor|reshor).{0,90}(?:cost|fragment|delay|subscale|burden)/.test(ct)){autonomyUp+=2.2;performanceDown+=2.2}
      if(/(?:foreign capital|us venture|american venture|us market|foreign market|foreign platform|overseas manufacturing).{0,90}(?:scale|growth|commerciali|expand)|(?:rely|depend).{0,70}(?:foreign capital|us venture capital|american venture capital|us market|foreign market|foreign platform)/.test(ct)){autonomyDown+=2.8;performanceUp+=2.5}
      if(/(?:r&d|research|production|manufacturing|value capture|ip|headquarters).{0,60}(?:move|moved|moving|relocat|abroad)|relocat\w*.{0,45}(?:r&d|research|production|manufacturing|headquarters)|(?:exit europe|leave europe|foreign acquisition).{0,80}(?:r&d|research|production|control|value)/.test(ct)){autonomyDown+=5;performanceDown+=5;autonomyUp=Math.max(0,autonomyUp-1.5);performanceUp=Math.max(0,performanceUp-1.5)}
    }
    if(row.id==='rules'){
      const rt=norm(`${direct} ${support}`);
      if(/(?:eu|european).{0,70}(?:common(?: technology)? standard|mutual[- ]recognition|harmoni|coordina|joint funding|coordinated procurement|science diplomacy)/.test(rt) && /reduce.{0,30}fragment|market access|interoperab|faster|strengthen|competit|innovation/.test(rt)){autonomyUp+=2.4;performanceUp+=2.2;performanceDown=Math.max(0,performanceDown-1.5)}
      if(/(?:eu|european).{0,60}(?:research[- ]security|knowledge[- ]security|export[- ]control|screening).{0,80}(?:burden|delay|slow|restrict|friction|collaboration)/.test(rt)){autonomyUp+=2.2;performanceDown+=2.2}
      if(/(?:us|american|foreign|non-eu).{0,60}(?:export licen[cs]es?|rule|standard|platform terms|platform licensing terms|licensing terms).{0,80}(?:access|market|technology|operate|scale)|(?:preserve|maintain).{0,40}access.{0,50}(?:us|american|foreign|non-eu).{0,40}(?:rule|licen[cs]e|standard)/.test(rt)){autonomyDown+=2.4;performanceUp+=2.0}
      if(/(?:fragmented national|regulatory fragmentation|approval delay|permit delay|decision delay).{0,80}(?:research|innovation|technology|project|competit)|(?:foreign export control|foreign sanction|licen[cs]e denied).{0,80}(?:access|technology|research|innovation)/.test(rt)){autonomyDown+=2.2;performanceDown+=2.4}
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
    // V17.13.26: every Matrix placement, including reviewed/manual adjudications, must
    // still satisfy a minimal semantic contract. A stored row/quadrant is a strong prior,
    // not a permanent bypass. This protects the Matrix from stale adjudications and from
    // broad keyword matches that happen to mention Europe, technology, investment or risk.
    const d=norm(`${candidateWhat(x)} ${signalTheme(x)} ${clean(x.signal_note||x._evidencePoint||'')}`);
    const support=norm(`${clean(evidence?.title||'')} ${clean(evidence?.summary||'')} ${clean(evidence?.relevance_note||'')} ${clean(x._matrixBasis||evidence?.matrix_evidence_basis||'')} ${clean(evidence?.bridge_sentence||'')} ${clean(evidence?.external_eu_bridge||'')}`);
    const t=`${d} ${support}`;
    const evidenceSignal=x._origin==='Evidence signal';
    const reviewedMatrix=clean(x._matrixSource||evidence?.matrix_classification_source||'')==='reviewed_underlying_source';
    const ext=/\b(china|chinese|united states|us|american|foreign|non-eu|third-country|third country|extra-eu|taiwan|japan|south korea|korea|uk|britain|canada)\b/;
    const eu=EU_SCOPE_RE;
    const euScoped=eu.test(t) || (evidenceSignal && clean(evidence?.eu_relevance||'').toLowerCase()==='direct');
    if(!euScoped) return false;

    if(reviewedMatrix){
      // Reviewed source adjudications remain valuable, but the saved evidence basis must
      // itself express the row mechanism and both axes. This catches stale/manual mappings
      // without forcing the generic keyword classifier to rediscover a reviewed source.
      // For reviewed Knowledge-A talent findings, the reviewed basis may select the
      // source-supported European capability-building mechanism from a source that also
      // reports a secondary external-talent mechanism. Other cells keep the fuller saved
      // source context used by the established semantic contract.
      const reviewedBasis=clean(x._matrixBasis||evidence?.matrix_evidence_basis||'');
      const b=norm((row.id==='knowledge' && column.id==='A' && reviewedBasis)
        ? `${reviewedBasis} ${clean(evidence?.title||'')}`
        : `${reviewedBasis} ${clean(evidence?.summary||'')} ${clean(evidence?.title||'')}`);
      const has2=(a,z)=>a.test(b)&&z.test(b);
      if(row.id==='knowledge'){
        if(column.id==='A') return /researcher|scientist|talent|research workforce|research career|doctoral|research mobility|brain circulation|fifth freedom/.test(b) && /retain|return|domestic|european capacity|leading researchers|research careers|funding|circulation|mobility|career portability|remove barriers|free movement/.test(b) && !/external demand|international talent|third-country|foreign talent|us research disruption|outside europe/.test(b);
        if(column.id==='B'){ const europeanSafeguard=/(?:eu|european|member states|national|netherlands|dutch).{0,90}(?:research[- ]security|knowledge[- ]security|screening|safeguard|protect|restriction)|(?:research[- ]security|knowledge[- ]security|screening|safeguard).{0,90}(?:eu|european|member states|national|netherlands|dutch)/.test(b); return europeanSafeguard && /collaboration|mobility|openness|friction|cost|burden|delay|restrict/.test(b) && !/pressure behind restrictions|evidence of (?:the )?security pressure|may lead to restrictions|incident.{0,50}(?:screening|restriction)/.test(b) && !/(?:us|american|china|chinese|foreign).{0,70}(?:grant restriction|funding restriction|export control|restriction).{0,90}(?:damage|harm|restrict).{0,60}(?:collaboration|mobility|science)/.test(b); }
        if(column.id==='C') return /international|third-country|foreign|external|outside europe|global talent|visiting researcher|research network/.test(b) && /inflow|attract|retain|access|expertise|capacity|competit|strengthen|benefit|career/.test(b);
        return /brain drain|outflow|leave|loss|leakage|espionage|knowledge theft|access loss|exclusion|adverse|weaken|strategic exposure|collaboration loss|network loss/.test(b) && /researcher|scientist|talent|knowledge|research|expertise|collaboration|network/.test(b);
      }
      if(row.id==='infrastructure'){
        if(column.id==='A') return /european|eu|home-controlled|indispensable|domestic/.test(b) && /capacity|capability|infrastructure|semiconductor|compute|input|chokepoint|supplier/.test(b) && /leverage|competit|reduce|resilien|control|secure/.test(b);
        if(column.id==='B') return /european|eu|domestic|control|sovereign|autonomy/.test(b) && /cost|performance|expensive|delay|substitut|trade-off|tradeoff/.test(b);
        if(column.id==='C') return /external|us|foreign|non-eu|rented|dependent|reliant|outside/.test(b) && /(?:access|service|facility|compute|input).{0,70}(?:enable|support|provide|sustain|essential|frontier|capability|performance)|(?:enable|support|provide|sustain|essential).{0,70}(?:access|service|facility|compute|capability|performance)|continues? to obtain/.test(b);
        return /depend|external|chokepoint|supply|restriction|disruption|vulnerab/.test(b) && /loss|adverse|obstacle|cost|disrupt|weaker|capacity|performance|severe/.test(b);
      }
      if(row.id==='conversion'){
        if(column.id==='A') return /european|eu|home champion|remain european|value retention/.test(b) && /scale|production|industrial|capability|finance|commercial|operational/.test(b);
        if(column.id==='B') return /control|autonomy|security|domestic|european|preference|local/.test(b) && /cost|effectiveness|competit|openness|burden|subscale|friction/.test(b);
        if(column.id==='C') return /foreign|external|non-eu|outside|venture|capital|market/.test(b) && /depend|reliance|externally dependent|foreign/.test(b) && /(?:foreign|non-eu|outside|venture|capital|market).{0,90}(?:enable|finance|fund|support|close.{0,20}(?:gap|shortage)|expand|scale|growth|productive capacity|supply)|(?:enable|finance|fund|support|close.{0,20}(?:gap|shortage)|expand|scale|growth).{0,90}(?:foreign|non-eu|outside|venture|capital|market)/.test(b) && !/\bimplied\b|\braises? (?:the )?risk\b|\badvocated remedy\b/.test(b);
        return /loss|move|abroad|hollow|decline|fail|gap|acquisition|position/.test(b) && /industrial|firm|scale|production|technology|value|commercial/.test(b);
      }
      if(row.id==='rules'){
        if(column.id==='A') return /eu|european|common|framework|standard|science diplomacy|coordination/.test(b) && /adopt|set|common terms|project|coordina|improve|advantage|market|performance/.test(b);
        if(column.id==='B') return /security|autonomy|protect|screening|sovereignty|deterrence|restriction/.test(b) && /cost|friction|burden|openness|collaboration|competition|retaliation|slow/.test(b);
        if(column.id==='C') return /external|us|foreign|outside|rule-taking|american|non-eu/.test(b) && /(?:rule|rules|standard|standards|licen[cs]e|licen[cs]es|platform terms|regime)/.test(b) && /(?:comply|compliance|licen[cs]e|standard|platform|rule).{0,90}(?:preserve|maintain|enable|allow|provide).{0,45}(?:access|market|technology|research|operation)|(?:preserve|maintain|enable|allow|provide).{0,45}(?:access|market|technology|research|operation).{0,90}(?:foreign|us|american|non-eu|rule|standard|licen[cs]e)/.test(b);
        return /fragment|delay|weak|paper tiger|did not deliver|constraint|blocked|foreign rule|export control|sanction/.test(b) && /performance|industrial|technology|research|innovation|strategic effect|capability/.test(b);
      }
      return false;
    }

    // Concrete row mechanisms. Generic words such as "research", "investment", "market",
    // "AI" or "program" are not enough to choose a row.
    const rowPatterns={
      knowledge:/\b(researcher|researchers|scientist|scientists|academic|academics|faculty|doctoral|phd|doctoral candidate|doctoral candidates|phd student|phd students|research talent|scientific talent|research workforce|science workforce|research collaboration|scientific collaboration|research cooperation|scientific cooperation|knowledge flow|knowledge flows|knowledge transfer|knowledge leakage|know-how|expertise|research careers?|research mobility|researcher mobility|visiting researcher|visiting researchers|research visit|research visits|scientific visitor|scientific visitors|international student|international students|international graduate|international graduates|science diplomacy|open science|research security|academic freedom|higher education|research network|research networks)\b/,
      infrastructure:/\b(compute|computing|supercomputer|gpu|gpus|cloud|data center|data centre|semiconductor|semiconductors|chip|chips|microelectronics|quantum|reactor|reactors|nuclear|grid|electricity|battery|batteries|lithium|critical mineral|critical minerals|critical raw material|critical raw materials|rare earth|research instrument|scientific instrument|research facility|research facilities|infrastructure|telecom|telecommunications|5g|6g|satellite|cable|supply chain|supply chains|strategic input|strategic inputs|technology vendor|technology vendors|value chain|value chains|research infrastructure|advanced material|advanced materials|research data|scientific data|research database|scientific database|data repository|data repositories|biobank|biobanks|ai factory|gigafactory)\b/,
      conversion:/\b(startup|startups|start-up|start-ups|scale-up|scale-ups|scaleup|scaleups|technology firm|technology firms|deep tech firm|deep tech firms|manufacturer|manufacturing|commercialisation|commercialization|industrialisation|industrialization|venture capital|growth capital|equity finance|procurement|production capacity|manufacturing capacity|factory|factories|market expansion|market share|value capture|industrial capacity|technology transfer|technology transfers|foreign acquisition|acquisition|acquired|relocation|scale-up gap|funding gap)\b/,
      rules:/\b(export control|export controls|regulation|regulatory|standard|standards|standardisation|standardization|governance|funding programme|funding program|framework programme|framework program|joint programme|joint program|screening|research security|knowledge security|restriction|restrictions|ban|bans|law|laws|directive|decision process|approval|approvals|permitting|permit|permits|subsidy|subsidies|state aid|sanction|sanctions|licensing|licences|licenses|licence|license|rule|rules|policy framework|science diplomacy|mutual recognition|coordination)\b/
    };
    const rowRe=rowPatterns[row.id];
    if(!rowRe.test(t)) return false;

    const externalTalentInput=/(?:international|foreign|non-eu|third-country|third country|extra-eu).{0,75}(?:researchers?|scientists?|research talent|scientific talent|expertise|doctoral candidates?|phd students?|stem students?|graduates?|visiting researchers?|research visitors?|research networks?|collaboration)|(?:researchers?|scientists?|research talent|scientific talent|expertise|doctoral candidates?|phd students?|stem students?|graduates?|visiting researchers?|research visitors?|research networks?|collaboration).{0,75}(?:international|foreign|non-eu|third-country|third country|extra-eu)/.test(t);
    const talentBenefit=/\b(?:strengthen|boost|improve|support|enable|fill|address|increase|expand|build|maintain|sustain).{0,50}(?:research|scientific|innovation|technology|workforce|capacity|capability|competitiveness|excellence)|(?:research|scientific|innovation|technology).{0,45}(?:capacity|capability|competitiveness|excellence)|skills? shortage|talent shortage|critical expertise|innovation ecosystem|technological leadership\b/.test(t);
    const talentRetention=/retain|retention|stay|post-study|post study|post-research|post research|job search|employment|research career|research careers|workforce transition|settle|long-term career/.test(t);
    const euTalentOutflow=/\b(?:eu|europe|european|member states|austria|belgium|bulgaria|croatia|cyprus|czech|denmark|estonia|finland|france|germany|greece|hungary|ireland|italy|latvia|lithuania|luxembourg|malta|netherlands|poland|portugal|romania|slovakia|slovenia|spain|sweden).{0,90}(?:brain drain|researcher outflow|scientists? leave|researchers? leave|talent outflow|talent loss|unable to retain|failure to retain|moving abroad)|(?:brain drain|researcher outflow|scientists? leave|researchers? leave|talent outflow|talent loss|unable to retain|failure to retain|moving abroad).{0,90}(?:eu|europe|european|member states)\b/.test(t);
    const knowledgeAccessLoss=/\b(?:eu|europe|european).{0,100}(?:excluded|cut off|lost access|los(?:e|es|ing) access|collaboration suspended|network access lost|network loss|knowledge leakage|knowledge theft|espionage|appropriation|loss of know-how|loss of expertise)|(?:knowledge leakage|knowledge theft|espionage|loss of know-how|loss of expertise|collaboration suspended|access cut|lost access|network loss).{0,100}(?:eu|europe|european)\b/.test(t);

    const infraExternal=/\b(?:foreign|non-eu|us|american|china|chinese|taiwan|korea|japan|uk|britain).{0,70}(?:compute|gpu|cloud|semiconductor|chip|quantum|research facility|research infrastructure|instrument|critical raw material|critical mineral|advanced material|research data|scientific data|database|data repository|biobank|supplier|vendor|technology)|(?:compute|gpu|cloud|semiconductor|chip|quantum|research facility|research infrastructure|instrument|critical raw material|critical mineral|advanced material|research data|scientific data|database|data repository|biobank|supplier|vendor|technology).{0,70}(?:foreign|non-eu|us|american|china|chinese|taiwan|korea|japan|uk|britain)\b/.test(t);
    const infraDependency=/depend|reliance|rely on|foreign supplier|external supplier|non-eu vendor|vendor lock|lock-in|single supplier|concentrat|import dependence|access depends|access contingent/.test(t);
    const infraBenefit=/\b(?:enable|enables|enabled|support|supports|provide|provides|allow|allows|give|gives|access to|scale|accelerat|expand|increase|boost|frontier|best available|critical for|essential for|preserve|preserves|maintain|maintains|comparable performance).{0,70}(?:research|innovation|ai|science|compute|capability|capacity|performance|technology)|(?:research|innovation|science|technology).{0,60}(?:benefit|capability|capacity|performance|scale|frontier access)|comparable performance\b/.test(t);
    const infraControlGain=/\b(?:build|built|deploy|deployed|operate|operational|expand|expanded|invest|fund|procure|secure|diversif|substitut|switch|adopt|locali|sovereign|domestic|alternative supplier|multi-source|multi source|onshor|reshor|european-owned|eu-owned|european controlled|eu-controlled|eu-sourced|european-sourced|joint european|shared european).{0,80}(?:compute|cloud|chip|semiconductor|quantum|research infrastructure|facility|critical raw material|critical mineral|advanced material|research data|database|repository|supply|capacity|infrastructure)|(?:reduce|cut).{0,45}(?:dependence|reliance|import dependence)\b/.test(t);
    const infraHarm=/\b(?:restricted access|loss of access|access cut|cut off|export controls?|ban|sanctions?|shortage|bottleneck|chokepoint|outage|no substitute|cannot obtain|unable to obtain|delays?|slower|capacity loss|loss of.{0,30}capacity|reduces? capacity|limits? capacity|constrains? research|blocks? research|supply disruption)\b/.test(t);
    const infraTradeoff=/\b(?:higher cost|costlier|costly|expensive|cost increase|delay|slower|duplication|fragmentation|lower performance|performance penalty|inefficien|scarcer|shortage|longer lead time)\b/.test(t);

    const conversionExternal=/\b(?:foreign capital|foreign venture|us venture capital|american venture capital|us venture|american venture|non-eu capital|foreign market|us market|american market|foreign platform|us platform|american platform|foreign cloud|non-eu cloud|overseas manufacturing|foreign manufacturing|joint venture|foreign partner|foreign acquisition)\b/.test(t);
    const conversionEnable=/\b(?:rely|relies|reliant|depend|depends|financed by|funded by|capital from|access to|scale through|scale via|grow through|grow via|commerciali.{0,20}through|sell into|market access|platform access|manufactur.{0,20}abroad|partner.{0,20}to scale).{0,110}(?:foreign|non-eu|us|american|china|chinese|global market|platform|capital|venture|market|manufactur|partner)|(?:foreign capital|foreign venture|us venture capital|american venture capital|us market|american market|foreign platform|global market).{0,110}(?:scale|growth|commerciali|expand|market access|production)\b/.test(t);
    const conversionScale=/\b(?:scale-ups?|scale up|scale|scaled|scaling|startups?|start-ups?|commerciali\w*|industriali\w*|manufactur\w*|production capacity|factory|factories|market expansion|market share|growth|venture round|growth capital|procurement order|procurement contract|value creation|industrial capacity)\b/.test(t);
    const conversionControl=/\b(?:local[- ]content|european preference|eu preference|onshor|reshor|locali|domestic production|european production|eu production|de-risk|derisk|strategic autonomy|sovereignty|screening|secure supply|retain control|keep.{0,25}in europe)\b/.test(t);
    const conversionTradeoff=/\b(?:higher cost|costly|expensive|delay|slower|fragment|subscale|burden|reduced scale|smaller market|less competitive|lost efficiency|duplication)\b/.test(t);
    const conversionLoss=/\b(?:exit europe|leave europe|move abroad|moving abroad|relocat\w*.{0,45}(?:r&d|research|production|manufacturing|headquarters)|(?:r&d|research|production|manufacturing|headquarters).{0,45}(?:move|moved|moving|relocat\w*|abroad)|factory closure|shut down|hollow|lost production|loss of production|value capture abroad|profits? abroad|ip sold abroad|technology sold abroad|commerciali\w*.{0,30}abroad|foreign acquisition.{0,80}(?:control|r&d|research|production|headquarters|value)|scale-up gap.{0,60}(?:leave|abroad|lost)|funding gap.{0,60}(?:leave|relocat|fail.{0,20}scale))\b/.test(t);

    const euRuleAction=/\b(?:eu|european union|european commission|council|member states|european parliament|europe).{0,85}(?:adopt|enact|launch|agree|harmoni|standard|regulat|screen|research[- ]security|knowledge[- ]security|export[- ]control|funding programme|funding program|joint programme|joint program|procurement|state aid|science diplomacy|mutual[- ]recognition|coordinate|coordination)|(?:eu|european).{0,50}(?:framework|standard|regulation|programme|program|strategy)\b/.test(t);
    const foreignRule=/\b(?:us|united states|american|china|chinese|non-eu|foreign|platform).{0,80}(?:export controls?|export licen[cs]es?|rule|rules|standard|standards|regulation|licence|license|licensing terms|platform licensing terms|platform terms|terms of service|sanction|restriction)|(?:foreign|non-eu|us|american|chinese).{0,35}(?:rules|standards|regime|licensing|licensing terms)\b/.test(t);
    const ruleBenefit=/\b(?:reduce|reduces|reduced).{0,35}(?:fragmentation|dependence|reliance|delay)|faster decision|shorter approval|mutual[- ]recognition|common(?: technology)? standard|harmoni|interoperab|market access|global adoption|international adoption|sets? the standard|rule-setting|coordinate|coordination.{0,35}(?:improve|strengthen|enable)|funding.{0,35}(?:scale|strengthen|build|support).{0,35}(?:research|innovation|technology|capacity)\b/.test(t);
    const ruleFriction=/\b(?:delays?|slow|slows|burden|compliance cost|fragment|restrict|barrier|licen[cs]ing burden|licen[cs]e burden|administrative burden|collaboration cost|mobility cost|exclude|suspend|longer approval)\b/.test(t);
    const externalRuleBenefit=/\b(?:access|market access|technology access|licen[cs]ed access|platform access|permission|authori[sz]ation|compliance).{0,65}(?:enable|allow|support|scale|market|technology|research|innovation)|(?:foreign|us|american|non-eu).{0,70}(?:licen[cs]es?|licensing terms|standard|platform|rule).{0,75}(?:preserve|maintain|enable|allow|access|market|technology|scale|operate)|(?:comply|compliance).{0,60}(?:foreign|us|american|non-eu).{0,60}(?:licen[cs]e|licensing terms|standard|platform|rule).{0,60}(?:access|technology|market|research)\b/.test(t);
    const ruleBlock=/\b(?:gridlock|cannot decide|unable to decide|decision delay|regulatory delay|fragmented governance|regulatory fragmentation|national fragmentation|approval rules? delay|approval delay|blocked by|export controls?|sanctions?|exclusion|licen[cs]e denied|access denied|foreign restriction|foreign rules?.{0,40}(?:block|restrict|delay)|standards? incompatib|permit delay|approval delay)\b/.test(t);

    // A-cells require an observed or committed European capability gain, not aspiration.
    const openingText=evidenceSignal?t:d;
    const openingRealized=/\b(?:operational|deployed|opened|completed|implemented|secured|attracted|retained|recruited|expanded|increased|built|now produces|now provides|market share rose|overtook|outpaced|adopted by|internationally adopted|global adoption|reduced dependence|reduced reliance)\b/.test(openingText);
    // Bare mentions of "funding" in a report are not a capability gain.  Count a
    // commitment only when the text describes an actual programme/action, award or money.
    const openingCommitted=/\b(?:launch(?:es|ed|ing)?|co-fund(?:s|ed|ing)?|jointly fund(?:s|ed|ing)?|award(?:s|ed|ing)?|approve(?:s|d|ing)?|select(?:s|ed|ing)?|establish(?:es|ed|ing)?|create(?:s|d|ing)?|sign(?:s|ed|ing)?|adopt(?:s|ed|ing)?|enact(?:s|ed|ing)?|begin(?:s|ning)? construction|under construction|procure(?:s|d|ment)?|invest(?:s|ed|ing)?|commits?\s+(?:€|\$|£|[0-9])|backs?\s+(?:€|\$|£|[0-9]))\b/.test(openingText)
      || /(?:eu|european commission|erc|msca|horizon europe|programme|program|initiative|grant scheme).{0,70}(?:funds|funded|funding|awards?|allocat(?:es|ed|ing)?|commits?)/.test(openingText)
      || /(?:funding|grant|investment).{0,45}(?:€|\$|£|[0-9])/.test(openingText);
    const aspirational=/\b(?:aims? to|plans? to|proposal|proposed|roadmap|could|would|should|needs? to|must|potential to|prospects? for|recommend(?:s|ed|ation)|intends? to|seeks? to|calls? for)\b/.test(openingText);
    const nonOpening=/\b(?:funding gap|capital gap|finance gap|shortage|may seek|could seek|might seek)\b/.test(openingText);
    const concreteOpening=(openingRealized||openingCommitted||reviewedMatrix)&&!aspirational&&!nonOpening;

    if(row.id==='knowledge'){
      if(column.id==='A'){
        // Attracting a specifically international/third-country pipeline is C, not A,
        // unless the evidence is about returning Europeans or building the domestic pipeline.
        const ownPipeline=/\b(?:retain european|retain eu|european researchers?|eu researchers?|domestic researchers?|research careers?|doctoral training|researcher careers?|returning researchers?|researchers? return|brain gain|brain circulation|intra-eu researcher mobility|researcher mobility within europe|fifth freedom|career portability|free movement of researchers).{0,90}(?:strengthen|capacity|competitiveness|excellence|career|retain|return|fund|circulation|mobility|remove barriers|free movement)|(?:erc|msca|horizon europe).{0,70}(?:researcher|talent|career|grant|fund)\b/.test(t);
        return concreteOpening && !externalTalentInput && (ownPipeline||talentBenefit) && /retain|recruit|return|career|grant|fund|training|brain gain|brain circulation|mobility|free movement|career portability|talent/.test(t);
      }
      if(column.id==='B'){ const selfSafeguard=/(?:eu|european|member states|national).{0,90}(?:research[- ]security|knowledge[- ]security|screening|safeguard|protect)|(?:research[- ]security|knowledge[- ]security|screening).{0,90}(?:eu|european|member states|national)/.test(t); return selfSafeguard && /research[- ]security|knowledge[- ]security|screening|protect|safeguard|sensitive|espionage|interference/.test(t) && ruleFriction && /collabor|mobility|visa|openness|researcher|university|academic/.test(t); }
      if(column.id==='C') return externalTalentInput && (talentBenefit||talentRetention) && /retain|retention|stay|access|collabor|cooperat|mobility|expertise|research network|research visit|visiting researcher|recruit|employment/.test(t) && !/lost access|los(?:e|es|ing) access|access lost|cut off|collaboration suspended|suspended collaboration|network loss|excluded from/.test(t);
      return euTalentOutflow || (knowledgeAccessLoss && /capacity|capability|competit|loss|weaken|harm|strategic|adverse|risk/.test(t));
    }

    if(row.id==='infrastructure'){
      if(column.id==='A') return concreteOpening && infraControlGain && infraBenefit;
      if(column.id==='B') return infraControlGain && infraTradeoff;
      if(column.id==='C') return infraExternal && infraDependency && infraBenefit;
      return infraDependency && infraHarm;
    }

    if(row.id==='conversion'){
      if(column.id==='A') return concreteOpening && conversionScale && /\b(?:eu|europe|european).{0,80}(?:firm|startup|scale-up|manufactur|production|industrial|technology|deep tech)|(?:firm|startup|scale-up|manufactur|production).{0,80}(?:eu|europe|european)\b/.test(t);
      if(column.id==='B') return conversionControl && conversionScale && conversionTradeoff;
      if(column.id==='C'){ const negatedForeignEnable=/(?:does not|did not|no evidence|without evidence|fails? to|not show).{0,110}(?:foreign capital|foreign investor|non-eu|us venture|foreign market).{0,110}(?:enable|finance|fund|scale|growth|commerciali)/.test(t); return conversionExternal && conversionEnable && conversionScale && !negatedForeignEnable; }
      return conversionLoss;
    }

    if(row.id==='rules'){
      if(column.id==='A') return concreteOpening && euRuleAction && ruleBenefit;
      if(column.id==='B'){ const selfRule=euRuleAction || /(?:eu|european|member states).{0,80}(?:research[- ]security|knowledge[- ]security|export[- ]controls?|screening|rules?)/.test(t); return selfRule && !foreignRule && /research[- ]security|knowledge[- ]security|screening|export[- ]controls?|de-risk|derisk|protect|safeguard|sovereign/.test(t) && ruleFriction; }
      if(column.id==='C'){ const negatedProductiveRule=/(?:does not|did not|no evidence|without evidence|fails? to|not establish).{0,100}(?:foreign rule|licen[cs]e|licensing|standard|platform|preserve|maintain|enable).{0,100}(?:access|technology|market|research|scale)/.test(t); return foreignRule && externalRuleBenefit && !negatedProductiveRule; }
      return ruleBlock && /research|innovation|technology|scientific|firm|startup|compute|chip|semiconductor|market access/.test(t);
    }
    return false;
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
    const meritApi=SourceMerit||null;
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
      const dir=directionScores(x,evidence,r,questions);
      const col=columnFor(dir);
      if(!col) continue;
      if(!cellEvidencePass(x,evidence,r,col)) continue;
      // With the V17.13.26 cell contract, a single explicit source-backed row mechanism
      // can be enough for an evidence record; weak signals still require the higher
      // materiality threshold because their headlines must carry the mechanism themselves.
      if(m<2.4 && !(x._origin==='Evidence signal' && m>=1.1)) continue;
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
    const meritInput={
      title:clean(x._origin==='Evidence signal' ? (evidence?.title||x.title||candidateWhat(x)) : (x.headline||x.title||candidateWhat(x))),
      authors:clean(x._origin==='Evidence signal' ? (evidence?.authors||'') : (x.authors||'')),
      source:sourceFor(x),
      date:dateFor(x),
      link:linkFor(x),
      itemType:clean(x._origin==='Evidence signal' ? (evidence?.type||x.type||'') : (x.type||x.signal_kind||x.signal_type||'')),
      sourceTier:clean(x._origin==='Evidence signal' ? (evidence?.source_tier||x.source_tier||'') : (x.source_tier||'')),
      euRelevance:clean(x._origin==='Evidence signal' ? (evidence?.eu_relevance||x.eu_relevance||'') : (x.eu_relevance||'')),
      origin:x._origin||'Weak signal',
      strand:clean(x.strand||'')
    };
    const sourceMerit=meritApi?.forItem?meritApi.forItem(meritInput):null;
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
      matrixEvidenceBasis:clean(x._matrixBasis||x.matrix_evidence_basis||evidence?.matrix_evidence_basis||''),
      row,rowScore:rowPick.score,column,cellName:cell[0],cellSubtitle:cell[1],
      questions,questionFlags:flags,questionCount:qCount,
      direction,triage:{reach,irreversibility,attentionGap:attention,actionability,total:triage},
      actor:actorFor(row),
      why:whyQualifies(flags,column,row),
      originalWhy:signalWhy(x),
      materiality,euLink,overall,
      strongCandidate:qCount>=2,
      confidence:clamp(Math.round((Math.min(6,materiality)/6*.35 + Math.min(6,euLink)/6*.2 + Math.min(3,qCount)/3*.25 + Math.min(8,Math.abs(direction.autonomy)+Math.abs(direction.performance))/8*.2)*100),35,96),
      sourceTier:meritInput.sourceTier,
      euRelevance:meritInput.euRelevance,
      sourceMerit,
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
      [/industrial accelerator act count/, 'Industrial Accelerator Act risks weak implementation.'],
      [/talent for innovation attraction platform/, 'Europe’s R&I capability relies partly on attracting and retaining international talent.']
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

  function whyBullet(x){
    const b=shortBullet(x);
    const t=norm(`${b} ${x?.bibliographicTitle||''}`);
    if(/talent for innovation attraction platform|international talent/.test(t)) return 'This matters because Europe gains research capability from international students and researchers only if it can attract them and convert study or research stays into longer-term careers.';
    if(/ai export controls|frontier compute/.test(t)) return 'This matters because restrictions on frontier compute can directly limit which models European teams can train, audit and deploy.';
    if(/ai supply-chain governance/.test(t)) return 'This matters because control over model, chip, cloud and data-chain bottlenecks determines where Europe remains dependent.';
    if(/ai rule fragmentation|digital power/.test(t)) return 'This matters because fragmented AI rules reduce Europe’s ability to turn regulation into coherent market and technology leverage.';
    if(/ai competitiveness.*capital and compute/.test(t)) return 'This matters because simultaneous shortages of growth capital and compute make it harder for European AI firms to reach frontier scale.';
    if(/military-ai autonomy/.test(t)) return 'This matters because buying foreign military AI can deliver short-term capability without transferring the models, compute or know-how needed for autonomy.';
    if(/us coercion.*digital firms/.test(t)) return 'This matters because dependence on US digital providers creates channels through which external political pressure can affect EU policy choices.';
    if(/tech dependence has risen|growth remains exposed to external tech dependence/.test(t)) return 'This matters because rising external technology dependence narrows Europe’s options when suppliers, standards or geopolitical conditions change.';
    if(/tech sovereignty still relies on us platforms/.test(t)) return 'This matters because platform dependence leaves core digital services and data flows subject to non-European infrastructure and corporate decisions.';
    if(/defence-tech firms raise/.test(t)) return 'This matters because very large European defence-tech rounds show whether strategic firms can reach scale without relocating or relying on non-European capital.';
    if(/manufacturing resilience.*reconfigurable/.test(t)) return 'This matters because reconfigurable digital production can let European manufacturers absorb disruptions without rebuilding entire production systems.';
    if(/procurement preferences/.test(t)) return 'This matters because procurement preferences can create a home market for European technology, but may also raise deployment costs or slow access to the best available tools.';
    if(/industrial accelerator act risks weak implementation/.test(t)) return 'This matters because an industrial policy that is ambitious on paper but weak in execution will not create the scale or investment certainty European innovators need.';
    if(/dual circulation.*ev/.test(t)) return 'This matters because China’s domestic-demand and technology strategy changes cost, scale and market pressure on Europe’s EV producers and suppliers.';
    if(/cee industry.*geopolitical scale/.test(t)) return 'This matters because Central and Eastern European production networks are highly exposed to shifts in trade, investment and supply-chain geography.';
    if(/us ev strategy/.test(t)) return 'This matters because faster US scaling of EV supply chains raises the capital, technology and policy benchmark European industry must match.';
    if(/china.?s ev shift.*coordination/.test(t)) return 'This matters because fragmented national responses make it harder for Europe to answer a fast-moving Chinese industrial challenge at continental scale.';
    if(/productivity gap.*r&d and equity/.test(t)) return 'This matters because weak R&D intensity and shallow equity finance jointly reduce the rate at which European ideas become high-productivity firms.';
    if(/geo-industrial policy.*scale with resilience/.test(t)) return 'This matters because Europe needs industrial scale and supply resilience at the same time; optimising only one leaves the other as a strategic weakness.';
    if(/industrial accelerator act may raise eu costs/.test(t)) return 'This matters because stronger European preference rules can support domestic suppliers while increasing input or deployment costs for firms and researchers.';
    if(/espionage case/.test(t)) return 'This matters because access gained through research or institutional placements can become a route to sensitive knowledge and facilities.';
    if(/chinese interference.*knowledge flows/.test(t)) return 'This matters because foreign-interference tactics can distort partnerships and create channels for sensitive knowledge to leave European institutions.';
    if(/allea links open science/.test(t)) return 'This matters because safeguards that are too broad can damage openness, while safeguards that are too weak leave sensitive collaborations exposed.';
    if(/dutch 2026 guidance/.test(t)) return 'This matters because national knowledge-security guidance changes the due-diligence and collaboration burden placed on universities and research organisations.';
    if(/ethics committees/.test(t)) return 'This matters because ethics-style review committees are one practical way to screen security-sensitive research without imposing blanket restrictions.';
    if(/vc gap.*outside-investor/.test(t)) return 'This matters because a domestic VC gap can move ownership, governance and eventual exits of European technology firms toward outside investors.';
    if(/scale-ups lack deep institutional capital/.test(t)) return 'This matters because without deep European late-stage capital, promising firms may need foreign funding or listings just when strategic value is highest.';
    if(/€80bn.*scale-up alliance|investment alliance.*scale up/.test(t)) return 'This matters because pooling large pools of European capital can close the late-stage financing gap that pushes successful firms to scale elsewhere.';
    if(/radio astronomy|astronomy/.test(t)) return 'This matters because European researchers can depend on access to overseas facilities, spectrum and scientific networks.';
    if(/erc adds|erc advanced grant/.test(t)) return 'This matters because large frontier grants determine whether Europe can retain leading researchers and sustain ambitious long-horizon projects.';
    if(/research talent|researcher mobility|barriers to eu mobility|attract us research talent/.test(t)) return 'This matters because researcher mobility changes the skills and scientific capacity available to European labs and universities.';
    if(/research-security|research security|espionage|foreign interference|knowledge flows|open science|research safeguards|ethics committees|security-relevant research/.test(t)) return 'This matters because research-security choices set the boundary between open collaboration and protection of sensitive knowledge.';
    if(/science diplomacy|collaboration curbs|research-collaboration/.test(t)) return 'This matters because partnership rules determine which research networks, facilities and expertise remain accessible to European teams.';
    if(/chip|semiconductor/.test(t)) return 'This matters because chip access and production determine whether European R&I can use critical hardware without external restrictions.';
    if(/frontier compute|compute dependence|capital and compute|ai export|ai supply-chain|ai rule|digital power|military-ai|defence ai|us platforms|digital firms|digital tech|tech dependence/.test(t)) return 'This matters because control of compute, platforms and AI infrastructure determines whether Europe can build and govern frontier digital capability on its own terms.';
    if(/vc gap|scale-up|scale up|institutional capital|€80bn|investment alliance/.test(t)) return 'This matters because growth capital determines whether European technology firms can scale while keeping headquarters, IP, talent and high-value jobs in Europe.';
    if(/battery|raw-material|raw material/.test(t)) return 'This matters because access to strategic materials and production equipment sets the resilience and scale ceiling for European advanced manufacturing.';
    if(/circular economy/.test(t)) return 'This matters because reuse and substitution can reduce Europe’s exposure to imported materials and industrial inputs.';
    if(/dual-use|defence|military|space capability/.test(t)) return 'This matters because dual-use and defence policy can build strategic capability while adding security, export-control and openness constraints.';
    if(/manufactur|industrial|industry|electric vehicle| ev |procurement|productivity|geo-industrial|automotive capacity/.test(` ${t} `)) return 'This matters because industrial policy determines whether European research is converted into domestic production, deployment and scale.';
    if(/tech sovereignty|sovereignty rules|autonomy|strategic dependence|critical dependence/.test(t)) return 'This matters because sovereignty choices trade off external access, domestic control and the cost of replacing foreign capability.';
    if(/investment screening|foreign investment|economic-security|economic security|openness to deterrence|strategic conditions/.test(t)) return 'This matters because screening and economic-security tools can protect strategic capability while narrowing access to capital, partners or markets.';
    if(/china.*technology|china tech|leverage over china|fragmented.*china|dual circulation|china.?s ev/.test(t)) return 'This matters because EU–China technology ties can combine market opportunity with asymmetric dependence and pressure to de-risk.';
    if(/cbdc|e-hryvnia|monetary infrastructure/.test(t)) return 'This matters because technical standards, cyber resilience and governance determine who controls critical digital payment infrastructure.';
    const fallback=RadarInsights?.whyFor?.({title:x?.bibliographicTitle||x?.title||'',core_message:b,matrix_evidence_basis:x?.matrixEvidenceBasis||''})||'';
    if(fallback && norm(fallback)!==norm(b)) return fallback;
    const row=x?.row?.id||'other';
    const rowWhy={knowledge:'It changes Europe’s access to people, knowledge and research networks.',infrastructure:'It changes Europe’s control over critical research infrastructure and technical inputs.',conversion:'It changes whether European research can be commercialised and scaled in Europe.',rules:'It changes whether Europe can shape the rules governing strategic research and technology.'}[row]||'It changes Europe’s control, capability or external dependence in research and innovation.';
    return rowWhy;
  }

  function qualityAwareScore(x){
    // Substantive Matrix qualification happens before this function is used. Once a
    // finding is legitimately placed, combine finding strength with the source-merit
    // score documented in Stuff (authority + relevance + evidence + transparency).
    // Source prestige never creates a Matrix placement; it only helps order qualified findings.
    const meritScore=Number(x?.sourceMerit?.score||0);
    const findingScore=Number(x?.overall||0);
    return findingScore*4+meritScore;
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
    signals.sort((a,b)=>qualityAwareScore(b)-qualityAwareScore(a)||((b.sourceMerit?.score||0)-(a.sourceMerit?.score||0))||b.overall-a.overall||b.triage.total-a.triage.total||String(b.date).localeCompare(String(a.date))||a.title.localeCompare(b.title));
    const cells={};for(const r of ROWS){cells[r.id]={};for(const c of COLUMNS)cells[r.id][c.id]=[]}
    for(const s of signals)cells[s.row.id][s.column.id].push(s);
    for(const r of ROWS)for(const c of COLUMNS)cells[r.id][c.id].sort((a,b)=>qualityAwareScore(b)-qualityAwareScore(a)||((b.sourceMerit?.score||0)-(a.sourceMerit?.score||0))||b.overall-a.overall||b.triage.total-a.triage.total);
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

  return {ROWS,COLUMNS,CELL_NAMES,buildEvidenceIndex,classifySignal,buildFrontier,weakCandidates,evidenceCandidates,questionScores,rowScores,shortBullet,whyBullet,qualityAwareScore};
});
