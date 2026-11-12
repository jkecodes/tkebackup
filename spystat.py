"""內奸診斷: 全電腦自我對戰,統計內奸怎麼輸的。 python spystat.py [--games 4000] [--players 5]"""
import argparse, collections, random, sys
from multiprocessing import Pool
sys.stdout.reconfigure(encoding="utf-8")
from ai_pro import ProAgent
from characters import ROSTER
from engine import Game


class G(Game):
    def die(self, tgt, src):
        if tgt.role == "內奸":
            self._spy = (len(self.alive_players()) + 1, src.role if src else "-", self.round,
                         sum(1 for q in self.alive_players() if q.role == "反賊"), sum(1 for q in self.alive_players() if q.role == "忠臣"), self.lord.hp)
        if tgt.role == "主公":
            self._lordkill = (src.role if src else "-", len(self.alive_players()) + 1)
        super().die(tgt, src)


def play(a):
    seed, n = a
    rng = random.Random(seed * 7919 + 13)
    g = G([ProAgent() for _ in range(n)], max_rounds=100, seed=seed, chars=[ROSTER[x]() for x in rng.sample(list(ROSTER), n)], lord_seat=rng.randrange(n))
    g._spy = g._lordkill = None
    w = g.run()
    spy = next(p for p in g.players if p.role == "內奸")
    return w, g._spy, g._lordkill, getattr(spy, "duel1", False), spy.alive, g.round, spy.dmg_total


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--games", type=int, default=4000); ap.add_argument("--players", type=int, default=5); ap.add_argument("--seed0", type=int, default=700000)
    a = ap.parse_args()
    with Pool(6) as pool:
        res = pool.map(play, [(s, a.players) for s in range(a.seed0, a.seed0 + a.games)], chunksize=16)
    n = len(res); C = collections.Counter
    print(f"{a.players} 人 {n} 局: 勝方", {k: f"{100 * v / n:.1f}%" for k, v in C(r[0] for r in res).most_common()})
    duel = [r for r in res if r[3]]
    print(f"內奸撐到和主公單挑 {100 * len(duel) / n:.1f}%, 單挑贏 {100 * sum(r[0] == '內奸' for r in duel) / max(1, len(duel)):.1f}%")
    dead = [r for r in res if r[1]]
    print(f"內奸死亡 {100 * len(dead) / n:.1f}%: 死的時候場上人數", sorted(C(r[1][0] for r in dead).items()), " 兇手", C(r[1][1] for r in dead).most_common())
    print("  死時 (反賊數, 忠臣數):", C((r[1][3], r[1][4]) for r in dead).most_common(8))
    print("  死在第幾輪:", sorted(C(min(r[1][2], 8) for r in dead).items()))
    la = [r for r in res if r[4] and r[0] == "反賊"]
    print(f"內奸還活著但反賊贏 (主公先死) {100 * len(la) / n:.1f}%: 殺主公的人", C(r[2][0] for r in la if r[2]).most_common(), " 當時人數", sorted(C(r[2][1] for r in la if r[2]).items()))


if __name__ == "__main__":
    main()
