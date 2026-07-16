# Runtime 偵測 Spike — 訊號清單與實測狀態

> 目的：在寫任何 schema 之前，實測「Runtime Profile 各欄位到底拿不拿得到、可信度幾級」。
> 本目錄為拋棄式 spike：決策做完後整個 `spikes/runtime-detect/` 可整組刪除，只留報告結論。
> 偵測分級沿用 plan 0.2：`verified`（環境/CLI/harness 直接取得）> `detected`（可靠特徵推定）> `reported`（agent 自述）> `unknown`。
> **鐵律：腳本零 LLM 呼叫、零網路呼叫、失敗一律降級為 unknown，不猜。**

## 執行方式

```
python -X utf8 spikes/runtime-detect/detect_spike.py                       # 人讀摘要
python -X utf8 spikes/runtime-detect/detect_spike.py --out result-X.json   # 存證據（UTF-8 bytes）
```

⚠️ 不要用 PowerShell 的 `>` 重導存證據——PS 5.1 會寫成 UTF-16，下游 UTF-8 解析會炸。一律用 `--out`。

在每個要實測的 agent session 裡跑一次（Claude Code、Codex CLI、Gemini CLI、IDE 插件），
把輸出存成 `result-<agent>-<surface>.json` 收在本目錄。

## 每個 agent 要實測的訊號

### Claude Code（2026-07-16 已實測，Windows / desktop app）

| 欄位 | 訊號 | 實測結果 | 分級 |
|---|---|---|---|
| agent | env `CLAUDECODE=1` | ✅ 存在 | verified |
| agent_version | env `CLAUDE_CODE_EXECPATH`（路徑含版本 `...\claude-code\2.1.209\claude.exe`） | ✅ 2.1.209 | verified |
| agent_version（備援） | `claude --version`（CLI 若在 PATH） | ❌ desktop 版不在 PATH | — |
| model | env（`ANTHROPIC_MODEL` 等） | ❌ 不存在 | — |
| model | transcript：`~/.claude/projects/<slug>/<CLAUDE_CODE_SESSION_ID>.jsonl` 的 `"model"` 欄位（harness 寫入，非 agent 自述） | ✅ claude-fable-5 | verified* |
| surface | env `CLAUDE_CODE_ENTRYPOINT`（`claude-desktop` / `cli` / `sdk-*`） | ✅ claude-desktop | verified |
| session 綁定 | env `CLAUDE_CODE_SESSION_ID` | ✅ | verified |
| permission_mode | bare shell 環境 | ❌ 只存在於 hook payload | unknown（正式版應改由 SessionStart hook 收） |
| tools | 同上 | ❌ | unknown（同上） |

\* transcript 由 harness 寫盤、以環境變數的 session ID 定位，非 agent 可控輸出；保守可降記 detected，但來源鏈完整。

**結論：Claude Code 四大欄位（agent/version/model/surface）全部可達 verified，不需 agent 自述。**

### Codex（2026-07-16 已實測，Windows / Codex Desktop）

| 欄位 | 實測訊號 | 結果 |
|---|---|---|
| agent | env `CODEX_INTERNAL_ORIGINATOR_OVERRIDE=Codex Desktop` | ✅ `codex` / verified |
| agent | 父行程鏈裡是否有 `codex` / `codex.exe` | ❌ parent chain 為空；不可作主訊號 |
| agent_version | `codex --version` | ❌ WindowsApps 執行別名回傳 `PermissionError` / unknown |
| model | `~/.codex/config.toml` 的 `model =` | ✅ `gpt-5.6-sol` / detected（預設值，未證明與本 session 綁定） |
| surface | `CODEX_INTERNAL_ORIGINATOR_OVERRIDE` raw env | ✅ raw evidence 為 `Codex Desktop`；現有 profile mapper 仍為 unknown |
| session 綁定 | env `CODEX_THREAD_ID` | ✅ raw evidence 存在；現有 profile mapper 仍為 unknown |
| permission_mode | env/config 的 sandbox/approval 設定 | ⚠️ 只見 `CODEX_SANDBOX_NETWORK_DISABLED=1`，不足以代表完整 permission mode / unknown |

### GitHub Copilot（2026-07-16 已實測，Windows / VS Code）

| 欄位 | 實測訊號 | 結果 |
|---|---|---|
| agent | env `COPILOT_AGENT=1` | ✅ raw 有；**初測時 mapper 未映射 → 保守回報 unknown（降級正確）**；測後補一行映射，replay 升為 `github_copilot` / verified |
| agent | 父行程鏈 | ❌ 只見 `Code.exe`，無 Copilot 專屬執行檔訊號 |
| agent_version / model / session_id | env、config | ❌ 全 unknown，目前無已知訊號 |
| surface | `TERM_PROGRAM=vscode` | ✅ `vscode` / verified |
| 其他 raw | `COPILOT_DEBUG_NONCE` | 存在（證據檔保留、不展開） |

