# PLAN.md - AI Governance Framework

> **最後更新**: 2026-04-16
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
    - **Phase 2 → Phase 3 readiness gate（五個條件全部満足）**：
      1. 總 session 數 ≥ 20（可配置 `--min-sessions`）
      2. 獨立 repo 數 ≥ 3（可配置 `--min-repos`）
      3. 非 degenerate repo 比例 ≥ 0.7（可配置 `--min-nondegenerate`）
      4. 最大單一 repo 佔比 ≤ 0.6（可配置 `--max-dominance`）
      5. unique session pattern ratio ≥ 0.4（可配置 `--min-unique-pattern`）
         — 防止 pseudo-diversity：3 個 repo 但全部跑同一種生命周期 pattern
      『 advisory 不是 gate 條件』 degenerate_rate < 0.05 → 「low (verify coverage)」警告》
         — degenerate_rate 太低也可能代表 broken-pipeline / skip-abuse scenario 沒有被觀測到
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
  - 新增 `_session_fingerprint(entry)`：(artifact_state, sorted_signals, gate_blocked) 元組
    主要防御：3 個 repo 但跑同一種 lifecycle pattern → unique_pattern_ratio 挪出 pseudo-diversity
  - 新增 `degenerate_rate_interpretation`（advisory，不是 gate blocker）：
    - < 0.05 → 「coverage review required」—— 確認是真正健康，而非 broken-pipeline 根本未被觀測；degenerate_rate 低本身不是問題，但需要能回答「為什麼低」
    - 0.05–0.30 → 「expected mixed」
    - > 0.30 → 「high — possible systemic instability」
  - Phase 2 readiness gate（**五條件**，全過 → READY，可進 Phase 3）：
    - min_sessions ≥ 20（`--min-sessions`）
    - min_repos ≥ 3（`--min-repos`）
    - non-degenerate ratio ≥ 0.7（`--min-nondegenerate`，從 0.5 提高）
    - max repo dominance ≤ 0.6（`--max-dominance`）
    - ~~unique_pattern_ratio ≥ 0.4（`--min-unique-pattern`）~~ ← **已廢棄（2026-04-15）**
      → 替換為 **`lifecycle_active_ratio ≥ 0.5`（`--min-lifecycle-active`）**
      = lifecycle_capable repos 中 lifecycle_class != stuck_absent 的比例
      原因：unique_pattern_ratio 是 non-identifiable metric——健康 fleet 也會低（stable_ok 收斂到同一 fingerprint）；
      lifecycle_active_ratio 才能正確區分「真的有跑 lifecycle」vs「宣告 capable 卻從沒跑」
  - **Gate 分層結構（不得混用，已釘住）**：
    - **Type A（存在性 gate）**：`distinct repos ≥ 3` + `lifecycle_active_ratio ≥ 0.5`
      回答：有沒有足夠多活的樣本池？
      `lifecycle_active_ratio` 是「樣本池是否活著」指標，**不是「樣本池是否成熟」指標**。
      `stable_ok` 與 `mixed_active` 在這裡都算過——兩者的包含是此指標的 naive 粗粒化上限，
      不代表 mixed_active 等同 stable_ok（後者的語意差距交由 Type B 回答）。
    - **Type B（品質 / 分布 gate）**：`non-degenerate ratio ≥ 0.7` + `dominant repo ≤ 0.6`
      回答：樣本池品質與分布是否夠好？
    - **診斷次序**：SA 接通 → Type A 有機會過 → 再看 Type B 兩條——這才是正確的進度鄰接。
      SA 接通**只解存在性**，不等於 Type B 自動通過；Type B 需要 Stage 2/3/4 的累積。
    - **Type A PASS 的語意邊界（不得混淆）**：
      **Type A PASS 只表示樣本池具備可評估性，不表示樣本池已具備可通過性。**
      Type A 過，代表終於有足夠活著的母體可以開始認真看品質；
      不代表品質已經好、readiness 快通過、Phase 3 近了。
    - **SA → Condition 5 的前提**：`lifecycle_active_ratio` 通過的前提是 SA stuck_absent 被穩定脫離。
      若 SA 後續在 `mixed_active` 與 `stuck_absent` 間抖動，Condition 5 仍展神。
      正確說法：**SpecAuthority 完成 Layer 1 且穩定脫離 stuck_absent，Condition 5 才會自然通過。**
  - 支援 `--json` 輸出（機器可讀）
  - 支援多 log path 合併（跨 repo 合并視圖：`--log-path a.jsonl b.jsonl c.jsonl`）
  - 純分析工具，NEVER 影響 gate；不寫入任何 artifact
  - **設計邊界（已釘住，不得遺忘）**：
    1. `_session_fingerprint` 是 gate guard，不是 session type classifier。同 fingerprint ≠ 同 operational meaning（absent 可能是短暫缺失、長期靜態、create 後被刪的 tail-state）。若 Phase 3 需要 pattern-level 分析，fingerprint 必須升級再使用。
    2. `min_nondegenerate=0.7` 是 pre-empirical 政策值，不是 empirically derived threshold。它是在沒有 baseline 的情況下避免爛資料主導判斷的保守選擇。若未來觀測到真實分布，可以依據數據調整，但在有數據之前不能用「0.7 被實證」來宣稱。
    3. `degenerate_rate` 解讀層的目的是 coverage review，不是紅旗。degenerate_rate = 0 不是 fail，它是一個可解釋性要求：需要回答「是真的健康，還是觀測面太窄」。
  - **Phase 2 真正的下一步**：用現有工具跑第一批真實資料，觀察五條 gate 哪條最先被卡，那才是比繼續修 gate 更有資訊量的動作。

---

### Phase 2.5 — Fleet Reality Assessment（2026-04-18）

**觀測結果（10 repos / 272 sessions）**：

| Repo | skip | policy_source | 信號歷史 | 評估 |
|------|------|---------------|---------|------|
| Bookstore-Scraper | false | repo_local | ok:40 absent:1 | **lifecycle 正常運作** |
| gl_electron_tool | true | repo_local | 前 20 sessions 有 signal，後零 | skip 是在初期幾次 session 之後才寫入；signals 是 pre-skip 歷史 artifact |
| hp-oci-avalonia | true | repo_local | 第 1 筆是 framework_default + signal，之後零 | 第一次 session 無 repo-local policy，配置後 signal 消失 |
| cli | true | repo_local | 前 2 筆是 builtin_default + signal，之後零 | 前兩次 session 無 repo-local policy，配置後正常 |
| Enumd | true | repo_local | 0 signals 全程 | Python/JS repo，聲明 no pytest runner |
| Standard_ISP_Tool | true | repo_local | 0 signals 全程 | skip=true，**無說明原因**（待補） |
| Kernel-Driver-Contract | true | repo_local | 0 signals 全程 | contract/doc repo，正確 declared |
| SpecAuthority | true | repo_local | 0 signals 全程 | Python repo，聲明 no pytest runner |
| lenovo_isp_tool | true | repo_local | 0 signals 全程 | C# firmware，正確 declared |
| ai-governance-framework | false | repo_local | 1 筆 absent + signal | 框架本身，尚未有 test artifact |

**fleet 分類（事後）**：

| 分類 | Repos | 含義 |
|------|-------|------|
| `declared_no_test` ← 正確 | gl_electron_tool, hp-oci-avalonia, Kernel-Driver-Contract, lenovo_isp_tool | 非 Python 技術棧，lifecycle 不會發生，skip 語意正確 |
| `test_expected_not_wired` ← 採用缺口 | Enumd, SpecAuthority | Python repo，但未配置 pytest；skip 是 workaround，不是宣告 |
| `test_requires_ci` ← infra gap | cli | C++ GTest 需要 CI Docker，本地不可執行；正確聲明 |
| `undeclared_reason` ← 需補說明 | Standard_ISP_Tool | skip=true 但無 comment，無法確認分類 |
| `lifecycle_active` ← 目標狀態 | Bookstore-Scraper | test 跑通，lifecycle 正常 |

**關鍵發現（修正前一版的錯誤判斷）**：

1. **「absent + signals」不是執行斷裂**。三個 repo（gl/hp/cli）的 signals 全部來自「尚未配置 gate_policy.yaml 的早期 session」。policy 配置後 signal 消失。這是配置時序問題，不是 ingestor 斷裂。

