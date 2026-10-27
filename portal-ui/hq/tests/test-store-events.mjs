import assert from 'node:assert/strict';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('../js/store.js',import.meta.url),'utf8');
let serial=0;
async function transition(taskStatus, jobState) {
 const callbacks={}; let stage=0;
 globalThis.document={hidden:false,addEventListener:(k,fn)=>{callbacks[k]=fn;}};
 globalThis.sessionStorage={getItem:()=>null,setItem:()=>{}};
 globalThis.setInterval=()=>++serial; globalThis.clearInterval=()=>{};
 globalThis.fetch=async path=>({ok:true,json:async()=>path.endsWith('/tasks')?[{task_id:'TEST',status:stage?taskStatus:'ACTIVE',assigned_to:'jarvis-qa',title:'fixture'}]:{agents:[],incidents:[],engine:{active:[],recent:stage?[{id:'fixture',state:jobState,tokens_new:0}]:[]}}});
 const store=await import('data:text/javascript;base64,'+Buffer.from(source+'\n//case '+(++serial)).toString('base64'));
 const events=[]; const off=store.subscribe((s,fresh)=>events.push(...fresh));
 await new Promise(setImmediate); stage=1; callbacks.visibilitychange(); await new Promise(setImmediate); off();
 return events;
}
let failures=0;
for (const [name,status,jobState,taskSev,jobSev] of [
 ['NOT_DONE and failed are not successes','NOT_DONE','failed','info','warn'],
 ['done is successful','DONE','done','ok','ok'],
 ['cancelled is terminal but not success','CANCELLED','cancelled','info','info'],
 ['failed task warns','FAILED','error','warn','warn'],
 ['completed is successful','COMPLETED','completed','ok','ok']
]) {
 try {
  const ev=await transition(status,jobState);
  assert.equal(ev.find(e=>e.type==='task_status')?.sev,taskSev,'task severity');
  assert.equal(ev.find(e=>e.type==='job_done')?.sev,jobSev,'job severity');
  assert.ok(ev.find(e=>e.type==='job_done').text.includes(jobState),'preserve raw verdict');
  console.log('PASS',name);
 } catch(e) {failures++; console.error('FAIL',name,e.message);}
}
if(failures) process.exitCode=1;
