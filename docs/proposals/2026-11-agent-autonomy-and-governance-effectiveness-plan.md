# AI Governance — Agent 自主交付與治理效益驗收計畫 v2

**建立日期：** 2026-11-02（Asia/Taipei）  
**最近文件對帳：** 2026-11-05（Asia/Taipei）；歷史快照以標示日期為準  
**後續方向增補：** 2026-11-14（§2.1；不改變舊快照的日期與狀態）  
**狀態：** Owner 已確認規劃方向；**Docs-only Draft Proposal，尚非正式治理權威或執行授權**  
**公開內容限制：** 只使用「Internal Consumer」指稱非公開專案，不揭露內部位置、組織、客戶、產品或任務細節。

> **唯一要回答的問題：AI Governance 能不能讓 Agent 更少需要人工救援、更可靠地完成工程工作，且增加的 Token、時間與人工負擔值得？**
>
> **兩個產品目標必須分開驗收：** (1) AI 自主完成一項真實工程任務；(2) Governance 相對於 Baseline／Rules Only 是否提供可觀察的淨效益。成功 HOLD 只證明拒絕行為，不算產品完成。

## 產品方向：三個核心 Goal（Owner 已確認方向；非新增 Gate／Policy）

**優先順序：Goal 1 可信任決策 > Goal 2 效率 > Goal 3 有邊界的持續自主性。** 三者是長期產品方向，不是三項新的執行 Gate；任何量化門檻、技術方案、實驗變更或執行權限仍按既有契約另行凍結／核准。既有**兩項分開驗收的產品條件**保持不變：(1) 真實任務能自主完成，由 V-03～V-05 檢驗；(2) Governance 比沒有 Governance 有可觀察淨效益，由 E-01 檢驗。**E-01 受控比較是驗證 Goal 1 與 Goal 2 的主要方法**，不因新增 Goal 敘述而取消 A/B/C 對照。

### Goal 1 — Trustworthy Agent Decisions（不可犧牲的可信任基礎）

**Agent 可以自行決定怎麼完成任務，但不能自行改變什麼叫完成。**

降低 Agent 因迎合使用者、追求 PASS、趕進度、規避困難、修改測試使結果看似成功，或掩蓋不利證據而做錯決策／錯誤宣稱完成的風險。以 Owner 事前凍結的需求、允許／禁止範圍、驗收 Oracle 及可重現證據為準；無充分證據就如實報告 PARTIAL／HOLD／NOT_ASSESSABLE，不因任何 AI（包括不同模型、其他 reviewer Agent）的 PASS／APPROVE 自動視為獨立證明。任何 AI 審查只能是輔助，最終仍須符合外部、事前固定且可獨立重現的驗收。

**正確 HOLD 與不必要 HOLD 必須分別計數：** 由事前契約／獨立 Oracle 判定應停而停，是安全行為的證據，但不是產品交付成功；原本可合法繼續卻停下或重複詢問，是 Goal 2 的成本及 Goal 3 的摩擦／失敗。不能把所有 HOLD 當成功，也不能以跳過必要 HOLD 來提升自主完成率。

### Goal 2 — Efficient, Risk-Proportionate Governance（可信前提下的最小合理成本）

在 Goal 1 與不可豁免的授權／安全邊界內，依任務風險、複雜度、可驗證性選擇最小必要檢查，避免重讀指令、重複 Review、過量 Evidence／Memory、無增益的文件與人工確認。**只參照 #260 既有 `minimal`／`standard`／`strict` 提案（其更正及採納仍待審議）；不在本文件另立第二套分級、預設啟用或授權實作。** 調整成本不能放寬已生效的 Owner Gate 與硬性安全契約。

實驗只用可觀測成本與結果：Token／金額（可取得時）、總耗時、重讀／工具呼叫、人工互動（RESCUE、APPROVAL、CLARIFICATION 各計次數與耗時）、返工次數，以及**獨立封存 Oracle 揭露的缺陷中，Agent 已宣稱 DONE 的件數**。不把不可測量的「未發現缺陷損失」當成本 KPI。保留各平台實際載入的指令檔大小與載入證據，包括 Codex 的 AGENTS.md **32 KiB 預算**；驗證受當時工具版本與實際載入機制約束，不以檔案存在推定已讀取。

