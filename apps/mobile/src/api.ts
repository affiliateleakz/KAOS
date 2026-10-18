import * as SecureStore from 'expo-secure-store';
export const BASE=(process.env.EXPO_PUBLIC_KAOS_API_URL || 'https://api.tradingwithkaos.com').replace(/\/$/,'');
const SESSION_KEY='kaos_mobile_access_token';
export type Evidence={source:string;direction:string;summary:string;observed_at:string;published_at:string;source_url?:string;weight:number};
export type Opportunity={asset:string;asset_class:string;score:number;bias:string;status:string;independent_sources:number;confirming_directional_sources?:number;opposing_directional_sources?:number;evidence_truncated?:boolean;score_type:string;trade_recommendation:boolean;evidence:Evidence[]};
export type Feed={mode:string;coverage:string;results:Opportunity[];scanned_observations:number;note:string};
export async function getToken(){return SecureStore.getItemAsync(SESSION_KEY)}
export async function setToken(token:string){await SecureStore.setItemAsync(SESSION_KEY,token)}
export async function logout(){await SecureStore.deleteItemAsync(SESSION_KEY)}
export async function request<T>(path:string):Promise<T>{
 const token=await getToken(); if(!token) throw new Error('Sign in required');
 const response=await fetch(BASE+path,{headers:{Authorization:`Bearer ${token}`,Accept:'application/json'}});
 if(response.status===401) throw new Error('Session expired. Sign in again.');
 if(response.status===403) throw new Error('This feature needs a KAOS Pro or Ultimate membership.');
 if(!response.ok) throw new Error(`KAOS API error ${response.status}`);
 return response.json() as Promise<T>;
}
export async function loadFeed(assetClass?:string):Promise<Feed>{return request<Feed>(`/api/v1/intelligence/opportunities?limit=50${assetClass?`&asset_class=${encodeURIComponent(assetClass)}`:''}`)}
export async function loadStatus(){return request<{mode:string;collector_configured:boolean;live_feeds_included:boolean;asset_classes:string[]}>('/api/v1/intelligence/status')}

export type SourceHealth={provider:string;asset_class:string;source:string;age_minutes:number;state:string;observations_in_sample:number};
export type Health={mode:string;status_meaning:string;sample_observations:number;sample_truncated:boolean;sources:SourceHealth[]};
export async function loadHealth():Promise<Health>{return request<Health>('/api/v1/intelligence/health')}

export async function send<T>(path:string,method:'POST'|'PUT',body:unknown={}):Promise<T>{
 const token=await getToken(); if(!token) throw new Error('Sign in required');
 const response=await fetch(BASE+path,{method,headers:{Authorization:`Bearer ${token}`,Accept:'application/json','Content-Type':'application/json'},body:JSON.stringify(body)});
 const data=await response.json().catch(()=>({}));
 if(response.status===401) throw new Error('Session expired. Sign in again.');
 if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:`KAOS API error ${response.status}`);
 return data as T;
}
export type Candle={time:number;open:number;high:number;low:number;close:number;volume:number};
export type PaperSession={broker:string;symbol:string;granularity:number;notional:string;fee_rate?:string;slippage_bps?:number};
export type Quote={bid:string;ask:string;quote_time:string;source:string;delivery?:string;age_seconds?:number};
export type Signal={signal_id:string;symbol:string;action:string;setup:string;status:string;reasons:string[];risk:{approved:boolean;reason:string};risk_at_execution?:{approved:boolean;reason:string};created_at:string};
export type PaperOrder={client_order_id:string;symbol:string;side:string;quantity:string;fill_price:string;fee?:string;execution_kind?:string;created_at:string};
export type PaperPosition={symbol:string;asset_class:string;units:string;cost:string;avg_price:string};
export type PaperBook={cash:string;open_cost:string;realized_pnl:string;fees_paid?:string;positions?:PaperPosition[]};
export const paper={
 session:()=>request<PaperSession>('/api/v1/paper/session'),
 quote:(s:string)=>request<Quote>(`/api/v1/paper/quote/${encodeURIComponent(s)}`),
 candles:(s:string,g:number)=>request<{candles:Candle[];source:string}>(`/api/v1/paper/candles/${encodeURIComponent(s)}?granularity=${g}`),
 orders:()=>request<{orders:PaperOrder[];book:PaperBook;kill_switch:boolean}>('/api/v1/paper/orders'),
 signals:()=>request<{signals:Signal[]}>('/api/v1/paper/signals'),
 runStrategy:(s:PaperSession)=>send<Signal>(`/api/v1/paper/signals/${encodeURIComponent(s.symbol)}?granularity=${s.granularity}`,'POST',{notional:s.notional}),
 execute:(id:string)=>send<PaperOrder>(`/api/v1/paper/signals/${id}/execute`,'POST'),
 close:(symbol:string)=>send<PaperOrder>(`/api/v1/paper/positions/${encodeURIComponent(symbol)}/close`,'POST',{client_order_id:`mob-close-${symbol}-${Date.now()}`}),
};
