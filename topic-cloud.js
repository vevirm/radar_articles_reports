(()=>{
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean=s=>String(s??'').replace(/\s+/g,' ').trim();
  const sourceKey=x=>clean(x.source||x.venue||x.source_domain||'Unknown source').toLowerCase();
  const textFor=x=>' '+clean([x.title,x.headline,x.summary,x.core_message,x.relevance_note,x.why_it_matters,x.signal_note].filter(Boolean).join(' ')).toLowerCase()+' ';
  const patternHit=(text,p)=>text.includes(String(p||'').toLowerCase());
  const dateMs=v=>{const n=Date.parse(v||'');return Number.isFinite(n)?n:0};
  const fmtDate=v=>{const d=new Date(v);return Number.isNaN(d.getTime())?'':new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'long'}).format(d)};

  function buildTopics(data,vocab){
    const records=[...(data.strand_a||[]),...(data.strand_b||[]),...(data.strand_c||[])];
    const updated=dateMs(data.last_updated||data.run_completed_at)||Date.now();
    const recentCut=updated-90*86400000;
    return vocab.map(t=>{
      const sources=new Map();
      for(const x of records){
        const text=textFor(x);
        if(!(t.patterns||[]).some(p=>patternHit(text,p))) continue;
        const sk=sourceKey(x); if(!sk) continue;
        const old=sources.get(sk)||{recent:false,count:0};
        old.count++; if(dateMs(x.date)>=recentCut) old.recent=true; sources.set(sk,old);
      }
      const sourceCount=sources.size;
      const recentSources=[...sources.values()].filter(v=>v.recent).length;
      return {...t,sourceCount,recentSources,recentShare:sourceCount?recentSources/sourceCount:0};
    }).filter(t=>t.sourceCount>=2).sort((a,b)=>b.sourceCount-a.sourceCount||b.recentShare-a.recentShare||a.label.localeCompare(b.label));
  }

  function visibleLimit(){
    const w=innerWidth,h=innerHeight;
    let n=w>=1500?63:w>=1200?50:w>=900?35:w>=700?28:w>=520?18:10;
    if(h<700) n=Math.min(n,w<620?10:28);
    return n;
  }

  function distribute(xs){
    const out=[];let lo=0,hi=xs.length-1;let takeHi=false;
    while(lo<=hi){out.push(takeHi?xs[hi--]:xs[lo++]);takeHi=!takeHi}
    return out;
  }

  function render(data,vocab){
    const topics=buildTopics(data,vocab);
    const records=[...(data.strand_a||[]),...(data.strand_b||[]),...(data.strand_c||[])];
    const sources=new Set(records.map(sourceKey).filter(Boolean));
    document.getElementById('evidenceCount').textContent=records.length.toLocaleString('en-GB');
    document.getElementById('sourceCount').textContent=sources.size.toLocaleString('en-GB');
    document.getElementById('updated').textContent=fmtDate(data.last_updated||data.run_completed_at)||'recently';

    const moving=new Set(topics.filter(t=>t.sourceCount>=5&&t.recentShare>.5).sort((a,b)=>b.sourceCount-a.sourceCount||b.recentShare-a.recentShare).slice(0,6).map(t=>t.label));
    const n=Math.min(visibleLimit(),topics.length);
    const shown=topics.slice(0,n);
    const counts=shown.map(t=>t.sourceCount); const min=Math.min(...counts,1),max=Math.max(...counts,1);
    const mobile=innerWidth<620; const minPx=mobile?14:14,maxPx=mobile?24:38;
    const size=t=>{if(max===min)return(minPx+maxPx)/2;const r=(Math.sqrt(t.sourceCount)-Math.sqrt(min))/(Math.sqrt(max)-Math.sqrt(min));return minPx+r*(maxPx-minPx)};
    const cloud=document.getElementById('cloud');
    cloud.innerHTML=distribute(shown).map(t=>`<a class="topic${moving.has(t.label)?' moving':''}" style="--size:${size(t).toFixed(1)}px" href="radar/?q=${encodeURIComponent(t.patterns[0]||t.label)}" title="${t.sourceCount} sources">${esc(t.label)}</a>`).join('');

    const more=document.getElementById('cloudMore');
    if(n<topics.length){more.textContent=`See all ${topics.length} topics`;more.classList.add('show')}else more.classList.remove('show');
    const list=document.getElementById('allTopics');
    list.innerHTML=topics.map(t=>`<div class="topic-row${moving.has(t.label)?' moving':''}"><a href="radar/?q=${encodeURIComponent(t.patterns[0]||t.label)}">${esc(t.label)}</a><span>${t.sourceCount} ${t.sourceCount===1?'source':'sources'}</span></div>`).join('');
    document.getElementById('dialogTitle').textContent=`All ${topics.length} topics`;
  }

  async function load(){
    try{
      const [data,vocab]=await Promise.all([RadarData.load('radar.json','radar_seed.json'),fetch('topic_vocabulary.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('topic vocabulary');return r.json()})]);
      render(data,vocab);
      let timer;addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(()=>render(data,vocab),120)});
    }catch(err){console.error(err);document.getElementById('cloud').innerHTML='<div style="font-size:18px">Current topic map unavailable.</div>'}
  }
  window.TopicCloud={load};
})();
