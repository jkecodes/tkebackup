"""AI 代理介面。其他代理只要實作同樣的方法即可接上。

act(g, p, options)               -> options 的索引,或 None 結束出牌
respond(g, p, need, cands, ctx)  -> cands 中的一張牌,或 None (不出)
choose_discard(g, p, n, cands)   -> 要棄的牌 list
choose_from(g, p, target, cands) -> cands 中的一項 ("HAND" 代表對方手牌隨機一張)
show_card(g, p, hand)            -> 火攻時要展示的手牌
choose_target(g, p, kind, cands) -> 反/... 要選的玩家
choose_dir(g, p)                 -> 'L' / 'R' (突襲、調虎離山的結算方向)
choose_x(g, p)                   -> 發憤圖強要抽的張數 1~5
choose_chain(g, p)               -> 鐵索連環要橫置的玩家 list (空 = 重鑄)
pick_pile(g, p, pile)            -> 五穀豐登要拿的牌
"""
import re


class RandomAgent:
    def choose_offturn(self, g, p, options, cur, when):
        return None

    def choose_option(self, g, p, skill, labels):
        if skill == "輪次方向":
            return g.rng.randrange(2)
        if skill in ("發憤圖強-少棄", "換裝"):
            return 0
        if skill.startswith("留下哪一件"):
            from cards import WEAPON_RANGE
            rs = [WEAPON_RANGE.get(x.split()[1][1:], 0) for x in labels]
            return rs.index(max(rs))
        return g.rng.randrange(len(labels))

    def act(self, g, p, options):
        if g.rng.random() < 0.2:
            return None
        return g.rng.randrange(len(options))

    def respond(self, g, p, need, cands, ctx):
        return cands[0] if g.rng.random() < 0.7 else None

    def choose_discard(self, g, p, n, cands, msg=None):
        return g.rng.sample(cands, n)

    def choose_from(self, g, p, target, cands):
        return g.rng.choice(cands)

    def show_card(self, g, p, hand):
        return g.rng.choice(hand)

    def choose_target(self, g, p, kind, cands):
        return g.rng.choice(cands)

    def choose_dir(self, g, p):
        return g.rng.choice("LR")

    def choose_x(self, g, p):
        return g.rng.randint(1, 5)

    def choose_chain(self, g, p):
        others = g.alive_players()
        return g.rng.sample(others, 2) if len(others) >= 2 and g.rng.random() < 0.5 else []

    def pick_pile(self, g, p, pile):
        return g.rng.choice(pile)

    # 偽裝選武將: 依手牌情境查表 (殺張數 / 有無南蠻萬箭 / 血量 / 手牌數)。實測整體最好的是張角、孔融、司馬昭、李儒、曹仁、周魴;
    # 殺多偏殺類武將,低血偏回血武將,有南蠻萬箭偏鄧艾。實測最差 (孟獲 / 黃蓋 / 袁術 / 董卓 / 公孫淵) 和淨少牌的伊籍不選。
    DG_BASE = ("張角", "孔融", "司馬昭", "李儒", "曹仁", "周魴")
    DG_BAD = ("孟獲", "黃蓋", "袁術", "董卓", "公孫淵", "伊籍")

    def _dg_rank(self, p):
        n_sha = sum(1 for c in p.hand if c.name in ("殺", "火殺", "冰殺", "雷殺"))
        aoe = any(c.name in ("南", "萬", "南蠻入侵", "萬箭齊發") for c in p.hand)
        order = []
        if aoe:
            order.append("鄧艾")
        if n_sha >= 2:
            order += ["許褚", "張飛", "周倉"]
        if p.hp <= 2:
            order += ["張角", "孔融", "華佗", "劉備"]
        order += self.DG_BASE
        return list(dict.fromkeys(order))

    def _best_disguise(self, g, p, names):
        """偽裝只持續一回合: 先照情境名次表挑第一個「場上還沒有的」,表上的人都不能選才退回原本的評分。"""
        for nm in self._dg_rank(p):
            if nm in names:
                return names.index(nm)
        sc = self._disguise_scores(g, p, names)
        best = max(names, key=lambda nm: sc.get(nm, 0) - (4 if nm in self.DG_BAD else 0) + 1.5 * g.rng.random())   # 加一點隨機,避免每次都選同一個
        return names.index(best)

    def _disguise_scores(self, g, p, names):
        n_sha = sum(1 for c in p.hand if c.name in ("殺", "火殺", "冰殺", "雷殺"))
        n_aoe = sum(1 for c in p.hand if c.name in ("南", "萬", "南蠻入侵", "萬箭齊發"))
        foes = self.foes(g, p, -0.5)
        hp, hn = p.hp, len(p.hand)
        big = max((len(q.hand) for q in g.others(p)), default=0)
        sc = {}
        def add(nm, v):
            sc[nm] = sc.get(nm, 0) + v
        for nm in ("曹彰", "許褚", "張遼", "劉諶", "司馬昭", "夏侯惇", "呂布"):   # 殺類爆發
            add(nm, 1.5 * min(n_sha, 3))
        add("曹彰", 3 if n_sha >= 2 else -2)
        add("許褚", 3 if n_sha >= 2 and foes else -2)
        add("張遼", 4 if n_sha >= 2 and len(foes) >= 3 else (1 if n_sha and len(foes) >= 2 else 0))   # 張遼要殺多、敵人多才真的賺
        add("劉諶", 2 if hn >= 3 and foes else 0)
        add("鄧艾", 5 * min(n_aoe, 1) + (-3 if not n_aoe else 0))
        if hp <= 2:
            for nm in ("伊籍", "劉備", "華佗", "荀彧", "張角", "曹洪", "曹仁"):
                add(nm, 4)
        if hn <= 2:
            for nm in ("司馬懿", "曹操", "吳懿", "曹休", "郭嘉", "崔琰", "荀彧"):
                add(nm, 2)
            add("司馬懿", 2 if big >= 3 else 0)
            add("吳懿", 3 if big >= 4 else 0)
        else:
            add("伊籍", 1.5)
        over = hn - max(hp, 0)   # 手牌比上限多幾張: 偽裝成回合結束不用棄牌的武將,省下白白丟掉的牌
        if over > 0:
            b = 2 + min(over, 4)
            for nm in ("孟獲", "伊籍", "呂布"):
                add(nm, b)
            add("呂蒙", b if g.sha_used == 0 else -1)
        if hn >= 5:
            add("劉禪", 1); add("曹植", 1)
        add("張郃", 2 if hn == 0 else -1)
        for nm in ("曹丕", "楊修", "孟獲", "左慈", "甘寧", "王允", "鍾繇"):   # 泛用好用
            add(nm, 1)
        return sc

    def choose_skill(self, g, p, skill):
        return g.rng.random() < 0.5

    def choose_mode(self, g, p, skill, tgt):
        return g.rng.choice(["discard", "damage"])

    def choose_give(self, g, p, drawn, others):
        if g.rng.random() < 0.3:
            return g.rng.choice(others), [g.rng.choice(drawn)]
        return None

    def choose_count(self, g, p, skill, maxn):
        return g.rng.randint(1, max(1, maxn))


