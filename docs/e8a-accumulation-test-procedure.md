# E8a 累積測試流程 — E1b 評估準備

**目的**：在多個 external repo 上跑 `session_end_hook`，累積 E8a canonical audit log，
讓 E8b trend 有足夠資料，才能客觀評估 E1b（canonical usage enforcement）是否有根據。

**不是目的**：驗證 governance 本身是否「正確」。這一輪跑的是 signal 收集，不是正確性判斷。

---

## E1b 評估前提（先釘住）

E1b 只有在以下條件都成立時才進入評估：

| 條件 | 量化 |
|------|------|
| 每個 repo 至少有 `window_size`（預設 20）筆 E8a log entries | 避免單次異常影響 ratio |
| signal_ratio 在多個 repo 一致偏高（>= 50%） | 代表系統性問題，不是個別 repo 操作失誤 |
| 跨 repo 觀察到相同 signal（e.g. `test_result_artifact_absent` 重複出現） | 代表 canonical path 真的沒被走到 |
| 至少覆蓋 Tier A + Tier B 各一個 repo | 避免只看單一 tier 的結論 |

**如果上述條件不滿足，E1b 不開工。**

---

## 本機可用 Repo

### 已 adopt（有 `governance/`、`contract.yaml`）

| Repo | 語言 | Tier 建議 | 備註 |
|------|------|-----------|------|
| `Bookstore-Scraper` | Python | B | 已測試過一次，適合多次 repeat |
| `cli` | C++ | B + skip_test_result_check | GTest XML，本地無 pytest；需 skip_test_result_check |
| `hp-oci-avalonia` | C# / .NET | B | .NET 生態，不同 test toolchain |

### 尚未 adopt（green-field）

| Repo | 語言 | Tier 建議 | 備註 |
|------|------|-----------|------|
| `Standard_ISP_Tool` | C/C++ | B + skip | firmware ISP，類似 cli |
| `gl_electron_tool` | JavaScript | B | Electron/Node，JS 生態 |

### 部分導入（有 AGENTS.md 但無 contract.yaml）

| Repo | 語言 | 狀態 | 建議 |
|------|------|------|------|
| `Ashfall` | ? | agents only | 先跑 readiness 確認再決定 |

---

## 前置設定

```powershell
# 啟動 framework venv（含 pyyaml）
cd e:\BackUp\Git_EE\ai-governance-framework
.venv\Scripts\Activate.ps1

# 確認 pyyaml 有安裝
python -c "import yaml; print('pyyaml ok')"

# 設定 framework path 變數（後面指令共用）
$FW = "e:\BackUp\Git_EE\ai-governance-framework"
```

---

## Phase 1：已 adopt repo — 直接開始累積 log

對已有 `governance/gate_policy.yaml` 的 repo，直接跑 session_end_hook。
**每次跑 = 一筆 E8a log entry**。

### 1-1 單次執行

```powershell
# Bookstore-Scraper
python $FW\governance_tools\session_end_hook.py \
  --project-root e:\BackUp\Git_EE\Bookstore-Scraper

# cli
python $FW\governance_tools\session_end_hook.py \
  --project-root e:\BackUp\Git_EE\cli

# hp-oci-avalonia
python $FW\governance_tools\session_end_hook.py \
  --project-root e:\BackUp\Git_EE\hp-oci-avalonia
```

輸出中觀察這幾個欄位：

```
gate_verdict=...             ← BLOCKED / NON-GATE-FAILURE / OK+ADVISORIES / OK
canonical_path_audit: ...    ← artifact_present / signals
canonical_audit_trend: ...   ← entries_read / signal_ratio / adoption_risk
[ADVISORY] ...               ← 具體 advisory 訊息
```

### 1-2 多次執行（累積 log）

每個 repo 至少要有 20 筆才有 trend 意義。
用 loop 快速累積（模擬多 session 的 footprint）：

```powershell
$REPOS = @(
    "e:\BackUp\Git_EE\Bookstore-Scraper",
    "e:\BackUp\Git_EE\cli",
    "e:\BackUp\Git_EE\hp-oci-avalonia"
)

foreach ($repo in $REPOS) {
    Write-Host "`n=== $repo ===" -ForegroundColor Cyan
    for ($i = 1; $i -le 5; $i++) {
        Write-Host "  run $i/5..."
        python $FW\governance_tools\session_end_hook.py --project-root $repo --format json |
            ConvertFrom-Json |
            Select-Object ok, gate_verdict, @{n="signal_ratio"; e={$_.canonical_audit_trend.signal_ratio}}, @{n="entries"; e={$_.canonical_audit_trend.entries_read}}
    }
}
```

---

## Phase 2：Green-field repo — Adopt 後累積

### 2-1 採用流程

```powershell
# Standard_ISP_Tool
python $FW\governance_tools\adopt_governance.py `
  --target e:\BackUp\Git_EE\Standard_ISP_Tool `
  --framework-root $FW

