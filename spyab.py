"""內奸打法對照測試: 內奸那個座位換上新設定,其他人不變,同種子成對比較內奸勝率。

python spyab.py 設定.json [--games 6000] [--players 5] [--seed0 0] [--procs 6]
  設定.json 例: {"spy": {"b": 30, "dhp": 2, "margin": 0, "block": 0, "nosave": 1}}  (逐項 setattr 到內奸座位的 ProAgent)
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

VAR = {}


def _init(path):
    global VAR
    VAR = json.load(open(path, encoding="utf-8"))


def play(seed, n, on):
    rng = random.Random(seed * 7919 + 13)
    names = rng.sample(list(ROSTER), n)
    lord = rng.randrange(n)
    mk = lambda ags: Game(ags, max_rounds=100, seed=seed, chars=[ROSTER[x]() for x in names], lord_seat=lord)
    probe = mk([ProAgent() for _ in range(n)])   # 身分是建局時用種子洗的: 先建一局看內奸坐哪
    seat = next(p.idx for p in probe.players if p.role == "內奸")
    agents = [ProAgent() for _ in range(n)]
    if on:
        for k, v in VAR.items():
            setattr(agents[seat], k, v)
    g = mk(agents)
    w = g.run()
    return w == "內奸", bool(getattr(g.players[seat], "duel1", False))


def job(a):
    return play(a[0], a[1], False), play(a[0], a[1], True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("var")
    ap.add_argument("--games", type=int, default=6000)
    ap.add_argument("--players", type=int, default=5)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--procs", type=int, default=6)
    a = ap.parse_args()
    with Pool(a.procs, initializer=_init, initargs=(a.var,)) as pool:
        res = pool.map(job, [(s, a.players) for s in range(a.seed0, a.seed0 + a.games)], chunksize=16)
    n = len(res)
    d = [r[1][0] - r[0][0] for r in res]
    m = sum(d) / n
    se = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1) / n)
    print(f"{a.players}人 內奸勝率 {sum(r[0][0] for r in res) / n:.1%} → {sum(r[1][0] for r in res) / n:.1%}  差 {100 * m:+.2f} ± {100 * se:.2f} pp"
          f"  撐到單挑 {sum(r[0][1] for r in res) / n:.1%} → {sum(r[1][1] for r in res) / n:.1%} (n={n})")


if __name__ == "__main__":
    main()