2. **degenerate_rate = 0.9 是正確反映 fleet 選擇，不是 instability**。9/10 repos 聲明 skip=true（其中大部分有明確理由）。這不是系統壞掉，是 fleet 主動選擇不走 artifact lifecycle。

3. **E1b gate 卡在第 3、5 條是因為 fleet 組成，不是資料不夠**。即使再累積 10,000 sessions，degenerate_rate 仍會在 0.9 附近，unique_pattern_ratio 仍會很低。這個 gate 設計是基於「假設 fleet 有混合 lifecycle」，但現實 fleet 主要是 skip。

**Phase 2.5 的核心選擇（需要明確對齊）**：

> E1b 裡想要觀測的「lifecycle entropy」，前提是 fleet 裡有足夠多的 repo 在走 artifact lifecycle。
> 現實是 fleet 裡至少 60% 的 repo 永遠宣告 skip。
> 這意味著：是要把 E1b 當「監測已走 lifecycle 的 repo 健康」，還是「推動更多 repo 走 lifecycle」？

| 策略 | 含義 | 下一步 |
|------|------|--------|
| A. Observation scope   | E1b 只分析 `skip=false` 的 repo；skip repo 不進 entropy 計算 | 重新設計 analyze tool 以排除 skip repo；有效 pool = Bookstore-Scraper + cli（CI）|
| B. Adoption driver | E1b 作為壓力：要求 Enumd、SpecAuthority 實際配置 pytest；skip 需要人工 review | 對 `test_expected_not_wired` 分類的 repo 建立最小的 pytest onboarding 路徑 |
| C. Dual-track | skip repo 進 `fleet_coverage` 報表；active repo 進 `entropy quality` 報表 | 分層輸出，兩個 tier 有不同 gate 條件 |

**目前建議**：策略 A 是最誠實也最省力的 immediate fix；策略 B 是中期目標（Enumd + SpecAuthority 值得推動）；策略 C 是將來 Phase 3 前的正確形式。

**Standard_ISP_Tool 待辦**：補 gate_policy.yaml 的 skip 說明 comment。

**決策（2026-04-18 執行）**：採用 **策略 C + A**（dual-layer report + lifecycle-capable 子母體）。

實施內容：
- `gate_policy.yaml` schema 新增 `skip_type: structural | temporary` 欄位（含驗證，invalid 值嚴格拒絕）
- `GatePolicy` dataclass 新增 `skip_type: str | None = None`；透過 `to_provenance_dict()` 傳入 E8a log
- `session_end_hook.py` — E8a log policy_provenance 現在記錄 `skip_type`
- `analyze_e1b_distribution.py` 重構為雙層輸出：
  - **Layer 1 (Fleet Coverage)**：所有 repo 分類（lifecycle_capable / structural_skip / temporary_skip / unclassified_skip）
  - **Layer 2 (Entropy Quality)**：僅 lifecycle_capable 子母體，phase 2 readiness gate 只對此母體負責
- `compute_fleet_coverage()` 獨立函式，`evaluate_phase2_gate()` 改為 lifecycle-capable only
- 8 consuming repos gate_policy.yaml 已補 `skip_type` 標記：
  - `structural`：gl_electron_tool, hp-oci-avalonia, Kernel-Driver-Contract, lenovo_isp_tool, Standard_ISP_Tool
  - `temporary`：cli, Enumd, SpecAuthority
- 新增 4 個 skip_type 測試（parse structural/temporary、拒絕 invalid、預設 None）

現況（C+A 實施後）：
- fleet 1 lifecycle_capable repo（ai-governance-framework），Phase 2 gate 繼續 NOT_READY，但現在給出正確的理由：母體只有 1 repo / 1 session
- `skip_type: structural` = 永遠不適用（非 Python 技術棧）
- `skip_type: temporary` = 理論上可以，但尚未接通（採用缺口）

**Phase 2.5 Hardening（2026-04-14）— 防誤用層**：

三個防誤用機制加入 `analyze_e1b_distribution.py`：

1. **structural_skip consistency advisory**（`structural_skip_inconsistencies`）
   - 檢查：`skip_type=structural` 但曾出現 `signal_ratio > 0` 或 non-absent state
   - 語意：觀測資料反推 policy 誠實性。structural 宣告代表「永遠不走 lifecycle」，
     若有 lifecycle activity 出現，代表 skip_type 可能是逃避 governance 的標籤
   - 行為：soft advisory（不 block gate），輸出在 Layer 1 Fleet Coverage 區塊

2. **temporary_skip aging**（`temporary_skip_aging`）
   - 計算每個 temporary skip repo 的 `age_days`（`first_seen` 起算至今）
   - Stale 閾值：90 天（`_TEMPORARY_SKIP_STALE_DAYS`）
   - 語意：temporary 是「理論上可以，但尚未接通」的狀態，不是永久分類。
     如果一直不轉正（變 lifecycle_capable），會顯示 `[STALE >90d]`
   - 行為：Layer 1 Fleet Coverage 顯示 aging table

3. **lifecycle_capable_ratio**（`lifecycle_capable_ratio`）
   - 計算：`lifecycle_capable_count / total_repos`
   - 閾值：< 0.3（`_LIFECYCLE_CAPABLE_MIN_RATIO`）觸發 `baseline_not_representative`
   - 語意：就算 Phase 2 gate READY，如果 lifecycle_capable 母體佔 fleet < 30%，
     這個 baseline 只反映少數健康 repo 的狀態，不代表 fleet 整體 adoption 現況
   - 行為：Layer 1 顯示 `[LOW]` 標記；Layer 2 Gate 下方顯示 advisory banner

**語意邊界（強制明記）**：

> **E1b ≠ adoption completeness**
>
> E1b 只評估 lifecycle-capable 子母體的 entropy quality。
> ``lifecycle_capable_ratio`` 低不影響 Phase 2 gate 的 READY/NOT_READY 判定，
> 但會觸發 advisory 警告：這個 baseline 不代表 fleet 現實。
>
> 要知道「有多少 repo 走了 lifecycle」→ 看 ``lifecycle_capable_ratio``（Fleet Coverage）
> 要知道「走了 lifecycle 的 repo 品質如何」→ 看 Entropy Quality（E1b gate）
>
> 兩者是正交指標，不能互相替代。

**Phase 2.5 Temporal Hardening（2026-04-14）— 時間維度防護**：

三個問題的修正：

1. **Temporal Drift — 歷史資料與新語意混用**
   - 問題：舊 log entries 無 `skip_type`，一律算 `lifecycle_capable`，與新語意混用
   - 修正：加入 `skip_type_coverage_ratio`（每個 entry 是否攜帶 skip_type 欄位的比率）
   - Fleet ERA 標籤：`CURRENT` ≥ 0.7 / `TRANSITION` ≥ 0.3 / `PRE-SKIP-TYPE-ERA` < 0.3
   - 目的：報表消費者可判斷「這份 distribution 是在語意完整之前還是之後建立的」

2. **Structural consistency false positive — 暫態不一致的誤報**
   - 問題：舊 guard 對整個 repo 歷史做 `signal_ratio > 0` 判斷，把 pre-policy 配置前
     的 signal（正常採用序列）也當作語意矛盾
   - 修正：改用 `post_skip_lifecycle_count`（只看 `policy_provenance.skip_type` 已設定
     的 entries 是否還有 lifecycle activity）
   - 效果：pre-policy 的 signal 不再觸發 advisory；只有「明確宣告 structural 後
     卻仍在走 lifecycle」的情況才算矛盾

3. **Temporary aging lacks progress — 時間 vs 進展的分離**
   - 問題：stale 標記只看天數，無法分辨「慢但在動」vs「完全死掉」
   - 修正：加入 `fingerprint_diversity`（distinct session fingerprints / session_count）
   - `activity` 欄位：`slow`（diversity > 0.1，lifecycle pattern 有在變化）vs `dead`
     （diversity ≤ 0.1，lifecycle pattern 完全凍結）
   - 意義：兩種 stale temporary 的治理行動完全不同：
     slow = 需要耐心或 CI infra 支援
     dead = 需要重新評估是否應改為 structural 或真正接通 lifecycle

**三層觀測模型（E1b 的完整架構）**：

