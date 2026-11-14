const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const connected = {step:'DASHBOARD',status:'CONNECTED',license:{authorized:true},platform:'pocketoption'};
function session({defer=false, response={ok:true,state:connected}}={}) {
  const events={}, calls=[], updated=[]; let charts=0, callback;
  const context={window:{},document:{addEventListener:(name,cb)=>events[name]=cb},
    startFlow:()=>charts++, chrome:{runtime:{sendMessage:(msg,cb)=>{calls.push(msg); if(defer) callback=cb; else cb(response);}},
      tabs:{onUpdated:{addListener:cb=>updated.push(cb)}},storage:{local:{get:(keys,cb)=>cb({KAOSTargetTabId:42})}}}};
  vm.runInNewContext(fs.readFileSync(__dirname+'/kaos-chart-session.js','utf8'),context);
  return {calls, event:(state, brokerAttached=false)=>events['kaos-cloud-state-changed']({detail:{state,brokerAttached}}),
    update:(id,status='complete')=>updated[0](id,{status}), finish:()=>callback(response), charts:()=>charts};
}
test('restored session reconnects through the authorized background handler before showing charts',()=>{
  const c=session(); c.event(connected);
  assert.equal(c.calls[0].type,'KAOS_CONNECT_PLATFORM'); assert.equal(c.charts(),1);
  c.update(99); assert.equal(c.charts(),1);
  c.update(42); assert.equal(c.charts(),2);
  c.event(connected); assert.equal(c.calls.length,1);
  assert.ok(c.calls.every(m=>!['START_BOT','BUY','SELL'].includes(m.type)));
});
test('signed-out, unselected or unlicensed states never connect or show charts',()=>{
  const c=session();
  for(const state of [{step:'LOGIN'}, {...connected,step:'PLATFORM'}, {...connected,license:{authorized:false}}, {...connected,platform:'coinbase'}]) c.event(state);
  c.update(42); assert.equal(c.calls.length,0); assert.equal(c.charts(),0);
});
test('broker picker attachment does not open another connection',()=>{
  const c=session(); c.event(connected,true); assert.equal(c.calls.length,0); assert.equal(c.charts(),1);
});
test('connection failure never advances to charts',()=>{
  const c=session({response:{ok:false,error:'Device revoked'}}); c.event(connected); assert.equal(c.charts(),0);
});
test('sign-out invalidates an in-flight connection response',()=>{
  const c=session({defer:true}); c.event(connected); c.event({step:'LOGIN'}); c.finish(); c.update(42); assert.equal(c.charts(),0);
});
function picker(state, result) {
  const handlers={}, nodes={}, calls=[], saved={};
  function node(){return {hidden:false,textContent:'',children:[],classList:{add(){},remove(){}},replaceChildren(){this.children=[];},append(n){this.children.push(n);},addEventListener(){}};}
  const context={window:{},setInterval(){},CustomEvent:class{constructor(type,opts){this.type=type;this.detail=opts.detail;}},
    document:{getElementById:id=>nodes[id]||(nodes[id]=node()),createElement:node,querySelectorAll:()=>[],
      addEventListener:(type,cb)=>handlers[type]=cb,dispatchEvent:event=>handlers[event.type]?.(event)},
    chrome:{runtime:{sendMessage:(msg,cb)=>{calls.push(msg);cb(msg.type==='KAOS_STARTUP'?{ok:true,state}:result);}},
      storage:{local:{set:async obj=>Object.assign(saved,obj)}},tabs:{create:async()=>{throw Error('Must use authorized background connect');}}}};
  vm.runInNewContext(fs.readFileSync(__dirname+'/kaos-broker-selector.js','utf8'),context);
  return {init:()=>handlers.DOMContentLoaded(),choose:()=>context.window.KAOSBroker.choose('pocketoption'),calls,saved,nodes};
}
test('broker picker uses connection handler instead of merely opening a tab',async()=>{
  const c=picker({step:'PLATFORM'},{ok:true,state:connected}); await c.init(); await c.choose();
  assert.equal(c.calls.filter(x=>x.type==='KAOS_CONNECT_PLATFORM').length,1); assert.equal(c.saved.kaosSelectedBroker,'pocketoption');
});
test('broker picker preserves the connection error and does not select failed broker',async()=>{
  const c=picker({step:'PLATFORM'},{ok:false,error:'Chart reload failed'}); await c.init(); await c.choose();
  assert.equal(c.saved.kaosSelectedBroker,undefined); assert.equal(c.nodes['kaos-broker-status'].children[0].textContent,'Chart reload failed');
});
test('broker picker cannot connect before cloud sign-in',async()=>{
  const c=picker({step:'LOGIN'},{ok:true,state:connected}); await c.init(); await c.choose(); assert.equal(c.calls.length,1);
});
