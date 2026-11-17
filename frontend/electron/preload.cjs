const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("videoOS", {
  isDesktop: true,
  pickFiles: () => ipcRenderer.invoke("video-os:pick-files"),
  pickFolder: () => ipcRenderer.invoke("video-os:pick-folder"),
  openPath: (targetPath) => ipcRenderer.invoke("video-os:open-path", targetPath)
});
