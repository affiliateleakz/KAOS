import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Brand } from "../components/Brand";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Progress } from "../components/ui/progress";
import { Check, ExternalLink, ArrowRight } from "lucide-react";
import { toast } from "sonner";

const STEPS = [
  "Create Account", "Verify Email", "Pocket Option Signup", "Affiliate Verification",
  "Choose Membership", "Checkout", "Membership Active", "Install Extension", "Open & Login",
];

export default function Onboarding() {
  const nav = useNavigate();
  const { user, refreshUser } = useAuth();
  const [step, setStep] = useState(2);
  const [affCfg, setAffCfg] = useState(null);
  const [plans, setPlans] = useState([]);
  const [poUid, setPoUid] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/api/affiliate/config").then((r) => setAffCfg(r.data)).catch(() => {});
    api.get("/api/billing/plans").then((r) => setPlans(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!user) return;
    // resume at server-tracked step
    let s = 2;
    if (user.email_verified) s = 3;
    if (user.affiliate_status === "PENDING") s = 4;
    if (user.affiliate_status === "VERIFIED") s = 5;
    if (user.membership_status === "ACTIVE") s = 7;
    setStep((prev) => Math.max(prev, s));
  }, [user]);

  const verifyEmail = async () => {
    setBusy(true);
    try {
      const token = sessionStorage.getItem("verifyToken");
      await api.post("/api/auth/verify-email", { token });
      await refreshUser();
      toast.success("Email verified");
      setStep(3);
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  const submitAffiliate = async () => {
    setBusy(true);
    try {
      await api.post("/api/affiliate/submit", { poUid });
      await refreshUser();
      toast.success("Submitted for verification");
      setStep(4);
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  const checkout = async (lookup_key) => {
    setBusy(true);
    try {
      const { data } = await api.post("/api/billing/checkout", { lookup_key, origin_url: window.location.origin });
      window.location.href = data.checkout_url;
    } catch (e) { toast.error(errMsg(e)); setBusy(false); }
  };

  const pct = Math.round((step / 9) * 100);

  return (
    <div className="min-h-screen bg-[#080808] text-white">
      <div className="glass-nav px-6 py-4"><Brand /></div>
      <div className="mx-auto max-w-3xl px-4 py-10">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <span className="label-mono">Step {step} of 9</span>
            <span className="font-mono text-sm text-[#D4AF37]">{pct}%</span>
          </div>
          <Progress value={pct} className="mt-2 h-2 bg-[#111111]" />
          <p className="mt-3 font-heading text-xl font-semibold">{STEPS[step - 1]}</p>
        </div>

        <div className="card-surface p-8">
          {step === 2 && (
            <div>
              <p className="text-slate-400">We use demo-mode email verification. Click below to verify instantly.</p>
              <Button data-testid="onboarding-verify-email-button" onClick={verifyEmail} disabled={busy} className="mt-6 bg-[#22C55E] text-black font-semibold">Verify Email</Button>
            </div>
          )}
          {step === 3 && (
            <div>
              <h3 className="font-heading text-lg font-semibold">Create your Pocket Option account</h3>
              <p className="mt-2 text-slate-400">{affCfg?.instructions}</p>
              <a href={affCfg?.affiliateUrl} target="_blank" rel="noreferrer" data-testid="onboarding-create-po-button"
                className="mt-4 inline-flex items-center gap-2 rounded-md bg-[#D4AF37] px-5 py-2.5 font-semibold text-[#080808] hover:opacity-90">
                Create Pocket Option Account <ExternalLink className="h-4 w-4" />
              </a>
              <p className="mt-3 text-xs text-slate-500">Affiliate disclosure: we may earn a commission for referrals.</p>
              <div className="mt-6"><Button data-testid="onboarding-po-done-button" variant="outline" className="border-[#3A3A3A] bg-transparent text-white" onClick={() => setStep(4)}>I've created my account <ArrowRight className="ml-2 h-4 w-4" /></Button></div>
            </div>
          )}
          {step === 4 && (
            <div>
              {user?.affiliate_status === "VERIFIED" ? (
                <div className="text-[#D4AF37]"><Check className="mb-2 h-8 w-8" /> Affiliate verified! Continue to membership.</div>
              ) : user?.affiliate_status === "PENDING" ? (
                <div>
                  <p className="text-[#FFB800]">Your affiliate submission is pending manual review. You'll be notified once verified.</p>
                  <Button className="mt-4" variant="outline" onClick={refreshUser}>Refresh status</Button>
                </div>
              ) : (
                <div>
                  <Label className="label-mono">Pocket Option UID</Label>
                  <Input data-testid="affiliate-uid-input" value={poUid} onChange={(e) => setPoUid(e.target.value)} placeholder="e.g. 77345678" className="mt-1 bg-[#0F0F0F] border-[#3A3A3A]" />
                  <p className="mt-2 text-xs text-slate-500">Submit only your Pocket Option UID for verification.</p>
                  <Button data-testid="affiliate-submit-button" onClick={submitAffiliate} disabled={busy || !poUid} className="mt-4 bg-[#22C55E] text-black font-semibold">Submit for verification</Button>
                </div>
              )}
              {user?.affiliate_status === "VERIFIED" && (
                <Button className="mt-4 bg-[#22C55E] text-black font-semibold" onClick={() => setStep(5)}>Continue</Button>
              )}
            </div>
          )}
          {step === 5 && (
            <div>
              <h3 className="font-heading text-lg font-semibold">Choose your membership</h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {plans.map((p) => (
                  <div key={p.id} className="card-surface p-5">
                    <div className="font-heading font-semibold">{p.name}</div>
                    <div className="mt-1 font-mono text-2xl text-[#D4AF37]">${(p.amount / 100).toFixed(0)}<span className="text-sm text-slate-500">/{p.interval}</span></div>
                    <Button data-testid={`onboarding-select-plan-${p.id}`} onClick={() => checkout(p.lookup_key)} disabled={busy} className="mt-4 w-full bg-[#22C55E] text-black font-semibold">Select</Button>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-xs text-slate-500">Stripe test mode — use card 4242 4242 4242 4242.</p>
            </div>
          )}
          {step >= 7 && (
            <div>
              <div className="text-[#D4AF37]"><Check className="mb-2 h-8 w-8" /> Membership active!</div>
              <p className="mt-2 text-slate-400">Download the extension, install it, and log in with your account to authorize.</p>
              <div className="mt-6 flex gap-3">
                <Button data-testid="onboarding-goto-dashboard" onClick={() => nav("/dashboard")} className="bg-[#22C55E] text-black font-semibold">Go to Dashboard</Button>
                <Button variant="outline" className="border-[#3A3A3A] bg-transparent text-white" onClick={() => nav("/dashboard/downloads")}>Download Extension</Button>
              </div>
            </div>
          )}
          {step === 6 && <p className="text-slate-400">Redirecting to secure checkout…</p>}
        </div>

        <button onClick={() => nav("/dashboard")} className="mt-6 text-sm text-slate-500 hover:text-slate-300">Skip for now →</button>
      </div>
    </div>
  );
}
