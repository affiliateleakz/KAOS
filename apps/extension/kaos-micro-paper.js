/* Public-data/local-file paper lab. No broker or KAOS account messages are sent. */
(()=>{'use strict';
const $=id=>document.getElementById(id),BASE='https://data-api.binance.vision',ORIGIN=BASE+'/*';
let model=null,session=null,running=false,generation=0,timer=null,controller=null,offset=0,mode='idle',startedAt=null;
function message(text){$('status').textContent=text;}
function controls(){for(const id of ['model-file','candles-file','symbol','payout','adverse'])$(id).disabled=running||(!model&&id==='candles-file');$('start').disabled=running||!model;$('stop').disabled=!running;$('export').disabled=!session;}
function stop(){running=false;generation++;clearTimeout(timer);controller?.abort();controller=null;controls();}
function render(){
 const data=session?.summary(),stats=$('stats');stats.replaceChildren();
 for(const [name,value] of [['Wins',data?.wins??0],['Losses',data?.losses??0],['Ties',data?.ties??0],['Paper P/L',data?data.pnl.toFixed(2)+' units':'0 units'],['Win rate',data?.winRate==null?'—':(data.winRate*100).toFixed(1)+'%'],['Warmup',data?Math.min(320,data.warmup)+'/320':'0/320'],['Gaps',data?.gaps??0],['Cancelled',data?.cancelled??0]]){const box=document.createElement('div');box.className='stat';const b=document.createElement('b');b.textContent=value;const span=document.createElement('span');span.textContent=name;box.append(b,span);stats.append(box);}
 const d=session?.lastDecision;$('decision').textContent=!d?'No signal yet.':d.probUp==null?'HOLD · warming up after a start or gap':`${d.direction} · up-score ${(d.probUp*100).toFixed(1)}% · research only${data.open?' · paper position open':''}`;
 $('results').replaceChildren();for(const r of (session?.results||[]).slice(-50).reverse()){const tr=document.createElement('tr');for(const value of [new Date(r.entryTs).toISOString(),r.direction,r.outcome,r.pnl.toFixed(2)]){const td=document.createElement('td');td.textContent=value;tr.append(td);}$('results').append(tr);}controls();
}
function validModel(data){
 if(data?.id!=='kaos-micro-reversion-research-v1'||data.schema!=='kaos-crypto-12-v1'||data.researchOnly!==true||data.executionEnabled!==false||data.features?.length!==12||data.trees?.length!==80||!Number.isFinite(data.base)||!Array.isArray(data.symbols)||data.symbols.join(',')!=='BTCUSDT,ETHUSDT,SOLUSDT')throw Error('Choose the KAOS Micro Reversion paper-model JSON, not the native training model or an account backup.');
 function node(n,depth=0){if(!n||depth>3)throw Error('Invalid research tree');if(Object.hasOwn(n,'leaf')){if(!Number.isFinite(n.leaf))throw Error('Invalid leaf');return;}if(!Number.isInteger(n.f)||n.f<0||n.f>=12||!Number.isFinite(n.t))throw Error('Invalid research split');node(n.l,depth+1);node(n.r,depth+1);}
 data.trees.forEach(n=>node(n));return data;
}
function create(){const payout=Number($('payout').value)/100,adverseBps=Number($('adverse').value);session=new KAOSMicroPaper.PaperSession(model,$('symbol').value,{payout,adverseBps});startedAt=new Date().toISOString();}
$('model-file').addEventListener('change',async event=>{try{stop();$('error').textContent='';const file=event.target.files[0];if(!file)return;if(file.size>250000)throw Error('Model file is too large');model=validModel(JSON.parse(await file.text()));session=null;$('model-status').textContent='Experimental model loaded locally · failed adverse-fill gate · paper only';message('Ready. Choose live public paper feed or a historical candle replay.');render();}catch(e){model=null;session=null;$('error').textContent=e.message;controls();}});
async function api(path,params,gen){const response=await fetch(BASE+path+(params?'?'+new URLSearchParams(params):''),{signal:AbortSignal.any([controller.signal,AbortSignal.timeout(15000)]),credentials:'omit',cache:'no-store'});if(gen!==generation)throw new DOMException('Stopped','AbortError');if(!response.ok)throw Error('Public price feed returned HTTP '+response.status+'. Try later or use a local candle replay.');return response.json();}
const aggregate=KAOSMicroPaper.aggregateSeconds;
$('start').addEventListener('click',async()=>{
 $('error').textContent='';running=true;const gen=++generation;controller=new AbortController();controls();
 try{
  const permission=await chrome.permissions.request({origins:[ORIGIN]});if(gen!==generation)return;if(!permission)throw Error('Public feed access was not granted. You can still replay a local file.');
  create();mode='live-paper';message('Loading completed public candles; no historical paper trades will be created.');
  const clock=await api('/api/v3/time',null,gen);offset=Number(clock.serverTime)-Date.now();if(!Number.isFinite(offset))throw Error('Public clock unavailable');
  const latest=await api('/api/v3/klines',{symbol:session.symbol,interval:'1s',limit:1000},gen);if(!Array.isArray(latest)||!latest.length)throw Error('Public feed is empty');
  const earlier=await api('/api/v3/klines',{symbol:session.symbol,interval:'1s',limit:1000,endTime:Number(latest[0][0])-1},gen);
  if(!Array.isArray(earlier))throw Error('Public warmup history unavailable');
  const warm=aggregate([...earlier,...latest],Date.now()+offset);for(const bar of warm)session.context.push(bar);
  session.lastDecision=session.context.vector?KAOSMicroPaper.score(model,session.context.vector):null;render();message('Live paper observation started. Positions and results are simulated in this tab.');
  async function poll(){if(gen!==generation)return;try{const rows=await api('/api/v3/klines',{symbol:session.symbol,interval:'1s',limit:30},gen);if(!Array.isArray(rows))throw Error('Invalid public feed response');for(const bar of aggregate(rows,Date.now()+offset)){if(!session.context.last||bar.ts>session.context.last.ts)session.step(bar);}render();if(gen===generation)timer=setTimeout(poll,5000);}catch(e){if(gen===generation){stop();$('error').textContent=e.message;message('Feed stopped. Unresolved positions remain unresolved; export before closing.');render();}}}
  timer=setTimeout(poll,5000);
 }catch(e){if(gen===generation){stop();$('error').textContent=e.message;message('Paper feed did not start. Your regular bot is unchanged.');render();}}
});
$('stop').addEventListener('click',()=>{stop();message('Stopped. Export results before closing. No real trades were submitted.');render();});
$('candles-file').addEventListener('change',async event=>{
 try{stop();$('error').textContent='';const file=event.target.files[0];if(!file)return;if(file.size>40000000)throw Error('Use one market JSON under 40 MB');const data=JSON.parse(await file.text()),symbol=$('symbol').value,rows=data.markets?.[symbol];if(!Array.isArray(rows)||!rows.length||rows.length>600000)throw Error('Choose a five-second public candle JSON for '+symbol);create();mode='historical-replay';for(const row of rows)session.step(row);message('Historical paper replay complete. These are not forward-test results.');render();}catch(e){session=null;$('error').textContent=e.message;render();}
});
$('export').addEventListener('click',()=>{if(!session)return;const data={kind:'KAOS-Micro-Reversion-Paper-Test',version:1,mode,startedAt,exportedAt:new Date().toISOString(),symbol:session.symbol,modelSource: model.source_sha256,assumedPayout:session.payout,adverseEntryBps:session.adverseBps,expirySeconds:15,summary:session.summary(),openPosition:session.open,pendingSignal:session.pending,results:session.results,executionEnabled:false,researchOnly:true};const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='KAOS-paper-'+session.symbol+'-'+Date.now()+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
async function loadOwnerModel(){
 if(typeof chrome==='undefined'||!chrome.runtime?.sendMessage)return;
 $('model-status').textContent='Loading your owner research model from KAOS…';
 try{const response=await chrome.runtime.sendMessage({type:'KAOS_GET_RESEARCH_MODEL'});if(!response?.ok)throw Error(response?.error||'Research model unavailable');model=validModel(response.data?.model);$('model-status').textContent='Owner research model loaded from KAOS · paper only';message('Ready. Start the paper feed when you choose.');render();}
 catch(e){$('model-status').textContent=e.message+' You can also import the separate paper-model JSON.';}
}
loadOwnerModel();
window.addEventListener('beforeunload',()=>{clearTimeout(timer);controller?.abort();});render();
})();
