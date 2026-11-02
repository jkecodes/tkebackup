"""把遊戲狀態轉成 GUI 用的 JSON (含身分/手牌遮蔽)。"""
import time
import os
import re
from cards import ViewCard, WEAPON
import cardart
from characters import SkillAct, ROSTER

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("SGS_DATA") or _HERE   # 打包版: 玩家資料 (帳號 / 戰績 / 頭像) 放在使用者資料夾
# 素材 (三國殺牌 / 三國殺武將卡 圖片) 資料夾: 環境變數 > 程式旁邊上一層 (開發環境) > 資料夾裡的 assets
_PARENT = os.path.dirname(_HERE)
ROOT = os.environ.get("SGS_ASSETS") or (_PARENT if os.path.isdir(os.path.join(_PARENT, "三國殺牌")) else os.path.join(DATA, "assets"))
CARD_DIR = os.path.join(ROOT, "三國殺牌")
ALIAS = {
    "八卦陣": "八", "仁王盾": "仁", "藤甲": "藤", "緩衝盾": "緩", "孔雀羽扇": "朱雀", "青龍偃月刀": "青龍",
    "青釭劍": "青", "寒冰劍": "寒", "方天畫戟": "方", "流星錘": "流", "麒麟弓": "麒麟", "丈八蛇矛": "丈",
    "諸葛連弩": "諸葛", "貫石斧": "貫", "五": "五穀豐登",
}
_img_cache: dict = {}
THUMB_V = "?v=ink2"   # 武將圖換成水墨版: 換網址讓瀏覽器不要用舊的快取
ROLE_RE = re.compile(r"P(\d+)\((主公|忠臣|反賊|內奸)((?:/[^)]*)?)\)")


def _chain_cards(g):
    return g.chain_view


def card_img(name, color):
    key = (name, color)
    if key not in _img_cache:
        url = None
        if name in cardart.E:   # 新卡面 (SVG,不分紅黑;依牌名畫,風格由玩家選的「卡面」決定)
            _img_cache[key] = "/cards/" + name + ".svg?v=" + cardart.VER
            return _img_cache[key]
        for stem in (color + name, color + ALIAS.get(name, name)):
            for ext in (".png", ".jpg"):
                if os.path.exists(os.path.join(CARD_DIR, stem + ext)):
                    url = "/assets/三國殺牌/" + stem + ext
                    break
            if url:
                break
        _img_cache[key] = url
    return _img_cache[key]


from card_desc import DESC


def _skill_img(name):
    """技能進連鎖時,卡面放武將的卡圖。"""
    stem = name.split("-")[0]
    if stem in ROSTER:
        return "/thumb/char/" + stem + THUMB_V
    return card_img(stem, "紅") or card_img(stem, "黑")   # 丈八蛇矛等裝備技能: 用裝備牌的圖


def _chain_dict(c, who=None):
    d = _chain_dict0(c)
    d["who"] = who
    return d


def _chain_dict0(c):
    if isinstance(c, tuple):   # 基本牌當無懈用
        d = card_dict(c[1])
        d.update(as_=None, **{"as": "無懈", "real": c[1].name, "text": f"{c[1].color}無懈(←{c[1].name})"})
        d.pop("as_")
        return d
    return dict(c, img=_skill_img(c["name"])) if isinstance(c, dict) else card_dict(c)


_FULL = {"無懈": "無懈可擊"}


def full_name(name):
    """卡牌全名 (同卡牌圖鑑): 反 → 反擊、無 → 無中生有、無懈 → 無懈可擊。殺 / 閃 / 裝備本來就是全名。"""
    if name in _FULL:
        return _FULL[name]
    d = DESC.get(name, "")
    if d.startswith(("裝備(", "武器(")):
        return name
    m = re.match(r"([^:：]+)[:：]", d)
    return re.sub(r"^[⚡⏳]\s*", "", m.group(1)).strip() if m else name


WEAPON_RANGE = {n: r for n, _c, r in WEAPON}


def range_label(name):
    """武器牌右下角方框裡的數字: 攻擊範圍。"""
    return str(WEAPON_RANGE[name]) if name in WEAPON_RANGE else ""


def bolt_name(name):
    """卡面上的牌名: ⚡ 連鎖型錦囊 (可在傷害結算前使用) 前面加 ⚡,例: ⚡占卜。"""
    return ("⚡" if DESC.get(name, "").startswith("⚡") else "") + full_name(name)


TYPE_LABEL = {"basic": "基本", "trick": "錦囊", "weapon": "武器", "armor": "防具", "horse": "坐騎"}


def type_label(name, kind):
    if cardart.KIND.get(name) == "delay":
        return "⌛錦囊"
    return TYPE_LABEL.get(kind, "")


