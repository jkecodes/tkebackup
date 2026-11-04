"""牌庫定義。數量取自「三國殺卡片分配表」: 各項加總 755,實際整副牌是 ×2 = 1510 張。"""
from dataclasses import dataclass
import random

# (名稱, 數量)
NATURE_SHA = [("火", 10), ("冰", 10), ("雷", 10)]  # 各種屬性殺的張數 (與一般殺同樣 ×2 副)
BASIC = [("殺", 20), ("閃", 25), ("桃", 25), ("酒", 15)]
TRICK = [
    ("順", 10), ("過", 10), ("反", 10), ("調", 10), ("占", 10), ("南", 15), ("萬", 15),
    ("無", 10), ("無懈", 10), ("轉", 10), ("突", 10), ("桃園", 5), ("樂", 20), ("聲", 10),
    ("增", 10), ("決", 10), ("強", 15), ("弱", 15), ("火攻", 20), ("借", 10), ("飢", 15),
    ("草", 15), ("閃電", 10), ("降雷", 15), ("發", 15), ("毒", 15), ("兵", 15), ("偽", 10),
    ("出", 10), ("拋", 10), ("未", 10), ("笑", 10), ("鴻", 10), ("隔", 10), ("孤", 10), ("投", 10),
    ("五", 20), ("鐵", 15), ("漁", 15),
]
ARMOR = [("雷盾", 10), ("火盾", 10), ("冰盾", 10), ("八卦陣", 15), ("仁王盾", 15), ("藤甲", 15), ("緩衝盾", 10)]
HORSE = [("+1馬", 20), ("-1馬", 20)]
WEAPON = [
    ("諸葛連弩", 10, 1), ("孔雀羽扇", 10, 4), ("青龍偃月刀", 10, 3), ("寒冰劍", 10, 2),
    ("方天畫戟", 10, 4), ("流星錘", 10, 2), ("麒麟弓", 10, 5), ("青釭劍", 10, 2), ("丈八蛇矛", 10, 3),
    ("貫石斧", 10, 3),
]
WEAPON_RANGE = {n: r for n, _, r in WEAPON}

# 目前引擎已實作的牌;其餘種類先不放進牌庫
IMPLEMENTED_TRICKS = {
    "順", "過", "反", "調", "占", "南", "萬", "無", "無懈", "轉", "突", "桃園", "樂", "聲", "增", "決",
    "強", "弱", "火攻", "借", "飢", "草", "閃電", "發", "毒", "兵", "出", "拋", "未", "笑", "鴻", "隔",
    "投", "五", "鐵", "孤", "降雷", "偽", "漁",
}  # 全部錦囊都已實作
DELAYED = {"閃電", "樂", "毒", "兵", "草"}  # 延時型錦囊: 放進判定區,在持有者回合開始時判定
SELF_DELAYED = {"閃電"}  # 只能放在自己判定區 (草/樂/兵/毒 可放自己或別人)
IMPLEMENTED_ARMOR = {"八卦陣", "仁王盾", "藤甲", "緩衝盾", "雷盾", "火盾", "冰盾"}


@dataclass(eq=False)
class Card:
    id: int
    name: str
    color: str  # 紅 / 黑
    kind: str   # basic trick weapon armor horse
    nature: str = None  # 屬性殺: 火 / 冰 / 雷 (name 仍是「殺」)

    def __repr__(self):
        return f"{self.color}{self.nature or ''}{self.name}"


@dataclass(eq=False)
class ViewCard:
    """當作別的牌使用 (例如馬超: 紅色錦囊當殺)。orig 是實際的手牌。"""
    name: str
    color: str
    kind: str
    orig: Card
    id: int = -1

    def __repr__(self):
        return f"{self.color}{self.name}(←{self.orig.name})"


@dataclass(eq=False)
class PairView(ViewCard):
    """丈八蛇矛: 兩張手牌當一張殺 (orig + extra)。"""
    extra: Card = None

    def __repr__(self):
        return f"{self.color}殺(←{self.orig}+{self.extra})"



DECK_COPIES = 2


def build_deck(rng: random.Random, only_implemented: bool = True) -> list[Card]:
    entries = [(n, c, "basic") for n, c in BASIC]
    entries += [("殺", c, "basic", nt) for nt, c in NATURE_SHA]
    entries += [(n, c, "trick") for n, c in TRICK if not only_implemented or n in IMPLEMENTED_TRICKS]
    entries += [(n, c, "armor") for n, c in ARMOR if not only_implemented or n in IMPLEMENTED_ARMOR]
    entries += [(n, c, "horse") for n, c in HORSE]
    entries += [(n, c, "weapon") for n, c, _ in WEAPON]
    deck, toggle, cid = [], 0, 0
    for name, count, kind, *nat in entries:
        for _ in range(count * DECK_COPIES):
            deck.append(Card(cid, name, "紅" if toggle == 0 else "黑", kind, nat[0] if nat else None))
            toggle ^= 1  # 紅黑交替,總數相等
            cid += 1
    rng.shuffle(deck)
    return deck
