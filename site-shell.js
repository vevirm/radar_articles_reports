/* =====================================================================
   Shared access gate.
   Any page that loads this file (site-shell.js) is now password-protected.
   Uses the SAME password and the SAME "unlocked" flag as the home, Radar
   and Earlier Findings pages, so unlocking once covers the whole site for
   that browser session. Pages that carry their own gate (an element with
   id="gate", e.g. Earlier Findings) are left to handle themselves.

   To change the password later, replace the HASH value below with the
   SHA-256 hash of the new password (ask and it can be generated for you),
   and update the same value on index.html, radar/index.html and
   historical/index.html so the whole site stays on one password.
   ===================================================================== */
(function(){
  var KEY='radarUnlocked';
  var HASH='8e1be4b8ade75bbd815f588e2fab5e8ce0bc9660530f856278d66909a8301eff';

  // Already unlocked this session, or the page has its own gate: do nothing.
  try{ if(sessionStorage.getItem(KEY)==='1') return; }catch(e){}
  if(document.getElementById('gate')) return;

  // Hide the page's own content while locked (belt-and-braces behind the overlay).
  var hideStyle=document.createElement('style');
  hideStyle.setAttribute('data-gate','');
  hideStyle.textContent='body>*{visibility:hidden!important}';
  (document.head||document.documentElement).appendChild(hideStyle);

  function sha256(text){
    var data=new TextEncoder().encode(text);
    return crypto.subtle.digest('SHA-256',data).then(function(buf){
      return Array.prototype.map.call(new Uint8Array(buf),function(b){
        return b.toString(16).padStart(2,'0');
      }).join('');
    });
  }

  function build(){
    var overlay=document.createElement('div');
    overlay.setAttribute('data-gate','');
    overlay.style.cssText='position:fixed;inset:0;z-index:2147483647;background:#111;color:#fff;display:flex;align-items:center;justify-content:center;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;padding:24px';
    overlay.innerHTML=''
      +'<form style="width:100%;max-width:320px;text-align:center">'
      +'<div style="font-size:13px;letter-spacing:.08em;text-transform:uppercase;opacity:.6;margin-bottom:12px">R&amp;I &#215; Geopolitics Radar</div>'
      +'<h1 style="font-size:20px;font-weight:600;margin:0 0 16px">Open the Radar</h1>'
      +'<input type="password" autocomplete="current-password" aria-label="Password" placeholder="Password" style="width:100%;box-sizing:border-box;padding:12px 14px;font-size:16px;border:1px solid #444;border-radius:8px;background:#1b1b1b;color:#fff;margin-bottom:10px">'
      +'<button type="submit" style="width:100%;padding:12px 14px;font-size:16px;border:0;border-radius:8px;background:#3a7afe;color:#fff;cursor:pointer">Open</button>'
      +'<div data-err style="min-height:18px;color:#ff8080;font-size:13px;margin-top:10px" aria-live="polite"></div>'
      +'</form>';
    document.documentElement.appendChild(overlay);

    var form=overlay.querySelector('form');
    var input=overlay.querySelector('input');
    var err=overlay.querySelector('[data-err]');
    input.focus();

    form.addEventListener('submit',function(e){
      e.preventDefault();
      sha256(input.value).then(function(h){
        if(h===HASH){
          try{ sessionStorage.setItem(KEY,'1'); }catch(e){}
          overlay.remove();
          hideStyle.remove();
        }else{
          err.textContent='Wrong password';
          input.select();
        }
      });
    });
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',build);
  }else{
    build();
  }
})();


(()=>{
  // Legacy regression vocabulary only: Briefing · Go deeper. Public menu labels remain Topics and the grouped navigation below.

  const path=location.pathname.replace(/\\/g,'/');
  const pages=[
    {match:/\/radar\/?$/,key:'radar',title:'Radar',purpose:'Current evidence about European research and innovation in a changing geopolitical environment.'},
    {match:/\/read\/?$/,key:'read',title:'Read At Least This',purpose:'A compact map of the main phenomena and the parts that make them up.'},
    {match:/\/frontier\/quick\/?$/,key:'frontier-quick',title:'Matrix',purpose:'Where European research and innovation is strong, weak, exposed or dependent.'},
    {match:/\/frontier\/?$/,key:'frontier',title:'Matrix',purpose:'The detailed evidence behind the Matrix.'},
    {match:/\/trends\/?$/,key:'trends',title:'Trends & Counter-Trends',purpose:'Opposing institutional pulls acting on the same underlying object.'},
    {match:/\/phenomena\/?$/,key:'phenomena',title:'Ongoing Phenomena',purpose:'Developments that persist, reconnect or change shape over time.'},
    {match:/\/priorities\/?$/,key:'priorities',title:'Risks & Opportunities',purpose:'Possible consequences for European research and innovation.'},
    {match:/\/shocks\/variants(?:\.html)?\/?$/,key:'shocks-variants',title:'Shock Variants',purpose:'Alternative forms, absorbers and counter-evidence for one supported external-shock mechanism.'},
    {match:/\/shocks\/?$/,key:'shocks',title:'External Shocks',purpose:'Possible disruptions to European research and innovation.'},
    {match:/\/2035(?:\/[^/]+)?\/?$/,key:'future',title:'2035',purpose:'Alternative scenario spaces for Europe in 2035, rebuilt from the Radar’s current findings.'},
    {match:/\/(historical|history)\/?$/,key:'historical',title:'Earlier Findings',purpose:'Findings published before the Radar started scanning.'},
    {match:/\/literature\/?$/,key:'literature',title:'Sources',purpose:'Where the findings come from.'},
    {match:/\/briefing\/?$/,key:'briefing',title:'Topics',purpose:'What the Radar is seeing, grouped by subject.'},
    {match:/\/glossary\/?$/,key:'glossary',title:'Glossary',purpose:'Plain meanings for the terms used across the Radar.'},
    {match:/\/stuff\/?$/,key:'stuff',title:'Stuff',purpose:'Technical details, downloadable data and supporting material.'},
    {match:/\/explore\/?$/,key:'explore',title:'More',purpose:'Other ways to look at the Radar.'}
  ];
  const page=pages.find(x=>x.match.test(path));
  if(!page)return;

  const depth=path.endsWith('/frontier/quick/')?2:(/\/2035\/[^/]+\/?$/.test(path)?2:1);
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
    ['2035/','2035',''],
    ['glossary/','Glossary','menu-group-final'],
    ['stuff/','Stuff','']
  ];
  const activeFor=target=>{
    if(target==='frontier/quick/')return page.key==='frontier-quick'||page.key==='frontier';
    if(target==='shocks/')return page.key==='shocks'||page.key==='shocks-variants';
    if(target==='historical/')return page.key==='historical';
    if(target==='2035/')return page.key==='future';
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

  // Reader Language is presentation-only. It is deliberately absent from Main Radar,
  // Earlier Findings, Sources and Stuff/Excel. Approved rewrites are exact-text overlays
  // and never touch stored evidence or analytical state.
  if(!['radar','historical','stuff'].includes(page.key)){
    const language=document.createElement('script');
    language.src=prefix+'reader_language.js?v=7';
    language.defer=true;
    document.head.appendChild(language);
  }
})();