def card_dict(c):
    if isinstance(c, SkillAct):
        return {"id": "skill:" + c.name, "name": c.name, "color": "", "kind": "skill", "img": _skill_img(c.name),
                "text": f"〈{c.name}〉", "desc": f"發動技能〈{c.name}〉"}
    real = getattr(c, "orig", c)
    d = {"id": real.id, "name": c.name, "color": c.color, "kind": c.kind,
         "img": card_img(getattr(real, "nature", None) or real.name, real.color),
         "text": f"{bolt_name(c.name)[:1] if bolt_name(c.name)[:1] == '⚡' else ''}{c.color}{getattr(c, 'nature', None) or ''}{full_name(c.name)}",
         "full": full_name(c.name), "bolt": "⚡" if DESC.get(c.name, "").startswith("⚡") else "", "nat": getattr(real, "nature", None) or "",
         "desc": DESC.get(real.name, ""), "tp": type_label(real.name, c.kind), "rng": range_label(real.name), "land": cardart.KIND.get(real.name) == "delay"}
    if getattr(real, "nature", None):
        d["desc"] = f"{real.nature}屬性殺: " + DESC["殺"]
    if isinstance(c, ViewCard):
        d["as"] = c.name
        d["real"] = real.name
        d["text"] = f"{d['bolt']}{c.color}{full_name(c.name)}(←{bolt_name(real.name)})"
        d["as_full"], d["real_full"] = bolt_name(c.name), bolt_name(real.name)
        if c.kind == "armor":   # 手牌當作防具裝備 (張遼): 詳細資訊顯示防具本身,並註明原本是哪張牌
            d["img"] = card_img(c.name, c.color)
            d["desc"] = DESC.get(c.name, "") + (f"\n(張遼: 由 {c.color}{full_name(real.name)} 當作{c.name}裝備,離開裝備欄會變回原本的牌)"
                                                  f"\n原本的牌 — {full_name(real.name)}: {DESC.get(real.name, '')}")
            d["tp"], d["rng"] = type_label(c.name, c.kind), range_label(c.name)
    return d


def fog_text(s, g, viewer, show_all):
    if show_all or not isinstance(s, str):
        return s

    def rep(m):
        i = int(m.group(1))
        if i == viewer or i in g.revealed:
            return m.group(0)
        return f"P{i}(?{m.group(3)})"
    return ROLE_RE.sub(rep, s)


def fog_any(x, g, viewer, show_all):
    if show_all:
        return x
    if isinstance(x, str):
        return fog_text(x, g, viewer, show_all)
    if isinstance(x, list):
        return [fog_any(i, g, viewer, show_all) for i in x]
    if isinstance(x, dict):
        return {k: fog_any(v, g, viewer, show_all) for k, v in x.items()}
    return x


_SK = {}


def _skill_lines(name):
    """characters.md 裡某武將的技能說明 (去掉編號),複製技能的標記要寫出複製了哪些技能。"""
    if not _SK:
        import os
        cur = None
        try:
            for line in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "characters.md"), encoding="utf-8"):
                line = line.strip()
                if line.startswith("### "):
                    cur = line[4:].strip(); _SK[cur] = []
                elif cur and re.match(r"\d+\.\s", line):
                    _SK[cur].append(re.sub(r"^\d+\.\s*", "", line).strip())
        except OSError:
            pass
    return _SK.get(name, [])


