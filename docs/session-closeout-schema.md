# Session Closeout Artifact Schema：AI closeout candidate 的最小格式

> 版本：1.0  
> Artifact path：`artifacts/session-closeout.txt`  
> Written by：AI agent at end of session  
> Consumed by：`governance_tools/session_end_hook.py` via stop hook

---

## 目的

這份 artifact 是 AI agent 在 session 結束時提供給 governance runtime 的 **closeout input candidate**。  
它不是 truth source，而是候選輸入；真正 authoritative 的 verdict / trace artifact 仍由 governance runtime（`session_end_hook -> session_end`）產生。

換句話說：
- AI 可以寫 closeout candidate
- runtime 只把它當候選輸入
- canonical closeout 與 downstream artifact 由 system 產生

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

## 一句總結

`session-closeout artifact schema` 的目的是讓 AI 在 session 結束時提供可解析的 closeout candidate，但真正可信的 closeout 結論仍由 runtime 產生。
