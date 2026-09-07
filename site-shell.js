// Regression compatibility only: Briefing · Radar · Go deeper
// Shared reader shell. Keeps normal pages simple; technical detail lives in Radar and Stuff.
(()=>{
  const path=location.pathname.replace(/\\/g,'/');
  const meta=[
    ['read/','Read this first','A quick view of what matters.'],
    ['frontier/quick/','Matrix','Where Europe looks strong, weak or dependent.'],
    ['trends/','Trends','What looks stronger, weaker or contested.'],
    ['phenomena/','Ongoing patterns','What keeps happening.'],
    ['priorities/','Risks & opportunities','What could go wrong — or right.'],
    ['shocks/','External shocks','Big outside events that could change things fast.'],
    ['historical/','History','Older findings for comparison.'],
    ['literature/','Sources','The publications and organisations behind the Radar.'],
    ['glossary/','Glossary','Plain meanings of the words used here.'],
    ['stuff/','Stuff','Download the full technical data.'],
    ['briefing/','Evidence by topic','Findings grouped by topic.'],
    ['explore/','More','Choose another view.']
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
