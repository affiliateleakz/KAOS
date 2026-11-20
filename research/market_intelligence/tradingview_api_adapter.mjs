/**
 * KAOS offline-first TradingView-API research adapter.
 *
 * Based on public API concepts documented by Mathieu2301/TradingView-API
 * (ISC). Does not copy upstream code. No data requests unless the operator
 * explicitly enables --fetch and acknowledges separately verified provider rights.
 * Never used for orders, public members, or automated collection by default.
 */
import fs from "node:fs";
import path from "node:path";

const TF = new Map([["1",60],["3",180],["5",300],["15",900],["60",3600],["1S",1],["5S",5],["15S",15],["30S",30]]);
const SYMBOL = /^[A-Z0-9_.-]+:[A-Z0-9_.-]{2,32}$/;

export function normalizeTvBars(bars,{symbol,timeframe,nowSeconds=Math.floor(Date.now()/1000)}={}) {
  if (!SYMBOL.test(symbol||"")) throw new Error("Exchange-qualified TradingView symbol required");
  const interval=TF.get(timeframe);
  if (!interval) throw new Error("Unsupported TradingView interval");
  if (!Array.isArray(bars)||bars.length>20000) throw new Error("Invalid or unbounded history");
  const normalized=[];
  for(const row of bars) {
    if (!row||typeof row!=="object") throw new Error("Invalid candle");
    const time=row.time;
    const prices=["open","high","low","close","volume"].map(k=>row[k]);
    if(!Number.isInteger(time)||time<=0||time%interval!==0||
       prices.some(x=>typeof x!=="number"||!Number.isFinite(x))) throw new Error("Invalid OHLCV or timestamp");
    const [o,h,l,c,v]=prices;
    if(Math.min(o,h,l,c)<=0||l>Math.min(o,c)||h<Math.max(o,c)||v<0) throw new Error("Inconsistent OHLCV");
    if(time+interval>nowSeconds) continue; // never label an unfinished bar as complete
    normalized.push({ts:time*1000,open:o,high:h,low:l,close:c,volume:v});
  }
  normalized.sort((a,b)=>a.ts-b.ts);
  for(let i=1;i<normalized.length;i++){
    if(normalized[i].ts===normalized[i-1].ts) throw new Error("Duplicate candle");
  }
  const gaps=normalized.reduce((n,row,i)=>i&&row.ts-normalized[i-1].ts!==interval*1000?n+1:n,0);
  return {
    status:"local_research_only_not_ingested",symbol,
    timeframe,seconds:interval,source:"tradingview_community_unofficial",
    complete_bars:normalized.length,gaps,candles:normalized,
    ai_training_approved:false,
    note:"No commercial data license or live execution access is inferred. Verify feed, session, provenance and rights."
  };
}

async function cli(){
  const args=process.argv.slice(2);
  const arg=(name)=>{const i=args.indexOf(name);return i>=0?args[i+1]:null;};
  const symbol=arg("--symbol"), timeframe=arg("--timeframe")||"1";
  const out=arg("--output"), fixture=arg("--input-json");
  const fetch=args.includes("--fetch");
  if(!out||fetch===Boolean(fixture)) throw new Error("Provide --output and exactly one of --input-json or --fetch");
  if(fs.existsSync(out)) throw new Error("Refusing to overwrite existing research export");
  let bars;
  if(fetch){
    if(!args.includes("--acknowledge-provider-rights"))
      throw new Error("Verify provider rights, then acknowledge explicitly");
    const count=Number(arg("--count")||300);
    if(!Number.isInteger(count)||count<1||count>2000) throw new Error("Count out of range");
    // Deliberately not part of the production frontend or API server.
    const {getCandles}=await import("@mathieuc/tradingview/data");
    bars=await getCandles({symbol,timeframe,count,timeoutMs:30000});
  }else{
    bars=JSON.parse(fs.readFileSync(fixture,"utf8")).candles;
  }
  const result=normalizeTvBars(bars,{symbol,timeframe});
  fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(result,null,2)+"\n",{flag:"wx"});
  process.stdout.write(JSON.stringify({output:out,bars:result.complete_bars,gaps:result.gaps})+"\n");
}
if(process.argv[1]&&path.resolve(process.argv[1])===path.resolve(new URL(import.meta.url).pathname)){
  cli().catch(error=>{console.error(error.message);process.exitCode=1;});
}
