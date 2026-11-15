import React, {createContext, useContext, useEffect, useState} from 'react';
import {Link} from 'react-router-dom';
import {LockKeyhole, ArrowUpRight, Check} from 'lucide-react';
import {api} from '../lib/api';

const MembershipContext = createContext(null);
export const FEATURE_ROUTES = {
  opportunities: {key:'scanners', title:'Opportunity Radar', description:'Organize market observations into one focused research workspace.'},
  'public-trades': {key:'scanners', title:'Political & Wall Street Trades', description:'Explore reported disclosures and institutional holdings in one place.'},
  'crypto-scanner': {key:'scanners', title:'Crypto Scanner & Heat Map', description:'Explore market pairs, filter opportunities and compare reported market activity.'},
  'stock-heatmap': {key:'scanners', title:'Stock Heat Map', description:'See a curated stock and ETF watchlist organized by sector and reported performance.'},
  'kaos-ai': {key:'aiInsights', title:'KAOS AI Insights', description:'Bring AI research and market observations into your review process.'},
  strategies: {key:'cloudStrategies', title:'Cloud Strategies', description:'Keep your strategies organized in your KAOS account.'},
};
export const useMembership = () => useContext(MembershipContext);

export function MembershipProvider({children}) {
  const [result, setResult] = useState({loading:true});
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setResult({loading:true});
    api.get('/api/v1/trading/config', {signal:controller.signal}).then(({data}) => {
      if (!data?.entitlements || typeof data.entitlements !== 'object') throw Error('Missing entitlements');
      setResult({entitlements:data.entitlements, loading:false});
    }).catch(error => {
      if (!controller.signal.aborted) setResult({loading:false, error:true, status:error.response?.status});
    });
    return () => controller.abort();
  }, [revision]);
  return <MembershipContext.Provider value={{...result, retry:()=>setRevision(n=>n+1)}}>{children}</MembershipContext.Provider>;
}

export function UpgradeContent({title, description, compact=false}) {
  return <section data-testid="membership-upgrade" className={`overflow-hidden rounded-xl border border-[#8a6b32]/60 bg-[#11100d] ${compact?'my-4':'mx-auto max-w-5xl'}`}>
    <div className="relative overflow-hidden px-6 py-9 sm:px-10">
      {!compact && <div aria-hidden="true" className="absolute inset-0 bg-[url('/kaos-cinematic-header.jpg')] bg-cover bg-center opacity-20" />}
      <div className="relative max-w-2xl">
        <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[.18em] text-[#e8c46f]"><LockKeyhole size={15}/> More room for your KAOS</span>
        <h1 className="mt-5 text-3xl font-semibold text-[#f4e6c6] sm:text-4xl">Unlock {title}</h1>
        <p className="mt-4 max-w-xl text-base leading-relaxed text-[#c4b89f]">{description}</p>
        <p className="mt-3 text-sm text-[#c4b89f]">Included with Pro and Ultimate. Your current access does not include this tool.</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link data-testid="compare-memberships" to="/dashboard/subscription" className="inline-flex min-h-11 items-center gap-2 rounded-md bg-[#d4af37] px-5 py-3 font-semibold text-[#171207] hover:bg-[#e8c46f]">Compare memberships <ArrowUpRight size={16}/></Link>
          <Link to="/dashboard/trading" className="inline-flex min-h-11 items-center rounded-md border border-[#66502a] px-5 py-3 text-[#e8d8b2]">Keep using your current tools</Link>
        </div>
      </div>
    </div>
    {!compact && <div className="grid gap-5 border-t border-[#514027] bg-[#17140e] p-6 sm:grid-cols-3 sm:p-10">
      {['Four-chart workspace','Scanners and market research','Cloud strategies and AI insights'].map(text=><div key={text} className="flex items-start gap-3 text-sm text-[#e8d8b2]"><Check className="shrink-0 text-[#d4af37]" size={18}/>{text}</div>)}
      <p className="text-xs leading-relaxed text-[#ad9f85] sm:col-span-3">Market-data availability depends on the configured provider. Membership does not guarantee returns or enable unvalidated AI trading. Review current plans and availability before upgrading.</p>
    </div>}
  </section>;
}

export function FeatureGate({route, children}) {
  const access = useMembership();
  const feature = FEATURE_ROUTES[route];
  if (!access || access.loading) return <p role="status" className="p-6 text-[#c4b89f]">Checking your membership access…</p>;
  if (access.error) return <section className="rounded-lg border border-amber-700/40 p-6" role="alert">
    <h1 className="text-xl font-semibold">We couldn’t check your access</h1>
    <p className="my-3 text-slate-400">{access.status===401?'Your session may have expired. Sign in again to check your membership.':'The account service is unavailable. This does not mean you need to upgrade.'}</p>
    <button onClick={access.retry} className="rounded border border-[#8a6b32] px-4 py-2 text-[#e8c46f]">Try again</button>
    {access.status===401 && <Link to="/login" className="ml-4 underline">Sign in</Link>}
  </section>;
  if (access.entitlements[feature.key] === true) return children;
  return <UpgradeContent title={feature.title} description={feature.description}/>;
}
