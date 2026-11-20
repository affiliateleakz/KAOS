/**
 * KAOS Cloudflare scheduled candle collector + private R2 archive.
 *
 * Uses authorized Alpaca, Coinbase Exchange, optionally OANDA market data.
 * Designed for 5-minute scheduled executions rather than a resident VPS.
 * R2 is the durable archive; optional mirror to existing KAOS Mongo-backed API.
 * Does not execute trades, run models, or expose prices publicly.
 */
const ASSET = new Set(["stock","etf","crypto","forex"]);
const INTERVAL = new Set([60,300,900]);
const MAX_MARKETS = 20;
const MAX_BARS_PER_DAY = 1500;
const HEADERS = {"User-Agent":"KAOS-R2-Candle-Collector/1.0","Accept":"application/json"};

export function validateMarkets(value) {
  if (!Array.isArray(value) || value.length<1 || value.length>MAX_MARKETS)
    throw Error("Configure 1–20 markets per Worker; shard larger universes");
  const found = new Set();
  return value.map(m=>{
    if(!m || typeof m!=="object" || !ASSET.has(m.asset_class) ||
       !INTERVAL.has(m.seconds) || typeof m.symbol!=="string")
      throw Error("Invalid market config");
    const sym=m.symbol;
    const pattern=m.asset_class==="crypto"?/^[A-Z0-9]{2,10}-[A-Z]{3,5}$/:
      m.asset_class==="forex"?/^[A-Z]{3}_[A-Z]{3}$/:
      /^[A-Z][A-Z0-9.]{0,11}$/;
    if (!pattern.test(sym)) throw Error("Invalid market symbol");
    const id=`${m.asset_class}:${sym}:${m.seconds}`;
    if(found.has(id))throw Error("Duplicate market");
    found.add(id);
    return Object.freeze({symbol:sym,asset_class:m.asset_class,seconds:m.seconds});
  });
}

async function jsonFetch(url,headers={}) {
  const response=await fetch(url,{headers:{...HEADERS,...headers},
    // Cloudflare Workers does not implement redirect: "error".
    // Manual handling also ensures credentials are never forwarded on redirects.
    redirect:"manual",signal:AbortSignal.timeout(12000)});
  if(response.status>=300 && response.status<400)throw Error(`feed_redirect_${response.status}`);
  if(!response.ok)throw Error(`feed_http_${response.status}`);
  const obj=await response.json();
  if(!obj)throw Error("empty_feed_response");
  return obj;
}

export async function providerBars(m,env,read=jsonFetch) {
  const {symbol,asset_class,seconds}=m;
  if(asset_class==="crypto"){
    const url=`https://api.exchange.coinbase.com/products/${encodeURIComponent(symbol)}/candles?granularity=${seconds}`;
    const v=await read(url);
    if(!Array.isArray(v))throw Error("invalid_coinbase_feed");
    return {source:"coinbase_exchange_public",bars:v.filter(r=>Array.isArray(r)&&r.length>=6).map(
      r=>({ts:Number(r[0])*1000,low:r[1],high:r[2],open:r[3],close:r[4],volume:r[5]})
    )};
  }
  if(asset_class==="stock"||asset_class==="etf"){
    if(!env.APCA_API_KEY_ID||!env.APCA_API_SECRET_KEY)throw Error("alpaca_keys_not_configured");
    const feed=env.ALPACA_FEED||"iex";
    if(!["iex","sip"].includes(feed))throw Error("invalid_alpaca_feed");
    const tf={60:"1Min",300:"5Min",900:"15Min"}[seconds];
    const url=`https://data.alpaca.markets/v2/stocks/${encodeURIComponent(symbol)}/bars?timeframe=${tf}&limit=300&sort=desc&feed=${feed}&adjustment=raw`;
    const v=await read(url,{"APCA-API-KEY-ID":env.APCA_API_KEY_ID,
      "APCA-API-SECRET-KEY":env.APCA_API_SECRET_KEY});
    if(!Array.isArray(v.bars))throw Error("invalid_alpaca_feed");
    return {source:`alpaca_${feed}`,bars:v.bars.map(
      r=>({ts:Date.parse(r.t),open:r.o,high:r.h,low:r.l,close:r.c,volume:r.v})
    )};
  }
  if(!env.OANDA_TOKEN)throw Error("oanda_token_not_configured");
  const environment=env.OANDA_ENVIRONMENT||"practice";
  if(!["practice","live"].includes(environment))throw Error("invalid_oanda_environment");
  const host=environment==="practice"?"api-fxpractice.oanda.com":"api-fxtrade.oanda.com";
  const tf={60:"M1",300:"M5",900:"M15"}[seconds];
  const v=await read(`https://${host}/v3/instruments/${encodeURIComponent(symbol)}/candles?count=300&granularity=${tf}&price=M`,
    {"Authorization":`Bearer ${env.OANDA_TOKEN}`});
  if(!Array.isArray(v.candles))throw Error("invalid_oanda_feed");
  return {source:`oanda_${environment}_mid`,bars:v.candles.filter(x=>x.complete===true).map(
    r=>({ts:Date.parse(r.time),open:r.mid.o,high:r.mid.h,low:r.mid.l,close:r.mid.c,volume:r.volume})
  )};
}

