"""對戰測試台: 量某位武將在「有策略 / 沒策略」下的勝率。

python arena.py 武將名 [--games 2000] [--players 5] [--seed0 0] [--opp-strategies] [--base-only] [--role 主公|忠臣|反賊|內奸]
  對手一律是 level 4 通用 AI (預設不吃策略,避免目標移動;加 --opp-strategies 則對手也用各自策略)。
  該武將每局隨機座位 / 身分,兩組 (通用 vs 策略) 用相同的種子成對比較。
  勝利判定: 主公/忠臣 = 主公陣營贏、反賊 = 反賊贏、內奸 = 內奸贏。
"""
import argparse
import math
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")
from characters import ROSTER
from engine import Game
from strategy_agent import StrategyAgent

CAMP = {"主公": "主公陣營", "忠臣": "主公陣營", "反賊": "反賊", "內奸": "內奸"}


def play(target, seed, n, use_strategy, opp_strategies=False, level=4, force_role=None, variant=0):
    rng = random.Random(seed * 7919 + 13)
    others = [k for k in ROSTER if k != target]
    names = rng.sample(others, n - 1)
    seat = rng.randrange(n)
    names.insert(seat, target)
    agents = [StrategyAgent(level, use_strategy if i == seat else opp_strategies) for i in range(n)]
    g = Game(agents, max_rounds=200, seed=seed, chars=[ROSTER[x]() for x in names], role_variant=variant)
    if force_role:   # 換身分: 與目標座位的身分對調 (開局前)
        for q in g.players:
            if q.role == force_role and q.idx != seat:
                q.role, g.players[seat].role = g.players[seat].role, q.role
                break
        g.lord = next(q for q in g.players if q.role == "主公")
        g.revealed = {g.lord.idx: "主公"}
    role = g.players[seat].role
    w = g.run()
    return role, CAMP.get(role) == w, g.round


def wilson(k, n, z=1.96):
    if n == 0:
        return 0, 0, 0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, (c - m) / d, (c + m) / d


def run_set(target, games, players, seed0, use_strategy, opp, force_role=None):
    res = {}
    wins = tot = 0
    for s in range(seed0, seed0 + games):
        n = players if players else random.Random(s).choice([4, 5, 5, 6, 6, 7, 8])
        role, win, rounds = play(target, s, n, use_strategy, opp, force_role=force_role, variant=s % 2)
        r = res.setdefault(role, [0, 0])
        r[1] += 1
        r[0] += win
        wins += win
        tot += 1
    return wins, tot, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--games", type=int, default=2000)
    ap.add_argument("--players", type=int, default=0, help="0=隨機 4~8 人")
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--opp-strategies", action="store_true")
    ap.add_argument("--base-only", action="store_true")
    ap.add_argument("--role", default=None)
    a = ap.parse_args()
    if a.name not in ROSTER:
        sys.exit("沒有這位武將: " + a.name)
    out = []
    for label, us in (("通用", False), ("策略", True)):
        if a.base_only and us:
            continue
        w, t, res = run_set(a.name, a.games, a.players, a.seed0, us, a.opp_strategies, a.role)
        p, lo, hi = wilson(w, t)
        by = " ".join(f"{r}{v[0]}/{v[1]}={v[0] / v[1]:.0%}" for r, v in sorted(res.items()))
        print(f"[{label}] {a.name}: 勝率 {p:.1%} (95% 區間 {lo:.1%}~{hi:.1%}, n={t})  依身分: {by}")
        out.append(p)
    if len(out) == 2:
        print(f"差 {100 * (out[1] - out[0]):+.1f} 個百分點")


if __name__ == "__main__":
    main()
