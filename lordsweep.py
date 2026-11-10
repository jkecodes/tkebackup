"""掃描「主公體力加成」對各陣營勝率的影響 (全電腦 ProAgent 5 級自我對戰)。
python lordsweep.py 人數 加成列表(逗號) [場數] [變體]   例: python lordsweep.py 4 0,1,2,3 3000"""
import collections, random, sys
from multiprocessing import Pool
sys.stdout.reconfigure(encoding="utf-8")
from ai_pro import ProAgent
from characters import ROSTER
from engine import Game, ROLES

def job(a):
    n, s, lb, var = a
    rng = random.Random(s * 7919 + 13); names = rng.sample(sorted(ROSTER), n)
    g = Game([ProAgent() for _ in range(n)], seed=s, chars=[ROSTER[x]() for x in names], lord_seat=s % n, max_rounds=100, lord_bonus=lb, role_variant=var)
    return g.run()

if __name__ == "__main__":
    n = int(sys.argv[1]); lbs = [int(x) for x in sys.argv[2].split(",")]
    G = int(sys.argv[3]) if len(sys.argv) > 3 else 3000; var = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    for lb in lbs:
        with Pool(6) as p: res = p.map(job, [(n, s, lb, var) for s in range(100000, 100000 + G)], chunksize=10)
        c = collections.Counter(res)
        rl = ROLES[n][var % len(ROLES[n])]; nc = sum(r in ("主公", "忠臣") for r in rl); nr = rl.count("反賊"); ns = rl.count("內奸")
        gap = c['主公陣營'] / nc - c['反賊'] / nr   # 每人平均勝率差 (主公陣營 - 反賊): 越接近 0 越平衡
        print(f"{n}人 變體{var} 主公+{lb} ({G}場) | 主公陣營 {c['主公陣營']/G:.1%} 反賊 {c['反賊']/G:.1%} 內奸 {c['內奸']/G:.1%}  | 每人 主公陣營 {c['主公陣營']/nc/G:.1%} 反賊 {c['反賊']/nr/G:.1%} 內奸 {c['內奸']/ns/G:.1%} | 每人差 {100*gap/G:+.1f}", flush=True)
