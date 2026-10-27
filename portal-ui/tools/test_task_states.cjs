const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('js/store.js','utf8').replace(/export /g,'')+'\nglobalThis.T={S,agentState};';
const c={console,document:{addEventListener(){}},sessionStorage:{getItem(){return null}},setInterval(){},clearInterval(){},setTimeout(){},fetch(){},Set,Date};
vm.createContext(c);vm.runInContext(src,c);
for(const status of ['CANCELLED','ARCHIVED','FAILED','DONE','COMPLETED','CLOSED']){
 c.T.S.tasks=[{task_id:'probe',assigned_to:'jarvis-core',status}];
 assert.equal(c.T.agentState('jarvis-core').open.length,0,`${status} must not count as open`);
}
for(const status of ['ACTIVE','PLANNING','INBOX','BLOCKED','NOT_DONE']){
 c.T.S.tasks=[{task_id:'probe',assigned_to:'jarvis-core',status}];
 assert.equal(c.T.agentState('jarvis-core').open.length,1,`${status} must remain open`);
}
for(const name of ['cc.js','hq.js','voice.js']){
 const s=fs.readFileSync('js/'+name,'utf8');
 assert(s.includes('CANCELLED')&&s.includes('ARCHIVED')&&s.includes('FAILED'),name+' must recognize terminal states');
}
console.log('PASS terminal/open status semantics in shared store and all consuming views');
