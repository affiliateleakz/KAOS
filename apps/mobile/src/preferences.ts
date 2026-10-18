import * as SecureStore from 'expo-secure-store';
const WATCHLIST_KEY='kaos_mobile_watchlist_v1';
const PREFS_KEY='kaos_mobile_alert_preferences_v1';
export type SavedAsset={asset:string;asset_class:string};
export type AlertPreferences={opportunities:boolean;news:boolean;social:boolean;moneyFlow:boolean};
export const DEFAULT_ALERTS:AlertPreferences={opportunities:true,news:true,social:false,moneyFlow:false};
export async function readWatchlist():Promise<SavedAsset[]>{
 try {const raw=await SecureStore.getItemAsync(WATCHLIST_KEY); const parsed=raw?JSON.parse(raw):[];return Array.isArray(parsed)?parsed.filter(v=>typeof v?.asset==='string'&&typeof v?.asset_class==='string').slice(0,100):[];}catch{return [];}
}
export async function toggleWatchlist(asset:SavedAsset):Promise<{saved:boolean;items:SavedAsset[]}>{
 const items=await readWatchlist();const i=items.findIndex(x=>x.asset===asset.asset&&x.asset_class===asset.asset_class);
 if(i>=0)items.splice(i,1);else {if(items.length>=100)throw new Error('Watchlist limited to 100 assets on this device.');items.unshift(asset);}
 await SecureStore.setItemAsync(WATCHLIST_KEY,JSON.stringify(items));return {saved:i<0,items};
}
export async function readAlertPreferences():Promise<AlertPreferences>{
 try {const raw=await SecureStore.getItemAsync(PREFS_KEY);return raw?{...DEFAULT_ALERTS,...JSON.parse(raw)}:DEFAULT_ALERTS;}catch{return DEFAULT_ALERTS;}
}
export async function saveAlertPreferences(prefs:AlertPreferences){await SecureStore.setItemAsync(PREFS_KEY,JSON.stringify(prefs));}
