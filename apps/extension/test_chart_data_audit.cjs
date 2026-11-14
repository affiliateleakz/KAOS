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
 const c=attachment({ok:true,markets:[]});const result=await c.run();assert.equal(result.alreadyAttached,true);assert.deepEqual(c.calls,['GET_TERMINAL_SNAPSHOT']);
});
test('early ping-only listener cannot masquerade as a working chart engine',async()=>{
 const c=attachment({ok:true});const result=await c.run();assert.equal(result.reloaded,true);assert.deepEqual(c.calls,['GET_TERMINAL_SNAPSHOT','RELOAD']);
});
test('unapproved attachment never reloads or probes the broker',async()=>{
 const c=attachment({ok:true,markets:[]},false);assert.equal((await c.run()).reason,'KAOS_AUTH_REQUIRED');assert.deepEqual(c.calls,[]);
});
test('audit build rejects Start Bot before any state or browser write',()=>{
 const begin=source.indexOf('chrome.runtime.onMessage.addListener('),end=source.indexOf('\nconst KAOS_PO_PATTERNS',begin);
 let listener;const botState={running:false},writes=[],context={KAOS_AUDIT_READ_ONLY:true,kaosAuthorizedPo:true,botState,
  chrome:{runtime:{onMessage:{addListener:cb=>listener=cb}},storage:{local:{set:()=>writes.push('storage')}},tabs:{reload:()=>writes.push('reload')}}};
 vm.runInNewContext(source.slice(begin,end),context);
 let response;listener({type:'START_BOT',tabId:42},{},r=>response=r);
 assert.equal(response.ok,false);assert.match(response.error,/disabled/);assert.equal(botState.running,false);assert.deepEqual(writes,[]);
});
test('chart healing delegates to the worker and never directly injects page scripts',async()=>{
 const popup=fs.readFileSync(__dirname+'/popup.js','utf8'),start=popup.indexOf('async function kaosHealPoTab('),end=popup.indexOf('\nfunction kaosRenderEmptyChartState',start);
 const calls=[],context={window:{__kaosChartSessionAuthorized:true},chrome:{runtime:{sendMessage:async msg=>{calls.push(msg);return {ok:true,alreadyAttached:true};}},
  scripting:{executeScript(){assert.fail('Direct injection must not be used');}}}};
 vm.runInNewContext('let kaosHealBusy=false,kaosHealStamp=0,kaosHealNote="";'+popup.slice(start,end)+';globalThis.heal=kaosHealPoTab;',context);
 assert.equal(await context.heal({id:42}),true);assert.equal(calls[0].type,'KAOS_PO_ENSURE_ATTACH');assert.equal(calls[0].tabId,42);
});
test('MAIN-world audit bridge rejects start and order commands while preserving manual WebSocket sends',()=>{
 const messages=[],posted=[],frames=[];
 class Socket {constructor(){this.readyState=1;}addEventListener(){}send(data){frames.push(data);}}
 Object.assign(Socket,{CONNECTING:0,OPEN:1,CLOSING:2,CLOSED:3});
 const document={querySelector:()=>null,querySelectorAll:()=>[],addEventListener(){},dispatchEvent(){},body:{innerText:''}};
 const context={document,location:{href:'https://pocketoption.com/'},console:{log(){},warn(){},info(){}},WebSocket:Socket,
  setInterval(){},clearInterval(){},setTimeout(){},clearTimeout(){},MutationObserver:class{observe(){}disconnect(){}},
  addEventListener:(type,cb)=>{if(type==='message')messages.push(cb);},postMessage:msg=>posted.push(msg),
  getComputedStyle:()=>({display:'block',visibility:'visible',opacity:'1'})};
 context.window=context;vm.createContext(context);
 vm.runInContext(fs.readFileSync(__dirname+'/po-bridge.js','utf8'),context);
 vm.runInContext("globalThis.auditCommands=[{_poatCmd:true,type:'START'},{_poatCmd:true,type:'PLACE_TRADE',asset:'EURUSD',dir:'BUY',amount:10}];",context);
 // Use the context's window identity, as actual same-window MessageEvents do.
 context.callbacks=messages;
 vm.runInContext('for(const data of auditCommands)for(const cb of callbacks)cb({source:window,data});',context);
 assert.equal(posted.filter(m=>m.type==='TRADE_ERROR'&&/disabled/.test(m.reason)).length,2);
 const manual='42["openOrder",{"asset":"EURUSD","amount":5}]';
 const ws=vm.runInContext('new WebSocket("wss://example.invalid")',context);ws.send(manual);
 assert.deepEqual(frames,[manual]);
});
