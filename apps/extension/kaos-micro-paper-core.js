/* Isolated research scorer. No Chrome messaging, broker access or order functions. */
(function(root){'use strict';
const avg=a=>a.reduce((s,v)=>s+v,0)/a.length;
class Context{
 constructor(){this.reset();}
 reset(){this.count=0;this.last=null;this.closes=[];this.tr=[];this.e20=null;this.e50=null;this.vector=null;}
 push(row){
  const ts=Number(row.ts),end=Number(row.closeTs??ts+5000),o=Number(row.open),h=Number(row.high),l=Number(row.low),c=Number(row.close);
  if(![ts,end,o,h,l,c].every(Number.isFinite)||ts<=0||ts%5000||end!==ts+5000||!(0<l&&l<=Math.min(o,c)&&Math.max(o,c)<=h))throw Error('Require valid completed five-second OHLC bars');
  if(this.last&&ts<=this.last.ts)throw Error('Candles must be unique and sorted');
  const gap=Boolean(this.last&&ts!==this.last.ts+5000);if(gap)this.reset();
  const span=Math.max(1e-12,h-l),tr=this.last?Math.max(h-l,Math.abs(h-this.last.close),Math.abs(l-this.last.close)):h-l;
  this.e20=this.e20===null?c:this.e20+(2/21)*(c-this.e20);this.e50=this.e50===null?c:this.e50+(2/51)*(c-this.e50);
  this.closes.push(c);if(this.closes.length>100)this.closes.shift();this.tr.push(tr);if(this.tr.length>100)this.tr.shift();this.count++;this.last={ts,close:c};this.vector=null;
  if(this.count>=320){
   const recent=this.closes.slice(-20),mean=avg(recent),sd=Math.max(1e-12,Math.sqrt(recent.reduce((s,v)=>s+(v-mean)**2,0)/19)),atr=Math.max(1e-12,avg(this.tr.slice(-20)));
   this.vector=[(c-o)/span,(Math.min(o,c)-l)/span,(h-Math.max(o,c))/span,(this.e20-this.e50)/atr,(c-mean)/sd,(c-this.e20)/atr,atr/Math.max(1e-12,avg(this.tr)),...[1,3,6,12].map(n=>(c-this.closes[this.closes.length-1-n])/atr),span/atr].map(Math.fround);
  }
  return {gap,ready:Boolean(this.vector),ts:ts+5000};
 }
}
function score(model,vector){
 if(model?.schema!=='kaos-crypto-12-v1'||!Array.isArray(vector)||vector.length!==12||!vector.every(Number.isFinite))throw Error('Unsupported research model/features');
 let margin=Math.fround(model.base);
 for(let node of model.trees){while(!Object.hasOwn(node,'leaf'))node=vector[node.f]<node.t?node.l:node.r;margin=Math.fround(margin+node.leaf);}
 const probability=1/(1+Math.exp(-margin));return {probUp:probability,direction:probability>=.6?'BUY':probability<=.4?'SELL':'HOLD',researchOnly:true,executionEnabled:false};
}
class PaperSession{
 constructor(model,symbol,{payout=.8,adverseBps=0}={}){
  if(!model.symbols.includes(symbol))throw Error('Choose a supported crypto research market');
  if(!(payout>0&&payout<=1)||!Number.isFinite(adverseBps)||adverseBps<0||adverseBps>100)throw Error('Invalid paper assumptions');
  this.model=model;this.symbol=symbol;this.payout=payout;this.adverseBps=adverseBps;this.context=new Context();this.pending=null;this.open=null;this.results=[];this.lastDecision=null;this.gaps=0;this.cancelled=0;
 }
 step(row){
  const old=this.context.last,ts=Number(row.ts),gap=Boolean(old&&ts!==old.ts+5000);
  // Validate before mutating paper positions.
  const state=this.context.push(row);
  if(gap){this.gaps++;if(this.open)this.cancelled++;this.open=null;this.pending=null;}
  if(this.open&&ts>=this.open.exitTs){
   if(ts===this.open.exitTs){const delta=(Number(row.open)-this.open.entry)*(this.open.direction==='BUY'?1:-1),outcome=delta===0?'TIE':delta>0?'WIN':'LOSS';this.results.push({...this.open,settlement:Number(row.open),outcome,pnl:outcome==='WIN'?this.payout:outcome==='LOSS'?-1:0,symbol:this.symbol,paper:true});}
   else this.cancelled++;
   this.open=null;
  }
  if(this.pending&&ts===this.pending.entryTs&&!this.open){const side=this.pending.direction==='BUY'?1:-1;this.open={...this.pending,entry:Number(row.open)*(1+side*this.adverseBps/10000),exitTs:ts+15000};}
  this.pending=null;
  this.lastDecision=state.ready?score(this.model,this.context.vector):{direction:'HOLD',probUp:null,executionEnabled:false,researchOnly:true};
  const decisionTs=ts+5000;
  if(this.lastDecision.direction!=='HOLD'&&(!this.open||decisionTs>=this.open.exitTs))this.pending={direction:this.lastDecision.direction,entryTs:decisionTs,decisionAt:decisionTs};
  return this.lastDecision;
 }
 summary(){const wins=this.results.filter(r=>r.outcome==='WIN').length,losses=this.results.filter(r=>r.outcome==='LOSS').length;return {symbol:this.symbol,wins,losses,ties:this.results.length-wins-losses,winRate:wins+losses?wins/(wins+losses):null,pnl:this.results.reduce((s,r)=>s+r.pnl,0),gaps:this.gaps,cancelled:this.cancelled,open:Boolean(this.open),pending:Boolean(this.pending),warmup:this.context.count,researchOnly:true,executionEnabled:false};}
}
function aggregateSeconds(rows,now){
 const groups=new Map();for(const r of rows){const ts=Number(r[0]);if(Number(r[6])>=now)continue;const bucket=Math.floor(ts/5000)*5000;const group=groups.get(bucket)||[];group.push(r);groups.set(bucket,group);}
 const output=[];for(const [ts,group] of [...groups].sort((a,b)=>a[0]-b[0])){group.sort((a,b)=>a[0]-b[0]);if(group.length!==5||group.some((r,i)=>Number(r[0])!==ts+i*1000)||ts+5000>now||!group.some(r=>Number(r[8])>0))continue;output.push({ts,closeTs:ts+5000,open:Number(group[0][1]),high:Math.max(...group.map(r=>Number(r[2]))),low:Math.min(...group.map(r=>Number(r[3]))),close:Number(group[4][4])});}return output;
}

const api={Context,score,PaperSession,aggregateSeconds};if(typeof module!=='undefined')module.exports=api;else root.KAOSMicroPaper=api;
})(typeof window!=='undefined'?window:globalThis);
