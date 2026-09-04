/* v17.20.24 — one-shot, non-persistent shock hypothesis constructor.
   Source-merit scores assign evidence roles only. They never rank shocks or hypotheses. */
(function(root,factory){
  const api=factory(root.RadarSourceMerit||(typeof require==='function'?require('../source_merit.js'):null));
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.RadarShockToy=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(Merit){
  'use strict';

  const BANNED=/\b(?:strategic autonomy|technological sovereignty|geopolitics|dual[- ]use|critical raw materials|science diplomacy|research security|export control|de-risking)\b/i;
  const MECHANISM_AUTH=/peer-reviewed|policy research institute|academic publisher/i;

  function clean(v){return String(v||'').replace(/\s+/g,' ').trim()}
  function norm(v){return clean(v).toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()}
  function titleOf(x){return clean(x.title||x.headline||x.what||'Untitled evidence')}
  function sourceOf(x){return clean(x.source||x.journal||x.institution||'Unknown source')}
  function dateOf(x){return clean(x.date||'').slice(0,10)}
  function linkOf(x){return clean(x.link||x.url||'')}
  function scoreOf(x){return Merit?.scoreFor?Number(Merit.scoreFor(x))||0:Number(x.quality||0)}
  function meritOf(x){return Merit?.forItem?Merit.forItem(x):{score:scoreOf(x),authority:''}}
  function euOfficial(x){return Merit?.isEuOfficial?!!Merit.isEuOfficial(sourceOf(x),linkOf(x)):false}
  function firstSentence(v,max=230){let s=clean(v);if(!s)return '';const m=s.match(/^(.{18,}?[.!?])(?:\s|$)/);if(m)s=m[1];if(s.length>max)s=s.slice(0,max-1).replace(/\s+\S*$/,'')+'…';return s}
  function excerpt(x){return firstSentence(x.what||x._usableCore||x.summary||x.signal_note||x.relevance_note||titleOf(x))}
  function primaryText(x){return clean([x.title,x.headline,x.what,x._usableCore].filter(Boolean).join(' '))}
  function titleText(x){return clean([x.title,x.headline].filter(Boolean).join(' '))}
  function quoteFor(x,re){const fields=[x.what,x._usableCore,x.summary,x.signal_note,x.relevance_note,titleOf(x)].filter(Boolean);for(const f of fields){const bits=clean(f).match(/[^.!?]+[.!?]?/g)||[clean(f)];for(const bit of bits)if(re&&re.test(bit))return firstSentence(bit)}return excerpt(x)}
  function rand(rng,n){return Math.max(0,Math.min(n-1,Math.floor((rng?rng():Math.random())*n)))}
  function pickRandom(xs,rng){return xs.length?xs[rand(rng,xs.length)]:null}
  function titleTokens(v){return new Set(norm(v).split(' ').filter(t=>t.length>3))}
  function similarity(a,b){const A=titleTokens(a),B=titleTokens(b);if(!A.size||!B.size)return 0;let n=0;for(const t of A)if(B.has(t))n++;return n/Math.min(A.size,B.size)}
  function claimContained(claim,rowText){const ts=norm(claim).split(' ').filter(t=>t.length>4);if(ts.length<7)return false;const hay=new Set(norm(rowText).split(' '));let hit=0;for(const t of ts)if(hay.has(t))hit++;return hit/ts.length>=0.80}
  function rowText(x){return clean([x.title,x.headline,x.what,x.summary,x._usableCore,x.relevance_note,x.signal_note,x.why_it_matters,...(x.eu_evidence||[]),...(x.ri_evidence||[]),...(x.geo_evidence||[]),...(x.a_context_evidence||[])].filter(Boolean).join(' '))}

  function prepareCorpus(data){
    const raw=[];
    for(const [strand,key] of [['A','strand_a'],['B','strand_b'],['C','strand_c']])for(const x0 of Array.isArray(data?.[key])?data[key]:[])raw.push({...x0,_strand:strand});
    const repeated=new Map();
    for(const x of raw){const c=norm(x.core_message);if(c&&c.length>35)repeated.set(c,(repeated.get(c)||0)+1)}
    const seen=new Set(),rows=[];
    for(const x of raw){const t=norm(titleOf(x));if(!t||seen.has(t))continue;seen.add(t);const c=norm(x.core_message);x._usableCore=c&&repeated.get(c)>=3?'':clean(x.core_message);x._toyText=rowText(x);x._toyScore=scoreOf(x);x._toyMerit=meritOf(x);rows.push(x)}
    return rows;
  }

  const LANES=[
    {
      id:'measurement_layer',
      event:x=>x._toyScore<78&&!euOfficial(x)&&/Preprint/i.test(clean(x._toyMerit?.authority))&&/\b(?:openalex|scopus|bibliographic|citation database|research database)\b/i.test(primaryText(x))&&/\b(?:vs\.?|versus|comparison|coverage)\b/i.test(primaryText(x)),
      surface:x=>/\b(?:European innovation scoreboard|research assessment)\b/i.test(titleText(x)),
      mechanism:x=>/\b(?:performance-based funding|funding evaluation|governance by measurement|composite indicators)\b/i.test(titleText(x))&&/\b(?:indicator|measurement|funding|evaluation)\b/i.test(x._toyText),
      eventQuote:/\b(?:openalex|scopus|bibliographic|citation database)\b/i,
      surfaceQuote:/\b(?:scoreboard|research assessment|indicator)\b/i,
      mechanismQuote:/\b(?:invalid indicator|performance indicator|funding|measurement|evaluation)\b/i,
      shock:'A change in a privately controlled research-information layer could move the numbers used to judge or fund European research even when the underlying science has not changed.',
      effect:'If the measurement layer changes while the allocation or assessment rule stays fixed, money or institutional judgement can move before research performance itself does.',
      usual:'The usual framing sees a measurement-quality problem; this hypothesis watches the moment a technical measurement change becomes an allocation decision.',
      indicator:'A major research database changes coverage, access, ownership or field definitions and an EU or national indicator moves without a matching change in underlying research output.'
    },
    {
      id:'foreign_restriction_research',
      event:x=>x._toyScore<78&&!euOfficial(x)&&x._strand==='C'&&/\bchina|chinese\b/i.test(primaryText(x))&&/\b(?:entity list|barring|barred|restriction|controlled exports?)\b/i.test(primaryText(x))&&/\b(?:eu entit(?:y|ies)|research organisations?|research organizations?|technology organisations?|technology organizations?)\b/i.test(primaryText(x)),
      surface:x=>/\b(?:European Innovation Council opens to defence and dual-use technologies|JRC Security Research and Innovation Campus|Dual-Use Regulation)\b/i.test(titleText(x)),
      mechanism:x=>/\b(?:dual-use by design research|Dual-use and Defence Research|research security)\b/i.test(titleText(x))&&/\b(?:universit|research institut|compliance|export control|restricted technolog|screening)\b/i.test(x._toyText),
      eventQuote:/\b(?:entity list|barring|barred|controlled exports?|restriction)\b/i,
      surfaceQuote:/\b(?:research|defence|dual-use|security)\b/i,
      mechanismQuote:/\b(?:universit|research institut|compliance|export control|screening|dual-use)\b/i,
      shock:'A foreign restriction aimed at European entities could stop work inside university or research institutes before it becomes visible as an industrial shortage.',
      effect:'Once specialised inputs or permissions sit inside ordinary research projects, a restriction can interrupt experiments and collaborations even when no European programme is cancelled.',
      usual:'The usual framing sees export control as something Europe applies outward; this hypothesis watches European research organisations becoming the operational target.',
      indicator:'A European university or public research organisation reports that a named component, instrument, licence or collaboration has become unavailable because it is covered by a third-country restriction.'
    },
    {
      id:'specific_substitute_blindspot',
      event:x=>x._toyScore<78&&!euOfficial(x)&&x._strand==='C'&&/\bchina|chinese\b/i.test(primaryText(x))&&/\b(?:entity list|barring|barred|restriction|controlled exports?)\b/i.test(primaryText(x)),
      surface:x=>/\b(?:Research infrastructures|Quantum Experimental Pilot Lines|JRC Security Research and Innovation Campus)\b/i.test(titleText(x)),
      mechanism:x=>/\bA self-reliance framework for identifying strategic advanced materials\b/i.test(titleText(x))&&/\bEuropean-sourced substitutes?\b/i.test(x._toyText)&&/\bcomparable performance\b/i.test(x._toyText),
      eventQuote:/\b(?:controlled exports?|restriction|entity list|barring)\b/i,
      surfaceQuote:/\b(?:research infrastructure|pilot line|laborator|quantum)\b/i,
      mechanismQuote:/\b(?:European-sourced substitutes?|comparable performance)\b/i,
      shock:'A lab-specific input could disappear even while broad substitute assessments say Europe has comparable alternatives for the material class.',
      effect:'Research needs an exact property and an already-qualified input, so a reassuring class-level substitute can coexist with a project-level stoppage.',
      usual:'The usual framing sees whether substitutes exist at material-class level; this hypothesis asks whether the exact reagent, crystal, isotope, chip grade or component a laboratory uses has ever been qualified.',
      indicator:'A laboratory or pilot facility delays work because the available European substitute matches broad performance measures but cannot yet replace the exact input in the experiment or process.'
    },
    {
      id:'partner_funding_shock',
      event:x=>x._toyScore<78&&!euOfficial(x)&&/Preprint/i.test(clean(x._toyMerit?.authority))&&/\b(?:declines? in research funding|funding cut|rapid declines?|science ecosystem fragility)\b/i.test(primaryText(x))&&/\b(?:United States|US|U\.S\.)\b/i.test(x._toyText),
      surface:x=>/\b(?:Horizon Europe association|International cooperation with|Global approach to research and innovation)\b/i.test(titleText(x)),
      mechanism:x=>/\b(?:Research funding, science production, and international collaborations|Bi-national academic funding and collaboration dynamics)\b/i.test(titleText(x)),
      eventQuote:/\b(?:declines? in research funding|funding cut|scientific collaboration|science ecosystem fragility)\b/i,
      surfaceQuote:/\b(?:association|international cooperation|research and innovation)\b/i,
      mechanismQuote:/\b(?:research funding|international collaboration|collaboration dynamics|collaborations)\b/i,
      shock:'A sudden research-funding cut in a partner country could remove people and project tasks from European collaborations while every European grant remains formally intact.',
      effect:'The shock enters through the partner’s lost capacity, so the European project can keep its legal consortium yet lose researchers, facilities or work packages it cannot immediately replace.',
      usual:'The usual framing watches European funding and formal association agreements; this hypothesis watches whether foreign partners can still carry the tasks those agreements assume.',
      indicator:'An EU-funded consortium starts redistributing work or extending deadlines because a non-European partner has lost staff, facilities or matching research funding.'
    },
    {
      id:'talent_pull',
      event:x=>x._toyScore<78&&!euOfficial(x)&&x._strand==='C'&&/\b(?:India|Canada|United States|US|UK|United Kingdom|China)\b/i.test(primaryText(x))&&/\b(?:lure scientists? back|lure researchers? back|recruit scientists?|recruit researchers?|attract scientists?|attract researchers?)\b/i.test(primaryText(x)),
      surface:x=>/\b(?:Choose Europe for Science|Talent for Innovation Attraction Platform|keep brightest tech talents|HPC Skills)\b/i.test(titleText(x)),
      mechanism:x=>/\b(?:brain drain|researcher mobility|Doctor Mobility|research talent|researcher retention|job offers)\b/i.test(titleText(x)),
      eventQuote:/\b(?:lure|recruit|attract|scientist|researcher)\b/i,
      surfaceQuote:/\b(?:talent|science|skills|researcher)\b/i,
      mechanismQuote:/\b(?:brain drain|mobility|job offer|retention|researcher|talent)\b/i,
      shock:'A successful recruitment drive abroad could leave a newly funded European research capability short of a narrow specialist workforce just as it comes online.',
      effect:'The capital and equipment remain, but the operating bottleneck moves to the small group of researchers able to run the facility, method or programme.',
      usual:'The usual framing sees talent attraction and infrastructure investment as separate policy files; this hypothesis treats specialist staffing as an operating condition of the investment.',
      indicator:'A newly funded European facility repeatedly advertises the same specialist roles, delays commissioning or becomes unusually dependent on recruiting from one external labour market.'
    },
    {
      id:'quantum_subsidy_pull',
      event:x=>x._toyScore<78&&!euOfficial(x)&&x._strand==='C'&&/\b(?:Canada|Japan|United States|US|China)\b/i.test(primaryText(x))&&/\bquantum\b/i.test(primaryText(x))&&/\b(?:invest|fund|funding|partnership)\b/i.test(primaryText(x)),
      surface:x=>/\b(?:Quantum|EuroHPC.*quantum|quantum.*EuroHPC)\b/i.test(titleText(x)),
      mechanism:x=>/\b(?:Beyond the European Chips Act|Revamping Europe’s chips strategy|semiconductor.*supply|chips strategy)\b/i.test(titleText(x))&&/\b(?:supplier|supply chain|dependenc|capacity|chokepoint)\b/i.test(x._toyText),
      eventQuote:/\b(?:quantum|invest|fund|partnership|supply chain)\b/i,
      surfaceQuote:/\b(?:quantum|skills|pilot|access|computer)\b/i,
      mechanismQuote:/\b(?:supplier|supply chain|dependenc|capacity|chokepoint)\b/i,
      shock:'A subsidy push elsewhere could absorb a scarce supplier or fabrication slot that European quantum programmes assume will still be available when their own capacity scales.',
      effect:'The European programme can be fully funded yet arrive second to the supplier, component or fabrication capacity on which commissioning depends.',
      usual:'The usual framing compares headline investment totals; this hypothesis watches the few suppliers and specialists that several national programmes may be trying to buy at the same time.',
      indicator:'A European quantum project reports longer lead times, supplier exclusivity or repeated specialist vacancies after a major non-European funding programme expands.'
    }
  ];
  function laneForEvent(x){return LANES.filter(l=>l.event(x))}
  function validSurface(x,l,event){return x._toyScore>=93&&euOfficial(x)&&sourceOf(x)!==sourceOf(event)&&l.surface(x)}
  function validMechanism(x,l,event,surface){if(x._toyScore<75||x._toyScore>92)return false;if(!MECHANISM_AUTH.test(clean(x._toyMerit?.authority)))return false;if(sourceOf(x)===sourceOf(event)||sourceOf(x)===sourceOf(surface))return false;if(!l.mechanism(x))return false;if(similarity(titleOf(x),titleOf(event))>.55||similarity(titleOf(x),titleOf(surface))>.55)return false;return true}
  function contribution(role,x,l){const re=role==='event'?l.eventQuote:role==='surface'?l.surfaceQuote:l.mechanismQuote;const e=quoteFor(x,re)||titleOf(x);if(role==='event')return `Carries the outside event: ${e}`;if(role==='surface')return `Defines the European commitment or capability the event could hit: ${titleOf(x)}`;return `Explains how a change in that layer can turn into a research effect: ${e}`}
  function snapshot(role,x,l){return {role,score:x._toyScore,source:sourceOf(x),date:dateOf(x),title:titleOf(x),link:linkOf(x),contribution:contribution(role,x,l)}}
  function novel(l,rows){return !BANNED.test(l.shock)&&!rows.some(x=>claimContained(l.shock,x._toyText))}
  function build(event,l,rows,rng){
    const surfaces=rows.filter(x=>validSurface(x,l,event));if(!surfaces.length)return {fail:'European commitment/capability'};
    const surface=pickRandom(surfaces,rng);
    const mechanisms=rows.filter(x=>validMechanism(x,l,event,surface));if(!mechanisms.length)return {fail:'explanatory middle-band source'};
    const mechanism=pickRandom(mechanisms,rng);
    if(new Set([sourceOf(event),sourceOf(surface),sourceOf(mechanism)]).size!==3)return {fail:'three different sources'};
    if(!(event._toyScore<78&&surface._toyScore>=93&&mechanism._toyScore>=75&&mechanism._toyScore<=92))return {fail:'source-role score bands'};
    if(!novel(l,rows))return {fail:'novelty / usual-framing check'};
    const path=[
      `${sourceOf(event)} reports or observes: ${quoteFor(event,l.eventQuote)||titleOf(event)}`,
      `${sourceOf(surface)} shows the European commitment or capability the event could hit: ${titleOf(surface)}`,
      `${sourceOf(mechanism)} provides the mechanism: ${quoteFor(mechanism,l.mechanismQuote)||titleOf(mechanism)}`,
      l.effect
    ];
    return {ok:true,lane:l.id,shock:l.shock,sources:[snapshot('event',event,l),snapshot('surface',surface,l),snapshot('mechanism',mechanism,l)],path,usual:l.usual,indicator:l.indicator,disclaimer:'a constructed hypothesis drawn from the corpus, asserted by no source in it, not admitted, not retained.'};
  }
  function construct(data,opts={}){
    const rows=prepareCorpus(data),rng=typeof opts.rng==='function'?opts.rng:Math.random;
    const events=rows.filter(x=>laneForEvent(x).length);if(!events.length)return {ok:false,attempts:0,message:'No eligible low-score outside event is currently present. The corpus may be thin in current-event, foreign, specialist or preprint evidence.'};
    const pool=[...events],fails={};let lastLane='';let attempts=0;
    while(attempts<5&&pool.length){attempts++;const event=pool.splice(rand(rng,pool.length),1)[0];const lanes=laneForEvent(event);const l=pickRandom(lanes,rng);lastLane=l?.id||'';if(!l){fails['outside-event classification']=(fails['outside-event classification']||0)+1;continue}const r=build(event,l,rows,rng);if(r.ok)return {...r,attempts};fails[r.fail]=(fails[r.fail]||0)+1}
    const worst=Object.entries(fails).sort((a,b)=>b[1]-a[1])[0];const check=worst?.[0]||'cross-source connection';
    return {ok:false,attempts,failedCheck:check,message:`Stopped after ${attempts} failed attempt${attempts===1?'':'s'}. The check that failed most often was ${check}. ${lastLane?`The corpus has an outside event around ${lastLane.replace(/_/g,' ')}, but not enough independent evidence to connect it safely without inventing a bridge.`:'The corpus does not contain enough independent evidence to build a short checkable path.'}`};
  }

  return {construct,prepareCorpus,lanes:LANES,banned:BANNED};
});
