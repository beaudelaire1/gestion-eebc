const {chromium}=require('C:/Users/vilme/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs');
const out=__dirname;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 let axe;try{axe=await (await fetch('https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js')).text()}catch(e){}
 const results=[];
 for(const mode of ['desktop','mobile']){
  const ctx=await browser.newContext({viewport:mode==='desktop'?{width:1440,height:1000}:{width:390,height:844},deviceScaleFactor:1,isMobile:mode==='mobile',hasTouch:mode==='mobile'});
  for(const path of ['/','/nos-eglises/','/contact/','/inscription/','/don/','/evenements/','/actualites/','/carte/','/app/accounts/login/']){
   const page=await ctx.newPage();const errors=[],bad=[],net=[];
   page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)bad.push({url:r.url(),status:r.status()});net.push({url:r.url(),status:r.status(),bytes:r.headers()['content-length']})});
   await page.addInitScript(()=>{window.__audit={lcp:0,cls:0};try{new PerformanceObserver(l=>{for(const e of l.getEntries())window.__audit.lcp=e.startTime}).observe({type:'largest-contentful-paint',buffered:true});new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.__audit.cls+=e.value}).observe({type:'layout-shift',buffered:true})}catch(e){}});
   try{
    const response=await page.goto('https://eglise-ebc.org'+path,{waitUntil:'load',timeout:45000});await page.waitForTimeout(1800);
    const data=await page.evaluate(()=>({title:document.title,description:document.querySelector('meta[name=description]')?.content,canonical:document.querySelector('link[rel=canonical]')?.href,robots:document.querySelector('meta[name=robots]')?.content,h1:[...document.querySelectorAll('h1')].map(x=>x.textContent.trim()),headings:[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(x=>({tag:x.tagName,text:x.textContent.trim()})),overflow:document.documentElement.scrollWidth>innerWidth,bodyHeight:document.body.scrollHeight,text:document.body.innerText.slice(0,18000),images:[...document.images].map(x=>({src:x.currentSrc,alt:x.alt,width:x.naturalWidth,height:x.naturalHeight,loading:x.loading,renderWidth:x.width,complete:x.complete})),timing:performance.getEntriesByType('navigation')[0]?.toJSON(),vitals:window.__audit,resources:performance.getEntriesByType('resource').map(x=>({url:x.name,bytes:x.transferSize,duration:x.duration})),jsonld:[...document.querySelectorAll('script[type="application/ld+json"]')].map(x=>{try{return JSON.parse(x.textContent)}catch(e){return {error:e.message}}}),links:[...document.querySelectorAll('a[href]')].map(x=>({text:x.textContent.trim(),href:x.href}))}));
    const name=mode+(path==='/'?'home':path.replaceAll('/','_'));
    await page.screenshot({path:out+'/'+name+'.png',fullPage:path!=='/'});
    let violations=[];if(axe){await page.addScriptTag({content:axe});const a=await page.evaluate(async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','best-practice']}}));violations=a.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,help:v.help,helpUrl:v.helpUrl,nodes:v.nodes.map(n=>({target:n.target,html:n.html,summary:n.failureSummary}))}));}
    results.push({mode,path,status:response.status(),headers:await response.allHeaders(),...data,errors,bad,network:net,violations});
    console.log(mode,path,response.status(),JSON.stringify({lcp:data.vitals.lcp,cls:data.vitals.cls,overflow:data.overflow,violations:violations.map(v=>[v.id,v.nodes.length]),bad:bad.length}));
   }catch(e){results.push({mode,path,error:e.message});console.log(mode,path,e.message)}
   fs.writeFileSync(out+'/live.json',JSON.stringify(results,null,2));await page.close();
  }await ctx.close();
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
