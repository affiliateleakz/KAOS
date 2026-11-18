const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync(__dirname+'/background.js','utf8');
function attachment(reply,authorized=true){
 const begin=source.indexOf('async function kaosEnsurePoAttached('),end=source.indexOf('\nasync function kaosEnsureAnyPoAttached',begin);
 const calls=[],context={kaosAuthorizedPo:authorized,kaosIsSupportedPoUrl:()=>true,kaosAttachedTabIds:new Set(),kaosAttachAttemptAt:new Map(),setTimeout,clearTimeout,
  chrome:{tabs:{get:async()=>({url:'https://pocketoption.com/'}),sendMessage:async(id,msg)=>{calls.push(msg.type);return reply;},reload:async()=>calls.push('RELOAD')}}};
 vm.runInNewContext(source.slice(begin,end)+';globalThis.attach=kaosEnsurePoAttached;',context);
 return {calls,run:()=>context.attach(42)};
}
test('empty candle store is healthy when the real snapshot listener responds',async()=>{
 const c=attachment({ok:true,markets:[]});const result=await c.run();assert.equal(result.alreadyAttached,true);assert.deepEqual(c.calls,['GET_COMPANION_STATUS']);
});
test('companion engine readiness does not require chart snapshots',async()=>{
 const c=attachment({ok:true,engineReady:true});assert.equal((await c.run()).alreadyAttached,true);
 assert.deepEqual(c.calls,['GET_COMPANION_STATUS']);
});
test('early ping-only listener cannot masquerade as a working chart engine',async()=>{
 const c=attachment({ok:true});const result=await c.run();assert.equal(result.reloaded,true);assert.deepEqual(c.calls,['GET_COMPANION_STATUS','RELOAD']);
});
test('unapproved attachment never reloads or probes the broker',async()=>{
 const c=attachment({ok:true,markets:[]},false);assert.equal((await c.run()).reason,'KAOS_AUTH_REQUIRED');assert.deepEqual(c.calls,[]);
});
test('recent reload reports loading without reloading the broker twice',async()=>{
 const c=attachment({ok:true});await c.run();const result=await c.run();
 assert.equal(result.reason,'BROKER_LOADING');assert.ok(result.retryAfterMs>0);
 assert.equal(c.calls.filter(type=>type==='RELOAD').length,1);
});
for(const mode of ['ready','timeout','logout'])test('connection waits for real receiver: '+mode,async()=>{
 const begin=source.indexOf('async function kaosWaitForPoAttached('),end=source.indexOf('\nasync function kaosEnsureAnyPoAttached',begin);
 const attempts=[];let now=0;
 const context={kaosBrokerGeneration:1,kaosAuthorizedPo:true,Date:{now:()=>now},
  setTimeout:cb=>{now+=1000;if(mode==='logout')context.kaosAuthorizedPo=false;cb();},
  kaosEnsurePoAttached:async(id,reload)=>{attempts.push(reload);return attempts.length===1?{ok:false,reason:'BROKER_LOADING'}:mode==='ready'?{ok:true,alreadyAttached:true}:{ok:false,reason:'BROKER_LOADING'};}};
 vm.runInNewContext(source.slice(begin,end)+';globalThis.wait=kaosWaitForPoAttached;',context);
 const result=await context.wait(42);
 assert.equal(result.ok,mode==='ready');assert.ok(attempts.slice(1).every(reload=>reload===false));
 if(mode==='timeout')assert.match(result.reason,/still loading/);
 if(mode==='logout')assert.equal(result.reason,'KAOS_AUTH_REQUIRED');
});
test('audit build rejects Start Bot before any state or browser write',()=>{
 const begin=source.indexOf('chrome.runtime.onMessage.addListener('),end=source.indexOf('\nconst KAOS_PO_PATTERNS',begin);
 let listener;const botState={running:false},writes=[],context={KAOS_AUDIT_READ_ONLY:true,kaosAuthorizedPo:true,botState,
  chrome:{runtime:{onMessage:{addListener:cb=>listener=cb}},storage:{local:{set:()=>writes.push('storage')}},tabs:{reload:()=>writes.push('reload')}}};
 vm.runInNewContext(source.slice(begin,end),context);
 let response;listener({type:'START_BOT',tabId:42},{},r=>response=r);
 assert.equal(response.ok,false);assert.match(response.error,/disabled/);assert.equal(botState.running,false);assert.deepEqual(writes,[]);
});
test('trading release enables all four execution layers but retains explicit Start',()=>{
 for(const file of ['popup.js','background.js','content.js','po-bridge.js']){
  assert.match(fs.readFileSync(__dirname+'/'+file,'utf8'),/const KAOS_AUDIT_READ_ONLY = false;/);
 }
 assert.match(fs.readFileSync(__dirname+'/popup.js','utf8'),/▶ START KAOS/);
});
for(const [authorized,deadline] of [[false,null],[true,null],[true,'2000-01-01T00:00:00Z'],[true,'2999-01-01T00:00:00Z']])test('Start Bot requires broker authorization and valid deadline: '+authorized+' '+deadline,()=>{
 const begin=source.indexOf('chrome.runtime.onMessage.addListener('),end=source.indexOf('\nconst KAOS_PO_PATTERNS',begin);
 let listener;const botState={running:false},writes=[];
 const expected=authorized&&require('./kaos-membership-lease').allowed(deadline);
 const context={self:{KaosMembershipLease:require('./kaos-membership-lease')},kaosTrialExpiresAt:deadline,KAOS_AUDIT_READ_ONLY:false,kaosAuthorizedPo:authorized,botState,setTimeout(){},appendAiAudit(){},
  chrome:{runtime:{onMessage:{addListener:cb=>listener=cb}},storage:{local:{set:()=>writes.push('storage')}},
   tabs:{update:async()=>{},reload:()=>writes.push('reload')}}};
 vm.runInNewContext(source.slice(begin,end),context);
 let response;listener({type:'START_BOT',tabId:42},{},r=>response=r);
 assert.equal(response.ok,expected);assert.equal(botState.running,expected);
 assert.deepEqual(writes,expected?['storage','reload']:[]);
});
test('chart healing delegates to the worker and never directly injects page scripts',async()=>{
 const popup=fs.readFileSync(__dirname+'/popup.js','utf8'),start=popup.indexOf('async function kaosHealPoTab('),end=popup.indexOf('\nfunction kaosRenderEmptyChartState',start);
 const calls=[],context={window:{__kaosChartSessionAuthorized:true},chrome:{runtime:{sendMessage:async msg=>{calls.push(msg);return {ok:true,alreadyAttached:true};}},
  scripting:{executeScript(){assert.fail('Direct injection must not be used');}}}};
 vm.runInNewContext('let kaosHealBusy=false,kaosHealStamp=0,kaosHealNote="";'+popup.slice(start,end)+';globalThis.heal=kaosHealPoTab;',context);
 assert.equal(await context.heal({id:42}),true);assert.equal(calls[0].type,'KAOS_PO_ENSURE_ATTACH');assert.equal(calls[0].tabId,42);
});
for(const readOnly of [true,false])test('MAIN-world bridge Start/Stop and order gating, read-only='+readOnly,()=>{
 const messages=[],posted=[],frames=[];
 class Socket {constructor(){this.readyState=1;}addEventListener(){}send(data){frames.push(data);}}
 Object.assign(Socket,{CONNECTING:0,OPEN:1,CLOSING:2,CLOSED:3});
 const document={querySelector:()=>null,querySelectorAll:()=>[],addEventListener(){},dispatchEvent(){},body:{innerText:''}};
 const context={document,location:{href:'https://pocketoption.com/'},console:{log(){},warn(){},info(){}},WebSocket:Socket,
  setInterval(){},clearInterval(){},setTimeout(){},clearTimeout(){},MutationObserver:class{observe(){}disconnect(){}},
  addEventListener:(type,cb)=>{if(type==='message')messages.push(cb);},postMessage:msg=>posted.push(msg),
  getComputedStyle:()=>({display:'block',visibility:'visible',opacity:'1'})};
 context.window=context;vm.createContext(context);
 // Retain coverage of the optional read-only switch, independent of release default.
 vm.runInContext(fs.readFileSync(__dirname+'/po-bridge.js','utf8').replace('const KAOS_AUDIT_READ_ONLY = false;', 'const KAOS_AUDIT_READ_ONLY = '+readOnly+';'),context);
 vm.runInContext("globalThis.auditCommands=[{_poatCmd:true,type:'START'},{_poatCmd:true,type:'PLACE_TRADE',asset:'EURUSD',dir:'BUY',amount:10}];",context);
 if(!readOnly)vm.runInContext("auditCommands=[{_poatCmd:true,type:'PLACE_TRADE'},{_poatCmd:true,type:'START'},{_poatCmd:true,type:'STOP'},{_poatCmd:true,type:'PLACE_TRADE'}];",context);
 // Use the context's window identity, as actual same-window MessageEvents do.
 context.callbacks=messages;
 vm.runInContext('for(const data of auditCommands)for(const cb of callbacks)cb({source:window,data});',context);
 assert.equal(posted.filter(m=>m.type==='TRADE_ERROR'&&(readOnly?/disabled/:/not started/).test(m.reason)).length,2);
 if(!readOnly)assert.ok(posted.some(m=>m.type==='BRIDGE_READY'));
 const manual='42["openOrder",{"asset":"EURUSD","amount":5}]';
 const ws=vm.runInContext('new WebSocket("wss://example.invalid")',context);ws.send(manual);
 assert.deepEqual(frames,[manual]);
});

for(const [requested,plan,expected] of [[1,4,1],[2,4,2],[3,4,3],[4,4,4],[4,1,1],[4,2,2],[null,4,4],['invalid',4,1],[2.5,4,1]]) {
 test('broker scan count respects selected count '+requested+' and plan '+plan,()=>{
  const content=fs.readFileSync(__dirname+'/content.js','utf8');
  const begin=content.indexOf('  function multiScanAssets()'),end=content.indexOf('  function getActiveAssets()',begin);
  const context={botConfig:requested===null?{}:{chartCount:requested},kaosChartLimit:plan,visibleGridAssets:()=>['EURUSD','GBPUSD','USDJPY','AUDUSD','EURUSD']};
  vm.runInNewContext(content.slice(begin,end)+';globalThis.assets=multiScanAssets;',context);
  assert.equal(context.assets().length,expected);
 });
}
