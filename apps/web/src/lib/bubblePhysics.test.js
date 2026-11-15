import {describe,it,expect} from 'vitest';
import {createBubbles,stepBubbles} from './bubblePhysics';
const rows=Array.from({length:100},(_,i)=>({symbol:'C'+i,market_cap:i===0?1e12:(100-i)*1e7,change_24h:(i%2?-1:1)*(i+1)/10}));
describe('interactive bubble field',()=>{
 it('restarts drifting from rest instead of settling permanently',()=>{
  const nodes=[{id:'resting',x:100,y:100,r:15,vx:0,vy:0}];
  for(let i=0;i<1800;i++)stepBubbles(nodes,500,360,1);
  expect(Math.hypot(nodes[0].vx,nodes[0].vy)).toBeGreaterThan(.1);
  const x=nodes[0].x,y=nodes[0].y;for(let i=0;i<30;i++)stepBubbles(nodes,500,360,1);
  expect(Math.hypot(nodes[0].x-x,nodes[0].y-y)).toBeGreaterThan(1);
 });
 it('keeps the full 100-coin universe bounded at mobile and desktop sizes',()=>{
  for(const [width,height] of [[300,360],[1000,620]]){
   const nodes=createBubbles(rows,{width,height});
   expect(nodes).toHaveLength(100);
   for(let i=0;i<300;i++)stepBubbles(nodes,width,height,1);
   for(const n of nodes){expect(n.x-n.r).toBeGreaterThanOrEqual(0);expect(n.x+n.r).toBeLessThanOrEqual(width);expect(n.y-n.r).toBeGreaterThanOrEqual(0);expect(n.y+n.r).toBeLessThanOrEqual(height);}
  }
 });
 it('uses absolute movement for performance sizing, including losing coins',()=>{
  const nodes=createBubbles([{symbol:'WIN',change_24h:5},{symbol:'LOSS',change_24h:-5},{symbol:'SMALL',change_24h:1}],{sizing:'performance'});
  expect(nodes.find(n=>n.item.symbol==='LOSS').r).toBe(nodes.find(n=>n.item.symbol==='WIN').r);
  expect(nodes.find(n=>n.item.symbol==='SMALL').r).toBeLessThan(nodes.find(n=>n.item.symbol==='WIN').r);
 });
 it('separates collisions and reflects boundaries while honoring the dragged node',()=>{
  const nodes=[{id:'a',x:80,y:60,r:20,vx:0,vy:0},{id:'b',x:90,y:60,r:20,vx:0,vy:0}];
  stepBubbles(nodes,300,200,0,{id:'a',x:80,y:60});
  expect(nodes[0].x).toBe(80);expect(nodes[1].x).toBeGreaterThanOrEqual(123);
  nodes[0].x=0;nodes[0].vx=-1;stepBubbles(nodes,300,200,1);
  expect(nodes[0].x).toBe(22);expect(nodes[0].vx).toBeGreaterThan(0);
 });
 it('retains zero/missing-metric coins and uses stable IDs without NaN geometry',()=>{
  const input=[{symbol:'ZERO',market_cap:0},{symbol:'MISSING',market_cap:null},{symbol:'BAD',market_cap:Infinity}];
  const a=createBubbles(input),b=createBubbles(input);
  expect(a).toEqual(b);expect(a).toHaveLength(3);
  for(const n of a)expect(Number.isFinite(n.r+n.x+n.y)).toBe(true);
 });
});
