(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.RadarPhenomena=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const PHENOMENA=[
    {
      id:'research-security-openness',
      title:'Open science keeps meeting the security desk',
      what:'Research security keeps reshaping how Europe balances protection, openness and international collaboration.',
      why:'The same tension appears in older work and keeps returning in current policy and research.',
      current:/research security|knowledge security|foreign interference|trusted research|dual[- ]use|academic freedom|open science/i,
      historical:['research-security','academic-freedom','open-science-platforms']
    },
    {
      id:'talent-careers',
      title:'Talent keeps packing a suitcase',
      what:'Research careers, mobility and retention keep returning as questions of European scientific capacity.',
      why:'Europe can fund ambitious research and still lose capability when people cannot build durable careers.',
      current:/researcher mobility|research talent|scientific talent|brain drain|research workforce|doctoral|\bphd\b|postdoc|research career|talent retention|talent attraction/i,
      historical:['talent','research-careers','doctoral-workforce']
    },
    {
      id:'research-infrastructure',
      title:'Europe keeps building the machine',
      what:'Shared laboratories, computing facilities and other research infrastructure keep returning as strategic investments.',
      why:'Capability depends on having places, machines and networks that researchers can actually use.',
      current:/research infrastructure|supercomputer|eurohpc|ai factor|gigafactor|pilot line|testbed|data cent(?:re|er)|quantum facilit|research facilit/i,
      historical:['research-infrastructure']
    },
    {
      id:'ai-compute',
      title:'Compute keeps moving the goalposts',
      what:'Artificial intelligence and computing capacity keep resurfacing as questions of access, investment and dependence.',
      why:'Every jump in computing needs changes what European researchers can build and who controls the bottleneck.',
      current:/artificial intelligence|\bai\b|compute|supercomputer|\bgpu\b|foundation model|large language model/i,
      historical:['ai-compute']
    },
    {
      id:'chips',
      title:'The chip problem refuses to leave',
      what:'Semiconductor capability keeps returning as a constraint on European technology autonomy and research capacity.',
      why:'Many strategic technologies still depend on chips, equipment and production capacity concentrated outside Europe.',
      current:/semiconductor|chips? act|microelectronics|lithograph|foundry|\bfab\b|wafer/i,
      historical:['chips']
    },
    {
      id:'international-cooperation',
      title:'Science diplomacy keeps renewing its passport',
      what:'International research cooperation keeps being rebuilt around changing partners, risks and strategic interests.',
      why:'Europe still needs global science while deciding where openness creates dependence or security concerns.',
      current:/science diplomacy|scientific cooperation|research cooperation|international research|horizon europe.{0,80}associat|association to horizon|research collaboration|scientific collaboration/i,
      historical:['global-rivalry']
    },
    {
      id:'scale-up',
      title:'The scale-up gap is still here',
      what:'Europe keeps returning to the problem of turning research strength into firms, investment and market scale.',
      why:'Scientific strength produces less strategic capacity when successful ideas grow elsewhere or remain too small.',
      current:/scale[- ]?up|commerciali[sz]|technology transfer|innovation gap|competitiveness gap|venture capital|startup|start-up/i,
      historical:['scale-up','technology-transfer']
    },
    {
      id:'rules-standards',
      title:'Europe keeps writing the rulebook',
      what:'Rules, standards and safeguards keep returning as tools for shaping strategic technologies and research.',
      why:'Rule-setting can create trust and influence markets, but it can also expose slow delivery.',
      current:/standardisation|standardization|standards?|regulation|governance|rulebook|technical committee|dual-use regulation|investment screening|export control/i,
      historical:['rules-standards']
    },
    {
      id:'materials-energy',
      title:'The important bits keep hiding upstream',
      what:'Critical materials and energy inputs keep resurfacing behind Europe’s technology and research ambitions.',
      why:'Advanced systems still depend on physical inputs that can become strategic bottlenecks before laboratories notice.',
      current:/critical raw material|rare earth|lithium|cobalt|gallium|germanium|battery|hydrogen|energy technolog|critical mineral/i,
      historical:['materials-energy']
    },
    {
      id:'funding-governance',
      title:'Research money keeps becoming strategy',
      what:'Funding programmes keep being used to steer European research toward capability, security and competitiveness goals.',
      why:'Budget choices determine which fields, partnerships and infrastructures gain momentum across the research system.',
      current:/framework programme|fp10|horizon europe|research funding|innovation funding|european innovation council|european research council|state aid|funding governance|research budget/i,
      historical:['funding-governance']
    }
  ];

  function clean(v){return String(v??'').replace(/\s+/g,' ').trim()}
  function dateOf(x){return clean(x?.date).slice(0,10)}
  function textOf(x){return clean([x?.title,x?.headline,x?.summary,x?.core_message,x?.relevance_note,x?.signal_note,x?.anchor,x?.why_it_matters,x?.watch_theme].filter(Boolean).join(' '))}
  function sourceOf(x){return clean(x?.source||x?.source_domain||x?.venue||x?.publisher||'Unknown source')}
  function sourceCount(rows){return new Set(rows.map(sourceOf).filter(Boolean)).size}
  function cutoff(history){return clean(history?.cutoff_exclusive||history?.date_to||'')}
  function currentCorpus(data,history){
    const boundary=cutoff(history);
    const rows=[...(Array.isArray(data?.strand_a)?data.strand_a:[]),...(Array.isArray(data?.strand_c)?data.strand_c:[])];
    return rows.filter(x=>!boundary||dateOf(x)>=boundary);
  }
  function historicalCorpus(history){return Array.isArray(history?.items)?history.items:[]}
  function unique(rows){
    const seen=new Set(),out=[];
    for(const row of rows){
      const key=clean(row?.link||row?.url||row?.title||row?.headline).toLowerCase();
      if(!key||seen.has(key))continue;seen.add(key);out.push(row);
    }
    return out;
  }
  function matchCurrent(row,p){return p.current.test(textOf(row))}
  function matchHistorical(row,p){
    const topics=Array.isArray(row?.topics)?row.topics:[];
    return p.historical.some(t=>topics.includes(t));
  }
  function evidenceSlice(rows,n,oldestToo=false){
    const sorted=unique(rows).sort((a,b)=>dateOf(b).localeCompare(dateOf(a))||sourceOf(a).localeCompare(sourceOf(b)));
    if(!oldestToo||sorted.length<=n)return sorted.slice(0,n);
    const out=sorted.slice(0,Math.max(1,n-1));
    const oldest=sorted[sorted.length-1];
    if(oldest&&!out.includes(oldest))out.push(oldest);
    return out.slice(0,n);
  }
  function build(data,history){
    const currentRows=currentCorpus(data,history),historicalRows=historicalCorpus(history),out=[];
    for(const p of PHENOMENA){
      const current=unique(currentRows.filter(x=>matchCurrent(x,p)));
      const historical=unique(historicalRows.filter(x=>matchHistorical(x,p)));
      const currentSources=sourceCount(current),historicalSources=sourceCount(historical);
      if(current.length<3||currentSources<2||historical.length<2||historicalSources<2)continue;
      const dates=historical.map(dateOf).filter(Boolean).sort();
      const newest=current.map(dateOf).filter(Boolean).sort().slice(-1)[0]||'';
      const score=Math.min(40,current.length)*2+Math.min(20,currentSources)*3+Math.min(30,historical.length)+Math.min(15,historicalSources)*2;
      out.push({...p,currentCount:current.length,currentSources,historicalCount:historical.length,historicalSources,firstSeen:dates[0]||'',latestSeen:newest,currentEvidence:evidenceSlice(current,4),historicalEvidence:evidenceSlice(historical,3,true),score});
    }
    return out.sort((a,b)=>b.score-a.score||b.currentCount-a.currentCount||a.title.localeCompare(b.title));
  }
  function stats(data,history){
    return {current:currentCorpus(data,history).length,historical:historicalCorpus(history).length,cutoff:cutoff(history)};
  }
  return {build,stats,phenomena:PHENOMENA,currentCorpus,historicalCorpus};
});
