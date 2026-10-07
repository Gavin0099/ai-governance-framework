# S0：目前決策表

日期：2026-09-15。這是本輪唯一決策入口；原始查核資料另存同目錄 JSON。

## 依據與界線

- 工作順序與能力凍結：來自本輪 owner 明示的 S0 → S1 → S2 → S3 → S4 指令。
- owner 後續要求將 closeout 問題加入排程並分析優先權。下表 S1.5 是本輪 AI 排程建議，尚不是 owner 對 reproduction、修復、merge 或平台事件觸發的授權。
- repo 已交付內容的固定基準：`beecfd8d36f83dbb6c2dc04010f0c8f19c71c482`。本次查詢的 GitHub main 與 GitLab main 均指向此 OID；只聲明查詢時的遠端狀態。
- 乾淨隔離 checkout：`E:/BackUp/Git_EE/ai-governance-framework-worktrees/s0-state-reconciliation-20260915`，detached HEAD 固定於上述 OID。
- 原工作區仍在 `codex/engineering-explanation-contract`、`be5734cc8d1ba1a4f68f84e6752f08ff58488ecd`，落後六個提交；本輪沒有 pull、stash、切換原分支或恢復任何舊工作。
- 本表是具來源的本輪對帳結果，尚未提交或獨立審查，不是新的治理規則，也不使舊 memory／PLAN 自動成為當前授權。
- S0 許可：查核、分類、產生本表與證據、canonical writer 記錄。S1 之後的實作、PR disposition、cleanup、PLAN 改寫、commit/push 不在本輪執行。

## 唯一 current decision table

| 順序／項目 | 固定基準下的狀態 | Findings／取代關係 | 本輪決策或建議 |
| --- | --- | --- | --- |
| S0：狀態對帳 | main OID 與隔離 checkout 已固定；5 PR、144 個既有 dirty 路徑項目已有證據清單 | 既有目錄以整個目錄為分類單位；6 個不可讀目錄另保留 unknown 警告 | 產出本表後停止。不是整個 repo 已完成或原工作區已對齊 |
| S1：PR #179，對齊 lock 的提示文字 | Open、非 Draft；與固定 main 的衝突只在兩份 memory 文件 | 0 個 inline review threads；不等於獨立 review 通過。`superseded-by: NOT_ESTABLISHED`；#177/#180 是 memory 完成邊界與提示，不是此 lock 顯示修正 | owner 的第一交付目標。後續從 resolution HEAD 重建 scoped diff、tests、current-HEAD review 與合併資格；不能沿用舊綠燈 |
| S1.5 建議：closeout 最小 reproduction | 本 repo daily 可觀察到 canonical closeout missing 與 stale_or_mismatched 終態；runtime input 與中間資料鏈尚未重播 | 是既有缺陷診斷，不是新 Memory 能力。失敗終態可見，首次出錯位置及 code-level root cause 未確認；無已驗證修復版本 | 建議排程優先度高：#179 後、#178 前先診斷。若證實已知輸入在支援路徑遺失，優先修該跳；若平台／session 來源不明，保留 UNKNOWN，不阻塞整批 PR |
| S2：PR #178，Lenovo composed hook | Open、非 Draft；兩個 memory 文件衝突；1 個未解決、未過期 P2 | 獨立 installer 更新合法舊 hook 的問題尚未重播。PR 文件明文包含 standalone installer 的新 base 安裝；`superseded-by: NOT_ESTABLISHED` | owner 的第二交付目標。S2 先重播該支援路徑；若成立，修復或由 owner 明確接受縮限，不能以其他 adoption path 綠燈掩蓋 |
| S3：PR #176，歷史 daily 記錄恢復 | Draft；daily 2026-09-14 add/add 衝突 | 12 份歷史日期文件的 25 個新增 path+record_identity 配對，均未見於 main 的同日期文件；不是 25 個獨立工作項。`superseded-by: NOT_ESTABLISHED` | 留待 RETAIN／SUPERSEDED／PARTIALLY_SUPERSEDED／RETIRE 決定；目前沒有「main 已吸收」證據，不預設解衝突或刪除 |
| S3：PR #88，交付末端記錄觀察 | Draft；authority contract 與 daily memory 衝突；沒有 inline review thread | PR 是 latest substantive state 的 terminal-closeout 觀察；本地 candidate 是 range-any companion 觀察。main 的 memory_provenance.py 未含兩者符號。`superseded-by: NOT_ESTABLISHED` | 先選唯一保留路線與需求，再決定舊 PR 去留；禁止兩邊同時修。既有 memory 功能或 #180 不足以證明此 PR 已被取代 |
| S3：PR #80，第二 repo 的 incident knowledge | Open、非 Draft；daily memory add/add 衝突；1 個未解決、未過期 P2 | 審查指出引用 commit 不在 PR 可取得歷史；canonical known_incidents.md 仍只有第一次發生的記錄。`superseded-by: NOT_ESTABLISHED` | 保留知識的需求與是否救回此 PR 分開決定。不能因已有一般 memory 治理而認定 incident 已保存；若 retire，先選可追溯的知識保留方式 |
| S4：workspace／PLAN current-state reconciliation | 原工作區 dirty；staged pilot 文件少了 main 的 owner amendment 確認行；active-task 混有舊狀態 | memory protocol 本地內容與 main 相同（BOM／CRLF 正規化後），該本地語義候選已 superseded。其餘逐項見 inventory，未授權刪除 | 等交付與 S3 處置後再做限定 cleanup／PLAN 對帳；不以未勾選或較早 next_step 恢復工作 |
| 新 Memory／cross-session／isolation 能力 | NOT CURRENT WORK：暫停擴張 | 功能缺口與既有 closeout 缺陷分開；歷史執行鏈後續 PLAN 不構成執行授權 | 本輪不開設計、不實作、不資格認證 |
| 外部工程師與治理效果證據 | 保留證據缺口，不自動轉成框架 code backlog | Lite 未建立穩定優勢是既有結果，不改写為「實驗未完成」；效果／成本效益不從 gate 或 writer 綠燈推導 | 等交付收斂後再決定是否收集自然證據 |
| v1.3.0 | NOT RELEASE-READY：本轮 owner 的發布處置 | 產生物不是 release readiness 證據；本輪未做完整發布資格審查 | 作為 PR 債務、狀態一致性、release contents 與指定 consumer evidence 滿足後的結果 gate，不另開 release task |

