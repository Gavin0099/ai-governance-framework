# Claude Code session lifecycle：接線盤點與最小修復規格（2026-10-22）

狀態：**規格草案，未實作**。本文件只做唯讀盤點與修復規格；不修改任何 hook 設定、不重裝 consumer、不啟動付費 Claude session。每一項實作與驗收都需 owner 另行授權。

## 目標（只有一個）

讓**一次真正的 Claude Code 工作階段**可以可靠地：開始（有可信身分）→ 保存（摘要屬於這個 session／worktree）→ 結束（正式結案只發生一次，失敗可查）→ 下一次開始時讀得回來。

不在目標內：新增治理規則、改 memory 架構、處理 Copilot／Codex。

## 一、實測證據（本 repo，唯讀）

來源：在 framework repo 本身執行的 Claude Code session `6b0cedb0-c542-43da-aa73-c35f30b59ecf`，2026-10-21T05:53Z → 2026-10-22T07:58Z。

| 觀察 | 數值 | 位置 |
|---|---|---|
| 已安裝的 hook | 只有 `Stop` → `session_closeout_entry.py --project-root ...; exit 0` | `.claude/settings.json` |
| 單一 session 的 closeout 次數 | **44**（每次回答一次） | `artifacts/runtime/closeout-receipts/`、`canonical-audit-log.jsonl` |
| `agent_id` / `trigger_mode` | 44 次皆 `unknown` | receipt；CLI 預設值 `session_closeout_entry.py:684-694` |
| exit code | 44 次皆 0（`; exit 0` 吞掉失敗） | receipt |
| closeout 產物狀態 | 44 次 `stale`；canonical closeout 逐回合覆寫，最後為 `missing` | audit log、`artifacts/runtime/closeouts/<sid>.json` |
| session 信封 | **不存在**（無 SessionStart） | `artifacts/runtime/sessions/` |
| 正式摘要保存 | 無法使用（`prepare_closeout_candidate` 需要 v1.1 root-bound 信封） | `shared_closeout_ownership._identity` |

`E:\BackUp\meiandraybook` 本機副本：hook 指向不存在的 `D:/meiandraybook/...`，且 `2>/dev/null || true` 隱藏錯誤 → 本機靜默失效（0 張 receipt）。這只證明本機副本接線無效，不否定其他機器 2026-07-22 的觸發證據。

## 二、框架現況（`main@de9beeba`）

- `governance_tools/manage_agent_closeout.py` 的 `ClaudeAdapter`：
  - docstring 與說明寫「Stop hook that fires at session end」「Fires automatically at every session end」——**與平台語意不符**。
  - 目前 installer 產生的命令已改善：帶 `--format json --agent-id claude --trigger-mode native_hook`，失敗時印出原因並 exit 1（不是 2，所以不會逼 Claude 繼續）。但仍綁在 `Stop`。
  - 只安裝 `Stop`；不安裝 `SessionStart`／`SessionEnd`。
  - 本 repo 與 meiandraybook 的實際安裝都是舊格式，從未用新 installer 重裝。
- `runtime_hooks/adapters/claude_code/{pre_task,post_task,normalize_event}.py` 存在，但**沒有任何 installer 把它們接到 Claude hooks**（只有 census 文件提到）。
- root-bound 身分（`_ROOT_BOUND_SOURCE_BY_PROVIDER`）目前只有 `codex`、`github-copilot-vscode`；Claude 沒有。

## 三、平台事實（Claude Code 官方 hooks 文件）

- `Stop`：「When Claude finishes responding」——**每回合**。exit 2 會阻止停止、讓對話繼續（最多連續 8 次）。input 含 `stop_hook_active`、`last_assistant_message`。
- `SessionStart`：開始或恢復 session 時。`source` ∈ `startup`／`resume`／`clear`／`compact`／`fork`。可用 `additionalContext`（或純文字 stdout）把內容注入 Claude 的 context。
- `SessionEnd`：reason ∈ `clear`／`resume`／`logout`／`prompt_input_exit`／`other`；**不能阻止結束**；所有 SessionEnd hooks **共用 1.5 秒預算**，設定較長的 per-hook `timeout` 可提高到最多 60 秒。
- command hook 預設 timeout 600 秒（SessionEnd 除外，受上述預算限制）。

