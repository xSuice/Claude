import test from 'node:test';
import assert from 'node:assert/strict';
const { speechText, speechChunks } = await import('./js/speech-text.js');
test('speech removes markup without destroying German pauses',()=>{
 assert.equal(speechText('**Hallo.**\n\nDer Worker wartet. [Details](https://example.org)'),'Hallo. Der Worker wartet. Details');
});
test('long answers are preserved and split into bounded speech chunks',()=>{
 const text=Array.from({length:30},()=> 'Der Auftrag wartet auf deine Freigabe.').join(' ');
 const chunks=speechChunks(text);
 assert.ok(chunks.length>1);
 assert.ok(chunks.every(c=>c.length<=240));
 assert.equal(chunks.join(' '),text);
});
test('code is not read character by character',()=>{
 assert.equal(speechText('Hier ist der Code:\n```js\nsecret();\n```\nFertig.'),'Hier ist der Code: Den Code findest du im Text. Fertig.');
});
