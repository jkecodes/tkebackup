"""武將系統。技能原文見 characters.md。

每位武將是 Char 的子類,覆寫需要的掛鉤即可。引擎在對應時機呼叫掛鉤:
  draw_count / after_draw    抽牌階段張數與抽完後的額外效果
  sha_limit / no_range / dist_mod / as_sha   殺的次數、射程、距離修正、當殺用的牌
  cap_damage / on_damaged    傷害上限、受傷後觸發
  on_other_wu / on_le_placed 他人使用無 / 樂被放置時
  peach_heal / jiu_heal / jiu_self_heal      桃酒回體力、酒自己回合回血
  max_fa / fa_free / end_turn  發憤圖強上限與免代價、回合結束時

連鎖: 每張牌/每次判定開始一條連鎖 (g.new_chain),依序編號 Chain 1、2...,後發動的先結算。
觸發型技能發動前必須呼叫 g.trigger_ok(p, 技能名): 主動發動 (要選擇) 的技能同一條連鎖最多一次,被動技能不限次數 (見 Game.PASSIVE_SKILLS);
被毒翻面的武將 (p.flipped) 技能全部失效 (Player.char 會回傳無技能的空武將)。
"""


DELAYED_NAMES = {"閃電", "樂", "毒", "兵", "草"}  # 延時型錦囊 (鄧艾「非延時」判斷用)


class SkillAct:
    """主動技能的出牌選項。run(g, p, tgt) 執行技能。"""
    kind = "skill"
    color = ""

    def __init__(self, name, run):
        self.name, self.run = name, run

    def __repr__(self):
        return f"〈{self.name}〉"


class Char:
    name = "無名"
    faction = ""
    maxhp = 4

    def draw_count(self, g, p): return 2
    def after_draw(self, g, p, drawn): pass
    def after_extra_draw(self, g, p, drawn): pass   # 抽牌階段以外抽到牌後 (孫策的黑牌多抽也算)
    def sha_limit(self, g, p): return 1            # None = 無限
    def no_range(self, g, p): return False
    def dist_mod(self, g, p, t): return 0
    def views(self, g, p, c): return []            # 這張手牌還可以當作哪些牌 (名稱 list) 使用
    def as_card(self, g, p, c, name): return False  # 響應/需要 name 時,c 是否可當 name 打出
    def skill_options(self, g, p): return []        # 主動技能: [(SkillAct, 目標)]
    def ai_choose(self, g, p, options): return None  # AI 對自己主動技能的決策 (回傳 options 索引)
    def on_targeted(self, g, p, user, card): pass   # 被 user 的 card 指定為目標時
    def blocks_target(self, g, p, card): return False  # card 是否無法以 p 為目標
    immune_delayed = False                          # 延時錦囊對你無效
    no_flip = False                                 # 武將牌不會翻面
    def on_flipped(self, g, p): pass
    def lose_marks(self, g, p): pass   # 被降雷翻成背面後 (整條連鎖結算完還是背面),身上的標記全部消失
    def on_flip_change(self, g_or_p, flipped=None): pass   # 翻面狀態改變時 (p, 是否翻面)
    def on_dying(self, g, p): pass
    def on_dying_help(self, g, p, tgt): pass   # 別人 (或自己) 瀕死時,p 有機會幫忙 (劉備: 用仁回血)
    def on_deal_damage(self, g, p, tgt, n): pass    # p 對別人造成傷害後
    def on_any_damaged(self, g, p, tgt, n): pass    # 任何人受傷後
    def takes_dead_cards(self, g, p): return False  # 角色死亡時獲得其所有牌
    def hand_limit(self, g, p, h): return h   # 手牌上限 (預設 = 目前體力)
    def dyn_maxhp(self, p): return None       # 體力上限隨局面變動時回傳數字 (孟獲)
    def skip_discard(self, g, p): return False      # 這回合不用棄牌
    def discard_amount(self, g, p, extra): return extra  # 棄牌階段實際要棄幾張
    def after_discard(self, g, p): pass             # 棄牌階段後
    def dmg_dealt_mod(self, g, p, tgt, n): return n  # p 對別人造成的傷害修正
    def sha_targets(self, g, p, targets): return targets  # 殺可選的目標
    def on_view_used(self, g, p, card): pass        # 使用了「當作」的牌後
    def on_other_trick(self, g, p, user, real): pass  # 別人使用錦囊牌 (結算後) 時
    equip_safe = False                              # 裝備不會被過/順/借/轉
    def plain_immune(self, g, p): return False      # 非屬性傷害對你無效
    def on_game_start(self, g, p): pass             # 開局 (發完起手牌後)
    def on_turn_start(self, g, p): pass             # 自己回合開始 (判定階段前)
    def on_sha_dodged(self, g, p, tgt): pass        # 自己的殺被閃
    def on_sha_hit(self, g, p, tgt, n): pass        # 自己的殺造成傷害後
    def on_any_trick(self, g, p, user, real): pass  # 任何人 (含自己) 使用錦囊牌時
    def group_damage(self, g, p, trick): return 1   # 自己的南/萬 傷害量
    def virtual_bagua(self, g, p): return False     # 需要閃時,臨時當八卦陣 (回傳 True = 已付出代價)
    def virtual_renwang(self, g, p): return False   # 被黑殺指定時,臨時當仁王盾
    def immune_nature(self, g, p, nature): return False  # 屬性傷害對你無效
    def cap_damage(self, g, p, n): return n
    def on_damaged(self, g, p, src, n): pass
    def after_damage(self, g, p): pass   # 一次傷害完整結算後 (含連鎖、麒麟弓等)
    def on_other_wu(self, g, p, user): pass
    def on_le_placed(self, g, p, owner): pass
    def peach_heal(self, g, p): return 1
    def jiu_heal(self, g, p): return 1
    def jiu_self_heal(self, g, p): return 0
    def max_fa(self, g, p): return 5
    def fa_free(self, g, p): return False         # 發憤圖強不用棄也不扣血
    def end_turn(self, g, p): pass
    # --- 第六批新增掛鉤 ---
    def dist_in(self, g, p, a): return 0           # 別人 a 計算到我的距離修正
    damage_only_sha = False                         # 只有殺能對你造成傷害
    no_jiu_target = False                           # 酒殺不能以你為目標
    no_armor = False                                # 不能裝備防具
    immune_names = ()                               # 這些延時錦囊對你無效
    sha_reflect = False                             # 殺對你無效,使用者扣血
    bans = frozenset()                              # 全場禁用的牌名
    def replace_draw(self, g, p): return False      # 是否取代抽牌階段
    def on_other_turn_start(self, g, p, cur): pass  # 別人回合開始時 (cur 是回合者)
    def on_sha_used(self, g, p, card): pass         # 自己使用殺時
    def on_healed(self, g, p): pass
    def stay_flipped(self, g, p): return False      # 回合結束後是否仍維持翻面
    # --- 第七批新增掛鉤 ---
    dual_weapon = False                             # 可同時裝備 2 把武器
    dual_armor = False                              # 可同時裝備 2 件防具
    def sha_dodge_need(self, g, p, tgt): return 1   # 你的殺需要對方打出幾張閃
    def on_other_dodge(self, g, p, user): pass      # 別人打出閃時
    judge_pick = False                              # 1 點體力時可決定判定牌 (張苞)
    wu_picks = 1                                    # 五穀豐登可拿幾張
    tie_extra = 0                                   # 鐵索連環重鑄多抽幾張
    block_names = ()                                # 不能以你為目標的牌 (出)
    one_card = False                                # 全場每人每回合只能用 1 張牌 (曹沖)
    cap3 = False                                    # 全場手牌上限最多 3 (劉禪)
    no_extra_draw = False                           # 全場一般抽牌以外完全不能抽牌 (張紘)
    peach_lock = False                              # 其他人除了瀕死救人,不能在出牌階段吃桃 (賈詡自己不受限)
    single_to_all = False                           # 單一對象錦囊對其他所有人有效 (關興)
    basic_as_trick = False                          # 全場基本牌的種類也算錦囊 (魯肅)
    def blocks_card(self, g, p, card): return False  # 這張牌你不能使用
    def trick_lock(self, g, p): return False         # 你 (沒手牌) 讓別人不能使用錦囊牌 (鐘繇)
    def range_floor(self, g, p): return 0           # 攻擊距離至少為
    def on_hand_empty(self, g, p): pass             # 失去最後一張手牌
    def on_turn_end(self, g, p, cur): pass          # 任何人的回合結束
    def on_equip_broken(self, g, p, owner, c): pass  # 別人的裝備被棄置
    def on_equipped(self, g, p, owner, c): pass  # 別人放置 (裝上) 了一件裝備
    def on_cards_discarded(self, g, p, c): pass     # 自己的牌被捨棄
    def on_judged(self, g, p, c): pass              # 自己判定後 (袁術)
    def on_any_judge(self, g, p, who, c): pass      # 任何人判定後 (郭嘉: 拿走判定牌)
    def on_any_death(self, g, p, victim, killer): pass
    def on_other_draw(self, g, p, cur): pass        # 別人抽牌階段
    def on_card_used(self, g, p, user, card): pass  # 任何人使用牌 / 反調占
    thunder_reflect = False                         # 降雷對你無效,使用者扣 1 點體力 (曹操)
    no_thunder_unflip = False                       # 不能被降雷翻回正面 (曹叡)
    def on_other_wei(self, g, p, user, name): pass  # 別人偽裝成某武將時 (郭圖&逢紀)
    tao_self_only = False                           # 投桃報李只能令自己回血 (孔融)
    def offturn_options(self, g, p): return []      # 別人回合也能發動的技能 [(SkillAct, 目標)]
    equip_void = False                              # 全場裝備無效 (太史慈)
    tao_no_heal = False                             # 使用投桃報李不幫別人回血 (周胤)
    gu_no_loss = False                              # 孤注一擲不扣血 (周胤)
    fan_double = False                              # 反的傷害雙倍 (張昭)
    def pre_damage(self, g, p, src, n, nature): return n  # 受傷前處理,回傳 0 = 被轉移/抵銷
    def on_other_basic(self, g, p, user, real): pass       # 別人使用基本牌時


class Combo:
    """借來 / 化身的武將技能: own 是本尊,extras 是額外擁有的武將 (馬謖、陳群、韓當、公孫淵、左慈)。

    事件類掛鉤 (on_*) 每個武將都會呼叫;清單類掛鉤合併;布林類任一為真即成立;
    數值修正串接;其餘以本尊優先 (本尊沒覆寫才用借來的)。"""
    EVENTS_EXTRA = {"after_draw", "after_discard", "end_turn", "after_damage"}
    LIST_MERGE = {"skill_options", "offturn_options", "views"}
    OR_HOOKS = {"no_range", "blocks_target", "blocks_card", "as_card", "virtual_bagua", "virtual_renwang",
                "plain_immune", "immune_nature", "trick_lock", "skip_discard", "takes_dead_cards", "replace_draw"}
    CHAIN = {"sha_targets": 2, "cap_damage": 2, "discard_amount": 2, "pre_damage": 3, "dmg_dealt_mod": 3}
    SUM = {"dist_mod", "dist_in", "range_floor"}

    def __init__(self, own, extras):
        self.own, self.extras = own, list(extras)

    def __getattr__(self, k):
        own, extras = self.own, self.extras
        if k in ("name", "faction", "maxhp"):
            return getattr(own, k)
        allc = [own] + extras
        v = getattr(own, k)
        if not callable(v):
            for c in allc:
                cv = getattr(c, k)
                if cv != getattr(Char, k, cv):
                    return cv
            return v
        if k.startswith("on_") or k in self.EVENTS_EXTRA:
            def run(*a, **kw):
                for c in allc:
                    getattr(c, k)(*a, **kw)
            return run
        if k in self.LIST_MERGE:
            return lambda *a, **kw: [x for c in allc for x in getattr(c, k)(*a, **kw)]
        if k in self.OR_HOOKS:
            return lambda *a, **kw: any(getattr(c, k)(*a, **kw) for c in allc)
        if k in self.SUM:
            return lambda *a, **kw: sum(getattr(c, k)(*a, **kw) for c in allc)
        if k in self.CHAIN:
            i = self.CHAIN[k]

            def chain(*a):
                a = list(a)
                for c in allc:
                    a[i] = getattr(c, k)(*a)
                return a[i]
            return chain
        if k == "ai_choose":
            def pick(*a):
                for c in allc:
                    r = c.ai_choose(*a)
                    if r is not None:
                        return r
            return pick
        if k == "sha_limit":
            def lim(*a):
                vals = [c.sha_limit(*a) for c in allc]
                return None if None in vals else max(vals)
            return lim
        for c in allc:  # 其餘: 第一個有覆寫的武將 (本尊優先)
            if getattr(type(c), k, None) is not getattr(Char, k, None):
                return getattr(c, k)
        return v


class 張飛(Char):
    name, faction = "張飛", "蜀"

    def sha_limit(self, g, p): return None

    def cap_damage(self, g, p, n):  # 一回合最多扣 2 點體力
        return max(0, min(n, 2 - p.dmg_turn))

    def on_other_wu(self, g, p, user):
        if g.trigger_ok(p, "張飛-抽牌"):
            g.link(f"{p.name}[張飛] 也抽 2 張")
            g.draw(p, 2)


