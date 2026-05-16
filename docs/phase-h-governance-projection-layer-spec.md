# Phase H — Governance Projection Layer Spec

Date: 2026-05-09
Status: Spec (supersedes Phase H Draft Plan)
Replaces: Phase H Hybrid Reviewer Surface Plan (draft)

---

## 1. Framing

Phase H 的核心保護目標是：

**Projection Integrity**

不是 dashboard sophistication，不是 HTML 美觀。

具體定義：

> HTML output 必須忠實反映 source evidence，
> 不得合成、推論、或產生任何不存在於 source artifacts 的 governance claim。

這個框架稱為 **Governance Projection Layer**，不是 Governance HTML System。

命名本身是 contract 的一部分：

- `render_*` 命名 → 合法
- `generate_*` 命名 → 禁止
- `project_*` 命名 → 合法
- `summarize_*` 命名 → 禁止

---

## 2. Core Contracts

### 2.1 Renderer Synthesis Contract

```
RENDERER MUST NOT SYNTHESIZE.
```

**Structural Rule（可機器驗證）：**

> Every element in HTML output MUST be traceable to a named field in a source artifact.
> No rendered content may originate from renderer-internal logic alone.

**Semantic Rule（需 contract test 覆蓋）：**

> Renderer MUST NOT produce absence-based verdicts.
>
> 具體禁止：
> - if (warnings.length === 0) → render "No issues detected"   ← 禁止
> - if (drift === null) → render "Drift-free session"          ← 禁止
>
> 理由：source JSON 中不存在的 positive claim，renderer 產生後即為 synthesis。
> "沒有 WARNING" ≠ "通過"。這個 verdict 只能來自 authority layer，不能由 renderer 推論。

**允許的 renderer 操作：**

| 操作 | 允許 |
|------|------|
| 重排 field 的顯示順序 | ✓ |
| 高亮特定 severity level | ✓ |
| filter by field value | ✓ |
| aggregate count of items | ✓ |
| display field value verbatim | ✓ |
| 推論不存在的 verdict | ✗ |
| 產生 absence-based positive claim | ✗ |
| 解釋 drift 原因 | ✗ |
| 總結不存在的 risk | ✗ |

### 2.2 Projection Integrity Contract (H1 Success Criterion)

這是 H1 的 machine-verifiable success criterion，取代 UX 導向的「1~3 分鐘理解」標準。

```
PROJECTION INTEGRITY RULES:

R1. Every FAIL item in source JSON MUST appear in HTML projection.
R2. Every WARNING item in source JSON MUST appear in HTML projection.
R3. Every DRIFT item in source JSON MUST appear in HTML projection.
R4. Renderer MUST disclose missing source fields (not silently omit).
R5. Renderer MUST disclose schema mismatch (not silently degrade).
R6. Renderer MUST disclose partial rendering when input is incomplete.
```

驗證方式：

- `tests/test_projection_integrity.py`
- 輸入已知 source JSON（含若干 FAIL/WARNING/DRIFT items）
- 解析 HTML output
- Assert 每個 item 的 id / label 出現在 HTML 中

### 2.3 Cross-Artifact Interpretation Prohibition

這是 Renderer Synthesis Contract 的特定延伸，針對多 artifact 情境。

```
RENDERER MUST NOT derive semantic conclusions
from multi-artifact relationships.
```

**具體禁止（即使 cross-artifact 事實上存在衝突）：**

```
禁止：
  "Claim binding may be unreliable"          ← renderer 推論
  "Runtime integrity appears degraded"        ← renderer 推論
  "Inconsistency detected across artifacts"   ← renderer 推論

允許：
  [claim-enforcement-check.json] drift: true  ← verbatim field display
  [runtime-completeness-audit.json] claim_binding_written: false  ← verbatim field display
```

理由：cross-artifact semantic interpretation 是 authority layer 的職責。若 reviewer 觀察到 artifact A 和 artifact B 有邏輯矛盾，這是 reviewer 的 governance decision，不是 renderer 的輸出。

**Renderer 允許的唯一 cross-artifact 操作：**

- 將多個 artifact 的 field 並排顯示（side-by-side layout）
- 在 Projection Coverage Block 中顯示每個 artifact 的覆蓋計數

---

### 2.4 Projection Coverage Block

Projection Integrity Contract (2.2) 是 test-time verification。
Coverage Block 將同一資訊暴露給 archive reviewer，成為 runtime-visible。

#### Item Identity (CLOSED — Decision 4)

每個 projection item 使用 canonical identity，格式：

```
<artifact_name>#<json_pointer>#<severity>#<item_key>
```

範例：

```
claim-enforcement-check.json#/violations/0#FAIL#CLAIM_DRIFT_001
runtime-completeness-audit.json#/checks/claim_binding_written#WARNING#claim_binding_written
```

