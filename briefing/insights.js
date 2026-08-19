(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  root.RadarInsights=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  const TOPICS=[
    {name:'Raw materials', terms:['critical raw material','critical raw materials','critical mineral','critical minerals','rare earth','rare earths','lithium','cobalt','nickel','graphite','copper','gallium','germanium','tungsten','mining','refining','mineral supply','resource security']},
    {name:'Research', terms:['horizon europe','framework programme','framework program','european research council','erc plus','erc grant','research funding','research infrastructure','research security','knowledge security','science diplomacy','scientific cooperation','research cooperation','research collaboration','research and innovation','research policy','university','universities','researcher','researchers']},
    {name:'AI', terms:['artificial intelligence','foundation model','foundation models','large language model','large language models','machine learning','ai factory','ai factories','gpu','gpus','compute capacity','computing capacity','supercomputing',' ai ']},
    {name:'Semiconductors & quantum', terms:['semiconductor','semiconductors','microelectronics','microchip','microchips','advanced chip','advanced chips','chip','chips','chip act','chips act','chip supply','chips supply','quantum','photonics']},
    {name:'Energy', terms:['energy security','nuclear','reactor','reactors','small modular reactor','smr','hydrogen','renewable','renewables','electricity grid','power grid','battery','batteries','clean tech','cleantech','fusion','decarbonisation','decarbonization']},
    {name:'Security & defence', terms:['defence','defense','dual-use','dual use','military','nato','security screening','export control','export controls','foreign interference','knowledge leakage','economic coercion','sanction','sanctions','war','ukraine','russia']},
    {name:'Trade & industry', terms:['economic security','industrial policy','industrial competitiveness','competitiveness','manufacturing','supply chain','supply chains','trade','tariff','tariffs','investment screening','foreign direct investment','strategic autonomy','strategic dependency','strategic dependencies','de-risking','derisking','single market','industry policy']},
    {name:'Digital & cyber', terms:['digital infrastructure','cloud infrastructure','cloud','telecom','telecommunications','5g','6g','submarine cable','subsea cable','data governance','data space','digital sovereignty','cybersecurity','cyber security','cyber']},
    {name:'Space', terms:['satellite','satellites','launch vehicle','launcher','copernicus','galileo','earth observation','orbital','space sector','space programme','space program']},
    {name:'Health & biotech', terms:['biotech','biotechnology','life science','life sciences','health security','pharma','pharmaceutical','pharmaceuticals','vaccine','vaccines','biomedical','genomics','bioeconomy','global health']},
    {name:'Talent & skills', terms:['researcher mobility','scientist mobility','brain drain','brain gain','talent','skills','visa','visas','doctoral','phd','workforce','training']},
    {name:'International partnerships', terms:['global gateway','indo-pacific','indo pacific','international cooperation','international partnership','international partnerships','association agreement','associated country','eu-asia','europe-asia','china','chinese','united states','japan','south korea','india','taiwan','africa','latin america','arctic','geopolitical']},
    {name:'Foresight', terms:['foresight','horizon scanning','scenario planning','scenario building','weak signal','weak signals','delphi','backcasting','anticipatory governance','futures literacy','futures research','strategic intelligence','scenario','scenarios']}
  ];
  const OTHER='Other strategic R&I';
  const ACTION=/\b(introduc|launch|adopt|propos|plan|expand|scale|build|fund|invest|restrict|tighten|strengthen|reduce|diversif|shift|change|increase|decrease|accelerat|delay|block|ban|require|open|close|create|develop|deploy|establish|agree|sign|join|withdraw|prioriti[sz]|target|support|secure|protect|screen|coordinate|cooperat|compete|decoupl|derisk|de-risk|reform|amend|extend|raise|cut|approve|reject)\w*/i;
  const BOILER=/\b(annual activity report|this amount does not include|grant agreement no\.?|received funding from|table of contents|references|copyright|all rights reserved|cf\.|article \d+ of|council regulation \(ec\)|implementation decision c\(|commission decision c\()\b/i;
  const PRONOUN=/^(it|this|these|they|their|its|the report|the study|the paper)\b/i;
  const DOC_DEBRIS_WORDS=/\b(annex|appendix|methodology|table of contents|contents|list of (?:figures|tables)|bibliography|references|glossary|acronyms?|abbreviations?|chapter|section)\b/i;

  function clean(v){return String(v??'').replace(/\u00ad/g,'').replace(/[ \t]+/g,' ').replace(/\s*\n\s*/g,' ').trim()}
  function norm(v){return ` ${clean(v).toLowerCase().replace(/[–—]/g,'-').replace(/[^a-z0-9+.#/&-]+/g,' ').replace(/\s+/g,' ').trim()} `}
  function keyFor(x){return norm(x.link||x.title||x.headline||'').trim()}
  function dateFor(x){return clean(x.date||x.published||x.updated||x.first_seen||'')}
  function sourceText(x){return clean([x.title,x.headline,x.summary,x.signal_note,x.anchor].filter(Boolean).join(' '))}

  function containsTerm(text,term){const n=norm(term).trim();return !!n&&text.includes(` ${n} `)}
  function topicScore(x,topic){
    const title=norm(x.title||x.headline||'');
    const body=norm(sourceText(x));
    let score=0;
    for(const term of topic.terms){
      if(containsTerm(title,term)) score+=8;
      if(containsTerm(body,term)) score+=2;
    }
    return score;
  }
  function topicFor(x){
    let best=OTHER,score=0;
    for(const topic of TOPICS){const s=topicScore(x,topic);if(s>score){score=s;best=topic.name}}
    return best;
  }

  function isDocumentDebris(value){
    const s=clean(value);
    if(!s) return true;
    // PDF table-of-contents / section-heading artefacts such as
    // "114 ANNEX 3: METHODOLOGY (EXTENDED) ................."
    if(/\.{4,}|·{4,}|_{4,}|-{8,}/.test(s)) return true;
    if(/^\s*(?:page\s*)?\d{1,4}\s+(?:annex|appendix|chapter|section|methodology)\b/i.test(s)) return true;
    if(/^(?:annex|appendix|chapter|section)\s+[a-z0-9ivx.-]+\s*[:.-]/i.test(s)) return true;
    if(/^(?:table of contents|contents|list of (?:figures|tables)|bibliography|references|glossary|acronyms?|abbreviations?)\b/i.test(s)) return true;
    if(/\b(?:annex|appendix)\s+\d+\s*:\s*(?:methodology|methods?|technical annex)\b/i.test(s)) return true;
    if(/^\s*\d{1,4}\s+[A-Z][A-Z0-9 &()/:,.-]{8,}\s*$/.test(s)) return true;
    if(/^\s*(?:page\s+)?\d{1,4}\s*(?:of\s+\d{1,4})?\s*$/i.test(s)) return true;

    const letters=(s.match(/[A-Za-z]/g)||[]).length;
    const upper=(s.match(/[A-Z]/g)||[]).length;
    const words=s.split(/\s+/).filter(Boolean).length;
    // Short, mostly-uppercase document headings are not signals.
    if(words<=14 && letters>=8 && upper/letters>0.78 && DOC_DEBRIS_WORDS.test(s) && !ACTION.test(s)) return true;
    return false;
  }

  function splitSentences(text){
    return clean(text)
      .replace(/\((?:\d+|[ivx]+)\)/gi,' ')
      .replace(/\[(?:\d+|[a-z])\]/gi,' ')
      .replace(/\s+/g,' ')
      .split(/(?<=[.!?])\s+(?=[A-Z0-9“"'‘])/)
      .map(clean).filter(Boolean);
  }
  function topicTerms(topic){const t=TOPICS.find(x=>x.name===topic);return t?t.terms:[]}
  function scoreSentence(s,topic,index){
    if(s.length<28) return -100;
    if(isDocumentDebris(s)) return -1000;
    let score=0;
    if(s.length>=55&&s.length<=220) score+=6; else if(s.length<=300) score+=3; else score-=5;
    if(ACTION.test(s)) score+=8;
    if(BOILER.test(s)) score-=16;
    if(PRONOUN.test(s)) score-=3;
    if(index===0) score+=1;
    const n=norm(s);
    for(const term of topicTerms(topic)){const t=norm(term).trim();if(n.includes(t))score+=2}
    if(/\b(EU|European|Europe|China|US|United States|Japan|Korea|India|Russia|Ukraine|NATO)\b/.test(s)) score+=2;
    if(/\b(202[0-9]|2030|billion|million|grant|programme|program|policy|strategy|framework|agreement|funding|investment|capacity|dependency|security)\b/i.test(s)) score+=2;
    return score;
  }
  function extractActionClause(s){
    const markers=[' with a view to ',' in order to ',' aims to ',' aimed to ',' seeks to ',' will ',' plans to ',' agreed to ',' decided to ',' proposes to ',' proposed to '];
    const low=s.toLowerCase();
    for(const m of markers){
      const i=low.indexOf(m);
      if(i>40){
        let c=clean(s.slice(i+m.length));
        if(c.length>=35){
          if(m.trim()==='will') c='Will '+c;
          else if(m.trim()==='plans to') c='Plans to '+c;
          else if(m.trim()==='agreed to') c='Agreed to '+c;
          else if(m.trim()==='decided to') c='Decided to '+c;
          else if(m.trim()==='proposes to'||m.trim()==='proposed to') c='Proposes to '+c;
          else if(m.trim()==='aims to'||m.trim()==='aimed to') c='Aims to '+c;
          else if(m.trim()==='seeks to') c='Seeks to '+c;
          else c=c.charAt(0).toUpperCase()+c.slice(1);
          return c;
        }
      }
    }
    return s;
  }
  function cleanPoint(s){
    s=clean(s)
      .replace(/^SUMMARY\s*/i,'')
      .replace(/\s*\(\d+\)\s*/g,' ')
      .replace(/\s*\[[^\]]{1,24}\]\s*/g,' ')
      .replace(/\s+/g,' ')
      .trim();
    s=extractActionClause(s);
    s=s.replace(/^(finally|moreover|however|therefore|in addition|accordingly),?\s+/i,'');
    if(s.length>230){
      const parts=s.split(/\s*[;:]\s*|\s+[–—]\s+/).map(clean).filter(Boolean);
      const actionable=parts.find(p=>p.length>=45&&ACTION.test(p));
      if(actionable) s=actionable;
    }
    const words=s.split(/\s+/);
    if(words.length>34) s=words.slice(0,34).join(' ').replace(/[,:;\-–—]+$/,'')+'…';
    else if(s.length>225) s=s.slice(0,222).replace(/\s+\S*$/,'').replace(/[,:;\-–—]+$/,'')+'…';
    s=s.trim();
    if(s&&!/[.!?…]$/.test(s)) s+='.';
    if(s) s=s.charAt(0).toUpperCase()+s.slice(1);
    return s;
  }
  function titlePoint(x){
    let t=clean(x.headline||x.title||'').replace(/\s+[–—-]\s+[^–—-]{2,70}$/,'').trim();
    if(!t||isDocumentDebris(t)) return '';
    if(!/[.!?]$/.test(t)) t+='.';
    return cleanPoint(t);
  }
  function specialPoint(x){
    const s=clean(x.summary||'');
    if(/horizon europe/i.test(s)&&/introduc(?:e|ing) a new grant scheme/i.test(s)){
      const m=s.match(/introduc(?:e|ing) a new grant scheme\s*[–—-]\s*(?:the\s+)?([^.;]{3,70})/i);
      if(m) return cleanPoint(`Horizon Europe will introduce a new grant scheme, the ${clean(m[1])}.`);
    }
    return '';
  }
  function pointFor(x,topic){
    if(x.signal_note){
      const first=splitSentences(x.signal_note)[0];
      if(first&&first.length>=28&&!BOILER.test(first)&&!isDocumentDebris(first)) return cleanPoint(first);
    }
    const special=specialPoint(x);if(special)return special;
    const sents=splitSentences(x.summary||'');
    let best='',bestScore=-999;
    sents.forEach((s,i)=>{const sc=scoreSentence(s,topic,i);if(sc>bestScore){best=s;bestScore=sc}});
    if(best&&bestScore>=1&&!isDocumentDebris(best)) return cleanPoint(best);
    return titlePoint(x);
  }
  function flatten(data){
    return [
      ...(Array.isArray(data?.strand_a)?data.strand_a:[]),
      ...(Array.isArray(data?.strand_b)?data.strand_b:[]),
      ...(Array.isArray(data?.strand_c)?data.strand_c:[])
    ];
  }
  function buildInsights(data){
    const order=[...TOPICS.map(t=>t.name),OTHER];
    const groups=new Map(order.map(name=>[name,[]]));
    const seen=new Set();
    for(const x of flatten(data)){
      const key=keyFor(x);if(!key||seen.has(key))continue;seen.add(key);
      const topic=topicFor(x);
      const point=pointFor(x,topic);
      if(!point||isDocumentDebris(point)) continue;
      groups.get(topic).push({point,date:dateFor(x),newThisScan:!!x.new_this_scan});
    }
    for(const items of groups.values()) items.sort((a,b)=>(Number(b.newThisScan)-Number(a.newThisScan))||b.date.localeCompare(a.date)||a.point.localeCompare(b.point));
    return order.map(name=>({name,items:groups.get(name)})).filter(g=>g.items.length);
  }
  return {TOPICS,OTHER,topicFor,pointFor,buildInsights,cleanPoint,isDocumentDebris};
});
