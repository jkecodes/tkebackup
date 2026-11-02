const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("sgsDesktop", {   // 桌面版專用: 網頁的設定視窗用這個開關 Discord 狀態
  presenceGet: () => ipcRenderer.invoke("sgs:presence-get"),
  presenceSet: on => ipcRenderer.invoke("sgs:presence-set", !!on),
});
