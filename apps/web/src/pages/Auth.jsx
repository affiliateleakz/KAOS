import React, { useState, useEffect } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import CheckoutHandoff from "../components/CheckoutHandoff";
import {registrationLink,purchaseLoginLink} from "../lib/purchaseFlow";
import {planPrice} from './Memberships';
import {useReferralCapture} from '../lib/useReferralCapture';
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Brand } from "../components/Brand";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";

function Shell({ title, subtitle, children }) {
  return (
    <div className="kaos-auth-shell">
      <div className="kaos-auth-art" aria-hidden="true" />
      <header className="kaos-auth-nav">
        <Brand />
        <Link to="/" className="kaos-auth-back">← Back to KAOS</Link>
      </header>
      <main className="kaos-auth-layout">
        <section className="kaos-auth-story" aria-label="KAOS Trading">
          <span className="kaos-auth-eyebrow">TRADE WITH KAOS</span>
          <h2>Your bot. Your data.<br /><span>Your KAOS.</span></h2>
          <p>Your account. Your strategies. Your control.</p>
        </section>
        <section className="kaos-auth-content" aria-label={title}>
          <div className="kaos-auth-card">
            <div className="kaos-auth-card-heading"><span className="kaos-auth-rune" aria-hidden="true">ᚠ</span><span>KAOS MEMBER ACCESS</span><span className="kaos-auth-rule" /></div>
            <h1>{title}</h1>
            {subtitle && <p className="kaos-auth-subtitle">{subtitle}</p>}
            <div className="kaos-auth-form">{children}</div>
          </div>
          <footer className="kaos-auth-footer"><a href="/privacy.html">Privacy policy</a><span>·</span><a href="mailto:support@tradewithkaos.com">Support</a></footer>
        </section>
      </main>
    </div>
  );
}

function GoogleButton({planId,refCode}={}) {
  const nav = useNavigate();
  const { setUser } = useAuth();
  const [purchaseSearch] = useSearchParams();
  const [err, setErr] = useState("");
  const clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || "588189138338-oa8uu7k1dsrf40fj2tga7svqfus09tli.apps.googleusercontent.com";

  useEffect(() => {
    const render = () => {
      if (!window.google?.accounts?.id) return;
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }) => {
          try {
            setErr("");
            const { data } = await api.post("/api/auth/google/credential", { credential, ...(planId?{planId,refCode}: {}) });
            setUser(data);
            nav(planId ? (planId==='free'?'/dashboard':registrationLink(planId,purchaseSearch)) : ["moderator", "admin", "super_admin"].includes(data?.role) ? "/admin" : "/dashboard");
          } catch (e) { setErr(errMsg(e)); }
        }
      });
      const target = document.getElementById("kaos-google-button");
      if (target) window.google.accounts.id.renderButton(target, { theme: "filled_black", size: "large", width: Math.min(350, target.clientWidth || 350), text: "continue_with" });
    };
    if (window.google?.accounts?.id) { render(); return; }
    let script = document.querySelector('script[data-kaos-google="1"]');
    if (!script) {
      script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true; script.defer = true; script.dataset.kaosGoogle = "1";
      document.head.appendChild(script);
    }
    const onError = () => setErr("Google sign-in could not load. Check network access to accounts.google.com and the Google OAuth authorized origins.");
    script.addEventListener("error", onError);
    script.addEventListener("load", render);
    return () => { script?.removeEventListener("load", render); script?.removeEventListener("error", onError); };
  }, [clientId, nav, setUser, planId, refCode, purchaseSearch]);

  return <div className="mt-3"><div id="kaos-google-button" data-testid="google-login-button" className="flex justify-center" />{err && <p className="mt-2 text-sm text-[#C62828]">{err}</p>}</div>;
}