class 馬超(Char):
    name, faction = "馬超", "蜀"

    def draw_count(self, g, p): return 3
    def dist_mod(self, g, p, t): return -1
    def views(self, g, p, c): return ["殺"] if c.kind == "trick" and c.color == "紅" else []


class 黃忠(Char):
    name, faction = "黃忠", "蜀"

    def max_fa(self, g, p): return 3
    def fa_free(self, g, p): return True

    def end_turn(self, g, p):
        if p.played == 0 and p.hp < p.maxhp:
            g.heal(p)
            g.log(f"  {p.name} 本回合未出牌,回 1 點體力 -> 體力 {p.hp}")


class 荀彧(Char):
    name, faction = "荀彧", "魏"

    def jiu_self_heal(self, g, p): return 2

    def on_damaged(self, g, p, src, n):
        if p.flipped:
            return
        g.new_dmg_chain()   # 受傷之後才發動: 另開一條新連鎖
        if g.trigger_ok(p, "荀彧-抽牌"):
            g.link(f"{p.name}[荀彧] 受傷,抽 {2 * n} 張")
            g.draw(p, 2 * n)


class 孫策(Char):
    name, faction = "孫策", "吳"

    def no_range(self, g, p): return True

    def after_extra_draw(self, g, p, drawn):   # 抽牌階段以外得到牌 (抽、拿、獲得…)
        self.after_draw(g, p, drawn)

    def after_draw(self, g, p, drawn):
        # 得到的牌中每張黑色牌多抽 1 張;後來多抽到的牌也要算 (連續)
        if getattr(self, "_busy", False):
            return
        self._busy = True
        try:
            blacks = sum(1 for c in drawn if c.color == "黑")
            while blacks:
                g.log(f"  {p.name} 抽到 {blacks} 張黑牌,多抽 {blacks} 張")
                more = g.draw(p, blacks)
                blacks = sum(1 for c in more if c.color == "黑")
        finally:
            self._busy = False


class 華雄(Char):
    name, faction, maxhp = "華雄", "群", 6

    def draw_count(self, g, p): return 5

    def on_damaged(self, g, p, src, n):  # 華雄被扣血: 「打他的人」判定,紅色回 1 血、黑色抽 1 張
        if src is None or (src is p and not getattr(g, "_lt_dmg", False)) or not src.alive or p.flipped:   # 自己放的閃電打到自己 (閃電繞一圈) 也算: 放閃電的人判定
            return
        g.new_dmg_chain()   # 受傷之後才發動: 另開一條新連鎖
        if not g.trigger_ok(p, "華雄-判定"):
            return
        g.link(f"{p.name}[華雄] 受傷,{src.name} 判定")
        j = g.flip_judge(src)
        if j.color == "紅":
            g.heal(src)
            g.log(f"  {src.name} 判定 {j}: 回 1 點體力 -> 體力 {src.hp}")
        else:
            g.draw(src, 1)
            g.log(f"  {src.name} 判定 {j}: 抽 1 張")


class 董卓(Char):
    name, faction, maxhp = "董卓", "群", 8

    def peach_heal(self, g, p): return 2
    def jiu_heal(self, g, p): return 3

    def end_turn(self, g, p):
        if all(p.hp > q.hp for q in g.others(p)):
            g.log(f"  {p.name} 體力場上最多,扣 1 點體力")
            g.damage(None, p, 1)

    def on_le_placed(self, g, p, owner):
        if owner is not p and g.trigger_ok(p, "董卓-樂"):
            p.skip_play_flag = True
            g.log(f"  {p.name} 也被樂 (不判定,下個出牌階段跳過)")

    def on_flip_change(self, p, flipped):   # 翻面時體力上限變 4 (體力超過就降到 4),翻回正面又變回 8
        if flipped:
            p.maxhp -= 4   # 8 → 4 (主公的額外上限保留)
            p.hp = min(p.hp, p.maxhp)
            if p.g is not None:
                p.g.log(f"  {p.name}[董卓] 翻面,體力上限變成 {p.maxhp}")
        else:
            p.maxhp += 4
            if p.g is not None:
                p.g.log(f"  {p.name}[董卓] 翻回正面,體力上限變回 {p.maxhp}")


class 曹彰(Char):
    name, faction = "曹彰", "魏"

    def draw_count(self, g, p):
        if p.agent.choose_skill(g, p, "曹彰-少抽一張"):
            p.turn_flags["cz"] = True
            g.log(f"  {p.name} 少抽一張: 本回合可出兩張殺且無距離限制")
            return 1
        return 2

    def sha_limit(self, g, p): return 2 if p.turn_flags.get("cz") else 1
    def no_range(self, g, p): return bool(p.turn_flags.get("cz"))


class 關羽(Char):
    name, faction = "關羽", "蜀"

    def draw_count(self, g, p): return 2 + max(0, p.maxhp - p.hp)

    def views(self, g, p, c): return ["桃"] if c.name == "閃" else []

    def as_card(self, g, p, c, name):
        return (c.name, name) in (("閃", "桃"), ("桃", "閃"))

    def on_flipped(self, g, p):  # 翻面時,你和另一名玩家棄掉所有的牌 (手牌 + 裝備 + 判定區)
        others = list(g.others(p))
        if others and g.trigger_ok(p, "關羽-棄牌"):
            q = p.agent.choose_target(g, p, "關羽-棄牌", others)
            g.link(f"{p.name}[關羽] 與 {q.name} 棄掉所有的牌")
            for x in (p, q):
                for c in list(x.hand) + x.equip_cards() + list(x.judge):
                    g.discard_card(x, c)


class 孫權(Char):
    name, faction = "孫權", "吳"
    no_flip = True

    def skill_options(self, g, p):
        opts = []
        if not p.turn_flags.get("sq_swap") and p.hand:
            opts.append((SkillAct("孫權-換牌", self._swap), None))
        shas = [c for c in p.hand if c.name == "殺"]
        if not p.turn_flags.get("sq_sha") and len(shas) >= 2:
            opts += [(SkillAct("孫權-殺殺", self._two_sha), t) for t in g.others(p)]
        return opts

    def _swap(self, g, p, t):
        p.turn_flags["sq_swap"] = True
        k = max(1, min(len(p.hand), p.agent.choose_count(g, p, "孫權-換牌", len(p.hand))))
        for c in p.agent.choose_discard(g, p, k, list(p.hand)):
            g.discard_card(p, c)
        g.log(f"  {p.name}[孫權] 棄 {k} 張,再抽 {k} 張")
        g.draw(p, k)

    def _two_sha(self, g, p, t):
        p.turn_flags["sq_sha"] = True
        for c in [c for c in p.hand if c.name == "殺"][:2]:
            g.discard_card(p, c)
        g.log(f"  {p.name}[孫權] 棄兩張殺,強制 {t.name} 扣 1 點體力")
        g.damage(p, t, 1)

    def ai_choose(self, g, p, options):
        att = getattr(p.agent, "attitude", None)
        for i, (c, t) in enumerate(options):
            if getattr(c, "name", "") == "孫權-殺殺" and att and att(g, p, t) < 0 and t.hp <= 2:
                return i
        for i, (c, t) in enumerate(options):
            junk = sum(1 for h in p.hand if h.name not in ("桃", "閃", "殺", "無", "無懈", "酒"))
            if getattr(c, "name", "") == "孫權-換牌" and junk >= 2:
                return i


class 孫堅(Char):
    name, faction = "孫堅", "吳"

    def on_targeted(self, g, p, user, card):
        using = getattr(card, "orig", card)  # 正在使用的那張牌不能被選
        if g.in_group:   # 南蠻入侵 / 萬箭齊發 / 突襲 / 飢餓這種「全部人都是對象」的錦囊不算「對你使用」
            return
        if g.is_trick(card) and g.trigger_ok(p, "孫堅-棄牌") and _may(g, p, "孫堅-棄牌"):
            pool = [x for x in user.hand + user.equip_cards() + [j for j in user.judge if j.name != "閃電"]
                    if x is not using]
            if pool:
                c = g.rng.choice(pool)
                g.remove_from(user, c)
                g.discard.append(getattr(c, "orig", c))
                g.link(f"{p.name}[孫堅] 棄置 {user.name} 的一張牌")
        elif card.kind == "basic" and g.trigger_ok(p, "孫堅-奪牌") and _may(g, p, "孫堅-奪牌"):
            pool = [x for x in user.hand + user.equip_cards() if x is not using]
            if pool:
                c = g.rng.choice(pool)
                g.remove_from(user, c)
                p.hand.append(c)
                g.link(f"{p.name}[孫堅] 獲得 {user.name} 的一張牌")


class 丁奉(Char):
    name, faction = "丁奉", "吳"

    def on_any_damaged(self, g, p, tgt, n):
        if not p.flipped and tgt is not p:   # 不含自己; 每次傷害都各抽一次 (萬箭齊發 7 人受傷 = 抽 7 次)
            g.new_dmg_chain()  # 結算完才發動: 另開一條新連鎖
            g.link(f"{p.name}[丁奉] 有人受傷,抽 {n} 張")
            g.draw(p, n)

    def skill_options(self, g, p):
        def act(g, p, c):   # c = 玩家選的那件裝備 (選項的「目標」)
            g.log(f"  {p.name}[丁奉] 棄置 {c},抽 1 張")
            g.discard_card(p, c)
            g.draw(p, 1)
        return [(SkillAct("丁奉-棄裝備抽牌", act), c) for c in p.equip_cards()]   # 同一個技能,目標是裝備

    def ai_choose(self, g, p, options):
        if len(p.hand) <= 1:
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", "") == "丁奉-棄裝備抽牌":
                    return i


class 呂蒙(Char):
    name, faction = "呂蒙", "吳"

    def skip_discard(self, g, p): return g.sha_used == 0

    last = -1   # 上次發動的 g.turn_id: 每個回合 (自己或別人的) 最多一次

    def _five(self, g, p):
        if self.last == g.turn_id or not g.trigger_ok(p, "呂蒙-判定五次"):
            return
        self.last = g.turn_id
        g.link(f"{p.name}[呂蒙] 判定五次")
        for _ in range(5):
            j = g.flip_judge(p)
            if j.color == "紅":
                g.heal(p)
            else:
                g.draw(p, 1)
        g.log(f"  {p.name} 判定完 -> 體力 {p.hp}, 手牌 {len(p.hand)}")

    def on_flipped(self, g, p): self._five(g, p)
    def on_dying(self, g, p): self._five(g, p)


class 魏延(Char):
    name, faction = "魏延", "蜀"
    immune_delayed = True

    def on_deal_damage(self, g, p, tgt, n):
        if g.trigger_ok(p, "魏延-抽牌") and _may(g, p, "魏延-抽牌"):
            g.new_dmg_chain()  # 結算完才發動: 另開一條新連鎖
            g.link(f"{p.name}[魏延] 造成傷害,抽 1 張")
            g.draw(p, 1)


class 曹丕(Char):
    name, faction = "曹丕", "魏"

    def views(self, g, p, c): return ["兵"] if c.name == "殺" else []

    def blocks_target(self, g, p, card):
        return card.kind == "trick" and card.color == "黑"

    def takes_dead_cards(self, g, p): return True


class 許褚(Char):
    name, faction = "許褚", "魏"

    def draw_count(self, g, p):
        if p.agent.choose_skill(g, p, "許褚-放棄抽牌"):
            p.turn_flags["xc"] = True
            g.log(f"  {p.name} 放棄抽牌: 本回合對他人傷害 x2")
            return 0
        return 2

    def dmg_dealt_mod(self, g, p, tgt, n):
        return n * 2 if p.turn_flags.get("xc") else n

    def views(self, g, p, c): return ["決"] if c.name == "殺" else []

    def discard_amount(self, g, p, extra):  # 可以不照體力棄牌,改成只棄 1 張手牌
        if extra > 1 and p.hand and p.agent.choose_skill(g, p, "許褚-只棄一張"):
            g.log(f"  {p.name}[許褚] 不依體力棄牌,只棄 1 張")
            return 1
        return extra


class 趙雲(Char):
    name, faction = "趙雲", "蜀"

    def blocks_target(self, g, p, card): return card.name in ("順", "樂")

    def skill_options(self, g, p):
        if p.turn_flags.get("zy"):
            return []
        return [(SkillAct("趙雲-棄牌或扣血", self._run), t) for t in g.others(p) if t.hand]

    def _run(self, g, p, t):
        p.turn_flags["zy"] = True
        # 被指定的人自己選: 棄 1 張手牌,否則扣 1 點體力 (可閃)
        pick = t.agent.choose_option(g, t, "趙雲-棄牌或扣血", ["棄 1 張手牌", "扣 1 點體力 (可閃)"]) if t.hand else 1
        if pick == 0 and t.hand:
            c = t.agent.choose_discard(g, t, 1, list(t.hand))[0]
            g.discard_card(t, c)
            g.log(f"  {p.name}[趙雲] 令 {t.name} 棄 1 張手牌: {c}")
        else:
            g.log(f"  {p.name}[趙雲] 令 {t.name} 扣 1 點體力 (可閃)")
            if not g.need_response(t, "閃", {"attacker": p}):
                g.damage(p, t, 1)

    def ai_choose(self, g, p, options):
        att = getattr(p.agent, "attitude", None)
        for i, (c, t) in enumerate(options):
            if getattr(c, "name", "") == "趙雲-棄牌或扣血" and att and att(g, p, t) < 0:
                return i


