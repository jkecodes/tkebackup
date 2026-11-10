"""ProAgent 版對戰測試台 (線上電腦用的就是 ProAgent): 量某位武將「有策略 / 沒策略」的勝率,同種子成對比較。

python arena_pro.py 武將名 [--games 800] [--players 5] [--seed0 0] [--procs 6]
  對手一律是 5 級 ProAgent、不吃策略 (避免目標移動)。目標武將每局隨機座位 / 身分,兩組用相同種子。
驗證 (README 的規則): 調參用 --seed0 0,驗證用沒調過的 --seed0 100000 --games 2000,提升 >= +1.5 個百分點才保留。
"""
import argparse
import math
import random
import sys
from multiprocessing import Pool

sys.stdout.reconfigure(encoding="utf-8")
from ai_pro import ProAgent
from characters import ROSTER
from engine import Game

CAMP = {"主公": "主公陣營", "忠臣": "主公陣營", "反賊": "反賊", "內奸": "內奸"}


def play(target, seed, n, use_strategy):
    rng = random.Random(seed * 7919 + 13)
    names = rng.sample([k for k in ROSTER if k != target], n - 1)
    seat = rng.randrange(n)
    names.insert(seat, target)
    agents = []
    for i in range(n):
        a = ProAgent()
        a.use_strategy = use_strategy if i == seat else False
        agents.append(a)
    g = Game(agents, max_rounds=100, seed=seed, chars=[ROSTER[x]() for x in names], lord_seat=rng.randrange(n))
    role = g.players[seat].role
    return role, CAMP.get(role) == g.run()


def job(a):
    target, seed, n = a
    return play(target, seed, n, False), play(target, seed, n, True)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, (c - m) / d, (c + m) / d


def measure(target, games=800, n=5, seed0=0, procs=6):
    with Pool(procs) as pool:
        res = pool.map(job, [(target, s, n) for s in range(seed0, seed0 + games)], chunksize=8)
    out = []
    for k in (0, 1):
        w = sum(r[k][1] for r in res)
        by = {}
        for r in res:
            b = by.setdefault(r[k][0], [0, 0]); b[1] += 1; b[0] += r[k][1]
        out.append((w, len(res), by))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--games", type=int, default=800)
    ap.add_argument("--players", type=int, default=5)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--procs", type=int, default=6)
    a = ap.parse_args()
    if a.name not in ROSTER:
        sys.exit("沒有這位武將: " + a.name)
    ps = []
    for label, (w, t, by) in zip(("通用", "策略"), measure(a.name, a.games, a.players, a.seed0, a.procs)):
        p, lo, hi = wilson(w, t)
        ps.append(p)
        print(f"[{label}] {a.name}: 勝率 {p:.1%} (95% {lo:.1%}~{hi:.1%}, n={t})  " + " ".join(f"{r}{v[0]}/{v[1]}={v[0] / v[1]:.0%}" for r, v in sorted(by.items())))
    print(f"差 {100 * (ps[1] - ps[0]):+.1f} 個百分點")


if __name__ == "__main__":
    main()
