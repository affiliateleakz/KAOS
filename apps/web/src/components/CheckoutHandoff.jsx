import React,{useEffect,useRef,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {api,errMsg} from '../lib/api';
import {stripeCheckoutUrl} from '../lib/purchaseFlow';

export default function CheckoutHandoff({plan,user}) {
 const [sp]=useSearchParams();const trial=sp.get('trial')==='1'&&plan.tier==='pro'&&plan.interval==='month';
 const request=useRef(null),[attempt,setAttempt]=useState(0),[error,setError]=useState('');
 useEffect(()=>{
  const key=user.id+':'+plan.id+':'+trial;
  // Reuse the promise on React effect replay; Stripe/server idempotency is the second boundary.
  if(request.current?.key!==key||request.current?.attempt!==attempt)
   request.current={key,attempt,promise:api.post('/api/billing/checkout',{plan_id:plan.id,origin_url:window.location.origin,start_trial:trial},{timeout:60000})
    .then(({data})=>stripeCheckoutUrl(data.checkout_url))};
  let active=true;setError('');
  request.current.promise.then(url=>{if(active)window.location.assign(url);}).catch(e=>{if(active)setError(errMsg(e));});
  return ()=>{active=false;};
 },[plan.id,user.id,trial,attempt]);
 return <section data-testid="checkout-handoff" className="space-y-4">
  <h2 className="text-xl text-[#e8c46f]">{error?'Continue your payment':'Opening secure payment…'}</h2>
  <p className="text-sm text-slate-400">Your selected membership is {plan.name}. Stripe will show the full price and renewal terms before you pay. Paid access starts only after verified payment.</p>
  {error&&<><p role="alert" className="text-amber-200">{error}</p><button onClick={()=>setAttempt(n=>n+1)} className="kaos-auth-submit w-full">Retry secure checkout</button></>}
  <Link to="/dashboard/subscription" className="block text-sm text-[#e8c46f] underline">Already subscribed? Manage existing billing</Link>
 </section>;
}
