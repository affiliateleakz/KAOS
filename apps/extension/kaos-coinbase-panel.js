// Coinbase Advanced account (read-only) in the extension. Data comes from the member's KAOS cloud account
// (/api/v1/broker-connections/coinbase/accounts); keys never reach the extension. No orders are placed here.
(function(){
  const root=()=>document.getElementById('kaos-coinbase-panel');
  const call=(path)=>chrome.runtime.sendMessage({type:'KAOS_BROKER_VAULT',method:'GET',path});
  const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const rows=(list,cols,empty)=>list&&list.length?list.map(r=>'<tr>'+cols.map(c=>`<td style="padding:2px 6px">${esc(r[c]??'–')}</td>`).join('')+'</tr>').join(''):`<tr><td colspan="${cols.length}" style="color:#8b96a5">${empty}</td></tr>`;
  const table=(title,heads,body)=>`<div style="margin-top:8px"><b>${title}</b><table style="width:100%;border-collapse:collapse"><tr style="color:#8b96a5">${heads.map(h=>`<th style="text-align:left;padding:2px 6px">${h}</th>`).join('')}</tr>${body}</table></div>`;
  async function load(){
    const el=root(); if(!el)return;
    const st=await call('/broker-connections/coinbase/status');
    if(!st||!st.ok){el.textContent='Sign in to KAOS to load your Coinbase account.';return;}
    if(!st.data.connected){el.innerHTML='No Coinbase account connected. Connect it on tradingwithkaos.com → Broker Connections, or choose Coinbase in the broker selector.';return;}
    const a=await call('/broker-connections/coinbase/accounts');
    if(!a||!a.ok){el.innerHTML=`<span style="color:#f5b041">Coinbase unavailable: ${esc((a&&a.data&&a.data.detail)||(a&&a.error)||'error')}</span>`;return;}
    const d=a.data;
    el.innerHTML=`<b style="color:#7DB8FF">COINBASE ADVANCED · READ-ONLY · key ${esc(d.key_hint)}</b>
      <div style="color:#8b96a5;margin:4px 0">Live from Coinbase Advanced API · fetched ${esc(String(d.fetched_at).slice(11,19))} UTC · same data as the website and mobile app. KAOS does not place orders on this account.</div>
      ${table('Balances',['Asset','Available','On hold'],rows(d.balances,['currency','available','hold'],'No non-zero balances'))}
      ${table('Open orders',['Market','Side','Type','Status','Filled'],rows(d.open_orders,['product_id','side','order_type','status','filled_size'],'No open orders'))}
      ${table('Recent fills',['Market','Side','Size','Price','Fee'],rows(d.fills,['product_id','side','size','price','commission'],'No fills yet'))}
      <div style="margin-top:8px">Fee tier: ${esc(d.fees.tier||'–')} · maker ${esc(d.fees.maker_rate??'–')} · taker ${esc(d.fees.taker_rate??'–')}</div>`;
  }
  let timer=null;
  document.addEventListener('click',e=>{
    const nav=e.target.closest&&e.target.closest('[data-kaos-view]');
    if(!nav)return;
    clearInterval(timer);
    if(nav.dataset.kaosView==='coinbase'){load();timer=setInterval(()=>{if(!document.hidden)load();},15000);}
  });
})();
