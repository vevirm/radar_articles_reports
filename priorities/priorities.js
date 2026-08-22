(function(root,factory){
  if(typeof module==='object'&&module.exports) module.exports=factory(require('../frontier/frontier.js'));
  else root.RadarPriorities=factory(root.SovereigntyFrontier);
})(typeof globalThis!=='undefined'?globalThis:this,function(Frontier){
  'use strict';

  function structuralScore(x){
    if(!x) return 0;
    return (x.triage?.total||0)*10 + (x.questionCount||0)*4 + (x.confidence||0)/10 + Math.min(8,x.materiality||0);
  }

  function buildPriorityView(data,opts={}){
    const frontier=Frontier.buildFrontier(data,opts);
    const opportunities=frontier.signals
      .filter(x=>x.column.id==='A')
      .sort((a,b)=>structuralScore(b)-structuralScore(a)||String(b.date).localeCompare(String(a.date))||a.title.localeCompare(b.title));
    const severity={D:3,C:2,B:1};
    const risks=frontier.signals
      .filter(x=>x.column.id!=='A')
      .sort((a,b)=>(severity[b.column.id]||0)-(severity[a.column.id]||0)||structuralScore(b)-structuralScore(a)||String(b.date).localeCompare(String(a.date))||a.title.localeCompare(b.title));
    return {
      frontier,
      opportunities,
      risks,
      stats:{
        cumulativeQualifying:frontier.signals.length,
        opportunities:opportunities.length,
        risks:risks.length,
        doubleLoss:risks.filter(x=>x.column.id==='D').length,
        dependencies:risks.filter(x=>x.column.id==='C').length,
        tradeoffs:risks.filter(x=>x.column.id==='B').length,
      }
    };
  }

  return {buildPriorityView,structuralScore};
});