class 曹仁(Char):
    name, faction = "曹仁", "魏"

    def after_discard(self, g, p):
        total = 0
        for _ in range(2):  # 展示手牌,同色就抽 2;再重複一次
            if p.hand and len({c.color for c in p.hand}) == 1 and g.trigger_ok(p, f"曹仁-展示{total}") and _may(g, p, "曹仁-展示"):
                g.link(f"{p.name}[曹仁] 展示手牌全是{p.hand[0].color}色,抽 2 張")
                g.last_reveal = ("曹仁 展示手牌", [(p.idx, c) for c in p.hand])   # 桌面中央讓大家看到
                g.draw(p, 2)
                total += 2
            else:
                break
        if total >= 2 and p.hp < p.maxhp and g.trigger_ok(p, "曹仁-回血"):
            g.heal(p)
            g.log(f"  {p.name}[曹仁] 回 1 點體力 -> 體力 {p.hp}")


class 孟獲(Char):
    name, faction = "孟獲", "蜀"

    def hand_limit(self, g, p, h): return 99   # 不用棄牌
    def dyn_maxhp(self, p): return len(p.hand) + 1   # 手牌數 + 1 = 體力上限,隨時變動

    def end_turn(self, g, p):
        if p.turn_flags.get("tricks"):
            g.log(f"  {p.name}[孟獲] 本回合出了錦囊牌,扣 1 點體力")
            g.damage(None, p, 1)

    def on_any_damaged(self, g, p, tgt, n):  # 別人出的牌造成傷害,可以獲得那張牌
        card = g.cur_card
        if card is None or g.cur_user is p:
            return
        real = getattr(card, "orig", card)
        if real in g.discard and g.trigger_ok(p, "孟獲-獲得") and _may(g, p, "孟獲-獲得"):
            g.discard.remove(real)
            p.hand.append(real)
            g.new_dmg_chain()  # 結算完才發動: 另開一條新連鎖
            g.link(f"{p.name}[孟獲] 獲得造成傷害的 {real}")


class 陸遜(Char):
    name, faction = "陸遜", "吳"

    def views(self, g, p, c):
        if c.kind == "trick" and c.name != "無" and not p.turn_flags.get("lx"):
            return ["無"]
        return []

    def on_view_used(self, g, p, card):
        if card.name == "無":
            p.turn_flags["lx"] = True

    def blocks_target(self, g, p, card): return card.name in ("順", "樂")


class 黃蓋(Char):
    name, faction = "黃蓋", "吳"

    def views(self, g, p, c): return ["過"] if c.name == "殺" else []

    def sha_targets(self, g, p, targets):  # 周瑜在場時,只能對他用殺
        zy = [q for q in g.alive_players() if q._char.name == "周瑜"]
        return [t for t in targets if t in zy] if zy else targets

    def skill_options(self, g, p):
        return [(SkillAct("黃蓋-苦肉", self._run), None)]  # 次數不限

    def _run(self, g, p, t):
        g.log(f"  {p.name}[黃蓋] 強制扣 1 點體力,抽 1 張")
        g.damage(None, p, 1)
        if p.alive:
            g.draw(p, 1)

    def ai_choose(self, g, p, options):
        if p.hp >= 3 and len(p.hand) <= 2:
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", "") == "黃蓋-苦肉":
                    return i


class 龐德(Char):
    name, faction = "龐德", "群"

    def views(self, g, p, c): return ["萬"] if c.name == "閃" else []
    def dist_mod(self, g, p, t): return -1

    def on_other_trick(self, g, p, user, real):
        if p.turn_flags.get("pd_turn") != g.turn_id and real in g.discard:
            p.turn_flags["pd_turn"] = g.turn_id
            g.discard.remove(real)
            p.hand.append(real)
            g.new_dmg_chain()  # 結算完才發動: 另開一條新連鎖
            g.link(f"{p.name}[龐德] 獲得 {user.name} 使用的 {real}")


class 袁紹(Char):
    name, faction = "袁紹", "群"

    def views(self, g, p, c): return ["萬"] if c.name == "閃" else []

    def draw_count(self, g, p):
        if p.agent.choose_skill(g, p, "袁紹-多抽2張"):
            p.turn_flags["ys"] = True
            g.log(f"  {p.name}[袁紹] 多抽 2 張,本回合不可出殺")
            return 4
        return 2

    def sha_limit(self, g, p): return 0 if p.turn_flags.get("ys") else 1


class 張遼(Char):
    name, faction = "張遼", "魏"

    def views(self, g, p, c):   # 每張紅牌可裝備成八卦陣、黑牌裝備成仁王盾
        return ["八卦陣"] if c.color == "紅" else ["仁王盾"] if c.color == "黑" else []

    def skill_options(self, g, p):  # 一張殺打場上所有其他人
        lim = p.char.sha_limit(g, p)
        shas = [c for c in p.hand if c.name == "殺"]
        if shas and g.others(p) and (lim is None or g.sha_used < lim or p.has_weapon("諸葛連弩")):
            return [(SkillAct("張遼-殺全部人", self._all), None)]
        return []

    def _all(self, g, p, t):
        sha = next(c for c in p.hand if c.name == "殺")
        g.discard_card(p, sha)
        g.sha_used += 1
        g.log(f"  {p.name}[張遼] 一張殺打場上所有其他人")
        g.cur_card, g.cur_user = sha, p
        jiu = g.jiu
        for q in g.others(p):
            if not p.alive:
                break
            g.jiu = jiu
            g.use_sha(p, q, sha, count=False)
        g.jiu = False

    def ai_choose(self, g, p, options):
        att = getattr(p.agent, "attitude", None)
        if not att:
            return None
        foes = sum(1 for q in g.others(p) if att(g, p, q) < 0)
        friends = sum(1 for q in g.others(p) if att(g, p, q) >= 1)
        if foes >= 2 and foes > friends:
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", "") == "張遼-殺全部人":
                    return i


class 馬良(Char):
    name, faction = "馬良", "蜀"

    def immune_nature(self, g, p, nature): return not p.all_cards()

    def after_draw(self, g, p, drawn):
        """抽牌後把至少 1 張牌交給另一人,他多一個出牌階段;沒出那張牌就扣 1 點體力並還牌。"""
        others = g.others(p)
        if not others or not drawn:
            return
        pick = p.agent.choose_give(g, p, drawn, others)
        if not pick:
            return
        x, cards = pick
        if not g.trigger_ok(p, "馬良-交牌"):
            return
        g.link(f"{p.name}[馬良] 把 {len(cards)} 張牌交給 {x.name},{x.name} 多一個出牌階段")
        for c in cards:
            p.hand.remove(c)
            x.hand.append(c)
        g.extra_play_phase(x)
        if not x.alive:
            return
        unplayed = [c for c in cards if c in x.hand]
        if unplayed:
            g.log(f"  {x.name} 沒出給的牌,扣 1 點體力並還牌")
            for c in unplayed:
                x.hand.remove(c)
                p.hand.append(c)
            g.damage(p, x, 1)


class 司馬昭(Char):
    name, faction = "司馬昭", "魏"
    next_double = False

    def on_sha_dodged(self, g, p, tgt):
        self.next_double = True
        g.log(f"  {p.name}[司馬昭] 殺被閃,下一回合傷害 x2")

    def on_turn_start(self, g, p):
        if self.next_double:
            p.turn_flags["sm_double"] = True
            self.next_double = False

    def dmg_dealt_mod(self, g, p, tgt, n):
        return n * 2 if p.turn_flags.get("sm_double") else n

    def on_any_trick(self, g, p, user, real):
        if not g.trigger_ok(p, "司馬昭-判定") or not _may(g, p, "司馬昭-判定"):
            return
        g.new_dmg_chain()  # 結算完才發動: 另開一條新連鎖
        j = g.flip_judge(p)
        g.link(f"{p.name}[司馬昭] 有人使用錦囊,判定 {j}")
        if j.color == "黑":
            g.draw(p, 1)
        else:
            g.heal(p)


class 夏侯惇(Char):
    name, faction = "夏侯惇", "魏"

    def on_sha_hit(self, g, p, tgt, n):
        if not g.trigger_ok(p, "夏侯惇-判定"):
            return
        j = g.flip_judge(p)
        g.link(f"{p.name}[夏侯惇] 殺造成傷害,判定 {j}")
        if j.color == "紅":
            g.heal(p)
        elif tgt.alive:
            g.log(f"  黑色: 傷害 +1")
            g.damage(p, tgt, 1)


class 徐晃(Char):
    name, faction = "徐晃", "魏"
    equip_safe = True

    def views(self, g, p, c): return ["兵"] if c.name == "殺" else []


class 曹洪(Char):
    name, faction = "曹洪", "魏"

    def on_any_damaged(self, g, p, tgt, n):
        if tgt is not p and p.hp < p.maxhp and g.trigger_ok(p, "曹洪-回血"):   # 滿血就不發動 (不然連鎖 / 特效白跑一次)
            g.new_dmg_chain()  # 結算完才發動: 另開一條新連鎖
            g.link(f"{p.name}[曹洪] 有人受到 {n} 點傷害,回 {n} 點體力")
            g.heal(p, n)

    def on_turn_start(self, g, p):  # 判定: 黑 與另一人交換手牌;紅 判定區的牌全部無效
        if not g.trigger_ok(p, "曹洪-判定") or not _may(g, p, "曹洪-判定"):
            return
        j = g.flip_judge(p)
        g.link(f"{p.name}[曹洪] 判定 {j}")
        if j.color == "黑":
            others = [q for q in g.others(p)]
            if others:
                q = p.agent.choose_target(g, p, "曹洪-換牌", others)
                g.log(f"  {p.name}[曹洪] 與 {q.name} 交換手牌")
                p.hand, q.hand = q.hand, p.hand
        else:
            for d in list(p.judge):
                p.judge.remove(d)
                g.discard.append(getattr(d, "orig", d))
            g.log("  判定區的延時錦囊全部無效")


class 鄧艾(Char):
    name, faction = "鄧艾", "魏"

    def blocks_target(self, g, p, card): return card.name == "兵"

    def group_damage(self, g, p, trick): return 2 if trick in ("南", "萬") else 1

    def on_other_trick(self, g, p, user, real):  # 別人使用非延時錦囊: 他扣 1 點體力 (可閃)
        if real.name in DELAYED_NAMES or not user.alive:
            return
        if g.trigger_ok(p, "鄧艾-扣血"):
            g.new_dmg_chain()   # 別人的錦囊結算完才發動: 另開一條新連鎖 (不接在那張牌的連鎖後面)
            g.link(f"{p.name}[鄧艾] {user.name} 使用錦囊,扣 1 點體力 (可閃)")
            if not g.need_response(user, "閃", {"attacker": p}):
                g.damage(p, user, 1)


class 劉備(Char):
    name, faction = "劉備", "蜀"
    ren = 0

    def blocks_target(self, g, p, card): return card.name == "殺" and self.ren >= 3

    def lose_marks(self, g, p):
        if self.ren:
            g.log(f"  {p.name}[劉備] 被翻面,{self.ren} 個仁全部消失")
            self.ren = 0

    def skill_options(self, g, p):
        opts = []
        tricks = [c for c in p.hand if g.is_trick(c)]
        if tricks and self.ren < 10:   # 仁最多 10 個
            opts.append((SkillAct("劉備-棄錦囊得仁", lambda g, p, t: self._gain(g, p, tricks)), None))
        if self.ren > 0:
            opts += [(SkillAct("劉備-仁回血", self._heal), q) for q in g.alive_players() if q.hp < q.maxhp]
        return opts

    def _gain(self, g, p, tricks):
        c = p.agent.choose_discard(g, p, 1, tricks)[0]
        g.discard_card(p, c)
        self.ren += 1
        g.log(f"  {p.name}[劉備] 棄 {c},獲得 1 個仁 (共 {self.ren})")

    def on_dying_help(self, g, p, tgt):   # 瀕死的人 (自己或其他玩家) 也可以用仁救,每次 -1 仁 +1 體力
        while g.cur is p and self.ren > 0 and p.alive and tgt.alive and tgt.hp <= 0 and p.agent.choose_skill(g, p, f"劉備-仁救 {tgt.name}"):
            self._heal(g, p, tgt)

    def _heal(self, g, p, t):
        self.ren -= 1
        g.heal(t)
        g.log(f"  {p.name}[劉備] 消耗 1 個仁,{t.name} 回 1 點體力 -> 體力 {t.hp} (剩 {self.ren})")

    def ai_choose(self, g, p, options):
        att = getattr(p.agent, "attitude", None)
        best = None
        for i, (c, t) in enumerate(options):
            if getattr(c, "name", "") == "劉備-仁回血" and att and att(g, p, t) >= 1:
                if best is None or t.hp < options[best][1].hp:
                    best = i
        if best is not None:
            return best
        junk = [c for c in p.hand if c.kind == "trick" and c.name not in ("無", "無懈", "桃園", "決", "火攻")]
        if junk and self.ren < 3:   # 有 3 個仁就已經殺不到了,再存只是白白丟牌 (十個劉備會永遠打不下去)
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", "") == "劉備-棄錦囊得仁":
                    return i


