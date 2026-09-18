(()=>{
  'use strict';
  if(globalThis.__RADAR_READER_LANGUAGE_V5__)return;
  globalThis.__RADAR_READER_LANGUAGE_V5__=true;

  const path=location.pathname.replace(/\\/g,'/');
  // Raw evidence views are deliberately untouched.
  if(/\/(?:radar|historical|history|stuff)\/?$/.test(path))return;

  const SKIP=new Set(['SCRIPT','STYLE','NOSCRIPT','TEXTAREA','INPUT','SELECT','OPTION','CODE','PRE']);
  const normalise=v=>String(v??'').replace(/\s+/g,' ').trim();

  const exact=new Map(Object.entries({
    // Shared labels
    'Evidence tug-of-war':'Evidence moving in opposite directions',
    'Reading the tug-of-war':'How to read these pairs',
    'Each card shows a live pull and the force pushing the other way.':'Each card compares evidence pointing in two different directions.',
    'The balance reflects the strength and independence of the evidence.':'The balance reflects how strong the evidence is and how many independent sources support it.',
    'It is a tug-of-war score, not a forecast.':'The score compares the evidence. It is not a forecast.',
    'Current evidence has to pull in both directions.':'A pair appears only when there is credible evidence in both directions.',
    'A one-way movement stays a developing pattern until a credible counter-pull appears.':'If the evidence moves only one way, it remains a developing pattern until credible evidence appears on the other side.',
    'Older evidence can reveal roots, persistence or reversal.':'Older evidence can show where a pattern came from, how long it has lasted, or whether it has changed direction.',
    'It adds perspective without deciding the current balance.':'It adds context but does not determine the current balance.',
    "The wording above is the Radar's synthesis. The statements below are the narrower claims attributed to the sources.":'The summary above combines the evidence. Open this section to see the individual sources and what each one says.',
    "The phenomenon above is the Radar's synthesis. Current source evidence and historical context are kept separate below.":'The summary above combines the evidence. Current sources and older context are shown separately below.',
    'Read source evidence':'See the evidence',
    'What is pulling:':'Why the balance looks this way:',
    'What would move the balance:':'What to watch next:',
    'What could change the balance:':'What to watch next:',
    'Possible balance:':'Evidence range:',
    'Contribution:':'Why it matters here:',
    'Source statement:':'What the source says:',
    'Source evidence that could weaken the finding:':'Evidence pointing the other way:',
    'What the sources state:':'What the sources say:',
    'What the Radar infers:':'What this could mean:',
    'Plainly:':'In short:',
    'Net assessment:':'Overall assessment:',
    'Speaks for the shock':'Evidence supporting this scenario',
    'Pushes against it':'Evidence that could make this scenario less likely',

    // Current Trends titles
    'Green technology gains momentum':'Green technology is advancing',
    'Rules and costs rein green technology in':'Costs and supply problems are slowing green technology',
    'Build more European computing capacity':'Europe is building more computing capacity',
    'Power, supply and access constrain the build-out':'Power, land and supply limits are slowing the build-out',
    'Fresh commitments for strategic investment':'Strategic investment is attracting more support',
    'Friction grows around strategic investment':'Conditions on strategic investment remain limited',
    'Scaling up research security':'Research-security measures are increasing',
    'Research security gets harder to do':'Research-security requirements are becoming harder to meet',
    'Europe bets bigger on AI':'Europe is investing more in artificial intelligence',
    'The bill for AI keeps rising':'Artificial intelligence is becoming more costly and complex to use',
    'Europe doubles down on critical infrastructure resilience':'Europe is strengthening protection for critical infrastructure',
    'Second thoughts slow critical infrastructure resilience':'Preparedness for infrastructure risks remains uneven',
    'Horizon access: the build-out accelerates':'Access to European research facilities is expanding',
    'Horizon access: the fine print tightens':'Access to European research funding still has important limits',
    'Venture capital is on the rise':'Investment in young technology companies is rising',
    'Venture capital meets resistance':'Young technology companies still struggle to get growth funding',
    'Build more strategic autonomy':'Europe is reducing reliance on outside suppliers and systems',
    'Dependencies keep setting the terms':'Outside dependencies still limit Europe’s choices',
    'Open more research partnerships':'Europe is opening more international research partnerships',
    'Put more conditions around collaboration':'Europe is adding more safeguards to international research collaboration',
    'Put more money behind the next Horizon programme':'Europe is preparing more funding for the next research programme',
    'Frugal positions keep the budget under pressure':'Budget pressure could limit the next research programme',
    'Opening the throttle on energy supply':'More energy is being secured for computing',
    'Pulling the handbrake on energy supply':'New permit rules could slow data-centre growth',
    'Expand research-system capacity':'Europe is adding research capacity',
    'Capacity is being stretched or made conditional':'Pressure and new conditions are stretching research capacity',
    'Strengthen research-system governance':'Europe is improving how the research system is run',
    'More conditions complicate research governance':'More rules are making the research system harder to manage',
    'Push harder on innovation performance':'Europe is trying to get more results from innovation',
    'Structural bottlenecks keep holding performance back':'Long-standing obstacles are still holding innovation back',

    // Current Trends lead sentences, rewritten as reader summaries without source branding.
    'European Commission, Joint Research Centre: Environmental biotechnology offers routes to cleaner production, resource recovery and reduced dependence on fossil and primary raw materials.':'New biotechnology methods could make production cleaner, recover more resources and reduce reliance on fossil fuels and newly mined raw materials.',
    'JRC Publications Repository: The EU has selective manufacturing strengths but persistent gaps in batteries and solar supply chains, alongside weaker venture investment.':'Europe has strengths in some green industries, but important gaps remain in battery and solar supply chains and in growth funding.',
    'EuroHPC Joint Undertaking: EuroHPC opened a competitive call for consortia to build and operate up to seven AI Gigafactories, with joint public procurement of compute access time and a…':'Europe has opened a competition to build and operate up to seven very large artificial-intelligence computing centres.',
    'Reuters: New market data show Europe’s AI data-centre geography changing in response to power and land constraints.':'Power and land shortages are already affecting where new artificial-intelligence data centres can be built in Europe.',
    'Journal of Economic Geography: Geopolitical and supply-chain concerns increased the value of European capacity, while subsidies helped compensate for Germany’s cost disadvantages.':'Security and supply-chain concerns are making European production capacity more valuable, while subsidies are helping offset high costs in Germany.',
    'Jacques Delors Centre: Selective conditionality is narrowly targeted and, as currently designed, likely to exert only limited leverage over foreign investors.':'The proposed conditions on foreign investment are narrow and are likely to have only limited influence on investors.',
    'Reuters: Belgian authorities opened a concrete semiconductor-espionage case involving sensitive gallium-nitride know-how.':'Belgian authorities opened an espionage case involving sensitive semiconductor technology.',
    'Research Council of Finland: A research security self-assessment appendix is a mandatory, admissibility-relevant part of every Research Council of Finland application.':'Research funding applications in Finland must now include a research-security self-assessment.',
    "European Commission: The Commission proposes a regulation creating a framework of measures to strengthen Europe's cloud and AI ecosystem.":'The EU has proposed rules intended to expand Europe’s cloud and artificial-intelligence capacity.',
    'AI and Ethics: Greater perceived legal clarity is associated with deeper, not necessarily broader, enterprise AI adoption.':'Companies that see the rules as clearer tend to use artificial intelligence more deeply, though not necessarily in more parts of their business.',
    'Euractiv: Spain proposed a stronger EU climate-resilience framework with binding targets, systematic risk assessments and dedicated financing.':'Spain proposed EU-wide rules with binding targets, regular risk checks and dedicated funding to prepare for climate-related disruption.',
    'Bertelsmann Stiftung: European firms recognise geopolitical risks, but preparedness and integration into corporate strategy remain uneven.':'European companies recognise geopolitical risks, but many are still unevenly prepared for them.',
    'European Science Foundation: Three linked Horizon Europe initiatives launched to improve access, financing and industry collaboration across European research infrastructures.':'Three European initiatives were launched to improve access to research facilities, financing and collaboration with industry.',
    "Euractiv: Hungary's continued exclusion from Horizon Europe grants is holding back its dementia research and diagnostic capacity.":'Hungary’s exclusion from European research grants is limiting dementia research and diagnostic capacity.',
    'Reuters: Mistral closed a EUR 3 billion round at roughly EUR 21 billion valuation with EU-backed and Korean investors joining.':'Mistral raised €3 billion from European and Korean investors, valuing the company at about €21 billion.',
    'CEPS: The EU leads globally in scientific output but underperforms markedly in patenting, venture capital and scale-up, with AI acting as a central hub linking the fifteen…':'Europe produces a great deal of research but trails leading competitors in patents, growth funding and building large technology companies.',
    'Nature: European institutions are pursuing greater sovereign space capability to reduce reliance on US infrastructure.':'Europe is building more of its own space capability to reduce reliance on US infrastructure.',
    'European Council on Foreign Relations: ECFR argues that European resilience requires both reducing strategic dependencies and adapting to those that persist.':'Europe needs both to reduce important outside dependencies and to prepare for the ones it cannot quickly remove.',
    'European Commission — Research & Innovation: The Council adopted the first EU framework for science diplomacy as a coordinated basis for EU and member-state action.':'European countries adopted their first common approach to using science in international relations.',
    'Royal Society Open Science: It can contribute, but only if security and sovereignty measures do not collapse the openness needed for science.':'Security safeguards can help, but they can also damage research if they make ordinary scientific collaboration too difficult.',
    'ERA Portal Austria: The Council adopted a recommendation establishing a European framework for science diplomacy and advanced but did not conclude negotiations on the next Framework Programme.':'European countries agreed on a common approach to science diplomacy, while negotiations on the next research programme continued.',
    'ERA Portal Austria: FP10 should manage dual-use risk through clear, proportionate procedures without treating broad areas of basic research as restricted.':'The next research programme may need clearer safeguards for research that could have both civilian and military uses, without broadly restricting basic research.',
    'Reuters: Google announced a major new AI-compute investment and energy arrangement in Finland.':'Google announced a major investment in artificial-intelligence computing and energy capacity in Finland.',
    'Reuters: Finnish opposition parties proposed a national permitting framework for data centres following a major AI-infrastructure deal.':'Finnish opposition parties proposed national permit rules for data centres after a major artificial-intelligence infrastructure deal.',
    'ALLEA: The first High-Level Steering Committee of the International Coalition for Science, Research and Innovation in Ukraine produced and signed the Gdansk Declaration.':'An international research coalition agreed on a common plan to support science, research and innovation in Ukraine.',
    'Euractiv: Irish preparedness confidence fell, while cross-country analysis identified distinct vulnerability profiles linked strongly to psychosocial resources and trust.':'Confidence in preparedness fell in Ireland, while wider European evidence shows that vulnerability differs sharply between countries and is linked to trust and social resources.',
    'EFSA Supporting Publications: EFSA processed 55 emerging-risk topics in 2025, confirmed four as emerging risks, and established an EU Early Warning System for emerging chemical risks.':'European food-safety experts reviewed 55 possible new risks in 2025, confirmed four as emerging risks and created an early-warning system for chemical risks.',
    'JRC Publications Repository: Non-animal methods are advancing across experimental, computational and regulatory domains, but validation and uptake remain uneven.':'Research methods that do not use animals are advancing, but their validation and practical use remain uneven.',
    'EU Digital Strategy: The Commission proposed new EU legislation aimed at strengthening the single market for innovation.':'The EU proposed new rules intended to make it easier for innovation to move and grow across Europe.',
    'JRC Publications Repository: EU27 improves but remains behind the US, South Korea and Japan; Romania, Bulgaria, Slovakia and Latvia rank lowest in the EU.':'Europe is improving, but it still trails the United States, South Korea and Japan on key innovation measures, with large differences between European countries.'
  }));

  const LABEL_PREFIX=/^(?:Why the balance looks this way|What to watch next|Evidence range|Overall assessment|In short|Why it matters here|What the source says|Evidence supporting this scenario|Evidence that could make this scenario less likely):\s*/i;
  const institutionWords=/\b(?:commission|council|centre|center|foundation|institute|university|agency|ministry|repository|publication|society|stiftung|parliament|bank|portal|strategy|research|science|reuters|euractiv|nature|bruegel|ceps|ecfr|oecd|unesco|allea|efsa|eurohpc|jrc|era)\b/i;

  function stripInstitutionLead(s){
    const m=s.match(/^([^:]{2,95}):\s+(.+)$/);
    if(!m)return s;
    const prefix=m[1].trim(), rest=m[2].trim();
    if(LABEL_PREFIX.test(s))return s;
    // Strip obvious publisher/source branding from reader summaries. Attribution remains in evidence details/meta.
    if(institutionWords.test(prefix) || /^[A-Z][A-Z0-9& .–—-]{1,24}$/.test(prefix) || /(?:Journal|Review|Policy|Digital|Innovation|Research|Science)/i.test(prefix))return rest;
    return s;
  }

  function plainify(value,{stripSource=false}={}){
    let s=normalise(value); if(!s)return s;
    if(exact.has(s))s=exact.get(s);
    if(stripSource)s=stripInstitutionLead(s);

    // Repeated generator language -> ordinary prose.
    s=s.replace(/^Current evidence is adding or widening (.+?)(?: as a whole)? through (.+)\.$/i,(_,topic,means)=>`Evidence points to growth in ${topic}, supported by ${means}.`);
    s=s.replace(/^Current evidence (?:is making|shows) (.+?)(?: as a whole)? (?:becoming )?more conditional or constrained through (.+)\.$/i,(_,topic,means)=>`${topic.replace(/^./,c=>c.toUpperCase())} is facing tighter conditions, including ${means}.`);
    s=s.replace(/^Current evidence shows (.+?) expanding through (.+)\.$/i,(_,topic,means)=>`${topic.replace(/^./,c=>c.toUpperCase())} is expanding, supported by ${means}.`);

    // Trend balance language.
    s=s.replace(/^Both sides are still mostly analysis and positions; neither has turned into concrete action yet\.$/i,'Most of the evidence on both sides is still analysis or stated policy rather than action already taken.');
    s=s.replace(/^Both sides are equally concrete:\s*(.+)$/i,'Both directions currently contain a similar amount of action already taken: $1');
    s=s.replace(/^The push is more concrete \((.+?)\) than the pushback \((.+?)\)\.$/i,'There is more evidence of action in the first direction ($1) than in the second ($2).');
    s=s.replace(/^The pushback is more concrete \((.+?)\) than the push \((.+?)\)\.$/i,'There is more evidence of action in the second direction ($1) than in the first ($2).');
    s=s.replace(/^Nothing on either side is pending a decision, so the balance will move only with new evidence\.$/i,'There is no single pending decision likely to change the balance. New evidence will determine the next shift.');
    s=s.replace(/^The next swing depends on “([^”]+)”: if it goes ahead, the push gains; if it stalls, the constraints hold\.$/i,'A key thing to watch is “$1”. Progress would strengthen the first direction; delay or cancellation would strengthen the second.');
    s=s.replace(/^Watch two things: if “([^”]+)” goes ahead, the push wins ground; if “([^”]+)” takes effect, the brakes do\.$/i,'Two developments matter most: “$1” would strengthen the first direction, while “$2” would strengthen the second.');

    // Common jargon.
    const replacements=[
      [/\bR&I\b/g,'research and innovation'],[/\bAI\b/g,'artificial intelligence'],[/\bHPC\b/g,'high-performance computing'],
      [/\bconditionality\b/gi,'conditions'],[/\bleverage\b/gi,'influence'],[/\badmissibility[- ]relevant\b/gi,'required for an application to be accepted'],
      [/\bprocurement\b/gi,'public purchasing'],[/\bregulatory\b/gi,'rule-based'],[/\becosystem\b/gi,'sector'],[/\benterprise adoption\b/gi,'use by companies'],
      [/\badoption\b/gi,'use'],[/\bscale[- ]ups?\b/gi,'growing technology firms'],[/\bcompute access\b/gi,'access to computing power'],[/\bcompute capacity\b/gi,'computing capacity'],
      [/\bdual[- ]use\b/gi,'civilian and military'],[/\bde[- ]risking\b/gi,'reducing risk'],[/\bstrategic autonomy\b/gi,'ability to act with less reliance on others'],
      [/\bstrategic dependencies\b/gi,'important dependencies on outside suppliers or partners'],[/\bchokepoints?\b/gi,'critical bottlenecks'],[/\bbottlenecks?\b/gi,'obstacles'],
      [/\bcommercialisation\b/gi,'turning research into products and companies'],[/\blongitudinal\b/gi,'over time'],[/\bresilience\b/gi,'ability to withstand disruption'],
      [/\bconcrete actions?\b/gi,m=>m.toLowerCase().endsWith('s')?'actions already taken':'action already taken'],[/\bpieces of evidence\b/gi,'sources'],[/\bsignals\b/gi,'pieces of evidence'],
      [/\bdiagnostic finding\b/gi,'finding'],[/\bdiagnosis\b/gi,'finding'],[/\bpushback\b/gi,'evidence in the other direction'],[/\bthe push\b/gi,'the first direction'],
      [/\bas a whole\b/gi,''],[/\bdocumented constraints\b/gi,'identified limits']
    ];
    for(const [re,to] of replacements)s=s.replace(re,to);
    s=s.replace(/\s{2,}/g,' ').replace(/\s+([,.;:!?])/g,'$1').trim();
    return exact.get(s)||s;
  }

  function inEvidence(el){return !!el.closest('details,.evidence,.meta,.sources,.source-list,[data-source],.bibliography');}
  function applyNode(node){
    if(!node||node.nodeType!==Node.TEXT_NODE||!node.parentElement)return;
    const el=node.parentElement;if(SKIP.has(el.tagName))return;
    const raw=node.nodeValue||'', key=normalise(raw);if(!key)return;
    const replacement=plainify(key,{stripSource:!inEvidence(el)});
    if(!replacement||replacement===key)return;
    const lead=(raw.match(/^\s*/)||[''])[0],trail=(raw.match(/\s*$/)||[''])[0];
    node.nodeValue=lead+replacement+trail;
  }
  function applyTree(root){
    if(!root)return;
    if(root.nodeType===Node.TEXT_NODE){applyNode(root);return;}
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let n;while((n=walker.nextNode()))applyNode(n);
  }
  const start=()=>{
    applyTree(document.body);
    const obs=new MutationObserver(muts=>{for(const m of muts){if(m.type==='characterData')applyNode(m.target);for(const n of m.addedNodes||[])applyTree(n)}});
    obs.observe(document.body,{subtree:true,childList:true,characterData:true});
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true}); else start();
})();