def _badges(g, p, c=None):
    """武將身上的標記 / 狀態 (都是公開資訊)。k 決定顏色: cnt 計數 / once 一次性技能 / st 狀態 / mk 指定。"""
    out = []

    def add(t, k):
        out.append({"t": t, "k": k})
    sub = c is not None   # 偽裝 / 化身成別的武將: 只顯示那個新武將的標記
    c = c or p._char
    def chars_badges(c):   # 武將專屬標記 (馬謖 / 陳群 / 韓當複製技能時,連複製來源的標記也一起顯示)
        n = c.name
        if n == "劉備":
            add(f"仁 ×{getattr(c, 'ren', 0)}", "ren")
        elif n == "曹操":
            add(f"弒 ×{getattr(c, 'shi', 0)}", "shi")
        elif n == "張松" and getattr(c, "mark", None) is not None:
            add(f"🎯 指定 P{c.mark}", "mk")
        elif n == "呂布":
            add("無效 (已用)" if c.used else "無效 (可用)", "once")
            if g.void and g.cur is p:
                add("⚡ 本回合全場無效", "st")
        elif n == "劉禪" and c.used:
            add("令棄牌 (已用)", "once")
        elif n == "楊修":
            if getattr(c, "armed", -1) == g.turn_id and g.cur is p:
                add(f"吸收傷害中 {getattr(c, 'acc', 0)}", "st")
            add("吸傷 (已用)" if c.used else "吸傷 (可用)", "once")
        elif n == "陳群":
            add({4: "4血: 手牌當突襲", 3: "3血: 無距離限制", 2: "2血: 複製技能", 1: "1血: 手牌當占卜"}.get(p.hp, f"{p.hp}血"), "st")
        elif n == "崔琰":
            add("技能無效 (到下個自己回合)" if c.off else f"跟抽 {c.cnt}/3", "st" if c.off else "cnt")
        elif n == "曹真":
            add("阻擋 (本回合已用)" if c.used == g.turn_id else "阻擋 (可用)", "once")
        elif n == "司馬昭" and (c.next_double or (g.cur is p and p.turn_flags.get("sm_double"))):
            add("下回合傷害 ×2" if c.next_double else "本回合傷害 ×2", "st")
        elif n == "許褚" and p.turn_flags.get("xc"):
            add("本回合傷害 ×2", "st")   # 放棄抽牌: 跟強化一樣掛一個傷害倍率的標記
        elif n == "姜維" and getattr(c, "bonus", 0):
            add(f"下回合多抽 ×{c.bonus}", "st")
        elif n == "張飛":
            add(f"本回合已扣血 {p.dmg_turn}/2", "cnt")
        elif n == "諸葛亮" and not p.equip.get("armor") and not p.equip.get("armor2"):
            add("無防具: 視為八卦陣", "st")
        elif n == "曹植":
            b = g.__dict__.get("_cz_rounds", {}).get(p.idx)   # 跟勝利判定同一個起算點: 現在是第幾輪 (1~7)
            add(f"第 {max(1, min(7, g.round - b[0])) if b else 1}/7 輪", "cnt")
        elif n == "虞翻" and c.base is not None:
            add(f"全場殺 {g.sha_total - c.base}/7", "cnt")
        elif n == "郭圖&逢紀" and c.next_char:
            add(f"下回合變成 {c.next_char}", "st")
        elif n == "公孫淵" and c.pending is not None and c.pending.alive:
            add(f"下回合獲得 P{c.pending.idx} 的技能", "st")
        elif n == "左慈" and c.used:
            add(f"化身 ×{len(c.used)}", "cnt")
    chars_badges(c)
    for q in p.borrow + p.borrow2:   # 複製技能: 標記也照抄 (狀態用原本武將那張的)
        if q is not p and q.alive and not sub and q._char.name != c.name:
            chars_badges(q._char)
    if p.skip_turn:   # 被劉禪指定: 下個自己的回合整個跳過
        add("⏭ 下回合被跳過", "st")
    if p.dmg_x2 or p.dmg_half:   # 強 / 弱: 這回合「造成」的傷害倍率
        d = p.dmg_x2 - p.dmg_half
        if d:   # 強弱抵銷剛好 ×1 就不顯示
            mult = f"×{2 ** d}" if d >= 0 else f"×1/{2 ** -d}"
            add(f"傷害 {mult}", "st")
    if sub:
        for a in p.alias:
            add(f"化身為 {a.name}", "st")
        return out
    for a in p.alias:   # 左慈等「化身」: 現在變成哪個武將
        add(f"化身為 {a.name}", "st")
    for q in p.borrow + p.borrow2:   # 馬謖/陳群/韓當: 複製了誰的技能
        if q is p:
            continue
        if q.alive:
            add(f"複製 P{q.idx} {q._char.name} 的技能", "st")   # 技能內容寫在點兩下武將的說明裡 (黃字)
            out[-1]["bw"] = [q.idx, q._char.name]
        else:
            add(f"P{q.idx} {q._char.name} 已死亡,失去複製的技能", "st")
    for q in g.players:   # 被張松指定的人
        if q is not p and q.alive and q._char.name == "張松" and getattr(q._char, "mark", None) == p.idx:
            add(f"🎯 被 P{q.idx} 張松指定", "mk")
    return out


