import React,{useCallback,useEffect,useState} from 'react';
import {ActivityIndicator,Pressable,ScrollView,StyleSheet,Text,View} from 'react-native';
import {useFocusEffect,useRouter} from 'expo-router';
import {loadFeed,Opportunity} from '../src/api';
import {readWatchlist,toggleWatchlist,SavedAsset} from '../src/preferences';
export default function Watchlist(){
 const router=useRouter();const [saved,setSaved]=useState<SavedAsset[]>([]);const [feed,setFeed]=useState<Opportunity[]>([]);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 useFocusEffect(useCallback(()=>{let active=true;readWatchlist().then(x=>{if(active)setSaved(x)});return()=>{active=false}},[]));
 const refresh=async()=>{setBusy(true);setError('');try{const f=await loadFeed();setFeed(f.results)}catch(e){setError(e instanceof Error?e.message:String(e))}finally{setBusy(false)}};
 useEffect(()=>{refresh()},[]);
 return <ScrollView style={s.page} contentContainerStyle={{paddingBottom:40}}><Text style={s.h}>My Watchlist</Text><Text style={s.muted}>Saved locally on this device. Live opportunity coverage requires configured KAOS collectors.</Text>
 <Pressable style={s.action} onPress={refresh}><Text style={s.actionText}>Refresh market research</Text></Pressable>{busy?<ActivityIndicator color="#e9c879"/>:null}{error?<Text style={s.error}>{error}</Text>:null}
 {saved.length===0?<Text style={s.empty}>Your watchlist is empty. Open an opportunity in Radar and tap Save to watchlist.</Text>:saved.map(x=>{const item=feed.find(f=>f.asset===x.asset&&f.asset_class===x.asset_class);return <View key={`${x.asset_class}:${x.asset}`} style={s.card}><Text style={s.asset}>{x.asset}  <Text style={s.muted}>{x.asset_class.toUpperCase()}</Text></Text><Text style={s.muted}>{item?`Research priority ${item.score.toFixed(1)}/100 · ${item.bias}`:'No recent ingested research available'}</Text><View style={s.row}>{item?<Pressable onPress={()=>router.push({pathname:'/opportunity',params:{data:JSON.stringify(item)}})}><Text style={s.link}>Open research</Text></Pressable>:<Text style={s.muted}>Awaiting data</Text>}<Pressable onPress={async()=>{await toggleWatchlist(x);setSaved(await readWatchlist())}}><Text style={s.remove}>Remove</Text></Pressable></View></View>})}</ScrollView>
}
const s=StyleSheet.create({page:{flex:1,backgroundColor:'#0a0e15',padding:18},h:{fontSize:26,color:'#e9c879',fontWeight:'900'},muted:{color:'#96a4b5',fontSize:12,marginTop:7},action:{marginVertical:18,borderColor:'#82672f',borderWidth:1,padding:12,borderRadius:10,alignItems:'center'},actionText:{color:'#e9c879',fontWeight:'700'},card:{backgroundColor:'#18212e',padding:16,borderRadius:12,marginBottom:12},asset:{color:'#fff',fontWeight:'900',fontSize:19},row:{flexDirection:'row',justifyContent:'space-between',marginTop:18},link:{color:'#e9c879'},remove:{color:'#fa9b9b'},error:{color:'#fa9b9b',marginBottom:12},empty:{color:'#bdc6d3',lineHeight:22,marginTop:24}});
