(()=>{
  'use strict';
  const path=location.pathname.replace(/\\/g,'/');
  const ROUTES=[
    [/\/frontier\/quick\/?$/,'frontier-quick'],
    [/\/frontier\/?$/,'frontier'],
    [/\/trends\/?$/,'trends'],
    [/\/phenomena\/?$/,'phenomena'],
    [/\/priorities\/?$/,'priorities'],
    [/\/shocks\/variants(?:\.html)?\/?$/,'shocks-variants'],
    [/\/shocks\/?$/,'shocks'],
    [/\/read\/?$/,'read'],
    [/\/briefing\/?$/,'briefing'],
    [/\/glossary\/?$/,'glossary'],
    [/\/explore\/?$/,'explore'],
    [/\/literature\/?$/,'literature']
  ];
  const excluded=/\/(?:radar|stuff|historical|history)\/?$/;
  if(excluded.test(path))return;
  let route=(ROUTES.find(([re])=>re.test(path))||[])[1]||'';
  if(!route){
    // The repository root is the Start page.  Do not guess for arbitrary files.
    if(/\/$/.test(path)&&!/\/[^/]+\/(?:[^/]+)\/$/.test(path))route='start';
    else return;
  }

  const script=document.currentScript;
  if(!script?.src)return;
  const dataUrl=new URL('reader_language/approved.json',script.src);
  const normalise=v=>String(v??'').replace(/\s+/g,' ').trim();
  const SKIP=new Set(['SCRIPT','STYLE','NOSCRIPT','TEXTAREA','INPUT','SELECT','OPTION','CODE','PRE']);

  // Presentation-only cleanup for recurring machine-generated phrasing. These rules are
  // intentionally narrow and preserve direction, modality, counts and named entities.
  const SOURCE_PREFIX=/^(?:Reuters|Euractiv|Nature|Science|Politico|Financial Times|The Guardian|BBC|OECD|UNESCO|European Commission(?:\s*[—-]\s*Research\s*&\s*Innovation)?|European Council on Foreign Relations|Research Council of Finland|Joint Research Centre(?: Publications Repository)?|EFSA Supporting Publications|Royal Society Open Science|Jacques Delors Centre|Bertelsmann Stiftung|European Science Foundation|EU Digital Strategy|Council of the European Union|European Parliament|European Research Council|European Innovation Council|European Investment Bank|Science Europe|Bruegel|CEPS|ALLEA)\s*:\s*/i;
  const INSTITUTION_PREFIX=/^[^:]{2,90}:\s+(?=.+)/;
  const INSTITUTION_WORDS=/\b(?:commission|council|centre|center|foundation|institute|university|agency|ministry|repository|publications|society|stiftung|parliament|bank|strategy|research|science|reuters|euractiv|nature|bruegel|ceps|ecfr|oecd|unesco)\b/i;

  function friendlyText(value, opts={}){
    let s=normalise(value);
    if(!s)return s;

    // On the main reader cards, lead with the finding rather than an institutional
    // source name. Source names remain visible inside expandable evidence sections.
    if(opts.stripSourcePrefix){
      s=s.replace(SOURCE_PREFIX,'');
      const m=s.match(INSTITUTION_PREFIX);
      if(m){const prefix=s.slice(0,s.indexOf(':'));if(INSTITUTION_WORDS.test(prefix))s=s.slice(s.indexOf(':')+1).trim();}
    }

    s=s.replace(/^Current evidence is adding or widening (.+?)(?: as a whole)? through (.+)\.$/i,
      (_,topic,means)=>`Evidence points to growth in ${topic}, supported by ${means}.`);
    s=s.replace(/^Current evidence (?:is making|shows) (.+?)(?: as a whole)? (?:becoming )?more conditional or constrained through (.+)\.$/i,
      (_,topic,means)=>`${topic.replace(/^./,c=>c.toUpperCase())} is facing tighter conditions, including ${means}.`);
    s=s.replace(/^Current evidence shows (.+?) expanding through (.+)\.$/i,
      (_,topic,means)=>`${topic.replace(/^./,c=>c.toUpperCase())} is expanding, supported by ${means}.`);

    const targeted=[
      [/^Selective conditionality is narrowly targeted and, as currently designed, likely to exert only limited leverage over foreign\.?$/i,'The proposed conditions are narrowly targeted and are likely to have only limited influence on foreign partners.'],
      [/^A research security self-assessment appendix is a mandatory, admissibility-relevant part of every Research Council of Finland\.?$/i,'Every funding application must include a research-security self-assessment.'],
      [/^The Commission proposes a regulation creating a framework of measures to strengthen Europe['’]s cloud and artificial intelligence ecosystem\.?$/i,'The EU has proposed rules intended to expand Europe’s cloud and artificial-intelligence capacity.'],
      [/^Greater perceived legal clarity is associated with deeper, not necessarily broader, enterprise artificial intelligence adoption\.?$/i,'Companies that see the rules as clearer tend to use artificial intelligence more deeply, though not necessarily in more parts of the business.'],
      [/^Three linked Horizon Europe initiatives launched to improve access, financing and industry collaboration across European research infrastructures\.?$/i,'Three EU initiatives were launched to improve access to research facilities, financing and collaboration with industry.'],
      [/^Hungary['’]s continued exclusion from Horizon Europe grants is holding back its dementia research and diagnostic capacity\.?$/i,'Hungary’s exclusion from EU research grants is limiting dementia research and diagnostic capacity.'],
      [/^Spain proposed a stronger EU climate-resilience framework with binding targets, systematic risk assessments and dedicated financing\.?$/i,'Spain proposed EU-wide climate-resilience rules with binding targets, regular risk checks and dedicated funding.'],
      [/^European firms recognise geopolitical risks, but preparedness and integration into corporate strategy remain uneven\.?$/i,'European companies recognise geopolitical risks, but many are still unevenly prepared for them.'],
      [/^European institutions are pursuing greater sovereign space capability to reduce reliance on US infrastructure\.?$/i,'Europe is building more of its own space capability to reduce reliance on US infrastructure.'],
      [/^ECFR argues that European resilience requires both reducing strategic dependencies and adapting to those\.?$/i,'Europe needs both to reduce important outside dependencies and to prepare for the ones it cannot quickly remove.'],
      [/^The Council adopted the first EU framework for science diplomacy as a coordinated basis\.?$/i,'EU countries adopted their first common approach to using science in international relations.'],
      [/^Google announced a major new artificial intelligence-compute investment and energy arrangement in Finland\.?$/i,'Google announced a major investment in artificial-intelligence computing and energy capacity in Finland.'],
      [/^Finnish opposition parties proposed a national permitting framework for data centres following a major artificial intelligence-infrastructure deal\.?$/i,'Finnish opposition parties proposed national permit rules for data centres after a major artificial-intelligence infrastructure deal.'],
      [/^Mistral closed a EUR 3 billion round at roughly EUR 21 billion valuation with EU-backed and Korean investors joining\.?$/i,'Mistral raised €3 billion from European and Korean investors, valuing the company at about €21 billion.'],
      [/^The EU leads globally in scientific output but underperforms markedly in patenting, venture capital and growing technology firms\.?$/i,'Europe produces a great deal of research but trails leading competitors in patents, growth funding and building large technology companies.'],
      [/^EFSA processed 55 emerging-risk topics in 2025, confirmed four as emerging risks, and established an EU Early\.?$/i,'EU food-safety experts reviewed 55 possible new risks in 2025 and confirmed four as emerging risks.'],
      [/^Non-animal methods are advancing across experimental, computational and regulatory domains\.?$/i,'Research methods that do not use animals are advancing in experiments, computer modelling and regulation.'],
      [/^The Commission proposed new EU legislation aimed at strengthening the single market for innovation\.?$/i,'The EU proposed new rules intended to make it easier for innovation to move and grow across Europe.'],
      [/^EU27 improves but remains behind the US, South Korea and Japan\.?$/i,'Europe is improving, but it still trails the United States, South Korea and Japan on key innovation measures.']
    ];
    for(const [re,to] of targeted){if(re.test(s)){s=to;break;}}

    const simple=[
      [/\bconditionality\b/gi,'conditions'],
      [/\bselective conditions\b/gi,'targeted conditions'],
      [/\bleverage\b/gi,'influence'],
      [/\badmissibility[- ]relevant\b/gi,'required for an application to be accepted'],
      [/\badmissibility\b/gi,'eligibility'],
      [/\bprocurement\b/gi,'public purchasing'],
      [/\bregulatory\b/gi,'rule-based'],
      [/\bframework of measures\b/gi,'set of measures'],
      [/\becosystem\b/gi,'sector'],
      [/\benterprise adoption\b/gi,'use by companies'],
      [/\badoption\b/gi,'use'],
      [/\bdiagnostic finding\b/gi,'finding'],
      [/\bscale[- ]ups?\b/gi,'growing technology firms'],
      [/\bscale[- ]up\b/gi,'growth'],
      [/\bcompute access\b/gi,'access to computing power'],
      [/\bcompute capacity\b/gi,'computing capacity'],
      [/\bdual[- ]use\b/gi,'civilian and defence'],
      [/\bde[- ]risking\b/gi,'reducing risk'],
      [/\bstrategic autonomy\b/gi,'ability to act without relying heavily on others'],
      [/\bstrategic dependencies\b/gi,'important dependencies on outside suppliers or partners'],
      [/\bchokepoints?\b/gi,'critical bottlenecks'],
      [/\bbottlenecks?\b/gi,'obstacles'],
      [/\bcommercialisation\b/gi,'turning research into products and companies'],
      [/\binstrument\b/gi,'programme'],
      [/\barbitration rule\b/gi,'tie-break rule'],
      [/\bcodifying\b/gi,'formalising'],
      [/\bdoctrine\b/gi,'policy'],
      [/\blongitudinal\b/gi,'over time'],
      [/\bresilience\b/gi,'ability to withstand disruption'],
      [/\bR&I\b/g,'research and innovation'],
      [/\bAI\b/g,'artificial intelligence'],
      [/\bHPC\b/g,'high-performance computing']
    ];
    for(const [re,to] of simple)s=s.replace(re,to);

    s=s.replace(/\bas a whole\b/gi,'');
    s=s.replace(/\bdocumented constraints\b/gi,'identified limits');
    s=s.replace(/\bconcrete action\b/gi,'action already taken');
    s=s.replace(/\bconcrete actions\b/gi,'actions already taken');
    s=s.replace(/\bpieces of evidence\b/gi,'sources');
    s=s.replace(/\s{2,}/g,' ').replace(/\s+([,.;:!?])/g,'$1').trim();

    const exact=new Map([
      ['Current evidence has to pull in both directions.','A trend appears here only when there is credible evidence in both directions.'],
      ['A one-way movement stays a developing pattern until a credible counter-pull appears.','Movement in only one direction remains a developing pattern until credible evidence appears on the other side.'],
      ["The wording above is the Radar's synthesis. The statements below are the narrower claims attributed to the sources.",'The summary above combines the evidence. The source statements below show what each source says directly.'],
      ["The phenomenon above is the Radar's synthesis. Current source evidence and historical context are kept separate below.",'The summary above combines the evidence. Current sources and older context are shown separately below.'],
      ['What is pulling:','Why the balance looks this way:'],
      ['What would move the balance:','What to watch next:'],
      ['What could change the balance:','What to watch next:'],
      ['Current source evidence:','Current sources:'],
      ['Source evidence that could weaken the finding:','Evidence that points the other way:'],
      ['What the sources state:','What the sources say:'],
      ['What the Radar infers:','What this could mean:'],
      ['Speaks for the shock','Evidence supporting the scenario'],
      ['Pushes against it','Evidence that could soften the scenario'],
      ['Plainly:','In short:'],
      ['Net assessment:','Overall assessment:'],
      ['Possible balance:','Evidence range:'],
      ['Contribution:','Why it matters here:'],
      ['Source statement:','What the source says:'],
      ['Horizon access: the build-out accelerates','Access to EU research facilities is expanding'],
      ['Horizon access: the fine print tightens','Access to EU research funding faces tighter limits'],
      ['Venture capital is on the rise','Investment in young technology companies is rising'],
      ['Venture capital meets resistance','Young technology companies still struggle to get growth funding'],
      ['Strengthen research-system governance','Improve how the research system is run'],
      ['More conditions complicate research governance','More rules make the research system harder to manage'],
      ['Push harder on innovation performance','Europe is trying to get more results from innovation'],
      ['Structural bottlenecks keep holding performance back','Long-standing obstacles still hold innovation back'],
      ['Build more strategic autonomy','Reduce reliance on outside suppliers and systems'],
      ['Dependencies keep setting the terms','Outside dependencies still limit Europe’s choices'],
      ['Opening the throttle on energy supply','More energy is being secured for computing'],
      ['Pulling the handbrake on energy supply','New limits could slow energy use by data centres'],
      ['Europe doubles down on critical infrastructure resilience','Europe is strengthening protection for critical infrastructure'],
      ['Second thoughts slow critical infrastructure resilience','Preparedness for critical infrastructure risks remains uneven'],
      ['Open more research partnerships','Open more international research partnerships'],
      ['Put more conditions around collaboration','Add more safeguards to international research collaboration'],
      ['Scaling up research security','Research-security measures are increasing'],
      ['Research security gets harder to do','Research-security rules are becoming harder to meet'],
      ['Europe bets bigger on artificial intelligence','Europe is investing more in artificial intelligence'],
      ['The bill for artificial intelligence keeps rising','The cost and complexity of artificial intelligence keep rising']
    ]);
    return exact.get(s)||s;
  }


  fetch(dataUrl,{cache:'no-store'}).then(r=>r.ok?r.json():null).then(data=>{
    const items=data&&data.items&&typeof data.items==='object'?Object.values(data.items):[];
    const map=new Map();
    for(const item of items){
      if(!item||item.status!=='rewrite')continue;
      const routes=Array.isArray(item.routes)?item.routes:[];
      if(routes.length&&!routes.includes(route))continue;
      const source=normalise(item.source),replacement=normalise(item.replacement);
      const matches=Array.isArray(item.matches)&&item.matches.length?item.matches:[source];
      if(source&&replacement&&source!==replacement){
        for(const match of matches){const key=normalise(match);if(key)map.set(key,replacement)}
      }
    }
    function applyNode(node){
      if(!node||node.nodeType!==Node.TEXT_NODE||!node.parentElement)return;
      if(SKIP.has(node.parentElement.tagName))return;
      const raw=node.nodeValue||'',key=normalise(raw);
      const exact=map.get(key);
      const inEvidence=!!node.parentElement.closest('details,.evidence,.shock-detail,.meta');
      const replacement=friendlyText(exact||key,{stripSourcePrefix:!inEvidence});
      if(!replacement||replacement===key)return;
      const lead=(raw.match(/^\s*/)||[''])[0],trail=(raw.match(/\s*$/)||[''])[0];
      node.nodeValue=lead+replacement+trail;
    }
    function applyTree(root){
      if(!root)return;
      if(root.nodeType===Node.TEXT_NODE){applyNode(root);return;}
      const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
      let n;while((n=walker.nextNode()))applyNode(n);
    }
    applyTree(document.body);
    const observer=new MutationObserver(muts=>{
      for(const m of muts){
        if(m.type==='characterData')applyNode(m.target);
        for(const n of m.addedNodes||[])applyTree(n);
      }
    });
    observer.observe(document.body,{subtree:true,childList:true,characterData:true});
  }).catch(()=>{});
})();
