/* 動畫特效 (聲望限定外觀): 每組 = 進場 + 勝利 + 落敗。完全不用文字,全部是圖形。
 * 播在玩家的座位上,所有人 (含觀戰) 都看得到;本人勝負時改看全螢幕版。
 * 動畫以 transform / opacity 為主;開了「減少動態」就只淡入淡出一個光點。 */
(function () {
  "use strict";
  const THEMES = {   // g = 外觀視窗裡的小圖示 (圖形符號,不是文字)
    ink:     { g: "🖌️", c1: "#f1e8d2", c2: "#c8281e", c3: "#14110f", ic: "linear-gradient(135deg,#f1e8d2 50%,#c8281e 50%)" },
    sakura:  { g: "🌸", c1: "#ffd1e6", c2: "#ff8fc0", c3: "#b08a96", ic: "linear-gradient(135deg,#ffd1e6 50%,#ff6fa8 50%)" },
    thunder: { g: "⚡", c1: "#e8f6ff", c2: "#6aa8ff", c3: "#ffe14d", ic: "linear-gradient(135deg,#18306a 50%,#ffe14d 50%)" },
    flame:   { g: "🔥", c1: "#ffd27a", c2: "#ff4d1f", c3: "#7a0e00", ic: "linear-gradient(135deg,#ff4d1f 50%,#ffd27a 50%)" },
    pixel:   { g: "👾", c1: "#9bffd8", c2: "#ff4df0", c3: "#1b0b3a", ic: "linear-gradient(135deg,#ff4df0 50%,#3dffd0 50%)" },
    bushi:   { g: "🗡️", c1: "#f4f4f2", c2: "#8a8a86", c3: "#14110f", ic: "linear-gradient(135deg,#14110f 50%,#f4f4f2 50%)" },
  };
  const DUR = { in: 1.9, win: 3.4, lose: 3.1, hurt: 1.0, heal: 1.4, atk: 1.1, die: 2.0 };
  const reduce = () => { try { return matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; } };

  const CSS = `
.anm{position:fixed;pointer-events:none;z-index:19;contain:layout style;overflow:visible}
.anm>*{position:absolute;box-sizing:border-box;will-change:transform,opacity}
.anm .bg{inset:0;animation:anm-bg var(--T) ease-in-out both}
.anm .sv{left:50%;top:50%;width:calc(var(--u)*var(--sz));height:calc(var(--u)*var(--sz));overflow:visible;transform:translate(-50%,-50%);animation:var(--an) var(--t) cubic-bezier(.2,.9,.25,1.05) var(--dl) both}
.anm .glow{filter:drop-shadow(0 0 calc(var(--u)*1.2) var(--gc)) drop-shadow(0 0 calc(var(--u)*3.5) var(--gc))}
.anm .mono{filter:grayscale(.9) brightness(.78)}
.anm .rg{left:50%;top:50%;width:calc(var(--u)*20);height:calc(var(--u)*20);border-radius:50%;border:calc(var(--u)*1.1) solid var(--c);transform:translate(-50%,-50%) scale(.1);animation:anm-ring var(--t,1.4s) cubic-bezier(.1,.7,.3,1) var(--dl,0s) both}
.anm .ray{left:50%;top:50%;width:calc(var(--u)*150);height:calc(var(--u)*150);border-radius:50%;background:repeating-conic-gradient(from 0deg,var(--c) 0 5deg,transparent 5deg 16deg);-webkit-mask-image:radial-gradient(circle,#000 8%,transparent 62%);mask-image:radial-gradient(circle,#000 8%,transparent 62%);transform:translate(-50%,-50%);animation:anm-ray var(--t,var(--T)) ease-out var(--dl,0s) both}
.anm .pt{left:calc(var(--x)*1%);top:calc(var(--y)*1%);width:calc(var(--u)*var(--s));height:calc(var(--u)*var(--s));background:var(--c);border-radius:50%;animation:anm-fly var(--t) cubic-bezier(.2,.6,.3,1) var(--dl) both}
.anm .pt.pe{border-radius:150% 0 150% 0;width:calc(var(--u)*var(--s)*1.5);height:calc(var(--u)*var(--s)*.95)}
.anm .pt.sq{border-radius:1px}
.anm .pt.ln{width:calc(var(--u)*.35);height:calc(var(--u)*var(--s)*2.2);border-radius:2px;opacity:.7}
.anm .pt.em{box-shadow:0 0 calc(var(--u)*1.4) calc(var(--u)*.3) var(--c)}
.anm .pt.co{background:radial-gradient(circle at 35% 30%,#fff7c8,#ffc928 55%,#b97500);box-shadow:inset 0 0 0 calc(var(--u)*.25) rgba(120,60,0,.55)}
.anm .pt.sm{background:radial-gradient(circle,rgba(110,110,110,.75),rgba(110,110,110,0) 70%);animation-name:anm-smoke}
.anm .fire{left:calc(var(--x)*1%);bottom:-3%;width:calc(var(--u)*var(--w));height:calc(var(--u)*var(--w)*1.9);margin-left:calc(var(--u)*var(--w)*-.5);transform-origin:50% 100%;overflow:visible;animation:var(--an,anm-fire) var(--t) ease-out var(--dl) both}
.anm .fire path{transform-box:fill-box;transform-origin:50% 100%;animation:anm-flick var(--fk) ease-in-out var(--fd) infinite}
.anm .heat{left:calc(var(--bx0,0)*100%);width:calc((var(--bx1,1) - var(--bx0,0))*100%);bottom:calc((1 - var(--by,1.1))*100%);height:calc(var(--hs,.7)*100%);background:radial-gradient(ellipse at 50% 100%,var(--c),transparent 68%);animation:anm-bg var(--T) ease-in-out both}
.anm:not([data-full="1"]) .heat{--hs:.3}
.anm .blob{left:calc(var(--x)*1%);top:calc(var(--y)*1%);width:calc(var(--u)*var(--s));height:calc(var(--u)*var(--s));border-radius:var(--br);background:radial-gradient(circle,var(--c) 40%,transparent 72%);transform:translate(-50%,-50%) scale(0);animation:anm-blob var(--t) cubic-bezier(.1,.7,.3,1) var(--dl) both}
.anm .brush{left:50%;top:calc(var(--y)*1%);width:calc(var(--u)*var(--s));height:calc(var(--u)*2.4);border-radius:50% 12% 50% 12%/100% 30% 100% 30%;background:linear-gradient(90deg,transparent,var(--c) 18%,var(--c) 82%,transparent);transform:translateX(-50%) rotate(var(--r)) scaleX(0);animation:anm-brush var(--t) ease-out var(--dl) both}
.anm .drip{left:calc(var(--x)*1%);top:calc(var(--y)*1%);width:calc(var(--u)*var(--s));height:calc(var(--u)*var(--h));border-radius:0 0 50% 50%;background:linear-gradient(var(--c),var(--c) 85%,rgba(0,0,0,.6));transform-origin:50% 0;transform:scaleY(0);animation:anm-drip var(--t) cubic-bezier(.4,0,.6,1) var(--dl) both}
.anm .shake{inset:0;animation:anm-shake .45s linear .5s both}
.anm .fl{inset:0;background:radial-gradient(circle at 50% 50%,var(--c) 0,transparent 68%);animation:anm-flash .7s ease-out var(--dl,0s) both}
.anm svg.bolt{left:calc(var(--x)*1%);top:0;width:calc(var(--u)*22);height:62%;margin-left:calc(var(--u)*-11);overflow:visible;animation:anm-bolt .9s linear var(--dl) both}
.anm .cloud{left:calc(var(--x)*1%);top:-6%;width:calc(var(--u)*var(--s));height:calc(var(--u)*var(--s)*.5);margin-left:calc(var(--u)*var(--s)*-.5);border-radius:50%;background:radial-gradient(ellipse,rgba(70,78,98,.95),rgba(40,44,60,0) 70%);animation:anm-cloud var(--T) ease-out var(--dl) both}
.anm .dot{left:50%;top:50%;width:calc(var(--u)*14);height:calc(var(--u)*14);border-radius:50%;background:radial-gradient(circle,#fff,var(--c) 60%,transparent 72%);transform:translate(-50%,-50%);animation:anm-fade var(--T) ease both}
.anm .shot{left:calc(var(--x,0)*1%);width:calc(var(--u)*var(--w,6));height:calc(var(--u)*var(--h,6));margin:calc(var(--u)*var(--h,6)*-.5) 0 0 calc(var(--u)*var(--w,6)*-.5);background:var(--c);border-radius:50%;animation:anm-shot var(--t,.45s) cubic-bezier(.5,0,.8,.6) var(--dl,0s) both}
.anm .shot.pe{border-radius:150% 0 150% 0}
.anm .shot.ball{background:radial-gradient(circle,#fff6c4 0,#ffb02e 34%,#ff4d0a 64%,rgba(255,40,0,0) 72%);box-shadow:0 0 calc(var(--u)*3) calc(var(--u)*.8) rgba(255,110,20,.75)}
.anm .shot.gold{background:radial-gradient(circle,#fffbe0 0,#ffd24a 40%,#c88a10 68%,rgba(200,138,16,0) 74%);box-shadow:0 0 calc(var(--u)*3) calc(var(--u)*.8) rgba(255,200,60,.7)}
.anm .slash{width:var(--len);height:calc(var(--u)*var(--h,2.4));margin-top:calc(var(--u)*var(--h,2.4)*-.5);transform-origin:0 50%;border-radius:50%;background:linear-gradient(90deg,transparent,var(--c) 14%,var(--c) 88%,transparent);animation:anm-slash .55s ease-out var(--dl,0s) both}
.anm svg.bolt2{left:0;top:0;width:100%;height:100%;overflow:visible;animation:anm-bolt .7s linear var(--dl,0s) both}
.anm .sv.stp{animation-timing-function:steps(10,end)}
.anm .pt.px{border-radius:0;animation-timing-function:steps(8,end);box-shadow:0 0 calc(var(--u)*1.2) var(--c)}
.anm .rg.pq{border-radius:0;animation-timing-function:steps(6,end)}
.anm .shot.px{border-radius:0;background:var(--c);box-shadow:0 0 calc(var(--u)*2) var(--c);animation-timing-function:steps(9,end)}
.anm .gl{left:0;right:0;top:calc(var(--y)*1%);height:calc(var(--u)*var(--h));background:var(--c);opacity:0;animation:anm-glitch var(--t,.9s) steps(1,end) var(--dl,0s) both}
@keyframes anm-glitch{0%{opacity:.85;transform:translateX(-5%)}12%{opacity:0}24%{opacity:.85;transform:translateX(6%)}36%{opacity:0}48%{opacity:.75;transform:translateX(-3%)}60%{opacity:0}72%{opacity:.6;transform:translateX(2%)}84%{opacity:0}100%{opacity:0}}
@keyframes anm-pxdrop{0%{transform:translate(-50%,-170%);opacity:1}30%{transform:translate(-50%,-50%)}62%{opacity:1}68%{opacity:.15}74%{opacity:1}88%{opacity:1}100%{transform:translate(-50%,-50%);opacity:0}}
@keyframes anm-pxwin{0%{transform:translate(-50%,-50%) scale(0);opacity:0}12%{transform:translate(-50%,-50%) scale(1.35);opacity:1}22%{transform:translate(-50%,-50%) scale(1)}38%{transform:translate(-50%,-58%)}54%{transform:translate(-50%,-50%)}70%{transform:translate(-50%,-58%)}84%{transform:translate(-50%,-50%);opacity:1}100%{transform:translate(-50%,-50%) scale(1.1);opacity:0}}
@keyframes anm-pxfall{0%{transform:translate(-50%,-50%);opacity:0}8%{opacity:1}45%{transform:translate(-50%,-50%);opacity:1}100%{transform:translate(-50%,calc(-50% + var(--u)*40));opacity:0}}
@keyframes anm-cutv{0%{opacity:1}60%{opacity:1}100%{opacity:0}}
.anm .shot.kn{background:none;border-radius:0;box-shadow:none;animation-timing-function:cubic-bezier(.35,0,.7,.7)}
@keyframes anm-shot{0%{transform:translate(0,0) rotate(var(--ang)) scale(.5);opacity:0}15%{opacity:1}90%{opacity:1}100%{transform:translate(var(--mx),var(--my)) rotate(var(--ang)) scale(1);opacity:0}}
@keyframes anm-slash{0%{transform:rotate(var(--ang)) scaleX(0);opacity:1}55%{transform:rotate(var(--ang)) scaleX(1);opacity:1}100%{transform:rotate(var(--ang)) scaleX(1);opacity:0}}
.anm .rot{transform-box:fill-box;transform-origin:50% 50%;animation:anm-rotg 4s linear infinite}
@keyframes anm-bg{0%{opacity:0}18%{opacity:1}78%{opacity:1}100%{opacity:0}}
@keyframes anm-pop{0%{transform:translate(-50%,-50%) scale(var(--s0,1)) rotate(var(--r0,0deg));opacity:0}20%{transform:translate(-50%,-50%) scale(1) rotate(0);opacity:1}78%{transform:translate(-50%,-50%) scale(1.04);opacity:1}100%{transform:translate(-50%,-50%) scale(1.16);opacity:0}}
@keyframes anm-zap{0%{opacity:0;transform:translate(-50%,-50%) scale(1.4)}8%{opacity:1;transform:translate(-50%,-50%) scale(1)}15%{opacity:.25}22%{opacity:1}72%{opacity:1;transform:translate(-50%,-50%) scale(1.03)}100%{opacity:0;transform:translate(-50%,-50%) scale(1.1)}}
@keyframes anm-bloom{0%{transform:translate(-50%,-50%) rotate(calc(var(--a) - 70deg)) scale(0);opacity:0}28%{transform:translate(-50%,-50%) rotate(var(--a)) scale(1.07);opacity:1}38%{transform:translate(-50%,-50%) rotate(var(--a)) scale(1)}80%{transform:translate(-50%,-50%) rotate(calc(var(--a) + 8deg)) scale(1);opacity:1}100%{transform:translate(-50%,-50%) rotate(calc(var(--a) + 14deg)) scale(1.08);opacity:0}}
@keyframes anm-wilt{0%{transform:translate(-50%,-50%) rotate(calc(var(--a) - 60deg)) scale(0);opacity:0}22%{transform:translate(-50%,-50%) rotate(var(--a)) scale(1);opacity:1}42%{transform:translate(-50%,-50%) rotate(var(--a)) scale(1);opacity:1}100%{transform:translate(calc(-50% + var(--u)*var(--dx)),calc(-50% + var(--u)*var(--dy))) rotate(calc(var(--a) + var(--wr))) scale(.9);opacity:0}}
@keyframes anm-stamp{0%{transform:translate(-50%,-50%) scale(3.2) rotate(-16deg);opacity:0}26%{transform:translate(-50%,-50%) scale(.9) rotate(-7deg);opacity:1}34%{transform:translate(-50%,-50%) scale(1.05) rotate(-7deg)}42%{transform:translate(-50%,-50%) scale(1) rotate(-7deg)}82%{opacity:1}100%{transform:translate(-50%,-50%) scale(1) rotate(-7deg);opacity:0}}
@keyframes anm-draw{from{stroke-dashoffset:100}to{stroke-dashoffset:0}}
@keyframes anm-rotg{to{transform:rotate(360deg)}}
@keyframes anm-ring{0%{transform:translate(-50%,-50%) scale(.1);opacity:.95}100%{transform:translate(-50%,-50%) scale(var(--sc,5));opacity:0}}
@keyframes anm-ray{0%{transform:translate(-50%,-50%) rotate(0) scale(.35);opacity:0}22%{opacity:.7}100%{transform:translate(-50%,-50%) rotate(var(--rot,80deg)) scale(1.05);opacity:0}}
@keyframes anm-fly{0%{transform:translate(0,0) scale(.3) rotate(0);opacity:0}14%{opacity:1}100%{transform:translate(calc(var(--u)*var(--dx)),calc(var(--u)*var(--dy))) scale(1) rotate(var(--r,0deg));opacity:0}}
@keyframes anm-smoke{0%{transform:translate(0,0) scale(.3);opacity:0}25%{opacity:.8}100%{transform:translate(calc(var(--u)*var(--dx)),calc(var(--u)*var(--dy))) scale(2.4);opacity:0}}
@keyframes anm-fire{0%{transform:scaleY(.08) scaleX(.6);opacity:0}18%{transform:scaleY(.75) scaleX(.95);opacity:1}55%{transform:scaleY(1.05) scaleX(1);opacity:1}100%{transform:scaleY(1.12) scaleX(.9) translateY(-5%);opacity:0}}
@keyframes anm-fireout{0%{transform:scaleY(1) scaleX(1);opacity:1}100%{transform:scaleY(.08) scaleX(.7);opacity:0}}
@keyframes anm-flick{0%{transform:scale(1,1) skewX(0)}25%{transform:scale(.92,1.08) skewX(4deg)}50%{transform:scale(1.05,.94) skewX(-3deg)}75%{transform:scale(.95,1.06) skewX(-5deg)}100%{transform:scale(1,1) skewX(0)}}
@keyframes anm-blob{0%{transform:translate(-50%,-50%) scale(0);opacity:.95}70%{opacity:.8}100%{transform:translate(-50%,-50%) scale(1);opacity:0}}
@keyframes anm-brush{0%{transform:translateX(-50%) rotate(var(--r)) scaleX(0);opacity:1}35%{transform:translateX(-50%) rotate(var(--r)) scaleX(1);opacity:1}100%{transform:translateX(-50%) rotate(var(--r)) scaleX(1.05);opacity:0}}
@keyframes anm-drip{0%{transform:scaleY(0);opacity:1}55%{transform:scaleY(1);opacity:1}100%{transform:scaleY(1.04) translateY(calc(var(--u)*6));opacity:0}}
@keyframes anm-shake{0%,100%{transform:translate(0,0)}15%{transform:translate(calc(var(--u)*-1.2),calc(var(--u)*.8))}35%{transform:translate(calc(var(--u)*1.1),calc(var(--u)*-.9))}60%{transform:translate(calc(var(--u)*-.6),calc(var(--u)*.5))}80%{transform:translate(calc(var(--u)*.4),0)}}
@keyframes anm-flash{0%{opacity:0}10%{opacity:.85}100%{opacity:0}}
@keyframes anm-bolt{0%{opacity:0}6%{opacity:1}14%{opacity:.25}22%{opacity:1}60%{opacity:.7}100%{opacity:0}}
@keyframes anm-cloud{0%{transform:translateY(-40%) scale(.6);opacity:0}30%{opacity:1}80%{opacity:1;transform:translateY(25%) scale(1.15)}100%{opacity:0;transform:translateY(30%) scale(1.2)}}
@keyframes anm-hl{0%,28%{transform:translate(-50%,-50%) rotate(0);opacity:1}100%{transform:translate(calc(-50% - var(--u)*14),calc(-50% + var(--u)*38)) rotate(-24deg);opacity:0}}
@keyframes anm-hr{0%,28%{transform:translate(-50%,-50%) rotate(0);opacity:1}100%{transform:translate(calc(-50% + var(--u)*14),calc(-50% + var(--u)*44)) rotate(26deg);opacity:0}}
@keyframes anm-fade{0%{opacity:0}30%{opacity:1}75%{opacity:1}100%{opacity:0}}
@keyframes anm-spin{0%{transform:translate(-50%,-50%) rotate(0);opacity:0}15%{opacity:1}80%{opacity:1}100%{transform:translate(-50%,-50%) rotate(var(--rot,160deg));opacity:0}}
`;
  function css() {
    if (document.getElementById("anm-css")) return;
    const s = document.createElement("style"); s.id = "anm-css"; s.textContent = CSS; document.head.append(s);
  }

  /* ---- 小工具 ---- */
  let sd = 7;
  const rnd = () => { sd = (sd * 1664525 + 1013904223) >>> 0; return sd / 4294967296; };
  const f = n => (+n).toFixed(1);
  const col = c => `--c:${c};`;
  const pt = (cls, c, x, y, s, dx, dy, t, dl, r) => `<i class="pt ${cls}" style="${col(c)}--x:${f(x)};--y:${f(y)};--s:${f(s)};--dx:${f(dx)};--dy:${f(dy)};--t:${f(t)}s;--dl:${f(dl)}s;--r:${Math.round(r || 0)}deg"></i>`;
  const ring = (c, t, dl, sc) => `<i class="rg" style="${col(c)}--t:${t}s;--dl:${dl}s;--sc:${sc || 5}"></i>`;
  const ray = (c, t, dl, rot) => `<i class="ray" style="${col(c)}--t:${t}s;--dl:${dl}s;--rot:${rot || 80}deg"></i>`;
  const dim = (c, a) => `<i class="bg" style="background:radial-gradient(circle at 50% 50%,${c}${a || "cc"},rgba(0,0,0,.0) 78%)"></i>`;
  const many = (n, fn) => { let o = ""; for (let i = 0; i < n; i++) o += fn(i); return o; };
  const burst = (n, cls, cs, y0, d0, d1, t0, dl0, sz) => many(n, i => { const a = rnd() * 6.283, d = d0 + rnd() * (d1 - d0); return pt(cls, cs[i % cs.length], 50, y0, sz[0] + rnd() * sz[1], Math.cos(a) * d, Math.sin(a) * d, t0 + rnd() * .8, dl0 + rnd() * .5, rnd() * 360); });
  /* SVG 圖形: 以 (0,0) 為中心、-50..50 的座標。o: sz 大小(u)、dl 延遲、t 時長、an 動畫、a 旋轉、gc 發光色… */
  const sv = (inner, o = {}) => `<svg class="sv ${o.cls || ""}" viewBox="-50 -50 100 100" style="--sz:${o.sz || 40};--dl:${o.dl || 0}s;--t:${o.t ? o.t + "s" : "var(--T)"};--an:${o.an || "anm-pop"};--s0:${o.s0 || 1};--a:${o.a || 0}deg;--dx:${o.dx || 0};--dy:${o.dy || 0};--wr:${o.wr || 0}deg;--gc:${o.gc || "#fff"};${o.st || ""}">${inner}</svg>`;
  const cv = m => `<canvas class="cv" data-fire="${m}" style="left:0;top:0;width:100%;height:100%"></canvas>`;
  const halves = (inner, o = {}) => sv(inner, Object.assign({}, o, { an: "anm-hl", dl: o.dl || .9, st: "clip-path:inset(0 50% 0 0);" })) + sv(inner, Object.assign({}, o, { an: "anm-hr", dl: o.dl || .9, st: "clip-path:inset(0 0 0 50%);" }));
  const jag = (seed, x, dl, c, flip) => {   // 鋸齒閃電 (背景裝飾)
    let y = 0, cx = 50; const pts = [[50, 0]];
    while (y < 100) { y += 9 + rnd() * 9; cx = Math.max(14, Math.min(86, cx + (rnd() - .5) * 46)); pts.push([cx, Math.min(y, 100)]); }
    const p = pts.map(v => v[0].toFixed(1) + "," + v[1].toFixed(1)).join(" ");
    return `<svg class="bolt" viewBox="0 0 100 100" preserveAspectRatio="none" style="--x:${x};--dl:${dl}s${flip ? ";transform:scaleX(-1)" : ""}"><polyline points="${p}" fill="none" stroke="${c}" stroke-linejoin="round" opacity=".35" vector-effect="non-scaling-stroke" style="stroke-width:9px"/><polyline points="${p}" fill="none" stroke="#fff" stroke-linejoin="round" vector-effect="non-scaling-stroke" style="stroke-width:2.6px"/></svg>`;
  };

  /* ---- 圖形素材 ---- */
  const enso = (c, w, gap, gid) => {   // 圓相: 一筆畫出的圓,有飛白的細筆疊在上面
    const g = gap || .35, R = 30, ex = (-R * Math.sin(g)).toFixed(1), ey = (-R * Math.cos(g)).toFixed(1);
    const draw = "stroke-dasharray:100;stroke-dashoffset:100;animation:anm-draw 1.1s ease-out .15s forwards";
    return `<path pathLength="100" d="M0,-${R} A${R},${R} 0 1 1 ${ex},${ey}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" style="${draw}"/>`
      + `<path pathLength="100" d="M-4,-${R - 2.6} A${R - 2.6},${R - 2.6} 0 1 1 ${(-(R - 2.6) * Math.sin(g + .12)).toFixed(1)},${(-(R - 2.6) * Math.cos(g + .12)).toFixed(1)}" fill="none" stroke="${c}" stroke-width="${(w * .35).toFixed(1)}" stroke-linecap="round" opacity=".7" style="${draw.replace(".15s", ".3s")}"/>`;
  };
  const seal = (lose) => {   // 朱印: 紅底方章,中間一個圓相;敗: 灰、圓相斷開、裂痕
    const bg = lose ? "#6e3a34" : "#c8281e", fg = "#f6e9d4";
    return `<rect x="-32" y="-32" width="64" height="64" rx="3" fill="${bg}"/><rect x="-27.5" y="-27.5" width="55" height="55" fill="none" stroke="${fg}" stroke-width="2"/>`
      + `<path d="M0,-17 A17,17 0 1 1 ${lose ? "-13,-11" : "-4,-16.5"}" fill="none" stroke="${fg}" stroke-width="5.5" stroke-linecap="round"/>`
      + (lose ? `<polyline points="-30,-6 -12,2 -18,14 6,20 0,32" fill="none" stroke="#1b0d0a" stroke-width="1.6"/><polyline points="24,-30 14,-12 26,0" fill="none" stroke="#1b0d0a" stroke-width="1.4"/>` : `<circle cx="14" cy="14" r="2.4" fill="${fg}"/>`);
  };
  const petalDef = `<defs><linearGradient id="anmP" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="-33"><stop offset="0" stop-color="#ff5c9b"/><stop offset=".55" stop-color="#ff9cc7"/><stop offset="1" stop-color="#ffe6f0"/></linearGradient></defs>`;
  const petal = `${petalDef}<path d="M0,0 C-14,-8 -14,-30 -4.5,-34 L0,-28.5 L4.5,-34 C14,-30 14,-8 0,0Z" fill="url(#anmP)" stroke="#ff7fb2" stroke-width=".5"/><path d="M0,-4 L0,-24" stroke="#ff5c9b" stroke-width=".7" opacity=".55"/>`;
  const stamen = () => { let o = `<circle r="5" fill="#ffb11f"/>`; for (let i = 0; i < 10; i++) { const a = i * 36 * Math.PI / 180, r1 = 5, r2 = 12 + (i % 2) * 3; o += `<line x1="${(Math.cos(a) * r1).toFixed(1)}" y1="${(Math.sin(a) * r1).toFixed(1)}" x2="${(Math.cos(a) * r2).toFixed(1)}" y2="${(Math.sin(a) * r2).toFixed(1)}" stroke="#d8326e" stroke-width=".8"/><circle cx="${(Math.cos(a) * r2).toFixed(1)}" cy="${(Math.sin(a) * r2).toFixed(1)}" r="1.5" fill="#ffd34a"/>`; } return o; };
  const orb = () => {   // 電漿球: 白熱核心 + 向外延伸的電絲 (取代閃電符號)
    let o = `<defs><radialGradient id="anmO"><stop offset="0" stop-color="#fff"/><stop offset=".22" stop-color="#e8f6ff"/><stop offset=".5" stop-color="#7fb4ff" stop-opacity=".9"/><stop offset="1" stop-color="#2a5cff" stop-opacity="0"/></radialGradient></defs><circle r="46" fill="url(#anmO)"/>`;
    for (let k = 0; k < 8; k++) {
      let a = k * 6.283 / 8 + rnd() * .4, r = 6, pts = "";
      for (let i = 0; i < 7; i++) { a += (rnd() - .5) * .55; r += 5.5; pts += `${(Math.cos(a) * r).toFixed(1)},${(Math.sin(a) * r).toFixed(1)} `; }
      o += `<polyline points="${pts}" fill="none" stroke="#9fd0ff" stroke-width="4" stroke-linejoin="round" opacity=".35"/><polyline points="${pts}" fill="none" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/>`;
    }
    return o + `<circle r="8" fill="#fff"/>`;
  };
  const arcs = (n, c) => {   // 圍成一圈的電弧
    let o = "";
    for (let k = 0; k < n; k++) {
      const a0 = k * 6.283 / n, span = 6.283 / n * .7; let pts = "";
      for (let i = 0; i <= 8; i++) { const a = a0 + span * i / 8, r = 40 + (i % 2 ? 4 : -4) * (.5 + rnd()); pts += `${(Math.cos(a) * r).toFixed(1)},${(Math.sin(a) * r).toFixed(1)} `; }
      o += `<polyline points="${pts}" fill="none" stroke="${c}" stroke-width="1.8" stroke-linejoin="round" opacity=".9"/><polyline points="${pts}" fill="none" stroke="#fff" stroke-width=".7" stroke-linejoin="round"/>`;
    }
    return o;
  };
  /* 像素精靈: 用文字格子畫 (# = 主色, h = 亮點),以 (0,0) 為中心、塞進 -50..50 */
  const spr = (rows, c, hi) => {
    const w = rows[0].length, h = rows.length, k = 100 / Math.max(w, h), x0 = -w * k / 2, y0 = -h * k / 2; let o = `<g shape-rendering="crispEdges">`;
    rows.forEach((r, y) => { for (let x = 0; x < w; x++) { const ch = r[x]; if (ch === "#" || ch === "h") o += `<rect x="${(x0 + x * k).toFixed(2)}" y="${(y0 + y * k).toFixed(2)}" width="${(k + .15).toFixed(2)}" height="${(k + .15).toFixed(2)}" fill="${ch === "h" ? (hi || "#fff") : c}"/>`; } });
    return o + "</g>";
  };
  const INV = ["..#.....#..", "...#...#...", "..#######..", ".##h###h##.", "###########", "#.#######.#", "#.#.....#.#", "...##.##..."];
  const HEART = [".###.###.", "#hh######", "#h#######", "#########", ".#######.", "..#####..", "...###...", "....#...."];
  const TROPHY = ["#########", "#hh######", "#h#######", ".#######.", "..#####..", "...###...", "....#....", "...###...", "..#####.."];
  const SKULL = [".#######.", "#########", "##.###.##", "##.###.##", "#########", ".#######.", "..#.#.#..", "..#####.."];
  const PXC = ["#3dffd0", "#ff4df0", "#ffe14d", "#7a5cff"];
  const pring = (c, t, dl, sc) => `<i class="rg pq" style="${col(c)}--t:${t}s;--dl:${dl}s;--sc:${sc || 5}"></i>`;
  const gl = (c, n, t, dl) => many(n, () => `<i class="gl" style="${col(c)}--y:${f(rnd() * 90)};--h:${f(1.2 + rnd() * 2.6)};--t:${t}s;--dl:${f(dl + rnd() * .3)}s"></i>`);
  const bits = (n, cs, x0, x1, y0, y1, dx, dy, t0, dl0) => many(n, i => pt("px", cs[i % cs.length], x0 + rnd() * (x1 - x0), y0 + rnd() * (y1 - y0), 1.4 + Math.floor(rnd() * 3), (rnd() - .5) * dx, dy * (.6 + rnd() * .8), t0 + rnd() * .6, dl0 + rnd() * .7, 0));

  /* ---- 五組主題: 每組 in / win / lose 回傳 HTML ---- */
  const B = {
    /* 墨韻丹青: 圓相 + 朱印 */
    ink: {
      in: () => dim("rgba(241,232,210,", ".30)") + many(3, i => `<i class="blob" style="${col("#14110f")}--x:50;--y:50;--s:${46 + i * 26};--br:${40 + i * 6}% ${60 - i * 5}% ${55 + i * 3}% ${45 - i * 4}%;--t:${1.1 + i * .25}s;--dl:${i * .12}s"></i>`)
        + sv(enso("#14110f", 7), { sz: 48 }) + `<i class="brush" style="${col("#c8281e")}--y:78;--s:58;--r:-5deg;--t:1.3s;--dl:.35s"></i>`
        + burst(12, "", ["#14110f"], 50, 24, 48, .9, .15, [1.4, 2.6]),
      win: () => dim("rgba(241,232,210,", ".42)") + many(5, i => `<i class="blob" style="${col(i % 2 ? "#14110f" : "#3a1410")}--x:${30 + i * 10};--y:${46 + (i % 2) * 10};--s:${60 + i * 8};--br:${42 + i * 4}% ${58 - i * 3}% 60% 40%;--t:${1.5 + i * .2}s;--dl:${i * .08}s"></i>`)
        + `<div class="shake">${sv(seal(false), { sz: 46, an: "anm-stamp", dl: .25 })}</div>` + ring("#c8281e", 1.4, .75, 6)
        + `<i class="brush" style="${col("#14110f")}--y:80;--s:80;--r:-3deg;--t:1.4s;--dl:.9s"></i>`
        + burst(22, "", ["#14110f", "#c8281e", "#14110f"], 48, 26, 62, 1.1, .75, [1, 3]),
      lose: () => dim("rgba(20,17,15,", ".7)") + sv(seal(true), { sz: 46, an: "anm-stamp", dl: .2, cls: "mono" })
        + many(9, i => `<i class="drip" style="${col("#14110f")}--x:${8 + i * 10.5};--y:${-2 + rnd() * 6};--s:${1.6 + rnd() * 1.8};--h:${34 + rnd() * 36};--t:${1.5 + rnd() * .6}s;--dl:${.5 + rnd() * .7}s"></i>`)
        + many(10, () => pt("", "#14110f", 20 + rnd() * 60, 30 + rnd() * 20, 1.2 + rnd() * 2, (rnd() - .5) * 16, 16 + rnd() * 28, 1.3 + rnd() * .6, .6 + rnd() * .6)),
    },
    /* 落櫻繽紛: 一朵櫻花綻放 */
    sakura: {
      in: () => dim("rgba(255,160,200,", ".22)") + ring("#ff8fc0", 1.5, .2, 4)
        + many(5, k => sv(petal, { sz: 44, a: k * 72, an: "anm-bloom", dl: .08 * k, cls: "glow", gc: "#ff8fc0" })) + sv(stamen(), { sz: 44, dl: .42, an: "anm-pop" })
        + many(22, i => { const a = rnd() * 6.283, x = 50 + Math.cos(a) * 52, y = 50 + Math.sin(a) * 52; return pt("pe", i % 3 ? "#ffb6d5" : "#ffd1e6", x, y, 2.2 + rnd() * 2, 50 - x + (rnd() - .5) * 8, 50 - y - 10 - rnd() * 14, 1.2 + rnd() * .5, rnd() * .45, rnd() * 360); }),
      win: () => dim("rgba(255,140,190,", ".5)") + ray("#ffb6d5", 3.2, 0, 60) + ring("#ff8fc0", 1.6, .1, 6) + ring("#ffd1e6", 1.9, .4, 8)
        + many(5, k => sv(petal, { sz: 58, a: k * 72 + 36, an: "anm-bloom", dl: .05 * k, st: "opacity:.85;filter:brightness(1.12)" }))
        + many(5, k => sv(petal, { sz: 48, a: k * 72, an: "anm-bloom", dl: .12 + .07 * k, cls: "glow", gc: "#ff8fc0" })) + sv(stamen(), { sz: 48, dl: .55 })
        + many(46, i => { const a = rnd() * 6.283, d = 20 + rnd() * 44; return pt("pe", i % 3 ? "#ff9fc9" : "#fff0f6", 50, 50, 2.4 + rnd() * 2.6, Math.cos(a) * d, Math.sin(a) * d + 18 + rnd() * 20, 2 + rnd() * 1.1, .3 + rnd() * .5, rnd() * 540); }),
      lose: () => dim("rgba(60,40,52,", ".6)")
        + many(5, k => sv(petal, { sz: 46, a: k * 72, an: "anm-wilt", dl: .05 * k, dx: (rnd() - .5) * 30, dy: 30 + rnd() * 18, wr: (rnd() - .5) * 120, cls: "mono" })) + sv(stamen(), { sz: 46, dl: .3, cls: "mono" })
        + many(30, i => pt("pe", i % 2 ? "#9a7686" : "#7a5e6c", 6 + rnd() * 88, -6 + rnd() * 30, 2 + rnd() * 2.2, (rnd() - .5) * 18, 48 + rnd() * 38, 1.7 + rnd() * 1.1, rnd() * .9, 200 + rnd() * 340)),
    },
    /* 驚雷破空: 閃電 */
    thunder: {
      in: () => `<i class="fl" style="${col("#dff1ff")}--dl:.05s"></i>` + dim("rgba(14,26,66,", ".7)") + jag(0, 36, .05, "#6aa8ff") + jag(0, 64, .16, "#ffe14d", 1)
        + ring("#6aa8ff", 1.2, .2, 5) + sv(orb(), { sz: 46, an: "anm-zap", dl: .12, cls: "glow", gc: "#6aa8ff" })
        + burst(14, "sq", ["#ffe14d", "#bfe6ff"], 50, 18, 48, .7, .2, [.9, 1.6]),
      win: () => `<i class="fl" style="${col("#ffffff")}--dl:0s"></i>` + dim("rgba(10,20,70,", ".85)") + ray("#6aa8ff", 3.2, .1, 70) + ray("#ffe14d", 3.0, .2, -50)
        + jag(0, 24, .05, "#6aa8ff") + jag(0, 76, .3, "#6aa8ff", 1) + ring("#ffe14d", 1.5, .45, 6) + ring("#6aa8ff", 1.8, .7, 8)
        + sv(arcs(9, "#bfe6ff"), { sz: 78, an: "anm-spin", dl: .2, st: "--rot:200deg", cls: "glow", gc: "#6aa8ff" }) + sv(orb(), { sz: 54, an: "anm-zap", dl: .25, cls: "glow", gc: "#6aa8ff" })
        + burst(36, "sq", ["#ffe14d", "#bfe6ff"], 50, 24, 68, .9, .4, [.9, 1.8]),
      lose: () => dim("rgba(14,18,34,", ".8)") + many(4, i => `<i class="cloud" style="--x:${18 + i * 22};--s:${44 + (i % 2) * 14};--dl:${i * .14}s"></i>`)
        + halves(orb(), { sz: 44, cls: "mono" })
        + many(34, () => pt("ln", "#9fb6d8", 4 + rnd() * 92, -8 + rnd() * 14, 1.4 + rnd() * 1.4, -4 - rnd() * 4, 100 + rnd() * 40, .8 + rnd() * .5, .3 + rnd() * 1.9, 0)),
    },
    /* 赤壁烈焰: 粒子火牆 (canvas) */
    flame: {
      in: () => dim("rgba(60,8,0,", ".6)") + `<i class="heat" style="${col("rgba(255,110,20,.5)")}"></i>` + cv("in") + ring("#ff7a2b", 1.3, .35, 5),
      win: () => dim("rgba(70,10,0,", ".8)") + `<i class="heat" style="${col("rgba(255,120,24,.65)")}"></i>` + cv("win") + ring("#ffd27a", 1.6, .3, 6) + ring("#ff7a2b", 1.9, .6, 8),
      lose: () => dim("rgba(18,10,8,", ".78)") + `<i class="heat" style="${col("rgba(120,40,10,.35)")}"></i>` + cv("lose"),
    },
    /* 像素街機: 8-bit 方塊 + 精靈 (全程階梯式動畫,像舊遊戲機) */
    pixel: {
      in: () => dim("rgba(20,8,50,", ".55)") + pring("#3dffd0", 1.2, .1, 5) + pring("#ff4df0", 1.4, .35, 7)
        + sv(spr(INV, "#3dffd0"), { sz: 34, an: "anm-pxdrop", t: 1.7, cls: "glow stp", gc: "#3dffd0" })
        + bits(26, PXC, 6, 94, 62, 96, 10, -46, 1.1, .2),
      win: () => dim("rgba(24,8,60,", ".8)") + pring("#ffe14d", 1.5, .2, 5) + pring("#3dffd0", 1.8, .5, 7) + pring("#ff4df0", 2.1, .8, 9)
        + sv(spr(TROPHY, "#ffd33d", "#fff6b0"), { sz: 44, an: "anm-pxwin", t: 3.2, dl: .1, cls: "glow stp", gc: "#ffd33d" })
        + bits(54, PXC, 2, 98, -8, 6, 10, 112, 1.8, .4)
        + bits(18, ["#fff6b0", "#ffe14d"], 30, 70, 30, 70, 90, 60, 1.2, .4),
      lose: () => dim("rgba(10,10,18,", ".82)") + sv(spr(INV, "#8f8a80"), { sz: 34, an: "anm-pxfall", t: 2.6, dl: .2, cls: "stp" })
        + gl("#ff4d6d", 5, 1.2, .1) + gl("#3dffd0", 3, 1.2, .2) + bits(24, ["#8f8a80", "#5b5870"], 30, 70, 40, 56, 34, 46, 1.6, .9),
    },
  };

  /* ---- 扣血 / 回血 (短動畫,放在被扣血 / 回血的玩家座位上) ---- */
  Object.assign(B.ink, {
    hurt: () => many(2, i => `<i class="blob" style="${col(i ? "#8a1810" : "#14110f")}--x:50;--y:50;--s:${40 + i * 18};--br:${44 + i * 6}% ${56 - i * 4}% 60% 40%;--t:.8s;--dl:${i * .05}s"></i>`)
      + `<i class="brush" style="${col("#c8281e")}--y:50;--s:72;--r:-26deg;--t:.75s;--dl:0s"></i>` + burst(14, "", ["#14110f", "#c8281e"], 50, 14, 40, .6, 0, [1, 2.4]),
    heal: () => dim("rgba(241,232,210,", ".28)") + ring("#f1e8d2", 1.2, 0, 4) + sv(enso("#f1e8d2", 5), { sz: 38, t: 1.3 })
      + many(12, () => pt("em", "#f1e8d2", 36 + rnd() * 28, 62 + rnd() * 10, .8 + rnd() * 1.4, (rnd() - .5) * 8, -(18 + rnd() * 22), 1 + rnd() * .3, rnd() * .5, 0)),
  });
  Object.assign(B.sakura, {
    hurt: () => dim("rgba(255,80,120,", ".28)") + ring("#ff6f9a", .8, 0, 4) + many(16, () => { const a = rnd() * 6.283, d = 14 + rnd() * 30; return pt("pe", rnd() > .5 ? "#c98aa0" : "#ff9fc9", 50, 50, 1.8 + rnd() * 1.6, Math.cos(a) * d, Math.sin(a) * d + 10, .8 + rnd() * .3, rnd() * .12, rnd() * 400); }),
    heal: () => dim("rgba(255,160,200,", ".22)") + ring("#ff8fc0", 1.3, 0, 4) + many(5, k => sv(petal, { sz: 28, a: k * 72, an: "anm-bloom", dl: .04 * k, t: 1.3, cls: "glow", gc: "#ff8fc0" })) + sv(stamen(), { sz: 28, dl: .25, t: 1.3 })
      + many(10, () => pt("pe", "#ffc2dc", 36 + rnd() * 28, 60 + rnd() * 12, 1.6 + rnd() * 1.4, (rnd() - .5) * 14, -(20 + rnd() * 22), 1.1 + rnd() * .3, rnd() * .5, rnd() * 360)),
  });
  Object.assign(B.thunder, {
    hurt: () => `<i class="fl" style="${col("#dff1ff")}--dl:0s"></i>` + jag(0, 50, 0, "#6aa8ff") + sv(orb(), { sz: 30, an: "anm-zap", t: .9, cls: "glow", gc: "#6aa8ff" }) + burst(10, "sq", ["#ffe14d", "#bfe6ff"], 50, 10, 34, .6, 0, [.8, 1.4]),
    heal: () => dim("rgba(20,40,90,", ".3)") + ring("#9fd0ff", 1.3, 0, 4) + sv(arcs(7, "#bfe6ff"), { sz: 52, an: "anm-spin", t: 1.3, st: "--rot:120deg", cls: "glow", gc: "#6aa8ff" })
      + many(12, () => pt("sq", rnd() > .5 ? "#ffe14d" : "#bfe6ff", 34 + rnd() * 32, 62 + rnd() * 10, .8 + rnd() * 1.2, (rnd() - .5) * 10, -(20 + rnd() * 24), 1 + rnd() * .35, rnd() * .5, rnd() * 360)),
  });
  Object.assign(B.pixel, {
    hurt: () => `<i class="fl" style="${col("#ff4d6d")}--dl:0s"></i>` + gl("#ff4d6d", 3, .8, 0) + halves(spr(HEART, "#ff4d6d"), { sz: 30, dl: .05, t: .95, cls: "stp" })
      + burst(14, "px", ["#ff4d6d", "#ffe14d"], 50, 8, 34, .7, 0, [1.6, 2.4]),
    heal: () => dim("rgba(10,50,30,", ".3)") + pring("#3dffa0", 1.2, 0, 4) + sv(spr(HEART, "#3dffa0", "#d9ffe9"), { sz: 28, s0: 1.5, t: 1.3, cls: "glow stp", gc: "#3dffa0" })
      + bits(14, ["#3dffa0", "#d9ffe9"], 34, 66, 62, 74, 10, -34, 1.1, 0),
    die: () => dim("rgba(10,10,18,", ".62)") + sv(spr(SKULL, "#d8dce6"), { sz: 34, an: "anm-pxfall", t: 1.9, cls: "stp" })
      + gl("#ff4d6d", 4, 1, 0) + pring("#8f8a80", 1.2, .3, 4) + bits(22, ["#8f8a80", "#d8dce6", "#5b5870"], 30, 70, 40, 56, 34, 44, 1.2, .3),
  });
  B.flame.hurt = () => `<i class="fl" style="${col("#ff7a2b")}--dl:0s"></i>` + cv("hurt");
  B.flame.heal = () => dim("rgba(70,30,0,", ".25)") + ring("#ffd27a", 1.3, 0, 4) + cv("heal");

  /* ---- 攻擊特效 (對別人出殺 / 決鬥 / 火攻: 從出手的人飛向目標,各主題不同) ---- */
  const shot = (g, cls, c, w, h, t, dl, o = {}) => `<i class="shot ${cls}" style="${col(c)}left:${f(g.ax + (o.jx || 0))}%;top:${f(g.ay + (o.jy || 0))}%;--mx:${f(g.dx)}px;--my:${f(g.dy)}px;--ang:${f(g.ang)}deg;--w:${w};--h:${h};--t:${t}s;--dl:${dl}s;${o.st || ""}"></i>`;
  const ringAt = (c, x, y, t, dl, sc) => `<i class="rg" style="${col(c)}left:${f(x)}%;top:${f(y)}%;--t:${t}s;--dl:${dl}s;--sc:${sc || 4}"></i>`;
  const burstAt = (g, n, cls, cs, d0, d1, dl0, sz) => many(n, i => { const a = rnd() * 6.283, d = d0 + rnd() * (d1 - d0); return pt(cls, cs[i % cs.length], g.bx, g.by, sz[0] + rnd() * sz[1], Math.cos(a) * d, Math.sin(a) * d, .5 + rnd() * .35, dl0 + rnd() * .1, rnd() * 360); });
  const slash = (g, c, h, dl) => `<i class="slash" style="${col(c)}left:${f(g.ax)}%;top:${f(g.ay)}%;--len:${f(g.len)}px;--ang:${f(g.ang)}deg;--h:${h};--dl:${dl}s"></i>`;
  const arcLine = (g, c, dl, w) => {   // 從出手的人拉到目標的鋸齒電弧
    const n = 10, nx = -g.dy, ny = g.dx, nl = Math.hypot(nx, ny) || 1; let pts = "";
    for (let i = 0; i <= n; i++) {
      const t = i / n, amp = (i === 0 || i === n) ? 0 : (rnd() - .5) * 2 * 3.2;
      pts += `${f(g.ax + (g.bx - g.ax) * t + (nx / nl) * amp)},${f(g.ay + (g.by - g.ay) * t + (ny / nl) * amp)} `;
    }
    return `<svg class="bolt2" viewBox="0 0 100 100" preserveAspectRatio="none" style="--dl:${dl}s"><polyline points="${pts}" fill="none" stroke="${c}" stroke-linejoin="round" opacity=".45" vector-effect="non-scaling-stroke" style="stroke-width:${w * 3}px"/><polyline points="${pts}" fill="none" stroke="#fff" stroke-linejoin="round" vector-effect="non-scaling-stroke" style="stroke-width:${w}px"/></svg>`;
  };
  Object.assign(B.ink, { atk: (T, g) => slash(g, "#14110f", 3.4, 0) + slash(g, "#c8281e", 1.3, .05)
    + `<i class="blob" style="${col("#14110f")}--x:${f(g.bx)};--y:${f(g.by)};--s:20;--br:44% 56% 60% 40%;--t:.6s;--dl:.4s"></i>` + burstAt(g, 14, "", ["#14110f", "#c8281e"], 8, 26, .4, [.8, 2]) + ringAt("#c8281e", g.bx, g.by, .6, .4, 3) });
  Object.assign(B.sakura, { atk: (T, g) => many(14, () => shot(g, "pe", rnd() > .4 ? "#ffb6d5" : "#ff8fc0", 3.2, 2.1, .38 + rnd() * .14, rnd() * .22, { jx: (rnd() - .5) * 5, jy: (rnd() - .5) * 5 }))
    + burstAt(g, 12, "pe", ["#ffd1e6", "#ff9fc9"], 8, 24, .45, [1.6, 1.6]) + ringAt("#ff8fc0", g.bx, g.by, .6, .45, 3) });
  Object.assign(B.thunder, { atk: (T, g) => arcLine(g, "#6aa8ff", 0, 3.4) + arcLine(g, "#ffe14d", .06, 2.2)
    + sv(orb(), { sz: 16, an: "anm-zap", t: .75, dl: .3, st: `left:${f(g.bx)}%;top:${f(g.by)}%;`, cls: "glow", gc: "#6aa8ff" }) + ringAt("#9fd0ff", g.bx, g.by, .6, .35, 3) + burstAt(g, 10, "sq", ["#ffe14d", "#bfe6ff"], 6, 24, .35, [.7, 1.3]) });
  Object.assign(B.flame, { atk: (T, g) => many(7, k => shot(g, "ball", "#ff7a2b", 5.5 - k * .5, 5.5 - k * .5, .42, .035 * k)) + shot(g, "ball", "#ff7a2b", 8, 8, .42, 0)
    + ringAt("#ff7a2b", g.bx, g.by, .65, .4, 3.6) + burstAt(g, 16, "em", ["#ffd27a", "#ff7a2b"], 8, 32, .4, [.9, 1.6]) });
  const pringAt = (c, x, y, t, dl, sc) => `<i class="rg pq" style="${col(c)}left:${f(x)}%;top:${f(y)}%;--t:${t}s;--dl:${dl}s;--sc:${sc || 4}"></i>`;
  Object.assign(B.pixel, { atk: (T, g) => many(6, k => shot(g, "px", PXC[k % 2], 3.4 - k * .3, 3.4 - k * .3, .5, .05 * k + .02)) + shot(g, "px", "#ffe14d", 5.2, 5.2, .5, 0)
    + pringAt("#3dffd0", g.bx, g.by, .65, .45, 3.4) + pringAt("#ff4df0", g.bx, g.by, .8, .55, 4.6) + burstAt(g, 16, "px", PXC, 8, 30, .45, [1.6, 2]) });

  /* ---- 死亡 (被淘汰的玩家座位上播,各主題不同) ---- */
  B.ink.die = () => dim("rgba(20,16,14,", ".55)") + many(3, i => `<i class="blob" style="${col("#14110f")}--x:50;--y:50;--s:${64 + i * 26};--br:${44 + i * 6}% ${56 - i * 4}% 60% 40%;--t:1.5s;--dl:${i * .12}s"></i>`)
    + `<i class="brush" style="${col("#c8281e")}--y:50;--s:84;--r:28deg;--t:1.3s;--dl:.15s"></i>`
    + many(3, i => `<i class="drip" style="${col("#14110f")}--x:${38 + i * 12};--y:34;--s:5;--h:${30 + i * 8};--t:1.5s;--dl:${.3 + i * .1}s"></i>`) + burst(18, "", ["#14110f", "#c8281e"], 50, 12, 44, .9, .1, [1, 2.6]);
  B.sakura.die = () => dim("rgba(80,30,50,", ".4)") + ring("#c98aa0", 1.2, 0, 4)
    + many(28, () => pt("pe", ["#c98aa0", "#8a5a70", "#ffb6d5"][Math.floor(rnd() * 3)], 20 + rnd() * 60, 14 + rnd() * 26, 2 + rnd() * 2, (rnd() - .5) * 30, 40 + rnd() * 50, 1.5 + rnd() * .5, rnd() * .7, rnd() * 500));
  B.thunder.die = () => dim("rgba(10,16,40,", ".5)") + `<i class="fl" style="${col("#dff1ff")}--dl:0s"></i>` + jag(0, 50, 0, "#6aa8ff") + sv(orb(), { sz: 34, an: "anm-zap", t: 1.4, cls: "glow", gc: "#6aa8ff" })
    + ring("#9fd0ff", 1.2, .2, 5) + burst(16, "sq", ["#ffe14d", "#bfe6ff"], 50, 12, 44, .9, .1, [.8, 1.6]);
  B.flame.die = () => dim("rgba(18,10,8,", ".6)") + `<i class="heat" style="${col("rgba(120,40,10,.4)")}"></i>` + cv("lose")
    + many(14, () => pt("sm", "#777", 30 + rnd() * 40, 50 + rnd() * 20, 8 + rnd() * 6, (rnd() - .5) * 10, -(20 + rnd() * 30), 1.6, rnd() * .8, 0));

  /* ---- 驚雷破空 (重畫): 乾淨的電能反應爐 — 六角核心 + 旋轉虛線環 + 白色能量核,霓虹青 / 電藍 / 白三色 ---- */
  const EL = "#38e8ff", EB = "#3d7bff";
  const reactor = (c1, c2) => {
    const pts = r => [0, 1, 2, 3, 4, 5].map(i => { const a = (i * 60 - 90) * Math.PI / 180; return (r * Math.cos(a)).toFixed(1) + "," + (r * Math.sin(a)).toFixed(1); }).join(" ");
    let o = `<defs><radialGradient id="thC" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff"/><stop offset=".35" stop-color="${c1}"/><stop offset="1" stop-color="${c1}" stop-opacity="0"/></radialGradient></defs>`
      + `<circle r="17" fill="url(#thC)"/><polygon points="${pts(25)}" fill="rgba(56,232,255,.1)" stroke="${c1}" stroke-width="1.6" stroke-linejoin="round"/><polygon points="${pts(15)}" fill="none" stroke="#fff" stroke-width="1" stroke-linejoin="round"/>`;
    for (let i = 0; i < 6; i++) { const a = (i * 60 - 90) * Math.PI / 180, c = Math.cos(a), n = Math.sin(a); o += `<line x1="${(15 * c).toFixed(1)}" y1="${(15 * n).toFixed(1)}" x2="${(25 * c).toFixed(1)}" y2="${(25 * n).toFixed(1)}" stroke="${c1}" stroke-width="1"/>`; }
    o += `<g class="rot"><circle r="34" fill="none" stroke="${c1}" stroke-width="1.4" stroke-dasharray="8 5"/></g><circle r="42" fill="none" stroke="${c2}" stroke-width="1.1" stroke-dasharray="2 6"/>`;
    for (let i = 0; i < 4; i++) o += `<line x1="0" y1="-45" x2="0" y2="-49.5" stroke="${c1}" stroke-width="1.6" transform="rotate(${i * 90})"/>`;
    return o;
  };
  const spokes = (n, r0, r1, c) => { let o = ""; for (let i = 0; i < n; i++) { const a = i / n * 6.283 + .3, ca = Math.cos(a), sa = Math.sin(a); o += `<line x1="${(r0 * ca).toFixed(1)}" y1="${(r0 * sa).toFixed(1)}" x2="${(r1 * ca).toFixed(1)}" y2="${(r1 * sa).toFixed(1)}" stroke="${c}" stroke-width="1.4" stroke-linecap="round"/>`; } return o; };
  const RX = reactor(EL, EB), RXM = reactor("#9aa3b2", "#6b7385");
  Object.assign(B.thunder, {
    in: () => dim("rgba(6,18,48,", ".55)") + ring(EL, 1.3, .15, 5) + ring(EB, 1.6, .4, 7) + sv(RX, { sz: 46, s0: 1.8, an: "anm-pop", t: 1.8, cls: "glow", gc: EL })
      + sv(spokes(14, 30, 46, "#fff"), { sz: 80, an: "anm-fade", t: 1.4, dl: .1 }) + bits(20, [EL, EB, "#fff"], 8, 92, 30, 90, 14, -30, 1, .2),
    win: () => dim("rgba(6,18,52,", ".82)") + ray(EL, 3.2, 0, 50) + ring(EL, 1.6, .2, 5) + ring(EB, 1.9, .5, 7) + ring("#fff", 2.2, .8, 9)
      + sv(RX, { sz: 60, s0: 2.2, an: "anm-pop", t: 3.2, dl: .1, cls: "glow", gc: EL }) + sv(spokes(18, 34, 52, "#fff"), { sz: 100, an: "anm-fade", t: 2.4, dl: .3 })
      + bits(40, [EL, EB, "#fff"], 4, 96, 20, 92, 60, -50, 2, .4),
    lose: () => dim("rgba(10,12,20,", ".82)") + sv(RXM, { sz: 46, an: "anm-zap", t: 2.8, dl: .1 }) + gl("#38e8ff", 4, 1.2, .1) + gl("#3d7bff", 3, 1.2, .3)
      + bits(22, ["#6b7385", "#9aa3b2"], 30, 70, 42, 58, 30, 46, 1.6, .9),
    hurt: () => `<i class="fl" style="${col("#bfefff")}--dl:0s"></i>` + ring(EL, .8, 0, 4) + sv(reactor(EL, EB), { sz: 30, an: "anm-zap", t: .9, cls: "glow", gc: EL }) + sv(spokes(12, 16, 40, "#fff"), { sz: 60, an: "anm-fade", t: .7 })
      + burst(10, "sq", [EL, "#fff"], 50, 10, 34, .6, 0, [.8, 1.4]),
    heal: () => dim("rgba(6,30,48,", ".3)") + ring("#7dffd8", 1.3, 0, 4) + sv(reactor("#7dffd8", EL), { sz: 34, s0: 1.5, t: 1.3, cls: "glow", gc: "#7dffd8" })
      + bits(12, ["#7dffd8", "#fff", EL], 34, 66, 62, 74, 10, -34, 1.1, 0),
    atk: (T, g) => slash(g, EL, 3.6, 0) + slash(g, "#fff", 1.3, .02) + ringAt(EL, g.bx, g.by, .6, .3, 3.4) + ringAt("#fff", g.bx, g.by, .45, .32, 2)
      + sv(spokes(10, 6, 22, "#fff"), { sz: 40, an: "anm-fade", t: .6, dl: .3, st: `left:${f(g.bx)}%;top:${f(g.by)}%;` }) + burstAt(g, 12, "sq", [EL, "#fff"], 6, 26, .32, [.8, 1.3]),
    die: () => dim("rgba(6,10,24,", ".62)") + sv(RXM, { sz: 40, an: "anm-pxfall", t: 1.9 }) + gl("#38e8ff", 4, 1, 0) + ring("#6b7385", 1.2, .3, 4)
      + bits(18, ["#6b7385", "#9aa3b2", EL], 30, 70, 42, 58, 30, 42, 1.2, .3),
  });

  /* ---- 武士 (水墨風): 宣紙米白底 + 墨黑 + 一點朱紅,毛筆邊緣 (feTurbulence 位移),極簡高對比、不用漸層和陰影 ---- */
  const INKF = `<filter id="inkr" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".05" numOctaves="2" seed="4" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="2.6"/></filter>`;
  const KAT = (() => {   // 水墨武士刀: 直立 (刀尖朝上),墨黑刀身 + 宣紙色刃紋 + 朱紅柄頭
    let o = `<defs>${INKF}</defs><g filter="url(#inkr)">`
      + `<path d="M-2.8,24 L-2.8,-38 L.6,-48 L3.3,-38 L3.3,24Z" fill="#14110f"/><path d="M1.4,22 C.8,10 1.9,0 1.2,-14 C.9,-24 1.5,-32 1.1,-41" fill="none" stroke="#f4f4f2" stroke-width=".9" opacity=".85"/>`
      + `<rect x="-3.2" y="24" width="7" height="3" fill="#14110f"/><ellipse cx=".3" cy="29" rx="8.2" ry="2.3" fill="#14110f"/><ellipse cx=".3" cy="29" rx="5" ry="1" fill="none" stroke="#f4f4f2" stroke-width=".5" opacity=".7"/>`
      + `<rect x="-2.8" y="31" width="6.2" height="18" fill="#14110f"/>`;
    for (let y = 34; y < 48; y += 4.4) o += `<path d="M-2.8,${y} L.3,${y + 2.3} L3.4,${y} L.3,${y - 2.3}Z" fill="#f4f4f2" opacity=".8"/>`;
    return o + `<circle cx=".3" cy="50" r="2.4" fill="#f4f4f2" stroke="#14110f" stroke-width=".6"/></g>`;
  })();
  const SUN = `<defs>${INKF}</defs><g filter="url(#inkr)"><circle r="30" fill="#8a8a86" opacity=".6"/><circle r="30" fill="none" stroke="#14110f" stroke-width="1.8" opacity=".85" stroke-dasharray="40 6"/></g>`;
  const CROSS = `<g transform="rotate(-36)">${KAT}</g><g transform="rotate(36)">${KAT}</g>`;
  const DAG = `<g stroke="#f4f4f2" stroke-width="5" paint-order="stroke" stroke-linejoin="round"><path d="M50,0 L-14,-8 L-14,8Z" fill="#14110f"/><rect x="-19" y="-11" width="5" height="22" fill="#14110f"/><rect x="-47" y="-4.5" width="28" height="9" fill="#14110f"/><circle cx="-49" cy="0" r="4.6" fill="#f4f4f2"/></g>`;
  const kshot = (g, w, t, dl, jx, jy) => shot(g, "kn", "none", w, w, t, dl, { jx, jy }).replace("</i>", `<svg viewBox="-50 -50 100 100" style="width:100%;height:100%;overflow:visible">${DAG}</svg></i>`);
  const PAPER = a => dim("rgba(240,240,238,", a);
  const ib = (c, x, y, sz, t, dl, k) => `<i class="blob" style="${col(c)}--x:${x};--y:${y};--s:${sz};--br:${44 + k * 6}% ${56 - k * 4}% 60% 40%;--t:${t}s;--dl:${dl}s"></i>`;
  const idots = (n, x0, x1, y0, y1, dx, dy, t0, dl0) => many(n, i => pt("", i % 4 ? "#14110f" : "#8a8a86", x0 + rnd() * (x1 - x0), y0 + rnd() * (y1 - y0), 1.2 + rnd() * 2.4, (rnd() - .5) * dx, dy * (.6 + rnd() * .8), t0 + rnd() * .6, dl0 + rnd() * .7, 0));
  const cut = (x1, y1, x2, y2, c, w, dl) => sv(`<defs>${INKF}</defs><g filter="url(#inkr)"><path d="M${x1 - 50},${y1 - 50} L${x2 - 50},${y2 - 50}" pathLength="100" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" style="stroke-dasharray:100;stroke-dashoffset:100;animation:anm-draw .2s ease-out ${dl}s forwards"/></g>`, { sz: 100, an: "anm-cutv", t: 1.1, dl });
  const snap = (inner, o) => sv(inner, Object.assign({}, o, { an: "anm-hl", st: "clip-path:inset(0 0 50% 0);" })) + sv(inner, Object.assign({}, o, { an: "anm-hr", st: "clip-path:inset(50% 0 0 0);" }));
  B.bushi = {
    in: () => PAPER(".5)") + ring("#14110f", 1.3, .15, 5) + sv(SUN, { sz: 62, s0: .6, an: "anm-pop", t: 1.8 }) + sv(CROSS, { sz: 84, s0: 1.8, an: "anm-pop", t: 1.8, dl: .05 })
      + cut(8, 90, 92, 10, "#14110f", 3.2, .3) + cut(8, 90, 92, 10, "#f4f4f2", 1.2, .34) + idots(18, 20, 80, 40, 80, 40, -30, 1, .3),
    win: () => PAPER(".62)") + ray("#14110f", 3.4, 0, 40) + ring("#14110f", 1.6, .2, 5) + ring("#14110f", 1.9, .5, 7)
      + sv(SUN, { sz: 78, s0: .4, an: "anm-pop", t: 3.2, dl: .05 }) + sv(KAT, { sz: 76, s0: 1.6, an: "anm-pop", t: 3.2, dl: .25 })
      + cut(6, 24, 94, 76, "#14110f", 3.2, .7) + cut(6, 24, 94, 76, "#f4f4f2", 1.2, .74) + cut(94, 24, 6, 76, "#14110f", 3.2, .95) + cut(94, 24, 6, 76, "#f4f4f2", 1.2, .99)
      + idots(34, 4, 96, 70, 96, 40, -60, 1.8, .6),
    lose: () => dim("rgba(70,68,66,", ".72)") + sv(SUN, { sz: 60, an: "anm-fade", t: 2.8, dl: .05, cls: "mono" }) + snap(KAT, { sz: 72, dl: .5, t: 2.4, cls: "mono" }) + idots(22, 30, 70, 40, 56, 30, 46, 1.6, .9),
    hurt: () => PAPER(".3)") + ib("#14110f", 50, 50, 36, .8, .05, 0) + cut(6, 14, 94, 86, "#14110f", 3.6, 0) + cut(6, 14, 94, 86, "#f4f4f2", 1.4, .02) + burst(12, "", ["#14110f", "#8a8a86"], 50, 10, 34, .6, .1, [1, 2.2]),
    heal: () => PAPER(".3)") + ring("#14110f", 1.3, 0, 4) + sv(SUN, { sz: 30, s0: 1.4, t: 1.3 }) + sv(KAT, { sz: 50, s0: 1.4, t: 1.3, dl: .05 }) + idots(14, 34, 66, 62, 74, 10, -34, 1.1, 0),
    atk: (T, g) => many(12, k => kshot(g, 12 + (k % 3) * 1.5, .42, .04 * k, (rnd() - .5) * 7, (rnd() - .5) * 7)) + ib("#14110f", g.bx, g.by, 16, .55, .42, 0)
      + ringAt("#14110f", g.bx, g.by, .6, .42, 3.2) + burstAt(g, 14, "", ["#14110f", "#8a8a86"], 6, 26, .42, [1, 2.2]),
    die: () => dim("rgba(50,48,46,", ".62)") + snap(KAT, { sz: 56, dl: .1, t: 1.8, cls: "mono" }) + ring("#8f8a80", 1.2, .3, 4) + idots(18, 30, 70, 42, 58, 30, 42, 1.2, .3),
  };

  /* ---- 粒子火 (canvas): 一束束火舌 + 火星,疊加混色 ---- */
  const PAL = {
    fire: [[0, [255, 226, 130]], [.2, [255, 170, 48]], [.45, [255, 96, 18]], [.75, [190, 30, 6]], [1, [50, 6, 0]]],
    dead: [[0, [255, 170, 90]], [.3, [190, 60, 20]], [.6, [90, 30, 20]], [1, [40, 30, 30]]],
    heal: [[0, [255, 252, 220]], [.3, [255, 220, 120]], [.7, [255, 160, 60]], [1, [150, 70, 10]]],
  };
  const spCache = {};
  function lerpPal(p, f) { for (let i = 1; i < p.length; i++) if (f <= p[i][0]) { const a = p[i - 1], b = p[i], t = (f - a[0]) / (b[0] - a[0] || 1); return a[1].map((v, k) => Math.round(v + (b[1][k] - v) * t)).join(","); } return p[p.length - 1][1].join(","); }
  function sprites(name) {
    if (spCache[name]) return spCache[name];
    const arr = [];
    for (let i = 0; i < 24; i++) {
      const c = document.createElement("canvas"); c.width = c.height = 64;
      const g = c.getContext("2d"), cl = lerpPal(PAL[name], i / 23), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      gr.addColorStop(0, `rgba(${cl},.95)`); gr.addColorStop(.5, `rgba(${cl},.6)`); gr.addColorStop(1, `rgba(${cl},0)`);
      g.fillStyle = gr; g.fillRect(0, 0, 64, 64); arr.push(c);
    }
    return (spCache[name] = arr);
  }
  const env = (t, up, hold, end) => t < up ? t / up : t < hold ? 1 : Math.max(0, 1 - (t - hold) / (end - hold));
  const FM = {   // x0/x1: 火的橫向範圍; kf/ks: 全螢幕 / 座位版的火束數; sy: 座位版火根的高度比例; h: 火舌高度 (佔畫面比例); rate: 每束每秒噴幾顆; sp: 火星
    in:   { x0: .06, x1: .94, kf: 14, ks: 4, sy: .72, h: .7, rate: 70, pal: "fire", I: t => env(t, .25, 1.1, 1.9), sp: 3 },
    win:  { x0: 0, x1: 1, kf: 18, ks: 5, sy: .78, h: 1.0, rate: 62, pal: "fire", I: t => env(t, .35, 2.5, 3.4), sp: 4 },
    lose: { x0: .08, x1: .92, kf: 10, ks: 4, sy: .72, h: .45, rate: 55, pal: "dead", I: t => Math.max(0, 1 - t / 1.4), sp: 2, smoke: true },
    hurt: { x0: .28, x1: .72, kf: 6, ks: 5, sy: .62, h: .55, rate: 130, pal: "fire", I: t => t < .15 ? 1 : Math.max(0, 1 - (t - .15) / .5), sp: 12 },
    heal: { x0: .34, x1: .66, kf: 5, ks: 3, sy: .66, h: .55, rate: 55, pal: "heal", I: t => env(t, .2, .8, 1.3), sp: 6 },
  };
  function startFire2d(cv, mode, T, el, done) {
    const cfg = FM[mode]; if (!cfg || !cv.getContext) return;
    const w = el.clientWidth, h = el.clientHeight; if (!w || !h) return;
    const u = Math.min(w, h) / 100, dpr = Math.min(window.devicePixelRatio || 1, 1.5), full = el.dataset.full === "1";
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    const g = cv.getContext("2d"); g.scale(dpr, dpr);
    const X0 = full ? cfg.x0 : +el.dataset.bx0, X1 = full ? cfg.x1 : +el.dataset.bx1, K = full ? cfg.kf : cfg.ks, y0 = h * (full ? 1.01 : +el.dataset.by), spr = sprites(cfg.pal), smk = sprites("dead");
    const P = [], SP = [], SM = [], ph = []; for (let i = 0; i < K; i++) ph.push(rnd() * 6.283);
    let last = performance.now(), t0 = last, acc = 0, accS = 0, accM = 0;
    const gauss = () => (rnd() + rnd() + rnd() - 1.5) / 1.5;
    function frame(now) {
      if (!el.isConnected) { done && done(); return; }
      const t = (now - t0) / 1000, dt = Math.min(.05, (now - last) / 1000); last = now;
      if (t > T + .1) { done && done(); return; }
      const I = cfg.I(t), span = (X1 - X0) * w;
      acc += cfg.rate * K * I * dt;
      while (acc >= 1) {
        acc--; const c = Math.floor(rnd() * K), flare = .55 + .45 * Math.sin(t * 3.2 + ph[c] * 2), cx = X0 * w + (c + .5) / K * span + Math.sin(t * .8 + ph[c]) * u * 2.4;
        if (rnd() > flare) continue;
        const life = .7 + rnd() * .9;
        P.push({ x: cx + gauss() * span / K * .55, y: y0, vx: (rnd() - .5) * u * 5, vy: -h * cfg.h * (.85 + rnd() * .6), age: 0, life, sz: u * (4.5 + rnd() * 6.5), ph: rnd() * 6.283, fr: 2.5 + rnd() * 4.5, am: u * (2.2 + rnd() * 4.2) });
      }
      accS += cfg.sp * K * I * dt;
      while (accS >= 1) { accS--; const c = Math.floor(rnd() * K); SP.push({ x: X0 * w + (c + .5) / K * span + gauss() * span / K * .4, y: y0 - rnd() * h * .15, vx: (rnd() - .5) * u * 14, vy: -h * (.35 + rnd() * .75), age: 0, life: 1 + rnd() * 1.1, sz: u * (.3 + rnd() * .45), ph: rnd() * 6.283 }); }
      if (cfg.smoke) { accM += 14 * dt; while (accM >= 1) { accM--; SM.push({ x: X0 * w + rnd() * span, y: y0 - h * (.1 + rnd() * .12), vy: -h * (.12 + rnd() * .1), vx: (rnd() - .5) * u * 3, age: 0, life: 1.8 + rnd() * .9, sz: u * (14 + rnd() * 14) }); } }
      g.clearRect(0, 0, w, h);
      g.globalCompositeOperation = "source-over";
      for (let i = SM.length - 1; i >= 0; i--) {
        const p = SM[i]; p.age += dt; const f = p.age / p.life; if (f >= 1) { SM.splice(i, 1); continue; }
        g.globalAlpha = .26 * (1 - f) * Math.min(1, f * 6); const s = p.sz * (1 + f * 1.6);
        g.drawImage(smk[10], p.x + p.vx * p.age - s / 2, p.y + p.vy * p.age - s / 2, s, s);
      }
      g.globalCompositeOperation = "lighter";
      for (let i = P.length - 1; i >= 0; i--) {
        const p = P[i]; p.age += dt; const f = p.age / p.life; if (f >= 1) { P.splice(i, 1); continue; }
        const px = p.x + p.vx * p.age + Math.sin(p.age * p.fr + p.ph) * p.am * (.3 + f), py = p.y + p.vy * p.age * (1 - .35 * f), s = p.sz * (1 - .55 * f);
        g.globalAlpha = Math.min(1, f * 12) * Math.pow(1 - f, .9) * .3;
        g.drawImage(spr[Math.min(23, Math.floor(f * 23))], px - s * .5, py - s * 1.1, s, s * 2.3);
      }
      for (let i = SP.length - 1; i >= 0; i--) {
        const p = SP[i]; p.age += dt; const f = p.age / p.life; if (f >= 1) { SP.splice(i, 1); continue; }
        const px = p.x + p.vx * p.age + Math.sin(p.age * 6 + p.ph) * u * 1.2, py = p.y + p.vy * p.age + 14 * p.age * p.age * u * .4, s = p.sz * (1 - f * .4) * 2.2;
        g.globalAlpha = (1 - f) * (.65 + .35 * Math.sin(p.age * 30 + p.ph));
        g.drawImage(spr[Math.min(8, Math.floor(f * 12))], px - s / 2, py - s / 2, s, s);
      }
      g.globalAlpha = 1;
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  /* ---- WebGL 火焰: 噪聲往上捲動 + 域扭曲,做出邊緣銳利、一縷一縷扭動的火舌 (沒有 WebGL 時退回粒子火) ---- */
  const VS = "attribute vec2 a;void main(){gl_Position=vec4(a,0.,1.);}";
  const FS = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform vec2 res;uniform vec2 xr;uniform float t,I,hh,yb,aspect,pal,dens;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1.,0.)),f.x),mix(hash(i+vec2(0.,1.)),hash(i+vec2(1.,1.)),f.x),f.y);}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<5;i++){v+=a*noise(p);p=p*2.02+vec2(3.1,1.7);a*=.5;}return v;}
