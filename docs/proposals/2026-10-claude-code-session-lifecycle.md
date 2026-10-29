# Claude Code session lifecycle：接線盤點與最小修復規格（2026-10-22，修訂 1）

狀態：**規格草案，未實作**。本文件只做唯讀盤點與修復規格；不修改任何 hook 設定、不重裝 consumer、不啟動付費 Claude session。每一項實作與驗收都需 owner 另行授權。

修訂 1（#231 審查後）：SessionEnd 改為**可恢復的 checkpoint**，不再寫不可逆的 completion marker；`trigger_mode` 沿用既有的 `native_hook`；明定誰負責預先保存摘要；讀回改為附上經驗證的摘要內容；`cwd` 改為比對 Git worktree root；補上 resume／fork 與「SessionEnd 沒跑」的語意；第六節列出審查建議的預設值。

## 目標（第一階段，只有一個）

**Claude 不會因為退出程式而忘記進度，也不會把未完成的工作誤認為完成。**

具體來說，一次真正的 Claude Code 工作階段可以：開始（有可信身分）→ 保存進度（摘要屬於這個 session／worktree）→ 退出時留下可恢復的 checkpoint → 之後 `resume` 或新 session 時讀得回最新進度。

不在第一階段：每次退出都做不可逆的正式結案、新增治理規則、改 memory 架構、處理 Copilot／Codex。

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

## 二、框架現況（`main`，引用檔案自 `de9beeba` 起未變）

- `governance_tools/manage_agent_closeout.py` 的 `ClaudeAdapter`：
  - docstring 與說明寫「Stop hook that fires at session end」「Fires automatically at every session end」——**與平台語意不符**。
  - 目前 installer 產生的命令已改善：帶 `--format json --agent-id claude --trigger-mode native_hook`，失敗時印出原因並 exit 1（不是 2，所以不會逼 Claude 繼續）。但仍綁在 `Stop`。
  - 只安裝 `Stop`；不安裝 `SessionStart`／`SessionEnd`。
  - 本 repo 與 meiandraybook 的實際安裝都是舊格式，從未用新 installer 重裝。
- `runtime_hooks/adapters/claude_code/{pre_task,post_task,normalize_event}.py` 存在，但**沒有任何 installer 把它們接到 Claude hooks**（只有 census 文件提到）。
- root-bound 身分（`_ROOT_BOUND_SOURCE_BY_PROVIDER`）目前只有 `codex`、`github-copilot-vscode`；Claude 沒有。
- `session_closeout_entry.py:51` 的 `ALLOWED_TRIGGER_MODES` = `native_hook`、`manual_fallback`、`wrapper`、`synthetic_smoke`、`unknown`（receipt schema 同）。
- 一旦寫入 completion marker，`prepare_closeout_candidate._preflight_session` 會以 `consumed session cannot prepare` 拒絕同一 session 的後續摘要。

## 三、平台事實（Claude Code 官方 hooks 文件）

- `Stop`：「When Claude finishes responding」——**每回合**。exit 2 會阻止停止、讓對話繼續（最多連續 8 次）。input 含 `stop_hook_active`、`last_assistant_message`。
- `SessionStart`：開始或恢復 session 時。`source` ∈ `startup`／`resume`／`clear`／`compact`／`fork`（`fork` = 從既有 session 分出的新 session，例如 `--fork-session`、`/branch`）。「SessionStart hooks run again on resume with `source` set to `"resume"`」。可用 `additionalContext`（或純文字 stdout）把內容注入 Claude 的 context。
- `SessionEnd`：reason ∈ `clear`／`resume`（以互動式 `/resume` 切換 session）／`logout`／`prompt_input_exit`／`other`；**不能阻止結束**，JSON 輸出會被丟棄。預設 timeout **1.5 秒**；per-hook `timeout` 可把整體預算提高到最多 **60 秒**，或以 `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` 明確覆寫。
- 平台**不保證** SessionEnd 一定執行（例如程序被強制終止）。
- 審查者另指出：v2.1.214 以前的 Claude Code 可能把 `fork` 回報成 `resume`。**目前官方頁面未找到此說明**，列為未驗證，設計上以保守方式處理（見 4.1）。

## 四、最小修復規格

### 4.1 SessionStart：建立可信身分（需 owner 核准，屬信任結構變更）

- 新增 Claude SessionStart hook，走既有 `establish_bound_session`（與 Codex／VS Code 同一實作），provider 維持真實身分 `claude`，source label `claude_session_start`；不可接管其他 provider 的身分（沿用既有檢查）。
- **工作目錄**：installer 把 `--project-root`（Git worktree root）寫進 hook 命令，比照 Codex 比對 `git toplevel(cwd)` 與該 root——Claude 可以從子目錄啟動，不要求路徑字串完全相同。
- `startup`／`clear`／`fork`：建立新身分。
- `resume`／`compact`：需既存身分，沿用既有身分，不重建。
- `resume` 但**沒有**既存身分（可能是舊版把 `fork` 回報成 `resume`，也可能是不可信的 payload）：**不憑空建立**，此 session 維持未綁定並回報 `UNKNOWN`；不推定為任何既有 session。
- 讀回（4.4）也在這裡注入。

### 4.2 Stop：移除治理結案

