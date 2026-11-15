import React,{useEffect,useMemo,useState} from "react";
import {api,errMsg} from "../../lib/api";

// Admin API-key manager. Saved keys are write-only: the API returns status and a
// masked hint, never the stored secret, so nothing sensitive lands in the browser.
export default function ApiKeys(){
 const [data,setData]=useState(null),[error,setError]=useState(""),[notice,setNotice]=useState("");
 const [values,setValues]=useState({}),[busy,setBusy]=useState({}),[results,setResults]=useState({});
 const load=async()=>{setError("");try{const r=await api.get("/api/admin/integrations");setData(r.data)}catch(e){setError(errMsg(e)||"Could not load the integration catalog")}};
 useEffect(()=>{load()},[]);
 const setValue=(id,env,v)=>setValues(old=>({...old,[id]:{...(old[id]||{}),[env]:v}}));
 const payload=id=>Object.fromEntries(Object.entries(values[id]||{}).filter(([,v])=>String(v??"").trim()!==""));
 const save=async id=>{
  const body=payload(id);
  if(!Object.keys(body).length){setNotice("Type a value into at least one field first. Blank fields keep their current value.");return}
  setBusy(b=>({...b,[id]:"save"}));setNotice("");
  try{await api.put("/api/admin/integrations/"+id,{values:body});
   setValues(old=>({...old,[id]:{}}));
   setNotice("Saved. The new value is encrypted and active immediately — no restart needed.");
   setResults(old=>({...old,[id]:null}));
   await load();
  }catch(e){setNotice(errMsg(e)||"Could not save")}
  finally{setBusy(b=>({...b,[id]:null}))}
 };
 const test=async id=>{
  setBusy(b=>({...b,[id]:"test"}));
  try{const r=await api.post("/api/admin/integrations/"+id+"/test");setResults(old=>({...old,[id]:r.data}))}
  catch(e){setResults(old=>({...old,[id]:{ok:false,detail:errMsg(e)||"Check failed"}}))}
  finally{setBusy(b=>({...b,[id]:null}))}
 };
 const remove=async id=>{
  setBusy(b=>({...b,[id]:"remove"}));setNotice("");
  try{await api.delete("/api/admin/integrations/"+id);setNotice("Stored value removed.");setResults(old=>({...old,[id]:null}));await load()}
  catch(e){setNotice(errMsg(e)||"Could not remove")}
  finally{setBusy(b=>({...b,[id]:null}))}
 };
 const grouped=useMemo(()=>{
  const out=[];
  for(const item of data?.integrations||[]){
   const last=out[out.length-1];
   if(last&&last.category===item.category)last.items.push(item);else out.push({category:item.category,items:[item]});
  }
  return out;
 },[data]);
 return <section className="space-y-6" data-testid="admin-api-keys">
  <div>
   <h1 className="font-heading text-2xl font-bold">API Keys & Integrations</h1>
   <p className="mt-1 max-w-3xl text-sm text-slate-400">Every feature that needs a third-party service is listed here with what it powers, where to get the credential (with a free option wherever one exists), and a live check. Keys are encrypted at rest, never shown again, and take effect immediately.</p>
  </div>
  {notice&&<p role="status" className="rounded border border-[#D4AF37]/40 bg-[#D4AF37]/10 p-3 text-sm text-[#E8D9A8]">{notice}</p>}
  {error&&<p role="alert" className="text-sm text-red-400">{error}</p>}
  {!data&&!error&&<p className="text-sm text-slate-400">Loading catalog…</p>}
  {data&&<>
   <div className="rounded border border-white/10 bg-[#111] p-4 text-sm">
    <div className="flex flex-wrap items-center gap-2">
     <span className="font-semibold">Encryption:</span>
     <span className={data.vault_ready?"text-emerald-400":"text-amber-300"}>{data.vault_ready?"ready":"not configured"}</span>
     <span className="text-xs text-slate-500">({data.vault_source})</span>
    </div>
    {!data.vault_ready&&<p className="mt-1 text-xs text-amber-300">Set KAOS_INTEGRATION_VAULT_KEY (or JWT_SECRET) before saving keys.</p>}
   </div>

   <div>
    <h2 className="font-heading text-lg font-semibold">Working with no key at all</h2>
    <div className="mt-2 grid gap-3 md:grid-cols-3">{data.keyless.map(k=><div key={k.name} className="card-surface p-4">
     <div className="flex items-center justify-between gap-2"><strong className="text-sm">{k.name}</strong><span className="rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-300">No key</span></div>
     <p className="mt-1 text-xs text-slate-400">Powers: {k.powers}</p>
     <p className="mt-1 text-xs text-slate-500">{k.note}</p>
    </div>)}</div>
   </div>

   {grouped.map(group=><div key={group.category}>
    <h2 className="font-heading text-lg font-semibold">{group.category}</h2>
    <div className="mt-2 grid gap-3 lg:grid-cols-2">{group.items.map(item=><div key={item.id} className="card-surface flex flex-col p-4" data-testid={`integration-${item.id}`}>
     <div className="flex flex-wrap items-start justify-between gap-2">
      <div>
       <strong>{item.name}</strong>
       <div className="mt-1 flex flex-wrap gap-1">{item.powers.map(p=><span key={p} className="rounded border border-[#333] bg-[#181818] px-1.5 py-0.5 text-[11px] text-slate-300">{p}</span>)}</div>
      </div>
      <span className={item.ready?"rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-300":"rounded border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-300"}>{item.ready?"Configured":`${item.configured_fields}/${item.total_fields} set`}</span>
     </div>
     <p className="mt-2 text-xs text-slate-400">{item.purpose}</p>
     <p className="mt-2 text-xs text-slate-300"><span className="text-slate-500">Get it at: </span><a href={item.get_it_at} target="_blank" rel="noopener noreferrer" className="text-[#D4AF37] underline">{item.get_it_at}</a>{item.docs&&<>{' · '}<a href={item.docs} target="_blank" rel="noopener noreferrer" className="text-slate-400 underline">docs</a>}</>}</p>
     <p className="mt-1 text-xs text-slate-500">{item.cost}</p>
     <div className="mt-3 space-y-2">{item.fields.map(f=>f.toggle?
      <label key={f.env} className="flex items-center justify-between gap-2 text-xs"><span>{f.label}{f.optional&&<span className="text-slate-500"> (optional)</span>}</span>
       <select aria-label={f.label} value={values[item.id]?.[f.env]??(f.set?"on":"off")} onChange={e=>setValue(item.id,f.env,e.target.value)} className="rounded border border-[#444] bg-[#111] p-1.5">
        <option value="off">Not approved</option><option value="on">Approved</option>
       </select></label>:
      <label key={f.env} className="block text-xs"><span className="text-slate-300">{f.label}{f.optional&&<span className="text-slate-500"> (optional)</span>}</span>
       <input aria-label={f.label} type={f.secret?"password":"text"} autoComplete="off" spellCheck={false}
        placeholder={f.set?(f.preview?"Saved "+f.preview:"Saved"):(f.hint||"")} value={values[item.id]?.[f.env]??""}
        onChange={e=>setValue(item.id,f.env,e.target.value)} className="mt-1 w-full rounded border border-[#444] bg-[#111] p-2 text-sm"/>
       <span className="mt-0.5 block text-[11px] text-slate-500">{f.set?`Currently set from ${f.source==="admin"?"this panel":"the server environment"} — leave blank to keep it.`:f.hint}</span>
      </label>)}</div>
     <div className="mt-3 flex flex-wrap gap-2">
      <button disabled={busy[item.id]} onClick={()=>save(item.id)} className="rounded bg-[#D4AF37] px-3 py-1.5 text-sm font-semibold text-black disabled:opacity-40">{busy[item.id]==="save"?"Saving…":"Save"}</button>
      <button disabled={busy[item.id]} onClick={()=>test(item.id)} className="rounded border border-[#555] px-3 py-1.5 text-sm disabled:opacity-40">{busy[item.id]==="test"?"Checking…":"Test connection"}</button>
      <button disabled={busy[item.id]||!item.configured_fields} onClick={()=>remove(item.id)} className="rounded border border-red-600/60 px-3 py-1.5 text-sm text-red-300 disabled:opacity-30">Remove stored</button>
     </div>
     {results[item.id]&&<p className={results[item.id].ok?"mt-2 text-xs text-emerald-400":"mt-2 text-xs text-red-400"}>{results[item.id].ok?"✓ ":"✗ "}{results[item.id].detail}</p>}
     {item.updated_at&&<p className="mt-1 text-[11px] text-slate-500">Last saved {new Date(item.updated_at).toLocaleString()}{item.updated_by?` by ${item.updated_by}`:""}</p>}
    </div>)}</div>
   </div>)}
  </>}
 </section>;
}
