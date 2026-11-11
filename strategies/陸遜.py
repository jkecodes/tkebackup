"""陸遜: 每回合一次,錦囊牌 (無中生有以外) 可以當無中生有。

打法重點
- 通用 AI 只在「這張錦囊本來就打算出、而且沒有別的事可做」時才順便轉成無中生有,
  像強化 / 降雷 / 借刀殺人 / 閃電這類留在手上的牌永遠不會被轉掉 → 技能大多數回合沒發動。
- 改成每回合一開始就把手上最不值錢的錦囊轉成無中生有 (1 張換 2 張),先抽牌再決定怎麼打。
"""
import os

from ai_pro import SkillAct

TH = float(os.environ.get("LX_TH", "200"))   # 保留價值 <= 這個的錦囊才拿去轉


class Strategy:
    def act(self, agent, g, p, options):
        if p.turn_flags.get("lx"):
            return NotImplemented
        vs = [i for i, (c, t) in enumerate(options)
              if not isinstance(c, SkillAct) and c.name == "無" and getattr(c, "orig", None) is not None]
        if not vs:
            return NotImplemented
        i = min(vs, key=lambda i: agent.keep_val(g, p, options[i][0]))
        if agent.keep_val(g, p, options[i][0]) > TH:
            return NotImplemented
        return i
