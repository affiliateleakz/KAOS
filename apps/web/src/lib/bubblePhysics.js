// Bounded, deterministic initialization and client-only collision simulation.
export const finite = value => typeof value === 'number' && Number.isFinite(value);
export const bubbleId = item => `${item.chain || item.source || ''}:${item.id || item.symbol || ''}:${item.pair_address || item.url || item.name || ''}`;
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
function seedFor(text) { let seed=2166136261; for(const ch of text) seed=Math.imul(seed^ch.charCodeAt(0),16777619); return seed>>>0; }
function random(seed) { let state=seed||1; return ()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state/4294967296;}; }

export function createBubbles(items, {width=1000,height=620,valueKey='market_cap',changeKey='change_24h',sizing='value'}={}) {
 const seen=new Set();
 const rows=items.filter(item=>{const id=bubbleId(item);if(seen.has(id))return false;seen.add(id);return true;}).slice(0,100).map(item=>{
  const raw=sizing==='performance'?(finite(item[changeKey])?Math.abs(item[changeKey]):0):item[valueKey];
  return {item,id:bubbleId(item),weight:finite(raw)&&raw>0?raw:0};
 });
 if(!rows.length)return [];
 const total=rows.reduce((sum,row)=>sum+row.weight,0);
 const minimum=Math.max(9,Math.min(19,Math.sqrt(width*height/(rows.length*Math.PI))*0.36));
 const maximum=Math.min(width,height)*0.25;
 const nodes=rows.map(row=>({...row,r:clamp(total?Math.sqrt(row.weight/total*width*height*0.46/Math.PI):minimum,minimum,maximum)})).sort((a,b)=>b.r-a.r);
 const placed=[];
 for(const node of nodes){
  const rand=random(seedFor(node.id)),r=node.r+3;
  let best=null,bestScore=-Infinity;
  for(let attempt=0;attempt<240;attempt++){
   const x=r+rand()*(width-2*r),y=r+rand()*(height-2*r);
   const score=placed.reduce((score,p)=>Math.min(score,Math.hypot(p.x-x,p.y-y)-p.r-node.r-3),Infinity);
   if(score>bestScore){bestScore=score;best={x,y};}
   if(score>=0)break;
  }
  node.x=best.x;node.y=best.y;node.vx=(rand()-.5)*0.7;node.vy=(rand()-.5)*0.7;node.phase=rand()*Math.PI*2;placed.push(node);
 }
 for(let i=0;i<45;i++)stepBubbles(nodes,width,height,0,null);
 return nodes;
}

export function stepBubbles(nodes,width,height,delta=1,drag=null){
 const dt=clamp(delta,0,2);
 for(const n of nodes){
  if(drag?.id===n.id){n.x=drag.x;n.y=drag.y;n.vx=0;n.vy=0;}
  else{n.x+=n.vx*dt;n.y+=n.vy*dt;}
 }
 for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
  const a=nodes[i],b=nodes[j],dx=b.x-a.x,dy=b.y-a.y;
  const distance=Math.hypot(dx,dy),required=a.r+b.r+3;
  if(distance>=required)continue;
  const nx=distance>0.001?dx/distance:1,ny=distance>0.001?dy/distance:0;
  const overlap=required-distance;
  const aFixed=drag?.id===a.id,bFixed=drag?.id===b.id;
  if(!aFixed){a.x-=nx*overlap*(bFixed?1:.5);a.y-=ny*overlap*(bFixed?1:.5);}
  if(!bFixed){b.x+=nx*overlap*(aFixed?1:.5);b.y+=ny*overlap*(aFixed?1:.5);}
  const approach=(b.vx-a.vx)*nx+(b.vy-a.vy)*ny;
  if(approach<0){if(!aFixed){a.vx+=approach*nx*.85;a.vy+=approach*ny*.85;}if(!bFixed){b.vx-=approach*nx*.85;b.vy-=approach*ny*.85;}}
 }
 for(const n of nodes){
  const left=n.r+2,right=width-n.r-2,top=n.r+2,bottom=height-n.r-2;
  if(n.x<left){n.x=left;n.vx=Math.abs(n.vx);}if(n.x>right){n.x=right;n.vx=-Math.abs(n.vx);}
  if(n.y<top){n.y=top;n.vy=Math.abs(n.vy);}if(n.y>bottom){n.y=bottom;n.vy=-Math.abs(n.vy);}
  // Gentle energy keeps the field drifting after collisions dissipate momentum.
  if(dt>0&&drag?.id!==n.id){
   n.phase=(n.phase||0)+.009*dt;n.vx+=Math.cos(n.phase)*.003*dt;n.vy+=Math.sin(n.phase)*.003*dt;
   if(Math.hypot(n.vx,n.vy)<.14){n.vx=Math.cos(n.phase)*.18;n.vy=Math.sin(n.phase)*.18;}
  }
  n.vx=clamp(n.vx,-.8,.8);n.vy=clamp(n.vy,-.8,.8);
 }
 return nodes;
}
