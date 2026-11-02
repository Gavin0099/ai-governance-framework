# AI Governance — Agent 自主交付與治理效益驗收計畫 v2

**日期：** 2026-11-02（Asia/Taipei）  
**狀態：** Owner 已確認規劃方向；**Docs-only Draft Proposal，尚非正式治理權威或執行授權**  
**公開內容限制：** 只使用「Internal Consumer」指稱非公開專案，不揭露內部位置、組織、客戶、產品或任務細節。

> **唯一要回答的問題：AI Governance 能不能讓 Agent 更少需要人工救援、更可靠地完成工程工作，且增加的 Token、時間與人工負擔值得？**
>
> **兩個產品目標必須分開驗收：** (1) AI 自主完成一項真實工程任務；(2) Governance 相對於 Baseline／Rules Only 是否提供可觀察的淨效益。成功 HOLD 只證明拒絕行為，不算產品完成。

## 0. Agent 交接入口：先讀這裡，別重做完成的工作

這是供後續 Agent 查閱的**計畫與驗收索引**，不是新的 Policy、Gate、Hook、常駐 Loop 或自動授權來源。**只開 Draft PR 不會讓每個 Agent 自動讀到文件**；後續任務的交接訊息需明確附上本文件路徑／PR 連結。每次執行前重新核對遠端 PR HEAD、CI、Owner 授權與 Consumer 實際狀態，不得把本文件的歷史快照當作最新事實。

- **已做過、勿原樣重跑：** #270 已合併；#272 F3 拋棄式 Agent 修 Bug／記錄／結案、F4 無關建議不做與任務收斂，已有單次正向證據；一次 Claude 真實 A→B ownership 交接已有紀錄；Solo R2／Lite 有非正式、非計數實驗資料。
- **未證明：** 真實 Internal Consumer 跨 Session 的完整產品自主交付；完整 Governance 的因果增益、一般化效果與成本效益。
- **證據天花板：** #272 的本機 Agent 審查紀錄不能冒充 GitHub Codex／人工正式 Review；#259 交接紀錄尚未合併，該次 CLI 過程沒有成功的模型自主推理；F3/F4 只證明各自受控情境。
- **工作規則：** 只針對會影響當前驗收、授權或資料完整性的缺陷做最小修正；無關的 P2/P3 一行紀錄後停止，不為了完善流程開新 Gate、Schema、Memory stream 或 PR。
- **通報原則：** 工作已達到事前 DONE 就停止。原本必要的 SessionEnd／Memory obligation 仍照既有契約處理；Task DONE 不等於 SessionEnd。

## 1. 2026-11-02 可核對的公開快照（會過期）

| 事項 | 快照 | 下次動作 |
|---|---|---|
| #270（統一核心規則） | 已合併至 main，merge commit `04e91055` | 不重做 |
| main Post-Merge Audit | `plan_freshness` PASS，`expansion_boundary` 的 `session_envelope` transitional 期限警告導致 Audit FAIL | R-02 |
| #272（F1–F5／F-J／A-1～A-3） | Draft，HEAD `4c9644f6`；**base 已是 main**；截至本快照未見該 HEAD 的 GitHub CI Check Runs／正式 Review | R-03 取得 exact-HEAD CI 與 Review，禁止以本機審查取代 |
| #271（既有過度治理／Loop handoff） | Docs-only Draft，仍以舊 #270 分支為 base | 獨立對帳；不是 #272 前置條件 |
| #245／#259（Claude ownership） | #245 REVIEW HOLD、#259 交接紀錄尚未合併 | 不能視為完整的真實 Agent 接手成功 |

