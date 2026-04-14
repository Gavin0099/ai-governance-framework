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
- [x] E8b：canonical audit aggregation / escalation semantics — sliding-window ratio（sort by timestamp, not position）；repo_name best-effort（scope_note always present）；adoption_risk = signal_ratio >= threshold AND entries_read > 0；advisory_only=True hard-coded，NEVER gate.blocked；configurable window_size/signal_threshold_ratio via gate_policy.yaml canonical_audit_trend section；separate result key canonical_audit_trend（與 E7 canonical_path_audit 獨立）；format_human_result 渲染 [ADVISORY] block；5/5 tests
- [x] E1a：canonical usage auditability — _build_canonical_usage_audit() pure synthesis of E7 + E8b into usage_status (observed / missing / observed_with_trend_risk / trend_risk_context)；canonical_key_present（命名精確：marker key present，不宣稱 ingestor 一定被呼叫）；advisory_only=True hard-coded；NEVER gate.blocked；internal_error fallback 不 silent success；basis="E7+E8b synthesis" derivation anchor；format_human_result 渲染 [ADVISORY] for all non-observed states；interpretation layer，非 signal producer；5/5 tests
- [x] E9a：structural absence opt-out — skip_test_result_check: false in gate_policy.yaml（default=false）；GatePolicy.skip_test_result_check bool field；_build_canonical_path_audit suppresses test_result_artifact_absent when skip=True（structural absence declared）；canonical_interpretation_missing still fires normally（artifact must be present to trigger it）；format_human_result shows [skipped] instead of [ADVISORY] when skip+absent；gate.blocked completely unaffected；E8a log still written with signals=[]；return dict carries skip_test_result_check key for display layer；5/5 tests
- [ ] E1b：canonical usage enforcement（強制版） — 只有在 stable observability + 足夠歷史 evidence 後才考慮；E1b 存在的合理性必須由 E8a/E8b 資料面撐腰，不能只靠主張
  - [x] **Phase 1（完成 db5f20f）**: Passive Observation — `_build_e1b_observation()`，advisory_only=True；資料收集 layer，NEVER 影響 gate；見 G5
  - [ ] **Phase 2（進行中，見 G6）**: Distribution Understanding
    - Phase 2 不是純等待，而是兩件事同時進行：
      - A. 等真實 session 在不同 repo 下累積 canonical audit log entries
      - B. 運行 `scripts/analyze_e1b_distribution.py` 觀察 pool 是否正在長成可用分布
    - Analysis surface（G6）至少能回答：repo-level entropy、signal_ratio 分布、degenerate rate、是否有單一 repo 壟斷樣本
    - **Phase 2 → Phase 3 readiness gate（四個條件全部滿足）**：
      1. 總 session 數 ≥ 20（可配置 `--min-sessions`）
      2. 獨立 repo 數 ≥ 3（可配置 `--min-repos`）
      3. 非 degenerate repo 比例 ≥ 0.5（可配置 `--min-nondegenerate`）
      4. 最大單一 repo 佔比 ≤ 0.6（可配置 `--max-dominance`）
    - loop replay 無法代替真實 session（loop 產生退化資料，不具統計效力）
  - [ ] **Phase 3（blocked）**: Trigger Design — 動態 threshold、trend_direction、cross-repo correlation；必須等 Phase 2 readiness gate 全過才能開工；不允許在沒有 evidence baseline 的情況下拍腦袋設 threshold

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

## Phase F Sprint（Adoption Contract Repair）

### 背景
Bookstore-Scraper 和 cli 兩個 adoption test（各 8/8、9/9 PASS，agent=Copilot Tier B）
揭露了三個系統性問題：

1. **Tier B misfit**：Tier B repo 沒寫 closeout → `ok=False`（Tier A 語義強加）
2. **pyyaml silent bypass**：pyyaml 不在 venv → policy 靜默回 builtin_default → `blocked=True`
3. **API parameter bugs**：`session_end_hook.py` 和 `pre_task_check.py` 文件參數名稱錯誤

API bugs 已在 2026-04-14 前的 session 修正（commits `1728e07` / `e318297`）。

### F1 Closeout Contract by Tier
- [x] F1a：`GatePolicy.hook_coverage_tier` 成為 parsed field（str | None）
  - 有效值 A/B/C；invalid → `ValueError`（config error，非靜默 fallback）
  - `governance/gate_policy.yaml`：`hook_coverage_tier: A`（framework default 啟用）
  - `_load_from_path()`：`_build_policy()` 移出 try/except，讓 config ValueError 傳播