- 移除 governance 的 Stop closeout hook：`Stop` 不執行 closeout、不消費摘要、不寫 daily memory。
- 使用者自訂的非治理 Stop hook 保持不動。
- 不新增 Stop 的替代紀錄；若日後需要回合觀察，另案處理，且永遠不得回傳 exit 2。

### 4.3 摘要的保存責任（MVP）

- **由 Claude 在工作過程中呼叫既有的 `prepare_closeout_candidate`** 保存摘要（里程碑時、退出前）；這是 agent 的明確動作，由 agent contract（`CLAUDE.md`）要求。
- MVP **不宣稱**自動生成摘要；hook 不負責寫摘要內容。
- 沒有保存過摘要的 session，checkpoint 會明確標示「無摘要」，不以空內容冒充進度。

### 4.4 SessionEnd：可恢復的 checkpoint，不是正式結案

- SessionEnd 只做有界的輕量工作：記錄「此 session 在此時退出」以及**目前最新有效摘要**的參照（candidate 識別與雜湊）。
- SessionEnd **不寫 completion marker**、不消費摘要；因此 `claude --resume` 之後仍可繼續 `prepare_closeout_candidate` 與再次退出。
- 正式、不可逆的結案維持**明確的完成操作**（例如手動執行 formal closeout），不由退出觸發。若日後要「每次退出都正式結案、恢復後再結案」，需另行設計 generation／execution identity，不在本階段。
- hook 設定明確 `timeout`（審查建議 5 秒，見第六節）；不得在退出時做大型掃描。
- receipt 沿用 `trigger_mode=native_hook`、`agent_id=claude`，另以 payload 的 `hook_event_name=SessionEnd` 與 `reason` 作為實際來源證據；**不擴大 receipt schema**。
- 結果必須可查：失敗不得以 exit 0 掩蓋（SessionEnd 無法阻止結束，但要留下紀錄）。

### 4.5 「SessionEnd 沒跑」與下一次讀回

- 下一次 SessionStart（`resume` 或新 session）**不依賴** SessionEnd 有沒有跑，而是從同一 worktree 的 envelope、最新有效 candidate、checkpoint、completion marker 推導前一次的狀態：
  - 有 checkpoint：上次正常退出。
  - 有 candidate 但無 checkpoint：上次可能沒跑到 SessionEnd，標示為「未確認退出」。
  - 都沒有或資料矛盾：`UNKNOWN`，**不推定成功**。
- 讀回內容透過 `additionalContext` 注入：**最多 800 字的經驗證摘要內容**（來自同一 worktree 最近有效的 candidate／checkpoint，內容雜湊相符才使用），加上狀態與可追溯的來源路徑。
- 注入內容明確標示為**資料、不是指令**；不載入整份 memory，也不注入其他 worktree 或其他 provider 的內容。

### 4.6 Installer 與文件

- `ClaudeAdapter` 安裝 SessionStart + SessionEnd，移除 governance Stop closeout；修正 docstring 與說明。
- `verify` 能辨識舊格式（含 `; exit 0`、`|| true`、只有 Stop）並回報需要重裝；**重裝各 repo 的 hook 是獨立的授權動作**。

## 五、驗收（需付費 session，另行授權）

先在拋棄式 consumer 以新 installer 安裝，再逐一導入正式專案。

1. **開始與保存**：`startup` 建立 v1.1 身分；多回合工作中**沒有**任何 closeout；Claude 呼叫 `prepare_closeout_candidate` 保存摘要。
2. **退出 → 恢復 → 繼續 → 再退出 → 讀回最新**：退出（SessionEnd 寫 checkpoint、無 completion marker）→ `claude --resume` 同一 session（沿用身分、`additionalContext` 帶回摘要）→ 繼續修改並再次 `prepare_closeout_candidate` → 再退出 → 下一次開始時讀回的是**第二次**的摘要。
3. **新 session 交接**：新 `startup` session 讀回前一個 session 的最新有效摘要，狀態正確。
4. **負向**：
   - 強制結束程序使 SessionEnd 未執行 → 下一次 SessionStart 標示「未確認退出」或 `UNKNOWN`，不推定成功。
   - 讓 SessionEnd 逾時／失敗 → 留下可查的紀錄。
   - `resume` 但無既存身分 → 不建立身分、回報 `UNKNOWN`。
   - 從子目錄啟動 → 正常綁定到 worktree root。
5. **正式結案**：在明確的完成操作後才寫 completion marker；之後同一 session 不能再準備摘要（沿用既有規則）。

## 六、需要 owner 決定的事（附審查建議的預設值）

| 決策 | 審查建議 | 狀態 |
|---|---|---|
| 1. `claude` 成為 root-bound provider | 原則同意：`claude → claude_session_start`，沿用 Codex 的專案綁定檢查，不可接管其他 provider | 待 owner 核准（信任結構變更） |
| 2. Stop 如何處理 | 移除 governance 的 Stop 結案 hook；保留非治理用途的自訂 hook | 待決定 |
| 3. SessionEnd timeout | 先設 5 秒，只做輕量 checkpoint；實測不足再調整 | 待決定 |
| 4. 讀回內容 | 最多 800 字經驗證摘要 + 來源指標，只讀同一 worktree 最近有效摘要／checkpoint | 待決定 |
| 5. 安裝與付費驗收 | 先拋棄式專案，再逐一導入；真實 Claude 驗收與正式專案重裝另外授權 | 待決定 |

以上是建議採納的設計選項，不是修改本機 hook 或執行付費 session 的授權。
