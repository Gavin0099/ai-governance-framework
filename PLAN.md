# PLAN.md - AI Governance Framework

> **最後更新**: 2026-04-10
> **?敺??*: 2026-04-10
> **Owner**: GavinWu
> **Freshness**: Sprint (7d)
> **Risk Tier**: L2
> **Planning Window**: 2026-03 ~ 2026-06

---

## 專案目標

本 repo 的目標是把 AI 治理從靜態提示與散落文件，收斂成可被 runtime 消費、可被 reviewer 重建、也可被外部 repo 採用的治理框架。

目前主線聚焦在五個面向：

- execution / evidence / decision 的可驗證治理流程
- session workflow 與 closeout 的 canonical artifact 化
- memory / state 的可觀測更新與 closeout 決策
- external repo adoption、readiness、version/source audit
- 高可見度 governance 與 docs 入口的可讀性與維護性

## 邊界

- 本 repo 不是 full execution harness
- 本 repo 不是 machine-authoritative advisory system
- 本 repo 不是 generic multi-agent orchestration platform

---

## 階段總覽

- [x] Phase A : 建立治理工具核心與 baseline
- [x] Phase B : 補齊 adoption / validator / freshness / memory 基礎能力
- [x] Phase C : 建立 runtime governance、DBL 與 observation surfaces
- [x] Phase D : 收斂 session workflow、external adoption 與文件入口
- [>] Phase E : Failure decision boundary、exclusion governance、usage enforcement

## Current Sprint

- [x] 穩定 canonical closeout、closeout audit 與 session continuity 主線
- [x] 補齊 consuming repo adoption 缺口，包括 governance markdown pack、rules pack 與 framework source audit
- [x] 補上 memory closeout visibility，讓 no-write reason 可觀測
- [x] 修正高可見度 docs / governance 文件的亂碼與英文主敘事殘留
- [x] 重建 root PLAN / state source of truth，讓 state_generator 與 freshness surface 回到可維護狀態
- [x] 建立 starter-pack 自動升級路徑，讓 starter-pack 不只停在手動複製

## Phase E Sprint（Current）

- [x] E1：建立 failure_disposition.py（FailureKind + ActionPolicy + confidence）
- [x] E1.5：seed corpus 10 筆 ground truth，作為 taxonomy calibration baseline
- [x] E2：建立 test_exclusion_registry.yaml + exclusion_registry_tool.py
- [x] E2+：run_filtered_tests.py — 唯一合法的 filtered suite 入口，強制 registry 使用
- [x] E3-Slice1：test_result_ingestor._apply_failure_disposition — 所有 ingest 自動分類，不可繞過
- [x] E3-Slice1.5：test_result_ingestor main() 加 --out PATH，寫標準 artifact（artifacts/runtime/test-results/latest.json）
- [x] E3-Slice2：session_end_hook.format_human_result 顯示 failure_disposition 摘要（verdict_blocked / [GATE] / [SIGNAL]）
- [x] E3-Slice3：session_end_hook.run_session_end_hook 讀 test-results artifact — production_fix_required → ok=False gate
- [x] E4：gate_policy.py + governance/gate_policy.yaml — 顯式 fail_mode（strict/permissive/audit），artifact state 語義分化（absent/malformed/stale/ok），blocking_actions 可配置，unknown_treatment 可配置；session_end_hook 不再 hardcode 任何 gate Logic
- [x] E5：repo-local gate policy discovery + provenance — project_root/governance/gate_policy.yaml 優先；fallback → framework default → builtin；policy_source / policy_path / fallback_used / repo_policy_present reviewer-visible；session_end_hook 傳 project_root；repo_local_policy_missing warning 顯式暴露 adoption 缺口
- [x] E6：replay_verification.py — re-runnable decision-path evidence tool；seed corpus 每筆 case 兩層驗證（classification correctness + gate-effect correctness）；evidence artifact 寫入 artifacts/runtime/replay-evidence/latest.json；10/10 兩層全通；evidence_scope 明確標示 claim 邊界（seed corpus only）
- [x] E7：canonical path usage audit — session boundary footprint observability；_build_canonical_path_audit() 純函數；ArtifactResult.failure_disposition_key_present 區分 key absent vs null；advisory signal（test_result_artifact_absent / canonical_interpretation_missing）接入 session_end_hook warnings + human output；5/5 tests
- [x] E8a：canonical audit signal persistence — append-only observability JSONL；repo-local（project_root/artifacts/runtime/canonical-audit-log.jsonl）；non-authoritative（observability substrate，不是 authority of truth）；每筆含 timestamp / session_id / repo_name / artifact_state / signals / gate_blocked / policy provenance；rotation 上限 500 筆；tmp-file swap atomic write；寫入失敗降聲吞嚺；5/5 tests
- [ ] E8b：canonical audit aggregation / escalation semantics — 建立在 E8a 持久化資料上；repeated advisory thresholds；adoption risk signals；reviewer-facing summary；不直接 block；需要先確認 session identity 定義與 rotation 語意
- [ ] E1a：canonical usage auditability（弱觀測版） — after-the-fact footprint checks；advisory only；不宣稱 runtime exclusivity；與 E7/E8 重疊的部分視 E8a/E8b 完成程度決定剩餘 scope
- [ ] E1b：canonical usage enforcement（強制版） — 只有在 stable observability + 足夠歷史 evidence 後才考慮；E1b 存在的合理性必須由 E8a/E8b 資料面撐腰，不能只靠主張

