export function plansForInterval(plans,interval){return (plans||[]).filter(p=>p.id==='free'||(p.interval||'month')===interval);}
export function annualSaving(plan,plans){
 if(plan.interval!=='year')return null;
 const monthly=(plans||[]).find(p=>p.tier===plan.tier&&p.interval==='month'&&p.currency===plan.currency);
 if(!monthly||!Number.isSafeInteger(monthly.amount)||!Number.isSafeInteger(plan.amount)||monthly.amount<=0||plan.amount<=0)return null;
 const cents=monthly.amount*12-plan.amount;
 return cents>0?{cents,currency:plan.currency}:null;
}
export function recommendedMonthly(plan){return plan.interval==='month'&&(plan.recommended===true||(plan.recommended===undefined&&plan.tier==='ultimate'));}
