// Verknuepft 'Tiefencheck (30 min)' mit der Signal-Benachrichtigung (idempotent).
const { io } = require('/app/node_modules/socket.io-client');
const fs = require('fs');
const call = (s, ev, ...a) => new Promise((res, rej) => { const t = setTimeout(() => rej(new Error(ev + ' timeout')), 20000); s.emit(ev, ...a, r => { clearTimeout(t); res(r); }); });
(async () => {
  const s = io('http://127.0.0.1:3001', { transports: ['websocket'], reconnection: false });
  await new Promise((res, rej) => { s.on('connect', res); s.on('connect_error', rej); });
  const monP = new Promise(res => { s.once('monitorList', res); setTimeout(() => res({}), 8000); });
  const notP = new Promise(res => { s.once('notificationList', res); setTimeout(() => res([]), 8000); });
  const l = await call(s, 'login', { username: 'jarvis-admin', password: fs.readFileSync('/app/data/.ma-admin', 'utf8').trim(), token: '' });
  if (!l.ok) throw new Error('login failed');
  const [mons, nots] = await Promise.all([monP, notP]);
  const sig = nots.find(n => n.name === 'Signal (JARVIS)');
  const m = Object.values(mons).find(x => x.name === 'Tiefencheck (30 min)');
  if (!sig || !m) throw new Error('missing ' + (!sig ? 'notification' : 'monitor'));
  const g = await call(s, 'getMonitor', m.id);
  const mon = g.monitor; mon.notificationIDList = { [sig.id]: true };
  const r = await call(s, 'editMonitor', mon);
  console.log('edit', r.ok, r.msg || '');
  const linked = Object.values(mons).filter(x => x.notificationIDList && x.notificationIDList[sig.id]).length;
  console.log('monitors already linked before edit:', linked, 'of', Object.keys(mons).length);
  s.close();
})().catch(e => { console.error('FEHLER', e.message); process.exit(1); });
