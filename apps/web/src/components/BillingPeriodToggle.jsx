import React from 'react';
import './BillingPeriodToggle.css';
export default function BillingPeriodToggle({value,onChange,plans}){
 const available=(interval)=>(plans||[]).some(p=>p.id!=='free'&&(p.interval||'month')===interval);
 return <div className="kaos-billing-period"><div role="group" aria-label="Billing period">{[['month','Monthly'],['year','Yearly']].map(([id,label])=><button key={id} type="button" aria-pressed={value===id} disabled={!available(id)} onClick={()=>onChange(id)}>{label}</button>)}</div><p>{value==='year'?'Billed once per year. Same tier benefits.':'Billed monthly. Choose yearly to compare annual savings.'}</p>{!available('year')&&<p>Yearly memberships are not currently available.</p>}</div>;
}
