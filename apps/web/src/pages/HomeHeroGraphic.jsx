import React from 'react';
import {Link} from 'react-router-dom';
import './HomeHeroGraphic.css';

const nav=[['Home','#top',33,5.5],['Features','#features',39.5,7],['Pricing','#pricing',47,6.5],['Results','#results',54,6.5],['FAQ','#faq',60.5,5]];
const cards=[
 {id:'bot',title:'BOT CONTROLS',subtitle:'YOUR CURRENT KAOS EXTENSION',image:'bot-controls',alt:'Actual KAOS extension Bot controls and broker chart selection'},
 {id:'strategy',title:'KAOS STRATEGY',subtitle:'YOUR STRATEGY WORKSPACE',image:'strategy',alt:'Actual KAOS Strategy editor in the current extension'},
 {id:'heatmap',title:'KAOS WEBSITE',subtitle:'RESEARCH · HEATMAPS · COMMUNITY',image:'heatmap',alt:'Actual KAOS website crypto heatmap and member navigation'},
];
export default function HomeHeroGraphic({freeLink,onPreview}){
 return <>
 <section id="kx-hero" className="kh-reference-hero" aria-labelledby="home-title">
  <h1 id="home-title" className="sr-only">KAOS TRADING BOT</h1>
  <img className="kh-reference-art" src="/kaos-approved-hero.png" alt="KAOS Trading gold Viking and mountain artwork with framed product previews" width="1671" height="941" fetchPriority="high"/>
  <nav aria-label="Homepage navigation" className="kh-reference-nav">
   {nav.map(([name,href,left,width])=><a aria-label={name} key={name} href={href} style={{left:left+'%',width:width+'%',top:'1%',height:'5.5%'}}/>)}
   <Link aria-label="Login" to="/login" style={{left:'73.4%',width:'8.2%',top:'1.2%',height:'5.1%'}}/>
   <Link aria-label="Get KAOS" to="/register" style={{left:'82.8%',width:'12.5%',top:'1.2%',height:'5.1%'}}/>
   <a aria-label="Download KAOS Bot from the official Chrome Web Store listing" href="https://chromewebstore.google.com/detail/gbobopmnjgeeegniphckfpalhnebapjm" target="_blank" rel="noopener noreferrer" style={{left:'11.7%',width:'30.6%',top:'53.4%',height:'6.8%'}}/>
  </nav>
  <div className="kh-reference-main" data-testid="homepage-current-product-images">
   <a href="#kaos-bot" onClick={()=>onPreview('radar')} className="kh-reference-site" aria-label="Explore the current KAOS website"><span>KAOS WEBSITE · OPPORTUNITY RADAR</span><img src="/product-previews/radar.png" alt="Current KAOS website opportunity radar with labeled example research data" width="1440" height="960"/></a>
   <a href="#kaos-bot" onClick={()=>onPreview('bot')} className="kh-reference-bot" aria-label="Explore the current KAOS extension"><span>KAOS BOT · BROKER COMPANION</span><img src="/product-previews/bot-controls.png" alt="Current KAOS extension controls — demo account, bot stopped, four broker chart slots selected"/></a>
   <a href="#kaos-bot" onClick={()=>onPreview('heatmap')} className="kh-reference-heatmap" aria-label="Explore the current KAOS website heatmap"><span>WEBSITE HEATMAP</span><img src="/product-previews/heatmap.png" alt="Current KAOS website animated crypto bubbles — labeled example market data" width="1440" height="960"/></a>
   <small>ACTUAL KAOS INTERFACES · LABELED EXAMPLE DATA</small>
  </div>
  <div className="kh-reference-cards">{cards.map(card=><article className={'kh-reference-card kh-reference-card-'+card.id} key={card.id}><div className="kh-reference-card-title"><h2>{card.title}</h2><p>{card.subtitle}</p></div><a href="#kaos-bot" onClick={()=>onPreview(card.id)} aria-label={'Explore '+card.title}><img src={'/product-previews/'+card.image+'.png'} alt={card.alt+' — example data'}/></a></article>)}</div>
 </section>
 <div className="kh-reference-caption"><p>Current KAOS extension and website · labeled example data · charts remain on your broker · no performance results claimed.</p><div><Link className="kh-button" to={freeLink}>7-day free trial</Link><a href="#pricing" className="kh-button kh-button-outline">Memberships & benefits</a><a href="#affiliate" className="kh-button kh-button-outline">Affiliate earnings</a><Link to="/follow-us" className="kh-button kh-button-outline">Follow Us</Link></div></div>
 </>;
}
