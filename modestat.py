"""休閒模式 (暗殺目標 / 抓叛徒) 的電腦對戰統計。

python modestat.py hunt|traitor [--games 600] [--players 5] [--level 5] [--olevel N]
  座位 0 用 --level,其他人用 --olevel (沒給就全部同一個難度)。
"""
import argparse
import collections
import random
import sys
from multiprocessing import Pool

sys.stdout.reconfigure(encoding="utf-8")
from ai_pro import ProAgent
from characters import ROSTER
from engine import Game


def play(a):
    seed, n, mode, lv, olv = a
    rng = random.Random(seed * 7919 + 13)
    names = rng.sample(list(ROSTER), n)
    g = Game([ProAgent(lv if i == 0 else olv) for i in range(n)], max_rounds=60, seed=seed, chars=[ROSTER[x]() for x in names], role_mode=mode)
    w = g.run()
    p0 = g.players[0]
    if mode == "hunt":
        return w, w == "P0", g.round, any("親手殺死了自己的暗殺目標" in x for x in g.logs), p0.role
    return w, w == p0.role, g.round, False, p0.role


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode")
    ap.add_argument("--games", type=int, default=600)
    ap.add_argument("--players", type=int, default=5)
    ap.add_argument("--level", type=int, default=5)
    ap.add_argument("--olevel", type=int, default=None)
    ap.add_argument("--seed0", type=int, default=0)
    a = ap.parse_args()
    olv = a.level if a.olevel is None else a.olevel
    with Pool(6) as pool:
        res = pool.map(play, [(s, a.players, a.mode, a.level, olv) for s in range(a.seed0, a.seed0 + a.games)], chunksize=8)
    n = len(res)
    C = collections.Counter(("某位玩家" if r[0].startswith("P") else r[0]) for r in res)
    out = f"{a.mode} {a.players}人 L{a.level} vs L{olv}: 平均 {sum(r[2] for r in res) / n:.1f} 輪  結果 " + " ".join(f"{k}{100 * v / n:.0f}%" for k, v in C.most_common(4))
    if a.mode == "hunt":
        out += f"  靠殺目標結束 {100 * sum(r[3] for r in res) / n:.0f}%  座位0勝率 {100 * sum(r[1] for r in res) / n:.1f}% (平均應為 {100 / a.players:.0f}%)"
    else:
        t = [r for r in res if r[4] == "叛徒"]
        gd = [r for r in res if r[4] == "好人"]
        out += f"  座位0當叛徒勝率 {100 * sum(r[1] for r in t) / max(1, len(t)):.0f}% (n={len(t)})  當好人勝率 {100 * sum(r[1] for r in gd) / max(1, len(gd)):.0f}%"
    print(out)


if __name__ == "__main__":
    main()