## PR 身分、衝突與意見

所有 PR 的 base branch 都是 `main`。以下 `baseRefOid` 是查詢當下 API 回傳值，不能當成當前 main；各項合併預演一律使用固定 `beecfd8d...` 與 PR HEAD。#88 的共同祖先另列，避免誤把 base metadata 當成 merge-base。

- **#179**：HEAD `774bda1ee017b0e919a8546d7f4a594981137cc8`；API base／merge-base `85adb41cf9151762909d37c3e1e801d8e3c311fa`。衝突：`memory/04_review_log.md`、`memory/2026-09-14.md`。取代關係：尚未建立。[PR](https://github.com/Gavin0099/ai-governance-framework/pull/179)
- **#178**：HEAD `663d13d2a5bb5e241e7879f864b9d2ebff26ff14`；API base／merge-base `85adb41cf9151762909d37c3e1e801d8e3c311fa`。衝突同 #179。P2 位置：該 HEAD 的 `governance_tools/hook_installer.py:804`。支援範圍來源：該 HEAD 的 `docs/governance/canonical-composed-hook-support.md`，Comparison and installation 段落明文包含 standalone installer。[意見](https://github.com/Gavin0099/ai-governance-framework/pull/178#discussion_r4003850697)
- **#176**：HEAD `4245db94dc6fd1ad91a0afd5eff20633b7ec7dfe`；API base／merge-base `be5734cc8d1ba1a4f68f84e6752f08ff58488ecd`。衝突：`memory/2026-09-14.md`。25 筆以日期路徑與 record_identity 的配對計算，沒有因此證明內容正確或需要合併。[PR](https://github.com/Gavin0099/ai-governance-framework/pull/176)
- **#88**：HEAD `c6a8976bc13360d155af4df7f7eb4cef9afc7c75`；API base `4b84b8d477639a4ea258275c51ad4bc199ee7545`；固定基準共同祖先 `6fedb405531bbe920b7f267cfa49b5d00bc841ad`。衝突：`governance/MEMORY_AUTHORITY_CONTRACT.md`、`memory/2026-08-21.md`。[PR](https://github.com/Gavin0099/ai-governance-framework/pull/88)
- **#80**：HEAD `b1639e3f07db369e82f8503fec22b083b8b56ae1`；API base／merge-base `9772f840fa750c15514f685414f7c3b87bb70240`。衝突：`memory/2026-08-21.md`。P2 位置：該 HEAD 的 `memory/2026-08-21.md:8`；保留其原 P2 標籤，未將本輪排程優先度當成缺陷分級。[意見](https://github.com/Gavin0099/ai-governance-framework/pull/80#discussion_r3826733680)

現有 HEAD 的 check rollups 皆為 SUCCESS 或 SKIPPED，沒有 failure。它们不是 resolution HEAD 的證據。本輪未重跑程式測試，沒有核准任一 PR 合併，也沒有判定 P2 已解決。

## Dirty 分類的解讀

`dirty-inventory.json` 對 S0 開始時 `git status --porcelain=v1 -z --untracked-files=normal` 回報的 **144 個路徑項目**逐項保留 status、分類、理由、是否可刪及檔案雜湊：

