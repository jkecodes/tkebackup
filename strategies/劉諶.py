"""劉諶: 少抽 1 張 → 本回合所有手牌都能當決鬥; 決鬥造成傷害雙方各抽 1 張 (一次打 2 點以上技能就失效)。

打法重點
- 殺只佔牌堆約 6%: 對手 4 張手牌時約 78% 拿不出殺。每張「廢牌」當決鬥約 0.8 點傷害,打中還補 1 張牌回來繼續決鬥,
  是一條會自己續航的傷害鏈。通用 AI 的問題:
  * 先把殺打掉才決鬥 → 決鬥被對方出殺時沒有殺可以回,白吃傷害。改成「殺留在手上當後盾,廢牌決鬥打完才出殺」。
  * 不看自己血量: 1 血沒有殺還在決鬥 (每次約 2 成機率自殺)。改成沒有殺當後盾時血量夠才決鬥。
  * 目標只看血量: 改成手牌少的優先 (手牌越少越拿不出殺)。
  * 用不到的裝備 / 強化 不會拿去決鬥: 一律當決鬥材料 (強化 / 流星錘會讓決鬥變 2 點而讓技能失效,決鬥打完才用)。
- 曹沖 / 鄧艾在場 (連續出錦囊會被罰) 時交給通用 AI。
"""
import os

from ai_pro import SkillAct, fn, is_sha, real

MINHP = int(os.environ.get("LC_MINHP", "1"))     # 手上沒有殺當後盾時,體力 >= 這個才決鬥
HW = float(os.environ.get("LC_HW", "0"))         # 目標每多 1 張手牌扣幾分 (越多越可能有殺)
MINFOD = int(os.environ.get("LC_MINFOD", "1"))   # 抽牌前手上至少幾張決鬥材料才發動少抽
KEEP = {"桃", "酒", "無懈可擊", "反擊", "調虎離山", "占卜", "發憤圖強", "偽裝"}   # 不拿去決鬥的牌
LATE = {"強化", "流星錘"}                         # 決鬥打完才用 (會讓決鬥變 2 點 → 技能失效)


def _is_view(c):
    return not isinstance(c, SkillAct) and getattr(c, "orig", None) is not None and c.name == "決"


class Strategy:
    _busy = False

    def _hazard(self, g, p):
        return any(q._char.name in ("曹沖", "鄧艾") for q in g.others(p))

    def _generic(self, agent, g, p, options, idxs):
        if not idxs:
            return None
        self._busy = True
        try:
            r = agent.act(g, p, [options[i] for i in idxs])
        finally:
            self._busy = False
        return None if r is None else idxs[r]

    def choose_skill(self, agent, g, p, skill):
        if skill != "劉諶-少抽一張":
            return NotImplemented
        if self._hazard(g, p):
            return NotImplemented
        if not agent.foes_of(g, p):
            return False
        if p.hp < MINHP and not any(is_sha(c) for c in p.hand):
            return False
        return sum(1 for c in p.hand if fn(c) not in KEEP and not is_sha(c)) >= MINFOD

    def act(self, agent, g, p, options):
        if self._busy or not p.turn_flags.get("lc") or self._hazard(g, p):
            return NotImplemented
        views = [i for i, (c, t) in enumerate(options) if _is_view(c)]
        if not views:
            return NotImplemented
        vs = set(views)
        real_sha = {id(c) for c, t in options if not _is_view(c) and is_sha(c)}   # 還能正常打出去的殺
        # 1. 先做一般該做的事 (抽牌 / 回血 / 裝備 / 拆順 …), 但殺、強化、流星錘先留著
        hold = lambda c: not isinstance(c, SkillAct) and (is_sha(c) or fn(real(c)) in LATE)
        r = self._generic(agent, g, p, options, [i for i, (c, t) in enumerate(options) if i not in vs and not hold(c)])
        if r is not None:
            return r
        # 2. 廢牌當決鬥
        best, bs = None, -1e9
        off = g.equip_off()
        for i in views:
            c, t = options[i]
            o = c.orig
            n = fn(o)
            if n in KEEP or n in LATE or not hasattr(t, "hp"):
                continue
            if is_sha(o) and id(o) in real_sha:
                continue   # 這張殺還能當殺打: 留著當後盾,最後再出
            backup = sum(1 for h in p.hand if is_sha(h) and h is not o)
            if not backup and p.hp < MINHP:
                continue
            ts = agent.tscore(g, p, t)
            if ts <= -100 or t.char.damage_only_sha or t.char.plain_immune(g, t) or (not off and "緩衝盾" in t.armor_names()):
                continue
            sc = ts - HW * len(t.hand) - agent.keep_val(g, p, o) / 50.0 - (40 if is_sha(o) else 0)
            if sc > bs:
                bs, best = sc, i
        if best is not None:
            return best
        # 3. 決鬥打完: 出殺 / 強化 / 流星錘等剩下的
        return self._generic(agent, g, p, options, [i for i in range(len(options)) if i not in vs])
