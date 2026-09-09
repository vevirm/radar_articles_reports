(()=>{
  const genericTitle=/^(download|open|view|pdf|document|publication|read more)$/i;
  const stripDownloadNoise=(value)=>{
    let s=String(value||'').replace(/\s+/g,' ').trim();
    s=s.replace(/^download\s*(?:\d+)?\s*[.\-–—:]*\s*/i,'');
    s=s.replace(/^pdf\s*(?:download)?\s*[.\-–—:]*\s*/i,'');
    s=s.replace(/\s+[\-–—:]?\s*(?:download|pdf)\s*[.!?]*$/i,'');
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
      card.querySelectorAll('.whatline,.signal-what').forEach(el=>{
        cleanTextTail(el);
        const htxt=stripDownloadNoise((card.querySelector('.claim-title')?.textContent||'')).toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
        const etxt=stripDownloadNoise((el.textContent||'')).toLowerCase().replace(/^(?:what|what happened)\s*/,'').replace(/[^a-z0-9]+/g,' ').trim();
        if(htxt&&etxt&&(htxt===etxt||htxt.includes(etxt)||etxt.includes(htxt))) el.remove();
      });
      card.querySelectorAll('.info-button').forEach(b=>{if(b.textContent.trim()==='More info')b.textContent='Evidence';});
      card.querySelectorAll('.publication-link').forEach(a=>{if(/^(Open publication|Open source evidence)/i.test(a.textContent.trim()))a.textContent='Source';});
      card.querySelectorAll('.biblio summary').forEach(x=>{if(x.textContent.trim()==='Source information')x.textContent='Details';});
      // The WHAT/WHY pair is part of the reader contract, so the label stays.
      // It is only normalised to sentence case, which reads better at label size.
      card.querySelectorAll('.whatline strong,.whyline strong,.signal-what strong').forEach(x=>{
        const m=/^(WHAT|WHY):?$/i.exec(x.textContent.trim());
        if(m){const t=m[1].toLowerCase()==='what'?'What':'Why';if(x.textContent!==t)x.textContent=t;}
      });
      card.querySelectorAll('.visible-source strong').forEach(x=>{if(/^Source:?$/i.test(x.textContent.trim()))x.remove();});
      const sourceBox=card.querySelector('.visible-source');
      if(sourceBox){
        [...sourceBox.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).forEach(n=>{n.textContent=(n.textContent||'').replace(/\s*[·•]\s*[^·•]+$/,'').trim();});
      }
    });
  };
  const observer=new MutationObserver(tidyRadar);
  observer.observe(document.documentElement,{childList:true,subtree:true});
  tidyRadar();
  const s=document.createElement('script');
  s.src='../site-shell.js?v=28';
  s.async=false;
  document.body.appendChild(s);
})();
