import React,{useEffect,useId,useMemo,useRef,useState} from "react";
import {bubbleId,createBubbles,finite,stepBubbles} from "../lib/bubblePhysics";
import "./BubbleMap.css";

export const changeColor=change=>!finite(change)||change===0?"#6a7472":change>0?"#64cf83":"#e36a70";
const money=n=>!finite(n)?"—":new Intl.NumberFormat("en-US",{notation:"compact",maximumFractionDigits:2}).format(n);
const percent=n=>!finite(n)?"—":(n>=0?"+":"")+n.toFixed(2)+"%";
const price=n=>!finite(n)?"—":new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumSignificantDigits:8}).format(n);
const safeURL=value=>typeof value==='string'&&/^https:\/\//i.test(value)?value:null;
const periods=[["change_1h","1 hour"],["change_24h","24 hours"],["change_7d","7 days"],["change_30d","30 days"],["change_1y","1 year"]];

export default function BubbleMap({items=[],valueKey="market_cap",changeKey="change_24h",label="Market cap",emptyText="No market data available.",onSelect,sizing='value',periodLabel='Selected period',favorites=[],onToggleFavorite}){
 const host=useRef(null),svg=useRef(null),elements=useRef(new Map()),drag=useRef(null),suppressClick=useRef(false),closeButton=useRef(null);
 const [dimensions,setDimensions]=useState({width:1000,height:620});
 const [motion,setMotion]=useState(true);
 const [reducedMotion,setReducedMotion]=useState(()=>typeof window!=='undefined'&&Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches));
 const [selected,setSelected]=useState(null);
 const prefix=useId().replace(/:/g,'');
 const nodes=useMemo(()=>createBubbles(items,{...dimensions,valueKey,changeKey,sizing}),[items,valueKey,changeKey,sizing,dimensions]);
 const chosen=selected?items.find(item=>bubbleId(item)===selected):null;
 const sizeLabel=sizing==='performance'?`absolute ${periodLabel.toLowerCase()} change`:label.toLowerCase();
 const paint=()=>{for(const node of nodes)elements.current.get(node.id)?.setAttribute('transform',`translate(${node.x.toFixed(2)} ${node.y.toFixed(2)})`);};
 useEffect(()=>{
  if(!host.current)return;
  const measure=()=>{const width=Math.floor(host.current?.clientWidth||0);if(width<100)return;const height=Math.max(360,Math.min(650,Math.round(width*.64)));setDimensions(old=>old.width===width&&old.height===height?old:{width,height});};
  measure();const observer=new ResizeObserver(measure);observer.observe(host.current);return()=>observer.disconnect();
 },[]);
 useEffect(()=>{
  const media=window.matchMedia('(prefers-reduced-motion: reduce)');
  const changed=()=>setReducedMotion(media.matches);media.addEventListener('change',changed);return()=>media.removeEventListener('change',changed);
 },[]);
 useEffect(()=>{
  let frame=null,last=0,onScreen=true,disposed=false;
  const stop=()=>{if(frame!==null)cancelAnimationFrame(frame);frame=null;last=0;};
  const tick=time=>{
   frame=null;if(disposed||document.hidden||!onScreen||!motion||nodes.length<1)return;
   if(!last||time-last>=32){stepBubbles(nodes,dimensions.width,dimensions.height,(last?(time-last)/16.67:1)*(reducedMotion ? 0.25 : 1),drag.current);paint();last=time;}
   frame=requestAnimationFrame(tick);
  };
  const resume=()=>{if(disposed)return;stop();if(motion&&!document.hidden&&onScreen&&nodes.length>0)frame=requestAnimationFrame(tick);};
  document.addEventListener('visibilitychange',resume);
  const observer=new IntersectionObserver(entries=>{onScreen=entries[0]?.isIntersecting!==false;resume();});
  if(host.current)observer.observe(host.current);resume();
  return()=>{disposed=true;stop();observer.disconnect();document.removeEventListener('visibilitychange',resume);drag.current=null;};
 },[nodes,motion,reducedMotion,dimensions]); // Positions stay outside React's render loop.
 useEffect(()=>{if(chosen)closeButton.current?.focus();},[selected]);
 function select(item){setSelected(bubbleId(item));onSelect?.(item);}
 function close(){const id=selected;setSelected(null);elements.current.get(id)?.focus();}
 function point(event){const matrix=svg.current?.getScreenCTM();if(!matrix)return null;const p=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());return {x:p.x,y:p.y};}
 function pointerDown(event,node){
  if(event.button!==0)return;const p=point(event);if(!p)return;
  suppressClick.current=false;drag.current={id:node.id,x:node.x,y:node.y,offsetX:node.x-p.x,offsetY:node.y-p.y,startX:event.clientX,startY:event.clientY,moved:false};
  event.currentTarget.setPointerCapture(event.pointerId);
 }
 function pointerMove(event){
  if(!drag.current)return;const p=point(event);if(!p)return;
  if(Math.hypot(event.clientX-drag.current.startX,event.clientY-drag.current.startY)>6)drag.current.moved=true;
  Object.assign(drag.current,{x:p.x+drag.current.offsetX,y:p.y+drag.current.offsetY});stepBubbles(nodes,dimensions.width,dimensions.height,0,drag.current);paint();
 }
 function pointerEnd(){if(drag.current)suppressClick.current=drag.current.moved;drag.current=null;}
 return <div className="kaos-bubbles" data-testid="bubble-map" ref={host}>
  <div className="kaos-bubble-toolbar"><span>{nodes.length} assets · Size: {sizeLabel}</span>
   <button type="button" onClick={()=>setMotion(value=>!value)} aria-pressed={motion} aria-label="Animate bubbles">{motion?'Pause motion':'Resume motion'}</button>
  </div>
  <div className="kaos-bubble-stage">
   <svg ref={svg} viewBox={`0 0 ${dimensions.width} ${dimensions.height}`} role="group" aria-label={label+" bubble heat map"}>
    <defs>{[['gain','#07150d','#57c976'],['loss','#20090e','#db5a65'],['neutral','#141918','#78847f']].map(([name,center,edge])=>
     <radialGradient key={name} id={`${prefix}-${name}`} cx="45%" cy="42%" r="60%"><stop offset="0%" stopColor={center}/><stop offset="72%" stopColor={center}/><stop offset="100%" stopColor={edge} stopOpacity=".9"/></radialGradient>)}</defs>
    {nodes.map(node=>{
     const c=node.item,change=c[changeKey],tone=!finite(change)||change===0?'neutral':change>0?'gain':'loss';
     const font=Math.max(9,Math.min(30,node.r*.36));
     const icon=safeURL(c.image),showIcon=icon&&node.r>=26;
     return <g key={node.id} ref={el=>el?elements.current.set(node.id,el):elements.current.delete(node.id)} transform={`translate(${node.x} ${node.y})`}
       className="kaos-bubble-node" role="button" tabIndex="0" data-bubble-id={node.id} data-change={finite(change)?change:'unavailable'}
       aria-label={`${c.symbol} ${c.name||''}, ${periodLabel}: ${percent(change)}. Open details`} aria-pressed={selected===node.id}
       onPointerDown={event=>pointerDown(event,node)} onPointerMove={pointerMove} onPointerUp={pointerEnd} onPointerCancel={()=>{drag.current=null;suppressClick.current=true;}}
       onLostPointerCapture={pointerEnd} onClick={()=>{if(!suppressClick.current)select(c);suppressClick.current=false;}}
       onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(c);}}}>
      <title>{`${c.symbol} · ${periodLabel}: ${percent(change)} · ${label}: ${money(c[valueKey])}`}</title>
      <circle className="kaos-bubble-edge" r={node.r} fill={`url(#${prefix}-${tone})`} stroke={changeColor(change)} strokeWidth="1.7"/>
      {showIcon&&<image href={icon} x={-Math.min(16,node.r*.18)} y={-node.r*.64} width={Math.min(32,node.r*.36)} height={Math.min(32,node.r*.36)} pointerEvents="none" onError={event=>{event.currentTarget.style.display='none';}}/>}
      <text y={showIcon?node.r*.06:-node.r*.12} textAnchor="middle" dominantBaseline="middle" fontSize={font} fontWeight="650">{String(c.symbol||'').slice(0,node.r<16?2:node.r<26?4:9)}</text>
      {node.r>=19&&<text y={node.r*.4} textAnchor="middle" dominantBaseline="middle" fontSize={Math.max(9,font*.63)}>{percent(change)}</text>}
      {favorites.includes(node.id)&&<text x={node.r*.55} y={-node.r*.55} textAnchor="middle" fontSize="13">★</text>}
     </g>;
    })}
   </svg>
  </div>
  {!nodes.length&&<p className="kaos-bubble-help">{emptyText}</p>}
  <p className="kaos-bubble-help">Drag to move · Select a bubble for details · Green = gain, red = loss, grey = zero / unavailable. Bubble sizes use {sizeLabel}, with display limits for readability.</p>
  {chosen&&<section className="kaos-bubble-details" data-testid="bubble-detail" aria-label="Asset details" onKeyDown={event=>{if(event.key==='Escape')close();}}>
   <header><div><h3>{chosen.symbol} · {chosen.name||chosen.symbol}</h3><p>{periodLabel}: {percent(chosen[changeKey])}</p></div><button ref={closeButton} type="button" aria-label="Close asset details" onClick={close}>×</button></header>
   <dl><div><dt>Price</dt><dd>{price(chosen.price_usd??chosen.price)}</dd></div><div><dt>{label}</dt><dd>{money(chosen[valueKey])}</dd></div>
    {periods.map(([key,text])=><div key={key}><dt>{text}</dt><dd style={{color:changeColor(chosen[key])}}>{percent(chosen[key])}</dd></div>)}
   </dl>
   {onToggleFavorite&&<button type="button" className="mt-4" onClick={()=>onToggleFavorite(bubbleId(chosen))}>{favorites.includes(bubbleId(chosen))?'Remove from watchlist':'Add to watchlist'}</button>}
   {safeURL(chosen.url)&&<div><a href={chosen.url} target="_blank" rel="noopener noreferrer">Open {chosen.source||'data source'} ↗</a></div>}
  </section>}
 </div>;
}
