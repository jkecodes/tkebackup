"""成就 + 外觀解鎖 (顏色主題 / 頭像框 / 頭像特效)。

解鎖條件有三種: free 免費、tier 達到某段位 (看歷史最高積分,降段不會失去)、ach 完成某個成就。
成就在每場對局結束時依玩家資料檢查 (Profiles.award 呼叫 check_achievements)。
"""
import time

TIER_NAMES = ["青銅", "白銀", "黃金", "白金", "鑽石", "大師", "傳說"]
ROLES4 = ("主公", "忠臣", "反賊", "內奸")


def _best_char_wins(p):
    return max([v[1] for v in p.get("chars", {}).values()] + [0])


# (id, 名稱, 說明, 檢查函式 (p, level, peak_tier, facts) -> bool, 進度函式 或 None)
def _lesson_total():
    import lessons
    return len(lessons.LESSONS)


ACHIEVEMENTS = [
    ("practice", "新兵報到", "通關全部練習關卡 (獎勵: 新兵框)", lambda p, lv, pt, f: len(p.get("lessons", [])) >= _lesson_total()),
    ("first_game", "初出茅廬", "完成 1 場對局", lambda p, lv, pt, f: p["games"] >= 1),
    ("first_win", "首戰告捷", "贏得 1 場勝利", lambda p, lv, pt, f: p["wins"] >= 1),
    ("games100", "身經百戰", "完成 100 場對局", lambda p, lv, pt, f: p["games"] >= 100),
    ("wins25", "常勝將軍", "累計 25 場勝利", lambda p, lv, pt, f: p["wins"] >= 25),
    ("losses50", "常輸將軍", "累計輸 50 場", lambda p, lv, pt, f: p["games"] - p["wins"] >= 50),
    ("streak3", "三連勝", "連續贏 3 場", lambda p, lv, pt, f: p.get("best_streak", 0) >= 3),
    ("streak5", "勢如破竹", "連續贏 5 場", lambda p, lv, pt, f: p.get("best_streak", 0) >= 5),
    ("ranked1", "初入戰場", "完成 1 場段位模式", lambda p, lv, pt, f: p.get("rgames", 0) >= 1),
    ("ranked10", "段位常客I", "段位模式贏 10 場 (獎勵: 青玉框)", lambda p, lv, pt, f: p.get("rwins", 0) >= 10),
    ("ranked30", "段位常客II", "段位模式贏 30 場 (獎勵: 漣漪特效)", lambda p, lv, pt, f: p.get("rwins", 0) >= 30),
    ("ranked100", "段位常客III", "段位模式贏 100 場 (獎勵: 脈衝特效)", lambda p, lv, pt, f: p.get("rwins", 0) >= 100),
    ("roles4", "四方通達", "主公、忠臣、反賊、內奸各贏過一次", lambda p, lv, pt, f: all(p.get("roles", {}).get(r, [0, 0])[1] > 0 for r in ROLES4)),
    ("chars10", "博覽群雄", "使用過 10 位不同武將", lambda p, lv, pt, f: len(p.get("chars", {})) >= 10),
    ("chars30", "天下英雄", "使用過 30 位不同武將", lambda p, lv, pt, f: len(p.get("chars", {})) >= 30),
    ("main10", "一將成名", "同一位武將贏 10 場", lambda p, lv, pt, f: _best_char_wins(p) >= 10),
    ("games50", "資深玩家", "累計完成 50 場對局", lambda p, lv, pt, f: p["games"] >= 50),
    ("tier_gold", "黃金之路", "段位達到黃金", lambda p, lv, pt, f: pt >= 2),
    ("tier_dia", "鑽石之光", "段位達到鑽石", lambda p, lv, pt, f: pt >= 4),
    ("tier_legend", "名留青史", "段位達到傳說", lambda p, lv, pt, f: pt >= 6),
    ("clutch", "絕地求生", "以 1 點體力存活並獲勝", lambda p, lv, pt, f: bool(f.get("won") and f.get("alive") and f.get("hp") == 1)),
    ("speed", "閃電戰", "在第 1 輪內獲勝", lambda p, lv, pt, f: bool(f.get("won") and 0 < f.get("rounds", 99) <= 1)),
    ("ten_free", "十雄爭霸", "在十人無身分模式下獲勝", lambda p, lv, pt, f: bool(f.get("won") and f.get("n") == 10 and f.get("noroles"))),
    ("heal32", "起死回生", "單場回復 32 點以上體力 (獎勵: 回春框)", lambda p, lv, pt, f: f.get("heal", 0) >= 32),
    ("dmg32", "毀天滅地", "單場對其他玩家打出 32 點以上傷害", lambda p, lv, pt, f: f.get("dmg", 0) >= 32),
    ("no_sha", "君子動口不動手", "整場沒有使用或打出過殺,卻贏得勝利", lambda p, lv, pt, f: bool(f.get("won") and f.get("sha", 1) == 0)),
    ("comeback", "死而後勝", "先陣亡,但最後取得勝利", lambda p, lv, pt, f: bool(f.get("won") and not f.get("alive", True))),
    ("hand20", "手牌收藏家", "手牌同時超過 20 張", lambda p, lv, pt, f: f.get("maxhand", 0) > 20),
    ("chain11", "連鎖大師", "接出第 11 個以上的連鎖", lambda p, lv, pt, f: bool(f.get("chain11"))),
    ("wei5", "易容大師", "單場使用「偽」5 次以上", lambda p, lv, pt, f: f.get("wei", 0) >= 5),
    ("prestige1", "榮耀轉生", "達到傳說後按下「轉生」,重新從青銅3出發 (獎勵: 轉生 1 頭像框)", lambda p, lv, pt, f: p.get("pres", 0) >= 1),
    ("clones", "千人一面", "在所有人武將都一樣的對局中獲勝", lambda p, lv, pt, f: bool(f.get("won") and f.get("same"))),
]
ACH_BY_ID = {a[0]: a for a in ACHIEVEMENTS}
ACH_NAME = {a[0]: a[1] for a in ACHIEVEMENTS}


