'use strict';
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('ma', {
  config: () => ipcRenderer.invoke('config'),
  status: () => ipcRenderer.invoke('status'),
  loadChats: () => ipcRenderer.invoke('chats:load'),
  saveChats: d => ipcRenderer.invoke('chats:save', d),
  send: o => ipcRenderer.send('chat:send', o),
  stop: id => ipcRenderer.send('chat:stop', id),
  onEvent: cb => ipcRenderer.on('chat:event', (_e, m) => cb(m)),
  loginHint: () => ipcRenderer.invoke('login-hint')
});
