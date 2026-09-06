(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.RadarStuffWorkbook=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
  const norm=v=>clean(v).toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  const titleOf=x=>clean(x?.title||x?.headline);
  const linkOf=x=>clean(x?.link||x?.url);
  const enc=new TextEncoder();

  function buildRows(data,Merit){
    const products=[['A',data?.strand_a],['B',data?.strand_b],['C',data?.strand_c],['Matrix evidence',data?.frontier_evidence],['Strategic pathway',data?.strategic_pathways]];
    const groups=new Map();
    for(const [product,items] of products){
      for(const x of Array.isArray(items)?items:[]){
        if(!x||typeof x!=='object')continue;
        const u=linkOf(x).toLowerCase().replace(/\/$/,'');
        const t=norm(titleOf(x));
        const key=u?'u:'+u:'t:'+t;
        if(key==='t:')continue;
        const comp=[x.summary,x.core_message,x.relevance_note,x.why_it_matters,x.authors,x.source,x.link].filter(v=>clean(v)).length;
        const score=Merit.scoreFor(x);
        const old=groups.get(key);
        if(!old)groups.set(key,{x,products:new Set([product]),score,comp});
        else{
          old.products.add(product);
          if(score>old.score||(score===old.score&&comp>old.comp)){old.x=x;old.score=score;old.comp=comp;}
        }
      }
    }
    const rows=[...groups.values()].map(g=>{
      const x=g.x,m=Merit.forItem(x),c=Merit.componentsFor(x);
      const sc=x.strategic_classification&&typeof x.strategic_classification==='object'?clean(x.strategic_classification.primary):'';
      return {
        score:m.score,band:`${m.code} — ${m.label}`,title:titleOf(x),date:clean(x.date).slice(0,10),product:[...g.products].sort().join(', '),
        source:clean(x.source||x.journal||x.institution),authors:clean(x.authors),authorityPoints:c.authorityPoints,authority:c.authority,
        relevancePoints:c.relevancePoints,relevance:c.relevance,evidencePoints:c.evidencePoints,evidence:c.evidence,
        authorPoints:c.authorTransparencyPoints,type:clean(x.type||x.signal_kind),euRelevance:clean(x.eu_relevance||x.euRelevance),
        euEvidence:(x.eu_evidence||[]).map(clean).join('; '),riEvidence:(x.ri_evidence||[]).map(clean).join('; '),geoEvidence:(x.geo_evidence||[]).map(clean).join('; '),
        core:clean(x.core_message||x.signal_note||x.summary),note:clean(x.relevance_note||x.why_it_matters),matrix:clean(x.matrix_auto_cell),strategic:sc,
        provenance:clean(x.discovery_provenance||x.origin),sourceTier:clean(x.source_tier||x.sourceTier),firstSeen:clean(x.first_seen),link:linkOf(x)
      };
    }).sort((a,b)=>b.score-a.score||b.date.localeCompare(a.date)||a.title.localeCompare(b.title));
    rows.forEach((r,i)=>r.rank=i+1);
    return rows;
  }

  const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  const col=n=>{let s='';for(;n>0;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s};
  function cell(v,r,c,style=0){const ref=col(c)+r;if(typeof v==='number'&&Number.isFinite(v))return `<c r="${ref}" s="${style}"><v>${v}</v></c>`;return `<c r="${ref}" s="${style}" t="inlineStr"><is><t xml:space="preserve">${esc(v)}</t></is></c>`;}
  function sheetXml(headers,body,widths){
    const maxc=headers.length;
    let xml=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>${widths.map((w,i)=>`<col min="${i+1}" max="${i+1}" width="${w}" customWidth="1"/>`).join('')}</cols><sheetData>`;
    xml+=`<row r="1" ht="28" customHeight="1">${headers.map((h,i)=>cell(h,1,i+1,1)).join('')}</row>`;
    for(let i=0;i<body.length;i++)xml+=`<row r="${i+2}">${body[i].map((v,j)=>cell(v,i+2,j+1,j===1?2:3)).join('')}</row>`;
    return xml+`</sheetData><autoFilter ref="A1:${col(maxc)}${body.length+1}"/></worksheet>`;
  }

  let crcTable=null;
  function crc32(buf){
    if(!crcTable)crcTable=Array.from({length:256},(_,n)=>{let c=n;for(let k=0;k<8;k++)c=(c&1)?0xEDB88320^(c>>>1):c>>>1;return c>>>0});
    let c=0xFFFFFFFF;for(const b of buf)c=crcTable[(c^b)&255]^(c>>>8);return (c^0xFFFFFFFF)>>>0;
  }
  function write16(view,off,v){view.setUint16(off,v,true)}
  function write32(view,off,v){view.setUint32(off,v>>>0,true)}
  function concat(parts){const total=parts.reduce((n,p)=>n+p.length,0),out=new Uint8Array(total);let off=0;for(const p of parts){out.set(p,off);off+=p.length;}return out;}
  function zip(entries){
    const locals=[],centrals=[];let offset=0;const date=33,time=0,flag=0x800;
    for(const [name,text] of Object.entries(entries)){
      const nb=enc.encode(name),db=enc.encode(text),crc=crc32(db);
      const lh=new Uint8Array(30),lv=new DataView(lh.buffer);write32(lv,0,0x04034b50);write16(lv,4,20);write16(lv,6,flag);write16(lv,8,0);write16(lv,10,time);write16(lv,12,date);write32(lv,14,crc);write32(lv,18,db.length);write32(lv,22,db.length);write16(lv,26,nb.length);write16(lv,28,0);
      locals.push(lh,nb,db);
      const ch=new Uint8Array(46),cv=new DataView(ch.buffer);write32(cv,0,0x02014b50);write16(cv,4,20);write16(cv,6,20);write16(cv,8,flag);write16(cv,10,0);write16(cv,12,time);write16(cv,14,date);write32(cv,16,crc);write32(cv,20,db.length);write32(cv,24,db.length);write16(cv,28,nb.length);write16(cv,30,0);write16(cv,32,0);write16(cv,34,0);write16(cv,36,0);write32(cv,38,0);write32(cv,42,offset);
      centrals.push(ch,nb);offset+=lh.length+nb.length+db.length;
    }
    const central=concat(centrals),local=concat(locals),end=new Uint8Array(22),ev=new DataView(end.buffer),count=Object.keys(entries).length;
    write32(ev,0,0x06054b50);write16(ev,4,0);write16(ev,6,0);write16(ev,8,count);write16(ev,10,count);write32(ev,12,central.length);write32(ev,16,local.length);write16(ev,20,0);
    return concat([local,central,end]);
  }

  function buildShockRows(data){
    const shocks=Array.isArray(data?.shock_inference?.dynamic_shocks)?data.shock_inference.dynamic_shocks:[];
    const evidence=x=>(Array.isArray(x)?x:[]).map(e=>{
      if(!e||typeof e!=='object')return clean(e);
      const bits=[e.row?`#${e.row}`:'',clean(e.title),clean(e.source)].filter(Boolean);
      return bits.join(' · ');
    }).filter(Boolean).join(' | ');
    return shocks.map(s=>[
      clean(s.status),Number(s.inference_score)||0,clean(s.title),clean(s.plainly),clean(s.second_order),
      (s.conditions||[]).map(clean).filter(Boolean).join(' | '),
      (s.case_against||[]).map(clean).filter(Boolean).join(' | '),
      (s.prevention_actions||[]).map(clean).filter(Boolean).join(' | '),
      (s.watch_for||[]).map(clean).filter(Boolean).join(' | '),
      clean(s.net_assessment),s.official_trigger_present?'yes':'no',Number(s.coupling_count)||0,
      evidence(s.support),evidence(s.prevention_evidence||s.against)
    ]);
  }

  function buildXlsx(data,Merit){
    if(!Merit?.scoreFor||!Merit?.forItem||!Merit?.componentsFor)throw new Error('RadarSourceMerit unavailable');
    const rows=buildRows(data,Merit);
    const shockRows=buildShockRows(data);
    const h1=['Rank','Score / 100','Band','Title','Date','Product','Source','Authors','Authority / 55','Authority basis','EU relevance / 25','EU relevance basis','Evidence / 15','Evidence basis','Author transparency / 5','Type','EU relevance code','EU evidence','R&I evidence','Strategic evidence','Core message','Relevance / admission note','Matrix auto cell','Strategic classification','Discovery provenance','Source tier','First seen','Source link'];
    const b1=rows.map(r=>[r.rank,r.score,r.band,r.title,r.date,r.product,r.source,r.authors,r.authorityPoints,r.authority,r.relevancePoints,r.relevance,r.evidencePoints,r.evidence,r.authorPoints,r.type,r.euRelevance,r.euEvidence,r.riEvidence,r.geoEvidence,r.core,r.note,r.matrix,r.strategic,r.provenance,r.sourceTier,r.firstSeen,r.link]);
    const widths=[8,11,16,42,12,16,27,32,12,28,15,31,12,28,18,24,18,28,28,28,42,48,20,22,24,20,20,42];
    const method=[
      ['TECHNICAL EVIDENCE RANKING — HOW TO READ IT',''],
      ['Purpose','Audit/export ranking for evidence used by the EU R&I × geopolitics radar. It is intentionally confined to Stuff.'],
      ['Score','0–100 = source authority + EU relevance + evidence strength + author transparency.'],
      ['Authority (max 55)','EU official/body 55; major public/multilateral 48; strong science network or leading peer-reviewed journal 46; leading policy institute 43; established journal/publisher 38; ordinary peer-reviewed journal 32; specialist/current-event source about 25–27; preprint 22.'],
      ['EU relevance (max 25)','Direct EU relevance 25; material external development with EU implications 20; relevance by comparison/implication 18. EU relevance is also enforced separately by scanner admission logic for substantive evidence products.'],
      ['Evidence (max 15)','Official or peer-reviewed source 15; institutional/manual-verified research 13–14; current-event signal 9; preprint or abstract 8.'],
      ['Author transparency (max 5)','Named author(s) 5; identifiable institutional author 4; no named author in radar metadata 2.'],
      ['Bands','A ≥93 Highest; B 85–92 Very strong; C 75–84 Strong; D 65–74 Useful; E <65 Supporting.'],
      ['Scanner role','The 0–100 score itself does not admit or reject findings. Scanner admission separately requires acceptable source provenance and EU/R&I scope.'],
      ['Reader-ordering rule','The score must not order Radar, Matrix, Literature, Risks & Opportunities, External Shocks, issue views or Historical evidence.'],
      ['Matrix rule','Source quality and this score do not determine Matrix placement. Matrix is a separate analytical product.'],
      ['Strategic-products rule','Risks, Opportunities and External Shocks are independently scanned and classified from source text; this score is audit metadata only.'],
      ['Shock inference rule','A shock must connect evidence across distinct parts of the corpus, state what must be true, test the case against itself, identify what could prevent it, and list observable indicators.'],
      ['Shock challenge rule','Surprise is not enough. Missing triggers, weak mechanisms, concentrated evidence, existing protections, or too many required conditions must reduce confidence or replace the dramatic version with a better-supported one.'],
      ['Shock audit sheet','The Shock audit sheet keeps technical reasoning out of the easiest pages while preserving assumptions, counter-evidence, prevention actions, indicators and source links for review.'],
      ['Current data state',`${clean(data?.run_completed_at||data?.last_updated)} · A=${(data?.strand_a||[]).length} · B=${(data?.strand_b||[]).length} · C=${(data?.strand_c||[]).length} · Strategic pathways=${(data?.strategic_pathways||[]).length}`],
      ['Workbook rows',`${rows.length} deduplicated evidence records`],
      ['Shock rows',`${shockRows.length} inferred shock records`]
    ];
    const shockHeaders=['Status','Inference score','Shock','Plain-language shock','Second-order effect','Conditions that must hold','Case against','What could prevent it','What to watch','Net assessment','Official trigger present','Evidence couplings','Evidence for','Prevention / counter evidence'];
    const shockWidths=[16,14,34,46,46,58,65,58,58,32,18,16,70,70];
    const styles=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="3"><font><sz val="10"/><name val="Arial"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Arial"/></font><font><b/><color rgb="FFC40018"/><sz val="10"/><name val="Arial"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF111111"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;
    const files={
      '[Content_Types].xml':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>`,
      '_rels/.rels':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`,
      'xl/workbook.xml':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Ranked sources" sheetId="1" r:id="rId1"/><sheet name="Method" sheetId="2" r:id="rId2"/><sheet name="Shock audit" sheetId="3" r:id="rId3"/></sheets></workbook>`,
      'xl/_rels/workbook.xml.rels':`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/><Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`,
      'xl/styles.xml':styles,
      'xl/worksheets/sheet1.xml':sheetXml(h1,b1,widths),
      'xl/worksheets/sheet2.xml':sheetXml(['Field','Explanation'],method,[28,95]),
      'xl/worksheets/sheet3.xml':sheetXml(shockHeaders,shockRows,shockWidths)
    };
    return zip(files);
  }
  return {buildRows,buildShockRows,buildXlsx};
});
