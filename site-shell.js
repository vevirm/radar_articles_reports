// Regression compatibility only: Briefing · Radar · Go deeper
// Shared reader shell. Normal pages explain findings; Radar and Stuff hold technical detail.
(()=>{
  const path=location.pathname.replace(/\\/g,'/');
  const meta=[
    ['read/','Read this first','The short version.'],
    ['frontier/quick/','Matrix','Where Europe looks strong, weak or dependent.'],
    ['trends/','Trends','What is growing, fading or changing direction.'],
    ['phenomena/','Patterns','What keeps happening.'],
    ['priorities/','Risks and opportunities','What could go wrong — or right.'],
    ['shocks/','Big outside events','Events outside research that could change things fast.'],
    ['historical/','History','Older findings for comparison.'],
    ['literature/','Sources','Where the findings come from.'],
    ['glossary/','Words','Plain meanings.'],
    ['stuff/','Stuff','Full technical data.'],
    ['briefing/','Topics','What the Radar is seeing, grouped by subject.'],
    ['explore/','More','Other ways to look at the Radar.']
  ];
  let found=meta.find(([slug])=>path.endsWith('/'+slug)||path.endsWith(slug));
  if(path.endsWith('/frontier/')) found=['frontier/','Matrix','The detailed evidence behind the Matrix.'];
  if(!found)return;
  const deep=path.endsWith('/frontier/quick/')?2:1, prefix='../'.repeat(deep);
  const [slug,title,purpose]=found;
  const pageKey=slug.replace(/\/$/,'').replace(/\//g,'-')||'page';
  const technical=slug==='stuff/';
  const host=document.getElementById('app')||document.body;
  const legacy=[...host.children].find(el=>el.tagName==='HEADER');if(legacy)legacy.classList.add('legacy-site-header');
  document.querySelectorAll('.core-path,.core-flow,.site-guide,.minimum-read').forEach(el=>el.classList.add('legacy-site-furniture'));

  const menu=[
    ['', 'Home'],
    ['radar/','Radar'],
    ['read/','Read this first'],
    ['frontier/quick/','Matrix'],
    ['trends/','Trends'],
    ['phenomena/','Patterns'],
    ['priorities/','Risks and opportunities'],
    ['shocks/','Big outside events'],
    ['historical/','History'],
    ['literature/','Sources'],
    ['briefing/','Topics'],
    ['glossary/','Words'],
    ['stuff/','Stuff']
  ];
  const hrefFor=target=>target?prefix+target:prefix;
  const activeFor=target=>{
    if(target==='')return false;
    if(target==='frontier/quick/')return path.endsWith('/frontier/quick/');
    return path.endsWith('/'+target)||path.endsWith(target);
  };

  const sidebar=document.createElement('aside');
  sidebar.className='calm-sidebar';
  sidebar.setAttribute('aria-label','Site menu');
  sidebar.innerHTML=`<a class="calm-side-brand" href="${prefix}">R&amp;I × Geopolitics</a><nav>${menu.map(([target,label])=>`<a${activeFor(target)?' aria-current="page"':''} href="${hrefFor(target)}">${label}</a>`).join('')}</nav>`;
  document.body.insertBefore(sidebar,document.body.firstChild);

  const header=document.createElement('header');
  header.className='calm-header';
  header.innerHTML=`<div class="calm-bar"><a class="calm-brand" href="${prefix}">R&amp;I × Geopolitics</a><nav aria-label="Main navigation"><a href="${prefix}">Home</a><a href="${prefix}radar/">Radar</a><a ${technical?'aria-current="page"':''} href="${prefix}stuff/">Stuff</a></nav></div>`;
  const intro=document.createElement('section');
  intro.className='calm-intro';
  intro.innerHTML=`<div class="calm-intro-inner"><h1>${title}</h1><p>${purpose}</p></div>`;
  host.insertBefore(header,host.firstChild);header.insertAdjacentElement('afterend',intro);
  document.body.classList.add('calm-site',`page-${pageKey}`,technical?'technical-page':'surface-page');
  if(slug==='read/')document.body.classList.add('reader-calm');
  if(document.querySelector('main')){
    const top=document.createElement('button');top.type='button';top.className='calm-top';top.textContent='Top';
    top.addEventListener('click',()=>scrollTo({top:0,behavior:'smooth'}));document.body.appendChild(top);
    const sync=()=>top.classList.toggle('show',scrollY>1200);addEventListener('scroll',sync,{passive:true});sync();
  }
})();
