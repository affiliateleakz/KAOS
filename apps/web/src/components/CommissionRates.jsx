import React,{useEffect,useState} from 'react';
import {api,errMsg} from '../lib/api';
import {useAuth} from '../context/AuthContext';
const names={free:'Free / unpaid',trial:'7-day free trial',pro:'Pro · monthly & yearly',ultimate:'Ultimate · monthly & yearly'};
export default function CommissionRates(){
 const {user}=useAuth();const [config,setConfig]=useState(null),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
 async function load(){setError('');try{const {data}=await api.get('/api/admin/affiliate/commission-rates');setConfig(data);}catch(e){setError(errMsg(e));}}
 useEffect(()=>{if(user?.role==='super_admin')load();},[user?.role]);
 if(user?.role!=='super_admin')return <p className="mb-5 text-sm text-slate-400">Commission percentages are managed by the super admin.</p>;
 async function save(e){e.preventDefault();setBusy(true);setError('');setNotice('');try{const {data}=await api.put('/api/admin/affiliate/commission-rates',{revision:config.revision,rates:config.rates});setConfig(data);setNotice('Commission percentages saved for future qualifying payments. Payout activation is separate.');}catch(e){setError(errMsg(e));}finally{setBusy(false);}}
 return <section className="mb-6 rounded-xl border border-[#8a6b32] bg-[#12100d] p-5" data-testid="commission-rate-settings"><h2 className="text-xl text-[#e8c46f]">Commission percentages by membership</h2><p className="mt-3 text-sm text-[#c4b89f]">Rates belong to the affiliate receiving each referral level, not the buyer’s plan. Monthly and annual memberships share their tier’s rates. Free and trial members cannot enroll or earn commissions.</p>
 {error&&<p role="alert" className="mt-3 text-amber-200">{error} <button onClick={load} className="underline">Reload commission rates</button></p>}
 {notice&&<p role="status" className="mt-3 text-[#e8c46f]">{notice}</p>}
 {config&&<form onSubmit={save}><div className="mt-5 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th>Membership</th>{[1,2,3].map(level=><th key={level}>Level {level} %</th>)}</tr></thead><tbody>{Object.entries(names).map(([tier,name])=><tr key={tier}><th className="py-3 pr-4">{name}</th>{[0,1,2].map(level=><td className="p-2" key={level}><input aria-label={`${tier} level ${level+1} percent`} type="number" min="0" max="100" step="0.01" required readOnly={['free','trial'].includes(tier)} value={config.rates[tier]?.[level]??0} onChange={e=>setConfig(current=>({...current,rates:{...current.rates,[tier]:current.rates[tier].map((v,i)=>i===level?e.target.value:v)}}))} className="w-24 rounded border border-[#66502a] bg-black p-2 text-[#e8c46f] read-only:opacity-50"/></td>)}</tr>)}</tbody></table></div><p className="mt-4 text-xs text-[#c4b89f]">The highest possible mixed-tier three-level payout cannot exceed 100%. Existing entries and refunds retain the original recorded rates and hold dates.</p><button disabled={busy} className="mt-5 rounded bg-[#d4af37] px-5 py-3 font-semibold text-black">{busy?'Saving…':'Save commission percentages'}</button></form>}
 </section>;
}
