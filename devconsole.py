"""開發者管理介面的後端 (web/index.html 裡 Ctrl+` 開啟):只有開發者帳號能用,api() 會檢查。
每個動作都記在 DATA/dev_console.log (誰、什麼時候、做了什麼);刪帳號前會先備份資料檔。
api(ctx, tok, d): ctx 是 server 模組的 globals(),回傳 JSON。"""
import json
import math
import os
import shutil
import time


def _find(ctx, key):
    """帳號名稱 (不分大小寫) 或 8 位數 UID -> (帳號 key, 帳號, token, 玩家資料);找不到回傳 None。"""
    A, P = ctx["ACCOUNTS"], ctx["PROFILES"]
    k = key.strip().lower()
    a = A.d.get(k)
    if not a and k.isdigit():
        for kk, aa in A.d.items():
            if str(P.d.get(aa["uuid"], {}).get("uid")) == k:
                k, a = kk, aa
                break
    if not a:
        return None
    return k, a, a["uuid"], P.d.get(a["uuid"], {})


def _backup(ctx):
    d = os.path.join(ctx["DATA"], "bak-devconsole-" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(d, exist_ok=True)
    for f in ("accounts.json", "profiles.json", "social.json"):
        src = os.path.join(ctx["DATA"], f)
        if os.path.exists(src):
            shutil.copy2(src, d)
    return d


def _delete(ctx, me_key, k, a, tok, p):
    P, A, S = ctx["PROFILES"], ctx["ACCOUNTS"], ctx["SOCIAL"]
    if P.dev(tok) == "dev" or k == me_key:
        return "開發者帳號和你自己不能刪"
    bak = _backup(ctx)
    try:
        pid = ctx["Profiles"]._pid(tok)
        ap = os.path.join(ctx["Profiles"].AVATAR_DIR, pid + ".jpg")
        if os.path.exists(ap):
            os.remove(ap)
    except Exception:
        pass
    with P.lock:
        P.d.pop(tok, None)
        P._save()
    with A.lock if hasattr(A, "lock") else P.lock:
        A.d.pop(k, None)
        A.uuids.pop(tok, None)
        A._save()
    with S.lock:
        S.d["u"].pop(k, None)
        for u in S.d["u"].values():   # 別人好友清單 / 請求裡的這個帳號也拿掉
            for f in ("fr", "in", "out"):
                if k in u.get(f, []):
                    u[f] = [x for x in u[f] if x != k]
        for dk in [x for x in S.d["dm"] if k in str(x).lower()]:
            S.d["dm"].pop(dk, None)
        S._save()
    return f"已刪除 {a['user']};備份在 {bak}"


# ---------- GUI 用的 API: 每個動作都回傳 {ok, ...},並記在 dev_console.log ----------
def _log(ctx, me_key, text):
    try:
        with open(os.path.join(ctx["DATA"], "dev_console.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {me_key} [gui] {text[:200]}\n")
    except OSError:
        pass


def _rank_opts(P):
    """段位下拉選單: [{label, rp}],每個小段的最低積分。"""
    out = []
    for i, (nm, lo) in enumerate(P.RANKS):
        hi = P.RANKS[i + 1][1] if i + 1 < len(P.RANKS) else None
        if hi is None:
            out.append({"label": nm, "rp": lo})
            continue
        step = (hi - lo) / 3
        for k in range(3):
            out.append({"label": f"{nm}{3 - k}", "rp": math.ceil(lo + k * step - 1e-9)})
    return out


def _detail(ctx, k, a, t, p):
    P, S, cos = ctx["PROFILES"], ctx["SOCIAL"], ctx["cosmetics"]
    P._ensure_shop(p)
    tier, achs, owned, pres = P.peak_tier(p), p.get("ach", {}), set(p.get("owned", [])), p.get("pres", 0)
    natural = cos.unlocked_ids(tier, achs, owned, pres)
    u = S.d["u"].get(k, {"fr": [], "in": [], "out": []})
    nm = lambda x: {"key": x, "user": (ctx["ACCOUNTS"].d.get(x) or {}).get("user", x + " (已刪除)")}
    return {"ok": True, "key": k, "user": a["user"], "uid": p.get("uid"), "tag": P.dev(t) or "", "lv": P.level(p.get("xp", 0)), "xp": p.get("xp", 0),
            "rp": p.get("rp", 0), "peak_rp": p.get("peak_rp", 0), "rank": P.rank_tag(p), "rank_opts": _rank_opts(P), "coins": p.get("coins", 0), "renown": p.get("renown", 0), "pres": pres, "games": p.get("games", 0), "wins": p.get("wins", 0),
            "lessons": len(p.get("lessons", [])), "ach": achs, "natural": natural, "grant": p.get("dev_grant", []), "revoke": p.get("dev_revoke", []),
            "friends": [nm(x) for x in u.get("fr", [])], "incoming": [nm(x) for x in u.get("in", [])], "outgoing": [nm(x) for x in u.get("out", [])],
            "created": a.get("created", 0)}


def api(ctx, tok, d):
    A, P, S = ctx["ACCOUNTS"], ctx["PROFILES"], ctx["SOCIAL"]
    if P.dev(tok) != "dev":
        return {"ok": False, "error": "沒有權限"}
    me_key = A.uuids.get(tok)
    act = str(d.get("a") or "")
    if act == "players":
        kw = str(d.get("q") or "").strip().lower()
        rows = []
        for k, a in A.d.items():
            p = P.d.get(a["uuid"], {})
            if kw and kw not in k and kw not in a["user"].lower() and kw != str(p.get("uid")):
                continue
            rows.append({"key": k, "user": a["user"], "uid": p.get("uid"), "lv": P.level(p.get("xp", 0)), "rank": P.rank_tag(p), "rp": p.get("rp", 0), "coins": p.get("coins", 0), "tag": P.dev(a["uuid"]) or ""})
        rows.sort(key=lambda r: r["user"].lower())
        return {"ok": True, "players": rows[:200], "total": len(rows)}
    if act == "rooms":
        with ctx["ROOMS_LOCK"]:
            return {"ok": True, "rooms": [{"id": rid, "name": getattr(m, "room_name", "") or rid, "n": len(getattr(m, "humans", []) or []), "solo": bool(getattr(m, "solo", False)),
                                           "playing": bool(getattr(m, "game_active", False))} for rid, m in ctx["ROOMS"].items()]}
    if act == "room_delete":
        rid = str(d.get("id") or "")
        m = ctx["ROOMS"].get(rid)
        if rid == "main" or m is None:
            return {"ok": False, "error": "這個房間不能刪除 (公共房間或已不存在)"}
        m.abort = True; m._ans_ev.set(); m._step_ev.set()
        with ctx["ROOMS_LOCK"]:
            ctx["ROOMS"].pop(rid, None)
        _log(ctx, me_key, "room_delete " + rid)
        return {"ok": True}
    hit = _find(ctx, str(d.get("key") or ""))
    if not hit:
        return {"ok": False, "error": "找不到這個玩家"}
    k, a, t, p = hit
    if act == "detail":
        return _detail(ctx, k, a, t, p)
    _log(ctx, me_key, f"{act} {k} " + json.dumps({x: d[x] for x in d if x not in ("tok", "a", "key")}, ensure_ascii=False))
    if act == "coins":
        try:
            n = int(d.get("n"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "請輸入整數"}
        cur = "renown" if d.get("cur") == "renown" else "coins"
        with P.lock:
            p[cur] = max(0, n if d.get("mode") == "set" else p.get(cur, 0) + n)
            P._save()
    elif act == "ach":
        aid, on = str(d.get("id") or ""), bool(d.get("on"))
        if aid not in ctx["cosmetics"].ACH_BY_ID:
            return {"ok": False, "error": "沒有這個成就"}
        with P.lock:
            got = p.setdefault("ach", {})
            if on:
                got.setdefault(aid, int(time.time()))
            else:
                got.pop(aid, None)   # 收回後,下次對局結算若條件仍然符合還是會重新拿到
            P._save()
    elif act == "cos":
        kind, iid, st = str(d.get("kind") or ""), str(d.get("id") or ""), str(d.get("state") or "")
        if not ctx["cosmetics"].find(kind, iid) or st not in ("default", "grant", "revoke"):
            return {"ok": False, "error": "沒有這個外觀"}
        key = kind + ":" + iid
        with P.lock:
            g, r = [x for x in p.get("dev_grant", []) if x != key], [x for x in p.get("dev_revoke", []) if x != key]
            if st == "grant":
                g.append(key)
            elif st == "revoke":
                r.append(key)
            p["dev_grant"], p["dev_revoke"] = g, r
            P._save()
    elif act == "rp":
        try:
            n = int(d.get("n"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "請輸入整數"}
        if not 0 <= n <= 100000:
            return {"ok": False, "error": "積分要在 0 ~ 100000"}
        with P.lock:
            p["rp"] = n
            p["peak_rp"] = n if d.get("peak") else max(p.get("peak_rp", 0), n)   # 外觀 / 成就看歷史最高,預設只往上加
            P._save()
    elif act == "uid":
        import random
        new = str(d.get("uid") or "").strip()
        with P.lock:
            used = {q.get("uid") for tk, q in P.d.items() if tk != t}
            if not new:   # 留空 = 隨機換一個
                while True:
                    new = str(random.randint(10000000, 99999999))
                    if new not in used:
                        break
            elif not (new.isdigit() and len(new) == 8 and new[0] != "0"):
                return {"ok": False, "error": "UID 必須是 8 位數字,開頭不能是 0"}
            elif new in used:
                return {"ok": False, "error": "這個 UID 已經有人用了"}
            p["uid"] = new
            P._save()
    elif act == "tag":
        want = str(d.get("tag") or "")
        if want not in ("", "dev", "tester"):
            return {"ok": False, "error": "不認識的標籤"}
        if k == me_key:
            return {"ok": False, "error": "不能改自己的標籤"}
        if k in P.DEVS:
            return {"ok": False, "error": "這是寫死在程式裡的開發者,不能在這裡改"}
        with P.lock:
            if want:
                p["tag"] = want
            else:
                p.pop("tag", None)
            P._save()
        if k in P.TESTERS and not want:
            return _detail(ctx, k, a, t, p) | {"note": "這個帳號在程式的測試者名單裡,拿掉標籤後仍會顯示測試者"}
    elif act == "lessons":
        if d.get("mode") == "all":
            P.lesson_clear(t, [L["id"] for L in ctx["lessons"].LESSONS])
        else:
            with P.lock:
                p["lessons"] = []
                P._save()
    elif act in ("friend_add", "friend_remove"):
        o = _find(ctx, str(d.get("other") or ""))
        if not o:
            return {"ok": False, "error": "找不到對方"}
        ok_ = o[0]
        if ok_ == k:
            return {"ok": False, "error": "不能是同一個人"}
        if act == "friend_add":
            with S.lock:
                S._u(k), S._u(ok_)
                S._become(k, ok_)   # 直接成為好友,不用對方同意
        else:
            S.remove(k, ok_)
    elif act == "delete":
        if str(d.get("confirm") or "") != a["user"]:
            return {"ok": False, "error": "請輸入該帳號名稱來確認"}
        msg = _delete(ctx, me_key, k, a, t, p)
        return {"ok": msg.startswith("已刪除"), "msg": msg, "gone": msg.startswith("已刪除")}
    else:
        return {"ok": False, "error": "不認識的動作"}
    return _detail(ctx, k, a, t, p)
