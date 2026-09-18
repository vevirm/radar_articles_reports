(()=>{
  'use strict';
  const path=location.pathname.replace(/\\/g,'/');
  const ROUTES=[
    [/\/frontier\/quick\/?$/,'frontier-quick'],
    [/\/frontier\/?$/,'frontier'],
    [/\/trends\/?$/,'trends'],
    [/\/phenomena\/?$/,'phenomena'],
    [/\/priorities\/?$/,'priorities'],
    [/\/shocks\/variants(?:\.html)?\/?$/,'shocks-variants'],
    [/\/shocks\/?$/,'shocks'],
    [/\/read\/?$/,'read'],
    [/\/briefing\/?$/,'briefing'],
    [/\/glossary\/?$/,'glossary'],
    [/\/explore\/?$/,'explore'],
    [/\/literature\/?$/,'literature']
  ];
  const excluded=/\/(?:radar|stuff|historical|history)\/?$/;
  if(excluded.test(path))return;
  let route=(ROUTES.find(([re])=>re.test(path))||[])[1]||'';
  if(!route){
    // The repository root is the Start page.  Do not guess for arbitrary files.
    if(/\/$/.test(path)&&!/\/[^/]+\/(?:[^/]+)\/$/.test(path))route='start';
    else return;
  }

  const script=document.currentScript;
  if(!script?.src)return;
  const dataUrl=new URL('reader_language/approved.json',script.src);
  const normalise=v=>String(v??'').replace(/\s+/g,' ').trim();
  const SKIP=new Set(['SCRIPT','STYLE','NOSCRIPT','TEXTAREA','INPUT','SELECT','OPTION','CODE','PRE']);

  // Presentation-only cleanup for recurring machine-generated phrasing. These rules are
  // intentionally narrow and preserve direction, modality, counts and named entities.
  function friendlyText(value){
    let s=normalise(value);
    if(!s)return s;
    s=s.replace(/^Current evidence is adding or widening (.+?)(?: as a whole)? through (.+)\.$/i,
      (_,topic,means)=>`Evidence points to growth in ${topic}, supported by ${means}.`);
    s=s.replace(/^Current evidence (?:is making|shows) (.+?)(?: as a whole)? (?:becoming )?more conditional or constrained through (.+)\.$/i,
      (_,topic,means)=>`${topic.replace(/^./,c=>c.toUpperCase())} is facing tighter conditions, including ${means}.`);
    s=s.replace(/^Current evidence shows (.+?) expanding through (.+)\.$/i,
      (_,topic,means)=>`${topic.replace(/^./,c=>c.toUpperCase())} is expanding, supported by ${means}.`);
    s=s.replace(/\bas a whole\b/gi,'');
    s=s.replace(/\bdocumented constraints\b/gi,'identified constraints');
    s=s.replace(/\s{2,}/g,' ').replace(/\s+([,.;:!?])/g,'$1').trim();

    const exact=new Map([
      ['Current evidence has to pull in both directions.','A trend appears here only when there is credible evidence in both directions.'],
      ['A one-way movement stays a developing pattern until a credible counter-pull appears.','Movement in only one direction remains a developing pattern until credible evidence appears on the other side.'],
      ["The wording above is the Radar's synthesis. The statements below are the narrower claims attributed to the sources.",'The summary above combines the evidence. The source statements below show what each source says directly.'],
      ["The phenomenon above is the Radar's synthesis. Current source evidence and historical context are kept separate below.",'The summary above combines the evidence. Current sources and older context are shown separately below.'],
      ['What is pulling:','Why the balance looks this way:'],
      ['What would move the balance:','What could change the balance:'],
      ['Current source evidence:','Current sources:'],
      ['Source evidence that could weaken the finding:','Evidence that points the other way:'],
      ['What the sources state:','What the sources say:'],
      ['Speaks for the shock','Evidence supporting the scenario'],
      ['Pushes against it','Evidence that could soften the scenario'],
      ['Plainly:','In short:'],
      ['Net assessment:','Overall assessment:']
    ]);
    return exact.get(s)||s;
  }

  fetch(dataUrl,{cache:'no-store'}).then(r=>r.ok?r.json():null).then(data=>{
    const items=data&&data.items&&typeof data.items==='object'?Object.values(data.items):[];
    const map=new Map();
    for(const item of items){
      if(!item||item.status!=='rewrite')continue;
      const routes=Array.isArray(item.routes)?item.routes:[];
      if(routes.length&&!routes.includes(route))continue;
      const source=normalise(item.source),replacement=normalise(item.replacement);
      const matches=Array.isArray(item.matches)&&item.matches.length?item.matches:[source];
      if(source&&replacement&&source!==replacement){
        for(const match of matches){const key=normalise(match);if(key)map.set(key,replacement)}
      }
    }
    if(!map.size)return;

    function applyNode(node){
      if(!node||node.nodeType!==Node.TEXT_NODE||!node.parentElement)return;
      if(SKIP.has(node.parentElement.tagName))return;
      const raw=node.nodeValue||'',key=normalise(raw);
      const exact=map.get(key);
      const replacement=friendlyText(exact||key);
      if(!replacement||replacement===key)return;
      const lead=(raw.match(/^\s*/)||[''])[0],trail=(raw.match(/\s*$/)||[''])[0];
      node.nodeValue=lead+replacement+trail;
    }
    function applyTree(root){
      if(!root)return;
      if(root.nodeType===Node.TEXT_NODE){applyNode(root);return;}
      const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
      let n;while((n=walker.nextNode()))applyNode(n);
    }
    applyTree(document.body);
    const observer=new MutationObserver(muts=>{
      for(const m of muts){
        if(m.type==='characterData')applyNode(m.target);
        for(const n of m.addedNodes||[])applyTree(n);
      }
    });
    observer.observe(document.body,{subtree:true,childList:true,characterData:true});
  }).catch(()=>{});
})();
