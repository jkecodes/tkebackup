"""ProAgent 設定對照測試: 一個座位換上新設定 (卡牌優先度表 / 武將集火加分 / 偽裝選擇表),其他座位用原設定,同種子成對比較勝率。

python prioab.py 設定.json [--games 10000] [--players 5] [--seed0 0] [--procs 6]
  設定.json = {"pri": {牌名: 優先度}, "threat": {武將: 加分}, ...}  → 逐項 setattr 到受測座位的 ProAgent 上。
  武將每局隨機抽 (受測座位也是隨機武將),所以量到的是「整體」的勝率變化。
"""
import argparse
import json
import math
import random
import sys
from multiprocessing import Pool

sys.stdout.reconfigure(encoding="utf-8")
from ai_pro import ProAgent
from characters import ROSTER
from engine import Game

CAMP = {"主公": "主公陣營", "忠臣": "主公陣營", "反賊": "反賊", "內奸": "內奸"}
VAR = {}


def _init(path):
    global VAR
    VAR = json.load(open(path, encoding="utf-8"))


def play(seed, n, on):
    rng = random.Random(seed * 7919 + 13)
    names = rng.sample(list(ROSTER), n)
    seat, lord = rng.randrange(n), rng.randrange(n)
    agents = [ProAgent() for _ in range(n)]
    if on:
        for k, v in VAR.items():
            setattr(agents[seat], k, v)
    g = Game(agents, max_rounds=100, seed=seed, chars=[ROSTER[x]() for x in names], lord_seat=lord)
    role = g.players[seat].role
    return role, CAMP.get(role) == g.run()


def job(a):
    return play(a[0], a[1], False), play(a[0], a[1], True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("var")
    ap.add_argument("--games", type=int, default=10000)
    ap.add_argument("--players", type=int, default=5)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--procs", type=int, default=6)
    a = ap.parse_args()
    with Pool(a.procs, initializer=_init, initargs=(a.var,)) as pool:
        res = pool.map(job, [(s, a.players) for s in range(a.seed0, a.seed0 + a.games)], chunksize=16)
    n = len(res)
    d = [r[1][1] - r[0][1] for r in res]
    m = sum(d) / n
    se = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1) / n)
    by = {}
    for r in res:
        b = by.setdefault(r[0][0], [0, 0, 0]); b[0] += r[0][1]; b[1] += r[1][1]; b[2] += 1
    print(f"原 {sum(r[0][1] for r in res) / n:.1%} → 新 {sum(r[1][1] for r in res) / n:.1%}  差 {100 * m:+.2f} ± {100 * se:.2f} pp (n={n})  "
          + " ".join(f"{k}{100 * (v[1] - v[0]) / v[2]:+.1f}" for k, v in sorted(by.items())))


if __name__ == "__main__":
    main()
