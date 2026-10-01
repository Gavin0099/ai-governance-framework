# M3-b-2A — single-work-item adoption review

結果：工程交付與 legacy claim 退位的解讀有證據支持；正式採納保持 candidate，未 mutation。
判定：ESCALATED（採納權限／資格仍待確認），不是程式錯誤或重新 qualification。
風險：Low for this isolated review；不得把候選資格當作正式 current authority。

## Frozen decision boundary

- Owner 指定只審查 M3-b-2A；五項條件成立才 mutation，缺項維持 candidate 並停止。
- DONE：核對五項條件，交付只針對該 work item 的 exact patch 與保存證據。
- 所有新 artifact 僅在本目錄；正式 `memory/01_active_task.md`、PLAN、review log、writer、R1 均未修改。
- 已授權的是限定採納審查。沒有將 broader agreement 或樣本可讀性當作 exact current-authority attestation。

## Five conditions

| 條件 | 結論 | 證據 / 界線 |
|---|---|---|
| 1. PR #108 / merge 支持 MERGED | 成立 | 此輪 GitHub PR state=MERGED；merge=`a59b0aef93753630f9949233d03be555bad165c5`；mergedAt=`2026-08-24T10:59:42Z`；merge 是本次 live main=`7dd78070e6ea462fe218837832026d53b9120db8` 的 ancestor。見 pr108.json、main-head.json、manifest.json。 |
| 2. 舊 uncommitted 指涉同一 work item | 成立，為 evidence-backed derived interpretation | exact legacy L61–64 的 291-test receipt / 六檔敘述與 PR #108 中 checkpoint 對應。committed-prior-analysis.md L105–138 已分析相同 referent；本輪 receipt.json 與 PR file list corroborate。這不是宣稱 dirty checkout 的所有 local diff 已提交。 |
| 3. 更晚 qualified evidence 是否改變此答案 | 在宣告範圍內未發現 | 截至本次 live main，六個實作／測試檔與 PR #108 merge bytes 一致；後續 7d750039 / PR #109 記錄 merged，6d38a254 的已提交分析亦將此 checkpoint 的 uncommitted 視為過時。只核對工程 merge fact 與此 implementation checkpoint，不聲稱全 repo、私有對話或其他未讀分支沒有新工作。 |
| 4. Reviewer 能把 exact candidate 判成 current | 尚未成立 | 本 agent 有 owner 指定的限定技術審查 scope，但沒有可追溯來源證明本輪 exact patch 已取得 authority-qualified current-adoption review。不能由 candidate 作者自己填 qualified / reviewed，不能沿用 Slice 2 模擬 R1 authority 或 fresh-agent 可讀性結果。 |
| 5. Owner 僅此 work-item 的修改授權 | 審查授權成立；正式 mutation 条件未滿 | 本輪指令明確限定 work item 與「全部成立才 mutation」；第 4 項未成立，因此任何條件式 mutation 權限尚不能生效。沒有要求重複授權已允許的查證，也沒有擴成整份 active-task 整理。 |

採納 disposition：`reviewer_required`（需要具來源的採納審查）；不是將 merged 事實降回未知。

## Six-field information candidate

| 欄位 | 此輪候選答案 |
|---|---|
| Objective | M3-b-2A bounded in-process transport checkpoint 的工程交付，已合併 |
| Blocker | 工程 merge 沒有待合併 blocker；其他 current blockers UNKNOWN |
| Delivery status | MERGED：PR #108 / a59b0aef；只限工程 checkpoint |
| Next action | 本 tranche 完成採納審查後停止；M3-b-2B / Gate 3 / 其他工作不獲新權限 |
| Evidence pointers | pr108.json、main-head.json、receipt.json、committed-prior-analysis.md L105–138、committed-plan.md L2597–2602、pre-adoption-active-task.md L61–64 / L139 |
| Qualification status | Candidate、尚未正式 current adoption；工程 merge 不能推論 production activation / Gate 3 qualification |

## Exact proposed mutation — not applied

`proposed-change.patch` 只將正式入口舊 L61–64 的 legacy paragraph 換成一行 historical pointer，明確指向既有 PR #108 engineering checkpoint。
沒有改動原 L139 的 canonical projection、其 identity 或內容。沒有建立假的 R1 predecessor，沒有改動其他 work item。

完整原始 working-tree bytes 保存為 `pre-adoption-active-task.md`，不是只保留摘要。SHA 見 manifest。
範圍外 prefix / suffix 原始 bytes 不變，candidate 由 147 行 / 11731 字元變成 144 行 / 11664 字元；兩者仍是 CRITICAL，不宣稱 recovery 或 memory 健康改善。
`proposed-active-task.md` 只是 patch 效果樣本，不是已採納檔案。

## Findings / current-decision impact

1. WARNING — 未建立 exact candidate 的採納 reviewer authority
   - Source / location：`governance/MEMORY_SURFACE_AUTHORITY_CONTRACT.md:108`；Slice 3 `adoption-plan.md:50`；本表第 4 項。
   - Attribution：exposed（此輪從資訊候選進正式採納時顯現），不是此輪引入的程式 defect。
   - Current-decision impact：yes for formal current adoption；no for recording this evidence-backed candidate review。
   - Status：open；Disposition：保持 candidate，交付 exact patch 給 authority-qualified reviewer / owner；不加新 gate 或修改 qualification 規則。

這個 finding 不否定第 1–3 項，也不能透過 PR #108 的工程 review 回溯授予本輪 projection 採納資格。

## Review inputs checked

- `governance/REVIEW_CRITERIA.md`、`governance/MEMORY_SURFACE_AUTHORITY_CONTRACT.md`、`governance/MEMORY_PROTOCOL.md`、`governance/AUTHORITY.md`、`governance/MEMORY_AUTHORITY_CONTRACT.md`。
- 指定範圍的 `memory/01_active_task.md`、PLAN、`memory/04_review_log.md`、`memory/03_knowledge_base.md`；未分析其他 dirty work。
- 已提交的 `docs/governance/current-state-claim-verification-20260913.md` 中此 referent 的分析。
- 本次 live PR / main metadata、merge ancestry、六檔 byte comparison；沒有重跑 tests、delivery qualification 或 consumer / native execution。
- Architecture：沿用 evidence / interpretation / authorization 三層；無新 API、schema、writer、R1、Hook 或 gate。
- Native / thread safety：N/A；沒有執行產品程式。
- Knowledge-base alignment：保留歷史與現行範圍分開；不存在因來源記錄為 canonical 就升級成 truth 的處置。
- Workspace：既有 dirty work 保持，無 clean delivery、commit、push 宣稱。

## Next action

只對本目錄 `proposed-change.patch` 與 `proposed-active-task.md` 的 exact identity 取得 current-adoption reviewer authority / 接受結論；在此之前維持 candidate 並 STOP。
已允許的單項審查已完成，不重新設計 Memory 或整理其他 work item。
