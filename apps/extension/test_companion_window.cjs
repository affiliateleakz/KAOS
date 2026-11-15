const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(__dirname+'/background.js','utf8');
for(const [allowed,withTab] of [[true,true],[true,false],[false,true]])test('companion resize validates sender, allowed='+allowed+', tab='+withTab,async()=>{
 const start=source.indexOf("chrome.runtime.onMessage.addListener((msg,sender,sendResponse)=>{\n  if(!msg || msg.type!=='KAOS_RESIZE_APP') return;");
 assert.ok(start>=0);const end=source.indexOf('\n});',start)+4;
 let listener;const updates=[];
 const context={chrome:{runtime:{getURL:file=>'chrome-extension://fixture/'+file,onMessage:{addListener:fn=>listener=fn}},
  storage:{local:{get:async()=>({KAOSTargetWindowId:2})}},tabs:{query:async()=>[{url:'chrome-extension://fixture/popup.html'}]},windows:{
   get:async id=>id===9?{id:9,type:'popup'}:{id:2,type:'normal',left:100,top:40,width:1400,height:900},
   getCurrent:()=>assert.fail('Never resize last-focused window'),update:async(id,dims)=>updates.push({id,...dims})}}};
 vm.runInNewContext(source.slice(start,end),context);
 const response=await new Promise(resolve=>listener({type:'KAOS_RESIZE_APP',mode:'mini',windowId:9},
  {url:allowed?'chrome-extension://fixture/popup.html?kaosApp=1':'https://pocketoption.com/',...(withTab?{tab:{windowId:9}}:{})},resolve));
 assert.equal(response.ok,allowed);
 if(allowed){assert.equal(updates.length,1);assert.equal(updates[0].id,9);assert.equal(updates[0].state,'normal');assert.equal(updates[0].width,430);assert.equal(updates[0].left,1070);assert.equal(updates[0].top,40);}
 else assert.deepEqual(updates,[]);
});