**item_key 規則：**

1. source item 有 explicit `id` field → 使用 `id` 作為 item_key
2. 無 `id` → 使用 stable field name 作為 item_key
3. array-based item → JSON pointer 含 index

**renderer 行為：**

- 每個 rendered item 必須在 HTML 中附加 `data-projection-id="<canonical_id>"`
- renderer MUST NOT 發明不可追溯至 source location 的 synthetic id

#### Coverage Block 格式

```html
<!-- PROJECTION COVERAGE
coverage_complete: true
total_fail_items: 2
rendered_fail_items: 2
total_warning_items: 1
rendered_warning_items: 1
total_drift_items: 1
rendered_drift_items: 1
missing_projection_ids: []
partial_reason: null
-->
```

coverage_complete = false 範例：

```html
<!-- PROJECTION COVERAGE
coverage_complete: false
total_fail_items: 2
rendered_fail_items: 2
total_warning_items: 1
rendered_warning_items: 0
total_drift_items: 1
rendered_drift_items: 1
missing_projection_ids:
  - runtime-completeness-audit.json#/checks/claim_binding_written#WARNING#claim_binding_written
partial_reason: missing_warning_projection
-->
```

**coverage_complete 規則：**

```
coverage_complete = true
  當且僅當：
  rendered_fail_items == total_fail_items
  AND rendered_warning_items == total_warning_items
  AND rendered_drift_items == total_drift_items

coverage_complete = false 時：
  missing_projection_ids 必須列出所有未渲染的 canonical id
  partial_reason 必須填入原因（schema_mismatch / parse_error / field_missing / missing_warning_projection）
  兩者不得為 null / 空
```

**reviewer 使用方式：**

reviewer 可以 grep HTML 文件中的 `PROJECTION COVERAGE` 區塊，機器可讀，不需要解析 HTML 結構。

---

### 2.5 Projection Provenance Block

每個 HTML 輸出必須內嵌 Provenance Block，格式如下：

```html
<!-- PROJECTION PROVENANCE
renderer_version: 0.1.0
template_version: 0.1.0
render_timestamp: 2026-05-09T10:00:00Z
schema_version: 1.0
source_artifact_hash: sha256:<hash>
-->
```

**source_artifact_hash 計算規格：**

多個 source artifact 的 hash 計算方式如下：

```python
import hashlib, json

def compute_source_hash(artifact_paths: list[str]) -> str:
    pairs = []
    for path in sorted(artifact_paths):           # sorted → deterministic
        with open(path, "rb") as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()
        pairs.append(f"{path}:{content_hash}")
    combined = "\n".join(pairs)
    return hashlib.sha256(combined.encode()).hexdigest()
```

特性：
- order-independent（sorted）
- multi-file（每個 artifact 獨立 hash 後再合併）
- deterministic（相同 input 必然相同 output）

---

### 2.6 Obligation Trigger Boundary Contract (NEW)

此條款定義 commit class 與 obligation trigger 的可採信邊界，避免 causal self-contamination。

```
AUTO COMMIT MUST NOT BE USED AS OBLIGATION TRIGGER SOURCE.
```

**Rationale:**
- `auto:` commit 可能同時包含 trigger artifact（例如 code change）與 obligation artifact（例如 memory / PLAN 更新）
- 同一 commit 若同時宣稱「觸發義務」與「滿足義務」，causal attribution 不可分
- verifier 在僅有 git diff 的情況下無法可靠判斷誰導致誰

**Commit class policy（v1）**

```yaml
commit_classes:
  auto:
    can_trigger_obligation: false
    can_satisfy_obligation: true
    can_be_evidence_carrier: true
    can_be_observation_artifact: true
    can_authorize_phase_transition: false
    can_authorize_policy_mutation: false
    requires_human_causal_review: true
    reason: "auto commits may co-mingle trigger and obligation artifacts"
```

**Verifier enforcement**

1. 若 commit class = `auto` 且檢測到 trigger-like 變更，該 trigger 標記為 `non_authoritative_trigger`
2. `non_authoritative_trigger` 不得啟動 obligation deadline/expiry 計時器
3. `auto` commit 仍可被計入 obligation satisfaction candidate（僅在已有 authoritative trigger 前提下）
4. 若同一 `auto` commit 同時包含 trigger-like 與 obligation-like 變更，必須標記 `causal_self_contamination=true`
5. `causal_self_contamination=true` 時，verifier 只能輸出 observation，不得輸出 causal assertion

**Machine-readable output contract (v1)**
- Canonical schema: `schemas/contamination_admissibility.schema.json`
- Enforcement intent: detect layer may evolve; inference permissioning must stay fail-closed.

