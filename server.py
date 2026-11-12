"""進化三國 GUI 伺服器 (只用標準函式庫,瀏覽器開 http://127.0.0.1:8765)。

    python server.py          # 啟動並自動開啟瀏覽器
"""
import hashlib
import json
import math
import mimetypes
import os
import random
import re
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse, parse_qs

from ai import HeuristicAgent, LeveledAgent
from ai_pro import ProAgent
from characters import ROSTER
from engine import Game, ROLES
from human import HumanAgent
from thinking import Observed, Recorder
import lessons
from view import ROOT, DATA, snapshot
import cosmetics
import devconsole
import cardart

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
CACHE = os.path.join(WEB, "cache") if DATA == HERE else os.path.join(DATA, "cache")
PORT = int(os.environ.get("SGS_PORT", "8765"))
BETA = os.environ.get("SGS_BETA") == "1" or (not os.environ.get("SGS_DATA") and os.environ.get("SGS_BETA") != "0")   # 雲端有設 SGS_DATA;本機直接跑 server.py 就是測試服 (名稱改「進化三國測試服」、版本寫 beta version)
BEHIND = [0]   # 測試服: 本機比 GitHub 落後幾個提交 (啟動時背景 git fetch 後算出來,0 = 最新或查不到)
def _check_behind():
    import subprocess
    try:
        kw = dict(cwd=HERE, capture_output=True, text=True, timeout=30)
        subprocess.run(["git", "fetch", "-q", "origin", "main"], **kw)
        r = subprocess.run(["git", "rev-list", "--count", "HEAD..origin/main"], **kw)
        BEHIND[0] = int(r.stdout.strip() or 0)
        if BEHIND[0]: print("GitHub 上有新版本: 落後 %d 個提交 (git pull 可更新)" % BEHIND[0])
    except Exception:
        pass
if BETA and __name__ == "__main__":   # 只有真的啟動伺服器才去 GitHub 問 (被別的程式 import / 多程序模擬時不要每個程序都 git fetch)
    threading.Thread(target=_check_behind, daemon=True).start()
os.makedirs(DATA, exist_ok=True)



def make_ai(level):
    """電腦代理: 全部難度都是最強的 ProAgent (移植自實戰機器人),難度越低,進階判斷關得越多 (見 ProAgent.adv)。"""
    return ProAgent(level)


