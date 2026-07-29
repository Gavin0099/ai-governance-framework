# Session Closeout Artifact Schema：AI closeout candidate 的最小格式

> 版本：1.0  
> Artifact path：`artifacts/session-closeout.txt`  
> Written by：AI agent at end of session  
> Consumed by：`governance_tools/session_end_hook.py` via stop hook

> Session binding：automatic closeout additionally requires the
> `artifacts/runtime/sessions/<session_id>/session-envelope.json` created by
> `session_start` and a candidate under
> `artifacts/runtime/closeout_candidates/<session_id>/`.
> The active marker is stored at
> `artifacts/runtime/.current-session-id`; the repo-root marker remains a
> legacy read-compatible input only.

---

## 目的

這份 artifact 是 AI agent 在 session 結束時提供給 governance runtime 的 **closeout input candidate**。  
它不是 truth source，而是候選輸入；真正 authoritative 的 verdict / trace artifact 仍由 governance runtime（`session_end_hook -> session_end`）產生。

換句話說：
- AI 可以寫 closeout candidate
- runtime 只把它當候選輸入
- canonical closeout 與 downstream artifact 由 system 產生

對自動 session-end 而言，共用的 `artifacts/session-closeout.txt` 不是
session identity。Runtime 只允許相同 `session_id`、且
`candidate.generated_at >= envelope.started_at`，且共同欄位內容與共享
closeout 一致的 session-bound candidate 進入 promotion 與 daily-memory
side effects。Promotion 的內容由已綁定 candidate 產生，不直接信任共享
文字檔。

Canonical closeout 檔案本身不代表 session 已 consumed。只有 runtime 在
所有必要 artifact 寫入完成後，原子寫入
`artifacts/runtime/closeout-completions/<session_id>.json`，且該 marker
所列 artifact 仍可驗證存在時，session 才視為 consumed。中途失敗但只留下
部分 canonical artifact 的 session 必須允許重試；已完成 session 的重複
stop hook 不得再寫 audit、candidate、transcript 或 promotion side effects。

只有舊版共用文字檔、沒有 session-bound candidate 時必須 fail closed；
runtime 不得在 session end 才替該文字補上新的 identity 或 timestamp。

---

## 設計原則

每個欄位都應具備可解析、可缺省、可降級的特性。  
若某欄位不存在，應明確寫成 `NONE` 或 `NO_UPDATE`，而不是留給 parser 猜測。

## 最小欄位（runtime required）

`governance_tools/session_end_hook.py` 目前要求以下 7 欄（缺任一欄位會是 schema_invalid）：
- `TASK_INTENT`
- `WORK_COMPLETED`
- `FILES_TOUCHED`
- `CHECKS_RUN`
- `OPEN_RISKS`
- `NOT_DONE`
- `RECOMMENDED_MEMORY_UPDATE`

### P5 Codex 固定 evidence checklist（closeout 建議寫法）

當 session 涉及 CodeBurn P5（Codex ingestion/smoke/replay）時，`CHECKS_RUN` 建議固定包含以下證據入口（可直接複製）：

`python -m codeburn.phase2.codeburn_codex_smoke --json`

`python -m pytest tests/test_codeburn_codex_smoke.py -q -p no:cacheprovider --basetemp .tmp_pytest_codex_smoke`

`python -m pytest tests/test_codeburn_codex_replay.py -q -p no:cacheprovider --basetemp .tmp_pytest_codex_replay`

`FILES_TOUCHED` 建議至少包含：
- `codeburn/phase2/codeburn_codex_smoke.py`
- `tests/test_codeburn_codex_smoke.py`
- `tests/test_codeburn_codex_replay.py`

語意邊界（必須保留）：
- P5.4 smoke 只驗證 ingestion pipeline operability，不驗證 token 正確性
- 不開放 cross-provider comparison
- replay stable != provider truthful
- duplicate ingest allowed != duplicate semantic consumption allowed

### Copilot Class D 固定 evidence checklist（closeout 建議寫法）

當 session 涉及 Copilot AI Credits ingestion（Class D）時，`CHECKS_RUN` 建議固定包含以下證據入口（可直接複製）：

`python -m pytest tests/test_codeburn_copilot_ingestion.py tests/test_codeburn_copilot_smoke.py -q -p no:cacheprovider --basetemp .tmp_pytest_copilot`

`python codeburn/phase2/codeburn_copilot_smoke.py --csv codeburn/phase2/examples/copilot_smoke_fixture.csv --json`

`python codeburn/phase2/codeburn_copilot_smoke.py --csv codeburn/phase2/examples/copilot_smoke_fixture.csv --mark-final --json`

`FILES_TOUCHED` 建議至少包含：
- `codeburn/phase2/codeburn_copilot_smoke.py`
- `tests/test_codeburn_copilot_ingestion.py`
- `tests/test_codeburn_copilot_smoke.py`

closeout 目標語句（必須保留）：
- `Copilot AI Credits billing evidence ingestion supported`

避免語句（禁止）：
- `Copilot cost analysis supported`

語意邊界（必須保留）：
- Class D = billing-reported evidence
- AI Credits != raw token truth
- billing evidence != session provenance
- preview/projection != final billing
- final billing evidence != decision-safe cost audit

## 邊界

這份 schema 目前只做：
- 規範 AI closeout candidate 的最小格式
- 讓 stop hook / `session_end` 能穩定解析
- 讓 reviewer 知道 candidate 與 canonical artifact 的差別

這份 schema **不做**：
- 讓 AI candidate 直接變成 canonical verdict
- 取代 runtime 的 closeout validation
- 讓 missing field 自動推論為成功完成
- 讓固定 closeout 路徑本身證明 current-session ownership
- 讓已 consumed 的 closeout 再次 promotion

## 一句總結

`session-closeout artifact schema` 的目的是讓 AI 在 session 結束時提供可解析的 closeout candidate，但真正可信的 closeout 結論仍由 runtime 產生。
