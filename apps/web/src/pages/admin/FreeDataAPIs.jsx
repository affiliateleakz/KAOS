import React,{useEffect,useState} from "react";
import {api,errMsg} from "../../lib/api";

// Never returns, logs or persists raw API keys in the browser.
export default function FreeDataAPIs(){
 const [sources,setSources]=useState([]),[keys,setKeys]=useState({}),[notice,setNotice]=useState("");
 const load=()=>api.get("/api/admin/data-apis").then(r=>setSources(r.data.sources)).catch(e=>setNotice(errMsg(e)));
 useEffect(()=>{load()},[]);
 const save=async id=>{
  try{await api.put("/api/admin/data-apis/"+id,{api_key:keys[id]||""});setKeys(old=>({...old,[id]:""}));setNotice("Encrypted key saved. Feed remains disabled pending commercial review.");load()}
  catch(e){setNotice(errMsg(e))}
 };
 const remove=async id=>{
  try{await api.delete("/api/admin/data-apis/"+id);setKeys(old=>({...old,[id]:""}));setNotice("Key removed.");load()}
  catch(e){setNotice(errMsg(e))}
 };
 return <section className="mt-8" data-testid="free-data-api-settings">
  <h2 className="font-heading text-xl font-semibold">Free Data APIs · Admin Key Vault</h2>
  <p className="mt-1 mb-4 text-sm text-slate-400">Only public no-cost sources and providers advertising a free API tier. Saved keys are encrypted server-side, never displayed again. Saving a key does not activate a provider or authorize commercial redistribution. Paid endpoints and automatic charges are disabled.</p>
  {notice&&<p role="status" className="mb-3 text-sm text-amber-300">{notice}</p>}
  <div className="grid gap-3 md:grid-cols-2">{sources.map(src=><div key={src.id} className="card-surface p-4">
   <div className="flex flex-wrap justify-between gap-2"><strong>{src.name}</strong><span className="text-xs text-slate-400">{src.access==="free_public"?"Free · no key":"Free-tier key"} · {src.connected?"Feed implemented":"Not enabled"}</span></div>
   <p className="mt-2 text-xs text-slate-400">{src.note}</p>
   {src.key_required&&<div className="mt-3 flex flex-wrap gap-2">
    <input aria-label={src.name+" API key"} type="password" autoComplete="off" placeholder={src.key_saved?"Replace stored key":"Enter free API key"} value={keys[src.id]||""}
      onChange={e=>setKeys(old=>({...old,[src.id]:e.target.value}))} className="min-w-0 flex-1 rounded border border-[#444] bg-[#111] p-2 text-sm"/>
    <button disabled={!(keys[src.id]||"").trim()} onClick={()=>save(src.id)} className="rounded border border-[#2F8CFF] px-3 text-sm disabled:opacity-40">Save</button>
    {src.key_saved&&<button onClick={()=>remove(src.id)} className="rounded border border-red-600 px-3 text-sm">Remove</button>}
   </div>}
   {src.key_required&&<p className="mt-1 text-xs text-slate-500">{src.key_saved?"Key encrypted and stored · integration not activated":"No stored key"}</p>}
  </div>)}</div>
  <p className="mt-4 text-xs text-slate-500">Finviz API requires paid Elite access; Messari's commercial free-tier rights are unverified; Invo has no verified public developer API. Those three are intentionally excluded from the free API key vault.</p>
 </section>
}
