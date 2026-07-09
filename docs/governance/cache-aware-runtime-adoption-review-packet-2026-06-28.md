# 快取感知 Runtime Adoption Review Packet - 2026-06-28
> Consolidation pointer: this source note is covered by
> `docs/governance/cache-aware-round-b-summary.md`.
> Pointer only; this note is not removed, archived, invalidated, or
> reclassified.


狀態（Status）：`PENDING`
範圍（Scope）：docs-only implementation readiness review packet
執行環境行為（runtime behavior）變更：否
工具行為（tooling behavior）變更：否
測試行為（test behavior）變更：否
強制執行（enforcement）變更：否
提示快取實作（prompt cache implementation）：否

## 問題

快取感知（cache-aware）文件已經完成設計面、回執對齊與操作者日常規則。
下一步若直接進入 schema、runtime、tooling 或外部 harness 整合，容易把
「repo 可以描述的治理訊號」誤讀成「repo 可以實作 prompt cache runtime」。

這份 packet 的用途是把落地層切清楚，讓 reviewer 可以做 go / no-go 判斷。
它不是第 N 份候選行為規格，也不是新的 authority map。

## 一開始必須切開的三類

| 類別 | 含意 | 目前判斷 |
| --- | --- | --- |
| HARNESS-only | 只能由外部代理框架或模型供應商提供 | prompt cache 本體、cache hit/miss 監控、compaction 控制、deferred tool loading、mode-as-tool-call 機制 |
| REPO-feasible | 本 repo 可以用文件、工具或測試產生可稽核訊號 | `AUTHORITY_MANIFEST v1` 產生器、權威變更失效訊號、candidate receipt tooling、surface 分層與 evidence packet |
| ENFORCEMENT-limited | repo 可做 detection / accountability，但不是 prevention-grade | receipt、report、validator、CI 或 hook 訊號仍受 audit-not-prevention 邊界限制 |

任何後續 review 若把 HARNESS-only 項目列成本 repo 的直接 backlog，應要求降級或重切範圍。

## 目前儲存庫事實

已讀取並用作本 packet 依據的現有表面：

- `PLAN.md` Active Claim Boundaries：反覆限定 detection / accountability，不把文件或 catalog 升格成 enforcement。
- `governance/AUTHORITY.md`：定義 `canonical > reference > derived`；derived surface 不能創造 authority。
- `docs/governance/cache-aware-agent-harness-design-note-2026-06-27.md`：提出快取感知 agent harness 的設計背景。
- `docs/governance/cache-aware-governance-surface-spec-2026-06-28.md`：分出 stable prefix / dynamic tail / ignored surfaces。
- `docs/governance/cache-aware-authority-manifest-invalidation-spec-2026-06-28.md`：定義候選 `AUTHORITY_MANIFEST v1` 與 invalidation matrix。
- `docs/governance/cache-aware-mode-authorization-anti-forgery-spec-2026-06-28.md`：定義 mode / authorization receipts 的候選欄位。
- `docs/governance/cache-aware-tool-denial-receipt-spec-2026-06-28.md`：定義候選 `TOOL_DENIAL_RECEIPT v0.1`。
- `docs/governance/cache-aware-compaction-summary-field-spec-2026-06-28.md`：定義候選 compaction summary 欄位。
- `docs/governance/cache-aware-round-b-summary.md`：保留外部 harness adoption
  evidence gap 與 deferred handoff boundary 的 surviving summary。
- `docs/governance/cache-aware-receipt-alignment-note-2026-06-28.md`：標明 cache-aware receipts 多數仍是 `candidate/PENDING`。
- `docs/governance/operator-prompt-playbook-2026-06-26.md`：把 cache-aware receipt alignment 收斂成日常操作規則。

窄範圍搜尋結果：

- repo 內沒有既有 `cache-aware runtime adoption review packet`；
- repo 內沒有已實作的 prompt cache hit/miss monitor；
- repo 內沒有已產生的 `AUTHORITY_MANIFEST v1` artifact；
- repo 內沒有 runtime-emitted mode/auth/tool-denial/compaction receipts。

因此，本 packet 填的是 implementation readiness gap，不是 duplicate spec。

## 目標結果

產生一份可供 Claude / human reviewer 或等效高嚴格度 reviewer 審查的落地前 packet，回答：

