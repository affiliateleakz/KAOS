import React, { useEffect, useState } from "react";
import { api, errMsg } from "../../lib/api";
import { StatusBadge } from "../../components/Brand";
import { Button } from "../../components/ui/button";
import { Switch } from "../../components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { toast } from "sonner";
import { Copy, Brain, Share2, TrendingUp, Trophy } from "lucide-react";

const H = ({ children }) => <h1 className="mb-6 font-heading text-2xl font-bold tracking-wide">{children}</h1>;
const Stat = ({ l, v }) => (<div className="card-surface p-4"><div className="label-mono">{l}</div><div className="mt-1 font-mono text-2xl font-bold text-[#D4AF37]">{v}</div></div>);

function LedgerCard({ ledger }) {
  const b = ledger.balance;
  return (
    <div className="card-surface mt-6 p-0 overflow-x-auto" data-testid="affiliate-ledger">
      <div className="flex flex-wrap items-center gap-2 border-b border-[#2E2E2E] p-4">
        <TrendingUp className="h-5 w-5 text-[#D4AF37]" /><h3 className="font-heading font-semibold">3-Level Commission Ledger</h3>
        <span className="rounded bg-[#D4AF37]/15 px-2 py-0.5 font-mono text-[10px] uppercase text-[#D4AF37]" data-testid="ledger-tier">{ledger.tier} tier</span>
        <span className="font-mono text-xs text-slate-500" data-testid="ledger-note">{ledger.note}</span>
      </div>
      <div className="grid grid-cols-2 gap-3 p-4 md:grid-cols-4">
        <Stat l="In 30-day hold" v={`$${b.pending}`} /><Stat l="Available (preview)" v={`$${b.available}`} />
        <Stat l="Reversed" v={`$${b.reversed}`} /><Stat l="Paid out" v={`$${b.paid}`} />
      </div>
      <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Date</TableHead><TableHead>Level</TableHead><TableHead>Your tier</TableHead><TableHead>Rate</TableHead><TableHead>Payment</TableHead><TableHead>Amount</TableHead><TableHead>Type</TableHead></TableRow></TableHeader>
        <TableBody>
          {ledger.entries.length === 0 && <TableRow><TableCell colSpan={7} className="py-6 text-center text-slate-500">No ledger entries yet</TableCell></TableRow>}
          {ledger.entries.map((e) => (
            <TableRow key={e.entry_id} className="border-[#2E2E2E]">
              <TableCell className="font-mono text-xs text-slate-400">{e.created_at.slice(0, 10)}</TableCell>
              <TableCell className="font-mono">L{e.level}</TableCell><TableCell className="capitalize">{e.recipient_tier}</TableCell>
              <TableCell className="font-mono">{e.rate_pct}%</TableCell><TableCell className="font-mono text-slate-400">${e.base_amount}</TableCell>
              <TableCell className={`font-mono ${e.amount.startsWith("-") ? "text-red-400" : "text-[#22C55E]"}`}>${e.amount}</TableCell>
              <TableCell className="capitalize">{e.kind}</TableCell>
            </TableRow>
          ))}
        </TableBody></Table>
    </div>
  );
}

