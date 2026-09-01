const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  elegirCarpetaDestino: () => ipcRenderer.invoke("elegir-carpeta"),
  guardarExpediente: (payload) => ipcRenderer.invoke("guardar-expediente", payload),
});