Contaminated example:

```json
{
  "schema_version": "1.0",
  "trigger_authority": "contaminated",
  "causal_self_contamination": true,
  "contamination_types": ["self"],
  "causal_assertion_allowed": false,
  "allowed_output_modes": ["observation_only"],
  "prohibited_output_modes": [
    "causal_inference",
    "phase_transition_assertion",
    "obligation_satisfaction_assertion"
  ],
  "admissibility_status": "degraded"
}
```

Normative rules:
1. `causal_assertion_allowed=false` 時，`allowed_output_modes` 不得包含 `causal_inference`
2. `trigger_authority=contaminated|unknown` 時，`admissibility_status` 不得為 `admissible`
3. `prohibited_output_modes` 必須至少包含 `causal_inference`
4. contamination detection `unknown` 仍需 fail-closed（不得升級為 causal assertion）

**Boundary note**
- 在未引入外部 state source（CI artifact / deployment record）前，
  obligation timing boundary 以 `same-working-day` 為 operational default，
  不採 `N commits after trigger`。

---

## 3. Phase H1 — Runtime Closeout HTML

Priority: HIGH

### 3.1 Input Contract

```
artifacts/runtime/<session_id>/
  ├── closeout-summary.json        (required)
  ├── claim-enforcement-check.json (required)
  └── runtime-completeness-audit.json (required)
```

若任何 required artifact 缺失：renderer 必須在 HTML 中明確顯示 `[MISSING: <filename>]`，不得靜默跳過或推論其內容。

### 3.2 Output

```
artifacts/reports/<session_id>/session-closeout.html
```

### 3.3 Technical Constraints

```
Single-file HTML:
  - inline CSS (no external stylesheet)
  - inline JS (no CDN, no external script)
  - offline-readable
  - deterministic: same input → same output (modulo render_timestamp)

Read-only projection:
  - HTML MUST NOT modify source artifacts
  - HTML MUST NOT write to runtime artifact paths
```

### 3.4 Visual Sections

顯示順序：

1. **Projection Provenance Block** — renderer / template / hash / timestamp（HTML comment，機器可讀）
2. **Projection Coverage Block** — total vs rendered counts per severity（HTML comment，機器可讀）
3. **Session Summary** — session_id, repo, runtime_status, closeout_validity, reviewer_override_required
4. **Drift Visibility** — 僅顯示 WARNING / FAIL / DRIFT / DOWNGRADE / BLOCK；PASS 不顯示
5. **Claim Enforcement** — claim_level, enforcement_action, drift_detected, publication_scope（逐 artifact verbatim，不做 cross-artifact interpretation）
6. **Runtime Completeness** — session_end_invoked, canonical_closeout_written, claim_binding_written, integrity_ok（逐 artifact verbatim，不做 cross-artifact interpretation）
7. **Missing / Schema Mismatch Disclosure** — 若有

注意：Provenance Block 和 Coverage Block 為 HTML comment 格式，不在 visible UI 中顯示，但存在於 HTML source 供機器讀取。

### 3.5 Error Handling Policy

| 狀況 | renderer 行為 |
|------|--------------|
| required field 缺失 | 顯示 `[FIELD MISSING: <field_name>]`，繼續 render 其他欄位 |
| source artifact 缺失 | 顯示 `[ARTIFACT MISSING: <filename>]`，不 render 該 section |
| schema version mismatch | 顯示 `[SCHEMA MISMATCH: expected <X>, got <Y>]` |
| JSON parse error | 顯示 `[PARSE ERROR: <filename>]`，不 render 該 section |

禁止：silently render empty section。

### 3.6 Trigger

`render_session_closeout_html.py` 由 `session_end_hook.py` 在 canonical closeout 寫入後自動呼叫。

不在 pre-push hook 執行（pre-push 不應依賴 session artifact state）。

### 3.7 Deliverables

```
governance_tools/render_session_closeout_html.py
templates/session_closeout_single_file.html
tests/test_projection_integrity.py
tests/test_render_session_closeout_html.py
```

### 3.8 Early Inflation Guard (H1)

```
max_sections: 6
max_inline_css_lines: 150
max_inline_js_lines: 100
renderer_loc_budget: 300 lines (excluding template)
```

超出 budget 必須在 PR review 時明確 justify，不得自然膨脹。

---

## 4. Phase H2 — Reviewer Navigation Surface

Priority: MEDIUM

### 4.1 Collapsible Sections Policy

H2 的「預設摺疊 PASS spam」需要解決與 Renderer Synthesis Contract 的張力。

**決定：**

Renderer 不得自行判斷哪些 section 是 "spam"。摺疊行為由 source artifact 的 field 決定：

