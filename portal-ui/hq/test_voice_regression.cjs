const fs=require('fs'),vm=require('vm'),assert=require('assert');
let src=fs.readFileSync('js/voice.js','utf8').replace(/^import .*;\r?\n/gm,'').replace(/export /g,'');
src+='\n globalThis.testAPI={V,setWake,talkOnce,onFinal,stopRec};';
const recs=[],timers=[],storage=new Map();
class SR{constructor(){recs.push(this)}start(){}abort(){}}
const c={console,window:{SpeechRecognition:SR},speechSynthesis:{cancel(){},getVoices(){return[]}},
 navigator:{mediaDevices:{getUserMedia:()=>Promise.reject(Error('no hardware'))}},
 localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},confirm:()=>true,
 setTimeout:(f,ms)=>{timers.push({f,ms});return timers.length},clearTimeout(){},
 toast(){}, S:{agents:[],tasks:[],incidents:[]},ROSTER:[],agentState(){},isFresh(){},shortName:x=>x,
 refresh:async()=>{}, voiceAsk:async()=>{throw Error('must not call cloud')},Date,Set,Math,SpeechSynthesisUtterance:class{},
 // neuere Importe von voice.js (lokale Stimme, Engine, Aufträge, Qwen) als neutrale Attrappen; hier wird nur der Browser-Erkennungspfad geprüft
 LOCAL_VOICE:'local',LocalEar:class{},localHealth:async()=>({ok:false}),playLocal:()=>()=>{},unlockAudio(){},transcribeWav:async()=>'',
 stripWake:t=>t,qwenChat:async()=>{throw Object.assign(Error('off'),{state:'off'})},warmChat:async()=>'off',handleTaskVoice:async()=>null,speechChunks:t=>[t]};
vm.createContext(c);vm.runInContext(src,c);
(async()=>{
 const a=c.testAPI;await a.setWake(true);let r=recs.at(-1);
 assert.equal(r.continuous,false);assert.equal(r.interimResults,true);assert.equal(r.lang,'de-DE');
 console.log('PASS recognition configuration incl interimResults');
 r.onresult({resultIndex:0,results:[Object.assign([{transcript:'Das Wetter ist schoen'}],{isFinal:true})]});
 assert.equal(a.V.transcript.length,0);assert.equal(a.V.state,'wake');console.log('PASS no wakeword: discarded, no cloud call');
 r.onresult({resultIndex:0,results:[Object.assign([{transcript:'Jarvis'}],{isFinal:true})]});
 assert.equal(a.V.state,'listening');console.log('PASS standalone wakeword opens command window');
 r.onend();assert(timers.some(t=>t.ms===120));console.log('PASS regular end schedules short restart');
 await a.setWake(false);assert.equal(a.V.enabled,false);assert.equal(a.V.state,'off');console.log('PASS explicit off disables wake');
 await a.setWake(true);r=recs.at(-1);r.onerror({error:'not-allowed'});
 assert.equal(a.V.enabled,false);assert.equal(a.V.state,'off');console.log('PASS denied permission fails closed');
 console.log('6 regression groups passed (mocked recognition; not a hardware E2E)');
})().catch(e=>{console.error(e);process.exitCode=1});
