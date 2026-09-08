const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electron", {
  isElectron: true,
  platform: process.platform,
  getApiBase: () => ipcRenderer.invoke("get-api-base"),
});
