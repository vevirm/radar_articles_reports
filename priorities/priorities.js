(function(root,factory){
  if(typeof module==='object'&&module.exports) module.exports=factory(require('../frontier/frontier.js'));
  else root.RadarPriorities=factory(root.SovereigntyFrontier);
})(typeof globalThis!=='undefined'?globalThis:this,function(Frontier){
  'use strict';

  function structuralScore(x){
    if(!x) return 0;
    return (x.triage?.total||0)*10 + (x.questionCount||0)*4 + (x.confidence||0)/10 + Math.min(8,x.materiality||0);
  }

  function diversifiedTop(items,limit,maxPerRow=2){
    if(limit<=0) return [];
    const out=[],deferred=[],perRow=new Map();
    for(const x of items){
      const row=x?.row?.id||'other',n=perRow.get(row)||0;
      if(n<maxPerRow&&out.length<limit){out.push(x);perRow.set(row,n+1)}
      else deferred.push(x);
    }
    for(const x of deferred){if(out.length>=limit)break;out.push(x)}
    return out;
  }

  function buildPriorityView(data,opts={}){
    const frontier=Frontier.buildFrontier(data,opts);
    const limit=Number.isFinite(opts.limit)?Math.max(1,Math.floor(opts.limit)):6;
    const allOpportunities=frontier.signals
      .filter(x=>x.column.id==='A')
      .sort((a,b)=>structuralScore(b)-structuralScore(a)||String(b.date).localeCompare(String(a.date))||a.title.localeCompare(b.title));
    const severity={D:3,C:2,B:1};
    const allRisks=frontier.signals
      .filter(x=>x.column.id!=='A')
      .sort((a,b)=>(severity[b.column.id]||0)-(severity[a.column.id]||0)||structuralScore(b)-structuralScore(a)||String(b.date).localeCompare(String(a.date))||a.title.localeCompare(b.title));
    const opportunities=diversifiedTop(allOpportunities,limit,2);
    const risks=diversifiedTop(allRisks,limit,2);
    return {
      frontier,
      opportunities,
      risks,
      stats:{
        cumulativeQualifying:frontier.signals.length,
        opportunities:allOpportunities.length,
        risks:allRisks.length,
        shownOpportunities:opportunities.length,
        shownRisks:risks.length,
        doubleLoss:allRisks.filter(x=>x.column.id==='D').length,
        dependencies:allRisks.filter(x=>x.column.id==='C').length,
        tradeoffs:allRisks.filter(x=>x.column.id==='B').length,
      }
    };
  }

  return {buildPriorityView,structuralScore,diversifiedTop};
});
