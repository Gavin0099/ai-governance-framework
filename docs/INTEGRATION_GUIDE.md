# INTEGRATION_GUIDE.md - 整合指南

> **Version**: v1.0
> **Last Updated**: 2026-04-09
>
> 這份文件說明如何把 `ai-governance-framework` 整合進實際 repo，並以最小風險建立可運作的 adoption path。
>
> 這不是 generic platform setup guide；它聚焦的是 **repo-level governance integration**。

---

## 1. 整合目標

整合這個 framework 的目的，是讓 consuming repo 具備以下能力：
- 有 canonical governance baseline
- 有可檢查的 drift / readiness / onboarding surface
- 有最小 memory scaffold 與 governance markdown pack
- 有可執行的 runtime hook / review / status 路徑
- 有 bounded session workflow 與 closeout path

如果你要的是完整 multi-agent orchestration platform，這份指南不是在處理那件事。

---

## 2. 最小整合組成

一個最小、可工作的整合，至少包含：

- framework source（建議用 submodule）
- `adopt_governance.py` 跑過一次
- `.governance/baseline.yaml`
- `AGENTS.base.md`
- `contract.yaml`
- root `PLAN.md`
- `memory/01_active_task.md`
- `memory/02_tech_stack.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`
- `governance/*.md`
- `governance/rules/**`

若缺少這些，通常代表只是把 framework 拉進 repo，還沒有真正 adopt。

---

## 3. 建議的整合方式

### 3.1 使用官方 canonical source

建議使用：

```text
https://github.com/Gavin0099/ai-governance-framework.git
```

不要把落後 fork 當成等價來源。
現在 framework 已經能在 readiness / onboarding / version audit 中顯示 canonical source 是否正確。

### 3.2 用 submodule 導入

典型做法：

```powershell
git submodule add https://github.com/Gavin0099/ai-governance-framework.git additional/ai-governance-framework
git submodule update --init --recursive
```

也可以用直接 clone，但 submodule 較容易保留 consuming repo 自己的 pinned version 決策。

### 3.3 跑 adopt

在 consuming repo 根目錄執行：

```powershell
python additional/ai-governance-framework/governance_tools/adopt_governance.py --target . --framework-root additional/ai-governance-framework
```

這會：
- 建立 baseline
- 複製 governance markdown pack
- 建立 `governance/rules/`
- 建立最小 memory scaffold
- 修補 `contract.yaml` 的必要 documents

---

## 4. Adopt 後的第一輪驗證

### 4.1 檔案存在性

至少確認這些檔案存在：

- `.governance/baseline.yaml`
- `AGENTS.base.md`
- `contract.yaml`
- `PLAN.md`
- `memory/01_active_task.md`
- `memory/02_tech_stack.md`
- `memory/03_knowledge_base.md`
- `memory/04_review_log.md`
- `governance/TESTING.md`
- `governance/ARCHITECTURE.md`
- `governance/rules/common/core.md`

### 4.2 跑 readiness / drift

```powershell
python additional/ai-governance-framework/governance_tools/governance_drift_checker.py --repo . --framework-root additional/ai-governance-framework

python additional/ai-governance-framework/governance_tools/external_repo_readiness.py --repo . --framework-root additional/ai-governance-framework --format human
```

你要確認的是：
- 沒有 critical drift
- `memory_schema_status` 不是隱性 partial
- framework source 是 canonical

### 4.3 跑 quickstart / smoke

```powershell
python additional/ai-governance-framework/governance_tools/quickstart_smoke.py
python additional/ai-governance-framework/governance_tools/runtime_surface_manifest_smoke.py --format human
```

若這些都過，代表 adoption 已經從「文件存在」跨到「基本 runtime 可用」。

---

## 5. Memory 與 Closeout 整合現況

這個 framework 現在已經有：
- memory schema scaffold
- memory sync signal
- memory closeout visibility

但要注意：
- adopt 只保證 scaffold，不保證每次都自動寫 memory
- `session_end` 是否真的被 shared path 接到，要看 consuming repo 的實際 workflow
- closeout 現在能明確輸出：
  - `candidate_detected`
  - `promotion_considered`
  - `decision`
  - `reason`

所以更正確的期待是：
- system 能說明為什麼沒寫
- 不代表它一定會自動幫你寫進 long-term memory

---

## 6. Rule Pack 與 Contract 整合

`contract.yaml` 可宣告：
- `rule_roots`
- `documents`
- repo-local risk / language / domain 資訊

目前最重要的是：
- `governance/rules/` 必須存在
- `documents:` 至少要能把 `TESTING.md`、`ARCHITECTURE.md` 等高價值文件接進 agent 可讀路徑

rule pack name 必須來自 `governance/RULE_REGISTRY.md`，例如：
- `common`
- `python`
- `cpp`
- `csharp`
- `kernel-driver`
- `refactor`

`onboarding` 不是合法 rule pack 名稱。

---

## 7. 常見整合失敗型態

### 7.1 只有 submodule，沒有 adopt

現象：
- framework 在 repo 裡，但 `.governance/baseline.yaml`、memory scaffold、governance pack 都不存在

這代表只是 clone 了 framework，沒有真的導入。

### 7.2 memory schema partial 卻被誤認為完整

舊版本很容易出現：
- 只有 `02_tech_stack.md`
- intake 還能繼續

現在 framework 已補上 partial / complete visibility，但 consuming repo 仍要跑新版工具才能看見。

### 7.3 用錯 framework source

若 consuming repo 指到落後 fork，可能會看到：
- 行為比官方主線舊
- 缺少新 signal / closeout / readiness surface

現在已有 canonical source 檢查，應直接用它辨識。

### 7.4 把 advisory 誤當 authority

advisory signal 目前是 reviewer-visible、non-verdict-bearing。不要在 consuming repo 端自行把它升格成硬裁決依據。

---

## 8. 建議的整合節奏

最穩的節奏是：

1. **導入 source**
2. **跑 adopt**
3. **確認 baseline / memory / governance pack 存在**
4. **跑 drift / readiness / smoke**
5. **確認 runtime hook 至少有一條可讀輸出**
6. **再決定是否接 closeout / audit / reviewer surface**

不要一開始就把所有 signal、status、memory、closeout、advisory 全部一起打開。

---

## 9. 一句話整合原則

> 先把 consuming repo 接成一個可驗證、可檢查、可回退的 bounded governance path，再考慮擴到更多 runtime surface；不要一開始就把整個 framework 當成全自動平台能力一次導入。