export function closedBars(m,source,raw,nowMs) {
  if(typeof source!=="string"||!source)throw Error("missing source");
  if(!Array.isArray(raw)||raw.length>1000)throw Error("unbounded provider response");
  const output=new Map();
  for(const r of raw){
    if(!r || !Number.isInteger(r.ts)||r.ts<=0 ||
       r.ts%(m.seconds*1000)!==0 || r.ts+m.seconds*1000>nowMs)continue;
    const vals=["open","high","low","close","volume"].map(k=>r[k]);
    const [o,h,l,c,v]=vals.map(x=>x==null?null:Number(x));
    if([o,h,l,c].some(x=>!Number.isFinite(x)||x<=0) ||
       l>Math.min(o,c)||h<Math.max(o,c) ||
       (v!==null&&(!Number.isFinite(v)||v<0)))continue;
    const item={ts:r.ts,symbol:m.symbol,asset_class:m.asset_class,
      seconds:m.seconds,source,open:o,high:h,low:l,close:c,volume:v};
    if(output.has(item.ts) && JSON.stringify(output.get(item.ts))!==JSON.stringify(item))
      throw Error("conflicting_provider_bar");
    output.set(item.ts,item);
  }
  return [...output.values()].sort((a,b)=>a.ts-b.ts);
}

export function objectKey(row){
  const day=new Date(row.ts).toISOString().slice(0,10);
  return `candles/v1/${row.source}/${row.asset_class}/${row.symbol}/${row.seconds}s/${day}.json`;
}

export async function storeBars(bucket,rows) {
  const byKey=new Map();
  for(const bar of rows){
    const key=objectKey(bar);
    if(!byKey.has(key))byKey.set(key,[]);
    byKey.get(key).push(bar);
  }
  let written=0;
  for(const [key,newBars] of byKey){
    const existing=await bucket.get(key);
    let past=[];
    if(existing){
      const payload=await existing.json();
      if(payload?.schema!=="kaos_candles_v1" || !Array.isArray(payload.candles))
        throw Error("incompatible_r2_archive");
      past=payload.candles;
    }
    const merged=new Map();
    for(const row of [...past,...newBars]){
      const found=merged.get(row.ts);
      if(found && JSON.stringify(found)!==JSON.stringify(row))
        throw Error("historical_price_revision_needs_manual_review");
      merged.set(row.ts,row);
    }
    const candles=[...merged.values()].sort((a,b)=>a.ts-b.ts);
    if(candles.length>MAX_BARS_PER_DAY)throw Error("daily_archive_limit");
    if(candles.length===past.length)continue; // no R2 PUT for unchanged history
    await bucket.put(key,JSON.stringify({
      schema:"kaos_candles_v1",source:newBars[0].source,
      symbol:newBars[0].symbol,asset_class:newBars[0].asset_class,
      seconds:newBars[0].seconds,candles,
    }),{httpMetadata:{contentType:"application/json"}});
    written+=candles.length-past.length;
  }
  return {newBars:written,objectsTouched:byKey.size};
}

