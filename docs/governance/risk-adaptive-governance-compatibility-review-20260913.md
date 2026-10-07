# RA0 — 風險調適治理相容性審查

現有 L0 / L1 / L2 已足以表達任務分類、升級與驗證強度。本次未證實「L0 fast-track 必然與 canonical memory 衝突」；可確認的是記憶交付條件與通用完成定義之間有適用範圍歧義。

建議保留既有分類，不啟動 L0 記憶豁免；只將記憶／收尾適用時點列為文字釐清候選。本文是 AI 文件分析，不是政策、待辦清單、人工批准或執行授權。

## 範圍與證據基準

- 審查日：2026-09-14（Asia/Taipei）；檔名依使用者指定保留 20260913。
- 授權：使用者「再來幫我分析」及附上的 RA0 規格，允許閱讀、比對、分類、保存指定報告後停止。
- 固定基準：`be5734cc8d1ba1a4f68f84e6752f08ff58488ecd`。下列治理來源與此 HEAD 無差異；不宣稱此刻遠端最新版。
- 核心來源：`governance/SYSTEM_PROMPT.md:333`、`governance/AGENT.md:21`、`governance/MEMORY_PROTOCOL.md:20`；補充來源見各列。行號均屬上述基準。
- 工作區原有 20 個 tracked dirty 路徑及 113 個 untracked 狀態項目；本次僅新增此報告，不納入其他修改，也不將 dirty 工具實作當成 canonical 行為證據。
- 先前審查交叉檢查：已查閱本地 review / knowledge 記錄，並以 L0、fast-track、risk-adaptive、exemption、豁免作限定搜尋，未找到直接對應項目；不推論整個歷史從未發生問題。
- DONE：完成三份核心文件的限定比對、矩陣、Q1–Q4、候選去留與來源引用，保存文件；不修改政策、runtime、writer、validator、hook、CI 或 consumer。

判定詞：KEEP＝保留已存在能力；AMEND＝文字值得釐清但未修改；CONFLICT＝無法同時遵守的規則；GAP＝必要能力缺失；NO_CHANGE＝沒有變更依據；INVARIANT＝不得因降級而放寬的正確性要求。NEEDS_EVIDENCE 僅表示證據不足，不是矩陣判定。

## 相容性矩陣

| Capability / Rule | Current Source | Current Behavior | Verdict | Needed Change |
|---|---|---|---|---|
| L0 classification | `governance/AGENT.md:50` §2.2 | 以全數符合的 allowlist 進入；排除 domain、I/O、schema、API 等變更，已限制 fast-track 濫用 | KEEP | 無 |
| L0 → L1 escalation | `governance/AGENT.md:27` §1、`:79` §2.2 | 行為、邊界、共享邏輯等變更升級，已涵蓋工作途中風險增加 | KEEP | 無 |
| L1 → L2 escalation | `governance/AGENT.md:28` §1、`:97` §2.4 | core domain、security、data integrity、flash、不可逆轉換升級 | KEEP | 無 |
| Classification uncertainty | `governance/AGENT.md:30` §1 | 不確定時向上升級，沒有向下猜測的空間 | KEEP | 無 |
| Repo baseline | `governance/AGENT.md:21`、`:25` §1 | 分類依實際工作性質；所查規則不足以支持只依 repo 名稱統一 L2 | NO_CHANGE | 不新增 repo 統一最低等級；既有特定路徑限制仍適用 |
| Verification scaling | `governance/TESTING.md:32`、`:50`、`:63` §2 | L0 輕量；L1 適用子集合；L2 強化 behavior、boundary、integration、regression 與驗收證據 | KEEP | 無；不得把 L1 子集合改成每項必跑 |
| Review scaling | `governance/REVIEW_CRITERIA.md:35` §0、`:125` §2.2、`:139` §2.3 | 審查綁定當前決策、差異及必要語意影響範圍；工程合併不等於整體 qualification | KEEP | 無；L0 輕量不免除會影響決策的問題 |
| L0 memory / closeout applicability | `governance/MEMORY_PROTOCOL.md:196` Delivery And Closeout Memory Protocol、`:328` Definition Of Done；`governance/AGENT.md:67` §2.2 | fast-track 僅免完整實作流程；memory 交付段有條件句，DoD 卻未重述條件 | AMEND | 見 M1：釐清何時適用，不推導或啟用 L0 豁免 |
| L1/L2 memory and writer contract | `governance/MEMORY_PROTOCOL.md:98` Canonical Memory Writer Rule、`:120`、`:198` | session-derived 使用同一 writer；可記真實測試證據或明確未驗證邊界，格式不要求另設 L1/L2 schema | KEEP | 無 schema 修改依據；實作相容性另需證據 |
| Durable memory signal | `governance/SYSTEM_PROMPT.md:337` §6.1 | 記錄 milestone、commit preparation/task close、決策及 gotcha；不要逐 micro-step 記錄 | KEEP | 保留內容價值篩選；不解讀成所有 L0 均可免記 |
| Task DONE versus session end | `AGENTS.md:233` Hard Stop、`:257` Session-End Closeout Responsibility | 任務完成不等於 session end；後者需明確生命週期事件或使用者要求，closeout 不授權 push | KEEP | 不在每次回覆後自動跑收尾 |
| Delivery controls | `governance/AGENT.md:149` §3、`:174` §4；`governance/REVIEW_CRITERIA.md:139` §2.3 | 交付前完成可本地執行的直接相關驗證；高風險需授權；合併、執行授權、結果接受分開 | KEEP | 語意可重用；六類交付邊界映射見 Q3，不新增 level |
| Tool subject correctness | `governance/REVIEW_CRITERIA.md:103` §2.1；`docs/governance/current-state-claim-verification-20260913.md:245` | 驗證結果必須對應所宣稱 subject；驗錯對象會使依賴證據失效 | INVARIANT | 不列入可選控制 |
| Commit / ref / artifact identity | `docs/governance/current-state-claim-verification-20260913.md:267`；`governance/MEMORY_PROTOCOL.md:341` | ref 先解析固定 OID；本地 memory 不等於遠端驗證，artifact 不得替換後沿用舊證據 | INVARIANT | 不因 L0 允許對象偷換 |
| Environment / tool identity | `docs/governance/current-state-claim-verification-20260913.md:258`；`governance/REVIEW_CRITERIA.md:159` | 執行證據受實際環境及依賴／資格假設限制 | INVARIANT | 遵守該工具既有 contract；不是新增所有工具一律相同的 pinning 制度 |
| Evidence claim ceiling | `governance/RESPONSE_ENVELOPE_CONTRACT.md:326` Claim Ceiling Preservation | 已完成、可宣稱、未宣稱各自保留，文件檢查不升格為 runtime 證明 | INVARIANT | 不因風險低而誇大證據 |
| New G0–G3 taxonomy | `governance/AGENT.md:25` §1、`:50` §2.2 | 既有 L0/L1/L2 已承載需要的分類能力 | NO_CHANGE | 不新增重複等級或 risk score |