- 完整證據：`result-copilot-vscode.json`（**profile 反映補映射前的腳本**；補映射後的判定以離線 replay 驗證，見下）
- 這是預測中的「半盲組合」實例：surface 可驗、agent 起初不可辨。價值：驗證了 plan 1.3「未知 agent 不誤判、不擋工作」在真實環境成立。
- Copilot 線的 model 目前無任何非自述訊號 → 若未來 Copilot 進 pilot，其樣本會全數落在 model=unknown 組，統計上會誠實呈現而非污染。

### Gemini CLI（本機有裝 0.17.1，待在 gemini session 裡實測）

| 欄位 | 要測的訊號 | 預期 |
|---|---|---|
| agent | 掃所有 `GEMINI_*` 環境變數；父行程鏈 | 待確認 |
| agent_version | `gemini --version` → 0.17.1（PATH 安裝版，最高 detected） | ✅ CLI 可取 |
| model | `~/.gemini/settings.json` 的 model 設定 | 待確認 |
| surface | 同 Codex 的 TERM_PROGRAM 判別 | 待確認 |

### 其他 surface 判別訊號（腳本一律掃描）

- `TERM_PROGRAM=vscode` → VS Code 整合終端
- `CURSOR_TRACE_ID` / `CURSOR_AGENT` → Cursor
- `TERMINAL_EMULATOR=JetBrains-JediTerm` → JetBrains
- `WT_SESSION` → Windows Terminal
- `COPILOT_*` → GitHub Copilot CLI
- `AIDER_*` → Aider

### governance_version

- 讀 repo README.md 的 `- version: \`x.y.z\`` 或 badge（與 `framework_versioning.py` 同源）→ verified

## 2026-07-16 實測結果（Claude Code / Windows / desktop）

- 摘要：**verified=6（agent, agent_version, model, surface, session_id, governance_version）/ detected=0 / unknown=2（permission_mode, tools——只存在於 hook payload，非 shell 可見）**
- 完整證據：`result-claude_code-claude-desktop.json`
- 負面測試（剝掉 env 標記重跑）：全欄降級為 unknown，無猜測 → 保守降級路徑通過。
- ⚠️ 發現：**父行程鏈偵測很脆弱**——中介 shell 先退出就斷鏈（實測 `env -u` 包一層後，鏈在 env.exe 斷掉，走不到上層的 claude.exe）。父鏈只能當 fallback 訊號，不能當主訊號；正式版主訊號必須是 env 標記 + hook payload。
- Kill-switch 判定：Claude Code 這條線 **繼續**（agent+model 均 verified）。

## 2026-07-16 實測結果（Codex / Windows / Codex Desktop）

- 摘要：**verified=2（agent, governance_version）/ detected=1（model）/ unknown=5（agent_version, surface, session_id, permission_mode, tools）**。
- 完整證據：`result-codex-codex-desktop.json`。
- raw env 額外證據：`CODEX_INTERNAL_ORIGINATOR_OVERRIDE=Codex Desktop`、`CODEX_THREAD_ID=<thread id>`；目前腳本只用前者辨識 agent，尚未映射 surface/session_id。
- 負面測試（剝掉四個已觀察到的 `CODEX_*` 標記重跑）：agent 與 model 都降級 unknown；只保留 repo README 可獨立驗證的 governance_version，無猜測 → 保守降級路徑通過。
- CLI 限制：`codex` 位於 WindowsApps package，`codex --version` 在此 sandbox 回傳 `PermissionError`，所以 agent_version 維持 unknown。
- Kill-switch 判定：Codex 這條線 **繼續**（agent=verified、model=detected）。Claude Code 與 Codex 兩個主力 agent 均達事前判準，整案 **GO**，可以進入表面預算程序；這不代表正式 runtime detection 已實作或所有欄位已可得。

## 2026-07-16 實測結果（GitHub Copilot / Windows / VS Code）＋腳本修訂

- 摘要：初測 **verified=2（surface, governance_version）/ unknown=6**；raw 存在 `COPILOT_AGENT=1` 但 mapper 未接。
- 測後腳本修訂兩筆：(1) `COPILOT_AGENT` → `github_copilot` 映射；(2) 新增 `--out <path>` 直寫 UTF-8 bytes——**PowerShell 5.1 的 `>` 會把 stdout 存成 UTF-16**，證據檔一律改用 `--out` 保存。
- 修訂後離線 replay 迴歸（用三份已存證據的 raw env 重跑判定）：claude_code=verified、codex=verified 不變；copilot 升為 verified；copilot 負向 replay（剝 `COPILOT_*`）仍回 unknown。三份 result JSON 的 profile 欄位反映各自執行當下的腳本版本，raw 欄位是重驗依據。
- Kill-switch 影響：無（Copilot 非事前判準中的主力 agent；GO 維持）。

## Spike 的 kill-switch 判準（事前寫死，避免事後合理化）

- **繼續**：主力 agent（Claude Code、Codex）在實際使用的 surface 上，agent + model 兩欄至少達 detected，且 agent 欄至少一個 verified 訊號。
- **擱置**：主力 agent 有任一個的 model 與 agent_version 都只能 unknown / reported → plan 的分組統計失去輸入，整案停在 spike 報告。