> 排序根據：E8a 先讓 signal 有歷史，E8b 才能讓歷史有語意，E1a/E1b 再決定是否有可靠證據基礎支持更強約束。
> E1b 不等同於「系統已 enforce agent behavior」——agent 中途決策無法直接 observe，強制版頂多能驗到 artifact footprint 層，不能聲稱 runtime exclusivity。

## Phase E Decision Impact

> 這節記錄 Phase E 的改變對系統行為的實際影響，不是進度紀錄。

| 面向 | Before E1/E2 | After E1/E2 |
|------|-------------|-------------|
| Failure 判斷 | 人工看 pytest 結果做分類 | 必須經過 `FailureKind → ActionPolicy`，有 confidence 標記 |
| Filtered suite 邊界 | 手寫 `-k "not xxx..."` 字串，implicit | 由 `test_exclusion_registry.yaml` 生成，每條有 justification / expiry |
| Unknown failure 處置 | 無規則，agent 自行判斷 | 強制 `escalate`，禁止 `ignore_for_verdict` |
| Registry 腐化偵測 | 無 | `audit` 指令偵測過期/缺 justification/integrity 違規 |
| Session 行為強制 | failure_disposition opt-in，agent 可繞過 | session_end_hook 讀 artifact → `production_fix_required` → `ok=False` 強制 gate |
| Test result artifact | 無標準路徑 | `test_result_ingestor --out artifacts/runtime/test-results/latest.json` |
| Gate 決策 authority | Hardcoded `except: pass` fail-open | `governance/gate_policy.yaml`：fail_mode / blocking_actions / unknown_treatment 可配置；artifact absent/malformed/stale 語義明確 |
| Gate authority 歸屬 | Framework 替所有 repo 做決定 | Consuming repo 可放置自己的 `governance/gate_policy.yaml`；policy_source / fallback_used reviewer-visible；缺少 repo-local policy → 顯式 warning |
| Decision correctness evidence | 無 | `replay_verification.py`：每次可重跑，兩層比較（classification/gate-effect），機器可讀 JSON artifact + 人類可讀摘要，evidence_scope statement 精確聲明 claim 邊界 |
| Canonical path observability | 無 | `session_end_hook` 在 session boundary 驗證 canonical interpretation footprint；`failure_disposition_key_present` 區分 key absent 與 null；advisory signal 透明表明局面（不 blocking） |
| Multi-session footprint history | 無 | `_append_canonical_audit_log()`：append-only JSONL per repo-local path；每筆含 session_id / repo_name / signals / policy provenance；rotation 500 筆；non-authoritative observability substrate，不是 authority of truth |

