"""第 5 級電腦 (ProAgent): 把實戰機器人 (LoneAChess) 的決策邏輯移植進引擎。

和第 1~4 級一樣只看公開資訊 (場上血量 / 手牌張數 / 裝備 / 已公開的身分 / 公開行為推理的態度),不偷看別人的手牌和身分。

主要規則 (數字都是「卡牌優先度」, 越高越捨不得丟):
- 留牌 / 棄牌 / 給牌 / 五穀豐登 / 丈八蛇矛選牌 / 各種「棄 X」: 一律照卡牌優先度排序 (見 PRI 與 keep_val)。
- 手上有發憤圖強時, 反擊與調虎離山 +100; 再有 (反擊或調虎離山) 時, 強化與鐵索連環 +40。
- 已經裝備同欄位 (武器 / 防具 / +1馬 / -1馬分開算; 雙欄武將兩格都滿才算) 且已裝備的優先度不低於手牌 → 手牌 -50。
- 發憤圖強爆發法: 有發憤圖強又有轉傷牌 (反擊 / 調虎離山, 蔣幹是任何牌) 時, 少棄牌自傷再把傷害轉給敵人。
- 貫石斧一律發動, 寒冰劍一律不發動。
"""
import math
import re

from ai import LeveledAgent
from characters import SkillAct
from engine import Player as Player_cls
from view import full_name

# ---------------------------------------------------------------- 卡牌優先度 (全名)
# 2026-11 用 priostat.py 的 10 萬局自我對戰重新校正: 「起手有這張牌的勝率變化」和原本的表各佔一半重排
# (對照測試 prioab.py: 換沒調過的種子 2 萬組,連同偽裝實測表一起 +1.85 個百分點)。發憤圖強 / 偽裝維持原值。
PRI = {
    "發憤圖強": 444, "緩衝盾": 100, "反擊": 99, "調虎離山": 98, "偽裝": 97, "增兵減灶": 95, "流星錘": 95, "無中生有": 94,
    "酒": 93, "飢餓": 92, "南蠻入侵": 92, "順手牽羊": 91, "萬箭齊發": 90, "桃": 85, "拋磚引玉": 84, "未雨綢繆": 81,
    "五穀豐登": 80, "閃": 80, "決鬥": 75, "隔岸觀火": 74, "過河拆橋": 74, "藤甲": 74, "強化": 73, "殺": 73,
    "鴻門宴": 72, "聲東擊西": 71, "突襲": 71, "占卜": 70, "樂不思蜀": 70, "青釭劍": 70, "火攻": 70, "孔雀羽扇": 70,
    "八卦陣": 70, "笑裡藏刀": 69, "降雷": 68, "無懈可擊": 65, "孤注一擲": 65, "鐵索連環": 65, "兵糧寸斷": 60, "諸葛連弩": 60,
    "火盾": 60, "仁王盾": 60, "貫石斧": 55, "弱化": 50, "轉移": 50, "方天畫戟": 50, "丈八蛇矛": 50, "+1馬": 50,
    "-1馬": 50, "借刀殺人": 50, "投桃報李": 45, "出其不意": 40, "草木皆兵": 40, "桃園結義": 35, "毒": 30, "雷盾": 30,
    "冰盾": 30, "閃電": 30, "青龍偃月刀": 20, "寒冰劍": 0, "麒麟弓": 0,
}
DUAL_W = {"甘寧", "夏侯淵"}
DUAL_A = {"周瑜", "甘寧", "夏侯淵"}
AOE = ("南蠻入侵", "萬箭齊發", "飢餓", "突襲")
DMG_CARDS = ("決鬥", "火攻", "笑裡藏刀", "降雷")
SHA_NAMES = ("殺", "火殺", "冰殺", "雷殺")

_FN = {}


def fn(c):
    """牌的全名 (反 → 反擊 …); ViewCard 用它當成的那種牌。"""
    n = getattr(c, "name", "")
    r = _FN.get(n)
    if r is None:
        r = _FN[n] = full_name(n)
    return r


def is_sha(c):
    return getattr(c, "name", "") == "殺"


def real(c):
    return getattr(c, "orig", c)


def slot_of(c):
    k = getattr(c, "kind", "")
    if k == "horse":
        return "h+" if c.name == "+1馬" else "h-"
    return k if k in ("weapon", "armor") else None


