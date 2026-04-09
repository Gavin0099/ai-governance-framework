# Stop Hook Setup

設定 Claude Code 在 session 結束時自動呼叫 `session_end_hook`。

這樣 session closeout 會在 runtime 層被觸發，而不是只靠 AI 自覺遵守。

---

## 全域 hook（套用到所有 repo）

編輯 `~/.claude/settings.json`（Windows：`C:\Users\<you>\.claude\settings.json`）：

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

**注意：** `${workspaceFolder}` 在 Claude Code 中會解析成目前專案根目錄。  
這個 hook 會在 framework repo 的工作目錄下執行；如果你是從外部 consuming repo 使用，請把 `--project-root` 指向 consuming repo 的路徑。

---

## 每個 repo 各自設定 hook（若不同 repo 需要不同 project root）

如果某個 consuming repo 需要自己的 `.claude/settings.json`，可在該 repo 內加入：

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

請把 `<path-to-ai-governance-framework>` 換成這個 repo 的絕對路徑。

---

## 這個 hook 會做什麼

1. 讀取 `${workspaceFolder}/artifacts/session-closeout.txt`
2. 分類 closeout artifact（`valid` / `missing` / `insufficient`）
3. 無論分類結果如何，都呼叫 `session_end.py`
4. 產生 `artifacts/runtime/verdicts/` 與 `artifacts/runtime/traces/` artifact
5. 如果 closeout 有效，且 policy 判定為 `AUTO_PROMOTE`，就更新 memory

**這個 hook 一定會跑。**  
即使 closeout 缺失或無效，也不會直接 abort，而是產生 degraded verdict，把缺口記錄下來。

---

## AI 在 session 結束前必須做的事

在 stop hook 觸發之前，AI 必須先寫出 `artifacts/session-closeout.txt`。

所需欄位請看 [docs/session-closeout-schema.md](session-closeout-schema.md)。

如果 AI 沒有寫這個檔案，hook 還是會跑，並在 verdict 中記錄 `closeout_missing`。  
這時 memory 不會更新，但這個缺口會被保留成可審計紀錄。

---

## 如何驗證 hook 有正常工作

設定完成後，結束一次 session，然後檢查：

```bash
# 應該看得到新的 session artifact
ls artifacts/runtime/verdicts/

# 讀最新 verdict
python -c "
import json, pathlib, os
d = pathlib.Path('artifacts/runtime/verdicts')
latest = max(d.glob('*.json'), key=os.path.getmtime)
v = json.loads(latest.read_text())
print('decision:', v['verdict']['decision'])
print('closeout_status:', v.get('evidence_summary', {}).get('check_keys'))
"
```

如果 verdict 裡出現 `closeout_missing`，表示 hook 有跑，但 AI 沒有先寫出 closeout 檔案。  
這是預期中的 degraded state，不是 hook 本身故障。