## M1 — 記憶交付規則的適用範圍歧義

判定 AMEND；屬已存在的文字歧義。本項阻止直接採納「RA3 已有衝突證據」的推論，不阻止完成這份分析。處置僅為後續文字審查候選。

精確來源與現行文字：

1. `governance/AGENT.md:67`，§2.2：「只要 task 維持在這個 fast-track boundary 內，L0 **不需要**完整 `Analyze -> Define -> Test -> Implement` ceremony。」豁免受詞是該流程，沒有寫 canonical memory exemption。
2. `governance/SYSTEM_PROMPT.md:349`，§6.1：「不要為每個 micro-step 都更新 memory。只記錄 session restart 後仍有價值的 state change。」同節 `:343` 另列「Commit preparation / task close」更新；因此不能把 signal-rich 解讀成 L0 一律不記。
3. `governance/MEMORY_PROTOCOL.md:198`，Delivery And Closeout Memory Protocol：「Use a two-commit delivery sequence when a completed implementation needs canonical session memory:」。這是有條件的交付序列，但此處沒有明訂哪些 implementation 不需要。
4. `governance/MEMORY_PROTOCOL.md:330`，Definition Of Done：「A change is done when:」，接著 `:332` 要求 implementation validated and committed，`:333` 要求 canonical memory，`:335` 要求兩個 commits pushed，`:336` 要求遠端驗證。該段未明說僅適用上述交付條件。
5. `AGENTS.md:257`，Session-End Closeout Responsibility：「Task DONE is not session end.」同節 `:282`：「A closeout, including the manual fallback, does not authorize commit, push, pull request, or a new task; each still needs its own explicit authorization.」這已提供操作邊界，不能忽略。

理由：若把 memory DoD 當所有分析或微調任務的無條件完成定義，就會把任務完成、已授權交付、session end 混在一起；若按其交付章節與 workspace 邊界理解，則可以同時遵守。故目前證據支持「適用範圍歧義」，不支持「L0 fast-track 與 canonical memory 在邏輯上不能並存」。

最小候選方向：由負責人確認後，在 memory DoD 釐清其適用事件，引用既有 task/session-end 與交付授權邊界。不得順手加入 L0 例外、改 writer schema 或降低現有要求。本報告沒有起草生效條文。

## Q1 — 是否需要 Repo Baseline？

不需要新增。REPO_BASELINE = NOT_REQUIRED，意義是本次沒有新增統一 repo 風險下限的依據，不是否定已存在的路徑或領域限制。

