// 桌面版外殼: 啟動內建的 Python 伺服器 (sgs-server),再用視窗載入它。
const { app, BrowserWindow, Menu, shell, dialog, ipcMain } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const net = require("net");

let server = null, win = null, port = 8765, lan = false, quitting = false, remote = null;

function cfgPath() { return path.join(app.getPath("userData"), "desktop.json"); }
function loadCfg() { try { return JSON.parse(fs.readFileSync(cfgPath(), "utf8")); } catch (e) { return {}; } }
function saveCfg(o) { try { fs.writeFileSync(cfgPath(), JSON.stringify({ ...loadCfg(), ...o })); } catch (e) {} }

function normalizeUrl(s) {
  s = String(s || "").trim();
  if (!s) return null;
  if (!/^https?:\/\//i.test(s)) s = "http://" + s;
  try { const u = new URL(s); if (!u.port && u.protocol === "http:") u.port = "8765"; return u.origin + "/"; } catch (e) { return null; }
}

function probe(url) {   // 確認對方真的是三國殺伺服器
  return new Promise(resolve => {
    const lib = url.startsWith("https") ? require("https") : require("http");
    const req = lib.get(url, { timeout: 4000 }, res => { res.resume(); resolve(res.statusCode === 200); });
    req.on("error", () => resolve(false)); req.on("timeout", () => { req.destroy(); resolve(false); });
  });
}

function openConnectDialog() {
  const d = new BrowserWindow({ parent: win, modal: true, width: 440, height: 280, resizable: false, minimizable: false, autoHideMenuBar: true, title: "連線到伺服器",
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true } });
  d.setMenuBarVisibility(false);
  d.loadFile(path.join(__dirname, "connect.html"));
  const done = () => { ipcMain.removeHandler("sgs:last"); ipcMain.removeHandler("sgs:connect"); ipcMain.removeAllListeners("sgs:cancel"); };
  ipcMain.handle("sgs:last", () => loadCfg().lastServer || "");
  ipcMain.handle("sgs:connect", async (_e, raw) => {
    const url = normalizeUrl(raw);
    if (!url) return "網址格式不對";
    if (!(await probe(url))) return "連不上這個伺服器 (請確認網址、同一個網路,以及主機已開啟區網模式)";
    saveCfg({ lastServer: raw.trim(), autoConnect: true });   // 下次開啟自動連線
    remote = url; stopServer();
    await win.loadURL(url);
    Menu.setApplicationMenu(buildMenu());
    d.close();
    return "";
  });
  ipcMain.once("sgs:cancel", () => d.close());
  d.on("closed", done);
}

async function backToLocal() {
  saveCfg({ autoConnect: false });
  remote = null; stopServer(); startServer();
  try { await waitReady(); await win.loadURL("http://127.0.0.1:" + port + "/"); } catch (e) {}
  Menu.setApplicationMenu(buildMenu());
}

// ---------- 檢查更新: 對 GitHub 問最新版本,有新版就提示 (不會自動安裝,按「前往下載」開啟下載頁) ----------
const REPO = "jkemusic/Threekingdoms";
function getJson(url) {
  return new Promise(resolve => {
    const req = require("https").get(url, { headers: { "User-Agent": "sgs-sim", Accept: "application/vnd.github+json" }, timeout: 8000 }, res => {
      let b = ""; res.on("data", d => (b += d)); res.on("end", () => { try { resolve(res.statusCode === 200 ? JSON.parse(b) : null); } catch (e) { resolve(null); } });
    });
    req.on("error", () => resolve(null)); req.on("timeout", () => { req.destroy(); resolve(null); });
  });
}
function newer(a, b) {   // a 比 b 新? (1.4.10 > 1.4.9)
  const x = String(a).replace(/^v/, "").split(".").map(n => parseInt(n, 10) || 0), y = String(b).replace(/^v/, "").split(".").map(n => parseInt(n, 10) || 0);
  for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0); }
  return false;
}
async function checkUpdate(manual) {
  const rel = await getJson("https://api.github.com/repos/" + REPO + "/releases/latest");
  const tag = rel && rel.tag_name;
  if (!tag) { if (manual) dialog.showMessageBox(win, { message: "無法檢查更新", detail: "連不上 GitHub,請稍後再試。" }); return; }
  const cur = app.getVersion();
  if (!newer(tag, cur)) { if (manual) dialog.showMessageBox(win, { message: "已經是最新版本", detail: "目前版本 v" + cur }); return; }
  if (!manual && loadCfg().skipVersion === tag) return;
  const r = await dialog.showMessageBox(win, { type: "info", buttons: ["前往下載", "稍後再說", "略過這個版本"], defaultId: 0, cancelId: 1,
    message: "有新版本 " + tag, detail: "你目前是 v" + cur + "。\n" + String(rel.body || "").split("\n").slice(0, 8).join("\n") });
  if (r.response === 0) shell.openExternal(rel.html_url || "https://github.com/" + REPO + "/releases/latest");
  else if (r.response === 2) saveCfg({ skipVersion: tag });
}

