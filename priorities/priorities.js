(function(root,factory){
  if(typeof module==='object'&&module.exports) module.exports=factory(require('../frontier/frontier.js'),require('../briefing/insights.js'),require('../source_merit.js'));
  else root.RadarPriorities=factory(root.SovereigntyFrontier,root.RadarInsights,root.RadarSourceMerit);
})(typeof globalThis!=='undefined'?globalThis:this,function(Frontier,Insights,Merit){
  'use strict';

  function structuralScore(x){
    if(!x) return 0;
    const merit=x.sourceMerit?.score||(Merit?.scoreFor?Merit.scoreFor(x):0);
    const finding=Number(x.overall||0);
    // Matrix qualification/severity comes first. Within qualified findings, source
    // merit is deliberately a major part of ordering, using the same 0-100 rubric
    // documented in Stuff rather than a separate reader-page quality score.
    return finding*4 + merit + (x.confidence||0)/20 + Math.min(8,x.materiality||0);
  }

  function topicKey(x){
    const t=clean(`${x?.bibliographicTitle||''} ${x?.coreMessage||''} ${x?.abstract||''}`).toLowerCase();
    const groups=[
      ['research security',/research security|knowledge security|foreign interference|espionage/],
      ['talent',/research talent|researcher|scientist|brain drain|mobility|doctoral|postdoctoral/],
      ['chips',/semiconductor|chip|microelectronics/],
      ['compute-ai',/compute|cloud|frontier ai|ai factory|foundation model|military ai/],
      ['materials',/critical raw|critical mineral|rare earth|battery|materials/],
      ['scale-finance',/venture capital|scale-up|scaleup|startup|investment|capital|listing|headquarter/],
      ['defence-dual-use',/dual-use|dual use|defen[cs]e|military/],
      ['rules-security',/regulat|standard|rule|export control|screening|sovereignty|autonomy/],
      ['partnerships',/china|united states| us |india|international|partnership|science diplomacy/],
      ['industry',/industrial|manufactur|procurement|productivity|automotive|electric vehicle/],
    ];
    for(const [k,re] of groups) if(re.test(` ${t} `)) return k;
    return x?.row?.id||'other';
  }

  function diversifiedTop(items,limit,maxPerRow=2,maxPerTopic=2){
    if(limit<=0) return [];
    const out=[],deferred=[],perRow=new Map(),perTopic=new Map();
    for(const x of items){
      const row=x?.row?.id||'other',topic=topicKey(x),rn=perRow.get(row)||0,tn=perTopic.get(topic)||0;
      if(rn<maxPerRow&&tn<maxPerTopic&&out.length<limit){out.push(x);perRow.set(row,rn+1);perTopic.set(topic,tn+1)}
      else deferred.push(x);
    }
    for(const x of deferred){
      if(out.length>=limit)break;
      const topic=topicKey(x),tn=perTopic.get(topic)||0;
      if(tn>=maxPerTopic)continue;
      out.push(x);perTopic.set(topic,tn+1);
    }
    return out;
  }


  function clean(v){return String(v||'').replace(/\s+/g,' ').trim()}
  function maxChars(v,n=120){
    const s=clean(v);
    if(s.length<=n) return s;
    const sentences=s.match(/[^.!?]+[.!?]+/g)||[];
    for(const sentence of sentences){const q=clean(sentence);if(q.length<=n)return q}
    return '';
  }
  function simplePriorityText(x){
    return Insights?.readerPoint?.(x?.coreMessage||'')||Insights?.pointFor?.(x)||'The source does not provide a concise claim.';
  }
  function priorityInterpretation(x){
    const row=x?.row?.id||'other',col=x?.column?.id||'B';
    const topic={knowledge:'people and knowledge',infrastructure:'tools and infrastructure',conversion:'firms and scale',rules:'rules and coordination',other:'research and innovation'}[row]||'research and innovation';
    if(col==='A') return `Europe gains control and becomes stronger in ${topic}.`;
    if(col==='B') return `Europe gains more control in ${topic}, but pays in speed, scale or performance.`;
    if(col==='C') return `Europe becomes stronger in ${topic}, but still relies on outside access.`;
    return `Europe loses control and becomes weaker in ${topic}.`;
  }
  function simpleEvidenceText(x){
    let t=clean(x?.title||'').replace(/\s+[–—-]\s+(?:Company Announcement\s+-\s+)?(?:FT\.com|Reuters|Bloomberg).*$/i,'');
    t=t.replace(/\s+–\s+Company Announcement.*$/i,'');
    return maxChars(t,118);
  }

  function buildPriorityView(data,opts={}){
    const frontier=Frontier.buildFrontier(data,opts);
    const limit=Number.isFinite(opts.limit)?Math.max(1,Math.min(12,Math.floor(opts.limit))):10;
    const types=x=>{
      const c=x?.strategicClassification;
      if(!c||typeof c!=='object') return null; // legacy evidence: Matrix fallback below
      const out=new Set((c.lenses||[]).map(v=>clean(v?.type)).filter(Boolean));
      if(clean(c.primary)) out.add(clean(c.primary));
      return out;
    };
    const allOpportunities=frontier.signals
      .filter(x=>{const t=types(x);return t?t.has('opportunity'):x.column.id==='A'})
      .sort((a,b)=>structuralScore(b)-structuralScore(a)||String(b.date).localeCompare(String(a.date))||a.title.localeCompare(b.title));
    const severity={D:3,C:2,B:1};
    const allRisks=frontier.signals
      .filter(x=>{const t=types(x);return t?t.has('risk'):x.column.id!=='A'})
      .sort((a,b)=>(severity[b.column.id]||0)-(severity[a.column.id]||0)||structuralScore(b)-structuralScore(a)||String(b.date).localeCompare(String(a.date))||a.title.localeCompare(b.title));
    const externalShocks=frontier.signals
      .filter(x=>types(x)?.has('external_shock'))
      .sort((a,b)=>String(b.date).localeCompare(String(a.date))||structuralScore(b)-structuralScore(a));
    const opportunities=diversifiedTop(allOpportunities,limit,2);
    const risks=diversifiedTop(allRisks,limit,2);
    return {
      frontier,
      opportunities,
      risks,
      externalShocks,
      stats:{
        cumulativeQualifying:frontier.signals.length,
        opportunities:allOpportunities.length,
        risks:allRisks.length,
        externalShocks:externalShocks.length,
        shownOpportunities:opportunities.length,
        shownRisks:risks.length,
        doubleLoss:allRisks.filter(x=>x.column.id==='D').length,
        dependencies:allRisks.filter(x=>x.column.id==='C').length,
        tradeoffs:allRisks.filter(x=>x.column.id==='B').length,
      }
    };
  }

  return {buildPriorityView,structuralScore,diversifiedTop,simplePriorityText,simpleEvidenceText,priorityInterpretation,topicKey};
});