### Goal 3 — Continuous, Bounded Agent Autonomy（預授權範圍內持續執行）

一旦 Owner 固定最終目標、驗收、允許／禁止操作、資源與授權邊界，Agent **應該**能自行規劃、實作、測試、修正、留下必要紀錄並接續下一 Slice；**Slice DONE 不等於 Task DONE**，已授權範圍內的下一步不應反覆向 Owner 索取同一核准。這是**待驗證的產品方向，不是宣稱目前已有跨 Session 自動 Loop controller**。沿用 #271 及既有 autonomous-loop 草稿作為提案參考；不重啟暫緩的 controller 實作，也不新增 daemon／Hook／Schema。跨 Session 的真實驗收仍受 #275、#261、#245 與 Consumer 既有 legacy closeout 狀態影響；PR merge 本身不等於 V-03／V-04／V-05 DONE。

- **不必要停頓的可操作定義：** Agent 停下來詢問的答案，其實已由事前凍結的契約／已授權決策明確給出，而且沒有新風險、新資訊或新的授權邊界。保留問題、契約定位、等待時間與是否重複核准的證據。
- **解讀需求不得偷偷改驗收：** Agent 在契約允許的空間做推論，應記錄所採用假設與依據；若假設將改變驗收標準、授權範圍、禁止操作或重要安全條件，必須停止取得 Owner 裁決，不得用假設代替核准。
- **停止條件與介入分類分開：** `RESCUE` 是人類提供解法，`APPROVAL` 是人類核准，`CLARIFICATION` 是澄清需求；這三類只用於統計互動，**不直接決定是否停止**。是否停止由下表的觸發條件判定。

| Stop／Continue 判斷 | 行為 | 計分邊界 |
|---|---|---|
| 子 Slice 已完成，下一步在已凍結目標與授權內 | **CONTINUE**；自行選下一步 | 無需重複 APPROVAL；停問已知答案記不必要停頓 |
| 必要驗收 Oracle 已 PASS、合法 Closeout 及整體目標完成 | **DONE** | 產品交付成功仍依 V-05 獨立驗收 |
| 新操作超出授權／須新高風險核准 | **HOLD / APPROVAL** | 正確停止是安全證據，不是交付成功 |
| 解讀會改驗收標準、或關鍵需求無法由凍結契約決定 | **HOLD / CLARIFICATION** | 不能自行放寬標準 |
| 不可接受風險、不可恢復阻擋、無效反覆重試或預算／時間上限 | **HOLD / PARTIAL** 並揭露原因 | 停滯與停損判準需事前固定；不得無限 Loop |
| 可在授權內修復且尚未觸及停損 | **RETRY / CONTINUE** | 記錄有限重試及返工，不以重新提問代替分析 |

**Loop 的 Token、時間、重試上限、停滯判準與停止門檻均由 Owner 在實驗前凍結，Agent 不得自行創設／放寬數字。** 若 Harness 不支援真實持續執行，只能報告已觀察到的接續能力，不能將文件規劃當作實際 runtime 保證。

### 三個 Goal 與既有驗收的關係／E-01C 機制去留原則

- **V-03／V-04／V-05**：先在一個 Internal Consumer、優先候選 Claude（實際啟動前核准）驗證真實跨 Session 自主產品交付。必要 PR／Consumer 整合及獨立 Oracle 的 DONE 要分別確認；不是只合併 #275、#261、#245 就等於完成。
- **E-01A/B/C**：主要檢查 Goal 1 的可靠性增益、Goal 2 的成本效益；沿用 §4 現有 A Baseline / B Rules Only / C Full Governance，**三組都以同一個事前密封的評分 Oracle 判定**，不能把 Agent 可見測試與最終評分 Oracle 混為一談。Test-first 是**待 Owner 評估的實驗設計修訂候選**，不是已採納的新 B 組或第四組；需在正式凍結前另外裁決，不得並存兩套正式比較設計。排除 #279 T1–T3、F3／F4 及 V-05 已用或受污染的任務；正式樣本另選 3–5 個未受既有 Agent 修復污染的 Internal Consumer 工作，依 §4 的預註冊要求處理。
- **E-01C KEEP／SIMPLIFY／STOP／INSUFFICIENT**：對每個既有 Hook、Memory、Gate 或規則，記錄「具體改善哪個 Goal、是否使其他 Goal 變差、對比證據與成本」；無法證明額外效益時，優先 SIMPLIFY 或證據不足判定，而不是自動新增機制。安全硬性約束不得只因效益不易量化就直接移除。所有量化門檻仍依 §5 由 Owner 在 E-01B 前凍結，本節不預設百分比或成功率。
- **依賴與授權**：目標敘述不使 E-01 立即開始；先取得相應 Hook／Closeout 修正及 Consumer 採用證據，再讓 Claude 的 V-03～V-05 依各自契約 DONE，E-01 試跑／正式比較仍需各自授權。此處不改原 Slice 順序、Gate3／Gate4、任何 production 行為，也不新增權威。