class 姜維(Char):
    name, faction = "姜維", "蜀"
    bonus = 0

    def views(self, g, p, c): return ["發"] if c.name == "增" else []

    def draw_count(self, g, p):
        n = 2 + self.bonus
        if self.bonus:
            g.log(f"  {p.name}[姜維] 上回合棄 {self.bonus} 張,多抽 {self.bonus} 張")
        self.bonus = 0
        return n

    def after_discard(self, g, p):
        self.bonus = min(4, p.turn_flags.get("discarded", 0))


class 諸葛亮(Char):
    name, faction = "諸葛亮", "蜀"

    def cap_damage(self, g, p, n): return 0 if not p.hand else n
    def blocks_target(self, g, p, card): return card.kind == "trick" and not p.hand
    def virtual_bagua(self, g, p): return True  # 沒有防具時等於裝了八卦陣


class 張角(Char):
    name, faction = "張角", "群"

    def views(self, g, p, c): return ["南"] if c.name == "殺" else []

    def skill_options(self, g, p):
        if p.turn_flags.get("zj") or p.hp >= p.maxhp or not p.all_cards():
            return []
        return [(SkillAct("張角-捨牌回血", self._run), None)]

    def _run(self, g, p, t):
        p.turn_flags["zj"] = True
        x = min(p.maxhp - p.hp, len(p.all_cards()))
        x = max(1, min(x, p.agent.choose_count(g, p, "張角-捨牌回血", x)))
        for c in p.agent.choose_discard(g, p, x, p.all_cards()):
            g.discard_card(p, c)
        g.heal(p, x)
        g.log(f"  {p.name}[張角] 捨 {x} 張,回 {x} 血 -> 體力 {p.hp}")

    def ai_choose(self, g, p, options):
        junk = sum(1 for c in p.hand if c.name not in ("桃", "閃", "殺", "無", "無懈", "酒"))
        if junk >= 1 and p.hp <= p.maxhp - 1:
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", "") == "張角-捨牌回血":
                    return i


class 華佗(Char):
    name, faction = "華佗", "群"

    def views(self, g, p, c): return ["桃"] if g.cur is p and c.name == "殺" else []

    def as_card(self, g, p, c, name):
        return name == "桃" and ((g.cur is not p and c.color == "紅") or (g.cur is p and c.name == "殺"))

    def blocks_target(self, g, p, card): return card.name in ("決", "南", "萬")


class 劉協(Char):
    name, faction = "劉協", "群"

    def plain_immune(self, g, p): return True

    def on_turn_start(self, g, p):  # 別人各棄 1 張手牌,否則扣 1 點體力
        g.link(f"{p.name}[劉協] 回合開始: 其他人各棄 1 張手牌,否則扣 {g.dmg_preview(p, 1, bonus=True)} 點體力")
        for q in g.others(p):
            if not q.alive:
                continue
            c = q.agent.respond(g, q, "劉協棄牌", list(q.hand), {"source": p}) if q.hand else None
            if c:
                g.discard_card(q, c)
                g.log(f"  {q.name} 棄置 {c}")
            else:
                g.damage(p, q, 1)


class 顏良文醜(Char):
    name, faction = "顏良&文醜", "群"

    def no_range(self, g, p): return True

    def virtual_renwang(self, g, p): return True  # 沒有防具時視為佩戴仁王盾


class 滿寵(Char):
    name, faction = "滿寵", "魏"

    def views(self, g, p, c): return ["兵"] if c.name == "火攻" else []
    def dist_in(self, g, p, a): return 1  # 別人攻擊我的距離 +1

    def on_damaged(self, g, p, src, n):  # 被殺並受傷: 對方扣 1 點體力 (可閃),我抽 2 張
        card = g.cur_card
        if src is None or src is p or card is None or card.name != "殺" or g.cur_user is not src:
            return
        g.new_dmg_chain()   # 受傷之後才發動: 另開一條新連鎖
        if not g.trigger_ok(p, "滿寵-反擊"):
            return
        g.link(f"{p.name}[滿寵] 被殺受傷: {src.name} 扣 1 點體力 (可閃),自己抽 2 張")
        g.draw(p, 2)
        if src.alive and not g.need_response(src, "閃", {"attacker": p}):
            g.damage(p, src, 1)


class 公孫瓚(Char):
    name, faction = "公孫瓚", "群"

    def dist_mod(self, g, p, t):  # 3 點體力以上 -1;1 點體力以下 +1;剛好 2 點體力沒有效果
        return -1 if p.hp > 2 else (1 if p.hp < 2 else 0)

    def as_card(self, g, p, c, name): return name == "調" and c.name == "閃"


class 呂布(Char):
    name, faction = "呂布", "群"
    used = False

    def sha_limit(self, g, p): return None
    def skip_discard(self, g, p): return True

    def skill_options(self, g, p):
        if self.used or g.void:
            return []
        return [(SkillAct("呂布-無效全場", self._run), None)]

    def _run(self, g, p, t):
        self.used = True
        g.void = True
        g.log(f"  {p.name}[呂布] 遊戲中一次: 本回合全場效果無效 (武將技能、強/弱/反、錦囊、武器、防具、坐騎)")

    def ai_choose(self, g, p, options):
        foes = sum(1 for q in g.others(p) if q.hp >= 3 and len(q.hand) >= 4)
        if p.hp <= 1 and foes:
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", "") == "呂布-無效全場":
                    return i


class 典韋(Char):
    name, faction = "典韋", "魏"
    damage_only_sha = True
    no_jiu_target = True
    no_armor = True
    immune_names = ("閃電", "樂", "兵")

    def blocks_target(self, g, p, card): return card.name in ("樂", "兵")


class 司馬懿(Char):
    name, faction = "司馬懿", "魏"

    def on_damaged(self, g, p, src, n):  # 拿走造成傷害的牌 (一回合一次)
        card = g.cur_card
        if card is None or p.turn_flags.get("sy_" + str(g.turn_id)):
            return
        real = getattr(card, "orig", card)
        if real not in g.discard:
            return
        g.new_dmg_chain()   # 受傷之後才發動: 另開一條新連鎖
        if not g.trigger_ok(p, "司馬懿-拿牌"):
            return
        p.turn_flags["sy_" + str(g.turn_id)] = True
        g.discard.remove(real)
        p.hand.append(real)
        g.link(f"{p.name}[司馬懿] 受傷,拿走造成傷害的牌 {real}")

    def replace_draw(self, g, p):  # 放棄抽牌,改抽別人一張手牌
        cands = [q for q in g.others(p) if q.hand]
        if not cands or not p.agent.choose_skill(g, p, "司馬懿-奪牌"):
            return False
        t = p.agent.choose_target(g, p, "司馬懿-奪牌", cands)
        c = g.rng.choice(t.hand)
        t.hand.remove(c)
        p.hand.append(c)
        g.log(f"  {p.name}[司馬懿] 放棄抽牌,改抽 {t.name} 的一張手牌")
        return True


class 崔琰(Char):
    name, faction = "崔琰", "魏"
    cnt, off = 0, False

    def on_turn_start(self, g, p): self.cnt, self.off = 0, False

    def on_other_trick(self, g, p, user, real):
        if self.off or not g.trigger_ok(p, "崔琰-抽牌"):
            return
        g.new_dmg_chain()  # 結算完才發動: 另開一條新連鎖
        g.link(f"{p.name}[崔琰] 有人使用錦囊,抽 1 張")
        g.draw(p, 1)
        self.cnt += 1
        if self.cnt >= 3:
            self.cnt = 0
            if p.agent.choose_skill(g, p, "崔琰-再抽2張"):
                g.draw(p, 2)
                self.off = True
                g.log(f"  {p.name}[崔琰] 再多抽 2 張,技能無效直到下個自己的回合")


class 曹植(Char):
    name, faction = "曹植", "魏"

    def views(self, g, p, c): return ["五"] if c.name == "桃" else []

    def on_turn_start(self, g, p):  # 七輪後勝利 (輪數從這個人變成曹植的時候開始算: 化身 / 偽裝 / 交換武將都一樣)
        st = g.__dict__.setdefault("_cz_rounds", {})   # 存在這局上: 化身 (左慈) 的曹植每次都是新實例,連續幾輪都選曹植才接著算
        base, last = st.get(p.idx, (None, None))
        if base is None or g.round - last > (1 if p._char is not self else 3):   # 第一次擁有 (或中斷了才又變成他): 從第一輪重新算
            base = g.round - 1
        st[p.idx] = (base, g.round)
        if g.round - base >= 7:   # 第 7 輪開頭就贏
            from engine import GameOver
            if p._char is not self and p.alias and self not in p.alias:   # 左慈: 同一個回合開頭已換了新化身,勝利畫面要顯示真正獲勝的曹植
                p.alias = [self]
            g.winner = "曹植 (七輪後獨自勝利)"
            g.solo_winner = p.idx   # 結算 / 畫面用: 只有這個座位的人贏,其他人 (含同陣營) 都算輸
            raise GameOver()

    def skill_options(self, g, p):
        if p.turn_flags.get("cz2"):
            return []
        return [(SkillAct("曹植-洗手牌", self._run), None)]

    def _run(self, g, p, t):
        p.turn_flags["cz2"] = True
        alive = [q for q in g.alive_players() if q is not p]   # 除了自己
        pool = [c for q in alive for c in q.hand]
        sizes = [len(q.hand) for q in alive]
        g.rng.shuffle(pool)
        k = 0
        for q, s in zip(alive, sizes):
            q.hand = pool[k:k + s]
            k += s
        g.log(f"  {p.name}[曹植] 除了他以外全部人的手牌 (不含裝備) 隨機交換")

    def ai_choose(self, g, p, options):
        mine = len(p.hand)
        avg = sum(len(q.hand) for q in g.others(p)) / max(1, len(g.others(p)))
        if mine <= 1 and avg >= 3:
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", "") == "曹植-洗手牌":
                    return i


class 鐘繇(Char):
    name, faction = "鐘繇", "魏"
    bans = frozenset({"強", "弱", "反"})  # 全場禁用,翻面時亦同

    def trick_lock(self, g, p): return not p.hand   # 若你沒有手牌,別人無法使用錦囊牌


class 張嶷(Char):
    name, faction = "張嶷", "蜀"

    def as_card(self, g, p, c, name): return name == "閃" and c.name == "殺" and p.hp == 1

    def on_turn_start(self, g, p):  # 回合開始前和一名別人同時展示手牌,同色: 他扣 1 點體力、我回 1 點體力
        if not p.hand:
            return
        cands = [q for q in g.others(p) if q.hand]
        if not cands or not g.trigger_ok(p, "張嶷-同時亮牌") or not _may(g, p, "張嶷-同時亮牌"):
            return
        t = p.agent.choose_target(g, p, "張嶷-同時亮牌", cands)
        a, b = p.agent.show_card(g, p, list(p.hand)), t.agent.show_card(g, t, list(t.hand))
        g.link(f"{p.name}[張嶷] 與 {t.name} 同時亮牌: {a} / {b}")
        g.last_reveal = ("張嶷 同時亮牌", [(p.idx, a), (t.idx, b)])   # 桌面中央讓大家看到
        if a.color == b.color:
            g.heal(p)
            g.damage(p, t, 1)


class 王允(Char):
    name, faction = "王允", "群"
    sha_reflect = True

    def skill_options(self, g, p):
        if p.turn_flags.get("wy2"):
            return []
        return [(SkillAct("王允-全員重抽", self._run), None)]

    def _run(self, g, p, t):
        p.turn_flags["wy2"] = True
        for q in g.alive_players():   # 每人各棄置自己的一張手牌,再各抽一張
            if q.hand:
                c = q.agent.choose_discard(g, q, 1, list(q.hand))[0]
                g.discard_card(q, c)
            elif q is not p:
                continue
            g.draw(q, 2 if q is p else 1)
        g.log(f"  {p.name}[王允] 每名角色各棄置一張手牌再各抽一張,王允自己抽兩張")

    def ai_choose(self, g, p, options):
        junk = sum(1 for c in p.hand if c.name not in ("桃", "閃", "無", "無懈", "殺", "酒"))
        others = sum(len(q.hand) for q in g.others(p))
        if junk >= 1 and others >= 3:
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", "") == "王允-全員重抽":
                    return i


