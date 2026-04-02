# Memory Closeout 驗證指南

## 目的

這份文件用來驗證 consuming repo 在實際導入 `ai-governance-framework`
之後，`session_end` 是否已經把 memory closeout 變成可觀測 decision
surface，而不是只看到「memory 沒更新」這個結果。

這份驗證要回答的不是：

- memory 有沒有一定自動寫入

而是：

- shared path 或手動 closeout 是否有進到 `session_end`
- `memory_closeout` 是否真的出現在輸出與 artifact 中
- 沒有寫入 memory 時，系統是否明確說明原因

## 驗證重點

最小成功條件：

1. `session_end` 有被執行
2. human-readable output 有 `memory_closeout` 相關欄位
3. summary artifact 有結構化 `memory_closeout`
4. 高價值候選 session 不會像沒發生過一樣靜默消失

目前 first-slice 可觀測欄位：

- `memory_candidate_detected`
- `memory_candidate_signals`
- `memory_promotion_considered`
- `memory_closeout_decision`
- `memory_closeout_reason`

## 測試分層

建議分兩層驗證：

### 第 1 層：framework repo 內部驗證

先確認 framework 自己的 `session_end` closeout 邏輯正常。

```powershell
python -m pytest tests/test_runtime_session_end.py -q -k "memory_closeout or auto_promotes_low_risk_candidate or requires_review_for_high_risk or stateless or public_api_diff or human_output"
```

預期：

- 測試通過
- 可以證明 `memory_closeout` 的結果與 human output 已被 framework 內部測試保護

### 第 2 層：consuming repo 真實驗證

這一層才是驗證 consuming repo 是否真的看得到 closeout decision。

## 前置條件

在 consuming repo 根目錄確認：

- 已導入 framework submodule 或本地 framework checkout
- repo 已有 `contract.yaml`
- repo 可正常執行 framework Python 工具

若 framework 是以 submodule 放在 `additional/ai-governance-framework`，
可先設定：

```powershell
$env:PYTHONPATH="additional/ai-governance-framework"
```

若 framework 在其他相對路徑，請自行調整。

## 手動 closeout 驗證

在 consuming repo 根目錄執行：

```powershell
@'
from pathlib import Path
from runtime_hooks.core.session_end import run_session_end, format_human_result

project_root = Path(".").resolve()

runtime_contract = {
    "name": "demo-repo",
    "memory_mode": "candidate",
    "oversight": "review-required",
    "risk": "high",
    "rules": ["common", "refactor"],
}

result = run_session_end(
    project_root=project_root,
    session_id="manual-memory-closeout-check",
    runtime_contract=runtime_contract,
    checks={
        "ok": True,
        "errors": [],
        "public_api_diff": {
            "ok": True,
            "removed": [],
            "added": ["public int Ping() => 0;"],
            "warnings": [],
            "errors": [],
        },
    },
    response_text="Fixed a crash caused by invalid state transition.",
    summary="Crash fix with public API impact",
)

print(format_human_result(result))
print(result["summary_artifact"])
'@ | python -
```

## 預期輸出

human-readable output 至少應該出現：

```text
memory_candidate_detected=True
memory_candidate_signals=public_api_change
memory_promotion_considered=True
memory_closeout_decision=REVIEW_REQUIRED
memory_closeout_reason=...
```

這代表：

- 高價值候選有被看到
- promotion 有被考慮
- 沒有寫入 memory 時，不是黑箱

## 建議情境

至少跑下面 4 個情境。

### 情境 A：有 candidate，但需要 review

設定：

- `risk=high`
- `oversight=review-required`
- 有 `public_api_diff`、crash、regression 或其他候選訊號

預期：

- `memory_candidate_detected=True`
- `memory_promotion_considered=True`
- `memory_closeout_decision=REVIEW_REQUIRED`

### 情境 B：stateless session

把 contract 改成：

```python
"memory_mode": "stateless"
```

預期：

- `memory_promotion_considered=False`
- `memory_closeout_reason=memory_mode=stateless disables durable memory closeout`

### 情境 C：缺少 response_text

把 `response_text` 改成空字串或 `None`。

預期：

- 不建立 candidate snapshot
- `memory_closeout_reason` 會提到 `response_text missing`

### 情境 D：沒有 candidate

拿掉 `public_api_diff`，也不要放 crash / regression 類訊號。

預期：

- `memory_candidate_detected=False`
- 仍然有 `memory_closeout_decision`
- 仍然有 `memory_closeout_reason`

## Artifact 驗證

手動 closeout script 會印出 `summary_artifact` 路徑。
打開對應 JSON，應至少看到：

```json
{
  "memory_closeout": {
    "candidate_detected": true,
    "candidate_signals": ["public_api_change"],
    "promotion_considered": true,
    "decision": "REVIEW_REQUIRED",
    "reason": "..."
  }
}
```

這一步用來確認：

- 不只是 human output 有字串
- artifact 也真的帶了結構化 closeout decision

## 判讀原則

目前這條線修到的是：

- closeout decision observability
- no-write reason visibility
- 高價值候選 session 不再靜默消失

目前還**不是**：

- memory 一定自動寫入
- candidate taxonomy 已完整成熟
- consuming repo shared path 已全面穩定接入

## 一句話結論

如果 consuming repo 能穩定看到：

- `memory_candidate_detected`
- `memory_promotion_considered`
- `memory_closeout_decision`
- `memory_closeout_reason`

那就表示 `memory closeout visibility` 已經進到真實 repo 的 closeout 驗證面。
