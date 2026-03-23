# Minimum Legal Schema Reference

> **驗證基礎**: ziwei-service、governance_tools（碰撞案例）、Mirra（通過案例）
> **目的**: 讓使用者不看 source code 也能寫出正確的治理檔案
> **原則**: 最小可寫 × 最小可過 × 最小可理解

---

## 如何使用這份文件

如果你在跑 `adopt_governance.py` 之後，某個 check 還是 FAIL，這份文件告訴你：
- 每個檔案的欄位語義是什麼
- 哪些欄位由工具自動生成、不建議手改
- 哪些欄位需要你填入 repo-specific 內容

**最快的路**：跑 adopt，讓工具生成預設值，只改標記 `← 需填` 的欄位。

---

## 1. contract.yaml

### 最小合法範例

```yaml
name: my-service-contract
plugin_version: "1.0.0"
framework_interface_version: "1"
framework_compatible: ">=1.0.0,<2.0.0"
domain: my-service
documents:
  - AGENTS.base.md
  - PLAN.md
ai_behavior_override:
  - AGENTS.base.md
rule_roots:
validators:
```

### 欄位說明

| 欄位 | 必填 | 說明 |
|------|------|------|
| `name` | ✅ | repo 名稱，加 `-contract` 後綴，無空格。`adopt` 會自動用 repo 目錄名填入 |
| `plugin_version` | ✅ | 此 contract 的版本，從 `"1.0.0"` 開始即可 |
| `framework_interface_version` | ✅ | 固定填 `"1"`，代表你使用的 framework 介面版本 |
| `framework_compatible` | ✅ | 固定填 `">=1.0.0,<2.0.0"`，除非你明確需要限制版本 |
| `domain` | ✅ | repo 的領域識別符，小寫、無空格。`adopt` 會用 repo 目錄名填入 |
| `documents` | 建議 | 列出 AGENTS.base.md 和 PLAN.md，讓 drift checker 確認它們存在 |
| `ai_behavior_override` | 建議 | 至少列 AGENTS.base.md，確保框架行為規則被引用 |
| `rule_roots` | 選填 | 若有自定義規則目錄（如 `governance/rules/`）才需要填；空白合法 |
| `validators` | 選填 | 若有自定義 validator 腳本才填；`validators:` 空白行或 `[]` 都合法 |

### 常見錯誤

```yaml
# ❌ 觸發 check #13 contract_no_placeholders
name: <repo-name>-contract
domain: <domain>

# ❌ validators: [] 現在已修正（v1.1.0+），但舊版會報 phantom path 錯誤
validators: []   # ← 空行或省略 key 都比 [] 更保險

# ❌ 不支援嵌套結構
documents:
  main:
    - AGENTS.base.md    # ← 這會拋出 parse error

# ✅ 只支援平面列表
documents:
  - AGENTS.base.md
```

### 不阻塞 readiness 的 False 狀態

- `framework_version_known = False`：無 `governance/framework.lock.json` 時預期出現，不影響 `ready`
- `hooks_ready = False`：hooks 是部署便利性，不是 governance gate，不影響 `ready`

---

## 2. .governance/baseline.yaml

### 最小合法範例（由 `adopt` 自動生成）

```yaml
schema_version: "1"
baseline_version: 1.0.0
framework_version: v1.0.0-alpha
initialized_by: governance_tools/adopt_governance.py
initialized_at: 2026-03-22T00:00:00+00:00
source_commit: abc1234

sha256.AGENTS.base.md: <hash>
sha256.PLAN.md: <hash>
sha256.contract.yaml: <hash>

overridable.PLAN.md: overridable
overridable.contract.yaml: overridable

# CONTRACT layer — values here override validation thresholds
# plan_freshness_threshold_days: 14

plan_section_inventory:
  - "## Current Phase"
  - "## Active Sprint"
```

### 欄位分層語義