export function Login() {
  const nav = useNavigate();
  const { login } = useAuth();
  const [sp] = useSearchParams();
  const planId=sp.get("plan");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const u = await login(email, password);
      const isAdmin = ["moderator", "admin", "super_admin"].includes(u?.role);
      nav(planId&&planId!=="free"?registrationLink(planId,sp):(isAdmin ? "/admin" : "/dashboard"));
    }
    catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <Shell title="Welcome back" subtitle="Sign in to your member account.">
      <p className="mb-4 text-xs leading-relaxed text-slate-400" data-testid="service-learning-notice">KAOS uses de-identified settled trade and market features to train personal, shared and owner models as a standard part of the service. Account credentials, payments, balances and raw screenshots are excluded from training. <a href="/privacy.html" className="text-[#e8c46f] underline">Privacy and data use</a>.</p>
      <form onSubmit={submit} className="space-y-4">
        <div><Label htmlFor="login-email" className="label-mono">Email address</Label>
          <Input id="login-email" autoComplete="username" placeholder="you@example.com" data-testid="login-email-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="kaos-auth-input mt-2" /></div>
        <div><Label htmlFor="login-password" className="label-mono">Password</Label>
          <Input id="login-password" autoComplete="current-password" placeholder="Enter your password" data-testid="login-password-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="kaos-auth-input mt-2" /></div>
        {err && <p role="alert" data-testid="login-error" className="text-sm text-[#C62828]">{err}</p>}
        <Button data-testid="login-submit-button" disabled={busy} className="kaos-auth-submit w-full font-semibold">{busy ? "Signing in…" : "Sign In"}</Button>
      </form>
      <div className="kaos-auth-divider"><span>or continue with</span></div>
      <GoogleButton planId={planId||undefined} refCode={sp.get("ref")||undefined}/>
      <div className="mt-6 flex justify-between gap-3 text-sm">
        <Link to="/forgot-password" data-testid="forgot-password-link" className="text-slate-400 hover:text-[#D4AF37]">Forgot password?</Link>
        <Link to={planId?registrationLink(planId,sp):"/register"} data-testid="go-register-link" className="text-[#D4AF37] hover:underline">Join now</Link>
      </div>
    </Shell>
  );
}

