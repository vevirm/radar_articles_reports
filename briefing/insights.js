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
  const VAGUE_START=/^(?:(?:and|or|but|nor|yet|so)\b|(?:this|these|those|it|they|such)\b|(?:what|why|how|where|when|who)\b|the (?:study|paper|article|report|analysis|research|results?|finding|findings|development|developments|change|changes|trend|trends|issue|issues)\b|(?:broader|wider) implications?\b)/i;
  const MAX_POINT_CHARS=120;
  const DEPENDENT_START=/^(?:and\b|or\b|but\b|nor\b|yet\b|so\b|to support (?:this|these)|with\b|since\b|because\b|while\b|although\b|building on\b|drawing on\b|based on\b)/i;
  const POINT_PREDICATE=/\b(?:is|are|was|were|has|have|had|can|could|may|might|will|would|should|must|show|find|argue|conclude|reveal|indicate|suggest|highlight|shape|treat|use|map|face|gain|lose|create|make|help|drive|constrain|allow|remain|become|depend|rely|change|shift|link|raise|cut|add|limit|fund|launch|open|close|adopt|propose|plan|build|develop|deploy|establish|agree|sign|join|withdraw|target|support|secure|protect|screen|coordinate|compete|reform|amend|extend|approve|reject|connect|urge|struggle|perform|serve|stress|need|trail|offer|respond|pivot|introduce|expand|reduce|increase|strengthen|weaken|move|pull|push|balance|tighten|reset|outpace|concentrat|lag|rank|improv|undermin|accelerat|erod|diversif|retain|attract|exclude|require|steer|reshape|reward|leave|equip|prepare|align|integrat|harmoni[sz]|reconfigur)\w*\b/i;

  function clean(v){return String(v??'').replace(/\u00ad/g,'').replace(/[ \t]+/g,' ').replace(/\s*\n\s*/g,' ').trim()}
  function norm(v){return ` ${clean(v).toLowerCase().replace(/[–—]/g,'-').replace(/[^a-z0-9+.#/&-]+/g,' ').replace(/\s+/g,' ').trim()} `}
  function likelyEnglish(v){
    const s=clean(v); if(!s) return false;
    // Display guard, not corpus classification: allow technical names/acronyms but reject
    // obvious non-English prose before it reaches cards.
    if(/[А-Яа-яІіЇїЄєҐґЁё一-龯ぁ-んァ-ン가-힣]/.test(s)) return false;
    const n=` ${s.toLowerCase().replace(/[^a-zà-ž]+/g,' ').replace(/\s+/g,' ').trim()} `;
    const english=(n.match(/\b(the|a|an|and|or|of|to|in|for|on|with|as|is|are|was|were|be|by|from|that|this|its|eu|europe|european)\b/g)||[]).length;
    const foreign=(n.match(/\b(und|der|die|das|des|den|ein|eine|et|les|des|une|un|dans|pour|avec|sur|del|della|delle|gli|che|con|per|los|las|una|para|con|sobre|y|de|la|el|van|het|een|voor|met|și|sau|din|pentru|cu|w|oraz|dla|jest|na)\b/g)||[]).length;
    const words=s.split(/\s+/).filter(Boolean).length;
    if(words<5) return true;
    return english>=2 || foreign<=1;
  }
  function completeCoreMessage(v){
    const s=repairOcr(v).replace(/\s+/g,' ').trim();
    if(!s || /…|\.\.\./.test(s) || isDocumentDebris(s) || !likelyEnglish(s)) return '';
    if(s.split(/\s+/).length<5) return '';
    return readerPoint(s);
  }
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
      // Never publish a chopped sentence. Prefer a complete proposition-sized clause;
      // if none exists, reject this candidate and let pointFor try another sentence.
      const clauses=s.split(/\s*[;]\s*|\s+[–—]\s+|,\s+(?=(?:while|as|but|although|which|with|including|reflecting|raising|pushing|binding|and)\b)/i).map(clean).filter(Boolean);
      const good=clauses.find(c=>c.split(/\s+/).length>=9&&c.split(/\s+/).length<=maxWords&&EVENT_VERB.test(c));
      const complete=good||clauses.find(c=>c.split(/\s+/).length>=9&&c.split(/\s+/).length<=maxWords&&!META.test(c));
      if(complete) s=complete;
      else return '';
    }
    s=s.replace(/\s+([,.!?;:])/g,'$1').trim();
    if(s&&!/[.!?…]$/.test(s)) s+='.';
    return s.charAt(0).toUpperCase()+s.slice(1);
  }


  function readerPoint(v,maxChars=MAX_POINT_CHARS){
    let s=repairOcr(v)
      .replace(/^\s*(?:finally|moreover|however|therefore|in addition|accordingly|rather|in this respect|on the other hand|in conclusion),?\s+/i,'')
      .replace(/\s+/g,' ')
      .trim();
    if(!s||/…|\.\.\./.test(s)) return '';

    const shrink=q=>repairOcr(q)
      .replace(/\bthe European Union\b/gi,'the EU')
      .replace(/\bEuropean Union\b/gi,'EU')
      .replace(/\bUnited States\b/gi,'US')
      .replace(/\bartificial intelligence\b/gi,'AI')
      .replace(/\bresearch and innovation\b/gi,'R&I')
      .replace(/\btechnological sovereignty\b/gi,'tech sovereignty')
      .replace(/\bstrategic autonomy\b/gi,'autonomy')
      .replace(/\bin order to\b/gi,'to')
      .replace(/\bwith a view to\b/gi,'to')
      .replace(/\bcomparatively\b/gi,'')
      .replace(/\bparticularly\b/gi,'')
      .replace(/\s+/g,' ')
      .trim();

    const finish=q=>{
      q=shrink(q).replace(/\s+([,.!?;:])/g,'$1').trim();
      if(!q||VAGUE_START.test(q)||DEPENDENT_START.test(q)||/\?$/.test(q)||/\b(?:broader|wider) implications?\b/i.test(q)||q.length>maxChars||isDocumentDebris(q)||META.test(q)) return '';
      if(!POINT_PREDICATE.test(q)) return '';
      q=q.replace(/[;:,]+$/,'').trim();
      if(!/[.!?]$/.test(q)) q+='.';
      if(q.length>maxChars) return '';
      return q.charAt(0).toUpperCase()+q.slice(1);
    };

    const direct=finish(s); if(direct) return direct;
    const sentenceList=splitSentences(s);
    for(const sentence of sentenceList){const q=finish(sentence);if(q)return q;}

    const pool=[s,...sentenceList];
    for(const candidate of pool){
      const q=shrink(candidate);
      const clauses=q.split(/\s*[;]\s*|\s+[–—]\s+|,\s+(?=(?:while|but|although|which|with|including|reflecting|raising|pushing|binding|and|as|increasing|reducing|broadening|expanding|creating|leaving|showing|giving|making|providing|allowing|helping|limiting|keeping|turning)\b)|\s+(?=without\b)|\s+(?=as\b)/i).map(clean).filter(Boolean);
      for(const clause of clauses){
        if(clause.split(/\s+/).length<6) continue;
        const done=finish(clause); if(done) return done;
      }
    }
    return '';
  }

  function structuredPoint(x){
    const title=repairOcr(x.title||x.headline||'');
    const s=prepareSummary(x.summary||'');
    const n=norm(`${title} ${s} ${x.core_message||''}`);

    // Reader-first rewrites requested for dense recurring evidence. These use only facts
    // already present in the source record; bibliography and original summary remain untouched.
    if(/e-hryvnia/.test(n)&&/bahamas/.test(n)&&/china/.test(n)&&/cyber resilience/.test(n))
      return "The paper compares central-bank digital money in China, the EU and the Bahamas. Ukraine's e-hryvnia puts unusual weight on transparency and cyber resilience.";

    if(/global cybersecurity governance/.test(n)&&/african union/.test(n)&&/(multistakeholder|gfce|igf)/.test(n))
      return 'Regional blocs such as the EU and African Union can move toward shared cyber rules, while open forums that include governments, industry and civil society help countries build the capacity to apply them.';

    if(/ai4s/.test(n)&&/china/.test(n)&&/japan/.test(n)&&/united kingdom/.test(n))
      return 'The US, China, the EU, the UK and Japan now treat AI for science in much the same way: as a tool to break through hard problems, produce knowledge faster and stay competitive.';

    if(/mapping of technology specialisation/.test(n)&&/venture capital/.test(n)&&/patent/.test(n))
      return 'Patents, research papers and venture-capital deals from 2010 to 2025 show where the EU and its partners specialise: what they invent, what they research and where new companies take root.';

    if(/no one builds alone/.test(n)&&/open hardware/.test(n)&&/india/.test(n)&&/ai chips?/.test(n))
      return 'Open hardware could give Europe and India more control over AI-chip technology without either side having to build the whole stack alone.';

    // Explicit research-talent loss is itself the substantive Frontier finding.  Prefer
    // the sentence that states the loss/brain-drain condition over a nearby generic
    // investment or policy sentence; otherwise a report can be admitted correctly but
    // appear in Knowledge/A while Knowledge/D stays falsely empty.
    if(/brain drain|researcher outflow|research talent outflow|scientific talent outflow|talent loss/.test(n)
       && /research|researcher|scientist|academic|science/.test(n)
       && /europe|european union|\beu\b|member state/.test(n)){
      const talentSentence=splitSentences(s).find(sent=>{
        const q=norm(`${title} ${sent}`);
        return /brain drain|researcher outflow|research talent outflow|scientific talent outflow|talent loss/.test(q)
          && /research|researcher|scientist|academic|science/.test(q);
      });
      if(talentSentence) return concise(talentSentence,42);
    }

    // These are general claim patterns, not title-specific overrides. They turn recurring
    // scanner text structures into the actual policy/technology signal rather than quoting prose.
    if(/non-eu technology vendors/.test(n)&&/(reactor|smr)/.test(n)&&/strategic dependenc/.test(n))
      return 'EU nuclear expansion is becoming more dependent on non-EU reactor technology.';

    if(/global gateway/.test(n)&&/(investment-led geopolitical statecraft|pivot away from traditional grant-based aid|recasting development cooperation)/.test(n)&&/(china|united states| us )/.test(n))
      return 'The EU is shifting Global Gateway from grants toward investment-led geopolitical statecraft.';

    if(/japan/.test(n)&&/south korea/.test(n)&&/us security architecture/.test(n)&&/(technology supply chains|export control)/.test(n))
      return 'Japan and South Korea are diversifying partnerships as US security commitments become more transactional, while remaining tied to US technology supply chains and export controls.';

    if(/horizon europe/.test(n)&&/erc plus grant/.test(n)&&/new grant scheme/.test(n))
      return 'Horizon Europe is introducing the ERC Plus Grant as a new European Research Council funding scheme.';

    if(/global gateway/.test(n)&&/health/.test(n)&&/science diplomacy/.test(n))
      return 'Global Gateway health partnerships remain underused as an EU science-diplomacy tool.';

    if(/advanced semiconductors/.test(n)&&/ai infrastructure/.test(n)&&/technology competition/.test(n))
      return 'Advanced chips and AI infrastructure are a key arena for EU technology competition.';

    if(/wellbeing within planetary boundaries/.test(n)&&/(environmental action programme|sustainability|green deal|egd)/.test(n))
      return 'EU sustainability policy is moving toward wellbeing within planetary boundaries.';

    if(/same foresight methods perform different institutional functions/.test(n)&&/governance/.test(n))
      return 'Foresight methods serve different functions under different governance models.';

    if(/participatory foresight framework/.test(n)&&/community-led visioning/.test(n)&&/(administrative prioritization|administrative prioritisation)/.test(n))
      return 'Participatory foresight can connect local climate visions with formal city planning.';

    if(/replicable procedure for building plausible scenarios/.test(n)&&/identical instruments/.test(n)&&/perform differently/.test(n))
      return 'Scenario methods can test why the same circular-economy tools work differently across institutions.';

    // Reader-first rewrites for recurring evidence structures where the abstract's academic
    // phrasing obscures the actual signal.
    if(/bulgaria/.test(n)&&/critical raw material|crma/.test(n)&&/first strategic selection|strategic selection/.test(n))
      return "The EU's first CRMA list includes no Bulgarian projects — outdated data, slow permits and low trust keep it out.";

    if(/green protectionism|green trade agenda|trade defence instruments/.test(n)&&/(cbam|deforestation regulation|foreign subsidies|anti-dumping)/.test(n))
      return 'The EU says its new trade rules protect the climate. Trading partners say they protect EU industry.';

    if(/digital identity/.test(n)&&/artificial intelligence act|ai act/.test(n)&&/convergence/.test(n))
      return 'EU AI rules are converging with digital-identity governance, expanding responsibilities for platforms and regulators.';

    if(/geoeconomic exposure/.test(n)&&/export depend/.test(n)&&/industrial policy/.test(n))
      return "Europe's industrial-policy risk is not only import dependence — export dependence on US and Chinese markets also constrains EU choices.";

    if(/waste material trading|waste trade/.test(n)&&/r&d intensity/.test(n)&&/ai innovation/.test(n))
      return 'EU waste-trade evidence links stronger R&D intensity to better circular-economy performance; AI investment does not yet show the same effect.';

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
    s=s.replace(/^(?:First|Second|Third|Fourth|Finally),?\s+/i,'')
       .replace(/^The (?:study|paper|article|report) (?:shows|finds|argues|demonstrates|identifies|reveals|indicates) (?:that )?/i,'')
       .replace(/^This (?:study|paper|article|report) (?:shows|finds|argues|demonstrates|identifies|reveals|indicates) (?:that )?/i,'')
       .replace(/^The European Union has responded by /i,'The EU is ')
       .replace(/^The growing role of /i,'Growing reliance on ')
       .replace(/ raises broader questions regarding /i,' is increasing concerns over ')
       .replace(/\bThe European Union\s*\(EU\)/g,'The EU')
       .replace(/\bthe European Union\s*\(EU\)/g,'the EU')
       .replace(/\bEuropean Union\s*\(EU\)/g,'EU')
       .replace(/\bThe European Union\b/g,'The EU')
       .replace(/\bthe European Union\b/g,'the EU')
       .replace(/\bUnited States\s*\(US\)/g,'US')
       .replace(/\bUnited States\b/g,'US')
       .replace(/\bin order to\b/gi,'to')
       .replace(/\bwith a view to\b/gi,'to')
       .replace(/\bas also reflected in\b.*$/i,'')
       .trim();
    return concise(s);
  }

  function plainLanguagePoint(x,value){
    let s=repairOcr(value);
    if(!s) return readerPoint('');
    const context=norm(`${x?.title||x?.headline||''} ${x?.summary||''} ${x?.core_message||''} ${s}`);

    // Reader-first rewrites for recurring dense source language. The original title,
    // Source-specific anaphora is rewritten with an explicit actor before display.
    if(/(?:artificial intelligence act|eu ai act|ai act)/.test(context)&&/regulatory/.test(context)&&/ethical/.test(context))
      return readerPoint('The EU AI Act creates a risk-based governance framework for AI systems.');

    // abstract, authors, source and date remain unchanged in the detail layer.
    if(/ireland/.test(context)&&/pressure to diversify/.test(context)&&/current us administration/.test(context)&&/geopolitical instability/.test(context))
      return "US–China tensions and US uncertainty are narrowing Ireland's room for science-tech cooperation with China.";

    if(/semiconductor export controls/.test(context)&&/economic interests toward china/.test(context)&&/security relations with the united states/.test(context))
      return 'EU chip controls protect technology while Europe balances China trade and US security ties.';

    if(/copernican academy/.test(context)&&/collegium intermarium/.test(context)&&/intermarium/.test(context)&&/neo-nationalist/.test(context))
      return 'Polish research policy has been pulled into geopolitical and neo-nationalist projects.';

    if(/diffusion of dual-use technologies/.test(context)&&/cross-border knowledge transfer/.test(context)&&/dependencies in strategically important supply chains/.test(context))
      return 'EU research-security risks include dual-use spread, knowledge leakage and critical-supply dependence.';

    if(/e-hryvnia/.test(context)&&/bahamas/.test(context)&&/china/.test(context)&&/cyber resili/.test(context))
      return "The paper compares central-bank digital money in China, the EU and the Bahamas. Ukraine's e-hryvnia puts unusual weight on transparency and cyber resilience.";

    if(/global cybersecurity governance/.test(context)&&/african union/.test(context)&&/(multistakeholder|gfce|igf)/.test(context))
      return 'Regional blocs such as the EU and African Union can move toward shared cyber rules, while open forums that include governments, industry and civil society help countries build the capacity to apply them.';

    if(/ai4s/.test(context)&&/china/.test(context)&&/japan/.test(context)&&/(united kingdom| uk )/.test(` ${context} `))
      return 'The US, China, the EU, the UK and Japan now treat AI for science in much the same way: as a tool to break through hard problems, produce knowledge faster and stay competitive.';

    if(/mapping of technology specialisation/.test(context)&&/venture capital/.test(context)&&/patent/.test(context))
      return 'Patents, research papers and venture-capital deals from 2010 to 2025 show where the EU and its partners specialise: what they invent, what they research and where new companies take root.';

    if(/no one builds alone/.test(context)&&/open hardware/.test(context)&&/india/.test(context)&&/ai chips?/.test(context))
      return 'Open hardware could give Europe and India more control over AI-chip technology without either side having to build the whole stack alone.';

    // General cleanup: remove list/academic scaffolding and prefer short verbs.
    s=s.replace(/^(?:First|Second|Third|Fourth|Finally),?\s*/i,'')
       .replace(/^(?:Focusing on|Drawing on|Drawing upon|Based on|Using)\b[^,]{0,220},\s*(?=(?:the|this) (?:study|paper|article|report)\b)/i,'')
       .replace(/^(?:the|this) (study|paper|article|report) demonstrates how\s+/i,'The $1 shows how ')
       .replace(/^(?:the|this) (study|paper|article|report) demonstrates that\s+/i,'The $1 shows that ')
       .replace(/\bdemonstrates\b/gi,'shows')
       .replace(/\binstrumentali[sz]ed to advance\b/gi,'used to support')
       .replace(/\binstrumentali[sz]ed\b/gi,'used')
       .replace(/\bsemiconductor export controls\b/gi,'chip export controls')
       .replace(/\bsecurity relations\b/gi,'security ties')
       .replace(/\beconomic interests\b/gi,'trade interests')
       .replace(/\bgeopolitical instability\b/gi,'global instability')
       .replace(/\bstrategically important supply chains\b/gi,'critical supply chains')
       .replace(/\bthe emergence of dependencies in\b/gi,'dependence on')
       .replace(/\bthe diffusion of dual-use technologies\b/gi,'dual-use tech spreading')
       .replace(/\bcross-border knowledge transfer\b/gi,'knowledge moving abroad')
       .replace(/\bwith a view to\b/gi,'to')
       .replace(/\s+/g,' ')
       .trim();
    return readerPoint(s)||readerPoint(value)||'';
  }

  function headlinePoint(x){
    let h=stripPublisher(repairOcr(x.headline||''),x.source);
    if(!h||isDocumentDebris(h)) return '';
    // News headlines are already event statements; remove editorial labels and publisher debris.
    h=h.replace(/^(?:Analysis|Opinion|Explainer)\s*:\s*/i,'').trim();
    return readerPoint(h);
  }


  function fallbackPoint(x){
    const text=norm(`${x?.title||x?.headline||''} ${x?.summary||''} ${x?.relevance_note||''} ${x?.watch_theme||''}`);
    const b=String(x?.strand||'').toUpperCase()==='B';
    if(b){
      if(/horizon scan/.test(text)) return 'Horizon scanning can identify emerging strategic risks before they become established trends.';
      if(/weak signal/.test(text)) return 'Weak-signal methods can detect early strategic change before it becomes an established trend.';
      if(/scenario/.test(text)) return 'Scenario methods can test how uncertain strategic futures may unfold for European R&I.';
      if(/backcasting/.test(text)) return 'Backcasting can connect long-term R&I futures with decisions made today.';
      return 'Foresight methods can test emerging strategic change around European R&I.';
    }
    const bridge=readerPoint(x?.external_eu_bridge||x?.bridge_sentence||'');
    if(bridge) return bridge;
    if(/strategic procurement/.test(text)&&/global europe/.test(text)) return 'EU procurement preferences can backfire when European firms face higher costs, security risks or deployment barriers.';
    if(/normal research trap/.test(text)||(/research trap/.test(text)&&/european union/.test(text))) return "The EU research system is smaller than China's and less efficient than the US system.";
    if(/paediatric care/.test(text)&&/cross-border collaboration/.test(text)) return 'EU-funded paediatric innovation networks expand cross-border health-technology collaboration.';
    if(/dual circulation/.test(text)&&/electric vehicle/.test(text)) return "China's dual-circulation strategy is increasing competitive pressure on Europe's EV industry.";
    if(/foreign policy identities/.test(text)&&/climate/.test(text)) return 'US climate messaging stresses competition; EU messaging stresses cooperation and shared responsibility.';
    if(/iderha|federated health data/.test(text)&&/european health data space/.test(text)) return 'IDERHA is building a pan-European health data space for medical research, AI and regulatory use.';
    if(/pv recycling|pv waste/.test(text)) return 'Europe, the US, China and India need stronger PV recycling capacity and more aligned rules.';
    if(/sme sustainable development/.test(text)&&/moldova/.test(text)) return 'Moldovan SMEs remain weakly integrated into EU-aligned value chains despite regulatory alignment.';
    if(/portugal.s productivity gap|productivity gap vis-a-vis/.test(text)) return 'European tech leaders trail global peers partly because Europe invests less in R&D and equity finance.';
    if(/ai implementation gap/.test(text)&&/(uae|egypt)/.test(text)) return 'AI audit gaps in the UAE and Egypt offer a comparison point for EU AI governance.';
    if(/future city hub/.test(text)&&/(jakarta|berlin)/.test(text)) return 'Berlin–Jakarta cooperation transferred technology to startups, but EU funding ended.';
    if(/agricultural market infrastructure/.test(text)&&/ukraine/.test(text)) return "Ukraine's wartime farm trade is shifting toward the EU as logistics and export infrastructure adapt.";
    if(/genetically modified organisms|gmo/.test(text)&&/agricultur/.test(text)) return 'EU GMO rules use process-based controls that differ from several non-EU regulatory models.';
    if(/ellis institute finland/.test(text)) return 'ELLIS Institute Finland activity may affect European AI capability-building.';
    if(/radio astronomy/.test(text)&&/africa/.test(text)) return 'African radio astronomy changes may affect EU research partnerships and infrastructure access.';
    if(/machine learning/.test(text)&&/ict infrastructure/.test(text)) return 'Machine learning can help map ICT infrastructure relevant to European capability and resilience.';
    if(/ai and democracy/.test(text)) return 'AI governance for democracy can shape European safeguards and institutional capacity.';
    if(/ireland/.test(text)&&/china/.test(text)&&/(science|technology|innovation)/.test(text)) return "US–China tensions and US uncertainty are narrowing Ireland's room for science-tech cooperation with China.";
    if(/fragmented europe/.test(text)&&/china/.test(text)) return 'European approaches to China remain fragmented despite shared de-risking and research-security concerns.';
    if(/polish universit/.test(text)&&/(neo-national|intermarium|geopolitical tensions)/.test(text)) return 'Polish research policy has been pulled into geopolitical and neo-nationalist projects.';
    if(/drone research/.test(text)&&/knowledge flows/.test(text)) return 'Drone research shows growing geopolitical gaps in output, citations and international knowledge flows.';
    if(/venture capital gap/.test(text)&&/high-growth firms/.test(text)) return "Europe's late-stage VC gap increases reliance on non-EU investors and raises relocation risks.";
    if(/mapping of technology specialisation/.test(text)&&/venture capital/.test(text)) return 'Patents, papers and venture capital show where the EU and global partners specialise.';
    if(/growth model/.test(text)&&/strategic capitalism/.test(text)) return 'External technology and infrastructure dependence makes the EU growth model vulnerable to geoeconomic competition.';
    if(/india-eu free trade|india eu free trade/.test(text)&&/medical device/.test(text)) return 'The India–EU trade deal may speed medical-device approvals and encourage joint technology ventures.';
    if(/genoese migration/.test(text)&&/technology transfer/.test(text)) return 'Genoese migration helped transfer manufacturing know-how across the Spanish monarchy.';
    if(/bioeconomy/.test(text)&&/agricultural regions/.test(text)) return 'Bioeconomy models link R&D support, institutions and regional innovation capacity.';
    if(/three seas initiative/.test(text)&&/eurasian/.test(text)) return 'The Three Seas Initiative is framed as a Europe–Asia hinge in a more fragmented Eurasia.';
    if(/pharma/.test(text)&&/(mergers|acquisitions|m&a)/.test(text)) return 'European pharma M&A is driven partly by technological and geopolitical shifts.';
    if(/neoclassical realist/.test(text)&&/research program/.test(text)) return 'Neoclassical realism offers a structured guide for analysing contemporary geopolitical scenarios.';
    if(/biobank act/.test(text)&&/international collaboration/.test(text)) return 'Different biobank rules across Europe can help or hinder international health research.';
    if(/global gateway/.test(text)&&/health/.test(text)) return 'Global Gateway health partnerships remain underused as an EU science-diplomacy tool.';
    if(/defence industry/.test(text)&&/control/.test(text)) return 'European states use ownership and board rights to control strategically important defence firms.';
    if(/cbdc|central bank digital/.test(text)) return 'CBDCs can reshape state control over money and the technology of monetary systems.';
    if(/ai4s|ai for science/.test(text)) return 'The US, China, EU, UK and Japan treat AI for science as a tool for faster research and competitiveness.';
    if(/itu ai\/ml challenge/.test(text)||/application inference from packet flows/.test(text)) return 'ITU launched an AI/ML challenge on inferring applications from packet flows.';
    const title=readerPoint(x?.title||x?.headline||'');
    if(title&&EVENT_VERB.test(title)) return title;
    if(/research security|knowledge security|foreign interference/.test(text)) return 'Research-security pressure is changing how Europe protects knowledge while keeping science open.';
    if(/science diplomacy|scientific collaboration|research collaboration/.test(text)) return 'Geopolitical rivalry is changing Europe’s research partnerships and use of science diplomacy.';
    if(/brain drain|researcher mobility|research talent|scientific talent|research workforce/.test(text)) return 'Researcher mobility is becoming a strategic issue for Europe’s scientific capacity.';
    if(/horizon europe|fp10|framework programme/.test(text)) return 'Geopolitical pressure is reshaping EU research funding and international partnerships.';
    if(/semiconductor|chip/.test(text)) return 'Semiconductor dependence is constraining Europe’s technology choices and strategic autonomy.';
    if(/quantum/.test(text)) return 'Quantum capability is becoming part of Europe’s competition for technology security.';
    if(/artificial intelligence| ai /.test(text)&&/depend|investment|sovereign|security|compute/.test(text)) return 'AI capacity and dependence are becoming strategic issues for Europe’s technology position.';
    if(/advanced material|critical mineral|raw material|battery/.test(text)) return 'Critical raw materials shape Europe’s technology resilience and industrial autonomy.';
    if(/dual.?use|military|defen[cs]e/.test(text)&&/innovation|technology|research/.test(text)) return 'Security competition is pulling more European R&I toward dual-use priorities.';
    if(/digital sovereignty|digital strategy|cyber/.test(text)) return 'Digital and cyber policy is shaping Europe’s geopolitical and technology position.';
    if(/industrial policy|innovation ecosystem|competitiveness/.test(text)) return 'Geopolitical competition is pushing Europe to link innovation policy more closely to resilience.';
    if(/supply chain|dependenc|strategic autonomy|sovereignty/.test(text)) return 'Strategic dependencies are changing Europe’s room for manoeuvre in research and technology.';
    return '';
  }

  function whyFor(x){
    // Why-it-matters text is derived from the individual record, not from a reusable topic label.
    // Prefer a source sentence or a faithful compressed clause that is distinct from the visible claim.
    const what=pointFor(x);
    const whatNorm=norm(what||'');
    const title=repairOcr(x?.title||x?.headline||'');
    const titleNorm=norm(title);
    const GENERIC_WHY=/^(?:AI capacity and dependence are becoming strategic issues|Geopolitical competition is pushing Europe|European access and investment may shift|Geopolitical rivalry is changing Europe|Foresight methods can test emerging strategic change|Research-security pressure is changing how Europe|Semiconductor dependence is constraining Europe|Security competition is pulling more European R&I|Geopolitical pressure is reshaping EU research funding|EU–China R&I cooperation may become narrower|Strategic dependencies are changing Europe|Digital and cyber policy is shaping Europe|Quantum capability is becoming part of Europe|Critical raw materials shape Europe|Current geopolitical change may alter Europe)/i;
    const SOURCE_SCAFFOLD=/\b(?:its EU relevance is classified|this may affect European access, investment or capability-building|this is new evidence that may strengthen|consult the linked publication|based on explicit EU\/European policy content|the item was admitted to Strand|source text available at scan time)\b/i;
    const BAD_START=/^(?:(?:this|these|those|it|they|such)\b|the (?:study|paper|article|report|analysis|research|results?|finding|findings|development|developments|change|changes|trend|trends|issue|issues|evidence)\b|(?:and|or|but|yet|so|as|amid|from|with|since|because|while|although|using|based on|drawing on|building on|could|may|might|would|will|can|must|should|has|have|had|is|are|was|were)\b)/i;
    const IMPACT=/\b(depend|reli|risk|expos|constrain|limit|restrict|delay|weaken|strengthen|increase|reduce|raise|lower|cost|capacity|capabilit|access|control|compet|collabor|cooperat|partner|fund|invest|scale|supply|security|sovereign|autonom|resilien|fragment|leak|transfer|mobility|talent|skill|adopt|deploy|coordina|standard|govern|regulat|market|production|manufactur|infrastructure|compute|knowledge|research|innovation|technology|science|trade|procurement|concentrat|underinvest|shortage|gap|scrutin|exclude|screen|protect)\w*/i;
    const SPECIFIC=/\b(EU|Europe|European|Horizon Europe|ERC|MSCA|China|Chinese|US|United States|Ukraine|Russia|India|Japan|NATO|AI|quantum|semiconductor|chip|cloud|compute|biotech|health|defen[cs]e|raw material|battery|researcher|university|firm|company|industry|infrastructure|funding|programme|regulation|directive|standard|science diplomacy|research security|knowledge security)\b/i;

    const direct=readerPoint(x?.why_it_matters||'');
    if(direct&&!GENERIC_WHY.test(direct)&&!SOURCE_SCAFFOLD.test(direct)&&!BAD_START.test(direct)) return direct;

    function compress(q){
      return repairOcr(q)
        .replace(/^Abstract\s*/i,'')
        .replace(/\bthe European Union\b/gi,'the EU')
        .replace(/\bEuropean Union\b/gi,'EU')
        .replace(/\bUnited States\b/gi,'US')
        .replace(/\bartificial intelligence\b/gi,'AI')
        .replace(/\bresearch and innovation\b/gi,'R&I')
        .replace(/\btechnological sovereignty\b/gi,'tech sovereignty')
        .replace(/\bstrategic autonomy\b/gi,'autonomy')
        .replace(/\bthe capability benchmark Europe must match\b/gi,'the benchmark Europe must match')
        .replace(/\bnumerous measures designed to limit or eliminate risks of\b/gi,'measures against')
        .replace(/\billicit technological theft\b/gi,'technology theft')
        .replace(/\bintensifying economic and geopolitical competition\b/gi,'geopolitical competition')
        .replace(/\bthe EU’s collective reliance\b/gi,'EU reliance')
        .replace(/\bthe EU's collective reliance\b/gi,'EU reliance')
        .replace(/\binternational scientific collaboration\b/gi,'scientific collaboration')
        .replace(/\binternational collaboration\b/gi,'collaboration')
        .replace(/\bEuropean businesses\b/gi,'European firms')
        .replace(/\bcivil aviation\b/gi,'aviation')
        .replace(/\bpharmaceuticals\/biotechnology\b/gi,'biotech')
        .replace(/\bthe final version of the EU AI Act\b/gi,'the EU AI Act')
        .replace(/\bthe final version of the EU Artificial Intelligence Act\b/gi,'the EU AI Act')
        .replace(/\bthe divide between expert consensus and varied geopolitical implementations\b/gi,'expert consensus and geopolitical implementation')
        .replace(/\ba necessary prerequisite for\b/gi,'necessary for')
        .replace(/\ba series of national and international policy initiatives designed to\b/gi,'policies to')
        .replace(/\breduce risks associated with\b/gi,'reduce risks in')
        .replace(/\bfull frontier AI value chain\b/gi,'frontier AI value chain')
        .replace(/\bmore efficiently by\b/gi,'by')
        .replace(/\bwith a view to\b/gi,'to')
        .replace(/\bin order to\b/gi,'to')
        .replace(/\s+/g,' ')
        .trim();
    }

    function demeta(q){
      let s=compress(q);
      if(!s) return '';
      if(title&&s.toLowerCase().startsWith(title.toLowerCase())){
        s=s.slice(title.length).replace(/^[\s.:;–—-]+/,'').trim();
      }
      s=s
        .replace(/^Ultimately,?\s*this (?:evaluation|analysis) (?:shows|finds|argues|concludes|demonstrates|indicates|suggests|highlights) that\s+/i,'')
        .replace(/^(?:The|This) (?:study|paper|article|report|analysis) examines how\s+/i,'')
        .replace(/^Abstract\s+Using [^,]{0,220},\s*this article examines how\s+/i,'')
        .replace(/^Using [^,]{0,220},\s*this article examines how\s+/i,'')
        .replace(/^(?:The|This) (?:study|paper|article|report|analysis) (?:shows|finds|argues|concludes|demonstrates|indicates|suggests|highlights) that\s+/i,'')
        .replace(/^(?:The|This) (?:study|paper|article|report|analysis) (?:shows|finds|argues|concludes|demonstrates|indicates|suggests|highlights)\s+/i,'')
        .replace(/^It (?:shows|finds|argues|concludes|demonstrates|indicates|suggests|highlights) that\s+/i,'')
        .replace(/^The results? (?:show|shows|find|finds|indicate|indicates|suggest|suggests) that\s+/i,'')
        .replace(/^The findings? (?:show|shows|find|finds|indicate|indicates|suggest|suggests) that\s+/i,'')
        .replace(/^This (?:decoupling|pattern|evidence|result) suggests that\s+/i,'')
        .replace(/^In the EU \(EU\) Member States\s+/i,'EU Member States ')
        .replace(/^In the European Union \(EU\) Member States\s+/i,'EU Member States ')
        .replace(/^From [^,]{0,150},\s*(the EU(?:’s|'s)? approach\s+)/i,'$1')
        .replace(/^the EU(?:’s|'s) approach/i,'The EU approach')
        .replace(/^Although [^,]{0,220},\s*/i,'')
        .replace(/^However,?\s*/i,'')
        .replace(/^and\s+/i,'')
        .trim();
      // Source-faithful repairs for common abstract grammar that otherwise leaves no explicit subject.
      if(/^This creates skills mismatches and leaves many researchers underprepared/i.test(s))
        s=s.replace(/^This creates skills mismatches and leaves many researchers underprepared/i,'Many researchers remain underprepared');
      if(/^The results? show a diversified but unbalanced European semiconductor ecosystem/i.test(s))
        s=s.replace(/^The results? show a diversified but unbalanced European semiconductor ecosystem/i,'Europe has a diversified but unbalanced semiconductor ecosystem');
      if(/^China still depends on European firms in narrow strategic sectors including/i.test(s))
        s=s.replace(/^China still depends on European firms in narrow strategic sectors including/i,'China still depends on European firms in');
      if(/^They analysed/i.test(s)&&/^ALLEA Task Forces/i.test(title)) s=s.replace(/^They/i,'ALLEA task forces');
      if(/^They also addressed/i.test(s)&&/^ALLEA Task Forces/i.test(title)) s=s.replace(/^They/i,'ALLEA task forces');
      if(/^OS is core to/i.test(s)) s=s.replace(/,?\s*and we urgently need to.*$/i,'');
      if(/digital power is now inseparable from economic security/i.test(s)){
        const m=s.match(/digital power is now inseparable from economic security[^.;]*/i); if(m)s=m[0];
      }
      if(/there has been an increasing recognition of the strategic and security dimensions of new technologies/i.test(s))
        s='The EU increasingly recognises the strategic and security dimensions of new technologies';
      if(/^The paper maps EU strategic import dependencies/i.test(s))
        s='EU strategic import dependencies combine economic, geoeconomic and geopolitical risks';
      if(/^It highlights research and innovation frameworks, institutional links and co-funding arrangements as practical channels for cooperation/i.test(s))
        s='R&I frameworks, institutional links and co-funding are practical channels for EU–Asia cooperation';
      if(/^Based on [^,]{0,260},\s*the study identifies key constraints to industrial competitiveness:/i.test(s))
        s=s.replace(/^Based on [^,]{0,260},\s*the study identifies key constraints to industrial competitiveness:\s*/i,'EU industrial competitiveness faces ');
      if(/^The study identifies key constraints to industrial competitiveness:/i.test(s))
        s=s.replace(/^The study identifies key constraints to industrial competitiveness:\s*/i,'EU industrial competitiveness faces ');
      if(/^Geopolitical pressure is forcing science policy to trade off/i.test(s))
        s=s.replace(/^Geopolitical pressure is forcing science policy to trade off/i,'Science policy now trades off');
      if(/geopolitical tensions strongly impinge on scientific collaboration/i.test(s))
        s='Geopolitical tensions are putting scientific collaboration under pressure';
      if(/^Intensifying geopolitical rivalries have triggered/i.test(s))
        s=s.replace(/^Intensifying geopolitical rivalries have triggered\s+/i,'Geopolitical rivalry has triggered ');
      if(/^Regarding liability,?\s*the study concludes that\s+/i.test(s))
        s=s.replace(/^Regarding liability,?\s*the study concludes that\s+/i,'');
      s=s.replace(/^Individual users, not platform providers, bear responsibility/i,'Individual users bear responsibility');
      if(/^Leaves many researchers underprepared/i.test(s)) s=s.replace(/^Leaves/i,'Many researchers remain');
      // Turn one common nominal result into a complete subject-first statement.
      let m=s.match(/^a diversified but unbalanced European ([^.;]+)$/i);
      if(m) s=`Europe has a diversified but unbalanced ${m[1]}`;
      m=s.match(/^([A-Z][^.;]{2,90})\s+remains?\s+(fragmented|dependent|exposed|concentrated|underprepared)\b/i);
      if(m) s=s;
      return compress(s);
    }

    function pieces(raw){
      const out=[];
      for(const sentence0 of splitSentences(raw||'')){
        const sentence=compress(sentence0);
        if(!sentence) continue;
        out.push(sentence);
        // Only split at boundaries where at least one side can stand as a full proposition.
        for(const re of [
          /\s*;\s*/,
          /,\s+(?=(?:while|but|although|yet|however|with|turning|making|leaving|giving|raising|creating|increasing|reducing|allowing|highlighting|exploiting|focusing|linking)\b)/i,
          /\s+(?=(?:while|although|yet)\b)/i,
          /\s+and\s+(?=(?:increase|increases|increased|raise|raises|raised|reduce|reduces|reduced|limit|limits|limited|strengthen|strengthens|strengthened|weaken|weakens|weakened|create|creates|created|leave|leaves|left|make|makes|made|give|gives|gave|add|adds|added|require|requires|required|use|uses|used|link|links|linked|show|shows|showed|highlight|highlights|highlighted|place|places|placed|contrast|contrasts|contrasted|explore|explores|explored|address|addresses|addressed)\b)/i,
          /\s+than\s+by\s+/i,
          /\s+as\s+(?=[A-Z][a-z])/,
          /\s+(?:and|but)\s+(?=(?:could|may|might|would|will|can|must|should|has|have|had|is|are|was|were)\b)/i,
          /\s+and\s+to\s+(?=[A-Z])/,
          /:\s+(?=(?:From|from|The|the|EU|Europe|European|China|Chinese|US|Member States|Research|Innovation|Technology|Scientific)\b)/
        ]){
          const ps=sentence.split(re).map(clean).filter(Boolean);
          if(ps.length>1) out.push(...ps);
        }
      }
      return out;
    }

    function finish(raw){
      let q=demeta(raw);
      if(!q||SOURCE_SCAFFOLD.test(q)||GENERIC_WHY.test(q)||BAD_START.test(q)||META.test(q)||isDocumentDebris(q)) return '';
      if(/^(?:create|creates|creating|leave|leaves|leaving|allow|allows|allowing|highlight|highlights|highlighting|place|places|placing|show|shows|showing|find|finds|finding|argue|argues|arguing|make|makes|making|give|gives|giving|provide|provides|providing|link|links|linking)\b/i.test(q)) return '';
      q=q.replace(/\s+([,.!?;:])/g,'$1').replace(/[;:,]+$/,'').trim();
      if(!q||q.length<28||q.length>119||/…|\.\.\./.test(q)||/\?$/.test(q)||!POINT_PREDICATE.test(q)) return '';
      if(!/[.!?]$/.test(q)) q+='.';
      if(q.length>120) return '';
      // readerPoint is now used only as a final safety check on an already complete short proposition.
      const safe=readerPoint(q);
      if(!safe||safe.length>120||BAD_START.test(safe)||GENERIC_WHY.test(safe)||SOURCE_SCAFFOLD.test(safe)) return '';
      return safe;
    }

    const fields=[
      {v:x?.summary||'',base:20},
      {v:x?.signal_note||'',base:19},
      {v:x?.matrix_evidence_basis||'',base:16},
      {v:x?.external_eu_bridge||x?.bridge_sentence||'',base:15},
      {v:x?.core_message||'',base:10}
    ];
    const candidates=[];
    const seen=new Set();
    for(const field of fields){
      for(const raw of pieces(field.v)){
        const q=finish(raw);
        if(!q) continue;
        const nq=norm(q);
        if(!nq||seen.has(nq)||nq===titleNorm) continue;
        seen.add(nq);
        const wTok=new Set(whatNorm.split(' ').filter(t=>t.length>4));
        const qTok=nq.split(' ').filter(t=>t.length>4);
        const overlap=qTok.length?qTok.filter(t=>wTok.has(t)).length/qTok.length:0;
        let score=field.base;
        if(IMPACT.test(q)) score+=10;
        if(SPECIFIC.test(q)) score+=6;
        if(/\b(EU|Europe|European)\b/i.test(q)) score+=3;
        if(/\b(depend|risk|security|fund|partner|capacity|access|control|compet|cost|fragment|concentrat|underinvest|exclude|scrutin|shortage|gap)\w*/i.test(q)) score+=5;
        if(q.length>=55&&q.length<=116) score+=2;
        if(nq===whatNorm) score-=10;
        else if(overlap>.82) score-=6;
        candidates.push({q,score});
      }
    }
    candidates.sort((a,b)=>b.score-a.score||a.q.length-b.q.length||a.q.localeCompare(b.q));
    if(candidates[0]) return candidates[0].q;

    // Thin records may not contain a second consequence sentence. In that case reuse a specific source-bound point,
    // never a generic topic template, rather than inventing a broader implication.
    const stored=finish(x?.core_message||'');
    if(stored&&!GENERIC_WHY.test(stored)) return stored;
    const safeWhat=finish(what||'');
    if(safeWhat&&!GENERIC_WHY.test(safeWhat)) return safeWhat;
    const titlePoint=finish(title);
    if(titlePoint&&!GENERIC_WHY.test(titlePoint)) return titlePoint;
    return '';
  }


  function pointFor(x){
    if(x.headline){
      const stored=completeCoreMessage(x.core_message||'');
      if(stored&&norm(stored).trim()!==norm(x.headline||'').trim()){
        const p=readerPoint(plainLanguagePoint(x,stored));
        if(p&&likelyEnglish(p)) return p;
      }
      const h=headlinePoint(x);
      const hp=likelyEnglish(h)?readerPoint(plainLanguagePoint(x,h)):'';
      if(hp) return hp;
      return readerPoint(fallbackPoint(x));
    }
    const special=structuredPoint(x);
    if(special){const sp=readerPoint(special)||readerPoint(plainLanguagePoint(x,special));if(sp)return sp;}
    const stored=completeCoreMessage(x.core_message||'');
    if(stored){const point=readerPoint(plainLanguagePoint(x,stored));if(point)return point;}

    const candidates=splitSentences(x.summary||'')
      .map(s=>({s,score:candidateScore(s)}))
      .filter(o=>o.score>=7)
      .sort((a,b)=>b.score-a.score||a.s.length-b.s.length);
    for(const candidate of candidates){
      const point=readerPoint(plainLanguagePoint(x,simplifyCandidate(candidate.s)));
      if(point&&!META.test(point)&&!isDocumentDebris(point)&&likelyEnglish(point)&&!/…|\.\.\./.test(point)) return point;
    }
    // Final fallback stays explicit, English and source-topic bound.
    return readerPoint(fallbackPoint(x));
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
      if(!point||isDocumentDebris(point)||META.test(point)||!likelyEnglish(point)) continue;
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
        title:clean(x.title||x.headline||''),
        authors:clean(x.authors||''),
        summary:prepareSummary(x.summary||''),
        itemType:clean(x.type||''),
        euRelevance:clean(x.eu_relevance||'')
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
    const am=a.match(/(?:Strand A theme|Recurring Strand A theme):\s*([^—;]+)/i);
    if(am) return clean(am[1]);
    return '';
  }

  function themeWhy(theme){
    const n=norm(theme);
    if(/research security|foreign interference|knowledge security/.test(n)) return 'EU research organisations may face tighter rules on openness, access and international collaboration.';
    if(/technology sovereignty|strategic autonomy/.test(n)) return "European tech capacity may depend less on external suppliers.";
    if(/china|de-risk/.test(n)) return 'EU–China R&I cooperation may become narrower or more selective.';
    if(/export control|dual use/.test(n)) return 'Export controls may change European access to technology, equipment, knowledge and partners.';
    if(/fragmentation/.test(n)) return 'Scientific fragmentation may raise collaboration and access risks for Europe.';
    if(/transatlantic|us-china|competition/.test(n)) return "US–China competition may narrow Europe's room for manoeuvre in technology and research.";
    if(/critical and emerging|semiconductor|quantum|biotech|artificial intelligence/.test(n)) return 'European access and investment may shift in a strategically important technology.';
    if(/economic security/.test(n)) return 'Economic-security policy may steer European R&I funding, capability and dependencies.';
    if(/competitiveness|capabilit/.test(n)) return "Europe's relative R&I capability may shift in technologies that shape geopolitical power.";
    if(/supply chain|dependenc|raw material|mineral/.test(n)) return "Europe's exposure to strategic inputs, infrastructure or supply chains may change.";
    if(/horizon europe|fp10/.test(n)) return 'EU research funding, participation or international cooperation may change.';
    if(/science diplomacy/.test(n)) return 'Science diplomacy may open, narrow or redirect channels for European research cooperation.';
    return '';
  }

  function signalWhat(x){
    const v=clean(x.what||'')||headlinePoint(x)||clean(x.headline||'');
    return readerPoint(v)||readerPoint(fallbackPoint(x));
  }

  function signalWhy(x){
    const direct=readerPoint(x.why_it_matters||'');
    if(direct) return direct;
    const theme=signalTheme(x);
    const themed=readerPoint(themeWhy(theme));
    if(themed) return themed;
    const note=clean(x.signal_note||'');
    if(note){
      const what=clean(x.headline||'');
      let remainder=note;
      if(what&&remainder.toLowerCase().startsWith(what.toLowerCase())) remainder=clean(remainder.slice(what.length).replace(/^\.?\s*/,''));
      const safe=readerPoint(remainder); if(safe) return safe;
    }
    return "Current geopolitical change may alter Europe's R&I or strategic technology position.";
  }

  function buildSignals(data){
    const seen=new Set();
    const out=[];
    for(const x of (Array.isArray(data?.strand_c)?data.strand_c:[])){
      const key=keyFor(x); if(!key||seen.has(key)) continue; seen.add(key);
      const what=signalWhat(x); if(!what||isDocumentDebris(what)||!likelyEnglish(what)) continue;
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
    return buildInsights({strand_a:Array.isArray(data?.strand_a)?data.strand_a:[],strand_b:[],strand_c:[]});
  }

  return {TOPICS,OTHER,topicFor,pointFor,whyFor,fallbackPoint,plainLanguagePoint,readerPoint,buildInsights,buildSignals,buildResearchInsights,signalWhat,signalWhy,signalTheme,concise,isDocumentDebris,prepareSummary,candidateScore,structuredPoint,likelyEnglish,completeCoreMessage};
});
