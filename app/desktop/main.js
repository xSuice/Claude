'use strict';
const { app, BrowserWindow, ipcMain, shell, Menu, Notification, Tray, nativeImage } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const HOST = 'ma-server';
const PORTAL = 'https://ma-server.duckdns.org/';
const CLAUDE = '~/.local/bin/claude';
const DIRS = {
  notizen: '/srv/ma-home/library/vault-notizen',
  server: '/home/andrew',
  bibliothek: '/srv/ma-home/library'
};
// Rechte je Modus. Es gibt kein sudo-Passwort: Claude kann auf dem Server nichts mit Root-Rechten tun.
const READ_BASH = ['ls', 'cat', 'head', 'tail', 'df', 'du', 'uptime', 'free', 'ps', 'ss', 'systemctl status', 'systemctl list-timers', 'systemctl is-active', 'journalctl', 'find', 'grep', 'wc', 'stat', 'date', 'lsblk'].map(c => `Bash(${c}:*)`);
const MODES = {
  lesen: { tools: ['Read', 'Grep', 'Glob', ...READ_BASH], perm: 'default' },
  notizen: { tools: ['Read', 'Grep', 'Glob', 'Edit', 'Write', ...READ_BASH], perm: 'acceptEdits' }
};
const store = path.join(app.getPath('userData'), 'chats.json');
let win, tray, quitting = false;
const runs = new Map();
const settingsFile = path.join(app.getPath('userData'), 'settings.json');
function loadSettings() { try { return JSON.parse(fs.readFileSync(settingsFile, 'utf8')); } catch (e) { return {}; } }
function saveSettings(o) { try { fs.writeFileSync(settingsFile, JSON.stringify(o)); } catch (e) { /* ohne Speicher */ } }

function createWindow() {
  win = new BrowserWindow({
    width: (loadSettings().bounds || {}).width || 1280, height: (loadSettings().bounds || {}).height || 820, x: (loadSettings().bounds || {}).x, y: (loadSettings().bounds || {}).y, minWidth: 820, minHeight: 560, backgroundColor: '#0d0b1a', title: 'MA Home',
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, webviewTag: true, sandbox: true }
  });
  Menu.setApplicationMenu(null);
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  win.on('close', e => { if (!quitting) { e.preventDefault(); win.hide(); } });
  win.on('close', () => { if (!win.isMinimized() && !win.isMaximized()) { const st = loadSettings(); st.bounds = win.getBounds(); saveSettings(st); } });
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https:\/\//.test(url)) shell.openExternal(url); return { action: 'deny' }; });
}