- [x] F1b：tier-aware closeout enforcement（`_evaluate_closeout_by_tier()`）
  - Tier A / undeclared：`closeout_missing → ok=False`（violation / fail）
  - Tier B：`closeout_missing → advisory only`（ok 不被拉低）
  - Tier C：`closeout_missing → no enforcement`（ok 不受影響）
  - undeclared 額外 advisory signal：`hook_coverage_tier_undeclared`
  - 結果輸出：`hook_coverage_tier` + `closeout_evaluation` 新增至 result dict
  - `format_human_result()` 渲染 closeout_evaluation（tier/enforcement/ok_effect/signals）
  - 16/16 tests passing（`tests/test_f1_tier_aware_closeout.py`）

### F2 pyyaml Fail-Fast
- [x] F2：pyyaml config presence → hard config error（非靜默 bypass）
  - guard 範圍：`policy_source == POLICY_SOURCE_REPO_LOCAL`（user-declared file）
  - repo-local yaml 存在但 pyyaml 不可用 → `RuntimeError`：refusing silent fallback to builtin default
  - framework default 仍在 pyyaml 缺席時 gracefully fall to builtin（非 user-declared）
  - 2 new tests：F2-1（yaml+nopyaml→RuntimeError），F2-2（noyaml+nopyaml→builtin OK）
  - 18/18 tests passing（`tests/test_f1_tier_aware_closeout.py`，加上 F1 的 16）

### F3 taxonomy_expansion_signal action contract
- [x] F3a：`unknown_threshold` 加入 `BatchDispositionResult` artifact output
  - `BatchDispositionResult.unknown_threshold: int` field（值 = `UNKNOWN_ESCALATION_THRESHOLD`）
  - ingestor warning：`{unknown_count} unknown failures >= threshold ({unknown_threshold})`
  - gate_policy advisory warning：同格式含 threshold 數值
- [x] F3b：action contract doc（`docs/taxonomy-action-contract.md`）
  - 定義 signal 語義、prescribed operator response、threshold tuning 原則
- [x] F3c：2 new tests（`tests/test_failure_disposition.py`）
  - `test_batch_result_carries_unknown_threshold`：artifact to_dict() 含 unknown_threshold
  - `test_taxonomy_signal_threshold_matches_at_boundary`：boundary / off-by-one 確認

### F3.5 observability contract （補強 F2 + F3）
- [x] F2 E2E：`RuntimeError` 從 `_load_from_path()` 穿透至 `run_session_end_hook()` 不被吞掉
  - `test_f2_end_to_end_run_session_end_hook_raises_when_repo_yaml_present_no_pyyaml`
  - `session_end_hook.main()` catch `RuntimeError` → clean fatal message → exit 1
- [x] F3.5 unit：`_add_advisory_warnings()` warning string 契約測試（含 count + threshold 數值）
  - `test_f3_5_add_advisory_warnings_includes_threshold_number`
- [x] F3.5 E2E：hook output warnings 含 threshold 數值（operator 不用看 source code）
  - `test_f3_5_taxonomy_signal_visible_with_threshold_in_hook_warnings`

### F4 Taxonomy Remediation Trace
- [x] F4a：`governance_tools/taxonomy_expansion_log.py` substrate
  - `append_pending_entry()` / `read_log()` / `list_pending()`
  - NDJSON log：`governance/taxonomy_expansion_log.ndjson`
  - Entry schema：`session_id`, `timestamp_utc`, `unknown_count`, `unknown_threshold`
    `review_status`（pending|reviewed|updated|dismissed）, `review_note`, `review_evidence`
- [x] F4b：`session_end_hook` 接入
  - `taxonomy_expansion_signal=True` → `append_pending_entry()` → `taxonomy_expansion_log_entry` 在 result
  - 非阻斷：write 失敗 → warning only，gate 不受影響
- [x] F4c：8 tests（`tests/test_f4_taxonomy_expansion_log.py`）
  - substrate：schema, persistence, list_pending, multi-entry accumulation, empty read
  - E2E：signal fires → log written；signal absent → no log；gate unaffected by log

### F4.5 Remediation State Transition
- [x] F4.5：`update_entry_status()` — pending → reviewed/updated/dismissed
  - rewrite-on-update（governance data 量小，避免 tombstone complexity）
  - returns updated entry or None if session_id not found（不 raise）
  - invalid status → `ValueError`
  - review_note + review_evidence 欄位可一併更新
  - 5 tests added

