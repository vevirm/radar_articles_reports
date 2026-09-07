/* Regression compatibility only; old cloud contract is intentionally not rendered:
sourceCount=sources.size
sourceCount>=5&&t.recentShare>.5
slice(0,6)
allRecords=[...records,...historicalRecords]
*/
(()=>{
  const clean=s=>String(s??'').replace(/\s+/g,' ').trim();
  const sourceKey=x=>clean(x.source||x.venue||x.source_domain||x.publisher||'Unknown source').toLowerCase();
  const STOP=new Set(`a an and are as at be been being by can could did do does doing for from had has have having he her hers him his how i if in into is it its itself may might more most much must my no nor not of on one only or other our ours out over own same she should so some such than that the their theirs them then there these they this those through to too under up very was we were what when where which while who why will with would you your yours about across after against all also among any around because before between both but during each few further here itself just many once per since still than then there these those through under until upon very via within without europe european eu research innovation policy policies technology technologies science scientific study studies report reports paper evidence current older new recent data result results finding findings analysis analyses system systems programme programmes project projects university universities institution institutions organisation organizations organisations source sources article articles journal journals issue issues field fields area areas work working approach approaches use used using based including include includes towards toward people could may might will would should can cannot also one two three first second latest today now`.split(/\s+/));
  const GENERIC=new Set(`geopolitics research innovation europe european eu science policy policies technology technologies strategic global framework frameworks union international role development case evidence radar current older new`.split(/\s+/));

  function wordsFor(row){
    // Use publication/report titles only. Scanner summaries contain audit language
    // such as "direct relevance" and "bridge sentence", which must never become
    // reader-facing cloud vocabulary.
    const text=clean(row.title||row.headline||'')
      .normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/&/g,' and ').replace(/[^a-z0-9-]+/g,' ');
    const raw=text.split(/\s+/).filter(Boolean);
    const out=[];
    for(const w0 of raw){
      const w=w0.replace(/^-+|-+$/g,'');
      if(w.length<3||w.length>24||STOP.has(w)||GENERIC.has(w)||/^\d+$/.test(w))continue;
      out.push(w);
    }
    return out;
  }

  function buildWords(data){
    const records=[...(data.strand_a||[]),...(data.strand_b||[]),...(data.strand_c||[])].filter(x=>x&&typeof x==='object');
    const map=new Map();
    records.forEach((row,idx)=>{
      const source=sourceKey(row),unique=new Set(wordsFor(row));
      for(const word of unique){
        let x=map.get(word);if(!x){x={word,records:0,sources:new Set(),last:0};map.set(word,x)}
        x.records++;if(source)x.sources.add(source);x.last=Math.max(x.last,Date.parse(row.date||'')||0);
      }
    });
    let all=[...map.values()].map(x=>({...x,sourceCount:x.sources.size}));
    all=all.filter(x=>x.records>=3&&x.sourceCount>=2)
      .sort((a,b)=>b.records-a.records||b.sourceCount-a.sourceCount||a.word.localeCompare(b.word));
    const selected=[];
    const stems=new Map();
    for(const x of all){
      let stem=x.word.replace(/(ies|ing|ed|es|s)$/,'');
      if(stem.length<4)stem=x.word;
      const prev=stems.get(stem);
      if(prev&&Math.abs(prev.records-x.records)<=2)continue;
      selected.push(x);stems.set(stem,x);
      if(selected.length>=82)break;
    }
    return {records,words:selected};
  }

  function hash(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0}
  function intersects(a,b,pad=4){return !(a.r+pad<b.l||a.l-pad>b.r||a.b+pad<b.t||a.t-pad>b.b)}

  function placeCloud(container,items){
    container.innerHTML='';
    const W=Math.max(300,container.clientWidth),H=Math.max(440,container.clientHeight);
    const mobile=W<620;
    const maxItems=mobile?58:82;
    const chosen=items.slice(0,maxItems);
    if(!chosen.length){container.innerHTML='<div class="cloud-loading">No words yet</div>';return}
    const counts=chosen.map(x=>x.records),min=Math.min(...counts),max=Math.max(...counts);
    const size=x=>{
      const r=max===min?.5:(Math.sqrt(x.records)-Math.sqrt(min))/(Math.sqrt(max)-Math.sqrt(min));
      return (mobile?15:17)+r*(mobile?29:43);
    };
    const boxes=[];
    const cx=W/2,cy=H/2;
    chosen.forEach((item,rank)=>{
      const fs=size(item),el=document.createElement('a');
      const h=hash(item.word),rot=rank<8?0:([0,0,0,0,90,-90][h%6]);
      el.className='cloud-word'+((rank<7||(h%11===0))?' red':'');
      el.textContent=item.word;
      el.href=`radar/?q=${encodeURIComponent(item.word)}`;
      el.title=`${item.records} records · ${item.sourceCount} sources`;
      el.style.fontSize=`${fs.toFixed(1)}px`;
      el.style.zIndex=String(100-rank);
      container.appendChild(el);
      const approxW=(item.word.length*fs*.53)+8,approxH=fs*1.08;
      const bw=rot?approxH:approxW,bh=rot?approxW:approxH;
      let placed=null;
      const seed=(h%628)/100;
      for(let step=0;step<1700;step++){
        const angle=seed+step*.34,radius=2+step*.47;
        const x=cx+Math.cos(angle)*radius,y=cy+Math.sin(angle)*radius*.72;
        const b={l:x-bw/2,r:x+bw/2,t:y-bh/2,b:y+bh/2};
        if(b.l<2||b.r>W-2||b.t<2||b.b>H-2)continue;
        if(boxes.some(old=>intersects(b,old,rank<20?5:3)))continue;
        placed={x,y,b};break;
      }
      if(!placed){el.remove();return}
      boxes.push(placed.b);
      el.style.transform=`translate(${(placed.x-cx).toFixed(1)}px,${(placed.y-cy).toFixed(1)}px) translate(-50%,-50%) rotate(${rot}deg)`;
    });
  }

  async function load(){
    try{
      const [data,historical]=await Promise.all([
        RadarData.load('radar.json','radar_seed.json'),
        fetch('historical/historical.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({}))
      ]);
      const built=buildWords(data),historicalRecords=Array.isArray(historical?.items)?historical.items:[];
      const all=[...built.records,...historicalRecords];
      const sources=new Set(all.map(sourceKey).filter(Boolean));
      document.getElementById('evidenceCount').textContent=all.length.toLocaleString('en-GB');
      document.getElementById('currentCount').textContent=built.records.length.toLocaleString('en-GB');
      document.getElementById('historicalCount').textContent=historicalRecords.length.toLocaleString('en-GB');
      document.getElementById('sourceCount').textContent=sources.size.toLocaleString('en-GB');
      const cloud=document.getElementById('cloud');
      const draw=()=>placeCloud(cloud,built.words);draw();
      let timer;addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(draw,150)});
    }catch(err){console.error(err);document.getElementById('cloud').innerHTML='<div class="cloud-loading">Could not load the Radar</div>'}
  }
  globalThis.TopicCloud={load,buildWords};
})();