def player_dict(g, p, viewer, show_all, nicks={}, humans=(), m_host=(), lvs={}, avs={}):
    reveal = show_all or p.idx == viewer or p.idx in g.revealed
    show_hand = show_all or p.idx == viewer
    sub_c = (p.disguise or p.alias or [None])[0]   # 翻面: 標記先藏起來;偽裝 / 化身成別人: 改顯示新武將的標記;變回來才恢復原本的
    hide_bd = bool(p.flipped)
    return {
        "idx": p.idx, "name": p.name if reveal else fog_text(p.name, g, viewer, False),
        "char": p._char.name if p._char.name != "無名" else "", "faction": p._char.faction,
        "disguise": p.disguise[0].name if p.disguise else (p.alias[0].name if p.alias else None), "disguise_kind": "disguise" if p.disguise else "alias" if p.alias else None,
        "role": p.role if reveal else "?", "hp": p.hp, "maxhp": p.maxhp, "alive": p.alive,
        "hand_n": len(p.hand), "hand": [card_dict(c) for c in p.hand] if show_hand else None,
        "equip": {k: (card_dict(v) if v else None) for k, v in p.equip.items()},
        "judge": [card_dict(c) for c in p.judge], "stash_n": len(p.stash),
        "chained": p.chained, "flipped": p.flipped, "dg_flip": p.dg_flip, "is_viewer": p.idx == viewer, "nick": nicks.get(p.idx), "lv": lvs.get(p.idx), "avatar": avs.get(p.idx), "human": p.idx in humans, "host_seat": bool(m_host) and p.idx in m_host,
        "marks": getattr(p._char, "ren", None) if p._char.name == "劉備" and not hide_bd and sub_c is None else None,
        "badges": [] if hide_bd else _badges(g, p, sub_c),
    }


def snapshot(m, viewer, since_log, since_th, peek):
    """viewer: 人類玩家座位,None = 觀戰 (全部可見)。"""
    g = m.game
    if g is None:
        return {"ready": False}
    # 有真人座位時,沒坐位的人 (旁觀者) 只能看公開資訊,不能全知
    dead = viewer is not None and 0 <= viewer < len(g.players) and not g.players[viewer].alive
    cfg_ = m.cfg or {}
    spec_all = (viewer is None or dead) and bool(cfg_.get("spec_all")) and not cfg_.get("ranked")   # 房主開了「旁觀者可看全部」(只有休閒模式);已陣亡的真人也算旁觀者
    show_all = (viewer is None and not m.humans) or spec_all   # 沒開這個選項時,旁觀者 / 陣亡的人只能看公開資訊
    spectator = viewer is None or dead
    if spectator and not show_all:
        viewer = -1
    elif dead:
        viewer = -1
    over = g.winner is not None
    show_thoughts = show_all or over or peek
    logs = g.logs[since_log:]
    out = {
        "ready": True, "round": g.round, "cur": g.cur.idx, "winner": g.winner, "over": over,
        "deck": len(g.deck), "discard": len(g.discard), "discard_top": card_dict(g.discard[-1]) if g.discard else None,
        "discard_chain": [_chain_dict(c, w) for c, w in _chain_cards(g)[-10:]], "discard_chain_off": max(0, len(_chain_cards(g)) - 10),
        "reveal": ({"title": g.last_reveal[0], "cards": [{"who": w, "card": card_dict(c)} for w, c in g.last_reveal[1] if c]} if g.last_reveal else None),
        "last_judge": ({"who": g.last_judge[0], "card": card_dict(g.last_judge[1])} if g.last_judge and g.last_judge[1].id >= 0 else None), "viewer": None if spectator else viewer,
        "multi": len(m.humans) > 1,
        "players": [player_dict(g, p, viewer, show_all or over, m.seat_names(), m.humans, {s for s, t in m.claims.items() if t == m.host}, m.seat_levels(), m.seat_avatars()) for p in g.players],
        "logs": [fog_text(x, g, viewer, show_all or over) for x in logs], "log_total": len(g.logs),
        "thoughts": [], "thought_total": len(m.rec.items), "thoughts_visible": show_thoughts,
        "paused": m.paused, "speed": m.speed, "error": m.error,
        "pending": None,
    }
    if show_thoughts:
        out["thoughts"] = fog_any(m.rec.items[since_th:], g, viewer, show_all or over or peek)
    pend = m.pending
    multi = m.multi
    if multi:   # 同時詢問多人 (瀕死): 每個人看到自己的那一份
        out["waiting"] = next(iter(multi))
        out["waiting_all"] = list(multi)
        if viewer is not None and viewer in multi and viewer not in m.multi_res:
            out["pending"] = fog_any(multi[viewer], g, viewer, over)
        return out
    out["waiting"] = pend["seat"] if pend else None   # 目前正在等誰操作 (只公開座位,不公開內容)
    if pend and viewer is not None and pend["seat"] == viewer:
        out["pending"] = fog_any(pend, g, viewer, over)  # 提示文字裡的身分也要遮蔽
        if pend.get("deadline"):
            out["pending"]["left"] = max(0, round(pend["deadline"] - time.time(), 1))   # 倒數秒數
    return out


def ctext(c):
    """詢問框 / 選項上的牌名: 花色 + 屬性 + 圖鑑全名 (當作時: 當作的全名←原牌全名)。"""
    d = card_dict(c)
    if d.get("as"):
        return (d.get("as_full") or d["as"]) + "←" + (d.get("real_full") or d["real"])
    return (d.get("color") or "") + (d.get("nat") or "") + (d.get("full") or d["name"])
