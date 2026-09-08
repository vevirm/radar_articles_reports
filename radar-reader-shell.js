// Dedicated Radar reader shell v25. Presentation only; the Radar application script remains unchanged.
(()=>{
  const app=document.getElementById('app');if(!app)return;
  const menu=[
    ['../','Home'],['./','Radar'],['../read/','Read this first'],['../frontier/quick/','Matrix'],
    ['../trends/','Trends and counter-trends'],['../phenomena/','Ongoing phenomena'],['../priorities/','Risks and opportunities'],
    ['../shocks/','External shocks'],['../historical/','Historical evidence'],['../literature/','Sources'],
    ['../briefing/','Topics'],['../glossary/','Glossary'],['../stuff/','Stuff']
  ];
  const links=menu.map(([href,label],i)=>`<a${i===1?' aria-current="page"':''} href="${href}">${label}</a>`).join('');
  const side=document.createElement('aside');side.className='radar-shell-sidebar';side.innerHTML=`<a class="radar-shell-brand" href="../">R&amp;I × Geopolitics Radar</a><nav>${links}</nav><div class="radar-shell-foot">One evidence base, several views.</div>`;document.body.insertBefore(side,document.body.firstChild);
  const head=document.createElement('header');head.className='radar-shell-header';head.innerHTML=`<div class="radar-shell-bar"><a href="../">R&amp;I × Geopolitics Radar</a><button type="button" aria-expanded="false" aria-controls="radarShellDrawer">Menu</button></div><div id="radarShellDrawer" class="radar-shell-drawer" hidden><nav>${links}</nav></div>`;
  const intro=document.createElement('section');intro.className='radar-shell-intro';intro.innerHTML=`<div class="radar-shell-inner"><h1>Radar</h1><p class="radar-shell-question">What has the evidence found, and why does it matter?</p><p class="radar-shell-explain">This is the evidence reader. Each record says what the source found and why it matters for European research and innovation.</p><div id="radarShellFacts" class="radar-shell-facts"><span>Loading live counts…</span></div></div>`;
  app.insertBefore(head,app.firstChild);head.insertAdjacentElement('afterend',intro);document.body.classList.add('radar-shell-site');
  const button=head.querySelector('button'),drawer=head.querySelector('.radar-shell-drawer');button.addEventListener('click',()=>{const open=drawer.hasAttribute('hidden');drawer.toggleAttribute('hidden',!open);button.setAttribute('aria-expanded',String(open));button.textContent=open?'Close':'Menu'});
  const lock=document.createElement('button');lock.className='radar-shell-lock';lock.type='button';lock.textContent='Lock';lock.addEventListener('click',()=>{sessionStorage.removeItem('radarUnlocked');location.reload()});side.appendChild(lock);
  const mobileLock=lock.cloneNode(true);mobileLock.addEventListener('click',()=>{sessionStorage.removeItem('radarUnlocked');location.reload()});drawer.appendChild(mobileLock);
  const clean=v=>String(v??'').replace(/\s+/g,' ').trim(), fmt=n=>Number(n||0).toLocaleString();
  const fact=(n,label,accent=false)=>`<div class="radar-shell-fact${accent?' accent':''}"><strong>${n}</strong><span>${label}</span></div>`;
  const fmtDate=v=>{const d=new Date(v);return Number.isNaN(d.getTime())?clean(v):d.toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'})};
  fetch('../radar.json',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{const rows=[...(d.strand_a||[]),...(d.strand_b||[]),...(d.strand_c||[])],fresh=Number(d.scan_results?.new_items??d.latest_productive_scan?.new_items??0),sources=new Set(rows.map(x=>clean(x.source)).filter(Boolean)).size;document.getElementById('radarShellFacts').innerHTML=fact(fmt(rows.length),'live records')+fact(fmt(fresh),'new last scan',fresh>0)+fact(fmt(sources),'sources')+fact(fmtDate(d.run_completed_at||d.last_updated),'last scan')}).catch(()=>{document.getElementById('radarShellFacts').innerHTML='<span>Live counts unavailable.</span>'});
})();
