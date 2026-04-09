# External Repo Functional Test Checklist：外部 repo 功能驗證清單

> 版本：2026-04-05 rev2  
> Framework 狀態：Beta（Beta Gate passed 2026-03-28）

## 目的

這份清單用來驗證：`ai-governance-framework` 套用到外部 repo 後，核心功能是否真的能正常工作。

## 前置條件

```bash
git clone https://github.com/Gavin0099/ai-governance-framework.git ai-gov
cd ai-gov
pip install -r requirements.txt
```

被測 repo 至少要：

- 是 git repository
- 可被本機路徑存取
- memory 檔案為 UTF-8（非 UTF-8 會被 replace，不會 crash）

## F1：Onboarding Adoption

驗證 `adopt_governance.py` 能否把治理骨架寫進新 repo。

### Pass Criteria

- dry-run 不寫檔但能正確預覽
- live run 會寫出：
  - `contract.yaml`
  - `AGENTS.md`
  - `.governance/baseline.yaml`
  - `memory/01..04`

## F2：Governance Drift Check

驗證 consuming repo 是否能被 drift checker 正確檢查。

### Pass Criteria

- 輸出含 `ok`、`severity`、`findings`、`errors`
- `ok=True` 代表無 blocking drift
- `warning` 可存在，但必須可解釋

## F3：Quickstart Smoke

驗證最小 runtime（`session_start` + `pre_task`）是否可用。

### Pass Criteria

- `ok=True`
- `pre_task_ok=True`
- `session_start_ok=True`

## F4：Session Lifecycle

驗證 `pre_task_check` / `post_task_check` 能否在真實 task 路徑上返回結構化輸出。

### Pass Criteria

- `pre_task_check` 能回傳結構化 JSON
- `decision_boundary.preconditions_checked` 存在
- `post_task_check` 不應拋未處理例外

## F5：DBL Enforcement

驗證 DBL 不是只做文件敘事，而是真的在 runtime path 上執行 precondition gate。

### Pass Criteria

- `missing_spec.applies = true`
- `missing_spec.action = restrict_code_generation_and_escalate`
- `boundary_effect = escalate`

## F6：Domain Rule Packs

驗證 contract 指定的 domain / rule pack 是否真的存在並能被載入。

### Pass Criteria

- `governance/rules/<domain>/...` 存在
- `quickstart_smoke` 可成功載入

## F7：External Repo Readiness

驗證 framework 能否正確說明外部 repo 是否 ready。

### Pass Criteria

- 有結構化輸出
- 明確給出 `ready=True` 或 `ready=False`
- 缺失檔案會被明講，不會被靜默略過

## F8：Project Facts Intake

驗證 framework 能否從 adopted repo 讀出 project facts 與 memory schema 狀態。

### Pass Criteria

- command exit 0
- 產生 `artifacts/external-project-facts/<repo>.json`
- 含 `fact_sources`
- 含 `memory_schema_status`

## F9：Session Closeout 與 Memory Update

驗證 `session_end_hook`、closeout artifact、memory promotion path 是否可被觀測。

### 至少應驗三種情境

1. `closeout_missing`
2. `closeout_insufficient`
3. `closeout_valid`

### Pass Criteria

- degraded 狀態不 crash
- 有結構化 verdict artifact
- valid closeout 時，能看到 snapshot / promotion 決策

## 已知限制

- 某些 long-CI / release surface 測試不屬於這份清單的最小核心範圍
- 若外部 contract 引用了不存在的 rule pack，`quickstart_smoke` 會失敗
- facts intake 要用 module invocation，避免直接 script invocation 的 import 問題

## 一句話結論

這份清單的目的，不是把所有測試一次跑滿，而是確認外部 repo 已至少完成：adopt、drift、smoke、runtime hook、facts intake、以及 closeout 可觀測性。