function sh(s) { return "'" + String(s).replace(/'/g, "'\''") + "'"; }

ipcMain.handle('config', () => ({ version: app.getVersion(), portal: PORTAL, dirs: Object.keys(DIRS), modes: Object.keys(MODES) }));
ipcMain.handle('chats:load', () => { try { return JSON.parse(fs.readFileSync(store, 'utf8')); } catch (e) { return []; } });
ipcMain.handle('chats:save', (_e, data) => { fs.writeFileSync(store, JSON.stringify(data)); return true; });

ipcMain.on('chat:send', (e, { id, prompt, sessionId, dir, mode, model }) => {
  const m = MODES[mode] || MODES.lesen;
  const cwd = DIRS[dir] || DIRS.notizen;
  const mdl = ['haiku', 'sonnet', 'opus'].includes(model) ? model : 'sonnet';
  const args = ['-p', '--output-format', 'stream-json', '--verbose', '--include-partial-messages', '--model', mdl,
    '--permission-mode', m.perm, '--allowedTools', m.tools.join(','), '--max-turns', '12'];
  if (sessionId && /^[0-9a-f-]{36}$/.test(sessionId)) args.push('--resume', sessionId);
  const remote = `cd ${sh(cwd)} && ${CLAUDE} ${args.map(sh).join(' ')}`;
  const p = spawn('ssh', ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', HOST, remote], { windowsHide: true });
  runs.set(id, p);
  let buf = '', err = '';
  const send = (type, data) => { if (!e.sender.isDestroyed()) e.sender.send('chat:event', { id, type, data }); };
  p.stdout.on('data', d => {
    buf += d.toString('utf8');
    let i;
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
      if (!line) continue;
      try { send('json', JSON.parse(line)); } catch (x) { /* keine JSON-Zeile */ }
    }
  });
  p.stderr.on('data', d => { err += d.toString('utf8'); });
  p.on('close', code => {
    runs.delete(id);
    send('end', { code, err: err.slice(-600) });
    if (win && !win.isFocused() && Notification.isSupported()) new Notification({ title: 'MA Home', body: 'Claude ist fertig.' }).show();
  });
  p.on('error', x => send('end', { code: -1, err: String(x) }));
  p.stdin.end(prompt);
});
ipcMain.on('chat:stop', (_e, id) => { const p = runs.get(id); if (p) p.kill(); });

ipcMain.handle('status', () => new Promise(resolve => {
  const cmd = [
    "echo up=$(cut -d' ' -f1 /proc/uptime)",
    "echo disk=$(df -B1 --output=used,size / | tail -1)",
    "echo mem=$(free -b | awk '/Mem/{print $3, $2}')",
    "echo swap=$(free -b | awk '/Swap/{print $3, $2}')",
    "echo load=$(cut -d' ' -f1 /proc/loadavg)",
    "echo timer=$(systemctl is-active ma-usb-backup.timer)",
    "echo backup=$(systemctl show ma-usb-backup.service -p Result --value)",
    "echo backupAt=$(systemctl show ma-usb-backup.service -p ExecMainExitTimestamp --value)",
    "echo claude=$(" + CLAUDE + " --version 2>&1 | head -c 40)",
    "echo '##W'; cat /var/lib/ma-watchdog/status.txt 2>/dev/null",
    "echo '##S'; cat /var/lib/ma-watchdog/sicherheit.kurz 2>/dev/null",
    "echo '##P'; grep -m1 'Stand' /srv/ma-home/library/vault-notizen/_Claude-Memory/Dienste/Paritaet.md 2>/dev/null"
  ].join('; ');
  const p = spawn('ssh', ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=6', HOST, cmd], { windowsHide: true });
  let out = ''; p.stdout.on('data', d => out += d); p.on('close', code => resolve({ ok: code === 0, out })); p.on('error', () => resolve({ ok: false, out: '' }));
  setTimeout(() => p.kill(), 15000);
}));

ipcMain.handle('login-hint', () => 'ssh -t ma-server "~/.local/bin/claude"');

function setAutostart(on) {
  const st = loadSettings(); st.autostart = on; saveSettings(st);
  if (app.isPackaged) app.setLoginItemSettings({ openAtLogin: on, args: ['--hidden'] });
  buildTray();
}
function showWin() { if (!win) createWindow(); win.show(); win.restore(); win.focus(); }
function buildTray() {
  if (!tray) {
    const img = nativeImage.createFromPath(path.join(__dirname, 'build', 'icon.png')).resize({ width: 16, height: 16 });
    tray = new Tray(img); tray.setToolTip('MA Home'); tray.on('click', showWin);
  }
  const st = loadSettings();
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'MA Home öffnen', click: showWin },
    { label: 'Mit Windows starten', type: 'checkbox', checked: !!st.autostart, click: m => setAutostart(m.checked) },
    { label: 'Server-Status jetzt prüfen', click: () => pollWatch(true) },
    pendingUpdate ? { label: 'Jetzt aktualisieren auf ' + pendingUpdate.version, click: updateNow } : { label: 'Nach Updates suchen', click: () => checkUpdate(true) },
    { type: 'separator' },
    { label: 'Beenden', click: () => { quitting = true; app.quit(); } }
  ]));
}

