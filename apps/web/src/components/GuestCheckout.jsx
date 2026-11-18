import React,{useState,useEffect} from 'react';
import {Link,useNavigate,useSearchParams} from 'react-router-dom';
import {planPrice} from '../pages/Memberships';
import {api,errMsg} from '../lib/api';
import {stripeCheckoutUrl,purchaseLoginLink,registrationLink} from '../lib/purchaseFlow';

export default function GuestCheckout({plan,plans=[]}) {
 const [sp]=useSearchParams(),nav=useNavigate();
 const [name,setName]=useState(''),[email,setEmail]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[signin,setSignin]=useState(false);
 const trial=sp.get('trial')==='1'&&plan.tier==='pro'&&plan.interval==='month';
 const price=planPrice(plan);
 const alternatives=plans.filter(p=>(['pro','ultimate'].includes(p.tier)&&p.interval==='month')||p.id===plan.id);
 function choose(id){const next=new URLSearchParams(sp);if(id==='pro')next.set('trial','1');else next.delete('trial');nav(registrationLink(id,next));setError('');setSignin(false);}
 async function submit(e){e.preventDefault();setBusy(true);setError('');setSignin(false);
  try {let refCode=sp.get('ref');try{refCode=refCode||localStorage.getItem('kaos_ref');}catch{}
   await api.post('/api/billing/guest-intent',{name,email,plan_id:plan.id,refCode,start_trial:trial});
   const {data}=await api.post('/api/billing/guest-checkout',{}, {timeout:60000});
   if(data.completed)nav('/payment/complete?session_id='+encodeURIComponent(data.session_id));
   else window.location.assign(stripeCheckoutUrl(data.checkout_url));
  }catch(e){const detail=e.response?.data?.detail;setSignin(detail?.code==='SIGN_IN_REQUIRED');setError(typeof detail==='object'?detail.message:errMsg(e));}finally{setBusy(false);}}
 return <form onSubmit={submit} className="space-y-4" data-testid="guest-checkout">
  <label className="block">Name<input data-testid="checkout-name" required maxLength={120} autoComplete="name" value={name} onChange={e=>setName(e.target.value)} className="kaos-auth-input mt-2 w-full"/></label>
  <label className="block">Email<input data-testid="checkout-email" type="email" required autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} className="kaos-auth-input mt-2 w-full"/></label>
  <label className="block">Membership<select aria-label="Membership plan" value={plan.id} onChange={e=>choose(e.target.value)} className="kaos-auth-input mt-2 w-full">{alternatives.map(p=><option key={p.id} value={p.id}>{p.name} · {planPrice(p)} / {p.interval}{p.tier==='pro'&&p.interval==='month'?' · 7-day free trial available':''}</option>)}</select></label>
  {trial?<section data-testid="trial-terms" className="rounded border border-[#8a6b32] p-4"><h2 className="text-lg text-[#e8c46f]">7-day Pro free trial</h2><p>All Pro features for 7 days. $0 today, then {price} / month unless canceled. One trial per customer email.</p><p>Stripe collects your payment details and shows the exact first charge date before you confirm. Cancel in Manage billing before the trial ends.</p></section>:<p>Stripe will show {price} / {plan.interval} and renewal terms before you pay. Only Pro monthly offers a free trial.</p>}
  <p className="text-sm text-slate-400">After Stripe confirms {trial?'your trial':'payment'}, we’ll email your secure account-setup link.</p>
  <p className="text-xs text-slate-400">Using KAOS includes the service data use described in our <a href="/privacy.html" className="underline">privacy policy</a>. Membership does not guarantee trading profits.</p>
  {error&&<p role="alert">{error}</p>}
  {signin?<Link className="block text-[#e8c46f] underline" to={purchaseLoginLink(plan.id,sp)}>Sign in to continue this membership</Link>:<button disabled={busy} className="kaos-auth-submit w-full">{busy?'Opening Stripe…':'Continue to secure payment'}</button>}
  <Link className="block text-[#e8c46f] underline" to={purchaseLoginLink(plan.id,sp)}>Already have an account? Sign in</Link>
 </form>;
}

export function PaymentComplete(){
 const [sp]=useSearchParams(),sid=sp.get('session_id');const [receipt,setReceipt]=useState(null),[error,setError]=useState(''),[attempt,setAttempt]=useState(0),[notice,setNotice]=useState('');
 useEffect(()=>{let active=true,timer;async function check(){try{const {data}=await api.get('/api/billing/guest-status/'+encodeURIComponent(sid));if(!active)return;setReceipt(data);setError('');if(data.state==='pending')timer=setTimeout(check,3000);}catch(e){if(active)setError(errMsg(e));}}if(sid)check();else setError('Missing payment receipt');return()=>{active=false;clearTimeout(timer);};},[sid,attempt]);
 async function cancelTrial(){try{const {data}=await api.post('/api/billing/guest-cancel/'+encodeURIComponent(sid));if(data.cancelAtPeriodEnd)setNotice('Trial cancellation confirmed. It will not renew.');}catch(e){setError(errMsg(e));}}
 async function resend(){try{const {data}=await api.post('/api/billing/guest-resend/'+encodeURIComponent(sid));setNotice(data.sent?'Setup email sent. Check your inbox and spam folder.':'Please wait one minute, then retry.');}catch(e){setError(errMsg(e));}}
 return <main className="kaos-auth-shell p-8"><section className="kaos-auth-card mx-auto max-w-xl"><h1 className="text-2xl text-[#e8c46f]">{receipt?.state==='active'?(receipt.trial?'Pro trial confirmed':'Payment confirmed'):'Confirming your membership'}</h1>{error?<><p role="alert">{error}</p><button onClick={()=>setAttempt(n=>n+1)}>Retry confirmation</button></>:receipt?.state==='active'?<><p>{receipt.trial?('Your Pro trial is confirmed. Trial ends '+(receipt.trialEndsAt?new Date(receipt.trialEndsAt).toLocaleString():'at the date shown in Stripe')+'. Manage or cancel your subscription from billing after sign-in.'):'Your payment was confirmed.'}</p>{receipt.setupRequired?<><p>Finish account setup using the secure link sent to {receipt.receiptEmail}. This page cannot set your password.</p>{!receipt.emailSent&&<p>Your setup email has not been delivered yet. Retry below or contact support with your Stripe receipt.</p>}<button onClick={resend} className="kaos-auth-submit mt-4">Resend account setup email</button></>:<p>Your account is ready to sign in.</p>}<p role="status">{notice}</p>{receipt.trial&&<button onClick={cancelTrial} className="block mt-4 text-[#e8c46f] underline">Cancel trial renewal</button>}<Link to="/login" className="block mt-4 text-[#e8c46f] underline">Sign in to KAOS</Link></>:receipt?.state==='signin_required'?<Link to={'/login?purchase='+encodeURIComponent(sid)} className="text-[#e8c46f] underline">Sign in to attach your paid membership</Link>:<p role="status">Waiting for Stripe payment confirmation. No membership is granted until payment is verified.</p>}</section></main>;
}