## 0. Agent 交接入口：先讀這裡，別重做完成的工作

這是供後續 Agent 查閱的**計畫與驗收索引**，不是新的 Policy、Gate、Hook、常駐 Loop 或自動授權來源。**只開 Draft PR 不會讓每個 Agent 自動讀到文件**；後續任務的交接訊息需明確附上本文件路徑／PR 連結。每次執行前重新核對遠端 PR HEAD、CI、Owner 授權與 Consumer 實際狀態，不得把本文件的歷史快照當作最新事實。

- **已做過、勿原樣重跑：** #270 已合併；#272 F3 拋棄式 Agent 修 Bug／記錄／結案、F4 無關建議不做與任務收斂，已有單次正向證據；一次 Claude 真實 A→B ownership 交接已有紀錄；Solo R2／Lite 有非正式、非計數實驗資料。
- **未證明：** 真實 Internal Consumer 跨 Session 的完整產品自主交付；完整 Governance 的因果增益、一般化效果與成本效益。
- **證據天花板：** #272 的本機 Agent 審查紀錄不能冒充 GitHub Codex／人工正式 Review；#259 交接紀錄尚未合併，該次 CLI 過程沒有成功的模型自主推理；F3/F4 只證明各自受控情境。
- **工作規則：** 只針對會影響當前驗收、授權或資料完整性的缺陷做最小修正；無關的 P2/P3 一行紀錄後停止，不為了完善流程開新 Gate、Schema、Memory stream 或 PR。
- **通報原則：** 工作已達到事前 DONE 就停止。原本必要的 SessionEnd／Memory obligation 仍照既有契約處理；Task DONE 不等於 SessionEnd。

### 0.1 討論後的保存與接續判準（不以每次新增 PR 為預設）

**目的：** 讓下一個 Codex／Claude Session 找到「目前已接受的決策、完成進度、未解阻擋與下一個 Slice」，而不是把每段聊天都變成 PR。此處是本次計畫的**建議操作方式**，不創設新的規範、寫入權限或自動化保證；已有的 `SYSTEM_PROMPT.md` §6.1、`MEMORY_PROTOCOL.md`、Owner Gate 及 Repo 契約仍優先。

| 討論結果 | 保存方式 | 避免誤用 |
|---|---|---|
| 想法交流、尚未採納的建議 | 不建立 PR、不新增正式 Memory；必要時保留於原討論 | 不得標示為 Owner 已決策 |
| 已接受的架構決策、重要風險或里程碑 | 按**現有** Memory 分類、Writer 與授權，更新適當的 workflow／active task／daily 等既有紀錄；只有 PLAN 的 phase、scope、anti-goal 或既有 obligation 改變才同步 PLAN | Session-derived 紀錄須走 canonical writer；儲存／寫入不等於審查或權威提升 |
| 現有 Slice 的執行結果或下一步改變 | 更新既有 Active Task／正式 closeout 所需紀錄，附實際 commit、test／review、限制與下一步 | 不把未推送、未合併或只做本機測試的狀態寫成 DONE |
| 本計畫的**目標、Slice 順序、驗收標準或實驗設計**有實質新決議 | 只更新**同一份計畫入口**（本 Draft #273 的這份文件；若日後已合併，使用 main 的已採納文件並遵循一般變更流程） | 不因一次討論另開下一個 Draft PR；若缺少編輯／push 授權，先記錄「待更新」而不擅自修改 |
| 新的、獨立且需要正式審查的交付物 | 依實際新 scope 與 Owner／Repo 授權決定是否另開 PR | 不將每筆狀態更新包裝成新功能或新 PR |

