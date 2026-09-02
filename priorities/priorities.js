(function(root,factory){
  if(typeof module==='object'&&module.exports) module.exports=factory(require('../briefing/insights.js'));
  else root.RadarPriorities=factory(root.RadarInsights);
})(typeof globalThis!=='undefined'?globalThis:this,function(Insights){
  'use strict';

  function clean(v){return String(v||'').replace(/\s+/g,' ').trim()}
  function norm(v){return clean(v).toLowerCase().replace(/[–—]/g,'-').replace(/[^a-z0-9+.#/&'€$-]+/g,' ').replace(/\s+/g,' ').trim()}
  function dateValue(v){const t=Date.parse(clean(v));return Number.isFinite(t)?t:0}
  function titleFor(x){return clean(x?.headline||x?.title||x?.what||x?.core_message||'')}
  function sourceFor(x){return clean(x?.source||x?.authors||'')}
  function linkFor(x){return clean(x?.link||'')}
  function coreFor(x){return clean(x?.what||x?.core_message||x?.reader_point||x?.summary||x?.signal_note||titleFor(x))}
  function firstMatch(text,patterns){for(const p of patterns){const m=text.match(p);if(m)return clean(m[0])}return ''}
  function any(text,patterns){return !!firstMatch(text,patterns)}

  /*
   * ANALYTICAL LAYER, NOT SCANNER SPECIFICATION
   * -------------------------------------------
   * The scanner decides what to research and retain.  This reader may then interpret
   * retained evidence for analytical products.  These tests never inspect Matrix cells
   * and never prescribe source discovery, rotation, admission or rejection upstream.
   *
   * A scanner-filed source-text lens remains authoritative.  When no such lens exists,
   * the repository can make a conservative item-level interpretation from the evidence
   * text and metadata retained by the scanner.  The page identifies that basis.
   */

  const RISK_MECHANISM=[
    /\bcould (?:restrict|revoke|deny|cut off|withhold|block|ban|limit)\b/i,
    /\bwould (?:deny|cut off|restrict|block|limit)\b/i,
    /\bmay be withheld\b/i,/\bsubject to (?:licen[cs]e|approval)\b/i,/\bconditional on\b/i,
    /\bat the discretion of\b/i,/\bcan be weaponi[sz]ed\b/i,/\bcould be extended to\b/i,
    /\bextraterritorial(?: reach|-law)?\b/i,/\bsecondary sanctions?\b/i,/\bcatch-all clause\b/i,
    /\btermination for convenience\b/i,/\bswitching costs?\b/i,/\block-in\b/i,
    /\blong qualification times?\b/i,/\bno substitute available\b/i,/\bno alternative supplier\b/i,
    /\bproposed .{0,45}restrictions?\b/i,/\bexport controls?\b/i,/\bgrant restrictions?\b/i,
    /\bforeign interference\b/i,
  ];
  const RISK_CARRIER=[
    /\bunder review by\b/i,/\bcontrolled by\b/i,/\brequires approval from\b/i,/\bsubject to .{0,45} jurisdiction\b/i,
    /\bon the entity list\b/i,/\bdesignated\b/i,/\bstate-linked\b/i,/\bmilitary-affiliated\b/i,
    /\bforeign interference\b/i,/\btalent recruitment by\b/i,/\bcoercion\b/i,/\bleverage over\b/i,/\bpressure to align\b/i,
    /\b(?:white house|u\.s\.|united states|china|chinese|russia|russian|india|canada|united kingdom|uk government)\b/i,
    /\b(?:government|regulator|authority|supplier|provider|platform operator|cloud provider)\b/i,
    /\bnon-european .{0,30}(?:supplier|provider|company|firm)s?\b/i
  ];
  const RISK_ASSET=[
    /\bdependent on .{0,80} for\b/i,/\breliant on imports? of\b/i,/\bno domestic capacity\b/i,/\bsingle source\b/i,/\bsole supplier\b/i,
    /\bconcentrated (?:in|computing capacity)\b/i,/\bmonopoly risk\b/i,/\bbottleneck\b/i,/\bchokepoint\b/i,/\berosion of\b/i,
    /\bhollowing out\b/i,/\bloss of control over\b/i,/\bbrain drain\b/i,/\brelocation of\b/i,/\bforeign ownership of\b/i,
    /\bstrategic dependenc(?:y|ies)\b/i,/\bexposure to retaliation\b/i,/\bdependence on .{0,80}(?:supplier|provider|cloud|technology|imports?)\b/i,
    /\b(?:research collaboration|academic freedom|research access|research capacity|talent pool|research talent|data flow|computing capacity|cloud and ai infrastructure|supply chain|technology access|equipment|knowledge|semiconductor supply|critical raw material supply)\b/i
  ];
  const RISK_FORWARD=[
    /\b(?:could|would|may|might|can)\b/i,/\bproposed\b/i,/\bunder review\b/i,/\bsubject to\b/i,/\bat the discretion\b/i,
    /\block-in\b/i,/\bextraterritorial\b/i,/\bno substitute\b/i,/\bno alternative supplier\b/i,/\bdependence\b/i,/\bdependency\b/i
  ];

  const OPP_MECHANISM=[
    /\bcould leverage\b/i,/\bcan leverage\b/i,/\bcan convert .{0,80} into\b/i,/\bsubstitution potential\b/i,/\brecycling could supply\b/i,
    /\bdemand-side measure\b/i,/\bspillover into\b/i,/\badjacent market\b/i,/\brelatedness to existing strengths\b/i,
    /\bbuilds on installed base\b/i,/\btransferable to\b/i,/\bscalable\b/i,/\bdual-use potential\b/i,/\bnetwork effects favour\b/i,
    /\b(?:call|programme|program|fund|initiative)(?: [A-Z0-9_-]{3,})? aims? (?:to|at) (?:strengthen|build|support|expand|accelerate|develop|establish|establishing)\b/i,
    /\b(?:will|can|could) (?:help |allow |enable )?(?:strengthen|build|secure|expand|scale|attract|retain|develop|establish|provide)\b/i,
    /\bprovide(?:s|d)? .{0,50}(?:funding|investment|access|support)\b/i,/\bpresented upcoming opportunities? under\b/i,/\bopen-access .{0,40}(?:infrastructure|facility)\b/i
  ];
  const OPP_ACTOR=[
    /\beuropean commission\b/i,/\beuropean innovation council\b/i,/\beic\b/i,/\beurohpc(?: joint undertaking)?\b/i,
    /\bhorizon europe\b/i,/\bmarie skłodowska-curie actions\b/i,/\bmsca\b/i,/\beuropean research council\b/i,/\berc\b/i,
    /\beuropean investment bank\b/i,/\beib\b/i,/\bbusiness finland\b/i,/\b(?:national|federal) government\b/i,
    /\bministry of [a-z -]+\b/i,/\bgovernment of [a-z -]+\b/i,/\bmember states?\b/i,
    /\b[a-z][a-z&.-]+ (?:agency|authority|council|fund|foundation|joint undertaking)\b/i
  ];
  const OPP_INSTRUMENT=[
    /\bexisting instrument\b/i,/\blegal basis already exists\b/i,/\bno new legislation required\b/i,/\bprocurement could\b/i,
    /\bconditionality attached to\b/i,/\beligibility criteria allow\b/i,/\bassociation agreement\b/i,/\bco-funding available\b/i,
    /\bcall open until\b/i,/\bdesignation as strategic project\b/i,/\bfast-track\b/i,/\bregulatory sandbox\b/i,/\bpilot line\b/i,
    /\banchor customer\b/i,/\blaunch customer\b/i,/\bhorizon europe\b/i,/\beic\b/i,/\berc\b/i,/\bmsca\b/i,/\beurohpc\b/i,
    /\b(?:funding|investment) (?:programme|program|instrument|facility|call|scheme)\b/i,/\bwork programme\b/i,/\bopen call\b/i,
    /\bcall [A-Z0-9_-]{5,}\b/i,/\b€\s?\d[\d.,]*\s?(?:million|billion)?\b/i,/\beur\s?\d[\d.,]*\s?(?:million|billion)?\b/i
  ];
  const OPP_GAIN=[
    /\b(?:strengthen|secure|build|expand|increase|improve|accelerate|develop|establish|attract|retain|scale|boost) .{0,90}(?:capacity|capabilit|autonomy|resilience|competitiveness|leadership|innovation|research|technology|talent|supply|access|infrastructure|ecosystem|collaboration)\b/i,
    /\b(?:capacity|capability|autonomy|resilience|competitiveness|leadership|talent|investment|innovation)\b/i
  ];
  const OPP_WINDOW=[
    /\b(?:status )?open\b/i,/\bopening date\b/i,/\bdeadline(?: date)?\b/i,/\bopen until\b/i,/\bapply\b/i,/\bapplications?\b/i,
    /\bupcoming opportunities?\b/i,/\b2026[–-]2027\b/i,/\bcall(?:s)? launched\b/i,/\bnew (?:call|programme|program|fund|initiative)\b/i,
    /\bavailable for (?:this|the) call\b/i,/\bbudget available for (?:this|the) call\b/i,/\bfunding (?:is )?available\b/i,/\bcurrently open\b/i
  ];
  const OPP_BASELINE=[/\badopted\b/i,/\bentered into force\b/i,/\btook effect\b/i,/\bselected\b/i,/\bapproved\b/i,/\bnow funds\b/i];
  const OPP_NOISE=[/\bhas the potential to\b/i,/\bcould become a global leader\b/i,/\bvision for\b/i,/\bambition to\b/i,/\baspires to\b/i,/\bmust seize\b/i,/\bcalls for bold action\b/i,/\bunprecedented opportunity\b/i,/\broadmap towards\b/i];

  const SHOCK_FAMILIES=[
    {id:'natural_disaster',label:'Natural disasters',patterns:[/\bearthquake\b/i,/\btsunami\b/i,/\bvolcan(?:ic|o|ic eruption)\b/i,/\blandslide\b/i,/\b(?:major |severe )?(?:flood|wildfire|hurricane|typhoon|cyclone|storm)\b/i]},
    {id:'pandemic_epidemic',label:'Pandemics and epidemics',patterns:[/\bpandemic\b/i,/\bepidemic\b/i,/\bdisease outbreak\b/i,/\boutbreak of .{0,35}(?:virus|disease|infection)\b/i]},
    {id:'armed_conflict',label:'Armed conflicts',patterns:[/\barmed conflict\b/i,/\binvasion\b/i,/\bwar (?:in|between|against)\b/i,/\bhostilities\b/i,/\bmilitary (?:strike|attack|offensive)\b/i,/\bmissile strike\b/i]},
    {id:'terrorist_attack',label:'Terrorist attacks',patterns:[/\bterrorist attack\b/i,/\bterror attack\b/i,/\bterrorism-related attack\b/i]},
    {id:'financial_crisis',label:'Global financial crises',patterns:[/\bglobal financial crisis\b/i,/\bbanking crisis\b/i,/\bfinancial crisis\b/i,/\bmarket crash\b/i,/\bliquidity crisis\b/i,/\bcredit crunch\b/i]},
    {id:'commodity_price',label:'Commodity price shocks',patterns:[/\bcommodity price (?:shock|spike|surge|collapse)\b/i,/\b(?:oil|gas|metal|copper|lithium|nickel|rare earth) prices? (?:doubled|spiked|surged|collapsed)\b/i,/\bspot price spiked\b/i]},
    {id:'energy_supply',label:'Energy supply disruptions',patterns:[/\benergy supply (?:disruption|cut|interruption)\b/i,/\b(?:gas|oil|electricity|power) supply (?:was |were )?(?:cut|halted|suspended|disrupted)\b/i,/\bblackout\b/i,/\bpower outage\b/i,/\bpipeline (?:shut|closed|ruptured|severed)\b/i]},
    {id:'food_supply',label:'Food supply shocks',patterns:[/\bfood supply (?:shock|disruption)\b/i,/\bgrain (?:export|supply) (?:ban|halt|disruption)\b/i,/\bwheat (?:export|supply) (?:ban|halt|disruption)\b/i,/\bfertiliser supply (?:cut|disruption)\b/i]},
    {id:'trade_disruption',label:'Trade disruptions',patterns:[/\btrade (?:disruption|halt|interruption)\b/i,/\bexport ban\b/i,/\bimport ban\b/i,/\bexport control list\b/i,/\bembargo\b/i,/\bcustoms (?:closure|halt|blockage)\b/i]},
    {id:'supply_chain',label:'Supply chain disruptions',patterns:[/\bsupply chain (?:disruption|interruption|breakdown)\b/i,/\bshipping (?:disruption|halt|interruption)\b/i,/\bport (?:closure|shutdown|blockage)\b/i,/\blogistics (?:disruption|halt)\b/i,/\bshipment(?:s)? (?:halted|blocked|stranded)\b/i]},
    {id:'currency_crisis',label:'Currency crises',patterns:[/\bcurrency crisis\b/i,/\bexchange-rate crisis\b/i,/\bcurrency (?:collapsed|plunged)\b/i,/\bdevaluation of \d/i,/\bcapital controls? (?:were )?imposed\b/i]},
    {id:'sanctions',label:'International sanctions',patterns:[/\binternational sanctions?\b/i,/\bsecondary sanctions?\b/i,/\b(?:u\.s\.|united states|china|russia|uk|united kingdom) sanctions?\b/i,/\bsanctions? (?:were )?(?:imposed|took effect|entered into force)\b/i,/\bblacklisted\b/i]},
    {id:'migration_refugee',label:'Migration and refugee surges',patterns:[/\brefugee (?:surge|influx|wave)\b/i,/\bmigration (?:surge|influx|wave)\b/i,/\bmass displacement\b/i]},
    {id:'cyberattack',label:'Cyberattacks',patterns:[/\bcyberattack\b/i,/\bcyber attack\b/i,/\bransomware attack\b/i,/\bmajor data breach\b/i,/\bbreach detected\b/i,/\bdistributed denial.of.service\b/i,/\bddos attack\b/i]},
    {id:'technological_disruption',label:'Technological disruptions',patterns:[/\btechnological disruption\b/i,/\btechnology disruption\b/i,/\bcloud (?:outage|failure)\b/i,/\bplatform (?:outage|failure)\b/i,/\bsoftware (?:outage|failure)\b/i,/\bcritical system (?:outage|failure)\b/i]},
    {id:'climate_shock',label:'Climate-related shocks',patterns:[/\bclimate-related shock\b/i,/\bextreme heat\b/i,/\bheatwave\b/i,/\bsevere drought\b/i,/\bextreme weather event\b/i]},
    {id:'neighboring_instability',label:'Political instability in neighboring regions',patterns:[/\bpolitical instability (?:in|across)\b/i,/\bgovernment (?:fell|collapsed)\b/i,/\bcoup(?: d['’]etat)?\b/i,/\bsnap election\b/i,/\bstate of emergency\b/i]},
    {id:'foreign_investment_withdrawal',label:'Sudden foreign investment withdrawal',patterns:[/\bforeign investment (?:withdrawal|pulled out|was withdrawn)\b/i,/\bforeign investors? (?:withdrew|pulled out|exited)\b/i,/\bsudden capital flight\b/i,/\binvestment (?:was )?withdrawn abruptly\b/i]},
    {id:'global_demand',label:'Global demand shocks',patterns:[/\bglobal demand shock\b/i,/\bglobal demand (?:collapsed|plunged|fell sharply)\b/i,/\borders? (?:collapsed|plunged)\b/i,/\bdemand (?:collapsed|plunged) overnight\b/i]},
    {id:'infrastructure',label:'Major infrastructure disruptions',patterns:[/\bmajor infrastructure (?:disruption|failure)\b/i,/\bsubsea cable (?:cut|severed|damaged)\b/i,/\bcable (?:cut|severed)\b/i,/\bbridge collapse\b/i,/\brail (?:shutdown|closure)\b/i,/\bairport (?:shutdown|closure)\b/i,/\bgrid (?:failure|collapse)\b/i,/\bfacility (?:shut down|went offline)\b/i]}
  ];
  const SHOCK_DISCRETE=[
    /\bwith immediate effect\b/i,/\beffective immediately\b/i,/\bas of \d{1,2} [a-z]+ 20\d{2}\b/i,/\bentered into force\b/i,/\btook effect\b/i,
    /\bsuspended\b/i,/\bhalted\b/i,/\bshut down\b/i,/\bwent offline\b/i,/\bdeclared force majeure\b/i,/\bwithout prior notice\b/i,/\babruptly\b/i,/\bunannounced\b/i,/\bovernight\b/i,
    /\b(?:earthquake|hurricane|typhoon|cyclone|tsunami|wildfire|flood|storm) (?:struck|hit)\b/i,/\b(?:war|hostilities|fighting) (?:erupted|broke out)\b/i,
    /\b(?:cyberattack|cyber attack|terrorist attack|military strike|missile strike) (?:hit|struck|disabled|disrupted)\b/i,/\bgovernment (?:fell|collapsed)\b/i,/\bcoup\b/i
  ];
  const SHOCK_EVENT=[
    /\bcut off\b/i,/\bblocked\b/i,/\bblacklisted\b/i,/\brevoked licen[cs]es?\b/i,/\bexport ban\b/i,/\bimport ban\b/i,/\bexport control list\b/i,/\bbarring .{0,50}exports?\b/i,
    /\bembargo\b/i,/\bquota imposed\b/i,/\ballocation cut\b/i,/\brationing\b/i,/\bseized\b/i,/\bimpounded\b/i,/\bexpelled\b/i,
    /\bdetained\b/i,/\barrested\b/i,/\braided\b/i,/\boutage\b/i,/\bstrike on\b/i,/\bsabotage of\b/i,/\bsevered\b/i,
    /\bprice doubled\b/i,/\bprices? spiked\b/i,/\btrading halted\b/i,/\bdefault\b/i,/\bfiled for bankruptcy\b/i,/\bcollapsed\b/i,
    /\bvetoed\b/i,/\bfailed to ratify\b/i,/\bborders closed\b/i,/\bstrait closed\b/i,/\bairspace closed\b/i,
    /\b(?:earthquake|hurricane|typhoon|cyclone|tsunami|wildfire|flood|storm) (?:struck|hit)\b/i,/\b(?:cyberattack|cyber attack|terrorist attack|military strike|missile strike)\b/i,
    /\b(?:pandemic|epidemic|outbreak) (?:was declared|erupted|spread)\b/i,/\b(?:power|cloud|platform|network|grid) (?:outage|failure)\b/i,/\bgovernment (?:fell|collapsed)\b/i,/\bcoup\b/i
  ];
  const SHOCK_EXTERNAL_ACTOR=[
    /\b(?:china|chinese|united states|u\.s\.|white house|russia|russian|india|canada|united kingdom|uk government|japan|south korea|taiwan|iran)\b/i,
    /\bforeign (?:government|authority|regulator|state|investor|company|supplier)\b/i,/\bnon-eu (?:government|authority|company|supplier|investor)\b/i
  ];
  const SHOCK_SYSTEMIC_EXTERNAL=[
    /\b(?:earthquake|tsunami|volcan(?:ic|o)|landslide|hurricane|typhoon|cyclone|wildfire|flood|storm|heatwave|extreme heat|severe drought)\b/i,
    /\b(?:pandemic|epidemic|disease outbreak)\b/i,/\b(?:terrorist attack|cyberattack|cyber attack|ransomware attack)\b/i,
    /\b(?:global financial crisis|banking crisis|market crash|commodity price shock|currency crisis|global demand shock)\b/i,
    /\b(?:war|armed conflict|invasion|hostilities|military strike|missile strike)\b/i,/\b(?:power outage|blackout|grid failure|cloud outage|subsea cable)\b/i,
    /\b(?:refugee surge|migration surge|mass displacement)\b/i,/\b(?:supply chain disruption|shipping disruption|port closure)\b/i
  ];
  const SHOCK_EFFECT=[
    /\bbarring .{0,80}(?:exports?|access|entities)\b/i,/\b(?:cut off|blocked|blacklisted|revoked|seized|halted|suspended) .{0,90}(?:access|exports?|imports?|supply|technology|equipment|data|research|entities|firms?|organisations?|operations?|projects?|funding|investment)\b/i,
    /\b(?:eu|european) entit(?:y|ies)\b.{0,90}\b(?:barred|barring|blocked|blacklisted|cut off|suspended|halted|disrupted)\b/i,
    /\b(?:supply|access|operations?|trading|airspace|border|facility|system|laborator(?:y|ies)|university|research infrastructure|data centre|datacenter|network|grid) (?:was|were|is|are|has been|have been) (?:cut off|blocked|halted|suspended|closed|disrupted|disabled|damaged|destroyed|unavailable)\b/i,
    /\b(?:forced|caused|triggered) .{0,100}(?:research|laborator(?:y|ies)|universit(?:y|ies)|facility|infrastructure|project|trial|experiment|production|operations?) .{0,60}(?:to close|to shut down|to suspend|to halt|to stop|closure|shutdown|suspension|delay|disruption)\b/i,
    /\b(?:research|innovation|r&d|laborator(?:y|ies)|universit(?:y|ies)|researchers?|scientists?|projects?|clinical trials?|experiments?|compute|cloud|data|equipment|technology|supply chains?) .{0,80}(?:was|were|has been|have been) (?:halted|suspended|delayed|disrupted|blocked|cut off|displaced|evacuated|damaged|lost|made unavailable)\b/i,
    /\b(?:shortage|shortages|price spike|price surge|cost increase|costs increased|prices increased) .{0,80}(?:equipment|energy|materials?|components?|chips?|semiconductors?|compute|research|laborator(?:y|ies)|production)\b/i,
    /\b(?:funding|investment|capital) .{0,60}(?:was|were|has been|have been) (?:withdrawn|frozen|halted|suspended)\b/i,
    /\b(?:researchers?|scientists?|students?|technical staff) .{0,50}(?:were|have been) (?:displaced|evacuated|stranded|expelled)\b/i,
    /\b(?:disrupted|halted|suspended|blocked|disabled|damaged|destroyed|severed) .{0,80}(?:research|r&d|laborator(?:y|ies)|universit(?:y|ies)|projects?|clinical trials?|experiments?|research data|data access|compute|cloud|network|infrastructure|operations?)\b/i
  ];
  const SHOCK_SPEED=[
    /\bwith immediate effect\b/i,/\beffective immediately\b/i,/\bwithout prior notice\b/i,/\babruptly\b/i,/\bunannounced\b/i,/\bovernight\b/i,
    /\b(?:earthquake|hurricane|typhoon|cyclone|tsunami|wildfire|flood|storm) (?:struck|hit)\b/i,/\b(?:cyberattack|cyber attack|terrorist attack|military strike|missile strike) (?:hit|struck|disabled|disrupted)\b/i,
    /\b(?:went offline|shut down|trading halted|borders closed|airspace closed|government fell|government collapsed)\b/i
  ];
  const INTENTION_ONLY=[/\bplans to\b/i,/\bintends to\b/i,/\bconsiders\b/i,/\bweighs\b/i,/\bmulls\b/i,/\breportedly preparing\b/i,/\bthreatens to\b/i,/\bwarns that\b/i,/\bsignals willingness\b/i,/\bexpected to\b/i,/\bslated for\b/i,/\bon track to\b/i];
  const OWN_EU_SHOCK=/\b(?:european commission|european union|\beu\b|council|member states?)\b.{0,100}\b(?:imposed|adopted|suspended|halted|closed|revoked|blocked|banned)\b/i;

  function shockFamilies(text){
    const t=clean(text);
    if(!t) return [];
    return SHOCK_FAMILIES.filter(f=>any(t,f.patterns)).map(f=>({id:f.id,label:f.label}));
  }

  function primaryShockFamily(text){
    const families=shockFamilies(text);
    return families.length?families[0]:null;
  }

  function evidenceText(x){
    const filed=(x?.strategic_classification_source==='source_text'&&x?.strategic_classification)||null;
    const filedPassages=Array.isArray(filed?.lenses)?filed.lenses.map(v=>clean(v?.passage)).filter(Boolean):[];
    const trendPassage=clean(filed?.trend_action_passage);
    const fields=x?.headline?[x.headline,x.signal_note,x.why_it_matters]:[x?.title,x?.summary,x?.core_message,x?.bridge_sentence];
    return [...filedPassages,trendPassage,...fields.map(clean).filter(Boolean)].filter((v,i,a)=>a.indexOf(v)===i).join(' ');
  }

  function inferredLens(raw,kind,text){
    const t=clean(text); if(!t) return null;
    if(kind==='external_shock'){
      if(!dateValue(raw?.date||raw?.first_seen)||any(t,INTENTION_ONLY)||OWN_EU_SHOCK.test(t)) return null;
      const discrete=firstMatch(t,SHOCK_DISCRETE),event=firstMatch(t,SHOCK_EVENT),effect=firstMatch(t,SHOCK_EFFECT),speed=firstMatch(t,SHOCK_SPEED);
      const actorExternality=firstMatch(t,SHOCK_EXTERNAL_ACTOR),systemicExternality=firstMatch(t,SHOCK_SYSTEMIC_EXTERNAL);
      const externality=actorExternality||systemicExternality;
      if(!(discrete&&event&&externality&&effect&&speed)) return null;
      const families=shockFamilies(t),family=families[0]||null;
      return {type:'external_shock',passage:t.slice(0,1200),shock_family:family?.label||'',shock_family_id:family?.id||'',shock_families:families,components:{discrete,event,externality,effect,speed},analysis_basis:'repository_evidence_interpretation',analysis_score:100};
    }
    if(kind==='risk'){
      const mechanism=firstMatch(t,RISK_MECHANISM),carrier=firstMatch(t,RISK_CARRIER),asset=firstMatch(t,RISK_ASSET),conditional=firstMatch(t,RISK_FORWARD);
      if(!(mechanism&&carrier&&asset&&conditional)) return null;
      return {type:'risk',status:'open',passage:t.slice(0,1200),components:{mechanism,carrier,asset},analysis_basis:'repository_evidence_interpretation',analysis_score:100};
    }
    if(kind==='opportunity'){
      const mechanism=firstMatch(t,OPP_MECHANISM),actor=firstMatch(t,OPP_ACTOR),instrument=firstMatch(t,OPP_INSTRUMENT),gain=firstMatch(t,OPP_GAIN),window=firstMatch(t,OPP_WINDOW);
      if(!(mechanism&&actor&&instrument&&gain&&window)) return null;
      // An adopted measure is baseline unless the same retained evidence also identifies a live/open instrument window.
      if(any(t,OPP_BASELINE)&&!any(t,OPP_WINDOW)) return null;
      // Aspiration is allowed only because all five positive components above independently pass.
      const noise=firstMatch(t,OPP_NOISE);
      return {type:'opportunity',passage:t.slice(0,1200),components:{mechanism,actor,instrument,gain,window},noise_cue:noise||'',analysis_basis:'repository_evidence_interpretation',analysis_score:100};
    }
    return null;
  }

  function scannerLenses(raw){
    const c=raw?.strategic_classification;
    if(!c||typeof c!=='object'||clean(raw?.strategic_classification_source)!=='source_text') return [];
    let lenses=Array.isArray(c.lenses)?c.lenses.filter(x=>x&&typeof x==='object'&&['risk','opportunity','external_shock'].includes(clean(x.type))):[];
    if(!lenses.length&&['risk','opportunity','external_shock'].includes(clean(c.primary))) lenses=[{type:clean(c.primary),passage:''}];
    return lenses.map(l=>{const kind=clean(l.type),family=kind==='external_shock'?primaryShockFamily(`${clean(l.passage)} ${evidenceText(raw)}`):null;return {...l,shock_family:clean(l.shock_family||family?.label||''),shock_family_id:clean(l.shock_family_id||family?.id||''),analysis_basis:'scanner_source_classification',analysis_score:110}});
  }

  function interpretLenses(raw){
    const filed=scannerLenses(raw);
    const kinds=new Set(filed.map(x=>clean(x.type)));
    const t=evidenceText(raw);
    // A realised shock supersedes a conditional risk in the same retained item.
    const inferredShock=!kinds.has('external_shock')?inferredLens(raw,'external_shock',t):null;
    if(inferredShock){
      const withoutRisk=filed.filter(x=>clean(x.type)!=='risk');
      return [...withoutRisk,inferredShock];
    }
    const out=[...filed];
    for(const kind of ['risk','opportunity']) if(!kinds.has(kind)){
      const lens=inferredLens(raw,kind,t); if(lens) out.push(lens);
    }
    return out;
  }

  function topicKey(x){
    const t=norm(`${titleFor(x)} ${coreFor(x)} ${x?.lensPassage||''}`);
    const groups=[
      ['research security',/research security|knowledge security|foreign interference|espionage/],
      ['talent',/research talent|researcher|scientist|brain drain|mobility|doctoral|postdoctoral/],
      ['chips',/semiconductor|chip|microelectronics|accelerator|gpu/],
      ['compute-ai',/compute|cloud|frontier ai|ai factory|foundation model/],
      ['materials',/critical raw|critical mineral|rare earth|battery|materials/],
      ['scale-finance',/venture capital|scale-up|scaleup|startup|investment|capital|listing|headquarter/],
      ['defence-dual-use',/dual-use|dual use|defen[cs]e|military/],
      ['rules-security',/regulat|standard|rule|export control|screening|sanction|licen[cs]e/],
      ['partnerships',/china|united states|india|international|partnership|science diplomacy/],
      ['infrastructure',/infrastructure|facility|laborator|supply chain|supplier|vendor|data flow/],
    ];
    for(const [k,re] of groups) if(re.test(` ${t} `)) return k;
    return 'other';
  }

  function pathwayScore(x){
    const components=x?.lens?.components&&typeof x.lens.components==='object'?Object.values(x.lens.components).filter(Boolean).length:0;
    const basis=clean(x?.lens?.analysis_basis)==='scanner_source_classification'?2:1;
    return (x?.newThisScan?1e15:0)+dateValue(x?.date)*100+(basis*10)+components;
  }

  function diversifiedTop(items,limit,maxPerTopic=2){
    if(limit<=0) return [];
    const out=[],deferred=[],perTopic=new Map();
    for(const x of items){
      const topic=topicKey(x),n=perTopic.get(topic)||0;
      if(n<maxPerTopic&&out.length<limit){out.push(x);perTopic.set(topic,n+1)}else deferred.push(x);
    }
    for(const x of deferred){if(out.length>=limit)break;out.push(x)}
    return out;
  }

  function rawEvidenceItems(data){
    const collections=[
      Array.isArray(data?.strategic_pathways)?data.strategic_pathways:[],
      Array.isArray(data?.strand_a)?data.strand_a:[],
      Array.isArray(data?.strand_b)?data.strand_b:[],
      Array.isArray(data?.frontier_evidence)?data.frontier_evidence:[],
      Array.isArray(data?.strand_c)?data.strand_c:[],
    ];
    const rows=collections.flat().filter(x=>x&&typeof x==='object');
    const byKey=new Map(),unkeyed=[];
    for(const x of rows){
      const key=norm(linkFor(x)||titleFor(x));
      if(!key){unkeyed.push(x);continue}
      const prior=byKey.get(key);
      const weight=y=>scannerLenses(y).length*100+(evidenceText(y).length>0?1:0);
      if(!prior||weight(x)>weight(prior)) byKey.set(key,x);
    }
    return [...byKey.values(),...unkeyed];
  }

  function lensRows(data){
    const out=[];
    for(const raw of rawEvidenceItems(data)){
      const lenses=interpretLenses(raw);
      for(const lens of lenses){
        const kind=clean(lens.type);
        if(!['risk','opportunity','external_shock'].includes(kind)) continue;
        out.push({
          raw,kind,lens,lensPassage:clean(lens.passage),strategicClassification:raw.strategic_classification||{},
          title:titleFor(raw),coreMessage:coreFor(raw),source:sourceFor(raw),date:clean(raw.date||raw.first_seen||''),
          link:linkFor(raw),abstract:clean(raw.summary||raw.signal_note||raw.why_it_matters||''),newThisScan:!!raw.new_this_scan,
          interpretationBasis:clean(lens.analysis_basis),
        });
      }
    }
    return out;
  }

  function sortPathways(items){
    return items.sort((a,b)=>pathwayScore(b)-pathwayScore(a)||String(b.date).localeCompare(String(a.date))||a.title.localeCompare(b.title));
  }

  function buildPriorityView(data,opts={}){
    const limit=Number.isFinite(opts.limit)?Math.max(1,Math.min(50,Math.floor(opts.limit))):10;
    const rows=lensRows(data);
    const closedRisks=rows.filter(x=>x.kind==='risk'&&clean(x.lens?.status)==='closed_into_shock');
    const allRisks=sortPathways(rows.filter(x=>x.kind==='risk'&&clean(x.lens?.status)!=='closed_into_shock'));
    const allOpportunities=sortPathways(rows.filter(x=>x.kind==='opportunity'));
    const externalShocks=sortPathways(rows.filter(x=>x.kind==='external_shock'));
    const sourceFiled=rows.filter(x=>x.interpretationBasis==='scanner_source_classification').length;
    const repositoryInterpreted=rows.filter(x=>x.interpretationBasis==='repository_evidence_interpretation').length;
    return {
      risks:diversifiedTop(allRisks,limit,2),
      opportunities:diversifiedTop(allOpportunities,limit,2),
      externalShocks,
      stats:{
        interpreted:allRisks.length+allOpportunities.length+externalShocks.length,
        sourceFiled,repositoryInterpreted,
        risks:allRisks.length,opportunities:allOpportunities.length,externalShocks:externalShocks.length,
        closedRisks:closedRisks.length,shownRisks:Math.min(limit,allRisks.length),shownOpportunities:Math.min(limit,allOpportunities.length),
      }
    };
  }

  function simplePriorityText(x){
    const raw=clean(x?.coreMessage||x?.title||'');
    return Insights?.readerPoint?.(raw)||Insights?.completeCoreMessage?.(raw)||raw||'The retained evidence does not provide a concise claim.';
  }

  function simpleEvidenceText(x){return clean(x?.title||'')}

  return {buildPriorityView,pathwayScore,diversifiedTop,simplePriorityText,simpleEvidenceText,topicKey,lensRows,interpretLenses,evidenceText,inferredLens,shockFamilies,primaryShockFamily};
});
