# 快取感知回執對齊說明 - 2026-06-28

狀態（Status）：`PENDING`
範圍（Scope）：docs-only receipt alignment and index note
執行環境行為（runtime behavior）變更：否
測試行為（test behavior）變更：否
提示快取實作（prompt cache implementation）：否
強制執行（enforcement）變更：否

## 目的

這份文件整理快取感知（cache-aware）文件裡提出的候選回執（receipt），
並把它們對齊到既有權威文件。

本文件只做對齊、索引與衝突提醒，不建立新的權威順位。

## 向上引用的權威

本文件不得自行定義頂層權威順位。遇到衝突時，依下列既有來源判斷：

| 來源 | 本文件如何使用 |
| --- | --- |
| `governance/AUTHORITY.md` | 判斷 canonical / reference / derived 的權威層級與衝突處理。 |
| `PLAN.md` 的 Active Claim Boundaries | 判斷目前可宣稱的上限；若本文件與 `PLAN.md` 衝突，`PLAN.md` 勝出。 |
| `docs/REVIEWER_ENTRYPOINT.md` | 作為 reviewer 的入口索引；其宣稱仍受 `PLAN.md` 限制。 |
| `governance/RESPONSE_ENVELOPE_CONTRACT.md` | 作為 final response / closeout 報告格式的 reference convention。 |
| `governance/MEMORY_PROTOCOL.md` | 作為記憶寫入、標準寫入器與記憶證據語意的 canonical protocol。 |
| `governance/PHASE_D_CLOSE_AUTHORITY.md` | 作為 Phase D closeout 權威事件與 reviewer closeout artifact 的 canonical source。 |

本文件不能覆蓋上述來源，也不能把候選回執升格成已採用合約。

## 狀態分類

| 狀態 | 意義 |
| --- | --- |
| `adopted-contract` | 已由既有 governance 文件定義，且可在其原本範圍內被引用。 |
| `candidate/PENDING` | 文件提出的候選欄位或慣例；尚未成為 runtime schema、tool output 或 repo contract。 |

若某個表面是摘要、包裝或 handoff，應在對齊邊界中標為 derived。
`derived` 不是第三種採用狀態；它只表示該表面不能取代原始權威或原始回執。

## 回執狀態表

| 回執或表面 | 狀態 | 來源 | 對齊邊界 |
| --- | --- | --- | --- |
| response envelope | `adopted-contract` / reference | `governance/RESPONSE_ENVELOPE_CONTRACT.md` | 規範 result-first reporting；不改 runtime gate 或 evidence admissibility。 |
| memory record | `adopted-contract` / canonical workflow | `governance/MEMORY_PROTOCOL.md` | 標準寫入器建立 provenance 與 placement；不證明內容真實、已接受或已 push。 |
| closeout receipt / reviewer closeout artifact | `adopted-contract` where governed by existing closeout authority | `governance/PHASE_D_CLOSE_AUTHORITY.md` and closeout tooling docs | 可作 closeout chain 的 evidence；不得被 candidate receipt 取代。 |
| `REVIEW_RECEIPT` | `candidate/PENDING` convention | cache-aware specs and operator playbook usage | 只能承載 reviewer scope、findings、claim ceiling；不能授權 push、memory write、cross-repo write 或 closeout authority。 |
| `CACHE_AWARE_SURFACE_RECEIPT v0.1` | `candidate/PENDING` | `docs/governance/cache-aware-governance-surface-spec-2026-06-28.md` | 只能輔助描述 stable prefix / dynamic tail 表面；不證明 harness 已實作 prompt cache。 |
| `AUTHORITY_MANIFEST v1` | `candidate/PENDING` | `docs/governance/cache-aware-authority-manifest-invalidation-spec-2026-06-28.md` | 描述候選權威清單；不能取代 `governance/AUTHORITY.md`。 |
| `MODE_STATE_RECEIPT v0.1` | `candidate/PENDING` | `docs/governance/cache-aware-mode-authorization-anti-forgery-spec-2026-06-28.md` | 描述候選 mode state；自然語言 mode request 不能自動變成 machine-accepted state。 |
| `PUSH_AUTHORIZATION_RECEIPT v0.1` | `candidate/PENDING` | `docs/governance/cache-aware-mode-authorization-anti-forgery-spec-2026-06-28.md` | 只能描述特定 push 授權；不能由 `REVIEW_RECEIPT` 自行產生。 |
| `MEMORY_WRITE_AUTHORIZATION_RECEIPT v0.1` | `candidate/PENDING` | `docs/governance/cache-aware-mode-authorization-anti-forgery-spec-2026-06-28.md` | 不取代 `governance/MEMORY_PROTOCOL.md` 或 `governance_tools.memory_record`。 |
| `CROSS_REPO_WRITE_AUTHORIZATION_RECEIPT v0.1` | `candidate/PENDING` | `docs/governance/cache-aware-mode-authorization-anti-forgery-spec-2026-06-28.md` | 防止把 writable workspace 誤讀成 cross-repo write authorization；不授權跨 repo 寫入。 |
| `TOOL_DENIAL_RECEIPT v0.1` | `candidate/PENDING` | `docs/governance/cache-aware-tool-denial-receipt-spec-2026-06-28.md` | 記錄工具被拒絕；不授權 retry，也不證明 tool denial 已被 machine-enforced。 |
| `CACHE_AWARE_COMPACTION_SUMMARY v0.1` | `candidate/PENDING` | `docs/governance/cache-aware-compaction-summary-field-spec-2026-06-28.md` | 若被產生，仍是 derived summary；只能摘要 authority、evidence、dirty state 與 receipt references，不能取代原始來源。 |
| `CACHE_AWARE_HARNESS_HANDOFF_PACKET v0.1` | `candidate/PENDING` | `docs/governance/cache-aware-harness-handoff-checklist-2026-06-28.md` | 若被產生，仍是 derived handoff；不證明外部 harness 採用或 prompt cache enforcement 存在。 |

