# Session Closeout Artifact Schema

> Version: 1.0
> Artifact path: `artifacts/session-closeout.txt`
> Written by: AI agent at end of session
> Consumed by: `governance_tools/session_end_hook.py` via stop hook

---

## 目的

這份 artifact 是 AI agent 在 session 結束時交給 governance runtime 的 **closeout input**。

它不是 truth source，而是 candidate artifact，必須接受 runtime 檢查。  
真正的 authoritative verdict / trace artifact 由 governance runtime（`session_end_hook -> session_end`）產生。

AI 的責任是提供輸入；runtime 的責任是決定哪些內容可以被正式記錄。

---

## 必填欄位

每個欄位都必須存在。即使沒有內容，也要明確填 `NONE` 或 `NO_UPDATE`，不能省略。

```text
TASK_INTENT: <一句話描述本次 session 的目標>
WORK_COMPLETED: <實際完成的工作，只能寫可驗證內容，不寫敘事感想>
FILES_TOUCHED: <本次改動檔案，以逗號分隔；若沒有則寫 NONE>
CHECKS_RUN: <本次實際執行的測試 / smoke / validation；若沒有則寫 NONE>
OPEN_RISKS: <尚未解決的風險；若沒有則寫 NONE>
NOT_DONE: <本次沒完成的事；若沒有則寫 NONE>
RECOMMENDED_MEMORY_UPDATE: <建議更新哪個 memory 檔以及原因；若不更新則寫 NO_UPDATE>
```

---

## 欄位約束

| Field | Constraint |
|-------|-----------|
| `TASK_INTENT` | 必填，不可為空 |
| `WORK_COMPLETED` | 必填，不可為空 |
| `FILES_TOUCHED` | 必填，可為 `NONE` |
| `CHECKS_RUN` | 必填，可為 `NONE` |
| `OPEN_RISKS` | 必填，可為 `NONE` |
| `NOT_DONE` | 必填，可為 `NONE` |
| `RECOMMENDED_MEMORY_UPDATE` | 必填，可為 `NO_UPDATE` |

以下情況會被視為 **insufficient**：
- 任一必填欄位缺失
- `WORK_COMPLETED` 雖存在，但只有模糊描述，例如「做了一些改善」「更新了東西」
- `CHECKS_RUN` 不等於 `NONE`，但沒有列出明確 command 或 check 名稱

以下情況會被視為 **missing**：
- session 結束時根本找不到 closeout 檔案

---

## 範例：正常 session

```text
TASK_INTENT: implement session_end_hook.py for automatic memory closeout
WORK_COMPLETED: wrote governance_tools/session_end_hook.py; updated AGENTS.base.md session closeout section; verified with quickstart smoke ok=True
FILES_TOUCHED: governance_tools/session_end_hook.py, baselines/repo-min/AGENTS.base.md
CHECKS_RUN: python -m governance_tools.quickstart_smoke (ok=True); python -m governance_tools.session_end_hook --project-root . (ok=True, promoted=True)
OPEN_RISKS: stop hook not yet configured in any repo; AGENTS.base.md change not yet re-adopted by existing repos
NOT_DONE: .claude/settings.json stop hook template; checklist F9 section
RECOMMENDED_MEMORY_UPDATE: memory/active_task - update current task to session_end_hook complete, stop hook pending
```

## 範例：被阻塞的 session

```text
TASK_INTENT: fix F8 UTF-8 crash in external_project_facts_intake.py
WORK_COMPLETED: identified root cause at line 47 (missing errors= parameter); applied fix
FILES_TOUCHED: governance_tools/external_project_facts_intake.py
CHECKS_RUN: python -m governance_tools.external_project_facts_intake --repo D:\\meiandraybook\\artifacts\\framework-checklist-scratch (ok, exit 0)
OPEN_RISKS: fix not tested against the actual non-UTF-8 file that caused the original crash
NOT_DONE: end-to-end test on real non-UTF-8 repo
RECOMMENDED_MEMORY_UPDATE: NO_UPDATE - risk still open, not a stable state to record
```

## 範例：沒有實質進展的 session

```text
TASK_INTENT: investigate memory update failure in external repos
WORK_COMPLETED: NONE - session used for analysis only, no code changes
FILES_TOUCHED: NONE
CHECKS_RUN: NONE
OPEN_RISKS: memory pipeline gap confirmed; session_end never called in external repos
NOT_DONE: actual fix - deferred to next session
RECOMMENDED_MEMORY_UPDATE: memory/active_task - add note: memory pipeline gap is confirmed root cause, fix is session_end_hook
```

---

## 四層分類

runtime 會對 closeout 做四層獨立分類。  
所有 layer 都會執行，不會因前面失敗就跳過。整體 `closeout_status` 取最差的一層。

| Layer | Values | 檢查內容 |
|-------|--------|----------|
| `presence` | `present` / `missing` | 檔案是否存在且可讀 |
| `schema_validity` | `valid` / `invalid` | 七個必填欄位是否都在 |
| `content_sufficiency` | `sufficient` / `insufficient` | 內容是否具體、非空泛 |
| `evidence_consistency` | `consistent` / `inconsistent` / `unchecked` | 宣稱的檔案 / checks 是否能和可觀測訊號互相對上 |

**`valid` 不等於只有 schema_valid。**  
如果七欄都填了，但內容全部是模糊句，依然屬於 `content_insufficient`，不是 `valid`。

### Content sufficiency 規則

若 `WORK_COMPLETED` 或 `CHECKS_RUN` 只包含模糊語句，例如：
- made improvements
- worked on things
- updated files
- ran checks

就應判為 insufficient。  
內容必須能提供具體、可驗證的 claim。

`TASK_INTENT` 也必須夠具體，不能只有一兩個泛稱字。

### Evidence consistency 範圍

evidence consistency 是 **best-effort**。  
它只能根據 filesystem 與現有 artifact 檢查，不會主動再執行 command。

目前檢查重點：
- `FILES_TOUCHED` 若不為 `NONE`，每個檔案都應存在於專案中
- `CHECKS_RUN` 若宣稱執行 governance tools，會 spot-check 對應 artifact 目錄

**通過 evidence consistency 不代表 claim 一定為真。**  
它只表示沒有找到可檢出的不一致，仍然無法防止偽造結果或幻覺描述。

---

## Runtime 會怎麼使用這份 artifact

| Overall closeout_status | Runtime 行為 |
|------------------------|--------------|
| `valid` | `session_end` 以完整內容運行；memory 是否更新由 promotion policy 決定 |
| `closeout_missing` | `session_end` 仍會運行，但沒有 closeout 內容；memory 不更新 |
| `schema_invalid` | `session_end` 仍會運行，但記錄 schema_invalid；memory 不更新 |
| `content_insufficient` | `session_end` 仍會運行，但記錄 content_insufficient；memory 不更新 |
| `evidence_inconsistent` | `session_end` 仍會運行，但記錄 evidence_inconsistent；memory 不更新 |

stop hook 在 session end 時**一定會跑**。  
closeout 退化不會中止 hook，而是生成一份明確記錄缺口的 degraded verdict。
