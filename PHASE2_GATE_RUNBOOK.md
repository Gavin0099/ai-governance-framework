# Phase 2 Gate Runbook

> 作者：自動生成 2026-04-15
> 目標：Phase 2 readiness gate 五個條件通過（NOT_READY → READY）
> 前提：所有指令從 `E:\BackUp\Git_EE\ai-governance-framework` 執行

---

## 當前缺口（精確數字，2026-04-15）

```
[PASS] total sessions >= 20       : actual=44     ← 已過
[FAIL] distinct repos >= 3        : actual=2      ← 差 1 個 repo
[FAIL] non-degenerate ratio >= 0.7: actual=0.50   ← 需 3/3 全過，目前 1/2
[FAIL] dominant repo <= 0.6       : actual=0.977  ← BS 佔 97.7%，需 ~30 個新 sessions
[NOTE] lifecycle-active >= 0.5    : actual=?      ← Condition 5 已重新設計（見下方說明）
```

lifecycle-capable pool（目前）：
- **Bookstore-Scraper**: 43 sessions (`stable_ok`)  ← 唯一成熟 baseline
- **ai-governance-framework**: 1 session (`mixed_active`, artifact=absent)  ← 自己沒跑 ingestor

temporary_skip（不計入 Phase 2 gate）：
- SpecAuthority: 25 sessions（全部 absent，skip=true）← 主要目標

---

## Stage 0：Pre-flight（今天就做，5 分鐘）

### S0-1 確認工具版本

```powershell
cd E:\BackUp\Git_EE\ai-governance-framework

# 確認 framework 目前 HEAD
git log --oneline -3
```

### S0-2 確認 artifacts 目錄存在

```powershell
# SpecAuthority
New-Item -ItemType Directory -Force "E:\BackUp\Git_EE\SpecAuthority\artifacts\runtime\test-results"

# ai-governance-framework 本身
New-Item -ItemType Directory -Force "E:\BackUp\Git_EE\ai-governance-framework\artifacts\runtime\test-results"
```

### S0-3 快速確認 SpecAuthority gate_policy 現況

```powershell
Get-Content E:\BackUp\Git_EE\SpecAuthority\governance\gate_policy.yaml
```

預期看到 `skip_test_result_check: true` 和 `skip_type: temporary`（Layer 2 完成前不得動）

---

## Stage 1：SpecAuthority Layer 1（第一次執行）

> ⚠️ 目標：跑通整條鏈，確認 artifact_state=ok
> ⚠️ 注意：這是 Layer 1 第一次，不算「穩定」，不要動 gate_policy.yaml

### S1-1 跑 pytest

```powershell
cd E:\BackUp\Git_EE\SpecAuthority

python -m pytest spec_truth/ --tb=short 2>&1 | Out-File .\artifacts\pytest_output.txt -Encoding utf8

# 確認測試結果
Get-Content .\artifacts\pytest_output.txt | Select-String "passed|failed|error" | Select-Object -Last 5
```

**預期**：`498 passed`（或接近）

記錄：
- [ ] 通過：________（待填入日期）
- [ ] pytest 最後一行：`________________ passed`

### S1-2 跑 ingestor

```powershell
cd E:\BackUp\Git_EE\ai-governance-framework

python governance_tools/test_result_ingestor.py `
  --file E:\BackUp\Git_EE\SpecAuthority\artifacts\pytest_output.txt `
  --kind pytest-text `
  --out E:\BackUp\Git_EE\SpecAuthority\artifacts\runtime\test-results\latest.json
```

**預期**：無 error，生成 artifact 檔案

驗證：
```powershell
Test-Path "E:\BackUp\Git_EE\SpecAuthority\artifacts\runtime\test-results\latest.json"
# 應輸出 True

Get-Content "E:\BackUp\Git_EE\SpecAuthority\artifacts\runtime\test-results\latest.json" | ConvertFrom-Json | Select-Object total_tests, passed, failed, verdict
```

記錄：
- [ ] artifact 生成：True / False
- [ ] verdict：________

### S1-3 跑 session_end_hook

```powershell
cd E:\BackUp\Git_EE\ai-governance-framework

python governance_tools/session_end_hook.py --project-root E:\BackUp\Git_EE\SpecAuthority
```

**Pass 條件**：
- [ ] 輸出含 `artifact_state=ok`（表示 test result artifact 讀到了）
- [ ] 不出現 `artifact_state=absent` 或 `malformed`
- [ ] `gate_verdict` 不是 `BLOCKED`

記錄（S1 第一次）：
- 日期：__________
- artifact_state：__________
- gate_verdict：__________

---

## Stage 1b：agf 自身 session（同一天可做）

> 目的：讓 agf 本身也產生 lifecycle ok session，改善 non-degenerate ratio

### agf-1 跑自己的測試

```powershell
cd E:\BackUp\Git_EE\ai-governance-framework

