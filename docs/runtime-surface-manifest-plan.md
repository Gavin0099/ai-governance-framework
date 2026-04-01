# Runtime Surface Manifest 計畫

> 狀態：draft
> 日期：2026-04-01
> 目的：參考 `instructkr/claw-code` 這類 inventory-first 的 runtime 觀察方式，
> 為本 repo 定義一個最小的 execution surface manifest 計畫，但不把目前的
> governance runtime 降格成一般 agent harness 專案。

---

## 為什麼要做這個

這個 framework 目前已經有很強的治理面：

- runtime hooks
- evidence normalization
- verdict / trace artifacts
- reviewer handoff
- authority 與 policy 文件

但目前比較不夠顯式的是 **execution surface 本身**：

- 有哪些 adapter
- 有哪些 runtime entrypoint
- 哪些工具是 adoption / smoke / audit 的正式入口
- 哪些輸出面是 reviewer 可消費的 evidence surface
- 哪些地方是 authority 的宣告來源，哪些只是觀測來源

這份計畫要補的是一層很小的 **runtime surface manifest**：

- 位於 governance semantics 之下
- 位於原始程式碼探索之上

它的目的是提升 observability、replayability 與外部 orientation，
不是取代目前的 governance runtime。

---

## 設計目標

產出一個小型、可查詢的 execution-surface 視圖，讓 reviewer 或 agent
可以快速回答：

1. 現在有哪些 runtime entrypoint？
2. 支援哪些 adapter family？
3. adoption、drift、smoke、audit 的正式工具入口是哪些？
4. 哪些輸出面是 first-class evidence surface？
5. 哪些 authority boundary 已經被宣告，它們的來源在哪裡？

這一層必須是 **inventory-first**，不是 verdict-first。

但它不應該永遠停在完全被動的 inventory。

first slice 雖然不直接改變 verdict，仍應保留一個最小的
**manifest consistency signal** 能力，避免 manifest 與 runtime reality
分裂卻沒有任何觀測面。

---

## 非目標

這份計畫 **不是** 用來：

- 取代 `governance/governance_decision_model.v2.6.json`
- 重定義 authority semantics
- 擴張 DBL 超過目前 first slice
- 引入第二套 rule engine
- 推論 repo 尚未正式宣告的 runtime capability
- 生成新的 maturity score 或 risk score

這是一份 **surface manifest**，不是新的 governance model。

它的第一版不是 hard gate，也不是 rule engine；但它不應該是完全不會
發出訊號的純文件層。

---

## 建議的 First Slice 交付物

### 1. Adapter Inventory

候選來源：

- `runtime_hooks/adapters/`
- `runtime_hooks/ADAPTER_CONTRACT.md`
- `runtime_hooks/event_contract.md`

最小欄位：

- `adapter_family`
- `supported_events`
- `normalizer_path`
- `runner_path`
- `contract_dependency`
- `notes`

第一批預期項目：

- `claude_code`
- `codex`
- `gemini`

### 2. Runtime Entrypoint Inventory

候選來源：

- `runtime_hooks/core/`
- `runtime_hooks/README.md`
- `scripts/run-runtime-governance.sh`

最小欄位：

- `entrypoint_name`
- `path`
- `category`
- `input_mode`
- `primary_output`
- `artifact_effect`

第一批預期項目：

- `session_start`
- `pre_task_check`
- `post_task_check`
- `session_end`
- shared enforcement shell entrypoint

### 3. Governance Tool Entry Inventory

只盤點正式 operator-facing 的工具，不把 `governance_tools/` 全部塞進來。

第一批分類：

- adoption
- drift
- smoke
- reviewer handoff
- release surface

候選第一批工具：

- `adopt_governance.py`
- `governance_drift_checker.py`
- `quickstart_smoke.py`
- `runtime_enforcement_smoke.py`
- `reviewer_handoff_summary.py`
- `trust_signal_overview.py`

最小欄位：

