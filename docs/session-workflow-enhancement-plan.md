# Session Workflow Enhancement — Implementation Plan

> Based on: `session-workflow-enhancement-v2.md` (Trust-Bounded Closeout Design)
> Status: Planning
> Date: 2026-04-07

---

## Executive Summary

V2 的設計方向正確，信任邊界清晰，三角色分工合理。可行性整體為高，但有一個架構對齊問題需要在動工前確認。

**可行性結論**：

| Slice | 可行性 | 主要風險 |
|-------|--------|---------|
| 1. Schema contract doc | ✅ 無風險 | — |
| 2. session_end_hook（canonical producer） | ⚠ 中等 | 架構對齊問題（見下） |
| 3. /wrap-up skill（candidate writer） | ✅ 低風險 | — |
| 4. session-index.ndjson | ✅ 低風險 | — |
| 5. session_start context injection | ⚠ 中等 | graceful degrade 路徑需完整 |
| 6. closeout_audit.py | ✅ 低風險 | 可重用現有 aggregation pattern |

---

## 架構決策

### 核心問題：Validation Ownership

選 Option A 或 B，真正的差異不是「改動大小」，而是 **validation + normalization 的 ownership 放在哪裡**：

| 問題 | Option A（inline） | Option A（分層） | Option B |
|------|-------------------|----------------|---------|
| 誰擁有 canonicalization | run_session_end（綁死） | build_canonical_closeout（可抽出） | session_end_hook |
| validation 可重用 | ❌ | ✅ | ✅ |
| 未來插 enforcement/audit/replay | ❌ 卡住 | ✅ 開放 | ✅ 開放 |
| 需要改 dispatcher | 否 | 否 | 是（或確認 caller） |

### 決定：Option A + 強制內部分層

選 Option A（不改 dispatcher），但**必須**抽出內部 layer，不能 inline：

```
run_session_end()                  ← orchestration only
  → build_canonical_closeout()     ← 新增，可獨立呼叫，pure function
  → _run_session_end_core()        ← 原本邏輯（verdict / memory / summary）
```

**`build_canonical_closeout()` 必須是 pure function**：同一 input → 同一 canonical output。
這樣未來才能做 replay、audit re-run、dry-run policy testing。

**Implementation guardrail（不可違反）**：
> `build_canonical_closeout()` must not perform filesystem discovery, timestamp generation, or runtime dispatch internally. All external inputs must be passed in explicitly.

正確結構：
```
外層（run_session_end orchestration）負責收集：
  - candidate_payload  ← _pick_latest_candidate() 的結果
  - closed_at          ← datetime.now(timezone.utc).isoformat()
  - existing_artifacts ← 當下已知存在的 artifact 路徑集合
  - runtime_signals    ← session 期間的 tool usage signals

build_canonical_closeout() 只做確定性邏輯，不做 IO。
```

**設計 sanity check**：
> 如果把 `/wrap-up` 拿掉，系統還能不能產生 canonical closeout？
>
> 答案必須是「可以」——走 missing 路徑，closeout_status = missing，但 canonical artifact 仍然產生。
> 如果答案是「不行」，設計就錯了。

---

## Session Identity Contract

### 問題

`/wrap-up` 寫 candidate 時，必須知道 session_id 才能命名檔案。但「能不能拿到」不夠——必須定義 session_id 在整個 lifecycle 中是否**穩定**。

### 決定：hard requirement

> `/wrap-up` 執行 context MUST include session_id。

Session_id 是整個 closeout pipeline 的 primary key。所有 hook / command 必須能取得。

若未來發現取不到的情境（tool callback、resume 等），解法是 UUID binding pattern：

```
closeout_candidates/tmp/{uuid}.json  ← /wrap-up 寫
session_end 時做 binding             ← hook 找最新 tmp + bind to session_id
```

但這會讓系統複雜化——目前先保持 hard requirement，遇到問題再處理。

---

## Candidate Closeout Schema（/wrap-up 輸出）

AI 寫，untrusted，寬鬆格式：

```json
{
  "task_intent": "string",
  "work_summary": "string",
  "tools_used": ["string"],
  "artifacts_referenced": ["string"],
  "open_risks": ["string"]
}
```

**沒有** `session_id`、`closed_at`、`closeout_status`——這三個由 system 補。

路徑：`artifacts/runtime/closeout_candidates/{session_id}/{timestamp}.json`

**Timestamp 命名格式**（固定，可字典序排序）：
```
20260408T143210123456Z.json
```
Python 產生：`datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")`

**Append-only，不覆寫**。若 `/wrap-up` 被呼叫兩次，兩份 candidate 都保留。
`_pick_latest_candidate()` 依檔名字典序取最新一份，在外層呼叫（不在 `build_canonical_closeout()` 內部）。

