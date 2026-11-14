// Browser regression fixtures only: no real accounts, broker connections or orders.
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const {spawn}=require('node:child_process');
const root=path.resolve(__dirname,'../..');
const mime={'.js':'application/javascript','.css':'text/css','.html':'text/html','.png':'image/png','.jpg':'image/jpeg','.ico':'image/x-icon','.json':'application/json'};
async function serve(folder,spa=false){
 const server=http.createServer((req,res)=>{
  const pathname=new URL(req.url,'http://localhost').pathname;
  let file=path.resolve(folder,'.'+decodeURIComponent(pathname));
  if(!file.startsWith(folder+path.sep)&&file!==folder){res.writeHead(403);res.end();return;}
  if(!fs.existsSync(file)||fs.statSync(file).isDirectory())file=spa?path.join(folder,'index.html'):'';
  if(!file){res.writeHead(404);res.end();return;}
  res.setHeader('content-type',mime[path.extname(file)]||'application/octet-stream');
  fs.createReadStream(file).pipe(res);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 return {server,url:'http://127.0.0.1:'+server.address().port};
}
function check(name,env){return new Promise((resolve,reject)=>{
 const child=spawn(process.execPath,[path.join(__dirname,name)],{env,stdio:'inherit'});
 child.on('error',reject);child.on('exit',code=>code===0?resolve():reject(Error(name+' failed: '+code)));
});}
(async()=>{
 const web=await serve(path.join(root,'apps/web/build'),true);
 const ext=await serve(path.join(root,'apps/extension'));
 const chrome=process.env.CHROME_BIN || ['/usr/bin/chromium','/usr/bin/google-chrome','/opt/google/chrome/chrome'].find(file=>fs.existsSync(file));
 const env={...process.env,KAOS_WEB_PREVIEW_URL:web.url,KAOS_EXTENSION_PREVIEW_URL:ext.url,...(chrome?{CHROME_BIN:chrome}:{})};
 try{for(const name of ['auth_login.cjs','extension_charts.cjs','content_candles.cjs'])await check(name,env);}
 finally{web.server.close();ext.server.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