// ---------- Discord Rich Presence: 在 Discord 顯示「進化三國」目前在大廳 / 對戰 / 觀戰 (沒開 Discord 或沒設 Application ID 就什麼都不做) ----------
const DISCORD_APP_ID = process.env.SGS_DISCORD_APP_ID || "1566752297814331423";   // Discord 開發者後台建的 Application ID (不是密碼)
const SITE_URL = "https://161.33.203.60.sslip.io/";            // 第一個按鈕「Play the game」連到網站版
const DISCORD_URL = "https://discord.gg/e6f24U3T68";           // 第二個按鈕連到官方 Discord 伺服器            // 「Play the game」按鈕連到網站版
let rpc = null, rpcOk = false, rpcStart = Date.now(), rpcTimer = null;

async function readPresence() {   // 從遊戲頁面讀目前狀態 (只讀畫面上的資料;房間名稱不顯示)
  if (!win || win.isDestroyed()) return null;
  try {
    return await win.webContents.executeJavaScript(`(() => { try {
      const on = id => { const e = document.getElementById(id); return !!(e && e.classList.contains("on")); };
      const s = (typeof S !== "undefined" && S.snap) || null, chip = document.getElementById("bProf");
      return { auth: on("auth"), lobby: on("rooms"), inGame: !!(s && s.round && !s.lobby), over: !!(s && s.over), spectator: !!(s && s.viewer == null), round: s ? s.round : 0, ranked: !!(s && s.ranked), gmode: s ? s.gmode : "", rmode: s ? s.rmode : "", rank: chip ? chip.textContent.trim() : "", name: (typeof S !== "undefined" && S.user) || (typeof myNick === "function" ? myNick() : ""), avatar: (typeof S !== "undefined" && S.prof && S.prof.avatar) || "", origin: location.origin };
    } catch (e) { return null; } })()`);
  } catch (e) { return null; }
}

const RM_NAME = { none: "無身分", open: "身分全公開", hidden: "主公不公開" };
async function updatePresence() {
  if (!rpcOk || !rpc || !rpc.user) return;
  const st = await readPresence();
  const who = st && st.name ? "玩家 " + st.name : "";   // 玩家名字一律寫在第二行最前面
  let details = "閒置中", state = "";   // 閒置中 = 沒在打牌 (大廳 / 登入 / 房間等開局)
  if (st) {
    if (st.inGame && !st.over) {   // 對戰中 / 觀戰中: 下一行寫現在在打什麼模式
      details = (st.spectator ? "觀戰中" : "對戰中") + " · 第 " + st.round + " 輪";
      state = [who, st.ranked ? "段位模式" : "休閒模式", st.gmode === "shuffle" ? "百變" : "", RM_NAME[st.rmode] || ""].filter(Boolean).join(" · ");
    } else {
      state = st.auth ? "登入中" : st.lobby ? "在大廳" : st.inGame ? "對局結束" : "在房間等待開局";
      state = [who, state, st.rank].filter(Boolean).join(" · ");
    }
  }
  // 小圖: 玩家自己上傳的頭貼 (Discord 要從網路抓圖,所以只有連到 https 伺服器時才放;本機 127.0.0.1 的抓不到)
  const av = st && st.avatar && /^https:\/\//.test(st.origin || "") ? st.origin + st.avatar : "";
  try {
    await rpc.user.setActivity({ details, state: state || undefined, startTimestamp: rpcStart, largeImageKey: SITE_URL + "icons/icon-512.png", largeImageText: "進化三國 Three Kingdoms Evolution", ...(av ? { smallImageKey: av, smallImageText: st.name || "玩家" } : {}),
      buttons: [{ label: "Play the game", url: SITE_URL }, { label: "Discord server", url: DISCORD_URL }] });
  } catch (e) { rpcOk = false; }
}

