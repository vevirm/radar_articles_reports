(function(root){
'use strict';
const TERMS=[
['Brain circulation','Research talent','Researchers move between countries or sectors but keep returning, collaborating or transferring knowledge.','It can strengthen Europe even when people leave temporarily, if networks and knowledge continue to flow back.'],
['Brain drain','Research talent','A persistent net loss of skilled researchers, engineers or entrepreneurs to other places.','Europe can lose research capacity, firm creation and strategic know-how if high-value talent leaves faster than it is replaced.'],
['Chokepoint','Dependencies','A concentrated node, supplier, technology or infrastructure that many others depend on and that is hard to replace quickly.','Control of a chokepoint can give another actor leverage over European research or industry.'],
['Compute capacity','Digital infrastructure','The amount of computing power that researchers, firms or public bodies can actually use.','Advanced AI and some areas of science increasingly depend on access to very large amounts of compute.'],
['Critical infrastructure','Security','Infrastructure whose disruption would seriously affect essential services, the economy, security or research capability.','Research networks, data centres, energy systems and communications can become geopolitical pressure points.'],
['Critical raw materials','Supply chains','Materials that are economically important and exposed to significant supply risk.','Many strategic technologies depend on inputs Europe cannot easily substitute in the short term.'],
['Critical technology','Technology policy','A technology considered important for economic strength, security or essential public functions.','Such technologies attract more public funding, protection, screening and international competition.'],
['Decoupling','Geoeconomics','A broad separation of trade, investment, technology or research ties between countries or blocs.','Full separation can reduce some security risks but also raise costs and reduce scientific or commercial exchange.'],
['De-risking','Geoeconomics','Reducing selected dependencies or vulnerabilities without trying to end most economic or research ties.','The EU often uses this idea when it wants more resilience without broad economic separation.'],
['Dual-use','Security and research','A technology, product or research result that can have both civilian and military or security uses.','Security demand can change who funds research, who may access it, which partners are acceptable and how results are controlled.'],
['Economic security','Geoeconomics','Protecting economic and technological strengths from coercion, leakage or dangerous dependencies while keeping useful openness.','It links trade, investment, technology and research policy to security concerns.'],
['Emerging technology','Technology policy','A technology that is developing quickly and may become strategically important, but whose effects are still uncertain.','Early leadership can shape future industries, standards and dependencies.'],
['European preference','Industrial policy','A policy choice that gives some advantage to European suppliers, production or capabilities.','It can help build capacity in Europe, but may also increase costs or create trade tensions.'],
['Export controls','Policy tool','Rules that restrict the export or transfer of certain goods, software, technology or know-how.','They can limit collaboration and market access in areas such as advanced chips, AI, quantum or defence-related technologies.'],
['FDI screening','Investment policy','Government review of incoming foreign direct investment for security or public-order risks.','It can affect foreign ownership of sensitive European firms, infrastructure and technologies.'],
['Foreign interference','Research security','Covert, deceptive or coercive activity by an external actor intended to influence or exploit institutions and people.','Universities and research organisations may need safeguards that go beyond normal research-integrity rules.'],
['Foundry','Semiconductors','A company or facility that manufactures semiconductor chips, often for other companies that design them.','Foundry capacity is concentrated globally, so access can become a strategic dependency.'],
['Friend-shoring','Supply chains','Moving sourcing or production toward countries considered politically or strategically trusted.','It can lower geopolitical risk, but may reduce supplier choice or increase costs.'],
['Frontier compute','Digital infrastructure','Very advanced, large-scale computing used for leading-edge AI and computational science.','Who can access frontier compute increasingly affects who can perform the most demanding research and develop frontier AI systems.'],
['Geoeconomics','Geopolitics','The use of economic tools and economic relationships as instruments of geopolitical power or competition.','Trade, investment, subsidies, technology controls and supply dependencies can shape Europe’s R&amp;I choices.'],
['Horizon Europe association','EU programmes','An agreement that lets a non-EU country participate in Horizon Europe under negotiated conditions, often with access similar to Member States in many calls.','Association changes who can collaborate and compete for EU research funding.'],
['Intellectual property (IP)','Research and firms','Legal rights over inventions, designs, creative works, software, brands or confidential know-how.','Control of IP can determine who captures value from European research and who may use strategic technologies.'],
['Knowledge security','Research security','Protecting sensitive knowledge, data, people and research relationships from unwanted transfer, misuse or coercion.','It is central when openness in science conflicts with security or technology-control concerns.'],
['Knowledge valorisation','Research and firms','Turning research results and knowledge into economic, social or public value.','Europe can be strong in research yet weak at converting discoveries into scaled firms, products or public capabilities.'],
['Near-shoring','Supply chains','Moving production or sourcing geographically closer to the home market.','Shorter supply chains can improve resilience but do not automatically remove geopolitical dependence.'],
['Open science','Research system','Making research outputs, data, methods or processes more accessible and reusable when appropriate.','The policy challenge is preserving openness while managing legitimate security, privacy and IP concerns.'],
['Open strategic autonomy','EU strategy','The ability to act independently in important areas while remaining open to trade, investment and international cooperation.','It captures the EU attempt to reduce dangerous dependencies without becoming economically or scientifically closed.'],
['Outbound investment screening','Investment policy','Reviewing or restricting investments made by domestic actors into sensitive technologies or sectors abroad.','It aims to prevent capital and know-how from strengthening capabilities considered security risks.'],
['Pre-commercial procurement','Innovation policy','Public bodies buy research and development services to develop solutions before a normal commercial product exists.','It can create demand for new European technology and help bridge the gap between research and deployment.'],
['Public procurement','Innovation policy','Goods and services bought by governments and other public bodies.','Large public buyers can create early markets, influence standards and help strategic technologies scale.'],
['Research infrastructure','Research system','Facilities, equipment, data resources, computing systems and networks that researchers need to do research.','Dependence on scarce infrastructures can determine where research can be done and who controls access.'],
['Research security','Research security','Policies and practices that protect research from theft, misuse, interference or harmful dependencies while preserving legitimate collaboration.','It affects partnerships, access to facilities, data handling, talent policy and international cooperation.'],
['Scale-up','Firms and finance','A company that has moved beyond the earliest startup stage and is trying to grow rapidly in customers, staff, production or markets.','Europe often produces strong startups but struggles to keep and finance firms as they grow to global scale.'],
['Science diplomacy','International cooperation','The interaction between science and foreign policy: science can support diplomacy, and diplomacy can enable scientific cooperation.','Research partnerships can maintain relationships, build influence or become harder when geopolitical tensions rise.'],
['Security of supply','Supply chains','Confidence that essential inputs, equipment, services or capabilities will remain available when needed.','It matters when Europe relies on a small number of external suppliers for strategic research or industrial capability.'],
['Semiconductor fab','Semiconductors','A fabrication plant where semiconductor chips are physically manufactured.','Fabs are extremely expensive and geographically concentrated, so production location matters for resilience and strategic control.'],
['Sovereign cloud','Digital infrastructure','Cloud arrangements designed to meet stronger requirements on jurisdiction, data control, operational control or trusted providers.','They are intended to reduce exposure to foreign legal or technological dependence in sensitive uses.'],
['Spin-off / spinout','Research and firms','A new company created to commercialise knowledge or technology originating in a university, laboratory or other organisation.','Spinouts are one route for turning European research into firms and strategic industrial capability.'],
['Standard-setting','Rules and standards','The process by which technical, safety, interoperability or industry standards are developed and agreed.','Actors that shape widely used standards can influence markets, technologies and regulatory expectations.'],
['Standards power','Rules and standards','Influence that comes from shaping standards that others adopt because they want access, compatibility or market acceptance.','Europe can exercise global influence even when it does not dominate production, if its rules or standards become widely used.'],
['Strategic autonomy','EU strategy','The capacity to make and carry out important choices without being blocked by excessive dependence on others.','For R&amp;I, this concerns access to talent, infrastructure, technology, finance and supply chains.'],
['Strategic dependency','Dependencies','Reliance on an external supplier, country, technology or capability that is important and difficult to replace.','A dependency becomes geopolitical when another actor can exploit it or when disruption would seriously weaken European capability.'],
['Technology leakage','Research security','Sensitive know-how or capability moves to another actor in a way policymakers or organisations did not intend or consider safe.','It is one reason collaborations, investment and access to research may face additional controls.'],
['Technology readiness level (TRL)','Innovation policy','A 1-to-9 scale commonly used in EU programmes to describe how mature a technology is, from basic principles to proven operation.','Funding and policy tools often target different TRLs, so the scale helps show where an innovation is between research and deployment.'],
['Technology sovereignty','Technology policy','Having sufficient control, capability or assured access to technologies considered strategically important.','The goal is not necessarily to make everything in Europe, but to avoid being unable to act because critical technology is controlled elsewhere.'],
['Technology transfer','Research and firms','Moving knowledge, intellectual property or technology from a research organisation to a company, public body or other user.','Effective transfer helps convert research excellence into economic and strategic capability.'],
['Third country','EU terminology','In EU policy language, a country that is outside the European Union. It does not mean the country is hostile or unimportant.','The term appears frequently in rules on research participation, data, investment and international cooperation.'],
['Trusted research','Research security','An approach to international research that tries to keep collaboration open while identifying and managing security, integrity and dependency risks.','It gives researchers and institutions a practical framework for deciding when extra safeguards are needed.'],
['Valley of death','Innovation finance','The difficult stage between a promising research result and a product or company that can attract enough commercial finance and customers.','European technologies can fail to scale if funding, demonstration or early demand disappears at this stage.'],
['Bibliographic coupling','Foresight methods','A similarity measure based on two publications citing some of the same earlier sources.','It can reveal emerging research fronts before a mature field name is widely used.'],
['Change-point detection','Foresight methods','Statistical methods for identifying when the behaviour of a time series or stream changes materially.','It can flag breaks in publication, patent, funding or collaboration patterns that deserve strategic attention.'],
['Citation burst','Foresight methods','A sharp temporary increase in citations to a publication, topic or reference.','Bursts can help identify fast-rising research fronts before conventional indicators catch up.'],
['Co-citation analysis','Foresight methods','Mapping how often two publications or authors are cited together by later work.','It can expose changing intellectual clusters and the structure behind an emerging technology field.'],
['Dynamic topic model','Foresight methods','A topic model designed to track how latent themes change across time slices.','It can detect vocabulary and topic shifts that ordinary static keyword counts miss.'],
['Horizon scanning','Foresight methods','A structured process for finding early evidence of emerging change, risks and opportunities.','It helps the Radar search beyond already-established policy language and identify developments before they become mainstream.'],
['Novelty detection','Foresight methods','Methods that identify observations, combinations or texts that differ materially from an established reference set.','For weak signals, novelty is useful as a candidate generator but does not replace evidence and relevance checks.'],
['Research front','Foresight methods','A relatively coherent cluster of recent research activity forming around a shared problem, method or technology.','Tracking research fronts can show where capability and competition are moving before journal categories or policy labels catch up.'],
['Semantic shift','Foresight methods','A measurable change in how a word or concept is used across time or contexts.','It can reveal narrative change, such as collaboration language moving closer to security, screening or risk language.'],
['Technology intelligence','Foresight methods','Systematic collection and analysis of evidence about technologies, actors, capabilities and trajectories.','It connects papers, patents, firms and policy signals into a view of where strategic technology competition may be moving.'],
['Emerging topic detection','Foresight methods','Computational methods for identifying research themes that are forming or accelerating.','It can generate candidates before a field has a stable label, but the Radar still requires substantive evidence before admission.'],
['Temporal embeddings','Foresight methods','Representations designed to track how words, entities or relationships move across time.','They can help detect changing concepts or networks, while the final Radar judgement remains evidence-based.'],
['Dynamic community detection','Foresight methods','Network methods for identifying communities that form, split or merge through time.','It can reveal changing research or technology collaboration structures before aggregate indicators show the shift.'],
['Graph anomaly detection','Foresight methods','Methods for identifying unusual nodes, links or structural changes in a network.','It can flag unexpected collaboration or technology-network changes for later evidence checking.'],
['Weak signal','Foresight methods','An early, incomplete indication of change whose significance depends on its relationship to established evidence.','In this Radar, a weak signal is temporary, lasts 60 days and must be anchored to relevant Strand A evidence.'],
['Weaponised interdependence','Geoeconomics','Using control over important networks, technologies, finance or supply chains to monitor, pressure or constrain other actors.','It explains why ordinary economic or research dependencies can become sources of geopolitical power.']
].map(([term,category,meaning,why])=>({term,category,meaning,why})).sort((a,b)=>a.term.localeCompare(b.term,'en',{sensitivity:'base'}));
const ALIASES=[
  ['dual use','Dual-use'],['dual-use','Dual-use'],
  ['de-risking','De-risking'],['derisking','De-risking'],
  ['research security','Research security'],['knowledge security','Knowledge security'],
  ['open science','Open science'],['science diplomacy','Science diplomacy'],
  ['frontier compute','Frontier compute'],['compute capacity','Compute capacity'],
  ['critical raw materials','Critical raw materials'],['critical infrastructure','Critical infrastructure'],
  ['research infrastructure','Research infrastructure'],
  ['strategic autonomy','Strategic autonomy'],['open strategic autonomy','Open strategic autonomy'],
  ['strategic dependency','Strategic dependency'],['strategic dependencies','Strategic dependency'],
  ['technology sovereignty','Technology sovereignty'],['technology leakage','Technology leakage'],
  ['technology transfer','Technology transfer'],
  ['export controls','Export controls'],['export control','Export controls'],
  ['fdi screening','FDI screening'],
  ['foreign interference','Foreign interference'],
  ['economic security','Economic security'],['geoeconomics','Geoeconomics'],
  ['friend-shoring','Friend-shoring'],['near-shoring','Near-shoring'],
  ['security of supply','Security of supply'],
  ['scale-up','Scale-up'],['scaleup','Scale-up'],
  ['public procurement','Public procurement'],['pre-commercial procurement','Pre-commercial procurement'],
  ['standard-setting','Standard-setting'],['standards power','Standards power'],
  ['third country','Third country'],['trusted research','Trusted research'],
  ['brain drain','Brain drain'],['brain circulation','Brain circulation'],
  ['chokepoint','Chokepoint'],['decoupling','Decoupling'],
  ['technology readiness level','Technology readiness level (TRL)'],['trl','Technology readiness level (TRL)'],
  ['intellectual property','Intellectual property (IP)'],['ip','Intellectual property (IP)'],
  ['semiconductor fab','Semiconductor fab'],['foundry','Foundry'],
  ['spinout','Spin-off / spinout'],['spin-off','Spin-off / spinout'],
  ['valley of death','Valley of death'],['weaponised interdependence','Weaponised interdependence'],
  ['horizon scanning','Horizon scanning'],['weak signal','Weak signal'],['weak signals','Weak signal'],
  ['technology intelligence','Technology intelligence'],['research front','Research front'],
  ['emerging topic detection','Emerging topic detection'],['temporal embeddings','Temporal embeddings'],['temporal embedding','Temporal embeddings'],
  ['dynamic community detection','Dynamic community detection'],['graph anomaly detection','Graph anomaly detection'],['network anomaly detection','Graph anomaly detection'],
  ['citation burst','Citation burst'],['change-point detection','Change-point detection'],['changepoint detection','Change-point detection'],
  ['semantic shift','Semantic shift'],['novelty detection','Novelty detection'],['dynamic topic model','Dynamic topic model'],
  ['bibliographic coupling','Bibliographic coupling'],['co-citation analysis','Co-citation analysis']
];
const byTerm=new Map(TERMS.map(x=>[x.term.toLowerCase(),x]));
const aliasRows=ALIASES.map(([alias,term])=>({alias,term:byTerm.get(term.toLowerCase())})).filter(x=>x.term).sort((a,b)=>b.alias.length-a.alias.length);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function slug(s){return String(s||'').toLowerCase().replace(/&/g,'and').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')}
function lookup(name){return byTerm.get(String(name||'').toLowerCase())||null}
function find(text,max=4){
  const s=String(text||''), lower=s.toLowerCase(), hits=[], seen=new Set();
  for(const row of aliasRows){
    if(seen.has(row.term.term))continue;
    let from=0;
    while(true){
      const i=lower.indexOf(row.alias,from); if(i<0)break;
      const before=i?lower[i-1]:'', after=lower[i+row.alias.length]||'';
      const okBefore=!before||!/[_a-z0-9]/.test(before), okAfter=!after||!/[_a-z0-9]/.test(after);
      if(okBefore&&okAfter){hits.push({index:i,length:row.alias.length,term:row.term});seen.add(row.term.term);break}
      from=i+row.alias.length;
    }
  }
  return hits.sort((a,b)=>a.index-b.index).slice(0,Math.max(0,max));
}
function annotate(text,max=4){
  const s=String(text||''), hits=find(s,max); if(!hits.length)return esc(s);
  let out='',pos=0;
  for(const h of hits){
    if(h.index<pos)continue;
    out+=esc(s.slice(pos,h.index));
    const shown=s.slice(h.index,h.index+h.length);
    out+=`<span class="glossary-inline" title="${esc(h.term.meaning)}" data-glossary="${esc(h.term.term)}">${esc(shown)}</span>`;
    pos=h.index+h.length;
  }
  return out+esc(s.slice(pos));
}
function simpleDefinitions(text,max=3){return find(text,max).map(h=>h.term)}
root.RadarGlossary={terms:TERMS,lookup,slug,find,simpleDefinitions,annotate};
})(typeof globalThis!=='undefined'?globalThis:this);
