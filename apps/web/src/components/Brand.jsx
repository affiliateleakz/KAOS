import React from "react";
import { Link } from "react-router-dom";
import { CONFIG } from "../config";

export function Brand({ size = "md", className = "" }) {
  const h = size === "lg" ? "h-20" : "h-16";
  return (
    <Link to="/" data-testid="brand-logo" className={`flex items-center group ${className}`}>
      <img src={CONFIG.logoHorizontal} alt={CONFIG.productName} className={`${h} w-auto object-contain`} />
    </Link>
  );
}

const MAP = {
  ACTIVE: "text-[#2F8CFF] bg-[#2F8CFF]/10 border-[#2F8CFF]/30",
  TRIAL: "text-[#2F8CFF] bg-[#2F8CFF]/10 border-[#2F8CFF]/30",
  VERIFIED: "text-[#2F8CFF] bg-[#2F8CFF]/10 border-[#2F8CFF]/30",
  PENDING: "text-amber-300 bg-amber-400/10 border-amber-400/30",
  MANUAL_REVIEW: "text-amber-300 bg-amber-400/10 border-amber-400/30",
  PAST_DUE: "text-amber-300 bg-amber-400/10 border-amber-400/30",
  CANCELED: "text-slate-400 bg-slate-500/10 border-slate-500/30",
  EXPIRED: "text-[#C62828] bg-[#C62828]/10 border-[#C62828]/40",
  SUSPENDED: "text-[#C62828] bg-[#C62828]/10 border-[#C62828]/40",
  REVOKED: "text-[#C62828] bg-[#C62828]/10 border-[#C62828]/40",
  REJECTED: "text-[#C62828] bg-[#C62828]/10 border-[#C62828]/40",
  NOT_STARTED: "text-slate-400 bg-slate-500/10 border-slate-500/30",
};

export function StatusBadge({ value, testid }) {
  const cls = MAP[value] || "text-slate-300 bg-slate-500/10 border-slate-500/30";
  return (
    <span data-testid={testid} className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1 font-mono text-xs uppercase tracking-wider ${cls}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {value || "—"}
    </span>
  );
}

export function RiskBar() {
  return (
    <div data-testid="risk-disclosure-bar" className="border-t border-[#2E2E2E] bg-[#0c0c0c] px-4 py-3 text-center text-xs text-slate-500">
      Trading involves substantial risk of loss. Historical backtest results do not guarantee future results. Not financial advice.
    </div>
  );
}