```
Layer 1 — Coverage（誰在玩）
  lifecycle_capable / structural_skip / temporary_skip
  lifecycle_capable_ratio
  skip_type_coverage (ERA 標籤) ← 新：時間維度
  structural inconsistencies    ← 新：post-policy only
  temporary aging + activity    ← 新：slow vs dead

Layer 2 — Quality（玩得好不好）
  entropy / signal_ratio / gate readiness
  degenerate detection
  unique_pattern_ratio

Layer 3 — Integrity（有沒有自欺）
  structural consistency (post-policy guard)
  temporary aging (adoption-dead detection)
  baseline_representative (lifecycle_capable_ratio)
  temporal era (skip_type_coverage_ratio)
```

> **E1b 不再僅是統計指標，而是結合 coverage、quality 與 integrity 的觀測系統。**
> Phase 2 的目標不是通過 gate，而是確保觀測結果在語意、時間與母體上具備可解釋性。

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

---

**E1b 作為 Adoption Failure Detector（2026-04-14 fleet 實地診斷）**

首次以全艦隊視角（10 repos / 272 sessions）執行 `analyze_e1b_distribution.py`，觀測到：

| 指標 | 數值 |
|---|---|
| degenerate repos | 9/10 (90%) |
| entropy median | 0.042 |
| sig_ratio median | 0.024 |
| unique session patterns | 4/272 (ratio=0.015) |

**兩層原因必須分開處理（不能混在一起）：**

**Layer A — skip_type migration 未完成（PRE-SKIP-TYPE-ERA）**
- 所有 audit log entries 均無 `skip_type` 欄位
- skip_type-based classification（structural/temporary/lifecycle_capable）**UNAVAILABLE**
- 這是 control plane 與 data plane 的時間差，需要補 post-schema session 解決
- 解法：在各類型 repo 實際完成 session，讓 audit log 產生攜帶 `skip_type` 的條目

**Layer B — lifecycle 根本沒有被執行（與 skip_type 完全無關）**
- `artifact_state` 幾乎永遠是 `absent`（lifecycle gate 從未被走過）
- 這是獨立的 adoption 問題，不是 ERA 偏差
- **即使 skip_type migration 完成，Layer 2 的 degenerate pattern 很可能仍然存在**

> 兩層原因是正交的。Layer A 修完不會讓 Layer B 消失。必須分別追蹤與處理。

**關鍵結論（不可被 PRE-ERA 狀態覆蓋）：**

> 9/10 repos degenerate 不是因為資料還沒準備好，而是因為 E1b 偵測到
> **大部分 repo 根本沒有進入 lifecycle**。
> skip_type migration 只會讓這個結論更可解釋，不會讓它消失。

**E1b 的角色轉換：**

E1b 原本設計為「統計品質測量工具」，但全艦隊資料揭露了一個更重要的功能：

> **E1b 是 adoption failure detector** —— 它能精確識別哪些 repo「應該走 lifecycle 卻沒走」。

**下一步行動優先序（已修正）：**

| 步驟 | 目標 | 問題類型 |
|---|---|---|
| Step 1 | 跑 3–5 個 post-skip-type session | Layer A：讓 PRE-ERA 結束，classification 可用 |
| Step 2 | 針對 9 個 degenerate repo 診斷：lifecycle 為何沒發生 | Layer B：真實 adoption 問題 |
| Step 3 | 分類 degenerate 原因（no-test / 未接通 / CI-only / tool gap） | Layer B：治理行動分類 |

**degenerate repo 原因分類框架：**

| 類型 | 可能原因 | 治理行動 |
|---|---|---|
| 真正 no-test | 無 artifact lifecycle 可走（正常 structural） | 確認 skip_type=structural |
| test 可跑但未接通 | adoption gap | 引導接通 lifecycle gate |
| CI-only | workflow 未整合 | infra 支援 |
| tool 未 integration | system gap | onboarding 補完 |

**語意釘住：**
- `lifecycle_capable_ratio = 1.0（10/10）`：因為 PRE-ERA，所有 repo 被視為 lifecycle_capable（假陽性）
- `degenerate_rate = 0.9`：這是真實觀測，不是測量誤差
- 兩者都需要 Layer A 修完後才能再評估實際分布，但 Layer B 的問題現在已經可以行動

---

**E1b v2 shadow metrics — 設計邊界（2026-04-14，`bea9a03`）**

`lifecycle_class`（stuck_absent / stable_ok / mixed_active）已加入 `compute_repo_stats()` 作為 shadow 指標。最嚴重的 false positive（把 `stable_ok` 的 Bookstore-Scraper 判成 degenerate）已被修正。

**已解決的問題：**
> v2 修正了 legacy 將「低變化」錯判為「無效資料」的問題，並初步把 lifecycle 狀態拆成健康穩態、未執行穩態與未定型活動態三類。

**三個語意邊界（不得混淆）：**

**① `mixed_active` 的語意仍然過寬**

目前 `mixed_active` 同時代表兩件不同的事：
- 資料不足無法判斷（1 session）
- 真實有狀態變化（absent/ok/stale 之間切換）

這兩者在治理決策上完全不同：前者不能算 progress，後者才是。
未來當 v2 升格為正式 gate blocker 之前，`mixed_active` 必須拆成：
- `insufficient_evidence`（session count 太少）
- `transitioning_active`（真實狀態變化）
否則 `mixed_active` 會成為新的大垃圾桶。**現在不改，但語意邊界必須清楚記錄。**

**② `stable_ok` ≠ 統計代表性，只是語意正確**

`stable_ok` 解決的是誤判問題（不應被當 degenerate），不是直接等於「可作為 baseline」。
一個 repo 可能長期穩定 ok，但同時：
- 樣本數仍少
- fingerprint 幾乎單一
- 只反映單一 workflow

因此：`stable_ok` 是必要條件，不是充分條件。與統計代表性判斷分開處理。

**③ PRE-ERA 結束是必要條件，不是充分條件**

v2 升格為正式 gate blocker 必須同時確認三件事：
- A. 新分類在 post-schema pool 中穩定（不只在現有三個例子上對）
- B. `stuck_absent` 和 skip_type classification 的關係合理（不把 structural skip repo 誤讀成 adoption failure）
- C. `stable_ok` 不會讓 gate 過度樂觀（健康穩態 repo 多 ≠ fleet readiness 高）

**v2 升格條件（完整版）：**

| 條件 | 狀態 |
|---|---|
| PRE-ERA 結束（skip_type 進 log） | ⏳ 待完成 |
| post-schema pool ≥ N 筆 | ⏳ 待完成 |
| stuck_absent / skip_type 關係驗證 | ⏳ 待完成 |
| stable_ok + fleet readiness 不過樂觀 | ⏳ 待完成 |
| mixed_active 拆成雙類 | 🔜 升格前必做 |

**當前位置聲明：**
- `lifecycle_class` v2 現在的最大價值是「更不會誤傷健康 repo」
- 它尚未足夠敏感地偵測「真正應該擋的 repo」（後者需要 post-schema 資料驗證）
- **「語意變對」和「gate 已可用」是兩件事，不能混**

---

### Post-schema Semantic Probe Set（2026-04-14，**已執行 2026-04-15**）

**目的聲明（語意要準確）：**

這三個 session 的目的不是證明 v2 已穩定，  
而是確認 v2 的三個核心語意槽位在 post-schema reality 中可被正確承載，  
並判斷是否值得進一步擴大樣本。

不叫「驗證 sessions」，叫 **post-schema semantic probe set**：  
補的不是資料量，是探測三個語意槽位有沒有被真實 evidence 正確承載。

**三探針目標（精確版）：**

| 順序 | Repo | skip_type | 真正驗證目標 |
|---|---|---|---|
| 1 | Bookstore-Scraper | 無 | 驗證 post-schema 下 `stable_ok` + `lifecycle_capable` 語意仍正確，新 schema 不破壞唯一已知健康樣本 |
| 2 | Kernel-Driver-Contract | structural | 驗證 structural skip repo 被正確排除於 lifecycle 母體之外，不被 `stuck_absent` 誤讀 |
| 3 | Enumd / SpecAuthority | temporary | 驗證 temporary classification 與 aging wiring **開始生效**（不是驗 aging 本身，aging 需要時間維度） |

**Pass/fail 驗收條件 + 執行結果（2026-04-15）：**

前置修正：執行前發現 ERA detect bug — `skip_type_entry_count` 用 `is not None` 而非 key presence，  
導致 lifecycle-capable repo 的 post-schema entries（`"skip_type": null`）永遠不計入 ERA coverage。  
已修 `scripts/analyze_e1b_distribution.py` + 4 個覆蓋測試（`test_e1b_distribution_v2.py` 33/33）。