- `tool_name`
- `category`
- `canonical_use`
- `human_track`
- `agent_track`
- `produces_artifact`

### 4. Evidence Surface Inventory

這不是完整 evidence ontology，只列出目前可被 reviewer / governance flow
消費的 first-class output surface。

候選第一批項目：

- `artifacts/runtime/verdicts/<session_id>.json`
- `artifacts/runtime/traces/<session_id>.json`
- reviewer handoff summaries
- quickstart smoke terminal output
- drift checker structured output

最小欄位：

- `surface_name`
- `producer`
- `artifact_type`
- `machine_readable`
- `human_auditable`
- `used_by`

### 5. Authority Boundary Inventory

這一塊在 first slice 要刻意保持很淺。

候選來源：

- `governance/AUTHORITY.md`
- `governance_tools/authority_loader.py`
- `docs/beta-gate/agent-adoption-pass-criteria.md`
- `docs/decision-boundary-layer.md`

最小欄位：

- `authority_surface`
- `declared_source`
- `scope`
- `can_change_verdict`
- `notes`

重要限制：

這一版只盤點 **已宣告的 authority surface**，不處理完整 precedence
resolution。

---

## 建議輸出形狀

先做一份 machine-readable JSON，再做一份人可讀的摘要頁。

### Machine-readable

建議路徑：

- `docs/status/generated/runtime-surface-manifest.json`

頂層形狀：

```json
{
  "generated_at": "2026-04-01T12:00:00Z",
  "repo_commit": "<sha>",
  "adapters": [],
  "runtime_entrypoints": [],
  "tool_entries": [],
  "evidence_surfaces": [],
  "authority_surfaces": []
}
```

### Human-readable

建議路徑：

- `docs/status/runtime-surface-manifest.md`

用途：

- reviewer orientation
- agent orientation
- quick inventory lookup

Markdown 只做摘要，不複製完整 JSON。

---

## 生成方式

### Phase 1：只做靜態萃取

第一版不要做 runtime introspection。

先從這些來源萃取：

- 目錄結構
- 已知檔名
- 小型 declarative mapping
- 現有 docs

原因：

- 比較好 audit
- 比較好 replay
- 比較不容易偷偷長成第二套 semantic engine

### Phase 2：加入明確 generator script

候選路徑：

- `governance_tools/runtime_surface_manifest.py`

first-slice 責任只限於：

- 收集靜態 inventory
- 輸出 JSON
- 輸出簡短 human summary

不負責：

- runtime coverage scoring
- policy precedence reasoning
- verdict simulation

### Phase 3：只加一個 smoke check

候選檢查：

- 已知 adapter family 是否都列進 manifest
- core runtime entrypoint 是否都存在
- 生成出的 manifest 是否結構完整

這應該是一個 consistency smoke，不是新 gate。

### Phase 4：最小 Manifest Consistency Layer

在 first slice 後，建議補一層非常輕量的 signal 機制。

這層不應：

- 改變 verdict
- 阻擋 execution
- 重新解釋 authority semantics

這層只做三件事：

1. `unknown_surface`
   - runtime 出現未列於 manifest 的 adapter / entrypoint / tool / evidence producer
   - emit signal
2. `orphan_surface`
   - manifest 裡列出的 surface 在實際 runtime / repo state 中找不到
   - 先作 warning，不作 fail
3. `evidence_surface_mismatch`
   - 有 output 被當成 evidence surface 使用，但不在 manifest.evidence_surfaces 中
   - emit signal

這一層的定位是：

- soft enforcement
- non-invasive governance boundary
- self-awareness for the governance runtime

---

## 細部實作流程

### Step A：先凍結 first-slice scope

在寫 code 前，先明確凍結：

- 要包含哪些 adapter
- 要包含哪些 runtime entrypoint
- 要包含哪些工具分類
- 要包含哪些 evidence surface
- 要包含哪些 authority surface

這些清單之外的內容，全部先視為 out of scope。

### Step B：先手寫 extraction table

先用小型 mapping table 寫清楚：

