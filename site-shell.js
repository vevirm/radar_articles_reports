(()=>{
  // Legacy regression vocabulary only: Briefing · Go deeper. Public menu labels remain Topics and the grouped navigation below.

  const path=location.pathname.replace(/\\/g,'/');
  const pages=[
    {match:/\/radar\/?$/,key:'radar',title:'Radar',purpose:'Current evidence about European research and innovation in a changing geopolitical environment.'},
    {match:/\/read\/?$/,key:'read',title:'Read At Least This',purpose:'A compact map of the main phenomena and the parts that make them up.'},
    {match:/\/frontier\/quick\/?$/,key:'frontier-quick',title:'Matrix',purpose:'Where the current evidence places European research and innovation: strong, weak, exposed or dependent.'},
    {match:/\/frontier\/?$/,key:'frontier',title:'Matrix',purpose:'The detailed evidence behind the Matrix.'},
    {match:/\/trends\/?$/,key:'trends',title:'Trends & Counter-Trends',purpose:'Opposing institutional pulls acting on the same underlying object.'},
    {match:/\/phenomena\/?$/,key:'phenomena',title:'Ongoing Phenomena',purpose:'Developments that persist, reconnect or change shape over time.'},
    {match:/\/priorities\/?$/,key:'priorities',title:'Risks & Opportunities',purpose:'Consequences supported by the current evidence base.'},
    {match:/\/shocks\/variants(?:\.html)?\/?$/,key:'shocks-variants',title:'Shock Variants',purpose:'Alternative forms, absorbers and counter-evidence for one supported external-shock mechanism.'},
    {match:/\/shocks\/?$/,key:'shocks',title:'External Shocks',purpose:'Potential disruptions, ordered from more obvious to more inferential.'},
    {match:/\/(historical|history)\/?$/,key:'historical',title:'Earlier Findings',purpose:'Findings published before the Radar started scanning.'},
    {match:/\/literature\/?$/,key:'literature',title:'Sources',purpose:'Where the findings come from.'},
    {match:/\/briefing\/?$/,key:'briefing',title:'Topics',purpose:'What the Radar is seeing, grouped by subject.'},
    {match:/\/glossary\/?$/,key:'glossary',title:'Glossary',purpose:'Plain meanings for the terms used across the Radar.'},
    {match:/\/stuff\/?$/,key:'stuff',title:'Stuff',purpose:'Technical details, downloadable data and supporting material.'},
    {match:/\/explore\/?$/,key:'explore',title:'More',purpose:'Other ways to look at the Radar.'}
  ];
  const page=pages.find(x=>x.match.test(path));
  if(!page)return;

  const depth=path.endsWith('/frontier/quick/')?2:1;
  const prefix='../'.repeat(depth);
  const menu=[
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
  const activeFor=target=>{
    if(target==='frontier/quick/')return page.key==='frontier-quick'||page.key==='frontier';
    if(target==='shocks/')return page.key==='shocks'||page.key==='shocks-variants';
    if(target==='historical/')return page.key==='historical';
    return page.key===target.replace(/\/$/,'').replace(/\//g,'-');
  };

  document.body.classList.add('radar-site',`page-${page.key}`);
  if(['trends','phenomena','priorities','shocks'].includes(page.key))document.body.classList.add('obviousness-ordered');

  const sidebar=document.createElement('aside');
  sidebar.className='site-sidebar';
  sidebar.setAttribute('aria-label','Site menu');
  sidebar.innerHTML=`<a class="site-sidebar-brand" href="${prefix}">R&amp;I × Geopolitics Radar</a><button class="site-menu-toggle" type="button" aria-expanded="false" aria-controls="siteMap">Menu</button><nav id="siteMap">${menu.map(([target,label,cls])=>`<a${cls?` class="${cls}"`:''}${activeFor(target)?' aria-current="page"':''} href="${prefix+target}">${label}</a>`).join('')}</nav>`;
  document.body.insertBefore(sidebar,document.body.firstChild);

  // Small screens carry the same complete map, behind one Menu button.
  const toggle=sidebar.querySelector('.site-menu-toggle');
  toggle.addEventListener('click',()=>{
    const open=sidebar.classList.toggle('open');
    toggle.setAttribute('aria-expanded',String(open));
  });

  const host=document.getElementById('app')||document.body;
  const intro=document.createElement('section');
  intro.className='shared-page-intro';
  intro.innerHTML=`<div class="shared-page-intro-inner"><h1>${page.title}</h1><p>${page.purpose}</p></div>`;
  // The page name and the reader's question come before the fact strip and the search
  // toolbar, so the reader always knows what page they are on before they filter it.
  // On pages with no #app wrapper the host is <body>, where the sidebar is already
  // first; the map must stay ahead of the page name when the shell stacks on mobile.
  if(host===document.body)host.insertBefore(intro,sidebar.nextSibling);
  else host.insertBefore(intro,host.firstChild);

  document.querySelectorAll('header,.core-flow,.core-path,.site-guide,.minimum-read').forEach(el=>el.classList.add('legacy-site-furniture'));
})();
