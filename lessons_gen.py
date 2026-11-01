"""武將關卡: 每位武將一關。你扮演他,桌上有現成的牌和對手,照技能說明試用一次。
(技能的觸發在紀錄裡會寫成「[武將名]」,偵測到就算完成;少數被動技能沒有這種紀錄,改成自由練習。)"""
import re

from lessons_skills import SK

BS = chr(92)


# 要「複製別人技能」的武將: 對手也要有武將,不然選單只會看到一排「無名」
BORROW = {"馬謖", "陳群", "韓當", "公孫淵"}
BORROW_OPP = ["關羽", "張飛", "趙雲"]
BORROW_OPP_WU = ["孫權", "周瑜", "關羽"]   # 韓當只能複製吳勢力的人


# 技能要等「別人」出錦囊 / 出閃才會發動: 教學裡讓對手照劇本做,玩家只要結束回合或出殺就看得到
REACT_TRICK = {"張飛", "龐德", "鄧艾", "崔琰", "曹沖"}
REACT_SHAN = {"夏侯淵"}
# 要瀕死 / 剛好 1 血 / 偽裝才會發動,沒辦法穩定佈置: 改成自由練習
SHA_COUNT = {"張飛", "呂布"}   # 殺不限次數: 同一回合打出 2 張殺就算學會
LATE = {"曹洪", "劉協", "張嶷", "司馬炎", "左慈"}
FREE_ONLY = {"呂蒙", "張苞"}
# 把牌當別的牌用的武將: 紀錄會寫成「使用 兵(←殺)」,偵測到就算學會
CONV = r"P0\([^)]*\)[^\n]*使用[^\n]*(\(←| 當作 )"   # 出牌時的轉換記成 (←原牌);受傷響應裡手牌當調 / 占記成「當作 調」
CONVERT = {
    "馬超": "點一張紅色錦囊 (如決鬥、順手牽羊) 當成殺使用,對 P1 出手",
    "曹丕": "點手牌的「殺」,當成兵糧寸斷對 P1 使用",
    "徐晃": "點手牌的「殺」,當成兵糧寸斷對 P1 使用",
    "陸遜": "點一張錦囊牌 (如南蠻入侵),當成無中生有使用",
    "華佗": "體力沒滿時,點手牌的「殺」當成桃使用,回復體力",
    "甘寧": "點一張基本牌 (殺 / 閃 / 桃),當成無中生有使用",
    "龐統": "點手牌的「殺」,當成鐵索連環使用",
    "羊祜": "點手牌的「殺」當成拋磚引玉使用;或點「鐵索連環」選「重鑄」,會多抽 1 張",
}


SHA_RX = r"^P0" + BS + "([^)]*" + BS + ") 對 P" + BS + "d" + BS + "([^)]*" + BS + ") 使用 ?[紅黑]?[火冰雷]?殺"


def _rx(m, name, key):
    """技能表裡的偵測寫法 → regex (None = 沒辦法偵測,要玩家按「我看懂了」)。"""
    if key is None:
        return None
    if key == "COUNT":
        return "(?!)"
    if key == "CV:":
        return CONV
    if key.startswith("U:"):   # 使用某張牌
        return m.U(key[2:])
    if key.startswith("R:"):
        return key[2:]
    kw = key[2:]
    return r"P0" + BS + "([^)]*" + BS + ")[^" + BS + "n]*" + BS + "[" + re.escape(name) + "[^" + BS + "]]*" + BS + "]" + ("[^" + BS + "n]*" + kw if kw else "")


