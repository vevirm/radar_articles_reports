(()=>{
  const path=location.pathname.replace(/\\/g,'/');
  const meta=[
    ['read/','Read at least this','The shortest useful reading of what matters now.'],
    ['frontier/quick/','Matrix','Where Europe appears to gain control, carry costs, remain reliant or lose ground.'],
    ['trends/','Trends','Directions that are strengthening or weakening in the current evidence.'],
    ['phenomena/','Ongoing phenomena','Patterns that keep returning across the evidence.'],
    ['priorities/','Risks & opportunities','The clearest downside and upside pathways in the current evidence.'],
    ['shocks/','External shocks','Stress tests for the research and innovation system.'],
    ['historical/','Historical evidence','Older evidence for context, kept separate from the live Radar.'],
    ['literature/','Sources','The publications and institutions behind the Radar.'],
    ['glossary/','Glossary','Plain-language meanings for terms used across the site.'],
    ['stuff/','Stuff','Methods, files and technical audit material.'],
    ['briefing/','Evidence by topic','Current evidence grouped into themes.'],
    ['explore/','Go deeper','Choose the question you want the site to answer.']
  ];
  let found=meta.find(([slug])=>path.endsWith('/'+slug)||path.endsWith(slug));
  if(path.endsWith('/frontier/')) found=['frontier/','Matrix · full evidence','The detailed evidence behind each Matrix position.'];
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
