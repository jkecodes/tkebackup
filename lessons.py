"""教學關卡: 預先佈置好牌桌 (手牌 / 裝備 / 體力 / 牌堆順序),一步一步教每張牌、每個身分、每位武將怎麼用。

一關 = 一個 dict:
  id / group / name / intro (一句話) / tips (多行重點) / steps [(提示文字, 紀錄 regex)]
  players: 座位 0 是玩家本人; 每位 {char, hp, maxhp, hand, equip, judge, chained, ai, plan, resp}
  top: 牌堆頂依序會抽到的牌;  roles / lord: 身分關卡才用
  bot: 自動測試用的解法 [(牌名, 目標座位)];  bot_resp: 自動測試時願意回應的需求
牌的寫法: "決" / "火殺" / "殺@黑" (@紅 @黑 指定花色)。
步驟的 regex 比對遊戲紀錄的每一行,依序比對到才算完成這一步。
"""
import re

from ai import RandomAgent
from engine import Player
from view import full_name

NATURES = ("火", "冰", "雷")


def parse(spec):
    color = None
    if "@" in spec:
        spec, color = spec.split("@")
    nature = None
    if len(spec) == 2 and spec[0] in NATURES and spec[1] == "殺":
        nature, spec = spec[0], "殺"
    return spec, nature, color


def take(g, spec):
    name, nature, color = parse(spec)
    for i in range(len(g.deck) - 1, -1, -1):
        c = g.deck[i]
        if c.name == name and c.nature == nature and (color is None or c.color == color):
            return g.deck.pop(i)
    raise KeyError(f"牌堆找不到 {spec}")


def _slot(p, c):
    if c.kind == "horse":
        return "h+" if c.name == "+1馬" else "h-"
    return c.kind


def apply(g, L):
    """開局佈置: 取代一般的每人抽 5 張。"""
    if L.get("roles"):
        for p, r in zip(g.players, L["roles"]):
            p.role = r
        g.lord = next(p for p in g.players if p.role == "主公")
        g.revealed = {g.lord.idx: "主公"}
    for i, ps in enumerate(L["players"]):
        p = g.players[i]
        if ps.get("maxhp"):
            p.maxhp = ps["maxhp"]
        for s in ps.get("hand", []):
            p.hand.append(take(g, s))
        p.hp = ps.get("hp", p.maxhp)   # 先發手牌再定體力 (孟獲的體力上限 = 手牌數 + 1)
        for s in ps.get("equip", []):
            c = take(g, s)
            p.equip[_slot(p, c)] = c
        for s in ps.get("judge", []):
            c = take(g, s)
            c.placed_by = g.players[ps.get("by", 0)]
            p.judge.append(c)
        p.chained = bool(ps.get("chained"))
        if ps.get("deal"):   # 從牌堆再抽幾張 (身分關卡: 對手拿一般的手牌)
            g.draw(p, ps["deal"])
    for s in reversed(L.get("top", [])):   # 牌堆是從尾端抽: 最先抽到的放最後
        g.deck.append(take(g, s))
    g.scn_nodraw = (0,) if not L.get("draw", 0) else ()
    for p in g.players:
        p.max_hand = len(p.hand)


