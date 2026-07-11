# AI Governance 新手導入指南

這份指南把既有導入文件整理成新手可走的最小路徑。它不取代
F-7、External Repo Onboarding SOP 或 consuming-repo adoption checklist；衝突
時以那些文件為準。

適用範圍：你正在導入或更新一個會由團隊持續修改的 consuming repo。
它不表示導入已完成，也不取代 owner 對 domain、risk tier 或 repository
topology 的決定。

## 先選對路徑

先以 read-only 方式判斷 repo 的治理拓撲：

- **submodule consumer**：使用 F-7 更新流程與 External Repo Onboarding SOP。
- **copy-based / starter-pack**：只可宣稱 audit 或最小骨架；不可因此宣稱
  runtime self-contained 或完整導入。
- **不確定**：先停在分類，不要直接執行導入或更新。

參考：`docs/ADOPTION_MODEL.md`、
`governance/fleet/external_repo_onboarding_sop.md`。

## 六個新手問題

### 1. 我怎麼知道是否真的完整導入？

不要以「有 submodule」、「指令 exit 0」或「table 看起來綠色」單獨判定。

對 submodule consumer，F-7 的 `final_status=full_update_completed` 只能在下列
各 stage 都是合格狀態時使用：framework pointer、repo-local instruction、
memory writer coverage、hook / validator coverage、existing memory
normalization，以及 adoption summary 的人類可讀 relay。

對初次導入，依 SOP 逐步保留：分類、gap scan、owner 的 domain/risk 決定、
memory skeleton、hook 實際觸發、runtime smoke、reviewer handoff。任何一項
missing、blocked、needed 或 not_verified，都不是完整完成。

參考：`governance/F7_FULL_UPDATE.md`、
`governance/fleet/external_repo_onboarding_sop.md`。

### 2. F-7 table 要怎麼讀？

先看 `final_status`，再看每個 stage，而不是只看其中一格：

| 讀到的狀態 | 意思 | 下一步 |
| --- | --- | --- |
| `full_update_completed` | 每個必需 stage 都已符合 F-7 合格條件。 | 保留 report；這仍不等於 runtime correctness 或全域合規。 |
| `already_current` | 已由受管流程驗證當前狀態。 | 確認 report 中的 stage 沒有 `not_verified`。 |
| `partially_updated` | 有些更新做了，但至少一個必需 stage 不合格或未驗。 | 看該 stage 的 `missing`、`needed`、`blocked` 或 `not_verified`。 |
| `blocked` / `not_verified` | 流程無法完成或證據不足。 | 不要自行補 claim；先按錯誤類型排查或找 owner。 |

`governance_maturity_summary` 與 human-readable adoption summary 是讓人理解
可見導入面；它們不證明 runtime enforcement、語義正確性或 release readiness。

參考：`governance/F7_FULL_UPDATE.md`。

### 3. 之後要如何更新 AI Governance？

只有已註冊且初始化的 submodule consumer 才能走 F-7 更新。先 dry-run，接受
結果後才 apply；F-7 不會自動 push。

```powershell
scripts\update-governance-submodule.ps1 `
  -Repo <consumer-repo-path> `
  -SubmodulePath ai-governance-framework `
  -Format json
```

更新後依 F-7 report 確認各 stage，並只在 owner 明確授權後另行 push。若 repo
不是 submodule consumer、nested checkout 不乾淨，或已有 staged work，先停止並
做分類／清理決策；不要把手動 checkout 或 lock edit 說成完整 F-7 更新。

參考：`docs/fleet/f7-governance-submodule-updater.md`、
`governance/F7_FULL_UPDATE.md`。

### 4. 我怎麼知道哪些功能已啟用？

把 F-7 table 的每個 stage 當成「已驗證的 surface」，不是功能總開關：

- `repo_local_instruction`：consumer 的 instruction surfaces 是否已刷新。
- `memory_writer_coverage`：canonical memory writer 路由是否有覆蓋。
- `hook_validator_enforcement`：hook / validator coverage 是否驗證或更新。
- `existing_memory_normalization`：歷史 memory 狀態是否已處理或不適用。
- `governance_maturity_summary`：可讀的 adoption surface 摘要是否產生。

要知道 runtime path 是否真的可用，仍需按 checklist 跑 drift/readiness、runtime
smoke 與至少一次 `pre_task_check`。單一 stage 合格不代表其他 capability 已啟用。

參考：`governance/F7_FULL_UPDATE.md`、
`docs/consuming-repo-adoption-checklist.md`。

### 5. 出錯時怎麼排查？

依問題分類，從最小檢查開始：

| 現象 | 先做什麼 | 不要做什麼 |
| --- | --- | --- |
| 不確定 adoption 類型 | 依 adoption model 做 read-only classification。 | 不要把 copy-based repo 直接當 submodule consumer。 |
| 缺檔或 memory 顯示 partial | 跑 onboarding gap scan / readiness，讀出明確 gap。 | 不要只補檔就宣稱完成。 |
| hooks 看似存在但不確定有沒有生效 | 依 SOP 驗 real commit/push trigger 與 hook validator。 | 不要只靠檔案存在判定。 |
| runtime 行為不清楚 | 跑 runtime smoke，再跑最小 `pre_task_check`。 | 不要用 README 或 clean build 取代 runtime evidence。 |
| F-7 顯示 partial、blocked 或 not_verified | 找出該 stage 與 report 的原因。 | 不要把手動修正說成 full update。 |

參考：`governance/fleet/external_repo_onboarding_sop.md`、
`docs/consuming-repo-adoption-checklist.md`。

### 6. 什麼時候必須找 owner？

以下情況不要由 agent 或新手自行猜測：

- 決定 consumer role、domain 或 risk tier；
- repo topology 不清楚，或要從 copy-based 改為 submodule consumer；
- F-7 出現 `blocked`、`not_verified`、`needed` 或 `missing`；
- 需要選擇 framework pin、允許 detached target checkout、處置 dirty/staged work；
- 要新增／改變 hook、gate policy、runtime rules、CI 或權限；
- 外部 repo 的產品或領域規則需要補充（例如 C# / Avalonia 的專案規則）。

owner 決定後，才執行被授權的下一個最小 slice，並保留相應 evidence。

## 最小導入順序

1. 分類 consumer topology。
2. 按 SOP 跑 gap scan，讓缺口明確。
3. 由 owner 決定 domain 與 risk。
4. 安裝／驗證 memory、hooks、runtime smoke 與 reviewer handoff。
5. 之後更新才走 F-7：先 dry-run，再 apply，最後讀完整 table。

## Claim Boundary

完成上述步驟所支持的是「在記錄的 commit 上，有對應的 onboarding 或 F-7
evidence」。它不自動證明：完整治理、所有 agent 行為受控、domain correctness、
runtime correctness、CI enforcement 或法規合規。

## Source Documents

- `governance/F7_FULL_UPDATE.md`
- `governance/fleet/external_repo_onboarding_sop.md`
- `docs/consuming-repo-adoption-checklist.md`
- `docs/fleet/f7-governance-submodule-updater.md`
- `docs/ADOPTION_MODEL.md`