def F(): return {"t": "free"}
def T(i): return {"t": "tier", "v": i}
def A(a): return {"t": "ach", "v": a}
def P(n): return {"t": "pres", "v": n}   # Prestige 次數達到 n
def S(price): return {"t": "shop", "price": price, "cur": "coins"}   # 遊戲幣商店購買
def R(price): return {"t": "shop", "price": price, "cur": "renown"}   # 聲望 (轉生才會拿到) 商店購買


# 顏色主題 (a 主色 / b 底色)、頭像框 (id 對應前端 CSS fr-<id>)、頭像特效 (fx-<id>)
THEMES = [
    {"id": "default", "n": "古風三國", "a": None, "b": None, "req": F()},
    {"id": "pixel", "n": "像素·糖粉", "a": "#ff77a8", "b": "#1d2b53", "req": F()},
    {"id": "pixel_gb", "n": "像素·掌機綠", "a": "#9bbc0f", "b": "#0f380f", "req": F()},
    {"id": "pixel_blue", "n": "像素·海藍", "a": "#29adff", "b": "#0b1a3a", "req": F()},
    {"id": "pixel_amber", "n": "像素·琥珀", "a": "#ffa300", "b": "#2e1706", "req": F()},
    {"id": "pixel_violet", "n": "像素·暮紫", "a": "#83769c", "b": "#1f1633", "req": F()},
    {"id": "pixel_red", "n": "像素·赤紅", "a": "#ff004d", "b": "#2a0a14", "req": F()},
    {"id": "pixel_bw", "n": "像素·黑白", "a": "#c2c3c7", "b": "#1a1a1a", "req": F()},
    {"id": "classic", "n": "電競藍", "a": "#3fd2ff", "b": "#0c1830", "req": F()},
    {"id": "graphite", "n": "石墨", "a": "#c3ccd8", "b": "#14161a", "req": F()},
    {"id": "jade", "n": "翡翠", "a": "#46e0a0", "b": "#0a1f1a", "req": T(1)},
    {"id": "amethyst", "n": "紫晶", "a": "#b58cff", "b": "#150f2e", "req": T(2)},
    {"id": "sakura", "n": "櫻花", "a": "#ff8fc0", "b": "#26101e", "req": A("streak3")},
    {"id": "blaze", "n": "烈焰", "a": "#ff7a45", "b": "#240f0f", "req": A("chars10")},
    {"id": "gold", "n": "金色", "a": "#f0c95c", "b": "#1d1608", "req": A("roles4")},
    {"id": "galaxy", "n": "星河", "a": "#9b8cff", "b": "#080824", "req": T(6)},
    {"id": "mint", "n": "薄荷", "a": "#7fffd4", "b": "#0b1f1d", "req": A("first_win")},
    {"id": "ocean", "n": "深海", "a": "#4d8dff", "b": "#0a1330", "req": A("games50")},
    {"id": "ice", "n": "冰藍", "a": "#bfe9ff", "b": "#0c1a28", "req": A("ranked10")},
    {"id": "coffee", "n": "咖啡", "a": "#d9a066", "b": "#21160e", "req": A("games100")},
    {"id": "forest", "n": "森林", "a": "#7ed957", "b": "#0c1f10", "req": A("chars30")},
    {"id": "ash", "n": "灰燼", "a": "#b8c0cc", "b": "#15181d", "req": A("losses50")},
    {"id": "crimson", "n": "緋紅", "a": "#ff5d73", "b": "#240c12", "req": A("wins25")},
    {"id": "sunset", "n": "夕陽", "a": "#ffb347", "b": "#26160a", "req": T(3)},
    {"id": "toxic", "n": "毒綠", "a": "#b6ff3a", "b": "#0f1a08", "req": A("chain11")},
    {"id": "cyber", "n": "賽博", "a": "#ff4de0", "b": "#1a0828", "req": A("hand20")},
    {"id": "mono", "n": "黑白", "a": "#ffffff", "b": "#0a0a0a", "req": A("no_sha")},
    {"id": "lavender", "n": "薰衣草", "a": "#c9a7ff", "b": "#1a1230", "req": T(4)},
    {"id": "royal", "n": "皇家", "a": "#ffd700", "b": "#1a0f3a", "req": A("tier_dia")},
    # 以下為商店新品
    {"id": "bamboo", "n": "青竹", "a": "#8fd694", "b": "#0d1f14", "req": S(160)},
    {"id": "plum", "n": "紅梅", "a": "#ff7b8f", "b": "#2a0f18", "req": S(160)},
    {"id": "dusk", "n": "暮色", "a": "#ff9f7a", "b": "#1d1029", "req": S(180)},
    {"id": "teal", "n": "青碧", "a": "#35e0d0", "b": "#07201f", "req": S(180)},
    {"id": "ink", "n": "墨染", "a": "#e8e2d0", "b": "#101010", "req": S(200)},
    {"id": "rosegold", "n": "玫瑰金", "a": "#f4b6a0", "b": "#241519", "req": S(260)},
    {"id": "aurora", "n": "極光夜", "a": "#7dffc3", "b": "#0b1233", "req": S(300)},
    {"id": "sapphire", "n": "藍寶石", "a": "#5aa2ff", "b": "#071a3d", "req": S(320)},
    # 聲望限定 (轉生後才買得到)
    {"id": "rn_gold", "n": "轉生·曜金", "a": "#ffd24a", "b": "#241a02", "req": R(20)},
    {"id": "rn_void", "n": "轉生·虛空", "a": "#c28bff", "b": "#07030f", "req": R(30)},
]
FRAMES = [
    {"id": "", "n": "無框", "req": F()},
    {"id": "0", "n": "青銅框", "req": F()},
    {"id": "1", "n": "白銀框", "req": T(1)},
    {"id": "2", "n": "黃金框", "req": T(2)},
    {"id": "3", "n": "白金框", "req": T(3)},
    {"id": "4", "n": "鑽石框", "req": T(4)},
    {"id": "5", "n": "大師框", "req": T(5)},
    {"id": "6", "n": "傳說框", "req": T(6)},
    {"id": "vic", "n": "勝利之框", "req": A("wins25")},
    {"id": "hund", "n": "百戰之框", "req": A("games100")},
    {"id": "coll", "n": "群英之框", "req": A("chars30")},
    {"id": "sam", "n": "武士之框", "req": A("speed")},
    {"id": "neon", "n": "霓虹框", "req": A("ten_free")},
    {"id": "rookie", "n": "新兵框", "req": A("practice")},
    {"id": "ink", "n": "墨玉框", "req": A("first_game")},
    {"id": "blossom", "n": "櫻花框", "req": A("first_win")},
    {"id": "frost", "n": "冰霜框", "req": A("ranked1")},
    {"id": "forest", "n": "翠林框", "req": A("games50")},
    {"id": "ocean", "n": "海潮框", "req": A("roles4")},
    {"id": "sunset", "n": "夕陽框", "req": A("streak3")},
    {"id": "jade", "n": "青玉框", "req": A("ranked10")},
    {"id": "ember", "n": "赤焰框", "req": A("chars10")},
    {"id": "storm", "n": "雷鳴框", "req": A("streak5")},
    {"id": "gear", "n": "齒輪框", "req": A("games100")},
    {"id": "royal", "n": "皇家紫金框", "req": A("tier_gold")},
    {"id": "crystal", "n": "水晶框", "req": A("no_sha")},
    {"id": "galaxy", "n": "星空框", "req": A("hand20")},
    {"id": "lava", "n": "熔岩框", "req": A("clutch")},
    {"id": "spring", "n": "回春框", "req": A("heal32")},
    {"id": "yinyang", "n": "陰陽框", "req": A("clones")},
    {"id": "pres1", "n": "轉生 1 框", "req": A("prestige1")},
    {"id": "pres2", "n": "轉生 2 框", "req": P(2)},
    {"id": "pres3", "n": "轉生 3 框", "req": P(3)},
    {"id": "pres4", "n": "轉生 4 框", "req": P(4)},
    {"id": "pres5", "n": "轉生 5 框", "req": P(5)},
    # 以下為商店新品
    {"id": "bronzeedge", "n": "古銅雕花框", "req": S(220)},
    {"id": "pearl", "n": "珍珠框", "req": S(240)},
    {"id": "jadebi", "n": "玉璧框", "req": S(260)},
    {"id": "cinnabar", "n": "朱砂框", "req": S(260)},
    {"id": "azure", "n": "蒼藍框", "req": S(280)},
    {"id": "candy", "n": "糖果框", "req": S(280)},
    {"id": "obsidian", "n": "黑曜石框", "req": S(320)},
    {"id": "dragon", "n": "金龍框", "req": S(420)},
    # 聲望限定
    {"id": "rn_crown", "n": "聲望之冠", "req": R(25)},
    {"id": "rn_eternal", "n": "永恆框", "req": R(45)},
]
EFFECTS = [
    {"id": "", "n": "無特效", "req": F()},
    {"id": "glow", "n": "呼吸光暈", "req": T(1)},
    {"id": "spark", "n": "星光閃爍", "req": T(2)},
    {"id": "ring", "n": "旋轉光環", "req": T(3)},
    {"id": "flame", "n": "烈焰", "req": T(4)},
    {"id": "aurora", "n": "極光", "req": T(5)},
    {"id": "rainbow", "n": "虹彩", "req": T(6)},
    {"id": "bolt", "n": "電光", "req": A("streak5")},
    {"id": "petal", "n": "落櫻", "req": A("main10")},
    {"id": "katana", "n": "武士斬", "req": A("dmg32")},
    {"id": "orbit", "n": "星軌", "req": A("games50")},
    {"id": "ripple", "n": "漣漪", "req": A("ranked30")},
    {"id": "shadow", "n": "幽冥", "req": A("comeback")},
    {"id": "dust", "n": "金粉", "req": A("chain11")},
    {"id": "snow", "n": "飄雪", "req": A("first_win")},
    {"id": "heart", "n": "心動", "req": A("ranked1")},
    {"id": "firefly", "n": "螢火", "req": dict(A("wei5"), alt="games50")},   # 已經靠「資深玩家」解鎖的人保留,
    {"id": "ice", "n": "冰晶", "req": A("streak3")},
    {"id": "pulse", "n": "脈衝", "req": A("ranked100")},
    {"id": "toxic", "n": "毒霧", "req": A("no_sha")},
    {"id": "glitch", "n": "故障", "req": A("hand20")},
    {"id": "meteor", "n": "流星", "req": A("chars10")},
    {"id": "arc", "n": "雷環", "req": A("streak5")},
    {"id": "radar", "n": "雷達", "req": A("tier_gold")},
    {"id": "ki", "n": "霸氣", "req": A("wins25")},
    {"id": "comet", "n": "彗星", "req": A("roles4")},
    {"id": "vortex", "n": "漩渦", "req": A("tier_dia")},
    {"id": "beam", "n": "光柱", "req": A("tier_legend")},
    {"id": "sun", "n": "烈陽", "req": A("chars30")},
    # 以下為商店新品
    {"id": "halo", "n": "聖輝", "req": S(380)},
    {"id": "twin", "n": "雙星", "req": S(420)},
    {"id": "embers", "n": "餘燼", "req": S(460)},
    {"id": "bubble", "n": "泡泡", "req": S(360)},
    # 聲望限定
    {"id": "rn_flame", "n": "轉生之焰", "req": R(40)},
    {"id": "rn_ring", "n": "星環", "req": R(60)},
]


