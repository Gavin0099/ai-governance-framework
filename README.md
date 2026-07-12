# AI Governance Framework

> 讓 AI coding agent 的**邊界、證據、宣稱**可被審核——契約式執行、artifact 證據驗證、fail-closed 決策。

**Version 1.2.0** · Python 3.9+（核心 stdlib-only）· 3,200+ tests · Windows / Git Bash 驗證 · [English summary below](#english-summary)

---

## 這個 repo 是做什麼的？

AI agent 會改你的程式、寫摘要、然後宣稱「任務完成」。這個 framework 的工作是回答三個問題：

1. **它做的事在授權範圍內嗎？**（Task Contract：allowed / forbidden scope）
2. **它說完成，證據撐得住嗎？**（Claim Ceiling：test pass ≠ system safe）
3. **這個 repo 的治理到底導入到什麼程度？**（導入狀態表：哪些防線有、哪些沒有）

它不是讓 AI 更聰明，而是讓 AI 的行為**可見、可審、可歸因**。

> **信任模型（必讀）**：這是 audit framework，不是 security boundary。它在明確定義的 gate 上 fail-closed 並揭露 provenance，但不阻止蓄意繞過工具鏈的 agent。手工繞過會被標記為 `manual_update`（不完整更新），而不是被攔截。

## 為什麼需要它？

在真實 repo 裡，AI 輔助工程的常見失敗不是「寫錯 code」，而是：

- **範圍越界** — 改到需求以外的檔案
- **宣稱膨脹** — 「測試通過」被說成「系統安全」
- **證據不足摘要** — 文字漂亮但無 artifact 支撐
- **觀測 ≠ 治理** — 有 log 就被當成 gate pass
- **記憶污染** — 一次成功 session 被升級成永久知識
- **導入狀態不明** — repo 掛著治理檔案，但沒人知道哪些防線真的有效

## 核心功能

| 功能 | 說明 | Claim class |
|---|---|---|
| **Task Contract + Fail-Closed Gate** | 執行前定義 scope 與 required evidence；已接入 gate 的缺 scope / 缺證據情境會 fail-closed | Enforced for wired gates |
| **Claim Ceiling / Non-Claims** | 每份 closeout receipt 明列「這次結果**不代表**什麼」 | Enforced |
| **導入狀態表（中文）** | 每次更新後輸出「功能 / 狀態 / 這個功能是做什麼」表格：框架本體、hooks、validator、runtime、記憶工作流逐項標示 已可用 / 未導入 / 未驗證 | Report-only |
| **Lock 帳實一致性** | 比對 `framework.lock.json` 與實際 framework checkout，抓出「更新一半」的漂移 | Report-only |
| **F-7 受治理更新流** | submodule / external-contract repo 的受治理更新路徑；copy-based consumer 主要提供 audit / reporting boundary；自動從 `.gitmodules` 發現非標準路徑；手工 bump 標記為 `manual_update` | Advisory |
| **Domain Contract** | 每個領域一份契約：前置條件、禁止假設、證據分級、repo 專屬 validator（kernel-driver、PCIe Gen5、Verilog RTL、USB hub FW 等硬體域方向） | 依 contract |
| **Memory 治理** | canonical writer + authority guard；session 記憶不自動升級為長期知識 | Advisory + selective Enforced |
| **Fleet 治理** | 多 repo 掃描、7 訊號檢查、scope-normalized 成熟度分類 | Observation |
| **多 agent runtime hooks** | claude_code / codex / gemini adapter + dispatcher；session start/end、pre/post task 檢查 | 依 gate |

完整的能力成熟度與 claim class 對照表見 [`docs/REVIEWER_ENTRYPOINT.md`](docs/REVIEWER_ENTRYPOINT.md)。

Scope / allowed-forbidden 規則只有在 repo 實際接上對應 gate、validator 或 hook
時才可宣稱 enforced；沒有接線的規則仍是 reviewer-facing guidance，不是自動執行保證。

## 快速上手

### 前置需求

- Python 3.9+（框架核心零第三方依賴；`requirements.txt` 只為測試與 demo app）
- Git

### 路徑 A｜第一次接觸：驗證框架本身（2 分鐘）

```bash
git clone https://github.com/Gavin0099/ai-governance-framework.git
cd ai-governance-framework

# 治理 smoke test（不需安裝任何依賴）
python governance_tools/quickstart_smoke.py \
  --project-root . --plan PLAN.md \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human

# 框架自我漂移檢查
python governance_tools/governance_drift_checker.py --repo . --framework-root .
```

看到 `[quickstart_smoke]` 輸出 `ok=True`、且漂移檢查輸出 `severity = ok`，就代表環境正常（兩個工具的成功欄位不同：smoke 看 `ok`，漂移檢查看 `severity`）。

### 路徑 B｜導入到你的 repo

```bash
# 完整 onboarding（會安裝 hooks、AGENTS 指引、contract 骨架）
python governance_tools/adopt_governance.py --target /path/to/your/repo

# 先看不改：加 --dry-run
python governance_tools/adopt_governance.py --target /path/to/your/repo --dry-run
```

**導入前先分類**：consumer 角色決定 automation ceiling 與 evidence duty。見 [`docs/ADOPTION_MODEL.md`](docs/ADOPTION_MODEL.md)（submodule / F-7 / contract repo / copy-based audit-only）。最小起步包在 [`examples/starter-pack/`](examples/starter-pack/)。

### 路徑 C｜更新與查看導入狀態（已導入的 repo）

```bash
# 查看目前導入狀態（dry-run，不改任何東西）
python -X utf8 governance_tools/f7_full_update.py \
  --repo /path/to/your/repo \
  --framework-root /path/to/ai-governance-framework \
  --format human
```

輸出會包含 `[human_readable_adoption_summary]` 中文表格：

```text
| 功能 | 狀態 | 這個功能是做什麼 |
| 框架本體（Framework checkout） | 已可用 | 提供 AI Governance 工具與規則來源… |
| 版本帳實一致性（Lock vs checkout consistency） | 不一致 | 比對 lock 的 adopted_commit 與本地 checkout… |
| 本機 commit/push 檢查（Git hooks） | 未導入 | 在本機 commit 或 push 前提示/檢查治理狀態… |
```

確認後加 `--apply` 執行實際更新。**規則**：final report 必須轉述這張表；只回報機器欄位或「F-7 completed」視為不完整更新回報。手工 `git checkout` submodule + 改 lock 的更新只能自我申報為 `manual_update`，不得宣稱 completed。

對 AI agent 說「幫我更新 AI Governance 到最新」時，agent 應走上述受治理路徑——詳見 [`governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md`](governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md)。

## 運作方式

每個 AI 任務經過一條治理生命週期：

```text
Pre Hook          →  載入授權來源 + 產生 task contract
Agent Execution   →  在 contract 邊界內執行
Post Hook         →  獨立 artifact 檢查 + claim ceiling
Decision Gate     →  PASS / FAIL / BLOCKED（預設 fail-closed）
Closeout Receipt  →  可審核收據，含明確 non-claims
Memory Check      →  依資格決定升級，不做自動學習
```

治理文件採分層權威模型：`governance/*.md` 的 frontmatter 由 runtime 機器讀取（authority filter），法典內文供人與 agent 閱讀；[`governance/AUTHORITY.md`](governance/AUTHORITY.md) 是 human-facing 註冊表。canonical > reference > derived，workspace 指引不得覆蓋 repo canonical。

## 適用場景

本框架在**錯誤成本高、需要證據紀律**的領域價值最大。已用或已評估的
domain contract 方向包括：

| 領域 | Contract | 特色 |
|---|---|---|
| Windows kernel driver | Kernel-Driver-Contract | IRQL / DPC / pool type 等 7 個 validator |
| PCIe Gen5 協議 | pcie_g5_contract | LTSSM 等 7 個協議 validator + hard stops |
| Verilog RTL | verilog-domain-contract | 前置條件降級模型 + L0-L3 證據分級 |
| USB Hub 韌體 | USB-Hub-Firmware-Architecture-Contract | 追溯矩陣 + class request 參照 |
| 跨平台桌面工具 | firmware / avalonia consumers | csharp / avalonia rule packs |

此表是 README 導覽，不代表每個列出的 repo 都已完整接上 validator 或達到
full governance adoption。自己寫一份 domain contract：參考 [`examples/`](examples/)
與 domain contract 相關文件。

## 本框架不主張（Non-Claims）

以下是規範邊界，不是免責聲明：

- 不保證 AI 語義正確性；不把 test-pass 當 production-safety 證明
- 不把「matrix-visible」當「verified」；不把 AI explanation 升級為 evidence
- 不把 observation 自動升級為 enforcement；不把 closeout receipt 當「governance complete」
- 不阻止蓄意繞過工具鏈的 agent（手工路徑只能被標記，不能被攔截）
- 導入狀態表為 report-only 本地快照：不 fetch、不代表遠端最新、不證明 hook 在所有機器強制執行

## 專案結構

```text
governance/             # 治理法典（8 大核心文件）、AUTHORITY 註冊表、rule packs、fleet 配置
governance_tools/       # 190+ 工具（2026-07 時點）：導入、更新、漂移、成熟度、記憶、fleet
runtime_hooks/          # claude_code / codex / gemini adapters + dispatcher + core hooks
memory_pipeline/        # 記憶升級邏輯（eligibility-controlled）
baselines/              # consumer repo 的 AGENTS 基準模板
examples/               # starter pack 與範例 contract
scripts/                # hooks 安裝、runtime governance 入口、fleet 掃描
tests/                  # 測試套件（3,200+）
docs/                   # explainer、reviewer 入口、release notes
```

## 文件索引

| 我想要… | 看這份 |
|---|---|
| 最短 reviewer 入口（英文） | [`docs/REVIEWER_ENTRYPOINT.md`](docs/REVIEWER_ENTRYPOINT.md) |
| 完整框架長文（14 節） | [`docs/ai-governance-framework-explainer.md`](docs/ai-governance-framework-explainer.md) |
| 導入模式分類 | [`docs/ADOPTION_MODEL.md`](docs/ADOPTION_MODEL.md) |
| 外部 repo 導入 SOP | [`governance/fleet/external_repo_onboarding_sop.md`](governance/fleet/external_repo_onboarding_sop.md) |
| 「更新到最新版」契約 | [`governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md`](governance/AI_GOVERNANCE_UPDATE_PROTOCOL.md)、[`governance/F7_FULL_UPDATE.md`](governance/F7_FULL_UPDATE.md) |
| F-7 updater 使用說明 | [`docs/fleet/f7-governance-submodule-updater.md`](docs/fleet/f7-governance-submodule-updater.md) |
| Fleet 治理語意 | [`governance/fleet/operational_semantics_v1.md`](governance/fleet/operational_semantics_v1.md) |
| 專案路線圖 / 版本紀錄 | [`PLAN.md`](PLAN.md) / [`CHANGELOG.md`](CHANGELOG.md) |

## Fleet 治理（多 repo）

單次任務之上，框架可掃描整個 repo 群：scope 分類（required / recommended / exempt）→ 每 repo 7 訊號檢查 → 成熟度分類（matrix_only → partial → candidate → verified）。

**Freshness 語意**：`required_verified` ratio 是時間窗內的證據存在性，**不是** repo 健康分數；fleet refresh 是 event-driven（rollout / release 前重新產生 snapshot），閒置期 ratio 衰減是設計行為。最新 snapshot 在 `artifacts/session/`，趨勢在 `governance/fleet/scope_normalized_trend.jsonl`。

## 貢獻

歡迎 PR，請先讀 [`CONTRIBUTING.md`](CONTRIBUTING.md)。修改 governance contract 或 decision boundary 前，請先看 [framework explainer](docs/ai-governance-framework-explainer.md) 的 authority source 要求；治理面變更需通過 `authority_metadata_consistency` 檢查（AUTHORITY 表格必須鏡射 frontmatter）。

## License

見 repository license 檔案。

---

## English Summary

**AI Governance Framework** — contract-bound execution, artifact-backed verification, and fail-closed decisions for AI-assisted engineering.

Your AI agents modify code and claim tasks are complete. This framework makes their **boundaries, evidence, and claims auditable**: task contracts define allowed/forbidden scope; wired gates fail closed on missing scope or evidence; claim ceilings stop "tests passed" from becoming "system is safe"; every closeout receipt states explicit non-claims; a per-repo adoption status table shows exactly which governance surfaces are installed, missing, or unverified.

It is an **audit framework, not a security boundary** — it makes bypass visible and attributable; it does not prevent a deliberately bypassing agent.

Quick start:

```bash
python governance_tools/quickstart_smoke.py \
  --project-root . --plan PLAN.md \
  --contract examples/usb-hub-contract/contract.yaml --format human
```

For the full English reviewer path — claims, non-claims, evidence requirements, and how to read advisory vs enforcement — start at [`docs/REVIEWER_ENTRYPOINT.md`](docs/REVIEWER_ENTRYPOINT.md).
