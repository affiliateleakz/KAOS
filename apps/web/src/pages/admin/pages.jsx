import { deviceDate } from "../../lib/deviceDate";
import React, { useEffect, useState } from "react";
import { Navigate, Link } from "react-router-dom";
import { api, errMsg } from "../../lib/api";
import { StatusBadge } from "../../components/Brand";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../../components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { Switch } from "../../components/ui/switch";
import { toast } from "sonner";
import { Users as UsersIcon, DollarSign, BadgeCheck, Boxes, Flag, Activity, Download } from "lucide-react";

const H = ({ children }) => <h1 className="mb-6 font-heading text-2xl font-bold">{children}</h1>;
const Card = ({ children, className = "" }) => <div className={`card-surface p-5 ${className}`}>{children}</div>;

export function AdminDashboard() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { api.get("/api/admin/dashboard").then((r) => setD(r.data)).catch(setErr); }, []);
  if (err?.response?.status === 403) return <Navigate to="/admin/moderation" replace />;
  if (err) return <p className="text-red-400">{errMsg(err)}</p>;
  if (!d) return <p className="text-slate-500">Loading…</p>;
  const stats = [
    ["Total Users", d.totalUsers, UsersIcon], ["Active Members", d.activeMembers, BadgeCheck],
    ["Past Due", d.pastDue, DollarSign], ["Canceled", d.canceled, Activity],
    ["Suspended", d.suspended, Flag], ["Affiliate Pending", d.affiliatePending, BadgeCheck],
    ["Affiliate Verified", d.affiliateVerified, BadgeCheck], ["Published Strategies", d.publishedStrategies, Boxes],
    ["Open Reports", d.openReports, Flag], ["New Members (7d)", d.newMembers, UsersIcon],
    ["Est. MRR", `$${(d.revenueMRR ?? 0).toFixed(0)}`, DollarSign],
    ["Commissions Payable", `$${(d.commissionsPayable ?? 0).toFixed(0)}`, DollarSign],
    ["Confirmed Trades", d.confirmedTrades ?? 0, Activity],
  ];
  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <H>Admin Overview</H>
        <a href={`${process.env.REACT_APP_BACKEND_URL}/api/admin/export/source.zip`} target="_blank" rel="noreferrer" data-testid="export-source-button">
          <Button variant="outline" className="border-[#D4AF37]/40 bg-transparent text-[#D4AF37] hover:bg-[#D4AF37]/10"><Download className="mr-2 h-4 w-4" /> Download Source</Button>
        </a>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {stats.map(([l, v, Icon]) => (
          <Card key={l}><div className="flex items-center justify-between"><span className="label-mono">{l}</span><Icon className="h-4 w-4 text-slate-600" /></div>
            <div className="mt-2 font-mono text-3xl font-bold text-[#D4AF37]">{v}</div></Card>
        ))}
      </div>
      <Card className="mt-6">
        <h3 className="font-heading font-semibold">Plan Mix <span className="font-mono text-xs text-slate-500">· active members & monthly revenue</span></h3>
        <div className="mt-3 space-y-2 font-mono text-sm" data-testid="plan-mix">
          {(!d.planMix || d.planMix.length === 0) && <p className="text-slate-500">No active members.</p>}
          {(d.planMix || []).map((p) => (
            <div key={p.planId} className="flex items-center justify-between border-b border-[#2E2E2E] py-1.5">
              <span className="text-slate-300">{p.name}</span>
              <span className="text-slate-500">{p.count} member{p.count === 1 ? "" : "s"}</span>
              <span className="text-[#D4AF37]">${p.monthlyRevenue.toFixed(0)}/mo</span>
            </div>
          ))}
        </div>
      </Card>
      <Card className="mt-6">
        <h3 className="font-heading font-semibold">Extension Version Distribution</h3>
        <div className="mt-3 space-y-2 font-mono text-sm">
          {Object.entries(d.extensionVersions || {}).length === 0 && <p className="text-slate-500">No active devices.</p>}
          {Object.entries(d.extensionVersions || {}).map(([v, c]) => (
            <div key={v} className="flex justify-between border-b border-[#2E2E2E] py-1"><span className="text-slate-400">{v}</span><span className="text-white">{c}</span></div>
          ))}
        </div>
      </Card>
    </div>
  );
}