Bookstore-Scraper：
- [x] `migration_state.classifications_interpretable` 開始改善（ERA coverage 從 0 → 0.011，已起步）
- [x] repo 仍被歸為 `lifecycle_capable`
- [x] `lifecycle_class == stable_ok`
- [x] 不觸發 `stuck_absent`

Kernel-Driver-Contract：
- [x] repo 被歸為 structural skip（`structural_skip: 1 ['Kernel-Driver-Contract']`）
- [x] 不進入 `lifecycle_capable` baseline 母體
- [x] 不觸發 `stuck_absent`
- [x] 不出現 structural inconsistency advisory

Enumd / SpecAuthority：
- [x] SpecAuthority 被歸為 temporary skip（`temporary_skip: 1 ['SpecAuthority']`）
- [x] temporary aging 欄位出現（`age=1d`）
- [x] `age_days` 有基準值（不為 null）
- [x] activity 欄不為空（`activity=[dead]`，正確反映無 lifecycle 活動）

**所有 6 個 pass/fail 條件全部通過。**

**探針後的真實限制（釘住不可偷渡）：**

1. **ERA 是 adoption distribution 問題，不是時間問題。**  
   coverage = 0.011（3/276）。這 3 筆是手動 probe，不是自然流量。  
   核心問題不是「需要更多 session」，而是：  
   > **「有多少 repo 會在自然工作流程中產生 post-schema entries？」**  
   
   ERA coverage ≈ (自然產生 post-schema entry 的 repo 數) / (全艦隊活躍 repo 數)  
   
   如果多數 repo 的 session_end_hook 沒被正常觸發，或 lifecycle 根本沒走，  
   再多 session 也不會讓 coverage 推進。  
   
   **下一步：有條件的觀察，不是單純等待。**

   在下一批自然 session（非手動 probe）後，執行一次 `analyze_e1b_distribution.py --auto-discover --emit-json`，
   記錄以下三個觀察目標的狀態：

   | 觀察目標 | 記錄項目 |
   |---|---|
   | 是否有新的 `skip_type` entry 出現 | 新增 entry 數 |
   | 這些 entry 來自幾個不同 repo | 不同 repo 數 |
   | 來源 repo 屬於哪一類 | structural / temporary / lifecycle-capable 各幾筆 |

   **最小判定（三岔：不得模糊）：**

   - **若 skip_type 完全沒有新增**：Blocker B 不是「等待更多時間」，而是
     natural path 沒有接上。需升級為 adoption/wiring 問題診斷。
   - **若只有手動 probe 過的 repo 出現**：系統 wiring 可用，但自然工作流沒有觸發
     session_end_hook → 診斷觸發路徑（Tier B wrapper / VS Code task）。
   - **若多個 repo 自然出現 skip_type**：Blocker B 鬆動，可繼續積累。

   **這個 checkpoint 結果會決定後續路徑，不得用「時間還不夠」替代判斷。**


2. **Fleet reality（2026-04-15 清除兩個 bug 後的確認）：**

   清除 YAML parse fallback 與 banner 顯示 bug 後，fleet 中僅剩 **2 個 repo 被歸為 lifecycle-capable**；  
   但**實際成熟母體只有 1 個**：

   - **Bookstore-Scraper**：唯一有意義的 `stable_ok`，是現階段唯一可信 baseline
   - **ai-governance-framework**：技術上屬 lifecycle-capable，但目前單筆 `mixed_active`，  
     不算成熟母體。不得拿它「湊數」成「已有 2 個」，  
     更誠實的表述是：**1 個成熟 + 1 個尚未形成穩定證據的候選**

   Phase 2 無法通過 `distinct repos ≥ 3`，反映的是 fleet 母體不足，而不是分析器過嚴。

   **真實 fleet 組成（釘住，不得混淆）：**

   | 分類 | Repo | 說明 |
   |---|---|---|
   | structural_skip | gl_electron_tool, hp-oci-avalonia, Kernel-Driver-Contract, lenovo_isp_tool, Standard_ISP_Tool | 明確不進 baseline |
   | temporary_skip | cli, Enumd, SpecAuthority | adoption/wiring debt；**Phase 2 擴母體唯一候選** |
   | lifecycle_capable（成熟） | Bookstore-Scraper | 唯一有意義的 `stable_ok` baseline |
   | lifecycle_capable（候選） | ai-governance-framework | 單筆 `mixed_active`，尚未形成穩定證據 |

   **Phase 2 真正的 blocker 重整：**
   - **Blocker A（fleet 母體不足）**：lifecycle-capable 實際只有 1 個成熟 repo，
     `distinct repos ≥ 3` 不是門檻太嚴，而是 fleet 現實就是這麼瘦。
     解法不是修分析器，而是讓 temporary 三選一（cli/Enumd/SpecAuthority）中至少一個升級為真正 lifecycle-capable。
   - **Blocker B（post-schema evidence 未自然產生）**：ERA coverage=0.055（16/289），仍在 PRE-SKIP-TYPE-ERA。
     即使 Blocker A 解了，若 lifecycle-capable repo 的 hook 沒自然觸發，ERA 仍不進。

   兩個 blocker 有交集（lifecycle 沒走 → hook 沒跑 → 兩者都卡），但診斷路徑不同。  
   **臨時 repo 接通才是最近的解鎖路徑。SpecAuthority → 完成兩層 wiring 證明 → 移除 skip → 第三個 lifecycle-capable。**

