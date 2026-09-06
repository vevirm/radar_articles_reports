(function(g){
'use strict';
const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
function words(v){return clean(v).split(/\s+/).filter(Boolean)}
function limit(v,n){const a=words(v);if(a.length<=n)return a.join(' ');return a.slice(0,n).join(' ').replace(/[,:;–—-]+$/,'')+'…'}
function whatFor(x){
  return clean(g.RadarInsights?.whatForEuRiGeo?.(x)||g.RadarInsights?.signalWhat?.(x)||g.RadarInsights?.pointFor?.(x)||x?.what||x?.core_message||x?.headline||x?.title||'');
}
function whyFor(x){
  return clean(g.RadarInsights?.whyFor?.(x)||g.RadarInsights?.whyYouShouldCare?.(x)||x?.why_it_matters||x?.relevance_note||x?.signal_note||'');
}
function radarPair(x,opt={}){
  const w=limit(opt.what||whatFor(x),20);
  const y=limit(opt.why||whyFor(x)||'It changes a documented capability, dependency, rule or partnership in European research and innovation.',20);
  return {what:w,why:y};
}
function matrixPair(x,opt={}){
  const w=limit(opt.what||g.SovereigntyFrontier?.shortBullet?.(x)||whatFor(x),12);
  const y=limit(opt.why||x?.why||whyFor(x)||'It changes European control or capability in this part of the R&I system.',15);
  return {what:w,why:y,line:`${w} — ${y}`};
}
function pagePair(what,why,whatWords=20,whyWords=20){return {what:limit(what,whatWords),why:limit(why,whyWords)}}
function wordCount(v){return words(v).length}
g.RadarReaderStyle={clean,limit,wordCount,whatFor,whyFor,radarPair,matrixPair,pagePair};
})(globalThis);