class ScriptAgent(RandomAgent):
    """關卡裡的對手: 照劇本行動 (plan 是 [(牌名, 目標座位)]),其餘一律不動; resp 指定哪些響應要打出。"""

    def __init__(self, plan=(), resp=(), skill=(), chain=(), off=()):
        self.plan, self.resp, self.skill, self.chain, self.off = list(plan), set(resp), set(skill), list(chain), list(off)

    def act(self, g, p, options):
        for k, (name, tgt) in enumerate(self.plan):
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", None) != name:
                    continue
                if isinstance(tgt, int) and not (isinstance(t, Player) and t.idx == tgt):
                    continue
                if isinstance(tgt, tuple) and not (isinstance(t, tuple) and [x.idx for x in t] == list(tgt)):
                    continue
                self.plan.pop(k)
                return i
        return None

    def respond(self, g, p, need, cands, ctx):
        return cands[0] if cands and need in self.resp else None

    def choose_offturn(self, g, p, options, cur, when):
        for k, (name, tgt) in enumerate(self.off):
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", None) == name and (not isinstance(tgt, int) or (isinstance(t, Player) and t.idx == tgt)):
                    self.off.pop(k)
                    return i
        return None

    def choose_option(self, g, p, skill, labels):
        return 0

    def choose_discard(self, g, p, n, cands, msg=None):
        return list(cands[:n])

    def choose_from(self, g, p, target, cands):
        return cands[0]

    def show_card(self, g, p, hand):
        return hand[0]

    def choose_target(self, g, p, kind, cands):
        return cands[0]

    def choose_borrow(self, g, p, skill, cands):
        return cands[0] if cands else None

    def choose_dir(self, g, p):
        return "L"

    def choose_x(self, g, p):
        return 2

    def choose_chain(self, g, p):
        return [g.players[i] for i in self.chain]

    def pick_pile(self, g, p, pile):
        return pile[0]

    def choose_skill(self, g, p, skill):
        return skill in self.skill

    def choose_mode(self, g, p, skill, tgt):
        return "damage"

    def choose_give(self, g, p, drawn, others):
        return None

    def choose_count(self, g, p, skill, maxn):
        return 1


# ---------- 步驟 regex 小工具 ----------
def U(card, who=0):   # P{who} 使用某張牌 (紀錄裡有時寫簡稱、有時寫全名)
    names = "|".join(re.escape(x) for x in dict.fromkeys((full_name(card), card)))
    return rf"P{who}\([^)]*\)[^\n]*使用 ?[紅黑]?[火冰雷]?(?:{names})(?![一-鿿])"


def DMG(i, n=1):      # P{i} 受到 n 點傷害
    return rf"P{i}\([^)]*\)\s*受到 {n} 點"


def TURN(i):          # 輪到 P{i} 的回合
    return rf"--- 第\d+輪 P{i}\("


def P(i):
    return rf"P{i}\("


GROUPS = ["基本牌", "錦囊", "裝備", "身分", "武將"]
LESSONS: list[dict] = []


def lesson(id, group, name, intro, players, steps, tips=(), top=(), bot=(), bot_resp=(), bot_skill=(), bot_chain=(), bot_off=(), roles=None, lord=0, draw=0, real_ai=0, chars=None, n=4):
    L = dict(id=id, group=group, name=name, intro=intro, players=players, steps=steps, tips=list(tips), top=list(top), bot=list(bot),
             bot_resp=set(bot_resp), bot_skill=set(bot_skill), bot_chain=list(bot_chain), bot_off=list(bot_off), roles=roles, lord=lord, draw=draw, real_ai=real_ai, chars=chars or [None] * n, n=n)
    LESSONS.append(L)
    return L


def pad(players, n=4):
    ps = [dict(p) for p in players]
    while len(ps) < n:
        ps.append({})
    return ps


import sys  # noqa: E402
from lessons_data import build  # noqa: E402  (關卡資料另放一個檔)

build(sys.modules[__name__])


def add_generals(roster_data):
    """伺服器載入武將資料後呼叫: 每位武將生出一關。"""
    from lessons_gen import build_generals
    if not any(L["group"] == "武將" for L in LESSONS):
        build_generals(sys.modules[__name__], roster_data, UNTAGGED)


UNTAGGED = {'公孫瓚', '典韋', '周瑜', '周胤', '孫策', '徐晃', '曹丕', '曹彰', '甘寧', '羊祜', '華佗', '董卓', '諸葛亮', '鐘繇', '陸遜', '顏良&文醜', '馬超', '黃忠'}


def by_id(i):
    return next((L for L in LESSONS if L["id"] == i), None)


def public(L):
    return {k: L[k] for k in ("id", "group", "name", "intro", "tips") if k in L} | {"faction": L.get("faction"), "steps": [s[0] for s in L["steps"]]}


def catalog():
    return [public(L) for L in LESSONS]
