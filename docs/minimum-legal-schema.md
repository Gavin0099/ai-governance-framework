# Minimum Legal Schema Reference：adopt 後最小合法結構

> 適用範圍：新導入 repo、`governance_tools` 驗證、以及 consuming repo readiness 檢查  
> 目的：定義什麼叫做「最小可接受、可被 framework 辨識」的 adoption 結構

## 目的

這份文件的用途不是取代 source code，而是定義 adopt 後 consuming repo 至少要長成什麼樣子，才不會在第一輪 check 就出現結構性失敗。

它說明：

- `contract.yaml` 至少要有哪些欄位
- `.governance/baseline.yaml` 至少要有哪些 provenance / integrity / contract 欄位
- `AGENTS.md` 裡哪些 repo-specific section 是合法最小值
- `PLAN.md` freshness 要如何被解讀

## 1. `contract.yaml`

### 最小合法形狀

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
  - governance/rules
validators: []
```

### 關鍵欄位說明

| 欄位 | 必要性 | 說明 |
|---|---|---|
| `name` | 必要 | repo contract 名稱 |
| `plugin_version` | 必要 | 目前 contract schema/plugin 版本 |
| `framework_interface_version` | 必要 | framework 介面版本 |
| `framework_compatible` | 必要 | 相容 framework 範圍 |
| `domain` | 必要 | repo domain 名稱 |
| `documents` | 建議 | 至少列出 `AGENTS.base.md`、`PLAN.md`，必要時再加 governance docs |
| `ai_behavior_override` | 建議 | 通常至少包含 `AGENTS.base.md` |
| `rule_roots` | 必要 | 預設應指向 `governance/rules` |
| `validators` | 必要 | 可以是空陣列，但 key 應存在 |

### 常見錯誤

- placeholder 沒被替換，例如 `<repo-name>`、`<domain>`
- `validators` 整個欄位缺失
- `documents` 寫成錯誤巢狀結構
- `rule_roots` 指到不存在的路徑

### 不影響 legality、但會影響 readiness 的欄位

- `framework.lock.json` 缺失
- hooks 未安裝

這些不一定讓 adoption 非法，但會影響 readiness 與 drift / version audit 的結果。

## 2. `.governance/baseline.yaml`

### 最小合法形狀

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

### 欄位分層

- **PROVENANCE**
  - `initialized_by`
  - `initialized_at`
  - `source_commit`
- **INTEGRITY**
  - `sha256.*`
  - `overridable.*`
- **CONTRACT**
  - `plan_freshness_threshold_days` 之類的 override
- **OBSERVED**
  - `plan_section_inventory`

### 關鍵點

- `sha256.*` 缺失會讓 protected file 類檢查失效
- `initialized_at` 影響 baseline freshness 類檢查
- `plan_section_inventory` 影響 plan inventory 類 drift check

## 3. `AGENTS.md`

### adopt 後最小合法 repo-specific section

```markdown
## Repo-Specific Risk Levels
<!-- governance:key=risk_levels -->
N/A

## Must-Test Paths
<!-- governance:key=must_test_paths -->
N/A

## L1 / L2 Escalation Triggers
<!-- governance:key=escalation_triggers -->
N/A

## Repo-Specific Forbidden Behaviors
<!-- governance:key=forbidden_behaviors -->
N/A
```

### `governance:key` 的作用

這些 anchor 讓 drift checker 能辨識：

- 該 section 是否存在
- repo-specific 區塊是否仍是合法最小值

`N/A` 目前是 prototype / minimal repo 的合法值，不應被當成自動失敗。

### `AGENTS.base.md` vs `AGENTS.md`

| 文件 | 角色 | 規則 |
|---|---|---|
| `AGENTS.base.md` | protected canonical baseline | 不應被任意修改 |
| `AGENTS.md` | overridable repo-specific layer | 可由 consuming repo 補充 |

## 4. `PLAN.md` Freshness

### 最小 header 形狀

```markdown
> **Last Updated**: 2026-03-22
> **Owner**: your-name
> **Freshness**: Sprint (7d)
```

### Freshness policy 解讀順序

1. `PLAN.md` 內寫的 freshness header
2. `.governance/baseline.yaml` / CONTRACT override
3. framework default（通常 `14d`）

如果 override 大於 framework default，可能會出現 guardrail warning，但不必然代表 adoption 非法。

### 常見錯誤

- freshness label 格式不對
- 少了括號或天數
- header key 大小寫漂移到 parser 無法辨識

## adopt 後預期會通過的核心檢查

至少應能讓以下檢查成立：

- `baseline_yaml_present`
- `baseline_version_known`
- `protected_files_present`
- `contract_required_fields_present`
- `contract_agents_base_referenced`
- `contract_no_placeholders`
- `plan_required_sections_present`
- `agents_sections_filled`

## 一句話結論

這份 reference 的作用，是把「最小合法 adoption」寫清楚：不是要求 consuming repo 一開始就完美，而是要求它至少具備能被 framework 正確辨識、檢查、與維護的基礎結構。
