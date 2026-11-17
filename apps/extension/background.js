let kaosExpiryStorageQueue = Promise.resolve();
// Pocket Option Auto Trader — background.js v5.2.0
// KAOS cloud clients are loaded alongside the existing bot worker (broker execution untouched).
importScripts('kaos-sync-client.js', 'kaos-learning-client.js', 'kaos-cloud.js');

const KAOS_AUDIT_READ_ONLY = false;
let botState = { running: false, tabId: null, config: null };

// ── Automatic XGBoost trainer bridge ─────────────────────────────
// The MV3 worker forwards the current rolling dataset to a real Python
// XGBoost trainer through Chrome Native Messaging. The dataset is supplied
// by content.js on every labeled outcome, so worker suspension cannot erase it.
let xgbPort = null;
let xgbTraining = false;
let xgbPendingSamples = null;
let xgbPendingMode = "single";
let xgbActiveMode = "single";
let xgbLastTrainAt = 0;
let xgbLastResult = null;
let xgbLastError = null;
let xgbTrainTimer = null;
let xgbRuntimeLoaded = false;
const XGB_RUNTIME_KEY = 'KAOS_xgb_runtime';
const xgbRequesterTabs = new Set();
const xgbPendingResponses = [];
const XGB_TRAIN_DEBOUNCE_MS = 1000;
const AI_AUDIT_KEY = 'KAOS_ai_audit_log';
const AI_AUDIT_MAX = 5000;
let aiAuditWriteTimer = null;
let aiAuditBuffer = [];
async function appendAiAudit(entry) {
  try {
    aiAuditBuffer.push(entry);
    if (aiAuditWriteTimer) return;
    aiAuditWriteTimer = setTimeout(async () => {
      aiAuditWriteTimer = null;
      const d = await chrome.storage.local.get(AI_AUDIT_KEY);
      const old = Array.isArray(d[AI_AUDIT_KEY]) ? d[AI_AUDIT_KEY] : [];
      const all = old.concat(aiAuditBuffer.splice(0));
      await chrome.storage.local.set({[AI_AUDIT_KEY]:all.slice(-AI_AUDIT_MAX)});
    }, 250);
  } catch (_) {}
}



// V24.1 XGB diagnostics: never leave the UI silently stuck in COLLECTING.
function reportXGBHostError(err) {
  const msg = String(err && (err.message || err) || "Native host disconnected");
  appendAiAudit({ts:Date.now(),event:'XGB_NATIVE_HOST_ERROR',error:msg});
  const targets = new Set(xgbRequesterTabs);
  if (botState.tabId != null) targets.add(botState.tabId);
  for (const id of targets) {
    try {
      chrome.tabs.sendMessage(id, {
        type: "XGB_NATIVE_HOST_ERROR",
        error: msg,
        timestamp: Date.now()
      }, () => { void chrome.runtime.lastError; });
    } catch (_) {}
  }
}

async function loadXgbRuntime() {
  try {
    const d = await chrome.storage.local.get(XGB_RUNTIME_KEY);
    const r = d && d[XGB_RUNTIME_KEY];
    if (r && typeof r === 'object') {
      xgbLastResult = r.result || null;
      xgbLastError = r.error || null;
      xgbLastTrainAt = Number(r.lastTrainAt || 0);
    }
    xgbRuntimeLoaded = true;
  } catch (_) { xgbRuntimeLoaded = true; }
}
function persistXgbRuntime(extra={}) {
  try {
    chrome.storage.local.set({[XGB_RUNTIME_KEY]: {
      result: xgbLastResult, error: xgbLastError, training: xgbTraining,
      lastTrainAt: xgbLastTrainAt, updatedAt: Date.now(), ...extra
    }});
  } catch (_) {}
}
loadXgbRuntime();

function finishXgbTraining(msg) {
  xgbTraining = false;
  xgbLastTrainAt = Date.now();
  xgbLastResult = msg || null;
  if((xgbActiveMode==='multi'||xgbActiveMode==='specialist') && msg?.models){
    appendAiAudit({ts:Date.now(),event:'XGB_MULTI_EXPIRY_EVALUATED',horizons:msg.horizonsEvaluated,results:Object.fromEntries(Object.entries(msg.models).map(([k,v])=>[k,{status:v.status,report:v.report}]))});
  }
  xgbLastError = (msg && msg.error) ? String(msg.error) : null;
  appendAiAudit({ts:Date.now(),event:msg?.ok?'XGB_TRAIN_RESULT':'XGB_TRAIN_ERROR',result:msg?.ok?'ok':'error',samples:msg?.report?.samples||0,error:msg?.error||null});
  if (xgbTrainTimer) { clearTimeout(xgbTrainTimer); xgbTrainTimer = null; }
  persistXgbRuntime();
  while (xgbPendingResponses.length) { try { xgbPendingResponses.shift()(msg || {ok:false,status:'error',error:'Empty XGB result'}); } catch (_) {} }
  const targets = new Set();
  if (botState.tabId != null) targets.add(botState.tabId);
  for (const id of xgbRequesterTabs) targets.add(id);
  xgbRequesterTabs.clear();
  for (const id of targets) {
    try { chrome.tabs.sendMessage(id, {type:xgbActiveMode==='multi'?'XGB_MULTI_EXPIRY_RESULT':'XGB_MODEL_UPDATE', payload:msg}).catch(()=>{}); } catch (_) {}
  }
}

function xgbConnect() {
  if (xgbPort) return xgbPort;
  try {
    xgbPort = chrome.runtime.connectNative('com.kaos.aidata');
    xgbPort.onMessage.addListener((msg) => {
      finishXgbTraining(msg);
      if (xgbPendingSamples && xgbPendingSamples.length) {
        const next=xgbPendingSamples; xgbPendingSamples=null; setTimeout(()=>xgbTrain(next, xgbPendingMode),250);
      }
    });
    xgbPort.onDisconnect.addListener(() => {
      const le = chrome.runtime.lastError;
      const msg = le && le.message ? le.message : 'Native XGBoost host disconnected.';
      xgbPort=null; xgbTraining=false;
      xgbLastError = msg;
      xgbLastResult = {ok:false,status:'error',error:msg};
      persistXgbRuntime();
      while (xgbPendingResponses.length) { try { xgbPendingResponses.shift()(xgbLastResult); } catch (_) {} }
      reportXGBHostError({message:msg});
    });
  } catch(e) {
    xgbPort=null; xgbTraining=false;
    xgbLastError=String(e && (e.message || e) || 'Native XGBoost connection failed');
    xgbLastResult={ok:false,status:'error',error:xgbLastError};
    persistXgbRuntime();
    while (xgbPendingResponses.length) { try { xgbPendingResponses.shift()({ok:false,status:'error',error:xgbLastError}); } catch (_) {} }
    reportXGBHostError(e);
  }
  return xgbPort;
}
function xgbTrain(samples, mode="single") {
  if (!Array.isArray(samples) || !samples.length) return;
  if (xgbTraining) { xgbPendingSamples=samples.slice(); xgbPendingMode=mode; return; }
  if (Date.now()-xgbLastTrainAt < XGB_TRAIN_DEBOUNCE_MS) { xgbPendingSamples=samples.slice(); xgbPendingMode=mode; setTimeout(()=>{ if(xgbPendingSamples&&!xgbTraining){const next=xgbPendingSamples;xgbPendingSamples=null;xgbTrain(next,xgbPendingMode);}},XGB_TRAIN_DEBOUNCE_MS); return; }
  const port=xgbConnect(); if(!port) return;
  xgbTraining=true;
  xgbActiveMode=mode;
  xgbLastError=null;
  persistXgbRuntime({samples: samples.length});
  if (xgbTrainTimer) clearTimeout(xgbTrainTimer);
  xgbTrainTimer = setTimeout(() => {
    if (!xgbTraining) return;
    xgbTraining=false;
    xgbLastError='XGBoost trainer timed out without returning a result.';
    xgbLastResult={ok:false,status:'error',error:xgbLastError};
    persistXgbRuntime();
    while (xgbPendingResponses.length) { try { xgbPendingResponses.shift()({ok:false,status:'error',error:xgbLastError}); } catch (_) {} }
    reportXGBHostError({message:xgbLastError});
    try { if (xgbPort) xgbPort.disconnect(); } catch (_) {}
    xgbPort=null;
  }, 90000);
  try {
    // 1.6.48: preserve the complete canonical vector. The bundled native host
    // accepts all 104 features; no silent 88-feature truncation.
    const wireSamples=(mode==='multi'||mode==='specialist'?samples:samples.slice(-1200)).filter(r=>r && Array.isArray(r.x) && r.x.length===104);
    port.postMessage({type:mode==='specialist'?'train_specialists':mode==='multi'?'train_multi_expiry':'train_xgboost',samples:wireSamples,targetHorizonMs:30000,now:Date.now(),sourceFeatures:104,wireFeatures:104});
  }
  catch(e){xgbTraining=false;xgbPort=null;xgbLastError=e.message||String(e);persistXgbRuntime();reportXGBHostError(e);setTimeout(()=>xgbTrain(samples,mode),2000);}
}



