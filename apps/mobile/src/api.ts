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
 if(response.status===403) throw new Error('Active KAOS membership required.');
 if(!response.ok) throw new Error(`KAOS API error ${response.status}`);
 return response.json() as Promise<T>;
}
export async function loadFeed(assetClass?:string):Promise<Feed>{return request<Feed>(`/api/v1/intelligence/opportunities?limit=50${assetClass?`&asset_class=${encodeURIComponent(assetClass)}`:''}`)}
export async function loadStatus(){return request<{mode:string;collector_configured:boolean;live_feeds_included:boolean;asset_classes:string[]}>('/api/v1/intelligence/status')}

export type SourceHealth={provider:string;asset_class:string;source:string;age_minutes:number;state:string;observations_in_sample:number};
export type Health={mode:string;status_meaning:string;sample_observations:number;sample_truncated:boolean;sources:SourceHealth[]};
export async function loadHealth():Promise<Health>{return request<Health>('/api/v1/intelligence/health')}
