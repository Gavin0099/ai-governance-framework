# Rule Registry

This file is the authoritative registry of valid rule pack names.
Any rule pack not listed here will cause `Unknown rule packs: [...]` errors.

## Valid Rule Packs

| Pack Name | Description | Typical Use |
|---|---|---|
| `common` | Universal baseline rules | All repos (always include) |
| `cpp` | C/C++ code standards | Firmware, driver, embedded repos |
| `csharp` | C# code standards | .NET, Avalonia repos |
| `kernel-driver` | Kernel/driver-specific constraints | KDC and similar driver repos |
| `python` | Python code standards | Service, tooling repos |
| `refactor` | Refactoring guidance | Any repo undergoing refactor |
| `swift` | Swift code standards | iOS/macOS repos |
| `avalonia` | Avalonia UI framework rules | Desktop app repos |

## How Rule Packs Are Selected

Rule packs are selected by `_get_default_rule_packs()` in `adopt_governance.py`
based on detected repo type, or passed explicitly via `--rules` CLI argument.

Use `get_context_aware_rule_packs()` or `available_rule_packs()` from
`governance_tools/rule_pack_loader.py` to enumerate valid options programmatically.

---

## ⚠️ `onboarding` is NOT a valid rule pack

`onboarding` is **not** a rule pack name. If you see:

```
Unknown rule packs: ['onboarding']
```

This means `adopt_governance.py` or a calling script is passing `"onboarding"` as a
rule pack argument. Fix by removing it and using `get_context_aware_rule_packs()` or
an explicit valid pack from the table above.

**Correct approach for onboarding sessions:**

| Repo Type | Rule Packs |
|---|---|
| Firmware / driver repo | `["common", "cpp", "kernel-driver"]` |
| Product repo (TypeScript) | `["common"]` |
| Service repo (Python) | `["common", "python"]` |
| Unknown | `["common"]` |

Onboarding sessions use the same rule packs as regular L1 sessions for that repo type.
There is no special `onboarding` rule pack.
