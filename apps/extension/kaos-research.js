const el=id=>document.getElementById(id);el('date').value=new Date().toISOString().slice(0,10);async function req(path,opts){const base=el('server').value.replace(/\/$/,'');if(!/^http:\/\/127\.0\.0\.1:8765$/.test(base))throw Error('Only the local service at 127.0.0.1:8765 is permitted');const r=await fetch(base+path,opts);const d=await r.json();if(!r.ok)throw Error(d.error||'HTTP '+r.status);return d}el('health').onclick=async()=>{try{el('result').textContent=JSON.stringify(await req('/health'),null,2)}catch(e){el('result').textContent=String(e)}};el('run').onclick=async()=>{el('result').textContent='Research running. This can take minutes and incur LLM API charges.';try{const d=await req('/research',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticker:el('ticker').value.trim(),date:el('date').value})});el('result').textContent=JSON.stringify(d,null,2)}catch(e){el('result').textContent=String(e)}};
// Local closed-candle research; accepts OHLC CSV, no extension trade permission.
function parseCsv(text){const lines=text.replace(/\r/g,'').trim().split('\n');if(lines.length<2)throw Error('CSV has no rows');const headers=lines[0].split(',').map(x=>x.trim().replace(/^"|"$/g,'').toLowerCase());const idx=['open','high','low','close'].map(k=>headers.indexOf(k));if(idx.some(i=>i<0))throw Error('CSV needs open,high,low,close columns');return lines.slice(1).filter(Boolean).map(line=>{const v=line.split(',');return Object.fromEntries(['open','high','low','close'].map((k,i)=>[k,Number(v[idx[i]])]))}).filter(c=>Object.values(c).every(Number.isFinite)).slice(-12000)}
el('otcrun').onclick=async()=>{try{const file=el('otcfile').files?.[0];if(!file)throw Error('Choose a CSV file');if(file.size>5000000)throw Error('CSV too large (5 MB max)');const candles=parseCsv(await file.text());el('result').textContent='Analyzing '+candles.length+' candles...';const result=await req('/otc/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({market:el('otcmarket').value,candles})});el('result').textContent=JSON.stringify(result,null,2)}catch(e){el('result').textContent=String(e)}};

// Read the same shadow research status that the background service writes.
async function showLiveAgentStatus(){
  try{
    const state=(await chrome.storage.local.get('KAOS_agent_live_status_v1')).KAOS_agent_live_status_v1;
    el('live-agent-status').textContent=state ? `${state.status} · ${state.market||'no active market'} · ${state.decision||'HOLD'}` : 'Waiting for recorded closed candles';
    el('live-agent-detail').textContent=state ? JSON.stringify(state,null,2) : '';
  }catch(e){el('live-agent-status').textContent=String(e)}
}
chrome.storage.onChanged.addListener((c,a)=>{if(a==='local'&&c.KAOS_agent_live_status_v1)void showLiveAgentStatus()});
void showLiveAgentStatus();
