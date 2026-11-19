import React,{useCallback,useEffect,useState} from 'react';
import {api,errMsg} from '../lib/api';

const initial=()=>({title:'',description:'',source:'',kind:'indicator',market:'Any',timeframe:'Any',thumbnail:'',revision:'',status:'pending',official:false,featured:false,moderation_note:'',rights_confirmed:false});
const input='w-full rounded border border-[#66512d] bg-[#0b0b0b] p-3 text-white';
const button='rounded border border-[#8b6b32] px-4 py-2 text-[#e8c46f] disabled:opacity-50';
const statuses=['draft','pending','published','rejected','archived'];
export default function PineScripts({admin=false}){
 const [items,setItems]=useState([]),[total,setTotal]=useState(0),[page,setPage]=useState(1),[scope,setScope]=useState('library');
 const [search,setSearch]=useState(''),[query,setQuery]=useState(''),[kind,setKind]=useState(''),[status,setStatus]=useState('');
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[loading,setLoading]=useState(false),[busy,setBusy]=useState(false);
 const [viewer,setViewer]=useState(null),[editing,setEditing]=useState(null),[form,setForm]=useState(initial);
 const endpoint=admin?'/api/admin/pine-scripts':'/api/pine-scripts';
 const load=useCallback(async()=>{
  setLoading(true);setError('');
  try{const {data}=await api.get(endpoint,{params:{search:query,kind,status,page,...(!admin?{scope}:{})}});setItems(data.items);setTotal(data.total);}
  catch(e){setError(errMsg(e));}finally{setLoading(false);}
 },[endpoint,query,kind,status,page,scope,admin]);
 useEffect(()=>{load();},[load]);
 const change=(key,value)=>setForm(old=>({...old,[key]:value}));
 async function open(item,edit=false){
  setError('');setBusy(true);
  try{const {data}=await api.get('/api/pine-scripts/'+item.id);
   if(edit){const next=initial();for(const key of Object.keys(next))if(data[key]!==undefined)next[key]=data[key];next.rights_confirmed=true;if(!admin){next.official=false;next.featured=false;next.moderation_note='';if(!['draft','pending','archived'].includes(next.status))next.status='pending';}setForm(next);setEditing(data.id);setViewer(null);}
   else{setViewer(data);setEditing(null);}
  }catch(e){setError(errMsg(e));}finally{setBusy(false);}
 }
 function create(){setForm({...initial(),status:admin?'draft':'pending',official:admin});setEditing('new');setViewer(null);setError('');setNotice('');}
 async function sourceFile(file){
  if(!file)return;
  try{if(!/\.(pine|txt)$/i.test(file.name)||file.size>128*1024)throw Error('Choose a .pine or .txt file up to 128 KiB');change('source',await file.text());}
  catch(e){setError(e.message);}
 }
 async function imageFile(file){
  if(!file)return;
  if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>2*1024*1024){setError('Choose a PNG, JPEG or WebP thumbnail up to 2 MiB');return;}
  try{const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('Could not read thumbnail'));reader.readAsDataURL(file);});change('thumbnail',data);}
  catch(e){setError(e.message);}
 }
 async function installPack(){
  if(!window.confirm('Install three original KAOS research drafts? Backtests did not establish a robust edge. They remain unpublished until you review and publish them.'))return;
  setBusy(true);setError('');try{const {data}=await api.post('/api/admin/pine-scripts/starter-pack',{});setNotice(data.message+' Added '+data.created.length+'; already present '+data.skipped.length+'.');setStatus('');setPage(1);await load();}catch(e){setError(errMsg(e));}finally{setBusy(false);}
 }
 async function save(event){event.preventDefault();setBusy(true);setError('');setNotice('');
  try{if(editing==='new')await api.post(endpoint,form);else await api.put(endpoint+'/'+editing,form);setEditing(null);setNotice(admin?'Script saved.':'Script saved. Submitted changes need approval before appearing in the library.');await load();}
  catch(e){setError(errMsg(e));}finally{setBusy(false);}
 }
 async function remove(item){
  if(!window.confirm('Permanently delete “'+item.title+'” and its source? This cannot be undone.'))return;
  setBusy(true);setError('');
  try{await api.delete('/api/admin/pine-scripts/'+item.id,{params:{revision:item.revision}});setViewer(null);setEditing(null);setNotice('Script deleted.');await load();}
  catch(e){setError(errMsg(e));}finally{setBusy(false);}
 }
 async function download(item){
  try{const response=await api.get('/api/pine-scripts/'+item.id+'/download',{responseType:'blob'});const url=URL.createObjectURL(response.data);const link=document.createElement('a');link.href=url;link.download=(item.title.replace(/[^A-Za-z0-9_-]/g,'_').slice(0,80)||'kaos-script')+'.pine';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  catch(e){setError(errMsg(e));}
 }
 return <section className="mx-auto max-w-6xl space-y-6 text-white">
  <header className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs uppercase tracking-widest text-[#e8c46f]">TradingView · Pine Script</p><h1 className="mt-2 text-3xl font-bold">{admin?'Pine Script Management':'TradingView Script Library'}</h1><p className="mt-3 max-w-2xl text-sm text-slate-400">{admin?'Manage member submissions and KAOS official releases.':'Discover KAOS and community scripts, or share your own with a thumbnail and description.'} Copy or download source and use it in TradingView’s Pine Editor.</p></div><button className={button} onClick={create}>{admin?'Upload official script':'Upload your script'}</button></header>
  {admin&&<div className="flex flex-wrap items-center gap-3"><button disabled={busy} className={button} onClick={installPack}>Install KAOS research starter pack</button><a className="text-sm text-[#e8c46f] underline" href="/research/kaos-pine-pack-v1.md" target="_blank" rel="noopener noreferrer">Read backtest report</a></div>}
  {error&&<p role="alert" className="rounded border border-red-700 p-3 text-red-300">{error}</p>}{notice&&<p role="status" className="rounded border border-[#66512d] p-3 text-[#e8c46f]">{notice}</p>}
  {editing&&<form onSubmit={save} className="space-y-4 rounded-xl border border-[#66512d] bg-[#111] p-5">
   <h2 className="text-xl font-semibold">{editing==='new'?'New script':'Edit script'}</h2>
   <label className="block">Title<input required maxLength={100} className={input} value={form.title} onChange={e=>change('title',e.target.value)}/></label>
   <label className="block">Description & setup instructions<textarea required maxLength={5000} rows={4} className={input} value={form.description} onChange={e=>change('description',e.target.value)}/></label>
   <div className="grid gap-3 md:grid-cols-3"><label>Type<select className={input} value={form.kind} onChange={e=>change('kind',e.target.value)}>{['indicator','strategy','library'].map(x=><option key={x}>{x}</option>)}</select></label><label>Markets<input maxLength={60} required className={input} value={form.market} onChange={e=>change('market',e.target.value)}/></label><label>Timeframes<input maxLength={60} required className={input} value={form.timeframe} onChange={e=>change('timeframe',e.target.value)}/></label></div>
   <label className="block">Thumbnail · PNG/JPEG/WebP, up to 2 MiB<input className="mt-2 block" type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>imageFile(e.target.files[0])}/></label>{form.thumbnail&&<img alt="Thumbnail preview" src={form.thumbnail} className="max-h-48 rounded object-contain"/>}
   <label className="block">Upload .pine / .txt · up to 128 KiB<input className="mt-2 block" type="file" accept=".pine,.txt,text/plain" onChange={e=>sourceFile(e.target.files[0])}/></label>
   <label className="block">Pine source<textarea required spellCheck={false} rows={14} className={input+' font-mono text-sm'} value={form.source} onChange={e=>change('source',e.target.value)} placeholder={'//@version=6\nindicator("My indicator")\nplot(close)'}/></label>
   <p className="text-xs text-slate-400">Sharing makes the source available to library members after approval. Pine code is not executed or compiled by KAOS; check it in TradingView. Include your script’s license and attribution in its source.</p>
   <label className="block">Publication status<select className={input} value={form.status} onChange={e=>change('status',e.target.value)}>{(admin?statuses:['draft','pending','archived']).map(x=><option key={x} value={x}>{x==='pending'?'Submit for review':x}</option>)}</select></label>
   {admin&&<><div className="flex gap-5"><label><input type="checkbox" checked={form.official} onChange={e=>change('official',e.target.checked)}/> KAOS official</label><label><input type="checkbox" checked={form.featured} onChange={e=>change('featured',e.target.checked)}/> Featured</label></div><label className="block">Moderation note · visible to the author<textarea maxLength={1000} className={input} value={form.moderation_note} onChange={e=>change('moderation_note',e.target.value)}/></label></>}
   <label className="block text-sm"><input required type="checkbox" checked={form.rights_confirmed} onChange={e=>change('rights_confirmed',e.target.checked)}/> I confirm permission to share this source and thumbnail.</label>
   <div className="flex gap-3"><button disabled={busy} className={button}>{busy?'Saving…':'Save script'}</button><button type="button" className={button} onClick={()=>setEditing(null)}>Cancel</button></div>
  </form>}
  {viewer&&<article className="space-y-4 rounded-xl border border-[#66512d] bg-[#111] p-5"><div className="flex justify-between gap-4"><h2 className="text-2xl font-semibold">{viewer.title}</h2><button className={button} onClick={()=>setViewer(null)}>Close</button></div><img src={viewer.thumbnail} alt={viewer.title+' thumbnail'} className="max-h-72 rounded object-contain"/><p className="text-sm text-[#e8c46f]">{viewer.official?'KAOS official':'Community'} · {viewer.author_name} · {viewer.kind} · {viewer.market} · {viewer.timeframe}</p><p className="whitespace-pre-wrap text-slate-300">{viewer.description}</p>{viewer.moderation_note&&<p className="rounded border border-[#66512d] p-3">Moderation: {viewer.moderation_note}</p>}<label className="block">Pine source<textarea readOnly spellCheck={false} rows={16} className={input+' font-mono text-sm'} value={viewer.source}/></label><div className="flex flex-wrap gap-3"><button className={button} onClick={async()=>{try{await navigator.clipboard.writeText(viewer.source);setNotice('Source copied. Paste it into TradingView’s Pine Editor.');}catch{setError('Clipboard unavailable. Select and copy the source above.');}}}>Copy source</button><button className={button} onClick={()=>download(viewer)}>Download .pine</button>{viewer.can_edit&&<button disabled={busy} className={button} onClick={()=>open(viewer,true)}>Edit / {admin?'moderate':'resubmit'}</button>}{admin&&<button disabled={busy} className={button} onClick={()=>remove(viewer)}>Delete permanently</button>}</div></article>}
  <div className="flex flex-wrap gap-3">{!admin&&<><button className={button} aria-pressed={scope==='library'} onClick={()=>{setScope('library');setStatus('');setPage(1);}}>Library</button><button className={button} aria-pressed={scope==='mine'} onClick={()=>{setScope('mine');setPage(1);}}>My uploads</button></>}<form className="flex flex-1 gap-2" onSubmit={e=>{e.preventDefault();setQuery(search);setPage(1);}}><input aria-label="Search scripts" maxLength={100} className={input} value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search scripts or authors"/><button className={button}>Search</button></form><select aria-label="Filter script type" className={input+' max-w-40'} value={kind} onChange={e=>{setKind(e.target.value);setPage(1);}}><option value="">All types</option>{['indicator','strategy','library'].map(x=><option key={x}>{x}</option>)}</select>{(admin||scope==='mine')&&<select aria-label="Filter publication status" className={input+' max-w-40'} value={status} onChange={e=>{setStatus(e.target.value);setPage(1);}}><option value="">All statuses</option>{statuses.map(x=><option key={x}>{x}</option>)}</select>}</div>
  {loading?<p role="status">Loading scripts…</p>:items.length===0?<p className="rounded border border-[#66512d] p-8 text-slate-400">{admin?'No scripts match this view. Upload an official script or review future member submissions.':scope==='mine'?'You have no uploads in this view.':'No published scripts match this view yet. Share a script for review.'}</p>:<div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{items.map(item=><article key={item.id} className="overflow-hidden rounded-xl border border-[#66512d] bg-[#111]"><img loading="lazy" src={item.thumbnail} alt={item.title+' thumbnail'} className="h-44 w-full object-cover"/><div className="space-y-3 p-4"><p className="text-xs uppercase text-[#e8c46f]">{item.official?'KAOS official':'Community'}{item.featured?' · Featured':''} · {item.status}</p><h2 className="text-lg font-semibold">{item.title}</h2><p className="line-clamp-3 whitespace-pre-wrap text-sm text-slate-400">{item.description}</p><p className="text-xs text-slate-400">By {item.author_name} · {item.kind} · {item.market} · {item.timeframe}</p><div className="flex flex-wrap gap-2"><button disabled={busy} className={button} onClick={()=>open(item)}>View script</button>{item.can_edit&&<button disabled={busy} className={button} onClick={()=>open(item,true)}>{admin?'Manage':'Edit'}</button>}</div></div></article>)}</div>}
  <footer className="flex items-center justify-between"><button className={button} disabled={page===1||loading} onClick={()=>setPage(p=>p-1)}>Previous</button><span className="text-sm text-slate-400">{total} scripts · page {page}</span><button className={button} disabled={page*12>=total||loading} onClick={()=>setPage(p=>p+1)}>Next</button></footer>
 </section>;
}