// ═══════════════════════════════════════════════════════════════════
// V219 LIVE VISUAL/VIDEO FEATURE STREAM — RAM ONLY
// Captures the visible Pocket Option tab every 3s, splits the 4-chart grid into
// quadrants, extracts compact pixel/motion measurements, and keeps only rolling
// numeric history (max 10 minutes). No screenshots/video are written to disk.
// ═══════════════════════════════════════════════════════════════════
let v219VisionTimer=null, v219VisionTabId=null, v219VisionAssets=[];
const v219VisionHistory=new Map();
const v219PrevGray=new Map();
const V219_CAPTURE_MS=3000, V219_MAX_MS=10*60*1000;

function v219Stats(gray,w,h,prev){
  const n=gray.length||1;
  let sum=0,sum2=0,bright=0,dark=0,ex=0,ey=0,diff=0;
  let motionL=0,motionR=0,motionT=0,motionB=0,mln=0,mrn=0,mtn=0,mbn=0;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    const i=y*w+x,g=gray[i]; sum+=g;sum2+=g*g;if(g>.72)bright++;if(g<.22)dark++;
    if(x){ex+=Math.abs(g-gray[i-1]);}
    if(y){ey+=Math.abs(g-gray[i-w]);}
    if(prev&&prev.length===gray.length){
      const d=Math.abs(g-prev[i]);diff+=d;
      if(x<w/2){motionL+=d;mln++;}else{motionR+=d;mrn++;}
      if(y<h/2){motionT+=d;mtn++;}else{motionB+=d;mbn++;}
    }
  }
  const mean=sum/n, sd=Math.sqrt(Math.max(0,sum2/n-mean*mean));
  return [mean*2-1,Math.min(1,sd*4)*2-1,Math.min(1,ex/Math.max(1,n-w)*5)*2-1,Math.min(1,ey/Math.max(1,n-h)*5)*2-1,
    bright/n*2-1,dark/n*2-1,Math.min(1,diff/n*8)*2-1,
    Math.min(1,motionL/Math.max(1,mln)*8)*2-1,Math.min(1,motionR/Math.max(1,mrn)*8)*2-1,
    Math.min(1,motionT/Math.max(1,mtn)*8)*2-1,Math.min(1,motionB/Math.max(1,mbn)*8)*2-1];
}
function v219Aggregate(asset,raw,now){
  let h=v219VisionHistory.get(asset); if(!h){h=[];v219VisionHistory.set(asset,h);}
  h.push({t:now,f:raw}); while(h.length&&now-h[0].t>V219_MAX_MS)h.shift();
  const avg=(sec,k)=>{const a=h.filter(q=>now-q.t<=sec*1000);return a.length?a.reduce((z,q)=>z+Number(q.f[k]||0),0)/a.length:0;};
  // 16 learned visual features: current appearance/motion + short/medium/10m temporal summaries.
  const f=[
    raw[0],raw[1],raw[2],raw[3],raw[4],raw[5],raw[6],
    raw[7]-raw[8],raw[9]-raw[10],
    avg(30,6),avg(120,6),avg(600,6),
    avg(30,3)-avg(30,2),avg(120,3)-avg(120,2),
    avg(30,7)-avg(30,8),avg(120,9)-avg(120,10)
  ].map(x=>Math.max(-1,Math.min(1,Number(x)||0)));
  return {features:f,frames:h.length,windowSec:h.length?Math.min(600,(now-h[0].t)/1000):0};
}
async function v219Capture(){
  if(!botState.running||!v219VisionTabId||!v219VisionAssets.length)return;
  try{
    const tab=await chrome.tabs.get(v219VisionTabId);
    if(!tab||!tab.active)return; // captureVisibleTab only uses the visible active tab
    const dataUrl=await chrome.tabs.captureVisibleTab(tab.windowId,{format:'jpeg',quality:45});
    const blob=await (await fetch(dataUrl)).blob();
    const bmp=await createImageBitmap(blob);
    // Exclude top/bottom platform chrome; split central trading area as 2x2 grid.
    const sx=Math.floor(bmp.width*.10), sy=Math.floor(bmp.height*.12);
    const sw=Math.floor(bmp.width*.82), sh=Math.floor(bmp.height*.78);
    const cw=Math.floor(sw/2), ch=Math.floor(sh/2);
    const now=Date.now();
    for(let slot=0;slot<Math.min(4,v219VisionAssets.length);slot++){
      const asset=v219VisionAssets[slot]; if(!asset)continue;
      const col=slot%2,row=Math.floor(slot/2);
      const canvas=new OffscreenCanvas(64,36),ctx=canvas.getContext('2d',{willReadFrequently:true});
      ctx.drawImage(bmp,sx+col*cw,sy+row*ch,cw,ch,0,0,64,36);
      const px=ctx.getImageData(0,0,64,36).data, gray=new Float32Array(64*36);
      for(let i=0,j=0;i<px.length;i+=4,j++)gray[j]=(px[i]*.299+px[i+1]*.587+px[i+2]*.114)/255;
      const prev=v219PrevGray.get(asset)||null,raw=v219Stats(gray,64,36,prev);v219PrevGray.set(asset,gray);
      const agg=v219Aggregate(asset,raw,now);
      try{chrome.tabs.sendMessage(v219VisionTabId,{type:'V219_VISUAL_FEATURES',asset,features:agg.features,frames:agg.frames,windowSec:agg.windowSec,at:now}).catch(()=>{});}catch(_){}
    }
    bmp.close();
  }catch(e){appendAiAudit({ts:Date.now(),event:'V219_VISION_CAPTURE_ERROR',error:String(e?.message||e)});}
}
function v219Start(tabId){
  v219VisionTabId=Number(tabId||botState.tabId||0)||null;
  v219VisionHistory.clear();v219PrevGray.clear();
  if(v219VisionTimer)clearInterval(v219VisionTimer);
  v219VisionTimer=setInterval(v219Capture,V219_CAPTURE_MS);
  setTimeout(v219Capture,500);
}
function v219Stop(){
  if(v219VisionTimer)clearInterval(v219VisionTimer);v219VisionTimer=null;
  v219VisionHistory.clear();v219PrevGray.clear();v219VisionAssets=[];
}