```json
{
  "display_priority": "low"   // renderer 讀此 field → 預設摺疊
  "display_priority": "high"  // renderer 讀此 field → 預設展開
}
```

若 source artifact 未提供 `display_priority`，renderer 預設展開（保守策略）。

理由：renderer 若自行決定哪些 PASS 不重要，即為 governance classification，違反 Synthesis Contract。

### 4.2 Evidence Filters

Filter 選項由 source artifact 中實際出現的 severity level 決定，不由 renderer hardcode。

允許的 filter 實作：

```javascript
// 只 filter，不 synthesize
function filterBySeverity(level) {
  document.querySelectorAll('[data-severity]').forEach(el => {
    el.hidden = (el.dataset.severity !== level);
  });
}
```

### 4.3 Early Inflation Guard (H2)

```
max_filters: 5
max_js_lines_delta_from_H1: +150
max_new_sections: 2
```

---

## 5. Phase H3 — Governance Observability Pipeline

Priority: MEDIUM（前置條件：H3A 完成）

H3 不是 H1/H2 的 renderer extension，而是獨立的 observability pipeline。

拆分：

```
H3A — Aggregation Layer    (先做)
H3B — Dashboard Renderer   (H3A contract 完成後才開始)
```

### 5.1 H3A — Aggregation Layer

**第一個 deliverable 是 contract 文件，不是 code。**

```
docs/phase-h-aggregation-contract.md
```

此 contract 必須定義：

**Session Comparability Definition**

```
兩個 session 可比較的條件：
- 相同 schema_version，或
- schema_version 差異在 backfill policy 覆蓋範圍內
```

**Schema Evolution Policy**

```
Option A: Window Policy
  - aggregation 只處理 schema_version >= <baseline> 的 sessions
  - 舊 session 不進入 aggregation window

Option B: Backfill Policy
  - 舊 schema 有 migration map → normalize 後可比較
  - 無 migration map → 標記為 INCOMPARABLE，不進入 trend

選擇哪個 option 是 H3A 的第一個架構決定。
```

**Window Integrity Rules**

```
- aggregation window 必須有明確的時間範圍或 session count 上限
- 不得做 unbounded aggregation（所有 session 的 all-time trend）
- missing artifact 的處理：標記 GAP，不填補，不插值
```

**Sampling Bias Disclosure**

```
若 aggregation window 內有 artifact missing sessions，
dashboard 必須顯示：
  "X of Y sessions in window had missing artifacts (excluded)"
不得靜默排除。
```

沒有這份 contract，H3B 不得開始。

### 5.2 H3B — Dashboard Renderer

前置條件：`docs/phase-h-aggregation-contract.md` 完成並通過 review。

技術選型：Vanilla JS + SVG（無 CDN，無 server dependency）。

---

## 6. Phase H4 — Governance Self-Observability

Priority: LONG TERM

### 6.1 Critical Constraint

```
H4 is READ-ONLY observability.

MUST NOT:
  - auto-delete governance rules
  - auto-downgrade enforcement
  - auto-adjust runtime policy

H4 surfaces problems. Remediation is human decision.
```

### 6.2 Early Inflation Signal (Bridge to H4)

在 H4 正式開始前，H1/H2 的 Early Inflation Guard 是唯一的 inflation 觀測機制。

H4 前的 interim 做法：在每次 renderer PR 中，reviewer 必須確認：

```
Checklist:
[ ] renderer LOC within budget
[ ] no new synthesized claims added
[ ] no new governance verdict generated by renderer
[ ] Projection Integrity tests still cover all FAIL/WARNING/DRIFT paths
```

---

## 7. Architecture Summary

```
authority layer          projection layer
─────────────────        ─────────────────
runtime artifacts    →   render_session_closeout_html.py
claim binding            │
decision logs            ↓
memory records           session-closeout.html
validator outputs        (read-only, single-file, offline)
                         (Projection Provenance Block embedded)

cross-session data   →   aggregate_sessions.py (H3A)
(after H3A contract)     │
                         ↓
                         render_dashboard_html.py (H3B)
                         dashboard.html
```

---

## 8. Open Decisions

| # | 決定 | 影響 | 負責人 |
|---|------|------|--------|
| 1 | H3A Schema Evolution: Window Policy vs Backfill Policy | H3A aggregation contract | TBD |
| 2 | `display_priority` field 加入哪些 source artifact schema | H2 collapsible sections | TBD |
| 3 | renderer LOC budget 超出時是 CI fail 還是 PR warning | Early Inflation Guard enforcement | TBD |
| 4 | ~~Projection Coverage Block item identity~~ | ~~test_projection_integrity.py~~ | CLOSED: canonical id = `<artifact>#<json_pointer>#<severity>#<item_key>` |
