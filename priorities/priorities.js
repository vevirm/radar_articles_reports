(function(root,factory){
  if(typeof module==='object'&&module.exports) module.exports=factory(require('../briefing/insights.js'));
  else root.RadarPriorities=factory(root.RadarInsights);
})(typeof globalThis!=='undefined'?globalThis:this,function(Insights){
  'use strict';

  function clean(v){return String(v||'').replace(/\s+/g,' ').trim()}
  function norm(v){return clean(v).toLowerCase().replace(/[–—]/g,'-').replace(/[^a-z0-9+.#/&'-]+/g,' ').replace(/\s+/g,' ').trim()}
  function dateValue(v){const t=Date.parse(clean(v));return Number.isFinite(t)?t:0}
  function titleFor(x){return clean(x?.headline||x?.title||x?.what||x?.core_message||'')}
  function sourceFor(x){return clean(x?.source||x?.authors||'')}
  function linkFor(x){return clean(x?.link||'')}
  function coreFor(x){return clean(x?.what||x?.core_message||x?.reader_point||x?.summary||titleFor(x))}

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
    return (x?.newThisScan?1e15:0)+dateValue(x?.date)*100+components;
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

  function rawStrategicItems(data){
    const rows=[
      ...(Array.isArray(data?.strand_a)?data.strand_a:[]),
      ...(Array.isArray(data?.frontier_evidence)?data.frontier_evidence:[]),
      ...(Array.isArray(data?.strand_c)?data.strand_c:[]),
    ].filter(x=>x&&typeof x==='object');
    const byKey=new Map(),unkeyed=[];
    for(const x of rows){
      const c=x.strategic_classification;
      if(!c||typeof c!=='object'||clean(x.strategic_classification_source)!=='source_text') continue;
      const lenses=Array.isArray(c.lenses)?c.lenses.filter(v=>['risk','opportunity','external_shock'].includes(clean(v?.type))):[];
      if(!lenses.length&&!['risk','opportunity','external_shock'].includes(clean(c.primary))) continue;
      const key=norm(linkFor(x)||titleFor(x));
      if(!key){unkeyed.push(x);continue}
      const prior=byKey.get(key);
      const weight=y=>Array.isArray(y?.strategic_classification?.lenses)?y.strategic_classification.lenses.length:0;
      if(!prior||weight(x)>weight(prior)) byKey.set(key,x);
    }
    return [...byKey.values(),...unkeyed];
  }

  function lensRows(data){
    const out=[];
    for(const raw of rawStrategicItems(data)){
      const c=raw.strategic_classification||{};
      let lenses=Array.isArray(c.lenses)?c.lenses.filter(x=>x&&typeof x==='object'):[];
      if(!lenses.length&&clean(c.primary)) lenses=[{type:clean(c.primary),passage:''}];
      for(const lens of lenses){
        const kind=clean(lens.type);
        if(!['risk','opportunity','external_shock'].includes(kind)) continue;
        out.push({
          raw,kind,lens,lensPassage:clean(lens.passage),strategicClassification:c,
          title:titleFor(raw),coreMessage:coreFor(raw),source:sourceFor(raw),date:clean(raw.date||raw.first_seen||''),
          link:linkFor(raw),abstract:clean(raw.summary||raw.signal_note||raw.why_it_matters||''),newThisScan:!!raw.new_this_scan,
        });
      }
    }
    return out;
  }

  function sortPathways(items){
    return items.sort((a,b)=>pathwayScore(b)-pathwayScore(a)||String(b.date).localeCompare(String(a.date))||a.title.localeCompare(b.title));
  }

  function buildPriorityView(data,opts={}){
    const limit=Number.isFinite(opts.limit)?Math.max(1,Math.min(12,Math.floor(opts.limit))):10;
    const rows=lensRows(data);
    const closedRisks=rows.filter(x=>x.kind==='risk'&&clean(x.lens?.status)==='closed_into_shock');
    const allRisks=sortPathways(rows.filter(x=>x.kind==='risk'&&clean(x.lens?.status)!=='closed_into_shock'));
    const allOpportunities=sortPathways(rows.filter(x=>x.kind==='opportunity'));
    const externalShocks=sortPathways(rows.filter(x=>x.kind==='external_shock'));
    return {
      risks:diversifiedTop(allRisks,limit,2),
      opportunities:diversifiedTop(allOpportunities,limit,2),
      externalShocks,
      stats:{
        sourceBacked:rawStrategicItems(data).length,
        risks:allRisks.length,
        opportunities:allOpportunities.length,
        externalShocks:externalShocks.length,
        closedRisks:closedRisks.length,
        shownRisks:Math.min(limit,allRisks.length),
        shownOpportunities:Math.min(limit,allOpportunities.length),
      }
    };
  }

  function simplePriorityText(x){
    const raw=clean(x?.coreMessage||x?.title||'');
    return Insights?.readerPoint?.(raw)||Insights?.completeCoreMessage?.(raw)||raw||'The source does not provide a concise claim.';
  }

  function simpleEvidenceText(x){return clean(x?.title||'')}

  return {buildPriorityView,pathwayScore,diversifiedTop,simplePriorityText,simpleEvidenceText,topicKey,lensRows};
});
