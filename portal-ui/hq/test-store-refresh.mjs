import assert from 'node:assert/strict';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('./js/store.js',import.meta.url),'utf8');
const realTimeout=globalThis.setTimeout;
globalThis.setTimeout=(fn,ms,...args)=>realTimeout(fn,ms===6000?25:ms,...args);
let serial=0;
async function setup(){
 globalThis.document={hidden:false,addEventListener:()=>{}};
 globalThis.sessionStorage={getItem:()=>null,setItem:()=>{}};
 globalThis.setInterval=()=>++serial;globalThis.clearInterval=()=>{};
 let mode='ok',calls=0,version=1;
 globalThis.fetch=async path=>{if(path==='/api/jarvis')return {ok:true,json:async()=>({ok:true,data:{agents:{},events:[],last_id:0}})};calls++;if(mode==='error')throw Error('fixture offline');if(mode==='hang')return new Promise(()=>{});return {ok:true,json:async()=>path.endsWith('/tasks')?[{task_id:'T'+version,status:'ACTIVE'}]:{agents:[],incidents:[],engine:{active:[],recent:[]}}};};
 const store=await import('data:text/javascript;base64,'+Buffer.from(source+'\n//'+(++serial)).toString('base64'));
 const off=store.subscribe(()=>{});await new Promise(setImmediate);
 return {store,off,setMode:m=>{mode=m;version++;},calls:()=>calls};
}
let fail=0;
for(const [name,test] of [
 ['refresh forces fresh data while already subscribed',async x=>{x.setMode('ok');assert.equal(await x.store.refresh(),true);assert.equal(x.store.S.tasks[0].task_id,'T2');assert.equal(x.calls(),4);}],
 ['offline refresh returns failure instead of cached success',async x=>{x.setMode('error');assert.equal(await x.store.refresh(),false);assert.match(x.store.S.error,/offline/);}],
 ['concurrent refresh shares one poll',async x=>{x.setMode('ok');assert.deepEqual(await Promise.all([x.store.refresh(),x.store.refresh()]),[true,true]);assert.equal(x.calls(),4);}],
 ['timeout returns failure',async x=>{x.setMode('hang');assert.equal(await x.store.refresh(),false);}]
]){const x=await setup();try{await test(x);console.log('PASS',name);}catch(e){fail++;console.error('FAIL',name,e.message);}finally{x.off();}}
if(fail)process.exitCode=1;
