import React,{useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {api,errMsg} from '../../lib/api';
import {marketingCopy,BANNER_FORMATS,downloadBanner,campaignLink} from '../../lib/affiliateKit';
import {LedgerCard} from './AffiliateAI';

const panel='rounded-xl border border-[#514027] bg-[#12100d] p-5 sm:p-7';
const button='inline-flex min-h-11 items-center justify-center rounded-md border border-[#8a6b32] px-4 py-2 text-sm font-semibold text-[#efd28a] disabled:opacity-50';
export default function AffiliateHub(){
 const [overview,setOverview]=useState(null),[program,setProgram]=useState(null),[ledger,setLedger]=useState(null),[assets,setAssets]=useState([]);
 const [connect,setConnect]=useState(null);
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[tab,setTab]=useState('Email');
 async function load(){setError('');try{const [o,p]=await Promise.all([api.get('/api/affiliate/overview'),api.get('/api/affiliate/program')]);setOverview(o.data);setProgram(p.data);}catch(e){setError(errMsg(e));}}
 useEffect(()=>{load();api.get('/api/affiliate/ledger').then(r=>setLedger(r.data)).catch(()=>{});api.get('/api/affiliate/marketing').then(r=>setAssets(r.data)).catch(()=>{});},[]);
 async function activate(){setBusy(true);try{await api.post('/api/affiliate/activate');await load();setNotice('Your referral link is ready. Choose a campaign below.');}catch(e){setError(errMsg(e));}finally{setBusy(false);}}
 async function copy(text){try{await navigator.clipboard.writeText(text);setNotice('Copied. For promotions, include your referral link and an affiliate disclosure.');}catch{setNotice('Copy was blocked by your browser. Select and copy the text below.');}}
 const active=overview?.active===true,link=active?overview.referralLink:null;
 useEffect(()=>{if(active)api.get('/api/affiliate/connect/status').then(r=>setConnect(r.data)).catch(()=>setConnect({error:true}));},[active]);
 async function connectStripe(){setBusy(true);try{const {data}=await api.post('/api/affiliate/connect/onboarding');const url=new URL(data.url);if(url.protocol!=='https:'||url.hostname!=='connect.stripe.com')throw Error('Invalid onboarding link');window.location.assign(url.href);}catch(e){setError(errMsg(e));setBusy(false);}}
 const templates=link?marketingCopy(link):[];
 return <div className="space-y-6" data-testid="affiliate-hub">
  <section className="relative overflow-hidden rounded-xl border border-[#8a6b32] bg-[#12100d] p-7 sm:p-10">
   <div aria-hidden="true" className="absolute inset-0 bg-[url('/kaos-cinematic-header.jpg')] bg-cover bg-center opacity-20"/>
   <div className="relative max-w-2xl"><p className="text-xs font-semibold tracking-[.2em] text-[#e8c46f]">KAOS PARTNER DESK</p>
    <h1 className="mt-4 text-3xl font-semibold leading-tight text-[#f3ead8] sm:text-5xl">Share your KAOS.<br/>Build your community.</h1>
    <p className="mt-5 leading-relaxed text-[#c4b89f]">Introduce traders to a workspace you know. Get your referral link, choose ready-to-use creative, and track qualifying membership referrals in one place.</p>
    {!active&&<button data-testid="affiliate-activate-button" disabled={busy||!program?.enrollmentEnabled} onClick={activate} className={`${button} mt-6 bg-[#d4af37] !text-[#171207]`}>{busy?'Creating your link…':program?.enrollmentEnabled?'Create my referral link':'Enrollment unavailable'}</button>}
    {active&&<a href="#affiliate-toolkit" className={`${button} mt-6 bg-[#d4af37] !text-[#171207]`}>Open my promotion toolkit ↓</a>}
   </div>
  </section>
  {error&&<div role="alert" className={panel}><p>{error}</p><button onClick={load} className={`${button} mt-3`}>Retry account details</button></div>}
  {!program&&!error&&<p role="status">Loading your partner desk…</p>}
  {notice&&<p role="status" className="rounded border border-[#8a6b32] p-3 text-[#efd28a]">{notice}</p>}
  {program&&!program.payoutsEnabled&&<p className="rounded-lg border border-amber-700/40 bg-amber-950/20 p-4 text-sm text-amber-200">Promotion and commission accounting are separate from cash payouts. Payouts are not live yet. Recorded balances are not funds available to withdraw.</p>}
  {active&&<section className={panel}>
   <h2 className="text-xl font-semibold">Your referral link</h2><p className="mt-2 text-sm text-[#bcac8e]">Campaign copy below includes this link automatically.</p>
   <div className="mt-4 flex flex-wrap gap-3"><input aria-label="Your referral link" data-testid="affiliate-link" readOnly value={link} className="min-w-0 flex-1 rounded border border-[#66502a] bg-black p-3 text-sm text-[#e8c46f]"/><button data-testid="copy-affiliate-link" onClick={()=>copy(link)} className={button}>Copy link</button></div>
   <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">{[['Link clicks',overview.clicks],['Signups',overview.signups],['Paid referrals',overview.payingReferrals],['Pending commission',`$${Number(overview.pending||0).toFixed(2)}`]].map(([label,value])=><div key={label}><p className="text-xs text-[#bcac8e]">{label}</p><p className="mt-2 text-2xl text-[#e8c46f]">{value??0}</p></div>)}</div>
  </section>}
  <section className={panel}><h2 className="text-xl font-semibold">Three levels. Real membership referrals.</h2>
   <p className="mt-3 text-sm leading-relaxed text-[#bcac8e]">Level 1 is your direct referral. Levels 2 and 3 are qualifying membership purchases referred through the next two levels below you. Each recipient’s membership tier determines their rate at the time of payment. Recruitment alone earns no commission.</p>
   {program&&<div className="mt-5 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{['Your affiliate tier','Level 1','Level 2','Level 3'].map(x=><th key={x} className="p-3 text-[#e8c46f]">{x}</th>)}</tr></thead><tbody>{Object.entries(program.rates||{}).map(([tier,rates])=><tr key={tier} className={`border-t border-[#514027] ${program.tier===tier?'bg-[#d4af37]/10':''}`}><th className="p-3 capitalize">{tier}{program.tier===tier?' · Your tier':''}</th>{rates.map((rate,index)=><td key={index} className="p-3">{rate?`${rate}%`:'—'}</td>)}</tr>)}</tbody></table></div>}
   <p className="mt-4 text-xs leading-relaxed text-[#bcac8e]">Qualifying paid subscriptions and renewals accrue commission. The ledger applies a {program?.holdDays??30}-day hold; refunds and chargebacks reverse commissions. Earnings depend on actual qualifying sales and are not guaranteed. Your affiliate commission tier is based on membership records, separately from administrator tool access.</p>
   <Link to="/dashboard/subscription" className="mt-4 inline-block text-sm text-[#e8c46f] underline">Review membership options</Link>
  </section>
  <section id="affiliate-toolkit" className={panel}><h2 className="text-2xl font-semibold">Your promotion toolkit</h2><p className="mt-2 text-sm text-[#bcac8e]">Make it your voice. Keep your referral link, affiliate disclosure and risk statement.</p>
   {!active?<p className="mt-6 text-[#e8c46f]">Create your referral link above to personalize your campaigns.</p>:<>
    <div className="my-5 flex gap-3" aria-label="Marketing format">{['Email','Social','Community'].map(type=><button key={type} onClick={()=>setTab(type)} aria-pressed={tab===type} className={`${button} ${tab===type?'bg-[#342914]':''}`}>{type}</button>)}</div>
    <div className="grid gap-4 lg:grid-cols-2">{templates.filter(t=>t.type===tab).map(t=><article key={t.id} className="rounded-lg border border-[#514027] p-4"><h3 className="font-semibold text-[#e8c46f]">{t.title}</h3>{t.subject&&<p className="my-3 text-sm">Subject: {t.subject}</p>}<textarea aria-label={t.title} readOnly value={t.body} className="mt-3 min-h-64 w-full rounded border border-[#514027] bg-[#080808] p-3 text-sm leading-relaxed text-[#c4b89f]"/><button onClick={()=>copy((t.subject?`Subject: ${t.subject}\n\n`:'')+t.body)} className={`${button} mt-3`}>Copy {t.type.toLowerCase()}</button></article>)}</div>
    <h3 className="mt-8 text-xl font-semibold">Black-and-gold banner library</h3>
    <div className="mt-4 grid gap-4 lg:grid-cols-3">{BANNER_FORMATS.map(format=><article key={format.name} className="rounded-lg border border-[#514027] p-4"><div className="rounded border border-[#8a6b32] bg-black p-5"><p className="font-serif text-xl text-[#e8c46f]">KAOS TRADING</p><p className="mt-2 text-xs text-[#c4b89f]">Your bot. Your data. Your KAOS.</p></div><h4 className="mt-4 font-semibold">{format.name}</h4><p className="my-2 text-xs text-[#bcac8e]">{format.width} × {format.height} PNG</p><button className={button} onClick={async()=>{try{await downloadBanner(format);setNotice('Banner downloaded. Add your campaign link and affiliate disclosure when publishing.');}catch{setNotice('Banner export failed. Try again after the artwork finishes loading.');}}}>Download banner</button><button className={`${button} mt-2`} onClick={()=>copy(campaignLink(link,'banner'))}>Copy banner link</button></article>)}</div>
   </>}
   {assets.length>0&&<div className="mt-7"><h3 className="text-lg font-semibold">Additional published campaigns</h3>{assets.map(asset=><article key={asset.id} className="mt-3 border-t border-[#514027] pt-3"><h4>{asset.title}</h4>{asset.copy&&<button className={`${button} mt-2`} onClick={()=>copy(asset.copy)}>Copy published text</button>}</article>)}</div>}
  </section>
  <section className={panel}><h2 className="text-xl font-semibold">A simple way to start</h2><ol className="mt-4 list-decimal space-y-3 pl-5 text-sm text-[#c4b89f]"><li>Explore KAOS yourself and describe only the features you have used.</li><li>Pick a banner, email or social post and personalize it for your audience.</li><li>Share where promotion is welcome, disclose your affiliate relationship, and review your referral activity here.</li></ol><p className="mt-4 text-xs text-[#bcac8e]">Send email only to people who have agreed to receive it. Add your sender details and an unsubscribe method. Do not promise trading profits, guaranteed income or risk-free trading.</p></section>
  {active&&<section className={panel} data-testid="affiliate-connect"><h2 className="text-xl font-semibold">Stripe payout setup</h2><p className="mt-3 text-sm text-[#bcac8e]">Connect your account through Stripe’s hosted onboarding. Enter identity, tax and banking details only on Stripe’s website.</p><p className="mt-3 text-sm text-[#e8c46f]">{!connect?'Checking setup…':connect.error?'Cannot check Stripe setup right now.':!connect.configured?'Platform setup is not available yet.':connect.payoutsReady?'Stripe reports your payout profile is ready.':connect.connected?'Your Stripe profile needs attention.':'Your Stripe account is not connected.'}</p><button disabled={busy||!connect?.configured} onClick={connectStripe} className={`${button} mt-4`}>{busy?'Opening Stripe…':'Continue to Stripe'}</button><p className="mt-3 text-xs text-[#bcac8e]">{connect?.configured&&connect.mode==='test'?'Test-mode onboarding. ':''}Completing onboarding does not enable transfers or release a pending commission hold.</p></section>}
  {ledger&&<LedgerCard ledger={ledger}/>}
 </div>;
}