3. **temporary 三選一升級評估（2026-04-15 調查）：**

   | Repo | 測試現況 | 接通難度 | 評估 |
   |---|---|---|---|
   | cli | 0 py test files，C++ GTest，需 CI Docker（本地無 cmake）| 高（CI-only path）| **最難：本地無法接通，需 CI infra 工作** |
   | Enumd | 0 py test files，純 JS/Node.js（lib/、no tests/）| 高（非 Python，需新建 pytest layer）| **難：無現成 Python test 可接，需從零建測試** |
   | SpecAuthority | `spec_truth/` 有 27 個 py 檔，其中含 `test_*.py`（498 tests 已驗證通過）| **低（tests 已存在，只需接 ingestor + 移除 skip）** | **首選：路徑最短** |

   **結論：SpecAuthority 是最有機會第一個脫離 temporary debt 的 repo。**

   **Phase 2 當前行動定義（釘住）：**

   > Phase 2 的進展不再以 session 數量衡量，而以 lifecycle-capable 母體是否擴張衡量。
   > SpecAuthority 是最短路徑候選，但只有在 wiring 閉環穩定、並留下多筆 post-wiring evidence 後，
   > 才可視為第三個有效母體。

   **兩層結構（不得合併成一步）：**

   **Layer 1：證明 lifecycle wiring 活了（先做）**

   在移除任何 skip 宣告之前，必須先確認：

   - Checkpoint 1：`pytest spec_truth/ --tb=short` 輸出可被現有 ingestor 正常解析
   - Checkpoint 2：`test_result_ingestor --out artifacts/runtime/test-results/latest.json` 確實生成 artifact（不是空檔或 malformed）
   - Checkpoint 3：`session_end_hook` 讀到 artifact，回報 `artifact_state=ok`，而非 absent/malformed

   Layer 1 完成代表：wiring 活了，lifecycle gate 有辦法走完。
   **Layer 1 未穩定之前，不得更動 gate_policy.yaml。**

   **Layer 1「穩定」最小判定標準（文件層定義，不要求全部，但必須說清楚）：**
   - 連續成功次數：至少 2 次獨立執行均通過（不能只有 1 次 probe 就宣告）
   - session 獨立性：橫跨至少 2 個不同 session（同一天連續執行不算獨立）
   - 自然性比例：至少 1 次來自非手動 probe 的自然工作流（純手動 probe 不構成 Layer 1 穩定）
   - 判定是否穩定不得以「應該沒問題」替代，需要明文記錄哪幾次通過、各自的 session_id 或日期

   **⚠️ 觸發路徑現實（2026-04-16 確認，不得低估）：**

   session_end_hook 在 GitHub Copilot 環境（Tier B）下**沒有自動觸發路徑**：
   - `~/.claude/settings.json` 的 `"hooks": { "Stop": [...] }` 是 Claude-native hook；Copilot 不支援此機制
   - 目前 permission 清單中的 session_end_hook 是 allow-listed bash 命令，不是觸發器
   - Copilot session 結束時，不會自動執行任何 governance hook

   因此，「自然工作流」在 Tier B 的正確定義是：

   > **在真實 SpecAuthority 開發工作結束後，作為收尾程序手動執行 session_end_hook**（不是因為要測試 hook，而是因為工作結束了）。

   這與「手動 probe」的區別是**動機與脈絡**，不是機制：
   - 手動 probe = 為了驗證 hook 而跑 hook
   - Tier B 自然工作流 = 為了結束真實工作 session 而跑 hook

   若要建立更接近 Tier A 的自動觸發，可選項為：
   - VS Code task（在 `.vscode/tasks.json` 加入 session end task，手動觸發但有固定入口）
   - 但此為 Layer 2 後的優化；Layer 1 的自然性條件以 Tier B 定義即可

   **Layer 1 執行紀錄（不得刪除，累積 evidence）：**

   | 次數 | 日期 | session_id | source | artifact_state | artifact_present | 備註 |
   |---|---|---|---|---|---|---|
   | #1 | 2026-04-15 | session-20260415T070356-a10167 | pytest-text | ok | True | 首次成功；手動 probe；ok=false 來自 failure_test_validation 命名模式（非 pipeline 斷裂）|
   | #2 | 2026-04-16 | session-20260416T015634-fafa87 | pytest-text | ok | True | 手動 probe；跨 session 確認 pipeline 可行；ok=false 同 #1（命名模式，非斷裂）；自然性條件未驗證 |
   | #3 | 2026-04-16 | — | pytest-text | ok | True | **Tier B 自然工作流**；Phase G 真實開發 session 收尾；gate_verdict=OK；closeout_status=valid；memory_tier=verified_state_update；641 tests 0 failures；commits 8621554 + ef0e40e |

   **Layer 1 穩定狀態**：✅ STABLE（3 次跨 session 成功；#3 為 Tier B 自然工作流，非 probe；自然性條件達標）

   **Layer 2：證明可以移除 temporary skip（Layer 1 穩定後才做）**

   - Checkpoint 4：多次自然 session 後累積不只 1 筆 post-wiring evidence，且 `lifecycle_class` 不再是 `stuck_absent`

   > **只有單次成功不算 Layer 2 達成。**
   > 單次可能是手動特例、probe、或非自然工作流。
   > 此 repo 已有「單筆樣本被高估」的紀錄，不得再犯。

   **✅ Layer 2 時間尺度宣告（已落地到分析器，2026-04-16）：**

   > 新完成 wiring 的 repo，其 Layer 2 穩定性以**近期 rolling window** 判定，不以全歷史分布作為主要成功條件。
   > 全歷史僅保留作為 adoption history 與遷移脈絡，不作為 stable_ok 的主要判準。
   > 理由：用全歷史懲罰已穩定修復的 repo，在治理語意上不合理；早期 absent 反映 wiring 前狀態，不反映當前 lifecycle 成熟度。
   >
   > **程式落地**：`scripts/analyze_e1b_distribution.py` 加入 `recent_lifecycle_class`（last `_LC_RECENT_WINDOW=20` entries）作為 Layer 2 主判欄位；`lifecycle_class`（全歷史）降格為 audit context。5 個新測試驗證時間尺度獨立性。

   **✅ Layer 2 完成（2026-04-16）— SpecAuthority 正式進入 lifecycle-capable pool**

   rolling window 20/20 ok 達成路徑：Sprint K–Q（7 個 vendor command evaluator），共 +272 tests（802 → 1074）。
   全為自然工作流 session，non-probe。最後一筆：Phase Q `aec4802`。

   | 時間尺度 | 指標 | Phase Q 後（最終） | 說明 |
   |---|---|---|---|
   | 全歷史 | artifact_state=absent | 25 | pre-wiring 舊 session，audit context only |
   | 全歷史 | artifact_state=ok | 20 | Sprint K–Q 自然累積 |
   | 全歷史 | lifecycle_class | **mixed_active** | 全歷史 absent 55.6%；此欄僅 audit context |
   | rolling window（後 20 筆） | ok 數 | **20/20** | window 全部 ok |
   | rolling window（後 20 筆） | recent_lifecycle_class | **stable_ok ✅** | Layer 2 判準達標 |

   **Layer 2 Checklist（Phase Q 後）：**

   | # | 條件 | 狀態 |
   |---|---|---|
   | ① | ok > 0 in window | ✅ PASS |
   | ② | 不是全 absent | ✅ PASS |
   | ③ | ok ratio ≥ 0.90（recent_lifecycle_class = stable_ok） | ✅ PASS（20/20 = 100%） |
   | ④ | 無連續 ≥ 2 absent（window 內） | ✅ PASS（window 全 ok，無 absent） |
   | ⑤ | 自然 session 存在 | ✅ PASS（Sprint K–Q 全為自然工作流） |

   **Layer 2 完成後已允許（待執行）：** `gate_policy.yaml` 移除 `skip_test_result_check: true` 與 `skip_type: temporary`。
   SpecAuthority 現為 lifecycle-capable pool **第三個有效 repo**。

   **✅ gate_policy.yaml 清理已確認（2026-04-16）：**
   SpecAuthority `gate_policy.yaml` 已無 `skip_test_result_check` 與 `skip_type` 欄位。

   **⚠️ lifecycle_capable 語意 bug 修正（2026-04-16，`analyze_e1b_distribution.py`）：**
   舊邏輯 `has_any_skip`（全歷史 any）會讓 SpecAuthority 因歷史 `skip_type: temporary` entries 永遠被排除在 lifecycle_capable 之外，即使 gate_policy.yaml 已清理。
   已修正為：使用最近一筆 schema-aware entry（`policy_provenance` 中 `skip_type` key 存在的 entry）的 skip_type 值。
   若最近 schema-aware entry 的 skip_type=null → lifecycle_capable=True；pre-schema repo 仍 fallback 到舊邏輯。

   **修正後 fleet 狀態（2026-04-16）：**
   - lifecycle_capable repos：3（Bookstore-Scraper, SpecAuthority, ai-governance-framework）
   - Phase 2 gate `min_repos ≥ 3`：✅ PASS
   - Phase 2 gate `min_nondegenerate_ratio ≥ 0.7`：❌ FAIL（legacy entropy metric；all 3 repos are stable_ok by v2，但 entropy 低於 0.3 觸發 legacy false-positive）
   - Phase 2 gate `lifecycle_active_ratio ≥ 0.5`：✅ PASS（1.0，shadow v2 metric）
   - 剩餘 blocker 是 legacy v2-upgrade 問題，不是母體不足

   **Phase 2 精確現況（2026-04-16，釘住不得混淆）：**

   > **Phase 2 blocked by metric promotion decision, not by repository readiness.**

   fleet pool 已足夠（3 lifecycle_capable repos，99 sessions），但 `min_nondegenerate_ratio` 仍讀 legacy `is_degenerate`（distinct_states/n < 0.3），對所有 stable_ok repo 均回傳 false positive。v2 等效指標（`lifecycle_active_ratio=1.0`）已健康，但尚未升格成正式 gate check。

   不做 v2 gate promote 的理由（已釘住，不得繞過）：

   | 原因 | 說明 |
   |---|---|
   | gate semantics 升格，不是 bugfix | promote 改變的是 Phase 2 通過條件、fleet readiness 判準、reviewer 對 degenerate 的理解方式，是政策升格 |
   | mixed_active 拆分未完成 | 升格前必做的語意清理仍 pending |
   | 三 repo pool 樣本偏小 | 三個 stable_ok repo 是目前觀測；不排除是剛好乾淨的 pool，非充分證據 |
   | PRE-ERA coverage 仍低 | 資料分布仍帶時代切換痕跡，此時升 gate 容易把「目前觀測上合理」誤當「正式可依賴」 |

   promote 的正式前提（全部滿足才做）：
   1. `mixed_active` 拆成 `insufficient_evidence` / `transitioning_active`（語意清理）
   2. 三 repo 觀測時間差夠長，非集中於同一時段
   3. 明確 promote decision，說明不會在 stable_ok-heavy fleet 引入樂觀偏誤
   4. PLAN.md 有對應的政策切換記錄條目（不得只改 code）

   **待清理項（Layer 2 完成後仍需處理）：**
   session_end_hook 輸出的 `e1b_observation.is_degenerate=True` 是 legacy entropy 公式（entropy < 0.3）殘留。
   v2 公式（`is_degenerate_v2 = lifecycle_class == "stuck_absent"`）回傳 False。
   **這是輸出層語意污染，需清理或加 deprecation 標記。**