### F4.6 Close-Path Evidence Expectation
- [x] F4.6：close-path evidence expectation（`_check_close_path_evidence()`）
  - `dismissed` → `review_note` 必須非空（dismissal reason required）
  - `updated` → `review_evidence` 必須非空（taxonomy/corpus change reference required）
  - `reviewed` → `review_note` 或 `review_evidence` 至少一個非空
  - `pending` 無要求（initial state，不是 close path）
  - check 在 apply 新值後、寫入前（resultant state 驗證）
  - check 失敗 → `ValueError`，不寫檔案（caller 可修正後重試）
  - 5 new tests in `tests/test_f4_taxonomy_expansion_log.py`（total 18 tests）
    - dismissed without note → ValueError（entry untouched）
    - updated without evidence → ValueError（entry untouched）
    - reviewed without either → ValueError（entry untouched）
    - reviewed with just note → succeeds
    - dismissed with note → succeeds

### F5 Operator-Facing Output Semantics
- [x] F5a：`gate_verdict` field in `run_session_end_hook()` result dict
  - `BLOCKED` — `gate.blocked=True` OR errors present（production/infra fix required）
  - `NON-GATE-FAILURE` — `ok=False` but gate not blocked（structural/process issue, e.g. missing closeout）
  - `OK+ADVISORIES` — `ok=True` with advisory warnings
  - `OK` — clean
  - `format_human_result()` shows `gate_verdict=` prominently (line 3, after `ok=`)
  - `NON-GATE-FAILURE` prints 3-line reading guide: distinguishes Tier B advisory from hard gate failure
  - `format_human_result()` derives `gate_verdict` inline if not provided（backward-compatible）
- [x] F5b：Semantic prefix labels for warnings / errors in `format_human_result()`
  - Advisory warning prefixes（`[gate_policy:signal]`, `[closeout_evaluation:...]`, etc.）→ `[ADVISORY]`
  - Gate error prefixes（`[GATE:...]`, `[gate_policy:strict]`）→ `[BLOCKED]`
  - Other warnings → `[WARNING]`（no longer plain `warning: `）
  - Other errors → `[ERROR]`（no longer plain `error: `）
  - 28 tests in `tests/test_f5_gate_verdict_semantics.py`（28 passed）

## Backlog

### P0

- [x] 讓 starter-pack 有最小可用的 opt-in upgrade / refresh 路徑
- [x] 確認 regenerated `.governance-state.yaml` 與 runtime/status surfaces 一致

### P1

- [ ] 觀察 session workflow enhancement 的真實 session 分布
- [x] 整理 closeout / advisory / runtime observation 的 maintenance checklist → docs/governance-maintenance-checklist.md（gate policy review / audit log health / advisory signal calibration / E6 corpus / framework-consumer sync）
- [ ] 釐清 consuming repo 常用 workflow 對 memory closeout 的實際可見性

### E8a Phase 2 — Event-Based Measurement Layer（2026-04-14）

**動機**：E8a loop 產生的資料是「靜態狀態 × N 次觀測」，不是「N 個獨立 session 事件」。
這使得 E1b precondition `entries >= 20` 在統計意義上等於 `sample_size = 1`。
需要 artifact lifecycle 時間序列作為 E1b 的有效 input。

**設計合約（已釘住）**：
- event_id = sha1(repo + scenario + t + state_hash)
- state_hash = sha1(exists + content_hash + mtime_floor)
- 去重：consecutive same state_hash = same event（不計入 effective_entries）
- entropy = distinct_states / raw_entries；< 0.3 → E1b invalid measurement

- [x] G1：Event fixture base layer
  - `tests/fixtures/e8a_event_scenarios/base.py`：EventStep dataclass + state_hash/event_id 計算 + entropy helpers
  - `compute_effective_entries`, `compute_entropy`, `compute_signal_ratio` 純函數
  - `validate_monotonic_timeline`：強制 t 嚴格遞增

- [x] G2：三個 lifecycle scenario
  - `scenario_a_normal_ci.py`：absent → create → touch（healthy CI path）；expected ratio≈1/3
  - `scenario_b_broken_pipeline.py`：present → delete → noop（artifact disappears）；expected ratio≈2/3
  - `scenario_c_skip_abuse.py`：absent+noskip → absent+skip → absent+skip（suppression pattern）；expected ratio=1/3
  - 所有 scenario 的 `expected_match_ratio = 1.0`（信號預測完全正確）

- [x] G3：runner `scripts/run_e8a_fixture.py`
  - 逐 t 設定檔案（create/delete/touch/noop）+ 改寫 gate_policy（skip 欄位）
  - 呼叫 `run_session_end_hook()` 得到真實 E8a log entry
  - 計算 state_hash/event_id 並寫入 `artifacts/e8a_fixture_output/e8a-event-log-{scenario}.ndjson`
  - `--repeats N`：重複執行 N 次，讓真實 canonical-audit-log 累積多 session footprint

- [x] G4：validator `scripts/validate_e8a_entropy.py`
  - 讀 event log → 去重 → 計算 effective_entries / entropy / signal_ratio / expected_match_ratio
  - Verdict：VALID（entropy ≥ 0.3）/ INVALID（degenerate）/ EMPTY
  - E1b readiness：READY / PARTIAL / NOT_READY

