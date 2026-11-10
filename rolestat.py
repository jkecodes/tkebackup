"""全電腦 (ProAgent 5 級) 自我對戰,量各陣營勝率; 用環境變數 SGS_EXP 開關 ai_pro 的實驗性打法,同種子比較。
python rolestat.py 5 1500   → 5 人局 1500 場"""
import collections, random, sys
from multiprocessing import Pool
sys.stdout.reconfigure(encoding="utf-8")
from ai_pro import ProAgent
from characters import ROSTER
from engine import Game

def job(a):
    n, s = a
    rng = random.Random(s * 7919 + 13); names = rng.sample(sorted(ROSTER), n)
    try:
        g = Game([ProAgent() for _ in range(n)], seed=s, chars=[ROSTER[x]() for x in names], lord_seat=s % n, max_rounds=100)
        w = g.run(); return w if w in ("主公陣營", "反賊", "內奸") else "其他", g.round
    except Exception as e:
        return "錯誤:" + repr(e)[:60], 0

if __name__ == "__main__":
    n, G = int(sys.argv[1]), int(sys.argv[2]); seed0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    with Pool(6) as p: res = p.map(job, [(n, s) for s in range(seed0, seed0 + G)], chunksize=10)
    c = collections.Counter(r[0] for r in res)
    print(f"{n}人 {G}場 平均{sum(r[1] for r in res)/G:.1f}輪 | " + " ".join(f"{k} {c[k]/G:.1%}" for k in ("主公陣營", "反賊", "內奸")) + (f" | 其他/錯誤 {dict((k,v) for k,v in c.items() if k not in ('主公陣營','反賊','內奸'))}" if set(c) - {"主公陣營", "反賊", "內奸"} else ""))
