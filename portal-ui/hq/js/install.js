/* MA-HOME HQ — „App installieren“ (PWA). Android/Chrome/Edge: echtes Installationsfenster über beforeinstallprompt.
   iOS Safari kennt das Ereignis nicht: dort einmalig Hinweis „Teilen → Zum Home-Bildschirm“. Installiert (standalone) = kein Knopf. */
export function isStandalone(w = window) {
  return !!((w.matchMedia && w.matchMedia('(display-mode: standalone)').matches) || (w.navigator && w.navigator.standalone));
}
export const isIOS = (ua = navigator.userAgent) => /iphone|ipad|ipod/i.test(ua) && !/crios|fxios|edgios/i.test(ua);

export function mountInstall(host, toast) {
  if (!host || isStandalone()) return null;
  let deferred = null;
  const b = document.createElement('button');
  b.type = 'button'; b.className = 'voice-btn install-btn'; b.hidden = true; b.id = 'install-btn';
  b.innerHTML = '<span aria-hidden="true">⤓</span><span class="vlbl">App</span>';
  b.title = 'JARVIS als App auf diesem Gerät installieren';
  host.insertBefore(b, host.querySelector('.palette-trigger'));
  window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); deferred = e; b.hidden = false; });
  window.addEventListener('appinstalled', () => { b.hidden = true; deferred = null; toast && toast('JARVIS ist jetzt als App installiert.'); });
  if (isIOS()) b.hidden = false;
  b.onclick = async () => {
    if (deferred) { deferred.prompt(); try { await deferred.userChoice; } catch (e) { /* */ } deferred = null; b.hidden = true; return; }
    toast && toast('iPhone/iPad: unten auf „Teilen“ tippen, dann „Zum Home-Bildschirm“.');
  };
  return b;
}