chrome.runtime.onStartup.addListener(() => {
  // Registrations are non-persistent; signed-out browser startups never hook broker traffic.
  kaosAuthorizedPo = false;
  botState = { running: false, tabId: null, config: null };
  chrome.storage.local.set({ botRunning: false });
});

chrome.runtime.onInstalled.addListener(() => {
  kaosAuthorizedPo = false;
  botState = { running: false, tabId: null, config: null };
  chrome.storage.local.set({ botRunning: false });
});

chrome.alarms.create('keepAlive', { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name !== 'keepAlive') return;
  if (!botState.running || !botState.tabId) return;
  chrome.tabs.sendMessage(botState.tabId, { type: 'PING' }, (resp) => {
    if (chrome.runtime.lastError || !resp) {
      // content.js is declared in manifest.json and is injected automatically.
      // Never execute it a second time: top-level const declarations would collide.
      return;
    }
    // Refresh broker-backed 5s history while the Pocket Option tab is backgrounded.
    // If the live page/WebSocket is throttled, this repairs the missing interval
    // from real history instead of inventing candles.
    try { chrome.tabs.sendMessage(botState.tabId, {type:'BACKGROUND_HISTORY_SYNC'}, ()=>void chrome.runtime.lastError); } catch (_) {}
  });
});