# 一個成就只給一個獎勵: 同一個成就原本解鎖多個外觀的,只保留下面指定 (或第一個) 的那個,其餘改到商店買。
ACH_REWARD = {
    "first_win": ("frames", "blossom"), "games50": ("themes", "ocean"), "games100": ("frames", "hund"), "wins25": ("frames", "vic"),
    "streak3": ("themes", "sakura"), "streak5": ("fx", "bolt"), "ranked1": ("fx", "heart"), "ranked10": ("frames", "jade"),
    "ranked30": ("fx", "ripple"), "ranked100": ("fx", "pulse"), "roles4": ("themes", "gold"), "chars10": ("fx", "meteor"),
    "chars30": ("frames", "coll"), "no_sha": ("frames", "crystal"), "tier_gold": ("fx", "radar"), "tier_dia": ("themes", "royal"),
    "tier_legend": ("fx", "beam"), "hand20": ("frames", "galaxy"), "chain11": ("fx", "dust"), "heal32": ("frames", "spring"),
}
_HARD = {"tier_legend", "ranked100", "chars30", "tier_dia", "ten_free", "hand20", "chain11", "clones", "clutch"}
_MID = {"games100", "wins25", "streak5", "ranked30", "roles4", "tier_gold", "no_sha", "main10", "ranked10", "games50", "dmg32", "speed", "comeback", "wei5"}
_BASE = {"themes": 120, "frames": 200, "fx": 300, "boxes": 250}


