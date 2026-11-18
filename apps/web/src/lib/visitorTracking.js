const VISITOR='kaos_analytics_visitor',SESSION='kaos_analytics_session';
const REF='kaos_ref',REF_AT='kaos_ref_saved_at';
const DAY=86400000;
export function analyticsEnabled(){
 try{return typeof window!=='undefined'&&navigator.doNotTrack!=='1'&&!navigator.globalPrivacyControl&&localStorage.getItem('kaos_analytics_opt_out')!=='1';}catch{return false;}
}
export function captureReferral(search){
 const value=search?.get('ref');
 if(!value||value.length>128)return;
 try{localStorage.setItem(REF,value);localStorage.setItem(REF_AT,String(Date.now()));}catch{}
}
export function referralCode(search){
 const current=search?.get('ref');if(current&&current.length<=128){captureReferral(search);return current;}
 try{
  const value=localStorage.getItem(REF);if(!value||value.length>128)return undefined;
  const saved=Number(localStorage.getItem(REF_AT));
  if(!saved){localStorage.setItem(REF_AT,String(Date.now()));return value;}
  if(Date.now()-saved>30*DAY){localStorage.removeItem(REF);localStorage.removeItem(REF_AT);return undefined;}
  return value;
 }catch{return undefined;}
}
export function trackingIds(search){
 if(!analyticsEnabled())return null;
 try{
  const stamp=Date.now();let visitor=JSON.parse(localStorage.getItem(VISITOR)||'null');
  if(!visitor?.id||stamp-visitor.createdAt>90*DAY){visitor={id:crypto.randomUUID(),createdAt:stamp};localStorage.setItem(VISITOR,JSON.stringify(visitor));}
  let session=JSON.parse(sessionStorage.getItem(SESSION)||'null');
  const incoming={ref:referralCode(search),source:search?.get('utm_source')||'',medium:search?.get('utm_medium')||'',campaign:search?.get('utm_campaign')||''};
  const changed=session&&((incoming.source&&incoming.source!==session.source)||(incoming.campaign&&incoming.campaign!==session.campaign)||(incoming.ref&&incoming.ref!==session.ref));
  if(!session?.id||stamp-session.seenAt>30*60000||changed){session={id:crypto.randomUUID(),...incoming,referrer:referrerOrigin(),seenAt:stamp};}
  session.seenAt=stamp;sessionStorage.setItem(SESSION,JSON.stringify(session));
  return {visitorId:visitor.id,sessionId:session.id,...session};
 }catch{return null;}
}
export function storedTrackingIds(){
 if(!analyticsEnabled())return null;
 try{const visitor=JSON.parse(localStorage.getItem(VISITOR)||'null'),session=JSON.parse(sessionStorage.getItem(SESSION)||'null');return visitor?.id&&session?.id?{visitorId:visitor.id,sessionId:session.id}:null;}catch{return null;}
}

function referrerOrigin(){try{return document.referrer?new URL(document.referrer).origin:'';}catch{return '';}}
export function trackingPath(path){
 const parts=path.split('/').filter(Boolean);const head=parts[0]||'';
 if(!['','register','checkout','login','memberships','privacy','privacy.html','payment','dashboard','share','s','community'].includes(head))return '/other';
 if(['share','s','community'].includes(head))return '/'+head;
 if(['payment','dashboard','register'].includes(head))return '/'+head+(parts[1]&&['account','complete','success','cancel','subscription','affiliate','trading','strategies','community','radar','profile'].includes(parts[1])?'/'+parts[1]:'');
 return '/'+head;
}
