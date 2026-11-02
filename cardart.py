# -*- coding: utf-8 -*-
"""卡面 / 卡背 (SVG) 產生器: 依牌名畫圖 (成語、典故),可換底色風格 (商店賣的「卡面」) 和卡背。統一風格: 深色底 + 雙線框 + 粗線條向量圖示。"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))

GOLD = "#e8c872"
PAR = "#f6ecd0"     # 米白 (描邊 / 亮部)
INK = "#10141c"
CATS = {   # 分類: (背景亮, 背景暗, 主色)
    "basic": ("#7a1f1f", "#2a0a0e", "#ff6b5a"),
    "trick": ("#1d3f7a", "#0a1530", "#5aa8ff"),
    "delay": ("#4a2478", "#170a2e", "#b98cff"),
    "weapon": ("#3a4a5f", "#10161f", "#9fc3e8"),
    "armor": ("#1f5a46", "#08201a", "#5be0a8"),
    "horse": ("#6a4420", "#241508", "#e0a15a"),
}


def st(c=PAR, w=5, fill="none", extra=""):
    return f'fill="{fill}" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" {extra}'


def sword(rot=-45, blade="#e8eef5", edge="#8aa0b8", cx=100, cy=125, s=1.0, guard=GOLD):
    return (f'<g transform="translate({cx} {cy}) rotate({rot}) scale({s}) translate(-100 -125)">'
            f'<polygon points="92,28 108,28 108,168 100,184 92,168" fill="{blade}" stroke="{edge}" stroke-width="3" stroke-linejoin="round"/>'
            f'<line x1="100" y1="34" x2="100" y2="170" stroke="{edge}" stroke-width="2"/>'
            f'<rect x="68" y="168" width="64" height="11" rx="5" fill="{guard}" stroke="#7a5a10" stroke-width="2"/>'
            f'<rect x="94" y="179" width="12" height="36" rx="4" fill="#6a3a1a" stroke="#2a1408" stroke-width="2"/>'
            f'<circle cx="100" cy="220" r="8" fill="{guard}" stroke="#7a5a10" stroke-width="2"/></g>')


def flame(cx=100, cy=118, s=1.0, c1="#ff8a1a", c2="#ffe27a"):
    return (f'<g transform="translate({cx} {cy}) scale({s}) translate(-100 -118)">'
            f'<path d="M100 30 C124 72 158 84 148 128 C142 162 60 162 54 128 C48 96 82 80 100 30Z" fill="{c1}" stroke="#7a2a00" stroke-width="3"/>'
            f'<path d="M100 78 C114 100 132 108 126 132 C122 152 78 152 74 132 C70 112 90 104 100 78Z" fill="{c2}"/></g>')


def snow(cx=100, cy=118, r=62, c="#bfe9ff", w=6):
    out = ""
    for a in (0, 60, 120):
        dx, dy = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
        out += f'<line x1="{cx-dx:.1f}" y1="{cy-dy:.1f}" x2="{cx+dx:.1f}" y2="{cy+dy:.1f}" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>'
        for sgn in (1, -1):
            ex, ey = cx + sgn * dx * .72, cy + sgn * dy * .72
            for da in (-35, 35):
                bx, by = ex + sgn * r * .28 * math.cos(math.radians(a + da)), ey + sgn * r * .28 * math.sin(math.radians(a + da))
                out += f'<line x1="{ex:.1f}" y1="{ey:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{c}" stroke-width="{w-2}" stroke-linecap="round"/>'
    return out


def bolt(cx=100, cy=120, s=1.0, c="#ffe45a"):
    return (f'<g transform="translate({cx} {cy}) scale({s}) translate(-100 -120)"><polygon points="118,34 66,128 98,128 84,206 138,104 106,104" fill="{c}" stroke="#8a6a00" stroke-width="3" stroke-linejoin="round"/></g>')


def peach(cx=100, cy=125, s=1.0, c1="#ffc2c9", c2="#ff6f86"):
    return (f'<g transform="translate({cx} {cy}) scale({s}) translate(-100 -125)">'
            f'<defs><radialGradient id="pg{int(cx)}{int(cy)}{int(s*10)}" cx="35%" cy="30%"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></radialGradient></defs>'
            f'<path d="M100 70 C150 56 178 112 150 156 C136 180 108 182 100 172 C92 182 64 180 50 156 C22 112 50 56 100 70Z" fill="url(#pg{int(cx)}{int(cy)}{int(s*10)})" stroke="#8a2a3a" stroke-width="3"/>'
            f'<path d="M100 72 C92 100 94 140 100 172" fill="none" stroke="#c4475f" stroke-width="3"/>'
            f'<path d="M104 70 C116 44 142 38 156 46 C148 66 126 76 104 70Z" fill="#59b24a" stroke="#1f5a24" stroke-width="3"/></g>')


def arrow(x1, y1, x2, y2, c=PAR, w=5, head=14):
    a = math.atan2(y2 - y1, x2 - x1)
    p1 = (x2 - head * math.cos(a - .45), y2 - head * math.sin(a - .45)); p2 = (x2 - head * math.cos(a + .45), y2 - head * math.sin(a + .45))
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2-6*math.cos(a):.1f}" y2="{y2-6*math.sin(a):.1f}" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>'
            f'<polygon points="{x2},{y2} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}" fill="{c}"/>')


def shield(cx=100, cy=122, s=1.0, fill="#3a4a66", edge=GOLD, inner=None):
    return (f'<g transform="translate({cx} {cy}) scale({s}) translate(-100 -122)">'
            f'<path d="M100 40 L158 58 C158 120 140 168 100 204 C60 168 42 120 42 58Z" fill="{fill}" stroke="{edge}" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M100 54 L146 68 C146 118 130 158 100 188 C70 158 54 118 54 68Z" fill="none" stroke="{edge}" stroke-width="2" opacity=".7"/>'
            + (inner or "") + '</g>')


def bagua(cx=100, cy=122, r=62):
    out = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#1a2430" stroke="{GOLD}" stroke-width="5"/>'
    for i in range(8):
        a = i * 45
        out += f'<g transform="rotate({a} {cx} {cy})">' + ''.join(
            f'<rect x="{cx-9}" y="{cy-r+10+j*7}" width="{18 if (i+j)%2==0 else 7}" height="4" fill="{GOLD}"/>' + ('' if (i + j) % 2 == 0 else f'<rect x="{cx+2}" y="{cy-r+10+j*7}" width="7" height="4" fill="{GOLD}"/>') for j in range(3)) + '</g>'
    out += (f'<circle cx="{cx}" cy="{cy}" r="26" fill="#f6ecd0"/><path d="M{cx} {cy-26} A13 13 0 0 1 {cx} {cy} A13 13 0 0 0 {cx} {cy+26} A26 26 0 0 1 {cx} {cy-26}Z" fill="#10141c"/>'
            f'<circle cx="{cx}" cy="{cy-13}" r="4" fill="#f6ecd0"/><circle cx="{cx}" cy="{cy+13}" r="4" fill="#10141c"/>')
    return out


def card(cx, cy, rot=0, w=54, h=76, fill="#f6ecd0", edge="#8a6a2a", extra=""):
    return f'<g transform="translate({cx} {cy}) rotate({rot})"><rect x="{-w/2}" y="{-h/2}" width="{w}" height="{h}" rx="7" fill="{fill}" stroke="{edge}" stroke-width="3"/>{extra}</g>'


def star4(cx, cy, r, c="#fff6c4"):
    return f'<path d="M{cx} {cy-r} Q{cx+r*.18} {cy-r*.18} {cx+r} {cy} Q{cx+r*.18} {cy+r*.18} {cx} {cy+r} Q{cx-r*.18} {cy+r*.18} {cx-r} {cy} Q{cx-r*.18} {cy-r*.18} {cx} {cy-r}Z" fill="{c}"/>'


def chevrons(cx, cy, n=2, up=True, c="#7dffa0", w=9):
    out = ""
    for i in range(n):
        y = cy + (i * 24 if up else -i * 24)
        d = -1 if up else 1
        out += f'<polyline points="{cx-34},{y} {cx},{y+d*0-26 if up else y+26} {cx+34},{y}" {st(c, w)}/>'
    return out


def horse_head(cx=100, cy=130, s=1.0, c="#c98a4a"):
    return (f'<g transform="translate({cx} {cy}) scale({s}) translate(-100 -130)">'
            f'<path d="M62 204 L68 130 C68 92 88 62 118 54 L126 34 L136 58 C162 66 176 92 178 120 L182 138 C184 148 172 156 160 150 L150 146 C148 168 130 182 120 204Z" fill="{c}" stroke="#3a2008" stroke-width="4" stroke-linejoin="round"/>'
            f'<path d="M118 54 C98 72 88 100 90 130 M110 60 C92 82 82 110 86 140" fill="none" stroke="#3a2008" stroke-width="5" stroke-linecap="round"/>'
            f'<circle cx="150" cy="100" r="5" fill="#10141c"/><circle cx="168" cy="132" r="3" fill="#3a2008"/></g>')


E = {}


def reg(*names):
    def deco(fn):
        for n in names:
            E[n] = (fn, n)
        return fn
    return deco


# ---------------- 基本牌 ----------------
@reg("殺")
def _():
    return '<path d="M34 196 Q96 96 170 56" fill="none" stroke="#ff4a3d" stroke-width="11" stroke-linecap="round" opacity=".75"/>' + sword()


@reg("火")
def _():
    return flame(100, 120, 1.1) + sword(-45, s=.95)


@reg("冰")
def _():
    return snow(100, 120, 70) + sword(-45, "#d8f4ff", "#5aa8d8", s=.95)


@reg("雷")
def _():
    return bolt(100, 118, 1.15) + sword(-45, "#f4f4ff", "#8a8ad8", s=.95)


@reg("閃")
def _():
    return (f'<path d="M40 96 C92 54 160 74 156 112 C153 140 112 138 110 116" {st("#7fe0ff", 9)}/>'
            f'<path d="M52 142 C96 112 140 128 136 152 C134 168 108 166 108 154" {st("#bff2ff", 7)}/>'
            f'<line x1="26" y1="176" x2="86" y2="176" {st("#7fe0ff", 5)}/><line x1="44" y1="194" x2="110" y2="194" {st("#bff2ff", 4)}/><line x1="150" y1="170" x2="176" y2="170" {st("#7fe0ff", 4)}/>')


@reg("桃")
def _():
    return peach(100, 122, 1.05)


@reg("酒")
def _():
    return (f'<ellipse cx="100" cy="150" rx="46" ry="52" fill="#a8541f" stroke="#3a1a08" stroke-width="4"/>'
            f'<rect x="84" y="78" width="32" height="34" rx="8" fill="#8a4318" stroke="#3a1a08" stroke-width="4"/>'
            f'<rect x="78" y="64" width="44" height="18" rx="7" fill="#d6452a" stroke="#6a1408" stroke-width="3"/>'
            f'<path d="M62 146 H138 M64 166 H136" stroke="#e8c872" stroke-width="4"/><circle cx="100" cy="150" r="16" fill="#e8c872" stroke="#7a5a10" stroke-width="3"/>'
            f'<path d="M92 50 q-8 -10 0 -18 M108 50 q8 -10 0 -18" {st("#f6ecd0", 4)} opacity=".8"/>')


# ---------------- 錦囊 ----------------
@reg("順")
def _():
    fingers = ''.join(f'<rect x="{66+i*17}" y="{92-(6 if i in (1,2) else 0)}" width="14" height="56" rx="7" fill="#f2c9a0" stroke="#7a4a20" stroke-width="3"/>' for i in range(4))
    return (card(100, 150, -8, 62, 86) + fingers + '<rect x="62" y="136" width="74" height="56" rx="20" fill="#f2c9a0" stroke="#7a4a20" stroke-width="3"/>'
            '<rect x="42" y="150" width="32" height="14" rx="7" transform="rotate(-30 56 157)" fill="#f2c9a0" stroke="#7a4a20" stroke-width="3"/>')


@reg("過")
def _():
    return ('<path d="M24 160 Q60 90 96 118 L96 160Z" fill="#8a6a3a" stroke="#3a2a10" stroke-width="4"/><path d="M176 160 Q140 90 108 118 L108 160Z" fill="#8a6a3a" stroke="#3a2a10" stroke-width="4"/>'
            f'<rect x="102" y="148" width="22" height="8" rx="2" transform="rotate(35 113 152)" fill="#c9a060" stroke="#3a2a10" stroke-width="2"/><rect x="82" y="168" width="22" height="8" rx="2" transform="rotate(-30 93 172)" fill="#c9a060" stroke="#3a2a10" stroke-width="2"/>'
            f'<path d="M14 190 q16 -12 32 0 t32 0 t32 0 t32 0 t32 0" {st("#7fe0ff", 6)}/><path d="M14 212 q16 -12 32 0 t32 0 t32 0 t32 0 t32 0" {st("#4aa8e0", 6)}/>')


@reg("反")
def _():
    return (f'<path d="M150 98 A52 52 0 0 0 60 92" {st("#7fe0ff", 9)}/><polygon points="52,70 78,100 44,108" fill="#7fe0ff"/>'
            f'<path d="M50 154 A52 52 0 0 0 140 160" {st("#ffb347", 9)}/><polygon points="148,182 122,152 156,144" fill="#ffb347"/>'
            f'<circle cx="100" cy="127" r="14" fill="{PAR}" stroke="#7a5a10" stroke-width="3"/>')


@reg("調")
def _():
    return ('<polygon points="22,196 78,92 112,150 134,118 182,196" fill="#4a5a3a" stroke="#1f2a14" stroke-width="4" stroke-linejoin="round"/>'
            '<circle cx="104" cy="104" r="40" fill="#f0a030" stroke="#5a3008" stroke-width="4"/><circle cx="76" cy="74" r="14" fill="#f0a030" stroke="#5a3008" stroke-width="4"/><circle cx="132" cy="74" r="14" fill="#f0a030" stroke="#5a3008" stroke-width="4"/>'
            '<path d="M104 68 v18 M88 74 l6 14 M120 74 l-6 14 M70 108 h14 M124 108 h14" stroke="#3a1a04" stroke-width="5" stroke-linecap="round"/>'
            '<circle cx="90" cy="102" r="5" fill="#10141c"/><circle cx="118" cy="102" r="5" fill="#10141c"/><path d="M96 122 q8 8 16 0" stroke="#3a1a04" stroke-width="4" fill="none" stroke-linecap="round"/>')


@reg("占")
def _():
    return ('<circle cx="100" cy="112" r="56" fill="#3a2a78" stroke="#c9b8ff" stroke-width="5"/><circle cx="100" cy="112" r="44" fill="#5a46b0" opacity=".6"/>'
            '<path d="M70 92 Q84 66 112 64" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" opacity=".7"/>'
            + star4(120, 118, 14) + star4(84, 128, 9) + star4(104, 90, 7)
            + '<path d="M62 176 H138 L124 204 H76Z" fill="#8a6a2a" stroke="#3a2a08" stroke-width="4" stroke-linejoin="round"/>')


@reg("南")
def _():
    return ('<line x1="40" y1="200" x2="150" y2="50" stroke="#c9a060" stroke-width="7" stroke-linecap="round"/><polygon points="150,32 158,66 138,60" fill="#e8eef5" stroke="#6a7a8a" stroke-width="3"/>'
            '<line x1="160" y1="200" x2="50" y2="50" stroke="#c9a060" stroke-width="7" stroke-linecap="round"/><polygon points="50,32 62,60 42,66" fill="#e8eef5" stroke="#6a7a8a" stroke-width="3"/>'
            '<ellipse cx="100" cy="132" rx="38" ry="48" fill="#8a2a1a" stroke="#e8c872" stroke-width="5"/><path d="M100 90 V176 M70 132 H130" stroke="#e8c872" stroke-width="5"/><circle cx="100" cy="132" r="12" fill="#e8c872"/>'
            '<path d="M86 84 q-6 -26 14 -40 q20 14 14 40" fill="#3ab870" stroke="#14502c" stroke-width="3"/>')


@reg("萬")
def _():
    out = ""
    for i, (x, y) in enumerate([(60, 70), (100, 52), (140, 70), (80, 120), (122, 124)]):
        out += (f'<g transform="translate({x} {y}) rotate(25)"><line x1="0" y1="0" x2="0" y2="84" stroke="#c9a060" stroke-width="5" stroke-linecap="round"/><polygon points="0,98 -9,80 9,80" fill="#e8eef5" stroke="#6a7a8a" stroke-width="2"/>'
                f'<polygon points="0,6 -10,-8 0,-2 10,-8" fill="#ff6b5a"/><polygon points="0,18 -10,4 0,10 10,4" fill="#ff6b5a"/></g>')
    return out


@reg("無")
def _():
    return ('<circle cx="100" cy="112" r="50" fill="none" stroke="#c9d8ff" stroke-width="5" stroke-dasharray="10 9"/>' + star4(100, 112, 38, "#fff6c4") + star4(150, 74, 12) + star4(52, 150, 10)
            + card(74, 192, -10, 40, 56) + card(126, 192, 10, 40, 56))


@reg("無懈")
def _():
    return shield(100, 120, 1.05, "#26407a", "#9fc3ff", f'<line x1="66" y1="82" x2="134" y2="156" {st("#ff5a5a", 12)}/><line x1="134" y1="82" x2="66" y2="156" {st("#ff5a5a", 12)}/>')


@reg("轉")
def _():
    return (f'<rect x="26" y="88" width="56" height="56" rx="10" fill="#2a4a8a" stroke="{PAR}" stroke-width="4"/><rect x="118" y="88" width="56" height="56" rx="10" fill="#8a4a2a" stroke="{PAR}" stroke-width="4"/>'
            f'<path d="M50 166 Q100 200 150 166" {st("#7fe0ff", 7)}/><polygon points="156,160 138,158 148,178" fill="#7fe0ff"/><path d="M150 70 Q100 36 50 70" {st("#ffb347", 7)}/><polygon points="44,76 62,78 52,58" fill="#ffb347"/>'
            + sword(-45, cx=54, cy=116, s=.38) + shield(146, 118, .34, "#6a4a2a"))


@reg("突")
def _():
    return ('<path d="M20 124 H110" stroke="#ffb347" stroke-width="7" stroke-linecap="round" opacity=".6"/><path d="M34 98 H98 M30 150 H92" stroke="#ffb347" stroke-width="5" stroke-linecap="round" opacity=".5"/>'
            '<line x1="40" y1="124" x2="168" y2="124" stroke="#c9a060" stroke-width="8" stroke-linecap="round"/><polygon points="186,124 150,100 156,124 150,148" fill="#e8eef5" stroke="#6a7a8a" stroke-width="3"/>'
            '<polygon points="88,124 110,84 120,124 110,164" fill="#d6452a" stroke="#6a1408" stroke-width="3"/>')


@reg("桃園")
def _():
    return peach(100, 82, .5) + peach(58, 160, .5) + peach(142, 160, .5) + f'<path d="M100 120 m-60 20 a60 60 0 0 1 120 0" {st(GOLD, 4)} opacity=".7"/>'


@reg("樂")
def _():
    return ('<path d="M70 168 V70 L146 52 V150" fill="none" stroke="#f6ecd0" stroke-width="8" stroke-linejoin="round"/><path d="M70 90 L146 72" stroke="#f6ecd0" stroke-width="12"/>'
            '<ellipse cx="56" cy="170" rx="22" ry="16" fill="#f6ecd0" transform="rotate(-18 56 170)"/><ellipse cx="132" cy="152" rx="22" ry="16" fill="#f6ecd0" transform="rotate(-18 132 152)"/>'
            '<path d="M24 100 q-8 -14 0 -28 M176 120 q8 -14 0 -28" ' + st("#e8c8ff", 4) + '/>')


@reg("聲")
def _():
    return ('<ellipse cx="100" cy="132" rx="52" ry="46" fill="#a8341f" stroke="#e8c872" stroke-width="5"/><ellipse cx="100" cy="132" rx="52" ry="20" fill="none" stroke="#e8c872" stroke-width="3"/>'
            + ''.join(f'<circle cx="{x}" cy="{y}" r="4" fill="#e8c872"/>' for x, y in [(60, 112), (84, 104), (116, 104), (140, 112), (60, 152), (84, 160), (116, 160), (140, 152)])
            + '<line x1="36" y1="60" x2="92" y2="118" stroke="#c9a060" stroke-width="7" stroke-linecap="round"/><line x1="164" y1="60" x2="108" y2="118" stroke="#c9a060" stroke-width="7" stroke-linecap="round"/>' + arrow(20, 200, 70, 200, "#7fe0ff") + arrow(180, 200, 130, 200, "#ffb347"))


@reg("增")
def _():
    return (card(66, 140, -14, 58, 82, "#cfe0ff") + card(100, 132, 0, 58, 82, "#f6ecd0") + card(134, 140, 14, 58, 82, "#ffe0cf")
            + '<circle cx="146" cy="70" r="26" fill="#3ab870" stroke="#14502c" stroke-width="4"/><path d="M146 56 V84 M132 70 H160" stroke="#fff" stroke-width="7" stroke-linecap="round"/>')


@reg("決")
def _():
    return sword(-50, cx=100, cy=122, s=1.0) + sword(50, cx=100, cy=122, s=1.0, blade="#ffe8d8", edge="#c08060")


@reg("強")
def _():
    return star4(100, 112, 70, "#ffe27a") + chevrons(100, 150, 2, True, "#ff7a45", 11) + '<circle cx="100" cy="112" r="14" fill="#fff6c4"/>'


@reg("弱")
def _():
    return ('<polyline points="66,70 100,100 134,70" ' + st("#d6e2ff", 11) + '/><polyline points="66,112 100,142 134,112" ' + st("#b4c6ee", 11) + '/><polyline points="66,154 100,184 134,154" ' + st("#8fa6d8", 11) + '/>'
            '<circle cx="100" cy="124" r="64" fill="none" stroke="#b4c6ee" stroke-width="4" stroke-dasharray="4 10"/>')


@reg("火攻")
def _():
    return flame(100, 112, 1.1) + card(100, 178, 0, 70, 44, "#f6ecd0")


@reg("借")
def _():
    return ('<path d="M52 84 A58 58 0 0 1 148 84" ' + st("#7fe0ff", 7) + '/><polygon points="156,82 138,76 146,98" fill="#7fe0ff"/><path d="M148 168 A58 58 0 0 1 52 168" ' + st("#ffb347", 7) + '/><polygon points="44,170 62,176 54,154" fill="#ffb347"/>'
            + sword(-35, "#d8dde5", "#7a8aa0", s=.7))


@reg("飢")
def _():
    return ('<path d="M44 124 H156 C156 168 130 194 100 194 C70 194 44 168 44 124Z" fill="#c9a060" stroke="#3a2a10" stroke-width="5"/><path d="M44 124 H156" stroke="#3a2a10" stroke-width="5"/>'
            '<ellipse cx="100" cy="124" rx="56" ry="10" fill="#3a2a10"/><path d="M80 100 q-8 -10 0 -20 q8 -10 0 -20 M104 100 q-8 -10 0 -20 q8 -10 0 -20 M128 100 q-8 -10 0 -20 q8 -10 0 -20" ' + st("#cfd8e8", 4) + ' opacity=".7"/>'
            '<line x1="150" y1="40" x2="124" y2="116" stroke="#e8c872" stroke-width="5" stroke-linecap="round"/><line x1="164" y1="46" x2="134" y2="118" stroke="#e8c872" stroke-width="5" stroke-linecap="round"/>')


@reg("草")
def _():
    out = ""
    for x, h, rot in [(60, 90, -14), (84, 120, -6), (108, 130, 4), (132, 104, 12), (150, 76, 20)]:
        out += f'<path d="M{x} 206 Q{x+rot} {206-h/2} {x+rot*2} {206-h}" stroke="#6ecb54" stroke-width="9" fill="none" stroke-linecap="round"/>'
    return out + '<line x1="100" y1="40" x2="100" y2="206" stroke="#8a6a3a" stroke-width="6"/><polygon points="102,44 150,56 102,74" fill="#d6452a" stroke="#6a1408" stroke-width="3"/>'


@reg("閃電")
def _():
    return ('<path d="M44 96 a28 28 0 0 1 22 -40 a34 34 0 0 1 64 6 a26 26 0 0 1 28 38 Z" fill="#5a4a8a" stroke="#c9b8ff" stroke-width="4"/>' + bolt(100, 150, .9))


@reg("降雷")
def _():
    return ('<path d="M44 84 a26 26 0 0 1 22 -36 a32 32 0 0 1 60 6 a24 24 0 0 1 26 34 Z" fill="#46508a" stroke="#a8b8ff" stroke-width="4"/>' + bolt(100, 128, .62) + card(100, 190, 0, 70, 50, "#d8c8ff")
            + '<path d="M60 210 A40 12 0 0 0 140 210" ' + st("#e8c8ff", 4) + '/>')


@reg("發")
def _():
    rays = ''.join(f'<line x1="100" y1="118" x2="{100+78*math.cos(math.radians(a)):.1f}" y2="{118+78*math.sin(math.radians(a)):.1f}" stroke="#ffd24a" stroke-width="6" stroke-linecap="round"/>' for a in range(0, 360, 30))
    return rays + '<circle cx="100" cy="118" r="38" fill="#ff7a2a" stroke="#6a2a00" stroke-width="5"/>' + chevrons(100, 128, 2, True, "#fff6c4", 8)


@reg("毒")
def _():
    return ('<path d="M82 60 H118 V96 L152 170 Q156 204 120 204 H80 Q44 204 48 170 L82 96Z" fill="#2a3a2a" stroke="#cfe8cf" stroke-width="5" stroke-linejoin="round"/>'
            '<path d="M60 150 H140 L152 170 Q156 198 120 198 H80 Q44 198 48 170Z" fill="#7be04a" opacity=".85"/><rect x="76" y="44" width="48" height="18" rx="6" fill="#8a6a3a" stroke="#3a2a10" stroke-width="3"/>'
            '<circle cx="84" cy="150" r="7" fill="#d8ffb0"/><circle cx="108" cy="136" r="5" fill="#d8ffb0"/><circle cx="118" cy="162" r="6" fill="#d8ffb0"/>'
            '<circle cx="100" cy="176" r="12" fill="#f6ecd0"/><circle cx="95" cy="174" r="3" fill="#10141c"/><circle cx="105" cy="174" r="3" fill="#10141c"/>')


@reg("兵")
def _():
    return ('<path d="M70 80 Q56 130 64 176 Q100 214 136 176 Q144 130 130 80 Z" fill="#d8b878" stroke="#5a4010" stroke-width="5"/><path d="M68 84 Q100 62 132 84" fill="none" stroke="#5a4010" stroke-width="5"/>'
            '<path d="M90 70 L84 48 M110 70 L116 48" ' + st("#d8b878", 7) + '/><path d="M76 118 q24 12 48 0" stroke="#8a6a2a" stroke-width="4" fill="none"/>'
            '<line x1="32" y1="184" x2="168" y2="104" stroke="#ff5a5a" stroke-width="9" stroke-linecap="round"/>')


@reg("偽")
def _():
    return ('<g transform="rotate(-12 80 128)"><ellipse cx="80" cy="128" rx="40" ry="50" fill="#f6ecd0" stroke="#7a5a2a" stroke-width="4"/><path d="M58 118 q10 -10 20 0 M86 118 q10 -10 20 0" ' + st("#10141c", 5) + '/><path d="M62 146 q18 16 38 0" ' + st("#c4252a", 5) + '/></g>'
            '<g transform="rotate(12 124 138)"><ellipse cx="124" cy="138" rx="40" ry="50" fill="#2a2a3a" stroke="#c9b8ff" stroke-width="4"/><path d="M102 130 l18 8 M146 130 l-18 8" ' + st("#ffd24a", 5) + '/><path d="M106 162 q18 -14 38 0" ' + st("#ffd24a", 5) + '/></g>')


@reg("出")
def _():
    return (card(86, 120, -6, 58, 82, "#cfe0ff") + card(112, 130, 8, 58, 82, "#f6ecd0") + '<path d="M40 190 Q100 230 168 160" ' + st("#ffb347", 7) + '/><polygon points="176,152 152,156 166,176" fill="#ffb347"/><circle cx="140" cy="82" r="22" fill="#d6452a" stroke="#fff" stroke-width="3"/><text x="140" y="92" font-size="28" font-weight="900" text-anchor="middle" fill="#fff" font-family="sans-serif">!</text>')


@reg("拋")
def _():
    return ('<rect x="22" y="130" width="56" height="34" rx="4" fill="#a8541f" stroke="#3a1a08" stroke-width="4"/><path d="M22 147 H78 M50 130 V147" stroke="#3a1a08" stroke-width="3"/>'
            '<circle cx="150" cy="122" r="36" fill="#5be0a8" stroke="#14502c" stroke-width="5"/><circle cx="150" cy="122" r="11" fill="#10141c"/>' + arrow(86, 120, 112, 120, PAR) + '<path d="M40 112 Q100 40 142 78" ' + st("#ffd24a", 5) + ' stroke-dasharray="2 10"/>')


@reg("未")
def _():
    drops = ''.join(f'<line x1="{x}" y1="{y}" x2="{x-6}" y2="{y+18}" stroke="#7fe0ff" stroke-width="5" stroke-linecap="round"/>' for x, y in [(34, 60), (166, 66), (48, 100), (154, 108), (26, 140), (172, 150)])
    return (drops + '<path d="M36 124 A64 64 0 0 1 164 124 Z" fill="#c4252a" stroke="#6a1408" stroke-width="5"/><path d="M68 124 A32 64 0 0 1 100 60 M132 124 A32 64 0 0 0 100 60 M100 60 V124" fill="none" stroke="#6a1408" stroke-width="3"/>'
            '<path d="M100 124 V190 q0 14 -14 14 q-10 0 -10 -10" ' + st("#e8c872", 6) + '/>')


@reg("笑")
def _():
    return ('<circle cx="100" cy="106" r="50" fill="#ffd24a" stroke="#7a5a10" stroke-width="5"/><path d="M78 96 q8 -8 16 0 M106 96 q8 -8 16 0" ' + st("#3a2a08", 5) + '/><path d="M72 120 q28 34 56 0" ' + st("#3a2a08", 6) + '/>'
            + sword(-28, "#d8dde5", "#7a8aa0", cx=100, cy=196, s=.5))


@reg("鴻")
def _():
    cup = lambda x, rot: f'<g transform="translate({x} 110) rotate({rot})"><path d="M-26 -30 H26 L18 14 Q0 30 -18 14Z" fill="#e8c872" stroke="#7a5a10" stroke-width="4"/><rect x="-5" y="22" width="10" height="26" fill="#e8c872" stroke="#7a5a10" stroke-width="3"/><rect x="-22" y="46" width="44" height="9" rx="4" fill="#e8c872" stroke="#7a5a10" stroke-width="3"/></g>'
    return cup(56, -14) + cup(144, 14) + sword(90, "#e8eef5", "#8aa0b8", cx=100, cy=196, s=.55)


@reg("隔")
def _():
    return (flame(144, 92, .5) + '<path d="M14 168 q16 -12 32 0 t32 0 t32 0 t32 0 t32 0" ' + st("#7fe0ff", 6) + '/><path d="M14 194 q16 -12 32 0 t32 0 t32 0 t32 0 t32 0" ' + st("#4aa8e0", 6) + '/>'
            '<path d="M28 116 Q64 86 100 116 Q64 146 28 116Z" fill="#f6ecd0" stroke="#10141c" stroke-width="4"/><circle cx="64" cy="116" r="11" fill="#2a4a8a"/><circle cx="64" cy="116" r="5" fill="#10141c"/>')


@reg("孤")
def _():
    def die(x, y, rot, pips):
        dots = ''.join(f'<circle cx="{x+dx}" cy="{y+dy}" r="5" fill="#10141c"/>' for dx, dy in pips)
        return f'<g transform="rotate({rot} {x} {y})"><rect x="{x-30}" y="{y-30}" width="60" height="60" rx="11" fill="#f6ecd0" stroke="#8a6a2a" stroke-width="4"/></g>' + dots
    return die(70, 112, -12, [(-12, -12), (12, 12), (0, 0), (-12, 12), (12, -12)]) + die(130, 150, 10, [(-10, -10), (10, 10), (0, 0)]) + star4(138, 76, 14, "#ffd24a")


@reg("投")
def _():
    return (peach(64, 108, .55) + '<circle cx="140" cy="116" r="30" fill="#8a5ad0" stroke="#3a1a70" stroke-width="4"/><path d="M140 86 q8 -14 20 -12" ' + st("#59b24a", 5) + '/>'
            + '<path d="M60 176 Q100 206 142 176" ' + st("#7fe0ff", 6) + '/><polygon points="150,170 132,168 142,188" fill="#7fe0ff"/><path d="M142 60 Q100 30 62 62" ' + st("#ffb347", 6) + '/><polygon points="56,68 74,70 64,50" fill="#ffb347"/>')


@reg("五")
def _():
    out = ""
    for a in (-24, 0, 24):
        out += f'<g transform="rotate({a} 100 200)"><line x1="100" y1="204" x2="100" y2="60" stroke="#c9a060" stroke-width="5"/>'
        for i in range(6):
            y = 64 + i * 15
            out += f'<ellipse cx="90" cy="{y+6}" rx="6" ry="11" transform="rotate(-30 90 {y+6})" fill="#ffd24a" stroke="#7a5a10" stroke-width="2"/><ellipse cx="110" cy="{y+6}" rx="6" ry="11" transform="rotate(30 110 {y+6})" fill="#ffd24a" stroke="#7a5a10" stroke-width="2"/>'
        out += '</g>'
    return out


@reg("鐵")
def _():
    link = lambda x, y, rot: f'<g transform="translate({x} {y}) rotate({rot})"><rect x="-34" y="-17" width="68" height="34" rx="17" fill="none" stroke="#c8d0dc" stroke-width="9"/><rect x="-34" y="-17" width="68" height="34" rx="17" fill="none" stroke="#6a7a8c" stroke-width="3"/></g>'
    return link(66, 78, 38) + link(100, 122, -38) + link(134, 166, 38) + '<circle cx="42" cy="54" r="9" fill="#5a6a7c"/><circle cx="160" cy="190" r="9" fill="#5a6a7c"/>'


# ---------------- 防具 ----------------
@reg("八卦陣")
def _():
    return bagua()


@reg("仁王盾")
def _():
    return shield(100, 122, 1.05, "#1a1a22", GOLD, '<circle cx="100" cy="112" r="26" fill="#d6452a" stroke="#e8c872" stroke-width="4"/><path d="M86 106 l12 6 M114 106 l-12 6 M86 128 q14 -10 28 0" ' + st("#e8c872", 4) + '/>')


@reg("藤甲")
def _():
    w = ''.join(f'<line x1="{44+i*16}" y1="60" x2="{44+i*16-40}" y2="200" stroke="#2a6a30" stroke-width="6"/><line x1="{44+i*16-40}" y1="60" x2="{44+i*16}" y2="200" stroke="#3a8a40" stroke-width="6"/>' for i in range(0, 10))
    return ('<clipPath id="vc"><path d="M60 52 H140 L172 92 L152 114 V200 H48 V114 L28 92Z"/></clipPath><path d="M60 52 H140 L172 92 L152 114 V200 H48 V114 L28 92Z" fill="#1f5a26"/><g clip-path="url(#vc)">' + w + '</g>'
            '<path d="M60 52 H140 L172 92 L152 114 V200 H48 V114 L28 92Z" fill="none" stroke="#bff2a0" stroke-width="5" stroke-linejoin="round"/><path d="M76 52 Q100 84 124 52" fill="none" stroke="#bff2a0" stroke-width="5"/>')


@reg("緩衝盾")
def _():
    return shield(100, 122, 1.05, "#3a4a66", "#9fe8ff", ''.join(f'<ellipse cx="100" cy="116" rx="{r}" ry="{r*.8:.0f}" fill="none" stroke="#9fe8ff" stroke-width="3" opacity="{1-r/70:.2f}"/>' for r in (14, 28, 42, 56)))


@reg("雷盾")
def _():
    return shield(100, 122, 1.05, "#2a2a5a", "#c9c9ff", bolt(100, 116, .5))


@reg("火盾")
def _():
    return shield(100, 122, 1.05, "#5a1f1a", "#ffb08a", flame(100, 114, .5))


@reg("冰盾")
def _():
    return shield(100, 122, 1.05, "#1f4a6a", "#bfe9ff", snow(100, 112, 34, "#e8fbff", 5))


# ---------------- 坐騎 ----------------
@reg("+1馬")
def _():
    return horse_head(100, 118, 1.0, "#eef2f8") + '<circle cx="46" cy="190" r="22" fill="#26407a" stroke="#9fc3ff" stroke-width="4"/><text x="46" y="199" font-size="24" font-weight="900" text-anchor="middle" fill="#fff" font-family="sans-serif">+1</text>'


@reg("-1馬")
def _():
    return horse_head(100, 118, 1.0, "#b8381c") + '<circle cx="46" cy="190" r="22" fill="#8a2a1a" stroke="#ffb08a" stroke-width="4"/><text x="46" y="199" font-size="24" font-weight="900" text-anchor="middle" fill="#fff" font-family="sans-serif">-1</text>'


# ---------------- 武器 ----------------
# ---------------- 武器 (依實物外型重畫: 鋼身 + 金色配件 + 深色描邊) ----------------
_GOLD, _GD = "#e8c35a", "#6a4a10"
_ST, _STD, _STL = "#b6bcc4", "#2a2f36", "#e8edf2"
_WOOD, _WOODD = "#9a6a34", "#3a2410"


def _tassel(x, y, c="#d8262c", n=5, ln=26):
    return (f'<circle cx="{x}" cy="{y}" r="5" fill="{_GOLD}" stroke="{_GD}" stroke-width="2.5"/>'
            + ''.join(f'<path d="M{x + (k - n // 2) * 3} {y + 4} q{(k - n // 2) * 2} {ln * .5} {(k - n // 2) * 3} {ln}" fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round"/>' for k in range(n)))


@reg("諸葛連弩")
def _():   # 連弩: 木製弩身 + 頂上的箭匣 + 前端的弩臂和弦 + 後面的扳機槓桿
    bolts = ''.join(f'<line x1="{x}" y1="86" x2="{x}" y2="100" stroke="{_STL}" stroke-width="4" stroke-linecap="round"/><path d="M{x - 3} 86 l3 -8 l3 8z" fill="{_ST}" stroke="{_STD}" stroke-width="1.5"/>' for x in (82, 96, 110))
    return ('<g transform="rotate(-14 100 150)">'
            f'<path d="M150 70 Q202 150 150 230" fill="none" stroke="{_WOODD}" stroke-width="12" stroke-linecap="round"/><path d="M150 70 Q202 150 150 230" fill="none" stroke="{_WOOD}" stroke-width="7" stroke-linecap="round"/>'
            '<line x1="150" y1="70" x2="116" y2="150" stroke="#f1ead0" stroke-width="2.5"/><line x1="150" y1="230" x2="116" y2="150" stroke="#f1ead0" stroke-width="2.5"/>'
            f'<rect x="30" y="136" width="130" height="26" rx="8" fill="{_WOOD}" stroke="{_WOODD}" stroke-width="4.5"/><line x1="40" y1="149" x2="150" y2="149" stroke="{_WOODD}" stroke-width="2"/>'
            f'<rect x="64" y="100" width="62" height="38" rx="5" fill="#b8843e" stroke="{_WOODD}" stroke-width="4.5"/>'
            + ''.join(f'<line x1="{x}" y1="106" x2="{x}" y2="132" stroke="{_WOODD}" stroke-width="2.2"/>' for x in (78, 92, 106, 120))
            + bolts
            + f'<rect x="146" y="132" width="14" height="34" rx="3" fill="{_GOLD}" stroke="{_GD}" stroke-width="3.5"/>'
            f'<path d="M36 156 L18 196" fill="none" stroke="{_WOODD}" stroke-width="11" stroke-linecap="round"/><path d="M36 156 L18 196" fill="none" stroke="{_WOOD}" stroke-width="6" stroke-linecap="round"/><circle cx="16" cy="200" r="7" fill="none" stroke="{_GOLD}" stroke-width="4"/>'
            f'<line x1="44" y1="132" x2="190" y2="132" stroke="{_ST}" stroke-width="4" stroke-linecap="round"/><path d="M192 132 l-12 -7 v14z" fill="{_ST}" stroke="{_STD}" stroke-width="2"/></g>')


@reg("孔雀羽扇")
def _():   # 一把半圓形的孔雀翎羽扇: 七片羽毛從扇柄放射開來,每片尾端一個「眼」
    feather = ''.join(f'<g transform="rotate({a} 100 220)"><ellipse cx="100" cy="160" rx="15" ry="54" fill="#2a9a86" stroke="#0a3a3a" stroke-width="3"/>'
                      '<line x1="100" y1="212" x2="100" y2="118" stroke="#8be0c0" stroke-width="1.6"/>'
                      '<ellipse cx="100" cy="126" rx="8" ry="12" fill="#1a5aa0" stroke="#e8c872" stroke-width="2"/><ellipse cx="100" cy="126" rx="3.5" ry="6" fill="#ffd24a"/></g>'
                      for a in sorted((-48, -32, -16, 0, 16, 32, 48), key=lambda v: -abs(v)))
    return ('<g transform="translate(0 -38)">' + feather + '<path d="M64 214 Q100 190 136 214" fill="none" stroke="#e8c872" stroke-width="5" stroke-linecap="round"/>'
            '<path d="M92 214 L108 214 L104 262 Q100 266 96 262Z" fill="#8a4318" stroke="#3a1a08" stroke-width="3" stroke-linejoin="round"/><circle cx="100" cy="214" r="9" fill="#e8c872" stroke="#8a6a2a" stroke-width="2"/></g>')


@reg("青龍偃月刀")
def _():   # 長柄大刀: 寬闊彎曲的刀身 (背面有缺口)、刀面刻龍、金色刀座 / 握把 / 柄尾
    GOLD_, GD = "#e8c35a", "#6a4a10"
    blade = ('<path d="M90 110 C70 92 68 58 82 40 C92 28 114 22 142 20 C130 32 126 44 128 54 L140 58 L127 64 L142 74 C132 88 124 100 112 110Z" fill="#b6bcc4" stroke="#2a2f36" stroke-width="4.5" stroke-linejoin="round"/>'
             '<path d="M90 110 C70 92 68 58 82 40" fill="none" stroke="#e8edf2" stroke-width="3" stroke-linecap="round" stroke-opacity=".85"/>'
             '<path d="M118 46 C98 50 100 66 108 74 C116 82 100 90 106 100" fill="none" stroke="#2a2f36" stroke-width="3.2" stroke-linecap="round"/>'
             '<circle cx="119" cy="45" r="4.5" fill="#2a2f36"/><path d="M121 41 L128 36 M118 40 L119 33" stroke="#2a2f36" stroke-width="2.4" stroke-linecap="round"/>'
             '<path d="M86 62 C92 58 96 64 94 70 M84 84 C92 80 98 88 94 96" fill="none" stroke="#2a2f36" stroke-width="2.2" stroke-linecap="round" stroke-opacity=".7"/>')
    collar = (f'<path d="M88 108 L114 108 L110 134 L92 134Z" fill="{GOLD_}" stroke="{GD}" stroke-width="4" stroke-linejoin="round"/>'
              f'<path d="M94 112 Q101 120 98 130 M104 112 Q108 120 104 130" fill="none" stroke="{GD}" stroke-width="2.4" stroke-linecap="round"/>'
              f'<rect x="86" y="134" width="30" height="8" rx="2" fill="{GOLD_}" stroke="{GD}" stroke-width="3.5"/>')
    grip = (f'<rect x="95" y="142" width="12" height="46" fill="{GOLD_}" stroke="{GD}" stroke-width="3.5"/>'
            + ''.join(f'<path d="M95 {y} L107 {y + 8}" stroke="{GD}" stroke-width="2"/>' for y in range(146, 184, 8)))
    pole = ('<rect x="97" y="188" width="8" height="58" fill="#aab0b8" stroke="#2a2f36" stroke-width="3.5"/>'
            '<line x1="99.5" y1="190" x2="99.5" y2="244" stroke="#e8edf2" stroke-width="1.6" stroke-opacity=".8"/>')
    butt = (f'<rect x="95" y="246" width="12" height="22" fill="{GOLD_}" stroke="{GD}" stroke-width="3.5"/>'
            f'<path d="M96 268 L106 268 L101 284Z" fill="{GOLD_}" stroke="{GD}" stroke-width="3.5" stroke-linejoin="round"/>')
    return '<g transform="translate(0 -6)">' + blade + collar + grip + pole + butt + '</g>'


@reg("寒冰劍")
def _():   # 冰藍的直劍: 劍身有血槽、刃緣參差像冰晶、護手是水晶、周圍飄著雪花
    stars = ''.join(f'<path d="M{x} {y - r} L{x + r * .28} {y - r * .28} L{x + r} {y} L{x + r * .28} {y + r * .28} L{x} {y + r} L{x - r * .28} {y + r * .28} L{x - r} {y} L{x - r * .28} {y - r * .28}Z" fill="#fff" stroke="#6ab8e0" stroke-width="1.5"/>' for x, y, r in ((52, 70, 9), (156, 112, 11), (60, 190, 7), (150, 214, 8)))
    return ('<g transform="rotate(24 100 143)">'
            '<path d="M100 18 L113 40 L110 56 L114 70 L110 86 L113 102 L110 150 L100 172 L90 150 L87 102 L90 86 L86 70 L90 56 L87 40Z" fill="#dff4ff" stroke="#2f6f98" stroke-width="4.5" stroke-linejoin="round"/>'
            '<path d="M100 26 V160" stroke="#7ec4ec" stroke-width="5" stroke-linecap="round"/><path d="M96 40 V150" stroke="#fff" stroke-width="1.8" stroke-opacity=".9"/>'
            '<path d="M60 172 L88 160 L100 172 L112 160 L140 172 L126 186 L74 186Z" fill="#8fd6ff" stroke="#2a6a90" stroke-width="4" stroke-linejoin="round"/><path d="M80 174 L100 168 L120 174" fill="none" stroke="#fff" stroke-width="2"/>'
            f'<rect x="93" y="186" width="14" height="40" rx="4" fill="#27486a" stroke="#0e1e30" stroke-width="3.5"/>' + ''.join(f'<path d="M93 {y} l14 6" stroke="#8fd6ff" stroke-width="2"/>' for y in (192, 202, 212))
            + '<path d="M100 226 L109 236 L100 248 L91 236Z" fill="#8fd6ff" stroke="#2a6a90" stroke-width="3.5"/></g>' + stars)


@reg("方天畫戟")
def _():   # 方天畫戟: 長桿 + 中間的矛尖 + 兩側的月牙刃 + 紅纓
    moon = lambda sg: (f'<path d="M{100 + sg * 4} 76 C{100 + sg * 46} 66 {100 + sg * 58} 104 {100 + sg * 34} 128 C{100 + sg * 30} 108 {100 + sg * 18} 100 {100 + sg * 4} 100Z" fill="{_ST}" stroke="{_STD}" stroke-width="4.5" stroke-linejoin="round"/>'
                       f'<path d="M{100 + sg * 12} 82 C{100 + sg * 40} 78 {100 + sg * 48} 102 {100 + sg * 34} 120" fill="none" stroke="{_STL}" stroke-width="2.4" stroke-linecap="round"/>')
    return ('<g transform="rotate(10 100 143)">'
            f'<rect x="96" y="70" width="8" height="196" fill="{_WOOD}" stroke="{_WOODD}" stroke-width="3.5"/>'
            + moon(-1) + moon(1)
            + f'<path d="M100 14 C114 32 114 52 100 74 C86 52 86 32 100 14Z" fill="{_ST}" stroke="{_STD}" stroke-width="4.5" stroke-linejoin="round"/><path d="M100 26 V68" stroke="{_STL}" stroke-width="2.4"/>'
            f'<rect x="90" y="72" width="20" height="9" rx="2" fill="{_GOLD}" stroke="{_GD}" stroke-width="3.5"/>'
            + _tassel(100, 130, ln=34)
            + f'<rect x="94" y="236" width="12" height="22" fill="{_GOLD}" stroke="{_GD}" stroke-width="3.5"/><path d="M95 258 L105 258 L100 276Z" fill="{_GOLD}" stroke="{_GD}" stroke-width="3.5" stroke-linejoin="round"/></g>')


@reg("流星錘")
def _():   # 流星錘: 帶尖刺的鐵球 + 一節一節的鐵鏈 + 握把和紅穗
    cx, cy, r = 134, 96, 32
    spikes = ''.join(f'<path d="M{cx + (r - 4) * math.cos(math.radians(a - 11)):.1f} {cy + (r - 4) * math.sin(math.radians(a - 11)):.1f} L{cx + (r + 17) * math.cos(math.radians(a)):.1f} {cy + (r + 17) * math.sin(math.radians(a)):.1f} L{cx + (r - 4) * math.cos(math.radians(a + 11)):.1f} {cy + (r - 4) * math.sin(math.radians(a + 11)):.1f}Z" fill="#8c95a0" stroke="{_STD}" stroke-width="3" stroke-linejoin="round"/>' for a in range(0, 360, 30))
    pts = [((1 - t) ** 2 * 112 + 2 * (1 - t) * t * 70 + t * t * 48, (1 - t) ** 2 * 122 + 2 * (1 - t) * t * 190 + t * t * 226) for t in [k / 9 for k in range(10)]]
    links = ''
    for k in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[k], pts[k + 1]
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        links += f'<ellipse cx="{(x0 + x1) / 2:.1f}" cy="{(y0 + y1) / 2:.1f}" rx="9" ry="{4 if k % 2 else 6}" transform="rotate({ang:.0f} {(x0 + x1) / 2:.1f} {(y0 + y1) / 2:.1f})" fill="none" stroke="#8c95a0" stroke-width="3.6"/>'
    return (links + spikes
            + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#6a7482" stroke="{_STD}" stroke-width="4.5"/><circle cx="{cx - 10}" cy="{cy - 11}" r="9" fill="#c5ccd6" fill-opacity=".85"/><path d="M{cx - r + 4} {cy} h{2 * r - 8}" stroke="{_STD}" stroke-width="2.2" stroke-opacity=".55"/>'
            + f'<rect x="30" y="218" width="30" height="14" rx="6" transform="rotate(-30 45 225)" fill="{_WOOD}" stroke="{_WOODD}" stroke-width="3.5"/>' + _tassel(34, 240, ln=24))


@reg("麒麟弓")
def _():   # 麒麟弓: 鑲金的長弓,弓梢是麒麟角 / 雲紋,搭著一支箭
    return ('<g>'
            f'<path d="M126 24 Q44 143 126 262" fill="none" stroke="{_WOODD}" stroke-width="13" stroke-linecap="round"/><path d="M126 24 Q44 143 126 262" fill="none" stroke="#7a2a1a" stroke-width="8" stroke-linecap="round"/><path d="M126 24 Q44 143 126 262" fill="none" stroke="{_GOLD}" stroke-width="2.6" stroke-dasharray="10 7" stroke-linecap="round"/>'
            f'<path d="M126 24 q14 -10 22 2 q-12 -2 -18 8z M126 262 q14 10 22 -2 q-12 2 -18 -8z" fill="{_GOLD}" stroke="{_GD}" stroke-width="3" stroke-linejoin="round"/>'
            '<line x1="126" y1="26" x2="152" y2="143" stroke="#f1ead0" stroke-width="2.6"/><line x1="126" y1="260" x2="152" y2="143" stroke="#f1ead0" stroke-width="2.6"/>'
            f'<rect x="56" y="124" width="14" height="38" rx="5" fill="#2fa07a" stroke="#0e4a38" stroke-width="3.5"/><circle cx="63" cy="143" r="4" fill="{_GOLD}"/>'
            f'<line x1="70" y1="143" x2="190" y2="143" stroke="{_WOOD}" stroke-width="5" stroke-linecap="round"/><path d="M194 143 l-16 -8 v16z" fill="{_ST}" stroke="{_STD}" stroke-width="2.5" stroke-linejoin="round"/>'
            '<path d="M152 143 l-12 -9 m12 9 l-12 9 m22 -9 l-12 -9 m12 9 l-12 9" stroke="#d8262c" stroke-width="3" stroke-linecap="round" fill="none"/></g>')


@reg("青釭劍")
def _():   # 青釭劍: 細長的碧玉色劍身發著青光,金色護手和紅色劍穗
    return ('<circle cx="100" cy="150" r="70" fill="#2ad0b0" opacity=".22"/>'
            '<g transform="rotate(32 100 143)">'
            '<path d="M100 10 L110 36 L108 170 L100 184 L92 170 L90 36Z" fill="#d8f7ee" stroke="#1f7a68" stroke-width="4.5" stroke-linejoin="round"/>'
            '<path d="M100 18 V176" stroke="#2ad0b0" stroke-width="4"/><path d="M96 40 V160" stroke="#fff" stroke-width="1.8"/>'
            f'<path d="M70 186 Q100 170 130 186 L124 196 Q100 186 76 196Z" fill="{_GOLD}" stroke="{_GD}" stroke-width="4" stroke-linejoin="round"/><circle cx="100" cy="186" r="5" fill="#2ad0b0" stroke="#0e5a4a" stroke-width="2"/>'
            f'<rect x="94" y="195" width="12" height="38" rx="4" fill="#1d5a4a" stroke="#0a2a22" stroke-width="3.5"/>' + ''.join(f'<path d="M94 {y} l12 6" stroke="{_GOLD}" stroke-width="2"/>' for y in (201, 211, 221))
            + f'<circle cx="100" cy="238" r="8" fill="{_GOLD}" stroke="{_GD}" stroke-width="3.5"/>' + _tassel(100, 246, ln=30) + '</g>')


@reg("丈八蛇矛")
def _():   # 丈八蛇矛: 矛頭像蛇一樣彎彎曲曲 (波浪形刃)
    L, Rr = [], []
    for k in range(0, 21):
        t = k / 20
        y = 126 - t * 106
        cxx = 100 + 11 * math.sin(t * 9.5)
        w = 9 * (1 - t) ** .8 + .6
        L.append((cxx - w, y)); Rr.append((cxx + w, y))
    pts = L + Rr[::-1]
    d = 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts) + 'Z'
    mid = ' L'.join(f'{100 + 11 * math.sin((k / 20) * 9.5):.1f} {126 - (k / 20) * 106:.1f}' for k in range(1, 20))
    return ('<g transform="rotate(14 100 143)">'
            f'<rect x="96" y="126" width="8" height="144" fill="{_WOOD}" stroke="{_WOODD}" stroke-width="3.5"/>'
            f'<path d="{d}" fill="{_ST}" stroke="{_STD}" stroke-width="4.5" stroke-linejoin="round"/><path d="M{mid}" fill="none" stroke="{_STL}" stroke-width="2.2" stroke-linecap="round" stroke-opacity=".9"/>'
            f'<rect x="90" y="122" width="20" height="12" rx="3" fill="{_GOLD}" stroke="{_GD}" stroke-width="3.5"/>'
            + _tassel(100, 142, ln=30)
            + f'<rect x="94" y="244" width="12" height="16" fill="{_GOLD}" stroke="{_GD}" stroke-width="3.5"/><path d="M95 260 L105 260 L100 276Z" fill="{_GOLD}" stroke="{_GD}" stroke-width="3.5" stroke-linejoin="round"/></g>')


@reg("貫石斧")
def _():   # 貫石斧: 長柄大斧,斧刃寬大,下面是被劈開的石頭
    rock = ('<path d="M30 252 L44 214 L76 200 L100 214 L124 204 L152 222 L164 252Z" fill="#8a8f98" stroke="#2a2d34" stroke-width="4.5" stroke-linejoin="round"/>'
            '<path d="M98 214 L90 232 L102 242 L94 252" fill="none" stroke="#2a2d34" stroke-width="3.4" stroke-linejoin="round" stroke-linecap="round"/><path d="M52 222 L66 212 M124 214 L140 226" stroke="#c5cad2" stroke-width="3" stroke-linecap="round"/>')
    return (rock + '<g transform="rotate(-14 100 143)">'
            f'<rect x="96" y="40" width="9" height="190" fill="{_WOOD}" stroke="{_WOODD}" stroke-width="3.5"/>'
            f'<path d="M104 46 C168 24 198 92 164 146 C148 124 126 118 104 118Z" fill="{_ST}" stroke="{_STD}" stroke-width="4.5" stroke-linejoin="round"/>'
            '<path d="M112 58 C158 46 180 92 158 128" fill="none" stroke="#e8edf2" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M96 70 L74 60 L82 88 L96 92Z" fill="{_ST}" stroke="{_STD}" stroke-width="4" stroke-linejoin="round"/>'
            f'<rect x="92" y="44" width="17" height="80" rx="3" fill="none" stroke="{_GOLD}" stroke-width="3" stroke-dasharray="14 6"/>'
            f'<rect x="92" y="118" width="17" height="10" rx="3" fill="{_GOLD}" stroke="{_GD}" stroke-width="3.5"/>'
            f'<circle cx="100" cy="236" r="7" fill="{_GOLD}" stroke="{_GD}" stroke-width="3.5"/></g>')


SKIN = "#f2c9a0"
SKINE = "#7a4a20"


def hand(x, y, rot=0, s=1.0):
    fingers = ''.join(f'<rect x="{-24+i*13}" y="-34" width="11" height="34" rx="5" fill="{SKIN}" stroke="{SKINE}" stroke-width="3"/>' for i in range(4))
    return (f'<g transform="translate({x} {y}) rotate({rot}) scale({s})">{fingers}<rect x="-27" y="-12" width="58" height="42" rx="16" fill="{SKIN}" stroke="{SKINE}" stroke-width="3"/>'
            f'<rect x="-40" y="-2" width="24" height="12" rx="6" transform="rotate(-25 -28 4)" fill="{SKIN}" stroke="{SKINE}" stroke-width="3"/></g>')


def skull(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})"><circle cx="0" cy="0" r="24" fill="{PAR}" stroke="#10141c" stroke-width="3"/><rect x="-13" y="14" width="26" height="16" rx="5" fill="{PAR}" stroke="#10141c" stroke-width="3"/>'
            '<ellipse cx="-9" cy="-2" rx="6" ry="7" fill="#10141c"/><ellipse cx="9" cy="-2" rx="6" ry="7" fill="#10141c"/><path d="M-3 10 l3 -5 l3 5Z" fill="#10141c"/><path d="M-6 20 v8 M0 20 v8 M6 20 v8" stroke="#10141c" stroke-width="2"/></g>')


@reg("順")
def _():   # 順手牽羊: 一隻手牽著羊走
    body = ''.join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#f6f2ea" stroke="#8a8a92" stroke-width="3"/>' for x, y, r in [(84, 130, 24), (110, 120, 26), (134, 132, 24), (100, 148, 22), (124, 150, 20), (72, 150, 18)])
    legs = ''.join(f'<rect x="{x}" y="164" width="9" height="36" rx="4" fill="#3a3a44"/>' for x in (76, 94, 118, 136))
    return (legs + body + '<circle cx="158" cy="118" r="20" fill="#3a3a44" stroke="#10141c" stroke-width="3"/><ellipse cx="144" cy="104" rx="9" ry="14" transform="rotate(-30 144 104)" fill="#3a3a44"/><circle cx="164" cy="114" r="3" fill="#fff"/>'
            '<path d="M150 124 Q110 70 62 82" fill="none" stroke="#c9a060" stroke-width="5" stroke-linecap="round" stroke-dasharray="1 0"/>' + hand(50, 100, -70, .8))


@reg("反")
def _():   # 反擊: 攻擊被盾彈回去
    return (shield(82, 132, .78, "#26407a", "#9fc3ff") + arrow(180, 52, 118, 108, PAR, 6, 16)
            + arrow(112, 114, 180, 178, "#ff5a4a", 7, 18) + star4(110, 112, 22, "#ffe27a"))


@reg("南")
def _():   # 南蠻入侵: 大象
    legs = ''.join(f'<rect x="{x}" y="164" width="20" height="46" rx="8" fill="#7a7a86" stroke="#2a2a34" stroke-width="3"/>' for x in (92, 114, 146, 168))
    return (legs + '<ellipse cx="130" cy="138" rx="58" ry="42" fill="#8a8a96" stroke="#2a2a34" stroke-width="4"/><circle cx="64" cy="118" r="30" fill="#8a8a96" stroke="#2a2a34" stroke-width="4"/>'
            '<ellipse cx="86" cy="122" rx="16" ry="26" fill="#6a6a78" stroke="#2a2a34" stroke-width="3"/><path d="M50 138 Q30 170 44 196 Q54 204 58 192" fill="none" stroke="#8a8a96" stroke-width="16" stroke-linecap="round"/>'
            '<path d="M58 134 Q74 156 62 164" fill="none" stroke="#f6ecd0" stroke-width="7" stroke-linecap="round"/><circle cx="62" cy="108" r="4" fill="#10141c"/>'
            '<path d="M104 104 H162 L172 124 H96Z" fill="#c4252a" stroke="#6a1408" stroke-width="3"/><line x1="134" y1="104" x2="134" y2="62" stroke="#c9a060" stroke-width="5"/><polygon points="136,62 168,72 136,84" fill="#e8c872" stroke="#7a5a10" stroke-width="2"/>')


@reg("無懈")
def _():   # 無懈可擊: 毫無破綻的盾,攻擊打不進去
    return (shield(106, 130, 1.0, "#26407a", "#9fc3ff", '<path d="M70 96 H130 M70 126 H130 M100 76 V170" stroke="#9fc3ff" stroke-width="3" opacity=".6"/>')
            + sword(-58, "#e8eef5", "#8aa0b8", cx=44, cy=70, s=.55) + star4(66, 92, 20, "#ffe27a") + '<path d="M36 112 l-14 8 M44 124 l-14 14" ' + st("#ffe27a", 4) + '/>')


@reg("突")
def _():   # 突襲: 騎兵衝鋒
    return ('<path d="M14 100 H70 M8 130 H60 M18 160 H72" stroke="#ffb347" stroke-width="6" stroke-linecap="round" opacity=".6"/>'
            + horse_head(112, 128, .86, "#b0663a") + '<line x1="30" y1="190" x2="176" y2="70" stroke="#c9a060" stroke-width="7" stroke-linecap="round"/><polygon points="188,60 160,62 172,84" fill="#e8eef5" stroke="#6a7a8a" stroke-width="3"/>')


@reg("樂")
def _():   # 樂不思蜀: 蜀旗 + 音樂
    return ('<line x1="62" y1="48" x2="62" y2="214" stroke="#c9a060" stroke-width="7" stroke-linecap="round"/><path d="M66 56 H162 L146 98 L162 140 H66Z" fill="#b5201f" stroke="#e8c872" stroke-width="4" stroke-linejoin="round"/>'
            '<text x="112" y="116" font-size="52" font-weight="900" text-anchor="middle" fill="#ffe27a" font-family="serif">蜀</text>'
            '<path d="M120 196 V162 L148 156 V190" fill="none" stroke="#f6ecd0" stroke-width="5" stroke-linejoin="round"/><ellipse cx="112" cy="198" rx="10" ry="7" fill="#f6ecd0"/><ellipse cx="140" cy="192" rx="10" ry="7" fill="#f6ecd0"/>')


@reg("增")
def _():   # 增兵減灶: 兵越來越多,灶越來越少
    helm = lambda x, s: f'<g transform="translate({x} 86) scale({s})"><path d="M-18 14 A18 18 0 0 1 18 14Z" fill="#8a9aae" stroke="#2a3a4e" stroke-width="3"/><rect x="-22" y="12" width="44" height="7" rx="3" fill="#6a7a8e" stroke="#2a3a4e" stroke-width="2"/><path d="M0 -4 v-12" stroke="#c4252a" stroke-width="5" stroke-linecap="round"/></g>'
    pot = lambda x, s, f: f'<g transform="translate({x} 186) scale({s})" opacity="{f}"><path d="M-22 -14 H22 L16 14 H-16Z" fill="#4a4a54" stroke="#cfd8e8" stroke-width="3"/><path d="M-6 -22 q-6 -8 0 -14 M6 -22 q6 -8 0 -14" stroke="#cfd8e8" stroke-width="3" fill="none"/></g>'
    return (helm(40, .7) + helm(78, .9) + helm(122, 1.1) + helm(166, 1.3)
            + '<path d="M30 130 H170" stroke="#3ab870" stroke-width="5" stroke-dasharray="2 9" stroke-linecap="round"/>' + pot(48, 1.5, 1) + pot(100, 1.1, .7) + pot(152, .75, .45))


@reg("強")
def _():   # 強化: 肌肉手臂
    return ('<defs><radialGradient id="mu" cx="40%" cy="35%"><stop offset="0" stop-color="#ffe0bf"/><stop offset="1" stop-color="#e8a870"/></radialGradient></defs>'
            f'<path d="M60 210 L74 150 Q40 130 62 100 Q92 88 112 116 L128 84 L116 70 Q120 44 144 52 Q166 60 158 86 L148 98 Q150 140 116 160 L106 210Z" fill="url(#mu)" stroke="{SKINE}" stroke-width="4" stroke-linejoin="round"/>'
            '<path d="M76 118 Q96 106 108 128" fill="none" stroke="#c4824a" stroke-width="4"/>' + star4(40, 70, 14, "#ffe27a") + star4(170, 128, 12, "#ffe27a") + star4(30, 150, 9, "#fff6c4"))


@reg("弱")
def _():   # 弱化: 凋萎的花
    return ('<path d="M100 210 C96 170 112 140 104 108 C98 84 122 74 140 86" fill="none" stroke="#7f9f78" stroke-width="8" stroke-linecap="round"/>'
            '<path d="M104 160 C80 150 66 164 60 178 C84 184 98 176 104 160Z" fill="#8fb088" stroke="#3a5a38" stroke-width="3"/>'
            + ''.join(f'<ellipse cx="{x}" cy="{y}" rx="13" ry="22" transform="rotate({r} {x} {y})" fill="#b4a0d8" stroke="#4a3a78" stroke-width="3"/>' for x, y, r in [(148, 108, 130), (160, 90, 160), (150, 72, 200), (132, 70, 235), (126, 92, 270)])
            + '<circle cx="140" cy="90" r="9" fill="#e8d8a0" stroke="#7a6a30" stroke-width="2"/><ellipse cx="70" cy="196" rx="8" ry="12" transform="rotate(30 70 196)" fill="#b4a0d8" opacity=".7"/><ellipse cx="40" cy="214" rx="7" ry="11" transform="rotate(60 40 214)" fill="#b4a0d8" opacity=".5"/>')


@reg("火攻")
def _():   # 火攻: 火箭
    return ('<line x1="30" y1="206" x2="150" y2="84" stroke="#c9a060" stroke-width="7" stroke-linecap="round"/><polygon points="168,66 140,72 160,94" fill="#e8eef5" stroke="#6a7a8a" stroke-width="3"/><polygon points="30,206 18,186 38,192" fill="#ff6b5a"/><polygon points="48,188 36,168 56,174" fill="#ff6b5a"/>'
            + flame(150, 70, .8) + '<circle cx="60" cy="100" r="4" fill="#ffb347"/><circle cx="170" cy="150" r="5" fill="#ff8a1a"/><circle cx="36" cy="140" r="3" fill="#ffe27a"/>')


@reg("借")
def _():   # 借刀殺人: 一手把刀遞給另一手,殺掉第三人
    return (skull(100, 62, .9) + sword(90, "#e8eef5", "#8aa0b8", cx=100, cy=148, s=.62, guard=GOLD) + hand(34, 184, -90, .75) + hand(166, 184, 90, .75)
            + '<path d="M70 108 L100 92 L130 108" fill="none" stroke="#ff5a4a" stroke-width="4" stroke-dasharray="3 7"/>')


@reg("草")
def _():   # 草木皆兵: 草叢裡全是兵
    bush = ''.join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#3a8a40" stroke="#14502c" stroke-width="3"/>' for x, y, r in [(60, 170, 30), (100, 160, 36), (142, 172, 30), (80, 190, 26), (126, 192, 26)])
    helm = '<path d="M-20 16 A20 20 0 0 1 20 16Z" fill="#8a9aae" stroke="#2a3a4e" stroke-width="3"/><rect x="-24" y="14" width="48" height="7" rx="3" fill="#6a7a8e" stroke="#2a3a4e" stroke-width="2"/><path d="M0 -6 v-14" stroke="#c4252a" stroke-width="6" stroke-linecap="round"/>'
    return (f'<g transform="translate(100 118)">{helm}<circle cx="-8" cy="30" r="3" fill="#fff"/><circle cx="8" cy="30" r="3" fill="#fff"/></g>'
            '<line x1="40" y1="170" x2="30" y2="70" stroke="#c9a060" stroke-width="5"/><polygon points="30,58 22,80 38,80" fill="#e8eef5"/><line x1="160" y1="170" x2="170" y2="76" stroke="#c9a060" stroke-width="5"/><polygon points="170,64 162,86 178,86" fill="#e8eef5"/>' + bush)


@reg("發")
def _():   # 發憤圖強: 握緊拳頭
    import math
    rays = ''.join(f'<line x1="100" y1="124" x2="{100+84*math.cos(math.radians(a)):.1f}" y2="{124+84*math.sin(math.radians(a)):.1f}" stroke="#ffd24a" stroke-width="5" stroke-linecap="round" opacity=".8"/>' for a in range(0, 360, 30))
    knuckles = ''.join(f'<rect x="{64+i*18}" y="88" width="18" height="40" rx="9" fill="{SKIN}" stroke="{SKINE}" stroke-width="3"/>' for i in range(4))
    return (rays + '<circle cx="100" cy="124" r="52" fill="#7a1f1f" opacity=".9"/>' + '<rect x="62" y="108" width="78" height="62" rx="20" fill="' + SKIN + '" stroke="' + SKINE + '" stroke-width="3"/>' + knuckles
            + '<path d="M70 132 H138 M76 150 H132" stroke="#c4824a" stroke-width="3"/><rect x="48" y="128" width="40" height="18" rx="9" transform="rotate(-25 68 137)" fill="' + SKIN + '" stroke="' + SKINE + '" stroke-width="3"/><rect x="86" y="170" width="30" height="40" rx="8" fill="#c4252a" stroke="#6a1408" stroke-width="3"/>')


KIND = {}
for n in ("殺", "火", "冰", "雷", "閃", "桃", "酒"):
    KIND[n] = "basic"
for n in ("樂", "草", "閃電", "毒", "兵"):
    KIND[n] = "delay"
for n in ("八卦陣", "仁王盾", "藤甲", "緩衝盾", "雷盾", "火盾", "冰盾"):
    KIND[n] = "armor"
for n in ("+1馬", "-1馬"):
    KIND[n] = "horse"
for n in ("諸葛連弩", "孔雀羽扇", "青龍偃月刀", "寒冰劍", "方天畫戟", "流星錘", "麒麟弓", "青釭劍", "丈八蛇矛", "貫石斧"):
    KIND[n] = "weapon"




# ---------------- 底色風格 (卡面) / 卡背: 古風 (宣紙 / 絹帛 / 竹簡 / 青花 / 玉色 / 朱漆 ...) ----------------
import colorsys
import cardglyph
import re as _re

FONT = "'Noto Serif TC','Songti TC','SimSun','Microsoft JhengHei',serif"
SEAL = {"無懈": "懈", "桃園": "園", "火攻": "攻", "八卦陣": "卦", "仁王盾": "盾", "藤甲": "藤", "緩衝盾": "緩", "雷盾": "雷", "火盾": "火", "冰盾": "冰",
        "+1馬": "守", "-1馬": "攻", "諸葛連弩": "弩", "孔雀羽扇": "扇", "青龍偃月刀": "龍", "寒冰劍": "冰", "方天畫戟": "戟", "流星錘": "錘"}


INKC = "#2a2018"   # 墨
WASH = {"basic": "#c4452f", "trick": "#4f7f96", "delay": "#7a5a96", "weapon": "#6a7078", "armor": "#5b8a6a", "horse": "#a8643a"}   # 朱砂 / 石青 / 紫 / 鐵灰 / 石綠 / 赭石
# paper: 紙色 (上, 下); ink: 墨色; dark: 深色底 (圖示維持亮色); frame: 外框; mist: 遠山 / 薄霧色; extra: 底紋
BGS = {
    "line": {"paper": ("#efe3c2", "#cdb98a"), "ink": INKC, "dark": False, "frame": "#6b3a1e", "mist": "#4a5560", "extra": "paper"},
    "classic": {"paper": ("#efe3c2", "#cdb98a"), "ink": INKC, "dark": False, "frame": "#6b3a1e", "mist": "#4a5560", "extra": "paper"},
    "silk": {"paper": ("#f0d68a", "#c79a44"), "ink": "#3a2410", "dark": False, "frame": "#8a2a1a", "mist": "#6a4a1a", "extra": "silk"},
    "bamboo": {"paper": ("#d9c58a", "#a98f55"), "ink": "#2a2010", "dark": False, "frame": "#4a3a18", "mist": "#4a3a18", "extra": "bamboo"},
    "qinghua": {"paper": ("#f4f7fa", "#c9d6e4"), "ink": "#1f3f7a", "dark": False, "frame": "#1f3f7a", "mist": "#2a4f8a", "extra": "paper"},
    "jade": {"paper": ("#d7e8d4", "#9bbf9f"), "ink": "#1f3a2a", "dark": False, "frame": "#2f5a44", "mist": "#2f5a44", "extra": "paper"},
    "vermilion": {"paper": ("#8a1f1a", "#3a0a0a"), "ink": "#ffe2a0", "dark": True, "frame": "#e8c872", "mist": "#000000", "extra": "cloud"},
    "ink": {"paper": ("#3c3a36", "#0e0d0c"), "ink": "#e8e2d0", "dark": True, "frame": "#cfc6a8", "mist": "#000000", "extra": "paper"},
    "ocean": {"paper": ("#1f5a8a", "#04152a"), "ink": "#d4f2ff", "dark": True, "frame": "#9fe8ff", "mist": "#000000", "extra": "wave"},
    "sakura": {"paper": ("#f9e1ea", "#e6b2c6"), "ink": "#4a1a30", "dark": False, "frame": "#8a2a4a", "mist": "#b04a70", "extra": "petal"},
    "night": {"paper": ("#2e2468", "#0a0620"), "ink": "#e4dcff", "dark": True, "frame": "#c9b8ff", "mist": "#000000", "extra": "stars"},
    "neon": {"paper": ("#14143a", "#04040c"), "ink": "#8ff8ff", "dark": True, "frame": "#ff4fd8", "mist": "#000000", "extra": "scan"},
    "pixel": {"paper": ("#2a3a7a", "#12183a"), "ink": "#fff1e8", "dark": True, "frame": "#ffa300", "mist": "#000000", "extra": "none", "pixel": ("#2a3a7a", "#222f6a", "#ff77a8", "#ffec27")},
    "pixel_gb": {"paper": ("#8bac0f", "#306230"), "ink": "#0f380f", "dark": False, "frame": "#0f380f", "mist": "#0f380f", "extra": "none", "pixel": ("#9bbc0f", "#8bac0f", "#0f380f", "#306230")},
    "gold": {"paper": ("#5a3e10", "#1c1204"), "ink": "#ffe27a", "dark": True, "frame": "#ffd24a", "mist": "#000000", "extra": "cloud"},
}


def _hx(c):
    c = c.lstrip("#")
    return tuple(int(c[k:k + 2], 16) / 255 for k in (0, 2, 4))


def _col(h, l, sat):
    r, g, b = colorsys.hls_to_rgb(h, l, sat)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def ancient(body, dark, ink):
    """把圖示的顏色換成古風用色: 降低飽和 (礦物顏料感)、淺色描邊改成墨線;深色底則保留亮色。"""
    def stroke_fix(m):
        r, g, b = _hx(m.group(1))
        h, l, sat = colorsys.rgb_to_hls(r, g, b)
        if not dark and l > .66:
            return 'stroke="%s"' % ink
        return 'stroke="%s"' % _col(h, l, sat * .7)

    def fill_fix(m):
        r, g, b = _hx(m.group(2))
        h, l, sat = colorsys.rgb_to_hls(r, g, b)
        if l > .9 and sat < .3:
            return '%s="%s"' % (m.group(1), "#f3e8c8" if not dark else "#e8dcc0")
        if dark:
            return '%s="%s"' % (m.group(1), _col(h, l, sat * .8))
        return '%s="%s"' % (m.group(1), _col(h, min(l, .8) * .94, sat * .66))
    body = _re.sub(r'stroke="(#[0-9a-fA-F]{6})"', stroke_fix, body)
    body = _re.sub(r'(fill|stop-color|flood-color)="(#[0-9a-fA-F]{6})"', fill_fix, body)
    return body


EMBER = {"basic": "#ff7a2a", "trick": "#7fd0ff", "delay": "#c79bff", "weapon": "#ffd27a", "armor": "#8fe0a8", "horse": "#ffb070"}


def _rng(seed):
    x = seed or 1
    while True:
        x = (x * 1103515245 + 12345) & 0x7fffffff
        yield x / 0x7fffffff


def _blob(cx, cy, r, rnd, n=11):
    pts = [(cx + r * (.62 + .5 * next(rnd)) * math.cos(2 * math.pi * k / n), cy + r * (.62 + .5 * next(rnd)) * math.sin(2 * math.pi * k / n)) for k in range(n)]
    mid = [((pts[k][0] + pts[(k + 1) % n][0]) / 2, (pts[k][1] + pts[(k + 1) % n][1]) / 2) for k in range(n)]
    d = f'M{mid[-1][0]:.1f} {mid[-1][1]:.1f}'
    for k in range(n):
        d += f' Q{pts[k][0]:.1f} {pts[k][1]:.1f} {mid[k][0]:.1f} {mid[k][1]:.1f}'
    return d + 'Z'


def _scroll(x, y, n, vertical=False, c="#e8c872"):
    d = ''.join(f'M{x} {y + k * 14} c-6 3 -6 9 0 9 c4 0 4 -5 0 -5' if vertical else f'M{x + k * 14} {y} c3 -6 9 -6 9 0 c0 4 -5 4 -5 0' for k in range(n))
    return f'<path d="{d}" fill="none" stroke="{c}" stroke-opacity=".5" stroke-width="1.3" stroke-linecap="round"/>'


def _pixel_glyph(ch, x0=142, y0=226, cell=3, color="#ffffff"):
    """像素風印章字: 12x12 點陣 (cardglyph.GLYPH),每列把連續的點合成一個長方形。沒有這個字就用一般字體。"""
    rows = cardglyph.GLYPH.get(ch)
    if not rows:
        return f'<text x="160" y="258" font-size="{32 if len(ch) == 1 else 22 if len(ch) == 2 else 15}" font-weight="900" text-anchor="middle" fill="{color}" font-family="{FONT}" shape-rendering="auto">{ch}</text>'
    out = []
    for r, bits in enumerate(rows):
        c = 0
        while c < 12:
            if bits >> (11 - c) & 1:
                k = c
                while k < 12 and bits >> (11 - k) & 1:
                    k += 1
                out.append(f'<rect x="{x0 + c * cell}" y="{y0 + r * cell}" width="{(k - c) * cell}" height="{cell}"/>')
                c = k
            else:
                c += 1
    return f'<g fill="{color}" shape-rendering="crispEdges">' + ''.join(out) + '</g>'


def _wrap_pixel(name, body, kind, P, seal, small=False, equip=False, land=False):
    """像素風卡面: 圖示用 SVG 濾鏡「降解析度」成方塊像素、階梯狀像素邊框、棋盤格底、方形像素印章。"""
    W, H = (286, 200) if land else (200, 286)
    c1, c2, hi, fr = P["pixel"]
    dark, ink = P["dark"], P["ink"]
    body = ancient(body, dark, ink)
    C = 6   # 一格像素的大小 (卡面座標)
    glyph = _pixel_glyph(seal, W - 58, H - 60)
    chk = ''.join(f'<rect x="{x}" y="{y}" width="10" height="10" fill="{c2}"/>' for y in range(14, H - 14, 10) for x in range(14 + (10 if (y // 10) % 2 else 0), W - 14, 20))
    notch = ''.join(f'<rect x="{x}" y="{y}" width="8" height="8" fill="#0b0b14"/>' for x, y in ((0, 0), (W - 8, 0), (0, H - 8), (W - 8, H - 8)))
    steps = ''.join(f'<rect x="{x}" y="{y}" width="4" height="4" fill="{fr}"/>' for x, y in ((8, 8), (W - 12, 8), (8, H - 12), (W - 12, H - 12)))
    pixf = "" if small else ' filter="url(#pix)"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" shape-rendering="crispEdges">'
            f'<defs><filter id="pix" filterUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}" color-interpolation-filters="sRGB"><feFlood x="{C / 2 - 1}" y="{C / 2 - 1}" width="2" height="2" flood-color="#000"/><feComposite width="{C}" height="{C}"/><feTile result="g"/><feComposite in="SourceGraphic" in2="g" operator="in"/><feMorphology operator="dilate" radius="{C / 2}"/></filter>'
            f'<filter id="outline" x="-12%" y="-12%" width="124%" height="124%"><feMorphology in="SourceAlpha" operator="dilate" radius="2.4" result="d"/><feFlood flood-color="#0b0b14"/><feComposite in2="d" operator="in" result="o"/><feMerge><feMergeNode in="o"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
            f'<rect width="{W}" height="{H}" fill="#0b0b14"/>{notch}'
            f'<rect x="4" y="4" width="{W - 8}" height="{H - 8}" fill="{fr}"/><rect x="8" y="8" width="{W - 16}" height="{H - 16}" fill="#0b0b14"/>'
            f'<clipPath id="pn"><rect x="12" y="12" width="{W - 24}" height="{H - 24}"/></clipPath><rect x="12" y="12" width="{W - 24}" height="{H - 24}" fill="{c1}"/><g clip-path="url(#pn)">{chk}</g>{steps}'
            f'<g{pixf}><g transform="translate({W / 2} {H / 2 - 5}) scale({.72 if land else .8}) translate(-100 -143)"><g filter="url(#outline)">{body}</g></g></g>'
            f'<rect x="12" y="12" width="{W - 24}" height="4" fill="#fff" fill-opacity=".18"/>'
            + ('' if equip else f'<g><rect x="{W - 68}" y="{H - 70}" width="56" height="56" fill="#0b0b14"/><rect x="{W - 64}" y="{H - 66}" width="48" height="48" fill="#d8262c"/>' + glyph + '</g>') + '</svg>')


SEAL_JA = str.maketrans({"樂": "楽", "鐵": "鉄", "龍": "竜", "萬": "万", "聲": "声", "增": "増", "發": "発", "轉": "転", "雷": "雷", "釭": "釭", "麒": "麒"})
ROLE_SEAL = {"zh": {}, "ja": {"主公": "君", "忠臣": "家", "反賊": "逆", "內奸": "内"}, "en": {"主公": "EMP", "忠臣": "LOY", "反賊": "REB", "內奸": "SPY"}}
EN_SEAL = {   # 英文介面: 印章字改成英文牌名前三個字母 (撞名的另外指定)
    "殺": "SLA", "火": "FIR", "冰": "ICE", "雷": "THU", "閃": "DOD", "桃": "PEA", "酒": "WIN", "順": "STE", "過": "DIS", "反": "CNT", "調": "DIV", "占": "DVN", "南": "BAR", "萬": "ARR",
    "無": "WFL", "無懈": "NUL", "轉": "SWP", "突": "RAI", "桃園": "GAR", "樂": "CMP", "聲": "FNT", "增": "RNF", "決": "DUE", "強": "EMP", "弱": "WKN", "火攻": "ATK", "借": "BOR",
    "飢": "FAM", "草": "SCA", "閃電": "LTN", "降雷": "CAL", "發": "RSV", "毒": "PSN", "兵": "STV", "偽": "DSG", "出": "SUR", "拋": "BRK", "未": "PLN", "笑": "DGR", "鴻": "HGM",
    "隔": "WCH", "孤": "ALL", "投": "RTN", "五": "HAR", "鐵": "CHN", "八卦陣": "8TG", "仁王盾": "REN", "藤甲": "RAT", "緩衝盾": "BUF", "雷盾": "TSH", "火盾": "FSH", "冰盾": "ISH",
    "+1馬": "+1", "-1馬": "-1", "諸葛連弩": "ZHU", "孔雀羽扇": "FAN", "青龍偃月刀": "GDB", "寒冰劍": "FRS", "方天畫戟": "SKY", "流星錘": "MET", "麒麟弓": "KIR", "青釭劍": "BLU",
    "丈八蛇矛": "SER", "貫石斧": "AXE"}


def seal_for(name, lg=""):
    """印章字: 依介面語言換 (zh 原樣、ja 換成日文字形與日文身分名、en 用英文牌名縮寫)。"""
    z = SEAL.get(name, name[0])
    if lg == "en":
        return ROLE_SEAL["en"].get(name) or EN_SEAL.get(name) or name[:3].upper()
    if lg == "ja":
        return ROLE_SEAL["ja"].get(name) or z.translate(SEAL_JA)
    return z


def wrap(name, body, kind, bg="classic", small=False, land=False, lg="", use_ink=True):
    """卡面統一概念: 深色浮雕金屬邊框 + 宣紙內框 + 水墨暈染 / 飛濺 + 火星 + 墨線圖示 + 朱砂印章 (印章是這張牌的關鍵字)。"""
    W, H = (286, 200) if land else (200, 286)   # 延時錦囊是橫的
    P = BGS.get(bg) or BGS["classic"]
    top, bot = P["paper"]
    dark, ink, fr, mist = P["dark"], P["ink"], P["frame"], P["mist"]
    seal = seal_for(name, lg)
    equip = kind in ("weapon", "armor", "horse")   # 武器 / 防具 / 坐騎: 右下角不放印章 (武器改寫攻擊範圍,見前端)
    if P.get("pixel"):
        out = _wrap_pixel(name, body, kind, P, seal, small, equip, land)
        return _ink_pixel(out, name, P, land) if use_ink else out
    wash = WASH.get(kind, "#4f7f96")
    ember = EMBER.get(kind, "#ff9a4a")
    body = ancient(body, dark, ink)
    rnd = _rng(sum(ord(ch) * (k + 3) for k, ch in enumerate(name)) + 7)
    extra = ''
    if P["extra"] == "silk":   # 絹帛: 細織紋
        extra = ''.join(f'<line x1="16" y1="{y}" x2="{W - 16}" y2="{y}" stroke="#7a5a1a" stroke-opacity=".12" stroke-width=".8"/>' for y in range(18, H, 4)) + ''.join(f'<line x1="{x}" y1="16" x2="{x}" y2="{H - 16}" stroke="#7a5a1a" stroke-opacity=".1" stroke-width=".8"/>' for x in range(20, W, 4))
    elif P["extra"] == "bamboo":   # 竹簡: 一條一條的竹片
        extra = ''.join(f'<rect x="{x}" y="16" width="1.6" height="254" fill="#4a3a18" fill-opacity=".35"/><rect x="{x + 9}" y="16" width=".8" height="254" fill="#fff" fill-opacity=".12"/>' for x in range(26, W, 24))
    elif P["extra"] == "wave":   # 海浪紋
        extra = ''.join(f'<path d="M{x} {y} q7 -9 14 0 t14 0 t14 0" fill="none" stroke="{ink}" stroke-opacity=".14" stroke-width="1.4"/>' for y in range(34, H, 18) for x in range(14 + (14 if (y // 18) % 2 else 0) - 14, W - 24, 42))
    elif P["extra"] == "petal":   # 飄落的櫻花瓣
        extra = ''.join(f'<ellipse cx="{(k * 47) % (W - 50) + 24}" cy="{(k * 83) % (H - 50) + 26}" rx="4" ry="2.4" transform="rotate({(k * 37) % 180} {(k * 47) % (W - 50) + 24} {(k * 83) % (H - 50) + 26})" fill="#d86a94" fill-opacity=".45"/>' for k in range(18))
    elif P["extra"] == "stars":   # 星點
        extra = ''.join(f'<circle cx="{(k * 53) % (W - 50) + 24}" cy="{(k * 97) % (H - 50) + 26}" r="{1 + k % 2 * .6}" fill="#fff" fill-opacity=".7"/>' for k in range(30))
    elif P["extra"] == "scan":   # 掃描線
        extra = ''.join(f'<line x1="16" y1="{y}" x2="{W - 16}" y2="{y}" stroke="#3ff0ff" stroke-opacity=".1"/>' for y in range(22, H, 12))
    elif P["extra"] == "cloud":   # 祥雲暗紋
        extra = ''.join(f'<path d="M{x} {y} q6 -9 14 -3 q8 -6 12 3 q-6 4 -12 2 q-6 4 -14 -2z" fill="none" stroke="{ink}" stroke-opacity=".12" stroke-width="1.4"/>' for y in range(34, H, 36) for x in range(22 + (18 if (y // 36) % 2 else 0), W - 24, 40))
    inkc = "#000" if not dark else "#000"
    mt = f"translate(16 {H - 286}) scale({(W - 32) / 168:.4f} 1) translate(-16 0)" if land else ""
    blobs = ''.join(f'<path d="{_blob(W / 2 + (next(rnd) - .5) * 40, H / 2 - 5 + (next(rnd) - .5) * 40, 52 + 14 * next(rnd), rnd)}" fill="{inkc}" fill-opacity="{.16 + .2 * next(rnd):.2f}"/>' for _ in range(5))
    spat = ''.join(f'<circle cx="{W / 2 + math.cos(a) * rr:.1f}" cy="{H / 2 - 5 + math.sin(a) * rr:.1f}" r="{.7 + 2.4 * next(rnd) ** 2:.1f}" fill="{inkc}" fill-opacity=".6"/>'
                   for a, rr in ((next(rnd) * 6.283, 46 + 48 * next(rnd)) for _ in range(34)))
    embers = ''.join(f'<circle cx="{W / 2 + (next(rnd) - .5) * W * .5:.1f}" cy="{H / 2 + 7 + (next(rnd) - .5) * H * .42:.1f}" r="{.8 + 1.4 * next(rnd):.1f}" fill="{ember}" fill-opacity="{.5 + .5 * next(rnd):.2f}"/>' for _ in range(24))
    studs = ''.join(f'<circle cx="{x}" cy="{y}" r="2.6" fill="url(#stud)" stroke="#0a0908" stroke-width=".6"/>' for x, y in ((9, 9), (W - 9, 9), (9, H - 9), (W - 9, H - 9), (9, H // 2), (W - 9, H // 2), (W // 2, 8)))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bot}"/></linearGradient>'
            f'<linearGradient id="mt" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4a4640"/><stop offset=".5" stop-color="#23211f"/><stop offset="1" stop-color="#3a3733"/></linearGradient>'
            f'<radialGradient id="stud" cx="35%" cy="30%" r="70%"><stop offset="0" stop-color="#d8b878"/><stop offset="1" stop-color="#4a3a1c"/></radialGradient>'
            f'<radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="{ember}" stop-opacity="{.5 if not dark else .35}"/><stop offset="1" stop-color="{ember}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="vg" cx="50%" cy="48%" r="75%"><stop offset=".62" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#3a2410" stop-opacity="{.5 if not dark else .45}"/></radialGradient>'
            f'<filter id="paper" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".75" numOctaves="3" seed="5" result="n"/><feColorMatrix in="n" values="0 0 0 0 .35  0 0 0 0 .25  0 0 0 0 .12  0 0 0 .5 -.12"/></filter>'
            f'<filter id="rough" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".05" numOctaves="2" seed="11" result="t"/><feDisplacementMap in="SourceGraphic" in2="t" scale="3.2" xChannelSelector="R" yChannelSelector="G"/></filter>'
            f'<filter id="inkr" x="-20%" y="-20%" width="140%" height="140%"><feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="3" seed="3" result="t"/><feDisplacementMap in="SourceGraphic" in2="t" scale="22" xChannelSelector="R" yChannelSelector="G"/><feGaussianBlur stdDeviation="1.4"/></filter>'
            f'<filter id="outline" x="-12%" y="-12%" width="124%" height="124%"><feMorphology in="SourceAlpha" operator="dilate" radius="2.2" result="d"/><feFlood flood-color="{ink}" flood-opacity=".92"/><feComposite in2="d" operator="in" result="o"/><feMerge><feMergeNode in="o"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
            f'<clipPath id="panel"><rect x="16" y="16" width="{W - 32}" height="{H - 32}"/></clipPath></defs>'
            # 內框: 宣紙
            f'<rect width="{W}" height="{H}" fill="#1c1b19"/><g clip-path="url(#panel)"><rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" filter="url(#paper)" opacity=".55"/>{extra}'
            f'<circle cx="{W / 2}" cy="{H / 2 - 5}" r="{76 if land else 82}" fill="url(#glow)"/>'
            f'<g filter="url(#inkr)">{blobs}</g>{spat}'
            f'<g transform="{mt}"><path d="M16 240 Q36 214 54 232 Q74 202 98 232 Q118 210 140 232 Q164 206 184 228 V270 H16Z" fill="{mist}" fill-opacity=".18"/></g>'
            f'<g transform="translate({W / 2} {H / 2 - 3}) scale({.78 if land else .86}) translate(-100 -143)"><g filter="url(#outline)"><g filter="url(#rough)">{body}</g></g></g>'
            f'{embers}<rect width="{W}" height="{H}" fill="url(#vg)"/></g>'
            f'<rect x="21" y="21" width="{W - 42}" height="{H - 42}" fill="none" stroke="{fr}" stroke-opacity=".55" stroke-width="1"/>'
            # 外框: 深色浮雕金屬
            f'<path fill-rule="evenodd" fill="url(#mt)" d="M6 0 H{W - 6} Q{W} 0 {W} 6 V{H - 6} Q{W} {H} {W - 6} {H} H6 Q0 {H} 0 {H - 6} V6 Q0 0 6 0Z M16 16 V{H - 16} H{W - 16} V16Z"/>'
            f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="5" fill="none" stroke="{fr}" stroke-opacity=".6" stroke-width="1.2"/>'
            f'<rect x="15" y="15" width="{W - 30}" height="{H - 30}" fill="none" stroke="#0a0908" stroke-width="2"/><rect x="16.5" y="16.5" width="{W - 33}" height="{H - 33}" fill="none" stroke="{fr}" stroke-opacity=".5" stroke-width=".8"/>'
            + _scroll(24, 9, (W - 32) // 14, False, fr) + _scroll(24, H - 5, (W - 32) // 14, False, fr) + _scroll(9, 30, (H - 60) // 14, True, fr) + _scroll(W - 9, 30, (H - 60) // 14, True, fr)
            + f'<path d="M{W / 2 - 8} 9 L{W / 2} 3 L{W / 2 + 8} 9 L{W / 2} 15Z" fill="url(#stud)" stroke="#0a0908" stroke-width=".7"/>' + studs
            # 印章 (壓在邊框上)
            + ('' if equip else f'<g><rect x="{W - 57}" y="{H - 62}" width="46" height="46" rx="4" fill="#3a1412" stroke="#0a0908" stroke-width="2"/><rect x="{W - 54}" y="{H - 59}" width="40" height="40" rx="3" fill="#b3232a" stroke="#e8c872" stroke-opacity=".6" stroke-width="1.2"/>'
              f'<rect x="{W - 50}" y="{H - 55}" width="32" height="32" fill="none" stroke="#ffd9d0" stroke-opacity=".6" stroke-width="1"/>'
              f'<text x="{W - 34}" y="{H - 29}" font-size="{28 if len(seal) == 1 else 20 if len(seal) == 2 else 14}" font-weight="900" text-anchor="middle" fill="#ffe9e0" font-family="{FONT}">{seal}</text></g>')
            + '</svg>')


def _bk_star(c):
    return f'<path d="M100 111 L106 137 L132 143 L106 149 L100 175 L94 149 L68 143 L94 137Z" fill="{c}"/>'


def _bk_wave(c):
    return ''.join(f'<path d="M62 {y} q9 -10 19 0 t19 0 t19 0 t19 0" fill="none" stroke="{c}" stroke-width="3"/>' for y in (126, 140, 154))


def _bk_coin(c):
    return f'<circle cx="100" cy="143" r="20" fill="none" stroke="{c}" stroke-width="4"/><rect x="90" y="133" width="20" height="20" fill="none" stroke="{c}" stroke-width="3"/>'


def _bk_taiji(c):
    return (f'<circle cx="100" cy="143" r="22" fill="{c}"/><path d="M100 121 A11 11 0 0 1 100 143 A11 11 0 0 0 100 165 A22 22 0 0 1 100 121Z" fill="#0c0c0e"/>'
            f'<circle cx="100" cy="132" r="3.5" fill="{c}"/><circle cx="100" cy="154" r="3.5" fill="#0c0c0e"/>')


def _bk_flower(c):
    out = ''.join(f'<ellipse cx="100" cy="124" rx="9" ry="16" transform="rotate({a} 100 143)" fill="{c}"/>' for a in range(0, 360, 72))
    return out + '<circle cx="100" cy="143" r="6" fill="#fff6c4"/>'


def _bk_rings(c):
    return ''.join(f'<circle cx="100" cy="143" r="{r}" fill="none" stroke="{c}" stroke-width="3"/>' for r in (10, 20, 30)) + f'<circle cx="100" cy="143" r="4" fill="{c}"/>'


BACKS = {   # id: (背景亮, 背景暗, 線條色, 中央圖示, 底紋)
    "classic": ("#5a1a1a", "#1c0608", "#e8c872", _bk_star, "diamond"),
    "azure": ("#1d4a8a", "#06142c", "#bfe9ff", _bk_wave, "diamond"),
    "jade": ("#1f6a52", "#06201a", "#ffe27a", _bk_coin, "dots"),
    "ink": ("#34343a", "#0a0a0c", "#e8e2d0", _bk_taiji, "dots"),
    "sakura": ("#7a2a4a", "#2a0c1c", "#ffc2dc", _bk_flower, "dots"),
    "gold": ("#6a4a14", "#241604", "#ffe27a", _bk_rings, "diamond"),
    "rn_void": ("#2a1050", "#07030f", "#c28bff", _bk_star, "dots"),
}


# 像素主題的配色 (亮, 暗): 每種像素主題各有一款像素卡面 (id 跟主題 id 相同)
PIXEL_PAL = {"pixel": ("#ff77a8", "#1d2b53"), "pixel_gb": ("#9bbc0f", "#0f380f"), "pixel_blue": ("#29adff", "#0b1a3a"), "pixel_amber": ("#ffa300", "#2e1706"),
             "pixel_violet": ("#83769c", "#1f1633"), "pixel_red": ("#ff004d", "#2a0a14"), "pixel_bw": ("#c2c3c7", "#1a1a1a")}


def _mix(c1, c2, t):
    a, b = _hx(c1), _hx(c2)
    return "#%02x%02x%02x" % tuple(round((x + (y - x) * t) * 255) for x, y in zip(a, b))


for _id, (_a, _b) in PIXEL_PAL.items():
    if _id not in BGS:
        BGS[_id] = {"paper": (_mix(_b, _a, .2), _b), "ink": "#fff1e8", "dark": True, "frame": _a, "mist": "#000000", "extra": "none", "pixel": (_mix(_b, _a, .2), _mix(_b, _a, .1), _a, _a)}


def back(bk="classic"):
    c1, c2, ln, emb, pat = BACKS.get(bk) or BACKS["classic"]
    if pat == "diamond":
        p = ''.join(f'<path d="M{x} {y} l12 12 l-12 12 l-12 -12z" fill="none" stroke="{ln}" stroke-opacity=".35" stroke-width="2"/>' for y in range(18, 280, 24) for x in range(12 + (12 if (y // 24) % 2 else 0), 200, 24))
    else:
        p = ''.join(f'<circle cx="{x}" cy="{y}" r="3" fill="{ln}" fill-opacity=".3"/>' for y in range(18, 280, 18) for x in range(14 + (9 if (y // 18) % 2 else 0), 200, 18))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 286" width="200" height="286"><defs><radialGradient id="bg" cx="50%" cy="45%" r="70%"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></radialGradient></defs>'
            f'<rect width="200" height="286" fill="url(#bg)"/>{p}<circle cx="100" cy="143" r="46" fill="{c2}" stroke="{ln}" stroke-width="4"/><circle cx="100" cy="143" r="36" fill="none" stroke="{ln}" stroke-opacity=".6" stroke-width="2"/>'
            f'{emb(ln)}<rect x="5" y="5" width="190" height="276" rx="14" fill="none" stroke="{ln}" stroke-width="4"/><rect x="12" y="12" width="176" height="262" rx="9" fill="none" stroke="{ln}" stroke-opacity=".55" stroke-width="1.5"/></svg>')


_cache = {}


def svg(name, bg="classic", small=False, lg="", art=""):
    """某張牌的卡面 SVG;沒有這張牌回傳 None。bg = 卡面風格 id;small = 很小的縮圖 (像素風不做降解析度,不然太小會看不到圖)。"""
    if name not in E:
        return None
    lg = lg if lg in ("en", "ja") else ""
    ink = art != "svg"   # art=svg: 玩家選用手繪向量圖 (舊版程式畫的卡面)
    key = (name, bg if bg in BGS else "classic", bool(small), lg, ink)
    if key not in _cache:
        out = wrap(name, E[name][0](), KIND.get(name, "trick"), key[1], small, KIND.get(name) == "delay", lg, use_ink=ink)
        if ink:   #所有卡面風格都用同一套水墨圖 (只有邊框 / 色調不同)
            out = _ink_overlay(out, name, bool(small), KIND.get(name) == "delay")
            out = _ink_frame(out, key[1], KIND.get(name) == "delay", name)
        _cache[key] = out
    return _cache[key]


def _ink_overlay(svg_text, name, small, land, sub="cards"):
    """預設卡面 = 水墨卡圖: 把內框 (宣紙 + 程式畫的圖示) 換成 ComfyUI 生成的水墨圖,外框 / 印章 / 角標照舊。沒有這張圖就維持程式畫的。"""
    fn = os.path.join(HERE, "web", "ink", sub, ("s_" if small else "") + name + ".jpg")
    if not os.path.isfile(fn):
        return svg_text
    W, H = (286, 200) if land else (200, 286)
    a = svg_text.find('<g clip-path="url(#panel)">')
    end = f'<rect width="{W}" height="{H}" fill="url(#vg)"/></g>'
    b = svg_text.find(end, a)
    if a < 0 or b < 0:
        return svg_text
    uri = _ink_uri(fn)
    panel = (f'<g clip-path="url(#panel)"><image href="{uri}" x="16" y="16" width="{W - 32}" height="{H - 32}" preserveAspectRatio="xMidYMid slice"/>'
             f'<rect width="{W}" height="{H}" fill="url(#vg)" opacity=".55"/></g>')
    return svg_text[:a] + panel + svg_text[b + len(end):]


def _ink_frame(svg_text, bg, land, name):
    """有 SDXL 邊框的卡面風格 (絹帛 / 竹簡 / 青花 …): 邊框圖當整張卡的底,拿掉程式畫的金屬邊框 (印章保留),中間仍是水墨圖。"""
    fn = os.path.join(HERE, "web", "ink", "frames", bg + ".jpg")
    if not os.path.isfile(fn) or "<image" not in svg_text:
        return svg_text
    W, H = (286, 200) if land else (200, 286)
    a = svg_text.find('<g clip-path="url(#panel)">')
    cut = svg_text.find(f'<rect x="21" y="21" width="{W - 42}"', a)
    seal = svg_text.find(f'<g><rect x="{W - 57}" y="{H - 62}"', cut)
    if a < 0 or cut < 0:
        return svg_text
    end = seal if seal > 0 else svg_text.rfind("</svg>")
    uri = _ink_uri(fn)
    if land:   # 橫的牌 (延時錦囊): 邊框圖轉 90 度
        fr = f'<image href="{uri}" width="{H}" height="{W}" transform="translate(0 {H}) rotate(-90)" preserveAspectRatio="none"/>'
    else:
        fr = f'<image href="{uri}" width="{W}" height="{H}" preserveAspectRatio="none"/>'
    win = (f'<rect x="15" y="15" width="{W - 30}" height="{H - 30}" fill="none" stroke="#1a1612" stroke-width="3"/>'
           f'<rect x="16.5" y="16.5" width="{W - 33}" height="{H - 33}" fill="none" stroke="#f1e7d0" stroke-opacity=".7" stroke-width=".8"/>')
    return svg_text[:a] + fr + svg_text[a:cut] + win + svg_text[end:]


def _ink_pixel(svg_text, name, P, land):
    """像素風卡面: 內框放同一張水墨圖 (外框 / 印章維持像素風)。沒圖就維持原本的像素圖示。"""
    fn = os.path.join(HERE, "web", "ink", "cards", name + ".jpg")
    if not os.path.isfile(fn):
        fn = os.path.join(HERE, "web", "ink", "roles", name + ".jpg")
    if not os.path.isfile(fn):
        return svg_text
    W, H = (286, 200) if land else (200, 286)
    a = svg_text.find('<g filter="url(#pix)"><g transform="translate(')
    if a < 0:
        a = svg_text.find('<g><g transform="translate(')
    end = f'<rect x="12" y="12" width="{W - 24}" height="4" fill="#fff" fill-opacity=".18"/>'
    b2 = svg_text.find(end)
    if a < 0 or b2 < 0:
        return svg_text
    img = f'<image href="{_ink_uri(fn)}" x="12" y="12" width="{W - 24}" height="{H - 24}" preserveAspectRatio="xMidYMid slice"/>'
    return svg_text[:a] + img + svg_text[b2:]


_uri_cache = {}


def _ink_uri(fn):
    if fn not in _uri_cache:
        import base64
        _uri_cache[fn] = "data:image/jpeg;base64," + base64.b64encode(open(fn, "rb").read()).decode()
    return _uri_cache[fn]


def svg_back(bk="classic"):
    key = ("_back", bk if bk in BACKS else "classic")
    if key not in _cache:
        _cache[key] = back(key[1])
    return _cache[key]


# ---------------- 身分牌 (教學用): 主公 / 忠臣 / 反賊 / 內奸,跟卡牌同一套古風畫法 ----------------
def _role_crown():
    return ('<path d="M52 172 L44 104 L78 134 L100 90 L122 134 L156 104 L148 172Z" fill="#e8c35a" stroke="#6a4a10" stroke-width="5" stroke-linejoin="round"/>'
            '<rect x="50" y="172" width="100" height="18" rx="4" fill="#c99a2a" stroke="#6a4a10" stroke-width="5"/>'
            + ''.join(f'<circle cx="{x}" cy="{y}" r="8" fill="#d6452a" stroke="#6a1a10" stroke-width="3"/>' for x, y in ((44, 104), (100, 90), (156, 104)))
            + '<circle cx="100" cy="150" r="9" fill="#2a8a8a" stroke="#0a3a3a" stroke-width="3"/>')


def _role_shield():
    return ('<path d="M100 78 L152 98 V152 Q152 194 100 218 Q48 194 48 152 V98Z" fill="#d9b34a" stroke="#6a4a10" stroke-width="5" stroke-linejoin="round"/>'
            '<path d="M100 78 L152 98 V152 Q152 194 100 218Z" fill="#b8902a" fill-opacity=".5"/>'
            '<path d="M100 102 V204 M62 140 H138" stroke="#6a4a10" stroke-width="7" stroke-linecap="round"/><circle cx="100" cy="140" r="12" fill="#d6452a" stroke="#6a1a10" stroke-width="3"/>')


def _role_flag():
    return ('<line x1="66" y1="78" x2="66" y2="226" stroke="#8a5a2a" stroke-width="8" stroke-linecap="round"/>'
            '<path d="M70 86 L154 104 L128 128 L158 150 L70 146Z" fill="#3aa86a" stroke="#14502a" stroke-width="5" stroke-linejoin="round"/>'
            '<path d="M84 104 L128 112 M84 124 L120 130" stroke="#14502a" stroke-width="3.5" stroke-linecap="round"/>'
            '<circle cx="66" cy="76" r="8" fill="#e8c35a" stroke="#6a4a10" stroke-width="3"/>')


def _role_eye():
    return ('<path d="M42 143 Q100 84 158 143 Q100 202 42 143Z" fill="#f6ecd0" stroke="#1a2a4a" stroke-width="5" stroke-linejoin="round"/>'
            '<circle cx="100" cy="143" r="26" fill="#2a5aa8" stroke="#10244a" stroke-width="4"/><circle cx="100" cy="143" r="11" fill="#10142a"/><circle cx="108" cy="134" r="5" fill="#fff"/>'
            '<path d="M60 104 L72 118 M100 86 V104 M140 104 L128 118" stroke="#1a2a4a" stroke-width="4" stroke-linecap="round"/>')


ROLE = {"主公": (_role_crown, "basic"), "忠臣": (_role_shield, "basic"), "反賊": (_role_flag, "basic"), "內奸": (_role_eye, "trick")}
SEAL.update({"主公": "主", "忠臣": "忠", "反賊": "反", "內奸": "奸"})


def svg_role(name, bg="classic", lg="", art=""):
    if name not in ROLE:
        return None
    lg = lg if lg in ("en", "ja") else ""
    ink = art != "svg"
    key = ("_role", name, bg if bg in BGS else "classic", lg, ink)
    if key not in _cache:
        fn, kind = ROLE[name]
        out = wrap(name, fn(), kind, key[2], lg=lg, use_ink=ink)
        if ink:
            out = _ink_overlay(out, name, False, False, "roles")
            out = _ink_frame(out, key[2], False, name)
        _cache[key] = out
    return _cache[key]


import hashlib as _hl
try:
    VER = _hl.md5(open(__file__, "rb").read()).hexdigest()[:8]
except OSError:   # 打包成 exe 後原始碼不在磁碟上: 用版本號當版本碼
    from version import VERSION as _V
    VER = _hl.md5(_V.encode()).hexdigest()[:8]   # 卡面程式的版本碼: 加在圖片網址後面,圖改了瀏覽器就會重新下載 (不會看到舊圖)
