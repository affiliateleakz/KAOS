import React,{useEffect,useState} from 'react';
import {Linking,Pressable,ScrollView,StyleSheet,Switch,Text,View} from 'react-native';
import {useRouter} from 'expo-router';
import {BASE,logout} from '../src/api';
import {AlertPreferences,DEFAULT_ALERTS,readAlertPreferences,saveAlertPreferences} from '../src/preferences';
const rows:{key:keyof AlertPreferences;title:string;desc:string}[]=[
 {key:'opportunities',title:'Opportunity Radar',desc:'High-priority market research'},
 {key:'news',title:'Breaking market news',desc:'Market-moving news and events'},
 {key:'social',title:'Social scanner',desc:'Unusual discussion and attention'},
 {key:'moneyFlow',title:'Follow the Money',desc:'Reported insider, institutional and wallet activity'}];
export default function Settings(){const router=useRouter();const [prefs,setPrefs]=useState(DEFAULT_ALERTS);
 useEffect(()=>{readAlertPreferences().then(setPrefs)},[]);
 async function update(key:keyof AlertPreferences,value:boolean){const p={...prefs,[key]:value};setPrefs(p);await saveAlertPreferences(p)}
 return <ScrollView style={s.page}><Text style={s.title}>Account & Alerts</Text><Text style={s.muted}>KAOS API: {BASE}</Text><Text style={s.heading}>Alert interests</Text><Text style={s.notice}>Preferences are saved on this device only. Push notifications are NOT active. KAOS must implement authenticated device registration, server-side alerts and user opt-in before delivery can begin.</Text>
 {rows.map(r=><View key={r.key} style={s.row}><View style={{flex:1,paddingRight:10}}><Text style={s.label}>{r.title}</Text><Text style={s.muted}>{r.desc}</Text></View><Switch accessibilityLabel={r.title} value={prefs[r.key]} onValueChange={v=>update(r.key,v)} trackColor={{true:'#9b7b37',false:'#353e4a'}} thumbColor="#e9c879"/></View>)}
 <Text style={s.heading}>Security</Text><Text style={s.notice}>Production Google/KAOS sign-in requires an OAuth PKCE mobile callback and audited token exchange. This build uses an already-issued KAOS token for development testing; do not distribute it as a production login.</Text>
 <Text style={s.heading}>Privacy</Text><Text style={s.notice}>Read how KAOS handles member accounts, trading data, and connected broker information.</Text>
 <Pressable accessibilityRole="link" accessibilityLabel="Read Privacy Policy" style={s.policy} onPress={()=>Linking.openURL('https://tradingwithkaos.com/privacy/').catch(()=>{})}><Text style={s.policyText}>Read Privacy Policy ↗</Text></Pressable>
 <Pressable style={s.signout} onPress={async()=>{await logout();router.replace('/')}}><Text style={s.signoutText}>Sign out of KAOS</Text></Pressable><Text style={s.footer}>Research mode only · No live order entry</Text></ScrollView>
}
const s=StyleSheet.create({page:{flex:1,backgroundColor:'#0a0e15',padding:18},title:{fontSize:26,fontWeight:'900',color:'#e9c879'},heading:{fontSize:19,color:'#fff',fontWeight:'700',marginTop:26,marginBottom:10},muted:{color:'#9ba9bd',fontSize:12,marginTop:5},notice:{color:'#c4cfde',lineHeight:21,marginTop:7},row:{backgroundColor:'#18212e',padding:14,borderRadius:10,marginTop:9,flexDirection:'row',alignItems:'center'},label:{fontSize:15,color:'#fff',fontWeight:'700'},policy:{marginTop:12,padding:14,borderColor:'#78602d',borderWidth:1,borderRadius:9,alignItems:'center'},policyText:{color:'#e9c879',fontWeight:'700'},signout:{borderColor:'#ae5555',borderWidth:1,padding:15,borderRadius:9,marginTop:23,alignItems:'center'},signoutText:{color:'#ffb3b3',fontWeight:'700'},footer:{color:'#8190a3',fontSize:11,marginTop:25,marginBottom:30}});
