(()=>{
  const PAGES=[
    ['read/','Read at least this','New here? Start here. The shortest route through what the evidence says.'],
    ['radar/','Radar','Browse the evidence. Search and filter what the scanner has found.'],
    ['frontier/quick/','Matrix','See where change strengthens Europe, creates costs, leaves reliance, or weakens capability.'],
    ['trends/','Trends','See where current evidence is pulling in opposite directions.'],
    ['phenomena/','Ongoing phenomena','Follow issues that keep resurfacing across current and older evidence.'],
    ['priorities/','Risks & opportunities','See the consequences the current evidence makes most important to watch.'],
    ['shocks/','External shocks','Test disruptive outside events against the evidence already in the Radar.'],
    ['historical/','Historical','Look at older evidence that helps explain the current position.'],
    ['literature/','Sources','Browse the publications and institutions behind the current evidence.'],
    ['glossary/','Glossary','Translate technical terms used across the Radar into plain language.'],
    ['stuff/','Stuff','Open the technical evidence, methods and audit material behind the reader pages.']
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
    'read/':['Read at least this','New here? Start here. Eight topic maps show the shortest useful reading of the current evidence.'],
    'radar/':['Radar','Browse the evidence itself. Search by topic, inspect the three evidence layers, and open the sources behind each finding.'],
    'frontier/quick/':['Matrix','See where change happens and whether it strengthens European control, creates costs, leaves reliance, or weakens capability.'],
    'trends/':['Trends','Compare directions that have enough independent current evidence on both sides.'],
    'phenomena/':['Ongoing phenomena','See which underlying issues keep appearing in both older and current evidence.'],
    'priorities/':['Risks & opportunities','Turn repeated evidence into a short list of consequences worth watching.'],
    'shocks/':['External shocks','Stress-test the current evidence against disruptive events outside the research system.'],
    'historical/':['Historical evidence','Use older evidence as context without mixing it into the live Radar.'],
    'literature/':['Sources','Browse the publications and institutions that support the Radar.'],
    'glossary/':['Glossary','Plain-language meanings for terms used across the site.'],
    'stuff/':['Stuff','Technical depth lives here: publications, methods, scanner grammar and audit material.'],
    'briefing/':['Evidence by topic','See the newest Radar findings grouped into plain-language themes.'],
    'frontier/full/':['Matrix · full evidence','Inspect the full evidence behind each Matrix position.']
  };
  const [title,purpose]=pageMeta[view||current]||['Radar','Evidence on research, innovation and geopolitics.'];

  const app=document.getElementById('app');
  const host=app||document.body;
  const legacy=[...host.children].find(el=>el.tagName==='HEADER');
  if(legacy) legacy.classList.add('legacy-site-header');

  const header=document.createElement('header');
  header.className='site-header';
  const links=PAGES.map(([slug,label])=>{
    const href=prefix+slug;
    const cls=slug==='read/'?' class="site-start-here"':'';
    const cur=slug===current?' aria-current="page"':'';
    return `<a${cls}${cur} href="${href}">${label}</a>`;
  }).join('');
  header.innerHTML=`<div class="site-header-inner"><a class="site-home-link" href="${prefix}">Research &amp; Innovation × Geopolitics Radar</a><div class="site-page-kicker">This page</div><h1 class="site-page-title">${title}</h1><p class="site-page-purpose">${purpose}</p><nav class="site-nav" aria-label="All sections">${links}</nav></div>`;

  if(document.getElementById('gate')){
    const lock=document.createElement('button');
    lock.type='button';lock.className='site-lock';lock.textContent='Lock';
    lock.addEventListener('click',()=>{sessionStorage.removeItem('radarUnlocked');location.reload()});
    header.appendChild(lock);
  }
  host.insertBefore(header,host.firstChild);
  document.body.classList.add('reader-reformed');

  const toolbar=document.querySelector('.toolbar');
  const main=document.querySelector('main');
  if(main){
    const returns=document.createElement('div');
    returns.className='page-return';
    returns.setAttribute('aria-label','Page navigation');
    if(toolbar){
      const filters=document.createElement('button');filters.type='button';filters.textContent='Filters';
      filters.addEventListener('click',()=>toolbar.scrollIntoView({behavior:'smooth',block:'start'}));
      returns.appendChild(filters);
    }
    const top=document.createElement('button');top.type='button';top.textContent='Top';
    top.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
    returns.appendChild(top);
    document.body.appendChild(returns);
  }
})();
