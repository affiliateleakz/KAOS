import React from "react";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AuthCallback from "./components/AuthCallback";

import Landing from "./pages/Landing";
import Privacy from "./pages/Privacy";
import { Login, Register, ForgotPassword, ResetPassword } from "./pages/Auth";
import Onboarding from "./pages/Onboarding";
import CommunityDetail from "./pages/CommunityDetail";
import SharePage from "./pages/SharePage";
import Profile from "./pages/Profile";
import { PaymentSuccess, PaymentCancel } from "./pages/Payment";
import DashboardLayout from "./pages/dashboard/DashboardLayout";
import * as DP from "./pages/dashboard/pages";
import Trading from "./pages/dashboard/Trading";
import OpportunityRadar from "./pages/dashboard/OpportunityRadar";
import BrokerConnections from "./pages/dashboard/BrokerConnections";
import PaperTrading from "./pages/dashboard/PaperTrading";
import MarketIntelligence from "./pages/dashboard/MarketIntelligence";
import { AffiliatePage, AIPage } from "./pages/dashboard/AffiliateAI";
import AdminLayout from "./pages/admin/AdminLayout";
import * as AP from "./pages/admin/pages";
import { TradingOps, Connectors } from "./pages/admin/TradingOps";
import { AICenter, Affiliates } from "./pages/admin/AICenter";
import ExtensionSimulator from "./pages/admin/ExtensionSimulator";
import DataSources from "./pages/admin/DataSources";

function Protected({ children, role }) {
  const { user, loading } = useAuth();
  if (loading || user === undefined)
    return <div className="flex min-h-screen items-center justify-center font-mono text-sm text-slate-400">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (role) {
    const rank = { user: 0, moderator: 1, admin: 2, super_admin: 3 };
    if ((rank[user.role] || 0) < rank[role]) return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/privacy/" element={<Privacy />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/community/:id" element={<CommunityDetail />} />
      <Route path="/u/:username" element={<Profile />} />
      <Route path="/s/:id" element={<SharePage />} />
      <Route path="/payment/success" element={<PaymentSuccess />} />
      <Route path="/payment/cancel" element={<PaymentCancel />} />

      <Route path="/onboarding" element={<Protected><Onboarding /></Protected>} />

      <Route path="/dashboard" element={<Protected><DashboardLayout /></Protected>}>
        <Route index element={<DP.Overview />} />
        <Route path="trading" element={<Trading />} />
        <Route path="opportunities" element={<OpportunityRadar />} />
        <Route path="intelligence" element={<MarketIntelligence />} />
        <Route path="brokers" element={<BrokerConnections />} />
        <Route path="paper" element={<PaperTrading />} />
        <Route path="kaos-ai" element={<AIPage />} />
        <Route path="affiliate" element={<AffiliatePage />} />
        <Route path="strategies" element={<DP.MyStrategies />} />
        <Route path="community" element={<DP.CommunityFeed />} />
        <Route path="indicators" element={<DP.Indicators />} />
        <Route path="scripts" element={<DP.Scripts />} />
        <Route path="backtests" element={<DP.Backtests />} />
        <Route path="saved" element={<DP.Saved />} />
        <Route path="following" element={<DP.Following />} />
        <Route path="subscription" element={<DP.Subscription />} />
        <Route path="devices" element={<DP.Devices />} />
        <Route path="downloads" element={<DP.Downloads />} />
        <Route path="account" element={<DP.Account />} />
        <Route path="support" element={<DP.Support />} />
      </Route>

      <Route path="/admin" element={<Protected role="moderator"><AdminLayout /></Protected>}>
        <Route index element={<AP.AdminDashboard />} />
        <Route path="trading-ops" element={<TradingOps />} />
        <Route path="kaos-ai" element={<AICenter />} />
        <Route path="affiliates" element={<Affiliates />} />
        <Route path="connectors" element={<Connectors />} />
        <Route path="sources" element={<DataSources />} />
        <Route path="users" element={<AP.Users />} />
        <Route path="subscriptions" element={<AP.Subscriptions />} />
        <Route path="devices" element={<AP.AdminDevices />} />
        <Route path="affiliate" element={<AP.Affiliate />} />
        <Route path="strategies" element={<AP.AdminStrategies />} />
        <Route path="moderation" element={<AP.Moderation />} />
        <Route path="extension" element={<AP.ExtensionReleases />} />
        <Route path="settings" element={<AP.Settings />} />
        <Route path="audit" element={<AP.Audit />} />
        <Route path="extension-test" element={<ExtensionSimulator />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster theme="dark" position="top-right" richColors />
        <AppRouter />
      </BrowserRouter>
    </AuthProvider>
  );
}
