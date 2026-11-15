import React,{useEffect,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {Brand} from '../components/Brand';
import {api} from '../lib/api';
import {useReferralCapture} from '../lib/useReferralCapture';

export function registrationLink(planId, search){
 const query=new URLSearchParams(search);query.set('plan',planId);
 return '/register/account?'+query.toString();
}
export function planPrice(plan){
 if(plan.id==='free')return '$0';
 try{return new Intl.NumberFormat('en-US',{style:'currency',currency:plan.currency||'usd',maximumFractionDigits:2}).format(plan.amount/100);}
 catch{return `${plan.amount/100} ${plan.currency}`;}
}
export default function Memberships(){
 const [sp]=useSearchParams(),[catalog,setCatalog]=useState(null),[error,setError]=useState('');
 useReferralCapture(sp);
 async function load(){setError('');try{const {data}=await api.get('/api/billing/memberships');if(!Array.isArray(data.plans)||!data.plans.length)throw Error('Unavailable');setCatalog(data);}catch{setError('We couldn’t load the current memberships. Please retry before choosing a plan.');}}
 useEffect(()=>{load();},[]);
 return <div className="min-h-screen bg-[#080808] text-[#f3ead8]" data-testid="membership-selection">
  <header className="flex flex-wrap items-center justify-between gap-4 border-b border-[#514027] px-5 py-5 sm:px-10"><Link to="/"><Brand/></Link><Link to="/login" className="text-sm text-[#e8c46f]">Already a member? Sign in →</Link></header>
  <main className="mx-auto max-w-7xl space-y-9 px-5 py-9 sm:px-10 sm:py-14">
   <section className="relative overflow-hidden rounded-xl border border-[#66502a] p-7 sm:p-10"><div aria-hidden="true" className="absolute inset-0 bg-[url('/kaos-cinematic-header.jpg')] bg-cover bg-center opacity-20"/><div className="relative max-w-3xl"><p className="text-xs font-semibold uppercase tracking-[.18em] text-[#e8c46f]">Step 1 · Choose your membership</p><h1 className="mt-5 text-4xl font-semibold leading-tight sm:text-5xl">Choose your KAOS.</h1><p className="mt-5 leading-relaxed text-[#c4b89f]">Compare your trading workspace, research tools and affiliate benefits first. Then create your account with the membership you want.</p><p className="mt-4 text-sm text-[#c4b89f]">Choose membership → Create account → Review payment (paid plans only)</p></div></section>
   {error&&<section role="alert" className="rounded-lg border border-amber-700/50 p-5"><p>{error}</p><button onClick={load} className="mt-4 rounded border border-[#8a6b32] px-5 py-3 text-[#e8c46f]">Retry memberships</button></section>}
   {!catalog&&!error&&<p role="status">Loading current membership options…</p>}
   {catalog&&<>
    <section className="grid items-stretch gap-5 lg:grid-cols-3" aria-label="Membership options">{catalog.plans.map(plan=>{
     const ent=plan.entitlements||{},rates=catalog.affiliateRates?.[plan.tier]||[0,0,0];
     const features=[['KAOS Strategy bot',ent.botAccess],['Community access',ent.community],['Market scanners & heatmaps',ent.scanners],['AI insights',ent.aiInsights],['Cloud strategies',ent.cloudStrategies],['Premium tools',ent.premiumTools]];
     return <article key={plan.id} className="flex min-w-0 flex-col rounded-xl border border-[#66502a] bg-[#12100d] p-6" data-testid={`membership-card-${plan.id}`}>
      <p className="text-xs uppercase tracking-widest text-[#b5a487]">{plan.id==='free'?'Start exploring':plan.interval==='year'?'Annual membership':plan.interval==='month'?'Monthly membership':'Paid membership'}</p><h2 className="mt-3 text-3xl font-semibold text-[#e8c46f]">{plan.name}</h2>
      <p className="mt-5 text-4xl font-semibold">{planPrice(plan)}{plan.interval&&<span className="text-sm font-normal text-[#b5a487]"> / {plan.interval}</span>}</p>
      <p className="mt-3 text-sm text-[#c4b89f]">{Math.min(4,Number(ent.chartLimit)||1)} chart{Number(ent.chartLimit)>1?'s':''} · {Number(ent.deviceLimit)||1} device{Number(ent.deviceLimit)>1?'s':''}</p>
      <p className="mt-2 text-xs text-[#b5a487]">Chart limits apply to the KAOS website workspace. The extension uses your broker’s native charts.</p>
      <ul className="my-6 space-y-3 text-sm">{features.map(([label,enabled])=><li key={label} className={enabled?'text-[#dfd1b5]':'text-[#8e8270]'}><span aria-hidden="true" className="mr-2">{enabled?'✓':'—'}</span>{label}{!enabled&&<span className="sr-only"> — not included</span>}</li>)}
       {(ent.modes||[]).includes('AI')&&<li className="text-[#c4b89f]">AI-mode eligibility · {catalog.aiExecutionValidated?'subject to account access':'execution validation pending'}</li>}
      </ul>
      <div className="mb-6 rounded-lg border border-[#514027] bg-[#1b170e] p-4"><h3 className="font-semibold text-[#e8c46f]">Affiliate benefits</h3><dl className="mt-3 space-y-2 text-sm">{rates.map((rate,index)=><div key={index} className="flex justify-between gap-4"><dt>{index===0?'Direct referral · Level 1':`Level ${index+1}`}</dt><dd>{rate?`${rate}%`:'Not included'}</dd></div>)}</dl><p className="mt-3 text-xs leading-relaxed text-[#b5a487]">On qualifying paid membership sales, based on your active tier when payment occurs. Not a guaranteed income.</p></div>
      <Link data-testid={`choose-membership-${plan.id}`} to={registrationLink(plan.id,sp)} className="mt-auto rounded-md bg-[#d4af37] px-5 py-3 text-center font-semibold text-[#171207] hover:bg-[#e8c46f]">{plan.id==='free'?'Start free':`Choose ${plan.name}`}</Link><p className="mt-3 text-center text-xs text-[#b5a487]">{plan.id==='free'?'No card required.':'Create your account next. Paid access starts after confirmed payment.'}</p>
     </article>;
    })}</section>
    {!catalog.checkoutEnabled&&<p role="status" className="rounded-lg border border-amber-700/50 p-4 text-sm text-amber-200">Paid checkout is not available yet. You can choose a preferred plan and create your account; paid features stay locked until payment is available and confirmed.</p>}
    <section className="rounded-xl border border-[#514027] bg-[#12100d] p-6 sm:p-8"><h2 className="text-2xl font-semibold">How the three-level affiliate program works</h2><ol className="mt-5 grid list-inside list-decimal gap-4 text-sm leading-relaxed text-[#c4b89f] sm:grid-cols-3"><li>Join KAOS, then optionally enroll in the affiliate program to get your referral link and promotion toolkit.</li><li>Your direct referrals are Level 1. Qualifying sales through the next two referral levels can count as Levels 2 and 3.</li><li>Your membership determines your rate at the time of payment. Commissions have a 30-day hold and refunds or chargebacks reverse them.</li></ol><p className="mt-5 text-sm text-[#b5a487]">Recruitment and unpaid signups do not earn commissions. Joining the affiliate program is optional; it is not required to use the trading tools.</p>{!catalog.affiliateEnrollmentEnabled&&<p className="mt-4 text-sm text-amber-200">Affiliate enrollment is currently paused.</p>}{!catalog.payoutsEnabled&&<p className="mt-4 text-sm text-amber-200">Cash payouts are not live yet. Commission examples and rates do not mean funds can currently be withdrawn.</p>}</section>
    <p className="text-xs leading-relaxed text-[#aa9a80]">Trading involves risk and can result in losses. A membership does not guarantee trading profits, affiliate income, provider availability or access to unvalidated AI execution. Market feeds require supported, configured providers. Selecting a paid plan does not charge you or activate paid access.</p>
   </>}
  </main>
 </div>;
}
