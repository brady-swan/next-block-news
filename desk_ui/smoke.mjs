// Read-only production acceptance. Never writes Typefully, invokes models or logs access URLs.
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const raw=await readFile(process.env.NBN_DESK_LINK_FILE||'../DESK-REPORT-URL.txt','utf8');
const link=new URL(raw.match(/https?:\/\/[^\s<>]+/)[0]);
const token=link.searchParams.get('k');
assert.ok(token,'Private access link is required');
const url=(path,params={})=>{const u=new URL(path,link.origin);u.searchParams.set('k',token);for(const[k,v]of Object.entries(params))u.searchParams.set(k,v);return u.href};
const summary={routes:[],views:[],screenshots:[]};
const safeError=e=>String(e.message||e).replaceAll(token,'[redacted]').slice(0,500);
try{
 for(const path of ['/desk','/desk/intake','/desk/runs','/desk/outputs','/desk/system','/report','/desk/system-guide.pdf']){
  const response=await fetch(url(path));assert.equal(response.status,200,path);summary.routes.push(path);
 }
 for(const name of ['workspace.js','workspace.css']){
  const response=await fetch(url('/desk/assets/'+name));assert.equal(response.status,200,name);
  const digest=crypto.createHash('sha256').update(Buffer.from(await response.arrayBuffer())).digest('hex');
  const manifest=JSON.parse(await readFile('../nbn/desk_assets/workspace-manifest.json','utf8'));
  assert.equal(digest,manifest[name],name+' exact release bytes');
 }
 for(const view of ['newsroom','intake','outputs','system']){
  const started=performance.now(),response=await fetch(url('/desk/api/workspace',{view}));
  assert.equal(response.status,200,view);const data=await response.json();assert.equal(data.version,1);
  assert.ok(!JSON.stringify(data).includes(token),'Access token excluded');
  summary.views.push({view,ms:Math.round(performance.now()-started),run:data.run?.run_id,artifacts:data.run?.artifacts.length,sources:data.sources?.length,outputs:data.outputs?.length});
  if(view==='intake'){
   assert.ok(data.items.every(i=>i.reconsider && Number.isInteger(i.reconsider.latest_action_id)),'Owner queue projection present');
   summary.reconsider={eligible:data.items.filter(i=>i.reconsider.eligible).length,queued:data.items.filter(i=>i.reconsider.request?.state==='queued').length};
  }
  if(view==='system'){assert.equal(data.now.autopost,false,'Autopost remains off');assert.equal(data.roster.seats.find(s=>s.role==='Daily receipt audit').mode,'disabled');summary.roster=data.roster.seats.map(({role,model,effort,mode})=>({role,model,effort,mode}));summary.worker=data.now.worker;summary.costs=data.costs.periods;}
  if(view==='newsroom'){
   summary.selected_run=data.run?.run_id;summary.run_status=data.run?.status;summary.packet_recorded=data.run?.packet_recorded;
   if(data.navigation.older){const r=await fetch(url('/desk/api/workspace',{view,run:data.navigation.older}));assert.equal(r.status,200);assert.equal((await r.json()).navigation.newer,data.run.run_id);}
  }
 }
 assert.equal((await fetch(new URL('/desk/api/workspace',link.origin))).status,403,'API rejects missing key');
 const req=createRequire(process.env.NBN_QA_RUNTIME||'/Users/brady/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json');
 const {chromium}=req('playwright');const browser=await chromium.launch({headless:true,channel:'chrome'});
 const page=await browser.newPage({viewport:{width:1728,height:1117}});const errors=[],writes=[];
 page.on('request',r=>{if(r.method()!=='GET')writes.push(r.method())});
 page.on('pageerror',e=>errors.push(safeError(e)));await mkdir('outputs/production',{recursive:true});
 try{
  await page.goto(url('/desk'));await page.locator('.run-summary').waitFor();await page.waitForTimeout(300);
  assert.equal(new URL(page.url()).searchParams.get('k'),token);
  for(const width of [390,1024,1728,2560]){
   await page.setViewportSize({width,height:1000});await page.waitForTimeout(250);
   const close=page.getByRole('button',{name:'Close story detail',exact:true});if(await close.isVisible())await close.click();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No overflow '+width);
   await page.screenshot({path:`outputs/production/newsroom-${width}.png`,fullPage:true});summary.screenshots.push('newsroom-'+width);
  }
  for(const view of ['system','outputs','intake']){await page.goto(url('/desk',{view}));await page.locator('.support-view').waitFor();await page.screenshot({path:`outputs/production/${view}.png`,fullPage:true});summary.screenshots.push(view);}
  assert.equal(errors.length,0,errors.join('; '));summary.browser_errors=errors.length;
  assert.deepEqual(writes,[],'Smoke never submits owner actions');summary.browser_writes=0;
 }finally{await browser.close()}
 await writeFile('outputs/production/smoke.json',JSON.stringify(summary,null,2));console.log(JSON.stringify(summary,null,2));
}catch(e){console.error(safeError(e));process.exitCode=1}
