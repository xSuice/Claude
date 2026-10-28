import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {speechChunks} from './js/speech-text.js';
async function boot(){
 const audio=[],requests=[],instances=[],timers=new Map();let id=0;
 class Rec{constructor(){instances.push(this)}start(){}abort(){}}
 globalThis.window={SpeechRecognition:Rec,speechSynthesis:{}};
 globalThis.SpeechSynthesisUtterance=class{constructor(t){this.text=t}};
 globalThis.speechSynthesis={getVoices:()=>[],cancel(){},speak(u){audio.push(u)}};
 globalThis.localStorage={getItem:()=>null,setItem(){}};
 globalThis.__deps={speechChunks,toast(){},S:{tasks:[],incidents:[],agents:[]},agentState(){return {status:'idle',open:[]}},isFresh:()=>true,shortName:s=>s,refresh:async()=>true,ROSTER:[],handleTaskVoice:async()=>null,voiceAsk:async p=>{requests.push(p);return 'Lass uns das zusammen anschauen.'}};
 let s=fs.readFileSync(new URL('./js/voice.js',import.meta.url),'utf8').replace(/^import .*;\r?$/gm,'');
 s='const {speechChunks,toast,S,agentState,isFresh,shortName,refresh,ROSTER,voiceAsk,handleTaskVoice}=globalThis.__deps;\n'+s;
 const saved={setTimeout:globalThis.setTimeout,clearTimeout:globalThis.clearTimeout};
 globalThis.setTimeout=(f,ms)=>{timers.set(++id,{f,ms});return id};globalThis.clearTimeout=i=>timers.delete(i);
 const m=await import('data:text/javascript;base64,'+Buffer.from(s+'//'+Math.random()).toString('base64'));
 return {m,audio,requests,instances,timers,cleanup(){m.stopAll();Object.assign(globalThis,saved)}};
}
test('a free-form sentence about a task is not replaced by the task counter',async()=>{
 const b=await boot();try{assert.equal(b.m.answerLocal('Ich möchte mit dir über meinen Auftrag reden'),null)}finally{b.cleanup()}
});
test('free conversation is not hijacked by error or status keywords',async()=>{
 const b=await boot();try{
  for(const text of ['Erzähle eine Geschichte über einen Fehler','Ich finde deine Zusammenfassung zu robotisch','Lass uns über Probleme beim Modding sprechen'])assert.equal(b.m.answerLocal(text),null,text);
  assert.ok(b.m.answerLocal('Gibt es Alarme?'));
  assert.ok(b.m.answerLocal('Wie ist die Lage?'));
  assert.ok(b.m.answerLocal('Welche Aufgaben sind offen?'));
 }finally{b.cleanup()}
});
test('wake conversation waits for a followup after speaking without another wakeword',async()=>{
 const b=await boot();try{
  b.m.V.enabled=true;
  await b.m.sayText('Jarvis, erzähl mir etwas Interessantes');
  for(let i=0;i<b.audio.length;i++)b.audio[i].onend();
  assert.equal(b.m.V.state,'listening');
  assert.ok([...b.timers.values()].some(x=>x.ms===12000));
 }finally{b.cleanup()}
});
test('recognizer restart preserves followup expiry',async()=>{
 const b=await boot();try{
  b.m.V.enabled=true;await b.m.sayText('Erzähle mir etwas Interessantes');
  for(let i=0;i<b.audio.length;i++)b.audio[i].onend();
  const rec=b.instances.at(-1);rec.onend();
  const restart=[...b.timers.values()].find(x=>x.ms===120);assert.ok(restart);restart.f();
  assert.ok([...b.timers.values()].some(x=>x.ms===12000));
 }finally{b.cleanup()}
});
test('followup has a bounded recent conversation context and stop closes listening',async()=>{
 const b=await boot();try{
  b.m.V.speakOn=false;
  await b.m.sayText('Erzähle mir etwas über Minecraft');
  await b.m.sayText('Und wie funktioniert das genau?');
  assert.ok(b.requests[1].includes('Erzähle mir etwas über Minecraft'));
  b.m.stopAll();assert.notEqual(b.m.V.state,'listening');
 }finally{b.cleanup()}
});

test('spoken fillers in front of a follow-up still reach the local intent',async()=>{
 const b=await boot();try{
  assert.ok(b.m.answerLocal('und welche Aufgaben sind offen?'));
  assert.ok(b.m.answerLocal('Also, wie ist die Lage?'));
  assert.ok(b.m.answerLocal('Äh, gibt es Alarme?'));
  assert.equal(b.m.answerLocal('und dann erzähl mir einen Witz'),null);
 }finally{b.cleanup()}
});
test('whisper hallucinations on silence are recognised',async()=>{
 const b=await boot();try{
  for(const x of ['Copyright WDR 2020','Untertitel im Auftrag des ZDF, 2021','Untertitel der Amara.org-Community','Vielen Dank fürs Zuschauen!','...'])assert.ok(b.m.isHallucination(x),x);
  for(const x of ['Wie spät ist es?','Welche Aufgaben sind offen?','Danke'])assert.equal(b.m.isHallucination(x),false,x);
 }finally{b.cleanup()}
});

test('hasSpeech: only silence after the wakeword means wait for the question',async()=>{
 const b=await boot();try{
  const sr=16000, tone=(sec,a)=>Float32Array.from({length:Math.round(sr*sec)},(_,i)=>a*Math.sin(i/5));
  const cat=(...xs)=>{const o=new Float32Array(xs.reduce((n,x)=>n+x.length,0));let k=0;for(const x of xs){o.set(x,k);k+=x.length}return o};
  const ref=b.m.peakRms(tone(0.5,0.3));
  assert.equal(b.m.hasSpeech(cat(tone(0.1,0.3),tone(0.9,0.001)),ref),false);   // Rest von „Jarvis“ + Nachlauf
  assert.equal(b.m.hasSpeech(cat(tone(1.0,0.2),tone(0.9,0.001)),ref),true);    // echte Frage
  assert.equal(b.m.hasSpeech(cat(tone(1.0,0.05),tone(0.9,0.001)),ref*0.2),true); // leise Stimme, leiser Massstab
 }finally{b.cleanup()}
});

test('conversation mode keeps listening after answers and window timers (no wakeword needed)',async()=>{
 const b=await boot();try{
  b.m.V.convo=true;
  await b.m.sayText('Erzähle mir etwas Interessantes');
  for(let i=0;i<b.audio.length;i++)b.audio[i].onend();
  assert.equal(b.m.V.state,'listening');
  for(const x of [...b.timers.values()])try{x.f()}catch(e){}
  assert.equal(b.m.V.state,'listening');
  b.m.stopAll();
  assert.equal(b.m.V.state,'listening');   // Unterbrechen beendet das Gespräch nicht
  b.m.endConversation();
  assert.equal(b.m.V.convo,false);
  assert.notEqual(b.m.V.state,'listening');
 }finally{b.cleanup()}
});

test('sentenceCut finds the end of the last complete sentence while streaming',async()=>{
 const b=await boot();try{
  assert.equal(b.m.sentenceCut('Hallo Andre'),-1);
  assert.equal(b.m.sentenceCut('Das ist Satz eins. Und zwei'),18);
  assert.equal(b.m.sentenceCut('Fertig.'),7);
  assert.equal(b.m.sentenceCut('Version 1.22 ist da'),-1);   // Dezimalpunkt ist kein Satzende
 }finally{b.cleanup()}
});