## 四、最小修復規格

### 4.1 SessionStart：建立可信身分（需 owner 核准，屬信任結構變更）

- 新增 Claude SessionStart hook，走既有 `establish_bound_session`（與 Codex／VS Code 同一實作），provider 維持真實身分 `claude`，source label `claude_session_start`。
- 安裝根目錄錨點：installer 把 `--project-root` 寫進 hook 命令（同 Codex），payload `cwd` 必須等於該根目錄。
- `resume`／`compact` 需既存身分；`startup`／`clear` 建新身分；`fork` 視為新 session（新 `session_id`），不繼承舊身分。
- 只用 `additionalContext` 注入**上一次已結案 session 的摘要指標**（有大小上限、只讀），作為「下次讀回」的正式管道；不注入整份 memory。

### 4.2 Stop：降為觀察，不再結案

- `Stop` 不執行 canonical closeout、不消費摘要、不寫 daily memory。
- 可保留輕量回合紀錄（例如：回合時間、`stop_hook_active`），明確標示 `not_a_session_end`。
- 永遠不回傳 exit 2（避免逼 Claude 繼續）；錯誤寫入可查的紀錄，而不是 `; exit 0` 或 `|| true`。

### 4.3 SessionEnd：在預算內完成「已準備好的」結案

- SessionEnd 只做有界工作：消費**已由 `prepare_closeout_candidate` 保存**的摘要、寫 completion marker。不得在 SessionEnd 內做摘要生成或大範圍掃描。
- hook 設定明確 `timeout`（建議 ≤ 30 秒，須在 60 秒上限內；具體值由 owner 決定）。
- 未完成（逾時、被中止、失敗）時留下 `closeout_incomplete` 標記與原因；**下一次 SessionStart** 偵測到未完成的前一個 session 時，回報並補完或明確標示無法補完——因為 SessionEnd 可能根本沒跑（當機、強制關閉）。
- 結果必須可查：不得以 exit code 0 掩蓋失敗；receipt 記錄 `agent_id=claude`、`trigger_mode=session_end`。

### 4.4 Installer 與文件

- `ClaudeAdapter` 安裝 SessionStart + SessionEnd（+ 降級後的 Stop 或移除 Stop，由 owner 決定），修正 docstring／說明。
- 驗證器（`verify`）能辨識舊格式並回報需要重裝；**重裝各 repo 的 hook 是獨立的授權動作**。

## 五、驗收（需付費 session，另行授權）

在一個拋棄式 consumer 以新 installer 安裝後，執行兩次真實 Claude Code session：

1. 第一次：SessionStart 建立 v1.1 身分 → 多回合工作中 Stop 不產生 closeout → `prepare_closeout_candidate` 保存摘要 → 結束時 SessionEnd 完成結案，receipt 為 `agent_id=claude`、`trigger_mode=session_end`、一次。
2. 第二次（`resume` 或新 session）：SessionStart 的 `additionalContext` 帶出上一次摘要指標；若上一次 SessionEnd 未完成，可看到明確的未完成狀態。
3. 負向：故意讓 SessionEnd 逾時／失敗，確認留下可查結果且下一次 SessionStart 會回報。

## 六、需要 owner 決定的事

1. 是否核准 `claude` 成為 root-bound provider（信任結構變更）。
2. `Stop` 要保留為輕量觀察，還是完全移除。
3. SessionEnd 的 `timeout` 值（≤ 60 秒）。
4. SessionStart 注入讀回內容的範圍與大小上限。
5. 何時重裝本 repo 與其他 consumer 的 hook；何時執行付費驗收 session。
