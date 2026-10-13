/* MA Home Service Worker. Netz zuerst: Jede Aenderung am Portal ist beim naechsten Oeffnen sofort da, ohne Update.
   Nur wenn das Netz fehlt, springt der Zwischenspeicher ein (Oberflaeche startet, Daten aus /api kommen nie aus dem Cache).
   Die Version steht in app.js (VERSION) und hier; bei Aenderung am Portal beide hochzaehlen. */
const VERSION = '2026-10-13-4';
const CACHE = 'ma-home-' + VERSION;
const SHELL = ['/', '/assets/app.js', '/assets/style.css', '/assets/manifest.webmanifest', '/assets/icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL).catch(() => {})).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('ma-home-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('message', e => { if (e.data === 'skip') self.skipWaiting(); });

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/') || url.pathname === '/healthz') return;
  e.respondWith(fetch(req).then(res => {
    if (res.ok && res.type === 'basic') { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
    return res;
  }).catch(() => caches.match(req).then(hit => hit || (req.mode === 'navigate' ? caches.match('/') : Response.error()))));
});