def _to_shop():
    seen = set()
    for kind, L in _KINDS:
        for x in L:
            r = x["req"]
            if r["t"] != "ach":
                continue
            a = r["v"]
            keep = ACH_REWARD.get(a)
            if keep is None and a not in seen:
                keep = (kind, x["id"])
            if keep == (kind, x["id"]):
                seen.add(a)
                continue
            mult = 2.5 if a in _HARD else 1.5 if a in _MID else 1
            x["old"] = r   # 舊規則的解鎖條件 (只用來把以前已經拿到的人補進「已擁有」)
            x["req"] = S(int(round(_BASE[kind] * mult / 10.0)) * 10)
    for a, (kind, i) in ACH_REWARD.items():
        assert any(x["id"] == i and x["req"] == A(a) for x in dict(_KINDS)[kind]), (a, kind, i)



def req_text(r):
    if r["t"] == "free":
        return "免費"
    if r["t"] == "tier":
        return f"段位達到{TIER_NAMES[r['v']]}"
    if r["t"] == "pres":
        return f"轉生 {r['v']} 次"
    if r["t"] == "shop":
        return f"商店 🏵{r['price']} 聲望" if r.get("cur") == "renown" else f"商店 💰{r['price']}"
    return "成就「" + ACH_NAME.get(r["v"], r["v"]) + "」"


