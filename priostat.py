"""全電腦 (5 級 ProAgent) 自我對戰,一次收三種資料,用來校正「卡牌優先度 / 武將集火優先度 / 偽裝推薦」。

python priostat.py --games 40000 --out stat.pkl [--players 5] [--seed0 500000] [--procs 6] [--early 7]

每局記錄:
- 每位玩家: 武將、身分、有沒有贏、離主公幾個座位、最早從牌堆拿到的 N 張牌 (起手 5 張 + 第一次抽牌)、整場造成的傷害。
  → 起手牌是隨機發的,拿「起手有這張牌」對勝率做迴歸 = 這張牌實際值多少。
- 每次偽裝: 這份腳本的電腦「有偽裝就用、變成誰用抽籤的」,記下當時的手牌情境、變成誰、
  這個回合結束時的局面變化 (自己和隊友的血 / 牌增加、敵人的血 / 牌減少)、最後有沒有贏。
  → 因為變成誰是抽籤的,各武將的平均局面變化可以直接比。
"""
import argparse
import pickle
import random
import sys
import time
from multiprocessing import Pool

sys.stdout.reconfigure(encoding="utf-8")
from ai_pro import SHA_NAMES, ProAgent, fn
from characters import ROSTER
from engine import Game

CAMP = {"主公": "主公陣營", "忠臣": "主公陣營", "反賊": "反賊", "內奸": "內奸"}
AOE = ("南蠻入侵", "萬箭齊發")
EARLY = 7


def cname(c):
    return "殺" if c.name in SHA_NAMES else fn(c)


class DgAgent(ProAgent):
    """有偽裝就用,變成誰用抽籤的 (探索用)。"""

    def disguise_plan(self, g, p):
        if p._char.name == "蔣幹" or p.disguise:
            return None
        taken = {q._char.name for q in g.players} | {x.name for q in g.players for x in q.disguise}
        pool = [nm for nm in ROSTER if nm not in taken]
        return g._xrng.choice(pool) if pool else None


def side(p, q):
    """q 的局面變化對 p 來說算幾分。"""
    if q is p:
        return 1.0
    if p.role == "內奸" or q.role == "內奸":
        return -0.5
    return 0.5 if CAMP[p.role] == CAMP[q.role] else -1.0


def worth(q):
    if not q.alive:
        return -3.0
    return 2 * max(q.hp, 0) + len(q.hand) + sum(1 for c in q.equip.values() if c)


class StatGame(Game):
    def draw(self, p, n, blocked=False):
        got = super().draw(p, n, blocked)
        log = self._early[p.idx]
        for c in got:
            if len(log) < EARLY:
                log.append(cname(c))
        return got

    def disguise(self, p):
        names = [cname(c) for c in p.hand]
        kinds = [getattr(c, "kind", "") for c in p.hand]
        foes = [q for q in self.alive_players() if side(p, q) < 0]
        ctx = (p._char.name, p.role, p.hp, p._char.maxhp if hasattr(p._char, "maxhp") else 0, len(names), names.count("殺"),
               sum(1 for k in kinds if k == "trick"), sum(1 for n in names if n in AOE), sum(1 for k in kinds if k in ("weapon", "armor", "horse")),
               len(foes), len(self.alive_players()), max((len(q.hand) for q in foes), default=0), min((q.hp for q in foes), default=9),
               names.count("桃") + names.count("酒"), names.count("閃"))
        super().disguise(p)
        if p.disguise:
            self._dg_cur = [p, p.disguise[0].name, ctx, {q.idx: worth(q) for q in self.players}]

    def take_turn(self, p):
        self._dg_cur = None
        try:
            super().take_turn(p)
        finally:
            cur = self._dg_cur
            if cur is not None:
                me, hero, ctx, v0 = cur
                delta = sum(side(me, q) * (worth(q) - v0[q.idx]) for q in self.players)
                self._dg_log.append([me.idx, hero, ctx, round(delta, 1)])
                self._dg_cur = None


def play(a):
    seed, n = a
    rng = random.Random(seed * 7919 + 13)
    names = rng.sample(list(ROSTER), n)
    lord = rng.randrange(n)
    g = StatGame([DgAgent() for _ in range(n)], max_rounds=100, seed=seed, chars=[ROSTER[x]() for x in names], lord_seat=lord)
    g._early = [[] for _ in range(n)]
    g._dg_log, g._dg_cur = [], None
    g._xrng = random.Random(seed * 31 + 7)
    w = g.run()
    ps = [(q._char.name, q.role, CAMP.get(q.role) == w, (q.idx - lord) % n, tuple(g._early[q.idx]), q.dmg_total, q.alive) for q in g.players]
    dg = [(hero, ctx, d, ps[i][2]) for i, hero, ctx, d in g._dg_log]
    return ps, dg, g.round


def main():
    global EARLY
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=2000)
    ap.add_argument("--players", type=int, default=5)
    ap.add_argument("--seed0", type=int, default=500000)
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--early", type=int, default=7)
    ap.add_argument("--out", default="priostat.pkl")
    a = ap.parse_args()
    EARLY = a.early
    t = time.time()
    with Pool(a.procs, initializer=_init, initargs=(a.early,)) as pool:
        res = pool.map(play, [(s, a.players) for s in range(a.seed0, a.seed0 + a.games)], chunksize=16)
    with open(a.out, "wb") as f:
        pickle.dump(res, f)
    nd = sum(len(r[1]) for r in res)
    print(f"{len(res)} 局, {nd} 次偽裝, 平均 {sum(r[2] for r in res) / len(res):.1f} 輪, {time.time() - t:.0f} 秒 → {a.out}")


def _init(early):
    global EARLY
    EARLY = early


if __name__ == "__main__":
    main()
