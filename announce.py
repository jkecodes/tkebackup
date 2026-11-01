"""版本更新公告: 伺服器啟動時,如果版本號比上次公告的新,就把 CHANGELOG.md 那一版的內容貼到 Discord。

Webhook 網址不放在程式碼 / repo 裡,只從這兩個地方讀 (都只有伺服器上看得到):
  環境變數 SGS_DISCORD_WEBHOOK
  檔案 SGS_DISCORD_WEBHOOK_FILE (預設 /etc/sgs/discord_webhook,權限 640 root:sgs)
沒設定就什麼都不做,所以本機測試不會誤發公告。網址也不會出現在任何紀錄或 API 回應裡。"""
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request

import view
from version import VERSION, REPO

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(view.DATA, "announced_version.txt")   # 上一次公告到哪一版
LIMIT = 3800   # Discord embed 描述上限 4096,留空間;超過就分成多則訊息
_lock = threading.Lock()


def webhook_url():
    url = os.environ.get("SGS_DISCORD_WEBHOOK", "").strip()
    if not url:
        path = os.environ.get("SGS_DISCORD_WEBHOOK_FILE", "/etc/sgs/discord_webhook")
        try:
            with open(path, encoding="utf-8") as f:
                url = f.read().strip()
        except OSError:
            return ""
    return url if url.startswith("https://discord.com/api/webhooks/") else ""


def section(version, path=None):
    """CHANGELOG.md 裡 `## v1.9.0` 那一段的內容 (找不到回傳空字串)。"""
    try:
        text = open(path or os.path.join(HERE, "CHANGELOG.md"), encoding="utf-8").read()
    except OSError:
        return ""
    for s in re.split(r"(?m)^## ", text)[1:]:
        head, _, rest = s.partition("\n")
        if head.strip() == f"v{version}":
            return rest.strip()
    return ""


def chunks(body, limit=LIMIT):
    """在行與行之間斷開,不把一行切成兩半;單行本身就超過上限才硬切。"""
    out, cur = [], ""
    for line in body.split("\n"):
        while len(line) > limit:
            if cur:
                out.append(cur)
                cur = ""
            out.append(line[:limit])
            line = line[limit:]
        if cur and len(cur) + 1 + len(line) > limit:
            out.append(cur)
            cur = line
        else:
            cur = line if not cur else cur + "\n" + line
    if cur:
        out.append(cur)
    return out


def _post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(3):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "sgs-release-announcer"})
        try:
            with urllib.request.urlopen(req, timeout=15):
                return True
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:   # 被限速: 照 Discord 說的時間等一下再試
                try:
                    wait = float(json.load(e).get("retry_after", 2))
                except Exception:
                    wait = 2
                time.sleep(min(wait, 10) + 0.5)
                continue
            print(f"[announce] Discord 回應 {e.code}", file=sys.stderr)   # 只記狀態碼,不記網址
            return False
        except Exception as e:
            print(f"[announce] 送出失敗: {type(e).__name__}", file=sys.stderr)
            return False
    return False


def announce_if_new(version=VERSION):
    """版本比上次公告的新才貼;第一次執行 (沒有紀錄) 只記下目前版本,不補貼舊的。"""
    with _lock:
        url = webhook_url()
        if not url:
            return False
        try:
            last = open(STATE, encoding="utf-8").read().strip()
        except OSError:
            last = ""
        if last == version:
            return False
        if not last:
            _save(version)
            return False
        body = section(version)
        if not body:   # CHANGELOG 還沒寫這一版: 不公告,下次啟動再試
            print(f"[announce] CHANGELOG.md 沒有 v{version} 的段落,先不公告", file=sys.stderr)
            return False
        link = f"{REPO}/blob/main/CHANGELOG.md"
        parts = chunks(body)
        for i, chunk in enumerate(parts, 1):
            name = f"進化三國 v{version} 更新" + (f" ({i}/{len(parts)})" if len(parts) > 1 else "")
            if not _post(url, {"embeds": [{"title": name, "url": link, "description": chunk, "color": 0xC9A227}]}):
                return False
            time.sleep(1)
        _save(version)
        return True


def _save(version):
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, "w", encoding="utf-8") as f:
            f.write(version)
    except OSError as e:
        print(f"[announce] 無法記錄公告版本: {e}", file=sys.stderr)


def start_background():
    """伺服器啟動時呼叫: 背景執行,失敗也不影響遊戲。"""
    def run():
        try:
            announce_if_new()
        except Exception as e:
            print(f"[announce] {type(e).__name__}", file=sys.stderr)
    threading.Thread(target=run, daemon=True).start()