- adapter 支援哪些 event
- runtime entrypoint 屬於哪一類
- governance tool 屬於哪一類

不要一開始就做 heuristics。

### Step C：先生成 JSON

JSON 是 source of truth。

Markdown 摘要頁應該從同一份資料模型導出，或至少使用同一組收集結果。

### Step D：先驗 reviewer usefulness

在說 manifest 完成之前，至少要驗證 reviewer 或 agent 能不能直接回答：

- 目前有哪些 adapter family？
- 哪些 entrypoint 真的會改變 runtime decision？
- adoption / drift / smoke 的正式工具入口是哪些？
- 哪些輸出面屬於 evidence-producing surface？

如果這些答不出來，代表 manifest 還太抽象。

### Step E：再決定是否擴張

後續可能擴的方向：

- runtime coverage checkpoint
- parity / maturity section
- multi-agent role inventory
- 更細的 authority-boundary annotations
- manifest consistency signals 接入既有 risk / drift surfaces

這些都不應該在 first slice 預設納入。

### Step F：決定 manifest 的 enforcement posture

在真正寫 generator 之前，先明確選定這條線的 posture：

- A. 純觀測（passive inventory）
- B. soft enforcement（emit signal，不改 verdict）
- C. hard enforcement（未列面不允許進入 decision pipeline）

目前建議採用：

- **B. soft enforcement**

原因：

- 保留 first-slice 的克制
- 不把 manifest 變成第二套 policy engine
- 但避免 manifest 與 runtime reality 分裂時完全沒有 signal

---

## 驗收條件

first slice 成功的標準：

1. cold reader 不用手動翻多個目錄，也能知道 framework 的 execution surfaces。
2. manifest 沒有創造新的語義，只整理既有 truth sources。
3. manifest 能把 execution surface 和 governance verdict logic 分開。
4. manifest 同時對兩種場景有用：
   - agent-assisted adoption
   - reviewer reconstruction
5. manifest 可以從 repo state 穩定重生。
6. manifest 與 runtime reality 發生偏離時，至少能發出 consistency signal。

---

## 需要注意的風險

### 風險 1：Semantic creep

manifest 一開始只是 inventory，後來悄悄變成第二套 policy layer。

緩解方式：

- first slice 只放 inventory 欄位
- 不直接改 verdict
- 不在 first slice 加 risk scoring

### 風險 2：Truth source duplication

manifest 用自己的話重述 policy / authority，最後和 canonical source 不一致。

緩解方式：

- 盡量只 reference canonical files
- 不重寫 precedence
- authority inventory 保持 shallow

### 風險 3：Execution / governance collapse

repo 開始把 harness surface 和 governance runtime 混成同一層。

緩解方式：

- 明確拆區塊：
  - execution surface
  - evidence surface
  - authority surface

### 風險 4：Overbuilding

first slice 不小心長成大型 observability 專案。

緩解方式：

- 一份 JSON
- 一份 Markdown 摘要
- 一個 generator
- 一個 smoke check
- 最多一層 consistency signal，不再往上長

### 風險 5：Passive manifest drift

manifest 看起來完整，但 runtime surface 已經漂移，而系統沒有任何告警。

緩解方式：

- 在 first slice 之後接入最小的 manifest consistency signal
- 將 `unknown_surface` / `orphan_surface` / `evidence_surface_mismatch`
  視為觀測事件，而不是立即性 verdict

---

## 建議下一步順序

1. 先判斷這份計畫要不要採用。
2. 如果採用，先凍結 first-slice inventory 清單。
3. 新增 `governance_tools/runtime_surface_manifest.py`。
4. 生成：
   - `docs/status/generated/runtime-surface-manifest.json`
   - `docs/status/runtime-surface-manifest.md`
5. 補一個最小 consistency smoke。
6. 再決定要不要把 manifest consistency signal 接到既有 drift / risk surface。

這樣可以把新線維持在小而可審計的範圍內，同時讓 framework 的
execution surface 更可見。
