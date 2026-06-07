# AI Governance Framework

> AI 輔助工程的契約式執行（contract-bound execution）、artifact 證據驗證（artifact-backed verification）、與 fail-closed 決策機制。

你的 AI agent 會改程式、產生摘要、宣稱任務完成；但在真實 repo 裡，常見風險是：

- **範圍越界（Scope overreach）**：改到需求以外的檔案
- **宣稱膨脹（Claim inflation）**：「測試通過」被說成「系統安全」
- **證據不足摘要（Evidence-light summaries）**：文字看似完整但無 artifact 支撐
- **觀測不等於治理（Observation ≠ enforcement）**：有 log 就被誤當成 gate pass
- **記憶污染（Memory pollution）**：一次成功 session 被錯誤升級為長期知識

這個 framework 不是讓 AI 更聰明，而是讓 AI 的邊界、證據、宣稱可以被**審核（auditable）且可強制執行（enforceable）**。

---

## 運作方式（How It Works）

每個 AI 任務都會經過一條治理生命週期：

```text
Pre Hook          →  載入授權來源 + 產生 task contract
Agent Execution   →  在 contract 邊界內執行
Post Hook         →  獨立 artifact 檢查 + claim ceiling
Decision Gate     →  PASS / FAIL / BLOCKED（預設 fail-closed）
Closeout Receipt  →  可審核收據，包含明確 non-claims
Memory Check      →  依資格決定是否可升級，不做自動學習
```

核心機制：

| 機制 | 功能 |
|---|---|
| **Task Contract** | 執行前定義 allowed scope、forbidden scope、required evidence、done definition |
| **Claim Ceiling** | 限制證據可支撐的宣稱上限：test pass ≠ system safety |
| **Fail-Closed Gate** | scope 不明即阻擋、證據不足不採信、授權不清不放行 |
| **Non-Claims** | 每份 closeout receipt 明確列出「這次結果不代表什麼」 |

## Fleet 治理（Fleet Governance）

除了單次任務，framework 也管理多 repo 的治理狀態：

```text
掃描 20 個 repo  →  scope 分類（required / recommended / exempt）
                →  每 repo 7 訊號檢查（hooks、framework lock、agents、
                   dirty 狀態、evidence、head match、timestamp freshness）
                →  fleet classification（matrix_only → partial → candidate → verified）
                →  scope-normalized ratio，並分離 structural readiness 與 freshness
```

Fleet 層回答的問題與單次任務不同：

| 層級 | 問題 |
|---|---|
| **單次任務（Single run）** | 這次任務有沒有符合契約？ |
| **Fleet** | 哪些 repo 具備可採信 evidence chain？瓶頸在哪裡？ |

目前 fleet 狀態請看 `artifacts/session/` 最新 matrix snapshot。  
趨勢紀錄在 `governance/fleet/scope_normalized_trend.jsonl`。

## 快速開始（Quick Start）

### 驗證本 repo

```bash
pip install -r requirements.txt

# Governance smoke test
python governance_tools/quickstart_smoke.py \
  --project-root . --plan PLAN.md \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human

# Drift check
python governance_tools/governance_drift_checker.py --repo . --framework-root .

# Runtime surface coverage
python governance_tools/runtime_surface_manifest_smoke.py --format human
python governance_tools/execution_surface_coverage_smoke.py --format human
```

### 導入到其他 repo

完整 onboarding：

```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo
```

最小起步包：見 [`examples/starter-pack/`](examples/starter-pack/) 與 [`governance/fleet/external_repo_onboarding_sop.md`](governance/fleet/external_repo_onboarding_sop.md)。

## 能力狀態（Capability Status）

不是所有能力都已完整 operational，下表標示目前狀態：

