import {it,expect} from 'vitest';
import {registrationLink,purchaseLoginLink,stripeCheckoutUrl} from './purchaseFlow';
it('paid homepage choices open checkout with exact annual plan and referral',()=>{
 const url=new URL(registrationLink('ultimate_yearly','ref=OWNER&utm_source=banner'),'https://example.com');
 expect(url.pathname).toBe('/checkout');expect(url.searchParams.get('plan')).toBe('ultimate_yearly');
 expect(url.searchParams.get('billing')).toBe('year');expect(url.searchParams.get('ref')).toBe('OWNER');
 expect(url.searchParams.get('utm_source')).toBe('banner');
});
it('Free CTA opens the Pro trial and login retains the selected purchase',()=>{
 expect(registrationLink('free','')).toBe('/checkout?trial=1&plan=pro');
 const login=new URL(purchaseLoginLink('pro','ref=OWNER'),'https://example.com');
 expect(login.pathname).toBe('/login');expect(login.searchParams.get('plan')).toBe('pro');
 expect(login.searchParams.get('ref')).toBe('OWNER');
});
it('only accepts secure Stripe checkout redirects, never arbitrary URLs',()=>{
 expect(stripeCheckoutUrl('https://checkout.stripe.com/c/pay/cs_fixture#step')).toContain('checkout.stripe.com');
 for(const url of [undefined,'javascript:alert(1)','http://checkout.stripe.com/pay','https://checkout.stripe.com.evil.test',
                  'https://checkout.stripe.com@evil.test/','https://user:secret@checkout.stripe.com/pay'])
  expect(()=>stripeCheckoutUrl(url)).toThrow();
});