CARD_VALUE = {"桃": 10, "無": 9, "無懈": 8, "閃": 7, "殺": 6, "酒": 4, "占": 7, "反": 7, "調": 6, "隔": 5}


def true_att(g, me, other):
    """用真實身分判斷敵友 (全部身分公開模式)。"""
    r, o = me.role, other.role
    if r in ("主公", "忠臣"):
        return 5 if o in ("主公", "忠臣") else (-3 if o == "反賊" else -1.5)
    if r == "反賊":
        return -4 if o == "主公" else (3 if o == "反賊" else (-1.5 if o == "忠臣" else -0.5))
    alive = g.alive_players()   # 內奸: 先清反賊,再清忠臣,最後打主公
    rebels = [q for q in alive if q.role == "反賊"]
    if o == "主公":
        return 1.5 if len(alive) > 2 else -3
    return -2 if (o == "反賊" or not rebels) else -0.3


class HeuristicAgent(RandomAgent):
    """只用自己看得到的資訊: 自己的身分、主公公開、死亡者身分、誰攻擊過主公。"""

    def __init__(self):
        self.sus = {}     # 玩家 idx -> 疑似反賊程度 (正=像反賊/與主公為敵, 負=像忠臣/護主)
        self.grudge = {}  # 玩家 idx -> 傷害過我的次數

    def observe(self, g, me, kind, src, tgt):
        """從公開行為更新身分判斷。只用任何玩家都看得到的資訊。"""
        if src is None or src is tgt or src is me:
            return
        s, lord = self.sus, (None if getattr(g, "hidden_lord", False) else g.lord)   # 主公不公開時,別人不知道誰是主公
        s.setdefault(src.idx, 0.0)
        s.setdefault(tgt.idx, 0.0)
        if kind in ("attack", "hurt"):
            w = 1.0 if kind == "attack" else 0.4
            if tgt is lord:
                s[src.idx] += 3.0 * w
            elif s[tgt.idx] >= 1.5:     # 打可疑的人 -> 像忠臣
                s[src.idx] -= 1.0 * w
            elif s[tgt.idx] <= -1.5:    # 打疑似忠臣的人 -> 像反賊
                s[src.idx] += 1.0 * w
            if tgt is me:
                self.grudge[src.idx] = self.grudge.get(src.idx, 0) + 1
        elif kind == "help":
            if tgt is lord:
                s[src.idx] -= 2.0
            elif s[tgt.idx] >= 1.5:
                s[src.idx] += 0.7
            elif s[tgt.idx] <= -1.5:
                s[src.idx] -= 0.7
        elif kind == "kill":
            if tgt.role == "反賊":
                s[src.idx] -= 2.0
            elif tgt.role == "忠臣":
                s[src.idx] += 2.5
        s[src.idx] = max(-6.0, min(6.0, s[src.idx]))

    # --- 態度: >0 友, <0 敵 ---
    # 模擬 6000 局統計勝率明顯偏高的武將: 對不是確定隊友的人,多提高一點攻擊優先度 (數字越大越想先處理)
    THREAT = {"司馬昭": 0.6, "曹真": 0.6, "孔融": 0.5, "呂蒙": 0.5,
              "劉協": 0.4, "典韋": 0.4, "周魴": 0.4, "沮授": 0.3}

    def attitude(self, g, me, other):
        a = self._att(g, me, other)
        if other is not me and a < 2.5:
            a -= self.THREAT.get(other._char.name, 0.0)
            if other._char.name == "龐統":   # 瀕死會滿血復活,正面朝上時打他是白費力氣;翻面期間 (技能失效) 才是殺他的機會
                a += -1.5 if other.flipped else 0.7
        return a

    def _att(self, g, me, other):
        if other is me:
            return 5
        if me.role == "無":   # 2~3 人無身分: 所有人都是敵人
            return -3
        if getattr(g, "role_mode", "") == "open":   # 全部身分公開: 直接用真實身分
            return true_att(g, me, other)
        r = me.role
        hid = getattr(g, "hidden_lord", False)   # 主公不公開: 沒人知道誰是主公,只能靠行為推理
        s = self.sus.get(other.idx, 0.0)
        known = g.revealed.get(other.idx)
        grudge = -0.7 * min(2, self.grudge.get(other.idx, 0))
        if r in ("主公", "忠臣"):
            if other.role == "主公" and not hid:
                return 5
            if known == "忠臣":
                return 5 if r == "主公" else 3
            return -0.3 - 0.8 * s + grudge  # 預設略懷疑,越像反賊越是敵人
        if r == "反賊":
            if other.role == "主公" and not hid:
                return -4
            return 0.8 * s - 0.2 + grudge * 0.5  # 打過主公的視為同伴
        # 內奸: 先留著主公,先清反賊,最後再對主公
        alive = g.alive_players()
        rebels_left = any(self.sus.get(q.idx, 0) >= 1.5 for q in alive if q is not me)  # 只看公開行為的推理
        if other.role == "主公" and not hid:
            return 1.5 if len(alive) > 2 else -3
        if s >= 1.5:
            return -1.5 + grudge   # 疑似反賊: 優先打
        if s <= -1.5:
            return (-0.3 if rebels_left else -1.2) + grudge  # 疑似忠臣: 反賊清完才打
        return -0.4 + grudge

    def foes(self, g, me, thresh=-1.0):
        return [q for q in g.others(me) if self.attitude(g, me, q) <= thresh]

    def val(self, c):
        return CARD_VALUE.get(c.name, 3 if c.kind == "trick" else 2)

    def _counter_prio(self, card_name, t):
        """針對勝率偏高的武將 (0 = 優先): 華雄一次抽 5 張 -> 兵糧/樂不思蜀先壓他;孔融靠手牌重鑄回血抽牌 -> 順手/過河先拆他的手牌;
        司馬昭每個錦囊都讓他判定賺到牌 -> 同樣先用延時錦囊 / 拆牌壓他。"""
        if isinstance(t, tuple):
            return 1
        nm = t._char.name
        if card_name in ("兵", "樂") and nm in ("司馬昭", "孔融"):
            return 0
        if card_name in ("順", "過", "火攻") and nm == "孔融" and len(t.hand) >= 2:
            return 0
        return 1

    FUTILE_DMG = {"殺", "火殺", "冰殺", "雷殺", "決", "火攻", "南", "萬", "突"}

    NO_FEED = {"五", "飢", "桃園", "未", "發"}   # 有司馬昭 (敵人) 在場時,這些不急的錦囊不要隨便出 (每個錦囊都讓他判定賺到牌)

    def act(self, g, p, options):
        """被「弱」之後,造成的傷害 ÷2 捨去: 1 點傷害的牌打出去等於 0,不要浪費。"""
        if p.dmg_half > p.dmg_x2 + (1 if g.jiu else 0):
            keep = [i for i, (c, t) in enumerate(options) if getattr(c, "name", "") not in self.FUTILE_DMG]
            if len(keep) < len(options):
                if not keep:
                    return None
                r = self._act_core(g, p, [options[i] for i in keep])
                return None if r is None else keep[r]
        sm = [q for q in g.alive_players() if q is not p and q._char.name == "司馬昭" and self.attitude(g, p, q) < 0]
        if sm and len(p.hand) <= p.hp + 1:
            keep = [i for i, (c, t) in enumerate(options) if getattr(c, "name", "") not in self.NO_FEED]
            if 0 < len(keep) < len(options):
                r = self._act_core(g, p, [options[i] for i in keep])
                return None if r is None else keep[r]
        return self._act_core(g, p, options)

    def _act_core(self, g, p, options):
        r = p.char.ai_choose(g, p, options)  # 武將主動技能
        if r is not None:
            return r

        def idxs(name):
            return [i for i, (c, t) in enumerate(options) if c.name == name]

        att = lambda q: max(self.attitude(g, p, x) for x in q) if isinstance(q, tuple) else self.attitude(g, p, q)
        hpof = lambda q: min(x.hp for x in q) if isinstance(q, tuple) else q.hp
        low = p.hp <= 2
        nsha = sum(1 for c in p.hand if c.name == "殺")

        ids = idxs("桃")
        if ids and p.hp < p.maxhp and (low or len(p.hand) > p.hp + 1):
            return ids[0]
        for i in idxs("降雷"):   # 劉備存了很多仁 (3 個就殺不到他): 降雷把他翻面,仁就全部消失
            t = options[i][1]
            if hasattr(t, "hp") and t is not p and t._char.name == "劉備" and getattr(t._char, "ren", 0) >= 2 and not t.flipped and att(t) < 1:
                return i
        for i in idxs("降雷"):   # 針對龐統: 先降雷把他翻面 (瀕死復活失效),本回合殺得死才這麼做
            t = options[i][1]
            if hasattr(t, "hp") and t._char.name == "龐統" and not t.flipped and att(t) < 2.5 and t is not p:
                if t.hp <= nsha + (1 if g.jiu else 0) + sum(1 for c in p.hand if c.name in ("決", "火攻")):
                    return i
        for i, (c, t) in enumerate(options):  # 空裝備欄先裝
            if c.kind in ("weapon", "armor", "horse"):
                slot = c.kind if c.kind != "horse" else ("h+" if c.name == "+1馬" else "h-")
                if p.equip[slot] is None:
                    return i
        if (p.dg_flip if p.disguise else p.flipped):   # 被降雷翻面: 偽裝成新武將就是正面,技能恢復
            ids = idxs("偽")
            if ids:
                return ids[0]
        for n in ("無", "增", "偽"):
            ids = idxs(n)
            if ids:
                return ids[0]
        if len(p.hand) <= 3:
            for n in ("未", "發"):
                ids = idxs(n)
                if ids:
                    return ids[0]
        for n in ("五", "鐵"):
            ids = idxs(n)
            if ids:
                return ids[0]
        ids = idxs("投")
        ids = [i for i in ids if att(options[i][1]) >= 1]
        if ids:
            return ids[0]
        ids = idxs("桃園")
        if ids:
            fr = sum(1 for q in g.alive_players() if q.hp < q.maxhp and att(q) >= 0)
            fo = sum(1 for q in g.alive_players() if q.hp < q.maxhp and att(q) < 0)
            if fr > fo:
                return ids[0]
        for n in ("南", "萬", "突", "飢"):
            ids = idxs(n)
            if ids and p.hp > 1:
                fo = len(self.foes(g, p, -0.5))
                fr = sum(1 for q in g.others(p) if att(q) >= 1)
                if fo > fr:
                    return ids[0]
        ids = idxs("孤")
        if ids and p.hp < p.maxhp and len(p.hand) <= 3 and p.hp <= 2:
            return ids[0]
        ids = idxs("閃電")
        if ids and p.hp >= 3:
            return ids[0]
        # 出: 把延時錦囊(壞的)從自己/友人移到敵人
        for i in idxs("出"):
            owner, d, dest = options[i][1]
            if d.name in ("樂", "兵", "毒", "閃電") and (owner is p or att(owner) >= 1) and att(dest) < 0:
                return i
        # 強: 先對要打的敵人上強化
        if nsha:
            for i in idxs("強"):
                if options[i][1] is p:   # 強: 替自己上強化,這回合打出的傷害 x2
                    return i
        # 借
        for i in idxs("借"):
            t, v = options[i][1]
            if att(t) < 0 and att(v) < 0:
                return i
        # 轉: 自己沒防具且對方有
        for i in idxs("轉"):
            t = options[i][1]
            if att(t) < 0 and not p.equip["armor"] and t.equip["armor"]:
                return i
        heal_jiu = [i for i in idxs("酒") if options[i][1] == "heal"]
        if heal_jiu and p.hp <= p.maxhp - 2:
            return heal_jiu[0]
        jiu = [i for i in idxs("酒") if options[i][1] != "heal"]
        sha = [i for i in idxs("殺") if att(options[i][1]) < 0]
        first = ("樂", "兵", "毒", "草", "火攻", "拋", "鴻", "笑", "順", "過", "決")   # 這些比殺優先: 酒打出去之後下一張會先打它們,酒就白白浪費了
        if jiu and sha and g.rng.random() < 0.5 and not any(att(options[i][1]) < 0 for n in first for i in idxs(n)):   # 只有「下一張真的打殺」才先喝酒,不再無緣無故單獨打一張酒
            return jiu[0]
        for n in ("樂", "兵", "毒", "草", "火攻", "拋", "鴻", "笑", "順", "過", "決", "殺"):
            ids = [i for i in idxs(n) if att(options[i][1]) < 0]
            if n == "決":
                ids = [i for i in ids if nsha > 1 or options[i][1].hp <= 1]
            if n == "笑":
                ids = [i for i in ids if len(p.hand) >= 3]
            if ids:
                return min(ids, key=lambda i: (self._counter_prio(n, options[i][1]), hpof(options[i][1])))
        zb = idxs("丈八蛇矛-雙牌當殺")  # 丈八蛇矛: 手牌太多時,兩張雜牌當殺打敵人
        zb = [i for i in zb if att(options[i][1]) < 0]
        if zb and len(p.hand) > p.hp + 1 and not idxs("殺"):
            return min(zb, key=lambda i: hpof(options[i][1]))
        if len(p.hand) > p.hp + 1:  # 手牌太多: 隨機砍非友人
            cand = [i for i in idxs("殺") if att(options[i][1]) < 1.0]
            if cand:
                return g.rng.choice(cand)
        return None

    def respond(self, g, p, need, cands, ctx):
        att = lambda q: self.attitude(g, p, q)
        if need == "桃":
            if "target" not in ctx:  # 飢: 血少才出桃
                return cands[0] if p.hp <= 2 else None
            tgt = ctx["target"]
            if tgt is p:
                return cands[0]
            if p.role == "內奸" and tgt.role == "主公" and len(g.alive_players()) <= 2:
                return None
            return cands[0] if att(tgt) >= 0.5 else None
        if need == "無懈":
            tgt, src, harmful = ctx["target"], ctx["source"], ctx["harmful"]
            a = (sum(att(t) for t in ctx["targets"]) / len(ctx["targets"])) if ctx.get("targets") else att(tgt)
            s = att(src) if src is not None else 0
            if ctx["negated"]:
                if harmful and a < 0 and s >= 0:
                    return cands[0]
                return None
            if harmful and a >= 1 and s < 0:
                return cands[0]
            if not harmful and a < 0 and tgt is not p and not ctx.get("targets"):
                return cands[0]
            return None
        if need == "受傷響應":
            by = {c.name: c for c in cands}
            n = ctx["n"]
            if ctx.get("src") is None and getattr(self, "_fa_reflect", None) == p.idx:   # 發憤圖強少棄的傷害: 轉給敵人
                self._fa_reflect = None
                for k in ("反", "調"):
                    if k in by:
                        return by[k]
            if p.hp - n <= 1:
                for k in ("占", "反", "調"):
                    if k in by:
                        return by[k]
                others = [c for c in cands if c.name not in ("占", "反", "調")]   # 陳群 1 血 / 蔣幹: 手牌當占卜 / 調虎離山
                if others:
                    return min(others, key=self.val)
            elif "調" in by and len(self.foes(g, p, -0.5)) >= 2:
                return by["調"]
            return None
        if need == "隔":
            return cands[0]
        if need == "張遼-八卦陣":  # 沒有閃時才犧牲低價值的紅牌
            low = min(cands, key=self.val)
            return low if self.val(low) <= 6 else None
        if need == "張遼-仁王盾":
            low = min(cands, key=self.val)
            return low if (self.val(low) <= 3 or p.hp <= 2) else None
        if need in ("趙雲棄牌", "劉協棄牌", "夏侯淵給牌", "袁術棄牌", "韓當棄牌"):  # 手牌不重要就棄,血少時一定棄
            low = min(cands, key=self.val)
            return low if (self.val(low) <= 3 or p.hp <= 1) else None
        if need == "借刀殺人":
            return cands[0] if att(ctx["victim"]) < 0 else None
        return cands[0]  # 殺 / 閃 / 火攻: 能出就出

    def choose_discard(self, g, p, n, cands, msg=None):
        return sorted(cands, key=self.val)[:n]

    def choose_from(self, g, p, target, cands):
        equips = [c for c in cands if c != "HAND"]
        if equips and ("HAND" not in cands or g.rng.random() < 0.5):
            return g.rng.choice(equips)
        return "HAND"

    def choose_target(self, g, p, kind, cands):
        return min(cands, key=lambda q: (self.attitude(g, p, q), q.hp))

    def choose_x(self, g, p):
        return 2 if p.hp >= 3 else 1

    def choose_chain(self, g, p):
        foes = sorted(self.foes(g, p, -0.5), key=lambda q: q.hp)
        return foes[:2] if len(foes) >= 2 else []

    def pick_pile(self, g, p, pile):
        return max(pile, key=self.val)

    def choose_mode(self, g, p, skill, tgt):
        if tgt.hp <= 1 or not tgt.hand:
            return "damage"
        return "discard" if len(tgt.hand) >= 3 or tgt.hp >= 3 else "damage"

    def choose_give(self, g, p, drawn, others):
        """馬良: 把用不出去的牌 (閃/無懈) 給敵人,讓他扣血;否則把好用的牌給友人。"""
        foes = sorted([q for q in others if self.attitude(g, p, q) < 0], key=lambda q: q.hp)
        friends = [q for q in others if self.attitude(g, p, q) >= 1]
        dead = [c for c in drawn if c.name in ("閃", "無懈")]
        if foes and dead:
            return foes[0], dead[:1]
        usable = [c for c in drawn if c.name in ("無", "桃", "殺", "南", "萬")]
        if friends and usable:
            return friends[0], usable[:1]
        return None

    def choose_offturn(self, g, p, options, cur, when):
        r = p.char.ai_choose(g, p, options)
        if r is not None:
            return r
        if when.startswith("降雷連鎖"):   # 有人對我降雷: 先對自己再降雷,兩個抵銷 (後出的先結算)
            if not p.flipped and f"對 {p.name} 使用降雷" in when and p._char.name != "無名":
                for i, (c, t) in enumerate(options):
                    if t is p:
                        return i
            return None
        if when.startswith(("對你使用", "使用了")):   # 被指定時: 殘血替自己弱化;敵人翻面降雷
            for i, (c, t) in enumerate(options):
                n = getattr(c, "name", "")
                if n == "弱" and t is cur and self.attitude(g, p, cur) <= -1 and p.hp <= 2:
                    return i
                if n == "降雷" and t is cur and self.attitude(g, p, cur) <= -1 and cur._char.name != "無名" and not cur.flipped:
                    return i
                if n == "強" and t is p and p.hp >= 3 and len(p.hand) >= 3 and self.foes(g, p, -0.5):
                    return i
                if n == "決" and t is cur and self.attitude(g, p, cur) <= -1 and sum(1 for h in p.hand if h.name == "殺") >= 2 and p.hp >= cur.hp:
                    return i
                if n == "孤" and p.hp <= p.maxhp - 2 and len(p.hand) <= 2:
                    return i
                if n == "出" and isinstance(t, tuple) and t[0] is p and self.attitude(g, p, t[2]) <= -1 and t[1].name in ("樂", "兵", "毒", "閃電", "草"):
                    return i
            return None
        if when.startswith("即將受到"):   # 傷害結算前的 ⚡: 受傷的人弱化對方,或傷害來源強化自己 (剛好能打死才值得)
            src, tgt = getattr(g, "_dmg_ctx", None) or (None, None)
            m = re.search(r"\d+", when)
            n = int(m.group()) if m else 1
            if src is None or tgt is None:
                return None
            for i, (c, t) in enumerate(options):
                nm = getattr(c, "name", "")
                if nm == "弱" and t is src and p is tgt and n >= 2 and (self.attitude(g, p, src) <= -1 or src is p) and (n >= p.hp or src is p):
                    return i
                if nm == "強" and t is p and p is src and tgt is not p and self.attitude(g, p, tgt) <= -1 and n < tgt.hp <= n * 2:
                    return i
            return None
        if when != "回合開始":
            return None
        att = lambda q: self.attitude(g, p, q)
        for i, (c, t) in enumerate(options):  # ⚡ 卡牌
            n = getattr(c, "name", "")
            if n == "降雷" and t is cur and att(cur) <= -1 and cur._char.name != "無名":
                return i
            if n == "降雷" and t is not p and getattr(t, "_char", None) is not None and t._char.name == "劉備" and getattr(t._char, "ren", 0) >= 2 and not t.flipped and att(t) < 1:
                return i
            if n == "弱" and t is cur and att(cur) <= -1 and any(att(q) >= 1 and q.hp <= 2 for q in g.alive_players()):
                return i
            if n == "強" and t is cur and att(cur) >= 1 and len(cur.hand) >= 3:
                return i
            if n == "漁" and t is cur and att(cur) <= -1 and len(cur.hand) >= 3:   # 坐收漁利: 敵人手牌多、回合剛開始 → 盯著他
                return i
        return None

    def choose_option(self, g, p, skill, labels):
        if skill == "趙雲-棄牌或扣血":   # 體力夠高 (或手上有閃) 才吃扣血,不然乖乖棄牌
            return 1 if p.hp >= 4 or (p.hp == 3 and any(c.name == "閃" for c in p.hand)) else 0
        if skill == "發憤圖強-少棄":
            # 手上有反 / 調 又有敵人: 故意少棄 1~2 張吃傷害,再用反 / 調把傷害轉給敵人 (留 2 點體力以上才敢)
            self._fa_reflect = None
            if ("反" in {c.name for c in p.hand} or "調" in {c.name for c in p.hand}) and self.foes(g, p, -0.5):
                best = 0
                for i, lb in enumerate(labels):
                    m = int(lb.split("其餘 ")[1].split(" 張")[0]) if "其餘" in lb else 0
                    if 0 < m <= 2 and p.hp - m >= 2:
                        best = i
                if best:
                    self._fa_reflect = p.idx
                return best
            return 0
        if skill == "輪次方向":
            return g.rng.randrange(2)
        if skill.startswith("留下哪一件"):   # 留下攻擊範圍較大的武器 (防具預設留第一件)
            from cards import WEAPON_RANGE
            rs = [WEAPON_RANGE.get(x.split()[1][1:], 0) for x in labels]
            return rs.index(max(rs))
        if skill == "換裝":   # 換掉攻擊範圍較小 / 較不重要的那件
            from cards import WEAPON_RANGE
            rng = [WEAPON_RANGE.get(x.replace("換掉 ", "")[1:], 9) for x in labels]
            return rng.index(min(rng))
        if skill == "偽裝":
            return self._best_disguise(g, p, labels)
        if skill == "鐵索連環":   # 有兩個以上敵人就橫置,否則重鑄換牌
            return 0 if len(self.foes(g, p, -0.5)) >= 2 else 1
        return 1 if p.hp <= 2 and len(labels) > 1 else 0

    def choose_skill(self, g, p, skill):
        if skill == "許褚-放棄抽牌":
            return sum(1 for c in p.hand if c.name in ("殺", "決")) >= 2 and bool(self.foes(g, p, -0.5))
        if skill == "貫石斧-強中":
            t = g.cur_sha_target
            return t is not None and self.attitude(g, p, t) <= -1 and (t.hp <= 2 or len(p.hand) > p.hp + 2)
        if skill == "寒冰劍-棄牌":
            t = g.cur_sha_target
            return t is not None and t.hp > 1 and len(t.all_cards()) >= 2
        if skill.startswith("劉備-仁救 "):
            t = next((q for q in g.alive_players() if q.hp <= 0 and q.name == skill[len("劉備-仁救 "):]), None)
            return t is not None and (t is p or self.attitude(g, p, t) >= 1)
        if skill == "沮授-轉移":
            return len(g.others(p)) > 0 and (p.hp <= 2 or p.hand and len(p.hand) >= 3)
        if skill == "周魴-換血":
            t = max(g.others(p), key=lambda q: q.hp)
            return t.hp - p.hp >= 1 and self.attitude(g, p, t) <= 0
        if skill == "魯肅-贈牌":   # 有隊友 / 不是敵人就送,不然不白白送牌給敵人
            return any(self.attitude(g, p, q) >= 0 for q in g.others(p))
        if skill == "司馬懿-奪牌":
            return len(p.hand) <= 1
        if skill == "袁紹-多抽2張":
            return not any(c.name == "殺" for c in p.hand)
        if skill == "曹彰-少抽一張":
            return sum(1 for c in p.hand if c.name == "殺") >= 2 and bool(self.foes(g, p, -0.5))
        return True

    def choose_count(self, g, p, skill, maxn):
        junk = sum(1 for c in p.hand if self.val(c) <= 3)
        return max(1, min(maxn, junk))


