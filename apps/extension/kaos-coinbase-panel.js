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
    if(!st.data.connected){el.textContent='Coinbase is not connected. Connect on the KAOS website.';await loadOtherBrokers(el);return;}
    const a=await call('/broker-connections/coinbase/accounts');
    if(!a||!a.ok){el.innerHTML=`<span style="color:#f5b041">Coinbase unavailable: ${esc((a&&a.data&&a.data.detail)||(a&&a.error)||'error')}</span>`;return;}
    const d=a.data;
    el.innerHTML=`<b style="color:#7DB8FF">COINBASE ADVANCED · READ-ONLY · key ${esc(d.key_hint)}</b> <b style="color:#f5b041">UNVERIFIED: not yet tested against a real Coinbase account</b>
      <div style="color:#8b96a5;margin:4px 0">Live from Coinbase Advanced API · fetched ${esc(String(d.fetched_at).slice(11,19))} UTC · same data as the website and mobile app. KAOS does not place orders on this account.</div>
      <div style="margin-top:6px">Buying power: $${esc(d.buying_power_usd??'–')}</div>
      ${table('Positions',['Market','Qty','Value $','Unreal. P&L'],rows(d.positions,['product_id','quantity','market_value','unrealized_pnl'],'No crypto holdings'))}
      ${table('Balances',['Asset','Available','On hold'],rows(d.balances,['currency','available','hold'],'No non-zero balances'))}
      ${table('Open orders',['Market','Side','Type','Status','Filled'],rows(d.open_orders,['product_id','side','order_type','status','filled_size'],'No open orders'))}
      ${table('Recent fills',['Market','Side','Size','Price','Fee'],rows(d.fills,['product_id','side','size','price','commission'],'No fills yet'))}
      <div style="margin-top:8px">Fee tier: ${esc(d.fees.tier||'–')} · maker ${esc(d.fees.maker_rate??'–')} · taker ${esc(d.fees.taker_rate??'–')}</div>`;
    await loadOtherBrokers(el);
  }
  // Other linked brokers are read-only practice/paper views. No credentials or order actions in extension.
  async function loadOtherBrokers(el) {
    const links=await call('/broker-connections');
    if(!links?.ok || !Array.isArray(links.data?.connections))return;
    for(const brokerId of ['alpaca','oanda']){
      const saved=links.data.connections.find(c=>c.broker===brokerId && c.verified);
      if(!saved)continue;
      const part=document.createElement('section');
      part.style.marginTop='14px';
      const heading=document.createElement('b');
      heading.textContent=brokerId==='alpaca'?'ALPACA PAPER · READ-ONLY':'OANDA PRACTICE · READ-ONLY';
      part.appendChild(heading);
      const response=await call('/broker-connections/'+brokerId+'/account');
      const line=document.createElement('div');
      line.style.marginTop='4px';
      if(!response?.ok){
        line.textContent='Account currently unavailable. Manage connection on the KAOS website.';
      }else{
        const d=response.data||{};
        const summary=d.account||{};
        line.textContent='Fetched '+(d.fetched_at||'unknown')+' · '+Object.entries(summary)
          .filter(([k])=>['currency','cash','buying_power','equity','balance','NAV','marginAvailable'].includes(k))
          .map(([k,v])=>k+': '+String(v)).join(' · ');
        const counts=document.createElement('div');
        counts.textContent='Positions: '+(d.positions||[]).length+' · Orders: '+(d.orders||[]).length;
        part.appendChild(counts);
      }
      part.appendChild(line);
      el.appendChild(part);
    }
  }
  let timer=null;
  document.addEventListener('click',e=>{
    const nav=e.target.closest&&e.target.closest('[data-kaos-view]');
    if(!nav)return;
    clearInterval(timer);
    if(nav.dataset.kaosView==='coinbase'){load();timer=setInterval(()=>{if(!document.hidden)load();},15000);}
  });
})();
