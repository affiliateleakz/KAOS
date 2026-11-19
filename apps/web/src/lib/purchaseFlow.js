// Public plan selection is retained through account creation, never a paid entitlement.
export function registrationLink(planId, search) {
 const query=new URLSearchParams(search);
 if(planId==='free'){planId='pro';query.set('trial','1');}
 if(planId!=='pro')query.delete('trial');
 query.set('plan',planId);
 if(planId==='yearly'||planId.endsWith('_yearly'))query.set('billing','year');else query.delete('billing');
 return (planId==='free'?'/register/account':'/checkout')+'?'+query.toString();
}
export function purchaseLoginLink(planId, search) {
 const query=new URLSearchParams(search);
 if(planId==='free'){planId='pro';query.set('trial','1');}
 if(planId!=='pro')query.delete('trial');
 query.set('plan',planId);
 return '/login?'+query.toString();
}
export function stripeCheckoutUrl(value) {
 if(typeof value!=='string')throw Error('Secure payment link is unavailable. Please retry.');
 let url;try{url=new URL(value);}catch{throw Error('Secure payment link is unavailable. Please retry.');}
 if(url.protocol!=='https:'||url.hostname!=='checkout.stripe.com'||url.port||url.username||url.password)
  throw Error('The payment link could not be verified. Please contact KAOS support.');
 return url.href;
}
