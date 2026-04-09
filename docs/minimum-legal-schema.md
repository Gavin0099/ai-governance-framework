# Minimum Legal Schema Reference：adopt 後 consuming repo 的最小合法結構

> 用途：提供 consuming repo、`governance_tools` 與 readiness 檢查的共同最小 schema 參考  
> 目標：定義哪些檔案與欄位是 adoption 後最低限度必須成立的結構

## 目的

這份文件不是 source code，而是用來說明 adopt 後 consuming repo 至少要長成什麼樣子，才能讓 framework 正常接上、並讓 readiness / drift / version audit 有共同判準。

它主要描述：
- `contract.yaml` 至少要有哪些欄位
- `.governance/baseline.yaml` 至少要有哪些 provenance / integrity / contract 資訊
- `AGENTS.md` 與 `PLAN.md` 在 repo 中的最小位置與作用

## 1. `contract.yaml`

### 最小合法樣式

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

### 欄位說明

| 欄位 | 是否必要 | 說明 |
|---|---|---|
| `name` | 必要 | repo contract 名稱 |
| `plugin_version` | 必要 | contract schema/plugin 版本 |
| `framework_interface_version` | 必要 | framework interface 版本 |
| `framework_compatible` | 必要 | 允許的 framework 版本範圍 |
| `domain` | 必要 | repo domain 名稱 |
| `documents` | 建議 | 至少列出 `AGENTS.base.md`、`PLAN.md`，以及 repo-local governance docs |
| `ai_behavior_override` | 建議 | 用來聲明 AI 行為覆寫入口 |
| `rule_roots` | 必要 | 預設至少包含 `governance/rules` |
| `validators` | 必要 | 可以為空，但 key 本身應存在 |

### 常見錯誤

- placeholder 沒有替換，例如 `<repo-name>`、`<domain>`
- `validators` 完全缺失
- `documents` 沒有跟 adopt 後實際文件對齊
- `rule_roots` 指向不存在路徑

### Legality 與 readiness 的差別

以下項目通常影響 readiness，但不一定影響 legality：
- `framework.lock.json` 缺失
- hooks 未安裝
- adopted release 尚未記錄

也就是說，合法結構不等於 readiness 已完全通過。

## 2. `.governance/baseline.yaml`

### 最小合法樣式

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

plan_section_inventory:
  required:
    - Current Status
```

### 必要元素

- schema / baseline / framework 版本資訊
- initialization provenance
- protected file hashes
- overridable file 宣告
- 最小 `plan_section_inventory`

### 不要求的東西

- 每個 consuming repo 都必須有相同的 custom threshold
- 每個 baseline 都要有完整 lock metadata
- 每個 repo 都要在 baseline 中寫滿 release 歷史

## 3. 其他最小檔案

adopt 後 consuming repo 至少還應具備：
- `AGENTS.base.md`
- `PLAN.md`
- `memory/01_active_task.md`
- `memory/02_tech_stack.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`
- `governance/` markdown pack
- `governance/rules/` pack

## 4. 一句總結

`minimum legal schema` 的目的是讓 adopt 後的 consuming repo 至少有一個可被 framework、readiness、drift 與 reviewer 共同理解的最低治理結構；它不是在保證 repo 已經 fully ready，而是在定義「至少沒有連骨架都缺」。
