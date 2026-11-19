/* Offline harness for reviewed, user-supplied pure indicator/decision files only.
   Never loads the extension, accesses a browser, calls a service, or submits an order. */
const fs=require('node:fs'),vm=require('node:vm'),readline=require('node:readline');
const [indicatorsPath,enginePath]=process.argv.slice(2);
if(!indicatorsPath||!enginePath)throw Error('Supply local indicators.js and signalEngine.js paths');
let intensity='mid';
const context=vm.createContext({state:{activePair:null,activePeriod:30,settings:{}},getRequiredCandles:()=>({low:12,mid:16,high:20}[intensity]),getBufferedCandles:()=>[],getCurrentPair:()=>''});
vm.runInContext(fs.readFileSync(indicatorsPath,'utf8'),context,{timeout:1000});
vm.runInContext(fs.readFileSync(enginePath,'utf8'),context,{timeout:1000});
if(typeof context.buildIndicators!=='function'||typeof context.AvalisaSignalEngine?.evaluateSignal!=='function')throw Error('Unexpected pure source interface');
readline.createInterface({input:process.stdin,crlfDelay:Infinity}).on('line',line=>{
 const {asset,rows}=JSON.parse(line),buffer=[],signals={};
 for(const mode of ['sampled5','closed30'])for(const level of ['low','mid','high'])signals[mode+':'+level]=[];
 for(const row of rows){
  const [ts,open,high,low,close]=row,start=Math.floor(ts/30000)*30;
  if(!buffer.length&&ts%30000!==0)continue; // Never seed an incomplete first candle.
  let last=buffer.at(-1);
  if(last&&last.time===start){last.high=Math.max(last.high,high);last.low=Math.min(last.low,low);last.close=close;}
  else {buffer.push({time:start,open,high,low,close});if(buffer.length>50)buffer.shift();}
  const decision=ts+5000;
  for(const level of ['low','mid','high']){
   intensity=level;
   const indicators=context.buildIndicators(buffer,asset,'S30');
   if(!indicators)continue;
   const result=context.AvalisaSignalEngine.evaluateSignal(indicators,level);
   if(!['CALL','PUT'].includes(result.action))continue;
   const seconds={S30:30,M1:60,M3:180,M5:300}[result.timeframe];if(!seconds)throw Error('Unknown selected expiry');
   const signal={decision,direction:result.action==='CALL'?1:-1,expiry:seconds,confidence:result.snapshot.confidence,regime:result.snapshot.regime};
   signals['sampled5:'+level].push(signal);
   if(decision%30000===0)signals['closed30:'+level].push(signal);
  }
 }
 process.stdout.write(JSON.stringify({asset,signals})+'\n');
});
