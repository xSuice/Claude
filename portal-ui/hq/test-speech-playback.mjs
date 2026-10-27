import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {speechChunks} from './js/speech-text.js';
async function setup(){
 const spoken=[];
 globalThis.window={speechSynthesis:{}};
 globalThis.SpeechSynthesisUtterance=class {constructor(text){this.text=text}};
 globalThis.speechSynthesis={getVoices:()=>[],cancel(){},speak(u){spoken.push(u)}};
 globalThis.__speechChunks=speechChunks;
 let src=fs.readFileSync(new URL('./js/voice.js',import.meta.url),'utf8').replace(/^import .*;\r?$/gm,'');
 src='const speechChunks=globalThis.__speechChunks;\n'+src+'\nexport {speak};\n';
 return {m:await import('data:text/javascript;base64,'+Buffer.from(src+'//'+Math.random()).toString('base64')),spoken};
}
test('long speech reaches the end instead of clipping at 700 characters',async()=>{
 const {m,spoken}=await setup(); const input=Array(30).fill('Der Auftrag wartet auf deine Freigabe.').join(' ');
 let done=0;m.speak(input,()=>done++);
 for(let i=0;i<100&&done===0;i++){assert.ok(spoken[i]);spoken[i].onend();}
 assert.equal(done,1);assert.equal(spoken.map(u=>u.text).join(' '),input);
 m.cancelSpeech();
});
test('stop prevents stale completion from continuing queued speech',async()=>{
 const {m,spoken}=await setup();m.speak(Array(30).fill('Das ist ein langer Satz.').join(' '));
 const first=spoken[0];m.cancelSpeech();first.onend();
 assert.equal(spoken.length,1);
});
