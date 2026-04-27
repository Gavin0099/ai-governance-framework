# E1b Phase 2 — Lifecycle-Capable Repo 設置指南

> **對象**：已採用本治理框架、希望讓自己的 repo 進入 E1b Phase 2 metric 母體的外部 repo 維護者
> **目的**：說明如何讓你的 repo 被辨識為 `lifecycle_capable`，並確認你的 session 資料正在累積到有效的觀測 pool

---

## 什麼是 lifecycle_capable

Phase 2 readiness gate 只對 `lifecycle_capable` repo 計算 entropy / lifecycle_class。

`lifecycle_capable = true` 的條件：

1. `gate_policy.yaml` 中 **沒有** `skip_test_result_check: true`（預設 false 即可）
2. `skip_type` 未設定，或不是 `structural` / `temporary`
3. repo 有 Python test suite（可跑 pytest）

`lifecycle_capable = false`（被排除）：
- `skip_test_result_check: true` → 計入 `structural_skip` 或 `temporary_skip`
- `skip_type: structural` → 永遠不進 lifecycle 分析（C/C++、純文件 repo 等）
- `skip_type: temporary` → 暫時排除（等待採用補齊）

---

## Phase 2 readiness gate 目前條件

只統計 `lifecycle_capable` 子母體：

| 條件 | 閾值 | 說明 |
|------|------|------|
| 總 sessions | ≥ 20 | lifecycle_capable repos 的 session 總和 |
| 獨立 repo 數 | ≥ 3 | 有資料的 lifecycle_capable repos 數量 |
| non-stuck-absent 比例（v2） | ≥ 0.7 | lifecycle_class ≠ stuck_absent 的 repo 比例 |
| 最大單 repo 佔比 | ≤ 0.6 | 防止單一 repo 壟斷樣本 |
| lifecycle_active_ratio | ≥ 0.5 | 有非 stuck 生命周期的 repo 比例 |

> **注意**：`nondegenerate_ratio`（舊版）已廢棄，gate 改用 v2 的 `non_stuck_absent_ratio_v2`。

---

## 步驟一：確認 gate_policy.yaml 設定

你的 repo 需要有 `governance/gate_policy.yaml`：

```yaml
version: "1"
fail_mode: strict              # 或 permissive

# lifecycle_capable 的關鍵：不要加 skip_test_result_check: true
# skip_test_result_check: false  ← 預設值，可以不寫

# 如果你確實沒有 Python test suite，請用 skip 並說明原因：
# skip_test_result_check: true
# skip_type: structural          # C/C++ / 純文件等
```

**確認你的設定不包含**：
- `skip_test_result_check: true`
- `skip_type: structural` 或 `skip_type: temporary`

---

## 步驟二：確認 session_end_hook 在每次 session 後執行

每次 session 結束後，`session_end_hook.py` 必須被呼叫，才會寫入 canonical audit log。

```bash
# 在你的 repo 目錄下
python path/to/ai-governance-framework/runtime_hooks/session_end_hook.py \
  --project-root .
```

或透過 Codex / Claude Code adapter 自動觸發（詳見 `runtime_hooks/` 設置文件）。

### 確認 log 有在累積

```bash
# 應該在你的 repo 裡出現這個檔案
ls artifacts/runtime/canonical-audit-log.jsonl

# 查看最新幾筆
python -c "
import json
from pathlib import Path
lines = Path('artifacts/runtime/canonical-audit-log.jsonl').read_text().splitlines()
for l in lines[-3:]:
    print(json.dumps(json.loads(l), indent=2, ensure_ascii=False))
"
```

每筆 entry 的 `policy_provenance.fallback_used` 應為 `false`（代表你有有效的 gate_policy.yaml）。

---

## 步驟三：驗證你出現在 lifecycle_capable 子母體

**從 ai-governance-framework 目錄**執行：

```bash
# 指定你的 log 單獨分析
python scripts/analyze_e1b_distribution.py \
  --log-path /path/to/your-repo/artifacts/runtime/canonical-audit-log.jsonl

# 或合并多個 repo 的 log
python scripts/analyze_e1b_distribution.py \
  --log-path /path/to/your-repo/artifacts/runtime/canonical-audit-log.jsonl \
             artifacts/runtime/canonical-audit-log.jsonl
```

輸出中確認你的 repo 出現在：

```
=== Fleet Coverage ===
lifecycle_capable:
  - your-repo-name     sessions=N  lifecycle_class=stable_ok | transitioning_active
```

**你不應該出現在**：
```
structural_skip:       ← 代表 skip_type: structural
temporary_skip:        ← 代表 skip_type: temporary 或 skip=true 但未配置 test
```

---

## 步驟四：自動參與 framework 的多 repo 分析

如果你的 repo 和 `ai-governance-framework` 在**同一個父目錄下**，
`--auto-discover` 會自動找到你的 log：

```
parent/
├── ai-governance-framework/
│   └── artifacts/runtime/canonical-audit-log.jsonl
└── your-repo/
    └── artifacts/runtime/canonical-audit-log.jsonl  ← 自動被發現
```

執行：
```bash
cd ai-governance-framework
python scripts/analyze_e1b_distribution.py --auto-discover
```

你的 repo 會自動出現在分析結果中。

---

## lifecycle_class 值說明

| 值 | 含義 | 你應該看到 |
|----|------|-----------|
| `stable_ok` | 大多數 session artifact_state=ok，已收斂 | 健康目標狀態 |
| `transitioning_active` | 多樣 state，還沒收斂 | 正常，非錯誤 |
| `insufficient_evidence` | session 數太少（< 5），無法判斷 | 需要更多 session 累積 |
| `stuck_absent` | 大多數 session artifact 缺失，pattern 已凍結 | 代表 test runner 可能未正確設置 |

**`transitioning_active` 是中性觀察，不代表「正在改善」或「進展良好」。**

---

## 常見問題

### Q：我設了 `skip_test_result_check: false` 但仍出現在 structural_skip？

`skip_type` 欄位會覆蓋 `skip_test_result_check`。確認你的 `gate_policy.yaml` 沒有：
```yaml
skip_type: structural   # 這會讓你被排除
```

### Q：我的 lifecycle_class 一直是 insufficient_evidence？

需要累積至少 5 個 session。確認 `session_end_hook.py` 有在每次 session 結束後被呼叫。

### Q：我的 lifecycle_class 是 stuck_absent？

代表大多數 session 的 `artifact_state` 是 `absent`，且 pattern 已凍結。
可能原因：
1. pytest 沒有正確執行（test artifact 沒有產生）
2. `test_result_ingestor.py` 沒有在測試後被呼叫

---

## 目前 Phase 2 狀態

| 條件 | 現狀（2026-04-27） |
|------|------------------|
| lifecycle_capable repos | Bookstore-Scraper, SpecAuthority, ai-governance-framework（3 個）|
| total sessions | 待確認（需 ≥ 20） |
| non_stuck_absent_ratio_v2 | ai-governance-framework 為 stable_ok → v2 通過 |
| 門檻狀態 | Phase 2 仍在累積中，等真實 session 資料 |

如果你的 repo 成功進入 `lifecycle_capable`，請告知框架維護者，更新 [`memory/MEMORY.md`](../memory/) 的外部 repo 採用記錄。