# gl_electron_tool
python $FW\governance_tools\adopt_governance.py `
  --target e:\BackUp\Git_EE\gl_electron_tool `
  --framework-root $FW
```

### 2-2 設定 gate_policy.yaml

**Standard_ISP_Tool**（C++，無本地 pytest）：

```powershell
$policy = @"
version: "1"
fail_mode: permissive
hook_coverage_tier: B
skip_test_result_check: true
blocking_actions:
  - production_fix_required
unknown_treatment:
  mode: block_if_count_exceeds
  threshold: 3
canonical_audit_trend:
  window_size: 20
  signal_threshold_ratio: 0.5
"@
$policy | Set-Content "e:\BackUp\Git_EE\Standard_ISP_Tool\governance\gate_policy.yaml"
```

**gl_electron_tool**（JS，可能有 jest/mocha）：

```powershell
$policy = @"
version: "1"
fail_mode: permissive
hook_coverage_tier: B
blocking_actions:
  - production_fix_required
unknown_treatment:
  mode: block_if_count_exceeds
  threshold: 3
canonical_audit_trend:
  window_size: 20
  signal_threshold_ratio: 0.5
"@
$policy | Set-Content "e:\BackUp\Git_EE\gl_electron_tool\governance\gate_policy.yaml"
```

### 2-3 Readiness 確認

```powershell
python $FW\governance_tools\external_repo_readiness.py `
  --repo e:\BackUp\Git_EE\Standard_ISP_Tool `
  --framework-root $FW `
  --format human

python $FW\governance_tools\external_repo_readiness.py `
  --repo e:\BackUp\Git_EE\gl_electron_tool `
  --framework-root $FW `
  --format human
```

### 2-4 開始累積

同 Phase 1 的方式，對這兩個 repo 各跑 5 次以上。

---

## Phase 3：Log 檢查 — 看 E8a 資料品質

### 3-1 看單一 repo 的 audit log

```powershell
$repo = "e:\BackUp\Git_EE\Bookstore-Scraper"
$logPath = "$repo\artifacts\runtime\canonical-audit-log.jsonl"

if (Test-Path $logPath) {
    Get-Content $logPath |
        ForEach-Object { $_ | ConvertFrom-Json } |
        Select-Object timestamp_utc, @{n="signals"; e={$_.signals -join ", "}}, gate_blocked |
        Format-Table -AutoSize
} else {
    Write-Host "Log 不存在：$logPath"
}
```

### 3-2 看所有 repo 的 entry 數量

```powershell
@(
    "Bookstore-Scraper",
    "cli",
    "hp-oci-avalonia",
    "Standard_ISP_Tool",
    "gl_electron_tool"
) | ForEach-Object {
    $logPath = "e:\BackUp\Git_EE\$_\artifacts\runtime\canonical-audit-log.jsonl"
    $count = if (Test-Path $logPath) {
        (Get-Content $logPath | Measure-Object -Line).Lines
    } else { 0 }
    Write-Host "$_  entries=$count"
}
```

### 3-3 計算 signal_ratio（手動驗算 E8b）

```powershell
$repo = "e:\BackUp\Git_EE\Bookstore-Scraper"
$entries = Get-Content "$repo\artifacts\runtime\canonical-audit-log.jsonl" |
    ForEach-Object { $_ | ConvertFrom-Json }

$window = $entries | Sort-Object timestamp_utc | Select-Object -Last 20
$withSignals = ($window | Where-Object { $_.signals.Count -gt 0 }).Count
$ratio = if ($window.Count -gt 0) { [math]::Round($withSignals / $window.Count, 2) } else { 0 }

Write-Host "entries_in_window=$($window.Count)  with_signals=$withSignals  ratio=$ratio"
```

---

## Phase 4：E1b 評估 Checklist

跑完 Phase 1–3 後，填寫以下 checklist：

```
日期：___________

[ ] Bookstore-Scraper  entries >= 20  signal_ratio = ___  adoption_risk = ___
[ ] cli                entries >= 20  signal_ratio = ___  adoption_risk = ___
[ ] hp-oci-avalonia    entries >= 20  signal_ratio = ___  adoption_risk = ___
[ ] Standard_ISP_Tool  entries >= 20  signal_ratio = ___  adoption_risk = ___
[ ] gl_electron_tool   entries >= 20  signal_ratio = ___  adoption_risk = ___

觀察到的高頻 signal：
  - ___
  - ___

跨 repo 一致性：
  [ ] 多個 repo 出現相同 signal（代表系統性問題）
  [ ] 只有個別 repo 有 signal（代表操作問題，非框架問題）

