(()=>{
  async function load(primary='radar.json', fallback='radar_seed.json'){
    const stamp='ts='+Date.now();
    for(const path of [primary,fallback]){
      try{
        const sep=path.includes('?')?'&':'?';
        const r=await fetch(path+sep+stamp,{cache:'no-store'});
        if(r.ok) return await r.json();
      }catch(_e){}
    }
    throw new Error('Radar data unavailable');
  }
  globalThis.RadarData={load};
})();
