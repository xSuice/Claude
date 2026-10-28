// Fuegt den Push-Monitor 'Tiefencheck (30 min)' hinzu (idempotent). Token -> /app/data/.ma-deep-push (0600). Keine Geheimnisse im Output.
const { io } = require('/app/node_modules/socket.io-client');
const crypto = require('crypto'), fs = require('fs');
const call = (s, ev, ...a) => new Promise((res, rej) => { const t = setTimeout(() => rej(new Error(ev + ' timeout')), 20000); s.emit(ev, ...a, r => { clearTimeout(t); res(r); }); });
(async () => {
  const s = io('http://127.0.0.1:3001', { transports: ['websocket'], reconnection: false });
  await new Promise((res, rej) => { s.on('connect', res); s.on('connect_error', rej); });
  const monP = new Promise(res => { s.once('monitorList', res); setTimeout(() => res({}), 8000); });
  const l = await call(s, 'login', { username: 'jarvis-admin', password: fs.readFileSync('/app/data/.ma-admin', 'utf8').trim(), token: '' });
  if (!l.ok) throw new Error('login failed');
  const mons = Object.values(await monP);
  const name = 'Tiefencheck (30 min)';
  if (mons.some(m => m.name === name)) { console.log('exists'); s.close(); return; }
  const notif = await new Promise(res => { s.once('notificationList', res); setTimeout(() => res([]), 3000); s.emit('getNotificationList'); });
  const sig = (notif || []).find(n => n.name === 'Signal (JARVIS)');
  const f = '/app/data/.ma-deep-push';
  const tok = fs.existsSync(f) ? fs.readFileSync(f, 'utf8').trim() : crypto.randomBytes(24).toString('base64url');
  fs.writeFileSync(f, tok + '\n', { mode: 0o600 });
  const r = await call(s, 'add', { name, type: 'push', pushToken: tok, interval: 2100, retryInterval: 300, maxretries: 0, resendInterval: 0, active: true,
    description: 'jarvis_deepcheck.py: haengende Auftraege, Leases, Tick-Fehler, Speicher/Platte. down = Befund oder Lauf ausgeblieben',
    notificationIDList: sig ? { [sig.id]: true } : {}, accepted_statuscodes: ['200-299'], conditions: [], kafkaProducerBrokers: [], kafkaProducerSaslOptions: { mechanism: 'None' } });
  console.log('add', r.ok, r.msg || '', 'signal', !!sig);
  s.close();
})().catch(e => { console.error('FEHLER', e.message); process.exit(1); });
