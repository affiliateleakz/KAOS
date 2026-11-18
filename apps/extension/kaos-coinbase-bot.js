/* Coinbase Start uses the same bot controls. No keys, market signals or orders in this page. */
(()=>{'use strict';
let selected=false,busy=false,settingsReady=null;
const $=id=>document.getElementById(id);
const send=msg=>new Promise(resolve=>chrome.runtime.sendMessage(msg,r=>{void chrome.runtime.lastError;resolve(r||{ok:false,error:'KAOS background unavailable'});}));
async function api(action,payload){const r=await send({type:'KAOS_COINBASE_BOT',action,payload});if(!r.ok)throw Error(r.data?.detail||r.error||'Coinbase bot request failed');return r.data;}
function paint(data){
 const active=data.state==='RUNNING';state.running=active;setRunningUI(active);
 $('kaos-coinbase-bot-detail').textContent=[data.state,data.workerReady===false?'Automatic worker offline':'',data.detail].filter(Boolean).join(' · ');
 setStatus(active?'active':'idle',`COINBASE · ${data.state} · ${data.detail||''}`);
}
async function refresh(){
 const saved=await chrome.storage.local.get('kaosSelectedBroker');selected=saved.kaosSelectedBroker==='coinbase';
 const panel=$('kaos-coinbase-bot-panel');if(!panel)return;panel.hidden=!selected;
 const expiry=$('kaos-expiry-select');if(expiry)expiry.disabled=selected;
 if(!selected)return;
 try{paint(await api('status'));}catch(e){$('kaos-coinbase-bot-detail').textContent=e.message+' · Server trading state is unverified; check Coinbase.';}
}
async function markets(){
 const r=await send({type:'KAOS_BROKER_VAULT',method:'GET',path:'/broker-connections/coinbase/products'});
 if(!r.ok)throw Error(r.data?.detail||r.error||'Coinbase markets unavailable');
 const select=$('kaos-coinbase-products'),chosen=new Set([...select.selectedOptions].map(o=>o.value));
 select.replaceChildren();
 for(const product of r.data.products||[]){if(product.trading_disabled||product.view_only)continue;const option=document.createElement('option');option.value=option.textContent=product.product_id;option.selected=chosen.has(option.value);select.append(option);}
}
window.KAOSCoinbaseBot={
 selected:()=>selected,
 ready:()=>settingsReady||Promise.resolve(),
 open(entitlements){
  selected=true;
  if(!settingsReady)settingsReady=loadSettings();
  if(entitlements&&typeof kaosApplyChartLimit==='function')kaosApplyChartLimit(entitlements);
  const shell=$('screen-main');if(shell){shell.classList.add('active','view-dashboard');shell.style.display='flex';}
  showScreen('main');
  const badge=$('trader-badge');if(badge)badge.style.display='none';
  if($('kaos-live-asset'))$('kaos-live-asset').textContent='COINBASE SPOT';
  refresh();
 },
 refresh,
 async start(settings){
  if(busy)return;busy=true;
  try{
   const products=[...$('kaos-coinbase-products').selectedOptions].map(o=>o.value);
   if(products.length!==settings.chartCount)throw Error('Select one Coinbase USD market for each chart. Load markets below if needed.');
   if(!confirm(`Start AUTOMATIC REAL Coinbase spot trading?\n$${settings.amount} per trade · ${settings.chartCount} markets · up to $${Number(settings.amount)*settings.chartCount} notional.\nUses your existing risk controls. New entries run for up to 12 hours. Spot positions have no binary expiration. Stop prevents new buys; existing holdings still need exit management.`))return;
   paint(await api('start',{settings,products}));
  }catch(e){setStatus('idle','COINBASE · START NOT CONFIRMED');$('kaos-coinbase-bot-detail').textContent='Start not confirmed: '+e.message+'. Refresh status and check Coinbase before retrying.';}
  finally{busy=false;}
 },
 async stop(){try{paint(await api('stop'));}catch(e){$('kaos-coinbase-bot-detail').textContent='STOP NOT CONFIRMED: '+e.message+'. Check Coinbase and the server worker.';}}
};
document.addEventListener('DOMContentLoaded',()=>{
 const panel=document.createElement('section');panel.id='kaos-coinbase-bot-panel';panel.hidden=true;panel.style.cssText='padding:12px;margin:12px 0;border:1px solid #80632b;border-radius:8px;background:#11100c;color:#e6d5ac';
 panel.innerHTML='<b>COINBASE · AUTOMATIC SPOT</b><p>Uses Trade Amount, chart count and Risk Controls above. KAOS Strategy buys spot and sells held positions on an opposite signal or configured session risk limit. No binary expiration. Martingale and Compounding must be off.</p><label for="kaos-coinbase-products">Coinbase markets · select the same number as chart count</label><select id="kaos-coinbase-products" multiple size="4" style="width:100%;background:#080808;color:#e6d5ac"></select><button type="button" id="kaos-coinbase-markets">Load Coinbase markets</button><p id="kaos-coinbase-bot-detail" role="status">Not started. A dedicated live worker is required; browser closure does not stop an active server session.</p>';
 $('start-btn')?.closest('.kaos-run-rail')?.after(panel);
 $('kaos-coinbase-markets').addEventListener('click',()=>markets().catch(e=>{$('kaos-coinbase-bot-detail').textContent=e.message;}));
 refresh();setInterval(refresh,15000);
 document.addEventListener('kaos-selected-broker-changed',refresh);
});
})();