function stopPresence() {
  if (rpcTimer) { clearInterval(rpcTimer); rpcTimer = null; }
  if (rpc) { try { rpc.user && rpc.user.clearActivity(); } catch (e) {} try { rpc.destroy(); } catch (e) {} }
  rpc = null; rpcOk = false;
}

async function startPresence() {
  if (!DISCORD_APP_ID || rpcTimer || loadCfg().discordRpc === false) return;   // 設定裡可以關 (預設開)
  let Client; try { ({ Client } = require("@xhayper/discord-rpc")); } catch (e) { return; }
  const connect = async () => {
    if (rpcOk || quitting) return;
    try {
      rpc = new Client({ clientId: DISCORD_APP_ID });
      rpc.on("disconnected", () => { rpcOk = false; });
      await rpc.login(); rpcOk = true; updatePresence();
    } catch (e) { rpcOk = false; try { rpc && rpc.destroy(); } catch (e2) {} }   // Discord 沒開: 之後每 30 秒再試
  };
  connect();
  rpcTimer = setInterval(() => { if (!rpcOk) connect(); else updatePresence(); }, 15000);
}

function freePort(pref) {
  return new Promise(resolve => {
    const s = net.createServer();
    s.once("error", () => { const t = net.createServer(); t.listen(0, "127.0.0.1", () => { const p = t.address().port; t.close(() => resolve(p)); }); });
    s.listen(pref, "127.0.0.1", () => s.close(() => resolve(pref)));
  });
}

function assetsDir() {
  const d = path.join(app.getPath("userData"), "assets");
  fs.mkdirSync(d, { recursive: true });
  return d;
}

function startServer() {
  const env = { ...process.env, SGS_PORT: String(port), SGS_DATA: app.getPath("userData"), SGS_ASSETS: assetsDir(), PYTHONUTF8: "1" };
  const args = ["--no-browser"].concat(lan ? ["--lan"] : []);
  if (app.isPackaged) {
    const exe = path.join(process.resourcesPath, "server", process.platform === "win32" ? "sgs-server.exe" : "sgs-server");
    server = spawn(exe, args, { env, windowsHide: true });
  } else {   // 開發: 直接跑原始碼
    server = spawn(process.platform === "win32" ? "python" : "python3", [path.join(__dirname, "..", "server.py")].concat(args), { env, windowsHide: true });
  }
  server.stdout.on("data", () => {}); server.stderr.on("data", () => {});
  server.on("exit", code => { server = null; if (!quitting && code) dialog.showErrorBox("伺服器已停止", "內建伺服器結束了 (代碼 " + code + ")。請重新開啟程式。"); });
}

function stopServer() {
  if (server) { try { server.kill(); } catch (e) {} server = null; }
}

function waitReady(tries = 80) {
  return new Promise((resolve, reject) => {
    const tick = n => {
      const c = net.connect(port, "127.0.0.1");
      c.once("connect", () => { c.destroy(); resolve(); });
      c.once("error", () => { c.destroy(); n <= 0 ? reject(new Error("伺服器沒有啟動")) : setTimeout(() => tick(n - 1), 250); });
    };
    tick(tries);
  });
}

