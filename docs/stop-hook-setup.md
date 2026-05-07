# Stop Hook 安裝設定
這份文件說明如何把 Claude Code 的 stop / session 結束事件接到 `session_end_hook`。
這份文件說明如何把 Claude Code 的 stop / session 結束事件接到 `session_end_hook`。
目的不是把 closeout 變成 agent 自述，而是讓 session closeout 經過 runtime 驗證，留下可審計的 artifact。

In GitHub Copilot Tier B, memory closeout is not triggered automatically.
Use `scripts/run_closeout.ps1` after task completion to produce canonical closeout and memory update evidence.

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

它的角色是把 session 結束時的 closeout 接進 runtime，而不是把 closeout 直接變成 authority。

## 一句總結

`Stop Hook Setup` 的目的，是把 session 結束時的 closeout 帶進可驗證的 runtime path，讓 missing / insufficient / valid 的差異可以被系統看見，而不是悄悄消失。