class 曹操(Char):
    name, faction = "曹操", "魏"
    shi = 0
    thunder_reflect = True

    def on_sha_used(self, g, p, card):
        if self.shi >= 10:   # 弒最多 10 個
            g.log(f"  {p.name}[曹操] 弒已達上限 10 個")
            return
        self.shi += 1
        g.log(f"  {p.name}[曹操] 獲得 1 個弒 (共 {self.shi})")

    def skill_options(self, g, p):
        return [(SkillAct("曹操-弒抽牌", self._run), None)] if self.shi > 0 else []

    def _run(self, g, p, t):
        self.shi -= 1
        g.draw(p, 1)
        g.log(f"  {p.name}[曹操] 消耗 1 個弒,抽 1 張 (剩 {self.shi})")

    def ai_choose(self, g, p, options):
        for i, (c, t) in enumerate(options):
            if getattr(c, "name", "") == "曹操-弒抽牌":
                return i


class 曹叡(Char):
    name, faction = "曹叡", "魏"
    no_thunder_unflip = True

    def on_other_turn_start(self, g, p, cur):  # 別人回合開始前判定: 基本牌交給別人,錦囊自己拿
        if not g.trigger_ok(p, "曹叡-判定") or not p.agent.choose_skill(g, p, "曹叡-判定"):
            return
        j = g.flip_judge(p)
        real = getattr(j, "orig", j)
        g.link(f"{p.name}[曹叡] 判定 {j}")
        if real in g.discard and j.kind in ("basic", "trick"):
            others = [q for q in g.others(p)]
            if j.kind == "trick":
                g.discard.remove(real)
                p.hand.append(real)
                g.log(f"  錦囊牌: {p.name} 獲得 {real}")
            elif others:
                q = p.agent.choose_target(g, p, "曹叡-交牌", others)
                g.discard.remove(real)
                q.hand.append(real)
                g.log(f"  基本牌: 交給 {q.name}")

    def on_damaged(self, g, p, src, n):
        if p.hp <= 1 and p.alive and not p.flipped:
            p.flipped = True
            g.log(f"  {p.name}[曹叡] 體力 1 以下,翻面 (直到 2 點體力以上)")

    def on_healed(self, g, p):
        if p.flipped and p.hp >= 2:
            p.flipped = False
            g.log(f"  {p.name}[曹叡] 回到 2 點體力以上,翻回正面")

    def stay_flipped(self, g, p): return p.hp <= 1

    def blocks_target(self, g, p, card): return card.name == "毒"

class 張昭(Char):
    name, faction = "張昭", "群"
    fan_double = True

    def on_damaged(self, g, p, src, n):  # 傷害來源翻面一回合
        if src is None or src is p or not src.alive or p.flipped:
            return
        g.new_dmg_chain()   # 受傷之後才發動: 另開一條新連鎖
        if not g.trigger_ok(p, "張昭-翻面"):
            return
        g.link(f"{p.name}[張昭] 受傷,{src.name} 翻面一回合")
        g.flip_char(src)


class 邯鄲淳(Char):
    name, faction = "邯鄲淳", "魏"

    def on_other_basic(self, g, p, user, real):  # 判定: 紅 回手牌數的血,黑 抽體力張數
        if getattr(self, "used_turn", None) == g.turn_id or not g.trigger_ok(p, "邯鄲淳-判定") or not _may(g, p, "邯鄲淳-判定"):   # 一回合一次
            return
        self.used_turn = g.turn_id
        g.new_dmg_chain()  # 結算完才發動: 另開一條新連鎖
        j = g.flip_judge(p)
        g.link(f"{p.name}[邯鄲淳] {user.name} 使用基本牌,判定 {j}")
        if j.color == "紅":
            g.heal(p, len(p.hand))
        else:
            g.draw(p, max(p.hp, 0))


class 周胤(Char):
    name, faction = "周胤", "吳"
    tao_no_heal = True
    gu_no_loss = True


class 沮授(Char):
    name, faction = "沮授", "群"

    def pre_damage(self, g, p, src, n, nature):  # 棄 1 張手牌,把傷害改成 1 點轉給另一個人
        if not p.hand or not g.others(p) or not g.trigger_ok(p, "沮授-轉移"):
            return n
        if not p.agent.choose_skill(g, p, "沮授-轉移"):
            return n
        c = p.agent.choose_discard(g, p, 1, list(p.hand))[0]
        g.discard_card(p, c)
        t = p.agent.choose_target(g, p, "沮授-轉移", g.others(p))
        g.link(f"{p.name}[沮授] 棄 {c},把傷害轉為 1 點轉給 {t.name}")
        from types import SimpleNamespace   # 傷害轉給他 = 他被指定為目標: 先讓他有機會接連鎖用 ⚡
        g.sha_window(p, t, SimpleNamespace(name="沮授轉移的傷害"), "對你使用沮授轉移的傷害")
        g.damage(src, t, 1, nature=nature, _bonus=False, _mods=False)   # 轉移的傷害保留屬性,也不再乘一次加成
        return 0


class 太史慈(Char):
    name, faction = "太史慈", "吳"
    equip_void = True

    def after_draw(self, g, p, drawn):  # 抽牌階段沒抽到錦囊牌,再抽一次
        if p.turn_flags.get("tsc") or any(g.is_trick(c) for c in drawn):
            return
        p.turn_flags["tsc"] = True
        if not _may(g, p, "太史慈-再抽"):
            return
        extra = g.draw(p, self.draw_count(g, p))
        g.log(f"  {p.name}[太史慈] 沒抽到錦囊,再進行一次抽牌階段: {len(extra)} 張")


class 周魴(Char):
    name, faction = "周魴", "吳"

    def skill_options(self, g, p):
        if p.turn_flags.get("zf") or not p.all_cards():
            return []
        return [(SkillAct("周魴-棄牌扣血", self._run), t) for t in g.others(p)]

    def _run(self, g, p, t):
        p.turn_flags["zf"] = True
        pool = p.all_cards()
        x = max(1, min(3, len(pool), p.agent.choose_count(g, p, "周魴-棄牌扣血", min(3, len(pool)))))
        for c in p.agent.choose_discard(g, p, x, pool):
            g.discard_card(p, c)
        g.log(f"  {p.name}[周魴] 棄 {x} 張,令 {t.name} 扣 {x} 血 (可閃)")
        if not g.need_response(t, "閃", {"attacker": p}):
            g.damage(p, t, x)

    def ai_choose(self, g, p, options):
        junk = [c for c in p.hand if c.name not in ("桃", "閃", "殺", "無", "無懈", "酒")]
        att = getattr(p.agent, "attitude", None)
        if len(junk) < 2 or not att:
            return None
        best = None
        for i, (c, t) in enumerate(options):
            if getattr(c, "name", "") == "周魴-棄牌扣血" and att(g, p, t) <= -1 and (best is None or t.hp < options[best][1].hp):
                best = i
        return best

    def on_turn_start(self, g, p):  # 和場上體力最多的人交換體力 (上限 = 各自體力上限)
        others = g.others(p)
        if not others:
            return
        t = max(others, key=lambda q: q.hp)
        if t.hp <= p.hp or not p.agent.choose_skill(g, p, "周魴-換血"):
            return
        a, b = p.hp, t.hp
        p.hp, t.hp = min(b, p.maxhp), min(a, t.maxhp)
        g.log(f"  {p.name}[周魴] 與 {t.name} 交換體力: {p.name} {a}->{p.hp}, {t.name} {b}->{t.hp}")


class 龐統(Char):
    name, faction = "龐統", "蜀"

    def views(self, g, p, c): return ["鐵"] if c.name == "殺" else []

    used = -1   # 上次發動的回合 (一回合最多一次)

    def on_dying(self, g, p):  # 瀕死: 棄掉所有牌,體力回到 4,抽 4 張,翻回正面 (一回合一次)
        if p.hp > 0 or self.used == g.turn_id or not p.agent.choose_skill(g, p, "龐統-浴火"):
            return
        self.used = g.turn_id
        for c in list(p.all_cards()) + list(p.judge):   # 區域內所有牌 (含判定區的延時錦囊)
            g.discard_card(p, c)
        p.hp = min(4, p.maxhp) if p.maxhp < 4 else 4
        p.flipped = False
        g.draw(p, 4)
        g.log(f"  {p.name}[龐統] 瀕死: 棄掉所有牌,體力回到 {p.hp},抽 4 張,翻回正面")

class 周瑜(Char):
    name, faction = "周瑜", "吳"
    dual_armor = True

    def sha_dodge_need(self, g, p, tgt): return 2  # 對方要出 2 張閃

    def sha_targets(self, g, p, targets):  # 黃蓋在場時,只能對他用殺
        hg = [q for q in g.alive_players() if q._char.name == "黃蓋" and q is not p]
        return [t for t in targets if t in hg] if hg else targets


class 甘寧(Char):
    name, faction = "甘寧", "吳"
    dual_weapon = dual_armor = True

    def views(self, g, p, c):  # 每回合一次,基本牌當無
        return ["無"] if c.kind == "basic" and not p.turn_flags.get("gn") else []

    def on_view_used(self, g, p, card):
        if card.name == "無":
            p.turn_flags["gn"] = True


class 夏侯淵(Char):
    name, faction = "夏侯淵", "魏"
    dual_weapon = dual_armor = True

    def on_other_dodge(self, g, p, user):  # 別人使用閃: 交一張手牌給我,否則扣 1 點體力
        if not user.alive or not g.trigger_ok(p, "夏侯淵-索牌"):
            return
        c = user.agent.respond(g, user, "夏侯淵給牌", list(user.hand), {"source": p}) if user.hand else None
        g.link(f"{p.name}[夏侯淵] {user.name} 使用閃,要交一張手牌 (否則扣 {g.dmg_preview(p, 1, tgt=user, bonus=True)} 點體力)")
        if c:
            user.hand.remove(c)
            p.hand.append(c)
            g.log(f"  {user.name} 交給 {p.name} 一張牌")
        else:
            g.damage(p, user, 1)

class 孔融(Char):
    name, faction = "孔融", "群"
    tao_self_only = True
    last = -1  # 上次發動的 g.turn_id (每個回合最多一次,自己或別人的回合皆可)

    def skill_options(self, g, p):
        if self.last == g.turn_id or not p.hand:
            return []
        return [(SkillAct("孔融-重鑄手牌", self._run), None)]

    offturn_options = skill_options

    def _run(self, g, p, t):
        self.last = g.turn_id
        x = max(1, min(len(p.hand), p.agent.choose_count(g, p, "孔融-重鑄手牌", len(p.hand))))
        for c in p.agent.choose_discard(g, p, x, list(p.hand)):
            g.discard_card(p, c)
        drawn = g.draw(p, x)
        black = sum(1 for c in drawn if c.color == "黑")
        red = sum(1 for c in drawn if c.color == "紅")
        g.log(f"  {p.name}[孔融] 重鑄 {x} 張: 抽到 黑{black} 紅{red}")
        if black:
            g.draw(p, black)
        if red:
            g.heal(p, red)

    def ai_choose(self, g, p, options):
        junk = sum(1 for c in p.hand if c.name not in ("桃", "閃", "殺", "無", "無懈", "酒", "決", "火攻"))
        if junk >= 2:
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", "") == "孔融-重鑄手牌":
                    return i


class 伊籍(Char):
    name, faction = "伊籍", "蜀"

    def skip_discard(self, g, p): return True  # 手牌無上限

    def skill_options(self, g, p):
        if len(p.all_cards()) < 2:
            return []
        return [(SkillAct("伊籍-棄2張", self._run), None)]

    offturn_options = skill_options

    def _run(self, g, p, t):
        for c in p.agent.choose_discard(g, p, 2, p.all_cards()):
            g.discard_card(p, c)
        if p.hp < p.maxhp and p.agent.choose_option(g, p, "伊籍-棄2張", ["抽 1 張牌", "回 1 點血"]) == 1:
            g.heal(p)
            g.log(f"  {p.name}[伊籍] 棄 2 張,回 1 點體力 -> 體力 {p.hp}")
        else:
            g.draw(p, 1)
            g.log(f"  {p.name}[伊籍] 棄 2 張,抽 1 張")

    def ai_choose(self, g, p, options):
        junk = sum(1 for c in p.hand if c.name not in ("桃", "閃", "殺", "無", "無懈", "酒", "決", "火攻"))
        if junk >= 2 and (p.hp < p.maxhp or len(p.hand) <= 4):
            for i, (c, t) in enumerate(options):
                if getattr(c, "name", "") == "伊籍-棄2張":
                    return i

def _may(g, p, skill):
    """技能寫「可以」= 可以選擇要不要發動: 真人會問他發動不發動,電腦照舊一律發動。"""
    return p.agent.choose_skill(g, p, skill) if getattr(p.agent, "is_human", False) else True


def _ally_pick(g, p, cands):
    """AI 選最友好的人;真人則讓他自己選。"""
    if hasattr(p.agent, "attitude"):
        return max(cands, key=lambda q: p.agent.attitude(g, p, q))
    return p.agent.choose_target(g, p, "選擇對象", cands)


def _skill_idx(options, name):
    for i, (c, t) in enumerate(options):
        if getattr(c, "name", "") == name:
            return i


