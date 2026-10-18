import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Brand, RiskBar, StatusBadge } from "../components/Brand";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Heart, Bookmark, GitFork, Lock, Send, Flag } from "lucide-react";
import { toast } from "sonner";

export default function CommunityDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const [s, setS] = useState(null);
  const [comment, setComment] = useState("");

  const load = () => api.get(`/api/community/strategies/${id}`).then((r) => setS(r.data)).catch(() => setS(null));
  useEffect(() => { load(); }, [id]);

  const act = async (verb) => {
    if (!user) return nav("/login");
    try {
      if (verb === "like") s.liked ? await api.delete(`/api/community/strategies/${id}/like`) : await api.post(`/api/community/strategies/${id}/like`);
      if (verb === "save") { s.saved ? await api.delete(`/api/community/strategies/${id}/save`) : await api.post(`/api/community/strategies/${id}/save`); toast.success(s.saved ? "Removed" : "Added to library"); }
      if (verb === "fork") { await api.post(`/api/community/strategies/${id}/fork`); toast.success("Forked to your strategies"); }
      load();
    } catch (e) { toast.error(errMsg(e)); }
  };

  const postComment = async () => {
    if (!user) return nav("/login");
    try { await api.post(`/api/community/strategies/${id}/comment`, { body: comment }); setComment(""); load(); }
    catch (e) { toast.error(errMsg(e)); }
  };

  const report = async () => {
    if (!user) return nav("/login");
    try { await api.post(`/api/reports`, { targetType: "strategy", targetId: id, reason: "Other", details: "Reported from detail page" }); toast.success("Reported to moderators"); }
    catch (e) { toast.error(errMsg(e)); }
  };

  if (!s) return <div className="flex min-h-screen items-center justify-center bg-[#080808] text-slate-400">Strategy not found or private.</div>;

  return (
    <div className="min-h-screen bg-[#080808] text-white">
      <div className="glass-nav sticky top-0 z-40 flex items-center justify-between px-6 py-4">
        <Brand />
        <Link to={user ? "/dashboard/community" : "/login"} className="text-sm text-slate-300 hover:text-white">← Back</Link>
      </div>
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="card-surface p-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-heading text-3xl font-bold">{s.name}</h1>
                {s.type === "BUILT_IN" && <span className="inline-flex items-center gap-1 rounded bg-[#FFB800]/10 border border-[#FFB800]/30 px-2 py-0.5 font-mono text-xs text-[#FFB800]"><Lock className="h-3 w-3" />BUILT-IN</span>}
              </div>
              <Link to={`/u/${s.owner?.username}`} className="mt-1 block font-mono text-sm text-[#2F8CFF] hover:underline">@{s.owner?.username}</Link>
            </div>
            <button data-testid="strategy-report-button" onClick={report} className="text-slate-500 hover:text-[#C62828]"><Flag className="h-5 w-5" /></button>
          </div>
          <p className="mt-4 text-slate-300">{s.description}</p>
          <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4 font-mono text-sm">
            <div><div className="label-mono">Timeframe</div><div className="text-white">{s.signalTimeframe}</div></div>
            <div><div className="label-mono">Expiry</div><div className="text-white">{s.expiry}</div></div>
            <div><div className="label-mono">Version</div><div className="text-white">v{s.version}</div></div>
            <div><div className="label-mono">Engine</div><div className="text-white">{s.engineType}</div></div>
          </div>
          <div className="mt-4 flex flex-wrap gap-1.5">
            {(s.indicators || []).map((i, idx) => <span key={idx} className="rounded bg-[#1A1A1A] px-2 py-0.5 font-mono text-xs text-[#2F8CFF]">{i.name || i}</span>)}
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button data-testid="detail-like-button" onClick={() => act("like")} variant="outline" className={`border-[#3A3A3A] bg-transparent ${s.liked ? "text-[#C62828]" : "text-white"}`}><Heart className="mr-2 h-4 w-4" fill={s.liked ? "currentColor" : "none"} />{s.likesCount}</Button>
            <Button data-testid="detail-save-button" onClick={() => act("save")} variant="outline" className={`border-[#3A3A3A] bg-transparent ${s.saved ? "text-[#2F8CFF]" : "text-white"}`}><Bookmark className="mr-2 h-4 w-4" fill={s.saved ? "currentColor" : "none"} />Add to Library</Button>
            {s.type !== "BUILT_IN" && <Button data-testid="detail-fork-button" onClick={() => act("fork")} className="bg-[#22C55E] text-black font-semibold"><GitFork className="mr-2 h-4 w-4" />Fork ({s.forksCount})</Button>}
          </div>
          {s.forkedFromStrategyId && <p className="mt-3 text-xs text-slate-500">Forked from another strategy · attribution preserved.</p>}
        </div>

        {/* Versions */}
        <div className="card-surface mt-6 p-6">
          <h2 className="font-heading text-lg font-semibold">Version history</h2>
          <div className="mt-3 space-y-2">
            {(s.versions || []).map((v) => (
              <div key={v.id} className="flex items-center justify-between border-b border-[#2E2E2E] pb-2 font-mono text-sm">
                <span className="text-[#2F8CFF]">v{v.version}</span>
                <span className="text-slate-400">{v.changelog}</span>
                <span className="text-slate-600 text-xs">{new Date(v.createdAt).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Comments */}
        <div className="card-surface mt-6 p-6">
          <h2 className="font-heading text-lg font-semibold">Comments</h2>
          <div className="mt-4 flex gap-2">
            <Textarea data-testid="comment-input" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Add a comment…" className="bg-[#0F0F0F] border-[#3A3A3A]" />
            <Button data-testid="comment-submit-button" onClick={postComment} disabled={!comment} className="bg-[#22C55E] text-black"><Send className="h-4 w-4" /></Button>
          </div>
          <div className="mt-4 space-y-3">
            {(s.comments || []).filter((c) => !c.hidden).map((c) => (
              <div key={c.id} className="border-b border-[#2E2E2E] pb-3">
                <div className="font-mono text-sm text-[#2F8CFF]">@{c.author?.username}</div>
                <p className="mt-1 text-sm text-slate-300">{c.body}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="mt-6 text-center text-xs text-slate-500">Historical backtest results, where shown, do not guarantee future results.</p>
      </div>
      <RiskBar />
    </div>
  );
}
