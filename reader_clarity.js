/* Reader clarity layer v1.
   Presentation only. It does not change Radar records, findings, scoring, selection,
   reasoning, or 2035 scenario generation. It turns already-selected material into
   a broader reader-facing point and an explicit "why it matters" line.

   Deliberately conservative: when no safe, topic-level restatement is available,
   the original reader copy is kept. */
(function(g){
  'use strict';
  const clean=v=>String(v??'').replace(/\s+/g,' ').replace(/\s+([,.;:!?])/g,'$1').replace(/([,;:])\s*([,.;:!?])/g,'$2').trim();
  const sentence=v=>{let t=clean(v);if(!t)return '';return /[.!?]$/.test(t)?t:`${t}.`};
  const low=v=>clean(v).toLowerCase();

  const TOPICS=[
    [/open science|research openness|open research|research security|sensitive knowledge/, 'openness'],
    [/compute|supercomput|data cent(?:re|er)|ai factor|gigafactor/, 'compute'],
    [/research workforce|research talent|researcher|career|skills|brain drain/, 'talent'],
    [/scale[- ]?up|venture capital|growth finance|commerciali[sz]|startup|deep[- ]tech/, 'scaleup'],
    [/chip|semiconductor|microelectronic/, 'chips'],
    [/critical material|raw material|advanced material|battery|supply chain/, 'materials'],
    [/energy|hydrogen|electricity|power squeeze|grid/, 'energy'],
    [/research collaboration|science diplomacy|international research|horizon.*access|association/, 'collaboration'],
    [/data protection|digital governance|ai governance|rulebook|regulation|standard/, 'governance'],
    [/regional innovation|cohesion|regional capacity/, 'regional'],
    [/research infrastructure|laborator|facility/, 'infrastructure'],
    [/strategic investment|private investment|strategic spending|public programme|research funding|horizon budget|funding|subsid|programme budget/, 'funding'],
    [/defence|defense|dual[- ]use/, 'defence'],
    [/health[- ]data|clinical research/, 'healthdata'],
    [/green technology|clean tech|climate tech/, 'greentech'],
    [/innovation performance|productivity|industrial competitiveness/, 'competitiveness']
  ];
  function topic(...parts){const t=low(parts.filter(Boolean).join(' '));for(const [rx,k] of TOPICS)if(rx.test(t))return k;return ''}

  const WHY={
    openness:'Europe needs international and open research to create knowledge, but it also needs to protect sensitive capabilities. How that balance is struck affects both scientific reach and security.',
    compute:'Access to large-scale computing increasingly determines who can develop advanced AI and other data-intensive technologies. Capacity that exists on paper matters only if European researchers and firms can actually use it.',
    talent:'Funding and facilities do not become research capability without people. Europe’s ability to attract, retain and deploy specialised talent therefore sets a practical limit on what it can build.',
    scaleup:'Europe can produce strong research without capturing the resulting companies, jobs and industrial capability. The scale-up stage determines whether research strength becomes durable economic capacity in Europe.',
    chips:'Semiconductors sit upstream of many strategic technologies. Dependence on outside production, equipment or inputs can therefore constrain several European technology sectors at once.',
    materials:'Strategic technologies depend on a small number of specialised materials and supply chains. Bottlenecks upstream can delay research, pilots and industrial production long before final demand weakens.',
    energy:'Energy security is not only about adding supply. Cost, reliability, storage and grid constraints determine whether European research and industrial capacity can operate when conditions change.',
    collaboration:'International partnerships expand Europe’s access to talent, knowledge and infrastructure, but they also create exposure to political, legal and security restrictions. The terms of access increasingly matter as much as the partnership itself.',
    governance:'European rules can shape markets and technical choices, but regulation only creates strategic leverage if implementation keeps pace with technology and investment.',
    regional:'European capability depends on where research, finance and infrastructure are actually available. Persistent regional gaps can leave strong EU-level policy with uneven real-world capacity.',
    infrastructure:'Shared laboratories, facilities and computing systems are now strategic assets. Their availability, resilience and access conditions directly affect what European research can do.',
    funding:'The size and design of funding affect which capabilities are built, where they are built and who controls them. Large gaps between programmes can shift strategic direction away from the public priorities Europe intended to set.',
    defence:'The balance between procurement and innovation shapes whether Europe mainly buys today’s capabilities or also develops tomorrow’s. Large spending without a comparable innovation pipeline can lock in dependence.',
    healthdata:'European health research increasingly depends on data moving lawfully and consistently across borders. Fragmented rules or infrastructure can weaken the value of otherwise strong clinical and research networks.',
    greentech:'Green technologies are becoming part of industrial and security policy as well as climate policy. Europe’s position depends on whether investment can be matched by supply chains, scale-up finance and domestic capability.',
    competitiveness:'Research strength matters economically only when it becomes productive firms, technologies and industrial capacity. The gap between invention and deployment is therefore a strategic issue, not just a business one.'
  };
  function whyFor(...parts){const k=topic(...parts);return WHY[k]||''}

  function generalHeadline(product,headline,lead){
    const h=clean(headline), l=clean(lead), t=low(`${h} ${l}`);
    if(product==='continuity'){
      if(/open science|research openness/.test(t))return 'Europe is still trying to keep research open while protecting sensitive knowledge.';
      if(/research workforce|research talent|career|staff quality/.test(t))return 'Europe’s research capacity still depends on whether it can attract and keep the people it needs.';
      if(/public ai compute|computing power|compute access/.test(t))return 'Access to large-scale computing is becoming a basic condition for European research and innovation.';
      if(/scale[- ]?up|innovation conversion/.test(t))return 'Europe still struggles to turn strong research into firms and industrial capacity at scale.';
      if(/critical material|raw material/.test(t))return 'Critical inputs remain an upstream constraint on European technology and research.';
      if(/chip|semiconductor/.test(t))return 'Semiconductor dependence remains a recurring limit on European technology autonomy.';
    }
    if(product==='risk'||product==='opportunity'){
      if(/one member state.*rivals.*eu|single national.*rivals.*eu/.test(t))return 'National strategic spending can now rival individual EU-level innovation programmes.';
      if(/single private project.*outweighs.*eu|private project.*bigger than.*eu/.test(t))return 'A single private investment can outscale an individual EU technology or research programme.';
      if(/defence procurement.*defence innovation|defense procurement.*defense innovation/.test(t))return 'Defence procurement is expanding on a much larger scale than defence innovation funding.';
    }
    // Keep strong mechanism headlines such as dependency chains and shock hypotheses.
    return h;
  }

  function card(product,input){
    input=input||{};
    const headline=generalHeadline(product, input.headline||input.title, input.lead);
    const lead=sentence(input.lead||input.explanation||'');
    const suppliedWhy=sentence(input.so||input.why||'');
    const inferredWhy=sentence(whyFor(headline,lead,input.topic||''));
    return {
      headline,
      what:lead,
      why:suppliedWhy||inferredWhy,
      basis:sentence(input.basis||'')
    };
  }

  function trendSide(input){
    input=input||{};
    const title=clean(input.title);
    const evidence=sentence(input.plain||'');
    const why=sentence(input.why||whyFor(title,input.pairTitle||'',evidence));
    return {title,evidence,why};
  }

  function phenomenon(input){
    return card('continuity',input||{});
  }
  function priority(kind,input){return card(kind,input||{})}
  function shock(input){return card('shock',input||{})}

  g.RadarReaderClarity={clean,sentence,topic,whyFor,card,trendSide,phenomenon,priority,shock};
})(typeof globalThis!=='undefined'?globalThis:this);
