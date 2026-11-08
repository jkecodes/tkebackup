"""三國殺重製版規則引擎。規則依據見 rulebook.md。

尚未實作: 降雷/偽、武將技能 (characters.md)、剩餘武器效果 (孔雀/青龍/寒冰/方天/丈八)、
⚡ 型錦囊 (轉/強/弱/出) 在他人回合的使用時機 (目前只能在自己出牌階段用)。
"""
import itertools
import re
import random
from cards import Card, ViewCard, PairView, build_deck, WEAPON_RANGE, DELAYED, SELF_DELAYED
from characters import Char, SkillAct, Combo

# 身分配置 (作者提供): 人數 -> [配置...];6、8 人有兩種 (第二種內奸 2 人)
def _r(z, f, n):  # 忠臣數, 反賊數, 內奸數
    return ["主公"] + ["忠臣"] * z + ["反賊"] * f + ["內奸"] * n


ROLES = {
    2: [["無", "無"]],   # 2~3 人: 沒有身分,各打各的,最後活著的人獲勝
    3: [["無", "無", "無"]],
    4: [_r(1, 1, 1)],
    5: [_r(1, 2, 1)],
    6: [_r(1, 3, 1), _r(1, 2, 2)],
    7: [_r(2, 3, 1)],
    8: [_r(2, 4, 1), _r(2, 3, 2)],
    9: [_r(3, 4, 1)],
    10: [_r(3, 4, 2)],
}
def _fn(n):   # 紀錄裡的牌名一律用圖鑑全名
    from view import full_name
    return full_name(n)


_CV = {"桃": 10, "無": 9, "無懈": 8, "閃": 7, "殺": 6, "酒": 4}  # 丈八蛇矛挑最不重要的牌用
NATURE_ARMOR = {"火": "火盾", "雷": "雷盾", "冰": "冰盾"}
HARM_CARDS = {"降雷", "殺", "決", "火攻", "順", "過", "樂", "兵", "毒", "草", "拋", "笑", "鴻", "轉", "弱", "漁"}
HELP_CARDS = {"投", "強"}
BASIC_NAMES = {"殺", "閃", "桃", "酒"}
NO_SKILL = Char()  # 翻面時使用: 沒有任何技能
EMPTY_EQUIP = {"weapon": None, "armor": None, "h+": None, "h-": None, "weapon2": None, "armor2": None}


class GameOver(Exception):
    pass


class Player:
    @property
    def flip_char(self):
        """翻面作用在哪個武將: 偽裝中就是偽裝的那位,本尊不受影響。"""
        return self.disguise[0] if self.__dict__.get("disguise") else self._char

    @property
    def flipped(self):
        return self.__dict__.get("_flipped", False)

    @flipped.setter
    def flipped(self, v):
        old = self.flipped
        self.__dict__["_flipped"] = v
        if bool(old) != bool(v) and "_char" in self.__dict__:
            self._char.on_flip_change(self, bool(v))   # 蔣幹: 翻面時體力上限變 4

    @property
    def maxhp(self):
        d = self._char.dyn_maxhp(self) if getattr(self, "_char", None) is not None else None   # 孟獲: 手牌數 + 1,隨時變動
        if d is not None:
            if self.g is not None and self.g.lord is self:
                d += self.g.lord_bonus
            if self.hp > d and self.alive:
                self.hp = max(1, d)
            return d
        eff = self._maxhp
        dis = self.__dict__.get("disguise")
        if dis and not self.flipped and dis[0].dyn_maxhp(self) is None:   # 偽裝: 體力上限變成偽裝武將的 (蔣幹偽裝成 4 血武將就是 4 血上限),偽裝結束變回來
            eff += dis[0].maxhp - self._char.maxhp
            self.__dict__["_dgm"] = True
        elif self.__dict__.get("_dgm"):
            self.__dict__["_dgm"] = False
            if self.alive and self.hp > eff:
                self.hp = max(1, eff)
        return eff

    @maxhp.setter
    def maxhp(self, v):
        self._maxhp = v

    def __init__(self, idx, role, agent, char=None):
        self.idx, self.role, self.agent = idx, role, agent
        self._char = char or Char()
        self.maxhp = self.hp = self._char.maxhp
        self.turn_flags: dict = {}    # 本回合的武將技能旗標
        self.dmg_turn = 0             # 本回合已受傷害 (張飛上限用)
        self.played = 0               # 本回合出牌數 (黃忠用)
        self.skip_play_flag = False   # 下個出牌階段跳過 (董卓/樂)
        self.hand: list[Card] = []
        self.equip: dict[str, Card | None] = dict(EMPTY_EQUIP)
        self.alive = True
        self.judge: list[Card] = []   # 判定區 (延時錦囊)
        self.stash: list[Card] = []   # 未: 蓋在武將牌下,下個自己回合入手
        self.flipped = False          # 武將牌翻面 (技能無法使用)
        self.chained = False          # 鐵索橫置
        self.dmg_x2 = 0               # 強: 本回合「造成」的傷害 x2 的層數
        self.dmg_half = 0             # 弱: 本回合「造成」的傷害 ÷2 的層數
        self.cao = 0                  # 草木皆兵: 本回合摸牌階段少摸的張數
        self.fa_debt = []             # 發: 每使用一張發憤圖強,記下回合結束要棄的張數 (一張問一次)
        self.g = None                 # 所屬 Game (Game.__init__ 設定)
        self.skip_turn = False        # 下個自己的回合整個跳過 (劉禪)
        self.borrow: list = []        # 馬謖複製技能的對象: 對方死亡即失效
        self.borrow2: list = []       # 陳群 (2 血) / 韓當 複製技能的對象 (和馬謖分開存,否則被馬謖複製時會互相洗掉)
        self.alias: list = []         # 化身 / 暫時獲得的武將 (左慈/公孫淵)
        self.disguise: list = []      # 偽裝成的武將 (一回合)
        self.dg_flip = False          # 偽裝的那張武將牌是否翻面 (本尊是否翻面看 flipped)
        self.healed = 0   # 成就統計: 整場回復的體力總量
        self.dmg_total = self.sha_n = self.max_hand = 0   # 成就統計: 整場造成的傷害 / 打出或使用的殺數 / 手牌最多張數
        self.chain11 = False           # 成就: 接出第 11 個以上的連鎖
        self.wei_n = 0                 # 成就: 整場使用「偽」的次數
        self.thunder = None           # 降雷: (使用的 turn_id, 原本是否翻面)
        self.empty_seen = False       # 手牌已空 (曹休「失去最後一張手牌」用)

    @property
    def char(self):
        if self.g is not None and self.g.void:
            return NO_SKILL
        if self.disguise:   # 偽裝中: 看偽裝的那張有沒有翻面 (本尊被降雷翻面後再偽裝,新的偽裝是正面、技能可用)
            if self.dg_flip:
                return NO_SKILL
        elif self.flipped:
            return NO_SKILL
        extras = [q._char for q in self.borrow + self.borrow2 if q.alive and q is not self] + list(self.alias)
        if self.disguise:   # 偽裝: 技能完全取代 (李儒保留自己的「偽裝時殺=閃=桃」)
            if getattr(self._char, "keep_disguised", False) and not self.flipped:
                extras.append(self._char)
            return Combo(self.disguise[0], extras)
        return Combo(self._char, extras) if extras else self._char

    @property
    def name(self):
        c = self.char.name if self.char.name != "無名" else ""
        return f"P{self.idx}({self.role}{'/' + c if c else ''})"

    def equip_cards(self):
        return [c for c in self.equip.values() if c]

    def all_cards(self):
        return self.hand + self.equip_cards()

    def _worn(self, slots):
        if self.g is not None and self.g.equip_off():
            return []
        return [self.equip[s].name for s in slots if self.equip[s]]

    def weapon_names(self):
        return self._worn(("weapon", "weapon2"))

    def armor_names(self):
        return self._worn(("armor", "armor2"))

    def has_weapon(self, name):
        return name in self.weapon_names()

    def has_armor(self, name):
        return name in self.armor_names()

    def weapon_name(self):
        w = self.weapon_names()
        return w[0] if w else None

    def armor_name(self):
        a = self.armor_names()
        return a[0] if a else None

    def attack_range(self):
        return max([WEAPON_RANGE.get(w, 1) for w in self.weapon_names()] + [1, self.char.range_floor(self.g, self)])

    def __repr__(self):
        return self.name


