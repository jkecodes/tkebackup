"""AI 思考過程紀錄。

Observed 包住任何代理 (HeuristicAgent / 其他代理),每次決策都記下:
當下手牌與體力、考慮過的選項、最後選了什麼、以及這個 AI 對每位玩家的身分判斷 (疑似反賊分數與態度)。
GUI 的「AI 思考」面板就是讀這些紀錄。
"""
from engine import Player
from view import ctext, full_name
from characters import SkillAct

CARD_REASON = {"降雷": "翻轉目標的武將牌", "偽": "偽裝成另一位武將,獲得他的技能", 
    "桃": "體力偏低,回血", "酒": "搭配殺增加傷害", "殺": "攻擊敵人", "決": "手上殺多/對方血少,決鬥",
    "火攻": "同色牌能打出火焰傷害", "順": "拿走對手的牌", "過": "拆掉對手的牌", "南": "敵人比友人多,全體攻擊",
    "萬": "敵人比友人多,全體攻擊", "突": "敵人比友人多,全體攻擊", "飢": "敵人比友人多,全體攻擊",
    "無": "抽 2 張牌", "增": "抽牌補手牌", "發": "抽牌補手牌", "未": "預先抽牌", "五": "拿一張好牌",
    "鐵": "橫置敵人 / 重鑄", "草": "判定可能多抽牌", "閃電": "體力夠,放入自己判定區賭一把",
    "樂": "讓敵人跳過出牌階段", "兵": "讓敵人跳過抽牌階段", "毒": "讓敵人翻面", "拋": "逼敵人棄牌並自己抽牌",
    "笑": "給牌並造成傷害", "鴻": "賭顏色造成傷害", "投": "幫友人回血", "借": "奪取敵人的武器",
    "轉": "換掉對手較好的防具", "強": "讓要攻擊的敵人受傷加倍", "弱": "減輕傷害", "孤": "體力低,賭一把回血", "漁": "盯著手牌多的敵人,他每出錦囊我就抽牌",
    "桃園": "友人受傷比敵人多", "聲": "交換手牌", "出": "把壞的延時錦囊移給敵人",
}


def pname(t):
    return t.name if isinstance(t, Player) else repr(t)


def opt_label(opt):
    card, t = opt
    base = f"〈{card.name}〉" if isinstance(card, SkillAct) else ctext(card)
    if t is None:
        return base
    if t == "heal":
        return base + " (回血)"
    if isinstance(t, Player):
        return f"{base} → {pname(t)}"
    if isinstance(t, tuple):
        return f"{base} → " + "、".join(pname(x) for x in t)
    if hasattr(t, "kind") and hasattr(t, "color"):   # 目標是一張牌 (丁奉: 要棄的裝備)
        return f"{base} → {ctext(t)}"
    return base


def belief_table(g, p, agent):
    """這個 AI 對每位其他玩家的判斷。只有有身分推理能力的代理才有。"""
    if not hasattr(agent, "attitude"):
        return []
    rows = []
    for q in g.others(p):
        a = agent.attitude(g, p, q)
        rows.append({
            "who": q.idx, "name": q.name, "hp": q.hp, "hand": len(q.hand),
            "sus": round(getattr(agent, "sus", {}).get(q.idx, 0.0), 1),
            "grudge": getattr(agent, "grudge", {}).get(q.idx, 0),
            "attitude": round(a, 1),
            "label": "敵" if a <= -1.0 else ("友" if a >= 1.0 else "未知"),
        })
    return rows


class Recorder:
    def __init__(self):
        self.items = []

    def add(self, g, p, kind, title, reason="", options=None, chosen=None, belief=None):
        self.items.append({
            "i": len(self.items), "round": g.round, "who": p.idx, "who_name": p.name, "kind": kind,
            "title": title, "reason": reason, "options": options or [], "chosen": chosen,
            "belief": belief or [],
            "state": f"體力 {p.hp}/{p.maxhp} 手牌 {len(p.hand)}: " + " ".join(repr(c) for c in p.hand),
        })


