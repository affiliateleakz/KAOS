export function campaignLink(link, channel) {
  const url = new URL(link);
  url.searchParams.set('utm_source', channel);
  url.searchParams.set('utm_medium', 'affiliate');
  url.searchParams.set('utm_campaign', 'kaos_member');
  return url.href;
}

export function marketingCopy(link) {
  const disclosure = 'Disclosure: I am a KAOS affiliate and may receive a commission if you purchase through my link.';
  return [
    {id:'welcome', type:'Email', title:'Introduce your audience to KAOS', subject:'Your bot. Your data. Your KAOS.',
      body:`Hi [First name],\n\nIf you want a trading workspace that keeps charts, strategy controls and research together, take a look at KAOS. Try the 7-day Pro free trial, explore the interface and decide whether the available paid tools fit your workflow.\n\nExplore KAOS: ${campaignLink(link,'email_welcome')}\n\nTrading involves risk. Tools and past results do not guarantee future returns.\n\n${disclosure}\n\n[Your name]\n[Your mailing address]\nUnsubscribe: [your unsubscribe link]`},
    {id:'research', type:'Email', title:'Share your research workflow', subject:'A closer look at the KAOS trading workspace',
      body:`Hi [First name],\n\nA good workflow starts with organized information. KAOS brings chart controls, strategy tools and membership-based research features into one account. Review the current plans and supported integrations to see what fits your needs.\n\nTake a look: ${campaignLink(link,'email_research')}\n\nI recommend exploring the tools and practicing on a demo account before considering real-money trading. Trading can result in losses.\n\n${disclosure}\n\n[Your name]\n[Your mailing address]\nUnsubscribe: [your unsubscribe link]`},
    {id:'social', type:'Social', title:'Short social post', body:`Your bot. Your data. Your KAOS. Explore the KAOS trading workspace and try the 7-day Pro free trial: ${campaignLink(link,'social')}\n\nTrading involves risk; no returns are guaranteed. ${disclosure}`},
    {id:'community', type:'Community', title:'Community introduction', body:`For anyone comparing trading tools: KAOS offers a chart and strategy workspace with a 7-day Pro free trial and paid memberships. Check the currently supported features and choose what fits your process: ${campaignLink(link,'community')}\n\nTrading is risky. This is not a promise of results. ${disclosure}`},
  ];
}

export const BANNER_FORMATS = [
  {name:'Social landscape',width:1200,height:628},
  {name:'Square post',width:1080,height:1080},
  {name:'Website leaderboard',width:728,height:90},
];

export async function downloadBanner(format) {
  const canvas = document.createElement('canvas');canvas.width=format.width;canvas.height=format.height;
  const ctx=canvas.getContext('2d');const image=new Image();image.src='/kaos-cinematic-header.jpg';
  await image.decode();
  ctx.fillStyle='#080808';ctx.fillRect(0,0,canvas.width,canvas.height);
  const scale=Math.max(canvas.width/image.width,canvas.height/image.height);
  ctx.drawImage(image,(canvas.width-image.width*scale)/2,(canvas.height-image.height*scale)/2,image.width*scale,image.height*scale);
  ctx.fillStyle='rgba(0,0,0,.78)';ctx.fillRect(0,0,canvas.width,canvas.height);
  const small=format.height<200,pad=small?24:60;
  ctx.strokeStyle='#d4af37';ctx.lineWidth=2;ctx.strokeRect(4,4,canvas.width-8,canvas.height-8);
  ctx.fillStyle='#e8c46f';ctx.font=`bold ${small?26:74}px Georgia`;ctx.fillText('KAOS TRADING',pad,small?40:pad+85);
  ctx.fillStyle='#f3ead8';ctx.font=`${small?14:34}px Arial`;
  ctx.fillText('Your bot. Your data. Your KAOS.',pad,small?64:pad+150);
  if(!small){ctx.fillStyle='#c4b89f';ctx.font='24px Arial';ctx.fillText('Explore the workspace. Start with free membership.',pad,canvas.height-130);ctx.font='18px Arial';ctx.fillText('Trading involves risk. No guaranteed returns.',pad,canvas.height-65);}
  const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw Error('Banner export failed');
  const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`kaos-${format.width}x${format.height}.png`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