// KAOS 1.6.9 — one app instance only.
// Never leave KAOS running as both a normal browser tab and an extension window.
let KAOS_APP_OPEN_PROMISE=null;
async function kaosOpenSingleAppWindow(){
  if(KAOS_APP_OPEN_PROMISE) return KAOS_APP_OPEN_PROMISE;
  KAOS_APP_OPEN_PROMISE=(async()=>{
  const appUrl=chrome.runtime.getURL('popup.html');
  const ownTabs=await chrome.tabs.query({});
  const kaosTabs=ownTabs.filter(t=>String(t.url||'').startsWith(appUrl));
  let appWin=null;

  // Reuse an existing popup/app window if present.
  for(const t of kaosTabs){
    try{
      const w=await chrome.windows.get(t.windowId);
      if(w && w.type==='popup'){appWin={tab:t,win:w};break;}
    }catch(_){}
  }
  if(appWin){
    // Remove duplicate KAOS tabs/windows, preserve the chosen app window.
    for(const t of kaosTabs){
      if(t.id!==appWin.tab.id) try{await chrome.tabs.remove(t.id);}catch(_){}
    }
    await chrome.windows.update(appWin.win.id,{focused:true});
    return {ok:true,reused:true,windowId:appWin.win.id};
  }

  // If KAOS exists in a normal Chrome tab, close it before creating the app window.
  for(const t of kaosTabs) try{await chrome.tabs.remove(t.id);}catch(_){}

  const w=await chrome.windows.create({
    url:appUrl+'?kaosApp=1',type:'popup',focused:true,width:430,height:800
  });
  return {ok:true,created:true,windowId:w.id};
  })();
  try { return await KAOS_APP_OPEN_PROMISE; }
  finally { KAOS_APP_OPEN_PROMISE=null; }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // KAOS_* messages are owned by the dedicated KAOS cloud listener below — ignore here so the
  // existing bot handler never hijacks their sendResponse channel.
  if (msg && typeof msg.type === 'string' && msg.type.indexOf('KAOS_') === 0 &&
      !['KAOS_EXPIRY_LABEL_BATCH','KAOS_EXPIRY_TRAIN_COLLECTED','KAOS_TRAIN_SPECIALISTS'].includes(msg.type)) return false;
  if (msg.type === 'START_BOT') {
    if (KAOS_AUDIT_READ_ONLY) { sendResponse({ok:false,error:'Trading is disabled during the release audit; chart data remains available'}); return false; }
    if (!kaosAuthorizedPo) { sendResponse({ok:false,error:'KAOS sign-in and broker connection required'}); return false; }
    botState.running = true;
    botState.tabId   = msg.tabId;
    botState.config  = msg;
    chrome.storage.local.set({ botRunning: true });
    // Keep the trading tab resident when Chrome is under memory pressure.
    try { chrome.tabs.update(msg.tabId, {autoDiscardable:false}).catch(()=>{}); } catch (_) {}

    // KAOS 1.6.8: user should never have to press browser Refresh manually.
    // A real Pocket Option reload guarantees the MAIN-world po-bridge is installed
    // at document_start. The onUpdated handler below restores this START_BOT config
    // automatically once the refreshed broker page is complete.
    chrome.tabs.reload(msg.tabId, {bypassCache:false}, () => {
      if (chrome.runtime.lastError) {
        // Reload can fail transiently; fall back to the existing live page.
        try { chrome.tabs.sendMessage(msg.tabId, msg).catch(()=>{}); } catch (_) {}
      }
    });
    setTimeout(() => {
      if (xgbLastResult?.ok && xgbLastResult.model) {
        try { chrome.tabs.sendMessage(msg.tabId, {type:'XGB_MODEL_UPDATE', payload:xgbLastResult}).catch(()=>{}); } catch (_) {}
      }
    }, 800);
    appendAiAudit({ts:Date.now(),event:'BOT_START',tabId:msg.tabId});
    sendResponse({ ok: true });
    return true;
  }

  if (msg.type === 'STOP_BOT') {
    v219Stop();
    botState.running = false;
    botState.config  = null;
    chrome.storage.local.set({ botRunning: false });
    if (botState.tabId) {
      chrome.tabs.sendMessage(botState.tabId, { type: 'STOP_BOT' }).catch(() => {});
    }
    sendResponse({ ok: true });
    return true;
  }


  if (msg.type === 'V219_VISION_START') {
    v219Start(msg.tabId||sender?.tab?.id||botState.tabId); sendResponse({ok:true}); return true;
  }
  if (msg.type === 'V219_VISION_STOP') {
    v219Stop(); sendResponse({ok:true}); return true;
  }
  if (msg.type === 'V219_VISION_GRID_ASSETS') {
    v219VisionAssets=(Array.isArray(msg.assets)?msg.assets:[]).map(String).filter(Boolean).slice(0,4);
    sendResponse({ok:true,assets:v219VisionAssets}); return true;
  }

  if (msg.type === 'AI_EVENT_LOG') {
    appendAiAudit(msg.entry || {ts:Date.now(),event:'AI_EVENT'});
    sendResponse({ok:true});
    return true;
  }

  if (msg.type === 'GET_AI_AUDIT_LOG') {
    (async()=>{ const d=await chrome.storage.local.get(AI_AUDIT_KEY); sendResponse({ok:true,events:Array.isArray(d[AI_AUDIT_KEY])?d[AI_AUDIT_KEY].slice(-Math.min(AI_AUDIT_MAX,Number(msg.limit||1000))):[]}); })();
    return true;
  }

  if (msg.type === 'RESET_XGB_FRESH') {
    try {
      if (xgbTrainTimer) { clearTimeout(xgbTrainTimer); xgbTrainTimer=null; }
      try { if (xgbPort) xgbPort.disconnect(); } catch (_) {}
      xgbPort=null; xgbTraining=false; xgbPendingSamples=null; xgbLastTrainAt=0;
      xgbLastResult=null; xgbLastError=null; xgbRuntimeLoaded=true;
      xgbRequesterTabs.clear();
      chrome.storage.local.remove(XGB_RUNTIME_KEY);
      chrome.storage.local.remove(AI_AUDIT_KEY);
      appendAiAudit({ts:Date.now(),event:'AI_FRESH_RESET',scope:'XGBOOST_RUNTIME_AND_AUDIT'});
      sendResponse({ok:true});
    } catch(e) {
      sendResponse({ok:false,error:e.message||String(e)});
    }
    return true;
  }

  if (msg.type === 'XGB_TRAIN_NOW') {
    if (!Array.isArray(msg.samples)) { sendResponse({ok:false,error:'Invalid XGBoost dataset'}); return true; }
    if (sender && sender.tab && sender.tab.id != null) xgbRequesterTabs.add(sender.tab.id);
    xgbLastResult = null;
    xgbLastError = null;
    persistXgbRuntime({samples:Math.min(msg.samples.length,1200),training:true});
    xgbPendingResponses.push(sendResponse);
    xgbTrain(msg.samples.slice(-1200));
    // If the native host could not be connected, xgbConnect/xgbTrain records
    // the concrete error but there may be no asynchronous callback. Resolve
    // the popup request immediately from the stored error instead of leaving
    // the import request hanging.
    if (!xgbPort && xgbLastError) {
      const err={ok:false,status:'error',error:xgbLastError};
      while (xgbPendingResponses.length) { try { xgbPendingResponses.shift()(err); } catch (_) {} }
    }
    return true;
  }

  if (msg.type === 'KAOS_EXPIRY_LABEL_BATCH') {
    // Serialize read-modify-write operations: concurrent ticks previously lost
    // observations and acknowledged success before storage completed.
    const allowed=new Set([5000,10000,15000,20000,25000,30000,60000]);
    const rows=(Array.isArray(msg.samples)?msg.samples:[]).filter(r=>r &&
      typeof r.asset==='string' && r.asset.length>0 &&
      Array.isArray(r.x)&&r.x.length===104&&r.x.every(Number.isFinite)&&
      (r.label===0||r.label===1)&&allowed.has(r.targetHorizonMs)&&
      Number.isFinite(r.t)&&Number.isFinite(r.settlementTs)&&
      Number.isFinite(r.entryPrice)&&r.entryPrice>0&&
      Number.isFinite(r.exitPrice)&&r.exitPrice>0&&
      r.label===(r.exitPrice>r.entryPrice?1:0)&&r.exitPrice!==r.entryPrice&&
      (r.specialist==null||['REVERSAL','RUNNER','BREAKOUT'].includes(r.specialist))&&
      r.settlementTs>=r.t+r.targetHorizonMs&&r.settlementTs<=r.t+r.targetHorizonMs+2000);
    const job=kaosExpiryStorageQueue.then(async()=>{
      const v=await chrome.storage.local.get(['kaosExpiryLabels']);
      const all=Array.isArray(v.kaosExpiryLabels)?v.kaosExpiryLabels:[];
      const keys=new Set(all.map(r=>r.asset+':'+r.t+':'+r.targetHorizonMs));
      let added=0;
      for(const r of rows){const k=r.asset+':'+r.t+':'+r.targetHorizonMs;
        if(!keys.has(k)){all.push(r);keys.add(k);added++;}}
      const horizons=[5000,10000,15000,20000,25000,30000,60000];
      const kept=horizons.flatMap(h=>all.filter(r=>r.targetHorizonMs===h).slice(-1200));
      await chrome.storage.local.set({kaosExpiryLabels:kept});
      return {ok:true,received:Array.isArray(msg.samples)?msg.samples.length:0,valid:rows.length,added,stored:kept.length,
        perExpiryCounts:Object.fromEntries(horizons.map(h=>[String(h),kept.filter(r=>r.targetHorizonMs===h).length]))};
    });
    kaosExpiryStorageQueue=job.catch(()=>{});
    job.then(sendResponse).catch(e=>sendResponse({ok:false,error:'Expiry storage failed: '+String(e)}));
    return true;
  }
  if (msg.type === 'KAOS_EXPIRY_TRAIN_COLLECTED') {
    kaosExpiryStorageQueue.then(()=>chrome.storage.local.get(['kaosExpiryLabels'])).then(v=>{
      const rows=Array.isArray(v.kaosExpiryLabels)?v.kaosExpiryLabels:[];
      const counts=Object.fromEntries([5000,10000,15000,20000,25000,30000,60000].map(h=>[String(h),rows.filter(r=>r.targetHorizonMs===h).length]));
      if(!Object.values(counts).some(n=>n>=1000)){
        sendResponse({ok:false,status:'warming',samples:rows.length,perExpiryCounts:counts,message:'Need approximately 1,000 observations per expiration for a 200-example holdout.'});return;
      }
      xgbPendingResponses.push(sendResponse);
      xgbTrain(rows,'multi');
    }).catch(e=>sendResponse({ok:false,error:String(e)}));
    return true;
  }
  if (msg.type === 'KAOS_TRAIN_SPECIALISTS') {
    kaosExpiryStorageQueue.then(()=>chrome.storage.local.get(['kaosExpiryLabels'])).then(v=>{
      const rows=(Array.isArray(v.kaosExpiryLabels)?v.kaosExpiryLabels:[])
        .filter(r=>['REVERSAL','RUNNER','BREAKOUT'].includes(r.specialist));
      const counts={};for(const r of rows){const k=r.specialist+':'+r.targetHorizonMs;counts[k]=(counts[k]||0)+1;}
      if(!Object.values(counts).some(n=>n>=1000)){
        sendResponse({ok:false,status:'warming',perSpecialistCounts:counts,
          message:'Need at least 1,000 correctly classified samples for one specialist/expiry; unknown setups excluded.'});return;
      }
      xgbPendingResponses.push(sendResponse);
      xgbTrain(rows,'specialist');
    }).catch(e=>sendResponse({ok:false,error:String(e)}));
    return true;
  }
  if (msg.type === 'XGB_TRAIN_MULTI_EXPIRY') {
    const allowed = new Set([5000,10000,15000,20000,25000,30000,60000]);
    if (!Array.isArray(msg.samples)) { sendResponse({ok:false,error:'Expected labeled multi-expiry samples'}); return true; }
    const rows=msg.samples.filter(r=>r && Array.isArray(r.x) && r.x.length===104 &&
      (r.label===0 || r.label===1) && allowed.has(Number(r.targetHorizonMs)) &&
      Number.isFinite(Number(r.t)) && String(r.asset||'').length>0);
    if (!rows.length) { sendResponse({ok:false,status:'warming',error:'No verified expiration-specific labeled observations. A 30s label cannot be reused for other expirations.'}); return true; }
    if (sender?.tab?.id!=null) xgbRequesterTabs.add(sender.tab.id);
    xgbPendingResponses.push(sendResponse);
    xgbTrain(rows,'multi');
    if (!xgbPort && xgbLastError) {
      const err={ok:false,status:'error',error:xgbLastError};
      while(xgbPendingResponses.length){try{xgbPendingResponses.shift()(err);}catch(_){}}
    }
    return true;
  }

  if (msg.type === 'GET_XGB_STATUS') {
    (async () => {
      if (!xgbRuntimeLoaded) await loadXgbRuntime();
      const r = xgbLastResult || {};
      sendResponse({
        ok: true,
        training: xgbTraining,
        result: r,
        error: xgbLastError,
        hasResult: !!(r && r.ok),
        lastTrainAt: xgbLastTrainAt
      });
    })();
    return true;
  }

  if (msg.type === 'GET_BOT_STATE') {
    sendResponse({ running: botState.running });
    return true;
  }

  if (msg.type === 'TRADE_RESULT' || msg.type === 'BOT_STATUS' || msg.type === 'BOT_STOPPED') {
    chrome.runtime.sendMessage(msg).catch(() => {});
    sendResponse({ ok: true });
    return true;
  }

  // ── AI Full Backup Export (v19.0.2) ──
  // Content script can't call chrome.downloads directly in MV3;
  // it sends the full backup blob here for download.
  if (msg.type === 'EXPORT_AI_BACKUP' && msg.payload && msg.manual === true) {
    const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const json = JSON.stringify(msg.payload, null, 2);
    const dataUrl = 'data:application/json;base64,' + btoa(unescape(encodeURIComponent(json)));
    
    // Write both a timestamped version and a "latest" version
    const files = [
      `KAOS_backup_v19_${ts}.json`,
      'KAOS_backup_v19_latest.json'
    ];
    let done = 0;
    files.forEach(fn => {
      chrome.downloads.download({ url: dataUrl, filename: 'AIData/' + fn, saveAs: false, conflictAction: 'overwrite' }, () => {
        if (++done === files.length) {
          sendResponse({ ok: true, filename: 'AIData/' + files[0] });
        }
      });
    });
    return true;
  }

  sendResponse({ ok: true });
  return true;
});