python -m pytest tests/ -q --tb=short 2>&1 | Out-File .\artifacts\pytest_output.txt -Encoding utf8

# 確認
Get-Content .\artifacts\pytest_output.txt | Select-String "passed|failed" | Select-Object -Last 3
```

### agf-2 ingestor

```powershell
cd E:\BackUp\Git_EE\ai-governance-framework

python governance_tools/test_result_ingestor.py `
  --file .\artifacts\pytest_output.txt `
  --kind pytest-text `
  --out .\artifacts\runtime\test-results\latest.json
```

### agf-3 session_end_hook（對自己）

```powershell
python governance_tools/session_end_hook.py --project-root .
```

**Pass 條件**：
- [ ] artifact_state=ok
- [ ] agf 在 canonical-audit-log.jsonl 累積了新的 ok entry

---

## Stage 2：Layer 1 穩定確認（第二次，不同 session）

> ⚠️ 必須間隔至少 1 天（隔天做）
> ⚠️ 至少 1 次來自自然工作流（不是專門跑 probe）

**重複 S1-1 到 S1-3 的全部步驟**，然後記錄：

記錄（S2 第二次）：
- 日期：__________（必須與第一次不同天）
- artifact_state：__________
- gate_verdict：__________

**Layer 1 穩定判定**：
- [ ] 兩次都是 artifact_state=ok
- [ ] 日期不同（不同 session）
- [ ] 至少一次是在做 SpecAuthority 實際工作時自然跑到的，不是專門 probe

**Layer 1 穩定後才執行 Stage 3。**

---

## Stage 3：移除 temporary skip（Layer 2 — Layer 1 穩定後才做）

> ⚠️ 先確認 Layer 1 已穩定（見上方兩欄均有記錄）

### S3-1 編輯 SpecAuthority gate_policy

```powershell
notepad E:\BackUp\Git_EE\SpecAuthority\governance\gate_policy.yaml
```

修改以下兩行：
```yaml
# 改為：
skip_test_result_check: false   # 原本是 true，現在移除 skip

# 移除或改為：
# skip_type: temporary   ← 整行刪除（或改成 lifecycle_capable 不寫）
```

修改後 gate_policy.yaml 相關部分應為：
```yaml
version: "1"
fail_mode: permissive
hook_coverage_tier: B
skip_test_result_check: false
# skip_type 行 → 刪除

blocking_actions:
  - production_fix_required

unknown_treatment:
  mode: block_if_count_exceeds
  threshold: 3

canonical_audit_trend:
  window_size: 20
  signal_threshold_ratio: 0.5
```

### S3-2 再跑一次完整鏈確認

```powershell
cd E:\BackUp\Git_EE\SpecAuthority
python -m pytest spec_truth/ --tb=short 2>&1 | Out-File .\artifacts\pytest_output.txt -Encoding utf8

cd E:\BackUp\Git_EE\ai-governance-framework
python governance_tools/test_result_ingestor.py `
  --file E:\BackUp\Git_EE\SpecAuthority\artifacts\pytest_output.txt `
  --kind pytest-text `
  --out E:\BackUp\Git_EE\SpecAuthority\artifacts\runtime\test-results\latest.json

python governance_tools/session_end_hook.py --project-root E:\BackUp\Git_EE\SpecAuthority
```

**Pass 條件**：
- [ ] artifact_state=ok
- [ ] SpecAuthority 出現在 lifecycle_capable pool（驗證見 Stage 4 gate check）
- [ ] lifecycle_class 不是 stuck_absent

### S3-3 commit SpecAuthority gate_policy 變更

```powershell
cd E:\BackUp\Git_EE\SpecAuthority
git add governance/gate_policy.yaml
git commit -m "feat(governance): wire test lifecycle — remove temporary skip

Layer 1 stability confirmed:
  - first run: <填入日期>  artifact_state=ok
  - second run: <填入日期>  artifact_state=ok (different session)

Layer 2: temporary skip removed
  skip_test_result_check: true -> false
  skip_type: temporary -> (removed)