- 哪些項目 repo 做不到，必須保持 HARNESS-only；
- 哪些項目 repo 可以先做，且可用 focused tests 驗證；
- 哪些項目即使落地，也只能宣稱 detection / accountability；
- 若要開始實作，最小且最值得做的第一個子集是什麼。

## 範圍

本 packet 涵蓋：

- cache-aware runtime adoption 的 go / no-go 問題；
- `AUTHORITY_MANIFEST v1` 產生器可行性；
- authority-change invalidation signal 可行性；
- mode/auth/tool denial/compaction receipts 的現實邊界；
- prompt cache hit/miss monitoring 的 harness-only 邊界；
- future implementation tranche 的 evidence plan。

## 非目標

本 packet 不做以下事項：

- 不修改 runtime；
- 不修改 tests；
- 不修改 `PLAN.md`；
- 不新增 artifacts；
- 不修改 `governance_tools/`；
- 不新增 schema；
- 不實作 prompt cache；
- 不監控 cache hit rate；
- 不新增任何 receipt writer；
- 不新增 enforcement；
- 不宣稱外部 harness 已採用 cache-aware specs。

## 受影響表面

本 docs-only packet 直接影響：

- `docs/governance/cache-aware-runtime-adoption-review-packet-2026-06-28.md`

若未來進入實作，可能影響的候選表面必須另案確認：

- `governance_tools/**`
- `runtime_hooks/**`
- `schemas/**`
- `tests/**`
- `docs/governance/cache-aware-*.md`

本 packet 不授權修改上述候選實作表面。

## 落地項目與現實宣稱上限

| 項目 | 類別 | 可行下一步 | 現實 claim ceiling |
| --- | --- | --- | --- |
| prompt cache 本體 | HARNESS-only | 不在本 repo 實作 | NOT CLAIMED |
| cache hit/miss 監控 | HARNESS-only | 只接受 harness/provider evidence | repo NOT CLAIMED; harness/provider may report separately |
| compaction 控制 | HARNESS-only | repo 可定義保留欄位；不可控制 harness 壓縮 | detection/accountability only |
| deferred tool loading | HARNESS-only | repo 可記錄需求；不可控制 tool schema loading | NOT CLAIMED |
| mode-as-tool-call | HARNESS-only | repo 可定義 desired receipt shape；不可保證 harness mode switch | detection/accountability only |
| `AUTHORITY_MANIFEST v1` 產生器 | REPO-feasible | 可做 CLI 產生 path/hash/base-ref/loaded_as | detection/accountability only |
| authority-change invalidation signal | REPO-feasible | 可比較 manifest hash / authority file hash | detection/accountability only |
| mode/auth receipts | REPO-feasible but harness-dependent | 可先做 schema/proposed validator；真 receipt 仍需 harness issuer | detection/accountability only |
| `TOOL_DENIAL_RECEIPT v0.1` | REPO-feasible but harness-dependent | 可定義 validator 或 fixture；真 denial 仍需 permission layer | detection/accountability only |
| compaction summary fields | REPO-feasible but harness-dependent | 可做 validator/fixture；真 compaction 仍需 harness | detection/accountability only |
| cache miss classification | REPO-feasible as report taxonomy | 可分類 known triggers；不能測 provider cache key | detection/accountability only |

## 最小可實作子集建議

如果 reviewer 同意從 docs 進入 implementation，第一個 repo-side 子集應該是：

```text
AUTHORITY_MANIFEST generator + authority-change invalidation signal
```

理由：

- 它是 REPO-feasible，不需要外部 prompt cache provider；
- 它可用 deterministic file/path/hash/base-ref 測試；
- 它直接支撐 stable prefix / dynamic tail 的治理前提；
- 它能把 authority change 轉成 visible signal，但不假裝 prevention；
- 它不需要先實作 mode/auth receipts、tool denial receipts 或 compaction tooling。

第一個實作 tranche 的建議輸出只應是：

- 一個只讀 CLI 或 module，輸出 `AUTHORITY_MANIFEST v1` candidate artifact；
- focused tests 驗證 path selection、hash stability、base_ref/head fields、dynamic fields 不污染 stable source refs；
- 一個 invalidation comparison helper 或 report，指出 authority source changed / unchanged；
- docs update 明確保留 `repo_enforces_prompt_cache: false`。

## 暫緩項目

下列項目應維持 `PENDING`，直到 `AUTHORITY_MANIFEST` 子集有 reviewer-approved evidence：

