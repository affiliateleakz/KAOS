/* KAOS live closed-candle research bridge. Shadow mode only.
 * Runs in the extension service worker; no order-routing privileges.
 */
(() => {
  const HISTORY='KAOS_raw5_history_v1';
  const STATUS='KAOS_agent_live_status_v1';
  const ENDPOINT='http://127.0.0.1:8765/otc/analyze';
  let running=false, lastKey='', lastAttempt=0;
  async function evaluate(){
    if(running || Date.now()-lastAttempt<8000)return;
    lastAttempt=Date.now();running=true;
    try{
      const stored=await chrome.storage.local.get(HISTORY);
      const markets=stored?.[HISTORY]?.byAsset||{};
      const candidates=Object.entries(markets).filter(([_,rows])=>Array.isArray(rows)&&rows.length>=60)
        .map(([market,rows])=>({market,rows,ts:Number(rows.at(-1)?.closeTs||rows.at(-1)?.ts||0)}))
        .filter(x=>x.ts>0&&Date.now()-x.ts<120000).sort((a,b)=>b.ts-a.ts);
      if(!candidates.length){await chrome.storage.local.set({[STATUS]:{status:'waiting_for_recent_closed_candles',at:Date.now(),trade_authorized:false}});return;}
      const {market,rows}=candidates[0];
      const recent=rows.slice(-240);
      // Refuse data gaps and incomplete candles. Never fill gaps synthetically.
      if(recent.some((c,i)=>i>0&&(Number(c.ts)-Number(recent[i-1].ts)!==5000))){
        await chrome.storage.local.set({[STATUS]:{status:'waiting_for_contiguous_candles',market,at:Date.now(),trade_authorized:false}});return;
      }
      const latest=recent.at(-1), key=market+':'+latest.ts;
      if(key===lastKey)return;
      if(Number(latest.closeTs||Number(latest.ts)+5000)>Date.now())return;
      const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),3500);
      let response;
      try{response=await fetch(ENDPOINT,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({market,candles:recent}),signal:controller.signal});}
      finally{clearTimeout(timer);}
      if(!response.ok)throw Error('Research service HTTP '+response.status);
      const result=await response.json();lastKey=key;
      await chrome.storage.local.set({[STATUS]:{status:'connected',at:Date.now(),market,candleTs:latest.ts,decision:result.decision,agents:result.agents,trade_authorized:false,source:'observed_closed_5s_candles'}});
    }catch(err){await chrome.storage.local.set({[STATUS]:{status:'service_unavailable',at:Date.now(),error:String(err).slice(0,250),trade_authorized:false}}).catch(()=>{});}
    finally{running=false;}
  }
  chrome.storage.onChanged.addListener((changes,area)=>{if(area==='local'&&changes[HISTORY])void evaluate();});
  chrome.alarms.create('kaos_agent_research_poll',{periodInMinutes:0.5});
  chrome.alarms.onAlarm.addListener(alarm=>{if(alarm.name==='kaos_agent_research_poll')void evaluate();});
  void evaluate();
})();
