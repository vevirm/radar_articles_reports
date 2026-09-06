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
    const foreign=(n.match(/\b(und|der|die|das|des|den|ein|eine|et|les|des|une|un|dans|pour|avec|sur|del|della|delle|gli|che|con|per|los|las|una|para|sobre|y|de|la|el|van|het|een|voor|met|și|sau|din|pentru|cu|w|oraz|dla|jest|na|strategi|dalam|menghadapi|dampak|amerika|serikat|tiongkok|terhadap|pengembangan|penelitian|teknologi|eropa)\b/g)||[]).length;
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
    if(/\b(?:info|contact)@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/i.test(s)||/\bCantersteen\b/i.test(s)||/^\d+\s+European Citizen Action Service\b/i.test(s)) return true;
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
    // Abstract feeds sometimes concatenate sentence boundaries ("industry.The").
    // Restore the boundary before sentence ranking so source-specific findings are not buried.
    s=s.replace(/(?<=[a-z0-9])\.(?=[A-Z])/g,'. ');
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

  function fastReaderText(v){
    let s=clean(v);
    if(!s) return '';
    const swap=(re,repl)=>{s=s.replace(re,(m,...args)=>{const offset=args[args.length-2];return offset===0&&/^[A-Z]/.test(m)?repl.charAt(0).toUpperCase()+repl.slice(1):repl})};
    const replacements=[
      [/\bAI rules split across countries weakens\b/gi,'AI rules split across countries weaken'],
      [/\bRules for AI supply chains exposes\b/gi,'Rules for AI supply chains expose'],
      [/\bDigital central-bank money shift\b/gi,'Digital central-bank money shifts'],
      [/\bEU agrees an fast-moving\b/gi,'EU agrees a fast-moving'],
      [/\bEU checks on foreign investment limits\b/gi,'EU checks on foreign investment limit'],
      [/\btech transfer\b/gi,'technology moving abroad'],
      [/\bextra extra cost or delay\b/gi,'extra cost or delay'],
      [/\bEU defence R&D can build capability but add controls\b/gi,'EU defence research can build European strength but add restrictions'],
      [/\bEU geo-industrial policy links scale with resilience\b/gi,'EU industrial policy links growth with stronger supply chains'],
      [/\bEU manufacturing resilience depends on reconfigurable digital systems\b/gi,'EU manufacturing can handle disruption better when digital production systems can be changed quickly'],
      [/\bEU economic-security policy is moving from openness to deterrence\b/gi,'EU policy is moving from openness toward stronger protection from economic pressure'],
      [/\bEU tech-sovereignty policy combines protection and capacity-building\b/gi,'EU technology policy combines protection with efforts to build more European strength'],
      [/\bEurope cannot buy military-AI autonomy from outside\b/gi,'Europe cannot become independent in military AI just by buying from outside suppliers'],
      [/\bNATO espionage case exposes research-security risk\b/gi,'NATO espionage case shows risks to sensitive research'],
      [/\bDual-use research creates new export-control risks\b/gi,'Research with civilian and military uses creates new risks from limits on selling technology abroad'],
      [/\bResearchers flag barriers to EU mobility\b/gi,'Researchers flag barriers to moving within the EU'],
      [/\bScandinavian research-security models differ on openness\b/gi,'Scandinavian approaches to protecting sensitive research differ on openness'],
      [/\bChina’s EV shift exposed weak EU industrial coordination\b/gi,'China’s EV shift exposed weak coordination between EU countries and industry'],
      [/\bChina's EV shift exposed weak EU industrial coordination\b/gi,"China's EV shift exposed weak coordination between EU countries and industry"],
      [/\bAI supply-chain governance exposes EU dependency risks\b/gi,'Rules for AI supply chains expose the risks of relying on others'],
      [/\bcontrol over model, chip, cloud and data-chain bottlenecks\b/gi,'control over AI models, chips, cloud services and key data links'],
      [/\bfragmented AI rules reduce Europe’s ability to turn regulation into coherent market and technology leverage\b/gi,'AI rules split across countries reduce Europe’s ability to create a consistent market and influence technology'],
      [/\bfragmented AI rules reduce Europe's ability to turn regulation into coherent market and technology leverage\b/gi,"AI rules split across countries reduce Europe's ability to create a consistent market and influence technology"],
      [/\bchip access and production determine whether European R&I can use critical hardware without external restrictions\b/gi,'chip access and production determine whether European research and innovation can use essential hardware without outside restrictions'],
      [/\bat continental scale\b/gi,'across Europe'],
      [/\bresearcher mobility changes the skills and scientific capacity available to European labs and universities\b/gi,'researchers moving between countries and jobs changes which skills and research strength European labs and universities can access'],
      [/\bsafeguards that are too broad can damage openness, while safeguards that are too weak leave sensitive collaborations exposed\b/gi,'protections that are too broad can hurt open research, while weak protections leave sensitive partnerships exposed'],
      [/\blong-horizon projects\b/gi,'long-term projects'],
      [/\bvery large European defence-tech rounds\b/gi,'very large funding deals for European defence-technology companies'],
      [/\btechnology ties can combine market opportunity with asymmetric dependence and pressure to de-risk\b/gi,'technology ties can create chances to grow but also one-sided reliance that Europe may need to reduce'],
      [/\bdual-use and defence policy can build strategic capability while adding security, export-control and openness constraints\b/gi,'civilian-and-military technology and defence policy can build European strength but also add tighter security checks, limits on selling technology abroad and limits on open collaboration'],
      [/\bAI rule fragmentation\b/gi,'AI rules split across countries'],
      [/\bAI supply-chain governance\b/gi,'rules for AI supply chains'],
      [/\bresearch-collaboration curbs\b/gi,'limits on research partnerships'],
      [/\bCBDCs?\b/g,'digital central-bank money'],
      [/\bmonetary infrastructure\b/gi,'money systems'],
      [/\bCEE industry\b/g,'Central and Eastern European industry'],
      [/\bgeopolitical scale pressures\b/gi,'pressure from global competition to grow'],
      [/\braw-material access\b/gi,'access to key materials'],
      [/\bdual circulation\b/gi,'domestic-focused economic strategy'],
      [/\bresearch safeguards\b/gi,'protections for sensitive research'],
      [/\bcyber resilience\b/gi,'ability to withstand cyber attacks'],
      [/\bAI competitiveness is constrained by capital and compute gaps\b/gi,'AI firms are held back by funding and computing-power gaps'],
      [/\bsets a framework for\b/gi,'sets common principles for'],
      [/\bagile defence-innovation programme\b/gi,'fast-moving defence research programme'],
      [/\bprocurement preferences\b/gi,'preference for European suppliers in public buying'],
      [/\bdeployment costs\b/gi,'costs of putting technology into use'],
      [/\bgeopolitical shocks\b/gi,'international political disruptions'],
      [/\bindispensability\b/gi,'areas where Europe cannot easily be replaced'],
      [/\beconomic-security\b/gi,'protection from economic pressure'],
      [/\bfrom openness to deterrence\b/gi,'from openness toward stronger defensive measures'],
      [/\bgeo-industrial policy\b/gi,'industrial policy'],
      [/\breconfigurable digital systems\b/gi,'digital production systems that can be changed quickly'],
      [/\bcapacity-building\b/gi,'building European strength'],
      [/\bcritical dependence\b/gi,'risky reliance'],
      [/\bleverage\b/gi,'influence'],
      [/\bstrategic conditions\b/gi,'conditions to protect key interests'],
      [/\bautomotive capacity for defence scale\b/gi,'car-industry factories to increase defence production'],
      [/\bmilitary-AI autonomy\b/gi,'ability to run military AI without outside suppliers'],
      [/\bresearch talent\b/gi,'researchers'],
      [/\bbattery-production machinery sovereignty\b/gi,'control over battery-making equipment'],
      [/\btech scale-up alliance\b/gi,'alliance to fund growing tech companies'],
      [/\bremains fragmented\b/gi,'remains divided'],
      [/\bspace capability\b/gi,'space technology and services'],
      [/\bVC gap\b/g,'shortage of investment for young companies'],
      [/\boutside-investor reliance\b/gi,'reliance on foreign investors'],
      [/\bproductivity gap tracks weak R&D and equity\b/gi,'productivity gap is linked to weak research spending and investment funding'],
      [/\bethics committees for research security\b/gi,'ethics committees to review sensitive research'],
      [/\brisks weak implementation\b/gi,'may be hard to put into practice'],
      [/\bresearch-security\b/gi,'protection of sensitive research'],
      [/\bbarriers to EU mobility\b/gi,'barriers for researchers moving within the EU'],
      [/\bexport-control\b/gi,'limits on technology sales abroad'],
      [/\bdual-use access\b/gi,'access to goods usable for civilian and military purposes'],
      [/\bdual-use tech\b/gi,'technology usable for civilian and military purposes'],
      [/\bdual-use research\b/gi,'research with civilian and military uses'],
      [/\bdual-use and defence policy\b/gi,'civilian-and-military technology and defence policy'],
      [/\breach scale\b/gi,'grow large enough to compete'],
      [/\bto scale\b/gi,'to grow'],
      [/\bdefence-tech rounds\b/gi,'funding deals for defence-tech companies'],
      [/\bnon-European capital\b/gi,'funding from outside Europe'],
      [/\bmarket opportunity\b/gi,'chance to grow'],
      [/\basymmetric dependence\b/gi,'one-sided reliance'],
      [/\bde-risk\b/gi,'reduce risky dependence'],
      [/\bcritical hardware\b/gi,'essential hardware'],
      [/\bresearcher mobility\b/gi,'researchers moving between countries and jobs'],
      [/\bscientific capacity\b/gi,'research strength'],
      [/\bcontinental scale\b/gi,'across Europe'],
      [/\bsupply-chain geography\b/gi,'where suppliers and factories are located'],
      [/\bfrontier grants\b/gi,'grants for top-level research'],
      [/\bstrategic firms\b/gi,'important firms'],
      [/\bopenness constraints\b/gi,'limits on open collaboration'],
      [/\bforeign-interference tactics\b/gi,'outside attempts to influence or steal'],
      [/\bfragmented AI rules\b/gi,'AI rules split across countries'],
      [/\bfragmented national responses\b/gi,'different national responses'],
      [/\bfragmented implementation\b/gi,'countries putting rules into practice differently'],
      [/\bindustrial coordination\b/gi,'EU countries and industry working together'],
      [/\bstrategic capability\b/gi,'ability to act independently'],
      [/\bstrategic ability\b/gi,'ability to act independently'],
      [/\bexternal tech dependence\b/gi,'reliance on outside technology'],
      [/\bexternal restrictions\b/gi,'outside restrictions'],
      [/\bexternal dependence\b/gi,'outside reliance'],
      [/\bdependency risks\b/gi,'risks from relying on others'],
      [/\bdependencies\b/gi,'reliance'],
      [/\bdependency\b/gi,'reliance'],
      [/\bregulation\b/gi,'rules'],
      [/\btechnology leverage\b/gi,'influence through technology'],
      [/\bbrain circulation\b/gi,'researchers moving between countries and sharing knowledge'],
      [/\bbrain drain\b/gi,'researchers leaving Europe'],
      [/\bchokepoints?\b/gi,'hard-to-replace weak points'],
      [/\bbottlenecks?\b/gi,'hard-to-replace weak points'],
      [/\bfrontier compute\b/gi,'top-end computing power'],
      [/\bcompute capacity\b/gi,'available computing power'],
      [/\bcompute\b/gi,'computing power'],
      [/\bresearch infrastructure\b/gi,'research facilities and tools'],
      [/\bcritical infrastructure\b/gi,'essential systems and facilities'],
      [/\bcritical raw materials?\b/gi,'hard-to-replace materials'],
      [/\bcritical technolog(?:y|ies)\b/gi,'key technologies'],
      [/\bde-?risking\b/gi,'reducing risky dependence'],
      [/\bdecoupling\b/gi,'cutting ties'],
      [/\bdual[- ]use\b/gi,'usable for civilian and military purposes'],
      [/\beconomic security\b/gi,'protection from economic pressure'],
      [/\bemerging technolog(?:y|ies)\b/gi,'new technologies'],
      [/\bEuropean preference\b/gi,'preference for European suppliers'],
      [/\bexport controls?\b/gi,'limits on technology sales abroad'],
      [/\bFDI screening\b/gi,'checks on foreign investment'],
      [/\boutbound investment screening\b/gi,'checks on European investment abroad'],
      [/\binvestment screening\b/gi,'checks on foreign investment'],
      [/\bforeign interference\b/gi,'outside attempts to influence or steal'],
      [/\bsemiconductor fabs?\b/gi,'chip factories'],
      [/\bsemiconductors?\b/gi,'chips'],
      [/\bfoundr(?:y|ies)\b/gi,'chip factories'],
      [/\bfriend-?shoring\b/gi,'buying more from trusted partner countries'],
      [/\bnear-?shoring\b/gi,'moving production closer to Europe'],
      [/\bgeoeconomics?\b/gi,'use of trade, money or technology for political pressure'],
      [/\bHorizon Europe association\b/gi,'participation in Horizon Europe'],
      [/\bintellectual property\s*\(IP\)\b/gi,'ownership of inventions and ideas'],
      [/\bintellectual property\b/gi,'ownership of inventions and ideas'],
      [/\bknowledge security\b/gi,'protecting sensitive research and know-how'],
      [/\bknowledge valorisation\b/gi,'turning research into useful products and businesses'],
      [/\bopen science\b/gi,'openly shared research'],
      [/\bopen strategic autonomy\b/gi,'ability to act with less outside dependence while staying open'],
      [/\bpre-commercial procurement\b/gi,'public buying to test new solutions'],
      [/\bpublic procurement\b/gi,'public-sector buying'],
      [/\bprocurement\b/gi,'buying'],
      [/\bresearch security\b/gi,'protecting sensitive research'],
      [/\bscale-ups?\b/gi,'growing companies'],
      [/\bscience diplomacy\b/gi,'research ties between countries'],
      [/\bsecurity of supply\b/gi,'reliable access to supplies'],
      [/\bsovereign cloud\b/gi,'cloud services under European control'],
      [/\bspin[- ]?(?:off|out)s?\b/gi,'new companies created from research'],
      [/\bstandard-setting\b/gi,'setting common rules'],
      [/\brule-setting\b/gi,'setting common rules'],
      [/\btechnical standards\b/gi,'shared rules for how things work'],
      [/\bstandards power\b/gi,'influence over common rules'],
      [/\bstrategic autonomy\b/gi,'ability to act without relying too much on others'],
      [/\btechnolog(?:y|ical) sovereignty\b/gi,'control over key technology'],
      [/\btech sovereignty\b/gi,'control over key technology'],
      [/\bsovereignty\b/gi,'control'],
      [/\bautonomy\b/gi,'ability to act independently'],
      [/\bfrontier\b/gi,'most advanced'],
      [/\bfriction\b/gi,'extra cost or delay'],
      [/\bdeployment\b/gi,'use'],
      [/\bstrategic dependenc(?:y|ies)\b/gi,'risky reliance on others'],
      [/\btechnology leakage\b/gi,'sensitive know-how leaving Europe'],
      [/\btechnology readiness level(?:s)?\s*\(TRLs?\)\b/gi,'how close a technology is to practical use'],
      [/\btechnology transfer\b/gi,'moving technology or know-how to another organisation or country'],
      [/\bthird countries?\b/gi,'non-EU countries'],
      [/\btrusted research\b/gi,'research with safeguards against misuse'],
      [/\bvalley of death\b/gi,'funding gap between research and the market'],
      [/\bweaponised interdependence\b/gi,'using dependence as pressure'],
      [/\binteroperability\b/gi,'systems working together'],
      [/\bfederated infrastructure\b/gi,'linked systems run by different organisations'],
      [/\bdata spaces?\b/gi,'shared data systems'],
      [/\bcommercialisation\b/gi,'turning research into products and businesses'],
      [/\bcommercialization\b/gi,'turning research into products and businesses'],
      [/\blate-stage finance\b/gi,'funding for growing companies'],
      [/\blate-stage capital\b/gi,'funding for growing companies'],
      [/\binstitutional capital\b/gi,'money from large long-term investors'],
      [/\bventure capital\b/gi,'investment in young companies'],
      [/\bVC\b/g,'investment in young companies'],
      [/\bequity finance\b/gi,'investment funding'],
      [/\bregulatory influence\b/gi,'influence over rules'],
      [/\bregulatory\b/gi,'rule-setting'],
      [/\bgovernance\b/gi,'rules and decision-making'],
      [/\bfragmentation\b/gi,'countries or systems working separately'],
      [/\bimplementation delays?\b/gi,'delays putting rules into practice'],
      [/\bimplementation\b/gi,'putting rules into practice'],
      [/\bmember-state coordination\b/gi,'EU countries working together'],
      [/\basymmetric dependencies\b/gi,'one-sided reliance'],
      [/\bdiversification\b/gi,'spreading reliance across more suppliers or partners'],
      [/\bprogramme association\b/gi,'access to the programme'],
      [/\bprogram association\b/gi,'access to the programme'],
      [/\bindustrial translation\b/gi,'turning research into production'],
      [/\bresearch acceleration\b/gi,'faster research'],
      [/\bsecurity clauses?\b/gi,'security conditions'],
      [/\beligibility\b/gi,'who can take part'],
      [/\bcompetitiveness\b/gi,'ability to compete'],
      [/\bcompetitive\b/gi,'able to compete'],
      [/\bcapabilities\b/gi,'abilities'],
      [/\bcapability\b/gi,'ability'],
      [/\bresilience\b/gi,'ability to keep working through disruption'],
      [/\bcoercion\b/gi,'pressure'],
      [/\bR&I\b/g,'research and innovation'],
      [/\bR&D\b/g,'research and development'],
    ];
    for(const [re,repl] of replacements) swap(re,repl);
    s=s
      .replace(/\bAI rules split across countries weakens\b/gi,'AI rules split across countries weaken')
      .replace(/\bRules for AI supply chains exposes\b/gi,'Rules for AI supply chains expose')
      .replace(/\bDigital central-bank money shift\b/gi,'Digital central-bank money shifts')
      .replace(/\bagrees an fast-moving\b/gi,'agrees a fast-moving')
      .replace(/\bchecks on foreign investment limits\b/gi,'checks on foreign investment limit')
      .replace(/\bextra extra cost or delay\b/gi,'extra cost or delay')
      .replace(/\bresearchers moving between countries and jobs changes\b/gi,'researchers moving between countries and jobs change')
      .replace(/\bat across Europe\b/gi,'across Europe')
      .replace(/\bdeep money from large long-term investors\b/gi,'large pools of long-term investment')
      .replace(/\bdefence-tech\b/gi,'defence-technology')
      .replace(/\btech-control policy\b/gi,'technology policy')
      .replace(/\btech dependence\b/gi,'reliance on outside technology')
      .replace(/\bdigital tech\b/gi,'digital technology')
      .replace(/\bweaponise access to key materials against Europe\b/gi,'use access to key materials as pressure against Europe')
      .replace(/^Circular economy\b/i,'Reuse and recycling')
      .replace(/^African radio astronomy reshapes EU infrastructure access\.?$/i,"Large radio telescopes in Africa reshape Europe’s access to research facilities.")
      .replace(/^E-hryvnia design stresses transparency and ability to withstand cyber attacks\.?$/i,"Ukraine’s planned digital currency stresses transparency and resistance to cyber attacks.")
      .replace(/^ALLEA\b/,'European academies group ALLEA')
      .replace(/^EIC\b/,'European Innovation Council')
      .replace(/^ERC\b/,'European Research Council')
      .replace(/\btech\b/gi,'technology')
      .replace(/\s+/g,' ').replace(/\s+([,.!?;:])/g,'$1').trim();
    return s;
  }

  // V17.13.27 reader-language contract. The same evidence is phrased at different
  // levels on different pages; this changes presentation only, never admission or
  // Matrix placement. Read is the simplest. Matrix/Priorities are still plain but
  // keep a few analytical terms. The main Radar keeps policy terminology. Excel
  // and record-detail exports keep the technical wording and classifier evidence.
  function readText(v){
    let s=fastReaderText(v);
    if(!s)return '';
    return s
      .replace(/\bability to act without relying too much on others\b/gi,'freedom to act without relying too much on others')
      .replace(/\bability to act independently\b/gi,'freedom to act')
      .replace(/\bcontrol over key technology\b/gi,'control of important technology')
      .replace(/\brules and decision-making\b/gi,'rules and decisions')
      .replace(/\bcountries or systems working separately\b/gi,'countries or systems not working together')
      .replace(/\bone-sided reliance\b/gi,'relying much more on one side')
      .replace(/\binvestment in young companies\b/gi,'funding for young companies')
      .replace(/\bexternal suppliers?\b/gi,'suppliers outside Europe')
      .replace(/\bexternal access\b/gi,'access from outside Europe')
      .replace(/\boutside dependence\b/gi,'reliance on others')
      .replace(/\bexternal dependence\b/gi,'reliance on others')
      .replace(/\bstrategic capability\b/gi,'important European capacity')
      .replace(/\bstrategic technology\b/gi,'important technology')
      .replace(/\bgeopolitical competition\b/gi,'international competition')
      .replace(/\bgeopolitical pressure\b/gi,'international political pressure')
      .replace(/\s+/g,' ').trim();
  }

  function matrixText(v){
    let s=fastReaderText(v);
    if(!s)return '';
    return s
      .replace(/\bexternal dependence\b/gi,'outside reliance')
      .replace(/\bstrategic dependence\b/gi,'risky reliance on others')
      .replace(/\bstrategic dependencies\b/gi,'risky reliance on others')
      .replace(/\bcompetitive position\b/gi,'ability to compete')
      .replace(/\bgeopolitical leverage\b/gi,'political leverage')
      .replace(/\bpolicy lever\b/gi,'policy response')
      .replace(/\s+/g,' ').trim();
  }

  function radarText(v){
    // Main Radar: clean extraction/OCR artefacts, but do not translate standard
    // R&I-policy vocabulary into beginner language.
    return repairOcr(v).replace(/\s+/g,' ').trim();
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


  function whatForEuRiGeo(x){
    // Main-Radar answer to: “What does this source actually say for EU R&I geopolitics?”
    // Reusable topic slogans are deliberately rejected. Prefer a concrete proposition from
    // this source: named actor/instrument/dependency + the specific change or consequence.
    const MAX_RADAR_CHARS=300;
    const GENERIC_RADAR_POINT=/^(?:AI capacity and dependence are becoming strategic issues|Geopolitical competition is pushing Europe|European access and investment may shift|Geopolitical rivalry is changing Europe|Foresight methods can test emerging strategic change|Research-security pressure is changing how Europe|Semiconductor dependence is constraining Europe|Security competition is pulling more European R&I|Geopolitical pressure is reshaping EU research funding|EU–China R&I cooperation may become narrower|Strategic dependencies are changing Europe|Digital and cyber policy is shaping Europe|Quantum capability is becoming part of Europe|Critical raw materials shape Europe|Researcher mobility is becoming a strategic issue|Current geopolitical change may alter Europe)/i;
    const GENERIC_RADAR_FRAGMENT=/This may affect European access, investment or capability-building in a technology that is becoming strategically important/i;
    const PROCESS_META=/\b(?:exact .*page (?:was )?reviewed|source (?:was )?reviewed|underlying source|primary source|reviewed_source|review establishes|source text available|scanner|admitted to strand|research is based on|mixed methodology|comparative method|statistical method|analytical method|its EU relevance is classified|explicit EU\/European policy content|consult the linked publication|collected from researchers|responses? \(.*Member States|\bMethod\b)\b/i;
    const RI=/\b(research|innovation|science|scientific|technology|technological|university|universit|researcher|talent|skills?|r&d|r&i|compute|cloud|semiconductor|chip|quantum|biotech|infrastructure|funding|horizon|erc|industrial|digital|cyber|patent|data|laborator|doctoral|phd|venture capital|scale.?up)\w*/i;
    const GEO=/\b(geopolit|strategic|security|depend|reli|autonom|sovereign|compet|export control|sanction|de-risk|derisk|supply chain|foreign|international|cross-border|collabor|cooperat|partner|access|control|restrict|screen|fragment|trade|tariff|subsid|locali[sz]ation|procurement|acquisition|china|chinese|united states|\bus\b|russia|ukraine|nato|india|japan|taiwan|global)\w*/i;
    const EU=/\b(EU|Europe|European|Horizon Europe|ERC|Member States|euro area|European Research Area|Netherlands|Dutch|Finland|Finnish|Germany|German|France|French|Romania|Romanian|Bulgaria|Bulgarian|Poland|Polish)\b/i;
    const META_WHAT=/^(?:Learning outcomes?\b|To address this\b|By 20\d{2}\b|The purpose of\b|This (?:study|paper|article|report) (?:examines|explores|analyses|analyzes|aims|uses)\b|The (?:study|paper|article|report) (?:examines|explores|analyses|analyzes|aims|uses)\b)/i;
    const ACTION_SENTENCE=/\b(?:is|are|was|were|has|have|had|can|could|may|might|will|would|should|must|show|find|argu|conclud|reveal|indicat|suggest|highlight|affect|change|shift|raise|cut|limit|restrict|reduc|increas|strengthen|weaken|depend|rely|build|fund|open|close|adopt|introduc|expand|creat|link|leave|move|trail|outpac|constrain|enabl|protect|reshap|redirect|determin|pressur|face|gain|lose|need|remain|becom|treat|use|map|offer|support|driv|updat|propos|coordinat|requir|reward|allow|delay|retain|attract|concentrat|lack|reinforc|translat|reconfigur|narrow|widen|rank|tighten|contribut|correspond|diversif|identif|present)\w*\b/i;
    const title=repairOcr(x?.title||x?.headline||'');
    const scope=repairOcr([title,x?.summary||'',x?.relevance_note||'',x?.core_message||''].join(' '));
    const isB=String(x?.strand||'').toUpperCase()==='B';
    const METHOD=/\b(foresight|horizon scanning|weak signal|scenario|backcasting|roadmap|Delphi|cross-impact|anticipat|future method|strategic futures|forecast|technology intelligence|emerging technolog)\w*/i;
    const titleLike=v=>!!v&&norm(v).trim()===norm(title).trim()&&!ACTION_SENTENCE.test(v);

    function radarCandidate(raw){
      let q=repairOcr(raw||'').replace(/^Abstract\s*/i,'').replace(/^Purpose\s+/i,'').trim();
      if(!q||GENERIC_RADAR_FRAGMENT.test(q)||PROCESS_META.test(q)||isDocumentDebris(q))return '';
      // Remove academic scaffolding while keeping the proposition itself.
      q=q.replace(/^(?:It|The (?:study|paper|article|report|analysis)|This (?:study|paper|article|report|analysis))\s+(?:finds|shows|argues|concludes|demonstrates|identifies|reveals|indicates|suggests|highlights)\s+(?:that\s+)?/i,'')
         .replace(/^Using\b[^,]{0,230},\s*(?:this|the) (?:study|paper|article|report|analysis) (?:examines|shows|finds|argues|demonstrates|identifies) (?:how|that\s+)?/i,'')
         .replace(/^(?:This|The) (?:study|paper|article|report|analysis) examines how\s+/i,'')
         .replace(/^(?:This|The) (?:study|paper|article|report|analysis) argues that\s+/i,'')
         .replace(/^It argues that\s+/i,'')
         .replace(/^It shows that\s+/i,'')
         .replace(/^The results show (?:that\s+)?/i,'')
         .replace(/^Results show (?:that\s+)?/i,'')
         .replace(/^The findings (?:show|indicate|suggest|reveal) (?:that\s+)?/i,'')
         .replace(/^Findings (?:show|indicate|suggest|reveal) (?:that\s+)?/i,'')
         .replace(/^(?:This|The) (?:research|study|paper|article|report) aimed to (?:analyse|analyze|examine|assess)\s+/i,'')
         .replace(/\bthis Analysis\b/g,'the analysis')
         .replace(/\.{2,}$/,'.')
         .replace(/\s+/g,' ').trim();
      if(/Horizon Europe/i.test(q)&&/Chinese (?:investments?|entities)/i.test(q)&&/de-risking|economic security/i.test(q))
        q="Excluding Chinese entities from large parts of Horizon Europe and scrutinising Chinese high-tech investment mark the EU's shift from broad openness toward de-risking and economic security.";
      if(!q||GENERIC_RADAR_POINT.test(q)||PROCESS_META.test(q)||titleLike(q))return '';
      if(q.length>MAX_RADAR_CHARS){
        const clauses=q.split(/\s*[;]\s*|\s+[–—]\s+|,\s+(?=(?:while|but|although|whereas|because|which|with|including|allowing|leaving|giving|creating|reducing|increasing|reinforcing|highlighting|showing)\b)/i)
          .map(clean).filter(c=>c.length>=45&&c.length<=MAX_RADAR_CHARS&&ACTION_SENTENCE.test(c));
        if(clauses.length) q=clauses.sort((a,b)=>specificity(b)-specificity(a)||b.length-a.length)[0];
        else return '';
      }
      if(!ACTION_SENTENCE.test(q))return '';
      q=q.replace(/[;:,]+$/,'').trim();
      if(!/[.!?]$/.test(q))q+='.';
      return q.charAt(0).toUpperCase()+q.slice(1);
    }
    const fit=v=>!!v&&!GENERIC_RADAR_POINT.test(v)&&!PROCESS_META.test(v)&&!META_WHAT.test(v)&&!titleLike(v)&&ACTION_SENTENCE.test(v)
      &&(isB ? (METHOD.test(v)||METHOD.test(scope)) : ((EU.test(v)||EU.test(scope))&&(RI.test(v)||RI.test(scope))&&(GEO.test(v)||GEO.test(scope))));
    function specificity(v){
      let score=candidateScore(v);
      if(GENERIC_RADAR_POINT.test(v)||PROCESS_META.test(v))score-=80;
      if(/\b(?:tariff|subsid|locali[sz]ation|export control|procurement|screening|retention|post-study|post-research|licen[cs]|standard|acquisition|headquarter|IP|patent|venture capital|funding|grant|compute|fab|factory|supply|repository|database|biobank|doctoral|researcher|R&D|knowledge exchange|science diplomacy)\w*/i.test(v))score+=5;
      if(/[€$£]\s?\d|\b\d+(?:\.\d+)?\s?(?:%|bn|billion|million|GW|MW|months?|years?)\b/i.test(v))score+=5;
      if(/\b(?:China|Chinese|US|United States|EU|Europe|European|Ukraine|Russia|India|Japan|Taiwan|NATO|Commission|Council|ECB|ERC|MSCA|Horizon Europe|Netherlands|Germany|France|Finland)\b/i.test(v))score+=3;
      if(v.length>=95&&v.length<=MAX_RADAR_CHARS)score+=2;
      return score;
    }
    if(/governance logics and foresight functions/i.test(title)&&/networked and anticipatory governance infrastructure/i.test(scope))
      return 'EU strategic foresight operates as a networked governance infrastructure linking reports, ESPAS, the EU-wide Foresight Network, Better Regulation tools and resilience dashboards, rather than as isolated forecasting.';

    if(/European Commission updates EIC Fund Investment Guidelines/i.test(title)&&/Eligible applicants under the EIC Accelerator/i.test(scope))
      return 'EIC Accelerator equity targets highly innovative SMEs and small mid-caps established in EU Member States or Horizon Europe associated countries, typically with a strong intellectual-property component.';
    if(/Fifth Freedom in (?:the )?European Research Area|Insights from Researchers on the Fifth Freedom/i.test(title)&&/researcher|research managers|moving and working across Europe/i.test(scope))
      return "Surveyed researchers identify barriers to moving and working across Europe and support formal recognition of an EU 'Fifth Freedom' to improve research mobility and knowledge circulation.";
    const pool=[];
    const add=(raw,bonus=0)=>{const p=radarCandidate(raw);if(fit(p)&&likelyEnglish(p))pool.push({p,score:specificity(p)+bonus});};

    // Source text first. This prevents a stored legacy slogan from outranking an actual finding.
    for(const q of splitSentences(x?.summary||''))add(q,15);
    for(const q of splitSentences(x?.source_review_basis||''))add(q,8);
    for(const q of (Array.isArray(x?.eu_evidence)?x.eu_evidence:[]))add(q,6);
    for(const q of (Array.isArray(x?.ri_evidence)?x.ri_evidence:[]))add(q,6);
    for(const q of (Array.isArray(x?.geo_evidence)?x.geo_evidence:[]))add(q,6);
    add(x?.why_it_matters,4);
    add(x?.core_message,1);
    add(x?.what,1);
    add(x?.signal_note,1);
    add(pointFor(x),0);
    add(fallbackPoint(x),-3);

    pool.sort((a,b)=>b.score-a.score||b.p.length-a.p.length);
    if(pool[0]?.p)return pool[0].p;

    // Last resort is bibliographically specific rather than a reusable geopolitical slogan.
    if(x?.headline){
      const h=repairOcr(x.headline).replace(/[.!?]+$/,'').trim();
      let m=h.match(/^(.+?):\s*Funding opportunities to boost\s+(.+)$/i);
      if(m)return `${m[1]} offers funding to boost ${m[2]}.`;
      if(/EuroCC 3 and CASTIEL 3/i.test(h)&&/National Competence Centres for HPC/i.test(h))return 'EuroCC 3 and CASTIEL 3 continue support for Europe’s network of national HPC competence centres.';
      if(h&&h.length<=MAX_RADAR_CHARS-2)return `${h}.`;
    }
    const topic=repairOcr(title).replace(/[.!?]+$/,'').trim();
    if(topic&&topic.length<=MAX_RADAR_CHARS-22)return `Source focus: ${topic}.`;
    return '';
  }

  function sourceNavigationBoilerplate(v){
    const n=norm(v);
    return /access to joint research cent(?:re|er)(?: s)? publications|joint research cent(?:re|er) publications repository|browse jrc publications|search jrc publications/.test(n);
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
      if(!q||sourceNavigationBoilerplate(q)||SOURCE_SCAFFOLD.test(q)||GENERIC_WHY.test(q)||BAD_START.test(q)||META.test(q)||isDocumentDebris(q)) return '';
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
    const distinctCandidate=candidates.find(c=>{
      const nq=norm(c.q);
      if(!nq||nq===whatNorm||nq===titleNorm) return false;
      const wt=new Set(whatNorm.split(' ').filter(t=>t.length>4));
      const qt=nq.split(' ').filter(t=>t.length>4);
      const overlap=qt.length?qt.filter(t=>wt.has(t)).length/qt.length:0;
      return overlap<.9;
    });
    if(distinctCandidate) return distinctCandidate.q;

    // When a record has only one usable source sentence, explain the concrete mechanism
    // instead of repeating that sentence or leaving an empty "Why it matters" line.
    const all=norm([title,x?.bibliographicTitle,x?.summary,x?.abstract,x?.core_message,x?.coreMessage,x?.matrix_evidence_basis,x?.matrixEvidenceBasis,x?.relevance_note,x?.watch_theme,x?.theme].join(' '));
    const bibliographic=norm([title,x?.bibliographicTitle,x?.core_message,x?.coreMessage,what].join(' '));
    const primary=norm([title,x?.bibliographicTitle,what,x?.core_message,x?.coreMessage].join(' '));
    const mechanism=(()=>{
      if(/circular economy|resource efficiency|recycl|secondary raw material/.test(bibliographic)) return 'Reuse and substitution can reduce Europe’s exposure to imported materials and vulnerable industrial inputs.';
      if(/cbdc|central bank digital|digital euro|monetary infrastructure|prudential policy/.test(bibliographic)) return 'Technical standards, cyber resilience and governance determine who controls critical European payment infrastructure.';
      if(String(x?.strand||'').toUpperCase()==='B'||/foresight|horizon scan|weak signal|scenario planning|backcasting/.test(primary)){
        if(/weak signal/.test(primary)) return 'Weak-signal methods matter because they can surface emerging strategic change before it becomes an established trend.';
        if(/horizon scan/.test(primary)) return 'Horizon scanning can connect early evidence to emerging risks before policy choices become difficult to reverse.';
        if(/scenario/.test(primary)) return 'Scenario methods matter because they let decision-makers test R&I choices against several plausible strategic futures.';
        if(/backcasting/.test(primary)) return 'Backcasting links a desired long-term research position to decisions that must be taken earlier.';
        return 'Foresight methods matter because they make uncertain strategic change testable before it becomes a settled trend.';
      }
      if(/china|chinese/.test(primary)&&/technology|innovation|research|science/.test(primary)) return 'EU–China technology ties matter because de-risking can narrow collaboration while leaving asymmetric dependencies in place.';
      if(/itu ai ml challenge|application inference from packet flows/.test(primary)) return 'Shared international benchmarks can influence European methods and standards for artificial-intelligence network analysis.';
      if(/eurocc|castiel/.test(primary)) return 'National competence centres give researchers local routes to European supercomputers, training and specialist support.';
      if(/high performance computing|hpc/.test(primary)) return 'Shared computing centres give European researchers wider access to supercomputers, training and specialist support.';
      if(/research.?security|knowledge.?security|foreign interference/.test(primary)) return 'Research-security rules change who European researchers can work with and what knowledge can cross borders.';
      if(/artificial intelligence| ai |ai-|ai4s|machine learning/.test(` ${all} `)) return 'AI policy, capital and infrastructure affect whether European researchers and firms can build and govern frontier capability.';
      if(/patent|intellectual property|\bip\b/.test(primary)) return 'IP rules affect who captures value from European research and how technology can be transferred, licensed or reused.';
      if(/trade|market access|capital inflow|investment asymmetry|foreign investment|economic integration|global value chain/.test(primary)) return 'Trade and investment conditions affect whether European technology can attract capital, reach markets and scale at home.';
      if(/academic cooperation|higher education|university cooperation|education area|knowledge flow/.test(primary)) return 'Academic cooperation affects Europe’s access to research partners, knowledge flows, skills and international networks.';
      if(/tech sovereignty|technology sovereignty|technological sovereignty|strategic autonomy|self-reliance|self reliance|external dependence|technological dependence/.test(primary)) return 'Technology-sovereignty choices trade off external access, domestic control and the cost of substituting foreign capability.';
      if(/brain drain|brain gain|researcher mobility|research talent|scientific talent|research workforce|doctoral|postdoctoral/.test(primary)) return 'Researcher mobility changes the scientific skills and capacity available to European labs and universities.';
      if(/semiconductor|microchip|chips act| chip /.test(` ${all} `)) return 'Chip access and production determine whether European R&I can use critical hardware without external restrictions.';
      if(/compute|supercomput|cloud|ai factory|frontier ai|foundation model/.test(primary)) return 'Compute access determines whether European teams can train and deploy frontier AI without relying on foreign providers.';
      if(/quantum/.test(primary)) return 'Quantum capability affects whether Europe can keep strategic research, infrastructure and industrial know-how at the frontier.';
      if(/critical raw material|critical mineral|rare earth|battery|advanced material/.test(primary)) return 'Strategic-material access affects whether European clean-tech and advanced manufacturing can scale without supply disruption.';
      if(/circular economy|resource efficiency|recycl|secondary raw material/.test(primary)) return 'Reuse and substitution can reduce Europe’s exposure to imported materials and vulnerable industrial inputs.';
      if(/cbdc|central bank digital|digital euro|monetary infrastructure|prudential policy/.test(primary)) return 'Technical standards, cyber resilience and governance determine who controls critical European payment infrastructure.';
      if(/venture capital|scale-up|scaleup|startup|start-up|late-stage|listing|headquarter/.test(primary)) return 'Scale-up finance affects whether European firms keep headquarters, IP, talent and high-value jobs in Europe.';
      if(/dual.?use|defen[cs]e|military/.test(primary)) return 'Dual-use policy redirects R&I funding and can add security, export-control and openness constraints.';
      if(/horizon europe|fp10|framework programme|erc|msca|eic|research funding|funding programme/.test(primary)) return 'Funding and eligibility rules determine which European capabilities and international research partnerships can be sustained.';
      if(/science diplomacy|research collaboration|scientific collaboration|international cooperation|cooperation|partnership/.test(primary)) return 'Partnership choices determine which research networks, facilities, expertise and markets remain accessible to Europe.';
      if(/economic security|reactive assertiveness|de-risking|derisking/.test(primary)) return 'Screening and controls can protect strategic capability while narrowing European access to partners, knowledge and markets.';
      if(/productivity gap|r&d and equity|equity finance|r&d investment/.test(primary)) return 'Productivity gaps matter because weak R&D investment and shallow growth capital make it harder for European firms to commercialise and scale research.';
      if(/standard|regulat|governance|directive|liability|rule-setting|rule setting|export control|screening/.test(primary)) return 'Rules and standards determine whether Europe shapes technology markets or adapts to regimes set elsewhere.';
      if(/radio astronomy|astronomy|telescope|observatory/.test(primary)) return 'European astronomy depends on continued access to international facilities, spectrum, research networks and external partners.';
      if(/data space|interoperab|research infrastructure|infrastructure|federat|data reuse/.test(primary)) return 'Infrastructure and data rules determine whether European researchers can access and reuse shared assets across borders.';
      if(/cyber|digital sovereignty|digital identity|platform|telecom|5g|6g/.test(primary)) return 'Digital and cyber choices affect Europe’s control over research data, infrastructure and critical technology services.';
      if(/industrial policy|industrial|industry|manufactur|productivity|commerciali|innovation ecosystem|innovation capacity|innovation policy|procurement|electric vehicle/.test(primary)) return 'Industrial-policy choices affect whether European research turns into domestic production, scale and strategic capability.';
      if(/biotech|pharma|health|medical|biobank/.test(primary)) return 'Health and biotech rules affect cross-border research, technology transfer and access to data, trials and markets.';
      if(/energy|climate|clean tech|cleantech|renewable|nuclear|hydrogen/.test(primary)) return 'Energy and clean-tech capability affects the cost and resilience of Europe’s research and industrial transition.';
      if(/geoeconomic|geoeconom/.test(primary)) return 'Geoeconomic tools matter because screening, subsidies and trade measures only create leverage when EU institutions and member states can act coherently.';
      if(/polish universit|neo-nationalism|higher education.*poland/.test(primary)) return 'Geopolitical mobilisation can change university autonomy, international openness and the direction of publicly funded research.';
      if(/fintech|digital transition.*eastern europe/.test(primary)) return 'Geopolitical shocks can change regional access to capital, digital infrastructure and innovation investment.';
      if(/draghi|central europe.*competitiveness/.test(primary)) return 'Competitiveness gaps matter because weak innovation investment and fragmented implementation can keep strategic-autonomy policy from producing scale.';
      if(/three seas|eurasian hinge/.test(primary)) return 'Cross-border infrastructure initiatives matter because they can redirect research, technology and investment links between Europe and neighbouring regions.';
      if(/diaspora/.test(primary)) return 'Scientific diasporas matter because they move expertise, collaboration and science-diplomacy links across national research systems.';
      if(/green supply chain/.test(primary)) return 'Innovation, finance and institutional quality determine how well European production absorbs external supply shocks.';
      if(/arctic.*technolog|technological capabilities.*arctic/.test(primary)) return 'Specialised Arctic know-how can translate European scientific capability into strategic influence and alliance value.';
      if(/hrm knowledge transfer|knowledge transfer.*multinational/.test(primary)) return 'Multinational firms can spread skills and organisational capability across European innovation systems through cross-border knowledge transfer.';
      if(/intellectual services.*ukraine|ukraine.*export model/.test(primary)) return 'Knowledge-intensive exports matter because human capital, R&D services and IP commercialisation determine how much innovation value is retained in the region.';
      if(/strategic resilience.*integration bloc|integration blocs.*fragmentation/.test(primary)) return 'Exposure to sanctions and value-chain shocks determines how reliably research and technology capabilities can be supplied.';
      return 'European R&I is affected through the paper’s evidence on capability, access, cost, coordination or external dependence.';
    })();
    const rawTag=repairOcr(title||what||'').replace(/\s+[–—-]\s+[^–—-]{2,40}$/,'').trim();
    let tag=rawTag;
    if(tag.length>58){tag=tag.slice(0,59).replace(/\s+\S*$/,'').trim();}
    if(tag && norm(tag)!==whatNorm){
      return `${mechanism.replace(/[.!?]+$/,'')}; in this paper, that mechanism is evidenced through “${tag}”.`;
    }
    return mechanism;
  }


  function whyYouShouldCare(x){
    let direct=clean(whyFor(x)||'').replace(/;\s*in this paper,[\s\S]*$/i,'.');
    const IMPACT=/\b(?:matter|affect|determin|shape|change|shift|depend|reli|risk|expos|constrain|limit|restrict|delay|weaken|strengthen|increase|reduce|raise|lower|cost|capacity|capabilit|access|control|compet|collabor|cooperat|partner|fund|invest|scale|supply|security|sovereign|autonom|resilien|fragment|leak|transfer|mobility|talent|skill|deploy|coordina|standard|govern|regulat|market|production|manufactur|infrastructure|compute|knowledge|research|innovation|technology|trade|procurement|shortage|gap|screen|protect)\w*/i;
    if(direct&&IMPACT.test(direct)) return direct;

    const n=norm(`${x?.title||x?.headline||''} ${x?.summary||''} ${x?.core_message||''} ${x?.watch_theme||''}`);
    if(/venture capital|scale-up|scaleup|eic accelerator|step scaleup|startup|start-up|late-stage|listing/.test(n))
      return 'Scale-up finance affects whether European deep-tech firms keep IP, talent, ownership and growth in Europe.';
    if(/research security|knowledge security|foreign interference|espionage/.test(n))
      return 'Research-security rules affect who European researchers can work with and what knowledge can cross borders.';
    if(/brain drain|brain gain|researcher mobility|research talent|scientific talent|doctoral|postdoctoral/.test(n))
      return 'Researcher mobility changes the skills and scientific capacity available to European labs and universities.';
    if(/semiconductor|microchip|chips act| chip /.test(` ${n} `))
      return 'Chip access and production determine whether European R&I can use critical hardware without external restrictions.';
    if(/compute|supercomput|cloud|ai factory|frontier ai|foundation model|artificial intelligence| ai /.test(` ${n} `))
      return 'AI and compute access affect whether European teams can build, train and govern frontier technology without foreign bottlenecks.';
    if(/quantum/.test(n))
      return 'Quantum capability affects whether Europe can retain strategic research, infrastructure and industrial know-how.';
    if(/critical raw material|critical mineral|rare earth|battery|advanced material/.test(n))
      return 'Strategic-material access affects whether European clean-tech and advanced manufacturing can scale reliably.';
    if(/dual.?use|defen[cs]e|military/.test(n))
      return 'Dual-use policy can build strategic capability while adding security, export-control and openness constraints.';
    if(/horizon europe|fp10|framework programme|erc|msca|research funding|funding programme/.test(n))
      return 'Funding and eligibility rules determine which European capabilities and international research partnerships can be sustained.';
    if(/science diplomacy|research collaboration|scientific collaboration|international cooperation|partnership/.test(n))
      return 'Partnership choices determine which research networks, facilities, expertise and markets remain accessible to Europe.';
    if(/standard|regulat|directive|rule-setting|rule setting|export control|screening/.test(n))
      return 'Rules and standards determine whether Europe shapes technology markets or adapts to regimes set elsewhere.';
    if(/industrial policy|industrial|industry|manufactur|productivity|commerciali|innovation ecosystem|procurement/.test(n))
      return 'Industrial-policy choices affect whether European research turns into domestic production, scale and strategic capability.';
    if(/data space|interoperab|research infrastructure|federat|data reuse/.test(n))
      return 'Infrastructure and data rules determine whether European researchers can access and reuse shared assets across borders.';
    if(/cyber|digital sovereignty|digital identity|platform|telecom|5g|6g/.test(n))
      return 'Digital and cyber choices affect Europe’s control over research data, infrastructure and critical technology services.';
    if(/energy|climate|clean tech|cleantech|renewable|nuclear|hydrogen/.test(n))
      return 'Energy and clean-tech capability affects the cost and resilience of Europe’s research and industrial transition.';
    return direct||'The source matters because it changes European capability, access, cost, coordination or external dependence.';
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

  return {TOPICS,OTHER,topicFor,pointFor,whatForEuRiGeo,whyFor,whyYouShouldCare,fallbackPoint,plainLanguagePoint,fastReaderText,readText,matrixText,radarText,readerPoint,buildInsights,buildSignals,buildResearchInsights,signalWhat,signalWhy,signalTheme,concise,isDocumentDebris,prepareSummary,candidateScore,structuredPoint,likelyEnglish,completeCoreMessage};
});
