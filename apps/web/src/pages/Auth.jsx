import React, { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Brand } from "../components/Brand";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

function Shell({ title, subtitle, children }) {
  return (
    <div className="flex min-h-screen flex-col bg-[#080808]">
      <div className="glass-nav px-6 py-4"><Brand /></div>
      <div className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="card-surface p-8">
            <h1 className="font-heading text-2xl font-bold text-white">{title}</h1>
            {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
            <div className="mt-6">{children}</div>
          </div>
          <p className="mt-4 text-center text-xs text-slate-400"><a href="/privacy/" className="text-[#2F8CFF] hover:underline">Privacy Policy</a> · <a href="mailto:support@tradewithkaos.com" className="hover:underline">Support</a></p>
        </div>
      </div>
    </div>
  );
}

function GoogleButton() {
  const nav = useNavigate();
  const { setUser } = useAuth();
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
            const { data } = await api.post("/api/auth/google/credential", { credential });
            setUser(data);
            nav(["moderator", "admin", "super_admin"].includes(data?.role) ? "/admin" : "/dashboard");
          } catch (e) { setErr(errMsg(e)); }
        }
      });
      const target = document.getElementById("kaos-google-button");
      if (target) window.google.accounts.id.renderButton(target, { theme: "filled_black", size: "large", width: 350, text: "continue_with" });
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
  }, [clientId, nav, setUser]);

  return <div className="mt-3"><div id="kaos-google-button" data-testid="google-login-button" className="flex justify-center" />{err && <p className="mt-2 text-sm text-[#C62828]">{err}</p>}</div>;
}

export function Login() {
  const nav = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const u = await login(email, password);
      const isAdmin = ["moderator", "admin", "super_admin"].includes(u?.role);
      nav(isAdmin ? "/admin" : "/dashboard");
    }
    catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <Shell title="Welcome back" subtitle="Sign in to your member account.">
      <form onSubmit={submit} className="space-y-4">
        <div><Label className="label-mono">Email</Label>
          <Input data-testid="login-email-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="mt-1 bg-[#0F0F0F] border-[#3A3A3A]" /></div>
        <div><Label className="label-mono">Password</Label>
          <Input data-testid="login-password-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="mt-1 bg-[#0F0F0F] border-[#3A3A3A]" /></div>
        {err && <p data-testid="login-error" className="text-sm text-[#C62828]">{err}</p>}
        <Button data-testid="login-submit-button" disabled={busy} className="w-full bg-[#2F8CFF] text-black hover:bg-[#7DB8FF] font-semibold">{busy ? "Signing in…" : "Sign In"}</Button>
      </form>
      <GoogleButton />
      <div className="mt-4 flex justify-between text-sm">
        <Link to="/forgot-password" data-testid="forgot-password-link" className="text-slate-400 hover:text-[#2F8CFF]">Forgot password?</Link>
        <Link to="/register" data-testid="go-register-link" className="text-[#2F8CFF] hover:underline">Join now</Link>
      </div>
    </Shell>
  );
}

export function Register() {
  const nav = useNavigate();
  const { register } = useAuth();
  const [sp] = useSearchParams();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { const r = sp.get("ref"); if (r) { try { localStorage.setItem("kaos_ref", r); } catch (e) {} } }, [sp]);
  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      let refCode; try { refCode = sp.get("ref") || localStorage.getItem("kaos_ref") || undefined; } catch (e3) { refCode = sp.get("ref") || undefined; }
      const data = await register({ ...form, refCode });
      if (data.verificationToken) sessionStorage.setItem("verifyToken", data.verificationToken);
      toast.success("Account created! Let's get you onboarded.");
      nav("/onboarding");
    } catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <Shell title="Become a member" subtitle="Create your account to unlock the extension.">
      <form onSubmit={submit} className="space-y-4">
        <div><Label className="label-mono">Full name</Label>
          <Input data-testid="register-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="mt-1 bg-[#0F0F0F] border-[#3A3A3A]" /></div>
        <div><Label className="label-mono">Email</Label>
          <Input data-testid="register-email-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required className="mt-1 bg-[#0F0F0F] border-[#3A3A3A]" /></div>
        <div><Label className="label-mono">Password</Label>
          <Input data-testid="register-password-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} className="mt-1 bg-[#0F0F0F] border-[#3A3A3A]" />
          <p className="mt-1 text-xs text-slate-500">At least 8 characters.</p></div>
        {err && <p data-testid="register-error" className="text-sm text-[#C62828]">{err}</p>}
        <Button data-testid="register-submit-button" disabled={busy} className="w-full bg-[#2F8CFF] text-black hover:bg-[#7DB8FF] font-semibold">{busy ? "Creating…" : "Create Account"}</Button>
      </form>
      <GoogleButton />
      <p className="mt-4 text-center text-sm text-slate-400">Already a member? <Link to="/login" className="text-[#2F8CFF] hover:underline">Sign in</Link></p>
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
          <div className="mt-4"><Link to="/login" className="text-[#2F8CFF] hover:underline">Back to sign in</Link></div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <div><Label className="label-mono">Email</Label>
            <Input data-testid="forgot-email-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="mt-1 bg-[#0F0F0F] border-[#3A3A3A]" /></div>
          <Button data-testid="forgot-submit-button" disabled={busy} className="w-full bg-[#2F8CFF] text-black hover:bg-[#7DB8FF] font-semibold">Send reset link</Button>
          <div><Link to="/login" className="text-sm text-slate-400 hover:text-[#2F8CFF]">Back to sign in</Link></div>
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
          <Input data-testid="reset-password-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} className="mt-1 bg-[#0F0F0F] border-[#3A3A3A]" /></div>
        {err && <p data-testid="reset-error" className="text-sm text-[#C62828]">{err}</p>}
        <Button data-testid="reset-submit-button" disabled={busy} className="w-full bg-[#2F8CFF] text-black hover:bg-[#7DB8FF] font-semibold">Reset password</Button>
        <div><Link to="/login" className="text-sm text-slate-400 hover:text-[#2F8CFF]">Back to sign in</Link></div>
      </form>
    </Shell>
  );
}
