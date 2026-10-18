import React, { useEffect, useState } from "react";
import { api, errMsg } from "../../lib/api";
import { StatusBadge } from "../../components/Brand";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { toast } from "sonner";

const H = ({ children }) => <h1 className="mb-6 font-heading text-2xl font-bold tracking-wide">{children}</h1>;
const Stat = ({ l, v }) => (<div className="card-surface p-4"><div className="label-mono">{l}</div><div className="mt-1 font-mono text-2xl font-bold text-[#D4AF37]">{v}</div></div>);

// ---------- Admin AI Control Center ----------
export function AICenter() {
  const [models, setModels] = useState([]);
  const [learn, setLearn] = useState(null);
  const load = () => {
    api.get("/api/admin/ai/models").then((r) => setModels(r.data)).catch(() => {});
    api.get("/api/admin/ai/learning").then((r) => setLearn(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);
  const [training, setTraining] = useState(false);
  const act = async (path, modelId) => { try { await api.post(`/api/admin/ai/${path}`, { modelId }); toast.success(path); load(); } catch (e) { toast.error(errMsg(e)); } };
  const deployModel = async (id) => {
    try { await api.post("/api/admin/ai/models/deploy", { modelId: id }); toast.success("deployed"); load(); }
    catch (e) {
      const d = e?.response?.data?.detail;
      if (d && d.error === "below_live") {
        if (window.confirm(d.message + "\n\nForce deploy anyway?")) {
          try { await api.post("/api/admin/ai/models/deploy", { modelId: id, override: true }); toast.success("deployed (override)"); load(); }
          catch (e2) { toast.error(errMsg(e2)); }
        }
      } else { toast.error(errMsg(e)); }
    }
  };
  const train = async () => {
    setTraining(true);
    try {
      const r = await api.post("/api/admin/ai/train");
      const acc = r.data?.report?.holdoutAccuracy;
      toast.success(`Trained candidate ${r.data.version} · ${r.data.usableSamples} samples${acc != null ? ` · holdout ${(acc * 100).toFixed(1)}%` : ""}`);
      load();
    } catch (e) { toast.error(errMsg(e)); }
    finally { setTraining(false); }
  };
  return (
    <div><H>KAOS AI Control Center</H>
      <div className="mb-4 rounded-lg border border-[#D4AF37]/20 bg-[#D4AF37]/5 p-3 text-xs text-[#D4AF37]">Raw samples never auto-deploy. Training builds a CANDIDATE (native XGBoost/LightGBM tree bundle) from consented learning samples; it must pass chronological + out-of-sample validation and an explicit Deploy before it serves live inference. AI is learning/reporting only — it never overrides the deterministic KAOS Strategy.</div>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Button data-testid="ai-train-button" onClick={train} disabled={training} className="bg-[#22C55E] text-black">
          {training ? "Training…" : "Train KAOS AI model"}
        </Button>
        <span className="font-mono text-xs text-slate-500">Trains over collected learning samples that carry a 104-feature vector. Needs ≥12 usable labeled samples.</span>
      </div>
      {learn && <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat l="Learning Samples" v={learn.totalSamples} /><Stat l="Real" v={learn.realSamples} /><Stat l="Paper/Shadow" v={learn.paperSamples} /><Stat l="Consented Users" v={learn.consentedUsers} />
      </div>}
      <div className="card-surface p-0 overflow-x-auto"><div className="border-b border-[#2E2E2E] p-4"><h3 className="font-heading font-semibold">Model Registry</h3></div>
        <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Version</TableHead><TableHead>Status</TableHead><TableHead>Holdout acc.</TableHead><TableHead>vs Live</TableHead><TableHead>Notes</TableHead><TableHead></TableHead></TableRow></TableHeader>
          <TableBody>{models.map((m) => {
            const acc = m.report?.holdoutAccuracy;
            const deployed = models.find((x) => x.status === "deployed");
            const liveAcc = deployed?.report?.holdoutAccuracy;
            const beats = acc != null && liveAcc != null && m.id !== deployed?.id ? acc >= liveAcc : null;
            return (<TableRow key={m.id} className="border-[#2E2E2E]" data-testid={`ai-model-${m.id}`}>
            <TableCell className="font-mono text-sm">{m.version}{m.simulated && " ·SIM"}</TableCell>
            <TableCell><span className={m.status === "deployed" ? "text-green-400 font-mono text-xs" : "text-slate-400 font-mono text-xs"}>{m.status}</span></TableCell>
            <TableCell className="font-mono text-xs text-[#D4AF37]">{acc != null ? (acc * 100).toFixed(1) + "%" : "—"}</TableCell>
            <TableCell>{beats == null ? <span className="text-slate-600 text-xs">—</span> : beats ? <span className="rounded bg-[#22C55E]/10 border border-[#22C55E]/30 px-2 py-0.5 font-mono text-[10px] text-[#22C55E]">BEATS LIVE</span> : <span className="rounded bg-amber-400/10 border border-amber-400/30 px-2 py-0.5 font-mono text-[10px] text-amber-300">BELOW LIVE</span>}</TableCell>
            <TableCell className="text-xs text-slate-400">{m.notes}</TableCell>
            <TableCell className="flex gap-2">
              <Button data-testid={`ai-deploy-${m.id}`} size="sm" className="bg-[#22C55E] text-black" onClick={() => deployModel(m.id)}>Deploy</Button>
              <Button size="sm" variant="outline" className="border-[#C62828]/30 bg-transparent text-[#C62828]" onClick={() => act("models/rollback", m.id)}>Retire</Button>
            </TableCell></TableRow>);})}</TableBody></Table></div>
      {learn && <div className="card-surface mt-6 p-5"><h3 className="font-heading font-semibold">Training Runs & Datasets</h3>
        <p className="mt-2 font-mono text-xs text-slate-500">Datasets: {learn.datasets.length} · Training runs: {learn.trainingRuns.length}</p>
        {learn.trainingRuns.map((r) => <div key={r.id} className="mt-2 border-b border-[#2E2E2E] py-2 font-mono text-xs text-slate-400">{r.id} · {r.status}{r.metrics?.holdoutAccuracy != null ? ` · holdout ${(r.metrics.holdoutAccuracy * 100).toFixed(1)}%` : ""}{r.usableSamples != null ? ` · ${r.usableSamples} samples` : (r.datasetVersion ? ` · dataset ${r.datasetVersion}` : "")}</div>)}
      </div>}
    </div>
  );
}

// ---------- Admin Affiliates & Commissions ----------
export function Affiliates() {
  const [accs, setAccs] = useState([]);
  const [comms, setComms] = useState([]);
  const [prog, setProg] = useState(null);
  const [mkt, setMkt] = useState({ title: "", type: "banner", copy: "" });
  const load = () => {
    api.get("/api/admin/affiliates").then((r) => setAccs(r.data)).catch(() => {});
    api.get("/api/admin/commissions").then((r) => setComms(r.data)).catch(() => {});
    api.get("/api/admin/affiliate-program").then((r) => setProg(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);
  const setStatus = async (cid, status) => { try { await api.post(`/api/admin/commissions/${cid}/status`, { status }); toast.success(status); load(); } catch (e) { toast.error(errMsg(e)); } };
  const saveProg = async () => { try { await api.post("/api/admin/affiliate-program", prog); toast.success("Program saved"); } catch (e) { toast.error(errMsg(e)); } };
  const addMkt = async () => { try { await api.post("/api/admin/marketing-assets", mkt); toast.success("Asset added"); setMkt({ title: "", type: "banner", copy: "" }); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div><H>Affiliates & Commissions</H>
      {prog && <div className="card-surface mb-6 p-5"><h3 className="font-heading font-semibold">Commission Program (configurable)</h3>
        <div className="mt-3 grid gap-3 md:grid-cols-4">
          <div><label className="label-mono">Default rate %</label><Input data-testid="commission-rate-input" type="number" value={prog.defaultRatePct} onChange={(e) => setProg({ ...prog, defaultRatePct: parseInt(e.target.value) })} className="mt-1 bg-[#080808] border-[#3A3A3A] font-mono" /></div>
          <div><label className="label-mono">Hold days</label><Input type="number" value={prog.holdDays} onChange={(e) => setProg({ ...prog, holdDays: parseInt(e.target.value) })} className="mt-1 bg-[#080808] border-[#3A3A3A] font-mono" /></div>
          <div><label className="label-mono">Min payout $</label><Input type="number" value={prog.minPayout} onChange={(e) => setProg({ ...prog, minPayout: parseInt(e.target.value) })} className="mt-1 bg-[#080808] border-[#3A3A3A] font-mono" /></div>
          <div className="flex items-end"><Button data-testid="save-program-button" onClick={saveProg} className="bg-[#22C55E] text-black">Save</Button></div>
        </div></div>}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card-surface p-0 overflow-x-auto"><div className="border-b border-[#2E2E2E] p-4"><h3 className="font-heading font-semibold">Affiliates</h3></div>
          <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>User</TableHead><TableHead>Code</TableHead><TableHead>Referrals</TableHead></TableRow></TableHeader>
            <TableBody>{accs.map((a) => (<TableRow key={a.id} className="border-[#2E2E2E]"><TableCell className="font-mono text-sm">{a.user?.username}</TableCell><TableCell className="font-mono text-xs text-[#D4AF37]">{a.code}</TableCell><TableCell>{a.referrals}</TableCell></TableRow>))}</TableBody></Table></div>
        <div className="card-surface p-0 overflow-x-auto"><div className="border-b border-[#2E2E2E] p-4"><h3 className="font-heading font-semibold">Commissions</h3></div>
          <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Amount</TableHead><TableHead>Status</TableHead><TableHead>Set</TableHead></TableRow></TableHeader>
            <TableBody>{comms.length === 0 && <TableRow><TableCell colSpan={3} className="py-6 text-center text-slate-500">None</TableCell></TableRow>}
              {comms.map((c) => (<TableRow key={c.id} className="border-[#2E2E2E]"><TableCell className="font-mono text-[#D4AF37]">${c.amount}</TableCell><TableCell><StatusBadge value={c.status} /></TableCell>
                <TableCell><Select onValueChange={(s) => setStatus(c.id, s)}><SelectTrigger data-testid={`commission-status-${c.id}`} className="h-8 w-32 bg-[#080808] border-[#3A3A3A] text-xs"><SelectValue placeholder="Change" /></SelectTrigger><SelectContent className="bg-[#0F0F0F] text-white">{["APPROVED", "PAYABLE", "PAID", "REVERSED"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select></TableCell></TableRow>))}</TableBody></Table></div>
      </div>
      <div className="card-surface mt-6 p-5"><h3 className="font-heading font-semibold">Marketing Center</h3>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <Input data-testid="marketing-title-input" placeholder="Title" value={mkt.title} onChange={(e) => setMkt({ ...mkt, title: e.target.value })} className="bg-[#080808] border-[#3A3A3A]" />
          <Input placeholder="Type (banner/copy/video)" value={mkt.type} onChange={(e) => setMkt({ ...mkt, type: e.target.value })} className="bg-[#080808] border-[#3A3A3A]" />
          <Button data-testid="add-marketing-button" onClick={addMkt} disabled={!mkt.title} className="bg-[#22C55E] text-black">Add asset</Button>
        </div>
        <Textarea placeholder="Approved ad copy / swipe text" value={mkt.copy} onChange={(e) => setMkt({ ...mkt, copy: e.target.value })} className="mt-3 bg-[#080808] border-[#3A3A3A]" />
      </div>
    </div>
  );
}
