import React from "react";
import { useNavigate } from "react-router-dom";
import { Heart, Bookmark, GitFork, MessageSquare, Lock, Clock, Timer } from "lucide-react";
import { api } from "../lib/api";
import { toast } from "sonner";

export function StrategyCard({ s, onChange }) {
  const nav = useNavigate();
  const act = async (e, verb) => {
    e.stopPropagation();
    try {
      if (verb === "like") {
        s.liked ? await api.delete(`/api/community/strategies/${s.id}/like`) : await api.post(`/api/community/strategies/${s.id}/like`);
      } else if (verb === "save") {
        s.saved ? await api.delete(`/api/community/strategies/${s.id}/save`) : await api.post(`/api/community/strategies/${s.id}/save`);
        toast.success(s.saved ? "Removed from library" : "Added to your library");
      } else if (verb === "fork") {
        await api.post(`/api/community/strategies/${s.id}/fork`);
        toast.success("Forked to your strategies");
      }
      onChange && onChange();
    } catch (err) {
      toast.error("Please sign in to interact");
    }
  };
  const isBuiltIn = s.type === "BUILT_IN";
  return (
    <div
      data-testid={`strategy-card-${s.id}`}
      onClick={() => nav(`/community/${s.id}`)}
      className="card-surface cursor-pointer p-5 flex flex-col gap-3"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-heading font-semibold text-white text-lg leading-tight">{s.name}</h3>
            {isBuiltIn && (
              <span className="inline-flex items-center gap-1 rounded bg-[#FFB800]/10 border border-[#FFB800]/30 px-1.5 py-0.5 font-mono text-[10px] uppercase text-[#FFB800]">
                <Lock className="h-3 w-3" /> Built-in
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 font-mono mt-0.5">@{s.owner?.username || s.ownerUsername || "system"} · v{s.version}</p>
        </div>
      </div>
      <p className="text-sm text-slate-400 line-clamp-2 min-h-[2.5rem]">{s.description}</p>
      <div className="flex flex-wrap gap-1.5">
        {(s.indicators || []).slice(0, 3).map((i, idx) => (
          <span key={idx} className="rounded bg-[#1A1A1A] px-2 py-0.5 font-mono text-[11px] text-[#D4AF37]">
            {i.name || i}
          </span>
        ))}
      </div>
      <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
        <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{s.signalTimeframe}</span>
        <span className="flex items-center gap-1"><Timer className="h-3.5 w-3.5" />{s.expiry}</span>
      </div>
      <div className="mt-1 flex items-center justify-between border-t border-[#2E2E2E] pt-3">
        <div className="flex items-center gap-3 text-sm">
          <button data-testid={`strategy-card-like-button-${s.id}`} onClick={(e) => act(e, "like")}
            className={`flex items-center gap-1 transition-colors ${s.liked ? "text-[#C62828]" : "text-slate-400 hover:text-[#C62828]"}`}>
            <Heart className="h-4 w-4" fill={s.liked ? "currentColor" : "none"} />{s.likesCount}
          </button>
          <button data-testid={`strategy-card-save-button-${s.id}`} onClick={(e) => act(e, "save")}
            className={`flex items-center gap-1 transition-colors ${s.saved ? "text-[#D4AF37]" : "text-slate-400 hover:text-[#D4AF37]"}`}>
            <Bookmark className="h-4 w-4" fill={s.saved ? "currentColor" : "none"} />{s.savesCount}
          </button>
          <span className="flex items-center gap-1 text-slate-400"><GitFork className="h-4 w-4" />{s.forksCount}</span>
          <span className="flex items-center gap-1 text-slate-400"><MessageSquare className="h-4 w-4" />{s.commentsCount}</span>
        </div>
        {!isBuiltIn && (
          <button data-testid={`strategy-card-fork-button-${s.id}`} onClick={(e) => act(e, "fork")}
            className="rounded bg-[#1A1A1A] px-2.5 py-1 font-mono text-[11px] text-[#D4AF37] hover:bg-[#262626] transition-colors">
            FORK
          </button>
        )}
      </div>
    </div>
  );
}
