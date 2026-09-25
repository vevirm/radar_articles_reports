(function(root,factory){
  if(typeof module==='object'&&module.exports) module.exports=factory(require('../briefing/insights.js'),require('../reader_rank.js'));
  else root.RadarPriorities=factory(root.RadarInsights,root.RadarReaderRank);
})(typeof globalThis!=='undefined'?globalThis:this,function(Insights,ReaderRank){
  'use strict';

  function clean(v){return String(v||'').replace(/\s+/g,' ').trim()}
  function norm(v){return clean(v).toLowerCase().replace(/[–—]/g,'-').replace(/[^a-z0-9+.#/&'€$-]+/g,' ').replace(/\s+/g,' ').trim()}
  function dateValue(v){const t=Date.parse(clean(v));return Number.isFinite(t)?t:0}
  function titleFor(x){return clean(x?.headline||x?.title||x?.what||x?.core_message||'')}
  function sourceFor(x){return clean(x?.source||x?.authors||'')}
  function linkFor(x){return clean(x?.link||'')}
  function qualityScore(x){return Math.max(0,Math.min(100,Number(ReaderRank?.scoreFor?.(x))||0))}
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
    /\bforeign interference\b/i,/\b(?:dependence|dependency|dependencies) (?:on|in)\b/i,
    /\b(?:constrained|limited|exposed|vulnerable) by\b/i,/\bcan constrain\b/i,/\bexternal dominance\b/i,
    /\bmarket concentration\b/i,/\bconcentrated supply\b/i,/\bdifficult substitution\b/i,/\bscarcity\b/i,
    /\b(?:increase|raises?|creates?) .{0,65}(?:costs?|barriers?|exposure|risk)\b/i,/\b(?:disrupt|erode|undermine)s? .{0,65}(?:access|capacity|collaboration|supply|autonomy|competitiveness|research)\b/i,
    /\b(?:barriers?|fragmentation|precarity|scarcity|shortages?) (?:to|in|of)\b/i,/\blimited (?:access|accessibility|availability)\b/i,
    /\bbrain drain\b/i,/\b(?:risk|risks) of .{0,80}(?:dependence|loss|restriction|disruption|erosion|transfer)\b/i,
  ];
  const RISK_CARRIER=[
    /\bunder review by\b/i,/\bcontrolled by\b/i,/\brequires approval from\b/i,/\bsubject to .{0,45} jurisdiction\b/i,
    /\bon the entity list\b/i,/\bdesignated\b/i,/\bstate-linked\b/i,/\bmilitary-affiliated\b/i,
    /\bforeign interference\b/i,/\btalent recruitment by\b/i,/\bcoercion\b/i,/\bleverage over\b/i,/\bpressure to align\b/i,
    /\b(?:white house|u\.s\.|united states|china|chinese|russia|russian|india|canada|united kingdom|uk government)\b/i,
    /\b(?:government|regulator|authority|supplier|provider|platform operator|cloud provider)\b/i,
    /\bnon-european .{0,30}(?:supplier|provider|company|firm)s?\b/i,
    /\b(?:market|supplier|supply|platform|cloud|technology) concentration\b/i,/\bstate-backed .{0,30}(?:competitor|company|firm|actor)s?\b/i,
    /\b(?:export-control|export control|sanctions?|investment screening|procurement) (?:regime|rules?|restrictions?|controls?)\b/i,
    /\b(?:china|taiwan|united states|u\.s\.|us|russia) .{0,70}(?:supply|technology|investment|provider|market|control|dominance)\b/i,
    /\b(?:international|foreign) investments?\b/i,/\bprocurement preferences?\b/i,/\bcritical (?:raw )?materials?(?: supply| market| exports?)?\b/i,/\bdual[- ]use export control regulation\b/i,
    /\b(?:fragmentation|precarity|mobility barriers?|research career conditions|limited accessibility)\b/i
  ];
  const RISK_ASSET=[
    /\bdependent on .{0,80} for\b/i,/\breliant on imports? of\b/i,/\bno domestic capacity\b/i,/\bsingle source\b/i,/\bsole supplier\b/i,
    /\bconcentrated (?:in|computing capacity)\b/i,/\bmonopoly risk\b/i,/\bbottleneck\b/i,/\bchokepoint\b/i,/\berosion of\b/i,
    /\bhollowing out\b/i,/\bloss of control over\b/i,/\bbrain drain\b/i,/\brelocation of\b/i,/\bforeign ownership of\b/i,
    /\bstrategic dependenc(?:y|ies)\b/i,/\bexposure to retaliation\b/i,/\bdependence on .{0,80}(?:supplier|provider|cloud|technology|imports?)\b/i,
    /\b(?:research collaboration|academic freedom|peer review|research access|research capacity|research careers?|researcher mobility|talent pool|research talent|data flow|research data|computing capacity|compute capacity|cloud and ai infrastructure|research infrastructure|supply chain|technology access|technology transfer|equipment|knowledge|semiconductor supply|semiconductors?|critical raw material supply|critical raw materials?|strategic autonomy|technological autonomy|competitiveness|innovation ecosystem|deep tech|scale-up funding|ai capability|ai capabilities|digital capability|digital capabilities|scientific infrastructure|research excellence|open science|autonomous policy|economic performance)\b/i
  ];
  const RISK_FORWARD=[
    /\b(?:could|would|may|might|can)\b/i,/\bproposed\b/i,/\bunder review\b/i,/\bsubject to\b/i,/\bat the discretion\b/i,
    /\block-in\b/i,/\bextraterritorial\b/i,/\bno substitute\b/i,/\bno alternative supplier\b/i,/\bdependence\b/i,/\bdependency\b/i,
    /\bdependencies\b/i,/\b(?:risk|risks|vulnerable|vulnerability|exposure|challenge|constraint|scarcity|shortage)s?\b/i,/\bcan constrain\b/i,
    /\b(?:foreign interference|brain drain|precarity|fragmentation|barriers?|limited accessibility)\b/i
  ];
  const RISK_LOSS=[
    /\b(?:constrain|restrict|deny|block|cut off|withhold|disrupt|erode|undermine|hollow out|drain|damage|weaken|reduce|limit)s?\b/i,
    /\b(?:loss|losses|brain drain|dependency|dependence|dependencies|vulnerability|exposure|scarcity|shortage|bottleneck|lock-in|compliance costs?|barriers? to)\b/i,
    /\b(?:obtain|acquire|extract) .{0,60}(?:advanced knowledge|technology|know-how|research knowledge)\b/i,/\btechnology transfer\b/i,/\brisks?\b/i,/\brestrictions?\b/i
  ];

  const RESPONSE_TO_RISK=[
    /\baddress(?:es|ed|ing)? (?:the )?(?:issue|challenge|problem|risk) of\b/i,
    /\b(?:aims?|designed|intended) to (?:reduce|mitigate|counter|tackle|prevent|reverse|address|overcome)\b/i,
    /\bturn(?:s|ed|ing)? .{0,80}(?:brain drain|dependence|challenge|loss) .{0,30}into .{0,80}(?:brain gain|capacity|resilience|strength|opportunity)\b/i,
    /\bincrease the attractiveness of .{0,80}(?:research careers?|european research|europe)\b/i,
    /\b(?:offer|offers|offering|provide|provides|providing) .{0,70}(?:excellent working conditions|longer-term employment|stable careers?|better research careers?)\b/i
  ];
  const RESPONSE_FAILURE=[
    /\b(?:despite|even with|even after) .{0,100}(?:risk|brain drain|dependence|shortage|barrier|loss) .{0,50}(?:remain|persist|worsen|continue)\w*\b/i,
    /\b(?:insufficient|not enough|fails? to|failed to|unable to) .{0,90}(?:reduce|reverse|prevent|stop|address|mitigate)\b/i,
    /\b(?:risk|brain drain|dependence|shortage|barrier|vulnerability) (?:remains?|persists?|continues?|worsens?)\b/i,
    /\bcould still (?:lose|restrict|deny|cut off|weaken|undermine|worsen|increase)\b/i
  ];
  const OPP_REMEDY=[
    ...RESPONSE_TO_RISK,
    /\b(?:pilot action|programme|program|scheme|initiative) .{0,90}(?:supports?|funds?|recruits?|enables?|provides?)\b/i,
    /\bwith a view to (?:offering|providing|building|strengthening|reducing|increasing)\b/i
  ];
  const OPP_OPERATIONAL_RESPONSE=[
    /\bpilot action\b/i, /\bprojects? in which .{0,80}(?:recruit|build|develop|provide|support)\b/i,
    /\b(?:programme|program|scheme|initiative|action) supports? projects?\b/i,
    /\b(?:organisation|organization|entity|applicant)s? .{0,45}(?:apply|applies|can apply|may apply)\b/i,
    /\b(?:funds?|funding|supports?|recruits?|provides?) .{0,80}(?:researchers|projects|capacity|infrastructure|technology|access)\b/i
  ];
  const STRATEGIC_PROBLEM=[
    /\bbrain drain\b/i,/\bprecarity\b/i,/\bstrategic dependenc(?:y|ies)\b/i,/\bdependence on\b/i,/\breliance on\b/i,
    /\bshortage\b/i,/\bscarcity\b/i,/\bfragmentation\b/i,/\bbarriers?\b/i,/\bvulnerab(?:ility|le)\b/i,/\bexposure\b/i,
    /\bforeign interference\b/i,/\bexport controls?\b/i,/\bresearch security\b/i,/\bknowledge security\b/i
  ];

  function remedialOnlyRiskText(text){
    const t=clean(text);
    return !!t && any(t,RESPONSE_TO_RISK) && !any(t,RESPONSE_FAILURE);
  }

  const OPP_MECHANISM=[
    /\bcould leverage\b/i,/\bcan leverage\b/i,/\bcan convert .{0,80} into\b/i,/\bsubstitution potential\b/i,/\brecycling could supply\b/i,
    /\bdemand-side measure\b/i,/\bspillover into\b/i,/\badjacent market\b/i,/\brelatedness to existing strengths\b/i,
    /\bbuilds on installed base\b/i,/\btransferable to\b/i,/\bscalable\b/i,/\bdual-use potential\b/i,/\bnetwork effects favour\b/i,
    /\b(?:call|programme|program|fund|initiative|pilot action|action)(?: [A-Z0-9_-]{3,})? aims? (?:to|at) (?:strengthen|build|support|expand|accelerate|develop|establish|establishing|attract|retain|reduce|address)\b/i,
    /\b(?:will|can|could) (?:help |allow |enable )?(?:strengthen|build|secure|expand|scale|attract|retain|develop|establish|provide)\b/i,
    /\bprovide(?:s|d)? .{0,50}(?:funding|investment|access|support)\b/i,/\bpresented upcoming opportunities? under\b/i,/\bopen-access .{0,40}(?:infrastructure|facility)\b/i,
    /\b(?:launch(?:es|ed)?|open(?:s|ed)?|offer(?:s|ed)?|fund(?:s|ed)?|support(?:s|ed)?|enable(?:s|d)?|allow(?:s|ed)?) .{0,80}(?:call|programme|program|funding|investment|access|research|innovation|mobility|capacity|companies|projects?)\b/i,
    /\b(?:agreement|association|partnership|initiative|programme|program|scheme) .{0,65}(?:enable|support|strengthen|expand|increase|accelerate|provide)s?\b/i,
    /\bcan now (?:request|access|use|apply|participate)\b/i,/\bturn(?:ing)? .{0,65} into .{0,65}(?:gain|capacity|advantage|brain gain)\b/i
  ];
  const OPP_ACTOR=[
    /\beuropean commission\b/i,/\beuropean innovation council\b/i,/\beic\b/i,/\beurohpc(?: joint undertaking)?\b/i,
    /\bhorizon europe\b/i,/\bmarie skłodowska-curie actions\b/i,/\bmsca\b/i,/\beuropean research council\b/i,/\berc\b/i,
    /\beuropean investment bank\b/i,/\beib\b/i,/\bbusiness finland\b/i,/\b(?:national|federal) government\b/i,
    /\bministry of [a-z -]+\b/i,/\bgovernment of [a-z -]+\b/i,/\bmember states?\b/i,/\beuropean union\b/i,/\beu\b/i,
    /\bjoint research centre\b/i,/\bjrc\b/i,/\bcouncil of the european union\b/i,/\beuropean parliament\b/i,
    /\b[a-z][a-z&.-]+ (?:agency|authority|council|fund|foundation|joint undertaking|university|consortium)\b/i
  ];
  const OPP_INSTRUMENT=[
    /\bexisting instrument\b/i,/\blegal basis already exists\b/i,/\bno new legislation required\b/i,/\bprocurement could\b/i,
    /\bconditionality attached to\b/i,/\beligibility criteria allow\b/i,/\bassociation agreement\b/i,/\bco-funding available\b/i,
    /\bcall open until\b/i,/\bdesignation as strategic project\b/i,/\bfast-track\b/i,/\bregulatory sandbox\b/i,/\bpilot line\b/i,
    /\banchor customer\b/i,/\blaunch customer\b/i,/\bhorizon europe\b/i,/\beic\b/i,/\berc\b/i,/\bmsca\b/i,/\beurohpc\b/i,
    /\b(?:funding|investment) (?:programme|program|instrument|facility|call|scheme)\b/i,/\bwork programme\b/i,/\bopen call\b/i,
    /\b(?:call|programme|program|initiative|scheme|facility|fund|partnership|association agreement|letter of intent|pilot action|action)\b/i,
    /\b(?:free|open) access to .{0,60}(?:research infrastructure|supercomput|quantum|facility|resource)\b/i,
    /\bcall [A-Z0-9_-]{5,}\b/i,/\b€\s?\d[\d.,]*\s?(?:million|billion)?\b/i,/\beur\s?\d[\d.,]*\s?(?:million|billion)?\b/i
  ];
  const OPP_GAIN=[
    /\b(?:strengthen|secure|build|expand|increase|improve|accelerate|develop|establish|attract|retain|scale|boost) .{0,90}(?:capacity|capabilit|autonomy|resilience|competitiveness|leadership|innovation|research|technology|talent|supply|access|infrastructure|ecosystem|collaboration)\b/i,
    /\b(?:capacity|capability|autonomy|resilience|competitiveness|leadership|talent|investment|innovation|research access|research careers?|researcher mobility|knowledge exchange|technology transfer|deep tech|scale-up|supercomputing|quantum|semiconductor|infrastructure|collaboration|brain gain)\b/i
  ];
  const OPP_WINDOW=[
    /\b(?:status )?open\b/i,/\bopening date\b/i,/\bdeadline(?: date)?\b/i,/\bopen until\b/i,/\bapply\b/i,/\bapplications?\b/i,
    /\bupcoming opportunities?\b/i,/\b2026[–-]2027\b/i,/\bcall(?:s)? launched\b/i,/\bnew (?:call|programme|program|fund|initiative)\b/i,
    /\bavailable for (?:this|the) call\b/i,/\bbudget available for (?:this|the) call\b/i,/\bfunding (?:is )?available\b/i,/\bcurrently open\b/i,
    /\b(?:launch(?:es|ed)?|open(?:s|ed)?) (?:a |an |the )?(?:new )?(?:call|programme|program|initiative|scheme|facility)\b/i,
    /\bcan now (?:request|access|use|apply|participate)\b/i,/\bupcoming (?:call|calls|opportunities|programme|program)\b/i,/\b2026 (?:call|work programme|programme|program)\b/i
  ];
  const OPP_STRONG_WINDOW=[
    /\bstatus\s+open\b/i,/\bopening date\b/i,/\bdeadline(?: date)?\b/i,/\bopen until\b/i,/\bcall open\b/i,/\bopen call\b/i,
    /\bapplications? (?:open|close|closing|deadline)\b/i,/\bcall(?:s)? launched\b/i,/\blaunch(?:es|ed) (?:a |an |the )?(?:new )?call\b/i,
    /\bopen(?:s|ed) (?:a |an |the )?(?:new )?call\b/i,/\bclosing soon\b/i,/\bupcoming opportunities?\b/i,/\bupcoming calls?\b/i,
    /\bcan now (?:request|access|use|apply|participate)\b/i,/\bopen access to .{0,70}(?:research infrastructure|quantum computers?|supercomput|facility|resource)\b/i,
    /\bnew (?:funding )?(?:programme|program|scheme|initiative)\b/i,/\b2026(?:–|-|\s)2027 (?:programme|program|work programme|calls?)\b/i
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

  function evidenceParts(x){
    const filed=(x?.strategic_classification_source==='source_text'&&x?.strategic_classification)||null;
    const filedPassages=Array.isArray(filed?.lenses)?filed.lenses.map(v=>clean(v?.passage)).filter(Boolean):[];
    const trendPassage=clean(filed?.trend_action_passage);
    const fields=[x?.headline,x?.title,x?.summary,x?.core_message,x?.what,x?.signal_note,x?.why_it_matters,x?.bridge_sentence,x?.relevance_note,x?.eu_evidence,x?.ri_evidence,x?.geo_evidence,x?.a_context_evidence];
    return [...filedPassages,trendPassage,...fields.map(clean).filter(Boolean)].filter((v,i,a)=>a.indexOf(v)===i);
  }

  function evidenceText(x){return evidenceParts(x).join(' ')}

  function inferredOpportunityActor(raw,text){
    const direct=firstMatch(text,OPP_ACTOR); if(direct) return direct;
    const source=sourceFor(raw);
    if(/European Commission|European Innovation Council|EuroHPC|Joint Research Centre|Council of the European Union|European Research Council|Marie Skłodowska-Curie|ERA Portal|European Investment Bank/i.test(source)) return source;
    const title=titleFor(raw);
    if(/^EU\b|^European (?:Commission|Union|Innovation Council|Research Council)|^EuroHPC/i.test(title)) return firstMatch(title,[/^EU\b/i,/^European [A-Za-z -]+/i,/^EuroHPC(?: Joint Undertaking)?/i])||source||'European Union';
    return '';
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
      // A programme that is explicitly trying to solve a problem is not itself the risk.
      // It can still be evidence that the problem exists, but the Risks list should not
      // turn a mitigation measure into a loss pathway unless the same passage says the
      // response is failing or the risk remains.
      if(remedialOnlyRiskText(t)) return null;
      const mechanism=firstMatch(t,RISK_MECHANISM),asset=firstMatch(t,RISK_ASSET),conditional=firstMatch(t,RISK_FORWARD),loss=firstMatch(t,RISK_LOSS);
      let carrier=firstMatch(t,RISK_CARRIER);
      const structural=firstMatch(t,[/\blimited accessibility\b/i,/\bprecarity\b/i,/\bfragmentation\b/i,/\b(?:market|supplier|supply|platform|cloud|technology) concentration\b/i,/\bprocurement preferences?\b/i]);
      if(structural&&/barriers?|fragmentation|precarity|limited|concentrat/i.test(mechanism)) carrier=structural;
      if(!(mechanism&&carrier&&asset&&conditional&&loss)) return null;
      if(/^fragmentation/i.test(mechanism)&&/^fragmentation/i.test(carrier)&&!/(constrain|barrier|loss|depend|vulnerab|expos|scarcity|shortage)/i.test(t)) return null;
      if(/^foreign interference$/i.test(mechanism)&&/^foreign interference$/i.test(carrier)&&!/(obtain|acquire|extract|exploit|transfer|steal|loss|access to)/i.test(t)) return null;
      return {type:'risk',status:'open',passage:t.slice(0,1200),components:{mechanism,carrier,asset,loss},analysis_basis:'repository_evidence_interpretation',analysis_score:100};
    }
    if(kind==='opportunity'){
      const remedy=firstMatch(t,OPP_REMEDY),operational=firstMatch(t,OPP_OPERATIONAL_RESPONSE),problem=firstMatch(t,STRATEGIC_PROBLEM);
      const mechanism=firstMatch(t,OPP_MECHANISM)||remedy,actor=inferredOpportunityActor(raw,t),instrument=firstMatch(t,OPP_INSTRUMENT),gain=firstMatch(t,OPP_GAIN),window=firstMatch(t,OPP_STRONG_WINDOW);
      const openWindowPath=!!(mechanism&&actor&&instrument&&gain&&window);
      const strategicResponsePath=!!(remedy&&operational&&problem&&actor&&instrument&&gain);
      if(!(openWindowPath||strategicResponsePath)) return null;
      // Adopted measures are not automatically opportunities. They qualify without a live
      // application window only when the source describes an operational response to a
      // concrete strategic problem (for example turning brain drain into brain gain).
      if(any(t,OPP_BASELINE)&&!any(t,OPP_WINDOW)&&!strategicResponsePath) return null;
      const noise=firstMatch(t,OPP_NOISE);
      return {type:'opportunity',passage:t.slice(0,1200),components:{mechanism,actor,instrument,gain,window:window||operational},response_to:problem||'',noise_cue:noise||'',analysis_basis:'repository_evidence_interpretation',analysis_score:100};
    }
    return null;
  }

  function scannerLenses(raw){
    const c=raw?.strategic_classification;
    const classificationSource=clean(raw?.strategic_classification_source);
    if(!c||typeof c!=='object'||!['source_text','deep_scan_v2_semantics'].includes(classificationSource)) return [];
    let lenses=Array.isArray(c.lenses)?c.lenses.filter(x=>x&&typeof x==='object'&&['risk','opportunity','external_shock'].includes(clean(x.type))):[];
    if(!lenses.length&&['risk','opportunity','external_shock'].includes(clean(c.primary))) lenses=[{type:clean(c.primary),passage:''}];
    // Protect the reader from legacy/source-filed polarity errors: a source passage that
    // describes a mitigation/response is not presented as a risk unless it explicitly says
    // the response is failing or the risk remains.  V2-derived classifications receive the
    // same polarity guard; "authoritative" describes the source semantics, not an exemption
    // from the reader-product pathway rules.
    lenses=lenses.filter(l=>clean(l.type)!=='risk'||!remedialOnlyRiskText(clean(l.passage)||evidenceText(raw)));
    const analysisBasis=classificationSource==='deep_scan_v2_semantics'?'deep_scan_v2_semantic_classification':'scanner_source_classification';
    const analysisScore=classificationSource==='deep_scan_v2_semantics'?115:110;
    return lenses.map(l=>{const kind=clean(l.type),family=kind==='external_shock'?primaryShockFamily(`${clean(l.passage)} ${evidenceText(raw)}`):null;return {...l,shock_family:clean(l.shock_family||family?.label||''),shock_family_id:clean(l.shock_family_id||family?.id||''),analysis_basis:analysisBasis,analysis_score:analysisScore}});
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
    const analysisBasis=clean(x?.lens?.analysis_basis);
    const basis=analysisBasis==='deep_scan_v2_semantic_classification'?3:analysisBasis==='scanner_source_classification'?2:1;
    const quality=Number(x?.qualityScore)||qualityScore(x?.raw||x);
    // Weak-signal context is a bounded tie-breaker only.  It can reinforce an already
    // supported primary pathway, but it cannot compensate for weaker primary evidence.
    const context=Math.min(0.60,Math.max(0,Number(x?.contextWeightTotal)||0));
    // Publication/evidence quality is deliberately the dominant ordering signal.
    // Recency and corroborating context break close ties; neither lets weak evidence lead.
    return quality*1e13+basis*1e11+Math.round(context*100)*1e9+components*1e8+dateValue(x?.date)+(x?.newThisScan?1:0);
  }

  function analyticalWeight(raw){
    const explicit=Number(raw?.analytical_weight);
    const role=norm(raw?.evidence_role||'');
    const low=norm(raw?.evidence_status||'')==='low'||raw?.context_only===true||/weak signal|weak_signal|context/.test(role);
    if(low) return Math.min(0.30,Math.max(0,Number.isFinite(explicit)?explicit:0.30));
    return 1;
  }

  function contextOnly(raw){return analyticalWeight(raw)<0.999}

  function sourceIdentity(x){
    const raw=x?.raw||x||{};
    const link=linkFor(raw);
    try{if(link)return new URL(link).hostname.toLowerCase().replace(/^www\./,'')}catch(_e){}
    return norm(sourceFor(raw)||x?.source||'');
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

  // Several independent records can support the same analytical pathway.  Consolidate
  // by the interpreted mechanism + exposed asset when both are clear, rather than by
  // surface wording alone.  A broad/uncertain pathway keeps its own card; we never hide
  // distinct reasoning merely because two sentences happen to sound alike.
  function consolidateReaderDuplicates(items){
    const out=[],bySemantic=new Map(),byTitle=new Map();
    for(const x of items){
      const title=clean(plainPriorityTitle(x)),titleKey=`${clean(x?.kind)}|reader:${norm(title)}`;
      const semantic=semanticPathwayKey(x);
      // Identical reader wording must never appear as separate cards.  Where the wording
      // differs, a clear mechanism+asset key can still consolidate semantically equivalent
      // records.  Distinct mechanisms are preserved by plainPriorityTitle() before this step.
      const lead=byTitle.get(titleKey)||(semantic?bySemantic.get(semantic):null);
      if(!lead){
        const copy={...x,relatedPrimaryEvidence:[]};
        if(titleKey&&!titleKey.endsWith('reader:'))byTitle.set(titleKey,copy);
        if(semantic)bySemantic.set(semantic,copy);
        out.push(copy);
        continue;
      }
      lead.relatedPrimaryEvidence.push({
        title:clean(x?.title||x?.coreMessage||title),source:clean(x?.source),date:clean(x?.date),link:clean(x?.link),
        evidence:clean(x?.lensPassage||x?.abstract||x?.coreMessage||x?.title||''),qualityScore:Number(x?.qualityScore)||0,
        semanticSource:clean(x?.semanticSource||''),deepScanAuthoritative:!!x?.deepScanAuthoritative,
      });
      if(titleKey&&!titleKey.endsWith('reader:'))byTitle.set(titleKey,lead);
      if(semantic)bySemantic.set(semantic,lead);
    }
    return out;
  }

  function rawEvidenceItems(data){
    const collections=[
      Array.isArray(data?.strategic_pathways)?data.strategic_pathways:[],
      Array.isArray(data?.strand_a)?data.strand_a:[],
      // Strand B is a persistent methods library, not evidence about the external world.
      Array.isArray(data?.frontier_evidence)?data.frontier_evidence:[],
      Array.isArray(data?.strand_c)?data.strand_c:[],
    ];
    const rows=collections.flat().filter(x=>x&&typeof x==='object');
    const byKey=new Map(),unkeyed=[];
    for(const x of rows){
      const key=norm(linkFor(x)||titleFor(x));
      if(!key){unkeyed.push(x);continue}
      const prior=byKey.get(key);
      const weight=y=>scannerLenses(y).length*10000+qualityScore(y)*100+(evidenceText(y).length>0?1:0);
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
        const interpretationBasis=clean(lens.analysis_basis),quality=qualityScore(raw);
        // Keep repository inference active. Publication quality is the dominant ordering
        // signal in pathwayScore(), so stronger papers/reports lead while lower-ranked
        // evidence can still surface a supported risk or opportunity instead of being
        // silently discarded by a fixed quality cutoff.
        out.push({
          raw,kind,lens,lensPassage:clean(lens.passage),strategicClassification:raw.strategic_classification||{},
          title:titleFor(raw),coreMessage:coreFor(raw),source:sourceFor(raw),date:clean(raw.date||raw.first_seen||''),
          link:linkFor(raw),abstract:clean(raw.summary||raw.signal_note||raw.why_it_matters||''),newThisScan:!!raw.new_this_scan,
          readerWhat:clean(raw.reader_what||''),readerWhy:clean(raw.reader_why||''),readerMore:clean(raw.reader_more||''),
          why_it_matters:clean(raw.reader_why||raw.why_it_matters||''),relevance_note:clean(raw.relevance_note||''),
          semanticSource:clean(raw.semantic_source||''),deepScanAuthoritative:!!raw.deep_scan_authoritative,
          interpretationBasis,qualityScore:quality,analyticalWeight:analyticalWeight(raw),contextOnly:contextOnly(raw),
        });
      }
    }
    return out;
  }

  function sortPathways(items){
    return items.sort((a,b)=>pathwayScore(b)-pathwayScore(a)||String(b.date).localeCompare(String(a.date))||a.title.localeCompare(b.title));
  }

  function attachWeakContext(primary,contexts){
    const pSource=sourceIdentity(primary),topic=topicKey(primary),used=new Set(),matches=[];
    for(const c of sortPathways([...contexts])){
      if(c.kind!==primary.kind||topicKey(c)!==topic) continue;
      const sid=sourceIdentity(c);
      if(sid&&sid===pSource) continue;
      if(sid&&used.has(sid)) continue;
      if(sid) used.add(sid);
      matches.push(c);
      if(matches.length>=3) break;
    }
    const total=matches.reduce((n,c)=>n+Math.min(0.30,Math.max(0,Number(c.analyticalWeight)||0.30)),0);
    return {...primary,weakSignalContext:matches,contextWeightTotal:Math.min(0.60,total)};
  }

  function highOrderRows(data,kind){
    const state=data?.high_order_inference&&typeof data.high_order_inference==='object'?data.high_order_inference:{};
    const ids=Array.isArray(state?.publications?.[kind])?state.publications[kind]:[];
    const byId=new Map((Array.isArray(state?.candidates)?state.candidates:[]).filter(x=>x&&typeof x==='object').map(x=>[clean(x.id),x]));
    const evidenceRow=x=>({title:clean(x?.title||''),source:clean(x?.source||''),date:clean(x?.date||''),link:clean(x?.link||''),role:clean(x?.role||''),quality:Number(x?.quality)||0,analyticalWeight:Number(x?.analytical_weight)||0,sourceStatement:clean(x?.source_statement||''),contribution:clean(x?.evidence_contribution||'')});
    return ids.map((id,publicationRank)=>byId.get(clean(id))).filter(Boolean).map((c,publicationRank)=>{
      const support=Array.isArray(c.support)?c.support:[],against=Array.isArray(c.against)?c.against:[],ctx=Array.isArray(c.context)?c.context:[];
      const sourceLabel=Number(c.primary_sources||0)>=2?'Multiple sources':clean(support[0]?.source||'Evidence base');
      return {highOrder:true,kind,title:clean(c.reader_title||c.topic_label||'Evidence-backed finding'),coreMessage:clean(c.card&&typeof c.card==='object'?c.card.lead:c.reader_summary),
        source:sourceLabel,date:clean(c.last_updated_at||state.evaluated_at||''),link:'',abstract:clean(c.reader_summary||''),newThisScan:!!c.new_this_scan,
        qualityScore:Number(c.score)||0,analyticalWeight:1,contextOnly:false,lens:{type:kind,passage:clean(c.reader_summary||'')},
        lensPassage:clean(c.reader_summary||''),interpretationBasis:'claim_native_publication',raw:{title:clean(c.reader_title),summary:clean(c.reader_summary)},
        candidateId:clean(c.id),publicationRank,readerAuthored:!!clean(c.reader_title),readerWhy:clean(c.reader_why||''),readerKindLabel:clean(c.reader_kind_label||''),readerBasis:clean(c.reader_basis||''),grammarId:clean(c.grammar_id),topicLabel:clean(c.topic_label),
        objectKey:clean(c.object||c.topic_key),mechanism:clean(c.mechanism),direction:clean(c.direction),claimStatus:clean(c.claim_status||c.status),
        wow:Number(c.wow)||0,readerStatusChip:clean(c.reader_status_chip),inferentialDistance:Number(c.inferential_distance)||Number(c.level)||0,
        evidenceSemantics:clean(c.evidence_semantics||''),
        supportEvidence:support.map(evidenceRow),counterEvidence:against.map(evidenceRow),
        primaryRecords:Number(c.primary_records)||0,primarySources:Number(c.primary_sources)||0,counterRecords:Number(c.counter_records)||0,
        weakSignalContext:ctx.map(evidenceRow),contextWeightTotal:Math.min(.60,ctx.reduce((n,x)=>n+(Number(x.analytical_weight)||.30),0)),
        evidenceSummary:support.slice(0,5).map(x=>x.title).filter(Boolean).join('; ')};
    });
  }

  function buildPriorityView(data,opts={}){
    const limit=Number.isFinite(opts.limit)?Math.max(1,Math.floor(opts.limit)):Number.POSITIVE_INFINITY;
    const state=data?.high_order_inference&&typeof data.high_order_inference==='object'?data.high_order_inference:{};
    const claimNative=state?.detector_backend==='claim_native'&&Number(state?.selection_stage||0)>=7;

    // After the Stage-7 cutover the Python reasoning shelf is authoritative.  The old
    // item-by-item source lens remains as a rollback/compatibility reader only; mixing
    // it back into a live claim-native shelf would let one high-merit publication
    // outrank a verified multi-record finding and would silently undo the reform.
    if(claimNative){
      const riskRows=highOrderRows(data,'risk');
      const opportunityRows=highOrderRows(data,'opportunity');
      const riskSel=state?.selection?.risk&&typeof state.selection.risk==='object'?state.selection.risk:{};
      const oppSel=state?.selection?.opportunity&&typeof state.selection.opportunity==='object'?state.selection.opportunity:{};
      const shownRisks=riskRows.slice(0,limit),shownOpportunities=opportunityRows.slice(0,limit);
      return {
        risks:shownRisks,
        opportunities:shownOpportunities,
        externalShocks:[],
        stats:{
          claimNativeCutover:true,
          interpreted:riskRows.length+opportunityRows.length,sourceFiled:0,repositoryInterpreted:0,weakSignalContextUsed:0,
          risks:riskRows.length,opportunities:opportunityRows.length,externalShocks:0,rawRisks:riskRows.length,rawOpportunities:opportunityRows.length,
          mergedRiskRecords:0,mergedOpportunityRecords:0,closedRisks:0,
          shownRisks:shownRisks.length,shownOpportunities:shownOpportunities.length,
          riskReserve:Number(riskSel.reserve)||0,riskWatch:Number(riskSel.watch)||0,
          opportunityReserve:Number(oppSel.reserve)||0,opportunityWatch:Number(oppSel.watch)||0,
        }
      };
    }

    const rows=lensRows(data);
    const primaryRows=rows.filter(x=>!x.contextOnly);
    const contextRows=rows.filter(x=>x.contextOnly);
    const closedRisks=primaryRows.filter(x=>x.kind==='risk'&&clean(x.lens?.status)==='closed_into_shock');
    const allRisks=sortPathways(primaryRows.filter(x=>x.kind==='risk'&&clean(x.lens?.status)!=='closed_into_shock').map(x=>attachWeakContext(x,contextRows)));
    const allOpportunities=sortPathways(primaryRows.filter(x=>x.kind==='opportunity').map(x=>attachWeakContext(x,contextRows)));
    const readerRisks=consolidateReaderDuplicates(allRisks);
    const readerOpportunities=consolidateReaderDuplicates(allOpportunities);
    // Reader-level external-shock lenses are also primary-only.  The dedicated shock page
    // uses the stricter Python inference engine, where C/history are explicitly contextual.
    const externalShocks=sortPathways(primaryRows.filter(x=>x.kind==='external_shock'));
    const sourceFiled=primaryRows.filter(x=>x.interpretationBasis==='scanner_source_classification').length;
    const repositoryInterpreted=primaryRows.filter(x=>x.interpretationBasis==='repository_evidence_interpretation').length;
    const weakSignalContextUsed=[...allRisks,...allOpportunities].reduce((n,x)=>n+(x.weakSignalContext?.length||0),0);
    return {
      risks:diversifiedTop(readerRisks,limit,2),
      opportunities:diversifiedTop(readerOpportunities,limit,2),
      externalShocks,
      stats:{
        claimNativeCutover:false,interpreted:allRisks.length+allOpportunities.length+externalShocks.length,
        sourceFiled,repositoryInterpreted,weakSignalContextUsed,
        risks:readerRisks.length,opportunities:readerOpportunities.length,externalShocks:externalShocks.length,
        rawRisks:allRisks.length,rawOpportunities:allOpportunities.length,
        mergedRiskRecords:Math.max(0,allRisks.length-readerRisks.length),mergedOpportunityRecords:Math.max(0,allOpportunities.length-readerOpportunities.length),
        closedRisks:closedRisks.length,shownRisks:Math.min(limit,readerRisks.length),shownOpportunities:Math.min(limit,readerOpportunities.length),
        riskReserve:0,riskWatch:0,opportunityReserve:0,opportunityWatch:0,
      }
    };
  }

  function simplePriorityText(x){
    const raw=clean(x?.title||x?.coreMessage||'');
    const readable=Insights?.fastReaderText?.(raw)||Insights?.readerPoint?.(raw)||Insights?.completeCoreMessage?.(raw)||raw;
    const text=clean(readable)||'Finding';
    return text.length>180?text.slice(0,180).replace(/\s+\S*$/,''):text;
  }

  function pathwayText(x){return norm(`${x?.title||''} ${x?.coreMessage||''} ${x?.lensPassage||''} ${x?.abstract||''}`)}
  function componentText(x){const c=x?.lens?.components&&typeof x.lens.components==='object'?Object.values(x.lens.components).filter(Boolean).join(' '):'';return norm(c)}

  // Reader grouping is based first on the pathway components produced by the analytical
  // layer.  The broad source text is only a fallback.  This prevents words such as
  // "materials" or "investment" elsewhere in an article from silently redefining the
  // risk that the lens actually identified.
  function semanticAssetFamily(x){
    const c=componentText(x),p=norm(x?.lensPassage||''),t=c||p;
    if(/semiconductor|microelectronic|chips?/.test(t))return 'chips';
    if(/computing capacity|compute capacity|cloud|ai infrastructure|supercomput/.test(t))return 'compute';
    if(/brain drain|research talent|researcher|research careers?|talent/.test(t))return 'talent';
    if(/research collaboration|research cooperation|international collaboration/.test(t))return 'collaboration';
    if(/research infrastructure|research facilit|shared facilit|laborator/.test(t))return 'research-infrastructure';
    if(/critical raw|critical mineral|rare earth|gallium|germanium|lithium|cobalt/.test(t))return 'critical-materials';
    if(/research security|sensitive research knowledge|knowledge security|foreign interference/.test(t))return 'research-security';
    if(/research data|open science|data infrastructure/.test(t))return 'research-data';
    if(/intellectual property|deep tech firms?|scale.?ups?|ownership/.test(t))return 'firms-ip';
    if(/strategic depend|external technology|technology dependence|technological dependence|technology access/.test(t))return 'technology-dependence';
    if(/competitiveness/.test(t))return 'competitiveness';
    return 'other';
  }

  function semanticMechanismFamily(x){
    const c=componentText(x),p=norm(x?.lensPassage||''),t=c||p;
    if(/export control|export restriction|licen[cs]ing/.test(t))return 'export-control';
    if(/extraterritorial|foreign legal|third country law/.test(t))return 'foreign-law';
    if(/sanction/.test(t))return 'sanctions';
    if(/market concentration|supplier concentration|concentrated/.test(t))return 'concentration';
    if(/dependence|dependency|depend on|reliance/.test(t))return 'dependency';
    if(/brain drain|precarity|talent flow|recruit|retain/.test(t))return 'talent-flow';
    if(/foreign interference|espionage|knowledge leakage/.test(t))return 'interference';
    if(/barriers? to|access denial|limited access|restrict|constrained by/.test(t))return 'access-barrier';
    if(/fragmentation/.test(t))return 'fragmentation';
    if(/acquisition|ownership transfer|foreign investment/.test(t))return 'ownership-transfer';
    if(/shortage|supply interruption|cutoff|scarcity/.test(t))return 'supply-interruption';
    if(/call|programme|pilot action|work programme|funding|procurement/.test(t))return 'programme-route';
    if(/open access|opening/.test(t))return 'open-access';
    if(/standard/.test(t))return 'standards';
    if(/partnership|association|cooperation/.test(t))return 'partnership';
    return 'other';
  }

  function semanticPathwayKey(x){
    if(x?.highOrder)return '';
    const kind=clean(x?.kind),asset=semanticAssetFamily(x),mechanism=semanticMechanismFamily(x);
    // "competitiveness" and "other" are too broad to merge safely: two very different
    // mechanisms can affect competitiveness.  Keep those findings separate unless their
    // final reader wording is literally the same.
    if(!kind||asset==='other'||asset==='competitiveness'||mechanism==='other')return '';
    return `${kind}|semantic:${asset}|${mechanism}`;
  }

  function friendlyCandidateTopic(x){
    let raw=clean(x?.topicLabel||x?.objectKey||x?.title||'European research and innovation');
    raw=raw.split(' — ')[0].replace(/[._]/g,' ').replace(/\s+/g,' ').trim();
    const aliases={
      'compute public procurement':'Europe’s AI-factory procurement',
      'talent retention':'researcher retention',
      'defence drone research':'defence-drone research',
      'research security screening':'research-security screening',
      'innovation system performance':'innovation-system performance',
      'digital governance':'digital governance',
      'ai governance':'AI governance',
      'goal strategic autonomy':'strategic autonomy',
      'research system governance':'research-system governance',
      'defence innovation funding':'defence-innovation funding',
      'horizon association':'Horizon association',
      'compute gigafactory':'European AI-gigafactory capacity',
      'research collaboration':'research collaboration',
      'industrial competitiveness':'industrial competitiveness',
      'export control regulation':'export-control rules',
      'research openness':'research openness',
      'finance strategic investment':'strategic investment finance'
    };
    return aliases[raw.toLowerCase()]||raw;
  }

  function claimNativeFallbackTitle(x){
    const topic=friendlyCandidateTopic(x),g=clean(x?.grammarId),kind=clean(x?.kind),dir=clean(x?.direction),mech=clean(x?.mechanism);
    if(g==='clock_before_rule')return `The delivery clock is running before the rules are settled for ${topic}.`;
    if(g==='success_metric_gap')return `${topic.charAt(0).toUpperCase()+topic.slice(1)} can be funded before success is properly measured.`;
    if(g==='deployment_before_rules')return `${topic.charAt(0).toUpperCase()+topic.slice(1)} is moving ahead of settled rules.`;
    if(g==='conflicting_criteria')return `Two rule systems are pulling ${topic} in different directions.`;
    if(g==='dependency_pathway')return `A dependency could propagate into ${topic}.`;
    if(g==='corroborated_claim'&&kind==='risk'){
      if(dir==='contracts')return `${topic.charAt(0).toUpperCase()+topic.slice(1)} is under sustained pressure.`;
      if(dir==='becomes_conditional')return `${topic.charAt(0).toUpperCase()+topic.slice(1)} is becoming more conditional.`;
      if(dir==='becomes_contested')return `${topic.charAt(0).toUpperCase()+topic.slice(1)} is becoming more contested.`;
      return `${topic.charAt(0).toUpperCase()+topic.slice(1)} is showing a corroborated constraint.`;
    }
    if(g==='corroborated_claim'&&kind==='opportunity'){
      if(['builds','procures','adds_capacity'].includes(mech))return `Europe is adding ${topic} through a live instrument.`;
      if(['associates','collaborates'].includes(mech))return `${topic.charAt(0).toUpperCase()+topic.slice(1)} is widening through active agreements.`;
      if(mech==='funds')return `New funding is expanding ${topic}.`;
      if(mech==='prioritises')return `${topic.charAt(0).toUpperCase()+topic.slice(1)} is being backed by adopted priorities.`;
      if(mech==='launches')return `${topic.charAt(0).toUpperCase()+topic.slice(1)} is moving into operation through new instruments.`;
      if(mech==='coordinates')return `${topic.charAt(0).toUpperCase()+topic.slice(1)} is gaining an active coordination route.`;
      if(mech==='invests')return `New investment is expanding ${topic}.`;
      if(mech==='supports')return `A live support instrument is expanding ${topic}.`;
      return `A live European instrument is expanding ${topic}.`;
    }
    return clean(x?.title)||`${topic.charAt(0).toUpperCase()+topic.slice(1)}.`;
  }

  function plainPriorityTitle(x){
    if(x?.highOrder)return x?.readerAuthored?(clean(x.title)||'Evidence-backed finding'):claimNativeFallbackTitle(x);
    const t=pathwayText(x),title=norm(x?.title||''),kind=clean(x?.kind),asset=semanticAssetFamily(x),mechanism=semanticMechanismFamily(x);
    if(kind==='risk'){
      if(asset==='talent') return 'Precarious career paths can make Europe lose research talent it has trained or attracted.';
      if(asset==='research-security'||mechanism==='interference') return 'Foreign interference could pull sensitive research knowledge out of Europe.';
      if(asset==='chips'&&mechanism==='export-control') return 'Export controls could cut European access to advanced chips before alternatives are ready.';
      if(asset==='chips'&&['dependency','concentration','supply-interruption'].includes(mechanism)) return 'Concentrated external chip supply could leave European research and industry without fast substitutes.';
      if(asset==='critical-materials') return 'Critical-material shortages or export controls could slow European research and industry.';
      if(asset==='compute'&&['dependency','foreign-law','concentration','access-barrier'].includes(mechanism)) return "Dependence on outside cloud and compute providers could narrow Europe's control over strategic computing.";
      if(asset==='collaboration'&&['access-barrier','sanctions','fragmentation'].includes(mechanism)) return 'Unequal or restrictive collaboration conditions could narrow who can participate in and benefit from European research partnerships.';
      if(asset==='research-infrastructure'&&['access-barrier','concentration','dependency'].includes(mechanism)) return 'Limited access to key research infrastructure could slow European research.';
      if(asset==='technology-dependence') return "Dependence on outside technology could limit Europe's freedom to act.";
      if(asset==='research-data'&&mechanism==='fragmentation') return 'Fragmented research systems could make data, collaboration and open science harder to sustain.';
      if(asset==='firms-ip'&&mechanism==='ownership-transfer') return 'Foreign acquisition could move strategic technology, intellectual property and decision-making out of Europe.';
      if(asset==='competitiveness'&&mechanism==='export-control') return "Export-control uncertainty could constrain Europe's technology competitiveness and international cooperation.";
      if(asset==='competitiveness'&&mechanism==='concentration') return 'Concentrated markets could make it harder for European research-led firms to scale into globally competitive capability.';
      if(asset==='competitiveness'&&mechanism==='access-barrier') return 'Structural barriers could keep European research from translating into stronger competitiveness.';
      // Conservative fallbacks for records whose lens predates component extraction.
      if(/brain drain|precarity|research careers?|research talent|researcher mobility/.test(t)) return 'Precarious career paths can make Europe lose research talent it has trained or attracted.';
      if(/foreign interference|espionage|knowledge leakage/.test(t)) return 'Foreign interference could pull sensitive research knowledge out of Europe.';
      if(/critical raw|critical mineral|rare earth|gallium|germanium|lithium|cobalt/.test(t)) return 'Critical-material shortages or export controls could slow European research and industry.';
      if(/research infrastructure|facility|bottleneck|limited access/.test(t)) return 'Limited access to key research infrastructure could slow European research.';
      if(/technology transfer|technological dependence|technology dependence|strategic depend/.test(t)) return "Dependence on outside technology could limit Europe's freedom to act.";
      return simplePriorityText(x);
    }
    if(kind==='opportunity'){
      if(asset==='talent'||/choose europe for science/.test(title)) return 'Better research careers could help Europe keep and attract researchers.';
      if(/ocean research|ocean.*innovation strategy/.test(title)) return 'Europe has a chance to improve how ocean research and innovation are coordinated.';
      if(/eit|innovation agenda|call for evidence/.test(title)) return 'Europe has a chance to reshape innovation policy around future strategic needs.';
      if(/quantum/.test(title)&&/standards?/.test(title)) return 'European work on quantum standards could help shape the rules of an emerging technology.';
      if(/quantum/.test(title)&&/pilot line|testing infrastructure|experimental/.test(title)) return 'European quantum testing and pilot facilities could build more capability at home.';
      if(/quantum/.test(title)&&/open|access/.test(title)) return 'Opening European quantum computers could give researchers more strategic compute access.';
      if(/quantum/.test(title)) return 'New European quantum calls and facilities could strengthen capability in a strategic technology.';
      if(asset==='compute'||/ai gigafactor|computing capacity/.test(title)) return 'More European computing capacity could reduce dependence and give researchers more room to scale.';
      if(/open access to jrc|research infrastructures?/.test(title)&&/open access/.test(title)) return 'Opening European research facilities could give researchers better access to strategic infrastructure.';
      if(/egypt|north macedonia|association|partnership|international cooperation/.test(title)) return 'Deeper research partnerships could widen European networks, talent and access.';
      return simplePriorityText(x);
    }
    return simplePriorityText(x);
  }

  function plainPriorityExplanation(x){
    if(x?.highOrder&&x?.readerAuthored&&clean(x?.coreMessage))return clean(x.coreMessage);
    if(x?.highOrder){
      const topic=friendlyCandidateTopic(x),g=clean(x?.grammarId),dir=clean(x?.direction),mech=clean(x?.mechanism),kind=clean(x?.kind);
      if(g==='dependency_pathway')return 'A constraint in one connected part of the system could carry into the other, widening the impact beyond the original bottleneck.';
      if(g==='clock_before_rule')return 'Projects may commit money, infrastructure or operating choices before the rules are final, making later changes harder and more expensive.';
      if(g==='success_metric_gap')return `Funding can increase before there is a clear way to tell whether ${topic} is actually improving.`;
      if(g==='deployment_before_rules'||g==='practice_before_doctrine')return 'Early implementation can harden into the default before the formal framework has resolved the main trade-offs.';
      if(g==='conflicting_criteria')return 'Institutions can make inconsistent choices when two valid requirements pull in different directions without a clear tie-break.';
      if(g==='latent_channel')return 'Existing European structures could be connected to close the gap without building an entirely new programme from scratch.';
      if(g==='corroborated_claim'&&kind==='risk'){
        if(dir==='becomes_conditional')return `More approvals or requirements could make access to ${topic} harder and less predictable.`;
        if(dir==='becomes_contested')return `Competing demands could make decisions around ${topic} slower, less predictable or harder to coordinate.`;
        if(dir==='contracts')return `If the current constraint persists, capacity and room to act around ${topic} could narrow further.`;
        return `The current pressure could reduce capacity, access or room to act around ${topic} if it persists.`;
      }
      if(g==='corroborated_claim'&&kind==='opportunity'){
        if(['collaborates','associates'].includes(mech))return `Keeping the agreement active could widen access to partners, expertise and networks around ${topic}.`;
        if(['procures','builds','adds_capacity','invests'].includes(mech))return `If the current build-out reaches users, it could add usable European capacity around ${topic}.`;
        if(mech==='funds')return `If funded work turns into delivery, it could strengthen European capability around ${topic}.`;
        if(['supports','launches','coordinates','retains','allocates','prioritises'].includes(mech))return `If the current instrument works as intended, it could strengthen European capability around ${topic}.`;
        return `If current implementation continues, Europe could gain more usable capability around ${topic}.`;
      }
      if(kind==='risk')return `The current pathway could reduce European capacity, access or room to act around ${topic}.`;
      if(kind==='opportunity')return `The current pathway could turn existing European activity into more usable capability around ${topic}.`;
    }
    const t=pathwayText(x),title=norm(x?.title||''),kind=clean(x?.kind),asset=semanticAssetFamily(x),mechanism=semanticMechanismFamily(x);
    if(kind==='risk'){
      if(asset==='talent') return 'Insecure career paths can push researchers elsewhere, leaving laboratories, infrastructure and strategic programmes short of specialist people.';
      if(asset==='research-security'||mechanism==='interference') return 'Outside access to sensitive knowledge or know-how can weaken future European capability as well as compromise individual projects.';
      if(asset==='chips') return mechanism==='export-control'?'Export controls can remove access to advanced chips faster than European substitutes can be qualified.':'Concentrated chip supply can interrupt European research and production faster than alternative suppliers can be qualified.';
      if(asset==='critical-materials') return 'A shortage or export restriction can delay research and production when critical materials have no fast substitute.';
      if(asset==='compute') return 'Access, price or permitted use can change quickly when essential computing infrastructure is controlled by outside suppliers or foreign legal regimes.';
      if(asset==='collaboration') return 'Restrictive participation or governance conditions can narrow the people, knowledge and networks European teams can use.';
      if(asset==='research-infrastructure') return 'Limited access to scarce facilities can slow experiments, training and innovation even when funding is available.';
      if(asset==='technology-dependence') return 'Reliance on capabilities that Europe cannot replace quickly can narrow policy choices when political or commercial conditions change.';
      if(asset==='research-data'&&mechanism==='fragmentation') return 'Separate systems and rules can make data movement and collaboration harder, reducing the effective scale of European research.';
      if(asset==='firms-ip'&&mechanism==='ownership-transfer') return 'An acquisition can move intellectual property, product decisions and high-value research outside Europe even when the company remains commercially successful.';
      if(asset==='competitiveness'&&mechanism==='export-control') return 'Uncertain export rules can restrict access to advanced technology and make international cooperation harder for European firms and research programmes.';
      if(asset==='competitiveness'&&mechanism==='concentration') return 'Concentrated markets can leave European research strengths without firms large enough to retain production, investment and strategic capability in Europe.';
      if(asset==='competitiveness'&&mechanism==='access-barrier') return 'A persistent bottleneck between research strength and deployment can prevent European knowledge from becoming wider industrial capability.';
      if(/critical raw|critical mineral|rare earth|gallium|germanium|lithium|cobalt/.test(t)) return 'A shortage or export restriction can delay research and production when critical materials have no fast substitute.';
      return 'A dependency, bottleneck, rule or structural constraint could reduce European research capacity, access or freedom to act.';
    }
    if(kind==='opportunity'){
      if(asset==='talent'||/choose europe for science/.test(title)) return 'More stable and attractive research careers could help Europe retain researchers and draw more of them in.';
      if(/ocean research|ocean.*innovation strategy/.test(title)) return 'Better coordination can align priorities and institutions before the future European ocean research and innovation strategy is fixed.';
      if(/eit|innovation agenda|call for evidence/.test(title)) return 'A live policy-design process creates room to improve priorities and instruments before they are fixed.';
      if(/quantum/.test(title)&&/standards?/.test(title)) return 'Early standards work can help European research strengths shape the technical rules that later govern deployment and markets.';
      if(/quantum/.test(title)&&/pilot line|testing infrastructure|experimental/.test(title)) return 'Shared testing and pilot facilities can move quantum research toward usable technology without every organisation duplicating expensive infrastructure.';
      if(/quantum/.test(title)&&/open|access/.test(title)) return 'Direct access to European quantum computers can turn public infrastructure into usable scientific and technological capability.';
      if(/quantum/.test(title)) return 'Current calls and facilities can build European quantum capability while the technology and market structure are still developing.';
      if(asset==='compute'||/ai gigafactor|computing capacity/.test(title)) return 'More European-controlled computing capacity can support AI work while reducing exposure to outside suppliers.';
      if(/open access to jrc|research infrastructures?/.test(title)&&/open access/.test(title)) return 'Opening existing facilities lets more researchers use expensive infrastructure and can speed experimentation and collaboration.';
      if(/egypt|north macedonia|association|partnership|international cooperation/.test(title)) return 'A well-chosen partnership can widen access to researchers, infrastructure, data and complementary expertise.';
      return 'Europe has a concrete route to strengthen research, innovation, access, resilience or control.';
    }
    return simplePriorityText(x);
  }

  function supportingEvidenceText(x){
    if(x?.highOrder)return '';
    const raw=clean(x?.lensPassage||x?.abstract||x?.coreMessage||x?.title||'');
    if(!raw) return 'Evidence text unavailable.';
    const first=raw.split(/(?<=[.!?])\s+/).filter(Boolean).slice(0,3).join(' ');
    const text=clean(first||raw);
    return text.length>520?text.slice(0,517).replace(/\s+\S*$/,''):text;
  }

  function simpleEvidenceText(x){return clean(x?.title||'')}

  return {buildPriorityView,pathwayScore,diversifiedTop,consolidateReaderDuplicates,semanticPathwayKey,semanticAssetFamily,semanticMechanismFamily,simplePriorityText,plainPriorityTitle,plainPriorityExplanation,supportingEvidenceText,simpleEvidenceText,topicKey,lensRows,interpretLenses,evidenceText,evidenceParts,inferredLens,shockFamilies,primaryShockFamily,remedialOnlyRiskText};
});
