/* Historical reasoning context adapter.
   Raw historical findings remain untouched in historical/historical.json.
   This adapter joins Deep Scan sidecars at read time and exposes only active
   historical context to derived reasoning, with explicit trust weights:
   - authoritative Deep Scan + keep: 1.00
   - Deep Scan review:               0.60
   - awaiting Deep Scan/provisional: 0.35
   - not retained/drop:              0.00 (audit only, never reasoning)
*/
(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.RadarHistoricalReasoning=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';

  const ACTIVE=new Set(['provisional','keep','review']);
  const SAFE_CORRECTION_FIELDS=new Set([
    'title','authors','source','date','type','eu_relevance','text_mode','source_text_mode','event_status'
  ]);
  const AUTHORITATIVE_PROFILE='deep-reader-v2-authoritative';

  function clean(v){return String(v??'').replace(/\s+/g,' ').trim()}
  function clone(v){return v&&typeof v==='object'?JSON.parse(JSON.stringify(v)):v}
  function recordKey(row){
    const id=clean(row?.id||row?.record_id||row?.fingerprint);
    if(id)return `historical:id:${id}`;
    let doi=clean(row?.doi).toLowerCase().replace(/^https?:\/\/(?:dx\.)?doi\.org\//,'');
    if(doi)return `historical:doi:${doi}`;
    const link=clean(row?.link||row?.url);
    return link?`historical:link:${link}`:'';
  }
  function decisionFor(key,admission){
    const raw=key&&admission?.records&&typeof admission.records[key]==='object'?admission.records[key]:null;
    let decision=clean(raw?.decision).toLowerCase()||'provisional';
    if(!ACTIVE.has(decision)&&!['drop','drop_unverifiable','duplicate','needs_manual_verification'].includes(decision))decision='review';
    return {...(raw||{}),decision};
  }
  function statusFor(decision,entry){
    const v2=entry?.profile===AUTHORITATIVE_PROFILE;
    if(!ACTIVE.has(decision))return 'not_retained';
    if(decision==='keep'&&v2)return 'authoritative';
    if(decision==='review')return 'review';
    return 'awaiting_deep_scan';
  }
  function weightFor(status){
    if(status==='authoritative')return 1;
    if(status==='review')return 0.60;
    if(status==='awaiting_deep_scan')return 0.35;
    return 0;
  }
  function applyCorrection(row,correction){
    const out={...row};
    if(!correction||typeof correction!=='object')return out;
    const fields=correction.fields&&typeof correction.fields==='object'?correction.fields:{};
    for(const [field,value] of Object.entries(fields)){
      if(SAFE_CORRECTION_FIELDS.has(field)&&value!==null&&value!=='')out[field]=clone(value);
    }
    if(Object.prototype.hasOwnProperty.call(fields,'source')){
      delete out.source_tier;delete out.source_merit_score;
    }
    const unset=Array.isArray(correction.unset)?correction.unset:[];
    for(const field of unset){
      if(SAFE_CORRECTION_FIELDS.has(field)||field==='source_tier')delete out[field];
    }
    if(Object.keys(fields).length||unset.length){
      out.metadata_corrected=true;
      out.metadata_corrected_fields=Object.keys(fields).filter(k=>SAFE_CORRECTION_FIELDS.has(k)).sort();
      out.metadata_correction_reason=clean(correction.reason);
      out.metadata_correction_source=clean(correction.source);
    }
    return out;
  }
  function applyReader(row,entry){
    const out={...row};
    if(!entry||typeof entry!=='object')return out;
    for(const field of ['reader_title','reader_what','reader_why','reader_more','deep_read_mode','reader_text_model','reader_text_written_at']){
      if(entry[field]!==null&&entry[field]!==undefined&&entry[field]!=='')out[field]=clone(entry[field]);
    }
    if(entry.deep_analysis&&typeof entry.deep_analysis==='object')out.deep_analysis=clone(entry.deep_analysis);
    if(entry.profile!==AUTHORITATIVE_PROFILE)return out;

    // Mirror the active-corpus V2 semantics: old scanner hypothesis fields must
    // not keep driving interpretation after authoritative Deep Scan replacement.
    for(const field of ['eu_evidence','ri_evidence','geo_evidence','a_context_evidence','a_route','bridge_sentence','external_eu_bridge','external_eu_bridge_is_inference','strategic_classification','strategic_classification_source'])delete out[field];
    const verified=new Set(Array.isArray(out.metadata_corrected_fields)?out.metadata_corrected_fields:[]);
    if(!verified.has('eu_relevance'))delete out.eu_relevance;
    const deep=entry.deep_analysis&&typeof entry.deep_analysis==='object'?entry.deep_analysis:{};
    const what=clean(entry.reader_what),why=clean(entry.reader_why),more=clean(entry.reader_more);
    const main=clean(deep.main_finding)||what,relevance=clean(deep.radar_relevance)||why;
    if(what)out.what=what;
    if(main)out.core_message=main;
    if(more||main)out.summary=more||main;
    if(relevance)out.relevance_note=relevance;else delete out.relevance_note;
    if(why)out.why_it_matters=why;else delete out.why_it_matters;
    out.deep_scan_authoritative=true;
    out.semantic_source='deep_scan_v2';
    return out;
  }
  function decorate(raw,admission,reader,corrections){
    const key=recordKey(raw);
    const state=decisionFor(key,admission||{});
    const entry=key&&reader?.records&&typeof reader.records[key]==='object'?reader.records[key]:null;
    const correction=key&&corrections?.records&&typeof corrections.records[key]==='object'?corrections.records[key]:null;
    let row=applyCorrection(raw,correction);
    row=applyReader(row,entry);
    const status=statusFor(state.decision,entry);
    row.historical_deep_scan_key=key;
    row.historical_admission_status=state.decision;
    row.historical_target_strand=clean(state.target_strand||raw?.strand).toUpperCase();
    row.historical_reasoning_status=status;
    row.historical_reasoning_weight=weightFor(status);
    row.historical_deep_scan_profile=clean(entry?.profile);
    return row;
  }
  function build(history,admission,reader,corrections){
    const base=history&&typeof history==='object'?history:{};
    const rawItems=Array.isArray(base.items)?base.items:[];
    const auditItems=rawItems.filter(x=>x&&typeof x==='object').map(x=>decorate(x,admission,reader,corrections));
    const items=auditItems.filter(x=>Number(x.historical_reasoning_weight)>0);
    const counts={authoritative:0,review:0,awaiting_deep_scan:0,not_retained:0};
    for(const row of auditItems){
      const s=row.historical_reasoning_status;
      if(Object.prototype.hasOwnProperty.call(counts,s))counts[s]++;
    }
    return {
      ...base,
      items,
      audit_items:auditItems,
      reasoning_stats:{
        total_scanner_findings:auditItems.length,
        active_context:items.length,
        ...counts
      }
    };
  }

  return {build,decorate,recordKey,weightFor,statusFor};
});