class 張郃(Char):
    name, faction = "張郃", "魏"

    def sha_targets(self, g, p, targets): return [t for t in targets if t.hp > p.hp]

    def skill_options(self, g, p):  # 沒有人可以攻擊時: 抽 5 張並翻面 (每回合一次)
        if p.turn_flags.get("zh"):
            return []
        reach = [t for t in g.others(p) if t.hp > p.hp and (self.no_range(g, p) or g.distance(p, t) <= p.attack_range())]
        return [] if reach else [(SkillAct("張郃-無人可攻擊", self._run), None)]

    def _run(self, g, p, t):
        p.turn_flags["zh"] = True
        g.draw(p, 5)
        g.log(f"  {p.name}[張郃] 沒有可殺的人,抽 5 張並翻面")
        g.flip_char(p)

    def ai_choose(self, g, p, options): return _skill_idx(options, "張郃-無人可攻擊")


class 曹休(Char):
    name, faction = "曹休", "魏"

    def range_floor(self, g, p): return max(0, 4 - p.hp)  # 攻擊距離 = 4 - 體力

    def on_hand_empty(self, g, p):
        if not g.trigger_ok(p, "曹休-無手牌") or not g.others(p):
            return
        if not p.agent.choose_skill(g, p, "曹休-無手牌"):
            return
        g.link(f"{p.name}[曹休] 失去最後一張手牌: 抽 1 張並令一名角色翻面")
        g.draw(p, 1)
        t = p.agent.choose_target(g, p, "曹休-翻面", g.others(p))
        g.flip_char(t)


class 曹沖(Char):
    name, faction = "曹沖", "魏"
    one_card = True

    def on_other_trick(self, g, p, user, real):  # 和使用錦囊的人永遠交換武將 (不可閃;可閃的是「超過一張錦囊扣血」那條)
        if not user.alive or not g.trigger_ok(p, "曹沖-交換"):
            return
        if not p.agent.choose_skill(g, p, "曹沖-交換武將"):
            return
        g.new_dmg_chain()  # 結算完才發動: 另開一條新連鎖
        g.link(f"{p.name}[曹沖] 要和 {user.name} 永遠交換武將")
        p._char, user._char = user._char, p._char
        for q in (p, user):
            q.borrow, q.borrow2, q.alias, q.disguise = [], [], [], []   # 換了武將: 原本複製 / 化身 / 偽裝的狀態不帶過去
            q.maxhp = max(1, q._char.maxhp + g.hp_offset) + (g.lord_bonus if q is g.lord else 0)   # 主公加成 / 難度調整跟著座位走,不跟武將
            q.hp = max(1, min(q.hp, q.maxhp))
        g.log(f"  交換完成: {p.name} / {user.name}")


class 曹真(Char):
    name, faction = "曹真", "魏"
    used = -1
    seen = None

    def pre_damage(self, g, p, src, n, nature):  # 每回合一次阻擋一次傷害
        if self.used == g.turn_id or not p.agent.choose_skill(g, p, "曹真-阻擋"):
            return n
        self.used = g.turn_id
        g.log(f"  {p.name}[曹真] 阻擋了這次傷害")
        return 0

    def on_game_start(self, g, p):  # 開局時場上每有一名魏勢力武將 (含自己),體力上限 +1 (永久)
        n = sum(1 for q in g.players if q._char.faction == "魏")
        if n:
            p.maxhp += n
            p.hp += n
            g.log(f"  {p.name}[曹真] 開局場上有 {n} 名魏勢力,體力上限永久 +{n} -> {p.maxhp}")


class 楊修(Char):
    name, faction = "楊修", "魏"
    used = False
    armed = -1
    acc = 0
    nats = ()   # 吸收的傷害帶有的屬性 (全部同一種屬性才會保留)

    def skill_options(self, g, p):
        return [] if self.used else [(SkillAct("楊修-宣告吸收傷害", self._run), None)]

    offturn_options = skill_options

    def _run(self, g, p, t):
        self.used, self.armed, self.acc, self.nats = True, g.turn_id, 0, ()
        g.log(f"  {p.name}[楊修] 宣告: 這個回合吸收所有傷害,回合結束時判定")

    def ai_choose(self, g, p, options):
        att = getattr(p.agent, "attitude", None)
        if p.hp <= 2 and att and att(g, p, g.cur) < 0:
            return _skill_idx(options, "楊修-宣告吸收傷害")

    def pre_damage(self, g, p, src, n, nature):
        if self.armed == g.turn_id:
            self.acc += n
            self.nats = tuple(set(self.nats) | {nature})
            g.log(f"  {p.name}[楊修] 吸收 {n} 點傷害 (累計 {self.acc})")
            g._absorbed = True
            return 0
        return n

    def on_turn_end(self, g, p, cur):
        if self.armed != g.turn_id:
            return
        self.armed = -1
        acc, self.acc = self.acc, 0
        nat = self.nats[0] if len(self.nats) == 1 else None   # 吸收的都是同一種屬性 → 轉移時保留
        self.nats = ()
        j = g.flip_judge(p)
        g.link(f"{p.name}[楊修] 回合結束判定 {j} (吸收 {acc} 點)")
        if j.color == "紅":
            g.heal(p, acc)
        elif acc and g.others(p):
            t = p.agent.choose_target(g, p, "楊修-轉移傷害", g.others(p))
            g.log(f"  黑色: 把 {acc} 點傷害改由 {t.name} 承受")
            g.damage(p, t, acc, nature=nat, _bonus=False, _mods=False)


class 蔣幹(Char):
    name, faction = "蔣幹", "魏"
    maxhp = 1
    last = -1

    def on_flip_change(self, p, flipped):   # 翻面後技能失效: 體力上限變回 4;翻回來又是 1
        if flipped:
            p.maxhp += 3   # 1 → 4 (主公的額外上限保留)
        else:
            p.maxhp -= 3
            p.hp = min(p.hp, p.maxhp)

    def views(self, g, p, c): return ["調"]  # 所有牌都可以當調虎離山

    def as_card(self, g, p, c, name): return name == "調"

    def on_card_used(self, g, p, user, card):  # 別人在自己回合使用強/弱/反: 跳過他的出牌 (一輪一次)
        if user is p or card.name not in ("強", "弱", "反") or g.cur is not user or self.last == g.round:
            return
        self.last = g.round
        user.turn_flags["skip_rest"] = True
        g.log(f"  {p.name}[蔣幹] {user.name} 使用 {__import__('view').full_name(card.name)},他的回合直接跳過")

    def on_other_draw(self, g, p, cur):  # 別人抽牌階段,我也抽 2 張
        if not _may(g, p, "蔣幹-趁機抽牌"):
            return
        g.draw_phase(p, 2)
        g.log(f"  {p.name}[蔣幹] 趁 {cur.name} 抽牌,也抽 2 張")


class 郭嘉(Char):
    name, faction = "郭嘉", "魏"

    def on_any_judge(self, g, p, who, c):  # 任何人判定翻出的牌 (牌堆頂翻開用來分辨結果的那張): 可以拿走
        if p.flipped or c not in g.discard or not p.agent.choose_skill(g, p, "郭嘉-拿判定牌"):
            return
        g.discard.remove(c)
        p.hand.append(c)
        g.log(f"  {p.name}[郭嘉] 拿走判定牌 {c}")

    def on_equipped(self, g, p, owner, c):   # 別人放置裝備時: 抽 2 張牌或回 1 血
        if not g.trigger_ok(p, "郭嘉-裝備"):
            return
        g.link(f"{p.name}[郭嘉] {owner.name} 放置了 {c}")
        if p.hp < p.maxhp and p.agent.choose_option(g, p, "郭嘉-裝備", ["抽 2 張牌", "回 1 點血"]) == 1:
            g.heal(p)
        else:
            g.draw(p, 2)


class 劉禪(Char):
    name, faction = "劉禪", "蜀"
    cap3 = True
    used = False

    def skill_options(self, g, p):
        if self.used:
            return []
        return [(SkillAct("劉禪-棄光並跳過回合", self._run), t) for t in g.others(p)]

    def _run(self, g, p, t):
        self.used = True
        for c in list(t.all_cards()):
            g.discard_card(t, c)
        t.skip_turn = True
        g.log(f"  {p.name}[劉禪] {t.name} 棄掉所有牌,下個回合被跳過")

    def ai_choose(self, g, p, options):
        best = None
        for i, (c, t) in enumerate(options):
            if getattr(c, "name", "") == "劉禪-棄光並跳過回合" and p.agent.attitude(g, p, t) <= -1 and len(t.all_cards()) >= 5:
                if best is None or len(t.all_cards()) > len(options[best][1].all_cards()):
                    best = i
        return best

    def on_turn_end(self, g, p, cur):  # 回合結束時,不是回合者的人手牌每超過 3 張扣 1 點體力並棄到 3 張
        if g.round <= 1 or not g.trigger_ok(p, "劉禪-手牌上限"):   # 第一輪不算
            return
        for q in list(g.alive_players()):
            if q is cur or not q.alive or len(q.hand) <= 3:
                continue
            extra = len(q.hand) - 3
            g.log(f"  [劉禪] {q.name} 手牌超過 3 張 ({extra} 張),扣 {extra} 血並棄到 3 張")
            for c in q.agent.choose_discard(g, q, extra, list(q.hand)):
                g.discard_card(q, c)
            g.damage(p, q, extra, _bonus=False)


class 劉諶(Char):
    name, faction = "劉諶", "蜀"

    def draw_count(self, g, p):
        if p.agent.choose_skill(g, p, "劉諶-少抽一張"):
            p.turn_flags["lc"] = True
            g.log(f"  {p.name}[劉諶] 少抽 1 張,本回合手牌都可以當決鬥")
            return 1
        return 2

    def views(self, g, p, c): return ["決"] if p.turn_flags.get("lc") and c.name != "決" else []

    def on_deal_damage(self, g, p, tgt, n):
        card = g.cur_card
        if card is None or card.name != "決" or g.cur_user is not p:
            return
        if n >= 2:
            p.turn_flags["lc"] = False
            g.log(f"  {p.name}[劉諶] 決鬥造成 2 點傷害,本回合的技能失效")
        if g.trigger_ok(p, "劉諶-抽牌"):
            g.new_dmg_chain()  # 結算完才發動: 另開一條新連鎖
            g.link(f"{p.name}[劉諶] 決鬥造成傷害,和 {tgt.name} 各抽 1 張")
            g.draw(p, 1)
            g.draw(tgt, 1)


class 吳懿(Char):
    name, faction = "吳懿", "蜀"

    def skill_options(self, g, p):
        if p.turn_flags.get("wu1"):
            return []
        return [(SkillAct("吳懿-交換手牌", self._run), t) for t in g.others(p)]

    def _run(self, g, p, t):
        p.turn_flags["wu1"] = True
        p.hand, t.hand = t.hand, p.hand
        p.turn_flags["wu_ids"] = {id(getattr(c, "orig", c)) for c in p.hand}   # 換到手上的牌: 這回合用掉幾張,下回合就扣幾點體力
        p.turn_flags["wu_used"] = 0
        g.log(f"  {p.name}[吳懿] 和 {t.name} 交換所有手牌")

    def on_card_used(self, g, p, user, card):
        ids = p.turn_flags.get("wu_ids")
        if user is not p or not ids:
            return
        real = id(getattr(card, "orig", card))
        if real in ids:
            ids.discard(real)
            p.turn_flags["wu_used"] = p.turn_flags.get("wu_used", 0) + 1

    def end_turn(self, g, p):
        x = p.turn_flags.get("wu_used", 0)
        if x:
            p.wu_debt = getattr(p, "wu_debt", 0) + x
            g.log(f"  {p.name}[吳懿] 用掉了 {x} 張交換來的牌,下個回合抽牌階段後扣 {x} 點體力")

    def after_draw(self, g, p, drawn):
        x = getattr(p, "wu_debt", 0)
        if x:
            p.wu_debt = 0
            g.log(f"  {p.name}[吳懿] 交換手牌的代價: 扣 {x} 點體力")
            g.damage(None, p, x)

    def ai_choose(self, g, p, options):
        best = None
        for i, (c, t) in enumerate(options):
            if getattr(c, "name", "") == "吳懿-交換手牌" and len(t.hand) - len(p.hand) >= 3:
                if best is None or len(t.hand) > len(options[best][1].hand):
                    best = i
        return best

    def on_damaged(self, g, p, src, n):
        g.new_dmg_chain()   # 受傷之後才發動: 另開一條新連鎖
        if not g.trigger_ok(p, "吳懿-抽牌"):   # 「可以」抽: 由玩家決定要不要發動
            return
        g.link(f"{p.name}[吳懿] 扣 {n} 血,抽 {n} 張")
        g.draw(p, n)


