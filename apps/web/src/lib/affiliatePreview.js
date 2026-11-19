// Positive commissions are rounded per payment, like the server Decimal ledger.
export function commissionPreview(amountCents,rates,counts){
 if(!Number.isSafeInteger(amountCents)||amountCents<0||!Array.isArray(rates)||rates.length!==3||!Array.isArray(counts)||counts.length!==3)return null;
 if(rates.some(rate=>!Number.isFinite(rate)||rate<0||rate>100)||counts.some(count=>!Number.isInteger(count)||count<0||count>10000))return null;
 const levels=rates.map((rate,index)=>Math.floor((amountCents*Math.round(rate*100)+5000)/10000)*counts[index]);
 return {levels,total:levels.reduce((sum,value)=>sum+value,0)};
}
export function commissionMoney(cents,currency='usd'){
 try{return new Intl.NumberFormat('en-US',{style:'currency',currency,maximumFractionDigits:2}).format(cents/100);}
 catch{return (cents/100).toFixed(2)+' '+currency.toUpperCase();}
}