- [x] G5：E1b Phase 1 — Passive Observation Layer（2026-04-18）
  - `_E1B_MIN_VALID_ENTROPY = 0.3` 常數（`session_end_hook.py`，與 G1-G4 fixture layer 鏡像）
  - `_build_e1b_observation(project_root, window_size) -> dict` 純觀測函數
    - 從 canonical-audit-log.jsonl 讀取當前 window
    - 狀態代理：`artifact_state`（absent / ok / stale / malformed）
    - entropy = distinct_states / entries_in_window
    - is_degenerate = entropy < 0.3（所有 entry 同 state → 無統計解讀能力）
    - signal_ratio：同 E8b 計算，但標籤分離
    - `advisory_only: True` 硬編碼；NEVER 影響 `gate.blocked` 或 `ok`
    - 任何讀取錯誤 → is_degenerate=True、internal_error=True（fail-safe）
  - `run_session_end_hook()` result 新增 key：`e1b_observation`
    - schema：raw_entries, valid_entries, distinct_states, entropy,
      signal_ratio, is_degenerate, observation_note, advisory_only
  - `format_human_result()` 渲染 `e1b_observation:` summary line（always）
    + `[ADVISORY] e1b:` 當 is_degenerate=True 或 internal_error=True
  - **authority boundary 明確釘住**：Phase 1 輸出只能被 read、不能被 enforce
    - advisory_only=True 不得在沒有 PLAN.md 條目的情況下放鬆
  - 6/6 tests (`tests/test_e1b_observation.py`)：empty log → degenerate；均一態 → degenerate；
    混合態 → valid；advisory_only=True 永遠成立；result schema 含 key；format 渲染

- [x] G6：E1b Phase 2 — Distribution Analysis Surface（2026-04-18）
  - `scripts/analyze_e1b_distribution.py`：讀取一或多個 canonical-audit-log.jsonl，計算 per-repo 分布
  - Per-repo 指標：session_count, distinct_states, entropy, is_degenerate, signal_ratio,
    state_breakdown, gate_blocked_count, first_seen / last_seen
  - 跨 repo 聚合：entropy median/p90/p95、signal_ratio median/p90/p95、degenerate rate
  - Phase 2 readiness gate（四條件全過 → READY，可進 Phase 3）：
    - min_sessions ≥ 20（`--min-sessions`）
    - min_repos ≥ 3（`--min-repos`）
    - non-degenerate ratio ≥ 0.5（`--min-nondegenerate`）
    - max repo dominance ≤ 0.6（`--max-dominance`）
  - 支援 `--json` 輸出（機器可讀）
  - 支援多 log path 合併（跨 repo 合并視圖：`--log-path a.jsonl b.jsonl c.jsonl`）
  - 純分析工具，NEVER 影響 gate；不寫入任何 artifact

**執行結果（--repeats 10）**：

| Scenario | verdict | entropy | effective/raw | signal_ratio | expected_match |
|----------|---------|---------|--------------|-------------|---------------|
| a_normal_ci | VALID ✅ | 0.70 | 21/30 | 0.048 | 1.00 |
| b_broken_pipeline | INVALID ✅ | 0.167 | 6/30 | 0.333 | 1.00 |
| c_skip_abuse | INVALID ✅ | 0.033 | 3/30 | 0.333 | 1.00 |

**結論（精確版）**：
- `expected_match_ratio = 1.0` 三個 scenario 全部通過，代表 fixture 期望與 validator 判定完全對齊。
- b/c 被判為 INVALID 是預期且正確的結果，不是 bug。
- 在重複 loop 模擬下，`absent` 狀態沒有前進的 artifact timestamp（mtime_floor=0），
  連續的 absent 步驟會收斂到相同的 state_hash，產生 degenerate dataset。
- 只有具備真實 artifact 狀態前進（如 create / touch）的 lifecycle 才有足夠 entropy
  用於 E1b 統計解讀。

**設計邊界（明確釘住）**：
- 本次驗證支持的是：`E8a loop fixture 只適合驗證有狀態前進的 lifecycle`。
- 對於靜態 absent 類型的模式（b/c），loop replay 只能驗證 validator 會正確拒收
  degenerate data，不能替代真實 session evidence。
- b/c 類型資料在目前設計下，不能靠重複 loop replay 取得統計效力；
  是否能在真實 agent session 中形成足夠 entropy，**仍需後續觀測確認**。
- 這次 `expected_match_ratio = 1.0` 證明的是：fixture 設計與 validator 判定對齊。
  它不是「E1b 已在真實 repo / 真實 agent workflow 下完成實證」的依據。

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
