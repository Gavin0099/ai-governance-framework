# ZoneTruth External Repo Governance Analysis

> Source: https://github.com/Gavin0099/ZoneTruth
> Analysis date: 2026-05-22
> Analyst: ai-governance-framework (CodeBurn v1.1)
> Analysis class: Class C — single-session observation, not verified third-party audit

---

## 1. Repository Identity

| Field | Value |
|---|---|
| Repo | Gavin0099/ZoneTruth |
| Domain | `ai-governance` (per contract.yaml) |
| Primary language | Python 68.5% |
| Anomalous component | Swift 12.4% — purpose unconfirmed |
| Framework version stated | v1.2 |
| contract.yaml present | Yes |
| AGENTS.md present | Yes |

---

## 2. Governance Readiness Checklist

| Surface | Status | Notes |
|---|---|---|
| `contract.yaml` | present | Minimal but valid schema |
| `rule_roots` defined | yes — `governance/rules` | Not verified to contain rules |
| `validators` defined | BLOCKED — empty | No domain validators registered |
| `AGENTS.md` | present | Two-layer hierarchy (workspace / repo) |
| Evidence class labeling | absent | v1.2 metrics not class-annotated |
| Forbidden phrase audit | pass | No FCP violations observed in README |
| Checklist artifacts | present in docs/ | Not wired to contract validators |

---

## 3. README Claims Analysis (v1.2)

### 3a. Bounded Claims — Correctly Stated

The README explicitly lists what the framework does NOT claim:

- Engineering quality uplift proof — NOT claimed
- Reasoning uplift proof — NOT claimed
- Deterministic cognitive control — NOT claimed
- Machine-authoritative compliance verdicts — NOT claimed
- Universal semantic correctness verification — NOT claimed
- Automatic truth judgment over ambiguous reasoning — NOT claimed
- Long-horizon semantic drift without reviewer oversight — NOT claimed

ADVISORY: This NOT-claim list is the strongest governance signal in the README. Its presence reduces authority inflation risk at the language layer.

### 3b. Metrics (v1.2 Test Results)

| Metric | Value | Class | Note |
|---|---|---|---|
| `scope_violation_count` | 0 | unlabeled | Single evaluator, n=5 |
| `evidence_traceability` | 5/5 | unlabeled | Internal scoring |
| `claim_overreach_count` | 0 | unlabeled | Single evaluator |
| `semantic_consistency` | 4/5 | unlabeled | Internal scoring |
| `tokens_per_actionable_fix` | ~8,630 | labeled "proxy measure only" | Correctly bounded |
| `actionable_fix_latency_sec` | 405 | unlabeled | No uncertainty stated |

ADVISORY: These metrics are internally measured by a single evaluator with n=5 homogeneous test cases. They should be treated as observational indicators only, not verified governance benchmarks. Evidence class: Class C (session-observed, single-party).

### 3c. Methodology Limitations — Correctly Disclosed

The README states:

- Single evaluator (no inter-rater reliability)
- Homogeneous test set (n=5, single package focus)
- Doc remediation emphasis; code scenarios awaiting quantification
- A/B arm metrics asymmetrical (B arm more complete)

ADVISORY: These disclosures are correctly bounded. "Cannot claim universal effectiveness across all codebases/task types" is the right framing. This reduces semantic preauthorization risk.

---

## 4. contract.yaml Gap Analysis

Current state:

```yaml
name: ai-governance-framework-contract
plugin_version: "1.0.0"
domain: ai-governance
rule_roots:
  - governance/rules
validators:
  # empty
```

BLOCKED surface: validators section is empty. The governance framework can discover this repo via contract.yaml, but no domain-specific validation can execute. Current mode: advisory-only (no enforcement).

To move from advisory-only to enforcement mode, at minimum one validator must be registered in the `validators` section pointing to a callable validator in `governance/rules`.

---

## 5. AGENTS.md Hierarchy Assessment

Two-layer architecture observed:

- Layer 1 — Workspace level: personal privacy, external communication gate, memory access restrictions
- Layer 2 — Repo level: "repo governance prevails for repo work" when conflicts arise

This hierarchy is correctly ordered. Repo-level governance taking precedence over workspace instructions for repo tasks is the right precedence rule.

ADVISORY: The "agent-agnostic closeout rule with receipt artifacts and memory eligibility evaluation" mentioned in AGENTS.md mirrors the main governance framework's session_end pattern. This is a positive signal for framework compatibility.

---

## 6. Swift Component (12.4%) — Unresolved

ADVISORY: Swift at 12.4% of codebase is anomalous for a governance framework. Common interpretations:

- macOS/iOS presentation tool (GUI for governance reports)
- Platform-specific hook or notifier
- Legacy code from prior project context

This surface is outside the confirmed governance rule_roots. Until the Swift component's purpose is confirmed and either included in or explicitly excluded from governance scope, it represents an unverified boundary.

---

## 7. Evidence Class Ceiling

Based on available evidence, the maximum permissible claim for ZoneTruth v1.2 results is:

| Claim type | Maximum permitted | Blocking condition |
|---|---|---|
| "Boundary discipline demonstrated in 5 doc tasks" | PERMITTED | Within stated scope |
| "Zero scope violations" | PERMITTED with n=5 qualifier | Must carry sample size |
| "Universally effective governance" | FORBIDDEN | No cross-codebase evidence |
| "Verified audit trail" | FORBIDDEN | validators empty, single evaluator |
| "Production-ready enforcement" | FORBIDDEN | validators empty |

FROZEN INVARIANT: evidence class ceiling is determined by weakest link — single evaluator + n=5 + empty validators = Class C observational, not enforcement-grade.

---

## 8. Onboarding Readiness

| Gate | Status |
|---|---|
| contract.yaml present | PASS |
| domain defined | PASS |
| rule_roots defined | PASS — unverified content |
| validators registered | FAIL — empty |
| evidence class labeled | FAIL — absent |
| Swift component scoped | FAIL — unconfirmed |

**Verdict**: Partially ready. Onboarding is structurally possible (contract.yaml discoverable), but enforcement gates cannot activate without validators.

**Minimum actions before enforcement onboarding**:

1. Register at least one validator in contract.yaml
2. Label v1.2 metrics with evidence class (Class C recommended)
3. Confirm Swift component scope (in-scope or explicitly excluded)

---

## 9. Summary

ZoneTruth demonstrates good semantic posture at the language layer (NOT-claims, honest disclosure, proxy labeling). The structural gap is enforcement infrastructure: validators are empty and metrics are unlabeled. The repo is governance-discoverable but not governance-enforced.

This analysis is Class C — single-session, single-analyst observation of public repo content. It cannot serve as a verified audit or certification.
