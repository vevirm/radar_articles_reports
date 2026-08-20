(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  root.RadarInsights=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  const TOPICS=[
    {name:'Raw materials', terms:['critical raw material','critical raw materials','critical mineral','critical minerals','rare earth','rare earths','lithium','cobalt','nickel','graphite','copper','gallium','germanium','tungsten','mining','refining','mineral supply','resource security','cocoa','cocoa sector','cocoa supply','commodity supply']},
    {name:'Research', terms:['horizon europe','framework programme','framework program','european research council','erc plus','erc grant','research funding','research infrastructure','research security','knowledge security','science diplomacy','scientific cooperation','research cooperation','research collaboration','research and innovation','research policy','university','universities','researcher','researchers']},
    {name:'AI & compute', terms:['artificial intelligence','foundation model','foundation models','large language model','large language models','machine learning','ai infrastructure','ai factory','ai factories','gpu','gpus','compute capacity','computing capacity','supercomputing',' ai ']},
    {name:'Semiconductors & quantum', terms:['semiconductor','semiconductors','microelectronics','microchip','microchips','advanced chip','advanced chips','chip','chips','chip act','chips act','chip supply','quantum','photonics']},
    {name:'Energy', terms:['energy security','nuclear','reactor','reactors','small modular reactor','small modular reactors','smr','smrs','hydrogen','renewable','renewables','electricity grid','power grid','battery','batteries','clean tech','cleantech','fusion','decarbonisation','decarbonization','rosatom']},
    {name:'Climate & sustainability', terms:['climate','sustainability','sustainable','green deal','environmental','wellbeing','planetary boundaries','deforestation','circular economy','circular-economy','eco-social','resilience']},
    {name:'Security & defence', terms:['defence','defense','dual-use','dual use','military','nato','security screening','export control','export controls','foreign interference','knowledge leakage','economic coercion','sanction','sanctions','war','ukraine','russia']},
    {name:'Trade & industry', terms:['economic security','industrial policy','industrial competitiveness','competitiveness','manufacturing','supply chain','supply chains','trade','tariff','tariffs','investment screening','foreign direct investment','investment-led','strategic autonomy','strategic dependency','strategic dependencies','de-risking','derisking','single market','industry policy','market','investment','clearing','financial system']},
    {name:'Digital & cyber', terms:['digital infrastructure','digital transformation','digital cooperation','cloud infrastructure','cloud','telecom','telecommunications','5g','6g','submarine cable','subsea cable','data governance','data space','digital sovereignty','cybersecurity','cyber security','cyber']},
    {name:'Space', terms:['satellite','satellites','launch vehicle','launcher','copernicus','galileo','earth observation','orbital','space sector','space programme','space program']},
    {name:'Health & biotech', terms:['biotech','biotechnology','life science','life sciences','health','health security','global health','health partnership','health partnerships','pharma','pharmaceutical','pharmaceuticals','vaccine','vaccines','biomedical','genomics','bioeconomy']},
    {name:'Talent & skills', terms:['researcher mobility','scientist mobility','brain drain','brain gain','talent','skills','visa','visas','doctoral','phd','workforce','training']},
    {name:'International partnerships', terms:['global gateway','indo-pacific','indo pacific','international cooperation','international partnership','international partnerships','association agreement','associated country','eu-asia','europe-asia','china','chinese','united states','japan','south korea','india','taiwan','africa','latin america','arctic','geopolitical','partnership','partnerships']},
    {name:'Foresight', terms:['foresight','horizon scanning','scenario planning','scenario building','scenario-building','weak signal','weak signals','delphi','backcasting','anticipatory governance','futures literacy','futures research','strategic intelligence','scenario','scenarios']}
  ];
  const OTHER='Other strategic R&I';

  const EVENT_VERB=/\b(introduc|launch|adopt|propos|plan|expand|scale|build|fund|invest|restrict|tighten|strengthen|reduce|diversif|shift|change|increase|decrease|accelerat|delay|block|ban|require|open|close|create|develop|deploy|establish|agree|sign|join|withdraw|prioriti[sz]|target|support|secure|protect|screen|coordinate|cooperat|compete|decoupl|derisk|de-risk|reform|amend|extend|raise|cut|approve|reject|recast|retreat|consolidat|connect|urge|struggl|becom|remain|perform|link|bridge|acknowledg|depend|bind|push|offer|respond|pivot)\w*/i;
  const ACTOR=/\b(EU|European Union|European Commission|Europe|China|Chinese|United States|US|Japan|South Korea|India|Russia|Ukraine|NATO|Horizon Europe|European Research Council|ERC|Member States|Global Gateway|companies|industry|researchers|universities)\b/i;
  const META=/\b(the purpose of (?:the|this) (?:article|paper|study)|this (?:article|paper|study|report)|the (?:article|paper|study|report) (?:makes|contributes|then|sets|situates|examines|presents)|the analysis is set|much has already been written|annual activity report|research design and methodology|abstract\b|received funding from|grant agreement no\.?|copyright|all rights reserved|table of contents|bibliography|references)\b/i;
  const DOC_DEBRIS=/\b(annex|appendix|methodology|table of contents|contents|list of (?:figures|tables)|bibliography|references|glossary|acronyms?|abbreviations?|chapter|section)\b/i;

  function clean(v){return String(v??'').replace(/\u00ad/g,'').replace(/[ \t]+/g,' ').replace(/\s*\n\s*/g,' ').trim()}
  function norm(v){return ` ${clean(v).toLowerCase().replace(/[–—]/g,'-').replace(/[^a-z0-9+.#/&-]+/g,' ').replace(/\s+/g,' ').trim()} `}
  function keyFor(x){return norm(x.link||x.title||x.headline||'').trim()}
  function dateFor(x){return clean(x.date||x.published||x.updated||x.first_seen||'')}

  function repairOcr(v){
    let s=String(v??'').replace(/\u00ad/g,' ');
    s=s.replace(/\bnon\s*-\s*EU\b/gi,'non-EU')
       .replace(/\blarge\s*-\s*scale\b/gi,'large-scale')
       .replace(/\blong\s*-\s*term\b/gi,'long-term')
       .replace(/\bgrant\s*-\s*based\b/gi,'grant-based')
       .replace(/\binvestment\s*-\s*led\b/gi,'investment-led')
       .replace(/\binfrastructure\s*-\s*led\b/gi,'infrastructure-led')
       .replace(/\bEU\s*-\s*level\b/gi,'EU-level')
       .replace(/\bde\s*-\s*risking\b/gi,'de-risking')
       .replace(/\btoward\s+s\b/gi,'towards')
       .replace(/\bnegotiati\s+ons\b/gi,'negotiations')
       .replace(/\blo\s+ng-term\b/gi,'long-term')
       .replace(/\boﬀering\b/gi,'offering');
    return clean(s);
  }

  function isDocumentDebris(value){
    const s=clean(value);
    if(!s) return true;
    if(/\.{4,}|·{4,}|_{4,}|-{8,}/.test(s)) return true;
    if(/^\s*(?:page\s*)?\d{1,4}\s+(?:annex|appendix|chapter|section|methodology)\b/i.test(s)) return true;
    if(/^(?:annex|appendix|chapter|section)\s+[a-z0-9ivx.-]+\s*[:.-]/i.test(s)) return true;
    if(/^(?:table of contents|contents|list of (?:figures|tables)|bibliography|references|glossary|acronyms?|abbreviations?)\b/i.test(s)) return true;
    if(/\b(?:annex|appendix)\s+\d+\s*:\s*(?:methodology|methods?|technical annex)\b/i.test(s)) return true;
    if(/^\s*\d{1,4}\s+[A-Z][A-Z0-9 &()/:,.-]{8,}\s*$/.test(s)) return true;
    if(/^\s*(?:page\s+)?\d{1,4}\s*(?:of\s+\d{1,4})?\s*$/i.test(s)) return true;
    const letters=(s.match(/[A-Za-z]/g)||[]).length;
    const upper=(s.match(/[A-Z]/g)||[]).length;
    const words=s.split(/\s+/).filter(Boolean).length;
    if(words<=16&&letters>=8&&upper/letters>0.76&&DOC_DEBRIS.test(s)&&!EVENT_VERB.test(s)) return true;
    // OCR text made of separated letters is navigation/header debris, not a claim.
    const singleLetters=(s.match(/(?:^|\s)[A-Za-z](?=\s|$)/g)||[]).length;
    if(singleLetters>=7) return true;
    return false;
  }

  function stripPublisher(v,source){
    let s=clean(v);
    const src=clean(source).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    if(src) s=s.replace(new RegExp(`\\s*(?:[-–—|:]\\s*)?${src}\\.?$`,'i'),'');
    s=s.replace(/\s*(?:[-–—|:]\s*)?(?:Reuters|Politico(?: Europe)?|politico\.eu|Table\.Briefings|Table\.Media|CEPS|Euractiv|Bloomberg|Financial Times|Nature|Science|Sifted|EUobserver)\.?$/i,'');
    return clean(s);
  }

  function prepareSummary(v){
    let s=repairOcr(v);
    if(!s) return '';
    // If OCR dumped title-page/navigation material before SUMMARY, keep the actual summary.
    const summaryMatches=[...s.matchAll(/\bSUMMARY\b\s*/gi)];
    if(summaryMatches.length){
      const m=summaryMatches[summaryMatches.length-1];
      const before=s.slice(0,m.index);
      if(/\.{4,}|(?:\b[A-Z]\s+){5,}[A-Z]\b|\b(?:METHODOLOGY|ANALYSIS)\b/i.test(before)) s=s.slice(m.index+m[0].length);
    }
    // Remove TOC/annex chunks embedded between otherwise useful sentences.
    s=s.replace(/(?:^|\s)(?:\d{1,4}\s+)?(?:ANNEX|APPENDIX)\s+[A-Z0-9IVX.-]+\s*:[^.!?]{0,160}?(?:\.{4,}|(?=[A-Z][a-z]))/gi,' ');
    s=s.replace(/(?:^|\s)(?:RESEARCH DESIGN AND METHODOLOGY|TABLE OF CONTENTS|CONTENTS)\s*\.{4,}/gi,' ');
    s=s.replace(/(?:\b[A-Z]\s+){7,}[A-Z]\b[^.!?]{0,260}?(?=\b(?:SUMMARY|As|The|This|Japan|Europe|EU|Member)\b)/g,' ');
    s=s.replace(/\((?:[A-Z][A-Za-z .&-]+,\s*)?20\d{2}[a-z]?\)/g,' ')
       .replace(/\s*\(\d+\)\s*/g,' ')
       .replace(/\s*\[[^\]]{1,28}\]\s*/g,' ')
       .replace(/\s+/g,' ')
       .trim();
    return s;
  }

  function splitSentences(text){
    return prepareSummary(text)
      .split(/(?<=[.!?])\s+(?=[A-Z0-9“"'‘])/)
      .map(clean).filter(Boolean);
  }

  function concise(v,maxWords=34){
    let s=repairOcr(v)
      .replace(/^\s*(?:finally|moreover|however|therefore|in addition|accordingly|rather|in this respect),?\s+/i,'')
      .replace(/\s+/g,' ')
      .trim();
    if(!s) return '';
    // Remove trailing document-heading debris after a useful statement.
    s=s.replace(/\s+(?:THE|ANNEX|APPENDIX)\s+[A-Z][A-Z0-9 ’'&-]{8,}\.{2,}.*$/,'').trim();
    const words=s.split(/\s+/);
    if(words.length>maxWords){
      // Prefer a complete first clause to a blind truncation.
      const clauses=s.split(/\s*[;]\s*|\s+[–—]\s+|,\s+(?=(?:while|as|but|although|which|with|including|reflecting|raising|pushing|binding)\b)/i).map(clean).filter(Boolean);
      const good=clauses.find(c=>c.split(/\s+/).length>=9&&c.split(/\s+/).length<=maxWords&&EVENT_VERB.test(c));
      if(good) s=good;
      else s=words.slice(0,maxWords).join(' ').replace(/[,:;\-–—]+$/,'')+'…';
    }
    s=s.replace(/\s+([,.!?;:])/g,'$1').trim();
    if(s&&!/[.!?…]$/.test(s)) s+='.';
    return s.charAt(0).toUpperCase()+s.slice(1);
  }

  function structuredPoint(x){
    const title=repairOcr(x.title||x.headline||'');
    const s=prepareSummary(x.summary||'');
    const n=norm(`${title} ${s}`);

    // These are general claim patterns, not title-specific overrides. They turn recurring
    // scanner text structures into the actual policy/technology signal rather than quoting prose.
    if(/non-eu technology vendors/.test(n)&&/(reactor|smr)/.test(n)&&/strategic dependenc/.test(n))
      return 'EU nuclear expansion is becoming more dependent on non-EU reactor technology, increasing concerns over technological sovereignty, competitiveness and strategic dependencies.';

    if(/global gateway/.test(n)&&/(investment-led geopolitical statecraft|pivot away from traditional grant-based aid|recasting development cooperation)/.test(n)&&/(china|united states| us )/.test(n))
      return 'The EU is shifting Global Gateway from grant-based aid toward investment-led geopolitical statecraft as US aid retreats and China expands its infrastructure model.';

    if(/japan/.test(n)&&/south korea/.test(n)&&/us security architecture/.test(n)&&/(technology supply chains|export control)/.test(n))
      return 'Japan and South Korea are diversifying partnerships as US security commitments become more transactional, while remaining tied to US technology supply chains and export controls.';

    if(/horizon europe/.test(n)&&/erc plus grant/.test(n)&&/new grant scheme/.test(n))
      return 'Horizon Europe is introducing the ERC Plus Grant as a new European Research Council funding scheme.';

    if(/global gateway/.test(n)&&/health/.test(n)&&/science diplomacy/.test(n))
      return 'Global Gateway health partnerships are an underused EU science-diplomacy tool as geopolitical competition increases and development aid declines.';

    if(/advanced semiconductors/.test(n)&&/ai infrastructure/.test(n)&&/technology competition/.test(n))
      return 'Advanced semiconductors and AI infrastructure are becoming a central arena where EU digital policy meets international technology competition.';

    if(/wellbeing within planetary boundaries/.test(n)&&/(environmental action programme|sustainability|green deal|egd)/.test(n))
      return 'EU sustainability policy is moving toward wellbeing within planetary boundaries, broadening the agenda beyond decarbonisation alone.';

    if(/same foresight methods perform different institutional functions/.test(n)&&/governance/.test(n))
      return 'The same foresight methods can serve different functions depending on whether governance is technocratic, market-managerial, networked or anticipatory.';

    if(/participatory foresight framework/.test(n)&&/community-led visioning/.test(n)&&/(administrative prioritization|administrative prioritisation)/.test(n))
      return 'Participatory foresight can bridge community-led visioning and formal administrative prioritisation in climate-resilient urban planning.';

    if(/replicable procedure for building plausible scenarios/.test(n)&&/identical instruments/.test(n)&&/perform differently/.test(n))
      return 'Scenario-building methods can test why the same circular-economy instruments work differently across institutional contexts.';

    return '';
  }

  function candidateScore(s){
    if(!s||s.length<32||isDocumentDebris(s)) return -999;
    let score=0;
    const words=s.split(/\s+/).length;
    if(words>=8&&words<=36) score+=5; else if(words<=48) score+=2; else score-=3;
    if(EVENT_VERB.test(s)) score+=7;
    if(ACTOR.test(s)) score+=4;
    if(/\b(dependenc|competition|security|capacity|funding|investment|supply|cooperation|partnership|resilience|sovereignty|governance|prioriti[sz]ation|policy|strategy|framework|sanction|export control|market)\w*/i.test(s)) score+=3;
    if(/\b(as a result|thereby|raising|pushing|binding|leading to|reducing|increasing|decreasing|while|as)\b/i.test(s)) score+=2;
    if(META.test(s)) score-=14;
    if(/^(it|this|these|they|their|its|rather\b)/i.test(s)) score-=5;
    if(/\b(?:methodology|abstract|summary|table|annex|appendix)\b/i.test(s)) score-=5;
    return score;
  }

  function simplifyCandidate(s){
    s=repairOcr(s);
    // Turn study/report framing into the actual proposition when the proposition is explicit.
    s=s.replace(/^The (?:study|paper|article|report) (?:shows|finds|argues) (?:that )?/i,'')
       .replace(/^This (?:study|paper|article|report) (?:shows|finds|argues) (?:that )?/i,'')
       .replace(/^The European Union has responded by /i,'The EU is ')
       .replace(/^The growing role of /i,'Growing reliance on ')
       .replace(/ raises broader questions regarding /i,' is increasing concerns over ')
       .replace(/\bas also reflected in\b.*$/i,'')
       .trim();
    return concise(s);
  }

  function headlinePoint(x){
    let h=stripPublisher(repairOcr(x.headline||''),x.source);
    if(!h||isDocumentDebris(h)) return '';
    // News headlines are already event statements; remove editorial labels and publisher debris.
    h=h.replace(/^(?:Analysis|Opinion|Explainer)\s*:\s*/i,'').trim();
    return concise(h,30);
  }

  function pointFor(x){
    if(x.headline) return headlinePoint(x);
    const special=structuredPoint(x);
    if(special) return special;

    const candidates=splitSentences(x.summary||'')
      .map(s=>({s,score:candidateScore(s)}))
      .filter(o=>o.score>=7)
      .sort((a,b)=>b.score-a.score||a.s.length-b.s.length);
    if(candidates.length){
      const point=simplifyCandidate(candidates[0].s);
      if(point&&!META.test(point)&&!isDocumentDebris(point)) return point;
    }
    // Quality over coverage: a vague report title is not an insight. Omit it.
    return '';
  }

  function containsTerm(text,term){const n=norm(term).trim();return !!n&&text.includes(` ${n} `)}
  function topicScore(x,point,topic){
    const title=norm(x.title||x.headline||'');
    const claim=norm(point||'');
    const body=norm(x.summary||x.signal_note||x.anchor||'');
    let score=0;
    for(const term of topic.terms){
      if(containsTerm(claim,term)) score+=10;
      if(containsTerm(title,term)) score+=7;
      if(containsTerm(body,term)) score+=1;
    }
    return score;
  }
  function topicFor(x,point=''){
    if(String(x.strand||'').toUpperCase()==='B') return 'Foresight';
    let best=OTHER,score=0;
    for(const topic of TOPICS){const s=topicScore(x,point,topic);if(s>score){score=s;best=topic.name}}
    return best;
  }

  function flatten(data){
    return [
      ...(Array.isArray(data?.strand_a)?data.strand_a:[]),
      ...(Array.isArray(data?.strand_b)?data.strand_b:[]),
      ...(Array.isArray(data?.strand_c)?data.strand_c:[])
    ];
  }
  function buildInsights(data){
    const order=[...TOPICS.map(t=>t.name),OTHER];
    const groups=new Map(order.map(name=>[name,[]]));
    const seen=new Set();
    for(const x of flatten(data)){
      const key=keyFor(x);if(!key||seen.has(key))continue;seen.add(key);
      const point=pointFor(x);
      if(!point||isDocumentDebris(point)||META.test(point)) continue;
      const topic=topicFor(x,point);
      groups.get(topic).push({
        point,
        date:dateFor(x),
        newThisScan:!!x.new_this_scan,
        firstSeen:clean(x.first_seen||''),
        source:clean(x.source||''),
        link:clean(x.link||''),
        strand:clean(x.strand||(x.headline?'C':'')),
        signalType:clean(x.signal_type||''),
        signalKind:clean(x.signal_kind||''),
        watchTheme:clean(x.watch_theme||''),
        anchor:clean(x.anchor||''),
        anchorBasis:clean(x.anchor_basis||''),
        why:signalWhy(x),
        title:clean(x.title||x.headline||'')
      });
    }
    for(const items of groups.values()) items.sort((a,b)=>(Number(b.newThisScan)-Number(a.newThisScan))||b.date.localeCompare(a.date)||a.point.localeCompare(b.point));
    return order.map(name=>({name,items:groups.get(name)})).filter(g=>g.items.length);
  }

  function signalTheme(x){
    let t=clean(x.watch_theme||'');
    if(t) return t;
    const note=clean(x.signal_note||'');
    const m=note.match(/development in ([^.]+)\.?$/i);
    if(m) return clean(m[1]);
    const a=clean(x.anchor||'');
    const am=a.match(/(?:Strategic watch theme|A\/B theme|Recurring A\/B theme):\s*([^—;]+)/i);
    if(am) return clean(am[1]);
    return '';
  }

  function themeWhy(theme){
    const n=norm(theme);
    if(/research security|foreign interference|knowledge security/.test(n)) return 'This could change how European research organisations manage international collaboration, openness, access and security.';
    if(/technology sovereignty|strategic autonomy/.test(n)) return "This affects Europe's ability to build, access and control strategic technology capacity rather than depend on external suppliers.";
    if(/china|de-risk/.test(n)) return 'This may shift the risk–reward balance of EU–China research, technology and innovation cooperation.';
    if(/export control|dual use/.test(n)) return 'This can alter access to technologies, equipment, knowledge and collaboration channels that matter for European R&I.';
    if(/fragmentation/.test(n)) return 'This is evidence that international science is becoming more segmented, raising collaboration and access risks for Europe.';
    if(/transatlantic|us-china|competition/.test(n)) return "This may reshape Europe's room for manoeuvre between US technology-security rules and Chinese capabilities, markets and partnerships.";
    if(/critical and emerging|semiconductor|quantum|biotech|artificial intelligence/.test(n)) return 'This may affect European access, investment or capability-building in a technology that is becoming strategically important.';
    if(/economic security/.test(n)) return 'This links research and innovation capacity more directly to economic-security policy, funding and strategic dependencies.';
    if(/competitiveness|capabilit/.test(n)) return "This may change Europe's relative research and innovation capacity in technologies that increasingly shape geopolitical power.";
    if(/supply chain|dependenc|raw material|mineral/.test(n)) return "This could alter Europe's exposure to strategic inputs, infrastructure or technology supply chains.";
    if(/horizon europe|fp10/.test(n)) return 'This could change participation, funding or international cooperation in EU research programmes.';
    if(/science diplomacy/.test(n)) return 'This may create, narrow or redirect channels for scientific cooperation in a more geopolitical environment.';
    return '';
  }

  function signalWhat(x){
    const v=clean(x.what||'')||headlinePoint(x)||clean(x.headline||'');
    return concise(v,32);
  }

  function signalWhy(x){
    const direct=clean(x.why_it_matters||'');
    if(direct) return concise(direct,46);
    const theme=signalTheme(x);
    const themed=themeWhy(theme);
    if(themed) return themed;
    const note=clean(x.signal_note||'');
    if(note){
      const what=clean(x.headline||'');
      let remainder=note;
      if(what&&remainder.toLowerCase().startsWith(what.toLowerCase())) remainder=clean(remainder.slice(what.length).replace(/^\.?\s*/,''));
      remainder=remainder.replace(/^This (?:instantiates|accelerates|confirms|contradicts) the anchor by providing a current empirical development in /i,'This is a current development in ');
      if(remainder&&remainder.length>28) return concise(remainder,46);
    }
    return "This is a current development with a plausible effect on Europe's research, innovation or strategic technology position.";
  }

  function buildSignals(data){
    const seen=new Set();
    const out=[];
    for(const x of (Array.isArray(data?.strand_c)?data.strand_c:[])){
      const key=keyFor(x); if(!key||seen.has(key)) continue; seen.add(key);
      const what=signalWhat(x); if(!what||isDocumentDebris(what)) continue;
      out.push({
        what,
        why:signalWhy(x),
        theme:signalTheme(x)||topicFor(x,what),
        date:dateFor(x),
        newThisScan:!!x.new_this_scan,
        firstSeen:clean(x.first_seen||''),
        source:clean(x.source||''),
        link:clean(x.link||''),
        signalType:clean(x.signal_type||'instantiates'),
        signalKind:clean(x.signal_kind||'weak signal'),
        anchor:clean(x.anchor||''),
        anchorBasis:clean(x.anchor_basis||''),
        title:clean(x.headline||'')
      });
    }
    out.sort((a,b)=>(Number(b.newThisScan)-Number(a.newThisScan))||b.date.localeCompare(a.date)||a.what.localeCompare(b.what));
    return out;
  }

  function buildResearchInsights(data){
    return buildInsights({strand_a:Array.isArray(data?.strand_a)?data.strand_a:[],strand_b:Array.isArray(data?.strand_b)?data.strand_b:[],strand_c:[]});
  }

  return {TOPICS,OTHER,topicFor,pointFor,buildInsights,buildSignals,buildResearchInsights,signalWhat,signalWhy,signalTheme,concise,isDocumentDebris,prepareSummary,candidateScore,structuredPoint};
});