class 周倉(Char):
    name, faction = "周倉", "蜀"

    def after_draw(self, g, p, drawn):  # 再進行一次抽牌階段,但這回合不能出基本牌
        if p.turn_flags.get("zc") or not p.agent.choose_skill(g, p, "周倉-再抽牌"):
            return
        p.turn_flags["zc"] = True
        extra = g.draw_phase(p, 2)
        g.log(f"  {p.name}[周倉] 再進行一次抽牌階段 ({len(extra)} 張),本回合不能出基本牌")

    def blocks_card(self, g, p, card): return bool(p.turn_flags.get("zc")) and getattr(card, "kind", "") == "basic"

    def pre_damage(self, g, p, src, n, nature):  # 可以出等量的閃抵擋傷害
        k = 0
        while k < n and g.need_response(p, "閃", {"attacker": src if src is not None else p}):
            k += 1
        if k:
            g.log(f"  {p.name}[周倉] 打出 {k} 張閃,抵擋 {k} 點傷害")
        return n - k


class 張松(Char):
    name, faction = "張松", "蜀"
    mark = None

    def skill_options(self, g, p):
        if p.turn_flags.get("zs") or self.mark:
            return []
        return [(SkillAct("張松-指定", self._run), t) for t in g.others(p)]

    def _run(self, g, p, t):
        p.turn_flags["zs"] = True
        self.mark = t.idx
        g.log(f"  {p.name}[張松] 指定 {t.name}: 一輪內他若死亡,我和擊殺者各抽 4 張,否則他 -1 點體力")

    def ai_choose(self, g, p, options):
        best = None
        att = p.agent.attitude
        for i, (c, t) in enumerate(options):
            if getattr(c, "name", "") == "張松-指定" and att(g, p, t) <= -1 and t.hp <= 2:
                if best is None or t.hp < options[best][1].hp:
                    best = i
        return best

    def on_any_death(self, g, p, victim, killer):
        if self.mark != victim.idx:
            return
        self.mark = None
        if killer and killer.alive and killer is not victim:
            g.link(f"{p.name}[張松] 指定的 {victim.name} 死亡,{p.name} 和 {killer.name} 各抽 4 張")
            g.draw(p, 4)
            if killer is not p:
                g.draw(killer, 4)
        else:
            g.link(f"{p.name}[張松] 指定的 {victim.name} 死亡 (沒有擊殺者),{p.name} 抽 4 張")
            g.draw(p, 4)

    def on_turn_start(self, g, p):
        if self.mark is None:
            return
        t = g.players[self.mark]
        self.mark = None
        g.log(f"  {p.name}[張松] 指定的 {t.name} 一輪內沒有死亡,{t.name} -1 點體力")
        if t.alive:
            g.damage(None, t, 1)


class 李嚴(Char):
    name, faction = "李嚴", "蜀"
    immune_names = ("兵",)
    wu_picks = 2

    def after_draw(self, g, p, drawn):
        if any(c.name in DELAYED_NAMES for c in drawn) and g.trigger_ok(p, "李嚴-抽牌") and _may(g, p, "李嚴-抽牌"):
            g.link(f"{p.name}[李嚴] 抽到延時錦囊,再抽 2 張")
            g.draw(p, 2)

    def on_other_trick(self, g, p, user, real):
        if real.name in DELAYED_NAMES and g.trigger_ok(p, "李嚴-延時") and _may(g, p, "李嚴-延時"):
            g.new_dmg_chain()  # 結算完才發動: 另開一條新連鎖
            g.link(f"{p.name}[李嚴] {user.name} 使用延時錦囊,抽 2 張")
            g.draw(p, 2)


class 關興(Char):
    name, faction = "關興", "蜀"
    single_to_all = True
    immune_turn = -1

    def blocks_target(self, g, p, card):   # 別人的單一對象錦囊 (順 / 過 / 決 / 火攻 / 降雷 / 樂 / 兵…) 不能指定關興;強 / 弱 / 突 是 ⚡ 或全體牌,不算
        return getattr(card, "kind", "") == "trick" and card.name not in ("強", "弱", "突", "南", "萬", "飢", "桃園", "五")   # 全體牌 (南蠻 / 萬箭 / 飢餓 / 桃園 / 五穀) 不是單一對象,對關興照常生效

    def offturn_options(self, g, p):
        if self.immune_turn == g.turn_id:
            return []
        names = sorted({c.name for c in p.hand if sum(1 for x in p.hand if x.name == c.name) >= 2})
        return [(SkillAct(f"關興-棄兩張{n}", lambda g, p, t, n=n: self._run(g, p, n)), None) for n in names]

    def _run(self, g, p, n):   # 只能在別人的回合發動 (回合開始 / 出牌階段結束時會跳出詢問框),自己的出牌階段不能用
        for c in [x for x in p.hand if x.name == n][:2]:
            g.discard_card(p, c)
        self.immune_turn = g.turn_id
        g.log(f"  {p.name}[關興] 棄兩張 {n},本回合不會扣血")

    def ai_choose(self, g, p, options):
        if p.hp <= 2 and g.cur is not p:
            return next((i for i, (c, t) in enumerate(options) if getattr(c, "name", "").startswith("關興-")), None)

    def cap_damage(self, g, p, n): return 0 if self.immune_turn == g.turn_id else n


class 張苞(Char):
    name, faction = "張苞", "蜀"
    judge_pick = True
    untarget_turn = -1

    def offturn_options(self, g, p):
        if self.untarget_turn == g.turn_id:
            return []
        names = sorted({c.name for c in p.hand if sum(1 for x in p.hand if x.name == c.name) >= 2})
        return [(SkillAct(f"張苞-棄兩張{n}", lambda g, p, t, n=n: self._run(g, p, n)), None) for n in names]

    def _run(self, g, p, n):
        for c in [x for x in p.hand if x.name == n][:2]:
            g.discard_card(p, c)
        self.untarget_turn = g.turn_id
        g.log(f"  {p.name}[張苞] 棄兩張 {n},本回合不會成為牌的對象")

    def ai_choose(self, g, p, options):
        if p.hp <= 2 and g.cur is not p:
            return next((i for i, (c, t) in enumerate(options) if getattr(c, "name", "").startswith("張苞-")), None)

    def blocks_target(self, g, p, card): return self.untarget_turn == g.turn_id


class 張紘(Char):
    name, faction = "張紘", "吳"
    no_extra_draw = True

    def blocks_target(self, g, p, card): return card.name in ("強", "弱", "突")

    def on_damaged(self, g, p, src, n):  # 我扣血時,其他人都扣血
        g.new_dmg_chain()   # 受傷之後才發動: 另開一條新連鎖
        if not g.trigger_ok(p, "張紘-連坐"):
            return
        g.link(f"{p.name}[張紘] 扣血,其他人也各扣 {n} 血 (可閃)")
        for q in list(g.others(p)):
            if q.alive and not g.need_response(q, "閃", {"attacker": p}):   # 每個人可以打出一張閃躲掉
                g.damage(p, q, n, _bonus=False)


class 虞翻(Char):
    name, faction = "虞翻", "吳"
    base = None

    def on_turn_start(self, g, p):
        if self.base is not None and g.sha_total - self.base < 7:  # 輪完一輪殺還不到 7 張
            g.link(f"{p.name}[虞翻] 一輪內全場只出了 {g.sha_total - self.base} 張殺 (未滿 7),全部人 -2 點體力 (可閃)")
            for q in g.order_from(p):
                if q.alive and not g.need_response(q, "閃", {"attacker": p}):
                    g.damage(p, q, 2, _bonus=False)
        self.base = g.sha_total


class 魯肅(Char):
    name, faction = "魯肅", "吳"
    basic_as_trick = True

    def draw_count(self, g, p):  # 可以選擇要不要發動: 多抽 2 張,再把手牌 2 張交給另一名玩家
        if g.others(p) and p.agent.choose_skill(g, p, "魯肅-贈牌"):
            p.turn_flags["ls"] = True
            return 4
        return 2

    def blocks_target(self, g, p, card): return card.name == "火攻"

    def after_draw(self, g, p, drawn):  # 多抽的 2 張: 把手牌 2 張交給另一名玩家
        if not p.turn_flags.pop("ls", False):
            return
        others = g.others(p)
        if not others or len(p.hand) < 2:
            return
        t = _ally_pick(g, p, others)
        cards = p.agent.choose_discard(g, p, 2, list(p.hand), msg=f"選擇要給 {t.name} 的 2 張手牌")
        for c in cards:
            p.hand.remove(c)
            t.hand.append(c)
        g.log(f"  {p.name}[魯肅] 把 2 張手牌交給 {t.name}")


class 李儒(Char):
    keep_disguised = True   # 偽裝時仍保有本尊技能
    name, faction = "李儒", "群"

    def views(self, g, p, c):  # 屬性殺當火攻;偽裝時,殺=閃=桃
        v = ["火攻"] if c.name == "殺" and getattr(c, "nature", None) else []
        return v + ([n for n in ("殺", "閃", "桃") if n != c.name] if p.turn_flags.get("disguised") and c.name in ("殺", "閃", "桃") else [])

    def as_card(self, g, p, c, name): return bool(p.turn_flags.get("disguised")) and name in ("殺", "閃", "桃") and c.name in ("殺", "閃", "桃")

    def skill_options(self, g, p):
        if p.turn_flags.get("lr"):
            return []
        return [(SkillAct("李儒-逼出閃", self._run), t) for t in g.others(p)]

    def _run(self, g, p, t):
        p.turn_flags["lr"] = True
        g.log(f"  {p.name}[李儒] 令 {t.name} 出一張閃,否則受到 1 點火焰傷害")
        if not g.need_response(t, "閃", {"attacker": p}):
            g.damage(p, t, 1, nature="火")

    def ai_choose(self, g, p, options):
        best = None
        for i, (c, t) in enumerate(options):
            if getattr(c, "name", "") == "李儒-逼出閃" and p.agent.attitude(g, p, t) <= -1:
                if best is None or t.hp < options[best][1].hp:
                    best = i
        return best


class 袁術(Char):
    name, faction = "袁術", "群"

    def on_cards_discarded(self, g, p, c):  # 我的牌被捨棄: 其他人也要棄 1 張牌,否則 -1 點體力 (可閃)
        if getattr(g, "in_discard_phase", False) or not g.trigger_ok(p, "袁術-連坐"):   # 棄牌階段的棄牌不觸發
            return
        g.link(f"{p.name}[袁術] 牌被捨棄,其他人要棄 1 張牌,否則 -{g.dmg_preview(p, 1)} 點體力 (可閃)")
        for q in list(g.others(p)):
            if not q.alive:
                continue
            pool = q.all_cards()
            cd = q.agent.respond(g, q, "袁術棄牌", pool, {"source": p}) if pool else None
            if cd:
                g.discard_card(q, cd)
                g.log(f"  {q.name} 棄置 {cd}")
            elif not g.need_response(q, "閃", {"attacker": p}):
                g.damage(p, q, 1, _bonus=False)

    def on_judged(self, g, p, c): self.on_cards_discarded(g, p, c)   # 判定也算「牌被捨棄」

    def on_sha_used(self, g, p, card):  # 每出一張殺扣 1 點血
        g.log(f"  {p.name}[袁術] 出殺,扣 1 點體力")
        g.damage(None, p, 1)


class 賈詡(Char):
    name, faction = "賈詡", "群"

    # 技能一: 賈詡在場時,其他人除了瀕死 (救人 / 被救) 都不能用桃,只有賈詡自己可以 (engine.peach_locked)
    peach_lock = True

    def skill_options(self, g, p):  # 出一張殺,使 2 個人決鬥
        shas = [c for c in p.hand if c.name == "殺"]
        others = g.others(p)
        if not shas or len(others) < 2:
            return []
        return [(SkillAct("賈詡-殺令決鬥", self._run), (a, b)) for i, a in enumerate(others) for b in others[i + 1:]]

    def _run(self, g, p, t):
        a, b = t
        sha = p.agent.choose_discard(g, p, 1, [c for c in p.hand if c.name == "殺"])[0]
        g.discard_card(p, sha)
        g.log(f"  {p.name}[賈詡] 出殺,令 {a.name} 和 {b.name} 決鬥")
        x, y = a, b
        while x.alive and y.alive:
            if not g.need_response(x, "殺", {"duel_with": y}):
                g.damage(y, x, 1)
                break
            x, y = y, x

    def ai_choose(self, g, p, options):
        att = p.agent.attitude
        for i, (c, t) in enumerate(options):
            if getattr(c, "name", "") == "賈詡-殺令決鬥" and att(g, p, t[0]) <= -0.5 and att(g, p, t[1]) <= -0.5:
                return i


class 郭圖逢紀(Char):
    name, faction = "郭圖&逢紀", "群"
    next_char = None

    def on_other_wei(self, g, p, user, name):  # 別人偽裝時,我下個回合變成那個武將 (一次一隻)
        self.next_char = name
        g.log(f"  {p.name}[郭圖&逢紀] 記下 {getattr(g, '_wei_who', user.name)} 偽裝成 {name},下個回合會變成他")

    def on_turn_start(self, g, p):
        if self.next_char and not _may(g, p, "郭圖&逢紀-變身"):
            self.next_char = None
        if self.next_char:
            from characters import ROSTER
            p.disguise = [g.wei_chars.setdefault(self.next_char, ROSTER[self.next_char]())]
            g.log(f"  {p.name}[郭圖&逢紀] 這回合變成 {self.next_char}")
            self.next_char = None

    def sha_limit(self, g, p): return max(0, p.hp)  # 出殺次數 = 體力


