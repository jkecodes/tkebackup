"""孟獲: 體力上限 = 手牌數 + 1 (隨時變動,體力超過上限會被砍掉); 不用棄牌; 回合內出過錦囊,回合結束扣 1 點體力。

打法重點
- 手牌就是血: 手牌數掉到「體力 - 1」以下,每少一張就少一滴血。所以只出「多出來的」牌 (上限 - 體力 = 可以出的張數)。
  通用 AI 不知道這件事,把手牌打光等於自己砍血。
- 錦囊是「整回合只扣一次血」: 要嘛整回合不出,要嘛攢到夠多張一次出完 (扣 1 點換好幾張錦囊)。
  通用 AI 每回合出一兩張就扣 1 點,兩回合掉到 2 血之後再也不敢出錦囊。
  手上有反擊 / 調虎離山時,回合結束那 1 點可以轉給敵人,所以直接開錦囊回合。
- 桃: 出掉一張牌上限也 -1,所以要有 2 張以上的空間才真的補得到血。
- 沒有多餘手牌時被打不要出閃: 出閃少一張牌一樣掉 1 血,不如留著牌 (1 血時上限不會再砍,照常出閃)。
"""
import os

from ai_pro import SkillAct, fn, is_sha, real

K = int(os.environ.get("MH_K", "3"))          # 至少能出幾張錦囊才開「錦囊回合」
HPMIN = int(os.environ.get("MH_HP", "3"))     # 體力至少多少才開錦囊回合
BUF = int(os.environ.get("MH_BUF", "0"))      # 額外多留幾張手牌當緩衝 (防被拆 / 被順)
HOARD = os.environ.get("MH_HOARD", "1") == "1"   # 只出「多出來的」手牌
FREE = os.environ.get("MH_FREE", "0") == "1"     # 錦囊不攢,有空間就出
REACT = {"反擊", "調虎離山", "占卜", "無懈可擊"}


class Strategy:
    def act_filter(self, agent, g, p, options):
        room = p.maxhp - p.hp - BUF          # 還能出幾張牌而不掉血
        played = p.turn_flags.get("tricks", 0)
        foes = agent.foes_of(g, p)
        tricks = {id(c) for c, t in options if not isinstance(c, SkillAct) and getattr(c, "kind", "") == "trick" and fn(real(c)) not in REACT}
        mode = played > 0 or FREE
        if not mode and p.hp >= HPMIN and min(len(tricks), room) >= K:
            mode = True
        if not mode and foes and room >= 1 and tricks and p.hp >= 2 and any(fn(c) in ("反擊", "調虎離山") for c in p.hand):
            mode = True   # 回合結束扣的那 1 點可以轉給敵人
        keep = []
        for i, (c, t) in enumerate(options):
            if isinstance(c, SkillAct):
                keep.append(i)
                continue
            n = fn(real(c))
            kill = hasattr(t, "hp") and t.hp <= 1 and p.hp >= 2 and agent.tscore(g, p, t) > -100 and (is_sha(real(c)) or n in ("決鬥", "火攻"))
            if n in ("桃", "酒") and not kill:
                ok = room + BUF >= 2
            elif getattr(c, "kind", "") == "trick":
                ok = (mode and (room >= 1 or not HOARD)) or (kill and played > 0)
            else:
                ok = room >= 1 or kill or not HOARD
            if ok:
                keep.append(i)
        return keep

    def respond(self, agent, g, p, need, cands, ctx):
        if need == "閃" and cands and p.hp >= 2 and p.maxhp - p.hp <= 0 and ctx.get("attacker") is not None:
            return None
        return NotImplemented
