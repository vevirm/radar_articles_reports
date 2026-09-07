// Regression compatibility only: Go deeper
(()=>{
  const path=location.pathname.replace(/\\/g,'/');
  const meta=[
    ['read/','Read this first','The short version of what matters now.'],
    ['frontier/quick/','Matrix','Where Europe is strong, weak or dependent.'],
    ['trends/','Trends','What is getting stronger or weaker.'],
    ['phenomena/','Ongoing patterns','What keeps coming back.'],
    ['priorities/','Risks & opportunities','What could go wrong or go well.'],
    ['shocks/','External shocks','What a big outside event could do.'],
    ['historical/','History','Older evidence for comparison.'],
    ['literature/','Sources','Where the evidence comes from.'],
    ['glossary/','Glossary','What the words mean.'],
    ['stuff/','Stuff','Technical methods, files and audit detail.'],
    ['briefing/','Evidence by topic','What we found, grouped by topic.'],
    ['explore/','More','Choose what you want to look at.']
  ];
  let found=meta.find(([slug])=>path.endsWith('/'+slug)||path.endsWith(slug));
  if(path.endsWith('/frontier/')) found=['frontier/','Matrix · full evidence','The detailed evidence behind the Matrix.'];
  if(!found)return;
  const deep=path.endsWith('/frontier/quick/')?2:1, prefix='../'.repeat(deep);
  const [slug,title,purpose]=found;const deeper=!['read/','radar/','explore/'].includes(slug);
  const host=document.getElementById('app')||document.body;
  const legacy=[...host.children].find(el=>el.tagName==='HEADER');if(legacy)legacy.classList.add('legacy-site-header');
  document.querySelectorAll('.core-path,.site-guide,.minimum-read').forEach(el=>el.classList.add('legacy-site-furniture'));
  const header=document.createElement('header');header.className='calm-header';header.innerHTML=`<div class="calm-bar"><a class="calm-brand" href="${prefix}">R&amp;I × Geopolitics</a><nav aria-label="Main navigation"><a ${slug==='read/'?'aria-current="page"':''} href="${prefix}read/">Briefing</a><a ${slug==='radar/'?'aria-current="page"':''} href="${prefix}radar/">Radar</a><a ${(slug==='explore/'||deeper)?'aria-current="page"':''} href="${prefix}explore/">Go deeper</a></nav></div>`;
  const intro=document.createElement('section');intro.className='calm-intro';intro.innerHTML=`<div class="calm-intro-inner"><h1>${title}</h1><p>${purpose}</p></div>`;
  host.insertBefore(header,host.firstChild);header.insertAdjacentElement('afterend',intro);document.body.classList.add('calm-site');if(slug==='read/')document.body.classList.add('reader-calm');
  const method=document.querySelector('main .method');if(method&&!method.closest('.depth-fold')){const fold=document.createElement('details');fold.className='depth-fold';fold.innerHTML='<summary>How this page works</summary>';method.parentNode.insertBefore(fold,method);fold.appendChild(method)}
  if(document.querySelector('main')){const top=document.createElement('button');top.type='button';top.className='calm-top';top.textContent='Top';top.addEventListener('click',()=>scrollTo({top:0,behavior:'smooth'}));document.body.appendChild(top);const sync=()=>top.classList.toggle('show',scrollY>1000);addEventListener('scroll',sync,{passive:true});sync()}
})();
