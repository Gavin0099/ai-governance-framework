# Closeout Repo Readiness

> Version: 1.0

repo 若要被視為 **closeout-ready**，至少要滿足以下條件。  
這不代表 closeout 品質已經很好，只代表 session closeout 的基礎設施已經到位。

---

## 最低條件

### 1. `AGENTS.base.md` 存在，且包含 closeout obligation

adopt 後的 repo 應具備 `AGENTS.base.md`，或至少把相同 obligation 放進 `AGENTS.md`。  
其中必須包含 `Session Closeout Obligation` 段落。

驗證：

```bash
grep -l "Session Closeout Obligation" AGENTS.base.md AGENTS.md 2>/dev/null
```

若缺失，重新 adopt：

```bash
python governance_tools/adopt_governance.py --target <repo> --framework-root <ai-gov>
```

---

### 2. Artifact 寫入路徑存在或可建立

`session_end_hook` 會寫：
- `artifacts/session-closeout.txt`
- `artifacts/runtime/`

repo 不能阻擋這些路徑的寫入。

驗證：

```bash
mkdir -p artifacts/runtime && echo "ok" > artifacts/.write-test && rm artifacts/.write-test
```

---

### 3. 能從 framework repo 執行 `session_end_hook`

stop hook 會呼叫：

```bash
python -m governance_tools.session_end_hook
```

這表示環境至少要具備：
- 可執行的 Python
- framework repo 在 Python path 之中（例如先切到 framework root）

驗證：

```bash
# 從 framework repo root 執行
python -m governance_tools.session_end_hook --project-root <your-repo> --format human
```

預期輸出：`closeout_status=closeout_missing`，exit code 為 1。  
若直接看到 Python import error，表示依賴或路徑尚未接好。

---

### 4. Schema 文件可被引用

framework repo 中應存在：

```text
docs/session-closeout-schema.md
```

AI 才能在寫 closeout 時參照合法 schema。

驗證：

```bash
test -f docs/session-closeout-schema.md && echo "present"
```

---

### 5. Stop hook 已設定（若要自動 closeout）

若希望每次 session 自動 closeout，`.claude/settings.json` 需要設定 `Stop` hook。  
可參考 [stop-hook-setup.md](/e:/BackUp/Git_EE/ai-governance-framework/docs/stop-hook-setup.md)。

手動備援方式：

```bash
python -m governance_tools.session_end_hook --project-root .
```

---

## Readiness 檢查命令

最小檢查：

```bash
python -m governance_tools.session_end_hook --project-root <your-repo> --format human
```

| Output | Meaning |
|--------|---------|
| `closeout_status=closeout_missing` | 基礎設施已就緒，但 AI 還沒寫 closeout |
| `closeout_status=valid` + `promoted=True` | closeout 流程已完整跑通，且上次 session 有成功 promotion |
| Python `ModuleNotFoundError` | 依賴未安裝或 path 未接好 |
| `FileNotFoundError` on project-root | 指定的 repo 路徑不存在 |

---

## Readiness 不保證什麼

- 不保證 AI 一定會寫出合法 closeout
- 不保證 memory 一定更新
- 不保證 evidence claims 一定為真
- 不保證 repo 在其他治理維度都已完全合規

Readiness 只是讓 closeout contract 能運作的前提，不是治理品質證書。

---

## Memory Promotion Note

memory 只有在 `closeout_status=valid` 時才會更新。

這是刻意保守的策略，也帶來明確取捨：

- **太嚴**：若 evidence consistency 因環境差異誤判，真實工作也可能無法更新 memory
- **太鬆**：若允許 `content_insufficient` closeout 也寫入 memory，就會讓 AI 自述繞過驗證

目前 policy 偏向保守。  
如果未來 recurring false positive 變多，應優先修 evidence consistency 檢查，而不是直接降低 `valid` 門檻。

長期來看可以考慮兩層 memory promotion：
- `memory_safe_update`：內容可信，但 evidence 未完全驗證
- `memory_high_confidence_update`：四層都通過

但那是未來選項，不是目前 contract。