**探針判斷：v2 語意槽位可運作，可擴大樣本。**

**期待值邊界（不可超越）：**

跑完這三個後，最多只能確認：

> v2 在三種基本語意槽位上可運作，且沒有出現一階錯誤分類。

「穩定」需要：多 repo、多 session、至少一點時間差、沒有因 schema 遷移出現跳動。  
這三個 probe sessions 不足以宣告穩定。  
跑完判斷的是：**是否值得擴大樣本**，不是「v2 已穩定」。

**驗證指令：**
```powershell
cd e:\BackUp\Git_EE\ai-governance-framework
python scripts/analyze_e1b_distribution.py --auto-discover
```

---

### Harness Engineering 外部文章評估（2026-04-15，已評估）

**文章核心主張（三點）：**
1. Hallucination 根源是「沒有被強迫看現實」，不是模型能力問題
2. Harness = 認知框架 + 能力邊界 + 工作流程（Planner → Generator → Evaluator）
3. Feedback loop quality 決定學習方向

**對這個 repo 的對應關係：**

| 文章概念 | 此 repo 對應 | 狀態 |
|---|---|---|
| Harness 工作流程 | session_start → pre_task_check → post_task_check → session_end | ✅ 超越 |
| Evaluator | post_task_check | ✅ 已有 |
| 記憶整理 | session_end + canonical closeout | ✅ 已有 |
| agents.md（自然語言規則） | AGENTS.md + decision_boundary_layer（機器可解讀） | ✅ 已超越 |
| Ralph Loop（generate → feedback → regenerate） | 跨 session long-loop + memory injection | ✅ 已超越 |

**有效批評（2 點真正成立）：**

**① Feedback 仍在 process-semantic，缺 outcome-semantic**

現有 feedback 信號：`missing_evidence`、`artifact_state=absent`、`taxonomy_signal` → process level  
缺少的：「你的 closeout 結論與觀測到的信號不一致」→ outcome/semantic level

這是真實缺口。現有 feedback 是「結構正確性」，不是「決策一致性」。  
未來可補：post_task_check 增加 closeout-vs-signal 一致性對比（rule-based，不需 LLM）。

**② pre_task_check 是結構驗證，缺 goal interpretation check**

現有 pre_task_check：rule filtering、scope classification、task topic routing → 驗 WHAT is asked  
缺少的：確認 AI 理解的任務意圖與 task context 是否一致 → 驗 WHY is asked + plan makes sense

這是真實缺口，但難以用 deterministic rule 覆蓋。需要一層「plan propose → validate → approve」  
的輕量結構，代價相對高，放 backlog。

**無效批評（3 點，對此 repo 不適用）：**

- **「你過度相信結構，低估認知引導」**：decision_boundary_layer + advisory taxonomy 已是語意層，  
  不只是 schema 層。文章低估了現有架構的深度。

- **「Evaluator 來得太晚」**：pre_task_check 已做 task classification + rule scope 篩選，  
  文章描述的 "Evaluator front-movement" 在結構上已存在，只缺 semantic 層。  
  這是精確的（結構完整，語意待補），不是「完全沒有前驗」。

- **「情緒污染 / prompt tone」**：warning/error 是給 operator 看的 machine-readable 信號，  
  不是 LLM 的 instruction stream。這個點對 stateless execution 框架不適用。

**結論（釘住優先序）：**

| 項目 | 評估 | 行動 |
|---|---|---|
| Outcome-semantic feedback | ✅ 真實缺口，low-medium cost | 列 backlog，ERA 穩定後考慮 |
| Goal interpretation pre-check | ✅ 真實缺口，medium-high cost | 列 backlog |
| Cognitive Harness 整體重構 | ❌ 架構已覆蓋，過度工程 | 不做 |
| Prompt tone audit | ❌ 對此框架不適用 | 不做 |

**不得偷渡：** 「文章說要補 cognitive control」不是本 phase 任務的依據。  
這個評估只是確認現有架構在語意邊界上的 gap 定位，不是 Phase 3 前的必做項。



---

### P2

- [ ] 評估 BUG-003 後續是否需要從 byte-size 再擴到更高階的多維記憶壓力信號
- [ ] 評估 starter-pack 升級路徑是否要補 lock/manifest，而不是只有 refresh
- [ ] **gate_policy parse failure（observability integrity risk，不是一般 backlog）**：  
  這不是單純解析錯一個 repo 的問題，而是：  
  「設定錯 → 靜默回退 → 偽正常觀測」三步被包成同一個外觀。  
  `skip_type=None`、`fallback_used=True` 雖然存在，但對觀測者而言外觀與「正常 repo」無法區分，  
  直接破壞 fleet reality 的信任度。cli 個案是靠「分類異常」才倒推發現；  
  下次不能靠偶然觀察。**每一個被靜默吸收的 parse error 都是一次未被記錄的 fleet 污染。**  
  **最低可接受結果（三選一，不要求全做，但必須有一層可見）：**  
  - `policy_provenance` 加 `policy_source=fallback_due_to_parse_error` + parse error message（provenance 層）
  - session_end_hook output 加 `[ADVISORY] gate_policy: YAML parse failed, using builtin_defaults`（operator 層）
  - E8a log 標記 `parse_error: true`（observability substrate 層）

  **⚠️ 這三選一是最低保底，不是終態。**  
  parse failure 的本質是 fleet observability integrity issue，不是操作提醒。  
  advisory / provenance / log 只解決「不再靜默」的問題，但這類錯誤如果只停留在 advisory，  
  仍然容易被忽略。長期走向是更強的可見性（阻斷或強制 operator ack），目前先以三選一保底，  
  但這條不能被視為「解決了」，只能視為「最小保底」。

---

### SOUL Observability — 分析紀錄（2026-04-14，已評估，暫不實作）

**背景問題**：`SOUL.md` 目前是靜態 persona 宣言，完全在 governance runtime 之外。
按照 repo 自身的 evidence 標準：無可觀測性、無可驗證性、無 artifact、無 hooks。

**可以做的部分（observable facts，符合既有 evidence 標準）**：

```python
soul_check = {
    "soul_file_present": (project_root / "SOUL.md").exists(),
    "soul_hash": _sha1(soul_path) if soul_path.exists() else None,
    "soul_drift": prev_soul_hash != current_soul_hash,
}
```

接法與 `governance_drift_checker.py` 對齊，hash 比對存入 `.governance-state.yaml`，
在 `session_start.py` 加 advisory signal。這是可測試、可 replay、無語意歧義的。

**不適合做的部分（behavioral inference）**：

```python
# 這些無法用 repo 標準驗：
"no_opinion_detected": True       # 需要 LLM audit LLM → circular
"filler_language_detected": False  # 非 deterministic，無法 replay
"assumption_not_challenged": True  # 無 actionable downstream decision
```

驗證標準（用 repo 自身框架）：
> 若 signal 出現，reviewer 的決策是什麼？能寫進 `replay_verification.py` 嗎？能設 `expected_match` 嗎？

以上三個皆否 → 是 governance theater，不是 governance。

**結論（已釘住）**：

| 做法 | 評估 |
|---|---|
| SOUL.md 的 hash drift 追蹤 | ✅ 符合標準，低成本，可接 session_start |
| behavioral audit（opinion/filler/stance） | ❌ 語意上不 fit；需要獨立 LLM eval pipeline，那是另一個 project |
| 完整 soul_profile artifact（assertiveness: 0.6 等） | ❌ 無 deterministic anchor，無法 replay |

**當前優先序**：E1b fleet 資料問題更迫切。SOUL hash drift 追蹤列入 backlog，等 E1b Phase 2 穩定後再考慮。

---

### Compression Provenance Layer（2026-04-15，Phase 1 完成）

**Phase 1 完成：Plan Context Provenance（`b3b1bbc`）**

`plan_summary.py` / `session_start.py` / `session_end_hook.py` 三條鏈路已可記錄：

- `plan_context_fidelity`：`full` | `summarized`
- `plan_context_origin`：`PLAN.md` | `plan_summary.py`
- `plan_context_summary_kind`：`deterministic_extract` | `null`

這使得 canonical audit log 的每筆 entry 可攜帶 `plan_context_provenance`，讓 replay / 比較 / 審查知道該次 session 是在什麼 context fidelity 下做決策的。