// Wachhund des Servers (/var/lib/ma-watchdog) alle 10 Minuten lesen; neue Probleme als Windows-Meldung, jedes nur einmal
const seen = new Set();
function pollWatch(manual) {
  const cmd = 'cat /var/lib/ma-watchdog/status.txt /var/lib/ma-watchdog/sicherheit.kurz 2>/dev/null';
  const p = spawn('ssh', ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', HOST, cmd], { windowsHide: true });
  let out = ''; p.stdout.on('data', d => out += d);
  p.on('close', () => {
    const probs = out.split('\n').filter(l => l.startsWith('PROBLEM') || l.startsWith('- '));
    const neu = probs.filter(l => !seen.has(l)); neu.forEach(l => seen.add(l));
    if (Notification.isSupported() && (neu.length || manual)) {
      new Notification({ title: neu.length ? 'MA-Server: Problem' : 'MA-Server', body: neu.length ? neu.join('; ').slice(0, 240) : (out ? 'Alles in Ordnung.' : 'Server nicht erreichbar.') }).show();
    }
  });
  p.on('error', () => { /* ssh fehlt oder Server aus: still bleiben */ });
  setTimeout(() => p.kill(), 20000);
}

// Auto-Update: Server legt ~/app-updates/latest.json {version,file,sha256} ab (deploy.py). Laden per scp, sha256 pruefen, still installieren beim Beenden.
const UPD_DIR = path.join(app.getPath('userData'), 'updates');
let pendingUpdate = null, updating = false;
function cmpVer(a, b) { const x = String(a).split('.').map(Number), y = String(b).split('.').map(Number); for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0) ? 1 : -1; } return 0; }
function run(cmd, args, ms) {
  return new Promise(resolve => {
    const p = spawn(cmd, args, { windowsHide: true }); let out = '';
    p.stdout.on('data', d => out += d); p.on('error', () => resolve({ code: -1, out })); p.on('close', code => resolve({ code, out }));
    setTimeout(() => p.kill(), ms || 30000);
  });
}
function sha256File(f) { return new Promise(res => { const h = require('crypto').createHash('sha256'); fs.createReadStream(f).on('data', d => h.update(d)).on('end', () => res(h.digest('hex'))).on('error', () => res('')); }); }
async function checkUpdate(manual) {
  if (updating || pendingUpdate) { if (manual && pendingUpdate) notify('Update ' + pendingUpdate.version + ' ist geladen und wird beim Beenden installiert.'); return; }
  updating = true;
  try {
    const r = await run('ssh', ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', HOST, 'cat ~/app-updates/latest.json'], 20000);
    let j; try { j = JSON.parse(r.out); } catch (e) { j = null; }
    if (!j || !/^\d+\.\d+\.\d+$/.test(j.version || '') || !/^[\w. -]+\.exe$/.test(j.file || '') || !/^[0-9a-f]{64}$/.test(j.sha256 || '')) { if (manual) notify('Kein Update-Hinweis auf dem Server.'); return; }
    if (cmpVer(j.version, app.getVersion()) <= 0) { if (manual) notify('MA Home ist aktuell (' + app.getVersion() + ').'); return; }
    fs.mkdirSync(UPD_DIR, { recursive: true });
    const dest = path.join(UPD_DIR, 'MA-Home-Setup-' + j.version + '.exe');
    if (await sha256File(dest) !== j.sha256) {
      const c = await run('scp', ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', HOST + ':app-updates/' + j.file.replace(/ /g, '\\ '), dest], 300000);
      if (c.code !== 0 || await sha256File(dest) !== j.sha256) { try { fs.unlinkSync(dest); } catch (e) { /* weg */ } if (manual) notify('Update-Download fehlgeschlagen oder Pruefsumme falsch.'); return; }
    }
    pendingUpdate = { version: j.version, file: dest };
    notify('Update ' + j.version + ' geladen. Es wird beim Beenden still installiert (Tray: Jetzt aktualisieren).');
    buildTray();
  } finally { updating = false; }
}
function notify(body) { if (Notification.isSupported()) new Notification({ title: 'MA Home', body }).show(); }
function installPending() {
  if (!pendingUpdate) return false;
  const f = pendingUpdate.file; pendingUpdate = null;
  // kurz warten, bis diese Instanz beendet ist; /S = still, --force-run startet die App danach neu
  const p = spawn('cmd', ['/c', 'ping -n 4 127.0.0.1 >nul & "' + f + '" /S --force-run'], { detached: true, stdio: 'ignore', windowsHide: true, windowsVerbatimArguments: true });
  p.unref(); return true;
}
function updateNow() { if (installPending()) { quitting = true; app.quit(); } }

const lock = app.requestSingleInstanceLock();
if (!lock) app.quit(); else {
  app.on('second-instance', showWin);
  app.whenReady().then(() => {
    const st = loadSettings();
    if (st.autostart === undefined) setAutostart(true);          // erster Start: mit Windows starten (im Tray abschaltbar)
    createWindow(); buildTray();
    if (process.argv.includes('--hidden')) win.hide();
    setTimeout(() => pollWatch(false), 15000); setInterval(() => pollWatch(false), 10 * 60 * 1000);
    if (app.isPackaged) { setTimeout(() => checkUpdate(false), 45000); setInterval(() => checkUpdate(false), 60 * 60 * 1000); }
  });
}
app.on('before-quit', () => { quitting = true; });
app.on('will-quit', () => { installPending(); });
app.on('window-all-closed', () => { /* bleibt im Tray */ });
