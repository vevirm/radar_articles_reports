// Regression compatibility only: Briefing · Radar · Go deeper
// Reader shell v25. Presentation only: it does not alter scanner data or logic.
(()=>{
  const path=location.pathname.replace(/\\/g,'/');
  const pages={
    'radar/':{
      title:'Radar',
      question:'What has the evidence found, and why does it matter?',
      explain:'This is the evidence reader. Each record says what the source found and why it matters for European research and innovation.'
    },
    'read/':{
      title:'Read this first',
      question:'What should I notice before I open the detail?',
      explain:'A short reading of the strongest current issues. Open the Radar from any item when you want the underlying evidence.'
    },
    'frontier/quick/':{
      title:'Matrix',
      question:'Where is Europe gaining or losing ground?',
      explain:'The Matrix places current findings by the kind of R&I capability involved and whether Europe is building strength, paying a cost, relying on others or remaining exposed.'
    },
    'frontier/':{
      title:'Matrix',
      question:'Where is Europe gaining or losing ground?',
      explain:'The detailed evidence view behind the Matrix.'
    },
    'trends/':{
      title:'Trends and counter-trends',
      question:'Which directions are getting stronger, and what is pulling the other way?',
      explain:'A trend needs repeated current evidence from independent sources. The balance numbers show evidence pull, not probability or a forecast.'
    },
    'phenomena/':{
      title:'Ongoing phenomena',
      question:'What keeps happening?',
      explain:'These are recurring developments supported across time rather than one-off events. They stay here when older and current evidence point to the same continuing pattern.'
    },
    'priorities/':{
      title:'Risks and opportunities',
      question:'What could go wrong, or right?',
      explain:'Forward-looking pathways supported by the Radar evidence: risks describe plausible loss of capability or room to act; opportunities describe plausible gains.'
    },
    'shocks/':{
      title:'External shocks',
      question:'What outside event could abruptly change Europe’s R&I position?',
      explain:'These are concrete outside events that could rapidly change access, collaboration, infrastructure or strategic capability. They are not forecasts.'
    },
    'historical/':{
      title:'Historical evidence',
      question:'What did the scanner find before the live Radar timeframe?',
      explain:'Older accepted evidence stays available for comparison and long-run context. It is a separate cumulative scanner pointed at an earlier period.'
    },
    'history/':{
      title:'Historical evidence',
      question:'What did the scanner find before the live Radar timeframe?',
      explain:'Older accepted evidence stays available for comparison and long-run context.'
    },
    'literature/':{
      title:'Sources',
      question:'Where do the findings come from?',
      explain:'A source-oriented view of the publications and organisations behind the Radar.'
    },
    'briefing/':{
      title:'Topics',
      question:'What subjects are appearing across the Radar?',
      explain:'A light thematic reading of the evidence. The publication-level detail remains in the Radar.'
    },
    'glossary/':{
      title:'Glossary',
      question:'What do these words mean?',
      explain:'Plain meanings for the Radar’s own vocabulary and recurring R&I terms.'
    },
    'stuff/':{
      title:'Stuff',
      question:'What has the Radar collected, and how can I check it?',
      explain:'Workbooks, technical material and downloadable data live here so the reader-facing pages can stay light.'
    },
    'explore/':{
      title:'Explore',
      question:'What other ways can I look at the Radar?',
      explain:'A map of the reader views built from the same underlying evidence.'
    }
  };
  let slug=Object.keys(pages).find(s=>path.endsWith('/'+s)||path.endsWith(s));
  if(!slug)return;
  const deep=slug==='frontier/quick/'?2:1;
  const prefix='../'.repeat(deep);
  const page=pages[slug];
  const pageKey=slug.replace(/\/$/,'').replace(/\//g,'-')||'page';
  const technical=slug==='stuff/';
  const host=document.getElementById('app')||document.body;

  const menu=[
    ['', 'Home'],['radar/','Radar'],['read/','Read this first'],['frontier/quick/','Matrix'],
    ['trends/','Trends and counter-trends'],['phenomena/','Ongoing phenomena'],
    ['priorities/','Risks and opportunities'],['shocks/','External shocks'],['historical/','Historical evidence'],
    ['literature/','Sources'],['briefing/','Topics'],['glossary/','Glossary'],['stuff/','Stuff']
  ];
  const hrefFor=target=>target?prefix+target:prefix;
  const activeFor=target=>{
    if(!target)return false;
    if(target==='frontier/quick/')return slug==='frontier/quick/'||slug==='frontier/';
    return slug===target;
  };
  const navLinks=menu.map(([target,label])=>`<a${activeFor(target)?' aria-current="page"':''} href="${hrefFor(target)}">${label}</a>`).join('');

  // Mark only legacy reader furniture. Existing data-generating DOM stays in place.
  [...host.children].filter(el=>el.tagName==='HEADER').forEach(el=>el.classList.add('legacy-site-header'));
  document.querySelectorAll('.core-path,.core-flow,.site-guide,.minimum-read').forEach(el=>el.classList.add('legacy-site-furniture'));

  const sidebar=document.createElement('aside');
  sidebar.className='calm-sidebar';
  sidebar.setAttribute('aria-label','Site map');
  sidebar.innerHTML=`<a class="calm-side-brand" href="${prefix}">R&amp;I × Geopolitics Radar</a><nav>${navLinks}</nav><div class="calm-side-foot"><span>One evidence base, several views.</span></div>`;
  document.body.insertBefore(sidebar,document.body.firstChild);

  const header=document.createElement('header');
  header.className='calm-header';
  header.innerHTML=`<div class="calm-bar"><a class="calm-brand" href="${prefix}">R&amp;I × Geopolitics Radar</a><button class="calm-menu-button" type="button" aria-expanded="false" aria-controls="calmDrawer">Menu</button></div><div id="calmDrawer" class="calm-drawer" hidden><nav aria-label="Site map">${navLinks}</nav></div>`;

  const intro=document.createElement('section');
  intro.className='calm-intro';
  intro.innerHTML=`<div class="calm-intro-inner"><div class="calm-title"><h1>${page.title}</h1><p class="calm-question">${page.question}</p><p class="calm-explain">${page.explain}</p></div><div id="calmFacts" class="calm-facts" aria-live="polite"><span>Loading live counts…</span></div></div>`;
  host.insertBefore(header,host.firstChild);
  header.insertAdjacentElement('afterend',intro);

  document.body.classList.add('calm-site',`page-${pageKey}`,technical?'technical-page':'surface-page');
  if(slug==='read/')document.body.classList.add('reader-calm');

  const menuButton=header.querySelector('.calm-menu-button');
  const drawer=header.querySelector('.calm-drawer');
  menuButton?.addEventListener('click',()=>{
    const open=drawer.hasAttribute('hidden');
    drawer.toggleAttribute('hidden',!open);
    menuButton.setAttribute('aria-expanded',String(open));
    menuButton.textContent=open?'Close':'Menu';
  });

  // Keep a lock control available on gated pages even after the old header is hidden.
  if(document.getElementById('lock')){
    const lock=document.createElement('button');
    lock.type='button';lock.className='calm-lock';lock.textContent='Lock';
    lock.addEventListener('click',()=>{sessionStorage.removeItem('radarUnlocked');location.reload()});
    sidebar.appendChild(lock);
    const mobileLock=lock.cloneNode(true);
    mobileLock.addEventListener('click',()=>{sessionStorage.removeItem('radarUnlocked');location.reload()});
    drawer.appendChild(mobileLock);
  }

  const clean=v=>String(v??'').replace(/\s+/g,' ').trim();
  const fmtDate=v=>{if(!v)return '';const d=new Date(v);return Number.isNaN(d.getTime())?clean(v):d.toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'})};
  const fmt=n=>Number(n||0).toLocaleString();
  const fact=(n,label,accent=false)=>`<div class="calm-fact${accent?' accent':''}"><strong>${n}</strong><span>${label}</span></div>`;
  const sourceCount=rows=>new Set(rows.map(x=>clean(x?.source)).filter(Boolean)).size;
  async function loadFacts(){
    const box=document.getElementById('calmFacts');if(!box)return;
    try{
      if(slug==='historical/'||slug==='history/'){
        const res=await fetch(prefix+'historical/historical.json',{cache:'no-store'});if(!res.ok)throw new Error('history');
        const d=await res.json(), rows=d.items||[], fresh=Number(d.last_scan?.new_items||0);
        box.innerHTML=fact(fmt(rows.length),'works found')+fact(fmt(fresh),'new last scan',fresh>0)+fact(fmt(sourceCount(rows)),'sources')+fact(fmtDate(d.last_updated),'last scan');
      }else{
        const res=await fetch(prefix+'radar.json',{cache:'no-store'});if(!res.ok)throw new Error('radar');
        const d=await res.json(), rows=[...(d.strand_a||[]),...(d.strand_b||[]),...(d.strand_c||[])], fresh=Number(d.scan_results?.new_items??d.latest_productive_scan?.new_items??0);
        box.innerHTML=fact(fmt(rows.length),'live records')+fact(fmt(fresh),'new last scan',fresh>0)+fact(fmt(sourceCount(rows)),'sources')+fact(fmtDate(d.run_completed_at||d.last_updated),'last scan');
      }
    }catch(_){box.innerHTML='<span>Live counts unavailable.</span>'}
  }
  loadFacts();

  if(document.querySelector('main')){
    const top=document.createElement('button');top.type='button';top.className='calm-top';top.textContent='Top';
    top.addEventListener('click',()=>scrollTo({top:0,behavior:'smooth'}));document.body.appendChild(top);
    const sync=()=>top.classList.toggle('show',scrollY>1000);addEventListener('scroll',sync,{passive:true});sync();
  }
})();