class Observed:
    """包住一個代理,記錄每次決策。其餘屬性 (attitude / observe ...) 直接轉給內部代理。"""

    def __init__(self, inner, rec: Recorder):
        self.inner, self.rec = inner, rec

    def __getattr__(self, name):
        return getattr(self.inner, name)

    # --- 主要決策: 出牌 ---
    def act(self, g, p, options):
        i = self.inner.act(g, p, options)
        labels = [opt_label(o) for o in options]
        if i is None:
            title, reason = "結束出牌階段", "沒有值得出的牌 (或手牌留著更好)"
        else:
            card, t = options[i]
            title = "出牌: " + labels[i]
            parts = []
            if isinstance(card, SkillAct):
                parts.append("使用武將技能")
            else:
                parts.append(CARD_REASON.get(card.name, ""))
            if isinstance(t, Player) and hasattr(self.inner, "attitude"):
                a = self.inner.attitude(g, p, t)
                s = getattr(self.inner, "sus", {}).get(t.idx, 0.0)
                parts.append(f"對 {t.name} 態度 {a:+.1f} (疑似反賊分 {s:+.1f})")
            reason = ";".join(x for x in parts if x)
        if getattr(self.inner, "last_reason", None):
            reason = self.inner.last_reason + (";" + reason if reason else "")
        self.rec.add(g, p, "act", title, reason, labels, i, belief_table(g, p, self.inner))
        return i

    # --- 響應 ---
    def respond(self, g, p, need, cands, ctx):
        c = self.inner.respond(g, p, need, cands, ctx)
        who = ""
        for k in ("attacker", "source", "src", "target", "victim"):
            if isinstance(ctx.get(k), Player):
                who = f" (相關: {ctx[k].name})"
                break
        title = f"響應 {full_name(need)}{who}: " + (f"打出 {ctext(c)}" if c else "不出")   # 對話框裡的牌名都用全名
        self.rec.add(g, p, "respond", title, getattr(self.inner, "last_reason", None) or "", [repr(x) for x in cands],
                     cands.index(c) if c in cands else None, belief_table(g, p, self.inner))
        return c

    # --- 其他選擇 (簡短記錄) ---
    def _short(self, kind, title_fn):
        def f(g, p, *a, **kw):
            r = getattr(self.inner, kind)(g, p, *a, **kw)
            self.rec.add(g, p, kind, title_fn(r, a))
            return r
        return f

    def choose_discard(self, g, p, n, cands, msg=None):
        r = self.inner.choose_discard(g, p, n, cands)
        self.rec.add(g, p, "discard", f"選擇棄 {n} 張: " + " ".join(ctext(c) for c in r),
                     "棄掉價值最低的牌", [repr(c) for c in cands])
        return r

    def choose_target(self, g, p, kind, cands):
        r = self.inner.choose_target(g, p, kind, cands)
        self.rec.add(g, p, "target", f"{kind}: 選擇目標 {pname(r)}", "選態度最差、體力最少的人",
                     belief=belief_table(g, p, self.inner))
        return r

    def choose_offturn(self, g, p, options, cur, when):
        i = self.inner.choose_offturn(g, p, options, cur, when)
        self.rec.add(g, p, "skill", f"{cur.name} 的{when}: " + (f"發動 {opt_label(options[i])}" if i is not None else "不發動技能"),
                     "", [opt_label(o) for o in options], i)
        return i

    def choose_skill(self, g, p, skill):
        r = self.inner.choose_skill(g, p, skill)
        self.rec.add(g, p, "skill", f"{skill}: {'發動' if r else '不發動'}")
        return r

    def choose_mode(self, g, p, skill, tgt):
        r = self.inner.choose_mode(g, p, skill, tgt)
        self.rec.add(g, p, "skill", f"{skill}: 對 {pname(tgt)} 選擇「{'令他棄牌' if r == 'discard' else '令他扣血'}」")
        return r

    def choose_give(self, g, p, drawn, others):
        r = self.inner.choose_give(g, p, drawn, others)
        self.rec.add(g, p, "skill", "馬良: " + (f"把 {r[1]} 交給 {pname(r[0])}" if r else "不交牌"))
        return r

    def pick_pile(self, g, p, pile):
        r = self.inner.pick_pile(g, p, pile)
        self.rec.add(g, p, "pile", f"五穀豐登: 拿 {ctext(r) if r else '不拿'}", "選價值最高的牌", [repr(c) for c in pile])
        return r
