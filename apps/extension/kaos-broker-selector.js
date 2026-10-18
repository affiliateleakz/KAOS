/* KAOS 1.7.4: broker selection is only available after server-verified KAOS sign-in. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const brokerURLs={pocketoption:'https://pocketoption.com/',coinbase:'https://advanced.coinbase.com/',kraken:'https://www.kraken.com/',ibkr:'https://www.interactivebrokers.com/',alpaca:'https://alpaca.markets/',oanda:'https://www.oanda.com/',tradier:'https://tradier.com/',tastytrade:'https://tastytrade.com/',binanceus:'https://www.binance.us/',schwab:'https://www.schwab.com/'};
let authenticated=false,selected=null,checking=false;
const send=msg=>new Promise(resolve=>chrome.runtime.sendMessage(msg,r=>{void chrome.runtime.lastError;resolve(r||{ok:false});}));
async function cloudState(){const r=await send({type:'KAOS_STARTUP'});return r?.state||{};}
function brokerScreen(){return $('kaos-broker-overlay');}
// Header reflects the broker actually chosen; never a hard-coded connection claim.
function setHeader(id){const t={kaos_paper:'● KAOS PAPER · COINBASE PUBLIC DATA · PAPER ONLY',pocketoption:'● BROKER: POCKET OPTION',coinbase:'● BROKER: COINBASE (TRADING ADAPTER PENDING)'}[id]||'● BROKER: NOT SELECTED';
 document.querySelectorAll('.kaos-broker-state').forEach(el=>{el.textContent=t;});}
function show(){if(authenticated)brokerScreen()?.classList.add('visible');}
function hide(){brokerScreen()?.classList.remove('visible');}
function message(text,link){const el=$('kaos-broker-status');el.replaceChildren();el.hidden=false;const p=document.createElement('p');p.textContent=text;el.append(p);if(link){const a=document.createElement('a');a.href=link;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Open broker website';el.append(a);}}
async function choose(id){if(!authenticated)return;
 if(id==='kaos_paper'){
  // Shared server-side paper session (same account as website/mobile). Opens no broker site and needs no broker credentials.
  selected=id;await chrome.storage.local.set({kaosSelectedBroker:id});setHeader(id);hide();$('kaos-broker-switch').hidden=false;$('kaos-broker-switch').textContent='Broker: KAOS Paper · Change';
  const nav=document.querySelector('#screen-chart [data-kaos-view="paper"]');
  if(nav)nav.click();else{if(typeof terminalShow==='function')await terminalShow();document.querySelector('.terminal-tab[data-page="paper"]')?.click();}
  return;
 }
 if(!brokerURLs[id])return;
 if(id==='coinbase'){
  const r=await send({type:'KAOS_BROKER_VAULT',method:'GET',path:'/broker-connections/coinbase/status'});
  if(!r.ok||!r.data?.connection?.saved){document.dispatchEvent(new CustomEvent('kaos-coinbase-setup'));return;}
  const a=await send({type:'KAOS_BROKER_VAULT',method:'GET',path:'/broker-connections/coinbase/accounts'});
  if(!a.ok){message('Your saved Coinbase connection needs attention. Reconnect it in KAOS account settings.');return;}
  selected=id;await chrome.storage.local.set({kaosSelectedBroker:id});setHeader(id);hide();$('kaos-broker-switch').hidden=false;$('kaos-broker-switch').textContent='Broker: Coinbase · Change';
  await chrome.tabs.create({url:brokerURLs[id],active:true});
  message('Coinbase API verified and account restored. Coinbase automated trading is not enabled yet; Start KAOS remains Pocket Option-only.');return;
 }
 if(id!=='pocketoption'){message('This broker is listed for future integration. No account, market-data, or trade execution adapter is active. Visit the broker site for information.',brokerURLs[id]);return;}
 selected=id;await chrome.storage.local.set({kaosSelectedBroker:id});setHeader(id);hide();$('kaos-broker-switch').hidden=false;$('kaos-broker-switch').textContent='Broker: Pocket Option · Change';
 await chrome.tabs.create({url:brokerURLs[id],active:true});
 if(typeof startFlow==='function') startFlow();
}
async function refresh(){if(checking)return;checking=true;try{const s=await cloudState();authenticated=s.step==='PLATFORM'||s.step==='DASHBOARD';if(!authenticated){hide();$('kaos-broker-switch').hidden=true;selected=null;setHeader(null);return;}
 if(!selected)show();}finally{checking=false;}}
document.addEventListener('DOMContentLoaded',async()=>{
 // Ignore cached broker selection until the server has validated membership.
 document.querySelectorAll('[data-kaos-broker]').forEach(b=>b.addEventListener('click',()=>choose(b.dataset.kaosBroker)));
 $('kaos-broker-switch').addEventListener('click',()=>{selected=null;setHeader(null);show();});
 await refresh();setInterval(refresh,12000);
 document.addEventListener('kaos-cloud-state-changed',()=>refresh());
});
window.KAOSBroker={choose,refresh,show};
})();