| Capability | Status | Notes |
|---|---|---|
| Evidence anchoring（artifact-backed，不依賴 AI summary） | **Operational** | fleet rollout 期間已驗證 gate_blocked admissibility fix |
| Fail-closed decision gate | **Operational** | 測試覆蓋：無 closeout commit 會從 verified 立即掉回 unverified |
| Fleet matrix + scope-normalized ratio | **Operational** | required 10 repos 可 verified；structural readiness 與 freshness 分離追蹤 |
| Evidence tier（hardware-aware） | **Operational** | snapshot 可見 tier_2 / tier_3 / ci_strict |
| Claim vs. evidence separation | **Partial** | 原則已落地，但不同 claim 類型自動化覆蓋仍不一 |
| Minimal rule selection | **Partial** | rule registry 已有；task-type 驅動的自動載入尚未完整 |
| Decision gate intermediate states | **Designed** | PASS_WITH_DOWNGRADED_CLAIMS、NEEDS_REVIEW 為語義概念；程式路徑覆蓋待補 |
| Memory promotion strictness | **Partial** | 結構已存在；不是所有 memory path 都有 rejection 證據 |
| CodeBurn（usage observation） | **Optional** | 觀測層，不是 gate 輸入 |

## 本框架不主張（What This Framework Does Not Claim）

以下是規範邊界，不是一般免責聲明：

- 不保證 AI 語義正確性（semantic correctness）
- 不把 test-pass 視為 production-safety 證明
- 不把「matrix-visible」等同於「verified」
- 不把 AI explanation 升級為 evidence
- 不把 observation record 自動升級為 enforcement authority
- 不把 closeout receipt 視為「governance complete」
- 不把 session 結果自動寫入長期記憶

## 專案結構（Project Structure）

```text
runtime_hooks/          # Pre/post task checks, session start/end
governance_tools/       # Adoption, drift check, readiness, onboarding
governance/             # Canonical rules, fleet config, scope definitions
  fleet/                # governance_scope.yaml, trend.jsonl, operational semantics
artifacts/              # Session snapshots, matrix output, audit logs
memory/                 # Memory state (eligibility-controlled)
memory_pipeline/        # Memory promotion logic
scripts/                # Runtime governance entry point
tests/                  # Test suite
docs/                   # Explainer, status surfaces, release notes
examples/               # Starter pack, sample contracts
```

## 關鍵文件（Key Documents）

| 文件 | 用途 |
|---|---|
| [`governance/fleet/operational_semantics_v1.md`](governance/fleet/operational_semantics_v1.md) | Fleet 治理定義與決策邊界 |
| [`governance/fleet/external_repo_onboarding_sop.md`](governance/fleet/external_repo_onboarding_sop.md) | 外部 repo 導入 SOP |
| [`docs/ai-governance-framework-explainer.md`](docs/ai-governance-framework-explainer.md) | 長文說明（14 sections） |
| [`governance/fleet/governance_scope.yaml`](governance/fleet/governance_scope.yaml) | Repo tier 分類（required / recommended / exempt） |
| [`PLAN.md`](PLAN.md) | Project roadmap |
| [`CHANGELOG.md`](CHANGELOG.md) | 版本紀錄 |

## Runtime 入口（Runtime Entry Points）

| Entry Point | 用途 |
|---|---|
| `scripts/run-runtime-governance.sh` | hooks 與 CI 共用的 enforcement entrypoint |
| `artifacts/session/governance_repo_matrix_20260525.ps1` | Fleet matrix 掃描器（PowerShell） |
| `governance_tools/session_end_hook.py` | Closeout receipt 產生器 |

## 貢獻（Contributing）

歡迎 PR。請先閱讀 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

若要修改 governance contract 或 decision boundary，請先看 [framework explainer](docs/ai-governance-framework-explainer.md) 中的 authority source 要求。

## 授權（License）

請見 repository license 檔案。

---

# AI Governance Framework (English)

> Contract-bound execution, artifact-backed verification, and fail-closed decisions for AI-assisted engineering.

Your AI agents modify code, generate summaries, and claim tasks are complete. But in real repositories:

- **Scope overreach** — the agent edits files outside the request
- **Claim inflation** — "tests passed" gets reported as "system is safe"
- **Evidence-light summaries** — polished text with no artifact backing
- **Observation ≠ enforcement** — a log entry gets treated as a gate pass
- **Memory pollution** — one successful session becomes permanent knowledge

