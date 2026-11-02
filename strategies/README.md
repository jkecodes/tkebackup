# 武將策略 (strategies/)

每位武將一個檔 `strategies/<武將名>.py` (名字裡的 `&` 換成 `_`,例如 `顏良_文醜.py`),裡面一個 `class Strategy`。
只實作想接管的方法 (見 ../strategy_agent.py 開頭說明)。回傳 `NotImplemented` = 交給通用 AI。
檔案開頭用 docstring 寫: 這位武將的打法重點、各身分的差異、為什麼這樣做、實測勝率變化。

## 流程 (每位武將)
1. 讀 ../characters.md (技能原文) 與 ../characters.py (實作) 與 ../rulebook.md,弄懂技能與弱點。
2. `python arena.py 武將名 --games 2000` 看通用 AI 下的勝率 (依身分)。
3. 寫 strategies/<名>.py,再跑一次 arena 比較 (調整用種子 --seed0 0)。
4. 驗證: 用沒調過的種子 `--seed0 100000 --games 4000` 再跑一次; 驗證集上提升 >= +1.5 個百分點 (且區間不明顯變差) 才保留,否則刪掉檔案/退回。
5. 不可修改 ai.py / engine.py / characters.py / strategy_agent.py / arena.py; 只能新增修改自己負責的 strategies/*.py。