export function Register({purchase=false}) {
  const nav = useNavigate();
  const { register,user,loading:authLoading } = useAuth();
  const [sp] = useSearchParams();
  useReferralCapture(sp);
  const planId=sp.get('plan');
  const [catalog,setCatalog]=useState(null),[catalogError,setCatalogError]=useState('');
  const selectionQuery=new URLSearchParams(sp);selectionQuery.delete('plan');
  const selectionUrl='/register'+(selectionQuery.size?'?'+selectionQuery.toString():'');
  const selected=catalog?.plans?.find(plan=>plan.id===planId);
  async function loadMembership(){setCatalogError('');try{const r=await api.get('/api/billing/memberships');if(!Array.isArray(r.data?.plans))throw Error('Invalid membership catalog');setCatalog(r.data);}catch{setCatalogError('Cannot load your selected membership. Please retry.');}}
  useEffect(()=>{if(planId)loadMembership();},[planId]);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      let refCode; try { refCode = sp.get("ref") || localStorage.getItem("kaos_ref") || undefined; } catch (e3) { refCode = sp.get("ref") || undefined; }
      if(purchase&&!catalog?.checkoutEnabled)throw Error('Paid checkout is temporarily unavailable. Please retry later.');
      const data = await register({ ...form, refCode, planId:selected.id });
      if (data.verificationToken) sessionStorage.setItem("verifyToken", data.verificationToken);
      if(selected.id==='free'){toast.success('Your free account is ready.');nav('/dashboard');}
      else if(!purchase)nav(registrationLink(selected.id,sp),{replace:true});
    } catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };
  if(!planId || (catalog&&!selected))return <Navigate to={selectionUrl} replace/>;
  if(!selected)return <Shell title="Your membership" subtitle="Confirming the current plan details."><p role={catalogError?'alert':'status'}>{catalogError||'Loading membership…'}</p>{catalogError&&<button onClick={loadMembership} className="mt-4 text-[#e8c46f] underline">Retry membership</button>}<Link to={selectionUrl} className="mt-4 block text-[#e8c46f]">Back to membership choices</Link></Shell>;
  if(selected.id!=='free'&&!purchase)return <Navigate to={registrationLink(selected.id,sp)} replace/>;
  if(purchase&&selected.id==='free')return <Navigate to={registrationLink('free',sp)} replace/>;
  if(purchase&&authLoading)return <Shell title="Your secure checkout"><p role="status">Checking your account…</p></Shell>;
  if(purchase&&!catalog.checkoutEnabled)return <Shell title="Checkout temporarily unavailable" subtitle="No payment has been started."><section data-testid="paid-checkout-unavailable"><p role="status" className="text-sm text-slate-300">We cannot accept membership payments right now. Please retry later or choose a Free membership. No paid membership has been activated.</p><button onClick={loadMembership} className="kaos-auth-submit mt-5 w-full">Retry payment availability</button><Link to={registrationLink('free',sp)} className="mt-4 block text-[#e8c46f] underline">Choose Free instead</Link><Link to={selectionUrl} className="mt-4 block text-[#e8c46f] underline">Back to memberships</Link>{user?.role==='super_admin'&&<Link to="/admin/commerce" className="mt-4 block text-[#e8c46f] underline">Review payment setup</Link>}</section></Shell>;
  if(purchase&&user)return <Shell title="Secure membership checkout" subtitle={selected.name+' · '+planPrice(selected)+' / '+selected.interval}><CheckoutHandoff plan={selected} user={user}/></Shell>;
  let referral=sp.get('ref');try{referral=referral||localStorage.getItem('kaos_ref')||undefined;}catch{}
  return (
    <Shell title={purchase?"Complete your membership":"Create your account"} subtitle={purchase?"Create your sign-in, then continue directly to secure Stripe payment.":"Step 2 · Your membership choice is saved with your account."}>
      <p className="mb-4 text-xs leading-relaxed text-slate-400" data-testid="registration-learning-notice">Using KAOS includes de-identified settled trade and market data contributing to personal, shared and owner models. This is required service data use, not an optional setting. <a href="/privacy.html" className="text-[#e8c46f] underline">Privacy and data use</a>.</p>
      <section className="mb-6 rounded-lg border border-[#8a6b32] bg-[#d4af37]/5 p-4" data-testid="registration-plan-summary"><h2 className="font-semibold text-[#e8c46f]">{selected.name} · {planPrice(selected)}{selected.interval?' / '+selected.interval:''}</h2><p className="mt-2 text-xs text-[#c4b89f]">{selected.id==='free'?'No card required.':'No charge at signup. Paid features require a confirmed payment.'}</p><Link to={selectionUrl} className="mt-3 inline-block text-sm text-[#e8c46f] underline">Change membership</Link></section>
      <form onSubmit={submit} className="space-y-4">
        <div><Label className="label-mono">Full name</Label>
          <Input data-testid="register-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="kaos-auth-input mt-2" /></div>
        <div><Label className="label-mono">Email</Label>
          <Input data-testid="register-email-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required className="kaos-auth-input mt-2" /></div>
        <div><Label className="label-mono">Password</Label>
          <Input data-testid="register-password-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} className="kaos-auth-input mt-2" />
          <p className="mt-1 text-xs text-slate-500">At least 8 characters.</p></div>
        {err && <p data-testid="register-error" className="text-sm text-[#C62828]">{err}</p>}
        <Button data-testid="register-submit-button" disabled={busy} className="kaos-auth-submit w-full font-semibold">{busy ? "Creating…" : purchase?"Continue to secure payment":"Create Account"}</Button>
      </form>
      <GoogleButton planId={selected.id} refCode={referral}/>
      <p className="mt-4 text-center text-sm text-slate-400">Already a member? <Link to={purchase?purchaseLoginLink(selected.id,sp):"/login"} className="text-[#D4AF37] hover:underline">Sign in</Link></p>
    </Shell>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState(""); const [sent, setSent] = useState(false); const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true);
    try { await api.post("/api/auth/forgot-password", { email }); } catch {}
    setSent(true); setBusy(false);
  };
  return (
    <Shell title="Reset password" subtitle="We'll send a reset link if the email is registered.">
      {sent ? (
        <div data-testid="forgot-confirmation" className="text-sm text-slate-300">
          If that email is registered, a reset link has been sent. Check your inbox.
          <div className="mt-4"><Link to="/login" className="text-[#D4AF37] hover:underline">Back to sign in</Link></div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <div><Label className="label-mono">Email</Label>
            <Input data-testid="forgot-email-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="kaos-auth-input mt-2" /></div>
          <Button data-testid="forgot-submit-button" disabled={busy} className="w-full bg-[#22C55E] text-black font-semibold">Send reset link</Button>
          <div><Link to="/login" className="text-sm text-slate-400 hover:text-[#D4AF37]">Back to sign in</Link></div>
        </form>
      )}
    </Shell>
  );
}

export function ResetPassword() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [password, setPassword] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      await api.post("/api/auth/reset-password", { token: params.get("token"), password });
      toast.success("Password reset. Please sign in.");
      nav("/login");
    } catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <Shell title="Set a new password">
      <form onSubmit={submit} className="space-y-4">
        <div><Label className="label-mono">New password</Label>
          <Input data-testid="reset-password-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} className="kaos-auth-input mt-2" /></div>
        {err && <p data-testid="reset-error" className="text-sm text-[#C62828]">{err}</p>}
        <Button data-testid="reset-submit-button" disabled={busy} className="w-full bg-[#22C55E] text-black font-semibold">Reset password</Button>
        <div><Link to="/login" className="text-sm text-slate-400 hover:text-[#D4AF37]">Back to sign in</Link></div>
      </form>
    </Shell>
  );
}