## 關係規則

候選回執可以引用已採用合約，但不能覆蓋已採用合約。

`REVIEW_RECEIPT` 可以提供 skeptical evidence，例如 blocking findings、required fixes、claim ceiling 與 push gate recommendation。
它不能直接授權 push、memory write、cross-repo write、closeout acceptance 或 runtime policy change。

授權類候選回執若未由外部框架或明確工具產生，只能視為 proposed shape。
使用者自然語言可以是工作授權來源，但不能自動被重寫成 machine-accepted authorization receipt。

`TOOL_DENIAL_RECEIPT` 表示拒絕或阻擋事件。它不是 retry token，也不是授權替代品。

壓縮摘要與 handoff packet 都是 derived surface。
若它們與原始文件、原始 receipt、`PLAN.md` 或 `governance/` 權威來源衝突，必須回讀原始來源。

## 衝突處理

| 衝突 | 處理 |
| --- | --- |
| candidate cache-aware receipt vs `governance/AUTHORITY.md` | `governance/AUTHORITY.md` 勝出。 |
| candidate claim vs `PLAN.md` Active Claim Boundaries | `PLAN.md` 勝出。 |
| compaction summary vs original receipt | 原始 receipt 或原始 artifact 勝出；摘要需更正。 |
| `REVIEW_RECEIPT` approval vs missing user push authorization | 不得 push；review approval 不是 push authorization。 |
| memory authorization candidate vs `governance/MEMORY_PROTOCOL.md` | `governance/MEMORY_PROTOCOL.md` 與標準寫入器要求勝出。 |
| tool visible vs tool executable | 可見不等於可執行；權限閘門或 repo 規則仍可拒絕。 |
| external harness evidence vs repo-local non-claim | 只能宣稱 harness 提供的 evidence；repo 本身不因此宣稱 runtime enforcement。 |

## 快取感知文件索引

目前快取感知文件仍是 `PENDING` docs-only 設計面，不是 runtime implementation。

建議閱讀順序：

1. `docs/governance/cache-aware-agent-harness-design-note-2026-06-27.md`
2. `docs/governance/cache-aware-governance-surface-spec-2026-06-28.md`
3. `docs/governance/cache-aware-authority-manifest-invalidation-spec-2026-06-28.md`
4. `docs/governance/cache-aware-mode-authorization-anti-forgery-spec-2026-06-28.md`
5. `docs/governance/cache-aware-tool-denial-receipt-spec-2026-06-28.md`
6. `docs/governance/cache-aware-compaction-summary-field-spec-2026-06-28.md`
7. `docs/governance/cache-aware-harness-handoff-checklist-2026-06-28.md`
8. 本文件：receipt alignment and index note

本文件同時承擔 receipt alignment、索引與短期 roadmap 的角色。
除非出現新的實作 evidence 或審查要求，不應再新增一份獨立 index / roadmap meta-doc。

## 後續 roadmap

建議下一步若要整理 operator workflow，優先擴充既有
`docs/governance/operator-prompt-playbook-2026-06-26.md`，
不要新增另一份 operator checklist。

實作層若要開始，應先準備獨立 review packet，並明確分出：

- schema 是否新增；
- runtime gate 是否新增；
- `AUTHORITY_MANIFEST v1` 是否由工具產生；
- authorization receipt 是否由 harness 產生；
- compaction summary 是否由工具產生；
- prompt cache hit / miss 是否有 provider 或 harness evidence；
- 哪些 claim 仍受 non-bypassability gap 限制。

這些屬於較重要的治理落地審查，應交給 Claude / human reviewer 或等效高嚴格度 review。

## 不做的事

本文件不做以下事項：

- 不新增 runtime hook；
- 不新增或修改 tests；
- 不修改 `PLAN.md`；
- 不新增 artifacts；
- 不修改 `governance_tools/`；
- 不定義新 schema；
- 不宣稱 prompt cache 已實作；
- 不宣稱 tool denial 已被 machine-enforced；
- 不宣稱外部 harness 已採用本 repo 的候選規格；
- 不建立平行 authority map。

## 宣稱上限

本文件只能宣稱：

- 目前 cache-aware docs 中的候選 receipt 已被整理成一份 alignment / index note；
- 候選 receipt 與既有 adopted / canonical receipt surfaces 的引用邊界已被明列；
- `REVIEW_RECEIPT` 被標為 candidate convention，而非 formal contract；
- index / roadmap 已併入本文件以降低 meta-doc sprawl。

本文件不能宣稱：

- 任何候選 receipt 已被 runtime 實作；
- prompt cache 已被本 repo 或外部 harness enforcement；
- push、memory write 或 cross-repo write 可由 reviewer 自動授權；
- closeout authority 可由 candidate receipt 取代；
- 本 repo 已具備 cache-aware harness。