// KAOS broker isolation: no Pocket Option page scripts are registered at install.
// A member must authenticate and explicitly connect to Pocket Option first.
const KAOS_PO_PATTERNS = [
  'https://pocketoption.com/*', 'https://*.pocketoption.com/*',
  'https://platform58.po2.capital/*', 'https://p.finance/*',
  'https://po.company/*', 'https://po1.capital/*', 'https://pocket-link22.co/*'
];
const KAOS_PO_BRIDGE_SCRIPT = 'kaos-authorized-po-bridge';
const KAOS_PO_ENGINE_SCRIPT = 'kaos-authorized-po-engine';
const KAOS_PO_SCRIPT_IDS = [KAOS_PO_BRIDGE_SCRIPT, KAOS_PO_ENGINE_SCRIPT];
let kaosAuthorizedPo = false;
let kaosBrokerGeneration = 0;
const kaosAttachedTabIds = new Set();
const kaosAttachAttemptAt = new Map();

async function kaosStopBrokerIntegration() {
  kaosBrokerGeneration++;
  kaosAuthorizedPo = false;
  botState.running = false;
  botState.config = null;
  await chrome.storage.local.set({botRunning:false, kaosPoAttached:false});
  const existing = await chrome.scripting.getRegisteredContentScripts({ids:KAOS_PO_SCRIPT_IDS});
  if (existing.length) await chrome.scripting.unregisterContentScripts({ids:existing.map(s=>s.id)});
  // A MAIN-world wrapper persists until the document is unloaded. Reload only
  // documents to which KAOS attached, restoring the broker's native WebSocket.
  const tabs = [...kaosAttachedTabIds];
  kaosAttachedTabIds.clear();
  kaosAttachAttemptAt.clear();
  for(const id of tabs) {
    try { await chrome.tabs.reload(id, {bypassCache:false}); } catch (_) {}
  }
}

async function kaosPermitBrokerIntegration() {
  const generation = kaosBrokerGeneration;
  const state = await self.KaosCloud.startup();
  if (generation !== kaosBrokerGeneration) throw new Error('KAOS session changed during broker connection');
  const broker = String(state.platform || '').toLowerCase();
  if (state.step !== 'DASHBOARD' || state.status !== 'CONNECTED' ||
      !state.license?.authorized ||
      (broker !== 'pocketoption' && broker !== 'pocket_option')) {
    throw new Error('Sign in to KAOS and select Pocket Option before attaching broker scripts');
  }
  const existing = await chrome.scripting.getRegisteredContentScripts({ids:KAOS_PO_SCRIPT_IDS});
  if (generation !== kaosBrokerGeneration) throw new Error('KAOS session changed during broker connection');
  if (existing.length) await chrome.scripting.unregisterContentScripts({ids:existing.map(x=>x.id)});
  if (generation !== kaosBrokerGeneration) throw new Error('KAOS session changed during broker connection');
  await chrome.scripting.registerContentScripts([
    {id:KAOS_PO_BRIDGE_SCRIPT, matches:KAOS_PO_PATTERNS,
     js:['po-bridge.js'], runAt:'document_start', world:'MAIN', persistAcrossSessions:false},
    {id:KAOS_PO_ENGINE_SCRIPT, matches:KAOS_PO_PATTERNS,
     js:['candidate7b_strategy.js','kaos_expiry_collector.js','content.js','kaos-cloud-ui.js'],
     css:['kaos-cloud-ui.css'], runAt:'document_idle', world:'ISOLATED', persistAcrossSessions:false}
  ]);
  if (generation !== kaosBrokerGeneration) {
    await chrome.scripting.unregisterContentScripts({ids:KAOS_PO_SCRIPT_IDS});
    throw new Error('KAOS session changed during broker connection');
  }
  kaosAuthorizedPo = true;
  return state;
}