# 玩家框 (牌桌上自己座位方塊的外觀,所有人都看得到;前端 theme.js 依 id 畫出來): 4 種免費,16 種要成就解鎖
BOXES = [
    {"id": "classic", "n": "經典", "req": F()},
    {"id": "felt", "n": "綠絨", "req": F()},
    {"id": "charcoal", "n": "炭灰", "req": F()},
    {"id": "jade", "n": "翡翠", "req": A("first_win")},
    {"id": "ink", "n": "水墨", "req": A("games50")},
    {"id": "tatami", "n": "榻榻米", "req": A("games100")},
    {"id": "gold", "n": "鎏金", "req": A("wins25")},
    {"id": "sakura", "n": "櫻花", "req": A("streak3")},
    {"id": "thunder", "n": "雷霆", "req": A("streak5")},
    {"id": "ice", "n": "冰原", "req": A("ranked10")},
    {"id": "lava", "n": "熔岩", "req": A("ranked30")},
    {"id": "royal", "n": "皇家", "req": A("ranked100")},
    {"id": "sunset", "n": "黃昏", "req": A("tier_gold")},
    {"id": "crystal", "n": "水晶", "req": A("tier_dia")},
    {"id": "galaxy", "n": "星河", "req": A("tier_legend")},
    {"id": "bamboo", "n": "竹林", "req": A("roles4")},
    {"id": "samurai", "n": "武士", "req": A("chars30")},
    {"id": "scroll", "n": "卷軸", "req": A("chars30")},
    {"id": "zen", "n": "禪意", "req": A("no_sha")},
    {"id": "neon", "n": "霓虹網格", "req": A("hand20")},
    {"id": "px_grass", "n": "像素·草地", "req": F()},
    {"id": "px_dungeon", "n": "像素·地牢", "req": F()},
    {"id": "px_coin", "n": "像素·金幣", "req": A("wins25")},
    {"id": "px_lava", "n": "像素·熔岩", "req": A("ranked30")},
    {"id": "px_night", "n": "像素·星夜", "req": A("tier_gold")},
]


