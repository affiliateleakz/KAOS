import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { RefreshCw, ShieldCheck, ShieldOff } from "lucide-react";

const card = "rounded-xl border border-[#2E2E2E] bg-[#0F0F0F]";

function Flag({ ok, yes, no }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${
      ok ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-amber-500/30 bg-amber-500/10 text-amber-300"}`}>
      {ok ? <ShieldCheck className="h-3 w-3" /> : <ShieldOff className="h-3 w-3" />}
      {ok ? yes : no}
    </span>
  );
}

export default function DataSources() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/api/admin/intelligence/sources");
      setData(response.data);
    } catch (err) {
      setError(errMsg(err));
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggle = async (source) => {
    try {
      await api.put(`/api/admin/intelligence/sources/${source.provider}`, { enabled: !source.enabled });
      toast.success(`${source.name} ${source.enabled ? "disabled" : "enabled"}`);
      load();
    } catch (err) { toast.error(errMsg(err)); }
  };

  return (
    <div className="space-y-5" data-testid="admin-data-sources">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-bold">Intelligence Data Sources</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-400">
            Free or owner-supplied integrations only. This page manages which sources member scanners may read
            and shows credential <em>presence</em>; secret values are never displayed or returned by the API.
          </p>
        </div>
        <Button onClick={load} disabled={loading} variant="outline" className="border-[#3A3A3A] bg-transparent text-white">
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </div>

      {error && (
        <div role="alert" className="rounded-lg border border-[#C62828]/40 bg-[#C62828]/10 p-4 text-sm text-red-200">
          {error}
        </div>
      )}

      {loading && !data && <p role="status" className="font-mono text-sm text-slate-400">Loading sources…</p>}

      {data && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className={`${card} p-4`}>
              <p className="label-mono">Collector key</p>
              <p className="mt-2"><Flag ok={data.collector_configured} yes="Configured" no="Missing" /></p>
            </div>
            <div className={`${card} p-4`}>
              <p className="label-mono">Credential values exposed</p>
              <p className="mt-2 font-mono text-sm text-white">{String(data.credentials_exposed)}</p>
            </div>
            <div className={`${card} p-4`}>
              <p className="label-mono">Paid providers allowed</p>
              <p className="mt-2 font-mono text-sm text-white">{String(data.allows_paid_providers)}</p>
            </div>
          </div>

          <div className={`${card} overflow-x-auto`}>
            <table className="w-full min-w-[900px] border-collapse">
              <thead>
                <tr className="border-b border-[#2E2E2E]">
                  {["Source", "Kind", "Enabled", "Credentials", "Last stored observation", "Notes", ""].map((label) => (
                    <th key={label} className="px-3 py-2 text-left font-mono text-[10px] uppercase tracking-wider text-slate-500">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.sources.map((source) => (
                  <tr key={source.provider} className="border-b border-[#1c1c1c]">
                    <td className="px-3 py-3">
                      <p className="text-sm font-semibold text-white">{source.name}</p>
                      <p className="font-mono text-[11px] text-slate-500">{source.provider}</p>
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-slate-400">{source.kind.replace(/_/g, " ")}</td>
                    <td className="px-3 py-3">
                      <Flag ok={source.enabled} yes="Enabled" no="Disabled" />
                    </td>
                    <td className="px-3 py-3">
                      <Flag ok={source.configured} yes="Present" no="Missing" />
                      {source.missing_env.length > 0 && (
                        <p className="mt-1 font-mono text-[11px] text-amber-300">{source.missing_env.join(", ")}</p>
                      )}
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-slate-400">
                      {source.last_observation
                        ? <>{new Date(source.last_observation.observed_at).toLocaleString()}<br /><span className="text-slate-600">{source.last_observation.event_id}</span></>
                        : "—"}
                    </td>
                    <td className="max-w-[320px] px-3 py-3 text-xs text-slate-400">{source.note}</td>
                    <td className="px-3 py-3">
                      <Button size="sm" onClick={() => toggle(source)}
                        variant="outline" className="border-[#3A3A3A] bg-transparent text-white">
                        {source.enabled ? "Disable" : "Enable"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500">{data.note}</p>
        </>
      )}
    </div>
  );
}
