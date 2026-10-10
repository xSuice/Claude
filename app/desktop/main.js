'use strict';
const { app, BrowserWindow, ipcMain, shell, Menu, Notification } = require('electron');
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
let win;
const runs = new Map();

function createWindow() {
  win = new BrowserWindow({
    width: 1180, height: 780, minWidth: 760, minHeight: 520, backgroundColor: '#0d0b1a', title: 'MA Home',
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, webviewTag: true, sandbox: true }
  });
  Menu.setApplicationMenu(null);
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https:\/\//.test(url)) shell.openExternal(url); return { action: 'deny' }; });
}

function sh(s) { return "'" + String(s).replace(/'/g, "'\''") + "'"; }

ipcMain.handle('config', () => ({ portal: PORTAL, dirs: Object.keys(DIRS), modes: Object.keys(MODES) }));
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
  const cmd = "echo up=$(cut -d' ' -f1 /proc/uptime); df -B1 --output=used,size / | tail -1; free -b | awk '/Mem/{print $3, $2}'; systemctl is-active ma-usb-backup.timer; " +
    "systemctl show ma-usb-backup.service -p ActiveState -p Result -p ExecMainExitTimestamp | tr '\n' ' '; echo; echo claude=$(" + CLAUDE + " --version 2>&1 | head -c 40)";
  const p = spawn('ssh', ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=6', HOST, cmd], { windowsHide: true });
  let out = ''; p.stdout.on('data', d => out += d); p.on('close', code => resolve({ ok: code === 0, out })); p.on('error', () => resolve({ ok: false, out: '' }));
  setTimeout(() => p.kill(), 15000);
}));

ipcMain.handle('login-hint', () => 'ssh -t ma-server "~/.local/bin/claude"');

const lock = app.requestSingleInstanceLock();
if (!lock) app.quit(); else { app.on('second-instance', () => { if (win) { win.restore(); win.focus(); } }); app.whenReady().then(createWindow); }
app.on('window-all-closed', () => app.quit());