Tier 覆蓋：
  [ ] Tier A 至少一個 repo 資料足夠
  [ ] Tier B 至少一個 repo 資料足夠

E1b 開工條件：
  [ ] 上述全部滿足 → 可開始 E1b 評估
  [ ] 尚未滿足 → 繼續累積，下次 sprint 再評估
```

---

## 推薦的測試 Repo Profile

### 本機（已有）

| Repo | 推薦理由 | 預期主要 signal |
|------|----------|-----------------|
| `Bookstore-Scraper` | Python，Tier B，已有 base — 最快出 signal | closeout_evaluation advisory |
| `cli` | C++，需 skip_test_result_check — 測試 structural absence opt-out | test_result_artifact_absent suppressed |
| `hp-oci-avalonia` | C# / Avalonia — 測試 non-Python 生態的 canonical footprint | canonical_interpretation_missing |
| `gl_electron_tool` | JS — 測試 JS 生態 + 無 Python test artifact | test_result_artifact_absent |
| `Standard_ISP_Tool` | firmware，類 cli — 驗證跨 C++ project signal 一致性 | 同 cli |

### 公開 GitHub Repo（如需更多樣本）

以下均為無 governance 的 green-field 場景，適合測試 adoption signal 的完整路徑：

| Repo | 語言 | 特性 |
|------|------|------|
| `psf/requests` | Python | 有完整 pytest，最乾淨的「應該能走 canonical path」基準 |
| `pallets/flask` | Python | 中型專案，有 tests/ 但結構複雜 |
| `microsoft/terminal` | C++ | 大型 C++ + GTest，測試 skip_test_result_check 適用性 |
| `nickvdyck/webjob-sdk` | C# | .NET 中型專案，類 hp-oci-avalonia |

> 使用公開 repo 時：clone 到本機後用 `adopt_governance.py` 導入，
> **不要 push governance 檔案到公開 repo**（只在 local branch 測試）。

---

## 注意事項

1. **不要用同一個 session ID 重複 commit**  
   每次 session_end_hook 會用 timestamp 產生 session_id，多次跑不會衝突。

2. **log 上限 500 筆後自動 rotation**  
   `canonical-audit-log.jsonl` 超過 500 筆會保留最新 500 筆，不會無限增長。

3. **E8a log 不是 gate**  
   log 寫入失敗只會產生 advisory warning，不影響 `gate_verdict`。

4. **E1b 評估是 deliberate decision，不是自動觸發**  
   `adoption_risk=True` 出現 ≠ 立刻開工 E1b。
   需要 human review：severity 夠高嗎？原因是系統性還是操作性？

5. **`hook_coverage_tier` 未宣告 = Tier A fallback（最嚴格）**  
   未宣告的 repo 會把 `closeout_file_missing` 當成 violation（`ok=False`），
   而非 advisory。這不代表 governance 判斷是錯的——它反映的是「沒有宣告 = 不知道你的情況 = 保守處理」。
   **任何 repo 在納入 E8a 累積測試前，都應先在 `gate_policy.yaml` 宣告 `hook_coverage_tier`。**

6. **signal_ratio 高但 skip 剛宣告 = 歷史 entries 尚未 flush**  
   新加入 `skip_test_result_check: true` 後，舊 window entries 仍記錄著有 signal 的歷史。
   ratio 會隨後續 clean run 自然稀釋，不需要手動清 log。
   觀察 `adoption_risk` 從 True 降回 False 的速度，可以驗算 window_size 設定是否合理。

---

## 第一輪測試紀錄（2026-04-14）

**執行結果與決策：**

| Repo | 發現的問題 | 採取的行動 | 修正後 verdict |
|------|-----------|-----------|---------------|
| `Bookstore-Scraper` | `hook_coverage_tier` 未宣告 → Tier A fallback → `ok=False` | 宣告 `hook_coverage_tier: B` | `OK+ADVISORIES` ✅ |
| `cli` | 同上 | 同上 | `OK+ADVISORIES` ✅ |
| `hp-oci-avalonia` | 同上 | 同上 | `OK+ADVISORIES` ✅ |
| `gl_electron_tool` | `skip_test_result_check` 未設 → 100% signal_ratio | 加入 `skip_test_result_check: true` | signals=[] （ratio 稀釋中）✅ |
| `Standard_ISP_Tool` | 正常，tier=B + skip 均已設 | 無需動作 | `OK+ADVISORIES` ✅ |

**E1b 條件評估（第一輪）：**
- entries 均 < 20：❌ 未達標
- signal_ratio 多 repo 一致 >= 50%：❌ 修正後均低於門檻
- 跨 repo 相同 signal：✅（`test_result_artifact_absent` 出現於多個 repo，但 skip 宣告後已抑制）
- **結論：E1b 不開工。繼續累積至每 repo >= 20 筆。**