```
PROVENANCE  — 記錄這個 baseline 是誰在何時怎麼生成的
  initialized_by       工具路徑
  initialized_at       ISO 8601 timestamp
  source_commit        git SHA（確保可追溯）

INTEGRITY   — 記錄受保護檔案的 hash，用於 drift 偵測
  sha256.AGENTS.base.md   唯一 protected 檔案，不得手改
  sha256.PLAN.md          overridable，hash 變更不阻斷
  sha256.contract.yaml    overridable，hash 變更不阻斷

CONTRACT    — 覆蓋 validation 行為的政策值（目前只有一個）
  plan_freshness_threshold_days   覆蓋 freshness 閾值（預設 14d）
                                  若設定值 > 14 會出現 guardrail warning

OBSERVED    — adoption/refresh 時觀察到的狀態快照
  plan_section_inventory  PLAN.md 的 ## heading 列表
  plan_path               非標準位置的 PLAN.md 路徑（非 root 時才出現）
```

### 哪些欄位不要手改

| 欄位 | 原因 |
|------|------|
| `sha256.*` | 手改會立刻觸發 `protected_files_unmodified` FAIL |
| `initialized_at` | 用於 `baseline_yaml_freshness` 計算，手改會造成誤判 |
| `plan_section_inventory` | 改了但 PLAN.md 沒跟著改會觸發 `plan_inventory_current` warning |

### 唯一建議手加的欄位

```yaml
# 若你的 repo 要求 PLAN.md 必須有特定 section：
plan_required_sections:
  - "## Current Phase"
  - "## Active Sprint"
```

這會啟動 `plan_required_sections_present` check，缺少任一 section 時 drift 會 FAIL。
`adopt` 預設不設這個欄位（不強制任何 mandate）。

---

## 3. AGENTS.md（adopt 後的預設語義）

### 預設結構

`adopt` 生成的 AGENTS.md 包含四個 `governance:key` section：

```markdown
## Repo-Specific Risk Levels
<!-- governance:key=risk_levels -->
N/A

## Must-Test Paths
<!-- governance:key=must_test_paths -->
N/A

## L1 → L2 Escalation Triggers
<!-- governance:key=escalation_triggers -->
N/A

## Repo-Specific Forbidden Behaviors
<!-- governance:key=forbidden_behaviors -->
N/A
```

### `governance:key` 的作用

這些 anchor 讓 drift checker（check #14 `agents_sections_filled`）知道哪些 section 代表「repo-specific 內容」。

**通過的條件**：section 內有任何一行非空、非 HTML comment 的文字。
`N/A`（純文字，不含 "fill in or replace" 尾綴）就足以讓 check 通過。

> ⚠️ **注意**：`N/A — fill in or replace with ...` 這種帶模板尾綴的寫法會被 checker 識別為未填寫的占位符，**不算通過**。
> adopt 工具生成的模板已使用純 `N/A`（2026-03-23 後的版本）。

**什麼時候需要填真實內容**：

| Section | 何時應填實內容 |
|---------|---------------|
| `risk_levels` | 有 auth、payment、migration 等高風險路徑時 |
| `must_test_paths` | 有明確不能 skip test 的目錄時 |
| `escalation_triggers` | 有 L2 evidence 需求的場景時 |
| `forbidden_behaviors` | 有超出框架基線的限制時 |

對於 prototype / minimal repo，保留 `N/A` 完全合法，drift 不會 FAIL。

### AGENTS.base.md vs AGENTS.md

| 檔案 | 性質 | 可修改？ |
|------|------|---------|
| `AGENTS.base.md` | protected — 框架提供的不可協商規則 | ❌ 不得修改，`adopt` 每次會刷新 |
| `AGENTS.md` | overridable — repo-specific 延伸 | ✅ 自由修改，hash 變更不影響 drift |

---

## 4. PLAN.md freshness 最小合法格式

### 最小合法寫法

