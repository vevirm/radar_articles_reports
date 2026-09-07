(()=>{
  const PAGES=[
    ['read/','Read at least this','The shortest useful reading of what matters now.'],
    ['radar/','Radar','Search the current evidence and open the sources behind it.'],
    ['frontier/quick/','Matrix','See where change strengthens Europe, creates costs, leaves reliance, or weakens capability.'],
    ['trends/','Trends','See which directions are gaining or losing support in the current evidence.'],
    ['phenomena/','Ongoing phenomena','See the issues and patterns that keep returning across time.'],
    ['priorities/','Risks & opportunities','See the consequences the evidence makes most important to watch.'],
    ['shocks/','External shocks','Stress-test the evidence against disruptive events outside the research system.'],
    ['historical/','Historical','Use older evidence as context without mixing it into the live Radar.'],
    ['literature/','Sources','Browse the publications and institutions behind the current evidence.'],
    ['glossary/','Glossary','Plain-language meanings for terms used across the site.'],
    ['stuff/','Stuff','Technical depth: methods, files and audit material.']
  ];
  const pathname=location.pathname.replace(/\\/g,'/');
  let current=''; let view='';
  for(const [slug] of PAGES){if(pathname.endsWith('/'+slug)||pathname.endsWith(slug)){current=slug;view=slug;break}}
  if(pathname.endsWith('/frontier/')){current='frontier/quick/';view='frontier/full/'}
  if(pathname.endsWith('/briefing/')){current='read/';view='briefing/'}
  if(pathname.endsWith('/history/')){current='historical/';view='historical/'}
  if(!current) return;

  const deep=pathname.endsWith('/frontier/quick/')?2:1;
  const prefix='../'.repeat(deep);
  const pageMeta={
    'read/':['Read at least this','Eight things worth knowing before you go deeper.'],
    'radar/':['Radar','Search the current evidence. Open detail only when you need it.'],
    'frontier/quick/':['Matrix','A quick view of where Europe gains control, carries costs, remains reliant, or loses ground.'],
    'trends/':['Trends','The strongest competing directions in the current evidence.'],
    'phenomena/':['Ongoing phenomena','Patterns that keep returning, and the ones whose shape is changing.'],
    'priorities/':['Risks & opportunities','The clearest downside and upside pathways supported by current evidence.'],
    'shocks/':['External shocks','What the evidence suggests could break, bend or hold under outside disruption.'],
    'historical/':['Historical evidence','Older evidence for context, kept separate from the live Radar.'],
    'literature/':['Sources','The publications and institutions behind the Radar.'],
    'glossary/':['Glossary','Plain language for terms used across the site.'],
    'stuff/':['Stuff','Methods, files and technical audit material.'],
    'briefing/':['Evidence by topic','The newest evidence grouped into plain-language themes.'],
    'frontier/full/':['Matrix · full evidence','The detailed evidence behind each Matrix position.']
  };
  const [title,purpose]=pageMeta[view||current]||['Radar','Evidence on research, innovation and geopolitics.'];
  const app=document.getElementById('app');
  const host=app||document.body;
  const legacy=[...host.children].find(el=>el.tagName==='HEADER');
  if(legacy) legacy.classList.add('legacy-site-header');

  const secondary=PAGES.filter(([slug])=>!['read/','radar/'].includes(slug)).map(([slug,label,desc])=>{
    const cur=slug===current?' aria-current="page"':'';
    return `<a${cur} href="${prefix+slug}"><strong>${label}</strong><span>${desc}</span></a>`;
  }).join('');
  const header=document.createElement('header');
  header.className='site-header';
  header.innerHTML=`
    <div class="site-bar">
      <a class="site-home-link" href="${prefix}">R&amp;I × Geopolitics Radar</a>
      <nav class="site-primary" aria-label="Primary navigation">
        <a class="site-start-here" ${current==='read/'?'aria-current="page"':''} href="${prefix}read/">Read at least this</a>
        <a ${current==='radar/'?'aria-current="page"':''} href="${prefix}radar/">Radar</a>
        <details class="site-more"><summary>Explore</summary><div class="site-menu">${secondary}</div></details>
      </nav>
    </div>`;
  if(document.getElementById('gate')){
    const lock=document.createElement('button');
    lock.type='button';lock.className='site-lock';lock.textContent='Lock';
    lock.addEventListener('click',()=>{sessionStorage.removeItem('radarUnlocked');location.reload()});
    header.querySelector('.site-bar').appendChild(lock);
  }
  const intro=document.createElement('section');
  intro.className='site-intro';
  intro.innerHTML=`<div class="site-intro-inner"><h1>${title}</h1><p>${purpose}</p></div>`;
  host.insertBefore(header,host.firstChild);
  header.insertAdjacentElement('afterend',intro);
  document.body.classList.add('reader-reformed','reader-calm');

  // Put methodological explanation behind one calm disclosure instead of leading with it.
  const method=document.querySelector('main .method');
  if(method && !method.closest('.depth-fold')){
    const fold=document.createElement('details');
    fold.className='depth-fold';
    fold.innerHTML='<summary>How this page works</summary>';
    method.parentNode.insertBefore(fold,method);
    fold.appendChild(method);
  }

  // One unobtrusive return control, only after the reader has actually gone deep.
  const main=document.querySelector('main');
  if(main){
    const top=document.createElement('button');
    top.type='button';top.className='site-top-button';top.textContent='↑ Top';
    top.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
    document.body.appendChild(top);
    const sync=()=>top.classList.toggle('show',window.scrollY>900);
    addEventListener('scroll',sync,{passive:true});sync();
  }

  // Close the Explore menu after a destination is chosen and when Escape is pressed.
  const menu=header.querySelector('.site-more');
  menu?.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>menu.removeAttribute('open')));
  addEventListener('keydown',e=>{if(e.key==='Escape')menu?.removeAttribute('open')});
})();
