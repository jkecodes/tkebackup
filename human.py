"""人類玩家代理: 每個決策都透過 Manager.ask 停下來等 GUI 回答。"""
import re
from engine import Player
from cards import ViewCard
from characters import SkillAct
from thinking import opt_label, pname
from view import ctext, full_name
from view import card_dict

NEED_PROMPT = {
    "閃": "你被攻擊了,要打出閃嗎?",
    "殺": "需要打出殺",
    "無懈": "要使用無懈嗎?",
    "受傷響應": "你即將受到傷害,要使用 ⚡ 牌嗎?",
    "隔": "有人受傷了,要使用隔 抽牌嗎?",
    "火攻": "要棄置同色手牌造成 1 點火焰傷害嗎?",
    "借刀殺人": "要對指定的人出殺嗎?(不出會被奪走武器)",
    "趙雲棄牌": "棄 1 張手牌 (不棄就會扣 1 點體力)",
    "劉協棄牌": "棄 1 張手牌 (不棄就會扣 1 點體力)",
    "青龍追擊": "殺被閃避了: 要用青龍偃月刀再對他出一張殺嗎?",
    "夏侯淵給牌": "夏侯淵: 交給他 1 張手牌 (不給就扣 1 點體力)",
    "韓當棄牌": "韓當: 不是吳勢力要棄 1 張手牌 (不棄就要出閃,否則扣 1 點體力)",
    "袁術棄牌": "袁術的牌被捨棄了: 你要棄 1 張牌 (不棄要出閃,否則扣 1 點體力)",
    "張遼-八卦陣": "要把一張紅色手牌當作八卦陣裝備嗎?(棄掉這張牌,再像八卦陣一樣判定,紅色視為打出閃)",
    "張遼-仁王盾": "要把一張黑色手牌當作仁王盾裝備嗎?(棄掉這張牌,被黑殺指定時無效)",
}


