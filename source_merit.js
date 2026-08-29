(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  root.RadarSourceMerit=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';

  const EU_NAMES=[
    'European Commission','Council of the European Union','European Central Bank',
    'European Innovation Council','European Research Council','European Investment Bank',
    'EuroHPC Joint Undertaking','European Union Institute for Security Studies','EUISS',
    'EFSA Supporting Publications'
  ];
  const PUBLIC_HIGH=new Set([
    'OECD','International Telecommunication Union',
    'National Contact Point for Knowledge Security, Government of the Netherlands',
    'Rathenau Instituut'
  ]);
  const SCIENCE_NETWORK_HIGH=new Set(['ALLEA','League of European Research Universities (LERU)']);
  const LEADING_POLICY=new Set([
    'Bruegel','CEPS','MERICS','MERICS / European Think-tank Network on China','European Policy Centre',
    'Finnish Institute of International Affairs (FIIA)','European Council on Foreign Relations',
    'European Council on Foreign Relations (ECFR)','Stockholm International Peace Research Institute',
    'Stockholm International Peace Research Institute (SIPRI)','Center for Security Studies, ETH Zurich',
    'ECIPE','Jacques Delors Centre','Jacques Delors Institute','Carnegie Endowment for International Peace',
    'Carnegie Europe','German Marshall Fund of the United States (GMF)','Istituto Affari Internazionali (IAI)',
    'The Hague Centre for Strategic Studies (HCSS)','ECDPM','EUROPEUM Institute for European Policy',
    'Center for European Policy Analysis','Institut Montaigne / CHIPDIPLO','Wilfried Martens Centre for European Studies',
    'VoxEU/CEPR','European Citizen Action Service'
  ]);
  const TOP_JOURNALS=new Set([
    'Nature','Nature Communications','Policy and Society','Science and Public Policy',
    'European Journal of International Relations','JCMS Journal of Common Market Studies','Scientific Reports',
    'European Security','Business Strategy and the Environment','Sustainable Development',
    'Journal of Medical Internet Research','Royal Society Open Science','Statistics in Biopharmaceutical Research',
    'Applied Health Economics and Health Policy','Nonlinear Dynamics','Asian Economic Policy Review','Geopolitics',
    'Higher Education Policy'
  ]);
  const ESTABLISHED_JOURNALS=new Set([
    'European Journal of Futures Research','Politics and Governance','AI and Ethics','Frontiers in Political Science',
    'Frontiers in Medicine','Frontiers in Research Metrics and Analytics','The Journal of World Intellectual Property',
    'Legal Issues of Economic Integration','Empirica','European Journal of Innovation Management',
    'Journal of Science and Technology Policy Management','Education Inquiry','Asia Europe Journal',
    'Review of Evolutionary Political Economy','Energy Sustainability and Society','Sustainability','Applied Sciences',
    'Electronics','Circular Economy and Sustainability','Social Inclusion','Journal of Pharmaceutical Policy and Practice',
    'International Journal of Health Governance','European Countryside','Agricultural Economics (Zemědělská ekonomika)',
    'Journal of Data and Information Science','FUTURES & FORESIGHT SCIENCE',
    'Forestry: An International Journal of Forest Research','Journal of Innovation Management'
  ]);
  const ACADEMIC_PUBLISHERS=new Set(['Edward Elgar Publishing','Routledge']);

  function clean(v){return String(v||'').replace(/\s+/g,' ').trim()}
  function domain(link){try{return new URL(clean(link)).hostname.toLowerCase().replace(/^www\./,'')}catch(e){return ''}}
  function sourceOf(x){return clean(x?.source||x?.journal||x?.institution||'')}
  function typeOf(x){return clean(x?.itemType||x?.type||x?.signal_kind||x?.signalType||x?.signal_type||'').toLowerCase()}
  function tierOf(x){return clean(x?.sourceTier||x?.source_tier||'')}
  function euRelOf(x){return clean(x?.euRelevance||x?.eu_relevance||'').toLowerCase()}
  function authorsOf(x){return clean(x?.authors||'')}
  function linkOf(x){return clean(x?.link||x?.url||'')}

  function isEuOfficial(src,link){
    const s=clean(src).toLowerCase(),d=domain(link);
    if(EU_NAMES.some(n=>s.includes(n.toLowerCase())))return true;
    return d.endsWith('.europa.eu')||['ecb.europa.eu','consilium.europa.eu','data.consilium.europa.eu','op.europa.eu'].includes(d);
  }
  function isJournal(x){
    const src=sourceOf(x),typ=typeOf(x),tier=tierOf(x).toLowerCase();
    if(isEuOfficial(src,linkOf(x))||PUBLIC_HIGH.has(src)||SCIENCE_NETWORK_HIGH.has(src)||LEADING_POLICY.has(src))return false;
    return /peer-reviewed|journal/.test(typ)||tier.includes('journal')||TOP_JOURNALS.has(src)||ESTABLISHED_JOURNALS.has(src)||src==='Open Research Europe';
  }
  function authority(x){
    const src=sourceOf(x),link=linkOf(x),tier=tierOf(x).toLowerCase(),typ=typeOf(x);
    if(src==='Greens/EFA Group, European Parliament')return {points:44,kind:'EU parliamentary political group'};
    if(isEuOfficial(src,link))return {points:55,kind:'EU official / EU body'};
    if(PUBLIC_HIGH.has(src))return {points:48,kind:'Major public / international body'};
    if(SCIENCE_NETWORK_HIGH.has(src))return {points:46,kind:'Strong European science network'};
    if(TOP_JOURNALS.has(src))return {points:46,kind:'Leading peer-reviewed journal'};
    if(LEADING_POLICY.has(src))return {points:43,kind:'Leading policy research institute'};
    if(ESTABLISHED_JOURNALS.has(src))return {points:38,kind:'Established peer-reviewed journal'};
    if(tier.includes('tier 2 comparable')&&isJournal(x))return {points:38,kind:'Established peer-reviewed journal'};
    if(tier==='tier 2'&&!isJournal(x))return {points:37,kind:'Established policy / research source'};
    if(ACADEMIC_PUBLISHERS.has(src))return {points:38,kind:'Established academic publisher'};
    if(src==='Open Research Europe')return {points:36,kind:'EU-supported peer-reviewed platform'};
    if(/peer-reviewed/.test(typ)||tier.includes('tier 2 broad journal'))return {points:32,kind:'Peer-reviewed journal'};
    if(/preprint/.test(typ)||src==='arXiv')return {points:22,kind:'Preprint'};
    if(/abstract|conference/.test(src.toLowerCase()))return {points:24,kind:'Conference / abstract outlet'};
    if(tier.includes('tier 3 specialist'))return {points:27,kind:'Specialist source'};
    if(clean(x?.origin).toLowerCase().includes('weak signal')||clean(x?.strand).toUpperCase()==='C'||x?.headline)return {points:25,kind:'Current-event / signal source'};
    return {points:26,kind:'Other source'};
  }
  function relevance(x){
    const rel=euRelOf(x),src=sourceOf(x),link=linkOf(x);
    if(rel==='direct')return {points:25,kind:'Direct EU relevance'};
    if(rel==='material_external')return {points:20,kind:'External development with material EU implications'};
    if(rel==='derived')return {points:18,kind:'Relevant by comparison / implication'};
    if(clean(x?.origin).toLowerCase().includes('weak signal')||clean(x?.strand).toUpperCase()==='C'||x?.headline){
      return isEuOfficial(src,link)?{points:25,kind:'Direct EU signal'}:{points:18,kind:'Fast-moving EU-relevant signal'};
    }
    if(isEuOfficial(src,link))return {points:25,kind:'Direct EU relevance'};
    return {points:16,kind:'Relevant; level not explicitly coded'};
  }
  function evidence(x){
    const src=sourceOf(x),link=linkOf(x),typ=typeOf(x);
    if(isEuOfficial(src,link))return {points:15,kind:'Primary/official source'};
    if(/peer-reviewed/.test(typ))return {points:15,kind:'Peer-reviewed article'};
    if(/institutional report/.test(typ))return {points:14,kind:'Institutional report'};
    if(/manual-verified/.test(typ))return {points:14,kind:'Manually verified research/policy source'};
    if(/research\/policy paper/.test(typ))return {points:13,kind:'Research/policy paper'};
    if(/preprint/.test(typ))return {points:8,kind:'Preprint; not peer-reviewed'};
    if(/abstract|conference/.test(src.toLowerCase()))return {points:8,kind:'Conference/abstract evidence'};
    if(clean(x?.origin).toLowerCase().includes('weak signal')||clean(x?.strand).toUpperCase()==='C'||x?.headline)return {points:9,kind:'Current-event/signal evidence'};
    return {points:10,kind:'General evidence source'};
  }
  function authorPoints(x){
    const a=authorsOf(x);if(!a)return 2;
    if(/commission|council|institute|undertaking|bank|agency|organisation|organization|university|academies/i.test(a))return 4;
    return 5;
  }
  function band(score){
    if(score>=93)return {code:'A',label:'Highest',long:'Highest authority',tone:'highest'};
    if(score>=85)return {code:'B',label:'Very strong',long:'Very strong',tone:'very-strong'};
    if(score>=75)return {code:'C',label:'Strong',long:'Strong',tone:'strong'};
    if(score>=65)return {code:'D',label:'Useful',long:'Useful with context',tone:'useful'};
    return {code:'E',label:'Supporting',long:'Supporting / lower weight',tone:'supporting'};
  }
  function forItem(x){
    const a=authority(x),r=relevance(x),e=evidence(x),ap=authorPoints(x),score=Math.max(0,Math.min(100,a.points+r.points+e.points+ap)),b=band(score);
    return {score,...b,authority:a.kind,relevance:r.kind,evidence:e.kind,authorPoints:ap};
  }
  function componentsFor(x){
    const a=authority(x),r=relevance(x),e=evidence(x),ap=authorPoints(x);
    return {
      authorityPoints:a.points,authority:a.kind,
      relevancePoints:r.points,relevance:r.kind,
      evidencePoints:e.points,evidence:e.kind,
      authorTransparencyPoints:ap
    };
  }
  function scoreFor(x){return forItem(x).score}
  function compare(a,b){return scoreFor(b)-scoreFor(a)}
  function aggregate(items){
    const xs=(Array.isArray(items)?items:[]).filter(Boolean);if(!xs.length)return {...band(0),score:0,count:0,best:0};
    const scores=xs.map(scoreFor),avg=Math.round(scores.reduce((a,b)=>a+b,0)/scores.length),b=band(avg);
    return {score:avg,count:scores.length,best:Math.max(...scores),...b};
  }
  function badgeText(x,prefix='Evidence'){const m=forItem(x);return `${prefix}: ${m.label}`}
  function explanation(x){const m=forItem(x);return `${m.label} evidence weight (${m.score}/100): ${m.authority}; ${m.relevance.toLowerCase()}; ${m.evidence.toLowerCase()}.`}
  return {forItem,componentsFor,scoreFor,compare,aggregate,band,badgeText,explanation,isEuOfficial};
});