**Phase 1 的精確定位（不得超越）：**

> Phase 1 不證明 full 與 summarized 等價；它只把兩者差異變成可觀測、可審計的事實。
>
> 已能觀測：decision 發生時的 context fidelity 類型（full / summarized）
> 尚未觀測：rule-level retention 差異、summarized 版本的裁切是否影響某次 decision

**三個釘住的語意邊界（不得自欺）：**

1. **`no_sidecar` → `assumed_full_for_backward_compatibility`，非 `proven_full`**
   無 sidecar 有三種可能：真的 full、full 但 sidecar 寫失敗、fidelity 根本未知。
   現在把三種壓成 `assumed_full` 是相容舊資料的務實選擇，不是語意上的乾淨聲明。

2. **`summary_kind=deterministic_extract` 只回答「怎麼產生的」，不回答「裁掉了什麼」**
   有了 provenance ≠ fidelity impact 已可比較。
   知道是 deterministic_extract ≠ 知道哪些 rule 被保留 / 裁掉 / 裁掉是否影響 decision。

3. **human marker 是 reviewer convenience，不是主要真相來源**
   真正可信的 source：structured JSON key + audit log entry + sidecar。
   不應讓後續工具依賴 human text marker 判讀 fidelity。

**Phase 2 / Phase 3 邊界（deferred，釘住位置）：**

| Phase | 目標 | 前提 |
|---|---|---|
| Phase 2 | `rule_fidelity`：記錄 topic filtering / stripping 保留了哪些 rule pack | ERA 穩定、E1b Phase 2 有足夠樣本後評估 |
| Phase 3 | `cli_output_fidelity`：interactive dev session 的 CLI 壓縮觀測 | governance pipeline 內已由 ingestor 解決，Phase 3 只對 interactive 路徑有意義 |

---

### External Integration Seam — Enumd + Hermes（2026-04-16，已完成）

**背景**：Enumd（`E:\BackUp\Git_EE\Enumd`）是一個 domain-calibrated synthesis pipeline，
以 ai-governance-framework 作為 submodule。先前無任何橋接機制；governance report 只停在 Enumd 本地。

**已完成的三層工作（commits `af8e45b` + `b17eeac`）：**

#### Enumd External Observation Seam（Mode A）

`integrations/enumd/` 建立四個檔：

| 檔案 | 職責 |
|---|---|
| `schema.sample.json` | canonical sample（含 routing directive 注解和 calibration threshold 警告）|
| `ingestor.py` | 驗證 provenance → assert `represents_agent_behavior=false` → 輸出 `artifacts/external-observations/enumd-{run_id}.json` |
| `mapping.md` | 欄位對應表 + 7 條非等值硬限制 + 被明確排除的 Enumd internals 清單 |
| `usage.md` | CLI 用法、output schema、不等值警告（3-question format）|

**Enumd internals 明確排除於 integration surface 之外（不得偷渡）：**
- `CROSS_DOMAIN_SLUG_PATTERNS`（corpus-specific slug 清單）
- `LOW_OVERLAP_THRESHOLD = 0.40`（Enumd Wave 1 corpus 校準值，不是 framework 門檻）
- `HANDOFF` threshold `0.30`、any-node threshold `0.50`（同上）
- `STRUCTURAL_ALLOWLIST`（含中文 marker 的 synthesis artifact）
- `SANITIZATION_PATTERNS`（20 個 regex，Enumd claim ingestion 用）
- `KalResult`（CONVERGED / THIN_SYNTHESIS / SKIPPED）、`THIN_CONTEXT_MARKERS`

**非等值硬限制（不得做以下對應）：**

| Enumd 概念 | 禁止對應到 | 原因 |
|---|---|---|
| KEEP | framework `ignore` | 不同 evidence model |
| DOWNGRADE | `test_fix` | 不同決策語意 |
| REMOVE | `production_fix` / `escalate` | 不同 action scope |
| `LOW_OVERLAP_THRESHOLD=0.40` | 任何 framework 門檻 | corpus-calibrated，不 generalizable |
| `domain_misalignment_risk` advisory | framework risk signal | synthesis-local，不影響 session_start overrides |

#### P1 — 測試守門（`tests/test_enumd_ingestor.py`）

6 個 tests，全 pass，鎖住以下邊界：

| Test | 守住的邊界 |
|---|---|
| `test_valid_sample_pass` | schema.sample.json 被接受；routing directive 在 envelope 保存；policy_applied 原封不動在 payload |
| `test_missing_semantic_boundary_fail` | 沒有 semantic_boundary → reject（routing guard 不可省）|
| `test_represents_agent_behavior_true_fail` | `represents_agent_behavior=True` → reject，error 可審計 |
| `test_missing_provenance_field_fail` | 沒有 calibration_profile → reject（provenance root 不可缺）|
| `test_validate_report_clean_sample` | `validate_report()` 對 sample 返回 empty list |
| `test_validate_report_wrong_producer` | 非 enumd producer → 被 flag |

#### P2 — Analysis Boundary（`scripts/analyze_e1b_distribution.py`）

新增 `is_runtime_eligible()` 為**模組級 public 函式**：

```python
def is_runtime_eligible(obs: dict) -> bool:
    """True only for observations representing agent runtime behaviour."""
    return obs.get("semantic_boundary", {}).get("represents_agent_behavior", True)
```

`_load_entries()` 在 entry 進 `compute_repo_stats` 之前先 filter：
- `represents_agent_behavior=False` 的 entry 被排除於 lifecycle_class、E1b、Phase 2 gate 之外
- 預設 `True`：舊 entry（無 semantic_boundary 欄位）向後相容，不受影響
- 被 filter 的數量 emit 到 stderr 作 diagnostic，不影響 exit code

**為何不做 Option B（把 filter 移到 governance_tools/ 作 shared utility）**：
目前 `canonical-audit-log.jsonl` 是 framework runtime sessions 的專屬路徑；
Enumd ingestor 寫至 `external-observations/`，不寫 canonical-audit-log。
真實危險路徑是手動操作問題，不是程式問題。
One-callsite abstraction 現在提取是 premature；等出現第二個消費點再做。

**測試結果（P1 + P2 合併）：1811 passed，0 failed**（+6 新測試，無 regression）

#### Mode B — Hermes Instance（docs-only，實作未著手）

`docs/governed-agents/hermes.md` 定義：
- Hermes 是公開 OSS（NousResearch，91k stars），NOT a local repo
- 框架只能提供「要求」（contract.yaml + AGENTS.base.md），無法驗證內部執行
- 最小 attestation schema（`session_closeout.json`）透過 `on_session_end()` 發出
- 驗證不對稱性是**永久特性**，不是暫時缺口

**明確記錄：Mode B 實作未著手。**  
前提條件：需要真實 Hermes instance + 真實 session_closeout.json 樣本 + 明確 operator flow。  
在此之前，`hermes.md` 是設計文件，不是已上線的 integration。

**Enumd seam drift detector（`cfd46b8`）：**

`scripts/check_enumd_integration_state.py` — 12 assertions，exit 0/1，支援 `--json`：
- 4 seam file existence checks
- 2 critical content checks in ingestor.py（routing directive + provenance root）
- 1 analysis boundary check（`is_runtime_eligible` in analyze_e1b_distribution.py）
- 4 critical test function name checks（T1-T4 semantic guards）

**pytest wrapper（`tests/test_enumd_integration_state.py`，13 tests）：**

把 seam state check 納入 pytest filtered suite，每次測試自動驗證 seam 結構完整性：
- `test_enumd_integration_state_all_pass`（aggregate，12 checks）
- 4 × seam file existence（parametrized）
- P1 test file existence
- ingestor routing directive check
- ingestor provenance root check
- P2 analysis boundary check
- 4 × semantic guard presence（parametrized）

**測試結果（路線 2 + 路線 3 合併）：1824 passed，0 failed**（+19 新測試，無 regression）

Mode B（Hermes）明確記錄為 docs-only，實作未著手。

---

**Enumd integration 架構批評回應（2026-04-16，釘住不得回溯）：**

> **Track A closes with no article-driven code changes required. Track B remains an internal taxonomy-upgrade task, not a remediation for any external critique.**

背景：一份外部架構評論提出四點批評：① Enumd ≠ 事實（只是 observation model）、② Governance = 盲裁判（evidence completeness 不足）、③ 閉環缺 rollback/decay、④ Hermes ≠ 執行器（系統演化來源）。