class ProAgent(LeveledAgent):
    """第 5 級: 用實戰機器人的優先度與戰術取代第 4 級的出牌 / 選牌判斷。"""

    # 難度 1~5: 不再「隨機亂出牌 / 該響應卻不響應」(看起來像壞掉),而是逐級關掉進階判斷,基本常識 (回血 / 裝備 / 出殺出閃 / 不打已知隊友) 一直保留:
    #   5 極強: 全開
    #   4 很強: 關掉連招規劃與武將專屬戰術 (發憤圖強爆發 / 鐵索連環連擊 / 偽裝計畫 / 集火特定武將…)
    #   3 強:   再關掉「挑最佳目標」 (改成在可打的敵人裡隨機選)
    #   2 中:   再關掉身分推理 (不從公開行為推測誰是反賊 / 忠臣, 也不記仇)
    #   1 弱:   再關掉 ⚡ 連鎖牌 / 受傷響應的取捨 (被打時只會出閃 / 桃,不用反擊 / 調虎離山 / 占卜 / 弱化 / 降雷)
    def adv(self, name):
        """這個進階判斷在目前難度有沒有開。"""
        need = {"combo": 5, "pick": 4, "infer": 3, "bolt": 2}[name]   # 難度 >= need 才開
        return self.err_level >= need

    def __init__(self, level=5):
        super().__init__(level=4)
        self.level = 5
        self.err_level = max(1, min(5, int(level)))   # 內部判斷一律走 5 級的程式,難度只決定上面哪些進階判斷有開
        self._tries = {}
        self._dg_want = None

    def observe(self, g, me, kind, src, tgt):
        if self.adv("infer"):   # 2 級以下不從公開行為推理身分 (態度只剩「主公公開 / 已翻開的身分」這些明擺著的資訊)
            super().observe(g, me, kind, src, tgt)

    # ------------------------------------------------------------ 卡牌優先度
    pri = PRI        # 卡牌優先度表 (測試台可以換成別張表做對照)
    spy = None       # 內奸的平衡打法參數 (None = 關)
    hunt_bonus = 40  # 暗殺目標模式: 打自己目標的加分
    threat = {}      # 武將集火加分 (武將名 → 加到 tscore 的分數)。實測「照武將勝率加分」沒效果 (+0.2 / +0.3 / +0.05 / -0.2), 所以留空
    dg_data = 1      # 偽裝變成誰: 0 = 原本的固定順序, 1 = 照實測表 (對照測試 +1.03 個百分點)
    dg_th = 0.5      # 實測表分數至少多少才用偽裝

    def base_pri(self, c):
        n = fn(real(c))
        if is_sha(real(c)):
            return self.pri["殺"]
        if n in self.pri:
            return self.pri[n]
        return 30 if getattr(real(c), "kind", "") in ("weapon", "armor", "horse") else 50

    def equipped(self, p, slot):
        if slot in ("weapon", "armor"):
            two = (p._char.name in (DUAL_W if slot == "weapon" else DUAL_A))
            cs = [p.equip.get(slot)] + ([p.equip.get(slot + "2")] if two else [])
            return cs if all(cs) else None   # 兩格都裝滿才回傳
        c = p.equip.get(slot)
        return [c] if c else None

    def keep_val(self, g, p, c):
        """這張牌對 p 的保留價值 (卡牌優先度, 含手牌 / 裝備的動態加減)。"""
        c = real(c)
        n = fn(c)
        if p._char.name == "蔣幹" and n == "偽裝":
            return -444
        v = self.base_pri(c)
        names = [fn(h) for h in p.hand]
        if n == "諸葛連弩" and sum(1 for h in p.hand if is_sha(h)) >= 2 and not p.has_weapon("諸葛連弩"):
            v += 19
        if "發憤圖強" in names:
            if n in ("反擊", "調虎離山"):
                v += 100
            if ("反擊" in names or "調虎離山" in names) and n in ("強化", "鐵索連環"):
                v += 40
        sl = slot_of(c)
        if sl:
            cur = self.equipped(p, sl)
            if cur and not any(x is c for x in cur) and min(self.base_pri(x) for x in cur) >= v:
                v -= 50
        return v

    def kv(self, g, p):
        return lambda c: self.keep_val(g, p, c)

    # ------------------------------------------------------------ 情勢判斷 (只用公開資訊)
    def tscore(self, g, p, q):
        """攻擊價值: 越高越該打; <= -100 代表不能 / 不該打 (隊友、必須保留的主公)。"""
        if q is p or not q.alive:
            return -999
        att = self.attitude(g, p, q)
        if att >= 1.0:
            return -999
        sc = 50 - q.hp * 5 - len(q.hand) * 0.3 + (25 if q.hp <= 1 else 0) - att * 6
        if getattr(g, "hunt", False) and g.targets.get(p.idx) == q.idx:   # 暗殺目標模式: 自己的目標優先打 (親手殺死就贏)
            sc += self.hunt_bonus
        if self.threat and self.adv("combo"):   # 強的武將先打 (5 級才開)
            sc += self.threat.get(q._char.name, 0)
        if p.role == "反賊" and q is g.lord and not getattr(g, "hidden_lord", False):
            sc += 300 if self._lethal else (50 if q.hp <= 2 else 15)
        elif p.role == "內奸" and q is g.lord and not getattr(g, "hidden_lord", False):
            others = [x for x in g.alive_players() if x is not p and x is not g.lord]
            return -999 if others else (200 if self._lethal else 100)
        elif p.role == "內奸" and self.spy and self.adv("combo") and not getattr(g, "hidden_lord", False):
            b = self.spy_bias(g, p, q)
            if b <= -900:
                return -999
            sc += b
        return sc

    def spy_want(self, g, p):
        """內奸現在該削弱哪一邊: 'R' 反賊 / 'Z' 忠臣 / None (只剩一邊,照常打)。回傳 (想打的一邊, {玩家idx: 'R' / 'Z' / '?'})。
        場上還剩幾個反賊 / 忠臣是公開資訊 (總數固定,死掉的會翻身分); 誰是誰只靠公開行為推理 (sus)。"""
        cfg = self.spy
        lord = g.lord
        others = [x for x in g.alive_players() if x is not p and x is not lord]
        R = sum(1 for x in others if x.role == "反賊")
        Z = sum(1 for x in others if x.role == "忠臣")
        th = cfg.get("th", 1.0)
        cls = {x.idx: ("R" if self.sus.get(x.idx, 0.0) >= th else "Z" if self.sus.get(x.idx, 0.0) <= -th else "?") for x in others}
        if R == 0 or Z == 0:
            return None, cls
        nr, nz = sum(1 for v in cls.values() if v == "R"), sum(1 for v in cls.values() if v == "Z")
        if nr >= R:      # 反賊都認出來了: 剩下的是忠臣
            cls = {k: ("Z" if v == "?" else v) for k, v in cls.items()}
        elif nz >= Z:    # 忠臣都認出來了: 剩下的是反賊
            cls = {k: ("R" if v == "?" else v) for k, v in cls.items()}
        if not lord.alive or lord.hp <= cfg.get("dhp", 2):
            return "R", cls      # 主公有危險: 先清反賊 (主公一死就是反賊贏)
        if R <= Z + cfg.get("margin", 0):
            return "Z", cls      # 反賊不比忠臣多: 留著反賊牽制,先削忠臣
        return "R", cls

    def spy_bias(self, g, p, q):
        want, cls = self.spy_want(g, p)
        c = cls.get(q.idx, "?")
        if want is None or c == "?":
            return 0
        cfg = self.spy
        if c == want:
            return cfg.get("b", 30)
        if want == "Z" and cfg.get("block", 0):   # 留著牽制用的反賊: 完全不打
            return -999
        return -cfg.get("b", 30)

    def foes_of(self, g, p):
        return [q for q in g.others(p) if self.tscore(g, p, q) > -100]

    def dir_score(self, g, p, side, n=1):
        """調虎離山往這個方向轉 n 點傷害的期望價值: 依序每個人「沒有閃而中招」的機率 x 打到他的好壞 (敵人 +, 隊友 -)。
        閃只佔牌堆約 3%, 所以幾乎都是該方向第一個人中招。"""
        prob, score = 1.0, 0.0
        for q in g.side_order(p, side):
            pf = 0.97 ** len(q.hand)
            if q.has_armor("八卦陣") and not g.equip_off():
                pf *= 0.5
            if self.attitude(g, p, q) >= 1.0:
                val = -1.5 - (2 if q is g.lord else 0) - (1 if q.hp <= n else 0)
            else:
                ts = self.tscore(g, p, q)
                val = -1.0 if ts <= -100 else 1 + ts / 100 + (0.5 if q.hp <= n else 0)
            score += prob * pf * val
            prob *= 1 - pf
        return score

    def choose_dir(self, g, p):
        """突襲 / 調虎離山的方向: 往敵人那邊轉 (3 級以下照舊隨機)。"""
        if not self.adv("pick"):
            return super().choose_dir(g, p)
        l, r = self.dir_score(g, p, "L"), self.dir_score(g, p, "R")
        return "L" if l > r else "R" if r > l else super().choose_dir(g, p)

    def burst(self, g, p):
        hand = p.hand
        hammer = 1 if (p.has_weapon("流星錘") or any(fn(c) == "流星錘" for c in hand)) else 0
        n = sum(1 for c in hand if fn(c) in ("決鬥", "南蠻入侵", "萬箭齊發", "飢餓", "突襲", "火攻", "笑裡藏刀")) + min(1, sum(1 for c in hand if is_sha(c)))
        buff = sum(1 for c in hand if fn(c) == "強化")
        per = (1 + hammer) * 2 ** min(buff, 3)
        return {"n": n, "buff": buff, "hammer": hammer, "per": per, "total": n * per}

    def redirect_cnt(self, p):
        c = sum(1 for h in p.hand if fn(h) in ("反擊", "調虎離山"))
        if p._char.name == "蔣幹":
            c += max(0, len(p.hand) - 1)
        return c

    def potential_damage(self, g, p):
        b = self.burst(g, p)
        mult = 2 ** min(b["buff"], 3)
        sha = sum(1 for c in p.hand if is_sha(c))
        d = b["total"] + (mult if any(fn(c) == "酒" for c in p.hand) and sha else 0)
        if any(fn(c) == "發憤圖強" for c in p.hand) and self.redirect_cnt(p) > 0:
            d = max(d, (5 + b["hammer"]) * mult)
        return d

    def lethal_on_lord(self, g, p):
        lord = g.lord
        if getattr(g, "hidden_lord", False) or not lord.alive or lord is p:
            return False
        dmg = self.potential_damage(g, p)
        hands = sum(len(q.hand) for q in g.others(p))
        need = dmg - lord.hp + 1
        return dmg >= lord.hp and need >= max(1, math.ceil(hands * 0.13 + 0.4))

    def update_lethal(self, g, p):
        self._lethal = False
        if p.role == "反賊" or (p.role == "內奸" and not [x for x in g.alive_players() if x is not p and x is not g.lord]):
            self._lethal = self.lethal_on_lord(g, p)

    _lethal = False

    def atk_adj(self, g, p, card, t):
        """對 t 打這張牌的修正: <= -100 代表打了沒用 (被防具擋掉)。"""
        c = real(card)
        n = fn(c)
        sha = is_sha(c)
        if not (sha or n in AOE or n in DMG_CARDS):
            return 0
        if g.equip_off() or not t.armor_names():
            return 0
        nature = getattr(c, "nature", None)
        if sha and p.has_weapon("孔雀羽扇"):
            nature = "火"
        if n == "火攻":
            nature = "火"
        if n == "降雷":
            nature = "雷"
        if sha and p.has_weapon("青釭劍"):
            return 0
        b = self.burst(g, p)
        dmg = (1 + b["hammer"]) * 2 ** min(3, b["buff"])
        adj = 0
        for a in t.armor_names():
            if a == "仁王盾" and sha and c.color == "黑":
                return -999
            if a == "藤甲":
                if nature == "火":
                    adj += 12
                elif (sha and not nature) or n in AOE:
                    return -999
            if (a, nature) in (("火盾", "火"), ("冰盾", "冰"), ("雷盾", "雷")):
                return -999
            if a == "緩衝盾" and dmg <= 1 and n not in AOE:
                return -999
            if a == "八卦陣" and sha:
                adj -= 12
        return adj

    # ------------------------------------------------------------ 出牌
    def act(self, g, p, options):
        if not options:
            return None
        self.update_lethal(g, p)
        if self._tries.get("turn") != g.turn_id:
            self._tries = {"turn": g.turn_id}
        hand = p.hand
        hurt = p.hp < p.maxhp
        foes = self.foes_of(g, p)
        b = self.burst(g, p)
        cs = sum(1 for c in hand if is_sha(c))
        owed = sum(p.fa_debt) if p.fa_debt else 0
        red = self.redirect_cnt(p)
        names = [fn(c) for c in hand]
        sbr = ("發憤圖強" in names) and red > 0 and bool(foes) and (p.hp >= 2 or "占卜" in names or "桃" in names)
        if not self.adv("combo"):   # 4 級以下不做連招規劃
            sbr = False
            self._lethal = False
        chain_plan = self.chain_plan(g, p) if self.adv("combo") else None
        chained = self.chained_enemy(g, p) if self.adv("combo") else None
        combo_on = sbr or bool(chained)
        keep_floor = 0
        if owed > 0 and red == 0 and not chained and not chain_plan and not self._lethal:
            keep_floor = owed
        elif owed > 0 and p._char.name == "蔣幹" and not self._lethal and foes:
            keep_floor = 3
        lord = g.lord if not getattr(g, "hidden_lord", False) else None
        lord_low = bool(lord and lord.alive and lord.hp <= 2)
        best_t = max(foes, key=lambda q: self.tscore(g, p, q)) if foes else None
        killable = bool(best_t and b["total"] >= best_t.hp)

        # 依牌分組, 同一張牌 (或同一個技能) 只留最該打的目標
        groups = {}
        for i, (c, t) in enumerate(options):
            key = ("s", c.name) if isinstance(c, SkillAct) else ("c", id(c))
            groups.setdefault(key, []).append(i)

        cands = []   # (bucket, pri, index, name)
        for key, idxs in groups.items():
            c = options[idxs[0]][0]
            if isinstance(c, SkillAct):
                r = self.skill_cand(g, p, c, [(i, options[i][1]) for i in idxs], foes, keep_floor)
                if r:
                    cands.append(r)
                continue
            r = self.card_cand(g, p, c, [(i, options[i][1]) for i in idxs], foes, b, cs, hurt, sbr, chain_plan,
                               chained, combo_on, killable, lord, lord_low)
            if r is None:
                continue
            bucket, pri, i, n = r
            if pri > 0 and keep_floor and len(hand) - 1 < keep_floor and n not in ("發憤圖強", "無中生有") and not (n == "桃" and p.hp <= 2):
                continue
            if pri > 0:
                cands.append((bucket, pri, i, n))
        if self.adv("combo"):
            cands = self.tactics(g, p, options, cands, foes)
        elif g.void and p is g.cur:   # 規則限制 (呂布 無效全場): 只能出基本牌,這是基本常識,所有難度都遵守
            cands = [c for c in cands if isinstance(options[c[2]][0], SkillAct) or getattr(real(options[c[2]][0]), "kind", "") == "basic"]
        r = self.char_act(g, p, options)
        if r is not None:
            cands.append(r)
        if not cands:
            return None
        cands.sort(key=lambda x: (x[0], -x[1]))
        bucket, pri, i, n = cands[0]
        cd = options[i][0]
        k = ("s", cd.name) if isinstance(cd, SkillAct) else ("c", id(cd))   # 同一張牌 / 同一個技能重複選到 (沒打成功) 才擋, 避免無窮迴圈
        self._tries[k] = self._tries.get(k, 0) + 1
        if self._tries[k] > 3:
            return None
        return i

    # ------------------------------------------------------------ 武將專屬戰術 / 偽裝
    def on_field(self, g, nm):
        return any(q._char.name == nm for q in g.players)

    def disguise_plan(self, g, p):
        """偽裝變身目標 (使用者給的順序): 劉禪(單挑) > 劉備 > 陳群 > 孔融 > 周魴 > 吳懿; 目標必須不在場上。"""
        if p._char.name == "蔣幹" or p.disguise:
            return None
        hand = [c for c in p.hand if fn(c) != "偽裝"]
        n = len(hand)
        tricks = sum(1 for c in hand if c.kind == "trick")
        lord = g.lord if not getattr(g, "hidden_lord", False) else None
        team = p.role in ("主公", "忠臣")
        low = p.hp <= 2 or (team and lord is not None and lord.alive and lord.hp <= 2)
        foes = self.foes_of(g, p)
        used = g.__dict__.setdefault("_pro_ld", set())
        if self.dg_data:   # 照實測表挑分數最高的 (dg_table.py)
            taken = {q._char.name for q in g.players} | {x.name for q in g.players for x in q.disguise}
            from characters import ROSTER
            pool = [nm for nm in ROSTER if nm not in taken and not (nm == "劉禪" and p.idx in used)]
            if pool:
                sc = self.dg_scores(g, p, pool, foes)
                best = max(pool, key=lambda nm: sc[nm])
                if sc[best] >= self.dg_th:
                    return best
            if self.dg_data == 1:
                return None
        if len(g.alive_players()) == 2 and not self.on_field(g, "劉禪") and "劉禪" not in used:
            return "劉禪"
        if tricks >= 3 and low and not self.on_field(g, "劉備"):
            return "劉備"
        if p.hp == 4 and n >= 4 and not self.on_field(g, "陳群"):
            return "陳群"
        if p.hp != 4 and n >= 4 and not self.on_field(g, "孔融"):
            return "孔融"
        if n >= 3 and not self.on_field(g, "周魴") and any(q.hp <= 3 and "緩衝盾" not in q.armor_names() for q in foes):
            return "周魴"
        if not self.on_field(g, "吳懿") and any(len(q.hand) >= 5 and len(q.hand) >= n + 2 for q in foes):
            return "吳懿"
        return None

    def keep_color(self, g, p):
        sums = {"紅": 0, "黑": 0}
        for c in p.hand:
            if c.color in sums:
                sums[c.color] += self.keep_val(g, p, c) + 1
        return "紅" if sums["紅"] >= sums["黑"] else "黑"

    def tactics(self, g, p, options, cands, foes):
        me = p._char.name
        cur = p.disguise[0].name if p.disguise else me   # 目前實際使用技能的武將 (偽裝中是偽裝的那位)
        hand = p.hand
        out = list(cands)
        sk = lambda nm: [(i, t) for i, (c, t) in enumerate(options) if isinstance(c, SkillAct) and c.name == nm]
        card_of = lambda c: options[c[2]][0]
        # --- 偽裝: 照使用者的策略變身
        for i, (c, t) in enumerate(options):
            if not isinstance(c, SkillAct) and fn(real(c)) == "偽裝" and not p.disguise:
                want = self.disguise_plan(g, p)
                if want:
                    self._dg_want = (g.turn_id, want)
                    out.append((-0.6, 160, i, "偽裝→" + want))
                break
        # --- 偽裝中的專屬技能
        if p.disguise:
            if cur == "劉禪":
                tg = [(i, t) for i, t in sk("劉禪-棄光並跳過回合") if hasattr(t, "hp") and self.tscore(g, p, t) > -100]
                if tg:
                    best = max(tg, key=lambda it: self.tscore(g, p, it[1]))
                    g.__dict__.setdefault("_pro_ld", set()).add(p.idx)
                    out.append((-0.5, 150, best[0], "劉禪技能"))
            elif cur == "陳群":
                for i, t in sk("陳群-手牌當突襲"):
                    out.append((-0.5, 150, i, "陳群技能"))
            elif cur == "孔融":
                for i, t in sk("孔融-重鑄手牌"):
                    out.append((-0.5, 150, i, "孔融技能"))
            elif cur == "劉備":
                low_ally = [(i, t) for i, t in sk("劉備-仁回血") if hasattr(t, "hp") and self.attitude(g, p, t) >= 1]
                if low_ally:
                    best = min(low_ally, key=lambda it: it[1].hp)
                    out.append((-0.5, 150, best[0], "劉備回血"))
                for i, t in sk("劉備-棄錦囊得仁"):
                    out.append((-0.5, 88, i, "劉備得仁"))
            elif cur == "周魴" and len(hand) <= 3:
                tg = [(i, t) for i, t in sk("周魴-棄牌扣血") if hasattr(t, "hp") and t.hp <= 3 and self.tscore(g, p, t) > -100]
                if tg:
                    best = min(tg, key=lambda it: it[1].hp * 10 + len(it[1].hand))
                    out.append((-0.5, 150, best[0], "周魴技能"))
            elif cur == "吳懿" and (len(hand) <= 1 or not [c for c in cands if c[0] >= 0]):
                tg = [(i, t) for i, t in sk("吳懿-交換手牌") if hasattr(t, "hand")]
                if tg:
                    best = max(tg, key=lambda it: len(it[1].hand))
                    out.append((-0.5, 150, best[0], "吳懿技能"))
        # --- 每回合一定發動的技能
        if cur in ("曹植", "公孫淵") or me in ("曹植", "公孫淵"):
            for nm in ("曹植-洗手牌", "公孫淵-亮牌抽2"):
                for i, t in sk(nm):
                    k = ("always", nm)
                    if self._tries.get(k, 0) < 2:
                        self._tries[k] = self._tries.get(k, 0) + 1
                        out.append((-2, 250, i, nm))
        # --- 呂蒙: 這回合沒出殺就不用棄牌, 所以不出殺 (除非能殺人)
        if cur == "呂蒙" and not self._lethal and not any(q.hp <= 1 for q in foes):
            out = [c for c in out if not is_sha(real(card_of(c)))]
        # --- 諸葛亮: 手牌盡量出光 (沒手牌 = 無敵), 不補牌、不出有風險的
        if cur == "諸葛亮" and hand:
            skip = {"無中生有", "增兵減灶", "未雨綢繆", "五穀豐登", "桃園結義", "發憤圖強", "閃電", "偽裝"}
            risk = {"決鬥", "孤注一擲", "鴻門宴"}
            def blocked(cd):
                if isinstance(cd, SkillAct):
                    return False
                n = fn(real(cd))
                return n in skip or (n in risk and len(hand) > 1)
            out = [c for c in out if not blocked(card_of(c))]
            used = {id(card_of(c)) for c in out}
            seen = set()
            for i, (c, t) in enumerate(options):
                if isinstance(c, SkillAct) or id(c) in used or id(c) in seen or blocked(c):
                    continue
                seen.add(id(c))
                out.append((6, 8, i, "(清手牌)" + fn(real(c))))
        # --- 忠臣: 主公缺血時主動幫他回血
        lord = g.lord if not getattr(g, "hidden_lord", False) else None
        if p.role == "忠臣" and lord is not None and lord.alive and lord.hp < lord.maxhp:
            for i, (c, t) in enumerate(options):
                if isinstance(c, SkillAct):
                    continue
                n = fn(real(c))
                if n == "投桃報李" and t is lord:
                    out.append((-0.4, 120, i, "投桃報李→主公"))
                    break
                if n == "桃園結義" and me != "劉備":
                    out.append((-0.4, 119, i, n))
                    break
        # --- 對付敵人蔣幹: 降雷 > 拆/拿牌 > 傷害牌, 不用強化弱化 (免得被他調虎離山後跳過我的回合)
        jg = [q for q in foes if q._char.name == "蔣幹"]
        if jg and me != "蔣幹":
            j = jg[0]
            out = [c for c in out if isinstance(card_of(c), SkillAct) or fn(real(card_of(c))) not in ("強化", "弱化")]
            for i, (c, t) in enumerate(options):
                if isinstance(c, SkillAct) or t is not j:
                    continue
                n = fn(real(c))
                if n == "降雷":
                    out.append((-0.3, 195, i, "降雷→蔣幹"))
                elif n in ("過河拆橋", "順手牽羊"):
                    out.append((-0.3, 190, i, n + "→蔣幹"))
                elif (is_sha(real(c)) or n in ("決鬥", "火攻", "笑裡藏刀", "鴻門宴")) and self.atk_adj(g, p, c, j) > -100:
                    out.append((-0.3, 185, i, n + "→蔣幹"))
        # --- 曹植在場 (敵人): 前 8 輪集火他
        ct = [q for q in foes if q._char.name == "曹植"]
        if ct and me != "曹植" and g.round <= 8 and not (p.role == "忠臣" and ct[0] is g.lord and g.round <= 5):
            q0 = ct[0]
            for i, (c, t) in enumerate(options):
                if isinstance(c, SkillAct):
                    continue
                n = fn(real(c))
                if t is q0 and (is_sha(real(c)) or n in ("決鬥", "火攻", "笑裡藏刀", "降雷", "鴻門宴")) and self.atk_adj(g, p, c, q0) > -100:
                    out.append((-0.2, 190, i, n + "→曹植"))
        # --- 曹仁: 出牌階段盡量把手牌打成同色 (棄牌階段後展示全同色就抽 2)
        if cur == "曹仁" and len(hand) > 1 and len({c.color for c in hand}) > 1:
            keep = self.keep_color(g, p)
            seen = set()
            for i, (c, t) in enumerate(options):
                if isinstance(c, SkillAct) or c.color == keep or not c.color or id(c) in seen:
                    continue
                n = fn(real(c))
                ok = False
                if c.kind in ("weapon", "armor", "horse"):
                    ok = t is None
                elif n in ("無中生有", "增兵減灶", "未雨綢繆") or n == "五穀豐登":
                    ok = True
                elif n in AOE:
                    ok = not [q for q in g.others(p) if self.attitude(g, p, q) >= 1]
                elif n == "桃":
                    ok = p.hp < p.maxhp
                elif isinstance(t, Player_cls):
                    if t is p:
                        ok = n in ("無中生有", "增兵減灶", "未雨綢繆")
                    elif self.tscore(g, p, t) > -100:
                        ok = (is_sha(real(c)) or n in ("順手牽羊", "過河拆橋", "樂不思蜀", "兵糧寸斷", "降雷", "火攻", "笑裡藏刀", "拋磚引玉")
                              or (n == "決鬥" and p.hp >= 2 and any(is_sha(h) for h in hand)))
                        if ok and self.atk_adj(g, p, c, t) <= -100:
                            ok = False
                if ok and n not in ("偽裝", "發憤圖強"):
                    seen.add(id(c))
                    out.append((-0.1, 170 if n in ("無中生有", "增兵減灶", "未雨綢繆") else 160, i, "曹仁-打掉" + c.color + n))
        # --- 呂布: 敵人有防具、殺夠多才發動「無效全場」; 發動後只出基本牌
        if cur == "呂布":
            for i, t in sk("呂布-無效全場"):
                k = sum(1 for c in hand if is_sha(c)) + (1 if any(fn(c) == "酒" for c in hand) else 0)
                for q in foes:
                    if q.armor_names() and k >= q.hp + round(len(q.hand) * 0.3) and k >= 2:
                        out.append((-1.5, 200, i, "呂布-無效全場"))
                        break
        if g.void and p is g.cur:
            out = [c for c in out if isinstance(card_of(c), SkillAct) or getattr(real(card_of(c)), "kind", "") == "basic"]
        # --- 鄧艾 / 曹沖在場或我是孟獲: 血少就先不出 (會扣血的) 錦囊
        others = [q._char.name for q in g.others(p) if q.alive]
        if ("鄧艾" in others or "曹沖" in others or me == "孟獲") and cur != "諸葛亮":
            safe = p.hp >= 3 or (p.hp == 2 and any(fn(c) == "閃" for c in hand))
            delay = {"樂不思蜀", "兵糧寸斷", "閃電", "毒", "草木皆兵"}

            def bad(c):
                cd = card_of(c)
                if isinstance(cd, SkillAct):
                    return False
                rc = real(cd)
                if getattr(cd, "kind", "") != "trick" or fn(rc) in delay:
                    return False
                if "鄧艾" in others and not safe:
                    return True
                if "曹沖" in others and g.tricks_this_turn(p) >= 1 and not safe:
                    return True
                return me == "孟獲" and p.hp <= 2
            out = [c for c in out if not bad(c)]
        return out

    AI_CHOOSE = (-1, 100)   # 武將內建的主動技能決策 (沿用第 3/4 級的 ai_choose): (bucket, pri)

    def char_act(self, g, p, options):
        if not self.AI_CHOOSE:
            return None
        r = p.char.ai_choose(g, p, options)
        if r is None:
            return None
        c = options[r][0]
        return (self.AI_CHOOSE[0], self.AI_CHOOSE[1], r, "技能:" + getattr(c, "name", ""))

    def best_target(self, g, p, card, idx_t):
        best, bs = None, -1e9
        if not self.adv("pick"):   # 3 級以下不挑最佳目標: 只排除「不能打 / 打了沒用」的,在剩下的敵人裡隨機選
            ok = [(i, t) for i, t in idx_t if hasattr(t, "hp") and self.tscore(g, p, t) > -100 and self.atk_adj(g, p, card, t) > -100]
            if not ok:
                return None
            i, t = g.rng.choice(ok)
            return i, self.tscore(g, p, t)
        for i, t in idx_t:
            if not hasattr(t, "hp"):
                continue
            ts = self.tscore(g, p, t)
            if ts <= -100:
                continue
            a = self.atk_adj(g, p, card, t)
            if a <= -100:
                continue
            if ts + a > bs:
                bs, best = ts + a, i
        return (best, bs) if best is not None else None

    def chain_plan(self, g, p):
        names = [fn(c) for c in p.hand]
        if "鐵索連環" not in names or "發憤圖強" not in names:
            return None
        k = min(5, p.hp - 1)
        if k < 2:
            return None
        cand = [q for q in self.foes_of(g, p) if q.hp <= k]
        return max(cand, key=lambda q: self.tscore(g, p, q)) if cand else None

    def chained_enemy(self, g, p):
        if not p.chained:
            return None
        c = [q for q in self.foes_of(g, p) if q.chained]
        return min(c, key=lambda q: q.hp) if c else None

    def skill_cand(self, g, p, sk, idx_t, foes, keep_floor):
        """武將主動技能 (包含丈八蛇矛): 沿用內建的 ai_choose,再依優先度規則過濾。"""
        n = sk.name
        hand = p.hand
        i0 = idx_t[0][0]
        if n == "丈八蛇矛-雙牌當殺":
            if not foes or len(hand) < 2:
                return None
            v = sorted(self.keep_val(g, p, c) for c in hand)
            if not (v[0] < self.pri["殺"] and v[1] < self.pri["殺"]):
                return None
            r = self.best_target(g, p, _FakeSha, idx_t)
            return (5, 60, r[0], n) if r else None
        return None   # 其他武將技能交給 ai_choose (在 act 外層處理)

    def card_cand(self, g, p, c, idx_t, foes, b, cs, hurt, sbr, chain_plan, chained, combo_on, killable, lord, lord_low):
        n = fn(real(c))
        hand = p.hand
        first = idx_t[0][0]
        kind = real(c).kind if hasattr(real(c), "kind") else ""
        tgt_players = [(i, t) for i, t in idx_t if hasattr(t, "hp")]
        # ---- 抽牌 / 回血 / 爆發準備
        if n == "桃":
            return (3, 100, first, n) if hurt else None
        if n == "發憤圖強":
            return (0, 97, first, n)
        if n == "鐵索連環":
            return (5, 98 if chain_plan else (22 if len(hand) <= 6 else 0), first, n)
        if n == "無中生有":
            return (2, 96, first, n)
        if n == "增兵減灶":
            return (2, 90 if len(hand) <= 7 else 25, first, n)
        if n == "未雨綢繆":
            return (2, 85, first, n)
        if n == "五穀豐登":
            return (2, 55, first, n)
        if n == "桃園結義":
            fr = sum(1 for q in g.alive_players() if q.hp < q.maxhp and self.attitude(g, p, q) >= 0)
            fo = sum(1 for q in g.alive_players() if q.hp < q.maxhp and self.attitude(g, p, q) < 0)
            return (3, 70 if (hurt and fr >= fo) else (60 if fr > fo else 8), first, n)
        if n == "酒":
            heal = [i for i, t in idx_t if t == "heal"]
            if heal and p.hp <= p.maxhp - 2:
                return (3, 95, heal[0], n)
            plain = [i for i, t in idx_t if t != "heal"]
            if plain and cs >= 1 and foes and not combo_on:
                return (5, 79.5, plain[0], n)
            return None
        if n == "強化":
            if foes and (b["n"] >= 1 or sbr):
                mine = [i for i, t in tgt_players if t is p]
                if mine:
                    pri = 99 if sbr else (91 if (killable or b["buff"] >= 1 or self._lethal) else 0)
                    return (3, pri, mine[0], n) if pri else None
            return None
        if n == "降雷":
            r = self.best_target(g, p, c, tgt_players)
            return (5, 40, r[0], n) if r else None
        if n == "出其不意":
            if not p.judge:
                return None
            for i, t in idx_t:
                if isinstance(t, tuple) and t[0] is p and t[1].name in ("樂", "兵", "毒", "閃電", "草") and self.attitude(g, p, t[2]) < 0:
                    return (5, 77, i, n)
            return None
        if n == "轉移":
            r = self.best_target(g, p, c, tgt_players)
            if r:
                t = dict(tgt_players)[r[0]]
                if (t.equip["weapon"] or t.equip["armor"]) and not p.equip["weapon"] and not p.equip["armor"]:
                    return (5, 45, r[0], n)
            return None
        if n == "投桃報李":
            ally = [(i, t) for i, t in tgt_players if self.attitude(g, p, t) >= 1]
            if ally:
                best = max(ally, key=lambda it: self.attitude(g, p, it[1]) - it[1].hp * 0.1)
                return (5, 35, best[0], n)
            return None
        if n in ("閃電", "偽裝"):
            return None
        if n in ("反擊", "調虎離山", "占卜", "無懈可擊", "隔岸觀火", "孤注一擲", "弱化", "坐收漁利"):   # 坐收漁利: 只在敵人回合開始時用 (ai.py choose_offturn)
            return None
        # ---- 裝備
        sl = slot_of(real(c))
        if sl:
            if sl == "armor" and p._char.name == "典韋":
                return None
            cur = self.equipped(p, sl)
            if not cur or (len(cur) < 1):
                return (1, 90 + self.keep_val(g, p, c) / 1000.0, first, n)
            # 空欄位 (雙欄武將只裝了一件) 或比已裝備的更好才換
            two = sl in ("weapon", "armor") and p._char.name in (DUAL_W if sl == "weapon" else DUAL_A)
            slots = [sl, sl + "2"] if two else [sl]
            if any(p.equip.get(s) is None for s in slots):
                return (1, 90 + self.keep_val(g, p, c) / 1000.0, first, n)
            worst = min(self.base_pri(x) for x in cur)
            if self.keep_val(g, p, c) > worst:
                return (1, 90 + self.keep_val(g, p, c) / 1000.0, first, n)
            return None
        # ---- 攻擊牌 / 單一目標
        if tgt_players and n not in AOE:
            r = self.best_target(g, p, c, tgt_players)
            if not r:
                return None
            i, sc = r
            t = dict(tgt_players)[i]
            hp = t.hp
            if is_sha(real(c)):
                pri = 80 + (5 if hp <= 1 else 0)
            elif n == "決鬥":
                pri = 78 if cs >= 1 else 30
            elif n == "火攻":
                pri = 72 if len(hand) >= 3 else 35
            elif n in ("過河拆橋", "順手牽羊"):
                pri = 74
            elif n in ("樂不思蜀", "兵糧寸斷", "毒", "草木皆兵"):
                pri = 73
            elif n == "拋磚引玉":
                pri = 50
            elif n == "鴻門宴":
                pri = 45
            elif n == "笑裡藏刀":
                pri = (70 if hp <= 1 else 38) if len(hand) >= 3 else 0
            elif n == "借刀殺人":
                pri = 30
            elif n == "聲東擊西":
                pri = 20
            else:
                pri = 25
            if self._lethal and lord is not None and t is lord and re.search(r"殺|決鬥|火攻|笑裡藏刀", n):
                pri += 12
            return (5, pri, i, n)
        # 方天畫戟: 殺指定多人 (目標是 tuple)
        if is_sha(real(c)) and any(isinstance(t, tuple) for _, t in idx_t):
            best, bs = None, -1e9
            for i, t in idx_t:
                if isinstance(t, tuple):
                    if any(self.tscore(g, p, x) <= -100 or self.atk_adj(g, p, c, x) <= -100 for x in t):
                        continue
                    s = sum(self.tscore(g, p, x) for x in t)
                    if s > bs:
                        bs, best = s, i
            if best is not None:
                return (5, 83, best, n)
            return None
        if n in AOE:
            hits_ally = p.role != "反賊" and lord is not None and lord.alive
            hit = [q for q in foes if self.atk_adj(g, p, c, q) > -100]
            pri = 68 if hit and not (hits_ally and lord_low) else 0
            if self._lethal and p.role == "反賊":
                pri += 12 if pri else 0
            return (5, pri, first, n) if pri else None
        if n in ("聲東擊西", "借刀殺人", "出其不意"):
            return None
        return (5, 10, first, n)

    # ------------------------------------------------------------ 棄牌 / 取牌 / 給牌
    def choose_discard(self, g, p, n, cands, msg=None):
        if p._char.name == "曹仁" and len({c.color for c in p.hand}) > 1 and all(c in p.hand for c in cands):
            keep = self.keep_color(g, p)
            return sorted(cands, key=lambda c: (c.color == keep, self.keep_val(g, p, c)))[:n]
        return sorted(cands, key=self.kv(g, p))[:n]

    def pick_pile(self, g, p, pile):
        return max(pile, key=self.kv(g, p))

    def choose_from(self, g, p, target, cands):
        equips = [c for c in cands if c != "HAND"]
        best = max(equips, key=self.kv(g, p), default=None)
        if best is not None and (self.keep_val(g, p, best) >= 60 or "HAND" not in cands):
            return best
        return "HAND" if "HAND" in cands else best

    def choose_offturn(self, g, p, options, cur, when):
        if not self.adv("bolt"):   # 1 級不用 ⚡ 連鎖牌 (弱化 / 強化 / 降雷 / 坐收漁利 …)
            return None
        return super().choose_offturn(g, p, options, cur, when)

    def choose_skill(self, g, p, skill):
        if skill == "貫石斧-強中":
            return True
        if skill == "寒冰劍-棄牌":
            return False
        if skill == "司馬懿-奪牌":   # 手牌 > 3 發動; 單挑且對方手牌至少 2 張也發動
            others = g.others(p)
            duel = len(g.alive_players()) == 2 and bool(others) and len(others[0].hand) >= 2
            return len(p.hand) > 3 or duel
        if skill == "周倉-再抽牌":   # 敵人血 1 且殺得到 / 急需回血 / 單挑 → 不再抽, 其餘一律再抽
            if len(g.alive_players()) == 2:
                return False
            if p.hp <= 2 and any(c.name == "桃" for c in p.hand):
                return False
            for q in self.foes_of(g, p):
                if q.hp == 1 and q._char.name != "蔣幹" and (p._char.name == "孫策" or g.distance(p, q) <= p.attack_range()):
                    return False
            return True
        if skill in ("曹沖-交換武將", "曹真-阻擋", "沮授-轉移"):
            return True
        return super().choose_skill(g, p, skill)

    def choose_count(self, g, p, skill, maxn):
        if skill == "孔融-重鑄手牌":   # 除了一定要留的牌, 盡量重鑄越多越好
            must = sum(1 for c in p.hand if fn(c) in ("發憤圖強", "偽裝", "反擊", "調虎離山"))
            return max(1, min(maxn, len(p.hand) - must))
        if skill == "周魴-棄牌扣血":
            foes = sorted(self.foes_of(g, p), key=lambda q: q.hp)
            x = min(3, foes[0].hp) if foes else 3
            return max(1, min(maxn, x))
        return super().choose_count(g, p, skill, maxn)

    # ------------------------------------------------------------ 響應
    def respond(self, g, p, need, cands, ctx):
        if need in ("殺", "閃", "火攻", "借刀殺人", "青龍追擊") and cands:
            if need == "借刀殺人" and self.attitude(g, p, ctx["victim"]) >= 0:
                return None
            if need in ("殺", "閃", "火攻", "青龍追擊"):
                return min(cands, key=self.kv(g, p))
        if need in ("趙雲棄牌", "劉協棄牌", "夏侯淵給牌", "袁術棄牌", "韓當棄牌") and cands:
            low = min(cands, key=self.kv(g, p))
            return low if (self.keep_val(g, p, low) <= 75 or p.hp <= 1) else None
        if need == "無懈" and ctx.get("source") is p and p._char.name != "諸葛亮":
            return None
        if need == "受傷響應":
            return self.react_damage(g, p, cands, ctx) if self.adv("bolt") else None
        if (need == "桃" and p.role == "內奸" and self.spy and self.spy.get("nosave", 1) and self.adv("combo")
                and ctx.get("target") not in (None, p, g.lord)):
            return None   # 內奸的桃只留給自己和主公 (不救假裝的隊友)
        return super().respond(g, p, need, cands, ctx)

    def react_damage(self, g, p, cands, ctx):
        by = {}
        for c in cands:
            by.setdefault(c.name, c)
        n, src = ctx["n"], ctx.get("src")
        foes = self.foes_of(g, p)
        names = [fn(c) for c in p.hand]
        self_hit = g.cur is p
        if src is None and getattr(self, "_fa_reflect", None) == p.idx:
            self._fa_reflect = None
            for k in ("反", "調"):
                if k in by:
                    return by[k]
        lethal = n >= p.hp
        if p._char.name == "蔣幹" and foes:
            others = [c for c in cands if c.name not in ("占", "反", "調")]
            for k in ("反", "調"):
                if k in by:
                    return by[k]
            return min(others, key=self.kv(g, p)) if others else None
        if sum(p.fa_debt or [0]) > 0 and g.cur is p and self.redirect_cnt(p) <= 1 and n < p.hp and p._char.name != "蔣幹":
            return None
        plan_hold = "發憤圖強" in names and ("反擊" in names or "調虎離山" in names)
        if plan_hold and not lethal and not self_hit:
            return None   # 留著轉傷牌做爆發, 硬吃
        for k in ("反", "調"):
            if k in by and foes and (n >= 2 or lethal or self_hit):
                return by[k]
        if "占" in by and lethal:
            return by["占"]
        if p.hp - n <= 1 and not foes:
            for k in ("占", "反", "調"):
                if k in by:
                    return by[k]
        if p._char.name == "陳群" and p.hp - n <= 1:
            others = [c for c in cands if c.name not in ("占", "反", "調")]
            if others:
                return min(others, key=self.kv(g, p))
        return None

    # ------------------------------------------------------------ 發憤圖強
    BORROW_PREF = ("劉協", "典韋", "曹植", "諸葛亮", "劉禪", "孔融", "曹真", "董卓", "華雄", "龐統", "蔣幹", "陳群", "許褚", "張角", "曹彰", "劉諶", "張昭", "鄧艾", "呂布")

    def pick_borrow(self, g, p, cands, skill):
        """馬謖 / 陳群 / 韓當借技能: 照優先名單挑, 名單上都沒有就挑血最多的。"""
        order = {nm: i for i, nm in enumerate(self.BORROW_PREF)}
        best = min(cands, key=lambda q: order.get(q._char.name, 99))
        return best if best._char.name in order else max(cands, key=lambda q: q.hp)

    def choose_x(self, g, p):
        return 5 if self.adv("combo") else 2 if p.hp >= 3 else 1

    def choose_option(self, g, p, skill, labels):
        if skill == "發憤圖強-少棄" and not self.adv("combo"):
            return 0   # 4 級以下不玩「少棄牌吃傷害再轉給敵人」的爆發
        if skill == "發憤圖強-少棄":
            ks = []
            for lb in labels:
                m = re.search(r"扣 (\d+) 點", lb)
                ks.append(int(m.group(1)) if m else 0)
            max_k = max(ks)
            red = self.redirect_cnt(p)
            backup = sum(1 for c in p.hand if fn(c) in ("占卜", "桃"))
            chained = self.chained_enemy(g, p)
            self._fa_reflect = None
            k = 0
            if chained:
                k = min(max_k, p.hp - 1)
            elif red > 0 and self.foes_of(g, p):
                if p._char.name == "蔣幹":
                    k = max_k if len(p.hand) >= 3 else 0
                else:
                    k = max_k if (red >= 2 or backup >= 1 or p.hp > max_k) else min(max_k, p.hp - 1)
            k = max(0, min(k, max_k, max(0, p.hp - 1) if p._char.name != "蔣幹" else max_k))
            best = max((i for i, kk in enumerate(ks) if kk <= k), key=lambda i: ks[i], default=0)
            if ks[best] > 0:
                self._fa_reflect = p.idx
            return best
        if skill == "偽裝" and self._dg_want and self._dg_want[0] == g.turn_id and self._dg_want[1] in labels:
            return labels.index(self._dg_want[1])
        return super().choose_option(g, p, skill, labels)


class _FakeSha:
    """best_target 用的假殺 (丈八蛇矛合成的殺無色, 不被仁王盾擋)。"""
    name = "殺"
    color = ""
    nature = None
    kind = "basic"


_FakeSha = _FakeSha()


from strategy_agent import attach_strategies   # noqa: E402  武將專屬策略 (strategies/<武將名>.py) 掛上來
attach_strategies(ProAgent)
