const fs=require('fs'),vm=require('vm'),assert=require('assert');
const file='js/ledger-view.js';assert(fs.existsSync(file),'ledger renderer missing');
const c={};vm.createContext(c);vm.runInContext(fs.readFileSync(file,'utf8').replace(/export /g,'')+'\nglobalThis.render=renderLedger;',c);
const fixture={ledger:{claude:{calls_24h:3,tokens_24h:90,limits:{calls_per_day:10,tokens_per_day:1000}},helper:{calls_24h:0,tokens_24h:0,limits:{calls_per_day:0,tokens_per_day:0}},plan_block:'<blocked>'},jobs_24h:{cache:12}};
let html=c.render(fixture);
assert(html.includes('3 / 10'));assert(html.includes('90 / 1000'));assert(html.includes('deaktiviert'));assert(html.includes('12'));assert(html.includes('&lt;blocked&gt;'));assert(!html.includes('<blocked>'));
assert(c.render(null).includes('nicht verfügbar'));
assert(!c.render({ledger:{claude:{calls_24h:0,limits:{}}}}).includes('0 / 0'));
console.log('PASS actual ledger values, disabled limits, cache, escaping and missing data');
