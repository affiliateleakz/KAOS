/* Offline pure-source replay. No browser, network, or order interface. */
const fs=require('node:fs'),vm=require('node:vm'),readline=require('node:readline');
const [ip,ep]=process.argv.slice(2);
const ctx=vm.createContext({state:{settings:{}},getRequiredCandles:()=>12,getBufferedCandles:()=>[],getCurrentPair:()=>''});
vm.runInContext(fs.readFileSync(ip,'utf8'),ctx,{timeout:1000});
vm.runInContext(fs.readFileSync(ep,'utf8'),ctx,{timeout:1000});
readline.createInterface({input:process.stdin,crlfDelay:Infinity}).on('line',line=>{
 const {asset,tf,rows}=JSON.parse(line),buffer=[],signals={low:[],mid:[],high:[]};
 for(const [ts,open,high,low,close] of rows){
  buffer.push({time:ts/1000,open,high,low,close});if(buffer.length>50)buffer.shift();
  if(buffer.length<12)continue;
  const ind=ctx.buildIndicators(buffer,asset,'S'+tf);if(!ind)continue;
  for(const level of ['low','mid','high']){
   if(buffer.length<({low:12,mid:16,high:20}[level]))continue;
   const r=ctx.AvalisaSignalEngine.evaluateSignal(ind,level);
   if(!['CALL','PUT'].includes(r.action))continue;
   const expiry={S30:30,M1:60,M3:180,M5:300}[r.timeframe];if(!expiry)throw Error('Unknown expiry');
   signals[level].push([ts+tf*1000,r.action==='CALL'?1:-1,expiry]);
  }
 }
 process.stdout.write(JSON.stringify({asset,tf,signals})+'\n');
});
