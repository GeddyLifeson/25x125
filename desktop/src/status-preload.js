// Bridge for the status window only (status.html). The app window gets no preload and no Node access.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("x25", {
  init: () => ipcRenderer.invoke("status:init"),
  openApp: () => ipcRenderer.invoke("status:open-app"),
  onLog: (fn) => ipcRenderer.on("log", (_e, line) => fn(line)),
  onStatus: (fn) => ipcRenderer.on("status", (_e, text) => fn(text)),
});
