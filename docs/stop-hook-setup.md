# Stop Hook 安裝設定
這份文件說明如何把 Claude Code、VS Code Agent Hooks 與 GitHub Copilot 的 session 結束事件接到 canonical `session_end`。
目的不是把 closeout 變成 agent 自述，而是讓 session closeout 經過 runtime 驗證，留下可審計的 artifact。

VS Code Agent Hooks（Preview）與 GitHub Copilot lifecycle hooks 可透過同一個薄 wrapper 傳遞 `cwd` 與 `session_id`。若平台、版本或組織政策未啟用 hooks，仍應使用 `scripts/run_closeout.ps1` 作為明確的手動 fallback。

---

## 1. 在使用者層安裝 hook

請編輯 `~/.claude/settings.json`  
Windows 通常位於：`C:\Users\<you>\.claude\settings.json`

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python -m governance_tools.session_end_hook --project-root \"${workspaceFolder}\" --format human"
          }
        ]
      }
    ]
  }
}
```

注意：`${workspaceFolder}` 會由 Claude Code 代入目前工作區路徑。  
如果 hook 是從 framework repo 本身執行，這個值通常就是 framework repo；若是從 consuming repo 使用，`--project-root` 應指向 consuming repo。

---

## 2. 在 consuming repo 中使用 hook

如果 framework 是以 submodule / nested checkout 的方式存在，通常要在 consuming repo 的 `.claude/settings.json` 中明確指定 framework 的 `cwd`：

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python -m governance_tools.session_end_hook --project-root \"${workspaceFolder}\" --format human",
            "cwd": "<path-to-ai-governance-framework>"
          }
        ]
      }
    ]
  }
}
```

請把 `<path-to-ai-governance-framework>` 換成實際 checkout 路徑。

### VS Code / Copilot lifecycle bridge

執行 governed hook installer 後，consuming repo 會得到：

- `.github/hooks/ai-governance-lifecycle.py`
- `.github/hooks/ai-governance-vscode.json`
- `.github/hooks/ai-governance-copilot.json`

兩份 JSON 的職責如下：

- VS Code 專用設定的框架範本為空 `hooks`，不註冊 closeout
- GitHub Copilot 相容設定宣告 `sessionStart`、`sessionEnd`

VS Code 的 [`Stop`](https://code.visualstudio.com/docs/agents/reference/hooks-reference#_stop) 只表示目前 agent execution 停止，不表示 session 結束。Local harness 沒有經確認的 session-end 事件時，需在明確的 session 結束使用既有手動 closeout；本修復不新增替代事件。支援真正 `sessionEnd` 的 Copilot 平台仍使用原有 bridge。不得在 VS Code 設定重複註冊框架 `SessionStart`；它會與 Copilot 相容設定重複。

正常安裝、`--copilot-only`、`--copilot-vscode-only` 與 F-7 apply 共用退役流程：只移除 VS Code 設定中可辨識的舊框架 `Stop`／重複 `SessionStart` 項目，保留同檔的自訂 hook 與其他欄位。修改前依既有規則備份；無需修改的自訂檔保留原始 bytes。無法辨識的 bridge 命令或損壞配置會回報錯誤並保留原檔，須人工處理，不以範本覆蓋。`--copilot-vscode-only` 保留為相容的退役入口，不再提供 VS Code 自動 closeout。

可用 validator 檢查 repo-local wiring：

```bash
python -m governance_tools.hook_install_validator --repo .
```

`copilot_lifecycle_installed=true` 只表示 bridge、真正 `sessionEnd` 配置與可選 VS Code 配置的靜態檢查成立。VS Code 配置可不存在、為空或只保留自訂 hook；殘留框架 lifecycle 項目會使 validator 回報不合規。這不證明平台已載入配置或 sessionEnd 實際觸發，也不評估自訂 hook 的業務正確性。

---

## 3. 這個 hook 會做什麼

在 session 結束時，hook 會：
1. 讀取 `${workspaceFolder}/artifacts/session-closeout.txt`
2. 檢查 closeout artifact 狀態，例如 `valid` / `missing` / `insufficient`
3. 視需要呼叫 `session_end.py`
4. 產出 `artifacts/runtime/verdicts/` 與 `artifacts/runtime/traces/` 中的 artifact
5. 若 closeout 與 policy 條件成立，才考慮 memory promotion

注意：
如果 closeout 缺失或格式不符，hook 不應假裝成功，而應輸出 degraded verdict 與具體原因。

---

## 4. AI 端應準備的 closeout 內容

stop hook 觸發前，AI 應先產出 `artifacts/session-closeout.txt`。  
其欄位格式請參考 [docs/session-closeout-schema.md](session-closeout-schema.md)。

如果 AI 沒有寫出對應格式，hook 會把這次 closeout 視為 `closeout_missing` 或 `closeout_insufficient`。  
這代表 memory 不會被 promote，而且 session 會留下可觀測缺口。

---

## 5. 如何驗證 hook 是否真的接上

至少應檢查：

```bash
ls artifacts/runtime/verdicts/
ls artifacts/runtime/traces/
```

如果 stop hook 有正確執行，應該能看到新的 runtime verdict / trace artifact，且 `session_end` 的 human-readable output 可被 reviewer 讀到。

也可以額外確認：
- `artifacts/runtime/summaries/` 是否有新的 summary artifact
- `memory_closeout` 是否出現在 summary artifact 中
- `memory_closeout_decision` / `memory_closeout_reason` 是否可見

---

## 6. 非目標

這份文件目前**不主張**：
- stop hook 等於完整 enforcement
- 有 closeout artifact 就等於 closeout 正確
- stop hook 可以取代 reviewer reconstruction
- hook 檔案存在就等於編輯器或 Copilot 已載入並觸發
- Preview hook 在所有版本與組織政策下都可用

它的角色是把 session 結束時的 closeout 接進 runtime，而不是把 closeout 直接變成 authority。

## 一句總結

`Stop Hook Setup` 的目的，是把 session 結束時的 closeout 帶進可驗證的 runtime path，讓 missing / insufficient / valid 的差異可以被系統看見，而不是悄悄消失。