公開來源：[PR #270](https://github.com/Gavin0099/ai-governance-framework/pull/270)、[PR #272](https://github.com/Gavin0099/ai-governance-framework/pull/272)、[PR #271](https://github.com/Gavin0099/ai-governance-framework/pull/271)、[main CI](https://github.com/Gavin0099/ai-governance-framework/actions/runs/41380993427)、[PR #259](https://github.com/Gavin0099/ai-governance-framework/pull/259)。狀態更新必須有新證據，不能因計畫寫「預期」就改成 DONE。

## 2. Slice 順序、依賴與 DONE

| Slice | 目標與最小範圍 | DONE 證據／不得宣稱 |
|---|---|---|
| **R-02 — main Drift 收斂** | 只裁決 `session_envelope` transitional→core／移除的正確處置；先比對 ADR-0002 #258，保持 envelope=identity、非 closeout obligation；不得因修警告而默默採納未完成的 ADR | 有具體決策、相應最小測試／審查與 main Post-Merge Audit PASS；不靠改日期、延長期限或放寬規則換綠燈 |
| **R-03 — #272 正式交付** | #272 已改以 main 為 base；核對新 base diff、在合併候選上取得 hosted CI 與獨立 Review，處理真正阻擋項，再依 Owner Gate 決定是否合併；若改 base 未自動觸發 CI，需另行按權限觸發 | exact-HEAD／實際合併候選證據及授權 Merge；**本機 APPROVE ≠ GitHub Review，沒有 CI 不能宣稱全綠** |
| **P-01 — 驗收計畫** | 本文件，僅 Docs-only Draft PR；固定 V/E 判準、保密、停止條件與下一步 | Draft PR 可讀、單檔 diff、無治理程式／Consumer 修改；**不阻擋 R-03** |
| **V-01 — Internal Consumer 唯讀盤點** | 在隔離工作區確認採用模式、Framework pin、dirty／未推送修改、lock 是否必要、Memory 行數與字元壓力、更新前後 `AGENTS.md` 的 32 KiB 預算、`CLAUDE.md` 是否具備收斂規則及實際載入證據 | 本地保留原始狀態與 rollback／方案甲更新計畫；不要求先公開或處理無關產品 commits；敏感證據僅內部保存 |
| **V-02 — 真實 Consumer F-7** | 依已核准方案甲：先切換 Framework 版本，再跑受治理更新；驗證正常更新、HOLD、原檔保留、重跑、失敗收據、可還原性；需另有 Consumer 寫入授權 | 正式 Consumer 版本與證據一致、無非授權改動；HOLD 不算更新成功 |
| **V-03／V-04／V-05 — 同一真實工作取證** | 先挑一個平台（**Claude 為候選，須在啟動前定案與核准**），使用真實模型與兩個新 Session：Session A 做產品工作並記錄未完事項；Session B 在新 Context 中接手、測試、完成並正式結案；事前凍結獨立 Oracle | 分開報告 V-03 Memory 讀寫、V-04 身分／ownership 交接、V-05 產品自主交付，三項不可互相代替；同一天兩 Session 可先驗收，跨日持久性未測須揭露 |
| **E-01A — 三組試跑** | **不使用 V-05 整合任務當樣本**；另選相同基準的任務，三組各跑一次，先驗證資料收集、評分、成本及隔離流程 | 僅證明實驗可量測；不能宣稱哪組有效或一般化 |
| **E-01B — 正式比較** | 若試跑可行且 Owner 已採納成本上限、門檻、樣本與任務封存，再以 3–5 個任務、每組 2–3 次作探索性重複比較（預估 18–45 次）；不將既有歷史樣本混入 | 全部結果含失敗、耗時／Token／人工介入與可比性限制；樣本仍偏小，不冒充統計定論 |
| **E-01C — 決策** | 依事前門檻輸出 KEEP／SIMPLIFY／STOP／INSUFFICIENT，不在看到結果後改門檻 | 若成本顯著增加而沒有可信收益，優先提減法；不自動開發新規則 |

**可並行：** R-02 及 P-01／V-01 唯讀準備；R-03 待適用的 main 與 CI／Merge 條件確立。R-03 不以 #271 或 P-01 完成為前置。V-02 需有 Framework 正式交付、Consumer 寫入範圍與獨立授權；後續實驗另行授權。

## 3. V-03～V-05：事前凍結自主交付驗收

1. **工作選擇：** 使用真正有價值、原本就要做的 Internal Consumer 產品任務；不捏造 Bug，不為驗收硬造新需求；公開文件不得揭露任務內容。
2. **事前凍結：** Owner 在 Agent 開始前固定任務、允許／禁止範圍、初始 commit、Oracle（預期輸出／測試及版本）、交接邊界與失敗條件。Agent 自己新增的測試是研發證據，不能取代外部 Oracle。
3. **執行：** 事前授權內由 Agent 自己分析、修改、測試、修正、記錄、接續與結案；Agent 可以做自我 Review，但**自我 Review 不能當獨立驗收**。另一 Agent Review 仍須綁定客觀驗收依據；Owner 或獨立執行的事前固定測試負責最終結果。
4. **介入類別分開記：** `RESCUE`（人類提供卡關解法）、`APPROVAL`（需要人的核准）、`CLARIFICATION`（需求澄清）。每類記次數與耗時，全部算互動成本；既有 Owner Gate 下的必要核准不算 AI 修復能力失敗，重複索取原已核准的同一操作則是可觀察摩擦。
5. **三項判定分開：** V-03 要有真實 Memory 寫入、身分綁定與新 Session 精確讀回；V-04 要有兩個 Session 的正式交接與授權隔離；V-05 要有產品獨立 Oracle PASS、在原授權範圍內無 `RESCUE`、記錄完整及合法 Closeout。
6. **停止／失敗：** 禁止動作正確 HOLD 是安全證據，**不是產品交付成功**。未取得核准、不可恢復狀態、超範圍與證據不足應回報 PARTIAL／HOLD／NOT_ASSESSABLE，不能填作 DONE。
7. **排除實驗：** 本整合工作是為了驗證 Full Governance 的交接設計，**不得拿來當 E-01 的 A/B/C 比較樣本**。

## 4. E-01：三組可比較的治理效益研究

| 組 | 精確處置 | 想回答的問題 |
|---|---|---|
| **A — Baseline** | 相同 Agent／模型／Harness／工具／產品授權與基本安全限制；無 Governance 專屬文字、Hook、Gate、Memory 記錄；必須用真正乾淨的 disposable repo，不能留下原有治理檔 | 未加入框架時的任務能力與成本 |
| **B — Rules Only** | A 的條件加上**版本凍結的精簡 Core Rules 本文**：`governance/AGENT_CORE_RULES.md` 的 `agent-core-rules BEGIN/END` 內容（記錄 exact SHA／digest）。**不是整份 AGENTS.md，也不帶 Hook、Gate、Governance Memory** | 單靠規則文字有多少效果與 Token 成本 |
| **C — Full Governance** | 同一份精簡 Core Rules，加上完整已核准的 Governance Hook／Gate／Memory／Evidence 流程；如有額外必要指令，記錄實際投入內容及 token | 完整執行治理相對 B 的額外淨效果（不把全部差異錯歸因於 Hook） |

- **公平性：** 共同固定模型、Harness、工具能力、安全與權限、任務內容、開始狀態、可用時間、評分 Oracle；獨立隔離各次執行，沒有跨組資料污染。每次重設 clean workspace 和 Memory 起點；A/B 不能讀到舊 Governance 訊號。若真實生產規則不允許停用治理，只能在經授權 disposable 環境做 A/B，不能繞過生產保護。
- **任務來源：** E-01A 的試跑任務與 V-05 不同；正式比較另行預註冊多個具體任務，包含失敗與無效試次；如只限一種 Consumer 類型，結論只適用該類型，不宣稱跨 Repo 通用。
- **計數：** E-01A 每組一次是量測管線試跑，不能宣稱療效；E-01B 要先凍結 3–5 個任務 × 每組 2–3 次、順序／隨機化、所有模型與工具版本、成本預算、上限與停止閾值。這是探索性設計，不是統計效力保證。
- **獨立評分：** Oracle／預期結果在跑之前封存；評分人盡可能不知道 A/B/C 身分。記錄產品成功、危險違規、誤擋、返工、人工介入三類、總時間、Token／金額（取得不到就標 UNKNOWN），以及歸因與不可比原因。
- **與 Skill Gate 分離：** 此處 E-01 是整體治理效果研究，不是既有四臂 Engineering Skill 計畫的正式 Gate 3／Gate 4；不可把歷史 Solo R2／Lite 非計數結果視為本實驗有效樣本。

## 5. 停止與決策規則（實驗前採納門檻）

| 判定 | 適用條件 |
|---|---|
| **KEEP** | 有可重現的產品／安全／人工負擔收益，且符合事前凍結的成本門檻 |
| **SIMPLIFY** | 對比未見可信的品質或救援改善，治理卻持續產生已超過事前可接受值的時間／Token／互動成本；優先減少無效流程 |
| **STOP** | 安全越界、偽造或無法核實的成果、污染不可恢復、超預算、未授權高風險操作、不可比的實驗條件；停止受影響的實驗或部署，不自動追加架構 |
| **INSUFFICIENT** | 樣本／成本／獨立證據不足，或數據不穩定；不強行作出有效或無效宣稱 |

**必須由 Owner 在 E-01B 前填定而非事後選擇：** 產品品質／安全最低條件、可容忍的 Token 與時間增幅、人工救援／核准／澄清的判讀門檻、每組次數、總成本預算與停損。此 Proposal **不擅自設定 X%**。STOP/IMPASSE 並非自動授權增加測試、重構或新 Gate。

## 6. 公開資料最小化與 Non-Claims

- 此公共 Proposal 只稱 **Internal Consumer**。不得含任何私有 Git 位置或連結、公司／客戶名稱、內部 repo／分支名稱、內部檔案路徑、產品特徵、程式碼片段、截圖、測試 fixture 或可推知內部細節的原始 evidence。
- 真實 Consumer 的 Task、Oracle、精確 SHA、授權、日志與成本資料只留在合規的內部保存處；公開版僅可發佈匿名化、經另行授權的結果彙總。
- 本 PR **不修改** `PLAN.md`、`memory/`、Framework Runtime、Hooks、Gate、Schema、CI、Consumer、protected hash；不做 Push 到 Consumer、不開真實實驗、不 Merge，也不授予任何後續寫入或高風險操作許可。
- 文件存在 **不等於** Agent 已讀取、Policy 已採納、CI 已通過、獨立 Review 已通過、Memory 自主交接已成功，也不等於 Governance 有效。

## 7. 相關既有文件（只引用，不複製治理條文）

- [既有 2026-10-29 instruction architecture／bounded loop proposal](2026-10-29-instruction-architecture-autonomous-loop.md)
- [#271 過度治理與 delivery-first handoff（仍為獨立 Draft）](https://github.com/Gavin0099/ai-governance-framework/pull/271)
- [Engineering Skill four-arm study 與既有 Gate 0–5](../governance/evidence-backed-engineering-skill-program-2026-07-24.md)
- [ADR-0002 提案／#258：Session Envelope 是 Identity，不是 Closeout Obligation](https://github.com/Gavin0099/ai-governance-framework/pull/258)
- [已合併 #270](https://github.com/Gavin0099/ai-governance-framework/pull/270)、[待交付 #272](https://github.com/Gavin0099/ai-governance-framework/pull/272)

**下個 Agent 的第一步：** 重新核對 R-02 的 main audit 與 #272 HEAD／base／CI；只繼續第一個有真實缺口且已授權的 Slice。P-01／V-01 可並行唯讀準備。不要因為看見本文件就重做已完成的 F3/F4、開新治理系統，或自行觸發 Consumer 寫入與 Merge。
