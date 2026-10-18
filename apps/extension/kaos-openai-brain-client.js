/* KAOS OpenAI Brain Client 1.6.38
Security boundary: NEVER stores or accepts an OpenAI API key.
Calls the authenticated KAOS backend only. Backend should verify active paid
membership and then call OpenAI Responses API server-side.
Shadow-only in this extension build.
*/
(function(g){
  const DEFAULT_PATH='/api/v1/ai/brain';
  async function analyze(snapshot, opts={}){
    const base=String(opts.baseUrl||'https://api.tradingwithkaos.com').replace(/\/+$/,'');
    const token=opts.accessToken||null;
    const r=await fetch(base+(opts.path||DEFAULT_PATH),{
      method:'POST',
      credentials:'include',
      headers:{
        'Content-Type':'application/json',
        ...(token?{'Authorization':'Bearer '+token}:{})
      },
      body:JSON.stringify({
        mode:'shadow',
        schema:'KAOS_BRAIN_V1',
        horizons:[5,10,15,30],
        snapshot
      })
    });
    if(!r.ok) throw new Error(`KAOS Brain HTTP ${r.status}`);
    const out=await r.json();
    const rec={
      ts:Date.now(),
      direction:['BUY','SELL','HOLD'].includes(out.direction)?out.direction:'HOLD',
      confidence:Number.isFinite(+out.confidence)?+out.confidence:null,
      expirySec:[5,10,15,30].includes(+out.expirySec)?+out.expirySec:null,
      regime:String(out.regime||'UNKNOWN'),
      setupType:String(out.setupType||'UNKNOWN'),
      shadowOnly:true
    };
    try{chrome.storage.local.set({kaosOpenAiBrainShadow:rec})}catch(_){}
    return rec;
  }
  g.KAOS_OPENAI_BRAIN={analyze,DEFAULT_PATH};
})(typeof globalThis!=='undefined'?globalThis:this);