async function kaosEnsurePoAttached(tabId, allowReload = true) {
  if(!tabId) return {ok:false,reason:'NO_TAB'};
  if(!kaosAuthorizedPo) return {ok:false,reason:'KAOS_AUTH_REQUIRED'};
  const tab = await chrome.tabs.get(tabId);
  if(!kaosIsSupportedPoUrl(tab.url))return {ok:false,reason:'NOT_POCKET_OPTION'};
  try{
    const pong=await new Promise(resolve=>{
      const timer=setTimeout(()=>resolve(null),2000);
      chrome.tabs.sendMessage(tabId,{type:'GET_COMPANION_STATUS'}).then(
        response=>{clearTimeout(timer);resolve(response);},()=>{clearTimeout(timer);resolve(null);});
    });
    if(!kaosAuthorizedPo)return {ok:false,reason:'KAOS_AUTH_REQUIRED'};
    if(pong?.ok&&(pong.engineReady===true||Array.isArray(pong.markets))){kaosAttachedTabIds.add(tabId);return {ok:true,alreadyAttached:true};}
  }catch(_){}
  const now = Date.now(), last = kaosAttachAttemptAt.get(tabId) || 0;
  if(!kaosAuthorizedPo)return {ok:false,reason:'KAOS_AUTH_REQUIRED'};
  if (!allowReload || now - last < 15000) return {ok:false,reason:'BROKER_LOADING',retryAfterMs:Math.max(400,15000-(now-last))};
  kaosAttachAttemptAt.set(tabId, now);
  kaosAttachedTabIds.add(tabId);
  try{
    await chrome.tabs.reload(tabId,{bypassCache:false});
    return {ok:true,reloaded:true,reason:'AUTHORIZED_ATTACH'};
  }catch(e){return {ok:false,reason:'RELOAD_FAILED',error:String(e&&e.message||e)};}
}
async function kaosWaitForPoAttached(tabId) {
  const generation = kaosBrokerGeneration;
  const deadline = Date.now() + 20000;
  let result = await kaosEnsurePoAttached(tabId);
  while (true) {
    if (!kaosAuthorizedPo || generation !== kaosBrokerGeneration) return {ok:false,reason:'KAOS_AUTH_REQUIRED'};
    if (result.alreadyAttached) return result;
    if (!result.reloaded && result.reason !== 'BROKER_LOADING') return result;
    if (Date.now() >= deadline) return {ok:false,reason:'Pocket Option is still loading. Keep its tab open and try Connect again.'};
    await new Promise(resolve => setTimeout(resolve, 400));
    result = await kaosEnsurePoAttached(tabId, false);
  }
}
async function kaosEnsureAnyPoAttached(tabId){
  if(!kaosAuthorizedPo)await kaosPermitBrokerIntegration();
  if(Number.isInteger(tabId))return kaosEnsurePoAttached(tabId);
  const tabs=await chrome.tabs.query({url:KAOS_PO_PATTERNS});
  if(!tabs?.length)return {ok:false,reason:'NO_PO_TAB'};
  return kaosEnsurePoAttached(tabs[0].id);
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status !== 'complete') return;
  if (tabId !== botState.tabId) return;
  // content.js is injected by the manifest on every navigation. Do not inject it
  // again here. Only restore the bot state after the manifest content script loads.
  setTimeout(() => {
    chrome.storage.local.get('botRunning', data => {
      const shouldRun = data.botRunning === true && botState.running && botState.config;
      if (shouldRun) {
        try { chrome.tabs.sendMessage(tabId, botState.config).catch(() => {}); } catch (_) {}
      } else {
        chrome.storage.local.set({ botRunning: false });
        botState.running = false;
      }
    });
  }, 2000);
});


// ════════════════════════════════════════════════════════════
// ════════════════════════════════════════════════════════════
//  V1.2.1 — TOOLBAR ACTION POPUP
//  The extension icon now opens popup.html as a real toolbar popup
//  (manifest default_popup). No floating window is created.
// ════════════════════════════════════════════════════════════
const KAOS_FLOATING_WINDOW = { id: null, targetTabId: null, targetWindowId: null };

async function openKaosAppWindow() {
  try {
    const tabs = await chrome.tabs.query({ active:true, currentWindow:true });
    const target = tabs && tabs[0];
    if (target && target.id) {
      KAOS_FLOATING_WINDOW.targetTabId = target.id;
      KAOS_FLOATING_WINDOW.targetWindowId = target.windowId;
      await chrome.storage.local.set({
        KAOSTargetTabId: target.id,
        KAOSTargetWindowId: target.windowId
      });
    }
    if (KAOS_FLOATING_WINDOW.id) {
      try {
        await chrome.windows.update(KAOS_FLOATING_WINDOW.id,{focused:true});
        return;
      } catch (_) { KAOS_FLOATING_WINDOW.id=null; }
    }
    const w = await chrome.windows.create({
      url: chrome.runtime.getURL('popup.html?kaosApp=1'),
      type:'popup',
      width:1280,
      height:860,
      focused:true
    });
    KAOS_FLOATING_WINDOW.id = w && w.id ? w.id : null;
  } catch(e) { console.error('[KAOS] app window error:',e); }
}
// KAOS 1.6.21: duplicate toolbar click handler removed; single-window manager below is authoritative.
chrome.windows.onRemoved.addListener(id=>{
  if(id===KAOS_FLOATING_WINDOW.id) KAOS_FLOATING_WINDOW.id=null;
});
async function kaosKeepPocketOptionActive(refocusApp){
  try{
    const saved=await chrome.storage.local.get(['KAOSTargetTabId','KAOSTargetWindowId']);
    let tab=null;
    if(saved.KAOSTargetTabId){ try{ tab=await chrome.tabs.get(saved.KAOSTargetTabId); }catch(_){} }
    const poHosts=['pocketoption.com','po2.capital','p.finance','po.company','po1.capital','pocket-link22.co'];
    const valid=t=>{ try{ const host=new URL(t?.url||'').hostname; return poHosts.some(d=>host===d||host.endsWith('.'+d)); }catch(_){return false;} };
    if(!valid(tab)){
      const tabs=await chrome.tabs.query({});
      tab=tabs.find(valid)||null;
    }
    if(!tab) return {ok:false,reason:'NO_PO_TAB'};
    // Make PO the selected tab in its Chrome window and prevent discard.
    await chrome.tabs.update(tab.id,{active:true,autoDiscardable:false});
    await chrome.storage.local.set({KAOSTargetTabId:tab.id,KAOSTargetWindowId:tab.windowId});
    // Keep PO selected, but return keyboard focus to the separate KAOS app window.
    if(refocusApp){
      try{
        const cur=await chrome.windows.getCurrent();
        if(cur && cur.type==='popup') await chrome.windows.update(cur.id,{focused:true});
      }catch(_){}
    }
    return {ok:true,tabId:tab.id,windowId:tab.windowId};
  }catch(e){ return {ok:false,error:String(e&&e.message||e)}; }
}
chrome.runtime.onMessage.addListener((msg,_sender,sendResponse)=>{
  if(!msg || msg.type!=='KAOS_KEEP_PO_ACTIVE') return;
  kaosKeepPocketOptionActive(!!msg.refocusApp).then(sendResponse);
  return true;
});

chrome.runtime.onMessage.addListener((msg,sender,sendResponse)=>{
  if(!msg || msg.type!=='KAOS_RESIZE_APP') return;
  (async()=>{
    try{
      // A service worker's getCurrent() can be the broker window. Only resize
      // the verified extension sender's popup window, never Pocket Option.
      if (!String(sender.url||sender.tab?.url||'').startsWith(chrome.runtime.getURL('popup.html'))) throw Error('Open KAOS in its app window');
      const windowId=sender.tab?.windowId ?? msg.windowId;
      if(!Number.isInteger(windowId))throw Error('KAOS app window is unavailable');
      const win = await chrome.windows.get(windowId);
      if(win.type!=='popup')throw Error('KAOS companion requires an app window');
      const ownTabs=await chrome.tabs.query({windowId});
      if(!ownTabs.some(tab=>String(tab.url||'').startsWith(chrome.runtime.getURL('popup.html'))))throw Error('Not a KAOS app window');
      const saved = await chrome.storage.local.get(['KAOSTargetWindowId']);
      let broker = null;
      if(saved.KAOSTargetWindowId && saved.KAOSTargetWindowId!==win.id)try{broker=await chrome.windows.get(saved.KAOSTargetWindowId);}catch(_){}
      const width=msg.mode==='mini'?430:1280, height=msg.mode==='mini'?Math.min(800,Math.max(500,broker?.height||720)):900;
      const dims={state:'normal',width,height,focused:true};
      if(msg.mode==='mini'&&broker){dims.left=Math.max(broker.left||0,(broker.left||0)+(broker.width||width)-width);dims.top=broker.top||0;}
      await chrome.windows.update(win.id,dims);
      if(msg.mode==='max') await kaosKeepPocketOptionActive(true);
      sendResponse({ok:true});
    }catch(e){ sendResponse({ok:false,error:String(e&&e.message||e)}); }
  })();
  return true;
});


