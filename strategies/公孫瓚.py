"""公孫瓚: 閃可以當調虎離山。

打法重點
- 通用 AI 從來不會把閃當調虎離山 (它只認真正的 反 / 調 / 占),等於沒有技能。
- 閃只佔牌堆約 3%,調虎離山轉出去幾乎一定是「該方向第一個人」中招。所以只要左右鄰居有一邊是敵人:
  * 任何傷害 (決鬥 / 南蠻 / 火攻 …) 都用閃轉給他: 同樣花一張閃,不但不扣血還讓敵人扣血。
  * 被殺時不出閃,等「要受到傷害時」再把閃當調虎離山 (比直接閃多賺敵人一滴血)。
    風險是被無懈 (白吃傷害),所以血少又只有一張閃時還是老實出閃。
- 兩邊鄰居都是隊友就照一般打法 (出閃 / 硬吃),快死了才轉給隊友 (不轉給主公)。
"""
import os

TH = float(os.environ.get("GSZ_TH", "0.4"))       # 方向分數超過這個才轉
SAFE = int(os.environ.get("GSZ_SAFE", "3"))       # 體力 >= 這個才敢「不出閃改轉傷害」(只有一張閃時)


class Strategy:
    def _best(self, agent, g, p, n=1):
        return max(agent.dir_score(g, p, "L", n), agent.dir_score(g, p, "R", n))

    def respond(self, agent, g, p, need, cands, ctx):
        if need == "受傷響應":
            r = agent.react_damage(g, p, cands, ctx)
            if r:
                return r
            shan = [c for c in cands if c.name == "閃"]
            if not shan:
                return None
            n = ctx["n"]
            sc = self._best(agent, g, p, n)
            if sc > TH or (n >= p.hp and sc > -2.2):
                return shan[0]
            return None
        if need == "閃" and cands and ctx.get("attacker") not in (None, p):
            shan = [c for c in p.hand if c.name == "閃"]
            if shan and (p.hp >= SAFE or len(shan) >= 2):
                usable = g._reaction_cands(p)[0]
                if any(c.name == "閃" for c in usable) and self._best(agent, g, p) > TH:
                    return None   # 不閃,等受傷時把閃當調虎離山轉出去
        return NotImplemented
