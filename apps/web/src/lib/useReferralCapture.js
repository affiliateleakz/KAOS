import {useEffect} from 'react';
import {api} from './api';

export function useReferralCapture(search){
 useEffect(()=>{
  const ref=search.get('ref');if(!ref||ref.length>128)return;
  try{localStorage.setItem('kaos_ref',ref);}catch{}
  try{
   const campaign=search.get('utm_source')||'signup';
   const key='kaos-ref-click:'+ref+':'+campaign;
   if(sessionStorage.getItem(key))return;
   sessionStorage.setItem(key,'1');
   api.get('/api/aff/track',{params:{ref,campaign}}).catch(()=>{});
  }catch{}
 },[search]);
}
