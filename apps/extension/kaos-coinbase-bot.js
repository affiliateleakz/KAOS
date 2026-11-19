/* Extension-driven Coinbase spot decisions; backend holds keys and forwards orders. */
(()=>{'use strict';
let selected=false,busy=false,settingsReady=null,loopBusy=false,armed=null,closeRequested=false;
const $=id=>document.getElementById(id),cache=new Map();
const send=msg=>new Promise(resolve=>chrome.runtime.sendMessage(msg,r=>{void chrome.runtime.lastError;resolve(r||{ok:false,error:'KAOS background unavailable'});}));
async function api(action,payload){const r=await send({type:'KAOS_COINBASE_BOT',action,payload});if(!r.ok)throw Error(r.data?.detail||r.error||'Coinbase request failed');return r.data;}
function detail(text){if($('kaos-coinbase-bot-detail'))$('kaos-coinbase-bot-detail').textContent=text;}
function paint(data){const active=data.state==='RUNNING';state.running=active;setRunningUI(active);detail([data.state,data.detail].filter(Boolean).join(' · '));setStatus(active?'active':'idle','COINBASE · '+data.state);}
async function refresh(){
 const saved=await chrome.storage.local.get('kaosSelectedBroker');selected=saved.kaosSelectedBroker==='coinbase';
 const panel=$('kaos-coinbase-bot-panel');if(!panel)return;panel.hidden=!selected;
 const expiry=$('kaos-expiry-select');if(expiry){expiry.disabled=selected;if(expiry.closest('.kaos-tb-field'))expiry.closest('.kaos-tb-field').hidden=selected;}
 document.querySelectorAll('.top-strategy-summary').forEach(el=>{el.hidden=selected;});
 if(!selected){armed=null;return;}
 try{const data=await api('status');paint(data);if(!armed&&['RUNNING','STOPPING'].includes(data.state))detail('Existing '+data.executionMode+' session: use Resume only for an extension session. No automatic restart.');}catch(e){detail(e.message+' · Trading state unverified; check Coinbase.');}
}
async function markets(){
 const r=await send({type:'KAOS_BROKER_VAULT',method:'GET',path:'/broker-connections/coinbase/products'});
 if(!r.ok)throw Error(r.data?.detail||r.error||'Coinbase markets unavailable');
 const select=$('kaos-coinbase-products'),chosen=new Set([...select.selectedOptions].map(o=>o.value));select.replaceChildren();
 for(const product of r.data.products||[]){if(product.trading_disabled||product.view_only||!/-USD$/.test(product.product_id))continue;const option=document.createElement('option');option.value=option.textContent=product.product_id;option.selected=chosen.has(option.value);select.append(option);}
}
async function publicData(product,kind){
 const response=await fetch('https://api.exchange.coinbase.com/products/'+encodeURIComponent(product)+'/'+kind,{cache:'no-store',signal:AbortSignal.timeout(10000)});
 if(!response.ok)throw Error('Coinbase market data HTTP '+response.status);return response.json();
}
async function market(product){
 const q=KAOSCoinbaseSpot.quote(await publicData(product,'ticker'),Date.now());
 try {
  let item=cache.get(product);const now=Date.now();
  if(!item||now-item.loaded>60000){item={rows:KAOSCoinbaseSpot.candles(await publicData(product,'candles?granularity=60'),Date.now()),loaded:Date.now()};cache.set(product,item);}
  if(Date.now()-(item.rows.at(-1).ts+60000)>90000)throw Error('Closed candles are stale');
  return {...q,signal:KAOSCoinbaseSpot.signal(item.rows)};
 } catch(e) {
  // Missing signal history pauses entries but must not disable quote-based exits.
  return {...q,signal:{direction:'WAIT'},feedIssue:e.message};
 }
}

const num=value=>{const n=Number(value);if(!Number.isFinite(n)||n<0)throw Error('Unverified Coinbase fill values');return n;};
async function submit(session,intent){
 if(armed!==session.sessionId)throw Error('Local session stopped');
 // The identity is deterministic and reserved server-side before Coinbase is called.
 // An interrupted response cannot create a replacement trade on retry.
 return api('browser-order',{session_id:session.sessionId,intent});
}
async function tick(){
 if(loopBusy||!selected||!armed)return;loopBusy=true;
 try{
  const data=await api('snapshot'),s=data.session;
  if(!s||s.sessionId!==armed||s.executionMode!=='extension'){armed=null;throw Error('Session changed; automatic decisions paused');}
  if(!['RUNNING','STOPPING'].includes(s.state)){armed=null;paint({state:s.state});return;}
  const orders=data.orders,settings=s.settings,spot=settings.spot,quotes={};
  if(!spot)throw Error('Spot settings unavailable');
  const open=orders.filter(o=>o.side==='BUY'&&o.state==='FILLED');
  const uncertain=orders.some(o=>!['FILLED','CLOSED','REJECTED','CANCELLED'].includes(o.state));
  // Unknown or pending orders must be reconciled before another trade is sent.
  if(uncertain)throw Error('Order pending or uncertain; reconciling. No replacement orders.');
  for(const p of settings.products)quotes[p]=await market(p);
  let pnl=0;const results=[];
  for(const buy of orders.filter(o=>o.side==='BUY'&&['FILLED','CLOSED'].includes(o.state))){
   const cost=num(buy.fill_notional)+num(buy.fill_fees),exit=orders.find(o=>o.side==='SELL'&&o.source_buy_client_order_id===buy.client_order_id&&o.state==='FILLED');
   if(exit){const result=num(exit.fill_notional)-num(exit.fill_fees)-cost;pnl+=result;results.push({time:Date.parse(exit.updated_at),pnl:result});}
   else {if(!quotes[buy.product_id])throw Error('Missing position quote');pnl+=num(buy.filled_size)*quotes[buy.product_id].bid-cost;}
  }
  results.sort((a,b)=>a.time-b.time);let streak=0;for(const r of [...results].reverse()){if(r.pnl>=0)break;streak++;}
  const halt=(Number(settings.dailyLossLimit)>0&&pnl<=-Number(settings.dailyLossLimit))||(Number(settings.profitTarget)>0&&pnl>=Number(settings.profitTarget))||(settings.maxLossStreak>0&&streak>=settings.maxLossStreak);
  const lastLoss=[...results].reverse().find(r=>r.pnl<0),cooldown=Math.max(settings.cooldownAfterLoss,settings.autoCooldownOn?(streak>=8?3600:streak>=5?900:streak>=3?300:0):0);
  const cooling=lastLoss&&Date.now()-lastLoss.time<cooldown*1000;
  if((halt||Date.now()-s.startedAtMs>=12*3600000)&&s.state==='RUNNING'){await api('stop');s.state='STOPPING';}
  state.running=s.state==='RUNNING';setRunningUI(state.running);
  $('kaos-coinbase-positions').textContent=open.length?open.map(o=>o.product_id+' · '+o.filled_size+' held · entry $'+(num(o.fill_notional)/num(o.filled_size)).toFixed(4)).join('\n'):'No verified open KAOS positions';
  detail((s.state==='RUNNING'?'SCANNING':'ENTRIES STOPPED')+' · Estimated session P/L $'+pnl.toFixed(2)+' · '+(armed?'Extension running':'Paused'));
  for(const buy of open){
   const q=quotes[buy.product_id],entry=(num(buy.fill_notional)+num(buy.fill_fees))/num(buy.filled_size),change=(q.bid-entry)/entry*100;
   if(closeRequested||halt||change<=-Number(spot.stopLossPct)||change>=Number(spot.takeProfitPct)||q.signal.direction==='SELL'){
    if(Date.now()-q.stamp>15000)throw Error('Exit quote expired');
    await submit(s,{client_order_id:('cbx_'+buy.client_order_id).slice(0,64),product_id:buy.product_id,side:'SELL',base_size:buy.filled_size,source_buy_client_order_id:buy.client_order_id});
    return; // Reconcile before the next action.
   }
  }
  if(closeRequested&&!open.length){closeRequested=false;armed=null;detail('Close requested: no tracked open positions remain. Verify Coinbase directly.');return;}
  if(s.state!=='RUNNING'||cooling||halt)return;
  if(Object.values(quotes).some(q=>q.feedIssue)){detail('Entries paused: incomplete candle history. Software price exits remain active.');return;}
  for(const p of settings.products){
   const q=quotes[p];if(open.some(o=>o.product_id===p)||q.signal.direction!=='BUY'||q.spreadPct>Number(spot.maxSpreadPct))continue;
   if(Date.now()-q.stamp>15000||Date.now()-(q.signal.stamp+60000)>90000)throw Error('Entry data expired');
   const id='cbe_'+s.sessionId.slice(0,16)+'_'+p+'_'+q.signal.stamp;
   if(orders.some(o=>o.client_order_id===id))continue;
   await submit(s,{client_order_id:id,product_id:p,side:'BUY',quote_size:settings.amount});return;
  }
 }catch(e){detail('PAUSED · '+e.message+' Keep this window open; inspect Coinbase for actual holdings.');}
 finally{loopBusy=false;}
}
window.KAOSCoinbaseBot={selected:()=>selected,managing:()=>!!armed,ready:()=>settingsReady||Promise.resolve(),
 open(entitlements){selected=true;if(!settingsReady)settingsReady=loadSettings();if(entitlements&&typeof kaosApplyChartLimit==='function')kaosApplyChartLimit(entitlements);const shell=$('screen-main');if(shell){shell.classList.add('active','view-dashboard');shell.style.display='flex';}showScreen('main');if($('trader-badge'))$('trader-badge').style.display='none';if($('kaos-live-asset'))$('kaos-live-asset').textContent='COINBASE SPOT';refresh();},refresh,
 async start(settings){if(busy)return;busy=true;try{
  const products=[...$('kaos-coinbase-products').selectedOptions].map(o=>o.value);
  const spot={stopLossPct:$('kaos-cb-sl').value,takeProfitPct:$('kaos-cb-tp').value,maxSpreadPct:$('kaos-cb-spread').value};
  if(products.length!==settings.chartCount)throw Error('Select one USD market per market slot.');
  if(!confirm('Start REAL Coinbase spot trading?\n$'+settings.amount+' per entry; '+products.length+' markets.\n1-minute spot trend/breakout candidate, NOT the binary strategy. No established profitable track record.\nStop loss '+spot.stopLossPct+'%, take profit '+spot.takeProfitPct+'%, maximum entry spread '+spot.maxSpreadPct+'%. Software exits need this window open; these are not exchange-native stops. Fees/slippage apply.'))return;
  const result=await api('start',{settings,products,execution_mode:'extension',spot});armed=result.sessionId;closeRequested=false;paint(result);await tick();
 }catch(e){detail('Start not confirmed: '+e.message+'. Refresh before retrying.');}finally{busy=false;}},
 async stop(){try{await api('stop');state.running=false;setRunningUI(false);detail('New entries stopped. Keep KAOS open for software exits, or close positions explicitly.');}catch(e){detail('STOP NOT CONFIRMED: '+e.message);}}
};
document.addEventListener('DOMContentLoaded',()=>{
 const panel=document.createElement('section');panel.id='kaos-coinbase-bot-panel';panel.hidden=true;panel.style.cssText='padding:12px;margin:12px 0;border:1px solid #80632b;border-radius:8px;background:#11100c;color:#e6d5ac';
 panel.innerHTML='<b>COINBASE · SPOT TRADING</b><p>KAOS Spot Trend v1 · 1-minute trend/breakout candidate. Trade Amount is USD per entry. Market slots set maximum concurrent positions. No binary expiration, Martingale or Compounding.</p><label>USD markets <select id="kaos-coinbase-products" multiple size="4" style="width:100%;background:#080808;color:#e6d5ac"></select></label><button type="button" id="kaos-coinbase-markets">Load markets</button><p><label>Stop loss % <input id="kaos-cb-sl" type="number" min="0.01" max="50" step="0.01" value="2"></label> <label>Take profit % <input id="kaos-cb-tp" type="number" min="0.01" max="50" step="0.01" value="4"></label> <label>Max entry spread % <input id="kaos-cb-spread" type="number" min="0.01" max="50" step="0.01" value="0.3"></label></p><button type="button" id="kaos-cb-resume">Resume existing session</button> <button type="button" id="kaos-cb-close">Stop entries & close KAOS positions</button><p>Keep this KAOS window open. Closing it stops decisions and software protection. No exchange-native stop is placed. Stop blocks new buys; it does not immediately sell holdings.</p><pre id="kaos-coinbase-positions"></pre><p id="kaos-coinbase-bot-detail" role="status">Not started.</p>';
 $('start-btn')?.closest('.kaos-run-rail')?.after(panel);
 $('kaos-coinbase-markets').onclick=()=>markets().catch(e=>detail(e.message));
 $('kaos-cb-resume').onclick=async()=>{try{const {session:s}=await api('snapshot');if(!s||s.executionMode!=='extension'||!['RUNNING','STOPPING'].includes(s.state))throw Error('No extension session to resume; stop the legacy worker/session before a new Start.');if(!confirm('Resume saved Coinbase session: $'+s.settings.amount+' per entry; '+s.settings.products.join(', ')+'. Stop '+s.settings.spot.stopLossPct+'%, take profit '+s.settings.spot.takeProfitPct+'%. Includes exits and any still-authorized entries. Keep KAOS open.'))return;for(const [key,id] of [['stopLossPct','kaos-cb-sl'],['takeProfitPct','kaos-cb-tp'],['maxSpreadPct','kaos-cb-spread']])$(id).value=s.settings.spot[key];armed=s.sessionId;await tick();}catch(e){detail(e.message);}};
 $('kaos-cb-close').onclick=async()=>{try{const {session:s}=await api('snapshot');if(!s||s.executionMode!=='extension')throw Error('No extension session to close');if(!confirm('Stop new entries and submit market sells for verified KAOS positions? Fees and slippage apply.'))return;await api('stop');armed=s.sessionId;closeRequested=true;await tick();}catch(e){detail(e.message);}};
 refresh();setInterval(()=>{if(armed)tick();},15000);document.addEventListener('kaos-selected-broker-changed',refresh);
});
})();
