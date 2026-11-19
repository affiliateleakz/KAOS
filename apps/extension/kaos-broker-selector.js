/* KAOS 1.7.4: broker selection is only available after server-verified KAOS sign-in. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const brokerURLs={pocketoption:'https://pocketoption.com/',coinbase:'https://advanced.coinbase.com/',kraken:'https://www.kraken.com/',ibkr:'https://www.interactivebrokers.com/',alpaca:'https://alpaca.markets/',oanda:'https://www.oanda.com/',tradier:'https://tradier.com/',tastytrade:'https://tastytrade.com/',binanceus:'https://www.binance.us/',schwab:'https://www.schwab.com/'};
let authenticated=false,selected=null,checking=false,connecting=false,chooserOpen=false;
const send=msg=>new Promise(resolve=>chrome.runtime.sendMessage(msg,r=>{void chrome.runtime.lastError;resolve(r||{ok:false});}));
async function cloudState(){const r=await send({type:authenticated?'KAOS_SESSION_STATUS':'KAOS_STARTUP'});return r?.state||{};}
function brokerScreen(){return $('kaos-broker-overlay');}
function show(error){if(authenticated){brokerScreen()?.classList.add('visible');chooserOpen=true;if(error)message(error);}}
function hide(){brokerScreen()?.classList.remove('visible');chooserOpen=false;}
function message(text,link){const el=$('kaos-broker-status');el.replaceChildren();el.hidden=false;const p=document.createElement('p');p.textContent=text;el.append(p);if(link){const a=document.createElement('a');a.href=link;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Open broker website';el.append(a);}}
function setupMessage(){
 message('Finish Coinbase setup on the KAOS API page, then return here and continue. Connecting does not start trades.');
 const button=document.createElement('button');button.type='button';button.textContent='Continue with saved Coinbase connection';
 button.addEventListener('click',()=>choose('coinbase',true));$('kaos-broker-status').append(button);
}
async function openSetup(){
 try{await chrome.tabs.create({url:'https://tradingwithkaos.com/dashboard/api?broker=coinbase',active:true});setupMessage();}
 catch(error){message('Could not open KAOS API setup. Visit https://tradingwithkaos.com/dashboard/api?broker=coinbase');}
}
async function choose(id,useSaved=false){if(!authenticated)return;if(!brokerURLs[id])return;if(typeof state!=='undefined'&&state.running){message('Stop the running bot before changing brokers.');return;}
 if(id!=='coinbase' && window.KAOSCoinbaseBot?.managing()){message('Coinbase is still managing this session. Close and reconcile its positions before switching brokers.');return;}
 if(id==='coinbase'){
  if(!useSaved){await openSetup();return;}
  message('Checking your Coinbase connection…');
  const r=await send({type:'KAOS_BROKER_VAULT',method:'GET',path:'/broker-connections/coinbase/status'});
  if(!r.ok){message(r.data?.detail||r.error||'Could not check Coinbase connection. Try again or open Broker Connections on the website.');return;}
  if(!(r.data?.saved||r.data?.connection?.saved)){setupMessage();message('Coinbase is not connected or needs attention. Open KAOS API setup to verify your account.');const link=document.createElement('button');link.type='button';link.textContent='Open KAOS API setup';link.onclick=openSetup;$('kaos-broker-status').append(link);return;}
  const a=await send({type:'KAOS_BROKER_VAULT',method:'GET',path:'/broker-connections/coinbase/accounts'});
  if(!a.ok){setupMessage();message('Coinbase is not connected or needs attention. Open KAOS API setup to verify your account.');const link=document.createElement('button');link.type='button';link.textContent='Open KAOS API setup';link.onclick=openSetup;$('kaos-broker-status').append(link);return;}
  const preference=await send({type:'KAOS_BROKER_VAULT',method:'PUT',path:'/broker-selection',payload:{broker:id}});
  if(!preference.ok){message(preference.data?.detail||preference.error||'Could not save Coinbase broker preference');return;}
  selected=id;await chrome.storage.local.set({kaosSelectedBroker:id});window.KAOSCoinbaseBot?.open((await cloudState()).entitlements);document.dispatchEvent(new CustomEvent('kaos-selected-broker-changed'));hide();$('kaos-broker-switch').hidden=false;$('kaos-broker-switch').textContent='Broker: Coinbase · Change';
  message('Coinbase connected. Load USD spot markets in the main bot tab, review your existing risk settings, then press Start KAOS. Keep the KAOS window open for extension-run decisions. The backend securely relays orders.');return;
 }
 if(id!=='pocketoption'){message('This broker is listed for future integration. No account, market-data, or trade execution adapter is active. Visit the broker site for information.',brokerURLs[id]);return;}
 if(connecting)return;
 connecting=true;
 message('Connecting to your Pocket Option charts…');
 try {
  const result=await send({type:'KAOS_CONNECT_PLATFORM',platform:'pocketoption',remember:true});
  const state=result.state;
  if(!result.ok || state?.step!=='DASHBOARD' || state?.status!=='CONNECTED' || !state?.license?.authorized){
   message(result.error || state?.detail || 'The broker connection could not be authorized. Re-check your KAOS account and try again.');
   return;
  }
  selected=id;
  await chrome.storage.local.set({kaosSelectedBroker:id});
  document.dispatchEvent(new CustomEvent('kaos-selected-broker-changed'));
  hide();
  $('kaos-broker-switch').hidden=false;
  $('kaos-broker-switch').textContent='Broker: Pocket Option · Change';
  document.dispatchEvent(new CustomEvent('kaos-cloud-state-changed',{detail:{state,brokerAttached:true}}));
 } catch(error) {message(String(error?.message || 'Broker connection failed'));}
 finally {connecting=false;}
}
async function refresh(){if(checking)return;checking=true;try{const s=await cloudState();authenticated=s.step==='PLATFORM'||s.step==='DASHBOARD';if(!authenticated){hide();$('kaos-broker-switch').hidden=true;selected=null;return;}
 if(!selected&&!chooserOpen){const remembered=await chrome.storage.local.get('kaosSelectedBroker');if(remembered.kaosSelectedBroker==='coinbase'){
   const connection=await send({type:'KAOS_BROKER_VAULT',method:'GET',path:'/broker-connections/coinbase/status'});
   if(connection.ok&&(connection.data?.saved||connection.data?.connection?.saved)){selected='coinbase';window.KAOSCoinbaseBot?.open(s.entitlements);hide();$('kaos-broker-switch').hidden=false;$('kaos-broker-switch').textContent='Broker: Coinbase · Change';document.dispatchEvent(new CustomEvent('kaos-selected-broker-changed'));}
 }}
 if(selected==='coinbase')return;
 if(['pocketoption','pocket_option'].includes(s.platform)){selected='pocketoption';if(!chooserOpen)hide();$('kaos-broker-switch').hidden=false;$('kaos-broker-switch').textContent='Broker: Pocket Option · Change';}
 else if(!selected)show();}finally{checking=false;}}
document.addEventListener('DOMContentLoaded',async()=>{
 // Ignore cached broker selection until the server has validated membership.
 document.querySelectorAll('[data-kaos-broker]').forEach(b=>b.addEventListener('click',()=>choose(b.dataset.kaosBroker)));
 $('kaos-broker-switch').addEventListener('click',()=>{selected=null;show();});
 await refresh();setInterval(refresh,12000);
 document.addEventListener('kaos-cloud-state-changed',event=>{
  const state=event.detail?.state;
  if(selected!=='coinbase' && state?.step==='DASHBOARD' && state.status==='CONNECTED' && state.license?.authorized && ['pocketoption','pocket_option'].includes(state.platform)){
   selected='pocketoption';if(!chooserOpen)hide();$('kaos-broker-switch').hidden=false;$('kaos-broker-switch').textContent='Broker: Pocket Option · Change';
  }
  refresh();
 });
});
window.KAOSBroker={choose,refresh,show};
})();
