"""武將專屬策略掛鉤。

StrategyAgent 是 LeveledAgent 加上「依武將查表」: 每個決策點先問 strategies/ 裡該武將的策略檔
有沒有同名方法,有且回傳值不是 NotImplemented 就採用,否則走原本的通用 AI。

策略檔: strategies/<武將名>.py,裡面寫一個 class Strategy,只需實作想接管的方法。
可接管的方法 (簽名和 ai.py 的代理介面相同,多一個 self=代理本身):
    act(self, g, p, options) / respond(self, g, p, need, cands, ctx) / choose_skill(self, g, p, skill)
    choose_mode / choose_option / choose_count / choose_discard / choose_from / choose_target / choose_offturn / pick_pile ...
另外可提供 act_filter(self, g, p, options) -> 過濾後的 options 索引 list (不接管,只縮小通用 AI 的選擇)。
"""
import importlib
import os

from ai import LeveledAgent

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies")
_cache = {}


def strategy_for(name):
    if name in _cache:
        return _cache[name]
    s = None
    fn = os.path.join(_DIR, name.replace("&", "_") + ".py")
    if os.path.exists(fn):
        mod = importlib.import_module("strategies." + name.replace("&", "_"))
        s = mod.Strategy()
    _cache[name] = s
    return s


def reload_all():
    _cache.clear()
    import sys
    for k in [k for k in sys.modules if k.startswith("strategies.")]:
        del sys.modules[k]


def _hook(method):
    def f(self, g, p, *a, **k):
        s = strategy_for(p._char.name) if getattr(p, "_char", None) is not None and self.use_strategy else None
        h = getattr(s, method, None) if s else None
        if h:
            r = h(self, g, p, *a, **k)
            if r is not NotImplemented:
                return r
        return getattr(LeveledAgent, method)(self, g, p, *a, **k)
    f.__name__ = method
    return f


class StrategyAgent(LeveledAgent):
    use_strategy = True

    def __init__(self, level=4, use_strategy=True):
        super().__init__(level)
        self.use_strategy = use_strategy

    def act(self, g, p, options):   # 先讓策略縮小選項,再走原本流程
        s = strategy_for(p._char.name) if getattr(p, "_char", None) is not None and self.use_strategy else None
        flt = getattr(s, "act_filter", None) if s else None
        if flt:
            keep = flt(self, g, p, options)
            if keep is not None and len(keep) < len(options):
                if not keep:
                    return None
                sub = [options[i] for i in keep]
                r = _hook("act")(self, g, p, sub)
                return None if r is None else keep[r]
        return _hook("act")(self, g, p, options)


for _m in ("respond", "choose_skill", "choose_mode", "choose_option", "choose_count", "choose_discard", "choose_from",
           "choose_target", "choose_offturn", "pick_pile", "choose_dir", "choose_x", "choose_chain", "show_card", "choose_give", "choose_borrow"):
    if hasattr(LeveledAgent, _m):
        setattr(StrategyAgent, _m, _hook(_m))