- `MODE_STATE_RECEIPT v0.1` tooling；
- `PUSH_AUTHORIZATION_RECEIPT v0.1` tooling；
- `MEMORY_WRITE_AUTHORIZATION_RECEIPT v0.1` tooling；
- `CROSS_REPO_WRITE_AUTHORIZATION_RECEIPT v0.1` tooling；
- `TOOL_DENIAL_RECEIPT v0.1` tooling；
- `CACHE_AWARE_COMPACTION_SUMMARY v0.1` tooling；
- `CACHE_AWARE_HARNESS_HANDOFF_PACKET v0.1` tooling；
- cache miss monitoring；
- any runtime gate or enforcement path。

## 邊界與 API 考量

`AUTHORITY_MANIFEST` 若實作，應保持只讀、deterministic、repo-local：

- input: project root, base ref, head ref, optional mode；
- output: structured manifest to stdout or explicit output path；
- no implicit artifact writes；
- no ledger append；
- no runtime hook side effect；
- no push / memory / cross-repo authorization；
- generated time belongs to dynamic tail, not stable prefix hash。

任何 receipt tooling 若未來實作，必須明確區分：

- issuer：誰產生 receipt；
- authority source：receipt 依據哪個 canonical/reference source；
- scope：receipt 適用的 repo、commit、mode 或 action；
- claim ceiling：detection / accountability，不是 prevention；
- invalidation：receipt 何時失效；
- non-claim：不得替代 user authorization 或 main-thread gate。

## Failure Paths / Risk Points

- 把 HARNESS-only 項目列成本 repo backlog，會製造無法實作的假承諾。
- 把 `AUTHORITY_MANIFEST` 誤讀成 prompt cache enforcement，會造成 claim inflation。
- 把 receipt writer 誤當 permission gate，會把 detection 說成 prevention。
- 把 `REVIEW_RECEIPT` 或 sub-agent approval 誤當 push authorization，會破壞主執行緒 gate。
- 把 compaction summary 當原始 evidence，會丟失 authority、dirty-tree、not_claimed 與 authorization state。
- 把 cache miss 分類用來責備 safety/freshness miss，會鼓勵沿用過期權威。
- 在 `.tmp_codex_closeout_bypass_tests/` residual 未明確處理前，仍不得宣稱 workspace clean。

## Evidence Plan

本 docs-only packet 的驗證：

- `git diff --check -- docs/governance/cache-aware-runtime-adoption-review-packet-2026-06-28.md`
- scope check：只有本 packet 新增；
- overclaim scan：不得出現「已實作 prompt cache」、「已監控 cache hit rate」、「已新增 enforcement」等正向宣稱；
- sub-agent read-only review：檢查 HARNESS-only / REPO-feasible / ENFORCEMENT-limited 是否清楚；
- commit only after review approval。

未來 `AUTHORITY_MANIFEST` 子集若被核准，最低 evidence 應包含：

- focused unit tests for manifest field presence and stable hashing；
- fixture test showing authority file content change changes manifest hash；
- fixture test showing `generated_at` does not alter stable source hash；
- CLI smoke with explicit `--project-root` and `--format json`；
- claim-ceiling doc update stating detection/accountability only。

## Implementation Tranche Recommendation

Recommended next action after this packet review:

```text
needs high-rigor review before implementation
```

若 reviewer 批准 implementation，唯一建議進入的 first tranche 是：

```text
Implement AUTHORITY_MANIFEST generator + authority-change invalidation signal.
```

其餘項目維持 `PENDING`，直到第一個 repo-feasible tranche 有 evidence。

## 宣稱上限

本 packet 只能宣稱：

- cache-aware docs 階段已收斂到 implementation readiness review；
- HARNESS-only / REPO-feasible / ENFORCEMENT-limited 三類邊界已明列；
- 每個落地項的現實 claim ceiling 已標為 detection/accountability 或 NOT CLAIMED；
- 最小可實作子集建議是 `AUTHORITY_MANIFEST` 產生器加 authority-change invalidation signal。

本 packet 不能宣稱：

- prompt cache 已實作；
- cache hit/miss 已可監控；
- runtime gate 已新增；
- receipt schema 已正式存在於執行環境；
- permission denial 已被 machine-enforced；
- compaction 已由 repo 控制；
- 外部 harness 已採用本組 cache-aware specs；
- workspace clean。