This framework doesn't make AI smarter. It makes AI's boundaries, evidence, and claims **auditable and enforceable**.

---

## How It Works

Each AI task runs through a governance lifecycle:

```text
Pre Hook          →  Load authority source + generate task contract
Agent Execution   →  Operate within contract boundaries
Post Hook         →  Independent artifact inspection + claim ceiling
Decision Gate     →  PASS / FAIL / BLOCKED (fail-closed default)
Closeout Receipt  →  Auditable record with explicit non-claims
Memory Check      →  Eligibility-controlled promotion, not auto-learning
```

The key mechanisms:

| Mechanism | What It Does |
|---|---|
| **Task Contract** | Defines allowed scope, forbidden scope, required evidence, and done definition before execution starts |
| **Claim Ceiling** | Limits what conclusions the evidence can support — test pass ≠ system safety |
| **Fail-Closed Gate** | Unknown scope → blocked. Missing evidence → not admitted. Unclear authority → denied |
| **Non-Claims** | Every closeout receipt explicitly states what the result does *not* prove |

## Fleet Governance

Beyond single tasks, this framework manages governance across multiple repositories:

```text
20 repos scanned  →  scope classified (required / recommended / exempt)
                  →  per-repo 7-signal check (hooks, framework lock, agents,
                     dirty status, evidence, head match, timestamp freshness)
                  →  fleet classification (matrix_only → partial → candidate → verified)
                  →  scope-normalized ratio with structural readiness tracked separately
```

Fleet governance answers different questions than single-run governance:

| Layer | Question |
|---|---|
| **Single run** | Did this task meet its contract? |
| **Fleet** | Which repos have admissible evidence chains? Where are the blockers? |

Current fleet status is in `artifacts/session/` (latest matrix snapshot).  
Trend history is in `governance/fleet/scope_normalized_trend.jsonl`.

## Quick Start

### Verify this repo

```bash
pip install -r requirements.txt

# Governance smoke test
python governance_tools/quickstart_smoke.py \
  --project-root . --plan PLAN.md \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human

# Drift check
python governance_tools/governance_drift_checker.py --repo . --framework-root .

# Runtime surface coverage
python governance_tools/runtime_surface_manifest_smoke.py --format human
python governance_tools/execution_surface_coverage_smoke.py --format human
```

### Adopt into another repo

Full onboarding:

```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo
```

One-line latest governance apply prompt:

```text
Please run latest AI governance apply for <REPO_PATH> (install hooks, execute closeout, rerun apply) until repo_native_verified=True, then return hooks/fw/agents/evidence/head_ok/ts_ok.
```

Minimal starter pack: see [`examples/starter-pack/`](examples/starter-pack/) and [`governance/fleet/external_repo_onboarding_sop.md`](governance/fleet/external_repo_onboarding_sop.md).

## Capability Status

Not everything described here is fully operational. This table tracks what's verified vs. what's still maturing:

| Capability | Status | Notes |
|---|---|---|
| Evidence anchoring (artifact-backed, not AI summary) | **Operational** | gate_blocked admissibility fix verified in fleet rollout |
| Fail-closed decision gate | **Operational** | Tested: commit without closeout → immediate verified → unverified drop |
| Fleet matrix + scope-normalized ratio | **Operational** | 10 required repos verified; structural readiness tracked separately from freshness |
| Evidence tier (hardware-aware) | **Operational** | tier_2 / tier_3 / ci_strict visible per repo in snapshot |
| Claim vs. evidence separation | **Partial** | Principle enforced; per-claim-type automation coverage varies |
| Minimal rule selection | **Partial** | Rule registry exists; task-type-driven loading not yet fully automated |
| Decision gate intermediate states | **Designed** | PASS_WITH_DOWNGRADED_CLAIMS, NEEDS_REVIEW are decision concepts; code path coverage TBD |
| Memory promotion strictness | **Partial** | Structure exists; not all memory paths have rejection evidence |
| CodeBurn (usage observation) | **Optional** | Observation layer; not a gate input |

## Agent Runtime Governance Profile