export function Users() {
  const [list, setList] = useState([]);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(null);
  const load = () => api.get(`/api/admin/users?q=${encodeURIComponent(q)}`).then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const action = async (uid, path, body) => { try { await api.post(`/api/admin/users/${uid}/${path}`, body || {}); toast.success("Done"); load(); if (sel) openDetail(uid); } catch (e) { toast.error(errMsg(e)); } };
  const openDetail = async (uid) => { const { data } = await api.get(`/api/admin/users/${uid}`); setSel(data); };
  return (
    <div>
      <H>User Management</H>
      <div className="mb-4 flex gap-2">
        <Input data-testid="admin-user-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search email / username…" className="max-w-sm bg-[#0F0F0F] border-[#3A3A3A]" />
        <Button data-testid="admin-user-search-button" onClick={load} className="bg-[#22C55E] text-black">Search</Button>
      </div>
      <div className="card-surface overflow-x-auto p-0">
        <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Email</TableHead><TableHead>Role</TableHead><TableHead>Membership</TableHead><TableHead>Affiliate</TableHead><TableHead>Status</TableHead><TableHead></TableHead></TableRow></TableHeader>
          <TableBody>
            {list.map((u) => (
              <TableRow key={u.id} className="border-[#2E2E2E]" data-testid={`admin-user-row-${u.username}`}>
                <TableCell className="font-mono text-sm">{u.email}</TableCell>
                <TableCell><span className="font-mono text-xs text-[#D4AF37]">{u.role}</span></TableCell>
                <TableCell><StatusBadge value={u.membership_status} /></TableCell>
                <TableCell><StatusBadge value={u.affiliate_status} /></TableCell>
                <TableCell><span className={u.account_status === "active" ? "text-[#D4AF37]" : "text-[#C62828]"}>{u.account_status}</span></TableCell>
                <TableCell><Button data-testid={`admin-user-manage-${u.username}`} size="sm" variant="outline" onClick={() => openDetail(u.id)} className="border-[#3A3A3A] bg-transparent text-white">Manage</Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={!!sel} onOpenChange={(o) => !o && setSel(null)}>
        <DialogContent className="bg-[#0F0F0F] border-[#3A3A3A] text-white max-w-lg">
          {sel && <>
            <DialogHeader><DialogTitle>{sel.email}</DialogTitle></DialogHeader>
            <div className="space-y-2 font-mono text-sm text-slate-400">
              <div>Role: <span className="text-white">{sel.role}</span> · Devices: {(sel.devices || []).length} · Strategies: {sel.strategies}</div>
              <div>Membership: {sel.membership_status} · Affiliate: {sel.affiliate_status} · Access revoked: {String(sel.extension_access_revoked)}</div>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-2">
              <Button data-testid="admin-suspend" size="sm" variant="outline" className="border-[#3A3A3A] bg-transparent text-white" onClick={() => action(sel.id, "suspend")}>Suspend</Button>
              <Button data-testid="admin-unsuspend" size="sm" variant="outline" className="border-[#3A3A3A] bg-transparent text-white" onClick={() => action(sel.id, "unsuspend")}>Unsuspend</Button>
              <Button data-testid="admin-revoke-access" size="sm" variant="outline" className="border-[#C62828]/30 bg-transparent text-[#C62828]" onClick={() => action(sel.id, "revoke-access")}>Revoke Extension Access</Button>
              <Button data-testid="admin-restore-access" size="sm" variant="outline" className="border-[#D4AF37]/30 bg-transparent text-[#D4AF37]" onClick={() => action(sel.id, "restore-access")}>Restore Access</Button>
              <Button data-testid="admin-force-logout" size="sm" variant="outline" className="border-[#3A3A3A] bg-transparent text-white" onClick={() => action(sel.id, "force-logout")}>Force Logout</Button>
              <Button data-testid="admin-revoke-all-devices" size="sm" variant="outline" className="border-[#C62828]/30 bg-transparent text-[#C62828]" onClick={() => action(sel.id, "revoke-all-devices")}>Revoke All Devices</Button>
              <Button data-testid="admin-activate-membership" size="sm" className="bg-[#22C55E] text-black" onClick={() => api.post(`/api/admin/users/${sel.id}/set-membership`, { key: "m", value: { status: "ACTIVE", plan: "monthly" } }).then(() => { toast.success("Membership set ACTIVE"); openDetail(sel.id); })}>Set Active</Button>
              <Select onValueChange={(role) => action(sel.id, "role", { role })}>
                <SelectTrigger data-testid="admin-role-select" className="bg-[#080808] border-[#3A3A3A]"><SelectValue placeholder="Change role" /></SelectTrigger>
                <SelectContent className="bg-[#0F0F0F] text-white">{["user", "moderator", "admin", "super_admin"].map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </>}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function Subscriptions() {
  const [list, setList] = useState([]);
  useEffect(() => { api.get("/api/admin/users?status=ACTIVE").then((r) => setList(r.data)).catch(() => {}); }, []);
  return (<div><H>Subscriptions & Payments</H>
    <div className="mb-4 rounded-lg border border-[#2E2E2E] bg-[#0F0F0F] p-3 text-xs text-slate-500">Revenue and subscription events are driven by Stripe webhooks (test mode).</div>
    <div className="card-surface p-0 overflow-x-auto"><Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Email</TableHead><TableHead>Plan</TableHead><TableHead>Status</TableHead><TableHead>Renewal</TableHead></TableRow></TableHeader>
      <TableBody>{list.map((u) => (<TableRow key={u.id} className="border-[#2E2E2E]"><TableCell className="font-mono text-sm">{u.email}</TableCell><TableCell>{u.membership_plan || "—"}</TableCell><TableCell><StatusBadge value={u.membership_status} /></TableCell><TableCell className="font-mono text-xs">{u.membership_expires_at ? new Date(u.membership_expires_at).toLocaleDateString() : "—"}</TableCell></TableRow>))}</TableBody></Table></div>
  </div>);
}

export function AdminDevices() {
  const [list, setList] = useState([]);
  const load = () => api.get("/api/admin/devices").then((r) => setList(r.data)).catch((e) => toast.error(errMsg(e)));
  useEffect(() => { load(); }, []);
  const revoke = async (id) => { try { await api.post(`/api/admin/devices/${encodeURIComponent(id)}/revoke`); toast.success("Revoked"); load(); } catch (e) { toast.error(errMsg(e)); } };
  return (<div><H>Connected Devices Monitor</H>
    <div className="card-surface p-0 overflow-x-auto"><Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>User</TableHead><TableHead>Device</TableHead><TableHead>Version</TableHead><TableHead>Last Active</TableHead><TableHead>Status</TableHead><TableHead></TableHead></TableRow></TableHeader>
      <TableBody>{list.map((d) => (<TableRow key={d.id} className="border-[#2E2E2E]" data-testid={`admin-device-row-${d.id}`}><TableCell className="font-mono text-sm">{d.user?.username}</TableCell><TableCell>{d.deviceName}</TableCell><TableCell className="font-mono text-xs">{d.extensionVersion}</TableCell><TableCell className="font-mono text-xs">{deviceDate(d)}</TableCell><TableCell className={d.revoked ? "text-[#C62828]" : "text-[#D4AF37]"}>{d.revoked ? "REVOKED" : "ACTIVE"}</TableCell><TableCell>{!d.revoked && <Button data-testid={`admin-revoke-device-${d.id}`} size="sm" variant="outline" className="border-[#C62828]/30 bg-transparent text-[#C62828]" onClick={() => revoke(d.id)}>Revoke</Button>}</TableCell></TableRow>))}</TableBody></Table></div>
  </div>);
}

export function Affiliate() {
  const [list, setList] = useState([]);
  const load = () => api.get("/api/admin/affiliate").then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const act = async (uid, verb) => { try { await api.post(`/api/admin/affiliate/${uid}/${verb}`); toast.success(verb === "approve" ? "Verified" : "Rejected"); load(); } catch (e) { toast.error(errMsg(e)); } };
  return (<div><H>Pocket Option Affiliate Queue</H>
    {list.length === 0 ? <div className="card-surface p-10 text-center text-slate-500">No affiliate submissions.</div> : (
      <div className="card-surface p-0 overflow-x-auto"><Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>User</TableHead><TableHead>PO UID</TableHead><TableHead>Note</TableHead><TableHead>Status</TableHead><TableHead></TableHead></TableRow></TableHeader>
        <TableBody>{list.map((r) => (<TableRow key={r.id} className="border-[#2E2E2E]" data-testid={`affiliate-row-${r.userId}`}>
          <TableCell className="font-mono text-sm">{r.user?.username}</TableCell><TableCell className="font-mono">{r.poUid}</TableCell><TableCell className="text-sm text-slate-400">{r.note}</TableCell><TableCell><StatusBadge value={r.status} /></TableCell>
          <TableCell className="flex gap-2">
            <Button data-testid={`admin-affiliate-approve-button-${r.userId}`} size="sm" className="bg-[#22C55E] text-black" onClick={() => act(r.userId, "approve")}>Approve</Button>
            <Button data-testid={`admin-affiliate-reject-button-${r.userId}`} size="sm" variant="outline" className="border-[#C62828]/30 bg-transparent text-[#C62828]" onClick={() => act(r.userId, "reject")}>Reject</Button>
          </TableCell></TableRow>))}</TableBody></Table></div>
    )}
  </div>);
}

export function AdminStrategies() {
  const [list, setList] = useState([]);
  useEffect(() => { api.get("/api/admin/strategies").then((r) => setList(r.data)).catch(() => {}); }, []);
  return (<div><H>Strategy Repository</H>
    <div className="card-surface p-0 overflow-x-auto"><Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Name</TableHead><TableHead>Type</TableHead><TableHead>Owner</TableHead><TableHead>Visibility</TableHead><TableHead>Version</TableHead><TableHead>Likes</TableHead></TableRow></TableHeader>
      <TableBody>{list.map((s) => (<TableRow key={s.id} className="border-[#2E2E2E]"><TableCell>{s.name}</TableCell><TableCell><span className="font-mono text-xs text-[#D4AF37]">{s.type}</span></TableCell><TableCell className="font-mono text-sm">{s.ownerUsername}</TableCell><TableCell className="font-mono text-xs">{s.visibility}</TableCell><TableCell>v{s.version}</TableCell><TableCell>{s.likesCount}</TableCell></TableRow>))}</TableBody></Table></div>
  </div>);
}

export function Moderation() {
  const [list, setList] = useState([]);
  const load = () => api.get("/api/admin/reports").then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const act = async (rid, action) => { try { await api.post(`/api/admin/reports/${rid}/action`, { key: "a", value: { action } }); toast.success(action); load(); } catch (e) { toast.error(errMsg(e)); } };
  return (<div><H>Moderation Queue</H>
    {list.length === 0 ? <div className="card-surface p-10 text-center text-slate-500">No reports.</div> : (
      <div className="space-y-3">{list.map((r) => (
        <div key={r.id} className="card-surface flex flex-wrap items-center justify-between gap-3 p-4" data-testid={`report-${r.id}`}>
          <div className="min-w-0"><div className="font-medium">{r.targetType} · {r.reason}</div><div className="break-words font-mono text-xs text-slate-500">{r.details} · {r.status}</div>{["community_post","community_comment"].includes(r.targetType)&&<Link className="mt-2 inline-block text-sm text-[#e8c46f] underline" to={"/dashboard/community?post="+encodeURIComponent(r.postId||r.targetId)} target="_blank" rel="noopener noreferrer">Review reported post</Link>}</div>
          {r.status === "open" && <div className="flex gap-2">
            <Button size="sm" variant="outline" className="border-[#3A3A3A] bg-transparent text-white" onClick={() => act(r.id, "dismiss")}>Dismiss</Button>
            <Button size="sm" variant="outline" className="border-[#FFB800]/30 bg-transparent text-[#FFB800]" onClick={() => act(r.id, "hide")}>Hide</Button>
            <Button data-testid={`report-remove-${r.id}`} size="sm" variant="outline" className="border-[#C62828]/30 bg-transparent text-[#C62828]" onClick={() => act(r.id, "remove")}>Remove</Button>
          </div>}
        </div>
      ))}</div>
    )}
  </div>);
}

export function ExtensionReleases() {
  const [list, setList] = useState([]);
  const [form, setForm] = useState({ version: "", releaseNotes: "", downloadUrl: "", mandatory: false, published: true });
  const load = () => api.get("/api/admin/extension/releases").then((r) => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const create = async () => { try { await api.post("/api/admin/extension/releases", { key: "r", value: form }); toast.success("Release published"); setForm({ version: "", releaseNotes: "", downloadUrl: "", mandatory: false, published: true }); load(); } catch (e) { toast.error(errMsg(e)); } };
  return (<div><H>Extension Release Management</H>
    <div className="card-surface mb-6 max-w-lg p-5 space-y-3">
      <Input data-testid="release-version-input" placeholder="Version (e.g. 1.5.0)" value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} className="bg-[#080808] border-[#3A3A3A]" />
      <Textarea placeholder="Release notes" value={form.releaseNotes} onChange={(e) => setForm({ ...form, releaseNotes: e.target.value })} className="bg-[#080808] border-[#3A3A3A]" />
      <Input placeholder="Download URL" value={form.downloadUrl} onChange={(e) => setForm({ ...form, downloadUrl: e.target.value })} className="bg-[#080808] border-[#3A3A3A]" />
      <div className="flex items-center gap-2"><Switch checked={form.mandatory} onCheckedChange={(v) => setForm({ ...form, mandatory: v })} /><Label className="text-sm">Mandatory update</Label></div>
      <Button data-testid="create-release-button" onClick={create} disabled={!form.version} className="bg-[#22C55E] text-black font-semibold">Publish Release</Button>
    </div>
    <div className="space-y-2">{list.map((r) => (<div key={r.id} className="card-surface flex items-center justify-between p-4"><div><span className="font-mono text-[#D4AF37]">v{r.version}</span> <span className="text-sm text-slate-400">{r.releaseNotes}</span></div>{r.mandatory && <span className="font-mono text-xs text-[#C62828]">MANDATORY</span>}</div>))}</div>
  </div>);
}

export function Settings() {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/api/admin/settings").then((r) => setS(r.data)).catch(() => {}); }, []);
  const saveAffiliate = async () => { try { await api.post("/api/admin/settings", { key: "affiliate", value: { value: s.affiliate } }); toast.success("Affiliate settings saved"); } catch (e) { toast.error(errMsg(e)); } };
  const saveBranding = async () => { try { await api.post("/api/admin/settings", { key: "branding", value: { value: s.branding } }); toast.success("Branding saved"); } catch (e) { toast.error(errMsg(e)); } };
  const savePlans = async () => { try { await api.post("/api/admin/settings", { key: "plans", value: { value: s.plans } }); toast.success("Plans saved"); } catch (e) { toast.error(errMsg(e)); } };
  if (!s) return <p className="text-slate-500">Loading…</p>;
  return (<div><H>Platform Settings</H>
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="card-surface p-5"><h3 className="font-heading font-semibold">Branding</h3>
        <Label className="label-mono mt-3 block">Product name</Label>
        <Input data-testid="settings-product-name" value={s.branding.productName || ""} onChange={(e) => setS({ ...s, branding: { ...s.branding, productName: e.target.value } })} className="mt-1 bg-[#080808] border-[#3A3A3A]" />
        <Button data-testid="save-branding-button" onClick={saveBranding} className="mt-3 bg-[#22C55E] text-black">Save</Button></div>
      <div className="card-surface p-5"><h3 className="font-heading font-semibold">Affiliate Program</h3>
        <Label className="label-mono mt-3 block">Affiliate URL</Label>
        <Input data-testid="settings-affiliate-url" value={s.affiliate.affiliateUrl || ""} onChange={(e) => setS({ ...s, affiliate: { ...s.affiliate, affiliateUrl: e.target.value } })} className="mt-1 bg-[#080808] border-[#3A3A3A]" />
        <Label className="label-mono mt-3 block">Instructions</Label>
        <Textarea value={s.affiliate.instructions || ""} onChange={(e) => setS({ ...s, affiliate: { ...s.affiliate, instructions: e.target.value } })} className="mt-1 bg-[#080808] border-[#3A3A3A]" />
        <Button data-testid="save-affiliate-button" onClick={saveAffiliate} className="mt-3 bg-[#22C55E] text-black">Save</Button></div>
      <div className="card-surface p-5 lg:col-span-2"><h3 className="font-heading font-semibold">Membership Plans</h3>
        {s.plans.map((p, i) => (
          <div key={p.id} className="mt-3 grid grid-cols-3 gap-2">
            <Input value={p.name} onChange={(e) => { const pl = [...s.plans]; pl[i] = { ...p, name: e.target.value }; setS({ ...s, plans: pl }); }} className="bg-[#080808] border-[#3A3A3A]" />
            <Input type="number" value={p.amount} onChange={(e) => { const pl = [...s.plans]; pl[i] = { ...p, amount: parseInt(e.target.value) }; setS({ ...s, plans: pl }); }} className="bg-[#080808] border-[#3A3A3A] font-mono" />
            <Input value={p.interval} disabled className="bg-[#080808] border-[#3A3A3A] font-mono opacity-60" />
          </div>
        ))}
        <Button data-testid="save-plans-button" onClick={savePlans} className="mt-3 bg-[#22C55E] text-black">Save Plans</Button>
        <p className="mt-2 text-xs text-slate-500">Amount in cents. Pricing is configurable — never hardcoded in app logic.</p></div>
    </div>
  </div>);
}

export function Audit() {
  const [list, setList] = useState([]);
  useEffect(() => { api.get("/api/admin/audit").then((r) => setList(r.data)).catch(() => {}); }, []);
  return (<div><H>Audit Log</H>
    <div className="card-surface p-0 overflow-x-auto"><Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Time</TableHead><TableHead>Actor</TableHead><TableHead>Action</TableHead><TableHead>Target</TableHead></TableRow></TableHeader>
      <TableBody>{list.map((a) => (<TableRow key={a.id} className="border-[#2E2E2E]"><TableCell className="font-mono text-xs">{new Date(a.createdAt).toLocaleString()}</TableCell><TableCell className="font-mono text-sm">{a.actorEmail}</TableCell><TableCell><span className="font-mono text-xs text-[#FFB800]">{a.action}</span></TableCell><TableCell className="font-mono text-xs text-slate-400">{a.targetType}:{a.targetId}</TableCell></TableRow>))}</TableBody></Table></div>
  </div>);
}
