import React, { useState } from "react";
import { Outlet, NavLink, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { Brand } from "../../components/Brand";
import {
  Shield, LayoutGrid, Users, CreditCard, MonitorSmartphone, BadgeCheck, Boxes,
  Flag, Chrome, Settings, ScrollText, TerminalSquare, ArrowLeft, Activity, Plug, Menu, X,
} from "lucide-react";

const NAV = [
  ["", "Dashboard", LayoutGrid],
  ["launch", "Launch Status", BadgeCheck],
  ["trading-ops", "Trading Ops", Activity],
  ["kaos-ai", "KAOS AI", Activity],
  ["follow-us", "Follow Us Links", Activity],
  ["analytics", "Visitors & Referrals", Activity],
  ["affiliates", "Affiliates", BadgeCheck],
  ["commerce", "Payments & Payouts", CreditCard],
  ["radar", "Radar Sources & AI", Activity],
  ["connectors", "Connectors", Plug],
  ["users", "Users", Users],
  ["subscriptions", "Subscriptions", CreditCard],
  ["devices", "Devices", MonitorSmartphone],
  ["affiliate", "Affiliate Queue", BadgeCheck],
  ["strategies", "Strategies", Boxes],
  ["moderation", "Moderation", Flag],
  ["extension", "Extension Releases", Chrome],
  ["settings", "Settings", Settings],
  ["audit", "Audit Log", ScrollText],
  ["extension-test", "API Simulator", TerminalSquare],
];

export default function AdminLayout() {
  const { user } = useAuth();
  const [mobileNav, setMobileNav] = useState(false);

  const renderSidebar = (onNavigate) => (
    <>
      <div className="border-b border-[#DC2626]/20 px-5 py-5">
        <div className="flex items-center justify-between">
          <Brand />
          {onNavigate && (
            <button onClick={onNavigate} data-testid="admin-mobile-menu-close" className="text-slate-400 hover:text-white lg:hidden">
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
        <div className="mt-3 inline-flex items-center gap-1.5 rounded border border-red-500/30 bg-red-500/10 px-2.5 py-1 font-mono text-xs uppercase tracking-wider text-red-400">
          <Shield className="h-3.5 w-3.5" /> Admin Portal
        </div>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-3">
        {NAV.filter(([path])=>(path!=="analytics"||["admin","super_admin"].includes(user?.role))&&!["commerce","radar","launch","follow-us"].includes(path) || user?.role==="super_admin").map(([path, label, Icon]) => (
          <NavLink key={path} to={`/admin/${path}`} end={path === ""} onClick={onNavigate} data-testid={`${onNavigate ? "mobile-" : ""}admin-nav-${path || "dashboard"}`}
            className={({ isActive }) => `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${isActive ? "bg-red-500/10 text-red-300" : "text-slate-400 hover:bg-[#111111] hover:text-white"}`}>
            <Icon className="h-4 w-4" />{label}
          </NavLink>
        ))}
      </nav>
      <Link to="/dashboard" onClick={onNavigate} className="mx-3 mb-4 flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-400 hover:bg-[#111111] hover:text-white">
        <ArrowLeft className="h-4 w-4" /> Back to member area
      </Link>
    </>
  );

  return (
    <div className="flex min-h-screen bg-[#080808] text-white">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-[#DC2626]/20 bg-[#0A0A0A] lg:flex">
        {renderSidebar()}
      </aside>

      {mobileNav && (
        <div className="fixed inset-0 z-[60] lg:hidden" data-testid="admin-mobile-nav-drawer">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileNav(false)} />
          <aside className="absolute left-0 top-0 flex h-full w-72 max-w-[85%] flex-col border-r border-[#DC2626]/20 bg-[#0A0A0A]">
            {renderSidebar(() => setMobileNav(false))}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-[#DC2626]/20 bg-[#0A0A0A] px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <button data-testid="admin-mobile-menu-button" onClick={() => setMobileNav(true)} className="text-slate-300 hover:text-white lg:hidden">
              <Menu className="h-6 w-6" />
            </button>
            <span className="font-mono text-xs uppercase tracking-widest text-red-400">Restricted · {user?.role}</span>
          </div>
          <span className="hidden font-mono text-sm text-slate-400 sm:block">{user?.email}</span>
        </header>
        <main className="flex-1 overflow-y-auto p-4 sm:p-6"><Outlet /></main>
      </div>
    </div>
  );
}