對照現有 code 的有效結論：

| 批評 | 當前狀態 | 依據 |
|---|---|---|
| Enumd ≠ 事實 | **已處理**（conservative design） | `observation_class="external_analysis_artifact"`；`represents_agent_behavior=false`；`is_runtime_eligible()=False`；mapping 明文禁止 threshold / advisory / verdict 轉義 |
| Governance = 盲裁判 | **不是當前 code 缺陷，但屬潛在 consumer semantics 風險** | distribution gate 防止單點信任；`calibration_profile` 保存 evidence scope；但不自動保證 downstream consumer 不過度解讀——目前無發生證據，不值得新增 code |
| 缺 rollback/decay | **當前豁免，非永久已解** | memory promotion / execution loop coupling 尚未引入 scope，故尚未暴露；這是未來架構前提，不是當前缺陷 |
| Hermes 複雜性 | **不適用（無此組件）** | 當前豁免源於尚未引入，不是架構天然回答 |

這篇文章對當前 codebase 的有效影響是：**驗證現有保守邊界設計成立**，不是觸發新的實作修補。

**Track B（mixed_active 語意拆分）仍待做，但驅動原因是 v2 promote 前置整理，不是本批評的 remediation。** 兩件事驅動原因不同，不得混讀。

**補充說明：目前邊界是 trust-based，尚未是 constraint-based**

現有防線（`is_runtime_eligible()`、routing directive、mapping 禁用清單）均為 discipline-based：正確使用者遵守即有效，但不能阻止 downstream consumer（含 LLM agent）繞過。真正的 constraint-based 防線需要 enforcement 層（schema validation at consumption point 或 gated read API），目前不存在。

**Observation vs Decision Boundary — 未來觀察項（不是現在的 code task）：**

若日後出現以下任一情況，視為邊界侵蝕，需立即處理，不得當 feature：
- `external_analysis_artifact` 被用作 lifecycle classification 輸入
- `calibration_profile` 或 `advisories` 被當成 gate decision evidence
- Enumd 的 threshold 值出現在任何非 Enumd 的判斷邏輯中
- `semantic_boundary` 被 consumer 自行重新解讀成允許影響 decision 的依據

---

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

## Ecosystem Test Taxonomy（2026-04-14，固定記錄）

跨 repo 測試不能全混進同一個「通過/失敗」框架。以下四種狀態要分開處理：

| 層次 | 定義 | 判讀標準 |
|---|---|---|
| **Framework mainline** | ai-governance-framework 自身測試套件 | 全綠才算 mainline 穩定 |
| **Domain contract** | consuming repo 的 spec_truth / contract tests | 合約層穩定 = 必要條件，不等於 consuming repo app 業務穩定 |
| **Consumer syncedness** | consuming repo 的 governance_tools / runtime_hooks 版本是否與 framework HEAD 對齊 | version drift 失敗需 sync 後重跑才能正式關閉；pattern 判讀不算關閉 |
| **Domain app behavior** | consuming repo 的 app-level tests（業務邏輯、schema 格式、fixture 依賴） | test-schema drift / 外部 fixture 失敗 ≠ framework regression |

**補充：無法執行的 repo**

「不在範圍」≠「沒問題」。以下情況應記為 **unverified under current local conditions**：
- 缺少 prerequisites（如 Kernel-Driver-Contract 缺 `.checks.json`）
- 依賴外部 API / env（如 Enumd 的 `test:graph`）
- 非 Python/pytest 技術棧且無本地 runner（如 Command_Line_Tool .NET sln）

**重要：unverified ≠ neutral（中止推論，不是綠燈）**

unverified repo 不能被拿來支持「沒有 regression」，也不能被拿來支持「有 regression」。  
它應留在真正中止推論的狀態，不得被心理上視為綠燈或紅燈。

**本輪 meiandraybook sync 完成後的 post-sync diff 記錄（2026-04-14）：**

sync 前：22 failed, 1360 passed（pre-sync，governance version drift）

sync 動作（按發現順序）：
1. `governance_tools/` 14 個新檔（gate_policy.py, session_end_hook.py, taxonomy_expansion_log.py 等）
2. `tests/` 21 個新測試檔（test_e1b_distribution_v2.py, test_f4_taxonomy_expansion_log.py 等）
3. `runtime_hooks/core/_canonical_closeout.py` + `_canonical_closeout_context.py`
4. `tests/fixtures/failure_disposition_corpus.json` + `e8a_event_scenarios/`
5. `scripts/analyze_e1b_distribution.py`（E1b 分析工具）
6. `governance/gate_policy.yaml`（消費 repo 需取 framework 版本）
7. `runtime_hooks/core/session_end.py` + `session_start.py` + `post_task_check.py` + `pre_task_check.py` + `payload_audit_logger.py`
8. `governance_tools/test_result_ingestor.py`

sync 後核心模組驗證：**290/290 passed**（test_gate_policy, test_f1~f5, test_e1b_distribution_v2, test_canonical_closeout, test_failure_disposition_pipeline, test_session_end_closeout_integration 等）

**結論（精確版，2026-04-15 收緊）：**

meiandraybook 先前 22 failures 所對應的 **governance drift 假設**，已由 post-sync 核心模組 290/290 通過而關閉。  
關閉範圍：governance version drift 對核心治理模組的影響。  
未關閉範圍：meiandraybook 整體所有 integration risk；未來 sync 後不再漂移的保證。

Bookstore-Scraper 的 regression-like failure（`test_excel_writer_strips_illegal_control_characters`）  
已定位為 test-schema drift（`_HEADERS` col3 已改為「評分」，test 基於舊 col3=書名）。  
`_sanitize_cell_value` 邏輯仍存在且可運作。  
關閉範圍：那 1 個 regression-like case 與 framework 改動無交集。  
未關閉範圍：Bookstore-Scraper 整體仍有一整包 test-schema drift / fixture drift / external dependency 問題，整體仍屬 noisy，不適合做太強的正負向結論。

**可合理宣稱的主結論：**

> 主線與合約層均全綠；meiandraybook 先前的 governance version drift 已由 post-sync 核心模組 290/290 通過而硬性關閉；Bookstore-Scraper 的 regression-like failure 已定位為 test-schema drift，與 framework 改動無交集。基於目前已同步且可驗證的 consuming repo 子集，未觀察到任何 framework 改動引入 regression。Kernel-Driver-Contract、Enumd、Command_Line_Tool 目前仍屬 unverified under current local conditions，尚不納入 regression 正反結論。

**尚未解決 / 不得偷渡的問題：**
- Kernel-Driver-Contract / Enumd / Command_Line_Tool：unverified，中止推論
- Bookstore-Scraper 整體 17 failures：属既有漂移，尚未清理
- **E1b v2 是否能升格為正式 gate：不是 code correctness 問題，仍是 post-schema semantics 問題**  
  「測試都過了」≠「Phase 3 快可以開了」，這條邊界必須守住

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
| 2026-04-15 | Condition 5 廢棄 unique_pattern_ratio，改用 lifecycle_active_ratio | unique_pattern_ratio 是 non-identifiable metric（健康 fleet 也低）；lifecycle_active_ratio 正確區分「有跑 lifecycle」vs「宣告 capable 卻從沒跑」；threshold 0.5；已實施至 analyze_e1b_distribution.py + 4 新測試 |
| 2026-04-15 | Compression Provenance Layer Phase 1 — plan context | fidelity+origin+summary_kind 三條鏈路（plan_summary→session_start→session_end→audit log）；Phase 1 不證明 full 與 summarized 等價，只把差異變成可觀測事實；no_sidecar=assumed_full_for_backward_compatibility 非 proven_full；Phase 2/3 deferred |
| 2026-04-15 | Topic filtering adoption gap 分析 — 釘住邊界 | `pre_task_check` topic filtering 對 consuming repos 的實際覆蓋率極低：session_start 呼叫 pre_task_check 時 task_text="" → classify_task_topic 永遠回 "general" → 無 filtering；AGENTS.base.md 無 pre_task_check 指示；無 CI hook / pre-commit hook；唯一有效情境：AI 主動傳 `--task-text` 或 domain rule pack 觸發 _PACK_TOPIC_HINTS；KDC 的 `kernel-driver` pack 是目前唯一自動 topic 的 repo；此為 coverage gap，非 regression；不修復，只記錄邊界 |
