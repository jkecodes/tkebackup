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

## 補充 (2026-11 更新: 線上電腦已接上策略檔)
- **線上電腦用的是 `ProAgent` (ai_pro.py),已經接上這套策略掛鉤**; 放進 `strategies/<武將名>.py` 的檔案,線上電腦遇到那位武將就會自動使用。沒有檔案 / 方法回傳 `NotImplemented` 就走原本邏輯。
- **策略方法的簽名多一個代理參數**: `def choose_skill(self, agent, g, p, skill)`、`def act(self, agent, g, p, options)` (`self` 是 Strategy 物件,`agent` 才是電腦代理,可以呼叫 `agent.foes_of(g, p)`、`agent.burst(g, p)`、`agent.attitude(g, p, q)` 等 ProAgent 的判斷函式)。
- **測試請用 `arena_pro.py`** (不是舊的 arena.py,那支是拿舊的 LeveledAgent 當基底): `python arena_pro.py 武將名 --games 800` (5 人局、同種子成對比較「有策略 / 沒策略」)。驗證用沒調過的種子: `--seed0 100000 --games 2000`,提升 >= +1.5 個百分點才保留。800 場的誤差約 ±3 個百分點,小差距要拉高場數。
- 調參時可以用環境變數開關 (策略檔裡 `os.environ.get(...)`),`arena_pro.py` 的子行程會繼承,記得驗證完把環境變數寫死成最終值。
- 打包成 exe 時 `strategies/` 已列在 `sgs_server.spec` 的 datas,新增策略檔後 exe 要重新打包才會帶到。
- 其他測試台: `rolestat.py` (全電腦自我對戰量各陣營勝率)、`lordsweep.py` (掃描主公體力加成對勝率的影響)。

## 已試過沒效果的 (不用再試一次)
勝率低不等於 AI 沒用好技能,下面幾隻我試過,勝率變化都在誤差內:
- 黃忠: 受傷時跳過出牌階段換回血 (HP<=2 / <=3 / 任何受傷) → -0.5 ~ +0.4
- 許褚: 放棄抽牌換傷害 x2 的各種觸發條件。通用 AI 本來就幾乎不觸發; 放寬到只要 1 張傷害牌反而 -1.5
- 馬良: 只交牌給隊友 (-1.5) / 完全不交 (+0.4)
- 羊祜: 多出來的殺改當拋磚引玉 → +0.4
這些多半是武將本身偏弱 (平衡問題),不是策略能補的。建議先量「技能實際觸發了幾次」再決定值不值得寫。

## 陣營平衡的實驗結論 (8 人局主公陣營勝率偏低的原因)
- 8 人局主公有 28% 在第 1 輪就死,58% 撐不過第 3 輪: 4 個反賊同一輪集火,是人數結構問題,不是某個 AI 漏洞。
- 試過沒效果: 打全場錦囊誤傷時不出、桃留到瀕死、打全場錦囊的無懈改用淨利益判斷、內奸反賊死光前當忠臣、內奸留著最後的反賊。
- 唯一有效的旋鈕: 降低反賊集火主公的力道 (ai_pro.py tscore 的 +15 / +50)。5 人局降到 -15 剛好平衡,但 6、8 人局到頂也只到 ~33% / ~31%。
