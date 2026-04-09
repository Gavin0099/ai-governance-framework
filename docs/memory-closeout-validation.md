# Memory Closeout 驗證指南

## 目的

這份文件說明如何在 consuming repo 驗證 `ai-governance-framework` 的 `session_end` 是否真的有產生 memory closeout decision surface。

要驗證的不只是：
- memory 有沒有寫進去

還包括：
- shared path 是否有把 closeout 帶進 `session_end`
- `memory_closeout` 是否有出現在 human output 與 summary artifact
- 沒有更新 memory 時，系統是否能說清楚原因

## 核心檢查欄位

first slice 至少要能看見：
- `memory_candidate_detected`
- `memory_candidate_signals`
- `memory_promotion_considered`
- `memory_closeout_decision`
- `memory_closeout_reason`

## 測試分兩層

### 第 1 層：framework repo 內部驗證

先確認 framework 自身的 `session_end` closeout 邏輯沒有壞：

```powershell
python -m pytest tests/test_runtime_session_end.py -q -k "memory_closeout or auto_promotes_low_risk_candidate or requires_review_for_high_risk or stateless or public_api_diff or human_output"
```

預期：
- 測試通過
- framework 端已能輸出 `memory_closeout`
- human-readable output 已帶出對應欄位

### 第 2 層：consuming repo 真實驗證

在 consuming repo 手動呼叫 `run_session_end`，確認 closeout decision surface 是否可見。

## 前置條件

對 consuming repo，至少要確認：
- framework submodule 或 checkout 可被 Python 匯入
- repo 有 `contract.yaml`
- repo 能執行 framework Python 工具

如果 framework 是放在 `additional/ai-governance-framework`，通常可先設定：

```powershell
$env:PYTHONPATH="additional/ai-governance-framework"
```

## Canonical Framework Source

驗這份 closeout visibility 時，建議使用官方 canonical source：
- `https://github.com/Gavin0099/ai-governance-framework.git`

若使用落後 fork，可能只驗到舊版 `session_end` closeout，而不是新版 memory closeout visibility。

可先確認：

```powershell
git remote -v
git rev-parse HEAD
git log --oneline -3
```

至少應包含：
- `6c9f0aa` `Add memory closeout visibility`
- `dea37c5` `Add memory closeout validation guide`

## 手動 closeout 驗證命令

在 consuming repo 執行：

```powershell
python -c "from pathlib import Path; from runtime_hooks.core.session_end import run_session_end, format_human_result; project_root = Path('.').resolve(); runtime_contract = {'name':'demo-repo','memory_mode':'candidate','oversight':'review-required','risk':'high','rules':['common','refactor']}; result = run_session_end(project_root=project_root, session_id='manual-memory-closeout-check', runtime_contract=runtime_contract, checks={'ok': True, 'errors': [], 'public_api_diff': {'ok': True, 'removed': [], 'added': ['public int Ping() => 0;'], 'warnings': [], 'errors': []}}, response_text='Fixed a crash caused by invalid state transition.', summary='Crash fix with public API impact'); print(format_human_result(result)); print(result['summary_artifact'])"
```

## 驗證標準

human-readable output 至少要出現：

```text
memory_candidate_detected=True
memory_promotion_considered=True
memory_closeout_decision=REVIEW_REQUIRED
memory_closeout_reason=...
```

summary artifact 內則至少應看到：

```json
"memory_closeout": {
  "candidate_detected": true,
  "candidate_signals": ["public_api_change"],
  "promotion_considered": true,
  "decision": "REVIEW_REQUIRED",
  "reason": "..."
}
```

## 如何解讀結果

常見情況：
- `candidate_detected=False`
  - 代表這次 session 沒被視為高價值 memory candidate
- `promotion_considered=False`
  - 代表 policy 或 mode 使它不進 promotion consideration
- `decision=REVIEW_REQUIRED`
  - 代表有 candidate，但高風險或需要人工 review
- `reason` 提到 `memory_mode=stateless` 或 `response_text missing`
  - 代表 closeout lane 有跑，但被明確擋下

## 一句總結

這份驗證不是要證明 memory 一定會自動更新，而是要確認：當 session 值得被考慮進 memory 時，framework 至少會留下可觀測的 closeout decision 與理由，而不是像沒發生過一樣消失。
