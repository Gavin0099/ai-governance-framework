# Domain Enforcement Matrix

更新日期：2026-04-08

這一頁是比較 external domain-contract repo enforcement posture 的穩定入口。它的用途是回答：

- 哪些 domain 仍偏 advisory-only
- 哪些 domain 已進入 mixed enforcement
- 哪些 rule ID 目前有經過 `hard_stop_rules` 進 runtime decision

## 最快本地指令

```bash
python governance_tools/external_contract_policy_index.py \
  --repo /path/to/USB-Hub-Firmware-Architecture-Contract \
  --repo /path/to/Kernel-Driver-Contract \
  --repo /path/to/IC-Verification-Contract \
  --format human
```

Markdown 輸出：

```bash
python governance_tools/external_contract_policy_index.py \
  --repo /path/to/USB-Hub-Firmware-Architecture-Contract \
  --repo /path/to/Kernel-Driver-Contract \
  --repo /path/to/IC-Verification-Contract \
  --format markdown
```

## 目前讀法

目前三個真實 external contract repo 都已經暴露出 runtime policy-input posture：

| Repo | Domain | Hard-Stop Rules | Advisory Surface |
| --- | --- | --- | --- |
| `USB-Hub-Firmware-Architecture-Contract` | `firmware` | `HUB-004` | 較廣的 firmware review，例如 `HUB-001` |
| `Kernel-Driver-Contract` | `kernel-driver` | `KD-002`, `KD-003` | pool allocation guidance，例如 `KD-005` |
| `IC-Verification-Contract` | `ic-verification` | `ICV-001` | clock/reset declaration 類檢查，例如 `ICV-002` |

## 這頁的重要意義

這張 matrix 的價值不是說 framework 已經變成 full policy engine，而是把一個重要邊界說清楚：

- framework 已經不只停在 validator discovery
- domain validator 已經真的執行
- 部分 rule ID 已可透過 `hard_stop_rules` 進 runtime decision

但這仍然**不代表**：

- 每條 domain rule 都是 hard-stop
- 每個 domain 的 evidence 深度都一樣
- framework 已經變成通用 policy engine

這頁的作用就是讓這些 enforcement boundary 保持可見。

## 相關頁面

- [Status Index](README.md)
- [Runtime Governance 狀態](runtime-governance-status.md)
- [Trust Signal Dashboard](trust-signal-dashboard.md)
