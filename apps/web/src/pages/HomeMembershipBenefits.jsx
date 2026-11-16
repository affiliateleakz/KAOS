import React from 'react';

// Read access from the same public catalog as registration and admin plan settings.
const TOOLS=[
 ['KAOS Strategy bot',e=>e.botAccess],
 ['Strategy & risk controls',e=>e.botAccess],
 ['Paper trading',e=>e.botAccess],
 ['Community, profiles & following',e=>e.community],
 ['Market scanners & heatmaps',e=>e.scanners],
 ['AI research insights',e=>e.aiInsights],
 ['Private AI training · starts untrained',e=>e.aiTraining],
 ['Published pretrained bot models',e=>e.pretrainedModels],
 ['Cloud strategies',e=>e.cloudStrategies],
 ['Premium tools',e=>e.premiumTools],
 ['AI / Strategy + AI eligibility',e=>(e.modes||[]).includes('AI')],
];
export default function HomeMembershipBenefits({catalog}){
 if(!catalog)return null;
 const plans=catalog.plans;
 return <div className="kh-membership-details" data-testid="homepage-membership-benefits"><h3>Everything included, side by side.</h3><p>Prices and allowances come from your current KAOS membership catalog. A chart slot uses your broker’s native chart.</p><div className="kh-table-wrap"><table aria-label="Membership benefits comparison"><thead><tr><th scope="col">Membership benefits</th>{plans.map(p=><th scope="col" key={p.id}>{p.name}</th>)}</tr></thead><tbody>
 <tr><th scope="row">Broker chart slots</th>{plans.map(p=><td key={p.id}>{Math.min(4,Number(p.entitlements?.chartLimit)||1)}</td>)}</tr>
 <tr><th scope="row">Devices</th>{plans.map(p=><td key={p.id}>{Number(p.entitlements?.deviceLimit)||1}</td>)}</tr>
 {TOOLS.map(([name,included])=><tr key={name}><th scope="row">{name}</th>{plans.map(p=><td key={p.id}>{included(p.entitlements||{})?'Included':'Not included'}</td>)}</tr>)}
 <tr><th scope="row">Affiliate link & promotion toolkit</th>{plans.map(p=><td key={p.id}>Optional enrollment</td>)}</tr>
 {[0,1,2].map(level=><tr key={level}><th scope="row">Affiliate Level {level+1}</th>{plans.map(p=>{const rate=catalog.affiliateRates?.[p.tier]?.[level];return <td key={p.id}>{typeof rate==='number'?(rate?rate+'%':'Not included'):'Unavailable'}</td>;})}</tr>)}
 </tbody></table></div><p className="kh-note">AI research and AI-controlled execution are separate. AI-mode eligibility requires independent model validation and account authorization. Provider availability still applies. Paid checkout or affiliate payouts are not enabled by choosing a membership.</p></div>;
}