**重要語意**：「最新」代表 authoring precedence（最後一版候選），不是 truth precedence（最可信版本）。

不使用 `closeout_candidates/{session_id}.json`（單一檔案）——被覆寫後最後版本不等於最完整版本。

---

## Canonical Closeout Schema v1

System 寫，trusted，schema 固定：

```json
{
  "session_id": "string",
  "closed_at": "ISO-8601 datetime",
  "closeout_status": "valid | missing | schema_invalid | content_insufficient | inconsistent",
  "task_intent": "string | null",
  "work_summary": "string | null",
  "evidence_summary": {
    "tools_used": ["string"],
    "artifacts_referenced": ["string"]
  },
  "open_risks": ["string"]
}
```

路徑：`artifacts/runtime/closeouts/{session_id}.json`

### closeout_status 決定邏輯

| Status | 條件 |
|--------|------|
| `missing` | candidate 不存在，且無 fallback |
| `schema_invalid` | candidate JSON 不合法或欄位型別錯誤 |
| `content_insufficient` | schema 合法但 work_summary 空、evidence 空 |
| `inconsistent` | artifacts_referenced 中的檔案不存在；或 tools_used 有 pytest/build 但無對應 session signal |
| `valid` | 通過 schema validation + minimal semantic validation |

---

## 實作 Slices

---

### Slice 1：Schema Contract 文件（零代碼風險）

**產出物**：
- `docs/closeout-schema.md`：定義 candidate + canonical schema、trust boundary、ownership rules
- 更新 `docs/classification-reaction-policy.md` 相關引用（若有）

**完成條件**：
- candidate schema 有明確欄位定義
- canonical schema 有明確欄位定義
- closeout_status 5 個值有明確判定條件
- trust boundary 明文化（AI 只能寫 candidate，不能寫 canonical）

---

### Slice 2：session_end_hook — Canonical Producer

**修改範圍**（Option A + 強制分層）：
- `runtime_hooks/core/session_end.py`

**新增函數（internal layer）**：

```python
# Pure function — same input → same canonical output
def build_canonical_closeout(
    session_id: str,
    project_root: Path,
    closed_at: str,
) -> dict:
    candidate = _pick_latest_candidate(session_id, project_root)
    if candidate is None:
        return _make_canonical(session_id, closed_at, "missing", None)
    ok, reason = _validate_candidate_schema(candidate)
    if not ok:
        return _make_canonical(session_id, closed_at, "schema_invalid", candidate)
    ok, reason = _run_semantic_validation(candidate, project_root)
    status = "valid" if ok else reason  # reason 直接是 status string
    return _make_canonical(session_id, closed_at, status, candidate)

def _pick_latest_candidate(session_id: str, project_root: Path) -> dict | None: ...
def _validate_candidate_schema(candidate: dict) -> tuple[bool, str]: ...
def _run_semantic_validation(candidate: dict, project_root: Path) -> tuple[bool, str]: ...
def _make_canonical(session_id, closed_at, status, candidate) -> dict: ...
def _write_canonical_closeout(canonical: dict, project_root: Path) -> Path: ...
```

**`run_session_end()` 的改動**（orchestration only，不加業務邏輯）：

```python
def run_session_end(project_root, session_id, runtime_contract, ...):
    canonical = build_canonical_closeout(session_id, project_root, closed_at)
    _write_canonical_closeout(canonical, project_root)
    _append_session_index(canonical, project_root)  # Slice 4
    return _run_session_end_core(...)  # 原本邏輯，不動
```

**closeout_status 判定順序**：
```
candidate 不存在 → missing
JSON 解析失敗 → schema_invalid
必要欄位缺失 → schema_invalid
semantic validation 失敗 → content_insufficient or inconsistent
全部通過 → valid
```

**向後相容**：
- 若 `artifacts/runtime/closeout_candidates/{session_id}.json` 不存在，直接走 missing 路徑，不 crash
- `run_session_end()` 現有 `runtime_contract` 輸入路徑維持不變

**測試**：
- `test_session_end_canonical_closeout.py`
  - no candidate → status=missing
  - schema_invalid candidate → status=schema_invalid
  - empty work_summary → status=content_insufficient
  - artifact not found → status=inconsistent
  - clean candidate → status=valid

---

### Slice 3：/wrap-up Skill（Candidate Writer）

**產出物**：
- Claude Code skill 定義（`skills/wrap-up/SKILL.md` 或 project-level instructions）

**行為規格**：
- AI 依 candidate schema 整理 session 內容
- 寫入 `artifacts/runtime/closeout_candidates/{session_id}.json`
- 不判定 closeout_status
- 不寫 canonical artifact

**pre-validation checklist（提示層）**：
- 是否列出具體檔案名稱（不能只寫「相關檔案」）
- 是否列出具體工具（pytest, build, lint 等）
- 是否列出未完成事項
- 是否列出 open_risks
- 不含純 vague phrases（「已完成相關修改」等）

