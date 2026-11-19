import {it,expect} from 'vitest';
import {plansForInterval,annualSaving,recommendedMonthly} from './billingPlans';
const plans=[{id:'free'},{id:'pro',tier:'pro',amount:2995,currency:'usd',interval:'month'},{id:'ultimate',tier:'ultimate',amount:9995,currency:'usd',interval:'month'},{id:'pro_yearly',tier:'pro',amount:29995,currency:'usd',interval:'year'},{id:'ultimate_yearly',tier:'ultimate',amount:99595,currency:'usd',interval:'year'}];
it('keeps Free in either billing period and selects only matching paid plans',()=>{
 expect(plansForInterval(plans,'month').map(p=>p.id)).toEqual(['free','pro','ultimate']);
 expect(plansForInterval(plans,'year').map(p=>p.id)).toEqual(['free','pro_yearly','ultimate_yearly']);
});
it('computes annual savings from configured prices without treating annual as monthly',()=>{
 expect(annualSaving(plans[3],plans).cents).toBe(5945);
 expect(annualSaving(plans[4],plans).cents).toBe(20345);
 expect(annualSaving({...plans[3],amount:100000},plans)).toBeNull();
 expect(annualSaving(plans[3],[])).toBeNull();
 expect(annualSaving(plans[1],plans)).toBeNull();
});
it('recommends Ultimate monthly, never its yearly alternative',()=>{
 expect(recommendedMonthly(plans[2])).toBe(true);
 expect(recommendedMonthly(plans[4])).toBe(false);
 expect(recommendedMonthly(plans[1])).toBe(false);
});
