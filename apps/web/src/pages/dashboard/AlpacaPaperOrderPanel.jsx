import AlpacaPaperStockChart from "./AlpacaPaperStockChart";
import React,{useCallback,useEffect,useState} from "react";
import {api,errMsg} from "../../lib/api";

const textBox="w-full rounded border border-[#48402E] bg-[#080808] p-2 text-sm text-white";

export default function AlpacaPaperOrderPanel({showChart=true}){
  const [symbol,setSymbol]=useState("AAPL");
  const [notional,setNotional]=useState("10");
  const [preview,setPreview]=useState(null);
  const [orders,setOrders]=useState([]);
  const [result,setResult]=useState(null);
  const [error,setError]=useState("");
  const [review,setReview]=useState(null);
  const [reviewError,setReviewError]=useState("");
  const [readiness,setReadiness]=useState(null);
  const [readinessError,setReadinessError]=useState("");
  const [recovery,setRecovery]=useState(null);
  const [ledger,setLedger]=useState(null);
  const [fillAudit,setFillAudit]=useState(null);
  const [fifoAudit,setFifoAudit]=useState(null);
  const [safetyError,setSafetyError]=useState("");
  const [safetyBusy,setSafetyBusy]=useState(false);
  const [busy,setBusy]=useState(false);
  const load=useCallback(async()=>{
    try {const r=await api.get("/api/v1/alpaca-paper/orders/kaos");setOrders(r.data.orders||[]);}
    catch(e){if(e?.response?.status!==503&&e?.response?.status!==403)setError(errMsg(e));}
  },[]);
  useEffect(()=>{load();},[load]);
  const loadReview=useCallback(async()=>{
    try{
      const {data}=await api.get("/api/v1/alpaca-paper/research-review");
      setReview(data);setReviewError("");
    }catch(e){
      setReview(null);
      if(e?.response?.status!==403&&e?.response?.status!==503){
        setReviewError(errMsg(e)||"AI paper research review unavailable");
      }else{
        setReviewError("AI review is available only to the KAOS owner during beta.");
      }
    }
  },[]);
  useEffect(()=>{loadReview();},[loadReview]);

  const loadReadiness=useCallback(async()=>{
    try{
      const r=await api.get("/api/v1/alpaca-paper/ai-paper-readiness",{params:{symbol:symbol.trim().toUpperCase()}});
      setReadiness(r.data);setReadinessError("");
    }catch(e){
      setReadiness(null);
      setReadinessError(e?.response?.status===403?"Owner-only AI readiness view":
        errMsg(e)||"AI readiness unavailable");
    }
  },[symbol]);
  useEffect(()=>{loadReadiness();},[loadReadiness]);
  const checkPaperSafety=async()=>{
    setSafetyBusy(true);setSafetyError("");
    try{
      const results=await Promise.all([
        api.post("/api/v1/alpaca-paper/orders/recovery-audit",{}),
        api.get("/api/v1/alpaca-paper/risk-ledger-readiness"),
        api.get("/api/v1/alpaca-paper/fill-audit"),
        api.get("/api/v1/alpaca-paper/fifo-gross-research")
      ]);
      setRecovery(results[0].data);setLedger(results[1].data);setFillAudit(results[2].data);setFifoAudit(results[3].data);
      await load();
    }catch(e){setSafetyError(errMsg(e)||"Paper recovery or ledger checks unavailable");}
    finally{setSafetyBusy(false);}
  };
  const previewOrder=async(e)=>{
    e.preventDefault();setBusy(true);setError("");setPreview(null);setResult(null);
    try {
      const r=await api.post("/api/v1/alpaca-paper/orders/preview",{
        symbol:symbol.trim().toUpperCase(),notional:String(notional)
      });
      setPreview(r.data);
    } catch(e){setError(errMsg(e)||"Paper preview unavailable");}
    finally{setBusy(false);}
  };
  const confirm=async()=>{
    if(!preview?.preview_id)return;
    if(!window.confirm("Send this BUY order to your ALPACA PAPER account? It cannot use real money."))return;
    setBusy(true);setError("");setResult(null);
    try {
      const r=await api.post("/api/v1/alpaca-paper/orders/confirm",{preview_id:preview.preview_id});
      setResult(r.data);setPreview(null);await load();
    }catch(e){
      setError(errMsg(e)||"Paper broker response unknown. Check order history and reconcile before submitting again.");
      setPreview(null);await load();
    }finally{setBusy(false);}
  };
  const reconcile=async(cid)=>{
    setBusy(true);setError("");
    try{
      const r=await api.post("/api/v1/alpaca-paper/orders/reconcile",{client_order_id:cid});
      setResult(r.data);await load();
    }catch(e){setError(errMsg(e)||"Broker reconciliation unavailable");}
    finally{setBusy(false);}
  };
  return <section className="card-surface mb-6 space-y-4 p-5" data-testid="alpaca-paper-stock-order">
    <div>
      <h2 className="text-lg font-semibold text-[#D4AF37]">Alpaca Paper — Test a Stock Order</h2>
      <p className="mt-1 text-xs text-slate-400">Owner-only beta · manual BUY · US equities only · $1–$25 · market hours · real IEX quote, Alpaca simulated execution</p>
    </div>
    {showChart&&<AlpacaPaperStockChart symbol={symbol}/>}
    <section className="space-y-3 rounded border border-[#48402E] p-3" data-testid="alpaca-paper-safety-audit">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold text-[#D4AF37]">Broker recovery &amp; daily risk ledger</h3>
          <p className="text-xs text-slate-400">Read-only broker reconciliation · no order resubmissions</p>
        </div>
        <button type="button" disabled={safetyBusy} onClick={checkPaperSafety}
          className="rounded border border-[#D4AF37] px-3 py-2 text-xs text-[#D4AF37] disabled:opacity-50">
          {safetyBusy?"Checking…":"Audit paper safety"}
        </button>
      </div>
      {safetyError&&<p role="alert" className="text-xs text-amber-300">{safetyError}</p>}
      {recovery&&<p className="text-xs text-slate-300">Orders reconciled: {recovery.checked} · still unresolved: {recovery.unresolved} · new orders sent: {recovery.orders_submitted}</p>}
      {fillAudit&&<>
        <p className="text-xs text-slate-300">Broker fill audit: {fillAudit.matched_fills} KAOS-matched fill activities across {fillAudit.matched_orders} orders · {fillAudit.unmatched_broker_fills} unrelated broker fills</p>
        <p className="text-xs text-amber-300">Historical completeness: {fillAudit.partial_history?"Incomplete: broker pagination limit reached":"Returned activity pages exhausted"} · rejected records: {fillAudit.rejected_records} · realized P&amp;L: not verified</p>
        <div className="max-h-40 overflow-auto space-y-1">
          {(fillAudit.rows||[]).slice(0,12).map((r,i)=><p key={r.client_order_id||i} className="border-b border-[#292929] py-1 font-mono text-xs">{r.symbol}: {r.fills} fills · qty {r.filled_qty} · gross buy ${r.gross_buy_notional} · gross sell ${r.gross_sell_notional}</p>)}
        </div>
      </>}
      {fifoAudit&&<div className="space-y-2 rounded border border-[#48402E] p-3" data-testid="alpaca-fifo-gross-research">
        <h4 className="font-semibold text-[#D4AF37]">Alpaca Paper FIFO — provisional gross P&amp;L</h4>
        <p className="font-mono text-sm">Gross matched-lot P&amp;L (unverified): ${fifoAudit.gross_fifo_pnl_provisional}</p>
        <p className="text-xs text-amber-300">Verified realized net P&amp;L: unavailable. Do not use this estimate for risk approval or performance claims.</p>
        <p className="text-xs text-slate-400">Outstanding verification: {(fifoAudit.blockers||[]).join(", ")}</p>
        <div className="max-h-40 space-y-1 overflow-auto">
          {(fifoAudit.symbol_summaries||[]).map(s=><p key={s.symbol} className="border-b border-[#292929] py-1 font-mono text-xs">
            {s.symbol} · gross ${s.gross_fifo_pnl} · closed qty {s.gross_closed_qty} · unknown sell qty {s.unpaired_sell_qty}
          </p>)}
        </div>
      </div>}
      {ledger&&<>
        <p className="text-xs text-amber-300">Verified daily realized loss: {ledger.realized_loss_limit_verified?"Yes":"Not yet"} · automated paper trading disabled</p>
        <p className="text-xs text-slate-400">Risk ledger missing: {ledger.incomplete_requirements?.join(", ")}</p>
        <p className="text-xs text-slate-500">{ledger.note}</p>
      </>}
    </section>

    <section className="rounded border border-[#48402E] p-3 space-y-2" data-testid="kaos-alpaca-ai-paper-readiness">
      <div className="flex flex-wrap justify-between gap-2">
        <div><h3 className="font-semibold text-[#D4AF37]">AI-to-Alpaca Paper Readiness</h3>
          <p className="text-xs text-slate-400">Bot-controlled research checks · no automatic order submission</p></div>
        <button type="button" onClick={loadReadiness} className="rounded border border-[#D4AF37] px-2 py-1 text-xs text-[#D4AF37]">Check readiness</button>
      </div>
      {readinessError&&<p className="text-xs text-amber-300">{readinessError}</p>}
      {readiness&&<>
        <p className="text-xs text-slate-300">{readiness.checked} historical forecasts checked · AI paper execution disabled</p>
        {!readiness.evaluations?.length&&<p className="text-sm text-slate-400">No matching, trained stock AI forecasts are recorded yet.</p>}
        {(readiness.evaluations||[]).slice(0,8).map((r,i)=><article key={r.forecast_id||i} className="rounded border border-[#302F2C] p-2 text-xs">
          <p><strong>{r.symbol} · {r.direction||"Unknown"}</strong> · {r.candidate_action} · {r.paper_status}</p>
          <p className="mt-1 text-slate-300">Research gates: {r.observational_checks_passed?"Pass":"Not passed"}</p>
          <p className="mt-1 text-amber-300">Blocked by: {r.reasons?.join(", ")}</p>
        </article>)}
        <p className="text-xs text-amber-300">Passing research checks does not authorize a trade. The bot must independently verify live paper quotes, risk limits, daily loss and fees before future automated testing.</p>
      </>}
    </section>

    <form onSubmit={previewOrder} className="flex flex-wrap items-end gap-3">
      <label className="text-xs">Stock ticker
        <input className={textBox+" mt-1"} value={symbol} maxLength={6} onChange={e=>{setSymbol(e.target.value.toUpperCase());setPreview(null);}} required placeholder="AAPL"/>
      </label>
      <label className="text-xs">Paper order notional (USD)
        <input className={textBox+" mt-1"} type="number" min="1" max="25" step=".01" value={notional} onChange={e=>{setNotional(e.target.value);setPreview(null);}} required />
      </label>
      <button disabled={busy} type="submit" className="rounded bg-[#D4AF37] px-4 py-2 text-sm font-semibold text-black disabled:opacity-50">
        {busy?"Checking…":"Preview paper order"}
      </button>
    </form>
    {error&&<p role="alert" className="rounded border border-red-600 p-3 text-sm text-red-300">{error}</p>}
    {preview&&<div className="rounded border border-[#D4AF37]/40 p-4 text-sm space-y-2">
      <p className="font-semibold text-[#D4AF37]">Confirm Alpaca Paper BUY · {preview.symbol} · ${preview.notional}</p>
      <p>Fresh IEX quote ask: ${preview.quote?.ask} · source: {preview.quote?.source}</p>
      <p>Risk status: {preview.risk} · market open: {String(preview.market_open)}</p>
      <p className="text-xs text-amber-300">Preview expires in approximately 25 seconds. Alpaca paper fills can differ from this quote. No AI signal is authorized to submit this order.</p>
      <button type="button" disabled={busy} onClick={confirm} className="rounded bg-[#22C55E] px-4 py-2 font-semibold text-black disabled:opacity-50">
        Confirm BUY in Alpaca Paper
      </button>
    </div>}
    {result&&<p role="status" className="rounded border border-[#D4AF37]/40 p-3 text-sm">
      Broker paper status: {result.broker_status||result.status||"unknown"} · Order: {result.client_order_id}
    </p>}
    <div>
      <div className="mb-2 flex justify-between"><h3 className="font-semibold">KAOS paper order journal</h3>
        <button type="button" onClick={load} className="text-xs text-[#D4AF37]">Refresh</button></div>
      {!orders.length&&<p className="text-xs text-slate-400">No KAOS-submitted Alpaca paper orders.</p>}
      <div className="max-h-52 overflow-auto">
        {orders.map((o,i)=><div key={o.client_order_id||i} className="flex flex-wrap items-center justify-between gap-2 border-b border-[#292929] py-2 text-xs">
          <span>{o.symbol} · ${o.notional} · {o.broker_status||o.state}</span>
          {o.client_order_id&&<button type="button" disabled={busy} className="rounded border border-[#D4AF37]/40 px-2 py-1 text-[#D4AF37]" onClick={()=>reconcile(o.client_order_id)}>Reconcile</button>}
        </div>)}
      </div>
    </div>
    <section className="space-y-3 rounded border border-[#48402E] p-4" data-testid="alpaca-paper-ai-research-review">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold text-[#D4AF37]">KAOS AI versus Alpaca Paper</h3>
          <p className="text-xs text-slate-400">Compare independent research forecasts to your manually placed paper orders</p>
        </div>
        <button className="rounded border border-[#D4AF37] px-2 py-1 text-xs text-[#D4AF37]" onClick={loadReview} type="button">Refresh review</button>
      </div>
      {reviewError&&<p role="status" className="text-xs text-amber-300">{reviewError}</p>}
      {review&&<>
        <p className="text-xs text-slate-300">{review.orders_reviewed} manual orders · {review.matched_prior_research_forecasts} with an earlier matching AI forecast · {review.broker_reported_filled_orders} broker-reported filled</p>
        {!review.rows.length&&<p className="text-sm text-slate-400">No eligible manual Alpaca paper orders yet.</p>}
        <div className="max-h-64 space-y-2 overflow-auto">
          {review.rows.slice(0,15).map((r,i)=><div key={r.client_order_id||i} className="rounded border border-[#35302B] p-2 text-xs">
            <p className="font-semibold">{r.symbol} · {r.broker_status} · Manual paper order</p>
            {r.research_forecast
              ? <p className="mt-1 text-slate-300">Prior AI research: {r.research_forecast.bias} · P(up): {(100*Number(r.research_forecast.prob_up)).toFixed(1)}% · outcome: {r.research_forecast.outcome_status||"unknown"}</p>
              : <p className="mt-1 text-slate-400">No eligible earlier research forecast was available.</p>}
          </div>)}
        </div>
        <p className="text-xs text-amber-300">These manual paper orders were not placed by the AI. A matching forecast does not establish a profitable trade; fees, realized P&amp;L and execution attribution are not verified here.</p>
      </>}
    </section>
    <p className="text-xs text-amber-300">Disabled until owner explicitly enables the server flag. An ambiguous broker response is never retried automatically; reconcile it first. This does not place real trades or execute AI signals.</p>
  </section>;
}
