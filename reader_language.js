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
    [/\/2035\/?$/,'future'],
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
      const raw=node.nodeValue||'',key=normalise(raw),replacement=map.get(key);
      if(!replacement)return;
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
