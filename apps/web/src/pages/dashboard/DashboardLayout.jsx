import React, { useEffect, useState } from "react";
import { Outlet, NavLink, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../lib/api";
import { Brand, RiskBar } from "../../components/Brand";
import {
  LayoutGrid, Boxes, Users, Activity, FileCode, LineChart, Bookmark, UserPlus,
  CreditCard, MonitorSmartphone, Download, Settings, LifeBuoy, Bell, LogOut, Shield, Bot, Menu, X,
} from "lucide-react";

const NAV = [
  ["", "Dashboard", LayoutGrid],
  ["trading", "Trading", Bot],
  ["opportunities", "Opportunity Radar", Activity],
  ["public-trades", "Political & Wall Street Trades", LineChart],
  ["crypto-scanner", "Crypto Scanner & Heat Map", Activity],
  ["stock-heatmap", "Stock Heat Map", LineChart],
  ["brokers", "Broker Connections", MonitorSmartphone],
  ["kaos-ai", "KAOS AI", Activity],
  ["strategies", "My Strategies", Boxes],
  ["community", "Community", Users],
  ["indicators", "Indicators", Activity],
  ["scripts", "Scripts", FileCode],
  ["backtests", "Backtests", LineChart],
  ["saved", "Saved", Bookmark],
  ["following", "Following", UserPlus],
  ["subscription", "Subscription", CreditCard],
  ["affiliate", "Affiliate Program", UserPlus],
  ["devices", "Devices", MonitorSmartphone],
  ["downloads", "Downloads", Download],
  ["account", "Account", Settings],
  ["support", "Support", LifeBuoy],
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [notifs, setNotifs] = useState([]);
  const [open, setOpen] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);

  const loadNotifs = () => api.get("/api/notifications").then((r) => setNotifs(r.data)).catch(() => {});
  useEffect(() => { loadNotifs(); }, []);
  const unread = notifs.filter((n) => !n.read).length;

  const doLogout = async () => { await logout(); nav("/"); };
  const isAdmin = ["moderator", "admin", "super_admin"].includes(user?.role);

  const renderSidebar = (onNavigate) => (
    <>
      <div className="flex items-center justify-between px-5 py-5">
        <Brand />
        {onNavigate && (
          <button onClick={onNavigate} data-testid="mobile-menu-close" className="text-slate-400 hover:text-white lg:hidden">
            <X className="h-5 w-5" />
          </button>
        )}
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3">
        {NAV.map(([path, label, Icon]) => (
          <NavLink key={path} to={`/dashboard/${path}`} end={path === ""} onClick={onNavigate}
            data-testid={`${onNavigate ? "mobile-" : ""}nav-${label.toLowerCase().replace(/ /g, "-")}-link`}
            className={({ isActive }) => `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${isActive ? "bg-[#D4AF37]/10 text-[#D4AF37]" : "text-slate-400 hover:bg-[#111111] hover:text-white"}`}>
            <Icon className="h-4 w-4" />{label}
          </NavLink>
        ))}
      </nav>
      {isAdmin && (
        <Link to="/admin" onClick={onNavigate} data-testid="nav-admin-link" className="mx-3 mb-2 flex items-center gap-2 rounded-md border border-[#DC2626]/30 bg-[#DC2626]/10 px-3 py-2 text-sm text-red-400 hover:bg-[#DC2626]/20">
          <Shield className="h-4 w-4" /> Admin Portal
        </Link>
      )}
      <button onClick={() => { if (onNavigate) onNavigate(); doLogout(); }} data-testid="logout-button" className="mx-3 mb-4 flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-400 hover:bg-[#111111] hover:text-white">
        <LogOut className="h-4 w-4" /> Log out
      </button>
    </>
  );

  return (
    <div className="flex min-h-screen bg-[#080808] text-white">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-[#2E2E2E] bg-[#0A0A0A] lg:flex">
        {renderSidebar()}
      </aside>

      {mobileNav && (
        <div className="fixed inset-0 z-[60] lg:hidden" data-testid="mobile-nav-drawer">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileNav(false)} />
          <aside className="absolute left-0 top-0 flex h-full w-72 max-w-[85%] flex-col border-r border-[#2E2E2E] bg-[#0A0A0A]">
            {renderSidebar(() => setMobileNav(false))}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="glass-nav flex items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3 lg:hidden">
            <button data-testid="mobile-menu-button" onClick={() => setMobileNav(true)} className="text-slate-300 hover:text-white">
              <Menu className="h-6 w-6" />
            </button>
            <Brand />
          </div>
          <div className="hidden lg:block"><span className="label-mono">Member Portal</span></div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <button data-testid="notifications-button" onClick={() => { setOpen(!open); if (!open && unread) api.post("/api/notifications/read").then(loadNotifs); }} className="relative text-slate-400 hover:text-white">
                <Bell className="h-5 w-5" />
                {unread > 0 && <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-[#C62828] text-[10px] font-bold">{unread}</span>}
              </button>
              {open && (
                <div className="absolute right-0 mt-2 w-80 rounded-lg border border-[#2E2E2E] bg-[#0F0F0F] p-2 shadow-xl z-50">
                  {notifs.length === 0 && <p className="p-4 text-center text-sm text-slate-500">No notifications</p>}
                  {notifs.slice(0, 10).map((n) => (
                    <Link key={n.id} to={n.link || "#"} onClick={() => setOpen(false)} className="block rounded p-2 text-sm text-slate-300 hover:bg-[#111111]">{n.message}</Link>
                  ))}
                </div>
              )}
            </div>
            <Link to={`/u/${user?.username}`} className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#1A1A1A] text-sm font-bold text-[#D4AF37]">{(user?.name || "U")[0]}</span>
            </Link>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 sm:p-6"><Outlet /></main>
        <div style={{fontSize:12,padding:"6px 24px",textAlign:"right"}}><a href="/privacy.html" style={{color:"#b9a36e"}}>Privacy Policy</a></div>
        <RiskBar />
      </div>
    </div>
  );
}