def _checklist(m, L, name, items):
    """每個技能一項,不分順序,全部做完才過關。對手照劇本出殺 / 錦囊 / 裝備,讓各種被動技能有東西可以觸發。"""
    L["skills"] = [dict(text=t, rx=_rx(m, name, k), count=(SHA_RX, 2) if k == "COUNT" else None) for t, k in items]
    L["steps"] = [(x["text"], x["rx"]) for x in L["skills"]]
    L["checklist"], L["free"], L["late"], L["count"] = True, False, False, None
    hand = ["殺", "殺", "決", "順", "過", "桃", "閃", "無", "南", "萬", "鐵", "火攻"] + (["投", "孤"] if name == "周胤" else []) + (["增"] if name == "姜維" else []) + (["發"] if name == "黃忠" else [])
    p0 = dict(hand=hand)
    if name == "太史慈":   # 要「抽牌階段沒抽到錦囊」才會再抽一次: 牌堆頂排成不是錦囊的牌 (對手各抽 2 張也算進去)
        L["top"] = ["殺", "閃"] * 6
    if name == "曹休":
        p0, L["draw"] = dict(hand=["殺"]), 0
    elif name in ("華佗", "關羽"):
        p0 = dict(hand=hand, hp=2, maxhp=4)
    elif name == "滿寵":
        p0 = dict(hand=[c for c in hand if c != "閃"])
    p2 = [("無", None), ("南", None)] + ([("樂", 0)] if name == "李嚴" else []) + ([("偽", None)] if name == "郭圖&逢紀" else []) + ([("鴻", 0)] if name == "周胤" else [])
    L["players"] = m.pad([p0,
                          dict(hand=["殺", "殺", "閃"], equip=["麒麟弓"], plan=[("殺", 0)], resp=["閃"], hp=4, maxhp=4),
                          dict(hand=[c for c, _ in p2], plan=p2, hp=4, maxhp=4),
                          dict(hand=["諸葛連弩", "藤甲", "閃", "閃"], plan=[("諸葛連弩", None), ("藤甲", None)], hp=4, maxhp=4)])
    if name == "孟獲":   # 體力上限 = 手牌數 + 1: 手牌少一點,體力才不會誇張
        L["players"][0] = dict(hand=["殺", "決", "順", "過"], hp=4, maxhp=5)
    if name == "張角":   # 要有血可以回: 開局先少 2 滴血
        L["players"][0] = dict(hand=hand, hp=2, maxhp=4)
    if name == "周魴":   # 要場上有人血比自己多才能換: 自己先少血
        L["players"][0] = dict(hand=hand, hp=2, maxhp=4)
    if name == "周倉":   # 一開局判定區就有閃電,手上 3 張閃: 回合開始判定到黑色受 3 點雷傷,連出 3 張閃抵擋
        L["players"][0] = dict(hand=["閃", "閃", "閃"], judge=["閃電"])
        L["top"] = ["殺@黑"] + list(L.get("top") or [])
    if name == "袁術":   # 對手對袁術用過河拆橋,拆掉一張牌就觸發技能 1
        L["players"][1] = dict(hand=["過", "過"], plan=[("過", 0)], hp=4, maxhp=4)
    if name == "劉備":   # 技能 2 要有人缺血才能回: P1 一開始就少 1 滴血
        L["players"][1] = dict(hand=["殺", "閃"], plan=[("殺", 0)], resp=["閃"], hp=3, maxhp=4)
    if name == "曹仁":   # 技能 2 要回血: 一開始就少 1 滴血
        L["players"][0] = dict(hand=hand, hp=3, maxhp=4)
    if name in ("夏侯惇", "曹洪"):   # 要自己的殺打中別人: P1 / P3 手上不留閃
        L["players"][1] = dict(hand=["殺", "殺", "桃"], equip=["麒麟弓"], plan=[("殺", 0)], hp=4, maxhp=4)
        L["players"][3] = dict(hand=["諸葛連弩", "藤甲", "桃"], plan=[("諸葛連弩", None), ("藤甲", None)], hp=4, maxhp=4)
    if name == "曹洪":   # 技能 2 會跟別人交換手牌: 自己手上不留閃,換過去之後對方才閃不掉
        L["players"][0] = dict(hand=[c for c in hand if c != "閃"], hp=2, maxhp=4)   # 先少血,才看得到回血
    if name == "魏延":   # 對 P1 或 P3 出殺都行: 兩邊都不留閃,殺才打得中
        L["players"][1] = dict(hand=["殺", "殺", "桃"], equip=["麒麟弓"], plan=[("殺", 0)], hp=4, maxhp=4)
        L["players"][3] = dict(hand=["諸葛連弩", "藤甲", "桃"], plan=[("諸葛連弩", None), ("藤甲", None)], hp=4, maxhp=4)
    if name == "呂蒙":   # 殘血 + 手上沒閃沒桃: 對手的殺打中就瀕死,觸發判定五次
        L["players"][0] = dict(hand=[c for c in hand if c not in ("閃", "桃", "無")], hp=1, maxhp=4)
        L["players"][1] = dict(hand=["殺", "殺"], plan=[("殺", 0)], hp=4, maxhp=4)
    if name == "丁奉":   # 要有人真的受傷 (對手不留閃) + 自己要有裝備可以棄
        L["players"][0] = dict(hand=hand, equip=["諸葛連弩", "藤甲", "+1馬"])
        L["players"][1] = dict(hand=["殺", "桃"], plan=[("殺", 0)], hp=4, maxhp=4)
        L["players"][3] = dict(hand=["桃", "桃"], hp=4, maxhp=4)