function buildMenu() {
  const t = [
    { label: "遊戲", submenu: [
      { label: "重新載入", accelerator: "CmdOrCtrl+R", click: () => win && win.reload() },
      { label: "全螢幕", accelerator: "F11", role: "togglefullscreen" },
      { label: "連線到朋友的伺服器…", click: openConnectDialog },
      ...(remote ? [{ label: "← 回到本機 (離開 " + remote.replace(/^https?:\/\//, "").replace(/\/$/, "") + ")", click: backToLocal }] : []),
      { label: lan ? "✔ 區網模式 (朋友可連線)" : "區網模式 (讓朋友連線)", enabled: !remote, click: async () => {
          lan = !lan; stopServer(); startServer();
          try { await waitReady(); win && win.reload(); } catch (e) {}
          if (lan) dialog.showMessageBox(win, { message: "區網模式已開啟", detail: "朋友用瀏覽器開 http://<你的區網 IP>:" + port + "/ 即可加入。\nWindows 防火牆若詢問,請允許私人網路。" });
          Menu.setApplicationMenu(buildMenu());
        } },
      { type: "separator" },
      { label: "開啟素材資料夾 (放卡牌 / 武將圖片)", click: () => shell.openPath(assetsDir()) },
      { label: "開啟玩家資料夾", click: () => shell.openPath(app.getPath("userData")) },
      { label: "Discord 狀態顯示 (Rich Presence)", type: "checkbox", checked: loadCfg().discordRpc !== false, click: m => { saveCfg({ discordRpc: m.checked }); if (m.checked) startPresence(); else stopPresence(); } },
      { label: "檢查更新…", click: () => checkUpdate(true) },
      { type: "separator" },
      { role: process.platform === "darwin" ? "close" : "quit", label: "結束" },
    ] },
    { label: "編輯", submenu: [{ role: "copy" }, { role: "paste" }, { role: "selectAll" }] },
    { label: "檢視", submenu: [{ role: "zoomIn" }, { role: "zoomOut" }, { role: "resetZoom" }, { role: "toggleDevTools" }] },
  ];
  return Menu.buildFromTemplate(t);
}

ipcMain.handle("sgs:presence-get", () => ({ on: loadCfg().discordRpc !== false, available: !!DISCORD_APP_ID }));
ipcMain.handle("sgs:presence-set", (_e, on) => { saveCfg({ discordRpc: !!on }); if (on) startPresence(); else stopPresence(); Menu.setApplicationMenu(buildMenu()); return !!on; });

async function createWindow() {
  port = await freePort(8765);
  const cfg = loadCfg();
  if (cfg.autoConnect && cfg.lastServer) {   // 上次選了連線到某個伺服器: 開啟就直接連 (連不上才退回本機)
    const url = normalizeUrl(cfg.lastServer);
    if (url && await probe(url)) remote = url;
  }
  if (!remote) startServer();
  win = new BrowserWindow({ width: 1280, height: 860, title: "進化三國", icon: path.join(__dirname, "icon.png"), backgroundColor: "#0e0f11", webPreferences: { preload: path.join(__dirname, "preload-main.js"), contextIsolation: true } });
  Menu.setApplicationMenu(buildMenu());
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  try {
    if (remote) await win.loadURL(remote);
    else { await waitReady(); await win.loadURL("http://127.0.0.1:" + port + "/"); }
  } catch (e) { dialog.showErrorBox("無法啟動", String(e.message || e)); app.quit(); return; }
  startPresence();
  if (app.isPackaged) setTimeout(() => checkUpdate(false), 4000);   // 啟動後自動檢查一次 (開發模式不檢查)
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) app.quit();
else {
  app.on("second-instance", () => { if (win) { if (win.isMinimized()) win.restore(); win.focus(); } });
  app.whenReady().then(createWindow);
}
app.on("before-quit", () => { quitting = true; stopPresence(); stopServer(); });
app.on("window-all-closed", () => app.quit());