- `retained candidate`：37 項，僅代表保留候選／歷史證據，不代表通過審查或應交付。
- `superseded`：1 項，`governance/MEMORY_PROTOCOL.md` 與固定 main 內容相同（忽略 BOM／CRLF）；沒有新語義變更待交付，仍不授權丟棄。
- `generated`：11 項，release／status generated README 支持其產生物性質；不宣稱已發布或可以刪除。
- `unknown`：95 項，包括 staged pilot 的授權確認行刪除及用途未核實的暫存／工作樹目錄；不能因 `.tmp_` 名稱推論可安全刪除。

每個 untracked 目錄是一個保留單位，未遞迴宣稱內容全數審查。另有 Git 回報的 6 個 access-denied 目錄，清單保存在 discovery_warnings，全部視為 unknown；144 不包含這 6 個未能完整探索的盲點。這是有限深度的逐項分類，不是完整 filesystem census。

原有 daily/review-log 只准由 canonical writer 追加本輪紀錄；其既有內容必須保留。active-task 原文、PLAN、index 與其他既有文件保持原樣；本表與新增證據不混入上述 144 項歷史計數。

## 舊狀態如何被覆蓋

- M3-b-2A：`ff9cdb77` 實作與 `a59b0aef`（#108）合併均在固定 main 歷史內，checkpoint 涉及的檔案仍存在。因此「該 checkpoint 尚未提交」不是當前交付狀態；這不宣稱原生執行已接通。
- 單一 owner 合併規則：#104 合併 `f788e2b0` 已在固定 main；PLAN 的早期進行中標記不能要求重做交付。
- #28：合併 `bb0f3333` 已在固定 main；早期「先處置 PR28」不是尚未合併的證據。
- #177/#180：已在固定 main。本地舊版完成提示不應再驅動重複修正；上述版本差異也未包含 closeout bridge 修復。

## Closeout reproduction 的優先權與驗收界線

**排程建議：高優先診斷，置於 #179 後、#178 前。這不是 P1 缺陷裁決。** 已有重複終態異常，可能影響跨 session 交接及稽核；但未證明現有 PR 的獨立測試或 Git 身分證據失效，所以不把它升成所有交付的共同 blocker。

原始 owner 描述中的 `unbound_memory=4`、`85adb41` 消費環境及 writer／guard 正常，列為 owner-provided context，未綁到本 repo 同一次 reproduction。此 repo 兩份 daily 可確認的是收尾終態字串；從終態還不能證明已知 runtime 輸入在特定程式行遺失。

之後若授權 reproduction，先固定平台／harness、repo、framework OID、session identity、事件來源與已知 task_intent／summary；在隔離 fixture 比較 runtime input → canonical closeout JSON → session-index → daily memory。核對各層的語義對應與允許轉換，找出第一個消失／錯配邊界。fixture 成功不證明自然平台 session-end 事件已閉環。

修復驗收只適用於該綁定案例：task_intent 與 summary 保留、canonical closeout 存在、session-index 身分相符、该案例 stale_or_mismatched 不再發生、memory guard 沒有新 blocker。必須保留錯誤／缺少必要資料時仍拒絕的反向案例；不能靠降低 verifier 條件製造成功。

歷史 warning 清理、framework 升版、新 session schema、各平台一併改造、closeout bridge 實作都不在 S0。若證實原始事件不是該平台定義的 session end，先修正事件適用性判讀，不把 task DONE／每回合 Stop 當 session end。

## 證據與完成範圍

- `anchor.json`：原／隔離 checkout、index tree、遠端 OID 與時間。
- `prs.json`、`review-threads.json`：PR HEAD/base、check rollups、未解決 thread。
- `pr-*-merge-tree.txt`：固定 main 與各 HEAD 的不改工作樹合併預演；exit 1 是預期的衝突觀察，不是測試失敗。
- `supersession-evidence.json`：逐項取代證據及其限制；不是全 repo 語義等價證明。
- `dirty-inventory.json`、`status-before.txt`：既有 dirty 清單與分類。
- `state-claims.json`：歷史 commit 祖先關係与相關檔案存在證據。
- `closeout-priority-evidence.json`：owner 描述與本地終態觀察分離。
- `verification.json`：隔離基準、PR 身分、原檔／index 保留與表格覆蓋驗證。
- `memory-writer-result.json`、`memory-workflow-check.json`：canonical 記錄與範圍檢查結果；不證明記憶內容正確或 closeout bridge 已修復。
- `response-envelope.json`：本輪範圍、授權、非宣稱及下一步。

本輪只產出 S0 對帳候選與 closeout 優先權分析。沒有實作、解衝突、關閉 PR、清理、PLAN 改寫、commit、push、reproduction 或 session closeout。下一個既定交付目標是 #179；S1.5 仍為待採用的插入建議。
