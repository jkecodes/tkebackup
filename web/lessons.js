/* 練習關卡: 預先佈置好牌桌,一步一步教每張牌、每個身分、每位武將。
   選單 (SGS_LESSON.open) + 對局上方的步驟列 (SGS_LESSON.sync, 每次輪詢狀態時更新)。
   關卡內容 (牌 / 提示) 目前只有繁體中文; 介面文字有三語。 */
(function () {
  const KEY = "sgs_lessons_done";
  const T = {
    zh: { title: "練習關卡", sub: "不用照順序,挑想學的就好。隨時都能離開。", done: "已完成", of: "/", leave: "離開", retry: "重來", tips: "重點", next: "下一關", fin: "我學會了", ok: "過關!", step: "步驟", back: "回到教學", seen: "我看懂了", ask: "離開練習關卡?", free: "自由練習: 照技能說明試試看,學會了就按「我學會了」", all: "全部", todo: "只顯示未通關", alldone: "這一類全部通關了!", ng: "還沒有關卡", load: "載入中…", pass: "通過教學!", menu: "回到教學選單", again: "再玩一次", search: "搜尋名字或效果…", nores: "找不到符合的關卡" },
    en: { title: "Practice Levels", sub: "Pick any level, in any order. You can leave anytime.", done: "Done", of: "/", leave: "Leave", retry: "Retry", tips: "Tips", next: "Next", fin: "Got it", ok: "Cleared!", step: "Step", back: "Back to tutorial", seen: "Got it", ask: "Leave this level?", free: "Free practice: try the skill as described, then press \"Got it\".", all: "All", todo: "Unfinished only", alldone: "All cleared here!", ng: "No levels yet", load: "Loading…", pass: "Level cleared!", menu: "Back to levels", again: "Play again", search: "Search name or effect…", nores: "No matching levels" },
    ja: { title: "練習ステージ", sub: "好きな順番で選べます。いつでも終了できます。", done: "クリア", of: "/", leave: "終了", retry: "やり直し", tips: "ポイント", next: "次へ", fin: "覚えた", ok: "クリア!", step: "手順", back: "チュートリアルへ", seen: "わかった", ask: "このステージを終了しますか?", free: "自由練習: 説明どおりに試して、覚えたら「覚えた」を押してください。", all: "すべて", todo: "未クリアのみ", alldone: "このカテゴリは全部クリア!", ng: "ステージがありません", load: "読み込み中…", pass: "ステージクリア!", menu: "ステージ一覧へ", again: "もう一度", search: "名前や効果で検索…", nores: "該当するステージがありません" },
  };
  const tx = k => (T[(window.SGS_I18N && SGS_I18N.lang) || "zh"] || T.zh)[k];
  const GN = { "基本牌": { en: "Basic", ja: "基本" }, "錦囊": { en: "Tricks", ja: "錦囊" }, "裝備": { en: "Equipment", ja: "装備" }, "身分": { en: "Roles", ja: "身分" }, "武將": { en: "Generals", ja: "武将" } };
  const gname = g => { const l = (window.SGS_I18N && SGS_I18N.lang) || "zh"; return l === "zh" ? g : (GN[g] && GN[g][l]) || g; };
  let qry = "", qryTab = null, CAT = null, lessonRoom = "", fac = "", tab = null, curId = null, tipsOn = false, saved = false, synced = false, onlyTodo = false;

  const el = (tag, attrs, ...kids) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "text") e.textContent = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v);
    }
    for (const c of kids.flat()) if (c != null) e.append(c.nodeType ? c : document.createTextNode(c));
    return e;
  };
  const doneMap = () => { try { return JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { return {}; } };
  const markDone = id => { try { const m = doneMap(); if (!m[id]) { m[id] = 1; localStorage.setItem(KEY, JSON.stringify(m)); } } catch (e) {} };
  const load = async () => { if (!CAT) CAT = await (await fetch("/api/lessons")).json(); return CAT; };

  const tileImg = L => {   // 圖跟著自己選的卡面風格 / 新舊卡圖 / 武將圖
    if (!L.img) return null;
    let u = L.img; const ms = typeof mySel === "function" ? mySel() : {};
    if (u.startsWith("/cards/")) { const q = []; if (ms.cardbg && ms.cardbg !== "classic") q.push("bg=" + encodeURIComponent(ms.cardbg)); if (ms.cardart === "svg") q.push("art=svg"); if (q.length) u += "?" + q.join("&"); }
    else u += "?v=ink2" + (typeof gaQ === "function" ? gaQ() : "");
    return el("img", { src: u, alt: L.name, loading: "lazy" });
  };

  const css = `
#lsov{position:fixed;inset:0;background:rgba(0,0,0,.62);z-index:9000;display:flex;align-items:center;justify-content:center;padding:16px}
.lsdlg{background:#161c28;color:#e6edf7;border:1px solid #394559;border-radius:12px;width:min(820px,100%);max-height:90vh;max-height:90dvh;display:flex;flex-direction:column;box-shadow:0 10px 40px rgba(0,0,0,.6)}
.lsdlg .lsh{display:flex;align-items:center;gap:10px;padding:14px 18px 6px}.lsdlg .lsh b{font-size:17px}.lsdlg .lsh .sp{flex:1}
.lsdlg .lsh button{background:none;border:0;color:#9fb0c8;font-size:18px;cursor:pointer;min-width:36px;min-height:36px}
.lsdlg .lss{padding:0 18px 8px;color:#9fb0c8;font-size:13px}.lsgrid>.lss{grid-column:1/-1;padding:8px 2px}   /* 「全部通關了」「找不到」這類提示佔滿整排,不要被擠在一格裡換行 */
.lsdlg>.lsh,.lsdlg>.lss,.lsdlg>.lstabs{flex:none}.lssub{padding-top:0}.lssub button{font-size:13px;min-height:32px;padding:4px 12px}.lsgrid{flex:1 1 auto;min-height:0}
.lssrch{padding:0 18px 8px;flex:none}.lssrch input{width:100%;box-sizing:border-box;background:#232c3d;border:1px solid #394559;border-radius:8px;color:#e6edf7;padding:9px 12px;font-size:16px;min-height:40px}.lssrch input:focus{outline:2px solid #3fd2ff;border-color:#3fd2ff}
.lsflt{display:flex;align-items:center;gap:6px;padding:0 18px 8px;color:#c7d3e6;font-size:13px;cursor:pointer;flex:none}.lsflt input{width:16px;height:16px;accent-color:#3fd2ff}
.lstabs{display:flex;gap:6px;padding:4px 18px 10px;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none}.lstabs::-webkit-scrollbar{display:none}
.lstabs button{flex:none;background:#232c3d;border:1px solid #394559;border-radius:99px;color:#c7d3e6;padding:6px 14px;font-size:14px;cursor:pointer;min-height:36px}
.lstabs button.on{background:#2a7de1;border-color:#2a7de1;color:#fff}.lstabs button i{font-style:normal;opacity:.75;font-size:12px;margin-left:4px}
.lsgrid{padding:2px 18px 16px;overflow:auto;-webkit-overflow-scrolling:touch;display:grid;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));grid-auto-rows:max-content;align-content:start;gap:10px}
.lstile{position:relative;text-align:left;background:#1c2536;border:1px solid #33425a;border-radius:10px;color:#e6edf7;padding:8px;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:6px}
.lstile:hover,.lstile:focus-visible{border-color:#3fd2ff;box-shadow:0 0 0 2px rgba(63,210,255,.25);outline:0}
.lstile b{font-size:14px;text-align:center}.lstile{min-width:0;overflow:hidden}.lstile .im{position:relative;width:100%;aspect-ratio:5/7;overflow:hidden;flex:none}.lstile .im img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;border-radius:6px;display:block}   /* 卡圖不撐開格子 (原本圖原尺寸會跑出框外、蓋住名字) */
.lstile.ok{border-color:#2f8f5a}.lstile.ok b::after{content:"✓";margin-left:5px;color:#4cd488;font-weight:700}
#lsbar{position:fixed;top:60px;left:50%;transform:translateX(-50%);z-index:600;background:#16324a;color:#fff;border:1px solid #3fd2ff;border-radius:10px;padding:8px 12px;width:min(720px,calc(100vw - 16px));box-sizing:border-box;box-shadow:0 4px 18px rgba(0,0,0,.5);font-size:14px}
#lsbar.ok{background:#14382a;border-color:#4cd488}
#lsbar .r1{display:flex;align-items:center;gap:8px;flex-wrap:wrap}#lsbar .nm{color:#3fd2ff;font-weight:700;white-space:nowrap}#lsbar.ok .nm{color:#4cd488}
#lsbar .dots{display:flex;gap:4px}#lsbar .dots i{width:8px;height:8px;border-radius:50%;background:#456;display:block}#lsbar .dots i.d{background:#4cd488}#lsbar .dots i.c{background:#3fd2ff;box-shadow:0 0 0 2px rgba(63,210,255,.35)}
#lsbar .sp{flex:1}#lsbar button{background:#ffffff14;border:1px solid #ffffff30;border-radius:6px;color:#e6edf7;cursor:pointer;font-size:13px;padding:4px 10px;min-height:32px}
#lsbar button.pri{background:#2a7de1;border-color:#2a7de1;color:#fff}#lsbar.ok button.pri{background:#2f8f5a;border-color:#2f8f5a}
#lsbar .st{margin-top:6px;line-height:1.5}#lspass{position:fixed;inset:0;z-index:9000;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center}
.lspd{padding:22px 26px;text-align:center;max-width:min(380px,calc(100vw - 32px));min-width:0;height:auto;border:1px solid #4cd488}.lspt{font-size:22px;font-weight:700;color:#4cd488}.lsps{margin:6px 0 16px;color:#c7d3e6}
.lspb{display:flex;flex-direction:column;gap:8px}.lspb button{background:#232c3d;border:1px solid #394559;border-radius:8px;color:#e6edf7;font-size:15px;padding:10px;min-height:44px;cursor:pointer}.lspb button.pri{background:#2f8f5a;border-color:#2f8f5a;color:#fff}
#lsbar .cl{margin-top:6px;max-height:34vh;overflow:auto;display:flex;flex-direction:column;gap:4px}#lsbar .ci{display:flex;align-items:flex-start;gap:8px;line-height:1.45;font-size:13px}#lsbar .ci .ck{flex:none;width:16px;text-align:center;color:#8aa3bf}#lsbar .ci.ok .ck{color:#4cd488;font-weight:700}#lsbar .ci.ok .ct{opacity:.55;text-decoration:line-through}#lsbar .ci .ct{flex:1}#lsbar .ci button{flex:none;min-height:26px;padding:2px 8px;font-size:12px}
#lsbar .wr{padding:6px 10px;background:#4a1d1d;border:1px solid #e0605a;border-radius:6px;color:#ffd5d2;font-size:13px}#lsbar .tp{margin-top:6px;padding:6px 10px;background:#0b1622;border-radius:6px;font-size:13px;color:#cfe0f5;max-height:32vh;overflow:auto}
#lsbar .tp p{margin:3px 0;line-height:1.5;white-space:pre-line}
body.ls-on #modal .modal{padding-top:var(--lspush,0)!important;box-sizing:border-box;align-items:safe center!important}   /* 詢問視窗往下讓開步驟列 */
@media (max-width:600px){#lsbar{top:52px;font-size:13px}.lsgrid{grid-template-columns:repeat(2,1fr)}}
`;
  const addCss = () => { if (!document.getElementById("lscss")) document.head.append(el("style", { id: "lscss", text: css })); };

  const close = () => { const b = document.getElementById("lsov"); if (b) b.remove(); };

  const ranked = () => typeof S !== "undefined" && S.rankedLive;   // 自己正在打段位局: 不能開練習關卡 (會離開對局)
  const rankedMsg = () => ({ zh: "段位對局進行中,無法開始練習關卡", en: "Can't start a practice level during a ranked game", ja: "ランク戦の最中は練習ステージを始められません" })[(window.SGS_I18N && SGS_I18N.lang) || "zh"];

  async function open(t) {
    if (ranked()) { toast(rankedMsg()); return; }
    if (!synced && typeof api === "function") { synced = true; api("/api/lessons_sync", { ids: Object.keys(doneMap()) }).then(() => { if (typeof loadProfile === "function") loadProfile(); }).catch(() => { synced = false; }); }   // 以前通關的關卡只存在這台瀏覽器: 補報給伺服器 (全通關拿新兵框)
    addCss(); close();
    const box = el("div", { id: "lsov", onclick: e => { if (e.target === box) close(); } });
    document.body.append(box);
    box.append(el("div", { class: "lsdlg" }, el("div", { class: "lsh" }, el("b", { text: tx("title") })), el("div", { class: "lss", text: tx("load") })));
    let cat;
    try { cat = await load(); } catch (e) { box.textContent = ""; box.append(el("div", { class: "lsdlg" }, el("div", { class: "lss", text: String(e) }))); return; }
    if (!document.getElementById("lsov")) return;
    if (t) tab = t;
    if (!tab || !cat.groups.includes(tab)) tab = cat.groups[0];
    const dm = doneMap(), by = g => cat.lessons.filter(L => L.group === g);
    const total = cat.lessons.length, nd = cat.lessons.filter(L => dm[L.id]).length;
    const tabs = el("div", { class: "lstabs", role: "tablist" }, cat.groups.map(g => {
      const ls = by(g);
      return el("button", { type: "button", role: "tab", class: g === tab ? "on" : "", onclick: () => open(g) }, gname(g), el("i", { text: ls.filter(L => dm[L.id]).length + "/" + ls.length }));
    }));
    const facs = tab === "武將" ? ["魏", "蜀", "吳", "群", "晉"].filter(f => by(tab).some(L => L.faction === f)) : [];
    if (!facs.includes(fac)) fac = "";
    const sub = facs.length ? el("div", { class: "lstabs lssub", role: "tablist" }, ["", ...facs].map(f =>
      el("button", { type: "button", role: "tab", class: f === fac ? "on" : "", onclick: () => { fac = f; open(tab); } }, f || tx("all"), el("i", { text: String(by(tab).filter(L => !f || L.faction === f).length) })))) : null;
    if (qryTab !== tab) { qry = ""; qryTab = tab; }
    const grid = el("div", { class: "lsgrid" });
    const fill = () => {   // 只重畫格子,打字時搜尋欄不會失去焦點
      const q = qry.trim().toLowerCase();
      const hay = L => (L.name + " " + (L.intro || "") + " " + (L.tips || []).join(" ")).toLowerCase();
      grid.textContent = "";
      grid.append(...by(tab).filter(L => (!fac || L.faction === fac) && (!onlyTodo || !dm[L.id]) && (!q || hay(L).includes(q))).map(L =>
        el("button", { type: "button", title: L.intro, class: "lstile" + (dm[L.id] ? " ok" : ""), onclick: () => start(L.id) }, el("span", { class: "im" }, tileImg(L)), el("b", { text: L.name }))));
      if (!by(tab).length) grid.append(el("div", { class: "lss", text: tx("ng") }));
      else if (!grid.children.length) grid.append(el("div", { class: "lss", text: q ? tx("nores") : tx("alldone") }));
    };
    fill();
    const srch = tab === "錦囊" || tab === "武將" ? el("div", { class: "lssrch" }, el("input", { type: "search", placeholder: tx("search"), value: qry, "aria-label": tx("search"), oninput: ev => { qry = ev.target.value; fill(); } })) : null;
    const flt = el("label", { class: "lsflt" }, el("input", { type: "checkbox", onchange: ev => { onlyTodo = ev.target.checked; open(tab); } }), tx("todo"));
    flt.firstChild.checked = onlyTodo;
    box.textContent = "";
    box.append(el("div", { class: "lsdlg", role: "dialog", "aria-label": tx("title") },
      el("div", { class: "lsh" }, el("b", { text: "🎓 " + tx("title") }), el("span", { class: "sp" }), el("span", { class: "lss", style: "padding:0", text: tx("done") + " " + nd + tx("of") + total }),
        el("button", { type: "button", "aria-label": tx("leave"), text: "✕", onclick: close })),
      el("div", { class: "lss", text: tx("sub") }), tabs, sub, srch, flt, grid));
  }

  async function start(id) {
    close();
    if (ranked()) { toast(rankedMsg()); return; }
    try {
      if (window.SGS_HINT_OFF) SGS_HINT_OFF();
      curId = id; tipsOn = false;   // saved 不在這裡清掉: 新關卡還沒建好時,輪詢還會拿到上一關「已過關」的畫面,清掉會讓過關視窗再跳一次;等收到沒過關的新畫面 (sync) 才清
      if (!ROOM || ROOM !== lessonRoom) {   // 練習關卡一律開自己的私人單人房 (不動到公共房間 / 別人的房間)
        const old = ROOM;
        const r = await (await fetch("/api/room_create", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tok: TOK, name: "練習關卡", solo: true }) })).json();
        if (!r.ok) { toast("開房失敗: " + (r.error || "")); return; }
        if (old) { try { fetch("/api/leave", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tok: TOK, room: old }) }); } catch (e) {} }   // 先離開原本的房間
        lessonRoom = r.room;
        enterRoom(r.room, r.name);
        S.setupOff = r.name;   // 房間剛建好、關卡還沒開始: 不要讓輪詢自動彈出「新遊戲」視窗
      }
      S.logN = 0; S.thN = 0; S.thoughts = []; S.lastTh = {}; S.sel = null; S.picked = null; S.pendId = 0;
      document.getElementById("log").textContent = ""; document.getElementById("thl").textContent = "";
      const x = await api("/api/new", { lesson: id });
      if (x && x.ok === false) { toast("開始失敗: " + (x.error || "")); return; }
      const M = document.getElementById("modal"); M.textContent = ""; S.modalOpen = null;
      poll(true);
    } catch (e) { alert(String(e)); }
  }

  const nextOf = id => {
    if (!CAT) return null;
    const i = CAT.lessons.findIndex(L => L.id === id);
    return i >= 0 && i + 1 < CAT.lessons.length ? CAT.lessons[i + 1] : null;
  };

  const push = bar => { const r = bar.getBoundingClientRect(); document.body.style.setProperty("--lspush", Math.ceil(r.bottom + 8) + "px"); };

  function passDlg(ls) {   // 過關: 告訴玩家通過了,並可回到教學選單
    addCss();
    const old = document.getElementById("lspass"); if (old) old.remove();
    const nx = nextOf(ls.id), shut = () => { const d = document.getElementById("lspass"); if (d) d.remove(); };
    const box = el("div", { id: "lspass" }, el("div", { class: "lsdlg lspd", role: "dialog" },
      el("div", { class: "lspt", text: "🎓 " + tx("pass") }), el("div", { class: "lsps", text: gname(ls.group) + " · " + ls.name }),
      el("div", { class: "lspb" },
        el("button", { type: "button", class: "pri", text: tx("menu"), onclick: () => { shut(); api("/api/lesson_leave", {}).then(() => open(ls.group)).catch(() => open(ls.group)); } }),
        nx ? el("button", { type: "button", text: tx("next") + " ›", onclick: () => { shut(); start(nx.id); } }) : null,
        el("button", { type: "button", text: "↻ " + tx("again"), onclick: () => { shut(); start(ls.id); } }))));
    document.body.append(box);
  }

  function sync(snap) {
    const ls = snap && snap.lesson;
    let bar = document.getElementById("lsbar");
    if (!ls) { if (bar) bar.remove(); curId = null; document.body.classList.remove("ls-on"); return; }
    addCss(); load().catch(() => {});
    curId = ls.id;
    if (ls.done && !saved) { saved = true; markDone(ls.id); passDlg(ls); }
    if (!ls.done) saved = false;
    if (!bar) { bar = el("div", { id: "lsbar", role: "status" }); document.body.append(bar); }
    bar.className = ls.done ? "ok" : "";
    const nx = nextOf(ls.id), n = ls.steps.length;
    const text = ls.done ? "✅ " + tx("ok") : n ? ls.steps[Math.min(ls.cur, n - 1)] : tx("free");
    const got = ls.got || [], sig = [ls.id, ls.cur, ls.done, tipsOn, n, ls.hint || "", got.join(","), window.SGS_I18N ? SGS_I18N.lang : ""].join("|");
    document.body.classList.add("ls-on");
    if (bar.dataset.sig === sig) { push(bar); return; }
    bar.dataset.sig = sig;
    bar.textContent = "";
    bar.append(el("div", { class: "r1" },
      el("span", { class: "nm", text: "🎓 " + gname(ls.group) + " · " + ls.name }),
      n ? el("span", { class: "dots", "aria-label": tx("step") + " " + Math.min(ls.cur + 1, n) + "/" + n }, ls.steps.map((_, i) => el("i", { class: ls.checklist ? (ls.done || got.includes(i) ? "d" : "") : ls.done || i < ls.cur ? "d" : i === ls.cur ? "c" : "" }))) : null,
      el("span", { class: "sp" }),
      ls.tips && ls.tips.length ? el("button", { type: "button", text: "💡 " + tx("tips"), onclick: () => { tipsOn = !tipsOn; sync(S.snap || snap); } }) : null,
      el("button", { type: "button", text: "↻ " + tx("retry"), onclick: () => start(ls.id) }),
      ls.done && nx ? el("button", { type: "button", class: "pri", text: tx("next") + " ›", onclick: () => start(nx.id) }) : null,
      !ls.done && ls.free ? el("button", { type: "button", class: "pri", text: "✔ " + tx("fin"), onclick: () => api("/api/lesson_done", {}).then(() => poll(true)) }) : null,
      el("button", { type: "button", text: "☰", "aria-label": tx("title"), title: tx("title"), onclick: () => open(ls.group) }),
      el("button", { type: "button", text: "✕ " + tx("leave"), onclick: () => { if (confirm(tx("ask"))) { bar.remove(); curId = null; document.body.classList.remove("ls-on"); api("/api/lesson_leave", {}).then(() => { if (window.openSetup) openSetup(); }).catch(() => {}); } } })));
    if (ls.checklist && !ls.done) {   // 武將關: 每個技能一項,不分順序,全部打勾才過關
      bar.append(el("div", { class: "cl" }, ls.steps.map((t, i) => {
        const ok = got.includes(i);
        return el("div", { class: "ci" + (ok ? " ok" : "") }, el("span", { class: "ck", text: ok ? "✓" : "○" }), el("span", { class: "ct", text: t }),
          !ok && ls.manual && ls.manual[i] ? el("button", { type: "button", text: tx("seen"), onclick: () => api("/api/lesson_ack", { i }).then(() => poll(true)).catch(() => {}) }) : null);
      })));
    } else bar.append(el("div", { class: "st", text: text }));
    if (ls.hint && !ls.done) bar.append(el("div", { class: "st wr", text: ls.hint }));
    if (tipsOn && ls.tips && ls.tips.length) bar.append(el("div", { class: "tp" }, el("p", { text: ls.intro }), ls.tips.map(x => el("p", { text: /^\d+[.、]/.test(x) ? x : "• " + x }))));
    push(bar);
  }

  window.SGS_LESSON = { open, start, sync };
})();
