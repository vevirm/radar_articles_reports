// Regression compatibility only: Briefing · Radar · Go deeper
// Shared reader shell. Normal pages explain findings; Radar and Stuff hold technical detail.
(()=>{
  const path=location.pathname.replace(/\\/g,'/');
  const meta=[
    ['read/','Read At Least This','A compact map of the phenomena and their parts.'],
    ['frontier/quick/','Matrix','Where Europe looks strong, weak or dependent.'],
    ['trends/','Trends & Counter-Trends','Opposing institutional pulls acting on the same underlying object.'],
    ['phenomena/','Ongoing Phenomena','Developments that persist, reconnect or change shape over time.'],
    ['priorities/','Risks & Opportunities','Consequences supported by the current evidence base.'],
    ['shocks/','External Shocks','Potential disruptions, ordered from more obvious to more inferential.'],
    ['historical/','Earlier Findings','Findings published before the Radar started scanning.'],
    ['history/','Earlier Findings','Findings published before the Radar started scanning.'],
    ['literature/','Sources','Where the findings come from.'],
    ['glossary/','Glossary','Plain meanings.'],
    ['stuff/','Stuff','Full technical data.'],
    ['briefing/','Topics','What the Radar is seeing, grouped by subject.'],
    ['explore/','More','Other ways to look at the Radar.']
  ];
  let found=meta.find(([slug])=>path.endsWith('/'+slug)||path.endsWith(slug));
  if(path.endsWith('/frontier/')) found=['frontier/','Matrix','The detailed evidence behind the Matrix.'];
  if(!found)return;
  if(!document.querySelector('link[data-v25-visual]')){const css=document.createElement('link');css.rel='stylesheet';css.href='../'.repeat(path.endsWith('/frontier/quick/')?2:1)+'visual-v25.css?v=25.0';css.dataset.v25Visual='1';document.head.appendChild(css)}
  const deep=path.endsWith('/frontier/quick/')?2:1, prefix='../'.repeat(deep);
  const [slug,title,purpose]=found;
  const pageKey=slug.replace(/\/$/,'').replace(/\//g,'-')||'page';
  const technical=slug==='stuff/';
  const host=document.getElementById('app')||document.body;
  const legacy=[...host.children].find(el=>el.tagName==='HEADER');if(legacy)legacy.classList.add('legacy-site-header');
  document.querySelectorAll('.core-path,.core-flow,.site-guide,.minimum-read').forEach(el=>el.classList.add('legacy-site-furniture'));

  const menu=[
    ['', 'Home',''],
    ['radar/','Radar',''],
    ['historical/','Earlier Findings',''],
    ['literature/','Sources',''],
    ['briefing/','Topics',''],
    ['read/','Read At Least This','menu-group-start'],
    ['frontier/quick/','Matrix',''],
    ['trends/','Trends & Counter-Trends',''],
    ['phenomena/','Ongoing Phenomena',''],
    ['priorities/','Risks & Opportunities',''],
    ['shocks/','External Shocks',''],
    ['glossary/','Glossary','menu-group-final'],
    ['stuff/','Stuff','']
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
  sidebar.innerHTML=`<a class="calm-side-brand" href="${prefix}">R&amp;I × Geopolitics Radar</a><nav>${menu.map(([target,label,cls])=>`<a${cls?` class="${cls}"`:''}${activeFor(target)?' aria-current="page"':''} href="${hrefFor(target)}">${label}</a>`).join('')}</nav>`;
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
  if(['trends/','phenomena/','priorities/','shocks/'].includes(slug))document.body.classList.add('obviousness-ordered');
  if(document.querySelector('main')){
    const top=document.createElement('button');top.type='button';top.className='calm-top';top.textContent='Top';
    top.addEventListener('click',()=>scrollTo({top:0,behavior:'smooth'}));document.body.appendChild(top);
    const sync=()=>top.classList.toggle('show',scrollY>1200);addEventListener('scroll',sync,{passive:true});sync();
  }
})();
