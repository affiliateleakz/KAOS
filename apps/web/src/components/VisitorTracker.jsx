import {useEffect,useRef} from 'react';
import {useLocation} from 'react-router-dom';
import {useAuth} from '../context/AuthContext';
import {api} from '../lib/api';
import {analyticsEnabled,excludeOwnerBrowser,captureReferral,trackingIds,trackingPath} from '../lib/visitorTracking';

export default function VisitorTracker(){
 const location=useLocation(),last=useRef('');
 const {user,loading}=useAuth();
 useEffect(()=>{
  if(loading||user===undefined)return;
  if(['admin','super_admin','moderator'].includes(user?.role)){excludeOwnerBrowser();return;}
  if(!analyticsEnabled())return;
  if(location.pathname.startsWith('/admin')||location.pathname.includes('password')||location.pathname==='/auth/callback')return;
  const search=new URLSearchParams(location.search);captureReferral(search);
  const ids=trackingIds(search);if(!ids)return;
  const path=trackingPath(location.pathname);
  const key=path+':'+location.search+':'+ids.sessionId;
  async function record(kind,target='',entry=false){
   if(!analyticsEnabled())return;
   const payload={eventId:crypto.randomUUID(),visitorId:ids.visitorId,sessionId:ids.sessionId,kind,path,target,ref:ids.ref,
    source:ids.source,medium:ids.medium,campaign:ids.campaign,referrer:ids.referrer,entry};
   try{await api.post('/api/analytics/visit',payload,{timeout:5000});}catch{} // Telemetry never blocks navigation or checkout.
  }
  if(last.current!==key){last.current=key;record('pageview','',Boolean(search.get('ref')));}
  function click(event){
   const link=event.target.closest?.('a[href]');
   if(!link||event.button>0)return;
   try{const target=new URL(link.href,window.location.origin);if(['https:','http:'].includes(target.protocol))record('click',target.origin+(target.origin===window.location.origin?trackingPath(target.pathname):''));}catch{}
  }
  document.addEventListener('click',click,true);
  return()=>document.removeEventListener('click',click,true);
 },[location.pathname,location.search,user?.id,user?.role,loading]);
 return null;
}