**注意**：checklist 是 heuristic，不是 validation。通過 checklist ≠ canonical valid。

---

### Slice 4：Session Index（NDJSON append）

**修改範圍**：
- `runtime_hooks/core/session_end.py` — 在 canonical closeout 寫入後 append

**路徑**：`artifacts/session-index.ndjson`

**每行欄位**：
```json
{"session_id": "...", "closed_at": "...", "closeout_status": "...", "task_intent": "...", "has_open_risks": true}
```

**設計原則**：
- append-only，不重寫
- 失敗不影響主流程（try/except，write failure → warning only）
- 非 source of truth，source of truth = canonical closeout artifact

---

### Slice 5：Session Start Context Injection

**修改範圍**：
- `runtime_hooks/core/session_start.py` — `build_session_start_context()`

**讀取來源**：
- `artifacts/runtime/closeouts/` — 只讀 canonical closeout，不讀 candidate

**選擇邏輯**：
- 依 `closed_at` 欄位排序（不依檔名）
- 取最新一筆

**注入規則**：

| closeout_status | 注入內容 |
|-----------------|---------|
| `valid` | task_intent + work_summary + open_risks |
| `content_insufficient` | 僅注入 diagnostic warning（closeout 品質不足） |
| `schema_invalid` / `missing` / `inconsistent` | minimal warning，不注入 summary |

**Graceful Degradation**：
- `artifacts/runtime/closeouts/` 不存在 → 靜默，不 crash
- 目錄為空 → 靜默，不注入
- JSON 解析失敗 → warning，不注入

**注意**：不讀 raw verdict 作為 continuity 主資料。Verdict 是 decision artifact，不是 continuity artifact。

---

### Slice 6：Closeout Audit Script

**產出物**：`governance_tools/closeout_audit.py`

**讀取來源**：只讀 `artifacts/runtime/closeouts/`（canonical only）

**輸出**：

```
[closeout_audit]
summary=ok=True | sessions=N | valid=N | missing=N | insufficient=N | inconsistent=N | schema_invalid=N
valid_rate=0.XX
recent_7d_valid_rate=0.XX
[status_distribution]
  valid=N
  missing=N
  content_insufficient=N
  ...
```

**設計原則**：
- 重用 `classification_session_summary.py` 的 aggregation pattern
- 不另發明 closeout 判準（所有判準在 canonical artifact 裡）
- 可接 `session-index.ndjson` 作快取（可選）

---

## 測試策略

每個 slice 有對應測試，全部在 `tests/` 下：

| Slice | 測試檔 |
|-------|--------|
| 2 | `test_session_end_canonical_closeout.py` |
| 4 | `test_session_index.py`（或併入 2） |
| 5 | `test_session_start_context_injection.py` |
| 6 | `test_closeout_audit.py` |

Slice 1、3 不需要新測試（doc + skill）。

---

## 不做的事（Out of Scope）

- 修改 verdict / decision logic
- 引入 hidden state
- 讓 AI 自行判定 closeout_status
- 讓 candidate 直接進入 downstream（reviewer / audit / context injection 全部只讀 canonical）
- 建立 closeout 之外的新 summary 格式

---

## 最大風險

**主要風險**：AI 寫入結構正確但語意空洞的 candidate，通過 schema validation 但進入 content_insufficient 路徑，導致 session_start 只拿到 minimal warning 而非有用的 continuity context。

**緩解方式**：
1. Slice 3 的 pre-validation checklist（prompt-time heuristic）提高 candidate 品質
2. Slice 2 的 semantic validation 擋住空洞內容
3. Slice 5 的注入規則確保 content_insufficient 不污染 context（只注入 warning）

**次要風險**：Option A 讓 `run_session_end()` 過大。
緩解：每個新功能提取為獨立函數，`run_session_end()` 只做協調。

---

## 實作前確認清單

在開始 Slice 2 之前：

- [ ] Slice 1 文件完成（schema 定義先落地，再動代碼）
- [ ] 確認 `session_id` 在 `/wrap-up` 執行時是否可穩定取得（hard requirement，不是 nice-to-have）
- [ ] 確認 `/wrap-up` skill 的觸發方式（Claude Code slash command？）
- [ ] 確認 `build_canonical_closeout()` 介面設計（可在 Slice 1 文件中一起定義）

---

## 架構設計 Sanity Check

> **如果把 `/wrap-up` 拿掉，系統還能不能產生 canonical closeout？**
>
> ✅ 答案必須是「可以」：candidate 不存在 → `closeout_status = missing` → canonical artifact 仍然寫入。
>
> 這條 check 確保 canonical path 永遠是 `session_end → canonical`，`/wrap-up` 只是提高輸入品質的工具，不是系統運轉的前提。
