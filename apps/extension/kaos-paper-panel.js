// KAOS paper session in the extension: reads/writes the same server-side paper account as the website
// (broker/session, live quote, KAOS Strategy signal + risk decision, market-price paper fills, fees, journal).
// Paper only. No broker orders are placed from here.
(function(){
  const root=()=>document.getElementById('kaos-paper-panel');
  const call=(path,method,payload)=>chrome.runtime.sendMessage({type:'KAOS_PAPER',path,method:method||'GET',payload});
  const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const money=v=>'$'+Number(v||0).toFixed(2);
  let busy=false;
  async function load(){
    const el=root(); if(!el)return;
    const [ses,ord,sig]=await Promise.all([call('/paper/session'),call('/paper/orders'),call('/paper/signals')]);
    if(!ses||!ses.ok){el.textContent=(ses&&ses.status===401)||(ses&&/expired/.test(ses.error||''))?'Sign in to KAOS to load your paper session.':'KAOS paper session unavailable: '+esc(ses&&(ses.error||ses.status));return;}
    const s=ses.data, q=await call('/paper/quote/'+s.symbol);
    const book=(ord.data&&ord.data.book)||{}, orders=(ord.data&&ord.data.orders)||[], sigs=(sig.data&&sig.data.signals)||[], last=sigs[0];
    el.innerHTML=`<div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><b style="color:#7DB8FF">PAPER SESSION · ${esc(s.symbol)} · ${esc(s.broker)}</b>
      <span>${q&&q.ok?`bid ${esc(q.data.bid)} · ask ${esc(q.data.ask)} · ${esc(String(q.data.quote_time).slice(11,19))} UTC`:'no quote'}</span></div>
      <div style="color:#8b96a5;margin:4px 0 8px">Same account, signals and journal as tradingwithkaos.com → Paper Trading. Simulated fills at live Coinbase quotes. No real orders. AI-controlled execution locked.</div>
      <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:8px"><span>Cash ${money(book.cash)}</span><span>Open cost ${money(book.open_cost)}</span><span>Fees ${money(book.fees_paid)}</span><span>Realized P&amp;L ${money(book.realized_pnl)}</span></div>
      <button id="kaos-paper-run" ${busy?'disabled':''} style="background:#2F8CFF;color:#000;border:0;padding:6px 10px;font-weight:700;cursor:pointer">RUN KAOS STRATEGY</button>
      <div style="margin-top:8px;border:1px solid #2a3940;padding:8px">${last?`<b>${esc(last.action)}</b> ${esc(last.symbol)} · ${esc(last.setup)} · ${esc(last.status)}<br>${last.reasons.map(esc).join('<br>')}<br>
        <span style="color:${last.risk.approved?'#7DB8FF':'#f5c26b'}">Risk manager ${last.risk.approved?'approved':'rejected'}: ${esc(last.risk.reason)}</span>
        ${last.status==='PENDING'?`<br><button id="kaos-paper-exec" data-id="${esc(last.signal_id)}" style="margin-top:6px;background:#22C55E;color:#000;border:0;padding:5px 9px;font-weight:700;cursor:pointer">EXECUTE PAPER TRADE AT MARKET</button>`:''}`:'No signal yet.'}</div>
      <div style="margin-top:8px"><b>Journal</b>${orders.slice(0,8).map(o=>`<div>${esc(String(o.created_at).slice(0,19).replace('T',' '))} · ${esc(o.side)} ${esc(o.symbol)} ${money(o.quantity)} @ ${esc(o.fill_price)} · fee ${money(o.fee)} · ${o.execution_kind==='market_data_paper'?'market data':'manual demo'}</div>`).join('')||'<div>No paper orders.</div>'}</div>`;
    document.getElementById('kaos-paper-run').onclick=async()=>{busy=true;await call(`/paper/signals/${s.symbol}?granularity=${s.granularity}`,'POST',{notional:s.notional});busy=false;load();};
    const ex=document.getElementById('kaos-paper-exec');
    if(ex)ex.onclick=async()=>{busy=true;const r=await call(`/paper/signals/${ex.dataset.id}/execute`,'POST');busy=false;if(!r.ok)alert((r.data&&r.data.detail)||r.error);load();};
  }
  function visible(){const p=document.getElementById('terminal-paper');return p&&p.classList.contains('active');}
  document.addEventListener('click',e=>{const t=e.target.closest&&e.target.closest('.terminal-tab[data-page="paper"]');if(t)setTimeout(load,50);});
  setInterval(()=>{if(visible()&&!busy)load();},10000);
})();
