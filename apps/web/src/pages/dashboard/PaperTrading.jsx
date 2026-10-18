import React, { useCallback, useEffect, useState } from "react";
import { api, errMsg } from "../../lib/api";
import { StatusBadge } from "../../components/Brand";
import { Button } from "../../components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { toast } from "sonner";
import { FlaskConical, ShieldAlert } from "lucide-react";

const STARTING_BALANCE = 100;
const OPEN = ["SUBMITTED", "PARTIALLY_FILLED", "FILLED"];
const field = "w-full rounded border border-[#2E2E2E] bg-[#080808] px-3 py-2 font-mono text-sm text-white";

export default function PaperTrading() {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ symbol: "BTC-USD", asset_class: "CRYPTO_SPOT", side: "BUY", quantity: "10", quote_price: "" });
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get("/api/v1/paper/orders").then((r) => setData(r.data)).catch((e) => toast.error(errMsg(e))), []);
  useEffect(() => { load(); }, [load]);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await api.post("/api/v1/paper/orders", form);
      toast.success(`Paper order ${r.data.state}`);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
      load();
    }
  };

  if (!data) return <p className="text-slate-500">Loading…</p>;
  const exposure = data.orders.filter((o) => OPEN.includes(o.state) && o.side === "BUY").reduce((s, o) => s + Number(o.quantity), 0);

  return (
    <div>
      <h1 className="mb-2 font-heading text-2xl font-bold tracking-wide">Paper Trading</h1>
      <div className="mb-6 flex items-start gap-2 rounded border border-[#D4AF37]/40 bg-[#D4AF37]/5 p-3 text-sm text-slate-300" data-testid="paper-disclaimer">
        <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-[#D4AF37]" />
        <span>Simulation only. Orders never reach a broker and no money moves. Until an authorized market-data feed is connected, you enter the quote price yourself, so results are not market fills or real performance.</span>
      </div>
      {data.kill_switch && (
        <div className="mb-6 flex items-center gap-2 rounded border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-300" data-testid="kill-switch-banner">
          <ShieldAlert className="h-4 w-4" /> Emergency stop is active. All paper orders are blocked by an administrator.
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-3">
        <form onSubmit={submit} className="card-surface space-y-3 p-5" data-testid="paper-order-form">
          <h3 className="font-heading font-semibold">New paper order</h3>
          <label className="block"><span className="label-mono">Symbol</span><input data-testid="paper-symbol" className={field} value={form.symbol} onChange={set("symbol")} required maxLength={30} /></label>
          <label className="block"><span className="label-mono">Asset class</span>
            <select className={field} value={form.asset_class} onChange={set("asset_class")}><option>CRYPTO_SPOT</option><option>FOREX</option><option>EQUITY</option></select></label>
          <label className="block"><span className="label-mono">Side</span>
            <select data-testid="paper-side" className={field} value={form.side} onChange={set("side")}><option>BUY</option><option>SELL</option></select></label>
          <label className="block"><span className="label-mono">Notional (USD)</span><input data-testid="paper-quantity" className={field} type="number" min="0.01" step="0.01" value={form.quantity} onChange={set("quantity")} required /></label>
          <label className="block"><span className="label-mono">Quote price (manual)</span><input data-testid="paper-quote" className={field} type="number" min="0.00000001" step="any" placeholder="e.g. 67000" value={form.quote_price} onChange={set("quote_price")} required /></label>
          <Button data-testid="paper-submit" disabled={busy || data.kill_switch} className="w-full bg-[#22C55E] font-semibold text-black">{busy ? "Submitting…" : "Place paper order"}</Button>
        </form>
        <div className="space-y-4 lg:col-span-2">
          <div className="grid grid-cols-3 gap-4">
            {[["Paper balance", `$${STARTING_BALANCE}`], ["Open exposure", `$${exposure.toFixed(2)}`], ["Available", `$${Math.max(STARTING_BALANCE - exposure, 0).toFixed(2)}`]].map(([l, v]) => (
              <div key={l} className="card-surface p-4"><div className="label-mono">{l}</div><div className="mt-1 font-mono text-2xl font-bold text-[#D4AF37]" data-testid={`paper-${l.split(" ")[0].toLowerCase()}`}>{v}</div></div>
            ))}
          </div>
          <OrdersTable title="Paper orders" rows={data.orders} testid="paper-orders" />
          <OrdersTable title="Rejected by risk checks" rows={data.rejected} testid="paper-rejected" reason />
        </div>
      </div>
    </div>
  );
}

function OrdersTable({ title, rows, testid, reason }) {
  return (
    <div className="card-surface overflow-x-auto p-0" data-testid={testid}>
      <div className="border-b border-[#2E2E2E] p-4"><h3 className="font-heading font-semibold">{title}</h3></div>
      <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Time</TableHead><TableHead>Symbol</TableHead><TableHead>Side</TableHead><TableHead>Notional</TableHead><TableHead>Quote</TableHead><TableHead>{reason ? "Reason" : "State"}</TableHead></TableRow></TableHeader>
        <TableBody>
          {rows.length === 0 && <TableRow><TableCell colSpan={6} className="py-6 text-center text-slate-500">None yet</TableCell></TableRow>}
          {rows.map((o, i) => (
            <TableRow key={`${o.client_order_id}-${i}`} className="border-[#2E2E2E]">
              <TableCell className="font-mono text-xs text-slate-400">{o.created_at?.slice(0, 19).replace("T", " ")}</TableCell>
              <TableCell className="font-mono">{o.symbol}</TableCell><TableCell>{o.side}</TableCell>
              <TableCell className="font-mono">${o.quantity}</TableCell><TableCell className="font-mono text-slate-400">{o.quote_price}</TableCell>
              <TableCell>{reason ? <span className="text-xs text-red-300">{o.reason}</span> : <StatusBadge value={o.state} />}</TableCell>
            </TableRow>
          ))}
        </TableBody></Table>
    </div>
  );
}