_KINDS = (("themes", THEMES), ("frames", FRAMES), ("fx", EFFECTS), ("boxes", BOXES))
_to_shop()


# 卡面 (你打出的牌、手牌的底色風格,其他玩家看得到) / 卡背 (座位上顯示的卡背,其他玩家看得到): 全部商店買 (經典免費)
CARDBGS = [
    {"id": "classic", "n": "預設卡面", "req": F()},
    {"id": "silk", "n": "絹帛", "req": S(180)},
    {"id": "bamboo", "n": "竹簡", "req": S(200)},
    {"id": "qinghua", "n": "青花", "req": S(220)},
    {"id": "jade", "n": "玉色", "req": S(240)},
    {"id": "ocean", "n": "深海", "req": S(200)},
    {"id": "sakura", "n": "櫻花", "req": S(240)},
    {"id": "night", "n": "星夜", "req": S(280)},
    {"id": "neon", "n": "霓虹", "req": S(360)},
    {"id": "pixel", "n": "像素·糖粉", "req": S(300)},
    {"id": "pixel_gb", "n": "像素·掌機綠", "req": S(300)},
    {"id": "pixel_blue", "n": "像素·海藍", "req": S(300)},
    {"id": "pixel_amber", "n": "像素·琥珀", "req": S(300)},
    {"id": "pixel_violet", "n": "像素·暮紫", "req": S(300)},
    {"id": "pixel_red", "n": "像素·赤紅", "req": S(300)},
    {"id": "pixel_bw", "n": "像素·黑白", "req": S(300)},
    {"id": "vermilion", "n": "朱漆", "req": S(280)},
    {"id": "ink", "n": "墨黑", "req": S(320)},
    {"id": "gold", "n": "鎏金", "req": S(360)},
]
CARDBACKS = [
    {"id": "classic", "n": "經典", "req": F()},
    {"id": "azure", "n": "蒼浪", "req": S(150)},
    {"id": "jade", "n": "翡翠錢紋", "req": S(170)},
    {"id": "ink", "n": "太極", "req": S(190)},
    {"id": "sakura", "n": "櫻花", "req": S(220)},
    {"id": "gold", "n": "鎏金", "req": S(260)},
    # 聲望限定
    {"id": "rn_void", "n": "轉生·虛空", "req": R(35)},
]
# 動畫特效 (進場 + 勝利 + 落敗 三段一組,全部玩家都看得到): 只能用聲望買。前端 anim.js 依 id 畫出來
ANIMS = [
    {"id": "", "n": "無動畫", "req": F()},
    {"id": "ink", "n": "墨韻丹青", "req": R(40)},
    {"id": "sakura", "n": "落櫻繽紛", "req": R(45)},
    {"id": "thunder", "n": "驚雷破空", "req": R(55)},
    {"id": "flame", "n": "赤壁烈焰", "req": R(60)},
    {"id": "pixel", "n": "像素街機", "req": R(80)},
    {"id": "bushi", "n": "武士", "req": R(70)},
]
# 玩家框 -> 搭配的動畫特效 (只是推薦,各自購買、各自選用,不綁定)
BOX_ANIM = {
    "charcoal": "ink", "ink": "ink", "scroll": "ink", "zen": "ink",
    "samurai": "bushi", "tatami": "bushi",
    "felt": "sakura", "jade": "sakura", "sakura": "sakura", "bamboo": "sakura",
    "classic": "thunder", "thunder": "thunder", "ice": "thunder", "crystal": "thunder", "galaxy": "thunder", "neon": "thunder", "royal": "thunder",
    "lava": "flame", "sunset": "flame", "gold": "flame",
    "px_grass": "pixel", "px_dungeon": "pixel", "px_coin": "pixel", "px_lava": "pixel", "px_night": "pixel",
}
assert {b["id"] for b in BOXES} == set(BOX_ANIM), "每個玩家框都要有對應的動畫"
_KINDS = _KINDS + (("cardbgs", CARDBGS), ("cardbacks", CARDBACKS), ("anims", ANIMS))