```markdown
> **最後更新**: 2026-03-22
> **Owner**: your-name
> **Freshness**: Sprint (7d)
```

這三行必須出現在 PLAN.md **開頭附近**（前 30 行內）。

### Freshness policy 的格式

```
Sprint (7d)     ← 建議。Sprint 週期，7 天閾值
Release (30d)   ← Release 週期，30 天閾值
Custom (14d)    ← 自定義，14 天閾值
```

格式規則：`<Label> (<N>d)`，N 是天數，括號必須是半形。

### Freshness 閾值的優先順序

```
1. PLAN.md Freshness header 的 N 值         ← 最高優先（明確聲明 policy）
2. baseline.yaml CONTRACT 層的
   plan_freshness_threshold_days            ← 覆蓋 framework default
3. framework default: 14d                  ← 最低優先
```

Drift output 會標示來源：
- `PLAN.md policy: 7d` — 從 header 讀到
- `contract override: 30d` — 從 baseline CONTRACT 層讀到
- `framework default: 14d` — 兩者皆無時套用

**若 override > 14d**，drift 會出現 guardrail warning（不 FAIL，只提醒偏離 framework default）。

### 常見錯誤

```markdown
❌ **Freshness**: 7d          ← 缺少 label，無法解析 policy
❌ **Freshness**: Sprint(7d)  ← 缺少空格
❌ **freshness**: Sprint (7d) ← 欄位名大小寫錯誤（需大寫 F）

✅ **Freshness**: Sprint (7d)
```

---

## 快速對照：adopt 後的預期 check 狀態

| Check | adopt 後預期 | 說明 |
|-------|-------------|------|
| `baseline_yaml_present` | ✅ PASS | 工具自動生成 |
| `baseline_version_known` | ✅ PASS | 工具自動填入 |
| `framework_version_current` | ✅ PASS | 工具自動比對 |
| `source_commit_recorded` | ⚠️ warning | 需要 git commit 存在；首次 adopt 前若無 commit 則 warning |
| `protected_files_present` | ✅ PASS | 工具複製 AGENTS.base.md |
| `protected_files_unmodified` | ✅ PASS | 剛複製，hash 一致 |
| `protected_file_sentinel_present` | ✅ PASS | AGENTS.base.md 含 sentinel |
| `contract_required_fields_present` | ✅ PASS | 工具從 template 生成 |
| `contract_agents_base_referenced` | ✅ PASS | template 預設包含 |
| `contract_no_placeholders` | ✅ PASS | 工具自動替換 `<repo-name>` / `<domain>` |
| `contract_not_framework_copy` | ✅ PASS | 工具替換後名稱不同 |
| `plan_required_sections_present` | ✅ PASS | 無 mandate 預設通過 |
| `agents_sections_filled` | ✅ PASS | template 預設含純 `N/A`（不含模板尾綴） |
| `plan_freshness` | ✅ PASS | 工具寫入當天日期 |
| `plan_inventory_current` | ✅ PASS | 剛 adopt，inventory 與 PLAN.md 一致 |
| `baseline_yaml_freshness` | ✅ PASS | 剛生成 |

**16/16 PASS 是 adopt 後的正常狀態**。如果 `source_commit_recorded` 仍為 FAIL，表示 git repo 尚無 commit，或 baseline 在 commit 前生成；執行一次 commit 後重跑 drift check 即可轉為 PASS。

---

## 相關工具

```bash
# 初始採納
python governance_tools/adopt_governance.py --target /path/to/repo

# 預覽不寫入
python governance_tools/adopt_governance.py --target . --dry-run

# 更新 hash（檔案修改後）
python governance_tools/adopt_governance.py --target . --refresh

# 查看完整 drift 報告
python governance_tools/governance_drift_checker.py --repo . --format human

# 查看 readiness（含 drift）
python governance_tools/external_repo_readiness.py --repo . --format human
```
