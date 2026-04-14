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
    - unique_pattern_ratio ≥ 0.4（`--min-unique-pattern`） ← 新增
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
