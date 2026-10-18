import React, { useState } from "react";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { TerminalSquare, Play } from "lucide-react";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

const ACTIONS = [
  { id: "login", label: "Login as test user", method: "POST", path: "/api/v1/auth/login", body: (s) => ({ email: s.email, password: s.password }) },
  { id: "license", label: "Check license", method: "GET", path: "/api/v1/license/status", auth: true },
  { id: "register-device", label: "Register device", method: "POST", path: "/api/v1/devices/register", auth: true, body: () => ({ installId: "sim-install-" + Math.random().toString(36).slice(2, 8), deviceName: "Simulator Device", extensionVersion: "1.4.0" }) },
  { id: "devices", label: "List devices", method: "GET", path: "/api/v1/devices", auth: true },
  { id: "refresh", label: "Refresh authorization", method: "POST", path: "/api/v1/auth/refresh", body: (s) => ({ refreshToken: s.refreshToken }) },
  { id: "sync-pull", label: "Sync strategies (pull)", method: "GET", path: "/api/v1/sync", auth: true },
  { id: "community", label: "Fetch community strategies", method: "GET", path: "/api/v1/community/strategies" },
  { id: "extension", label: "Check extension version", method: "GET", path: "/api/v1/extension/latest" },
];

const PRESETS = {
  active: { email: "bob@demotrader.com", password: "Demo!2026", label: "Active member (bob)" },
  expired: { email: "dave@demotrader.com", password: "Demo!2026", label: "Expired membership (dave)" },
  pending: { email: "carol@demotrader.com", password: "Demo!2026", label: "Past due / affiliate pending (carol)" },
};

export default function ExtensionSimulator() {
  const [creds, setCreds] = useState(PRESETS.active);
  const [tokens, setTokens] = useState({ accessToken: "", refreshToken: "" });
  const [log, setLog] = useState([]);
  const [busy, setBusy] = useState(false);

  const run = async (action) => {
    setBusy(true);
    const state = { ...creds, ...tokens };
    const url = `${BACKEND}${action.path}`;
    const headers = { "Content-Type": "application/json" };
    if (action.auth && tokens.accessToken) headers["Authorization"] = `Bearer ${tokens.accessToken}`;
    const body = action.body ? action.body(state) : undefined;
    const t0 = performance.now();
    let entry = { action: action.label, method: action.method, url: action.path, request: body || null, status: 0, response: null, ms: 0, authHeader: headers["Authorization"] ? "Bearer ***" : null };
    try {
      const res = await fetch(url, { method: action.method, headers, body: body ? JSON.stringify(body) : undefined });
      entry.status = res.status;
      entry.response = await res.json().catch(() => ({}));
      entry.ms = Math.round(performance.now() - t0);
      if (action.id === "login" && entry.response.accessToken) setTokens({ accessToken: entry.response.accessToken, refreshToken: entry.response.refreshToken });
      if (action.id === "refresh" && entry.response.accessToken) setTokens((t) => ({ ...t, accessToken: entry.response.accessToken, refreshToken: entry.response.refreshToken || t.refreshToken }));
    } catch (e) {
      entry.response = { error: String(e) };
      entry.ms = Math.round(performance.now() - t0);
    }
    setLog((l) => [entry, ...l]);
    setBusy(false);
  };

  const statusColor = (s) => (s >= 200 && s < 300 ? "text-[#2F8CFF]" : s === 401 || s === 403 ? "text-[#FFB800]" : "text-[#C62828]");

  return (
    <div>
      <div className="mb-6 flex items-center gap-2">
        <TerminalSquare className="h-6 w-6 text-[#2F8CFF]" />
        <h1 className="font-heading text-2xl font-bold">Extension API Simulator</h1>
      </div>
      <p className="mb-6 max-w-2xl text-sm text-slate-400">Simulate exactly what your Chrome extension will do against the v1 API. Login to capture a token, then run any request and inspect the raw HTTP response, status code and authorization result.</p>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-1">
          <div className="card-surface p-5">
            <Label className="label-mono">Test account preset</Label>
            <div className="mt-2 space-y-2">
              {Object.entries(PRESETS).map(([k, v]) => (
                <button key={k} data-testid={`sim-preset-${k}`} onClick={() => { setCreds(v); setTokens({ accessToken: "", refreshToken: "" }); }}
                  className={`block w-full rounded-md border px-3 py-2 text-left text-sm ${creds.email === v.email ? "border-[#2F8CFF] bg-[#2F8CFF]/10 text-[#2F8CFF]" : "border-[#3A3A3A] text-slate-300 hover:bg-[#111111]"}`}>
                  {v.label}
                </button>
              ))}
            </div>
            <Input className="mt-3 bg-[#080808] border-[#3A3A3A] font-mono text-xs" value={creds.email} onChange={(e) => setCreds({ ...creds, email: e.target.value })} />
            <Input className="mt-2 bg-[#080808] border-[#3A3A3A] font-mono text-xs" value={creds.password} onChange={(e) => setCreds({ ...creds, password: e.target.value })} />
            <div className="mt-3 font-mono text-xs text-slate-500">Token: {tokens.accessToken ? <span className="text-[#2F8CFF]">captured</span> : "none"}</div>
          </div>
          <div className="card-surface p-5">
            <Label className="label-mono">Actions</Label>
            <div className="mt-2 space-y-2">
              {ACTIONS.map((a) => (
                <Button key={a.id} data-testid={`sim-action-${a.id}`} onClick={() => run(a)} disabled={busy}
                  variant="outline" className="w-full justify-start border-[#3A3A3A] bg-transparent text-left text-white hover:bg-[#111111]">
                  <Play className="mr-2 h-3.5 w-3.5 text-[#2F8CFF]" />
                  <span className="font-mono text-xs">{a.method}</span> <span className="ml-2 text-sm">{a.label}</span>
                </Button>
              ))}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2">
          <div className="card-surface p-5" data-testid="simulator-response-log">
            <div className="flex items-center justify-between">
              <h3 className="font-heading font-semibold">Request / Response Log</h3>
              <Button size="sm" variant="ghost" onClick={() => setLog([])} className="text-slate-400">Clear</Button>
            </div>
            <div className="mt-4 space-y-4 max-h-[70vh] overflow-y-auto">
              {log.length === 0 && <p className="text-sm text-slate-500">Run an action to see the HTTP exchange.</p>}
              {log.map((e, i) => (
                <div key={i} className="rounded-md border border-[#2E2E2E] bg-[#080808] p-4 font-mono text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-300">{e.method} {e.url}</span>
                    <span className={statusColor(e.status)}>{e.status} · {e.ms}ms</span>
                  </div>
                  {e.authHeader && <div className="mt-2 text-slate-500">Authorization: {e.authHeader}</div>}
                  {e.request && <><div className="mt-2 text-slate-500">Request:</div><pre className="mt-1 whitespace-pre-wrap text-[#2F8CFF]">{JSON.stringify(e.request, null, 2)}</pre></>}
                  <div className="mt-2 text-slate-500">Response:</div>
                  <pre className="mt-1 whitespace-pre-wrap text-slate-300">{JSON.stringify(e.response, null, 2)}</pre>
                  {e.response?.authorized !== undefined && (
                    <div className={`mt-2 ${e.response.authorized ? "text-[#2F8CFF]" : "text-[#C62828]"}`}>
                      AUTHORIZATION RESULT: {e.response.authorized ? "AUTHORIZED ✓" : "DENIED ✗"} {e.response.reasons?.length ? `(${e.response.reasons.join(", ")})` : ""}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
