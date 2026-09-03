/* v17.20.13 — reader-facing 0–100 ranking.
   Purpose: order admitted Radar evidence by source quality + actual strand relevance.
   This is separate from the Stuff audit/export source-merit score. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.RadarReaderRank=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const clean=v=>String(v||'').replace(/\s+/g,' ').trim();
  const low=v=>clean(v).toLowerCase();
  const list=v=>Array.isArray(v)?v.filter(Boolean):[];
  const source=x=>clean(x?.source||x?.journal||x?.institution||'');
  const tier=x=>low(x?.source_tier||x?.sourceTier||'');
  const type=x=>low(x?.type||x?.itemType||x?.signal_kind||x?.signal_type||'');
  const strand=x=>clean(x?.strand||'').toUpperCase()||(x?.headline?'C':'A');
  const text=x=>low([x?.title,x?.headline,x?.core_message,x?.summary,x?.what,x?.why_it_matters,x?.relevance_note,x?.bridge_sentence,list(x?.geo_evidence).join(' '),list(x?.a_context_evidence).join(' ')].join(' '));
  const TOP_NEWS=/\b(?:Financial Times|Reuters|Nature|Science|POLITICO|Politico Europe|Research Professional News|Science\|Business|The Economist)\b/i;
  const HIGH_POLICY=/\b(?:Bruegel|CEPS|ECFR|European Council on Foreign Relations|EUISS|European Union Institute for Security Studies|MERICS|SIPRI|Carnegie|Jacques Delors|DIIS|Danish Institute for International Studies|FIIA|Finnish Institute of International Affairs|Chatham House|RAND|OECD|JRC|Joint Research Centre)\b/i;
  const EU_OFFICIAL=/\b(?:European Commission|European Research Council|European Innovation Council|European Research Executive Agency|European Parliament|Council of the European Union|EuroHPC|Fusion for Energy|European Investment Bank|European Defence Agency|European Court of Auditors|ERA Portal|CORDIS)\b/i;
  const STRATEGIC=/\b(?:geopolit|geoeconom|economic security|research security|knowledge security|technology security|strategic autonomy|technological sovereignty|technology sovereignty|digital sovereignty|data sovereignty|strategic depend|critical depend|critical technolog|dual[- ]use|export control|investment screening|sanction|economic coercion|weaponised interdependence|de-risk|decoupl|science diplomacy|foreign interference|foreign influence|defen[cs]e innovation|civil-military|technology competition|supply[- ]chain resilience|critical raw material|semiconductor|chip sovereignty|third-country|extraterritorial|strategic competition)\b/i;
  const METHOD=/\b(?:foresight|horizon scan|weak signal|scenario|backcast|cross[- ]impact|roadmap|technology intelligence|forecast|anticipatory governance|futures literacy|robust decision|stress test|red team|Delphi|morphological analysis|causal layered|trend analysis)\b/i;

  function authority(x){
    const s=source(x),t=tier(x),ty=type(x);
    if(EU_OFFICIAL.test(s))return 45;
    if(/tier 1/.test(t))return HIGH_POLICY.test(s)?44:42;
    if(/tier 2 priority journal/.test(t))return 40;
    if(/tier 2 trusted-publisher journal/.test(t))return 37;
    if(/tier 2/.test(t))return 35;
    if(TOP_NEWS.test(s))return 38;
    if(HIGH_POLICY.test(s))return 39;
    if(/peer-reviewed|journal/.test(ty))return 34;
    if(/institutional|official|formal study|report|research\/policy/.test(ty))return 34;
    if(/preprint/.test(ty))return 25;
    return x?.headline?28:27;
  }
  function evidence(x){
    const ty=type(x);
    if(/peer-reviewed/.test(ty))return 15;
    if(/institutional report|formal study|official policy|institutional framework/.test(ty))return 15;
    if(/research\/policy paper|policy paper|working paper/.test(ty))return 13;
    if(/preprint/.test(ty))return 9;
    if(strand(x)==='C'||x?.headline)return TOP_NEWS.test(source(x))?12:10;
    return 10;
  }
  function euRiFit(x){
    const eu=list(x?.eu_evidence).length>0||low(x?.eu_relevance)==='direct'||/\b(?:eu|europe|european union|horizon europe|erc|eic|jrc|fp10|era)\b/.test(text(x));
    const ri=list(x?.ri_evidence).length>0||/\b(?:research|innovation|science|technology|r&d|university|researcher|laborator|research infrastructure|doctoral|patent|scientific)\b/.test(text(x));
    return (eu?10:0)+(ri?10:0);
  }
  function strategicFit(x){
    const route=low(x?.a_route),geo=list(x?.geo_evidence),ctx=list(x?.a_context_evidence),t=text(x);
    if(geo.length||route==='explicit-geopolitics')return 20;
    if(ctx.length||route==='triangulated-strategic-context')return 18;
    if(STRATEGIC.test(t))return 16;
    if(route==='ri-relevance-assessment')return 4;
    return 7;
  }
  function methodFit(x){
    const t=text(x);let n=0;
    if(METHOD.test(t))n+=25;
    if(/\b(?:develop|propose|introduce|adapt|extend|refine|method|framework|approach|tool|model)\b/.test(t))n+=10;
    return Math.min(35,n||8);
  }
  function signalFit(x){
    const t=text(x);let n=euRiFit(x)+strategicFit(x);
    if(/\b(?:announc|restrict|suspend|launch|agreement|policy|ban|control|investment|funding|partnership|warning|shift|change|pressure)\b/.test(t))n+=5;
    return Math.min(40,n);
  }
  function scoreFor(x){
    const s=strand(x);let score;
    if(s==='B')score=authority(x)+evidence(x)+methodFit(x);
    else if(s==='C')score=authority(x)+evidence(x)+signalFit(x);
    else score=authority(x)+evidence(x)+euRiFit(x)+strategicFit(x);
    return Math.max(0,Math.min(100,Math.round(score)));
  }
  function compare(a,b){return scoreFor(b)-scoreFor(a)}
  function band(score){if(score>=95)return 'top';if(score>=88)return 'very-strong';if(score>=78)return 'strong';if(score>=68)return 'useful';return 'supporting'}
  return {scoreFor,compare,band,authority,evidence,euRiFit,strategicFit,methodFit,signalFit};
});
