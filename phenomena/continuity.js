(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.RadarContinuity=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';

  const EXCLUDE_TOPICS=new Set(['foresight-methods','computational-emergence','main-a-evidence']);
  const GENERIC_TERMS=new Set([
    'research','innovation','technology','technologies','europe','european','eu','policy','future','futures',
    'governance','resilience','digital','data','strategic','energy','investment','infrastructure','facilities',
    'researchers','scientists'
  ]);
  const RENAME_EXCLUDE=new Set([
    'horizon europe','erc','eic','chips act','ai act','eosc','united states','researchers','scientists',
    'talent','artificial intelligence','research infrastructure'
  ]);

  function clean(v){return String(v??'').replace(/\s+/g,' ').trim()}
  function norm(v){return clean(v).toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim()}
  function pretty(v){return norm(v).replace(/\bai\b/g,'AI').replace(/\beu\b/g,'EU').replace(/\bus\b/g,'US').replace(/\br i\b/g,'R&I')}
  function dateOf(x){return clean(x?.date).slice(0,10)}
  function sourceOf(x){return clean(x?.source||x?.source_domain||x?.venue||x?.publisher||'Unknown source')}
  function sourceCount(rows){return new Set(rows.map(sourceOf).filter(Boolean)).size}
  function fullText(row){
    const scalar=['title','headline','summary','core_message','relevance_note','signal_note','anchor','why_it_matters','watch_theme','reader_point'];
    const list=['ri_evidence','geo_evidence','eu_evidence','a_context_evidence'];
    const out=[];
    for(const k of scalar)if(row?.[k])out.push(row[k]);
    for(const k of list)if(Array.isArray(row?.[k]))out.push(...row[k]);
    return norm(out.join(' '));
  }
  function analysisText(row){
    // Prefer validated phrase extractions and titles so broad summaries do not manufacture patterns.
    const out=[row?.title,row?.headline,row?.reader_point];
    for(const k of ['ri_evidence','geo_evidence'])if(Array.isArray(row?.[k]))out.push(...row[k]);
    // Strand C has different fields, so keep its concise evidence-bearing text.
    if(!Array.isArray(row?.ri_evidence)&&!Array.isArray(row?.geo_evidence))out.push(row?.anchor,row?.why_it_matters,row?.watch_theme);
    return norm(out.filter(Boolean).join(' '));
  }
  function titleText(row){return norm(row?.title||row?.headline||row?.reader_point||'')}
  function hasTerm(text,term){const t=norm(term);return !!t&&(` ${text} `).includes(` ${t} `)}
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
      const key=clean(row?.link||row?.url||row?.id||row?.title||row?.headline).toLowerCase();
      if(!key||seen.has(key))continue;
      seen.add(key);out.push(row);
    }
    return out;
  }
  function evidenceSlice(rows,n){
    return unique(rows).sort((a,b)=>dateOf(b).localeCompare(dateOf(a))||sourceOf(a).localeCompare(sourceOf(b))).slice(0,n);
  }
  function log2(v){return Math.log(v)/Math.log(2)}
  function clamp(v,a,b){return Math.max(a,Math.min(b,v))}

  function topicDefinitions(config){
    const out=[];
    for(const raw of Array.isArray(config?.topics)?config.topics:[]){
      const id=clean(raw?.id),label=clean(raw?.label);
      if(!id||!label||EXCLUDE_TOPICS.has(id))continue;
      const terms=[];
      for(const x of Array.isArray(raw?.url_terms)?raw.url_terms:[]){
        const t=norm(x);
        if(!t||GENERIC_TERMS.has(t)||t.length<3)continue;
        terms.push(t);
      }
      const dedup=[...new Set(terms)];
      if(dedup.length)out.push({id,label,terms:dedup});
    }
    return out;
  }

  function topicMatch(row,topic){
    const txt=analysisText(row);
    return topic.terms.some(t=>hasTerm(txt,t));
  }

  function buildAssignments(currentRows,historicalRows,topics){
    const topicById=new Map(topics.map(t=>[t.id,t]));
    const currentSets=currentRows.map(row=>{
      const set=new Set();
      for(const topic of topics)if(topicMatch(row,topic))set.add(topic.id);
      return set;
    });
    const historicalSets=historicalRows.map(row=>new Set((Array.isArray(row?.topics)?row.topics:[]).filter(id=>topicById.has(id))));
    return {topicById,currentSets,historicalSets};
  }

  function namedPairBlocks(namedPhenomena){
    const blocked=new Set();
    for(const p of Array.isArray(namedPhenomena)?namedPhenomena:[]){
      const ids=[...new Set(Array.isArray(p?.historical)?p.historical:[])].sort();
      for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++)blocked.add(`${ids[i]}|${ids[j]}`);
    }
    return blocked;
  }

  function pairSummary(topicSets,rows){
    const singles=new Map(),pairs=new Map();
    for(let i=0;i<topicSets.length;i++){
      const ids=[...topicSets[i]].sort();
      for(const id of ids)singles.set(id,(singles.get(id)||0)+1);
      for(let a=0;a<ids.length;a++)for(let b=a+1;b<ids.length;b++){
        const key=`${ids[a]}|${ids[b]}`;
        let p=pairs.get(key);
        if(!p){p={key,a:ids[a],b:ids[b],rows:[],sources:new Set()};pairs.set(key,p)}
        p.rows.push(rows[i]);p.sources.add(sourceOf(rows[i]));
      }
    }
    const N=Math.max(1,rows.length);
    for(const p of pairs.values()){
      p.count=p.rows.length;p.sourceCount=p.sources.size;
      const ac=singles.get(p.a)||0,bc=singles.get(p.b)||0;
      p.aCount=ac;p.bCount=bc;
      p.lift=ac&&bc?(p.count*N)/(ac*bc):0;
      p.jaccard=(ac+bc-p.count)?p.count/(ac+bc-p.count):0;
    }
    return {singles,pairs,N};
  }

  function sharedTerm(a,b){return a.terms.some(t=>b.terms.includes(t))}
  const SHORT_LABELS={
    'talent':'research talent','research-security':'research security','ai-compute':'AI/compute','chips':'semiconductors',
    'materials-energy':'critical materials','research-infrastructure':'research infrastructure','technology-transfer':'technology transfer/export controls',
    'scale-up':'scale-up/industrial capability','funding-governance':'R&I funding','rules-standards':'rules/standards',
    'global-rivalry':'EU-US-China rivalry','foresight':'strategic foresight','research-careers':'research careers',
    'doctoral-workforce':'doctoral workforce','open-science-platforms':'open science/platforms','academic-freedom':'academic freedom'
  };
  function compactLabel(topic){return SHORT_LABELS[topic?.id]||clean(topic?.label).replace(/,.*$/,'')}
  function topSourceShare(rows){
    if(!rows.length)return {source:'',share:0};
    const c=new Map();
    for(const r of rows){const s=sourceOf(r);c.set(s,(c.get(s)||0)+1)}
    const top=[...c.entries()].sort((a,b)=>b[1]-a[1])[0]||['',0];
    return {source:top[0],share:top[1]/rows.length};
  }
  function evidenceScore(cn,cs,hn,hs){return log2(1+cn)*2+log2(1+hn)+Math.min(6,cs)+Math.min(6,hs)}
  function displayScore(raw){return Math.round(clamp(raw*2.25,1,99))}

  function conjunctions(ctx,namedPhenomena){
    const current=pairSummary(ctx.currentSets,ctx.currentRows),older=pairSummary(ctx.historicalSets,ctx.historicalRows);
    const blocked=namedPairBlocks(namedPhenomena),strong=[],candidates=[];
    for(const p of current.pairs.values()){
      const old=older.pairs.get(p.key);
      if(!old||blocked.has(p.key))continue;
      const ta=ctx.topicById.get(p.a),tb=ctx.topicById.get(p.b);
      if(!ta||!tb||sharedTerm(ta,tb))continue; // shared matcher can manufacture a false conjunction
      if(p.count<3||p.sourceCount<3||old.count<2||old.sourceCount<2)continue;
      if(p.lift<1.12)continue;
      const gain=p.lift-old.lift;
      const strengthening=gain>=0.28&&p.lift>=1.35;
      const persistent=p.lift>=1.75&&old.lift>=1.3;
      if(!strengthening&&!persistent)continue;
      const ev=evidenceScore(p.count,p.sourceCount,old.count,old.sourceCount);
      const raw=ev*(1+Math.min(1.4,Math.max(0,gain))*0.5)*(persistent?1.08:1.16);
      const top=topSourceShare(p.rows);
      const a=compactLabel(ta),b=compactLabel(tb);
      const claim=strengthening
        ?`${a} and ${b} are coupled more tightly in the current radar than in the older archive.`
        :`${a} and ${b} repeatedly arrive in the same records in both eras.`;
      const against=top.share>=0.34
        ?`A large share of the current pairing comes from ${top.source}; a source-specific editorial agenda could exaggerate the connection.`
        :'Current topics are inferred from configured evidence terms while older topics are archive labels. The pairing should survive source rotation before it is treated as structural.';
      const item={
        id:`conjunction-${p.key.replace('|','-')}`,kind:'conjunction',shape:strengthening?'Strengthening conjunction':'Conjunction',
        title:strengthening?`${a} is increasingly travelling with ${b}`:`${a} and ${b} keep arriving together`,
        claim,why:'The two issues have separate headings elsewhere. Their intersection may be the more important continuity.',caseAgainst:against,
        currentCount:p.count,currentSources:p.sourceCount,historicalCount:old.count,historicalSources:old.sourceCount,
        currentLift:p.lift,historicalLift:old.lift,liftGain:gain,score:displayScore(raw),
        currentEvidence:evidenceSlice(p.rows,4),historicalEvidence:evidenceSlice(old.rows,3),
        metrics:[
          {value:p.count,label:'current joint records'},{value:p.sourceCount,label:'current sources'},
          {value:old.count,label:'older joint records'},{value:`${p.lift.toFixed(1)}×`,label:'current coupling lift'}
        ]
      };
      const isStrong=p.count>=6&&p.sourceCount>=5&&old.sourceCount>=3&&(gain>=0.38||persistent);
      (isStrong?strong:candidates).push(item);
    }
    strong.sort((a,b)=>b.score-a.score||b.currentCount-a.currentCount);
    candidates.sort((a,b)=>b.score-a.score||b.currentCount-a.currentCount);
    return {strong,candidates};
  }

  function termStats(rows,term){
    const full=rows.filter(r=>hasTerm(analysisText(r),term));
    const titles=rows.filter(r=>hasTerm(titleText(r),term));
    return {count:full.length,sources:sourceCount(full),share:rows.length?full.length/rows.length:0,titleCount:titles.length,titleShare:rows.length?titles.length/rows.length:0,rows:full};
  }

  function vocabularyShifts(ctx){
    const strong=[],candidates=[];
    for(const topic of ctx.topics){
      const terms=topic.terms.filter(t=>!RENAME_EXCLUDE.has(t));
      if(terms.length<2)continue;
      const currentRows=ctx.currentRows.filter((_,i)=>ctx.currentSets[i].has(topic.id));
      const historicalRows=ctx.historicalRows.filter((_,i)=>ctx.historicalSets[i].has(topic.id));
      if(currentRows.length<8||historicalRows.length<6)continue;
      const stats=new Map(terms.map(term=>[term,{term,cur:termStats(currentRows,term),old:termStats(historicalRows,term)}]));
      let best=null;
      for(const oldTerm of terms){
        const old=stats.get(oldTerm);
        if(old.old.count<3||old.old.sources<3)continue;
        for(const newTerm of terms){
          if(newTerm===oldTerm)continue;
          const neo=stats.get(newTerm);
          if(neo.cur.count<4||neo.cur.sources<4)continue;
          const odds=((neo.cur.count+0.5)/(old.cur.count+0.5))/((neo.old.count+0.5)/(old.old.count+0.5));
          if(odds<2.6)continue;
          const titleOdds=((neo.cur.titleCount+0.5)/(old.cur.titleCount+0.5))/((neo.old.titleCount+0.5)/(old.old.titleCount+0.5));
          const evidence=evidenceScore(neo.cur.count,neo.cur.sources,old.old.count,old.old.sources);
          const raw=evidence*(1+Math.min(3.5,Math.max(0,log2(odds)))*0.22)*(titleOdds>=1.4?1.15:1);
          if(!best||raw>best.raw)best={old,neo,odds,titleOdds,raw};
        }
      }
      if(!best)continue;
      const {old,neo,odds,titleOdds,raw}=best;
      const titleSupports=titleOdds>=1.4&&(old.old.titleCount+neo.cur.titleCount)>=3;
      const item={
        id:`rename-${topic.id}-${old.term.replace(/ /g,'-')}-${neo.term.replace(/ /g,'-')}`,
        kind:'renaming',shape:titleSupports?'Framing shift':'Vocabulary shift candidate',
        title:`“${pretty(old.term)}” → “${pretty(neo.term)}”`,
        claim:`Inside ${topic.label}, the balance of vocabulary has moved sharply from “${pretty(old.term)}” toward “${pretty(neo.term)}”.`,
        why:'The issue may not be new at all; the language used to carry it may be changing.',
        caseAgainst:titleSupports
          ?'The title-only comparison points the same way, which reduces the text-depth bias. Source mix can still exaggerate the shift.'
          :'Historical text is thinner than current text. Treat this as a candidate until a title-only or manual check points the same way.',
        currentCount:neo.cur.count,currentSources:neo.cur.sources,historicalCount:old.old.count,historicalSources:old.old.sources,
        currentTerm:neo.term,historicalTerm:old.term,oddsRatio:odds,titleOdds,titleSupports,score:displayScore(raw),
        currentEvidence:evidenceSlice(neo.cur.rows,4),historicalEvidence:evidenceSlice(old.old.rows,3),
        metrics:[
          {value:old.old.count,label:`older “${pretty(old.term)}” records`},{value:old.old.sources,label:'older sources'},
          {value:neo.cur.count,label:`current “${pretty(neo.term)}” records`},{value:`${odds.toFixed(1)}×`,label:'relative vocabulary shift'}
        ]
      };
      const isStrong=titleSupports&&old.old.sources>=3&&neo.cur.sources>=5&&odds>=3.0;
      (isStrong?strong:candidates).push(item);
    }
    strong.sort((a,b)=>b.score-a.score||b.currentSources-a.currentSources);
    candidates.sort((a,b)=>b.score-a.score||b.currentSources-a.currentSources);
    return {strong,candidates};
  }

  function namedMatch(row,p){
    const txt=clean([row?.title,row?.headline,row?.summary,row?.core_message,row?.relevance_note,row?.signal_note,row?.anchor,row?.why_it_matters,row?.watch_theme].filter(Boolean).join(' '));
    return !!(p?.current&&p.current.test(txt));
  }
  function darkCorpus(currentRows,namedPhenomena){return currentRows.filter(r=>!(Array.isArray(namedPhenomena)?namedPhenomena:[]).some(p=>namedMatch(r,p)))}

  function dateQuality(historicalRows){
    let exact=0,known=0,jan1=0;
    for(const row of historicalRows){
      const p=clean(row?.date_precision).toLowerCase();
      if(p){known++;if(p==='day'||p==='exact')exact++}
      if(/^\d{4}-01-01$/.test(dateOf(row)))jan1++;
    }
    const trustworthy=historicalRows.length>0&&known/historicalRows.length>=0.8&&jan1/historicalRows.length<0.12;
    return {total:historicalRows.length,known,exact,jan1,trustworthy};
  }

  function build(data,history,config,namedPhenomena){
    const currentRows=currentCorpus(data,history),historicalRows=historicalCorpus(history),topics=topicDefinitions(config);
    const assignments=buildAssignments(currentRows,historicalRows,topics);
    const ctx={currentRows,historicalRows,topics,...assignments};
    const conj=conjunctions(ctx,namedPhenomena),rename=vocabularyShifts(ctx);
    const findings=[...rename.strong,...conj.strong].sort((a,b)=>b.score-a.score).slice(0,8);
    const findingIds=new Set(findings.map(x=>x.id));
    const candidates=[...rename.candidates,...conj.candidates].filter(x=>!findingIds.has(x.id)).sort((a,b)=>b.score-a.score).slice(0,8);
    const dark=darkCorpus(currentRows,namedPhenomena);
    return {
      findings,candidates,
      meta:{
        current:currentRows.length,historical:historicalRows.length,darkCurrent:dark.length,
        namedCurrent:currentRows.length-dark.length,topics:topics.length,dateQuality:dateQuality(historicalRows),
        returnDetectorsEnabled:dateQuality(historicalRows).trustworthy
      }
    };
  }

  return {build,currentCorpus,historicalCorpus,topicDefinitions,dateQuality};
});
