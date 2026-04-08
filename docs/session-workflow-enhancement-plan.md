# Session Workflow Enhancement Implementation Plan

> 依據：bounded closeout trust-boundary 設計
> 狀態：implementation-complete
> 更新日期：2026-04-08

## 目的

這條線的目標不是把 session 結束流程做得更複雜，而是把 closeout 從「AI 自述」收斂成「system-validated canonical artifact」。

這條線已經固定的核心形狀是：

- AI 只能產生 candidate closeout
- system 只在 `session_end` 產生 canonical closeout
- downstream consumer 只能讀 canonical

也就是：

```text
AI candidate -> system canonicalization -> canonical consumer only
```

## 已完成的 bounded slices

### Slice 1：Canonical / Candidate Schema

已完成：

- [docs/closeout-schema.md](e:/BackUp/Git_EE/ai-governance-framework/docs/closeout-schema.md)
- `candidate` 與 `canonical` 的 trust boundary
- `closeout_status` 五種狀態定義

核心原則：

- candidate 是 untrusted input
- canonical 是 authoritative artifact
- `session-index.ndjson` 只是 cache，不是 source of truth

### Slice 2：Session-End Canonical Producer

已完成：

- [runtime_hooks/core/_canonical_closeout.py](e:/BackUp/Git_EE/ai-governance-framework/runtime_hooks/core/_canonical_closeout.py)
- [runtime_hooks/core/session_end.py](e:/BackUp/Git_EE/ai-governance-framework/runtime_hooks/core/session_end.py)

固定邊界：

- `build_canonical_closeout()` 是唯一 canonicalization function
- `run_session_end()` 做 orchestration，不做第二套 closeout semantics
- candidate 缺失或無效時，仍然要寫出 canonical artifact

### Slice 3：`/wrap-up` Candidate Drafting Surface

已完成：

- [.claude/skills/wrap-up/SKILL.md](e:/BackUp/Git_EE/ai-governance-framework/.claude/skills/wrap-up/SKILL.md)

固定邊界：

- `/wrap-up` 只是 candidate drafting surface
- 不是 canonical producer
- 不是 closeout authority
- 移除 `/wrap-up` 不應阻止 canonical closeout 被寫出

### Slice 4：Session Index Cache

已完成：

- `artifacts/session-index.ndjson`

固定邊界：

- append-only
- write failure 為 warning，不影響 canonical closeout
- 不可被 `session_start`、audit、或 downstream consumer 當成 source of truth

### Slice 5：Session-Start Closeout Context Injection

已完成：

- [runtime_hooks/core/_canonical_closeout_context.py](e:/BackUp/Git_EE/ai-governance-framework/runtime_hooks/core/_canonical_closeout_context.py)
- [runtime_hooks/core/session_start.py](e:/BackUp/Git_EE/ai-governance-framework/runtime_hooks/core/session_start.py)

固定邊界：

- 只讀 canonical closeout
- 依 `closeout_status` 做 bounded injection
- graceful degradation，不因 closeout 品質差而讓 session_start 崩潰

### Slice 6：Closeout Audit

已完成：

- [governance_tools/closeout_audit.py](e:/BackUp/Git_EE/ai-governance-framework/governance_tools/closeout_audit.py)

固定邊界：

- aggregation only
- 不新增第二套 authority
- 不重新定義 `closeout_status`
- 不直接碰 verdict

## 已固定的 trust boundary

這條線真正重要的不是檔案數量，而是信任責任已分開：

| Layer | Writer / Owner | 可做的事 | 不可做的事 |
| --- | --- | --- | --- |
| candidate | AI / `/wrap-up` | 提供 draft summary | 直接產生 canonical |
| canonical | system / `session_end` | validation、canonicalization、status 決定 | 讀 candidate 當作 source of truth |
| consumer | `session_start` / audit / reviewer surface | 只讀 canonical | 直接吃 candidate |

## 驗證狀態

目前在這台機器上已完成：

- canonical closeout 相關模組 `py_compile` 通過
- closeout 測試 slice 通過：
  - `tests/test_canonical_closeout.py`
  - `tests/test_canonical_closeout_context.py`
  - `tests/test_closeout_audit.py`
  - `tests/test_session_end_closeout_integration.py`
- 結果：`93 passed`

目前殘留的是 `.pytest_cache` 權限 warning，不屬於 closeout 邏輯失敗。

## 完成定義

這條線目前可視為：

> implementation-complete, semantics-observation phase

成立條件：

- producer / canonical / consumer 已分層
- closeout trust boundary 已固定
- consumer 已限制為 canonical-only
- `/wrap-up` 沒有升格成 canonical authority
- audit 維持 aggregation only

## 非目標

以下內容不屬於這一階段：

- full session orchestration platform
- machine-authoritative closeout advisory system
- 讓 candidate 直接進 downstream consumer
- 用 session index 取代 canonical artifact
- 再長一套 closeout taxonomy

## 下一階段不該做的事

目前不應該因為還能延伸就持續擴：

- 不應把 `/wrap-up` 變成官方唯一入口
- 不應把 audit 長成第二套 authority
- 不應為了 completeness 焦慮而再加更多 closeout status
- 不應把 canonical closeout 直接接進更強的 runtime gate

## 下一階段該觀察的事

這條線下一步不是擴功能，而是觀察真實 session 分布是否支持目前語義。

建議追的指標：

- `canonical closeout valid rate`
- `warning_only / none` 的 session 比例
- audit flags 的穩定度
- 沒有 `/wrap-up` 的 session，canonical closeout 品質是否顯著下降

## 一句話結論

這條線已經把 closeout 從鬆散輸入，收斂成有 trust boundary 的 runtime surface。  
後續重點是 semantics observation，不是再擴權。
