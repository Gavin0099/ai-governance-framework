# Domain Enforcement Matrix

?湔?交?嚗?026-04-08

???瘥? external domain-contract repo enforcement posture ?帘摰???????嚗?
- ?芯? domain 隞? advisory-only
- ?芯? domain 撌脤脣 mixed enforcement
- ?芯? rule ID ?桀?????`hard_stop_rules` ??runtime decision

## ?敹急?唳?隞?
```bash
python governance_tools/external_contract_policy_index.py \
  --repo /path/to/USB-Hub-Firmware-Architecture-Contract \
  --repo /path/to/Kernel-Driver-Contract \
  --repo /path/to/IC-Verification-Contract \
  --format human
```

Markdown 頛詨嚗?
```bash
python governance_tools/external_contract_policy_index.py \
  --repo /path/to/USB-Hub-Firmware-Architecture-Contract \
  --repo /path/to/Kernel-Driver-Contract \
  --repo /path/to/IC-Verification-Contract \
  --format markdown
```

## ?桀?霈瘜?
?桀?銝?撖?external contract repo ?賢歇蝬?脣 runtime policy-input posture嚗?
| Repo | Domain | Hard-Stop Rules | Advisory Surface |
| --- | --- | --- | --- |
| `USB-Hub-Firmware-Architecture-Contract` | `firmware` | `HUB-004` | 頛誨??firmware review嚗?憒?`HUB-001` |
| `Kernel-Driver-Contract` | `kernel-driver` | `KD-002`, `KD-003` | pool allocation guidance嚗?憒?`KD-005` |
| `IC-Verification-Contract` | `ic-verification` | `ICV-001` | clock/reset declaration 憿炎?伐?靘? `ICV-002` |

## ????閬?蝢?
?撐 matrix ??潔??航牧 framework 撌脩?霈? full policy engine嚗????閬??牧皜?嚗?
- framework 撌脩?銝? validator discovery
- domain validator 撌脩????瑁?
- ?典? rule ID 撌脣?? `hard_stop_rules` ??runtime decision

雿???*銝誨銵?*嚗?
- 瘥? domain rule ?賣 hard-stop
- 瘥?domain ??evidence 瘛勗漲?賭?璅?- framework 撌脩?霈?? policy engine

?????典停?航??? enforcement boundary 靽??航???
## ?賊??

- [Status Index](README.md)
- [Runtime Governance ??(runtime-governance-status.md)
- [Trust Signal Dashboard](trust-signal-dashboard.md)