class LeveledAgent(HeuristicAgent):
    """難度: 1 弱 / 2 中 / 3 強 (= 原本的規則 AI) / 4 很強 (和強一樣的判斷,但不會失誤;只靠公開資訊推測身分,不作弊)。"""
    NOISE = {1: 0.45, 2: 0.15}   # 隨機亂出牌的機率
    MISS = {1: 0.30, 2: 0.10}    # 該響應 (閃/殺/桃) 卻不出的機率

    def __init__(self, level=3):
        super().__init__()
        self.level = level

    def act(self, g, p, options):
        if g.rng.random() < self.NOISE.get(self.level, 0) and options:
            i = g.rng.randrange(len(options) + 1)
            return None if i == len(options) else i
        return super().act(g, p, options)

    def respond(self, g, p, need, cands, ctx):
        if need in ("閃", "殺", "桃") and not (need == "桃" and ctx.get("target") is p) and g.rng.random() < self.MISS.get(self.level, 0):   # 自己瀕死時不失手
            return None
        return super().respond(g, p, need, cands, ctx)

    # --- 很強 (level 4) 專屬: 都只用公開資訊 (場上血量 / 手牌張數 / 裝備) ---
    ATTACK = {"殺", "火殺", "冰殺", "雷殺", "決", "火攻"}
    F_TARGET = F_HOLD = F_ACC = True   # 三項各自可開關 (調校用)
    BOLT_KEEP = ("劉備", "龐統")   # 降雷只留給這兩種有明確收益的對象

    def _att(self, g, me, other):
        a = super()._att(g, me, other)
        # 偽裝: 內奸在場上人還多的時候假裝忠臣——不打疑似忠臣 (免得別人看出自己不是護主的),只打疑似反賊,
        # 並照常救主公;最後剩 3 人以下才露出真面目。別人只看得到公開行為,所以這樣最像忠臣。
        if (self.level >= 4 and me.role == "內奸" and other is not me and a < 0
                and len(g.alive_players()) > 3 and self.sus.get(other.idx, 0.0) <= -1.5):
            return 0.5
        return a

    def _turn_damage(self, g, p):
        """估這回合打得出的總傷害: 單次傷害 (酒 / 強 / 弱 已含) x 出殺次數。"""
        one = 1 + (1 if g.jiu else 0)
        one = (one << p.dmg_x2) >> p.dmg_half
        nsha = sum(1 for c in p.hand if c.name in ("殺", "火殺", "冰殺", "雷殺"))
        unlimited = any(str(getattr(p.equip.get(s), "name", "")).endswith("連弩") for s in ("weapon",))
        hits = max(nsha if unlimited else min(nsha, 1), 1 if any(c.name in ("決", "火攻") for c in p.hand) else 0)
        return one * hits

    def _act_core(self, g, p, options):
        if self.level < 4:
            return super()._act_core(g, p, options)
        total = self._turn_damage(g, p)
        foes = [q for q in g.others(p) if self.attitude(g, p, q) < 0]
        has_strong = any(c.name == "強" for c in p.hand)
        # 差一點才打得死 (強化後翻倍剛好夠) 才值得把強化用在自己身上
        boost = has_strong and total > 0 and any(total < q.hp <= total * 2 for q in foes)
        keep = []
        for i, (c, t) in enumerate(options):
            nm = getattr(c, "name", "")
            if not self.F_HOLD:
                pass
            elif nm == "強" and not (boost and t is p):
                continue
            elif nm == "弱":
                continue
            elif nm == "降雷" and not (hasattr(t, "_char") and t._char.name in self.BOLT_KEEP):
                continue
            keep.append(i)
        opts = [options[i] for i in keep]
        if not opts:
            return None
        killable = lambda q: q.hp <= total * (2 if boost else 1)
        pruned = []
        for name in self.ATTACK:   # 同一種攻擊牌只留「最該打」的目標: 打得死的 > 血少 + 手牌少 (閃的機會小) > 敵意高
            cs = [(c, t) for c, t in opts if c.name == name and not isinstance(t, tuple) and self.attitude(g, p, t) < 0]
            if not cs:
                continue
            if not self.F_TARGET:
                continue
            best = min(cs, key=lambda ct: (self._counter_prio(name, ct[1]), not killable(ct[1]),
                                          ct[1].hp + 0.4 * len(ct[1].hand) + 0.5 * self.attitude(g, p, ct[1])))[1]
            pruned += [(c, t) for c, t in cs if t is not best]
            # 打不死、對方手牌多又滿血、自己手牌不會爆: 先不丟出去,累積到打得死再一起出手
            if (self.F_ACC and not killable(best) and len(best.hand) >= 3 and best.hp >= 3 and len(p.hand) <= p.hp
                    and name in ("殺", "火殺", "冰殺", "雷殺")):
                pruned += [(c, t) for c, t in cs if t is best]
        opts = [ct for ct in opts if not any(ct[0] is c and ct[1] is t for c, t in pruned)]
        if not opts:
            return None
        r = super()._act_core(g, p, opts)
        return None if r is None else self._orig_index(options, opts[r])

    @staticmethod
    def _orig_index(options, opt):
        for i, o in enumerate(options):
            if o is opt:
                return i
        return 0

    def choose_offturn(self, g, p, options, cur, when):
        if self.level >= 4 and when == "回合開始":   # 平常不亂用強化,留到打得死的關鍵時刻 (傷害結算前的 ⚡ 另有判斷)
            keep = [i for i, (c, t) in enumerate(options) if getattr(c, "name", "") != "強"]
            if len(keep) < len(options):
                if not keep:
                    return None
                r = super().choose_offturn(g, p, [options[i] for i in keep], cur, when)
                return None if r is None else keep[r]
        return super().choose_offturn(g, p, options, cur, when)