Refs: ai-governance-framework PLAN.md SpecAuthority wiring plan"
```

---

## Stage 4：累積 sessions（Dominance 問題）

> 現況：Bookstore-Scraper 佔 97.7%（43/44），需要降到 ≤ 60%
> 計算：需要 SA + agf 合計達到 ~29+ 個 lifecycle_capable sessions
> 時間估計：每天 2 個 sessions（SA 1 + agf 1）→ 約 15 天

### 每天要做的事（Stage 4 loop）

**SpecAuthority（每次 SpecAuthority 工作時）：**
```powershell
cd E:\BackUp\Git_EE\SpecAuthority
python -m pytest spec_truth/ --tb=short 2>&1 | Out-File .\artifacts\pytest_output.txt -Encoding utf8

cd E:\BackUp\Git_EE\ai-governance-framework
python governance_tools/test_result_ingestor.py `
  --file E:\BackUp\Git_EE\SpecAuthority\artifacts\pytest_output.txt `
  --kind pytest-text `
  --out E:\BackUp\Git_EE\SpecAuthority\artifacts\runtime\test-results\latest.json

python governance_tools/session_end_hook.py --project-root E:\BackUp\Git_EE\SpecAuthority
```

**agf（每次做 agf 工作時）：**
```powershell
cd E:\BackUp\Git_EE\ai-governance-framework
python -m pytest tests/ -q --tb=short 2>&1 | Out-File .\artifacts\pytest_output.txt -Encoding utf8

python governance_tools/test_result_ingestor.py `
  --file .\artifacts\pytest_output.txt `
  --kind pytest-text `
  --out .\artifacts\runtime\test-results\latest.json

python governance_tools/session_end_hook.py --project-root .
```

### Dominance 進度追蹤公式

```
目前：43 / (43 + N_SA + N_agf) ≤ 0.6
需要：N_SA + N_agf ≥ 29

進度：累積 ___ 個 SA lifecycle_capable sessions + ___ 個 agf lifecycle_capable sessions = ___/29
```

---

## Stage 5：Gate Check（條件達成後驗證）

```powershell
cd E:\BackUp\Git_EE\ai-governance-framework
$env:PYTHONIOENCODING="utf-8"
python scripts/analyze_e1b_distribution.py --auto-discover
```

**五個條件驗收：**
- [ ] total sessions ≥ 20 : PASS（已過）
- [ ] distinct repos ≥ 3  : ____（Stage 3 後應 PASS）
- [ ] non-degenerate ≥ 0.7: ____（Stage 1b 後應有改善）
- [ ] dominance ≤ 0.6     : ____（Stage 4 累積後）
- [ ] lifecycle-active ≥ 0.5: ____（lifecycle_capable repos 中，不是 stuck_absent 的比例）

---

## Condition 5 重新設計（lifecycle_active_ratio 取代 unique_pattern_ratio）

**原指標問題：** `unique_pattern_ratio` 是 non-identifiable metric。

- 健康 repo 的 session fingerprint 幾乎全是 `(ok, [], False)` → ratio 永遠低
- 同一指標對「健康」和「不健康」給出同一訊號 → 無判別能力，不得當 gate blocker

**新指標（已實施）：** `lifecycle_active_ratio`

```
= repos 中 lifecycle_class != stuck_absent 的數量 / 全部 lifecycle_capable repos
```

| 情境 | ratio | gate |
|---|---|---|
| 全 stable_ok fleet | 1.0 | PASS ✓ |
| 2/3 stable_ok + 1/3 stuck_absent | 0.67 | PASS ✓ |
| 全 stuck_absent fleet | 0.0 | FAIL ✓（正確指出採用失敗）|

**threshold: `>= 0.5`**。`unique_pattern_ratio` 保持計算，在 `[INFO]` 顯示，但不再危害 gate。

---

## 快速進度總覽

| Stage | 行動 | 預計時間 | 目標 Gate 條件 |
|---|---|---|---|
| S0 | Pre-flight | 今天 5 分鐘 | 前置確認 |
| S1+1b | SpecAuthority Layer 1 (第一次) + agf 自身 | 今天 20 分鐘 | 條件 3 部分改善 |
| S2 | Layer 1 (第二次，不同天) | 明天+ | Layer 1 穩定確認 |
| S3 | 移除 skip → Layer 2 完成 | 明天+ (Layer 1 穩定後) | 條件 2 PASS |
| S4 | 累積 sessions (約 15 天) | 兩周 | 條件 4 PASS |
| S5 | Gate check | 累積後 | 確認 1-5 全 PASS |

**誠實預估**：條件 1-4 通過需要約 2-3 週。
條件 5（lifecycle_active_ratio）成功擴母體即自動通過：lifecycle_capable pool 擴到 3 個 repo 且都非 stuck_absent → ratio = 1.0。