**E2+ 完成後的強制約束：**
- filtered suite 只能透過 `run_filtered_tests.py` 執行，不允許手寫 `-k`
- 這不是建議，是 tooling 層的唯一入口

## Backlog

### P0

- [x] 讓 starter-pack 有最小可用的 opt-in upgrade / refresh 路徑
- [x] 確認 regenerated `.governance-state.yaml` 與 runtime/status surfaces 一致

### P1

- [ ] 觀察 session workflow enhancement 的真實 session 分布
- [ ] 整理 closeout / advisory / runtime observation 的 maintenance checklist
- [ ] 釐清 consuming repo 常用 workflow 對 memory closeout 的實際可見性

### P2

- [ ] 評估 BUG-003 後續是否需要從 byte-size 再擴到更高階的多維記憶壓力信號
- [ ] 評估 starter-pack 升級路徑是否要補 lock/manifest，而不是只有 refresh

---

## 目前主線

### 1. Session Workflow Enhancement

- producer / canonical / consumer 已分層
- consumer 只吃 canonical closeout
- closeout audit 維持 aggregation only，不長第二套 authority
- 目前狀態：implementation-complete, semantics-observation phase

### 2. Memory Closeout

- `session_end` 已輸出 `memory_closeout`
- 可區分 candidate detected / promotion considered / decision / reason
- 目前補的是可見性，不是 promotion 擴權

### 3. External Adoption

- adopt 會帶入 governance markdown pack 與 rules pack
- readiness / onboarding / version audit 會檢查 canonical framework source
- consuming repo 不再只看版本號，也會看 framework repo 來源是否正確

### 4. Documentation Surface

- `governance/` 與 `docs/` 的高可見度入口已大致改成中文主敘事
- 後續進 maintenance mode，只修真正會影響理解的殘留問題

---

## 風險與提醒

- `/wrap-up` 目前是 candidate drafting surface，不是 closeout 官方 authority
- advisory slice 目前是受限、reviewer-visible、non-verdict-bearing 的語義層
- starter-pack opt-in upgrade path 已完成（`upgrade_starter_pack.py`），README 有手動/自動分界說明
- `.governance-state.yaml` 已可重新生成且內容可讀

---

## 完成定義

本 sprint 要達成的最低條件：

- [x] `PLAN.md` 可被 `state_generator.py`、`plan_freshness.py` 穩定解析
- [x] `.governance-state.yaml` 能重新生成且內容可讀
- [x] starter-pack 有明確的 opt-in upgrade path
- [x] starter-pack README 說清楚手動初始化與自動升級的分界

---

## 決策紀錄

| 日期 | 決策 | 說明 |
|---|---|---|
| 2026-03-30 | 不直接擴張 entry layer | 先建立 justification / boundary，再決定是否授權 runtime 擴張 |
| 2026-04-01 | execution completeness 先於 harness | 先做 coverage / decision context，不先做 execution harness |
| 2026-04-02 | advisory signal 停在 reviewer-visible 邊界 | 不把 advisory 過早接進 verdict authority |
| 2026-04-08 | session workflow enhancement 主線收斂 | 進入 semantics-observation phase |
| 2026-04-10 | 先修 source of truth 再做 starter-pack upgrade | 避免在壞掉的 state surface 上擴 starter-pack 流程 |
| 2026-04-10 | Phase D sprint 全部完成，進入 maintenance mode | state source of truth 重建、starter-pack upgrade path 完成，三端同步 |
| 2026-04-10 | E1/E2 建立 failure decision boundary | failure 不再直接看 pytest 結果；filtered suite 不再手寫 -k；unknown 必須 escalate |
| 2026-04-10 | E2+ 強制 registry 使用，禁止 bypass | run_filtered_tests.py 成為唯一合法入口；手寫 -k 視為違規 |
