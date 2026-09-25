/* Shared rendering for engine-written cards (v26).
   The reasoning engine writes every card's copy (headline, lead, so-what, basis and a
   plain chip naming the kind of reasoning).  Pages only lay it out; they never
   replace engine copy with their own generic sentences. */
(function(g){
  'use strict';
  const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
  const esc=v=>clean(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  // Sentences that start with a number or currency ("€150 billion for ...") keep their
  // own casing; everything else gets the site's plain-language surface treatment.
  const surface=v=>{const t=clean(v);if(/^[^A-Za-z]/.test(t))return clean(g.RadarReaderStyle?.expandSurfaceTerms?.(t)||t);return clean(g.RadarReaderStyle?.surfaceText?.(t)||t)};
  function chip(label,wow){
    label=clean(label);if(!label)return '';
    const w=Math.max(0,Math.min(5,Number(wow)||0));
    return `<span class="kind-chip" data-wow="${w}" title="Reasoning depth ${w} of 5">${esc(label)}</span>`;
  }
  function fromCandidate(c){
    const card=c&&typeof c.card==='object'?c.card:{};
    return {
      kindLabel:clean(c?.reader_kind_label||card.kind_label||''),
      headline:clean(c?.reader_title||card.headline||c?.topic_label||''),
      lead:clean(c&&typeof c.card==='object'?card.lead:c?.reader_summary),
      so:clean(c?.reader_why||card.so_what||c?.reader_consequence||''),
      basis:clean(c?.reader_basis||card.basis||''),
      wow:Number(c?.wow)||0
    };
  }
  function body(x){
    return `${x.lead?`<p class="card-lead">${esc(surface(x.lead))}</p>`:''}${x.so?`<p class="card-so">${esc(surface(x.so))}</p>`:''}${x.basis?`<p class="card-basis">${esc(x.basis)}</p>`:''}`;
  }
  g.RadarCards={clean,esc,surface,chip,fromCandidate,body};
})(typeof globalThis!=='undefined'?globalThis:this);