class Game:
    def __init__(self, agents, seed=0, verbose=False, max_rounds=100, chars=None, role_variant=0, lord_seat=0, lord_bonus=1, mode="normal", role_mode="normal", base_hp=4):
        self.rng = random.Random(seed)
        self.mode, self.lord_bonus = mode, lord_bonus   # mode: normal 正常 / shuffle 百變 (第 2 輪起每次輪到自己都換新武將)
        n = len(agents)
        # role_mode: normal 正常 / none 無身分 (各打各的,最後活著的人贏;2~3 人固定這樣) / open 全部身分公開 / hidden 主公不公開 (不加體力上限)
        role_mode = role_mode if role_mode in ("normal", "none", "open", "hidden") and n >= 4 else ("none" if n < 4 else "normal")
        self.role_mode = role_mode
        roles = ["無"] * n if role_mode == "none" else ROLES[n][role_variant % len(ROLES[n])][:]
        self.rng.shuffle(roles)
        self.noroles = role_mode == "none"   # 沒有主公加成、沒有身分勝負
        self.hidden_lord = role_mode == "hidden"
        if self.hidden_lord:
            lord_bonus = 0
        self.lord_bonus = lord_bonus
        ls = self.rng.randrange(n) if lord_seat in (None, "random") else int(lord_seat) % n   # 無身分時 ls 只是起始座位
        if self.noroles:
            lord_bonus = 0
        else:
            roles.remove("主公")
            roles.insert(ls, "主公")  # 主公座位: 預設 0 號,GUI 預設隨機
        chars = chars or [None] * n
        self.players = [Player(i, roles[i], agents[i], chars[i]) for i in range(n)]
        self.hp_offset = max(-3, min(996, int(base_hp) - 4)) if isinstance(base_hp, (int, float)) else 0   # 基礎體力上限 (預設 4): 所有武將的體力上限一起加減
        for q in self.players:
            q.g = self
            if self.hp_offset:
                q._maxhp = max(1, q._maxhp + self.hp_offset)
                q.hp = q._maxhp
        self.void = False               # 呂布: 本回合全場效果無效
        self.ordinary = False           # 正在進行一般抽牌 (張紘: 其他抽牌需打出閃)
        self.sha_total = 0              # 全場累計使用的殺 (虞翻)
        self.wei_chars: dict = {}       # 偽裝用的武將實例 (一次的技能一場只能用一次)
        self.cur_sha_target = None
        self.lord = self.players[ls]
        self.dir = 1                    # 輪次方向: +1 往左 (座位號遞增) / -1 往右;主公第一回合結束後由主公決定
        self.lord.maxhp += lord_bonus   # 主公多 lord_bonus 點體力上限
        self.lord.hp += lord_bonus
        self.deck = build_deck(self.rng)
        self.total_cards = len(self.deck)
        self.discard: list[Card] = []
        self.last_reveal = None  # (標題, [(玩家idx, 牌), ...]) 例如鴻門宴亮出的兩張牌
        self.last_judge = None   # (被判定者idx或None, 判定牌)
        self.verbose = verbose
        self.on_log = None  # GUI 用: 每行紀錄呼叫一次 (控制節奏/暫停)
        self.logs: list[str] = []
        self.max_rounds = max_rounds
        self.winner = None
        self.round = 0
        self.lord_attackers: set[int] = set()
        self.revealed: dict[int, str] = {} if (self.noroles or self.hidden_lord) else {ls: "主公"}
        if role_mode == "open":
            self.revealed = {q.idx: q.role for q in self.players}   # 全部身分公開
        self.cur: Player = self.lord
        self.sha_used = 0
        self.jiu = False
        self.stats = {"damage": 0, "kills": 0, "cards_played": {}}
        self.last_dealt = 0             # 最近一次實際造成的傷害量
        self.in_group = False           # 正在結算全體錦囊 (傷害不視為針對性攻擊)
        self.turn_id = 0                # 全域回合計數 (龐德「一回合一次」用)
        self.cur_card = None            # 目前結算中的牌與使用者 (孟獲用)
        self.cur_user = None
        self.chain_no = 0               # 目前連鎖已有幾個 chain
        self.chain_start = 0            # 目前連鎖開始時的棄牌堆長度 (顯示同一連鎖的棄牌用)
        self.prev_start = 0
        self.chain_cleared = False      # 連鎖處理完: 桌面中央的連鎖演示清空
        self.exec_depth = 0
        self.chain_all = set()          # 想在「每一個動作」都被問要不要接連鎖的真人座位 (其他人: 只有牌指定到自己才問)
        self._chain_asked = set()
        self.eyes = []                  # 坐收漁利: [{"owner", "tgt", "turn"}] 目標這個回合每使用一張錦囊,owner 抽 1 張
        self.dmg_hook_depth = 0
        self.chain_view = []            # 連鎖演示: 這條連鎖實際打出的牌 / 發動的技能 (不含被棄掉的牌)
        self.chain_used: set = set()    # 本連鎖已發動過的技能 (玩家 idx, 技能名)
        self.chain_pcount: dict = {}    # 被動技能在本連鎖的觸發次數
        self.scn = None                 # 教學關卡: 開局時呼叫 scn(game) 佈置牌桌 (沒有就照一般規則發牌)
        self.scn_nodraw = ()            # 教學關卡: 這些座位第 1 輪的抽牌階段不抽牌 (手牌完全照關卡設定)

    # ---------- 連鎖 ----------
    def new_chain(self):
        """開始一條新連鎖 (一張牌/一次判定的完整結算)。"""
        self.chain_no = 0
        self.chain_cleared = False
        self.chain_used = set()
        self.chain_pcount = {}
        if len(self.discard) > self.chain_start:   # 上一條連鎖有牌進棄牌堆: 記下範圍,新連鎖還沒出牌前繼續顯示它
            self.prev_start, self.chain_start = self.chain_start, len(self.discard)

    def new_dmg_chain(self):
        """受傷後才發動的技能: 另開一條新連鎖。但已經在另一個受傷技能的連鎖裡 (例如張紘互相連坐) 就接在後面,
        才不會每次重置「同一連鎖只能發動一次」而無限循環。"""
        if self.dmg_hook_depth <= 1:
            self.new_chain()
            self.clear_chain_view()

    def clear_chain_view(self):
        self.prev_start = self.chain_start = len(self.discard)
        self.chain_cleared = True
        self.chain_view = []

    def link(self, text):
        """連鎖上新增一個 chain。結算時後發動的先處理。"""
        self.chain_no += 1
        if self.chain_no > 10:   # 成就「接連鎖超過 10」: 記下接出第 11 個以上連鎖的人
            wm0 = re.match(r"\s*P(\d+)", text)
            if wm0 and int(wm0.group(1)) < len(self.players):
                self.players[int(wm0.group(1))].chain11 = True
        m = re.search(r"\[([^\]\d][^\]]*)\]", text)
        if m:   # 技能也會出現在連鎖演示上
            wm = re.match(r"\s*P(\d+)", text)
            self.chain_view.append(({"id": f"sk:{m.group(1)}:{self.chain_no}", "name": m.group(1), "color": "", "kind": "skill", "img": None, "text": f"〈{m.group(1)}〉",
                                    "desc": f"{text[:m.start()].strip()} 發動了「{m.group(1)}」的技能:\n{text[m.end():].strip()}"}, int(wm.group(1)) if wm else None))
        self.log(f"  [Chain {self.chain_no}] {text}")

    def emit(self, kind, src, tgt):
        """公開事件 -> 每個還活著的 AI 都能觀察 (用來推理身分)。
        kind: attack 針對性攻擊 / help 幫助 / hurt 造成傷害 / kill 擊殺 (tgt 身分已公開)"""
        for q in self.players:
            if q.alive and hasattr(q.agent, "observe"):
                q.agent.observe(self, q, kind, src, tgt)

    # 被動 (自動觸發、沒有選擇) 的技能不受「同一連鎖一次」限制;只限制主動發動 (要選擇) 的技能。
    # 被動技能仍設安全上限,避免全場同武將互相觸發時無限遞迴。
    PASSIVE_SKILLS = {"張飛-抽牌", "荀彧-抽牌", "華雄-判定", "孫堅-棄牌", "孫堅-奪牌", "呂蒙-判定五次", "魏延-抽牌", "曹仁-展示", "曹仁-回血",
                      "孟獲-獲得", "馬良-交牌", "司馬昭-判定", "夏侯惇-判定", "鄧艾-扣血", "滿寵-反擊", "張昭-翻面", "邯鄲淳-判定", "劉諶-抽牌",
                      "李嚴-抽牌", "李嚴-延時", "吳懿-抽牌"}
    PASSIVE_CAP = 8

    def trigger_ok(self, p, skill):
        """主動發動的武將技能在同一條連鎖上最多一次;被動技能不限次數 (上限 PASSIVE_CAP)。可發動則登記並回傳 True。"""
        if p.flipped:
            return False
        base = skill.rstrip("0123456789")
        if base in self.PASSIVE_SKILLS:
            key = (p.idx, base)
            n = self.chain_pcount.get(key, 0)
            if n >= self.PASSIVE_CAP:
                return False
            self.chain_pcount[key] = n + 1
            return True
        key = (p.idx, skill)
        if key in self.chain_used:
            return False
        self.chain_used.add(key)
        return True

    # ---------- 工具 ----------
    def log(self, msg):
        self.logs.append(msg)
        if self.verbose:
            print(msg)
        if self.on_log:
            self.on_log(msg)

    def alive_players(self):
        return [p for p in self.players if p.alive]

    def order_from(self, p):
        n = len(self.players)
        return [self.players[(p.idx + self.dir * i) % n] for i in range(n) if self.players[(p.idx + self.dir * i) % n].alive]

    def others(self, p):
        return self.order_from(p)[1:]

    def pick_side(self, p):
        """突襲 / 調虎離山 要選結算方向; 場上只剩一個其他人 (例如 2 人局) 時往左往右都一樣,不用問。"""
        return "L" if len(self.others(p)) <= 1 else p.agent.choose_dir(self, p)

    def side_order(self, p, side):
        """突襲 / 調虎離山: 從 p 的左邊 ('L' = 座位號遞增) 或右邊 ('R' = 遞減) 開始的其他人,不受輪次方向影響。"""
        n, st = len(self.players), (1 if side == "L" else -1)
        return [q for q in (self.players[(p.idx + st * i) % n] for i in range(1, n)) if q.alive]

    def distance(self, a, b):
        if a is b:
            return 0
        alive = self.alive_players()
        ia, ib = alive.index(a), alive.index(b)
        d = abs(ia - ib)
        d = min(d, len(alive) - d)
        if a.equip["h-"] and not self.equip_off():
            d -= 1
        if b.equip["h+"] and not self.equip_off():
            d += 1
        d += a.char.dist_mod(self, a, b)
        d += b.char.dist_in(self, b, a)
        return max(1, d)

    def pop_deck(self):
        if not self.deck:
            self.deck, self.discard = self.discard, []
            self.rng.shuffle(self.deck)
        return self.deck.pop() if self.deck else None

    def draw_phase(self, p, n):
        """抽牌階段的一般抽牌 (不受張紘限制)。"""
        if self.round == 1 and p.idx in self.scn_nodraw:
            n = 0
        old, self.ordinary = self.ordinary, True
        try:
            return self.draw(p, n)
        finally:
            self.ordinary = old

    def is_trick(self, c):
        """牌的種類是不是錦囊。魯肅在場時,全場基本牌的「種類」也算錦囊 (只是種類互換,不是能當任何一張錦囊用)。"""
        return c.kind == "trick" or (c.kind == "basic" and self.aura("basic_as_trick"))

    def aura(self, attr):
        """場上任一存活玩家 (技能有效) 具備的全場效果。"""
        return any(getattr(q.char, attr) for q in self.alive_players())

    def hand_cap(self, p):
        h = p.char.hand_limit(self, p, max(p.hp, 0))
        return min(h, 3) if self.aura("cap3") else h

    def check_hands(self):
        """有人手牌剛好變空 (曹休)。"""
        for q in list(self.alive_players()):
            q.max_hand = max(q.max_hand, len(q.hand))
            if q.hand:
                q.empty_seen = False
            elif not q.empty_seen:
                q.empty_seen = True
                q.char.on_hand_empty(self, q)

    def draw(self, p, n, blocked=False):
        if n > 0 and blocked and not self.ordinary and self.aura("no_extra_draw"):   # 擊殺獎勵: 張紘在場完全抽不到,不能用閃換
            self.log(f"  [張紘] {p.name} 不能抽牌 (非一般抽牌)")
            return []
        if n > 0 and not self.ordinary and self.aura("no_extra_draw"):   # 張紘: 一般抽牌以外完全抽不到 (可閃是第 3 個技能,不是這個)
            self.log(f"  [張紘] {p.name} 不能抽牌 (非一般抽牌)")
            return []
        got = []
        for _ in range(n):
            c = self.pop_deck()
            if c is None:
                break
            got.append(c)
        p.hand.extend(got)
        p.max_hand = max(p.max_hand, len(p.hand))
        if got:
            self.log(chr(1) + f"DRAW|{p.idx}|{len(got)}")   # 給前端音效用的隱藏行
        if got and not self.ordinary:
            p.char.after_extra_draw(self, p, got)   # 孫策: 非抽牌階段的抽牌 (增/無/重鑄…) 抽到黑牌也多抽
        return got

    def flip_judge(self, who=None):
        c = self.pop_deck()
        if c is None:  # 牌堆和棄牌堆都空了: 沒有判定牌,視為黑色空白牌 (不進棄牌堆)
            self.log("  牌堆已空,判定沒有牌 (視為黑色)")
            return Card(-1, "空白", "黑", "basic")
        if who is not None and c is not None:
            for q in self.alive_players():
                if q.char.judge_pick and q.hp == 1:  # 張苞: 看牌堆頂 3 張,挑一張當判定牌
                    top = [c] + [x for x in (self.pop_deck() for _ in range(2)) if x]
                    pick = q.agent.pick_pile(self, q, top)
                    top.remove(pick)
                    self.deck.extend(reversed(top))
                    self.log(f"  [張苞] {q.name} 決定 {who.name} 的判定牌: {pick}")
                    c = pick
                    break
        self.discard.append(getattr(c, "orig", c))
        self.last_judge = (who.idx if who is not None else None, c)
        self.log(f"JUDGE|{who.idx if who is not None else -1}|{c.color}")   # 給前端音效用的隱藏行
        if who is not None and who.alive:
            who.char.on_judged(self, who, c)   # 袁術: 自己判定也算牌被捨棄
        for q in list(self.alive_players()):
            q.char.on_any_judge(self, q, who, c)   # 郭嘉: 任何人判定翻出的牌都可以拿走
        return c

    def discard_card(self, p, c, played=False):   # played=True: 這是「使用 / 打出」的牌 (無懈、閃、殺回應...),不算被捨棄,不觸發袁術
        if not (c in p.hand or c in p.judge or any(v is c for v in p.equip.values())):
            return  # 已經不在他身上 (例如連鎖效果先把牌棄光了)
        was_equip = any(v is c for v in p.equip.values())
        self.remove_from(p, c)
        self.discard.append(getattr(c, "orig", c))
        if was_equip:
            for q in list(self.alive_players()):
                if q is not p:
                    q.char.on_equip_broken(self, q, p, c)
        if p.alive and not played:
            p.char.on_cards_discarded(self, p, c)

    def remove_from(self, p, c):
        if c in p.hand:
            p.hand.remove(c)
        elif c in p.judge:
            p.judge.remove(c)
        else:
            for k, v in p.equip.items():
                if v is c:
                    p.equip[k] = None

    def count_cards(self):
        return len(self.deck) + len(self.discard) + sum(
            len(p.all_cards()) + len(p.judge) + len(p.stash) for p in self.players)

    # ---------- 傷害 / 瀕死 / 死亡 ----------
    def damage(self, src, tgt, n, via_sha=False, nature=None, _bonus=True, _chain=False, _mods=True):
        """nature: None / '火' / '雷' / '冰'"""
        self.__dict__.pop("_react_declined", None)
        self.__dict__.pop("_pre_react", None)
        er = self.__dict__.pop("_early_react", None)   # 出閃的詢問裡就選好了反 / 調 / 占 (一次問完): 接到這次傷害上
        if er is not None and er[2] is tgt and er[0] in tgt.hand:
            self._pre_react, self._react_pick = er[0], er[1]
        raw = n   # 還沒算任何加成的原始傷害: 反擊轉出去時從這個重算 (來源變成反擊的人,用他的加成)
        if not tgt.alive or n <= 0:
            return
        if nature is None and tgt.char.plain_immune(self, tgt):
            self.log(f"  {tgt.name} 不受非屬性傷害")
            return
        if tgt.char.damage_only_sha and not via_sha:
            self.log(f"  {tgt.name} 只會被殺傷害,此傷害無效")
            return
        if nature and tgt.char.immune_nature(self, tgt, nature):
            self.log(f"  {tgt.name} 不受{nature}傷害")
            return
        qg = via_sha and src is not None and src.has_weapon("青釭劍")   # 青釭劍: 殺無視對方防具 (屬性盾 / 緩衝盾也一樣)
        immune = NATURE_ARMOR.get(nature)
        if immune and not qg and tgt.has_armor(immune):
            self.log(f"  {tgt.name} 的{immune}: {nature}傷害無效")
            return
        if nature == "火" and not qg and tgt.has_armor("藤甲"):
            n += 1
        if _bonus and src and src.has_weapon("流星錘"):
            n += 1
        if src and src is not tgt and _mods:
            n = src.char.dmg_dealt_mod(self, src, tgt, n)
        n0 = n   # 還沒乘強化 / 弱化的傷害 (傷害結算前的 ⚡ 連鎖出了強 / 弱就從這裡重算)
        if not self.void and _mods:   # 反轉移出去的傷害不再重複乘 (否則每轉一手就 x2)
            if src:
                n *= 2 ** src.dmg_x2   # 強: 該玩家本回合「造成」的傷害 x2
            if src:
                n //= 2 ** src.dmg_half   # 弱: 該玩家本回合「造成」的傷害 ÷2 (無條件捨去)
            shield = 0 if qg else tgt.armor_names().count("緩衝盾")
            if n - shield > 0:   # 扣掉緩衝盾後是 0 點傷害就不用問 ⚡ 連鎖
                n = self._damage_window(src, tgt, n0, n, raw, shield)
                if self.__dict__.get("_pre_react") is not None:   # 傷害結算前已經選了反 / 調 / 占: 「要受到傷害時」就先結算,不管後面緩衝盾 / 曹真阻擋之類會不會把傷害減掉
                    n = self.damage_reactions(src, tgt, n, nature, raw)
                    self._react_declined = True   # 已經問過了,後面不再問第二次
                    if n <= 0 or not tgt.alive:
                        return
        if not qg:
            n -= tgt.armor_names().count("緩衝盾")
        n = tgt.char.cap_damage(self, tgt, n)
        if n > 0:
            n = tgt.char.pre_damage(self, tgt, src, n, nature)
        if n <= 0:
            if not self.__dict__.pop("_absorbed", False):   # 楊修吸收時已經寫過「吸收 N 點傷害」,不再重複寫「被抵銷」
                self.log(f"  {tgt.name} 的傷害被抵銷")
            return
        n = self.damage_reactions(src, tgt, n, nature, raw)
        if n > 0 and tgt.alive:
            n = tgt.char.cap_damage(self, tgt, n)   # 打出反 / 調 / 占 之後手牌可能空了 (諸葛亮: 沒手牌不扣血),要重新檢查
        if n <= 0 or not tgt.alive:
            return
        tgt.hp -= n
        tgt.dmg_turn += n
        if src is not None and src is not tgt:
            src.dmg_total += n
        self.last_dealt = n
        self.stats["damage"] += n
        self.log(f"  {tgt.name} 受到 {n} 點{nature or ''}傷害 (來源 {src.name if src else '技能或牌的效果'}) -> 體力 {tgt.hp}")
        if src and src is not tgt and tgt.role == "主公":
            self.lord_attackers.add(src.idx)
        if src and src is not tgt and not self.in_group:
            self.emit("hurt", src, tgt)
        if tgt.hp <= 0:   # 先確定是不是真的死了: 死人不能發動受傷後的被動技能
            self.dying(tgt, src)
        if tgt.alive:
            self.dmg_hook_depth += 1
            try:
                tgt.char.on_damaged(self, tgt, src, n)
            finally:
                self.dmg_hook_depth -= 1
        self.gelan(n)   # 隔岸觀火: 受傷結算完 (含瀕死、受傷後技能) 才問
        if src and src is not tgt and src.alive:
            src.char.on_deal_damage(self, src, tgt, n)
        for q in self.alive_players():
            q.char.on_any_damaged(self, q, tgt, n)
        horses = [c for k, c in tgt.equip.items() if c and k in ("h+", "h-")]
        if tgt.alive and src and src.has_weapon("麒麟弓") and horses and getattr(self.cur_card, "name", None) == "殺":
            c = horses[0] if len(horses) == 1 else src.agent.choose_discard(self, src, 1, horses)[0]
            self.log(f"  麒麟弓: {src.name} 棄置 {tgt.name} 的 {c}")
            self.discard_card(tgt, c)
        if tgt.chained and not _chain:   # 鐵索連環: 不限屬性;只傳導這一次,有人受傷後所有被連的人都重置
            linked = [q for q in self.order_from(tgt) if q.chained and q.alive]
            for q in linked:
                q.chained = False
            for q in linked:
                if q is not tgt and q.alive:
                    self.log(f"  鐵索連環: {q.name} 同受{nature or ''}傷害")
                    self.damage(src, q, n, nature=nature, _bonus=False, _chain=True, _mods=False)
        if tgt.alive:
            tgt.char.after_damage(self, tgt)   # 這次傷害全部結算完 (含瀕死、連鎖) 才跳出的選擇

    def _damage_window(self, src, tgt, n0, n, raw=None, shield=0):
        """傷害結算前: 受傷的人和傷害來源,手上只要有 ⚡ 牌 (強 / 弱 / 降雷 / 孤 / 出) 就問要不要接連鎖
        (例如王允反彈時,強化王允 → 傷害 x2);打出強 / 弱後從 n0 重算。反 / 調 / 占 之後在 damage_reactions 問。"""
        askers = [tgt] + ([src] if src is not None and src is not tgt else [])
        self._dmg_ctx = (src, tgt)
        self._react_declined = False
        for _ in range(3):
            acted = False
            for q in askers:
                if not (q.alive and tgt.alive and (src is None or src.alive)):
                    continue
                if n - shield <= 0:   # 打出弱化後傷害變 0: 不用再問
                    self._dmg_ctx = None
                    return n
                opts = [(c, t) for c, t in self.play_options(q) if not isinstance(c, SkillAct) and c.name in ("強", "弱", "降雷", "孤", "出")]
                reacts, vname = self._reaction_cands(tgt) if q is tgt and hasattr(q.agent, "_ask") and self.__dict__.get("_pre_react") is None else ([], None)   # 真人受傷: 反 / 調 / 占 也列在同一個詢問裡 (電腦照舊在 damage_reactions 決定)
                if not opts and not reacts:
                    continue
                rmap = {}   # 詢問裡的選項 -> (實際手牌, 當成哪種): 手牌是當作別的牌用的,選項要寫「閃 → 調虎離山」
                for c in reacts:
                    for k in self._react_kinds(tgt, c):
                        o = c if c.name == k else ViewCard(k, c.color, "trick", c, id=c.id)
                        rmap[id(o)] = (c, k)
                        opts.append((o, None))
                note = f" (反擊轉出 {self.dmg_preview(tgt, (raw if raw is not None else n) * (2 if tgt.char.fan_double else 1), bonus=True)} 點)" if any(vname(x) == "反" for x in reacts) else ""
                sh_note = f" (緩衝盾 −{shield})" if shield else ""   # 緩衝盾會在這之後才扣,提示直接寫扣完的點數
                i = q.agent.choose_offturn(self, q, opts, tgt, f"即將受到 {max(0, n - shield)} 點傷害{sh_note}{note}")
                if i is None:
                    if reacts:
                        self._react_declined = True   # 已經問過要不要出反 / 調 / 占 了,不再問第二次
                    continue
                c, t = opts[i]
                if q is tgt and id(c) in rmap:   # 選的是反 / 調 / 占: 交給 damage_reactions 結算 (不再問第二次)
                    c, self._react_pick = rmap[id(c)]
                    self._pre_react = c
                    self._dmg_ctx = None
                    return n
                self.new_chain()
                self.link(f"{q.name} 在傷害結算前連鎖使用 ⚡{c}" + (f" (對 {t.name})" if hasattr(t, "name") else ""))
                self._announced = True   # 這一行已經寫過「連鎖使用 ⚡牌」了,execute 不要再寫一次 (紀錄 / 動畫不重複)
                self.execute(q, c, t)
                self.after_play(q, c)
                if src is not None:
                    n = n0 * 2 ** src.dmg_x2 // 2 ** src.dmg_half
                acted = True
                break
            if not acted:
                break
        self._dmg_ctx = None
        return n

    def dmg_preview(self, src, n, tgt=None, nature=None, bonus=False):
        """提示文字用: 照 damage() 的順序先算一遍 (不改任何狀態),n 點傷害實際會是幾點。
        含流星錘 (bonus)、藤甲、來源武將的加成 (司馬昭 / 許褚…)、強化 / 弱化、緩衝盾、受傷上限 (一回合最多扣 N)。
        tgt 不確定 (例如「其他人」) 時略過對象那邊的防具 / 上限;要攔下傷害的技能 (pre_damage) 要問人,算不進來。"""
        t = tgt
        if t is None and src is not None:
            t = next(iter(self.others(src)), None)
        if tgt is not None and nature == "火" and tgt.has_armor("藤甲"):
            n += 1
        if bonus and src is not None and src.has_weapon("流星錘"):
            n += 1
        if src is not None and t is not None and src is not t:
            n = src.char.dmg_dealt_mod(self, src, t, n)
        if src is not None and not self.void:
            n = n * 2 ** src.dmg_x2 // 2 ** src.dmg_half
        if tgt is not None:
            n -= tgt.armor_names().count("緩衝盾")
            n = tgt.char.cap_damage(self, tgt, n)
        return max(0, n)

    def _reaction_cands(self, tgt):
        """受傷時能當 反 / 調 / 占 用的手牌,和「這張牌當成哪一種」的函式。"""
        banned = self.banned()
        def vname(c):   # 這張牌在這裡當成哪一種 (沒得用就 None)
            if c.name in ("反", "調", "占"):
                return None if c.name in banned else c.name
            return next((k for k in ("調", "占") if k not in banned and tgt.char.as_card(self, tgt, c, k)), None)
        if self.void or self.trick_locked(tgt):   # 呂布無效 / 鐘繇沒手牌: 反 / 調 / 占 也是錦囊,不能用
            return [], vname
        return [c for c in tgt.hand if vname(c)], vname

    def _react_kinds(self, tgt, c):
        """這張手牌在受傷時可以當成哪幾種 (反 / 調 / 占): 閃可以當調虎離山的人,詢問時要明講「閃 → 調虎離山」。"""
        banned = self.banned()
        if c.name in ("反", "調", "占"):
            return [] if c.name in banned else [c.name]
        return [k for k in ("調", "占") if k not in banned and tgt.char.as_card(self, tgt, c, k)]

    def damage_reactions(self, src, tgt, n, nature, raw=None):
        """⚡ 反/調/占: 要受到傷害時使用。回傳實際要承受的傷害 (0=被抵銷或轉移)。"""
        pre = self.__dict__.pop("_pre_react", None)   # 傷害結算前的 ⚡ 詢問裡,受傷的人已經選好的反 / 調 / 占 (合併成一次詢問)
        if self.__dict__.pop("_react_declined", False) and pre is None:
            return n
        while n > 0 and tgt.alive:
            cands, vname = self._reaction_cands(tgt)
            if not cands:
                break
            fan_n = None   # 打反擊轉出去的實際傷害 (原樣轉出;張昭加倍): 問的時候一起告訴玩家
            if any(vname(x) == "反" for x in cands):
                fan_n = self.dmg_preview(tgt, (raw if raw is not None else n) * (2 if tgt.char.fan_double else 1), bonus=True)
            if pre is not None and pre in cands:
                c, pre = pre, None
            else:
                pre = None
                c = tgt.agent.respond(self, tgt, "受傷響應", cands, {"src": src, "n": n, "nature": nature, "fan_n": fan_n})
            if not c:
                break
            self.discard_card(tgt, c)
            self.chain_view.append((c, tgt.idx))
            pick = self.__dict__.pop("_react_pick", None)
            cname = pick if pick in self._react_kinds(tgt, c) or pick == c.name else (vname(c) or "調")
            self.log(f"  {tgt.name} 使用 {c}" + ("" if cname == c.name else f" 當作 {cname}"))
            for q in list(self.alive_players()):
                q.char.on_card_used(self, q, tgt, c)
            self.after_play(tgt, c if c.kind == "trick" else ViewCard(cname, "", "trick", c))   # 反 / 調 / 占 也是錦囊: 鄧艾 / 崔琰 / 曹沖等「有人使用錦囊」的技能要觸發
            if not tgt.alive:
                return 0
            v = None
            if cname == "反":   # 先選好對象並寫進紀錄,才問大家要不要無懈
                victims = [q for q in self.alive_players() if q is not tgt]
                if victims:
                    v = tgt.agent.choose_target(self, tgt, "反", victims)
                    self.log(f"  {tgt.name} 對 {v.name} 使用 反擊")
            side = self.pick_side(tgt) if cname == "調" else None   # 調虎離山也一樣: 先選方向再問無懈
            if self.wuxie_contest(tgt, tgt, cname, False):
                continue
            if cname == "反":
                if v is not None:
                    self.log(f"  傷害改由 {v.name} 承受")
                    self.damage(tgt, v, (raw if raw is not None else n) * (2 if tgt.char.fan_double else 1), nature=None)   # 反擊: 傷害來源變成你,從「原始傷害」用你的流星錘 / 武將加成 / 強化 / 弱化重新算 (不是拿已經乘過的數字再乘);張昭加倍,轉出去變成無屬性
                    return 0
            elif cname == "占":
                j = self.flip_judge(tgt)
                self.log(f"  占卜判定 {j}")
                if j.kind == "trick":
                    self.log("  占卜: 判定到錦囊牌,傷害抵銷")
                    return 0
            elif cname == "調":
                order = self.side_order(tgt, side)
                for _ in range(40):   # 繞一圈 (別人依序,最後輪到使用者自己) 都出了閃就再繞一圈,直到有人沒出閃
                    for q in order + [tgt]:
                        if q.alive and not self.need_response(q, "閃", {"attacker": tgt, "group": "調"}):
                            if q is tgt:
                                self.log(f"  {tgt.name} 沒出閃,承受原本的傷害")
                                return n   # 輪到自己也沒閃: 原本的傷害照受 (不再觸發一次反應)
                            self.damage(tgt, q, n, nature=None, _bonus=False, _mods=False)   # 轉出去的傷害變成無屬性
                            return 0   # 調虎離山: 有人沒出閃受到傷害,結算就停止,原本的傷害也抵銷
                    if not any(q.alive for q in order):
                        break
        return n

    def equip_off(self):
        """呂布無效 / 太史慈: 全場裝備 (武器、防具、坐騎) 不產生效果。"""
        return self.void or any(q.char.equip_void for q in self.alive_players())

    def banned(self):
        """鍾繇: 全場禁用的牌名 (翻面也有效;呂布無效時不禁)。"""
        if self.void:
            return set()
        out = set()
        for q in self.alive_players():
            out |= q._char.bans
        return out

    def gelan(self, n):
        """⚡ 隔: 有玩家受到傷害時,持有者可抽等同傷害量的牌。"""
        for q in self.order_from(self.cur):
            cands = [c for c in q.hand if c.name == "隔"]
            if cands and q.agent.respond(self, q, "隔", cands, {"n": n}):
                self.discard_card(q, cands[0], played=True)
                self.log(f"  {q.name} 使用 隔, 抽 {n} 張")
                self.draw(q, n)

    def heal(self, p, n=1):
        if p.hp < p.maxhp:
            old = p.hp
            p.hp = min(p.maxhp, p.hp + n)
            p.healed += p.hp - old
            self.log(f"HEAL|{p.idx}|{n}")   # 給前端特效 / 音效用的隱藏行
            p._char.on_healed(self, p)

    def dying(self, tgt, src):
        self.log(f"  {tgt.name} 瀕死 (體力 {tgt.hp})")
        tgt.char.on_dying(self, tgt)
        while tgt.hp <= 0 and tgt.alive:
            for q in self.order_from(tgt):   # 劉備: 仁可以救瀕死的人
                if tgt.hp > 0 or not tgt.alive:
                    break
                if q.alive:
                    q.char.on_dying_help(self, q, tgt)
            if tgt.hp > 0 or not tgt.alive:
                break
            saved = False
            self.log("  依序詢問 " + "、".join(q.name for q in self.order_from(tgt)) + f" 是否出桃/酒救 {tgt.name}")
            entries = []
            for q in self.order_from(tgt):
                cands = [c for c in q.hand if c.name in ("桃", "酒") or q.char.as_card(self, q, c, "桃")]
                cands.sort(key=lambda c: c.name == "酒")   # 桃排前面,酒當備用
                if cands:
                    entries.append((q, cands))
            hum = [(q, cs) for q, cs in entries if hasattr(q.agent, "respond_race")]
            if len(hum) >= 2:   # 多個真人: 同時詢問,先出桃的人救;全部不出才輪到電腦
                r = hum[0][0].agent.respond_race(self, hum, tgt)
                if r:
                    entries = [r[:1] + ([r[1]],)]
                    first = r
                else:
                    entries = [(q, cs) for q, cs in entries if not hasattr(q.agent, "respond_race")]
                    first = None
            else:
                first = None
            for q, cands in entries:
                c = first[1] if first else q.agent.respond(self, q, "桃", cands, {"target": tgt})
                if c:
                    self.discard_card(q, c, played=True)
                    if c.name == "酒":
                        amt = max(2, q.char.jiu_heal(self, q))   # 酒救人: 回 2 點 (跟桃一樣,不夠還是瀕死)
                    else:
                        amt = q.char.peach_heal(self, q)
                    gain = max(0, min(amt, tgt.maxhp - tgt.hp))   # 體力不能超過上限 (上限 1 被酒救會變 2/1)
                    tgt.hp += gain
                    tgt.healed += gain
                    self.log(f"HEAL|{tgt.idx}|1")
                    self.log(f"  {q.name} 對 {tgt.name} 使用 {c} -> 體力 {tgt.hp}")
                    if q is not tgt:
                        self.emit("help", q, tgt)
                    saved = True
                    break
            if not saved:
                self.log(f"  無人出桃,{tgt.name} 陣亡")
                break
        if tgt.hp <= 0:
            self.die(tgt, src)

    def die(self, tgt, src):
        tgt.alive = False
        self.stats["kills"] += 1
        self.revealed[tgt.idx] = tgt.role
        for q in list(self.alive_players()):
            q.char.on_any_death(self, q, tgt, src)
        if src and src is not tgt:
            self.emit("kill", src, tgt)
        self.log(f"  *** {tgt.name} 陣亡 ***")
        taker = next((q for q in self.alive_players() if q.char.takes_dead_cards(self, q)), None)
        mine = tgt.all_cards()
        if taker:
            taker.hand.extend(mine)
            self.log(f"  {taker.name} 獲得 {tgt.name} 的 {len(mine)} 張牌")
        else:
            self.discard.extend(mine)
        self.discard.extend(getattr(c, "orig", c) for c in tgt.judge + tgt.stash)
        tgt.hand, tgt.judge, tgt.stash = [], [], []
        tgt.equip = dict(EMPTY_EQUIP)
        self.check_win()
        if src and src.alive:
            if tgt.role == "反賊":
                if self.draw(src, 3, blocked=True):
                    self.log(f"  {src.name} 擊殺反賊,抽3張")
            elif tgt.role == "忠臣" and src.role == "主公":
                for c in src.all_cards():
                    self.discard_card(src, c)
                self.log("  主公誤殺忠臣,棄置所有手牌與裝備")

    def check_win(self):
        if self.noroles:   # 無身分: 只剩一人就是他贏
            alive = self.alive_players()
            if len(alive) <= 1:
                self.winner = f"P{alive[0].idx}" if alive else "平手"
                raise GameOver()
            return
        roles = [p.role for p in self.alive_players()]
        if len(roles) == 2 and "內奸" in roles and self.lord.alive:   # 內奸撐到和主公單挑: 段位結算算「次級勝利」
            for q in self.alive_players():
                if q.role == "內奸":
                    q.duel1 = True
        if not self.lord.alive:
            self.winner = "內奸" if roles == ["內奸"] else "反賊"
        elif "反賊" not in roles and "內奸" not in roles:
            self.winner = "主公陣營"
        if self.winner:
            raise GameOver()

    # ---------- 無懈 / 響應 ----------
    def trick_locked(self, user):
        """鐘繇: 他沒有手牌時,別人 (不含他自己) 不能使用錦囊牌 (無懈 / ⚡ 也算)。"""
        return any(q.alive and q is not user and q.char.trick_lock(self, q) for q in self.players)

    def wuxie_contest(self, src, tgt, trick_name, harmful, targets=None):
        """回傳 True 代表此錦囊對 tgt 被無效。"""
        negated = False
        last_by = None
        while True:
            played = False
            for q in self.order_from(self.cur):
                cands = [c for c in q.hand if c.name == "無懈"]
                if not cands or self.trick_locked(q):
                    continue
                ctx = {"trick": trick_name, "source": src, "target": tgt, "targets": targets, "harmful": harmful,
                       "negated": negated, "last_wuxie_by": last_by}
                c = q.agent.respond(self, q, "無懈", cands, ctx)
                if c:
                    self.discard_card(q, c, played=True)
                    self.chain_view.append((c if c.name == "無懈" else ("as無懈", c), q.idx))   # 魯肅: 基本牌當無懈
                    negated = not negated
                    last_by = q
                    self.link(f"{q.name} 使用 無懈 ({_fn(trick_name)})")
                    if tgt is not q and isinstance(tgt, Player):
                        # 擋下有害錦囊 = 幫助 tgt;擋下有益錦囊 = 針對 tgt (再翻回來則相反)
                        self.emit("help" if negated == harmful else "attack", q, tgt)
                    self.log(f"  -> 結算後錦囊{'無效' if negated else '生效'}")
                    played = True
                    break
            if not played:
                return negated

    def need_response(self, p, name, ctx=None):
        """要求 p 打出一張 name。回傳 True 代表打出。"""
        ctx = ctx or {}
        self.__dict__.pop("_early_react", None)
        ans = self.__dict__.pop("_pre_ans", None)   # 殺指定目標後的合併詢問 (連鎖 ⚡ / 出閃 / 受傷前 ⚡ 一次問完) 已經回答過了
        if ans is not None and (name != "閃" or ans["tgt"] is not p):
            ans = None
        if name == "閃" and ctx.get("attacker") is not None:
            ctx["react"] = True   # 不閃就會受傷: 真人的詢問裡一起列出 ⚡ 反 / 調 / 占 (閃可以當調虎離山的人,點下去分「當閃」或「當調虎離山」)
        if name == "閃" and not ctx.get("ignore_armor") and (
                p.has_armor("八卦陣") or (not p.armor_names() and p.char.virtual_bagua(self, p))):
            j = self.flip_judge(p)
            self.log(f"  {p.name} 八卦陣判定 {j}")
            if j.color == "紅":
                return True
        cands = [c for c in p.hand if c.name == name or p.char.as_card(self, p, c, name)]
        if name == "殺" and p.has_weapon("丈八蛇矛") and len(p.hand) >= 2:  # 兩張手牌當一張殺打出
            low = sorted(p.hand, key=lambda x: _CV.get(x.name, 3 if x.kind == "trick" else 2))[:4]
            cands += [PairView("殺", "", "basic", a, extra=b) for a, b in itertools.combinations(low, 2)]
        if ans is not None and ans["react"]:
            self._early_react = (*ans["react"], p)   # 選了受傷前的 ⚡ 牌 = 不出閃,傷害結算時直接用
        if not cands:
            return False
        if ans is not None:
            c = ans["shan"] if ans["shan"] in cands else None
        else:
            c = p.agent.respond(self, p, name, cands, ctx)
        if c:
            if isinstance(c, PairView):
                self.discard_card(p, c.orig, played=True)
                self.discard_card(p, c.extra, played=True)
            else:
                self.discard_card(p, c, played=True)
            self.log(f"  {p.name} 打出 {c}")
            if name == "殺":
                p.sha_n += 1
            if name == "閃":
                for x in self.alive_players():
                    if x is not p and x.alive:
                        x.char.on_other_dodge(self, x, p)
            self.check_hands()
            return True
        return False

    def sha_window(self, p, tgt, card, when=None):
        """牌指定目標後、目標響應前: 目標可接連鎖使用 ⚡ 強 / 弱 / 降雷 / 孤 / 出 (各牌自己的條件由 play_options 決定)。
        反 / 調 / 占 在『要受到傷害時』、無懈 在錦囊結算時、隔 在受傷時各自詢問。"""
        self._chain_asked.add((id(card), tgt.idx))
        voided = False   # 呂布在這個窗口發動了無效 → 呼叫端可以讓這張牌沒有效果
        for _ in range(3):
            if not (tgt.alive and p.alive):
                return voided
            opts = [(c, t) for c, t in self.play_options(tgt)
                    if not isinstance(c, SkillAct) and c.name in ("強", "弱", "降雷", "孤", "出", "漁")]
            if tgt.char.name == "呂布" and p is not tgt:   # 呂布被指定時,也能在這個時機發動「無效全場一回合」
                opts += [(c, t) for c, t in tgt.char.skill_options(self, tgt) if getattr(c, "name", "") == "呂布-無效全場"]
            if not opts:
                return voided
            merged, rmap, shan_ids = False, {}, set()
            if getattr(card, "name", "") == "殺" and not when and hasattr(tgt.agent, "_ask"):
                # 真人被殺: 連鎖 ⚡ / 出閃 / 受傷前的 ⚡ (反 / 調 / 占) 放在同一個詢問裡,不要分兩次問
                merged = True
                for c in tgt.hand:
                    if c.name == "閃" or tgt.char.as_card(self, tgt, c, "閃"):
                        opts.append((c, None)); shan_ids.add(id(c))
                rc, _ = self._reaction_cands(tgt)
                for c in rc:
                    for k in self._react_kinds(tgt, c):
                        o = c if c.name == k else ViewCard(k, c.color, "trick", c, id=c.id)
                        rmap[id(o)] = (c, k)
                        opts.append((o, None))
            cur, w = p, when or f"對你使用{_fn(card.name)}"
            if when and when.startswith("使用了") and self.chain_view:   # 連鎖上已有別人接的牌: 問的是最新那張
                last, who = self.chain_view[-1]
                if not isinstance(last, (tuple, dict)) and hasattr(last, "name") and isinstance(who, int) and who != p.idx and who != tgt.idx:
                    from view import full_name
                    cur, w = self.players[who], f"使用了{full_name(last.name)}"
            self._offturn_merged = merged
            try:
                i = tgt.agent.choose_offturn(self, tgt, opts, cur, w)
            finally:
                self._offturn_merged = False
            if merged and (i is None or id(opts[i][0]) in shan_ids or id(opts[i][0]) in rmap):
                ans = {"tgt": tgt, "shan": None, "react": None}   # 選出閃 / 受傷前 ⚡ / 不出: 之後 need_response 直接照這個結果,不再問
                if i is not None:
                    c0 = opts[i][0]
                    if id(c0) in rmap:
                        ans["react"] = rmap[id(c0)]
                    else:
                        ans["shan"] = c0
                self._pre_ans = ans
                return voided
            if i is None:
                return voided
            c, t = opts[i]
            self.new_chain()
            if isinstance(c, SkillAct):
                self.link(f"{tgt.name} 對 {p.name} 的{_fn(card.name)}發動 {c.name}")
                self.execute(tgt, c, t)
                voided = voided or self.void
                continue
            self.link(f"{tgt.name} 對 {p.name} 的{_fn(card.name)}連鎖使用 ⚡{c}")
            self._announced = True   # 這一行已經寫過「連鎖使用 ⚡牌」了,execute 不要再寫一次 (紀錄 / 動畫不重複)
            self.execute(tgt, c, t)
            self.after_play(tgt, c)
        return voided

    def chain_all_window(self, p, card, tgt):
        """「全部都問」模式: 別人每打出一張牌,選了這個模式的真人都有機會接連鎖使用 ⚡ (強 / 弱 / 降雷 / 孤 / 出)。"""
        if not self.chain_all or self.exec_depth > 2 or getattr(card, "name", "") in ("無懈", "強", "弱", "降雷", "孤", "出", "漁"):
            return
        from view import full_name
        for q in self.order_from(p):
            if q is p or not q.alive or q.idx not in self.chain_all or (id(card), q.idx) in self._chain_asked or q is tgt:
                continue
            self._chain_asked.add((id(card), q.idx))
            opts = [(c, t) for c, t in self.play_options(q)
                    if not isinstance(c, SkillAct) and c.name in ("強", "弱", "降雷", "孤", "出", "漁")]
            if not opts or not p.alive:
                continue
            vt = [x.name for x in ([tgt] if isinstance(tgt, Player) else [x for x in tgt if isinstance(x, Player)] if isinstance(tgt, (tuple, list)) else []) if x is not p]
            i = q.agent.choose_offturn(self, q, opts, p, f"使用了{full_name(card.name)}" + (f" (對 {'、'.join(vt)})" if vt else ""))
            if i is None:
                continue
            c, t = opts[i]
            self.new_chain()
            self.link(f"{q.name} 對 {p.name} 的{_fn(card.name)}連鎖使用 ⚡{c}")
            self._announced = True   # 這一行已經寫過「連鎖使用 ⚡牌」了,execute 不要再寫一次 (紀錄 / 動畫不重複)
            self.execute(q, c, t)
            self.after_play(q, c)

    def _thunder_body(self, p, tgt):
        self.log(f"{p.name} 對 {tgt.name} 使用 降雷")
        self.thunder_window(p, tgt)   # 連鎖上可以接任意多個降雷,後出的先結算
        if not tgt.alive:
            return
        if not self.wuxie_contest(p, tgt, "降雷", tgt is not p):
            if tgt.char.thunder_reflect and tgt is not p:
                self.log(f"  {tgt.name}: 降雷對他無效,{p.name} 扣 1 點體力")
                self.damage(None, p, 1)
            elif tgt.flipped and tgt.flip_char.no_thunder_unflip:
                self.log(f"  {tgt.name} 不能被降雷翻回正面")
            else:
                prev = tgt.flipped
                new = not (tgt.dg_flip if tgt.disguise else prev)   # 偽裝中被降雷: 偽裝的那張和本尊一起翻
                if new and not prev:   # 即將被翻面: 呂蒙等「翻面時」的技能先發動 (和 flip_char 一樣,翻之前還能用技能)
                    tgt.flip_char.on_flipped(self, tgt)
                tgt.flipped = new
                if tgt.disguise:
                    tgt.dg_flip = new
                if tgt.thunder is None or tgt.thunder[0] != self.turn_id:
                    tgt.thunder = (self.turn_id, prev)
                self.log(f"  {tgt.name} 的武將牌翻成{'背面' if tgt.flipped else '正面'},直到回合結束")

    def thunder_window(self, p, tgt):
        """降雷 (⚡) 指定目標後: 所有人 (目標優先) 可以接連鎖再出降雷,可疊多個,後出的先結算。"""
        for _ in range(8):   # 連鎖上最多再接 8 個
            acted = False
            for q in self.order_from(tgt):
                if not q.alive or not p.alive:
                    continue
                opts = [(c, t) for c, t in self.play_options(q)
                        if not isinstance(c, SkillAct) and c.name == "降雷"]
                if not opts:
                    continue
                i = q.agent.choose_offturn(self, q, opts, p, f"降雷連鎖:{p.name} 對 {tgt.name} 使用降雷")
                if i is None:
                    continue
                c, t = opts[i]
                self.new_chain()
                self.link(f"{q.name} 連鎖使用 ⚡{c} (對 {t.name})")
                self._announced = True   # 這一行已經寫過「連鎖使用 ⚡牌」了,execute 不要再寫一次 (紀錄 / 動畫不重複)
                self.execute(q, c, t)
                self.after_play(q, c)
                acted = True
                break
            if not acted:
                return

    def use_sha(self, p, tgt, card, count=True):
        self.__dict__.pop("_pre_ans", None)
        try:
            return self._use_sha(p, tgt, card, count)
        finally:
            self.__dict__.pop("_pre_ans", None)

    def _use_sha(self, p, tgt, card, count=True):
        if count:
            self.sha_used += 1
        self.log(f"{p.name} 對 {tgt.name} 使用 {card}")
        p.sha_n += 1
        self.sha_total += 1
        p.char.on_sha_used(self, p, card)
        self.sha_window(p, tgt, card)
        if not (p.alive and tgt.alive):
            return
        if tgt.char.sha_reflect:
            self.log(f"  {tgt.name}: 殺對他無效,使用者 -1 點體力 (可閃)")
            if not self.need_response(p, "閃", {"attacker": tgt}):
                self.damage(tgt, p, 1)
            return
        ignore = p.has_weapon("青釭劍")
        fire = p.has_weapon("孔雀羽扇") and not tgt.has_armor("火盾")  # 孔雀羽扇: 殺當火焰傷害的殺
        sn = getattr(card, "nature", None) or getattr(getattr(card, "orig", None), "nature", None)  # 屬性殺
        nature = "火" if fire else sn
        dmg = 1
        if self.jiu:
            dmg += 1
            self.jiu = False
        if fire:
            self.log("  孔雀羽扇: 這張殺造成火焰傷害")
        if not ignore and not fire and not sn and tgt.has_armor("仁王盾") and card.color == "黑":
            self.log("  仁王盾: 黑色殺無效")
            return
        if not ignore and not fire and not sn and tgt.has_armor("藤甲"):
            self.log("  藤甲: 殺無效")
            return
        if not ignore and not fire and not sn and card.color == "黑" and not tgt.armor_names() and tgt.char.virtual_renwang(self, tgt):
            self.log("  仁王盾 (臨時): 黑色殺無效")
            return
        dodged = True
        for _ in range(max(1, p.char.sha_dodge_need(self, p, tgt))):
            if not self.need_response(tgt, "閃", {"attacker": p, "ignore_armor": ignore}):
                dodged = False
                break
        if dodged and p.has_weapon("貫石斧") and p.alive and tgt.alive:  # 被閃: 可棄兩張牌強制命中
            pool = [c for c in p.all_cards() if c.name != "貫石斧"]
            if len(pool) >= 2:
                self.cur_sha_target = tgt
                if p.agent.choose_skill(self, p, "貫石斧-強中"):
                    for c in p.agent.choose_discard(self, p, 2, pool):
                        self.discard_card(p, c)
                    self.log(f"  貫石斧: {p.name} 棄兩張牌,這張殺仍然命中")
                    dodged = False
        if dodged:
            self.log(f"  {tgt.name} 閃避")
            p.char.on_sha_dodged(self, p, tgt)
            if p.has_weapon("青龍偃月刀") and p.alive and tgt.alive:  # 殺被閃: 可立即再對同一目標出一張殺
                shas = [c for c in p.hand if c.name == "殺"]
                c = p.agent.respond(self, p, "青龍追擊", shas, {"victim": tgt}) if shas else None
                if c:
                    self.discard_card(p, c, played=True)
                    self.log(f"  青龍偃月刀: {p.name} 再對 {tgt.name} 出一張殺")
                    self.use_sha(p, tgt, c, count=False)
            return
        self.last_dealt = 0
        if p.has_weapon("寒冰劍") and tgt.alive and self.takeable(tgt):  # 可不造成傷害,改棄掉對方兩張牌
            self.cur_sha_target = tgt
            if p.agent.choose_skill(self, p, "寒冰劍-棄牌"):
                self.log(f"  寒冰劍: 不造成傷害,改棄掉 {tgt.name} 兩張牌")
                eqs = [] if tgt.char.equip_safe else tgt.equip_cards()
                if tgt.hand and eqs:   # 對方手牌和裝備都有: 一張裝備 (自己選) + 一張手牌 (看不到,隨機)
                    e = p.agent.choose_from(self, p, tgt, eqs)
                    if e not in eqs:
                        e = self.rng.choice(eqs)
                    h = self.rng.choice(tgt.hand)
                    for c in (e, h):
                        self.discard_card(tgt, c)
                        self.log(f"  {p.name} 棄置 {tgt.name} 的 {c}")
                    return
                for _ in range(2):   # 只有手牌或只有裝備: 照一般方式棄兩張
                    if not self.takeable(tgt):
                        break
                    c = self.pick_card(p, tgt)
                    self.discard_card(tgt, c)
                    self.log(f"  {p.name} 棄置 {tgt.name} 的 {c}")
                return
        self.damage(p, tgt, dmg, via_sha=True, nature=nature)
        if self.last_dealt > 0:
            p.char.on_sha_hit(self, p, tgt, self.last_dealt)

    # ---------- 出牌選項 ----------
    def play_options(self, p):
        opts = []
        alive_others = self.others(p)
        lim = p.char.sha_limit(self, p)
        can_sha = lim is None or (lim > 0 and (p.has_weapon("諸葛連弩") or self.sha_used < lim))
        reach = [t for t in alive_others if p.char.no_range(self, p) or self.distance(p, t) <= p.attack_range()]
        reach = p.char.sha_targets(self, p, reach)
        cards = []
        for hc in p.hand:
            cards.append(hc)
            for vn in p.char.views(self, p, hc):
                cards.append(ViewCard(vn, hc.color, "basic" if vn in BASIC_NAMES else "armor" if vn in ("八卦陣", "仁王盾") else "trick", hc, id=hc.id if vn in ("八卦陣", "仁王盾") else -1))   # 張遼: 紅牌當八卦陣 / 黑牌當仁王盾 (裝備)
        for c in cards:
            n = c.name
            if n == "殺":
                if can_sha:
                    opts += [(c, t) for t in reach]
                    if p.has_weapon("方天畫戟") and len(p.hand) == 1:  # 最後一張手牌: 可攻擊最多 3 名範圍內的玩家
                        near = [t for t in sorted(reach, key=lambda t: self.distance(p, t))
                                if not t.char.blocks_target(self, t, c) and not (self.jiu and t.char.no_jiu_target)][:6]
                        if len(near) >= 2:
                            opts += [(c, combo) for combo in itertools.combinations(near, min(3, len(near)))]
            elif n == "桃":
                if p.hp < p.maxhp:
                    opts.append((c, None))
            elif n == "酒":
                if not self.jiu:
                    opts.append((c, None))
                if p.char.jiu_self_heal(self, p) and p.hp < p.maxhp:
                    opts.append((c, "heal"))
            elif n == "順":
                opts += [(c, t) for t in alive_others
                         if (p.char.no_range(self, p) or self.distance(p, t) <= p.attack_range()) and self.takeable(t)]
            elif n == "過":
                opts += [(c, t) for t in alive_others if self.takeable(t)]
            elif n in ("決", "火攻", "拋", "鴻", "笑"):
                for t in alive_others:
                    if n == "火攻" and not t.hand:
                        continue
                    if n == "笑" and len(p.hand) < 2:
                        continue
                    if n == "拋" and not t.all_cards():
                        continue
                    opts.append((c, t))
            elif n in ("南", "萬", "無", "增", "突", "飢", "五", "未", "發", "鐵", "孤"):
                opts.append((c, None))
            elif n == "桃園":
                if any(q.hp < q.maxhp for q in self.alive_players()):
                    opts.append((c, None))
            elif n in DELAYED:
                if n in SELF_DELAYED:  # 閃電: 只能放自己
                    if not any(j.name == n for j in p.judge):
                        opts.append((c, None))
                else:  # 樂/兵/毒: 自己或別人;草 (草木皆兵): 只能對其他角色
                    opts += [(c, t) for t in (alive_others if n == "草" else self.alive_players()) if not any(j.name == n for j in t.judge)]
            elif n == "投":
                if p.char.tao_self_only:
                    if p.hp < p.maxhp:
                        opts += [(c, t) for t in alive_others]
                else:
                    opts += [(c, t) for t in alive_others if t.hp < t.maxhp]
            elif n == "借":
                for t in alive_others:
                    if t.equip["weapon"] or t.equip["weapon2"]:
                        for v in self.others(t):
                            if self.distance(t, v) <= t.attack_range():
                                opts.append((c, (t, v)))
            elif n == "轉":
                opts += [(c, t) for t in alive_others if (t.equip_cards() or p.equip_cards())]   # 武器 / 防具 / 坐騎 任一方有裝備就能換
            elif n in ("強", "弱"):
                if n not in self.banned():
                    opts += [(c, t) for t in self.alive_players()]
            elif n == "降雷":
                opts += [(c, t) for t in self.alive_players()]
            elif n == "漁":   # 每個回合自己最多出一張
                if getattr(p, "_eye_turn", None) != self.turn_id:
                    opts += [(c, t) for t in alive_others]
            elif n == "偽":
                opts.append((c, None))   # 同一回合可以偽裝多次 (每次換成另一位)
            elif n == "聲":
                if len(p.hand) >= 2:
                    for a in alive_others:
                        for b in self.alive_players():
                            if b is not a:
                                opts.append((c, (a, b)))
            elif n == "出":
                for owner in self.alive_players():
                    for d in owner.judge:
                        for dest in self.alive_players():
                            if dest is not owner and not any(j.name == d.name for j in dest.judge):
                                opts.append((c, (owner, d, dest)))
            elif c.kind in ("weapon", "armor", "horse"):
                opts.append((c, None))
        if can_sha and p.has_weapon("丈八蛇矛") and len(p.hand) >= 2:
            opts += [(SkillAct("丈八蛇矛-雙牌當殺", self._zhangba), t) for t in reach]
        opts += p.char.skill_options(self, p)
        opts = [o for o in opts if self.target_ok(p, o) and not p.char.blocks_card(self, p, o[0])
                and not (getattr(o[0], "kind", "") == "trick" and self.trick_locked(p))]   # 鐘繇沒手牌: 別人不能用錦囊牌
        if not any(getattr(o[0], "name", "") == "殺" and isinstance(o[1], Player) for o in opts):   # 酒不能平常單獨打出: 要有能打出的殺才能喝
            opts = [o for o in opts if not (getattr(o[0], "name", "") == "酒" and o[1] is None)]
        if self.aura("one_card") and not hasattr(p.agent, "respond_race") and self.tricks_this_turn(p) >= 1:   # 曹沖: 電腦不會自己多出錦囊來扣血
            opts = [o for o in opts if isinstance(o[0], SkillAct) or getattr(getattr(o[0], "orig", o[0]), "kind", "") != "trick"]
        return opts

    def _eye_watch(self, p):
        """p 使用了一張錦囊 (曹沖同一套算法: 重鑄不算): 盯著 p 的坐收漁利,擁有者抽 1 張。"""
        for e in list(self.eyes):
            if e["turn"] != self.turn_id:
                self.eyes.remove(e)
            elif e["tgt"] is p and e["owner"].alive:
                self.log(f"  坐收漁利: {p.name} 使用錦囊,{e['owner'].name} 抽 1 張")
                self.draw(e["owner"], 1)

    def _eye_start(self, owner, tgt):
        """坐收漁利生效: 這條連鎖上排在前面、目標已經使用的錦囊也算,先補抽;之後到回合結束前每用一張再抽 1 張。"""
        if not owner.alive or not tgt.alive:
            return
        recast = self.__dict__.get("_recast_ids", ())
        n = sum(1 for c, who in self.chain_view
                if who == tgt.idx and not isinstance(c, (tuple, dict)) and getattr(c, "kind", "") == "trick" and id(c) not in recast)
        self.eyes.append({"owner": owner, "tgt": tgt, "turn": self.turn_id})
        self.log(f"  坐收漁利: {tgt.name} 到這個回合結束前,每使用一張錦囊 {owner.name} 就抽 1 張" + (f";這條連鎖上他已經用了 {n} 張,先抽 {n} 張" if n else ""))
        if n:
            self.draw(owner, n)

    def tricks_this_turn(self, p):
        tk = getattr(p, "_trk", None)
        return tk[1] if tk and tk[0] == self.turn_id else 0

    def _zhangba(self, g, p, t):
        """丈八蛇矛: 兩張手牌當一張殺使用。"""
        if len(p.hand) < 2:   # 技能發動前被連鎖的 ⚡ 打掉了手牌
            self.log(f"  {p.name} 手牌不足,丈八蛇矛無法發動")
            return
        cs = p.agent.choose_discard(self, p, 2, list(p.hand))
        for c in cs:
            p.hand.remove(c)
            self.discard.append(c)
        view = ViewCard("殺", "", "basic", cs[0])   # 兩張牌合成的殺無色 (仁王盾擋不住)
        self.log(f"  丈八蛇矛: {cs[0]} + {cs[1]} 當作殺")
        self.cur_card, self.cur_user = view, p
        self.use_sha(p, t, view)

    def after_play(self, p, card):
        if self.__dict__.get("_last_recast") is card:   # 鐵索連環重鑄: 不算使用錦囊
            self._last_recast = None
            return
        real = getattr(card, "orig", card)
        if isinstance(card, ViewCard) and card.kind == "trick":   # 手牌當錦囊 (陳群 4 血當突襲…): 算錦囊牌,曹沖 / 鄧艾等「有人使用錦囊」的技能要觸發
            real = card
        if real.kind == "trick":
            for q in self.alive_players():
                q.char.on_any_trick(self, q, p, real)
            for q in self.others(p):
                q.char.on_other_trick(self, q, p, real)
        elif real.kind == "basic":
            for q in self.others(p):
                q.char.on_other_basic(self, q, p, real)

    def takeable(self, t):
        """順/過 可以拿或棄的牌 (徐晃的裝備不會被拿)。"""
        return t.hand + ([] if t.char.equip_safe else t.equip_cards())

    def target_ok(self, p, o):
        card, tgt = o
        if isinstance(card, SkillAct):
            return True
        if card.name in DELAYED and isinstance(tgt, Player) and card.name in tgt.char.immune_names:
            return False
        if card.name == "閃電" and tgt is None and card.name in p.char.immune_names:
            return False
        if card.name in DELAYED:
            if card.name in SELF_DELAYED and tgt is None:
                return not p.char.immune_delayed
            if isinstance(tgt, Player) and tgt.char.immune_delayed:
                return False
        if card.name == "出" and (tgt[2].char.immune_delayed or "出" in tgt[2].char.block_names):
            return False
        if isinstance(tgt, tuple) and card.name in ("聲", "借", "轉"):   # 兩個對象的錦囊: 關興這類「不能成為錦囊對象」的人,不能被指定 (聲: 兩個人都算;借 / 轉: 第一個人)
            for t in (tgt[:2] if card.name == "聲" else tgt[:1]):
                if isinstance(t, Player) and t is not p and t.char.blocks_target(self, t, card):
                    return False
        if card.name in ("借", "轉"):
            t = tgt[0] if isinstance(tgt, tuple) else tgt
            if t.char.equip_safe:
                return False
        if card.name == "殺" and self.jiu and isinstance(tgt, Player) and tgt.char.no_jiu_target:
            return False
        if card.kind == "armor" and p.char.no_armor:
            return False
        if isinstance(tgt, Player) and tgt is not p and tgt.char.blocks_target(self, tgt, card):
            return False
        return True

    def targeted(self, user, tgt, card):
        tgt.char.on_targeted(self, tgt, user, card)

    # ---------- 執行 ----------
    def group_effect(self, p, trick, need, order):
        """南/萬/突/飢: 其他玩家各出 need,否則 -1 點體力。"""
        self.log(f"{p.name} 使用 {trick}")
        self.in_group = True
        valid = []
        for q in order:
            if not q.alive:
                continue
            if trick in ("南", "萬", "飢") and q.has_armor("藤甲"):   # 藤甲: 南蠻入侵 / 萬箭齊發 / 飢餓 對你無效
                self.log(f"  藤甲: {q.name} 不受{ {'南': '南蠻入侵', '萬': '萬箭齊發', '飢': '飢餓'}[trick] }影響")
                continue
            if q.char.blocks_target(self, q, self.cur_card) if getattr(self, "cur_card", None) else False:
                self.log(f"  {q.name} 不會成為此錦囊的目標")
                continue
            valid.append(q)
        # 全體錦囊只能被無懈一次,擋下後所有人都不用響應
        if valid and self.wuxie_contest(p, None, trick, True, targets=valid):
            self.log(f"  {trick} 被無懈擋下,對所有人無效")
            self.in_group = False
            return
        cc = getattr(self, "cur_card", None)
        if cc is not None and cc.kind == "trick":
            for q in valid:   # 全體錦囊也算「被指定為目標」 (孫堅等)
                if q is not p and q.alive and p.alive:
                    self.targeted(p, q, cc)
        from types import SimpleNamespace
        if trick != "突":
            for q in valid:   # 每位被指定的人先有機會接連鎖用 ⚡弱 / 降雷 (例如替自己弱化飢餓的傷害)
                if q.alive and p.alive and not (cc is not None and (id(cc), q.idx) in self._chain_asked):   # 「全部都問」模式出牌時已經問過他了,不用再問第二次
                    self.sha_window(p, q, SimpleNamespace(name=trick), "使用了" + {"南": "南蠻入侵", "萬": "萬箭齊發", "突": "突襲"}.get(trick, trick))
        done = False
        cyc = valid + [p] if trick == "突" and valid else valid   # 突襲: 別人依序出殺,最後輪到出牌者自己也要出
        for _ in range(40 if trick == "突" else 1):   # 突襲: 都出了殺就再繞一圈,直到有人沒出而受傷
            for q in cyc:
                if not q.alive or not p.alive:
                    continue
                if trick == "突":   # 突襲: 有人受傷結算就停止,所以輪到這個人才問他 (後面沒輪到的人不會被問)
                    self.sha_window(p, q, SimpleNamespace(name=trick), "使用了" + {"南": "南蠻入侵", "萬": "萬箭齊發", "突": "突襲"}.get(trick, trick) + " (結算到你了)")
                    if not q.alive or not p.alive:
                        continue
                if not self.need_response(q, need, {"attacker": p, "group": trick}):
                    self.damage(p, q, p.char.group_damage(self, p, trick))
                    if trick == "突":
                        done = True
                        break   # 突襲: 有人沒出殺受到傷害,結算就停止
            if done or not p.alive or not any(q.alive for q in valid):
                break
        self.in_group = False

    def _fx_hint(self, p, card, tgt):
        """隱藏行 (控制字元 \x01 開頭,前端不顯示): 出牌者 | 目標座位 (-1=場中央) | 種類 (eq=裝備牌)。"""
        t = tgt if isinstance(tgt, (tuple, list)) else [tgt]
        t = next((x for x in t if isinstance(x, Player) and x is not p), None)
        if card.kind in ("weapon", "armor", "horse"):
            kind = "eq"
        elif card.name in DELAYED and card.name in SELF_DELAYED:
            kind, t = "self", None
        else:
            kind = ""
        return f"\x01FX|{p.idx}|{t.idx if t else -1}|{kind}"

    def execute(self, p, card, tgt, _repeat=False):
        """打出一張牌 / 技能。最外層的結算開始時清掉連鎖演示,連鎖內的回應 (巢狀 execute) 才會接在後面。"""
        if self.exec_depth == 0:
            self.clear_chain_view()
            self._chain_asked = set()
            self._flip_snap = {q.idx: q.flipped for q in self.players}   # 連鎖開始時誰是正面: 整條連鎖處理完才看最後有沒有翻面
        self.exec_depth += 1
        try:
            return self._execute(p, card, tgt, _repeat)
        finally:
            self.exec_depth -= 1
            if self.exec_depth == 0:
                snap, self._flip_snap = getattr(self, "_flip_snap", None) or {}, None
                for q in self.alive_players():
                    if q.flipped and snap.get(q.idx) is False:   # 連鎖處理完是背面 (偶數個降雷會翻回正面,就不會有事): 標記全部消失
                        q._char.lose_marks(self, q)

    def _spend(self, p, real):
        """使用的牌離開手牌進棄牌堆; 若這張牌在結算途中已被交給別人 / 棄掉 (例如曹沖交換武將後的技能), 就不重複處理。"""
        if real in p.hand:
            p.hand.remove(real)
            self.discard.append(real)

    def _execute(self, p, card, tgt, _repeat=False):
        n = card.name
        ann = self.__dict__.pop("_announced", False)   # 連鎖視窗已經寫過這張牌的連鎖行: 不重開連鎖、不重複寫
        if not ann:
            self.new_chain()
        if getattr(card, "kind", "") not in ("weapon", "armor", "horse") and card.name not in DELAYED and not _repeat:   # 只有需要效果處理的牌進連鎖 (裝備、延時錦囊放下去時不算)
            self.chain_view.append((card, p.idx))
        if not isinstance(card, SkillAct):
            self.log(self._fx_hint(p, card, tgt))   # 給前端動畫用的隱藏行: 牌飛向誰
        vs = [tgt] if isinstance(tgt, Player) else [x for x in tgt if isinstance(x, Player)] if isinstance(tgt, (tuple, list)) else []
        vs = [x for x in vs if x is not p]
        at = f"對 {'、'.join(x.name for x in vs)} " if vs and not isinstance(card, SkillAct) and card.kind in ("basic", "trick") else ""   # 先寫出對象,別人才知道要不要接連鎖 / 出無懈
        if not ann:
            self.link(f"{p.name} {at}使用 {card}")
        if isinstance(card, SkillAct):
            self.cur_card = self.cur_user = None   # 不要沿用上一張牌 (否則響應提示會寫成上一張牌的名字)
            if isinstance(tgt, Player) and tgt is not p:   # 武將技能指定到的人,也能接連鎖用 ⚡弱 / 降雷
                if self.sha_window(p, tgt, card):
                    self.log(f"  呂布「無效」: {card.name} 沒有效果")
                    return
                if not (p.alive and tgt.alive):
                    return
            card.run(self, p, tgt)
            return
        self.cur_card = card
        self.cur_user = p
        real = getattr(card, "orig", card)
        vtrick = isinstance(card, ViewCard) and card.kind == "trick"   # 手牌當錦囊使用: 也算一張錦囊 (曹沖: 超過一張扣血)
        recast = False
        if n == "鐵":   # 先問橫置還是重鑄: 重鑄不算使用錦囊 (曹沖計數 / 有人使用錦囊的技能都不觸發)
            self._tie_mode = p.agent.choose_option(self, p, "鐵索連環", ["橫置 / 重置 最多兩名角色", "重鑄 (棄掉這張,再抽 1 張)"])
            if self._tie_mode != 1:
                self._tie_targets = p.agent.choose_chain(self, p)
                if not self._tie_targets:   # 選了橫置卻沒選對象: 視為重鑄
                    self._tie_mode = 1
            recast = self._tie_mode == 1
        d =self.stats["cards_played"]
        d[n] = d.get(n, 0) + 1
        p.played += 1
        if n == "偽":
            p.wei_n += 1
        for q in list(self.alive_players()):
            q.char.on_card_used(self, q, p, card)
        if (real.kind == "trick" or vtrick) and not recast:
            p.turn_flags["tricks"] = p.turn_flags.get("tricks", 0) + 1
            tk = getattr(p, "_trk", None)
            if tk is None or tk[0] != self.turn_id:
                tk = p._trk = [self.turn_id, 0]
            tk[1] += 1
            self._eye_watch(p)   # 坐收漁利: 被盯上的人使用錦囊,盯他的人抽牌
            if tk[1] > 1 and self.aura("one_card"):   # 曹沖: 一回合只能用 1 張錦囊,每超過一張 -1 點體力
                cc = next((q for q in self.alive_players() if q.char.one_card), None)
                self.log(f"  {cc.name if cc else ''}[曹沖] {p.name} 這回合第 {tk[1]} 張錦囊,超過 1 張,扣 1 點體力 (可閃)")
                if not (p.alive and self.need_response(p, "閃", {"attacker": cc, "cao_n": tk[1]})):
                    self.damage(cc, p, 1, _bonus=False, _mods=False)   # 來源是曹沖 (場上有曹沖技能的人),只標來源,不吃武器 / 強弱加成
        if real is not card:
            p.char.on_view_used(self, p, card)
        if isinstance(tgt, Player) and tgt is not p and tgt.alive and card.kind in ("basic", "trick"):
            self.targeted(p, tgt, card)
        if isinstance(tgt, Player) and tgt is not p:
            if n in HARM_CARDS:
                self.emit("attack", p, tgt)
            elif n in HELP_CARDS:
                self.emit("help", p, tgt)
        self.chain_all_window(p, card, tgt)
        if not p.alive and real not in p.hand and not _repeat:   # 打出這張牌的人在途中死了 (例如曹沖: 超過一張錦囊扣血扣死),手牌已經被棄光
            return
        if n == "殺":
            self._spend(p, real)
            if isinstance(tgt, tuple):  # 方天畫戟: 同時攻擊最多 3 人
                self.log(f"  方天畫戟: 同時攻擊 " + "、".join(t.name for t in tgt))
                for k, t in enumerate(tgt):
                    if t.alive and p.alive:
                        self.targeted(p, t, card)
                        self.emit("attack", p, t)
                        self.use_sha(p, t, card, count=(k == 0))
            else:
                self.use_sha(p, tgt, card)
            return
        if self.void and card.kind == "trick" and n not in DELAYED:
            self._spend(p, real)
            self.log(f"  呂布「無效」: {card} 沒有效果")
            return
        if card.kind in ("weapon", "armor", "horse"):
            self.equip_card(p, card)
            return
        if n in DELAYED:
            if real in p.hand:
                p.hand.remove(real)
            owner = p if n in SELF_DELAYED else tgt
            card.placed_by = p
            owner.judge.append(card)
            self.log(f"{p.name} 將 {card} 放入 {owner.name} 的判定區")
            if n == "樂":
                for q in self.alive_players():
                    q.char.on_le_placed(self, q, owner)
            return
        if not _repeat:
            self._spend(p, real)
        if card.kind == "trick" and isinstance(tgt, Player) and tgt is not p and n not in ("降雷", "強", "弱", "無懈", "漁"):
            if self.sha_window(p, tgt, card) and card.kind == "trick":   # 被指定的錦囊: 目標也能接連鎖使用 ⚡ (呂布發動無效 → 這張沒有效果)
                self.log(f"  呂布「無效」: {card} 沒有效果")
                return
            if not (p.alive and tgt.alive):
                return
        if n == "桃":
            self.heal(p, p.char.peach_heal(self, p))
            self.log(f"{p.name} 使用桃 -> 體力 {p.hp}")
        elif n == "酒" and tgt == "heal":
            self.heal(p, p.char.jiu_self_heal(self, p))
            self.log(f"{p.name} 使用酒回血 -> 體力 {p.hp}")
        elif n == "酒":
            self.jiu = True
            self.log(f"{p.name} 使用酒 (下一張殺傷害+1)")
        elif n == "無":
            self.log(f"{p.name} 使用 無")
            if not self.wuxie_contest(p, p, "無", False):
                self.draw(p, 2)
                for q in self.others(p):
                    q.char.on_other_wu(self, q, p)
        elif n == "桃園":
            self.log(f"{p.name} 使用 桃園")
            for q in self.order_from(p):
                if q.hp < q.maxhp and not self.wuxie_contest(p, q, "桃園", False):
                    self.heal(q)
        elif n in ("南", "萬"):
            self.group_effect(p, n, "殺" if n == "南" else "閃", self.others(p))
        elif n == "飢":
            self.group_effect(p, n, "桃", self.others(p))
        elif n == "突":
            self.group_effect(p, n, "殺", self.side_order(p, self.pick_side(p)))
        elif n == "順":
            self.log(f"{p.name} 對 {tgt.name} 使用 順")
            if not self.wuxie_contest(p, tgt, "順", True) and tgt.all_cards():
                c = self.pick_card(p, tgt)
                self.remove_from(tgt, c)
                p.hand.append(getattr(c, "orig", c))   # 對方的裝備可能是手牌當的 (張遼)
                self.log(f"  {p.name} 取得 {tgt.name} 的一張牌")
        elif n == "過":
            self.log(f"{p.name} 對 {tgt.name} 使用 過")
            if not self.wuxie_contest(p, tgt, "過", True) and tgt.all_cards():
                c = self.pick_card(p, tgt)
                self.discard_card(tgt, c)   # 走一般的捨棄流程: 袁術的牌被拆掉要觸發技能
                self.log(f"  {p.name} 棄置 {tgt.name} 的 {c}")
        elif n == "決":
            self.log(f"{p.name} 對 {tgt.name} 使用 決")
            if not self.wuxie_contest(p, tgt, "決", True):
                a, b = tgt, p
                while True:
                    if not self.need_response(a, "殺", {"duel_with": b}):
                        self.damage(b, a, 1)
                        break
                    a, b = b, a
        elif n == "火攻":
            self.log(f"{p.name} 對 {tgt.name} 使用 火攻")
            if not self.wuxie_contest(p, tgt, "火攻", True) and tgt.hand:
                shown = tgt.agent.show_card(self, tgt, list(tgt.hand))
                self.log(f"  {tgt.name} 展示 {shown}")
                self.last_reveal = ("火攻", [(tgt.idx, shown)])   # 桌面中央讓大家看到展示的牌
                same = [c for c in p.hand if c.color == shown.color]
                if same:
                    c = p.agent.respond(self, p, "火攻", same, {"target": tgt})
                    if c:
                        self.discard_card(p, c)
                        self.log(f"  {p.name} 棄置 {c}")
                        self.damage(p, tgt, 1, nature="火")
        elif n == "增":
            self.log(f"{p.name} 使用 增")
            if not self.wuxie_contest(p, p, "增", False):
                drawn = self.draw(p, 3)
                nonbasic = [c for c in drawn if c.kind != "basic"]
                pool, k = (nonbasic, 1) if nonbasic else (drawn, min(2, len(drawn)))
                for c in p.agent.choose_discard(self, p, k, pool):
                    self.discard_card(p, c)
        elif n == "拋":
            self.log(f"{p.name} 對 {tgt.name} 使用 拋")
            if not self.wuxie_contest(p, tgt, "拋", True) and tgt.all_cards():
                c = tgt.agent.choose_discard(self, tgt, 1, tgt.all_cards())[0]
                self.discard_card(tgt, c)
                self.log(f"  {tgt.name} 棄置 {c}")
                self.draw(p, 1)
        elif n == "笑":
            self.log(f"{p.name} 對 {tgt.name} 使用 笑")
            give = p.agent.choose_discard(self, p, 1, list(p.hand), msg=f"選擇要給 {tgt.name} 的 1 張手牌")[0] if p.hand else None   # 先選好要給的牌,才問別人要不要出無懈
            if not self.wuxie_contest(p, tgt, "笑", True) and give in p.hand:   # 無懈 / 其他效果之後那張牌可能已經不在手上
                p.hand.remove(give)
                tgt.hand.append(give)
                if not self.need_response(tgt, "閃", {"attacker": p}):
                    self.damage(p, tgt, 1)
        elif n == "鴻":
            self.log(f"{p.name} 對 {tgt.name} 使用 鴻")
            if not self.wuxie_contest(p, tgt, "鴻", True):
                c1, c2 = self.pop_deck(), self.pop_deck()
                self.log(f"  {p.name} 亮出 {c1} / {tgt.name} 亮出 {c2}")
                self.last_reveal = ("鴻門宴", [(p.idx, c1), (tgt.idx, c2)])
                if c1 and c2 and c1.color == c2.color:
                    self.log(f"  同色 ({c1.color}): 兩張都棄掉,{tgt.name} 受到 1 點傷害")
                    self.discard.extend([c1, c2])
                    self.damage(p, tgt, 1)
                else:
                    self.log("  不同色: 各自拿走亮出的牌")
                    if c1:
                        p.hand.append(c1)
                    if c2:
                        tgt.hand.append(c2)
        elif n == "投":
            self.log(f"{p.name} 對 {tgt.name} 使用 投")
            if not self.wuxie_contest(p, tgt, "投", False):
                self.draw(p, 1)
                if not p.char.tao_no_heal:
                    self.heal(p if p.char.tao_self_only else tgt)
        elif n == "五":
            self.log(f"{p.name} 使用 五穀豐登")
            if not self.wuxie_contest(p, p, "五", False):
                pile = [c for c in (self.pop_deck() for _ in self.alive_players()) if c]
                for q in self.order_from(p):
                    for _ in range(q.char.wu_picks):
                        if not pile:
                            break
                        c = pile[0] if len(pile) == 1 else q.agent.pick_pile(self, q, pile)   # 最後一張不用選,直接拿
                        pile.remove(c)
                        q.hand.append(c)
        elif n == "降雷":
            self._thunder_body(p, tgt)
        elif n == "漁":
            p._eye_turn = self.turn_id   # 被無懈也算出過了
            self.log(f"{p.name} 對 {tgt.name} 使用 坐收漁利")
            if not self.wuxie_contest(p, tgt, "漁", True):
                self._eye_start(p, tgt)
        elif n == "偽":
            self.log(f"{p.name} 使用 偽裝")
            if not self.wuxie_contest(p, p, "偽", False):
                self.disguise(p)
        elif n == "未":
            self.log(f"{p.name} 使用 未雨綢繆")
            if not self.wuxie_contest(p, p, "未", False):
                p.stash.extend(c for c in (self.pop_deck(), self.pop_deck()) if c)
        elif n == "發":
            self.log(f"{p.name} 使用 發憤圖強")
            if not self.wuxie_contest(p, p, "發", False):
                x = max(1, min(p.char.max_fa(self, p), p.agent.choose_x(self, p)))
                self.draw(p, x)
                if not p.char.fa_free(self, p) and not p.char.blocks_target(self, p, card):   # 曹丕: 黑色錦囊對自己無效,不用付代價
                    p.fa_debt.append(x)
        elif n == "借":
            t, v = tgt
            self.log(f"{p.name} 對 {t.name} 使用 借, 目標 {v.name}")
            if not self.wuxie_contest(p, t, "借", True) and (t.equip["weapon"] or t.equip["weapon2"]):
                shas = [c for c in t.hand if c.name == "殺"]
                c = t.agent.respond(self, t, "借刀殺人", shas, {"victim": v, "lender": p}) if shas else None
                if c and v.alive:
                    self.discard_card(t, c, played=True)
                    self.use_sha(t, v, c, count=False)
                else:
                    ws = "weapon" if t.equip["weapon"] else "weapon2"
                    w = t.equip[ws]
                    t.equip[ws] = None
                    p.hand.append(w)
                    self.log(f"  {p.name} 取得 {t.name} 的 {w}")
        elif n == "轉":
            self.log(f"{p.name} 對 {tgt.name} 使用 轉")
            if not self.wuxie_contest(p, tgt, "轉", True):
                for slot in ("weapon", "armor", "weapon2", "armor2", "h+", "h-"):
                    p.equip[slot], tgt.equip[slot] = tgt.equip[slot], p.equip[slot]
                for q in (p, tgt):
                    self.fix_equip(q)
        elif n in ("強", "弱"):
            self.log(f"{p.name} 對 {tgt.name} 使用 {n}")
            if not self.wuxie_contest(p, tgt, n, n == "弱" and tgt is not p):
                if n == "強":
                    tgt.dmg_x2 += 1
                else:
                    tgt.dmg_half += 1
        elif n == "聲":
            a, b = tgt
            self.log(f"{p.name} 使用 聲, {a.name} -> {b.name}")
            if not self.wuxie_contest(p, a, "聲", False):
                give = p.agent.choose_discard(self, p, 1, list(p.hand), msg=f"選擇要給 {a.name} 的 1 張手牌")[0]
                p.hand.remove(give)
                a.hand.append(give)
                if a.hand:
                    two = a.agent.choose_discard(self, a, min(2, len(a.hand)), list(a.hand), msg=f"選擇要給 {b.name} 的 {min(2, len(a.hand))} 張手牌")
                    for c in two:
                        a.hand.remove(c)
                        b.hand.append(c)
        elif n == "出":
            owner, d_card, dest = tgt
            self.log(f"{p.name} 使用 出: {d_card} 從 {owner.name} 移到 {dest.name}")
            if not self.wuxie_contest(p, dest, "出", False) and d_card in owner.judge:
                owner.judge.remove(d_card)
                dest.judge.append(d_card)
        elif n == "孤":
            self.log(f"{p.name} 使用 孤注一擲")
            if not self.wuxie_contest(p, p, "孤", False):
                j = self.flip_judge(p)
                N = max(p.hp, 0)  # N = 手牌上限 = 當前體力
                self.log(f"  孤注一擲判定 {j} (N={N})")
                if j.kind != "trick":
                    for c in list(p.hand):
                        self.discard_card(p, c)
                    self.heal(p, N)
                    self.log(f"  棄置所有手牌,回復至 體力 {p.hp}")
                else:
                    self.draw(p, N)
                    self.log(f"  抽 {N} 張" + ("" if p.char.gu_no_loss else ",-1 點體力"))
                    if not p.char.gu_no_loss:
                        self.damage(None, p, 1)
        elif n == "鐵":
            mode = self.__dict__.pop("_tie_mode", None)
            if mode is None:
                mode = p.agent.choose_option(self, p, "鐵索連環", ["橫置 / 重置 最多兩名角色", "重鑄 (棄掉這張,再抽 1 張)"])
            if mode == 1:   # 重鑄: 不算使用,不能被無懈
                self.__dict__.pop("_tie_targets", None)
                self.__dict__.setdefault("_recast_ids", set()).add(id(card))
                self._last_recast = card   # after_play 看到這張就不觸發「有人使用錦囊」
                self.log(f"{p.name} 重鑄 鐵索連環")
                self.draw(p, 1 + p.char.tie_extra)
                self.log("  重鑄: 抽1張")
            else:
                self.log(f"{p.name} 使用 鐵索連環")
            if mode != 1 and not self.wuxie_contest(p, p, "鐵", False):
                targets = self.__dict__.pop("_tie_targets", None)
                if targets is None:
                    targets = p.agent.choose_chain(self, p)
                if not targets:
                    self.draw(p, 1 + p.char.tie_extra)
                    self.log("  沒有選擇對象: 改為重鑄,抽1張")
                else:
                    for q in targets[:2]:
                        q.chained = not q.chained
                        q.chain_by = p.idx if q.chained else None
                        q.chain_turn = self.turn_id   # 橫置最多維持到這個回合結束
                        self.log(f"  {q.name} {'橫置' if q.chained else '重置'}")

    def disguise(self, p):
        """偽裝: 變成另一位沒有人使用的武將一回合。"""
        from characters import ROSTER
        taken = {q._char.name for q in self.players} | {x.name for q in self.players for x in q.disguise}
        pool = [nm for nm in ROSTER if nm not in taken]
        if not pool:
            self.log("  沒有可偽裝的武將")
            return
        i = p.agent.choose_option(self, p, "偽裝", pool)
        name = pool[i if isinstance(i, int) and 0 <= i < len(pool) else 0]
        inst = self.wei_chars.setdefault(name, ROSTER[name]())
        if p.flipped or p.dg_flip:   # 被翻面後再偽裝: 新偽裝的武將是正面 (技能可用),本尊仍是翻面
            self.log(f"  {p.name} 的新偽裝是正面,本尊仍維持翻面")
        who = p.name   # 偽裝前的名字 (偽裝後 p.name 會顯示成新武將,紀錄會變成「陳群 偽裝成 陳群」)
        p.disguise = [inst]
        p.dg_flip = False
        p.turn_flags["disguised"] = True
        p.turn_flags["disguise_n"] = p.turn_flags.get("disguise_n", 0) + 1
        self.log(f"  {who} 偽裝成 {name},獲得他的技能直到回合結束")
        self._wei_who = who
        for q in list(self.others(p)):
            q.char.on_other_wei(self, q, p, name)

    def pick_card(self, p, tgt):
        cands = (["HAND"] if tgt.hand else []) + ([] if tgt.char.equip_safe else tgt.equip_cards())
        pick = p.agent.choose_from(self, p, tgt, cands)
        if pick == "HAND" or pick not in tgt.equip_cards():
            return self.rng.choice(tgt.hand) if tgt.hand else self.rng.choice(tgt.equip_cards())
        return pick

    def fix_equip(self, q):
        """換裝後: 不能裝防具的武將 (典韋) 換到的防具馬上丟進棄牌堆;不能雙裝的武將,武器 / 防具各只能留一件,多的要選一件丟掉。"""
        if q.char.no_armor:
            for slot in ("armor", "armor2"):
                if q.equip[slot]:
                    self.log(f"  {q.name} 不能裝備防具,{q.equip[slot]} 直接丟進棄牌堆")
                    self.discard.append(getattr(q.equip[slot], "orig", q.equip[slot]))
                    q.equip[slot] = None
        for a, b, dual, kind in (("weapon", "weapon2", q.char.dual_weapon, "武器"), ("armor", "armor2", q.char.dual_armor, "防具")):
            if dual:
                continue
            if q.equip[a] and q.equip[b]:
                i = q.agent.choose_option(self, q, "留下哪一件" + kind, [f"留下 {q.equip[a]!r} (丟掉 {q.equip[b]!r})", f"留下 {q.equip[b]!r} (丟掉 {q.equip[a]!r})"])
                drop = b if i in (None, 0) else a
                self.log(f"  {q.name} 不能同時裝備兩件{kind},丟掉 {q.equip[drop]}")
                self.discard.append(getattr(q.equip[drop], "orig", q.equip[drop]))
                q.equip[drop] = None
            if not q.equip[a] and q.equip[b]:   # 只剩第二格: 移回第一格
                q.equip[a], q.equip[b] = q.equip[b], None

    def equip_card(self, p, card):
        slot = {"weapon": "weapon", "armor": "armor"}.get(card.kind)
        if card.kind == "horse":
            slot = "h+" if card.name == "+1馬" else "h-"
        if card.kind == "weapon" and p.char.dual_weapon and p.equip["weapon"] and not p.equip["weapon2"]:
            slot = "weapon2"
        elif card.kind == "armor" and p.char.dual_armor and p.equip["armor"] and not p.equip["armor2"]:
            slot = "armor2"
        elif card.kind in ("weapon", "armor") and (p.char.dual_weapon if card.kind == "weapon" else p.char.dual_armor):
            a, b = ("weapon", "weapon2") if card.kind == "weapon" else ("armor", "armor2")
            if p.equip[a] and p.equip[b]:   # 兩格都滿了: 問要換掉哪一件
                i = p.agent.choose_option(self, p, "換裝", [f"換掉 {p.equip[a]!r}", f"換掉 {p.equip[b]!r}"])
                slot = (a, b)[i if i in (0, 1) else 0]
        _o = getattr(card, "orig", card)
        if _o in p.hand:
            p.hand.remove(_o)
        elif card in p.hand:
            p.hand.remove(card)
        # 手牌當裝備 (張遼): 實際從手牌拿走的是原本那張
        old = p.equip[slot]
        if old:
            self.discard.append(getattr(old, "orig", old))
        p.equip[slot] = card
        self.log(f"{p.name} 裝備 {card}")
        for q in list(self.alive_players()):
            if q is not p:
                q.char.on_equipped(self, q, p, card)

    # ---------- 回合 ----------
    def judge_phase(self, p):
        """依序判定判定區 (先放先判)。回傳 (跳過出牌, 跳過抽牌)。"""
        skip_play = skip_draw = False
        for c in list(p.judge):
            if not p.alive:
                break
            if c not in p.judge:   # 前一張判定牌的效果 (翻面 / 受傷觸發的技能) 已把它移走
                continue
            p.judge.remove(c)
            self.cur_card = None
            self.new_chain()
            self.link(f"{p.name} 判定區 {_fn(c.name)} 生效")
            src = getattr(c, "placed_by", None)
            harmful = True
            if self.wuxie_contest(src, p, c.name, harmful):
                if c.name == "閃電":
                    self.pass_lightning(p, c)
                else:
                    self.discard.append(getattr(c, "orig", c))
                continue
            j = self.flip_judge(p)
            self.log(f"{p.name} 判定 {_fn(c.name)}: {j}")
            if c.name == "樂":
                if j.color != "紅":
                    skip_play = True
                    self.log("  樂不思蜀: 跳過出牌階段")
                self.discard.append(getattr(c, "orig", c))
            elif c.name == "兵":
                if j.color != "黑":
                    skip_draw = True
                    self.log("  兵糧寸斷: 跳過抽牌階段")
                self.discard.append(getattr(c, "orig", c))
            elif c.name == "毒":
                if j.color == "紅":
                    self.flip_char(p)
                self.discard.append(getattr(c, "orig", c))
            elif c.name == "草":
                if j.color != "黑":
                    p.cao += 1
                    self.log(f"  草木皆兵生效: {p.name} 這個摸牌階段少摸 1 張,摸牌階段結束時與他距離 1 的角色各摸 1 張")
                self.discard.append(getattr(c, "orig", c))
            elif c.name == "閃電":
                if j.color == "黑":
                    self.discard.append(getattr(c, "orig", c))
                    self._lt_dmg = True   # 閃電傷害: 華雄這類「打他的人」的技能,連放閃電的人自己 (閃電繞一圈回到自己) 也算
                    try:
                        self.damage(src if src is not None and src.alive else None, p, 3, nature="雷")   # 傷害來源是發動 (放下) 閃電的那個人,吃他的流星錘 +1 和強化 / 弱化
                    finally:
                        self._lt_dmg = False
                else:
                    self.pass_lightning(p, c)
        return skip_play, skip_draw

    def flip_char(self, p):
        """武將牌翻面: 翻面當下的觸發技能先發動,之後技能全部失效。"""
        if p.flipped:
            return
        if p.flip_char.no_flip:
            self.log(f"  {p.name} 的武將牌不會翻面")
            return
        self.log(f"  {p.name} 武將牌翻面一回合 (技能無法使用)")
        p.flip_char.on_flipped(self, p)
        p.flipped = True

    def pass_lightning(self, p, c):
        nxt = [q for q in self.others(p) if not q.char.immune_delayed and "閃電" not in q.char.immune_names]  # 魏延/典韋: 閃電跳過
        if nxt and not any(j.name == "閃電" for j in nxt[0].judge):
            nxt[0].judge.append(c)
            self.log(f"  閃電移交 {nxt[0].name}")
        else:
            p.judge.append(c)  # 下家已有閃電: 留在原處
            self.log("  閃電無法移動,留在原玩家判定區")

    def play_phase(self, p):
        jiu_must, jiu_ask = False, 0
        for _ in range(60):
            if not p.alive:
                return
            if p.turn_flags.get("skip_rest"):
                self.log(f"  {p.name} 的出牌階段被迫結束")
                break
            opts = self.play_options(p)
            all_opts = opts
            if jiu_must:   # 酒要跟殺一起出: 喝了酒就只能接著出殺 (不能只喝酒就結束)
                opts = [o for o in opts if getattr(o[0], "name", "") == "殺" and isinstance(o[1], (Player, tuple, list))]
                if not opts:
                    jiu_must, opts = False, all_opts
            if not opts:
                break
            self.clear_chain_view()
            i = p.agent.act(self, p, opts)
            if i is None:
                if jiu_must and hasattr(p.agent, "_ask") and jiu_ask < 50:   # 不能只喝酒不出殺: 一直問到出殺為止 (50 次只是防呆,免得斷線卡死)
                    jiu_ask += 1
                    continue
                if not jiu_must or hasattr(p.agent, "_ask"):
                    break
                i = 0   # 電腦喝了酒卻不想出殺: 就近挑第一張殺打出去 (真人才可以放棄)
            card, tgt = opts[i]
            if getattr(card, "name", "") == "殺":
                jiu_must = False
            elif getattr(card, "name", "") == "酒" and tgt is None:
                jiu_must, jiu_ask = True, 0
            self.execute(p, card, tgt)
            if (p.alive and p.char.single_to_all and isinstance(tgt, Player) and not isinstance(card, SkillAct)
                    and card.name in ("順", "過", "決", "火攻", "拋", "鴻", "笑", "投", "轉")):
                for q in self.others(p):
                    if q is not tgt and q.alive and p.alive and not (card.name == "笑" and not p.hand):
                        self.log(f"  [關興] 單一對象錦囊對 {q.name} 也有效")
                        self.execute(p, card, q, _repeat=True)
            self.after_play(p, card)
            self.check_hands()

    def offturn_window(self, cur, when):
        """別人回合中的技能時機 (回合開始 / 出牌階段結束後): 有可用的「別人回合也能發動」技能的玩家,
        會被問『要不要發動』。每人每個時機最多連續問 3 次。"""
        for q in self.order_from(cur)[1:]:
            for _ in range(3):
                if not q.alive or not cur.alive:
                    break
                opts = list(q.char.offturn_options(self, q))
                opts += [(c, t) for c, t in self.play_options(q)
                         if not isinstance(c, SkillAct) and c.name in ("轉", "強", "弱", "出", "降雷", "漁")]
                if not opts:
                    break
                i = q.agent.choose_offturn(self, q, opts, cur, when)
                if i is None:
                    break
                card, t = opts[i]
                if isinstance(card, SkillAct):
                    self.new_chain()
                    self.link(f"{q.name} 在 {cur.name} 的回合發動 {card!r}")
                    card.run(self, q, t)
                else:
                    self.log(f"{q.name} 在 {cur.name} 的回合使用 {card}")
                    self.execute(q, card, t)
                    self.after_play(q, card)

    def extra_play_phase(self, x):
        """別人給 x 的額外出牌階段 (馬良)。殺次數與酒獨立計算。"""
        saved = (self.sha_used, self.jiu, self.cur)
        self.sha_used, self.jiu, self.cur = 0, False, x
        self.log(f"  {x.name} 多一個出牌階段")
        self.play_phase(x)
        self.sha_used, self.jiu, self.cur = saved

    def swap_char(self, p):
        """百變模式: 回合最一開始,隨機換成一位沒人用的新武將 (已損失的體力維持不變)。"""
        from characters import ROSTER
        taken = {q._char.name for q in self.players} | {x.name for q in self.players for x in q.disguise}
        pool = [nm for nm in ROSTER if nm not in taken]
        if not pool:
            return
        nm = self.rng.choice(pool)
        old, new = p._char, ROSTER[nm]()
        missing = p.maxhp - p.hp
        p._char, p.borrow, p.borrow2, p.alias, p.disguise = new, [], [], [], []
        p.maxhp = max(1, new.maxhp + self.hp_offset) + (self.lord_bonus if p is self.lord else 0)
        p.hp = max(1, p.maxhp - missing)
        self.log(f"  🔀 {p.idx} 號位的武將從 {old.name} 換成 {nm} (體力 {p.hp}/{p.maxhp})")

    def take_turn(self, p):
        self.cur = p
        self.last_reveal = None   # 上一回合的亮牌 (鴻門宴 / 公孫淵) 不留到下一回合
        self.sha_used = 0
        self.jiu = False
        p.played = 0
        p.turn_flags = {}
        self.turn_id += 1
        self.cur_card = self.cur_user = None
        self.new_chain()
        for q in self.players:
            q.dmg_turn = 0
        if self.mode == "shuffle" and self.round >= 2:
            self.swap_char(p)
        self.log(f"--- 第{self.round}輪 {p.name} 回合 體力{p.hp} 手牌{len(p.hand)} ---")
        for q in self.players:   # 鐵索橫置最多一回合: 施放者的回合再度開始 (或施放者已死) 就自動重置
            if q.chained and q.alive and (getattr(q, "chain_by", None) == p.idx or not self.players[getattr(q, "chain_by", p.idx)].alive):
                q.chained = False
                self.log(f"  {q.name} 的鐵索橫置時間到,重置")
        if p.skip_turn:
            p.skip_turn = False
            self.log(f"{p.name} 的回合被跳過")
            return
        if p.stash:
            p.hand.extend(p.stash)
            self.log(f"{p.name} 取回未雨綢繆的 {len(p.stash)} 張牌")
            p.stash = []
        self.void = False
        p.char.on_turn_start(self, p)
        if not p.alive:
            return
        for q in list(self.alive_players()):
            if q is not p and q.alive:
                q.char.on_other_turn_start(self, q, p)
                if not p.alive:
                    return
        self.offturn_window(p, "回合開始")
        if not p.alive:
            return
        skip_play, skip_draw = self.judge_phase(p)
        if not p.alive:
            return
        skip_play = skip_play or p.skip_play_flag
        p.skip_play_flag = False
        if not skip_draw and not p.char.replace_draw(self, p):
            drawn = self.draw_phase(p, max(0, p.char.draw_count(self, p) - p.cao))
            if p.cao:   # 草木皆兵: 摸牌階段結束時,與他距離 1 的角色各摸一張
                for q in self.order_from(p)[1:]:
                    if q.alive and self.distance(p, q) <= 1:
                        self.draw(q, 1)
            for q in list(self.others(p)):
                q.char.on_other_draw(self, q, p)
            p.char.after_draw(self, p, drawn)
        p.cao = 0
        if not skip_play:
            self.play_phase(p)
        if not p.alive:
            return
        self.offturn_window(p, "出牌階段結束")
        if not p.alive:
            return
        while p.fa_debt:   # 每一張發憤圖強各問一次: 要少棄幾張
            debt = p.fa_debt.pop(0)
            pool = list(p.hand)   # 發憤圖強的棄牌只能棄手牌
            lo = max(0, debt - len(pool))   # 牌不夠時,至少要少棄這麼多張
            labels = [f"棄 {debt - m} 張" + (f",其餘 {m} 張不棄 (扣 {self.dmg_preview(p, m, tgt=p)} 點體力)" if m else "") for m in range(lo, debt + 1)]   # 扣的點數是算完強化 / 弱化的
            m = lo + (p.agent.choose_option(self, p, "發憤圖強-少棄", labels) if len(labels) > 1 else 0)
            m = max(lo, min(debt, m))
            if m:   # 先結算少棄的傷害 (可觸發反擊/調虎離山/占卜等),再進行棄牌
                self.log(f"{p.name} 發憤圖強少棄 {m} 張,扣 {self.dmg_preview(p, m, tgt=p)} 點體力")
                self.damage(p, p, m, _bonus=False)   # 來源是自己: 自己的強化 / 弱化會算進去 (強化後少棄 5 張 = 10 點);不吃流星錘 +1
                if not p.alive:
                    p.fa_debt = []
                    return
            k = min(debt - m, len(p.hand))
            if k:
                for c in p.agent.choose_discard(self, p, k, list(p.hand)):
                    self.discard_card(p, c)
                self.log(f"{p.name} 發憤圖強棄 {k} 張")
        extra = 0 if p.char.skip_discard(self, p) else p.char.discard_amount(self, p, len(p.hand) - self.hand_cap(p))
        if extra > 0:
            self.in_discard_phase = True   # 棄牌階段自己丟的牌不算「被捨棄」(袁術不觸發)
            try:
                for c in p.agent.choose_discard(self, p, extra, list(p.hand)):
                    self.discard_card(p, c)
            finally:
                self.in_discard_phase = False
            self.log(f"{p.name} 棄 {extra} 張")
        p.turn_flags["discarded"] = max(0, extra)
        self.new_chain()
        p.char.after_discard(self, p)
        p.char.end_turn(self, p)
        if not p.alive:
            return
        for q in list(self.alive_players()):
            q.char.on_turn_end(self, q, p)
        self.check_hands()
        self.jiu = False
        self.void = False
        p.flipped = p._char.stay_flipped(self, p)
        for q in self.players:
            if q.thunder and q.thunder[0] == self.turn_id:
                if q is not p:
                    q.flipped = q.thunder[1]
                q.thunder = None
            if q.disguise and q._char.name not in ("馬謖", "陳群", "韓當"):
                q.borrow, q.borrow2 = [], []   # 偽裝成馬謖/陳群/韓當時複製的技能,偽裝結束就失效
            q.disguise = []
            q.dg_flip = False
            q.maxhp   # 偽裝結束: 體力上限變回來,體力超過就收到上限
        for q in self.players:   # 鐵索橫置最多只到這個回合結束: 這回合橫置的人回合結束就轉回來
            if q.chained and getattr(q, "chain_turn", None) == self.turn_id:
                q.chained = False
                self.log(f"  {q.name} 的鐵索橫置到回合結束,重置")
        p.chained = False
        for q in self.players:
            q.dmg_x2 = q.dmg_half = 0

    def run(self):
        try:
            self.ordinary = True
            if self.scn:   # 教學關卡: 手牌 / 裝備 / 體力 / 牌堆順序都由關卡指定
                self.scn(self)
            else:
                for p in self.players:
                    self.draw(p, 5)
            self.ordinary = False
            for p in self.players:
                p._char.on_game_start(self, p)
            n, ls = len(self.players), self.lord.idx
            for self.round in (range(1, self.max_rounds + 1) if self.max_rounds else itertools.count(1)):   # 每輪從主公開始 (預設上限 10000 輪)
                k = 0
                while k < n:
                    p = self.players[(ls + self.dir * k) % n]
                    if p.alive:
                        self.take_turn(p)
                        assert self.count_cards() == self.total_cards, "牌數不守恆"
                    if self.round == 1 and k == 0:   # 主公第一回合結束後,由主公決定往左還是往右輪
                        ask = self.lord.alive and len(self.alive_players()) > 2 and not self.scn   # 第一回合結束只剩兩個人 (或更少): 往哪邊輪都一樣,不用問
                        i = self.lord.agent.choose_option(self, self.lord, "輪次方向", ["往左 (座位號遞增)", "往右 (座位號遞減)"]) if ask else 0
                        self.dir = 1 if i == 0 else -1
                        if ask:
                            self.log(f"  {self.lord.name} 決定輪次方向: {'往左 (座位號遞增)' if self.dir == 1 else '往右 (座位號遞減)'}")
                    k += 1
            self.winner = "平手(超過回合上限)"
        except GameOver:
            pass
        self.log(f"=== 勝利: {self.winner} ===")
        return self.winner
