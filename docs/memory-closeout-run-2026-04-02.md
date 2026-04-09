# Manual Memory Closeout Check — 2026-04-02

## 狀態

已在官方 framework source 上通過 `memory closeout visibility` 驗證。

## 測試日期

- Local date: `2026-04-02`
- Session ID: `manual-memory-closeout-check`

## Framework Source

- Official remote: `https://github.com/Gavin0099/ai-governance-framework.git`
- Verified remote HEAD: `dea37c5c27538f9b04ce3987dba50eab41633337`
- Test path: `additional/ai-governance-framework-gavin0099`

## 背景

先前曾用 `https://github.com/GavinWu672/ai-governance-framework` 重跑同一份驗證，但那個來源當時的 `main` 仍停在較舊 commit，尚未包含 `memory closeout visibility` 相關變更。

這次改用官方 `Gavin0099` remote 後，才驗到新版 observability：

- human output 出現 `memory_candidate_detected`
- human output 出現 `memory_promotion_considered`
- human output 出現 `memory_closeout_decision`
- summary artifact 寫入結構化 `memory_closeout`

## 測試目的

驗證 `run_session_end` 是否能：

- 完成手動 closeout flow
- 輸出 human-readable memory closeout visibility
- 在 summary artifact 中寫入結構化 `memory_closeout`

測試條件：

- `memory_mode="candidate"`
- `oversight="review-required"`
- `risk="high"`
- `rules=["common", "refactor"]`
- `public_api_diff.added=["public int Ping() => 0;"]`

## 執行方式

```powershell
$env:PYTHONPATH="additional/ai-governance-framework-gavin0099"

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

## Human Output 結果

重點欄位如下：

```text
memory_candidate_detected=True
memory_candidate_signals=public_api_change
memory_promotion_considered=True
memory_closeout_decision=REVIEW_REQUIRED
memory_closeout_reason=High-risk sessions require human review before memory promotion.
```

這表示：

- 這次 session 被視為值得進 closeout consideration 的 candidate
- promotion decision 確實有發生
- 最終沒有 auto-promote 的原因是 high-risk session 需要 human review

## Summary Artifact 結果

檔案：

- `artifacts/runtime/summaries/manual-memory-closeout-check.json`

核心欄位：

```json
"memory_closeout": {
  "candidate_detected": true,
  "candidate_signals": [
    "public_api_change"
  ],
  "promotion_considered": true,
  "snapshot_created": true,
  "decision": "REVIEW_REQUIRED",
  "promoted": false,
  "reason": "High-risk sessions require human review before memory promotion."
}
```

## 產出 artifact

- Summary: `artifacts/runtime/summaries/manual-memory-closeout-check.json`
- Candidate: `artifacts/runtime/candidates/manual-memory-closeout-check.json`
- Curated: `artifacts/runtime/curated/manual-memory-closeout-check.json`
- Verdict: `artifacts/runtime/verdicts/manual-memory-closeout-check.json`
- Trace: `artifacts/runtime/traces/manual-memory-closeout-check.json`
- Snapshot: `memory/candidates/session_20260402T100720Z.json`

## 驗證結果

本次驗證已成立：

- `memory_candidate_detected=True`
- `memory_candidate_signals=public_api_change`
- `memory_promotion_considered=True`
- `memory_closeout_decision=REVIEW_REQUIRED`
- `memory_closeout_reason=High-risk sessions require human review before memory promotion.`
- summary artifact 含有結構化 `memory_closeout`

## 結論

這次測試證明：在官方 framework source `Gavin0099/ai-governance-framework@dea37c5c27538f9b04ce3987dba50eab41633337` 上，`memory closeout visibility` 已經成立。  
系統不只會產生 closeout 結果，還會清楚說明：

- 是否有 candidate
- 是否進 promotion consideration
- 最後決策是什麼
- 為什麼沒有直接寫入 durable memory