class 司馬炎(Char):
    name, faction = "司馬炎", "晉"

    def replace_draw(self, g, p):  # 翻開牌堆頂 x (=體力) 張,拿 2 張,其餘棄掉: 紅 +1 點體力,黑 +1 點體力量上限
        if not _may(g, p, "司馬炎-抽牌"):
            return False
        top = [c for c in (g.pop_deck() for _ in range(max(p.hp, 1))) if c]
        if not top:
            return True
        n_top = len(top)
        for k in range(min(2, len(top))):
            g.pile_ctx = f"司馬炎: 從翻開的 {n_top} 張牌中選 2 張加入手牌 (第 {k + 1} 張)"
            try:
                c = p.agent.pick_pile(g, p, top)
            finally:
                g.pile_ctx = None
            top.remove(c)
            p.hand.append(c)
        g.log(f"  {p.name}[司馬炎] 翻開 {len(top) + 2} 張,拿 2 張,棄掉 {len(top)} 張")
        for c in top:
            g.discard.append(c)
            if c.color == "紅":
                g.heal(p)
            elif p.maxhp < 8:   # 體力上限最多 8
                p.maxhp += 1
        return True


class 羊祜(Char):
    name, faction = "羊祜", "晉"
    block_names = ("出",)
    tie_extra = 1

    def views(self, g, p, c): return ["拋"] if c.name == "殺" else []

def _borrow_pick(g, p, cands, skill):
    """馬謖/陳群/韓當: 從 cands 中選一位借技能。真人自己選,AI 隨機。"""
    if not cands:
        return None
    if hasattr(p.agent, "pick_borrow"):   # 第 5 級電腦: 照優先名單挑
        return p.agent.pick_borrow(g, p, cands, skill)
    if hasattr(p.agent, "attitude"):
        return g.rng.choice(cands)
    if hasattr(p.agent, "choose_borrow"):   # 真人: 像選角色那樣看頭像與技能
        return p.agent.choose_borrow(g, p, skill, cands)
    return p.agent.choose_target(g, p, skill, cands)


class 馬謖(Char):
    name, faction = "馬謖", "蜀"

    def skill_options(self, g, p):  # 一回合一次,用 2 張手牌換別人 2 張 (對方隨機)
        if p.turn_flags.get("ms") or len(p.hand) < 2:
            return []
        return [(SkillAct("馬謖-換2張牌", self._run), t) for t in g.others(p) if len(t.hand) >= 2]

    def _run(self, g, p, t):
        p.turn_flags["ms"] = True
        if len(t.hand) < 2 or len(p.hand) < 2:   # 技能發動前被連鎖的 ⚡ 打光了手牌
            g.log(f"  {p.name}[馬謖] 換牌失敗 (手牌不足)")
            return
        mine = p.agent.choose_discard(g, p, 2, list(p.hand), msg=f"選擇要和 {t.name} 交換的 2 張手牌")
        theirs = g.rng.sample(t.hand, 2)
        for c in mine:
            p.hand.remove(c)
        for c in theirs:
            t.hand.remove(c)
        p.hand.extend(theirs)
        t.hand.extend(mine)
        g.log(f"  {p.name}[馬謖] 用 2 張手牌和 {t.name} 的 2 張手牌交換")

    def ai_choose(self, g, p, options):
        best = None
        for i, (c, t) in enumerate(options):
            if getattr(c, "name", "") == "馬謖-換2張牌" and p.agent.attitude(g, p, t) <= -1 and len(t.hand) >= 3:
                if best is None or len(t.hand) > len(options[best][1].hand):
                    best = i
        return best

    def _pick(self, g, p):
        cands = [q for q in g.others(p) if q._char.name != "馬謖"]
        if not cands:
            return
        t = _borrow_pick(g, p, cands, "馬謖-借技能")
        p.borrow = [t]
        g.log(f"  {p.name}[馬謖] 擁有 {t.name} 的技能 (直到他死亡)")

    def on_game_start(self, g, p): self._pick(g, p)   # 開局就選好要複製誰的技能

    # 複製的對象死了就失去那個技能,不會重新選 (Player.char 只算還活著的 borrow)


class 陳群(Char):
    name, faction = "陳群", "魏"
    tier = 4

    def skill_options(self, g, p):  # 基本牌可以重鑄 (棄掉抽 1 張)
        seen, out = set(), []
        for c in p.hand:
            if c.kind == "basic" and c.name not in seen:
                seen.add(c.name)
                out.append((SkillAct(f"陳群-重鑄{c.name}", lambda g, p, t, n=c.name: self._recast(g, p, n)), None))
        if p.hp == 4 and p.hand and "突" not in g.banned() and g.others(p):   # 4 點體力: 明確的「手牌當突襲」按鈕
            out.append((SkillAct("陳群-手牌當突襲", lambda g, p, t: self._raid(g, p)), None))
        return out

    def _raid(self, g, p):
        c = p.agent.choose_discard(g, p, 1, list(p.hand))[0]
        from cards import ViewCard
        view = ViewCard("突", c.color, "trick", c)
        g.log(f"  {p.name}[陳群] 把 {c} 當作突襲使用")
        g.execute(p, view, None)
        g.after_play(p, view)

    def _recast(self, g, p, n):
        c = next(x for x in p.hand if x.name == n and x.kind == "basic")
        g.discard_card(p, c)
        g.draw(p, 1)
        g.log(f"  {p.name}[陳群] 重鑄 {c},抽 1 張")

    def ai_choose(self, g, p, options):
        for i, (c, t) in enumerate(options):
            n = getattr(c, "name", "")[len("陳群-重鑄"):]
            cnt = sum(1 for x in p.hand if x.name == n)
            if n == "酒" or (n == "閃" and cnt >= 3) or (n == "殺" and cnt >= 4):
                return i

    def _borrow(self, g, p):   # 2 點體力: 複製另一位玩家的技能 (直接選,不再問要不要)
        if any(q.alive and q is not p for q in p.borrow2):
            return
        cands = [q for q in g.others(p) if q._char.name != "陳群"]
        if not cands:
            return
        t = _borrow_pick(g, p, cands, "陳群-借技能")
        p.borrow2 = [t]
        g.log(f"  {p.name}[陳群] 2 點體力: 擁有 {t.name} 的技能 (直到他死亡)")
        if t._char.name == "蔣幹":   # 蔣幹「你有1血」: 體力變 1,離開 2 血所以這次複製隨即失效
            p.hp = 1
            p.borrow2 = []
            g.log(f"  {p.name}[陳群] 複製蔣幹: 體力變成 1,離開 2 點體力,複製失效")

    def on_turn_start(self, g, p):  # 依回合開始時的體力取得不同能力
        if p.hp == 2:  # 2 點體力: 擁有另一位玩家的技能
            self._borrow(g, p)
        else:
            p.borrow2 = []

    def on_healed(self, g, p):   # 體力變成 2 時馬上選要複製誰;離開 2 血就失去
        if p.hp == 2 and p.alive:
            self._borrow(g, p)
        else:
            p.borrow2 = []

    ask = False

    def on_damaged(self, g, p, src, n):   # 掉到 2 血: 先記著,等這次傷害結算完才問要複製誰;離開 2 血就失去
        if p.hp == 2 and p.alive:
            self.ask = True
        elif p.alive:
            self.ask = False
            p.borrow2 = []

    def after_damage(self, g, p):
        if self.ask and p.alive and p.hp == 2:
            self.ask = False
            self._borrow(g, p)
        elif self.ask and p.hp != 2:
            self.ask = False

    def views(self, g, p, c): return ["突"] if p.hp == 4 and c.name != "突" else []  # 4 點體力: 手牌當突襲
    def no_range(self, g, p): return p.hp == 3                                      # 3 點體力: 沒有距離限制
    def as_card(self, g, p, c, name): return name == "占" and p.hp == 1              # 1 點體力: 手牌當占卜


class 韓當(Char):
    name, faction = "韓當", "吳"

    def _pick(self, g, p):
        cands = [q for q in g.others(p) if q._char.faction == "吳"]
        if not cands:
            p.borrow2 = []
            return
        t = _borrow_pick(g, p, cands, "韓當-借技能")
        p.borrow2 = [t]
        g.log(f"  {p.name}[韓當] 獲得吳勢力 {t.name} 的技能 (他死後失效)")

    def on_game_start(self, g, p): self._pick(g, p)   # 開局就選好要複製誰的技能

    def on_turn_start(self, g, p):   # 對象死了 (或還沒有對象): 回合開始重新選一位吳勢力
        if not any(q.alive and q is not p for q in p.borrow2):
            self._pick(g, p)
        self._tax(g, p, p)

    def on_other_turn_start(self, g, p, cur): self._tax(g, p, cur)

    def _tax(self, g, p, q):  # 不是吳勢力的玩家每回合要棄 1 張手牌或扣 1 點體力 (可閃)
        if q._char.faction == "吳" or not q.alive or not g.trigger_ok(p, f"韓當-{q.idx}"):
            return
        g.link(f"{p.name}[韓當] {q.name} 不是吳勢力,要棄 1 張手牌,否則扣 {g.dmg_preview(p, 1, tgt=q)} 點體力 (可閃)")
        cd = q.agent.respond(g, q, "韓當棄牌", list(q.hand), {"source": p}) if q.hand else None
        if cd:
            g.discard_card(q, cd)
            g.log(f"  {q.name} 棄置 {cd}")
        elif not g.need_response(q, "閃", {"attacker": p}):
            g.damage(p, q, 1, _bonus=False)


class 公孫淵(Char):
    name, faction = "公孫淵", "群"
    pending = None

    def skill_options(self, g, p):
        if p.turn_flags.get("gsy") or not p.hand:
            return []
        return [(SkillAct("公孫淵-亮牌抽2", self._run), None)]

    def _run(self, g, p, t):
        p.turn_flags["gsy"] = True
        g.log(f"  {p.name}[公孫淵] 展示所有手牌: " + " ".join(repr(c) for c in p.hand) + ",抽 2 張")
        g.last_reveal = ("公孫淵 展示手牌", [(p.idx, c) for c in p.hand])   # 桌面中央顯示這些牌 (所有人看得到)
        g.draw(p, 2)

    def ai_choose(self, g, p, options): return 0 if options and len(p.hand) <= 3 else None

    def on_targeted(self, g, p, user, card):  # 被使用基本牌: 下個回合獲得他的技能,直到回合結束
        if card.kind == "basic" and user is not p:
            self.pending = user

    def on_turn_start(self, g, p):
        p.alias = []
        if self.pending is not None and self.pending.alive:
            p.alias = [self.pending._char]
            g.log(f"  {p.name}[公孫淵] 獲得 {self.pending.name} 的技能,直到回合結束")
        self.pending = None

    def end_turn(self, g, p): p.alias = []


class 左慈(Char):
    name, faction = "左慈", "群"
    used = None

    def on_turn_start(self, g, p):
        from_ = {q._char.name for q in g.players}
        if self.used is None:
            self.used = set()
        pool = [n for n in ROSTER if n not in from_ and n not in self.used]
        if pool:
            n = pool[p.agent.choose_option(g, p, "左慈-化身", list(pool))]   # 還沒出現過的武將: 自己選 (電腦隨機)
            self.used.add(n)
            p.alias = [ROSTER[n]()]
            g.log(f"  {p.name}[左慈] 化身為 {n}")
        elif p.agent.choose_skill(g, p, "左慈-全部翻面"):
            g.link(f"{p.name}[左慈] 沒有角色可化身,把所有武將牌翻面")
            for q in list(g.alive_players()):
                g.flip_char(q)

    def on_flipped(self, g, p): p.alias = []

ROSTER = {c.name: c for c in (張飛, 馬超, 黃忠, 荀彧, 孫策, 華雄, 董卓,
                              曹彰, 關羽, 孫權, 孫堅, 丁奉, 呂蒙, 魏延, 曹丕,
                              許褚, 趙雲, 曹仁, 孟獲, 陸遜, 黃蓋, 龐德, 袁紹,
                              張遼, 馬良,
                              司馬昭, 夏侯惇, 徐晃, 曹洪, 鄧艾, 劉備, 姜維, 諸葛亮, 張角, 華佗, 劉協, 顏良文醜,
                              滿寵, 公孫瓚, 呂布, 典韋, 司馬懿, 崔琰, 曹植, 鐘繇, 張嶷, 王允, 曹操, 曹叡,
                              張昭, 邯鄲淳, 周胤, 沮授, 太史慈, 周魴, 龐統,
                              周瑜, 甘寧, 夏侯淵,
                              孔融, 伊籍,
                              張郃, 曹休, 曹沖, 曹真, 楊修, 蔣幹, 郭嘉, 劉禪, 劉諶, 吳懿, 周倉, 張松, 李嚴, 關興, 張苞,
                              張紘, 虞翻, 魯肅, 李儒, 袁術, 賈詡, 郭圖逢紀, 司馬炎, 羊祜,
                              馬謖, 陳群, 韓當, 公孫淵, 左慈)}