def catalog():
    """前端用的目錄 (不含玩家資料)。"""
    def pack(L):
        return [{k: v for k, v in dict(x, req_text=req_text(x["req"])).items() if k != "old"} for x in L]
    boxes = [dict(b, anim=BOX_ANIM.get(b["id"], "")) for b in pack(BOXES)]
    anims = [dict(x, boxes=[b["id"] for b in BOXES if BOX_ANIM.get(b["id"]) == x["id"]]) for x in pack(ANIMS)]
    return {"tiers": TIER_NAMES, "themes": pack(THEMES), "frames": pack(FRAMES), "fx": pack(EFFECTS), "boxes": boxes, "cardbgs": pack(CARDBGS), "cardbacks": pack(CARDBACKS), "anims": anims,
            "achs": [{"id": a[0], "n": a[1], "d": a[2]} for a in ACHIEVEMENTS]}


def is_unlocked(req, tier, achs, owned=(), pres=0, key=""):
    """key = "<種類>:<id>",商店的東西看有沒有買過。"""
    t = req["t"]
    if t == "free":
        return True
    if t == "tier":
        return tier >= req["v"]
    if t == "pres":
        return pres >= req["v"]
    if t == "shop":
        return key in owned
    return req["v"] in achs or (req.get("alt") in achs if req.get("alt") else False)


