(()=>{
  const genericTitle=/^(download|open|view|pdf|document|publication|read more)$/i;
  const tidyGenericHeadings=()=>{
    document.querySelectorAll('.page-radar .item').forEach(card=>{
      const h=card.querySelector('.claim-title');
      if(!h)return;
      const link=h.querySelector('a');
      const target=link||h;
      const title=(target.textContent||'').trim();
      if(!genericTitle.test(title))return;
      const what=card.querySelector('.whatline,.signal-what');
      if(!what)return;
      const replacement=(what.textContent||'').replace(/^WHAT:\s*/i,'').trim();
      if(replacement)target.textContent=replacement;
    });
  };
  const observer=new MutationObserver(tidyGenericHeadings);
  observer.observe(document.documentElement,{childList:true,subtree:true});
  tidyGenericHeadings();
  const s=document.createElement('script');
  s.src='../site-shell.js?v=26';
  s.async=false;
  document.body.appendChild(s);
})();
