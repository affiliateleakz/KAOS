import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errMsg } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { StatusBadge } from "../../components/Brand";
import { StrategyCard } from "../../components/StrategyCard";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "../../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { toast } from "sonner";
import { Plus, Copy, Trash2, Globe, EyeOff, Lock, ExternalLink, Chrome, CreditCard, Cpu, Trophy } from "lucide-react";

const H = ({ children, action }) => (
  <div className="mb-6 flex items-center justify-between">
    <h1 className="font-heading text-2xl font-bold">{children}</h1>{action}
  </div>
);
const Empty = ({ children }) => <div className="card-surface p-10 text-center text-slate-500">{children}</div>;

// ---------- Overview ----------
export function Overview() {
  const [d, setD] = useState(null);
  const [rank, setRank] = useState(null);
  useEffect(() => {
    api.get("/api/dashboard").then((r) => setD(r.data)).catch(() => {});
    api.get("/api/affiliate/my-rank").then((r) => setRank(r.data)).catch(() => {});
  }, []);
  if (!d) return <p className="text-slate-500">Loading…</p>;
  const stats = [
    ["Membership", <StatusBadge value={d.membershipStatus} testid="stat-membership" />],
    ["Affiliate", <StatusBadge value={d.affiliateStatus} testid="stat-affiliate" />],
    ["License", <StatusBadge value={d.license.authorized ? "ACTIVE" : "REVOKED"} testid="stat-license" />],
    ["Devices", <span className="font-mono text-xl text-white">{d.counts.devices}</span>],
  ];
  return (
    <div>
      <H>Dashboard</H>
      {rank?.ranked && (
        <Link to="/dashboard/affiliate" data-testid="rank-badge"
          className="mb-6 flex items-center justify-between rounded-lg border border-[#D4AF37]/30 bg-[#D4AF37]/5 p-4 transition hover:bg-[#D4AF37]/10">
          <div className="flex items-center gap-3">
            <Trophy className="h-5 w-5 text-[#D4AF37]" />
            <p className="text-sm text-[#D4AF37]">
              You're <span className="font-bold">#{rank.rank}</span> on the Top Sharers Leaderboard
              <span className="ml-2 font-mono text-xs text-slate-400">{rank.paying} paying · of {rank.totalAffiliates} affiliates</span>
            </p>
          </div>
          <span className="font-mono text-xs text-slate-400">View leaderboard →</span>
        </Link>
      )}
      {(d.membershipStatus !== "ACTIVE" || d.affiliateStatus !== "VERIFIED") && (
        <div className="mb-6 flex items-center justify-between rounded-lg border border-[#FFB800]/30 bg-[#FFB800]/10 p-4">
          <p className="text-sm text-[#FFB800]">Complete your onboarding to unlock the extension.</p>
          <Link to="/onboarding"><Button className="bg-[#FFB800] text-[#080808] font-semibold">Continue onboarding</Button></Link>
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(([l, v]) => (
          <div key={l} className="card-surface p-5"><div className="label-mono">{l}</div><div className="mt-3">{v}</div></div>
        ))}
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        {[["My Strategies", d.counts.myStrategies], ["Published", d.counts.published], ["Saved", d.counts.saved]].map(([l, v]) => (
          <div key={l} className="card-surface p-5"><div className="label-mono">{l}</div><div className="mt-2 font-mono text-3xl font-bold text-[#D4AF37]">{v}</div></div>
        ))}
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card-surface p-5">
          <h3 className="font-heading font-semibold">Recent Activity</h3>
          <div className="mt-3 space-y-2">
            {d.recentActivity.length === 0 && <p className="text-sm text-slate-500">No activity yet.</p>}
            {d.recentActivity.map((n) => <div key={n.id} className="border-b border-[#2E2E2E] pb-2 text-sm text-slate-400">{n.message}</div>)}
          </div>
        </div>
        <div className="card-surface p-5">
          <h3 className="font-heading font-semibold">Extension</h3>
          <div className="mt-3 font-mono text-sm text-slate-400">
            <div className="flex justify-between border-b border-[#2E2E2E] py-2"><span>Latest version</span><span className="text-white">{d.latestExtension?.version || "—"}</span></div>
            <div className="flex justify-between border-b border-[#2E2E2E] py-2"><span>Renewal</span><span className="text-white">{d.membershipExpiresAt ? new Date(d.membershipExpiresAt).toLocaleDateString() : "—"}</span></div>
            <div className="flex justify-between py-2"><span>Plan</span><span className="text-white">{d.membershipPlan || "—"}</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- My Strategies ----------
const emptyStrat = { name: "", description: "", signalTimeframe: "1m", expiry: "5m", visibility: "PRIVATE" };
export function MyStrategies() {
  const [list, setList] = useState([]);
  const [form, setForm] = useState(emptyStrat);
  const [openNew, setOpenNew] = useState(false);
  const load = () => api.get("/api/strategies").then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const create = async () => {
    try { await api.post("/api/strategies", { ...form, indicators: [] }); setOpenNew(false); setForm(emptyStrat); toast.success("Strategy created (private)"); load(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const publish = async (s) => { try { await api.post(`/api/strategies/${s.id}/publish`, { visibility: "PUBLIC" }); toast.success("Published to community"); load(); } catch (e) { toast.error(errMsg(e)); } };
  const unpublish = async (s) => { try { await api.post(`/api/strategies/${s.id}/unpublish`); toast.success("Unpublished"); load(); } catch (e) { toast.error(errMsg(e)); } };
  const del = async (s) => { try { await api.delete(`/api/strategies/${s.id}`); toast.success("Deleted"); load(); } catch (e) { toast.error(errMsg(e)); } };

  return (
    <div>
      <H action={
        <Dialog open={openNew} onOpenChange={setOpenNew}>
          <DialogTrigger asChild><Button data-testid="new-strategy-button" className="bg-[#22C55E] text-black font-semibold"><Plus className="mr-1 h-4 w-4" />New Strategy</Button></DialogTrigger>
          <DialogContent className="bg-[#0F0F0F] border-[#3A3A3A] text-white">
            <DialogHeader><DialogTitle>New Strategy</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div><Label className="label-mono">Name</Label><Input data-testid="strategy-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1 bg-[#080808] border-[#3A3A3A]" /></div>
              <div><Label className="label-mono">Description</Label><Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1 bg-[#080808] border-[#3A3A3A]" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label className="label-mono">Timeframe</Label><Input value={form.signalTimeframe} onChange={(e) => setForm({ ...form, signalTimeframe: e.target.value })} className="mt-1 bg-[#080808] border-[#3A3A3A]" /></div>
                <div><Label className="label-mono">Expiry</Label><Input value={form.expiry} onChange={(e) => setForm({ ...form, expiry: e.target.value })} className="mt-1 bg-[#080808] border-[#3A3A3A]" /></div>
              </div>
              <p className="text-xs text-slate-500">New strategies are always PRIVATE until you explicitly publish.</p>
            </div>
            <DialogFooter><Button data-testid="strategy-create-submit" onClick={create} disabled={!form.name} className="bg-[#22C55E] text-black font-semibold">Create</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      }>My Strategies</H>
      {list.length === 0 ? <Empty>No strategies yet. Create your first one.</Empty> : (
        <div className="space-y-3">
          {list.map((s) => (
            <div key={s.id} data-testid={`my-strategy-${s.id}`} className="card-surface flex items-center justify-between p-4">
              <div>
                <div className="flex items-center gap-2">
                  <Link to={s.published ? `/community/${s.id}` : "#"} className="font-heading font-semibold text-white">{s.name}</Link>
                  {s.visibility === "PRIVATE" && <Lock className="h-3.5 w-3.5 text-slate-500" />}
                  {s.visibility === "PUBLIC" && <Globe className="h-3.5 w-3.5 text-[#D4AF37]" />}
                  {s.visibility === "UNLISTED" && <EyeOff className="h-3.5 w-3.5 text-[#FFB800]" />}
                  {s.forkedFromStrategyId && <span className="rounded bg-[#1A1A1A] px-1.5 py-0.5 font-mono text-[10px] text-slate-400">FORK</span>}
                </div>
                <p className="font-mono text-xs text-slate-500">v{s.version} · {s.signalTimeframe}/{s.expiry} · {s.likesCount}♥ {s.forksCount}⑂</p>
              </div>
              <div className="flex gap-2">
                {s.published ? <Button data-testid={`unpublish-${s.id}`} onClick={() => unpublish(s)} variant="outline" size="sm" className="border-[#3A3A3A] bg-transparent text-white">Unpublish</Button>
                  : <Button data-testid={`publish-${s.id}`} onClick={() => publish(s)} size="sm" className="bg-[#22C55E] text-black font-semibold">Publish</Button>}
                <Button data-testid={`delete-strategy-${s.id}`} onClick={() => del(s)} variant="outline" size="sm" className="border-[#C62828]/30 bg-transparent text-[#C62828]"><Trash2 className="h-4 w-4" /></Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------- Community feed ----------
export function CommunityFeed() {
  const [sort, setSort] = useState("popular");
  const [list, setList] = useState([]);
  const load = () => api.get(`/api/community/strategies?sort=${sort}`).then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, [sort]);
  return (
    <div>
      <H>Community</H>
      <Tabs value={sort} onValueChange={setSort} className="mb-6">
        <TabsList className="bg-[#111111]">
          {[["popular", "Popular"], ["newest", "Newest"], ["saved", "Most Saved"], ["updated", "Recently Updated"]].map(([v, l]) => (
            <TabsTrigger key={v} value={v} data-testid={`community-sort-${v}`} className="data-[state=active]:bg-[#22C55E] data-[state=active]:text-black">{l}</TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {list.map((s) => <StrategyCard key={s.id} s={s} onChange={load} />)}
      </div>
    </div>
  );
}

// ---------- Indicators ----------
export function Indicators() {
  const [list, setList] = useState([]);
  const [form, setForm] = useState({ name: "", description: "", visibility: "PRIVATE" });
  const load = () => api.get("/api/indicators").then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const create = async () => { try { await api.post("/api/indicators", form); setForm({ name: "", description: "", visibility: "PRIVATE" }); toast.success("Indicator saved"); load(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div>
      <H action={
        <Dialog><DialogTrigger asChild><Button data-testid="new-indicator-button" className="bg-[#22C55E] text-black font-semibold"><Plus className="mr-1 h-4 w-4" />New</Button></DialogTrigger>
          <DialogContent className="bg-[#0F0F0F] border-[#3A3A3A] text-white"><DialogHeader><DialogTitle>New Indicator</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Input placeholder="Name" data-testid="indicator-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="bg-[#080808] border-[#3A3A3A]" />
              <Textarea placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="bg-[#080808] border-[#3A3A3A]" />
            </div>
            <DialogFooter><Button data-testid="indicator-create-submit" onClick={create} disabled={!form.name} className="bg-[#22C55E] text-black">Save</Button></DialogFooter>
          </DialogContent></Dialog>
      }>Indicators</H>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {list.map((i) => (
          <div key={i.id} className="card-surface p-5">
            <div className="flex items-center justify-between"><h3 className="font-heading font-semibold">{i.name}</h3>
              <span className="rounded bg-[#1A1A1A] px-2 py-0.5 font-mono text-[10px] text-[#D4AF37]">{i.type}</span></div>
            <p className="mt-2 text-sm text-slate-400">{i.description}</p>
            <p className="mt-3 font-mono text-xs text-slate-500">by {i.author} · v{i.version}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Scripts ----------
export function Scripts() {
  const [list, setList] = useState([]);
  const [form, setForm] = useState({ name: "", description: "", sourceType: "PINE", source: "", visibility: "PRIVATE" });
  const load = () => api.get("/api/scripts").then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const create = async () => { try { await api.post("/api/scripts", form); setForm({ name: "", description: "", sourceType: "PINE", source: "", visibility: "PRIVATE" }); toast.success("Script stored"); load(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div>
      <H action={
        <Dialog><DialogTrigger asChild><Button data-testid="new-script-button" className="bg-[#22C55E] text-black font-semibold"><Plus className="mr-1 h-4 w-4" />New</Button></DialogTrigger>
          <DialogContent className="bg-[#0F0F0F] border-[#3A3A3A] text-white"><DialogHeader><DialogTitle>New Script (stored, never executed)</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Input placeholder="Name" data-testid="script-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="bg-[#080808] border-[#3A3A3A]" />
              <Select value={form.sourceType} onValueChange={(v) => setForm({ ...form, sourceType: v })}>
                <SelectTrigger className="bg-[#080808] border-[#3A3A3A]"><SelectValue /></SelectTrigger>
                <SelectContent className="bg-[#0F0F0F] text-white"><SelectItem value="PINE">PINE</SelectItem><SelectItem value="CUSTOM_SCRIPT">CUSTOM_SCRIPT</SelectItem></SelectContent>
              </Select>
              <Textarea placeholder="Source (stored only)" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} className="bg-[#080808] border-[#3A3A3A] font-mono" />
            </div>
            <DialogFooter><Button data-testid="script-create-submit" onClick={create} disabled={!form.name} className="bg-[#22C55E] text-black">Save</Button></DialogFooter>
          </DialogContent></Dialog>
      }>Scripts</H>
      <div className="mb-4 rounded-lg border border-[#FFB800]/30 bg-[#FFB800]/10 p-3 text-xs text-[#FFB800]">Scripts are stored & versioned for future use. Community scripts are untrusted and never executed on our servers.</div>
      {list.length === 0 ? <Empty>No scripts yet.</Empty> : (
        <div className="grid gap-4 md:grid-cols-2">
          {list.map((s) => (
            <div key={s.id} className="card-surface p-5"><div className="flex items-center justify-between"><h3 className="font-heading font-semibold">{s.name}</h3>
              <span className="rounded bg-[#1A1A1A] px-2 py-0.5 font-mono text-[10px] text-[#D4AF37]">{s.sourceType}</span></div>
              <p className="mt-2 text-sm text-slate-400">{s.description}</p></div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------- Backtests ----------
export function Backtests() {
  const [list, setList] = useState([]);
  useEffect(() => { api.get("/api/backtests").then((r) => setList(r.data)).catch(() => {}); }, []);
  return (
    <div>
      <H>Backtests</H>
      <div className="mb-4 rounded-lg border border-[#2E2E2E] bg-[#0F0F0F] p-3 text-xs text-slate-500">Historical backtest results. Past performance does not guarantee future results.</div>
      {list.length === 0 ? <Empty>No backtest reports uploaded yet.</Empty> : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {list.map((b) => (
            <div key={b.id} className="card-surface p-5">
              <div className="flex items-center justify-between"><span className="font-mono text-sm text-white">{b.market}</span>
                <span className="rounded bg-[#1A1A1A] px-2 py-0.5 font-mono text-[10px] text-slate-400">{b.provenance}</span></div>
              <div className="mt-3 font-mono text-3xl font-bold text-[#D4AF37]">{b.winRate}%<span className="text-sm text-slate-500"> win</span></div>
              <div className="mt-3 grid grid-cols-3 gap-2 font-mono text-xs text-slate-400">
                <div>Trades<div className="text-white">{b.trades}</div></div>
                <div>Wins<div className="text-[#D4AF37]">{b.wins}</div></div>
                <div>Losses<div className="text-[#C62828]">{b.losses}</div></div>
              </div>
              <p className="mt-3 font-mono text-xs text-slate-600">{b.timeframe}/{b.expiry}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------- Saved / Following ----------
export function Saved() {
  const [list, setList] = useState([]);
  const load = () => api.get("/api/saved/strategies").then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  return (<div><H>Saved Strategies</H>{list.length === 0 ? <Empty>Nothing saved yet.</Empty> :
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">{list.map((s) => <StrategyCard key={s.id} s={s} onChange={load} />)}</div>}</div>);
}
export function Following() {
  const [list, setList] = useState([]);
  const load = () => api.get("/api/following/strategies").then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  return (<div><H>Following Feed</H>{list.length === 0 ? <Empty>Follow creators to see their strategies here.</Empty> :
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">{list.map((s) => <StrategyCard key={s.id} s={s} onChange={load} />)}</div>}</div>);
}

// ---------- Subscription ----------
export function Subscription() {
  const { user } = useAuth();
  const [plans, setPlans] = useState([]);
  useEffect(() => { api.get("/api/billing/plans").then((r) => setPlans(r.data)).catch(() => {}); }, []);
  const checkout = async (lookup_key) => { try { const { data } = await api.post("/api/billing/checkout", { lookup_key, origin_url: window.location.origin }); window.location.href = data.checkout_url; } catch (e) { toast.error(errMsg(e)); } };
  const portal = async () => { try { const { data } = await api.post("/api/billing/portal", { lookup_key: "x", origin_url: window.location.origin }); window.location.href = data.url; } catch (e) { toast.error(errMsg(e)); } };
  const cancel = async () => { try { await api.post("/api/billing/cancel"); toast.success("Subscription canceled"); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div>
      <H>Subscription & Billing</H>
      <div className="card-surface mb-6 flex items-center justify-between p-5">
        <div><div className="label-mono">Current status</div><div className="mt-2"><StatusBadge value={user?.membership_status} /></div></div>
        <div className="flex gap-2">
          <Button data-testid="billing-portal-button" onClick={portal} variant="outline" className="border-[#3A3A3A] bg-transparent text-white"><CreditCard className="mr-2 h-4 w-4" />Manage billing</Button>
          {user?.membership_status === "ACTIVE" && <Button data-testid="cancel-subscription-button" onClick={cancel} variant="outline" className="border-[#C62828]/30 bg-transparent text-[#C62828]">Cancel</Button>}
        </div>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        {plans.map((p) => (
          <div key={p.id} className="card-surface p-6">
            <h3 className="font-heading text-xl font-semibold">{p.name}</h3>
            <div className="mt-2 font-mono text-3xl font-bold text-[#D4AF37]">${(p.amount / 100).toFixed(0)}<span className="text-base text-slate-500">/{p.interval}</span></div>
            <ul className="mt-4 space-y-2 text-sm text-slate-300">{(p.features || []).map((f) => <li key={f}>• {f}</li>)}</ul>
            <Button data-testid={`subscribe-${p.id}`} onClick={() => checkout(p.lookup_key)} className="mt-6 w-full bg-[#22C55E] text-black font-semibold">Choose {p.name}</Button>
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs text-slate-500">Stripe test mode. Card 4242 4242 4242 4242, any future expiry & CVC.</p>
    </div>
  );
}

// ---------- Devices ----------
export function Devices() {
  const [list, setList] = useState([]);
  const load = () => api.get("/api/v1/devices").then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const revoke = async (id) => { try { await api.delete(`/api/v1/devices/${id}`); toast.success("Device revoked"); load(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div><H>Connected Devices</H>
      {list.length === 0 ? <Empty>No devices registered. Install the extension to register one.</Empty> : (
        <div className="space-y-3">{list.map((d) => (
          <div key={d.id} className="card-surface flex items-center justify-between p-4">
            <div className="flex items-center gap-3"><Cpu className="h-5 w-5 text-[#D4AF37]" />
              <div><div className="font-medium text-white">{d.deviceName}</div>
                <div className="font-mono text-xs text-slate-500">v{d.extensionVersion || "?"} · last active {new Date(d.lastActive).toLocaleString()}{d.revoked && " · REVOKED"}</div></div></div>
            {!d.revoked && <Button data-testid={`revoke-device-${d.id}`} onClick={() => revoke(d.id)} variant="outline" size="sm" className="border-[#C62828]/30 bg-transparent text-[#C62828]">Revoke</Button>}
          </div>
        ))}</div>
      )}
    </div>
  );
}

// ---------- Downloads ----------
export function Downloads() {
  const [rel, setRel] = useState(null);
  useEffect(() => { api.get("/api/v1/extension/latest").then((r) => setRel(r.data)).catch(() => {}); }, []);
  return (
    <div><H>Downloads & Extension Setup</H>
      <div className="card-surface p-6">
        <div className="flex items-center gap-3"><Chrome className="h-8 w-8 text-[#D4AF37]" />
          <div><h3 className="font-heading text-lg font-semibold">Chrome Extension</h3>
            <p className="font-mono text-sm text-slate-500">Latest version {rel?.version || "—"}</p></div></div>
        <p className="mt-4 text-sm text-slate-400">{rel?.releaseNotes}</p>
        <a href={rel?.downloadUrl || "#"} target="_blank" rel="noreferrer">
          <Button data-testid="download-extension-button" className="mt-4 bg-[#22C55E] text-black font-semibold">Download / Install <ExternalLink className="ml-2 h-4 w-4" /></Button></a>
        <ol className="mt-6 list-decimal space-y-2 pl-5 text-sm text-slate-400">
          <li>Install the extension in Chrome.</li><li>Open it and click Login.</li>
          <li>Sign in with your member account to authorize.</li><li>Your device registers automatically.</li>
        </ol>
      </div>
    </div>
  );
}

// ---------- Account ----------
export function Account() {
  const { user, refreshUser, logout } = useAuth();
  const nav = window.location;
  const [form, setForm] = useState({ name: user?.name || "", username: user?.username || "", bio: user?.bio || "" });
  const save = async () => { try { await api.patch("/api/auth/profile", form); await refreshUser(); toast.success("Profile updated"); } catch (e) { toast.error(errMsg(e)); } };
  const exportData = async () => { const { data } = await api.get("/api/auth/export"); const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "my-data.json"; a.click(); };
  const del = async () => { if (!window.confirm("Delete your account? Private strategies will be removed.")) return; await api.delete("/api/auth/account"); await logout(); nav.href = "/"; };
  return (
    <div><H>Account Settings</H>
      <div className="card-surface max-w-lg p-6 space-y-4">
        <div><Label className="label-mono">Name</Label><Input data-testid="account-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1 bg-[#080808] border-[#3A3A3A]" /></div>
        <div><Label className="label-mono">Username</Label><Input data-testid="account-username-input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} className="mt-1 bg-[#080808] border-[#3A3A3A]" /></div>
        <div><Label className="label-mono">Bio</Label><Textarea value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} className="mt-1 bg-[#080808] border-[#3A3A3A]" /></div>
        <Button data-testid="account-save-button" onClick={save} className="bg-[#22C55E] text-black font-semibold">Save changes</Button>
      </div>
      <div className="card-surface mt-6 max-w-lg p-6">
        <h3 className="font-heading font-semibold">Data & Privacy</h3>
        <div className="mt-4 flex gap-3">
          <Button data-testid="export-data-button" onClick={exportData} variant="outline" className="border-[#3A3A3A] bg-transparent text-white">Download my data</Button>
          <Button data-testid="delete-account-button" onClick={del} variant="outline" className="border-[#C62828]/30 bg-transparent text-[#C62828]">Delete account</Button>
        </div>
      </div>
    </div>
  );
}

// ---------- Support ----------
export function Support() {
  return (
    <div><H>Support & Docs</H>
      <div className="grid gap-4 md:grid-cols-2">
        {[["Privacy Policy", "How we handle your data."], ["Terms of Service", "Your agreement with us."],
          ["Trading Risk Disclosure", "Trading carries substantial risk of loss."], ["Affiliate Disclosure", "We may earn from Pocket Option referrals."],
          ["Subscription Terms", "Billing, renewal and cancellation."], ["Extension API Docs", "See EXTENSION_API.md in the repo."]].map(([t, d]) => (
          <div key={t} className="card-surface p-5"><h3 className="font-heading font-semibold">{t}</h3><p className="mt-2 text-sm text-slate-400">{d}</p></div>
        ))}
      </div>
    </div>
  );
}
