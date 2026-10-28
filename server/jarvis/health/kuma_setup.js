// Einmalige Einrichtung von Uptime Kuma (laeuft IM Container: node setup.js). Gibt keine Geheimnisse aus.
// ENV: BRIDGE_TOKEN (Header fuer die Signal-Bruecke). Schreibt /app/data/.ma-admin (Admin-Passwort) und /app/data/.ma-pc-push (Push-Token), beide 0600.
const { io } = require('/app/node_modules/socket.io-client');
const crypto = require('crypto'), fs = require('fs');
const rnd = n => crypto.randomBytes(n).toString('base64url');
const call = (s, ev, ...args) => new Promise((res, rej) => { const t = setTimeout(() => rej(new Error(ev + ' timeout')), 20000); s.emit(ev, ...args, r => { clearTimeout(t); res(r); }); });
(async () => {
  const s = io('http://127.0.0.1:3001', { transports: ['websocket'], reconnection: false });
  await new Promise((res, rej) => { s.on('connect', res); s.on('connect_error', rej); });
  const pwFile = '/app/data/.ma-admin';
  let pw;
  if (!fs.existsSync(pwFile)) {
    pw = rnd(24);
    fs.writeFileSync(pwFile, pw + '\n', { mode: 0o600 });
    const r = await call(s, 'setup', 'jarvis-admin', pw);
    console.log('setup', r.ok, r.msg || '');
  } else pw = fs.readFileSync(pwFile, 'utf8').trim();
  const monP = new Promise(res => { s.once('monitorList', res); setTimeout(() => res({}), 8000); });
  const l = await call(s, 'login', { username: 'jarvis-admin', password: pw, token: '' });
  if (!l.ok) throw new Error('login failed: ' + l.msg);
  const monitors = await monP;
  const have = new Set(Object.values(monitors).map(m => m.name));
  const n = await call(s, 'addNotification', { name: 'Signal (JARVIS)', type: 'webhook', isDefault: true, applyExisting: true, active: true,
    webhookURL: 'http://127.0.0.1:18772/kuma', webhookContentType: 'json', webhookAdditionalHeaders: JSON.stringify({ 'X-Bridge-Token': process.env.BRIDGE_TOKEN }) }, null);
  console.log('notification', n.ok, n.id);
  const notif = { [n.id]: true };
  const base = { method: 'GET', interval: 60, retryInterval: 60, resendInterval: 0, maxretries: 2, timeout: 20, ignoreTls: false, upsideDown: false, maxredirects: 0,
    expiryNotification: false, httpBodyEncoding: 'json', notificationIDList: notif, accepted_statuscodes: ['200-299'], conditions: [], kafkaProducerBrokers: [], kafkaProducerSaslOptions: { mechanism: 'None' }, active: true };
  const pushFile = '/app/data/.ma-pc-push';
  const pushToken = fs.existsSync(pushFile) ? fs.readFileSync(pushFile, 'utf8').trim() : rnd(24);
  if (!fs.existsSync(pushFile)) fs.writeFileSync(pushFile, pushToken + '\n', { mode: 0o600 });
  const list = [
    { name: 'Portal (intern)', type: 'http', url: 'http://127.0.0.1:18765/healthz' },
    { name: 'Portal (öffentlich, TLS)', type: 'http', url: 'https://ma-server.duckdns.org/healthz', accepted_statuscodes: ['200-399'], interval: 120, expiryNotification: true },
    { name: 'Anmeldung (Authelia)', type: 'http', url: 'http://127.0.0.1:19091/api/health' },
    { name: 'Signal-Dienst', type: 'http', url: 'http://127.0.0.1:18769/api/v1/check' },
    { name: 'Sprachdienst PC (Tunnel)', type: 'http', url: 'http://127.0.0.1:18790/health', accepted_statuscodes: ['401', '200-299'], description: '401 ohne Token = Dienst und Tunnel erreichbar' },
    { name: 'Agenten-Postfach (Tunnel 8484)', type: 'http', url: 'http://127.0.0.1:8484/healthz' },
    { name: 'Home Assistant', type: 'http', url: 'http://127.0.0.1:8123/', interval: 120 },
    { name: 'PC-Lebenszeichen (Telemetrie)', type: 'push', pushToken, interval: 240, retryInterval: 120, maxretries: 1, description: 'telemetry_ingest.py meldet jeden PC-Schnappschuss' },
  ];
  for (const m of list) {
    if (have.has(m.name)) { console.log('exists', m.name); continue; }
    const r = await call(s, 'add', { ...base, ...m });
    console.log('add', m.name, r.ok, r.msg || '');
  }
  const cur = await call(s, 'getSettings');
  const st = await call(s, 'setSettings', { ...(cur.data || {}), disableAuth: true, trustProxy: true, primaryBaseURL: 'https://status.ma-server.duckdns.org', searchEngineIndex: false, checkUpdate: false }, pw);
  console.log('settings', st.ok, st.msg || '');
  s.close();
})().catch(e => { console.error('FEHLER', e.message); process.exit(1); });
