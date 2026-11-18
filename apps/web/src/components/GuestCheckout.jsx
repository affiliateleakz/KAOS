import React,{useState,useEffect} from 'react';
import {Link,useNavigate,useSearchParams} from 'react-router-dom';
import {api,errMsg} from '../lib/api';
import {stripeCheckoutUrl,purchaseLoginLink} from '../lib/purchaseFlow';

export default function GuestCheckout({plan}) {
 const [sp]=useSearchParams(),nav=useNavigate();
 const [email,setEmail]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[signin,setSignin]=useState(false);
 async function submit(e){e.preventDefault();setBusy(true);setError('');setSignin(false);
  try {let refCode=sp.get('ref');try{refCode=refCode||localStorage.getItem('kaos_ref');}catch{}
   await api.post('/api/billing/guest-intent',{email,plan_id:plan.id,refCode});
   const {data}=await api.post('/api/billing/guest-checkout',{}, {timeout:60000});
   if(data.completed)nav('/payment/complete?session_id='+encodeURIComponent(data.session_id));
   else window.location.assign(stripeCheckoutUrl(data.checkout_url));
  }catch(e){const detail=e.response?.data?.detail;setSignin(detail?.code==='SIGN_IN_REQUIRED');setError(typeof detail==='object'?detail.message:errMsg(e));}finally{setBusy(false);}}
 return <form onSubmit={submit} className="space-y-4" data-testid="guest-checkout"><p>Pay securely with Stripe first. After payment, we’ll email a secure link to finish setting up your KAOS account.</p><label className="block">Receipt and account email<input data-testid="checkout-email" type="email" required autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} className="kaos-auth-input mt-2 w-full"/></label><p className="text-xs text-slate-400">Stripe shows the full price and renewal terms before you pay. Paid access starts after payment confirmation. Using KAOS includes the service data use described in our <a href="/privacy.html" className="underline">privacy policy</a>.</p>{error&&<p role="alert">{error}</p>}{signin?<Link className="block text-[#e8c46f] underline" to={purchaseLoginLink(plan.id,sp)}>Sign in to continue this membership</Link>:<button disabled={busy} className="kaos-auth-submit w-full">{busy?'Opening Stripe…':'Continue to secure payment'}</button>}<Link className="block text-[#e8c46f] underline" to={purchaseLoginLink(plan.id,sp)}>Already have an account? Sign in</Link></form>;
}

export function PaymentComplete(){
 const [sp]=useSearchParams(),sid=sp.get('session_id');const [receipt,setReceipt]=useState(null),[error,setError]=useState(''),[attempt,setAttempt]=useState(0),[notice,setNotice]=useState('');
 useEffect(()=>{let active=true,timer;async function check(){try{const {data}=await api.get('/api/billing/guest-status/'+encodeURIComponent(sid));if(!active)return;setReceipt(data);setError('');if(data.state==='pending')timer=setTimeout(check,3000);}catch(e){if(active)setError(errMsg(e));}}if(sid)check();else setError('Missing payment receipt');return()=>{active=false;clearTimeout(timer);};},[sid,attempt]);
 async function resend(){try{const {data}=await api.post('/api/billing/guest-resend/'+encodeURIComponent(sid));setNotice(data.sent?'Setup email sent. Check your inbox and spam folder.':'Please wait one minute, then retry.');}catch(e){setError(errMsg(e));}}
 return <main className="kaos-auth-shell p-8"><section className="kaos-auth-card mx-auto max-w-xl"><h1 className="text-2xl text-[#e8c46f]">{receipt?.state==='active'?'Payment confirmed':'Confirming your membership'}</h1>{error?<><p role="alert">{error}</p><button onClick={()=>setAttempt(n=>n+1)}>Retry confirmation</button></>:receipt?.state==='active'?<><p>Your payment was confirmed.</p>{receipt.setupRequired?<><p>Finish account setup using the secure link sent to {receipt.receiptEmail}. This page cannot set your password.</p>{!receipt.emailSent&&<p>Your setup email has not been delivered yet. Retry below or contact support with your Stripe receipt.</p>}<button onClick={resend} className="kaos-auth-submit mt-4">Resend account setup email</button><p role="status">{notice}</p></>:<p>Your account is ready to sign in.</p>}<Link to="/login" className="block mt-4 text-[#e8c46f] underline">Sign in to KAOS</Link></>:receipt?.state==='signin_required'?<Link to={'/login?purchase='+encodeURIComponent(sid)} className="text-[#e8c46f] underline">Sign in to attach your paid membership</Link>:<p role="status">Waiting for Stripe payment confirmation. No membership is granted until payment is verified.</p>}</section></main>;
}