void main(){
  vec2 uv=gl_FragCoord.xy/res;
  float y=(uv.y-yb)/max(hh,.001);
  float x=(uv.x-xr.x)/(xr.y-xr.x);
  if(y<0.||x<-.15||x>1.15){gl_FragColor=vec4(0.);return;}
  float yn=clamp(y,0.,1.5);
  float wob=fbm(vec2(x*2.5,y*1.4-t*.9));
  float xx=x*(xr.y-xr.x)*aspect*8.5*dens+(wob-.5)*3.4*yn;
  float n=fbm(vec2(xx,y*1.5-t*2.2));
  float n2=fbm(vec2(xx*1.9+4.,y*2.6-t*3.4));
  float env=smoothstep(-.05,.12,x)*smoothstep(1.05,.88,x);
  float body=pow(max(0.,1.-yn),.85);
  float v=((n*.75+n2*.5)*1.7+.1)*body*env-.04;
  float a=smoothstep(.3,.42,v)*smoothstep(0.,.12,I)*smoothstep(0.,.07,y);
  vec3 c;
  if(pal<.5){c=mix(vec3(.55,.04,.0),vec3(1.,.26,.02),smoothstep(.3,.55,v));c=mix(c,vec3(1.,.7,.1),smoothstep(.55,.82,v));c=mix(c,vec3(1.,.95,.65),smoothstep(.9,1.15,v));}
  else if(pal<1.5){c=mix(vec3(.18,.05,.03),vec3(.7,.2,.05),smoothstep(.22,.55,v));c=mix(c,vec3(.9,.55,.25),smoothstep(.6,.95,v));}
  else{c=mix(vec3(.9,.45,.05),vec3(1.,.8,.25),smoothstep(.25,.6,v));c=mix(c,vec3(1.,.98,.8),smoothstep(.7,1.,v));}
  vec2 sp=vec2(uv.x*aspect*38.,(uv.y-yb)*22.-t*5.);
  vec2 id=floor(sp);vec2 f=fract(sp)-.5;float r=hash(id);
  vec2 off=(vec2(hash(id+7.),hash(id+13.))-.5)*.5;
  float spark=smoothstep(.1,.0,length(f-off))*step(.94,r)*step(y,1.15)*env*smoothstep(0.,.1,I);
  gl_FragColor=vec4(c*a+vec3(1.,.8,.3)*spark,max(a,spark));
}`;
  const PALN = { fire: 0, dead: 1, heal: 2 };
  function startFireGL(cv, mode, T, el, done) {
    const cfg = FM[mode]; if (!cfg) return true;
    const w = el.clientWidth, h = el.clientHeight; if (!w || !h) return true;
    const full = el.dataset.full === "1", sc = full ? .6 : 1;
    cv.width = Math.max(2, Math.round(w * sc)); cv.height = Math.max(2, Math.round(h * sc));
    const gl = cv.getContext("webgl", { premultipliedAlpha: true, alpha: true, antialias: false });
    if (!gl) return false;
    cv._gl = gl;
    cv.addEventListener("webglcontextlost", e => { e.preventDefault(); done && done(); });   // 顯示卡 / 記憶體吃緊被系統收回 context: 立刻藏掉,不要留一塊空白 (白底) 畫布
    const mk =(type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null; };
    const vs = mk(gl.VERTEX_SHADER, VS), fs = mk(gl.FRAGMENT_SHADER, FS); if (!vs || !fs) return false;
    const pg = gl.createProgram(); gl.attachShader(pg, vs); gl.attachShader(pg, fs); gl.linkProgram(pg);
    if (!gl.getProgramParameter(pg, gl.LINK_STATUS)) return false;
    gl.useProgram(pg);
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(pg, "a"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const U = n => gl.getUniformLocation(pg, n);
    gl.viewport(0, 0, cv.width, cv.height);
    const sx0 = full ? cfg.x0 : Math.max(0, +el.dataset.bx0 - .03), sx1 = full ? cfg.x1 : Math.min(1, +el.dataset.bx1 + .03);
    gl.uniform2f(U("res"), cv.width, cv.height); gl.uniform2f(U("xr"), sx0, sx1); gl.uniform1f(U("dens"), full ? 1 : 1.8);
    gl.uniform1f(U("aspect"), w / h); gl.uniform1f(U("pal"), PALN[cfg.pal] || 0);
    gl.uniform1f(U("yb"), full ? -.02 : 1 - (+el.dataset.by));
    const uT = U("t"), uI = U("I"), uH = U("hh"), seed = rnd() * 50;
    const t0 = performance.now();
    function frame(now) {
      if (!el.isConnected || gl.isContextLost()) { done && done(); return; }
      const t = (now - t0) / 1000; if (t > T + .1) { done && done(); return; }
      const I = cfg.I(t);
      gl.uniform1f(uT, t + seed); gl.uniform1f(uI, I);
      gl.uniform1f(uH, cfg.h * (full ? 1 : .6) * (.28 + .72 * Math.pow(Math.max(0, I), .7)));
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      requestAnimationFrame(frame);
    }
    cv._loop = true; requestAnimationFrame(frame);
    return true;
  }

  /* 火焰畫布: 同時最多 3 個,播完立刻釋放 WebGL context (不然每播一次就多留一個,越積越多、吃掉一堆記憶體) */
  let fireLive = 0;
  function startFire(cv, mode, T, el) {   // cv 可能被換成新畫布 (WebGL 失敗改用 2d)
    if (fireLive >= 3) { cv.remove(); return; }
    fireLive++;
    let freed = false;
    const done = () => {
      if (freed) return; freed = true; fireLive--;
      cv.style.display = "none";   // 先藏起來: 畫布 CSS 是撐滿整個特效框,縮成 1x1 / 釋放 context 的那一瞬間會被拉成一整塊白底
      try { const gl = cv._gl; if (gl) { const x = gl.getExtension("WEBGL_lose_context"); if (x) x.loseContext(); } } catch (e) {}
      cv._gl = null; cv.width = cv.height = 1; cv.remove();
    };
    let ok = false;
    try { ok = startFireGL(cv, mode, T, el, done); } catch (e) { ok = false; }
    if (!ok) {
      try {
        if (cv._gl) { const n = cv.cloneNode(false); cv.replaceWith(n); cv = n; }   // 已經拿過 WebGL context 的畫布不能再開 2d: 換一張新的
        cv._gl = null; startFire2d(cv, mode, T, el, done);
      } catch (e) { cv.style.display = "none"; }
    }
    setTimeout(done, T * 1000 + 600);   // 保險: 不管迴圈有沒有正常結束都會釋放
  }

  /* ---- 專屬音效 (WebAudio 即時合成): 取代原本預設的扣血 / 回血 / 勝利音效 ---- */
  const T_ = (...a) => { const F = window.SGS_FX; if (F && F.tone) F.tone(...a); };
  const N_ = (...a) => { const F = window.SGS_FX; if (F && F.noise) F.noise(...a); };
  const crackle = (n, t0, span, v) => { for (let i = 0; i < n; i++) N_(.03 + Math.random() * .04, v * (.5 + Math.random() * .5), 2500 + Math.random() * 3500, 800, t0 + Math.random() * span, 1.5); };
  const arp = (fs, type, dur, v, gap, t0) => fs.forEach((fr, i) => T_(fr, dur, type, v, fr, (t0 || 0) + i * gap));
  const SND = {
    ink: {   // 太鼓 + 筆鋒 + 古箏
      in() { N_(.5, .4, 400, 3500, 0, .7); T_(92, .55, "sine", .5, 55, .1); },
      win() { T_(82, .7, "sine", .6, 50); N_(.3, .45, 300, 120); arp([523, 587, 659, 784, 880], "triangle", .5, .24, .11, .35); },
      lose() { T_(98, .9, "sine", .5, 48); arp([392, 349, 294, 262], "triangle", .5, .18, .2, .2); },
      hurt() { N_(.22, .6, 3200, 500, 0, .8); T_(150, .22, "sine", .5, 60); },
      heal() { arp([659, 784, 988], "triangle", .45, .2, .1); },
      atk() { N_(.28, .6, 600, 4200, 0, .7); T_(110, .2, "sine", .4, 60, .22); },
      die() { T_(70, 1.1, "sine", .6, 40); N_(.5, .5, 1200, 150, .05, .7); arp([294, 262, 220, 196], "triangle", .6, .16, .22, .3); },
    },
    sakura: {   // 風鈴 + 玻璃音
      in() { arp([1319, 1568, 1976, 2349], "sine", .5, .12, .09); N_(.5, .15, 3000, 7000, 0, 2); },
      win() { arp([523, 659, 784, 988, 1175, 1568], "triangle", .6, .2, .1); N_(.6, .12, 5000, 9000, .4, 2); },
      lose() { arp([784, 659, 523, 392], "sine", .7, .16, .24); N_(.6, .1, 1500, 400, .2, .8); },
      hurt() { N_(.25, .35, 2500, 600, 0, .8); T_(260, .22, "sine", .35, 150); },
      heal() { arp([784, 988, 1175], "sine", .5, .18, .09); },
      atk() { N_(.3, .4, 1500, 5000, 0, .8); arp([1319, 1760, 2349], "sine", .25, .1, .06, .22); },
      die() { arp([988, 784, 659, 523, 392], "sine", .7, .15, .2); N_(.8, .08, 2000, 400, .1, .8); },
    },
    thunder: {   // 雷鳴 + 電弧
      in() { N_(.4, .85, 5000, 300, 0, .5); T_(70, .6, "square", .22, 38, .03); },
      win() { N_(.5, .9, 5000, 300, 0, .5); T_(65, .9, "sawtooth", .28, 40); arp([196, 247, 294, 392], "sawtooth", .5, .12, .12, .3); T_(1568, .6, "sine", .1, 0, .75); },
      lose() { N_(1.2, .5, 600, 120, 0, .5); T_(60, 1.1, "sine", .4, 35, .1); N_(1.4, .22, 3500, 5200, .1, 1.5); },
      hurt() { T_(900, .18, "square", .22, 90); N_(.18, .75, 5000, 400, 0, .6); },
      heal() { arp([784, 988, 1319, 1568], "square", .16, .09, .06); N_(.3, .15, 4000, 7000, .1, 1.5); },
      atk() { T_(1100, .16, "square", .2, 100); N_(.2, .8, 5500, 500, .02, .6); T_(90, .25, "sine", .35, 45, .25); },
      die() { N_(1.1, .9, 5000, 200, 0, .5); T_(55, 1.2, "sine", .5, 30, .05); T_(1200, .3, "square", .15, 80); },
    },
    flame: {   // 火焰呼嘯 + 劈啪
      in() { N_(.6, .6, 500, 3200, 0, .5); crackle(8, .15, .9, .45); },
      win() { N_(1.3, .5, 300, 2600, 0, .5); crackle(16, .1, 1.8, .5); arp([130, 196, 262], "sawtooth", .8, .1, .08, .3); },
      lose() { N_(.9, .5, 3000, 300, 0, .6); crackle(5, 0, .8, .35); T_(110, .9, "sawtooth", .15, 45); },
      hurt() { N_(.3, .75, 2800, 500, 0, .6); crackle(5, 0, .3, .6); T_(120, .22, "sawtooth", .2, 60); },
      heal() { crackle(7, 0, .7, .3); arp([523, 659, 784], "sine", .5, .14, .12, .1); },
      atk() { N_(.4, .65, 500, 3000, 0, .6); crackle(4, .2, .3, .5); T_(100, .25, "sawtooth", .15, 50, .3); },
      die() { N_(1, .6, 2600, 200, 0, .6); crackle(6, 0, .9, .4); T_(90, 1, "sawtooth", .18, 40); },
    },
    pixel: {   // 8-bit 方波電子音
      in() { arp([523, 659, 784, 1047], "square", .12, .16, .07); },
      win() { arp([523, 659, 784, 1047, 784, 1047, 1319], "square", .14, .18, .09); T_(262, .6, "triangle", .2, 262, .1); },
      lose() { arp([392, 370, 349, 330, 262], "square", .2, .16, .14); N_(.4, .12, 2000, 300, .5, .8); },
      hurt() { T_(440, .18, "square", .22, 110); N_(.1, .3, 3000, 800); },
      heal() { arp([659, 784, 988, 1319], "square", .1, .14, .06); },
      atk() { T_(1500, .14, "square", .18, 200); N_(.05, .2, 4000, 1000, 0, 1); },
      die() { arp([523, 415, 330, 262, 196, 131], "square", .2, .16, .12); N_(.6, .2, 2500, 200, .6, .6); },
    },
  };
  SND.bushi = {   // 刀鳴 + 太鼓 + 五聲音階
    in() { N_(.2, .5, 700, 6500, 0, .7); T_(2400, .6, "sine", .15, 2400, .12); T_(90, .4, "sine", .5, 50, .05); },
    win() { T_(70, .5, "sine", .65, 45); T_(70, .5, "sine", .55, 45, .28); T_(90, .7, "sine", .7, 50, .56); arp([523, 587, 784, 880, 1047], "triangle", .5, .2, .12, .7); T_(2600, .6, "sine", .1, 2600, .8); },
    lose() { T_(70, .9, "sine", .6, 40); N_(.3, .3, 3000, 400, .1, .8); arp([392, 330, 262], "triangle", .6, .16, .22, .3); },
    hurt() { N_(.14, .6, 1000, 7000, 0, .7); T_(110, .2, "sine", .5, 60, .08); },
    heal() { arp([784, 880, 1175, 1319], "sine", .6, .14, .12); },
    atk() { N_(.16, .55, 900, 7000, 0, .7); T_(3000, .25, "sine", .12, 3000, .14); },
    die() { T_(65, 1.2, "sine", .6, 38); N_(.3, .4, 3500, 300, .05, .8); arp([330, 294, 247, 196], "triangle", .6, .16, .2, .25); },
  };
  function sound(id, kind) { const sn = SND[id] && SND[id][kind]; if (sn) try { sn(); } catch (e) {} }

  /* ---- 播放 ---- */
  const live = new Set();
  function play(id, kind, rect, o) {
    css();
    const th = THEMES[id], b = B[id];
    if (!th || !b || !rect) return null;
    if (document.hidden) return null;   // 分頁在背景: 不要播 (切回來才不會一次全部播出來)
    if (!(o && o.full) && live.size >= 12) return null;   // 座位動畫同時最多 12 個,避免瞬間疊太多
    o = o || {};
    const T = DUR[kind] || 2, el = document.createElement("div");
    const capPx = Math.max(200, Math.min(300, window.innerWidth * .72));   // 手機的座位框很寬: 座位版動畫最大 300px、不超過螢幕寬的 72%,才不會蓋到隔壁好幾個座位
    const side = o.full ? Math.min(rect.w, rect.h) : Math.min(Math.max(rect.w, rect.h) * (o.k || (kind === "in" ? 2.4 : 3.3)), capPx);
    const w = o.full ? rect.w : side, h = o.full ? rect.h : side, cx = rect.l + rect.w / 2, cy = rect.t + rect.h / 2;
    el.className = "anm";
    el.style.cssText = `left:${o.full ? rect.l : cx - w / 2}px;top:${o.full ? rect.t : cy - h / 2}px;width:${w}px;height:${h}px;--u:${Math.min(w, h) / 100}px;--T:${T}s;--c1:${th.c1};--c2:${th.c2};--c3:${th.c3}`;
    if (o.z) el.style.zIndex = o.z;
    el.dataset.full = o.full ? "1" : "";
    if (!o.full) {   // 座位版: 火從玩家框的底邊、沿著框的寬度燒起來
      const L0 = cx - w / 2, T0 = cy - h / 2, by = (rect.t + rect.h - T0) / h, bx0 = (rect.l - L0) / w, bx1 = (rect.l + rect.w - L0) / w;
      el.dataset.by = by; el.dataset.bx0 = bx0; el.dataset.bx1 = bx1;
      el.style.setProperty("--by", by); el.style.setProperty("--bx0", bx0); el.style.setProperty("--bx1", bx1);
    }
    if (reduce()) {   // 減少動態: 只淡入淡出一個光點
      el.innerHTML = `<i class="dot" style="--c:${th.c2};--T:${Math.min(T, 1.6)}s"></i>`;
    } else {
      sd = (o.seed || (id.charCodeAt(0) * 131 + kind.length * 31)) >>> 0;
      el.innerHTML = b[kind](T, o.g);
    }
    document.body.append(el); live.add(el);
    el.querySelectorAll("canvas[data-fire]").forEach(c => startFire(c, c.dataset.fire, T, el));
    setTimeout(() => { el.querySelectorAll("canvas").forEach(c => { c.style.display = "none"; c.width = c.height = 1; }); el.remove(); live.delete(el); }, T * 1000 + 300);
    return el;
  }
  function clearAll() { live.forEach(e => e.remove()); live.clear(); }
  const rectOf = e => { const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, w: r.width, h: r.height }; };
  const seatEl = i => document.querySelector(`.pl[data-idx="${i}"]`);
  const vw = () => ({ l: 0, t: 0, w: window.innerWidth, h: window.innerHeight });

  /* ---- 對局事件: 進場 / 勝負 (每個人都看得到) ---- */
  const st = { started: false, over: false, last: 0 };
  function anOf(snap, i) { const s = (snap.avstyles || {})[i]; return s && s.an && THEMES[s.an] ? s.an : ""; }
  function onSnap(snap) {
    if (!snap || !snap.players || snap.lesson) return;
    const now = Date.now();
    if (now - st.last > 5000) { st.started = false; st.over = false; }   // 中間沒有牌桌畫面 (回過大廳): 當作新的一局
    st.last = now;
    if (!snap.over) {
      st.over = false;
      if (!st.started) {
        st.started = true;
        if ((snap.round || 1) <= 1) setTimeout(() => entrance(snap), 650);
      }
      return;
    }
    st.started = false;
    if (st.over) return;
    st.over = true;
    setTimeout(() => finale(snap), 500);
  }
  function entrance(snap) {
    if (document.hidden) return;
    let n = 0;
    snap.players.forEach(p => {
      const id = anOf(snap, p.idx);
      if (id && seatEl(p.idx)) setTimeout(() => { const el = seatEl(p.idx); if (el) play(id, "in", rectOf(el)); }, 120 * n++);
    });
    const mine = snap.players.find(p => p.is_viewer && anOf(snap, p.idx)), first = snap.players.find(p => anOf(snap, p.idx)), sp = mine || first;
    if (sp) setTimeout(() => sound(anOf(snap, sp.idx), "in"), 700);   // 專屬進場音效只播一個: 自己的,沒有就第一個
  }
  let pendingFinale = null;
  function finale(snap) {
    if (document.hidden) { pendingFinale = { snap, t: Date.now() }; return; }   // 在背景結束: 切回來時再播一次
    const W = typeof winnerSet === "function" ? winnerSet(snap) : new Set();
    if (!W.size) return;   // 平手 / 沒有結果: 不播
    let me = null;
    snap.players.forEach(p => {
      const id = anOf(snap, p.idx), e = id && seatEl(p.idx);
      if (!e) return;
      const kind = W.has(p.idx) ? "win" : "lose";
      if (p.is_viewer) { me = [id, kind]; return; }   // 自己看全螢幕版 (不再疊座位版)
      play(id, kind, rectOf(e), { k: 3.6 });   // 其他人的座位版: 所有人都看得到
    });
    if (me) play(me[0], me[1], vw(), { full: true });   // 自己的全螢幕版 (別人看到的是你座位上的版本)
    const first = snap.players.find(p => anOf(snap, p.idx) && W.has(p.idx)) || snap.players.find(p => anOf(snap, p.idx));
    if (me) sound(me[0], me[1]); else if (first) sound(anOf(snap, first.idx), W.has(first.idx) ? "win" : "lose");   // 勝負音效只播一個: 自己的,沒有就第一位有動畫的
  }

  function num(rect, kind, n, z) {   // 扣 / 回多少體力: 寫在動畫前面 (動畫特效本身不放字,數字另外疊一層)
    n = Math.abs(+n || 0); if (!n || (kind !== "hurt" && kind !== "heal") || !rect) return;
    css();
    const e = document.createElement("div"), sz = Math.max(30, Math.min(72, rect.h * .62));
    e.className = "anmn"; e.textContent = (kind === "hurt" ? "-" : "+") + n;
    e.style.cssText = `left:${rect.l + rect.w / 2}px;top:${rect.t + rect.h * .45}px;font-size:${sz}px;--nc:${kind === "hurt" ? "#ff5d73" : "#46e0a0"};` + (z ? `z-index:${z + 1};` : "");
    document.body.append(e); setTimeout(() => e.remove(), 1700);
  }
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) return;
    clearAll(); document.querySelectorAll(".anmn").forEach(e => e.remove());   // 切回來: 清掉殘留的動畫,不重播錯過的
    for (const k in lastEv) delete lastEv[k];
    if (pendingFinale && Date.now() - pendingFinale.t < 30000) { const p = pendingFinale; pendingFinale = null; setTimeout(() => finale(p.snap), 400); } else pendingFinale = null;
  });
  const curSnap = () => (typeof S !== "undefined" && S) ? S.snap : null;   // S 是 index.html 的頂層 const,不在 window 上
  const lastEv = {};
  function event(seat, kind, n) {   // 扣血 / 回血: 這個座位有動畫特效就播動畫 + 專屬音效 (回傳 true = 已處理,原本的預設特效 / 音效不要播)
    const snap = curSnap(), id = snap && snap.players ? anOf(snap, seat) : "";
    if (!id) return false;
    if (document.hidden) return true;   // 背景分頁: 動畫、音效都略過 (也不要播原本的預設特效)
    const k = seat + kind, now = Date.now();
    if (lastEv[k] && now - lastEv[k] < 350) return true;
    lastEv[k] = now;
    const e = seatEl(seat);
    if (e) { const r = rectOf(e); play(id, kind, r, { k: 2.4 }); sound(id, kind); num(r, kind, n); }
    return true;
  }
  const geom = (ax, ay, bx, by) => { const W = window.innerWidth, H = window.innerHeight, dx = bx - ax, dy = by - ay; return { ax: ax / W * 100, ay: ay / H * 100, bx: bx / W * 100, by: by / H * 100, dx, dy, ang: Math.atan2(dy, dx) * 180 / Math.PI, len: Math.hypot(dx, dy) }; };
  const lastAtk = {};
  function attack(from, to) {   // 出手的人有動畫特效: 從他的座位飛向目標 (回傳 true = 已處理,原本的出牌音效不要播)
    const snap = curSnap(), id = snap && snap.players ? anOf(snap, from) : "";
    if (!id || from === to) return false;
    if (document.hidden) return true;
    const k = from + ">" + to, now = Date.now();
    if (lastAtk[k] && now - lastAtk[k] < 600) return true;
    lastAtk[k] = now;
    const a = seatEl(from), b = seatEl(to);
    if (a && b) { const ra = rectOf(a), rb = rectOf(b); play(id, "atk", vw(), { full: true, g: geom(ra.l + ra.w / 2, ra.t + ra.h / 2, rb.l + rb.w / 2, rb.t + rb.h / 2) }); }
    sound(id, "atk");
    return true;
  }
  const anyIn = () => { const snap = curSnap(); return !!(snap && snap.players && snap.players.some(p => anOf(snap, p.idx))); };
  function pvZ(rect) {   // 預覽的圖層: 剛好蓋在預覽框所在的彈窗上,仍在其他彈窗 / 提示之下
    try { const e = document.elementFromPoint(rect.l + rect.w / 2, rect.t + rect.h / 2), m = e && e.closest(".modal,#rooms,#auth"); const z = m ? parseInt(getComputedStyle(m).zIndex, 10) : NaN; if (z) return z + 1; } catch (e) {}
    return 19;
  }
  function preview(id, kind, rect) {
    clearAll();
    const PZ = pvZ(rect);
    if (kind === "hurt" || kind === "heal") num(rect, kind, 1, PZ);
    const el = kind === "atk" ? play(id, "atk", vw(), { full: true, z: PZ, g: geom(rect.l - rect.w * .35, rect.t + rect.h / 2, rect.l + rect.w * 1.35, rect.t + rect.h / 2) }) : play(id, kind, rect, { k: kind === "hurt" || kind === "heal" ? 2 : 1.25, z: PZ }); sound(id, kind); return el; }
  window.SGS_ANIM = { THEMES, DUR, play, preview, sound, event, attack, anyIn, clearAll, onSnap, rectOf, vw };
})();
