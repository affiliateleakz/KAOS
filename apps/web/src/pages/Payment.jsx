import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import {useAuth} from "../context/AuthContext";
import {registrationLink} from "../lib/purchaseFlow";
import { Brand } from "../components/Brand";
import { Button } from "../components/ui/button";
import { Check, X, Loader2 } from "lucide-react";

export function PaymentSuccess() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [state, setState] = useState("checking");
  const {refreshUser}=useAuth();
  const sessionId = params.get("session_id");

  useEffect(() => {
    if (!sessionId) { setState("error"); return; }
    let tries = 0,cancelled=false,timer;
    const poll = async () => {
      try {
        const { data } = await api.get(`/api/billing/status/${encodeURIComponent(sessionId)}`);
        if(cancelled)return;
        if (data.state === "active" || data.membershipStatus === "ACTIVE") { await refreshUser();if(!cancelled)setState("done");return; }
      } catch {}
      if(cancelled)return;
      if (++tries < 8) timer=setTimeout(poll, 2000);
      else setState("pending");
    };
    poll();
    return ()=>{cancelled=true;clearTimeout(timer);};
  }, [sessionId,refreshUser]);

  return (
    <div className="flex min-h-screen flex-col bg-[#080808] text-white">
      <div className="glass-nav px-6 py-4"><Brand /></div>
      <div className="flex flex-1 items-center justify-center px-4">
        <div className="card-surface max-w-md p-8 text-center" data-testid="payment-success-card">
          {state === "checking" && <><Loader2 className="mx-auto h-10 w-10 animate-spin text-[#D4AF37]" /><p className="mt-4 text-slate-400">Confirming your payment…</p></>}
          {state === "done" && <><Check className="mx-auto h-12 w-12 text-[#D4AF37]" /><h1 className="mt-4 font-heading text-2xl font-bold">Membership Active!</h1><p className="mt-2 text-slate-400">Your subscription is confirmed.</p><Button data-testid="payment-continue-button" onClick={() => nav("/dashboard")} className="mt-6 bg-[#22C55E] text-black font-semibold">Go to Dashboard</Button></>}
          {state === "pending" && <><Loader2 className="mx-auto h-10 w-10 text-[#FFB800]" /><p className="mt-4 text-slate-400">Your payment has not been confirmed yet. Check your payment status before trying again; paid access activates only after confirmation.</p><Button onClick={() => nav("/dashboard")} className="mt-6">Dashboard</Button></>}
          {state === "error" && <><X className="mx-auto h-12 w-12 text-[#C62828]" /><p className="mt-4 text-slate-400">Missing session.</p></>}
        </div>
      </div>
    </div>
  );
}

export function PaymentCancel() {
  const nav = useNavigate();
  const [params]=useSearchParams();
  const planId=params.get("plan");
  return (
    <div className="flex min-h-screen flex-col bg-[#080808] text-white">
      <div className="glass-nav px-6 py-4"><Brand /></div>
      <div className="flex flex-1 items-center justify-center px-4">
        <div className="card-surface max-w-md p-8 text-center">
          <X className="mx-auto h-12 w-12 text-[#C62828]" />
          <h1 className="mt-4 font-heading text-2xl font-bold">Checkout canceled</h1>
          <Button onClick={() => nav(planId?registrationLink(planId,params):"/memberships")} className="mt-6 bg-[#d4af37] text-black font-semibold">Return to checkout</Button>
        </div>
      </div>
    </div>
  );
}
