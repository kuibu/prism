const { contextBridge, ipcRenderer } = require("electron");

const UPDATE_EVENT_CHANNEL = "desktop:update-event";

contextBridge.exposeInMainWorld("prismDesktop", {
  getConfig: () => ipcRenderer.invoke("desktop:get-config"),
  reloadWeb: () => ipcRenderer.invoke("desktop:reload-web"),
  openExternal: (url) => ipcRenderer.invoke("desktop:open-external", url),
  checkForUpdates: () => ipcRenderer.invoke("desktop:check-for-updates"),
  getUpdateState: () => ipcRenderer.invoke("desktop:get-update-state"),
  onUpdateEvent: (callback) => {
    if (typeof callback !== "function") {
      return () => undefined;
    }
    const handler = (_event, payload) => callback(payload);
    ipcRenderer.on(UPDATE_EVENT_CHANNEL, handler);
    return () => ipcRenderer.removeListener(UPDATE_EVENT_CHANNEL, handler);
  }
});