// ═══════════════════════════════════════════════════════════════════
// KAOS CLOUD INTEGRATION — auth/license/device/platform/sync/AI/learning.
// Added AROUND the existing bot. Broker execution stays inside the bot; these clients only talk to
// the KAOS website. KAOS cloud connectivity is never confused with broker (Pocket Option) connectivity.
// ═══════════════════════════════════════════════════════════════════
const kaosAuth = async () => {
  const t = await self.KaosCloud.getTokens();
  const deviceId = await self.KaosCloud.installId();
  return { accessToken: t.accessToken, deviceId };
};
let _kaosSync = null, _kaosLearn = null;
async function kaosApiBase() { return (await self.KaosCloud.apiHost()) + '/api/v1'; }

async function kaosSync() {
  if (_kaosSync) return _kaosSync;
  _kaosSync = self.KaosSyncClient.createKaosSyncClient({
    apiBase: await kaosApiBase(),
    getAuth: kaosAuth,
    onAuthExpired: async () => (await self.KaosCloud.refresh()) ? (await self.KaosCloud.getTokens()) : null,
    scheduleRetry: (ms, fn) => {
      const when = Date.now() + ms;
      chrome.alarms.create('kaos-sync-retry', { when });
      chrome.alarms.onAlarm.addListener(function h(a) {
        if (a.name === 'kaos-sync-retry') { chrome.alarms.onAlarm.removeListener(h); fn(); }
      });
    }
  });
  return _kaosSync;
}
async function kaosLearn() {
  if (_kaosLearn) return _kaosLearn;
  _kaosLearn = self.KaosLearningClient.createKaosLearningClient({
    apiBase: await kaosApiBase(),
    getAuth: kaosAuth,
    hasConsent: async () => true,
    botVersion: (chrome.runtime.getManifest && chrome.runtime.getManifest().version) || '1.0'
  });
  return _kaosLearn;
}

