/* Speech preparation only: no model calls, no microphone permissions. */
export function speechText(text) {
 return String(text ?? '').replace(/```[\s\S]*?```/g,' Den Code findest du im Text. ')
  .replace(/\[([^\]]+)\]\([^)]+\)/g,'$1')
  .replace(/^\s*(?:#{1,6}\s+|[-*]\s+|\d+[.)]\s+)/gm,'')
  .replace(/[*_`#>|]/g,' ').replace(/\s+/g,' ').trim();
}
export function speechChunks(text, max=240) {
 const clean=speechText(text); if (!clean) return [];
 const chunks=[]; let current='';
 for(const word of clean.split(' ')) {
  if(current && current.length+1+word.length>max){chunks.push(current);current='';}
  while(word.length>max && !current) { // pathological long token; bounded without silently dropping text
   for(let p=0;p<word.length;p+=max)chunks.push(word.slice(p,p+max));
   break;
  }
  if(word.length>max)continue;
  current+=(current?' ':'')+word;
  if(/[.!?…]$/.test(word) && current.length>=70){chunks.push(current);current='';}
 }
 if(current)chunks.push(current);
 return chunks;
}
