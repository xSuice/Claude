/* MA-HOME HQ — Theme-Umschalter (U-06B "Arc Reactor"). Synchron im <head> geladen, damit kein Aufblitzen entsteht.
   Standard: Slate. Auswahl wird nur lokal im Browser gespeichert (localStorage "hq-theme"). */
(function () {
  var KEY = 'hq-theme', THEMES = { slate: 'Slate', arc: 'Arc Reactor' }, META = { slate: '#0E1116', arc: '#070B14' };
  function get() { try { var t = localStorage.getItem(KEY); return THEMES[t] ? t : 'slate'; } catch (e) { return 'slate'; } }
  function apply(t) {
    if (t === 'arc') document.documentElement.setAttribute('data-theme', 'arc'); else document.documentElement.removeAttribute('data-theme');
    var m = document.querySelector('meta[name="theme-color"]'); if (m) m.setAttribute('content', META[t]);
    var b = document.getElementById('theme-toggle');
    if (b) { b.textContent = 'Design: ' + THEMES[t]; b.setAttribute('aria-label', 'Design wechseln, aktuell ' + THEMES[t]); }
  }
  apply(get());
  document.addEventListener('DOMContentLoaded', function () {
    var bar = document.querySelector('.topbar'); if (!bar) return;
    var b = document.createElement('button'); b.type = 'button'; b.id = 'theme-toggle'; b.className = 'theme-toggle';
    b.addEventListener('click', function () { var n = get() === 'slate' ? 'arc' : 'slate'; try { localStorage.setItem(KEY, n); } catch (e) { /* ohne Speicher: nur Sitzung */ } apply(n); });
    bar.appendChild(b); apply(get());
  });
})();