async function mirrorToKaos(env,rows){
  if(!env.KAOS_API_BASE)return {status:"disabled"};
  if(!env.KAOS_COLLECTOR_KEY)throw Error("missing_kaos_collector_key");
  const base=new URL(env.KAOS_API_BASE);
  if(base.protocol!=="https:" || base.username || base.password || base.search)
    throw Error("invalid_kaos_api_base");
  const endpoint=new URL("/api/v1/collector/candles/ingest",base);
  const r=await fetch(endpoint.toString(),{method:"POST",
    headers:{"Content-Type":"application/json","X-KAOS-Collector-Key":env.KAOS_COLLECTOR_KEY},
    body:JSON.stringify(rows),signal:AbortSignal.timeout(15000)});
  if(!r.ok)throw Error(`kaos_ingest_http_${r.status}`);
  const out=await r.json();
  if(out.accepted!==rows.length)throw Error("kaos_ingest_incomplete");
  return {status:"mirrored",count:out.accepted};
}

export async function runScheduled(env,{nowMs=Date.now(),fetcher=providerBars}={}) {
  if(!env?.CANDLE_ARCHIVE)throw Error("R2 binding CANDLE_ARCHIVE required");
  const markets=validateMarkets(JSON.parse(env.MARKETS_JSON||"[]"));
  const results=[];
  for(const market of markets){
    try {
      const {source,bars}=await fetcher(market,env);
      const closed=closedBars(market,source,bars,nowMs);
      if(!closed.length){results.push({market:market.symbol,status:"no_new_closed_bars"});continue;}
      const written=await storeBars(env.CANDLE_ARCHIVE,closed);
      // Mirror can fail independently; archive remains durable in R2.
      let mirror={status:"disabled"};
      try{mirror=await mirrorToKaos(env,closed);}
      catch(e){mirror={status:"failed",reason:String(e.message).slice(0,80)};}
      results.push({market:market.symbol,source,status:"archived",
        closed:closed.length,...written,mirror});
    } catch(e){
      results.push({market:market.symbol,status:"error",
        reason:String(e.message).slice(0,90)});
    }
  }
  return {ranAt:new Date(nowMs).toISOString(),results,
    ok:results.filter(x=>x.status!=="error").length,errors:results.filter(x=>x.status==="error").length};
}

/**
 * Keep the last collection result in the private R2 bucket even when all
 * upstream feeds fail. Never include secret values or raw upstream responses.
 * This is a single small object overwritten on each cron invocation.
 */
export async function recordRunStatus(env,report) {
  if (!env?.CANDLE_ARCHIVE) throw Error("R2 binding CANDLE_ARCHIVE required");
  const safe = {
    schema:"kaos_candle_collector_status_v1",
    ranAt:report.ranAt,
    ok:report.ok,
    errors:report.errors,
    results:report.results.map(item=>({
      market:item.market,
      status:item.status,
      ...(item.reason ? {reason:item.reason} : {}),
      ...(typeof item.newBars==="number" ? {newBars:item.newBars} : {}),
      ...(item.mirror ? {mirror:item.mirror.status} : {}),
    })),
  };
  await env.CANDLE_ARCHIVE.put("status/last-run.json",JSON.stringify(safe),
    {httpMetadata:{contentType:"application/json"}});
  return safe;
}

export default {
  async scheduled(controller,env,ctx) {
    ctx.waitUntil((async()=>{
      const nowMs=controller.scheduledTime||Date.now();
      let report;
      try {
        report=await runScheduled(env,{nowMs});
      } catch (error) {
        // Even fatal configuration errors should be visible in the R2 status.
        report={ranAt:new Date(nowMs).toISOString(),ok:0,errors:1,
          results:[{market:"collector",status:"error",
            reason:String(error?.message||error).slice(0,90)}]};
      }
      try {
        const result=await recordRunStatus(env,report);
        console.log("KAOS scheduled collection",JSON.stringify(result));
      } catch(error) {
        console.error("KAOS R2 status write failure",String(error?.message||error));
      }
    })());
  },
  async fetch(){
    // No public history, status or control endpoint; private R2 binding only.
    return new Response("Not found",{status:404});
  },
};