def build_generals(m, roster_data, untagged):
    for d in roster_data:
        name = d["name"]
        untagged = (set(untagged) | FREE_ONLY) - set(CONVERT)
        tag = None if name in untagged else rf"P0\([^)]*\)[^\n]*\[{re.escape(name)}[^\]]*\]|\[{re.escape(name)}[^\]]*\][^\n]*P0\("
        hint = "照上面的技能說明,打出能觸發「" + name + "」的牌或情況 (對手 P1 會對你出一張殺)"
        if name in CONVERT:
            tag, hint = CONV, CONVERT[name]
            if name == "羊祜":
                tag = CONV + "|P0" + BS + "([^)]*" + BS + ") 重鑄 鐵索連環"
        if name == "鄧艾":
            tag = tag + "|" + m.U("萬") + "|" + m.U("南")
            hint = "點「萬箭齊發」或「南蠻入侵」 (你用它們傷害變 2 點);或按「結束出牌」,看對手 P2 出錦囊時你的技能怎麼發動"
        if name == "曹真":   # 開局加體力上限那行不算: 要被打中時選「阻擋」
            tag = r"P0" + BS + "([^)]*" + BS + ")" + BS + "[曹真" + BS + "] 阻擋"
            hint = "結束回合,對手 P1 會對你出殺 (別出閃,讓他打中),在詢問視窗選「阻擋」"
        if name in SHA_COUNT:
            tag = (tag + "|" if tag else "") + "(?!)"   # 另外用「出殺次數」判斷,見 count
            hint = "這一回合連續對 P1 出 2 張殺 (不受一回合一張的限制)" + ("; 或按「結束出牌」看對手 P2 出無中生有時你抽 2 張" if name == "張飛" else "")
        if name == "郭圖&逢紀":   # 要等別人偽裝,下個自己的回合選「變身」才看得到
            tag = r"P0" + BS + "([^)]*" + BS + ")" + BS + "[郭圖&逢紀" + BS + "] 這回合變成"
            hint = "按「結束出牌」,對手 P2 會使用偽裝;到你的下一個回合開始時,選「發動」變成他偽裝的武將"
        if name == "左慈":   # 化身的是「場上沒有」的武將,不是複製在場的人
            hint = "每個回合開始時,從場上沒有的武將裡選一位化身 (這回合擁有他的技能)。試著用用看,結束回合後再化身一次"
        if name == "陳群":   # 技能用「〈陳群-重鑄殺〉」這種格式寫進紀錄
            tag = r"P0" + BS + "([^)]*" + BS + ")[^" + BS + "n]*使用〈陳群-"
            hint = "點技能「重鑄」: 把手上一張基本牌 (如殺) 棄掉重抽一張;體力不同時還有別的能力,看左邊的技能說明"
        if name == "曹休":
            hint = "手上只剩一張殺: 把它對 P1 打出去,手牌變成 0 就會觸發技能 (抽 1 張並讓一名角色翻面)"
        if name == "郭嘉":
            hint = "按「結束出牌」,對手 P2 會裝備武器和防具,選「抽 2 張牌」或「回 1 點血」看「郭嘉」的技能"
        if name == "李嚴":
            hint = "按「結束出牌」,對手 P2 會對你使用樂不思蜀 (延時錦囊),選「發動」就抽 2 張"
        if name == "龐德":
            tag = tag + "|" + CONV
            hint = "點手牌的「閃」當成萬箭齊發使用;或按「結束出牌」,對手 P2 會對你們出南蠻入侵,看你怎麼拿到那張牌"
        if name == "曹彰":
            tag, hint = r"P0\([^)]*\)[^\n]*少抽一張", "抽牌階段選「少抽一張」,這回合就能出兩張殺、沒有距離限制"
        if name == "關羽":   # 被動技能只有「閃桃互換」看得到: 紀錄會寫成 紅桃(←閃)
            tag = r"P0\([^)]*\)[^\n]*\(←[閃桃]\)"
            hint = "體力沒滿,點手牌的「閃」當成桃使用 (閃和桃同色可以互換),回復體力"
        if name == "滿寵":
            hint = "結束回合,P1 會對你出殺 (這關手上沒有閃,讓他打中),看「滿寵」的技能怎麼發動"
        elif name in REACT_TRICK:
            hint = "按「結束出牌」,對手 P2 會使用錦囊牌,看「" + name + "」的技能怎麼發動"
        elif name in BORROW:
            hint = ("選一位吳勢力的對手 (孫權 / 周瑜 / 黃蓋) 複製他的技能" if name == "韓當" else "選一位對手 (關羽 / 張飛 / 趙雲) 複製他的技能") + ",然後試著用用看"
        elif name == "丁奉":   # 要有人真的受傷: 對手手上不留閃,殺才打得中
            L["players"][1] = dict(hand=["桃", "桃"], hp=4, maxhp=4)
        elif name in REACT_SHAN:
            hint = "對 P1 出殺,他會出閃,看「" + name + "」的技能怎麼發動"
        if name == "陳群":
            hint = "點技能「重鑄」: 把手上一張基本牌 (如殺) 棄掉重抽一張;體力不同時還有別的能力,看左邊的技能說明"
        if name in SHA_COUNT:
            hint = "這一回合連續對 P1 出 2 張殺 (不受一回合一張的限制)" + ("; 或按「結束出牌」看對手 P2 出無中生有時你抽 2 張" if name == "張飛" else "")
        steps = [(hint, tag)] if tag else []
        L = m.lesson("g_" + name, "武將", name, f"{d['faction']}  體力 {d['maxhp']}",
                     m.pad([dict(hand=["殺", "殺", "決", "順", "過", "桃", "閃", "無", "南"]),
                            dict(hand=["殺", "閃"], plan=[("殺", 0)], hp=4, maxhp=4), dict(hand=["桃", "殺"], hp=4, maxhp=4), dict(hand=["閃", "閃"], hp=4, maxhp=4)]),
                     steps, tips=list(d["skills"]) + ["這關沒有目標限制: 隨意出牌,多試幾種組合,看看技能怎麼發動。想結束隨時可以離開。"],
                     chars=[name, *((BORROW_OPP_WU if name == "韓當" else BORROW_OPP) if name in BORROW else [None] * 3)], draw=1)
        if name == "羊祜":
            L["players"][0] = dict(hand=["殺", "殺", "決", "順", "過", "桃", "閃", "鐵", "南"])
        if name == "鄧艾":
            L["players"][0] = dict(hand=["殺", "殺", "決", "順", "過", "桃", "閃", "無", "南", "萬"])
        if name == "郭圖&逢紀":
            L["players"][2] = dict(hand=["偽", "偽"], plan=[("偽", None)], hp=4, maxhp=4)
        if name == "曹休":
            L["players"][0] = dict(hand=["殺"])
            L["draw"] = 0   # 開局不抽牌,手上就只有這一張
        if name == "郭嘉":
            L["players"][2] = dict(hand=["諸葛連弩", "藤甲"], plan=[("諸葛連弩", None), ("藤甲", None)], hp=4, maxhp=4)
        if name == "李嚴":
            L["players"][2] = dict(hand=["樂", "樂"], plan=[("樂", 0)], hp=4, maxhp=4)
        if name == "華佗":
            L["players"][0] = dict(hand=["殺", "殺", "決", "順", "過", "閃", "無", "南"], hp=2, maxhp=4)
        if name == "關羽":
            L["players"][0] = dict(hand=["閃", "閃", "殺", "決", "順"], hp=2, maxhp=4)
        if name in REACT_TRICK:
            L["players"][2] = dict(hand=["南", "南"] if name == "龐德" else ["無", "無"], plan=[("南" if name == "龐德" else "無", None)], hp=4, maxhp=4)
        elif name == "滿寵":   # 要被殺中才會發動: 手上不留閃
            L["players"][0] = dict(hand=["殺", "殺", "決", "順", "過", "桃", "無", "南"])
            L["players"][1] = dict(hand=["殺", "閃"], equip=["麒麟弓"], plan=[("殺", 0)], hp=4, maxhp=4)   # 滿寵讓距離 +1,對手要有射程才打得到
        elif name in REACT_SHAN:
            L["players"][1] = dict(hand=["殺", "閃"], plan=[("殺", 0)], resp=["閃"], hp=4, maxhp=4)
        if name in SHA_COUNT:
            L["count"] = (r"^P0\([^)]*\) 對 P\d\([^)]*\) 使用 ?[紅黑]?[火冰雷]?殺", 2)
        L["late"] = name in LATE   # 回合開始就自動發動的技能: 要等進入出牌階段之後的那次才算
        L["free"] = not steps
        L["faction"] = d["faction"]
        if name in SK:
            _checklist(m, L, name, SK[name])
