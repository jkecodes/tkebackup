"""電腦難度對戰模擬 (不開伺服器): 同一副牌、同樣的武將和身分,只換其中一個座位的難度,比較勝率。

用法:
    python sim_ai.py --games 400 --a 5 --b 4 --opp 4        # 第 5 級 vs 第 4 級 (對手都是第 4 級)
    python sim_ai.py --games 200 --a 5 --b 3 --opp 3 --seed 1000
每個種子打兩場: 受測座位用 a 級、換成 b 級 (其他三位都是 opp 級),座位和身分輪流換。
"""
import argparse
import random
import sys
import time
import traceback
from multiprocessing import Pool

from ai import LeveledAgent
from characters import ROSTER
from engine import Game

CAMP = {"主公": "主公陣營", "忠臣": "主公陣營", "反賊": "反賊", "內奸": "內奸"}


def make_agent(level):
    from ai_pro import ProAgent   # 線上用的就是 ProAgent,難度 1~5 = 逐級開啟進階判斷
    return ProAgent(level)


def play(seed, seat, level, opp, char=None, n=4):
    rng = random.Random(seed * 7919 + 13)
    names = rng.sample(sorted(ROSTER), n)
    if char:   # 指定受測座位的武將 (其他座位如果剛好抽到同一位就換掉)
        if char in names:
            names[names.index(char)] = names[seat]
        names[seat] = char
    agents = [make_agent(level if i == seat else opp) for i in range(n)]
    g = Game(agents, seed=seed, chars=[ROSTER[nm]() for nm in names], lord_seat=seed % n, max_rounds=100)
    w = g.run()
    me = g.players[seat]
    return {"win": CAMP.get(me.role) == w, "role": me.role, "char": names[seat], "rounds": g.round, "winner": w}


def job(args):
    seed, seat, a, b, opp, char = args
    out = []
    for lv in (a, b):
        try:
            out.append(play(seed, seat, lv, opp, char))
        except Exception:
            out.append({"error": traceback.format_exc()})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--a", type=int, default=5)
    ap.add_argument("--b", type=int, default=4)
    ap.add_argument("--opp", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--char", default=None, help="固定受測座位的武將 (可用逗號接多位,各跑一輪)")
    args = ap.parse_args()
    chars = args.char.split(",") if args.char else [None]
    for ch in chars:
        run(args, ch)


def run(args, char):
    jobs = [(args.seed + i, (args.seed + i) // 4 % 4, args.a, args.b, args.opp, char) for i in range(args.games)]
    t0 = time.time()
    with Pool(args.procs) as pool:
        res = pool.map(job, jobs, chunksize=2)
    stat = {args.a: [0, 0], args.b: [0, 0]}   # 勝, 場
    by_role = {}
    errs = []
    for (seed, seat, a, b, opp, _ch), (ra, rb) in zip(jobs, res):
        for lv, r in ((a, ra), (b, rb)):
            if "error" in r:
                errs.append((seed, lv, r["error"]))
                continue
            stat[lv][1] += 1
            stat[lv][0] += r["win"]
            k = (lv, r["role"])
            by_role.setdefault(k, [0, 0])
            by_role[k][1] += 1
            by_role[k][0] += r["win"]
    print(f"[{char or '隨機武將'}] {args.games} 種子, 對手第 {args.opp} 級, 用時 {time.time() - t0:.0f}s")
    for lv in (args.a, args.b):
        w, n = stat[lv]
        print(f"  第 {lv} 級: {w}/{n} = {w / max(1, n):.1%}")
        for role in ("主公", "忠臣", "反賊", "內奸"):
            w2, n2 = by_role.get((lv, role), [0, 0])
            if n2:
                print(f"     {role}: {w2}/{n2} = {w2 / n2:.0%}")
    if errs:
        print(f"錯誤 {len(errs)} 場; 第一個 (種子 {errs[0][0]}, 第 {errs[0][1]} 級):")
        print(errs[0][2])
        sys.exit(1)


if __name__ == "__main__":
    main()
