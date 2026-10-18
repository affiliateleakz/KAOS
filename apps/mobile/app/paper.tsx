import React,{useCallback,useEffect,useState} from 'react';
import {Pressable,RefreshControl,ScrollView,StyleSheet,Text,View} from 'react-native';
import {paper,Candle,PaperBook,PaperOrder,PaperSession,Quote,Signal} from '../src/api';

// Same server-side paper session as the website and extension. Paper only; no broker orders.
function Chart({candles}:{candles:Candle[]}){
 const v=candles.slice(-60); if(!v.length) return <Text style={s.muted}>Loading market data…</Text>;
 const hi=Math.max(...v.map(c=>c.high)), lo=Math.min(...v.map(c=>c.low)), H=180, k=H/((hi-lo)||1);
 return <View style={s.chart} accessibilityLabel="Live candlestick chart">{v.map(c=>{const up=c.close>=c.open,col=up?'#22C55E':'#EF4444';
  return <View key={c.time} style={{flex:1,height:H,marginHorizontal:0.5}}>
   <View style={{position:'absolute',left:'45%',width:1,top:(hi-c.high)*k,height:Math.max(1,(c.high-c.low)*k),backgroundColor:col}}/>
   <View style={{position:'absolute',left:'15%',right:'15%',top:(hi-Math.max(c.open,c.close))*k,height:Math.max(1,Math.abs(c.open-c.close)*k),backgroundColor:col}}/></View>})}
  <Text style={s.axisHi}>{hi.toFixed(2)}</Text><Text style={s.axisLo}>{lo.toFixed(2)}</Text></View>;
}

export default function Paper(){
 const [ses,setSes]=useState<PaperSession|null>(null);const [q,setQ]=useState<Quote|null>(null);const [candles,setCandles]=useState<Candle[]>([]);
 const [book,setBook]=useState<PaperBook|null>(null);const [orders,setOrders]=useState<PaperOrder[]>([]);const [signals,setSignals]=useState<Signal[]>([]);
 const [err,setErr]=useState('');const [busy,setBusy]=useState(false);
 const load=useCallback(async()=>{try{const sx=await paper.session();setSes(sx);
  const [c,o,sg]=await Promise.all([paper.candles(sx.symbol,sx.granularity),paper.orders(),paper.signals()]);
  setCandles(c.candles);setBook(o.book);setOrders(o.orders);setSignals(sg.signals);setErr('')}catch(e:any){setErr(e.message)}},[]);
 useEffect(()=>{load();const t=setInterval(load,15000);return()=>clearInterval(t)},[load]);
 useEffect(()=>{if(!ses)return;const pull=()=>paper.quote(ses.symbol).then(setQ).catch(()=>setQ(null));pull();const t=setInterval(pull,5000);return()=>clearInterval(t)},[ses?.symbol]);
 async function act(fn:()=>Promise<unknown>){setBusy(true);try{await fn()}catch(e:any){setErr(e.message)}finally{setBusy(false);load()}}
 const last=signals[0];
 return <ScrollView style={s.page} refreshControl={<RefreshControl refreshing={false} onRefresh={load} tintColor="#2F8CFF"/>}>
  <Text style={s.title}>Paper Session</Text>
  <Text style={s.muted}>Same account, signals and journal as the KAOS website and Chrome extension. Simulated fills at live Coinbase quotes. No real orders.</Text>
  {!!err&&<Text style={s.err}>{err}</Text>}
  {ses&&<Text style={s.label}>{ses.symbol} · {ses.granularity/60}m · {ses.broker}</Text>}
  <Text style={s.mono}>{q?`bid ${q.bid} · ask ${q.ask} · ${q.quote_time.slice(11,19)} UTC`:'no quote'}</Text>
  <Chart candles={candles}/>
  {book&&<View style={s.row}><Text style={s.stat}>Cash ${Number(book.cash).toFixed(2)}</Text><Text style={s.stat}>Fees ${Number(book.fees_paid||0).toFixed(2)}</Text><Text style={s.stat}>P&L ${Number(book.realized_pnl).toFixed(2)}</Text></View>}
  <Pressable disabled={busy||!ses} style={s.btn} onPress={()=>ses&&act(()=>paper.runStrategy(ses))}><Text style={s.btnText}>Run KAOS Strategy</Text></Pressable>
  <Text style={s.muted}>KAOS Structure v2, unvalidated research strategy (archival audit FAIL). AI-controlled execution locked.</Text>
  {last&&<View style={s.card}><Text style={s.label}>{last.action} {last.symbol} · {last.setup} · {last.status}</Text>
   {last.reasons.map(r=><Text key={r} style={s.body}>• {r}</Text>)}
   <Text style={{color:last.risk.approved?'#7DB8FF':'#f5c26b',marginTop:6}}>Risk manager {last.risk.approved?'approved':'rejected'}: {last.risk.reason}</Text>
   {last.status==='PENDING'&&<Pressable disabled={busy} style={[s.btn,{backgroundColor:'#22C55E'}]} onPress={()=>act(()=>paper.execute(last.signal_id))}><Text style={s.btnText}>Execute paper trade at market</Text></Pressable>}</View>}
  <Text style={s.heading}>Journal</Text>
  {orders.slice(0,15).map(o=><Text key={o.client_order_id} style={s.mono}>{o.created_at.slice(5,19).replace('T',' ')} {o.side} {o.symbol} ${o.quantity} @ {o.fill_price} fee ${Number(o.fee||0).toFixed(2)} {o.execution_kind==='market_data_paper'?'market':'demo'}</Text>)}
  <View style={{height:40}}/></ScrollView>;
}
const s=StyleSheet.create({page:{flex:1,backgroundColor:'#050608',padding:16},title:{fontSize:24,fontWeight:'900',color:'#C0C7D1'},muted:{color:'#8b96a5',fontSize:12,marginTop:4},err:{color:'#ffb3b3',marginTop:8},
 label:{color:'#fff',fontWeight:'700',marginTop:10},mono:{color:'#c4cfde',fontFamily:'monospace',fontSize:11,marginTop:4},chart:{flexDirection:'row',height:180,marginTop:10,borderColor:'#1e2a36',borderWidth:1,paddingRight:56},
 axisHi:{position:'absolute',right:2,top:0,color:'#8b96a5',fontSize:10},axisLo:{position:'absolute',right:2,bottom:0,color:'#8b96a5',fontSize:10},row:{flexDirection:'row',justifyContent:'space-between',marginTop:10},stat:{color:'#fff',fontFamily:'monospace'},
 btn:{backgroundColor:'#2F8CFF',padding:13,borderRadius:8,alignItems:'center',marginTop:12},btnText:{color:'#000',fontWeight:'800'},card:{borderColor:'#1e2a36',borderWidth:1,borderRadius:8,padding:12,marginTop:10},body:{color:'#c4cfde',marginTop:3},heading:{color:'#fff',fontSize:17,fontWeight:'700',marginTop:20}});