def item_ok(kind, item, tier, achs, owned=(), pres=0):
    return is_unlocked(item["req"], tier, achs, owned, pres, kind + ":" + item["id"])


def unlocked_ids(tier, achs, owned=(), pres=0):
    return {k: [x["id"] for x in L if item_ok(k, x, tier, achs, owned, pres)] for k, L in _KINDS}


def find(kind, iid):
    return next((x for x in dict(_KINDS).get(kind, []) if x["id"] == iid), None)


def legacy_owned(tier, achs):
    """第一次進商店系統時: 以前靠成就拿到、現在改到商店的東西,照舊規則補給玩家。"""
    out = []
    for kind, L in _KINDS:
        for x in L:
            o = x.get("old")
            if o and is_unlocked(o, tier, achs):
                out.append(kind + ":" + x["id"])
    return out


def check_achievements(p, level, peak_tier, facts):
    """依玩家資料檢查成就;回傳這次新解鎖的成就 id 列表 (已寫入 p["ach"])。"""
    got = p.setdefault("ach", {})
    new = []
    for aid, _n, _d, fn, *_ in ACHIEVEMENTS:
        if aid not in got:
            try:
                ok = fn(p, level, peak_tier, facts)
            except Exception:
                ok = False
            if ok:
                got[aid] = int(time.time())
                new.append(aid)
    return new


def auto_frame(tier):
    return str(max(0, min(6, tier)))


# 未完成成就的進度: id -> (目前值函式 (p, level, peak_rp), 目標值)。沒列出的 (一次性事件) 不顯示進度條。
_RP = {"tier_gold": 400, "tier_dia": 1100, "tier_legend": 2000}
PROGRESS = {
    "practice": (lambda p, lv, rp: len(p.get("lessons", [])), _lesson_total()),
    "first_game": (lambda p, lv, rp: p["games"], 1),
    "first_win": (lambda p, lv, rp: p["wins"], 1),
    "games100": (lambda p, lv, rp: p["games"], 100),
    "wins25": (lambda p, lv, rp: p["wins"], 25),
    "losses50": (lambda p, lv, rp: p["games"] - p["wins"], 50),
    "streak3": (lambda p, lv, rp: p.get("best_streak", 0), 3),
    "streak5": (lambda p, lv, rp: p.get("best_streak", 0), 5),
    "ranked1": (lambda p, lv, rp: p.get("rgames", 0), 1),
    "ranked10": (lambda p, lv, rp: p.get("rwins", 0), 10),
    "ranked30": (lambda p, lv, rp: p.get("rwins", 0), 30),
    "ranked100": (lambda p, lv, rp: p.get("rwins", 0), 100),
    "roles4": (lambda p, lv, rp: sum(1 for r in ROLES4 if p.get("roles", {}).get(r, [0, 0])[1] > 0), 4),
    "chars10": (lambda p, lv, rp: len(p.get("chars", {})), 10),
    "chars30": (lambda p, lv, rp: len(p.get("chars", {})), 30),
    "main10": (lambda p, lv, rp: _best_char_wins(p), 10),
    "games50": (lambda p, lv, rp: p["games"], 50),
    "tier_gold": (lambda p, lv, rp: rp, 400),
    "tier_dia": (lambda p, lv, rp: rp, 1100),
    "tier_legend": (lambda p, lv, rp: rp, 2000),
}


def progress(p, level, peak_rp):
    out = {}
    for aid, (fn, goal) in PROGRESS.items():
        if aid in p.get("ach", {}):
            continue
        try:
            out[aid] = [min(int(fn(p, level, peak_rp)), goal), goal]
        except Exception:
            pass
    return out