This framework includes reviewer-facing, structural artifacts for analyzing agent runtime governance surfaces.

Start with:

- [`docs/governance/trust-boundary-taxonomy.md`](docs/governance/trust-boundary-taxonomy.md)
- [`docs/governance/agent-runtime-profile.md`](docs/governance/agent-runtime-profile.md)
- [`docs/governance/runtime-profile-validator-contract.md`](docs/governance/runtime-profile-validator-contract.md)
- [`examples/runtime-profiles/governed-coding-agent.yaml`](examples/runtime-profiles/governed-coding-agent.yaml)

These artifacts classify runtime surfaces such as memory, context files, skills, plugins, tool execution, gateways, schedulers, subagents, and rollback/checkpoint mechanisms.

Claim ceiling:

- Structural / reviewer-facing only.
- Not runtime enforcement.
- Not Hermes integration.
- Not semantic evidence validation.
- Not OS sandbox, RBAC, SoD, or containment.
- Not an authority correctness engine.
- Not complete AI governance automation.

## What This Framework Does Not Claim

These boundaries are normative, not disclaimers:

- Does not guarantee AI semantic correctness
- Does not treat test-pass as production-safety proof
- Does not equate "matrix-visible" with "verified"
- Does not promote AI explanation to evidence status
- Does not auto-upgrade observation records to enforcement authority
- Does not treat closeout receipt as "governance complete"
- Does not auto-write session results into long-term memory

## Project Structure

```text
runtime_hooks/          # Pre/post task checks, session start/end
governance_tools/       # Adoption, drift check, readiness, onboarding
governance/             # Canonical rules, fleet config, scope definitions
  fleet/                # governance_scope.yaml, trend.jsonl, operational semantics
artifacts/              # Session snapshots, matrix output, audit logs
memory/                 # Memory state (eligibility-controlled)
memory_pipeline/        # Memory promotion logic
scripts/                # Runtime governance entry point
tests/                  # Test suite
docs/                   # Explainer, status surfaces, release notes
examples/               # Starter pack, sample contracts
```

## Key Documents

| Document | Purpose |
|---|---|
| [`governance/fleet/operational_semantics_v1.md`](governance/fleet/operational_semantics_v1.md) | Fleet governance definitions and decision boundaries |
| [`governance/fleet/external_repo_onboarding_sop.md`](governance/fleet/external_repo_onboarding_sop.md) | Step-by-step onboarding for external repos |
| [`docs/fleet/f7-governance-submodule-updater.md`](docs/fleet/f7-governance-submodule-updater.md) | "Update AI Governance to latest" user-facing entrypoint and governed submodule update contract for external repos |
| [`docs/ai-governance-framework-explainer.md`](docs/ai-governance-framework-explainer.md) | Long-form framework explainer (14 sections) |
| [`governance/fleet/governance_scope.yaml`](governance/fleet/governance_scope.yaml) | Repo tier classification (required / recommended / exempt) |
| [`PLAN.md`](PLAN.md) | Project roadmap |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |

## Runtime Entry Points

| Entry Point | Use |
|---|---|
| `scripts/run-runtime-governance.sh` | Shared enforcement entrypoint for hooks and CI |
| `artifacts/session/governance_repo_matrix_20260525.ps1` | Fleet matrix scanner (PowerShell) |
| `governance_tools/session_end_hook.py` | Closeout receipt generator |

## Contributing

PRs welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

Before submitting changes to governance contracts or decision boundaries, review the authority source requirements in the [framework explainer](docs/ai-governance-framework-explainer.md).

## License

See repository license file.

## Governance Artifact Discipline Index

- [`docs/governance/reason-code-registry.md`](docs/governance/reason-code-registry.md)
- [`docs/governance/GOVERNANCE_ARTIFACT_FORMAT_RULE.md`](docs/governance/GOVERNANCE_ARTIFACT_FORMAT_RULE.md)
- [`docs/governance/minimal-retrieval-navigability-verification-2026-05-27.md`](docs/governance/minimal-retrieval-navigability-verification-2026-05-27.md)
