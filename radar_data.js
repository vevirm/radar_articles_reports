(()=>{
  'use strict';

  const clean=v=>String(v??'').replace(/\s+/g,' ').trim();

  function recordKey(r){
    const link=clean(r?.link||r?.url||'');
    if(link)return `link:${link}`;
    const doi=clean(r?.doi||'').toLowerCase();
    if(doi)return `doi:${doi.replace(/^https?:\/\/(?:dx\.)?doi\.org\//,'')}`;
    const id=clean(r?.id||r?.record_id||r?.fingerprint||'');
    if(id)return `id:${id}`;
    return '';
  }

  // Small deterministic hash. It is not a security primitive; it only prevents
  // stale reader prose from being overlaid after the source material changes.
  function sourceHash(r){
    const material=[r?.title,r?.summary,r?.bridge_sentence,r?.source,r?.type]
      .map(clean).join('\n');
    let h=0x811c9dc5;
    for(let i=0;i<material.length;i++){
      h^=material.charCodeAt(i);
      h=Math.imul(h,0x01000193)>>>0;
    }
    return h.toString(16).padStart(8,'0');
  }

  function readerSidecarPath(primary){
    const q=String(primary||'radar.json').split('?')[0];
    const slash=q.lastIndexOf('/');
    return (slash>=0?q.slice(0,slash+1):'')+'reader_text.json';
  }

  async function fetchJson(path){
    const stamp='ts='+Date.now();
    const sep=path.includes('?')?'&':'?';
    const r=await fetch(path+sep+stamp,{cache:'no-store'});
    if(!r.ok)throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }

  function applyReaderText(doc,sidecar){
    const table=sidecar&&typeof sidecar==='object'&&sidecar.records&&typeof sidecar.records==='object'
      ?sidecar.records:null;
    if(!table)return {doc,applied:0,stale:0};
    let applied=0,stale=0;
    for(const strand of ['strand_a','strand_b','strand_c']){
      const rows=Array.isArray(doc?.[strand])?doc[strand]:[];
      for(const r of rows){
        const key=recordKey(r);
        if(!key)continue;
        const t=table[key];
        if(!t||typeof t!=='object')continue;
        if(t.source_hash&&t.source_hash!==sourceHash(r)){
          stale++;
          continue;
        }
        const what=clean(t.reader_what),why=clean(t.reader_why),more=clean(t.reader_more);
        if(what)r.reader_what=what;
        if(why)r.reader_why=why;
        if(more)r.reader_more=more;
        if(what||why||more){
          r.reader_text_model=clean(t.reader_text_model||t.model||'');
          r.reader_text_written_at=clean(t.reader_text_written_at||t.written_at||'');
          applied++;
        }
      }
    }
    return {doc,applied,stale};
  }

  async function load(primary='radar.json',fallback='radar_seed.json'){
    let doc=null,loadedPath='';
    for(const path of [primary,fallback]){
      try{
        doc=await fetchJson(path);
        loadedPath=path;
        break;
      }catch(_e){}
    }
    if(!doc)throw new Error('Radar data unavailable');

    // Reader language is deliberately optional and downstream. Any failure here
    // is swallowed: the scanner output remains the source of truth and the site
    // falls back to browser-side wording.
    let status={enabled:false,applied:0,stale:0,error:''};
    try{
      const sidecar=await fetchJson(readerSidecarPath(loadedPath));
      const merged=applyReaderText(doc,sidecar);
      doc=merged.doc;
      status={enabled:true,applied:merged.applied,stale:merged.stale,error:''};
    }catch(e){
      status={enabled:false,applied:0,stale:0,error:clean(e?.message||e)};
    }
    globalThis.RadarReaderLanguageStatus=status;
    return doc;
  }

  globalThis.RadarData={load,recordKey,sourceHash,applyReaderText};
})();
