(()=>{'use strict';
const BASE='';
const overlay=document.getElementById('kaos-broker-overlay');
const status=document.getElementById('kaos-broker-status');
const grid=overlay?.querySelector('.broker-grid');
if(!overlay||!grid||!status)return;
const pane=document.createElement('section');pane.id='kaos-coinbase-connect';pane.hidden=true;
pane.innerHTML=`<h3>Connect Coinbase Advanced Trade</h3>
<p>1. <a href="https://advanced.coinbase.com/join/8H6AVRJ" target="_blank" rel="noopener noreferrer">Sign up for Coinbase through KAOS</a></p>
<p>2. <a href="https://portal.cdp.coinbase.com/" target="_blank" rel="noopener noreferrer">Create a CDP API key</a> with View and Trade permissions; disable Transfer. KAOS verifies account access before saving. Automated orders are not enabled.</p>
<label style="display:block;margin:8px 0">API Key Name<input id="kaos-cb-name" autocomplete="off" spellcheck="false" placeholder="organizations/.../apiKeys/..." style="width:100%;padding:10px;background:#151515;color:white;border:1px solid #826a36"></label>
<label style="display:block;margin:8px 0">API Private Key<textarea id="kaos-cb-key" rows="5" autocomplete="off" spellcheck="false" placeholder="Paste Coinbase Ed25519 base64, PEM, or credentials JSON" style="width:100%;padding:10px;background:#151515;color:white;border:1px solid #826a36"></textarea></label>
<button id="kaos-cb-connect" type="button" style="padding:12px">Connect Coinbase</button>
<button id="kaos-cb-back" type="button" style="padding:12px">Back</button>
<div id="kaos-cb-result" style="margin-top:12px;white-space:pre-wrap"></div>`;
grid.after(pane);
const el=id=>document.getElementById(id);
const result=el('kaos-cb-result');
async function request(path,opts={}){
 const method=opts.method||'GET'; const payload=opts.body?JSON.parse(opts.body):undefined;
 const d=await chrome.runtime.sendMessage({type:'KAOS_BROKER_VAULT',path:'/broker-connections/coinbase'+path.replace('/coinbase',''),method,payload});
 if(!d?.ok)throw Error(d?.data?.detail||d?.error||'Broker connection failed');return d.data;
}
// Capture Coinbase selection before the foundation selector's handler, which otherwise shows 'pending'.
document.addEventListener('kaos-coinbase-setup',()=>{grid.hidden=true;status.hidden=true;pane.hidden=false;overlay.classList.add('visible');});
// Broker selection is handled by kaos-broker-selector.js after member authentication.
el('kaos-cb-back').addEventListener('click',()=>{pane.hidden=true;grid.hidden=false;result.textContent='';});
el('kaos-cb-connect').addEventListener('click',async()=>{
 const btn=el('kaos-cb-connect');btn.disabled=true;result.textContent='Verifying Coinbase through KAOS cloud...';
 try{const d=await request('',{method:'PUT',body:JSON.stringify({key_name:el('kaos-cb-name').value,private_key:el('kaos-cb-key').value})});
 el('kaos-cb-key').value='';el('kaos-cb-name').value='';
 const products=await request('/products');
 result.textContent=`Coinbase authenticated and saved to your KAOS website account.  ${d.account_count} account(s) and ${products.products?.length||0} market(s) retrieved. Read access verified. No bot session was started; review Coinbase controls in the main bot tab.`;
 }catch(e){result.textContent='Connection failed: '+e.message;}
 finally{btn.disabled=false;}
});
})();