class HumanAgent:
    is_human = True   # 技能寫「可以」的,真人要問他發動不發動 (characters._may)
    def __init__(self, mgr, seat):
        self.mgr, self.seat = mgr, seat
        self.muted = {}   # 玩家選了「本輪不再詢問」的連鎖/別人回合發動選項: 簽名 -> 輪數

    def _ask(self, kind, prompt, options, mn=1, mx=1, timeout=None, default=None):
        try:   # 選項裡的牌如果其實在自己的裝備區 (技能把裝備當別的牌用): 卡面標「裝備區」
            me = self.mgr.game.players[self.seat]
            eq = {c.id for c in me.equip_cards()} - {c.id for c in me.hand}
            for o in options:
                if isinstance(o, dict) and isinstance(o.get("card"), dict) and o["card"].get("id") in eq:
                    o["card"]["zone"] = "裝備區"
        except Exception:
            pass
        return self.mgr.ask(self.seat, kind, prompt, options, mn, mx, timeout, default)

    @staticmethod
    def _copt(i, label, card=None, group=None):
        return {"i": i, "label": label, "card": card_dict(card) if card is not None else None, "group": group}

    @staticmethod
    def _is_move(t):   # 出奇不意: (原主人, 要移動的判定牌, 新主人)
        return isinstance(t, tuple) and len(t) == 3 and isinstance(t[0], Player) and not isinstance(t[1], Player) and isinstance(t[2], Player)

    # ---- 出牌階段 ----
    def act(self, g, p, options):
        opts = []
        for i, o in enumerate(options):
            card, t = o
            group = card_dict(card)["id"]
            tgt = None
            if isinstance(t, Player):
                tgt = {"kind": "player", "idx": t.idx, "label": pname(t)}
            elif t == "heal":
                tgt = {"kind": "heal", "label": "回血"}
            elif hasattr(t, "kind") and hasattr(t, "color") and not isinstance(t, tuple):
                tgt = {"kind": "equip", "cid": card_dict(t)["id"], "label": ctext(t)}   # 丁奉: 選一件自己的裝備
            elif self._is_move(t):   # 出其不意: 前端先點場上的延時錦囊 (cid),再點要移去的玩家 (idx)
                tgt = {"kind": "move", "owner": t[0].idx, "cid": card_dict(t[1])["id"], "idx": t[2].idx, "label": f"{pname(t[0])} 的 {ctext(t[1])} → {pname(t[2])}"}
            elif isinstance(t, tuple):
                tgt = {"kind": "multi", "label": "、".join(pname(x) for x in t)}
                if all(isinstance(x, Player) for x in t):
                    tgt["idxs"] = [x.idx for x in t]   # 前端依序點選這幾位玩家
            d = self._copt(i, opt_label(o), card, group)
            d["target"] = tgt
            opts.append(d)
        r = self._ask("act", f"你的出牌階段 (體力 {p.hp}/{p.maxhp})  選一張牌與目標,或結束出牌", opts, 0, 1)
        return r[0] if r else None

    # ---- 響應 ----
    def respond(self, g, p, need, cands, ctx):
        prompt = NEED_PROMPT.get(need)
        if need == "桃":
            t = ctx.get("target")
            prompt = (f"{pname(t)} 瀕死了,要使用桃/酒救他嗎?" if t is not None else "要打出桃嗎?(不出會扣 1 點體力)")
            if t is p:
                prompt = "你瀕死了,要使用桃/酒救自己嗎?"
        if need == "無懈":
            who = "全體" if ctx.get("targets") else pname(ctx["target"])
            on = "" if ctx.get("target") is ctx["source"] and not ctx.get("targets") else f" 對 {who}"   # 對自己 / 沒有對象的牌 (五穀豐登、無中生有…) 不寫「對 自己」
            prompt = (f"{pname(ctx['source'])}{on} 使用 {full_name(ctx['trick'])}" +
                      f"{' (已被無懈)' if ctx.get('negated') else ''},要使用無懈嗎?")
        if need == "受傷響應":
            prompt = f"你即將受到 {ctx['n']} 點傷害,要使用 ⚡ 牌嗎?"
            if ctx.get("fan_n") not in (None, ctx["n"]):
                prompt += f" (用反擊轉給別人會是 {ctx['fan_n']} 點,已含強化/弱化)"
        for k in ("attacker", "src", "source"):
            if need in ("閃", "殺") and isinstance(ctx.get(k), Player):
                who, cc = ctx[k], getattr(g, "cur_card", None)
                if ctx.get("cao_n"):   # 曹沖: 一回合第 2 張起的錦囊,可以閃掉扣 1 點體力
                    prompt = f"曹沖效果: 你這回合已使用第 {ctx['cao_n']} 張錦囊 (只能 1 張),要打出{need}嗎? (不出扣 1 點體力)"
                elif who is p:   # 周倉: 沒有傷害來源 (閃電…) 受到傷害,打出等量的閃抵擋
                    prompt = f"你即將受到傷害,要打出{need}抵擋嗎? (每打出一張抵擋 1 點)"
                elif ctx.get("group"):
                    prompt = f"{pname(who)} 使用 {full_name(ctx['group'])},要打出{need}嗎?"
                elif cc is not None and g.cur_user is who and cc.name == "殺":
                    prompt = f"{pname(who)} 對你使用殺,要打出{need}嗎? (不出會受到傷害)"
                elif cc is not None and g.cur_user is who:
                    prompt = f"{pname(who)} 使用 {full_name(cc.name)},要打出{need}嗎?"
                else:
                    prompt = f"{pname(who)} 的技能效果指向你,要打出{need}嗎?"
                break
        if need == "殺" and isinstance(ctx.get("duel_with"), Player):
            prompt = f"和 {pname(ctx['duel_with'])} 決鬥: 要打出殺嗎? (不出就扣 {g.dmg_preview(ctx['duel_with'], 1, tgt=p, bonus=True)} 點體力)"
        if need in ("劉協棄牌", "夏侯淵給牌", "韓當棄牌", "袁術棄牌") and prompt and isinstance(ctx.get("source"), Player):   # 提示裡的「扣 1 點」要是算完對方強化 / 弱化的
            prompt = prompt.replace("扣 1 點", f"扣 {g.dmg_preview(ctx['source'], 1, tgt=p, bonus=need in ('劉協棄牌', '夏侯淵給牌'))} 點")
        lab = lambda c: ctext(c) + (f"  → 當作 {full_name(need)}" if need in ("閃", "殺", "桃", "酒") and getattr(c, "name", need) != need else "")   # 技能把這張牌當別的牌用 (關羽的桃當閃…): 選項上寫清楚
        if need == "受傷響應":   # 手牌是靠技能當 反 / 調 / 占 用的: 每種用途各列一個選項,卡面和文字都寫「當作 X」
            pairs = [(c, k) for c in cands for k in (g._react_kinds(p, c) or [getattr(c, "name", "")])]
            opts = [self._copt(j, (f"{ctext(c)}  → 當作 {full_name(k)}" if c.name != k else ctext(c)),
                               c if c.name == k else ViewCard(k, c.color, "trick", c, id=c.id)) for j, (c, k) in enumerate(pairs)]
            opts.append(self._copt(len(pairs), "不出", None))
            r = self._ask("respond", prompt or f"響應: {need}", opts)
            if not r or r[0] >= len(pairs):
                return None
            c, k = pairs[r[0]]
            if c.name != k:
                g._react_pick = k
            return c
        reacts = []   # 不閃就會受傷: ⚡ 反 / 調 / 占 一起問 [(手牌, 當成哪種)]
        if need == "閃" and ctx.get("react"):
            rc, _ = g._reaction_cands(p)
            reacts = [(c, k) for c in rc for k in g._react_kinds(p, c)]
            if reacts and prompt:
                prompt = prompt.replace("要打出閃嗎", "要打出牌嗎")   # 選項裡有閃也有 ⚡ 牌: 不要只寫閃
        dual = {id(c) for c, _ in reacts}   # 同一張牌既能當閃、又能當 ⚡: 兩個用途分開列
        opts = [self._copt(i, (ctext(c) + "  → 當作閃打出") if id(c) in dual else lab(c), c) for i, c in enumerate(cands)]
        for j, (c, k) in enumerate(reacts):
            opts.append(self._copt(len(cands) + j, (f"{ctext(c)}  → 當作 {full_name(k)} (受傷前使用 ⚡)" if c.name != k else f"{ctext(c)} (受傷前使用 ⚡)"),
                                   c if c.name == k else ViewCard(k, c.color, "trick", c, id=c.id)))   # 畫面上這張牌直接顯示「當作調虎離山」
        opts.append(self._copt(len(cands) + len(reacts), "不出", None))
        r = self._ask("respond", prompt or f"響應: {need}", opts)
        if not r or r[0] >= len(cands) + len(reacts):
            return None
        if r[0] >= len(cands):
            c, k = reacts[r[0] - len(cands)]
            g._early_react = (c, k, p)   # 不出閃: 傷害結算時直接用這張 ⚡ 牌 (不再問第二次)
            return None
        return cands[r[0]]

    def respond_race(self, g, entries, tgt):
        """瀕死: 同時問所有真人能不能救,第一個出桃/酒的人救。entries: [(Player, cands)]。回傳 (Player, card) 或 None。"""
        reqs, by_seat = [], {}
        for q, cands in entries:
            seat = q.agent.seat
            who = "你" if q is tgt else pname(tgt)
            prompt = ("你瀕死了,要使用桃/酒救自己嗎?" if q is tgt else f"{who} 瀕死了,要使用桃/酒救他嗎?") + " (大家同時決定,先出的人救)"
            opts = [self._copt(i, ctext(c), c) for i, c in enumerate(cands)]
            opts.append(self._copt(len(cands), "不出", None))
            reqs.append((seat, "respond", prompt, opts, 1, 1, len(cands)))
            by_seat[seat] = (q, cands)
        r = self.mgr.ask_first(reqs)
        if not r:
            return None
        q, cands = by_seat[r[0]]
        return q, cands[r[1][0]]

    # ---- 各種選擇 ----
    def choose_discard(self, g, p, n, cands, msg=None):
        n = min(n, len(cands))
        if n == len(cands):
            return list(cands)
        opts = [self._copt(i, ctext(c), c) for i, c in enumerate(cands)]
        r = self._ask("discard", msg or f"選擇要棄置的 {n} 張牌", opts, n, n)
        return [cands[i] for i in r]

    def choose_from(self, g, p, target, cands):
        opts = [self._copt(i, "對方的一張手牌 (隨機)" if c == "HAND" else ctext(c), None if c == "HAND" else c)
                for i, c in enumerate(cands)]
        for o, c in zip(opts, cands):   # 前端: 直接點場上那張牌 (手牌沒有牌面,用按鈕)
            o["target"] = {"kind": "zonehand", "idx": target.idx} if c == "HAND" else {"kind": "zone", "idx": target.idx, "cid": card_dict(c)["id"]}
        r = self._ask("pick", f"選擇 {pname(target)} 的一張牌", opts)
        return cands[r[0]]

    def show_card(self, g, p, hand):
        opts = [self._copt(i, ctext(c), c) for i, c in enumerate(hand)]
        r = self._ask("show", "火攻: 選一張手牌展示 (展示後仍留在手牌)", opts)
        return hand[r[0]]

    def choose_target(self, g, p, kind, cands):
        opts = [self._copt(i, f"{pname(q)}  體力 {q.hp}/{q.maxhp}") for i, q in enumerate(cands)]
        for o, q in zip(opts, cands):   # 前端: 直接點場上的玩家
            if isinstance(q, Player):
                o["target"] = {"kind": "player", "idx": q.idx, "label": pname(q)}
        r = self._ask("target", f"{kind}: 選擇目標", opts)
        return cands[r[0]]

    def choose_borrow(self, g, p, skill, cands):
        """馬謖 / 陳群 / 韓當: 選一位玩家複製技能,畫面用武將卡片 (頭像 + 技能) 列出。"""
        opts = []
        for i, q in enumerate(cands):
            o = self._copt(i, q._char.name)
            o["sub"] = f"P{q.idx} {q.name}  體力 {q.hp}/{q.maxhp}"
            o["target"] = {"kind": "player", "idx": q.idx, "label": pname(q)}
            opts.append(o)
        r = self._ask("mode", f"複製技能: {skill.split('-')[0]}要複製誰的技能?", opts)
        return cands[r[0]]

    def choose_dir(self, g, p):
        r = self._ask("dir", "選擇結算方向", [self._copt(0, "從我左邊開始"), self._copt(1, "從我右邊開始")])
        return "LR"[r[0]]

    def choose_x(self, g, p):
        mx = max(1, min(5, p.char.max_fa(g, p)))   # 黃忠最多 3
        r = self._ask("count", "發憤圖強: 要抽幾張?" + (f" (最多 {mx} 張)" if mx < 5 else ""), [self._copt(i, str(i + 1)) for i in range(mx)])
        return r[0] + 1

    def choose_chain(self, g, p):
        alive = g.alive_players()
        opts = [self._copt(i, pname(q)) for i, q in enumerate(alive)]
        for o, q in zip(opts, alive):   # 前端: 直接點場上的玩家 (最多 2 位)
            o["target"] = {"kind": "player", "idx": q.idx, "label": pname(q)}
        r = self._ask("chain", "鐵索連環: 選 1~2 名玩家橫置 / 重置", opts, 1, 2)
        return [alive[i] for i in r]

    def pick_pile(self, g, p, pile):
        opts = [self._copt(i, ctext(c), c) for i, c in enumerate(pile)]
        r = self._ask("pile", getattr(g, "pile_ctx", None) or "五穀豐登: 選一張牌", opts)
        return pile[r[0]]

    def choose_skill(self, g, p, skill):
        r = self._ask("skill", f"{skill}: 要發動嗎?", [self._copt(0, "發動"), self._copt(1, "不發動")])
        return r[0] == 0

    def choose_count(self, g, p, skill, maxn):
        maxn = max(1, maxn)   # 不設上限: 手牌有幾張就能選到幾張
        r = self._ask("count", f"{skill}: 選擇張數", [self._copt(i, str(i + 1)) for i in range(maxn)])
        return r[0] + 1

    def choose_offturn(self, g, p, options, cur, when):
        wk = "回合" if when in ("回合開始", "出牌階段結束") else re.sub(r"\d+", "", when)   # 回合開始和出牌階段結束是同一類「別人回合的時機」: 選了「本回合不再詢問」兩個時機都不要再問
        sig = (wk,) + tuple(sorted({getattr(o[0], "name", str(o[0])) for o in options}))
        m = self.muted.get(sig)
        if m and ((m[0] == "round" and m[1] == g.round) or (m[0] == "turn" and m[1] == g.turn_id)):
            return None
        opts = []
        for i, o in enumerate(options):
            card, t = o
            verb = "發動 " if isinstance(card, SkillAct) else "使用 "
            d = self._copt(i, verb + opt_label(o), card, card_dict(card)["id"])
            d["gl"] = verb + (card.name if isinstance(card, SkillAct) else ctext(card))   # 第一步只問「要不要發動這個」
            d["target"] = {"kind": "player", "idx": t.idx, "label": pname(t)} if isinstance(t, Player) else None
            if self._is_move(t):   # 出奇不意: 同一張牌依「移動哪張判定牌」分組,再點目標玩家
                d["group"] = f"{d['group']}|{t[1].id}"
                d["gl"] += f": 移動 {pname(t[0])} 的 {ctext(t[1])}"
                d["label"] += f": {ctext(t[1])} {pname(t[0])} → {pname(t[2])}"
                d["target"] = {"kind": "player", "idx": t[2].idx, "label": pname(t[2])}
            opts.append(d)
        merged = bool(getattr(g, "_offturn_merged", False))   # 被殺的合併詢問: 選項有連鎖 ⚡ / 閃 / 受傷前 ⚡,不能「本回合不再詢問」
        opts.append(self._copt(len(options), "不出" if merged else "不發動"))
        if not merged:
            opts.append(self._copt(len(options) + 1, "不發動,這類選項本回合不再詢問"))
        r = self._ask("skill", (f"{pname(cur)} {when}: 要打出牌嗎?" if merged else f"{pname(cur)} {when}: 要接連鎖使用 ⚡ 嗎?" if when.startswith(("對你使用", "使用了", "即將受到")) else f"{pname(cur)} 的{when}: 要發動技能嗎?"), opts,
                      timeout=None if merged else 20, default=[len(options)])   # 20 秒沒回答 = 不發動 (出閃的合併詢問不設時限,跟原本的出閃詢問一樣)
        if r[0] == len(options) + 1:
            self.muted[sig] = ("turn", g.turn_id)
            return None
        return r[0] if r[0] < len(options) else None

    def choose_option(self, g, p, skill, labels):
        opts = [self._copt(i, x) for i, x in enumerate(labels)]
        if skill == "偽裝":   # 標出依目前局面推薦的偽裝對象 (前端有搜尋欄)
            from ai import HeuristicAgent
            sc = HeuristicAgent().dg_scores(g, p, list(labels))   # 實測表: 變身後那個回合的平均局面變化
            top = {n for n in sorted(labels, key=lambda n: -sc.get(n, 0))[:5] if sc.get(n, 0) >= 0.5}
            for o in opts:
                o["rec"] = labels[o["i"]] in top
                o["score"] = round(sc.get(labels[o["i"]], 0), 1)
        r = self._ask("mode", f"{skill}: 選擇效果", opts)
        return r[0]

    def choose_mode(self, g, p, skill, tgt):
        r = self._ask("mode", f"{skill}: 對 {pname(tgt)} 要怎麼做?",
                      [self._copt(0, "令他棄 1 張手牌"), self._copt(1, "令他扣 1 點體力 (可閃)")])
        return "discard" if r[0] == 0 else "damage"

    def choose_give(self, g, p, drawn, others):
        opts = [self._copt(i, ctext(c), c) for i, c in enumerate(drawn)]
        r = self._ask("give", "馬良: 選擇要交給別人的牌 (不選 = 不發動)", opts, 0, len(drawn))
        if not r:
            return None
        to = [self._copt(i, pname(q)) for i, q in enumerate(others)]
        for o, q in zip(to, others):
            o["target"] = {"kind": "player", "idx": q.idx, "label": pname(q)}
        t = self._ask("target", "交給誰?", to)
        return others[t[0]], [drawn[i] for i in r]
