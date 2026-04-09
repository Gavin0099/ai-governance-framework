# Session Closeout Artifact Schema：AI closeout candidate 的最小格式

> 版本：1.0  
> Artifact path：`artifacts/session-closeout.txt`  
> Written by：AI agent at end of session  
> Consumed by：`governance_tools/session_end_hook.py` via stop hook

---

## 目的

這份 artifact 是 AI agent 在 session 結束時提供給 governance runtime 的 **closeout input candidate**。  
它不是 truth source，而是候選輸入；真正 authoritative 的 verdict / trace artifact 仍由 governance runtime（`session_end_hook -> session_end`）產生。

換句話說：
- AI 可以寫 closeout candidate
- runtime 只把它當候選輸入
- canonical closeout 與 downstream artifact 由 system 產生

---

## 設計原則

每個欄位都應具備可解析、可缺省、可降級的特性。  
若某欄位不存在，應明確寫成 `NONE` 或 `NO_UPDATE`，而不是留給 parser 猜測。

## 最小欄位

建議至少包含：
- `task`
- `summary`
- `files_changed`
- `tests_run`
- `followups`
- `memory_candidate`

## 邊界

這份 schema 目前只做：
- 規範 AI closeout candidate 的最小格式
- 讓 stop hook / `session_end` 能穩定解析
- 讓 reviewer 知道 candidate 與 canonical artifact 的差別

這份 schema **不做**：
- 讓 AI candidate 直接變成 canonical verdict
- 取代 runtime 的 closeout validation
- 讓 missing field 自動推論為成功完成

## 一句總結

`session-closeout artifact schema` 的目的是讓 AI 在 session 結束時提供可解析的 closeout candidate，但真正可信的 closeout 結論仍由 runtime 產生。
