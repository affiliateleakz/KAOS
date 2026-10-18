import React,{useCallback,useEffect,useState} from 'react';
import {RefreshControl,ScrollView,StyleSheet,Text,View} from 'react-native';
import {broker,brokerManagement,CoinbaseAccount,BrokerCatalogEntry,BrokerConnection,ReadOnlyBrokerData,chartSettings,ChartSettings} from '../src/api';

// Same Coinbase account data as the website and extension. Read-only: no orders are placed from the app.
function Rows({items,cols,empty}:{items:Record<string,any>[];cols:string[];empty:string}){
 if(!items.length) return <Text style={s.muted}>{empty}</Text>;
 return <View>{items.map((r,i)=><View key={i} style={s.row}>{cols.map(c=><Text key={c} style={s.cell}>{String(r[c]??'–')}</Text>)}</View>)}</View>;
}

export default function Broker(){
 const [connected,setConnected]=useState<boolean|null>(null);const [acct,setAcct]=useState<CoinbaseAccount|null>(null);const [err,setErr]=useState('');
 const load=useCallback(async()=>{try{const st=await broker.status();setConnected(st.connected);
  if(st.connected){setAcct(await broker.coinbase());}setErr('')}catch(e:any){setErr(e.message)}},[]);
 useEffect(()=>{load();const t=setInterval(load,15000);return()=>clearInterval(t)},[load]);
 return <ScrollView style={s.page} refreshControl={<RefreshControl refreshing={false} onRefresh={load} tintColor="#2F8CFF"/>}>
  <BrokerDirectory />
  <SavedCharts />
  <Text style={s.h}>Coinbase Advanced · read-only</Text><Text style={s.err}>UNVERIFIED: not yet tested against a real Coinbase account</Text>
  {err?<Text style={s.err}>Coinbase unavailable: {err}{acct?' (showing last loaded data)':''}</Text>:null}
  {connected===false&&<Text style={s.muted}>No Coinbase account connected. Connect it on tradingwithkaos.com → Broker Connections.</Text>}
  {acct&&<>
   <Text style={s.muted}>Live from Coinbase Advanced API · key {acct.key_hint} · fetched {acct.fetched_at.slice(11,19)} UTC · KAOS does not place orders on this account.</Text>
   <Text style={s.txt}>Buying power: ${acct.buying_power_usd??'–'}</Text>
   <Text style={s.sec}>Positions</Text><Rows items={acct.positions||[]} cols={['product_id','quantity','market_value','unrealized_pnl']} empty="No crypto holdings"/>
   <Text style={s.sec}>Balances</Text><Rows items={acct.balances} cols={['currency','available','hold']} empty="No non-zero balances"/>
   <Text style={s.sec}>Open orders</Text><Rows items={acct.open_orders} cols={['product_id','side','status','filled_size']} empty="No open orders"/>
   <Text style={s.sec}>Recent fills</Text><Rows items={acct.fills} cols={['product_id','side','size','price','commission']} empty="No fills yet"/>
   <Text style={s.sec}>Fees</Text><Text style={s.txt}>Tier {acct.fees.tier||'–'} · maker {acct.fees.maker_rate??'–'} · taker {acct.fees.taker_rate??'–'}</Text>
  </>}
 </ScrollView>;
}
const s=StyleSheet.create({page:{flex:1,backgroundColor:'#0a0e15',padding:14},h:{color:'#7DB8FF',fontSize:18,fontWeight:'700',marginBottom:6},
 sec:{color:'#e9c879',fontWeight:'700',marginTop:14,marginBottom:4},muted:{color:'#8b96a5',fontSize:12,marginVertical:4},txt:{color:'#d6dde6'},
 err:{color:'#f5b041',marginVertical:6},row:{flexDirection:'row',borderTopWidth:1,borderTopColor:'#1c2430',paddingVertical:4},cell:{flex:1,color:'#d6dde6',fontSize:12,fontFamily:'monospace'}});

function BrokerDirectory(){
 const [catalog,setCatalog]=useState<BrokerCatalogEntry[]>([]);
 const [connections,setConnections]=useState<BrokerConnection[]>([]);
 const [accounts,setAccounts]=useState<Record<string,ReadOnlyBrokerData>>({});
 const [error,setError]=useState('');
 const load=useCallback(async()=>{
  try {
   const [c,linked]=await Promise.all([brokerManagement.catalog(),brokerManagement.connections()]);
   setCatalog(c.brokers);setConnections(linked.connections);setError('');
   const available=linked.connections.filter(x=>x.verified&&(['alpaca','oanda'] as string[]).includes(x.broker));
   const results=await Promise.allSettled(available.map(x=>brokerManagement.account(x.broker as 'alpaca'|'oanda')));
   const next:Record<string,ReadOnlyBrokerData>={};
   results.forEach((result,i)=>{if(result.status==='fulfilled')next[available[i].broker]=result.value});
   setAccounts(next);
  }catch(e:any){setError(e?.message||'Broker directory unavailable')}
 },[]);
 useEffect(()=>{load();const t=setInterval(load,30000);return()=>clearInterval(t)},[load]);
 const saved=new Set(connections.filter(x=>x.verified).map(x=>x.broker));
 return <View style={{marginBottom:20}}>
  <Text style={s.h}>KAOS Broker Connections</Text>
  <Text style={s.muted}>Manage broker credentials through the secured KAOS website. This screen reads the same connections and account data; no live orders can be placed here.</Text>
  {error?<Text style={s.err}>{error}</Text>:null}
  {catalog.map(b=><View key={b.id} style={{borderTopColor:'#1c2430',borderTopWidth:1,paddingVertical:8}}>
   <Text style={s.txt}>{b.name} · {saved.has(b.id)?'Saved connection':b.status.replace(/_/g,' ')}</Text>
   <Text style={s.muted}>{b.asset_classes.join(', ')}</Text>
   {accounts[b.id]&&<View>
    <Text style={s.muted}>{accounts[b.id].environment.toUpperCase()} · {accounts[b.id].source} · {accounts[b.id].fetched_at}</Text>
    {Object.entries(accounts[b.id].account||{}).filter(([k])=>['cash','buying_power','equity','NAV','balance','currency','marginAvailable'].includes(k)).map(([k,v])=><Text key={k} style={s.txt}>{k}: {String(v)}</Text>)}
    <Text style={s.muted}>Positions: {accounts[b.id].positions.length} · Orders: {accounts[b.id].orders.length}</Text>
   </View>}
  </View>)}
 </View>;
}

function SavedCharts(){
 const [charts,setCharts]=useState<ChartSettings[]>([]);
 const [error,setError]=useState('');
 const load=useCallback(async()=>{try{const r=await chartSettings.load();setCharts(r.charts);setError('')}catch(e:any){setError(e?.message||'Unable to load chart settings')}},[]);
 useEffect(()=>{load()},[load]);
 return <View style={{marginBottom:18}}>
  <Text style={s.h}>Saved KAOS Charts</Text>
  <Text style={s.muted}>Synchronized settings from your KAOS account. Chart feeds and live execution may not be supported by the selected broker.</Text>
  {error?<Text style={s.err}>{error}</Text>:null}
  {charts.map(c=><Text key={c.slot} style={s.txt}>Chart {c.slot+1} · {c.broker} · {c.symbol} · {c.seconds}s</Text>)}
 </View>;
}