依 `governance/AGENT.md:53` §2.2，README typo 在符合全部條件時可為 L0；一般行為變更升 L1；涉及 flash/security/data integrity 才依 `:28` 升 L2。「repo 是 CFU」本身不足以把 README typo 變成 L2。文件若改的是安全契約或資格宣稱，也不能只因副檔名是 Markdown 就當作 typo。

`governance/SYSTEM_PROMPT.md:316` §5 的 Legacy Refactor Baseline Validation 是既有系統變更前的驗證基準，與「整個 repo 最低 L2」是不同概念。

## Q2 — L0 memory exemption 是否是唯一明確 conflict？

不是：本次沒有證實這個前提，也不宣稱已找齊全框架所有衝突。RA3_CANDIDATE = NO，意義是依本次規格要求的「先確認衝突」條件，不啟動 RA3。

L0 的 allowlist 可用來辨識任務風險，不能直接充當 memory 豁免授權。免除完整實作 ceremony、少記 micro-step、交付時保留一份重要記錄，是可以同時成立的三件事。真正需要釐清的是 M1 的適用時點。

L1/L2 沿用同一 canonical writer 在文件契約上相容：`governance/MEMORY_PROTOCOL.md:120` 明確允許用 NOT RUN 或 NOT CLAIMED 加理由表達邊界。但這只是記錄格式，不能藉此免除 `governance/TESTING.md:63` 的 L2 必要證據。

證據狀態 NEEDS_EVIDENCE：未執行 writer/schema 測試、hook 追蹤或 consumer 成本量測，不能宣稱各級 runtime 已正確分流，也不能宣稱 canonical memory 是成本瓶頸。若未來主張要豁免，需另有實例、追溯需求與負責人政策決定；本次不建立該工作。

## Q3 — Delivery overlay 是否需要新 level？

不需要。NEW_LEVEL = NOT_REQUIRED，意義是既有風險、授權、驗證與資格決策可組合表達交付要求。以下為既有語意的分析映射，不是新 overlay 的啟用規則。

| 邊界 | 現有語意如何適用 | 尚不能宣稱 |
|---|---|---|
| Release | `governance/AGENT.md:149` 的交付前相關驗證；有實際高風險動作時適用 `:174` 的授權邊界 | 發行工具已 enforce，或每個 release 都一律 L2 |
| Signing | 真正使用簽署身分或改安全流程，按 `governance/AGENT.md:28` security 與 `:178` 高風險授權處理；修改說明文字另按任務性質 | 私鑰、簽署服務或成品驗證流程已實測 |
| Credential mutation | 安全狀態改動按 `governance/AGENT.md:28` 升級；未授權高風險依 `governance/SYSTEM_PROMPT.md:302` 停止 | 憑證輪替、撤銷或秘密處理已通過驗證 |
| Customer delivery | `governance/AGENT.md:149` 交付驗證；`governance/REVIEW_CRITERIA.md:141` 的工程通過不得升格為正式資格 | 客戶接受、寄送權限、交付完成或特定產品驗收已成立 |
| Production / irreversible state | 不可逆依 `governance/AGENT.md:28` 升 L2；正式環境實際動作需對應授權和環境證據 | 一般本地測試等於正式執行授權或安全證明 |
| Final qualification | `governance/REVIEW_CRITERIA.md:139` 明確分工程合併及資格；`:146` 分列執行授權與結果接受 | merge 即 qualification / GO，或既有 frozen 要求可被降級 |

三份核心文件沒有逐一列出六種操作的工具專屬流程，但「沒有每個關鍵字」不等於缺少治理語意。若要判斷某個簽署／交付工具是否真的錯放行，需要該工具 contract 與實際案例；標為 NEEDS_EVIDENCE，停止擴張。RA4 暫無已證實的語意不足可啟動。

## Q4 — 哪些要求不得隨 Level 降低？

可以縮放的是驗證工作量與審查深度；以下正確性要求不可縮放：

1. Subject：validator 所檢查對象必須就是宣稱通過的對象，不能把其他 branch 或 workspace 結果代入。
2. Identity：commit/ref/artifact 必須保持證據綁定；ref 可移動，因此固定 OID 的證據不能冒充 ref 後來的狀態。
3. Environment/tool：遵守該工具本來的版本、環境和執行契約；不同環境的成功不能無條件移植。
4. Claim ceiling：source/config 宣告不等於 runtime 行為，本地 commit 不等於遠端 push，工程驗證不等於 qualification。

來源為矩陣四項 INVARIANT。這些要求不表示每個 L0 都要執行所有工具；表示一旦使用結果作證據，對象與宣稱必須正確。本文未測任何 validator，因此不宣稱任何具體工具存在 subject-binding defect，也不復活 RA1。

