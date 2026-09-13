(()=>{
  'use strict';

  const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
  const ACTIVE=new Set(['provisional','keep','review']);
  const V2_PROFILE='deep-reader-v2-authoritative';

  function recordKey(r){
    const link=clean(r?.link||r?.url||'');
    if(link)return `link:${link}`;
    const doi=clean(r?.doi||'').toLowerCase();
    if(doi)return `doi:${doi.replace(/^https?:\/\/(?:dx\.)?doi\.org\//,'')}`;
    const id=clean(r?.id||r?.record_id||r?.fingerprint||'');
    return id?`id:${id}`:'';
  }

  function sourceHash(r){
    const material=[r?.title,r?.headline,r?.summary,r?.signal_note,r?.core_message,r?.what,r?.relevance_note,r?.why_it_matters,r?.bridge_sentence,r?.external_eu_bridge,r?.source,r?.type,r?.signal_kind,r?.event_status,r?.text_mode].map(clean).join('\n');
    let h=0x811c9dc5;
    for(let i=0;i<material.length;i++){h^=material.charCodeAt(i);h=Math.imul(h,0x01000193)>>>0}
    return h.toString(16).padStart(8,'0');
  }

  function siblingPath(primary,name){
    const q=String(primary||'radar.json').split('?')[0],slash=q.lastIndexOf('/');
    return (slash>=0?q.slice(0,slash+1):'')+name;
  }
  function activePath(primary){return siblingPath(primary,'radar_active.json')}
  function readerSidecarPath(primary){return siblingPath(primary,'reader_text.json')}
  function admissionPath(primary){return siblingPath(primary,'admission_state.json')}
  function correctionsPath(primary){return siblingPath(primary,'record_corrections.json')}

  async function fetchJson(path){
    const stamp='ts='+Date.now(),sep=path.includes('?')?'&':'?';
    const r=await fetch(path+sep+stamp,{cache:'no-store'});
    if(!r.ok)throw new Error(`HTTP ${r.status} ${path}`);
    return await r.json();
  }

  function applyCorrection(row,c){
    if(!c||typeof c!=='object')return row;
    const fields=c.fields&&typeof c.fields==='object'?c.fields:{};
    const allowed=new Set(['title','authors','source','date','type','eu_relevance','text_mode','source_text_mode','event_status']);
    const unsetAllowed=new Set([...allowed,'source_tier']);
    for(const [k,v] of Object.entries(fields))if(allowed.has(k)&&v!==null&&clean(v)!=='')row[k]=v;
    if(Object.prototype.hasOwnProperty.call(fields,'source')){delete row.source_tier;delete row.source_merit_score}
    for(const k of Array.isArray(c.unset)?c.unset:[])if(unsetAllowed.has(k)&&k!=='title')delete row[k];
    if(Object.keys(fields).length||(c.unset||[]).length){row.metadata_corrected=true;row.metadata_corrected_fields=Object.keys(fields).filter(k=>allowed.has(k)).sort();row.metadata_correction_reason=clean(c.reason)}
    return row;
  }

  function applyReaderEntry(row,t){
    if(!t||typeof t!=='object')return row;
    for(const k of ['reader_title','reader_what','reader_why','reader_more','deep_read_mode','reader_text_model','reader_text_written_at']){
      const v=t[k];if(v!==undefined&&v!==null&&clean(v)!=='')row[k]=v;
    }
    if(t.deep_analysis&&typeof t.deep_analysis==='object')row.deep_analysis=t.deep_analysis;
    if(clean(t.profile)!==V2_PROFILE)return row;
    for(const k of ['eu_evidence','ri_evidence','geo_evidence','a_context_evidence','a_route','bridge_sentence','external_eu_bridge','external_eu_bridge_is_inference','strategic_classification','strategic_classification_source'])delete row[k];if(!(row.metadata_corrected_fields||[]).includes('eu_relevance'))delete row.eu_relevance;
    const deep=t.deep_analysis&&typeof t.deep_analysis==='object'?t.deep_analysis:{};
    const what=clean(t.reader_what),why=clean(t.reader_why),more=clean(t.reader_more),main=clean(deep.main_finding)||what,relevance=clean(deep.radar_relevance)||why;
    if(what)row.what=what;
    if(main)row.core_message=main;
    if(more||main)row.summary=more||main;
    if(relevance)row.relevance_note=relevance;else delete row.relevance_note;
    if(why)row.why_it_matters=why;else delete row.why_it_matters;
    row.deep_scan_authoritative=true;row.semantic_source='deep_scan_v2';
    return row;
  }

  function applyReaderText(doc,sidecar){
    const table=sidecar&&typeof sidecar==='object'&&sidecar.records&&typeof sidecar.records==='object'?sidecar.records:null;
    if(!table)return {doc,applied:0,stale:0};
    let applied=0;
    for(const strand of ['strand_a','strand_b','strand_c','frontier_evidence'])for(const r of Array.isArray(doc?.[strand])?doc[strand]:[]){
      const t=table[recordKey(r)];if(!t)continue;applyReaderEntry(r,t);applied++;
    }
    return {doc,applied,stale:0};
  }

  function buildActiveDocument(doc,admission,corrections,reader){
    const clone=JSON.parse(JSON.stringify(doc)),a=admission?.records||{},c=corrections?.records||{},t=reader?.records||{};
    for(const k of ['strand_a','strand_b','strand_c','frontier_evidence'])clone[k]=[];
    const targets={A:'strand_a',B:'strand_b',C:'strand_c'},seen=new Set();
    const currentKeys=new Set();
    for(const source of ['strand_a','strand_b','strand_c','frontier_evidence'])for(const row of Array.isArray(doc?.[source])?doc[source]:[]){const k=recordKey(row);if(k)currentKeys.add(k)}
    let applied=0;
    for(const source of ['strand_a','strand_b','strand_c','frontier_evidence'])for(const original of Array.isArray(doc?.[source])?doc[source]:[]){
      if(!original||typeof original!=='object')continue;
      const key=recordKey(original);
      let state=(key&&a[key]&&typeof a[key]==='object')?a[key]:{decision:'provisional',reason_code:'AWAITING_DEEP_SCAN_V2'};
      let decision=clean(state.decision||'provisional').toLowerCase();
      if(decision==='duplicate'&&(!clean(state.duplicate_of)||!currentKeys.has(clean(state.duplicate_of)))){state={...state,decision:'review',reason_code:'DUPLICATE_CANONICAL_MISSING',reason:'The previously selected canonical duplicate is no longer in the raw corpus; manual review is required.'};decision='review'}
      if(!ACTIVE.has(decision))continue;
      let row=JSON.parse(JSON.stringify(original));
      row=applyCorrection(row,key?c[key]:null);row=applyReaderEntry(row,key?t[key]:null);
      let target=source;
      const ts=clean(state.target_strand).toUpperCase();
      if(source!=='frontier_evidence'&&targets[ts]){target=targets[ts];row.strand=ts}
      const sk=`${target}|${key||clean(row.title||row.headline)}`,verified=clean(state.source).toLowerCase()==='deep_scan_v2';if(verified&&seen.has(sk))continue;if(verified)seen.add(sk);
      row.admission_status=decision;row.admission_reason_code=clean(state.reason_code);if(clean(state.reason))row.admission_reason=clean(state.reason);
      clone[target].push(row);applied++;
    }
    clone.active_corpus_snapshot=true;
    return {doc:clone,applied};
  }

  function inactiveCountFromEmbeddedState(doc){
    const d=doc?.active_corpus?.decision_counts||{};
    return Number(d.drop||0)+Number(d.drop_unverifiable||0)+Number(d.duplicate||0);
  }

  async function load(primary='radar.json',fallback='radar_seed.json'){
    // Generated active snapshot is the preferred public contract. It already contains
    // corrections, authoritative V2 semantics and active-only derived reasoning.
    try{
      const active=await fetchJson(activePath(primary));
      if(active&&active.active_corpus_snapshot){globalThis.RadarReaderLanguageStatus={enabled:true,authoritative:true,source:'radar_active.json'};return active}
    }catch(_e){}

    let doc=null,loadedPath='';
    for(const path of [primary,fallback]){try{doc=await fetchJson(path);loadedPath=path;break}catch(_e){}}
    if(!doc)throw new Error('Radar data unavailable');

    // Compatibility/fail-safe path for deployments where radar_active.json has not yet
    // been generated. Build the active view in-browser from the same sidecars.
    try{
      const [admission,corrections,reader]=await Promise.all([
        fetchJson(admissionPath(loadedPath)),fetchJson(correctionsPath(loadedPath)),fetchJson(readerSidecarPath(loadedPath))
      ]);
      const built=buildActiveDocument(doc,admission,corrections,reader);
      globalThis.RadarReaderLanguageStatus={enabled:true,authoritative:true,source:'sidecars',applied:built.applied};
      return built.doc;
    }catch(e){
      // Never silently re-activate known dropped evidence because a sidecar fetch failed.
      if(inactiveCountFromEmbeddedState(doc)>0)throw new Error('Active-corpus verification data unavailable; refusing to display raw inactive evidence.');
      const merged=applyReaderText(doc,{records:{}});
      globalThis.RadarReaderLanguageStatus={enabled:false,authoritative:false,error:clean(e?.message||e)};
      return merged.doc;
    }
  }

  globalThis.RadarData={load,recordKey,sourceHash,applyReaderText,buildActiveDocument};
})();