// Flush queued telemetry whenever the worker wakes.
chrome.alarms.create('kaos-sync-heartbeat', { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener(async (a) => { if (a.name === 'kaos-sync-heartbeat') { try { (await kaosSync()).flush(); } catch (_) {} } });

// Cloud telemetry for every lifecycle transition + AI learning on settlement.
// CRITICAL: this NEVER places a broker order. If the KAOS cloud is offline after the bot already
// submitted a broker trade, the sync client durably queues the event (stable eventId) and retries —
// the broker order is NOT re-submitted; only the cloud sync event is replayed and server-deduped.
async function kaosOnTradeEvent(type, trade) {
  trade = trade || {};
  try { (await kaosSync()).enqueue({ type, signalId: trade.signalId, tradeId: trade.tradeId, payload: trade }); } catch (_) {}
  if (type === 'TRADE_RESULT' && trade.featureVector && trade.outcome) {
    try {
      (await kaosLearn()).emit({
        sampleType: trade.sampleType || (trade.paper ? 'PAPER' : 'UNKNOWN'), accountMode: trade.accountMode || 'UNKNOWN',
        platform: trade.platform || 'pocket_option',
        asset: trade.asset, timeframe: trade.timeframe || '5s', expiration: trade.expiration,
        strategy: trade.engine || trade.strategy || 'KAOS_STRATEGY', strategyVersion: trade.strategyVersion || null, direction: trade.direction,
        aiPrediction: trade.aiPrediction, aiConfidence: trade.aiConfidence, aiModelVersion: trade.aiModelVersion,
        entryPrice: trade.entryPrice, settlementPrice: trade.settlementPrice, outcome: trade.outcome,
        featureVector: trade.featureVector, sampleId: trade.tradeId, decisionAt: trade.decisionAt, settledAt: trade.settledAt
      });
    } catch (_) {}
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || typeof msg.type !== 'string' || msg.type.indexOf('KAOS_') !== 0 || ['KAOS_BROKER_VAULT','KAOS_PO_ENSURE_ATTACH','KAOS_OPEN_APP_WINDOW','KAOS_KEEP_PO_ACTIVE','KAOS_RESIZE_APP','KAOS_EXPIRY_LABEL_BATCH','KAOS_EXPIRY_TRAIN_COLLECTED','KAOS_TRAIN_SPECIALISTS'].includes(msg.type)) return false; // Dedicated listeners own these response channels
  (async () => {
    try {
      switch (msg.type) {
        case 'KAOS_HEALTH': sendResponse({ ok:true, health:await self.KaosCloud.health() }); break;
        case 'KAOS_SESSION_STATUS': sendResponse({ok:true,state:await self.KaosCloud.sessionStatus()}); break;
        case 'KAOS_STARTUP': sendResponse({ ok: true, state: await self.KaosCloud.startup() }); break;
        case 'KAOS_LOGIN': {
          await self.KaosCloud.login(msg.email, msg.password);
          // Authentication has succeeded. A later startup/license/network failure must
          // not be misreported as a failed password login.
          let state;
          try { state = await self.KaosCloud.startup(); }
          catch (startupError) { state = {status:'OFFLINE', authenticated:true, detail:String(startupError?.message || startupError)}; }
          sendResponse({ ok: true, state: state }); break;
        }
        case 'KAOS_GOOGLE_LOGIN': {
          await self.KaosCloud.googleLogin();
          let state;
          try { state = await self.KaosCloud.startup(); }
          catch (startupError) { state = {status:'OFFLINE', authenticated:true, detail:String(startupError?.message || startupError)}; }
          sendResponse({ ok: true, state }); break;
        }
        case 'KAOS_LOGOUT': await kaosStopBrokerIntegration(); await self.KaosCloud.logout(); sendResponse({ ok: true }); break;
        case 'KAOS_GET_RESEARCH_MODEL': {
          const response=await self.KaosCloud.authFetch('/ai/research/micro-reversion',{method:'GET',cache:'no-store'});
          sendResponse(response.ok?{ok:true,data:await response.json()}:{ok:false,error:'Owner research model unavailable. Sign in as super admin and update the website backend.'});break;
        }
        case 'KAOS_GET_TRAINED_MODEL': {
          const scope=typeof msg.scope==='string'&&/^pocket_option:binary:5s:(15|20|25|30|45|60)s:(real|paper)$/.test(msg.scope)?msg.scope:'pocket_option:binary:5s:20s:real';
          const response = await self.KaosCloud.authFetch('/ai/training/bundle?scope='+encodeURIComponent(scope), {method:'GET'});
          sendResponse(response.ok ? {ok:true,data:await response.json()} : {ok:false,error:'Model access is unavailable'}); break;
        }
        case 'KAOS_GET_PLATFORMS': sendResponse({ ok: true, platforms: await self.KaosCloud.platforms() }); break;
        case 'KAOS_SELECT_PLATFORM':
          await self.KaosCloud.selectPlatform(msg.platform, msg.remember);
          sendResponse({ ok: true, state: await self.KaosCloud.startup() }); break;
        case 'KAOS_CONNECT_PLATFORM': {
          const platform = String(msg.platform || '');
          if (platform !== 'pocketoption' && platform !== 'pocket_option') {
            sendResponse({ ok: false, error: 'Unsupported trading platform' }); break;
          }
          await self.KaosCloud.selectPlatform('pocketoption', msg.remember);
          const patterns = [
            'https://pocketoption.com/*', 'https://*.pocketoption.com/*',
            'https://platform58.po2.capital/*', 'https://p.finance/*',
            'https://po.company/*', 'https://po1.capital/*', 'https://pocket-link22.co/*'
          ];
          let poTabs = await chrome.tabs.query({ url: patterns });
          let poTab = poTabs && (poTabs.find(t => t.active) || poTabs[0]);
          // CONNECT means attach to an existing Pocket Option tab when one exists.
          // Only open a new tab when there truly is no Pocket Option tab anywhere.
          if (!poTab) {
            poTab = await chrome.tabs.create({ url: 'https://pocketoption.com/en/cabinet/demo-quick-high-low/', active: true });
          } else {
            await chrome.tabs.update(poTab.id, { active: true });
            if (poTab.windowId != null) await chrome.windows.update(poTab.windowId, { focused: true });
          }
          // No page injection until the KAOS session, membership/device and
          // selected broker are accepted by the server.
          await kaosPermitBrokerIntegration();
          const attached = await kaosWaitForPoAttached(poTab.id);
          if (!attached.ok) throw new Error('Pocket Option charts could not attach: ' + attached.reason);
          await chrome.storage.local.set({ KAOSTargetTabId: poTab.id, KAOSTargetWindowId: poTab.windowId, kaosPoAttached: true });
          KAOS_FLOATING_WINDOW.targetTabId = poTab.id;
          KAOS_FLOATING_WINDOW.targetWindowId = poTab.windowId;
          sendResponse({ ok: true, tabId: poTab.id, state: await self.KaosCloud.startup() }); break;
        }
        case 'KAOS_SET_CONSENT': sendResponse({ ok: true, result: await self.KaosCloud.setConsent(msg.consent) }); break;
        case 'KAOS_SET_HOST': await self.KaosCloud.setApiHost(msg.host); _kaosSync = null; _kaosLearn = null; sendResponse({ ok: true }); break;
        case 'KAOS_OPENAI_BRAIN': {
          const started=Date.now();
          try {
            const r=await self.KaosCloud.authFetch('/ai/brain',{
              method:'POST',
              headers:{'Content-Type':'application/json'},
              body:JSON.stringify({mode:'shadow',schema:'KAOS_BRAIN_V1',horizons:[5,10,15,30],snapshot:msg.snapshot||{}})
            });
            let data={}; try{data=await r.json();}catch(_){}
            if(!r.ok){
              const status={ts:Date.now(),state:r.status===403?'MEMBERSHIP_REQUIRED':r.status===401?'AUTH_REQUIRED':r.status===503?'SERVER_NOT_CONFIGURED':'SERVER_ERROR',httpStatus:r.status,detail:data?.detail||null};
              await chrome.storage.local.set({kaosOpenAiBrainStatus:status});
              sendResponse({ok:false,...status}); break;
            }
            const rec={ts:Date.now(),direction:String(data.direction||'HOLD').toUpperCase(),confidence:Number.isFinite(+data.confidence)?+data.confidence:null,expirySec:[5,10,15,30].includes(+data.expirySec)?+data.expirySec:null,regime:String(data.regime||'UNKNOWN'),setupType:String(data.setupType||'UNKNOWN'),model:String(data.model||'OPENAI'),requestId:data.requestId||null,shadowOnly:true,latencyMs:Date.now()-started};
            await chrome.storage.local.set({kaosOpenAiBrainShadow:rec,kaosOpenAiBrainStatus:{ts:Date.now(),state:'CONNECTED',httpStatus:200,latencyMs:rec.latencyMs}});
            sendResponse({ok:true,prediction:rec}); break;
          } catch(e) {
            const status={ts:Date.now(),state:e?.kind==='SESSION_EXPIRED'?'AUTH_REQUIRED':e?.kind==='OFFLINE'?'OFFLINE':'REQUEST_ERROR',detail:String(e?.message||e)};
            await chrome.storage.local.set({kaosOpenAiBrainStatus:status});
            sendResponse({ok:false,...status}); break;
          }
        }
        case 'KAOS_PREDICT': sendResponse({ ok: true, prediction: await self.KaosCloud.predict(msg.featureVector, msg.context) }); break;
        case 'KAOS_TRADE_EVENT': await kaosOnTradeEvent(msg.eventType, msg.trade); sendResponse({ ok: true }); break;
        case 'KAOS_SYNC_FLUSH': sendResponse({ ok: true, result: await (await kaosSync()).flush() }); break;
        default: sendResponse({ ok: false, error: 'unknown KAOS message' });
      }
    } catch (e) { sendResponse({ ok: false, error: String((e && e.message) || e), kind: (e && e.kind) || null }); }
  })();
  return true; // async response
});


function kaosIsSupportedPoUrl(url){
  try{const h=new URL(url||'').hostname.toLowerCase();return h==='pocketoption.com'||h.endsWith('.pocketoption.com')||h==='platform58.po2.capital'||h==='p.finance'||h==='po.company'||h==='po1.capital'||h==='pocket-link22.co';}catch(_){return false;}
}
chrome.tabs.onUpdated.addListener((tabId,changeInfo,tab)=>{
  if(kaosAuthorizedPo&&tab&&kaosIsSupportedPoUrl(tab.url)&&(changeInfo.status==='complete'||changeInfo.url)) kaosEnsurePoAttached(tabId).catch(()=>{});
});
chrome.tabs.onActivated.addListener(async({tabId})=>{
  try{const tab=await chrome.tabs.get(tabId);if(kaosAuthorizedPo&&kaosIsSupportedPoUrl(tab.url))await kaosEnsurePoAttached(tabId);}catch(_){}
});

chrome.runtime.onMessage.addListener((msg,_sender,sendResponse)=>{
  if(msg?.type!=='KAOS_PO_ENSURE_ATTACH')return;
  kaosEnsureAnyPoAttached(msg.tabId).then(sendResponse).catch(e=>sendResponse({ok:false,error:String(e)}));
  return true;
});

chrome.runtime.onMessage.addListener((msg,_sender,sendResponse)=>{
  if(msg?.type!=='KAOS_OPEN_APP_WINDOW')return;
  kaosOpenSingleAppWindow().then(sendResponse).catch(e=>sendResponse({ok:false,error:String(e)}));
  return true;
});

chrome.action.onClicked.addListener(()=>{kaosOpenSingleAppWindow().catch(()=>{});});

// KAOS Research Agents: live closed-candle feed (shadow-only).
importScripts('kaos-agent-live-bridge.js');

// KAOS member broker vault — proxy requests via the existing authenticated cloud client.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || msg.type !== 'KAOS_BROKER_VAULT') return;
  (async () => {
    try {
      const method = msg.method || 'GET';
      if (!['GET','PUT','DELETE'].includes(method) || !['/broker-connections','/broker-connections/coinbase','/broker-connections/coinbase/status','/broker-connections/coinbase/accounts','/broker-connections/coinbase/products'].includes(msg.path)) throw Error('Invalid broker request');
      const response = await self.KaosCloud.authFetch(msg.path, {method, headers:{'Content-Type':'application/json'}, ...(method==='PUT'?{body:JSON.stringify(msg.payload)}:{})});
      const data=await response.json();
      sendResponse({ok:response.ok,data});
    } catch (e) {sendResponse({ok:false,error:String(e.message||e)});}
  })();
  return true;
});