class Profiles:
    """玩家檔案: UUID (= 玩家的帳號憑證, 存在瀏覽器) -> 經驗值 / 場數 / 勝場。存在 profiles.json。"""
    PATH = os.path.join(DATA, "profiles.json")
    XP_GAME, XP_WIN = 20, 30

    def __init__(self):
        self.lock = threading.Lock()
        try:
            self.d = json.load(open(self.PATH, encoding="utf-8"))
        except (OSError, ValueError):
            self.d = {}
        self._migrate_rp()

    def _migrate_rp(self):
        """v1.7.58 把舊積分依比例換算到新門檻 (rkv=2),之後決定「積分數字維持原本的、段位依新門檻重算」:
        對 rkv=2 的人把換算反推回原本的積分 (rkv=3,只做一次,改之前先備份);其餘沒標記的人積分本來就是原本的,直接標 rkv=3。"""
        old, new = self.OLD_RANKS, [lo for _, lo in self.RANKS]
        def back(v):
            v = max(0, int(v or 0))
            if v >= new[-1]:
                return old[-1] + (v - new[-1])
            for i in range(len(new) - 1):
                if new[i] <= v < new[i + 1]:
                    return round(old[i] + (v - new[i]) * (old[i + 1] - old[i]) / (new[i + 1] - new[i]))
            return v
        todo = [p for p in self.d.values() if isinstance(p, dict) and p.get("rkv") != 3]
        if not todo:
            return
        if any(p.get("rkv") == 2 for p in todo):
            try:
                import shutil
                shutil.copy(self.PATH, self.PATH + ".bak-before-revert")   # 資料資料夾裡的備份,不在 repo
            except OSError:
                pass
        for p in todo:
            if p.get("rkv") == 2:
                for k in ("rp", "peak_rp"):
                    if k in p:
                        p[k] = back(p[k])
            p["rkv"] = 3
        try:
            self._save()
        except Exception:
            pass

    # 段位: 積分 (rp) 決定。每個段位 (傳說除外) 再分 3 / 2 / 1 三小段,1 最高
    RANKS = [("青銅", 0), ("白銀", 150), ("黃金", 400), ("白金", 700), ("鑽石", 1100), ("大師", 1500), ("傳說", 2000)]
    OLD_RANKS = (0, 100, 250, 450, 700, 1000, 1400)   # v1.7.57 以前的門檻: 啟動時把舊積分照比例換算到新門檻,每個人的段位維持不變
    WIN_RP = {1: 10, 2: 18, 3: 25, 4: 32, 5: 40}   # 段位模式贏: 依電腦難度加分 (全真人 25)
    RANK_DIFF = {"青銅": 1, "白銀": 2, "黃金": 3, "白金": 3, "鑽石": 4, "大師": 4, "傳說": 5}   # 段位模式: 電腦難度跟著段位 (弱 / 中 / 強 / 很強 / 極強)
    LOSS_RP = {1: 10, 2: 18, 3: 25, 4: 32, 5: 40}   # 段位模式輸: 扣分 = 同難度贏的加分 (所以勝率超過約 50% 積分才會往上走;全真人 25;最低 0 分)
    # 身分係數: 依人數和身分的實測勝率 (電腦對電腦各 300 場) 調整輸贏分數,讓每個身分的期望分數接近 0
    # (贏的倍率 = 輸贏賠率的平方根,限制在 0.7~2.5;輸的倍率 = 贏的倍率 / 賠率,限制在 0.5~1.2;主公和忠臣同一陣營,用同一組)
    ROLE_P = {4: {"主公": .59, "忠臣": .59, "反賊": .25, "內奸": .14}, 5: {"主公": .47, "忠臣": .47, "反賊": .38, "內奸": .12},
              6: {"主公": .36, "忠臣": .36, "反賊": .49, "內奸": .10}, 7: {"主公": .36, "忠臣": .36, "反賊": .54, "內奸": .07},
              8: {"主公": .36, "忠臣": .36, "反賊": .59, "內奸": .04}}

    @classmethod
    def role_mult(cls, n, role):
        """(贏的倍率, 輸的倍率)。人數超出 4~8 就用最接近的一組。"""
        p = cls.ROLE_P[max(4, min(8, int(n)))].get(role)
        if not p:
            return 1.0, 1.0
        s = (1 - p) / p
        w = max(0.7, min(2.5, math.sqrt(s)))
        l = max(0.5, min(1.2, w / s))
        return round(w, 2), round(l, 2)
    LOSS_TIER = ((700, 0.7), (1500, 1.0), (2000, 1.15), (10**9, 1.3))   # 分段式期望值: 低段位輸得少 (損益兩平勝率約 41%),高段位輸得多 (大師約 53%、傳說約 57%)

    @classmethod
    def loss_tier(cls, rp):
        rp = max(0, int(rp or 0))
        return next(m for hi, m in cls.LOSS_TIER if rp < hi)

    SPREAD = 500                            # 對手平均積分差 / 這個數 = 加減分比例 (±50% 封頂)

    @classmethod
    def rank(cls, rp):
        """回傳 (段位, 小段 3/2/1 或 None, 本段下限, 下一段門檻 或 None)。"""
        rp = max(0, int(rp or 0))
        for i, (nm, lo) in enumerate(cls.RANKS):
            hi = cls.RANKS[i + 1][1] if i + 1 < len(cls.RANKS) else None
            if hi is None or rp < hi:
                if hi is None:
                    return nm, None, lo, None
                step = (hi - lo) / 3
                k = min(2, int((rp - lo) // step))
                return nm, 3 - k, math.ceil(lo + k * step - 1e-9), math.ceil(lo + (k + 1) * step - 1e-9) if k < 2 else hi
        return cls.RANKS[0][0], 3, 0, 33

    @classmethod
    def rank_label(cls, rp):
        nm, sub, _, _ = cls.rank(rp)
        return nm if sub is None else f"{nm}{sub}"

    @staticmethod
    def level(xp):
        return 1 + int((xp / 50) ** 0.5)   # Lv2=50 Lv3=200 Lv4=450 Lv5=800 ...

    @staticmethod
    def xp_for(lv):
        return 50 * (lv - 1) ** 2

    def get(self, tok, create=True):
        if not tok:
            return None
        with self.lock:
            p = self.d.get(tok)
            if p is None and create:
                p = self.d[tok] = {"xp": 0, "games": 0, "wins": 0, "created": int(time.time()), "rkv": 3}
                self._save()
            return p

    def uid(self, tok):
        """對外顯示的 8 位數字 ID (登入憑證 tok 仍是長的隨機值,不能外洩)。"""
        import random
        with self.lock:
            p = self.d.get(tok)
            if p is None:
                return ""
            if not p.get("uid"):
                used = {q.get("uid") for q in self.d.values()}
                while True:
                    n = str(random.randint(10000000, 99999999))
                    if n not in used:
                        break
                p["uid"] = n
                self._save()
            return p["uid"]

    DEVS = {"jke", "lone_a"}   # 開發者 (帳號名稱小寫)

    TESTERS = {"名字真的很麻煩", "loneachess"}   # 測試者 (帳號名稱小寫): 顯示黃色「測試者」標籤

    def dev(self, tok):   # False / "dev" (開發者) / "tester" (測試者); 前端只看真假與字串
        u = ACCOUNTS.uuids.get(tok)
        if u in self.DEVS:
            return "dev"
        t = (self.d.get(tok) or {}).get("tag")   # 開發者主控台手動給的標籤
        return t if t in ("dev", "tester") else "tester" if u in self.TESTERS else False

    def info(self, tok):
        p = self.get(tok)
        if not p:
            return None
        lv = self.level(p["xp"])
        rp = p.get("rp", 0)
        nm, sub, lo, hi = self.rank(rp)
        return {"uuid": self.uid(tok), "dev": self.dev(tok), "rank": self.rank_tag(p), "coins": p.get("coins", 0), "renown": p.get("renown", 0), "pres": p.get("pres", 0), "can_prestige": rp >= self.PRESTIGE_RP, "prestige_rp": self.PRESTIGE_RP, "next_rank": self.rank_label(hi) if hi is not None else None, "tier": nm, "rp": rp, "rp_lo": lo, "rp_next": hi,
                "rstreak": p.get("rstreak", 0), "streak_bonus": min(self.STREAK_CAP, p.get("rstreak", 0) * self.STREAK_STEP), "streak_cap": self.STREAK_CAP, "streak_step": self.STREAK_STEP,
                "rgames": p.get("rgames", 0), "rwins": p.get("rwins", 0), "rank_note": p.get("rank_note"), "level": lv, "xp": p["xp"], "xp_cur": self.xp_for(lv), "xp_next": self.xp_for(lv + 1),
                "games": p["games"], "wins": p["wins"], "playtime": p.get("playtime", 0), "avatar": self.avatar_url(tok),
                "chars": sorted(([n, v[0], v[1]] for n, v in p.get("chars", {}).items()), key=lambda x: (-x[1], -x[2]))[:3],
                "roles": {n: v for n, v in p.get("roles", {}).items()},
                **self.cos_info(tok)}

    # ---------- 成就 / 外觀 (頭像框、頭像特效、顏色主題) ----------
    def tier_idx(self, rp):
        return cosmetics.TIER_NAMES.index(self.rank(rp)[0])

    def peak_tier(self, p):
        return self.tier_idx(max(p.get("peak_rp", 0), p.get("rp", 0)))

    LESSON_COINS, LESSON_COINS_ROLE = 10, 40   # 練習關卡第一次過關的遊戲幣 (身分關卡 40)

    def lesson_clear(self, tok, ids, reward=False):
        """記下這個帳號通關的練習關卡 (只收有效的關卡 id);全部通關就解鎖「新兵報到」(新兵框)。"""
        p = self.get(tok)
        if not p:
            return {"ok": False}
        valid = {L["id"] for L in lessons.LESSONS}
        with self.lock:
            have = set(p.get("lessons", []))
            new = {i for i in ids if i in valid} - have
            gain = 0
            if reward:   # 打完關卡才給遊戲幣 (只有第一次);瀏覽器補報舊紀錄不給
                for i in new:
                    L = lessons.by_id(i)
                    gain += self.LESSON_COINS_ROLE if L and L.get("group") == "身分" else self.LESSON_COINS
                if gain:
                    p["coins"] = p.get("coins", 0) + gain
            have |= new
            p["lessons"] = sorted(have)
            self._check_ach(p)
            self._save()
        return {"ok": True, "n": len(have), "total": len(valid), "coins": gain}

    def _check_ach(self, p, facts=None):
        new = cosmetics.check_achievements(p, self.level(p["xp"]), self.peak_tier(p), facts or {})
        if new:
            p.setdefault("ach_new", []).extend(new)
        return new

    PRESTIGE_RP = 2000      # 傳說 (積分達到這個數字) 才能 Prestige
    @staticmethod
    def renown_for(n):
        """第 n 次轉生拿到的聲望 (Renown): 20, 25, 30 ..."""
        return 15 + 5 * n
    PRESTIGE_MAX = 10

    def rank_tag(self, p):
        """名字旁邊的段位標籤: 有 Prestige 的在前面加 ★N。"""
        lab = self.rank_label(p.get("rp", 0))
        n = p.get("pres", 0)
        return f"★{n} {lab}" if n else lab

    def _ensure_shop(self, p):
        """商店系統上線前靠成就拿到、現在要用買的外觀: 照舊規則補進「已擁有」(只做一次)。"""
        if p.get("shopv") == 1:
            return
        with self.lock:
            if p.get("shopv") == 1:
                return
            self._check_ach(p)
            owned = set(p.get("owned", []))
            owned.update(cosmetics.legacy_owned(self.peak_tier(p), p.get("ach", {})))
            p["owned"] = sorted(owned)
            p["shopv"] = 1
            self._save()

    def _ok(self, p):
        """回傳 ok(kind, id): 這個外觀這位玩家能不能用。"""
        self._ensure_shop(p)
        tier, achs, owned, pres = self.peak_tier(p), p.get("ach", {}), set(p.get("owned", [])), p.get("pres", 0)
        grant, revoke = set(p.get("dev_grant", [])), set(p.get("dev_revoke", []))   # 開發者主控台手動給 / 收回的外觀
        def ok(kind, v):
            x = cosmetics.find(kind, v)
            key = kind + ":" + v
            return bool(x) and key not in revoke and (key in grant or cosmetics.item_ok(kind, x, tier, achs, owned, pres))
        return ok

    @staticmethod
    def dev_adj(p, cos):
        """開發者手動給 / 收回的外觀,套用到 unlocked_ids 的結果上。"""
        grant, revoke = set(p.get("dev_grant", [])), set(p.get("dev_revoke", []))
        out = {}
        for kind, ids in cos.items():
            keep = [i for i in ids if kind + ":" + i not in revoke]
            keep += [k.split(":", 1)[1] for k in grant if k.startswith(kind + ":") and k.split(":", 1)[1] not in keep]
            out[kind] = keep
        return out

    def buy(self, tok, kind, iid):
        p = self.get(tok)
        self._ensure_shop(p)
        x = cosmetics.find(kind, iid)
        if not x or x["req"]["t"] != "shop":
            return {"ok": False, "error": "這個東西不能購買"}
        key = kind + ":" + iid
        with self.lock:
            if key in p.get("owned", []):
                return {"ok": False, "error": "你已經擁有了"}
            price = x["req"]["price"]
            cur = x["req"].get("cur", "coins")
            name = "聲望" if cur == "renown" else "遊戲幣"
            if p.get(cur, 0) < price:
                return {"ok": False, "error": f"{name}不夠 (需要 {price},你有 {p.get(cur, 0)})"}
            p[cur] = p.get(cur, 0) - price
            p.setdefault("owned", []).append(key)
            self._save()
        return {"ok": True, "bought": key, "coins": p.get("coins", 0), "renown": p.get("renown", 0), **self.cos_info(tok)}

    def prestige(self, tok):
        """傳說之後按「轉生」(Prestige): 積分歸零回到青銅3,轉生次數 +1,拿到聲望 (外觀、成就、歷史最高段位都保留)。"""
        p = self.get(tok)
        with self.lock:
            if p.get("rp", 0) < self.PRESTIGE_RP:
                return {"ok": False, "error": "要先達到傳說才能轉生"}
            if p.get("pres", 0) >= self.PRESTIGE_MAX:
                return {"ok": False, "error": f"已經轉生到最高等級 ({self.PRESTIGE_MAX} 次)"}
            p["peak_rp"] = max(p.get("peak_rp", 0), p.get("rp", 0))
            p["pres"] = p.get("pres", 0) + 1
            p["rp"] = 0; p["rstreak"] = 0
            gain = self.renown_for(p["pres"])
            p["renown"] = p.get("renown", 0) + gain
            p.pop("rank_note", None)
            self._check_ach(p)
            self._save()
        return {"ok": True, "pres": p["pres"], "renown": p["renown"], "reward": gain}

    def cos_info(self, tok):
        p = self.get(tok)
        self._ensure_shop(p)
        with self.lock:
            if self._check_ach(p):   # 舊帳號第一次看資料時,依既有戰績補發成就
                self._save()
        tier, achs = self.peak_tier(p), p.get("ach", {})
        st = self.style(tok)
        return {"coins": p.get("coins", 0), "renown": p.get("renown", 0), "pres": p.get("pres", 0), "cos": self.dev_adj(p, cosmetics.unlocked_ids(tier, achs, set(p.get("owned", [])), p.get("pres", 0))), "sel": {"frame": st["fr"], "fx": st["fx"], "theme": p.get("theme"), "box": st["bx"], "cardbg": st["cb"], "cardback": st["bk"], "cardart": st["ca"], "genart": st["ga"], "anim": st["an"]},
                "ach": achs, "ach_new": list(p.get("ach_new", [])), "peak_tier": tier, "ach_prog": cosmetics.progress(p, self.level(p["xp"]), max(p.get("peak_rp", 0), p.get("rp", 0)))}

    def style(self, tok):
        """目前使用的頭像框 / 特效 (沒選過: 頭像框自動用最高段位的框)。"""
        p = self.d.get(tok)
        if not p:
            return {"fr": "", "fx": "", "bx": "", "cb": "", "bk": "", "ca": "", "ga": "", "an": ""}
        tier, sel = self.peak_tier(p), p.get("sel", {})
        ok = self._ok(p)
        fr = sel["frame"] if "frame" in sel and ok("frames", sel["frame"]) else cosmetics.auto_frame(tier)
        fx = sel.get("fx", "") if ok("fx", sel.get("fx", "")) else ""
        bx = sel.get("box", "") if ok("boxes", sel.get("box", "")) else ""
        cb = sel.get("cardbg", "") if ok("cardbgs", sel.get("cardbg", "")) else ""
        bk = sel.get("cardback", "") if ok("cardbacks", sel.get("cardback", "")) else ""
        ca = "svg" if sel.get("cardart") == "svg" else ""   # 卡圖外觀: "" = 新水墨圖, "svg" = 手繪向量圖 (免費,不用解鎖)
        an = sel.get("anim", "") if ok("anims", sel.get("anim", "")) else ""
        return {"fr": fr, "fx": fx, "bx": bx, "cb": cb, "bk": bk, "an": an, "ca": ca, "ga": "old" if sel.get("genart") == "old" else ""}

    def set_style(self, tok, frame, fx, theme=None, box=None, cardbg=None, cardback=None, cardart=None, genart=None, anim=None):
        p = self.get(tok)
        ok = self._ok(p)
        with self.lock:
            sel = p.setdefault("sel", {})
            if frame is not None and ok("frames", frame):
                sel["frame"] = frame
            if fx is not None and ok("fx", fx):
                sel["fx"] = fx
            if box is not None and (box == "" or ok("boxes", box)):
                sel["box"] = box
            if cardbg is not None and ok("cardbgs", cardbg):
                sel["cardbg"] = cardbg
            if anim is not None and (anim == "" or ok("anims", anim)):
                sel["anim"] = anim
            if cardart in ("", "svg", "ink"):
                sel["cardart"] = "svg" if cardart == "svg" else ""
            if genart in ("", "old", "ink"):
                sel["genart"] = "old" if genart == "old" else ""
            if cardback is not None and ok("cardbacks", cardback):
                sel["cardback"] = cardback
            if theme is not None:
                p["theme"] = theme if (theme == "" or ok("themes", theme)) else p.get("theme")
            self._save()
        return {"ok": True, **self.cos_info(tok)}

    def ack_ach(self, tok):
        p = self.get(tok)
        with self.lock:
            p["ach_new"] = []
            self._save()
        return {"ok": True}

    AVATAR_DIR = os.path.join(DATA, "avatars")

    @staticmethod
    def _pid(tok):
        return hashlib.sha1(("sgs:" + str(tok)).encode()).hexdigest()[:10]

    def avatar_url(self, tok):
        p = self.d.get(tok)
        return f"/avatar/{self._pid(tok)}.jpg?v={p['avatar']}" if p and p.get("avatar") else None

    def set_avatar(self, tok, raw):
        """raw: JPEG 位元組 (前端已縮成 128x128); None = 移除。"""
        p = self.get(tok)
        if not p:
            return {"ok": False, "error": "no profile"}
        os.makedirs(self.AVATAR_DIR, exist_ok=True)
        fn = os.path.join(self.AVATAR_DIR, self._pid(tok) + ".jpg")
        with self.lock:
            if raw is None:
                p.pop("avatar", None)
                try: os.remove(fn)
                except OSError: pass
            else:
                if len(raw) > 120_000 or raw[:3] != bytes([0xFF, 0xD8, 0xFF]):
                    return {"ok": False, "error": "圖片格式不對或太大"}
                open(fn, "wb").write(raw)
                p["avatar"] = int(time.time())
            self._save()
        return {"ok": True, "url": self.avatar_url(tok)}

    def ack_rank(self, tok, nid):
        """玩家看過升降段視窗了: 清掉通知。"""
        p = self.d.get(tok)
        with self.lock:
            if p and p.get("rank_note") and p["rank_note"].get("id") == nid:
                p.pop("rank_note")
                self._save()
        return {"ok": True}

    def lv(self, tok):
        """顯示在名字旁邊的段位標籤 (例: 黃金2)。"""
        p = self.d.get(tok)
        return self.rank_tag(p) if p else self.rank_label(0)

    STREAK_STEP, STREAK_CAP = 3, 15
    WIN_XP = {1: 15, 2: 30, 3: 45, 4: 70, 5: 100}   # 電腦難度 弱/中/強/很強: 打贏給的經驗值

    COIN_LOSS, COIN_DRAW = 8, 12   # 段位模式輸 / 平手 (含內奸次級勝利) 給的遊戲幣;贏 = 贏的積分 ×0.8 + 10 (弱電腦 18 ~ 很強 36)

    def award(self, tok, won, char=None, role=None, win_xp=None, ranked=False, win_rp=None, facts=None, loss_rp=None, secs=0, draw=False, partial=0, coins=None, no_gain=False):
        """回傳 (段位積分變化, 之前段位, 之後段位);休閒模式積分不變 (變化 0)。"""
        p = self.get(tok)
        if not p:
            return None
        gain = self.XP_GAME + ((win_xp if win_xp is not None else self.XP_WIN) if won else 0)
        before = self.rank_label(p.get("rp", 0))
        with self.lock:
            p["playtime"] = p.get("playtime", 0) + max(0, min(int(secs or 0), 6 * 3600))   # 累計遊玩秒數 (單場最多算 6 小時)
            p["xp"] += gain; p["games"] += 1; p["wins"] += 1 if won else 0
            delta = 0; bonus = 0
            if ranked and partial and not won:   # 內奸次級勝利: 加一小部分分數,不算贏也不算輸 (連勝不變)
                old = p.get("rp", 0)
                p["rp"] = old + partial
                delta = partial
                p["rgames"] = p.get("rgames", 0) + 1
            elif ranked and draw:   # 平手: 不算贏也不算輸,段位積分和連勝都不變
                p["rgames"] = p.get("rgames", 0) + 1
            elif ranked:
                old = p.get("rp", 0)
                rs = p.get("rstreak", 0)   # 段位連勝: 連勝中每多贏一場,下一場多給 3 分 (最多 +15);輸一場就歸零
                bonus = min(self.STREAK_CAP, rs * self.STREAK_STEP) if won else 0
                p["rstreak"] = (rs if no_gain else rs + 1) if won else 0
                p["rp"] = max(0, old + ((win_rp or 25) + bonus if won and not no_gain else 0 if won else -(loss_rp or self.LOSS_RP[3])))
                delta = p["rp"] - old
                p["rgames"] = p.get("rgames", 0) + 1; p["rwins"] = p.get("rwins", 0) + (1 if won and not no_gain else 0)
            p["peak_rp"] = max(p.get("peak_rp", 0), p.get("rp", 0))
            gold = 0   # 遊戲幣只有段位模式才有 (棄賽 coins=0)
            if ranked:
                gold = 0 if (won and no_gain) else coins if coins is not None else (round((win_rp or 25) * 0.8) + 10 if won else self.COIN_DRAW if (draw or partial) else self.COIN_LOSS)
                p["coins"] = p.get("coins", 0) + gold
            p["streak"] = p.get("streak", 0) + 1 if won else 0
            p["best_streak"] = max(p.get("best_streak", 0), p["streak"])
            after = self.rank_label(p.get("rp", 0))
            _, _, _, nxt = self.rank(p.get("rp", 0))
            # 每場結束都留一則結果通知 (積分變化 / 升降段 / 離下一段還差多少),玩家的瀏覽器讀到就跳出視窗
            p["rank_note"] = {"from": before, "to": after, "delta": delta, "rp": p.get("rp", 0), "up": delta > 0, "changed": after != before,
                              "ranked": bool(ranked), "coins": gold, "total_coins": p.get("coins", 0), "won": bool(won), "draw": bool(draw), "partial": bool(partial and not won), "streak": p.get("rstreak", 0) if ranked else 0, "bonus": bonus if ranked else 0, "next": self.rank_label(nxt) if nxt is not None else None,
                              "need": (nxt - p.get("rp", 0)) if nxt is not None else 0, "id": int(time.time() * 1000)}
            if char:
                c = p.setdefault("chars", {}).setdefault(char, [0, 0]); c[0] += 1; c[1] += 1 if won else 0
            if role:
                r = p.setdefault("roles", {}).setdefault(role, [0, 0]); r[0] += 1; r[1] += 1 if won else 0
            self._check_ach(p, dict(facts or {}, won=bool(won)))
            self._save()
        return delta, before, self.rank_label(p.get("rp", 0))

    def _save(self):
        try:
            tmp = self.PATH + ".tmp"
            json.dump(self.d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
            os.replace(tmp, self.PATH)
        except OSError:
            pass


PROFILES = Profiles()


class Accounts:
    """帳號: 使用者名稱 + 密碼 (PBKDF2 雜湊) -> uuid (玩家檔案的鍵, 同時是連線憑證)。存在 accounts.json。"""
    PATH = os.path.join(DATA, "accounts.json")
    NAME_RE = re.compile(r"^[A-Za-z0-9_一-鿿぀-ヿ]{2,10}$")

    def __init__(self):
        self.lock = threading.Lock()
        self.fails = {}   # 使用者名稱/IP -> [時間...] (防暴力破解)
        try:
            self.d = json.load(open(self.PATH, encoding="utf-8"))
        except (OSError, ValueError):
            self.d = {}
        changed = False
        for a in self.d.values():   # 舊帳號 (原本只靠 UID 登入) 一律先給預設密碼,請使用者自己改
            if "pw" not in a:
                a["pw"] = self._mk(DEFAULT_PW)
                changed = True
        if changed:
            self._save()
        self.uuids = {a["uuid"]: k for k, a in self.d.items()}
        self.sess = {a["sess"]: a["uuid"] for a in self.d.values() if a.get("sess")}   # 登入階段碼 -> 帳號 uuid (同一帳號只留最新一個)
        self.kicked = set()   # 被新登入踢掉的舊階段碼

    def new_session(self, uuid):
        import secrets
        a = self.d[self.uuids[uuid]]
        if a.get("sess"):
            self.sess.pop(a["sess"], None)
            self.kicked.add(a["sess"])
        a["sess"] = secrets.token_hex(16)
        self.sess[a["sess"]] = uuid
        self._save()
        return a["sess"]

    def resolve(self, sess):
        """瀏覽器送來的是階段碼;換成帳號 uuid (無效就回空字串,視同沒登入)。"""
        return self.sess.get(sess or "", "")

    @staticmethod
    def _hash(pw, salt):
        return hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt), 200_000).hex()

    @classmethod
    def _mk(cls, pw):
        """密碼只存加鹽的 PBKDF2 雜湊,不存明文。d = 還在用預設密碼。"""
        salt = os.urandom(16).hex()
        return {"s": salt, "h": cls._hash(pw, salt), "d": pw == DEFAULT_PW}

    @classmethod
    def _verify(cls, rec, pw):
        import hmac
        return hmac.compare_digest(cls._hash(pw or "", rec["s"]), rec["h"])

    def default_pw(self, tok):
        k = self.uuids.get(tok)
        return bool(k and self.d[k].get("pw", {}).get("d"))

    def change_pw(self, tok, old, new):
        k = self.uuids.get(tok)
        if not k:
            return {"ok": False, "error": "請先登入"}
        if self._blocked("pw:" + k):
            return {"ok": False, "error": "嘗試次數太多,請 5 分鐘後再試"}
        new = new or ""
        if not (MIN_PW <= len(new) <= MAX_PW):
            return {"ok": False, "error": f"新密碼長度要 {MIN_PW}~{MAX_PW} 個字元"}
        if new == DEFAULT_PW:
            return {"ok": False, "error": "不能使用預設密碼"}
        with self.lock:
            a = self.d[k]
            if not self._verify(a["pw"], old):
                self.fails.setdefault("pw:" + k, []).append(time.time())
                time.sleep(0.5)
                return {"ok": False, "error": "舊密碼不正確"}
            a["pw"] = self._mk(new)
            self._save()
        return {"ok": True}

    def is_account(self, tok):
        return tok in self.uuids

    def username(self, tok):
        k = self.uuids.get(tok)
        return self.d[k]["user"] if k else None

    def _blocked(self, key, limit=6):
        now = time.time()
        L = [t for t in self.fails.get(key, []) if now - t < 300]
        self.fails[key] = L
        return len(L) >= limit

    def register(self, user, pw=None, adopt_tok=None, ip=""):
        user = (user or "").strip()
        if not self.NAME_RE.match(user):
            return {"ok": False, "error": "使用者名稱 2~10 字,只能用中英文、數字、底線"}
        if not pw:
            return {"ok": False, "error": "密碼不能留空"}
        if not (MIN_PW <= len(pw) <= MAX_PW):
            return {"ok": False, "error": f"密碼長度要 {MIN_PW}~{MAX_PW} 個字元"}
        import uuid as _uuid
        now = time.time()
        with self.lock:
            L = [t for t in self.fails.get("reg:" + ip, []) if now - t < 3600]
            if len(L) >= 5:   # 同一個 IP 一小時最多註冊 5 個,避免灌帳號
                return {"ok": False, "error": "這個網路最近註冊太多帳號了,請稍後再試"}
            if len(self.d) >= MAX_ACCOUNTS:
                return {"ok": False, "error": "帳號數量已達上限"}
            if user.lower() in self.d:
                return {"ok": False, "error": "這個名稱已被使用"}
            # 若這個瀏覽器原本有舊的訪客檔案 (尚未綁帳號),直接沿用,等級不會丟
            u = adopt_tok if (adopt_tok and adopt_tok in PROFILES.d and adopt_tok not in self.uuids) else str(_uuid.uuid4())
            L.append(now)
            self.fails["reg:" + ip] = L
            self.d[user.lower()] = {"user": user, "uuid": u, "created": int(time.time()), "pw": self._mk(pw)}
            self.uuids[u] = user.lower()
            self._save()
        PROFILES.get(u)
        return {"ok": True, "tok": self.new_session(u), "user": user, "uid": PROFILES.uid(u), "default_pw": pw == DEFAULT_PW}

    def login(self, user, pw=None, ip=""):
        """使用者名稱 + 密碼登入。失敗一律回同一句話 (不透露帳號是否存在)。"""
        raw = (user or "").strip()
        key, via_uid = raw.lower(), False
        if key not in self.d and raw.isdigit() and len(raw) == 8:   # 也可以用 8 位數字 UID 登入 (還是要密碼)
            key = next((k for k, x in list(self.d.items()) if PROFILES.uid(x["uuid"]) == raw), raw)
            via_uid = key in self.d
        if self._blocked("ip:" + ip) or self._blocked("all", 60) or self._blocked("u:" + key, 8):
            return {"ok": False, "error": "嘗試次數太多,請 5 分鐘後再試"}
        a = self.d.get(key)
        if a:
            ok = self._verify(a["pw"], pw)
        else:
            self._hash(pw or "", "00" * 16)   # 帳號不存在也算一次雜湊,避免從回應時間猜出帳號是否存在
            ok = False
        if not ok:
            now = time.time()
            for k in ("ip:" + ip, "all", "u:" + key):
                self.fails.setdefault(k, []).append(now)
            time.sleep(0.5)
            return {"ok": False, "error": "帳號 / UID 或密碼不正確"}
        return {"ok": True, "tok": self.new_session(a["uuid"]), "user": a["user"], "default_pw": bool(a["pw"].get("d")), "via_uid": via_uid}

    def _save(self):
        try:
            tmp = self.PATH + ".tmp"
            json.dump(self.d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
            os.replace(tmp, self.PATH)
            try:
                os.chmod(self.PATH, 0o600)   # 密碼雜湊檔只有擁有者能讀
            except OSError:
                pass
        except OSError:
            pass


import social
DEFAULT_PW = "12345"
MIN_PW, MAX_PW = 8, 64
MAX_ACCOUNTS = 2000
MAX_BODY = 400_000   # 請求本文上限 (頭像 base64 約 160KB)
ACCOUNTS = Accounts()
SOCIAL = social.Social(os.path.join(DATA, "social.json"), ACCOUNTS)
class PublicChat:
    """公共頻道: 所有登入的玩家共用,不分房間 (只留在記憶體,最多 200 則)。"""
    def __init__(self):
        self.lock = threading.Lock()
        self.msgs, self.id, self.t = [], 0, {}

    def say(self, tok, nick, text):
        text = re.sub(r"\s+", " ", str(text or "")).strip()[:200]
        if not text:
            return {"ok": False, "error": "訊息是空的"}
        now = time.time()
        nick = re.sub(r"[\s<>&\"']", "", str(nick or ""))[:10] or ACCOUNTS.username(tok) or "未命名"
        with self.lock:
            if now - self.t.get(tok, 0) < 0.8:
                return {"ok": False, "error": "說話太快了"}
            self.t[tok] = now
            self.id += 1
            self.msgs.append({"id": self.id, "nick": nick, "who": Manager.pid(tok), "acc": ACCOUNTS.uuids.get(tok), "text": text, "t": int(now),
                              "avatar": PROFILES.avatar_url(tok), "style": PROFILES.style(tok), "lv": PROFILES.lv(tok), "dev": PROFILES.dev(tok)})
            del self.msgs[:-200]
        return {"ok": True}

    def since(self, n):
        with self.lock:
            L = [m for m in self.msgs if m["id"] > n] if n else self.msgs[-60:]
            return {"ok": True, "msgs": L, "last": self.id}


PUBCHAT = PublicChat()


def player_public(key):
    """別人看得到的個人資訊 (公開的統計 + UID;不含密碼 / 登入憑證)。"""
    a = ACCOUNTS.d.get((key or "").strip().lower())
    if not a:
        return {"ok": False, "error": "找不到這位玩家"}
    t = a["uuid"]
    p = PROFILES.d.get(t) or {}
    rp = p.get("rp", 0)
    lv = PROFILES.level(p.get("xp", 0))
    _nm, _sub, lo, hi = PROFILES.rank(rp)
    return {"ok": True, "uid": PROFILES.uid(t), "rp_lo": lo, "rp_next": hi, "next_rank": PROFILES.rank_label(hi) if hi is not None else None, "user": a["user"], "dev": PROFILES.dev(t), "avatar": PROFILES.avatar_url(t), "style": PROFILES.style(t),
            "rank": PROFILES.rank_tag(p), "pres": p.get("pres", 0), "rp": rp, "rstreak": p.get("rstreak", 0), "streak_bonus": min(PROFILES.STREAK_CAP, p.get("rstreak", 0) * PROFILES.STREAK_STEP), "streak_cap": PROFILES.STREAK_CAP, "streak_step": PROFILES.STREAK_STEP, "level": lv, "games": p.get("games", 0), "wins": p.get("wins", 0),
            "rgames": p.get("rgames", 0), "rwins": p.get("rwins", 0), "playtime": p.get("playtime", 0), "ach": len(p.get("ach", {})),
            "chars": sorted(([n, v[0], v[1]] for n, v in p.get("chars", {}).items()), key=lambda x: (-x[1], -x[2]))[:3]}


def _card(key):   # 好友列表用: 頭貼 / 框 / 特效 / 段位 / 等級
    a = ACCOUNTS.d.get(key)
    t = a["uuid"] if a else ""
    p = PROFILES.d.get(t) or {}
    return {"avatar": PROFILES.avatar_url(t), "style": PROFILES.style(t), "rank": PROFILES.lv(t), "rp": p.get("rp", 0), "playtime": p.get("playtime", 0), "level": PROFILES.level(p.get("xp", 0)), "dev": PROFILES.dev(t)}
SOCIAL.card = _card
SOCIAL.in_room = lambda k: friend_where(k)
SOCIAL.uid_key = lambda uid: next((k for k, a in list(ACCOUNTS.d.items()) if PROFILES.uid(a["uuid"]) == uid), None)


def leaderboard(me=""):
    """玩家排行榜: 所有有帳號的玩家 (段位、積分、段位模式的勝場 / 場數;休閒模式不計)。"""
    rows = []
    rk = SOCIAL.remarks(SOCIAL.key_of(me)) if me else {}
    for k, acc in list(ACCOUNTS.d.items()):
        t = acc["uuid"]
        p = PROFILES.d.get(t)
        if not p:
            continue
        rows.append({"name": rk.get(k) or acc["user"], "acc": acc["user"].lower(), "me": t == me, "lv": PROFILES.rank_tag(p), "pres": p.get("pres", 0), "rp": p.get("rp", 0), "rp_next": PROFILES.rank(p.get("rp", 0))[3], "xp": p["xp"],
                     "games": p.get("rgames", 0), "wins": p.get("rwins", 0), "playtime": p.get("playtime", 0), "avatar": PROFILES.avatar_url(t), "style": PROFILES.style(t), "dev": PROFILES.dev(t)})
    return {"rows": rows}
OPEN_API = {"/api/about", "/api/rooms", "/api/cardcat", "/api/lessons", "/api/cosmetics", "/api/i18n", "/api/roster", "/api/me", "/api/login", "/api/register"}


class AbortGame(Exception):
    pass


class Manager:
    def __init__(self):
        self.lock = threading.Lock()
        self.plock = threading.RLock()
        self.room_name, self.owner, self.created = "房間", None, time.time()
        self.act = self.created      # 房間裡最後一次有人操作 (不是單純開著網頁) 的時間
        self.over_at = None          # 這局結束的時間 (新局開始會清掉)
        self.game = None
        self.thread = None
        self.rec = Recorder()
        self.humans = set()
        self.claims = {}; self.ips = {}
        self.seen = {}    # tok -> 最後一次連線時間 (算目前在線人數)
        self.kicked = {}  # tok -> 解除時間 (被房主踢出)
        self.cap = 0       # 房間人數上限 (0 = 不限; 含觀戰的人)
        self.unlisted = False   # 不公開房間: 不顯示在大廳列表 (知道房號 / 被邀請的人還是進得來)
        self.solo = False  # 單人模式房間: 只有建立者進得去,不顯示在大廳,離開就刪除
        self.pw = None    # 房間密碼 (加鹽雜湊;None = 沒有密碼)
        self.allowed = set()   # 輸入過密碼 / 被邀請的玩家 (uuid)
        self.alive = {}   # tok -> 目前是否視為在線 (斷線偵測用)
        self.events = []  # 給所有人的通知 (斷線 / 重連 / 換房主)
        self.ev_id = 0
        self.nicks = {}   # tok -> 暱稱 (朋友入座時可自己取名)
        self.host = None
        self.public = False         # 公共房間: 房主下線就清空房主,不自動讓給別人
        self.host_cleared = False
        self.lobby = False
        self.picking, self.offers, self.picks = False, {}, {}
        self.chat, self.chat_id, self.chat_t = [], 0, {}   # 聊天室
        self.cfg = {}
        self.paused = False
        self.speed = 0.35
        self.error = None
        self.pending = None
        self.multi, self.multi_res, self.multi_win = {}, {}, None   # 同時詢問多人 (瀕死: 先出桃的人救)
        self._multi_ev = threading.Event()
        self.abort = False
        self._ans = None
        self._ans_ev = threading.Event()
        self._step_ev = threading.Event()
        self._req = 0

    # ---------- 建立新對局 ----------
    def is_host(self, tok):
        """尚無對局/無房主時任何人都可以;否則只有房主。"""
        return not self.host or tok == self.host

    def end_game(self, tok, force=False):
        """休閒局: 隨時可以強制結束這一局 (房主 / 公共房間的任何人 / 坐在位子上的人)。段位局要用棄賽。"""
        if not force and (self.cfg or {}).get("ranked") and self.game_active():
            return {"ok": False, "error": "段位局不能強制結束,請用棄賽"}
        if not force and not (self.is_host(tok) or self.seat_of(tok) is not None):
            return {"ok": False, "error": "only host"}
        if self.game is None and not self.lobby:
            return {"ok": True}
        with self.plock:
            self.abort = True
            self._ans_ev.set(); self._step_ev.set(); self._multi_ev.set()
            th = self.thread
            if th and th.is_alive() and th is not threading.current_thread():
                th.join(timeout=3)
            self.abort = False
            self._ans_ev.clear(); self._step_ev.clear(); self._multi_ev.clear()
            self.game, self.thread, self.rec = None, None, Recorder()
            self.humans, self.claims = set(), {}
            self.picking, self.offers, self.picks = False, {}, {}
            self.cfg, self.paused, self.error, self.pending, self.lobby = {}, False, None, None, False
            self.multi, self.multi_res, self.multi_win = {}, {}, None
            self.over_at, self._ans, self.les = None, None, None
            if not force:
                self._event(f"⛔ {self._name_of(tok)} 強制結束了這一局", "bad", tok)
        return {"ok": True}

    def rematch(self, tok):
        """依照上一局的設定再來一局 (只換種子,武將若原本是隨機就重新抽)。"""
        if not self.is_host(tok):
            return {"ok": False, "error": "只有房主可以再來一局"}
        if not getattr(self, "cfg", None):
            return {"ok": False, "error": "還沒有上一局的設定"}
        cfg = {k: v for k, v in self.cfg.items() if k not in ("n", "want", "pool", "chars_", "seed")}
        cfg["tok"], cfg["seed"], cfg["speed"] = tok, None, self.speed
        return self.new_game(cfg)

    def new_game(self, cfg):
        if not self.is_host(cfg.get("tok")):
            return {"ok": False, "error": "only host"}
        if self.game_active() and (self.cfg or {}).get("ranked"):
            if not self.ranked_abandoned():
                return {"ok": False, "error": "ranked game in progress"}   # 段位局打完前不能開新遊戲 (要先棄賽)
            for t in list(self.claims.values()):   # 入座的人都離開很久了: 房主可以收掉這局,離開的人照棄賽算輸
                self.forfeit(t)
        lesson = lessons.by_id(cfg.get("lesson")) if cfg.get("lesson") else None
        if lesson:   # 教學關卡: 人數 / 武將 / 主公座位都由關卡決定,固定休閒、不計經驗
            cfg = dict(cfg, players=lesson["n"], human="0", humans=[], ranked=False, practice=True, chars=[c or "none" for c in lesson["chars"]],
                       lord=lesson["lord"], variant=0, mode="normal", role_mode="normal", base_hp=4, diffs=[], difficulty=2)
        if cfg.get("ranked"):   # 段位模式: 固定規則 (正常模式 / 4 體力 / 隨機主公 / 正常身分)
            if cfg.get("human") in (None, "", "spectate") and not cfg.get("humans"):
                return {"ok": False, "error": "段位模式至少要有一個人參戰"}
            cfg = dict(cfg, spec_all=False, players=max(4, int(cfg.get("players", 5))), mode="normal", base_hp=4, lord="random", chars=["" for _ in (cfg.get("chars") or [])], role_mode="normal")
        self.abort = True
        self._ans_ev.set()
        self._step_ev.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)
        self.abort = False
        self._ans_ev.clear()
        self._step_ev.clear()
        n = int(cfg.get("players", 5))
        human = cfg.get("human")
        human = None if human in (None, "", "spectate") else int(human)
        seed = cfg.get("seed")
        seed = random.randrange(10 ** 6) if seed in (None, "") else int(seed)
        rng = random.Random(seed)
        # 武將: ''=隨機 / 'none'=無武將 / 名稱
        want = list(cfg.get("chars") or [""] * n) + [""] * n
        want = want[:n]
        used = {w for w in want if w in ROSTER}
        pool = [x for x in ROSTER if x not in used]
        rng.shuffle(pool)   # 隨機武將: 每人抽 3 張 (彼此不重複) 再選 1 張,見 start()
        self.picking, self.offers, self.picks = False, {}, {}
        self.rec = Recorder()
        humans = {int(x) for x in (cfg.get("humans") or []) if 0 <= int(x) < n}
        if human is not None and human < n:
            humans.add(human)
        self.humans = humans
        self.claims = {}
        starter = cfg.get("tok")
        self.host = None if self.public else starter   # 公共房間沒有房主,任何人都能操作
        self.host_cleared = False
        if starter and human is not None and human < n:
            self.claims[human] = starter
        self.cfg = dict(cfg, seed=seed, n=n, want=want, pool=pool)
        self.paused = False
        self.speed = max(0.05, float(cfg.get("speed", 0.35)))   # 每步延遲最低 0.05 秒
        self.error = None
        self.pending = None
        self.game = None
        self.lobby = True
        if humans <= set(self.claims):  # 純觀戰或只有房主一人: 直接開始
            self.start(starter, force=True)
        return {"ok": True, "seed": seed}

    def say(self, tok, text):
        name = self.nicks.get(tok)
        text = re.sub(r"\s+", " ", str(text or "")).strip()[:200]
        now = time.time()
        if not tok or not name:
            return {"ok": False, "error": "先取暱稱才能聊天"}
        if not text:
            return {"ok": False, "error": "訊息是空的"}
        if now - self.chat_t.get(tok, 0) < 0.5:
            return {"ok": False, "error": "說話太快了"}
        self.chat_t[tok] = now
        self.chat_id += 1
        self.chat.append({"id": self.chat_id, "nick": name, "seat": self.seat_of(tok), "host": tok == self.host,
                          "who": self.pid(tok), "text": text, "t": int(now),
                          "avatar": PROFILES.avatar_url(tok), "style": PROFILES.style(tok), "lv": PROFILES.lv(tok),
                          "spec": self._is_spec(tok)})
        del self.chat[:-200]
        self.prune_chat(now)
        return {"ok": True}

    CHAT_KEEP = 86400   # 公共房間的訊息最多留一天

    def prune_chat(self, now=None):
        """公共房間: 超過一天的訊息刪掉 (私人房間的聊天跟著房間走,房間刪除就一起沒了)。"""
        if self.public and self.chat:
            cut = (now or time.time()) - self.CHAT_KEEP
            if self.chat[0].get("t", 0) < cut:
                self.chat = [m for m in self.chat if m.get("t", 0) >= cut]

    def _is_spec(self, tok):
        """觀戰者: 開局後沒有座位的人,或座位上的武將已陣亡的人。"""
        seat = self.seat_of(tok)
        if self.game is None and not self.picking:
            return False
        if seat is None:
            return True
        if self.game is None:
            return False
        return 0 <= seat < len(self.game.players) and not self.game.players[seat].alive


    def chat_since(self, n, tok=None):
        self.prune_chat()
        return {"chat": [m for m in self.chat if m["id"] > n], "chat_total": self.chat_id, "me": self.pid(tok) if tok else None}

    def seat_of(self, tok):
        for s, t in self.claims.items():
            if tok and t == tok:
                return s
        return None

    def set_nick(self, tok, name):
        name = re.sub(r"[\s<>&\"']", "", str(name or ""))[:10]
        if tok:
            if self.game_active() and tok in self.nicks:   # 遊戲開始後不能改暱稱 (首次取名除外)
                return {"ok": False, "error": "遊戲進行中不能改暱稱", "name": self.nicks[tok]}
            if name:
                self.nicks[tok] = name
            else:
                self.nicks.pop(tok, None)
        return {"ok": True, "name": name}

    def touch(self, tok):
        if tok:
            now = time.time()
            if tok not in self.seen:
                self._event(f"→ {self._name_of(tok)} 進入房間", "ok", tok)
            self.seen[tok] = now
            if not self.host and not self.host_cleared and not self.public:   # 最先連線的人成為房主 (公共房間沒有房主)
                self.host = tok
            self.presence()

    OFFLINE_AFTER = 25   # 超過幾秒沒連線視為斷線

    def _name_of(self, tok):
        return self.nicks.get(tok) or ACCOUNTS.username(tok) or "未命名"

    def can_enter(self, tok):
        """沒設密碼的房間誰都能進;有密碼的要輸入過密碼、被邀請、或是房間建立者。"""
        if self.solo:
            return tok == self.owner
        return not self.pw or tok == self.owner or tok in self.allowed

    def is_kicked(self, tok):   # 被踢的人還沒收到通知 (收到一次就清掉,可以馬上再進來,沒有冷卻)
        return tok in self.kicked

    def pop_kicked(self, tok):
        return self.kicked.pop(tok, None) is not None

    def kick(self, tok, to_id):
        """房主踢人: 對方離開房間 (座位交給電腦,遊戲不中斷),一段時間內不能再進來。"""
        if not self.host:
            return {"ok": False, "error": "這個房間目前沒有房主 (公共房間的房主下線後會清空),不能踢人"}
        if not tok or tok != self.host:
            return {"ok": False, "error": "只有房主能踢人"}
        target = next((t for t in list(self.seen) if self.pid(t) == to_id), None)
        if target is None:
            return {"ok": False, "error": "對方已不在房間"}
        if target == tok:
            return {"ok": False, "error": "不能踢自己"}
        if self.game_active() and (self.cfg or {}).get("ranked"):   # 段位局進行中: 房主不能踢人 (不然可以把輸家 / 對手踢掉躲掉扣分)
            return {"ok": False, "error": "段位模式進行中不能踢人"}
        name = self._name_of(target)
        seat = self.seat_of(target)
        if seat is not None:
            if self.game_active():
                pl = self.game.players[seat]
                del self.claims[seat]
                pl.agent = Observed(make_ai(self._level(self.cfg, seat)), self.rec)
                with self.lock:
                    if self.pending and self.pending.get("seat") == seat:
                        self._ans = list(getattr(self, "_pend_default", None) or [])
                        self._ans_ev.set()
            else:
                self.claims.pop(seat, None)
        with self.plock:
            self.seen.pop(target, None)
            self.alive.pop(target, None)
            self.kicked[target] = True
            self._event(f"🚪 {name} 被房主踢出了房間", "bad")
        return {"ok": True, "name": name}

    def leave(self, tok):
        """主動離開房間 (回大廳): 不算斷線,不通知房內其他人;房主離開時交給別人。段位局打到一半離開 = 棄賽。"""
        if tok and (self.cfg or {}).get("ranked") and self.game_active() and self.seat_of(tok) is not None:
            self.forfeit(tok)
        elif tok and self.game_active() and self.seat_of(tok) is not None and not any(t != tok and time.time() - self.seen.get(t, 0) < self.OFFLINE_AFTER for t in self.claims.values()):
            self.end_game(tok)   # 休閒局: 最後一個入座的人離開 = 這局沒人玩了,直接結束
        with self.plock:
            if tok not in self.seen:
                return
            now = time.time()
            self.seen.pop(tok, None)
            self.alive.pop(tok, None)
            self._event(f"← {self._name_of(tok)} 離開了房間", "bad", tok)
            if tok == self.host:
                if self.public:
                    self.host, self.host_cleared = None, True
                else:
                    cand = [t for t, x in self.seen.items() if now - x < self.OFFLINE_AFTER]
                    if cand:
                        self.host = random.choice(cand)
                        self._event(f"👑 房主離開了,房主已隨機讓給 {self.nicks.get(self.host) or '未命名'}", "host")
            self._maybe_reset_public(True)

    def _maybe_reset_public(self, left=False):
        """公共房間: 唯一的真人離開 (或掉線超過 25 秒) 後,整個房間重置 (停掉對局、清空入座 / 設定 / 聊天),下一個進來的人看到全新的房間。
        段位局進行中的掉線不在這裡處理 (照原本的棄賽流程);主動離開 (left) 已經先棄賽了。"""
        if not self.public:
            return
        now = time.time()
        if any(now - x < self.OFFLINE_AFTER for x in self.seen.values()):
            return
        if not (self.game is not None or self.lobby or self.claims or self.cfg or self.chat or self.events):
            return   # 已經是乾淨的房間
        if not left and self.game_active() and (self.cfg or {}).get("ranked"):
            return
        self.abort = True
        self._ans_ev.set(); self._step_ev.set(); self._multi_ev.set()
        th = self.thread
        if th and th.is_alive() and th is not threading.current_thread():
            th.join(timeout=3)
        self.abort = False
        self._ans_ev.clear(); self._step_ev.clear(); self._multi_ev.clear()
        self.game, self.thread, self.rec = None, None, Recorder()
        self.humans, self.claims, self.ips, self.kicked, self.alive = set(), {}, {}, {}, {}
        self.seen, self.nicks, self.events, self.ev_id = {}, {}, [], 0
        self.host, self.host_cleared, self.lobby = None, False, False
        self.picking, self.offers, self.picks = False, {}, {}
        self.chat, self.chat_id, self.chat_t = [], 0, {}
        self.cfg, self.paused, self.speed, self.error, self.pending = {}, False, 0.35, None, None
        self.multi, self.multi_res, self.multi_win = {}, {}, None
        self.over_at, self._ans, self._req = None, None, 0
        self.act = now

    def _event(self, text, kind="info", actor=None):   # actor: 這件事的當事人 (自己不用被通知)
        self.ev_id += 1
        self.events.append({"id": self.ev_id, "text": text, "kind": kind, "who": self.pid(actor) if actor else None})
        del self.events[:-30]

    def _who(self, tok):
        seat = next((s for s, t in self.claims.items() if t == tok), None)
        nm = self.nicks.get(tok) or "未命名"
        return f"{nm}(座位 {seat})" if seat is not None else nm

    def _active_elsewhere(self, tok, now):
        return any(m is not self and now - m.seen.get(tok, 0) < self.OFFLINE_AFTER for m in list(ROOMS.values()))

    def presence(self):
        """偵測斷線 / 重連;房主斷線時隨機讓給一位仍在線的人。"""
        with self.plock:
            now = time.time()
            for tok, ts in list(self.seen.items()):
                up = now - ts < self.OFFLINE_AFTER
                was = self.alive.get(tok, True)
                if was and not up and self._active_elsewhere(tok, now):   # 人已經換到別的房間了: 不是斷線,當作離開
                    self.seen.pop(tok, None)
                    self.alive.pop(tok, None)
                    self._event(f"← {self._name_of(tok)} 離開了房間", "bad", tok)
                    if tok == self.host:
                        if self.public:
                            self.host, self.host_cleared = None, True
                        else:
                            cand = [t for t, x in self.seen.items() if now - x < self.OFFLINE_AFTER]
                            if cand:
                                self.host = random.choice(cand)
                                self._event(f"👑 房主離開了,房主已隨機讓給 {self.nicks.get(self.host) or '未命名'}", "host")
                    continue
                if was and not up:
                    self.alive[tok] = False
                    self._event(f"⚠ {self._who(tok)} 斷線了", "warn")
                    if tok == self.host and self.public:
                        self.host, self.host_cleared = None, True
                        self._event("👑 房主下線,公共房間的房主已清空", "host")
                    elif tok == self.host:
                        cand = [t for t, x in self.seen.items() if t != tok and now - x < self.OFFLINE_AFTER]
                        if cand:
                            self.host = random.choice(cand)
                            self._event(f"👑 房主斷線,房主已隨機讓給 {self.nicks.get(self.host) or '未命名'}", "host")
                elif not was and up:
                    self.alive[tok] = True
                    self._event(f"✅ {self._who(tok)} 重新連線", "ok")
            # 房主不在房間 (斷線 / 離開時房裡沒有別人,之後才有人進來;或是已經沒連線很久) 又沒交給別人: 現在補上,優先交給入座的玩家
            h = self.host
            if h and not self.public and now - self.seen.get(h, 0) >= self.OFFLINE_AFTER:
                cand = [t for t, x in self.seen.items() if t != h and now - x < self.OFFLINE_AFTER]
                if cand:
                    seated = [t for t in cand if self.seat_of(t) is not None]
                    self.host = random.choice(seated or cand)
                    self._event(f"👑 房主不在房間,房主已讓給 {self.nicks.get(self.host) or self._name_of(self.host)}", "host")
            self._maybe_reset_public()

    def online(self):
        now = time.time()
        return [{"id": self.pid(t), "name": self.nicks.get(t, ""), "host": t == self.host, "lv": PROFILES.lv(t), "dev": PROFILES.dev(t), "acc": ACCOUNTS.uuids.get(t), "avatar": PROFILES.avatar_url(t), "style": PROFILES.style(t),
                 "seat": self.seat_of(t), "spec": self._is_spec(t)}
                for t, ts in self.seen.items() if now - ts < 6]

    @staticmethod
    def pid(tok):   # 公開用代號 (不能洩漏 tok 本身,它等於身分憑證)
        return hashlib.sha1(("sgs:" + str(tok)).encode()).hexdigest()[:10]

    def transfer_host(self, tok, to_id):
        if tok != self.host:
            return {"ok": False, "error": "only host"}
        if self.pid(tok) == to_id:
            return {"ok": False, "error": "不能把房主讓給自己"}
        now = time.time()
        for t, ts in self.seen.items():
            if self.pid(t) == to_id and now - ts < 6 and t != tok:
                self.host = t
                return {"ok": True, "name": self.nicks.get(t, "")}
        return {"ok": False, "error": "對方已離線"}

    def host_name(self):
        return self.nicks.get(self.host, "") if self.host else None

    def forfeit(self, tok):
        """段位模式棄賽: 算輸 (扣分),座位交給電腦接手,這個人變成觀戰者。"""
        seat = self.seat_of(tok)
        if not tok or seat is None or not self.game_active() or not (self.cfg or {}).get("ranked"):
            return {"ok": False, "error": "cannot forfeit"}
        g = self.game
        pl = g.players[seat]
        lv = [self._level(self.cfg, i) for i in range(len(g.players)) if i not in self.claims]
        r = PROFILES.award(tok, False, pl._char.name if getattr(pl, "_char", None) else None, pl.role, None, True, None, {"hp": pl.hp, "alive": pl.alive}, loss_rp=round(1.5 * (Profiles.LOSS_RP.get(round(sum(lv) / len(lv)), 25) if lv else 25)), secs=time.time() - getattr(self, "game_t0", time.time()), coins=0)
        who = self.nicks.get(tok) or "未命名"
        if r:
            d, b, a = r
            self._event(f"🏳 {who} 棄賽,段位積分 {'-0' if d == 0 else format(d, '+d')} ({b}" + (f" → {a})" if a != b else ")"), "bad")   # 棄賽一定是輸: 紅底,已經最低分就寫 -0
        del self.claims[seat]
        pl.agent = Observed(make_ai(self._level(self.cfg, seat)), self.rec)
        with self.lock:   # 正卡在等這個人回答: 用預設答案放行
            if self.pending and self.pending.get("seat") == seat:
                self._ans = list(getattr(self, "_pend_default", None) or [])
                self._ans_ev.set()
        return {"ok": True}

    def game_active(self):
        return self.game is not None and not self.lobby and self.game.winner is None

    ABANDON_AFTER = 120   # 段位局入座的人全都超過這麼久沒連線: 視為丟下這局不管,房主可以直接開新遊戲

    def ranked_abandoned(self):
        if not (self.game_active() and (self.cfg or {}).get("ranked")):
            return False
        now = time.time()
        return all(now - self.seen.get(t, 0) >= self.ABANDON_AFTER for t in self.claims.values())

    def seat_avatars(self):
        return {s: u for s, t in self.claims.items() if (u := PROFILES.avatar_url(t))}

    def seat_styles(self):
        out = {s: PROFILES.style(t) for s, t in self.claims.items()}
        g = self.game
        if g is not None:   # 電腦玩家: 每局隨機套用頭像框 / 特效 / 玩家框 / 卡面 (同一局固定不變)
            if getattr(self, "_bot_gid", None) != id(g):
                rnd = random.Random(id(g))
                pick = lambda L, none: rnd.choice([x["id"] for x in L if x["id"]] + [""] * none)
                self._bot_gid = id(g)
                self._bot_sty = {}
                for i in range(len(g.players)):
                    bx = pick(cosmetics.BOXES, 2)
                    an = ""
                    if self._level(self.cfg, i) >= 5:   # 只有「極強」的電腦才會隨機帶動畫特效: 有玩家框的 5 成機率用配對的動畫,其餘 2 成隨機一組 (每局大約一半的電腦會有)
                        an = cosmetics.BOX_ANIM.get(bx, "") if bx and rnd.random() < .5 else ""
                        if not an and rnd.random() < .2:
                            an = rnd.choice([x["id"] for x in cosmetics.ANIMS if x["id"]])
                    self._bot_sty[i] = {"fr": pick(cosmetics.FRAMES, 1), "fx": pick(cosmetics.EFFECTS, 3), "bx": bx, "cb": rnd.choice([x["id"] if x["id"] != "classic" else "" for x in cosmetics.CARDBGS]), "bk": "", "an": an}
            for i, st in self._bot_sty.items():
                out.setdefault(i, st)
        return out

    def set_chain_pref(self, tok, on):
        if not hasattr(self, "chain_pref"):
            self.chain_pref = {}
        self.chain_pref[tok] = bool(on)
        if self.game is not None:
            self.game.chain_all = {s for s, t in self.claims.items() if self.chain_pref.get(t)}

    def seat_levels(self):
        return {s: PROFILES.lv(t) for s, t in self.claims.items()}

    def seat_names(self):
        return {s: self.nicks[t] for s, t in self.claims.items() if t in self.nicks}

    def claim(self, tok, seat, name=None, ip=""):
        if name is not None:
            self.set_nick(tok, name)
        if not tok or not self.lobby or self.game is not None or self.picking:
            return {"ok": False, "error": "not in lobby"}
        for s in [s for s, t in self.claims.items() if t == tok]:
            del self.claims[s]
        if seat is not None:
            seat = int(seat)
            if seat not in self.humans or seat in self.claims:
                return {"ok": False, "error": "seat unavailable"}
            self.claims[seat] = tok
            if ip:
                self.ips[tok] = ip   # 段位局防刷: 記下入座者的連線 IP
        return {"ok": True}

    def start(self, tok, force=False):
        if not force and (self.game is not None or self.picking or not self.is_host(tok)):
            return {"ok": False, "error": "only host can start"}
        cfg, n = self.cfg, self.cfg["n"]
        if cfg.get("ranked") and not self.claims:   # 段位模式: 沒有任何人按「我要參戰」就不能開始 (不然變成全電腦對打)
            return {"ok": False, "error": "段位模式至少要有一個人參戰"}
        self.humans = set(self.claims)   # 沒人坐的真人座位由 AI 接手
        if cfg.get("ranked"):   # 段位模式: 電腦難度由入座真人的平均段位決定,不能自己調
            rps = [PROFILES.get(t).get("rp", 0) if PROFILES.get(t) else 0 for t in self.claims.values()]
            avg = sum(rps) / len(rps) if rps else 0
            cfg["difficulty"], cfg["diffs"] = Profiles.RANK_DIFF.get(Profiles.rank(avg)[0], 3), []
        pool = list(cfg["pool"])
        self.pick_rng = random.Random(cfg["seed"] + 1)
        lord = cfg.get("lord", "random")
        self.lord_seat = random.Random(cfg["seed"] + 2).randrange(n) if lord in (None, "", "random") else int(lord)
        # 隨機武將: 每人抽 3 張 (彼此不重複),大家同時選 1 張
        self.offers = {i: [pool.pop() for _ in range(min(3, len(pool)))] for i, w in enumerate(cfg["want"]) if w == ""}
        self.picks = {i: None for i, o in self.offers.items() if not o}
        self.picking = True
        self.pick_deadline = time.time() + self.PICK_SECONDS   # 選武將倒數: 時間到沒選的人隨機
        return self._advance()

    def _advance(self):
        """選武將: 大家同時選。AI 馬上選好;真人各自挑,全部選完就開始。"""
        for seat, offer in self.offers.items():
            if seat not in self.picks and seat not in self.claims:
                self.picks[seat] = self.pick_rng.choice(offer)
        if all(i in self.picks for i in self.offers):
            self.picking = False
            return self._launch()
        return {"ok": True, "picking": True}

    def pick(self, tok, name):
        seat = self.seat_of(tok)
        if not self.picking or seat is None or seat not in self.offers or seat in self.picks:
            return {"ok": False, "error": "不能選"}
        if name not in self.offers[seat]:
            return {"ok": False, "error": "不在你抽到的三張裡"}
        self.picks[seat] = name
        return self._advance()

    PICK_SECONDS = 60

    def _pick_expire(self):
        dl = getattr(self, "pick_deadline", None)
        if self.picking and dl and time.time() >= dl:
            self.pick_deadline = None
            for seat, offer in self.offers.items():
                if seat not in self.picks:
                    self.picks[seat] = random.choice(offer)
                    self._event(f"⏰ 座位 {seat} 選武將超時,已隨機選擇", "warn")
            self._advance()

    def pick_view(self, tok):
        """大廳狀態: 只有自己看得到自己抽到的三張;其他人只看得到還在等誰 (選了什麼要到開局才公開)。"""
        self._pick_expire()
        if not self.picking:
            return {}
        seat = self.seat_of(tok)
        data = {d["name"]: d for d in ROSTER_DATA}
        out = {"picking": True, "pick_wait": sorted(i for i in self.offers if i not in self.picks),
               "pick_left": max(0, round(getattr(self, "pick_deadline", None) - time.time(), 1)) if getattr(self, "pick_deadline", None) else None}
        out["pick_spec"] = seat is None   # 沒入座的旁觀者: 畫面不要寫「你已選好武將」
        if seat is not None and seat in self.offers and seat not in self.picks:
            out["pick"] = {"seat": seat, "offers": [data[n] for n in self.offers[seat] if n in data]}
        return out

    def _launch(self):
        cfg, n = self.cfg, self.cfg["n"]
        want = cfg["want"]
        self.over_at = None
        chars = []
        for i, w in enumerate(want):
            if w == "none":
                chars.append(None)
            elif w in ROSTER:
                chars.append(ROSTER[w]())
            else:
                nm = self.picks.get(i)
                chars.append(ROSTER[nm]() if nm in ROSTER else None)
        cfg["chars_"] = chars
        agents = []
        lesson = lessons.by_id(cfg.get("lesson")) if cfg.get("lesson") else None
        self.les = {"id": lesson["id"], "step": 0, "done": False, "manual": False} if lesson else None
        for i in range(n):
            if i in self.claims:
                agents.append(HumanAgent(self, i))
            elif lesson and not lesson["real_ai"]:
                ps = lesson["players"][i]
                agents.append(lessons.ScriptAgent(ps.get("plan", ()), ps.get("resp", ())))
            else:
                agents.append(Observed(make_ai(self._level(cfg, i)), self.rec))
        g = Game(agents, max_rounds=100, seed=cfg["seed"], chars=cfg["chars_"], role_variant=int(cfg.get("variant", 0)), lord_seat=self.lord_seat,
                 mode="shuffle" if cfg.get("mode") == "shuffle" else "normal", role_mode=cfg.get("role_mode") or "normal", base_hp=int(cfg.get("base_hp") or 4))
        g.on_log = self.on_log
        if lesson:
            g.scn = lambda gg, L=lesson: lessons.apply(gg, L)
        self.game, self.lobby = g, False
        self.game_t0 = time.time()
        self.thread = threading.Thread(target=self._run, args=(g,), daemon=True)
        self.thread.start()
        return {"ok": True}

    @staticmethod
    def _level(cfg, i):
        """第 i 號座位的電腦難度 (1~5):個別設定優先,沒有就用整體難度。"""
        try:
            return max(1, min(5, int((cfg.get("diffs") or [])[i])))
        except (IndexError, TypeError, ValueError):
            return max(1, min(5, int(cfg.get("difficulty", 3) or 3)))

    def _award(self, g):
        """對局結束: 有入座的真人依勝負得經驗值。"""
        w = g.winner
        camp = lambda r: "主公陣營" if r in ("主公", "忠臣") else r
        noroles = getattr(g, "noroles", False)
        rps = {t: (PROFILES.get(t) or {}).get("rp", 0) for s, t in self.claims.items() if s in self.humans and s < len(g.players)}   # 結算前各真人的積分
        for seat, tok in self.claims.items():
            if seat in self.humans and seat < len(g.players):
                pl = g.players[seat]
                ai_present = any(i not in self.claims for i in range(len(g.players)))
                lv = [self._level(self.cfg, i) for i in range(len(g.players)) if i not in self.claims]
                wx = Profiles.WIN_XP.get(round(sum(lv) / len(lv)), 45) if ai_present else None   # 電腦難度取平均
                wrp = Profiles.WIN_RP.get(round(sum(lv) / len(lv)), 25) if ai_present else 25
                ranked = bool(self.cfg.get("ranked"))
                multi = False
                if ranked and self.ips.get(tok) and sum(1 for s2, t2 in self.claims.items() if s2 in self.humans and self.ips.get(t2) == self.ips.get(tok)) > 1:
                    multi = True   # 同一個 IP 有兩個以上帳號在同一場段位局: 贏了不加分、輸了照扣 (防止開小帳互相送分)
                    self._event(f"⚠ {self.nicks.get(tok) or '未命名'}: 同一個網路有多個帳號在這場段位局,這場贏了不加分、輸了照扣", "warn")
                lrp = Profiles.LOSS_RP.get(round(sum(lv) / len(lv)), 25) if ai_present else 25   # 輸的扣分 = 同難度贏的加分
                others = [v for t, v in rps.items() if t != tok]
                if others:   # 有其他真人: 對手平均段位比我高 → 贏得多、輸扣得少;比我低 → 贏得少、輸扣得多 (±50%)
                    diff = sum(others) / len(others) - rps.get(tok, 0)
                    wrp = round(wrp * max(0.5, min(1.5, 1 + diff / Profiles.SPREAD)))
                    lrp = round(lrp * max(0.5, min(1.5, 1 - diff / Profiles.SPREAD)))
                if len(g.players) <= 3:   # 2~3 人 (沒有隊友,只能靠自己): 贏的經驗加倍
                    wx = 2 * (wx if wx is not None else Profiles.XP_WIN)
                draw = str(w).startswith("平手")
                team = getattr(g, "team_mode", False)
                rw, rl = Profiles.role_mult(len(g.players), pl.role) if not (noroles or team) else (1.0, 1.0)
                won = (pl.idx == g.solo_winner) if getattr(g, "solo_winner", None) is not None else (w == f"P{pl.idx}") if noroles else (w == f"{pl.side}方") if team else (camp(pl.role) == w and (pl.role != "內奸" or pl.alive))   # 曹植七輪獨自勝利: 只有曹植那位算贏
                if not won and not draw and pl.alive and pl.role != "內奸":
                    rl *= 0.8   # 輸了但自己撐到最後: 扣分打 8 折
                partial = round(wrp * rw * 0.3) if (not won and not draw and pl.role == "內奸" and getattr(pl, "duel1", False)) else 0   # 內奸撐到和主公單挑才輸: 次級勝利,給贏分的 30%
                if draw:
                    partial = max(1, round(wrp * rw * 0.4))   # 平手: 加分,但只有贏的 40% (不算勝場、連勝不變)
                lrp = lrp * Profiles.loss_tier(rps.get(tok, 0))   # 分段式期望值: 依自己結算前的段位調整輸的扣分
                wrp, lrp = max(1, round(wrp * rw)), max(1, round(lrp * rl))
                r = PROFILES.award(tok, won, pl._char.name, pl.role, wx, ranked, wrp, {"practice": bool(self.cfg.get("practice")), "hp": pl.hp, "alive": pl.alive, "rounds": g.round, "n": len(g.players), "noroles": noroles, "dmg": pl.dmg_total, "heal": pl.healed, "sha": pl.sha_n,
                                                                                                                  "maxhand": pl.max_hand, "chain11": pl.chain11, "wei": pl.wei_n, "same": len(g.players) >= 2 and len({q._char.name for q in g.players}) == 1}, lrp, secs=time.time() - getattr(self, "game_t0", time.time()), draw=draw, partial=0 if multi else partial, no_gain=multi)
                if r:
                    d, b, a = r
                    who = self.nicks.get(tok) or '未命名'
                    if not ranked:
                        self._event(f"🎮 休閒模式: {who} 段位積分不變 ({a})", "ok")
                    else:
                        self._event(f"🏅 {who} 段位積分 {(format(d, '+d') + ' (平手)') if draw else '-0' if d == 0 and not won else format(d, '+d')}{' 內奸次級勝利' if partial and not won else ''} ({b}" + (f" → {a})" if a != b else ")") + (" 升段!" if d > 0 and a != b else " 降段" if d < 0 and a != b else ""), "ok" if draw or d > 0 else "bad" if d < 0 or not won else "ok")   # 輸了一律紅底 (已經最低分就是 -0)

    def _run(self, g):
        try:
            g.run()
            if not self.abort and g.winner and not self.cfg.get("lesson"):
                self._award(g)
            if self.game is g and not self.abort:
                self.over_at = time.time()
        except AbortGame:
            pass
        except Exception as ex:  # 規則引擎錯誤: 顯示在 GUI 上
            import traceback
            traceback.print_exc()
            self.error = f"{type(ex).__name__}: {ex}"

    # ---------- 節奏控制 ----------
    def _humans_all_dead(self):
        """段位模式: 所有真人都陣亡後直接快轉到結算 (不再等每一步的延遲)。"""
        g = self.game
        if g is None or not (self.cfg or {}).get("ranked") or not self.claims:
            return False
        try:
            return all(not g.players[s].alive for s in self.claims if s < len(g.players))
        except Exception:
            return False

    def lesson_view(self):
        st = getattr(self, "les", None)
        L = lessons.by_id(st["id"]) if st else None
        if not L or not (self.cfg or {}).get("lesson"):
            return None
        return {"id": L["id"], "name": L["name"], "group": L["group"], "intro": L["intro"], "tips": L["tips"], "free": bool(L.get("free")),
                "steps": [x[0] for x in L["steps"]], "cur": st["step"], "done": st["done"], "hint": "" if st["done"] else st.get("hint", ""),
                **({"checklist": True, "got": sorted(st.get("got", ())), "manual": [x["rx"] is None for x in L["skills"]], "cur": len(st.get("got", ()))} if L.get("skills") else {})}

    def lesson_leave(self, tok):
        """離開練習關卡: 連同這局練習對局一起結束 (不然對局會繼續跑,畫面上還會跳出關卡裡的技能詢問)。"""
        if (self.cfg or {}).get("lesson"):
            self.end_game(tok, force=True)
        self.les = None
        if self.cfg:
            self.cfg["lesson"] = None
        return {"ok": True}

    def lesson_done(self, tok):
        st = getattr(self, "les", None)
        if st and not st["done"]:
            st["done"] = True
            self._event("🎓 過關! 這一關完成了", "ok")
            self._lesson_credit(st["id"])
        return {"ok": True}

    def _lesson_credit(self, lid):
        for t in set(self.claims.values()):   # 坐在位子上的真人都記一次通關
            r = PROFILES.lesson_clear(t, [lid], reward=True)
            if r.get("coins"):
                self._event(f"🪙 第一次通過這關,獲得 {r['coins']} 遊戲幣", "ok")

    def _lesson_step(self, st, L, m=None):
        st["step"] += 1
        st["hint"] = ""
        st["last_use"] = m.group(1) if m else st.get("last_use", "")
        if st["step"] >= len(L["steps"]):
            st["done"] = True
            self._event("🎓 過關! 這一關完成了", "ok")
            self._lesson_credit(st["id"])

    def _lesson_flush(self, st, L):
        """檢查清單關: 已經發動的技能效果結算完了,正式打勾; 全部勾完就過關。"""
        got = st.setdefault("got", set())
        got |= st.setdefault("pend", set())
        st["pend"].clear()
        if len(got) >= len(L["skills"]) and not st["done"]:
            st["done"] = True
            self._event("🎓 過關! 這一關完成了", "ok")
            self._lesson_credit(st["id"])

    def _lesson_check(self, st, L, msg):
        got, pend, cnts = st.setdefault("got", set()), st.setdefault("pend", set()), st.setdefault("cnts", {})
        if re.match(r"--- 第\d+輪 ", msg):
            cnts.clear()
            self._lesson_flush(st, L)
        for i, sk in enumerate(L["skills"]):
            if i in got or i in pend:
                continue
            hit = bool(sk["rx"] and re.search(sk["rx"], msg))
            c = sk.get("count")
            if c and not hit and re.search(c[0], msg):
                cnts[i] = cnts.get(i, 0) + 1
                hit = cnts[i] >= c[1]
            if hit:
                pend.add(i)

    def lesson_ack(self, tok, i):
        """沒有紀錄可以偵測的被動技能: 玩家按「我看懂了」。"""
        st = getattr(self, "les", None)
        L = lessons.by_id(st["id"]) if st else None
        if not L or not L.get("skills") or st["done"] or not isinstance(i, int) or not 0 <= i < len(L["skills"]) or L["skills"][i]["rx"] is not None:
            return {"ok": False}
        st.setdefault("got", set()).add(i)
        self._lesson_flush(st, L)
        return {"ok": True}

    def lesson_resolved(self):
        """武將關: 技能發動後,引擎又回頭問玩家出牌 (或換回合),代表效果都結算完了。"""
        st = getattr(self, "les", None)
        L = lessons.by_id(st["id"]) if st else None
        if st and L and L.get("skills") and not st["done"]:
            self._lesson_flush(st, L)
            return
        if st and st.get("armed") and not st["done"]:
            st["armed"] = False
            self._lesson_step(st, lessons.by_id(st["id"]))

    def lesson_track(self, msg):
        """教學關卡: 紀錄的每一行都拿來比對目前這一步的 regex,比到就進下一步。"""
        st, L = getattr(self, "les", None), None
        if not st or st["done"]:
            return
        L = lessons.by_id(st["id"])
        if L is not None and L.get("skills"):
            self._lesson_check(st, L, msg)
            return
        if L is None or st["step"] >= len(L["steps"]):
            return
        text, rx = L["steps"][st["step"]][:2]
        m = re.search(r"^\s*(?:\[[^\]]*\]\s*)?P0\([^)]*\)[^\n]*使用 ?([^\s]+)", msg)   # 一定是 P0 自己出牌 (行首): 「P1 對 P0 使用 殺」是別人出的,不能算成玩家做錯
        if st.get("armed"):   # 武將關: 技能已發動,等效果結算完 (換下一回合) 才算過關
            if re.match(r"--- 第\d+輪 ", msg):
                self.lesson_resolved()
            return
        hit = bool(rx and re.search(rx, msg))
        cr = L.get("count")
        if cr and not hit:   # 「同一回合出幾張殺」這類沒有紀錄行可以比對的技能,自己計次
            if re.match(r"--- 第\d+輪 ", msg):
                st["cnt"] = 0
            elif re.search(cr[0], msg):
                st["cnt"] = st.get("cnt", 0) + 1
                hit = st["cnt"] >= cr[1]
        if hit:
            if L["group"] == "武將":
                if L.get("late") and not st.get("acted"):
                    return   # 一進關就自動發動的技能不算,等玩家真的打過一次出牌階段
                st["armed"] = True   # 先不過關: 等技能效果結算完 (輪到自己再出牌 / 換回合)
                return
            self._lesson_step(st, L, m)
            return
        if L["group"] in ("武將", "身分"):   # 武將關卡是自由試技能,出別的牌不算做錯
            return
        # 沒對上這一步: 判斷是不是做錯了,告訴玩家該怎麼做
        h = ""
        if m and not (st.get("last_use") and set(re.sub("[紅黑火冰雷]", "", st["last_use"])) & set(re.sub("[紅黑火冰雷]", "", m.group(1)))):
            h = f"剛剛出的「{m.group(1)}」不是這一步要的"
        elif re.search(r"P0\([^)]*\)\s*受到 \d+ 點", msg):
            h = "你受到傷害了,和這一步想教的不一樣"
        elif re.match(r"--- 第\d+輪 P0\(", msg):
            st["own"] = True
        elif st.get("own") and "點" in text and re.match(r"--- 第\d+輪 P[1-9]\(", msg):
            st["own"] = False
            h = "你的回合結束了,這一步還沒完成"
        if h:
            st["hint"] = f"❌ {h}。現在該做的是:{text}。想重來就按「↻ 重來」"

    def on_log(self, msg):
        self.lesson_track(msg)
        if msg[:1] == chr(1):   # 動畫用的隱藏行: 不佔步驟延遲 / 單步
            return
        if self.abort:
            raise AbortGame()
        _p0 = time.time() if self.paused else None
        while self.paused and not self._step_ev.is_set() and not self.abort and not self._humans_all_dead():
            time.sleep(0.05)
        if _p0 is not None:
            self.game_t0 = getattr(self, "game_t0", _p0) + (time.time() - _p0)   # 暫停的時間不算遊玩時間
        self._step_ev.clear()
        if self.abort:
            raise AbortGame()
        if self.speed > 0 and not self._humans_all_dead():
            time.sleep(self.speed)

    def control(self, d):
        if not self.is_host(d.get("tok")):
            return {"ok": False, "error": "only host"}
        if "pause" in d:
            self.paused = bool(d["pause"])
        if "speed" in d:
            self.speed = max(0.05, float(d["speed"]))
        if d.get("step"):
            self._step_ev.set()
        return {"ok": True}

    # ---------- 人類決策 ----------
    ASK_LONG = 90      # 出牌階段、偽裝選武將的時限
    ASK_SECONDS = 30   # 所有詢問 (出牌 / 響應 / 選擇) 的預設時限

    def ask(self, seat, kind, prompt, options, mn, mx, timeout=None, default=None):
        """timeout 秒內沒人回答就自動採用 default (選項 index 的 list)。沒指定時一律 30 秒:
        可以不選的 (出牌階段 = 結束出牌) 就不選;有「不出 / 不發動」就選它;否則自動選前 mn 個 (推薦的優先)。"""
        if not timeout:
            timeout = self.ASK_LONG if (kind == "act" or (kind == "mode" and str(prompt).startswith("偽裝"))) else self.ASK_SECONDS   # 出牌階段 / 偽裝選武將 90 秒
            idx = [o["i"] for o in options]
            if mn == 0:
                default = []
            else:
                nopass = next((o["i"] for o in options if str(o.get("label", "")).startswith(("不出", "不發動", "不使用"))), None)
                rec = [o["i"] for o in options if o.get("rec")]
                default = [nopass] if nopass is not None else ((rec + [i for i in idx if i not in rec])[:mn])
        if (self.cfg or {}).get("lesson"):
            timeout = None   # 練習關卡: 慢慢想,不倒數、不會自動出牌
            if kind == "act":
                self.lesson_resolved()
                if getattr(self, "les", None):
                    self.les["acted"] = True
        with self.lock:
            self._req += 1
            rid = self._req
            self.pending = {"id": rid, "seat": seat, "kind": kind, "prompt": prompt,
                            "options": options, "min": mn, "max": mx}
            if timeout:
                self.pending["deadline"] = time.time() + timeout
            self._ans = None
            self._pend_default = default
            self._ans_ev.clear()
        while not self._ans_ev.wait(0.2):
            if self.abort:
                raise AbortGame()
            if timeout and self.paused and self.pending and self.pending.get("deadline"):
                self.pending["deadline"] += 0.2   # 暫停時不倒數
            if timeout and default is not None and not self.paused and time.time() > self.pending["deadline"]:
                with self.lock:
                    if self.pending and self.pending["id"] == rid:
                        self._ans = list(default)
                        self._ans_ev.set()
                        self._event(f"⏰ 座位 {seat} 操作逾時 ({prompt[:14]}…),已自動選擇", "warn")
        if self.abort:
            raise AbortGame()
        with self.lock:
            ans = self._ans
            self.pending = None
        return ans

    def ask_first(self, reqs):
        """同時問好幾個人,第一個選了「真的動作」(不是不出) 的人勝出。回傳 (seat, choice) 或 None (全部不出)。
        reqs: [(seat, kind, prompt, options, mn, mx, pass_i)]"""
        with self.lock:
            multi = {}
            for seat, kind, prompt, options, mn, mx, pass_i in reqs:
                self._req += 1
                multi[seat] = {"id": self._req, "seat": seat, "kind": kind, "prompt": prompt, "options": options, "min": mn, "max": mx, "pass_i": pass_i}
            self.multi_res, self.multi_win = {}, None
            self._multi_ev.clear()
            self.multi = multi
        while not self._multi_ev.wait(0.2):
            if self.abort:
                self.multi = {}
                raise AbortGame()
        if self.abort:
            self.multi = {}
            raise AbortGame()
        with self.lock:
            win = self.multi_win
            self.multi = {}
        return win

    def answer(self, rid, choice, tok=None):
        with self.lock:
            if self.paused:
                return {"ok": False, "error": "遊戲暫停中,不能操作"}
            if self.multi:
                ent = next((e for e in self.multi.values() if e["id"] == rid), None)
                if not ent or self.multi_win is not None:
                    return {"ok": False, "error": "no such request"}
                if self.seat_of(tok) != ent["seat"]:
                    return {"ok": False, "error": "not your seat"}
                try:
                    ch = [int(x) for x in choice]
                except (TypeError, ValueError):
                    return {"ok": False, "error": "bad choice"}
                valid = {o["i"] for o in ent["options"]}
                if len(set(ch)) != len(ch) or any(c not in valid for c in ch) or not (ent["min"] <= len(ch) <= ent["max"]):
                    return {"ok": False, "error": "invalid selection"}
                if ch == [ent["pass_i"]]:
                    self.multi_res[ent["seat"]] = None
                    if len(self.multi_res) >= len(self.multi):
                        self._multi_ev.set()
                else:
                    self.multi_win = (ent["seat"], ch)
                    self._multi_ev.set()
                return {"ok": True}
            p = self.pending
            if not p or p["id"] != rid:
                return {"ok": False, "error": "no such request"}
            if self.seat_of(tok) != p["seat"]:
                return {"ok": False, "error": "not your seat"}
            try:
                ch = [int(x) for x in choice]
            except (TypeError, ValueError):
                return {"ok": False, "error": "bad choice"}
            valid = {o["i"] for o in p["options"]}
            if len(set(ch)) != len(ch) or any(c not in valid for c in ch) or not (p["min"] <= len(ch) <= p["max"]):
                return {"ok": False, "error": "invalid selection"}
            self._ans = ch
            self._ans_ev.set()
        return {"ok": True}


MGR = Manager()
MGR.room_name = "公共房間"
MGR.public = True
ROOMS = {"main": MGR}   # 房間 id -> Manager; main 永遠存在 (舊網址 / 沒指定房間時用)
ROOMS_LOCK = threading.Lock()


def friend_where(fkey):
    """好友目前在哪個房間 (給好友清單顯示)。沒在任何房間回傳空字串。"""
    a = ACCOUNTS.d.get(fkey)
    if not a:
        return ""
    t, now = a["uuid"], time.time()
    for m in list(ROOMS.values()):
        if now - m.seen.get(t, 0) < 8:
            tag = "" if not m.game_active() else "對戰中 · " if t in m.claims.values() else "觀戰中 · "
            return tag + (m.room_name or "房間")
    return ""


def is_playing(tok):
    return any(m.game_active() and tok in m.claims.values() for m in list(ROOMS.values()))


def create_room(tok, name, password=None, solo=False, cap=0):
    name = (name or "").strip()[:20] or "新房間"
    password = str(password or "")[:20]
    if not tok:
        return {"ok": False, "error": "no token"}
    with ROOMS_LOCK:
        if sum(1 for m in ROOMS.values() if m.owner == tok) >= 3:
            return {"ok": False, "error": "一個人最多同時開 3 個房間"}
        if len(ROOMS) >= 30:
            return {"ok": False, "error": "房間太多了,請稍後再試"}
        rid = "".join(random.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(5))
        m = Manager()
        m.room_name, m.owner, m.host = name, tok, tok   # 建立者就是房主
        if password:
            m.pw = Accounts._mk(password)
        m.solo = bool(solo)
        try:
            cap = int(cap or 0)
        except (TypeError, ValueError):
            cap = 0
        m.cap = cap if 2 <= cap <= 10 else 0
        m.created = time.time()
        ROOMS[rid] = m
    return {"ok": True, "room": rid, "name": name, "locked": bool(password)}


def join_room(tok, rid, password, ip=""):
    """輸入房間密碼加入 (錯太多次暫時鎖住)。"""
    m = ROOMS.get(rid)
    if m is None:
        return {"ok": False, "gone": True, "error": "房間已不存在"}
    if m.cap and m.pid(tok) not in {x["id"] for x in m.online()} and len(m.online()) >= m.cap:
        return {"ok": False, "error": "房間已滿 (上限 %d 人)" % m.cap}
    if not m.pw or m.can_enter(tok):
        return {"ok": True}
    key = "room:" + str(rid) + ":" + str(tok)
    if ACCOUNTS._blocked(key, 6) or ACCOUNTS._blocked("room-ip:" + ip, 30):
        return {"ok": False, "error": "密碼錯太多次了,請 5 分鐘後再試"}
    if not Accounts._verify(m.pw, str(password or "")):
        for k in (key, "room-ip:" + ip):
            ACCOUNTS.fails.setdefault(k, []).append(time.time())
        return {"ok": False, "error": "房間密碼不正確"}
    m.allowed.add(tok)
    return {"ok": True}


def set_room_password(tok, rid, password):
    """房主 / 建立者設定、修改或移除 (留空) 房間密碼。改密碼後,之前輸入過密碼的人 (包含現在在房間裡的) 都要重新輸入;房主和建立者不用。"""
    m = ROOMS.get(rid)
    if rid == "main" or m is None:
        return {"ok": False, "error": "這個房間不能設密碼"}
    if m.solo:
        return {"ok": False, "error": "單人模式的房間不能設密碼"}
    if tok not in (m.owner, m.host):
        return {"ok": False, "error": "只有房主可以設定房間密碼"}
    password = str(password or "")[:20]
    if password:
        m.pw = Accounts._mk(password)
        m.allowed.clear()
    else:
        m.pw = None
    return {"ok": True, "locked": bool(m.pw)}


def set_room_visibility(tok, rid, unlisted):
    """房主 / 建立者切換房間公開 (顯示在大廳) 或不公開 (不顯示在大廳列表)。"""
    m = ROOMS.get(rid)
    if rid == "main" or m is None:
        return {"ok": False, "error": "這個房間不能改公開設定"}
    if tok not in (m.owner, m.host):
        return {"ok": False, "error": "只有房主可以改房間公開設定"}
    m.unlisted = bool(unlisted)
    return {"ok": True, "unlisted": m.unlisted}


def delete_room(tok, rid):
    m = ROOMS.get(rid)
    if rid == "main" or m is None:
        return {"ok": False, "error": "這個房間不能刪除"}
    if not tok or tok != m.host:
        return {"ok": False, "error": "只有房主可以刪除房間 (在房間的「新遊戲」畫面裡)"}
    m.abort = True; m._ans_ev.set(); m._step_ev.set()
    m.chat = []   # 房間刪除: 聊天紀錄一起清掉
    with ROOMS_LOCK:
        ROOMS.pop(rid, None)
    return {"ok": True}


def tok_can_manage(m, tok):
    return bool(tok) and m is not MGR and tok in (m.owner, m.host)


def rename_room(tok, rid, name):
    m = ROOMS.get(rid)
    name = (name or "").strip()[:20]
    if rid == "main" or m is None:
        return {"ok": False, "error": "這個房間不能改名"}
    if tok not in (m.owner, m.host):
        return {"ok": False, "error": "只有房主可以改房間名稱"}
    if not name:
        return {"ok": False, "error": "房間名稱不能是空的"}
    m.room_name = name
    return {"ok": True, "name": name}


LOBBY_SEEN = {}   # tok -> 最後一次在大廳看房間列表的時間 (算全站在線人數)


def total_online(now=None):
    """全站目前在線人數: 各房間裡 6 秒內有連線的人 + 在大廳的人 (同一個人只算一次)。"""
    now = now or time.time()
    toks = {t for m in list(ROOMS.values()) for t, ts in list(m.seen.items()) if now - ts < 6}
    toks |= {t for t, ts in list(LOBBY_SEEN.items()) if now - ts < 6}
    for t in [t for t, ts in list(LOBBY_SEEN.items()) if now - ts > 60]:
        LOBBY_SEEN.pop(t, None)
    return len(toks)


def apply_remarks(snap, M, tok):
    """替好友取的暱稱只有自己看得到,而且除了好友介面和對方的玩家資訊以外,到處都顯示暱稱:
    座位名單 / 線上名單 / 房主 / 聊天 / 事件通知都換成暱稱 (遊戲內容本身不變)。"""
    rk = SOCIAL.remarks(SOCIAL.key_of(tok))
    if not rk:
        return snap
    by = {t: rk[k] for t in list(M.nicks) if t != tok for k in [SOCIAL.key_of(t)] if k in rk}
    if not by:
        return snap
    pid_map = {M.pid(t): r for t, r in by.items()}
    nick_map = sorted(((M.nicks[t], r) for t, r in by.items() if M.nicks.get(t)), key=lambda x: -len(x[0]))
    def sub(text):
        for n, r in nick_map:
            text = text.replace(n, r)
        return text
    if snap.get("names"):
        snap["names"] = {s: (by.get(M.claims.get(s)) or n) for s, n in snap["names"].items()}
    if snap.get("online"):
        snap["online"] = [dict(o, name=pid_map.get(o["id"], o["name"])) for o in snap["online"]]
    if M.host in by:
        snap["host_name"] = by[M.host]
    if snap.get("events"):
        snap["events"] = [dict(e, text=sub(e["text"])) if isinstance(e.get("text"), str) else e for e in snap["events"]]
    if snap.get("chat"):
        snap["chat"] = [dict(m, nick=pid_map[m["who"]]) if m.get("who") in pid_map else m for m in snap["chat"]]
    return snap


def list_rooms(tok=None):
    now = time.time()
    out = []
    if tok:
        LOBBY_SEEN[tok] = now
    rk = SOCIAL.remarks(SOCIAL.key_of(tok)) if tok else {}
    for rid, m in list(ROOMS.items()):
        if m.solo or (m.unlisted and tok not in (m.owner, m.host)):   # 不公開的房間: 只有房主 / 建立者在大廳看得到
            continue
        on = m.online()
        st = ("進行中" if m.game_active() else "選武將" if m.picking else "等待玩家" if m.lobby else "等待開局" if on else "空房")   # 有人在的房間不能寫空房
        out.append({"id": rid, "name": m.room_name, "online": len(on), "state": st, "host": (rk.get(SOCIAL.key_of(m.host)) if m.host and m.host != tok else None) or m.host_name() or "",
                    "n": m.cfg.get("n") if m.cfg else None, "ranked": bool(m.cfg.get("ranked")) if m.cfg and st in ("進行中", "選武將", "等待玩家") else None, "main": rid == "main",
                    "can_delete": rid != "main" and tok in (m.owner, m.host),
                    "locked": bool(m.pw), "need_pw": bool(m.pw) and not m.can_enter(tok), "cap": m.cap})
    out.sort(key=lambda r: (not r["main"], -r["online"]))
    tot = total_online(now)
    for r in out:
        r["total"] = tot
    return out


IDLE_AFTER_OVER = 300


def reap_rooms():
    """沒人在線的自訂房間: 沒開局的 1 分鐘後刪除,對局進行中的 3 分鐘後停掉對局並刪除 (給手機切換程式 / 斷線重連一點時間)。"""
    now = time.time()
    for rid, m in list(ROOMS.items()):
        if rid == "main" or m.public:
            continue
        last = max([m.created] + list(m.seen.values()))
        present = [t for t, x in m.seen.items() if now - x < m.OFFLINE_AFTER]
        idle_over = (m.over_at is not None and not m.game_active() and len(present) <= 1
                     and now - max(m.over_at, m.act) > IDLE_AFTER_OVER)   # 遊戲結束後只剩一個人掛機 5 分鐘: 請回大廳並刪除房間
        if idle_over or now - last > (180 if m.game_active() else 60):
            m.abort = True; m._ans_ev.set(); m._step_ev.set()
            m.chat = []   # 房間被回收: 聊天紀錄一起清掉
            with ROOMS_LOCK:
                ROOMS.pop(rid, None)


# ---------- 武將資料 ----------
def load_roster():
    imgs = json.load(open(os.path.join(HERE, "character_images.json"), encoding="utf-8"))
    skills, cur = {}, None
    for line in open(os.path.join(HERE, "characters.md"), encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("### "):
            cur = line[4:].strip()
            skills[cur] = []
        elif cur and (re.match(r"\d+\.", line) or line.startswith("(")):   # 「(最多8血)」這類備註也要顯示
            skills[cur].append(line)
    out = []
    for name, cls in ROSTER.items():
        c = cls()
        src = os.path.join(ROOT, imgs[name]["image"].replace("/", os.sep)) if name in imgs and imgs[name].get("image") else None
        out.append({"name": name, "faction": c.faction, "maxhp": c.maxhp, "skills": skills.get(name, []),
                    "img": "/thumb/char/" + name + "?v=ink2" if (src and os.path.isfile(src)) or os.path.isfile(os.path.join(WEB, "ink", "generals", name + ".jpg")) else None})   # 水墨圖或舊素材圖有一個就顯示;都沒有才只顯示文字
    return out, imgs


ROSTER_DATA, CHAR_IMGS = load_roster()
lessons.add_generals(ROSTER_DATA)


WUMING_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 360"><defs>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e9dcc0"/><stop offset="1" stop-color="#c9b48a"/></linearGradient>
<radialGradient id="mist" cx=".5" cy=".62" r=".6"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>
<rect width="260" height="360" fill="url(#bg)"/>
<path d="M0 250 L40 190 L70 225 L110 160 L150 230 L190 180 L260 250 L260 360 L0 360Z" fill="#8a7a5c" opacity=".35"/>
<path d="M0 290 L60 240 L100 270 L160 225 L220 275 L260 255 L260 360 L0 360Z" fill="#5c5038" opacity=".4"/>
<rect width="260" height="360" fill="url(#mist)"/>
<g stroke="#1d1a14" stroke-width="5" stroke-linejoin="round" stroke-linecap="round">
<path d="M130 282 L174 120 L186 124 L142 286Z" fill="#9aa1a8" transform="translate(40 24) rotate(8 130 200)"/>
<path d="M96 150 C92 200 84 250 76 326 L184 326 C176 250 168 200 164 150 C150 138 110 138 96 150Z" fill="#3b3a36"/>
<path d="M112 150 C116 190 118 240 114 326 M148 150 C144 190 142 240 146 326" fill="none" stroke="#1d1a14" stroke-width="3" opacity=".6"/>
<path d="M108 138 C108 122 152 122 152 138 C150 150 110 150 108 138Z" fill="#d9c8a4"/>
<path d="M54 112 L130 52 L206 112 C170 124 90 124 54 112Z" fill="#a8864a"/>
<path d="M70 108 L130 64 L190 108" fill="none" stroke="#6d5426" stroke-width="3"/>
<path d="M84 114 L176 114" stroke="#6d5426" stroke-width="3"/></g>
<text x="130" y="142" text-anchor="middle" font-size="26" font-family="serif" fill="#1d1a14" opacity=".55">?</text>
</svg>"""


def make_thumb(name, old=False):
    """old=True: 玩家選了舊版武將圖 (原本的素材圖 / 無名斗笠 SVG);舊版沒有這位武將的圖就退回水墨圖。"""
    r = _make_thumb(name, old)
    return r or (_make_thumb(name, False) if old else None)


def _make_thumb(name, old):
    if name not in ("無名", "_back") and name not in ROSTER:   # 只認得出的武將名 (擋掉 ../ 之類的路徑)
        return None
    ink = os.path.join(WEB, "ink", "generals", name + ".jpg")   # 水墨武將圖 (含「無名」) 優先
    if os.path.isfile(ink) and not old:
        return ink
    if name == "無名":   # 沒有指定武將 (練習關卡 / 無武將): 畫一個斗笠無面人
        os.makedirs(CACHE, exist_ok=True)
        dst = os.path.join(CACHE, "wuming.svg")
        if not os.path.exists(dst):
            with open(dst, "w", encoding="utf-8") as f:
                f.write(WUMING_SVG)
        return dst
    rel = CHAR_IMGS.get(name, {}).get("image")
    if not rel:
        return None
    src = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.isfile(src):
        return None
    os.makedirs(CACHE, exist_ok=True)
    dst = os.path.join(CACHE, hashlib.md5(name.encode()).hexdigest() + ".jpg")
    if not os.path.exists(dst):
        from PIL import Image
        im = Image.open(src).convert("RGB")
        im.thumbnail((260, 360))
        im.save(dst, quality=85)
    return dst


# ---------- HTTP ----------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8", cache=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", cache or ("no-store" if ctype.startswith(("application/json", "application/javascript", "text/", "image/svg")) else "max-age=3600"))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, cache=None):
        if not path or not os.path.isfile(path):
            return self._send(404, {"error": "not found"})
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            self._send(200, f.read(), ctype, cache)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        path = unquote(u.path)
        raw = q.get("tok", [""])[0]
        q["tok"] = [ACCOUNTS.resolve(raw)]
        try:
            if path == "/api/me":
                t = q["tok"][0]
                return self._send(200, {"ok": ACCOUNTS.is_account(t), "user": ACCOUNTS.username(t), "kicked": raw in ACCOUNTS.kicked, "default_pw": ACCOUNTS.default_pw(t)})
            if path.startswith("/api/") and path not in OPEN_API and not ACCOUNTS.is_account(q["tok"][0]):
                return self._send(200, {"auth": False, "ready": False, "kicked": raw in ACCOUNTS.kicked})
            if path.startswith("/avatar/"):
                fn = os.path.basename(path)
                full = os.path.join(Profiles.AVATAR_DIR, fn)
                if not fn.endswith(".jpg") or not os.path.isfile(full):
                    return self._send(404, {"error": "not found"})
                return self._file(full)
            if path == "/api/profile":
                return self._send(200, PROFILES.info(q.get("tok", [""])[0]) or {})
            if path == "/api/cosmetics":
                return self._send(200, cosmetics.catalog())
            if path == "/api/leaderboard":
                return self._send(200, leaderboard(q.get("tok", [""])[0]))
            if path == "/api/rooms":
                return self._send(200, list_rooms(q.get("tok", [""])[0]))
            if path == "/api/social":
                tk = q.get("tok", [""])[0]
                key = SOCIAL.key_of(tk)
                SOCIAL.touch(key)
                return self._send(200, SOCIAL.overview(key, friend_where, is_playing(tk)))
            if path == "/api/player":
                r = player_public(q.get("name", [""])[0])
                if r.get("ok"):   # 共同好友 (我和他都有加的人)
                    me_k = SOCIAL.key_of(q.get("tok", [""])[0])
                    r["self"] = me_k == r["user"].lower()
                    r["mutual"] = [dict(_card(k), id=k, name=(ACCOUNTS.d.get(k) or {}).get("user", k)) for k in SOCIAL.mutual(me_k, r["user"].lower())]
                    fk = r["user"].lower()   # 線上狀態: 誰都看得到在線 / 離線;所在房間和最後上線時間只有好友看得到
                    seen = SOCIAL._u(fk).get("seen", 0) if fk in SOCIAL.d["u"] else 0
                    wf = friend_where(fk)
                    r["online"] = time.time() - seen < 15 or bool(wf)
                    isf = fk in (SOCIAL.d["u"].get(me_k) or {}).get("fr", [])
                    r["where"] = wf if isf and r["online"] else ""
                    r["seen"] = int(seen) if isf else 0
                    r["now"] = int(time.time())
                return self._send(200, r)
            if path == "/api/gchat":
                try:
                    n = int(q.get("since", ["0"])[0])
                except ValueError:
                    n = 0
                out = PUBCHAT.since(n)
                rk = SOCIAL.remarks(SOCIAL.key_of(q.get("tok", [""])[0]))   # 公共頻道: 好友顯示我取的暱稱
                if rk and isinstance(out, dict) and isinstance(out.get("msgs"), list):
                    out["msgs"] = [dict(m, nick=rk[m["acc"]]) if m.get("acc") in rk else m for m in out["msgs"]]
                return self._send(200, out)
            if path == "/api/dm":
                tk = q.get("tok", [""])[0]
                return self._send(200, SOCIAL.thread(SOCIAL.key_of(tk), q.get("with", [""])[0]))
            M = ROOMS.get(q.get("room", ["main"])[0] or "main")
            if M is None and path.startswith("/api/") and path not in ("/api/cardcat", "/api/i18n", "/api/roster", "/api/lessons"):
                return self._send(200, {"gone": True, "ready": False})
            if path in ("/", "/index.html"):
                return self._file(os.path.join(WEB, "index.html"))
            if path == "/api/lessons":   # 教學關卡目錄
                from view import full_name
                full2key = {full_name(k): k for k in cardart.E}
                full2key.update({k: k for k in cardart.E})
                out = []
                for L in lessons.catalog():   # 每關附一張代表圖 (牌 / 身分牌 / 武將),選單用圖加名字顯示
                    g, nm = L["group"], L["name"]
                    img = ("/cards/_role_" + nm + ".svg") if g == "身分" else ("/thumb/char/" + nm) if g == "武將" else ("/cards/" + full2key[nm] + ".svg") if nm in full2key else ""
                    out.append(dict(L, img=img))
                return self._send(200, {"groups": lessons.GROUPS, "lessons": out})
            if path == "/api/cardcat":   # 牌的目錄: 戰報把牌名換成圖片、滑過去顯示說明用
                from view import card_img
                from card_desc import DESC
                from view import full_name
                from card_desc import body as _body
                cat = {k: {"desc": _body(v), "pre": (v[:1] + " ") if v[:1] in "⚡⏳" else "", "full": full_name(k), "img": {c: card_img(k, c) for c in ("紅", "黑")}} for k, v in DESC.items()}
                for nat in ("火", "冰", "雷"):
                    cat[nat + "殺"] = {"desc": nat + "屬性殺: " + DESC["殺"], "full": nat + "殺", "img": {c: card_img(nat, c) for c in ("紅", "黑")}, "nat": True}
                import cards as _cd
                from view import type_label
                _kd = {x[0]: "weapon" for x in _cd.WEAPON}
                _kd.update({x[0]: "armor" for x in _cd.ARMOR}); _kd.update({x[0]: "horse" for x in _cd.HORSE}); _kd.update({k: "basic" for k in ("殺", "閃", "桃", "酒", "火殺", "冰殺", "雷殺")})
                for k, e in cat.items():
                    e["tp"] = type_label("殺" if e.get("nat") else k, _kd.get(k, "trick"))
                    e["bolt"] = "⚡" if DESC.get(k, "").startswith("⚡") else ""
                    from view import range_label
                    e["rng"] = range_label(k)
                    e["land"] = k in ("樂", "兵", "草", "閃電", "毒")
                for n in [x[0] for x in _cd.WEAPON] + [x[0] for x in _cd.ARMOR] + [x[0] for x in _cd.HORSE]:
                    if n in cat:
                        cat[n]["eq"] = True   # 裝備牌: 前端動畫不往場中央飛
                return self._send(200, cat)
            if path == "/api/i18n":   # 卡牌說明翻譯: {中文說明: 譯文}
                from i18n_cards import exact
                import i18n_skills
                lg = q.get("lang", ["en"])[0]
                d = exact(lg)
                from card_desc import body as _b, body_tr as _bt
                for _k, _v in list(d.items()):   # 顯示用的效果文拿掉了符號和牌名: 譯文也要有對應的版本
                    _k2 = _b(_k)
                    if _k2 != _k and _k2 not in d:
                        d[_k2] = _bt(_k, _v)
                d.update(i18n_skills.exact(lg))
                return self._send(200, d)
            if path == "/api/roster":
                return self._send(200, {"chars": ROSTER_DATA, "roles": {str(k): v for k, v in ROLES.items()}})
            if path == "/api/state":
                tok = q.get("tok", [""])[0]
                if M.pop_kicked(tok):
                    return self._send(200, {"kicked": True, "ready": False})
                if not M.can_enter(tok):
                    return self._send(200, {"need_pw": True, "ready": False})
                viewer = M.seat_of(tok)
                M.touch(tok)
                SOCIAL.touch(SOCIAL.key_of(tok))   # 在房間裡輪詢也算上線 (好友名單才不會把觀戰中的人寫成離線)
                nk = q.get("nick", [None])[0]
                if nk is not None and M.nicks.get(tok, "") != nk[:10]:
                    M.set_nick(tok, nk)   # 伺服器重啟後暱稱會遺失,每次輪詢順便帶上
                M.set_chain_pref(tok, q.get("cm", [""])[0] == "all")   # 連鎖提示: 全部都問 / 只有影響到我才問
                if M.lobby:
                    return self._send(200, apply_remarks({"ready": True, "lobby": True, "n": M.cfg["n"],
                                            "humans": sorted(M.humans),
                                            "ranked": bool(M.cfg.get("ranked")), "claims": sorted(M.claims), "mine": viewer, "names": M.seat_names(), "levels": M.seat_levels(), "avatars": M.seat_avatars(), "avstyles": M.seat_styles(),
                                            "host": bool(tok) and tok == M.host, "is_host": M.is_host(tok),
                                            "online": M.online(), "host_name": M.host_name(), "events": M.events, "locked": M.game_active(), "room_name": M.room_name, "can_manage": tok_can_manage(M, tok),
                                            **M.pick_view(tok), **M.chat_since(int(q.get("chat", ["0"])[0]), tok)}, M, tok))
                snap = snapshot(M, viewer, int(q.get("log", ["0"])[0]),
                                int(q.get("th", ["0"])[0]),
                                q.get("peek", ["0"])[0] == "1" and not (M.cfg or {}).get("ranked") and (len(M.humans) <= 1 or M.is_host(tok)))   # 多人遊戲只有房主能偷看
                snap["room_name"] = M.room_name
                snap["can_manage"] = tok_can_manage(M, tok)
                snap["room_locked"] = bool(M.pw); snap["room_unlisted"] = bool(M.unlisted)
                snap["is_host"] = M.is_host(tok)
                snap["online"] = M.online()
                snap["ranked_abandoned"] = M.ranked_abandoned()
                snap["host_name"] = M.host_name()
                snap["events"] = M.events
                snap["avstyles"] = M.seat_styles(); snap["locked"] = M.game_active(); snap["ranked"] = bool((M.cfg or {}).get("ranked")); snap["gmode"] = (M.cfg or {}).get("mode") or "normal"; snap["rmode"] = (M.cfg or {}).get("role_mode") or "normal"
                snap["lesson"] = M.lesson_view()
                if M.cfg and "players" in snap:   # 每個電腦座位的難度 (1~4)
                    snap["ai_lv"] = [M._level(M.cfg, i) for i in range(len(snap["players"]))]
                snap.update(M.chat_since(int(q.get("chat", ["0"])[0]), tok))
                return self._send(200, apply_remarks(snap, M, tok))
            if path.startswith("/bg/"):   # 主題背景圖 (水墨山水)
                return self._file(os.path.join(WEB, "bg", os.path.basename(path)), "max-age=86400")
            if path.startswith("/icons/") or path == "/favicon.ico":   # 分頁圖示 / 手機加到主畫面的圖示
                return self._file(os.path.join(WEB, "icons", os.path.basename(path)), "max-age=86400")
            if path in ("/fonts/pixel-tw.woff2", "/fonts/pixel-ja.woff2"):   # 像素主題的字體 (Fusion Pixel Font, OFL 授權)
                return self._file(os.path.join(WEB, "fonts", path[len("/fonts/"):]))
            if path in ("/i18n.js", "/i18n_log.js", "/i18n_ui.js", "/i18n_log2.js", "/i18n_new.js", "/i18n_rank.js", "/fx.js", "/theme.js", "/anim.js", "/friends.js", "/lessons.js"):
                return self._file(os.path.join(WEB, path[1:]))
            if path == "/api/about":
                from version import VERSION, REPO
                try:
                    log = open(os.path.join(HERE, "CHANGELOG.md"), encoding="utf-8").read()
                except OSError:
                    log = ""
                return self._send(200, {"version": VERSION, "repo": REPO, "changelog": log, "beta": BETA, "behind": BEHIND[0]})
            if path.startswith("/thumb/char/"):
                nm = path[len("/thumb/char/"):]
                return self._file(make_thumb(nm, q.get("art", [""])[0] == "old"), "max-age=86400" if nm == "無名" else None)   # 無名的圖是 SVG,預設不快取: 牌桌每次重畫都重抓會一直閃
            if path.startswith("/cards/"):   # 卡面 / 卡背 (SVG,程式即時產生): /cards/<牌名>.svg?bg=<卡面風格>、/cards/_back.svg?bk=<卡背>
                fn = os.path.basename(path)
                if not fn.endswith(".svg"):
                    return self._send(404, {"error": "not found"})
                nm = fn[:-4]
                body = cardart.svg_back(q.get("bk", [""])[0]) if nm == "_back" else cardart.svg_role(nm[6:], lg=self._lang(), art=q.get("art", [""])[0]) if nm.startswith("_role_") else cardart.svg(nm, q.get("bg", [""])[0], q.get("s", [""])[0] == "1", self._lang(), q.get("art", [""])[0])
                if body is None:
                    return self._send(404, {"error": "not found"})
                raw = body.encode("utf-8")
                etag = '"' + hashlib.md5(raw).hexdigest() + '"'
                cc = "max-age=86400" if q.get("v", [""])[0] else "no-cache"   # 網址帶版本號 (?v=) 的卡面內容不會變: 讓瀏覽器直接用快取,座位上的武器 / 防具每次重畫才不會閃 (沒帶版本號的照舊每次確認)
                if self.headers.get("If-None-Match") == etag:   # 卡面 SVG 內嵌水墨圖很大: 沒變就回 304
                    self.send_response(304); self.send_header("ETag", etag); self.send_header("Cache-Control", cc); self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml"); self.send_header("Content-Length", str(len(raw)))
                self.send_header("ETag", etag); self.send_header("Cache-Control", cc)
                self.send_header("X-Content-Type-Options", "nosniff"); self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers(); self.wfile.write(raw)
                return
            if path.startswith("/assets/sgs_sim/web/hp/"):   # 血量圖示 (隨程式附上,不在素材資料夾)
                return self._file(os.path.join(WEB, "hp", os.path.basename(path)), "max-age=86400")   # 玉璧 SVG 不會變: 讓瀏覽器快取,牌桌每次重畫就不用重抓 (預設 SVG 是 no-store)
            if path.startswith("/assets/"):
                full = os.path.normpath(os.path.join(ROOT, path[len("/assets/"):].replace("/", os.sep)))
                if os.path.commonpath([full, os.path.normpath(ROOT)]) != os.path.normpath(ROOT):
                    return self._send(403, {"error": "forbidden"})
                return self._file(full)
            self._send(404, {"error": "not found"})
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _lang(self):
        """介面語言 (前端存在 cookie sgs_lang): 卡面的印章字要跟著換。"""
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "sgs_lang":
                return v if v in ("en", "ja") else ""
        return ""

    def _ip(self):
        """連線來源 IP。只有本機反向代理 (Caddy) 轉來的連線才相信 X-Forwarded-For。"""
        ip = self.client_address[0]
        if ip in ("127.0.0.1", "::1"):
            xf = (self.headers.get("X-Forwarded-For") or "").split(",")[-1].strip()
            if xf:
                return xf
        return ip

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            return self._send(413, {"error": "too large"})
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, {"error": "bad json"})
        path = urlparse(self.path).path
        raw = data.get("tok")
        if path != "/api/register":
            data["tok"] = ACCOUNTS.resolve(raw)
        try:
            if path == "/api/register":
                return self._send(200, ACCOUNTS.register(data.get("user"), data.get("pw"), data.get("tok"), self._ip()))
            if path == "/api/login":
                return self._send(200, ACCOUNTS.login(data.get("user"), data.get("pw"), self._ip()))
            if path.startswith("/api/") and path not in OPEN_API and not ACCOUNTS.is_account(data.get("tok")):
                return self._send(200, {"ok": False, "auth": False, "kicked": raw in ACCOUNTS.kicked, "error": "請先登入"})
            if path == "/api/change_pw":
                return self._send(200, ACCOUNTS.change_pw(data.get("tok"), data.get("old"), data.get("new")))
            if path == "/api/ach_ack":
                return self._send(200, PROFILES.ack_ach(data.get("tok")))
            if path == "/api/cosmetic":
                return self._send(200, PROFILES.set_style(data.get("tok"), data.get("frame"), data.get("fx"), data.get("theme"), data.get("box"), data.get("cardbg"), data.get("cardback"), data.get("cardart"), data.get("genart"), data.get("anim")))
            if path == "/api/buy":
                return self._send(200, PROFILES.buy(data.get("tok"), str(data.get("kind") or ""), str(data.get("id") or "")))
            if path == "/api/dev":   # 開發者管理介面 (GUI)
                if PROFILES.dev(data.get("tok")) != "dev":
                    return self._send(200, {"ok": False, "error": "沒有權限"})
                return self._send(200, devconsole.api(globals(), data.get("tok"), data))
            if path == "/api/delete_account":   # 玩家自己刪除帳號 (要輸入密碼)
                return self._send(200, devconsole.delete_self(globals(), data.get("tok"), str(data.get("pw") or "")))
            if path == "/api/prestige":
                if is_playing(data.get("tok")):
                    return self._send(200, {"ok": False, "error": "對局進行中不能轉生,請先離開或等這場結束"})
                return self._send(200, PROFILES.prestige(data.get("tok")))
            if path == "/api/rank_ack":
                return self._send(200, PROFILES.ack_rank(data.get("tok"), data.get("id")))
            if path == "/api/avatar":
                d = data.get("data") or ""
                if not d:
                    return self._send(200, PROFILES.set_avatar(data.get("tok"), None))
                if not d.startswith("data:image/jpeg;base64,"):
                    return self._send(200, {"ok": False, "error": "只接受 JPEG"})
                import base64
                try:
                    raw = base64.b64decode(d.split(",", 1)[1], validate=True)
                except ValueError:
                    return self._send(200, {"ok": False, "error": "圖片資料錯誤"})
                return self._send(200, PROFILES.set_avatar(data.get("tok"), raw))
            if path == "/api/gchat":
                return self._send(200, PUBCHAT.say(data.get("tok"), data.get("nick"), data.get("text")))
            if path.startswith(("/api/friend_", "/api/dm_", "/api/invite")):
                key = SOCIAL.key_of(data.get("tok"))
                if path == "/api/friend_add":
                    return self._send(200, SOCIAL.add(key, data.get("name")))
                if path == "/api/friend_accept":
                    return self._send(200, SOCIAL.accept(key, data.get("name")))
                if path == "/api/friend_decline":
                    return self._send(200, SOCIAL.decline(key, data.get("name")))
                if path == "/api/friend_cancel":
                    return self._send(200, SOCIAL.cancel(key, data.get("name")))
                if path == "/api/friend_remove":
                    return self._send(200, SOCIAL.remove(key, data.get("name")))
                if path == "/api/friend_nick":
                    return self._send(200, SOCIAL.set_remark(key, data.get("name"), data.get("nick")))
                if path == "/api/dm_send":
                    return self._send(200, SOCIAL.send(key, data.get("to"), data.get("text")))
                if path == "/api/invite":
                    rid = data.get("room") or "main"
                    m = ROOMS.get(rid)
                    if m is None or time.time() - m.seen.get(data.get("tok"), 0) > 30:
                        return self._send(200, {"ok": False, "error": "你不在這個房間裡"})
                    if m.solo:
                        return self._send(200, {"ok": False, "error": "單人模式的房間不能邀請別人"})
                    to_key = (data.get("to") or "").strip().lower(); now = time.time()
                    for rid2, m2 in list(ROOMS.items()):   # 已經在這個房間的人、或正在對局中 (有座位、對局還沒結束) 的人不能邀請
                        for t2, ts in list(m2.seen.items()):
                            if now - ts > 30 or ACCOUNTS.uuids.get(t2) != to_key:
                                continue
                            if rid2 == rid:
                                return self._send(200, {"ok": False, "error": "對方已經在這個房間裡了"})
                            g2 = m2.game
                            if g2 is not None and not getattr(g2, "winner", None) and t2 in m2.claims.values():
                                return self._send(200, {"ok": False, "error": "對方正在對局中,不能邀請"})
                    return self._send(200, SOCIAL.invite(key, data.get("to"), rid, m.room_name or "房間"))
                if path == "/api/invite_reply":
                    r = SOCIAL.reply(key, int(data.get("id") or 0), bool(data.get("accept")))
                    if r.get("room") and ROOMS.get(r["room"]) is None:
                        return self._send(200, {"ok": False, "error": "那個房間已經不存在了"})
                    if r.get("room"):   # 接受邀請才算數: 之後進這個房間不用輸入密碼 (拒絕的人還是要輸入)
                        ROOMS[r["room"]].allowed.add(data.get("tok"))
                    return self._send(200, r)
                return self._send(404, {"error": "not found"})
            if path == "/api/room_rename":
                return self._send(200, rename_room(data.get("tok"), data.get("target"), data.get("name")))
            if path == "/api/room_visibility":
                return self._send(200, set_room_visibility(data.get("tok"), data.get("target"), data.get("unlisted")))
            if path == "/api/room_password":
                return self._send(200, set_room_password(data.get("tok"), data.get("target"), data.get("password")))
            if path == "/api/room_delete":
                return self._send(200, delete_room(data.get("tok"), data.get("target")))
            if path == "/api/room_create" and not ACCOUNTS.is_account(data.get("tok")):
                return self._send(200, {"ok": False, "auth": False, "error": "請先登入"})
            if path == "/api/room_create":
                return self._send(200, create_room(data.get("tok"), data.get("name"), data.get("password"), bool(data.get("solo")), data.get("cap")))
            if path == "/api/room_join":
                return self._send(200, join_room(data.get("tok"), data.get("room") or "main", data.get("password"), self._ip()))
            M = ROOMS.get(data.get("room") or "main")
            if M is None:
                return self._send(200, {"ok": False, "gone": True, "error": "房間已不存在"})
            if path != "/api/leave":
                M.act = time.time()
            if M.is_kicked(data.get("tok")) and path != "/api/leave":
                return self._send(200, {"ok": False, "kicked": True, "error": "你被房主踢出了這個房間"})
            if not M.can_enter(data.get("tok")):
                return self._send(200, {"ok": False, "need_pw": True, "error": "這個房間需要密碼"})
            if path == "/api/kick":
                return self._send(200, M.kick(data.get("tok"), data.get("to")))
            if path == "/api/leave":
                if M.solo and data.get("tok") == M.owner:   # 單人模式: 離開就把房間 (和對局) 收掉
                    delete_room(data.get("tok"), data.get("room") or "main")
                    return self._send(200, {"ok": True})
                M.leave(data.get("tok"))
                return self._send(200, {"ok": True})
            if path == "/api/lesson_leave":
                return self._send(200, M.lesson_leave(data.get("tok")))
            if path == "/api/lessons_sync":   # 登入後把這台裝置上已通關的關卡補報給伺服器 (以前只存在瀏覽器)
                ids = data.get("ids") or []
                return self._send(200, PROFILES.lesson_clear(data.get("tok"), [str(i) for i in ids][:400]))
            if path == "/api/lesson_ack":
                return self._send(200, M.lesson_ack(data.get("tok"), data.get("i")))
            if path == "/api/lesson_done":
                return self._send(200, M.lesson_done(data.get("tok")))
            if path == "/api/end_game":
                return self._send(200, M.end_game(data.get("tok")))
            if path == "/api/rematch":
                return self._send(200, M.rematch(data.get("tok")))
            if path == "/api/new":
                return self._send(200, M.new_game(data))
            if path == "/api/answer":
                return self._send(200, M.answer(data.get("id"), data.get("choice", []), data.get("tok")))
            if path == "/api/claim":
                return self._send(200, M.claim(data.get("tok"), data.get("seat"), data.get("name"), self._ip()))
            if path == "/api/forfeit":
                return self._send(200, M.forfeit(data.get("tok")))
            if path == "/api/transfer":
                return self._send(200, M.transfer_host(data.get("tok"), data.get("to")))
            if path == "/api/nick":
                return self._send(200, M.set_nick(data.get("tok"), data.get("name")))
            if path == "/api/chat":
                return self._send(200, M.say(data.get("tok"), data.get("text")))
            if path == "/api/pick":
                return self._send(200, M.pick(data.get("tok"), data.get("name")))
            if path == "/api/start":
                return self._send(200, M.start(data.get("tok")))
            if path == "/api/control":
                return self._send(200, M.control(data))
            self._send(404, {"error": "not found"})
        except Exception as ex:
            import traceback
            traceback.print_exc()   # 詳細錯誤只留在伺服器日誌,不回傳給使用者
            self._send(500, {"error": "伺服器發生錯誤"})


def main():
    lan = "--lan" in sys.argv
    try:
        srv = ThreadingHTTPServer(("0.0.0.0" if lan else "127.0.0.1", PORT), Handler)
    except OSError:
        print(f"!! 埠 {PORT} 已被占用 (可能有舊的伺服器視窗還開著)。請關掉舊視窗,或用啟動遊戲.bat 自動清掉舊的。")
        sys.exit(1)
    def _tick():   # 每 2 秒偵測一次誰斷線 / 重連
        while True:
            time.sleep(2)
            try:
                for m in list(ROOMS.values()):   # 每個房間都要偵測 (房主斷線要交棒),順便清掉沒人的房間
                    m.presence()
                    m.prune_chat()
                reap_rooms()
            except Exception:
                pass
    threading.Thread(target=_tick, daemon=True).start()
    try:
        import announce
        announce.start_background()   # 版本更新了就把 changelog 貼到 Discord (沒設定 webhook 就什麼都不做)
    except Exception:
        pass
    url = f"http://127.0.0.1:{PORT}/"
    print("進化三國 GUI:", url, "(Ctrl+C 結束)")
    if lan:
        import socket
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            ip = "<你的區網 IP>"
        print(f"區域網路: 朋友開 http://{ip}:{PORT}/  (Windows 防火牆若詢問請允許私人網路)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
