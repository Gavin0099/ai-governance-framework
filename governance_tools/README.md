# governance_tools/ — AI Governance Framework 工具集

> **版本**: 當前（runtime governance prototype）
> **最後更新**: 2026-03-15
> **相依**: Python 3.9+；框架核心以 stdlib 為主，測試與 runnable demos 另外記於 repo root `requirements.txt`

---

## Python 啟動方式

所有 shell 入口會依序嘗試：

- `AI_GOVERNANCE_PYTHON`
- `python`
- `python3`
- `py -3`

若本機 Python 沒有加入 `PATH`，可先指定：

```bash
export AI_GOVERNANCE_PYTHON=/path/to/python
```

Windows PowerShell:

```powershell
$env:AI_GOVERNANCE_PYTHON='C:\Path\To\python.exe'
```

---

## 工具一覽

| 工具 | 功能 | 主要用途 |
|------|------|---------|
| [memory_janitor.py](#memory_janitorpy) | 記憶壓力監控與歸檔 | 防止 context 過載 |
| [contract_validator.py](#contract_validatorpy) | AI 初始化合規驗證 | CI gate |
| [quickstart_smoke.py](#quickstart_smokepy) | 最小上手流程驗證 | onboarding / quickstart |
| [example_readiness.py](#example_readinesspy) | 範例集健康度檢查 | onboarding / examples |
| [release_readiness.py](#release_readinesspy) | release-facing 文件對齊檢查 | trust signal / release prep |
| [trust_signal_overview.py](#trust_signal_overviewpy) | 高層 trust signal 總覽 | adoption / release / audit |
| [plan_freshness.py](#plan_freshnesspy) | PLAN.md 新鮮度檢查 | CI gate / Git hook |
| [state_generator.py](#state_generatorpy) | .governance-state.yaml 生成 | 狀態快照 |
| [linear_integrator.py](#linear_integratorpy) | PLAN.md → Linear 同步 | 任務追蹤 |
| [notion_integrator.py](#notion_integratorpy) | PLAN.md → Notion 同步 | 任務追蹤 |

---

## memory_janitor.py

記憶壓力監控工具。分析 `memory/` 目錄中的熱記憶體行數，判斷是否需要歸檔。

**狀態閾值**:

| 狀態 | 行數 | 行動 |
|------|------|------|
| SAFE | ≤ 150 | 無需動作 |
| WARNING | 151–180 | 計畫清理 |
| CRITICAL | 181–200 | 盡快執行 `--execute` |
| EMERGENCY | > 200 | 立即停止並手動整理 |

```bash
# 檢查狀態
python governance_tools/memory_janitor.py --check

# 查看歸檔計畫
python governance_tools/memory_janitor.py --plan

# 執行歸檔（copy+pointer 模式，原檔保留 pointer）
python governance_tools/memory_janitor.py --execute

# 查看歸檔紀錄
python governance_tools/memory_janitor.py --manifest

# JSON 輸出（CI/dashboard 用）
python governance_tools/memory_janitor.py --check --format json
```

**歸檔行為**: `--execute` 採用 copy+pointer 模式 — 內容複製到 `memory/archive/`，原位置留下 pointer 區塊，`manifest.json` 記錄每次操作。

---

## contract_validator.py

驗證 AI 初始化是否符合治理規範（Governance Contract）。檢查 8 大法典是否已載入。

```bash
# 基本驗證
python governance_tools/contract_validator.py

# 指定 memory 目錄
python governance_tools/contract_validator.py --memory-root ./memory

# JSON 輸出（CI 用）
python governance_tools/contract_validator.py --format json
```

**退出碼**:
- `0` = 合規
- `1` = 不合規（有缺失項）

---

## quickstart_smoke.py

將 repo 文件中的最小上手流程收成一條可執行 smoke command。

它會驗證：

- `pre_task_check`
- `session_start`
- optional external contract path

```bash
python governance_tools/quickstart_smoke.py \
  --project-root . \
  --plan PLAN.md \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human
```

適合用在：

- 新 clone 後先確認框架有沒有真的能跑
- onboarding 文件更新後做快速回歸
- demo / workshop 前先做最低限度驗證

---

## example_readiness.py

檢查 `examples/` 目錄目前的 onboarding readiness。

它會區分：

- runnable demos
- walkthrough-only examples
- scaffold-only examples
- domain-contract samples

並回報：

- 必要檔案是否齊全
- runnable example 在目前環境下是否具備執行條件
- domain contract example 是否可載入 / validator preflight 是否通過

```bash
python governance_tools/example_readiness.py --format human
```

若想把缺依賴也當作失敗，可加：

```bash
python governance_tools/example_readiness.py --strict-runtime --format human
```

這個模式特別適合放在 CI，因為 CI 已經會先安裝 `requirements.txt`。

---

## release_readiness.py

檢查 repo 的 release-facing 文件是否對齊指定版本。

會檢查：

- `docs/releases/<version>.md`
- `docs/releases/alpha-checklist.md`
- `CHANGELOG.md`
- `README.md`
- `docs/LIMITATIONS.md`
- `docs/status/runtime-governance-status.md`

```bash
python governance_tools/release_readiness.py --version v1.0.0-alpha --format human
```

human output now starts with a reviewer-first `summary=...` line so release status can be scanned quickly before reading individual checks.

這個工具適合用在：

- 發版前自查
- release note / changelog / README 是否同步
- 對外信任信號是否齊備

---

## trust_signal_overview.py

把幾條高層 adoption / trust signals 收成一條命令：

- `quickstart_smoke.py`
- `example_readiness.py`
- `release_readiness.py`
- `governance_auditor.py`

```bash
python governance_tools/trust_signal_overview.py \
  --project-root . \
  --plan PLAN.md \
  --release-version v1.0.0-alpha \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human
```

human output 會先給一行 reviewer-first `summary=...`，快速告訴你：

- quickstart 是否通
- examples 是否健康
- release-facing 文件是否對齊
- 高層 auditor 是否健康

這個工具適合用在：

- 對外 demo 前快速確認信號面是否完整
- 發版前做高層健康總覽
- 想快速確認 repo 現在是否處於「可展示 / 可採用」狀態

GitHub Actions / GitLab CI 現在也會產出這個 overview 的 human + JSON artifact，方便在 pipeline 後直接檢視。

---

## plan_freshness.py

檢查 PLAN.md 的 `最後更新` 欄位是否在有效期內。用於 CI gate 和 Git hook。

```bash
# 基本檢查（讀取當前目錄 PLAN.md）
python governance_tools/plan_freshness.py

# 指定 PLAN.md 路徑
python governance_tools/plan_freshness.py --file /path/to/PLAN.md

# 覆寫閾值（天）
python governance_tools/plan_freshness.py --threshold 14

# JSON 輸出（CI 用）
python governance_tools/plan_freshness.py --format json
```

**退出碼**:
- `0` = FRESH（距今 ≤ threshold）
- `1` = STALE（距今 > threshold，≤ 2×threshold）
- `2` = CRITICAL（距今 > 2×threshold）或欄位缺失

**PLAN.md 必要欄位**（blockquote 格式）:
```markdown
> **最後更新**: 2026-03-06
> **Owner**: GavinWu
> **Freshness**: Sprint (7d)
```

---

## state_generator.py

讀取 PLAN.md header，生成 `.governance-state.yaml` 狀態快照，供 AI session 初始化使用。

```bash
# 生成狀態快照
python governance_tools/state_generator.py

# 指定來源與輸出路徑
python governance_tools/state_generator.py \
  --plan PLAN.md \
  --output .governance-state.yaml
```

**輸出範例（.governance-state.yaml）**:
```yaml
last_updated: "2026-03-06"
owner: "GavinWu"
freshness_policy: "Sprint (7d)"
generated_at: "2026-03-06T10:00:00"
```

---

## linear_integrator.py

將 `memory/01_active_task.md` 中的未完成任務同步到 Linear，並將 Issue ID 寫回本地。

**前置**:
```bash
export LINEAR_API_KEY='your_linear_api_key'
```

```bash
# 列出可用 Teams
python governance_tools/linear_integrator.py --list-teams

# 同步未完成任務到指定 Team
python governance_tools/linear_integrator.py --sync --team-id <TEAM_ID>

# 指定優先級（0=無, 1=緊急, 2=高, 3=中, 4=低）
python governance_tools/linear_integrator.py --sync --team-id <TEAM_ID> --priority 2

# JSON 輸出（CI/dashboard 用）
python governance_tools/linear_integrator.py --sync --team-id <TEAM_ID> --format json
```

**同步後**：任務後面會加上 `[LINEAR:ENG-123]` 標記，防止重複建立。

**策略文件**: [docs/linear-source-of-truth.md](../docs/linear-source-of-truth.md)

---

## notion_integrator.py

將 `memory/01_active_task.md` 中的未完成任務同步到 Notion Database，並將短 ID 寫回本地。

**前置**:
```bash
export NOTION_API_KEY='secret_xxxx'        # Notion Integration Token
export NOTION_DATABASE_ID='<DB_ID>'        # 可選，也可用 --database-id 傳入
```

> 取得 Token：https://www.notion.so/my-integrations → 建立 Integration
> 建立後需在目標 Database 頁面加入此 Integration（右上角 `...` → Add connections）

```bash
# 列出 Integration 可存取的 Database
python governance_tools/notion_integrator.py --list-databases

# 同步未完成任務到指定 Database
python governance_tools/notion_integrator.py --sync --database-id <DB_ID>

# JSON 輸出（CI/dashboard 用）
python governance_tools/notion_integrator.py --sync --database-id <DB_ID> --format json
```

**同步後**：任務後面會加上 `[NOTION:XXXXXXXX]` 標記（8 字元短 ID），防止重複建立。

**策略文件**: [docs/notion-source-of-truth.md](../docs/notion-source-of-truth.md)

---

## 共通設計原則

- **零依賴**: 所有工具僅使用 Python stdlib（urllib、re、json、pathlib）
- **敏感資訊防護**: linear_integrator / notion_integrator 送出前掃描 title/description，偵測到 API key、密碼、private key 時拒絕送出
- **--format json**: 所有工具支援 JSON 輸出，可接 CI pipeline 或 dashboard
- **--help**: 所有工具有完整說明（`python <tool>.py --help`）
- **錯誤降級**: API 失敗時不影響本地工作流

---

## CI 整合

`.github/workflows/governance.yml` 和 `.gitlab-ci.yml` 已整合以下兩個自動檢查：

| Job | 工具 | 失敗條件 |
|-----|------|---------|
| `plan-freshness` | plan_freshness.py | CRITICAL（擋 push） |
| `memory-pressure` | memory_janitor.py | EMERGENCY（advisory，不擋） |

---

## Git Hook

```bash
# 一鍵安裝（PLAN.md 過期擋 commit）
bash scripts/install-hooks.sh
```

安裝後：`git commit` 時自動執行 `plan_freshness.py`，CRITICAL 狀態會擋下 commit。
若安裝到其他 repo，hooks 會透過 `.git/hooks/ai-governance-framework-root` 回指 framework 本體，降低 external contract repo 的攔截失效風險。
可再用 `governance_tools/hook_install_validator.py --repo /path/to/repo` 驗證 copied hooks 與 framework root 設定是否齊全。
`scripts/install-hooks.sh` 預設會在安裝後自動執行這個 validator，讓 external repo 的接入流程更接近 install-and-verify。
若要檢查整體 external repo readiness，也可跑 `governance_tools/external_repo_readiness.py --repo /path/to/repo`，一次看 hooks / PLAN / contract 狀態。
若要直接走 onboarding flow，也可用 `scripts/onboard-external-repo.sh --target /path/to/repo`，把 hook 安裝與 readiness report 串成一條命令。
onboarding flow 預設還會再跑一個最小 governance smoke，驗證 external contract 是否真的能通過 `session_start` 與 `pre_task_check`。
預設也會把 JSON onboarding report 寫到 target repo 的 `memory/governance_onboarding/latest.json`，讓接入狀態不只存在於當下終端輸出。
現在也會同步維護 `latest.txt`、`history/`、與 `INDEX.txt`，讓 external repo onboarding 狀態有基本的時間序列與索引。
若要在 framework repo 端集中查看多個 external repo 的 onboarding 狀態，可用 `governance_tools/external_repo_onboarding_index.py --repo /path/to/repo1 --repo /path/to/repo2`。
---

## Runtime Layer

The first runtime-governance modules now live under `runtime_hooks/`.

Core checks:

- `runtime_hooks/core/pre_task_check.py`
- `runtime_hooks/core/post_task_check.py`

New validated contract fields:

- `RULES`
- `RISK`
- `OVERSIGHT`
- `MEMORY_MODE`

Rule-pack runtime support:

- `rule_pack_loader.py` validates requested packs
- `describe_rule_selection(...)` returns selection metadata
- `load_rule_content(...)` returns loaded rule titles and markdown content for runtime injection
- external rule roots can now be merged in through `contract.yaml` discovery
- current seed packs include `common`, `python`, `cpp`, `refactor`, `csharp`, `swift`, `avalonia`, `kernel-driver`
- pack categories now distinguish `scope`, `language`, `framework`, and `platform`

Domain contract discovery:

- `domain_contract_loader.py` loads a minimal `contract.yaml` without adding non-stdlib dependencies
- `contract_resolver.py` resolves contracts through explicit path, environment override, and bounded upward discovery
- `contract_context.py` extracts stable reviewer-facing contract context from session-start artifacts
- `domain_governance_metadata.py` centralizes domain priority and risk-tier metadata
- supported keys today: `name`, `documents`, `rule_roots`, `validators`
- `runtime_hooks/core/session_start.py`, `pre_task_check.py`, and `post_task_check.py` can all consume this contract with `--contract`
- when `--contract` is omitted, runtime hooks fall back to `AI_GOVERNANCE_CONTRACT`, then bounded upward discovery
- `validator_interface.py` defines the external validator contract
- `domain_validator_loader.py` handles discovery, import isolation, startup preflight, and advisory execution routing

Test-result normalization:

- `test_result_ingestor.py` converts test runner output into normalized runtime `checks`
- currently supports `pytest-text`, `junit-xml`, `sdv-text`, `msbuild-warning-text`, `sarif`, and `wdk-analysis-text`

Architecture drift heuristics:

- `architecture_drift_checker.py` detects high-signal boundary drift patterns
- current heuristics include cross-project private includes, peer-path include directories, and refactor boundary drift warnings
- it also supports lightweight before/after dependency-edge diffing for imports and includes, without becoming a heavy graph engine

Example usage:

```bash
python governance_tools/state_generator.py \
  --rules common,python \
  --risk medium \
  --oversight review-required \
  --memory-mode candidate

python runtime_hooks/core/pre_task_check.py \
  --rules common,python \
  --risk high \
  --oversight review-required

python runtime_hooks/core/post_task_check.py \
  --file ai_response.txt \
  --risk medium \
  --oversight review-required \
  --api-before before.cs \
  --api-after after.cs
```

Governance self-audit:

- `governance_auditor.py` checks alignment between constitution docs, runtime enforcement entrypoints, seed rule packs, optional external onboarding state, and optional release-facing trust signals
- intended to detect governance drift, not to act as a general-purpose policy engine
- use `--release-version v1.0.0-alpha` when you want the same audit run to also confirm release-note / changelog / README / status-doc alignment
- human output now starts with `summary=...`, matching the reviewer-first style used in runtime hooks and other high-signal governance tools

Failure-path completeness:

- `failure_test_validator.py` checks whether available test names cover the minimum L1-style categories
- current categories: `invalid_input`, `boundary`, `failure_path`, optional `rollback_cleanup`
- outputs normalized `warnings` / `errors` so the result can be merged into runtime `checks`

Rule-pack suggestion:

- `rule_pack_suggester.py` suggests `language` and `framework` packs from repository signals
- `scope` suggestions are advisory only and should be confirmed by the contract or a human reviewer
- `state_generator.py` now includes these suggestions as `rule_pack_suggestions`, but does not mutate `runtime_contract.rules`
- `suggested_rules_preview` provides a convenience preview such as `common,csharp,avalonia,refactor`, but remains advisory

Public API diff:

- `public_api_diff_checker.py` extracts a high-signal public API manifest and compares before/after surfaces
- intended as a lightweight semantic-verification step for interface stability, not a full language-aware compiler front end

Architecture impact estimation:

- `architecture_impact_estimator.py` combines drift signals and public API diff into a proposal-time `Governance Impact Report`
- the report now includes `touched_layers`, `boundary_risk`, `expected_validators`, `required_evidence`, and recommended `risk` / `oversight`
- use `--format human` when the estimator is meant to guide an operator or AI before implementation, rather than feed JSON into another tool
- `state_generator.py` can include this same preview with `--impact-before/--impact-after`, keeping proposal context advisory rather than auto-mutating the runtime contract
- `change_proposal_builder.py` packages task text, rule suggestions, and architecture impact into a single proposal artifact for humans, AI agents, or review tooling
- `change_control_summary.py` merges session-start proposal context and session-end runtime outcomes into a single reviewable change-control summary
- `change_control_index.py` builds a lightweight index over generated session-start and change-control artifacts
- `change_control_summary.py --format human` is optimized for reviewer consumption: one-line summary first, then proposal/runtime detail blocks
- reviewer-facing outputs now also preserve contract metadata such as `contract_domain`, `plugin_version`, and `contract_risk_tier`
- `rule_pack_suggester.py` now also emits advisory `suggested_skills` and `suggested_agent`, keeping agent-role activation recommendation separate from the runtime contract
- it recommends evidence, risk, and oversight, but does not act as a policy engine or auto-decision maker

Kernel-driver governance:

- `kernel-driver` is treated as a high-risk `platform` pack rather than a plain C++ appendix
- the seed pack currently focuses on IRQL boundaries, memory / buffer trust boundaries, and cleanup / unwind symmetry
- `driver_evidence_validator.py` validates normalized evidence from SDV / SAL / WDK-style diagnostics and driver-focused tests