## 候選去留，沒有建立實作任務

| 候選 | 本次處置 | 理由 |
|---|---|---|
| RA-B0 成本量測 | 僅保留觀測候選，未授權或建立任務 | 文件比較不能回答耗時、token 或淨效益；若要談降成本，需獨立實測 |
| RA3 L0 canonical-memory exemption | 不啟動 | 規格要求的衝突證據未成立；M1 不等於豁免需求 |
| RA4 delivery clarification | 暫不啟動 | 現有語意可表達；需要具體未涵蓋操作才有新增釐清依據 |
| RA2 新 routing | 建議取消重複部分 | 已有分類、升級與驗證分級；本報告沒有更動任何正式任務狀態 |
| RA1 原 pre-push subject-binding fix | 依輸入維持 invalidated，不重新開啟 | 本次沒有新的 runtime 缺陷證據；並未重驗原案歷史 |
| M1 記憶適用條件 | 唯一文字釐清候選，待審閱 | 有具體條件句與通用 DoD 用語差異；不是新增 gate 或 level 的理由 |

## 完成範圍與未宣稱事項

已完成三份核心文件限定核對、17 列矩陣、M1 精確來源與理由、Q1–Q4、控制分離及候選去留，並保存此報告。沒有 CONFLICT/GAP 判定；不為湊足清單而增加問題。

本文件是未提交的審查成果。工作區原有修改不屬 RA0，未審查或排除其整體影響；不宣稱 repo 整體 DONE、工作區乾淨、已 commit/push、已合併或已完成 session closeout。

Claim ceiling：Risk-adaptive governance compatibility has been reviewed against the canonical governance documents at the named commit.

未宣稱 risk-adaptive runtime 已實作、L0 memory exemption 已啟用、consumer 成本已下降、delivery overlay 已生效、framework ROI 提高、G4／正式資格或人工認證。

下一步建議：審閱 M1 的適用時點判斷；若接受，再另行授權最小文字釐清。本次止於報告，不建立 implementation task。

## 驗證與完整回報資料

文件檢查：17 列矩陣、Q1–Q4 與候選項目完整；來源行號存在且非空白；以 `git diff --no-index --check -- NUL docs/governance/risk-adaptive-governance-compatibility-review-20260913.md` 檢查格式。這些結構檢查不等於人工語意審查。

記憶工作流程檢查：`python -X utf8 -m governance_tools.memory_workflow --check --repo . --changed-file docs/governance/risk-adaptive-governance-compatibility-review-20260913.md --task-text "RA0 read-only analysis of memory policy; documentation report only; no memory writes" --format json` 回傳可完成本範圍、沒有 blockers，不要求 canonical writer；沒有執行 memory authority guard，也沒有驗證既有 dirty memory。

以下保留機器回報資料。mode / mode_source 指本次檢查事件；task_authority 是本次使用者授權；scope、done、claim_ceiling、not_claimed 分別是工作範圍、已完成、宣稱上限、未宣稱事項；evidence_refs、risk、next_action 分別保留證據、限制、建議下一步。

```json
{
  "mode": "VALIDATION",
  "mode_source": "validation_command",
  "task": "RA0 compatibility review, 2026-09-14",
  "task_authority": "user_request",
  "scope": ["docs/governance/risk-adaptive-governance-compatibility-review-20260913.md"],
  "done": ["Scoped document comparison and 17-row matrix saved locally", "Q1-Q4 and candidate dispositions documented", "Report remains uncommitted; overall workspace is not DONE"],
  "claim_ceiling": ["Document compatibility analysis at be5734cc8d1ba1a4f68f84e6752f08ff58488ecd only"],
  "not_claimed": ["Runtime or writer-schema execution correctness", "L0 exemption or delivery overlay activated", "Cost reduction, ROI, G4 or qualification", "Human review or certification", "Commit, push, merge, clean workspace or session closeout"],
  "evidence_refs": [
    {"source": "Source sections and quotations in matrix and M1", "result": "AI document comparison"},
    {"command": "git diff --no-index --check -- NUL docs/governance/risk-adaptive-governance-compatibility-review-20260913.md", "result": "PASS"},
    {"command": "Scoped memory_workflow --check command printed above", "result": "PASS; no blockers; guard_ran=false"},
    {"source": "In-session Python matrix and nonblank source-line checks", "result": "PASS; structural checks only"}
  ],
  "risk": ["Pre-existing dirty work excluded from inspection and mutation", "Memory applicability wording remains ambiguous", "Runtime evidence and consumer cost measurements unavailable in this scope"],
  "next_action": "Review M1 applicability interpretation; any policy amendment requires a separately authorized scope."
}
```
