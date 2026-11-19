const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(__dirname+'/background.js','utf8');
const section=source.slice(source.indexOf('// Coinbase session controls:'));
for(const [action,url,poRunning,expected] of [
 ['status','chrome-extension://fixture/popup.html',false,true],
 ['start','chrome-extension://fixture/popup.html?kaosApp=1',false,true],
 ['stop','chrome-extension://fixture/popup.html',false,true],
 ['orders','chrome-extension://fixture/popup.html',false,false],
 ['start','https://pocketoption.com/',false,false],
 ['start','chrome-extension://another-item/popup.html',false,false],
 ['start','chrome-extension://fixture/popup.html',true,false]
])test(`Coinbase session proxy ${action} ${url} PO=${poRunning}`,async()=>{
 let listener;const calls=[];
 const context={URL,botState:{running:poRunning},chrome:{runtime:{getURL:p=>'chrome-extension://fixture/'+p,onMessage:{addListener:fn=>listener=fn}}},
  self:{KaosCloud:{authFetch:async(path,opts)=>{calls.push({path,...opts});return{ok:true,status:200,headers:{get:()=> 'application/json'},json:async()=>({state:'fixture'})};}}}};
 vm.runInNewContext(section,context);
 const response=await new Promise(resolve=>listener({type:'KAOS_COINBASE_BOT',action,payload:{settings:{amount:17.25}}},{url},resolve));
 assert.equal(response.ok,expected);
 assert.equal(calls.length,expected?1:0);
 if(expected){assert.equal(calls[0].path,'/coinbase-bot/'+action);assert.equal(calls[0].method,action==='status'?'GET':'POST');}
});
