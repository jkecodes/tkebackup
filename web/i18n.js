/* 多語言 (繁中 / English / 日本語) + 教學模式。
   做法: 遊戲內部一律是中文; 這裡用 MutationObserver 把畫面上的文字即時換成所選語言,
   原文保留在 WeakMap, 切回中文即還原。武將技能說明與部分技能紀錄仍是中文。 */
(function () {
"use strict";
const LANGS = [["zh", "繁體中文"], ["en", "English"], ["ja", "日本語"]];
let lang = "zh";
try { lang = localStorage.getItem("sgs_lang") || "zh"; } catch (e) {}
if (!LANGS.some(l => l[0] === lang)) lang = "zh";
function saveLangCookie() { try { document.cookie = "sgs_lang=" + lang + ";path=/;max-age=31536000;SameSite=Lax"; } catch (e) {} }   // 卡面印章字由伺服器依語言畫,要讓它知道目前語言
saveLangCookie();

/* ---------- 詞典: [中文, English, 日本語] ---------- */
const W = [
  // 介面
  ["進化三國", "Evolved Three Kingdoms", "進化三国"], ["基本", "Basic", "基本"], ["錦囊", "Trick", "錦嚢"], ["延時錦囊", "Delayed Trick", "遅延錦嚢"], ["武器", "Weapon", "武器"], ["防具", "Armor", "防具"], ["坐騎", "Mount", "騎乗"], ["暫停", "Pause", "一時停止"], ["繼續", "Resume", "再開"],
  ["新遊戲", "New game", "新規ゲーム"], ["單步", "Step", "コマ送り"], ["每步延遲 ", "Step delay ", "ステップ間隔 "],
  ["即時顯示 AI 思考", "Show AI thoughts live", "AIの思考を即表示"], ["暱稱", "Nickname", "ニックネーム"],
  ["側欄 ▸", "Sidebar ▸", "サイド ▸"], ["側欄", "Sidebar", "サイド"], ["對局紀錄", "Game log", "対局ログ"],
  ["AI 思考", "AI thoughts", "AI思考"], ["武將", "Generals", "武将"], ["聊天", "Chat", "チャット"],
  ["牌桌", "Table", "卓"], ["紀錄", "Log", "ログ"], ["自動捲到最新", "Auto-scroll", "自動スクロール"],
  ["↳ = 連鎖回應", "↳ = chain response", "↳ = チェーン応答"], ["全部玩家", "All players", "全プレイヤー"],
  ["只看 ", "Only ", "絞込 "], ["輸入訊息,Enter 送出", "Type a message, Enter to send", "メッセージを入力、Enterで送信"],
  ["送出", "Send", "送信"], ["取消", "Cancel", "キャンセル"], ["確定", "OK", "確定"], ["結束出牌", "End play phase", "出牌終了"],
  ["按住空白處拖曳可移動牌桌 · 雙擊還原", "Drag empty space to pan the table · double-click to reset", "空白をドラッグで卓を移動 · ダブルクリックでリセット"],
  ["設定你的暱稱 (朋友入座時別人會看到)", "Set your nickname (others see it when you sit)", "ニックネームを設定(着席時に他の人に表示)"],
  ["隱藏 / 顯示右側的紀錄、AI 思考、武將欄", "Hide / show the right-hand log, AI thoughts and generals", "右側のログ/AI思考/武将欄の表示切替"],
  ["暫停時前進一行紀錄", "Advance one log line while paused", "一時停止中に1行進める"],
  ["每一步 (每行紀錄) 之間的等待時間,最快 0.05 秒", "Delay between steps (log lines); fastest is 0.05s", "ステップ(ログ1行)ごとの待ち時間。最速は0.05秒"],
  ["勾選後,右側「AI 思考」分頁會在遊戲進行中就顯示每個 AI 的理由 (預設遊戲結束才顯示,避免洩漏)", "When ticked, the AI thoughts tab shows each AI's reasoning during play (by default only after the game ends, to avoid leaks)", "チェックすると対局中からAIの理由を表示(既定では終了後のみ)"],
  ["遊戲結束或勾選上方「即時顯示 AI 思考」後才會顯示 (多人遊戲只有房主能勾)", "Shown after the game ends or when \"Show AI thoughts live\" is ticked (host only in multiplayer)", "ゲーム終了後、または上の「AIの思考を即表示」で表示(マルチではホストのみ)"],
  ["點擊查看武將詳細資訊", "Click for general details", "クリックで武将の詳細"],
  ["點擊展開)", "click to expand)", "クリックで展開)"],
  // 大廳 / 設定
  ["選好人數與座位,按下開始", "Choose player count and seats, then start", "人数と席を選んで開始"], ["開始遊戲", "Start game", "ゲーム開始"],
  ["房主", "Host", "ホスト"], ["房主: ", "Host: ", "ホスト: "], ["你是房主", "You are the host", "あなたはホスト"],
  ["把房主讓給目前在線的某人", "Hand the host role to someone online", "オンラインの誰かにホストを譲る"],
  ["人數", "Players", "人数"], ["我的位置", "My seat", "自分の席"], ["觀戰 = 全部由 AI 對戰", "Spectate = all AI", "観戦 = 全員AI"],
  ["👁 觀戰", "👁 Spectate", "👁 観戦"], ["🎲 隨機", "🎲 Random", "🎲 ランダム"], ["座位 ", "Seat ", "席 "], ["座位", "Seat", "席"],
  ["主公座位", "Emperor's seat", "君主の席"], ["主公從哪個座位開始;身分會在開局時才揭曉", "Which seat the Emperor starts from; roles are revealed at the start", "君主の開始席。役職は開始時に公開"],
  ["身分配置", "Role set-up", "役職配置"], ["配置 ", "Set-up ", "配置 "], ["進階", "Advanced", "詳細"], ["亂數種子", "Random seed", "乱数シード"],
  ["隨機", "Random", "ランダム"], ["開放玩家", "Open to players", "プレイヤーに開放"],
  ["全部開放玩家", "Open all seats to players", "全席をプレイヤーに開放"], ["全部關閉 (不開放)", "Close all seats", "全席を閉じる"],
  ["朋友用瀏覽器開這個網址就能選座位。沒人坐的真人座位開始時會由 AI 接手。", "Friends open this address in a browser to take a seat. Empty human seats are taken over by AI at start.", "友達はこのアドレスをブラウザで開いて席を選べます。空席は開始時にAIが代行します。"],
  ["讓給 ", "Hand to ", "譲る: "], ["房主已讓給 ", "Host handed to ", "ホストを譲渡: "],
  ["只有房主可以操作", "Only the host can do this", "ホストのみ操作できます"], ["等待房主操作", "Waiting for the host", "ホストの操作待ち"],
  ["等待房主操作…", "Waiting for the host…", "ホストの操作待ち…"], ["等待房主建立遊戲…", "Waiting for the host to create a game…", "ホストがゲームを作成するのを待っています…"],
  ["大廳: 等待玩家入座", "Lobby: waiting for players to sit", "ロビー: 着席待ち"], ["等待玩家入座", "Waiting for players to sit", "着席待ち"],
  ["已入座 (點擊離開)", "Seated (click to leave)", "着席中(クリックで離席)"], ["坐這裡", "Sit here", "ここに座る"], ["已有人入座", "Occupied", "着席済み"],
  ["座位與武將", "Seats & generals", "席と武将"],
  ["留「隨機武將」會從 ", "Leaving \"random general\" draws from ", "「ランダム武将」は次の中から抽選: "],
  ["位武將中抽,不重複;勾「開放玩家」讓玩家入座", " generals without repeats; tick \"Open to players\" to let players sit", "人の武将から重複なしで抽選。「プレイヤーに開放」でプレイヤーが着席可能"],
  ["隨機武將", "Random general", "ランダム武将"], ["無武將 (4 體力)", "No general (4 HP)", "武将なし(体力4)"],
  ["先取個暱稱吧", "Pick a nickname first", "まずニックネームを決めましょう"],
  ["進入遊戲前需要暱稱,其他玩家會看到它 (最多 10 字,之後可用上方「👤 暱稱」按鈕修改)", "A nickname is needed before joining; others will see it (max 10 chars, change later via the \"👤 Nickname\" button)", "参加前にニックネームが必要です(最大10文字、後で「👤 ニックネーム」から変更可)"],
  ["輸入你的暱稱", "Enter your nickname", "ニックネームを入力"], ["例如: 阿明", "e.g. Ming", "例: ミン"], ["修改你的暱稱", "Change your nickname", "ニックネームを変更"],
  ["最多 10 字,其他玩家會看到新名字", "Max 10 chars; others will see the new name", "最大10文字。他の人に新しい名前が表示されます"],
  ["遊戲進行中不能改暱稱", "Can't change nickname during a game", "ゲーム中はニックネームを変更できません"],
  ["修改暱稱", "Change nickname", "ニックネーム変更"], ["改暱稱", "Edit nickname", "名前変更"], ["✎ 改暱稱", "✎ Nickname", "✎ 名前変更"],
  ["你的暱稱 (入座前先取名,別人會看到)", "Your nickname (set before sitting; others will see it)", "ニックネーム(着席前に設定、他の人に表示)"],
  ["目前沒有其他人在線,無人可讓", "Nobody else is online", "他にオンラインの人がいません"],
  ["連線中斷… ", "Disconnected… ", "接続が切れました… "], ["未命名", "Unnamed", "名無し"], ["無名", "Anonymous", "無名"],
  ["觀戰中", "Spectating", "観戦中"], ["電腦", "CPU", "CPU"], ["玩家", "Player", "プレイヤー"], ["你是 P", "You are P", "あなたは P"],
  ["尚未開始", "Not started", "未開始"], ["遊戲結束", "Game over", "ゲーム終了"], ["遊戲結束: ", "Game over: ", "ゲーム終了: "],
  ["勝利: ", "Winner: ", "勝利: "], ["理由: ", "Reason: ", "理由: "],
  ["選擇武將中", "Choosing generals", "武将選択中"], ["選擇你的武將 (三選一)", "Choose your general (1 of 3)", "武将を選択(3択)"],
  ["大家同時選;這三張是專屬抽給你的,不會和其他人重複。選了什麼要到開局才會公開。", "Everyone picks at the same time; these three are dealt only to you, no overlap with others. Picks are revealed at the start.", "全員同時に選択。この3枚はあなた専用で他と重複しません。選択は開始時に公開されます。"],
  ["你已選好武將", "You have picked", "武将を選択済み"], ["玩家選擇武將中", "Players are picking characters", "プレイヤーが武将を選択中"], ["還沒選: ", "Not yet picked: ", "未選択: "],
  ["等待還沒選的玩家: ", "Waiting for: ", "未選択のプレイヤーを待っています: "], ["選這位", "Pick this", "これにする"],
  ["觀戰模式: 可在左上調整速度、暫停、單步;右側 AI 思考可看每個決定的理由。", "Spectator mode: adjust speed, pause and step at top-left; the AI thoughts tab shows reasons for each decision.", "観戦モード: 左上で速度・一時停止・コマ送りを調整。右のAI思考で各判断の理由を確認できます。"],
  ["考慮過的選項:", "Options considered:", "検討した選択肢:"], ["身分推理:", "Role inference:", "役職推理:"], ["疑似反賊分", "Rebel score", "反逆者らしさ"],
  ["恨意", "Grudge", "恨み"], ["態度", "Attitude", "態度"], ["思考", "Thinking", "思考"], ["判斷", "Judgement", "判断"],
  ["對方", "Opponent", "相手"], ["第 ", "Round ", "第"],   // 手牌 / 操作
  ["手牌", "Hand", "手札"], ["沒有手牌)", "no hand cards)", "手札なし)"], ["體力", "HP", "体力"], ["體力上限 ", "Max HP ", "体力上限 "],
  ["目前: ", "Now: ", "現在: "], ["使用 ", "Use ", "使用 "], ["使用", "Use", "使用"], ["發動 ", "Activate ", "発動 "], ["發動", "Activate", "発動"],
  ["請選擇", "Choose", "選択してください"], ["操作…", "Act…", "操作…"], ["行動…", "Action…", "行動…"],
  ["不出", "Pass", "出さない"], ["不發動", "Don't activate", "発動しない"], ["不發動,這類選項本回合不再詢問", "Don't activate; stop asking about this this turn", "発動しない(このターンはもう聞かない)"],
  ["已陣亡", "Dead", "死亡"], ["檢視中", "Viewing", "表示中"], ["橫置", "Chained", "横向き"], ["翻面", "Flipped", "裏向き"],
  ["亮牌", "Reveal", "公開"], ["內奸", "Spy", "内通者"], ["主公", "Emperor", "君主"], ["忠臣", "Loyalist", "家来"], ["反賊", "Rebel", "反逆者"],
  ["點擊其他玩家切換", "click another player to switch", "他のプレイヤーをクリックで切替"],
  ["牌堆 ", "Deck ", "山札 "], ["本次連鎖", "This chain", "今回のチェーン"], ["棄牌堆 ", "Discard ", "捨て札 "], ["棄牌堆", "Discard pile", "捨て札"],
  ["判定結果", "Judgement", "判定結果"], ["連鎖回應", "Chain response", "チェーン応答"], ["詳細", "Details", "詳細"], ["全部", "All", "全て"],
  ["請點擊一位玩家 — ", "Click a player — ", "プレイヤーを1人クリック — "],
  ["選 ", "Choose ", "選択: "],
  // 提示
  ["你的出牌階段", "Your play phase", "あなたの出牌フェイズ"], ["選一張牌與目標,或結束出牌", "pick a card and target, or end your turn", "カードと対象を選ぶか、出牌を終了"],
  ["你被攻擊了,要打出閃嗎?", "You are being attacked. Play a Dodge?", "攻撃されています。閃を出しますか?"],
  ["要使用無懈嗎?", "Use Nullify?", "無懈可撃を使いますか?"], ["要打出桃嗎?(不出會扣 1 點體力)", "Play a Peach? (otherwise lose 1 HP)", "桃を出しますか?(出さないと体力-1)"],
  ["要使用反/調/占 嗎?", "Use Counter / Divert / Divination?", "反撃/調虎離山/占卜を使いますか?"],
  ["不出會受到傷害", "otherwise you take damage", "出さないとダメージを受けます"], ["不出就扣 1 點體力", "otherwise lose 1 HP", "出さないと体力-1"],
  ["要打出", "Play ", "出しますか: "], ["要發動嗎?", "Activate?", "発動しますか?"], ["選擇效果", "Choose effect", "効果を選択"],
  ["選擇目標", "Choose target", "対象を選択"], ["選擇結算方向", "Choose resolution direction", "解決方向を選択"],
  ["從我左邊開始", "Start from my left", "自分の左から"], ["從我右邊開始", "Start from my right", "自分の右から"],
  ["選擇張數", "Choose number", "枚数を選択"], ["交給誰?", "Give to whom?", "誰に渡す?"],
  ["往左 (座位號遞增)", "left (seat numbers ascending)", "左回り(席番号が増える方向)"], ["往右 (座位號遞減)", "right (seat numbers descending)", "右回り(席番号が減る方向)"],
  ["決定輪次方向", "decides the turn direction", "がターン方向を決定"],
  ["要接連鎖使用 ⚡ 嗎?", "Respond with ⚡ in this chain?", "チェーンで⚡を使いますか?"],
  ["要發動技能嗎?", "Activate a skill?", "スキルを発動しますか?"],
  ["對你使用", "uses on you", "があなたに使用"],
  ["使用 ", "uses ", "使用: "],
  // 紀錄動詞
  ["回合", "turn", "のターン"], ["受到 ", "takes ", "受けた: "], ["點火傷害", " fire damage", "点の火ダメージ"], ["點冰傷害", " ice damage", "点の氷ダメージ"],
  ["點雷傷害", " thunder damage", "点の雷ダメージ"], ["點傷害", " damage", "点のダメージ"], ["來源 ", "from ", "原因: "],
  ["瀕死 (體力 ", "is dying (HP ", "瀕死 (体力 "], ["陣亡", "has died", "死亡"], ["擊殺反賊,抽3張", "killed a rebel and draws 3", "反逆者を倒して3枚引く"],
  ["無人出桃", "Nobody plays a Peach", "誰も桃を出さない"],
  ["依序詢問 ", "Asking in turn: ", "順に確認: "], [" 是否出桃/酒救 ", " whether to save with Peach/Wine: ", " が桃/酒で救うか: "], [" 是否出桃救 ", " whether to save ", " が桃で救うか: "],
  ["展示 ", "shows ", "公開: "], ["棄置 ", "discards ", "捨てる: "], ["亮出 ", "reveals ", "公開: "], ["判定 ", "judges ", "判定: "],
  ["裝備 ", "equips ", "装備: "], ["重鑄 ", "recasts ", "再鋳造: "], ["重鑄: 抽1張", "Recast: draws 1", "再鋳造: 1枚引く"],
  ["將 ", "puts ", ""], [" 放入 ", " into ", " を "], [" 的判定區", "'s judgement zone", " の判定エリアに置く"],
  ["傷害改由 ", "Damage taken by ", "ダメージを受ける人: "], ["同色 ", "Same colour ", "同色 "], ["兩張都棄掉", "both discarded", "両方捨てる"],
  ["使用桃 -> 體力 ", "plays Peach -> HP ", "桃を使用 -> 体力 "], ["使用酒 (下一張殺傷害+1)", "drinks Wine (next Slash +1 damage)", "酒を使用(次の殺のダメージ+1)"],
  ["武將牌翻面一回合 (技能無法使用)", "character card flipped for a turn (skills disabled)", "武将カードが1ターン裏返る(スキル使用不可)"],
  ["翻面一回合", "is flipped for a turn", "が1ターン裏返る"], ["偽裝成 ", "disguises as ", "変身: "], ["獲得他的技能直到回合結束", "gaining their skills until end of turn", "ターン終了までそのスキルを得る"],
  ["發憤圖強棄 ", "Resolve: discards ", "発憤図強で捨てる: "], 
  ["抽 ", "draws ", "引く: "], ["受傷判定", "damage judgement", "ダメージ判定"],
  ["草木皆兵生效", "Scarecrow Panic takes effect", "草木皆兵が発動"], ["判定區 ", "judgement zone: ", "判定エリア: "], [" 生效", " takes effect", " が発動"],
  ["決鬥", "Duel", "決闘"], ["在 ", "at ", ""], ["決定輪次方向: ", "decides turn direction: ", "ターン方向を決定: "],
  ["目標 ", "target ", "対象 "], ["吸收", "absorb", "吸収"], ["宣告: ", "declares: ", "宣言: "],
  // 卡牌名
  ["火攻", "Fire Attack", "火攻"], ["八卦陣", "Eight-Trigram", "八卦陣"], ["仁王盾", "Renwang Shield", "仁王盾"], ["藤甲", "Rattan Armor", "藤甲"],
  ["緩衝盾", "Buffer Shield", "緩衝盾"], ["雷盾", "Thunder Shield", "雷盾"], ["火盾", "Fire Shield", "火盾"], ["冰盾", "Ice Shield", "氷盾"],
  ["+1馬", "+1 Horse", "+1馬"], ["-1馬", "-1 Horse", "-1馬"], ["諸葛連弩", "Zhuge Crossbow", "諸葛連弩"], ["孔雀羽扇", "Peacock Fan", "孔雀羽扇"],
  ["青龍偃月刀", "Green Dragon Blade", "青龍偃月刀"], ["寒冰劍", "Frost Sword", "寒氷剣"], ["方天畫戟", "Sky Piercer", "方天画戟"], ["流星錘", "Meteor Hammer", "流星鎚"],
  ["麒麟弓", "Kirin Bow", "麒麟弓"], ["青釭劍", "Blue Steel Sword", "青釭剣"], ["丈八蛇矛", "Serpent Spear", "丈八蛇矛"], ["貫石斧", "Stone Axe", "貫石斧"],
  ["鐵索連環", "Iron Chain", "鉄索連環"], ["桃園結義", "Peach Garden", "桃園結義"], ["桃園", "Peach Garden", "桃園"], ["無懈可擊", "Nullify", "無懈可撃"], ["無懈", "Nullify", "無懈"],
  ["南蠻入侵", "Barbarians", "南蛮入侵"], ["萬箭齊發", "Arrow Barrage", "万箭斉発"], ["無中生有", "Windfall", "無中生有"], ["順手牽羊", "Steal", "順手牽羊"],
  ["過河拆橋", "Dismantle", "過河拆橋"], ["借刀殺人", "Borrowed Blade", "借刀殺人"], ["樂不思蜀", "Complacency", "楽不思蜀"], ["兵糧寸斷", "Starvation", "兵糧寸断"],
  ["閃電", "Lightning", "閃電"], ["降雷", "Thunder Call", "降雷"], ["發憤圖強", "Resolve", "発憤図強"], ["孤注一擲", "All-In", "孤注一擲"],
  ["五穀豐登", "Harvest", "五穀豊穣"], ["草木皆兵", "Scarecrow Panic", "草木皆兵"], ["偽裝", "Disguise", "偽装"], ["鴻門宴", "Hongmen Feast", "鴻門宴"],
  ["未雨綢繆", "Plan Ahead", "未雨綢繆"], ["笑裏藏刀", "Hidden Dagger", "笑裏蔵刀"], ["隔岸觀火", "Watch the Fire", "隔岸観火"], ["投桃報李", "Return the Favor", "投桃報李"],
  ["拋磚引玉", "Lure with Brick", "拋磚引玉"], ["出其不意", "Surprise Move", "出其不意"], ["聲東擊西", "Feint", "聲東撃西"], ["增兵", "Reinforce", "増援"],
  ["火焰", "Fire", "火"], ["火殺", "Fire Slash", "火殺"], ["冰殺", "Ice Slash", "氷殺"], ["雷殺", "Thunder Slash", "雷殺"],
  ["反擊", "Counter", "反撃"], ["飢餓", "Famine", "飢餓"], ["當作 調", "as Divert the Tiger", "調虎離山として"], ["當作 占", "as Divination", "占卜として"], ["重鑄酒", "recast Wine", "酒を再鋳造"], ["重鑄閃", "recast Dodge", "閃を再鋳造"], ["棄兩張殺", "discard two Slash", "殺2枚を捨てる"], ["雙牌當殺", "two cards as Slash", "2枚を殺として"], ["換2張牌", "swap 2 cards", "2枚交換"], ["突襲", "Raid", "突襲"], ["調虎離山", "Divert the Tiger", "調虎離山"], ["占卜", "Divination", "占卜"],
  ["無來源", "none", "なし"],
  ["技能或牌的效果", "skill / card effect", "技能またはカードの効果"],
  ["魏國", "Wei", "魏"], ["蜀國", "Shu", "蜀"], ["吳國", "Wu", "呉"], ["群雄", "Qun", "群雄"], ["晉國", "Jin", "晋"],
  ["轉移", "Swap", "装備交換"], ["增兵減灶", "Reinforce", "増援"], ["增援", "Reinforce", "増援"], ["笑裡藏刀", "Hidden Dagger", "笑裏蔵刀"],
  ["殺", "Slash", "殺"], ["閃", "Dodge", "閃"], ["桃", "Peach", "桃"], ["酒", "Wine", "酒"],
  ["每步延遲", "Step delay", "ステップ間隔"], ["開始", " start", "開始"], ["輪", "", "巡"], ["弱", "Weaken", "弱化"], ["強", "Empower", "強化"],
  ["背面", "face-down", "裏"], ["正面", "face-up", "表"], ["火", "fire ", "火"], ["冰", "ice ", "氷"], ["雷", "thunder ", "雷"],
  ["的回合使用", "'s turn uses", "のターンに使用"], ["的回合發動", "'s turn activates", "のターンに発動"], ["的回合", "'s turn", "のターン"],
  ["的判定區", "'s judgement zone", "の判定エリア"], ["個仁", " Benevolence token(s)", "個の「仁」"], ["共 ", "total ", "計"], ["將", "puts", "を"],
  ["判定區", "judgement zone", "判定エリア"], ["判定", "judges", "判定"], ["生效", "takes effect", "が発動"], ["移交", "passes to", "移動先"],
  ["棄置", "discards", "捨てる"], ["展示", "shows", "公開"], ["亮出", "reveals", "公開"], ["取得", "takes", "得る"], ["獲得", "gets", "得る"],
  ["打出", "plays", "出す"], ["的傷害被抵銷", "'s damage is cancelled", "のダメージが相殺された"], ["是否出桃/酒救", "whether to save with Peach/Wine", "桃/酒で救うか"], ["是否出桃救", "whether to save", "桃で救うか"],
  ["依序詢問", "Asking in turn:", "順に確認:"], ["使用", "uses", "使用"], ["放入", "puts into", "置く"], ["裝備", "equips", "装備"],
  ["🚪 大廳", "🚪 Lobby", "🚪 ロビー"], ["回到大廳,選擇或創建房間", "Back to the lobby to pick or create a room", "ロビーに戻って部屋を選ぶ/作る"],
  ["進化三國 · 大廳", "Evolved Three Kingdoms · Lobby", "進化三国 · ロビー"], ["選一個房間加入,或自己創建一個。房間沒人超過 10 分鐘會自動刪除。", "Join a room or create your own. Rooms empty for over 10 minutes are deleted automatically.", "部屋に参加するか、自分で作成します。10分以上無人の部屋は自動削除されます。"],
  ["房間名稱 (例如: 阿明的房間)", "Room name (e.g. Ming's room)", "部屋の名前(例: ミンの部屋)"], ["創建房間", "Create room", "部屋を作成"], ["加入", "Join", "参加"], ["刪除", "Delete", "削除"], ["刪除這個房間", "Delete this room", "この部屋を削除"],
  ["公共房間", "Public room", "公開ルーム"], ["新房間", "New room", "新しい部屋"], ["進行中", "In game", "対局中"], ["等待玩家", "Waiting", "待機中"], ["空房", "Empty", "空き"], ["選武將", "Picking", "武将選択"],
  ["目前 ", "", ""], [" 人在線", " online", "人オンライン"], [" 人局 · ", "-player · ", "人戦 · "],
  ["確定要刪除房間「", "Delete the room \"", "部屋を削除しますか「"], ["創建失敗: ", "Create failed: ", "作成失敗: "], ["房間已不存在 (太久沒有人,已被刪除)", "The room no longer exists (deleted after being empty too long)", "部屋が存在しません(無人のため削除されました)"],
  ["一個人最多同時開 3 個房間", "You can have at most 3 rooms at once", "同時に作れる部屋は3つまでです"], ["房間太多了,請稍後再試", "Too many rooms; try again later", "部屋が多すぎます。後でもう一度"], ["只有房主可以刪除房間", "Only the host can delete the room", "ホストのみ部屋を削除できます"], ["這個房間不能刪除", "This room can't be deleted", "この部屋は削除できません"],
  ["玩家等級 / UID", "Player level / UID", "プレイヤーレベル / UID"], ["玩家檔案", "Player profile", "プレイヤー情報"], ["下一級", "next level", "次のレベル"],
  ["每場有入座的對局 +20 經驗。獲勝再加: 電腦難度 弱 +15 / 中 +30 / 強 +45 / 很強 +70 (多種難度取平均);全真人對戰獲勝 +30。", "+20 XP for every game you sit in. A win adds: vs AI Easy +15 / Medium +30 / Hard +45 / Expert +70 (averaged if mixed); all-human games +30.", "着席した対局ごとに経験値+20。勝利で追加: AI 弱+15 / 普通+30 / 強+45 / 最強+70(混在時は平均)、全員プレイヤーの対局は+30。"],
  ["你的 UUID (帳號憑證,請勿給別人)", "Your UUID (account credential — don't share it)", "あなたのUUID(アカウント情報、他人に渡さない)"], ["複製", "Copy", "コピー"], ["切換", "Switch", "切替"],
  ["換瀏覽器或裝置時,貼上舊的 UUID 就能取回等級。", "On a new browser or device, paste your old UUID to get your level back.", "ブラウザや端末を変える時は、古いUUIDを貼り付ければレベルを取り戻せます。"],
  ["貼上另一個 UUID 以切換帳號", "Paste another UUID to switch accounts", "別のUUIDを貼り付けてアカウント切替"], ["已複製 UUID", "UUID copied", "UUIDをコピーしました"], ["切換失敗: ", "Switch failed: ", "切替失敗: "], ["找不到這個 UUID", "UUID not found", "このUUIDは見つかりません"],
  ["經驗 ", "XP ", "経験値 "], [" 場 · ", " games · ", "戦 · "], [" 勝", " wins", "勝"],
  ["玩家資訊", "Player info", "プレイヤー情報"], ["總場數", "Games", "総試合数"], ["勝場", "Wins", "勝利数"], ["勝率", "Win rate", "勝率"],
  ["最常使用的武將", "Most-used generals", "よく使う武将"], ["還沒有紀錄 (入座打完一場就會出現)", "No record yet (appears after you finish a game seated)", "まだ記録がありません(着席して1戦終えると表示)"], ["身分戰績", "Record by role", "役職別の戦績"],
  ["經驗 ", "XP ", "経験値 "], [" 場 ", " games ", "戦 "],
  ["上傳大頭貼", "Upload avatar", "アイコンをアップロード"], ["移除", "Remove", "削除"], ["大頭貼已更新", "Avatar updated", "アイコンを更新しました"], ["上傳失敗: ", "Upload failed: ", "アップロード失敗: "],
  ["無法讀取這張圖片", "Can't read this image", "この画像を読み込めません"], ["圖片格式不對或太大", "Wrong image format or too large", "画像形式が不正、またはサイズが大きすぎます"], ["只接受 JPEG", "JPEG only", "JPEGのみ対応"], ["圖片資料錯誤", "Bad image data", "画像データが不正です"],
  ["請登入或註冊後開始遊戲", "Log in or register to play", "ログインまたは登録してください"], ["登入", "Log in", "ログイン"], ["註冊", "Register", "登録"],
  ["使用者名稱 (2~10 字)", "Username (2–10 chars)", "ユーザー名(2~10文字)"], ["密碼 (至少 6 個字元)", "Password (at least 6 chars)", "パスワード(6文字以上)"], ["再輸入一次密碼", "Repeat password", "パスワードを再入力"],
  ["密碼在區域網路內以明碼傳輸,請不要使用你在其他網站用的密碼。", "Passwords are sent unencrypted over the network — don't reuse a password from another site.", "パスワードは暗号化されずに送信されます。他のサイトのパスワードは使わないでください。"],
  ["兩次輸入的密碼不一樣", "The two passwords don't match", "パスワードが一致しません"], ["登出", "Log out", "ログアウト"], ["帳號: ", "Account: ", "アカウント: "],
  ["使用者名稱 2~10 字,只能用中英文、數字、底線", "Username: 2–10 chars; letters, digits, underscore only", "ユーザー名は2~10文字、英数字・かな漢字・アンダースコアのみ"], ["密碼至少 6 個字元", "Password must be at least 6 characters", "パスワードは6文字以上"],
  ["這個名稱已被使用", "This username is taken", "このユーザー名は使われています"], ["使用者名稱或密碼錯誤", "Wrong username or password", "ユーザー名またはパスワードが違います"], ["嘗試次數太多,請 5 分鐘後再試", "Too many attempts; try again in 5 minutes", "試行回数が多すぎます。5分後に再試行してください"], ["請先登入", "Please log in first", "先にログインしてください"],
  ["複製", "Copy", "コピー"], ["已複製", "Copied", "コピー済み"],
  ["🏆 排行榜", "🏆 Leaderboard", "🏆 ランキング"], ["玩家排行榜", "Leaderboard", "プレイヤーランキング"], ["依等級", "By level", "レベル順"], ["依勝場", "By wins", "勝利数順"], ["依勝率", "By win rate", "勝率順"], ["還沒有玩家資料", "No players yet", "プレイヤーなし"], ["尚無對局", "No games yet", "対局なし"],
  ["輸入你的 UID (8 位數字)", "Enter your UID (8 digits)", "UID(8桁の数字)を入力"], ["設定使用者名稱 (2~10 字)", "Choose a username (2–10 chars)", "ユーザー名(2~10文字)"], ["UID 或密碼錯誤", "Wrong UID or password", "UIDまたはパスワードが違います"],
  ["登入只需要 UID,請不要把你的 UID 給別人。", "Logging in only needs your UID — don't share it with anyone.", "ログインにはUIDだけが必要です。他人に教えないでください。"], ["找不到這個 UID", "UID not found", "このUIDは見つかりません"],
  ["主公陣營", "Emperor's side", "君主陣営"], ["陣營", "side", "陣営"], ["平手(超過回合上限)", "Draw (round limit reached)", "引き分け(ラウンド上限超過)"], ["平手", "Draw", "引き分け"],
  ["你的帳號已在另一個裝置登入,請重新登入", "Your account was logged in on another device. Please log in again.", "別の端末でログインされました。もう一度ログインしてください。"],
  ["音效 開/關", "Sound on/off", "効果音 オン/オフ"],
  ["🔁 再來一局 (同樣設定)", "🔁 Play again (same settings)", "🔁 もう一局(同じ設定)"], ["只有房主可以再來一局", "Only the host can start a rematch", "再戦できるのはホストだけです"], ["還沒有上一局的設定", "No previous game settings", "前回の設定がありません"],
  ["搜尋武將名稱或技能內容…", "Search hero name or skill text…", "武将名やスキル内容で検索…"], ["沒有符合的武將", "No matching hero", "該当する武将なし"], ["⭐ = 依目前手牌與局面推薦", "⭐ = recommended for your current hand and situation", "⭐ = 手札と状況に基づくおすすめ"], ["⭐ 推薦", "⭐ Recommended", "⭐ おすすめ"], ["🎭 偽裝成", "🎭 Disguised as", "🎭 変装中"], ["原本的武將", "Original hero", "元の武将"],
  ["遊戲模式", "Game mode", "ゲームモード"], ["正常模式", "Normal mode", "通常モード"], ["🔀 百變模式", "🔀 Shuffle mode", "🔀 シャッフルモード"],
  ["正常模式: 武將不變;百變模式: 第 2 輪起,每次輪到玩家的回合一開始都會隨機換成一位新武將 (已損失的體力不變)", "Normal: heroes never change. Shuffle: from round 2, at the start of each player's turn they become a new random hero (lost HP stays the same).", "通常: 武将は変わらない。シャッフル: 第2ラウンドから、各プレイヤーのターン開始時にランダムな新武将に変わる(減った体力はそのまま)。"],
  ["電腦難度", "AI difficulty", "AIの難易度"],
  ["上面一排是一次調整全部電腦;每個座位也可以在下方「座位與武將」各自調整。打贏電腦拿到的經驗值: 弱 +15 / 中 +30 / 強 +45 / 很強 +70 (另外每場 +20),多個難度取平均。", "The top row sets every AI at once; each seat can also be set individually under Seats & Heroes. XP for beating the AI: Easy +15 / Medium +30 / Hard +45 / Expert +70 (plus +20 per game), averaged over mixed difficulties.", "上の行で全AIを一括変更、各席は下の「席と武将」で個別にも変更できる。AIに勝った時の経験値: 弱+15 / 普通+30 / 強+45 / 最強+70(さらに毎局+20)、難易度が混在する場合は平均。"],
  ["先點「被借刀的人」(有武器的角色)", "First click the one being borrowed from (has a weapon)", "まず武器を持つ「刀を借りられる人」をクリック"], ["再點他要攻擊的對象", "Then click who they must attack", "次にその人が攻撃する相手をクリック"],
  ["先點「收到你手牌的人」", "First click who receives your card", "まず手札を受け取る人をクリック"], ["再點「收到他 2 張手牌的人」", "Then click who receives 2 of their cards", "次に2枚を受け取る人をクリック"],
  ["請點第 1 位玩家", "Click the 1st player", "1人目をクリック"], ["請點第 2 位玩家", "Click the 2nd player", "2人目をクリック"], ["(電腦)", "(CPU)", "(CPU)"],
  ["大家同時決定,先出的人救", "everyone decides at once; the first to play saves", "全員同時に決定。先に出した人が救う"],
  ["這個座位的電腦難度", "AI difficulty for this seat", "この席のAI難易度"],
  [" ⏱ ", " ⏱ ", " ⏱ "], [" 秒", "s", "秒"],
  ["仁 ×", "Benevolence ×", "仁 ×"], ["弒 ×", "Slay ×", "弒 ×"], ["🎯 指定 P", "🎯 Target P", "🎯 指定 P"], ["🎯 被 P", "🎯 Marked by P", "🎯 指定された P"], [" 張松指定", " (Zhang Song) mark", " 張松に指定"],
  ["無效 (已用)", "Void (used)", "無効(使用済)"], ["無效 (可用)", "Void (ready)", "無効(使用可)"], ["⚡ 本回合全場無效", "⚡ Everything void this turn", "⚡ このターン全て無効"], ["令棄牌 (已用)", "Discard-all (used)", "全捨て(使用済)"],
  ["吸收傷害中 ", "Absorbing damage ", "ダメージ吸収中 "], ["吸傷 (已用)", "Absorb (used)", "吸収(使用済)"], ["吸傷 (可用)", "Absorb (ready)", "吸収(使用可)"], ["下回合傷害 ×2", "Next turn damage ×2", "次ターンのダメージ×2"], ["本回合傷害 ×2", "This turn damage ×2", "このターンのダメージ×2"], ["下回合多抽 ×", "Extra draw next turn ×", "次ターンの追加ドロー×"],
  ["全場殺 ", "Slashes this round ", "場の殺 "], ["下回合變成 ", "Becomes next turn: ", "次ターンに変身: "], ["下回合獲得 P", "Next turn gains skills of P", "次ターンに獲得: P"], [" 的技能", "'s skills", " のスキル"], ["化身 ×", "Avatars ×", "化身 ×"],
  ["無效", "void", "無効"], ["紅", "Red ", "赤"], ["黑", "Black ", "黒"],
  ["弱化", "Weaken", "弱化"], ["強化", "Empower", "強化"],
  // 其它常見
  ["往左", "left", "左回り"], ["往右", "right", "右回り"], ["座位號遞增", "ascending seats", "席番号増加"],
  ["受傷,", "hurt, ", "負傷、"], ["受傷", "damaged", "負傷"],
  ["操作失敗: ", "Action failed: ", "操作失敗: "], ["引擎錯誤: ", "Engine error: ", "エンジンエラー: "], ["讓房主失敗: ", "Handover failed: ", "譲渡失敗: "],
  ["確定把房主讓給「", "Hand the host role to \"", "ホストを次の人に譲りますか「"], ["嗎?你之後就不能操作新遊戲/暫停等功能了。", "? You won't be able to use New game / Pause etc. afterwards.", "? 以後、新規ゲーム/一時停止などは操作できなくなります。"],
  ["目前 ", "", ""], [" 人在線", " online", "人オンライン"],
  ["防2", "Armor 2", "防具2"], ["武2", "Weapon 2", "武器2"], ["武", "W", "武"], ["防", "A", "防"],
  ["只有你)", "only you)", "あなただけ)"],
];
const TUT = {
  zh: {
    btn: "📖 教學", title: "新手教學", prev: "上一步", next: "下一步", fin: "完成", close: "關閉", skip: "跳過",
    page: "第 {a} / {b} 頁",
    steps: [
      ["遊戲目標", "每人有一個隱藏身分,只有主公公開:\n• 主公、忠臣: 打倒所有反賊和內奸。\n• 反賊: 打倒主公。\n• 內奸: 先清掉別人,最後單挑贏主公。\n不確定的時候,先觀察誰在幫誰、誰在打誰。"],
      ["你的回合", "每回合: 摸 2 張牌 → 出牌 → 手牌不能比體力多 (多的要棄掉)。\n出牌時點一張手牌,再點目標;不想出了就按「結束出牌」。\n被攻擊時會跳出視窗,選牌回應或按「不出」。"],
      ["最常用的牌", "• 殺: 打人,對方要出「閃」,否則扣 1 血。每回合只能出一張。\n• 閃: 躲掉一次殺。\n• 桃: 回 1 血,也能救瀕死的人。\n• 酒: 搭配殺傷害 +1。\n• 錦囊 (順手牽羊、決鬥、南蠻入侵…) 與裝備,滑鼠移上去就能看說明。⚡ 標記的可以在別人出牌時搶著用。"],
      ["瀕死與勝負", "體力降到 0 會瀕死,大家可以出桃救他,沒人救就陣亡。\n達成自己身分的目標就獲勝。\n遊戲最多進行 100 輪,超過算平手。"],
      ["段位與模式", "新遊戲可選「🎮 休閒」(不影響積分) 或「🏅 段位」(贏加分、輸扣分)。\n段位由低到高: 青銅 → 白銀 → 黃金 → 白金 → 鑽石 → 大師 → 傳說。\n詳細計分按開新遊戲畫面裡的「段位說明」。\n剛開始建議先打休閒。"],
      ["遊戲幣與外觀", "• 只有「🏅 段位」對局會得到遊戲幣: 贏 18~36 (依電腦難度)、輸 8、平手 12;棄賽沒有。\n• 遊戲幣可以到「🎨 外觀」買主題、玩家框、頭像框和特效。每個成就也會直接送你一個外觀。\n• 積分到「傳說」後可以按「轉生」: 回到青銅3,名字旁多一顆 ★,並得到聲望;聲望可以買轉生限定外觀。"],
    ],
  },
  en: {
    btn: "📖 Tutorial", title: "Beginner's Tutorial", prev: "Back", next: "Next", fin: "Done", close: "Close", skip: "Skip",
    page: "Page {a} / {b}",
    steps: [
      ["Goal", "Everyone has a hidden role; only the Emperor is public:\n• Emperor & Loyalists: defeat all Rebels and Spies.\n• Rebels: defeat the Emperor.\n• Spy: clear everyone else, then win the final duel against the Emperor.\nNot sure who's who? Watch who helps whom and who attacks whom."],
      ["Your turn", "Each turn: draw 2 → play cards → keep no more cards than your HP (discard the rest).\nTo play, click a hand card, then a target; press \"End play phase\" when done.\nWhen attacked, a window pops up: pick a card to respond or press \"Pass\"."],
      ["Key cards", "• Slash: attack; the target must play a Dodge or lose 1 HP. One per turn.\n• Dodge: avoids one Slash.\n• Peach: restore 1 HP, or save a dying player.\n• Wine: +1 damage on your Slash.\n• Tricks (Steal, Duel, Barbarians...) and equipment: hover for details. Cards marked ⚡ can be played in response to others."],
      ["Dying & winning", "At 0 HP a player is dying; others may play a Peach to save them, otherwise they die.\nAchieve your role's goal to win.\nA game lasts at most 100 rounds; beyond that it's a draw."],
      ["Ranks & modes", "A new game can be 🎮 Casual (no points change) or 🏅 Ranked (win = gain points, loss = lose points).\nRanks, low to high: Bronze → Silver → Gold → Platinum → Diamond → Master → Legend.\nFor the full scoring, press \"Rank guide\" on the new game screen.\nNew here? Start with Casual."],
      ["Coins & cosmetics", "• Only 🏅 Ranked games give coins: win 18-36 (by AI difficulty), loss 8, draw 12; forfeiting gives none.\n• Spend coins in 🎨 Cosmetics on themes, seat boxes, avatar frames and effects. Each achievement also gives one cosmetic for free.\n• After reaching Legend you can press Rebirth: back to Bronze 3 with a ★ next to your name, and you earn Renown, which buys Rebirth-only cosmetics."],
    ],
  },
  ja: {
    btn: "📖 チュートリアル", title: "初心者チュートリアル", prev: "戻る", next: "次へ", fin: "完了", close: "閉じる", skip: "スキップ",
    page: "{a} / {b} ページ",
    steps: [
      ["目的", "役職隠しのカードバトル。公開されるのは君主だけです。\n• 君主・家来: 反逆者と内通者を全員倒す。\n• 反逆者: 君主を倒す。\n• 内通者: 他を全員倒し、最後に君主と一騎打ちで勝つ。\n誰が味方か分からない時は、誰が誰を攻撃しているかを見ましょう。"],
      ["自分のターン", "① 2枚引く → ② カードを使う → ③ 手札を体力以下にする(超えた分は捨てる)。\n• 手札をクリック → 対象をクリック。\n• 終わったら「出牌終了」。\n• 攻撃されたら、カードで応じるか「出さない」を押す。\n迷ったら画面上部のヒントを見てください。"],
      ["基本の4枚", "• 殺: 攻撃。相手が「閃」を出せなければ体力-1。1ターンに1枚まで。\n• 閃: 殺を1回避ける。攻撃された時に出す。\n• 桃: 体力+1。瀕死の人も救える。\n• 酒: 次の殺のダメージ+1。\n錦嚢(順手牽羊・決闘・南蛮入侵…)と装備は、マウスを乗せると説明が出ます。⚡付きは他人の行動に割り込めます。"],
      ["瀕死と勝敗", "体力0で瀕死。誰かが桃を出せば助かり、出なければ死亡。\n自分の役職の目的を達成したチームの勝ちです。\n最大100巡で、超えると引き分け。"],
      ["ランクとモード", "• 🎮 カジュアル: ポイント変動なし。\n• 🏅 ランク戦: 勝てば加点、負ければ減点。\nランク: ブロンズ → シルバー → ゴールド → プラチナ → ダイヤ → マスター → レジェンド。\n計算は新規ゲーム画面の「ランクの説明」へ。最初はカジュアルがおすすめ。"],
      ["コインと外観", "• コインはランク戦のみ: 勝利 18~36(CPU難易度による)、敗北 8、引き分け 12、途中放棄 0。\n• 🎨 外観で、テーマ・枠・エフェクトに交換できます。実績ごとに外観が1つもらえます。\n• レジェンド到達後に「転生」: ブロンズ3に戻り、名前の横に ★ が付き、名声がもらえます(転生限定の外観に使用)。"],
    ],
  },
};

/* ---------- 武將名 ---------- */
const NAMES = {
  張飛: "Zhang Fei", 馬超: "Ma Chao", 黃忠: "Huang Zhong", 荀彧: "Xun Yu", 孫策: "Sun Ce", 華雄: "Hua Xiong", 董卓: "Dong Zhuo", 曹彰: "Cao Zhang",
  關羽: "Guan Yu", 孫權: "Sun Quan", 孫堅: "Sun Jian", 丁奉: "Ding Feng", 呂蒙: "Lü Meng", 魏延: "Wei Yan", 曹丕: "Cao Pi", 許褚: "Xu Chu",
  趙雲: "Zhao Yun", 曹仁: "Cao Ren", 孟獲: "Meng Huo", 陸遜: "Lu Xun", 黃蓋: "Huang Gai", 龐德: "Pang De", 袁紹: "Yuan Shao", 張遼: "Zhang Liao",
  馬良: "Ma Liang", 司馬昭: "Sima Zhao", 夏侯惇: "Xiahou Dun", 徐晃: "Xu Huang", 曹洪: "Cao Hong", 鄧艾: "Deng Ai", 劉備: "Liu Bei", 姜維: "Jiang Wei",
  諸葛亮: "Zhuge Liang", 張角: "Zhang Jue", 華佗: "Hua Tuo", 劉協: "Liu Xie", 顏良: "Yan Liang", 文醜: "Wen Chou", 滿寵: "Man Chong", 公孫瓚: "Gongsun Zan",
  呂布: "Lü Bu", 典韋: "Dian Wei", 司馬懿: "Sima Yi", 崔琰: "Cui Yan", 曹植: "Cao Zhi", 鐘繇: "Zhong Yao", 張嶷: "Zhang Yi", 王允: "Wang Yun",
  曹操: "Cao Cao", 曹叡: "Cao Rui", 張昭: "Zhang Zhao", 邯鄲淳: "Handan Chun", 周胤: "Zhou Yin", 沮授: "Ju Shou", 太史慈: "Taishi Ci", 周魴: "Zhou Fang",
  龐統: "Pang Tong", 周瑜: "Zhou Yu", 甘寧: "Gan Ning", 夏侯淵: "Xiahou Yuan", 孔融: "Kong Rong", 伊籍: "Yi Ji", 張郃: "Zhang He", 曹休: "Cao Xiu",
  曹沖: "Cao Chong", 曹真: "Cao Zhen", 楊修: "Yang Xiu", 蔣幹: "Jiang Gan", 郭嘉: "Guo Jia", 劉禪: "Liu Shan", 劉諶: "Liu Chen", 吳懿: "Wu Yi",
  周倉: "Zhou Cang", 張松: "Zhang Song", 李嚴: "Li Yan", 關興: "Guan Xing", 張苞: "Zhang Bao", 張紘: "Zhang Hong", 虞翻: "Yu Fan", 魯肅: "Lu Su",
  李儒: "Li Ru", 袁術: "Yuan Shu", 賈詡: "Jia Xu", 郭圖: "Guo Tu", 逢紀: "Pang Ji", 司馬炎: "Sima Yan", 羊祜: "Yang Hu", 馬謖: "Ma Su",
  陳群: "Chen Qun", 韓當: "Han Dang", 公孫淵: "Gongsun Yuan", 左慈: "Zuo Ci",
};
// 日文: 漢字直接沿用 (日本三國志也用漢字),僅把繁體異體字換成日文新字體/常用字形的少數字
const JA_CHARS = { "呂": "呂", "龐": "龐", "鐘": "鍾", "張": "張", "劉": "劉", "關": "関", "鄧": "鄧", "賈": "賈", "陸": "陸", "黃": "黄", "夏": "夏", "孫": "孫", "魯": "魯", "楊": "楊", "蔣": "蔣", "邯": "邯", "沮": "沮", "諶": "諶", "嶷": "嶷", "華": "華", "雲": "雲", "蓋": "蓋", "渊": "淵", "寵": "寵", "鐘繇": "鍾繇" };

/* ---------- 句型 (語序不同的紀錄) ---------- */
const PAT = {
  en: [
    [/^(.+?) 受到 (\d+) 點(火|冰|雷)?傷害 \(來源 (.+?)\) -> 體力 (-?\d+)$/, (m, t, n, e, s, hp) => `${t} takes ${n} ${{ 火: "fire ", 冰: "ice ", 雷: "thunder " }[e] || ""}damage (from ${s}) -> HP ${hp}`],
    [/^(.+?) 對 (.+?) 使用 (.+)$/, (m, a, b, c) => `${a} uses ${c} on ${b}`],
    [/^(.+?) 使用 (.+)$/, (m, a, c) => `${a} uses ${c}`],
    [/^--- 第(\d+)輪 (.+?) 回合 體力(\d+) 手牌(\d+) ---$/, (m, r, p, hp, hc) => `--- Round ${r}: ${p}'s turn  HP ${hp}  hand ${hc} ---`],
    [/^第(\d+)輪 · (.+)$/, (m, r, p) => `Round ${r} · ${p}`],
    [/^(.+?) 的(.+?): 要發動技能嗎\?$/, (m, a, w) => `${a}'s ${w}: activate a skill?`],
    [/^(.+?) 使用 (.+?),要打出(.+?)嗎\?$/, (m, a, c, n) => `${a} uses ${c}. Play ${n}?`],
    [/^(.+?) 對你使用殺,要打出(.+?)嗎\? \(不出會受到傷害\)$/, (m, a, n) => `${a} Slashes you. Play ${n}? (otherwise you take damage)`],
    [/^(\d+) 人$/, (m, n) => `${n} players`],
    [/^選擇棄 (\d+) 張: ?(.*)$/, (m, n, r) => `Choose ${n} to discard: ${r}`],
    [/^等待 P(\d+) ?(.*)$/, (m, i, c) => `Waiting for P${i} ${c}`],
    [/^體力 (\d+)\/(\d+)$/, (m, a, b) => `HP ${a}/${b}`],
    [/^手牌 (\d+)$/, (m, n) => `Hand ${n}`],
    [/^目前 (\d+)(?: \/ (\d+))? 人在線$/, (m, n, c) => `${n}${c ? "/" + c : ""} online`],
    [/^(.+?) 回合$/, (m, a) => `${a}'s turn`],
    [/^你\((.*)\)$/, (m, a) => `You (${a})`],
    [/^Round (\d+) 輪$/, (m, a) => `Round ${a}`],
  ],
  ja: [
    [/^(.+?) 受到 (\d+) 點(火|冰|雷)?傷害 \(來源 (.+?)\) -> 體力 (-?\d+)$/, (m, t, n, e, s, hp) => `${t} が${{ 火: "火", 冰: "氷", 雷: "雷" }[e] || ""}ダメージ${n}を受けた(原因 ${s}) -> 体力 ${hp}`],
    [/^(.+?) 對 (.+?) 使用 (.+)$/, (m, a, b, c) => `${a} が ${b} に ${c} を使用`],
    [/^(.+?) 使用 (.+)$/, (m, a, c) => `${a} が ${c} を使用`],
    [/^--- 第(\d+)輪 (.+?) 回合 體力(\d+) 手牌(\d+) ---$/, (m, r, p, hp, hc) => `--- 第${r}巡 ${p} のターン 体力${hp} 手札${hc} ---`],
    [/^第(\d+)輪 · (.+)$/, (m, r, p) => `第${r}巡 · ${p}`],
    [/^(.+?) 使用 (.+?),要打出(.+?)嗎\?$/, (m, a, c, n) => `${a} が ${c} を使用。${n} を出しますか?`],
    [/^(.+?) 對你使用殺,要打出(.+?)嗎\? \(不出會受到傷害\)$/, (m, a, n) => `${a} があなたに殺。${n} を出しますか?(出さないとダメージ)`],
    [/^(\d+) 人$/, (m, n) => `${n}人`],
    [/^選擇棄 (\d+) 張: ?(.*)$/, (m, n, r) => `${n}枚捨てる: ${r}`],
    [/^等待 P(\d+) ?(.*)$/, (m, i, c) => `P${i} ${c} を待っています`],
    [/^體力 (\d+)\/(\d+)$/, (m, a, b) => `体力 ${a}/${b}`],
    [/^手牌 (\d+)$/, (m, n) => `手札 ${n}`],
    [/^目前 (\d+)(?: \/ (\d+))? 人在線$/, (m, n, c) => `${n}${c ? "/" + c : ""}人オンライン`],
    [/^(.+?) 回合$/, (m, a) => `${a} のターン`],
    [/^你\((.*)\)$/, (m, a) => `あなた(${a})`],
  ],
};

/* ---------- 翻譯核心 ---------- */
let words = [], wre = null, pats = [], exact = {};
function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
function build() {
  const idx = lang === "en" ? 1 : 2;
  const map = new Map();
  for (const e of W) if (e[idx] != null) map.set(e[0], e[idx]);
  if (lang === "en") for (const [k, v] of Object.entries(NAMES)) map.set(k, v);
  if (lang === "ja") for (const k of Object.keys(NAMES)) map.set(k, ja(k));
  map.set("顏良&文醜", lang === "en" ? "Yan Liang & Wen Chou" : "顔良&文醜");
  map.set("郭圖&逢紀", lang === "en" ? "Guo Tu & Pang Ji" : "郭図&逢紀");
  words = [...map.keys()].sort((a, b) => b.length - a.length);
  wre = words.length ? new RegExp(words.map(esc).join("|"), "g") : null;
  W.map_ = map;
  pats = PAT[lang] || [];
  nameMap = new Map(Object.keys(NAMES).map(k => [k, lang === "en" ? NAMES[k] : ja(k)]));
  nameMap.set("顏良", lang === "en" ? "Yan Liang" : "顔良"); nameMap.set("文醜", lang === "en" ? "Wen Chou" : "文醜"); nameMap.set("郭圖", lang === "en" ? "Guo Tu" : "郭図"); nameMap.set("逢紀", lang === "en" ? "Pang Ji" : "逢紀");
  namesRe = new RegExp([...nameMap.keys()].sort((a, b) => b.length - a.length).map(esc).join("|"), "g");
  const k = lang === "en" ? 1 : 2;
  uiTpls = (window.SGS_UI_TPL || []).map(e => [new RegExp("^" + esc(e[0].trim()).replace(/\\{\\}/g, "(.+?)").replace(/,\s*/g, ",\\s*") + "$"), e[lang === "en" ? 1 : 2], e[0].length]).sort((a, b) => b[2] - a[2]);
  tpls = (window.SGS_LOG_TPL || []).map(e => [new RegExp("^" + esc(e[0].trim()).replace(/\\{\\}/g, "(.+?)").replace(/,\s*/g, ",\\s*") + "$"), e[k], e[0].length])
    .sort((a, b) => b[2] - a[2]);
}
let tpls = [], uiTpls = [];   // uiTpls: 介面樣板 (需要 {} / 成就「{}」…),{} 抓到的部分會再遞迴翻一次
function ja(s) { let o = ""; for (const c of s) o += JA_CHARS[c] || c; return o; }
const SHORT = {   // 戰報裡的牌名簡稱 -> [English, 日本語]
  "殺": ["Slash", "殺"], "閃": ["Dodge", "閃"], "桃": ["Peach", "桃"], "酒": ["Wine", "酒"], "順": ["Steal", "順手牽羊"], "過": ["Dismantle", "過河拆橋"],
  "反": ["Counter", "反撃"], "調": ["Divert the Tiger", "調虎離山"], "占": ["Divination", "占卜"], "南": ["Barbarians", "南蛮入侵"], "萬": ["Arrow Barrage", "万箭斉発"],
  "無": ["Windfall", "無中生有"], "無懈": ["Nullify", "無懈可撃"], "轉": ["Swap", "装備交換"], "突": ["Raid", "突襲"], "桃園": ["Peach Garden", "桃園結義"], "樂": ["Complacency", "楽不思蜀"],
  "聲": ["Feint", "聲東撃西"], "增": ["Reinforce", "増援"], "決": ["Duel", "決闘"], "強": ["Empower", "強化"], "弱": ["Weaken", "弱化"], "火攻": ["Fire Attack", "火攻"],
  "借": ["Borrowed Blade", "借刀殺人"], "飢": ["Famine", "飢餓"], "草": ["Scarecrow Panic", "草木皆兵"], "閃電": ["Lightning", "閃電"], "降雷": ["Thunder Call", "降雷"],
  "發": ["Resolve", "発憤図強"], "毒": ["Poison", "毒"], "兵": ["Starvation", "兵糧寸断"], "偽": ["Disguise", "偽装"], "出": ["Surprise Move", "出其不意"],
  "拋": ["Lure with Brick", "拋磚引玉"], "未": ["Plan Ahead", "未雨綢繆"], "笑": ["Hidden Dagger", "笑裏蔵刀"], "鴻": ["Hongmen Feast", "鴻門宴"], "隔": ["Watch the Fire", "隔岸観火"],
  "孤": ["All-In", "孤注一擲"], "投": ["Return the Favor", "投桃報李"], "五": ["Harvest", "五穀豊穣"], "鐵": ["Iron Chain", "鉄索連環"],
};
const SKILLS = [   // 〈武將-技能〉 的技能名
  [/^丁奉-棄置(.+)抽牌$/, "discard $1 & draw", "$1を捨てて引く"], [/^丈八蛇矛-雙牌當殺$/, "two cards as Slash", "2枚を殺として使う"],
  [/^伊籍-棄2張$/, "discard 2", "2枚捨てる"], [/^公孫淵-亮牌抽2$/, "reveal hand, draw 2", "手札公開して2枚引く"], [/^劉備-仁回血$/, "Benevolence heal", "仁で回復"],
  [/^劉備-棄錦囊得仁$/, "discard trick for token", "錦囊を捨てて仁を得る"], [/^劉禪-棄光並跳過回合$/, "discard all & skip turn", "全て捨てさせターンを飛ばす"],
  [/^吳懿-交換手牌$/, "swap hands", "手札交換"], [/^吳懿-抽牌$/, "draw when hurt", "受傷で引く"], [/^呂布-無效全場$/, "void everything", "全て無効"], [/^周魴-棄牌扣血$/, "discard to cost HP", "捨てて体力を奪う"],
  [/^孔融-重鑄手牌$/, "recast hand", "手札再鋳造"], [/^孫權-換牌$/, "exchange cards", "カード交換"], [/^孫權-殺殺$/, "two Slashes", "殺2枚"], [/^張松-指定$/, "designate", "指定"],
  [/^張苞-棄兩張(.+)$/, "discard two $1", "$1を2枚捨てる"], [/^張角-捨牌回血$/, "discard to heal", "捨てて回復"], [/^張遼-殺全部人$/, "Slash everyone", "全員に殺"],
  [/^張郃-無人可攻擊$/, "nobody to attack", "攻撃対象なし"], [/^曹操-弒抽牌$/, "token draw", "弒で引く"], [/^曹植-洗手牌$/, "shuffle hands", "手札シャッフル"],
  [/^李儒-逼出閃$/, "force a Dodge", "閃を強要"], [/^楊修-宣告吸收傷害$/, "declare absorb", "吸収を宣言"], [/^王允-全員重抽$/, "everyone redraws", "全員引き直し"],
  [/^賈詡-殺令決鬥$/, "Slash to start Duel", "殺で決闘させる"], [/^趙雲-棄牌或扣血$/, "discard or lose HP", "捨てるか体力-1"], [/^關興-棄兩張(.+)$/, "discard two $1", "$1を2枚捨てる"],
  [/^陳群-重鑄(.+)$/, "recast $1", "$1を再鋳造"], [/^陳群-手牌當突襲$/, "hand as Raid", "手札を突襲として使用"], [/^馬謖-換2張牌$/, "swap 2 cards", "2枚交換"], [/^黃蓋-苦肉$/, "Bitter Flesh", "苦肉の策"],
];
let shortRe1 = null, shortRe2 = null;
const FULL2SHORT = {};   // 卡牌全名 (反擊、無中生有…) → 簡稱 (反、無…),讓全名標籤也能翻譯
function syncFull() {
  try { if (typeof S !== "undefined" && S.cat) for (const [k, v] of Object.entries(S.cat)) if (v.full && v.full !== k && SHORT[k] && !SHORT[v.full]) FULL2SHORT[v.full] = k; } catch (e) {}
}
const shortOf = nm => SHORT[nm] || SHORT[FULL2SHORT[nm]];
function shortNames() { syncFull(); return Object.keys(SHORT).concat(Object.keys(FULL2SHORT)).sort((a, b) => b.length - a.length).map(esc).join("|"); }
function protect(t, store) {
  const tok = v => { store.push(v); return "\uE000" + (store.length - 1) + "\uE001"; };
  const k = lang === "en" ? 0 : 1;
  const col = c => c === "紅" ? (k ? "赤" : "Red ") : c === "黑" ? (k ? "黒" : "Black ") : "";
  const nat = c => !c ? "" : ({ 火: ["fire ", "火"], 冰: ["ice ", "氷"], 雷: ["thunder ", "雷"] })[c][k];
  t = t.replace(/\((無)(?=[\/)])/g, () => "(" + tok(k ? "役職なし" : "No role"));   // 玩家名稱裡的「無」是沒有身分,不是無中生有
  t = t.replace(/〈([^〉-]+)-([^〉]+)〉/g, (m, n, l) => {
    for (const [re, e, j] of SKILLS) if (re.test(n + "-" + l)) return tok("〈" + word(n) + "-" + skillText(re, e, j, n + "-" + l, k) + "〉");
    return m;
  });
  if (!shortRe1 || (S.cat && !Object.keys(FULL2SHORT).length)) { const n = shortNames(); shortRe1 = new RegExp("(紅|黑)(火|冰|雷)?(" + n + ")(?![㐀-鿿])", "g"); shortRe2 = new RegExp("(使用|打出|判定區|判定|亮出|展示|棄置|裝備|放入|將|⚡|\\(|\\/|: ?)( ?)(" + n + ")(?![㐀-鿿])", "g"); }
  t = t.replace(shortRe1, (m, c, na, nm) => tok(col(c) + (na && nm === "殺" ? (k ? nat(na) + "殺" : nat(na) + "Slash") : shortOf(nm)[k])));
  t = t.replace(shortRe2, (m, v, sp, nm) => v + sp + tok(shortOf(nm)[k]));
  return t;
}
const FACTION = { en: { "魏": "Wei", "蜀": "Shu", "吳": "Wu", "群": "Qun", "晉": "Jin" }, ja: { "魏": "魏", "蜀": "蜀", "吳": "呉", "群": "群", "晉": "晋" } };
function tr(s) {   // 勢力字 (魏蜀吳群晉) 在句首時一併翻譯
  const r = tr0(s);
  if (lang === "zh" || !r || !wre) return r;   // 詞典還沒建好時不動 (否則先翻一半會擋住之後的完整翻譯)
  return r.replace(/^(\s*)([魏蜀吳群晉])(?= )/, (m, sp, f) => sp + FACTION[lang][f]);
}
function tr0(s) {
  if (lang === "zh" || !s) return s;
  const t = s.trim();
  if (!t || !/[㐀-鿿]/.test(t)) return s;
  const lead = s.slice(0, s.indexOf(t)), trail = s.slice(s.indexOf(t) + t.length);
  if (exact[t]) return lead + names(exact[t]) + trail;
  { const m = t.match(/^([^㐀-鿿A-Za-z0-9]+)([㐀-鿿].*)$/s);   // 前面的符號 / 圖示 (「• 」「🔒 」「✔ 」…) 先拿掉,剩下的整句再查一次
    if (m && (exact[m[2]] || exact[m[2].replace(/[：:。！!…]+$/, "")])) return lead + m[1] + (exact[m[2]] || exact[m[2].replace(/[：:。！!…]+$/, "")]) + trail; }
  { let tm = null, um = null, tl = -1;   // 戰報樣板 (tpls) 與介面樣板 (uiTpls) 都對得上時,取原文較長 (較具體) 的那個
    for (const [re, o, len] of tpls) { const m = t.match(re); if (m) { tm = [m, o]; tl = len; break; } }
    for (const [re, o, len] of uiTpls) { const m = t.match(re); if (m) { if (len > tl) um = [m, o]; break; } }
    if (um) return lead + um[1].replace(/\{(\d+)\}/g, (x, i) => um[0][+i] == null ? "" : tr(um[0][+i])) + trail;
    if (tm) return lead + names(tm[1].replace(/\{(\d+)\}/g, (x, i) => tm[0][+i] == null ? "" : //.test(tm[0][+i]) ? tr(tm[0][+i]) : word(tm[0][+i]))) + trail; }
  for (const [re, f] of pats) { const m = t.match(re); if (m) return lead + f(...m.map((x, i) => i && typeof x === "string" ? word(x) : x)) + trail; }
  if (/^[^、]+「[^」]+」(、[^、]+「[^」]+」)+$/.test(t)) return lead + t.split("、").map(tr).join("、") + trail;   // 解鎖清單: 頭像框「A」、特效「B」
  for (const [re, o] of uiTpls) { const m = t.match(re); if (m) return lead + o.replace(/\{(\d+)\}/g, (x, i) => m[+i] == null ? "" : tr(m[+i])) + trail; }
  { const m = t.match(/^([^㐀-鿿A-Za-z0-9]+)([㐀-鿿].*)$/s);   // 前面的符號 (🔒 / 🤖 …) 拿掉,剩下的遞迴翻譯
    if (m && !/[〈〉「」]/.test(m[1])) { const r = tr(m[2]); if (r !== m[2]) return lead + m[1] + r + trail; } }
  return lead + word(t) + trail;
}
function names(t) {   // 只翻 [武將名] 等括號與殘留的武將名 (模板輸出已是目標語言,不能再套整本詞典)
  if (!namesRe) return t;
  return t.replace(namesRe, w => nameMap.get(w));
}
let namesRe = null, nameMap = new Map();
function skillText(re, e, j, t, k) { return t.replace(re, (m0, g1) => (k ? j : e).replace("$1", g1 ? word(g1) : "")); }   // 技能名裡的 $1 (例如「棄兩張殺」的牌名) 也要翻
function word(t) {
  { const tt0 = t.trim(); const mm = tt0.match(/^([^〈〉-]+)-([^〈〉]+)$/);   // 樣板只抓到「武將-技能」(括號在樣板上): 一樣查技能表
    if (mm) for (const [re, e, j] of SKILLS) if (re.test(tt0)) return t.replace(tt0, word(mm[1]) + "-" + skillText(re, e, j, tt0, lang === "en" ? 0 : 1)); }
  if (!wre) return t;
  const map = W.map_, store = [];
  const tt = t.trim();
  if (SHORT[tt] && tt !== "桃" && tt !== "酒" && tt !== "殺" && tt !== "閃") return t.replace(tt, SHORT[tt][lang === "en" ? 0 : 1]);
  t = protect(t, store);
  t = t.replace(/(\d+) 張(?=牌|[^㐀-鿿]|$)/g, (m, n) => lang === "en" ? n + " card(s)" : n + "枚");
  let out = t.replace(wre, w => map.get(w));
  out = out.replace(/\uE000(\d+)\uE001/g, (m, i) => store[+i]);
  if ((out.match(/[㐀-鿿]/g) || []).length > 8 && lang === "en") return t.replace(/\uE000(\d+)\uE001/g, (m, i) => store[+i]);   // 大段技能說明: 半翻半中反而難讀,維持原文
  if (lang === "en") out = out.replace(/ {2,}/g, " ");
  return out;
}

/* ---------- DOM 即時翻譯 ---------- */
const orig = new WeakMap();   // 文字節點 -> {zh, out}
const origAttr = new WeakMap();
const ATTRS = ["title", "placeholder", "aria-label", "alt"];
let busy = false;
function doText(n) {
  const v = n.nodeValue;
  const o = orig.get(n);
  if (o && o.out === v) { if (lang === "zh") { n.nodeValue = o.zh; orig.delete(n); } return; }
  if (lang === "zh") return;
  const out = tr(v);
  if (out !== v) { orig.set(n, { zh: v, out }); n.nodeValue = out; }
}
function doAttrs(e) {
  if (!e.getAttribute) return;
  let rec = origAttr.get(e);
  for (const a of ATTRS) {
    if (!e.hasAttribute(a)) continue;
    const v = e.getAttribute(a);
    if (rec && rec[a] && rec[a].out === v) { if (lang === "zh") { e.setAttribute(a, rec[a].zh); delete rec[a]; } continue; }
    if (lang === "zh") continue;
    const out = tr(v);
    if (out !== v) { if (!rec) { rec = {}; origAttr.set(e, rec); } rec[a] = { zh: v, out }; e.setAttribute(a, out); }
  }
}
function walk(root) {
  if (!root) return;
  if (root.nodeType === 3) return doText(root);
  if (root.nodeType !== 1) return;
  if (root.tagName === "SCRIPT" || root.tagName === "STYLE") return;
  doAttrs(root);
  const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    if (n.nodeType === 3) { if (n.parentNode && (n.parentNode.tagName === "SCRIPT" || n.parentNode.tagName === "STYLE")) continue; doText(n); }
    else doAttrs(n);
  }
}
const mo = new MutationObserver(muts => {
  if (busy) return;
  busy = true;
  try {
    for (const m of muts) {
      if (m.type === "characterData") doText(m.target);
      else if (m.type === "attributes") doAttrs(m.target);
      else m.addedNodes.forEach(walk);
    }
  } finally { busy = false; mo.takeRecords(); }
});
function start() { mo.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS }); }
function apply() {
  busy = true;
  try {
    build();
    walk(document.body);
    const T = document.querySelector("title");
    if (T) { if (!T._zh) T._zh = T.textContent; T.textContent = lang === "zh" ? T._zh : tr(T._zh); }
    document.documentElement.lang = lang === "zh" ? "zh-Hant" : lang;
  } finally { busy = false; mo.takeRecords(); }
}
async function loadExact() {
  exact = {};
  if (lang === "zh") return;
  try { exact = await (await fetch("/api/i18n?lang=" + lang)).json(); } catch (e) { exact = {}; }
}
async function setLang(l) {
  if (lang !== "zh") { lang = "zh"; apply(); }   // 先還原成中文原文,再翻成新語言 (否則譯文無法再被翻譯)
  lang = l;
  try { localStorage.setItem("sgs_lang", l); } catch (e) {}
  saveLangCookie();
  document.querySelectorAll('img[src^="/cards/"]').forEach(im => { im.src = im.getAttribute("src"); });   // 已畫出的卡面重抓,印章字換成新語言
  await loadExact();
  apply();
  refreshTut();
  document.querySelectorAll("select.langsel").forEach(x => { x.value = l; });
  const bl = document.getElementById("bLang"); if (bl) bl.textContent = { zh: "語言", en: "Language", ja: "言語" }[l];
  const tb = document.getElementById("bTut"); if (tb) { tb.textContent = TUT[l].btn; }
  if (typeof S !== "undefined" && S.snap) { try { S.handKey = null; } catch (e) {} }
  document.dispatchEvent(new CustomEvent("sgs-lang"));
}

/* ---------- 教學 ---------- */
let tutPage = 0;
function el(tag, props, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) { if (k === "class") e.className = v; else if (k.startsWith("on")) e[k] = v; else if (k === "text") e.textContent = v; else e.setAttribute(k, v); }
  for (const x of kids.flat()) if (x != null) e.append(x.nodeType ? x : document.createTextNode(x));
  return e;
}

/* ---------- 教學插圖 ---------- */
let CC = null;
fetch("/api/cardcat").then(r => r.json()).then(j => { CC = j; if (document.getElementById("tutov")) openTut(tutPage); }).catch(() => {});
const IMG = "/assets/三國殺牌/";
const NM = {   // 圖說: [中, 英, 日]
  殺: ["殺", "Strike", "殺"], 閃: ["閃", "Dodge", "閃"], 桃: ["桃", "Peach", "桃"], 酒: ["酒", "Wine", "酒"],
  順: ["順手牽羊", "Snatch", "順手牽羊"], 過: ["過河拆橋", "Dismantle", "過河拆橋"], 決: ["決鬥", "Duel", "決鬥"], 南: ["南蠻入侵", "Barbarians", "南蛮入侵"], 萬: ["萬箭齊發", "Arrow Barrage", "万箭斉発"], 無: ["無中生有", "Draw 2", "無中生有"],
  諸葛連弩: ["諸葛連弩", "Repeating Crossbow", "諸葛連弩"], 八卦陣: ["八卦陣", "Eight Trigrams", "八卦陣"], "+1馬": ["+1 馬", "+1 Horse", "+1 馬"], "-1馬": ["-1 馬", "-1 Horse", "-1 馬"],
  主公: ["主公", "Emperor", "君主"], 忠臣: ["忠臣", "Loyalist", "家来"], 反賊: ["反賊", "Rebel", "反逆者"], 內奸: ["內奸", "Spy", "内通者"],
};
const ROLEG = {   // 身分目標
  主公: ["殺光反賊與內奸", "Defeat all rebels and spies", "反逆者と内通者を倒す"], 忠臣: ["保護主公", "Protect the emperor", "君主を守る"],
  反賊: ["擊殺主公", "Kill the emperor", "君主を倒す"], 內奸: ["最後存活", "Be the last one alive", "最後まで生き残る"],
};
const ILLT = {   // 其他圖說
  flow: [["判定", "摸牌", "出牌", "棄牌"], ["Judge", "Draw", "Play", "Discard"], ["判定", "ドロー", "出牌", "捨て札"]],
  mockp: ["武將", "Hero", "武将"], mockhp: ["體力", "HP", "体力"], mockhand: ["手牌數", "Cards", "手札数"], mocktbl: ["牌桌", "Table", "卓"], mockmine: ["你的手牌 (在畫面下方)", "Your hand (bottom of screen)", "あなたの手札(画面下)"], mocklog: ["對局紀錄 (右側)", "Game log (right side)", "対局ログ(右側)"],
  step: [["① 點一張手牌", "② 選一個目標", "③ 按「使用」"], ["① Click a card", "② Pick a target", "③ Press Use"], ["① 手札をクリック", "② 対象を選ぶ", "③「使用」を押す"]],
  chain: [["① 殺", "② 無懈 (後出)", "③ 無懈 (最後出,最先結算)"], ["① Slash", "② Nullify", "③ Nullify (last, resolves first)"], ["① 殺", "② 無懈", "③ 無懈 (最後・最初に処理)"]],
  dying: [["體力 0", "有人出桃 → 存活", "沒人救 → 陣亡"], ["0 HP", "Someone plays a Peach → survives", "Nobody saves → dies"], ["体力 0", "桃を出す → 生存", "誰も救わない → 死亡"]],
  hp0: ["體力降到 0", "HP drops to 0", "体力が0に"],
};
function li() { return lang === "en" ? 1 : lang === "ja" ? 2 : 0; }
function cardImg(name, cap) {
  const src = CC && CC[name] && CC[name].img ? CC[name].img[name === "殺" ? "紅" : "紅"] : "";
  return el("div", { class: "icard" }, src ? el("img", { src, alt: name }) : el("div", { class: "iph", text: name }), el("div", { class: "icap", text: cap || NM[name][li()] }));
}
function roleImg(r) { return el("div", { class: "icard" }, el("img", { src: "/cards/_role_" + encodeURIComponent(r) + ".svg", alt: r }), el("div", { class: "icap", text: NM[r][li()] }), el("div", { class: "isub", text: ROLEG[r][li()] })); }
function chip(t, on) { return el("span", { class: "ichip" + (on ? " on" : ""), text: t }); }
function arrow() { return el("span", { class: "iarr", text: "➜" }); }
function mockPlayer(hl, hpn) {
  const L = li();
  return el("div", { class: "imp" + (hl ? " hl" : "") }, el("div", { class: "imph", text: ILLT.mockp[L] }), el("div", { class: "impi" },
    el("div", { text: "●".repeat(hpn == null ? 4 : hpn) + " " + ILLT.mockhp[L] }), el("div", { text: "🂠 4 " + ILLT.mockhand[L] })));
}
function tutIll(page) {
  const L = li(), row = (...k) => el("div", { class: "irow" }, k.flat());
  const wrap = x => el("div", { class: "till" }, x);
  if (page === 0) return wrap(row(["主公", "忠臣", "反賊", "內奸"].map(roleImg)));
  if (page === 1) return wrap(el("div", { class: "imock" },
    el("div", { class: "imtop" }, mockPlayer(false), mockPlayer(false), mockPlayer(true, 3)),
    el("div", { class: "imc" }, el("b", { text: ILLT.mocktbl[L] })),
    el("div", { class: "imbot" }, el("div", { class: "imlab", text: ILLT.mockmine[L] }), row(["殺", "閃", "桃"].map(n => cardImg(n)))),
    el("div", { class: "imside", text: ILLT.mocklog[L] })));
  if (page === 2) { const f = ILLT.flow[L]; return wrap(row(f.flatMap((t, i) => i ? [arrow(), chip(t, i === 2)] : [chip(t, false)]))); }
  if (page === 3) return wrap(row(["殺", "閃", "桃", "酒"].map(n => cardImg(n))));
  if (page === 4) return wrap(el("div", {}, row(["順", "過", "決", "南", "萬", "無"].map(n => cardImg(n))), row(["諸葛連弩", "八卦陣", "+1馬", "-1馬"].map(n => cardImg(n)))));
  if (page === 5) { const t = ILLT.step[L]; return wrap(row(el("div", { class: "istep" }, cardImg("殺"), el("div", { class: "icap", text: t[0] })), arrow(), el("div", { class: "istep" }, mockPlayer(true), el("div", { class: "icap", text: t[1] })), arrow(), el("div", { class: "istep" }, chip(NM.殺[L] + " ▶", true), el("div", { class: "icap", text: t[2] })))); }
  if (page === 6) { const t = ILLT.chain[L]; return wrap(row(el("div", { class: "istep" }, cardImg("殺"), el("div", { class: "icap", text: t[0] })), el("span", { class: "iarr", text: "⟵" }), el("div", { class: "istep" }, cardImg("無"), el("div", { class: "icap", text: t[1] })), el("span", { class: "iarr", text: "⟵" }), el("div", { class: "istep" }, cardImg("無"), el("div", { class: "icap", text: t[2] })))); }
  if (page === 7) { const t = ILLT.dying[L]; return wrap(row(el("div", { class: "istep" }, mockPlayer(false, 0), el("div", { class: "icap", text: t[0] })), arrow(), el("div", { class: "istep" }, cardImg("桃"), el("div", { class: "icap", text: t[1] })), el("span", { class: "iarr", text: "/" }), el("div", { class: "istep" }, el("div", { class: "iph big", text: "💀" }), el("div", { class: "icap", text: t[2] })))); }
  if (page === 8) return wrap(row(["青銅3", "白銀2", "黃金1", "白金3", "鑽石2", "大師1", "傳說"].map(r => el("span", { class: "rk big rk-" + r.replace(/\d+$/, ""), text: r }))));
  return null;
}
function tutBox() {
  let b = document.getElementById("tutov");
  if (!b) { b = el("div", { id: "tutov" }); document.body.append(b); }
  return b;
}
function closeTut() { const b = document.getElementById("tutov"); if (b) b.remove(); }
function openTut(p) {
  tutPage = p == null ? 0 : p;
  const T = TUT[lang], st = T.steps, box = tutBox();
  box.textContent = "";
  const [ti, body] = st[tutPage];
  const last = tutPage === st.length - 1;
  const dots = el("div", { class: "tdots" }, st.map((_, i) => el("i", { class: i === tutPage ? "on" : "", onclick: () => openTut(i) })));
  const dlg = el("div", { class: "tdlg" },
    el("div", { class: "th" }, el("b", { text: T.title }), el("span", { class: "tp", text: T.page.replace("{a}", tutPage + 1).replace("{b}", st.length) }),
      el("button", { class: "tx", text: "✕", onclick: closeTut })),
    el("h3", { text: ti }),
    el("div", { class: "tb" }, body.split("\n").map(l => el("p", { text: l }))),
    dots,
    el("div", { class: "tf" },
      el("button", { text: { zh: "🎓 練習關卡", en: "🎓 Practice levels", ja: "🎓 練習ステージ" }[lang], onclick: () => { closeTut(); if (window.SGS_LESSON) SGS_LESSON.open(); } }),
      el("span", { style: "flex:1" }),
      el("button", { id: "tutprev", text: T.prev, onclick: () => openTut(tutPage - 1) }),
      last ? el("button", { class: "primary", text: T.fin, onclick: closeTut })
           : el("button", { class: "primary", text: T.next, onclick: () => openTut(tutPage + 1) })));
  if (tutPage === 0) dlg.querySelector("#tutprev").disabled = true;
  const ill = tutIll(tutPage);
  if (ill) dlg.querySelector(".tb").after(ill);
  box.append(dlg);
}
const CATT = { btn: { zh: "🃏 卡牌圖鑑", en: "🃏 Card Gallery", ja: "🃏 カード図鑑" }, title: { zh: "卡牌圖鑑", en: "Card Gallery", ja: "カード図鑑" }, back: { zh: "← 回到教學", en: "← Back to tutorial", ja: "← チュートリアルへ" } };
function cardItems(cat) {   // 卡牌圖鑑的每一格 (教學彈窗與側欄分頁共用): [{node, text}]
  const T = x => (typeof tr === "function" ? tr(x) : x), out = [];
  for (const [k, v] of Object.entries(cat)) {
    if (/^[火冰雷]殺$/.test(k)) continue;
    const eq = /^(裝備|武器)[(（]/.test(v.desc);   // 武器 / 防具 / 坐騎: 名字用牌名,說明保留「裝備(類型)」
    const full = eq ? k : (v.desc.match(/^([^:：]+)[:：]/) || [0, k])[1];
    const nm = lang !== "zh" && !eq && SHORT[k] ? ((full.match(/^[⚡⏳]\s*/) || [""])[0]) + SHORT[k][lang === "en" ? 0 : 1] : T(full);
    const ds = eq ? T(v.desc) : (exact[v.desc] ? exact[v.desc].replace(/^[⚡⏳]\s*/, "") : T(v.desc.replace(/^[^:：]+[:：]\s*/, "")));
    out.push({ text: (k + " " + full + " " + v.desc + " " + nm + " " + ds).toLowerCase(),
      node: el("div", { class: "cgi" }, el("span", { class: "bigw", style: "flex:none" }, el("img", { src: v.img["紅"] || v.img["黑"], loading: "lazy" }), v.tp ? el("span", { class: "tp", text: T(v.tp) }) : null),
        el("div", {}, el("b", { text: nm }), el("div", { class: "cgd", text: ds }))) });
  }
  return out;
}
let cdCat = null;
async function renderCardPane() {   // 側欄「卡牌」分頁: 圖鑑 + 搜尋
  const q = document.getElementById("cdq"), L = document.getElementById("cdl"); if (!q || !L) return;
  if (!cdCat) { L.textContent = "…"; try { cdCat = await (await fetch("/api/cardcat")).json(); } catch (e) { L.textContent = String(e); return; } }
  const items = cardItems(cdCat), w = q.value.trim().toLowerCase();
  L.textContent = "";
  for (const it of items) if (!w || it.text.includes(w)) L.append(it.node);
  if (!L.children.length) L.append(el("div", { class: "meta", text: lang === "en" ? "No matching card" : lang === "ja" ? "該当するカードなし" : "找不到符合的卡牌" }));
}
async function openCatalog() {
  const box = tutBox(); box.textContent = "";
  const grid = el("div", { class: "cgrid" }, el("p", { text: "…" }));
  const dlg = el("div", { class: "tdlg cgdlg" },
    el("div", { class: "th" }, el("b", { text: CATT.title[lang] || CATT.title.zh }), el("button", { class: "tx", text: "✕", onclick: closeTut })),
    grid,
    el("div", { class: "tf" }, el("button", { text: CATT.back[lang] || CATT.back.zh, onclick: () => openTut(tutPage) })));
  box.append(dlg);
  let cat = {};
  try { cat = await (await fetch("/api/cardcat")).json(); } catch (e) { grid.textContent = String(e); return; }
  grid.textContent = "";
  for (const it of cardItems(cat)) grid.append(it.node);
}
function refreshTut() { if (document.getElementById("tutov")) openTut(tutPage); }
window.SGS_HINT_OFF = () => {};   // 舊的練習提示橫幅已移除,保留空函式給其他檔案呼叫

/* ---------- 啟動 ---------- */
const CSS = `
#langsel,.langsel{background:#1b2230;color:#e6edf7;border:1px solid #394559;border-radius:6px;padding:3px 6px;font-size:13px}#bLang{display:none}#langpop{position:fixed;inset:0;z-index:9600;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center}#langpop .lpbox{display:flex;flex-direction:column;gap:8px;min-width:min(260px,80vw);background:#0b1a30;border:1px solid #24557d;border-radius:12px;padding:14px;box-shadow:0 10px 30px rgba(0,0,0,.6)}#langpop button{min-height:46px;font-size:15px;border-radius:8px}#langpop button.on{border-color:#e9bf62;color:#e9bf62}#auth h2,#rooms h2{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px}#auth h2{justify-content:center}h2 .langsel{min-height:32px;font-size:13px;font-weight:400}
#tutov{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:9000;display:flex;align-items:center;justify-content:center;padding:16px}
.tdlg{background:#161c28;color:#e6edf7;border:1px solid #394559;border-radius:12px;max-width:560px;width:100%;padding:18px 20px;box-shadow:0 10px 40px rgba(0,0,0,.6);max-height:90vh;max-height:90dvh;overflow:auto;-webkit-overflow-scrolling:touch}
.tdlg .th{position:sticky;top:-18px;margin:-18px -20px 0;padding:14px 20px 8px;background:#161c28;z-index:2}.tdlg .tf{position:sticky;bottom:-18px;margin:0 -20px -18px;padding:10px 20px 14px;background:#161c28;z-index:2}
.tdlg .th{display:flex;align-items:center;gap:10px;color:#9fb0c8;font-size:13px}.tdlg .th b{color:#fff;font-size:14px}.tdlg .tp{flex:1;text-align:right}
.tdlg .tx{background:none;border:0;color:#9fb0c8;font-size:18px;cursor:pointer}
.tdlg h3{margin:12px 0 8px;font-size:20px}.tdlg .tb p{margin:6px 0;line-height:1.6;font-size:15px}
.tdots{display:flex;gap:6px;justify-content:center;margin:14px 0}.tdots i{width:9px;height:9px;border-radius:50%;background:#394559;cursor:pointer}.tdots i.on{background:#3fd2ff}
.tf{display:flex;gap:8px;align-items:center}
.tf button{background:#232c3d;color:#e6edf7;border:1px solid #394559;border-radius:7px;padding:7px 14px;cursor:pointer;font-size:14px}
.tf button.primary{background:#2a7de1;border-color:#2a7de1}.tf button:disabled{opacity:.4;cursor:default}
.till{margin:10px 0 0;padding:10px;background:#0f1522;border:1px solid #2a3547;border-radius:10px}
.irow{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;align-items:center}
.icard{width:68px;text-align:center}.icard img{width:68px;border-radius:5px;display:block;box-shadow:0 2px 8px rgba(0,0,0,.5)}
.iph{width:68px;height:96px;border:1px dashed #394559;border-radius:5px;display:flex;align-items:center;justify-content:center;color:#9fb0c8;font-size:13px}.iph.big{font-size:36px;height:70px}
.icap{font-size:12px;color:#c7d3e6;margin-top:4px;line-height:1.3}.isub{font-size:11px;color:#8fa3bf;margin-top:2px;line-height:1.3}
.ichip{background:#232c3d;border:1px solid #394559;border-radius:99px;padding:5px 12px;font-size:13px}.ichip.on{background:#2a7de1;border-color:#2a7de1;color:#fff}
.iarr{color:#3fd2ff;font-weight:700;font-size:16px}
.istep{display:flex;flex-direction:column;align-items:center;gap:2px;max-width:120px}
.imp{width:104px;background:#16202f;border:1px solid #2f3d52;border-radius:6px;padding:5px;font-size:11px;color:#c7d3e6}.imp.hl{border-color:#3fd2ff;box-shadow:0 0 8px rgba(63,210,255,.5)}.imph{font-weight:700;color:#fff;margin-bottom:2px}
.imock{position:relative;display:flex;flex-direction:column;gap:8px;align-items:center;padding-right:0}
.imtop{display:flex;gap:8px;justify-content:center}.imc{padding:5px 18px;border:1px solid #2a5a7c;border-radius:99px;color:#7fb7dd;font-size:12px}
.imlab,.imside{font-size:11px;color:#8fa3bf;text-align:center}.imbot{display:flex;flex-direction:column;align-items:center;gap:4px}
.tdlg.cgdlg{max-width:760px;width:min(760px,96vw)}#cdl{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px}.cgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px;max-height:62vh;overflow:auto;padding:4px 2px}.cgi{display:flex;gap:10px;align-items:flex-start;background:#0c1d36;border:1px solid #24557d;border-radius:8px;padding:6px}.cgi img{width:56px;border-radius:4px;flex:none}.cgi .bigw{width:56px}.cgi .bigw .tp{font-size:9px;left:2px;bottom:2px;padding:1px 3px;border-width:1px}.cgd{font-size:12px;color:#a9c4de;margin-top:2px;line-height:1.4}
`;
function openLangPop() {
  if (document.getElementById("langpop")) return;
  const close = () => { const x = document.getElementById("langpop"); if (x) x.remove(); };
  const pop = el("div", { id: "langpop", onclick: e => { if (e.target === pop) close(); } },
    el("div", { class: "lpbox", role: "dialog", "aria-label": "Language" },
      LANGS.map(([v, n]) => el("button", { type: "button", class: v === lang ? "on" : "", text: n, onclick: () => { close(); setLang(v); } }))));
  document.body.append(pop);
}
function init() {
  const st = document.createElement("style"); st.textContent = CSS; document.head.append(st);
  const top = document.getElementById("top");
  const mkSel = id => { const x = el("select", { class: "langsel", title: "Language / 言語 / 語言" }, LANGS.map(([v, n]) => el("option", { value: v, text: n }))); if (id) x.id = id; x.value = lang; x.onchange = () => setLang(x.value); return x; };
  window.SGS_LANGSEL = () => mkSel();   // 設定頁裡的語言選單
  for (const box of document.querySelectorAll("#auth .rbox")) {   // 登入畫面 (還進不去設定) 也能直接切換語言
    const h2 = box.querySelector("h2"); if (h2) h2.append(mkSel());
  }
  const tb = el("button", { id: "bTut", text: TUT[lang].btn, onclick: () => openTut(0) });
  const bn = document.getElementById("bNick");
  const LBL = { zh: "語言", en: "Language", ja: "言語" };
  const bl = el("button", { id: "bLang", type: "button", title: "Language / 言語 / 語言", onclick: () => openLangPop() });   // 手機選單用: 點開再選語言
  bl.textContent = LBL[lang];
  if (top && bn) top.insertBefore(tb, bn);   // 語言選單移進設定頁
  start();
  loadExact().then(() => { apply(); });
  try { if (!localStorage.getItem("sgs_tut_seen")) { localStorage.setItem("sgs_tut_seen", "1"); } } catch (e) {}
}
function mark(n) { orig.set(n, { zh: n.nodeValue, out: n.nodeValue }); return n; }   // 已經翻好的文字節點: 不要讓逐節點翻譯再碰一次
window.SGS_I18N = { renderCardPane, setLang, tr, mark, openTut, get lang() { return lang; } };
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
