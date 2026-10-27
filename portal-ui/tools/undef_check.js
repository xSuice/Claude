// Statische Heuristik: Bezeichner, die in port.js benutzt, aber nirgends deklariert/importiert/eingebaut sind.
const fs = require('fs');
let src = fs.readFileSync('js/port.js', 'utf8');
// Strings, Kommentare, Regex-Literale grob entfernen
src = src.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:\\])\/\/[^\n]*/g, '$1 ');
src = src.replace(/'(?:\\.|[^'\\\n])*'/g, "''").replace(/"(?:\\.|[^"\\\n])*"/g, '""');
// Template-Literale: nur ${...}-Ausdruecke behalten
src = src.replace(/`(?:\\.|[^`\\])*`/g, m => (m.match(/\$\{[^}]*\}/g) || []).join(' '));
const KW = new Set('break case catch class const continue debugger default delete do else export extends finally for function if import in instanceof let new return super switch this throw try typeof var void while with yield async await of from null true false undefined NaN Infinity arguments static get set'.split(' '));
const builtin = new Set([...Object.getOwnPropertyNames(globalThis),
  ...'window document navigator location history localStorage sessionStorage fetch console setTimeout clearTimeout setInterval clearInterval requestAnimationFrame cancelAnimationFrame performance Audio Image URL URLSearchParams AbortController TextDecoder TextEncoder FormData Blob File Notification crypto confirm alert prompt getComputedStyle ResizeObserver MutationObserver IntersectionObserver Event CustomEvent KeyboardEvent MouseEvent Option Response Request Headers WebSocket speechSynthesis SpeechSynthesisUtterance HTMLElement Element Node atob btoa structuredClone queueMicrotask matchMedia devicePixelRatio innerWidth innerHeight scrollTo isFinite parseInt parseFloat'.split(' ')]);
const declared = new Set();
let m;
for (const re of [/\b(?:function|class)\s+([A-Za-z_$][\w$]*)/g, /\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)/g]) while ((m = re.exec(src))) declared.add(m[1]);
for (const re of [/\b(?:const|let|var)\s*[\[{]([^\]}=]*)[\]}]/g, /\(([^()]*)\)\s*=>/g, /\b([A-Za-z_$][\w$]*)\s*=>/g, /function\s*[A-Za-z_$]*\s*\(([^)]*)\)/g, /catch\s*\(\s*([A-Za-z_$][\w$]*)/g, /\bfor\s*\(\s*(?:const|let|var)\s*[\[{]?([^)\]}]*?)[\]}]?\s+(?:of|in)\b/g, /\b(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^()]*\)\s*\{/g])
  while ((m = re.exec(src))) (m[1] || '').split(/[,\s:=\[\]{}]+/).forEach(x => { if (/^[A-Za-z_$][\w$]*$/.test(x)) declared.add(x); });
// Importe
(fs.readFileSync('js/port.js', 'utf8').match(/import\s*\{([^}]*)\}/g) || []).forEach(i => i.replace(/import\s*\{|\}/g, '').split(',').forEach(x => declared.add(x.trim().split(/\s+as\s+/).pop())));
const used = new Map();
const idre = /(?<![.\w$])([A-Za-z_$][\w$]*)\b(?!\s*:(?!:))/g;
while ((m = idre.exec(src))) { const id = m[1]; if (KW.has(id) || declared.has(id) || builtin.has(id)) continue; used.set(id, (used.get(id) || 0) + 1); }
// Objektschluessel-Rauschen filtern: Treffer nur melden, wenn Bezeichner nicht nur als {key: ...} vorkommt
const out = [...used.entries()].sort((a, b) => b[1] - a[1]);
console.log(out.length + ' Kandidaten:\n' + out.map(([k, v]) => k + '×' + v).join('  '));