**每次真正需要保存的最小資訊：** (1) 具體決定與決定者／接受狀態；(2) 已完成項及可查的 HEAD／證據；(3) 未完成、HOLD 或限制；(4) 下一個 Slice 與是否需要 Owner 授權。沒有改變這四項，就不為例行進度新增記錄、Commit 或 PR；有既有強制性 Memory／SessionEnd 義務時仍依法定流程履行。

**新 Session 的讀取順序：** 先讀當前 Repo 的既有記憶／工作入口；若任務涉及本計畫，交接訊息須明確提供 [Draft PR #273](https://github.com/Gavin0099/ai-governance-framework/pull/273) 或本文件路徑；接著比對 main、適用 PR 的 exact HEAD／CI／Review／Owner 授權和 Consumer 狀態，才接續第一個仍有效且已授權的 Slice。Draft PR **不會自動載入**，公開討論也不能替代受保護／未公開資料的正式來源。資料不一致時標 UNKNOWN／待對帳，不沿用過期快照或重做已驗證的工作。

**驗收關聯：** V-03／V-04 應觀察新 Session 能否找回正確的「已完成／未完成／下一步／授權邊界」；若需 Owner 重複提供先前已正確保存的決策，記為讀取／交接缺口，而不是為補漏再建立新 PR。

## 1. 公開狀態對帳（2026-11-05；仍需執行時重新核對）

| 事項 | 快照 | 下次動作 |
|---|---|---|
| #270（統一核心規則） | 已合併至 main，merge commit `04e91055` | 不重做 |
| main Post-Merge Audit | `plan_freshness` PASS，`expansion_boundary` 的 `session_envelope` transitional 期限警告導致 Audit FAIL | R-02 |
| #272（F1–F5／F-J／A-1～A-3） | **已於 2026-11-02 合併**；最終 PR HEAD `f3f18bd7`，merge commit `285911f4dbbbf6182bdf9e30ba282431143d2d32` | R-03 的交付狀態已完成（只指 #272 merge）；不能由此推定 Consumer 已採用或 V-03～V-05 完成 |
| #271（既有過度治理／Loop handoff） | Docs-only Draft，仍以舊 #270 分支為 base | 獨立對帳；不是 #272 前置條件 |
| #245／#259（Claude ownership） | #245 REVIEW HOLD、#259 交接紀錄尚未合併 | 不能視為完整的真實 Agent 接手成功 |

公開來源：[PR #270](https://github.com/Gavin0099/ai-governance-framework/pull/270)、[PR #272](https://github.com/Gavin0099/ai-governance-framework/pull/272)、[PR #271](https://github.com/Gavin0099/ai-governance-framework/pull/271)、[main CI](https://github.com/Gavin0099/ai-governance-framework/actions/runs/41380993427)、[PR #259](https://github.com/Gavin0099/ai-governance-framework/pull/259)。狀態更新必須有新證據，不能因計畫寫「預期」就改成 DONE。

## 2. Slice 順序、依賴與 DONE

| Slice | 目標與最小範圍 | DONE 證據／不得宣稱 |
|---|---|---|
| **R-02 — main Drift 收斂** | 只裁決 `session_envelope` transitional→core／移除的正確處置；先比對 ADR-0002 #258，保持 envelope=identity、非 closeout obligation；不得因修警告而默默採納未完成的 ADR | 有具體決策、相應最小測試／審查與 main Post-Merge Audit PASS；不靠改日期、延長期限或放寬規則換綠燈 |
| **R-03 — #272 正式交付** | **DELIVERED / MERGED 2026-11-02**：PR #272 最終 HEAD `f3f18bd7`，merge commit `285911f4dbbbf6182bdf9e30ba282431143d2d32`。交付後仍要分開核對 Consumer 採用／更新授權 | 只確認 GitHub 合併事實；**不把 merge 推論為 Consumer 實機／跨 Session 驗收 PASS** |
| **P-01 — 驗收計畫** | 本文件，僅 Docs-only Draft PR；固定 V/E 判準、保密、停止條件與下一步 | Draft PR 可讀、單檔 diff、無治理程式／Consumer 修改；**不阻擋 R-03** |
| **V-01 — Internal Consumer 唯讀盤點** | 在隔離工作區確認採用模式、Framework pin、dirty／未推送修改、lock 是否必要、Memory 行數與字元壓力、更新前後 `AGENTS.md` 的 32 KiB 預算、`CLAUDE.md` 是否具備收斂規則及實際載入證據；對照下方「候選更新順序」 | 本地保留原始狀態與 rollback／待授權更新計畫；未發現公開可核實的「方案甲已核准」來源，因此不宣稱已獲 Consumer 寫入授權；敏感證據僅內部保存 |
| **V-02 — 真實 Consumer F-7** | **待 Owner 針對 Consumer 採用明確核准**：依下方候選順序先切到已合併 #272 的 Framework 版本，再執行 F-7 與 F-J 受控 hash 同步；驗證正常更新、HOLD、原檔保留、重跑、失敗收據、可還原性 | #272 A-1 的「首次更新會執行舊 submodule code、可能需要一次 Owner 處置」是已知限制，不直接當產品失敗，也不得當作自動核准；正式 Consumer 版本與證據需一致，HOLD 不算成功更新 |
| **V-03／V-04／V-05 — 同一真實工作取證** | 先挑一個平台（**Claude 為候選，須在啟動前定案與核准**），使用真實模型與兩個新 Session：Session A 做產品工作並記錄未完事項；Session B 在新 Context 中接手、測試、完成並正式結案；事前凍結獨立 Oracle | 分開報告 V-03 Memory 讀寫、V-04 身分／ownership 交接、V-05 產品自主交付，三項不可互相代替；同一天兩 Session 可先驗收，跨日持久性未測須揭露 |
| **E-01A — 三組試跑** | **不使用 V-05 整合任務當樣本**；另選相同基準的任務，三組各跑一次，先驗證資料收集、評分、成本及隔離流程 | 僅證明實驗可量測；不能宣稱哪組有效或一般化 |
| **E-01B — 正式比較** | 若試跑可行且 Owner 已採納成本上限、門檻、樣本與任務封存，再以 3–5 個任務、每組 2–3 次作探索性重複比較（預估 18–45 次）；不將既有歷史樣本混入 | 全部結果含失敗、耗時／Token／人工介入與可比性限制；樣本仍偏小，不冒充統計定論 |
| **E-01C — 決策** | 依事前門檻輸出 KEEP／SIMPLIFY／STOP／INSUFFICIENT，不在看到結果後改門檻 | 若成本顯著增加而沒有可信收益，優先提減法；不自動開發新規則 |

**可並行：** R-02 及 P-01／V-01 唯讀準備；R-03（#272）已合併，不再當待執行項。R-03 不以 #271 或 P-01 完成為前置。V-02 需有 Framework 正式交付、Consumer 寫入範圍與獨立授權；後續實驗另行授權。

### 2.1 Owner 確認的後續發展主線（2026-11-14；非新 Gate／授權）

**產品終態：** Owner 交代一次真實工程任務的目標、驗收與授權邊界後，Agent 能在範圍內自行規劃、開發、測試、有限修復、保存可信進度；換 Session 後不需要 Owner 重述已保存的事實，仍能正確接續並提供可獨立查核的交付證據。只有超出授權、關鍵需求衝突、必要高風險核准或無法恢復的阻擋才詢問／HOLD。**這是待驗證的產品目標，不是宣稱現況已達成。**

**建議的下一段工作順序**（只收斂優先度；§2、§3 原有 Slice 的 DONE、依賴、Owner Gate 與平台選定程序不因此改變）：

1. **收斂 E-01B 探索性短任務量測：** 沿用 #303 的 A／B／C 定義。核對已完成的較強模型批次及其獨立審查（#304／#305），保留其執行環境差異、天花板與治理閉環未完成等限制；較輕量模型批次若經另行授權執行，完成後以批內組間比較為主，不將兩批混成單一受控實驗。短任務結果不直接觸發 KEEP／SIMPLIFY，也不為取得勝負繼續製造類似題目。
2. **優先打通一條真實 A→B 跨 Session 交付閉環：** 沿用 V-03／V-04／V-05 與已累積的證據，僅補尚未證明的環節。Session A 留下經證據支撐的進度與授權；全新 Session B 自行讀回、接續已授權工作、完成測試與合法交付；產品 Oracle、Memory 正確讀回、Ownership 與 Closeout 分別判定。Windows／Codex 可以是低準備成本的候選，但**不因此取代 §2 原列的 Claude 優先候選或自動授權 Consumer 寫入**；平台、任務及範圍在執行前由 Owner 明確定案。
3. **只修實際阻擋上述閉環的缺陷：** 先在選定的 exact Framework／Consumer 版本重現；現有 #233、#250、#299、#275 等只作為候選線索。若是 Hook Trust、Memory 誤讀、Ownership、R2 或接線問題，限定最小修復與回歸，不因 Issue 未關而推定缺陷仍存在；不批次合併 PR、不新增 Gate 或重構整套框架。
4. **觀察跨 Repo 真實工作表現：** 在既有正常開發中選取少量原本就要做的工作，觀察兩個以上 Repo 的自主接續、可信交付、人工介入及返工；一般使用觀察與嚴格 A/B/C 因果比較分開報告，不把歷史樣本事後升格。
5. **最後才做 E-01C 去留判定：** 以 Goal 1～3 的實際收益對照額外 Token／時間／人工負擔；對 Hook、Memory、Gate、規則輸出 KEEP／SIMPLIFY／STOP／INSUFFICIENT，按 §5 事前門檻與既有授權決策。硬性安全與 Owner Gate 不因短任務沒有差異而刪除。

**驗收重心改看使用結果，不看治理檔案數量：**

| 結果指標 | 需要區分的正、負面證據 |
|---|---|
| 自主完成 | 在既有授權內自行完成的工作；人工 RESCUE 與不必要停頓分開計數 |
| 跨 Session 正確接續 | 新 Session 自行找回已完成、未完成、下一步與授權界線；錯誤／遺漏記憶及 Owner 重述需求也要記 |
| 可信交付 | DONE 對得上產品測試、必要 Review、實際交付狀態與獨立驗收；部分完成不得冒稱交付 |
| 可避免錯誤與返工 | 漏驗證、錯誤決策、未授權操作、重做工作的實際事件；正確 HOLD 不算產品完成 |
| Owner 管理成本 | RESCUE、必要 APPROVAL、重複 APPROVAL、CLARIFICATION、等待／糾正時間分開記 |
| 治理淨成本 | 額外 Token／金額、牆鐘時間、Hook／Memory／Closeout 操作及維護；對照原生 Agent、Git、CI 已有能力 |

沿用現有 issue／PR／CI／Memory／執行紀錄取得證據，不為這些指標建立新儀表板、Schema、Logger、控制器或報表 Gate；沒有資料就標 **NOT MEASURED**，不臆造成功率與門檻。**同 Session 持續執行、跨 Session 接續、無人值守的排程／事件觸發是三種不同能力**：前兩者可先驗證；第三者需要具備執行能力的 Harness／Orchestrator 與另外的授權，Memory／Hooks 自身不會讓停止的 Agent 自動重啟。

**減法原則：** 優先重用模型／Harness 原生的任務執行、Checkpoint、工具權限，Git 的版本管理，CI 的測試及 PR Review。Framework 只補足經證據確認、原生能力尚未可靠解決的跨 Session 狀態、授權與獨立交付缺口；不要以「更多規則、Hook、Memory 或 PASS 次數」取代真實的自主性、可靠性與 Owner 負擔改善。這段是 Owner 接受的方向與排序，**不構成新的 Consumer 修改、真實實驗、合併或發布授權**。

### V-01／V-02 候選更新順序（定義工作步驟，不宣稱「方案甲已核准」）

1. 先在授權的隔離 Consumer 環境確認現有 submodule pin、lock、既有改動與回滾證據，核對 #272 已合併的精確 Framework 版本；**實際切換 pin 屬 Consumer 寫入，需另外取得 Owner 授權**。
2. 授權後先將 Framework submodule 切換至已包含 #272 的版本，再執行現有 F-7 受治理更新；此順序不等於可跳過現有 installer／hook 的安全限制。
3. protected `AGENTS.base.md` 若需同步 hash，只能依 #272 的 F-J 受控流程更新指定 hash；**不得藉 `adopt_governance --refresh` 重寫受保護內容**。任一來源、預期 hash 或檔案 bytes 不匹配時 **HOLD**，不能自行修正為 PASS。
4. #272 的 A-1 仍可能使首次更新走到舊 submodule code，需一次明確的 Owner 處置／授權；不能把此處置視為既得權限，也不能將正確 HOLD 誤判為成功更新。
5. 以 F-7 receipt、原檔保存、重跑／失敗與 rollback 證據核對結果；未完成則如實記 PARTIAL／HOLD。

**授權狀態：** #272 的合併可由 GitHub 證實，**但公開資料沒有提供「方案甲」對某 Internal Consumer 的可核實採納與寫入核准**。本段只是將 #273 原本未定義的操作順序明文化，不創設核准來源；在 Owner 另行核准前只允許既有授權範圍內的唯讀準備。

## 3. V-03～V-05：事前凍結自主交付驗收

1. **工作選擇：** 使用真正有價值、原本就要做的 Internal Consumer 產品任務；不捏造 Bug，不為驗收硬造新需求；公開文件不得揭露任務內容。
2. **事前凍結：** Owner 在 Agent 開始前固定任務、允許／禁止範圍、初始 commit、Oracle（預期輸出／測試及版本）、交接邊界與失敗條件。Agent 自己新增的測試是研發證據，不能取代外部 Oracle。
3. **執行：** 事前授權內由 Agent 自己分析、修改、測試、修正、記錄、接續與結案；Agent 可以做自我 Review，但**自我 Review 不能當獨立驗收**。另一 Agent Review 仍須綁定客觀驗收依據；Owner 或獨立執行的事前固定測試負責最終結果。
4. **介入類別分開記：** `RESCUE`（人類提供卡關解法）、`APPROVAL`（需要人的核准）、`CLARIFICATION`（需求澄清）。每類記次數與耗時，全部算互動成本；既有 Owner Gate 下的必要核准不算 AI 修復能力失敗，重複索取原已核准的同一操作則是可觀察摩擦。
5. **三項判定分開：** V-03 要有真實 Memory 寫入、身分綁定與新 Session 精確讀回；V-04 要有兩個 Session 的正式交接與授權隔離；V-05 要有產品獨立 Oracle PASS、在原授權範圍內無 `RESCUE`、記錄完整及合法 Closeout。
6. **停止／失敗：** 禁止動作正確 HOLD 是安全證據，**不是產品交付成功**。未取得核准、不可恢復狀態、超範圍與證據不足應回報 PARTIAL／HOLD／NOT_ASSESSABLE，不能填作 DONE。
7. **排除實驗：** 本整合工作是為了驗證 Full Governance 的交接設計，**不得拿來當 E-01 的 A/B/C 比較樣本**。

**跨 Harness 驗證：** 跨平台驗證應區分 Harness 原生能力與 AI Governance 的貢獻。先完成 Claude 的 V-03～V-05，再使用相同驗收標準評估 Codex／Copilot；只有觀察到具體的整合缺口，才考慮新增修正工作。跨 Harness 驗證不得混入 E-01 的同 Harness 治理效益對照。

## 4. E-01：三組可比較的治理效益研究

| 組 | 精確處置 | 想回答的問題 |
|---|---|---|
| **A — Baseline** | 相同 Agent／模型／Harness／工具／產品授權與基本安全限制；無 Governance 專屬文字、Hook、Gate、Memory 記錄；必須用真正乾淨的 disposable repo，不能留下原有治理檔 | 未加入框架時的任務能力與成本 |
| **B — Rules Only** | A 的條件加上**版本凍結的精簡 Core Rules 本文**：`governance/AGENT_CORE_RULES.md` 的 `agent-core-rules BEGIN/END` 內容（記錄 exact SHA／digest）。**不是整份 AGENTS.md，也不帶 Hook、Gate、Governance Memory** | 單靠規則文字有多少效果與 Token 成本 |
| **C — Full Governance** | 同一份精簡 Core Rules，加上完整已核准的 Governance Hook／Gate／Memory／Evidence 流程；如有額外必要指令，記錄實際投入內容及 token | 完整執行治理相對 B 的額外淨效果（不把全部差異錯歸因於 Hook） |

- **公平性：** 共同固定模型、Harness、工具能力、安全與權限、任務內容、開始狀態、可用時間、評分 Oracle；獨立隔離各次執行，沒有跨組資料污染。每次重設 clean workspace 和 Memory 起點；A/B 不能讀到舊 Governance 訊號。若真實生產規則不允許停用治理，只能在經授權 disposable 環境做 A/B，不能繞過生產保護。
- **任務來源：** E-01A 的試跑任務與 V-05 不同；正式比較另行預註冊多個具體任務，包含失敗與無效試次；如只限一種 Consumer 類型，結論只適用該類型，不宣稱跨 Repo 通用。
- **計數：** E-01A 每組一次是量測管線試跑，不能宣稱療效；E-01B 要先凍結 3–5 個任務 × 每組 2–3 次、順序／隨機化、所有模型與工具版本、成本預算、上限與停止閾值。這是探索性設計，不是統計效力保證。
- **獨立評分：** Oracle／預期結果在跑之前封存；評分人盡可能不知道 A/B/C 身分。記錄產品成功、危險違規、誤擋、返工、人工介入三類、總時間、Token／金額（取得不到就標 UNKNOWN），以及歸因與不可比原因。
- **與 Skill Gate 分離：** 此處 E-01 是整體治理效果研究，不是既有四臂 Engineering Skill 計畫的正式 Gate 3／Gate 4；不可把歷史 Solo R2／Lite 非計數結果視為本實驗有效樣本。

## 5. 停止與決策規則（實驗前採納門檻）

| 判定 | 適用條件 |
|---|---|
| **KEEP** | 有可重現的產品／安全／人工負擔收益，且符合事前凍結的成本門檻 |
| **SIMPLIFY** | 對比未見可信的品質或救援改善，治理卻持續產生已超過事前可接受值的時間／Token／互動成本；優先減少無效流程 |
| **STOP** | 安全越界、偽造或無法核實的成果、污染不可恢復、超預算、未授權高風險操作、不可比的實驗條件；停止受影響的實驗或部署，不自動追加架構 |
| **INSUFFICIENT** | 樣本／成本／獨立證據不足，或數據不穩定；不強行作出有效或無效宣稱 |

**必須由 Owner 在 E-01B 前填定而非事後選擇：** 產品品質／安全最低條件、可容忍的 Token 與時間增幅、人工救援／核准／澄清的判讀門檻、每組次數、總成本預算與停損。此 Proposal **不擅自設定 X%**。STOP/IMPASSE 並非自動授權增加測試、重構或新 Gate。

## 6. 公開資料最小化與 Non-Claims

- 此公共 Proposal 只稱 **Internal Consumer**。不得含任何私有 Git 位置或連結、公司／客戶名稱、內部 repo／分支名稱、內部檔案路徑、產品特徵、程式碼片段、截圖、測試 fixture 或可推知內部細節的原始 evidence。
- 真實 Consumer 的 Task、Oracle、精確 SHA、授權、日志與成本資料只留在合規的內部保存處；公開版僅可發佈匿名化、經另行授權的結果彙總。
- 本 PR **不修改** `PLAN.md`、`memory/`、Framework Runtime、Hooks、Gate、Schema、CI、Consumer、protected hash；不做 Push 到 Consumer、不開真實實驗、不 Merge，也不授予任何後續寫入或高風險操作許可。
- 文件存在 **不等於** Agent 已讀取、Policy 已採納、CI 已通過、獨立 Review 已通過、Memory 自主交接已成功，也不等於 Governance 有效。

## 7. 相關既有文件（只引用，不複製治理條文）

- [既有 2026-10-29 instruction architecture／bounded loop proposal](2026-10-29-instruction-architecture-autonomous-loop.md)
- [#271 過度治理與 delivery-first handoff（仍為獨立 Draft）](https://github.com/Gavin0099/ai-governance-framework/pull/271)
- [Engineering Skill four-arm study 與既有 Gate 0–5](../governance/evidence-backed-engineering-skill-program-2026-07-24.md)
- [ADR-0002 提案／#258：Session Envelope 是 Identity，不是 Closeout Obligation](https://github.com/Gavin0099/ai-governance-framework/pull/258)
- [已合併 #270](https://github.com/Gavin0099/ai-governance-framework/pull/270)、[已合併 #272](https://github.com/Gavin0099/ai-governance-framework/pull/272)

**下個 Agent 的第一步：** 重新核對 R-02 的 main audit、#272 已合併事實及 Consumer 是否具備獨立更新授權；只繼續第一個有真實缺口且已授權的 Slice。P-01／V-01 可並行唯讀準備。不要因為看見本文件就重做已完成的 F3/F4、開新治理系統，或自行觸發 Consumer 寫入與 Merge。