// ---------- Member Affiliate ----------
export function AffiliatePage() {
  const [d, setD] = useState(null);
  const [assets, setAssets] = useState([]);
  const [lb, setLb] = useState([]);
  const [ledger, setLedger] = useState(null);
  const load = () => {
    api.get("/api/affiliate/overview").then((r) => setD(r.data)).catch(() => {});
    api.get("/api/affiliate/ledger").then((r) => setLedger(r.data)).catch(() => {});
  };
  useEffect(() => {
    load();
    api.get("/api/affiliate/marketing").then((r) => setAssets(r.data)).catch(() => {});
    api.get("/api/affiliate/leaderboard").then((r) => setLb(r.data)).catch(() => {});
  }, []);
  const activate = async () => { try { await api.post("/api/affiliate/activate"); toast.success("Affiliate account activated"); load(); } catch (e) { toast.error(errMsg(e)); } };
  const copy = (t) => { navigator.clipboard.writeText(t); toast.success("Copied"); };
  if (!d) return <p className="text-slate-500">Loading…</p>;
  if (!d.active) return (
    <div><H>Affiliate Program</H>
      <div className="card-surface p-8 text-center">
        <Share2 className="mx-auto h-10 w-10 text-[#D4AF37]" />
        <p className="mt-4 text-slate-400">Earn commissions promoting KAOS Trading. Activate your affiliate account to get your referral link.</p>
        <Button data-testid="affiliate-activate-button" onClick={activate} className="mt-6 bg-[#22C55E] text-black font-semibold">Become an Affiliate</Button>
      </div>
    </div>
  );
  return (
    <div><H>Affiliate Program</H>
      <div className="card-surface mb-6 p-5">
        <div className="label-mono">Your referral link</div>
        <div className="mt-2 flex items-center gap-2">
          <code className="flex-1 truncate rounded bg-[#080808] border border-[#2E2E2E] px-3 py-2 text-sm text-[#D4AF37]" data-testid="affiliate-link">{d.referralLink}</code>
          <Button data-testid="copy-affiliate-link" onClick={() => copy(d.referralLink)} className="bg-[#22C55E] text-black"><Copy className="h-4 w-4" /></Button>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
        <Stat l="Clicks" v={d.clicks} /><Stat l="Signups" v={d.signups} /><Stat l="Paying" v={d.payingReferrals} />
        <Stat l="Conv %" v={d.conversionRate} /><Stat l="Pending" v={`$${d.pending}`} /><Stat l="Payable" v={`$${d.payable}`} /><Stat l="Lifetime" v={`$${d.lifetime}`} />
      </div>
      {ledger && <LedgerCard ledger={ledger} />}
      {d.shareFunnel && (
        <div className="card-surface mt-6 p-5" data-testid="share-funnel">
          <div className="flex items-center gap-2"><Share2 className="h-5 w-5 text-[#D4AF37]" /><h3 className="font-heading font-semibold">Signal Share Funnel</h3>
            <span className="font-mono text-xs text-slate-500">how your shared KAOS signals turn into paying referrals</span></div>
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              { l: "Signals Shared", v: d.shareFunnel.shares, sub: null },
              { l: "Share Clicks", v: d.shareFunnel.clicks, sub: null },
              { l: "Signups", v: d.shareFunnel.signups, sub: `${d.shareFunnel.clickToSignup}% of clicks` },
              { l: "Paying", v: d.shareFunnel.paying, sub: `${d.shareFunnel.signupToPaying}% of signups` },
            ].map((step, i) => (
              <div key={step.l} className="relative rounded-md border border-[#2E2E2E] bg-[#0c0c0c] p-4">
                <div className="label-mono">{step.l}</div>
                <div className="mt-1 font-mono text-2xl font-bold text-[#D4AF37]" data-testid={`funnel-${i}`}>{step.v}</div>
                {step.sub && <div className="mt-1 font-mono text-[10px] text-[#22C55E]">{step.sub}</div>}
                {i < 3 && <div className="absolute -right-2.5 top-1/2 hidden -translate-y-1/2 text-slate-600 md:block">→</div>}
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card-surface p-0 overflow-x-auto"><div className="border-b border-[#2E2E2E] p-4"><h3 className="font-heading font-semibold">Recent Commissions</h3></div>
          <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Plan</TableHead><TableHead>Amount</TableHead><TableHead>Status</TableHead></TableRow></TableHeader>
            <TableBody>{d.recentCommissions.length === 0 && <TableRow><TableCell colSpan={3} className="py-6 text-center text-slate-500">None yet</TableCell></TableRow>}
              {d.recentCommissions.map((c) => (<TableRow key={c.id} className="border-[#2E2E2E]"><TableCell>{c.planId}</TableCell><TableCell className="font-mono text-[#D4AF37]">${c.amount}</TableCell><TableCell><StatusBadge value={c.status} /></TableCell></TableRow>))}</TableBody></Table></div>
        <div className="card-surface p-5"><h3 className="font-heading font-semibold">Marketing Center</h3>
          <div className="mt-3 space-y-2">
            {assets.length === 0 && <p className="text-sm text-slate-500">No marketing assets yet.</p>}
            {assets.map((a) => (<div key={a.id} className="flex items-center justify-between border-b border-[#2E2E2E] py-2">
              <div><div className="text-sm text-white">{a.title}</div><div className="font-mono text-xs text-slate-500">{a.type}</div></div>
              {a.copy && <Button size="sm" variant="outline" className="border-[#3A3A3A] bg-transparent text-white" onClick={() => copy(a.copy)}>Copy text</Button>}
            </div>))}
          </div>
        </div>
      </div>
      <div className="card-surface mt-6 p-0 overflow-x-auto" data-testid="affiliate-leaderboard">
        <div className="flex items-center gap-2 border-b border-[#2E2E2E] p-4">
          <Trophy className="h-5 w-5 text-[#D4AF37]" /><h3 className="font-heading font-semibold">Top Sharers Leaderboard</h3>
          <span className="font-mono text-xs text-slate-500">ranked by paying referrals</span>
        </div>
        <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>#</TableHead><TableHead>Trader</TableHead><TableHead>Signups</TableHead><TableHead>Paying</TableHead><TableHead>Earned</TableHead></TableRow></TableHeader>
          <TableBody>
            {lb.length === 0 && <TableRow><TableCell colSpan={5} className="py-6 text-center text-slate-500">No paying referrals yet — be the first to top the board.</TableCell></TableRow>}
            {lb.map((r) => (
              <TableRow key={r.rank} className={`border-[#2E2E2E] ${r.isYou ? "bg-[#D4AF37]/5" : ""}`} data-testid={`leaderboard-row-${r.rank}`}>
                <TableCell className="font-mono">{r.rank <= 3 ? ["🥇", "🥈", "🥉"][r.rank - 1] : r.rank}</TableCell>
                <TableCell className="text-white">{r.name}{r.isYou && <span className="ml-2 rounded bg-[#22C55E]/15 px-2 py-0.5 font-mono text-[10px] text-[#22C55E]">YOU</span>}</TableCell>
                <TableCell className="font-mono text-slate-400">{r.signups}</TableCell>
                <TableCell className="font-mono text-[#D4AF37]">{r.paying}</TableCell>
                <TableCell className="font-mono text-[#22C55E]">${r.earned}</TableCell>
              </TableRow>
            ))}
          </TableBody></Table>
      </div>
    </div>
  );
}
export function AIPage() {
  const [d, setD] = useState(null);
  const load = () => api.get("/api/ai/overview").then((r) => setD(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const setConsent = async (v) => { try { await api.post("/api/v1/ai/consent", { consent: v }); toast.success(v ? "Contributing to Collective Learning" : "Opted out"); load(); } catch (e) { toast.error(errMsg(e)); } };
  if (!d) return <p className="text-slate-500">Loading…</p>;
  return (
    <div><H>KAOS AI</H>
      <div className="mb-6 rounded-lg border border-[#D4AF37]/20 bg-[#D4AF37]/5 p-3 text-xs text-[#D4AF37]">KAOS AI is not yet production-trained. Predictions shown are SIMULATED until the trained model is deployed. No guaranteed accuracy.</div>
      <div className="grid gap-4 md:grid-cols-4">
        <div className="card-surface p-5"><Brain className="h-6 w-6 text-[#D4AF37]" /><div className="mt-3 label-mono">Active Model</div><div className="mt-1 font-mono text-sm text-white">{d.activeModel?.version}</div></div>
        <Stat l="Real Samples" v={d.realSamples} /><Stat l="Paper Samples" v={d.paperSamples} />
        <div className="card-surface p-5"><div className="label-mono">Collective Learning</div><div className="mt-2"><StatusBadge value={d.consent ? "ACTIVE" : "NOT_STARTED"} /></div></div>
      </div>
      <div className="card-surface mt-6 p-5">
        <div className="flex items-center justify-between">
          <div><h3 className="font-heading font-semibold">KAOS Collective Learning</h3>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">Contribute anonymized market & trading learning data to help improve KAOS AI. No name, email, credentials, balances or payment info are ever used. You can opt out anytime.</p></div>
          <Switch data-testid="collective-learning-toggle" checked={d.consent} onCheckedChange={setConsent} />
        </div>
      </div>
      <div className="card-surface mt-6 p-0 overflow-x-auto"><div className="border-b border-[#2E2E2E] p-4"><h3 className="font-heading font-semibold">Recent Predictions</h3></div>
        <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Asset</TableHead><TableHead>Prediction</TableHead><TableHead>Confidence</TableHead><TableHead>Model</TableHead><TableHead>Outcome</TableHead></TableRow></TableHeader>
          <TableBody>{d.recentPredictions.length === 0 && <TableRow><TableCell colSpan={5} className="py-6 text-center text-slate-500">No predictions yet</TableCell></TableRow>}
            {d.recentPredictions.map((p) => (<TableRow key={p.id} className="border-[#2E2E2E]"><TableCell className="font-mono text-xs">{p.asset}</TableCell><TableCell className={p.prediction === "BUY" ? "text-green-400" : "text-[#C62828]"}>{p.prediction}</TableCell><TableCell className="font-mono text-xs">{p.confidence}</TableCell><TableCell className="font-mono text-xs">{p.model_version}</TableCell><TableCell className="font-mono text-xs">{p.outcome || "—"}</TableCell></TableRow>))}</TableBody></Table></div>
    </div>
  );
}
