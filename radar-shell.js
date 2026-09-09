(()=>{
  const genericTitle=/^(download|open|view|pdf|document|publication|read more)$/i;
  const stripDownloadNoise=(value)=>{
    let s=String(value||'').replace(/\s+/g,' ').trim();
    s=s.replace(/^download\s*(?:\d+)?\s*[.\-–—:]*\s*/i,'');
    s=s.replace(/\s+[\-–—:]?\s*download\s*[.!?]*$/i,'');
    s=s.replace(/^download\s*[\-–—:]?\s*/i,'').trim();
    return s;
  };
  const cleanTextTail=(el)=>{
    if(!el)return;
    [...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).forEach(n=>{
      const before=n.textContent||'';
      const after=stripDownloadNoise(before);
      if(after!==before.trim()) n.textContent=(before.startsWith(' ')?' ':'')+after;
    });
  };
  const tidyRadar=()=>{
    document.querySelectorAll('.page-radar .item').forEach(card=>{
      const h=card.querySelector('.claim-title');
      if(h){
        const link=h.querySelector('a');
        const target=link||h;
        const original=(target.textContent||'').trim();
        let title=stripDownloadNoise(original);
        if(genericTitle.test(title)){
          const what=card.querySelector('.whatline,.signal-what');
          title=stripDownloadNoise((what?.textContent||'').replace(/^(?:WHAT:|What happened:)\s*/i,''));
        }
        if(title&&title!==original)target.textContent=title;
      }
      card.querySelectorAll('.biblio-title').forEach(el=>{
        const before=(el.textContent||'').trim(),after=stripDownloadNoise(before);
        if(after&&after!==before)el.textContent=after;
      });
      card.querySelectorAll('.whatline,.signal-what').forEach(cleanTextTail);
      card.querySelectorAll('.info-button').forEach(b=>{if(b.textContent.trim()==='More info')b.textContent='Evidence';});
      card.querySelectorAll('.publication-link').forEach(a=>{if(/^(Open publication|Open source evidence)/i.test(a.textContent.trim()))a.textContent='Source ↗';});
      card.querySelectorAll('.biblio summary').forEach(x=>{if(x.textContent.trim()==='Source information')x.textContent='Details';});
    });
  };
  const observer=new MutationObserver(tidyRadar);
  observer.observe(document.documentElement,{childList:true,subtree:true});
  tidyRadar();
  const s=document.createElement('script');
  s.src='../site-shell.js?v=26';
  s.async=false;
  document.body.appendChild(s);
})();
